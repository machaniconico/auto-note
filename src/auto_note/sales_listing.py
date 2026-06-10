from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from . import __version__
from .article import write_text_atomic
from .paths import unique_path
from .sales_materials import (
    create_sales_materials,
    list_sales_materials,
    verify_sales_materials_text,
)
from .sales_screenshots import (
    SCREENSHOT_ASSETS,
    create_sales_screenshot_pack,
    list_sales_screenshot_packs,
    verify_sales_screenshot_pack,
)


@dataclass(frozen=True)
class SalesListingKit:
    directory: Path
    package_path: Path
    materials_path: Path
    screenshot_pack_path: Path
    manifest_path: Path
    checklist_path: Path
    readme_path: Path


REQUIRED_LISTING_KIT_FILES = (
    "SALES_MATERIALS.md",
    "SCREENSHOT_CAPTIONS.md",
    "index.html",
    "LISTING_UPLOAD_CHECKLIST.txt",
    "LISTING_KIT_README.txt",
    "SALES_LISTING_MANIFEST.json",
    "CHECKSUMS.txt",
)
REQUIRED_LISTING_IMAGE_FILES = tuple(f"images/{spec['filename']}" for spec in SCREENSHOT_ASSETS)


def create_sales_listing_kit(project_dir: Path, *, strict: bool = False) -> SalesListingKit:
    project_dir = project_dir.resolve()
    sales_dir = project_dir / ".auto-note" / "sales"
    listing_root = sales_dir / "listing-kits"
    listing_root.mkdir(parents=True, exist_ok=True)
    directory = unique_path(listing_root / f"auto-note-sales-listing-kit-{datetime.now():%Y%m%d-%H%M%S}")
    directory.mkdir(parents=True, exist_ok=False)

    materials_source = _latest_or_create_sales_materials(project_dir)
    screenshot_source = _latest_valid_or_create_screenshot_pack(project_dir)

    images_dir = directory / "images"
    images_dir.mkdir(parents=True, exist_ok=False)
    materials_path = directory / "SALES_MATERIALS.md"
    captions_path = directory / "SCREENSHOT_CAPTIONS.md"
    preview_path = directory / "index.html"
    readme_path = directory / "LISTING_KIT_README.txt"
    checklist_path = directory / "LISTING_UPLOAD_CHECKLIST.txt"
    manifest_path = directory / "SALES_LISTING_MANIFEST.json"
    checksums_path = directory / "CHECKSUMS.txt"

    shutil.copy2(materials_source, materials_path)
    shutil.copy2(screenshot_source / "SCREENSHOT_CAPTIONS.md", captions_path)
    shutil.copy2(screenshot_source / "index.html", preview_path)
    for spec in SCREENSHOT_ASSETS:
        filename = str(spec["filename"])
        shutil.copy2(screenshot_source / filename, images_dir / filename)

    write_text_atomic(readme_path, _render_listing_readme(materials_source, screenshot_source))
    write_text_atomic(checklist_path, _render_listing_checklist(materials_source, screenshot_source))

    entries = _file_entries(directory, exclude_names={"SALES_LISTING_MANIFEST.json", "CHECKSUMS.txt"})
    manifest = _build_manifest(
        directory=directory,
        materials_source=materials_source,
        screenshot_source=screenshot_source,
        entries=entries,
        strict=strict,
    )
    write_text_atomic(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    checksum_entries = _file_entries(directory, exclude_names={"CHECKSUMS.txt"})
    write_text_atomic(checksums_path, _render_checksums(checksum_entries))

    package_path = unique_path(sales_dir / f"{directory.name}.zip")
    _write_listing_zip(directory, package_path)
    return SalesListingKit(
        directory=directory,
        package_path=package_path,
        materials_path=materials_path,
        screenshot_pack_path=screenshot_source,
        manifest_path=manifest_path,
        checklist_path=checklist_path,
        readme_path=readme_path,
    )


def list_sales_listing_kits(project_dir: Path) -> list[Path]:
    root = project_dir / ".auto-note" / "sales" / "listing-kits"
    if not root.exists():
        return []
    return sorted(
        [path for path in root.glob("auto-note-sales-listing-kit-*") if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def list_sales_listing_packages(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(
        [path for path in sales_dir.glob("auto-note-sales-listing-kit-*.zip") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def verify_sales_listing_kit(path: Path, *, strict: bool = False, project_dir: Path | None = None) -> list[str]:
    path = path.resolve()
    if not path.exists():
        return [f"sales listing kit not found: {path}"]
    if path.is_dir():
        return _verify_listing_directory(path, strict=strict, project_dir=project_dir)
    if path.suffix.casefold() == ".zip":
        return _verify_listing_zip(path, strict=strict, project_dir=project_dir)
    return [f"sales listing kit must be a folder or zip: {path}"]


def format_sales_listing_kit(kit: SalesListingKit) -> str:
    return "\n".join(
        [
            "Sales listing kit / 販売ページ掲載キット",
            "",
            f"directory: {kit.directory}",
            f"package: {kit.package_path}",
            f"materials: {kit.materials_path}",
            f"screenshots: {kit.screenshot_pack_path}",
            f"manifest: {kit.manifest_path}",
            f"checklist: {kit.checklist_path}",
            "",
            "Seller use:",
            "- Upload images/01-*.svg through images/05-*.svg to the sales page.",
            "- Copy title, short description, feature bullets, FAQ, and support text from SALES_MATERIALS.md.",
            "- Use SCREENSHOT_CAPTIONS.md for each image caption.",
            "- Keep this kit as seller-side listing evidence; do not send it as the buyer delivery ZIP.",
        ]
    )


def format_sales_listing_verification(path: Path, errors: list[str], *, strict: bool = False) -> str:
    mode = "strict" if strict else "structure"
    if not errors:
        return f"[OK] sales listing kit verified ({mode}): {path}"
    lines = [f"[NG] sales listing kit verification failed ({mode}): {path}"]
    lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def _latest_or_create_sales_materials(project_dir: Path) -> Path:
    materials = list_sales_materials(project_dir)
    if materials:
        return materials[0]
    return create_sales_materials(project_dir).path


def _latest_valid_or_create_screenshot_pack(project_dir: Path) -> Path:
    for path in list_sales_screenshot_packs(project_dir):
        if not verify_sales_screenshot_pack(path):
            return path
    return create_sales_screenshot_pack(project_dir).directory


def _render_listing_readme(materials_source: Path, screenshot_source: Path) -> str:
    image_names = "\n".join(f"- images/{spec['filename']}" for spec in SCREENSHOT_ASSETS)
    return (
        "auto-note sales listing kit / 販売ページ掲載キット\n"
        "\n"
        "This folder is for the seller's marketplace listing work.\n"
        "Buyer delivery package: no\n"
        "It is not the buyer delivery package and should not be sent as the purchased product.\n"
        "\n"
        "Use these files:\n"
        "- SALES_MATERIALS.md: title ideas, short description, feature bullets, FAQ, support scope, refund summary\n"
        "- SCREENSHOT_CAPTIONS.md: captions for each listing image\n"
        "- index.html: local preview of the listing image flow\n"
        "- images/: SVG images for the listing page\n"
        "- LISTING_UPLOAD_CHECKLIST.txt: final paste/upload checklist\n"
        "- SALES_LISTING_MANIFEST.json and CHECKSUMS.txt: seller evidence and file integrity\n"
        "\n"
        "Images:\n"
        f"{image_names}\n"
        "\n"
        f"materials_source: {materials_source.name}\n"
        f"screenshot_source: {screenshot_source.name}\n"
    )


def _render_listing_checklist(materials_source: Path, screenshot_source: Path) -> str:
    images = "\n".join(f"- [ ] Upload images/{spec['filename']}" for spec in SCREENSHOT_ASSETS)
    return (
        "Listing upload checklist / 販売ページ掲載チェック\n"
        "\n"
        "Seller-only artifact: yes\n"
        "Buyer delivery package: no\n"
        "\n"
        f"Materials source: {materials_source.name}\n"
        f"Screenshot source: {screenshot_source.name}\n"
        "\n"
        "Copy / paste:\n"
        "- [ ] Listing title copied from SALES_MATERIALS.md\n"
        "- [ ] Short description copied from SALES_MATERIALS.md\n"
        "- [ ] Feature bullets copied from SALES_MATERIALS.md\n"
        "- [ ] Requirements, important notes, support scope, and refund summary copied\n"
        "- [ ] Delivery message adjusted for the actual buyer delivery ZIP name\n"
        "\n"
        "Images:\n"
        f"{images}\n"
        "- [ ] Captions copied from SCREENSHOT_CAPTIONS.md\n"
        "- [ ] index.html preview checked after image upload order is chosen\n"
        "\n"
        "Before publishing:\n"
        "- [ ] note official API / login bypass is not advertised\n"
        "- [ ] Support contact is public URL or marketplace message flow, not a raw private email\n"
        "- [ ] Refund policy URL and support scope are visible on the sales page\n"
        "- [ ] Buyer delivery ZIP was verified separately with sales-handoff or sales-finalize\n"
        "- [ ] Do not send this ZIP to buyers\n"
        "- [ ] This listing kit ZIP is stored as seller evidence and is not attached to the buyer message\n"
    )


def _build_manifest(
    *,
    directory: Path,
    materials_source: Path,
    screenshot_source: Path,
    entries: list[dict[str, object]],
    strict: bool,
) -> dict[str, object]:
    return {
        "kind": "auto-note-sales-listing-kit",
        "seller_listing_only": True,
        "buyer_delivery": False,
        "do_not_send_to_buyer": True,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "auto_note_version": __version__,
        "strict_materials_check": strict,
        "materials_source": materials_source.name,
        "screenshot_pack_source": screenshot_source.name,
        "directory": directory.name,
        "files": entries,
        "file_count": len(entries),
    }


def _file_entries(root: Path, *, exclude_names: set[str] | None = None) -> list[dict[str, object]]:
    exclude_names = exclude_names or set()
    entries: list[dict[str, object]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in exclude_names:
            continue
        entries.append({"path": relative, "size": path.stat().st_size, "sha256": _sha256_file(path)})
    return entries


def _render_checksums(entries: list[dict[str, object]]) -> str:
    lines = [f"{entry['sha256']}  {entry['path']}" for entry in entries]
    return "\n".join(lines) + "\n"


def _write_listing_zip(directory: Path, package_path: Path) -> None:
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(item for item in directory.rglob("*") if item.is_file()):
            archive.write(path, path.relative_to(directory).as_posix())


def _verify_listing_directory(path: Path, *, strict: bool, project_dir: Path | None) -> list[str]:
    errors: list[str] = []
    for name in (*REQUIRED_LISTING_KIT_FILES, *REQUIRED_LISTING_IMAGE_FILES):
        file_path = path / name
        if not file_path.exists():
            errors.append(f"missing required file: {name}")
            continue
        if file_path.is_file() and file_path.stat().st_size == 0:
            errors.append(f"empty file: {name}")
    if errors:
        return errors
    data = {item.relative_to(path).as_posix(): item.read_bytes() for item in path.rglob("*") if item.is_file()}
    errors.extend(_verify_listing_bytes(data, strict=strict, project_dir=project_dir))
    return errors


def _verify_listing_zip(path: Path, *, strict: bool, project_dir: Path | None) -> list[str]:
    errors: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = {name for name in archive.namelist() if not name.endswith("/")}
            for name in (*REQUIRED_LISTING_KIT_FILES, *REQUIRED_LISTING_IMAGE_FILES):
                if name not in names:
                    errors.append(f"missing required file: {name}")
            if errors:
                return errors
            data = {name: archive.read(name) for name in names}
    except zipfile.BadZipFile:
        return [f"invalid zip file: {path}"]
    except OSError as exc:
        return [f"sales listing zip unreadable: {exc}"]
    errors.extend(_verify_listing_bytes(data, strict=strict, project_dir=project_dir))
    return errors


def _verify_listing_bytes(
    data: dict[str, bytes],
    *,
    strict: bool,
    project_dir: Path | None,
) -> list[str]:
    errors: list[str] = []
    for name in (*REQUIRED_LISTING_KIT_FILES, *REQUIRED_LISTING_IMAGE_FILES):
        content = data.get(name)
        if content is None:
            errors.append(f"missing required file: {name}")
        elif not content.strip():
            errors.append(f"empty file: {name}")
    if errors:
        return errors

    manifest_errors = _verify_manifest(data["SALES_LISTING_MANIFEST.json"])
    errors.extend(manifest_errors)
    errors.extend(_verify_checksums(data))
    errors.extend(_verify_materials(data["SALES_MATERIALS.md"], strict=strict, project_dir=project_dir))
    errors.extend(_verify_images(data))
    captions = data["SCREENSHOT_CAPTIONS.md"].decode("utf-8", errors="replace")
    for spec in SCREENSHOT_ASSETS:
        if str(spec["filename"]) not in captions:
            errors.append(f"missing caption entry: {spec['filename']}")
    readme = data["LISTING_KIT_README.txt"].decode("utf-8", errors="replace")
    checklist = data["LISTING_UPLOAD_CHECKLIST.txt"].decode("utf-8", errors="replace")
    for marker in ("Seller-only artifact: yes", "Buyer delivery package: no"):
        if marker not in checklist:
            errors.append(f"missing listing checklist guard: {marker}")
    if "not the buyer delivery package" not in readme:
        errors.append("README does not warn that the kit is not buyer delivery")
    return errors


def _verify_manifest(content: bytes) -> list[str]:
    try:
        manifest = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as exc:
        return [f"manifest is invalid JSON: {exc}"]
    errors: list[str] = []
    if manifest.get("kind") != "auto-note-sales-listing-kit":
        errors.append("manifest kind is not auto-note-sales-listing-kit")
    if manifest.get("seller_listing_only") is not True:
        errors.append("manifest seller_listing_only must be true")
    if manifest.get("buyer_delivery") is not False:
        errors.append("manifest buyer_delivery must be false")
    if manifest.get("do_not_send_to_buyer") is not True:
        errors.append("manifest do_not_send_to_buyer must be true")
    paths = {str(item.get("path")) for item in manifest.get("files", []) if isinstance(item, dict)}
    for name in ("SALES_MATERIALS.md", "SCREENSHOT_CAPTIONS.md", "index.html"):
        if name not in paths:
            errors.append(f"manifest missing file entry: {name}")
    return errors


def _verify_checksums(data: dict[str, bytes]) -> list[str]:
    errors: list[str] = []
    text = data["CHECKSUMS.txt"].decode("utf-8", errors="replace")
    checksums: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        digest, _separator, name = line.partition("  ")
        if not digest or not name:
            errors.append(f"malformed checksum line: {line}")
            continue
        checksums[name] = digest
    for name, content in data.items():
        if name == "CHECKSUMS.txt":
            continue
        expected = checksums.get(name)
        if expected is None:
            errors.append(f"missing checksum: {name}")
            continue
        actual = hashlib.sha256(content).hexdigest()
        if actual != expected:
            errors.append(f"checksum mismatch: {name}")
    return errors


def _verify_materials(content: bytes, *, strict: bool, project_dir: Path | None) -> list[str]:
    text = content.decode("utf-8", errors="replace")
    return [f"sales materials: {error}" for error in verify_sales_materials_text(text, strict=strict, project_dir=project_dir)]


def _verify_images(data: dict[str, bytes]) -> list[str]:
    errors: list[str] = []
    for spec in SCREENSHOT_ASSETS:
        name = f"images/{spec['filename']}"
        text = data[name].decode("utf-8", errors="replace")
        if "<svg" not in text or "</svg>" not in text:
            errors.append(f"invalid SVG markup: {name}")
        if str(spec["title"]) not in text:
            errors.append(f"missing title in image: {name}")
    return errors


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
