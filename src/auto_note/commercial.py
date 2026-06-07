from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import zipfile

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


def _value(value: str) -> str:
    value = value.strip()
    return value if value else "(not set)"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


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

    report = run_privacy_audit(project_dir, include_sales_handoffs=include_sales_handoffs)
    if report.status == "fail":
        failures = sum(1 for item in report.items if item.status == "fail")
        return CommercialReadinessItem(
            "プライバシー監査",
            "fail",
            f"{failures} NG artifact(s)",
            "`auto-note privacy-audit --project-dir .` と `auto-note repair --project-dir . --cleanup-privacy` を確認してください。",
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
        return CommercialReadinessItem(
            "受入チェック",
            "fail",
            f"current status {current.status}, saved reports {len(reports)}",
            "`auto-note acceptance --project-dir . --create --gui-smoke --smoke-helper --report` を実行してください。",
        )
    if not reports:
        return CommercialReadinessItem(
            "受入チェック",
            "warn",
            f"current status {current.status}, no saved acceptance report",
            "`auto-note acceptance --project-dir . --create --gui-smoke --smoke-helper --report` で納品確認を保存してください。",
        )
    latest = reports[0]
    if current.has_warnings:
        return CommercialReadinessItem(
            "受入チェック",
            "warn",
            f"current status {current.status}, latest saved {latest.name}",
            "受入チェックのWARNを確認し、必要に応じて保存し直してください。",
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
            "販売ページ、決済方法、返金条件、サポート範囲に合わせて文書を最終レビューしてください。",
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
            "GUIの設定タブ、または `auto-note commercial-setup --help` で販売者情報を保存してください。",
        )
    warnings = commercial_setup_warnings(settings)
    if warnings:
        return CommercialReadinessItem(
            "販売者プロフィール",
            "warn",
            f"warnings: {', '.join(warnings)}",
            "販売ページURL、返金方針URL、サポート連絡先を公開URL形式で保存してください。",
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
        return CommercialReadinessItem(
            "販売最終確認",
            "warn",
            f"missing: {', '.join(missing)}",
            "販売ページ、利用条件、返金条件、サポート範囲を確認し、設定タブで最終確認を保存してください。",
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
            "販売素材にそのまま載せられる公開サポートURLを設定してください。",
        )
    return CommercialReadinessItem(
        "サポート連絡先",
        "warn",
        "support contact is not set",
        "GUIの設定タブでサポート連絡先を設定し、販売ページにも問い合わせ方法を明記してください。",
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
        "販売直前は `auto-note preflight --project-dir . --create-release --install-smoke --gui-smoke` と実機確認を実行してください。",
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
