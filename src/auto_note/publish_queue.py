from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .article import ArticleError, load_article
from .paths import unique_path
from .publish_ready import PublishReadyReport, run_publish_ready
from .settings import load_settings


@dataclass(frozen=True)
class PublishQueueEntry:
    source: Path
    title: str
    article_status: str
    readiness: str
    detail: str
    next_action: str
    scheduled: str = ""
    body_chars: int = 0
    tags_count: int = 0


@dataclass(frozen=True)
class PublishQueueReport:
    project_dir: Path
    generated_at: datetime
    entries: list[PublishQueueEntry]

    @property
    def status(self) -> str:
        if any(entry.readiness == "error" for entry in self.entries):
            return "fail"
        if any(entry.readiness in {"blocked", "check"} for entry in self.entries):
            return "warn"
        return "pass"

    @property
    def ready_count(self) -> int:
        return sum(1 for entry in self.entries if entry.readiness == "postable")

    @property
    def check_count(self) -> int:
        return sum(1 for entry in self.entries if entry.readiness == "check")

    @property
    def blocked_count(self) -> int:
        return sum(1 for entry in self.entries if entry.readiness == "blocked")

    @property
    def done_count(self) -> int:
        return sum(1 for entry in self.entries if entry.readiness == "done")

    @property
    def error_count(self) -> int:
        return sum(1 for entry in self.entries if entry.readiness == "error")


def build_publish_queue(
    project_dir: Path,
    *,
    pattern: str | None = None,
    append_tags: bool | None = None,
) -> PublishQueueReport:
    project_dir = project_dir.resolve()
    settings = load_settings(project_dir)
    pattern = pattern or settings.article_glob
    append_tags = settings.append_tags_by_default if append_tags is None else append_tags
    articles_dir = project_dir / "articles"
    generated_at = datetime.now()

    if not articles_dir.exists():
        return PublishQueueReport(project_dir=project_dir, generated_at=generated_at, entries=[])

    entries = [_entry_for_path(path, append_tags=append_tags) for path in _article_paths(articles_dir, pattern)]
    entries.sort(key=_entry_sort_key)
    return PublishQueueReport(project_dir=project_dir, generated_at=generated_at, entries=entries)


def write_publish_queue_report(
    project_dir: Path,
    *,
    report: PublishQueueReport | None = None,
    pattern: str | None = None,
    append_tags: bool | None = None,
    include_private: bool = False,
) -> Path:
    project_dir = project_dir.resolve()
    report = report or build_publish_queue(project_dir, pattern=pattern, append_tags=append_tags)
    reports_dir = project_dir / ".auto-note" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(reports_dir / f"publish-queue-{report.generated_at:%Y%m%d-%H%M%S}.txt")
    path.write_text(format_publish_queue_report(report, include_private=include_private) + "\n", encoding="utf-8")
    return path


def list_publish_queue_reports(project_dir: Path) -> list[Path]:
    reports_dir = project_dir / ".auto-note" / "reports"
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("publish-queue-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def format_publish_queue_report(report: PublishQueueReport, *, include_private: bool = True) -> str:
    verdict = {"pass": "READY", "warn": "CHECK", "fail": "BLOCKED"}[report.status]
    lines = [
        "Publish queue / 投稿キュー",
        f"Generated: {report.generated_at:%Y-%m-%d %H:%M:%S}",
        f"Verdict: {verdict}",
        (
            "Items: "
            f"{report.ready_count} POSTABLE, "
            f"{report.check_count} CHECK, "
            f"{report.blocked_count} BLOCKED, "
            f"{report.done_count} DONE, "
            f"{report.error_count} ERROR"
        ),
        "",
    ]
    if not report.entries:
        lines.append("記事がありません。")
        return "\n".join(lines)

    next_actions: list[str] = []
    for index, entry in enumerate(report.entries, start=1):
        label = _readiness_label(entry.readiness)
        name = entry.source.name if include_private else f"article-{index:03d}.md"
        title = entry.title if include_private else f"<title:{len(entry.title)} chars>"
        scheduled = entry.scheduled or "-"
        lines.append(
            f"[{label}] {name}: title={title}, status={entry.article_status}, "
            f"scheduled={scheduled}, chars={entry.body_chars}, tags={entry.tags_count}, {entry.detail}"
        )
        if entry.next_action:
            lines.append(f"  next: {entry.next_action}")
            if entry.readiness in {"postable", "check", "blocked", "error"}:
                next_actions.append(f"- {name}: {entry.next_action}")

    if next_actions:
        lines.extend(["", "Next actions"])
        lines.extend(next_actions[:8])
    return "\n".join(lines)


def has_publish_queue_blockers(report: PublishQueueReport, *, strict: bool = False) -> bool:
    if any(entry.readiness in {"blocked", "error"} for entry in report.entries):
        return True
    return strict and any(entry.readiness == "check" for entry in report.entries)


def _article_paths(articles_dir: Path, pattern: str) -> list[Path]:
    return sorted(
        (path for path in articles_dir.glob(pattern) if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _entry_for_path(path: Path, *, append_tags: bool) -> PublishQueueEntry:
    try:
        article = load_article(path)
        report = run_publish_ready(path, append_tags=append_tags, smoke_helper=False)
    except (ArticleError, OSError) as exc:
        return PublishQueueEntry(
            source=path,
            title=path.stem,
            article_status="error",
            readiness="error",
            detail=str(exc),
            next_action="記事ファイルを開いてfrontmatterと本文を修正してください。",
        )

    readiness = _readiness_for(report)
    detail = _detail_for(report)
    return PublishQueueEntry(
        source=path,
        title=article.title,
        article_status=article.status or "draft",
        readiness=readiness,
        detail=detail,
        next_action=_next_action_for(report, readiness),
        scheduled=article.scheduled,
        body_chars=len(article.body),
        tags_count=len(article.tags),
    )


def _readiness_for(report: PublishReadyReport) -> str:
    status = report.article.status or "draft"
    if status == "published":
        return "done"
    if report.status == "pass":
        return "postable"
    if report.status == "fail":
        return "blocked"
    return "check"


def _detail_for(report: PublishReadyReport) -> str:
    counts = {
        "pass": sum(1 for item in report.items if item.status == "pass"),
        "info": sum(1 for item in report.items if item.status == "info"),
        "warn": sum(1 for item in report.items if item.status == "warn"),
        "fail": sum(1 for item in report.items if item.status == "fail"),
    }
    return f"{counts['pass']} OK, {counts['info']} INFO, {counts['warn']} WARN, {counts['fail']} NG"


def _next_action_for(report: PublishReadyReport, readiness: str) -> str:
    if readiness == "postable":
        return "投稿ヘルパーを開いてnoteへ転記できます。"
    if readiness == "done":
        if report.article.published_url:
            return "公開URLが記録済みです。必要に応じて記事一覧で管理してください。"
        return "公開URLを保存すると後から追跡しやすくなります。"
    for target in ("fail", "warn"):
        for item in report.items:
            if item.status == target and item.action:
                return item.action
    return "投稿準備の詳細を確認してください。"


def _entry_sort_key(entry: PublishQueueEntry) -> tuple[int, str, str]:
    rank = {
        "postable": 0,
        "check": 1,
        "blocked": 2,
        "error": 3,
        "done": 4,
    }.get(entry.readiness, 9)
    return (rank, entry.scheduled or "9999-99-99 99:99", entry.source.name.casefold())


def _readiness_label(readiness: str) -> str:
    return {
        "postable": "POSTABLE",
        "check": "CHECK",
        "blocked": "BLOCKED",
        "done": "DONE",
        "error": "ERROR",
    }.get(readiness, readiness.upper())
