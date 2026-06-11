from __future__ import annotations

import ctypes
from dataclasses import replace
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import os
import subprocess
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
import traceback
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText
import webbrowser
import zipfile

from . import __version__
from .action_plan import ActionPlanStep, build_action_plan, format_action_plan
from .acceptance import (
    format_acceptance_report,
    list_acceptance_reports,
    run_acceptance_check,
    write_acceptance_report,
)
from .article import Article, ArticleError, body_with_tags, hashtags_for, load_article, text_bundle, write_text_atomic
from .app_info import collect_app_info, format_app_info
from .autosave import autosave_state, clear_autosave, has_newer_autosave, read_autosave, write_autosave
from .backup import create_backup, format_backup_inspection, inspect_backup, list_backups, restore_backup
from .commercial import (
    format_commercial_policy_review,
    format_commercial_readiness_report,
    list_commercial_readiness_reports,
    run_commercial_readiness,
    write_commercial_policy_review,
    write_commercial_readiness_report,
)
from .commercial_setup import (
    apply_commercial_setup_template,
    commercial_setup_completion,
    commercial_setup_missing_fields,
    commercial_setup_next_field,
    commercial_setup_next_focus,
    commercial_setup_warnings,
    create_commercial_setup_template,
    format_commercial_setup_apply_result,
    format_commercial_settings,
    list_commercial_setup_templates,
)
from .diagnostics import (
    create_diagnostic_report,
    format_diagnostic_report_verification,
    format_diagnostics,
    list_diagnostic_reports,
    mask_text,
    preview_diagnostic_report,
    run_diagnostics,
    verify_diagnostic_report,
)
from .export import export_article_inventory, list_reports
from .first_run import FirstRunItem, FirstRunReport, format_first_run_report, run_first_run_checklist
from .gui_errors import append_gui_error, clear_gui_error_log, gui_error_log_path
from .history import create_revision, format_revisions, list_revisions, restore_revision, revision_dir
from .images import (
    collect_article_images,
    format_image_report,
    import_image_for_article,
    inspect_images_path,
    missing_images,
    set_article_cover,
)
from .inspect import format_reports, inspect_article, inspect_path
from .improvement_plan import (
    ImprovementPlan,
    build_improvement_plan,
    format_improvement_plan,
    has_improvement_plan_blockers,
)
from .licenses import collect_dependency_notices, format_dependency_notices, write_dependency_notices
from .maintenance import cleanup_generated_files, format_cleanup_confirmation, format_cleanup_report
from .manual import NOTE_LOGIN_URL, open_manual_dashboard, open_manual_post_helper
from .overview import build_overview, format_overview_report, list_overview_reports, write_overview_report
from .paths import unique_path
from .preflight import format_preflight_report, run_preflight
from .privacy import format_privacy_audit_report, has_privacy_audit_blockers, run_privacy_audit
from .publish_ready import PublishReadyItem, PublishReadyReport, format_publish_ready_report, run_publish_ready
from .publish_queue import (
    PublishQueueReport,
    build_publish_queue,
    format_publish_queue_report,
    has_publish_queue_blockers,
    list_publish_queue_reports,
)
from .quality import format_quality_report, run_quality_checks
from .quickstart import format_quickstart_report, run_quickstart
from .readiness import format_readiness_report, run_readiness
from .repair import (
    format_recovery_kit_report,
    format_repair_report,
    list_recovery_kit_reports,
    run_recovery_kit,
    run_repair,
    write_recovery_kit_report,
)
from .release import create_release_package, format_release_verification, list_releases, verify_release_package
from .review import ArticleReview, format_review_report, has_review_blockers, review_article, review_path
from .scaffold import create_article, create_practice_article, list_article_templates
from .sales_handoff import (
    create_sales_handoff,
    extract_buyer_delivery,
    format_buyer_delivery_package_verification,
    format_buyer_delivery_result,
    format_buyer_delivery_verification,
    format_sales_handoff_verification,
    list_buyer_deliveries,
    list_buyer_delivery_packages,
    list_sales_handoffs,
    verify_buyer_delivery,
    verify_buyer_delivery_package,
    verify_sales_handoff,
)
from .sales_finalize import (
    create_sales_finalize,
    find_latest_seller_order_management_block,
    find_buyer_delivery_package_for_message,
    format_buyer_send_readiness_report,
    format_seller_delivery_receipt,
    format_sales_finalize_details,
    has_buyer_send_readiness_blockers,
    has_sales_finalize_blockers,
    list_buyer_delivery_messages,
    list_seller_delivery_receipts,
    run_buyer_send_readiness,
    write_buyer_send_readiness_report,
    write_seller_delivery_receipt,
)
from .sales_materials import (
    create_sales_materials,
    format_sales_materials_verification,
    list_sales_materials,
    verify_sales_materials,
)
from .sales_listing import (
    create_sales_listing_kit,
    format_sales_listing_kit,
    format_sales_listing_verification,
    list_sales_listing_kits,
    list_sales_listing_packages,
    verify_sales_listing_kit,
)
from .sales_screenshots import (
    create_sales_screenshot_pack,
    format_sales_screenshot_pack,
    format_sales_screenshot_verification,
    list_sales_screenshot_packs,
    verify_sales_screenshot_pack,
)
from .sales_plan import SalesPlanStep, build_sales_plan, format_sales_plan, write_sales_plan_report
from .sales_review import (
    format_sales_review,
    has_sales_review_blockers,
    run_sales_review,
    write_sales_review_report,
)
from .sales_launch import (
    format_sales_launch_checklist,
    has_sales_launch_blockers,
    list_sales_launch_checklists,
    list_sales_launch_confirmations,
    run_sales_launch_check,
    write_sales_launch_confirmation,
    write_sales_launch_checklist,
)
from .settings import AppSettings, DEFAULT_SETTINGS, UI_DENSITY_OPTIONS, load_settings, parse_tags, save_settings
from .selftest import format_self_test_report, run_self_test, write_self_test_report
from .setup_check import format_setup_report, run_setup_check
from .starter import (
    cleanup_starter_pack,
    create_starter_pack,
    format_starter_cleanup_result,
    format_starter_pack_result,
)
from .support import (
    create_support_bundle,
    create_support_request,
    format_support_bundle_verification,
    list_support_bundles,
    read_support_display_diagnostics,
    read_support_gui_log_summary,
    read_support_send_checklist,
    verify_support_bundle,
)
from .troubleshoot import format_troubleshoot_report, run_troubleshoot
from .workflow import (
    add_idea,
    clear_article_schedule,
    export_calendar,
    format_calendar,
    format_calendar_export,
    format_ideas,
    format_plan,
    list_calendar_exports,
    load_ideas,
    mark_article_published,
    promote_idea,
    set_article_schedule,
    set_article_status,
    update_article_metadata,
)
from .workflow_smoke import (
    format_workflow_smoke_report,
    list_workflow_smoke_reports,
    run_workflow_smoke,
    write_workflow_smoke_report,
)


STATUS_ORDER = ("draft", "ready", "scheduled", "published")
STATUS_LABELS = {
    "draft": "下書き",
    "ready": "準備OK",
    "scheduled": "予定あり",
    "published": "公開済み",
}
SUPPORT_BUNDLE_FRESHNESS_WARNING_HOURS = 24
RELEASE_CHECK_FRESHNESS_WARNING_HOURS = 24
# Prefer Windows-native Japanese UI faces first. Noto stays as a fallback,
# but Tk on Windows can render it with tall metrics and cramped glyphs.
UI_FONT_CANDIDATES = (
    "Yu Gothic",
    "Meiryo UI",
    "Meiryo",
    "メイリオ",
    "Yu Gothic UI",
    "Noto Sans JP",
    "Noto Sans CJK JP",
    "BIZ UDPゴシック",
    "BIZ UDゴシック",
    "MS Gothic",
    "Segoe UI",
)
CODE_FONT_CANDIDATES = ("Cascadia Mono", "Consolas", "MS Gothic")
UI_CRUSH_PRONE_FONT_KEYWORDS = (
    "noto sans jp",
    "noto sans cjk jp",
    "biz ud",
    "ms gothic",
    "ms pgothic",
    "segoe ui",
)
UI_FONT = UI_FONT_CANDIDATES[0]
CODE_FONT = "Consolas"
UI_MIN_FONT_LINESPACE_RATIO = 1.25
UI_TEXT_SIZE = 12
UI_SMALL_TEXT_SIZE = 11
UI_BADGE_FONT_SIZE = 11
UI_HEADING_FONT_WEIGHT = "normal"
UI_BADGE_FONT_WEIGHT = "normal"
UI_CONTROL_FONT_WEIGHT = "normal"
UI_TREE_ROW_HEIGHT = 54
UI_NOTEBOOK_TAB_PADDING = (18, 12)
UI_BUTTON_PADDING = (18, 10)
UI_PRIMARY_BUTTON_PADDING = (20, 10)
UI_DANGER_BUTTON_PADDING = (18, 10)
UI_ACTION_BUTTON_MIN_WIDTH = 208
UI_ACTION_BUTTON_MAX_COLUMNS = 4
UI_BUTTON_LABEL_FIT_MARGIN = 8
UI_BASE_WINDOW_SIZE = (1240, 780)
UI_BASE_MIN_SIZE = (1020, 640)
UI_INITIAL_WINDOW_SCREEN_RATIO = (0.92, 0.88)
UI_MIN_WINDOW_SCREEN_RATIO = (0.86, 0.78)
UI_BUTTON_LABEL_FIT_SAMPLES = (
    "コマンド検索",
    "問い合わせ一式",
    "表示診断コピー",
    "販売者情報確認",
    "テンプレ取込一括",
    "品質チェックへ",
)
UI_TEXT_SPACING_TOP = 4
UI_TEXT_SPACING_BOTTOM = 6
UI_DENSITY_LABELS = {
    "standard": "標準",
    "comfortable": "ゆったり",
    "large": "大きめ",
}
UI_DENSITY_LABEL_TO_VALUE = {label: value for value, label in UI_DENSITY_LABELS.items()}
UI_DENSITY_VALUES = {
    "standard": {
        "text_size": 12,
        "small_text_size": 11,
        "badge_font_size": 11,
        "tree_row_height": 54,
        "notebook_tab_padding": (18, 12),
        "button_padding": (18, 10),
        "primary_button_padding": (20, 10),
        "danger_button_padding": (18, 10),
        "text_spacing_top": 4,
        "text_spacing_bottom": 6,
    },
    "comfortable": {
        "text_size": 14,
        "small_text_size": 13,
        "badge_font_size": 13,
        "tree_row_height": 68,
        "notebook_tab_padding": (22, 16),
        "button_padding": (22, 15),
        "primary_button_padding": (24, 15),
        "danger_button_padding": (22, 14),
        "text_spacing_top": 6,
        "text_spacing_bottom": 8,
    },
    "large": {
        "text_size": 16,
        "small_text_size": 15,
        "badge_font_size": 15,
        "tree_row_height": 84,
        "notebook_tab_padding": (26, 22),
        "button_padding": (26, 20),
        "primary_button_padding": (28, 20),
        "danger_button_padding": (26, 19),
        "text_spacing_top": 8,
        "text_spacing_bottom": 10,
    },
}
_DPI_AWARENESS_ENABLED = False
UI_COLORS = {
    "bg": "#eef3f8",
    "surface": "#ffffff",
    "surface_alt": "#f6f8fb",
    "surface_hover": "#edf4f7",
    "surface_strong": "#e8f7f3",
    "surface_selected": "#e6f4ef",
    "text_bg": "#fbfdff",
    "ink": "#101828",
    "muted": "#667085",
    "line": "#d6dee8",
    "line_strong": "#bac6d5",
    "chrome": "#111827",
    "chrome_alt": "#263142",
    "chrome_muted": "#cbd5e1",
    "chrome_chip": "#202b3d",
    "accent": "#0f766e",
    "accent_hover": "#0d5f59",
    "accent_pressed": "#0a4e49",
    "accent_soft": "#dff7f2",
    "focus": "#99f6e4",
    "danger": "#dc2626",
    "danger_soft": "#fee2e2",
    "warn": "#b45309",
    "warn_soft": "#fff4db",
    "info": "#2563eb",
    "info_soft": "#e7f0ff",
    "ok": "#047857",
    "ok_soft": "#dff3ed",
}
STATUS_COLORS = {
    "draft": ("#f3f4f6", "#374151"),
    "ready": ("#e7f0ff", "#174ea6"),
    "scheduled": ("#fff4db", "#8a4f00"),
    "published": ("#dff3ed", "#105f54"),
}
AUTOSAVE_INTERVAL_MS = 30_000


def _normalise_ui_density(value: str) -> str:
    text = str(value or "").strip().lower()
    if text in UI_DENSITY_OPTIONS:
        return text
    return "comfortable"


def _ui_density_label(value: str) -> str:
    return UI_DENSITY_LABELS.get(_normalise_ui_density(value), UI_DENSITY_LABELS["comfortable"])


def _ui_density_value(label: str) -> str:
    text = str(label or "").strip()
    if text in UI_DENSITY_LABEL_TO_VALUE:
        return UI_DENSITY_LABEL_TO_VALUE[text]
    return _normalise_ui_density(text)


def _apply_ui_density(density: str) -> None:
    global UI_TEXT_SIZE, UI_SMALL_TEXT_SIZE, UI_BADGE_FONT_SIZE, UI_TREE_ROW_HEIGHT
    global UI_NOTEBOOK_TAB_PADDING, UI_BUTTON_PADDING, UI_PRIMARY_BUTTON_PADDING, UI_DANGER_BUTTON_PADDING
    global UI_TEXT_SPACING_TOP, UI_TEXT_SPACING_BOTTOM

    values = UI_DENSITY_VALUES[_normalise_ui_density(density)]
    UI_TEXT_SIZE = int(values["text_size"])
    UI_SMALL_TEXT_SIZE = int(values["small_text_size"])
    UI_BADGE_FONT_SIZE = int(values["badge_font_size"])
    UI_TREE_ROW_HEIGHT = int(values["tree_row_height"])
    UI_NOTEBOOK_TAB_PADDING = tuple(values["notebook_tab_padding"])
    UI_BUTTON_PADDING = tuple(values["button_padding"])
    UI_PRIMARY_BUTTON_PADDING = tuple(values["primary_button_padding"])
    UI_DANGER_BUTTON_PADDING = tuple(values["danger_button_padding"])
    UI_TEXT_SPACING_TOP = int(values["text_spacing_top"])
    UI_TEXT_SPACING_BOTTOM = int(values["text_spacing_bottom"])


def _enable_windows_dpi_awareness() -> None:
    global _DPI_AWARENESS_ENABLED
    if _DPI_AWARENESS_ENABLED or os.name != "nt":
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError, ValueError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except (AttributeError, OSError):
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except (AttributeError, OSError):
                    pass
    _DPI_AWARENESS_ENABLED = True


def _minimum_readable_linespace(size: int) -> int:
    return int(math.ceil(size * UI_MIN_FONT_LINESPACE_RATIO))


def _is_crush_prone_font_family(family: str) -> bool:
    normalized = " ".join(str(family or "").lower().split())
    return any(keyword in normalized for keyword in UI_CRUSH_PRONE_FONT_KEYWORDS)


def _candidate_font_linespace(root: tk.Misc, family: str, size: int, *, weight: str = "normal") -> int | None:
    try:
        font = tkfont.Font(root=root, family=family, size=size, weight=weight)
        return int(font.metrics("linespace"))
    except (tk.TclError, ValueError):
        return None


def _resolve_font_family(
    root: tk.Misc,
    candidates: tuple[str, ...],
    *,
    minimum_linespace_ratio: float | None = None,
) -> str:
    try:
        available = {family.lower(): family for family in tkfont.families(root)}
    except tk.TclError:
        return candidates[0]
    first_available: str | None = None
    for candidate in candidates:
        resolved = available.get(candidate.lower())
        if resolved:
            if first_available is None:
                first_available = resolved
            if minimum_linespace_ratio is not None:
                linespace = _candidate_font_linespace(root, resolved, UI_TEXT_SIZE)
                minimum = int(math.ceil(UI_TEXT_SIZE * minimum_linespace_ratio))
                if linespace is None or linespace < minimum:
                    continue
            return resolved
    return first_available or candidates[-1]


def _configure_tk_font_defaults(root: tk.Misc, ui_font: str, code_font: str) -> None:
    try:
        root.tk.call("tk", "scaling", max(1.0, root.winfo_fpixels("1i") / 72.0))
    except tk.TclError:
        pass
    for name in (
        "TkDefaultFont",
        "TkTextFont",
        "TkMenuFont",
        "TkHeadingFont",
        "TkTooltipFont",
        "TkCaptionFont",
        "TkSmallCaptionFont",
        "TkIconFont",
    ):
        try:
            tkfont.nametofont(name).configure(family=ui_font, size=UI_TEXT_SIZE, weight="normal")
        except tk.TclError:
            continue
    for name in ("TkFixedFont",):
        try:
            tkfont.nametofont(name).configure(family=code_font, size=UI_TEXT_SIZE, weight="normal")
        except tk.TclError:
            continue


def _font_linespace(root: tk.Misc, family: str, size: int, *, weight: str = "normal") -> int | None:
    return _candidate_font_linespace(root, family, size, weight=weight)


def _actual_font_family(root: tk.Misc, family: str, size: int, *, weight: str = "normal") -> str:
    try:
        font = tkfont.Font(root=root, family=family, size=size, weight=weight)
        return str(font.actual("family"))
    except (tk.TclError, ValueError):
        return "unknown"


def _readable_vertical_padding(
    current_padding: object,
    line_space: int | None,
    *,
    minimum: int,
    ratio: float,
) -> int:
    current = _vertical_padding(current_padding) or 0
    measured = math.ceil(line_space * ratio) if line_space is not None else 0
    return max(int(math.ceil(current)), minimum, int(measured))


def _padding_with_vertical(current_padding: object, vertical: int) -> tuple[int, ...]:
    numbers = [int(math.ceil(number)) for number in _numeric_tokens(current_padding)]
    if len(numbers) >= 4:
        return (numbers[0], vertical, numbers[2], vertical)
    horizontal = numbers[0] if numbers else 0
    return (horizontal, vertical)


def _horizontal_padding(value: object) -> float | None:
    numbers = _numeric_tokens(value)
    if len(numbers) >= 4:
        return min(numbers[0], numbers[2])
    return numbers[0] if numbers else None


def _button_label_fit_status(measured_widths: list[tuple[str, int]], available_width: int) -> tuple[bool, str]:
    if not measured_widths:
        return False, "unavailable"
    label, width = max(measured_widths, key=lambda item: item[1])
    return width <= available_width, f"{label} {width}px / room {available_width}px"


def _scaled_action_button_min_width(root: tk.Misc) -> int:
    scale_factor = _display_scale_factor(root)
    scaled_base_width = int(math.ceil(UI_ACTION_BUTTON_MIN_WIDTH * scale_factor))
    try:
        font = tkfont.Font(root=root, family=UI_FONT, size=UI_TEXT_SIZE)
        widest_label = max(font.measure(label) for label in UI_BUTTON_LABEL_FIT_SAMPLES)
    except (tk.TclError, ValueError):
        widest_label = 0
    horizontal_padding = _horizontal_padding(UI_BUTTON_PADDING) or 0
    minimum_width = max(scaled_base_width, int(math.ceil(widest_label + (horizontal_padding * 2))))
    for _ in range(2):
        margin = int(math.ceil(UI_BUTTON_LABEL_FIT_MARGIN * max(1.0, minimum_width / UI_ACTION_BUTTON_MIN_WIDTH)))
        minimum_width = max(
            scaled_base_width,
            int(math.ceil(widest_label + (horizontal_padding * 2) + margin)),
        )
    return minimum_width


def _guard_ui_readability_metrics(root: tk.Misc, ui_font: str) -> None:
    global UI_TREE_ROW_HEIGHT, UI_NOTEBOOK_TAB_PADDING, UI_BUTTON_PADDING
    global UI_PRIMARY_BUTTON_PADDING, UI_DANGER_BUTTON_PADDING

    main_linespace = _font_linespace(root, ui_font, UI_TEXT_SIZE) or (UI_TEXT_SIZE + 9)
    button_vertical = _readable_vertical_padding(
        UI_BUTTON_PADDING,
        main_linespace,
        minimum=11,
        ratio=0.42,
    )
    primary_vertical = _readable_vertical_padding(
        UI_PRIMARY_BUTTON_PADDING,
        main_linespace,
        minimum=11,
        ratio=0.42,
    )
    danger_vertical = _readable_vertical_padding(
        UI_DANGER_BUTTON_PADDING,
        main_linespace,
        minimum=10,
        ratio=0.40,
    )
    tab_vertical = _readable_vertical_padding(
        UI_NOTEBOOK_TAB_PADDING,
        main_linespace,
        minimum=12,
        ratio=0.38,
    )

    UI_BUTTON_PADDING = _padding_with_vertical(UI_BUTTON_PADDING, button_vertical)
    UI_PRIMARY_BUTTON_PADDING = _padding_with_vertical(UI_PRIMARY_BUTTON_PADDING, primary_vertical)
    UI_DANGER_BUTTON_PADDING = _padding_with_vertical(UI_DANGER_BUTTON_PADDING, danger_vertical)
    UI_NOTEBOOK_TAB_PADDING = _padding_with_vertical(UI_NOTEBOOK_TAB_PADDING, tab_vertical)
    UI_TREE_ROW_HEIGHT = max(UI_TREE_ROW_HEIGHT, int(math.ceil(main_linespace * 1.55)), main_linespace + 14)


def _style_text_widget(widget: tk.Text, *, code: bool = False) -> None:
    widget.configure(
        background=UI_COLORS["text_bg"],
        foreground=UI_COLORS["ink"],
        insertbackground=UI_COLORS["accent"],
        selectbackground=UI_COLORS["accent_soft"],
        selectforeground=UI_COLORS["ink"],
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=UI_COLORS["line"],
        highlightcolor=UI_COLORS["focus"],
        padx=10,
        pady=10,
        spacing1=UI_TEXT_SPACING_TOP,
        spacing3=UI_TEXT_SPACING_BOTTOM,
        font=(CODE_FONT if code else UI_FONT, UI_TEXT_SIZE),
    )


def _release_check_reports_dir(project_dir: Path) -> Path:
    return project_dir / ".auto-note" / "reports"


def _release_check_report_path(project_dir: Path) -> Path:
    reports_dir = _release_check_reports_dir(project_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    return unique_path(reports_dir / f"release-check-{datetime.now():%Y%m%d-%H%M%S}.txt")


def _list_release_check_reports(project_dir: Path) -> list[Path]:
    reports_dir = _release_check_reports_dir(project_dir)
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("release-check-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def _format_release_check_output(
    *,
    status: str,
    exit_code: int | None,
    started_at: datetime,
    finished_at: datetime | None,
    command: str,
    stdout: str,
    stderr: str,
) -> str:
    lines = [
        "Release check / 販売前一括チェック",
        "",
        f"status: {status}",
        f"exit_code: {exit_code if exit_code is not None else 'not-started'}",
        f"started_at: {started_at:%Y-%m-%d %H:%M:%S}",
    ]
    if finished_at is not None:
        seconds = max(0.0, (finished_at - started_at).total_seconds())
        lines.extend(
            [
                f"finished_at: {finished_at:%Y-%m-%d %H:%M:%S}",
                f"duration_seconds: {seconds:.1f}",
            ]
        )
    lines.extend(
        [
            f"command: {command}",
            "",
            "stdout:",
            stdout.rstrip() or "(empty)",
            "",
            "stderr:",
            stderr.rstrip() or "(empty)",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _numeric_tokens(value: object) -> list[float]:
    tokens = str(value).replace("(", " ").replace(")", " ").replace(",", " ").split()
    numbers: list[float] = []
    for token in tokens:
        try:
            numbers.append(float(token))
        except ValueError:
            continue
    return numbers


def _first_number(value: object) -> float | None:
    numbers = _numeric_tokens(value)
    return numbers[0] if numbers else None


def _display_scale_factor(root: tk.Misc) -> float:
    try:
        scaling_value: object = root.tk.call("tk", "scaling")
    except tk.TclError:
        return 1.0
    scaling = _first_number(scaling_value) or (96.0 / 72.0)
    return max(1.0, scaling / (96.0 / 72.0))


def _bounded_scaled_dimension(base: int, scale: float, screen: int, ratio: float) -> int:
    scaled = max(1, int(math.ceil(base * max(1.0, scale))))
    if screen <= 0:
        return scaled
    limit = max(1, int(math.floor(screen * ratio)))
    return max(1, min(scaled, limit))


def _scaled_window_size(root: tk.Misc, base_size: tuple[int, int], screen_ratio: tuple[float, float]) -> tuple[int, int]:
    scale = _display_scale_factor(root)
    width = _bounded_scaled_dimension(base_size[0], scale, root.winfo_screenwidth(), screen_ratio[0])
    height = _bounded_scaled_dimension(base_size[1], scale, root.winfo_screenheight(), screen_ratio[1])
    return width, height


def _vertical_padding(value: object) -> float | None:
    numbers = _numeric_tokens(value)
    if len(numbers) >= 4:
        return min(numbers[1], numbers[3])
    if len(numbers) >= 2:
        return numbers[1]
    return numbers[0] if numbers else None


def _command_palette_status(match_count: int, total_count: int, query: str) -> str:
    if match_count <= 0:
        return "一致するコマンドがありません。別の言葉で検索してください。"
    if query.strip():
        return f"{match_count}件のコマンドが見つかりました。上下キーで選択、Enterで実行できます。"
    return f"全{total_count}件のコマンドを表示しています。スペース区切りで絞り込めます。上下キーで選択できます。"


def _command_palette_matches(label: str, hint: str, query: str) -> bool:
    tokens = query.strip().lower().split()
    if not tokens:
        return True
    haystack = f"{label} {hint}".lower()
    return all(token in haystack for token in tokens)


def _home_quick_action_matches(label: str, query: str) -> bool:
    return _command_palette_matches(label, "", query)


def _home_quick_action_status(match_count: int, total_count: int, query: str) -> str:
    if match_count <= 0:
        return "一致する操作がありません。別の言葉で検索してください。"
    if query.strip():
        return f"{total_count}件中 {match_count}件を表示しています。"
    return f"全{total_count}件の操作を表示しています。必要な操作名で絞り込めます。"


def _command_palette_selection_index(current: int | None, delta: int, count: int) -> int:
    if count <= 0:
        return -1
    if current is None or current < 0:
        return 0 if delta >= 0 else count - 1
    return (current + delta) % count


def _note_login_safety_text() -> str:
    return "\n".join(
        [
            "note login safety / noteログイン安全ガイド",
            "",
            "結論",
            "- Googleログインなどで「このブラウザまたはアプリは安全ではない可能性があります」と出る場合は、自動操作ブラウザを使わず、普段使っている既定ブラウザでログインします。",
            "- auto-note は未公開APIやログイン回避を使わず、投稿ヘルパーでコピーしてnote画面へ貼り付ける運用を標準にします。",
            "",
            "GUIでの手順",
            "1. ヘッダーまたは記事タブの noteログイン を押して普段のブラウザでログインする",
            "2. 設定 > 投稿ヘルパー起動時にnote投稿画面も開く をONにする",
            "3. 記事 > 投稿ヘルパー でヘルパーとnote投稿画面を開く",
            "4. ヘルパーのコピー操作でタイトル/本文/タグを貼り付け、note画面で公開する",
            "",
            "CLIでの手順",
            "- auto-note login --default-browser",
            "- auto-note manual .\\articles\\post.md --append-tags",
            "",
            "自動操作ブラウザを使う場合",
            "- 使える環境だけ `auto-note login --browser msedge` または `auto-note login --browser chrome` を試します。",
            "- 二要素認証やCAPTCHAは手動で対応してください。",
            "- 弾かれる場合は無理に突破せず、既定ブラウザ + 投稿ヘルパーに戻してください。",
        ]
    )


def _gui_runtime_error_message(path: Path) -> str:
    return "\n".join(
        [
            "操作中にエラーが発生しました。",
            "",
            f"ログ: {path}",
            "",
            "次に試すこと:",
            "1. 診断タブの「GUIログ表示」で内容を確認",
            "2. 「復旧セット」で基本修復と再診断を実行",
            "3. 解決しない場合は「問い合わせ一式」で送付用ZIPを作成",
            "4. 解決後は「GUIログクリア」で確認済みログを退避して状態を戻す",
            "",
            "コマンド検索(Ctrl+K)から GUIログ表示 / GUIログクリア / 復旧セット / 問い合わせ一式 を探せます。",
        ]
    )


def _home_gui_log_status(path: Path) -> tuple[str, str]:
    if not path.exists():
        return "ok", "GUIログ: 直近エラーはありません。"
    try:
        size = path.stat().st_size
    except OSError as exc:
        return "fail", f"GUIログ: 確認不可 / {exc}"
    if size <= 0:
        return "ok", "GUIログ: 空です。直近エラーはありません。"
    return "warn", f"GUIログ: 要確認 / {_format_mtime(path)} / {_format_file_size(path)}"


def launch_gui(project_dir: Path, *, safe_display: bool = False) -> int:
    project_dir = _clean_path(project_dir)
    _enable_windows_dpi_awareness()
    app = AutoNoteApp(project_dir, ui_density_override="large" if safe_display else None)
    app.mainloop()
    return 0


def smoke_gui(project_dir: Path, *, safe_display: bool = False) -> str:
    project_dir = _clean_path(project_dir)
    _enable_windows_dpi_awareness()
    app: AutoNoteApp | None = None
    try:
        app = AutoNoteApp(project_dir, ui_density_override="large" if safe_display else None)
        app.withdraw()
        app.update_idletasks()
        tabs = len(app.notebook.tabs())
        articles = len(app.article_paths)
        first_run_items = len(app.first_run_tree.get_children()) if hasattr(app, "first_run_tree") else 0
        home_action_items = len(app.home_action_tree.get_children()) if hasattr(app, "home_action_tree") else 0
        review_items = len(app.review_tree.get_children()) if hasattr(app, "review_tree") else 0
        review_detail_action_items = len(app.review_detail_buttons) if hasattr(app, "review_detail_buttons") else 0
        publish_ready_items = (
            len(app.publish_ready_tree.get_children()) if hasattr(app, "publish_ready_tree") else 0
        )
        article_focus_chars = (
            len(app.article_focus_summary_var.get() + app.article_focus_next_var.get())
            if hasattr(app, "article_focus_summary_var")
            else 0
        )
        commercial_setup_items = (
            len(app.commercial_setup_tree.get_children()) if hasattr(app, "commercial_setup_tree") else 0
        )
        commercial_setup_chars = (
            len(app.commercial_progress_var.get() + app.commercial_next_var.get() + app.commercial_setup_action_var.get())
            if hasattr(app, "commercial_setup_action_var")
            else 0
        )
        home_commercial_focus_chars = (
            len(app.home_commercial_focus_var.get()) if hasattr(app, "home_commercial_focus_var") else 0
        )
        home_commercial_focus_button_chars = (
            len(app.home_commercial_focus_button_var.get())
            if hasattr(app, "home_commercial_focus_button_var")
            else 0
        )
        home_release_check_chars = (
            len(app.home_release_check_var.get()) if hasattr(app, "home_release_check_var") else 0
        )
        home_release_check_pill_chars = (
            len(str(app.home_release_check_status_pill.cget("text")))
            if hasattr(app, "home_release_check_status_pill")
            else 0
        )
        home_release_check_button_chars = (
            len(app.home_release_check_button_var.get()) if hasattr(app, "home_release_check_button_var") else 0
        )
        home_sales_chars = (
            len(
                app.home_sales_status_var.get()
                + app.home_sales_detail_var.get()
                + app.home_sales_next_var.get()
                + app.home_commercial_focus_var.get()
                + app.home_release_check_var.get()
                + app.home_buyer_send_var.get()
                + app.home_buyer_send_next_var.get()
                + app.home_delivery_release_var.get()
                + app.home_buyer_send_evidence_var.get()
            )
            if hasattr(app, "home_sales_status_var")
            else 0
        )
        home_sales_stage_chars = (
            sum(len(value.get()) for value in app.home_sales_stage_vars.values())
            if hasattr(app, "home_sales_stage_vars")
            else 0
        )
        home_sales_timeline_items = (
            len(app.home_sales_timeline_vars) if hasattr(app, "home_sales_timeline_vars") else 0
        )
        home_sales_timeline_chars = (
            len(app.home_sales_timeline_summary_var.get())
            + sum(len(value.get()) for value in app.home_sales_timeline_vars.values())
            if hasattr(app, "home_sales_timeline_vars")
            else 0
        )
        home_report_items = len(app.home_reports_tree.get_children()) if hasattr(app, "home_reports_tree") else 0
        home_snapshot_items = len(app.home_snapshot_vars) if hasattr(app, "home_snapshot_vars") else 0
        home_snapshot_chars = (
            sum(len(value.get()) for value in app.home_snapshot_vars.values())
            if hasattr(app, "home_snapshot_vars")
            else 0
        )
        home_progress_chars = len(app.home_progress_summary_var.get()) if hasattr(app, "home_progress_summary_var") else 0
        home_progress_stage_chars = (
            sum(len(value.get()) for value in app.home_progress_vars.values())
            if hasattr(app, "home_progress_vars")
            else 0
        )
        home_progress_action_items = (
            len(app.home_progress_buttons) if hasattr(app, "home_progress_buttons") else 0
        )
        home_scrollable = hasattr(app, "home_scroll_canvas")
        home_scrollregion_chars = (
            len(str(app.home_scroll_canvas.cget("scrollregion")))
            if hasattr(app, "home_scroll_canvas")
            else 0
        )
        home_quick_action_items = len(app.home_quick_actions) if hasattr(app, "home_quick_actions") else 0
        home_quick_filter_chars = (
            len(app.home_quick_filter_var.get()) if hasattr(app, "home_quick_filter_var") else 0
        )
        home_quick_status_chars = (
            len(app.home_quick_status_var.get()) if hasattr(app, "home_quick_status_var") else 0
        )
        home_status_badge_chars = (
            len(str(app.home_status_badge.cget("text"))) if hasattr(app, "home_status_badge") else 0
        )
        home_updated_chars = len(app.home_updated_var.get()) if hasattr(app, "home_updated_var") else 0
        home_primary_button_chars = (
            len(app.home_primary_button_var.get()) if hasattr(app, "home_primary_button_var") else 0
        )
        home_first_run_chars = len(app.home_first_run_var.get()) if hasattr(app, "home_first_run_var") else 0
        home_gui_log_chars = len(app.home_gui_log_var.get()) if hasattr(app, "home_gui_log_var") else 0
        style = ttk.Style(app)
        readability_style_chars = len(
            str(style.lookup("Treeview", "rowheight"))
            + str(style.lookup("TNotebook.Tab", "padding"))
            + str(style.lookup("TButton", "padding"))
        )
        ui_density_chars = len(getattr(app.settings, "ui_density", ""))
        active_ui_density_chars = len(app._active_ui_density()) if hasattr(app, "_active_ui_density") else 0
        display_safe_mode = getattr(app, "display_safe_mode", False)
        display_safe_mode_reason = getattr(app, "display_safe_mode_reason", "")
        display_safe_mode_warnings = len(getattr(app, "display_safe_mode_warnings", []))
        header_ui_density_chars = len(app.header_ui_density_var.get()) if hasattr(app, "header_ui_density_var") else 0
        header_display_reset_chars = (
            len(str(app.header_display_reset_button.cget("text")))
            if hasattr(app, "header_display_reset_button")
            else 0
        )
        header_safe_display_chars = (
            len(app.header_safe_display_var.get()) if hasattr(app, "header_safe_display_var") else 0
        )
        header_safe_display_visible = (
            bool(app.header_safe_display_chip.winfo_manager())
            if hasattr(app, "header_safe_display_chip")
            else False
        )
        command_palette_ui_density_actions = sum(
            1 for label, _hint, _action in app.command_palette_actions() if label.startswith("表示サイズ")
        )
        command_palette_display_reset_actions = sum(
            1 for label, _hint, _action in app.command_palette_actions() if label == "表示リセット"
        )
        command_palette_display_diagnostics_actions = sum(
            1 for label, _hint, _action in app.command_palette_actions() if label == "表示診断"
        )
        command_palette_display_diagnostics_copy_actions = sum(
            1 for label, _hint, _action in app.command_palette_actions() if label == "表示診断コピー"
        )
        command_palette_gui_log_clear_actions = sum(
            1 for label, _hint, _action in app.command_palette_actions() if label == "GUIログクリア"
        )
        command_palette_support_display_diagnostics_actions = sum(
            1 for label, _hint, _action in app.command_palette_actions() if label == "ZIP表示診断"
        )
        command_palette_note_login_actions = sum(
            1 for label, _hint, _action in app.command_palette_actions() if label == "noteログイン"
        )
        command_palette_note_login_safety_actions = sum(
            1 for label, _hint, _action in app.command_palette_actions() if label == "ログイン安全ガイド"
        )
        home_quick_login_safety_actions = sum(
            1 for item in getattr(app, "home_quick_actions", []) if item[0] == "ログイン安全ガイド"
        )
        note_login_safety_chars = len(_note_login_safety_text())
        display_readability_status, display_readability_lines = app._display_readability_checks(style)
        display_readability_warnings = sum(1 for line in display_readability_lines if "[WARN]" in line)
        display_button_label_fit_ok, _display_button_label_fit_detail, _display_button_label_fit_lines = (
            app._button_label_fit_details(style)
        )
        display_button_label_fit_status = "OK" if display_button_label_fit_ok else "WARN"
        display_button_label_fit_warnings = 0 if display_button_label_fit_ok else 1
        display_font_family = UI_FONT
        display_actual_font_family = _actual_font_family(app, UI_FONT, UI_TEXT_SIZE)
        display_font_linespace = _font_linespace(app, UI_FONT, UI_TEXT_SIZE) or 0
        display_badge_linespace = _font_linespace(app, UI_FONT, UI_BADGE_FONT_SIZE, weight=UI_BADGE_FONT_WEIGHT) or 0
        display_diagnostics = app._format_display_diagnostics()
        display_diagnostics_chars = len(display_diagnostics)
        diagnostics_chars = len(app.diagnostics_text.get("1.0", tk.END).strip())
        return (
            f"GUI smoke OK: tabs={tabs}, articles={articles}, "
            f"first_run_items={first_run_items}, home_action_items={home_action_items}, "
            f"review_items={review_items}, "
            f"review_detail_action_items={review_detail_action_items}, "
            f"publish_ready_items={publish_ready_items}, "
            f"article_focus_chars={article_focus_chars}, "
            f"commercial_setup_items={commercial_setup_items}, "
            f"commercial_setup_chars={commercial_setup_chars}, "
            f"home_commercial_focus_chars={home_commercial_focus_chars}, "
            f"home_commercial_focus_button_chars={home_commercial_focus_button_chars}, "
            f"home_release_check_chars={home_release_check_chars}, "
            f"home_release_check_pill_chars={home_release_check_pill_chars}, "
            f"home_release_check_button_chars={home_release_check_button_chars}, "
            f"home_sales_chars={home_sales_chars}, "
            f"home_sales_stage_chars={home_sales_stage_chars}, "
            f"home_sales_timeline_items={home_sales_timeline_items}, "
            f"home_sales_timeline_chars={home_sales_timeline_chars}, "
            f"home_report_items={home_report_items}, "
            f"home_snapshot_items={home_snapshot_items}, "
            f"home_snapshot_chars={home_snapshot_chars}, "
            f"home_progress_chars={home_progress_chars}, "
            f"home_progress_stage_chars={home_progress_stage_chars}, "
            f"home_progress_action_items={home_progress_action_items}, "
            f"home_scrollable={home_scrollable}, "
            f"home_scrollregion_chars={home_scrollregion_chars}, "
            f"home_quick_action_items={home_quick_action_items}, "
            f"home_quick_filter_chars={home_quick_filter_chars}, "
            f"home_quick_status_chars={home_quick_status_chars}, "
            f"home_status_badge_chars={home_status_badge_chars}, "
            f"home_updated_chars={home_updated_chars}, "
            f"home_primary_button_chars={home_primary_button_chars}, "
            f"home_first_run_chars={home_first_run_chars}, "
            f"home_gui_log_chars={home_gui_log_chars}, "
            f"readability_style_chars={readability_style_chars}, "
            f"ui_density_chars={ui_density_chars}, "
            f"active_ui_density_chars={active_ui_density_chars}, "
            f"display_safe_mode={display_safe_mode}, "
            f"display_safe_mode_reason={display_safe_mode_reason}, "
            f"display_safe_mode_warnings={display_safe_mode_warnings}, "
            f"header_ui_density_chars={header_ui_density_chars}, "
            f"header_display_reset_chars={header_display_reset_chars}, "
            f"header_safe_display_chars={header_safe_display_chars}, "
            f"header_safe_display_visible={header_safe_display_visible}, "
            f"command_palette_ui_density_actions={command_palette_ui_density_actions}, "
            f"command_palette_display_reset_actions={command_palette_display_reset_actions}, "
            f"command_palette_display_diagnostics_actions={command_palette_display_diagnostics_actions}, "
            f"command_palette_display_diagnostics_copy_actions={command_palette_display_diagnostics_copy_actions}, "
            f"command_palette_gui_log_clear_actions={command_palette_gui_log_clear_actions}, "
            f"command_palette_support_display_diagnostics_actions={command_palette_support_display_diagnostics_actions}, "
            f"command_palette_note_login_actions={command_palette_note_login_actions}, "
            f"command_palette_note_login_safety_actions={command_palette_note_login_safety_actions}, "
            f"home_quick_login_safety_actions={home_quick_login_safety_actions}, "
            f"note_login_safety_chars={note_login_safety_chars}, "
            f"display_readability_status={display_readability_status}, "
            f"display_readability_warnings={display_readability_warnings}, "
            f"display_button_label_fit_status={display_button_label_fit_status}, "
            f"display_button_label_fit_warnings={display_button_label_fit_warnings}, "
            f"display_font_family={display_font_family}, "
            f"display_actual_font_family={display_actual_font_family}, "
            f"display_font_linespace={display_font_linespace}, "
            f"display_badge_linespace={display_badge_linespace}, "
            f"display_diagnostics_chars={display_diagnostics_chars}, "
            f"diagnostics_chars={diagnostics_chars}"
        )
    except Exception as exc:
        raise RuntimeError(f"GUI smoke failed: {exc}") from exc
    finally:
        if app is not None:
            app.destroy()


def _clean_path(path: Path) -> Path:
    value = str(path).strip().strip('"').strip("'")
    return Path(value)


class _VerticalScrollFrame(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.canvas = tk.Canvas(
            self,
            background=UI_COLORS["bg"],
            borderwidth=0,
            highlightthickness=0,
        )
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.body = ttk.Frame(self.canvas)
        self.window_id = self.canvas.create_window((0, 0), window=self.body, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _on_body_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _bind_mousewheel(self, _event: tk.Event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event: tk.Event) -> None:
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event: tk.Event) -> str:
        bbox = self.canvas.bbox("all")
        if not bbox or bbox[3] <= self.canvas.winfo_height():
            return "break"
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if getattr(event, "delta", 0) > 0 else 1
        self.canvas.yview_scroll(delta, "units")
        return "break"


class AutoNoteApp(tk.Tk):
    def __init__(self, project_dir: Path, ui_density_override: str | None = None) -> None:
        _enable_windows_dpi_awareness()
        super().__init__()
        self.project_dir = project_dir.resolve()
        self.articles_dir = self.project_dir / "articles"
        self.output_dir = self.project_dir / ".auto-note"
        self.settings = load_settings(self.project_dir)
        self.display_density_override = _normalise_ui_density(ui_density_override) if ui_density_override else ""
        self.display_safe_mode = bool(self.display_density_override)
        self.display_safe_mode_reason = "requested" if self.display_safe_mode else ""
        self.display_safe_mode_warnings: list[str] = []
        self.article_paths: list[Path] = []
        self.selected_article: Article | None = None
        self.idea_ids: list[int] = []
        self._notification_job: str | None = None
        self._autosave_job: str | None = None
        self._last_autosave_text = ""
        self._ignored_autosaves: set[Path] = set()
        self._home_primary_step: ActionPlanStep | None = None
        self._home_action_steps: list[ActionPlanStep] = []
        self._last_first_run_report: FirstRunReport | None = None
        self._last_review_results: list[ArticleReview] = []
        self._last_publish_ready_report: PublishReadyReport | None = None
        self._last_publish_queue_report: PublishQueueReport | None = None
        self._last_improvement_plan: ImprovementPlan | None = None
        self._last_article_focus_plan: ImprovementPlan | None = None
        self._release_check_thread: threading.Thread | None = None
        self.editor_dirty = False
        self._restoring_selection = False
        self._home_sales_next_step = None
        self._home_report_paths: dict[str, tuple[str, Path]] = {}

        self.title("auto-note")
        self.configure(bg=UI_COLORS["bg"])

        self._configure_style()
        self._configure_window_bounds()
        self._auto_enable_safe_display_if_needed()
        self._build_ui()
        self._bind_shortcuts()
        self.report_callback_exception = self.handle_callback_exception
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_articles()
        self.refresh_ideas()
        self.refresh_schedule()
        self.refresh_home()
        self.refresh_first_run_panel()
        self.refresh_review_panel()
        self.refresh_help()
        self.run_check_all(show_popup=False)
        self.run_diagnostics_to_tab()
        if self.display_safe_mode:
            if self.display_safe_mode_reason == "auto-readability":
                message = "表示を自動補正: 文字が潰れそうなため大きめ表示で起動しました"
            else:
                message = "表示セーフモード: 大きめ表示で起動しました"
            self.after(
                500,
                lambda: self.notify(message, level="warning"),
            )
        self.after(350, self.show_onboarding_if_needed)
        self.schedule_autosave()

    def _active_ui_density(self) -> str:
        return self.display_density_override or _normalise_ui_density(getattr(self.settings, "ui_density", "comfortable"))

    def _configure_window_bounds(self) -> None:
        min_width, min_height = _scaled_window_size(self, UI_BASE_MIN_SIZE, UI_MIN_WINDOW_SCREEN_RATIO)
        width, height = _scaled_window_size(self, UI_BASE_WINDOW_SIZE, UI_INITIAL_WINDOW_SCREEN_RATIO)
        width = max(width, min_width)
        height = max(height, min_height)
        self.geometry(f"{width}x{height}")
        self.minsize(min_width, min_height)

    def _configure_style(self) -> None:
        global UI_FONT, CODE_FONT
        _apply_ui_density(self._active_ui_density())
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        UI_FONT = _resolve_font_family(
            self,
            UI_FONT_CANDIDATES,
            minimum_linespace_ratio=UI_MIN_FONT_LINESPACE_RATIO,
        )
        CODE_FONT = _resolve_font_family(self, CODE_FONT_CANDIDATES)
        _configure_tk_font_defaults(self, UI_FONT, CODE_FONT)
        _guard_ui_readability_metrics(self, UI_FONT)
        font = UI_FONT
        self.option_add("*Font", f"{{{font}}} {UI_TEXT_SIZE}")
        bg = UI_COLORS["bg"]
        surface = UI_COLORS["surface"]
        surface_alt = UI_COLORS["surface_alt"]
        selected = UI_COLORS["surface_selected"]
        primary = UI_COLORS["ink"]
        muted = UI_COLORS["muted"]
        line = UI_COLORS["line"]
        line_strong = UI_COLORS["line_strong"]
        chrome = UI_COLORS["chrome"]
        chrome_alt = UI_COLORS["chrome_alt"]
        chrome_muted = UI_COLORS["chrome_muted"]
        accent = UI_COLORS["accent"]
        style.configure("TFrame", background=bg)
        style.configure("Surface.TFrame", background=surface)
        style.configure("HomeLead.TFrame", background=UI_COLORS["surface_strong"])
        style.configure("HomeSnapshot.TFrame", background=surface)
        style.configure("HomeSnapshotTile.TFrame", background=surface_alt)
        style.configure("ArticleFocus.TFrame", background=surface_alt)
        style.configure("Elevated.TFrame", background=surface, relief="flat", borderwidth=1)
        style.configure("Toolbar.TFrame", background=surface_alt)
        style.configure("Chrome.TFrame", background=chrome)
        style.configure("ChromeAlt.TFrame", background=chrome_alt)
        style.configure("TLabel", background=bg, foreground=primary, font=(font, UI_TEXT_SIZE))
        style.configure("Surface.TLabel", background=surface, foreground=primary, font=(font, UI_TEXT_SIZE))
        style.configure(
            "HomeLead.TLabel",
            background=UI_COLORS["surface_strong"],
            foreground=primary,
            font=(font, UI_TEXT_SIZE),
        )
        style.configure(
            "HomeLeadMuted.TLabel",
            background=UI_COLORS["surface_strong"],
            foreground=muted,
            font=(font, UI_SMALL_TEXT_SIZE),
        )
        style.configure(
            "HomeEyebrow.TLabel",
            background=UI_COLORS["surface_strong"],
            foreground=accent,
            font=(font, UI_SMALL_TEXT_SIZE),
        )
        style.configure(
            "HomeTitle.TLabel",
            background=UI_COLORS["surface_strong"],
            foreground=primary,
            font=(font, 22, UI_HEADING_FONT_WEIGHT),
        )
        style.configure("SurfaceMuted.TLabel", background=surface, foreground=muted, font=(font, UI_SMALL_TEXT_SIZE))
        style.configure("Muted.TLabel", background=surface, foreground=muted, font=(font, UI_SMALL_TEXT_SIZE))
        style.configure("SmallMuted.TLabel", background=surface_alt, foreground=muted, font=(font, UI_SMALL_TEXT_SIZE))
        style.configure(
            "HomeSnapshotTitle.TLabel",
            background=surface_alt,
            foreground=muted,
            font=(font, UI_SMALL_TEXT_SIZE),
        )
        style.configure(
            "HomeSnapshotValue.TLabel",
            background=surface_alt,
            foreground=primary,
            font=(font, UI_TEXT_SIZE),
        )
        style.configure(
            "ArticleFocusTitle.TLabel",
            background=surface_alt,
            foreground=muted,
            font=(font, UI_SMALL_TEXT_SIZE),
        )
        style.configure(
            "ArticleFocusValue.TLabel",
            background=surface_alt,
            foreground=primary,
            font=(font, UI_TEXT_SIZE),
        )
        style.configure("ArticleFocusMuted.TLabel", background=surface_alt, foreground=muted, font=(font, UI_SMALL_TEXT_SIZE))
        style.configure("PageTitle.TLabel", background=bg, foreground=primary, font=(font, 20, UI_HEADING_FONT_WEIGHT))
        style.configure("PageSubtitle.TLabel", background=bg, foreground=muted, font=(font, UI_TEXT_SIZE))
        style.configure("AppTitle.TLabel", background=chrome, foreground="#ffffff", font=(font, 19, UI_HEADING_FONT_WEIGHT))
        style.configure("ChromeMuted.TLabel", background=chrome, foreground=chrome_muted, font=(font, UI_SMALL_TEXT_SIZE))
        style.configure("ChromeAction.TLabel", background=chrome_alt, foreground="#ffffff", font=(font, UI_TEXT_SIZE))
        style.configure(
            "ChromeChip.TLabel",
            background=UI_COLORS["chrome_chip"],
            foreground="#ffffff",
            font=(font, UI_SMALL_TEXT_SIZE),
            padding=(9, 5),
        )
        style.configure(
            "Chrome.TCombobox",
            padding=(7, 5),
            fieldbackground=UI_COLORS["chrome_chip"],
            background=chrome_alt,
            foreground="#ffffff",
            arrowcolor=chrome_muted,
            bordercolor="#475569",
            lightcolor="#475569",
            darkcolor="#475569",
            font=(font, UI_SMALL_TEXT_SIZE),
        )
        style.map(
            "Chrome.TCombobox",
            fieldbackground=[("readonly", UI_COLORS["chrome_chip"]), ("focus", UI_COLORS["chrome_chip"])],
            foreground=[("readonly", "#ffffff"), ("focus", "#ffffff")],
            arrowcolor=[("active", "#ffffff"), ("pressed", "#ffffff")],
            bordercolor=[("focus", UI_COLORS["focus"]), ("active", "#64748b")],
        )
        style.configure("Title.TLabel", background=surface, foreground=primary, font=(font, 16, UI_HEADING_FONT_WEIGHT))
        style.configure("KpiLabel.TLabel", background=surface, foreground=muted, font=(font, UI_SMALL_TEXT_SIZE))
        style.configure("KpiValue.TLabel", background=surface, foreground=primary, font=(font, 20, UI_HEADING_FONT_WEIGHT))
        style.configure("KpiHint.TLabel", background=surface, foreground=muted, font=(font, UI_SMALL_TEXT_SIZE))
        style.configure("TNotebook", background=bg, borderwidth=0, tabmargins=(0, 8, 0, 0))
        style.configure(
            "TNotebook.Tab",
            padding=UI_NOTEBOOK_TAB_PADDING,
            font=(font, UI_TEXT_SIZE, UI_CONTROL_FONT_WEIGHT),
            background=surface_alt,
            foreground=muted,
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", surface), ("active", selected)],
            foreground=[("selected", primary), ("active", primary)],
        )
        style.configure(
            "TEntry",
            padding=(9, 7),
            fieldbackground=UI_COLORS["text_bg"],
            foreground=primary,
            font=(font, UI_TEXT_SIZE),
            bordercolor=line,
            lightcolor=line,
            darkcolor=line,
            borderwidth=1,
            relief="flat",
        )
        style.map(
            "TEntry",
            fieldbackground=[("disabled", surface_alt), ("focus", "#ffffff")],
            bordercolor=[("focus", accent), ("active", line_strong)],
        )
        style.configure(
            "TCombobox",
            padding=(9, 7),
            fieldbackground=UI_COLORS["text_bg"],
            background=surface,
            foreground=primary,
            font=(font, UI_TEXT_SIZE),
            arrowcolor=muted,
            bordercolor=line,
            lightcolor=line,
            darkcolor=line,
            borderwidth=1,
            relief="flat",
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", UI_COLORS["text_bg"]), ("focus", "#ffffff")],
            bordercolor=[("focus", accent), ("active", line_strong)],
            arrowcolor=[("active", accent), ("pressed", accent)],
        )
        style.configure("TCheckbutton", background=surface, foreground=primary, font=(font, UI_TEXT_SIZE), padding=(2, 5))
        style.map("TCheckbutton", background=[("active", surface), ("pressed", surface)], foreground=[("active", primary)])
        style.configure(
            "Treeview",
            background=surface,
            fieldbackground=surface,
            foreground=primary,
            rowheight=UI_TREE_ROW_HEIGHT,
            borderwidth=0,
            font=(font, UI_TEXT_SIZE),
        )
        style.configure(
            "Treeview.Heading",
            background=surface_alt,
            foreground=muted,
            font=(font, UI_SMALL_TEXT_SIZE),
            padding=(8, 10),
            relief="flat",
        )
        style.map("Treeview", background=[("selected", selected)], foreground=[("selected", primary)])
        style.configure(
            "Vertical.TScrollbar",
            background=surface_alt,
            troughcolor=bg,
            arrowcolor=muted,
            bordercolor=bg,
            lightcolor=bg,
            darkcolor=bg,
        )
        style.configure(
            "Horizontal.TScrollbar",
            background=surface_alt,
            troughcolor=bg,
            arrowcolor=muted,
            bordercolor=bg,
            lightcolor=bg,
            darkcolor=bg,
        )
        style.configure("TProgressbar", background=accent, troughcolor=surface_alt, borderwidth=0)
        style.configure(
            "TButton",
            padding=UI_BUTTON_PADDING,
            font=(font, UI_TEXT_SIZE, UI_CONTROL_FONT_WEIGHT),
            background=surface_alt,
            foreground=primary,
            bordercolor=line,
            lightcolor=line,
            darkcolor=line,
        )
        style.map("TButton", background=[("active", selected), ("pressed", "#d9ece8")])
        style.configure(
            "Secondary.TButton",
            padding=UI_BUTTON_PADDING,
            font=(font, UI_TEXT_SIZE, UI_CONTROL_FONT_WEIGHT),
            background=surface,
            foreground=primary,
            bordercolor=line,
            lightcolor=line,
            darkcolor=line,
        )
        style.map(
            "Secondary.TButton",
            background=[("active", UI_COLORS["surface_hover"]), ("pressed", selected)],
        )
        style.configure(
            "Primary.TButton",
            padding=UI_PRIMARY_BUTTON_PADDING,
            font=(font, UI_TEXT_SIZE, UI_CONTROL_FONT_WEIGHT),
            background=accent,
            foreground="#ffffff",
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[
                ("active", UI_COLORS["accent_hover"]),
                ("pressed", UI_COLORS["accent_pressed"]),
                ("disabled", "#8acfc5"),
            ],
            foreground=[("disabled", "#ecfdf5")],
        )
        style.configure(
            "Quiet.TButton",
            padding=UI_BUTTON_PADDING,
            font=(font, UI_TEXT_SIZE, UI_CONTROL_FONT_WEIGHT),
            background=chrome_alt,
            foreground="#ffffff",
        )
        style.map("Quiet.TButton", background=[("active", "#2b394c"), ("pressed", "#34445a")])
        style.configure(
            "Danger.TButton",
            padding=UI_DANGER_BUTTON_PADDING,
            font=(font, UI_TEXT_SIZE, UI_CONTROL_FONT_WEIGHT),
            background=UI_COLORS["danger_soft"],
            foreground="#991b1b",
        )
        style.map("Danger.TButton", background=[("active", "#fecaca"), ("pressed", "#fca5a5")])
        style.configure("TLabelframe", background=surface, padding=14, relief="flat", borderwidth=0)
        style.configure("TLabelframe.Label", background=surface, foreground=primary, font=(font, UI_TEXT_SIZE))

    def _auto_enable_safe_display_if_needed(self) -> None:
        if self.display_safe_mode:
            return
        status, lines = self._display_readability_checks()
        if status == "OK":
            return
        self.display_density_override = "large"
        self.display_safe_mode = True
        self.display_safe_mode_reason = "auto-readability"
        self.display_safe_mode_warnings = [line for line in lines if "[WARN]" in line]
        self._configure_style()

    def _safe_display_badge_label(self) -> str:
        return "AUTO SAFE" if self.display_safe_mode_reason == "auto-readability" else "SAFE DISPLAY"

    def _sync_header_display_state(self) -> None:
        if hasattr(self, "header_ui_density_var"):
            self.header_ui_density_var.set(_ui_density_label(self._active_ui_density()))
        badge = getattr(self, "header_safe_display_chip", None)
        badge_var = getattr(self, "header_safe_display_var", None)
        if badge is None or badge_var is None:
            return
        badge_var.set(self._safe_display_badge_label())
        if self.display_safe_mode:
            if not badge.winfo_manager():
                project_label = getattr(self, "header_project_name_label", None)
                pack_options = {"side": tk.LEFT, "padx": (6, 0)}
                if project_label is not None:
                    pack_options["before"] = project_label
                badge.pack(**pack_options)
        elif badge.winfo_manager():
            badge.pack_forget()

    def _manual_status_widgets(self) -> list[tk.Label]:
        widgets: list[tk.Label] = []
        for name in (
            "home_status_badge",
            "home_first_run_status_pill",
            "home_gui_log_status_pill",
            "home_sales_status_pill",
            "home_buyer_send_status_pill",
            "home_release_check_status_pill",
            "first_run_status_pill",
            "status_pill",
            "article_focus_status_pill",
            "publish_ready_status_pill",
            "support_send_readiness_status_pill",
            "support_contact_status_pill",
            "support_bundle_status_pill",
            "notification",
        ):
            widget = getattr(self, name, None)
            if isinstance(widget, tk.Label):
                widgets.append(widget)
        for name in (
            "home_snapshot_pills",
            "home_progress_pills",
            "home_sales_stage_pills",
            "home_sales_timeline_pills",
        ):
            collection = getattr(self, name, {})
            if isinstance(collection, dict):
                widgets.extend(widget for widget in collection.values() if isinstance(widget, tk.Label))
        return widgets

    def _refresh_manual_readability_widgets(self) -> None:
        badge_linespace = _font_linespace(self, UI_FONT, UI_BADGE_FONT_SIZE, weight=UI_BADGE_FONT_WEIGHT)
        badge_padding = max(6, math.ceil((badge_linespace or UI_BADGE_FONT_SIZE + 7) * 0.38))
        for widget in self._manual_status_widgets():
            try:
                widget.configure(
                    font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
                    pady=badge_padding,
                )
            except tk.TclError:
                continue

    def _refresh_text_widget_readability(self) -> None:
        for name, code in (
            ("home_text", True),
            ("preview", False),
            ("editor", False),
            ("schedule_text", True),
            ("check_text", True),
            ("settings_help_box", False),
            ("diagnostics_text", True),
            ("help_text", False),
        ):
            widget = getattr(self, name, None)
            if isinstance(widget, tk.Text):
                try:
                    _style_text_widget(widget, code=code)
                except tk.TclError:
                    continue

    def _build_ui(self) -> None:
        self.configure(bg=UI_COLORS["bg"])
        shell = ttk.Frame(self, padding=(16, 16, 16, 12))
        shell.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(shell, style="Chrome.TFrame", padding=(18, 13))
        header.pack(fill=tk.X, pady=(0, 12))
        brand = ttk.Frame(header, style="Chrome.TFrame")
        brand.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(brand, text="auto-note", style="AppTitle.TLabel").pack(anchor=tk.W)
        meta = ttk.Frame(brand, style="Chrome.TFrame")
        meta.pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(meta, text="LOCAL WORKSPACE", style="ChromeChip.TLabel").pack(side=tk.LEFT)
        ttk.Label(meta, text=f"v{__version__}", style="ChromeChip.TLabel").pack(side=tk.LEFT, padx=(6, 0))
        self.header_safe_display_var = tk.StringVar(value=self._safe_display_badge_label())
        self.header_safe_display_chip = ttk.Label(meta, textvariable=self.header_safe_display_var, style="ChromeChip.TLabel")
        if self.display_safe_mode:
            self.header_safe_display_chip.pack(side=tk.LEFT, padx=(6, 0))
        self.header_project_name_label = ttk.Label(meta, text=self.project_dir.name, style="ChromeMuted.TLabel")
        self.header_project_name_label.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(
            brand,
            text=str(self.project_dir),
            style="ChromeMuted.TLabel",
        ).pack(anchor=tk.W, pady=(3, 0))

        ttk.Button(header, text="新規記事", style="Primary.TButton", command=self.new_article).pack(side=tk.RIGHT)
        ttk.Button(header, text="更新", style="Quiet.TButton", command=self.refresh_all).pack(side=tk.RIGHT, padx=6)
        ttk.Button(header, text="コマンド検索", style="Quiet.TButton", command=self.show_command_palette).pack(
            side=tk.RIGHT,
            padx=6,
        )
        density = ttk.Frame(header, style="ChromeAlt.TFrame", padding=(10, 7))
        density.pack(side=tk.RIGHT, padx=(0, 6))
        ttk.Label(density, text="表示", style="ChromeAction.TLabel").pack(side=tk.LEFT)
        self.header_ui_density_var = tk.StringVar(value=_ui_density_label(self._active_ui_density()))
        self.header_ui_density_combo = ttk.Combobox(
            density,
            textvariable=self.header_ui_density_var,
            values=tuple(UI_DENSITY_LABELS.values()),
            state="readonly",
            width=8,
            style="Chrome.TCombobox",
            font=(UI_FONT, UI_SMALL_TEXT_SIZE),
        )
        self.header_ui_density_combo.pack(side=tk.LEFT, padx=(8, 0))
        self.header_ui_density_combo.bind("<<ComboboxSelected>>", self.on_header_ui_density_selected)
        self.header_display_reset_button = ttk.Button(
            density,
            text="リセット",
            style="Quiet.TButton",
            command=self.reset_display_action,
        )
        self.header_display_reset_button.pack(side=tk.LEFT, padx=(8, 0))
        quick = ttk.Frame(header, style="ChromeAlt.TFrame", padding=(10, 7))
        quick.pack(side=tk.RIGHT, padx=(0, 6))
        ttk.Label(quick, text="note", style="ChromeAction.TLabel").pack(side=tk.LEFT)
        ttk.Button(quick, text="ログイン", style="Quiet.TButton", command=self.open_note_login_action).pack(
            side=tk.LEFT,
            padx=(8, 0),
        )

        self.notebook = ttk.Notebook(shell)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.home_tab = ttk.Frame(self.notebook, padding=10)
        self.first_run_tab = ttk.Frame(self.notebook, padding=10)
        self.article_tab = ttk.Frame(self.notebook, padding=10)
        self.ideas_tab = ttk.Frame(self.notebook, padding=10)
        self.schedule_tab = ttk.Frame(self.notebook, padding=10)
        self.check_tab = ttk.Frame(self.notebook, padding=10)
        self.settings_tab = ttk.Frame(self.notebook, padding=10)
        self.diagnostics_tab = ttk.Frame(self.notebook, padding=10)
        self.help_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.home_tab, text="ホーム")
        self.notebook.add(self.first_run_tab, text="初回")
        self.notebook.add(self.article_tab, text="記事")
        self.notebook.add(self.ideas_tab, text="アイデア")
        self.notebook.add(self.schedule_tab, text="予定")
        self.notebook.add(self.check_tab, text="チェック")
        self.notebook.add(self.settings_tab, text="設定")
        self.notebook.add(self.diagnostics_tab, text="診断")
        self.notebook.add(self.help_tab, text="ヘルプ")

        self._build_home_tab()
        self._build_first_run_tab()
        self._build_article_tab()
        self._build_ideas_tab()
        self._build_schedule_tab()
        self._build_check_tab()
        self._build_settings_tab()
        self._build_diagnostics_tab()
        self._build_help_tab()
        self._build_notification_bar(shell)
        self._refresh_manual_readability_widgets()

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-n>", lambda _event: self.new_article())
        self.bind_all("<Control-s>", lambda _event: self.save_editor())
        self.bind_all("<F5>", lambda _event: self.refresh_all())
        self.bind_all("<Control-k>", lambda _event: self.show_command_palette())
        self.bind_all("<Control-Return>", lambda _event: self.open_helper())
        self.bind_all("<Control-Shift-C>", lambda _event: self.copy_selected("body"))

    def _build_home_tab(self) -> None:
        home_scroll = _VerticalScrollFrame(self.home_tab)
        home_scroll.pack(fill=tk.BOTH, expand=True)
        self.home_scroll_frame = home_scroll
        self.home_scroll_canvas = home_scroll.canvas
        home = home_scroll.body

        top = ttk.Frame(home, style="HomeLead.TFrame", padding=(16, 14))
        top.pack(fill=tk.X, pady=(0, 10))
        tk.Frame(top, bg=UI_COLORS["accent"], width=4).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        title_group = ttk.Frame(top, style="HomeLead.TFrame")
        title_group.pack(side=tk.LEFT, fill=tk.X, expand=True)
        meta_row = ttk.Frame(title_group, style="HomeLead.TFrame")
        meta_row.pack(fill=tk.X)
        ttk.Label(meta_row, text="WORKSPACE STATUS", style="HomeEyebrow.TLabel").pack(side=tk.LEFT)
        self.home_status_badge = tk.Label(
            meta_row,
            text="CHECK",
            bg=UI_COLORS["warn"],
            fg="#ffffff",
            font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
            padx=9,
            pady=4,
            width=12,
        )
        self.home_status_badge.pack(side=tk.LEFT, padx=(10, 0))
        self.home_updated_var = tk.StringVar(value="更新待ち")
        ttk.Label(meta_row, textvariable=self.home_updated_var, style="HomeLeadMuted.TLabel").pack(
            side=tk.LEFT,
            padx=(10, 0),
        )
        ttk.Label(title_group, text="今日の状態", style="HomeTitle.TLabel").pack(anchor=tk.W, pady=(2, 0))
        ttk.Label(
            title_group,
            text="記事、投稿準備、販売、サポートを同じ作業面で確認します。",
            style="HomeLeadMuted.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))
        ttk.Button(top, text="新規記事", style="Primary.TButton", command=self.new_article).pack(side=tk.RIGHT)
        ttk.Button(top, text="コマンド検索", style="Secondary.TButton", command=self.show_command_palette).pack(
            side=tk.RIGHT,
            padx=6,
        )
        ttk.Button(
            top,
            text="診断",
            style="Secondary.TButton",
            command=lambda: self.notebook.select(self.diagnostics_tab),
        ).pack(side=tk.RIGHT, padx=6)

        snapshot = ttk.Frame(home, style="HomeSnapshot.TFrame")
        snapshot.pack(fill=tk.X, pady=(0, 10))
        self.home_snapshot_vars: dict[str, tk.StringVar] = {}
        self.home_snapshot_pills: dict[str, tk.Label] = {}
        self.home_snapshot_rails: dict[str, tk.Frame] = {}
        for index, (key, label) in enumerate(
            (
                ("readiness", "準備度"),
                ("next", "次の一手"),
                ("startup", "初回/復旧"),
                ("sales", "販売/送付"),
            )
        ):
            tile = ttk.Frame(snapshot, style="HomeSnapshotTile.TFrame", padding=(10, 9))
            tile.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 8, 0))
            snapshot.columnconfigure(index, weight=1, uniform="home_snapshot")
            rail = tk.Frame(tile, bg=UI_COLORS["line"], height=3)
            rail.pack(fill=tk.X, pady=(0, 8))
            self.home_snapshot_rails[key] = rail
            head = ttk.Frame(tile, style="HomeSnapshotTile.TFrame")
            head.pack(fill=tk.X)
            ttk.Label(head, text=label, style="HomeSnapshotTitle.TLabel").pack(side=tk.LEFT)
            pill = tk.Label(
                head,
                text="CHECK",
                bg=UI_COLORS["warn"],
                fg="#ffffff",
                font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
                padx=7,
                pady=3,
                width=8,
            )
            pill.pack(side=tk.RIGHT)
            self.home_snapshot_pills[key] = pill
            value = tk.StringVar(value="確認中")
            self.home_snapshot_vars[key] = value
            ttk.Label(
                tile,
                textvariable=value,
                style="HomeSnapshotValue.TLabel",
                wraplength=250,
            ).pack(anchor=tk.W, fill=tk.X, pady=(5, 0))

        self.kpi_frame = ttk.Frame(home)
        self.kpi_frame.pack(fill=tk.X, pady=(0, 10))
        self.kpi_vars: dict[str, tk.StringVar] = {}
        for index, key in enumerate(("準備度", "記事", "下書き", "準備OK", "予定", "公開済み")):
            box = ttk.Frame(self.kpi_frame, style="Surface.TFrame", padding=14)
            box.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 8, 0))
            tk.Frame(box, bg=UI_COLORS["accent"] if index == 0 else UI_COLORS["line"], height=3).pack(
                fill=tk.X,
                pady=(0, 9),
            )
            value = tk.StringVar(value="0")
            self.kpi_vars[key] = value
            ttk.Label(box, text=key, style="KpiLabel.TLabel").pack(anchor=tk.W)
            ttk.Label(box, textvariable=value, style="KpiValue.TLabel").pack(anchor=tk.W, pady=(4, 0))
            self.kpi_frame.columnconfigure(index, weight=1)

        progress = ttk.LabelFrame(home, text="作業進行", padding=10)
        progress.pack(fill=tk.X, pady=(0, 10))
        progress_header = ttk.Frame(progress, style="Surface.TFrame")
        progress_header.pack(fill=tk.X, pady=(0, 8))
        self.home_progress_summary_var = tk.StringVar(value="投稿までの進行状況を確認中です。")
        self.home_primary_button_var = tk.StringVar(value="次を実行")
        ttk.Label(
            progress_header,
            textvariable=self.home_progress_summary_var,
            style="Muted.TLabel",
            wraplength=820,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            progress_header,
            textvariable=self.home_primary_button_var,
            style="Primary.TButton",
            command=self.run_home_primary_action,
        ).pack(
            side=tk.RIGHT,
            padx=(6, 0),
        )
        ttk.Button(progress_header, text="詳細", command=self.run_action_plan_to_tab).pack(side=tk.RIGHT)

        self.home_progress_vars: dict[str, tk.StringVar] = {}
        self.home_progress_pills: dict[str, tk.Label] = {}
        self.home_progress_buttons: dict[str, ttk.Button] = {}
        self.home_progress_rails: dict[str, tk.Frame] = {}
        progress_steps = ttk.Frame(progress, style="Surface.TFrame")
        progress_steps.pack(fill=tk.X)
        for index, (key, label) in enumerate(
            (
                ("setup", "初回"),
                ("article", "記事"),
                ("review", "仕上げ"),
                ("publish", "投稿"),
                ("sales", "販売"),
                ("support", "サポート"),
            )
        ):
            step = ttk.Frame(progress_steps, style="Toolbar.TFrame", padding=(8, 8))
            step.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 8, 0))
            progress_steps.columnconfigure(index, weight=1, uniform="home_progress")
            rail = tk.Frame(step, bg=UI_COLORS["line"], height=3)
            rail.pack(fill=tk.X, pady=(0, 7))
            self.home_progress_rails[key] = rail
            ttk.Label(step, text=label, style="SmallMuted.TLabel").pack(anchor=tk.W)
            row = ttk.Frame(step, style="Toolbar.TFrame")
            row.pack(fill=tk.X, pady=(3, 0))
            pill = tk.Label(
                row,
                text="CHECK",
                bg="#8a4f00",
                fg="#ffffff",
                font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
                padx=8,
                pady=4,
                width=8,
            )
            pill.pack(side=tk.LEFT)
            value = tk.StringVar(value="確認中")
            self.home_progress_vars[key] = value
            self.home_progress_pills[key] = pill
            ttk.Label(row, textvariable=value, style="SmallMuted.TLabel", wraplength=140).pack(
                side=tk.LEFT,
                fill=tk.X,
                expand=True,
                padx=(6, 0),
            )
            button = ttk.Button(
                step,
                text="開く",
                command=lambda stage_key=key: self.open_home_progress_stage(stage_key),
            )
            button.pack(anchor=tk.W, pady=(5, 0))
            self.home_progress_buttons[key] = button

        first_run_box = ttk.LabelFrame(home, text="初回セットアップ", padding=10)
        first_run_box.pack(fill=tk.X, pady=(0, 10))
        first_run_text = ttk.Frame(first_run_box, style="Surface.TFrame")
        first_run_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        first_run_row = ttk.Frame(first_run_text, style="Surface.TFrame")
        first_run_row.pack(fill=tk.X)
        self.home_first_run_status_pill = tk.Label(
            first_run_row,
            text="CHECK",
            bg="#8a4f00",
            fg="#ffffff",
            font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
            padx=10,
            pady=4,
            width=12,
        )
        self.home_first_run_status_pill.pack(side=tk.LEFT)
        self.home_first_run_var = tk.StringVar(value="初回チェックを確認中です。")
        ttk.Label(first_run_row, textvariable=self.home_first_run_var, style="Surface.TLabel").pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=(10, 0),
        )
        self.home_first_run_next_var = tk.StringVar(value="")
        ttk.Label(
            first_run_text,
            textvariable=self.home_first_run_next_var,
            style="Muted.TLabel",
            wraplength=820,
        ).pack(anchor=tk.W, pady=(6, 0))
        first_run_actions = ttk.Frame(first_run_box, style="Surface.TFrame")
        first_run_actions.pack(side=tk.RIGHT, padx=(12, 0))
        self._build_button_bar(
            first_run_actions,
            [
                ("初回を開く", self.open_home_first_run_status, "Primary.TButton"),
                ("再チェック", self.run_first_run_to_tab),
                ("セットアップ", lambda: self.show_setup_wizard(force=True)),
                ("スターター", self.create_starter_pack_action),
            ],
            columns=2,
        )

        focus = ttk.Frame(home, style="Surface.TFrame", padding=12)
        focus.pack(fill=tk.X, pady=(0, 10))
        focus_text = ttk.Frame(focus, style="Surface.TFrame")
        focus_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(focus_text, text="おすすめ", style="Muted.TLabel").pack(anchor=tk.W)
        self.home_focus_var = tk.StringVar(value="アクションプランを確認中です。")
        ttk.Label(focus_text, textvariable=self.home_focus_var, style="Surface.TLabel", wraplength=820).pack(
            anchor=tk.W,
            pady=(4, 0),
        )
        ttk.Button(
            focus,
            textvariable=self.home_primary_button_var,
            style="Primary.TButton",
            command=self.run_home_primary_action,
        ).pack(
            side=tk.RIGHT,
            padx=(8, 0),
        )
        ttk.Button(focus, text="詳細", command=self.run_action_plan_to_tab).pack(side=tk.RIGHT)

        recovery_box = ttk.LabelFrame(home, text="復旧ステータス", padding=10)
        recovery_box.pack(fill=tk.X, pady=(0, 10))
        recovery_text = ttk.Frame(recovery_box, style="Surface.TFrame")
        recovery_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        recovery_row = ttk.Frame(recovery_text, style="Surface.TFrame")
        recovery_row.pack(fill=tk.X)
        self.home_gui_log_status_pill = tk.Label(
            recovery_row,
            text="OK",
            bg="#047857",
            fg="#ffffff",
            font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
            padx=10,
            pady=4,
            width=12,
        )
        self.home_gui_log_status_pill.pack(side=tk.LEFT)
        self.home_gui_log_var = tk.StringVar(value="GUIログを確認中です。")
        ttk.Label(recovery_row, textvariable=self.home_gui_log_var, style="Surface.TLabel").pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=(10, 0),
        )
        ttk.Label(
            recovery_text,
            text="ログがある時は、内容確認、復旧セット、問い合わせ一式までここから進めます。",
            style="Muted.TLabel",
            wraplength=820,
        ).pack(anchor=tk.W, pady=(6, 0))
        recovery_actions = ttk.Frame(recovery_box, style="Surface.TFrame")
        recovery_actions.pack(side=tk.RIGHT, padx=(12, 0))
        self._build_button_bar(
            recovery_actions,
            [
                ("GUIログ表示", self.show_gui_log_action, "Primary.TButton"),
                ("復旧セット", self.run_recovery_kit_to_tab),
                ("問い合わせ一式", self.create_support_bundle_action),
                ("ログクリア", self.clear_gui_log_action, "Danger.TButton"),
                ("場所", self.open_gui_log_folder_action),
            ],
            columns=3,
        )

        sales_box = ttk.LabelFrame(home, text="販売準備", padding=10)
        sales_box.pack(fill=tk.X, pady=(0, 10))
        sales_text = ttk.Frame(sales_box, style="Surface.TFrame")
        sales_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.home_sales_status_var = tk.StringVar(value="販売準備を確認中です。")
        self.home_sales_detail_var = tk.StringVar(value="")
        self.home_sales_next_var = tk.StringVar(value="")
        self.home_commercial_focus_var = tk.StringVar(value="販売者次項目を確認中です。")
        self.home_commercial_focus_button_var = tk.StringVar(value="販売者次へ")
        self.home_release_check_var = tk.StringVar(value="販売前一括チェックを確認中です。")
        self.home_release_check_button_var = tk.StringVar(value="一括実行")
        self.home_buyer_send_var = tk.StringVar(value="購入者送付を確認中です。")
        self.home_buyer_send_next_var = tk.StringVar(value="")
        self.home_buyer_send_action_var = tk.StringVar(value="購入者ZIP作成")
        self.home_buyer_send_button_var = tk.StringVar(
            value=_home_buyer_send_button_label(self.home_buyer_send_action_var.get())
        )
        self.home_delivery_release_var = tk.StringVar(value="納品照合を確認中です。")
        self.home_buyer_send_evidence_var = tk.StringVar(value="送付証跡を確認中です。")
        self.home_support_next_button_var = tk.StringVar(
            value=_home_support_next_button_label("問い合わせ一式を作成")
        )
        self.home_sales_timeline_summary_var = tk.StringVar(value="販売準備タイムラインを確認中です。")
        sales_status_row = ttk.Frame(sales_text, style="Surface.TFrame")
        sales_status_row.pack(fill=tk.X)
        self.home_sales_status_pill = tk.Label(
            sales_status_row,
            text="CHECK",
            bg="#8a4f00",
            fg="#ffffff",
            font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
            padx=10,
            pady=4,
            width=12,
        )
        self.home_sales_status_pill.pack(side=tk.LEFT)
        ttk.Label(sales_status_row, textvariable=self.home_sales_status_var, style="Surface.TLabel").pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=(10, 0),
        )
        self.home_sales_stage_vars: dict[str, tk.StringVar] = {}
        self.home_sales_stage_pills: dict[str, tk.Label] = {}
        sales_stage_bar = ttk.Frame(sales_text, style="Surface.TFrame")
        sales_stage_bar.pack(fill=tk.X, pady=(8, 0))
        for index, (key, label) in enumerate(
            (
                ("seller", "販売者情報"),
                ("release", "配布ZIP"),
                ("buyer", "購入者ZIP"),
                ("send", "送付準備"),
                ("support", "サポート"),
            )
        ):
            stage = ttk.Frame(sales_stage_bar, style="Surface.TFrame")
            stage.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 8, 0))
            sales_stage_bar.columnconfigure(index, weight=1, uniform="sales_stage")
            ttk.Label(stage, text=label, style="Muted.TLabel").pack(anchor=tk.W)
            row = ttk.Frame(stage, style="Surface.TFrame")
            row.pack(fill=tk.X, pady=(3, 0))
            pill = tk.Label(
                row,
                text="CHECK",
                bg="#8a4f00",
                fg="#ffffff",
                font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
                padx=8,
                pady=4,
                width=8,
            )
            pill.pack(side=tk.LEFT)
            value = tk.StringVar(value="確認中")
            self.home_sales_stage_vars[key] = value
            self.home_sales_stage_pills[key] = pill
            ttk.Label(row, textvariable=value, style="Muted.TLabel", wraplength=150).pack(
                side=tk.LEFT,
                fill=tk.X,
                expand=True,
                padx=(6, 0),
            )
        buyer_send_row = ttk.Frame(sales_text, style="Surface.TFrame")
        buyer_send_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(buyer_send_row, text="購入者送付", style="Muted.TLabel").pack(side=tk.LEFT)
        self.home_buyer_send_status_pill = tk.Label(
            buyer_send_row,
            text="CHECK",
            bg="#8a4f00",
            fg="#ffffff",
            font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
            padx=8,
            pady=4,
            width=8,
        )
        self.home_buyer_send_status_pill.pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(
            buyer_send_row,
            textvariable=self.home_buyer_send_button_var,
            command=self.run_home_buyer_send_next_action,
            style="Primary.TButton",
        ).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Label(buyer_send_row, textvariable=self.home_buyer_send_var, style="Surface.TLabel").pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=(8, 0),
        )
        ttk.Label(sales_text, textvariable=self.home_buyer_send_next_var, style="Muted.TLabel", wraplength=820).pack(
            anchor=tk.W,
            fill=tk.X,
            pady=(4, 0),
        )
        ttk.Label(
            sales_text,
            textvariable=self.home_delivery_release_var,
            style="Surface.TLabel",
            wraplength=820,
        ).pack(
            anchor=tk.W,
            fill=tk.X,
            pady=(6, 0),
        )
        ttk.Label(
            sales_text,
            textvariable=self.home_buyer_send_evidence_var,
            style="Muted.TLabel",
            wraplength=820,
        ).pack(
            anchor=tk.W,
            fill=tk.X,
            pady=(3, 0),
        )
        ttk.Label(sales_text, textvariable=self.home_sales_detail_var, style="Muted.TLabel", wraplength=820).pack(
            anchor=tk.W,
            fill=tk.X,
            pady=(8, 0),
        )
        ttk.Label(
            sales_text,
            textvariable=self.home_commercial_focus_var,
            style="Surface.TLabel",
            wraplength=820,
        ).pack(
            anchor=tk.W,
            fill=tk.X,
            pady=(4, 0),
        )
        ttk.Label(sales_text, textvariable=self.home_sales_next_var, style="Muted.TLabel", wraplength=820).pack(
            anchor=tk.W,
            fill=tk.X,
            pady=(3, 0),
        )
        release_check_row = ttk.Frame(sales_text, style="Surface.TFrame")
        release_check_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(release_check_row, text="一括チェック", style="Muted.TLabel").pack(side=tk.LEFT)
        self.home_release_check_status_pill = tk.Label(
            release_check_row,
            text="CHECK",
            bg="#8a4f00",
            fg="#ffffff",
            font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
            padx=8,
            pady=4,
            width=8,
        )
        self.home_release_check_status_pill.pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(
            release_check_row,
            textvariable=self.home_release_check_button_var,
            command=self.run_home_release_check_action,
            style="Primary.TButton",
        ).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Label(
            release_check_row,
            textvariable=self.home_release_check_var,
            style="Surface.TLabel",
            wraplength=640,
        ).pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=(8, 0),
        )
        sales_timeline = ttk.Frame(sales_text, style="Surface.TFrame")
        sales_timeline.pack(fill=tk.X, pady=(10, 0))
        timeline_header = ttk.Frame(sales_timeline, style="Surface.TFrame")
        timeline_header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(timeline_header, text="販売準備タイムライン", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(
            timeline_header,
            textvariable=self.home_sales_timeline_summary_var,
            style="Muted.TLabel",
            wraplength=560,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        self.home_sales_timeline_vars: dict[str, tk.StringVar] = {}
        self.home_sales_timeline_pills: dict[str, tk.Label] = {}
        self.home_sales_timeline_buttons: dict[str, ttk.Button] = {}
        timeline_grid = ttk.Frame(sales_timeline, style="Surface.TFrame")
        timeline_grid.pack(fill=tk.X)
        timeline_items = (
            ("seller", "販売者情報", self.focus_next_commercial_missing_field),
            ("release", "配布ZIP", self.run_preflight_create_release_to_tab),
            ("materials", "販売素材", self.create_sales_materials_action),
            ("screenshots", "掲載画像", self.create_sales_screenshots_action),
            ("listing", "掲載キット", self.create_sales_listing_kit_action),
            ("handoff", "販売一式", self.create_sales_handoff_action),
            ("buyer", "購入者ZIP/送付文", self.run_home_buyer_send_next_action),
            ("send", "送付前照合", self.run_buyer_send_readiness_to_tab),
            ("launch", "販売直前", self.run_sales_launch_to_tab),
            ("full", "一括チェック", self.run_release_check_full_action),
        )
        for index, (key, title, command) in enumerate(timeline_items):
            row_index, column_index = divmod(index, 2)
            timeline_grid.columnconfigure(column_index, weight=1, uniform="sales_timeline")
            item = ttk.Frame(timeline_grid, style="Surface.TFrame")
            item.grid(
                row=row_index,
                column=column_index,
                sticky="ew",
                padx=(0 if column_index == 0 else 10, 0),
                pady=(0 if row_index == 0 else 6, 0),
            )
            pill = tk.Label(
                item,
                text="CHECK",
                bg="#8a4f00",
                fg="#ffffff",
                font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
                padx=8,
                pady=4,
                width=8,
            )
            pill.grid(row=0, column=0, rowspan=2, sticky="nsw")
            ttk.Label(item, text=title, style="Surface.TLabel").grid(
                row=0,
                column=1,
                sticky="w",
                padx=(8, 0),
            )
            value = tk.StringVar(value="確認中")
            self.home_sales_timeline_vars[key] = value
            self.home_sales_timeline_pills[key] = pill
            ttk.Label(item, textvariable=value, style="Muted.TLabel", wraplength=330).grid(
                row=1,
                column=1,
                sticky="ew",
                padx=(8, 0),
            )
            button = ttk.Button(item, text="開く", command=command)
            self.home_sales_timeline_buttons[key] = button
            button.grid(row=0, column=2, rowspan=2, sticky="e", padx=(8, 0))
            item.columnconfigure(1, weight=1)
        sales_actions = ttk.Frame(sales_box, style="Surface.TFrame")
        sales_actions.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))
        sales_action_items = (
            ("次を実行", self.run_home_sales_next_action, "Primary.TButton"),
            (self.home_commercial_focus_button_var, self.run_home_commercial_focus_action, None),
            ("販売ナビ", self.run_sales_plan_to_tab, None),
            ("販売素材", self.create_sales_materials_action, None),
            ("掲載画像", self.create_sales_screenshots_action, None),
            ("掲載キット", self.create_sales_listing_kit_action, None),
            ("送付前チェック", self.run_buyer_send_readiness_to_tab, None),
            ("送付前保存", self.create_buyer_send_readiness_report_action, None),
            ("送付記録", self.create_seller_delivery_receipt_action, None),
            ("送付記録コピー", self.copy_latest_seller_delivery_receipt_action, None),
            ("注文控えコピー", self.copy_latest_seller_order_note_action, None),
            ("問い合わせ票", self.open_latest_buyer_support_request_action, None),
            ("購入者ZIP場所", self.open_latest_buyer_delivery_location_action, None),
            ("送付文コピー", self.copy_latest_buyer_delivery_message_action, None),
            ("ZIPパスコピー", self.copy_latest_buyer_delivery_zip_path_action, None),
            ("送付情報コピー", self.copy_latest_buyer_delivery_sheet_action, None),
            ("最終レビュー", self.run_sales_review_to_tab, None),
            ("レビュー保存", self.create_sales_review_report_action, None),
            ("販売直前", self.run_sales_launch_to_tab, None),
            ("直前保存", self.create_sales_launch_checklist_action, None),
            ("確認記録", self.create_sales_launch_confirmation_action, None),
            ("一括チェック", self.run_release_check_full_action, None),
            (self.home_support_next_button_var, self.run_home_support_next_action, None),
            ("サポート送付", self.show_support_send_panel_action, None),
        )
        for row_index, (text, command, style_name) in enumerate(sales_action_items):
            options = {"command": command}
            if isinstance(text, tk.Variable):
                options["textvariable"] = text
            else:
                options["text"] = text
            if style_name:
                options["style"] = style_name
            button = ttk.Button(sales_actions, **options)
            button.grid(row=row_index, column=0, sticky=tk.EW, pady=(0 if row_index == 0 else 6, 0))
        sales_actions.columnconfigure(0, weight=1)

        action_box = ttk.LabelFrame(home, text="優先アクション", padding=10)
        action_box.pack(fill=tk.X, pady=(0, 10))
        columns = ("severity", "title", "action")
        self.home_action_tree = ttk.Treeview(
            action_box,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=4,
        )
        self.home_action_tree.heading("severity", text="状態")
        self.home_action_tree.heading("title", text="項目")
        self.home_action_tree.heading("action", text="次の操作")
        self.home_action_tree.column("severity", width=72, minwidth=62, stretch=False)
        self.home_action_tree.column("title", width=180, minwidth=140, stretch=False)
        self.home_action_tree.column("action", width=620, minwidth=260)
        self.home_action_tree.pack(fill=tk.X)
        self.home_action_tree.bind("<<TreeviewSelect>>", lambda _event: self.on_select_home_action_step())
        self._configure_home_action_tree_tags()

        self.home_action_var = tk.StringVar(value="")
        ttk.Label(action_box, textvariable=self.home_action_var, style="Muted.TLabel", wraplength=920).pack(
            anchor=tk.W,
            fill=tk.X,
            pady=(6, 0),
        )
        action_buttons = ttk.Frame(action_box, style="Surface.TFrame")
        action_buttons.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(
            action_buttons,
            text="選択を実行",
            style="Primary.TButton",
            command=self.run_selected_home_action_step,
        ).pack(side=tk.LEFT)
        ttk.Button(action_buttons, text="CLIコピー", command=self.copy_selected_home_action_command).pack(
            side=tk.LEFT,
            padx=6,
        )
        ttk.Button(action_buttons, text="詳細", command=self.run_action_plan_to_tab).pack(side=tk.LEFT, padx=6)

        reports_box = ttk.LabelFrame(home, text="直近レポート", padding=10)
        reports_box.pack(fill=tk.X, pady=(0, 10))
        reports_header = ttk.Frame(reports_box, style="Surface.TFrame")
        reports_header.pack(fill=tk.X, pady=(0, 6))
        self.home_reports_var = tk.StringVar(
            value="診断、問い合わせ、復旧、配布、購入者送付の最新ファイルを確認中です。"
        )
        ttk.Label(reports_header, textvariable=self.home_reports_var, style="Muted.TLabel", wraplength=820).pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
        )
        report_actions = ttk.Frame(reports_header, style="Surface.TFrame")
        report_actions.pack(side=tk.RIGHT)
        ttk.Button(
            report_actions,
            text="表示",
            style="Primary.TButton",
            command=self.show_selected_home_report_action,
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(report_actions, text="場所", command=self.open_selected_home_report_location_action).pack(
            side=tk.LEFT,
            padx=(0, 6),
        )
        ttk.Button(report_actions, text="パスコピー", command=self.copy_selected_home_report_path_action).pack(
            side=tk.LEFT,
            padx=(0, 6),
        )
        ttk.Button(report_actions, text="更新", command=self.refresh_home).pack(side=tk.LEFT)

        report_columns = ("kind", "status", "updated", "location", "name")
        self.home_reports_tree = ttk.Treeview(
            reports_box,
            columns=report_columns,
            show="headings",
            selectmode="browse",
            height=5,
        )
        self.home_reports_tree.heading("kind", text="種類")
        self.home_reports_tree.heading("status", text="状態")
        self.home_reports_tree.heading("updated", text="更新")
        self.home_reports_tree.heading("location", text="場所")
        self.home_reports_tree.heading("name", text="ファイル")
        self.home_reports_tree.column("kind", width=110, minwidth=92, stretch=False)
        self.home_reports_tree.column("status", width=72, minwidth=62, stretch=False)
        self.home_reports_tree.column("updated", width=138, minwidth=120, stretch=False)
        self.home_reports_tree.column("location", width=200, minwidth=150, stretch=False)
        self.home_reports_tree.column("name", width=520, minwidth=240)
        self.home_reports_tree.pack(fill=tk.X)
        self._configure_home_reports_tree_tags()
        self.home_reports_tree.bind("<<TreeviewSelect>>", lambda _event: self.on_select_home_report())
        self.home_reports_tree.bind("<Double-1>", lambda _event: self.show_selected_home_report_action())

        quick = ttk.LabelFrame(home, text="次の作業", padding=10)
        quick.pack(fill=tk.X, pady=(0, 10))
        self.home_quick_actions = [
            ("投稿ヘルパーを開く", self.open_helper, "Primary.TButton"),
            ("ログイン安全ガイド", self.show_note_login_safety_action),
            ("投稿キュー", self.publish_queue_to_tab),
            ("運用サマリー", self.run_overview_to_tab),
            ("予定ICS出力", self.export_calendar_action),
            ("初回チェック", self.run_first_run_to_tab),
            ("受入チェック", self.run_acceptance_to_tab),
            ("受入フル保存", self.create_full_acceptance_report_action),
            ("販売ナビ", self.run_sales_plan_to_tab),
            ("販売ナビ保存", self.create_sales_plan_report_action),
            ("販売者情報確認", self.show_commercial_setup_status_action),
            ("販売者テンプレ", self.create_commercial_setup_template_action),
            ("テンプレ適用", self.apply_latest_commercial_setup_template_action),
            ("販売素材作成", self.create_sales_materials_action),
            ("販売素材検証", self.verify_latest_sales_materials_action),
            ("掲載画像作成", self.create_sales_screenshots_action),
            ("掲載画像検証", self.verify_latest_sales_screenshots_action),
            ("掲載キット作成", self.create_sales_listing_kit_action),
            ("掲載キット検証", self.verify_latest_sales_listing_kit_action),
            ("テンプレ取込一括", self.create_sales_finalize_with_template_action),
            ("販売一括作成", self.create_sales_finalize_action),
            ("販売準備", self.run_commercial_readiness_to_tab),
            ("方針レビュー", self.create_commercial_policy_review_action),
            ("販売一式作成", self.create_sales_handoff_action),
            ("購入者ZIP抽出", self.extract_latest_buyer_delivery_action),
            ("購入者ZIP検証", self.verify_latest_buyer_delivery_action),
            ("送付前チェック", self.run_buyer_send_readiness_to_tab),
            ("送付前保存", self.create_buyer_send_readiness_report_action),
            ("送付記録", self.create_seller_delivery_receipt_action),
            ("送付記録コピー", self.copy_latest_seller_delivery_receipt_action),
            ("注文控えコピー", self.copy_latest_seller_order_note_action),
            ("問い合わせ票", self.open_latest_buyer_support_request_action),
            ("購入者ZIP場所", self.open_latest_buyer_delivery_location_action),
            ("送付文コピー", self.copy_latest_buyer_delivery_message_action),
            ("ZIPパスコピー", self.copy_latest_buyer_delivery_zip_path_action),
            ("送付情報コピー", self.copy_latest_buyer_delivery_sheet_action),
            ("最終レビュー", self.run_sales_review_to_tab),
            ("レビュー保存", self.create_sales_review_report_action),
            ("販売直前", self.run_sales_launch_to_tab),
            ("直前保存", self.create_sales_launch_checklist_action),
            ("販売確認記録", self.create_sales_launch_confirmation_action),
            ("販売前一括チェック", self.run_release_check_full_action),
            ("アクションプラン", self.run_action_plan_to_tab),
            ("クイック確認", self.run_quickstart_to_tab),
            ("スターター一式", self.create_starter_pack_action),
            ("スターター整理", self.cleanup_starter_pack_action),
            ("練習記事作成", self.create_practice_article_action),
            ("記事レビュー", self.review_all_to_tab),
            ("準備度確認", self.run_readiness_to_tab),
            ("復旧セット", self.run_recovery_kit_to_tab),
            ("自動修復", self.run_repair_to_tab),
            ("トラブル診断", self.run_troubleshoot_to_tab),
            ("出荷前チェック", self.run_preflight_to_tab),
            ("全体チェック", lambda: self.run_check_all(True)),
            ("公開予定を見る", lambda: self.notebook.select(self.schedule_tab)),
            ("バックアップ作成", self.create_backup_action),
        ]
        quick_filter = ttk.Frame(quick, style="Surface.TFrame")
        quick_filter.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(quick_filter, text="操作検索", style="Muted.TLabel").pack(side=tk.LEFT)
        self.home_quick_filter_var = tk.StringVar()
        self.home_quick_filter_entry = ttk.Entry(quick_filter, textvariable=self.home_quick_filter_var)
        self.home_quick_filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 6))
        ttk.Button(quick_filter, text="解除", command=self.clear_home_quick_filter).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(quick_filter, text="コマンド検索", command=self.show_command_palette).pack(side=tk.LEFT)
        self.home_quick_status_var = tk.StringVar(value="")
        ttk.Label(quick, textvariable=self.home_quick_status_var, style="Muted.TLabel").pack(
            anchor=tk.W,
            fill=tk.X,
            pady=(0, 8),
        )
        self.home_quick_buttons_frame = ttk.Frame(quick, style="Surface.TFrame")
        self.home_quick_buttons_frame.pack(fill=tk.X)
        self.home_quick_filter_var.trace_add("write", lambda *_args: self._render_home_quick_actions())
        self._render_home_quick_actions()

        self.home_text = ScrolledText(home, wrap=tk.WORD, height=8, borderwidth=0)
        _style_text_widget(self.home_text, code=True)
        self.home_text.pack(fill=tk.BOTH, expand=True)
        self.home_text.configure(state=tk.DISABLED)

    def _build_first_run_tab(self) -> None:
        top = ttk.Frame(self.first_run_tab)
        top.pack(fill=tk.X, pady=(0, 10))
        title_group = ttk.Frame(top)
        title_group.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(title_group, text="初回チェック", style="PageTitle.TLabel").pack(anchor=tk.W)
        ttk.Label(
            title_group,
            text="初回起動、販売前チェック、サポート提出物をまとめて確認します。",
            style="PageSubtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))
        ttk.Button(top, text="再チェック", style="Primary.TButton", command=self.run_first_run_to_tab).pack(
            side=tk.RIGHT
        )
        self.first_run_action_filter_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            top,
            text="要対応だけ",
            variable=self.first_run_action_filter_var,
            command=self.toggle_first_run_action_filter,
        ).pack(side=tk.RIGHT, padx=6)
        ttk.Button(top, text="診断テキスト", command=self.show_first_run_text).pack(side=tk.RIGHT, padx=6)
        ttk.Button(top, text="受入チェック", command=self.run_acceptance_to_tab).pack(side=tk.RIGHT, padx=6)
        ttk.Button(top, text="受入保存", command=self.create_acceptance_report_action).pack(side=tk.RIGHT, padx=6)
        ttk.Button(top, text="受入フル保存", command=self.create_full_acceptance_report_action).pack(
            side=tk.RIGHT,
            padx=6,
        )
        ttk.Button(top, text="販売ナビ", command=self.run_sales_plan_to_tab).pack(side=tk.RIGHT, padx=6)
        ttk.Button(top, text="販売ナビ保存", command=self.create_sales_plan_report_action).pack(side=tk.RIGHT, padx=6)
        ttk.Button(top, text="販売者情報確認", command=self.show_commercial_setup_status_action).pack(
            side=tk.RIGHT,
            padx=6,
        )
        ttk.Button(top, text="販売者テンプレ", command=self.create_commercial_setup_template_action).pack(
            side=tk.RIGHT,
            padx=6,
        )
        ttk.Button(top, text="テンプレ適用", command=self.apply_latest_commercial_setup_template_action).pack(
            side=tk.RIGHT,
            padx=6,
        )
        ttk.Button(top, text="販売素材作成", command=self.create_sales_materials_action).pack(side=tk.RIGHT, padx=6)
        ttk.Button(top, text="販売素材検証", command=self.verify_latest_sales_materials_action).pack(
            side=tk.RIGHT,
            padx=6,
        )
        ttk.Button(top, text="掲載画像作成", command=self.create_sales_screenshots_action).pack(
            side=tk.RIGHT,
            padx=6,
        )
        ttk.Button(top, text="掲載画像検証", command=self.verify_latest_sales_screenshots_action).pack(
            side=tk.RIGHT,
            padx=6,
        )
        ttk.Button(top, text="掲載キット作成", command=self.create_sales_listing_kit_action).pack(side=tk.RIGHT, padx=6)
        ttk.Button(top, text="掲載キット検証", command=self.verify_latest_sales_listing_kit_action).pack(
            side=tk.RIGHT,
            padx=6,
        )
        ttk.Button(top, text="テンプレ取込一括", command=self.create_sales_finalize_with_template_action).pack(
            side=tk.RIGHT,
            padx=6,
        )
        ttk.Button(top, text="販売一括作成", command=self.create_sales_finalize_action).pack(side=tk.RIGHT, padx=6)
        ttk.Button(top, text="販売準備", command=self.run_commercial_readiness_to_tab).pack(side=tk.RIGHT, padx=6)
        ttk.Button(top, text="方針レビュー", command=self.create_commercial_policy_review_action).pack(
            side=tk.RIGHT,
            padx=6,
        )
        ttk.Button(top, text="販売準備保存", command=self.create_commercial_readiness_report_action).pack(
            side=tk.RIGHT,
            padx=6,
        )
        ttk.Button(top, text="セルフテスト保存", command=self.create_self_test_report_action).pack(
            side=tk.RIGHT, padx=6
        )
        ttk.Button(top, text="問い合わせ一式", command=self.create_support_bundle_action).pack(
            side=tk.RIGHT, padx=6
        )
        ttk.Button(top, text="スターター一式", command=self.create_starter_pack_action).pack(
            side=tk.RIGHT, padx=6
        )

        summary = ttk.Frame(self.first_run_tab, style="Surface.TFrame", padding=14)
        summary.pack(fill=tk.X, pady=(0, 10))
        left = ttk.Frame(summary, style="Surface.TFrame")
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(left, text="販売前の準備状態", style="Muted.TLabel").pack(anchor=tk.W)
        title_row = ttk.Frame(left, style="Surface.TFrame")
        title_row.pack(fill=tk.X, pady=(4, 0))
        self.first_run_status_pill = tk.Label(
            title_row,
            text="CHECK",
            bg="#8a4f00",
            fg="#ffffff",
            font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
            padx=12,
            pady=5,
            width=10,
        )
        self.first_run_status_pill.pack(side=tk.LEFT)
        self.first_run_score_var = tk.StringVar(value="0/100")
        ttk.Label(title_row, textvariable=self.first_run_score_var, style="Title.TLabel").pack(
            side=tk.LEFT,
            padx=(12, 0),
        )
        self.first_run_summary_var = tk.StringVar(value="初回チェックを実行中です。")
        ttk.Label(left, textvariable=self.first_run_summary_var, style="Surface.TLabel", wraplength=760).pack(
            anchor=tk.W,
            pady=(8, 0),
        )

        counts = ttk.Frame(summary, style="Surface.TFrame")
        counts.pack(side=tk.RIGHT, padx=(12, 0))
        self.first_run_count_vars: dict[str, tk.StringVar] = {}
        for index, key in enumerate(("OK", "INFO", "WARN", "NG")):
            value = tk.StringVar(value="0")
            self.first_run_count_vars[key] = value
            box = ttk.Frame(counts, style="Surface.TFrame", padding=(10, 4))
            box.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 6, 0))
            ttk.Label(box, text=key, style="KpiLabel.TLabel").pack(anchor=tk.CENTER)
            ttk.Label(box, textvariable=value, style="KpiValue.TLabel").pack(anchor=tk.CENTER)

        main = ttk.PanedWindow(self.first_run_tab, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True)

        list_panel = ttk.Frame(main, style="Surface.TFrame", padding=10)
        detail_panel = ttk.Frame(main, style="Surface.TFrame", padding=10)
        main.add(list_panel, weight=3)
        main.add(detail_panel, weight=2)

        ttk.Label(list_panel, text="確認項目", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 8))
        columns = ("status", "name", "detail", "action")
        self.first_run_tree = ttk.Treeview(list_panel, columns=columns, show="headings", selectmode="browse", height=10)
        self.first_run_tree.heading("status", text="状態")
        self.first_run_tree.heading("name", text="項目")
        self.first_run_tree.heading("detail", text="現在")
        self.first_run_tree.heading("action", text="次の操作")
        self.first_run_tree.column("status", width=70, minwidth=62, stretch=False)
        self.first_run_tree.column("name", width=130, minwidth=110, stretch=False)
        self.first_run_tree.column("detail", width=220, minwidth=150)
        self.first_run_tree.column("action", width=300, minwidth=180)
        self.first_run_tree.pack(fill=tk.BOTH, expand=True)
        self.first_run_tree.bind("<<TreeviewSelect>>", lambda _event: self.on_select_first_run_item())
        self._configure_first_run_tree_tags()

        ttk.Label(detail_panel, text="選択項目", style="Title.TLabel").pack(anchor=tk.W)
        self.first_run_detail_name_var = tk.StringVar(value="項目を選択してください")
        self.first_run_detail_status_var = tk.StringVar(value="")
        self.first_run_detail_text_var = tk.StringVar(value="")
        self.first_run_detail_gui_var = tk.StringVar(value="")
        self.first_run_detail_cli_var = tk.StringVar(value="")
        ttk.Label(
            detail_panel,
            textvariable=self.first_run_detail_name_var,
            style="Surface.TLabel",
            font=(UI_FONT, 12, UI_HEADING_FONT_WEIGHT),
        ).pack(
            anchor=tk.W,
            pady=(10, 0),
        )
        ttk.Label(detail_panel, textvariable=self.first_run_detail_status_var, style="Muted.TLabel").pack(
            anchor=tk.W,
            pady=(2, 8),
        )
        ttk.Label(detail_panel, textvariable=self.first_run_detail_text_var, style="Surface.TLabel", wraplength=380).pack(
            anchor=tk.W,
            fill=tk.X,
        )
        ttk.Label(detail_panel, textvariable=self.first_run_detail_gui_var, style="Muted.TLabel", wraplength=380).pack(
            anchor=tk.W,
            pady=(10, 0),
            fill=tk.X,
        )
        ttk.Label(detail_panel, textvariable=self.first_run_detail_cli_var, style="Muted.TLabel", wraplength=380).pack(
            anchor=tk.W,
            pady=(4, 0),
            fill=tk.X,
        )

        buttons = ttk.Frame(detail_panel, style="Surface.TFrame")
        buttons.pack(fill=tk.X, pady=(14, 0))
        ttk.Button(buttons, text="この項目を実行", style="Primary.TButton", command=self.run_selected_first_run_action).pack(
            fill=tk.X,
            pady=(0, 6),
        )
        ttk.Button(buttons, text="CLIをコピー", command=self.copy_selected_first_run_cli).pack(fill=tk.X, pady=(0, 6))
        ttk.Button(buttons, text="診断テキストで見る", command=self.show_first_run_text).pack(fill=tk.X)

    def _build_article_tab(self) -> None:
        pane = ttk.PanedWindow(self.article_tab, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True)

        list_panel = ttk.Frame(pane, style="Surface.TFrame", padding=10)
        detail_panel = ttk.Frame(pane, style="Surface.TFrame", padding=10)
        pane.add(list_panel, weight=3)
        pane.add(detail_panel, weight=2)

        list_header = ttk.Frame(list_panel, style="Surface.TFrame")
        list_header.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(list_header, text="記事一覧", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Button(list_header, text="ダッシュボード", command=self.open_dashboard).pack(side=tk.RIGHT)
        ttk.Button(list_header, text="CSV出力", command=self.export_inventory_action).pack(side=tk.RIGHT, padx=6)

        filters = ttk.Frame(list_panel, style="Surface.TFrame")
        filters.pack(fill=tk.X, pady=(0, 8))
        self.article_filter_var = tk.StringVar()
        self.status_filter_var = tk.StringVar(value="all")
        ttk.Entry(filters, textvariable=self.article_filter_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Combobox(
            filters,
            textvariable=self.status_filter_var,
            values=("all", *STATUS_ORDER),
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(filters, text="絞り込み解除", command=self.clear_article_filters).pack(side=tk.LEFT, padx=6)
        self.article_filter_var.trace_add("write", lambda *_args: self.refresh_articles())
        self.status_filter_var.trace_add("write", lambda *_args: self.refresh_articles())

        columns = ("status", "issues", "title", "scheduled", "chars", "tags")
        self.article_tree = ttk.Treeview(list_panel, columns=columns, show="headings", selectmode="browse")
        self.article_tree.heading("status", text="状態")
        self.article_tree.heading("issues", text="確認")
        self.article_tree.heading("title", text="タイトル")
        self.article_tree.heading("scheduled", text="公開予定")
        self.article_tree.heading("chars", text="文字")
        self.article_tree.heading("tags", text="タグ")
        self.article_tree.column("status", width=86, minwidth=78, stretch=False)
        self.article_tree.column("issues", width=82, minwidth=72, stretch=False)
        self.article_tree.column("title", width=260, minwidth=160)
        self.article_tree.column("scheduled", width=132, minwidth=116, stretch=False)
        self.article_tree.column("chars", width=70, minwidth=64, stretch=False, anchor=tk.E)
        self.article_tree.column("tags", width=180, minwidth=120)
        self.article_tree.pack(fill=tk.BOTH, expand=True)
        self.article_tree.bind("<<TreeviewSelect>>", lambda _event: self.on_select_article())
        self._configure_article_tree_tags()

        table_buttons = ttk.Frame(list_panel, style="Surface.TFrame")
        table_buttons.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(table_buttons, text="ファイルを開く", command=self.open_selected_file).pack(side=tk.LEFT)
        ttk.Button(table_buttons, text="投稿ヘルパー", style="Primary.TButton", command=self.open_helper).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(table_buttons, text="本文コピー", command=lambda: self.copy_selected("body")).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(table_buttons, text="投稿キュー", command=self.publish_queue_to_tab).pack(side=tk.LEFT, padx=6)

        self.title_var = tk.StringVar(value="記事を選択してください")
        self.meta_var = tk.StringVar(value="")
        detail_header = ttk.Frame(detail_panel, style="Surface.TFrame")
        detail_header.pack(fill=tk.X)
        ttk.Label(detail_header, textvariable=self.title_var, style="Title.TLabel").pack(side=tk.LEFT, fill=tk.X)
        self.status_pill = tk.Label(
            detail_header,
            text="draft",
            bg=STATUS_COLORS["draft"][0],
            fg=STATUS_COLORS["draft"][1],
            padx=10,
            pady=4,
        )
        self.status_pill.pack(side=tk.RIGHT)
        ttk.Label(detail_panel, textvariable=self.meta_var, style="Muted.TLabel").pack(anchor=tk.W, pady=(6, 10))
        self._build_article_focus_panel(detail_panel)

        action_grid = ttk.Frame(detail_panel, style="Surface.TFrame")
        action_grid.pack(fill=tk.X, pady=(0, 8))
        self._build_post_actions(action_grid)
        self._build_check_actions(action_grid)
        self._build_copy_actions(action_grid)
        self._build_workflow_actions(detail_panel)
        self._build_publish_ready_panel(detail_panel)

        self.article_content_tabs = ttk.Notebook(detail_panel)
        content_tabs = self.article_content_tabs
        content_tabs.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.article_preview_tab = ttk.Frame(content_tabs, style="Surface.TFrame", padding=6)
        self.article_editor_tab = ttk.Frame(content_tabs, style="Surface.TFrame", padding=6)
        preview_tab = self.article_preview_tab
        editor_tab = self.article_editor_tab
        content_tabs.add(preview_tab, text="プレビュー")
        content_tabs.add(editor_tab, text="編集")

        self.preview = ScrolledText(preview_tab, wrap=tk.WORD, height=18, borderwidth=0)
        _style_text_widget(self.preview)
        self.preview.pack(fill=tk.BOTH, expand=True)
        self.preview.configure(state=tk.DISABLED)

        editor_toolbar = ttk.Frame(editor_tab, style="Surface.TFrame")
        editor_toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(editor_toolbar, text="保存", style="Primary.TButton", command=self.save_editor).pack(side=tk.LEFT)
        ttk.Button(editor_toolbar, text="メタ編集", command=self.edit_article_metadata).pack(side=tk.LEFT, padx=6)
        ttk.Button(editor_toolbar, text="再読込", command=self.reload_editor).pack(side=tk.LEFT, padx=6)
        ttk.Button(editor_toolbar, text="保存履歴", command=self.show_selected_history).pack(side=tk.LEFT, padx=6)
        ttk.Button(editor_toolbar, text="履歴復元", command=self.restore_selected_history).pack(side=tk.LEFT, padx=6)
        ttk.Button(editor_toolbar, text="履歴フォルダ", command=self.open_selected_history_folder).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(editor_toolbar, text="画像挿入", command=self.insert_image_into_editor).pack(side=tk.LEFT, padx=6)
        ttk.Button(editor_toolbar, text="自動退避", command=self.show_autosave_dialog).pack(side=tk.LEFT, padx=6)
        ttk.Button(editor_toolbar, text="外部で開く", command=self.open_selected_file).pack(side=tk.LEFT, padx=6)
        self.editor = ScrolledText(editor_tab, wrap=tk.WORD, height=18, borderwidth=0, undo=True)
        _style_text_widget(self.editor)
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.editor.bind("<<Modified>>", self.on_editor_modified)

    def _build_article_focus_panel(self, parent: ttk.Frame) -> None:
        box = ttk.Frame(parent, style="ArticleFocus.TFrame", padding=(10, 9))
        box.pack(fill=tk.X, pady=(0, 8))

        self.article_focus_rail = tk.Frame(box, bg=UI_COLORS["line"], width=4)
        self.article_focus_rail.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        body = ttk.Frame(box, style="ArticleFocus.TFrame")
        body.pack(side=tk.LEFT, fill=tk.X, expand=True)
        head = ttk.Frame(body, style="ArticleFocus.TFrame")
        head.pack(fill=tk.X)
        ttk.Label(head, text="選択記事フォーカス", style="ArticleFocusTitle.TLabel").pack(side=tk.LEFT)
        self.article_focus_status_pill = tk.Label(
            head,
            text="未選択",
            bg="#344054",
            fg="#ffffff",
            font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
            padx=9,
            pady=4,
            width=9,
        )
        self.article_focus_status_pill.pack(side=tk.RIGHT)

        self.article_focus_summary_var = tk.StringVar(value="記事を選択すると仕上げ状態を確認できます。")
        ttk.Label(
            body,
            textvariable=self.article_focus_summary_var,
            style="ArticleFocusValue.TLabel",
            wraplength=500,
        ).pack(anchor=tk.W, fill=tk.X, pady=(5, 0))

        self.article_focus_next_var = tk.StringVar(value="次: 記事一覧から対象を選択してください。")
        ttk.Label(
            body,
            textvariable=self.article_focus_next_var,
            style="ArticleFocusMuted.TLabel",
            wraplength=500,
        ).pack(anchor=tk.W, fill=tk.X, pady=(3, 0))

        actions = ttk.Frame(body, style="ArticleFocus.TFrame")
        actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(actions, text="次を確認", style="Primary.TButton", command=self.run_article_focus_next_action).pack(
            side=tk.LEFT
        )
        ttk.Button(actions, text="投稿準備", command=self.publish_ready_selected_to_tab).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="HTML確認", command=self.generate_publish_ready_helper_action).pack(side=tk.LEFT)

    def _configure_article_tree_tags(self) -> None:
        for status, (bg, fg) in STATUS_COLORS.items():
            self.article_tree.tag_configure(status, background=bg, foreground=fg)
        self.article_tree.tag_configure("error", background="#ffe2df", foreground="#8b2119")

    def _build_post_actions(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="投稿")
        box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Button(box, text="投稿ヘルパー", style="Primary.TButton", command=self.open_helper).pack(
            fill=tk.X, pady=(0, 6)
        )
        ttk.Button(box, text="投稿準備", command=self.publish_ready_selected_to_tab).pack(fill=tk.X, pady=(0, 6))
        ttk.Button(box, text="改善プラン", command=self.improvement_plan_selected_to_tab).pack(
            fill=tk.X, pady=(0, 6)
        )
        ttk.Button(box, text="noteログイン", command=self.open_note_login_action).pack(fill=tk.X)

    def _build_check_actions(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="確認")
        box.grid(row=0, column=1, sticky="nsew", padx=8)
        ttk.Button(box, text="選択記事チェック", command=self.check_selected).pack(fill=tk.X, pady=(0, 6))
        ttk.Button(box, text="改善プラン", command=self.improvement_plan_selected_to_tab).pack(fill=tk.X, pady=(0, 6))
        ttk.Button(box, text="全体チェック", command=lambda: self.run_check_all(show_popup=True)).pack(
            fill=tk.X, pady=(0, 6)
        )
        ttk.Button(box, text="投稿キュー", command=self.publish_queue_to_tab).pack(fill=tk.X, pady=(0, 6))
        ttk.Button(box, text="画像チェック", command=self.check_images_selected).pack(fill=tk.X)

    def _build_copy_actions(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="コピー")
        box.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        ttk.Button(box, text="本文", command=lambda: self.copy_selected("body")).pack(fill=tk.X, pady=(0, 6))
        ttk.Button(box, text="全文", command=lambda: self.copy_selected("all")).pack(fill=tk.X, pady=(0, 6))
        ttk.Button(box, text="タグ", command=lambda: self.copy_selected("tags")).pack(fill=tk.X)
        for index in range(3):
            parent.columnconfigure(index, weight=1)

    def _build_workflow_actions(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="工程管理")
        box.pack(fill=tk.X, pady=(0, 8))

        row1 = ttk.Frame(box, style="Surface.TFrame")
        row1.pack(fill=tk.X)
        ttk.Label(row1, text="状態", style="Surface.TLabel").pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="draft")
        self.status_combo = ttk.Combobox(
            row1,
            textvariable=self.status_var,
            values=STATUS_ORDER,
            width=14,
            state="readonly",
        )
        self.status_combo.pack(side=tk.LEFT, padx=6)
        ttk.Button(row1, text="保存", command=self.save_status).pack(side=tk.LEFT)

        ttk.Label(row1, text="公開予定", style="Surface.TLabel").pack(side=tk.LEFT, padx=(18, 0))
        self.schedule_var = tk.StringVar()
        self.schedule_entry = ttk.Entry(row1, textvariable=self.schedule_var, width=22)
        self.schedule_entry.pack(side=tk.LEFT, padx=6)
        ttk.Button(row1, text="予定保存", command=self.save_schedule).pack(side=tk.LEFT)
        ttk.Button(row1, text="予定削除", command=self.clear_schedule).pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(box, style="Surface.TFrame")
        row2.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(row2, text="公開URL", style="Surface.TLabel").pack(side=tk.LEFT)
        self.url_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.url_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(row2, text="公開済みにする", command=self.mark_published).pack(side=tk.LEFT)

    def _build_publish_ready_panel(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="投稿準備", padding=8)
        box.pack(fill=tk.X, pady=(0, 8))

        top = ttk.Frame(box, style="Surface.TFrame")
        top.pack(fill=tk.X, pady=(0, 6))
        self.publish_ready_status_pill = tk.Label(
            top,
            text="未選択",
            bg="#344054",
            fg="#ffffff",
            padx=10,
            pady=4,
        )
        self.publish_ready_status_pill.pack(side=tk.LEFT)
        self.publish_ready_summary_var = tk.StringVar(value="記事を選択すると投稿準備を確認できます。")
        ttk.Label(top, textvariable=self.publish_ready_summary_var, style="Surface.TLabel", wraplength=420).pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=(10, 0),
        )

        columns = ("status", "name", "detail")
        self.publish_ready_tree = ttk.Treeview(box, columns=columns, show="headings", selectmode="browse", height=5)
        self.publish_ready_tree.heading("status", text="状態")
        self.publish_ready_tree.heading("name", text="項目")
        self.publish_ready_tree.heading("detail", text="内容")
        self.publish_ready_tree.column("status", width=62, minwidth=56, stretch=False)
        self.publish_ready_tree.column("name", width=116, minwidth=92, stretch=False)
        self.publish_ready_tree.column("detail", width=280, minwidth=160)
        self.publish_ready_tree.pack(fill=tk.X)
        self.publish_ready_tree.bind("<<TreeviewSelect>>", lambda _event: self.on_select_publish_ready_item())
        self._configure_publish_ready_tree_tags()

        self.publish_ready_action_var = tk.StringVar(value="")
        ttk.Label(box, textvariable=self.publish_ready_action_var, style="Muted.TLabel", wraplength=460).pack(
            anchor=tk.W,
            fill=tk.X,
            pady=(6, 0),
        )

        buttons = ttk.Frame(box, style="Surface.TFrame")
        buttons.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(buttons, text="更新", command=self.refresh_publish_ready_panel_action).pack(side=tk.LEFT)
        ttk.Button(buttons, text="次を実行", command=self.run_selected_publish_ready_action).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="詳細", command=self.publish_ready_selected_to_tab).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="改善プラン", command=self.improvement_plan_selected_to_tab).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="準備OK", command=self.mark_selected_publish_ready).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="HTML確認", command=self.generate_publish_ready_helper_action).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="投稿ヘルパー", style="Primary.TButton", command=self.open_helper).pack(side=tk.RIGHT)

    def _build_ideas_tab(self) -> None:
        top = ttk.Frame(self.ideas_tab)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(top, text="アイデア箱", font=(UI_FONT, 16, UI_HEADING_FONT_WEIGHT)).pack(side=tk.LEFT)
        ttk.Button(top, text="追加", style="Primary.TButton", command=self.add_idea_dialog).pack(
            side=tk.RIGHT, padx=(6, 0)
        )
        ttk.Button(top, text="記事にする", command=self.promote_selected_idea).pack(side=tk.RIGHT, padx=6)
        ttk.Button(top, text="更新", command=self.refresh_ideas).pack(side=tk.RIGHT, padx=6)

        columns = ("id", "state", "title", "tags", "note")
        self.ideas_tree = ttk.Treeview(self.ideas_tab, columns=columns, show="headings", selectmode="browse")
        for column, text, width in (
            ("id", "ID", 54),
            ("state", "状態", 78),
            ("title", "タイトル", 260),
            ("tags", "タグ", 180),
            ("note", "メモ", 360),
        ):
            self.ideas_tree.heading(column, text=text)
            self.ideas_tree.column(column, width=width, minwidth=50, stretch=column in {"title", "note"})
        self.ideas_tree.pack(fill=tk.BOTH, expand=True)
        self.ideas_tree.tag_configure("open", background="#ffffff", foreground="#16181d")
        self.ideas_tree.tag_configure("done", background="#f3f4f6", foreground="#667085")

        bottom = ttk.Frame(self.ideas_tab)
        bottom.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(bottom, text="一覧テキスト表示", command=self.show_ideas_text).pack(side=tk.LEFT)

    def _build_schedule_tab(self) -> None:
        top = ttk.Frame(self.schedule_tab)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(top, text="工程と公開予定", font=(UI_FONT, 16, UI_HEADING_FONT_WEIGHT)).pack(side=tk.LEFT)
        ttk.Button(top, text="更新", command=self.refresh_schedule).pack(side=tk.RIGHT)
        ttk.Button(top, text="ICS出力", command=self.export_calendar_action).pack(side=tk.RIGHT, padx=6)
        ttk.Button(top, text="選択記事を予定にする", command=self.save_schedule).pack(side=tk.RIGHT, padx=6)
        ttk.Button(top, text="選択記事を公開済みにする", command=self.mark_published).pack(side=tk.RIGHT, padx=6)

        self.schedule_text = ScrolledText(self.schedule_tab, wrap=tk.WORD, borderwidth=0)
        _style_text_widget(self.schedule_text, code=True)
        self.schedule_text.pack(fill=tk.BOTH, expand=True)
        self.schedule_text.configure(state=tk.DISABLED)

    def _build_check_tab(self) -> None:
        top = ttk.Frame(self.check_tab)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(top, text="公開前チェック", font=(UI_FONT, 16, UI_HEADING_FONT_WEIGHT)).pack(side=tk.LEFT)

        actions = ttk.Frame(self.check_tab)
        actions.pack(fill=tk.X, pady=(0, 8))
        self._build_button_bar(
            actions,
            [
                ("全体チェック", lambda: self.run_check_all(True), "Primary.TButton"),
                ("アクションプラン", self.run_action_plan_to_check_tab),
                ("選択記事チェック", self.check_selected_to_tab),
                ("改善プラン", self.improvement_plan_selected_to_tab),
                ("選択投稿準備", self.publish_ready_selected_to_tab),
                ("レビュー更新", self.refresh_review_panel_action),
                ("選択レビュー", self.review_selected_from_review_panel),
                ("画像チェック", self.check_images_all),
                ("クリア", lambda: self._set_check_text("")),
            ],
            columns=3,
        )

        body = ttk.PanedWindow(self.check_tab, orient=tk.VERTICAL)
        body.pack(fill=tk.BOTH, expand=True)

        review_panel = ttk.Frame(body, style="Surface.TFrame", padding=10)
        text_panel = ttk.Frame(body, style="Surface.TFrame", padding=8)
        body.add(review_panel, weight=3)
        body.add(text_panel, weight=2)

        self._build_review_panel(review_panel)

        self.check_text = ScrolledText(text_panel, wrap=tk.WORD, borderwidth=0, height=8)
        _style_text_widget(self.check_text, code=True)
        self.check_text.pack(fill=tk.BOTH, expand=True)
        self.check_text.configure(state=tk.DISABLED)

    def _build_review_panel(self, parent: ttk.Frame) -> None:
        summary = ttk.Frame(parent, style="Surface.TFrame")
        summary.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(summary, text="記事レビュー", style="Title.TLabel").pack(side=tk.LEFT)
        self.review_summary_var = tk.StringVar(value="レビューを実行中です。")
        ttk.Label(summary, textvariable=self.review_summary_var, style="Muted.TLabel").pack(
            side=tk.LEFT,
            padx=(12, 0),
        )
        ttk.Button(summary, text="投稿準備", command=self.publish_ready_selected_review_to_tab).pack(side=tk.RIGHT)
        ttk.Button(summary, text="改善プラン", command=self.improvement_plan_selected_review_to_tab).pack(
            side=tk.RIGHT,
            padx=6,
        )
        ttk.Button(summary, text="記事を編集", command=self.open_selected_review_article_editor).pack(
            side=tk.RIGHT, padx=6
        )
        ttk.Button(summary, text="準備OKにする", command=self.mark_selected_review_ready).pack(side=tk.RIGHT, padx=6)

        pane = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True)

        list_panel = ttk.Frame(pane, style="Surface.TFrame")
        detail_panel = ttk.Frame(pane, style="Surface.TFrame")
        pane.add(list_panel, weight=3)
        pane.add(detail_panel, weight=2)

        columns = ("score", "state", "fix", "improve", "status", "title")
        self.review_tree = ttk.Treeview(list_panel, columns=columns, show="headings", selectmode="browse", height=7)
        self.review_tree.heading("score", text="点")
        self.review_tree.heading("state", text="状態")
        self.review_tree.heading("fix", text="修正")
        self.review_tree.heading("improve", text="改善")
        self.review_tree.heading("status", text="工程")
        self.review_tree.heading("title", text="タイトル")
        self.review_tree.column("score", width=52, minwidth=48, stretch=False, anchor=tk.E)
        self.review_tree.column("state", width=96, minwidth=86, stretch=False)
        self.review_tree.column("fix", width=56, minwidth=50, stretch=False, anchor=tk.E)
        self.review_tree.column("improve", width=56, minwidth=50, stretch=False, anchor=tk.E)
        self.review_tree.column("status", width=86, minwidth=74, stretch=False)
        self.review_tree.column("title", width=300, minwidth=180)
        self.review_tree.pack(fill=tk.BOTH, expand=True)
        self.review_tree.bind("<<TreeviewSelect>>", lambda _event: self.on_select_review_item())
        self._configure_review_tree_tags()

        self.review_detail_title_var = tk.StringVar(value="記事を選択してください")
        self.review_detail_status_var = tk.StringVar(value="")
        ttk.Label(
            detail_panel,
            textvariable=self.review_detail_title_var,
            style="Surface.TLabel",
            font=(UI_FONT, 12, UI_HEADING_FONT_WEIGHT),
        ).pack(
            anchor=tk.W,
            pady=(0, 2),
        )
        ttk.Label(detail_panel, textvariable=self.review_detail_status_var, style="Muted.TLabel").pack(anchor=tk.W, pady=(0, 8))

        detail_columns = ("level", "category", "message")
        self.review_detail_tree = ttk.Treeview(
            detail_panel,
            columns=detail_columns,
            show="headings",
            selectmode="browse",
            height=7,
        )
        self.review_detail_tree.heading("level", text="種別")
        self.review_detail_tree.heading("category", text="項目")
        self.review_detail_tree.heading("message", text="内容")
        self.review_detail_tree.column("level", width=74, minwidth=66, stretch=False)
        self.review_detail_tree.column("category", width=86, minwidth=74, stretch=False)
        self.review_detail_tree.column("message", width=300, minwidth=180)
        self.review_detail_tree.pack(fill=tk.BOTH, expand=True)
        self.review_detail_tree.bind("<<TreeviewSelect>>", lambda _event: self.on_select_review_detail())
        self._configure_review_detail_tags()

        self.review_action_var = tk.StringVar(value="")
        ttk.Label(detail_panel, textvariable=self.review_action_var, style="Muted.TLabel", wraplength=420).pack(
            anchor=tk.W,
            fill=tk.X,
            pady=(8, 0),
        )
        detail_actions = ttk.Frame(detail_panel, style="Surface.TFrame")
        detail_actions.pack(fill=tk.X, pady=(8, 0))
        self.review_detail_buttons = [
            ttk.Button(
                detail_actions,
                text="本文を編集",
                style="Primary.TButton",
                command=self.open_selected_review_article_editor,
            ),
            ttk.Button(detail_actions, text="改善プラン", command=self.improvement_plan_selected_review_to_tab),
            ttk.Button(detail_actions, text="投稿準備", command=self.publish_ready_selected_review_to_tab),
        ]
        for index, button in enumerate(self.review_detail_buttons):
            button.pack(side=tk.LEFT, padx=(0 if index == 0 else 6, 0))

    def _build_settings_tab(self) -> None:
        top = ttk.Frame(self.settings_tab)
        top.pack(fill=tk.X, pady=(0, 10))
        title_group = ttk.Frame(top)
        title_group.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(title_group, text="設定", style="PageTitle.TLabel").pack(anchor=tk.W)
        ttk.Label(
            title_group,
            text="投稿補助、表示サイズ、販売者情報、画像最適化の既定値を管理します。",
            style="PageSubtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))
        ttk.Button(top, text="保存", style="Primary.TButton", command=self.save_app_settings).pack(side=tk.RIGHT)

        form = ttk.Frame(self.settings_tab, style="Surface.TFrame", padding=14)
        form.pack(fill=tk.X)

        self.default_tags_var = tk.StringVar(value=", ".join(self.settings.default_tags))
        self.default_status_var = tk.StringVar(value=self.settings.default_status)
        self.append_tags_var = tk.BooleanVar(value=self.settings.append_tags_by_default)
        self.open_note_var = tk.BooleanVar(value=self.settings.open_note_with_helper)
        self.article_glob_var = tk.StringVar(value=self.settings.article_glob)
        self.ui_density_var = tk.StringVar(value=_ui_density_label(self.settings.ui_density))
        self.support_contact_var = tk.StringVar(value=self.settings.support_contact)
        self.seller_name_var = tk.StringVar(value=self.settings.seller_name)
        self.sales_channel_url_var = tk.StringVar(value=self.settings.sales_channel_url)
        self.refund_policy_url_var = tk.StringVar(value=self.settings.refund_policy_url)
        self.commercial_terms_reviewed_var = tk.BooleanVar(value=self.settings.commercial_terms_reviewed)
        self.commercial_support_scope_var = tk.BooleanVar(value=self.settings.commercial_support_scope_confirmed)
        self.commercial_progress_var = tk.StringVar()
        self.commercial_next_var = tk.StringVar()
        self.commercial_setup_action_var = tk.StringVar(value="")
        self.image_optimize_var = tk.BooleanVar(value=self.settings.image_optimize_by_default)
        self.image_max_width_var = tk.IntVar(value=self.settings.image_max_width)
        self.image_quality_var = tk.IntVar(value=self.settings.image_quality)

        self._form_row(form, 0, "既定タグ", ttk.Entry(form, textvariable=self.default_tags_var))
        self._form_row(
            form,
            1,
            "新規記事の状態",
            ttk.Combobox(
                form,
                textvariable=self.default_status_var,
                values=STATUS_ORDER,
                state="readonly",
                width=18,
            ),
        )
        self._form_row(form, 2, "記事検索パターン", ttk.Entry(form, textvariable=self.article_glob_var))
        self.ui_density_combo = ttk.Combobox(
            form,
            textvariable=self.ui_density_var,
            values=tuple(UI_DENSITY_LABELS.values()),
            state="readonly",
            width=14,
        )
        self._form_row(
            form,
            3,
            "表示サイズ",
            self.ui_density_combo,
        )
        self.support_contact_entry = ttk.Entry(form, textvariable=self.support_contact_var)
        self.seller_name_entry = ttk.Entry(form, textvariable=self.seller_name_var)
        self.sales_channel_url_entry = ttk.Entry(form, textvariable=self.sales_channel_url_var)
        self.refund_policy_url_entry = ttk.Entry(form, textvariable=self.refund_policy_url_var)
        self._form_row(form, 4, "サポート連絡先", self.support_contact_entry)
        self._form_row(form, 5, "販売者/屋号", self.seller_name_entry)
        self._form_row(form, 6, "販売ページURL", self.sales_channel_url_entry)
        self._form_row(form, 7, "返金方針URL", self.refund_policy_url_entry)
        self._form_row(
            form,
            8,
            "画像最大幅",
            ttk.Spinbox(form, textvariable=self.image_max_width_var, from_=320, to=4000, increment=100, width=10),
        )
        self._form_row(
            form,
            9,
            "画像品質",
            ttk.Spinbox(form, textvariable=self.image_quality_var, from_=30, to=100, increment=5, width=10),
        )
        ttk.Checkbutton(form, text="画像挿入時に既定で最適化する", variable=self.image_optimize_var).grid(
            row=10, column=1, sticky=tk.W, pady=8
        )
        ttk.Checkbutton(form, text="投稿ヘルパーでタグを本文末尾に追加する", variable=self.append_tags_var).grid(
            row=11, column=1, sticky=tk.W, pady=8
        )
        ttk.Checkbutton(form, text="投稿ヘルパー起動時にnote投稿画面も開く", variable=self.open_note_var).grid(
            row=12, column=1, sticky=tk.W, pady=8
        )
        self.commercial_terms_reviewed_check = ttk.Checkbutton(
            form,
            text="利用条件/商用方針を販売前に確認済み",
            variable=self.commercial_terms_reviewed_var,
        )
        self.commercial_terms_reviewed_check.grid(
            row=13, column=1, sticky=tk.W, pady=8
        )
        self.commercial_support_scope_check = ttk.Checkbutton(
            form,
            text="サポート範囲と返金条件を販売ページに明記済み",
            variable=self.commercial_support_scope_var,
        )
        self.commercial_support_scope_check.grid(
            row=14,
            column=1,
            sticky=tk.W,
            pady=8,
        )
        progress_panel = ttk.Frame(form, style="Surface.TFrame")
        progress_panel.grid(row=15, column=1, sticky=tk.EW, pady=(2, 8))
        ttk.Label(progress_panel, textvariable=self.commercial_progress_var, style="Surface.TLabel").pack(
            anchor=tk.W,
            fill=tk.X,
        )
        ttk.Label(progress_panel, textvariable=self.commercial_next_var, style="Muted.TLabel", wraplength=720).pack(
            anchor=tk.W,
            fill=tk.X,
            pady=(3, 0),
        )
        self._build_commercial_setup_checklist(progress_panel)
        setup_actions = ttk.Frame(form, style="Surface.TFrame")
        setup_actions.grid(row=16, column=1, sticky=tk.EW, pady=8)
        ttk.Button(setup_actions, text="セットアップウィザード", command=lambda: self.show_setup_wizard(force=True)).pack(
            side=tk.LEFT
        )
        ttk.Button(setup_actions, text="次の不足へ", command=self.focus_next_commercial_missing_field).pack(
            side=tk.LEFT,
            padx=6,
        )
        ttk.Button(setup_actions, text="選択項目へ", command=self.focus_selected_commercial_setup_item).pack(
            side=tk.LEFT
        )
        ttk.Button(setup_actions, text="販売者情報確認", command=self.show_commercial_setup_status_action).pack(
            side=tk.LEFT,
            padx=6,
        )
        ttk.Button(setup_actions, text="販売者テンプレ", command=self.create_commercial_setup_template_action).pack(
            side=tk.LEFT
        )
        ttk.Button(setup_actions, text="テンプレ適用", command=self.apply_latest_commercial_setup_template_action).pack(
            side=tk.LEFT,
            padx=6,
        )
        form.columnconfigure(1, weight=1)
        self._bind_commercial_setup_progress()
        self._refresh_commercial_setup_progress()

        self.settings_help_box = ScrolledText(self.settings_tab, wrap=tk.WORD, height=10, borderwidth=0)
        _style_text_widget(self.settings_help_box)
        self.settings_help_box.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.settings_help_box.insert(
            tk.END,
            "設定は .auto-note/settings.json に保存されます。\n\n"
            "既定タグは、新規記事作成時にタグ入力を省略した場合に使われます。\n"
            "記事検索パターンは通常 *.md のままで構いません。\n"
            "表示サイズは、文字や行高が潰れて見える時にヘッダーの「表示」またはここから「大きめ」へ変更します。\n"
            "表示リセットは、表示サイズとウィンドウサイズを初期状態へ戻します。\n"
            "画像最大幅と画像品質は、画像挿入時の最適化に使われます。\n"
            "サポート連絡先はヘルプ画面に表示する任意のメモです。\n"
            "販売者情報と確認チェックは、販売準備レポートの根拠として保存されます。\n"
            "販売者テンプレは、販売ページ作成前に必要な情報と確認事項をMarkdownで下書きします。\n"
            "テンプレ適用は、最新の販売者テンプレから設定へ値を保存します。\n"
            "販売者情報確認は、未保存の入力欄も含めて不足項目と公開URLの確認事項を診断タブに表示します。\n"
            "次の不足へは、販売者情報の未入力または確認が必要な欄へ移動します。",
        )
        self.settings_help_box.configure(state=tk.DISABLED)

    def _build_commercial_setup_checklist(self, parent: ttk.Frame) -> None:
        columns = ("status", "field", "detail", "action")
        self.commercial_setup_tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=6,
        )
        self.commercial_setup_tree.heading("status", text="状態")
        self.commercial_setup_tree.heading("field", text="項目")
        self.commercial_setup_tree.heading("detail", text="現在")
        self.commercial_setup_tree.heading("action", text="次の操作")
        self.commercial_setup_tree.column("status", width=74, minwidth=64, stretch=False)
        self.commercial_setup_tree.column("field", width=154, minwidth=120, stretch=False)
        self.commercial_setup_tree.column("detail", width=210, minwidth=150)
        self.commercial_setup_tree.column("action", width=310, minwidth=180)
        self.commercial_setup_tree.pack(fill=tk.X, pady=(8, 0))
        self.commercial_setup_tree.bind("<<TreeviewSelect>>", lambda _event: self.on_select_commercial_setup_item())
        self._configure_commercial_setup_tree_tags()
        ttk.Label(
            parent,
            textvariable=self.commercial_setup_action_var,
            style="Muted.TLabel",
            wraplength=720,
        ).pack(anchor=tk.W, fill=tk.X, pady=(4, 0))

    def _configure_commercial_setup_tree_tags(self) -> None:
        self.commercial_setup_tree.tag_configure("ok", background="#dff3ed", foreground="#105f54")
        self.commercial_setup_tree.tag_configure("warn", background="#fff4db", foreground="#8a4f00")
        self.commercial_setup_tree.tag_configure("missing", background="#ffe2df", foreground="#8b2119")

    def _form_row(self, parent: ttk.Frame, row: int, label: str, widget: tk.Widget) -> None:
        ttk.Label(parent, text=label, style="Surface.TLabel").grid(row=row, column=0, sticky=tk.W, pady=8, padx=(0, 12))
        widget.grid(row=row, column=1, sticky=tk.EW, pady=8)

    def _render_home_quick_actions(self) -> None:
        if not hasattr(self, "home_quick_buttons_frame"):
            return
        for child in self.home_quick_buttons_frame.winfo_children():
            child.destroy()
        query = self.home_quick_filter_var.get() if hasattr(self, "home_quick_filter_var") else ""
        actions = list(getattr(self, "home_quick_actions", []))
        filtered = [
            action
            for action in actions
            if _home_quick_action_matches(self._button_label_text(action[0]), query)
        ]
        if hasattr(self, "home_quick_status_var"):
            self.home_quick_status_var.set(_home_quick_action_status(len(filtered), len(actions), query))
        if not filtered:
            ttk.Label(
                self.home_quick_buttons_frame,
                text="一致する操作はありません。検索語を短くするか、コマンド検索を開いてください。",
                style="Muted.TLabel",
                wraplength=760,
            ).grid(row=0, column=0, sticky=tk.W, pady=(2, 4))
            return
        self._build_button_bar(self.home_quick_buttons_frame, filtered, columns=5)

    def clear_home_quick_filter(self) -> None:
        if not hasattr(self, "home_quick_filter_var"):
            return
        if self.home_quick_filter_var.get():
            self.home_quick_filter_var.set("")
            self.notify("次の作業の絞り込みを解除しました", level="info", transient=True)

    def _button_label_text(self, value: object) -> str:
        if isinstance(value, tk.Variable):
            try:
                return str(value.get())
            except tk.TclError:
                return ""
        return str(value)

    def _build_button_bar(self, parent: ttk.Frame, actions, *, columns: int = 5) -> None:
        render_columns = max(1, min(columns, UI_ACTION_BUTTON_MAX_COLUMNS))
        for index, action in enumerate(actions):
            text = action[0]
            command = action[1]
            style = action[2] if len(action) > 2 else None
            row, column = divmod(index, render_columns)
            options = {"command": command}
            if isinstance(text, tk.Variable):
                options["textvariable"] = text
            else:
                options["text"] = text
            if style:
                options["style"] = style
            button = ttk.Button(parent, **options)
            button.grid(row=row, column=column, sticky=tk.EW, padx=(0 if column == 0 else 6, 0), pady=(0, 6))
        min_width = _scaled_action_button_min_width(parent)
        for column in range(render_columns):
            parent.columnconfigure(column, weight=1, uniform="button_bar", minsize=min_width)

    def _configure_home_action_tree_tags(self) -> None:
        self.home_action_tree.tag_configure("blocker", background="#ffe2df", foreground="#8b2119")
        self.home_action_tree.tag_configure("warning", background="#fff4db", foreground="#8a4f00")
        self.home_action_tree.tag_configure("maintenance", background="#e7f0ff", foreground="#174ea6")
        self.home_action_tree.tag_configure("ready", background="#dff3ed", foreground="#105f54")
        self.home_action_tree.tag_configure("info", background="#f3f4f6", foreground="#374151")

    def _render_home_action_plan(self, report) -> None:
        if not hasattr(self, "home_action_tree"):
            return
        self._home_action_steps = list(report.steps)
        self.home_action_tree.delete(*self.home_action_tree.get_children())
        for index, step in enumerate(self._home_action_steps):
            iid = str(index)
            self.home_action_tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(_action_step_label(step.severity), step.title, step.action),
                tags=(step.severity,),
            )
        children = self.home_action_tree.get_children()
        if children:
            self.home_action_tree.selection_set(children[0])
            self.home_action_tree.focus(children[0])
            self.on_select_home_action_step()
        else:
            self.home_action_var.set("")

    def on_select_home_action_step(self) -> None:
        step = self._selected_home_action_step()
        if step is None:
            self.home_action_var.set("")
            return
        suffix = f" / CLI: {step.command}" if step.command else ""
        self.home_action_var.set(f"{step.reason}{suffix}")

    def _selected_home_action_step(self) -> ActionPlanStep | None:
        if not hasattr(self, "home_action_tree"):
            return None
        selection = self.home_action_tree.selection()
        if not selection:
            return None
        try:
            index = int(selection[0])
        except ValueError:
            return None
        if 0 <= index < len(self._home_action_steps):
            return self._home_action_steps[index]
        return None

    def run_selected_home_action_step(self) -> None:
        step = self._selected_home_action_step()
        if step is None:
            self.notify("優先アクションを選択してください", level="warning")
            return
        self._run_action_plan_step(step)

    def copy_selected_home_action_command(self) -> None:
        step = self._selected_home_action_step()
        if step is None or not step.command:
            self.notify("コピーできるCLIがありません", level="warning")
            return
        self.clipboard_clear()
        self.clipboard_append(step.command)
        self.notify("CLIコマンドをコピーしました", level="success")

    def _build_diagnostics_tab(self) -> None:
        top = ttk.Frame(self.diagnostics_tab)
        top.pack(fill=tk.X, pady=(0, 6))
        title_group = ttk.Frame(top)
        title_group.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(title_group, text="診断と保守", style="PageTitle.TLabel").pack(anchor=tk.W)
        ttk.Label(
            title_group,
            text="品質チェック、配布ZIP、プライバシー監査、復旧作業を集約します。",
            style="PageSubtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))

        actions = ttk.Frame(self.diagnostics_tab)
        actions.pack(fill=tk.X, pady=(0, 8))
        self._build_button_bar(
            actions,
            [
                ("診断実行", self.run_diagnostics_to_tab, "Primary.TButton"),
                ("初回チェック", self.run_first_run_to_tab),
                ("受入チェック", self.run_acceptance_to_tab),
                ("受入保存", self.create_acceptance_report_action),
                ("受入フル保存", self.create_full_acceptance_report_action),
                ("販売ナビ", self.run_sales_plan_to_tab),
                ("販売ナビ保存", self.create_sales_plan_report_action),
                ("販売者情報確認", self.show_commercial_setup_status_action),
                ("販売者テンプレ", self.create_commercial_setup_template_action),
                ("テンプレ適用", self.apply_latest_commercial_setup_template_action),
                ("販売素材作成", self.create_sales_materials_action),
                ("販売素材検証", self.verify_latest_sales_materials_action),
                ("掲載画像作成", self.create_sales_screenshots_action),
                ("掲載画像検証", self.verify_latest_sales_screenshots_action),
                ("掲載キット作成", self.create_sales_listing_kit_action),
                ("掲載キット検証", self.verify_latest_sales_listing_kit_action),
                ("テンプレ取込一括", self.create_sales_finalize_with_template_action),
                ("販売一括作成", self.create_sales_finalize_action),
                ("販売準備", self.run_commercial_readiness_to_tab),
                ("販売準備保存", self.create_commercial_readiness_report_action),
                ("方針レビュー", self.create_commercial_policy_review_action),
                ("販売一式作成", self.create_sales_handoff_action),
                ("販売一式検証", self.verify_latest_sales_handoff_action),
                ("購入者ZIP抽出", self.extract_latest_buyer_delivery_action),
                ("購入者ZIP検証", self.verify_latest_buyer_delivery_action),
                ("送付前チェック", self.run_buyer_send_readiness_to_tab),
                ("送付前保存", self.create_buyer_send_readiness_report_action),
                ("送付記録", self.create_seller_delivery_receipt_action),
                ("送付記録コピー", self.copy_latest_seller_delivery_receipt_action),
                ("注文控えコピー", self.copy_latest_seller_order_note_action),
                ("問い合わせ票", self.open_latest_buyer_support_request_action),
                ("購入者ZIP場所", self.open_latest_buyer_delivery_location_action),
                ("送付文コピー", self.copy_latest_buyer_delivery_message_action),
                ("ZIPパスコピー", self.copy_latest_buyer_delivery_zip_path_action),
                ("送付情報コピー", self.copy_latest_buyer_delivery_sheet_action),
                ("最終レビュー", self.run_sales_review_to_tab),
                ("レビュー保存", self.create_sales_review_report_action),
                ("販売直前", self.run_sales_launch_to_tab),
                ("直前保存", self.create_sales_launch_checklist_action),
                ("販売確認記録", self.create_sales_launch_confirmation_action),
                ("販売前一括チェック", self.run_release_check_full_action),
                ("セルフテスト", self.run_self_test_to_tab),
                ("セルフテスト保存", self.create_self_test_report_action),
                ("運用サマリー", self.run_overview_to_tab),
                ("予定ICS出力", self.export_calendar_action),
                ("スターター一式", self.create_starter_pack_action),
                ("スターター整理", self.cleanup_starter_pack_action),
                ("投稿キュー", self.publish_queue_to_tab),
                ("E2E確認", self.run_workflow_smoke_to_tab),
                ("クイック確認", self.run_quickstart_to_tab),
                ("ヘルパー生成確認", self.run_quickstart_helper_smoke_to_tab),
                ("セットアップ確認", self.run_setup_to_tab),
                ("準備度", self.run_readiness_to_tab),
                ("復旧セット", self.run_recovery_kit_to_tab),
                ("最新復旧レポート", self.show_latest_recovery_kit_report_action),
                ("復旧レポートコピー", self.copy_latest_recovery_kit_report_action),
                ("復旧レポート場所", self.open_recovery_kit_reports_folder_action),
                ("自動修復", self.run_repair_to_tab),
                ("トラブル診断", self.run_troubleshoot_to_tab),
                ("出荷前チェック", self.run_preflight_to_tab),
                ("出荷ZIP作成", self.run_preflight_create_release_to_tab),
                ("プライバシー監査", self.run_privacy_audit_to_tab),
                ("危険生成物確認", self.preview_privacy_failed_cleanup_action),
                ("品質チェック", self.run_quality_to_tab),
                ("診断プレビュー", self.preview_diagnostic_report_action),
                ("診断レポート", self.create_diagnostic_report_action),
                ("診断ZIP検証", self.verify_latest_diagnostic_report_action),
                ("診断ZIP場所", self.open_latest_diagnostic_report_location_action),
                ("診断ZIPパス", self.copy_latest_diagnostic_report_path_action),
                ("バックアップ作成", self.create_backup_action),
                ("バックアップ確認", self.inspect_backup_action),
                ("バックアップ復元", self.restore_backup_action),
                ("配布ZIP作成", self.create_release_action),
                ("最新ZIP検証", self.verify_latest_release_action),
                ("生成物確認", self.preview_cleanup_action),
                ("表示診断", self.show_display_diagnostics_action),
                ("表示診断コピー", self.copy_display_diagnostics_action),
                ("GUIログ表示", self.show_gui_log_action),
                ("GUIログコピー", self.copy_gui_log_action),
                ("GUIログクリア", self.clear_gui_log_action, "Danger.TButton"),
                ("ログを開く", self.open_gui_log),
                ("GUIログ場所", self.open_gui_log_folder_action),
                ("保守フォルダ", self.open_maintenance_folder),
            ],
            columns=5,
        )

        self.diagnostics_text = ScrolledText(self.diagnostics_tab, wrap=tk.WORD, borderwidth=0)
        _style_text_widget(self.diagnostics_text, code=True)
        self.diagnostics_text.pack(fill=tk.BOTH, expand=True)
        self.diagnostics_text.configure(state=tk.DISABLED)

    def _build_help_tab(self) -> None:
        top = ttk.Frame(self.help_tab)
        top.pack(fill=tk.X, pady=(0, 10))
        title_group = ttk.Frame(top)
        title_group.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(title_group, text="ヘルプとサポート", style="PageTitle.TLabel").pack(anchor=tk.W)
        ttk.Label(
            title_group,
            text="購入者向け案内、問い合わせ一式、販売候補版の確認資料へ移動します。",
            style="PageSubtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))
        ttk.Button(top, text="セットアップ", command=lambda: self.show_setup_wizard(force=True)).pack(side=tk.RIGHT)

        support_panel = ttk.Frame(self.help_tab, style="Surface.TFrame", padding=12)
        support_panel.pack(fill=tk.X, pady=(0, 8))
        support_header = ttk.Frame(support_panel, style="Surface.TFrame")
        support_header.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(support_header, text="サポート送付", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(
            support_header,
            text="問い合わせ一式の作成、検証、送付前確認をここで完結します。",
            style="Muted.TLabel",
        ).pack(side=tk.LEFT, padx=(12, 0))

        self.support_contact_summary_var = tk.StringVar(value="未設定")
        self.support_send_readiness_var = tk.StringVar(value="未準備")
        self.support_bundle_summary_var = tk.StringVar(value="未作成")
        self.support_bundle_status_var = tk.StringVar(value="未検証")
        self.support_bundle_freshness_var = tk.StringVar(value="-")
        self.support_next_action_var = tk.StringVar(value="問い合わせ一式を作成")
        self.support_next_button_var = tk.StringVar(
            value=_support_next_button_label(self.support_next_action_var.get())
        )
        support_summary = ttk.Frame(support_panel, style="Surface.TFrame")
        support_summary.pack(fill=tk.X, pady=(0, 8))
        for column, (label, variable) in enumerate(
            (
                ("送付準備", self.support_send_readiness_var),
                ("連絡先", self.support_contact_summary_var),
                ("最新ZIP", self.support_bundle_summary_var),
                ("検証", self.support_bundle_status_var),
                ("更新", self.support_bundle_freshness_var),
                ("次の操作", self.support_next_action_var),
            )
        ):
            cell = ttk.Frame(support_summary, style="Surface.TFrame")
            cell.grid(row=0, column=column, sticky=tk.NSEW, padx=(0 if column == 0 else 8, 0))
            ttk.Label(cell, text=label, style="KpiLabel.TLabel").pack(anchor=tk.W)
            if label == "送付準備":
                status_row = ttk.Frame(cell, style="Surface.TFrame")
                status_row.pack(fill=tk.X, pady=(3, 0))
                pill_text, bg, fg = _support_send_readiness_indicator_style(variable.get())
                self.support_send_readiness_status_pill = tk.Label(
                    status_row,
                    text=pill_text,
                    bg=bg,
                    fg=fg,
                    font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
                    padx=6,
                    pady=3,
                    width=8,
                )
                self.support_send_readiness_status_pill.pack(side=tk.LEFT)
                ttk.Label(
                    status_row,
                    textvariable=variable,
                    style="Surface.TLabel",
                    wraplength=150,
                ).pack(
                    side=tk.LEFT,
                    fill=tk.X,
                    expand=True,
                    padx=(6, 0),
                )
            elif label == "連絡先":
                status_row = ttk.Frame(cell, style="Surface.TFrame")
                status_row.pack(fill=tk.X, pady=(3, 0))
                pill_text, bg, fg = _support_contact_indicator_style(variable.get())
                self.support_contact_status_pill = tk.Label(
                    status_row,
                    text=pill_text,
                    bg=bg,
                    fg=fg,
                    font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
                    padx=6,
                    pady=3,
                    width=8,
                )
                self.support_contact_status_pill.pack(side=tk.LEFT)
                ttk.Label(
                    status_row,
                    textvariable=variable,
                    style="Surface.TLabel",
                    wraplength=160,
                ).pack(
                    side=tk.LEFT,
                    fill=tk.X,
                    expand=True,
                    padx=(6, 0),
                )
            elif label == "検証":
                status_row = ttk.Frame(cell, style="Surface.TFrame")
                status_row.pack(fill=tk.X, pady=(3, 0))
                pill_text, bg, fg = _support_bundle_indicator_style(variable.get())
                self.support_bundle_status_pill = tk.Label(
                    status_row,
                    text=pill_text,
                    bg=bg,
                    fg=fg,
                    font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
                    padx=8,
                    pady=4,
                    width=8,
                )
                self.support_bundle_status_pill.pack(side=tk.LEFT)
                ttk.Label(status_row, textvariable=variable, style="Surface.TLabel", wraplength=160).pack(
                    side=tk.LEFT,
                    fill=tk.X,
                    expand=True,
                    padx=(6, 0),
                )
            else:
                ttk.Label(cell, textvariable=variable, style="Surface.TLabel", wraplength=220).pack(
                    anchor=tk.W,
                    pady=(3, 0),
                )
            support_summary.columnconfigure(column, weight=1, uniform="support_summary")
        support_buttons = ttk.Frame(support_panel, style="Surface.TFrame")
        support_buttons.pack(fill=tk.X)
        self._build_button_bar(
            support_buttons,
            [
                (self.support_next_button_var, self.run_support_next_action, "Primary.TButton"),
                ("問い合わせ一式", self.create_support_bundle_action),
                ("一式ZIP検証", self.verify_latest_support_bundle_action),
                ("ZIPログ要約", self.show_support_gui_log_summary_action),
                ("ZIP表示診断", self.show_support_display_diagnostics_action),
                ("最新復旧レポート", self.show_latest_recovery_kit_report_action),
                ("復旧レポートコピー", self.copy_latest_recovery_kit_report_action),
                ("復旧レポート場所", self.open_recovery_kit_reports_folder_action),
                ("送付前リスト", self.show_support_send_checklist_action),
                ("送付文コピー", self.copy_support_send_message_action),
                ("最新ZIP場所", self.open_latest_support_bundle_location_action),
                ("最新ZIPパス", self.copy_latest_support_bundle_path_action),
                ("問い合わせ作成", self.create_support_request_action),
                ("連絡先コピー", self.copy_support_contact_action),
                ("連絡先へ", self.focus_support_contact_field),
            ],
            columns=4,
        )

        docs = ttk.Frame(self.help_tab, style="Surface.TFrame", padding=12)
        docs.pack(fill=tk.X, pady=(0, 8))
        self._build_button_bar(
            docs,
            [
                ("README", self.open_readme),
                ("サポート", self.open_support_guide),
                ("ログイン安全", self.show_note_login_safety_action),
                ("更新手順", self.open_update_guide),
                ("プライバシー", self.open_privacy_guide),
                ("利用条件", self.open_terms_draft),
                ("販売方針", self.open_commercial_policy),
                ("変更履歴", self.open_changelog),
                ("リリース手順", self.open_release_checklist),
                ("RC引き渡し", self.open_rc_handoff),
                ("販売準備メモ", self.open_product_readiness),
                ("第三者表記", self.open_third_party_notices),
            ],
            columns=5,
        )

        actions = ttk.Frame(self.help_tab, style="Surface.TFrame", padding=12)
        actions.pack(fill=tk.X, pady=(0, 10))
        self._build_button_bar(
            actions,
            [
                ("アプリ情報", self.show_app_info),
                ("ログイン安全ガイド", self.show_note_login_safety_action),
                ("noteログイン", self.open_note_login_action),
                ("初回チェック", self.run_first_run_to_tab),
                ("受入チェック", self.run_acceptance_to_tab),
                ("受入保存", self.create_acceptance_report_action),
                ("受入フル保存", self.create_full_acceptance_report_action),
                ("販売ナビ", self.run_sales_plan_to_tab),
                ("販売ナビ保存", self.create_sales_plan_report_action),
                ("販売者情報確認", self.show_commercial_setup_status_action),
                ("販売素材作成", self.create_sales_materials_action),
                ("掲載画像作成", self.create_sales_screenshots_action),
                ("掲載キット作成", self.create_sales_listing_kit_action),
                ("掲載キット検証", self.verify_latest_sales_listing_kit_action),
                ("テンプレ取込一括", self.create_sales_finalize_with_template_action),
                ("販売一括作成", self.create_sales_finalize_action),
                ("販売準備", self.run_commercial_readiness_to_tab),
                ("販売準備保存", self.create_commercial_readiness_report_action),
                ("方針レビュー", self.create_commercial_policy_review_action),
                ("セルフテスト", self.run_self_test_to_tab),
                ("セルフテスト保存", self.create_self_test_report_action),
                ("運用サマリー", self.run_overview_to_tab),
                ("予定ICS出力", self.export_calendar_action),
                ("投稿キュー", self.publish_queue_to_tab),
                ("クイック確認", self.run_quickstart_to_tab),
                ("ヘルパー生成確認", self.run_quickstart_helper_smoke_to_tab),
                ("練習記事作成", self.create_practice_article_action),
                ("スターター一式", self.create_starter_pack_action),
                ("スターター整理", self.cleanup_starter_pack_action),
                ("ライセンス表示", self.show_dependency_notices),
                ("第三者表記更新", self.write_dependency_notices_action),
                ("セットアップ確認", self.run_setup_to_tab),
                ("復旧セット", self.run_recovery_kit_to_tab),
                ("最新復旧レポート", self.show_latest_recovery_kit_report_action),
                ("復旧レポートコピー", self.copy_latest_recovery_kit_report_action),
                ("復旧レポート場所", self.open_recovery_kit_reports_folder_action),
                ("自動修復", self.run_repair_to_tab),
                ("トラブル診断", self.run_troubleshoot_to_tab),
                ("問い合わせ作成", self.create_support_request_action),
                ("問い合わせ一式", self.create_support_bundle_action),
                ("一式ZIP検証", self.verify_latest_support_bundle_action),
                ("ZIPログ要約", self.show_support_gui_log_summary_action),
                ("ZIP表示診断", self.show_support_display_diagnostics_action),
                ("送付前リスト", self.show_support_send_checklist_action),
                ("送付文コピー", self.copy_support_send_message_action),
                ("販売者情報確認", self.show_commercial_setup_status_action),
                ("販売者テンプレ", self.create_commercial_setup_template_action),
                ("テンプレ適用", self.apply_latest_commercial_setup_template_action),
                ("テンプレ取込一括", self.create_sales_finalize_with_template_action),
                ("販売一括作成", self.create_sales_finalize_action),
                ("販売一式作成", self.create_sales_handoff_action),
                ("販売一式検証", self.verify_latest_sales_handoff_action),
                ("購入者ZIP抽出", self.extract_latest_buyer_delivery_action),
                ("購入者ZIP検証", self.verify_latest_buyer_delivery_action),
                ("送付前チェック", self.run_buyer_send_readiness_to_tab),
                ("送付前保存", self.create_buyer_send_readiness_report_action),
                ("送付記録", self.create_seller_delivery_receipt_action),
                ("送付記録コピー", self.copy_latest_seller_delivery_receipt_action),
                ("注文控えコピー", self.copy_latest_seller_order_note_action),
                ("問い合わせ票", self.open_latest_buyer_support_request_action),
                ("購入者ZIP場所", self.open_latest_buyer_delivery_location_action),
                ("送付文コピー", self.copy_latest_buyer_delivery_message_action),
                ("ZIPパスコピー", self.copy_latest_buyer_delivery_zip_path_action),
                ("送付情報コピー", self.copy_latest_buyer_delivery_sheet_action),
                ("最終レビュー", self.run_sales_review_to_tab),
                ("レビュー保存", self.create_sales_review_report_action),
                ("記事CSV出力", self.export_inventory_action),
                ("診断プレビュー", self.preview_diagnostic_report_action),
                ("診断レポート作成", self.create_diagnostic_report_action),
                ("診断ZIP検証", self.verify_latest_diagnostic_report_action),
                ("診断ZIP場所", self.open_latest_diagnostic_report_location_action),
                ("診断ZIPパス", self.copy_latest_diagnostic_report_path_action),
                ("プライバシー監査", self.run_privacy_audit_to_tab),
                ("危険生成物確認", self.preview_privacy_failed_cleanup_action),
                ("出荷ZIP作成", self.run_preflight_create_release_to_tab),
                ("配布ZIP作成", self.create_release_action),
                ("最新ZIP検証", self.verify_latest_release_action),
                ("生成物整理", self.apply_cleanup_action),
                ("危険生成物整理", self.apply_privacy_failed_cleanup_action),
                ("表示診断", self.show_display_diagnostics_action),
                ("表示診断コピー", self.copy_display_diagnostics_action),
                ("GUIログ表示", self.show_gui_log_action),
                ("GUIログコピー", self.copy_gui_log_action),
                ("GUIログクリア", self.clear_gui_log_action, "Danger.TButton"),
                ("GUIログ場所", self.open_gui_log_folder_action),
                ("保守フォルダ", self.open_maintenance_folder),
            ],
            columns=5,
        )

        self.help_text = ScrolledText(self.help_tab, wrap=tk.WORD, borderwidth=0)
        _style_text_widget(self.help_text)
        self.help_text.pack(fill=tk.BOTH, expand=True)
        self.help_text.configure(state=tk.DISABLED)

    def _build_notification_bar(self, parent: ttk.Frame) -> None:
        self.notification = tk.Label(
            parent,
            text="準備できました",
            anchor=tk.W,
            bg=UI_COLORS["surface_selected"],
            fg=UI_COLORS["ink"],
            font=(UI_FONT, UI_BADGE_FONT_SIZE, UI_BADGE_FONT_WEIGHT),
            padx=12,
            pady=7,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=UI_COLORS["line"],
        )
        self.notification.pack(fill=tk.X, pady=(8, 0))

    def refresh_all(self) -> None:
        self.refresh_articles()
        self.refresh_ideas()
        self.refresh_schedule()
        self.refresh_home()
        self.refresh_first_run_panel()
        self.refresh_review_panel()
        self.refresh_help()
        self._refresh_commercial_setup_progress()
        self.run_check_all(show_popup=False)
        self.notify("更新しました")

    def _configure_first_run_tree_tags(self) -> None:
        self.first_run_tree.tag_configure("pass", background="#dff3ed", foreground="#105f54")
        self.first_run_tree.tag_configure("info", background="#e7f0ff", foreground="#174ea6")
        self.first_run_tree.tag_configure("warn", background="#fff4db", foreground="#8a4f00")
        self.first_run_tree.tag_configure("fail", background="#ffe2df", foreground="#8b2119")

    def refresh_first_run_panel(self, *, show_popup: bool = False, select_tab: bool = False) -> FirstRunReport | None:
        if not hasattr(self, "first_run_tree"):
            return None
        report = run_first_run_checklist(self.project_dir)
        self._last_first_run_report = report
        self._refresh_home_first_run_summary(report)

        verdict = _first_run_verdict(report.status)
        bg, fg = _first_run_status_colors(report.status)
        self.first_run_status_pill.configure(text=verdict, bg=bg, fg=fg)
        self.first_run_score_var.set(f"{report.score}/100")
        self.first_run_summary_var.set(_first_run_summary(report))

        counts = _first_run_counts(report)
        for key, value in counts.items():
            if key in self.first_run_count_vars:
                self.first_run_count_vars[key].set(str(value))

        self._populate_first_run_tree(report)

        if select_tab:
            self.notebook.select(self.first_run_tab)
        if show_popup:
            self.notify("初回チェックを更新しました", level=self._first_run_notify_level(report))
        return report

    def toggle_first_run_action_filter(self) -> None:
        report = self._last_first_run_report
        if report is None:
            return
        self._populate_first_run_tree(report)
        visible = len(self.first_run_tree.get_children())
        if self.first_run_action_filter_var.get():
            self.notify(f"要対応の初回チェック項目だけ表示しています: {visible}件", level="info", transient=True)
        else:
            self.notify("すべての初回チェック項目を表示しています", level="info", transient=True)

    def _populate_first_run_tree(self, report: FirstRunReport) -> None:
        self.first_run_tree.delete(*self.first_run_tree.get_children())
        action_only = bool(
            hasattr(self, "first_run_action_filter_var") and self.first_run_action_filter_var.get()
        )
        actionable_iid = ""
        for index, item in enumerate(report.items):
            if action_only and item.status not in {"warn", "fail"}:
                continue
            iid = str(index)
            action = item.action or item.gui or item.command or ""
            label = _first_run_item_label(item.status)
            self.first_run_tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(label, item.name, item.detail, action),
                tags=(item.status,),
            )
            if not actionable_iid and item.status != "pass":
                actionable_iid = iid

        items = self.first_run_tree.get_children()
        if items:
            selected = actionable_iid or items[0]
            self.first_run_tree.selection_set(selected)
            self.first_run_tree.focus(selected)
            self.on_select_first_run_item()
            return

        self._clear_first_run_detail()
        if action_only:
            self.first_run_detail_name_var.set("要対応項目はありません")
            self.first_run_detail_status_var.set("READY")
            self.first_run_detail_text_var.set("初回チェックのWARN/NGはありません。受入保存へ進めます。")
            self.first_run_detail_gui_var.set("GUI: 受入保存 または 販売ナビ")
            self.first_run_detail_cli_var.set("CLI: auto-note acceptance --project-dir . --full")

    def on_select_first_run_item(self) -> None:
        item = self._selected_first_run_item()
        if item is None:
            self._clear_first_run_detail()
            return
        self.first_run_detail_name_var.set(item.name)
        self.first_run_detail_status_var.set(f"{_first_run_item_label(item.status)} / {item.detail}")
        detail = item.action or "この項目は現在の状態で問題ありません。"
        self.first_run_detail_text_var.set(detail)
        self.first_run_detail_gui_var.set(f"GUI: {item.gui}" if item.gui else "GUI: 関連画面から確認できます。")
        self.first_run_detail_cli_var.set(f"CLI: {item.command}" if item.command else "CLI: なし")

    def _clear_first_run_detail(self) -> None:
        self.first_run_detail_name_var.set("項目を選択してください")
        self.first_run_detail_status_var.set("")
        self.first_run_detail_text_var.set("")
        self.first_run_detail_gui_var.set("")
        self.first_run_detail_cli_var.set("")

    def _selected_first_run_item(self) -> FirstRunItem | None:
        report = self._last_first_run_report
        if report is None:
            return None
        selection = self.first_run_tree.selection()
        if not selection:
            return None
        try:
            index = int(selection[0])
        except ValueError:
            return None
        if 0 <= index < len(report.items):
            return report.items[index]
        return None

    def run_selected_first_run_action(self) -> None:
        item = self._selected_first_run_item()
        if item is None:
            self.notify("初回チェック項目を選択してください", level="warning")
            return
        actions = {
            "セットアップ": lambda: self.show_setup_wizard(force=True),
            "受入チェック": self.run_acceptance_to_tab,
            "受入保存": self.create_acceptance_report_action,
            "受入フル保存": self.create_full_acceptance_report_action,
            "セルフテスト": self.run_self_test_to_tab,
            "セルフテスト保存": self.create_self_test_report_action,
            "最初の記事": self.create_practice_article_action,
            "投稿ヘルパー": self.open_helper,
            "ログイン安全ガイド": self.show_note_login_safety_action,
            "バックアップ": self.create_backup_action,
            "問い合わせ一式": self.create_support_bundle_action,
            "販売ナビ": self.run_sales_plan_to_tab,
            "販売ナビ保存": self.create_sales_plan_report_action,
            "販売者情報確認": self.show_commercial_setup_status_action,
            "販売素材作成": self.create_sales_materials_action,
            "掲載画像作成": self.create_sales_screenshots_action,
            "掲載画像検証": self.verify_latest_sales_screenshots_action,
            "掲載キット作成": self.create_sales_listing_kit_action,
            "掲載キット検証": self.verify_latest_sales_listing_kit_action,
            "テンプレ適用": self.apply_latest_commercial_setup_template_action,
            "テンプレ取込一括": self.create_sales_finalize_with_template_action,
            "販売一括作成": self.create_sales_finalize_action,
            "販売一式作成": self.create_sales_handoff_action,
            "購入者ZIP抽出": self.extract_latest_buyer_delivery_action,
            "購入者ZIP検証": self.verify_latest_buyer_delivery_action,
            "送付前チェック": self.run_buyer_send_readiness_to_tab,
            "送付前保存": self.create_buyer_send_readiness_report_action,
            "送付記録": self.create_seller_delivery_receipt_action,
            "送付記録コピー": self.copy_latest_seller_delivery_receipt_action,
            "注文控えコピー": self.copy_latest_seller_order_note_action,
            "問い合わせ票": self.open_latest_buyer_support_request_action,
            "購入者ZIP場所": self.open_latest_buyer_delivery_location_action,
            "送付文コピー": self.copy_latest_buyer_delivery_message_action,
            "ZIPパスコピー": self.copy_latest_buyer_delivery_zip_path_action,
            "送付情報コピー": self.copy_latest_buyer_delivery_sheet_action,
            "最終レビュー": self.run_sales_review_to_tab,
            "レビュー保存": self.create_sales_review_report_action,
            "販売直前": self.run_sales_launch_to_tab,
            "直前保存": self.create_sales_launch_checklist_action,
            "販売確認記録": self.create_sales_launch_confirmation_action,
            "noteログイン": self.show_note_login_safety_action,
            "次の一手": self.run_home_primary_action,
        }
        action = actions.get(item.name)
        if action is None:
            self.show_first_run_text()
            return
        action()
        self.refresh_first_run_panel()

    def copy_selected_first_run_cli(self) -> None:
        item = self._selected_first_run_item()
        if item is None or not item.command:
            self.notify("コピーできるCLIがありません", level="warning")
            return
        self.clipboard_clear()
        self.clipboard_append(item.command)
        self.notify("CLIコマンドをコピーしました", level="success")

    def _configure_review_tree_tags(self) -> None:
        self.review_tree.tag_configure("ready", background="#dff3ed", foreground="#105f54")
        self.review_tree.tag_configure("work", background="#fff4db", foreground="#8a4f00")
        self.review_tree.tag_configure("fix", background="#ffe2df", foreground="#8b2119")

    def _configure_review_detail_tags(self) -> None:
        self.review_detail_tree.tag_configure("fix", background="#ffe2df", foreground="#8b2119")
        self.review_detail_tree.tag_configure("improve", background="#fff4db", foreground="#8a4f00")
        self.review_detail_tree.tag_configure("ok", background="#dff3ed", foreground="#105f54")

    def refresh_review_panel_action(self) -> None:
        self.refresh_review_panel(show_popup=True, select_tab=True)

    def refresh_review_panel(self, *, show_popup: bool = False, select_tab: bool = False) -> list[ArticleReview]:
        if not hasattr(self, "review_tree"):
            return []
        try:
            reviews = review_path(
                self.articles_dir,
                pattern=self.settings.article_glob,
                append_tags=self.settings.append_tags_by_default,
            )
        except ArticleError as exc:
            self._last_review_results = []
            self.review_tree.delete(*self.review_tree.get_children())
            self.review_detail_tree.delete(*self.review_detail_tree.get_children())
            self.review_summary_var.set("記事がありません。")
            self.review_detail_title_var.set("記事を選択してください")
            self.review_detail_status_var.set("")
            self.review_action_var.set(str(exc))
            if show_popup:
                self.notify("レビュー対象の記事がありません", level="warning")
            return []

        reviews = sorted(reviews, key=lambda review: (review.ready, not review.needs_fix, review.score, review.article.title))
        self._last_review_results = reviews
        self.review_tree.delete(*self.review_tree.get_children())
        for review in reviews:
            fix_count = sum(1 for item in review.items if item.level == "fix")
            improve_count = sum(1 for item in review.items if item.level == "improve")
            state = "READY" if review.ready else "NEEDS WORK"
            tag = "ready" if review.ready else "fix" if review.needs_fix else "work"
            self.review_tree.insert(
                "",
                tk.END,
                iid=str(review.article.source.resolve()),
                values=(
                    review.score,
                    state,
                    fix_count,
                    improve_count,
                    STATUS_LABELS.get(review.article.status, review.article.status or "draft"),
                    review.article.title,
                ),
                tags=(tag,),
            )
        self.review_summary_var.set(_review_summary_text(reviews))
        children = self.review_tree.get_children()
        if children:
            self.review_tree.selection_set(children[0])
            self.review_tree.focus(children[0])
            self.on_select_review_item()
        if select_tab:
            self.notebook.select(self.check_tab)
        if show_popup:
            level = "warning" if has_review_blockers(reviews) else "success"
            self.notify("記事レビューを更新しました", level=level)
        return reviews

    def on_select_review_item(self) -> None:
        review = self._selected_review()
        self.review_detail_tree.delete(*self.review_detail_tree.get_children())
        if review is None:
            self.review_detail_title_var.set("記事を選択してください")
            self.review_detail_status_var.set("")
            self.review_action_var.set("")
            return
        state = "READY" if review.ready else "NEEDS WORK"
        fix_count = sum(1 for item in review.items if item.level == "fix")
        improve_count = sum(1 for item in review.items if item.level == "improve")
        self.review_detail_title_var.set(review.article.title)
        self.review_detail_status_var.set(
            f"{review.score}/100 [{state}] / 修正 {fix_count} / 改善 {improve_count}"
        )
        for index, item in enumerate(review.items):
            label = {"fix": "FIX", "improve": "改善", "ok": "OK"}.get(item.level, item.level.upper())
            self.review_detail_tree.insert(
                "",
                tk.END,
                iid=str(index),
                values=(label, item.category, item.message),
                tags=(item.level,),
            )
        children = self.review_detail_tree.get_children()
        if children:
            self.review_detail_tree.selection_set(children[0])
            self.review_detail_tree.focus(children[0])
            self.on_select_review_detail()

    def on_select_review_detail(self) -> None:
        item = self._selected_review_detail_item()
        if item is not None:
            action = item.action or "この項目は問題ありません。"
            self.review_action_var.set(f"次の操作: {action}")
            return
        self.review_action_var.set("")

    def _selected_review(self) -> ArticleReview | None:
        if not hasattr(self, "review_tree"):
            return None
        selection = self.review_tree.selection()
        if not selection:
            return None
        selected = selection[0]
        for review in self._last_review_results:
            if str(review.article.source.resolve()) == selected:
                return review
        return None

    def _selected_review_detail_item(self):
        review = self._selected_review()
        if review is None or not hasattr(self, "review_detail_tree"):
            return None
        selection = self.review_detail_tree.selection()
        if not selection:
            return None
        try:
            index = int(selection[0])
        except ValueError:
            return None
        if 0 <= index < len(review.items):
            return review.items[index]
        return None

    def open_selected_review_article(self) -> None:
        self.open_selected_review_article_editor()

    def open_selected_review_article_editor(self) -> None:
        review = self._selected_review()
        if review is None:
            self.notify("レビュー対象の記事を選択してください", level="warning")
            return
        if self.select_article_path(review.article.source, select_tab=True) is None:
            return
        self._select_article_editor_tab()
        item = self._selected_review_detail_item()
        if item is not None and item.level != "ok":
            detail = _article_focus_brief(item.action or item.message, 70)
            level = "warning" if item.level == "fix" else "info"
            self.notify(f"{item.category}: {detail}", level=level)
            return
        self.notify("本文編集へ移動しました", level="success" if review.ready else "info")

    def review_selected_from_review_panel(self) -> None:
        review = self._selected_review()
        if review is None:
            self.review_selected_to_tab()
            return
        if self.select_article_path(review.article.source, select_tab=False) is None:
            return
        self._set_check_text(format_review_report([review]))
        self.notebook.select(self.check_tab)
        self.notify("選択記事レビューを表示しました", level="warning" if review.needs_fix else "success")

    def publish_ready_selected_review_to_tab(self) -> None:
        review = self._selected_review()
        if review is None:
            self.publish_ready_selected_to_tab()
            return
        if self.select_article_path(review.article.source, select_tab=False) is None:
            return
        self.publish_ready_selected_to_tab()

    def improvement_plan_selected_review_to_tab(self) -> None:
        review = self._selected_review()
        if review is None:
            self.improvement_plan_selected_to_tab()
            return
        if self.select_article_path(review.article.source, select_tab=False) is None:
            return
        self.improvement_plan_selected_to_tab()

    def mark_selected_review_ready(self) -> None:
        review = self._selected_review()
        if review is None:
            self.notify("準備OKにする記事を選択してください", level="warning")
            return
        try:
            report = run_publish_ready(
                review.article.source,
                append_tags=self.settings.append_tags_by_default,
                smoke_helper=True,
                output_dir=self.output_dir / "publish-ready",
                mark_ready=True,
            )
        except ArticleError as exc:
            self.notify("準備OKにできません", level="error")
            messagebox.showerror("投稿準備エラー", str(exc))
            return
        self._set_check_text(format_publish_ready_report(report))
        self.refresh_articles()
        self.refresh_schedule()
        self.refresh_home()
        self.refresh_review_panel()
        self.notebook.select(self.check_tab)
        level = {"pass": "success", "warn": "warning", "fail": "error"}.get(report.status, "info")
        if report.marked_ready:
            self.notify("記事を準備OKにしました", level="success")
        else:
            self.notify("準備OKにする前に修正が必要です", level=level)

    def select_article_path(self, path: Path, *, select_tab: bool = True) -> Article | None:
        if not self.confirm_editor_changes():
            return None
        if hasattr(self, "article_filter_var"):
            self.article_filter_var.set("")
        if hasattr(self, "status_filter_var"):
            self.status_filter_var.set("all")
        item_id = str(path.resolve())
        if not self.article_tree.exists(item_id):
            self.refresh_articles()
        if self.article_tree.exists(item_id):
            self.article_tree.selection_set(item_id)
            self.article_tree.focus(item_id)
            self.article_tree.see(item_id)
            self.on_select_article()
            if select_tab:
                self.notebook.select(self.article_tab)
            return self.selected_article
        try:
            article = load_article(path)
        except ArticleError as exc:
            self.notify("記事を開けません", level="error")
            messagebox.showerror("記事エラー", str(exc))
            return None
        self._set_selected_article(article)
        if select_tab:
            self.notebook.select(self.article_tab)
        return article

    def _select_article_editor_tab(self) -> None:
        if hasattr(self, "article_content_tabs") and hasattr(self, "article_editor_tab"):
            self.article_content_tabs.select(self.article_editor_tab)
        if hasattr(self, "editor"):
            self.editor.focus_set()

    def _configure_publish_ready_tree_tags(self) -> None:
        self.publish_ready_tree.tag_configure("pass", background="#dff3ed", foreground="#105f54")
        self.publish_ready_tree.tag_configure("info", background="#e7f0ff", foreground="#174ea6")
        self.publish_ready_tree.tag_configure("warn", background="#fff4db", foreground="#8a4f00")
        self.publish_ready_tree.tag_configure("fail", background="#ffe2df", foreground="#8b2119")

    def refresh_article_focus_panel(self, *, article: Article | None = None) -> ImprovementPlan | None:
        if not hasattr(self, "article_focus_summary_var"):
            return None
        article = article or self.selected_article
        if article is None:
            self._clear_article_focus_panel("記事を選択すると仕上げ状態を確認できます。")
            return None
        try:
            plan = build_improvement_plan(
                article.source,
                append_tags=self.settings.append_tags_by_default,
                limit=6,
            )
        except ArticleError as exc:
            self._last_article_focus_plan = None
            self._render_article_focus_error(str(exc))
            return None
        self._render_article_focus_panel(plan)
        return plan

    def _render_article_focus_panel(self, plan: ImprovementPlan) -> None:
        self._last_article_focus_plan = plan
        status_text, bg, fg = _article_focus_status_style(plan.status)
        self.article_focus_status_pill.configure(text=status_text, bg=bg, fg=fg)
        self.article_focus_summary_var.set(_article_focus_summary(plan))
        self.article_focus_next_var.set(_article_focus_next_text(plan))
        self.article_focus_rail.configure(bg=_article_focus_accent_color(plan.status))

    def _render_article_focus_error(self, message: str) -> None:
        status_text, bg, fg = _article_focus_status_style("blocked")
        self.article_focus_status_pill.configure(text=status_text, bg=bg, fg=fg)
        self.article_focus_summary_var.set("記事を読み込めません。")
        self.article_focus_next_var.set(f"次: {message}")
        self.article_focus_rail.configure(bg=_article_focus_accent_color("blocked"))

    def _clear_article_focus_panel(self, message: str) -> None:
        self._last_article_focus_plan = None
        self.article_focus_status_pill.configure(text="未選択", bg="#344054", fg="#ffffff")
        self.article_focus_summary_var.set(message)
        self.article_focus_next_var.set("次: 記事一覧から対象を選択してください。")
        self.article_focus_rail.configure(bg=UI_COLORS["line"])

    def run_article_focus_next_action(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        plan = self._last_article_focus_plan or self.refresh_article_focus_panel(article=article)
        if plan is None:
            self.notify("選択記事フォーカスを更新できません", level="error")
            return
        if plan.status == "ready":
            self.open_helper()
            return
        self._last_improvement_plan = plan
        self.refresh_review_panel()
        self._last_publish_ready_report = plan.publish_ready
        self._render_publish_ready_panel(plan.publish_ready)
        self._set_check_text(format_improvement_plan(plan))
        self.notebook.select(self.check_tab)
        self.notify("次に直す内容を改善プランで開きました", level=self._improvement_plan_notify_level(plan))

    def refresh_publish_ready_panel_action(self) -> None:
        report = self.refresh_publish_ready_panel(show_popup=True)
        if report is not None:
            self._set_check_text(format_publish_ready_report(report))

    def refresh_publish_ready_panel(
        self,
        *,
        article: Article | None = None,
        show_popup: bool = False,
        smoke_helper: bool = False,
        mark_ready: bool = False,
    ) -> PublishReadyReport | None:
        if not hasattr(self, "publish_ready_tree"):
            return None
        article = article or self.selected_article
        if article is None:
            self._clear_publish_ready_panel("記事を選択すると投稿準備を確認できます。")
            return None
        try:
            report = run_publish_ready(
                article.source,
                append_tags=self.settings.append_tags_by_default,
                smoke_helper=smoke_helper,
                output_dir=self.output_dir / "publish-ready",
                mark_ready=mark_ready,
            )
        except ArticleError as exc:
            self._last_publish_ready_report = None
            self._clear_publish_ready_panel(str(exc))
            if show_popup:
                self.notify("投稿準備を確認できません", level="error")
            return None

        self._last_publish_ready_report = report
        self._render_publish_ready_panel(report)
        if show_popup:
            self.notify("投稿準備を更新しました", level=self._publish_ready_notify_level(report.status))
        return report

    def _render_publish_ready_panel(self, report: PublishReadyReport) -> None:
        status_text = _publish_ready_verdict(report.status)
        bg, fg = _publish_ready_status_colors(report.status)
        self.publish_ready_status_pill.configure(text=status_text, bg=bg, fg=fg)
        self.publish_ready_summary_var.set(_publish_ready_summary(report))

        self.publish_ready_tree.delete(*self.publish_ready_tree.get_children())
        first_attention = ""
        for index, item in enumerate(report.items):
            label = _publish_ready_item_label(item.status)
            iid = str(index)
            self.publish_ready_tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(label, item.name, item.detail),
                tags=(item.status,),
            )
            if not first_attention and item.status != "pass":
                first_attention = iid
        children = self.publish_ready_tree.get_children()
        if children:
            selected = first_attention or children[0]
            self.publish_ready_tree.selection_set(selected)
            self.publish_ready_tree.focus(selected)
            self.on_select_publish_ready_item()
        else:
            self.publish_ready_action_var.set("")

    def _clear_publish_ready_panel(self, message: str) -> None:
        self.publish_ready_status_pill.configure(text="未選択", bg="#344054", fg="#ffffff")
        self.publish_ready_summary_var.set(message)
        self.publish_ready_tree.delete(*self.publish_ready_tree.get_children())
        self.publish_ready_action_var.set("")

    def on_select_publish_ready_item(self) -> None:
        item = self._selected_publish_ready_item()
        if item is None:
            self.publish_ready_action_var.set("")
            return
        if item.action:
            self.publish_ready_action_var.set(f"次の操作: {item.action}")
        elif item.status == "pass":
            self.publish_ready_action_var.set("この項目は問題ありません。")
        else:
            self.publish_ready_action_var.set("詳細を確認してください。")

    def run_selected_publish_ready_action(self) -> None:
        item = self._selected_publish_ready_item()
        if item is None:
            self.notify("投稿準備項目を選択してください", level="warning")
            return

        if item.name == "article":
            self.edit_article_metadata()
        elif item.name == "article check":
            self.check_selected()
        elif item.name == "article review":
            self.review_selected_to_tab()
        elif item.name == "workflow":
            self.notebook.select(self.article_tab)
            if self.selected_article and self.selected_article.status == "scheduled" and not self.selected_article.scheduled:
                self.schedule_entry.focus_set()
                self.notify("公開予定を入力してください", level="warning")
            elif self.selected_article and (self.selected_article.status or "draft") == "draft":
                self.mark_selected_publish_ready()
            else:
                self.status_combo.focus_set()
                self.notify("状態と公開URLを確認してください", level="warning")
        elif item.name in {"posting helper", "mark ready"}:
            if item.name == "posting helper":
                self.generate_publish_ready_helper_action()
            else:
                self.mark_selected_publish_ready()
        else:
            self.publish_ready_selected_to_tab()

    def _selected_publish_ready_item(self) -> PublishReadyItem | None:
        report = self._last_publish_ready_report
        if report is None or not hasattr(self, "publish_ready_tree"):
            return None
        selection = self.publish_ready_tree.selection()
        if not selection:
            return None
        try:
            index = int(selection[0])
        except ValueError:
            return None
        if 0 <= index < len(report.items):
            return report.items[index]
        return None

    def mark_selected_publish_ready(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        report = self.refresh_publish_ready_panel(
            article=article,
            show_popup=False,
            smoke_helper=True,
            mark_ready=True,
        )
        if report is None:
            return
        self._set_check_text(format_publish_ready_report(report))
        self.refresh_articles()
        self.refresh_schedule()
        self.refresh_home()
        self.refresh_review_panel()
        self.notebook.select(self.article_tab if report.marked_ready else self.check_tab)
        if report.marked_ready:
            self.notify("記事を準備OKにしました", level="success")
        else:
            self.notify("準備OKにする前に修正が必要です", level=self._publish_ready_notify_level(report.status))

    def generate_publish_ready_helper_action(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        report = self.refresh_publish_ready_panel(article=article, show_popup=False, smoke_helper=True)
        if report is None:
            return
        self._set_check_text(format_publish_ready_report(report))
        if report.helper_path:
            self.notify(f"ヘルパーHTMLを確認しました: {report.helper_path.name}", level=self._publish_ready_notify_level(report.status))
        else:
            self.notify("ヘルパーHTMLを確認しました", level=self._publish_ready_notify_level(report.status))

    def _publish_ready_notify_level(self, status: str) -> str:
        if status == "fail":
            return "error"
        if status == "warn":
            return "warning"
        return "success"

    def refresh_articles(self) -> None:
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        paths = sorted(
            self.articles_dir.glob(self.settings.article_glob),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        selected_path = self.selected_article.source if self.selected_article else None
        self.article_paths = paths
        self.article_tree.delete(*self.article_tree.get_children())

        selected_item = ""
        for path in paths:
            item_id = str(path.resolve())
            try:
                article = load_article(path)
                if not self.article_matches_filters(article):
                    continue
                report = inspect_article(article, append_tags=self.settings.append_tags_by_default)
                values = (
                    STATUS_LABELS.get(article.status, article.status or "draft"),
                    _issue_summary(report),
                    article.title,
                    article.scheduled or "",
                    report.stats.body_chars,
                    ", ".join(article.tags),
                )
                tag = article.status if article.status in STATUS_COLORS else "draft"
            except ArticleError:
                values = ("エラー", "NG", path.name, "", "", "")
                tag = "error"
            self.article_tree.insert("", tk.END, iid=item_id, values=values, tags=(tag,))
            if selected_path and path.resolve() == selected_path.resolve():
                selected_item = item_id

        visible_items = self.article_tree.get_children()
        if visible_items:
            item_to_select = selected_item or str(paths[0].resolve())
            if not self.article_tree.exists(item_to_select):
                item_to_select = visible_items[0]
            self.article_tree.selection_set(item_to_select)
            self.article_tree.focus(item_to_select)
            self.on_select_article()
        else:
            self._set_selected_article(None)
        self.notify(f"{len(visible_items)}件の記事を表示しました", level="info", transient=True)

    def article_matches_filters(self, article: Article) -> bool:
        status = self.status_filter_var.get() if hasattr(self, "status_filter_var") else "all"
        if status != "all" and (article.status or "draft") != status:
            return False
        query = self.article_filter_var.get().strip().lower() if hasattr(self, "article_filter_var") else ""
        if not query:
            return True
        haystack = " ".join(
            [
                article.title,
                article.source.name,
                article.summary,
                " ".join(article.tags),
                article.status,
                article.scheduled,
            ]
        ).lower()
        return query in haystack

    def clear_article_filters(self) -> None:
        self.article_filter_var.set("")
        self.status_filter_var.set("all")

    def on_select_article(self) -> None:
        if self._restoring_selection:
            return
        selection = self.article_tree.selection()
        if not selection:
            self._set_selected_article(None)
            return
        if not self.confirm_editor_changes():
            self.restore_current_selection()
            return
        path = Path(selection[0])
        try:
            self._set_selected_article(load_article(path))
        except ArticleError as exc:
            messagebox.showerror("読み込みエラー", str(exc))
            self._set_selected_article(None)

    def _set_selected_article(self, article: Article | None) -> None:
        self.selected_article = article
        if not article:
            self.title_var.set("記事を選択してください")
            self.meta_var.set("")
            self.status_var.set("draft")
            self.schedule_var.set("")
            self.url_var.set("")
            self._set_preview("")
            self._set_editor("")
            self._update_status_pill("draft")
            if hasattr(self, "article_focus_summary_var"):
                self._clear_article_focus_panel("記事を選択すると仕上げ状態を確認できます。")
            if hasattr(self, "publish_ready_tree"):
                self._clear_publish_ready_panel("記事を選択すると投稿準備を確認できます。")
            return

        report = inspect_article(article, append_tags=self.settings.append_tags_by_default)
        self.title_var.set(article.title)
        tags = ", ".join(article.tags) if article.tags else "(no tags)"
        self.meta_var.set(
            f"{article.source} | {report.stats.body_chars}文字 | 約{report.stats.reading_minutes}分 | {tags}"
        )
        self.status_var.set(article.status or "draft")
        self.schedule_var.set(article.scheduled)
        self.url_var.set(article.published_url)
        self._set_preview(body_with_tags(article))
        self._set_editor(_read_text(article.source))
        self._update_status_pill(article.status or "draft")
        plan = self.refresh_article_focus_panel(article=article)
        if plan is not None and hasattr(self, "publish_ready_tree"):
            self._last_publish_ready_report = plan.publish_ready
            self._render_publish_ready_panel(plan.publish_ready)
        else:
            self.refresh_publish_ready_panel(article=article)
        self.after(80, lambda path=article.source: self.offer_autosave_restore(path))

    def _update_status_pill(self, status: str) -> None:
        bg, fg = STATUS_COLORS.get(status, STATUS_COLORS["draft"])
        self.status_pill.configure(text=STATUS_LABELS.get(status, status), bg=bg, fg=fg)

    def _set_preview(self, text: str) -> None:
        self.preview.configure(state=tk.NORMAL)
        self.preview.delete("1.0", tk.END)
        self.preview.insert(tk.END, text)
        self.preview.configure(state=tk.DISABLED)

    def _set_editor(self, text: str) -> None:
        if not hasattr(self, "editor"):
            return
        self.editor.delete("1.0", tk.END)
        self.editor.insert(tk.END, text)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.editor_dirty = False
        self._last_autosave_text = ""

    def on_editor_modified(self, _event: tk.Event) -> None:
        if self.editor.edit_modified():
            self.editor_dirty = True
            self.editor.edit_modified(False)

    def schedule_autosave(self) -> None:
        self._autosave_job = self.after(AUTOSAVE_INTERVAL_MS, self.autosave_editor_loop)

    def autosave_editor_loop(self) -> None:
        self._autosave_job = None
        self.autosave_editor_if_needed()
        try:
            if self.winfo_exists():
                self.schedule_autosave()
        except tk.TclError:
            return

    def autosave_editor_if_needed(self, *, notify_user: bool = True) -> None:
        if not self.editor_dirty or not self.selected_article or not hasattr(self, "editor"):
            return
        article_path = self.selected_article.source
        text = self.editor.get("1.0", "end-1c")
        if text == self._last_autosave_text:
            return
        try:
            if article_path.exists() and _read_text(article_path) == text:
                clear_autosave(self.project_dir, article_path)
                self._last_autosave_text = ""
                return
            write_autosave(self.project_dir, article_path, text)
        except OSError as exc:
            if notify_user:
                self.notify(f"自動退避に失敗しました: {exc}", level="warning")
            return
        self._last_autosave_text = text
        if notify_user:
            self.notify("未保存の本文を自動退避しました", level="success", transient=True)

    def offer_autosave_restore(self, article_path: Path) -> None:
        if not self.selected_article or self.selected_article.source != article_path:
            return
        state = autosave_state(self.project_dir, article_path)
        if not state.exists or not state.newer_than_article or state.autosave_path in self._ignored_autosaves:
            return
        if not has_newer_autosave(self.project_dir, article_path):
            return
        restore = messagebox.askyesno(
            "自動退避",
            "未保存の自動退避が見つかりました。エディタに読み込みますか？\n\n"
            "元の記事ファイルは、保存ボタンを押すまで変更されません。",
        )
        if restore:
            self.restore_autosave_to_editor(article_path)
        else:
            self._ignored_autosaves.add(state.autosave_path)

    def restore_autosave_to_editor(self, article_path: Path | None = None) -> bool:
        article = self.selected_article
        if not article:
            return False
        target = article_path or article.source
        if article.source != target:
            return False
        try:
            text = read_autosave(self.project_dir, target)
        except OSError as exc:
            self.notify("自動退避の読み込みに失敗しました", level="error")
            messagebox.showerror("自動退避エラー", str(exc))
            return False
        self._set_editor(text)
        self.editor_dirty = True
        self.notify("自動退避をエディタに読み込みました。保存すると反映されます。", level="warning")
        return True

    def show_autosave_dialog(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        state = autosave_state(self.project_dir, article.source)
        if not state.exists:
            messagebox.showinfo("自動退避", "この記事の自動退避はありません。")
            return

        win = tk.Toplevel(self)
        win.title("自動退避")
        win.geometry("560x260")
        win.transient(self)

        frame = ttk.Frame(win, padding=14)
        frame.pack(fill=tk.BOTH, expand=True)
        updated = "-" if state.updated_at is None else _format_timestamp(state.updated_at)
        lines = [
            f"記事: {article.source.name}",
            f"退避ファイル: {state.autosave_path.name}",
            f"更新日時: {updated}",
            f"サイズ: {state.size_bytes} bytes",
            f"記事ファイルより新しい: {'はい' if state.newer_than_article else 'いいえ'}",
            "",
            "復元しても、保存ボタンを押すまで元の記事ファイルは変更されません。",
        ]
        text = ScrolledText(frame, wrap=tk.WORD, height=8, borderwidth=0)
        _style_text_widget(text)
        text.pack(fill=tk.BOTH, expand=True)
        self._set_text(text, "\n".join(lines))

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(10, 0))

        def restore() -> None:
            if self.restore_autosave_to_editor(article.source):
                win.destroy()

        def delete() -> None:
            if not messagebox.askyesno("自動退避削除", "この自動退避を削除しますか？"):
                return
            path = state.autosave_path
            try:
                clear_autosave(self.project_dir, article.source)
            except OSError as exc:
                self.notify("自動退避の削除に失敗しました", level="error")
                messagebox.showerror("自動退避エラー", str(exc))
                return
            self._ignored_autosaves.discard(path)
            self.notify("自動退避を削除しました", level="success")
            win.destroy()

        ttk.Button(buttons, text="復元して編集", style="Primary.TButton", command=restore).pack(side=tk.LEFT)
        ttk.Button(buttons, text="削除", command=delete).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="退避フォルダ", command=lambda: _open_path(state.autosave_path.parent)).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(buttons, text="閉じる", command=win.destroy).pack(side=tk.RIGHT)

    def confirm_editor_changes(self) -> bool:
        if not self.editor_dirty or not self.selected_article:
            return True
        self.autosave_editor_if_needed(notify_user=False)
        result = messagebox.askyesnocancel(
            "未保存の変更",
            "編集中の記事に未保存の変更があります。保存しますか？",
        )
        if result is None:
            return False
        if result:
            self.save_editor()
            return not self.editor_dirty
        self.editor_dirty = False
        return True

    def restore_current_selection(self) -> None:
        if not self.selected_article:
            return
        item_id = str(self.selected_article.source.resolve())
        if not self.article_tree.exists(item_id):
            return
        self._restoring_selection = True
        try:
            self.article_tree.selection_set(item_id)
            self.article_tree.focus(item_id)
        finally:
            self._restoring_selection = False

    def selected_or_warn(self, *, auto_select: bool = False) -> Article | None:
        if self.selected_article:
            return self.selected_article
        if auto_select:
            article = self.select_default_article()
            if article:
                self.notify(f"記事を自動選択しました: {article.source.name}", level="info")
                return article
        messagebox.showinfo("記事未選択", "記事を選択してください。")
        return None

    def select_default_article(self) -> Article | None:
        if not hasattr(self, "article_tree"):
            return None
        candidates: list[tuple[int, float, str, Article]] = []
        fallback: list[tuple[int, float, str, Article]] = []
        for item_id in self.article_tree.get_children():
            path = Path(item_id)
            try:
                article = load_article(path)
                mtime = path.stat().st_mtime
            except (ArticleError, OSError):
                continue
            entry = (_article_selection_rank(article), -mtime, item_id, article)
            fallback.append(entry)
            if (article.status or "draft") != "published":
                candidates.append(entry)
        pool = candidates or fallback
        if not pool:
            return None
        _rank, _mtime, item_id, article = sorted(pool, key=lambda item: (item[0], item[1]))[0]
        if self.article_tree.exists(item_id):
            self.article_tree.selection_set(item_id)
            self.article_tree.focus(item_id)
            self.article_tree.see(item_id)
        self._set_selected_article(article)
        return article


    def new_article(self) -> None:
        title = simpledialog.askstring("新規記事", "記事タイトル", parent=self)
        if not title:
            return
        raw_tags = simpledialog.askstring("新規記事", "タグ、カンマ区切り、省略可", parent=self) or ""
        tags = parse_tags(raw_tags) if raw_tags.strip() else self.settings.default_tags
        template = self.ask_article_template()
        if template is None:
            return
        try:
            path = create_article(title, articles_dir=self.articles_dir, tags=tags, template=template)
            if self.settings.default_status != "draft":
                set_article_status(path, self.settings.default_status)
            _open_path(path)
            self.refresh_articles()
            self.refresh_home()
            self.refresh_review_panel()
            self.notify(f"記事を作成しました: {path.name}", level="success")
        except OSError as exc:
            self.notify("記事作成に失敗しました", level="error")
            messagebox.showerror("作成エラー", str(exc))

    def create_practice_article_action(self) -> None:
        try:
            path = create_practice_article(articles_dir=self.articles_dir)
            _open_path(path)
            self.refresh_articles()
            self.refresh_home()
            self.refresh_review_panel()
            self.notify(f"練習記事を作成しました: {path.name}", level="success")
        except OSError as exc:
            self.notify("練習記事の作成に失敗しました", level="error")
            messagebox.showerror("作成エラー", str(exc))

    def create_starter_pack_action(self) -> None:
        if not messagebox.askyesno(
            "スターター一式",
            "サンプル記事3本、アイデア1件、匿名の予定ICSを追加します。\n\n"
            "既存の記事は上書きしません。続行しますか？",
        ):
            return
        try:
            result = create_starter_pack(self.project_dir, articles_dir=self.articles_dir)
        except (ArticleError, OSError) as exc:
            self.notify("スターター一式の作成に失敗しました", level="error")
            messagebox.showerror("スターター一式エラー", str(exc))
            return
        self.refresh_articles()
        self.refresh_ideas()
        self.refresh_schedule()
        self.refresh_home()
        self.refresh_first_run_panel()
        self.refresh_review_panel()
        self._set_text(self.diagnostics_text, format_starter_pack_result(result))
        self.notebook.select(self.diagnostics_tab)
        self.notify(
            f"スターター一式を確認しました: 作成 {len(result.articles)} / 既存 {len(result.skipped_articles)}",
            level="success",
        )

    def cleanup_starter_pack_action(self) -> None:
        preview = cleanup_starter_pack(self.project_dir, articles_dir=self.articles_dir, dry_run=True)
        if not preview.articles and not preview.idea_matched:
            self._set_text(self.diagnostics_text, format_starter_cleanup_result(preview))
            self.notebook.select(self.diagnostics_tab)
            self.notify("整理対象のスターター一式はありません", level="success")
            return
        if not messagebox.askyesno(
            "スターター整理",
            f"スターター由来の記事 {len(preview.articles)}件"
            f"{' と未使用アイデア1件' if preview.idea_matched else ''} を削除します。\n\n"
            "通常の記事や昇格済みアイデアは削除しません。続行しますか？",
        ):
            self._set_text(self.diagnostics_text, format_starter_cleanup_result(preview))
            self.notebook.select(self.diagnostics_tab)
            return
        try:
            result = cleanup_starter_pack(self.project_dir, articles_dir=self.articles_dir, dry_run=False)
        except OSError as exc:
            self.notify("スターター整理に失敗しました", level="error")
            messagebox.showerror("スターター整理エラー", str(exc))
            return
        self.refresh_articles()
        self.refresh_ideas()
        self.refresh_schedule()
        self.refresh_home()
        self.refresh_first_run_panel()
        self.refresh_review_panel()
        self._set_text(self.diagnostics_text, format_starter_cleanup_result(result))
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"スターター整理を実行しました: {len(result.articles)}記事", level="success")

    def ask_article_template(self) -> str | None:
        templates = list_article_templates()
        selected = {"value": templates[0][0]}

        win = tk.Toplevel(self)
        win.title("テンプレート選択")
        win.geometry("360x150")
        win.transient(self)
        win.grab_set()

        frame = ttk.Frame(win, padding=14)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="記事テンプレート").pack(anchor=tk.W)

        labels = [f"{key}: {label}" for key, label in templates]
        value = tk.StringVar(value=labels[0])
        combo = ttk.Combobox(frame, textvariable=value, values=labels, state="readonly")
        combo.pack(fill=tk.X, pady=(8, 12))
        combo.focus()

        def accept() -> None:
            index = labels.index(value.get()) if value.get() in labels else 0
            selected["value"] = templates[index][0]
            win.destroy()

        def cancel() -> None:
            selected["value"] = None
            win.destroy()

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="作成へ進む", style="Primary.TButton", command=accept).pack(side=tk.LEFT)
        ttk.Button(buttons, text="キャンセル", command=cancel).pack(side=tk.RIGHT)
        win.protocol("WM_DELETE_WINDOW", cancel)
        self.wait_window(win)
        return selected["value"]

    def open_selected_file(self) -> None:
        article = self.selected_or_warn()
        if article:
            _open_path(article.source)
            self.notify(f"ファイルを開きました: {article.source.name}")

    def edit_article_metadata(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        if not self.confirm_editor_changes():
            return

        article = load_article(article.source)
        win = tk.Toplevel(self)
        win.title("メタ情報編集")
        win.geometry("560x300")
        win.minsize(520, 280)
        win.transient(self)
        win.grab_set()

        frame = ttk.Frame(win, padding=14)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text=article.source.name, style="Muted.TLabel").pack(anchor=tk.W, pady=(0, 8))

        form = ttk.Frame(frame, style="Surface.TFrame", padding=12)
        form.pack(fill=tk.X)
        title_var = tk.StringVar(value=article.title)
        summary_var = tk.StringVar(value=article.summary)
        tags_var = tk.StringVar(value=", ".join(article.tags))
        cover_var = tk.StringVar(value=article.cover)
        self._form_row(form, 0, "タイトル", ttk.Entry(form, textvariable=title_var))
        self._form_row(form, 1, "概要", ttk.Entry(form, textvariable=summary_var))
        self._form_row(form, 2, "タグ", ttk.Entry(form, textvariable=tags_var))
        self._form_row(form, 3, "cover", ttk.Entry(form, textvariable=cover_var))
        form.columnconfigure(1, weight=1)

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(12, 0))

        def save() -> None:
            title = title_var.get().strip()
            if not title:
                messagebox.showinfo("メタ情報", "タイトルを入力してください。")
                return
            try:
                create_revision(self.project_dir, article.source, label="before-meta")
                update_article_metadata(
                    article.source,
                    title=title,
                    summary=summary_var.get(),
                    tags=parse_tags(tags_var.get()),
                    cover=cover_var.get(),
                )
                self._set_selected_article(load_article(article.source))
                self.refresh_articles()
                self.refresh_schedule()
                self.refresh_home()
                self.refresh_review_panel()
                self.run_check_all(show_popup=False)
            except (OSError, ArticleError) as exc:
                self.notify("メタ情報の保存に失敗しました", level="error")
                messagebox.showerror("メタ情報エラー", str(exc))
                return
            self.notify("メタ情報を保存しました", level="success")
            win.destroy()

        ttk.Button(buttons, text="保存", style="Primary.TButton", command=save).pack(side=tk.LEFT)
        ttk.Button(buttons, text="キャンセル", command=win.destroy).pack(side=tk.RIGHT)
        win.protocol("WM_DELETE_WINDOW", win.destroy)

    def save_editor(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        text = self.editor.get("1.0", "end-1c")
        try:
            if article.source.exists() and _read_text(article.source) != text:
                create_revision(self.project_dir, article.source)
            write_text_atomic(article.source, text)
        except OSError as exc:
            self.notify("記事の保存に失敗しました", level="error")
            messagebox.showerror("保存エラー", str(exc))
            return
        state = autosave_state(self.project_dir, article.source)
        try:
            clear_autosave(self.project_dir, article.source)
        except OSError as exc:
            self.notify(f"記事は保存しましたが自動退避の削除に失敗しました: {exc}", level="warning")
        self._ignored_autosaves.discard(state.autosave_path)
        self.editor_dirty = False
        self._last_autosave_text = ""
        self.refresh_articles()
        self.refresh_schedule()
        self.refresh_home()
        self.refresh_review_panel()
        self.run_check_all(show_popup=False)
        self.notify(f"記事を保存しました: {article.source.name}", level="success")

    def show_selected_history(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        _show_text_window(self, "保存履歴", format_revisions(list_revisions(self.project_dir, article.source)))

    def restore_selected_history(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        revisions = list_revisions(self.project_dir, article.source)
        if not revisions:
            messagebox.showinfo("保存履歴", "保存履歴はありません。")
            return

        win = tk.Toplevel(self)
        win.title("保存履歴から復元")
        win.geometry("860x520")
        win.transient(self)
        win.grab_set()

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(frame)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        right = ttk.Frame(frame)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        listbox = tk.Listbox(left, width=44, height=18)
        listbox.pack(fill=tk.Y, expand=False)
        for revision in revisions:
            listbox.insert(tk.END, f"{revision.created_at} | {revision.path.name}")

        preview = ScrolledText(right, wrap=tk.WORD, borderwidth=0)
        _style_text_widget(preview)
        preview.pack(fill=tk.BOTH, expand=True)
        preview.configure(state=tk.DISABLED)

        def set_preview(index: int) -> None:
            text = revisions[index].path.read_text(encoding="utf-8", errors="replace")
            self._set_text(preview, text[:12000])

        def on_select(_event=None) -> None:
            selection = listbox.curselection()
            if selection:
                set_preview(selection[0])

        def restore() -> None:
            selection = listbox.curselection()
            if not selection:
                messagebox.showinfo("保存履歴", "復元する履歴を選択してください。")
                return
            revision = revisions[selection[0]]
            if not messagebox.askyesno("保存履歴から復元", f"{revision.path.name} を復元しますか？"):
                return
            try:
                restore_revision(self.project_dir, article.source, revision.path)
            except (OSError, ValueError) as exc:
                self.notify("保存履歴の復元に失敗しました", level="error")
                messagebox.showerror("復元エラー", str(exc))
                return
            win.destroy()
            self._set_selected_article(load_article(article.source))
            self.refresh_articles()
            self.refresh_schedule()
            self.refresh_home()
            self.run_check_all(show_popup=False)
            self.notify(f"保存履歴を復元しました: {article.source.name}", level="success")

        listbox.bind("<<ListboxSelect>>", on_select)
        listbox.selection_set(0)
        set_preview(0)

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
        ttk.Button(buttons, text="復元", style="Primary.TButton", command=restore).pack(side=tk.LEFT)
        ttk.Button(buttons, text="閉じる", command=win.destroy).pack(side=tk.RIGHT)

    def open_selected_history_folder(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        path = revision_dir(self.project_dir, article.source)
        path.mkdir(parents=True, exist_ok=True)
        _open_path(path)

    def insert_image_into_editor(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        path = filedialog.askopenfilename(
            parent=self,
            title="画像を選択",
            filetypes=(
                ("Images", "*.png;*.jpg;*.jpeg;*.gif;*.webp;*.svg"),
                ("All files", "*.*"),
            ),
        )
        if not path:
            return
        alt = simpledialog.askstring("画像の代替テキスト", "altテキスト、省略可", parent=self) or ""
        optimize = messagebox.askyesno(
            "画像最適化",
            f"画像を最大{self.settings.image_max_width}px・品質{self.settings.image_quality}で最適化しますか？\n"
            "Pillow未導入の場合は案内が表示されます。",
            default=messagebox.YES if self.settings.image_optimize_by_default else messagebox.NO,
        )
        try:
            imported = import_image_for_article(
                article.source,
                Path(path),
                alt_text=alt,
                optimize=optimize,
                max_width=self.settings.image_max_width,
                quality=self.settings.image_quality,
            )
        except ArticleError as exc:
            self.notify("画像の取り込みに失敗しました", level="error")
            messagebox.showerror("画像取り込みエラー", str(exc))
            return
        self.editor.insert(tk.INSERT, f"\n\n{imported.markdown}\n")
        self.editor_dirty = True
        if messagebox.askyesno("カバー画像", "この画像を記事のcoverにも設定しますか？"):
            self.save_editor()
            if not self.editor_dirty:
                try:
                    create_revision(self.project_dir, article.source, label="before-cover")
                    set_article_cover(article.source, imported.relative_path)
                    self._set_selected_article(load_article(article.source))
                    self.refresh_articles()
                except (OSError, ArticleError) as exc:
                    self.notify("cover設定に失敗しました", level="error")
                    messagebox.showerror("cover設定エラー", str(exc))
                    return
        self.notify(f"画像を挿入しました: {imported.relative_path}", level="success")

    def reload_editor(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        try:
            self._set_selected_article(load_article(article.source))
        except ArticleError as exc:
            self._set_editor(_read_text(article.source))
            self.notify("記事の再読み込みに失敗しました", level="error")
            messagebox.showerror("再読み込みエラー", str(exc))
            return
        self.notify("記事を再読み込みしました", level="success")

    def on_close(self) -> None:
        self.autosave_editor_if_needed(notify_user=False)
        if self.confirm_editor_changes():
            if self._autosave_job:
                self.after_cancel(self._autosave_job)
                self._autosave_job = None
            self.destroy()

    def open_helper(self) -> None:
        article = self.selected_or_warn(auto_select=True)
        if not article:
            return
        if not self.confirm_helper_safety(article):
            return
        try:
            path = open_manual_post_helper(
                article,
                append_tags=self.settings.append_tags_by_default,
                output_dir=self.output_dir,
                open_note=self.settings.open_note_with_helper,
                open_helper=True,
            )
            self.notify(f"投稿ヘルパーを開きました: {path.name}", level="success")
        except OSError as exc:
            self.notify("投稿ヘルパーの起動に失敗しました", level="error")
            messagebox.showerror("ヘルパーエラー", str(exc))

    def open_note_login_action(self) -> None:
        webbrowser.open(NOTE_LOGIN_URL)
        self.notify("普段のブラウザでnoteログインを開きました", level="info")

    def show_note_login_safety_action(self) -> None:
        self._set_text(self.help_text, _note_login_safety_text())
        self.notebook.select(self.help_tab)
        self.notify("noteログイン安全ガイドを表示しました", level="info")

    def confirm_helper_safety(self, article: Article) -> bool:
        report = self.refresh_publish_ready_panel(article=article, show_popup=False, smoke_helper=False)
        if report is None:
            self.notebook.select(self.article_tab)
            self.notify("投稿前チェックを通せないためヘルパーを開きません", level="error")
            return False
        if report.status == "pass":
            return True

        self._set_check_text(format_publish_ready_report(report))
        self.notebook.select(self.article_tab)
        if report.status == "fail":
            answer = messagebox.askyesno(
                "投稿前NG",
                "投稿前チェックにNGがあります。\n\n"
                "先に投稿準備パネルの「次を実行」で修正することをおすすめします。\n"
                "それでも投稿ヘルパーを開きますか？",
                parent=self,
            )
            if not answer:
                self.notify("投稿ヘルパーを開かずに止めました", level="warning")
            return bool(answer)

        answer = messagebox.askyesno(
            "投稿前確認",
            "投稿前チェックに確認項目があります。\n\n"
            "内容を確認したうえで投稿ヘルパーを開きますか？",
            parent=self,
        )
        if not answer:
            self.notify("確認項目を見直してください", level="warning")
        return bool(answer)

    def open_dashboard(self) -> None:
        try:
            path = open_manual_dashboard(
                self.articles_dir,
                pattern=self.settings.article_glob,
                append_tags=self.settings.append_tags_by_default,
                output_dir=self.output_dir,
            )
            self.notify(f"ダッシュボードを開きました: {path.name}", level="success")
        except ArticleError as exc:
            self.notify("記事がありません", level="warning")
            messagebox.showinfo("記事なし", str(exc))

    def check_selected(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        report = inspect_article(article, append_tags=self.settings.append_tags_by_default)
        text = format_reports([report])
        self._set_check_text(text)
        self.notebook.select(self.check_tab)
        self.notify("選択記事をチェックしました", level="success" if report.ok else "warning")

    def check_selected_to_tab(self) -> None:
        self.check_selected()

    def publish_ready_selected_to_tab(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        report = self.refresh_publish_ready_panel(article=article, smoke_helper=True)
        if report is None:
            self.notify("投稿準備レポートを作成できません", level="error")
            return
        self._set_check_text(format_publish_ready_report(report))
        self.notebook.select(self.check_tab)
        if report.helper_path:
            self.notify(
                f"投稿準備レポートを表示しました: {report.helper_path.name}",
                level=self._publish_ready_notify_level(report.status),
            )
        else:
            self.notify("投稿準備レポートを表示しました", level=self._publish_ready_notify_level(report.status))

    def improvement_plan_selected_to_tab(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        try:
            plan = build_improvement_plan(
                article.source,
                append_tags=self.settings.append_tags_by_default,
            )
        except ArticleError as exc:
            self.notify("改善プランを作成できません", level="error")
            messagebox.showerror("改善プランエラー", str(exc))
            return
        self._last_improvement_plan = plan
        if hasattr(self, "article_focus_summary_var"):
            self._render_article_focus_panel(plan)
        self.refresh_review_panel()
        if hasattr(self, "publish_ready_tree"):
            self._last_publish_ready_report = plan.publish_ready
            self._render_publish_ready_panel(plan.publish_ready)
        self._set_check_text(format_improvement_plan(plan))
        self.notebook.select(self.check_tab)
        self.notify("改善プランを表示しました", level=self._improvement_plan_notify_level(plan))

    def publish_queue_to_tab(self) -> None:
        report = build_publish_queue(self.project_dir)
        self._last_publish_queue_report = report
        self._set_check_text(format_publish_queue_report(report))
        self.notebook.select(self.check_tab)
        if not report.entries:
            self.notify("投稿キューに記事がありません", level="warning")
        elif has_publish_queue_blockers(report):
            self.notify("投稿キューに修正が必要な記事があります", level="warning")
        elif report.check_count:
            self.notify("投稿キューに確認項目があります", level="warning")
        else:
            self.notify("投稿キューを表示しました", level="success")

    def check_images_selected(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        refs = collect_article_images(article)
        self._set_check_text(format_image_report(refs))
        self.notebook.select(self.check_tab)
        self.notify("画像チェックを実行しました", level="warning" if missing_images(refs) else "success")

    def check_images_all(self) -> None:
        try:
            refs = inspect_images_path(self.articles_dir, pattern=self.settings.article_glob)
        except ArticleError as exc:
            self._set_check_text(str(exc))
            messagebox.showinfo("記事なし", str(exc))
            return
        self._set_check_text(format_image_report(refs))
        self.notebook.select(self.check_tab)
        self.notify("画像チェックを実行しました", level="warning" if missing_images(refs) else "success")

    def review_selected_to_tab(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        review = review_article(article, append_tags=self.settings.append_tags_by_default)
        self.refresh_review_panel()
        self._set_check_text(format_review_report([review]))
        self.notebook.select(self.check_tab)
        self.notify("選択記事レビューを実行しました", level="warning" if review.needs_fix else "success")

    def _improvement_plan_notify_level(self, plan: ImprovementPlan) -> str:
        if has_improvement_plan_blockers(plan):
            return "error"
        if plan.status == "check":
            return "warning"
        return "success"

    def review_all_to_tab(self) -> None:
        reviews = self.refresh_review_panel(show_popup=False, select_tab=True)
        if not reviews:
            self._set_check_text("記事レビュー対象がありません。")
            return
        self._set_check_text(format_review_report(reviews))
        self.notebook.select(self.check_tab)
        self.notify("レビュー一覧を更新しました", level="warning" if has_review_blockers(reviews) else "success")

    def run_check_all(self, show_popup: bool = True) -> None:
        try:
            reports = inspect_path(
                self.articles_dir,
                pattern=self.settings.article_glob,
                append_tags=self.settings.append_tags_by_default,
            )
        except ArticleError as exc:
            self._set_check_text(str(exc))
            if show_popup:
                messagebox.showinfo("記事なし", str(exc))
            return
        text = format_reports(reports)
        self._set_check_text(text)
        has_issue = any(report.issues for report in reports)
        if show_popup:
            self.notebook.select(self.check_tab)
            self.notify("全体チェックを実行しました", level="warning" if has_issue else "success")

    def copy_selected(self, part: str) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        if part == "body":
            value = body_with_tags(article) if self.settings.append_tags_by_default else article.body
            label = "本文"
        elif part == "tags":
            value = hashtags_for(article)
            label = "タグ"
        else:
            value = text_bundle(article, append_tags=self.settings.append_tags_by_default)
            label = "全文"
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update()
        self.notify(f"{label}をコピーしました", level="success")

    def save_status(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        try:
            set_article_status(article.source, self.status_var.get())
            self.refresh_articles()
            self.refresh_schedule()
            self.refresh_home()
            self.refresh_review_panel()
            self.notify("状態を保存しました", level="success")
        except ArticleError as exc:
            self.notify("状態の保存に失敗しました", level="error")
            messagebox.showerror("状態エラー", str(exc))

    def save_schedule(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        value = self.schedule_var.get().strip()
        if not value:
            messagebox.showinfo("公開予定", "YYYY-MM-DD HH:MM の形式で入力してください。")
            return
        try:
            set_article_schedule(article.source, value)
            self.refresh_articles()
            self.refresh_schedule()
            self.refresh_home()
            self.refresh_review_panel()
            self.notify("公開予定を保存しました", level="success")
        except ArticleError as exc:
            self.notify("公開予定の保存に失敗しました", level="error")
            messagebox.showerror("公開予定エラー", str(exc))

    def clear_schedule(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        clear_article_schedule(article.source)
        self.refresh_articles()
        self.refresh_schedule()
        self.refresh_home()
        self.refresh_review_panel()
        self.notify("公開予定を削除しました", level="success")

    def mark_published(self) -> None:
        article = self.selected_or_warn()
        if not article:
            return
        mark_article_published(article.source, url=self.url_var.get().strip())
        self.refresh_articles()
        self.refresh_schedule()
        self.refresh_home()
        self.refresh_review_panel()
        self.notify("公開済みにしました", level="success")

    def refresh_ideas(self) -> None:
        if not hasattr(self, "ideas_tree"):
            return
        self.ideas_tree.delete(*self.ideas_tree.get_children())
        self.idea_ids.clear()
        for idea in load_ideas(self.project_dir):
            state = "done" if idea.promoted_to else "open"
            values = (idea.id, state, idea.title, ", ".join(idea.tags), idea.note)
            self.ideas_tree.insert("", tk.END, values=values, tags=(state,))
            self.idea_ids.append(idea.id)

    def add_idea_dialog(self) -> None:
        title = simpledialog.askstring("アイデア追加", "アイデア", parent=self)
        if not title:
            return
        note = simpledialog.askstring("アイデア追加", "メモ、省略可", parent=self) or ""
        raw_tags = simpledialog.askstring("アイデア追加", "タグ、カンマ区切り、省略可", parent=self) or ""
        tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
        try:
            idea = add_idea(self.project_dir, title, note=note, tags=tags)
            self.refresh_ideas()
            self.notify(f"アイデアを追加しました: {idea.title}", level="success")
        except ArticleError as exc:
            self.notify("アイデア追加に失敗しました", level="error")
            messagebox.showerror("アイデア追加エラー", str(exc))

    def promote_selected_idea(self) -> None:
        selection = self.ideas_tree.selection()
        if not selection:
            messagebox.showinfo("アイデア未選択", "アイデアを選択してください。")
            return
        values = self.ideas_tree.item(selection[0], "values")
        idea_id = int(values[0])
        try:
            path = promote_idea(self.project_dir, idea_id, articles_dir=self.articles_dir)
            _open_path(path)
            self.refresh_ideas()
            self.refresh_articles()
            self.refresh_home()
            self.notify(f"アイデアを記事化しました: {path.name}", level="success")
        except ArticleError as exc:
            self.notify("記事化に失敗しました", level="error")
            messagebox.showerror("記事化エラー", str(exc))

    def show_ideas_text(self) -> None:
        _show_text_window(self, "アイデア一覧", format_ideas(self.project_dir, include_done=True))

    def refresh_schedule(self) -> None:
        if not hasattr(self, "schedule_text"):
            return
        text = (
            format_plan(self.articles_dir, pattern=self.settings.article_glob)
            + "\n\n"
            + format_calendar(self.articles_dir, pattern=self.settings.article_glob, days=30)
        )
        self._set_text(self.schedule_text, text)

    def refresh_home(self) -> None:
        if not hasattr(self, "home_text"):
            return
        articles = []
        for path in sorted(self.articles_dir.glob(self.settings.article_glob)):
            try:
                articles.append(load_article(path))
            except ArticleError:
                continue
        counts = {status: 0 for status in STATUS_ORDER}
        for article in articles:
            counts[article.status if article.status in counts else "draft"] += 1
        readiness = run_readiness(self.project_dir)
        quickstart = run_quickstart(self.project_dir)
        action_plan = build_action_plan(self.project_dir, readiness=readiness, quickstart=quickstart)
        self.kpi_vars["準備度"].set(f"{readiness.score}%")
        self.kpi_vars["記事"].set(str(len(articles)))
        self.kpi_vars["下書き"].set(str(counts["draft"]))
        self.kpi_vars["準備OK"].set(str(counts["ready"]))
        self.kpi_vars["予定"].set(str(counts["scheduled"]))
        self.kpi_vars["公開済み"].set(str(counts["published"]))
        next_actions = self._home_next_actions(action_plan)
        if hasattr(self, "home_status_badge"):
            badge_text, badge_bg, badge_fg = _home_overview_badge(readiness.score, action_plan.status)
            self.home_status_badge.configure(text=badge_text, bg=badge_bg, fg=badge_fg)
        if hasattr(self, "home_updated_var"):
            self.home_updated_var.set(f"更新 {datetime.now().strftime('%H:%M')}")
        if hasattr(self, "home_focus_var"):
            self._home_primary_step = action_plan.steps[0] if action_plan.steps else None
            self.home_focus_var.set(self._format_home_focus(action_plan))
            if hasattr(self, "home_primary_button_var"):
                self.home_primary_button_var.set(_home_primary_button_label(self._home_primary_step))
        self._render_home_action_plan(action_plan)
        self._refresh_home_sales_summary()
        first_run_report = run_first_run_checklist(self.project_dir)
        self._refresh_home_first_run_summary(first_run_report)
        self._refresh_home_progress_lane(readiness, quickstart, action_plan, articles, counts)
        self._refresh_home_gui_log_status()
        self._refresh_home_snapshot_strip(readiness, action_plan, first_run_report)
        self._refresh_home_reports()

        lines = [
            "次にやること",
            "",
            f"現在の準備度: {readiness.score}/100",
            f"クイック確認: {quickstart.score}/100",
            f"状態: {action_plan.status}",
            "",
            "優先アクション",
            *[f"{index}. {action}" for index, action in enumerate(next_actions, start=1)],
            "",
            "通常フロー",
            "1. 下書き記事を書き進める",
            "2. 準備OKの記事を公開予定に入れる",
            "3. 投稿ヘルパーでnoteへ貼り付ける",
            "4. 公開後URLを保存する",
            "",
            format_calendar(self.articles_dir, pattern=self.settings.article_glob, days=14),
        ]
        self._set_text(self.home_text, "\n".join(lines))

    def _refresh_home_progress_lane(self, readiness, quickstart, action_plan, articles, counts) -> None:
        if not hasattr(self, "home_progress_summary_var"):
            return
        quick_items = {item.name: item for item in quickstart.items}
        readiness_items = {item.name: item for item in readiness.items}
        total_articles = len(articles)
        prepared_articles = counts["ready"] + counts["scheduled"] + counts["published"]
        post_candidates = counts["ready"] + counts["scheduled"]

        setup_item = quick_items.get("setup")
        setup_state = _home_progress_state_from_status(setup_item.status if setup_item else "info")
        setup_text = f"{quickstart.score}/100"

        if total_articles == 0:
            article_state = "warn"
            article_text = "未作成"
        elif prepared_articles:
            article_state = "ok" if prepared_articles == total_articles else "info"
            article_text = f"{prepared_articles}/{total_articles}準備"
        else:
            article_state = "warn"
            article_text = f"下書き {total_articles}"

        review_item = quick_items.get("article review") or readiness_items.get("article content")
        review_state = "warn" if total_articles == 0 else _home_progress_state_from_status(
            review_item.status if review_item else "info"
        )
        review_text = _home_progress_review_text(review_item.status if review_item else "info", total_articles)

        if post_candidates:
            publish_state = "ok"
            publish_text = f"候補 {post_candidates}"
        elif counts["published"]:
            publish_state = "info"
            publish_text = f"公開済み {counts['published']}"
        elif total_articles:
            publish_state = "warn"
            publish_text = "候補なし"
        else:
            publish_state = "info"
            publish_text = "記事待ち"

        sales_status = self.home_sales_status_var.get() if hasattr(self, "home_sales_status_var") else ""
        sales_state = "ok" if "READY TO VERIFY" in sales_status else "warn"
        sales_text = "検証待ち" if sales_state == "ok" else "残件あり"

        support_state, support_text = self._home_support_send_readiness()
        stages = {
            "setup": setup_state,
            "article": article_state,
            "review": review_state,
            "publish": publish_state,
            "sales": sales_state,
            "support": support_state,
        }
        self._set_home_progress_stage("setup", setup_state, setup_text)
        self._set_home_progress_stage("article", article_state, article_text)
        self._set_home_progress_stage("review", review_state, review_text)
        self._set_home_progress_stage("publish", publish_state, publish_text)
        self._set_home_progress_stage("sales", sales_state, sales_text)
        self._set_home_progress_stage("support", support_state, support_text)

        next_title = action_plan.steps[0].title if action_plan.steps else "出荷前チェック"
        self.home_progress_summary_var.set(_home_progress_summary(stages, next_title))

    def _set_home_progress_stage(self, key: str, state: str, text: str) -> None:
        value = getattr(self, "home_progress_vars", {}).get(key)
        pill = getattr(self, "home_progress_pills", {}).get(key)
        rail = getattr(self, "home_progress_rails", {}).get(key)
        if value is not None:
            value.set(text)
        if pill is not None:
            pill_text, bg, fg = _home_sales_indicator_style(state)
            pill.configure(text=pill_text, bg=bg, fg=fg)
        if rail is not None:
            rail.configure(bg=_home_state_accent_color(state))

    def _refresh_home_snapshot_strip(self, readiness, action_plan, first_run_report: FirstRunReport) -> None:
        if not hasattr(self, "home_snapshot_vars"):
            return
        next_step = action_plan.steps[0] if action_plan.steps else None
        next_title = next_step.title if next_step else "出荷前チェック"
        first_run_summary, _next_text = _home_first_run_summary(first_run_report)
        values = _home_snapshot_values(
            readiness_score=readiness.score,
            action_status=action_plan.status,
            next_title=next_title,
            first_run_summary=first_run_summary,
            gui_log_text=self.home_gui_log_var.get() if hasattr(self, "home_gui_log_var") else "",
            sales_status=self.home_sales_status_var.get() if hasattr(self, "home_sales_status_var") else "",
            buyer_send_summary=self.home_buyer_send_var.get() if hasattr(self, "home_buyer_send_var") else "",
        )
        next_state = _home_snapshot_next_state(getattr(next_step, "severity", "") if next_step else "")
        startup_state = _home_snapshot_worst_state(
            _home_progress_state_from_status(first_run_report.status),
            _home_gui_log_status(gui_error_log_path(self.project_dir))[0],
        )
        sales_state = "ok" if "READY TO VERIFY" in values["sales"] else "warn"
        if "ZIP検証NG" in values["sales"] or "NG" in values["sales"]:
            sales_state = "fail"
        states = {
            "readiness": _home_snapshot_readiness_state(readiness.score),
            "next": next_state,
            "startup": startup_state,
            "sales": sales_state,
        }
        for key, text in values.items():
            self._set_home_snapshot_item(key, states.get(key, "info"), text)

    def _set_home_snapshot_item(self, key: str, state: str, text: str) -> None:
        value = getattr(self, "home_snapshot_vars", {}).get(key)
        pill = getattr(self, "home_snapshot_pills", {}).get(key)
        rail = getattr(self, "home_snapshot_rails", {}).get(key)
        if value is not None:
            value.set(text)
        if pill is not None:
            pill_text, bg, fg = _home_sales_indicator_style(state)
            pill.configure(text=pill_text, bg=bg, fg=fg)
        if rail is not None:
            rail.configure(bg=_home_state_accent_color(state))

    def open_home_progress_stage(self, key: str) -> None:
        actions = {
            "setup": self.run_first_run_to_tab,
            "article": lambda: self._select_home_progress_tab(self.article_tab, "記事タブを開きました"),
            "review": self.review_all_to_tab,
            "publish": self.publish_queue_to_tab,
            "sales": self.run_sales_plan_to_tab,
            "support": self.show_support_send_panel_action,
        }
        action = actions.get(key)
        if action is None:
            self.run_action_plan_to_tab()
            return
        action()

    def _refresh_home_first_run_summary(self, report: FirstRunReport) -> None:
        if not hasattr(self, "home_first_run_var"):
            return
        verdict = _first_run_verdict(report.status)
        bg, fg = _first_run_status_colors(report.status)
        self.home_first_run_status_pill.configure(text=verdict, bg=bg, fg=fg)
        summary, next_text = _home_first_run_summary(report)
        self.home_first_run_var.set(summary)
        self.home_first_run_next_var.set(next_text)

    def open_home_first_run_status(self) -> None:
        self.refresh_first_run_panel(select_tab=True)
        self.notify("初回チェックの未完了項目を開きました", level="info")

    def _select_home_progress_tab(self, tab: ttk.Frame, message: str) -> None:
        self.notebook.select(tab)
        self.notify(message, level="info")

    def _refresh_home_reports(self) -> None:
        if not hasattr(self, "home_reports_tree"):
            return
        self._home_report_paths = {}
        for child in self.home_reports_tree.get_children():
            self.home_reports_tree.delete(child)

        items = self._latest_home_report_items()
        if not items:
            self.home_reports_var.set(
                "まだ保存レポートがありません。診断レポート、問い合わせ一式、復旧セット、販売前一括チェックを実行するとここに並びます。"
            )
            return

        for index, (label, path) in enumerate(items[:8]):
            item_id = f"report-{index}"
            status = _home_report_status(label, path)
            self._home_report_paths[item_id] = (label, path)
            self.home_reports_tree.insert(
                "",
                tk.END,
                iid=item_id,
                values=(
                    label,
                    status,
                    _format_mtime(path),
                    _relative_parent_label(self.project_dir, path),
                    path.name,
                ),
                tags=(_home_report_status_tag(status),),
            )
        first_label, first_path = items[0]
        first_status = _home_report_status(first_label, first_path)
        self.home_reports_var.set(_home_report_summary("最新", first_label, first_path, first_status))

    def _configure_home_reports_tree_tags(self) -> None:
        self.home_reports_tree.tag_configure("ok", background="#dff3ed", foreground="#105f54")
        self.home_reports_tree.tag_configure("check", background="#e7f0ff", foreground="#174ea6")
        self.home_reports_tree.tag_configure("fail", background="#ffe2df", foreground="#8b2119")
        self.home_reports_tree.tag_configure("missing", background="#f3f4f6", foreground="#667085")

    def on_select_home_report(self) -> None:
        item = self._selected_home_report()
        if item is None:
            return
        label, path = item
        status = _home_report_status(label, path)
        self.home_reports_var.set(_home_report_summary("選択", label, path, status))

    def _refresh_home_gui_log_status(self) -> None:
        if not hasattr(self, "home_gui_log_var"):
            return
        state, text = _home_gui_log_status(gui_error_log_path(self.project_dir))
        pill_text, bg, fg = _home_sales_indicator_style(state)
        self.home_gui_log_status_pill.configure(text=pill_text, bg=bg, fg=fg)
        self.home_gui_log_var.set(text)

    def _latest_home_report_items(self) -> list[tuple[str, Path]]:
        groups = [
            ("問い合わせZIP", list_support_bundles(self.project_dir)),
            ("復旧レポート", list_recovery_kit_reports(self.project_dir)),
            ("診断ZIP", list_diagnostic_reports(self.project_dir)),
            ("配布ZIP", list_releases(self.project_dir)),
            ("掲載画像", list_sales_screenshot_packs(self.project_dir)),
            ("掲載キット", list_sales_listing_packages(self.project_dir)),
            ("購入者ZIP", list_buyer_delivery_packages(self.project_dir)),
            ("購入者送付文", list_buyer_delivery_messages(self.project_dir)),
            ("送付記録", list_seller_delivery_receipts(self.project_dir)),
            ("販売直前", list_sales_launch_checklists(self.project_dir)),
            ("販売確認", list_sales_launch_confirmations(self.project_dir)),
            ("一括チェック", _list_release_check_reports(self.project_dir)),
            ("投稿キュー", list_publish_queue_reports(self.project_dir)),
            ("E2E確認", list_workflow_smoke_reports(self.project_dir)),
            ("運用サマリー", list_overview_reports(self.project_dir)),
            ("記事CSV", list_reports(self.project_dir)),
        ]
        items = [(label, paths[0]) for label, paths in groups if paths]
        return sorted(items, key=lambda item: _safe_mtime(item[1]), reverse=True)

    def _selected_home_report(self) -> tuple[str, Path] | None:
        if not hasattr(self, "home_reports_tree"):
            return None
        selection = self.home_reports_tree.selection()
        if selection:
            item = self._home_report_paths.get(selection[0])
            if item is not None:
                return item
        items = self._latest_home_report_items()
        return items[0] if items else None

    def show_selected_home_report_action(self) -> None:
        item = self._selected_home_report()
        if item is None:
            messagebox.showinfo(
                "直近レポート",
                "まだ保存レポートがありません。診断レポート、問い合わせ一式、復旧セットなどを実行してください。",
            )
            self.notify("直近レポートはまだありません", level="warning")
            return
        label, path = item
        if not path.exists():
            self.notify("選択したレポートが見つかりません", level="warning")
            self._refresh_home_reports()
            return
        text = self._format_home_report_preview(label, path)
        self._set_text(self.diagnostics_text, text)
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"直近レポートを表示しました: {path.name}", level="success")

    def open_selected_home_report_location_action(self) -> None:
        item = self._selected_home_report()
        if item is None:
            messagebox.showinfo("直近レポート", "まだ保存レポートがありません。")
            self.notify("直近レポートはまだありません", level="warning")
            return
        _label, path = item
        if not path.exists():
            self.notify("選択したレポートが見つかりません", level="warning")
            self._refresh_home_reports()
            return
        _open_path(path.parent)
        self.notify(f"直近レポートの場所を開きました: {path.name}", level="success")

    def copy_selected_home_report_path_action(self) -> None:
        item = self._selected_home_report()
        if item is None:
            messagebox.showinfo("直近レポート", "まだ保存レポートがありません。")
            self.notify("直近レポートはまだありません", level="warning")
            return
        _label, path = item
        if not path.exists():
            self.notify("選択したレポートが見つかりません", level="warning")
            self._refresh_home_reports()
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(str(path.resolve()))
            self.update_idletasks()
        except tk.TclError as exc:
            self.notify("直近レポートのパスをコピーできませんでした", level="error")
            messagebox.showerror("直近レポート", str(exc))
            return
        self.notify(f"直近レポートのパスをコピーしました: {path.name}", level="success")

    def _format_home_report_preview(self, label: str, path: Path) -> str:
        header = [
            f"直近レポート: {label}",
            f"file: {path.name}",
            f"folder: {_relative_parent_label(self.project_dir, path)}",
            f"updated: {_format_mtime(path)}",
            f"size: {_format_file_size(path)}",
            "",
        ]
        if label == "問い合わせZIP":
            return "\n".join([*header, format_support_bundle_verification(path, verify_support_bundle(path))])
        if label == "配布ZIP":
            return "\n".join([*header, format_release_verification(path, verify_release_package(path))])
        if label == "購入者ZIP":
            return "\n".join(
                [*header, format_buyer_delivery_package_verification(path, verify_buyer_delivery_package(path))]
            )
        if label == "掲載キット":
            return "\n".join([*header, format_sales_listing_verification(path, verify_sales_listing_kit(path))])
        if path.suffix.lower() == ".zip":
            return "\n".join([*header, *_format_zip_report_summary(path)])
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError as exc:
            return "\n".join([*header, f"[NG] レポートを読み取れません: {exc}"])
        if len(text) > 40000:
            text = text[-40000:]
            header.append("[INFO] ファイルが長いため末尾40000文字を表示します。")
            header.append("")
        return "\n".join([*header, text or "(empty)"])

    def _refresh_home_sales_summary(self) -> None:
        if not hasattr(self, "home_sales_status_var"):
            return
        settings = self.settings
        complete, total = commercial_setup_completion(settings)
        missing = commercial_setup_missing_fields(settings)
        warnings = commercial_setup_warnings(settings)
        releases = list_releases(self.project_dir)
        handoffs = list_sales_handoffs(self.project_dir)
        buyer_packages = list_buyer_delivery_packages(self.project_dir)
        buyer_messages = list_buyer_delivery_messages(self.project_dir)
        seller_receipts = list_seller_delivery_receipts(self.project_dir)
        materials = list_sales_materials(self.project_dir)
        screenshot_packs = list_sales_screenshot_packs(self.project_dir)
        listing_kits = list_sales_listing_kits(self.project_dir)
        listing_packages = list_sales_listing_packages(self.project_dir)
        release_checks = _list_release_check_reports(self.project_dir)
        latest_buyer_package = buyer_packages[0] if buyer_packages else None
        latest_buyer_message = buyer_messages[0] if buyer_messages else None
        latest_seller_receipt = seller_receipts[0] if seller_receipts else None
        support_state, support_text = self._home_support_send_readiness()
        artifact_remaining = sum(
            1
            for paths in (
                releases,
                materials,
                screenshot_packs,
                listing_packages,
                handoffs,
                buyer_packages,
                buyer_messages,
            )
            if not paths
        )
        buyer_package_errors = (
            verify_buyer_delivery_package(latest_buyer_package) if latest_buyer_package else []
        )
        artifact_ng_count = _home_sales_artifact_ng_count(
            releases,
            materials,
            screenshot_packs,
            listing_packages,
            handoffs,
            buyer_packages,
            buyer_package_errors=buyer_package_errors,
        )
        artifact_stale_count = _home_sales_artifact_stale_count(
            releases,
            handoffs,
            buyer_packages,
            buyer_package_errors=buyer_package_errors,
        )
        seller_remaining = len(missing) + len(warnings)
        score = max(
            0,
            100
            - seller_remaining * 8
            - artifact_remaining * 12
            - artifact_ng_count * 16
            - artifact_stale_count * 10,
        )
        status = (
            "READY TO VERIFY"
            if (
                seller_remaining == 0
                and artifact_remaining == 0
                and artifact_ng_count == 0
                and artifact_stale_count == 0
            )
            else "NEEDS ATTENTION"
        )
        self._home_sales_next_step = self._home_sales_lightweight_next_step(
            missing=missing,
            warnings=warnings,
            releases=releases,
            handoffs=handoffs,
            buyer_packages=buyer_packages,
            buyer_package_errors=buyer_package_errors,
            buyer_messages=buyer_messages,
            materials=materials,
            screenshot_packs=screenshot_packs,
            listing_packages=listing_packages,
        )
        buyer_package_text = "NG" if buyer_package_errors else ("あり" if buyer_packages else "なし")
        freshness_text = _home_sales_freshness_text(
            releases,
            handoffs,
            buyer_packages,
            buyer_package_errors=buyer_package_errors,
        )
        artifact_text = _home_sales_artifact_text(
            releases,
            materials,
            listing_packages,
            handoffs,
        )
        screenshot_text = _home_sales_screenshot_text(screenshot_packs)
        self.home_sales_status_var.set(f"販売準備: {status} / 軽量 {score}/100")
        self.home_sales_detail_var.set(
            f"販売者情報 {complete}/{total} / 販売者残件 {seller_remaining} / "
            f"生成物不足 {artifact_remaining} / 生成物NG {artifact_ng_count} / "
            f"生成物更新 {freshness_text} / "
            f"{artifact_text} / 掲載画像 {screenshot_text} / "
            f"購入者ZIP {buyer_package_text} / "
            f"送付文 {'あり' if buyer_messages else 'なし'} / 送付記録 {'あり' if seller_receipts else 'なし'} / "
            f"サポート {support_text}"
        )
        buyer_message_matches_package = _home_buyer_send_message_matches_package(
            latest_buyer_package,
            latest_buyer_message,
        )
        buyer_package_matches_release = _home_buyer_delivery_package_matches_release(
            latest_buyer_package,
            releases[0] if releases else None,
            package_errors=buyer_package_errors,
        )
        buyer_receipt_matches_delivery = _home_buyer_send_receipt_matches_delivery(
            latest_buyer_package,
            latest_buyer_message,
            latest_seller_receipt,
        )
        if hasattr(self, "home_delivery_release_var"):
            self.home_delivery_release_var.set(
                _home_delivery_release_summary(
                    releases[0] if releases else None,
                    latest_buyer_package,
                    package_errors=buyer_package_errors,
                    package_matches_release=buyer_package_matches_release,
                )
            )
        if hasattr(self, "home_buyer_send_evidence_var"):
            self.home_buyer_send_evidence_var.set(
                _home_buyer_send_evidence_summary(
                    latest_buyer_package,
                    latest_buyer_message,
                    latest_seller_receipt,
                    message_matches_package=buyer_message_matches_package,
                    receipt_matches_delivery=buyer_receipt_matches_delivery,
                    package_errors=buyer_package_errors,
                )
            )
        buyer_state, buyer_summary, buyer_next = _home_buyer_send_summary(
            latest_buyer_package,
            latest_buyer_message,
            latest_seller_receipt,
            package_errors=buyer_package_errors,
            package_matches_release=buyer_package_matches_release,
            message_matches_package=buyer_message_matches_package,
            receipt_matches_delivery=buyer_receipt_matches_delivery,
        )
        buyer_action = _home_buyer_send_action(
            latest_buyer_package,
            latest_buyer_message,
            latest_seller_receipt,
            package_errors=buyer_package_errors,
            package_matches_release=buyer_package_matches_release,
            message_matches_package=buyer_message_matches_package,
            receipt_matches_delivery=buyer_receipt_matches_delivery,
        )
        focus = commercial_setup_next_focus(settings)
        if hasattr(self, "home_commercial_focus_var"):
            self.home_commercial_focus_var.set(_home_commercial_focus_text(settings))
        if hasattr(self, "home_commercial_focus_button_var"):
            self.home_commercial_focus_button_var.set(_home_commercial_focus_button_label(focus.status))
        if hasattr(self, "home_release_check_var"):
            release_check_state, release_check_text = _home_release_check_summary(release_checks)
            self._set_home_release_check_status(release_check_state, release_check_text)
        if hasattr(self, "home_release_check_button_var"):
            self.home_release_check_button_var.set(_home_release_check_button_label(release_checks))
        self._set_home_buyer_send_status(buyer_state, buyer_summary)
        self._set_home_buyer_send_action(buyer_action)
        self.home_buyer_send_next_var.set(buyer_next)
        self._set_home_sales_status_pill("ok" if status == "READY TO VERIFY" else "warn")
        self._set_home_sales_stage(
            "seller",
            _home_commercial_focus_state(focus.status),
            f"{complete}/{total}" if focus.status == "ready" else f"{focus.label}",
        )
        self._set_home_sales_stage("release", "ok" if releases else "warn", "あり" if releases else "未作成")
        buyer_package_ready = bool(buyer_packages and not buyer_package_errors)
        buyer_ready = bool(buyer_package_ready and buyer_messages)
        buyer_package_stale = buyer_package_matches_release is False
        self._set_home_sales_stage(
            "buyer",
            (
                "fail"
                if buyer_package_errors
                else ("warn" if buyer_package_stale else ("ok" if buyer_ready else "warn"))
            ),
            (
                "ZIP NG"
                if buyer_package_errors
                else ("ZIP要更新" if buyer_package_stale else ("ZIP+送付文" if buyer_ready else "未完了"))
            ),
        )
        send_ready = bool(buyer_ready and seller_receipts)
        self._set_home_sales_stage(
            "send",
            "ok" if send_ready else ("info" if buyer_ready else "warn"),
            "記録あり" if send_ready else ("照合待ち" if buyer_ready else "未準備"),
        )
        self._set_home_sales_stage("support", support_state, support_text)
        self._refresh_home_sales_timeline(
            complete=complete,
            total=total,
            seller_remaining=seller_remaining,
            releases=releases,
            handoffs=handoffs,
            buyer_packages=buyer_packages,
            buyer_messages=buyer_messages,
            materials=materials,
            screenshot_packs=screenshot_packs,
            listing_kits=listing_kits,
            listing_packages=listing_packages,
            release_checks=release_checks,
            latest_buyer_package=latest_buyer_package,
            latest_buyer_message=latest_buyer_message,
            latest_seller_receipt=latest_seller_receipt,
            buyer_package_errors=buyer_package_errors,
            buyer_package_matches_release=buyer_package_matches_release,
            buyer_message_matches_package=buyer_message_matches_package,
            buyer_receipt_matches_delivery=buyer_receipt_matches_delivery,
        )
        if self._home_sales_next_step is None:
            self.home_sales_next_var.set("次: 販売ナビで詳細検証します。")
            return
        self.home_sales_next_var.set(
            f"次: {self._home_sales_next_step.title} - {self._home_sales_next_step.action}"
        )

    def _home_support_send_readiness(self) -> tuple[str, str]:
        contact = self.settings.support_contact.strip() if self.settings.support_contact else ""
        bundles = list_support_bundles(self.project_dir)
        if not bundles:
            return ("warn", "未作成")
        latest = bundles[0]
        if verify_support_bundle(latest):
            return ("fail", "要確認")
        try:
            mtime = latest.stat().st_mtime
        except OSError:
            return ("fail", "確認不可")
        stale = (datetime.now().timestamp() - mtime) > (SUPPORT_BUNDLE_FRESHNESS_WARNING_HOURS * 60 * 60)
        if stale:
            return ("warn", "要更新")
        if not contact:
            return ("warn", "連絡先")
        return ("ok", "準備OK")

    def _set_home_sales_status_pill(self, state: str) -> None:
        if not hasattr(self, "home_sales_status_pill"):
            return
        text, bg, fg = _home_sales_indicator_style(state)
        self.home_sales_status_pill.configure(text=text, bg=bg, fg=fg)

    def _set_home_sales_stage(self, key: str, state: str, text: str) -> None:
        value = getattr(self, "home_sales_stage_vars", {}).get(key)
        pill = getattr(self, "home_sales_stage_pills", {}).get(key)
        if value is not None:
            value.set(text)
        if pill is not None:
            pill_text, bg, fg = _home_sales_indicator_style(state)
            pill.configure(text=pill_text, bg=bg, fg=fg)

    def _set_home_sales_timeline_step(
        self,
        key: str,
        state: str,
        text: str,
        *,
        enabled: bool = True,
    ) -> None:
        value = getattr(self, "home_sales_timeline_vars", {}).get(key)
        pill = getattr(self, "home_sales_timeline_pills", {}).get(key)
        button = getattr(self, "home_sales_timeline_buttons", {}).get(key)
        if value is not None:
            value.set(text)
        if pill is not None:
            pill_text, bg, fg = _home_sales_indicator_style(state)
            pill.configure(text=pill_text, bg=bg, fg=fg)
        if button is not None:
            button.configure(state=tk.NORMAL if enabled else tk.DISABLED)

    def _refresh_home_sales_timeline(
        self,
        *,
        complete: int,
        total: int,
        seller_remaining: int,
        releases: list[Path],
        handoffs: list[Path],
        buyer_packages: list[Path],
        buyer_messages: list[Path],
        materials: list[Path],
        screenshot_packs: list[Path],
        listing_kits: list[Path],
        listing_packages: list[Path],
        release_checks: list[Path],
        latest_buyer_package: Path | None,
        latest_buyer_message: Path | None,
        latest_seller_receipt: Path | None,
        buyer_package_errors: list[str],
        buyer_package_matches_release: bool | None,
        buyer_message_matches_package: bool | None,
        buyer_receipt_matches_delivery: bool | None,
    ) -> None:
        if not hasattr(self, "home_sales_timeline_vars"):
            return

        timeline: list[tuple[str, str, str, str]] = []

        def put(key: str, title: str, state: str, detail: str) -> None:
            self._set_home_sales_timeline_step(key, state, detail)
            timeline.append((key, title, state, detail))

        put(
            "seller",
            "販売者情報",
            "ok" if seller_remaining == 0 else "warn",
            f"完了 {complete}/{total}" if seller_remaining == 0 else f"残件 {seller_remaining} / {complete}/{total}",
        )
        put(
            "release",
            "配布ZIP",
            "ok" if releases else "warn",
            f"最新 {_format_mtime(releases[0])}" if releases else "未作成",
        )
        put(
            "materials",
            "販売素材",
            "ok" if materials else "warn",
            f"最新 {_format_mtime(materials[0])}" if materials else "未作成",
        )
        screenshot_errors = verify_sales_screenshot_pack(screenshot_packs[0]) if screenshot_packs else []
        put(
            "screenshots",
            "掲載画像",
            "fail" if screenshot_errors else ("ok" if screenshot_packs else "warn"),
            f"NG {len(screenshot_errors)}件"
            if screenshot_errors
            else (f"最新 {_format_mtime(screenshot_packs[0])}" if screenshot_packs else "未作成"),
        )
        latest_listing = listing_packages[0] if listing_packages else (listing_kits[0] if listing_kits else None)
        listing_errors = verify_sales_listing_kit(latest_listing) if latest_listing else []
        put(
            "listing",
            "掲載キット",
            "fail" if listing_errors else ("ok" if latest_listing else "warn"),
            f"NG {len(listing_errors)}件" if listing_errors else (f"最新 {_format_mtime(latest_listing)}" if latest_listing else "未作成"),
        )
        put(
            "handoff",
            "販売一式",
            "ok" if handoffs else "warn",
            f"最新 {_format_mtime(handoffs[0])}" if handoffs else "未作成",
        )

        buyer_package_ready = bool(latest_buyer_package and latest_buyer_package.exists() and not buyer_package_errors)
        buyer_message_ready = bool(latest_buyer_message and latest_buyer_message.exists())
        if buyer_package_errors:
            buyer_state = "fail"
            buyer_detail = f"ZIP検証NG {len(buyer_package_errors)}件"
        elif buyer_package_matches_release is False:
            buyer_state = "warn"
            buyer_detail = "最新ZIPへ更新"
        elif buyer_package_ready and buyer_message_ready and buyer_message_matches_package is False:
            buyer_state = "fail"
            buyer_detail = "送付文のZIP/SHA不一致"
        elif buyer_package_ready and buyer_message_ready:
            buyer_state = "ok"
            buyer_detail = "ZIP+送付文OK"
        elif buyer_package_ready:
            buyer_state = "info"
            buyer_detail = "送付文待ち"
        else:
            buyer_state = "warn"
            buyer_detail = "購入者ZIP待ち"
        put("buyer", "購入者ZIP/送付文", buyer_state, buyer_detail)

        if buyer_package_matches_release is False:
            send_state = "warn"
            send_detail = "購入者ZIP要更新"
        elif buyer_message_matches_package is False:
            send_state = "fail"
            send_detail = "送付文のZIP/SHA不一致"
        elif buyer_receipt_matches_delivery is False:
            send_state = "fail"
            send_detail = "送付記録のZIP/SHA不一致"
        elif buyer_receipt_matches_delivery is True:
            send_state = "ok"
            send_detail = "送付記録OK"
        elif buyer_package_ready and buyer_message_ready:
            send_state = "info"
            send_detail = "送付前照合待ち"
        else:
            send_state = "warn"
            send_detail = "購入者ZIP/送付文待ち"
        put("send", "送付前照合", send_state, send_detail)

        launch_checks = list_sales_launch_checklists(self.project_dir)
        if launch_checks:
            launch_status = _home_report_status("販売直前", launch_checks[0])
            launch_state = _home_report_status_state(launch_status)
            launch_detail = f"{launch_status} / {_format_mtime(launch_checks[0])}"
        else:
            launch_state = "warn"
            launch_detail = "未保存"
        put("launch", "販売直前", launch_state, launch_detail)

        full_state, full_detail = _home_release_check_timeline_detail(release_checks)
        put("full", "一括チェック", full_state, full_detail)

        done = sum(1 for _key, _title, state, _detail in timeline if state == "ok")
        blocked = sum(1 for _key, _title, state, _detail in timeline if state == "fail")
        next_title = next((title for _key, title, state, _detail in timeline if state != "ok"), "販売ナビ")
        if blocked:
            summary = f"{done}/{len(timeline)} 完了 / NG {blocked} / 次: {next_title}"
        elif done == len(timeline):
            summary = f"{done}/{len(timeline)} 完了 / 販売ナビで最終確認"
        else:
            summary = f"{done}/{len(timeline)} 完了 / 次: {next_title}"
        self.home_sales_timeline_summary_var.set(summary)

    def _set_home_buyer_send_status(self, state: str, text: str) -> None:
        if not hasattr(self, "home_buyer_send_var"):
            return
        pill_text, bg, fg = _home_sales_indicator_style(state)
        self.home_buyer_send_status_pill.configure(text=pill_text, bg=bg, fg=fg)
        self.home_buyer_send_var.set(text)

    def _set_home_release_check_status(self, state: str, text: str) -> None:
        if not hasattr(self, "home_release_check_var"):
            return
        pill = getattr(self, "home_release_check_status_pill", None)
        if pill is not None:
            pill_text, bg, fg = _home_sales_indicator_style(state)
            pill.configure(text=pill_text, bg=bg, fg=fg)
        self.home_release_check_var.set(text)

    def run_home_release_check_action(self) -> None:
        reports = _list_release_check_reports(self.project_dir)
        if not _home_release_check_should_run(reports):
            self.show_latest_release_check_report_action()
            return
        self.run_release_check_full_action()

    def show_latest_release_check_report_action(self) -> None:
        reports = _list_release_check_reports(self.project_dir)
        if not reports:
            self.notify("販売前一括チェックはまだありません", level="warning")
            self.run_release_check_full_action()
            return
        latest = reports[0]
        if not latest.exists():
            self.notify("最新の販売前一括チェックが見つかりません", level="warning")
            self._refresh_home_reports()
            self._refresh_home_sales_summary()
            return
        text = self._format_home_report_preview("一括チェック", latest)
        self._set_text(self.diagnostics_text, text)
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"販売前一括チェック結果を表示しました: {latest.name}", level="success")

    def _set_home_buyer_send_action(self, action: str) -> None:
        action_var = getattr(self, "home_buyer_send_action_var", None)
        button_var = getattr(self, "home_buyer_send_button_var", None)
        if action_var is not None:
            action_var.set(action)
        if button_var is not None:
            button_var.set(_home_buyer_send_button_label(action))

    def _set_support_bundle_status(self, text: str) -> None:
        self.support_bundle_status_var.set(text)
        pill = getattr(self, "support_bundle_status_pill", None)
        if pill is None:
            return
        pill_text, bg, fg = _support_bundle_indicator_style(text)
        pill.configure(text=pill_text, bg=bg, fg=fg)

    def _set_support_contact_status(self, contact: str) -> None:
        self.support_contact_summary_var.set(contact or "未設定")
        pill = getattr(self, "support_contact_status_pill", None)
        if pill is None:
            return
        pill_text, bg, fg = _support_contact_indicator_style(contact)
        pill.configure(text=pill_text, bg=bg, fg=fg)

    def _set_support_send_readiness(self, text: str) -> None:
        self.support_send_readiness_var.set(text)
        pill = getattr(self, "support_send_readiness_status_pill", None)
        if pill is None:
            return
        pill_text, bg, fg = _support_send_readiness_indicator_style(text)
        pill.configure(text=pill_text, bg=bg, fg=fg)

    def _set_support_next_action(self, text: str) -> None:
        self.support_next_action_var.set(text)
        button_var = getattr(self, "support_next_button_var", None)
        if button_var is not None:
            button_var.set(_support_next_button_label(text))
        home_button_var = getattr(self, "home_support_next_button_var", None)
        if home_button_var is not None:
            home_button_var.set(_home_support_next_button_label(text))

    def _home_sales_lightweight_next_step(
        self,
        *,
        missing: list[str],
        warnings: list[str],
        releases: list[Path],
        handoffs: list[Path],
        buyer_packages: list[Path],
        buyer_package_errors: list[str],
        buyer_messages: list[Path],
        materials: list[Path],
        screenshot_packs: list[Path],
        listing_packages: list[Path],
    ) -> SalesPlanStep:
        if missing or warnings:
            detail = missing[0] if missing else warnings[0]
            return SalesPlanStep(
                title="販売者情報を整える",
                status="warning",
                detail=detail,
                action="未入力または公開URLの確認が必要な販売者情報を整えます。",
                gui="設定 > 次の不足へ",
                category="seller",
            )
        if not releases:
            return SalesPlanStep(
                title="配布ZIPを作成する",
                status="warning",
                detail="release package not found",
                action="購入者へ渡す配布ZIPを作成します。",
                gui="診断 > 出荷ZIP作成",
                category="tool",
            )
        release_errors = verify_release_package(releases[0])
        if release_errors:
            return SalesPlanStep(
                title="配布ZIPを作り直す",
                status="fail",
                detail=f"release package NG {len(release_errors)}件",
                action="最新の配布ZIPが壊れているため、出荷ZIPを作り直します。",
                gui="診断 > 出荷ZIP作成",
                category="tool",
            )
        if not materials:
            return SalesPlanStep(
                title="販売素材Markdownを作成する",
                status="warning",
                detail="sales materials not found",
                action="販売ページ文案、納品文、FAQを作成します。",
                gui="診断 > 販売素材作成",
                category="tool",
            )
        material_errors = verify_sales_materials(materials[0])
        if material_errors:
            return SalesPlanStep(
                title="販売素材Markdownを作り直す",
                status="fail",
                detail=f"sales materials NG {len(material_errors)}件",
                action="販売ページ文案、納品文、FAQの素材を再生成します。",
                gui="診断 > 販売素材作成",
                category="tool",
            )
        if not screenshot_packs:
            return SalesPlanStep(
                title="販売ページ掲載画像を作成する",
                status="warning",
                detail="sales screenshot pack not found",
                action="販売ページに載せる画像、キャプション、HTMLプレビューを作成します。",
                gui="診断 > 掲載画像作成",
                category="tool",
            )
        screenshot_errors = verify_sales_screenshot_pack(screenshot_packs[0])
        if screenshot_errors:
            return SalesPlanStep(
                title="販売ページ掲載画像を作り直す",
                status="fail",
                detail=f"sales screenshot pack NG {len(screenshot_errors)}件",
                action="販売ページに載せる画像、キャプション、HTMLプレビューを再生成します。",
                gui="診断 > 掲載画像作成",
                category="tool",
            )
        if not listing_packages:
            return SalesPlanStep(
                title="販売ページ掲載キットを作成する",
                status="warning",
                detail="sales listing kit not found",
                action="販売ページへ貼る文案、画像、キャプション、チェック表をZIP化します。",
                gui="診断 > 掲載キット作成",
                category="tool",
            )
        listing_errors = verify_sales_listing_kit(listing_packages[0])
        if listing_errors:
            return SalesPlanStep(
                title="販売ページ掲載キットを作り直す",
                status="fail",
                detail=f"sales listing kit NG {len(listing_errors)}件",
                action="販売ページへ貼る文案、画像、キャプション、チェック表をZIP化し直します。",
                gui="診断 > 掲載キット作成",
                category="tool",
            )
        if not handoffs:
            return SalesPlanStep(
                title="販売用一式ZIPを作成する",
                status="warning",
                detail="sales handoff not found",
                action="販売者が保管する証跡ZIPを作成します。",
                gui="診断 > 販売一式作成",
                category="tool",
            )
        handoff_errors = verify_sales_handoff(handoffs[0])
        if handoff_errors:
            return SalesPlanStep(
                title="販売用一式ZIPを作り直す",
                status="fail",
                detail=f"sales handoff NG {len(handoff_errors)}件",
                action="販売者が保管する証跡ZIPを作り直します。",
                gui="診断 > 販売一式作成",
                category="tool",
            )
        latest_release_name = releases[0].name if releases else ""
        handoff_release_name = _home_sales_handoff_release_name(handoffs[0])
        if latest_release_name and handoff_release_name and handoff_release_name != latest_release_name:
            return SalesPlanStep(
                title="販売用一式ZIPを最新配布ZIPで作り直す",
                status="warning",
                detail=f"handoff has {handoff_release_name}, latest release is {latest_release_name}",
                action="配布ZIPを作り直した後は、販売用一式ZIPも作り直してください。",
                gui="診断 > 販売一式作成",
                category="tool",
            )
        if not buyer_packages:
            return SalesPlanStep(
                title="購入者向けZIPを作成する",
                status="warning",
                detail="buyer delivery zip not found",
                action="購入者へそのまま添付できるZIPを作成します。",
                gui="診断 > 販売一括作成",
                category="tool",
            )
        if buyer_package_errors:
            return SalesPlanStep(
                title="購入者向けZIPを作り直す",
                status="fail",
                detail=f"buyer delivery zip NG {len(buyer_package_errors)}件",
                action="購入者へそのまま添付できるZIPを作り直します。",
                gui="診断 > 販売一括作成",
                category="tool",
            )
        buyer_release_name = _home_buyer_delivery_package_release_name(buyer_packages[0])
        if latest_release_name and buyer_release_name and buyer_release_name != latest_release_name:
            return SalesPlanStep(
                title="購入者向けZIPを最新配布ZIPで作り直す",
                status="warning",
                detail=f"buyer delivery has {buyer_release_name}, latest release is {latest_release_name}",
                action="購入者に添付するZIPを最新配布ZIPで作り直してください。",
                gui="診断 > 販売一括作成",
                category="tool",
            )
        if not buyer_messages:
            return SalesPlanStep(
                title="購入者向け送付文を作成する",
                status="warning",
                detail="buyer delivery message not found",
                action="最新ZIP名、サイズ、SHA-256入りの送付文を作成します。",
                gui="診断 > 販売一括作成",
                category="tool",
            )
        return SalesPlanStep(
            title="送付前チェックを実行する",
            status="info",
            detail="lightweight sales summary is complete",
            action="送付文、購入者ZIP、チェックリスト、販売証跡JSONを照合します。",
            gui="診断 > 送付前チェック",
            category="tool",
        )

    def run_home_sales_next_action(self) -> None:
        step = self._home_sales_next_step
        if step is None:
            self.run_sales_plan_to_tab()
            return
        title = step.title
        if step.category == "seller":
            self.focus_next_commercial_missing_field()
        elif "配布ZIP" in title or "インストール" in title:
            self.run_preflight_create_release_to_tab()
        elif "プライバシー" in title:
            self.run_privacy_audit_to_tab()
        elif "受入" in title:
            self.create_full_acceptance_report_action()
        elif "販売素材" in title and ("補完" in title or "検証" in step.gui):
            self.verify_latest_sales_materials_action()
        elif "販売素材" in title:
            self.create_sales_materials_action()
        elif "掲載画像" in title:
            self.create_sales_screenshots_action()
        elif "掲載キット" in title:
            self.create_sales_listing_kit_action()
        elif "販売用一式" in title:
            self.create_sales_handoff_action()
        elif "購入者向けZIP" in title:
            self.create_sales_finalize_with_template_action()
        elif "送付文" in title:
            self.create_sales_finalize_with_template_action()
        elif "送付前チェック" in title:
            self.run_buyer_send_readiness_to_tab()
        elif "最終確認" in title:
            self.verify_latest_buyer_delivery_action()
        else:
            self.run_sales_plan_to_tab()

    def run_home_commercial_focus_action(self) -> None:
        settings = self._settings_preview_from_controls() if hasattr(self, "seller_name_var") else self.settings
        focus = commercial_setup_next_focus(settings)
        if focus.status == "ready":
            self.create_sales_materials_action()
            return
        self.focus_next_commercial_missing_field()

    def run_home_buyer_send_next_action(self) -> None:
        self._refresh_home_sales_summary()
        action = self.home_buyer_send_action_var.get()
        if action in {"購入者ZIP作成", "購入者ZIP更新", "送付文作成"}:
            self.create_sales_finalize_with_template_action()
        elif action == "購入者ZIP検証":
            self.verify_latest_buyer_delivery_action()
        elif action == "送付記録":
            self.create_seller_delivery_receipt_action()
        elif action == "送付文コピー":
            self.copy_latest_buyer_delivery_message_action()
        elif action == "最終レビュー":
            self.run_sales_review_to_tab()
        else:
            self.run_buyer_send_readiness_to_tab()

    def _home_next_actions(self, action_plan) -> list[str]:
        actions = [
            f"{step.title}: {step.action}"
            for step in action_plan.steps[:4]
        ]
        if actions:
            return actions
        return [
            "記事レビューで仕上げを確認する",
            "投稿ヘルパーでnoteへ貼り付ける",
            "公開後URLを保存する",
        ]

    def _format_home_focus(self, action_plan) -> str:
        step = action_plan.steps[0] if action_plan.steps else None
        if not step:
            return "準備できています。投稿前に記事レビュー、バックアップ、出荷前チェックを確認できます。"
        return f"{step.title}: {step.action}"

    def refresh_help(self) -> None:
        if not hasattr(self, "help_text"):
            return
        self._refresh_support_summary()
        contact = self.settings.support_contact or "(未設定)"
        lines = [
            "サポート用メモ",
            "",
            f"バージョン: {__version__}",
            f"プロジェクト: {self.project_dir}",
            f"サポート連絡先: {contact}",
            "",
            "困った時に渡すもの",
            "",
            "1. 問い合わせ一式ZIP",
            "2. GUIで表示されたエラーメッセージ",
            "3. 問題が起きた操作手順",
            "",
            "問い合わせ一式ZIPには、サポート依頼Markdown、GUIログ要約、診断レポートZIP、送付前チェックリストが入ります。",
            "manifest/checksumも同梱され、ヘルプの 一式ZIP検証 と 送付前リスト で確認できます。",
            "標準でパス、ユーザー名、メール、記事タイトル、記事ファイル名を隠します。",
        ]
        self._set_text(self.help_text, "\n".join(lines))

    def _refresh_support_summary(self) -> None:
        if not hasattr(self, "support_bundle_summary_var"):
            return
        contact = self.settings.support_contact.strip() if self.settings.support_contact else ""
        self._set_support_contact_status(contact)
        bundles = list_support_bundles(self.project_dir)
        if not bundles:
            self.support_bundle_summary_var.set("未作成")
            self._set_support_bundle_status("未検証")
            self.support_bundle_freshness_var.set("-")
            self._set_support_send_readiness("未準備")
            self._set_support_next_action("問い合わせ一式を作成")
            return
        latest = bundles[0]
        errors = verify_support_bundle(latest)
        self.support_bundle_summary_var.set(latest.name)
        stale = False
        freshness_unknown = False
        try:
            mtime = latest.stat().st_mtime
            stale = (datetime.now().timestamp() - mtime) > (SUPPORT_BUNDLE_FRESHNESS_WARNING_HOURS * 60 * 60)
            suffix = " / 24h超" if stale else ""
            self.support_bundle_freshness_var.set(f"{_format_timestamp(mtime)}{suffix}")
        except OSError:
            freshness_unknown = True
            self.support_bundle_freshness_var.set("確認不可")
        if errors:
            self._set_support_bundle_status(f"NG {len(errors)}件")
            self._set_support_send_readiness("要確認")
            self._set_support_next_action("一式ZIP検証で詳細確認")
        elif freshness_unknown:
            self._set_support_bundle_status("確認不可")
            self._set_support_send_readiness("要確認")
            self._set_support_next_action("一式ZIP検証で詳細確認")
        elif stale:
            self._set_support_bundle_status("要更新")
            self._set_support_send_readiness("要更新")
            self._set_support_next_action("問い合わせ一式を再作成")
        else:
            self._set_support_bundle_status("OK")
            if contact:
                self._set_support_send_readiness("準備OK")
                self._set_support_next_action("送付前リストを確認")
            else:
                self._set_support_send_readiness("連絡先未設定")
                self._set_support_next_action("サポート連絡先を設定")

    def open_readme(self) -> None:
        _open_existing(self.project_dir / "README.md", "READMEが見つかりません。")

    def open_product_readiness(self) -> None:
        _open_existing(self.project_dir / "docs" / "PRODUCT_READINESS.md", "販売準備メモが見つかりません。")

    def open_support_guide(self) -> None:
        _open_existing(self.project_dir / "docs" / "SUPPORT.md", "サポート文書が見つかりません。")

    def open_update_guide(self) -> None:
        _open_existing(self.project_dir / "docs" / "UPDATE.md", "更新手順文書が見つかりません。")

    def open_privacy_guide(self) -> None:
        _open_existing(self.project_dir / "docs" / "PRIVACY.md", "プライバシー文書が見つかりません。")

    def open_terms_draft(self) -> None:
        _open_existing(self.project_dir / "docs" / "TERMS_DRAFT.md", "利用条件ドラフトが見つかりません。")

    def open_commercial_policy(self) -> None:
        _open_existing(self.project_dir / "docs" / "COMMERCIAL_POLICY_DRAFT.md", "販売方針ドラフトが見つかりません。")

    def open_changelog(self) -> None:
        _open_existing(self.project_dir / "docs" / "CHANGELOG.md", "変更履歴が見つかりません。")

    def open_release_checklist(self) -> None:
        _open_existing(self.project_dir / "docs" / "RELEASE_CHECKLIST.md", "リリース手順が見つかりません。")

    def open_rc_handoff(self) -> None:
        _open_existing(self.project_dir / "docs" / "RC_HANDOFF.md", "RC引き渡しメモが見つかりません。")

    def open_third_party_notices(self) -> None:
        _open_existing(self.project_dir / "docs" / "THIRD_PARTY_NOTICES.md", "第三者表記が見つかりません。")

    def show_onboarding_if_needed(self) -> None:
        if not self.settings.onboarding_seen:
            self.show_setup_wizard(force=False)

    def show_onboarding(self, *, force: bool = False) -> None:
        self.show_setup_wizard(force=force)

    def show_setup_wizard(self, *, force: bool = False) -> None:
        existing = getattr(self, "_setup_wizard_window", None)
        if existing and existing.winfo_exists():
            existing.focus()
            return

        win = tk.Toplevel(self)
        self._setup_wizard_window = win
        win.title("セットアップウィザード")
        win.geometry("780x620")
        win.minsize(680, 520)
        win.transient(self)

        frame = ttk.Frame(win, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="auto-note セットアップ", font=(UI_FONT, 18, UI_HEADING_FONT_WEIGHT)).pack(anchor=tk.W)

        notebook = ttk.Notebook(frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(12, 8))

        check_tab = ttk.Frame(notebook, padding=10)
        settings_tab = ttk.Frame(notebook, padding=10)
        next_tab = ttk.Frame(notebook, padding=10)
        notebook.add(check_tab, text="確認")
        notebook.add(settings_tab, text="設定")
        notebook.add(next_tab, text="次の操作")

        setup_text = ScrolledText(check_tab, wrap=tk.WORD, borderwidth=0)
        _style_text_widget(setup_text)
        setup_text.pack(fill=tk.BOTH, expand=True)
        self._set_text(setup_text, format_setup_report(run_setup_check(self.project_dir, create=True)))

        default_tags_var = tk.StringVar(value=", ".join(self.settings.default_tags))
        default_status_var = tk.StringVar(value=self.settings.default_status)
        support_contact_var = tk.StringVar(value=self.settings.support_contact)
        append_tags_var = tk.BooleanVar(value=self.settings.append_tags_by_default)
        open_note_var = tk.BooleanVar(value=self.settings.open_note_with_helper)
        image_optimize_var = tk.BooleanVar(value=self.settings.image_optimize_by_default)
        image_max_width_var = tk.IntVar(value=self.settings.image_max_width)
        image_quality_var = tk.IntVar(value=self.settings.image_quality)

        form = ttk.Frame(settings_tab, style="Surface.TFrame", padding=12)
        form.pack(fill=tk.X)
        self._form_row(form, 0, "既定タグ", ttk.Entry(form, textvariable=default_tags_var))
        self._form_row(
            form,
            1,
            "新規記事の状態",
            ttk.Combobox(form, textvariable=default_status_var, values=STATUS_ORDER, state="readonly", width=18),
        )
        self._form_row(form, 2, "サポート連絡先", ttk.Entry(form, textvariable=support_contact_var))
        self._form_row(
            form,
            3,
            "画像最大幅",
            ttk.Spinbox(form, textvariable=image_max_width_var, from_=320, to=4000, increment=100, width=10),
        )
        self._form_row(
            form,
            4,
            "画像品質",
            ttk.Spinbox(form, textvariable=image_quality_var, from_=30, to=100, increment=5, width=10),
        )
        ttk.Checkbutton(form, text="画像挿入時に既定で最適化する", variable=image_optimize_var).grid(
            row=5, column=1, sticky=tk.W, pady=8
        )
        ttk.Checkbutton(form, text="投稿ヘルパーでタグを本文末尾に追加する", variable=append_tags_var).grid(
            row=6, column=1, sticky=tk.W, pady=8
        )
        ttk.Checkbutton(form, text="投稿ヘルパー起動時にnote投稿画面も開く", variable=open_note_var).grid(
            row=7, column=1, sticky=tk.W, pady=8
        )
        form.columnconfigure(1, weight=1)

        next_text = ScrolledText(next_tab, wrap=tk.WORD, borderwidth=0)
        _style_text_widget(next_text)
        next_text.pack(fill=tk.BOTH, expand=True)
        self._set_text(
            next_text,
            "おすすめの開始手順\n\n"
            "1. 既定タグと投稿ヘルパー設定を保存\n"
            "2. 初回チェックで不足と次の操作を確認\n"
            "3. スターター一式で記事一覧、予定、アイデアを試す\n"
            "4. 投稿キュー、全体チェック、記事レビューを確認\n"
            "5. 投稿ヘルパーでnoteへ貼り付け\n\n"
            "困った時は ヘルプ > 問い合わせ一式 でサポート用zipを作成します。",
        )

        hide_next_var = tk.BooleanVar(value=not force)
        ttk.Checkbutton(frame, text="次回から自動表示しない", variable=hide_next_var).pack(anchor=tk.W)

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(10, 0))

        def save_wizard_settings() -> None:
            settings = AppSettings(
                default_tags=parse_tags(default_tags_var.get()),
                default_status=default_status_var.get(),
                append_tags_by_default=append_tags_var.get(),
                open_note_with_helper=open_note_var.get(),
                article_glob=self.settings.article_glob,
                onboarding_seen=self.settings.onboarding_seen,
                support_contact=support_contact_var.get().strip(),
                seller_name=self.settings.seller_name,
                sales_channel_url=self.settings.sales_channel_url,
                refund_policy_url=self.settings.refund_policy_url,
                commercial_terms_reviewed=self.settings.commercial_terms_reviewed,
                commercial_support_scope_confirmed=self.settings.commercial_support_scope_confirmed,
                commercial_reviewed_at=self.settings.commercial_reviewed_at,
                ui_density=self.settings.ui_density,
                image_optimize_by_default=image_optimize_var.get(),
                image_max_width=_bounded_int_var(image_max_width_var, 1600, 320, 4000),
                image_quality=_bounded_int_var(image_quality_var, 85, 30, 100),
            )
            save_settings(self.project_dir, settings)
            self.settings = settings
            self.sync_settings_tab()
            self.refresh_all()
            self.notify("セットアップ設定を保存しました", level="success")

        def close() -> None:
            if hide_next_var.get():
                self.settings = replace(self.settings, onboarding_seen=True)
                save_settings(self.project_dir, self.settings)
                self.sync_settings_tab()
            win.destroy()

        ttk.Button(buttons, text="設定を保存", style="Primary.TButton", command=save_wizard_settings).pack(side=tk.LEFT)
        ttk.Button(buttons, text="初回チェック", command=lambda: (close(), self.run_first_run_to_tab())).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(buttons, text="クイック確認", command=lambda: (close(), self.run_quickstart_to_tab())).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(buttons, text="スターター一式", command=lambda: (close(), self.create_starter_pack_action())).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(buttons, text="練習記事作成", command=lambda: (close(), self.create_practice_article_action())).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(buttons, text="新規記事", command=lambda: (close(), self.new_article())).pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="閉じる", command=close).pack(side=tk.RIGHT)
        win.protocol("WM_DELETE_WINDOW", close)

    def show_command_palette(self) -> None:
        existing = getattr(self, "_command_palette_window", None)
        if existing and existing.winfo_exists():
            existing.focus()
            return

        actions = self.command_palette_actions()
        win = tk.Toplevel(self)
        self._command_palette_window = win
        win.title("コマンド")
        win.geometry("620x430")
        win.minsize(520, 360)
        win.configure(bg=UI_COLORS["bg"])
        win.transient(self)

        frame = ttk.Frame(win, style="Surface.TFrame", padding=14)
        frame.pack(fill=tk.BOTH, expand=True)
        query_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=query_var)
        entry.pack(fill=tk.X, pady=(0, 8))
        entry.focus()

        command_palette_status_var = tk.StringVar()
        ttk.Label(frame, textvariable=command_palette_status_var, style="Muted.TLabel").pack(
            fill=tk.X, pady=(0, 6)
        )

        listbox = tk.Listbox(
            frame,
            height=14,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=UI_COLORS["line"],
            highlightcolor=UI_COLORS["focus"],
            background=UI_COLORS["text_bg"],
            foreground=UI_COLORS["ink"],
            selectbackground=UI_COLORS["accent"],
            selectforeground="#ffffff",
            activestyle="none",
            font=(UI_FONT, UI_TEXT_SIZE),
        )
        listbox.pack(fill=tk.BOTH, expand=True)

        visible: list[tuple[str, str, object]] = []

        def refresh() -> None:
            visible.clear()
            query = query_var.get().strip().lower()
            listbox.delete(0, tk.END)
            for label, hint, action in actions:
                if not _command_palette_matches(label, hint, query):
                    continue
                visible.append((label, hint, action))
                listbox.insert(tk.END, f"{label}  -  {hint}")
            command_palette_status_var.set(_command_palette_status(len(visible), len(actions), query))
            if visible:
                listbox.selection_set(0)
            else:
                listbox.insert(tk.END, "一致するコマンドがありません")

        def run_selected(_event=None) -> None:
            selection = listbox.curselection()
            if not selection or not visible:
                return
            _label, _hint, action = visible[selection[0]]
            win.destroy()
            action()

        def move_command_palette_selection(delta: int):
            if not visible:
                return "break"
            selection = listbox.curselection()
            current = selection[0] if selection else None
            next_index = _command_palette_selection_index(current, delta, len(visible))
            if next_index < 0:
                return "break"
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(next_index)
            listbox.activate(next_index)
            listbox.see(next_index)
            return "break"

        query_var.trace_add("write", lambda *_args: refresh())
        entry.bind("<Return>", run_selected)
        entry.bind("<Down>", lambda _event: move_command_palette_selection(1))
        entry.bind("<Up>", lambda _event: move_command_palette_selection(-1))
        listbox.bind("<Double-Button-1>", run_selected)
        listbox.bind("<Return>", run_selected)
        listbox.bind("<Down>", lambda _event: move_command_palette_selection(1))
        listbox.bind("<Up>", lambda _event: move_command_palette_selection(-1))
        win.bind("<Escape>", lambda _event: win.destroy())
        refresh()

    def set_ui_density_action(self, density: str) -> None:
        density = _normalise_ui_density(density)
        current = self._active_ui_density()
        label = _ui_density_label(density)
        if current == density and not self.display_safe_mode:
            self.notify(f"表示サイズはすでに{label}です", level="info")
            return
        self.display_density_override = ""
        self.display_safe_mode = False
        self.display_safe_mode_reason = ""
        self.display_safe_mode_warnings = []
        self.settings = replace(self.settings, ui_density=density)
        save_settings(self.project_dir, self.settings)
        self._configure_style()
        self._sync_header_display_state()
        self._refresh_manual_readability_widgets()
        self._refresh_text_widget_readability()
        self.sync_settings_tab()
        self.refresh_all()
        self.notify(f"表示サイズを{label}に変更しました", level="success")

    def focus_ui_density_setting_action(self) -> None:
        self.notebook.select(self.settings_tab)
        if hasattr(self, "ui_density_combo"):
            self.ui_density_combo.focus_set()
        self.notify("表示サイズを選んで保存できます", level="info")

    def reset_display_action(self) -> None:
        density = _normalise_ui_density(DEFAULT_SETTINGS.ui_density)
        self.display_density_override = ""
        self.display_safe_mode = False
        self.display_safe_mode_reason = ""
        self.display_safe_mode_warnings = []
        self.settings = replace(self.settings, ui_density=density)
        save_settings(self.project_dir, self.settings)
        self._configure_style()
        self._sync_header_display_state()
        self._refresh_manual_readability_widgets()
        self._refresh_text_widget_readability()
        self.sync_settings_tab()
        try:
            self.state("normal")
            self.geometry("1240x780")
            self.minsize(1020, 640)
            self.lift()
            self.focus_force()
        except tk.TclError:
            pass
        self.refresh_all()
        self.notify(f"表示をリセットしました: {_ui_density_label(density)} / 1240x780", level="success")

    def command_palette_actions(self):
        return [
            ("新規記事", "テンプレートから記事を作成", self.new_article),
            ("スターター一式", "サンプル記事、予定、アイデア、匿名ICSを作成", self.create_starter_pack_action),
            ("スターター整理", "スターター由来の記事と未使用アイデアを安全に整理", self.cleanup_starter_pack_action),
            ("練習記事作成", "初回投稿の練習用記事を作成", self.create_practice_article_action),
            ("更新", "記事一覧と各タブを再読み込み", self.refresh_all),
            ("表示サイズ: 大きめ", "文字や行高が潰れる時にすぐ拡大", lambda: self.set_ui_density_action("large")),
            ("表示サイズ: ゆったり", "標準より少し余白を増やして読みやすくする", lambda: self.set_ui_density_action("comfortable")),
            ("表示サイズ: 標準", "表示密度を標準に戻す", lambda: self.set_ui_density_action("standard")),
            ("表示サイズ設定へ", "設定タブの表示サイズを開く", self.focus_ui_density_setting_action),
            ("表示リセット", "表示サイズとウィンドウを初期状態へ戻す", self.reset_display_action),
            ("表示診断", "フォント、倍率、画面サイズ、表示スタイルを診断タブに表示", self.show_display_diagnostics_action),
            ("表示診断コピー", "表示診断をクリップボードへコピー", self.copy_display_diagnostics_action),
            ("作業進行: 初回", "ホームの初回工程を開く", lambda: self.open_home_progress_stage("setup")),
            ("作業進行: 記事", "ホームの記事工程を開く", lambda: self.open_home_progress_stage("article")),
            ("作業進行: 仕上げ", "ホームの仕上げ工程を開く", lambda: self.open_home_progress_stage("review")),
            ("作業進行: 投稿", "ホームの投稿工程を開く", lambda: self.open_home_progress_stage("publish")),
            ("作業進行: 販売", "ホームの販売工程を開く", lambda: self.open_home_progress_stage("sales")),
            ("作業進行: サポート", "ホームのサポート工程を開く", lambda: self.open_home_progress_stage("support")),
            ("ログイン安全ガイド", "安全ではない可能性がある表示時の既定ブラウザ投稿手順", self.show_note_login_safety_action),
            ("noteログイン", "普段の既定ブラウザでnoteログインを開く", self.open_note_login_action),
            ("投稿ヘルパー", "選択記事の投稿ヘルパーを開く", self.open_helper),
            ("投稿準備", "選択記事の投稿前チェックを表示", self.publish_ready_selected_to_tab),
            ("改善プラン", "選択記事の修正順と仕上げ項目を表示", self.improvement_plan_selected_to_tab),
            ("投稿キュー", "全記事を投稿できる順に並べて表示", self.publish_queue_to_tab),
            ("運用サマリー", "今日見るべき投稿、予定、古い下書きを表示", self.run_overview_to_tab),
            ("予定ICS出力", "公開予定をGoogle/Outlook向け.icsに保存", self.export_calendar_action),
            ("本文コピー", "選択記事の本文をコピー", lambda: self.copy_selected("body")),
            ("メタ編集", "タイトル/概要/タグ/coverを編集", self.edit_article_metadata),
            ("自動退避", "未保存退避の確認/復元/削除", self.show_autosave_dialog),
            ("全体チェック", "公開前チェックを実行", lambda: self.run_check_all(True)),
            ("レビュー一覧", "記事ごとの点数と改善項目を表示", self.review_all_to_tab),
            ("選択レビュー", "選択記事の改善案を表示", self.review_selected_to_tab),
            ("画像チェック", "全記事の画像参照を確認", self.check_images_all),
            ("初回チェック", "導入後10分の確認を順番に表示", self.run_first_run_to_tab),
            ("受入チェック", "購入者が受け取り後に確認する項目を表示", self.run_acceptance_to_tab),
            ("受入保存", "受入チェック結果をテキスト保存", self.create_acceptance_report_action),
            ("受入フル保存", "GUI初期化と投稿ヘルパー生成まで確認して保存", self.create_full_acceptance_report_action),
            ("販売ナビ", "販売前に残るタスクを優先順で表示", self.run_sales_plan_to_tab),
            ("販売ナビ保存", "販売ナビを時刻付きレポートとして保存", self.create_sales_plan_report_action),
            ("販売者情報確認", "未保存の入力欄も含めて販売者情報の不足と公開URLを確認", self.show_commercial_setup_status_action),
            ("販売者情報へ", "設定タブの次に直す販売者情報へ移動", self.focus_next_commercial_missing_field),
            ("販売者テンプレ", "販売者情報と販売前確認の下書きを作成", self.create_commercial_setup_template_action),
            ("テンプレ適用", "最新の販売者テンプレから設定へ値を保存", self.apply_latest_commercial_setup_template_action),
            ("販売素材作成", "販売ページ、納品文、FAQ、サポート文案を作成", self.create_sales_materials_action),
            ("販売素材検証", "最新販売素材Markdownの未設定項目と反映漏れを確認", self.verify_latest_sales_materials_action),
            ("掲載画像作成", "販売ページ掲載用のSVG画像、キャプション、HTMLプレビューを作成", self.create_sales_screenshots_action),
            ("掲載画像検証", "最新の販売ページ画像パックを検証", self.verify_latest_sales_screenshots_action),
            ("掲載キット作成", "販売ページへ貼る素材、画像、キャプション、チェック表をZIP化", self.create_sales_listing_kit_action),
            ("掲載キット検証", "最新の掲載キットフォルダとZIPを検証", self.verify_latest_sales_listing_kit_action),
            ("テンプレ取込一括", "最新販売者テンプレを取り込んでから販売一括作成", self.create_sales_finalize_with_template_action),
            ("販売一括作成", "配布ZIP、販売素材、掲載画像、掲載キット、販売一式ZIP、購入者ZIP、診断、監査をまとめて作成", self.create_sales_finalize_action),
            ("販売準備", "配布ZIP、監査、受入、文書、連絡先を販売目線で確認", self.run_commercial_readiness_to_tab),
            ("販売準備保存", "販売前に残る確認事項をレポート保存", self.create_commercial_readiness_report_action),
            ("方針レビュー", "返金、ライセンス、サポート範囲の販売者向け最終確認を保存", self.create_commercial_policy_review_action),
            ("販売一式作成", "最新配布ZIPと販売前エビデンスをまとめる", self.create_sales_handoff_action),
            ("販売一式検証", "最新販売用一式ZIPを検証", self.verify_latest_sales_handoff_action),
            ("購入者ZIP抽出", "最新販売用一式ZIPから購入者へ送る単体ZIPを作成", self.extract_latest_buyer_delivery_action),
            ("購入者ZIP検証", "購入者へ送るフォルダと単体ZIPに余計なファイルがないか確認", self.verify_latest_buyer_delivery_action),
            ("送付前チェック", "最新の送付文、購入者ZIP、販売者チェックリスト、販売証跡JSONを照合", self.run_buyer_send_readiness_to_tab),
            ("送付前保存", "購入者送付前チェックを時刻付きレポートとして保存", self.create_buyer_send_readiness_report_action),
            ("送付記録", "検証済みZIP名とSHA-256入りの販売者向け納品記録を保存", self.create_seller_delivery_receipt_action),
            ("送付記録コピー", "最新の販売者向け納品記録を注文管理へ控えやすい形でコピー", self.copy_latest_seller_delivery_receipt_action),
            ("注文控えコピー", "注文管理へ貼る短い控え欄だけをコピー", self.copy_latest_seller_order_note_action),
            ("購入者ZIP場所", "送付前チェック後に購入者向けZIPがあるフォルダを開く", self.open_latest_buyer_delivery_location_action),
            ("送付文コピー", "最新の購入者向け送付文をZIP検証後にクリップボードへコピー", self.copy_latest_buyer_delivery_message_action),
            ("ZIPパスコピー", "送付前チェック後に購入者向けZIPの絶対パスをコピー", self.copy_latest_buyer_delivery_zip_path_action),
            ("送付情報コピー", "ZIP名、絶対パス、サイズ、SHA-256、送付文ファイルをコピー", self.copy_latest_buyer_delivery_sheet_action),
            ("最終レビュー", "販売ページ文案、送付文、購入者ZIP、納品記録の整合性を確認", self.run_sales_review_to_tab),
            ("レビュー保存", "販売ページ・納品最終レビューを時刻付きレポートとして保存", self.create_sales_review_report_action),
            ("販売直前", "販売ページ公開前に決済後メッセージ、添付ZIP、返金/サポート表示を確認", self.run_sales_launch_to_tab),
            ("直前保存", "販売ページ公開前の最終目視チェックリストを保存", self.create_sales_launch_checklist_action),
            ("販売確認記録", "販売ページのプレビュー確認後に販売者専用の証跡を保存", self.create_sales_launch_confirmation_action),
            (
                "販売前一括チェック",
                "check-release.ps1 -Full をバックグラウンドで実行し、証跡レポートを保存",
                self.run_release_check_full_action,
            ),
            ("アクションプラン", "いま優先すべき操作を表示", self.run_action_plan_to_tab),
            ("セルフテスト", "インストール後の基本動作を確認", self.run_self_test_to_tab),
            ("セルフテスト保存", "セルフテスト結果をテキスト保存", self.create_self_test_report_action),
            ("E2E確認", "一時プロジェクトで投稿準備ワークフローを確認", self.run_workflow_smoke_to_tab),
            ("クイック確認", "初回投稿までの導線を確認", self.run_quickstart_to_tab),
            ("ヘルパー生成確認", "投稿ヘルパーHTML生成を確認", self.run_quickstart_helper_smoke_to_tab),
            ("セットアップ確認", "初回セットアップ状態を確認", self.run_setup_to_tab),
            ("準備度確認", "スコアと次の対応を表示", self.run_readiness_to_tab),
            ("復旧セット", "安全な基本修復、再診断、必要時の問い合わせ一式作成をまとめて実行", self.run_recovery_kit_to_tab),
            ("最新復旧レポート", "保存済みの最新復旧レポートを表示", self.show_latest_recovery_kit_report_action),
            ("復旧レポートコピー", "最新復旧レポートをクリップボードへコピー", self.copy_latest_recovery_kit_report_action),
            ("復旧レポート場所", "復旧レポート保存フォルダを開く", self.open_recovery_kit_reports_folder_action),
            ("自動修復", "基本フォルダ/設定を安全に再作成し、整理候補を確認", self.run_repair_to_tab),
            ("トラブル診断", "起動、ログイン、プライバシー、配布ZIPの詰まりどころを確認", self.run_troubleshoot_to_tab),
            ("出荷前チェック", "販売/配布前の総合チェックを表示", self.run_preflight_to_tab),
            ("出荷ZIP作成", "総合チェック後に配布ZIPを作成/検証", self.run_preflight_create_release_to_tab),
            ("RC引き渡し", "販売候補版の固定点、実機確認、停止条件を開く", self.open_rc_handoff),
            ("アプリ情報", "バージョンと環境概要を表示", self.show_app_info),
            ("GUIログ表示", "最新GUIログを診断タブに表示", self.show_gui_log_action),
            ("GUIログコピー", "最新GUIログをクリップボードへコピー", self.copy_gui_log_action),
            ("GUIログクリア", "確認済みGUIログを退避して復旧ステータスをリセット", self.clear_gui_log_action),
            ("GUIログ場所", "GUIログが保存されるフォルダを開く", self.open_gui_log_folder_action),
            ("ライセンス表示", "依存ライブラリの第三者表記を表示", self.show_dependency_notices),
            ("第三者表記更新", "依存ライブラリ表記をMarkdownへ書き出す", self.write_dependency_notices_action),
            ("問い合わせ作成", "サポート依頼テンプレートを作成", self.create_support_request_action),
            ("問い合わせ一式", "依頼文と診断ZIPを1つにまとめる", self.create_support_bundle_action),
            ("サポート次実行", "サポート送付の現在の次アクションを実行", self.run_support_next_action),
            ("一式ZIP検証", "最新問い合わせ一式ZIPを検証", self.verify_latest_support_bundle_action),
            ("ZIPログ要約", "最新問い合わせ一式ZIP内のGUIログ要約を表示", self.show_support_gui_log_summary_action),
            ("ZIP表示診断", "最新問い合わせ一式ZIP内の表示診断を表示", self.show_support_display_diagnostics_action),
            ("送付前リスト", "問い合わせ一式ZIPの送付前チェックリストを表示", self.show_support_send_checklist_action),
            ("送付文コピー", "連絡先と最新問い合わせ一式ZIPを送付メモとしてコピー", self.copy_support_send_message_action),
            ("最新ZIP場所", "最新問い合わせ一式ZIPがあるフォルダを開く", self.open_latest_support_bundle_location_action),
            ("最新ZIPパス", "最新問い合わせ一式ZIPの絶対パスをコピー", self.copy_latest_support_bundle_path_action),
            ("連絡先コピー", "サポート連絡先をクリップボードへコピー", self.copy_support_contact_action),
            ("連絡先へ", "設定タブのサポート連絡先へ移動", self.focus_support_contact_field),
            ("品質チェック", "販売/配布前チェックを実行", self.run_quality_to_tab),
            ("診断プレビュー", "診断レポートの内容を確認", self.preview_diagnostic_report_action),
            ("診断レポート作成", "匿名化済み診断ZIPを作成", self.create_diagnostic_report_action),
            ("診断ZIP検証", "最新診断ZIPの必須ファイルと破損を確認", self.verify_latest_diagnostic_report_action),
            ("診断ZIP場所", "最新診断ZIPがあるフォルダを開く", self.open_latest_diagnostic_report_location_action),
            ("診断ZIPパス", "最新診断ZIPの絶対パスをコピー", self.copy_latest_diagnostic_report_path_action),
            ("危険生成物確認", "プライバシー監査NGの生成物だけを表示", self.preview_privacy_failed_cleanup_action),
            ("危険生成物整理", "プライバシー監査NGの生成物だけを削除", self.apply_privacy_failed_cleanup_action),
            ("バックアップ作成", "記事と設定をZIP保存", self.create_backup_action),
            ("バックアップ確認", "ZIPの復元対象と危険な項目を確認", self.inspect_backup_action),
            ("バックアップ復元", "ZIPから記事/設定/アイデアを復元", self.restore_backup_action),
            ("配布ZIP作成", "ユーザー記事を含めない配布ZIPを作成", self.create_release_action),
            ("最新ZIP検証", "最新配布ZIPのchecksumを検証", self.verify_latest_release_action),
            ("記事CSV出力", "記事一覧CSVを作成", self.export_inventory_action),
            ("生成物確認", "古い診断/問い合わせ/CSV/HTML候補を表示", self.preview_cleanup_action),
            ("セットアップウィザード", "初回案内と設定を開く", lambda: self.show_setup_wizard(force=True)),
            ("記事フォルダ", "articlesフォルダを開く", lambda: _open_path(self.articles_dir)),
            ("初回タブ", "初回チェックのカード画面を開く", lambda: self.notebook.select(self.first_run_tab)),
            ("設定タブ", "設定を開く", lambda: self.notebook.select(self.settings_tab)),
            ("ヘルプタブ", "ヘルプを開く", lambda: self.notebook.select(self.help_tab)),
        ]

    def sync_settings_tab(self) -> None:
        if hasattr(self, "default_tags_var"):
            self.default_tags_var.set(", ".join(self.settings.default_tags))
        if hasattr(self, "default_status_var"):
            self.default_status_var.set(self.settings.default_status)
        if hasattr(self, "append_tags_var"):
            self.append_tags_var.set(self.settings.append_tags_by_default)
        if hasattr(self, "open_note_var"):
            self.open_note_var.set(self.settings.open_note_with_helper)
        if hasattr(self, "article_glob_var"):
            self.article_glob_var.set(self.settings.article_glob)
        if hasattr(self, "ui_density_var"):
            self.ui_density_var.set(_ui_density_label(self.settings.ui_density))
        if hasattr(self, "header_ui_density_var"):
            self.header_ui_density_var.set(_ui_density_label(self._active_ui_density()))
        if hasattr(self, "support_contact_var"):
            self.support_contact_var.set(self.settings.support_contact)
        if hasattr(self, "seller_name_var"):
            self.seller_name_var.set(self.settings.seller_name)
        if hasattr(self, "sales_channel_url_var"):
            self.sales_channel_url_var.set(self.settings.sales_channel_url)
        if hasattr(self, "refund_policy_url_var"):
            self.refund_policy_url_var.set(self.settings.refund_policy_url)
        if hasattr(self, "commercial_terms_reviewed_var"):
            self.commercial_terms_reviewed_var.set(self.settings.commercial_terms_reviewed)
        if hasattr(self, "commercial_support_scope_var"):
            self.commercial_support_scope_var.set(self.settings.commercial_support_scope_confirmed)
        if hasattr(self, "image_optimize_var"):
            self.image_optimize_var.set(self.settings.image_optimize_by_default)
        if hasattr(self, "image_max_width_var"):
            self.image_max_width_var.set(self.settings.image_max_width)
        if hasattr(self, "image_quality_var"):
            self.image_quality_var.set(self.settings.image_quality)
        self._refresh_commercial_setup_progress()

    def _bind_commercial_setup_progress(self) -> None:
        for variable in (
            self.support_contact_var,
            self.seller_name_var,
            self.sales_channel_url_var,
            self.refund_policy_url_var,
            self.commercial_terms_reviewed_var,
            self.commercial_support_scope_var,
        ):
            variable.trace_add("write", lambda *_args: self._refresh_commercial_setup_progress())

    def _refresh_commercial_setup_progress(self) -> None:
        if not hasattr(self, "commercial_progress_var"):
            return
        settings = self._settings_preview_from_controls()
        complete, total = commercial_setup_completion(settings)
        missing = commercial_setup_missing_fields(settings)
        warnings = commercial_setup_warnings(settings)
        self.commercial_progress_var.set(
            f"販売者情報: {complete}/{total} 完了 / 未入力 {len(missing)} / 確認 {len(warnings)}"
        )
        next_field = commercial_setup_next_field(settings)
        if next_field:
            self.commercial_next_var.set(f"次: {self._commercial_field_action(next_field)}")
        else:
            self.commercial_next_var.set("次: 設定を保存して、販売素材作成または販売一括作成へ進めます。")
        self._refresh_commercial_setup_checklist(settings, next_field)

    def _refresh_commercial_setup_checklist(self, settings: AppSettings, next_field: str = "") -> None:
        if not hasattr(self, "commercial_setup_tree"):
            return
        rows = _commercial_setup_field_rows(settings)
        selected_field = ""
        current_selection = self.commercial_setup_tree.selection()
        if current_selection:
            selected_field = current_selection[0]
        self.commercial_setup_tree.delete(*self.commercial_setup_tree.get_children())
        first_attention = ""
        for field, label, status, detail, action in rows:
            self.commercial_setup_tree.insert(
                "",
                tk.END,
                iid=field,
                values=(_commercial_setup_status_label(status), label, detail, action),
                tags=(status,),
            )
            if not first_attention and status != "ok":
                first_attention = field
        target = selected_field if selected_field and self.commercial_setup_tree.exists(selected_field) else ""
        if not target:
            target = next_field if next_field and self.commercial_setup_tree.exists(next_field) else ""
        if not target:
            children = self.commercial_setup_tree.get_children()
            target = first_attention or (children[0] if children else "")
        if target:
            self.commercial_setup_tree.selection_set(target)
            self.commercial_setup_tree.focus(target)
            self.on_select_commercial_setup_item()
        else:
            self.commercial_setup_action_var.set("")

    def on_select_commercial_setup_item(self) -> None:
        row = self._selected_commercial_setup_row()
        if row is None:
            self.commercial_setup_action_var.set("")
            return
        _field, label, status, detail, action = row
        if status == "ok":
            self.commercial_setup_action_var.set(f"{label}: OK / {detail}")
        else:
            self.commercial_setup_action_var.set(f"{label}: {action}")

    def focus_selected_commercial_setup_item(self) -> None:
        row = self._selected_commercial_setup_row()
        if row is None:
            self.focus_next_commercial_missing_field()
            return
        field, label, status, _detail, _action = row
        self.notebook.select(self.settings_tab)
        widget = self._commercial_field_widget(field)
        if widget is not None:
            try:
                widget.focus_set()
            except tk.TclError:
                pass
        if status == "ok":
            self.notify(f"{label}は設定済みです。必要なら編集して保存してください", level="info")
        else:
            self.notify(f"次に確認: {label}", level="warning")

    def _selected_commercial_setup_row(self) -> tuple[str, str, str, str, str] | None:
        if not hasattr(self, "commercial_setup_tree"):
            return None
        selection = self.commercial_setup_tree.selection()
        if not selection:
            return None
        field = selection[0]
        rows = {row[0]: row for row in _commercial_setup_field_rows(self._settings_preview_from_controls())}
        return rows.get(field)

    def focus_next_commercial_missing_field(self) -> None:
        if not hasattr(self, "seller_name_var"):
            return
        settings = self._settings_preview_from_controls()
        next_field = commercial_setup_next_field(settings)
        self.notebook.select(self.settings_tab)
        if not next_field:
            self._refresh_commercial_setup_progress()
            self.notify("販売者情報は整っています。保存して販売素材へ進めます", level="success")
            return
        widget = self._commercial_field_widget(next_field)
        if widget is not None:
            try:
                widget.focus_set()
            except tk.TclError:
                pass
        self._refresh_commercial_setup_progress()
        self.notify(f"次に確認: {self._commercial_field_label(next_field)}", level="warning")

    def focus_support_contact_field(self) -> None:
        self.notebook.select(self.settings_tab)
        widget = getattr(self, "support_contact_entry", None)
        if widget is not None:
            try:
                widget.focus_set()
                widget.selection_range(0, tk.END)
            except tk.TclError:
                pass
        if self.settings.support_contact.strip():
            self.notify("サポート連絡先は設定済みです。必要なら編集して保存してください", level="info")
        else:
            self.notify("サポート連絡先を入力して保存してください", level="warning")

    def show_support_send_panel_action(self) -> None:
        self._refresh_support_summary()
        self.notebook.select(self.help_tab)
        self.notify("サポート送付の状態を表示しました", level="info")

    def run_home_support_next_action(self) -> None:
        if self.support_next_action_var.get() != "送付文コピー":
            self._refresh_support_summary()
        self.notebook.select(self.help_tab)
        self.run_support_next_action()

    def copy_support_contact_action(self) -> None:
        self._refresh_support_summary()
        contact = self.settings.support_contact.strip()
        if not contact:
            self.notify("サポート連絡先が未設定です", level="warning")
            self.focus_support_contact_field()
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(contact)
            self.update_idletasks()
        except tk.TclError as exc:
            self.notify("サポート連絡先をコピーできませんでした", level="error")
            messagebox.showerror("連絡先コピー", str(exc))
            return
        self.notify("サポート連絡先をコピーしました", level="success")

    def run_support_next_action(self) -> None:
        action = self.support_next_action_var.get()
        if action == "送付文コピー":
            self.copy_support_send_message_action()
            return
        self._refresh_support_summary()
        action = self.support_next_action_var.get()
        if action in {"問い合わせ一式を作成", "問い合わせ一式を再作成"}:
            self.create_support_bundle_action()
        elif action == "一式ZIP検証で詳細確認":
            self.verify_latest_support_bundle_action()
        elif action == "サポート連絡先を設定":
            self.focus_support_contact_field()
        elif action == "送付前リストを確認":
            self.show_support_send_checklist_action()
        else:
            self.create_support_bundle_action()

    def _commercial_field_widget(self, field_key: str) -> tk.Widget | None:
        return {
            "seller_name": getattr(self, "seller_name_entry", None),
            "sales_channel_url": getattr(self, "sales_channel_url_entry", None),
            "refund_policy_url": getattr(self, "refund_policy_url_entry", None),
            "support_contact": getattr(self, "support_contact_entry", None),
            "commercial_terms_reviewed": getattr(self, "commercial_terms_reviewed_check", None),
            "commercial_support_scope_confirmed": getattr(self, "commercial_support_scope_check", None),
        }.get(field_key)

    def _commercial_field_label(self, field_key: str) -> str:
        return {
            "seller_name": "販売者/屋号",
            "sales_channel_url": "販売ページURL",
            "refund_policy_url": "返金方針URL",
            "support_contact": "サポート連絡先",
            "commercial_terms_reviewed": "利用条件/商用方針確認",
            "commercial_support_scope_confirmed": "サポート範囲確認",
        }.get(field_key, field_key)

    def _commercial_field_action(self, field_key: str) -> str:
        return {
            "seller_name": "販売者/屋号を入力します。",
            "sales_channel_url": "販売ページURLを https:// で始まる公開URLにします。",
            "refund_policy_url": "返金方針URLを https:// で始まる公開URLにします。",
            "support_contact": "サポート連絡先を公開サポートURLにします。",
            "commercial_terms_reviewed": "利用条件/商用方針の確認チェックをONにします。",
            "commercial_support_scope_confirmed": "サポート範囲と返金条件の明記チェックをONにします。",
        }.get(field_key, "販売者情報を確認します。")

    def _settings_preview_from_controls(self) -> AppSettings:
        if not hasattr(self, "seller_name_var"):
            return load_settings(self.project_dir)
        terms_reviewed = self.commercial_terms_reviewed_var.get()
        support_scope_confirmed = self.commercial_support_scope_var.get()
        reviewed_at = self.settings.commercial_reviewed_at if terms_reviewed or support_scope_confirmed else ""
        return replace(
            self.settings,
            default_tags=parse_tags(self.default_tags_var.get()),
            default_status=self.default_status_var.get(),
            append_tags_by_default=self.append_tags_var.get(),
            open_note_with_helper=self.open_note_var.get(),
            article_glob=self.article_glob_var.get().strip() or "*.md",
            ui_density=_ui_density_value(self.ui_density_var.get()),
            support_contact=self.support_contact_var.get().strip(),
            seller_name=self.seller_name_var.get().strip(),
            sales_channel_url=self.sales_channel_url_var.get().strip(),
            refund_policy_url=self.refund_policy_url_var.get().strip(),
            commercial_terms_reviewed=terms_reviewed,
            commercial_support_scope_confirmed=support_scope_confirmed,
            commercial_reviewed_at=reviewed_at,
            image_optimize_by_default=self.image_optimize_var.get(),
            image_max_width=_bounded_int_var(self.image_max_width_var, 1600, 320, 4000),
            image_quality=_bounded_int_var(self.image_quality_var, 85, 30, 100),
        )

    def save_app_settings(self) -> None:
        terms_reviewed = self.commercial_terms_reviewed_var.get()
        support_scope_confirmed = self.commercial_support_scope_var.get()
        reviewed_at = self.settings.commercial_reviewed_at
        if terms_reviewed or support_scope_confirmed:
            reviewed_at = reviewed_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            reviewed_at = ""
        settings = AppSettings(
            default_tags=parse_tags(self.default_tags_var.get()),
            default_status=self.default_status_var.get(),
            append_tags_by_default=self.append_tags_var.get(),
            open_note_with_helper=self.open_note_var.get(),
            article_glob=self.article_glob_var.get().strip() or "*.md",
            onboarding_seen=self.settings.onboarding_seen,
            support_contact=self.support_contact_var.get().strip(),
            seller_name=self.seller_name_var.get().strip(),
            sales_channel_url=self.sales_channel_url_var.get().strip(),
            refund_policy_url=self.refund_policy_url_var.get().strip(),
            commercial_terms_reviewed=terms_reviewed,
            commercial_support_scope_confirmed=support_scope_confirmed,
            commercial_reviewed_at=reviewed_at,
            ui_density=_ui_density_value(self.ui_density_var.get()),
            image_optimize_by_default=self.image_optimize_var.get(),
            image_max_width=_bounded_int_var(self.image_max_width_var, 1600, 320, 4000),
            image_quality=_bounded_int_var(self.image_quality_var, 85, 30, 100),
        )
        self.display_density_override = ""
        self.display_safe_mode = False
        self.display_safe_mode_reason = ""
        self.display_safe_mode_warnings = []
        save_settings(self.project_dir, settings)
        self.settings = settings
        self._configure_style()
        self._sync_header_display_state()
        self._refresh_manual_readability_widgets()
        self._refresh_text_widget_readability()
        self.refresh_all()
        self._notify_settings_saved(settings)

    def _notify_settings_saved(self, settings: AppSettings) -> None:
        commercial_started = bool(
            settings.seller_name.strip()
            or settings.sales_channel_url.strip()
            or settings.refund_policy_url.strip()
            or settings.support_contact.strip()
            or settings.commercial_terms_reviewed
            or settings.commercial_support_scope_confirmed
        )
        if not commercial_started:
            self.notify("設定を保存しました", level="success")
            return
        missing = commercial_setup_missing_fields(settings)
        warnings = commercial_setup_warnings(settings)
        if missing:
            self.notify(f"設定を保存しました。販売者情報の未入力: {len(missing)}件", level="warning")
        elif warnings:
            self.notify(f"設定を保存しました。販売者情報の確認事項: {len(warnings)}件", level="warning")
        else:
            self.notify("設定を保存しました。販売者情報も整っています", level="success")

    def on_header_ui_density_selected(self, _event=None) -> None:
        if not hasattr(self, "header_ui_density_var"):
            return
        self.set_ui_density_action(_ui_density_value(self.header_ui_density_var.get()))

    def run_diagnostics_to_tab(self) -> None:
        if not hasattr(self, "diagnostics_text"):
            return
        items = run_diagnostics(self.project_dir)
        backups = list_backups(self.project_dir)
        diagnostic_reports = list_diagnostic_reports(self.project_dir)
        releases = list_releases(self.project_dir)
        csv_reports = list_reports(self.project_dir)
        acceptance_reports = list_acceptance_reports(self.project_dir)
        commercial_reports = list_commercial_readiness_reports(self.project_dir)
        sales_handoffs = list_sales_handoffs(self.project_dir)
        overview_reports = list_overview_reports(self.project_dir)
        calendar_exports = list_calendar_exports(self.project_dir)
        buyer_deliveries = list_buyer_deliveries(self.project_dir)
        text = format_diagnostics(items)
        text += "\n\nBackups\n"
        if backups:
            text += "\n".join(str(path) for path in backups[:10])
        else:
            text += "(none)"
        text += "\n\nDiagnostic reports\n"
        if diagnostic_reports:
            text += "\n".join(str(path) for path in diagnostic_reports[:10])
        else:
            text += "(none)"
        text += "\n\nRelease packages\n"
        if releases:
            text += "\n".join(str(path) for path in releases[:10])
        else:
            text += "(none)"
        text += "\n\nCSV reports\n"
        if csv_reports:
            text += "\n".join(str(path) for path in csv_reports[:10])
        else:
            text += "(none)"
        text += "\n\nAcceptance reports\n"
        if acceptance_reports:
            text += "\n".join(str(path) for path in acceptance_reports[:10])
        else:
            text += "(none)"
        text += "\n\nCommercial readiness reports\n"
        if commercial_reports:
            text += "\n".join(str(path) for path in commercial_reports[:10])
        else:
            text += "(none)"
        text += "\n\nSales handoffs\n"
        if sales_handoffs:
            text += "\n".join(str(path) for path in sales_handoffs[:10])
        else:
            text += "(none)"
        text += "\n\nBuyer delivery folders\n"
        if buyer_deliveries:
            text += "\n".join(str(path) for path in buyer_deliveries[:10])
        else:
            text += "(none)"
        text += "\n\nOverview reports\n"
        if overview_reports:
            text += "\n".join(str(path) for path in overview_reports[:10])
        else:
            text += "(none)"
        text += "\n\nCalendar exports\n"
        if calendar_exports:
            text += "\n".join(str(path) for path in calendar_exports[:10])
        else:
            text += "(none)"
        self._set_text(self.diagnostics_text, text)

    def show_display_diagnostics_action(self) -> None:
        status, _lines = self._display_readability_checks()
        self._set_text(self.diagnostics_text, self._format_display_diagnostics())
        self.notebook.select(self.diagnostics_tab)
        if status == "OK":
            self.notify("表示診断を表示しました", level="success")
        else:
            self.notify("表示診断に注意項目があります", level="warning")

    def copy_display_diagnostics_action(self) -> None:
        status, _lines = self._display_readability_checks()
        text = self._format_display_diagnostics()
        self._set_text(self.diagnostics_text, text)
        self.notebook.select(self.diagnostics_tab)
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update_idletasks()
        except tk.TclError as exc:
            self.notify("表示診断をコピーできませんでした", level="error")
            messagebox.showerror("表示診断コピー", str(exc))
            return
        if status == "OK":
            self.notify("表示診断をコピーしました", level="success")
        else:
            self.notify("表示診断をコピーしました。注意項目があります", level="warning")

    def _button_label_fit_details(self, style: ttk.Style | None = None) -> tuple[bool, str, list[str]]:
        style = style or ttk.Style(self)
        try:
            button_padding = style.lookup("TButton", "padding")
        except tk.TclError as exc:
            return False, f"unavailable ({exc})", []
        horizontal_padding = _horizontal_padding(button_padding)
        minimum_width = _scaled_action_button_min_width(self)
        margin = int(math.ceil(UI_BUTTON_LABEL_FIT_MARGIN * max(1.0, minimum_width / UI_ACTION_BUTTON_MIN_WIDTH)))
        text_room = max(
            0,
            minimum_width
            - int(math.ceil((horizontal_padding or 0) * 2))
            - margin,
        )
        try:
            font = tkfont.Font(root=self, family=UI_FONT, size=UI_TEXT_SIZE)
            measured = [(label, int(font.measure(label))) for label in UI_BUTTON_LABEL_FIT_SAMPLES]
        except (tk.TclError, ValueError) as exc:
            return False, f"unavailable ({exc})", []
        ok, detail = _button_label_fit_status(measured, text_room)
        widest = sorted(measured, key=lambda item: item[1], reverse=True)[:3]
        sample_line = ", ".join(f"{label} {width}px" for label, width in widest)
        horizontal_text = (
            str(int(horizontal_padding))
            if horizontal_padding is not None and float(horizontal_padding).is_integer()
            else str(horizontal_padding if horizontal_padding is not None else "unknown")
        )
        lines = [
            f"- minimum button width: {minimum_width}px (base {UI_ACTION_BUTTON_MIN_WIDTH}px)",
            f"- horizontal padding: {horizontal_text}px each side",
            f"- available text room: {text_room}px",
            f"- widest samples: {sample_line}",
        ]
        return ok, detail, lines

    def _display_readability_checks(self, style: ttk.Style | None = None) -> tuple[str, list[str]]:
        style = style or ttk.Style(self)

        checks: list[tuple[str, bool, str, str]] = []

        def add(label: str, ok: bool, detail: str, action: str) -> None:
            checks.append((label, ok, detail, action))

        try:
            scaling_value: object = self.tk.call("tk", "scaling")
        except tk.TclError as exc:
            scaling_value = f"unavailable ({exc})"
        scaling_number = _first_number(scaling_value)
        tree_height = style.lookup("Treeview", "rowheight")
        tab_padding = style.lookup("TNotebook.Tab", "padding")
        button_padding = style.lookup("TButton", "padding")
        tree_height_number = _first_number(tree_height)
        tab_vertical_padding = _vertical_padding(tab_padding)
        button_vertical_padding = _vertical_padding(button_padding)
        main_linespace = _font_linespace(self, UI_FONT, UI_TEXT_SIZE)
        small_linespace = _font_linespace(self, UI_FONT, UI_SMALL_TEXT_SIZE)
        badge_linespace = _font_linespace(self, UI_FONT, UI_BADGE_FONT_SIZE, weight=UI_BADGE_FONT_WEIGHT)
        actual_font_family = _actual_font_family(self, UI_FONT, UI_TEXT_SIZE)
        button_label_fit_ok, button_label_fit_detail, _button_label_fit_lines = self._button_label_fit_details(style)
        minimum_main_linespace = _minimum_readable_linespace(UI_TEXT_SIZE)
        minimum_small_linespace = _minimum_readable_linespace(UI_SMALL_TEXT_SIZE)
        minimum_badge_linespace = _minimum_readable_linespace(UI_BADGE_FONT_SIZE)
        line_target = main_linespace or (UI_TEXT_SIZE + 9)
        tree_target = max(48, int(math.ceil(line_target * 1.55)), line_target + 14)
        tab_target = _readable_vertical_padding((0, 0), main_linespace, minimum=12, ratio=0.38)
        button_target = _readable_vertical_padding((0, 0), main_linespace, minimum=11, ratio=0.42)
        text_room_target = math.ceil((main_linespace or UI_TEXT_SIZE) * 0.75)

        add(
            "main text",
            UI_TEXT_SIZE >= 12,
            f"{UI_TEXT_SIZE}pt (target 12+)",
            "ヘッダーの 表示 で ゆったり または 大きめ を選ぶ",
        )
        add(
            "small text",
            UI_SMALL_TEXT_SIZE >= 11,
            f"{UI_SMALL_TEXT_SIZE}pt (target 11+)",
            "表示サイズを ゆったり または 大きめ にする",
        )
        add(
            "font line height",
            main_linespace is not None
            and small_linespace is not None
            and badge_linespace is not None
            and main_linespace >= minimum_main_linespace
            and small_linespace >= minimum_small_linespace
            and badge_linespace >= minimum_badge_linespace,
            (
                f"main {main_linespace or 'unknown'}px / small {small_linespace or 'unknown'}px / "
                f"badge {badge_linespace or 'unknown'}px "
                f"(target {minimum_main_linespace}/{minimum_small_linespace}/{minimum_badge_linespace}+)"
            ),
            "表示リセット後、改善しない場合は表示診断コピーを送る",
        )
        add(
            "Japanese font family",
            not _is_crush_prone_font_family(UI_FONT) and not _is_crush_prone_font_family(actual_font_family),
            f"{UI_FONT} -> actual {actual_font_family} (preferred: Yu Gothic / Meiryo UI / Meiryo)",
            "表示リセット後、ヘッダーの 表示 で 大きめ を選ぶ",
        )
        add(
            "tree rows",
            tree_height_number is not None and tree_height_number >= tree_target,
            f"{tree_height or 'unknown'}px (target {tree_target}+)",
            "表示リセット後、表示サイズを 大きめ にする",
        )
        add(
            "tabs",
            tab_vertical_padding is not None and tab_vertical_padding >= tab_target,
            f"vertical padding {tab_vertical_padding if tab_vertical_padding is not None else 'unknown'} (target {tab_target}+)",
            "表示リセットを実行する",
        )
        add(
            "buttons",
            button_vertical_padding is not None and button_vertical_padding >= button_target,
            f"vertical padding {button_vertical_padding if button_vertical_padding is not None else 'unknown'} (target {button_target}+)",
            "表示リセットを実行する",
        )
        add(
            "button text room",
            button_vertical_padding is not None
            and main_linespace is not None
            and button_vertical_padding * 2 >= text_room_target,
            f"vertical padding total {button_vertical_padding * 2 if button_vertical_padding is not None else 'unknown'}px / target {text_room_target}px / main line {main_linespace or 'unknown'}px",
            "表示リセットを実行し、改善しない場合は大きめを選ぶ",
        )
        add(
            "button label fit",
            button_label_fit_ok,
            f"{button_label_fit_detail} (min button {_scaled_action_button_min_width(self)}px)",
            "表示リセット後、改善しない場合は大きめ表示を使う",
        )
        add(
            "tk scaling",
            scaling_number is not None and scaling_number >= 1.0,
            f"{scaling_value} (target 1.0+)",
            "Windowsの表示倍率を確認し、auto-noteを再起動する",
        )
        add(
            "DPI awareness",
            _DPI_AWARENESS_ENABLED,
            f"requested={_DPI_AWARENESS_ENABLED}",
            "auto-noteを再起動して改善しない場合は問い合わせ一式ZIPを送る",
        )

        status = "OK" if all(ok for _label, ok, _detail, _action in checks) else "WARN"
        lines = [f"- status: {status}"]
        for label, ok, detail, action in checks:
            prefix = "OK" if ok else "WARN"
            suffix = "" if ok else f" / action: {action}"
            lines.append(f"- [{prefix}] {label}: {detail}{suffix}")
        return status, lines

    def _format_display_diagnostics(self) -> str:
        def _safe(callback) -> str:
            try:
                return str(callback())
            except tk.TclError as exc:
                return f"unavailable ({exc})"

        style = ttk.Style(self)
        saved_density = _normalise_ui_density(getattr(self.settings, "ui_density", "comfortable"))
        density = self._active_ui_density()
        safe_display = "on" if self.display_safe_mode else "off"
        safe_reason = self.display_safe_mode_reason or "none"
        scaling = _safe(lambda: self.tk.call("tk", "scaling"))
        fpixels = _safe(lambda: round(float(self.winfo_fpixels("1i")), 2))
        tree_height = _safe(lambda: style.lookup("Treeview", "rowheight"))
        tab_padding = _safe(lambda: style.lookup("TNotebook.Tab", "padding"))
        button_padding = _safe(lambda: style.lookup("TButton", "padding"))
        main_linespace = _safe(lambda: _font_linespace(self, UI_FONT, UI_TEXT_SIZE) or "unknown")
        small_linespace = _safe(lambda: _font_linespace(self, UI_FONT, UI_SMALL_TEXT_SIZE) or "unknown")
        badge_linespace = _safe(
            lambda: _font_linespace(self, UI_FONT, UI_BADGE_FONT_SIZE, weight=UI_BADGE_FONT_WEIGHT) or "unknown"
        )
        actual_font_family = _safe(lambda: _actual_font_family(self, UI_FONT, UI_TEXT_SIZE))
        crush_prone_font = "yes" if _is_crush_prone_font_family(UI_FONT) else "no"
        actual_crush_prone_font = "yes" if _is_crush_prone_font_family(actual_font_family) else "no"
        _status, readability_lines = self._display_readability_checks(style)
        button_label_fit_ok, button_label_fit_detail, button_label_fit_lines = self._button_label_fit_details(style)
        lines = [
            "Display diagnostics / 表示診断",
            "",
            f"generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"project: {self.project_dir}",
            "",
            "Readability check / 可読性チェック",
            *readability_lines,
            "",
            "Current display settings",
            f"- safe display mode: {safe_display}",
            f"- safe display reason: {safe_reason}",
            f"- safe display warnings: {len(self.display_safe_mode_warnings)}",
            f"- saved display density: {saved_density} / {_ui_density_label(saved_density)}",
            f"- display density: {density} / {_ui_density_label(density)}",
            f"- UI font: {UI_FONT}",
            f"- actual UI font: {actual_font_family}",
            f"- crush-prone font fallback: {crush_prone_font}",
            f"- actual crush-prone font fallback: {actual_crush_prone_font}",
            f"- code font: {CODE_FONT}",
            f"- text size: {UI_TEXT_SIZE}",
            f"- small text size: {UI_SMALL_TEXT_SIZE}",
            f"- badge font size: {UI_BADGE_FONT_SIZE}",
            f"- main font linespace: {main_linespace}",
            f"- small font linespace: {small_linespace}",
            f"- badge font linespace: {badge_linespace}",
            f"- text spacing: top {UI_TEXT_SPACING_TOP}, bottom {UI_TEXT_SPACING_BOTTOM}",
            f"- protected tree rowheight: {UI_TREE_ROW_HEIGHT}",
            f"- protected notebook tab padding: {UI_NOTEBOOK_TAB_PADDING}",
            f"- protected button padding: {UI_BUTTON_PADDING}",
            "",
            "Text fit sample / 文字収まりサンプル",
            f"- status: {'OK' if button_label_fit_ok else 'WARN'}",
            f"- widest sample: {button_label_fit_detail}",
            *button_label_fit_lines,
            "",
            "Window and screen",
            f"- window geometry: {self.geometry()}",
            f"- minimum size: {self.minsize()}",
            f"- screen: {self.winfo_screenwidth()}x{self.winfo_screenheight()}",
            f"- tk scaling: {scaling}",
            f"- pixels per inch: {fpixels}",
            f"- Windows DPI awareness requested: {_DPI_AWARENESS_ENABLED}",
            "",
            "Style metrics",
            f"- Treeview rowheight: {tree_height}",
            f"- Notebook tab padding: {tab_padding}",
            f"- Button padding: {button_padding}",
            "",
            "Recommended actions",
            "- 文字が潰れる時: ヘッダーの 表示 で 大きめ を選ぶ",
            "- フォントが Noto/BIZ/MS Gothic 系になった時: 表示リセット後に再起動する",
            "- 画面位置やサイズが扱いにくい時: 表示リセット を実行する",
            "- サポートへ送る時: この表示診断、GUIログ表示、復旧セットの結果を確認する",
        ]
        return "\n".join(lines)

    def run_overview_to_tab(self) -> None:
        try:
            report = build_overview(self.project_dir)
            path = write_overview_report(self.project_dir, report=report)
        except OSError as exc:
            self.notify("運用サマリー保存に失敗しました", level="error")
            messagebox.showerror("運用サマリーエラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            format_overview_report(report) + f"\n\nsaved: {path}",
        )
        self.notebook.select(self.diagnostics_tab)
        level = {"ready": "success", "check": "warning", "blocked": "error"}.get(report.status, "info")
        self.notify(f"運用サマリーを保存しました: {path.name}", level=level)

    def export_calendar_action(self) -> None:
        include_private = messagebox.askyesno(
            "予定ICS出力",
            "記事タイトルとファイル名を含めたICSを作成しますか？\n\n"
            "自分のGoogle/Outlookカレンダーに取り込む場合は「はい」。共有やサポート提出の可能性がある場合は「いいえ」。",
        )
        try:
            result = export_calendar(
                self.project_dir,
                self.articles_dir,
                pattern=self.settings.article_glob,
                include_private=include_private,
            )
        except OSError as exc:
            self.notify("予定ICS出力に失敗しました", level="error")
            messagebox.showerror("予定ICS出力エラー", str(exc))
            return
        text = (
            format_calendar_export(result)
            + "\n\n"
            + format_plan(self.articles_dir, pattern=self.settings.article_glob)
            + "\n\n"
            + format_calendar(self.articles_dir, pattern=self.settings.article_glob, days=30)
        )
        self._set_text(self.schedule_text, text)
        self.notebook.select(self.schedule_tab)
        level = "success" if result.event_count else "warning"
        privacy = "タイトル入り" if include_private else "匿名"
        self.notify(f"{privacy}ICSを保存しました: {result.path.name}", level=level)

    def run_quality_to_tab(self) -> None:
        checks = run_quality_checks(self.project_dir)
        self._set_text(self.diagnostics_text, format_quality_report(checks))
        self.notebook.select(self.diagnostics_tab)
        if any(check.status == "fail" for check in checks):
            level = "error"
        elif any(check.status == "warn" for check in checks):
            level = "warning"
        else:
            level = "success"
        self.notify("品質チェックを実行しました", level=level)

    def run_privacy_audit_to_tab(self) -> None:
        report = run_privacy_audit(self.project_dir)
        self._set_text(self.diagnostics_text, format_privacy_audit_report(report))
        self.notebook.select(self.diagnostics_tab)
        level = {"pass": "success", "warn": "warning", "fail": "error"}.get(report.status, "info")
        self.notify("プライバシー監査を実行しました", level=level)

    def run_quickstart_to_tab(self) -> None:
        report = run_quickstart(self.project_dir)
        self._set_text(self.diagnostics_text, format_quickstart_report(report))
        self.notebook.select(self.diagnostics_tab)
        self.notify("クイック確認を実行しました", level=self._quickstart_notify_level(report))

    def run_first_run_to_tab(self) -> None:
        report = self.refresh_first_run_panel(show_popup=False, select_tab=True)
        if report is None:
            report = run_first_run_checklist(self.project_dir)
        if hasattr(self, "diagnostics_text"):
            self._set_text(self.diagnostics_text, format_first_run_report(report))
        self.notify("初回チェックを表示しました", level=self._first_run_notify_level(report))

    def show_first_run_text(self) -> None:
        report = self.refresh_first_run_panel()
        if report is None:
            report = run_first_run_checklist(self.project_dir)
        self._set_text(self.diagnostics_text, format_first_run_report(report))
        self.notebook.select(self.diagnostics_tab)
        self.notify("初回チェックの診断テキストを表示しました", level=self._first_run_notify_level(report))

    def _first_run_notify_level(self, report) -> str:
        if not report.ok:
            return "error"
        if report.has_warnings:
            return "warning"
        return "success"

    def run_acceptance_to_tab(self) -> None:
        report = run_acceptance_check(self.project_dir)
        self._set_text(self.diagnostics_text, format_acceptance_report(report))
        self.notebook.select(self.diagnostics_tab)
        self.notify("受入チェックを実行しました", level=self._acceptance_notify_level(report))

    def create_acceptance_report_action(self) -> None:
        try:
            report = run_acceptance_check(self.project_dir)
            path = write_acceptance_report(self.project_dir, report=report)
        except OSError as exc:
            self.notify("受入チェック保存に失敗しました", level="error")
            messagebox.showerror("受入チェック保存エラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            format_acceptance_report(report) + f"\n\nsaved: {path}",
        )
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"受入チェックを保存しました: {path.name}", level=self._acceptance_notify_level(report))

    def create_full_acceptance_report_action(self) -> None:
        try:
            report = run_acceptance_check(
                self.project_dir,
                create=True,
                gui_smoke=True,
                smoke_helper=True,
            )
            path = write_acceptance_report(self.project_dir, report=report)
        except OSError as exc:
            self.notify("受入フル保存に失敗しました", level="error")
            messagebox.showerror("受入フル保存エラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            format_acceptance_report(report) + f"\n\nsaved: {path}",
        )
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"受入フルチェックを保存しました: {path.name}", level=self._acceptance_notify_level(report))

    def _acceptance_notify_level(self, report) -> str:
        if not report.ok:
            return "error"
        if report.has_warnings:
            return "warning"
        return "success"

    def run_sales_plan_to_tab(self) -> None:
        report = build_sales_plan(self.project_dir)
        self._set_text(self.diagnostics_text, format_sales_plan(report))
        self.notebook.select(self.diagnostics_tab)
        level = {"READY": "success", "NEEDS ATTENTION": "warning", "BLOCKED": "error"}.get(report.status, "info")
        self.notify("販売ナビを表示しました", level=level)

    def create_sales_plan_report_action(self) -> None:
        try:
            report = build_sales_plan(self.project_dir)
            path = write_sales_plan_report(self.project_dir, report=report)
        except OSError as exc:
            self.notify("販売ナビレポート保存に失敗しました", level="error")
            messagebox.showerror("販売ナビ保存エラー", str(exc))
            return
        text = format_sales_plan(report) + f"\n\nsaved: {path}"
        self._set_text(self.diagnostics_text, text)
        self.notebook.select(self.diagnostics_tab)
        _open_path(path)
        level = {"READY": "success", "NEEDS ATTENTION": "warning", "BLOCKED": "error"}.get(report.status, "info")
        self.notify(f"販売ナビレポートを保存しました: {path.name}", level=level)

    def create_commercial_setup_template_action(self) -> None:
        try:
            result = create_commercial_setup_template(self.project_dir)
            text = result.path.read_text(encoding="utf-8")
        except OSError as exc:
            self.notify("販売者テンプレートの作成に失敗しました", level="error")
            messagebox.showerror("販売者テンプレートエラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            f"販売者テンプレートを作成しました: {result.path}\nmissing: {result.missing}\n\n{text}",
        )
        self.notebook.select(self.diagnostics_tab)
        _open_path(result.path)
        level = "warning" if result.missing else "success"
        self.notify(f"販売者テンプレートを作成しました: {result.path.name}", level=level)

    def show_commercial_setup_status_action(self) -> None:
        settings = self._settings_preview_from_controls()
        missing = commercial_setup_missing_fields(settings)
        warnings = commercial_setup_warnings(settings)
        lines = [format_commercial_settings(settings)]
        if hasattr(self, "seller_name_var"):
            lines.append("")
            lines.append("note: 設定タブの未保存入力も含めて確認しています。販売素材へ反映するには設定を保存してください。")
        self._set_text(self.diagnostics_text, "\n".join(lines))
        self.notebook.select(self.diagnostics_tab)
        if missing:
            self.notify(f"販売者情報の未入力があります: {len(missing)}件", level="warning")
        elif warnings:
            self.notify(f"販売者情報に確認事項があります: {len(warnings)}件", level="warning")
        else:
            self.notify("販売者情報は販売素材向けに整っています", level="success")

    def apply_latest_commercial_setup_template_action(self) -> None:
        templates = list_commercial_setup_templates(self.project_dir)
        if not templates:
            messagebox.showinfo("テンプレ適用", "販売者テンプレートがまだありません。")
            self.notify("販売者テンプレートがありません", level="warning")
            return
        latest = templates[0]
        try:
            result = apply_commercial_setup_template(self.project_dir, latest)
        except (ArticleError, OSError) as exc:
            self.notify("販売者テンプレートの適用に失敗しました", level="error")
            messagebox.showerror("テンプレ適用エラー", str(exc))
            return
        self.settings = result.settings
        self.sync_settings_tab()
        self.refresh_home()
        self.refresh_help()
        self._set_text(
            self.diagnostics_text,
            format_commercial_setup_apply_result(result) + "\n\n" + format_commercial_settings(result.settings),
        )
        self.notebook.select(self.diagnostics_tab)
        if result.warnings or result.missing:
            self.notify(f"販売者テンプレートを適用しました: 未入力 {result.missing}", level="warning")
        else:
            self.notify(f"販売者テンプレートを適用しました: {latest.name}", level="success")

    def create_sales_materials_action(self) -> None:
        try:
            result = create_sales_materials(self.project_dir)
            text = result.path.read_text(encoding="utf-8")
        except OSError as exc:
            self.notify("販売素材の作成に失敗しました", level="error")
            messagebox.showerror("販売素材エラー", str(exc))
            return
        errors = verify_sales_materials(result.path, strict=True, project_dir=self.project_dir)
        verification = format_sales_materials_verification(result.path, errors, strict=True)
        self._set_text(
            self.diagnostics_text,
            f"販売素材を作成しました: {result.path}\nplaceholders: {result.placeholders}\n\n{verification}\n\n{text}",
        )
        self.notebook.select(self.diagnostics_tab)
        _open_path(result.path)
        level = "warning" if errors else "success"
        self.notify(f"販売素材を作成しました: {result.path.name}", level=level)

    def verify_latest_sales_materials_action(self) -> None:
        materials = list_sales_materials(self.project_dir)
        if not materials:
            messagebox.showinfo("販売素材検証", "販売素材Markdownがまだありません。")
            self.notify("販売素材Markdownがありません", level="warning")
            return
        latest = materials[0]
        errors = verify_sales_materials(latest, strict=True, project_dir=self.project_dir)
        self._set_text(
            self.diagnostics_text,
            format_sales_materials_verification(latest, errors, strict=True),
        )
        self.notebook.select(self.diagnostics_tab)
        if errors:
            self.notify("販売素材Markdownの検証で確認事項が見つかりました", level="warning")
        else:
            self.notify(f"販売素材Markdownを検証しました: {latest.name}", level="success")

    def create_sales_screenshots_action(self) -> None:
        try:
            pack = create_sales_screenshot_pack(self.project_dir)
        except OSError as exc:
            self.notify("掲載画像パックの作成に失敗しました", level="error")
            messagebox.showerror("掲載画像エラー", str(exc))
            return
        errors = verify_sales_screenshot_pack(pack.directory)
        text = (
            f"{format_sales_screenshot_pack(pack)}\n\n"
            f"{format_sales_screenshot_verification(pack.directory, errors)}"
        )
        self._set_text(self.diagnostics_text, text)
        self.notebook.select(self.diagnostics_tab)
        _open_path(pack.html_path)
        self.refresh_home()
        level = "warning" if errors else "success"
        self.notify(f"掲載画像パックを作成しました: {pack.directory.name}", level=level)

    def verify_latest_sales_screenshots_action(self) -> None:
        packs = list_sales_screenshot_packs(self.project_dir)
        if not packs:
            messagebox.showinfo("掲載画像検証", "掲載画像パックがまだありません。")
            self.notify("掲載画像パックがありません", level="warning")
            return
        latest = packs[0]
        errors = verify_sales_screenshot_pack(latest)
        self._set_text(
            self.diagnostics_text,
            format_sales_screenshot_verification(latest, errors),
        )
        self.notebook.select(self.diagnostics_tab)
        if errors:
            self.notify("掲載画像パックの検証で確認事項が見つかりました", level="warning")
        else:
            self.notify(f"掲載画像パックを検証しました: {latest.name}", level="success")

    def create_sales_listing_kit_action(self) -> None:
        try:
            kit = create_sales_listing_kit(self.project_dir, strict=True)
        except OSError as exc:
            self.notify("掲載キットの作成に失敗しました", level="error")
            messagebox.showerror("掲載キットエラー", str(exc))
            return
        errors = verify_sales_listing_kit(kit.directory, strict=True, project_dir=self.project_dir)
        package_errors = verify_sales_listing_kit(kit.package_path, strict=True, project_dir=self.project_dir)
        text = "\n\n".join(
            [
                format_sales_listing_kit(kit),
                format_sales_listing_verification(kit.directory, errors, strict=True),
                format_sales_listing_verification(kit.package_path, package_errors, strict=True),
            ]
        )
        self._set_text(self.diagnostics_text, text)
        self.notebook.select(self.diagnostics_tab)
        _open_path(kit.directory)
        _open_path(kit.package_path)
        _open_path(kit.directory / "index.html")
        self.refresh_home()
        level = "warning" if errors or package_errors else "success"
        self.notify(f"掲載キットを作成しました: {kit.directory.name}", level=level)

    def verify_latest_sales_listing_kit_action(self) -> None:
        kits = list_sales_listing_kits(self.project_dir)
        packages = list_sales_listing_packages(self.project_dir)
        if not kits and not packages:
            messagebox.showinfo("掲載キット検証", "掲載キットがまだありません。")
            self.notify("掲載キットがありません", level="warning")
            return
        parts: list[str] = []
        has_errors = False
        if kits:
            latest_kit = kits[0]
            errors = verify_sales_listing_kit(latest_kit, strict=True, project_dir=self.project_dir)
            has_errors = has_errors or bool(errors)
            parts.append(format_sales_listing_verification(latest_kit, errors, strict=True))
        if packages:
            latest_package = packages[0]
            errors = verify_sales_listing_kit(latest_package, strict=True, project_dir=self.project_dir)
            has_errors = has_errors or bool(errors)
            parts.append(format_sales_listing_verification(latest_package, errors, strict=True))
        self._set_text(self.diagnostics_text, "\n\n".join(parts))
        self.notebook.select(self.diagnostics_tab)
        if has_errors:
            self.notify("掲載キットの検証で確認事項が見つかりました", level="warning")
        else:
            self.notify("掲載キットを検証しました", level="success")

    def create_sales_finalize_action(self) -> None:
        self._create_sales_finalize_action(apply_latest_template=False)

    def create_sales_finalize_with_template_action(self) -> None:
        self._create_sales_finalize_action(apply_latest_template=True)

    def _create_sales_finalize_action(self, *, apply_latest_template: bool) -> None:
        label = "テンプレ取込一括" if apply_latest_template else "販売一括作成"
        try:
            report = create_sales_finalize(self.project_dir, apply_latest_template=apply_latest_template)
            text = format_sales_finalize_details(report)
        except Exception as exc:
            self.notify(f"{label}に失敗しました", level="error")
            messagebox.showerror(f"{label}エラー", str(exc))
            return
        self._set_text(self.diagnostics_text, text)
        self.notebook.select(self.diagnostics_tab)
        if has_sales_finalize_blockers(report):
            self.notify(f"{label}でNGが見つかりました", level="error")
            return
        self._refresh_home_sales_summary()
        level = "warning" if report.has_warnings else "success"
        if report.buyer_delivery_package_path:
            _open_path(report.buyer_delivery_package_path)
            if report.buyer_delivery_message_path:
                _open_path(report.buyer_delivery_message_path)
            if report.buyer_delivery_dir:
                support_request_path = _buyer_support_request_for(report.buyer_delivery_dir)
                if support_request_path.exists():
                    _open_path(support_request_path)
            if report.sales_plan_report_path:
                _open_path(report.sales_plan_report_path)
            if report.seller_send_checklist_path:
                _open_path(report.seller_send_checklist_path)
            if report.sales_evidence_manifest_path:
                _open_path(report.sales_evidence_manifest_path)
            if report.sales_screenshot_pack_path:
                screenshot_preview = report.sales_screenshot_pack_path / "index.html"
                _open_path(screenshot_preview if screenshot_preview.exists() else report.sales_screenshot_pack_path)
            if report.sales_listing_package_path:
                _open_path(report.sales_listing_package_path)
            if report.sales_listing_kit_path:
                listing_preview = report.sales_listing_kit_path / "index.html"
                _open_path(listing_preview if listing_preview.exists() else report.sales_listing_kit_path)
            self.notify(f"{label}が完了しました: {report.buyer_delivery_package_path.name}", level=level)
        elif report.buyer_delivery_dir:
            _open_path(report.buyer_delivery_dir)
            self.notify(f"{label}が完了しました: {report.buyer_delivery_dir.name}", level=level)
        elif report.sales_handoff_path:
            _open_path(report.sales_handoff_path)
            self.notify(f"{label}が完了しました: {report.sales_handoff_path.name}", level=level)
        elif report.report_path:
            _open_path(report.report_path)
            self.notify(f"販売一括レポートを作成しました: {report.report_path.name}", level=level)
        else:
            self.notify(f"{label}が完了しました", level=level)

    def run_commercial_readiness_to_tab(self) -> None:
        report = run_commercial_readiness(self.project_dir)
        self._set_text(self.diagnostics_text, format_commercial_readiness_report(report))
        self.notebook.select(self.diagnostics_tab)
        self.notify("販売準備を確認しました", level=self._commercial_readiness_notify_level(report))

    def create_commercial_readiness_report_action(self) -> None:
        try:
            report = run_commercial_readiness(self.project_dir)
            path = write_commercial_readiness_report(self.project_dir, report=report)
        except OSError as exc:
            self.notify("販売準備レポート保存に失敗しました", level="error")
            messagebox.showerror("販売準備保存エラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            format_commercial_readiness_report(report) + f"\n\nsaved: {path}",
        )
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"販売準備レポートを保存しました: {path.name}", level=self._commercial_readiness_notify_level(report))

    def create_commercial_policy_review_action(self) -> None:
        try:
            path = write_commercial_policy_review(self.project_dir)
        except OSError as exc:
            self.notify("方針レビュー保存に失敗しました", level="error")
            messagebox.showerror("方針レビュー保存エラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            format_commercial_policy_review(self.project_dir, review_path=path) + f"\n\nsaved: {path}",
        )
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"方針レビューを保存しました: {path.name}", level="success")

    def run_sales_review_to_tab(self) -> None:
        report = run_sales_review(self.project_dir)
        self._set_text(self.diagnostics_text, format_sales_review(report))
        self.notebook.select(self.diagnostics_tab)
        self.notify("販売ページ・納品最終レビューを表示しました", level=self._sales_review_notify_level(report))

    def create_sales_review_report_action(self) -> None:
        try:
            report = run_sales_review(self.project_dir)
            path = write_sales_review_report(self.project_dir, report=report)
        except OSError as exc:
            self.notify("最終レビュー保存に失敗しました", level="error")
            messagebox.showerror("最終レビュー保存エラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            format_sales_review(report) + f"\n\nsaved: {path}",
        )
        self.notebook.select(self.diagnostics_tab)
        _open_path(path)
        self.notify(f"最終レビューを保存しました: {path.name}", level=self._sales_review_notify_level(report))

    def run_sales_launch_to_tab(self) -> None:
        report = run_sales_launch_check(self.project_dir)
        self._set_text(self.diagnostics_text, format_sales_launch_checklist(report))
        self.notebook.select(self.diagnostics_tab)
        self.notify("販売直前チェックを表示しました", level=self._sales_launch_notify_level(report))

    def create_sales_launch_checklist_action(self) -> None:
        try:
            report = run_sales_launch_check(self.project_dir)
            path = write_sales_launch_checklist(self.project_dir, report=report)
        except OSError as exc:
            self.notify("販売直前チェック保存に失敗しました", level="error")
            messagebox.showerror("販売直前チェック保存エラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            format_sales_launch_checklist(report) + f"\n\nsaved: {path}",
        )
        self.notebook.select(self.diagnostics_tab)
        self._refresh_home_reports()
        _open_path(path)
        self.notify(f"販売直前チェックを保存しました: {path.name}", level=self._sales_launch_notify_level(report))

    def create_sales_launch_confirmation_action(self) -> None:
        report = run_sales_launch_check(self.project_dir)
        if has_sales_launch_blockers(report):
            self._set_text(self.diagnostics_text, format_sales_launch_checklist(report))
            self.notebook.select(self.diagnostics_tab)
            self.notify("販売直前チェックにNGがあるため確認記録は保存していません", level="error")
            messagebox.showwarning(
                "販売確認記録",
                "販売直前チェックにNGがあります。先にNGを解消してから、実画面確認後に記録してください。",
            )
            return
        note = simpledialog.askstring(
            "販売確認記録",
            "販売ページのプレビュー/テスト購入相当で確認したメモを入力してください。空欄でも保存できます。",
            parent=self,
        )
        if note is None:
            self.notify("販売確認記録をキャンセルしました", level="info")
            return
        try:
            path = write_sales_launch_confirmation(self.project_dir, report=report, note=note)
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self.notify("販売確認記録の保存に失敗しました", level="error")
            messagebox.showerror("販売確認記録エラー", str(exc))
            return
        self._set_text(self.diagnostics_text, text)
        self.notebook.select(self.diagnostics_tab)
        self._refresh_home_reports()
        _open_path(path)
        self.notify(f"販売確認記録を保存しました: {path.name}", level=self._sales_launch_notify_level(report))

    def _sales_review_notify_level(self, report) -> str:
        if has_sales_review_blockers(report):
            return "error"
        if report.has_warnings:
            return "warning"
        return "success"

    def _sales_launch_notify_level(self, report) -> str:
        if has_sales_launch_blockers(report):
            return "error"
        if report.has_warnings:
            return "warning"
        return "success"

    def _commercial_readiness_notify_level(self, report) -> str:
        if not report.ok:
            return "error"
        if report.has_warnings:
            return "warning"
        return "success"

    def run_self_test_to_tab(self) -> None:
        report = run_self_test(self.project_dir)
        self._set_text(self.diagnostics_text, format_self_test_report(report))
        self.notebook.select(self.diagnostics_tab)
        self.notify("セルフテストを実行しました", level=self._self_test_notify_level(report))

    def create_self_test_report_action(self) -> None:
        try:
            report = run_self_test(self.project_dir)
            path = write_self_test_report(self.project_dir, report=report)
        except OSError as exc:
            self.notify("セルフテスト保存に失敗しました", level="error")
            messagebox.showerror("セルフテスト保存エラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            format_self_test_report(report) + f"\n\nsaved: {path}",
        )
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"セルフテストを保存しました: {path.name}", level=self._self_test_notify_level(report))

    def _self_test_notify_level(self, report) -> str:
        if not report.ok:
            return "error"
        if report.has_warnings:
            return "warning"
        return "success"

    def run_workflow_smoke_to_tab(self) -> None:
        try:
            report = run_workflow_smoke(self.project_dir)
            path = write_workflow_smoke_report(self.project_dir, report=report)
        except Exception as exc:
            self.notify("E2E確認に失敗しました", level="error")
            messagebox.showerror("E2E確認エラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            format_workflow_smoke_report(report) + f"\n\nsaved: {path}",
        )
        self.notebook.select(self.diagnostics_tab)
        self.notify("E2E確認を実行しました", level=self._workflow_smoke_notify_level(report))

    def _workflow_smoke_notify_level(self, report) -> str:
        if not report.ok:
            return "error"
        if report.has_warnings:
            return "warning"
        return "success"

    def run_home_primary_action(self) -> None:
        step = self._home_primary_step
        if step is None:
            report = build_action_plan(self.project_dir)
            step = report.steps[0] if report.steps else None
        if step is None:
            self.run_action_plan_to_tab()
            return
        self._run_action_plan_step(step)

    def _run_action_plan_step(self, step: ActionPlanStep) -> None:
        title = step.title
        if title in {
            "投稿キューの先頭記事を直す",
            "投稿キューの確認項目を見る",
            "投稿キューの準備OK記事を投稿する",
        }:
            self._run_publish_queue_action_step(step)
        elif title == "セットアップを修復する":
            self.run_repair_to_tab()
        elif title == "製品品質のNGを確認する":
            self.run_quality_to_tab()
        elif title in {"トラブル診断を確認する", "トラブル診断のNGを確認する"}:
            self.run_troubleshoot_to_tab()
        elif title in {"販売者情報を埋める", "販売者情報の公開URLを確認する"}:
            self.focus_next_commercial_missing_field()
        elif title == "最初の記事を作る":
            self.create_practice_article_action()
        elif title == "公開前チェックを直す":
            self.run_check_all(True)
        elif title in {"記事レビューで仕上げる", "記事の仕上げ項目を確認する"}:
            self.review_all_to_tab()
        elif title == "バックアップを作成する":
            self.create_backup_action()
        elif title == "危険生成物を確認する":
            self.preview_privacy_failed_cleanup_action()
        elif title == "配布ZIPを作成/検証する":
            self.run_preflight_create_release_to_tab()
        elif title == "noteログインを確認する":
            self.show_note_login_safety_action()
        elif title == "投稿ヘルパーでnoteへ貼り付ける":
            self.open_helper()
        elif title == "公開後URLを保存する":
            self.notebook.select(self.article_tab)
            self.notify("記事を選び、公開URLを入れて公開済みにしてください。", level="info")
        elif title == "出荷前チェックを通す":
            self.run_preflight_to_tab()
        else:
            self.run_action_plan_to_tab()

    def _run_publish_queue_action_step(self, step: ActionPlanStep) -> None:
        if not step.target_path:
            self.publish_queue_to_tab()
            return
        article = self.select_article_path(Path(step.target_path), select_tab=True)
        if article is None:
            self.publish_queue_to_tab()
            return
        if step.title == "投稿キューの準備OK記事を投稿する":
            self.open_helper()
            return
        try:
            plan = build_improvement_plan(
                article.source,
                append_tags=self.settings.append_tags_by_default,
            )
        except ArticleError:
            report = self.refresh_publish_ready_panel(article=article, show_popup=False, smoke_helper=False)
            if report is not None:
                self._set_check_text(format_publish_ready_report(report))
            self.notebook.select(self.article_tab)
            self.notify("投稿キューの対象記事を開きました", level=self._publish_ready_notify_level(report.status) if report else "info")
            return
        self._last_improvement_plan = plan
        self.refresh_publish_ready_panel(article=article, show_popup=False, smoke_helper=False)
        self._set_check_text(format_improvement_plan(plan))
        self.notebook.select(self.check_tab)
        self.notify("投稿キューの対象記事の改善プランを表示しました", level=self._improvement_plan_notify_level(plan))

    def run_action_plan_to_tab(self) -> None:
        report = build_action_plan(self.project_dir)
        self._set_text(self.diagnostics_text, format_action_plan(report))
        self.notebook.select(self.diagnostics_tab)
        self.notify("アクションプランを表示しました", level=self._action_plan_notify_level(report))

    def run_action_plan_to_check_tab(self) -> None:
        report = build_action_plan(self.project_dir)
        self._set_check_text(format_action_plan(report))
        self.notebook.select(self.check_tab)
        self.notify("アクションプランを表示しました", level=self._action_plan_notify_level(report))

    def _action_plan_notify_level(self, report) -> str:
        severities = {step.severity for step in report.steps}
        if "blocker" in severities:
            return "error"
        if severities & {"warning", "maintenance"}:
            return "warning"
        return "success"

    def run_quickstart_helper_smoke_to_tab(self) -> None:
        report = run_quickstart(self.project_dir, smoke_helper=True)
        self._set_text(self.diagnostics_text, format_quickstart_report(report))
        self.notebook.select(self.diagnostics_tab)
        if report.helper_path:
            self.notify(f"ヘルパーHTMLを生成しました: {report.helper_path.name}", level=self._quickstart_notify_level(report))
        else:
            self.notify("ヘルパー生成確認を実行しました", level=self._quickstart_notify_level(report))

    def _quickstart_notify_level(self, report) -> str:
        if not report.ok:
            return "error"
        if report.has_warnings:
            return "warning"
        return "success"

    def run_release_check_full_action(self) -> None:
        running_thread = self._release_check_thread
        if running_thread is not None and running_thread.is_alive():
            self.notify("販売前一括チェックは実行中です。完了まで待ってください。", level="warning")
            return
        script_path = self.project_dir / "scripts" / "check-release.ps1"
        if not script_path.exists():
            message = f"販売前一括チェックのスクリプトが見つかりません: {script_path}"
            self._set_text(self.diagnostics_text, message)
            self.notebook.select(self.diagnostics_tab)
            self.notify("販売前一括チェックを開始できませんでした", level="error")
            return
        if not messagebox.askyesno(
            "販売前一括チェック",
            "ユニットテスト、品質ゲート、GUIスモーク、プライバシー監査、インストール/販売納品スモークをまとめて実行します。\n\n"
            "時間がかかるため、バックグラウンドで実行して結果を .auto-note\\reports に保存します。開始しますか？",
        ):
            self.notify("販売前一括チェックをキャンセルしました", level="info")
            return

        started_at = datetime.now()
        report_path = _release_check_report_path(self.project_dir)
        display_command = (
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\check-release.ps1 "
            "-ProjectDir <PROJECT_DIR> -Full"
        )
        initial_text = _format_release_check_output(
            status="RUNNING",
            exit_code=None,
            started_at=started_at,
            finished_at=None,
            command=display_command,
            stdout="販売前一括チェックを実行中です。完了後、この画面と直近レポートを更新します。",
            stderr="",
        )
        safe_initial_text = mask_text(initial_text, self.project_dir)
        try:
            write_text_atomic(report_path, safe_initial_text)
        except OSError as exc:
            self.notify("販売前一括チェックのレポート作成に失敗しました", level="error")
            messagebox.showerror("販売前一括チェック", str(exc))
            return
        self._set_text(self.diagnostics_text, safe_initial_text + f"\nsaved: {report_path}\n")
        self.notebook.select(self.diagnostics_tab)
        self._refresh_home_reports()
        self._refresh_home_sales_summary()
        self.notify(f"販売前一括チェックを開始しました: {report_path.name}", level="info")

        thread = threading.Thread(
            target=self._run_release_check_full_worker,
            args=(script_path, report_path, started_at, display_command),
            daemon=True,
        )
        self._release_check_thread = thread
        thread.start()

    def _run_release_check_full_worker(
        self,
        script_path: Path,
        report_path: Path,
        started_at: datetime,
        display_command: str,
    ) -> None:
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-ProjectDir",
            str(self.project_dir),
            "-Full",
        ]
        exit_code: int | None = None
        try:
            completed = subprocess.run(
                command,
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                errors="replace",
            )
            exit_code = int(completed.returncode)
            stdout = completed.stdout
            stderr = completed.stderr
            status = "OK" if exit_code == 0 else "NG"
        except Exception:
            stdout = ""
            stderr = traceback.format_exc()
            status = "NG"
        finished_at = datetime.now()
        text = _format_release_check_output(
            status=status,
            exit_code=exit_code,
            started_at=started_at,
            finished_at=finished_at,
            command=display_command,
            stdout=stdout,
            stderr=stderr,
        )
        safe_text = mask_text(text, self.project_dir)
        try:
            write_text_atomic(report_path, safe_text)
        except OSError as exc:
            safe_text += f"\n[NG] レポート保存に失敗しました: {exc}\n"
            status = "NG"

        try:
            self.after(0, lambda: self._finish_release_check_full(report_path, safe_text, status))
        except tk.TclError:
            pass

    def _finish_release_check_full(self, report_path: Path, text: str, status: str) -> None:
        self._release_check_thread = None
        self._set_text(self.diagnostics_text, text + f"\nsaved: {report_path}\n")
        self.notebook.select(self.diagnostics_tab)
        self._refresh_home_reports()
        self._refresh_home_sales_summary()
        if status == "OK":
            self.notify(f"販売前一括チェックが完了しました: {report_path.name}", level="success")
        else:
            self.notify(f"販売前一括チェックで確認が必要です: {report_path.name}", level="error")

    def run_preflight_to_tab(self) -> None:
        report = run_preflight(self.project_dir, gui_smoke=True)
        self._set_text(self.diagnostics_text, format_preflight_report(report))
        self.notebook.select(self.diagnostics_tab)
        self.notify("出荷前チェックを実行しました", level=self._preflight_notify_level(report.status))

    def run_preflight_create_release_to_tab(self) -> None:
        try:
            report = run_preflight(self.project_dir, create_release=True, gui_smoke=True)
        except OSError as exc:
            self.notify("出荷ZIP作成に失敗しました", level="error")
            messagebox.showerror("出荷ZIPエラー", str(exc))
            return
        self._set_text(self.diagnostics_text, format_preflight_report(report))
        self.notebook.select(self.diagnostics_tab)
        if report.created_release:
            self.notify(
                f"出荷ZIPを作成しました: {report.created_release.name}",
                level=self._preflight_notify_level(report.status),
            )
        else:
            self.notify("出荷前チェックを実行しました", level=self._preflight_notify_level(report.status))

    def _preflight_notify_level(self, status: str) -> str:
        if status == "fail":
            return "error"
        if status == "warn":
            return "warning"
        return "success"

    def run_readiness_to_tab(self) -> None:
        report = run_readiness(self.project_dir)
        self._set_text(self.diagnostics_text, format_readiness_report(report))
        self.notebook.select(self.diagnostics_tab)
        self.notify("準備度を確認しました", level="success" if report.ok else "warning")

    def run_troubleshoot_to_tab(self) -> None:
        report = run_troubleshoot(self.project_dir)
        self._set_text(self.diagnostics_text, format_troubleshoot_report(report))
        self.notebook.select(self.diagnostics_tab)
        level = {"pass": "success", "warn": "warning", "fail": "error"}.get(report.status, "info")
        self.notify("トラブル診断を実行しました", level=level)

    def run_recovery_kit_to_tab(self) -> None:
        if not messagebox.askyesno(
            "復旧セット",
            "安全な基本修復、再診断、必要時の問い合わせ一式ZIP作成をまとめて実行します。\n\n"
            "記事は変更しません。古い生成物やプライバシー監査NG生成物の削除も行いません。",
        ):
            return
        try:
            report = run_recovery_kit(self.project_dir)
            report_path = write_recovery_kit_report(self.project_dir, report=report)
        except OSError as exc:
            self.notify("復旧セットに失敗しました", level="error")
            messagebox.showerror("復旧セットエラー", str(exc))
            return
        self.settings = load_settings(self.project_dir)
        self.sync_settings_tab()
        self.refresh_all()
        self._refresh_support_summary()
        try:
            display_path = report_path.resolve().relative_to(self.project_dir.resolve())
        except ValueError:
            display_path = Path(report_path.name)
        self._set_text(
            self.diagnostics_text,
            "\n\n".join(
                [
                    format_recovery_kit_report(report),
                    f"Saved report: {display_path}",
                    "サポートへ共有する場合は、最新復旧レポート または 復旧レポートコピー を使えます。",
                ]
            ),
        )
        self.notebook.select(self.diagnostics_tab)
        level = {"pass": "success", "warn": "warning", "fail": "error"}.get(report.status, "info")
        self.notify(f"復旧セットを実行し、レポートを保存しました: {report_path.name}", level=level)

    def run_repair_to_tab(self) -> None:
        if not messagebox.askyesno(
            "自動修復",
            "基本フォルダ、設定、アイデア保存を安全に再作成します。\n\n"
            "記事は変更しません。古い生成物やプライバシー監査NG生成物の削除は、この操作では行いません。",
        ):
            report = run_repair(self.project_dir)
            self._set_text(self.diagnostics_text, format_repair_report(report))
            self.notebook.select(self.diagnostics_tab)
            return
        try:
            report = run_repair(self.project_dir, apply=True)
        except OSError as exc:
            self.notify("自動修復に失敗しました", level="error")
            messagebox.showerror("自動修復エラー", str(exc))
            return
        self.settings = load_settings(self.project_dir)
        self.sync_settings_tab()
        self.refresh_all()
        self._set_text(self.diagnostics_text, format_repair_report(report))
        self.notebook.select(self.diagnostics_tab)
        level = "warning" if any(item.status == "warn" for item in report.items) else "success"
        self.notify("自動修復を実行しました", level=level)

    def run_setup_to_tab(self) -> None:
        self._set_text(self.diagnostics_text, format_setup_report(run_setup_check(self.project_dir, create=True)))
        self.notebook.select(self.diagnostics_tab)
        self.notify("セットアップ確認を実行しました", level="success")

    def preview_diagnostic_report_action(self) -> None:
        self._set_text(self.diagnostics_text, preview_diagnostic_report(self.project_dir))
        self.notebook.select(self.diagnostics_tab)
        self.notify("診断レポートの内容をプレビューしました", level="success")

    def create_backup_action(self) -> None:
        try:
            path = create_backup(self.project_dir)
        except OSError as exc:
            self.notify("バックアップ作成に失敗しました", level="error")
            messagebox.showerror("バックアップエラー", str(exc))
            return
        self.run_diagnostics_to_tab()
        self.notify(f"バックアップを作成しました: {path.name}", level="success")

    def inspect_backup_action(self) -> None:
        path = self._ask_backup_zip("確認するバックアップZIPを選択")
        if not path:
            return
        try:
            inspection = inspect_backup(path)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            self.notify("バックアップ確認に失敗しました", level="error")
            messagebox.showerror("バックアップ確認エラー", str(exc))
            return
        self._set_text(self.diagnostics_text, format_backup_inspection(inspection))
        self.notebook.select(self.diagnostics_tab)
        self.notify("バックアップ内容を確認しました", level="success" if inspection.ok else "warning")

    def restore_backup_action(self) -> None:
        if not self.confirm_editor_changes():
            return
        path = self._ask_backup_zip("復元するバックアップZIPを選択")
        if not path:
            return
        try:
            inspection = inspect_backup(path)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            self.notify("バックアップ確認に失敗しました", level="error")
            messagebox.showerror("バックアップ確認エラー", str(exc))
            return
        self._set_text(self.diagnostics_text, format_backup_inspection(inspection))
        if not inspection.ok:
            self.notebook.select(self.diagnostics_tab)
            self.notify("このバックアップは復元できません", level="error")
            messagebox.showerror(
                "バックアップ復元エラー",
                "このZIPは復元できません。診断タブのバックアップ確認結果を見てください。",
            )
            return
        if not messagebox.askyesno(
            "バックアップ復元",
            _backup_restore_confirmation(inspection)
            + "\n\n"
            "復元前に現在の状態の安全バックアップを作成します。続行しますか？",
        ):
            return
        try:
            result = restore_backup(self.project_dir, Path(path), create_safety_backup=True)
            self.settings = load_settings(self.project_dir)
            self.sync_settings_tab()
            self.refresh_all()
            self.run_diagnostics_to_tab()
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            self.notify("バックアップ復元に失敗しました", level="error")
            messagebox.showerror("バックアップ復元エラー", str(exc))
            return
        detail = f"{len(result.restored_files)}件を復元しました。"
        if result.safety_backup:
            detail += f"\n安全バックアップ: {result.safety_backup.name}"
        messagebox.showinfo("バックアップ復元", detail)
        self.notify("バックアップを復元しました", level="success")

    def _ask_backup_zip(self, title: str) -> Path | None:
        initial_dir = self.project_dir / ".auto-note" / "backups"
        if not initial_dir.exists():
            initial_dir = self.project_dir / ".auto-note" / "install-backups"
        path = filedialog.askopenfilename(
            parent=self,
            title=title,
            initialdir=str(initial_dir if initial_dir.exists() else self.project_dir),
            filetypes=(("Backup zip", "*.zip"), ("All files", "*.*")),
        )
        return Path(path) if path else None

    def create_diagnostic_report_action(self) -> None:
        try:
            path = create_diagnostic_report(self.project_dir)
        except OSError as exc:
            self.notify("診断レポート作成に失敗しました", level="error")
            messagebox.showerror("診断レポートエラー", str(exc))
            return
        self.run_diagnostics_to_tab()
        self.notify(f"診断レポートを作成しました: {path.name}", level="success")

    def open_latest_diagnostic_report_location_action(self) -> None:
        reports = list_diagnostic_reports(self.project_dir)
        if not reports:
            messagebox.showinfo("診断ZIP場所", "診断レポートZIPがまだありません。先に 診断レポート を作成してください。")
            self.notify("診断レポートZIPがありません", level="warning")
            return
        latest = reports[0]
        _open_path(latest.parent)
        self.notify(f"最新診断ZIPの場所を開きました: {latest.name}", level="success")

    def verify_latest_diagnostic_report_action(self) -> None:
        reports = list_diagnostic_reports(self.project_dir)
        if not reports:
            messagebox.showinfo("診断ZIP検証", "診断レポートZIPがまだありません。先に 診断レポート を作成してください。")
            self.notify("診断レポートZIPがありません", level="warning")
            return
        latest = reports[0]
        errors = verify_diagnostic_report(latest)
        self._set_text(self.diagnostics_text, format_diagnostic_report_verification(latest, errors))
        self.notebook.select(self.diagnostics_tab)
        if errors:
            self.notify("診断レポートZIPの検証で問題が見つかりました", level="error")
        else:
            self.notify(f"診断レポートZIPを検証しました: {latest.name}", level="success")

    def copy_latest_diagnostic_report_path_action(self) -> None:
        reports = list_diagnostic_reports(self.project_dir)
        if not reports:
            messagebox.showinfo("診断ZIPパス", "診断レポートZIPがまだありません。先に 診断レポート を作成してください。")
            self.notify("診断レポートZIPがありません", level="warning")
            return
        latest = reports[0]
        try:
            self.clipboard_clear()
            self.clipboard_append(str(latest.resolve()))
            self.update_idletasks()
        except tk.TclError as exc:
            self.notify("診断レポートZIPのパスをコピーできませんでした", level="error")
            messagebox.showerror("診断ZIPパス", str(exc))
            return
        self.notify(f"診断レポートZIPのパスをコピーしました: {latest.name}", level="success")

    def create_release_action(self) -> None:
        try:
            path = create_release_package(self.project_dir)
        except OSError as exc:
            self.notify("配布ZIP作成に失敗しました", level="error")
            messagebox.showerror("配布ZIPエラー", str(exc))
            return
        self.run_diagnostics_to_tab()
        self.notify(f"配布ZIPを作成しました: {path.name}", level="success")

    def export_inventory_action(self) -> None:
        try:
            path = export_article_inventory(self.project_dir)
        except ArticleError as exc:
            self.notify("CSV出力に失敗しました", level="error")
            messagebox.showerror("CSV出力エラー", str(exc))
            return
        self.run_diagnostics_to_tab()
        self.notify(f"記事CSVを出力しました: {path.name}", level="success")

    def verify_latest_release_action(self) -> None:
        releases = list_releases(self.project_dir)
        if not releases:
            messagebox.showinfo("配布ZIP", "まだ配布ZIPがありません。")
            return
        path = releases[0]
        errors = verify_release_package(path)
        self._set_text(self.diagnostics_text, format_release_verification(path, errors))
        self.notebook.select(self.diagnostics_tab)
        self.notify("最新配布ZIPを検証しました", level="error" if errors else "success")

    def create_sales_handoff_action(self) -> None:
        try:
            result = create_sales_handoff(self.project_dir)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            self.notify("販売用一式の作成に失敗しました", level="error")
            messagebox.showerror("販売用一式エラー", str(exc))
            return
        errors = verify_sales_handoff(result.path)
        privacy = run_privacy_audit(self.project_dir)
        self._set_text(
            self.diagnostics_text,
            "\n\n".join(
                [
                    f"販売用一式を作成しました: {result.path}",
                    f"同梱配布ZIP: {result.release_path.name}",
                    f"販売準備WARN: {result.warnings}",
                    format_sales_handoff_verification(result.path, errors),
                    format_privacy_audit_report(privacy),
                ]
            ),
        )
        self.notebook.select(self.diagnostics_tab)
        if errors:
            self.notify("販売用一式ZIPの検証で問題が見つかりました", level="error")
            return
        if has_privacy_audit_blockers(privacy):
            self.notify("販売用一式の送付前チェックで問題が見つかりました", level="error")
            return
        level = "warning" if result.warnings else "success"
        self.notify(f"販売用一式を作成しました: {result.path.name}", level=level)
        _open_path(result.path)

    def verify_latest_sales_handoff_action(self) -> None:
        handoffs = list_sales_handoffs(self.project_dir)
        if not handoffs:
            messagebox.showinfo("販売用一式検証", "販売用一式ZIPがまだありません。")
            self.notify("販売用一式ZIPがありません", level="warning")
            return
        latest = handoffs[0]
        errors = verify_sales_handoff(latest)
        self._set_text(self.diagnostics_text, format_sales_handoff_verification(latest, errors))
        self.notebook.select(self.diagnostics_tab)
        if errors:
            self.notify("販売用一式ZIPの検証で問題が見つかりました", level="error")
        else:
            self.notify(f"販売用一式ZIPを検証しました: {latest.name}", level="success")

    def extract_latest_buyer_delivery_action(self) -> None:
        handoffs = list_sales_handoffs(self.project_dir)
        if not handoffs:
            messagebox.showinfo("購入者ZIP抽出", "販売用一式ZIPがまだありません。")
            self.notify("販売用一式ZIPがありません", level="warning")
            return
        latest = handoffs[0]
        try:
            result = extract_buyer_delivery(latest)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            self.notify("購入者向けZIPの抽出に失敗しました", level="error")
            messagebox.showerror("購入者ZIP抽出エラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            "\n".join(
                [
                    format_buyer_delivery_result(result),
                    "",
                    f"購入者に添付するのは {result.package_path.name} です。",
                    f"問い合わせ時に使う記入票: {result.buyer_support_request_path}",
                    "中には配布ZIP、START_HERE_FOR_BUYER.txt、BUYER_HANDOFF.txt、BUYER_SUPPORT_GUIDE.txt、BUYER_SUPPORT_REQUEST.txt、BUYER_DELIVERY_MANIFEST.json、SHA256SUMS.txt だけが入っています。",
                    "元の auto-note-sales-handoff-*.zip は販売者の証跡として保管してください。",
                ]
            ),
        )
        self.notebook.select(self.diagnostics_tab)
        self._refresh_home_sales_summary()
        _open_path(result.package_path)
        _open_path(result.buyer_support_request_path)
        self.notify(f"購入者向けZIPを作成しました: {result.package_path.name}", level="success")

    def open_latest_buyer_support_request_action(self) -> None:
        deliveries = list_buyer_deliveries(self.project_dir)
        if not deliveries:
            messagebox.showinfo(
                "問い合わせ票",
                "購入者向け抽出フォルダがまだありません。先に 販売一括作成 または 購入者ZIP抽出 を実行してください。",
            )
            self.notify("購入者向け問い合わせ票がありません", level="warning")
            return
        latest = deliveries[0]
        request_path = _buyer_support_request_for(latest)
        if not request_path.exists():
            self.notify("購入者向け問い合わせ票が見つかりません", level="error")
            messagebox.showinfo(
                "問い合わせ票",
                "BUYER_SUPPORT_REQUEST.txt が見つかりません。購入者ZIP抽出をもう一度実行してください。",
            )
            return
        _open_path(request_path)
        self._set_text(
            self.diagnostics_text,
            "\n".join(
                [
                    "Buyer support request / 購入者向け問い合わせ票",
                    "",
                    f"[OK] file: {request_path}",
                    "購入者が困った時は、この記入票と問い合わせ一式ZIP、スクリーンショットを一緒に送ってもらいます。",
                    "パスワード、ログインコード、未公開本文全文、支払い情報は入れないでください。",
                ]
            ),
        )
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"問い合わせ票を開きました: {request_path.name}", level="success")

    def verify_latest_buyer_delivery_action(self) -> None:
        deliveries = list_buyer_deliveries(self.project_dir)
        if not deliveries:
            messagebox.showinfo("購入者ZIP検証", "購入者向け抽出フォルダがまだありません。")
            self.notify("購入者向け抽出フォルダがありません", level="warning")
            return
        latest = deliveries[0]
        errors = verify_buyer_delivery(latest)
        parts = [format_buyer_delivery_verification(latest, errors)]
        packages = list_buyer_delivery_packages(self.project_dir)
        matching = _buyer_delivery_package_for(latest)
        package_path = matching if matching.exists() else (packages[0] if packages else None)
        package_errors: list[str] = []
        if package_path:
            package_errors = verify_buyer_delivery_package(package_path)
            parts.append(format_buyer_delivery_package_verification(package_path, package_errors))
        self._set_text(self.diagnostics_text, "\n\n".join(parts))
        self.notebook.select(self.diagnostics_tab)
        self._refresh_home_sales_summary()
        if errors or package_errors:
            self.notify("購入者向けフォルダの検証で問題が見つかりました", level="error")
        else:
            if package_path:
                self.notify(f"購入者向けZIPを検証しました: {package_path.name}", level="success")
            else:
                self.notify(f"購入者向けフォルダを検証しました: {latest.name}", level="success")

    def run_buyer_send_readiness_to_tab(self) -> None:
        report = run_buyer_send_readiness(self.project_dir)
        self._set_text(self.diagnostics_text, format_buyer_send_readiness_report(report))
        self.notebook.select(self.diagnostics_tab)
        if has_buyer_send_readiness_blockers(report):
            self.notify("送付前チェックでNGが見つかりました", level="error")
        elif report.has_warnings:
            self.notify("送付前チェックで確認事項があります", level="warning")
        else:
            self.notify("送付前チェックはOKです", level="success")

    def create_buyer_send_readiness_report_action(self) -> None:
        try:
            report = run_buyer_send_readiness(self.project_dir)
            path = write_buyer_send_readiness_report(self.project_dir, report=report)
            report = replace(report, report_path=path)
        except OSError as exc:
            self.notify("送付前チェック保存に失敗しました", level="error")
            messagebox.showerror("送付前保存エラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            format_buyer_send_readiness_report(report) + f"\n\nsaved: {path}",
        )
        self.notebook.select(self.diagnostics_tab)
        if has_buyer_send_readiness_blockers(report):
            self.notify(f"送付前チェックを保存しましたがNGがあります: {path.name}", level="error")
        elif report.has_warnings:
            self.notify(f"送付前チェックを保存しました: {path.name}", level="warning")
        else:
            self.notify(f"送付前チェックを保存しました: {path.name}", level="success")

    def create_seller_delivery_receipt_action(self) -> None:
        try:
            report = run_buyer_send_readiness(self.project_dir)
            readiness_path = write_buyer_send_readiness_report(self.project_dir, report=report)
            report = replace(report, report_path=readiness_path)
            if has_buyer_send_readiness_blockers(report):
                self._set_text(
                    self.diagnostics_text,
                    format_buyer_send_readiness_report(report)
                    + "\n\nseller delivery receipt not created because buyer send readiness has blockers.",
                )
                self.notebook.select(self.diagnostics_tab)
                self.notify("送付前チェックNGのため送付記録は作成していません", level="error")
                return
            receipt_path = write_seller_delivery_receipt(self.project_dir, report=report)
        except OSError as exc:
            self.notify("送付記録の作成に失敗しました", level="error")
            messagebox.showerror("送付記録エラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            format_buyer_send_readiness_report(report)
            + "\n\n"
            + format_seller_delivery_receipt(report, receipt_path=receipt_path)
            + f"\n\nsaved: {receipt_path}",
        )
        self.notebook.select(self.diagnostics_tab)
        self._refresh_home_sales_summary()
        if report.has_warnings:
            self.notify(f"送付記録を作成しました: {receipt_path.name}", level="warning")
        else:
            self.notify(f"送付記録を作成しました: {receipt_path.name}", level="success")

    def copy_latest_seller_delivery_receipt_action(self) -> None:
        receipts = list_seller_delivery_receipts(self.project_dir)
        if not receipts:
            messagebox.showinfo("送付記録コピー", "送付記録がまだありません。先に 送付記録 を作成してください。")
            self.notify("送付記録がありません", level="warning")
            return
        latest = receipts[0]
        try:
            receipt_text = latest.read_text(encoding="utf-8")
        except OSError as exc:
            self.notify("送付記録を読めません", level="error")
            messagebox.showerror("送付記録コピーエラー", str(exc))
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(receipt_text.rstrip() + "\n")
            self.update_idletasks()
        except tk.TclError as exc:
            self.notify("クリップボードへコピーできませんでした", level="error")
            messagebox.showerror("送付記録コピーエラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            "\n".join(
                [
                    "Copied seller delivery receipt / コピーした送付記録:",
                    f"source: {latest}",
                    "",
                    receipt_text.rstrip(),
                ]
            ),
        )
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"送付記録をコピーしました: {latest.name}", level="success")

    def copy_latest_seller_order_note_action(self) -> None:
        receipts = list_seller_delivery_receipts(self.project_dir)
        if not receipts:
            messagebox.showinfo("注文控えコピー", "送付記録がまだありません。先に 送付記録 を作成してください。")
            self.notify("送付記録がありません", level="warning")
            return
        latest, order_note = find_latest_seller_order_management_block(self.project_dir)
        if latest is None or not order_note:
            self.notify("注文管理コピー欄が見つかりません", level="error")
            messagebox.showerror(
                "注文控えコピーエラー",
                "送付記録に注文管理コピー欄がありません。送付記録を作り直してください。",
            )
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(order_note.rstrip() + "\n")
            self.update_idletasks()
        except tk.TclError as exc:
            self.notify("クリップボードへコピーできませんでした", level="error")
            messagebox.showerror("注文控えコピーエラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            "\n".join(
                [
                    "Copied seller order note / コピーした注文管理控え:",
                    f"source: {latest}",
                    "",
                    order_note.rstrip(),
                ]
            ),
        )
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"注文管理控えをコピーしました: {latest.name}", level="success")

    def copy_latest_buyer_delivery_message_action(self) -> None:
        send_report = run_buyer_send_readiness(self.project_dir)
        if has_buyer_send_readiness_blockers(send_report):
            self._set_text(self.diagnostics_text, format_buyer_send_readiness_report(send_report))
            self.notebook.select(self.diagnostics_tab)
            self.notify("送付前チェックNGのため送付文をコピーしませんでした", level="error")
            return
        messages = list_buyer_delivery_messages(self.project_dir)
        if not messages:
            messagebox.showinfo("送付文コピー", "購入者向け送付文がまだありません。先に販売一括作成を実行してください。")
            self.notify("購入者向け送付文がありません", level="warning")
            return
        message_path = send_report.buyer_delivery_message_path or messages[0]
        try:
            message_text = message_path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError as exc:
            self.notify("購入者向け送付文を読めません", level="error")
            messagebox.showerror("送付文コピーエラー", str(exc))
            return
        packages = list_buyer_delivery_packages(self.project_dir)
        package_path = send_report.buyer_delivery_package_path or find_buyer_delivery_package_for_message(
            message_text,
            packages,
        )
        if package_path is None:
            self._set_text(
                self.diagnostics_text,
                "\n".join(
                    [
                        "Buyer delivery message copy / 購入者向け送付文コピー",
                        "",
                        f"[NG] message: {message_path.name}",
                        "購入者向けZIPが見つからないため、送付文はコピーしていません。",
                        "先に 販売一括作成 または 購入者ZIP抽出 を実行してください。",
                    ]
                ),
            )
            self.notebook.select(self.diagnostics_tab)
            self.notify("購入者向けZIPがないため送付文をコピーしませんでした", level="error")
            return
        package_errors = verify_buyer_delivery_package(package_path)
        parts = [format_buyer_send_readiness_report(send_report), "", f"[OK] message: {message_path.name}"]
        parts.append(format_buyer_delivery_package_verification(package_path, package_errors))
        if package_errors:
            parts.extend(
                [
                    "",
                    "購入者向けZIPの検証で問題が見つかったため、送付文はコピーしていません。",
                    "販売一括作成で作り直すか、診断内容を確認してください。",
                ]
            )
            self._set_text(self.diagnostics_text, "\n".join(parts))
            self.notebook.select(self.diagnostics_tab)
            self.notify("購入者向けZIPに問題があるため送付文をコピーしませんでした", level="error")
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(message_text + "\n")
            self.update_idletasks()
        except tk.TclError as exc:
            self.notify("クリップボードへコピーできませんでした", level="error")
            messagebox.showerror("送付文コピーエラー", str(exc))
            return
        parts.extend(["", "Copied message / コピーした送付文:", "", message_text])
        self._set_text(self.diagnostics_text, "\n".join(parts))
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"送付文をコピーしました: {message_path.name}", level="success")

    def open_latest_buyer_delivery_location_action(self) -> None:
        send_report = run_buyer_send_readiness(self.project_dir)
        if has_buyer_send_readiness_blockers(send_report):
            self._set_text(self.diagnostics_text, format_buyer_send_readiness_report(send_report))
            self.notebook.select(self.diagnostics_tab)
            self.notify("送付前チェックNGのため購入者ZIP場所を開きませんでした", level="error")
            return
        package_path = send_report.buyer_delivery_package_path
        if package_path is None or not package_path.exists():
            messagebox.showinfo("購入者ZIP場所", "購入者向けZIPがまだありません。先に販売一括作成を実行してください。")
            self.notify("購入者向けZIPがありません", level="warning")
            return
        package_errors = verify_buyer_delivery_package(package_path)
        if package_errors:
            self._set_text(
                self.diagnostics_text,
                "\n".join(
                    [
                        format_buyer_send_readiness_report(send_report),
                        "",
                        format_buyer_delivery_package_verification(package_path, package_errors),
                        "",
                        "購入者向けZIPの検証で問題が見つかったため、場所は開いていません。",
                    ]
                ),
            )
            self.notebook.select(self.diagnostics_tab)
            self.notify("購入者向けZIPに問題があるため場所を開きませんでした", level="error")
            return
        folder_path = package_path.parent.resolve()
        _open_path(folder_path)
        self._set_text(
            self.diagnostics_text,
            "\n".join(
                [
                    format_buyer_send_readiness_report(send_report),
                    "",
                    format_buyer_delivery_package_verification(package_path, []),
                    "",
                    f"Opened folder / 開いたフォルダ: {folder_path}",
                    f"Buyer delivery ZIP / 購入者向けZIP: {package_path.name}",
                ]
            ),
        )
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"購入者向けZIPの場所を開きました: {package_path.name}", level="success")

    def copy_latest_buyer_delivery_zip_path_action(self) -> None:
        send_report = run_buyer_send_readiness(self.project_dir)
        if has_buyer_send_readiness_blockers(send_report):
            self._set_text(self.diagnostics_text, format_buyer_send_readiness_report(send_report))
            self.notebook.select(self.diagnostics_tab)
            self.notify("送付前チェックNGのためZIPパスをコピーしませんでした", level="error")
            return
        package_path = send_report.buyer_delivery_package_path
        if package_path is None or not package_path.exists():
            messagebox.showinfo("ZIPパスコピー", "購入者向けZIPがまだありません。先に販売一括作成を実行してください。")
            self.notify("購入者向けZIPがありません", level="warning")
            return
        package_errors = verify_buyer_delivery_package(package_path)
        if package_errors:
            self._set_text(
                self.diagnostics_text,
                "\n".join(
                    [
                        format_buyer_send_readiness_report(send_report),
                        "",
                        format_buyer_delivery_package_verification(package_path, package_errors),
                        "",
                        "購入者向けZIPの検証で問題が見つかったため、ZIPパスはコピーしていません。",
                    ]
                ),
            )
            self.notebook.select(self.diagnostics_tab)
            self.notify("購入者向けZIPに問題があるためZIPパスをコピーしませんでした", level="error")
            return
        copied_path = package_path.resolve()
        try:
            self.clipboard_clear()
            self.clipboard_append(str(copied_path))
            self.update_idletasks()
        except tk.TclError as exc:
            self.notify("クリップボードへコピーできませんでした", level="error")
            messagebox.showerror("ZIPパスコピーエラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            "\n".join(
                [
                    format_buyer_send_readiness_report(send_report),
                    "",
                    format_buyer_delivery_package_verification(package_path, []),
                    "",
                    "Copied ZIP path / コピーしたZIPパス:",
                    str(copied_path),
                ]
            ),
        )
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"購入者向けZIPパスをコピーしました: {package_path.name}", level="success")

    def copy_latest_buyer_delivery_sheet_action(self) -> None:
        send_report = run_buyer_send_readiness(self.project_dir)
        if has_buyer_send_readiness_blockers(send_report):
            self._set_text(self.diagnostics_text, format_buyer_send_readiness_report(send_report))
            self.notebook.select(self.diagnostics_tab)
            self.notify("送付前チェックNGのため送付情報をコピーしませんでした", level="error")
            return
        package_path = send_report.buyer_delivery_package_path
        if package_path is None or not package_path.exists():
            messagebox.showinfo("送付情報コピー", "購入者向けZIPがまだありません。先に販売一括作成を実行してください。")
            self.notify("購入者向けZIPがありません", level="warning")
            return
        package_errors = verify_buyer_delivery_package(package_path)
        if package_errors:
            self._set_text(
                self.diagnostics_text,
                "\n".join(
                    [
                        format_buyer_send_readiness_report(send_report),
                        "",
                        format_buyer_delivery_package_verification(package_path, package_errors),
                        "",
                        "購入者向けZIPの検証で問題が見つかったため、送付情報はコピーしていません。",
                    ]
                ),
            )
            self.notebook.select(self.diagnostics_tab)
            self.notify("購入者向けZIPに問題があるため送付情報をコピーしませんでした", level="error")
            return
        try:
            package_data = package_path.read_bytes()
        except OSError as exc:
            self.notify("購入者向けZIPを読めません", level="error")
            messagebox.showerror("送付情報コピーエラー", str(exc))
            return
        copied_path = package_path.resolve()
        package_sha = hashlib.sha256(package_data).hexdigest()
        message_path = send_report.buyer_delivery_message_path
        release_name = send_report.latest_release_path.name if send_report.latest_release_path else "none"
        message_name = message_path.name if message_path else "none"
        sheet_lines = [
            "Buyer delivery copy sheet / 購入者送付の照合値",
            f"- latest release package: {release_name}",
            f"- buyer delivery zip: {package_path.name}",
            f"- buyer delivery zip path: {copied_path}",
            f"- zip size: {len(package_data)} bytes",
            f"- zip SHA-256: {package_sha}",
            f"- delivery message: {message_name}",
            "- attach exactly this buyer delivery zip only / 購入者へ添付するのはこのZIPだけ",
        ]
        sheet_text = "\n".join(sheet_lines)
        try:
            self.clipboard_clear()
            self.clipboard_append(sheet_text + "\n")
            self.update_idletasks()
        except tk.TclError as exc:
            self.notify("クリップボードへコピーできませんでした", level="error")
            messagebox.showerror("送付情報コピーエラー", str(exc))
            return
        self._set_text(
            self.diagnostics_text,
            "\n".join(
                [
                    format_buyer_send_readiness_report(send_report),
                    "",
                    format_buyer_delivery_package_verification(package_path, []),
                    "",
                    sheet_text,
                ]
            ),
        )
        self.notebook.select(self.diagnostics_tab)
        self.notify(f"購入者送付情報をコピーしました: {package_path.name}", level="success")

    def show_app_info(self) -> None:
        info = format_app_info(collect_app_info(self.project_dir))
        self._set_text(self.help_text, info)
        self.notebook.select(self.help_tab)
        self.notify("アプリ情報を表示しました", level="success")

    def show_dependency_notices(self) -> None:
        text = format_dependency_notices(collect_dependency_notices())
        self._set_text(self.help_text, text)
        self.notebook.select(self.help_tab)
        self.notify("ライセンス情報を表示しました", level="success")

    def write_dependency_notices_action(self) -> None:
        try:
            path = write_dependency_notices(self.project_dir / "docs" / "THIRD_PARTY_NOTICES.md")
        except OSError as exc:
            self.notify("第三者表記の更新に失敗しました", level="error")
            messagebox.showerror("第三者表記更新エラー", str(exc))
            return
        self._set_text(self.help_text, _read_text(path))
        self.notebook.select(self.help_tab)
        self.notify(f"第三者表記を更新しました: {path.name}", level="success")

    def create_support_request_action(self) -> None:
        try:
            path = create_support_request(self.project_dir)
        except OSError as exc:
            self.notify("問い合わせテンプレート作成に失敗しました", level="error")
            messagebox.showerror("問い合わせ作成エラー", str(exc))
            return
        self.refresh_help()
        privacy = run_privacy_audit(self.project_dir)
        self._set_text(
            self.help_text,
            f"問い合わせテンプレートを作成しました: {path}\n\n{format_privacy_audit_report(privacy)}",
        )
        self.notebook.select(self.help_tab)
        if has_privacy_audit_blockers(privacy):
            self.notify("問い合わせ送付前チェックで問題が見つかりました", level="error")
            return
        self.notify(f"問い合わせテンプレートを作成しました: {path.name}", level="success")
        _open_path(path)

    def create_support_bundle_action(self) -> None:
        try:
            path = create_support_bundle(
                self.project_dir,
                extra_entries={"DISPLAY_DIAGNOSTICS.txt": self._format_display_diagnostics()},
            )
        except Exception as exc:
            self.notify("問い合わせ一式の作成に失敗しました", level="error")
            messagebox.showerror("問い合わせ一式エラー", str(exc))
            return
        self.refresh_help()
        verification_errors = verify_support_bundle(path)
        privacy = run_privacy_audit(self.project_dir)
        try:
            send_checklist = read_support_send_checklist(path)
        except (OSError, ValueError) as exc:
            send_checklist = f"送付前リストを表示できませんでした: {exc}"
        self._set_text(
            self.help_text,
            "\n\n".join(
                [
                    f"問い合わせ一式を作成しました: {path}",
                    send_checklist,
                    format_support_bundle_verification(path, verification_errors),
                    format_privacy_audit_report(privacy),
                ]
            ),
        )
        self.notebook.select(self.help_tab)
        if verification_errors:
            self.notify("問い合わせ一式ZIPの検証で問題が見つかりました", level="error")
            return
        if has_privacy_audit_blockers(privacy):
            self.notify("問い合わせ送付前チェックで問題が見つかりました", level="error")
            return
        self.notify(f"問い合わせ一式を作成しました: {path.name}", level="success")
        _open_path(path)

    def verify_latest_support_bundle_action(self) -> None:
        bundles = list_support_bundles(self.project_dir)
        if not bundles:
            messagebox.showinfo("一式ZIP検証", "問い合わせ一式ZIPがまだありません。")
            self.notify("問い合わせ一式ZIPがありません", level="warning")
            self._refresh_support_summary()
            return
        latest = bundles[0]
        errors = verify_support_bundle(latest)
        self._refresh_support_summary()
        self._set_text(self.help_text, format_support_bundle_verification(latest, errors))
        self.notebook.select(self.help_tab)
        if errors:
            self.notify("問い合わせ一式ZIPの検証で問題が見つかりました", level="error")
        else:
            self.notify(f"問い合わせ一式ZIPを検証しました: {latest.name}", level="success")

    def show_support_gui_log_summary_action(self) -> None:
        bundles = list_support_bundles(self.project_dir)
        if not bundles:
            messagebox.showinfo("ZIPログ要約", "問い合わせ一式ZIPがまだありません。先に 問い合わせ一式 を作成してください。")
            self.notify("問い合わせ一式ZIPがありません", level="warning")
            self._refresh_support_summary()
            return
        latest = bundles[0]
        errors = verify_support_bundle(latest)
        self._refresh_support_summary()
        try:
            summary = read_support_gui_log_summary(latest)
        except (OSError, ValueError) as exc:
            self._set_text(
                self.help_text,
                "\n\n".join(
                    [
                        f"ZIPログ要約: {latest}",
                        format_support_bundle_verification(latest, errors),
                        f"[INFO] GUIログ要約を表示できません: {exc}",
                        "最新形式で作り直すには、ヘルプの 問い合わせ一式 を実行してください。",
                    ]
                ),
            )
            self.notebook.select(self.help_tab)
            self.notify("GUIログ要約を表示できません", level="warning")
            return
        self._set_text(
            self.help_text,
            "\n\n".join(
                [
                    f"ZIPログ要約: {latest}",
                    summary,
                    format_support_bundle_verification(latest, errors),
                ]
            ),
        )
        self.notebook.select(self.help_tab)
        if errors:
            self.notify("問い合わせ一式ZIPの検証で問題が見つかりました", level="error")
        else:
            self.notify(f"GUIログ要約を表示しました: {latest.name}", level="success")

    def show_support_display_diagnostics_action(self) -> None:
        bundles = list_support_bundles(self.project_dir)
        if not bundles:
            messagebox.showinfo("ZIP表示診断", "問い合わせ一式ZIPがまだありません。先に 問い合わせ一式 を作成してください。")
            self.notify("問い合わせ一式ZIPがありません", level="warning")
            self._refresh_support_summary()
            return
        latest = bundles[0]
        errors = verify_support_bundle(latest)
        self._refresh_support_summary()
        try:
            display_diagnostics = read_support_display_diagnostics(latest)
        except (OSError, ValueError) as exc:
            self._set_text(
                self.help_text,
                "\n\n".join(
                    [
                        f"ZIP表示診断: {latest}",
                        format_support_bundle_verification(latest, errors),
                        f"[INFO] 表示診断を表示できません: {exc}",
                        "最新形式で作り直すには、ヘルプの 問い合わせ一式 を実行してください。",
                    ]
                ),
            )
            self.notebook.select(self.help_tab)
            self.notify("ZIP表示診断を表示できません", level="warning")
            return
        self._set_text(
            self.help_text,
            "\n\n".join(
                [
                    f"ZIP表示診断: {latest}",
                    display_diagnostics,
                    format_support_bundle_verification(latest, errors),
                ]
            ),
        )
        self.notebook.select(self.help_tab)
        if errors:
            self.notify("問い合わせ一式ZIPの検証で問題が見つかりました", level="error")
        else:
            self.notify(f"ZIP表示診断を表示しました: {latest.name}", level="success")

    def open_latest_support_bundle_location_action(self) -> None:
        bundles = list_support_bundles(self.project_dir)
        if not bundles:
            messagebox.showinfo("最新ZIP場所", "問い合わせ一式ZIPがまだありません。")
            self.notify("問い合わせ一式ZIPがありません", level="warning")
            self._refresh_support_summary()
            return
        latest = bundles[0]
        self._refresh_support_summary()
        _open_path(latest.parent)
        self.notify(f"最新問い合わせ一式ZIPの場所を開きました: {latest.name}", level="success")

    def copy_latest_support_bundle_path_action(self) -> None:
        bundles = list_support_bundles(self.project_dir)
        if not bundles:
            messagebox.showinfo("最新ZIPパス", "問い合わせ一式ZIPがまだありません。")
            self.notify("問い合わせ一式ZIPがありません", level="warning")
            self._refresh_support_summary()
            return
        latest = bundles[0]
        self._refresh_support_summary()
        try:
            self.clipboard_clear()
            self.clipboard_append(str(latest.resolve()))
            self.update_idletasks()
        except tk.TclError as exc:
            self.notify("最新問い合わせ一式ZIPのパスをコピーできませんでした", level="error")
            messagebox.showerror("最新ZIPパス", str(exc))
            return
        self.notify(f"最新問い合わせ一式ZIPのパスをコピーしました: {latest.name}", level="success")

    def copy_support_send_message_action(self) -> None:
        self._refresh_support_summary()
        contact = self.settings.support_contact.strip()
        if not contact:
            self.notify("サポート連絡先が未設定です", level="warning")
            self.focus_support_contact_field()
            return
        bundles = list_support_bundles(self.project_dir)
        if not bundles:
            messagebox.showinfo("送付文コピー", "問い合わせ一式ZIPがまだありません。先に 問い合わせ一式 を作成してください。")
            self.notify("問い合わせ一式ZIPがありません", level="warning")
            self._refresh_support_summary()
            return
        latest = bundles[0]
        errors = verify_support_bundle(latest)
        self._refresh_support_summary()
        if errors:
            self._set_text(self.help_text, format_support_bundle_verification(latest, errors))
            self.notebook.select(self.help_tab)
            self.notify("問い合わせ一式ZIPの検証で問題が見つかりました", level="error")
            return
        message = "\n".join(
            [
                "auto-note サポート送付メモ",
                f"連絡先: {contact}",
                f"問い合わせ一式ZIP: {latest.resolve()}",
                "",
                "送付前確認:",
                "- ヘルプ > 送付前リスト を確認済み",
                "- ヘルプ > 一式ZIP検証 がOK",
                "- 添付するのは上記ZIPだけ",
            ]
        )
        try:
            self.clipboard_clear()
            self.clipboard_append(message)
            self.update_idletasks()
        except tk.TclError as exc:
            self.notify("サポート送付メモをコピーできませんでした", level="error")
            messagebox.showerror("送付文コピー", str(exc))
            return
        self._set_text(self.help_text, message)
        self.notebook.select(self.help_tab)
        self.notify(f"サポート送付メモをコピーしました: {latest.name}", level="success")

    def show_support_send_checklist_action(self) -> None:
        bundles = list_support_bundles(self.project_dir)
        if not bundles:
            messagebox.showinfo("送付前リスト", "問い合わせ一式ZIPがまだありません。先に 問い合わせ一式 を作成してください。")
            self.notify("問い合わせ一式ZIPがありません", level="warning")
            self._refresh_support_summary()
            return
        latest = bundles[0]
        errors = verify_support_bundle(latest)
        self._refresh_support_summary()
        try:
            send_checklist = read_support_send_checklist(latest)
        except (OSError, ValueError) as exc:
            self.notify("送付前リストを表示できません", level="error")
            messagebox.showerror("送付前リスト", str(exc))
            return
        self._set_text(
            self.help_text,
            "\n\n".join(
                [
                    f"送付前リスト: {latest}",
                    send_checklist,
                    format_support_bundle_verification(latest, errors),
                ]
            ),
        )
        self.notebook.select(self.help_tab)
        if errors:
            self.notify("問い合わせ一式ZIPの検証で問題が見つかりました", level="error")
        else:
            self._set_support_next_action("送付文コピー")
            self.notify(f"送付前リストを表示しました: {latest.name}", level="success")

    def preview_cleanup_action(self) -> None:
        result = cleanup_generated_files(self.project_dir, dry_run=True)
        self._set_text(self.diagnostics_text, format_cleanup_report(result, dry_run=True))
        self.notebook.select(self.diagnostics_tab)
        self.notify("古い生成物候補を表示しました", level="success")

    def preview_privacy_failed_cleanup_action(self) -> None:
        result = cleanup_generated_files(
            self.project_dir,
            dry_run=True,
            include_releases=True,
            privacy_failed=True,
        )
        self._set_text(self.diagnostics_text, format_cleanup_report(result, dry_run=True))
        self.notebook.select(self.diagnostics_tab)
        self.notify(
            "プライバシー監査NGの生成物候補を表示しました",
            level="warning" if result.items else "success",
        )

    def apply_cleanup_action(self) -> None:
        preview = cleanup_generated_files(self.project_dir, dry_run=True)
        if not preview.items:
            self._set_text(self.diagnostics_text, format_cleanup_report(preview, dry_run=True))
            self.notebook.select(self.diagnostics_tab)
            self.notify("整理対象はありません", level="success")
            return
        if not messagebox.askyesno("生成物整理", format_cleanup_confirmation(preview)):
            return
        result = cleanup_generated_files(self.project_dir, dry_run=False)
        self._set_text(self.diagnostics_text, format_cleanup_report(result, dry_run=False))
        self.notebook.select(self.diagnostics_tab)
        self.notify("古い生成物を整理しました", level="success")

    def apply_privacy_failed_cleanup_action(self) -> None:
        preview = cleanup_generated_files(
            self.project_dir,
            dry_run=True,
            include_releases=True,
            privacy_failed=True,
        )
        if not preview.items:
            self._set_text(self.diagnostics_text, format_cleanup_report(preview, dry_run=True))
            self.notebook.select(self.diagnostics_tab)
            self.notify("プライバシー監査NGの生成物はありません", level="success")
            return
        if not messagebox.askyesno(
            "危険生成物整理",
            format_cleanup_confirmation(preview, privacy_failed=True),
        ):
            return
        result = cleanup_generated_files(
            self.project_dir,
            dry_run=False,
            include_releases=True,
            privacy_failed=True,
        )
        self._set_text(self.diagnostics_text, format_cleanup_report(result, dry_run=False))
        self.notebook.select(self.diagnostics_tab)
        self.notify("プライバシー監査NGの生成物を整理しました", level="success")

    def open_gui_log(self) -> None:
        path = gui_error_log_path(self.project_dir)
        if not path.exists():
            messagebox.showinfo("ログ", "まだGUIログはありません。")
            return
        _open_path(path)

    def open_gui_log_folder_action(self) -> None:
        path = gui_error_log_path(self.project_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        _open_path(path.parent)
        self.notify("GUIログの保存場所を開きました", level="success")

    def show_gui_log_action(self) -> None:
        text, has_log = self._format_gui_log_preview()
        self._set_text(self.diagnostics_text, text)
        self.notebook.select(self.diagnostics_tab)
        if has_log:
            self.notify("GUIログを表示しました", level="success")
        else:
            self.notify("GUIログはまだありません", level="info")

    def copy_gui_log_action(self) -> None:
        text, has_log = self._format_gui_log_preview()
        self._set_text(self.diagnostics_text, text)
        self.notebook.select(self.diagnostics_tab)
        if not has_log:
            self.notify("コピーできるGUIログはまだありません", level="warning")
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update_idletasks()
        except tk.TclError as exc:
            self.notify("GUIログをコピーできませんでした", level="error")
            messagebox.showerror("GUIログコピー", str(exc))
            return
        self.notify("GUIログをコピーしました", level="success")

    def clear_gui_log_action(self) -> None:
        path = gui_error_log_path(self.project_dir)
        has_log = False
        if path.exists():
            try:
                has_log = path.stat().st_size > 0
            except OSError as exc:
                self.notify("GUIログを確認できませんでした", level="error")
                messagebox.showerror("GUIログクリア", str(exc))
                return
        if has_log:
            confirmed = messagebox.askyesno(
                "GUIログクリア",
                "現在のGUIログを退避して、復旧ステータスをOKに戻します。\n"
                "退避ファイルは同じフォルダに残ります。実行しますか？",
            )
            if not confirmed:
                self.notify("GUIログクリアをキャンセルしました", level="info")
                return
        try:
            archive = clear_gui_error_log(self.project_dir)
        except OSError as exc:
            self.notify("GUIログをクリアできませんでした", level="error")
            messagebox.showerror("GUIログクリア", str(exc))
            return
        lines = [
            "GUI log clear / GUIログクリア",
            "",
            f"current log: {path}",
        ]
        if archive:
            lines.extend(
                [
                    f"archived to: {archive}",
                    "",
                    "[OK] GUIログを退避して、現在ログをクリアしました。",
                ]
            )
        else:
            lines.extend(["", "[OK] クリアするGUIログはありません。復旧ステータスを更新しました。"])
        self._set_text(self.diagnostics_text, "\n".join(lines))
        self.notebook.select(self.diagnostics_tab)
        self._refresh_home_gui_log_status()
        self.notify("GUIログをクリアしました", level="success")

    def _format_gui_log_preview(self) -> tuple[str, bool]:
        path = gui_error_log_path(self.project_dir)
        lines = [
            "GUI log / GUIログ",
            "",
            f"path: {path}",
            "note: サポートへ送る前に内容を確認してください。",
        ]
        if not path.exists():
            lines.extend(["", "[INFO] GUIログはまだありません。"])
            return "\n".join(lines), False
        try:
            size = path.stat().st_size
            content = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError as exc:
            lines.extend(["", f"[NG] GUIログを読めません: {exc}"])
            return "\n".join(lines), False
        max_chars = 20000
        if len(content) > max_chars:
            content = content[-max_chars:]
            lines.extend(["", f"[INFO] ログが長いため末尾 {max_chars} 文字だけ表示しています。"])
        lines.extend(["", f"size: {size} bytes", "", "content:", content or "(empty)"])
        return "\n".join(lines), True

    def show_latest_recovery_kit_report_action(self) -> None:
        text, latest = self._format_latest_recovery_kit_report_preview()
        self._set_text(self.diagnostics_text, text)
        self.notebook.select(self.diagnostics_tab)
        if latest:
            self.notify(f"最新復旧レポートを表示しました: {latest.name}", level="success")
        else:
            self.notify("復旧レポートはまだありません", level="warning")

    def copy_latest_recovery_kit_report_action(self) -> None:
        text, latest = self._format_latest_recovery_kit_report_preview()
        self._set_text(self.diagnostics_text, text)
        self.notebook.select(self.diagnostics_tab)
        if not latest:
            self.notify("コピーできる復旧レポートはまだありません", level="warning")
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update_idletasks()
        except tk.TclError as exc:
            self.notify("復旧レポートをコピーできませんでした", level="error")
            messagebox.showerror("復旧レポートコピー", str(exc))
            return
        self.notify(f"復旧レポートをコピーしました: {latest.name}", level="success")

    def open_recovery_kit_reports_folder_action(self) -> None:
        reports_dir = self.project_dir / ".auto-note" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        _open_path(reports_dir)
        self.notify("復旧レポートの保存場所を開きました", level="success")

    def _format_latest_recovery_kit_report_preview(self) -> tuple[str, Path | None]:
        reports_dir = self.project_dir / ".auto-note" / "reports"
        reports = list_recovery_kit_reports(self.project_dir)
        lines = [
            "Recovery report / 復旧レポート",
            "",
            "folder: .auto-note\\reports",
            "note: サポートへ送る前に内容を確認してください。",
        ]
        if not reports:
            lines.extend(
                [
                    "",
                    "[INFO] 復旧レポートはまだありません。",
                    "作成: 診断 > 復旧セット、または auto-note recovery-kit --project-dir . --report",
                ]
            )
            return "\n".join(lines), None

        latest = reports[0]
        try:
            size = latest.stat().st_size
            modified = datetime.fromtimestamp(latest.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            content = latest.read_text(encoding="utf-8", errors="replace").strip()
        except OSError as exc:
            lines.extend(["", f"[NG] 復旧レポートを読めません: {exc}"])
            return "\n".join(lines), None

        max_chars = 30000
        if len(content) > max_chars:
            content = content[-max_chars:]
            lines.extend(["", f"[INFO] レポートが長いため末尾 {max_chars} 文字だけ表示しています。"])
        lines.extend(
            [
                "",
                f"latest: {latest.name}",
                f"modified: {modified}",
                f"size: {size} bytes",
                f"saved reports: {len(reports)}",
                "",
                "content:",
                content or "(empty)",
            ]
        )
        return "\n".join(lines), latest

    def open_maintenance_folder(self) -> None:
        path = self.project_dir / ".auto-note"
        path.mkdir(parents=True, exist_ok=True)
        _open_path(path)

    def _set_check_text(self, text: str) -> None:
        if hasattr(self, "check_text"):
            self._set_text(self.check_text, text)

    def _set_text(self, widget: ScrolledText, text: str) -> None:
        _style_text_widget(widget)
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.configure(state=tk.DISABLED)

    def handle_callback_exception(self, exc_type, exc_value, exc_traceback) -> None:
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        try:
            path = append_gui_error(self.project_dir, "GUI runtime error", detail)
        except OSError:
            path = gui_error_log_path(self.project_dir)
        if hasattr(self, "notification"):
            self.notify("GUI操作中にエラーが発生しました。GUIログ表示または復旧セットを確認してください。", level="error")
        self._refresh_home_gui_log_status()
        try:
            messagebox.showerror("GUIエラー", _gui_runtime_error_message(path))
        except tk.TclError:
            pass

    def notify(self, message: str, *, level: str = "info", transient: bool = False) -> None:
        colors = {
            "info": (UI_COLORS["info_soft"], "#174ea6"),
            "success": (UI_COLORS["ok_soft"], UI_COLORS["ok"]),
            "warning": (UI_COLORS["warn_soft"], UI_COLORS["warn"]),
            "error": (UI_COLORS["danger_soft"], "#991b1b"),
        }
        bg, fg = colors.get(level, colors["info"])
        self.notification.configure(text=message, bg=bg, fg=fg)
        if self._notification_job:
            self.after_cancel(self._notification_job)
            self._notification_job = None
        if transient:
            self._notification_job = self.after(
                2500,
                lambda: self.notification.configure(
                    text="準備できました",
                    bg=UI_COLORS["surface_selected"],
                    fg=UI_COLORS["ink"],
                ),
            )


def _show_text_window(parent: tk.Misc, title: str, text: str) -> None:
    win = tk.Toplevel(parent)
    win.title(title)
    win.geometry("780x540")
    frame = ttk.Frame(win, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)
    box = ScrolledText(frame, wrap=tk.WORD)
    _style_text_widget(box)
    box.pack(fill=tk.BOTH, expand=True)
    box.insert(tk.END, text)
    box.configure(state=tk.DISABLED)
    ttk.Button(frame, text="閉じる", command=win.destroy).pack(anchor=tk.E, pady=(8, 0))


def _issue_summary(report) -> str:
    errors = sum(1 for issue in report.issues if issue.level == "error")
    warnings = sum(1 for issue in report.issues if issue.level == "warn")
    if errors:
        return f"NG {errors}"
    if warnings:
        return f"警告 {warnings}"
    return "OK"


def _review_summary_text(reviews: list[ArticleReview]) -> str:
    if not reviews:
        return "記事がありません。"
    average = round(sum(review.score for review in reviews) / len(reviews))
    ready_count = sum(1 for review in reviews if review.ready)
    fix_count = sum(1 for review in reviews if review.needs_fix)
    improve_count = sum(
        1
        for review in reviews
        if not review.ready and not review.needs_fix
    )
    return f"平均 {average}/100 / READY {ready_count} / 修正 {fix_count} / 改善 {improve_count} / 全 {len(reviews)}"


def _action_step_label(severity: str) -> str:
    return {
        "blocker": "NG",
        "warning": "要確認",
        "maintenance": "保守",
        "ready": "準備OK",
        "info": "案内",
    }.get(severity, severity.upper())


def _home_progress_state_from_status(status: str) -> str:
    return {
        "pass": "ok",
        "info": "info",
        "warn": "warn",
        "fail": "fail",
    }.get(status, "info")


def _home_progress_review_text(status: str, total_articles: int) -> str:
    if total_articles == 0:
        return "記事待ち"
    return {
        "pass": "準備OK",
        "info": "確認中",
        "warn": "要仕上げ",
        "fail": "NGあり",
    }.get(status, "確認中")


def _home_progress_summary(stages: dict[str, str], next_title: str) -> str:
    ready = sum(1 for state in stages.values() if state == "ok")
    blocked = sum(1 for state in stages.values() if state == "fail")
    check = sum(1 for state in stages.values() if state in {"warn", "info"})
    if blocked:
        status = f"NG {blocked} / CHECK {check} / READY {ready}"
    else:
        status = f"READY {ready}/{len(stages)} / CHECK {check}"
    return f"{status} - 次: {next_title}"


def _home_snapshot_values(
    *,
    readiness_score: int,
    action_status: str,
    next_title: str,
    first_run_summary: str,
    gui_log_text: str,
    sales_status: str,
    buyer_send_summary: str,
) -> dict[str, str]:
    gui_log = gui_log_text.replace("GUIログ: ", "").strip()
    sales = sales_status.replace("販売準備: ", "").strip()
    buyer = buyer_send_summary.replace("購入者送付: ", "").strip()
    return {
        "readiness": _home_snapshot_brief(f"{readiness_score}/100 / {action_status}", 54),
        "next": _home_snapshot_brief(next_title or "詳細確認", 54),
        "startup": _home_snapshot_brief(f"{first_run_summary} / {gui_log}", 58),
        "sales": _home_snapshot_brief(f"{sales} / {buyer}", 58),
    }


def _home_snapshot_brief(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."


def _home_snapshot_readiness_state(readiness_score: int) -> str:
    if readiness_score >= 90:
        return "ok"
    if readiness_score >= 75:
        return "info"
    if readiness_score >= 60:
        return "warn"
    return "fail"


def _home_snapshot_next_state(severity: str) -> str:
    return {
        "blocker": "fail",
        "warning": "warn",
        "maintenance": "info",
        "info": "info",
        "ready": "ok",
    }.get(severity, "info")


def _home_snapshot_worst_state(*states: str) -> str:
    rank = {"fail": 3, "warn": 2, "info": 1, "ok": 0}
    return max(states or ("info",), key=lambda state: rank.get(state, 1))


def _article_focus_summary(plan: ImprovementPlan) -> str:
    readiness = {
        "pass": "投稿OK",
        "warn": "投稿前確認",
        "fail": "投稿前NG",
    }.get(plan.publish_ready.status, "投稿前確認")
    return (
        f"レビュー {plan.review.score}/100 / {readiness} / "
        f"FIX {plan.fix_count} / WARN {plan.warn_count} / "
        f"IMPROVE {plan.improve_count} / 約{plan.total_minutes}分"
    )


def _article_focus_next_text(plan: ImprovementPlan) -> str:
    if plan.status == "ready":
        return "次: 投稿ヘルパーを開き、noteへ転記して公開後URLを保存します。"
    if not plan.steps:
        return "次: 改善プランを開いて投稿前の確認を進めます。"
    step = plan.steps[0]
    label = {
        "fix": "必須修正",
        "warn": "確認",
        "improve": "改善",
        "info": "次へ",
    }.get(step.severity, step.severity.upper())
    problem = _article_focus_brief(step.problem, 46)
    action = _article_focus_brief(step.action, 54) if step.action else "改善プランで確認"
    return f"次: {label} / {step.stage}-{step.category}: {problem} / {action}"


def _article_focus_status_style(status: str) -> tuple[str, str, str]:
    styles = {
        "ready": ("READY", UI_COLORS["ok"], "#ffffff"),
        "check": ("CHECK", UI_COLORS["warn"], "#ffffff"),
        "blocked": ("BLOCKED", UI_COLORS["danger"], "#ffffff"),
    }
    return styles.get(status, ("CHECK", "#344054", "#ffffff"))


def _article_focus_accent_color(status: str) -> str:
    return {
        "ready": UI_COLORS["ok"],
        "check": UI_COLORS["warn"],
        "blocked": UI_COLORS["danger"],
    }.get(status, UI_COLORS["line"])


def _article_focus_brief(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."


def _commercial_setup_field_rows(settings: AppSettings) -> list[tuple[str, str, str, str, str]]:
    fields = [
        (
            "seller_name",
            "販売者/屋号",
            settings.seller_name.strip(),
            "販売素材に表示する販売者名です。",
            "販売者/屋号を入力します。",
        ),
        (
            "sales_channel_url",
            "販売ページURL",
            settings.sales_channel_url.strip(),
            "購入者が確認できる販売ページです。",
            "https:// で始まる販売ページURLを入力します。",
        ),
        (
            "refund_policy_url",
            "返金方針URL",
            settings.refund_policy_url.strip(),
            "返金/キャンセル方針の公開ページです。",
            "https:// で始まる返金方針URLを入力します。",
        ),
        (
            "support_contact",
            "サポート連絡先",
            settings.support_contact.strip(),
            "購入者向け問い合わせ先です。",
            "問い合わせフォームなどの公開サポートURLを入力します。",
        ),
    ]
    rows: list[tuple[str, str, str, str, str]] = []
    for field, label, value, ok_detail, action in fields:
        status = "ok"
        detail = ok_detail
        if not value:
            status = "missing"
            detail = "未入力"
        elif field in {"sales_channel_url", "refund_policy_url"} and not _commercial_setup_public_url(value):
            status = "warn"
            detail = "公開URL形式ではありません。"
        elif field == "support_contact":
            if _commercial_setup_raw_email(value):
                status = "warn"
                detail = "メール直書きより公開サポートURL推奨です。"
            elif not _commercial_setup_public_url(value):
                status = "warn"
                detail = "公開サポートURL形式ではありません。"
        rows.append((field, label, status, detail, action))
    checks = [
        (
            "commercial_terms_reviewed",
            "利用条件/商用方針",
            settings.commercial_terms_reviewed,
            "販売前確認済み",
            "利用条件/商用方針の確認チェックをONにします。",
        ),
        (
            "commercial_support_scope_confirmed",
            "サポート範囲",
            settings.commercial_support_scope_confirmed,
            "販売ページに明記済み",
            "サポート範囲と返金条件の明記チェックをONにします。",
        ),
    ]
    for field, label, ok, ok_detail, action in checks:
        status = "ok" if ok else "missing"
        detail = ok_detail if ok else "未確認"
        rows.append((field, label, status, detail, action))
    return rows


def _commercial_setup_status_label(status: str) -> str:
    return {
        "ok": "OK",
        "warn": "確認",
        "missing": "未入力",
    }.get(status, status.upper())


def _commercial_setup_public_url(value: str) -> bool:
    return value.strip().lower().startswith(("http://", "https://"))


def _commercial_setup_raw_email(value: str) -> bool:
    text = value.strip()
    return "@" in text and not _commercial_setup_public_url(text)


def _home_primary_button_label(step: ActionPlanStep | None) -> str:
    if step is None:
        return "詳細を見る"
    source = f"{step.title} {step.gui} {step.source}".lower()
    if "セットアップ" in step.title or "setup" in source:
        return "セットアップへ"
    if "品質" in step.title or "quality" in source:
        return "品質チェックへ"
    if "トラブル" in step.title or "診断" in step.title or "troubleshoot" in source:
        return "診断を開く"
    if "販売者" in step.title or "commercial" in source:
        return "販売者情報へ"
    if "投稿キュー" in step.title or "publish" in source:
        return "投稿キューへ"
    if "記事" in step.title or "review" in source:
        return "記事を直す"
    if "サポート" in step.title or "support" in source:
        return "サポートへ"
    if "バックアップ" in step.title or "backup" in source:
        return "バックアップ"
    label = step.title.strip() or "次を実行"
    return label if len(label) <= 12 else label[:10] + "..."


def _home_overview_badge(readiness_score: int, status: str) -> tuple[str, str, str]:
    normalized = status.lower()
    if "blocker" in normalized or "ng" in normalized or readiness_score < 60:
        return ("ACTION", UI_COLORS["danger"], "#ffffff")
    if "ready" in normalized or readiness_score >= 90:
        return ("READY", UI_COLORS["ok"], "#ffffff")
    if readiness_score >= 75:
        return ("CHECK", UI_COLORS["info"], "#ffffff")
    return ("CHECK", UI_COLORS["warn"], "#ffffff")


def _home_state_accent_color(state: str) -> str:
    return {
        "ok": UI_COLORS["ok"],
        "info": UI_COLORS["info"],
        "warn": UI_COLORS["warn"],
        "fail": UI_COLORS["danger"],
    }.get(state, UI_COLORS["line"])


def _home_sales_indicator_style(state: str) -> tuple[str, str, str]:
    return {
        "ok": ("OK", "#047857", "#ffffff"),
        "info": ("CHECK", "#2563eb", "#ffffff"),
        "warn": ("CHECK", "#b45309", "#ffffff"),
        "fail": ("NG", "#dc2626", "#ffffff"),
    }.get(state, ("CHECK", "#334155", "#ffffff"))


def _support_bundle_indicator_style(text: str) -> tuple[str, str, str]:
    if text == "OK":
        return ("OK", "#047857", "#ffffff")
    if text.startswith("NG"):
        return ("NG", "#dc2626", "#ffffff")
    if text == "要更新":
        return ("UPDATE", "#b45309", "#ffffff")
    return ("CHECK", "#2563eb", "#ffffff")


def _support_contact_indicator_style(contact: str) -> tuple[str, str, str]:
    if contact.strip() and contact.strip() != "未設定":
        return ("OK", "#047857", "#ffffff")
    return ("REQ", "#b45309", "#ffffff")


def _support_send_readiness_indicator_style(text: str) -> tuple[str, str, str]:
    if text == "準備OK":
        return ("READY", "#047857", "#ffffff")
    if text in {"要確認", "要更新"}:
        return ("CHECK", "#b45309", "#ffffff")
    return ("REQ", "#dc2626", "#ffffff")


def _support_next_button_label(action: str) -> str:
    return {
        "問い合わせ一式を作成": "次: 一式作成",
        "問い合わせ一式を再作成": "次: 一式再作成",
        "一式ZIP検証で詳細確認": "次: ZIP検証",
        "サポート連絡先を設定": "次: 連絡先",
        "送付前リストを確認": "次: リスト確認",
        "送付文コピー": "次: 送付文",
    }.get(action, "次を実行")


def _home_support_next_button_label(action: str) -> str:
    return {
        "問い合わせ一式を作成": "サポート: 一式作成",
        "問い合わせ一式を再作成": "サポート: 再作成",
        "一式ZIP検証で詳細確認": "サポート: ZIP検証",
        "サポート連絡先を設定": "サポート: 連絡先",
        "送付前リストを確認": "サポート: リスト",
        "送付文コピー": "サポート: 送付文",
    }.get(action, "サポート次実行")


def _home_buyer_send_button_label(action: str) -> str:
    return {
        "購入者ZIP作成": "購入者送付: ZIP作成",
        "購入者ZIP更新": "購入者送付: ZIP更新",
        "購入者ZIP検証": "購入者送付: ZIP検証",
        "送付文作成": "購入者送付: 文作成",
        "送付記録": "購入者送付: 記録",
        "送付文コピー": "購入者送付: 文コピー",
        "最終レビュー": "購入者送付: 最終確認",
    }.get(action, "購入者送付: 次")


def _publish_ready_counts(report: PublishReadyReport) -> dict[str, int]:
    return {
        "OK": sum(1 for item in report.items if item.status == "pass"),
        "INFO": sum(1 for item in report.items if item.status == "info"),
        "WARN": sum(1 for item in report.items if item.status == "warn"),
        "NG": sum(1 for item in report.items if item.status == "fail"),
    }


def _publish_ready_verdict(status: str) -> str:
    return {"pass": "READY", "warn": "CHECK", "fail": "BLOCKED"}.get(status, status.upper())


def _publish_ready_item_label(status: str) -> str:
    return {"pass": "OK", "info": "INFO", "warn": "WARN", "fail": "NG"}.get(status, status.upper())


def _publish_ready_status_colors(status: str) -> tuple[str, str]:
    colors = {
        "pass": ("#146c5f", "#ffffff"),
        "info": ("#174ea6", "#ffffff"),
        "warn": ("#8a4f00", "#ffffff"),
        "fail": ("#8b2119", "#ffffff"),
    }
    return colors.get(status, ("#344054", "#ffffff"))


def _publish_ready_summary(report: PublishReadyReport) -> str:
    counts = _publish_ready_counts(report)
    if report.status == "fail":
        return f"NG {counts['NG']}件を直すまで投稿前準備は止めてください。"
    if report.status == "warn":
        return f"WARN {counts['WARN']}件を確認すれば投稿へ進めます。"
    return "投稿前の基本確認は通っています。"


def _first_run_counts(report: FirstRunReport) -> dict[str, int]:
    return {
        "OK": sum(1 for item in report.items if item.status == "pass"),
        "INFO": sum(1 for item in report.items if item.status == "info"),
        "WARN": sum(1 for item in report.items if item.status == "warn"),
        "NG": sum(1 for item in report.items if item.status == "fail"),
    }


def _first_run_verdict(status: str) -> str:
    return {"pass": "READY", "warn": "CHECK", "fail": "BLOCKED"}.get(status, status.upper())


def _first_run_item_label(status: str) -> str:
    return {"pass": "OK", "info": "INFO", "warn": "WARN", "fail": "NG"}.get(status, status.upper())


def _first_run_status_colors(status: str) -> tuple[str, str]:
    colors = {
        "pass": ("#047857", "#ffffff"),
        "info": ("#2563eb", "#ffffff"),
        "warn": ("#b45309", "#ffffff"),
        "fail": ("#dc2626", "#ffffff"),
    }
    return colors.get(status, ("#334155", "#ffffff"))


def _first_run_summary(report: FirstRunReport) -> str:
    counts = _first_run_counts(report)
    if report.status == "fail":
        return f"起動や基本動作を止める項目があります。NG {counts['NG']}件を先に解消してください。"
    if report.status == "warn":
        return f"投稿は進められますが、販売前または本番投稿前にWARN {counts['WARN']}件を確認してください。"
    return "初回導線は整っています。記事レビュー、バックアップ、投稿ヘルパーの流れで進められます。"


def _home_first_run_summary(report: FirstRunReport) -> tuple[str, str]:
    counts = _first_run_counts(report)
    summary = f"初回: {report.score}/100 / NG {counts['NG']} / WARN {counts['WARN']} / OK {counts['OK']}"
    for status in ("fail", "warn", "info"):
        for item in report.items:
            if item.status == status:
                action = item.action or item.gui or item.command or item.detail
                return summary, f"次: {item.name} - {action}"
    return summary, "次: 受入保存または販売ナビへ進めます。"


def _home_commercial_focus_state(status: str) -> str:
    return {
        "ready": "ok",
        "missing": "warn",
        "warn": "warn",
        "check": "info",
    }.get(status, "info")


def _home_commercial_focus_text(settings: AppSettings) -> str:
    focus = commercial_setup_next_focus(settings)
    label = {
        "ready": "OK",
        "missing": "未入力",
        "warn": "確認",
        "check": "確認",
    }.get(focus.status, focus.status.upper())
    detail = _home_snapshot_brief(focus.detail, 54)
    if focus.status == "ready":
        return f"販売者次項目: {focus.label} / {label} - {detail}"
    return f"販売者次項目: {focus.label} / {label} - {detail} / {focus.gui}"


def _home_commercial_focus_button_label(status: str) -> str:
    if status == "ready":
        return "販売素材へ"
    return "販売者次へ"


def _home_release_check_summary(reports: list[Path]) -> tuple[str, str]:
    if not reports:
        return (
            "warn",
            "販売前一括: 未実行 / 販売前一括チェックで出荷前の総点検を保存します。",
        )
    latest = reports[0]
    status = _home_report_status("一括チェック", latest)
    state = _home_release_check_state(status, latest)
    freshness = _home_release_check_freshness_label(latest)
    if status == "OK":
        if freshness == "24h超":
            action = f"{RELEASE_CHECK_FRESHNESS_WARNING_HOURS}h超のため再実行推奨です。"
        elif freshness == "更新確認不可":
            action = "更新時刻を確認できないため再実行推奨です。"
        else:
            action = "販売直前の証跡として利用できます。"
    elif status == "NG":
        action = "表示で失敗箇所を確認します。"
    elif freshness == "24h超":
        action = f"{RELEASE_CHECK_FRESHNESS_WARNING_HOURS}h超です。再実行して最新化します。"
    elif freshness == "更新確認不可":
        action = "更新時刻を確認できません。内容を確認します。"
    else:
        action = "表示で内容を確認します。"
    freshness_text = f" / {freshness}" if freshness else ""
    return state, f"販売前一括: {status} / {_format_mtime(latest)}{freshness_text} / {action}"


def _home_release_check_button_label(reports: list[Path]) -> str:
    if not reports:
        return "一括実行"
    if _home_release_check_should_run(reports):
        return "再実行"
    return "結果表示"


def _home_release_check_timeline_detail(reports: list[Path]) -> tuple[str, str]:
    if not reports:
        return ("warn", "未実行")
    latest = reports[0]
    status = _home_report_status("一括チェック", latest)
    state = _home_release_check_state(status, latest)
    freshness = _home_release_check_freshness_label(latest)
    detail = f"{status} / {_format_mtime(latest)}"
    if freshness:
        detail += f" / {freshness}"
    return state, detail


def _home_release_check_should_run(reports: list[Path]) -> bool:
    if not reports:
        return True
    latest = reports[0]
    status = _home_report_status("一括チェック", latest)
    return status != "NG" and bool(_home_release_check_freshness_label(latest))


def _home_release_check_state(status: str, path: Path) -> str:
    state = _home_report_status_state(status)
    if status != "NG" and _home_release_check_freshness_label(path):
        return "warn"
    return state


def _home_release_check_freshness_label(path: Path) -> str:
    timestamp = _safe_mtime(path)
    if timestamp <= 0:
        return "更新確認不可"
    age_hours = max(0.0, (datetime.now().timestamp() - timestamp) / 3600)
    if age_hours > RELEASE_CHECK_FRESHNESS_WARNING_HOURS:
        return "24h超"
    return ""


def _home_buyer_send_summary(
    package_path: Path | None,
    message_path: Path | None,
    receipt_path: Path | None,
    *,
    package_errors: list[str] | None = None,
    package_matches_release: bool | None = None,
    message_matches_package: bool | None = None,
    receipt_matches_delivery: bool | None = None,
) -> tuple[str, str, str]:
    package_ok = bool(package_path and package_path.exists())
    message_ok = bool(message_path and message_path.exists())
    receipt_ok = bool(receipt_path and receipt_path.exists())
    if not package_ok:
        return (
            "warn",
            "購入者送付: ZIPなし / 送付文なし / 記録なし",
            "次: 販売一括作成 または 購入者ZIP抽出",
        )
    package_name = package_path.name if package_path else "未作成"
    package_detail = f"{package_name} / {_format_file_size(package_path)}"
    package_error_count = len(package_errors or [])
    if package_error_count:
        return (
            "fail",
            f"購入者送付: {package_detail} / ZIP検証NG {package_error_count}件 / "
            f"送付文 {'あり' if message_ok else 'なし'} / 記録 {'あり' if receipt_ok else 'なし'}",
            "次: 購入者ZIP検証で詳細確認、必要なら販売一括作成で作り直す",
        )
    if package_matches_release is False:
        return (
            "warn",
            f"購入者送付: {package_detail} / 配布ZIP要更新 / "
            f"送付文 {'あり' if message_ok else 'なし'} / 記録 {'あり' if receipt_ok else 'なし'}",
            "次: 販売一括作成で最新配布ZIPの購入者ZIPと送付文を作り直す",
        )
    if not message_ok:
        return (
            "warn",
            f"購入者送付: ZIPあり / 送付文なし / 記録 {'あり' if receipt_ok else 'なし'}",
            "次: 販売一括作成で送付文を作成",
        )
    if message_matches_package is False:
        return (
            "warn",
            f"購入者送付: {package_detail} / 送付文不一致 / 記録 {'あり' if receipt_ok else 'なし'}",
            "次: 送付文作成で最新ZIP名とSHA-256に合わせる",
        )
    if not receipt_ok:
        return (
            "info",
            f"購入者送付: {package_detail} / 送付文あり / 記録なし",
            "次: 送付前チェックを確認して送付記録を保存",
        )
    if receipt_matches_delivery is False:
        return (
            "warn",
            f"購入者送付: {package_detail} / 送付文あり / 記録不一致",
            "次: 送付記録で最新ZIPと送付文に合わせる",
        )
    return (
        "ok",
        f"購入者送付: {package_detail} / 送付文あり / 記録あり",
        "次: 最終レビューで販売ページ文案と納品物の整合性を確認",
    )


def _home_sales_screenshot_text(screenshot_packs: list[Path]) -> str:
    if not screenshot_packs:
        return "なし"
    return "NG" if verify_sales_screenshot_pack(screenshot_packs[0]) else "あり"


def _home_sales_artifact_status(paths: list[Path], kind: str) -> str:
    if not paths:
        return "なし"
    latest = paths[0]
    if kind == "release":
        return "NG" if verify_release_package(latest) else "あり"
    if kind == "materials":
        return "NG" if verify_sales_materials(latest) else "あり"
    if kind == "listing":
        return "NG" if verify_sales_listing_kit(latest) else "あり"
    if kind == "handoff":
        return "NG" if verify_sales_handoff(latest) else "あり"
    return "あり"


def _home_sales_artifact_text(
    releases: list[Path],
    materials: list[Path],
    listing_packages: list[Path],
    handoffs: list[Path],
) -> str:
    return (
        f"配布ZIP {_home_sales_artifact_status(releases, 'release')} / "
        f"素材 {_home_sales_artifact_status(materials, 'materials')} / "
        f"掲載キット {_home_sales_artifact_status(listing_packages, 'listing')} / "
        f"販売一式 {_home_sales_artifact_status(handoffs, 'handoff')}"
    )


def _home_sales_artifact_ng_count(
    releases: list[Path],
    materials: list[Path],
    screenshot_packs: list[Path],
    listing_packages: list[Path],
    handoffs: list[Path],
    buyer_packages: list[Path],
    *,
    buyer_package_errors: list[str] | None = None,
) -> int:
    statuses = [
        _home_sales_artifact_status(releases, "release"),
        _home_sales_artifact_status(materials, "materials"),
        _home_sales_screenshot_text(screenshot_packs),
        _home_sales_artifact_status(listing_packages, "listing"),
        _home_sales_artifact_status(handoffs, "handoff"),
    ]
    if buyer_packages:
        statuses.append("NG" if buyer_package_errors else "あり")
    return sum(1 for status in statuses if status == "NG")


def _home_sales_handoff_release_name(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        with zipfile.ZipFile(path) as archive:
            raw = json.loads(archive.read("SALES_HANDOFF_MANIFEST.json").decode("utf-8"))
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if not isinstance(raw, dict):
        return ""
    release_package = raw.get("release_package")
    return release_package if isinstance(release_package, str) else ""


def _home_buyer_delivery_package_release_name(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        with zipfile.ZipFile(path) as archive:
            if "BUYER_DELIVERY_MANIFEST.json" in archive.namelist():
                raw = json.loads(archive.read("BUYER_DELIVERY_MANIFEST.json").decode("utf-8"))
                if isinstance(raw, dict) and isinstance(raw.get("release_package"), str):
                    return raw["release_package"]
            release_entries = [
                name
                for name in archive.namelist()
                if PurePosixPath(name).parent == PurePosixPath(".")
                and PurePosixPath(name).name.startswith("auto-note-release-")
                and PurePosixPath(name).suffix.casefold() == ".zip"
            ]
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if len(release_entries) != 1:
        return ""
    return PurePosixPath(release_entries[0]).name


def _home_buyer_delivery_package_matches_release(
    package_path: Path | None,
    release_path: Path | None,
    *,
    package_errors: list[str] | None = None,
) -> bool | None:
    if not (package_path and package_path.exists() and release_path):
        return None
    if package_errors:
        return None
    package_release_name = _home_buyer_delivery_package_release_name(package_path)
    if not package_release_name:
        return None
    return package_release_name == release_path.name


def _home_delivery_release_summary(
    release_path: Path | None,
    package_path: Path | None,
    *,
    package_errors: list[str] | None = None,
    package_matches_release: bool | None = None,
) -> str:
    latest_release = _home_snapshot_brief(release_path.name if release_path else "未作成", 42)
    if not package_path:
        return f"納品照合: 配布ZIP {latest_release} / 購入者ZIP 未作成"
    package_release = _home_buyer_delivery_package_release_name(package_path)
    package_release_text = _home_snapshot_brief(package_release or "確認不可", 42)
    package_text = _home_snapshot_brief(package_path.name, 42)
    if package_errors:
        status = f"ZIP検証NG {len(package_errors)}件"
    elif package_matches_release is False:
        status = "要更新"
    elif package_matches_release is True:
        status = "一致"
    else:
        status = "要確認"
    return f"納品照合: 配布ZIP {latest_release} / 購入者ZIP内 {package_release_text} / {status} / {package_text}"


def _home_buyer_send_evidence_summary(
    package_path: Path | None,
    message_path: Path | None,
    receipt_path: Path | None,
    *,
    message_matches_package: bool | None = None,
    receipt_matches_delivery: bool | None = None,
    package_errors: list[str] | None = None,
) -> str:
    if not package_path:
        message_text = "送付文あり" if message_path else "送付文なし"
        receipt_text = "記録あり" if receipt_path else "記録なし"
        return f"送付証跡: ZIPなし / {message_text} / {receipt_text}"
    package_name = _home_snapshot_brief(package_path.name, 38)
    try:
        package_sha = hashlib.sha256(package_path.read_bytes()).hexdigest()[:12]
    except OSError:
        package_sha = "確認不可"
    if package_errors:
        zip_text = f"ZIP検証NG {len(package_errors)}件"
    else:
        zip_text = f"ZIP {package_name} / SHA {package_sha}"
    if not message_path:
        message_text = "送付文なし"
    elif message_matches_package is False:
        message_text = "送付文不一致"
    elif message_matches_package is True:
        message_text = f"送付文一致 {_home_snapshot_brief(message_path.name, 32)}"
    else:
        message_text = f"送付文要確認 {_home_snapshot_brief(message_path.name, 32)}"
    if not receipt_path:
        receipt_text = "記録なし"
    elif receipt_matches_delivery is False:
        receipt_text = "記録不一致"
    elif receipt_matches_delivery is True:
        receipt_text = f"記録一致 {_home_snapshot_brief(receipt_path.name, 32)}"
    else:
        receipt_text = f"記録要確認 {_home_snapshot_brief(receipt_path.name, 32)}"
    return f"送付証跡: {zip_text} / {message_text} / {receipt_text}"


def _home_sales_artifact_stale_count(
    releases: list[Path],
    handoffs: list[Path],
    buyer_packages: list[Path],
    *,
    buyer_package_errors: list[str] | None = None,
) -> int:
    if not releases:
        return 0
    latest_release_name = releases[0].name
    stale_count = 0
    handoff_release_name = _home_sales_handoff_release_name(handoffs[0] if handoffs else None)
    if handoff_release_name and handoff_release_name != latest_release_name:
        stale_count += 1
    buyer_release_name = _home_buyer_delivery_package_release_name(
        buyer_packages[0] if buyer_packages and not buyer_package_errors else None
    )
    if buyer_release_name and buyer_release_name != latest_release_name:
        stale_count += 1
    return stale_count


def _home_sales_freshness_text(
    releases: list[Path],
    handoffs: list[Path],
    buyer_packages: list[Path],
    *,
    buyer_package_errors: list[str] | None = None,
) -> str:
    stale_count = _home_sales_artifact_stale_count(
        releases,
        handoffs,
        buyer_packages,
        buyer_package_errors=buyer_package_errors,
    )
    return "OK" if stale_count == 0 else f"要更新 {stale_count}"


def _home_buyer_send_action(
    package_path: Path | None,
    message_path: Path | None,
    receipt_path: Path | None,
    *,
    package_errors: list[str] | None = None,
    package_matches_release: bool | None = None,
    message_matches_package: bool | None = None,
    receipt_matches_delivery: bool | None = None,
) -> str:
    if not (package_path and package_path.exists()):
        return "購入者ZIP作成"
    if package_errors:
        return "購入者ZIP検証"
    if package_matches_release is False:
        return "購入者ZIP更新"
    if not (message_path and message_path.exists()):
        return "送付文作成"
    if message_matches_package is False:
        return "送付文作成"
    if not (receipt_path and receipt_path.exists()):
        return "送付記録"
    if receipt_matches_delivery is False:
        return "送付記録"
    return "最終レビュー"


def _home_buyer_send_message_matches_package(package_path: Path | None, message_path: Path | None) -> bool | None:
    if not (package_path and package_path.exists() and message_path and message_path.exists()):
        return None
    try:
        message_text = message_path.read_text(encoding="utf-8", errors="replace")
        package_sha = hashlib.sha256(package_path.read_bytes()).hexdigest()
    except OSError:
        return False
    return package_path.name in message_text and package_sha in message_text


def _home_buyer_send_receipt_matches_delivery(
    package_path: Path | None,
    message_path: Path | None,
    receipt_path: Path | None,
) -> bool | None:
    if not (
        package_path
        and package_path.exists()
        and message_path
        and message_path.exists()
        and receipt_path
        and receipt_path.exists()
    ):
        return None
    try:
        receipt_text = receipt_path.read_text(encoding="utf-8", errors="replace")
        package_sha = hashlib.sha256(package_path.read_bytes()).hexdigest()
    except OSError:
        return False
    return (
        package_path.name in receipt_text
        and message_path.name in receipt_text
        and package_sha in receipt_text
    )


def _article_selection_rank(article: Article) -> int:
    return {
        "ready": 0,
        "scheduled": 1,
        "draft": 2,
        "published": 4,
    }.get(article.status or "draft", 3)


def _backup_restore_confirmation(inspection) -> str:
    lines = [
        "選択したバックアップから記事、設定、アイデアを復元します。",
        "",
        f"復元対象: {len(inspection.restorable_files)}件",
        f"記事: {len(inspection.article_files)}件",
        f"設定: {'あり' if inspection.has_settings else 'なし'}",
        f"アイデア: {'あり' if inspection.has_ideas else 'なし'}",
    ]
    if inspection.ignored_files:
        lines.append(f"復元対象外: {len(inspection.ignored_files)}件")
    return "\n".join(lines)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _format_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _format_mtime(path: Path) -> str:
    timestamp = _safe_mtime(path)
    if timestamp <= 0:
        return "確認不可"
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def _format_file_size(path: Path) -> str:
    try:
        value = path.stat().st_size
    except OSError:
        return "確認不可"
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value} B"


def _relative_parent_label(project_dir: Path, path: Path) -> str:
    try:
        return str(path.parent.resolve().relative_to(project_dir.resolve()))
    except ValueError:
        return path.parent.name


def _home_report_status(label: str, path: Path) -> str:
    if not path.exists():
        return "なし"
    if label == "問い合わせZIP":
        return "NG" if verify_support_bundle(path) else "OK"
    if label == "配布ZIP":
        return "NG" if verify_release_package(path) else "OK"
    if label == "掲載画像":
        return "NG" if verify_sales_screenshot_pack(path) else "OK"
    if label == "掲載キット":
        return "NG" if verify_sales_listing_kit(path) else "OK"
    if label == "購入者ZIP":
        return "NG" if verify_buyer_delivery_package(path) else "OK"
    if label == "販売直前":
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return "NG"
        if "Verdict: BLOCKED" in text:
            return "NG"
        if "Verdict: NEEDS REVIEW" in text:
            return "確認"
        return "OK"
    if label == "販売確認":
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return "NG"
        if "blocker count: 0" not in text:
            return "NG"
        if "warning count: 0" not in text:
            return "確認"
        return "OK"
    if label == "一括チェック":
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return "NG"
        if "status: OK" in text:
            return "OK"
        if "status: NG" in text or "Traceback" in text:
            return "NG"
        return "確認"
    if path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(path) as archive:
                broken = archive.testzip()
        except (OSError, zipfile.BadZipFile):
            return "NG"
        return "NG" if broken else "OK"
    try:
        return "OK" if path.is_file() else "確認"
    except OSError:
        return "NG"


def _home_report_status_tag(status: str) -> str:
    if status == "OK":
        return "ok"
    if status == "NG":
        return "fail"
    if status == "なし":
        return "missing"
    return "check"


def _home_report_status_state(status: str) -> str:
    if status == "OK":
        return "ok"
    if status == "NG":
        return "fail"
    if status == "なし":
        return "warn"
    return "info"


def _home_report_summary(prefix: str, label: str, path: Path, status: str) -> str:
    if status == "NG":
        next_action = "表示で詳細確認"
    elif status in {"なし", "確認"}:
        next_action = "表示で内容確認"
    else:
        next_action = "利用可"
    updated = _format_mtime(path) if path.exists() else "not found"
    return f"{prefix}: {label} / {status} / {next_action} / {updated} / {path.name}"


def _format_zip_report_summary(path: Path) -> list[str]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    except (OSError, zipfile.BadZipFile) as exc:
        return [f"[NG] ZIPを読み取れません: {exc}"]
    lines = [f"ZIP contents: {len(names)} file(s)"]
    lines.extend(f"- {name}" for name in names[:80])
    if len(names) > 80:
        lines.append(f"... and {len(names) - 80} more")
    return lines


def _bounded_int_var(variable: tk.IntVar, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(variable.get())
    except (tk.TclError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _open_existing(path: Path, missing_message: str) -> None:
    if path.exists():
        _open_path(path)
    else:
        messagebox.showinfo("ファイルなし", missing_message)


def _open_path(path: Path) -> None:
    path = path.resolve()
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        webbrowser.open(path.as_uri())


def _buyer_delivery_package_for(directory: Path) -> Path:
    stamp = directory.name.replace("buyer-delivery-", "", 1)
    return directory.parent / f"auto-note-buyer-delivery-{stamp}.zip"


def _buyer_support_request_for(directory: Path) -> Path:
    return directory / "BUYER_SUPPORT_REQUEST.txt"
