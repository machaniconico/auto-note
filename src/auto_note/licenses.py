from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from pathlib import Path


@dataclass(frozen=True)
class DependencySpec:
    package: str
    display_name: str
    dependency_type: str
    purpose: str


@dataclass(frozen=True)
class DependencyNotice:
    package: str
    display_name: str
    dependency_type: str
    purpose: str
    installed: bool
    version: str
    license: str
    summary: str
    home_page: str


DEPENDENCY_SPECS = (
    DependencySpec(
        package="PyYAML",
        display_name="PyYAML",
        dependency_type="required",
        purpose="Read article frontmatter metadata.",
    ),
    DependencySpec(
        package="Pillow",
        display_name="Pillow",
        dependency_type="optional images",
        purpose="Resize and compress imported images when image optimization is enabled.",
    ),
    DependencySpec(
        package="playwright",
        display_name="Playwright",
        dependency_type="optional browser automation",
        purpose="Drive a browser for environments where automated posting is usable.",
    ),
    DependencySpec(
        package="pyee",
        display_name="pyee",
        dependency_type="optional transitive",
        purpose="Runtime dependency used by Playwright.",
    ),
    DependencySpec(
        package="greenlet",
        display_name="greenlet",
        dependency_type="optional transitive",
        purpose="Runtime dependency used by Playwright.",
    ),
    DependencySpec(
        package="typing_extensions",
        display_name="typing-extensions",
        dependency_type="optional transitive",
        purpose="Compatibility helpers used by optional dependencies on older Python versions.",
    ),
)


def collect_dependency_notices() -> list[DependencyNotice]:
    return [_notice_for_spec(spec) for spec in DEPENDENCY_SPECS]


def format_dependency_notices(notices: list[DependencyNotice] | None = None) -> str:
    notices = notices if notices is not None else collect_dependency_notices()
    lines = [
        "# Third-party notices",
        "",
        "This file summarizes auto-note's Python package dependencies.",
        "Run `auto-note licenses` in the installed environment before a commercial release to confirm versions.",
        "",
    ]
    for notice in notices:
        installed = "yes" if notice.installed else "no"
        lines.extend(
            [
                f"## {notice.display_name}",
                f"- Package: `{notice.package}`",
                f"- Type: {notice.dependency_type}",
                f"- Purpose: {notice.purpose}",
                f"- Installed: {installed}",
                f"- Version: {notice.version}",
                f"- License: {notice.license}",
            ]
        )
        if notice.summary:
            lines.append(f"- Summary: {notice.summary}")
        if notice.home_page:
            lines.append(f"- Home page: {notice.home_page}")
        lines.append("")
    lines.extend(
        [
            "Notes:",
            "- The release ZIP excludes `.venv`, so Python package files are not bundled in the source distribution.",
            "- Review each dependency license again when dependency versions change.",
        ]
    )
    return "\n".join(lines)


def write_dependency_notices(path: Path, notices: list[DependencyNotice] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_dependency_notices(notices) + "\n", encoding="utf-8")
    return path


def _notice_for_spec(spec: DependencySpec) -> DependencyNotice:
    try:
        package_version = importlib_metadata.version(spec.package)
        meta = importlib_metadata.metadata(spec.package)
    except importlib_metadata.PackageNotFoundError:
        return DependencyNotice(
            package=spec.package,
            display_name=spec.display_name,
            dependency_type=spec.dependency_type,
            purpose=spec.purpose,
            installed=False,
            version="not installed",
            license="not installed",
            summary="",
            home_page="",
        )

    display_name = _one_line(meta.get("Name")) or spec.display_name
    return DependencyNotice(
        package=spec.package,
        display_name=display_name,
        dependency_type=spec.dependency_type,
        purpose=spec.purpose,
        installed=True,
        version=package_version,
        license=_license_from_metadata(meta),
        summary=_one_line(meta.get("Summary")),
        home_page=_home_page_from_metadata(meta),
    )


def _license_from_metadata(meta) -> str:
    for key in ("License-Expression", "License"):
        value = _one_line(meta.get(key))
        if value:
            return _shorten(value)
    for classifier in meta.get_all("Classifier", []):
        classifier = _one_line(classifier)
        if classifier.startswith("License ::"):
            return _shorten(classifier.removeprefix("License ::").strip())
    return "Unknown"


def _home_page_from_metadata(meta) -> str:
    home_page = _one_line(meta.get("Home-page"))
    if home_page:
        return home_page
    for raw in meta.get_all("Project-URL", []):
        label, separator, url = raw.partition(",")
        if not separator:
            continue
        if label.strip().lower() in {"homepage", "home", "source", "repository", "documentation"}:
            return _one_line(url)
    return ""


def _one_line(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _shorten(value: str, *, limit: int = 140) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."
