from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

from . import __version__
from .article import write_text_atomic
from .commercial import run_commercial_readiness
from .commercial_setup import commercial_setup_warnings
from .paths import unique_path
from .release import list_releases
from .settings import load_settings


@dataclass(frozen=True)
class SalesMaterialsResult:
    path: Path
    placeholders: int


REQUIRED_SECTIONS = (
    "# auto-note Sales Materials / 販売素材",
    "## Listing Title Ideas / 販売タイトル案",
    "## Short Description / 短い説明",
    "## Feature Bullets / 特長",
    "## Included Files / 納品物",
    "## Requirements / 推奨環境",
    "## Important Notes / 重要事項",
    "## Buyer First 10 Minutes / 購入者の最初の10分",
    "## Delivery Message / 納品メッセージ案",
    "## FAQ / よくある質問",
    "## Support Scope / サポート範囲案",
    "## Refund Policy Summary / 返金方針要約案",
    "## Pre-Listing Checklist / 掲載前チェック",
)

PLACEHOLDER_MARKERS = (
    "[販売者/屋号]",
    "[販売ページURL]",
    "[返金方針URL]",
    "[サポート連絡先]",
    "[サポートメールを販売ページに手動で記載]",
    "[最新配布ZIPを作成]",
)


def create_sales_materials(project_dir: Path) -> SalesMaterialsResult:
    project_dir = project_dir.resolve()
    sales_dir = project_dir / ".auto-note" / "sales"
    sales_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(sales_dir / f"auto-note-sales-materials-{datetime.now():%Y%m%d-%H%M%S}.md")
    text, placeholders = build_sales_materials(project_dir)
    write_text_atomic(path, text)
    return SalesMaterialsResult(path=path, placeholders=placeholders)


def list_sales_materials(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(sales_dir.glob("auto-note-sales-materials-*.md"), key=lambda path: path.stat().st_mtime, reverse=True)


def verify_sales_materials(path: Path, *, strict: bool = False, project_dir: Path | None = None) -> list[str]:
    if not path.exists():
        return [f"sales materials not found: {path}"]
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"sales materials unreadable: {exc}"]
    return verify_sales_materials_text(text, strict=strict, project_dir=project_dir)


def verify_sales_materials_text(
    text: str,
    *,
    strict: bool = False,
    project_dir: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    if not text.strip():
        return ["sales materials is empty"]
    for section in REQUIRED_SECTIONS:
        if section not in text:
            errors.append(f"missing required section: {section}")

    if strict:
        placeholders = _find_placeholders(text)
        if placeholders:
            errors.append(f"unresolved placeholder(s): {', '.join(placeholders)}")
        if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text):
            errors.append("raw email address found; use a public support URL or edit the sales page manually")
        if project_dir is not None:
            project_dir = project_dir.resolve()
            latest_release = _latest_name(list_releases(project_dir))
            if latest_release and latest_release not in text:
                errors.append(f"latest release name is not reflected: {latest_release}")
            for warning in commercial_setup_warnings(load_settings(project_dir)):
                errors.append(f"commercial setup warning: {warning}")
    return errors


def format_sales_materials_verification(path: Path, errors: list[str], *, strict: bool = False) -> str:
    mode = "strict" if strict else "structure"
    if not errors:
        return f"[OK] sales materials verified ({mode}): {path}"
    lines = [f"[NG] sales materials verification failed ({mode}): {path}"]
    lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def build_sales_materials(project_dir: Path) -> tuple[str, int]:
    project_dir = project_dir.resolve()
    settings = load_settings(project_dir)
    readiness = run_commercial_readiness(project_dir)
    latest_release = _latest_name(list_releases(project_dir))

    seller_name, p1 = _value_or_placeholder(settings.seller_name, "[販売者/屋号]")
    sales_url, p2 = _value_or_placeholder(settings.sales_channel_url, "[販売ページURL]")
    refund_url, p3 = _value_or_placeholder(settings.refund_policy_url, "[返金方針URL]")
    support_contact, p4 = _support_contact(settings.support_contact)
    placeholders = p1 + p2 + p3 + p4
    if not latest_release:
        latest_release = "[最新配布ZIPを作成]"
        placeholders += 1

    generated = datetime.now()
    lines = [
        "# auto-note Sales Materials / 販売素材",
        "",
        f"- Generated: {generated:%Y-%m-%d %H:%M:%S}",
        f"- auto-note version: {__version__}",
        f"- Seller / 販売者: {seller_name}",
        f"- Sales page / 販売ページ: {sales_url}",
        f"- Refund policy / 返金方針: {refund_url}",
        f"- Support contact / サポート連絡先: {support_contact}",
        f"- Latest release: {latest_release}",
        f"- Commercial readiness: {readiness.status}, {readiness.score}/100",
        "",
        "## Listing Title Ideas / 販売タイトル案",
        "",
        "- auto-note: note投稿準備を一画面で整えるWindows向けMarkdown運用ツール",
        "- auto-note: 記事作成、公開前チェック、投稿補助、診断までまとめたnote運用キット",
        "",
        "## Short Description / 短い説明",
        "",
        "auto-noteは、Markdown記事の作成、公開前チェック、改善プラン、投稿キュー、予定管理、バックアップ、診断、問い合わせ一式作成をローカルGUIで扱えるWindows向けツールです。note公式APIによる完全自動投稿やログイン回避ではなく、普段使いのブラウザでnote投稿画面へ安全に貼り付ける運用を前提にしています。",
        "",
        "## Feature Bullets / 特長",
        "",
        "- GUIから記事作成、本文編集、メタ情報編集、投稿ヘルパー、コピー操作まで実行",
        "- 公開前チェック、記事レビュー、改善プラン、投稿準備、投稿キューで投稿前の抜け漏れを可視化",
        "- 予定管理、匿名ICS出力、アイデア箱、スターター一式で初回体験を短縮",
        "- バックアップ、履歴、自動退避、設定/アイデア破損時の修復でローカル運用を保護",
        "- セルフテスト、受入チェック、トラブル診断、問い合わせ一式、プライバシー監査を同梱",
        "- 配布ZIP、販売準備、販売ナビ、販売用一式ZIPで販売前後の証跡を残せる",
        "",
        "## Included Files / 納品物",
        "",
        f"- Buyer-facing release ZIP: {latest_release}",
        "- START_HERE.txt, install/uninstall shortcuts, README, Quickstart, Support, Privacy, Terms/Policy drafts",
        "- Seller-side evidence ZIP is kept by the seller and is not normally delivered to the buyer.",
        "",
        "## Requirements / 推奨環境",
        "",
        "- Windows 10/11",
        "- Python 3.11+ or bundled installer flow described in the release package",
        "- A normal browser login to note.com",
        "- Local folder where the buyer can extract the release ZIP",
        "",
        "## Important Notes / 重要事項",
        "",
        "- note.comのログイン制限、CAPTCHA、二要素認証を回避しません。",
        "- Googleログインやnote側の認証で止まる場合は、普段使いのブラウザでログインして投稿ヘルパーの貼り付け運用を使います。",
        "- 公開ボタンの最終操作、公開内容の確認、投稿結果の責任は購入者自身にあります。",
        "- 記事内容、収益、集客効果、note側仕様変更への完全追随は保証しません。",
        "",
        "## Buyer First 10 Minutes / 購入者の最初の10分",
        "",
        "購入者には、納品後まず次の順で動作確認してもらうとサポートの往復を減らせます。",
        "",
        "1. ZIPを展開し、`START_HERE.txt` を開く",
        "2. `shortcuts\\install-auto-note.bat` を実行する",
        "3. デスクトップまたはスタートメニューの `auto-note` を開く",
        "4. GUIの `受入チェック` または `auto-note acceptance --project-dir . --full` を実行する",
        "5. `スターター一式` でサンプル記事、予定、アイデアを作り、投稿ヘルパーを開けるか確認する",
        "6. 普段使うブラウザでnote.comへログインし、投稿ヘルパーのコピー/貼り付け運用を確認する",
        "7. 起動やログインで詰まる場合は、`ヘルプ > 問い合わせ一式` または `auto-note support --project-dir . --bundle` を作成する",
        "",
        "## Delivery Message / 納品メッセージ案",
        "",
        f"{seller_name}です。ご購入ありがとうございます。添付の `{latest_release}` を展開し、まず `START_HERE.txt` を開いてください。インストール後は `auto-note` を起動し、`受入チェック` と `スターター一式` で初回確認を行えます。起動しない場合は `auto-note-gui.bat` を直接開き、ヘルプの `問い合わせ一式` を作成して状況を共有してください。",
        "",
        "## FAQ / よくある質問",
        "",
        "### noteへ完全自動投稿できますか？",
        "",
        "いいえ。安全性とログイン制限回避を避けるため、通常ブラウザへの貼り付け補助を基本にしています。",
        "",
        "### noteログイン画面で安全ではないと表示された場合は？",
        "",
        "普段使っているブラウザでnote.comにログインし、auto-noteの投稿ヘルパーからタイトル/本文/タグをコピーして貼り付けてください。",
        "",
        "### 問い合わせ時に記事本文を送る必要はありますか？",
        "",
        "通常は不要です。問い合わせ一式と診断ZIPは、標準でパス、ユーザー名、メール、記事タイトル、記事ファイル名を匿名化します。",
        "",
        "## Support Scope / サポート範囲案",
        "",
        "- 初回起動、ショートカット、インストール/アンインストール",
        "- GUI操作、記事作成、投稿ヘルパー、公開前チェック、診断、バックアップ",
        "- 配布ZIPの破損、インストール手順、問い合わせ一式の確認",
        "- note.com側のログイン制限、アカウント制限、CAPTCHA、投稿結果、収益化は対象外",
        "",
        "## Refund Policy Summary / 返金方針要約案",
        "",
        f"返金方針の詳細は {refund_url} を確認してください。デジタル商品のため購入後の自己都合返金は原則対象外ですが、配布ZIP破損、推奨環境での初回起動不可、商品説明と著しく異なる挙動などは、診断レポート確認のうえ個別対応します。",
        "",
        "## Pre-Listing Checklist / 掲載前チェック",
        "",
        "- [ ] 販売ページに対応OS、インストール手順、サポート範囲、返金条件を明記した",
        "- [ ] note公式APIやログイン回避ツールではないことを明記した",
        "- [ ] 最新配布ZIPを作成し、販売用一式ZIPを作成/検証した",
        "- [ ] 販売ナビと販売準備で残WARNを確認した",
        "- [ ] サポート連絡先と返信目安を販売ページに記載した",
    ]
    remaining = [item for item in readiness.items if item.status in {"warn", "fail"}]
    if remaining:
        lines.extend(["", "## Remaining Readiness Items / 残確認項目", ""])
        for item in remaining:
            label = {"warn": "WARN", "fail": "NG"}.get(item.status, item.status.upper())
            lines.append(f"- [{label}] {item.name}: {item.detail}")
            if item.action:
                lines.append(f"  - next: {item.action}")
    return "\n".join(lines) + "\n", placeholders


def _latest_name(paths: list[Path]) -> str:
    return paths[0].name if paths else ""


def _value_or_placeholder(value: str, placeholder: str) -> tuple[str, int]:
    text = value.strip()
    return (text, 0) if text else (placeholder, 1)


def _support_contact(value: str) -> tuple[str, int]:
    text = value.strip()
    if not text:
        return "[サポート連絡先]", 1
    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text):
        return "[サポートメールを販売ページに手動で記載]", 1
    return text, 0


def _find_placeholders(text: str) -> list[str]:
    return [marker for marker in PLACEHOLDER_MARKERS if marker in text]
