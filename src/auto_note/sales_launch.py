from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
import hashlib
from pathlib import Path

from .article import write_text_atomic
from .paths import unique_path
from .sales_finalize import list_sales_evidence_manifests, list_seller_delivery_receipts
from .sales_review import SalesReviewReport, run_sales_review
from .settings import load_settings


@dataclass(frozen=True)
class SalesLaunchCheck:
    name: str
    status: str
    detail: str
    action: str = ""


@dataclass(frozen=True)
class MarketplaceLaunchProfile:
    name: str
    source: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class SalesLaunchReport:
    project_dir: Path
    status: str
    score: int
    generated_at: datetime
    checks: list[SalesLaunchCheck]
    sales_review: SalesReviewReport
    marketplace: MarketplaceLaunchProfile
    report_path: Path | None = None

    @property
    def ok(self) -> bool:
        return self.status != "fail"

    @property
    def has_warnings(self) -> bool:
        return any(check.status == "warn" for check in self.checks)


def run_sales_launch_check(project_dir: Path) -> SalesLaunchReport:
    project_dir = project_dir.resolve()
    settings = load_settings(project_dir)
    review = run_sales_review(project_dir)
    marketplace = _marketplace_profile_for_url(settings.sales_channel_url)
    checks: list[SalesLaunchCheck] = []

    checks.append(_review_gate_check(review))
    checks.append(_marketplace_url_check(settings.sales_channel_url))
    checks.append(_delivery_message_checkout_check(review))
    checks.append(_policy_alignment_check(review, settings))
    checks.append(_seller_evidence_check(project_dir))
    checks.append(
        SalesLaunchCheck(
            "manual marketplace preview",
            "info",
            "final click/preview depends on the marketplace or checkout service",
            "販売ページのプレビュー、決済後メッセージ欄、添付ZIP欄を実画面で確認してください。",
        )
    )

    status = _overall_status(checks)
    return SalesLaunchReport(
        project_dir=project_dir,
        status=status,
        score=_score(checks),
        generated_at=datetime.now(),
        checks=checks,
        sales_review=review,
        marketplace=marketplace,
    )


def format_sales_launch_checklist(report: SalesLaunchReport) -> str:
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
    review = report.sales_review
    lines = [
        "Sales launch checklist / 販売直前チェック",
        f"Generated: {report.generated_at:%Y-%m-%d %H:%M:%S}",
        f"Verdict: {verdict}",
        f"Score: {report.score}/100",
        f"Checks: {counts['pass']} OK, {counts['info']} INFO, {counts['warn']} WARN, {counts['fail']} NG",
        "",
        "Artifacts / 販売直前に見るもの",
        f"- sales materials: {_name_or_none(review.sales_materials_path)}",
        f"- buyer delivery message: {_name_or_none(review.buyer_delivery_message_path)}",
        f"- buyer delivery zip: {_name_or_none(review.buyer_delivery_package_path)}",
        f"- seller delivery receipt: {_name_or_none(review.seller_delivery_receipt_path)}",
        "",
        "Automated checks / 自動確認",
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
            "Marketplace launch confirmation / 販売ページ公開前の目視",
            "[ ] 販売ページの商品名、価格、更新日、対応OS、納品ZIP名が最新の販売素材と一致している",
            "[ ] 決済後メッセージ欄へ buyer delivery message の本文を貼り付けた",
            "[ ] 添付または送付対象は buyer delivery zip だけにした",
            "[ ] 販売者用ZIP、診断ZIP、.auto-note、.venv、ログイン情報、支払い情報を送付対象から外した",
            "[ ] 返金条件、ライセンス、サポート範囲が販売ページ、README、利用条件で矛盾していない",
            "[ ] 販売ページのプレビューまたはテスト購入で、購入者が最初に開くファイルまで確認した",
            "",
            f"Platform-specific launch checks / 販売先別チェック: {report.marketplace.name}",
            f"source: {report.marketplace.source}",
            *[f"[ ] {item}" for item in report.marketplace.items],
            "",
            "Seller note / 販売者メモ",
            "- This checklist is seller-only evidence. Do not attach it to buyer delivery or public support requests.",
            "- Keep the seller delivery receipt with the marketplace order record after sending.",
        ]
    )
    if report.report_path is not None:
        lines.extend(["", f"saved: {report.report_path.name}"])
    return "\n".join(lines)


def write_sales_launch_checklist(
    project_dir: Path,
    *,
    report: SalesLaunchReport | None = None,
) -> Path:
    project_dir = project_dir.resolve()
    report = report or run_sales_launch_check(project_dir)
    sales_dir = project_dir / ".auto-note" / "sales"
    sales_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(sales_dir / f"sales-launch-checklist-{report.generated_at:%Y%m%d-%H%M%S}.txt")
    saved_report = replace(report, report_path=path)
    write_text_atomic(path, format_sales_launch_checklist(saved_report) + "\n")
    return path


def list_sales_launch_checklists(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(sales_dir.glob("sales-launch-checklist-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def has_sales_launch_blockers(report: SalesLaunchReport, *, strict: bool = False) -> bool:
    if report.status == "fail":
        return True
    return strict and report.status == "warn"


def _review_gate_check(report: SalesReviewReport) -> SalesLaunchCheck:
    if report.status == "fail":
        return SalesLaunchCheck(
            "sales final review",
            "fail",
            f"sales-review is blocked, score {report.score}/100",
            "`auto-note sales-review --project-dir .` のNG項目を先に直してください。",
        )
    if report.status == "warn":
        return SalesLaunchCheck(
            "sales final review",
            "warn",
            f"sales-review has warnings, score {report.score}/100",
            "販売ページに載せる前にWARNの内容を販売者判断で確認してください。",
        )
    return SalesLaunchCheck("sales final review", "pass", f"sales-review ready, score {report.score}/100")


def _marketplace_url_check(value: str) -> SalesLaunchCheck:
    url = value.strip()
    if not url:
        return SalesLaunchCheck(
            "marketplace listing URL",
            "fail",
            "sales page URL is missing",
            "GUIの設定タブ、または `auto-note commercial-setup --sales-url` で販売ページURLを保存してください。",
        )
    if not url.startswith(("https://", "http://")):
        return SalesLaunchCheck(
            "marketplace listing URL",
            "warn",
            "sales page URL is not a web URL",
            "販売ページ、決済ページ、またはマーケットプレイス表示URLを公開URL形式で保存してください。",
        )
    if "example.com" in url.lower():
        return SalesLaunchCheck(
            "marketplace listing URL",
            "warn",
            "demo URL is still saved",
            "実際の販売ページURLへ差し替えてから販売直前チェックを保存してください。",
        )
    return SalesLaunchCheck("marketplace listing URL", "pass", "public sales URL is saved")


def _marketplace_profile_for_url(value: str) -> MarketplaceLaunchProfile:
    url = value.strip().lower()
    if "note.com" in url:
        return MarketplaceLaunchProfile(
            "note paid article / note有料記事",
            "inferred from sales URL",
            (
                "有料エリアまたは購入後に見える本文へ、購入者向け送付文のZIP名とSHA-256を貼り付けた",
                "外部ダウンロードURLを使う場合は、権限、期限、差し替え予定、購入者だけが読める導線を確認した",
                "無料エリアには購入者向けZIP、販売者用ZIP、診断ZIP、秘密URL、注文管理メモを載せていない",
                "プレビューまたはテスト購入で、購入後に最初に開く案内まで到達できることを確認した",
            ),
        )
    if "booth.pm" in url:
        return MarketplaceLaunchProfile(
            "BOOTH",
            "inferred from sales URL",
            (
                "商品ファイル欄または購入後案内に、最新のbuyer delivery zipだけを設定した",
                "商品説明、利用条件、返金/サポート範囲、対応OSが販売素材と矛盾していない",
                "販売者用ZIP、診断ZIP、.auto-note、.venv、ログイン情報を商品ファイルに含めていない",
                "非公開プレビューまたはテスト購入相当の確認で、購入者がSTART_HERE_FOR_BUYER.txtへ進めることを確認した",
            ),
        )
    if "gumroad.com" in url:
        return MarketplaceLaunchProfile(
            "Gumroad",
            "inferred from sales URL",
            (
                "Product filesには最新のbuyer delivery zipだけを登録した",
                "Receipt/content messageに購入者向け送付文のZIP名、サイズ、SHA-256を反映した",
                "古いバージョンのファイルや販売者用証跡ファイルを公開側に残していない",
                "購入後プレビューまたはテスト購入で、ダウンロードファイル名と送付文が一致することを確認した",
            ),
        )
    if "stores.jp" in url:
        return MarketplaceLaunchProfile(
            "STORES",
            "inferred from sales URL",
            (
                "デジタル納品または購入後メッセージに、最新のbuyer delivery zipと送付文を設定した",
                "商品説明、注意事項、返金/サポート範囲、対応OSが販売素材と矛盾していない",
                "販売者用ZIP、診断ZIP、注文管理メモを購入者へ見える場所に置いていない",
                "購入後メールまたはダウンロード画面で、ZIP名とSHA-256が送付文と一致することを確認した",
            ),
        )
    return MarketplaceLaunchProfile(
        "generic marketplace / 汎用販売ページ",
        "default checklist",
        (
            "販売ページの商品説明、価格、対応OS、納品物、サポート範囲を販売素材と照合した",
            "決済後メッセージ、自動返信、または納品欄へ購入者向け送付文を貼り付けた",
            "添付または送付対象は最新のbuyer delivery zipだけにした",
            "公開前プレビューまたはテスト購入で、購入者が最初に開くファイルまで確認した",
        ),
    )


def _delivery_message_checkout_check(report: SalesReviewReport) -> SalesLaunchCheck:
    message_path = report.buyer_delivery_message_path
    package_path = report.buyer_delivery_package_path
    if message_path is None or package_path is None:
        return SalesLaunchCheck(
            "checkout delivery message",
            "fail",
            "buyer delivery message or buyer ZIP is missing",
            "`auto-note sales-finalize --project-dir .` で購入者向けZIPと送付文を作成してください。",
        )
    message_text = _read_text(message_path)
    if not message_text:
        return SalesLaunchCheck(
            "checkout delivery message",
            "fail",
            f"{message_path.name} is unreadable or empty",
            "購入者向け送付文を作り直してください。",
        )
    missing: list[str] = []
    if package_path.name not in message_text:
        missing.append("ZIP name")
    package_sha = _sha256(package_path)
    if package_sha and package_sha not in message_text:
        missing.append("SHA-256")
    if missing:
        return SalesLaunchCheck(
            "checkout delivery message",
            "warn",
            f"{message_path.name} may not include latest {', '.join(missing)}",
            "`auto-note sales-finalize --project-dir .` で送付文を作り直し、決済後メッセージ欄へ貼り直してください。",
        )
    return SalesLaunchCheck(
        "checkout delivery message",
        "pass",
        f"{message_path.name} includes latest ZIP name and SHA-256",
    )


def _policy_alignment_check(report: SalesReviewReport, settings) -> SalesLaunchCheck:
    text = _read_text(report.sales_materials_path)
    expected = [
        ("refund policy URL", settings.refund_policy_url.strip()),
        ("support contact", settings.support_contact.strip()),
    ]
    missing = [name for name, value in expected if value and value not in text]
    if missing:
        return SalesLaunchCheck(
            "refund/support display alignment",
            "warn",
            "latest sales materials may not include " + ", ".join(missing),
            "`auto-note sales-materials --project-dir .` で販売素材を作り直し、販売ページの表示へ反映してください。",
        )
    if not text:
        return SalesLaunchCheck(
            "refund/support display alignment",
            "fail",
            "sales materials are missing",
            "`auto-note sales-materials --project-dir .` で販売素材を作成してください。",
        )
    return SalesLaunchCheck("refund/support display alignment", "pass", "refund and support values are reflected")


def _seller_evidence_check(project_dir: Path) -> SalesLaunchCheck:
    manifests = list_sales_evidence_manifests(project_dir)
    receipts = list_seller_delivery_receipts(project_dir)
    if not manifests and not receipts:
        return SalesLaunchCheck(
            "seller-only evidence",
            "warn",
            "sales evidence manifest and seller delivery receipt are missing",
            "`auto-note sales-finalize --project-dir .` と `auto-note sales-finalize --project-dir . --delivery-receipt` を実行してください。",
        )
    if not manifests:
        return SalesLaunchCheck(
            "seller-only evidence",
            "warn",
            "sales evidence manifest is missing",
            "`auto-note sales-finalize --project-dir .` で販売証跡JSONを作成してください。",
        )
    if not receipts:
        return SalesLaunchCheck(
            "seller-only evidence",
            "warn",
            "seller delivery receipt is not saved yet",
            "`auto-note sales-finalize --project-dir . --delivery-receipt` で注文管理用の記録を保存してください。",
        )
    return SalesLaunchCheck("seller-only evidence", "pass", f"{manifests[0].name} and {receipts[0].name} saved")


def _overall_status(checks: list[SalesLaunchCheck]) -> str:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "warn" for check in checks):
        return "warn"
    return "pass"


def _score(checks: list[SalesLaunchCheck]) -> int:
    penalty = sum(30 for check in checks if check.status == "fail") + sum(10 for check in checks if check.status == "warn")
    return max(0, 100 - penalty)


def _read_text(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _name_or_none(path: Path | None) -> str:
    return path.name if path else "none"
