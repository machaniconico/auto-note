from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import zipfile


@dataclass(frozen=True)
class BackupRestoreResult:
    backup: Path
    safety_backup: Path | None
    restored_files: list[str]


@dataclass(frozen=True)
class BackupInspection:
    backup: Path
    restorable_files: list[str]
    ignored_files: list[str]
    unsafe_files: list[str]
    article_files: list[str]
    has_settings: bool
    has_ideas: bool
    total_files: int
    total_bytes: int

    @property
    def ok(self) -> bool:
        return bool(self.restorable_files) and not self.unsafe_files


def create_backup(project_dir: Path) -> Path:
    backup_dir = project_dir / ".auto-note" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = _unique_backup_path(backup_dir, "auto-note-backup")

    with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _add_tree(archive, project_dir / "articles", "articles")
        for relative in (".auto-note/ideas.json", ".auto-note/settings.json"):
            path = project_dir / relative
            if path.exists():
                archive.write(path, relative)
        readme = project_dir / "README.md"
        if readme.exists():
            archive.write(readme, "README.md")

    return backup_path


def list_backups(project_dir: Path) -> list[Path]:
    backup_dir = project_dir / ".auto-note" / "backups"
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)


def inspect_backup(backup_path: Path) -> BackupInspection:
    backup_path = backup_path.resolve()
    if not backup_path.exists():
        raise FileNotFoundError(f"backup not found: {backup_path}")

    restorable_files: list[str] = []
    ignored_files: list[str] = []
    unsafe_files: list[str] = []
    article_files: list[str] = []
    total_files = 0
    total_bytes = 0
    has_settings = False
    has_ideas = False

    with zipfile.ZipFile(backup_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            total_files += 1
            total_bytes += max(info.file_size, 0)
            normalized = _normalize_member_name(info.filename)
            if not _safe_member_name(normalized):
                unsafe_files.append(normalized or info.filename)
                continue
            if _restorable_normalized_member(normalized):
                restorable_files.append(normalized)
                if normalized.startswith("articles/"):
                    article_files.append(normalized)
                elif normalized == ".auto-note/settings.json":
                    has_settings = True
                elif normalized == ".auto-note/ideas.json":
                    has_ideas = True
            else:
                ignored_files.append(normalized)

    return BackupInspection(
        backup=backup_path,
        restorable_files=restorable_files,
        ignored_files=ignored_files,
        unsafe_files=unsafe_files,
        article_files=article_files,
        has_settings=has_settings,
        has_ideas=has_ideas,
        total_files=total_files,
        total_bytes=total_bytes,
    )


def verify_backup(backup_path: Path) -> list[str]:
    try:
        inspection = inspect_backup(backup_path)
    except (OSError, zipfile.BadZipFile) as exc:
        return [f"backup could not be read: {exc}"]

    errors: list[str] = []
    if inspection.unsafe_files:
        errors.append(f"{len(inspection.unsafe_files)} unsafe file(s)")
    if not inspection.restorable_files:
        errors.append("no restorable articles/settings")
    return errors


def format_backup_inspection(inspection: BackupInspection) -> str:
    status = "OK" if inspection.ok else "NG"
    lines = [
        "Backup inspection",
        f"Status: {status}",
        f"Backup: {inspection.backup}",
        f"Total files: {inspection.total_files}",
        f"Total bytes: {inspection.total_bytes}",
        f"Restorable files: {len(inspection.restorable_files)}",
        f"Article files: {len(inspection.article_files)}",
        f"Settings: {'yes' if inspection.has_settings else 'no'}",
        f"Ideas: {'yes' if inspection.has_ideas else 'no'}",
        f"Ignored files: {len(inspection.ignored_files)}",
        f"Unsafe files: {len(inspection.unsafe_files)}",
    ]
    if inspection.article_files:
        lines.append("")
        lines.append("Articles:")
        lines.extend(f"- {name}" for name in inspection.article_files[:30])
        if len(inspection.article_files) > 30:
            lines.append(f"- ... {len(inspection.article_files) - 30} more")
    if inspection.unsafe_files:
        lines.append("")
        lines.append("Unsafe entries:")
        lines.extend(f"- {name}" for name in inspection.unsafe_files[:30])
        if len(inspection.unsafe_files) > 30:
            lines.append(f"- ... {len(inspection.unsafe_files) - 30} more")
    if inspection.ignored_files:
        lines.append("")
        lines.append("Ignored entries:")
        lines.extend(f"- {name}" for name in inspection.ignored_files[:20])
        if len(inspection.ignored_files) > 20:
            lines.append(f"- ... {len(inspection.ignored_files) - 20} more")
    return "\n".join(lines)


def restore_backup(project_dir: Path, backup_path: Path, *, create_safety_backup: bool = True) -> BackupRestoreResult:
    project_dir = project_dir.resolve()
    backup_path = backup_path.resolve()
    if not backup_path.exists():
        raise FileNotFoundError(f"backup not found: {backup_path}")

    inspection = inspect_backup(backup_path)
    if inspection.unsafe_files:
        raise ValueError("backup contains unsafe entries. Inspect the backup before restoring.")
    if not inspection.restorable_files:
        raise ValueError("backup has no restorable articles/settings.")

    with zipfile.ZipFile(backup_path) as archive:
        members = [info for info in archive.infolist() if _restorable_member(info.filename)]

        safety_backup = create_backup(project_dir) if create_safety_backup and _has_project_data(project_dir) else None
        if any(info.filename == "articles/" or info.filename.startswith("articles/") for info in members):
            articles_dir = project_dir / "articles"
            if articles_dir.exists():
                shutil.rmtree(articles_dir)
            articles_dir.mkdir(parents=True, exist_ok=True)

        restored: list[str] = []
        for info in members:
            if info.is_dir():
                continue
            normalized = _normalize_member_name(info.filename)
            target = _restore_target(project_dir, normalized)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            restored.append(normalized)

    return BackupRestoreResult(backup=backup_path, safety_backup=safety_backup, restored_files=restored)


def _add_tree(archive: zipfile.ZipFile, root: Path, archive_root: str) -> None:
    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_file():
            archive.write(path, f"{archive_root}/{path.relative_to(root).as_posix()}")


def _restorable_member(name: str) -> bool:
    normalized = _normalize_member_name(name)
    return _safe_member_name(normalized) and _restorable_normalized_member(normalized)


def _restorable_normalized_member(name: str) -> bool:
    return name.startswith("articles/") or name in {
        ".auto-note/settings.json",
        ".auto-note/ideas.json",
    }


def _safe_member_name(name: str) -> bool:
    if not name or name.startswith("/") or name.endswith("/.."):
        return False
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return False
    if any(":" in part for part in path.parts):
        return False
    return True


def _normalize_member_name(name: str) -> str:
    return name.replace("\\", "/")


def _restore_target(project_dir: Path, name: str) -> Path:
    target = project_dir.joinpath(*PurePosixPath(name).parts).resolve()
    if target != project_dir and project_dir not in target.parents:
        raise ValueError(f"unsafe backup member: {name}")
    return target


def _has_project_data(project_dir: Path) -> bool:
    if (project_dir / "articles").exists():
        return True
    return any((project_dir / relative).exists() for relative in (".auto-note/settings.json", ".auto-note/ideas.json"))


def _unique_backup_path(backup_dir: Path, prefix: str) -> Path:
    stem = f"{prefix}-{datetime.now():%Y%m%d-%H%M%S}"
    path = backup_dir / f"{stem}.zip"
    if not path.exists():
        return path
    for index in range(1, 1000):
        candidate = backup_dir / f"{stem}-{index:03d}.zip"
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"could not create a unique backup name in {backup_dir}")
