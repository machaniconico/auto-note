from __future__ import annotations

from pathlib import Path
import os
import sys
import webbrowser

from .article import Article, ArticleError, body_with_tags, load_article
from .clipboard import write_clipboard
from .inspect import format_reports, inspect_path
from .manual import NOTE_LOGIN_URL, open_manual_dashboard, open_manual_post_helper
from .scaffold import create_article
from .workflow import (
    add_idea,
    format_calendar,
    format_ideas,
    format_plan,
    mark_article_published,
    promote_idea,
    set_article_schedule,
    set_article_status,
)


def run_menu(project_dir: Path, *, initial_file: Path | None = None) -> int:
    project_dir = _clean_path(project_dir)
    project_dir = project_dir.resolve()
    articles_dir = project_dir / "articles"
    output_dir = project_dir / ".auto-note"

    if initial_file:
        return _open_helper(initial_file, output_dir)

    while True:
        _clear_screen()
        print("auto-note")
        print("=" * 32)
        print("1. 新しい記事を作る")
        print("2. 記事フォルダを開く")
        print("3. 公開前チェック")
        print("4. 記事一覧ダッシュボード")
        print("5. 投稿ヘルパーを開く")
        print("6. noteログイン画面を開く")
        print("7. 本文をコピー")
        print("8. 工程と公開予定を見る")
        print("9. 記事を公開予定にする")
        print("10. 記事を公開済みにする")
        print("11. アイデアを追加")
        print("12. アイデアを記事にする")
        print("13. 終了")
        print()
        choice = input("番号を入力: ").strip().lower()

        try:
            if choice == "1":
                _new_article(articles_dir)
            elif choice == "2":
                articles_dir.mkdir(parents=True, exist_ok=True)
                _open_path(articles_dir)
            elif choice == "3":
                _check_articles(articles_dir)
            elif choice == "4":
                open_manual_dashboard(
                    articles_dir,
                    pattern="*.md",
                    append_tags=True,
                    output_dir=output_dir,
                )
            elif choice == "5":
                article = _select_article(articles_dir)
                if article:
                    _open_helper(article.source, output_dir)
            elif choice == "6":
                webbrowser.open(NOTE_LOGIN_URL)
            elif choice == "7":
                article = _select_article(articles_dir)
                if article:
                    write_clipboard(body_with_tags(article))
                    print(f"copied: {article.source}")
                    _pause()
            elif choice == "8":
                _show_plan(articles_dir)
            elif choice == "9":
                _schedule_article(articles_dir)
            elif choice == "10":
                _mark_published(articles_dir)
            elif choice == "11":
                _add_idea(project_dir)
            elif choice == "12":
                _promote_idea(project_dir, articles_dir)
            elif choice in {"13", "q", "quit", "exit"}:
                return 0
            else:
                print("番号を選んでください。")
                _pause()
        except (ArticleError, RuntimeError, OSError) as exc:
            print(f"error: {exc}")
            _pause()


def _new_article(articles_dir: Path) -> None:
    print()
    title = input("記事タイトル: ").strip()
    if not title:
        print("タイトルが空です。")
        _pause()
        return

    raw_tags = input("タグ カンマ区切り、省略可: ").strip()
    tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    path = create_article(title, articles_dir=articles_dir, tags=tags)
    print(f"created: {path}")
    _open_path(path)
    _pause()


def _check_articles(articles_dir: Path) -> None:
    print()
    reports = inspect_path(articles_dir, pattern="*.md", append_tags=True)
    print(format_reports(reports))
    _pause()


def _show_plan(articles_dir: Path) -> None:
    print()
    print(format_plan(articles_dir, pattern="*.md"))
    print()
    print(format_calendar(articles_dir, pattern="*.md", days=30))
    _pause()


def _schedule_article(articles_dir: Path) -> None:
    article = _select_article(articles_dir)
    if not article:
        return
    raw = input("公開予定 YYYY-MM-DD HH:MM: ").strip()
    if not raw:
        return
    set_article_schedule(article.source, raw)
    print(f"scheduled: {article.source} -> {raw}")
    _pause()


def _mark_published(articles_dir: Path) -> None:
    article = _select_article(articles_dir)
    if not article:
        return
    url = input("公開URL、省略可: ").strip()
    mark_article_published(article.source, url=url)
    print(f"published: {article.source}")
    _pause()


def _add_idea(project_dir: Path) -> None:
    print()
    title = input("アイデア: ").strip()
    if not title:
        return
    note = input("メモ、省略可: ").strip()
    raw_tags = input("タグ カンマ区切り、省略可: ").strip()
    tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    idea = add_idea(project_dir, title, note=note, tags=tags)
    print(f"idea added: {idea.id}. {idea.title}")
    _pause()


def _promote_idea(project_dir: Path, articles_dir: Path) -> None:
    print()
    print(format_ideas(project_dir))
    print()
    raw = input("記事にするアイデア番号、Enterでキャンセル: ").strip()
    if not raw:
        return
    try:
        idea_id = int(raw)
    except ValueError:
        print("番号を入力してください。")
        _pause()
        return
    path = promote_idea(project_dir, idea_id, articles_dir=articles_dir)
    set_article_status(path, "draft")
    print(f"created: {path}")
    _open_path(path)
    _pause()


def _open_helper(path: Path, output_dir: Path) -> int:
    article = load_article(path)
    helper_path = open_manual_post_helper(
        article,
        append_tags=True,
        output_dir=output_dir,
        open_note=True,
        open_helper=True,
    )
    print(f"opened helper: {helper_path}")
    return 0


def _select_article(articles_dir: Path) -> Article | None:
    articles_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(
        articles_dir.glob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        print("記事ファイルがありません。先に新しい記事を作ってください。")
        _pause()
        return None

    articles: list[Article] = []
    for file in files:
        try:
            articles.append(load_article(file))
        except ArticleError:
            continue

    if not articles:
        print("読み込める記事ファイルがありません。")
        _pause()
        return None

    print()
    print("記事を選択")
    print("-" * 32)
    for index, article in enumerate(articles, start=1):
        print(f"{index}. {article.title}")
        print(f"   {article.source}")
    print()
    raw = input("番号を入力、Enterでキャンセル: ").strip()
    if not raw:
        return None
    try:
        selected = int(raw)
    except ValueError:
        print("番号を入力してください。")
        _pause()
        return None
    if selected < 1 or selected > len(articles):
        print("範囲外です。")
        _pause()
        return None
    return articles[selected - 1]


def _open_path(path: Path) -> None:
    resolved = path.resolve()
    if sys.platform.startswith("win"):
        os.startfile(resolved)  # type: ignore[attr-defined]
    else:
        webbrowser.open(resolved.as_uri())


def _clean_path(path: Path) -> Path:
    value = str(path).strip().strip('"').strip("'")
    return Path(value)


def _clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _pause() -> None:
    print()
    input("Enterで戻る...")
