from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path

from . import __version__
from .article import write_text_atomic
from .paths import unique_path


@dataclass(frozen=True)
class SalesScreenshotAsset:
    title: str
    filename: str
    path: Path
    caption: str


@dataclass(frozen=True)
class SalesScreenshotPack:
    directory: Path
    assets: list[SalesScreenshotAsset]
    html_path: Path
    captions_path: Path
    readme_path: Path


SCREENSHOT_ASSETS = (
    {
        "filename": "01-home-readiness.svg",
        "title": "ホームで今日の作業が見える",
        "subtitle": "投稿、復旧、販売準備まで一画面で確認",
        "accent": "#0f766e",
        "caption": "ホームで準備度、次の一手、作業進行、直近レポート、販売準備タイムラインをまとめて確認できます。",
        "kicker": "HOME",
        "bullets": (
            "準備度と次の一手",
            "初回/記事/投稿/販売の進行",
            "直近レポートと販売準備タイムライン",
        ),
        "mock": "home",
    },
    {
        "filename": "02-article-polish.svg",
        "title": "記事を選ぶと改善順が見える",
        "subtitle": "レビュー、投稿準備、投稿キューを横断",
        "accent": "#2563eb",
        "caption": "記事ごとのレビュー点数、修正項目、投稿準備、投稿キューを見ながら、次に直す内容へ進めます。",
        "kicker": "ARTICLE",
        "bullets": (
            "記事一覧と状態フィルター",
            "レビュー点数と改善プラン",
            "投稿前チェックと投稿キュー",
        ),
        "mock": "article",
    },
    {
        "filename": "03-safe-posting.svg",
        "title": "noteログイン制限に無理をしない",
        "subtitle": "普段のブラウザと投稿ヘルパーで安全に貼り付け",
        "accent": "#7c3aed",
        "caption": "noteやGoogleログインで安全警告が出る場合でも、普段のブラウザと投稿ヘルパーのコピー運用へ戻れます。",
        "kicker": "SAFE POSTING",
        "bullets": (
            "既定ブラウザでnoteログイン",
            "タイトル/本文/タグをコピー",
            "公開前チェックで誤投稿を防止",
        ),
        "mock": "helper",
    },
    {
        "filename": "04-sales-delivery.svg",
        "title": "販売と納品の証跡を一式化",
        "subtitle": "購入者ZIP、送付文、販売直前チェックを照合",
        "accent": "#b45309",
        "caption": "販売素材、購入者向けZIP、送付文、送付記録、販売直前チェックをつなげて、納品ミスを減らします。",
        "kicker": "SALES",
        "bullets": (
            "販売素材と販売一式ZIP",
            "購入者ZIP/送付文/送付記録",
            "販売直前チェックと一括チェック",
        ),
        "mock": "sales",
    },
    {
        "filename": "05-support-diagnostics.svg",
        "title": "問い合わせ一式でサポートを短縮",
        "subtitle": "匿名診断、GUIログ、表示診断をまとめて確認",
        "accent": "#be123c",
        "caption": "問い合わせ時は匿名診断ZIP、GUIログ、表示診断、送付前チェックをまとめ、サポートの往復を短縮できます。",
        "kicker": "SUPPORT",
        "bullets": (
            "匿名診断ZIPとGUIログ",
            "表示診断と復旧セット",
            "送付前チェックリスト",
        ),
        "mock": "support",
    },
)


def create_sales_screenshot_pack(project_dir: Path) -> SalesScreenshotPack:
    project_dir = project_dir.resolve()
    root = project_dir / ".auto-note" / "sales" / "screenshots"
    root.mkdir(parents=True, exist_ok=True)
    directory = unique_path(root / f"auto-note-sales-screenshots-{datetime.now():%Y%m%d-%H%M%S}")
    directory.mkdir(parents=True, exist_ok=False)

    assets: list[SalesScreenshotAsset] = []
    for spec in SCREENSHOT_ASSETS:
        path = directory / spec["filename"]
        write_text_atomic(path, _render_svg(spec))
        assets.append(
            SalesScreenshotAsset(
                title=str(spec["title"]),
                filename=str(spec["filename"]),
                path=path,
                caption=str(spec["caption"]),
            )
        )

    captions_path = directory / "SCREENSHOT_CAPTIONS.md"
    html_path = directory / "index.html"
    readme_path = directory / "README.txt"
    write_text_atomic(captions_path, _render_captions(assets))
    write_text_atomic(html_path, _render_html(assets))
    write_text_atomic(readme_path, _render_readme(assets))
    return SalesScreenshotPack(
        directory=directory,
        assets=assets,
        html_path=html_path,
        captions_path=captions_path,
        readme_path=readme_path,
    )


def list_sales_screenshot_packs(project_dir: Path) -> list[Path]:
    root = project_dir / ".auto-note" / "sales" / "screenshots"
    if not root.exists():
        return []
    return sorted(
        [path for path in root.glob("auto-note-sales-screenshots-*") if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def verify_sales_screenshot_pack(path: Path) -> list[str]:
    path = path.resolve()
    errors: list[str] = []
    if not path.exists() or not path.is_dir():
        return [f"sales screenshot pack not found: {path}"]
    required = [str(spec["filename"]) for spec in SCREENSHOT_ASSETS] + [
        "SCREENSHOT_CAPTIONS.md",
        "index.html",
        "README.txt",
    ]
    for name in required:
        file_path = path / name
        if not file_path.exists():
            errors.append(f"missing required file: {name}")
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"unreadable file: {name}: {exc}")
            continue
        if not text.strip():
            errors.append(f"empty file: {name}")
    for spec in SCREENSHOT_ASSETS:
        svg_path = path / str(spec["filename"])
        if not svg_path.exists():
            continue
        text = svg_path.read_text(encoding="utf-8", errors="replace")
        if "<svg" not in text or "</svg>" not in text:
            errors.append(f"invalid SVG markup: {svg_path.name}")
        if str(spec["title"]) not in text:
            errors.append(f"missing title in SVG: {svg_path.name}")
    return errors


def format_sales_screenshot_pack(pack: SalesScreenshotPack) -> str:
    lines = [
        "Sales screenshot pack / 販売ページ向け画像パック",
        "",
        f"directory: {pack.directory}",
        f"assets: {len(pack.assets)}",
        f"preview: {pack.html_path}",
        f"captions: {pack.captions_path}",
        "",
        "Files:",
    ]
    lines.extend(f"- {asset.filename}: {asset.title}" for asset in pack.assets)
    return "\n".join(lines)


def format_sales_screenshot_verification(path: Path, errors: list[str]) -> str:
    if not errors:
        return f"[OK] sales screenshot pack verified: {path}"
    lines = [f"[NG] sales screenshot pack verification failed: {path}"]
    lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def _render_svg(spec: dict[str, object]) -> str:
    title = str(spec["title"])
    subtitle = str(spec["subtitle"])
    accent = str(spec["accent"])
    kicker = str(spec["kicker"])
    bullets = tuple(str(item) for item in spec["bullets"])
    mock = str(spec["mock"])
    generated = datetime.now().strftime("%Y-%m-%d")

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720" role="img">',
        f"<title>{escape(title)}</title>",
        "<rect width=\"1280\" height=\"720\" fill=\"#f5f7fb\"/>",
        "<rect x=\"56\" y=\"54\" width=\"1168\" height=\"612\" rx=\"22\" fill=\"#ffffff\"/>",
        "<rect x=\"56\" y=\"54\" width=\"1168\" height=\"86\" rx=\"22\" fill=\"#102033\"/>",
        f"<rect x=\"56\" y=\"126\" width=\"1168\" height=\"14\" fill=\"{accent}\"/>",
        _text(kicker, 92, 108, 22, "#b9c5d6", weight="700"),
        _text("auto-note", 1090, 108, 24, "#ffffff", anchor="end", weight="700"),
        _text(title, 92, 210, 48, "#102033", weight="700"),
        _text(subtitle, 92, 254, 26, "#506074"),
        _bullets(bullets, 96, 324, accent),
        _mock_panel(mock, accent),
        _text(f"Generated with auto-note {__version__} / {generated}", 92, 626, 18, "#7c8798"),
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


def _mock_panel(kind: str, accent: str) -> str:
    x = 610
    y = 190
    parts = [
        f"<rect x=\"{x}\" y=\"{y}\" width=\"548\" height=\"374\" rx=\"18\" fill=\"#edf2f7\"/>",
        f"<rect x=\"{x + 24}\" y=\"{y + 28}\" width=\"500\" height=\"56\" rx=\"10\" fill=\"#102033\"/>",
        f"<rect x=\"{x + 40}\" y=\"{y + 44}\" width=\"120\" height=\"24\" rx=\"5\" fill=\"{accent}\"/>",
        f"<rect x=\"{x + 350}\" y=\"{y + 44}\" width=\"70\" height=\"24\" rx=\"5\" fill=\"#ffffff\" opacity=\"0.92\"/>",
        f"<rect x=\"{x + 430}\" y=\"{y + 44}\" width=\"78\" height=\"24\" rx=\"5\" fill=\"{accent}\"/>",
    ]
    if kind == "home":
        labels = ("READY", "初回", "記事", "販売", "サポート")
        for index, label in enumerate(labels):
            px = x + 40 + index * 92
            parts.append(f"<rect x=\"{px}\" y=\"{y + 114}\" width=\"76\" height=\"44\" rx=\"8\" fill=\"#ffffff\"/>")
            parts.append(_text(label, px + 38, y + 142, 16, accent if index == 0 else "#506074", anchor="middle", weight="700"))
        for row, label in enumerate(("販売者情報", "配布ZIP", "購入者ZIP", "一括チェック")):
            py = y + 190 + row * 44
            parts.append(f"<rect x=\"{x + 40}\" y=\"{py}\" width=\"468\" height=\"30\" rx=\"6\" fill=\"#ffffff\"/>")
            parts.append(f"<rect x=\"{x + 54}\" y=\"{py + 8}\" width=\"58\" height=\"14\" rx=\"4\" fill=\"{accent}\"/>")
            parts.append(_text(label, x + 130, py + 21, 15, "#334155", weight="700"))
    elif kind == "article":
        for row in range(5):
            py = y + 118 + row * 48
            parts.append(f"<rect x=\"{x + 40}\" y=\"{py}\" width=\"276\" height=\"34\" rx=\"6\" fill=\"#ffffff\"/>")
            parts.append(f"<rect x=\"{x + 54}\" y=\"{py + 10}\" width=\"86\" height=\"12\" rx=\"4\" fill=\"#cbd5e1\"/>")
            parts.append(f"<rect x=\"{x + 160}\" y=\"{py + 10}\" width=\"128\" height=\"12\" rx=\"4\" fill=\"#dbe4ef\"/>")
        parts.append(f"<rect x=\"{x + 340}\" y=\"{y + 118}\" width=\"168\" height=\"226\" rx=\"10\" fill=\"#ffffff\"/>")
        parts.append(_text("改善プラン", x + 424, y + 150, 17, accent, anchor="middle", weight="700"))
        for row in range(4):
            parts.append(f"<rect x=\"{x + 360}\" y=\"{y + 178 + row * 38}\" width=\"124\" height=\"14\" rx=\"4\" fill=\"#cbd5e1\"/>")
    elif kind == "helper":
        parts.append(f"<rect x=\"{x + 42}\" y=\"{y + 124}\" width=\"216\" height=\"188\" rx=\"12\" fill=\"#ffffff\"/>")
        parts.append(f"<rect x=\"{x + 290}\" y=\"{y + 124}\" width=\"218\" height=\"188\" rx=\"12\" fill=\"#ffffff\"/>")
        parts.append(_text("投稿ヘルパー", x + 150, y + 160, 18, accent, anchor="middle", weight="700"))
        parts.append(_text("note投稿画面", x + 399, y + 160, 18, "#334155", anchor="middle", weight="700"))
        for row in range(3):
            parts.append(f"<rect x=\"{x + 70}\" y=\"{y + 194 + row * 36}\" width=\"158\" height=\"18\" rx=\"5\" fill=\"#dbe4ef\"/>")
            parts.append(f"<rect x=\"{x + 318}\" y=\"{y + 194 + row * 36}\" width=\"162\" height=\"18\" rx=\"5\" fill=\"#dbe4ef\"/>")
        parts.append(f"<path d=\"M264 {y + 218} C286 {y + 218}, 288 {y + 218}, 306 {y + 218}\" stroke=\"{accent}\" stroke-width=\"6\" fill=\"none\"/>")
    elif kind == "sales":
        labels = ("販売素材", "販売一式", "購入者ZIP", "送付記録")
        for index, label in enumerate(labels):
            px = x + 40 + index * 116
            parts.append(f"<rect x=\"{px}\" y=\"{y + 146}\" width=\"96\" height=\"82\" rx=\"10\" fill=\"#ffffff\"/>")
            parts.append(f"<rect x=\"{px + 20}\" y=\"{y + 164}\" width=\"56\" height=\"18\" rx=\"4\" fill=\"{accent}\"/>")
            parts.append(_text(label, px + 48, y + 208, 14, "#334155", anchor="middle", weight="700"))
        parts.append(f"<rect x=\"{x + 62}\" y=\"{y + 286}\" width=\"422\" height=\"42\" rx=\"8\" fill=\"#ffffff\"/>")
        parts.append(_text("販売直前チェック / 一括チェック", x + 273, y + 313, 18, accent, anchor="middle", weight="700"))
    else:
        labels = ("GUIログ", "表示診断", "匿名診断ZIP", "送付前リスト")
        for row, label in enumerate(labels):
            py = y + 128 + row * 52
            parts.append(f"<rect x=\"{x + 62}\" y=\"{py}\" width=\"424\" height=\"36\" rx=\"8\" fill=\"#ffffff\"/>")
            parts.append(f"<rect x=\"{x + 78}\" y=\"{py + 10}\" width=\"62\" height=\"16\" rx=\"4\" fill=\"{accent}\"/>")
            parts.append(_text(label, x + 158, py + 24, 16, "#334155", weight="700"))
    return "\n".join(parts)


def _text(
    value: str,
    x: int,
    y: int,
    size: int,
    color: str,
    *,
    anchor: str = "start",
    weight: str = "500",
) -> str:
    return (
        f"<text x=\"{x}\" y=\"{y}\" font-family=\"Meiryo, Noto Sans JP, Arial, sans-serif\" "
        f"font-size=\"{size}\" font-weight=\"{weight}\" fill=\"{color}\" text-anchor=\"{anchor}\">"
        f"{escape(value)}</text>"
    )


def _bullets(values: tuple[str, ...], x: int, y: int, accent: str) -> str:
    parts: list[str] = []
    for index, value in enumerate(values):
        py = y + index * 54
        parts.append(f"<circle cx=\"{x}\" cy=\"{py - 7}\" r=\"9\" fill=\"{accent}\"/>")
        parts.append(_text(value, x + 28, py, 24, "#223044", weight="700"))
    return "\n".join(parts)


def _render_captions(assets: list[SalesScreenshotAsset]) -> str:
    lines = [
        "# auto-note Sales Screenshot Captions / 販売ページ画像キャプション",
        "",
        "販売ページの画像欄や説明文へ貼り付ける短文です。",
        "",
    ]
    for asset in assets:
        lines.extend([f"## {asset.filename}", "", asset.caption, ""])
    return "\n".join(lines)


def _render_html(assets: list[SalesScreenshotAsset]) -> str:
    cards = []
    for asset in assets:
        cards.append(
            "\n".join(
                [
                    "<section>",
                    f"<h2>{escape(asset.title)}</h2>",
                    f"<img src=\"{escape(asset.filename)}\" alt=\"{escape(asset.title)}\">",
                    f"<p>{escape(asset.caption)}</p>",
                    "</section>",
                ]
            )
        )
    return (
        "<!doctype html>\n"
        "<html lang=\"ja\">\n"
        "<meta charset=\"utf-8\">\n"
        "<title>auto-note sales screenshots</title>\n"
        "<style>\n"
        "body{margin:0;background:#eef2f7;color:#102033;font-family:Meiryo,'Noto Sans JP',Arial,sans-serif;}\n"
        "main{max-width:1120px;margin:0 auto;padding:32px;}\n"
        "section{background:white;border:1px solid #dbe4ef;margin:0 0 24px;padding:20px;}\n"
        "img{display:block;width:100%;height:auto;border:1px solid #dbe4ef;}\n"
        "h1{font-size:28px;margin:0 0 8px;}h2{font-size:20px;margin:0 0 12px;}p{line-height:1.7;color:#506074;}\n"
        "</style>\n"
        "<main>\n"
        "<h1>auto-note sales screenshots</h1>\n"
        "<p>販売ページ掲載前に、画像とキャプションの流れを確認できます。</p>\n"
        + "\n".join(cards)
        + "\n</main>\n</html>\n"
    )


def _render_readme(assets: list[SalesScreenshotAsset]) -> str:
    lines = [
        "auto-note sales screenshot pack",
        "",
        "Files in this folder are SVG images for marketplace listing pages.",
        "Open index.html to review the full set and copy captions from SCREENSHOT_CAPTIONS.md.",
        "If your marketplace requires PNG/JPEG, open each SVG in a browser or image editor and export it.",
        "",
        f"asset_count: {len(assets)}",
    ]
    lines.extend(f"- {asset.filename}" for asset in assets)
    return "\n".join(lines) + "\n"
