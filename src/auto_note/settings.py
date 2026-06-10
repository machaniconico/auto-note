from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import json
import shutil

from .article import write_text_atomic


@dataclass(frozen=True)
class AppSettings:
    default_tags: list[str]
    default_status: str
    append_tags_by_default: bool
    open_note_with_helper: bool
    article_glob: str
    onboarding_seen: bool
    support_contact: str
    seller_name: str
    sales_channel_url: str
    refund_policy_url: str
    commercial_terms_reviewed: bool
    commercial_support_scope_confirmed: bool
    commercial_reviewed_at: str
    ui_density: str
    image_optimize_by_default: bool
    image_max_width: int
    image_quality: int


@dataclass(frozen=True)
class SettingsStatus:
    path: Path
    exists: bool
    ok: bool
    detail: str


DEFAULT_SETTINGS = AppSettings(
    default_tags=["note"],
    default_status="draft",
    append_tags_by_default=True,
    open_note_with_helper=True,
    article_glob="*.md",
    onboarding_seen=False,
    support_contact="",
    seller_name="",
    sales_channel_url="",
    refund_policy_url="",
    commercial_terms_reviewed=False,
    commercial_support_scope_confirmed=False,
    commercial_reviewed_at="",
    ui_density="standard",
    image_optimize_by_default=False,
    image_max_width=1600,
    image_quality=85,
)

UI_DENSITY_OPTIONS = ("standard", "comfortable", "large")


def settings_path(project_dir: Path) -> Path:
    return project_dir / ".auto-note" / "settings.json"


def load_settings(project_dir: Path) -> AppSettings:
    path = settings_path(project_dir)
    if not path.exists():
        return DEFAULT_SETTINGS

    try:
        raw = _read_settings_json(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return DEFAULT_SETTINGS
    if not isinstance(raw, dict):
        return DEFAULT_SETTINGS

    return _settings_from_mapping(raw)


def inspect_settings(project_dir: Path) -> SettingsStatus:
    path = settings_path(project_dir)
    if not path.exists():
        return SettingsStatus(path, False, True, "not created yet")
    try:
        raw = _read_settings_json(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return SettingsStatus(path, True, False, f"invalid settings.json: {exc}")
    if not isinstance(raw, dict):
        return SettingsStatus(path, True, False, "invalid settings.json: root must be an object")
    _settings_from_mapping(raw)
    return SettingsStatus(path, True, True, "valid")


def _read_settings_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _backup_invalid_settings(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = path.with_name(f"settings.invalid-{timestamp}.json")
    shutil.copy2(path, backup_path)
    return backup_path


def _settings_from_mapping(raw: dict[str, Any]) -> AppSettings:
    merged: dict[str, Any] = asdict(DEFAULT_SETTINGS)
    merged.update(raw)
    merged["default_tags"] = _normalise_tags(merged.get("default_tags"))
    merged["default_status"] = str(merged.get("default_status") or "draft")
    merged["append_tags_by_default"] = bool(merged.get("append_tags_by_default"))
    merged["open_note_with_helper"] = bool(merged.get("open_note_with_helper"))
    merged["article_glob"] = str(merged.get("article_glob") or "*.md")
    merged["onboarding_seen"] = bool(merged.get("onboarding_seen"))
    merged["support_contact"] = str(merged.get("support_contact") or "")
    merged["seller_name"] = str(merged.get("seller_name") or "")
    merged["sales_channel_url"] = str(merged.get("sales_channel_url") or "")
    merged["refund_policy_url"] = str(merged.get("refund_policy_url") or "")
    merged["commercial_terms_reviewed"] = bool(merged.get("commercial_terms_reviewed"))
    merged["commercial_support_scope_confirmed"] = bool(merged.get("commercial_support_scope_confirmed"))
    merged["commercial_reviewed_at"] = str(merged.get("commercial_reviewed_at") or "")
    merged["ui_density"] = _normalise_ui_density(merged.get("ui_density"))
    merged["image_optimize_by_default"] = bool(merged.get("image_optimize_by_default"))
    merged["image_max_width"] = _clamp_int(merged.get("image_max_width"), default=1600, minimum=320, maximum=4000)
    merged["image_quality"] = _clamp_int(merged.get("image_quality"), default=85, minimum=30, maximum=100)
    known = asdict(DEFAULT_SETTINGS)
    return AppSettings(**{key: merged[key] for key in known})


def save_settings(project_dir: Path, settings: AppSettings) -> None:
    path = settings_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not inspect_settings(project_dir).ok:
        _backup_invalid_settings(path)
    write_text_atomic(path, json.dumps(asdict(settings), ensure_ascii=False, indent=2) + "\n")


def list_settings_recovery_files(project_dir: Path) -> list[Path]:
    directory = project_dir / ".auto-note"
    if not directory.exists():
        return []
    return sorted(directory.glob("settings.invalid-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)


def parse_tags(value: str) -> list[str]:
    return _normalise_tags(value)


def _normalise_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = value.replace("#", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        raw = list(value)
    else:
        raw = [value]
    tags: list[str] = []
    seen: set[str] = set()
    for item in raw:
        tag = str(item).strip().lstrip("#")
        if not tag or tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)
    return tags


def _normalise_ui_density(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in UI_DENSITY_OPTIONS:
        return text
    return DEFAULT_SETTINGS.ui_density


def _clamp_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))
