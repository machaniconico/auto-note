from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .article import Article, ArticleError, load_article
from .inspect import inspect_article
from .manual import write_manual_post_helper
from .review import review_article
from .workflow import set_article_status


@dataclass(frozen=True)
class PublishReadyItem:
    name: str
    status: str
    detail: str
    action: str = ""


@dataclass(frozen=True)
class PublishReadyReport:
    article: Article
    items: list[PublishReadyItem]
    helper_path: Path | None = None
    marked_ready: bool = False

    @property
    def status(self) -> str:
        if any(item.status == "fail" for item in self.items):
            return "fail"
        if any(item.status == "warn" for item in self.items):
            return "warn"
        return "pass"

    @property
    def ok(self) -> bool:
        return self.status == "pass"


def run_publish_ready(
    file: Path,
    *,
    append_tags: bool = False,
    smoke_helper: bool = False,
    output_dir: Path | None = None,
    mark_ready: bool = False,
) -> PublishReadyReport:
    article = load_article(file)
    helper_path: Path | None = None
    items = [
        _basic_item(article),
        _inspect_item(article, append_tags=append_tags),
        _review_item(article, append_tags=append_tags),
        _workflow_item(article),
    ]

    helper_item, helper_path = _helper_item(
        article,
        append_tags=append_tags,
        smoke_helper=smoke_helper,
        output_dir=output_dir or article.source.parent / ".auto-note" / "publish-ready",
    )
    items.append(helper_item)

    can_mark_ready = not any(item.status == "fail" for item in items)
    marked = False
    if mark_ready and can_mark_ready:
        set_article_status(article.source, "ready")
        article = load_article(article.source)
        marked = True
        items.append(PublishReadyItem("mark ready", "pass", "status updated to ready"))
    elif mark_ready:
        items.append(
            PublishReadyItem(
                "mark ready",
                "fail",
                "not updated because blocking issues remain",
                "先にNG項目を直してから再実行してください。",
            )
        )

    return PublishReadyReport(article=article, items=items, helper_path=helper_path, marked_ready=marked)


def format_publish_ready_report(report: PublishReadyReport, *, include_private: bool = True) -> str:
    counts = {
        "pass": sum(1 for item in report.items if item.status == "pass"),
        "info": sum(1 for item in report.items if item.status == "info"),
        "warn": sum(1 for item in report.items if item.status == "warn"),
        "fail": sum(1 for item in report.items if item.status == "fail"),
    }
    verdict = {
        "pass": "READY TO POST",
        "warn": "NEEDS REVIEW",
        "fail": "BLOCKED",
    }[report.status]
    article_label = str(report.article.source) if include_private else "<article>.md"
    title = report.article.title if include_private else f"<title:{len(report.article.title)} chars>"
    lines = [
        "Publish readiness report",
        f"Verdict: {verdict}",
        f"Article: {article_label}",
        f"Title: {title}",
        f"Status: {report.article.status}",
        f"Items: {counts['pass']} OK, {counts['info']} INFO, {counts['warn']} WARN, {counts['fail']} NG",
    ]
    if report.helper_path:
        helper = str(report.helper_path) if include_private else "<HELPER_HTML>"
        lines.append(f"Generated helper: {helper}")
    lines.append("")

    next_actions: list[str] = []
    for item in report.items:
        label = {"pass": "OK", "info": "INFO", "warn": "WARN", "fail": "NG"}.get(
            item.status,
            item.status.upper(),
        )
        detail = item.detail if include_private else _mask_item_detail(item.detail, report)
        lines.append(f"[{label}] {item.name}: {detail}")
        if item.action:
            lines.append(f"  next: {item.action}")
            next_actions.append(f"- {item.name}: {item.action}")

    if next_actions:
        lines.extend(["", "Next actions"])
        lines.extend(next_actions)
    return "\n".join(lines)


def has_publish_ready_blockers(report: PublishReadyReport, *, strict: bool = False) -> bool:
    if any(item.status == "fail" for item in report.items):
        return True
    return strict and any(item.status == "warn" for item in report.items)


def _mask_item_detail(detail: str, report: PublishReadyReport) -> str:
    masked = detail.replace(report.article.source.name, "<article>.md")
    masked = masked.replace(str(report.article.source), "<article>.md")
    masked = masked.replace(report.article.source.as_posix(), "<article>.md")
    if report.helper_path:
        masked = masked.replace(report.helper_path.name, "<helper>.html")
        masked = masked.replace(str(report.helper_path), "<HELPER_HTML>")
        masked = masked.replace(report.helper_path.as_posix(), "<HELPER_HTML>")
    return masked


def _basic_item(article: Article) -> PublishReadyItem:
    if not article.title.strip():
        return PublishReadyItem("article", "fail", "title is empty", "タイトルを入力してください。")
    return PublishReadyItem("article", "pass", f"{article.source.name} loaded")


def _inspect_item(article: Article, *, append_tags: bool) -> PublishReadyItem:
    report = inspect_article(article, append_tags=append_tags)
    errors = [issue for issue in report.issues if issue.level == "error"]
    warnings = [issue for issue in report.issues if issue.level == "warn"]
    if errors:
        return PublishReadyItem(
            "article check",
            "fail",
            f"{len(errors)} error(s), {len(warnings)} warning(s)",
            "GUIの選択記事チェックでNG項目を修正してください。",
        )
    if warnings:
        return PublishReadyItem(
            "article check",
            "warn",
            f"{len(warnings)} warning(s)",
            "投稿前に警告内容を確認してください。",
        )
    return PublishReadyItem(
        "article check",
        "pass",
        f"{report.stats.body_chars} chars, about {report.stats.reading_minutes} min",
    )


def _review_item(article: Article, *, append_tags: bool) -> PublishReadyItem:
    review = review_article(article, append_tags=append_tags)
    if review.needs_fix:
        blockers = sum(1 for item in review.items if item.level == "fix")
        return PublishReadyItem(
            "article review",
            "fail",
            f"score {review.score}/100, {blockers} fix item(s)",
            "GUIの改善プラン、または `auto-note improve <file>` で修正順を確認してください。",
        )
    if not review.ready:
        improvements = sum(1 for item in review.items if item.level == "improve")
        return PublishReadyItem(
            "article review",
            "warn",
            f"score {review.score}/100, {improvements} improvement item(s)",
            "GUIの改善プランで、導入、締め、タグ、画像などを確認してください。",
        )
    return PublishReadyItem("article review", "pass", f"score {review.score}/100")


def _workflow_item(article: Article) -> PublishReadyItem:
    if article.status == "published":
        return PublishReadyItem(
            "workflow",
            "warn",
            "already marked as published",
            "再投稿ではなく公開URLの記録だけでよいか確認してください。",
        )
    if article.status == "scheduled" and not article.scheduled:
        return PublishReadyItem(
            "workflow",
            "fail",
            "status is scheduled but scheduled is empty",
            "予定日時を入れるか、状態を下書きに戻してください。",
        )
    if article.status in {"ready", "scheduled"}:
        return PublishReadyItem("workflow", "pass", f"status is {article.status}")
    return PublishReadyItem(
        "workflow",
        "warn",
        f"status is {article.status or 'draft'}",
        "問題なければ `--mark-ready` またはGUIの状態保存で準備OKにできます。",
    )


def _helper_item(
    article: Article,
    *,
    append_tags: bool,
    smoke_helper: bool,
    output_dir: Path,
) -> tuple[PublishReadyItem, Path | None]:
    if not smoke_helper:
        return (
            PublishReadyItem(
                "posting helper",
                "info",
                "not generated",
                "`--smoke-helper` でブラウザを開かずHTML生成まで確認できます。",
            ),
            None,
        )
    try:
        helper_path = write_manual_post_helper(article, append_tags=append_tags, output_dir=output_dir)
    except (ArticleError, OSError) as exc:
        return (
            PublishReadyItem(
                "posting helper",
                "fail",
                str(exc),
                "記事内容と `.auto-note` への書き込み権限を確認してください。",
            ),
            None,
        )
    return (PublishReadyItem("posting helper", "pass", f"generated {helper_path.name}"), helper_path)
