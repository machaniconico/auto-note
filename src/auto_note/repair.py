from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .maintenance import cleanup_generated_files
from .readiness import run_readiness
from .setup_check import run_setup_check


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


def has_repair_blockers(report: RepairReport, *, strict: bool = False) -> bool:
    if any(item.status == "fail" for item in report.items):
        return True
    return strict and any(item.status == "warn" for item in report.items)


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
