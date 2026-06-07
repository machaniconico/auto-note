from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime
from pathlib import Path
import re

from .article import ArticleError, write_text_atomic
from .paths import unique_path
from .settings import AppSettings, load_settings, save_settings


@dataclass(frozen=True)
class CommercialSetupTemplateResult:
    path: Path
    missing: int


@dataclass(frozen=True)
class CommercialSetupApplyResult:
    path: Path
    settings: AppSettings
    updated: list[str]
    missing: int
    warnings: list[str]


def update_commercial_settings(
    project_dir: Path,
    *,
    seller_name: str | None = None,
    sales_channel_url: str | None = None,
    refund_policy_url: str | None = None,
    support_contact: str | None = None,
    terms_reviewed: bool | None = None,
    support_scope_confirmed: bool | None = None,
    clear_review: bool = False,
) -> AppSettings:
    settings = load_settings(project_dir)
    updates: dict[str, object] = {}
    if seller_name is not None:
        updates["seller_name"] = seller_name.strip()
    if sales_channel_url is not None:
        updates["sales_channel_url"] = sales_channel_url.strip()
    if refund_policy_url is not None:
        updates["refund_policy_url"] = refund_policy_url.strip()
    if support_contact is not None:
        updates["support_contact"] = support_contact.strip()
    if clear_review:
        updates["commercial_terms_reviewed"] = False
        updates["commercial_support_scope_confirmed"] = False
        updates["commercial_reviewed_at"] = ""
    else:
        if terms_reviewed is not None:
            updates["commercial_terms_reviewed"] = terms_reviewed
        if support_scope_confirmed is not None:
            updates["commercial_support_scope_confirmed"] = support_scope_confirmed
        reviewed = bool(updates.get("commercial_terms_reviewed", settings.commercial_terms_reviewed)) or bool(
            updates.get("commercial_support_scope_confirmed", settings.commercial_support_scope_confirmed)
        )
        if reviewed and not settings.commercial_reviewed_at:
            updates["commercial_reviewed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not reviewed:
            updates["commercial_reviewed_at"] = ""
    updated = replace(settings, **updates)
    save_settings(project_dir, updated)
    return updated


def create_commercial_setup_template(project_dir: Path) -> CommercialSetupTemplateResult:
    project_dir = project_dir.resolve()
    sales_dir = project_dir / ".auto-note" / "sales"
    sales_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(sales_dir / f"commercial-setup-template-{datetime.now():%Y%m%d-%H%M%S}.md")
    text, missing = build_commercial_setup_template(project_dir)
    write_text_atomic(path, text)
    return CommercialSetupTemplateResult(path=path, missing=missing)


def list_commercial_setup_templates(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(sales_dir.glob("commercial-setup-template-*.md"), key=lambda path: path.stat().st_mtime, reverse=True)


def apply_commercial_setup_template(project_dir: Path, template_path: Path) -> CommercialSetupApplyResult:
    project_dir = project_dir.resolve()
    template_path = template_path.resolve()
    try:
        text = template_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ArticleError(f"販売者テンプレートを読めません: {exc}") from exc

    values, warnings = parse_commercial_setup_template(text)
    if not values:
        raise ArticleError("販売者テンプレートから保存できる項目が見つかりません。")

    settings = update_commercial_settings(
        project_dir,
        seller_name=values.get("seller_name"),
        sales_channel_url=values.get("sales_channel_url"),
        refund_policy_url=values.get("refund_policy_url"),
        support_contact=values.get("support_contact"),
        terms_reviewed=values.get("terms_reviewed_bool"),
        support_scope_confirmed=values.get("support_scope_confirmed_bool"),
    )
    missing = commercial_setup_missing_count(settings)
    updated = [key for key in _DISPLAY_ORDER if key in values]
    return CommercialSetupApplyResult(
        path=template_path,
        settings=settings,
        updated=updated,
        missing=missing,
        warnings=warnings,
    )


def parse_commercial_setup_template(text: str) -> tuple[dict[str, object], list[str]]:
    values: dict[str, object] = {}
    warnings: list[str] = []
    for line in text.splitlines():
        parsed = _parse_template_line(line)
        if parsed is None:
            continue
        raw_key, raw_value = parsed
        key = _FIELD_ALIASES.get(raw_key)
        if key is None:
            continue
        value = _clean_template_value(raw_value)
        if key in _STRING_FIELDS:
            if not value:
                continue
            values[key] = value
            if key == "support_contact" and _has_raw_email(value):
                warnings.append("support_contact is a raw email address; a public support URL is safer for sales materials")
            continue
        boolean = _parse_bool(value)
        if boolean is None:
            warnings.append(f"{raw_key} could not be parsed as yes/no: {raw_value}")
            continue
        values[f"{key}_bool"] = boolean
    return values, warnings


def build_commercial_setup_template(project_dir: Path) -> tuple[str, int]:
    settings = load_settings(project_dir)
    seller_name, m1 = _value_or_placeholder(settings.seller_name, "[販売者/屋号]")
    sales_url, m2 = _value_or_placeholder(settings.sales_channel_url, "[販売ページURL]")
    refund_url, m3 = _value_or_placeholder(settings.refund_policy_url, "[返金方針URL]")
    support_contact, m4 = _value_or_placeholder(settings.support_contact, "[サポート連絡先]")
    terms_reviewed = "yes" if settings.commercial_terms_reviewed else "no"
    support_scope = "yes" if settings.commercial_support_scope_confirmed else "no"
    missing = commercial_setup_missing_count(settings)
    complete, total = commercial_setup_completion(settings)
    generated = datetime.now()
    apply_command = "python -m auto_note commercial-setup --project-dir . --apply-latest-template"
    direct_command = " ".join(
        [
            "python -m auto_note commercial-setup --project-dir .",
            f"--seller-name {_ps_quote(seller_name)}",
            f"--sales-url {_ps_quote(sales_url)}",
            f"--refund-url {_ps_quote(refund_url)}",
            f"--support-contact {_ps_quote(support_contact)}",
            "--terms-reviewed",
            "--support-scope-confirmed",
        ]
    )
    lines = [
        "# auto-note Commercial Setup Template / 販売者情報テンプレート",
        "",
        f"- Generated: {generated:%Y-%m-%d %H:%M:%S}",
        f"- Missing items: {missing}",
        f"- Completion: {complete}/{total}",
        "",
        "## Fill Values / 入力する情報",
        "",
        f"- seller_name: {seller_name}",
        f"- sales_url: {sales_url}",
        f"- refund_url: {refund_url}",
        f"- support_contact: {support_contact}",
        f"- terms_reviewed: {terms_reviewed}",
        f"- support_scope_confirmed: {support_scope}",
        "",
        "## Field Guide / 入力の目安",
        "",
        "- sales_url は販売ページ、マーケットプレイス、または購入ページの https:// URL にする",
        "- refund_url は返金/キャンセル方針を購入者が確認できる https:// URL にする",
        "- support_contact はメール直書きではなく、問い合わせフォームやサポートページの https:// URL を推奨",
        "- terms_reviewed は docs/TERMS_DRAFT.md と docs/COMMERCIAL_POLICY_DRAFT.md を販売ページに合わせて確認してから yes にする",
        "- support_scope_confirmed はサポート範囲、返金条件、返信目安を販売ページへ明記してから yes にする",
        "",
        "## Safe Apply / 編集後の保存",
        "",
        "1. 上の Fill Values を編集して、このファイルを保存する",
        "2. 確認済みの項目だけ yes にする",
        "3. 次のコマンドで最新テンプレートを設定へ取り込む",
        "",
        "```powershell",
        apply_command,
        "```",
        "",
    ]
    if missing == 0:
        lines.extend(
            [
                "## Direct CLI Command / 直接保存コマンド",
                "",
                "現在の保存値をそのままCLIで再保存する場合だけ使います。",
                "",
                "```powershell",
                direct_command,
                "```",
                "",
            ]
        )
    lines.extend(
        [
        "## Final Checks / 最終確認",
        "",
        "- [ ] 販売ページに対応OS、納品物、インストール手順を書いた",
        "- [ ] note公式APIやログイン回避ツールではないことを書いた",
        "- [ ] 返金条件、サポート範囲、返信目安を書いた",
        "- [ ] 利用条件と商用方針を販売ページの内容に合わせて確認した",
        "- [ ] `auto-note commercial-readiness --project-dir .` のWARNを確認した",
        "- [ ] `auto-note sales-materials --project-dir .` で販売素材を作り直した",
        "- [ ] `auto-note sales-finalize --project-dir . --apply-latest-template` で販売一括を作り直した",
        "",
        "## Notes / メモ",
        "",
        "このファイルは販売者側の下書きです。購入者へ渡す必要はありません。",
        ]
    )
    return "\n".join(lines) + "\n", missing


def format_commercial_settings(settings: AppSettings) -> str:
    missing_fields = commercial_setup_missing_fields(settings)
    warnings = commercial_setup_warnings(settings)
    next_actions = commercial_setup_next_actions(settings)
    complete, total = commercial_setup_completion(settings)
    lines = [
        "Commercial setup / 商用設定",
        f"completion: {complete}/{total}",
        f"seller name: {_value(settings.seller_name)}",
        f"sales page: {_value(settings.sales_channel_url)}",
        f"refund policy: {_value(settings.refund_policy_url)}",
        f"support contact: {_value(settings.support_contact)}",
        f"terms reviewed: {_yes_no(settings.commercial_terms_reviewed)}",
        f"support scope confirmed: {_yes_no(settings.commercial_support_scope_confirmed)}",
        f"reviewed at: {_value(settings.commercial_reviewed_at)}",
        f"missing fields: {_missing_text(missing_fields)}",
    ]
    if warnings:
        lines.append("warnings:")
        lines.extend(f"- {warning}" for warning in warnings)
    if next_actions:
        lines.append("next actions:")
        lines.extend(f"- {action}" for action in next_actions)
    return "\n".join(lines)


def format_commercial_setup_apply_result(result: CommercialSetupApplyResult) -> str:
    warnings = _unique([*result.warnings, *commercial_setup_warnings(result.settings)])
    next_actions = commercial_setup_next_actions(result.settings)
    lines = [
        "Commercial setup template applied / 販売者テンプレート適用",
        f"template: {result.path.name}",
        f"updated: {', '.join(result.updated) if result.updated else '(none)'}",
        f"missing: {result.missing}",
        f"missing fields: {_missing_text(commercial_setup_missing_fields(result.settings))}",
    ]
    if warnings:
        lines.append("warnings:")
        lines.extend(f"- {warning}" for warning in warnings)
    if next_actions:
        lines.append("next actions:")
        lines.extend(f"- {action}" for action in next_actions)
    return "\n".join(lines)


def commercial_setup_missing_count(settings: AppSettings) -> int:
    return len(commercial_setup_missing_fields(settings))


def commercial_setup_completion(settings: AppSettings) -> tuple[int, int]:
    total = 6
    return total - commercial_setup_missing_count(settings), total


def commercial_setup_next_field(settings: AppSettings) -> str:
    if not settings.seller_name.strip():
        return "seller_name"
    sales_url = settings.sales_channel_url.strip()
    if not sales_url or not _is_public_url(sales_url):
        return "sales_channel_url"
    refund_url = settings.refund_policy_url.strip()
    if not refund_url or not _is_public_url(refund_url):
        return "refund_policy_url"
    support_contact = settings.support_contact.strip()
    if not support_contact or _has_raw_email(support_contact) or not _is_public_url(support_contact):
        return "support_contact"
    if not settings.commercial_terms_reviewed:
        return "commercial_terms_reviewed"
    if not settings.commercial_support_scope_confirmed:
        return "commercial_support_scope_confirmed"
    return ""


def commercial_setup_missing_fields(settings: AppSettings) -> list[str]:
    missing: list[str] = []
    if not settings.seller_name.strip():
        missing.append("seller name / 販売者・屋号")
    if not settings.sales_channel_url.strip():
        missing.append("sales page URL / 販売ページURL")
    if not settings.refund_policy_url.strip():
        missing.append("refund policy URL / 返金方針URL")
    if not settings.support_contact.strip():
        missing.append("support contact / サポート連絡先")
    if not settings.commercial_terms_reviewed:
        missing.append("terms reviewed / 利用条件・商用方針確認")
    if not settings.commercial_support_scope_confirmed:
        missing.append("support scope confirmed / サポート範囲確認")
    return missing


def commercial_setup_warnings(settings: AppSettings) -> list[str]:
    warnings: list[str] = []
    if settings.sales_channel_url.strip() and not _is_public_url(settings.sales_channel_url):
        warnings.append("sales page URL should start with http:// or https://")
    if settings.refund_policy_url.strip() and not _is_public_url(settings.refund_policy_url):
        warnings.append("refund policy URL should start with http:// or https://")
    support_contact = settings.support_contact.strip()
    if support_contact:
        if _has_raw_email(support_contact):
            warnings.append("support contact is a raw email address; use a public support URL for sales materials")
        elif not _is_public_url(support_contact):
            warnings.append("support contact should be a public support URL for sales materials")
    return warnings


def commercial_setup_next_actions(settings: AppSettings) -> list[str]:
    actions: list[str] = []
    if not settings.seller_name.strip():
        actions.append('設定 > 販売者/屋号 を入力する / CLI: --seller-name "Your Shop"')
    if not settings.sales_channel_url.strip():
        actions.append('設定 > 販売ページURL を入力する / CLI: --sales-url "https://example.com"')
    elif not _is_public_url(settings.sales_channel_url):
        actions.append("販売ページURLを https:// で始まる公開URLに直す")
    if not settings.refund_policy_url.strip():
        actions.append('設定 > 返金方針URL を入力する / CLI: --refund-url "https://example.com/refund"')
    elif not _is_public_url(settings.refund_policy_url):
        actions.append("返金方針URLを https:// で始まる公開URLに直す")
    support_contact = settings.support_contact.strip()
    if not support_contact:
        actions.append('設定 > サポート連絡先 を入力する / CLI: --support-contact "https://example.com/support"')
    elif _has_raw_email(support_contact):
        actions.append("サポート連絡先はメール直書きではなく、問い合わせフォームなどの公開URLにする")
    elif not _is_public_url(support_contact):
        actions.append("サポート連絡先を https:// で始まる公開サポートURLに直す")
    if not settings.commercial_terms_reviewed:
        actions.append("設定 > 利用条件/商用方針を販売前に確認済み をONにする / CLI: --terms-reviewed")
    if not settings.commercial_support_scope_confirmed:
        actions.append("設定 > サポート範囲と返金条件を販売ページに明記済み をONにする / CLI: --support-scope-confirmed")
    if not actions:
        actions.append("販売素材へ反映する: auto-note sales-materials --project-dir .")
        actions.append("販売ナビで最終確認する: auto-note sales-plan --project-dir .")
    return actions


def _missing_text(fields: list[str]) -> str:
    return ", ".join(fields) if fields else "(none)"


def _value(value: str) -> str:
    return value.strip() or "(not set)"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _value_or_placeholder(value: str, placeholder: str) -> tuple[str, int]:
    text = value.strip()
    return (text, 0) if text else (placeholder, 1)


def _ps_quote(value: str) -> str:
    return '"' + value.replace("`", "``").replace('"', '`"') + '"'


def _is_public_url(value: str) -> bool:
    return bool(re.match(r"https?://[^\s]+$", value.strip(), flags=re.IGNORECASE))


def _has_raw_email(value: str) -> bool:
    return bool(re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", value))


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


_FIELD_ALIASES = {
    "seller_name": "seller_name",
    "seller": "seller_name",
    "sales_url": "sales_channel_url",
    "sales_channel_url": "sales_channel_url",
    "refund_url": "refund_policy_url",
    "refund_policy_url": "refund_policy_url",
    "support_contact": "support_contact",
    "terms_reviewed": "terms_reviewed",
    "commercial_terms_reviewed": "terms_reviewed",
    "support_scope_confirmed": "support_scope_confirmed",
    "commercial_support_scope_confirmed": "support_scope_confirmed",
}

_DISPLAY_ORDER = (
    "seller_name",
    "sales_channel_url",
    "refund_policy_url",
    "support_contact",
    "terms_reviewed_bool",
    "support_scope_confirmed_bool",
)

_STRING_FIELDS = {"seller_name", "sales_channel_url", "refund_policy_url", "support_contact"}

_PLACEHOLDERS = {
    "[販売者/屋号]",
    "[販売ページURL]",
    "[返金方針URL]",
    "[サポート連絡先]",
}

_TRUE_VALUES = {"1", "true", "yes", "y", "on", "checked", "done", "ok", "はい", "済", "済み", "確認済み"}
_FALSE_VALUES = {"0", "false", "no", "n", "off", "unchecked", "not yet", "未", "未確認"}


def _parse_template_line(line: str) -> tuple[str, str] | None:
    match = re.match(r"\s*-\s*([A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$", line)
    if not match:
        return None
    key = match.group(1).strip().lower().replace("-", "_")
    value = match.group(2).strip()
    return key, value


def _clean_template_value(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1].strip()
    if value in _PLACEHOLDERS:
        return ""
    if value.startswith("[") and value.endswith("]"):
        return ""
    return value


def _parse_bool(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return None
