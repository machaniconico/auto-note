from __future__ import annotations

from pathlib import Path


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index:02d}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"could not create a unique file name for {path}")
