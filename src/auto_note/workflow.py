from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import shutil
import tempfile

from .article import Article, ArticleError, load_article, read_markdown, write_markdown, write_text_atomic
from .paths import unique_path
from .scaffold import create_article


STATUSES = {"draft", "ready", "scheduled", "published"}


@dataclass(frozen=True)
class Idea:
    id: int
    title: str
    note: str
    tags: list[str]
    created_at: str
    promoted_to: str = ""
    promoted_at: str = ""


@dataclass(frozen=True)
class IdeaStoreStatus:
    path: Path
    exists: bool
    ok: bool
    detail: str


@dataclass(frozen=True)
class CalendarExportResult:
    path: Path
    event_count: int
    include_private: bool
    days: int


def set_article_status(path: Path, status: str) -> None:
    if status not in STATUSES:
        raise ArticleError(f"status must be one of: {', '.join(sorted(STATUSES))}")
    metadata, body = read_markdown(path)
    metadata["status"] = status
    write_markdown(path, metadata, body)


def set_article_schedule(path: Path, scheduled: str) -> None:
    _parse_schedule(scheduled)
    metadata, body = read_markdown(path)
    metadata["status"] = "scheduled"
    metadata["scheduled"] = scheduled
    write_markdown(path, metadata, body)


def clear_article_schedule(path: Path) -> None:
    metadata, body = read_markdown(path)
    metadata.pop("scheduled", None)
    if metadata.get("status") == "scheduled":
        metadata["status"] = "draft"
    write_markdown(path, metadata, body)


def mark_article_published(path: Path, *, url: str = "") -> None:
    metadata, body = read_markdown(path)
    metadata["status"] = "published"
    metadata["published_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if url:
        metadata["published_url"] = url
    write_markdown(path, metadata, body)


def update_article_metadata(
    path: Path,
    *,
    title: str,
    summary: str = "",
    tags: list[str] | None = None,
    cover: str = "",
) -> None:
    title = title.strip()
    if not title:
        raise ArticleError("title is required.")

    metadata, body = read_markdown(path)
    metadata["title"] = title
    _set_optional_metadata(metadata, "summary", summary)
    _set_optional_metadata(metadata, "cover", cover)
    if tags is not None:
        metadata["tags"] = _clean_tags(tags)
    write_markdown(path, metadata, body)


def format_plan(path: Path, *, pattern: str = "*.md") -> str:
    articles = _collect_articles(path, pattern)
    grouped: dict[str, list[Article]] = {status: [] for status in ("draft", "ready", "scheduled", "published")}
    for article in articles:
        status = article.status if article.status in grouped else "draft"
        grouped[status].append(article)

    lines: list[str] = []
    for status in ("draft", "ready", "scheduled", "published"):
        bucket = sorted(grouped.get(status, []), key=_article_sort_key)
        lines.append(f"[{status}] {len(bucket)}")
        if not bucket:
            lines.append("  (none)")
            lines.append("")
            continue
        for article in bucket:
            extra = ""
            if article.scheduled:
                extra = f" | scheduled: {article.scheduled}"
            if article.published_url:
                extra = f" | url: {article.published_url}"
            lines.append(f"  - {article.title}{extra}")
            lines.append(f"    {article.source}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_calendar(path: Path, *, pattern: str = "*.md", days: int = 30, include_private: bool = True) -> str:
    articles = _scheduled_articles(path, pattern=pattern, days=days)
    if not articles:
        return "公開予定はありません。"

    now = datetime.now()
    lines = [f"公開予定 直近{days}日"]
    for index, article in enumerate(articles, start=1):
        scheduled_at = _parse_schedule(article.scheduled)
        delta = (scheduled_at.date() - now.date()).days
        marker = "today" if delta == 0 else f"{delta:+d}d"
        title = article.title if include_private else f"<title:{len(article.title)} chars>"
        source = str(article.source) if include_private else f"article-{index:03d}.md"
        lines.append(f"- {article.scheduled} [{marker}] {title}")
        lines.append(f"  {source}")
    if len(lines) == 1:
        return f"直近{days}日に公開予定はありません。"
    return "\n".join(lines)


def export_calendar(
    project_dir: Path,
    path: Path | None = None,
    *,
    pattern: str = "*.md",
    days: int = 90,
    output_path: Path | None = None,
    include_private: bool = False,
) -> CalendarExportResult:
    source = path or (project_dir / "articles")
    articles = _scheduled_articles(source, pattern=pattern, days=days)
    destination = output_path or unique_path(
        project_dir / ".auto-note" / "reports" / f"calendar-{datetime.now():%Y%m%d-%H%M%S}.ics"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_calendar_text_atomic(destination, _build_ics(articles, include_private=include_private))
    return CalendarExportResult(
        path=destination,
        event_count=len(articles),
        include_private=include_private,
        days=days,
    )


def format_calendar_export(result: CalendarExportResult) -> str:
    privacy = "private titles included" if result.include_private else "privacy-safe titles"
    lines = [
        "Calendar export / 予定ICS",
        f"File: {result.path}",
        f"Events: {result.event_count}",
        f"Window: {result.days} day(s)",
        f"Privacy: {privacy}",
    ]
    if result.event_count == 0:
        lines.append("No scheduled articles were found in the selected window.")
    else:
        lines.append("Import this .ics file into Google Calendar, Outlook, or Apple Calendar.")
    return "\n".join(lines)


def list_calendar_exports(project_dir: Path) -> list[Path]:
    reports_dir = project_dir / ".auto-note" / "reports"
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("calendar-*.ics"), key=lambda path: path.stat().st_mtime, reverse=True)


def ideas_path(project_dir: Path) -> Path:
    return project_dir / ".auto-note" / "ideas.json"


def load_ideas(project_dir: Path) -> list[Idea]:
    path = ideas_path(project_dir)
    if not path.exists():
        return []
    try:
        return _ideas_from_raw(_read_ideas_json(path))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ArticleError):
        return []


def save_ideas(project_dir: Path, ideas: list[Idea]) -> None:
    path = ideas_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not inspect_ideas(project_dir).ok:
        _backup_invalid_ideas(path)
    data = [idea.__dict__ for idea in ideas]
    write_text_atomic(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def inspect_ideas(project_dir: Path) -> IdeaStoreStatus:
    path = ideas_path(project_dir)
    if not path.exists():
        return IdeaStoreStatus(path, False, True, "not created yet")
    try:
        ideas = _ideas_from_raw(_read_ideas_json(path))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ArticleError) as exc:
        return IdeaStoreStatus(path, True, False, f"invalid ideas.json: {exc}")
    return IdeaStoreStatus(path, True, True, f"valid, {len(ideas)} idea(s)")


def list_idea_recovery_files(project_dir: Path) -> list[Path]:
    directory = project_dir / ".auto-note"
    if not directory.exists():
        return []
    return sorted(directory.glob("ideas.invalid-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)


def add_idea(project_dir: Path, title: str, *, note: str = "", tags: list[str] | None = None) -> Idea:
    ideas = load_ideas(project_dir)
    next_id = max((idea.id for idea in ideas), default=0) + 1
    idea = Idea(
        id=next_id,
        title=title.strip(),
        note=note.strip(),
        tags=tags or [],
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    if not idea.title:
        raise ArticleError("idea title is empty.")
    ideas.append(idea)
    save_ideas(project_dir, ideas)
    return idea


def format_ideas(project_dir: Path, *, include_done: bool = False) -> str:
    ideas = load_ideas(project_dir)
    if not include_done:
        ideas = [idea for idea in ideas if not idea.promoted_to]
    if not ideas:
        return "アイデアはありません。"

    lines: list[str] = []
    for idea in ideas:
        state = "done" if idea.promoted_to else "open"
        tags = f" tags: {', '.join(idea.tags)}" if idea.tags else ""
        lines.append(f"{idea.id}. [{state}] {idea.title}{tags}")
        if idea.note:
            lines.append(f"   {idea.note}")
        if idea.promoted_to:
            lines.append(f"   promoted: {idea.promoted_to}")
    return "\n".join(lines)


def promote_idea(project_dir: Path, idea_id: int, *, articles_dir: Path, open_status: str = "draft") -> Path:
    ideas = load_ideas(project_dir)
    for index, idea in enumerate(ideas):
        if idea.id != idea_id:
            continue
        path = create_article(idea.title, articles_dir=articles_dir, tags=idea.tags)
        metadata, body = read_markdown(path)
        metadata["status"] = open_status
        if idea.note:
            metadata["summary"] = idea.note
        write_markdown(path, metadata, body)
        ideas[index] = Idea(
            id=idea.id,
            title=idea.title,
            note=idea.note,
            tags=idea.tags,
            created_at=idea.created_at,
            promoted_to=str(path),
            promoted_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        save_ideas(project_dir, ideas)
        return path
    raise ArticleError(f"Idea not found: {idea_id}")


def _collect_articles(path: Path, pattern: str) -> list[Article]:
    files = [path] if path.is_file() else sorted(path.glob(pattern))
    articles: list[Article] = []
    for file in files:
        if not file.is_file():
            continue
        try:
            articles.append(load_article(file))
        except ArticleError:
            continue
    return articles


def _scheduled_articles(path: Path, *, pattern: str, days: int) -> list[Article]:
    now = datetime.now()
    articles: list[Article] = []
    for article in _collect_articles(path, pattern):
        if not article.scheduled:
            continue
        try:
            scheduled_at = _parse_schedule(article.scheduled)
        except ArticleError:
            continue
        delta = (scheduled_at.date() - now.date()).days
        if delta <= days:
            articles.append(article)
    return sorted(articles, key=lambda article: _schedule_or_max(article.scheduled))


def _parse_schedule(value: str) -> datetime:
    normalized = value.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            pass
    raise ArticleError("scheduled must be 'YYYY-MM-DD HH:MM'.")


def _set_optional_metadata(metadata: dict[str, Any], key: str, value: str) -> None:
    value = value.strip()
    if value:
        metadata[key] = value
    else:
        metadata.pop(key, None)


def _clean_tags(tags: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        value = str(tag).strip().lstrip("#")
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def _schedule_or_max(value: str) -> datetime:
    try:
        return _parse_schedule(value)
    except ArticleError:
        return datetime.max


def _article_sort_key(article: Article) -> tuple[str, str]:
    scheduled = article.scheduled or "9999-99-99 99:99"
    return scheduled, article.title


def _build_ics(articles: list[Article], *, include_private: bool) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//auto-note//auto-note calendar//JA",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:auto-note publishing plan",
    ]
    for index, article in enumerate(articles, start=1):
        start = _parse_schedule(article.scheduled)
        end = start + timedelta(minutes=30)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{_event_uid(article)}",
                f"DTSTAMP:{now}",
                f"DTSTART:{start:%Y%m%dT%H%M%S}",
                f"DTEND:{end:%Y%m%dT%H%M%S}",
                f"SUMMARY:{_ical_escape(_event_summary(article, index=index, include_private=include_private))}",
                f"DESCRIPTION:{_ical_escape(_event_description(article, index=index, include_private=include_private))}",
                "CATEGORIES:auto-note,note",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    folded: list[str] = []
    for line in lines:
        folded.extend(_fold_ical_line(line))
    return "\r\n".join(folded) + "\r\n"


def _event_summary(article: Article, *, index: int, include_private: bool) -> str:
    if include_private:
        return f"note投稿: {article.title}"
    return f"note投稿予定 {index:03d}"


def _event_description(article: Article, *, index: int, include_private: bool) -> str:
    if include_private:
        return f"auto-note scheduled article\nTitle: {article.title}\nFile: {article.source}\nStatus: {article.status}"
    return (
        "auto-note scheduled article\n"
        f"Title: <title:{len(article.title)} chars>\n"
        f"File: article-{index:03d}.md\n"
        f"Status: {article.status}"
    )


def _event_uid(article: Article) -> str:
    raw = f"{article.source.resolve()}|{article.scheduled}|{article.title}"
    digest = hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"auto-note-{digest}"


def _ical_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def _fold_ical_line(line: str) -> list[str]:
    if len(line) <= 75:
        return [line]
    chunks = [line[:75]]
    rest = line[75:]
    while rest:
        chunks.append(" " + rest[:74])
        rest = rest[74:]
    return chunks


def _write_calendar_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            temp_path = Path(handle.name)
        temp_path.replace(path)
    except Exception:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def _read_ideas_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _ideas_from_raw(raw: Any) -> list[Idea]:
    if not isinstance(raw, list):
        raise ArticleError("root must be a list")
    ideas: list[Idea] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ArticleError(f"item {index} must be an object")
        try:
            ideas.append(Idea(**_idea_defaults(item)))
        except (TypeError, ValueError) as exc:
            raise ArticleError(f"item {index} is invalid: {exc}") from exc
    return ideas


def _backup_invalid_ideas(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = path.with_name(f"ideas.invalid-{timestamp}.json")
    shutil.copy2(path, backup_path)
    return backup_path


def _idea_defaults(item: dict[str, Any]) -> dict[str, Any]:
    raw_tags = item.get("tags", [])
    if isinstance(raw_tags, str):
        tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    else:
        tags = [str(tag) for tag in raw_tags]
    return {
        "id": int(item.get("id", 0)),
        "title": str(item.get("title", "")),
        "note": str(item.get("note", "")),
        "tags": tags,
        "created_at": str(item.get("created_at", "")),
        "promoted_to": str(item.get("promoted_to", "")),
        "promoted_at": str(item.get("promoted_at", "")),
    }
