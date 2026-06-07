from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class CleanupItem:
    path: Path
    size_bytes: int
    reason: str


@dataclass(frozen=True)
class CleanupResult:
    items: list[CleanupItem]
    deleted: int
    reclaimed_bytes: int


def collect_cleanup_items(project_dir: Path, *, older_than_days: int = 7) -> list[CleanupItem]:
    return collect_generated_artifacts(project_dir, older_than_days=older_than_days)


def collect_generated_artifacts(
    project_dir: Path,
    *,
    older_than_days: int = 7,
    include_reports: bool = True,
    include_releases: bool = False,
    keep_latest: int = 3,
) -> list[CleanupItem]:
    output_dir = project_dir / ".auto-note"
    if not output_dir.exists():
        return []
    cutoff = datetime.now() - timedelta(days=max(0, older_than_days))
    items: list[CleanupItem] = []
    items.extend(_old_items(_generated_html_files(output_dir), cutoff, reason="generated helper HTML", keep_latest=0))
    if include_reports:
        items.extend(
            _old_items(
                list((output_dir / "diagnostics").glob("*.zip")),
                cutoff,
                reason="diagnostic report ZIP",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "support").glob("support-request-*.md")),
                cutoff,
                reason="support request Markdown",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "support").glob("auto-note-support-bundle-*.zip")),
                cutoff,
                reason="support bundle ZIP",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "sales").glob("auto-note-sales-handoff-*.zip")),
                cutoff,
                reason="sales handoff ZIP",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "sales").glob("auto-note-sales-materials-*.md")),
                cutoff,
                reason="sales materials Markdown",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "sales").glob("commercial-setup-template-*.md")),
                cutoff,
                reason="commercial setup template Markdown",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "sales").glob("commercial-policy-review-*.txt")),
                cutoff,
                reason="commercial policy review",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "sales").glob("sales-plan-*.txt")),
                cutoff,
                reason="sales plan report",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "sales").glob("sales-finalize-*.txt")),
                cutoff,
                reason="sales finalize report",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "sales").glob("seller-send-checklist-*.txt")),
                cutoff,
                reason="seller send checklist",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "sales").glob("buyer-delivery-message-*.txt")),
                cutoff,
                reason="buyer delivery message",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "sales").glob("buyer-send-readiness-*.txt")),
                cutoff,
                reason="buyer send readiness report",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "sales").glob("seller-delivery-receipt-*.txt")),
                cutoff,
                reason="seller delivery receipt",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "sales").glob("sales-evidence-manifest-*.json")),
                cutoff,
                reason="sales evidence manifest",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "reports").glob("*.csv")),
                cutoff,
                reason="article inventory CSV",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "reports").glob("self-test-*.txt")),
                cutoff,
                reason="self-test report",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "reports").glob("acceptance-*.txt")),
                cutoff,
                reason="acceptance report",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "reports").glob("commercial-readiness-*.txt")),
                cutoff,
                reason="commercial readiness report",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "reports").glob("improvement-plan-*.txt")),
                cutoff,
                reason="improvement plan report",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "reports").glob("overview-*.txt")),
                cutoff,
                reason="overview report",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "reports").glob("calendar-*.ics")),
                cutoff,
                reason="calendar export ICS",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "reports").glob("publish-queue-*.txt")),
                cutoff,
                reason="publish queue report",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "reports").glob("workflow-smoke-*.txt")),
                cutoff,
                reason="workflow smoke report",
                keep_latest=keep_latest,
            )
        )
    if include_releases:
        items.extend(
            _old_items(
                list((output_dir / "releases").glob("*.zip")),
                cutoff,
                reason="release package ZIP",
                keep_latest=keep_latest,
            )
        )
    return sorted(items, key=lambda item: item.path.as_posix())


def collect_privacy_failed_artifacts(
    project_dir: Path,
    *,
    include_releases: bool = False,
) -> list[CleanupItem]:
    from .privacy import run_privacy_audit

    root = (project_dir / ".auto-note").resolve()
    report = run_privacy_audit(project_dir, all_artifacts=True)
    items: list[CleanupItem] = []
    seen: set[Path] = set()
    for audit_item in report.items:
        if audit_item.status != "fail" or audit_item.path is None:
            continue
        path = audit_item.path.resolve()
        if path in seen or not path.exists() or not path.is_file():
            continue
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if _is_release_artifact(project_dir, path) and not include_releases:
            continue
        seen.add(path)
        items.append(
            CleanupItem(
                path=path,
                size_bytes=path.stat().st_size,
                reason=f"privacy audit NG: {audit_item.name}",
            )
        )
    return sorted(items, key=lambda item: item.path.as_posix())


def cleanup_generated_files(
    project_dir: Path,
    *,
    older_than_days: int = 7,
    dry_run: bool = True,
    include_reports: bool = True,
    include_releases: bool = False,
    keep_latest: int = 3,
    privacy_failed: bool = False,
) -> CleanupResult:
    if privacy_failed:
        items = collect_privacy_failed_artifacts(project_dir, include_releases=include_releases)
    else:
        items = collect_generated_artifacts(
            project_dir,
            older_than_days=older_than_days,
            include_reports=include_reports,
            include_releases=include_releases,
            keep_latest=keep_latest,
        )
    deleted = 0
    reclaimed = 0
    if not dry_run:
        for item in items:
            try:
                item.path.unlink()
            except FileNotFoundError:
                continue
            deleted += 1
            reclaimed += item.size_bytes
    return CleanupResult(items=items, deleted=deleted, reclaimed_bytes=reclaimed)


def format_cleanup_report(result: CleanupResult, *, dry_run: bool = True) -> str:
    action = "削除候補" if dry_run else "削除済み"
    lines = [f"生成物整理: {action} {len(result.items)}件"]
    if not dry_run:
        lines.append(f"解放容量: {_format_bytes(result.reclaimed_bytes)}")
    if not result.items:
        lines.append("対象ファイルはありません。")
        return "\n".join(lines)
    lines.append("")
    for item in result.items:
        lines.append(f"- {item.path} ({_format_bytes(item.size_bytes)}): {item.reason}")
    return "\n".join(lines)


def _generated_html_files(output_dir: Path) -> list[Path]:
    files = list(output_dir.glob("*.html"))
    helper_dir = output_dir / "helpers"
    if helper_dir.exists():
        files.extend(helper_dir.glob("*.html"))
    quickstart_dir = output_dir / "quickstart"
    if quickstart_dir.exists():
        files.extend(quickstart_dir.glob("*.html"))
    return files


def _old_items(paths: list[Path], cutoff: datetime, *, reason: str, keep_latest: int) -> list[CleanupItem]:
    files = [path for path in paths if path.is_file()]
    keep = {
        path.resolve()
        for path in sorted(files, key=lambda item: item.stat().st_mtime, reverse=True)[: max(0, keep_latest)]
    }
    items: list[CleanupItem] = []
    for path in files:
        if path.resolve() in keep:
            continue
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        if modified <= cutoff:
            items.append(CleanupItem(path=path, size_bytes=path.stat().st_size, reason=reason))
    return items


def _is_release_artifact(project_dir: Path, path: Path) -> bool:
    release_dir = (project_dir / ".auto-note" / "releases").resolve()
    try:
        path.resolve().relative_to(release_dir)
        return True
    except ValueError:
        return False


def _format_bytes(value: int) -> str:
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value} B"
