from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import struct

from .article import Article, ArticleError, load_article, read_markdown, write_markdown


REMOTE_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
LARGE_IMAGE_BYTES = 5 * 1024 * 1024
SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


@dataclass(frozen=True)
class ImageReference:
    article: Path
    kind: str
    value: str
    path: Path | None
    exists: bool
    remote: bool
    size_bytes: int = 0
    width: int = 0
    height: int = 0
    image_type: str = ""

    @property
    def ok(self) -> bool:
        return self.remote or self.exists

    @property
    def large(self) -> bool:
        return self.exists and self.size_bytes > LARGE_IMAGE_BYTES


@dataclass(frozen=True)
class ImportedImage:
    source: Path
    target: Path
    relative_path: str
    markdown: str
    size_bytes: int
    width: int = 0
    height: int = 0
    image_type: str = ""


@dataclass(frozen=True)
class OptimizedImage:
    path: Path
    original_bytes: int
    optimized_bytes: int
    width: int
    height: int
    changed: bool


def collect_article_images(article: Article) -> list[ImageReference]:
    refs: list[ImageReference] = []
    if article.cover:
        refs.append(_reference(article.source, "cover", article.cover))
    for value in _body_images(article.body):
        refs.append(_reference(article.source, "body", value))
    return refs


def inspect_images_path(path: Path, *, pattern: str = "*.md") -> list[ImageReference]:
    refs: list[ImageReference] = []
    files = _collect_markdown_files(path, pattern)
    if not files:
        raise ArticleError(f"No markdown files found in {path}.")
    for file in files:
        refs.extend(collect_article_images(load_article(file)))
    return refs


def format_image_report(refs: list[ImageReference]) -> str:
    if not refs:
        return "画像参照はありません。"

    lines: list[str] = []
    missing = sum(1 for ref in refs if not ref.ok)
    large = sum(1 for ref in refs if ref.large)
    remote = sum(1 for ref in refs if ref.remote)
    lines.append(f"画像チェック: {len(refs)}件 / 欠落 {missing}件 / 大きめ {large}件 / 外部URL {remote}件")
    lines.append("")
    for ref in refs:
        status = "OK"
        if not ref.ok:
            status = "NG"
        elif ref.large:
            status = "WARN"
        detail = ref.value if ref.remote or ref.path is None else str(ref.path)
        size = f" ({_format_bytes(ref.size_bytes)})" if ref.size_bytes else ""
        dimensions = f" {ref.width}x{ref.height}" if ref.width and ref.height else ""
        image_type = f" {ref.image_type}" if ref.image_type else ""
        lines.append(f"[{status}] {ref.article.name} {ref.kind}: {detail}{size}{dimensions}{image_type}")
    return "\n".join(lines)


def missing_images(refs: list[ImageReference]) -> list[ImageReference]:
    return [ref for ref in refs if not ref.ok]


def import_image_for_article(
    article_path: Path,
    image_path: Path,
    *,
    alt_text: str = "",
    optimize: bool = False,
    max_width: int = 1600,
    quality: int = 85,
) -> ImportedImage:
    article_path = article_path.resolve()
    image_path = image_path.resolve()
    if not article_path.exists():
        raise ArticleError(f"article not found: {article_path}")
    if not image_path.exists() or not image_path.is_file():
        raise ArticleError(f"image not found: {image_path}")
    if image_path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        raise ArticleError(f"unsupported image type: {image_path.suffix}")

    assets_dir = article_path.parent / f"{article_path.stem}-assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    target = _next_available_path(assets_dir / _safe_filename(image_path.name))
    shutil.copy2(image_path, target)
    if optimize:
        optimize_image(target, max_width=max_width, quality=quality, replace=True)
    relative = target.relative_to(article_path.parent).as_posix()
    alt = alt_text.strip() or image_path.stem
    markdown = f"![{alt}]({relative})"
    info = image_info(target)
    return ImportedImage(
        source=image_path,
        target=target,
        relative_path=relative,
        markdown=markdown,
        size_bytes=target.stat().st_size,
        width=info.width,
        height=info.height,
        image_type=info.image_type,
    )


def optimize_image(
    image_path: Path,
    *,
    max_width: int = 1600,
    quality: int = 85,
    replace: bool = False,
) -> OptimizedImage:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise ArticleError(
            "画像最適化には Pillow が必要です。"
            "`.\\.venv\\Scripts\\python.exe -m pip install -e .[images]` を実行してください。"
        ) from exc

    image_path = image_path.resolve()
    if not image_path.exists() or not image_path.is_file():
        raise ArticleError(f"image not found: {image_path}")
    if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ArticleError(f"unsupported optimization image type: {image_path.suffix}")

    original_bytes = image_path.stat().st_size
    max_width = max(320, int(max_width))
    quality = min(100, max(40, int(quality)))

    with Image.open(image_path) as image:
        image = image.copy()
        resized = False
        if image.width > max_width:
            ratio = max_width / image.width
            new_size = (max_width, max(1, round(image.height * ratio)))
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            image = image.resize(new_size, resampling)
            resized = True
        if image.mode in {"RGBA", "LA", "P"} and image_path.suffix.lower() in {".jpg", ".jpeg"}:
            image = image.convert("RGB")
        output_path = image_path if replace else _next_available_path(image_path.with_name(f"{image_path.stem}-optimized{image_path.suffix}"))
        temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
        save_kwargs = _save_kwargs(image_path.suffix.lower(), quality)
        image.save(temp_path, **save_kwargs)

    optimized_bytes = temp_path.stat().st_size
    if optimized_bytes >= original_bytes and not resized and image_path.exists():
        temp_path.unlink(missing_ok=True)
        info = image_info(image_path)
        return OptimizedImage(
            path=image_path,
            original_bytes=original_bytes,
            optimized_bytes=original_bytes,
            width=info.width,
            height=info.height,
            changed=False,
        )

    temp_path.replace(output_path)
    info = image_info(output_path)
    return OptimizedImage(
        path=output_path,
        original_bytes=original_bytes,
        optimized_bytes=optimized_bytes,
        width=info.width,
        height=info.height,
        changed=True,
    )


def set_article_cover(article_path: Path, cover_path: str) -> None:
    metadata, body = read_markdown(article_path)
    metadata["cover"] = cover_path
    write_markdown(article_path, metadata, body)


@dataclass(frozen=True)
class ImageInfo:
    width: int = 0
    height: int = 0
    image_type: str = ""


def image_info(path: Path) -> ImageInfo:
    try:
        data = path.read_bytes()
    except OSError:
        return ImageInfo()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return ImageInfo(width=width, height=height, image_type="PNG")
    if data.startswith((b"GIF87a", b"GIF89a")) and len(data) >= 10:
        width, height = struct.unpack("<HH", data[6:10])
        return ImageInfo(width=width, height=height, image_type="GIF")
    if data.startswith(b"\xff\xd8"):
        return _jpeg_info(data)
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return ImageInfo(image_type="WEBP")
    if path.suffix.lower() == ".svg":
        return ImageInfo(image_type="SVG")
    return ImageInfo()


def _reference(article_path: Path, kind: str, value: str) -> ImageReference:
    cleaned = value.strip().strip("\"'")
    if not cleaned:
        return ImageReference(article=article_path, kind=kind, value=value, path=None, exists=False, remote=False)
    if REMOTE_RE.match(cleaned):
        return ImageReference(article=article_path, kind=kind, value=cleaned, path=None, exists=True, remote=True)

    local = (article_path.parent / cleaned).resolve()
    exists = local.exists()
    size = local.stat().st_size if exists and local.is_file() else 0
    info = image_info(local) if exists and local.is_file() else ImageInfo()
    return ImageReference(
        article=article_path,
        kind=kind,
        value=cleaned,
        path=local,
        exists=exists,
        remote=False,
        size_bytes=size,
        width=info.width,
        height=info.height,
        image_type=info.image_type,
    )


def _body_images(body: str) -> list[str]:
    images: list[str] = []
    for match in IMAGE_RE.finditer(body):
        value = match.group(1).strip().strip("\"'")
        if value:
            images.append(value)
    return images


def _collect_markdown_files(path: Path, pattern: str) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(file for file in path.glob(pattern) if file.is_file())


def _format_bytes(value: int) -> str:
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value} B"


def _jpeg_info(data: bytes) -> ImageInfo:
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            break
        length = int.from_bytes(data[index:index + 2], "big")
        if length < 2 or index + length > len(data):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = int.from_bytes(data[index + 3:index + 5], "big")
            width = int.from_bytes(data[index + 5:index + 7], "big")
            return ImageInfo(width=width, height=height, image_type="JPEG")
        index += length
    return ImageInfo(image_type="JPEG")


def _safe_filename(value: str) -> str:
    name = Path(value).name
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", Path(name).stem).strip("-") or "image"
    suffix = Path(name).suffix.lower()
    return f"{stem}{suffix}"


def _save_kwargs(suffix: str, quality: int) -> dict[str, object]:
    if suffix in {".jpg", ".jpeg"}:
        return {"format": "JPEG", "quality": quality, "optimize": True}
    if suffix == ".png":
        return {"format": "PNG", "optimize": True}
    if suffix == ".webp":
        return {"format": "WEBP", "quality": quality, "method": 6}
    return {}


def _next_available_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(path)
