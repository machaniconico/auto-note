from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import unicodedata

from .article import write_text_atomic


ARTICLE_TEMPLATES: dict[str, tuple[str, str]] = {
    "standard": (
        "標準",
        "## 導入\n\nここに導入を書きます。\n\n"
        "## 本文\n\nここに本文を書きます。\n\n"
        "## まとめ\n\nここにまとめを書きます。\n",
    ),
    "howto": (
        "手順・解説",
        "## この記事でわかること\n\n- \n\n"
        "## 背景\n\n\n"
        "## 手順\n\n1. \n2. \n3. \n\n"
        "## つまずきやすい点\n\n\n"
        "## まとめ\n\n",
    ),
    "review": (
        "レビュー",
        "## 結論\n\n\n"
        "## 使った理由\n\n\n"
        "## よかった点\n\n- \n\n"
        "## 気になった点\n\n- \n\n"
        "## どんな人に向いているか\n\n\n"
        "## まとめ\n\n",
    ),
    "announcement": (
        "告知",
        "## お知らせ\n\n\n"
        "## 概要\n\n\n"
        "## 対象者\n\n\n"
        "## 日時・場所・リンク\n\n\n"
        "## 申し込み方法\n\n\n"
        "## 最後に\n\n",
    ),
    "diary": (
        "日記・振り返り",
        "## 今日の出来事\n\n\n"
        "## 考えたこと\n\n\n"
        "## よかったこと\n\n\n"
        "## 次にやること\n\n",
    ),
}

PRACTICE_ARTICLE_TITLE = "auto-noteで初回投稿を練習する実践チェックリスト"
PRACTICE_ARTICLE_BODY = """この記事では、auto-noteを初めて使う人が、記事作成から投稿ヘルパーまでの流れを一度で確認できるように、短いチェックリスト形式で手順をまとめます。操作を覚える目的の記事なので、公開する前に自分の言葉や体験に置き換えると、そのまま発信の練習にも使えます。

## まず全体の流れをつかむ

auto-noteの基本は、Markdownで記事を作り、公開前チェックで不足を見つけ、投稿ヘルパーでnoteの投稿画面へ貼り付ける流れです。自動操作ブラウザでログインが弾かれる環境でも、普段使っているChromeやEdgeでnoteにログインし、ヘルパーからコピーして進められます。最初の目的は完璧な記事を書くことではなく、迷わず一連の操作を通せる状態にすることです。

## 記事を整える

タイトルは、誰に何を届ける記事なのかが伝わる形にします。概要には、検索や共有で見た人が内容を想像できる一文を入れます。本文は、導入、具体例、まとめの順に分けると読みやすくなります。タグは主題、読者、用途を意識して二つから五つ程度に絞ると、管理もしやすくなります。

## 投稿前に確認する

GUIの全体チェックでは、文字数、タグ、画像、公開予定などの基本的な抜けを確認できます。チェックタブのレビュー一覧では、タイトル、概要、導入、締め、タグ、画像、公開状態をスコアで見られます。警告が出た場合は、すぐ公開する合図ではなく、改善の優先順位を教えてくれるメモとして使うと便利です。

## 投稿ヘルパーを試す

投稿ヘルパーを開くと、タイトル、本文、タグをコピーしやすい画面が生成されます。note側の画面は通常ブラウザで開き、ログイン済みの状態で貼り付けます。公開前には、noteのプレビューで改行、見出し、リンク、画像を確認します。公開したら、auto-noteに公開URLを保存しておくと、あとで記事一覧から管理できます。

## 最後に

この練習記事で一度流れを確認したら、次は自分のテーマで新しい記事を作成してみてください。作成、確認、投稿ヘルパー、公開URL保存、バックアップまで通せれば、日々の投稿作業を安心して繰り返せるようになります。
"""


def create_article(
    title: str,
    *,
    articles_dir: Path,
    tags: list[str] | None = None,
    slug: str | None = None,
    force: bool = False,
    template: str = "standard",
) -> Path:
    articles_dir.mkdir(parents=True, exist_ok=True)
    clean_title = title.strip() or "無題の記事"
    filename = f"{datetime.now():%Y-%m-%d}-{slugify(slug or clean_title)}.md"
    path = articles_dir / filename

    if path.exists() and not force:
        path = _next_available_path(path)

    write_text_atomic(path, _article_template(clean_title, tags or [], template=template))
    return path


def create_practice_article(*, articles_dir: Path, force: bool = False) -> Path:
    articles_dir.mkdir(parents=True, exist_ok=True)
    path = articles_dir / f"{datetime.now():%Y-%m-%d}-auto-note-practice.md"
    if path.exists() and not force:
        path = _next_available_path(path)
    write_text_atomic(path, _practice_article_template())
    return path


def list_article_templates() -> list[tuple[str, str]]:
    return [(key, value[0]) for key, value in ARTICLE_TEMPLATES.items()]


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug or "note"


def _next_available_path(path: Path) -> Path:
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Could not find available filename for {path}.")


def _article_template(title: str, tags: list[str], *, template: str = "standard") -> str:
    tag_lines = "\n".join(f"  - {_yaml_string(tag)}" for tag in tags if tag.strip())
    if not tag_lines:
        tag_lines = "  - note"
    body = ARTICLE_TEMPLATES.get(template, ARTICLE_TEMPLATES["standard"])[1]

    return (
        "---\n"
        f"title: {_yaml_string(title)}\n"
        "summary: \n"
        "tags:\n"
        f"{tag_lines}\n"
        "status: draft\n"
        "scheduled: \n"
        "publish: false\n"
        "---\n\n"
        f"{body}"
    )


def _practice_article_template() -> str:
    return (
        "---\n"
        f"title: {_yaml_string(PRACTICE_ARTICLE_TITLE)}\n"
        "summary: \"auto-noteの作成、確認、投稿ヘルパー、公開URL保存までを一度で試せる初回練習用の記事です。\"\n"
        "tags:\n"
        "  - note\n"
        "  - auto-note\n"
        "  - 投稿準備\n"
        "  - 文章術\n"
        "status: draft\n"
        "scheduled: \n"
        "publish: false\n"
        "---\n\n"
        f"{PRACTICE_ARTICLE_BODY}\n"
    )


def _yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
