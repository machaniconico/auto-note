from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys

from .action_plan import build_action_plan
from .quality import run_quality_checks
from .readiness import run_readiness
from .release import create_release_package, list_releases, verify_release_package


@dataclass(frozen=True)
class PreflightItem:
    name: str
    status: str
    detail: str
    action: str = ""


@dataclass(frozen=True)
class PreflightReport:
    project_dir: Path
    status: str
    readiness_score: int
    items: list[PreflightItem]
    created_release: Path | None = None

    @property
    def ok(self) -> bool:
        return self.status != "fail"

    @property
    def has_warnings(self) -> bool:
        return any(item.status == "warn" for item in self.items)


def run_preflight(
    project_dir: Path,
    *,
    create_release: bool = False,
    install_smoke: bool = False,
    gui_smoke: bool = False,
    content_strict: bool = False,
    include_sales_handoffs: bool = True,
) -> PreflightReport:
    project_dir = project_dir.resolve()
    created_release = create_release_package(project_dir) if create_release else None

    readiness = run_readiness(project_dir)
    product_quality = run_quality_checks(project_dir, include_articles=False)
    content_quality = run_quality_checks(project_dir, include_articles=True)
    diagnostics = _run_diagnostics(project_dir)
    items: list[PreflightItem] = []

    items.append(_readiness_item(readiness))
    items.append(_action_plan_item(project_dir, readiness, include_sales_handoffs=include_sales_handoffs))
    items.append(_diagnostics_item(diagnostics))
    items.append(_troubleshoot_item(project_dir, include_sales_handoffs=include_sales_handoffs))
    items.append(_quality_item(product_quality))
    items.append(_article_review_item(content_quality, strict=content_strict))
    items.append(_backup_item(readiness))
    items.append(_release_item(project_dir))
    items.append(_privacy_item(project_dir, include_sales_handoffs=include_sales_handoffs))
    if gui_smoke:
        items.append(_gui_smoke_item(project_dir))
    if install_smoke:
        items.append(_install_smoke_item(project_dir))
    if created_release:
        errors = verify_release_package(created_release)
        items.append(
            PreflightItem(
                "created release",
                "fail" if errors else "pass",
                f"{created_release.name}: {len(errors)} verification error(s)" if errors else created_release.name,
                "`auto-note release --verify <zip>` の結果を確認してください。" if errors else "",
            )
        )

    status = _overall_status(items)
    return PreflightReport(
        project_dir=project_dir,
        status=status,
        readiness_score=readiness.score,
        items=items,
        created_release=created_release,
    )


def format_preflight_report(report: PreflightReport) -> str:
    counts = {
        "pass": sum(1 for item in report.items if item.status == "pass"),
        "info": sum(1 for item in report.items if item.status == "info"),
        "warn": sum(1 for item in report.items if item.status == "warn"),
        "fail": sum(1 for item in report.items if item.status == "fail"),
    }
    verdict = {
        "pass": "READY",
        "warn": "READY WITH WARNINGS",
        "fail": "BLOCKED",
    }.get(report.status, report.status.upper())
    lines = [
        "Preflight report",
        f"Verdict: {verdict}",
        f"Readiness score: {report.readiness_score}/100",
        f"Items: {counts['pass']} OK, {counts['info']} INFO, {counts['warn']} WARN, {counts['fail']} NG",
    ]
    if report.created_release:
        lines.append(f"Created release: {report.created_release}")
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
    return "\n".join(lines)


def has_preflight_blockers(report: PreflightReport, *, strict: bool = False) -> bool:
    if report.status == "fail":
        return True
    return strict and report.status == "warn"


def _run_diagnostics(project_dir: Path):
    from .diagnostics import run_diagnostics

    return run_diagnostics(project_dir)


def _readiness_item(readiness) -> PreflightItem:
    failures = [item for item in readiness.items if item.status == "fail"]
    warnings = [item for item in readiness.items if item.status == "warn"]
    if failures:
        return PreflightItem(
            "readiness",
            "fail",
            f"{readiness.score}/100, {len(failures)} failure(s), {len(warnings)} warning(s)",
            "準備度レポートのNG項目を先に修正してください。",
        )
    if warnings or readiness.score < 100:
        return PreflightItem(
            "readiness",
            "warn",
            f"{readiness.score}/100, {len(warnings)} warning(s)",
            "販売/配布前に警告内容を確認してください。",
        )
    return PreflightItem("readiness", "pass", f"{readiness.score}/100")


def _diagnostics_item(diagnostics) -> PreflightItem:
    failures = [item for item in diagnostics if not item.ok]
    if failures:
        return PreflightItem(
            "diagnostics",
            "fail",
            f"{len(failures)} diagnostic failure(s)",
            "`auto-note diagnose` のNG項目を確認してください。",
        )
    return PreflightItem("diagnostics", "pass", f"{len(diagnostics)} item(s) OK")


def _troubleshoot_item(project_dir: Path, *, include_sales_handoffs: bool = True) -> PreflightItem:
    from .troubleshoot import run_troubleshoot

    report = run_troubleshoot(project_dir, include_sales_handoffs=include_sales_handoffs)
    failures = [item for item in report.items if item.status == "fail"]
    warnings = [item for item in report.items if item.status == "warn"]
    serious_warnings = [item for item in warnings if item.name != "privacy cleanup candidates"]
    if failures:
        return PreflightItem(
            "troubleshoot",
            "fail",
            _troubleshoot_detail(failures, warnings),
            failures[0].action or "GUIの診断タブでトラブル診断を確認してください。",
        )
    if serious_warnings:
        return PreflightItem(
            "troubleshoot",
            "warn",
            _troubleshoot_detail(serious_warnings, warnings),
            serious_warnings[0].action or "GUIの診断タブでトラブル診断を確認してください。",
        )
    if warnings:
        action = warnings[0].action if warnings else ""
        return PreflightItem(
            "troubleshoot",
            "info",
            _troubleshoot_detail([], warnings),
            action,
        )
    return PreflightItem("troubleshoot", "pass", f"{len(report.items)} item(s) checked")


def _action_plan_item(project_dir: Path, readiness, *, include_sales_handoffs: bool = True) -> PreflightItem:
    report = build_action_plan(
        project_dir,
        readiness=readiness,
        include_sales_handoffs=include_sales_handoffs,
        limit=3,
    )
    top = report.steps[0] if report.steps else None
    detail = report.status
    if top:
        detail = f"{report.status}, top: {top.title}"
    action = top.action if top else ""
    if report.status == "BLOCKED":
        return PreflightItem("action plan", "fail", detail, action)
    if report.status == "NEEDS ATTENTION":
        return PreflightItem("action plan", "info", detail, action)
    return PreflightItem("action plan", "pass", detail)


def _quality_item(checks) -> PreflightItem:
    failures = [check for check in checks if check.status == "fail"]
    warnings = [check for check in checks if check.status == "warn"]
    if failures:
        return PreflightItem(
            "quality",
            "fail",
            f"{len(failures)} failure(s), {len(warnings)} warning(s)",
            "GUIの診断タブで品質チェックを開き、NG項目を修正してください。",
        )
    if warnings:
        return PreflightItem(
            "quality",
            "warn",
            f"{len(warnings)} warning(s)",
            "警告がユーザー記事由来か、配布物由来かを確認してください。",
        )
    return PreflightItem("quality", "pass", f"{len(checks)} check(s) OK")


def _article_review_item(checks, *, strict: bool = False) -> PreflightItem:
    review = next((check for check in checks if check.name == "article review"), None)
    if review is None:
        return PreflightItem(
            "article review",
            "warn" if strict else "info",
            "not available",
            "`auto-note review .\\articles` を確認してください。",
        )
    action = "`auto-note review .\\articles` で記事ごとの改善項目を確認してください。" if review.status == "warn" else ""
    status = review.status
    if status == "warn" and not strict:
        status = "info"
    return PreflightItem("article review", status, review.detail, action)


def _backup_item(readiness) -> PreflightItem:
    item = next((entry for entry in readiness.items if entry.name == "latest backup"), None)
    if item is None:
        return PreflightItem("backup", "warn", "latest backup status unavailable", "手動バックアップを作成してください。")
    return PreflightItem("backup", item.status, item.detail, item.action)


def _release_item(project_dir: Path) -> PreflightItem:
    releases = list_releases(project_dir)
    if not releases:
        return PreflightItem(
            "release package",
            "warn",
            "no release packages found",
            "`auto-note preflight --create-release` または `auto-note release` で作成してください。",
        )
    latest = releases[0]
    errors = verify_release_package(latest)
    if errors:
        return PreflightItem(
            "release package",
            "fail",
            f"{latest.name}: {len(errors)} verification error(s)",
            "`auto-note release --verify <zip>` の結果を確認してください。",
        )
    return PreflightItem("release package", "pass", f"{latest.name} verified")


def _privacy_item(project_dir: Path, *, include_sales_handoffs: bool = True) -> PreflightItem:
    from .privacy import run_privacy_audit

    report = run_privacy_audit(project_dir, include_sales_handoffs=include_sales_handoffs)
    failures = [item for item in report.items if item.status == "fail"]
    warnings = [item for item in report.items if item.status == "warn"]
    checked = sum(1 for item in report.items if item.status == "pass")
    if failures:
        return PreflightItem(
            "privacy audit",
            "fail",
            f"{len(failures)} failure(s), {checked} artifact(s) OK",
            "`auto-note privacy-audit --project-dir .` のNG項目を確認してください。",
        )
    if warnings:
        return PreflightItem(
            "privacy audit",
            "warn",
            f"{len(warnings)} warning(s), {checked} artifact(s) OK",
            "`auto-note privacy-audit --project-dir .` の警告を確認してください。",
        )
    return PreflightItem("privacy audit", "pass", f"{checked} artifact(s) OK")


def _install_smoke_item(project_dir: Path) -> PreflightItem:
    script = project_dir / "scripts" / "smoke-install.ps1"
    if not script.exists():
        return PreflightItem(
            "install smoke",
            "fail",
            f"script not found: {script}",
            "scripts\\smoke-install.ps1 が配布に含まれているか確認してください。",
        )
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        return PreflightItem(
            "install smoke",
            "fail",
            "PowerShell was not found",
            "Windows PowerShell または PowerShell 7 が使える環境で実行してください。",
        )
    try:
        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-SourceDir",
                str(project_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return PreflightItem(
            "install smoke",
            "fail",
            str(exc),
            "インストール/アンインストールのスモークテスト結果を確認してください。",
        )
    output = (result.stdout or result.stderr or "").strip().splitlines()
    detail = output[-1] if output else f"exit code {result.returncode}"
    if result.returncode != 0:
        return PreflightItem(
            "install smoke",
            "fail",
            detail,
            "scripts\\smoke-install.ps1 を単体実行して詳細を確認してください。",
        )
    return PreflightItem("install smoke", "pass", detail)


def _gui_smoke_item(project_dir: Path) -> PreflightItem:
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "auto_note",
                "gui",
                "--project-dir",
                str(project_dir),
                "--smoke",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return PreflightItem(
            "gui smoke",
            "fail",
            str(exc),
            "`auto-note gui --project-dir . --smoke` を単体実行してGUI初期化エラーを確認してください。",
        )
    output = (result.stdout or result.stderr or "").strip().splitlines()
    detail = output[-1] if output else f"exit code {result.returncode}"
    if result.returncode != 0:
        return PreflightItem(
            "gui smoke",
            "fail",
            detail,
            "`auto-note gui --project-dir . --smoke` を単体実行してGUI初期化エラーを確認してください。",
        )
    return PreflightItem("gui smoke", "pass", detail)


def _overall_status(items: list[PreflightItem]) -> str:
    if any(item.status == "fail" for item in items):
        return "fail"
    if any(item.status == "warn" for item in items):
        return "warn"
    return "pass"


def _troubleshoot_detail(primary_items, warning_items) -> str:
    if primary_items:
        names = ", ".join(item.name for item in primary_items[:3])
        extra = "" if len(primary_items) <= 3 else ", ..."
        return f"{len(primary_items)} issue(s): {names}{extra}"
    if warning_items:
        names = ", ".join(item.name for item in warning_items[:3])
        extra = "" if len(warning_items) <= 3 else ", ..."
        return f"{len(warning_items)} maintenance warning(s): {names}{extra}"
    return "0 issue(s)"
