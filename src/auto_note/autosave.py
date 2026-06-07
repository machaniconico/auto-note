from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path


@dataclass(frozen=True)
class AutosaveState:
    article_path: Path
    autosave_path: Path
    exists: bool
    newer_than_article: bool
    size_bytes: int
    updated_at: float | None


def autosave_path(project_dir: Path, article_path: Path) -> Path:
    key = sha1(str(article_path.resolve()).lower().encode("utf-8")).hexdigest()[:12]
    stem = _safe_stem(article_path.stem)
    return project_dir / ".auto-note" / "autosaves" / f"{stem}-{key}.md.autosave"


def write_autosave(project_dir: Path, article_path: Path, text: str) -> Path:
    path = autosave_path(project_dir, article_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def read_autosave(project_dir: Path, article_path: Path) -> str:
    return autosave_path(project_dir, article_path).read_text(encoding="utf-8")


def clear_autosave(project_dir: Path, article_path: Path) -> bool:
    path = autosave_path(project_dir, article_path)
    if not path.exists():
        return False
    path.unlink()
    return True


def autosave_state(project_dir: Path, article_path: Path) -> AutosaveState:
    path = autosave_path(project_dir, article_path)
    if not path.exists():
        return AutosaveState(article_path, path, False, False, 0, None)

    autosave_mtime = path.stat().st_mtime
    article_mtime = article_path.stat().st_mtime if article_path.exists() else 0
    return AutosaveState(
        article_path=article_path,
        autosave_path=path,
        exists=True,
        newer_than_article=autosave_mtime > article_mtime,
        size_bytes=path.stat().st_size,
        updated_at=autosave_mtime,
    )


def has_newer_autosave(project_dir: Path, article_path: Path) -> bool:
    state = autosave_state(project_dir, article_path)
    return state.exists and state.newer_than_article and state.size_bytes > 0


def _safe_stem(value: str) -> str:
    chars = []
    for char in value:
        if char.isalnum() or char in ("-", "_"):
            chars.append(char)
        elif char.isspace():
            chars.append("-")
    stem = "".join(chars).strip("-_")
    return stem[:48] or "article"
