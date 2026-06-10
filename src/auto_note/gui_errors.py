from __future__ import annotations

from datetime import datetime
from pathlib import Path


def gui_error_log_path(project_dir: Path) -> Path:
    return project_dir / ".auto-note" / "gui-error.log"


def append_gui_error(project_dir: Path, title: str, detail: str) -> Path:
    path = gui_error_log_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = [
        "",
        f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {title}",
        detail.rstrip(),
        "",
    ]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(entry))
    return path


def clear_gui_error_log(project_dir: Path) -> Path | None:
    path = gui_error_log_path(project_dir)
    if not path.exists():
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.stat().st_size <= 0:
        path.unlink()
        return None
    archive = path.with_name(f"gui-error-cleared-{datetime.now():%Y%m%d-%H%M%S-%f}.log")
    path.replace(archive)
    return archive
