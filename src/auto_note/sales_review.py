from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
import re

from .article import write_text_atomic
from .commercial_setup import commercial_setup_missing_fields, commercial_setup_warnings
from .paths import unique_path
from .sales_finalize import (
    BuyerSendReadinessReport,
    list_seller_delivery_receipts,
    run_buyer_send_readiness,
)
from .sales_materials import list_sales_materials, verify_sales_materials
from .settings import load_settings


@dataclass(frozen=True)
class SalesReviewCheck:
    name: str
    status: str
    detail: str
    action: str = ""


@dataclass(frozen=True)
class SalesReviewReport:
    project_dir: Path
    status: str
    score: int
    generated_at: datetime
    checks: list[SalesReviewCheck]
    sales_materials_path: Path | None = None
    buyer_delivery_message_path: Path | None = None
    buyer_delivery_package_path: Path | None = None
    seller_delivery_receipt_path: Path | None = None
    report_path: Path | None = None

    @property
    def ok(self) -> bool:
        return self.status != "fail"

    @property
    def has_warnings(self) -> bool:
        return any(check.status == "warn" for check in self.checks)


def run_sales_review(project_dir: Path) -> SalesReviewReport:
    project_dir = project_dir.resolve()
    settings = load_settings(project_dir)
    checks: list[SalesReviewCheck] = []

    missing = commercial_setup_missing_fields(settings)
    warnings = commercial_setup_warnings(settings)
    if missing:
        checks.append(
            SalesReviewCheck(
                "seller profile",
                "fail",
                f"missing {len(missing)} field(s): {', '.join(missing)}",
                "GUIの設定タブ、または `auto-note commercial-setup --help` で販売者情報を保存してください。",
            )
        )
    elif warnings:
        checks.append(
            SalesReviewCheck(
                "seller profile",
                "warn",
                "; ".join(warnings),
                "販売ページURL、返金方針URL、サポート連絡先を公開URL形式で保存してください。",
            )
        )
    else:
        checks.append(SalesReviewCheck("seller profile", "pass", "seller profile is complete"))

    materials_path = _latest_or_none(list_sales_materials(project_dir))
    materials_text = ""
    if materials_path is None:
        checks.append(
            SalesReviewCheck(
                "sales materials",
                "fail",
                "not found",
                "`auto-note sales-materials --project-dir .` で販売素材を作成してください。",
            )
        )
    else:
        material_errors = verify_sales_materials(materials_path, strict=True, project_dir=project_dir)
        if material_errors:
            checks.append(
                SalesReviewCheck(
                    "sales materials",
                    "fail",
                    f"{materials_path.name}: {len(material_errors)} issue(s): {'; '.join(material_errors[:3])}",
                    "`auto-note sales-materials --project-dir .` で販売素材を作り直してください。",
                )
            )
        else:
            checks.append(SalesReviewCheck("sales materials", "pass", f"{materials_path.name} verified"))
        materials_text = _read_text(materials_path)
        checks.extend(_sales_page_copy_checks(materials_text, settings))

    buyer_send = run_buyer_send_readiness(project_dir)
    checks.append(_buyer_send_check(buyer_send))
    checks.extend(_delivery_message_checks(buyer_send.buyer_delivery_message_path))

    receipt_path = _latest_or_none(list_seller_delivery_receipts(project_dir))
    if receipt_path is None:
        checks.append(
            SalesReviewCheck(
                "seller delivery receipt",
                "warn",
                "not saved yet",
                "`auto-note sales-finalize --project-dir . --delivery-receipt` で注文管理用の納品記録を保存してください。",
            )
        )
    else:
        checks.append(SalesReviewCheck("seller delivery receipt", "pass", f"{receipt_path.name} saved"))

    status = _overall_status(checks)
    return SalesReviewReport(
        project_dir=project_dir,
        status=status,
        score=_score(checks),
        generated_at=datetime.now(),
        checks=checks,
        sales_materials_path=materials_path,
        buyer_delivery_message_path=buyer_send.buyer_delivery_message_path,
        buyer_delivery_package_path=buyer_send.buyer_delivery_package_path,
        seller_delivery_receipt_path=receipt_path,
    )


def format_sales_review(report: SalesReviewReport) -> str:
    counts = {
        "pass": sum(1 for check in report.checks if check.status == "pass"),
        "info": sum(1 for check in report.checks if check.status == "info"),
        "warn": sum(1 for check in report.checks if check.status == "warn"),
        "fail": sum(1 for check in report.checks if check.status == "fail"),
    }
    verdict = {
        "pass": "READY",
        "warn": "NEEDS REVIEW",
        "fail": "BLOCKED",
    }.get(report.status, report.status.upper())
    lines = [
        "Sales final review / 販売ページ・納品最終レビュー",
        f"Generated: {report.generated_at:%Y-%m-%d %H:%M:%S}",
        f"Verdict: {verdict}",
        f"Score: {report.score}/100",
        f"Checks: {counts['pass']} OK, {counts['info']} INFO, {counts['warn']} WARN, {counts['fail']} NG",
        "",
        "Artifacts / 確認対象",
        f"- sales materials: {_name_or_none(report.sales_materials_path)}",
        f"- buyer delivery message: {_name_or_none(report.buyer_delivery_message_path)}",
        f"- buyer delivery zip: {_name_or_none(report.buyer_delivery_package_path)}",
        f"- seller delivery receipt: {_name_or_none(report.seller_delivery_receipt_path)}",
        "",
        "Checks / 確認結果",
    ]
    next_actions: list[str] = []
    for check in report.checks:
        label = {"pass": "OK", "info": "INFO", "warn": "WARN", "fail": "NG"}.get(
            check.status,
            check.status.upper(),
        )
        lines.append(f"[{label}] {check.name}: {check.detail}")
        if check.action:
            lines.append(f"  next: {check.action}")
            next_actions.append(f"- {check.name}: {check.action}")
    if next_actions:
        lines.extend(["", "Next actions / 次の操作", *next_actions])
    lines.extend(
        [
            "",
            "Seller confirmation / 販売者の最終目視",
            "[ ] 販売ページの納品物名が購入者向けZIP名と一致している",
            "[ ] 決済後メッセージへ貼る文面が buyer delivery message と一致している",
            "[ ] 返金条件、サポート範囲、ログイン制限の説明が販売ページと利用条件で矛盾していない",
            "[ ] 販売者用ZIP、診断ZIP、.auto-note、.venv、支払い情報、ログイン情報を購入者へ送らない",
        ]
    )
    if report.report_path is not None:
        lines.extend(["", f"saved: {report.report_path.name}"])
    return "\n".join(lines)


def write_sales_review_report(
    project_dir: Path,
    *,
    report: SalesReviewReport | None = None,
) -> Path:
    project_dir = project_dir.resolve()
    report = report or run_sales_review(project_dir)
    sales_dir = project_dir / ".auto-note" / "sales"
    sales_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(sales_dir / f"sales-review-{report.generated_at:%Y%m%d-%H%M%S}.txt")
    report = replace(report, report_path=path)
    write_text_atomic(path, format_sales_review(report) + "\n")
    return path


def list_sales_review_reports(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(sales_dir.glob("sales-review-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def has_sales_review_blockers(report: SalesReviewReport, *, strict: bool = False) -> bool:
    if report.status == "fail":
        return True
    return strict and report.status == "warn"


def _sales_page_copy_checks(text: str, settings) -> list[SalesReviewCheck]:
    checks: list[SalesReviewCheck] = []
    if not text:
        return checks
    expected_values = [
        ("sales page URL", settings.sales_channel_url.strip(), "販売素材に販売ページURLを反映してください。"),
        ("refund policy URL", settings.refund_policy_url.strip(), "販売素材に返金方針URLを反映してください。"),
        ("support contact", settings.support_contact.strip(), "販売素材にサポート連絡先を反映してください。"),
    ]
    missing_values = [name for name, value, _action in expected_values if value and value not in text]
    if missing_values:
        checks.append(
            SalesReviewCheck(
                "listing/settings alignment",
                "warn",
                "latest sales materials may be stale; missing " + ", ".join(missing_values),
                "`auto-note sales-materials --project-dir .` で販売素材を作り直してください。",
            )
        )
    else:
        checks.append(SalesReviewCheck("listing/settings alignment", "pass", "seller URLs are reflected"))

    required_copy = {
        "note official API limitation": ("note公式API", "note公式APIではない説明を販売ページに入れてください。"),
        "login bypass limitation": ("ログイン回避", "ログイン回避ツールではない説明を販売ページに入れてください。"),
        "support scope": ("Support Scope", "販売ページにサポート範囲を明記してください。"),
        "refund summary": ("Refund Policy Summary", "販売ページに返金方針要約を入れてください。"),
        "buyer first steps": ("Buyer First 10 Minutes", "購入者の最初の操作を販売素材に入れてください。"),
    }
    missing_copy = [name for name, (marker, _action) in required_copy.items() if marker not in text]
    if missing_copy:
        actions = [required_copy[name][1] for name in missing_copy[:2]]
        checks.append(
            SalesReviewCheck(
                "listing promise copy",
                "warn",
                "missing " + ", ".join(missing_copy),
                " ".join(actions),
            )
        )
    else:
        checks.append(SalesReviewCheck("listing promise copy", "pass", "limits, support, refund, and first steps are present"))

    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text):
        checks.append(
            SalesReviewCheck(
                "listing privacy",
                "warn",
                "raw email address found",
                "販売素材には公開サポートURLを使い、メール直書きは販売ページ側で必要時だけ管理してください。",
            )
        )
    else:
        checks.append(SalesReviewCheck("listing privacy", "pass", "no raw email address found"))
    return checks


def _buyer_send_check(report: BuyerSendReadinessReport) -> SalesReviewCheck:
    failures = [check for check in report.checks if check.status == "fail"]
    warnings = [check for check in report.checks if check.status == "warn"]
    if failures:
        return SalesReviewCheck(
            "buyer send readiness",
            "fail",
            f"{len(failures)} blocking issue(s): {failures[0].name}: {failures[0].detail}",
            "`auto-note sales-finalize --project-dir . --send-check --send-check-report` のNGを直してください。",
        )
    if warnings:
        return SalesReviewCheck(
            "buyer send readiness",
            "warn",
            f"{len(warnings)} warning(s): {warnings[0].name}: {warnings[0].detail}",
            "送付前チェックのWARNを確認してください。",
        )
    package = _name_or_none(report.buyer_delivery_package_path)
    message = _name_or_none(report.buyer_delivery_message_path)
    return SalesReviewCheck("buyer send readiness", "pass", f"{message} and {package} match")


def _delivery_message_checks(message_path: Path | None) -> list[SalesReviewCheck]:
    if message_path is None:
        return []
    text = _read_text(message_path)
    missing_parts = [
        part
        for part in ("添付ZIP", "SHA-256", "START_HERE_FOR_BUYER.txt", "パスワード", "支払い情報")
        if part not in text
    ]
    if missing_parts:
        return [
            SalesReviewCheck(
                "delivery message copy",
                "warn",
                "missing " + ", ".join(missing_parts),
                "`auto-note sales-finalize --project-dir .` で購入者向け送付文を再生成してください。",
            )
        ]
    return [SalesReviewCheck("delivery message copy", "pass", "attachment, checksum, first file, and do-not-send guidance are present")]


def _latest_or_none(paths: list[Path]) -> Path | None:
    return paths[0] if paths else None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _name_or_none(path: Path | None) -> str:
    return path.name if path is not None else "(none)"


def _overall_status(checks: list[SalesReviewCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "warn" for check in checks):
        return "warn"
    return "pass"


def _score(checks: list[SalesReviewCheck]) -> int:
    if not checks:
        return 0
    value = 0.0
    for check in checks:
        if check.status in {"pass", "info"}:
            value += 1.0
        elif check.status == "warn":
            value += 0.65
    return max(0, min(100, round(100 * value / len(checks))))
