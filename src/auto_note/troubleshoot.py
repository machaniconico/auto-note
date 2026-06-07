from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .gui_errors import gui_error_log_path
from .maintenance import collect_privacy_failed_artifacts
from .privacy import has_privacy_audit_blockers, run_privacy_audit
from .release import list_releases, verify_release_package
from .setup_check import run_setup_check


@dataclass(frozen=True)
class TroubleshootItem:
    name: str
    status: str
    detail: str
    action: str = ""


@dataclass(frozen=True)
class TroubleshootReport:
    project_dir: Path
    items: list[TroubleshootItem]

    @property
    def status(self) -> str:
        if any(item.status == "fail" for item in self.items):
            return "fail"
        if any(item.status == "warn" for item in self.items):
            return "warn"
        return "pass"


def run_troubleshoot(
    project_dir: Path,
    *,
    include_releases: bool = False,
    include_sales_handoffs: bool = True,
) -> TroubleshootReport:
    project_dir = project_dir.resolve()
    items = [
        _setup_item(project_dir),
        _gui_log_item(project_dir),
        _note_login_item(),
        _privacy_audit_item(project_dir, include_sales_handoffs=include_sales_handoffs),
        _privacy_cleanup_item(project_dir, include_releases=include_releases),
        _release_item(project_dir),
    ]
    return TroubleshootReport(project_dir=project_dir, items=items)


def format_troubleshoot_report(report: TroubleshootReport) -> str:
    counts = {
        "pass": sum(1 for item in report.items if item.status == "pass"),
        "info": sum(1 for item in report.items if item.status == "info"),
        "warn": sum(1 for item in report.items if item.status == "warn"),
        "fail": sum(1 for item in report.items if item.status == "fail"),
    }
    verdict = {"pass": "OK", "warn": "CHECK", "fail": "BLOCKED"}[report.status]
    lines = [
        "Troubleshooting report / トラブル診断",
        f"Verdict: {verdict}",
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


def has_troubleshoot_blockers(report: TroubleshootReport, *, strict: bool = False) -> bool:
    if report.status == "fail":
        return True
    return strict and report.status == "warn"


def _setup_item(project_dir: Path) -> TroubleshootItem:
    checks = run_setup_check(project_dir, create=False)
    warnings = [item for item in checks if not item.ok]
    if not warnings:
        return TroubleshootItem("setup", "pass", "basic folders, settings, and ideas storage look usable")
    names = ", ".join(item.name for item in warnings[:5])
    if len(warnings) > 5:
        names += ", ..."
    return TroubleshootItem(
        "setup",
        "warn",
        f"{len(warnings)} setup warning(s): {names}",
        "GUI の 自動修復、または `auto-note repair --project-dir . --apply` を実行してください。",
    )


def _gui_log_item(project_dir: Path) -> TroubleshootItem:
    path = gui_error_log_path(project_dir)
    if not path.exists():
        return TroubleshootItem("GUI log", "pass", "no GUI error log found")
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return TroubleshootItem(
            "GUI log",
            "warn",
            f"GUI error log exists but could not be read: {exc}",
            "`auto-note gui --project-dir . --smoke` で起動確認し、必要なら問い合わせ一式を作成してください。",
        )

    markers = _error_markers(text)
    detail = f"{path.name}, {_format_bytes(path.stat().st_size)}"
    tail = _last_non_empty_line(text)
    if tail:
        detail += f", last: {_sanitize(tail, project_dir)}"
    if markers:
        return TroubleshootItem(
            "GUI log",
            "warn",
            f"{detail}, marker(s): {', '.join(markers)}",
            "`auto-note gui --project-dir . --smoke` と `auto-note support --project-dir . --bundle` を使って状況を確認してください。",
        )
    return TroubleshootItem("GUI log", "info", f"{detail}, no common crash markers found")


def _note_login_item() -> TroubleshootItem:
    return TroubleshootItem(
        "note login",
        "info",
        "安全ではない可能性があるログイン画面で止まる場合は、普段使いのブラウザでnote.comにログインして投稿ヘルパーへ貼り付ける運用が安全です",
        "GUI の noteログイン/投稿ヘルパー、または `auto-note login --default-browser` を使ってください。",
    )


def _privacy_audit_item(project_dir: Path, *, include_sales_handoffs: bool = True) -> TroubleshootItem:
    report = run_privacy_audit(project_dir, include_sales_handoffs=include_sales_handoffs)
    counts = {
        "pass": sum(1 for item in report.items if item.status == "pass"),
        "info": sum(1 for item in report.items if item.status == "info"),
        "warn": sum(1 for item in report.items if item.status == "warn"),
        "fail": sum(1 for item in report.items if item.status == "fail"),
    }
    detail = f"latest artifacts: {counts['pass']} OK, {counts['info']} INFO, {counts['warn']} WARN, {counts['fail']} NG"
    if has_privacy_audit_blockers(report):
        return TroubleshootItem(
            "privacy audit",
            "fail",
            detail,
            "`auto-note privacy-audit --project-dir .` を確認し、NG生成物は `auto-note repair --project-dir . --cleanup-privacy` で候補確認してください。",
        )
    return TroubleshootItem("privacy audit", "pass" if report.status == "pass" else "warn", detail)


def _privacy_cleanup_item(project_dir: Path, *, include_releases: bool) -> TroubleshootItem:
    items = collect_privacy_failed_artifacts(project_dir, include_releases=include_releases)
    if not items:
        release_note = "" if include_releases else "; release packages excluded"
        return TroubleshootItem("privacy cleanup candidates", "pass", f"0 candidate(s){release_note}")
    total_size = sum(item.size_bytes for item in items)
    categories = _category_counts(project_dir, items)
    category_text = ", ".join(f"{name} {amount}" for name, amount in categories.items())
    release_note = "" if include_releases else "; release packages excluded"
    command = "auto-note repair --project-dir . --cleanup-privacy"
    if include_releases:
        command += " --include-releases"
    return TroubleshootItem(
        "privacy cleanup candidates",
        "warn",
        f"{len(items)} candidate(s), {_format_bytes(total_size)}, {category_text}{release_note}",
        f"`{command}` で削除前の候補を確認できます。削除する時だけ `--apply` を追加してください。",
    )


def _release_item(project_dir: Path) -> TroubleshootItem:
    releases = list_releases(project_dir)
    if not releases:
        return TroubleshootItem("latest release", "info", "no release package found yet")
    latest = releases[0]
    errors = verify_release_package(latest)
    if errors:
        return TroubleshootItem(
            "latest release",
            "fail",
            f"{latest.name}: {len(errors)} verification error(s)",
            "`auto-note release --verify <zip>` で詳細を確認し、`auto-note preflight --project-dir . --create-release` で作り直してください。",
        )
    return TroubleshootItem("latest release", "pass", f"{latest.name}: checksum and privacy manifest OK")


def _error_markers(text: str) -> list[str]:
    markers: list[str] = []
    patterns = {
        "Traceback": r"\bTraceback\b",
        "WinError": r"\bWinError\b",
        "failed": r"\bFailed\b|\bfailed\b",
        "Tk error": r"tkinter\.TclError|TclError",
    }
    for label, pattern in patterns.items():
        if re.search(pattern, text):
            markers.append(label)
    return markers


def _last_non_empty_line(text: str) -> str:
    for line in reversed(text.splitlines()):
        if line.strip():
            return line.strip()
    return ""


def _sanitize(text: str, project_dir: Path) -> str:
    replacements = {
        str(project_dir.resolve()): "<PROJECT_DIR>",
        project_dir.resolve().as_posix(): "<PROJECT_DIR>",
        str(Path.home()): "<HOME>",
        Path.home().as_posix(): "<HOME>",
        Path.home().name: "<USER>",
    }
    sanitized = text
    for value, replacement in sorted(replacements.items(), key=lambda pair: len(pair[0]), reverse=True):
        if value:
            sanitized = re.sub(re.escape(value), replacement, sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "<EMAIL>", sanitized)
    return sanitized[:240]


def _category_counts(project_dir: Path, items) -> dict[str, int]:
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


def _format_bytes(value: int) -> str:
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value} B"
