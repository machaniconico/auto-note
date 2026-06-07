from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import shutil


@dataclass(frozen=True)
class Revision:
    path: Path
    created_at: str
    size_bytes: int


def create_revision(project_dir: Path, article_path: Path, *, label: str = "save") -> Path:
    article_path = article_path.resolve()
    if not article_path.exists():
        raise FileNotFoundError(article_path)
    target_dir = revision_dir(project_dir, article_path)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_label = _safe_part(label)
    revision_path = target_dir / f"{stamp}-{safe_label}-{article_path.name}"
    if revision_path.exists():
        revision_path = _next_available_path(revision_path)
    shutil.copy2(article_path, revision_path)
    return revision_path


def list_revisions(project_dir: Path, article_path: Path) -> list[Revision]:
    target_dir = revision_dir(project_dir, article_path.resolve())
    if not target_dir.exists():
        return []
    revisions = [
        Revision(
            path=path,
            created_at=datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            size_bytes=path.stat().st_size,
        )
        for path in target_dir.glob("*.md")
        if path.is_file()
    ]
    return sorted(revisions, key=lambda revision: revision.path.stat().st_mtime, reverse=True)


def restore_revision(project_dir: Path, article_path: Path, revision_path: Path) -> Path:
    article_path = article_path.resolve()
    revision_path = revision_path.resolve()
    allowed_dir = revision_dir(project_dir, article_path).resolve()
    if allowed_dir not in revision_path.parents:
        raise ValueError(f"revision is outside history folder: {revision_path}")
    if not revision_path.exists():
        raise FileNotFoundError(revision_path)
    if article_path.exists():
        create_revision(project_dir, article_path, label="before-restore")
    shutil.copy2(revision_path, article_path)
    return article_path


def format_revisions(revisions: list[Revision]) -> str:
    if not revisions:
        return "保存履歴はありません。"
    lines = ["保存履歴"]
    for revision in revisions:
        lines.append(f"- {revision.created_at} | {_format_bytes(revision.size_bytes)} | {revision.path}")
    return "\n".join(lines)


def revision_dir(project_dir: Path, article_path: Path) -> Path:
    token = _safe_part(str(article_path.resolve()))
    return project_dir / ".auto-note" / "history" / token


def _safe_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "article"


def _next_available_path(path: Path) -> Path:
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(path)


def _format_bytes(value: int) -> str:
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value} B"
