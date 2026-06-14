from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import json
import platform
import shutil
import sys

from . import __version__
from .release import list_releases


@dataclass(frozen=True)
class AppInfo:
    version: str
    python: str
    platform: str
    project_dir: Path
    latest_release: Path | None
    install_info: InstallInfo | None
    install_info_status: InstallInfoStatus


@dataclass(frozen=True)
class InstallInfo:
    installed_at: str
    version: str
    preinstall_backup: str


@dataclass(frozen=True)
class InstallInfoStatus:
    ok: bool
    detail: str
    path: Path
    info: InstallInfo | None = None
    preinstall_backup_path: Path | None = None


def collect_app_info(project_dir: Path) -> AppInfo:
    releases = list_releases(project_dir)
    install_info_status = inspect_install_info(project_dir)
    return AppInfo(
        version=__version__,
        python=sys.version.split()[0],
        platform=platform.platform(),
        project_dir=project_dir,
        latest_release=releases[0] if releases else None,
        install_info=install_info_status.info,
        install_info_status=install_info_status,
    )


def format_app_info(info: AppInfo) -> str:
    latest_release = str(info.latest_release) if info.latest_release else "(none)"
    lines = [
        f"auto-note: {info.version}",
        f"Python: {info.python}",
        f"Platform: {info.platform}",
        f"Project: {info.project_dir}",
        f"Latest release: {latest_release}",
    ]
    if info.install_info:
        lines.extend(
            [
                f"Installed at: {info.install_info.installed_at}",
                f"Installed version: {info.install_info.version}",
                f"Pre-install backup: {info.install_info.preinstall_backup or '(none)'}",
                f"Install info status: {'OK' if info.install_info_status.ok else 'NG'} - {info.install_info_status.detail}",
            ]
        )
    else:
        lines.append(f"Install info: {info.install_info_status.detail}")
    return "\n".join(lines)


def read_install_info(project_dir: Path) -> InstallInfo | None:
    return inspect_install_info(project_dir).info


def archive_invalid_install_info(project_dir: Path) -> Path:
    path = project_dir / ".auto-note" / "install-info.json"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = path.with_name(f"install-info.invalid-{timestamp}.json")
    shutil.copy2(path, backup_path)
    path.unlink()
    return backup_path


def list_install_info_recovery_files(project_dir: Path) -> list[Path]:
    directory = project_dir / ".auto-note"
    if not directory.exists():
        return []
    return sorted(directory.glob("install-info.invalid-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)


def inspect_install_info(project_dir: Path) -> InstallInfoStatus:
    path = project_dir / ".auto-note" / "install-info.json"
    if not path.exists():
        return InstallInfoStatus(True, "not created yet", path)
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        return InstallInfoStatus(False, f"unreadable: {exc}", path)
    except json.JSONDecodeError as exc:
        return InstallInfoStatus(False, f"invalid JSON: {exc.msg}", path)
    if not isinstance(raw, dict):
        return InstallInfoStatus(False, "invalid JSON root: expected object", path)
    info = InstallInfo(
        installed_at=str(raw.get("installed_at") or ""),
        version=str(raw.get("version") or ""),
        preinstall_backup=str(raw.get("preinstall_backup") or ""),
    )
    missing = []
    if not info.installed_at:
        missing.append("installed_at")
    if not info.version:
        missing.append("version")
    if missing:
        return InstallInfoStatus(False, "missing field(s): " + ", ".join(missing), path, info=info)
    if info.preinstall_backup:
        backup_path = path.parent / "install-backups" / info.preinstall_backup
        if not backup_path.exists():
            return InstallInfoStatus(
                False,
                f"preinstall backup missing: {info.preinstall_backup}",
                path,
                info=info,
                preinstall_backup_path=backup_path,
            )
        return InstallInfoStatus(
            True,
            f"ok, preinstall backup found: {info.preinstall_backup}",
            path,
            info=info,
            preinstall_backup_path=backup_path,
        )
    return InstallInfoStatus(True, "ok, no preinstall backup recorded", path, info=info)
