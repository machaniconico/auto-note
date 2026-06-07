from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
import hashlib
import json
import zipfile

from .article import write_text_atomic
from .commercial import CommercialReadinessReport, run_commercial_readiness
from .paths import unique_path
from .release import list_releases, verify_release_package
from .sales_handoff import (
    list_buyer_delivery_packages,
    list_sales_handoffs,
    verify_buyer_delivery_package,
    verify_sales_handoff,
)
from .sales_materials import list_sales_materials, verify_sales_materials


@dataclass(frozen=True)
class SalesPlanStep:
    title: str
    status: str
    detail: str
    action: str
    gui: str = ""
    command: str = ""
    category: str = "tool"
    score_penalty: int = 0


@dataclass(frozen=True)
class SalesPlanReport:
    project_dir: Path
    status: str
    score: int
    generated_at: datetime
    readiness: CommercialReadinessReport
    latest_release: Path | None
    latest_handoff: Path | None
    latest_buyer_delivery_package: Path | None
    latest_materials: Path | None
    buyer_delivery_status: str
    buyer_delivery_detail: str
    steps: list[SalesPlanStep]

    @property
    def ok(self) -> bool:
        return self.status == "READY"

    @property
    def seller_remaining(self) -> int:
        return sum(1 for step in self.steps if step.category == "seller" and step.status in {"blocker", "warning"})

    @property
    def tool_remaining(self) -> int:
        return sum(1 for step in self.steps if step.category == "tool" and step.status in {"blocker", "warning"})


def build_sales_plan(project_dir: Path) -> SalesPlanReport:
    project_dir = project_dir.resolve()
    readiness = run_commercial_readiness(project_dir)
    releases = list_releases(project_dir)
    handoffs = list_sales_handoffs(project_dir)
    buyer_delivery_packages = list_buyer_delivery_packages(project_dir)
    materials = list_sales_materials(project_dir)
    latest_release = releases[0] if releases else None
    latest_handoff = handoffs[0] if handoffs else None
    latest_buyer_delivery_package = buyer_delivery_packages[0] if buyer_delivery_packages else None
    latest_materials = materials[0] if materials else None
    steps: list[SalesPlanStep] = []

    readiness_items = {item.name: item for item in readiness.items}
    for name, title, gui, command, category in (
        (
            "配布ZIP",
            "最新配布ZIPを作成・検証する",
            "診断 > 出荷ZIP作成",
            "auto-note preflight --project-dir . --create-release",
            "tool",
        ),
        (
            "プライバシー監査",
            "送付前のプライバシーNGをなくす",
            "診断 > プライバシー監査",
            "auto-note privacy-audit --project-dir .",
            "tool",
        ),
        (
            "受入チェック",
            "購入者目線の受入チェックを保存する",
            "診断 > 受入保存",
            "auto-note acceptance --project-dir . --create --gui-smoke --smoke-helper --report",
            "tool",
        ),
        (
            "販売者プロフィール",
            "販売者情報を保存する",
            "設定 > 販売者/屋号",
            "auto-note commercial-setup --project-dir . --seller-name \"Your Shop\" --sales-url \"https://example.com\" --refund-url \"https://example.com/refund\"",
            "seller",
        ),
        (
            "利用条件/商用方針",
            "利用条件と商用方針を最終レビューする",
            "設定 > 利用条件/商用方針を販売前に確認済み",
            "auto-note commercial-setup --project-dir . --terms-reviewed",
            "seller",
        ),
        (
            "販売最終確認",
            "販売ページとサポート範囲の最終確認を保存する",
            "設定 > サポート範囲と返金条件を販売ページに明記済み",
            "auto-note commercial-setup --project-dir . --terms-reviewed --support-scope-confirmed",
            "seller",
        ),
        (
            "サポート連絡先",
            "購入者向けサポート連絡先を保存する",
            "設定 > サポート連絡先",
            "auto-note commercial-setup --project-dir . --support-contact \"https://example.com/support\"",
            "seller",
        ),
        (
            "インストール導線",
            "実機インストール確認を行う",
            "診断 > 出荷前チェック",
            "auto-note preflight --project-dir . --install-smoke --gui-smoke",
            "tool",
        ),
    ):
        item = readiness_items.get(name)
        if item and item.status in {"fail", "warn"}:
            steps.append(
                SalesPlanStep(
                    title=title,
                    status="blocker" if item.status == "fail" else "warning",
                    detail=item.detail,
                    action=item.action or title,
                    gui=gui,
                    command=command,
                    category=category,
                )
            )

    release_errors = verify_release_package(latest_release) if latest_release else ["release package not found"]
    handoff_errors = verify_sales_handoff(latest_handoff) if latest_handoff else ["sales handoff not found"]
    buyer_package_errors = (
        verify_buyer_delivery_package(latest_buyer_delivery_package)
        if latest_buyer_delivery_package
        else ["buyer delivery zip not found"]
    )
    handoff_release_name = _handoff_release_name(latest_handoff) if latest_handoff and not handoff_errors else ""
    buyer_package_release_name = (
        _buyer_delivery_package_release_name(latest_buyer_delivery_package)
        if latest_buyer_delivery_package and not buyer_package_errors
        else ""
    )
    latest_release_name = latest_release.name if latest_release else ""
    buyer_delivery_status, buyer_delivery_detail = _buyer_delivery_readiness(
        latest_release=latest_release,
        latest_handoff=latest_handoff,
        latest_buyer_delivery_package=latest_buyer_delivery_package,
        latest_release_name=latest_release_name,
        buyer_package_release_name=buyer_package_release_name,
        release_errors=release_errors,
        handoff_errors=handoff_errors,
        buyer_package_errors=buyer_package_errors,
    )
    if handoff_errors:
        steps.append(
            SalesPlanStep(
                title="販売用一式ZIPを作成する",
                status="blocker" if release_errors else "warning",
                detail=handoff_errors[0],
                action="最新配布ZIP、販売準備、監査、購入者向け納品文をまとめた販売者用証跡ZIPを作ってください。",
                gui="診断 > 販売一式作成",
                command="auto-note sales-handoff --project-dir .",
                category="tool",
                score_penalty=18 if release_errors else 7,
            )
        )
    elif latest_release_name and handoff_release_name and handoff_release_name != latest_release_name:
        steps.append(
            SalesPlanStep(
                title="販売用一式ZIPを最新配布ZIPで作り直す",
                status="warning",
                detail=f"handoff has {handoff_release_name}, latest release is {latest_release_name}",
                action="配布ZIPを作り直した後は、販売用一式ZIPも作り直してください。",
                gui="診断 > 販売一式作成",
                command="auto-note sales-handoff --project-dir .",
                category="tool",
                score_penalty=7,
            )
        )
    elif buyer_package_errors:
        steps.append(
            SalesPlanStep(
                title="購入者向けZIPを作成・検証する",
                status="blocker" if latest_buyer_delivery_package else "warning",
                detail=buyer_package_errors[0],
                action="購入者にそのまま添付できる auto-note-buyer-delivery-*.zip を作り直してください。",
                gui="診断 > 販売一括作成",
                command="auto-note sales-finalize --project-dir . --apply-latest-template",
                category="tool",
                score_penalty=18 if latest_buyer_delivery_package is None else 7,
            )
        )
    elif latest_release_name and buyer_package_release_name and buyer_package_release_name != latest_release_name:
        steps.append(
            SalesPlanStep(
                title="購入者向けZIPを最新配布ZIPで作り直す",
                status="warning",
                detail=f"buyer delivery has {buyer_package_release_name}, latest release is {latest_release_name}",
                action="購入者に添付するZIPを最新配布ZIPで作り直してください。",
                gui="診断 > 販売一括作成",
                command="auto-note sales-finalize --project-dir . --apply-latest-template",
                category="tool",
                score_penalty=7,
            )
        )

    if latest_materials is None:
        steps.append(
            SalesPlanStep(
                title="販売素材Markdownを作成する",
                status="warning",
                detail="sales materials not found",
                action="販売ページ文案、納品メッセージ、FAQ、サポート範囲、返金方針要約を作成してください。",
                gui="診断 > 販売素材作成",
                command="auto-note sales-materials --project-dir .",
                category="tool",
                score_penalty=7,
            )
        )
    elif latest_release and latest_materials.stat().st_mtime < latest_release.stat().st_mtime:
        steps.append(
            SalesPlanStep(
                title="販売素材Markdownを最新配布ZIPで作り直す",
                status="warning",
                detail=f"{latest_materials.name} is older than {latest_release.name}",
                action="最新配布ZIPのファイル名と納品文を反映した販売素材を作り直してください。",
                gui="診断 > 販売素材作成",
                command="auto-note sales-materials --project-dir .",
                category="tool",
                score_penalty=7,
            )
        )
    else:
        material_errors = verify_sales_materials(latest_materials, strict=True, project_dir=project_dir)
        if material_errors:
            steps.append(
                SalesPlanStep(
                    title="販売素材Markdownを最終補完する",
                    status="warning",
                    detail=material_errors[0],
                    action="販売者情報、販売ページURL、返金方針、サポート連絡先、最新配布ZIP名が文案へ反映されているか確認してください。",
                    gui="診断 > 販売素材検証",
                    command=f'auto-note sales-materials --project-dir . --verify "{_project_relative_path(project_dir, latest_materials)}" --strict',
                    category="seller",
                )
            )

    if not steps:
        steps.append(
            SalesPlanStep(
                title="販売直前の最終確認",
                status="info",
                detail="販売準備、配布ZIP、販売用一式ZIP、購入者向けZIPはそろっています。",
                action="販売ページ、価格、返金条件、サポート範囲を実際の掲載内容と照合してください。",
                gui="診断 > 販売一式検証",
                command="auto-note sales-handoff --project-dir . --verify-buyer-package <購入者向けZIP>",
                category="seller",
            )
        )

    status = _overall_status(steps, readiness)
    score = _score(readiness, steps)
    return SalesPlanReport(
        project_dir=project_dir,
        status=status,
        score=score,
        generated_at=datetime.now(),
        readiness=readiness,
        latest_release=latest_release,
        latest_handoff=latest_handoff,
        latest_buyer_delivery_package=latest_buyer_delivery_package,
        latest_materials=latest_materials,
        buyer_delivery_status=buyer_delivery_status,
        buyer_delivery_detail=buyer_delivery_detail,
        steps=steps,
    )


def format_sales_plan(report: SalesPlanReport) -> str:
    lines = [
        "Sales plan / 販売ナビ",
        f"Generated: {report.generated_at:%Y-%m-%d %H:%M:%S}",
        f"Verdict: {report.status}",
        f"Score: {report.score}/100",
        f"Commercial readiness: {report.readiness.status}, {report.readiness.score}/100",
        f"Buyer delivery readiness: {report.buyer_delivery_status} - {report.buyer_delivery_detail}",
        f"Seller setup remaining: {report.seller_remaining}",
        f"Tool/artifact actions remaining: {report.tool_remaining}",
        f"Upload guidance: {_upload_guidance(report)}",
        f"Latest release: {report.latest_release.name if report.latest_release else '(none)'}",
        f"Latest sales handoff: {report.latest_handoff.name if report.latest_handoff else '(none)'}",
        f"Latest buyer delivery zip: {report.latest_buyer_delivery_package.name if report.latest_buyer_delivery_package else '(none)'}",
        f"Latest sales materials: {report.latest_materials.name if report.latest_materials else '(none)'}",
        "",
    ]
    for index, step in enumerate(report.steps, start=1):
        label = {
            "blocker": "NG",
            "warning": "WARN",
            "info": "INFO",
            "done": "OK",
        }.get(step.status, step.status.upper())
        lines.append(f"[{label}] {index}. {step.title}: {step.detail}")
        lines.append(f"  next: {step.action}")
        if step.gui:
            lines.append(f"  gui: {step.gui}")
        if step.command:
            lines.append(f"  cli: {step.command}")
    return "\n".join(lines)


def write_sales_plan_report(project_dir: Path, *, report: SalesPlanReport | None = None) -> Path:
    project_dir = project_dir.resolve()
    report = report or build_sales_plan(project_dir)
    sales_dir = project_dir / ".auto-note" / "sales"
    sales_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(sales_dir / f"sales-plan-{report.generated_at:%Y%m%d-%H%M%S}.txt")
    write_text_atomic(path, format_sales_plan(report) + "\n")
    return path


def list_sales_plan_reports(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(sales_dir.glob("sales-plan-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def has_sales_plan_blockers(report: SalesPlanReport, *, strict: bool = False) -> bool:
    if any(step.status == "blocker" for step in report.steps):
        return True
    return strict and any(step.status == "warning" for step in report.steps)


def _handoff_release_name(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        with zipfile.ZipFile(path) as archive:
            raw = json.loads(archive.read("SALES_HANDOFF_MANIFEST.json").decode("utf-8"))
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if not isinstance(raw, dict):
        return ""
    value = raw.get("release_package")
    return value if isinstance(value, str) else ""


def _buyer_delivery_package_release_name(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        with zipfile.ZipFile(path) as archive:
            release_entries = [
                name
                for name in archive.namelist()
                if PurePosixPath(name).parent == PurePosixPath(".")
                and PurePosixPath(name).name.startswith("auto-note-release-")
                and PurePosixPath(name).suffix.casefold() == ".zip"
            ]
    except (OSError, zipfile.BadZipFile):
        return ""
    if len(release_entries) != 1:
        return ""
    return PurePosixPath(release_entries[0]).name


def _buyer_delivery_readiness(
    *,
    latest_release: Path | None,
    latest_handoff: Path | None,
    latest_buyer_delivery_package: Path | None,
    latest_release_name: str,
    buyer_package_release_name: str,
    release_errors: list[str],
    handoff_errors: list[str],
    buyer_package_errors: list[str],
) -> tuple[str, str]:
    if latest_release is None:
        return "BLOCKED", "release package not found"
    if release_errors:
        return "BLOCKED", release_errors[0]
    if latest_handoff is None:
        return "BLOCKED", "sales handoff not found"
    if handoff_errors:
        return "BLOCKED", handoff_errors[0]
    if latest_buyer_delivery_package is None:
        return "BLOCKED", "buyer delivery zip not found"
    if buyer_package_errors:
        return "BLOCKED", buyer_package_errors[0]
    if latest_release_name and buyer_package_release_name and buyer_package_release_name != latest_release_name:
        return "NEEDS REFRESH", f"buyer delivery has {buyer_package_release_name}, latest release is {latest_release_name}"
    try:
        data = latest_buyer_delivery_package.read_bytes()
    except OSError as exc:
        return "BLOCKED", f"{latest_buyer_delivery_package.name}: unreadable ({exc})"
    digest = hashlib.sha256(data).hexdigest()
    return "READY", f"{latest_buyer_delivery_package.name}, {len(data)} bytes, SHA-256 {digest}"


def _overall_status(steps: list[SalesPlanStep], readiness: CommercialReadinessReport) -> str:
    if readiness.status == "fail" or any(step.status == "blocker" for step in steps):
        return "BLOCKED"
    if readiness.status == "warn" or any(step.status == "warning" for step in steps):
        return "NEEDS ATTENTION"
    return "READY"


def _score(readiness: CommercialReadinessReport, steps: list[SalesPlanStep]) -> int:
    penalty = sum(step.score_penalty for step in steps)
    return max(0, min(100, readiness.score - penalty))


def _upload_guidance(report: SalesPlanReport) -> str:
    if report.tool_remaining:
        return f"HOLD - tool/artifact actions remain: {report.tool_remaining}"
    if report.buyer_delivery_status != "READY":
        return f"HOLD - buyer delivery is {report.buyer_delivery_status}"
    if report.seller_remaining:
        return f"HOLD - seller setup remains: {report.seller_remaining}"
    return "READY - buyer delivery ZIP can be uploaded after final sales-page review"


def _project_relative_path(project_dir: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_dir.resolve()))
    except ValueError:
        return path.name
