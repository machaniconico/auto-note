from __future__ import annotations

from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any
import hashlib
import json
import zipfile

from . import __version__
from .article import write_text_atomic
from .diagnostics import create_diagnostic_report, preview_diagnostic_report
from .paths import unique_path


def create_support_request(project_dir: Path, *, include_private: bool = False) -> Path:
    support_dir = project_dir / ".auto-note" / "support"
    support_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(support_dir / f"support-request-{datetime.now():%Y%m%d-%H%M%S}.md")
    write_text_atomic(path, build_support_request(project_dir, include_private=include_private))
    return path


def create_support_bundle(project_dir: Path, *, include_private: bool = False) -> Path:
    support_dir = project_dir / ".auto-note" / "support"
    support_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bundle_path = unique_path(support_dir / f"auto-note-support-bundle-{stamp}.zip")
    temp_path = support_dir / f".{bundle_path.name}.tmp"
    diagnostic_path = create_diagnostic_report(project_dir, include_private=include_private)
    created_at = datetime.now().isoformat(timespec="seconds")
    entries = {
        "README.txt": _build_bundle_readme(include_private=include_private).encode("utf-8"),
        "SUPPORT_SEND_CHECKLIST.txt": _build_support_send_checklist(
            bundle_name=bundle_path.name,
            diagnostic_name=diagnostic_path.name,
            include_private=include_private,
        ).encode("utf-8"),
        "support-request.md": build_support_request(project_dir, include_private=include_private).encode("utf-8"),
        "diagnostic-report.zip": diagnostic_path.read_bytes(),
    }
    records = [_bundle_record(name, data) for name, data in entries.items()]
    manifest = _build_bundle_manifest(
        created_at=created_at,
        include_private=include_private,
        diagnostic_name=diagnostic_path.name,
        records=records,
    )
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    checksum_records = [*records, _bundle_record("SUPPORT_BUNDLE_MANIFEST.json", manifest_bytes)]
    checksums = _build_checksums(checksum_records).encode("utf-8")

    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
            archive.writestr("SUPPORT_BUNDLE_MANIFEST.json", manifest_bytes)
            archive.writestr("CHECKSUMS.txt", checksums)
        temp_path.replace(bundle_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return bundle_path


def verify_support_bundle(bundle_path: Path) -> list[str]:
    if not bundle_path.exists():
        return [f"support bundle not found: {bundle_path}"]
    try:
        with zipfile.ZipFile(bundle_path) as archive:
            names = archive.namelist()
            errors = _verify_bundle_names(names)
            for required in (
                "README.txt",
                "SUPPORT_SEND_CHECKLIST.txt",
                "support-request.md",
                "diagnostic-report.zip",
                "SUPPORT_BUNDLE_MANIFEST.json",
                "CHECKSUMS.txt",
            ):
                if required not in names:
                    errors.append(f"missing required file: {required}")
            if "CHECKSUMS.txt" in names:
                errors.extend(_verify_checksums(archive))
            if "SUPPORT_BUNDLE_MANIFEST.json" in names:
                errors.extend(_verify_manifest(archive))
            return errors
    except zipfile.BadZipFile as exc:
        return [f"invalid zip file: {exc}"]


def format_support_bundle_verification(bundle_path: Path, errors: list[str]) -> str:
    if not errors:
        return f"[OK] support bundle verified: {bundle_path}"
    lines = [f"[NG] support bundle verification failed: {bundle_path}"]
    lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def build_support_request(project_dir: Path, *, include_private: bool = False) -> str:
    privacy = "raw details included" if include_private else "paths, user name, email, and article titles are masked"
    return (
        "# auto-note support request\n\n"
        "## Summary / 概要\n\n"
        "- Problem / 困っていること:\n"
        "- Since / いつから:\n"
        "- Expected / 期待した動き:\n"
        "- Actual / 実際の動き:\n"
        "- Impact / 影響範囲: 起動不可 / 投稿不可 / 記事編集不可 / 配布ZIP作成不可 / その他\n"
        "- Workaround / 一時回避策:\n\n"
        "## Steps to reproduce / 再現手順\n\n"
        "1. \n"
        "2. \n"
        "3. \n\n"
        "## What changed recently / 直近の変更\n\n"
        "- auto-note update / 更新:\n"
        "- Windows or Python update / Windows・Python更新:\n"
        "- note.com login or account change / noteログイン・アカウント変更:\n"
        "- Article, image, or settings change / 記事・画像・設定変更:\n\n"
        "## Attachments\n\n"
        "- Diagnostic report ZIP / 診断ZIP:\n"
        "- Screenshot, if helpful:\n\n"
        "## Privacy note / プライバシー\n\n"
        "- This request is generated with the default privacy-safe mode unless `--include-private` was used.\n"
        "- 送付前に下の診断プレビューを確認し、記事本文や個人情報が不要に含まれていないか見てください。\n\n"
        "## Environment\n\n"
        f"- auto-note version: {__version__}\n"
        f"- Project privacy: {privacy}\n\n"
        "## Diagnostic preview\n\n"
        "```text\n"
        f"{preview_diagnostic_report(project_dir, include_private=include_private)}\n"
        "```\n"
    )


def list_support_requests(project_dir: Path) -> list[Path]:
    support_dir = project_dir / ".auto-note" / "support"
    if not support_dir.exists():
        return []
    return sorted(support_dir.glob("support-request-*.md"), key=lambda path: path.stat().st_mtime, reverse=True)


def list_support_bundles(project_dir: Path) -> list[Path]:
    support_dir = project_dir / ".auto-note" / "support"
    if not support_dir.exists():
        return []
    return sorted(support_dir.glob("auto-note-support-bundle-*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)


def _build_bundle_readme(*, include_private: bool = False) -> str:
    privacy = "raw details included" if include_private else "privacy-safe: paths, user name, email, and article details are masked"
    return (
        "auto-note support bundle\n\n"
        f"Privacy: {privacy}\n\n"
        "Files:\n"
        "- SUPPORT_SEND_CHECKLIST.txt: Confirm what to review before sending this zip.\n"
        "- support-request.md: Fill in the summary, reproduction steps, and recent changes before sending.\n"
        "- diagnostic-report.zip: Attach this nested diagnostic report when support asks for details.\n\n"
        "Verification:\n"
        "- SUPPORT_BUNDLE_MANIFEST.json lists the bundle contents.\n"
        "- CHECKSUMS.txt contains SHA-256 checksums.\n\n"
        "Privacy check:\n"
        "- Run `auto-note privacy-audit --project-dir .` before sending if you want an extra local check.\n\n"
        "Before sending, open support-request.md and confirm that it does not contain information you do not want to share.\n"
    )


def _build_support_send_checklist(*, bundle_name: str, diagnostic_name: str, include_private: bool = False) -> str:
    privacy = (
        "RAW DETAILS INCLUDED - send only to a trusted support contact."
        if include_private
        else "privacy-safe by default - paths, user name, email, article titles, and article file names are masked."
    )
    return (
        "auto-note support send checklist\n"
        "問い合わせ一式 送付前チェックリスト\n\n"
        f"Bundle / 送付するZIP: {bundle_name}\n"
        f"Diagnostic report inside / 同梱診断ZIP: {diagnostic_name}\n"
        f"Privacy / 匿名化状態: {privacy}\n\n"
        "Before sending / 送付前に確認:\n"
        "[ ] Open support-request.md and fill in Summary, Steps to reproduce, and Recent changes.\n"
        "[ ] Read the Diagnostic preview in support-request.md and confirm it does not contain article text, personal names, emails, order IDs, or purchase details.\n"
        "[ ] Run `auto-note support --verify <this zip>` or GUI `一式ZIP検証` and confirm `[OK] support bundle verified`.\n"
        "[ ] Run `auto-note privacy-audit --project-dir .` or GUI `プライバシー監査` before sending.\n"
        "[ ] Send this ZIP only. Do not attach the whole `.auto-note` folder, user articles, sales handoff ZIPs, buyer delivery ZIPs, or order records unless support explicitly asks.\n\n"
        "Files expected in this ZIP / このZIPに入るもの:\n"
        "- README.txt\n"
        "- SUPPORT_SEND_CHECKLIST.txt\n"
        "- support-request.md\n"
        "- diagnostic-report.zip\n"
        "- SUPPORT_BUNDLE_MANIFEST.json\n"
        "- CHECKSUMS.txt\n"
    )


def _bundle_record(name: str, data: bytes) -> dict[str, object]:
    return {
        "path": name,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _build_bundle_manifest(
    *,
    created_at: str,
    include_private: bool,
    diagnostic_name: str,
    records: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "name": "auto-note support bundle",
        "version": __version__,
        "created_at": created_at,
        "privacy": {
            "includes_raw_details": include_private,
            "default_masks_paths_user_email_and_article_details": not include_private,
        },
        "source_diagnostic_report": diagnostic_name,
        "file_count": len(records),
        "files": records,
    }


def _build_checksums(records: list[dict[str, object]]) -> str:
    return "\n".join(f"{record['sha256']}  {record['path']}" for record in records) + "\n"


def _verify_bundle_names(names: list[str]) -> list[str]:
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
    for line in lines:
        if not line.strip():
            continue
        try:
            expected, name = line.split("  ", 1)
        except ValueError:
            errors.append(f"invalid checksum line: {line}")
            continue
        if name not in archive.namelist():
            errors.append(f"checksum target missing: {name}")
            continue
        checked.add(name)
        actual = hashlib.sha256(archive.read(name)).hexdigest()
        if actual != expected:
            errors.append(f"checksum mismatch: {name}")
    for required in (
        "README.txt",
        "SUPPORT_SEND_CHECKLIST.txt",
        "support-request.md",
        "diagnostic-report.zip",
        "SUPPORT_BUNDLE_MANIFEST.json",
    ):
        if required in archive.namelist() and required not in checked:
            errors.append(f"checksum missing: {required}")
    return errors


def _verify_manifest(archive: zipfile.ZipFile) -> list[str]:
    errors: list[str] = []
    try:
        raw: Any = json.loads(archive.read("SUPPORT_BUNDLE_MANIFEST.json").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"manifest is not valid JSON: {exc}"]
    if not isinstance(raw, dict):
        return ["manifest root must be an object"]
    if raw.get("version") != __version__:
        errors.append(f"manifest version mismatch: {raw.get('version')}")
    privacy = raw.get("privacy")
    if not isinstance(privacy, dict):
        errors.append("manifest privacy must be an object")
    files = raw.get("files")
    if not isinstance(files, list):
        errors.append("manifest files must be a list")
        return errors
    names = set(archive.namelist())
    for item in files:
        if not isinstance(item, dict):
            errors.append("manifest file item must be an object")
            continue
        name = str(item.get("path") or "")
        if name not in names:
            errors.append(f"manifest file missing from zip: {name}")
    return errors
