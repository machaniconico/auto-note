from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


CLEANUP_REPORT_ITEM_LIMIT = 40


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
                list((output_dir / "sales").glob("sales-review-*.txt")),
                cutoff,
                reason="sales final review report",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "sales").glob("sales-launch-checklist-*.txt")),
                cutoff,
                reason="sales launch checklist",
                keep_latest=keep_latest,
            )
        )
        items.extend(
            _old_items(
                list((output_dir / "sales").glob("sales-launch-confirmation-*.txt")),
                cutoff,
                reason="sales launch confirmation",
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
    return sorted(items, key=_privacy_failed_cleanup_sort_key)


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


def format_cleanup_report(
    result: CleanupResult,
    *,
    dry_run: bool = True,
    max_items: int = CLEANUP_REPORT_ITEM_LIMIT,
    privacy_failed: bool = False,
    include_releases: bool = False,
    project_dir: Path | None = None,
    apply_command: str = "",
) -> str:
    action = "削除候補" if dry_run else "削除済み"
    total_bytes = sum(item.size_bytes for item in result.items)
    lines = [f"生成物整理: {action} {len(result.items)}件"]
    if privacy_failed:
        lines.append("対象: privacy-audit --all でNGになった生成物")
        lines.append("表示順: 販売/送付に近いNGと新しい生成物を優先表示しています。")
    if include_releases:
        lines.append("配布ZIP: 対象に含めています。")
    elif privacy_failed:
        lines.append("配布ZIP: 除外しています。含める場合は --include-releases を付けてください。")
    if dry_run:
        lines.append(f"見込み解放容量: {_format_bytes(total_bytes)}")
    else:
        lines.append(f"解放容量: {_format_bytes(result.reclaimed_bytes)}")
    if not result.items:
        lines.append("対象ファイルはありません。")
        return "\n".join(lines)
    lines.append("")
    lines.append("種類別:")
    for reason, count, size_bytes in _cleanup_reason_summary(result.items):
        lines.append(f"- {reason}: {count}件 / {_format_bytes(size_bytes)}")
    lines.append("")
    if dry_run:
        lines.append("削除はまだ実行していません。内容を確認してから --apply または GUIの整理実行を使ってください。")
        if apply_command:
            lines.append(f"実行コマンド例: {apply_command}")
        if privacy_failed:
            lines.extend(_privacy_cleanup_rc_followup(project_dir))
    else:
        lines.append("削除したファイル一覧:")
        if privacy_failed:
            lines.extend(_privacy_cleanup_rc_followup(project_dir))
    lines.append("")
    visible_items = result.items[: max(0, max_items)]
    for item in visible_items:
        lines.append(f"- {_format_cleanup_path(item.path, project_dir)} ({_format_bytes(item.size_bytes)}): {item.reason}")
    hidden = len(result.items) - len(visible_items)
    if hidden > 0:
        lines.append(f"- ほか {hidden}件。種類別サマリーで全体を確認できます。")
    return "\n".join(lines)


def _privacy_cleanup_rc_followup(project_dir: Path | None) -> list[str]:
    project_arg = _cleanup_project_dir_arg(project_dir)
    return [
        f"RC再判定: auto-note commercial-readiness --project-dir {project_arg}",
        f"再生成: auto-note sales-handoff --project-dir {project_arg}",
    ]


def _cleanup_project_dir_arg(project_dir: Path | None) -> str:
    if project_dir is None:
        return "."
    try:
        if project_dir.resolve() == Path.cwd().resolve():
            return "."
    except OSError:
        return "<project-dir>"
    return "<project-dir>"


def _format_cleanup_path(path: Path, project_dir: Path | None) -> str:
    if project_dir is not None:
        try:
            return str(path.resolve().relative_to(project_dir.resolve()))
        except ValueError:
            pass
    return str(path)


def format_cleanup_confirmation(
    result: CleanupResult,
    *,
    privacy_failed: bool = False,
    max_breakdown_items: int = 5,
) -> str:
    target = "プライバシー監査NG生成物" if privacy_failed else "古い生成物"
    total_bytes = sum(item.size_bytes for item in result.items)
    lines = [
        f"{len(result.items)}件の{target}を削除します。",
        f"見込み解放容量: {_format_bytes(total_bytes)}",
        "",
        "種類別:",
    ]
    summary = _cleanup_reason_summary(result.items)
    visible_summary = summary[: max(0, max_breakdown_items)]
    for reason, count, size_bytes in visible_summary:
        lines.append(f"- {reason}: {count}件 / {_format_bytes(size_bytes)}")
    hidden = len(summary) - len(visible_summary)
    if hidden > 0:
        lines.append(f"- ほか {hidden}種類")
    lines.extend(
        [
            "",
            "対象は .auto-note 内の生成物だけです。",
        ]
    )
    if _cleanup_includes_release_items(result.items):
        lines.append("配布ZIPも削除対象に含まれます。必要なら削除前に最新ZIPや販売証跡を作り直してください。")
    lines.append("この操作は元に戻せません。続行しますか？")
    return "\n".join(lines)


def _cleanup_reason_summary(items: list[CleanupItem]) -> list[tuple[str, int, int]]:
    summary: dict[str, tuple[int, int]] = {}
    for item in items:
        reason = _cleanup_summary_reason(item.reason)
        count, size_bytes = summary.get(reason, (0, 0))
        summary[reason] = (count + 1, size_bytes + item.size_bytes)
    return [
        (reason, count, size_bytes)
        for reason, (count, size_bytes) in sorted(
            summary.items(),
            key=lambda entry: (-entry[1][0], entry[0]),
        )
    ]


def _cleanup_summary_reason(reason: str) -> str:
    prefix, separator, detail = reason.partition(": ")
    if separator and prefix == "privacy audit NG":
        artifact_name, _separator, _detail = detail.partition(": ")
        return f"{prefix}: {artifact_name}"
    return reason


def _cleanup_includes_release_items(items: list[CleanupItem]) -> bool:
    for item in items:
        if "release package" in item.reason.lower():
            return True
        if "releases" in {part.lower() for part in item.path.parts}:
            return True
    return False


def _privacy_failed_cleanup_sort_key(item: CleanupItem) -> tuple[int, float, str]:
    reason = item.reason.lower()
    priority = 50
    if "sales handoff privacy" in reason:
        priority = 0
    elif "buyer delivery zip privacy" in reason:
        priority = 1
    elif any(
        marker in reason
        for marker in (
            "sales plan",
            "sales finalize",
            "sales launch",
            "sales listing",
            "sales materials",
            "sales evidence",
        )
    ):
        priority = 2
    elif "support bundle" in reason or "support request" in reason:
        priority = 3
    elif "release package privacy" in reason:
        priority = 4
    elif "diagnostic report privacy" in reason:
        priority = 5
    try:
        modified = -item.path.stat().st_mtime
    except OSError:
        modified = 0.0
    return priority, modified, item.path.as_posix()


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


def format_bytes(value: int) -> str:
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value} B"


def _format_bytes(value: int) -> str:
    return format_bytes(value)
