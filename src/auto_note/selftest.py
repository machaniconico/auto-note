from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import subprocess
import sys

from .action_plan import build_action_plan
from .paths import unique_path
from .privacy import run_privacy_audit
from .quickstart import ESSENTIAL_SETUP_ITEMS, QuickstartReport, run_quickstart
from .release import list_releases, verify_release_package
from .setup_check import run_setup_check


CONTENT_POLISH_QUICKSTART_ITEMS = {"article check", "article review"}


@dataclass(frozen=True)
class SelfTestItem:
    name: str
    status: str
    detail: str
    action: str = ""


@dataclass(frozen=True)
class SelfTestReport:
    project_dir: Path
    status: str
    score: int
    generated_at: datetime
    items: list[SelfTestItem]

    @property
    def ok(self) -> bool:
        return self.status != "fail"

    @property
    def has_warnings(self) -> bool:
        return any(item.status == "warn" for item in self.items)


def run_self_test(
    project_dir: Path,
    *,
    create: bool = False,
    gui_smoke: bool = False,
    include_sales_handoffs: bool = True,
) -> SelfTestReport:
    project_dir = project_dir.resolve()
    items = [
        _setup_item(project_dir, create=create),
        _quickstart_item(project_dir),
        _action_plan_item(project_dir),
        _privacy_item(project_dir, include_sales_handoffs=include_sales_handoffs),
        _release_item(project_dir),
    ]
    if gui_smoke:
        items.append(_gui_smoke_item(project_dir))
    return SelfTestReport(
        project_dir=project_dir,
        status=_overall_status(items),
        score=_score(items),
        generated_at=datetime.now(),
        items=items,
    )


def format_self_test_report(report: SelfTestReport) -> str:
    counts = {
        "pass": sum(1 for item in report.items if item.status == "pass"),
        "info": sum(1 for item in report.items if item.status == "info"),
        "warn": sum(1 for item in report.items if item.status == "warn"),
        "fail": sum(1 for item in report.items if item.status == "fail"),
    }
    verdict = {
        "pass": "READY",
        "warn": "CHECK",
        "fail": "BLOCKED",
    }.get(report.status, report.status.upper())
    lines = [
        "Self-test report / セルフテスト",
        f"Generated: {report.generated_at:%Y-%m-%d %H:%M:%S}",
        f"Verdict: {verdict}",
        f"Score: {report.score}/100",
        f"Items: {counts['pass']} OK, {counts['info']} INFO, {counts['warn']} WARN, {counts['fail']} NG",
        "",
    ]
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


def write_self_test_report(
    project_dir: Path,
    *,
    create: bool = False,
    gui_smoke: bool = False,
    include_sales_handoffs: bool = True,
    report: SelfTestReport | None = None,
) -> Path:
    project_dir = project_dir.resolve()
    report = report or run_self_test(
        project_dir,
        create=create,
        gui_smoke=gui_smoke,
        include_sales_handoffs=include_sales_handoffs,
    )
    reports_dir = project_dir / ".auto-note" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(reports_dir / f"self-test-{report.generated_at:%Y%m%d-%H%M%S}.txt")
    path.write_text(format_self_test_report(report) + "\n", encoding="utf-8")
    return path


def list_self_test_reports(project_dir: Path) -> list[Path]:
    reports_dir = project_dir / ".auto-note" / "reports"
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("self-test-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def has_self_test_blockers(report: SelfTestReport, *, strict: bool = False) -> bool:
    if report.status == "fail":
        return True
    return strict and report.status == "warn"


def _setup_item(project_dir: Path, *, create: bool) -> SelfTestItem:
    checks = run_setup_check(project_dir, create=create)
    missing = [item.name for item in checks if not item.ok]
    missing_essential = [name for name in missing if name in ESSENTIAL_SETUP_ITEMS]
    if missing_essential:
        return SelfTestItem(
            "setup",
            "fail",
            f"missing: {', '.join(missing_essential)}",
            "`auto-note setup --project-dir . --create` を実行してください。",
        )
    if missing:
        return SelfTestItem(
            "setup",
            "warn",
            f"optional missing: {', '.join(missing)}",
            "任意機能が必要な場合はセットアップ確認のWARNを確認してください。",
        )
    return SelfTestItem("setup", "pass", f"{len(checks)} setup check(s) OK")


def _quickstart_item(project_dir: Path) -> SelfTestItem:
    return _self_test_quickstart_item(run_quickstart(project_dir))


def _self_test_quickstart_item(report: QuickstartReport) -> SelfTestItem:
    if not report.ok:
        failures = sum(1 for item in report.items if item.status == "fail")
        return SelfTestItem(
            "quickstart",
            "fail",
            f"{report.score}/100, {failures} failure(s)",
            "`auto-note quickstart --project-dir .` のNG項目を確認してください。",
        )
    if report.has_warnings:
        warning_items = [item for item in report.items if item.status == "warn"]
        warnings = len(warning_items)
        if all(item.name in CONTENT_POLISH_QUICKSTART_ITEMS for item in warning_items):
            return SelfTestItem(
                "quickstart",
                "info",
                f"{report.score}/100, {warnings} content polish warning(s)",
                "記事の仕上げは投稿前にチェック/レビューで確認してください。",
            )
        return SelfTestItem(
            "quickstart",
            "warn",
            f"{report.score}/100, {warnings} warning(s)",
            "GUIのホームまたは `auto-note action-plan --project-dir .` で次の操作を確認してください。",
        )
    return SelfTestItem("quickstart", "pass", f"{report.score}/100")


def _action_plan_item(project_dir: Path) -> SelfTestItem:
    report = build_action_plan(project_dir, limit=3)
    top = report.steps[0] if report.steps else None
    detail = report.status if top is None else f"{report.status}, top: {top.title}"
    if report.status == "BLOCKED":
        return SelfTestItem("action plan", "warn", detail, top.action if top else "")
    if report.status == "NEEDS ATTENTION":
        return SelfTestItem("action plan", "info", detail, top.action if top else "")
    return SelfTestItem("action plan", "pass", detail)


def _privacy_item(project_dir: Path, *, include_sales_handoffs: bool = True) -> SelfTestItem:
    report = run_privacy_audit(project_dir, include_sales_handoffs=include_sales_handoffs)
    failures = sum(1 for item in report.items if item.status == "fail")
    warnings = sum(1 for item in report.items if item.status == "warn")
    passes = sum(1 for item in report.items if item.status == "pass")
    if failures:
        return SelfTestItem(
            "privacy audit",
            "fail",
            f"{failures} failure(s), {passes} artifact(s) OK",
            "`auto-note privacy-audit --project-dir .` のNG項目を確認してください。",
        )
    if warnings:
        return SelfTestItem(
            "privacy audit",
            "warn",
            f"{warnings} warning(s), {passes} artifact(s) OK",
            "`auto-note privacy-audit --project-dir .` の警告を確認してください。",
        )
    return SelfTestItem("privacy audit", "pass", f"{passes} artifact(s) OK")


def _release_item(project_dir: Path) -> SelfTestItem:
    releases = list_releases(project_dir)
    if not releases:
        return SelfTestItem(
            "release package",
            "info",
            "no local release zip found",
            "配布元なら `auto-note preflight --project-dir . --create-release` で作成できます。",
        )
    latest = releases[0]
    errors = verify_release_package(latest)
    if errors:
        return SelfTestItem(
            "release package",
            "fail",
            f"{latest.name}: {len(errors)} verification error(s)",
            "`auto-note release --verify <zip>` の結果を確認してください。",
        )
    return SelfTestItem("release package", "pass", f"{latest.name} verified")


def _gui_smoke_item(project_dir: Path) -> SelfTestItem:
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
        return SelfTestItem(
            "gui smoke",
            "fail",
            str(exc),
            "`auto-note gui --project-dir . --smoke` を単体実行して確認してください。",
        )
    output = (result.stdout or result.stderr or "").strip().splitlines()
    detail = output[-1] if output else f"exit code {result.returncode}"
    if result.returncode != 0:
        return SelfTestItem(
            "gui smoke",
            "fail",
            detail,
            "`auto-note gui --project-dir . --smoke` を単体実行して確認してください。",
        )
    return SelfTestItem("gui smoke", "pass", detail)


def _overall_status(items: list[SelfTestItem]) -> str:
    if any(item.status == "fail" for item in items):
        return "fail"
    if any(item.status == "warn" for item in items):
        return "warn"
    return "pass"


def _score(items: list[SelfTestItem]) -> int:
    if not items:
        return 0
    value = 0.0
    for item in items:
        if item.status in {"pass", "info"}:
            value += 1.0
        elif item.status == "warn":
            value += 0.6
    return max(0, min(100, round(100 * value / len(items))))
