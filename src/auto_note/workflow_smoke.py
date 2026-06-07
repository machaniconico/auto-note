from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tempfile

from .action_plan import build_action_plan
from .article import load_article
from .backup import create_backup, verify_backup
from .inspect import inspect_article
from .paths import unique_path
from .publish_ready import run_publish_ready
from .quickstart import run_quickstart
from .review import review_article
from .scaffold import create_practice_article
from .setup_check import run_setup_check


@dataclass(frozen=True)
class WorkflowSmokeItem:
    name: str
    status: str
    detail: str
    action: str = ""


@dataclass(frozen=True)
class WorkflowSmokeReport:
    status: str
    generated_at: datetime
    project_dir: Path
    temp_project_dir: Path
    kept: bool
    items: list[WorkflowSmokeItem]

    @property
    def ok(self) -> bool:
        return self.status == "pass"

    @property
    def has_warnings(self) -> bool:
        return any(item.status == "warn" for item in self.items)


def run_workflow_smoke(
    project_dir: Path,
    *,
    gui_smoke: bool = False,
    keep: bool = False,
) -> WorkflowSmokeReport:
    project_dir = project_dir.resolve()
    generated_at = datetime.now()
    temp_root: tempfile.TemporaryDirectory[str] | None = None
    if keep:
        temp_project = unique_path(
            project_dir
            / ".auto-note"
            / "workflow-smoke"
            / f"workflow-smoke-{generated_at:%Y%m%d-%H%M%S}"
        )
        temp_project.mkdir(parents=True, exist_ok=True)
    else:
        temp_root = tempfile.TemporaryDirectory(prefix="auto-note-workflow-")
        temp_project = Path(temp_root.name)

    items: list[WorkflowSmokeItem] = []
    try:
        _run_workflow_items(project_dir, temp_project, items, gui_smoke=gui_smoke)
        return WorkflowSmokeReport(
            status=_overall_status(items),
            generated_at=generated_at,
            project_dir=project_dir,
            temp_project_dir=temp_project,
            kept=keep,
            items=items,
        )
    finally:
        if temp_root is not None:
            temp_root.cleanup()


def write_workflow_smoke_report(
    project_dir: Path,
    *,
    gui_smoke: bool = False,
    keep: bool = False,
    report: WorkflowSmokeReport | None = None,
) -> Path:
    project_dir = project_dir.resolve()
    report = report or run_workflow_smoke(project_dir, gui_smoke=gui_smoke, keep=keep)
    reports_dir = project_dir / ".auto-note" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(reports_dir / f"workflow-smoke-{report.generated_at:%Y%m%d-%H%M%S}.txt")
    path.write_text(format_workflow_smoke_report(report) + "\n", encoding="utf-8")
    return path


def list_workflow_smoke_reports(project_dir: Path) -> list[Path]:
    reports_dir = project_dir / ".auto-note" / "reports"
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("workflow-smoke-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def format_workflow_smoke_report(report: WorkflowSmokeReport, *, include_private: bool = True) -> str:
    counts = {
        "pass": sum(1 for item in report.items if item.status == "pass"),
        "info": sum(1 for item in report.items if item.status == "info"),
        "warn": sum(1 for item in report.items if item.status == "warn"),
        "fail": sum(1 for item in report.items if item.status == "fail"),
    }
    verdict = {
        "pass": "READY",
        "warn": "CHECK",
        "fail": "BLOCKED",
    }.get(report.status, report.status.upper())
    temp_label = str(report.temp_project_dir) if include_private and report.kept else "<temporary project>"
    lines = [
        "Workflow smoke / 簡易E2Eチェック",
        f"Generated: {report.generated_at:%Y-%m-%d %H:%M:%S}",
        f"Verdict: {verdict}",
        f"Temp project: {temp_label}",
        f"Items: {counts['pass']} OK, {counts['info']} INFO, {counts['warn']} WARN, {counts['fail']} NG",
        "",
    ]
    next_actions: list[str] = []
    for item in report.items:
        label = {"pass": "OK", "info": "INFO", "warn": "WARN", "fail": "NG"}.get(
            item.status,
            item.status.upper(),
        )
        lines.append(f"[{label}] {item.name}: {item.detail}")
        if item.action:
            lines.append(f"  next: {item.action}")
            next_actions.append(f"- {item.name}: {item.action}")
    if next_actions:
        lines.extend(["", "Next actions"])
        lines.extend(next_actions)
    return "\n".join(lines)


def has_workflow_smoke_blockers(report: WorkflowSmokeReport, *, strict: bool = False) -> bool:
    if any(item.status == "fail" for item in report.items):
        return True
    return strict and any(item.status == "warn" for item in report.items)


def _run_workflow_items(
    source_project: Path,
    temp_project: Path,
    items: list[WorkflowSmokeItem],
    *,
    gui_smoke: bool,
) -> None:
    temp_project.mkdir(parents=True, exist_ok=True)
    _copy_smoke_launchers(source_project, temp_project)
    setup = run_setup_check(temp_project, create=True)
    critical_setup = {"project folder", "articles folder", "settings file", "settings readable", "ideas readable"}
    setup_failures = [item for item in setup if not item.ok and item.name in critical_setup]
    setup_warnings = [item for item in setup if not item.ok and item.name not in critical_setup]
    if setup_failures:
        items.append(
            WorkflowSmokeItem(
                "setup",
                "fail",
                f"{len(setup_failures)} critical setup failure(s)",
                "`auto-note setup --project-dir . --create` を確認してください。",
            )
        )
        return
    status = "warn" if setup_warnings else "pass"
    detail = f"critical setup OK, {len(setup_warnings)} optional warning(s)"
    items.append(WorkflowSmokeItem("setup", status, detail))

    article_path = create_practice_article(articles_dir=temp_project / "articles")
    article = load_article(article_path)
    items.append(WorkflowSmokeItem("practice article", "pass", f"created {article_path.name}"))

    inspection = inspect_article(article, append_tags=True)
    if not inspection.ok:
        errors = sum(1 for issue in inspection.issues if issue.level == "error")
        warnings = sum(1 for issue in inspection.issues if issue.level == "warn")
        items.append(
            WorkflowSmokeItem(
                "article check",
                "fail",
                f"{errors} error(s), {warnings} warning(s)",
                "練習記事テンプレートと公開前チェックの条件を確認してください。",
            )
        )
    else:
        warnings = sum(1 for issue in inspection.issues if issue.level == "warn")
        status = "warn" if warnings else "pass"
        detail = f"{inspection.stats.body_chars} chars, {warnings} warning(s)"
        items.append(WorkflowSmokeItem("article check", status, detail))

    review = review_article(article, append_tags=True)
    if review.needs_fix:
        items.append(
            WorkflowSmokeItem(
                "article review",
                "fail",
                f"score {review.score}/100, fix item(s) remain",
                "練習記事テンプレートのレビュー項目を確認してください。",
            )
        )
    elif not review.ready:
        items.append(WorkflowSmokeItem("article review", "warn", f"score {review.score}/100"))
    else:
        items.append(WorkflowSmokeItem("article review", "pass", f"score {review.score}/100"))

    publish_ready = run_publish_ready(
        article_path,
        append_tags=True,
        smoke_helper=True,
        output_dir=temp_project / ".auto-note" / "publish-ready",
        mark_ready=True,
    )
    publish_ready_failures = sum(1 for item in publish_ready.items if item.status == "fail")
    if (
        publish_ready_failures == 0
        and publish_ready.helper_path
        and publish_ready.helper_path.exists()
        and publish_ready.marked_ready
    ):
        items.append(
            WorkflowSmokeItem(
                "publish ready",
                "pass",
                f"helper generated, marked_ready={publish_ready.marked_ready}",
            )
        )
    else:
        items.append(
            WorkflowSmokeItem(
                "publish ready",
                "fail",
                publish_ready.status,
                "`auto-note publish-ready <file> --smoke-helper --mark-ready` を確認してください。",
            )
        )

    quickstart = run_quickstart(temp_project, smoke_helper=True)
    if quickstart.ok:
        items.append(WorkflowSmokeItem("quickstart", "pass", f"{quickstart.score}/100"))
    elif quickstart.has_warnings:
        items.append(WorkflowSmokeItem("quickstart", "warn", f"{quickstart.score}/100"))
    else:
        items.append(
            WorkflowSmokeItem(
                "quickstart",
                "fail",
                f"{quickstart.score}/100",
                "`auto-note quickstart --project-dir . --smoke-helper` を確認してください。",
            )
        )

    backup = create_backup(temp_project)
    backup_errors = verify_backup(backup)
    if backup_errors:
        items.append(
            WorkflowSmokeItem(
                "backup",
                "fail",
                f"{len(backup_errors)} verification error(s)",
                "`auto-note backup --inspect <zip>` を確認してください。",
            )
        )
    else:
        items.append(WorkflowSmokeItem("backup", "pass", backup.name))

    action_plan = build_action_plan(temp_project, limit=3)
    items.append(WorkflowSmokeItem("action plan", "pass", f"{len(action_plan.steps)} prioritized action(s) generated"))

    if gui_smoke:
        try:
            from .gui import smoke_gui

            detail = smoke_gui(temp_project)
        except Exception as exc:
            items.append(
                WorkflowSmokeItem(
                    "gui smoke",
                    "fail",
                    str(exc),
                    "`auto-note gui --project-dir . --smoke` を確認してください。",
                )
            )
        else:
            items.append(WorkflowSmokeItem("gui smoke", "pass", detail))


def _copy_smoke_launchers(source_project: Path, temp_project: Path) -> None:
    for name in ("auto-note-gui.bat", "auto-note.lnk", "auto-note GUI.lnk"):
        source = source_project / name
        if source.exists() and source.is_file():
            destination = temp_project / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())


def _overall_status(items: list[WorkflowSmokeItem]) -> str:
    if any(item.status == "fail" for item in items):
        return "fail"
    if any(item.status == "warn" for item in items):
        return "warn"
    return "pass"
