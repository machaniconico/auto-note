from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shlex
import zipfile

from .commercial_setup import (
    COMMERCIAL_SETUP_APPLY_GUI,
    COMMERCIAL_SETUP_REVIEW_GUI,
    COMMERCIAL_SETUP_TEMPLATE_GUI,
)
from .paths import unique_path


@dataclass(frozen=True)
class CommercialReadinessItem:
    name: str
    status: str
    detail: str
    action: str = ""


@dataclass(frozen=True)
class CommercialReadinessReport:
    project_dir: Path
    status: str
    score: int
    generated_at: datetime
    items: list[CommercialReadinessItem]

    @property
    def ok(self) -> bool:
        return self.status != "fail"

    @property
    def has_warnings(self) -> bool:
        return any(item.status == "warn" for item in self.items)


REQUIRED_COMMERCIAL_DOCS = (
    "README.md",
    "docs/INSTALL.md",
    "docs/QUICKSTART.md",
    "docs/SUPPORT.md",
    "docs/PRIVACY.md",
    "docs/TERMS_DRAFT.md",
    "docs/COMMERCIAL_POLICY_DRAFT.md",
    "docs/THIRD_PARTY_NOTICES.md",
    "docs/CHANGELOG.md",
    "docs/RELEASE_CHECKLIST.md",
)


DRAFT_MARKERS = (
    "Draft",
    "ドラフト",
    "販売前レビュー",
    "最終確認",
    "方針案",
    "ライセンス案",
    "返金方針案",
    "サポート方針案",
)

_COMMERCIAL_SETUP_TEMPLATE_COMMAND = "auto-note commercial-setup --project-dir . --template"
_COMMERCIAL_SETUP_APPLY_LATEST_TEMPLATE_COMMAND = "auto-note commercial-setup --project-dir . --apply-latest-template"
_COMMERCIAL_TERMS_REVIEW_COMMAND = "auto-note commercial-setup --project-dir . --terms-reviewed"
_ACCEPTANCE_REPORT_COMMAND = "auto-note acceptance --project-dir . --create --gui-smoke --smoke-helper --report"
_ACCEPTANCE_GUI = "診断 > 受入チェック"
_PREFLIGHT_CREATE_RELEASE_GUI = "診断 > 出荷ZIP作成"
_COMMERCIAL_SETUP_VALUE_OPTIONS = {
    "--project-dir",
    "--seller-name",
    "--sales-url",
    "--refund-url",
    "--support-contact",
}
_COMMERCIAL_SETUP_FLAG_OPTIONS = {"--terms-reviewed", "--support-scope-confirmed"}


def _value(value: str) -> str:
    value = value.strip()
    return value if value else "(not set)"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _commercial_final_review_command(settings) -> str:
    flags: list[str] = []
    if not settings.commercial_terms_reviewed:
        flags.append("--terms-reviewed")
    if not settings.commercial_support_scope_confirmed:
        flags.append("--support-scope-confirmed")
    if not flags:
        return ""
    return f"auto-note commercial-setup --project-dir . {' '.join(flags)}"


def _commercial_setup_template_action(project_dir: Path) -> str:
    from .commercial_setup import list_commercial_setup_templates

    templates = list_commercial_setup_templates(project_dir)
    if templates:
        latest = _project_relative_path(templates[0], project_dir)
        return (
            f"最新の販売者テンプレート `{latest}` を編集し、"
            f"`{_COMMERCIAL_SETUP_APPLY_LATEST_TEMPLATE_COMMAND}` で販売者情報を反映してください。"
            f"GUIでは「{COMMERCIAL_SETUP_APPLY_GUI}」を開いてください。"
            f"新しく作る場合は「{COMMERCIAL_SETUP_TEMPLATE_GUI}」または `{_COMMERCIAL_SETUP_TEMPLATE_COMMAND}` を使えます。"
        )
    return (
        f"GUIでは「{COMMERCIAL_SETUP_REVIEW_GUI}」で直接入力するか、"
        f"「{COMMERCIAL_SETUP_TEMPLATE_GUI}」または `{_COMMERCIAL_SETUP_TEMPLATE_COMMAND}` "
        "で販売者情報をまとめて保存してください。"
    )


def _project_relative_path(path: Path, project_dir: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_dir.resolve()))
    except ValueError:
        return path.name


def run_commercial_readiness(project_dir: Path, *, include_sales_handoffs: bool = True) -> CommercialReadinessReport:
    project_dir = project_dir.resolve()
    items = [
        _release_item(project_dir),
        _privacy_item(project_dir, include_sales_handoffs=include_sales_handoffs),
        _acceptance_item(project_dir, include_sales_handoffs=include_sales_handoffs),
        _seller_profile_item(project_dir),
        _commercial_docs_item(project_dir),
        _commercial_policy_item(project_dir),
        _commercial_final_review_item(project_dir),
        _support_contact_item(project_dir),
        _install_smoke_item(project_dir),
    ]
    return CommercialReadinessReport(
        project_dir=project_dir,
        status=_overall_status(items),
        score=_score(items),
        generated_at=datetime.now(),
        items=items,
    )


def format_commercial_readiness_report(report: CommercialReadinessReport) -> str:
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
        "Commercial readiness / 販売準備",
        f"Generated: {report.generated_at:%Y-%m-%d %H:%M:%S}",
        f"Verdict: {verdict}",
        f"Score: {report.score}/100",
        f"Items: {counts['pass']} OK, {counts['info']} INFO, {counts['warn']} WARN, {counts['fail']} NG",
        f"RC target / 販売RC目途: {_commercial_rc_milestone(report.items)}",
        f"RC path / 残り作業: {_commercial_rc_path_summary(report.items)}",
        f"RC checkpoint / 今回の目途: {_commercial_rc_checkpoint(report.items)}",
        "",
    ]
    next_actions: list[tuple[str, str]] = []
    for item in report.items:
        label = {"pass": "OK", "info": "INFO", "warn": "WARN", "fail": "NG"}.get(
            item.status,
            item.status.upper(),
        )
        lines.append(f"[{label}] {item.name}: {item.detail}")
        if item.action:
            lines.append(f"  next: {item.action}")
            next_actions.append((item.name, item.action))
    if next_actions:
        lines.extend(["", "Next actions"])
        lines.extend(_format_next_actions(next_actions))
    return "\n".join(lines)


def _format_next_actions(actions: list[tuple[str, str]]) -> list[str]:
    grouped: dict[str, list[str]] = {}
    ordered_actions: list[str] = []
    for name, action in actions:
        action_key = _next_action_key(action)
        if not action_key:
            continue
        contained_by = next((existing for existing in ordered_actions if _action_subsumes(existing, action_key)), "")
        if contained_by:
            _append_unique(grouped[contained_by], name)
            continue
        contained_actions = [existing for existing in ordered_actions if _action_subsumes(action_key, existing)]
        if contained_actions:
            insert_at = min(ordered_actions.index(existing) for existing in contained_actions)
            titles: list[str] = []
            for existing in contained_actions:
                for existing_title in grouped.pop(existing):
                    _append_unique(titles, existing_title)
                ordered_actions.remove(existing)
            ordered_actions.insert(insert_at, action_key)
            grouped[action_key] = titles
            _append_unique(grouped[action_key], name)
            continue
        if action_key not in grouped:
            grouped[action_key] = []
            ordered_actions.append(action_key)
        _append_unique(grouped[action_key], name)
    return [
        f"- {' / '.join(grouped[action])}: {action}{_next_action_gui_suffix(action)}"
        for action in ordered_actions
    ]


def _next_action_key(action: str) -> str:
    command = _first_backticked_command(action)
    return command or action.strip()


def _next_action_gui_suffix(action: str) -> str:
    gui = _next_action_gui_target(action)
    return f" / GUI: {gui}" if gui else ""


def _next_action_gui_target(action: str) -> str:
    tokens = _action_tokens(action)
    if _action_command_prefix(tokens) == ("auto-note", "cleanup") and "--privacy-failed" in tokens:
        return "診断 > 危険生成物確認"
    if _action_command_prefix(tokens) == ("auto-note", "commercial-setup"):
        if "--apply-latest-template" in tokens or "--apply-template" in tokens:
            return "設定 > テンプレ適用"
        if "--template" in tokens:
            return "設定 > 販売者テンプレ"
        if any(option in tokens for option in _COMMERCIAL_SETUP_FLAG_OPTIONS):
            return "設定 > 販売者情報確認"
        return "設定 > 販売者情報"
    if _action_command_prefix(tokens) == ("auto-note", "preflight"):
        if "--create-release" in tokens:
            return "診断 > 出荷ZIP作成"
        return "診断 > 出荷前チェック"
    if _action_command_prefix(tokens) == ("auto-note", "acceptance"):
        return "診断 > 受入チェック"
    if _action_command_prefix(tokens) == ("auto-note", "release"):
        return "診断 > 出荷前チェック"
    return ""


def _commercial_rc_milestone(items: list[CommercialReadinessItem]) -> str:
    fail_items = [item for item in items if item.status == "fail"]
    warn_items = [item for item in items if item.status == "warn"]
    if fail_items:
        first = fail_items[0]
        return (
            f"BLOCKED: NG {len(fail_items)}件を0件にすると販売RC判定へ進めます"
            f"（先頭: {first.name}）。"
        )
    if warn_items:
        first = warn_items[0]
        return (
            f"NEAR RC: NG 0件、WARN {len(warn_items)}件。"
            f"WARNを確認または保存すればREADYです（先頭: {first.name}）。"
        )
    return "READY: NG 0件、WARN 0件。販売RCとして固定できます。"


def _commercial_rc_path_summary(items: list[CommercialReadinessItem]) -> str:
    fail_count = sum(1 for item in items if item.status == "fail")
    warn_count = sum(1 for item in items if item.status == "warn")
    blocking_actions = [
        (item.name, item.action)
        for item in items
        if item.status in {"fail", "warn"} and item.action
    ]
    action_count = len(_format_next_actions(blocking_actions))
    first_action = _next_action_key(blocking_actions[0][1]) if blocking_actions else ""
    first_suffix = f" / 先頭: {first_action}" if first_action else ""
    if fail_count:
        if action_count:
            return (
                f"BLOCKED: {action_count}作業（NG {fail_count}件 -> WARN {warn_count}件）"
                f"{first_suffix}"
            )
        return f"BLOCKED: NG {fail_count}件、WARN {warn_count}件。詳細項目を確認してください。"
    if warn_count:
        if action_count:
            return f"NEAR RC: {action_count}作業（WARN {warn_count}件）を確認/保存"
        return f"NEAR RC: WARN {warn_count}件。詳細項目を確認してください。"
    return "READY: 必須残件0件。販売前一括チェックで固定できます。"


def _commercial_rc_checkpoint(items: list[CommercialReadinessItem]) -> str:
    fail_count = sum(1 for item in items if item.status == "fail")
    warn_count = sum(1 for item in items if item.status == "warn")
    blocking_actions = [
        (item.name, item.action)
        for item in items
        if item.status in {"fail", "warn"} and item.action
    ]
    first_action = _next_action_key(blocking_actions[0][1]) if blocking_actions else ""
    if fail_count:
        first_target = first_action or "未解消NG"
        return f"{first_target} -> commercial-readiness再判定でNG 0件"
    if warn_count:
        first_target = first_action or "WARN項目"
        return f"{first_target} -> 確認/保存してREADY判定"
    return "auto-note preflight --project-dir . --gui-smoke -> 販売RC固定"


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
    if _action_command_prefix(candidate_tokens) == ("auto-note", "commercial-setup"):
        candidate_options = _commercial_setup_options(candidate)
        action_options = _commercial_setup_options(action)
        if candidate_options is None or action_options is None:
            return candidate == action
        return set(action_options).issubset(set(candidate_options))
    return set(action_tokens).issubset(set(candidate_tokens))


def _commercial_setup_options(command: str) -> list[tuple[str, str | None]] | None:
    tokens = _action_tokens(command)
    if _action_command_prefix(tokens) != ("auto-note", "commercial-setup"):
        return None
    options: list[tuple[str, str | None]] = []
    index = 2
    while index < len(tokens):
        option = tokens[index]
        if option in _COMMERCIAL_SETUP_VALUE_OPTIONS:
            if index + 1 >= len(tokens):
                return None
            options.append((option, tokens[index + 1]))
            index += 2
        elif option in _COMMERCIAL_SETUP_FLAG_OPTIONS:
            options.append((option, None))
            index += 1
        else:
            return None
    return options


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


def write_commercial_readiness_report(
    project_dir: Path,
    *,
    report: CommercialReadinessReport | None = None,
) -> Path:
    project_dir = project_dir.resolve()
    report = report or run_commercial_readiness(project_dir)
    reports_dir = project_dir / ".auto-note" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(reports_dir / f"commercial-readiness-{report.generated_at:%Y%m%d-%H%M%S}.txt")
    path.write_text(format_commercial_readiness_report(report) + "\n", encoding="utf-8")
    return path


def list_commercial_readiness_reports(project_dir: Path) -> list[Path]:
    reports_dir = project_dir / ".auto-note" / "reports"
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("commercial-readiness-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def list_commercial_policy_reviews(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(sales_dir.glob("commercial-policy-review-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def write_commercial_policy_review(project_dir: Path) -> Path:
    project_dir = project_dir.resolve()
    sales_dir = project_dir / ".auto-note" / "sales"
    sales_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(sales_dir / f"commercial-policy-review-{datetime.now():%Y%m%d-%H%M%S}.txt")
    path.write_text(format_commercial_policy_review(project_dir, review_path=path) + "\n", encoding="utf-8")
    return path


def format_commercial_policy_review(project_dir: Path, *, review_path: Path | None = None) -> str:
    from .commercial_setup import commercial_setup_missing_fields, commercial_setup_warnings
    from .settings import load_settings

    project_dir = project_dir.resolve()
    settings = load_settings(project_dir)
    terms_path = project_dir / "docs" / "TERMS_DRAFT.md"
    policy_path = project_dir / "docs" / "COMMERCIAL_POLICY_DRAFT.md"
    terms_text = _read_text(terms_path)
    policy_text = _read_text(policy_path)
    draft_markers = [marker for marker in DRAFT_MARKERS if marker in f"{terms_text}\n{policy_text}"]
    missing = commercial_setup_missing_fields(settings)
    warnings = commercial_setup_warnings(settings)
    generated_at = datetime.now()
    lines = [
        "Commercial policy review / 販売方針レビュー",
        f"Generated: {generated_at:%Y-%m-%d %H:%M:%S}",
        f"Review file: {review_path.name if review_path else '(not saved)'}",
        "",
        "Current seller setup / 現在の販売者設定",
        f"- seller name: {_value(settings.seller_name)}",
        f"- sales page: {_value(settings.sales_channel_url)}",
        f"- refund policy: {_value(settings.refund_policy_url)}",
        f"- support contact: {_value(settings.support_contact)}",
        f"- terms reviewed: {_yes_no(settings.commercial_terms_reviewed)}",
        f"- support scope confirmed: {_yes_no(settings.commercial_support_scope_confirmed)}",
        f"- reviewed at: {_value(settings.commercial_reviewed_at)}",
        "",
        "Policy documents / 方針文書",
        f"- TERMS_DRAFT.md: {'present' if terms_path.exists() else 'missing'}",
        f"- COMMERCIAL_POLICY_DRAFT.md: {'present' if policy_path.exists() else 'missing'}",
        f"- draft markers: {', '.join(draft_markers) if draft_markers else '(none)'}",
        "",
        "Seller final checklist / 販売者最終チェック",
        "[ ] 販売ページに納品物、対応OS、インストール手順、制限事項を書いた",
        "[ ] note公式APIやログイン回避ツールではなく、投稿ヘルパーによる貼り付け運用であることを書いた",
        "[ ] 返金/キャンセル条件と返金方針URLが販売ページ・マーケットプレイス表示と一致している",
        "[ ] ライセンス/利用条件、再配布不可、サポート対象外の範囲を確認した",
        "[ ] サポート範囲、返信目安、問い合わせ時に送ってよい情報/送ってはいけない情報を書いた",
        "[ ] プライバシー監査と購入者送付前チェックの証跡を販売者側に保管した",
        "",
        "Recommended commands / 推奨コマンド",
        "- auto-note commercial-readiness --project-dir . --report",
        "- auto-note commercial-readiness --project-dir . --policy-review",
        "- auto-note sales-finalize --project-dir . --strict --gui-smoke",
        "- auto-note sales-finalize --project-dir . --send-check --send-check-report",
    ]
    if missing:
        lines.extend(["", "Missing setup / 未入力", *[f"- {field}" for field in missing]])
    if warnings:
        lines.extend(["", "Warnings / 確認事項", *[f"- {warning}" for warning in warnings]])
    lines.extend(
        [
            "",
            "Private note / 保管メモ",
            "- このレビューは販売者用の証跡です。購入者向けZIPや問い合わせ一式には添付しません。",
            "- 販売ページを更新したら、このレビューと販売素材を作り直してください。",
        ]
    )
    return "\n".join(lines)


def has_commercial_readiness_blockers(report: CommercialReadinessReport, *, strict: bool = False) -> bool:
    if report.status == "fail":
        return True
    return strict and report.status == "warn"


def _release_item(project_dir: Path) -> CommercialReadinessItem:
    from .release import list_releases, verify_release_package

    releases = list_releases(project_dir)
    if not releases:
        return CommercialReadinessItem(
            "配布ZIP",
            "fail",
            "no release package found",
            "GUIの出荷ZIP作成、または `auto-note preflight --project-dir . --create-release` を実行してください。",
        )
    latest = releases[0]
    try:
        errors = verify_release_package(latest)
    except (OSError, zipfile.BadZipFile) as exc:
        return CommercialReadinessItem(
            "配布ZIP",
            "fail",
            f"{latest.name}: unreadable release package: {exc}",
            "配布ZIP作成が完了してから `auto-note release --verify <zip>` を実行してください。",
        )
    if errors:
        first_error = f": {errors[0]}" if errors else ""
        return CommercialReadinessItem(
            "配布ZIP",
            "fail",
            f"{latest.name}: {len(errors)} verification error(s){first_error}",
            "`auto-note release --verify <zip>` の結果を確認してください。",
        )
    return CommercialReadinessItem("配布ZIP", "pass", f"{latest.name} verified")


def _privacy_item(project_dir: Path, *, include_sales_handoffs: bool = True) -> CommercialReadinessItem:
    from .privacy import run_privacy_audit
    from .privacy_actions import privacy_failed_cleanup_action

    report = run_privacy_audit(project_dir, include_sales_handoffs=include_sales_handoffs)
    if report.status == "fail":
        failures = sum(1 for item in report.items if item.status == "fail")
        return CommercialReadinessItem(
            "プライバシー監査",
            "fail",
            f"{failures} NG artifact(s)",
            privacy_failed_cleanup_action(
                "`auto-note sales-handoff --project-dir .` で販売用一式を作り直してください。",
                include_releases=True,
            ),
        )
    if report.status == "warn":
        warnings = sum(1 for item in report.items if item.status == "warn")
        return CommercialReadinessItem(
            "プライバシー監査",
            "warn",
            f"{warnings} warning(s)",
            "送付前に警告内容を確認してください。",
        )
    return CommercialReadinessItem("プライバシー監査", "pass", f"{len(report.items)} artifact(s) OK")


def _acceptance_item(project_dir: Path, *, include_sales_handoffs: bool = True) -> CommercialReadinessItem:
    from .acceptance import list_acceptance_reports, run_acceptance_check

    reports = list_acceptance_reports(project_dir)
    current = run_acceptance_check(project_dir, include_sales_handoffs=include_sales_handoffs)
    if not current.ok:
        first_issue = next((item for item in current.items if item.status == "fail"), None)
        first_detail = (
            f"; first NG: {first_issue.name}: {first_issue.detail}"
            if first_issue is not None
            else ""
        )
        action = (
            first_issue.action
            if first_issue is not None and first_issue.action
            else (
                f"GUIでは「{_ACCEPTANCE_GUI}」で受入チェックを保存してください。"
                f"`{_ACCEPTANCE_REPORT_COMMAND}` を実行することもできます。"
            )
        )
        return CommercialReadinessItem(
            "受入チェック",
            "fail",
            f"current status {current.status}, saved reports {len(reports)}{first_detail}",
            action,
        )
    if not reports:
        return CommercialReadinessItem(
            "受入チェック",
            "warn",
            f"current status {current.status}, no saved acceptance report",
            f"GUIでは「{_ACCEPTANCE_GUI}」で納品確認を保存してください。"
            f"`{_ACCEPTANCE_REPORT_COMMAND}` を実行することもできます。",
        )
    latest = reports[0]
    if current.has_warnings:
        return CommercialReadinessItem(
            "受入チェック",
            "warn",
            f"current status {current.status}, latest saved {latest.name}",
            f"GUIでは「{_ACCEPTANCE_GUI}」で受入チェックのWARNを確認し、必要に応じて保存し直してください。",
        )
    return CommercialReadinessItem("受入チェック", "pass", f"{latest.name} saved")


def _commercial_docs_item(project_dir: Path) -> CommercialReadinessItem:
    missing = [relative for relative in REQUIRED_COMMERCIAL_DOCS if not (project_dir / relative).exists()]
    if missing:
        return CommercialReadinessItem(
            "販売文書",
            "fail",
            f"{len(missing)} missing: {', '.join(missing[:3])}",
            "README/docs配下の販売前文書を復元してください。",
        )
    return CommercialReadinessItem("販売文書", "pass", f"{len(REQUIRED_COMMERCIAL_DOCS)} document(s) present")


def _commercial_policy_item(project_dir: Path) -> CommercialReadinessItem:
    from .settings import load_settings

    paths = [project_dir / "docs" / "TERMS_DRAFT.md", project_dir / "docs" / "COMMERCIAL_POLICY_DRAFT.md"]
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        return CommercialReadinessItem(
            "利用条件/商用方針",
            "fail",
            f"missing: {', '.join(missing)}",
            "利用条件と商用方針の文書を復元してください。",
        )
    text = "\n".join(_read_text(path) for path in paths)
    markers = [marker for marker in DRAFT_MARKERS if marker in text]
    if markers:
        settings = load_settings(project_dir)
        if settings.commercial_terms_reviewed:
            suffix = f" at {settings.commercial_reviewed_at}" if settings.commercial_reviewed_at else ""
            return CommercialReadinessItem(
                "利用条件/商用方針",
                "pass",
                f"draft markers acknowledged by seller review{suffix}",
            )
        return CommercialReadinessItem(
            "利用条件/商用方針",
            "warn",
            f"draft markers present: {', '.join(markers[:3])}",
            f"販売ページ、決済方法、返金条件、サポート範囲に合わせて文書を最終レビューし、"
            f"GUIでは「{COMMERCIAL_SETUP_REVIEW_GUI}」を開いてください。"
            f"`{_COMMERCIAL_TERMS_REVIEW_COMMAND}` で確認を保存することもできます。",
        )
    return CommercialReadinessItem("利用条件/商用方針", "pass", "no draft markers found")


def _seller_profile_item(project_dir: Path) -> CommercialReadinessItem:
    from .commercial_setup import commercial_setup_warnings
    from .settings import load_settings

    settings = load_settings(project_dir)
    missing: list[str] = []
    if not settings.seller_name.strip():
        missing.append("seller name")
    if not settings.sales_channel_url.strip():
        missing.append("sales page")
    if not settings.refund_policy_url.strip():
        missing.append("refund policy")
    if missing:
        return CommercialReadinessItem(
            "販売者プロフィール",
            "warn",
            f"missing: {', '.join(missing)}",
            _commercial_setup_template_action(project_dir),
        )
    warnings = commercial_setup_warnings(settings)
    if warnings:
        return CommercialReadinessItem(
            "販売者プロフィール",
            "warn",
            f"warnings: {', '.join(warnings)}",
            f"販売ページURL、返金方針URL、サポート連絡先を公開URL形式で保存してください。"
            f"{_commercial_setup_template_action(project_dir)}",
        )
    return CommercialReadinessItem("販売者プロフィール", "pass", "seller profile is set")


def _commercial_final_review_item(project_dir: Path) -> CommercialReadinessItem:
    from .settings import load_settings

    settings = load_settings(project_dir)
    missing: list[str] = []
    if not settings.commercial_terms_reviewed:
        missing.append("terms review")
    if not settings.commercial_support_scope_confirmed:
        missing.append("support scope")
    if missing:
        command = _commercial_final_review_command(settings)
        return CommercialReadinessItem(
            "販売最終確認",
            "warn",
            f"missing: {', '.join(missing)}",
            f"販売ページ、利用条件、返金条件、サポート範囲を確認し、"
            f"GUIでは「{COMMERCIAL_SETUP_REVIEW_GUI}」を開いてください。"
            f"`{command}` で最終確認を保存することもできます。",
        )
    suffix = f" at {settings.commercial_reviewed_at}" if settings.commercial_reviewed_at else ""
    return CommercialReadinessItem("販売最終確認", "pass", f"seller review confirmed{suffix}")


def _support_contact_item(project_dir: Path) -> CommercialReadinessItem:
    from .commercial_setup import commercial_setup_warnings
    from .settings import load_settings

    settings = load_settings(project_dir)
    support_warnings = [warning for warning in commercial_setup_warnings(settings) if warning.startswith("support contact")]
    if settings.support_contact.strip() and not support_warnings:
        return CommercialReadinessItem("サポート連絡先", "pass", "support contact is set")
    if support_warnings:
        return CommercialReadinessItem(
            "サポート連絡先",
            "warn",
            "; ".join(support_warnings),
            f"販売素材にそのまま載せられる公開サポートURLを設定してください。"
            f"{_commercial_setup_template_action(project_dir)}",
        )
    return CommercialReadinessItem(
        "サポート連絡先",
        "warn",
        "support contact is not set",
        f"GUIでは「{COMMERCIAL_SETUP_REVIEW_GUI}」でサポート連絡先を設定し、"
        "販売ページにも問い合わせ方法を明記してください。"
        f"{_commercial_setup_template_action(project_dir)}",
    )


def _install_smoke_item(project_dir: Path) -> CommercialReadinessItem:
    script = project_dir / "scripts" / "smoke-install.ps1"
    if not script.exists():
        return CommercialReadinessItem(
            "インストール導線",
            "fail",
            "scripts/smoke-install.ps1 not found",
            "インストール/アンインストール検証スクリプトを復元してください。",
        )
    return CommercialReadinessItem(
        "インストール導線",
        "info",
        "local smoke script is present",
        f"販売直前は、GUIでは「{_PREFLIGHT_CREATE_RELEASE_GUI}」を開き、"
        "`auto-note preflight --project-dir . --create-release --install-smoke --gui-smoke` "
        "と実機確認を実行してください。",
    )


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _overall_status(items: list[CommercialReadinessItem]) -> str:
    if any(item.status == "fail" for item in items):
        return "fail"
    if any(item.status == "warn" for item in items):
        return "warn"
    return "pass"


def _score(items: list[CommercialReadinessItem]) -> int:
    if not items:
        return 0
    value = 0.0
    for item in items:
        if item.status in {"pass", "info"}:
            value += 1.0
        elif item.status == "warn":
            value += 0.65
    return max(0, min(100, round(100 * value / len(items))))
