from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .backup import inspect_backup, list_backups
from .maintenance import collect_privacy_failed_artifacts, format_bytes
from .quality import run_quality_checks
from .review import review_path
from .release import list_releases, verify_release_package
from .setup_check import run_setup_check
from .settings import load_settings


@dataclass(frozen=True)
class ReadinessItem:
    name: str
    status: str
    detail: str
    action: str = ""


@dataclass(frozen=True)
class ReadinessReport:
    score: int
    items: list[ReadinessItem]

    @property
    def ok(self) -> bool:
        return not any(item.status == "fail" for item in self.items)


OPTIONAL_SETUP_ITEMS = {"icon shortcut", "optional image optimization"}


def run_readiness(project_dir: Path) -> ReadinessReport:
    project_dir = project_dir.resolve()
    items: list[ReadinessItem] = []
    items.extend(_setup_items(project_dir))
    items.append(_quality_item(project_dir))
    items.append(_article_content_item(project_dir))
    items.append(_backup_item(project_dir))
    items.append(_release_item(project_dir))
    items.append(_privacy_cleanup_item(project_dir))
    return ReadinessReport(score=_score(items), items=items)


def format_readiness_report(report: ReadinessReport) -> str:
    counts = {
        "pass": sum(1 for item in report.items if item.status == "pass"),
        "info": sum(1 for item in report.items if item.status == "info"),
        "warn": sum(1 for item in report.items if item.status == "warn"),
        "fail": sum(1 for item in report.items if item.status == "fail"),
    }
    lines = [
        "Readiness report",
        f"Score: {report.score}/100",
        f"Items: {counts['pass']} OK, {counts['info']} INFO, {counts['warn']} WARN, {counts['fail']} NG",
        "",
    ]
    for item in report.items:
        label = {"pass": "OK", "info": "INFO", "warn": "WARN", "fail": "NG"}.get(item.status, item.status.upper())
        lines.append(f"[{label}] {item.name}: {item.detail}")
        if item.action:
            lines.append(f"  next: {item.action}")
    return "\n".join(lines)


def _setup_items(project_dir: Path) -> list[ReadinessItem]:
    items: list[ReadinessItem] = []
    for item in run_setup_check(project_dir, create=False):
        if item.ok:
            status = "pass"
            action = ""
        elif item.name in OPTIONAL_SETUP_ITEMS:
            status = "warn"
            action = _setup_action(item.name)
        else:
            status = "fail"
            action = _setup_action(item.name)
        items.append(ReadinessItem(f"setup: {item.name}", status, item.detail, action))
    return items


def _quality_item(project_dir: Path) -> ReadinessItem:
    checks = run_quality_checks(project_dir, include_articles=False)
    failures = [check for check in checks if check.status == "fail"]
    warnings = [check for check in checks if check.status == "warn"]
    if failures:
        return ReadinessItem(
            "product quality",
            "fail",
            f"{len(failures)} failure(s), {len(warnings)} warning(s)",
            "GUIの診断タブで品質チェックを開き、NG項目を修正してください。",
        )
    if warnings:
        return ReadinessItem(
            "product quality",
            "warn",
            f"{len(warnings)} warning(s)",
            "公開前に警告内容を確認してください。",
        )
    return ReadinessItem("product quality", "pass", f"{len(checks)} check(s) OK")


def _article_content_item(project_dir: Path) -> ReadinessItem:
    settings = load_settings(project_dir)
    try:
        reviews = review_path(
            project_dir / "articles",
            pattern=settings.article_glob,
            append_tags=settings.append_tags_by_default,
        )
    except Exception as exc:
        return ReadinessItem(
            "article content",
            "info",
            f"not ready to evaluate: {exc}",
            "`auto-note review .\\articles` で記事状態を確認できます。",
        )
    average = round(sum(review.score for review in reviews) / len(reviews)) if reviews else 0
    ready = sum(1 for review in reviews if review.ready)
    blockers = sum(1 for review in reviews if review.needs_fix)
    if blockers:
        detail = f"average {average}/100, {blockers} article(s) need fixes, {ready}/{len(reviews)} ready"
        action = "`auto-note review .\\articles` で記事ごとの改善項目を確認してください。"
    elif ready == len(reviews):
        detail = f"average {average}/100, all {len(reviews)} article(s) ready"
        action = ""
    else:
        detail = f"average {average}/100, no blockers, {ready}/{len(reviews)} ready"
        action = "`auto-note review .\\articles` で仕上げ項目を確認できます。"
    return ReadinessItem("article content", "info", detail, action)


def _backup_item(project_dir: Path) -> ReadinessItem:
    backups = list_backups(project_dir)
    if not backups:
        return ReadinessItem(
            "latest backup",
            "warn",
            "no backups found",
            "GUIの診断タブ、または `auto-note backup --project-dir .` で作成してください。",
        )
    latest = backups[0]
    try:
        inspection = inspect_backup(latest)
    except Exception as exc:
        return ReadinessItem(
            "latest backup",
            "fail",
            f"{latest.name}: unreadable backup ({exc})",
            "GUIの診断タブでバックアップ確認を開き、新しいバックアップを作成してください。",
        )
    if not inspection.ok:
        reasons: list[str] = []
        if inspection.unsafe_files:
            reasons.append(f"{len(inspection.unsafe_files)} unsafe file(s)")
        if not inspection.restorable_files:
            reasons.append("no restorable files")
        return ReadinessItem(
            "latest backup",
            "fail",
            f"{latest.name}: {', '.join(reasons) or 'verification failed'}",
            "GUIの診断タブでバックアップ確認を開き、新しいバックアップを作成してください。",
        )
    age_days = max(0, (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).days)
    if age_days > 7:
        return ReadinessItem(
            "latest backup",
            "warn",
            f"{latest.name} ({age_days} days old, {len(inspection.restorable_files)} file(s) verified)",
            "更新前や大量編集前に新しいバックアップを作成してください。",
        )
    return ReadinessItem("latest backup", "pass", f"{latest.name} ({len(inspection.restorable_files)} file(s) verified)")


def _release_item(project_dir: Path) -> ReadinessItem:
    releases = list_releases(project_dir)
    if not releases:
        return ReadinessItem(
            "release package",
            "warn",
            "no release packages found",
            "販売/配布前にGUIまたは `auto-note release --project-dir .` で作成してください。",
        )
    latest = releases[0]
    errors = verify_release_package(latest)
    if errors:
        return ReadinessItem(
            "release package",
            "fail",
            f"{latest.name}: {len(errors)} verification error(s)",
            "`auto-note release --verify <zip>` の結果を確認してください。",
        )
    return ReadinessItem("release package", "pass", f"{latest.name} verified")


def _privacy_cleanup_item(project_dir: Path) -> ReadinessItem:
    items = collect_privacy_failed_artifacts(project_dir, include_releases=True)
    if not items:
        return ReadinessItem("privacy cleanup", "pass", "no privacy audit cleanup candidates")
    release_dir = (project_dir / ".auto-note" / "releases").resolve()
    release_count = 0
    release_bytes = 0
    generated_count = 0
    generated_bytes = 0
    for item in items:
        try:
            item.path.resolve().relative_to(release_dir)
        except ValueError:
            generated_count += 1
            generated_bytes += item.size_bytes
            continue
        release_count += 1
        release_bytes += item.size_bytes
    total_bytes = generated_bytes + release_bytes
    return ReadinessItem(
        "privacy cleanup",
        "info",
        (
            f"{generated_count} generated artifact(s), {release_count} release package(s), "
            f"estimated reclaim {format_bytes(total_bytes)} "
            f"(generated {format_bytes(generated_bytes)}, releases {format_bytes(release_bytes)})"
        ),
        (
            "`auto-note cleanup --project-dir . --privacy-failed --include-releases` "
            "で候補と見込み解放容量を確認できます（プレビューでは削除しません）。"
        ),
    )


def _setup_action(name: str) -> str:
    actions = {
        "articles folder": "`auto-note setup --project-dir . --create` を実行してください。",
        "settings file": "`auto-note setup --project-dir . --create` を実行してください。",
        "settings readable": "`auto-note setup --project-dir . --create` で既定設定を書き直してください。",
        "GUI launcher": "配布ZIPを展開し直すか、インストール手順を確認してください。",
        "icon shortcut": "`shortcuts\\create-gui-shortcut.bat` でショートカットを作成できます。",
        "GUI": "Pythonのtkinterが使える環境で起動してください。",
        "frontmatter parser": "`python -m pip install -e .` を実行してください。",
        "optional image optimization": "画像最適化を使う場合は `shortcuts\\install-image-tools.bat` を実行してください。",
    }
    return actions.get(name, "セットアップ状態を確認してください。")


def _score(items: list[ReadinessItem]) -> int:
    if not items:
        return 0
    value = 0.0
    for item in items:
        if item.status == "pass":
            value += 1.0
        elif item.status == "info":
            value += 1.0
        elif item.status == "warn":
            value += 0.55
    return max(0, min(100, round(100 * value / len(items))))
