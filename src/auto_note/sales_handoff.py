from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any
import hashlib
import io
import json
import tempfile
import zipfile

from . import __version__
from .commercial import format_commercial_readiness_report, run_commercial_readiness
from .paths import unique_path
from .privacy import format_privacy_audit_report, has_privacy_audit_blockers, run_privacy_audit
from .release import format_release_verification, list_releases, verify_release_package


@dataclass(frozen=True)
class SalesHandoffResult:
    path: Path
    release_path: Path
    warnings: int


@dataclass(frozen=True)
class BuyerDeliveryResult:
    directory: Path
    release_path: Path
    buyer_start_path: Path
    buyer_handoff_path: Path
    buyer_support_guide_path: Path
    buyer_support_request_path: Path
    manifest_path: Path
    checksum_path: Path
    package_path: Path


def create_sales_handoff(project_dir: Path, *, strict: bool = False) -> SalesHandoffResult:
    project_dir = project_dir.resolve()
    releases = list_releases(project_dir)
    if not releases:
        raise ValueError("release package not found. Run auto-note preflight --project-dir . --create-release first.")
    release_path = releases[0]
    release_errors = verify_release_package(release_path)
    if release_errors:
        raise ValueError(f"latest release package is not verified: {release_errors[0]}")

    privacy = run_privacy_audit(project_dir, include_sales_handoffs=False)
    if has_privacy_audit_blockers(privacy):
        blocker = next((item for item in privacy.items if item.status == "fail"), None)
        detail = f": {blocker.name} - {blocker.detail}" if blocker else ""
        raise ValueError(f"privacy audit has blockers{detail}. Run auto-note privacy-audit --project-dir . first.")

    readiness = run_commercial_readiness(project_dir, include_sales_handoffs=False)
    if readiness.status == "fail":
        blocker = next((item for item in readiness.items if item.status == "fail"), None)
        detail = f": {blocker.name} - {blocker.detail}" if blocker else ""
        raise ValueError(f"commercial readiness is blocked{detail}. Run auto-note commercial-readiness --project-dir . first.")
    if strict and readiness.status == "warn":
        raise ValueError("commercial readiness still has warnings. Re-run without --strict to create an evidence package anyway.")

    created_at = datetime.now()
    handoff_dir = project_dir / ".auto-note" / "sales"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    handoff_path = unique_path(handoff_dir / f"auto-note-sales-handoff-{created_at:%Y%m%d-%H%M%S}.zip")
    temp_path = handoff_dir / f".{handoff_path.name}.tmp"

    release_bytes = release_path.read_bytes()
    entries = {
        "README.txt": _build_readme(release_path.name, readiness.status).encode("utf-8"),
        "BUYER_HANDOFF.txt": _build_buyer_handoff(release_path.name).encode("utf-8"),
        "BUYER_SUPPORT_GUIDE.txt": _build_buyer_support_guide(release_path.name).encode("utf-8"),
        "BUYER_SUPPORT_REQUEST.txt": _build_buyer_support_request(release_path.name).encode("utf-8"),
        "DELIVERY_CHECKLIST.txt": _build_delivery_checklist(release_path.name, readiness).encode("utf-8"),
        "SELLER_DELIVERY_RECEIPT.txt": _build_seller_delivery_receipt(
            release_path.name,
            handoff_path.name,
            created_at,
        ).encode("utf-8"),
        "SELLER_FINAL_CHECKLIST.txt": _build_seller_final_checklist(readiness).encode("utf-8"),
        "SUPPORT_RESPONSE_TEMPLATE.txt": _build_support_response_template().encode("utf-8"),
        "SALES_MATERIALS.md": _build_sales_materials_entry(project_dir),
        "COMMERCIAL_READINESS.txt": (format_commercial_readiness_report(readiness) + "\n").encode("utf-8"),
        "PRIVACY_AUDIT.txt": (format_privacy_audit_report(privacy) + "\n").encode("utf-8"),
        "RELEASE_VERIFICATION.txt": (format_release_verification(Path(release_path.name), release_errors) + "\n").encode("utf-8"),
        f"release/{release_path.name}": release_bytes,
    }
    records = [_record(name, data) for name, data in entries.items()]
    manifest = _build_manifest(created_at=created_at, release_name=release_path.name, readiness_status=readiness.status, records=records)
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    checksum_records = [*records, _record("SALES_HANDOFF_MANIFEST.json", manifest_bytes)]
    checksums = _build_checksums(checksum_records).encode("utf-8")

    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
            archive.writestr("SALES_HANDOFF_MANIFEST.json", manifest_bytes)
            archive.writestr("CHECKSUMS.txt", checksums)
        temp_path.replace(handoff_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    warnings = sum(1 for item in readiness.items if item.status == "warn")
    return SalesHandoffResult(handoff_path, release_path, warnings)


def list_sales_handoffs(project_dir: Path) -> list[Path]:
    handoff_dir = project_dir / ".auto-note" / "sales"
    if not handoff_dir.exists():
        return []
    return sorted(handoff_dir.glob("auto-note-sales-handoff-*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)


def list_buyer_deliveries(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(
        [path for path in sales_dir.glob("buyer-delivery-*") if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def list_buyer_delivery_packages(project_dir: Path) -> list[Path]:
    sales_dir = project_dir / ".auto-note" / "sales"
    if not sales_dir.exists():
        return []
    return sorted(
        sales_dir.glob("auto-note-buyer-delivery-*.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def verify_sales_handoff(handoff_path: Path) -> list[str]:
    errors: list[str] = []
    if not handoff_path.exists():
        return [f"sales handoff not found: {handoff_path}"]
    try:
        with zipfile.ZipFile(handoff_path) as archive:
            names = archive.namelist()
            errors.extend(_verify_names(names))
            for required in (
                "README.txt",
                "BUYER_HANDOFF.txt",
                "BUYER_SUPPORT_GUIDE.txt",
                "BUYER_SUPPORT_REQUEST.txt",
                "DELIVERY_CHECKLIST.txt",
                "SELLER_DELIVERY_RECEIPT.txt",
                "SELLER_FINAL_CHECKLIST.txt",
                "SUPPORT_RESPONSE_TEMPLATE.txt",
                "SALES_MATERIALS.md",
                "COMMERCIAL_READINESS.txt",
                "PRIVACY_AUDIT.txt",
                "RELEASE_VERIFICATION.txt",
                "SALES_HANDOFF_MANIFEST.json",
                "CHECKSUMS.txt",
            ):
                if required not in names:
                    errors.append(f"missing required file: {required}")
            release_entries = [name for name in names if name.startswith("release/") and name.lower().endswith(".zip")]
            if len(release_entries) != 1:
                errors.append(f"expected one nested release zip, found {len(release_entries)}")
            if "CHECKSUMS.txt" in names:
                errors.extend(_verify_checksums(archive))
            if "SALES_HANDOFF_MANIFEST.json" in names:
                errors.extend(_verify_manifest(archive))
            if "SALES_MATERIALS.md" in names:
                errors.extend(_verify_sales_materials_entry(archive))
            if "SELLER_DELIVERY_RECEIPT.txt" in names:
                release_name = PurePosixPath(release_entries[0]).name if release_entries else ""
                errors.extend(_verify_seller_delivery_receipt(archive, release_name))
            if release_entries:
                errors.extend(_verify_nested_release(archive, release_entries[0]))
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"unreadable sales handoff: {exc}")
    return errors


def extract_buyer_delivery(handoff_path: Path, *, output_dir: Path | None = None) -> BuyerDeliveryResult:
    handoff_path = handoff_path.resolve()
    errors = verify_sales_handoff(handoff_path)
    if errors:
        raise ValueError(f"sales handoff is not verified: {errors[0]}")

    if output_dir is None:
        stamp = handoff_path.stem.replace("auto-note-sales-handoff-", "") or datetime.now().strftime("%Y%m%d-%H%M%S")
        target_dir = unique_path(handoff_path.parent / f"buyer-delivery-{stamp}")
    else:
        target_dir = output_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now()
    with zipfile.ZipFile(handoff_path) as archive:
        release_entries = [name for name in archive.namelist() if name.startswith("release/") and name.lower().endswith(".zip")]
        if len(release_entries) != 1:
            raise ValueError(f"expected one nested release zip, found {len(release_entries)}")
        release_name = PurePosixPath(release_entries[0]).name
        release_bytes = archive.read(release_entries[0])
        buyer_start_bytes = _build_buyer_start_here(release_name).encode("utf-8")
        buyer_handoff_bytes = archive.read("BUYER_HANDOFF.txt")
        buyer_support_guide_bytes = archive.read("BUYER_SUPPORT_GUIDE.txt")
        buyer_support_request_bytes = archive.read("BUYER_SUPPORT_REQUEST.txt")
        release_path = unique_path(target_dir / release_name)
        release_path.write_bytes(release_bytes)
        buyer_start_path = unique_path(target_dir / "START_HERE_FOR_BUYER.txt")
        buyer_start_path.write_bytes(buyer_start_bytes)
        buyer_handoff_path = unique_path(target_dir / "BUYER_HANDOFF.txt")
        buyer_handoff_path.write_bytes(buyer_handoff_bytes)
        buyer_support_guide_path = unique_path(target_dir / "BUYER_SUPPORT_GUIDE.txt")
        buyer_support_guide_path.write_bytes(buyer_support_guide_bytes)
        buyer_support_request_path = unique_path(target_dir / "BUYER_SUPPORT_REQUEST.txt")
        buyer_support_request_path.write_bytes(buyer_support_request_bytes)
        records = [
            _record(release_path.name, release_bytes),
            _record(buyer_start_path.name, buyer_start_bytes),
            _record(buyer_handoff_path.name, buyer_handoff_bytes),
            _record(buyer_support_guide_path.name, buyer_support_guide_bytes),
            _record(buyer_support_request_path.name, buyer_support_request_bytes),
        ]
        manifest = _build_buyer_delivery_manifest(
            created_at=created_at,
            source_handoff_name=handoff_path.name,
            release_name=release_path.name,
            records=records,
        )
        manifest_path = target_dir / "BUYER_DELIVERY_MANIFEST.json"
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
        manifest_path.write_bytes(manifest_bytes)
        checksum_path = target_dir / "SHA256SUMS.txt"
        checksum_path.write_text(
            _build_checksums([*records, _record(manifest_path.name, manifest_bytes)]),
            encoding="utf-8",
        )
    package_path = package_buyer_delivery(target_dir)
    return BuyerDeliveryResult(
        target_dir,
        release_path,
        buyer_start_path,
        buyer_handoff_path,
        buyer_support_guide_path,
        buyer_support_request_path,
        manifest_path,
        checksum_path,
        package_path,
    )


def format_buyer_delivery_result(result: BuyerDeliveryResult) -> str:
    return "\n".join(
        [
            f"buyer delivery extracted: {result.directory}",
            f"- release package to send: {result.release_path.name}",
            f"- buyer start guide: {result.buyer_start_path.name}",
            f"- buyer handoff note: {result.buyer_handoff_path.name}",
            f"- buyer support guide: {result.buyer_support_guide_path.name}",
            f"- buyer support request template: {result.buyer_support_request_path.name}",
            f"- manifest file: {result.manifest_path.name}",
            f"- checksum file: {result.checksum_path.name}",
            f"- buyer delivery zip: {result.package_path.name}",
            "- keep the original auto-note-sales-handoff-*.zip as seller evidence.",
        ]
    )


def package_buyer_delivery(directory: Path, *, output_path: Path | None = None) -> Path:
    directory = directory.resolve()
    errors = verify_buyer_delivery(directory)
    if errors:
        raise ValueError(f"buyer delivery folder is not verified: {errors[0]}")
    if output_path is None:
        stamp = directory.name.replace("buyer-delivery-", "", 1) or datetime.now().strftime("%Y%m%d-%H%M%S")
        package_path = unique_path(directory.parent / f"auto-note-buyer-delivery-{stamp}.zip")
    else:
        package_path = output_path.resolve()
    if package_path.parent == directory:
        raise ValueError("buyer delivery package must be outside the buyer delivery folder.")
    package_path.parent.mkdir(parents=True, exist_ok=True)
    files = _buyer_delivery_root_files(directory)
    temp_path = package_path.parent / f".{package_path.name}.tmp"
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, path.name)
        temp_path.replace(package_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return package_path


def verify_buyer_delivery(directory: Path) -> list[str]:
    errors: list[str] = []
    if not directory.exists():
        return [f"buyer delivery folder not found: {directory}"]
    if not directory.is_dir():
        return [f"buyer delivery path is not a folder: {directory}"]

    files = [path for path in directory.rglob("*") if path.is_file()]
    release_files = [
        path
        for path in files
        if path.parent == directory
        and path.name.startswith("auto-note-release-")
        and path.suffix.casefold() == ".zip"
    ]
    if len(release_files) != 1:
        errors.append(f"expected one buyer-facing release zip at folder root, found {len(release_files)}")
    buyer_start = directory / "START_HERE_FOR_BUYER.txt"
    if not buyer_start.exists():
        errors.append("missing START_HERE_FOR_BUYER.txt")
    buyer_handoff = directory / "BUYER_HANDOFF.txt"
    if not buyer_handoff.exists():
        errors.append("missing BUYER_HANDOFF.txt")
    buyer_support_guide = directory / "BUYER_SUPPORT_GUIDE.txt"
    if not buyer_support_guide.exists():
        errors.append("missing BUYER_SUPPORT_GUIDE.txt")
    buyer_support_request = directory / "BUYER_SUPPORT_REQUEST.txt"
    if not buyer_support_request.exists():
        errors.append("missing BUYER_SUPPORT_REQUEST.txt")
    manifest_file = directory / "BUYER_DELIVERY_MANIFEST.json"
    if not manifest_file.exists():
        errors.append("missing BUYER_DELIVERY_MANIFEST.json")
    checksum_file = directory / "SHA256SUMS.txt"
    if not checksum_file.exists():
        errors.append("missing SHA256SUMS.txt")

    allowed = {buyer_start, buyer_handoff, buyer_support_guide, buyer_support_request, manifest_file, checksum_file}
    if release_files:
        allowed.add(release_files[0])
    extras = sorted(path.relative_to(directory).as_posix() for path in files if path not in allowed)
    if extras:
        errors.append(f"unexpected file(s) in buyer delivery folder: {', '.join(extras)}")

    if release_files:
        release_errors = verify_release_package(release_files[0])
        errors.extend(f"release package: {error}" for error in release_errors)
    if buyer_start.exists():
        try:
            start_text = buyer_start.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"START_HERE_FOR_BUYER.txt unreadable: {exc}")
        else:
            if "auto-note buyer start here" not in start_text:
                errors.append("START_HERE_FOR_BUYER.txt does not look like an auto-note buyer start guide")
            if release_files and release_files[0].name not in start_text:
                errors.append(f"START_HERE_FOR_BUYER.txt does not mention release package: {release_files[0].name}")
            for required_text in (
                "START_HERE.txt",
                "shortcuts\\install-auto-note.bat",
                "BUYER_SUPPORT_GUIDE.txt",
                "BUYER_SUPPORT_REQUEST.txt",
            ):
                if required_text not in start_text:
                    errors.append(f"START_HERE_FOR_BUYER.txt is missing {required_text}")
    if buyer_handoff.exists():
        try:
            text = buyer_handoff.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"BUYER_HANDOFF.txt unreadable: {exc}")
        else:
            if "auto-note buyer handoff" not in text:
                errors.append("BUYER_HANDOFF.txt does not look like an auto-note buyer handoff")
            if release_files and release_files[0].name not in text:
                errors.append(f"BUYER_HANDOFF.txt does not mention release package: {release_files[0].name}")
            if "購入者の最初の10分" not in text:
                errors.append("BUYER_HANDOFF.txt is missing the buyer first 10 minutes section")
    if buyer_support_guide.exists():
        try:
            support_text = buyer_support_guide.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"BUYER_SUPPORT_GUIDE.txt unreadable: {exc}")
        else:
            if "auto-note buyer support guide" not in support_text:
                errors.append("BUYER_SUPPORT_GUIDE.txt does not look like an auto-note buyer support guide")
            if "auto-note support --project-dir . --bundle" not in support_text:
                errors.append("BUYER_SUPPORT_GUIDE.txt is missing support bundle instructions")
            if "BUYER_SUPPORT_REQUEST.txt" not in support_text:
                errors.append("BUYER_SUPPORT_GUIDE.txt is missing support request template instructions")
            if release_files and release_files[0].name not in support_text:
                errors.append(f"BUYER_SUPPORT_GUIDE.txt does not mention release package: {release_files[0].name}")
    if buyer_support_request.exists():
        try:
            request_text = buyer_support_request.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"BUYER_SUPPORT_REQUEST.txt unreadable: {exc}")
        else:
            if "auto-note buyer support request" not in request_text:
                errors.append("BUYER_SUPPORT_REQUEST.txt does not look like an auto-note buyer support request template")
            for required_text in (
                "Order ID / 注文ID",
                "Support bundle / 問い合わせ一式ZIP",
                ".auto-note\\support\\auto-note-support-bundle-*.zip",
                "Do not include / 入れないもの",
            ):
                if required_text not in request_text:
                    errors.append(f"BUYER_SUPPORT_REQUEST.txt is missing {required_text}")
            if release_files and release_files[0].name not in request_text:
                errors.append(f"BUYER_SUPPORT_REQUEST.txt does not mention release package: {release_files[0].name}")
    if manifest_file.exists():
        errors.extend(
            _verify_buyer_delivery_manifest(
                directory,
                release_files,
                buyer_start,
                buyer_handoff,
                buyer_support_guide,
                buyer_support_request,
                manifest_file,
            )
        )
    if checksum_file.exists():
        errors.extend(
            _verify_buyer_delivery_checksums(
                directory,
                release_files,
                buyer_start,
                buyer_handoff,
                buyer_support_guide,
                buyer_support_request,
                manifest_file,
                checksum_file,
            )
        )
    return errors


def verify_buyer_delivery_package(package_path: Path) -> list[str]:
    errors: list[str] = []
    if not package_path.exists():
        return [f"buyer delivery zip not found: {package_path}"]
    if not package_path.is_file():
        return [f"buyer delivery zip path is not a file: {package_path}"]
    try:
        with zipfile.ZipFile(package_path) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            errors.extend(_verify_names(names))
            release_entries = [
                name
                for name in names
                if PurePosixPath(name).parent == PurePosixPath(".")
                and PurePosixPath(name).name.startswith("auto-note-release-")
                and PurePosixPath(name).suffix.casefold() == ".zip"
            ]
            if len(release_entries) != 1:
                errors.append(f"expected one buyer-facing release zip at package root, found {len(release_entries)}")
            for required in (
                "START_HERE_FOR_BUYER.txt",
                "BUYER_HANDOFF.txt",
                "BUYER_SUPPORT_GUIDE.txt",
                "BUYER_SUPPORT_REQUEST.txt",
                "BUYER_DELIVERY_MANIFEST.json",
                "SHA256SUMS.txt",
            ):
                if required not in names:
                    errors.append(f"missing required buyer package file: {required}")
            allowed = {
                *(release_entries[:1]),
                "START_HERE_FOR_BUYER.txt",
                "BUYER_HANDOFF.txt",
                "BUYER_SUPPORT_GUIDE.txt",
                "BUYER_SUPPORT_REQUEST.txt",
                "BUYER_DELIVERY_MANIFEST.json",
                "SHA256SUMS.txt",
            }
            extras = sorted(name for name in names if name not in allowed)
            if extras:
                errors.append(f"unexpected file(s) in buyer delivery zip: {', '.join(extras)}")
            if (
                release_entries
                and "START_HERE_FOR_BUYER.txt" in names
                and "BUYER_HANDOFF.txt" in names
                and "BUYER_SUPPORT_GUIDE.txt" in names
                and "BUYER_SUPPORT_REQUEST.txt" in names
                and "BUYER_DELIVERY_MANIFEST.json" in names
                and "SHA256SUMS.txt" in names
            ):
                with tempfile.TemporaryDirectory() as tmp:
                    temp_dir = Path(tmp)
                    for name in (
                        release_entries[0],
                        "START_HERE_FOR_BUYER.txt",
                        "BUYER_HANDOFF.txt",
                        "BUYER_SUPPORT_GUIDE.txt",
                        "BUYER_SUPPORT_REQUEST.txt",
                        "BUYER_DELIVERY_MANIFEST.json",
                        "SHA256SUMS.txt",
                    ):
                        (temp_dir / PurePosixPath(name).name).write_bytes(archive.read(name))
                    errors.extend(verify_buyer_delivery(temp_dir))
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"unreadable buyer delivery zip: {exc}")
    return errors


def format_buyer_delivery_verification(directory: Path, errors: list[str]) -> str:
    if not errors:
        files = sorted(path.name for path in directory.iterdir() if path.is_file())
        lines = [f"[OK] buyer delivery verified: {directory}", "Files:"]
        lines.extend(f"- {name}" for name in files)
        lines.append("Send these files as the buyer delivery folder, or upload the verified auto-note-buyer-delivery-*.zip.")
        lines.append("Tell the buyer to open START_HERE_FOR_BUYER.txt first.")
        return "\n".join(lines)
    lines = [f"[NG] buyer delivery verification failed: {directory}"]
    lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def format_buyer_delivery_package_verification(package_path: Path, errors: list[str]) -> str:
    if not errors:
        try:
            with zipfile.ZipFile(package_path) as archive:
                files = sorted(name for name in archive.namelist() if not name.endswith("/"))
        except (OSError, zipfile.BadZipFile):
            files = []
        lines = [f"[OK] buyer delivery zip verified: {package_path}", "Files:"]
        lines.extend(f"- {name}" for name in files)
        try:
            package_bytes = package_path.read_bytes()
        except OSError:
            package_bytes = b""
        if package_bytes:
            lines.append(f"Package bytes: {len(package_bytes)}")
            lines.append(f"Package SHA-256: {hashlib.sha256(package_bytes).hexdigest()}")
        lines.append("Upload this ZIP as the buyer-facing delivery package, and keep the sales handoff ZIP as seller evidence.")
        lines.append("Tell the buyer to open START_HERE_FOR_BUYER.txt first.")
        return "\n".join(lines)
    lines = [f"[NG] buyer delivery zip verification failed: {package_path}"]
    lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def format_sales_handoff_verification(handoff_path: Path, errors: list[str]) -> str:
    if not errors:
        return f"[OK] sales handoff verified: {handoff_path}"
    lines = [f"[NG] sales handoff verification failed: {handoff_path}"]
    lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def _build_readme(release_name: str, readiness_status: str) -> str:
    return (
        "auto-note sales handoff\n\n"
        f"Release package: release/{release_name}\n"
        f"Commercial readiness status: {readiness_status}\n\n"
        "Files:\n"
        "- release/: Buyer-facing auto-note release zip.\n"
        "- BUYER_HANDOFF.txt: Short handoff note you can paste into the delivery message.\n"
        "- BUYER_SUPPORT_GUIDE.txt: What the buyer should send if they need support.\n"
        "- BUYER_SUPPORT_REQUEST.txt: Fillable support request template for the buyer.\n"
        "- DELIVERY_CHECKLIST.txt: What to send to the buyer and what to keep as seller evidence.\n"
        "- SELLER_DELIVERY_RECEIPT.txt: Seller-side order and delivery record template.\n"
        "- SELLER_FINAL_CHECKLIST.txt: Final seller-side confirmation before delivery.\n"
        "- SUPPORT_RESPONSE_TEMPLATE.txt: First reply template for buyer support requests.\n"
        "- SALES_MATERIALS.md: Marketplace listing, delivery, FAQ, support, and refund copy drafts.\n"
        "- COMMERCIAL_READINESS.txt: Seller-facing readiness evidence.\n"
        "- PRIVACY_AUDIT.txt: Privacy-safe audit result for generated artifacts.\n"
        "- RELEASE_VERIFICATION.txt: Release manifest/checksum verification result.\n"
        "- SALES_HANDOFF_MANIFEST.json and CHECKSUMS.txt: Contents and SHA-256 checksums.\n\n"
        "Before delivery:\n"
        "- Open COMMERCIAL_READINESS.txt and resolve or consciously accept remaining warnings.\n"
        "- Confirm your sales page, refund terms, and support scope match the saved commercial setup.\n"
        "- Send the release zip under release/ to the buyer. Keep this handoff zip as your seller evidence.\n"
    )


def _build_buyer_handoff(release_name: str) -> str:
    return (
        "auto-note buyer handoff / 購入者向け納品メモ\n\n"
        f"Attached release package: {release_name}\n"
        f"添付する配布ZIP: {release_name}\n\n"
        "Suggested delivery note / 納品メッセージ案:\n"
        "ご購入ありがとうございます。添付の配布ZIPを展開し、まず START_HERE.txt を開いてください。"
        "その後 shortcuts\\install-auto-note.bat を実行し、デスクトップまたはスタートメニューの auto-note を起動します。"
        "起動後は 受入チェック と スターター一式 で最初の動作確認を行ってください。"
        "もし起動しない場合は auto-note-gui.bat を直接開き、表示された内容と ヘルプ > 問い合わせ一式 で作成したZIPを共有してください。\n\n"
        "Buyer first 10 minutes / 購入者の最初の10分:\n"
        "1. 配布ZIPを展開します。\n"
        "2. START_HERE.txt を開きます。\n"
        "3. shortcuts\\install-auto-note.bat を実行します。\n"
        "4. auto-note を開き、受入チェックを実行します。\n"
        "5. スターター一式でサンプル記事、予定、アイデアを作ります。\n"
        "6. 投稿ヘルパーを開き、タイトル/本文/タグをコピーできることを確認します。\n"
        "7. 普段使うブラウザでnote.comにログインし、貼り付け運用を確認します。\n"
        "8. 困った時は ヘルプ > 問い合わせ一式 を作成します。\n"
    )


def _build_buyer_support_guide(release_name: str) -> str:
    return (
        "auto-note buyer support guide / 購入者向けサポートガイド\n\n"
        f"Release package / 配布ZIP: {release_name}\n\n"
        "Before contacting support / 連絡前に試すこと:\n"
        "1. 展開したフォルダの START_HERE.txt をもう一度確認してください。\n"
        "2. ショートカットで起動しない場合は auto-note-gui.bat を直接開いてください。\n"
        "3. GUIが開く場合は ヘルプ > 問い合わせ一式 を作成してください。\n"
        "4. CLIが使える場合は次を実行してください:\n"
        "   auto-note support --project-dir . --bundle\n"
        "5. note.com のログインが安全ではない可能性で止まる場合は、普段のブラウザでnote.comへログインし、投稿ヘルパーの貼り付け運用を使ってください。\n\n"
        "What to send / 送ってほしいもの:\n"
        "- 記入済みの BUYER_SUPPORT_REQUEST.txt\n"
        "- 問い合わせ一式ZIP: .auto-note\\support\\auto-note-support-bundle-*.zip\n"
        "- エラー画面のスクリーンショット\n"
        "- 何を押した直後に起きたか\n"
        "- 期待した動きと実際の動き\n"
        "- このファイルに書かれた配布ZIP名\n\n"
        "Use the request template / 問い合わせ票:\n"
        "- BUYER_SUPPORT_REQUEST.txt を開き、分かる範囲だけ記入して一緒に送ってください。\n"
        "- 分からない欄は空欄のままで構いません。\n\n"
        "Do not send unless asked / 通常は送らないもの:\n"
        "- noteアカウントのパスワードやログインコード\n"
        "- 記事本文全文、未公開原稿、個人メモ\n"
        "- .venv フォルダや Python 本体\n"
        "- 住所、電話番号、支払い情報が写ったスクリーンショット\n\n"
        "Privacy note / プライバシー:\n"
        "問い合わせ一式は標準でパス、ユーザー名、メール、記事タイトル、記事ファイル名を隠します。"
        "送付前に中身を確認し、不要な個人情報がないか見てください。\n"
    )


def _build_buyer_support_request(release_name: str) -> str:
    return (
        "auto-note buyer support request / 購入者向け問い合わせ票\n\n"
        f"Release package / 配布ZIP: {release_name}\n\n"
        "Fill in what you can / 分かる範囲で記入:\n"
        "- Order ID / 注文ID:\n"
        "- Marketplace / 購入した販売先:\n"
        "- Buyer name or handle / 購入者名またはハンドル:\n"
        "- Windows version / Windowsバージョン:\n"
        "- auto-note version / auto-noteバージョン:\n"
        "- Buyer delivery ZIP / 納品ZIP名:\n"
        f"- Release ZIP / 配布ZIP名: {release_name}\n"
        "- What you clicked / 押したもの:\n"
        "- Expected result / 期待した動き:\n"
        "- Actual result / 実際の動き:\n"
        "- Error message / 表示されたエラー:\n"
        "- Screenshot attached / スクリーンショット添付: yes/no\n"
        "- Support bundle / 問い合わせ一式ZIP: .auto-note\\support\\auto-note-support-bundle-*.zip\n"
        "- Support bundle attached / 問い合わせ一式ZIP添付: yes/no\n"
        "- SHA-256 checked / SHA-256確認: yes/no\n\n"
        "Attach / 添付するもの:\n"
        "[ ] This BUYER_SUPPORT_REQUEST.txt after filling it in\n"
        "[ ] .auto-note\\support\\auto-note-support-bundle-*.zip if available\n"
        "[ ] Screenshot of the error window if available\n\n"
        "Do not include / 入れないもの:\n"
        "- note password, login code, payment information, address, phone number\n"
        "- full unpublished article text or private notes\n"
        "- .venv folder, Python installer, or the whole workspace\n"
    )


def _build_buyer_start_here(release_name: str) -> str:
    return (
        "auto-note buyer start here / 購入者向け最初に読むメモ\n\n"
        f"Release package / 配布ZIP: {release_name}\n\n"
        "What this ZIP is / このZIPについて:\n"
        "- この auto-note-buyer-delivery-*.zip は購入者へそのまま渡すための納品物です。\n"
        "- まず同梱の配布ZIPを展開し、展開先の START_HERE.txt を開いてください。\n"
        "- このファイル、BUYER_HANDOFF.txt、BUYER_SUPPORT_GUIDE.txt、BUYER_SUPPORT_REQUEST.txt は、迷った時に確認する短い案内です。\n\n"
        "First 10 minutes / 最初の10分:\n"
        "1. auto-note-buyer-delivery-*.zip を展開します。\n"
        f"2. {release_name} を展開します。\n"
        "3. 展開先の START_HERE.txt を開きます。\n"
        "4. shortcuts\\install-auto-note.bat を実行します。\n"
        "5. デスクトップまたはスタートメニューの auto-note を起動します。\n"
        "6. GUIで 受入チェック を実行し、導入状態を確認します。\n"
        "7. スターター一式 を実行して、サンプル記事、予定、アイデアを作ります。\n"
        "8. 投稿ヘルパーでタイトル/本文/タグをコピーできることを確認します。\n\n"
        "note.com login / note.comログイン:\n"
        "- 自動ログインが「安全ではない可能性」で止まる場合は、普段使うブラウザでnote.comにログインしてください。\n"
        "- その後、投稿ヘルパーの貼り付け運用でタイトル、本文、タグをコピーして投稿できます。\n\n"
        "When something does not work / 困った時:\n"
        "- BUYER_SUPPORT_GUIDE.txt を開き、問い合わせ前に試すことを確認してください。\n"
        "- BUYER_SUPPORT_REQUEST.txt に状況を書いて、問い合わせ一式ZIPやスクリーンショットと一緒に送ってください。\n"
        "- GUIが開く場合は ヘルプ > 問い合わせ一式 を作成してください。\n"
        "- GUIが開かない場合は auto-note-gui.bat を直接開き、表示されたエラー画面を共有してください。\n"
    )


def _build_delivery_checklist(release_name: str, readiness) -> str:
    remaining = [item for item in readiness.items if item.status in {"warn", "fail"}]
    lines = [
        "auto-note delivery checklist / 納品チェックリスト",
        "",
        "Buyer delivery / 購入者に送るもの",
        "- auto-note-buyer-delivery-*.zip",
        f"- release/{release_name}",
        "- START_HERE_FOR_BUYER.txt の最初に読む案内",
        "- BUYER_HANDOFF.txt の納品メッセージ案",
        "- BUYER_SUPPORT_GUIDE.txt の問い合わせ手順",
        "- BUYER_SUPPORT_REQUEST.txt の問い合わせ記入票",
        "",
        "Seller evidence / 販売者が保管するもの",
        "- This full auto-note-sales-handoff-*.zip",
        "- SELLER_DELIVERY_RECEIPT.txt に記録した注文ID、送付日時、購入者向けZIP名",
        "- COMMERCIAL_READINESS.txt",
        "- PRIVACY_AUDIT.txt",
        "- RELEASE_VERIFICATION.txt",
        "- SALES_HANDOFF_MANIFEST.json and CHECKSUMS.txt",
        "",
        "Do not send by default / 通常は送らないもの",
        "- .auto-note folder",
        "- articles folder",
        "- diagnostic/support ZIPs unless the buyer asks for support",
        "- raw article drafts, private notes, screenshots with account details",
        "",
        "Before sending / 送信前",
        "- Confirm the buyer-facing attachment is the release ZIP, not this seller evidence ZIP.",
        "- Paste the buyer handoff message into the marketplace delivery message.",
        "- Confirm the sales page support scope and refund policy match your seller settings.",
        "- Save the order ID, delivery time, release ZIP name, and this handoff ZIP name in your records.",
        "- Ask the buyer to run the first 10 minutes checklist before opening a support request.",
        "",
        "Remaining readiness / 残確認",
    ]
    if remaining:
        for item in remaining:
            label = {"warn": "WARN", "fail": "NG"}.get(item.status, item.status.upper())
            lines.append(f"- [{label}] {item.name}: {item.detail}")
            if item.action:
                lines.append(f"  next: {item.action}")
    else:
        lines.append("- No warning/blocking items remain.")
    return "\n".join(lines) + "\n"


def _build_seller_final_checklist(readiness) -> str:
    lines = [
        "auto-note seller final checklist",
        "",
        f"Commercial readiness status: {readiness.status}",
        "",
        "Before listing or delivery",
        "- Confirm the sales page describes the exact included release zip.",
        "- Confirm refund terms, support scope, and response hours are written on the sales page.",
        "- Confirm the buyer receives only release/auto-note-release-*.zip, not this seller evidence zip.",
        "- Keep this handoff zip for your own audit trail.",
        "",
        "Readiness items",
    ]
    remaining = 0
    for item in readiness.items:
        label = {"pass": "OK", "info": "INFO", "warn": "WARN", "fail": "NG"}.get(item.status, item.status.upper())
        lines.append(f"[{label}] {item.name}: {item.detail}")
        if item.status in {"warn", "fail"}:
            remaining += 1
        if item.action:
            lines.append(f"  next: {item.action}")
    lines.extend(
        [
            "",
            "Remaining seller actions",
            f"- {remaining} warning/blocking item(s) remain." if remaining else "- No warning/blocking items remain.",
            "- Re-run auto-note commercial-readiness --project-dir . after changing seller settings or documents.",
            "- Use auto-note sales-handoff --project-dir . --strict when you want warnings to block the final package.",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_seller_delivery_receipt(release_name: str, handoff_name: str, created_at: datetime) -> str:
    return (
        "auto-note seller delivery receipt / 販売者向け納品記録テンプレ\n\n"
        f"Created at / 作成日時: {created_at.isoformat(timespec='seconds')}\n"
        f"Sales handoff ZIP / 販売者証跡ZIP: {handoff_name}\n"
        f"Release package / 配布ZIP: {release_name}\n"
        "Buyer delivery ZIP / 購入者へ送るZIP: auto-note-buyer-delivery-YYYYMMDD-HHMMSS.zip\n"
        "SHA-256 / 改ざん確認: CHECKSUMS.txt と BUYER_DELIVERY_MANIFEST.json を確認\n\n"
        "Order record / 注文記録:\n"
        "- Order ID / 注文ID:\n"
        "- Buyer name or marketplace handle / 購入者名または取引ID:\n"
        "- Marketplace URL / 販売ページURL:\n"
        "- Delivered at / 納品日時:\n"
        "- Delivered file / 送付ファイル:\n"
        "- Support contact used / 案内したサポート連絡先:\n\n"
        "Before sending / 送付前チェック:\n"
        "[ ] auto-note-buyer-delivery-*.zip を作成した\n"
        "[ ] auto-note sales-handoff --verify-buyer-package で購入者向けZIPを検証した\n"
        "[ ] 購入者へ販売者証跡ZIPではなく購入者向けZIPを送る\n"
        "[ ] BUYER_HANDOFF.txt の納品メッセージを販売サイトのメッセージ欄へ貼った\n"
        "[ ] サポート範囲、返金条件、連絡先が販売ページと一致している\n\n"
        "Support history / 対応履歴:\n"
        "- YYYY-MM-DD: \n"
    )


def _build_support_response_template() -> str:
    return (
        "auto-note support response template\n\n"
        "Subject: auto-note support request\n\n"
        "Thank you for reaching out. To help diagnose the issue, please send the following:\n\n"
        "1. The filled BUYER_SUPPORT_REQUEST.txt from your buyer delivery ZIP.\n"
        "2. What you clicked immediately before the issue happened.\n"
        "3. A screenshot of the message or window.\n"
        "4. Your Windows version if you know it.\n"
        "5. The support bundle created from Help > Support bundle, or by running:\n"
        "   auto-note support --project-dir . --bundle\n\n"
        "Please do not paste private article text into the message. The support bundle is designed to avoid raw article content.\n\n"
        "First checks to suggest:\n"
        "- Run auto-note-gui.bat directly if the shortcut does not open.\n"
        "- Run auto-note troubleshoot --project-dir . and share the summary lines.\n"
        "- If note login is blocked as unsafe, log in with the normal browser and use the posting helper paste flow.\n"
    )


def _build_sales_materials_entry(project_dir: Path) -> bytes:
    from .sales_materials import build_sales_materials, list_sales_materials, verify_sales_materials_text

    for path in list_sales_materials(project_dir):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not verify_sales_materials_text(text):
            return text.encode("utf-8")
    text, _placeholders = build_sales_materials(project_dir)
    return text.encode("utf-8")


def _build_manifest(
    *,
    created_at: datetime,
    release_name: str,
    readiness_status: str,
    records: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "name": "auto-note sales handoff",
        "version": __version__,
        "created_at": created_at.isoformat(timespec="seconds"),
        "release_package": release_name,
        "readiness_status": readiness_status,
        "privacy": {
            "includes_user_articles": False,
            "includes_generated_helpers": False,
            "includes_virtualenv": False,
            "includes_seller_evidence_only": True,
        },
        "file_count": len(records),
        "files": records,
    }


def _build_buyer_delivery_manifest(
    *,
    created_at: datetime,
    source_handoff_name: str,
    release_name: str,
    records: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "name": "auto-note buyer delivery",
        "version": __version__,
        "created_at": created_at.isoformat(timespec="seconds"),
        "source_sales_handoff": source_handoff_name,
        "release_package": release_name,
        "privacy": {
            "includes_user_articles": False,
            "includes_generated_helpers": False,
            "includes_virtualenv": False,
            "includes_seller_evidence": False,
            "buyer_facing_only": True,
        },
        "file_count": len(records),
        "files": records,
    }


def _record(name: str, data: bytes) -> dict[str, object]:
    return {
        "path": name,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _build_checksums(records: list[dict[str, object]]) -> str:
    return "\n".join(f"{record['sha256']}  {record['path']}" for record in records) + "\n"


def _verify_names(names: list[str]) -> list[str]:
    errors: list[str] = []
    for name in names:
        normalized = name.replace("\\", "/")
        parts = PurePosixPath(normalized).parts
        if not normalized or normalized.startswith("/") or ".." in parts or any(":" in part for part in parts):
            errors.append(f"unsafe file name: {name}")
        if normalized != name:
            errors.append(f"non-normalized file name: {name}")
    return errors


def _verify_checksums(archive: zipfile.ZipFile) -> list[str]:
    errors: list[str] = []
    checked: set[str] = set()
    lines = archive.read("CHECKSUMS.txt").decode("utf-8", errors="replace").splitlines()
    names = set(archive.namelist())
    for line in lines:
        if not line.strip():
            continue
        try:
            expected, name = line.split("  ", 1)
        except ValueError:
            errors.append(f"invalid checksum line: {line}")
            continue
        if name not in names:
            errors.append(f"checksum target missing: {name}")
            continue
        checked.add(name)
        actual = hashlib.sha256(archive.read(name)).hexdigest()
        if actual != expected:
            errors.append(f"checksum mismatch: {name}")
    for required in (
        "README.txt",
        "BUYER_HANDOFF.txt",
        "BUYER_SUPPORT_GUIDE.txt",
        "BUYER_SUPPORT_REQUEST.txt",
        "SELLER_DELIVERY_RECEIPT.txt",
        "SELLER_FINAL_CHECKLIST.txt",
        "SUPPORT_RESPONSE_TEMPLATE.txt",
        "SALES_MATERIALS.md",
        "COMMERCIAL_READINESS.txt",
        "PRIVACY_AUDIT.txt",
        "RELEASE_VERIFICATION.txt",
        "SALES_HANDOFF_MANIFEST.json",
    ):
        if required in names and required not in checked:
            errors.append(f"checksum missing: {required}")
    return errors


def _verify_buyer_delivery_checksums(
    directory: Path,
    release_files: list[Path],
    buyer_start: Path,
    buyer_handoff: Path,
    buyer_support_guide: Path,
    buyer_support_request: Path,
    manifest_file: Path,
    checksum_file: Path,
) -> list[str]:
    errors: list[str] = []
    checked: set[str] = set()
    targets = {
        path.name: path
        for path in [
            *release_files,
            buyer_start,
            buyer_handoff,
            buyer_support_guide,
            buyer_support_request,
            manifest_file,
        ]
        if path.exists()
    }
    try:
        lines = checksum_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return [f"SHA256SUMS.txt unreadable: {exc}"]
    for line in lines:
        if not line.strip():
            continue
        try:
            expected, name = line.split("  ", 1)
        except ValueError:
            errors.append(f"invalid buyer checksum line: {line}")
            continue
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            errors.append(f"invalid buyer checksum value: {name}")
            continue
        if "/" in name or "\\" in name or ":" in name or name in ("", ".", ".."):
            errors.append(f"unsafe buyer checksum target: {name}")
            continue
        target = targets.get(name)
        if target is None or target.parent != directory:
            errors.append(f"buyer checksum target missing: {name}")
            continue
        checked.add(name)
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"buyer checksum mismatch: {name}")
    for name in targets:
        if name not in checked:
            errors.append(f"buyer checksum missing: {name}")
    return errors


def _buyer_delivery_root_files(directory: Path) -> list[Path]:
    release_files = sorted(
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.name.startswith("auto-note-release-")
        and path.suffix.casefold() == ".zip"
    )
    files: list[Path] = []
    if release_files:
        files.append(release_files[0])
    files.extend(
        [
            directory / "START_HERE_FOR_BUYER.txt",
            directory / "BUYER_HANDOFF.txt",
            directory / "BUYER_SUPPORT_GUIDE.txt",
            directory / "BUYER_SUPPORT_REQUEST.txt",
            directory / "BUYER_DELIVERY_MANIFEST.json",
            directory / "SHA256SUMS.txt",
        ]
    )
    return files


def _verify_buyer_delivery_manifest(
    directory: Path,
    release_files: list[Path],
    buyer_start: Path,
    buyer_handoff: Path,
    buyer_support_guide: Path,
    buyer_support_request: Path,
    manifest_file: Path,
) -> list[str]:
    errors: list[str] = []
    try:
        raw: Any = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"BUYER_DELIVERY_MANIFEST.json unreadable: {exc}"]
    if not isinstance(raw, dict):
        return ["BUYER_DELIVERY_MANIFEST.json is not an object"]
    if raw.get("name") != "auto-note buyer delivery":
        errors.append("buyer manifest name mismatch")
    if not isinstance(raw.get("source_sales_handoff"), str) or not raw.get("source_sales_handoff"):
        errors.append("buyer manifest missing source_sales_handoff")
    expected_release = release_files[0].name if release_files else ""
    if expected_release and raw.get("release_package") != expected_release:
        errors.append(f"buyer manifest release mismatch: {raw.get('release_package')}")
    files = raw.get("files")
    if not isinstance(files, list):
        return [*errors, "buyer manifest files is not a list"]
    if raw.get("file_count") != len(files):
        errors.append("buyer manifest file_count mismatch")
    targets = {
        path.name: path
        for path in [*release_files, buyer_start, buyer_handoff, buyer_support_guide, buyer_support_request]
        if path.exists()
    }
    expected_names = set(targets)
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            errors.append("buyer manifest file entry is not an object")
            continue
        name = item.get("path")
        if not isinstance(name, str):
            errors.append("buyer manifest file path is not a string")
            continue
        if "/" in name or "\\" in name or ":" in name or name in ("", ".", ".."):
            errors.append(f"unsafe buyer manifest file path: {name}")
            continue
        if name in seen:
            errors.append(f"duplicate buyer manifest file path: {name}")
            continue
        seen.add(name)
        target = targets.get(name)
        if target is None or target.parent != directory:
            errors.append(f"buyer manifest file missing from delivery folder: {name}")
            continue
        data = target.read_bytes()
        if item.get("size") != len(data):
            errors.append(f"buyer manifest size mismatch: {name}")
        expected_sha = str(item.get("sha256") or "")
        actual_sha = hashlib.sha256(data).hexdigest()
        if expected_sha != actual_sha:
            errors.append(f"buyer manifest checksum mismatch: {name}")
    for name in expected_names:
        if name not in seen:
            errors.append(f"buyer manifest missing file: {name}")
    return errors


def _verify_manifest(archive: zipfile.ZipFile) -> list[str]:
    errors: list[str] = []
    try:
        raw: Any = json.loads(archive.read("SALES_HANDOFF_MANIFEST.json").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"manifest is not valid JSON: {exc}"]
    if not isinstance(raw, dict):
        return ["manifest root must be an object"]
    if raw.get("version") != __version__:
        errors.append(f"manifest version mismatch: {raw.get('version')}")
    privacy = raw.get("privacy")
    if not isinstance(privacy, dict):
        errors.append("manifest privacy must be an object")
    else:
        for key in ("includes_user_articles", "includes_generated_helpers", "includes_virtualenv"):
            if privacy.get(key) is not False:
                errors.append(f"manifest privacy flag must be false: {key}")
    files = raw.get("files")
    if not isinstance(files, list):
        errors.append("manifest files must be a list")
        return errors
    if raw.get("file_count") != len(files):
        errors.append("manifest file_count does not match files list")
    names = set(archive.namelist())
    for item in files:
        if not isinstance(item, dict):
            errors.append("manifest file item must be an object")
            continue
        name = str(item.get("path") or "")
        if name not in names:
            errors.append(f"manifest file missing from zip: {name}")
            continue
        data = archive.read(name)
        if item.get("size") != len(data):
            errors.append(f"manifest size mismatch: {name}")
        expected_sha = str(item.get("sha256") or "")
        actual_sha = hashlib.sha256(data).hexdigest()
        if expected_sha != actual_sha:
            errors.append(f"manifest checksum mismatch: {name}")
    return errors


def _verify_sales_materials_entry(archive: zipfile.ZipFile) -> list[str]:
    from .sales_materials import verify_sales_materials_text

    try:
        text = archive.read("SALES_MATERIALS.md").decode("utf-8", errors="replace")
    except KeyError as exc:
        return [f"sales materials missing: {exc}"]
    return [f"sales materials: {error}" for error in verify_sales_materials_text(text)]


def _verify_seller_delivery_receipt(archive: zipfile.ZipFile, release_name: str) -> list[str]:
    try:
        text = archive.read("SELLER_DELIVERY_RECEIPT.txt").decode("utf-8", errors="replace")
    except KeyError as exc:
        return [f"seller delivery receipt missing: {exc}"]
    errors: list[str] = []
    if "auto-note seller delivery receipt" not in text:
        errors.append("SELLER_DELIVERY_RECEIPT.txt does not look like an auto-note seller delivery receipt")
    if release_name and release_name not in text:
        errors.append(f"SELLER_DELIVERY_RECEIPT.txt does not mention release package: {release_name}")
    for required_text in ("Buyer delivery ZIP", "Order ID", "SHA-256"):
        if required_text not in text:
            errors.append(f"SELLER_DELIVERY_RECEIPT.txt is missing {required_text}")
    return errors


def _verify_nested_release(archive: zipfile.ZipFile, release_entry: str) -> list[str]:
    try:
        data = archive.read(release_entry)
        with zipfile.ZipFile(io.BytesIO(data)):
            pass
    except (KeyError, OSError, zipfile.BadZipFile) as exc:
        return [f"nested release zip unreadable: {exc}"]
    with tempfile.TemporaryDirectory() as tmp:
        temp_release = Path(tmp) / Path(release_entry).name
        temp_release.write_bytes(data)
        return [f"nested release: {error}" for error in verify_release_package(temp_release)]
