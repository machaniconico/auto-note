from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .article import ArticleError, load_article
from .backup import list_backups
from .inspect import inspect_path
from .manual import write_manual_post_helper
from .review import review_path
from .settings import load_settings
from .setup_check import run_setup_check


@dataclass(frozen=True)
class QuickstartItem:
    name: str
    status: str
    detail: str
    action: str = ""


@dataclass(frozen=True)
class QuickstartReport:
    project_dir: Path
    score: int
    items: list[QuickstartItem]
    helper_path: Path | None = None

    @property
    def ok(self) -> bool:
        return not any(item.status == "fail" for item in self.items)

    @property
    def has_warnings(self) -> bool:
        return any(item.status == "warn" for item in self.items)


ESSENTIAL_SETUP_ITEMS = {"project folder", "articles folder", "settings file", "GUI launcher"}


def run_quickstart(project_dir: Path, *, smoke_helper: bool = False) -> QuickstartReport:
    project_dir = project_dir.resolve()
    settings = load_settings(project_dir)
    articles_dir = project_dir / "articles"
    article_paths = _article_paths(articles_dir, settings.article_glob)
    latest_article = article_paths[0] if article_paths else None

    helper_path: Path | None = None
    items = [
        _setup_item(project_dir),
        _article_item(article_paths),
        _article_check_item(articles_dir, settings.article_glob, settings.append_tags_by_default),
        _article_review_item(articles_dir, settings.article_glob, settings.append_tags_by_default),
    ]
    helper_item, helper_path = _helper_item(
        project_dir,
        latest_article,
        append_tags=settings.append_tags_by_default,
        smoke_helper=smoke_helper,
    )
    items.append(helper_item)
    items.append(_note_login_item())
    items.append(_backup_item(project_dir))

    return QuickstartReport(
        project_dir=project_dir,
        score=_score(items),
        items=items,
        helper_path=helper_path,
    )


def format_quickstart_report(report: QuickstartReport, *, include_private: bool = True) -> str:
    counts = {
        "pass": sum(1 for item in report.items if item.status == "pass"),
        "info": sum(1 for item in report.items if item.status == "info"),
        "warn": sum(1 for item in report.items if item.status == "warn"),
        "fail": sum(1 for item in report.items if item.status == "fail"),
    }
    lines = [
        "Quickstart report",
        f"Score: {report.score}/100",
        f"Items: {counts['pass']} OK, {counts['info']} INFO, {counts['warn']} WARN, {counts['fail']} NG",
    ]
    if report.helper_path:
        lines.append(f"Generated helper: {report.helper_path}")
    lines.append("")

    next_actions: list[str] = []
    for item in report.items:
        label = {"pass": "OK", "info": "INFO", "warn": "WARN", "fail": "NG"}.get(
            item.status,
            item.status.upper(),
        )
        lines.append(f"[{label}] {item.name}: {item.detail}")
        if item.action:
            lines.append(f"  next: {item.action}")
            next_actions.append(f"- {item.name}: {item.action}")

    if next_actions:
        lines.extend(["", "Next actions"])
        lines.extend(next_actions)
    text = "\n".join(lines)
    if include_private:
        return text
    return _mask_private_quickstart_details(text, report)


def has_quickstart_blockers(report: QuickstartReport, *, strict: bool = False) -> bool:
    if any(item.status == "fail" for item in report.items):
        return True
    return strict and any(item.status == "warn" for item in report.items)


def _article_paths(articles_dir: Path, pattern: str) -> list[Path]:
    if not articles_dir.exists():
        return []
    return sorted(
        (path for path in articles_dir.glob(pattern) if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _setup_item(project_dir: Path) -> QuickstartItem:
    checks = run_setup_check(project_dir, create=False)
    missing = [item.name for item in checks if not item.ok]
    missing_essential = [name for name in missing if name in ESSENTIAL_SETUP_ITEMS]
    if missing_essential:
        return QuickstartItem(
            "setup",
            "fail",
            f"missing: {', '.join(missing_essential)}",
            "`auto-note setup --project-dir . --create` を実行してください。",
        )
    if missing:
        return QuickstartItem(
            "setup",
            "warn",
            f"optional missing: {', '.join(missing)}",
            "任意機能が必要な場合はセットアップ確認のWARNを確認してください。",
        )
    return QuickstartItem("setup", "pass", f"{len(checks)} setup check(s) OK")


def _article_item(article_paths: list[Path]) -> QuickstartItem:
    if not article_paths:
        return QuickstartItem(
            "first article",
            "warn",
            "no markdown articles",
            "GUIのスターター一式、または `auto-note starter-pack --project-dir .` でサンプル記事と予定を作成してください。",
        )
    return QuickstartItem(
        "first article",
        "pass",
        f"{len(article_paths)} article(s), latest {article_paths[0].name}",
    )


def _article_check_item(articles_dir: Path, pattern: str, append_tags: bool) -> QuickstartItem:
    try:
        reports = inspect_path(articles_dir, pattern=pattern, append_tags=append_tags)
    except ArticleError as exc:
        return QuickstartItem(
            "article check",
            "info",
            f"not ready: {exc}",
            "記事作成後にGUIの全体チェックを実行してください。",
        )
    errors = sum(1 for report in reports if not report.ok)
    warnings = sum(1 for report in reports for issue in report.issues if issue.level == "warn")
    if errors:
        return QuickstartItem(
            "article check",
            "fail",
            f"{errors} article(s) have blocking issues",
            "GUIのチェックタブ、または `auto-note check .\\articles` でNG項目を修正してください。",
        )
    if warnings:
        return QuickstartItem(
            "article check",
            "warn",
            f"{warnings} warning(s)",
            "投稿前に警告内容を確認してください。",
        )
    return QuickstartItem("article check", "pass", f"{len(reports)} article(s) OK")


def _article_review_item(articles_dir: Path, pattern: str, append_tags: bool) -> QuickstartItem:
    try:
        reviews = review_path(articles_dir, pattern=pattern, append_tags=append_tags)
    except ArticleError as exc:
        return QuickstartItem(
            "article review",
            "info",
            f"not ready: {exc}",
            "記事作成後にGUIのチェックタブでレビュー更新を実行してください。",
        )
    average = round(sum(review.score for review in reviews) / len(reviews)) if reviews else 0
    blockers = sum(1 for review in reviews if review.needs_fix)
    ready = sum(1 for review in reviews if review.ready)
    if blockers:
        return QuickstartItem(
            "article review",
            "warn",
            f"average {average}/100, {blockers} article(s) need fixes, {ready}/{len(reviews)} ready",
            "`auto-note review .\\articles` で改善項目を確認してください。",
        )
    if ready == len(reviews):
        return QuickstartItem("article review", "pass", f"average {average}/100, all {len(reviews)} ready")
    return QuickstartItem(
        "article review",
        "warn",
        f"average {average}/100, no blockers, {ready}/{len(reviews)} ready",
        "投稿前に導入、まとめ、タグ、画像などの仕上げを確認してください。",
    )


def _helper_item(
    project_dir: Path,
    article_path: Path | None,
    *,
    append_tags: bool,
    smoke_helper: bool,
) -> tuple[QuickstartItem, Path | None]:
    if article_path is None:
        return (
            QuickstartItem(
                "posting helper",
                "info",
                "waiting for an article",
                "記事作成後にGUIの投稿ヘルパーを開いてください。",
            ),
            None,
        )
    if not smoke_helper:
        return (
            QuickstartItem(
                "posting helper",
                "pass",
                f"ready for {article_path.name}",
                "`auto-note quickstart --smoke-helper` でHTML生成まで確認できます。",
            ),
            None,
        )
    try:
        article = load_article(article_path)
        helper_path = write_manual_post_helper(
            article,
            append_tags=append_tags,
            output_dir=project_dir / ".auto-note" / "quickstart",
        )
    except (ArticleError, OSError) as exc:
        return (
            QuickstartItem(
                "posting helper",
                "fail",
                str(exc),
                "記事のfrontmatterと `.auto-note` フォルダへの書き込み権限を確認してください。",
            ),
            None,
        )
    return (
        QuickstartItem("posting helper", "pass", f"generated {helper_path.name}"),
        helper_path,
    )


def _note_login_item() -> QuickstartItem:
    return QuickstartItem(
        "note login",
        "info",
        "login state is checked in the normal browser",
        "GUIのログイン安全ガイドを確認し、noteログイン、または普段使うブラウザで note.com にログインしてください。",
    )


def _backup_item(project_dir: Path) -> QuickstartItem:
    backups = list_backups(project_dir)
    if not backups:
        return QuickstartItem(
            "backup",
            "warn",
            "no backups found",
            "初回設定後にGUIのバックアップ作成、または `auto-note backup --project-dir .` を実行してください。",
        )
    latest = backups[0]
    age_days = max(0, (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).days)
    if age_days > 7:
        return QuickstartItem(
            "backup",
            "warn",
            f"{latest.name} ({age_days} days old)",
            "投稿前や更新前に新しいバックアップを作成してください。",
        )
    return QuickstartItem("backup", "pass", latest.name)


def _score(items: list[QuickstartItem]) -> int:
    if not items:
        return 0
    value = 0.0
    for item in items:
        if item.status in {"pass", "info"}:
            value += 1.0
        elif item.status == "warn":
            value += 0.55
    return max(0, min(100, round(100 * value / len(items))))


def _mask_private_quickstart_details(text: str, report: QuickstartReport) -> str:
    masked = text
    settings = load_settings(report.project_dir)
    articles_dir = report.project_dir / "articles"
    if articles_dir.exists():
        article_paths = sorted(path for path in articles_dir.glob(settings.article_glob) if path.is_file())
        for index, path in enumerate(article_paths, start=1):
            masked = masked.replace(path.name, f"article-{index:03d}.md")

    helper_paths: list[Path] = []
    if report.helper_path:
        helper_paths.append(report.helper_path)
    quickstart_dir = report.project_dir / ".auto-note" / "quickstart"
    if quickstart_dir.exists():
        helper_paths.extend(path for path in quickstart_dir.glob("*.html") if path.is_file())
    for path in sorted(set(helper_paths), key=lambda item: str(item)):
        masked = masked.replace(str(path), "<HELPER_HTML>")
        masked = masked.replace(path.as_posix(), "<HELPER_HTML>")
        masked = masked.replace(path.name, "<helper>.html")
    return masked
