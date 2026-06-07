from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re
import tempfile


@dataclass(frozen=True)
class Article:
    source: Path
    title: str
    body: str
    tags: list[str]
    publish: bool | None = None
    summary: str = ""
    cover: str = ""
    status: str = "draft"
    scheduled: str = ""
    published_at: str = ""
    published_url: str = ""


class ArticleError(ValueError):
    pass


def load_article(path: str | Path) -> Article:
    source = Path(path)
    text = source.read_text(encoding="utf-8-sig")
    metadata, body = split_frontmatter(text)

    title = _string_value(metadata.get("title"))
    if not title:
        heading = _first_h1(body)
        if heading:
            title = heading
            body = _remove_first_h1(body)
    if not title:
        title = source.stem.replace("-", " ").replace("_", " ").strip()

    body = body.strip()
    if not body:
        raise ArticleError(f"{source} has no article body.")

    return Article(
        source=source,
        title=title.strip(),
        body=body,
        tags=_normalise_tags(metadata.get("tags")),
        publish=_bool_or_none(metadata.get("publish")),
        summary=_first_string(metadata, ("summary", "description", "excerpt")),
        cover=_first_string(metadata, ("cover", "image", "thumbnail")),
        status=_first_string(metadata, ("status",)) or "draft",
        scheduled=_first_string(metadata, ("scheduled", "scheduled_at", "publish_at")),
        published_at=_first_string(metadata, ("published_at",)),
        published_url=_first_string(metadata, ("published_url", "url")),
    )


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, text

    raw_meta = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :])
    return _parse_metadata(raw_meta), body


def read_markdown(path: str | Path) -> tuple[dict[str, Any], str]:
    source = Path(path)
    return split_frontmatter(source.read_text(encoding="utf-8-sig"))


def write_markdown(path: str | Path, metadata: dict[str, Any], body: str) -> None:
    source = Path(path)
    ordered = _ordered_metadata(metadata)
    frontmatter = _dump_metadata(ordered).strip()
    write_text_atomic(source, f"---\n{frontmatter}\n---\n\n{body.strip()}\n")


def write_text_atomic(path: str | Path, text: str, *, encoding: str = "utf-8") -> None:
    source = Path(path)
    source.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding=encoding,
            dir=source.parent,
            prefix=f".{source.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            temp_path = Path(handle.name)
        temp_path.replace(source)
    except Exception:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def body_with_tags(article: Article) -> str:
    if not article.tags:
        return article.body
    hashtags = hashtags_for(article)
    if hashtags in article.body:
        return article.body
    return f"{article.body.rstrip()}\n\n{hashtags}"


def hashtags_for(article: Article) -> str:
    return " ".join(f"#{_compact_tag(tag)}" for tag in article.tags)


def text_bundle(article: Article, *, append_tags: bool = True, include_title: bool = True) -> str:
    body = body_with_tags(article) if append_tags else article.body
    if not include_title:
        return body
    return f"{article.title}\n\n{body}"


def _parse_metadata(raw_meta: str) -> dict[str, Any]:
    try:
        import yaml
    except ModuleNotFoundError:
        return _parse_simple_metadata(raw_meta)

    loaded = yaml.safe_load(raw_meta) or {}
    if not isinstance(loaded, dict):
        raise ArticleError("Frontmatter must be a mapping.")
    return loaded


def _dump_metadata(metadata: dict[str, Any]) -> str:
    try:
        import yaml
    except ModuleNotFoundError:
        return _dump_simple_metadata(metadata)

    return yaml.safe_dump(
        metadata,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


def _dump_simple_metadata(metadata: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in metadata.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in value)
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif value is None:
            lines.append(f"{key}:")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _ordered_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    preferred = (
        "title",
        "summary",
        "cover",
        "tags",
        "status",
        "scheduled",
        "publish",
        "published_at",
        "published_url",
    )
    ordered: dict[str, Any] = {}
    for key in preferred:
        if key in metadata:
            ordered[key] = metadata[key]
    for key, value in metadata.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _parse_simple_metadata(raw_meta: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    current_key: str | None = None

    for raw_line in raw_meta.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        if line.startswith("  - ") and current_key:
            metadata.setdefault(current_key, []).append(line[4:].strip().strip("'\""))
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_key = key
        if value:
            metadata[key] = value.strip("'\"")
        else:
            metadata[key] = []

    return metadata


def _normalise_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_tags = [part.strip() for part in re.split(r"[,#]", value)]
    elif isinstance(value, (list, tuple, set)):
        raw_tags = [str(part).strip() for part in value]
    else:
        raw_tags = [str(value).strip()]

    tags: list[str] = []
    seen: set[str] = set()
    for tag in raw_tags:
        cleaned = tag.lstrip("#").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        tags.append(cleaned)
    return tags


def _compact_tag(tag: str) -> str:
    return re.sub(r"\s+", "", tag.lstrip("#").strip())


def _first_h1(body: str) -> str | None:
    for line in body.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1)
    return None


def _remove_first_h1(body: str) -> str:
    removed = False
    output: list[str] = []
    for line in body.splitlines():
        if not removed and re.match(r"^#\s+.+?\s*$", line):
            removed = True
            continue
        output.append(line)
    return "\n".join(output)


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _first_string(metadata: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _string_value(metadata.get(key))
        if value:
            return value
    return ""
