from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import zipfile

from . import __version__
from .app_info import read_install_info
from .article import ArticleError, load_article
from .commercial_setup import (
    commercial_setup_completion,
    commercial_setup_missing_fields,
    commercial_setup_next_field,
    commercial_setup_warnings,
)
from .inspect import inspect_article
from .paths import unique_path
from .settings import inspect_settings, list_settings_recovery_files, load_settings
from .workflow import inspect_ideas, list_idea_recovery_files


@dataclass(frozen=True)
class DiagnosticItem:
    name: str
    ok: bool
    detail: str


REQUIRED_DIAGNOSTIC_REPORT_FILES = (
    "diagnostics.txt",
    "article-index.txt",
    "article-review.txt",
    "first-run.txt",
    "acceptance.txt",
    "self-test.txt",
    "action-plan.txt",
    "overview.txt",
    "calendar.txt",
    "quickstart.txt",
    "publish-ready.txt",
    "improvement-plan.txt",
    "publish-queue.txt",
    "gui-smoke.txt",
    "preflight.txt",
    "troubleshoot.txt",
    "settings-summary.txt",
    "readiness.txt",
    "commercial-readiness.txt",
    "commercial-setup-template.txt",
    "sales-plan.txt",
    "sales-materials.txt",
    "sales-finalize.txt",
    "sales-launch.txt",
    "seller-send-checklist.txt",
    "sales-evidence-manifest.json",
    "product-quality.txt",
    "quality.txt",
    "maintenance-summary.txt",
)

DIAGNOSTIC_PREVIEW_SECTION_LIMIT = 900
DIAGNOSTIC_PREVIEW_MAINTENANCE_LIMIT = 1600
DIAGNOSTIC_PREVIEW_OMITTED_SECTIONS = {
    "first-run.txt": "First-run checklist / 初回チェック",
    "acceptance.txt": "Acceptance check / 受入チェック",
    "self-test.txt": "Self-test report / セルフテスト",
    "action-plan.txt": "Action plan / 次の一手",
    "overview.txt": "Overview / 運用サマリー",
    "calendar.txt": "Calendar / 公開予定",
    "quickstart.txt": "Quickstart report",
    "publish-ready.txt": "Publish readiness report",
    "improvement-plan.txt": "Improvement plan / 改善プラン",
    "publish-queue.txt": "Publish queue / 投稿キュー",
    "gui-smoke.txt": "GUI smoke",
    "preflight.txt": "Preflight report",
    "readiness.txt": "Readiness report",
    "commercial-readiness.txt": "Commercial readiness / 販売準備",
    "sales-plan.txt": "Sales plan / 販売ナビ",
    "sales-materials.txt": "Sales materials / 販売素材",
    "sales-finalize.txt": "Sales finalize / 販売準備一括",
    "sales-launch.txt": "Sales launch checklist / 販売直前チェック",
    "seller-send-checklist.txt": "Seller send checklist / 販売者送付前チェックリスト",
    "product-quality.txt": "Product quality report",
    "quality.txt": "Quality report",
}


def _truncate_preview_text(text: str, *, max_chars: int = DIAGNOSTIC_PREVIEW_SECTION_LIMIT) -> str:
    clean = text.rstrip()
    if len(clean) <= max_chars:
        return clean
    if max_chars < 80:
        omitted = len(clean) - max_chars
        return (
            clean[:max_chars].rstrip()
            + f"\n...[truncated {omitted} chars; full content is in diagnostic-report.zip]"
        )
    head_chars = max_chars * 2 // 3
    tail_chars = max_chars - head_chars
    omitted = len(clean) - max_chars
    return (
        clean[:head_chars].rstrip()
        + f"\n...[truncated {omitted} chars; full content is in diagnostic-report.zip]"
        + "\n"
        + clean[-tail_chars:].lstrip()
    )


def _format_preview_section(
    name: str,
    text: str,
    *,
    max_chars: int = DIAGNOSTIC_PREVIEW_SECTION_LIMIT,
    required_prefixes: tuple[str, ...] = (),
) -> list[str]:
    body = _truncate_preview_text(text, max_chars=max_chars)
    if required_prefixes:
        missing = [
            line
            for line in text.splitlines()
            if line.startswith(required_prefixes) and line not in body
        ]
        if missing:
            body = body.rstrip() + "\n\nImportant lines\n" + "\n".join(missing)
    return [name, body] if body else [name, "(empty)"]


def _preview_omitted_report(title: str) -> str:
    return f"{title}\n\nPreview omitted for speed; full content is in diagnostic-report.zip."


def run_diagnostics(project_dir: Path) -> list[DiagnosticItem]:
    items = [
        DiagnosticItem("auto-note version", True, __version__),
        DiagnosticItem("Python", True, sys.version.split()[0]),
        DiagnosticItem("Platform", True, platform.platform()),
        _check_import("tkinter"),
        _check_project_dir(project_dir),
        _check_writable(project_dir),
        _check_path(project_dir / "articles", "articles folder"),
        _check_path(project_dir / "auto-note-gui.bat", "GUI launcher"),
        _check_path(project_dir / "auto-note.lnk", "GUI shortcut"),
        _check_path(project_dir / ".venv" / "Scripts" / "python.exe", "virtualenv python"),
        _settings_item(project_dir),
        _commercial_setup_item(project_dir),
        _ideas_item(project_dir),
        _install_info_item(project_dir),
    ]
    log_path = project_dir / ".auto-note" / "gui-error.log"
    if log_path.exists():
        detail = f"{log_path} ({log_path.stat().st_size} bytes)"
        items.append(DiagnosticItem("latest GUI log", True, detail))
    else:
        items.append(DiagnosticItem("latest GUI log", True, "not created yet"))
    return items


def format_diagnostics(items: list[DiagnosticItem]) -> str:
    lines = []
    for item in items:
        status = "OK" if item.ok else "NG"
        lines.append(f"[{status}] {item.name}: {item.detail}")
    return "\n".join(lines)


def _commercial_setup_item(project_dir: Path) -> DiagnosticItem:
    settings = load_settings(project_dir)
    complete, total = commercial_setup_completion(settings)
    missing = commercial_setup_missing_fields(settings)
    warnings = commercial_setup_warnings(settings)
    next_field = commercial_setup_next_field(settings) or "none"
    detail = f"completion {complete}/{total}, missing {len(missing)}, warnings {len(warnings)}, next field {next_field}"
    return DiagnosticItem("commercial setup", True, detail)


def create_diagnostic_report(project_dir: Path, *, include_private: bool = False) -> Path:
    reports_dir = project_dir / ".auto-note" / "diagnostics"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = unique_path(reports_dir / f"auto-note-diagnostic-{datetime.now():%Y%m%d-%H%M%S}.zip")

    diagnostics = format_diagnostics(run_diagnostics(project_dir))
    article_index = _build_article_index(project_dir, include_private=include_private)
    article_review = _build_article_review_report(project_dir, include_private=include_private)
    first_run = _build_first_run_report(project_dir)
    acceptance = _build_acceptance_report(project_dir)
    self_test = _build_self_test_report(project_dir)
    action_plan = _build_action_plan_report(project_dir)
    overview = _build_overview_report(project_dir, include_private=include_private)
    calendar = _build_calendar_report(project_dir, include_private=include_private)
    quickstart = _build_quickstart_report(project_dir, include_private=include_private)
    publish_ready = _build_publish_ready_report(project_dir, include_private=include_private)
    improvement_plan = _build_improvement_plan_report(project_dir, include_private=include_private)
    publish_queue = _build_publish_queue_report(project_dir, include_private=include_private)
    gui_smoke = _build_gui_smoke_report(project_dir)
    preflight = _build_preflight_report(project_dir)
    troubleshoot = _build_troubleshoot_report(project_dir)
    readiness = _build_readiness_report(project_dir)
    commercial_readiness = _build_commercial_readiness_report(project_dir)
    commercial_setup_template = _build_commercial_setup_template_report(project_dir)
    sales_plan = _build_sales_plan_report(project_dir)
    sales_materials = _build_sales_materials_report(project_dir)
    sales_finalize = _build_sales_finalize_report(project_dir)
    sales_launch = _build_sales_launch_report(project_dir)
    seller_send_checklist = _build_seller_send_checklist_report(project_dir)
    sales_evidence_manifest = _build_sales_evidence_manifest_report(project_dir)
    product_quality = _build_quality_report(project_dir, include_articles=False)
    quality = _build_quality_report(project_dir)
    maintenance = _build_maintenance_summary(project_dir)
    if not include_private:
        diagnostics = mask_text(diagnostics, project_dir)
        article_review = mask_text(article_review, project_dir)
        first_run = mask_text(first_run, project_dir)
        acceptance = mask_text(acceptance, project_dir)
        self_test = mask_text(self_test, project_dir)
        action_plan = mask_text(action_plan, project_dir)
        overview = mask_text(overview, project_dir)
        calendar = mask_text(calendar, project_dir)
        quickstart = mask_text(quickstart, project_dir)
        publish_ready = mask_text(publish_ready, project_dir)
        improvement_plan = mask_text(improvement_plan, project_dir)
        publish_queue = mask_text(publish_queue, project_dir)
        gui_smoke = mask_text(gui_smoke, project_dir)
        preflight = mask_text(preflight, project_dir)
        troubleshoot = mask_text(troubleshoot, project_dir)
        readiness = mask_text(readiness, project_dir)
        commercial_readiness = mask_text(commercial_readiness, project_dir)
        commercial_setup_template = mask_text(commercial_setup_template, project_dir)
        sales_plan = mask_text(sales_plan, project_dir)
        sales_materials = mask_text(sales_materials, project_dir)
        sales_finalize = mask_text(sales_finalize, project_dir)
        sales_launch = mask_text(sales_launch, project_dir)
        seller_send_checklist = mask_text(seller_send_checklist, project_dir)
        sales_evidence_manifest = mask_text(sales_evidence_manifest, project_dir)
        product_quality = mask_text(product_quality, project_dir)
        quality = mask_text(quality, project_dir)
        maintenance = mask_text(maintenance, project_dir)

    with zipfile.ZipFile(report_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostics.txt", diagnostics + "\n")
        archive.writestr("article-index.txt", article_index + "\n")
        archive.writestr("article-review.txt", article_review + "\n")
        archive.writestr("first-run.txt", first_run + "\n")
        archive.writestr("acceptance.txt", acceptance + "\n")
        archive.writestr("self-test.txt", self_test + "\n")
        archive.writestr("action-plan.txt", action_plan + "\n")
        archive.writestr("overview.txt", overview + "\n")
        archive.writestr("calendar.txt", calendar + "\n")
        archive.writestr("quickstart.txt", quickstart + "\n")
        archive.writestr("publish-ready.txt", publish_ready + "\n")
        archive.writestr("improvement-plan.txt", improvement_plan + "\n")
        archive.writestr("publish-queue.txt", publish_queue + "\n")
        archive.writestr("gui-smoke.txt", gui_smoke + "\n")
        archive.writestr("preflight.txt", preflight + "\n")
        archive.writestr("troubleshoot.txt", troubleshoot + "\n")
        archive.writestr("settings-summary.txt", _build_settings_summary(project_dir))
        archive.writestr("readiness.txt", readiness + "\n")
        archive.writestr("commercial-readiness.txt", commercial_readiness + "\n")
        archive.writestr("commercial-setup-template.txt", commercial_setup_template + "\n")
        archive.writestr("sales-plan.txt", sales_plan + "\n")
        archive.writestr("sales-materials.txt", sales_materials + "\n")
        archive.writestr("sales-finalize.txt", sales_finalize + "\n")
        archive.writestr("sales-launch.txt", sales_launch + "\n")
        archive.writestr("seller-send-checklist.txt", seller_send_checklist + "\n")
        archive.writestr("sales-evidence-manifest.json", sales_evidence_manifest + "\n")
        archive.writestr("product-quality.txt", product_quality + "\n")
        archive.writestr("quality.txt", quality + "\n")
        archive.writestr("maintenance-summary.txt", maintenance + "\n")
        _write_text_file(archive, project_dir, ".auto-note/gui-error.log", include_private=include_private)
        path = project_dir / "pyproject.toml"
        if path.exists() and path.is_file():
            archive.write(path, "pyproject.toml")
        if include_private:
            settings_path = project_dir / ".auto-note" / "settings.json"
            if settings_path.exists():
                archive.write(settings_path, ".auto-note/settings.json")

    return report_path


def preview_diagnostic_report(project_dir: Path, *, include_private: bool = False) -> str:
    diagnostics = format_diagnostics(run_diagnostics(project_dir))
    article_index = _build_article_index(project_dir, include_private=include_private)
    article_review = _build_article_review_report(project_dir, include_private=include_private)
    troubleshoot = _build_troubleshoot_report(project_dir)
    commercial_setup_template = _build_commercial_setup_template_report(project_dir)
    sales_evidence_manifest = _build_sales_evidence_manifest_report(project_dir)
    maintenance = _build_maintenance_summary(project_dir)
    omitted = {
        name: _preview_omitted_report(title)
        for name, title in DIAGNOSTIC_PREVIEW_OMITTED_SECTIONS.items()
    }
    if not include_private:
        diagnostics = mask_text(diagnostics, project_dir)
        article_review = mask_text(article_review, project_dir)
        troubleshoot = mask_text(troubleshoot, project_dir)
        commercial_setup_template = mask_text(commercial_setup_template, project_dir)
        sales_evidence_manifest = mask_text(sales_evidence_manifest, project_dir)
        maintenance = mask_text(maintenance, project_dir)

    lines = [
        "Diagnostic report preview",
        "",
        "Privacy",
        "raw details included" if include_private else "paths, user name, email, article titles, and article file names are masked",
        "",
        "Files",
        "- diagnostics.txt",
        "- article-index.txt",
        "- article-review.txt",
        "- first-run.txt",
        "- acceptance.txt",
        "- self-test.txt",
        "- action-plan.txt",
        "- overview.txt",
        "- calendar.txt",
        "- quickstart.txt",
        "- publish-ready.txt",
        "- improvement-plan.txt",
        "- publish-queue.txt",
        "- gui-smoke.txt",
        "- preflight.txt",
        "- troubleshoot.txt",
        "- settings-summary.txt",
        "- readiness.txt",
        "- commercial-readiness.txt",
        "- commercial-setup-template.txt",
        "- sales-plan.txt",
        "- sales-materials.txt",
        "- sales-finalize.txt",
        "- sales-launch.txt",
        "- seller-send-checklist.txt",
        "- sales-evidence-manifest.json",
        "- product-quality.txt",
        "- quality.txt",
        "- maintenance-summary.txt",
    ]
    if (project_dir / ".auto-note" / "gui-error.log").exists():
        lines.append("- .auto-note/gui-error.log")
    if (project_dir / "pyproject.toml").exists():
        lines.append("- pyproject.toml")
    if include_private and (project_dir / ".auto-note" / "settings.json").exists():
        lines.append("- .auto-note/settings.json")

    lines.extend(
        [
            "",
            "Preview note",
            "Shortened for fast support triage; full content is in diagnostic-report.zip.",
        ]
    )
    sections = [
        ("diagnostics.txt", diagnostics),
        ("article-index.txt", article_index),
        ("article-review.txt", article_review),
        ("first-run.txt", omitted["first-run.txt"]),
        ("acceptance.txt", omitted["acceptance.txt"]),
        ("self-test.txt", omitted["self-test.txt"]),
        ("action-plan.txt", omitted["action-plan.txt"]),
        ("overview.txt", omitted["overview.txt"]),
        ("calendar.txt", omitted["calendar.txt"]),
        ("quickstart.txt", omitted["quickstart.txt"]),
        ("publish-ready.txt", omitted["publish-ready.txt"]),
        ("improvement-plan.txt", omitted["improvement-plan.txt"]),
        ("publish-queue.txt", omitted["publish-queue.txt"]),
        ("gui-smoke.txt", omitted["gui-smoke.txt"]),
        ("preflight.txt", omitted["preflight.txt"]),
        ("troubleshoot.txt", troubleshoot),
        ("settings-summary.txt", _build_settings_summary(project_dir).rstrip()),
        ("readiness.txt", omitted["readiness.txt"]),
        ("commercial-readiness.txt", omitted["commercial-readiness.txt"]),
        ("commercial-setup-template.txt", commercial_setup_template),
        ("sales-plan.txt", omitted["sales-plan.txt"]),
        ("sales-materials.txt", omitted["sales-materials.txt"]),
        ("sales-finalize.txt", omitted["sales-finalize.txt"]),
        ("sales-launch.txt", omitted["sales-launch.txt"]),
        ("seller-send-checklist.txt", omitted["seller-send-checklist.txt"]),
        ("sales-evidence-manifest.json", sales_evidence_manifest),
        ("product-quality.txt", omitted["product-quality.txt"]),
        ("quality.txt", omitted["quality.txt"]),
        ("maintenance-summary.txt", maintenance),
    ]
    for name, text in sections:
        max_chars = (
            DIAGNOSTIC_PREVIEW_MAINTENANCE_LIMIT
            if name == "maintenance-summary.txt"
            else DIAGNOSTIC_PREVIEW_SECTION_LIMIT
        )
        required_prefixes = (
            (
                "latest_support_request:",
                "latest_support_bundle:",
                "latest_support_bundle_verified:",
                "latest_support_bundle_age_hours:",
                "latest_support_bundle_freshness:",
            )
            if name == "maintenance-summary.txt"
            else ()
        )
        lines.extend(
            [
                "",
                *_format_preview_section(
                    name,
                    text,
                    max_chars=max_chars,
                    required_prefixes=required_prefixes,
                ),
            ]
        )
    return "\n".join(lines)


def mask_text(text: str, project_dir: Path) -> str:
    masked = text
    replacements = {
        str(project_dir.resolve()): "<PROJECT_DIR>",
        project_dir.resolve().as_posix(): "<PROJECT_DIR>",
        str(Path.home()): "<HOME>",
        Path.home().as_posix(): "<HOME>",
        Path.home().name: "<USER>",
    }
    for value, replacement in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        if value:
            masked = re.sub(re.escape(value), replacement, masked, flags=re.IGNORECASE)
    masked = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "<EMAIL>", masked)
    return masked


def list_diagnostic_reports(project_dir: Path) -> list[Path]:
    reports_dir = project_dir / ".auto-note" / "diagnostics"
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)


def verify_diagnostic_report(report_path: Path) -> list[str]:
    if not report_path.exists():
        return [f"diagnostic report not found: {report_path}"]
    errors: list[str] = []
    try:
        with zipfile.ZipFile(report_path) as archive:
            names = archive.namelist()
            name_set = set(names)
            errors.extend(_verify_diagnostic_archive_names(names))
            bad_member = archive.testzip()
            if bad_member:
                errors.append(f"CRC check failed: {bad_member}")
            for required in REQUIRED_DIAGNOSTIC_REPORT_FILES:
                if required not in name_set:
                    errors.append(f"missing required file: {required}")
    except (OSError, zipfile.BadZipFile) as exc:
        return [f"unreadable diagnostic report: {exc}"]
    return errors


def format_diagnostic_report_verification(report_path: Path, errors: list[str]) -> str:
    details = _format_diagnostic_report_verification_details(report_path)
    if not errors:
        return "\n".join([f"[OK] diagnostic report verified: {report_path}", *details])
    lines = [f"[NG] diagnostic report verification failed: {report_path}"]
    lines.extend(f"- {error}" for error in errors)
    lines.extend(details)
    return "\n".join(lines)


def _verify_diagnostic_archive_names(names: list[str]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for name in names:
        normalized = name.replace("\\", "/")
        parts = [part for part in normalized.split("/") if part]
        if not normalized or normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
            errors.append(f"unsafe file name: {name}")
        if any(part == ".." or ":" in part for part in parts):
            errors.append(f"unsafe file name: {name}")
        if normalized != name:
            errors.append(f"non-normalized file name: {name}")
        if name in seen:
            errors.append(f"duplicate file name: {name}")
        seen.add(name)
    return errors


def _format_diagnostic_report_verification_details(report_path: Path) -> list[str]:
    try:
        size = report_path.stat().st_size
        with zipfile.ZipFile(report_path) as archive:
            names = set(archive.namelist())
    except (OSError, zipfile.BadZipFile):
        return ["Details / 詳細: unavailable"]
    required_present = sum(1 for name in REQUIRED_DIAGNOSTIC_REPORT_FILES if name in names)
    return [
        "Details / 詳細:",
        f"- files: {len(names)}",
        f"- required files: {required_present}/{len(REQUIRED_DIAGNOSTIC_REPORT_FILES)}",
        f"- size: {size} bytes",
        f"- GUI log: {'present' if '.auto-note/gui-error.log' in names else 'not included'}",
        f"- pyproject.toml: {'present' if 'pyproject.toml' in names else 'not included'}",
    ]


def _check_import(module_name: str) -> DiagnosticItem:
    try:
        __import__(module_name)
    except Exception as exc:
        return DiagnosticItem(module_name, False, str(exc))
    return DiagnosticItem(module_name, True, "available")


def _check_project_dir(project_dir: Path) -> DiagnosticItem:
    return DiagnosticItem("project directory", project_dir.exists(), str(project_dir))


def _check_path(path: Path, label: str) -> DiagnosticItem:
    return DiagnosticItem(label, path.exists(), str(path))


def _check_writable(project_dir: Path) -> DiagnosticItem:
    try:
        project_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=project_dir, delete=False) as handle:
            temp_path = Path(handle.name)
        temp_path.unlink(missing_ok=True)
    except Exception as exc:
        return DiagnosticItem("project writable", False, str(exc))
    return DiagnosticItem("project writable", True, os.fspath(project_dir))


def _install_info_item(project_dir: Path) -> DiagnosticItem:
    info = read_install_info(project_dir)
    if not info:
        return DiagnosticItem("install info", True, "not created yet")
    backup = info.preinstall_backup or "(none)"
    detail = f"version={info.version or '(unknown)'}, installed_at={info.installed_at or '(unknown)'}, backup={backup}"
    return DiagnosticItem("install info", True, detail)


def _settings_item(project_dir: Path) -> DiagnosticItem:
    status = inspect_settings(project_dir)
    recovery_files = list_settings_recovery_files(project_dir)
    detail = status.detail
    if recovery_files:
        detail += f", recovery backups: {len(recovery_files)}"
    return DiagnosticItem("settings file", status.ok, detail)


def _ideas_item(project_dir: Path) -> DiagnosticItem:
    status = inspect_ideas(project_dir)
    recovery_files = list_idea_recovery_files(project_dir)
    detail = status.detail
    if recovery_files:
        detail += f", recovery backups: {len(recovery_files)}"
    return DiagnosticItem("ideas file", status.ok, detail)


def _build_article_index(project_dir: Path, *, include_private: bool = False) -> str:
    articles_dir = project_dir / "articles"
    if not articles_dir.exists():
        return "articles folder not found"

    lines = ["Article index", ""]
    for path in sorted(articles_dir.glob("*.md")):
        try:
            article = load_article(path)
            report = inspect_article(article)
        except ArticleError as exc:
            name = path.name if include_private else "<article>.md"
            detail = str(exc) if include_private else "load error"
            lines.append(f"[NG] {name}: {detail}")
            continue
        status = article.status or "draft"
        scheduled = article.scheduled or "-"
        name = path.name if include_private else f"article-{len(lines) - 1:03d}.md"
        title = repr(article.title) if include_private else f"<title:{len(article.title)} chars>"
        tags = ", ".join(article.tags) if include_private and article.tags else f"{len(article.tags)} tag(s)"
        issue_count = len(report.issues)
        lines.append(
            f"[{'OK' if report.ok else 'NG'}] {name}: "
            f"title={title}, status={status}, scheduled={scheduled}, "
            f"chars={report.stats.body_chars}, tags={tags}, issues={issue_count}"
        )
    if len(lines) == 2:
        lines.append("no markdown articles")
    return "\n".join(lines)


def _build_settings_summary(project_dir: Path) -> str:
    settings = load_settings(project_dir)
    recovery_files = list_settings_recovery_files(project_dir)
    idea_recovery_files = list_idea_recovery_files(project_dir)
    lines = [
        "Settings summary",
        "",
        f"settings_status: {inspect_settings(project_dir).detail}",
        f"settings_recovery_backups: {len(recovery_files)}",
        f"ideas_status: {inspect_ideas(project_dir).detail}",
        f"ideas_recovery_backups: {len(idea_recovery_files)}",
        f"default_tags: {len(settings.default_tags)} tag(s)",
        f"default_status: {settings.default_status}",
        f"append_tags_by_default: {settings.append_tags_by_default}",
        f"open_note_with_helper: {settings.open_note_with_helper}",
        f"article_glob: {settings.article_glob}",
        f"onboarding_seen: {settings.onboarding_seen}",
        f"support_contact: {'set' if settings.support_contact else 'not set'}",
        f"image_optimize_by_default: {settings.image_optimize_by_default}",
        f"image_max_width: {settings.image_max_width}",
        f"image_quality: {settings.image_quality}",
    ]
    if recovery_files:
        lines.append(f"latest_settings_recovery: {recovery_files[0].name}")
    if idea_recovery_files:
        lines.append(f"latest_ideas_recovery: {idea_recovery_files[0].name}")
    return "\n".join(lines) + "\n"


def _build_article_review_report(project_dir: Path, *, include_private: bool = False) -> str:
    from .review import format_review_report, review_path

    settings = load_settings(project_dir)
    try:
        reviews = review_path(
            project_dir / "articles",
            pattern=settings.article_glob,
            append_tags=settings.append_tags_by_default,
        )
    except ArticleError as exc:
        return f"Article review\n\nreview unavailable: {exc}"
    return format_review_report(reviews, include_private=include_private)


def _build_preflight_report(project_dir: Path) -> str:
    from .preflight import format_preflight_report, run_preflight

    return format_preflight_report(run_preflight(project_dir))


def _build_troubleshoot_report(project_dir: Path) -> str:
    from .troubleshoot import format_troubleshoot_report, run_troubleshoot

    return format_troubleshoot_report(run_troubleshoot(project_dir))


def _build_quickstart_report(project_dir: Path, *, include_private: bool = False) -> str:
    from .quickstart import format_quickstart_report, run_quickstart

    return format_quickstart_report(run_quickstart(project_dir), include_private=include_private)


def _build_action_plan_report(project_dir: Path) -> str:
    from .action_plan import build_action_plan, format_action_plan

    return format_action_plan(build_action_plan(project_dir))


def _build_overview_report(project_dir: Path, *, include_private: bool = False) -> str:
    from .overview import build_overview, format_overview_report

    return format_overview_report(build_overview(project_dir), include_private=include_private)


def _build_calendar_report(project_dir: Path, *, include_private: bool = False) -> str:
    from .settings import load_settings
    from .workflow import format_calendar

    settings = load_settings(project_dir)
    return "Calendar / 公開予定\n\n" + format_calendar(
        project_dir / "articles",
        pattern=settings.article_glob,
        days=30,
        include_private=include_private,
    )


def _build_first_run_report(project_dir: Path) -> str:
    from .first_run import format_first_run_report, run_first_run_checklist

    return format_first_run_report(run_first_run_checklist(project_dir))


def _build_acceptance_report(project_dir: Path) -> str:
    from .acceptance import format_acceptance_report, run_acceptance_check

    return format_acceptance_report(run_acceptance_check(project_dir))


def _build_self_test_report(project_dir: Path) -> str:
    from .selftest import format_self_test_report, run_self_test

    return format_self_test_report(run_self_test(project_dir))


def _build_publish_ready_report(project_dir: Path, *, include_private: bool = False) -> str:
    from .publish_ready import format_publish_ready_report, run_publish_ready

    settings = load_settings(project_dir)
    articles_dir = project_dir / "articles"
    if not articles_dir.exists():
        return "Publish readiness report\n\nnot available: articles folder not found"
    article_paths = sorted(
        (path for path in articles_dir.glob(settings.article_glob) if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not article_paths:
        return "Publish readiness report\n\nnot available: no markdown articles"
    try:
        report = run_publish_ready(
            article_paths[0],
            append_tags=settings.append_tags_by_default,
            smoke_helper=False,
        )
    except ArticleError as exc:
        return f"Publish readiness report\n\nnot available: {exc}"
    return format_publish_ready_report(report, include_private=include_private)


def _build_improvement_plan_report(project_dir: Path, *, include_private: bool = False) -> str:
    from .improvement_plan import build_improvement_plan, format_improvement_plan
    from .publish_queue import build_publish_queue

    settings = load_settings(project_dir)
    report = build_publish_queue(project_dir)
    target: Path | None = None
    for entry in report.entries:
        if entry.readiness != "done":
            target = entry.source
            break
    if target is None:
        return "Improvement plan / 改善プラン\n\nnot available: no draft articles"
    try:
        plan = build_improvement_plan(
            target,
            append_tags=settings.append_tags_by_default,
        )
    except ArticleError as exc:
        return f"Improvement plan / 改善プラン\n\nnot available: {exc}"
    return format_improvement_plan(plan, include_private=include_private)


def _build_publish_queue_report(project_dir: Path, *, include_private: bool = False) -> str:
    from .publish_queue import build_publish_queue, format_publish_queue_report

    return format_publish_queue_report(build_publish_queue(project_dir), include_private=include_private)


def _build_gui_smoke_report(project_dir: Path) -> str:
    lines = ["GUI smoke", ""]
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "auto_note",
                "gui",
                "--project-dir",
                str(project_dir),
                "--smoke",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        lines.append(f"[NG] gui smoke: {exc}")
        lines.append("next: auto-note gui --project-dir . --smoke")
        return "\n".join(lines)

    output = (result.stdout or result.stderr or "").strip()
    detail = output.splitlines()[-1] if output else f"exit code {result.returncode}"
    if result.returncode == 0:
        lines.append(f"[OK] gui smoke: {detail}")
    else:
        lines.append(f"[NG] gui smoke: {detail}")
        lines.append("next: auto-note gui --project-dir . --smoke")
    return "\n".join(lines)


def _build_readiness_report(project_dir: Path) -> str:
    from .readiness import format_readiness_report, run_readiness

    return format_readiness_report(run_readiness(project_dir))


def _build_commercial_readiness_report(project_dir: Path) -> str:
    from .commercial import format_commercial_readiness_report, run_commercial_readiness

    return format_commercial_readiness_report(run_commercial_readiness(project_dir))


def _build_commercial_setup_template_report(project_dir: Path) -> str:
    from .commercial_setup import list_commercial_setup_templates

    templates = list_commercial_setup_templates(project_dir)
    if not templates:
        return "Commercial setup template / 販売者情報テンプレート\n\nNo commercial setup template found."
    latest = templates[0]
    try:
        text = latest.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Commercial setup template / 販売者情報テンプレート\n\nCould not read {latest.name}: {exc}"
    return text


def _build_sales_plan_report(project_dir: Path) -> str:
    from .sales_plan import build_sales_plan, format_sales_plan

    return format_sales_plan(build_sales_plan(project_dir))


def _build_sales_materials_report(project_dir: Path) -> str:
    from .sales_materials import format_sales_materials_verification, list_sales_materials, verify_sales_materials

    materials = list_sales_materials(project_dir)
    if not materials:
        return "Sales materials / 販売素材\n\nNo sales materials found."
    latest = materials[0]
    try:
        text = latest.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Sales materials / 販売素材\n\nCould not read {latest.name}: {exc}"
    errors = verify_sales_materials(latest, strict=True, project_dir=project_dir)
    verification = format_sales_materials_verification(latest, errors, strict=True)
    return f"Sales materials / 販売素材\n\n{verification}\n\n{text}"


def _build_sales_finalize_report(project_dir: Path) -> str:
    from .sales_finalize import list_sales_finalize_reports

    reports = list_sales_finalize_reports(project_dir)
    if not reports:
        return "Sales finalize / 販売準備一括\n\nNo sales finalize reports found."
    latest = reports[0]
    try:
        text = latest.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Sales finalize / 販売準備一括\n\nCould not read {latest.name}: {exc}"
    return text


def _build_sales_launch_report(project_dir: Path) -> str:
    from .sales_launch import list_sales_launch_checklists

    reports = list_sales_launch_checklists(project_dir)
    if not reports:
        return "Sales launch checklist / 販売直前チェック\n\nNo sales launch checklists found."
    latest = reports[0]
    try:
        text = latest.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Sales launch checklist / 販売直前チェック\n\nCould not read {latest.name}: {exc}"
    return text


def _build_seller_send_checklist_report(project_dir: Path) -> str:
    from .sales_finalize import list_seller_send_checklists

    checklists = list_seller_send_checklists(project_dir)
    if not checklists:
        return "Seller send checklist / 販売者送付前チェックリスト\n\nNo seller send checklists found."
    latest = checklists[0]
    try:
        text = latest.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Seller send checklist / 販売者送付前チェックリスト\n\nCould not read {latest.name}: {exc}"
    return text


def _build_sales_evidence_manifest_report(project_dir: Path) -> str:
    from .sales_finalize import list_sales_evidence_manifests

    manifests = list_sales_evidence_manifests(project_dir)
    if not manifests:
        return "{\n  \"message\": \"No sales evidence manifests found.\"\n}"
    latest = manifests[0]
    try:
        return latest.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as exc:
        return json.dumps({"error": f"Could not read {latest.name}: {exc}"}, ensure_ascii=False, indent=2)


def _build_quality_report(project_dir: Path, *, include_articles: bool = True) -> str:
    from .quality import format_quality_report, run_quality_checks

    return format_quality_report(run_quality_checks(project_dir, include_articles=include_articles))


def _build_maintenance_summary(project_dir: Path) -> str:
    from .acceptance import list_acceptance_reports
    from .backup import inspect_backup, list_backups
    from .commercial import list_commercial_policy_reviews, list_commercial_readiness_reports
    from .commercial_setup import list_commercial_setup_templates
    from .export import list_reports
    from .maintenance import collect_privacy_failed_artifacts
    from .release import list_releases, verify_release_package
    from .sales_finalize import (
        list_buyer_delivery_messages,
        list_buyer_send_readiness_reports,
        list_sales_evidence_manifests,
        list_sales_finalize_reports,
        list_seller_delivery_receipts,
        list_seller_send_checklists,
    )
    from .sales_handoff import list_sales_handoffs, verify_sales_handoff
    from .sales_materials import list_sales_materials, verify_sales_materials
    from .sales_plan import list_sales_plan_reports
    from .sales_launch import list_sales_launch_checklists, list_sales_launch_confirmations
    from .sales_review import list_sales_review_reports
    from .selftest import list_self_test_reports
    from .support import (
        SUPPORT_BUNDLE_FRESHNESS_WARNING_HOURS,
        is_support_bundle_stale,
        list_support_bundles,
        list_support_requests,
        support_bundle_age_hours,
        verify_support_bundle,
    )
    from .improvement_plan import list_improvement_plan_reports
    from .overview import list_overview_reports
    from .publish_queue import list_publish_queue_reports
    from .workflow import list_calendar_exports
    from .workflow_smoke import list_workflow_smoke_reports

    backups = list_backups(project_dir)
    releases = list_releases(project_dir)
    reports = list_reports(project_dir)
    self_test_reports = list_self_test_reports(project_dir)
    acceptance_reports = list_acceptance_reports(project_dir)
    commercial_readiness_reports = list_commercial_readiness_reports(project_dir)
    commercial_policy_reviews = list_commercial_policy_reviews(project_dir)
    commercial_setup_templates = list_commercial_setup_templates(project_dir)
    improvement_plan_reports = list_improvement_plan_reports(project_dir)
    overview_reports = list_overview_reports(project_dir)
    calendar_exports = list_calendar_exports(project_dir)
    publish_queue_reports = list_publish_queue_reports(project_dir)
    workflow_smoke_reports = list_workflow_smoke_reports(project_dir)
    diagnostics = list_diagnostic_reports(project_dir)
    support_requests = list_support_requests(project_dir)
    support_bundles = list_support_bundles(project_dir)
    sales_handoffs = list_sales_handoffs(project_dir)
    sales_materials = list_sales_materials(project_dir)
    sales_plan_reports = list_sales_plan_reports(project_dir)
    sales_launch_checklists = list_sales_launch_checklists(project_dir)
    sales_launch_confirmations = list_sales_launch_confirmations(project_dir)
    sales_review_reports = list_sales_review_reports(project_dir)
    sales_finalize_reports = list_sales_finalize_reports(project_dir)
    seller_send_checklists = list_seller_send_checklists(project_dir)
    buyer_delivery_messages = list_buyer_delivery_messages(project_dir)
    buyer_send_readiness_reports = list_buyer_send_readiness_reports(project_dir)
    seller_delivery_receipts = list_seller_delivery_receipts(project_dir)
    sales_evidence_manifests = list_sales_evidence_manifests(project_dir)
    sales_materials_errors = verify_sales_materials(sales_materials[0], strict=True, project_dir=project_dir) if sales_materials else []
    privacy_failed = collect_privacy_failed_artifacts(project_dir, include_releases=True)
    release_dir = (project_dir / ".auto-note" / "releases").resolve()
    privacy_failed_releases = 0
    for item in privacy_failed:
        try:
            item.path.resolve().relative_to(release_dir)
        except ValueError:
            continue
        privacy_failed_releases += 1
    privacy_failed_non_releases = len(privacy_failed) - privacy_failed_releases
    lines = [
        "Maintenance summary",
        "",
        f"backups: {len(backups)}",
        f"diagnostic_reports: {len(diagnostics)}",
        f"support_requests: {len(support_requests)}",
        f"support_bundles: {len(support_bundles)}",
        f"sales_handoffs: {len(sales_handoffs)}",
        f"sales_materials: {len(sales_materials)}",
        f"sales_plan_reports: {len(sales_plan_reports)}",
        f"sales_launch_checklists: {len(sales_launch_checklists)}",
        f"sales_launch_confirmations: {len(sales_launch_confirmations)}",
        f"sales_review_reports: {len(sales_review_reports)}",
        f"sales_finalize_reports: {len(sales_finalize_reports)}",
        f"seller_send_checklists: {len(seller_send_checklists)}",
        f"buyer_delivery_messages: {len(buyer_delivery_messages)}",
        f"buyer_send_readiness_reports: {len(buyer_send_readiness_reports)}",
        f"seller_delivery_receipts: {len(seller_delivery_receipts)}",
        f"sales_evidence_manifests: {len(sales_evidence_manifests)}",
        f"latest_sales_materials_ready: {'yes' if sales_materials and not sales_materials_errors else 'no'}",
        f"release_packages: {len(releases)}",
        f"csv_reports: {len(reports)}",
        f"self_test_reports: {len(self_test_reports)}",
        f"acceptance_reports: {len(acceptance_reports)}",
        f"commercial_readiness_reports: {len(commercial_readiness_reports)}",
        f"commercial_policy_reviews: {len(commercial_policy_reviews)}",
        f"commercial_setup_templates: {len(commercial_setup_templates)}",
        f"improvement_plan_reports: {len(improvement_plan_reports)}",
        f"overview_reports: {len(overview_reports)}",
        f"calendar_exports: {len(calendar_exports)}",
        f"publish_queue_reports: {len(publish_queue_reports)}",
        f"workflow_smoke_reports: {len(workflow_smoke_reports)}",
        f"privacy_failed_cleanup_candidates: {privacy_failed_non_releases}",
        f"privacy_failed_cleanup_candidates_including_releases: {len(privacy_failed)}",
    ]
    if privacy_failed:
        lines.append("privacy_failed_cleanup_next: auto-note cleanup --project-dir . --privacy-failed --include-releases")
    if backups:
        latest_backup = backups[0]
        lines.append(f"latest_backup: {latest_backup.name}")
        try:
            backup_inspection = inspect_backup(latest_backup)
        except Exception as exc:
            lines.append("latest_backup_verified: no")
            lines.append(f"latest_backup_error: {exc}")
        else:
            lines.append(f"latest_backup_verified: {'yes' if backup_inspection.ok else 'no'}")
            lines.append(f"latest_backup_restorable_files: {len(backup_inspection.restorable_files)}")
            if backup_inspection.unsafe_files:
                lines.append(f"latest_backup_unsafe_files: {len(backup_inspection.unsafe_files)}")
    if releases:
        latest_release = releases[0]
        errors = verify_release_package(latest_release)
        lines.append(f"latest_release: {latest_release.name}")
        lines.append(f"latest_release_verified: {'yes' if not errors else 'no'}")
        if errors:
            lines.append(f"latest_release_errors: {len(errors)}")
    if reports:
        lines.append(f"latest_csv_report: {reports[0].name}")
    if self_test_reports:
        lines.append(f"latest_self_test_report: {self_test_reports[0].name}")
    if acceptance_reports:
        lines.append(f"latest_acceptance_report: {acceptance_reports[0].name}")
    if commercial_readiness_reports:
        lines.append(f"latest_commercial_readiness_report: {commercial_readiness_reports[0].name}")
    if commercial_policy_reviews:
        lines.append(f"latest_commercial_policy_review: {commercial_policy_reviews[0].name}")
    if commercial_setup_templates:
        lines.append(f"latest_commercial_setup_template: {commercial_setup_templates[0].name}")
    if improvement_plan_reports:
        lines.append(f"latest_improvement_plan_report: {improvement_plan_reports[0].name}")
    if overview_reports:
        lines.append(f"latest_overview_report: {overview_reports[0].name}")
    if calendar_exports:
        lines.append(f"latest_calendar_export: {calendar_exports[0].name}")
    if publish_queue_reports:
        lines.append(f"latest_publish_queue_report: {publish_queue_reports[0].name}")
    if workflow_smoke_reports:
        lines.append(f"latest_workflow_smoke_report: {workflow_smoke_reports[0].name}")
    if diagnostics:
        lines.append(f"latest_diagnostic_report: {diagnostics[0].name}")
    if support_requests:
        lines.append(f"latest_support_request: {support_requests[0].name}")
    if support_bundles:
        latest_support_bundle = support_bundles[0]
        support_errors = verify_support_bundle(latest_support_bundle)
        support_age_hours = support_bundle_age_hours(latest_support_bundle)
        support_freshness = "unknown"
        if support_age_hours is not None:
            support_freshness = "stale" if is_support_bundle_stale(latest_support_bundle) else "fresh"
        lines.append(f"latest_support_bundle: {latest_support_bundle.name}")
        lines.append(f"latest_support_bundle_verified: {'yes' if not support_errors else 'no'}")
        lines.append(
            "latest_support_bundle_age_hours: "
            + (f"{support_age_hours:.1f}" if support_age_hours is not None else "unknown")
        )
        lines.append(f"latest_support_bundle_freshness: {support_freshness}")
        lines.append(f"latest_support_bundle_freshness_warning_hours: {SUPPORT_BUNDLE_FRESHNESS_WARNING_HOURS}")
        if support_errors:
            lines.append(f"latest_support_bundle_errors: {len(support_errors)}")
    if sales_handoffs:
        latest_sales_handoff = sales_handoffs[0]
        sales_errors = verify_sales_handoff(latest_sales_handoff)
        lines.append(f"latest_sales_handoff: {latest_sales_handoff.name}")
        lines.append(f"latest_sales_handoff_verified: {'yes' if not sales_errors else 'no'}")
        if sales_errors:
            lines.append(f"latest_sales_handoff_errors: {len(sales_errors)}")
    if sales_plan_reports:
        lines.append(f"latest_sales_plan_report: {sales_plan_reports[0].name}")
    if sales_launch_checklists:
        lines.append(f"latest_sales_launch_checklist: {sales_launch_checklists[0].name}")
    if sales_launch_confirmations:
        lines.append(f"latest_sales_launch_confirmation: {sales_launch_confirmations[0].name}")
    if sales_review_reports:
        lines.append(f"latest_sales_review_report: {sales_review_reports[0].name}")
    if sales_finalize_reports:
        lines.append(f"latest_sales_finalize_report: {sales_finalize_reports[0].name}")
    if seller_send_checklists:
        lines.append(f"latest_seller_send_checklist: {seller_send_checklists[0].name}")
    if buyer_delivery_messages:
        lines.append(f"latest_buyer_delivery_message: {buyer_delivery_messages[0].name}")
    if buyer_send_readiness_reports:
        lines.append(f"latest_buyer_send_readiness_report: {buyer_send_readiness_reports[0].name}")
    if seller_delivery_receipts:
        lines.append(f"latest_seller_delivery_receipt: {seller_delivery_receipts[0].name}")
    if sales_evidence_manifests:
        lines.append(f"latest_sales_evidence_manifest: {sales_evidence_manifests[0].name}")
    return "\n".join(lines)


def _write_text_file(
    archive: zipfile.ZipFile,
    project_dir: Path,
    relative: str,
    *,
    include_private: bool,
) -> None:
    path = project_dir / relative
    if not path.exists() or not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    if not include_private:
        text = mask_text(text, project_dir)
    archive.writestr(relative, text)
