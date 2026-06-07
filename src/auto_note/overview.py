from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .article import Article, ArticleError, load_article
from .paths import unique_path
from .publish_queue import PublishQueueEntry, build_publish_queue
from .settings import load_settings
from .workflow import load_ideas


@dataclass(frozen=True)
class OverviewItem:
    name: str
    status: str
    detail: str
    action: str = ""
    source: str = ""
    target_path: str = ""


@dataclass(frozen=True)
class OverviewReport:
    project_dir: Path
    generated_at: datetime
    total_articles: int
    status_counts: dict[str, int]
    items: list[OverviewItem]

    @property
    def status(self) -> str:
        if any(item.status == "fail" for item in self.items):
            return "blocked"
        if any(item.status == "warn" for item in self.items):
            return "check"
        return "ready"


def build_overview(
    project_dir: Path,
    *,
    days: int = 14,
    stale_days: int = 14,
    pattern: str | None = None,
) -> OverviewReport:
    project_dir = project_dir.resolve()
    settings = load_settings(project_dir)
    pattern = pattern or settings.article_glob
    articles = _load_articles(project_dir / "articles", pattern)
    status_counts = {status: 0 for status in ("draft", "ready", "scheduled", "published", "error")}
    for article in articles:
        status = article.status if article.status in status_counts else "draft"
        status_counts[status] += 1

    items: list[OverviewItem] = []
    items.append(_next_publish_item(project_dir))
    items.append(_schedule_item(articles, days=days))
    items.append(_stale_drafts_item(articles, stale_days=stale_days))
    items.append(_published_url_item(articles))
    items.append(_idea_item(project_dir, has_articles=bool(articles)))
    return OverviewReport(
        project_dir=project_dir,
        generated_at=datetime.now(),
        total_articles=len(articles),
        status_counts=status_counts,
        items=items,
    )


def format_overview_report(report: OverviewReport, *, include_private: bool = True) -> str:
    verdict = {"ready": "READY", "check": "CHECK", "blocked": "BLOCKED"}[report.status]
    lines = [
        "Overview / 運用サマリー",
        f"Generated: {report.generated_at:%Y-%m-%d %H:%M:%S}",
        f"Verdict: {verdict}",
        (
            "Articles: "
            f"{report.total_articles} total, "
            f"{report.status_counts.get('draft', 0)} draft, "
            f"{report.status_counts.get('ready', 0)} ready, "
            f"{report.status_counts.get('scheduled', 0)} scheduled, "
            f"{report.status_counts.get('published', 0)} published"
        ),
        "",
    ]
    next_actions: list[str] = []
    for item in report.items:
        label = {"pass": "OK", "info": "INFO", "warn": "WARN", "fail": "NG"}.get(
            item.status,
            item.status.upper(),
        )
        detail = _mask_private(item.detail, report) if not include_private else item.detail
        action = _mask_private(item.action, report) if not include_private else item.action
        lines.append(f"[{label}] {item.name}: {detail}")
        if action:
            lines.append(f"  next: {action}")
            if item.status in {"fail", "warn", "info"}:
                next_actions.append(f"- {item.name}: {action}")
    if next_actions:
        lines.extend(["", "Next actions"])
        lines.extend(next_actions[:8])
    return "\n".join(lines)


def has_overview_blockers(report: OverviewReport, *, strict: bool = False) -> bool:
    if any(item.status == "fail" for item in report.items):
        return True
    return strict and any(item.status == "warn" for item in report.items)


def write_overview_report(
    project_dir: Path,
    *,
    report: OverviewReport,
    include_private: bool = False,
) -> Path:
    reports_dir = project_dir.resolve() / ".auto-note" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(reports_dir / f"overview-{report.generated_at:%Y%m%d-%H%M%S}.txt")
    path.write_text(format_overview_report(report, include_private=include_private) + "\n", encoding="utf-8")
    return path


def list_overview_reports(project_dir: Path) -> list[Path]:
    reports_dir = project_dir / ".auto-note" / "reports"
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("overview-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def _load_articles(articles_dir: Path, pattern: str) -> list[Article]:
    if not articles_dir.exists():
        return []
    articles: list[Article] = []
    for path in sorted(articles_dir.glob(pattern)):
        if not path.is_file():
            continue
        try:
            articles.append(load_article(path))
        except ArticleError:
            continue
    return articles


def _next_publish_item(project_dir: Path) -> OverviewItem:
    try:
        queue = build_publish_queue(project_dir)
    except Exception as exc:
        return OverviewItem(
            "next publish",
            "fail",
            f"publish queue unavailable: {exc}",
            "記事ファイルと設定を確認してください。",
            "publish-queue",
        )
    if not queue.entries:
        return OverviewItem(
            "next publish",
            "info",
            "no articles yet",
            "練習記事または新規記事を作成してください。",
            "publish-queue",
        )
    entry = _first_queue_entry(queue.entries)
    if entry is None:
        return OverviewItem(
            "next publish",
            "info",
            "all articles are already marked as published",
            "次の記事アイデアを追加するか、新規記事を作成してください。",
            "publish-queue",
        )
    label = _queue_label(entry)
    status = "pass" if entry.readiness == "postable" else "warn" if entry.readiness in {"check", "blocked"} else "fail"
    return OverviewItem(
        "next publish",
        status,
        f"{label}: {entry.title} ({entry.source.name})",
        entry.next_action or "投稿キューを確認してください。",
        "publish-queue",
        str(entry.source),
    )


def _schedule_item(articles: list[Article], *, days: int) -> OverviewItem:
    now = datetime.now()
    scheduled = [(article, _parse_schedule_or_none(article.scheduled)) for article in articles if article.scheduled]
    scheduled = [(article, value) for article, value in scheduled if value is not None]
    overdue = [(article, value) for article, value in scheduled if value < now and article.status != "published"]
    today = [(article, value) for article, value in scheduled if value.date() == now.date()]
    upcoming = [
        (article, value)
        for article, value in scheduled
        if 0 <= (value.date() - now.date()).days <= max(0, days)
    ]
    if overdue:
        detail = _article_list_detail(overdue[:3])
        return OverviewItem(
            "schedule",
            "warn",
            f"{len(overdue)} overdue scheduled article(s): {detail}",
            "予定日時を更新するか、公開済みURLを保存してください。",
            "calendar",
            str(overdue[0][0].source),
        )
    if today:
        detail = _article_list_detail(today[:3])
        return OverviewItem(
            "schedule",
            "info",
            f"{len(today)} article(s) scheduled today: {detail}",
            "投稿ヘルパーを開き、公開後にURLを保存してください。",
            "calendar",
            str(today[0][0].source),
        )
    if upcoming:
        detail = _article_list_detail(upcoming[:3])
        return OverviewItem("schedule", "pass", f"{len(upcoming)} upcoming article(s): {detail}", source="calendar")
    return OverviewItem(
        "schedule",
        "info",
        f"no scheduled articles in the next {days} day(s)",
        "準備OKの記事に公開予定を入れると運用しやすくなります。",
        "calendar",
    )


def _stale_drafts_item(articles: list[Article], *, stale_days: int) -> OverviewItem:
    now = datetime.now()
    stale: list[tuple[Article, int]] = []
    for article in articles:
        if (article.status or "draft") != "draft":
            continue
        try:
            age = (now - datetime.fromtimestamp(article.source.stat().st_mtime)).days
        except OSError:
            continue
        if age >= max(1, stale_days):
            stale.append((article, age))
    stale.sort(key=lambda item: item[1], reverse=True)
    if not stale:
        return OverviewItem("stale drafts", "pass", f"no draft older than {stale_days} day(s)")
    detail = ", ".join(f"{article.title} ({age}d)" for article, age in stale[:3])
    return OverviewItem(
        "stale drafts",
        "warn",
        f"{len(stale)} stale draft(s): {detail}",
        "古い下書きを改善プランで仕上げるか、不要なら整理してください。",
        "articles",
        str(stale[0][0].source),
    )


def _published_url_item(articles: list[Article]) -> OverviewItem:
    missing = [article for article in articles if article.status == "published" and not article.published_url]
    if not missing:
        return OverviewItem("published URLs", "pass", "published articles have URLs or none are published")
    detail = ", ".join(f"{article.title} ({article.source.name})" for article in missing[:3])
    return OverviewItem(
        "published URLs",
        "warn",
        f"{len(missing)} published article(s) without URL: {detail}",
        "公開URLを保存すると、後から投稿一覧を追いやすくなります。",
        "workflow",
        str(missing[0].source),
    )


def _idea_item(project_dir: Path, *, has_articles: bool) -> OverviewItem:
    ideas = [idea for idea in load_ideas(project_dir) if not idea.promoted_to]
    if ideas:
        return OverviewItem("ideas", "pass", f"{len(ideas)} open idea(s)")
    if has_articles:
        return OverviewItem(
            "ideas",
            "info",
            "no open ideas",
            "次回用のネタをアイデア箱に1つ追加しておくと継続しやすくなります。",
            "ideas",
        )
    return OverviewItem(
        "ideas",
        "info",
        "no articles or ideas yet",
        "練習記事を作るか、アイデアを1つ追加してください。",
        "ideas",
    )


def _first_queue_entry(entries: list[PublishQueueEntry]) -> PublishQueueEntry | None:
    for readiness in ("postable", "check", "blocked", "error"):
        for entry in entries:
            if entry.readiness == readiness:
                return entry
    return None


def _queue_label(entry: PublishQueueEntry) -> str:
    return {
        "postable": "POSTABLE",
        "check": "CHECK",
        "blocked": "BLOCKED",
        "error": "ERROR",
        "done": "DONE",
    }.get(entry.readiness, entry.readiness.upper())


def _parse_schedule_or_none(value: str) -> datetime | None:
    normalized = value.strip().replace("T", " ")
    if not normalized:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            pass
    return None


def _article_list_detail(items: list[tuple[Article, datetime]]) -> str:
    return ", ".join(f"{article.title} ({when:%Y-%m-%d %H:%M})" for article, when in items)


def _mask_private(text: str, report: OverviewReport) -> str:
    masked = text
    articles_dir = report.project_dir / "articles"
    if articles_dir.exists():
        for path in articles_dir.glob("*"):
            if path.is_file():
                masked = masked.replace(str(path), "<article>.md")
                masked = masked.replace(path.as_posix(), "<article>.md")
                masked = masked.replace(path.name, "<article>.md")
                try:
                    title = load_article(path).title
                except ArticleError:
                    continue
                masked = masked.replace(f"{title} (", f"<title:{len(title)} chars> (")
                if len(title.strip()) >= 6:
                    masked = masked.replace(title, f"<title:{len(title)} chars>")
    return masked
