from __future__ import annotations

from datetime import datetime
from pathlib import Path
import csv

from .inspect import inspect_path
from .paths import unique_path
from .settings import load_settings


def export_article_inventory(project_dir: Path) -> Path:
    settings = load_settings(project_dir)
    reports = inspect_path(
        project_dir / "articles",
        pattern=settings.article_glob,
        append_tags=settings.append_tags_by_default,
    )
    reports_dir = project_dir / ".auto-note" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(reports_dir / f"article-inventory-{datetime.now():%Y%m%d-%H%M%S}.csv")

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "file",
                "title",
                "status",
                "scheduled",
                "published_url",
                "tags",
                "body_chars",
                "reading_minutes",
                "issue_count",
                "error_count",
                "warning_count",
            ]
        )
        for report in reports:
            article = report.article
            error_count = sum(1 for issue in report.issues if issue.level == "error")
            warning_count = sum(1 for issue in report.issues if issue.level == "warn")
            writer.writerow(
                [
                    article.source.name,
                    article.title,
                    article.status,
                    article.scheduled,
                    article.published_url,
                    ", ".join(article.tags),
                    report.stats.body_chars,
                    report.stats.reading_minutes,
                    len(report.issues),
                    error_count,
                    warning_count,
                ]
            )
    return path


def list_reports(project_dir: Path) -> list[Path]:
    reports_dir = project_dir / ".auto-note" / "reports"
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
