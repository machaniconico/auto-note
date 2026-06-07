from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
import zipfile

from .article import ArticleError, load_article
from .diagnostics import list_diagnostic_reports
from .release import list_releases, verify_release_package
from .settings import load_settings
from .support import list_support_bundles, list_support_requests, verify_support_bundle


@dataclass(frozen=True)
class PrivacyAuditItem:
    name: str
    status: str
    detail: str
    action: str = ""
    path: Path | None = None


@dataclass(frozen=True)
class PrivacyAuditReport:
    project_dir: Path
    items: list[PrivacyAuditItem]

    @property
    def status(self) -> str:
        if any(item.status == "fail" for item in self.items):
            return "fail"
        if any(item.status == "warn" for item in self.items):
            return "warn"
        return "pass"

    @property
    def ok(self) -> bool:
        return self.status != "fail"


@dataclass(frozen=True)
class SensitiveValue:
    label: str
    value: str


COMMON_ARTICLE_FILE_NAMES = {
    "article.md",
    "draft.md",
    "note.md",
    "post.md",
    "ready.md",
    "review.md",
    "sample.md",
    "test.md",
    "unfinished.md",
}


def run_privacy_audit(
    project_dir: Path,
    *,
    all_artifacts: bool = False,
    include_sales_handoffs: bool = True,
) -> PrivacyAuditReport:
    project_dir = project_dir.resolve()
    sensitive = _sensitive_values(project_dir)
    items: list[PrivacyAuditItem] = []
    items.extend(_diagnostic_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_self_test_report_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_acceptance_report_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_commercial_readiness_report_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_commercial_policy_review_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_improvement_plan_report_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_overview_report_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_calendar_export_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_publish_queue_report_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_workflow_smoke_report_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_support_request_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_support_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_commercial_setup_template_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_sales_material_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_sales_plan_report_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_sales_finalize_report_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_seller_send_checklist_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_buyer_delivery_message_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_buyer_send_readiness_report_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_seller_delivery_receipt_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_sales_evidence_manifest_items(project_dir, sensitive, all_artifacts=all_artifacts))
    if include_sales_handoffs:
        items.extend(_sales_handoff_items(project_dir, sensitive, all_artifacts=all_artifacts))
        items.extend(_buyer_delivery_package_items(project_dir, sensitive, all_artifacts=all_artifacts))
    items.extend(_release_items(project_dir, sensitive, all_artifacts=all_artifacts))
    return PrivacyAuditReport(project_dir=project_dir, items=items)


def format_privacy_audit_report(report: PrivacyAuditReport) -> str:
    counts = {
        "pass": sum(1 for item in report.items if item.status == "pass"),
        "info": sum(1 for item in report.items if item.status == "info"),
        "warn": sum(1 for item in report.items if item.status == "warn"),
        "fail": sum(1 for item in report.items if item.status == "fail"),
    }
    verdict = {"pass": "OK", "warn": "CHECK", "fail": "BLOCKED"}[report.status]
    lines = [
        "Privacy audit report",
        f"Verdict: {verdict}",
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


def has_privacy_audit_blockers(report: PrivacyAuditReport, *, strict: bool = False) -> bool:
    if report.status == "fail":
        return True
    return strict and report.status == "warn"


def _diagnostic_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    reports = list_diagnostic_reports(project_dir)
    if not reports:
        return [PrivacyAuditItem("diagnostic report privacy", "info", "no diagnostic reports found")]
    selected = reports if all_artifacts else reports[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note diagnose --report` で匿名化済み診断ZIPを作り直してください。"
    )
    return [
        _zip_privacy_item(
            path,
            sensitive,
            name=f"diagnostic report privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _self_test_report_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .selftest import list_self_test_reports

    reports = list_self_test_reports(project_dir)
    if not reports:
        return [PrivacyAuditItem("self-test report privacy", "info", "no self-test reports found")]
    selected = reports if all_artifacts else reports[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note self-test --project-dir . --report` で作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"self-test report privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _workflow_smoke_report_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .workflow_smoke import list_workflow_smoke_reports

    reports = list_workflow_smoke_reports(project_dir)
    if not reports:
        return [PrivacyAuditItem("workflow smoke report privacy", "info", "no workflow smoke reports found")]
    selected = reports if all_artifacts else reports[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note workflow-smoke --project-dir . --report` で作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"workflow smoke report privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _acceptance_report_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .acceptance import list_acceptance_reports

    reports = list_acceptance_reports(project_dir)
    if not reports:
        return [PrivacyAuditItem("acceptance report privacy", "info", "no acceptance reports found")]
    selected = reports if all_artifacts else reports[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note acceptance --project-dir . --report` で作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"acceptance report privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _commercial_readiness_report_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .commercial import list_commercial_readiness_reports

    reports = list_commercial_readiness_reports(project_dir)
    if not reports:
        return [PrivacyAuditItem("commercial readiness report privacy", "info", "no commercial readiness reports found")]
    selected = reports if all_artifacts else reports[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note commercial-readiness --project-dir . --report` で作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"commercial readiness report privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _commercial_policy_review_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .commercial import list_commercial_policy_reviews

    reviews = list_commercial_policy_reviews(project_dir)
    if not reviews:
        return [PrivacyAuditItem("commercial policy review privacy", "info", "no commercial policy reviews found")]
    selected = reviews if all_artifacts else reviews[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note commercial-readiness --project-dir . --policy-review` で方針レビューを作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"commercial policy review privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _commercial_setup_template_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .commercial_setup import list_commercial_setup_templates

    templates = list_commercial_setup_templates(project_dir)
    if not templates:
        return [PrivacyAuditItem("commercial setup template privacy", "info", "no commercial setup templates found")]
    selected = templates if all_artifacts else templates[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note commercial-setup --project-dir . --template` で販売者テンプレートを作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"commercial setup template privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _sales_finalize_report_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .sales_finalize import list_sales_finalize_reports

    reports = list_sales_finalize_reports(project_dir)
    if not reports:
        return [PrivacyAuditItem("sales finalize report privacy", "info", "no sales finalize reports found")]
    selected = reports if all_artifacts else reports[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note sales-finalize --project-dir .` で販売一括レポートを作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"sales finalize report privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _sales_plan_report_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .sales_plan import list_sales_plan_reports

    reports = list_sales_plan_reports(project_dir)
    if not reports:
        return [PrivacyAuditItem("sales plan report privacy", "info", "no sales plan reports found")]
    selected = reports if all_artifacts else reports[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note sales-plan --project-dir . --report` で販売ナビレポートを作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"sales plan report privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _seller_send_checklist_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .sales_finalize import list_seller_send_checklists

    checklists = list_seller_send_checklists(project_dir)
    if not checklists:
        return [PrivacyAuditItem("seller send checklist privacy", "info", "no seller send checklists found")]
    selected = checklists if all_artifacts else checklists[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note sales-finalize --project-dir .` で販売者送付前チェックリストを作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"seller send checklist privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _buyer_delivery_message_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .sales_finalize import list_buyer_delivery_messages

    messages = list_buyer_delivery_messages(project_dir)
    if not messages:
        return [PrivacyAuditItem("buyer delivery message privacy", "info", "no buyer delivery messages found")]
    selected = messages if all_artifacts else messages[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note sales-finalize --project-dir .` で購入者向け送付文を作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"buyer delivery message privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _buyer_send_readiness_report_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .sales_finalize import list_buyer_send_readiness_reports

    reports = list_buyer_send_readiness_reports(project_dir)
    if not reports:
        return [PrivacyAuditItem("buyer send readiness report privacy", "info", "no buyer send readiness reports found")]
    selected = reports if all_artifacts else reports[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note sales-finalize --project-dir . --send-check-report` で購入者送付前チェックレポートを作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"buyer send readiness report privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _seller_delivery_receipt_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .sales_finalize import list_seller_delivery_receipts

    receipts = list_seller_delivery_receipts(project_dir)
    if not receipts:
        return [PrivacyAuditItem("seller delivery receipt privacy", "info", "no seller delivery receipts found")]
    selected = receipts if all_artifacts else receipts[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note sales-finalize --project-dir . --delivery-receipt` で販売者向け納品記録を作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"seller delivery receipt privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _sales_evidence_manifest_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .sales_finalize import list_sales_evidence_manifests

    manifests = list_sales_evidence_manifests(project_dir)
    if not manifests:
        return [PrivacyAuditItem("sales evidence manifest privacy", "info", "no sales evidence manifests found")]
    selected = manifests if all_artifacts else manifests[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note sales-finalize --project-dir .` で販売証跡マニフェストを作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"sales evidence manifest privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _improvement_plan_report_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .improvement_plan import list_improvement_plan_reports

    reports = list_improvement_plan_reports(project_dir)
    if not reports:
        return [PrivacyAuditItem("improvement plan report privacy", "info", "no improvement plan reports found")]
    selected = reports if all_artifacts else reports[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note improve <file> --project-dir . --report` で匿名化済みレポートを作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"improvement plan report privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _publish_queue_report_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .publish_queue import list_publish_queue_reports

    reports = list_publish_queue_reports(project_dir)
    if not reports:
        return [PrivacyAuditItem("publish queue report privacy", "info", "no publish queue reports found")]
    selected = reports if all_artifacts else reports[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note publish-queue --project-dir . --report` で匿名化済みレポートを作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"publish queue report privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _calendar_export_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .workflow import list_calendar_exports

    reports = list_calendar_exports(project_dir)
    if not reports:
        return [PrivacyAuditItem("calendar export privacy", "info", "no calendar exports found")]
    selected = reports if all_artifacts else reports[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note calendar-export --project-dir .` で匿名化済みICSを作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"calendar export privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _overview_report_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .overview import list_overview_reports

    reports = list_overview_reports(project_dir)
    if not reports:
        return [PrivacyAuditItem("overview report privacy", "info", "no overview reports found")]
    selected = reports if all_artifacts else reports[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note overview --project-dir . --report` で匿名化済みレポートを作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"overview report privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _support_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    bundles = list_support_bundles(project_dir)
    if not bundles:
        return [PrivacyAuditItem("support bundle privacy", "info", "no support bundles found")]
    selected = bundles if all_artifacts else bundles[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note support --project-dir . --bundle` で問い合わせ一式を作り直してください。"
    )
    items: list[PrivacyAuditItem] = []
    for path in selected:
        verification_errors = verify_support_bundle(path)
        if verification_errors:
            items.append(
                PrivacyAuditItem(
                    f"support bundle verification: {path.name}",
                    "fail",
                    f"{len(verification_errors)} verification error(s)",
                    action,
                    path,
                )
            )
            continue
        items.append(
            _zip_privacy_item(
                path,
                sensitive,
                name=f"support bundle privacy: {path.name}",
                action=action,
            )
        )
    return items


def _support_request_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    requests = list_support_requests(project_dir)
    if not requests:
        return [PrivacyAuditItem("support request privacy", "info", "no support requests found")]
    selected = requests if all_artifacts else requests[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note support --project-dir .` で問い合わせMarkdownを作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"support request privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _release_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    releases = list_releases(project_dir)
    if not releases:
        return [PrivacyAuditItem("release package privacy", "info", "no release packages found")]
    selected = releases if all_artifacts else releases[:1]
    items: list[PrivacyAuditItem] = []
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed --include-releases` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note release --verify <zip>` の結果を確認してください。"
    )
    for path in selected:
        try:
            errors = verify_release_package(path)
        except (OSError, zipfile.BadZipFile) as exc:
            items.append(
                PrivacyAuditItem(
                    f"release package privacy: {path.name}",
                    "fail",
                    f"unreadable release package: {exc}",
                    action,
                    path,
                )
            )
            continue
        if errors:
            first_error = f": {errors[0]}" if errors else ""
            items.append(
                PrivacyAuditItem(
                    f"release package privacy: {path.name}",
                    "fail",
                    f"{len(errors)} verification error(s){first_error}",
                    action,
                    path,
                )
            )
        else:
            items.append(
                _zip_privacy_item(
                    path,
                    sensitive,
                    name=f"release package privacy: {path.name}",
                    action=action,
                )
            )
    return items


def _sales_handoff_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .sales_handoff import list_sales_handoffs, verify_sales_handoff

    handoffs = list_sales_handoffs(project_dir)
    if not handoffs:
        return [PrivacyAuditItem("sales handoff privacy", "info", "no sales handoffs found")]
    selected = handoffs if all_artifacts else handoffs[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note sales-handoff --project-dir .` で販売用一式を作り直してください。"
    )
    items: list[PrivacyAuditItem] = []
    for path in selected:
        errors = verify_sales_handoff(path)
        if errors:
            first_error = f": {errors[0]}" if errors else ""
            items.append(
                PrivacyAuditItem(
                    f"sales handoff privacy: {path.name}",
                    "fail",
                    f"{len(errors)} verification error(s){first_error}",
                    action,
                    path,
                )
            )
            continue
        items.append(
            _zip_privacy_item(
                path,
                sensitive,
                name=f"sales handoff privacy: {path.name}",
                action=action,
            )
        )
    return items


def _buyer_delivery_package_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .sales_handoff import list_buyer_delivery_packages, verify_buyer_delivery_package

    packages = list_buyer_delivery_packages(project_dir)
    if not packages:
        return [PrivacyAuditItem("buyer delivery zip privacy", "info", "no buyer delivery zips found")]
    selected = packages if all_artifacts else packages[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note sales-handoff --project-dir . --package-buyer <folder>` で購入者向けZIPを作り直してください。"
    )
    items: list[PrivacyAuditItem] = []
    for path in selected:
        errors = verify_buyer_delivery_package(path)
        if errors:
            first_error = f": {errors[0]}" if errors else ""
            items.append(
                PrivacyAuditItem(
                    f"buyer delivery zip privacy: {path.name}",
                    "fail",
                    f"buyer delivery zip verification failed{first_error}",
                    "`auto-note sales-handoff --project-dir . --verify-buyer-package <zip>` の結果を確認してください。",
                    path,
                )
            )
            continue
        items.append(
            _zip_privacy_item(
                path,
                sensitive,
                name=f"buyer delivery zip privacy: {path.name}",
                action=action,
            )
        )
    return items


def _sales_material_items(
    project_dir: Path,
    sensitive: list[SensitiveValue],
    *,
    all_artifacts: bool,
) -> list[PrivacyAuditItem]:
    from .sales_materials import list_sales_materials

    materials = list_sales_materials(project_dir)
    if not materials:
        return [PrivacyAuditItem("sales materials privacy", "info", "no sales materials found")]
    selected = materials if all_artifacts else materials[:1]
    action = (
        "`auto-note cleanup --project-dir . --privacy-failed` でプライバシー監査NGの整理候補を確認してください。"
        if all_artifacts
        else "`auto-note sales-materials --project-dir .` で販売素材を作り直してください。"
    )
    return [
        _file_privacy_item(
            path,
            sensitive,
            name=f"sales materials privacy: {path.name}",
            action=action,
        )
        for path in selected
    ]


def _zip_privacy_item(path: Path, sensitive: list[SensitiveValue], *, name: str, action: str) -> PrivacyAuditItem:
    try:
        leaks = _scan_zip_file(path, sensitive)
    except (OSError, zipfile.BadZipFile) as exc:
        return PrivacyAuditItem(name, "fail", f"unreadable zip: {exc}", action, path)
    if leaks:
        summary = "; ".join(_leak_summary(leaks))
        return PrivacyAuditItem(name, "fail", f"{len(leaks)} raw marker(s): {summary}", action, path)
    return PrivacyAuditItem(name, "pass", "no raw private markers found", path=path)


def _file_privacy_item(path: Path, sensitive: list[SensitiveValue], *, name: str, action: str) -> PrivacyAuditItem:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return PrivacyAuditItem(name, "fail", f"unreadable file: {exc}", action, path)
    leaks = _text_leaks(_normalize_scan_text(text, path.name), path.name, sensitive)
    if leaks:
        summary = "; ".join(_leak_summary(leaks))
        return PrivacyAuditItem(name, "fail", f"{len(leaks)} raw marker(s): {summary}", action, path)
    return PrivacyAuditItem(name, "pass", "no raw private markers found", path=path)


def _leak_summary(leaks: list[str]) -> list[str]:
    summary: list[str] = []
    for leak in leaks:
        _, _, marker = leak.partition(": ")
        value = marker or leak
        if value not in summary:
            summary.append(value)
        if len(summary) >= 8:
            break
    if len(summary) < len(set(leaks)):
        summary.append("more details available")
    return summary


def _scan_zip_file(path: Path, sensitive: list[SensitiveValue]) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return _scan_zip(archive, sensitive)


def _scan_zip(archive: zipfile.ZipFile, sensitive: list[SensitiveValue], *, prefix: str = "") -> list[str]:
    leaks: list[str] = []
    for name in archive.namelist():
        display = f"{prefix}{name}"
        data = archive.read(name)
        if name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(BytesIO(data)) as nested:
                    leaks.extend(_scan_zip(nested, sensitive, prefix=f"{display}!"))
            except zipfile.BadZipFile:
                leaks.append(f"{display}: nested zip is unreadable")
            continue
        text = _decode_if_text(data, name)
        if text is None:
            continue
        leaks.extend(_text_leaks(_normalize_scan_text(text, display), display, sensitive))
    return leaks


def _decode_if_text(data: bytes, name: str) -> str | None:
    suffix = Path(name).suffix.lower()
    if suffix and suffix not in {".txt", ".md", ".json", ".toml", ".log", ".csv", ".html", ".ics"}:
        return None
    if b"\x00" in data[:2048]:
        return None
    return data.decode("utf-8", errors="replace")


def _normalize_scan_text(text: str, location: str) -> str:
    if Path(location).suffix.lower() == ".ics":
        return re.sub(r"\r?\n[ \t]", "", text)
    return text


def _text_leaks(text: str, location: str, sensitive: list[SensitiveValue]) -> list[str]:
    leaks: list[str] = []
    folded = text.casefold()
    for item in sensitive:
        if item.value.casefold() in folded:
            leaks.append(f"{location}: raw {item.label}")
    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text):
        leaks.append(f"{location}: raw email address")
    return leaks


def _sensitive_values(project_dir: Path) -> list[SensitiveValue]:
    values: list[SensitiveValue] = []

    def add(label: str, value: str, *, min_length: int = 4) -> None:
        value = value.strip()
        if len(value) < min_length:
            return
        if any(existing.value.casefold() == value.casefold() for existing in values):
            return
        values.append(SensitiveValue(label, value))

    resolved = project_dir.resolve()
    add("project path", str(resolved))
    add("project path", resolved.as_posix())
    home = Path.home()
    add("home path", str(home))
    add("home path", home.as_posix())
    add("user name", home.name)

    settings = load_settings(project_dir)
    articles_dir = project_dir / "articles"
    if articles_dir.exists():
        for path in articles_dir.glob(settings.article_glob):
            if not path.is_file():
                continue
            if path.name.casefold() not in COMMON_ARTICLE_FILE_NAMES:
                add("article file name", path.name, min_length=8)
            try:
                article = load_article(path)
            except ArticleError:
                continue
            add("article title", article.title, min_length=6)
    return values
