from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .first_run import run_first_run_checklist
from .paths import unique_path
from .selftest import run_self_test
from .support import (
    SUPPORT_BUNDLE_FRESHNESS_WARNING_HOURS,
    is_support_bundle_stale,
    list_support_bundles,
    verify_support_bundle,
)
from .troubleshoot import run_troubleshoot


@dataclass(frozen=True)
class AcceptanceItem:
    name: str
    status: str
    detail: str
    action: str = ""
    gui: str = ""
    command: str = ""


@dataclass(frozen=True)
class AcceptanceReport:
    project_dir: Path
    status: str
    score: int
    generated_at: datetime
    items: list[AcceptanceItem]

    @property
    def ok(self) -> bool:
        return self.status != "fail"

    @property
    def has_warnings(self) -> bool:
        return any(item.status == "warn" for item in self.items)


def run_acceptance_check(
    project_dir: Path,
    *,
    create: bool = False,
    gui_smoke: bool = False,
    smoke_helper: bool = False,
    include_sales_handoffs: bool = True,
) -> AcceptanceReport:
    project_dir = project_dir.resolve()
    first_run = run_first_run_checklist(
        project_dir,
        create=create,
        gui_smoke=gui_smoke,
        smoke_helper=smoke_helper,
        include_sales_handoffs=include_sales_handoffs,
    )
    self_test = run_self_test(
        project_dir,
        create=create,
        gui_smoke=gui_smoke,
        include_sales_handoffs=include_sales_handoffs,
    )
    troubleshoot = run_troubleshoot(project_dir, include_sales_handoffs=include_sales_handoffs)
    items = [
        _first_run_item(first_run),
        _self_test_item(self_test),
        _troubleshoot_item(troubleshoot),
        _posting_helper_item(first_run, smoke_helper=smoke_helper),
        _gui_smoke_item(self_test, gui_smoke=gui_smoke),
        _display_readability_item(self_test, gui_smoke=gui_smoke),
        _support_item(project_dir),
    ]
    return AcceptanceReport(
        project_dir=project_dir,
        status=_overall_status(items),
        score=_score(items),
        generated_at=datetime.now(),
        items=items,
    )


def format_acceptance_report(report: AcceptanceReport) -> str:
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
        "Acceptance check / 受入チェック",
        f"Generated: {report.generated_at:%Y-%m-%d %H:%M:%S}",
        f"Verdict: {verdict}",
        f"Score: {report.score}/100",
        f"Items: {counts['pass']} OK, {counts['info']} INFO, {counts['warn']} WARN, {counts['fail']} NG",
        "",
    ]
    next_actions: list[tuple[str, str]] = []
    for index, item in enumerate(report.items, start=1):
        label = {"pass": "OK", "info": "INFO", "warn": "WARN", "fail": "NG"}.get(
            item.status,
            item.status.upper(),
        )
        lines.append(f"[{label}] {index}. {item.name}: {item.detail}")
        if item.action:
            lines.append(f"  next: {item.action}")
            next_actions.append((item.name, item.action))
        if item.gui:
            lines.append(f"  gui: {item.gui}")
        if item.command:
            lines.append(f"  cli: {item.command}")
    if next_actions:
        lines.extend(["", "Next actions"])
        lines.extend(_format_next_actions(next_actions))
    return "\n".join(lines)


def write_acceptance_report(
    project_dir: Path,
    *,
    create: bool = False,
    gui_smoke: bool = False,
    smoke_helper: bool = False,
    include_sales_handoffs: bool = True,
    report: AcceptanceReport | None = None,
) -> Path:
    project_dir = project_dir.resolve()
    report = report or run_acceptance_check(
        project_dir,
        create=create,
        gui_smoke=gui_smoke,
        smoke_helper=smoke_helper,
        include_sales_handoffs=include_sales_handoffs,
    )
    reports_dir = project_dir / ".auto-note" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(reports_dir / f"acceptance-{report.generated_at:%Y%m%d-%H%M%S}.txt")
    path.write_text(format_acceptance_report(report) + "\n", encoding="utf-8")
    return path


def list_acceptance_reports(project_dir: Path) -> list[Path]:
    reports_dir = project_dir / ".auto-note" / "reports"
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("acceptance-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def has_acceptance_blockers(report: AcceptanceReport, *, strict: bool = False) -> bool:
    if report.status == "fail":
        return True
    return strict and report.status == "warn"


def _first_run_item(report) -> AcceptanceItem:
    if report.status == "fail":
        issue = _first_report_issue(report.items, "fail")
        return AcceptanceItem(
            "初回チェック",
            "fail",
            _score_issue_detail(report.score, issue, "NG"),
            _issue_action(issue, "初回チェックのNG項目を先に解消してください。"),
            "初回 > 初回チェック",
            "auto-note first-run --project-dir . --create --gui-smoke --smoke-helper",
        )
    if report.status == "warn":
        issue = _first_report_issue(report.items, "warn")
        return AcceptanceItem(
            "初回チェック",
            "warn",
            _score_issue_detail(report.score, issue, "WARN"),
            _issue_action(issue, "WARN項目を確認し、必要なものだけ先に片付けてください。"),
            "初回 > 初回チェック",
            "auto-note first-run --project-dir . --create --gui-smoke --smoke-helper",
        )
    return AcceptanceItem("初回チェック", "pass", f"{report.score}/100")


def _self_test_item(report) -> AcceptanceItem:
    if report.status == "fail":
        issue = _first_report_issue(report.items, "fail")
        return AcceptanceItem(
            "セルフテスト",
            "fail",
            _score_issue_detail(report.score, issue, "NG"),
            _issue_action(issue, "セルフテストのNG項目を確認してください。"),
            "診断 > セルフテスト",
            "auto-note self-test --project-dir . --create --gui-smoke --report",
        )
    if report.status == "warn":
        issue = _first_report_issue(report.items, "warn")
        return AcceptanceItem(
            "セルフテスト",
            "warn",
            _score_issue_detail(report.score, issue, "WARN"),
            _issue_action(issue, "WARN項目を確認してください。"),
            "診断 > セルフテスト",
            "auto-note self-test --project-dir . --create --gui-smoke --report",
        )
    return AcceptanceItem("セルフテスト", "pass", f"{report.score}/100")


def _troubleshoot_item(report) -> AcceptanceItem:
    failures = [item for item in report.items if item.status == "fail"]
    warnings = [item for item in report.items if item.status == "warn"]
    serious = [item for item in warnings if item.name != "privacy cleanup candidates"]
    if failures:
        issue = failures[0]
        return AcceptanceItem(
            "トラブル診断",
            "fail",
            issue.detail,
            issue.action or "トラブル診断のNG項目を確認してください。",
            "診断 > トラブル診断",
            "auto-note troubleshoot --project-dir .",
        )
    if serious:
        issue = serious[0]
        return AcceptanceItem(
            "トラブル診断",
            "warn",
            issue.detail,
            issue.action or "トラブル診断のWARN項目を確認してください。",
            "診断 > トラブル診断",
            "auto-note troubleshoot --project-dir .",
        )
    if warnings:
        return AcceptanceItem(
            "トラブル診断",
            "info",
            "maintenance warning(s) only",
            warnings[0].action,
            "診断 > トラブル診断",
            "auto-note troubleshoot --project-dir .",
        )
    return AcceptanceItem("トラブル診断", "pass", f"{len(report.items)} item(s) checked")


def _posting_helper_item(first_run, *, smoke_helper: bool) -> AcceptanceItem:
    item = _item_by_name(first_run.items, "投稿ヘルパー")
    if item is None:
        return AcceptanceItem("投稿ヘルパー", "info", "not checked")
    if item.status == "fail":
        return AcceptanceItem(
            "投稿ヘルパー",
            "fail",
            item.detail,
            item.action,
            item.gui,
            item.command,
        )
    if smoke_helper and item.status in {"pass", "info"}:
        return AcceptanceItem("投稿ヘルパー", "pass", item.detail)
    return AcceptanceItem(
        "投稿ヘルパー",
        "info",
        "use --smoke-helper for file generation check" if not smoke_helper else item.detail,
        "投稿ヘルパーHTML生成まで確認する場合は smoke-helper 付きで実行してください。",
        "診断 > ヘルパー生成確認",
        "auto-note acceptance --project-dir . --smoke-helper",
    )


def _gui_smoke_item(self_test, *, gui_smoke: bool) -> AcceptanceItem:
    item = _item_by_name(self_test.items, "gui smoke")
    if item and item.status == "fail":
        return AcceptanceItem(
            "GUI初期化",
            "fail",
            item.detail,
            item.action,
            "診断 > セルフテスト",
            "auto-note acceptance --project-dir . --gui-smoke",
        )
    if item and item.status == "pass":
        return AcceptanceItem("GUI初期化", "pass", item.detail)
    return AcceptanceItem(
        "GUI初期化",
        "info",
        "not run in this report" if not gui_smoke else "not available",
        "GUIを表示せずに起動確認する場合は gui-smoke 付きで実行してください。",
        "診断 > セルフテスト",
        "auto-note acceptance --project-dir . --gui-smoke",
    )


def _display_readability_item(self_test, *, gui_smoke: bool) -> AcceptanceItem:
    item = _item_by_name(self_test.items, "gui smoke")
    if item is None:
        return AcceptanceItem(
            "表示の読みやすさ",
            "info",
            "not available" if gui_smoke else "not run in this report",
            "文字つぶれやボタン文字の収まりを確認する場合は gui-smoke 付きで実行してください。",
            "診断 > 表示診断 / ヘッダー > 表示",
            "auto-note acceptance --project-dir . --gui-smoke",
        )
    if item.status == "fail":
        return AcceptanceItem(
            "表示の読みやすさ",
            "fail",
            item.detail,
            "GUI起動ログを確認し、起動できる状態に戻してから表示診断を確認してください。",
            "診断 > GUIログ表示 / ヘルプ > 問い合わせ一式",
            "auto-note gui --project-dir . --smoke",
        )
    readability = _gui_smoke_metric(item.detail, "display_readability_status")
    button_fit = _gui_smoke_metric(item.detail, "display_button_label_fit_status")
    actual_font = _gui_smoke_metric(item.detail, "display_actual_font_family")
    if readability == "OK" and button_fit == "OK":
        detail = "readability OK, button labels OK"
        if actual_font:
            detail = f"{detail}, font {actual_font}"
        return AcceptanceItem("表示の読みやすさ", "pass", detail)
    detail = (
        f"readability {readability or 'unknown'}, "
        f"button labels {button_fit or 'unknown'}"
    )
    return AcceptanceItem(
        "表示の読みやすさ",
        "warn",
        detail,
        "文字や行高が潰れる場合は大きめ表示で開き、表示診断コピーを添えて相談してください。",
        "ヘッダー > 表示 > 大きめ / 診断 > 表示診断コピー",
        "auto-note gui --project-dir . --safe-display",
    )


def _support_item(project_dir: Path) -> AcceptanceItem:
    bundles = list_support_bundles(project_dir)
    if not bundles:
        return AcceptanceItem(
            "問い合わせ一式",
            "info",
            "not created yet",
            "困った時に作れる場所だけ確認してください。",
            "ヘルプ > 問い合わせ一式",
            "auto-note support --project-dir . --bundle",
        )
    latest = bundles[0]
    errors = verify_support_bundle(latest)
    if errors:
        return AcceptanceItem(
            "問い合わせ一式",
            "warn",
            f"{latest.name}: {len(errors)} verification error(s)",
            "問い合わせ一式ZIPを作り直してください。",
            "ヘルプ > 問い合わせ一式",
            "auto-note support --project-dir . --bundle",
        )
    if is_support_bundle_stale(latest):
        return AcceptanceItem(
            "問い合わせ一式",
            "warn",
            f"{latest.name}: verified but older than {SUPPORT_BUNDLE_FRESHNESS_WARNING_HOURS}h",
            "最新の状況で問い合わせ一式ZIPを作り直してください。",
            "ヘルプ > 問い合わせ一式",
            "auto-note support --project-dir . --bundle",
        )
    return AcceptanceItem(
        "問い合わせ一式",
        "pass",
        f"{latest.name} verified; open SUPPORT_SEND_CHECKLIST.txt before sending",
    )


def _item_by_name(items, name: str):
    for item in items:
        if item.name == name:
            return item
    return None


def _format_next_actions(actions: list[tuple[str, str]]) -> list[str]:
    grouped: dict[str, list[str]] = {}
    ordered_actions: list[str] = []
    for name, action in actions:
        action = action.strip()
        if not action:
            continue
        if action not in grouped:
            grouped[action] = []
            ordered_actions.append(action)
        if name not in grouped[action]:
            grouped[action].append(name)
    return [f"- {' / '.join(grouped[action])}: {action}" for action in ordered_actions]


def _first_report_issue(items, status: str):
    for item in items:
        if item.status == status:
            return item
    return None


def _score_issue_detail(score: int, issue, label: str) -> str:
    detail = f"{score}/100"
    if issue is None:
        return detail
    if f"first {label}:" in issue.detail:
        return f"{detail}; {issue.name}: {issue.detail}"
    return f"{detail}; first {label}: {issue.name}: {issue.detail}"


def _issue_action(issue, fallback: str) -> str:
    if issue is not None and issue.action:
        return issue.action
    return fallback


def _gui_smoke_metric(detail: str, name: str) -> str:
    marker = f"{name}="
    for part in detail.split(", "):
        if part.startswith(marker):
            return part.split("=", 1)[1].strip()
    return ""


def _overall_status(items: list[AcceptanceItem]) -> str:
    if any(item.status == "fail" for item in items):
        return "fail"
    if any(item.status == "warn" for item in items):
        return "warn"
    return "pass"


def _score(items: list[AcceptanceItem]) -> int:
    if not items:
        return 0
    value = 0.0
    for item in items:
        if item.status in {"pass", "info"}:
            value += 1.0
        elif item.status == "warn":
            value += 0.6
    return max(0, min(100, round(100 * value / len(items))))
