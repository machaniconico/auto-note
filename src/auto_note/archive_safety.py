from __future__ import annotations

from pathlib import PurePosixPath
import re
import stat
import zipfile


def verify_zip_member_names(
    names: list[str],
    *,
    unsafe_label: str = "unsafe file name",
    duplicate_label: str = "duplicate file name",
    reject_empty: bool = True,
    reject_colons: bool = True,
    reject_non_normalized: bool = True,
    duplicate_case_insensitive: bool = True,
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for name in names:
        normalized = name.replace("\\", "/")
        duplicate_key = normalized.casefold() if duplicate_case_insensitive else normalized
        parts = PurePosixPath(normalized).parts
        unsafe = False
        if (reject_empty and not normalized) or normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
            unsafe = True
        if ".." in parts:
            unsafe = True
        if reject_colons and any(":" in part for part in parts):
            unsafe = True
        if unsafe:
            errors.append(f"{unsafe_label}: {name}")
        if reject_non_normalized and normalized != name:
            errors.append(f"non-normalized file name: {name}")
        if duplicate_key in seen:
            errors.append(f"{duplicate_label}: {name}")
        seen.add(duplicate_key)
    return errors


def verify_zip_regular_entries(archive: zipfile.ZipFile) -> list[str]:
    errors: list[str] = []
    for info in archive.infolist():
        if info.is_dir():
            errors.append(f"non-file archive entry: {info.filename}")
            continue
        mode = (info.external_attr >> 16) & 0o170000
        if mode and mode != stat.S_IFREG:
            errors.append(f"unsafe archive entry type: {info.filename}")
    return errors
