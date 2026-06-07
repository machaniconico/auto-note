from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .article import Article, ArticleError, body_with_tags, load_article
from .images import collect_article_images


@dataclass(frozen=True)
class Issue:
    level: str
    message: str


@dataclass(frozen=True)
class ArticleStats:
    title_chars: int
    body_chars: int
    lines: int
    tag_count: int
    reading_minutes: int


@dataclass(frozen=True)
class ArticleReport:
    article: Article
    stats: ArticleStats
    issues: list[Issue]

    @property
    def ok(self) -> bool:
        return not any(issue.level == "error" for issue in self.issues)


def inspect_article(article: Article, *, append_tags: bool = False) -> ArticleReport:
    body = body_with_tags(article) if append_tags else article.body
    stats = ArticleStats(
        title_chars=len(article.title),
        body_chars=len(body),
        lines=len(body.splitlines()),
        tag_count=len(article.tags),
        reading_minutes=max(1, round(len(body) / 700)),
    )
    issues = _issues_for(article, body)
    return ArticleReport(article=article, stats=stats, issues=issues)


def inspect_path(path: Path, *, pattern: str = "*.md", append_tags: bool = False) -> list[ArticleReport]:
    files = _collect_markdown_files(path, pattern)
    if not files:
        raise ArticleError(f"No markdown files found in {path}.")
    return [inspect_article(load_article(file), append_tags=append_tags) for file in files]


def format_reports(reports: list[ArticleReport]) -> str:
    lines: list[str] = []
    for report in reports:
        article = report.article
        stats = report.stats
        status = "OK" if report.ok else "NG"
        lines.append(f"[{status}] {article.source}")
        lines.append(f"  title: {article.title} ({stats.title_chars} chars)")
        lines.append(
            f"  body: {stats.body_chars} chars, {stats.lines} lines, "
            f"about {stats.reading_minutes} min"
        )
        lines.append(f"  tags: {', '.join(article.tags) if article.tags else '(none)'}")
        if article.summary:
            lines.append(f"  summary: {article.summary}")
        if report.issues:
            for issue in report.issues:
                lines.append(f"  {issue.level}: {issue.message}")
        else:
            lines.append("  no issues")
        lines.append("")
    return "\n".join(lines).rstrip()


def _issues_for(article: Article, body: str) -> list[Issue]:
    issues: list[Issue] = []
    if len(article.title) > 80:
        issues.append(Issue("warn", "タイトルが80文字を超えています。"))
    if len(body) < 200:
        issues.append(Issue("warn", "本文が短めです。公開前に内容量を確認してください。"))
    if not article.tags:
        issues.append(Issue("warn", "タグが設定されていません。"))
    if len(article.tags) > 10:
        issues.append(Issue("warn", "タグが10個を超えています。"))
    if article.status == "scheduled" and not article.scheduled:
        issues.append(Issue("warn", "status が scheduled ですが scheduled が空です。"))
    if article.status == "published" and not article.published_url:
        issues.append(Issue("warn", "公開済みですが published_url が空です。"))
    if re.search(r"\b(TODO|FIXME|下書き|要確認)\b", body, flags=re.I):
        issues.append(Issue("warn", "本文に未処理メモらしき文字があります。"))

    for image in collect_article_images(article):
        if not image.ok:
            issues.append(Issue("error", f"画像ファイルが見つかりません: {image.value}"))
        elif image.large:
            issues.append(Issue("warn", f"画像サイズが大きめです: {image.value}"))

    return issues


def _collect_markdown_files(path: Path, pattern: str) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(file for file in path.glob(pattern) if file.is_file())
