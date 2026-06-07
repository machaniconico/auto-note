from __future__ import annotations

from datetime import datetime
from pathlib import Path
import hashlib
import json
import re
import zipfile

from .paths import unique_path


INCLUDE_ROOTS = (
    "src",
    "scripts",
    "shortcuts",
    "examples",
    "docs",
    "tests",
)
INCLUDE_FILES = (
    "auto-note-gui.bat",
    "README.md",
    "pyproject.toml",
)
EXCLUDED_PARTS = {
    ".git",
    ".auto-note",
    ".venv",
    "__pycache__",
    "auto_note.egg-info",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".lnk",
}


def create_release_package(project_dir: Path) -> Path:
    release_dir = project_dir / ".auto-note" / "releases"
    release_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now()
    package_path = unique_path(release_dir / f"auto-note-release-{created_at:%Y%m%d-%H%M%S}.zip")
    records: list[dict[str, object]] = []

    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_name in INCLUDE_FILES:
            path = project_dir / file_name
            if path.exists() and path.is_file():
                _write_file(archive, path, file_name, records)

        for root_name in INCLUDE_ROOTS:
            root = project_dir / root_name
            if root.exists():
                _add_tree(archive, project_dir, root, records)

        _write_text(archive, "articles/.keep", "", records)
        _write_text(archive, "START_HERE.txt", _build_start_here(), records)
        _write_text(archive, "FIRST_RUN_CHECKLIST.txt", _build_first_run_checklist(), records)
        _write_text(archive, "BUYER_ACCEPTANCE_CHECKLIST.txt", _build_buyer_acceptance_checklist(), records)
        _write_text(archive, "RELEASE_SUMMARY.txt", _build_release_summary(project_dir, created_at), records)
        manifest = _build_manifest(project_dir, created_at, records)
        _write_text(archive, "RELEASE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", records)
        _write_text(archive, "CHECKSUMS.txt", _build_checksums(records), records)

    return package_path


def list_releases(project_dir: Path) -> list[Path]:
    release_dir = project_dir / ".auto-note" / "releases"
    if not release_dir.exists():
        return []
    return sorted(release_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)


def verify_release_package(package_path: Path) -> list[str]:
    errors: list[str] = []
    if not package_path.exists():
        return [f"package not found: {package_path}"]
    try:
        with zipfile.ZipFile(package_path) as archive:
            names = set(archive.namelist())
            for required in (
                "RELEASE_MANIFEST.json",
                "CHECKSUMS.txt",
                "START_HERE.txt",
                "FIRST_RUN_CHECKLIST.txt",
                "BUYER_ACCEPTANCE_CHECKLIST.txt",
                "RELEASE_SUMMARY.txt",
            ):
                if required not in names:
                    errors.append(f"missing required file: {required}")
            _verify_archive_paths(names, errors)
            _verify_privacy_exclusions(names, errors)
            _verify_manifest(archive, names, errors)
            if "CHECKSUMS.txt" not in names:
                return errors
            checksums = archive.read("CHECKSUMS.txt").decode("utf-8", errors="replace").splitlines()
            for line in checksums:
                if not line.strip():
                    continue
                expected, _, archive_name = line.partition("  ")
                if not expected or not archive_name:
                    errors.append(f"invalid checksum line: {line}")
                    continue
                if archive_name not in names:
                    errors.append(f"missing checksummed file: {archive_name}")
                    continue
                actual = hashlib.sha256(archive.read(archive_name)).hexdigest()
                if actual != expected:
                    errors.append(f"checksum mismatch: {archive_name}")
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"unreadable package: {exc}")
    return errors


def _verify_archive_paths(names: set[str], errors: list[str]) -> None:
    for name in sorted(names):
        normalized = name.replace("\\", "/")
        parts = [part for part in normalized.split("/") if part]
        if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
            errors.append(f"unsafe archive path: {name}")
        if any(part == ".." for part in parts):
            errors.append(f"unsafe archive path: {name}")


def _verify_privacy_exclusions(names: set[str], errors: list[str]) -> None:
    for name in sorted(names):
        normalized = name.replace("\\", "/").strip("/")
        parts = normalized.split("/") if normalized else []
        if normalized.startswith("articles/") and normalized != "articles/.keep":
            errors.append(f"user article must not be included: {name}")
        excluded_part = next((part for part in parts if part in EXCLUDED_PARTS), "")
        if excluded_part:
            errors.append(f"excluded path must not be included: {name}")
        suffix = Path(normalized).suffix.lower()
        if suffix in EXCLUDED_SUFFIXES:
            errors.append(f"excluded file suffix must not be included: {name}")


def _verify_manifest(archive: zipfile.ZipFile, names: set[str], errors: list[str]) -> None:
    if "RELEASE_MANIFEST.json" not in names:
        return
    try:
        manifest = json.loads(archive.read("RELEASE_MANIFEST.json").decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        errors.append(f"invalid RELEASE_MANIFEST.json: {exc}")
        return
    if not isinstance(manifest, dict):
        errors.append("invalid RELEASE_MANIFEST.json: root must be an object")
        return

    privacy = manifest.get("privacy")
    if not isinstance(privacy, dict):
        errors.append("missing manifest privacy flags")
    else:
        for key in ("includes_user_articles", "includes_generated_helpers", "includes_virtualenv"):
            if privacy.get(key) is not False:
                errors.append(f"manifest privacy flag must be false: {key}")

    entrypoint = manifest.get("entrypoint")
    if not isinstance(entrypoint, str) or not entrypoint:
        errors.append("missing manifest entrypoint")
    elif entrypoint not in names:
        errors.append(f"manifest entrypoint missing from package: {entrypoint}")

    files = manifest.get("files")
    if not isinstance(files, list):
        errors.append("manifest files must be a list")
        return
    if manifest.get("file_count") != len(files):
        errors.append("manifest file_count does not match files list")
    for record in files:
        if not isinstance(record, dict):
            errors.append("manifest file record must be an object")
            continue
        archive_name = record.get("path")
        if not isinstance(archive_name, str) or not archive_name:
            errors.append("manifest file record missing path")
            continue
        if archive_name not in names:
            errors.append(f"manifest file missing from package: {archive_name}")


def format_release_verification(package_path: Path, errors: list[str]) -> str:
    if not errors:
        return "\n".join(
            [
                f"[OK] release package verified: {package_path}",
                "",
                *_release_verification_summary(package_path),
            ]
        )
    lines = [f"[NG] release package verification failed: {package_path}"]
    lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def _add_tree(
    archive: zipfile.ZipFile,
    project_dir: Path,
    root: Path,
    records: list[dict[str, object]],
) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or _is_excluded(path):
            continue
        _write_file(archive, path, path.relative_to(project_dir).as_posix(), records)


def _is_excluded(path: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return True
    return path.suffix.lower() in EXCLUDED_SUFFIXES


def _write_file(
    archive: zipfile.ZipFile,
    source: Path,
    archive_name: str,
    records: list[dict[str, object]],
) -> None:
    data = source.read_bytes()
    archive.writestr(archive_name, data)
    records.append(
        {
            "path": archive_name,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    )


def _write_text(
    archive: zipfile.ZipFile,
    archive_name: str,
    text: str,
    records: list[dict[str, object]],
) -> None:
    data = text.encode("utf-8")
    archive.writestr(archive_name, data)
    records.append(
        {
            "path": archive_name,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    )


def _build_manifest(project_dir: Path, created_at: datetime, records: list[dict[str, object]]) -> dict[str, object]:
    metadata = _project_metadata(project_dir)
    return {
        "name": metadata["name"],
        "version": metadata["version"],
        "created_at": created_at.isoformat(timespec="seconds"),
        "package_type": "source-zip",
        "privacy": {
            "includes_user_articles": False,
            "includes_generated_helpers": False,
            "includes_virtualenv": False,
        },
        "entrypoint": "auto-note-gui.bat",
        "file_count": len(records),
        "files": records,
    }


def _build_start_here() -> str:
    return (
        "auto-note START HERE\n"
        "\n"
        "1. このzipを好きな場所に展開します。\n"
        "2. shortcuts\\install-auto-note.bat をダブルクリックします。\n"
        "3. デスクトップまたはスタートメニューの auto-note を開きます。\n"
        "4. GUIのセットアップウィザードで基本設定を確認します。\n"
        "5. 起動後に不足が出る場合は GUI の 自動修復、または auto-note repair --project-dir . --apply を使います。\n"
        "6. 起動、ログイン、問い合わせ前の切り分けは GUI の トラブル診断、または auto-note troubleshoot --project-dir . を使います。\n"
        "7. 初めて触る場合は GUI の スターター一式 を押します。\n"
        "8. スターターを片付ける場合は GUI の スターター整理 で候補を確認します。\n"
        "9. 自分の記事を作る場合は GUI の 新規記事 を押します。\n"
        "10. note に投稿する時は 投稿ヘルパー を開き、普段のブラウザへ貼り付けます。\n"
        "11. 販売/配布前の確認は GUI の 出荷前チェック または 出荷ZIP作成 を使います。\n"
        "12. 購入者への納品確認は BUYER_ACCEPTANCE_CHECKLIST.txt と auto-note acceptance --project-dir . --full を使います。\n"
        "\n"
        "インストールせず試す場合:\n"
        "- auto-note-gui.bat を直接開きます。\n"
        "\n"
        "困った時:\n"
        "- docs\\INSTALL.md を確認します。\n"
        "- docs\\SUPPORT.md を確認します。\n"
        "- GUIのヘルプで 問い合わせ一式 を作成できます。\n"
        "- CLIでは auto-note support --project-dir . --bundle を使います。\n"
        "- GUIが起動しない場合は auto-note-gui.bat を開くとエラー内容を確認できます。\n"
        "\n"
        "配布内容の確認:\n"
        "- RELEASE_SUMMARY.txt に、このzipの概要と含まれないデータを書いています。\n"
        "- FIRST_RUN_CHECKLIST.txt に、初回起動後に確認する項目を書いています。\n"
        "- BUYER_ACCEPTANCE_CHECKLIST.txt に、購入者が受け取り後に確認する項目を書いています。\n"
        "- RELEASE_MANIFEST.json と CHECKSUMS.txt で同梱ファイルを確認できます。\n"
        "\n"
        "アンインストール:\n"
        "- shortcuts\\uninstall-auto-note.bat を実行します。標準では記事と設定は残ります。\n"
    )


def _build_first_run_checklist() -> str:
    return (
        "auto-note First Run Checklist\n"
        "\n"
        "最初の10分で確認すること:\n"
        "\n"
        "[ ] 1. shortcuts\\install-auto-note.bat を実行した\n"
        "[ ] 2. デスクトップまたはスタートメニューの auto-note を開けた\n"
        "[ ] 3. GUIの セットアップ で既定タグと投稿ヘルパー設定を確認した\n"
        "[ ] 4. GUIの 自動修復 で基本フォルダ/設定の修復導線を確認した\n"
        "[ ] 5. GUIの 初回チェック と セルフテスト保存 を確認した\n"
        "[ ] 6. スターター一式 でサンプル記事、予定、アイデアを作った\n"
        "[ ] 7. 全体チェック と 記事レビュー を確認した\n"
        "[ ] 8. 投稿ヘルパー を開き、タイトル/本文/タグをコピーできることを確認した\n"
        "[ ] 9. 普段使うブラウザで note.com にログインした\n"
        "[ ] 10. バックアップ作成 を実行した\n"
        "[ ] 11. 困った時に ヘルプ > 問い合わせ一式 を作れることを確認した\n"
        "\n"
        "CLIで同じ確認をする場合:\n"
        "- auto-note setup --project-dir . --create\n"
        "- auto-note repair --project-dir . --apply\n"
        "- auto-note troubleshoot --project-dir .\n"
        "- auto-note acceptance --project-dir . --full\n"
        "- auto-note first-run --project-dir . --create --gui-smoke --smoke-helper\n"
        "- auto-note self-test --project-dir . --create --gui-smoke --report\n"
        "- auto-note action-plan --project-dir .\n"
        "- auto-note quickstart --project-dir .\n"
        "- auto-note starter-pack --project-dir .\n"
        "- auto-note starter-clean --project-dir .\n"
        "- auto-note gui --project-dir . --smoke\n"
        "- auto-note support --project-dir . --bundle\n"
        "\n"
        "GUIが開かない場合:\n"
        "- auto-note-gui.bat を直接開き、表示されたエラーを確認します。\n"
        "- .auto-note\\gui-error.log があればサポートへ共有できます。\n"
        "- docs\\SUPPORT.md の手順で問い合わせ一式を作成します。\n"
        "\n"
        "投稿で迷った場合:\n"
        "- 自動操作ブラウザではなく、普段使うブラウザでnoteにログインします。\n"
        "- 投稿ヘルパーのコピー操作でnote投稿画面へ貼り付けます。\n"
    )


def _build_buyer_acceptance_checklist() -> str:
    return (
        "auto-note Buyer Acceptance Checklist\n"
        "\n"
        "購入者が受け取り後に確認すること:\n"
        "\n"
        "[ ] 1. auto-note を開けた\n"
        "[ ] 2. セットアップ画面で既定タグと投稿ヘルパー設定を確認した\n"
        "[ ] 3. 受入チェックを実行し、NGがないことを確認した\n"
        "[ ] 4. スターター一式でサンプル記事、予定、アイデアを作成できた\n"
        "[ ] 5. 投稿キュー、運用サマリー、予定タブを確認できた\n"
        "[ ] 6. 投稿ヘルパーを開き、タイトル/本文/タグをコピーできた\n"
        "[ ] 7. 普段使うブラウザでnote.comにログインできた\n"
        "[ ] 8. バックアップ作成を実行できた\n"
        "[ ] 9. 困った時にヘルプから問い合わせ一式を作れる場所を確認した\n"
        "\n"
        "CLIで確認する場合:\n"
        "- auto-note acceptance --project-dir . --full\n"
        "- auto-note troubleshoot --project-dir .\n"
        "- auto-note first-run --project-dir . --create --gui-smoke --smoke-helper\n"
        "- auto-note support --project-dir . --bundle\n"
        "\n"
        "合格目安:\n"
        "- Acceptance check が BLOCKED ではない\n"
        "- GUI smoke が OK\n"
        "- Privacy audit が OK\n"
        "- noteログインは普段使うブラウザで行える\n"
    )


def _build_release_summary(project_dir: Path, created_at: datetime) -> str:
    metadata = _project_metadata(project_dir)
    return (
        "auto-note Release Summary\n"
        "\n"
        f"Name: {metadata['name']}\n"
        f"Version: {metadata['version']}\n"
        f"Created at: {created_at.isoformat(timespec='seconds')}\n"
        "Entrypoint: auto-note-gui.bat\n"
        "\n"
        "What to open first:\n"
        "- START_HERE.txt\n"
        "- FIRST_RUN_CHECKLIST.txt\n"
        "- BUYER_ACCEPTANCE_CHECKLIST.txt\n"
        "- shortcuts\\install-auto-note.bat\n"
        "- auto-note-gui.bat if you want to try without installing\n"
        "\n"
        "Privacy of this package:\n"
        "- User articles are not included.\n"
        "- Generated helper files are not included.\n"
        "- The local virtual environment is not included.\n"
        "\n"
        "Verification files:\n"
        "- RELEASE_MANIFEST.json lists packaged files and privacy flags.\n"
        "- CHECKSUMS.txt contains SHA-256 checksums for packaged files.\n"
        "\n"
        "Important docs:\n"
        "- docs\\INSTALL.md\n"
        "- docs\\UPDATE.md\n"
        "- docs\\SUPPORT.md\n"
        "- docs\\PRIVACY.md\n"
        "- docs\\THIRD_PARTY_NOTICES.md\n"
    )


def _release_verification_summary(package_path: Path) -> list[str]:
    try:
        with zipfile.ZipFile(package_path) as archive:
            manifest = json.loads(archive.read("RELEASE_MANIFEST.json").decode("utf-8"))
    except (OSError, KeyError, json.JSONDecodeError, UnicodeDecodeError, zipfile.BadZipFile):
        return ["Package summary: unavailable"]
    if not isinstance(manifest, dict):
        return ["Package summary: unavailable"]
    privacy = manifest.get("privacy")
    if not isinstance(privacy, dict):
        privacy = {}
    files = manifest.get("files") if isinstance(manifest, dict) else []
    file_count = manifest.get("file_count", len(files) if isinstance(files, list) else "?")
    return [
        "Package summary",
        f"- name: {manifest.get('name', 'unknown')}",
        f"- version: {manifest.get('version', 'unknown')}",
        f"- entrypoint: {manifest.get('entrypoint', 'unknown')}",
        f"- file_count: {file_count}",
        "- first run: START_HERE.txt, FIRST_RUN_CHECKLIST.txt, BUYER_ACCEPTANCE_CHECKLIST.txt",
        "Privacy flags",
        f"- includes_user_articles: {privacy.get('includes_user_articles')}",
        f"- includes_generated_helpers: {privacy.get('includes_generated_helpers')}",
        f"- includes_virtualenv: {privacy.get('includes_virtualenv')}",
    ]


def _build_checksums(records: list[dict[str, object]]) -> str:
    return "\n".join(f"{record['sha256']}  {record['path']}" for record in records) + "\n"


def _project_metadata(project_dir: Path) -> dict[str, str]:
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        return {"name": "auto-note", "version": "0.0.0"}
    text = pyproject.read_text(encoding="utf-8")
    name = _toml_string(text, "name") or "auto-note"
    version = _toml_string(text, "version") or "0.0.0"
    return {"name": name, "version": version}


def _toml_string(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*[\"']([^\"']+)[\"']", text)
    return match.group(1).strip() if match else ""
