from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex

from .action_plan import ActionPlanReport, build_action_plan
from .privacy_actions import privacy_failed_cleanup_target
from .quickstart import QuickstartReport, run_quickstart
from .selftest import SelfTestReport, list_self_test_reports, run_self_test
from .support import (
    SUPPORT_BUNDLE_FRESHNESS_WARNING_HOURS,
    is_support_bundle_stale,
    list_support_bundles,
    verify_support_bundle,
)


CONTENT_POLISH_ACTION_TITLES = {
    "公開前チェックを直す",
    "記事レビューで仕上げる",
    "記事の仕上げ項目を確認する",
    "投稿キューの先頭記事を直す",
    "投稿キューの確認項目を見る",
}


@dataclass(frozen=True)
class FirstRunItem:
    name: str
    status: str
    detail: str
    action: str = ""
    gui: str = ""
    command: str = ""


@dataclass(frozen=True)
class FirstRunReport:
    project_dir: Path
    status: str
    score: int
    self_test_score: int
    quickstart_score: int
    items: list[FirstRunItem]
    self_test: SelfTestReport | None = None

    @property
    def ok(self) -> bool:
        return self.status != "fail"

    @property
    def has_warnings(self) -> bool:
        return any(item.status == "warn" for item in self.items)


def run_first_run_checklist(
    project_dir: Path,
    *,
    create: bool = False,
    gui_smoke: bool = False,
    smoke_helper: bool = False,
    include_sales_handoffs: bool = True,
) -> FirstRunReport:
    project_dir = project_dir.resolve()
    self_test = run_self_test(
        project_dir,
        create=create,
        gui_smoke=gui_smoke,
        include_sales_handoffs=include_sales_handoffs,
    )
    quickstart = run_quickstart(project_dir, smoke_helper=smoke_helper)
    action_plan = build_action_plan(project_dir, quickstart=quickstart)
    items = [
        _setup_item(self_test),
        _self_test_item(self_test),
        _display_readability_item(self_test, gui_smoke=gui_smoke),
        _self_test_report_item(project_dir),
        _first_article_item(quickstart),
        _posting_helper_item(quickstart),
        _backup_item(quickstart),
        _support_bundle_item(project_dir),
        _note_login_item(quickstart),
        _top_action_item(action_plan),
    ]
    return FirstRunReport(
        project_dir=project_dir,
        status=_overall_status(items),
        score=_score(items),
        self_test_score=self_test.score,
        quickstart_score=quickstart.score,
        items=items,
        self_test=self_test,
    )


def format_first_run_report(report: FirstRunReport) -> str:
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
        "First-run checklist / 初回チェック",
        f"Verdict: {verdict}",
        f"Score: {report.score}/100",
        f"Self-test: {report.self_test_score}/100",
        f"Quickstart: {report.quickstart_score}/100",
        f"Items: {counts['pass']} OK, {counts['info']} INFO, {counts['warn']} WARN, {counts['fail']} NG",
        "",
    ]
    next_actions: list[tuple[str, str, str]] = []
    for index, item in enumerate(report.items, start=1):
        label = {"pass": "OK", "info": "INFO", "warn": "WARN", "fail": "NG"}.get(
            item.status,
            item.status.upper(),
        )
        lines.append(f"[{label}] {index}. {item.name}: {item.detail}")
        if item.action:
            lines.append(f"  next: {item.action}")
            next_actions.append((item.name, item.command or item.action, item.gui))
        if item.gui:
            lines.append(f"  gui: {item.gui}")
        if item.command:
            lines.append(f"  cli: {item.command}")
    if next_actions:
        lines.extend(["", "Next actions"])
        lines.extend(_format_next_actions(next_actions))
    return "\n".join(lines)


def _format_next_actions(actions: list[tuple[str, str, str]]) -> list[str]:
    grouped: dict[str, list[str]] = {}
    gui_targets: dict[str, list[str]] = {}
    ordered_actions: list[str] = []
    for name, action, gui in actions:
        action_key = _next_action_key(action)
        if not action_key:
            continue
        contained_by = next((existing for existing in ordered_actions if _action_subsumes(existing, action_key)), "")
        if contained_by:
            _append_unique(grouped[contained_by], name)
            _append_unique_gui(gui_targets[contained_by], gui)
            continue
        contained_actions = [existing for existing in ordered_actions if _action_subsumes(action_key, existing)]
        if contained_actions:
            insert_at = min(ordered_actions.index(existing) for existing in contained_actions)
            titles: list[str] = []
            guis: list[str] = []
            for existing in contained_actions:
                for existing_title in grouped.pop(existing):
                    _append_unique(titles, existing_title)
                for existing_gui in gui_targets.pop(existing, []):
                    _append_unique_gui(guis, existing_gui)
                ordered_actions.remove(existing)
            ordered_actions.insert(insert_at, action_key)
            grouped[action_key] = titles
            gui_targets[action_key] = guis
            _append_unique(grouped[action_key], name)
            _append_unique_gui(gui_targets[action_key], gui)
            continue
        if action_key not in grouped:
            grouped[action_key] = []
            gui_targets[action_key] = []
            ordered_actions.append(action_key)
        _append_unique(grouped[action_key], name)
        _append_unique_gui(gui_targets[action_key], gui)
    return [
        f"- {' / '.join(grouped[action])}: {action}{_next_action_gui_suffix(gui_targets[action])}"
        for action in ordered_actions
    ]


def _next_action_gui_suffix(gui_targets: list[str]) -> str:
    if not gui_targets:
        return ""
    return f" / GUI: {' / '.join(gui_targets)}"


def _next_action_key(action: str) -> str:
    command = _first_backticked_command(action)
    return command or action.strip()


def _first_backticked_command(action: str) -> str:
    for index, segment in enumerate(action.split("`")):
        if index % 2 == 0:
            continue
        command = segment.strip()
        if command.startswith("auto-note "):
            return command
    return ""


def _action_subsumes(candidate: str, action: str) -> bool:
    candidate_tokens = _action_tokens(candidate)
    action_tokens = _action_tokens(action)
    if not candidate_tokens or not action_tokens:
        return candidate == action
    if _action_command_prefix(candidate_tokens) != _action_command_prefix(action_tokens):
        return False
    return set(action_tokens).issubset(set(candidate_tokens))


def _action_command_prefix(tokens: tuple[str, ...]) -> tuple[str, ...]:
    return tokens[:2] if len(tokens) >= 2 else tokens


def _action_tokens(action: str) -> tuple[str, ...]:
    try:
        return tuple(shlex.split(action))
    except ValueError:
        return tuple(action.split())


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _append_unique_gui(values: list[str], value: str) -> None:
    if value:
        _append_unique(values, value)


def has_first_run_blockers(report: FirstRunReport, *, strict: bool = False) -> bool:
    if report.status == "fail":
        return True
    return strict and report.status == "warn"


def _setup_item(self_test: SelfTestReport) -> FirstRunItem:
    setup = _self_test_item_by_name(self_test, "setup")
    if setup is None:
        return FirstRunItem("セットアップ", "fail", "setup check not available")
    if setup.status == "fail":
        return FirstRunItem(
            "セットアップ",
            "fail",
            setup.detail,
            "不足している基本ファイルを作成または確認してください。",
            "ヘッダー > セットアップ",
            "auto-note setup --project-dir . --create",
        )
    if setup.status == "warn":
        return FirstRunItem(
            "セットアップ",
            "warn",
            setup.detail,
            "任意機能が必要な場合はセットアップ確認のWARNを確認してください。",
            "診断 > セットアップ確認",
            "auto-note setup --project-dir . --create",
        )
    return FirstRunItem("セットアップ", "pass", setup.detail)


def _self_test_item(self_test: SelfTestReport) -> FirstRunItem:
    issue = None
    status = "pass" if self_test.status == "pass" else self_test.status
    if self_test.status == "fail":
        issue = _first_report_issue(self_test.items, "fail")
        detail = _score_issue_detail(self_test.score, issue, "NG")
        action = _issue_action(issue, "NG項目を確認し、基本動作の失敗を先に解消してください。")
    elif self_test.status == "warn":
        issue = _first_report_issue(self_test.items, "warn")
        detail = _score_issue_detail(self_test.score, issue, "WARN")
        action = _issue_action(issue, "WARN項目を確認し、投稿前に不足を潰してください。")
    else:
        detail = f"{self_test.score}/100"
        action = ""
    gui, command = _issue_target(
        issue,
        default_gui="診断 > セルフテスト",
        default_command="auto-note self-test --project-dir .",
    )
    return FirstRunItem(
        "セルフテスト",
        status,
        detail,
        action,
        gui,
        command,
    )


def _display_readability_item(self_test: SelfTestReport, *, gui_smoke: bool) -> FirstRunItem:
    item = _self_test_item_by_name(self_test, "gui smoke")
    if item is None:
        return FirstRunItem(
            "表示の読みやすさ",
            "info",
            "not available" if gui_smoke else "not run in this report",
            "文字つぶれやボタン文字の収まりを確認する場合はGUI smoke付きで実行してください。",
            "診断 > 表示診断 / ヘッダー > 表示",
            "auto-note first-run --project-dir . --gui-smoke",
        )
    if item.status == "fail":
        return FirstRunItem(
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
        return FirstRunItem("表示の読みやすさ", "pass", detail)
    detail = (
        f"readability {readability or 'unknown'}, "
        f"button labels {button_fit or 'unknown'}"
    )
    return FirstRunItem(
        "表示の読みやすさ",
        "warn",
        detail,
        "文字や行高が潰れる場合は大きめ表示で開き、表示診断コピーを添えて相談してください。",
        "ヘッダー > 表示 > 大きめ / 診断 > 表示診断コピー",
        "auto-note gui --project-dir . --safe-display",
    )


def _self_test_report_item(project_dir: Path) -> FirstRunItem:
    reports = list_self_test_reports(project_dir)
    if reports:
        return FirstRunItem("セルフテスト保存", "pass", reports[0].name)
    return FirstRunItem(
        "セルフテスト保存",
        "warn",
        "not saved yet",
        "サポートへ状況を渡せるよう、セルフテスト結果を保存してください。",
        "診断 > セルフテスト保存",
        "auto-note self-test --project-dir . --report",
    )


def _first_article_item(quickstart: QuickstartReport) -> FirstRunItem:
    item = _quickstart_item_by_name(quickstart, "first article")
    if item is None:
        return FirstRunItem("最初の記事", "warn", "not checked")
    if item.status == "pass":
        return FirstRunItem("最初の記事", "pass", _article_count_detail(item.detail))
    return FirstRunItem(
        "最初の記事",
        "warn",
        item.detail,
        item.action or "スターター一式、練習記事、または新規記事を作成してください。",
        "ホーム > スターター一式",
        "auto-note starter-pack --project-dir .",
    )


def _posting_helper_item(quickstart: QuickstartReport) -> FirstRunItem:
    item = _quickstart_item_by_name(quickstart, "posting helper")
    if item is None:
        return FirstRunItem("投稿ヘルパー", "info", "not checked")
    status = item.status if item.status in {"pass", "fail"} else "info"
    return FirstRunItem(
        "投稿ヘルパー",
        status,
        _posting_helper_detail(item.detail),
        item.action,
        "記事 > 投稿ヘルパー",
        "auto-note quickstart --project-dir . --smoke-helper",
    )


def _backup_item(quickstart: QuickstartReport) -> FirstRunItem:
    item = _quickstart_item_by_name(quickstart, "backup")
    if item is None:
        return FirstRunItem("バックアップ", "warn", "not checked")
    if item.status == "pass":
        return FirstRunItem("バックアップ", "pass", item.detail)
    return FirstRunItem(
        "バックアップ",
        "warn",
        item.detail,
        item.action or "初回設定後にバックアップを作成してください。",
        "ホーム > バックアップ作成",
        "auto-note backup --project-dir .",
    )


def _support_bundle_item(project_dir: Path) -> FirstRunItem:
    bundles = list_support_bundles(project_dir)
    if not bundles:
        return FirstRunItem(
            "問い合わせ一式",
            "info",
            "not created yet",
            "困った時の送付物として、問い合わせ一式ZIPを作れる場所だけ把握してください。",
            "ヘルプ > 問い合わせ一式",
            "auto-note support --project-dir . --bundle",
        )
    latest = bundles[0]
    errors = verify_support_bundle(latest)
    if errors:
        return FirstRunItem(
            "問い合わせ一式",
            "warn",
            f"{latest.name}: {len(errors)} verification error(s)",
            "問い合わせ一式ZIPを作り直してください。",
            "ヘルプ > 問い合わせ一式",
            "auto-note support --project-dir . --bundle",
        )
    if is_support_bundle_stale(latest):
        return FirstRunItem(
            "問い合わせ一式",
            "warn",
            f"{latest.name}: verified but older than {SUPPORT_BUNDLE_FRESHNESS_WARNING_HOURS}h",
            "送付する直前に最新の問い合わせ一式ZIPを作り直してください。",
            "ヘルプ > 問い合わせ一式",
            "auto-note support --project-dir . --bundle",
        )
    return FirstRunItem(
        "問い合わせ一式",
        "pass",
        f"{latest.name} verified; open SUPPORT_SEND_CHECKLIST.txt before sending",
    )


def _note_login_item(quickstart: QuickstartReport) -> FirstRunItem:
    item = _quickstart_item_by_name(quickstart, "note login")
    return FirstRunItem(
        "noteログイン",
        "info",
        item.detail if item else "login state is checked in the normal browser",
        item.action
        if item
        else "GUIのログイン安全ガイドを確認し、普段使うブラウザで note.com にログインしてください。",
        "ホーム > ログイン安全ガイド / ヘッダー > noteログイン",
        "auto-note login --default-browser",
    )


def _top_action_item(action_plan: ActionPlanReport) -> FirstRunItem:
    top = action_plan.steps[0] if action_plan.steps else None
    if top is None:
        return FirstRunItem("次の一手", "pass", action_plan.status)
    status = "warn" if top.severity in {"blocker", "warning", "maintenance"} else "info"
    if status == "warn" and (_is_content_polish_action(top) or _is_commercial_setup_action(top)):
        status = "info"
    return FirstRunItem(
        "次の一手",
        status,
        f"{action_plan.status}, top: {top.title}",
        top.action,
        top.gui,
        top.command,
    )


def _is_content_polish_action(step) -> bool:
    return step.title in CONTENT_POLISH_ACTION_TITLES


def _is_commercial_setup_action(step) -> bool:
    return step.source == "commercial_setup"


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


def _issue_target(issue, *, default_gui: str, default_command: str) -> tuple[str, str]:
    action = getattr(issue, "action", "") or ""
    if getattr(issue, "name", "") == "privacy audit" and "--privacy-failed" in action:
        return privacy_failed_cleanup_target(action)
    return default_gui, default_command


def _self_test_item_by_name(report: SelfTestReport, name: str):
    for item in report.items:
        if item.name == name:
            return item
    return None


def _quickstart_item_by_name(report: QuickstartReport, name: str):
    for item in report.items:
        if item.name == name:
            return item
    return None


def _gui_smoke_metric(detail: str, name: str) -> str:
    marker = f"{name}="
    for part in detail.split(", "):
        if part.startswith(marker):
            return part.split("=", 1)[1].strip()
    return ""


def _article_count_detail(detail: str) -> str:
    marker = " article(s)"
    if marker in detail:
        count = detail.split(marker, 1)[0].strip()
        if count.isdigit():
            return f"{count} article(s), latest article ready"
    return "article ready"


def _posting_helper_detail(detail: str) -> str:
    if detail.startswith("ready for "):
        return "ready for latest article"
    if detail.startswith("generated "):
        return "helper HTML generated"
    return detail


def _overall_status(items: list[FirstRunItem]) -> str:
    if any(item.status == "fail" for item in items):
        return "fail"
    if any(item.status == "warn" for item in items):
        return "warn"
    return "pass"


def _score(items: list[FirstRunItem]) -> int:
    if not items:
        return 0
    value = 0.0
    for item in items:
        if item.status in {"pass", "info"}:
            value += 1.0
        elif item.status == "warn":
            value += 0.55
    return max(0, min(100, round(100 * value / len(items))))
