from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .settings import inspect_settings, list_settings_recovery_files, load_settings, save_settings
from .workflow import inspect_ideas, list_idea_recovery_files, load_ideas, save_ideas


@dataclass(frozen=True)
class SetupItem:
    name: str
    ok: bool
    detail: str


def run_setup_check(project_dir: Path, *, create: bool = False) -> list[SetupItem]:
    if create:
        (project_dir / "articles").mkdir(parents=True, exist_ok=True)
        (project_dir / ".auto-note").mkdir(parents=True, exist_ok=True)
        save_settings(project_dir, load_settings(project_dir))
        save_ideas(project_dir, load_ideas(project_dir))

    items = [
        _path_item("project folder", project_dir),
        _path_item("articles folder", project_dir / "articles"),
        _path_item("settings file", project_dir / ".auto-note" / "settings.json"),
        _settings_item(project_dir),
        _ideas_item(project_dir),
        _path_item("GUI launcher", project_dir / "auto-note-gui.bat"),
        _path_item("icon shortcut", project_dir / "auto-note.lnk"),
        _import_item("tkinter", "GUI"),
        _import_item("yaml", "frontmatter parser"),
        _import_item("PIL", "optional image optimization"),
    ]
    recovery_files = list_settings_recovery_files(project_dir)
    if recovery_files:
        items.append(SetupItem("settings recovery backup", True, recovery_files[0].name))
    idea_recovery_files = list_idea_recovery_files(project_dir)
    if idea_recovery_files:
        items.append(SetupItem("ideas recovery backup", True, idea_recovery_files[0].name))
    return items


def format_setup_report(items: list[SetupItem]) -> str:
    lines = ["セットアップ確認", ""]
    for item in items:
        status = "OK" if item.ok else "WARN"
        lines.append(f"[{status}] {item.name}: {item.detail}")
    lines.extend(
        [
            "",
            "次の操作",
            "1. auto-note.lnk または auto-note-gui.bat を開く",
            "2. セットアップウィザードで既定タグと投稿設定を確認する",
            "3. クイック確認を実行する",
            "4. 練習記事、または新規記事を作成する",
            "5. 全体チェック後、投稿ヘルパーでnoteへ貼り付ける",
            "",
            "画像最適化を使う場合",
            ".\\.venv\\Scripts\\python.exe -m pip install -e .[images]",
        ]
    )
    return "\n".join(lines)


def _path_item(name: str, path: Path) -> SetupItem:
    return SetupItem(name, path.exists(), str(path))


def _settings_item(project_dir: Path) -> SetupItem:
    status = inspect_settings(project_dir)
    return SetupItem("settings readable", status.ok, status.detail)


def _ideas_item(project_dir: Path) -> SetupItem:
    status = inspect_ideas(project_dir)
    return SetupItem("ideas readable", status.ok, status.detail)


def _import_item(module_name: str, label: str) -> SetupItem:
    try:
        __import__(module_name)
    except Exception as exc:
        return SetupItem(label, False, str(exc))
    return SetupItem(label, True, "available")
