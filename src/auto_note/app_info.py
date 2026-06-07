from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import platform
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


@dataclass(frozen=True)
class InstallInfo:
    installed_at: str
    version: str
    preinstall_backup: str


def collect_app_info(project_dir: Path) -> AppInfo:
    releases = list_releases(project_dir)
    return AppInfo(
        version=__version__,
        python=sys.version.split()[0],
        platform=platform.platform(),
        project_dir=project_dir,
        latest_release=releases[0] if releases else None,
        install_info=read_install_info(project_dir),
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
            ]
        )
    else:
        lines.append("Install info: (none)")
    return "\n".join(lines)


def read_install_info(project_dir: Path) -> InstallInfo | None:
    path = project_dir / ".auto-note" / "install-info.json"
    if not path.exists():
        return None
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return InstallInfo(
        installed_at=str(raw.get("installed_at") or ""),
        version=str(raw.get("version") or ""),
        preinstall_backup=str(raw.get("preinstall_backup") or ""),
    )
