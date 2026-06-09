from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .maintenance import cleanup_generated_files
from .paths import unique_path
from .readiness import run_readiness
from .setup_check import run_setup_check
from .support import (
    create_support_bundle,
    format_support_bundle_verification,
    verify_support_bundle,
)
from .troubleshoot import TroubleshootReport, format_troubleshoot_report, run_troubleshoot


@dataclass(frozen=True)
class RepairItem:
    name: str
    status: str
    detail: str
    action: str = ""


@dataclass(frozen=True)
class RepairReport:
    project_dir: Path
    applied: bool
    readiness_score: int
    items: list[RepairItem]


@dataclass(frozen=True)
class RecoveryKitReport:
    project_dir: Path
    generated_at: datetime
    before: TroubleshootReport
    repair: RepairReport
    after: TroubleshootReport
    support_bundle: Path | None = None
    support_bundle_errors: list[str] | None = None
    support_bundle_error: str = ""

    @property
    def status(self) -> str:
        if self.support_bundle_error or (self.support_bundle_errors or []) or self.after.status == "fail":
            return "fail"
        if self.before.status != "pass" or self.after.status != "pass":
            return "warn"
        if any(item.status == "warn" for item in self.repair.items):
            return "warn"
        return "pass"


def run_repair(
    project_dir: Path,
    *,
    apply: bool = False,
    cleanup_privacy: bool = False,
    cleanup_old: bool = False,
    include_releases: bool = False,
    days: int = 7,
    keep_latest: int = 3,
) -> RepairReport:
    project_dir = project_dir.resolve()
    items: list[RepairItem] = []

    before_setup = run_setup_check(project_dir, create=False)
    before_warnings = [item for item in before_setup if not item.ok]
    if apply:
        after_setup = run_setup_check(project_dir, create=True)
        after_warnings = [item for item in after_setup if not item.ok]
        repaired = max(0, len(before_warnings) - len(after_warnings))
        status = "pass" if not after_warnings else "warn"
        detail = f"applied basic setup repair, {repaired} repaired, {len(after_warnings)} warning(s) remain"
        action = "残ったWARNはセットアップ確認で詳細を確認してください。" if after_warnings else ""
    else:
        status = "info" if before_warnings else "pass"
        detail = f"{len(before_warnings)} setup warning(s); basic folders/settings/ideas can be refreshed"
        action = "実行する場合は `auto-note repair --project-dir . --apply` を使います。"
    items.append(RepairItem("basic setup", status, detail, action))

    privacy_result = cleanup_generated_files(
        project_dir,
        dry_run=not (apply and cleanup_privacy),
        include_releases=include_releases,
        privacy_failed=True,
    )
    if cleanup_privacy:
        if apply:
            detail = f"deleted {privacy_result.deleted} privacy-failed artifact(s)"
            status = "pass"
            action = ""
        else:
            detail = _cleanup_detail(
                privacy_result,
                project_dir,
                label="privacy-failed cleanup candidate(s)",
                include_releases=include_releases,
            )
            status = "warn" if privacy_result.items else "pass"
            action = (
                f"削除する場合は `{_repair_cleanup_command('--cleanup-privacy', include_releases)}` を使います。"
                if privacy_result.items
                else ""
            )
    else:
        detail = _cleanup_detail(
            privacy_result,
            project_dir,
            label="privacy-failed cleanup candidate(s)",
            include_releases=include_releases,
        )
        status = "info" if privacy_result.items else "pass"
        action = (
            f"`{_repair_cleanup_command('--cleanup-privacy', include_releases, apply=False)}` で候補を確認できます。"
            if privacy_result.items
            else ""
        )
    items.append(RepairItem("privacy cleanup", status, detail, action))

    if cleanup_old:
        old_result = cleanup_generated_files(
            project_dir,
            older_than_days=days,
            dry_run=not apply,
            include_releases=include_releases,
            keep_latest=keep_latest,
        )
        if apply:
            detail = f"deleted {old_result.deleted} old generated artifact(s)"
            status = "pass"
            action = ""
        else:
            detail = _cleanup_detail(
                old_result,
                project_dir,
                label="old generated cleanup candidate(s)",
                include_releases=include_releases,
            )
            status = "info" if old_result.items else "pass"
            action = (
                f"削除する場合は `{_repair_cleanup_command('--cleanup-old', include_releases)}` を使います。"
                if old_result.items
                else ""
            )
        items.append(RepairItem("old generated cleanup", status, detail, action))

    readiness = run_readiness(project_dir)
    return RepairReport(
        project_dir=project_dir,
        applied=apply,
        readiness_score=readiness.score,
        items=items,
    )


def run_recovery_kit(
    project_dir: Path,
    *,
    create_bundle_on_issue: bool = True,
) -> RecoveryKitReport:
    project_dir = project_dir.resolve()
    generated_at = datetime.now()
    before = run_troubleshoot(project_dir)
    repair = run_repair(project_dir, apply=True)
    after = run_troubleshoot(project_dir)
    support_bundle: Path | None = None
    support_bundle_errors: list[str] | None = None
    support_bundle_error = ""

    if create_bundle_on_issue and after.status != "pass":
        try:
            support_bundle = create_support_bundle(project_dir)
            support_bundle_errors = verify_support_bundle(support_bundle)
        except Exception as exc:  # pragma: no cover - surfaced in report for GUI support
            support_bundle_error = str(exc)

    return RecoveryKitReport(
        project_dir=project_dir,
        generated_at=generated_at,
        before=before,
        repair=repair,
        after=after,
        support_bundle=support_bundle,
        support_bundle_errors=support_bundle_errors,
        support_bundle_error=support_bundle_error,
    )


def write_recovery_kit_report(
    project_dir: Path,
    *,
    report: RecoveryKitReport | None = None,
    create_bundle_on_issue: bool = True,
) -> Path:
    project_dir = project_dir.resolve()
    report = report or run_recovery_kit(project_dir, create_bundle_on_issue=create_bundle_on_issue)
    reports_dir = project_dir / ".auto-note" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(reports_dir / f"recovery-kit-{report.generated_at:%Y%m%d-%H%M%S}.txt")
    path.write_text(format_recovery_kit_report(report) + "\n", encoding="utf-8")
    return path


def list_recovery_kit_reports(project_dir: Path) -> list[Path]:
    reports_dir = project_dir / ".auto-note" / "reports"
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("recovery-kit-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def format_repair_report(report: RepairReport) -> str:
    mode = "APPLY" if report.applied else "PREVIEW"
    lines = [
        "Repair report / 自動修復",
        f"Mode: {mode}",
        f"Readiness: {report.readiness_score}/100",
        "",
    ]
    next_actions: list[str] = []
    for item in report.items:
        label = {"pass": "OK", "info": "INFO", "warn": "WARN", "fail": "NG"}.get(item.status, item.status.upper())
        lines.append(f"[{label}] {item.name}: {item.detail}")
        if item.action:
            lines.append(f"  next: {item.action}")
            next_actions.append(f"- {item.name}: {item.action}")
    if next_actions:
        lines.extend(["", "Next actions"])
        lines.extend(next_actions)
    return "\n".join(lines)


def format_recovery_kit_report(report: RecoveryKitReport) -> str:
    label = {"pass": "OK", "warn": "CHECK", "fail": "BLOCKED"}[report.status]
    lines = [
        "Recovery kit / 復旧セット",
        f"Verdict: {label}",
        f"Before: {_troubleshoot_label(report.before.status)}",
        f"After: {_troubleshoot_label(report.after.status)}",
        "Flow: safe setup repair -> troubleshoot -> support bundle when needed",
        "",
        "Safe repair result",
        _indent(format_repair_report(report.repair)),
        "",
        "Troubleshooting after repair",
        _indent(format_troubleshoot_report(report.after)),
    ]
    if report.support_bundle is not None:
        errors = report.support_bundle_errors or []
        lines.extend(
            [
                "",
                f"Support bundle: {_report_path(report.project_dir, report.support_bundle)}",
                _indent(
                    _mask_project_paths(
                        format_support_bundle_verification(report.support_bundle, errors),
                        report.project_dir,
                    )
                ),
            ]
        )
    elif report.support_bundle_error:
        lines.extend(
            [
                "",
                "Support bundle: failed to create "
                f"({_mask_project_paths(report.support_bundle_error, report.project_dir)})",
            ]
        )
    else:
        lines.extend(["", "Support bundle: not needed"])
    return "\n".join(lines)


def has_repair_blockers(report: RepairReport, *, strict: bool = False) -> bool:
    if any(item.status == "fail" for item in report.items):
        return True
    return strict and any(item.status == "warn" for item in report.items)


def has_recovery_kit_blockers(report: RecoveryKitReport, *, strict: bool = False) -> bool:
    if report.status == "fail":
        return True
    return strict and report.status == "warn"


def _cleanup_detail(result, project_dir: Path, *, label: str, include_releases: bool) -> str:
    count = len(result.items)
    total_size = sum(item.size_bytes for item in result.items)
    if not result.items:
        return f"0 {label}"
    categories = _cleanup_categories(project_dir, result.items)
    category_text = ", ".join(f"{name} {amount}" for name, amount in categories.items())
    release_note = "" if include_releases else "; release packages excluded"
    return f"{count} {label}, {_format_bytes(total_size)}, {category_text}{release_note}"


def _cleanup_categories(project_dir: Path, items) -> dict[str, int]:
    root = (project_dir / ".auto-note").resolve()
    labels = {
        "diagnostics": "diagnostic",
        "support": "support",
        "reports": "report",
        "releases": "release",
        "helpers": "helper",
        "quickstart": "quickstart",
    }
    counts: dict[str, int] = {}
    for item in items:
        label = "other"
        try:
            relative = item.path.resolve().relative_to(root)
        except ValueError:
            relative = item.path
        if relative.parts:
            label = labels.get(relative.parts[0], relative.parts[0])
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: pair[0]))


def _repair_cleanup_command(option: str, include_releases: bool, *, apply: bool = True) -> str:
    parts = ["auto-note", "repair", "--project-dir", ".", option]
    if include_releases:
        parts.append("--include-releases")
    if apply:
        parts.append("--apply")
    return " ".join(parts)


def _format_bytes(value: int) -> str:
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value} B"


def _troubleshoot_label(status: str) -> str:
    return {"pass": "OK", "warn": "CHECK", "fail": "BLOCKED"}.get(status, status.upper())


def _indent(text: str) -> str:
    return "\n".join(f"  {line}" if line else "" for line in text.splitlines())


def _report_path(project_dir: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_dir.resolve()))
    except ValueError:
        return path.name


def _mask_project_paths(text: str, project_dir: Path) -> str:
    resolved = project_dir.resolve()
    values = (str(resolved), resolved.as_posix())
    masked = text
    for value in sorted(values, key=len, reverse=True):
        if value:
            masked = masked.replace(value, "<PROJECT_DIR>")
    return masked
