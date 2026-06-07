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
