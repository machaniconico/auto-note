from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path, PurePosixPath
import hashlib
import json
import zipfile

from .article import ArticleError, write_text_atomic
from .acceptance import (
    has_acceptance_blockers,
    run_acceptance_check,
    write_acceptance_report,
)
from .commercial_setup import (
    apply_commercial_setup_template,
    commercial_setup_missing_fields,
    commercial_setup_warnings,
    create_commercial_setup_template,
    list_commercial_setup_templates,
    parse_commercial_setup_template,
)
from .diagnostics import create_diagnostic_report
from .paths import unique_path
from .preflight import format_preflight_report, has_preflight_blockers, run_preflight
from .privacy import (
    format_privacy_audit_report,
    has_privacy_audit_blockers,
    run_privacy_audit,
)
from .sales_handoff import (
    create_sales_handoff,
    extract_buyer_delivery,
    format_buyer_delivery_package_verification,
    format_buyer_delivery_verification,
    format_sales_handoff_verification,
    list_buyer_delivery_packages,
    verify_buyer_delivery_package,
    verify_buyer_delivery,
    verify_sales_handoff,
)
from .sales_materials import (
    create_sales_materials,
    format_sales_materials_verification,
    verify_sales_materials,
)
from .sales_listing import (
    create_sales_listing_kit,
    format_sales_listing_verification,
    verify_sales_listing_kit,
)
from .sales_screenshots import (
    create_sales_screenshot_pack,
    format_sales_screenshot_verification,
    verify_sales_screenshot_pack,
)
from .sales_plan import write_sales_plan_report
from .release import list_releases
from .settings import AppSettings, load_settings


@dataclass(frozen=True)
class SalesFinalizeStep:
    name: str
    status: str
    detail: str
    action: str = ""


@dataclass(frozen=True)
class SalesFinalizeReport:
    project_dir: Path
    status: str
    steps: list[SalesFinalizeStep]
    release_path: Path | None = None
    commercial_template_path: Path | None = None
    sales_materials_path: Path | None = None
    sales_screenshot_pack_path: Path | None = None
    sales_listing_kit_path: Path | None = None
    sales_listing_package_path: Path | None = None
    sales_handoff_path: Path | None = None
    buyer_delivery_dir: Path | None = None
    buyer_delivery_package_path: Path | None = None
    buyer_delivery_message_path: Path | None = None
    sales_plan_report_path: Path | None = None
    seller_send_checklist_path: Path | None = None
    sales_evidence_manifest_path: Path | None = None
    acceptance_report_path: Path | None = None
    diagnostic_report_path: Path | None = None
    report_path: Path | None = None

    @property
    def ok(self) -> bool:
        return self.status != "fail"

    @property
    def has_warnings(self) -> bool:
        return any(step.status == "warn" for step in self.steps)


@dataclass(frozen=True)
class BuyerSendCheck:
    name: str
    status: str
    detail: str
    action: str = ""


@dataclass(frozen=True)
class BuyerSendReadinessReport:
    project_dir: Path
    status: str
    checks: list[BuyerSendCheck]
    latest_release_path: Path | None = None
    buyer_delivery_package_path: Path | None = None
    buyer_delivery_message_path: Path | None = None
    seller_send_checklist_path: Path | None = None
    sales_evidence_manifest_path: Path | None = None
    report_path: Path | None = None

    @property
    def ok(self) -> bool:
        return self.status != "fail"

    @property
    def has_warnings(self) -> bool:
        return any(check.status == "warn" for check in self.checks)


def create_sales_finalize(
    project_dir: Path,
    *,
    strict: bool = False,
    content_strict: bool = False,
    gui_smoke: bool = False,
    install_smoke: bool = False,
    apply_latest_template: bool = False,
    save_report: bool = True,
) -> SalesFinalizeReport:
    project_dir = project_dir.resolve()
    steps: list[SalesFinalizeStep] = []
    release_path: Path | None = None
    commercial_template_path: Path | None = None
    sales_materials_path: Path | None = None
    sales_screenshot_pack_path: Path | None = None
    sales_listing_kit_path: Path | None = None
    sales_listing_package_path: Path | None = None
    sales_handoff_path: Path | None = None
    buyer_delivery_dir: Path | None = None
    buyer_delivery_package_path: Path | None = None
    buyer_delivery_message_path: Path | None = None
    sales_plan_report_path: Path | None = None
    seller_send_checklist_path: Path | None = None
    sales_evidence_manifest_path: Path | None = None
    acceptance_report_path: Path | None = None
    diagnostic_report_path: Path | None = None

    def current_report() -> SalesFinalizeReport:
        return SalesFinalizeReport(
            project_dir=project_dir,
            status=_overall_status(steps),
            steps=steps,
            release_path=release_path,
            commercial_template_path=commercial_template_path,
            sales_materials_path=sales_materials_path,
            sales_screenshot_pack_path=sales_screenshot_pack_path,
            sales_listing_kit_path=sales_listing_kit_path,
            sales_listing_package_path=sales_listing_package_path,
            sales_handoff_path=sales_handoff_path,
            buyer_delivery_dir=buyer_delivery_dir,
            buyer_delivery_package_path=buyer_delivery_package_path,
            buyer_delivery_message_path=buyer_delivery_message_path,
            sales_plan_report_path=sales_plan_report_path,
            seller_send_checklist_path=seller_send_checklist_path,
            sales_evidence_manifest_path=sales_evidence_manifest_path,
            acceptance_report_path=acceptance_report_path,
            diagnostic_report_path=diagnostic_report_path,
        )

    def finish() -> SalesFinalizeReport:
        report = current_report()
        if save_report:
            path = _report_path(project_dir)
            report = replace(report, report_path=path)
            write_text_atomic(path, format_sales_finalize_report(report) + "\n")
        return report

    if apply_latest_template:
        templates = list_commercial_setup_templates(project_dir)
        if not templates:
            steps.append(
                SalesFinalizeStep(
                    "commercial setup template apply",
                    "warn",
                    "no commercial setup template found",
                    "`auto-note commercial-setup --project-dir . --template` で販売者情報テンプレートを作成してください。",
                )
            )
        elif not _template_has_filled_seller_values(templates[0]):
            steps.append(
                SalesFinalizeStep(
                    "commercial setup template apply",
                    "warn",
                    f"{templates[0].name}, no filled seller values; skipped",
                    "`auto-note commercial-setup --project-dir . --template` の未入力項目を埋めてください。",
                )
            )
        else:
            try:
                applied = apply_commercial_setup_template(project_dir, templates[0])
            except (ArticleError, OSError) as exc:
                steps.append(
                    SalesFinalizeStep(
                        "commercial setup template apply",
                        "fail",
                        str(exc),
                        "最新の販売者テンプレートを確認し、必要なら作り直してください。",
                    )
                )
                return finish()
            applied_setup_warnings = commercial_setup_warnings(applied.settings)
            apply_status = "warn" if applied.missing or applied.warnings or applied_setup_warnings else "pass"
            updated = ", ".join(applied.updated) if applied.updated else "(none)"
            warning_detail = _warnings_detail([*applied.warnings, *applied_setup_warnings])
            missing_detail = _missing_fields_detail(applied.settings)
            steps.append(
                SalesFinalizeStep(
                    "commercial setup template apply",
                    apply_status,
                    f"{applied.path.name}, updated {updated}, missing {applied.missing}{missing_detail}{warning_detail}",
                    "`auto-note commercial-setup --project-dir . --template` の未入力項目を埋めてください。"
                    if applied.missing
                    else "",
                )
            )

    try:
        template = create_commercial_setup_template(project_dir)
    except OSError as exc:
        steps.append(
            SalesFinalizeStep(
                "commercial setup template",
                "fail",
                str(exc),
                "販売者情報テンプレートの保存先を確認してください。",
            )
        )
        return finish()
    commercial_template_path = template.path
    settings = load_settings(project_dir)
    setup_warnings = commercial_setup_warnings(settings)
    template_status = "warn" if template.missing or setup_warnings else "pass"
    template_missing_detail = _missing_fields_detail(settings)
    template_warnings_detail = _warnings_detail(setup_warnings)
    steps.append(
        SalesFinalizeStep(
            "commercial setup template",
            template_status,
            f"{template.path.name}, missing {template.missing}{template_missing_detail}{template_warnings_detail}",
            "`auto-note commercial-setup --project-dir . --seller-name ...` で未入力項目を保存してください。"
            if template.missing or setup_warnings
            else "",
        )
    )

    preflight = run_preflight(
        project_dir,
        create_release=True,
        install_smoke=install_smoke,
        gui_smoke=gui_smoke,
        content_strict=content_strict,
        include_sales_handoffs=False,
    )
    release_path = preflight.created_release
    preflight_blocked = has_preflight_blockers(preflight, strict=strict)
    preflight_status = "fail" if preflight_blocked else ("warn" if preflight.has_warnings else "pass")
    steps.append(
        SalesFinalizeStep(
            "release preflight",
            preflight_status,
            _preflight_detail(preflight),
            "出荷前チェックのNG/WARN項目を確認してください。" if preflight_blocked else "",
        )
    )
    if preflight_blocked:
        return finish()

    try:
        materials = create_sales_materials(project_dir)
    except OSError as exc:
        steps.append(
            SalesFinalizeStep(
                "sales materials",
                "fail",
                str(exc),
                "販売素材Markdownの保存先を確認してください。",
            )
        )
        return finish()
    sales_materials_path = materials.path
    material_errors = verify_sales_materials(materials.path, strict=True, project_dir=project_dir)
    material_status = "pass"
    material_action = ""
    if material_errors:
        material_status = "fail" if strict else "warn"
        material_action = (
            "`auto-note commercial-setup --project-dir . --template` で販売者情報を埋め、"
            "`auto-note sales-materials --project-dir . --verify <path> --strict` を再実行してください。"
        )
    steps.append(
        SalesFinalizeStep(
            "sales materials",
            material_status,
            f"{materials.path.name}, placeholders {materials.placeholders}, strict issues {len(material_errors)}",
            material_action,
        )
    )
    if material_status == "fail":
        return finish()

    try:
        screenshot_pack = create_sales_screenshot_pack(project_dir)
    except OSError as exc:
        steps.append(
            SalesFinalizeStep(
                "sales screenshots",
                "fail",
                str(exc),
                "販売ページ掲載画像の保存先を確認してください。",
            )
        )
        return finish()
    sales_screenshot_pack_path = screenshot_pack.directory
    screenshot_errors = verify_sales_screenshot_pack(screenshot_pack.directory)
    steps.append(
        SalesFinalizeStep(
            "sales screenshots",
            "fail" if screenshot_errors else "pass",
            f"{screenshot_pack.directory.name}, assets {len(screenshot_pack.assets)}, verify errors {len(screenshot_errors)}",
            "掲載画像パックを確認し、`auto-note sales-screenshots --project-dir .` を再実行してください。"
            if screenshot_errors
            else "",
        )
    )
    if screenshot_errors:
        return finish()

    try:
        listing_kit = create_sales_listing_kit(project_dir, strict=True)
    except OSError as exc:
        steps.append(
            SalesFinalizeStep(
                "sales listing kit",
                "fail",
                str(exc),
                "販売ページ掲載キットの保存先を確認してください。",
            )
        )
        return finish()
    sales_listing_kit_path = listing_kit.directory
    sales_listing_package_path = listing_kit.package_path
    listing_errors = verify_sales_listing_kit(listing_kit.directory, strict=True, project_dir=project_dir)
    listing_package_errors = verify_sales_listing_kit(listing_kit.package_path, strict=True, project_dir=project_dir)
    listing_status = "pass"
    listing_action = ""
    if listing_errors or listing_package_errors:
        listing_status = "fail" if strict else "warn"
        listing_action = (
            "`auto-note sales-listing --project-dir . --verify <folder-or-zip> --strict` で確認し、"
            "販売者情報、掲載画像、checksum、購入者向け混入を直してください。"
        )
    steps.append(
        SalesFinalizeStep(
            "sales listing kit",
            listing_status,
            f"{listing_kit.directory.name}, package {listing_kit.package_path.name}, "
            f"folder issues {len(listing_errors)}, zip issues {len(listing_package_errors)}",
            listing_action,
        )
    )
    if listing_status == "fail":
        return finish()

    try:
        handoff = create_sales_handoff(project_dir, strict=strict)
    except (OSError, ValueError) as exc:
        steps.append(
            SalesFinalizeStep(
                "sales handoff",
                "fail",
                str(exc),
                "販売準備、プライバシー監査、最新配布ZIPの状態を確認してください。",
            )
        )
        return finish()
    sales_handoff_path = handoff.path
    handoff_errors = verify_sales_handoff(handoff.path)
    handoff_status = "fail" if handoff_errors else ("warn" if handoff.warnings else "pass")
    steps.append(
        SalesFinalizeStep(
            "sales handoff",
            handoff_status,
            f"{handoff.path.name}, readiness warnings {handoff.warnings}, verify errors {len(handoff_errors)}",
            "販売用一式ZIPの検証結果を確認してください。" if handoff_errors else "",
        )
    )
    if handoff_errors:
        return finish()

    try:
        buyer_delivery = extract_buyer_delivery(handoff.path)
    except (OSError, ValueError) as exc:
        steps.append(
            SalesFinalizeStep(
                "buyer delivery",
                "fail",
                str(exc),
                "販売用一式ZIPを検証し、`auto-note sales-handoff --project-dir . --extract-buyer <zip>` を再実行してください。",
            )
        )
        return finish()
    buyer_delivery_dir = buyer_delivery.directory
    buyer_delivery_errors = verify_buyer_delivery(buyer_delivery.directory)
    steps.append(
        SalesFinalizeStep(
            "buyer delivery",
            "fail" if buyer_delivery_errors else "pass",
            f"{buyer_delivery.directory.name}, release {buyer_delivery.release_path.name}, verify errors {len(buyer_delivery_errors)}",
            "購入者向けフォルダの余計なファイルや配布ZIP破損を確認してください。" if buyer_delivery_errors else "",
        )
    )
    if buyer_delivery_errors:
        return finish()
    buyer_delivery_package_path = buyer_delivery.package_path
    buyer_delivery_package_errors = verify_buyer_delivery_package(buyer_delivery.package_path)
    steps.append(
        SalesFinalizeStep(
            "buyer delivery zip",
            "fail" if buyer_delivery_package_errors else "pass",
            f"{buyer_delivery.package_path.name}, verify errors {len(buyer_delivery_package_errors)}",
            "購入者向けZIPの中身とチェックサムを確認してください。" if buyer_delivery_package_errors else "",
        )
    )
    if buyer_delivery_package_errors:
        return finish()
    try:
        buyer_delivery_message_path = _write_buyer_delivery_message(
            project_dir,
            package_path=buyer_delivery.package_path,
            handoff_path=handoff.path,
            release_path=buyer_delivery.release_path,
        )
    except OSError as exc:
        steps.append(
            SalesFinalizeStep(
                "buyer delivery message",
                "fail",
                str(exc),
                "購入者向け送付文の保存先を確認してください。",
            )
        )
        return finish()
    steps.append(SalesFinalizeStep("buyer delivery message", "pass", buyer_delivery_message_path.name))

    try:
        acceptance = run_acceptance_check(
            project_dir,
            create=True,
            gui_smoke=gui_smoke,
            smoke_helper=True,
            include_sales_handoffs=False,
        )
        acceptance_report_path = write_acceptance_report(project_dir, report=acceptance)
    except OSError as exc:
        steps.append(
            SalesFinalizeStep(
                "buyer acceptance",
                "fail",
                str(exc),
                "受入チェックレポートの保存先を確認してください。",
            )
        )
        return finish()
    acceptance_blocked = has_acceptance_blockers(acceptance, strict=strict)
    acceptance_status = "fail" if acceptance_blocked else ("warn" if acceptance.has_warnings else "pass")
    steps.append(
        SalesFinalizeStep(
            "buyer acceptance",
            acceptance_status,
            f"{acceptance_report_path.name}, {_acceptance_detail(acceptance)}",
            "受入チェックのWARN/NG項目を確認してください。" if acceptance_status in {"warn", "fail"} else "",
        )
    )
    if acceptance_status == "fail":
        return finish()

    try:
        sales_plan_report_path = write_sales_plan_report(project_dir)
    except OSError as exc:
        steps.append(
            SalesFinalizeStep(
                "sales plan report",
                "fail",
                str(exc),
                "販売ナビレポートの保存先を確認してください。",
            )
        )
        return finish()
    steps.append(SalesFinalizeStep("sales plan report", "pass", sales_plan_report_path.name))

    try:
        diagnostic_report_path = create_diagnostic_report(project_dir)
    except OSError as exc:
        steps.append(
            SalesFinalizeStep(
                "diagnostic report",
                "fail",
                str(exc),
                "診断ZIPの保存先を確認してください。",
            )
        )
        return finish()
    steps.append(SalesFinalizeStep("diagnostic report", "pass", diagnostic_report_path.name))

    privacy = run_privacy_audit(project_dir)
    privacy_blocked = has_privacy_audit_blockers(privacy) or (strict and privacy.status == "warn")
    privacy_status = "fail" if privacy_blocked else ("warn" if privacy.status == "warn" else "pass")
    privacy_failures = sum(1 for item in privacy.items if item.status == "fail")
    privacy_warnings = sum(1 for item in privacy.items if item.status == "warn")
    steps.append(
        SalesFinalizeStep(
            "privacy audit",
            privacy_status,
            f"{privacy_failures} failure(s), {privacy_warnings} warning(s), {len(privacy.items)} checked",
            "`auto-note privacy-audit --project-dir .` のNG/WARN項目を確認してください。" if privacy_blocked else "",
        )
    )
    if privacy_blocked:
        return finish()

    final_preflight = run_preflight(project_dir, content_strict=content_strict)
    final_blocked = has_preflight_blockers(final_preflight, strict=strict)
    final_status = "fail" if final_blocked else ("warn" if final_preflight.has_warnings else "pass")
    steps.append(
        SalesFinalizeStep(
            "final preflight",
            final_status,
            _preflight_detail(final_preflight),
            "最終出荷前チェックのNG/WARN項目を確認してください。" if final_blocked else "",
        )
    )
    try:
        planned_sales_evidence_manifest_path = _sales_evidence_manifest_path(project_dir)
        seller_send_checklist_path = _write_seller_send_checklist(
            project_dir,
            buyer_package_path=buyer_delivery_package_path,
            buyer_message_path=buyer_delivery_message_path,
            sales_handoff_path=sales_handoff_path,
            release_path=release_path,
            sales_screenshot_pack_path=sales_screenshot_pack_path,
            sales_listing_kit_path=sales_listing_kit_path,
            sales_listing_package_path=sales_listing_package_path,
            acceptance_report_path=acceptance_report_path,
            sales_plan_report_path=sales_plan_report_path,
            sales_evidence_manifest_path=planned_sales_evidence_manifest_path,
            diagnostic_report_path=diagnostic_report_path,
            privacy_status=privacy_status,
            final_preflight_status=final_status,
            steps=steps,
        )
    except OSError as exc:
        steps.append(
            SalesFinalizeStep(
                "seller send checklist",
                "fail",
                str(exc),
                "販売者送付前チェックリストの保存先を確認してください。",
            )
        )
        return finish()
    steps.append(SalesFinalizeStep("seller send checklist", "pass", seller_send_checklist_path.name))

    sales_evidence_manifest_path = planned_sales_evidence_manifest_path
    try:
        _write_sales_evidence_manifest(current_report())
    except OSError as exc:
        steps.append(
            SalesFinalizeStep(
                "sales evidence manifest",
                "fail",
                str(exc),
                "販売証跡マニフェストの保存先を確認してください。",
            )
        )
        return finish()
    steps.append(SalesFinalizeStep("sales evidence manifest", "pass", sales_evidence_manifest_path.name))

    return finish()


def list_sales_finalize_reports(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(sales_dir.glob("sales-finalize-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def list_seller_send_checklists(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(sales_dir.glob("seller-send-checklist-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def list_buyer_delivery_messages(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(sales_dir.glob("buyer-delivery-message-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def list_buyer_send_readiness_reports(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(sales_dir.glob("buyer-send-readiness-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def list_seller_delivery_receipts(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(sales_dir.glob("seller-delivery-receipt-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def list_sales_evidence_manifests(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(sales_dir.glob("sales-evidence-manifest-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)


def find_buyer_delivery_package_for_message(message_text: str, packages: list[Path]) -> Path | None:
    for package_path in packages:
        if package_path.name in message_text:
            return package_path
    return packages[0] if packages else None


def _buyer_delivery_package_release_name(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if "BUYER_DELIVERY_MANIFEST.json" in names:
                raw = json.loads(archive.read("BUYER_DELIVERY_MANIFEST.json").decode("utf-8"))
                if isinstance(raw, dict) and isinstance(raw.get("release_package"), str):
                    return raw["release_package"]
            release_entries = [
                name
                for name in names
                if PurePosixPath(name).parent == PurePosixPath(".")
                and PurePosixPath(name).name.startswith("auto-note-release-")
                and PurePosixPath(name).suffix.casefold() == ".zip"
            ]
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if len(release_entries) != 1:
        return ""
    return PurePosixPath(release_entries[0]).name


def run_buyer_send_readiness(project_dir: Path) -> BuyerSendReadinessReport:
    checks: list[BuyerSendCheck] = []
    messages = list_buyer_delivery_messages(project_dir)
    packages = list_buyer_delivery_packages(project_dir)
    checklists = list_seller_send_checklists(project_dir)
    manifests = list_sales_evidence_manifests(project_dir)
    releases = list_releases(project_dir)
    latest_release = releases[0] if releases else None

    message_path = messages[0] if messages else None
    message_text = ""
    package_path: Path | None = None
    package_sha = ""

    if message_path is None:
        checks.append(
            BuyerSendCheck(
                "buyer delivery message",
                "fail",
                "not found",
                "販売一括作成で購入者向け送付文を作成してください。",
            )
        )
    else:
        try:
            message_text = message_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            checks.append(
                BuyerSendCheck(
                    "buyer delivery message",
                    "fail",
                    str(exc),
                    "購入者向け送付文を開けるか確認してください。",
                )
            )
        else:
            package_path = find_buyer_delivery_package_for_message(message_text, packages)
            if package_path is None:
                checks.append(
                    BuyerSendCheck(
                        "buyer delivery message",
                        "fail",
                        f"{message_path.name}: buyer delivery zip not referenced or not found",
                        "販売一括作成で送付文と購入者向けZIPを作り直してください。",
                    )
                )
            else:
                checks.append(
                    BuyerSendCheck(
                        "buyer delivery message",
                        "pass",
                        f"{message_path.name} references {package_path.name}",
                    )
                )
            missing_message_parts = [
                part
                for part in (
                    "Paste-ready message",
                    "SHA-256",
                    "START_HERE_FOR_BUYER.txt",
                    "BUYER_SUPPORT_REQUEST.txt",
                    "パスワード",
                )
                if part not in message_text
            ]
            if missing_message_parts:
                checks.append(
                    BuyerSendCheck(
                        "buyer delivery message contents",
                        "warn",
                        "missing " + ", ".join(missing_message_parts),
                        "販売一括作成で送付文を再生成してください。",
                    )
                )
            else:
                checks.append(BuyerSendCheck("buyer delivery message contents", "pass", "paste-ready"))

    if package_path is None and packages:
        package_path = packages[0]

    if package_path is None:
        checks.append(
            BuyerSendCheck(
                "buyer delivery zip",
                "fail",
                "not found",
                "販売一括作成または購入者ZIP抽出を実行してください。",
            )
        )
    else:
        package_errors = verify_buyer_delivery_package(package_path)
        if package_errors:
            checks.append(
                BuyerSendCheck(
                    "buyer delivery zip",
                    "fail",
                    f"{package_path.name}: {len(package_errors)} issue(s): {'; '.join(package_errors)}",
                    "販売一括作成で購入者向けZIPを作り直してください。",
                )
            )
        else:
            checks.append(BuyerSendCheck("buyer delivery zip", "pass", f"{package_path.name} verified"))
            package_release_name = _buyer_delivery_package_release_name(package_path)
            if latest_release and package_release_name == latest_release.name:
                checks.append(
                    BuyerSendCheck(
                        "buyer delivery zip freshness",
                        "pass",
                        f"{package_release_name} matches latest release",
                    )
                )
            elif latest_release and package_release_name:
                checks.append(
                    BuyerSendCheck(
                        "buyer delivery zip freshness",
                        "fail",
                        f"{package_path.name} contains {package_release_name}, latest release is {latest_release.name}",
                        "販売一括作成で最新配布ZIPの購入者ZIPと送付文を作り直してください。",
                    )
                )
            elif latest_release:
                checks.append(
                    BuyerSendCheck(
                        "buyer delivery zip freshness",
                        "warn",
                        f"{package_path.name}: release package name could not be confirmed",
                        "購入者ZIP検証を確認し、必要なら販売一括作成で作り直してください。",
                    )
                )
            else:
                checks.append(
                    BuyerSendCheck(
                        "buyer delivery zip freshness",
                        "warn",
                        "latest release package not found",
                        "配布ZIPを作成してから販売一括作成を再実行してください。",
                    )
                )
        try:
            package_sha = hashlib.sha256(package_path.read_bytes()).hexdigest()
        except OSError as exc:
            checks.append(
                BuyerSendCheck(
                    "buyer delivery zip checksum",
                    "fail",
                    str(exc),
                    "購入者向けZIPを読めるか確認してください。",
                )
            )
        else:
            if message_text and package_sha not in message_text:
                checks.append(
                    BuyerSendCheck(
                        "buyer delivery message checksum",
                        "fail",
                        f"{message_path.name if message_path else '(no message)'} does not include current ZIP SHA-256",
                        "送付文コピー前に販売一括作成で送付文を作り直してください。",
                    )
                )
            elif message_text:
                checks.append(BuyerSendCheck("buyer delivery message checksum", "pass", "message SHA-256 matches"))

    checklist_path = checklists[0] if checklists else None
    if checklist_path is None:
        checks.append(
            BuyerSendCheck(
                "seller send checklist",
                "warn",
                "not found",
                "販売一括作成で販売者送付前チェックリストを作成してください。",
            )
        )
    else:
        try:
            checklist_text = checklist_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            checks.append(
                BuyerSendCheck(
                    "seller send checklist",
                    "warn",
                    str(exc),
                    "販売者送付前チェックリストを開けるか確認してください。",
                )
            )
        else:
            missing_checklist_parts = []
            if package_path and package_path.name not in checklist_text:
                missing_checklist_parts.append(package_path.name)
            if message_path and message_path.name not in checklist_text:
                missing_checklist_parts.append(message_path.name)
            if "Do not attach auto-note-sales-handoff-*.zip" not in checklist_text:
                missing_checklist_parts.append("Do not attach auto-note-sales-handoff-*.zip")
            if "Do not attach auto-note-sales-listing-kit-*.zip" not in checklist_text:
                missing_checklist_parts.append("Do not attach auto-note-sales-listing-kit-*.zip")
            if missing_checklist_parts:
                checks.append(
                    BuyerSendCheck(
                        "seller send checklist",
                        "warn",
                        f"{checklist_path.name}: missing {', '.join(missing_checklist_parts)}",
                        "販売一括作成でチェックリストを作り直してください。",
                    )
                )
            else:
                checks.append(BuyerSendCheck("seller send checklist", "pass", f"{checklist_path.name} matches"))

    manifest_path = manifests[0] if manifests else None
    if manifest_path is None:
        checks.append(
            BuyerSendCheck(
                "sales evidence manifest",
                "warn",
                "not found",
                "販売一括作成で販売証跡JSONを作成してください。",
            )
        )
    else:
        manifest_errors = _buyer_send_manifest_errors(
            manifest_path,
            package_path=package_path,
            message_path=message_path,
            package_sha=package_sha,
        )
        if manifest_errors:
            checks.append(
                BuyerSendCheck(
                    "sales evidence manifest",
                    "fail",
                    f"{manifest_path.name}: {'; '.join(manifest_errors)}",
                    "販売一括作成で販売証跡JSONを作り直してください。",
                )
            )
        else:
            checks.append(BuyerSendCheck("sales evidence manifest", "pass", f"{manifest_path.name} matches"))

    status = _buyer_send_status(checks)
    return BuyerSendReadinessReport(
        project_dir=project_dir,
        status=status,
        checks=checks,
        latest_release_path=latest_release,
        buyer_delivery_package_path=package_path,
        buyer_delivery_message_path=message_path,
        seller_send_checklist_path=checklist_path,
        sales_evidence_manifest_path=manifest_path,
    )


def format_buyer_send_readiness_report(report: BuyerSendReadinessReport) -> str:
    counts = {
        "pass": sum(1 for check in report.checks if check.status == "pass"),
        "warn": sum(1 for check in report.checks if check.status == "warn"),
        "fail": sum(1 for check in report.checks if check.status == "fail"),
    }
    verdict = {"pass": "READY", "warn": "READY WITH WARNINGS", "fail": "DO NOT SEND"}.get(
        report.status,
        report.status.upper(),
    )
    lines = [
        "Buyer send readiness / 購入者送付前チェック",
        f"Verdict: {verdict}",
        f"Checks: {counts['pass']} OK, {counts['warn']} WARN, {counts['fail']} NG",
        "",
        "Artifacts / 送付関連ファイル",
        f"- latest release package: {_name_or_none(report.latest_release_path)}",
        f"- buyer delivery zip: {_name_or_none(report.buyer_delivery_package_path)}",
        f"- buyer delivery message: {_name_or_none(report.buyer_delivery_message_path)}",
        f"- seller send checklist: {_name_or_none(report.seller_send_checklist_path)}",
        f"- sales evidence manifest: {_name_or_none(report.sales_evidence_manifest_path)}",
        f"- buyer send readiness report: {_name_or_none(report.report_path)}",
        "",
        "Checks / 確認結果",
    ]
    status_label = {"pass": "OK", "warn": "WARN", "fail": "NG"}
    for check in report.checks:
        lines.append(f"[{status_label.get(check.status, check.status.upper())}] {check.name}: {check.detail}")
        if check.action:
            lines.append(f"    next: {check.action}")
    lines.extend(["", "Next / 次の操作"])
    if report.status == "fail":
        lines.append("- まだ購入者へ送付しないでください。NG項目を直してから再確認してください。")
    else:
        lines.append(f"- 添付するZIPは {_name_or_none(report.buyer_delivery_package_path)} だけです。")
        lines.append("- GUIの `送付文コピー` で、検証済み送付文をクリップボードへコピーできます。")
        lines.append("- GUIの `ZIPパスコピー` / `送付情報コピー` で、添付ZIPのパスと照合値をコピーできます。")
        lines.append("- 販売者は販売用一式ZIP、販売ナビ、販売証跡JSON、診断ZIPを証跡として保管してください。")
    return "\n".join(lines)


def has_buyer_send_readiness_blockers(report: BuyerSendReadinessReport, *, strict: bool = False) -> bool:
    if report.status == "fail":
        return True
    return strict and report.status == "warn"


def write_buyer_send_readiness_report(project_dir: Path, *, report: BuyerSendReadinessReport | None = None) -> Path:
    project_dir = project_dir.resolve()
    report = report or run_buyer_send_readiness(project_dir)
    path = _buyer_send_readiness_report_path(project_dir)
    saved_report = replace(report, report_path=path)
    write_text_atomic(path, format_buyer_send_readiness_report(saved_report) + "\n")
    return path


def format_seller_delivery_receipt(
    report: BuyerSendReadinessReport,
    *,
    receipt_path: Path | None = None,
    created_at: datetime | None = None,
) -> str:
    created_at = created_at or datetime.now()
    verdict = {"pass": "READY", "warn": "READY WITH WARNINGS", "fail": "DO NOT SEND"}.get(
        report.status,
        report.status.upper(),
    )
    lines = [
        "auto-note seller delivery receipt / 販売者向け納品記録",
        "",
        f"Created at / 作成日時: {created_at.isoformat(timespec='seconds')}",
        f"Receipt file / 記録ファイル: {_name_or_none(receipt_path)}",
        f"Buyer send readiness / 送付前判定: {verdict}",
        "",
        "Fill after sending / 送付後に記録",
        "- Order ID / 注文ID: (fill in your marketplace order record)",
        "- Marketplace / 販売先: (fill)",
        "- Buyer account / 購入者表示名: (fill only in your private seller record)",
        "- Sent at / 送付日時: (fill)",
        "- Sent by / 送付者: (fill)",
        "",
        "Sent package / 送付したもの",
        f"- Latest release package at check: {_name_or_none(report.latest_release_path)}",
        f"- Buyer delivery ZIP: {_file_evidence(report.buyer_delivery_package_path) or _name_or_none(report.buyer_delivery_package_path)}",
        f"- Buyer delivery message: {_name_or_none(report.buyer_delivery_message_path)}",
        f"- Buyer send readiness report: {_name_or_none(report.report_path)}",
        "",
        "Order management copy block / 注文管理コピー欄",
        f"- auto-note delivery record: {verdict}",
        f"- Buyer delivery ZIP: {_name_or_none(report.buyer_delivery_package_path)}",
        f"- ZIP evidence: {_file_evidence(report.buyer_delivery_package_path) or '(not available)'}",
        f"- Buyer delivery message: {_name_or_none(report.buyer_delivery_message_path)}",
        f"- Latest release package at check: {_name_or_none(report.latest_release_path)}",
        f"- Buyer send readiness report: {_name_or_none(report.report_path)}",
        "- Seller note: Attach/send only the buyer delivery ZIP. Keep this receipt seller-only.",
        "",
        "Seller evidence to keep / 販売者が保管する証跡",
        f"- Seller send checklist: {_name_or_none(report.seller_send_checklist_path)}",
        f"- Sales evidence manifest: {_name_or_none(report.sales_evidence_manifest_path)}",
        "- Sales handoff ZIP, sales plan report, diagnostics ZIP, and marketplace order record",
        "",
        "Delivery checklist / 送付チェック",
    ]
    if report.status == "fail":
        lines.extend(
            [
                "[ ] DO NOT SEND. Fix the NG items in the buyer send readiness report first.",
                "[ ] Re-run `auto-note sales-finalize --project-dir . --send-check --send-check-report` after fixing.",
            ]
        )
    else:
        lines.extend(
            [
                f"[ ] Attached exactly this ZIP: {_name_or_none(report.buyer_delivery_package_path)}",
                "[ ] Pasted the verified buyer delivery message.",
                "[ ] Confirmed no sales handoff ZIP, diagnostics ZIP, workspace, .auto-note, .venv, passwords, login codes, payment data, or full unpublished drafts were sent.",
                "[ ] Stored this receipt with the marketplace order record.",
            ]
        )
    lines.extend(
        [
            "",
            "Privacy note / プライバシーメモ",
            "- This receipt is seller-only. Do not attach it to buyer support requests.",
            "- If you fill buyer account or order ID here, keep this file private.",
        ]
    )
    return "\n".join(lines)


def write_seller_delivery_receipt(project_dir: Path, *, report: BuyerSendReadinessReport | None = None) -> Path:
    project_dir = project_dir.resolve()
    report = report or run_buyer_send_readiness(project_dir)
    path = _seller_delivery_receipt_path(project_dir)
    write_text_atomic(path, format_seller_delivery_receipt(report, receipt_path=path) + "\n")
    return path


def format_sales_finalize_report(report: SalesFinalizeReport) -> str:
    counts = {
        "pass": sum(1 for step in report.steps if step.status == "pass"),
        "warn": sum(1 for step in report.steps if step.status == "warn"),
        "fail": sum(1 for step in report.steps if step.status == "fail"),
    }
    verdict = {"pass": "READY", "warn": "READY WITH WARNINGS", "fail": "BLOCKED"}.get(
        report.status,
        report.status.upper(),
    )
    lines = [
        "Sales finalize / 販売準備一括",
        f"Verdict: {verdict}",
        f"Items: {counts['pass']} OK, {counts['warn']} WARN, {counts['fail']} NG",
        "",
        "Artifacts",
        f"- release package: {_name_or_none(report.release_path)}",
        f"- commercial setup template: {_name_or_none(report.commercial_template_path)}",
        f"- sales materials: {_name_or_none(report.sales_materials_path)}",
        f"- sales screenshot pack: {_name_or_none(report.sales_screenshot_pack_path)}",
        f"- sales listing kit: {_name_or_none(report.sales_listing_kit_path)}",
        f"- sales listing package: {_name_or_none(report.sales_listing_package_path)}",
        f"- sales handoff: {_name_or_none(report.sales_handoff_path)}",
        f"- buyer delivery: {_name_or_none(report.buyer_delivery_dir)}",
        f"- buyer delivery zip: {_name_or_none(report.buyer_delivery_package_path)}",
        f"- buyer delivery message: {_name_or_none(report.buyer_delivery_message_path)}",
        f"- sales plan report: {_name_or_none(report.sales_plan_report_path)}",
        f"- seller send checklist: {_name_or_none(report.seller_send_checklist_path)}",
        f"- sales evidence manifest: {_name_or_none(report.sales_evidence_manifest_path)}",
        f"- acceptance report: {_name_or_none(report.acceptance_report_path)}",
        f"- diagnostic report: {_name_or_none(report.diagnostic_report_path)}",
        f"- finalize report: {_name_or_none(report.report_path)}",
        "",
    ]
    buyer_contents = _buyer_delivery_contents(report)
    if buyer_contents:
        lines.append("Buyer delivery contents")
        lines.extend(f"- {name}" for name in buyer_contents)
        lines.append("")
    delivery_verification = _delivery_verification_lines(report)
    if delivery_verification:
        lines.append("Delivery verification")
        lines.extend(delivery_verification)
        lines.append("")
    lines.append("Checks")
    next_actions: list[str] = []
    for step in report.steps:
        label = {"pass": "OK", "warn": "WARN", "fail": "NG"}.get(step.status, step.status.upper())
        lines.append(f"[{label}] {step.name}: {step.detail}")
        if step.action:
            lines.append(f"  next: {step.action}")
            next_actions.append(f"- {step.name}: {step.action}")

    if report.sales_handoff_path and report.status != "fail":
        if report.buyer_delivery_dir:
            if report.buyer_delivery_package_path:
                next_actions.append(
                    f"- delivery: 購入者には {report.buyer_delivery_package_path.name} を渡し、"
                    f"販売者は {report.sales_handoff_path.name} を証跡として保管してください。"
                )
                if report.buyer_delivery_message_path:
                    next_actions.append(
                        f"- delivery message: {report.buyer_delivery_message_path.name} の文面を販売サイトの納品メッセージに貼り付けてください。"
                    )
                if report.sales_screenshot_pack_path:
                    next_actions.append(
                        f"- listing images: {report.sales_screenshot_pack_path.name} の index.html と SCREENSHOT_CAPTIONS.md を掲載前に確認してください。"
                    )
                if report.sales_listing_package_path:
                    next_actions.append(
                        f"- listing kit: {report.sales_listing_package_path.name} は販売ページ作成用に保管し、購入者には送らないでください。"
                    )
                if report.sales_plan_report_path:
                    next_actions.append(
                        f"- sales plan: {report.sales_plan_report_path.name} で販売者入力残件とアップロード判断を保管してください。"
                    )
                if report.seller_send_checklist_path:
                    next_actions.append(
                        f"- seller checklist: {report.seller_send_checklist_path.name} で、送るZIP/保管するZIP/送らないものを確認してください。"
                    )
                if report.sales_evidence_manifest_path:
                    next_actions.append(
                        f"- evidence manifest: {report.sales_evidence_manifest_path.name} を注文管理の証跡として保管してください。"
                    )
            else:
                next_actions.append(
                    f"- delivery: 購入者には {report.buyer_delivery_dir.name} の配布ZIP、START_HERE_FOR_BUYER.txt、BUYER_HANDOFF.txt、"
                    "BUYER_SUPPORT_GUIDE.txt、BUYER_SUPPORT_REQUEST.txt、BUYER_DELIVERY_MANIFEST.json、SHA256SUMS.txt を渡し、"
                    f"販売者は {report.sales_handoff_path.name} を証跡として保管してください。"
                )
        else:
            next_actions.append(
                f"- delivery: 販売者は {report.sales_handoff_path.name} を証跡として保管し、"
                "中の release/auto-note-release-*.zip を購入者へ渡してください。"
            )
    if next_actions:
        lines.extend(["", "Next actions"])
        lines.extend(next_actions)
    return "\n".join(lines)


def format_sales_finalize_details(report: SalesFinalizeReport) -> str:
    parts = [format_sales_finalize_report(report)]
    if report.sales_materials_path:
        material_errors = verify_sales_materials(report.sales_materials_path, strict=True, project_dir=report.project_dir)
        parts.append(format_sales_materials_verification(report.sales_materials_path, material_errors, strict=True))
    if report.sales_screenshot_pack_path:
        parts.append(
            format_sales_screenshot_verification(
                report.sales_screenshot_pack_path,
                verify_sales_screenshot_pack(report.sales_screenshot_pack_path),
            )
        )
        for filename in ("README.txt", "SCREENSHOT_CAPTIONS.md"):
            try:
                parts.append((report.sales_screenshot_pack_path / filename).read_text(encoding="utf-8", errors="replace").strip())
            except OSError:
                pass
    if report.sales_listing_kit_path:
        parts.append(
            format_sales_listing_verification(
                report.sales_listing_kit_path,
                verify_sales_listing_kit(report.sales_listing_kit_path, strict=True, project_dir=report.project_dir),
                strict=True,
            )
        )
    if report.sales_listing_package_path:
        parts.append(
            format_sales_listing_verification(
                report.sales_listing_package_path,
                verify_sales_listing_kit(report.sales_listing_package_path, strict=True, project_dir=report.project_dir),
                strict=True,
            )
        )
    if report.sales_handoff_path:
        parts.append(format_sales_handoff_verification(report.sales_handoff_path, verify_sales_handoff(report.sales_handoff_path)))
    if report.buyer_delivery_dir:
        parts.append(
            format_buyer_delivery_verification(
                report.buyer_delivery_dir,
                verify_buyer_delivery(report.buyer_delivery_dir),
            )
        )
    if report.buyer_delivery_package_path:
        parts.append(
            format_buyer_delivery_package_verification(
                report.buyer_delivery_package_path,
                verify_buyer_delivery_package(report.buyer_delivery_package_path),
            )
        )
    if report.buyer_delivery_message_path:
        try:
            parts.append(report.buyer_delivery_message_path.read_text(encoding="utf-8", errors="replace").strip())
        except OSError:
            pass
    if report.sales_plan_report_path:
        try:
            parts.append(report.sales_plan_report_path.read_text(encoding="utf-8", errors="replace").strip())
        except OSError:
            pass
    if report.seller_send_checklist_path:
        try:
            parts.append(report.seller_send_checklist_path.read_text(encoding="utf-8", errors="replace").strip())
        except OSError:
            pass
    if report.sales_evidence_manifest_path:
        try:
            parts.append(report.sales_evidence_manifest_path.read_text(encoding="utf-8", errors="replace").strip())
        except OSError:
            pass
    if report.acceptance_report_path:
        try:
            parts.append(report.acceptance_report_path.read_text(encoding="utf-8", errors="replace").strip())
        except OSError:
            pass
    parts.append(format_privacy_audit_report(run_privacy_audit(report.project_dir)))
    parts.append(format_preflight_report(run_preflight(report.project_dir)))
    return "\n\n".join(parts)


def has_sales_finalize_blockers(report: SalesFinalizeReport, *, strict: bool = False) -> bool:
    if report.status == "fail":
        return True
    return strict and report.status == "warn"


def _report_path(project_dir: Path) -> Path:
    sales_dir = project_dir / ".auto-note" / "sales"
    sales_dir.mkdir(parents=True, exist_ok=True)
    return unique_path(sales_dir / f"sales-finalize-{datetime.now():%Y%m%d-%H%M%S}.txt")


def _buyer_delivery_message_path(project_dir: Path) -> Path:
    sales_dir = project_dir / ".auto-note" / "sales"
    sales_dir.mkdir(parents=True, exist_ok=True)
    return unique_path(sales_dir / f"buyer-delivery-message-{datetime.now():%Y%m%d-%H%M%S}.txt")


def _buyer_send_readiness_report_path(project_dir: Path) -> Path:
    sales_dir = project_dir / ".auto-note" / "sales"
    sales_dir.mkdir(parents=True, exist_ok=True)
    return unique_path(sales_dir / f"buyer-send-readiness-{datetime.now():%Y%m%d-%H%M%S}.txt")


def _seller_delivery_receipt_path(project_dir: Path) -> Path:
    sales_dir = project_dir / ".auto-note" / "sales"
    sales_dir.mkdir(parents=True, exist_ok=True)
    return unique_path(sales_dir / f"seller-delivery-receipt-{datetime.now():%Y%m%d-%H%M%S}.txt")


def _seller_send_checklist_path(project_dir: Path) -> Path:
    sales_dir = project_dir / ".auto-note" / "sales"
    sales_dir.mkdir(parents=True, exist_ok=True)
    return unique_path(sales_dir / f"seller-send-checklist-{datetime.now():%Y%m%d-%H%M%S}.txt")


def _sales_evidence_manifest_path(project_dir: Path) -> Path:
    sales_dir = project_dir / ".auto-note" / "sales"
    sales_dir.mkdir(parents=True, exist_ok=True)
    return unique_path(sales_dir / f"sales-evidence-manifest-{datetime.now():%Y%m%d-%H%M%S}.json")


def _buyer_send_status(checks: list[BuyerSendCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "warn" for check in checks):
        return "warn"
    return "pass"


def _buyer_send_manifest_errors(
    manifest_path: Path,
    *,
    package_path: Path | None,
    message_path: Path | None,
    package_sha: str,
) -> list[str]:
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"unreadable JSON: {exc}"]
    if not isinstance(raw, dict):
        return ["manifest is not an object"]
    errors: list[str] = []
    if raw.get("schema") != "auto-note.sales-evidence-manifest.v1":
        errors.append("schema mismatch")
    if raw.get("verdict") == "fail":
        errors.append("manifest verdict is fail")
    artifacts = raw.get("artifacts")
    if not isinstance(artifacts, dict):
        return [*errors, "artifacts missing"]

    buyer_zip = artifacts.get("buyer_delivery_zip")
    if package_path is not None:
        if not isinstance(buyer_zip, dict):
            errors.append("buyer_delivery_zip artifact missing")
        else:
            if buyer_zip.get("file_name") != package_path.name:
                errors.append("buyer_delivery_zip file name mismatch")
            if package_sha and buyer_zip.get("sha256") != package_sha:
                errors.append("buyer_delivery_zip SHA-256 mismatch")

    buyer_message = artifacts.get("buyer_delivery_message")
    if message_path is not None:
        if not isinstance(buyer_message, dict):
            errors.append("buyer_delivery_message artifact missing")
        elif buyer_message.get("file_name") != message_path.name:
            errors.append("buyer_delivery_message file name mismatch")
    return errors


def _overall_status(steps: list[SalesFinalizeStep]) -> str:
    if any(step.status == "fail" for step in steps):
        return "fail"
    if any(step.status == "warn" for step in steps):
        return "warn"
    return "pass"


def _preflight_detail(report) -> str:
    failures = sum(1 for item in report.items if item.status == "fail")
    warnings = sum(1 for item in report.items if item.status == "warn")
    infos = sum(1 for item in report.items if item.status == "info")
    created = f", created {report.created_release.name}" if report.created_release else ""
    return f"{report.readiness_score}/100, {failures} failure(s), {warnings} warning(s), {infos} info{created}"


def _acceptance_detail(report) -> str:
    failures = sum(1 for item in report.items if item.status == "fail")
    warnings = sum(1 for item in report.items if item.status == "warn")
    infos = sum(1 for item in report.items if item.status == "info")
    return f"{report.score}/100, {failures} failure(s), {warnings} warning(s), {infos} info"


def _template_has_filled_seller_values(template_path: Path) -> bool:
    try:
        text = template_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ArticleError(f"販売者テンプレートを読めません: {exc}") from exc
    values, _warnings = parse_commercial_setup_template(text)
    return any(
        [
            bool(values.get("seller_name")),
            bool(values.get("sales_channel_url")),
            bool(values.get("refund_policy_url")),
            bool(values.get("support_contact")),
            values.get("terms_reviewed_bool") is True,
            values.get("support_scope_confirmed_bool") is True,
        ]
    )


def _missing_fields_detail(settings: AppSettings) -> str:
    fields = commercial_setup_missing_fields(settings)
    return f" ({', '.join(fields)})" if fields else ""


def _warnings_detail(warnings: list[str]) -> str:
    unique_warnings = []
    for warning in warnings:
        if warning not in unique_warnings:
            unique_warnings.append(warning)
    return f", warnings {len(unique_warnings)} ({'; '.join(unique_warnings)})" if unique_warnings else ""


def _name_or_none(path: Path | None) -> str:
    return path.name if path else "(not created)"


def _buyer_delivery_contents(report: SalesFinalizeReport) -> list[str]:
    if report.buyer_delivery_package_path and report.buyer_delivery_package_path.exists():
        try:
            with zipfile.ZipFile(report.buyer_delivery_package_path) as archive:
                return sorted(name for name in archive.namelist() if not name.endswith("/"))
        except (OSError, zipfile.BadZipFile):
            return []
    if report.buyer_delivery_dir and report.buyer_delivery_dir.exists():
        return sorted(path.name for path in report.buyer_delivery_dir.iterdir() if path.is_file())
    return []


def _delivery_verification_lines(report: SalesFinalizeReport) -> list[str]:
    paths = [
        ("buyer delivery zip", report.buyer_delivery_package_path),
        ("sales handoff zip", report.sales_handoff_path),
        ("release package", report.release_path),
        ("sales listing package", report.sales_listing_package_path),
    ]
    lines: list[str] = []
    for label, path in paths:
        evidence = _file_evidence(path)
        if evidence:
            lines.append(f"- {label}: {evidence}")
    screenshot_evidence = _directory_evidence(report.sales_screenshot_pack_path)
    if screenshot_evidence:
        lines.append(f"- sales screenshot pack: {screenshot_evidence}")
    listing_evidence = _directory_evidence(report.sales_listing_kit_path)
    if listing_evidence:
        lines.append(f"- sales listing kit: {listing_evidence}")
    return lines


def _write_buyer_delivery_message(
    project_dir: Path,
    *,
    package_path: Path,
    handoff_path: Path,
    release_path: Path,
) -> Path:
    path = _buyer_delivery_message_path(project_dir)
    write_text_atomic(
        path,
        _build_buyer_delivery_message(
            package_path=package_path,
            handoff_path=handoff_path,
            release_path=release_path,
        ),
    )
    return path


def _write_seller_send_checklist(
    project_dir: Path,
    *,
    buyer_package_path: Path | None,
    buyer_message_path: Path | None,
    sales_handoff_path: Path | None,
    release_path: Path | None,
    sales_screenshot_pack_path: Path | None,
    sales_listing_kit_path: Path | None,
    sales_listing_package_path: Path | None,
    acceptance_report_path: Path | None,
    sales_plan_report_path: Path | None,
    sales_evidence_manifest_path: Path | None,
    diagnostic_report_path: Path | None,
    privacy_status: str,
    final_preflight_status: str,
    steps: list[SalesFinalizeStep],
) -> Path:
    path = _seller_send_checklist_path(project_dir)
    write_text_atomic(
        path,
        _build_seller_send_checklist(
            buyer_package_path=buyer_package_path,
            buyer_message_path=buyer_message_path,
            sales_handoff_path=sales_handoff_path,
            release_path=release_path,
            sales_screenshot_pack_path=sales_screenshot_pack_path,
            sales_listing_kit_path=sales_listing_kit_path,
            sales_listing_package_path=sales_listing_package_path,
            acceptance_report_path=acceptance_report_path,
            sales_plan_report_path=sales_plan_report_path,
            sales_evidence_manifest_path=sales_evidence_manifest_path,
            diagnostic_report_path=diagnostic_report_path,
            privacy_status=privacy_status,
            final_preflight_status=final_preflight_status,
            steps=steps,
        ),
    )
    return path


def _build_buyer_delivery_message(
    *,
    package_path: Path,
    handoff_path: Path,
    release_path: Path,
) -> str:
    package_data = package_path.read_bytes()
    package_sha = hashlib.sha256(package_data).hexdigest()
    return (
        "auto-note buyer delivery message / 購入者向け送付文\n\n"
        "Paste-ready message / 貼り付け用文:\n"
        "ご購入ありがとうございます。以下のZIPを添付します。\n\n"
        f"- 添付ZIP: {package_path.name}\n"
        f"- サイズ: {len(package_data)} bytes\n"
        f"- SHA-256: {package_sha}\n\n"
        "ZIPを展開したら、まず START_HERE_FOR_BUYER.txt を開いてください。"
        "その案内に沿って配布ZIPを展開し、START_HERE.txt と shortcuts\\install-auto-note.bat から導入してください。"
        "note.com の自動ログインが安全ではない可能性で止まる場合は、普段使うブラウザでnote.comへログインし、投稿ヘルパーの貼り付け運用をご利用ください。\n\n"
        "困った時は BUYER_SUPPORT_GUIDE.txt を確認し、BUYER_SUPPORT_REQUEST.txt に状況を書いてください。"
        "GUIの ヘルプ > 問い合わせ一式、または `auto-note support --project-dir . --bundle` で作成したZIPと一緒に共有してください。"
        "パスワード、ログインコード、未公開本文全文、支払い情報は送らないでください。\n\n"
        "Seller note / 販売者メモ:\n"
        f"- Buyer delivery ZIP: {package_path.name}\n"
        f"- Source release: {release_path.name}\n"
        f"- Seller evidence ZIP to keep: {handoff_path.name}\n"
        "- Keep this message with your order record.\n"
    )


def _build_seller_send_checklist(
    *,
    buyer_package_path: Path | None,
    buyer_message_path: Path | None,
    sales_handoff_path: Path | None,
    release_path: Path | None,
    sales_screenshot_pack_path: Path | None,
    sales_listing_kit_path: Path | None,
    sales_listing_package_path: Path | None,
    acceptance_report_path: Path | None,
    sales_plan_report_path: Path | None,
    sales_evidence_manifest_path: Path | None,
    diagnostic_report_path: Path | None,
    privacy_status: str,
    final_preflight_status: str,
    steps: list[SalesFinalizeStep],
) -> str:
    warning_steps = [step for step in steps if step.status == "warn"]
    failure_steps = [step for step in steps if step.status == "fail"]
    warning_lines = "\n".join(
        f"- {step.name}: {step.detail}" + (f"\n  next: {step.action}" if step.action else "")
        for step in warning_steps
    )
    failure_lines = "\n".join(
        f"- {step.name}: {step.detail}" + (f"\n  next: {step.action}" if step.action else "")
        for step in failure_steps
    )
    if not warning_lines:
        warning_lines = "- none"
    if not failure_lines:
        failure_lines = "- none"

    return (
        "auto-note seller send checklist / 販売者送付前チェックリスト\n\n"
        "Send to buyer / 購入者へ送るもの\n"
        f"[ ] Attach exactly this ZIP: {_name_or_none(buyer_package_path)}\n"
        f"    {_file_evidence(buyer_package_path) or 'not available'}\n"
        f"[ ] Paste the message from: {_name_or_none(buyer_message_path)}\n"
        "[ ] Tell the buyer to open START_HERE_FOR_BUYER.txt first.\n"
        "[ ] Confirm the marketplace/order attachment name matches the ZIP above.\n\n"
        "Keep as seller evidence / 販売者が保管するもの\n"
        f"[ ] Seller evidence ZIP: {_name_or_none(sales_handoff_path)}\n"
        f"    {_file_evidence(sales_handoff_path) or 'not available'}\n"
        f"[ ] Source release: {_name_or_none(release_path)}\n"
        f"    {_file_evidence(release_path) or 'not available'}\n"
        f"[ ] Sales screenshot pack: {_name_or_none(sales_screenshot_pack_path)}\n"
        f"    {_directory_evidence(sales_screenshot_pack_path) or 'not available'}\n"
        f"[ ] Sales listing kit folder: {_name_or_none(sales_listing_kit_path)}\n"
        f"    {_directory_evidence(sales_listing_kit_path) or 'not available'}\n"
        f"[ ] Sales listing kit ZIP: {_name_or_none(sales_listing_package_path)}\n"
        f"    {_file_evidence(sales_listing_package_path) or 'not available'}\n"
        f"[ ] Acceptance evidence: {_name_or_none(acceptance_report_path)}\n"
        f"[ ] Sales plan evidence: {_name_or_none(sales_plan_report_path)}\n"
        f"[ ] Sales evidence manifest: {_name_or_none(sales_evidence_manifest_path)}\n"
        f"[ ] Diagnostic evidence: {_name_or_none(diagnostic_report_path)}\n\n"
        "Do not send in normal delivery / 通常納品では送らないもの\n"
        "[ ] Do not attach auto-note-sales-handoff-*.zip to the buyer.\n"
        "[ ] Do not attach auto-note-sales-listing-kit-*.zip to the buyer.\n"
        "[ ] Do not attach diagnostic ZIPs unless support asks for them.\n"
        "[ ] Do not attach the whole workspace, .auto-note folder, .venv folder, login data, payment data, passwords, login codes, or full unpublished drafts.\n\n"
        "Verification status / 検証状態\n"
        f"- privacy audit: {privacy_status}\n"
        f"- final preflight: {final_preflight_status}\n\n"
        "Remaining seller actions / 販売者側で残る確認\n"
        f"{warning_lines}\n\n"
        "Blocking issues / 送付前NG\n"
        f"{failure_lines}\n"
    )


def _write_sales_evidence_manifest(report: SalesFinalizeReport) -> Path:
    if report.sales_evidence_manifest_path is None:
        raise OSError("sales evidence manifest path is not set")
    payload = {
        "schema": "auto-note.sales-evidence-manifest.v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "verdict": report.status,
        "artifacts": {
            "buyer_delivery_zip": _manifest_file(report.buyer_delivery_package_path),
            "buyer_delivery_message": _manifest_file(report.buyer_delivery_message_path),
            "buyer_delivery_folder": _manifest_directory(report.buyer_delivery_dir),
            "sales_handoff_zip": _manifest_file(report.sales_handoff_path),
            "release_package": _manifest_file(report.release_path),
            "sales_materials": _manifest_file(report.sales_materials_path),
            "sales_screenshot_pack": _manifest_directory(report.sales_screenshot_pack_path),
            "sales_listing_kit": _manifest_directory(report.sales_listing_kit_path),
            "sales_listing_package": _manifest_file(report.sales_listing_package_path),
            "sales_plan_report": _manifest_file(report.sales_plan_report_path),
            "seller_send_checklist": _manifest_file(report.seller_send_checklist_path),
            "acceptance_report": _manifest_file(report.acceptance_report_path),
            "diagnostic_report": _manifest_file(report.diagnostic_report_path),
        },
        "buyer_delivery_contents": _buyer_delivery_contents(report),
        "checks": [
            {
                "name": step.name,
                "status": step.status,
                "detail": step.detail,
                "action": step.action,
            }
            for step in report.steps
        ],
        "remaining_actions": [
            {"step": step.name, "action": step.action}
            for step in report.steps
            if step.action
        ],
    }
    write_text_atomic(
        report.sales_evidence_manifest_path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return report.sales_evidence_manifest_path


def _manifest_file(path: Path | None) -> dict[str, str | int] | None:
    if path is None:
        return None
    item: dict[str, str | int] = {"file_name": path.name}
    if not path.exists() or not path.is_file():
        item["status"] = "missing"
        return item
    try:
        data = path.read_bytes()
    except OSError:
        item["status"] = "unreadable"
        return item
    item["bytes"] = len(data)
    item["sha256"] = hashlib.sha256(data).hexdigest()
    return item


def _manifest_directory(path: Path | None) -> dict[str, object] | None:
    if path is None:
        return None
    item: dict[str, object] = {"directory_name": path.name}
    if not path.exists() or not path.is_dir():
        item["status"] = "missing"
        return item
    try:
        item["entries"] = sorted(child.relative_to(path).as_posix() for child in path.rglob("*") if child.is_file())
    except OSError:
        item["status"] = "unreadable"
    return item


def _file_evidence(path: Path | None) -> str:
    if path is None or not path.exists() or not path.is_file():
        return ""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    return f"{path.name}, {len(data)} bytes, SHA-256 {hashlib.sha256(data).hexdigest()}"


def _directory_evidence(path: Path | None) -> str:
    if path is None or not path.exists() or not path.is_dir():
        return ""
    try:
        entries = sorted(child.name for child in path.iterdir() if child.is_file())
    except OSError:
        return ""
    return f"{path.name}, {len(entries)} file(s)"
