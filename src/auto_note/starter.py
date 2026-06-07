from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .article import ArticleError, load_article, write_text_atomic
from .scaffold import slugify
from .workflow import add_idea, export_calendar, load_ideas, save_ideas


@dataclass(frozen=True)
class StarterPackResult:
    project_dir: Path
    articles: list[Path]
    skipped_articles: list[Path]
    idea_added: bool
    idea_title: str
    calendar_path: Path | None = None
    calendar_events: int = 0


@dataclass(frozen=True)
class StarterCleanupResult:
    project_dir: Path
    articles: list[Path]
    idea_matched: bool
    idea_title: str
    dry_run: bool = True


@dataclass(frozen=True)
class StarterArticle:
    title: str
    summary: str
    tags: list[str]
    status: str
    slug: str
    body: str
    scheduled: str = ""


STARTER_IDEA_TITLE = "読者からよく聞かれる質問を、1問1答の記事にする"


def create_starter_pack(
    project_dir: Path,
    *,
    articles_dir: Path | None = None,
    include_calendar: bool = True,
) -> StarterPackResult:
    project_dir = project_dir.resolve()
    target_dir = articles_dir or (project_dir / "articles")
    if not target_dir.is_absolute():
        target_dir = project_dir / target_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    skipped: list[Path] = []
    for spec in _starter_articles():
        existing = _find_existing_article(target_dir, spec)
        if existing:
            skipped.append(existing)
            continue
        path = _next_article_path(target_dir, spec.slug)
        write_text_atomic(path, _article_text(spec))
        created.append(path)

    idea_added = _add_starter_idea(project_dir)
    calendar_path: Path | None = None
    calendar_events = 0
    if include_calendar:
        result = export_calendar(project_dir, target_dir, days=90)
        calendar_path = result.path
        calendar_events = result.event_count

    return StarterPackResult(
        project_dir=project_dir,
        articles=created,
        skipped_articles=skipped,
        idea_added=idea_added,
        idea_title=STARTER_IDEA_TITLE,
        calendar_path=calendar_path,
        calendar_events=calendar_events,
    )


def format_starter_pack_result(result: StarterPackResult) -> str:
    lines = [
        "Starter pack / スターター一式",
        f"Articles: {len(result.articles)} created, {len(result.skipped_articles)} already present",
    ]
    for path in result.articles:
        lines.append(f"- created: {path}")
    for path in result.skipped_articles:
        lines.append(f"- skipped: {path}")
    lines.append(f"Idea: {'added' if result.idea_added else 'already exists'}")
    lines.append(f"- {result.idea_title}")
    if result.calendar_path:
        lines.append(f"Calendar: {result.calendar_path} ({result.calendar_events} event(s))")
    else:
        lines.append("Calendar: skipped")
    lines.extend(
        [
            "",
            "Next actions",
            "- GUIの運用サマリーで、次に投稿する記事と公開予定を確認します。",
            "- 投稿キューで、POSTABLE / CHECK / BLOCKED の見え方を確認します。",
            "- 予定ICSをGoogle/Outlookへ取り込む場合は、必要に応じてタイトル入りICSを作り直します。",
        ]
    )
    return "\n".join(lines)


def cleanup_starter_pack(
    project_dir: Path,
    *,
    articles_dir: Path | None = None,
    dry_run: bool = True,
) -> StarterCleanupResult:
    project_dir = project_dir.resolve()
    target_dir = articles_dir or (project_dir / "articles")
    if not target_dir.is_absolute():
        target_dir = project_dir / target_dir

    article_paths = _find_starter_article_paths(target_dir)
    ideas = load_ideas(project_dir)
    remaining_ideas = [idea for idea in ideas if not _is_removable_starter_idea(idea)]
    idea_matched = len(remaining_ideas) != len(ideas)

    if not dry_run:
        for path in article_paths:
            path.unlink(missing_ok=True)
        if idea_matched:
            save_ideas(project_dir, remaining_ideas)

    return StarterCleanupResult(
        project_dir=project_dir,
        articles=article_paths,
        idea_matched=idea_matched,
        idea_title=STARTER_IDEA_TITLE,
        dry_run=dry_run,
    )


def format_starter_cleanup_result(result: StarterCleanupResult) -> str:
    action = "Preview" if result.dry_run else "Applied"
    lines = [
        f"Starter cleanup / スターター整理 ({action})",
        f"Articles: {len(result.articles)} {'would be removed' if result.dry_run else 'removed'}",
    ]
    for path in result.articles:
        lines.append(f"- {path}")
    idea_state = "would be removed" if result.dry_run else "removed"
    lines.append(f"Idea: {idea_state if result.idea_matched else 'not found or already promoted'}")
    lines.append(f"- {result.idea_title}")
    if not result.articles and not result.idea_matched:
        lines.extend(["", "Nothing to remove."])
    elif result.dry_run:
        lines.extend(
            [
                "",
                "Apply",
                "- CLIでは `auto-note starter-clean --project-dir . --apply` を実行します。",
                "- GUIでは スターター整理 を実行して確認ダイアログで続行します。",
            ]
        )
    return "\n".join(lines)


def _starter_articles() -> list[StarterArticle]:
    scheduled_at = (datetime.now() + timedelta(days=2)).replace(hour=9, minute=0, second=0, microsecond=0)
    return [
        StarterArticle(
            title="note投稿を続けるための週次ワークフロー",
            summary="記事作成、確認、予定管理、公開後の記録までを週1回の流れにまとめるサンプル記事です。",
            tags=["note", "発信", "習慣化", "ワークフロー"],
            status="ready",
            slug="starter-weekly-workflow",
            body=_WEEKLY_WORKFLOW_BODY,
        ),
        StarterArticle(
            title="公開前チェックで見落としを減らす方法",
            summary="タイトル、概要、本文、タグ、画像、公開状態を投稿前に見直すためのサンプル手順です。",
            tags=["文章術", "note", "チェックリスト", "投稿準備"],
            status="scheduled",
            scheduled=scheduled_at.strftime("%Y-%m-%d %H:%M"),
            slug="starter-prepublish-check",
            body=_PREPUBLISH_CHECK_BODY,
        ),
        StarterArticle(
            title="来週の発信テーマを決めるためのメモ",
            summary="アイデアを記事に育てる前に、読者、悩み、結論、具体例を整理するためのサンプルです。",
            tags=["アイデア", "編集", "note"],
            status="draft",
            slug="starter-topic-planning",
            body=_TOPIC_PLANNING_BODY,
        ),
    ]


def _next_article_path(articles_dir: Path, slug: str) -> Path:
    base = articles_dir / f"{datetime.now():%Y-%m-%d}-{slugify(slug)}.md"
    if not base.exists():
        return base
    for index in range(2, 1000):
        candidate = base.with_name(f"{base.stem}-{index}{base.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Could not create a starter article name in {articles_dir}.")


def _find_existing_article(articles_dir: Path, spec: StarterArticle) -> Path | None:
    slug = slugify(spec.slug)
    for path in sorted(articles_dir.glob("*.md")):
        if slug in path.stem:
            return path
    for path in sorted(articles_dir.glob("*.md")):
        try:
            article = load_article(path)
        except (ArticleError, OSError):
            continue
        if article.title == spec.title:
            return path
    return None


def _find_starter_article_paths(articles_dir: Path) -> list[Path]:
    if not articles_dir.exists():
        return []
    specs = _starter_articles()
    slugs = {slugify(spec.slug) for spec in specs}
    titles = {spec.title for spec in specs}
    matched: dict[str, Path] = {}
    for path in sorted(articles_dir.glob("*.md")):
        if any(slug in path.stem for slug in slugs):
            matched[str(path)] = path
            continue
        try:
            article = load_article(path)
        except (ArticleError, OSError):
            continue
        if article.title in titles:
            matched[str(path)] = path
    return list(matched.values())


def _is_removable_starter_idea(idea) -> bool:
    return idea.title == STARTER_IDEA_TITLE and not idea.promoted_to


def _article_text(spec: StarterArticle) -> str:
    tag_lines = "\n".join(f"  - {_yaml_string(tag)}" for tag in spec.tags)
    return (
        "---\n"
        f"title: {_yaml_string(spec.title)}\n"
        f"summary: {_yaml_string(spec.summary)}\n"
        "tags:\n"
        f"{tag_lines}\n"
        f"status: {spec.status}\n"
        f"scheduled: {_yaml_string(spec.scheduled) if spec.scheduled else ''}\n"
        "publish: false\n"
        "---\n\n"
        f"{spec.body.strip()}\n"
    )


def _add_starter_idea(project_dir: Path) -> bool:
    existing = {idea.title for idea in load_ideas(project_dir)}
    if STARTER_IDEA_TITLE in existing:
        return False
    add_idea(
        project_dir,
        STARTER_IDEA_TITLE,
        note="問い合わせやコメント欄の質問を1つ選び、背景、答え、具体例、次の行動に分けて記事化する。",
        tags=["note", "読者理解"],
    )
    return True


def _yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


_WEEKLY_WORKFLOW_BODY = """
この記事では、note投稿を無理なく続けたい人に向けて、週1回の作業で記事作成、確認、公開予定、公開後の記録まで進める流れをまとめます。毎日がんばる前提ではなく、迷う時間を減らして投稿のリズムを作ることを目的にします。

## 月曜にテーマを決める

最初にやることは、書きたいことを広げるよりも、今週届けたい読者を一人に絞ることです。たとえば「noteを始めたけれど投稿前に不安になる人」のように具体化すると、タイトル、導入、タグまで決めやすくなります。テーマが複数ある場合は、読者の困りごとが一番はっきりしているものを先に選びます。

テーマを決めたら、結論を一文で書きます。結論が曖昧なまま本文を書き始めると、途中で構成が散らばりやすくなります。「公開前チェックを型にすると、投稿前の不安を減らせる」のように、読後の変化が見える形にしておくと便利です。

## 水曜に原稿を整える

本文は、導入、具体例、手順、まとめの順で分けると読みやすくなります。導入では読者の悩みを先に置き、本文では自分の経験や判断基準を入れます。一般論だけで終わらせず、「自分ならどう使うか」を足すと、記事の温度が出ます。

auto-noteでは、記事を選んで投稿準備パネルを見ると、チェック、レビュー、工程状態、投稿ヘルパー生成の状態をまとめて確認できます。点数が低い場合も、失敗ではなく修正順が見えた状態です。改善プランを開き、必須修正、仕上げ、投稿前確認の順に直すと、手戻りを減らせます。

## 金曜に公開予定を入れる

記事が整ったら、状態を準備OKまたは予定ありにします。公開予定を入れておくと、運用サマリーで次に見るべき記事がわかりやすくなります。外部カレンダーで管理したい場合は予定ICSを出力し、Google CalendarやOutlookへ取り込むと、投稿作業を普段の予定と同じ場所で見られます。

公開後はURLを保存します。URLを残しておくと、あとで記事一覧から公開済みの記事を確認しやすくなります。投稿したら終わりではなく、次の記事のテーマや読者の反応もアイデア箱に残しておくと、翌週のスタートが軽くなります。

## 最後に

続けるコツは、気合いよりも迷わない順番を作ることです。テーマを決める、原稿を整える、公開予定を入れる、公開後に記録する。この流れを一度作っておけば、次に書く時も同じリズムで始められます。
"""


_PREPUBLISH_CHECK_BODY = """
この記事では、公開直前に何を確認すればよいか迷う人に向けて、note記事の見落としを減らすチェック方法をまとめます。文章の完成度だけではなく、タイトル、概要、タグ、画像、公開状態まで見ることで、投稿前の不安を小さくできます。

## タイトルと概要を見る

タイトルは、読者が一覧で見た時に「自分向けだ」とわかることが大切です。短すぎるタイトルは内容が伝わりにくく、長すぎるタイトルは約束がぼやけます。誰に、何を、どんな変化として届けるのかを一つ入れると、クリック前の期待が揃います。

概要は、検索や共有で見えた時の案内文です。本文の一部をそのまま置くよりも、読者の悩みと記事で得られることを一文にすると使いやすくなります。概要が空のままだと、記事の管理画面でも内容を思い出しにくくなります。

## 本文の入口と出口を見る

導入では、読者の悩み、この記事で扱うこと、読むと得られる変化を早めに伝えます。本文が良くても、入口で何の記事かわからないと読み進めてもらいにくくなります。最初の段落だけ読み返して、記事の約束が伝わるかを確認します。

最後の段落では、要点をもう一度まとめ、次に試してほしい行動を置きます。たとえば「次の記事では、公開前にタイトル、概要、タグだけでも確認してみてください」のように、読後の一歩があると記事の印象が残ります。

## タグと画像を見る

タグは多ければよいわけではありません。主題、読者、用途の三方向から二つから五つ程度に絞ると、記事の狙いがぶれにくくなります。タグが一つだけの場合は、読者が探しそうな言葉を一つ足してみます。

画像は必須ではありませんが、カバー画像や本文画像があると一覧で目に留まりやすくなります。ローカル画像を使う場合は、パスが切れていないかも確認します。画像挿入機能を使うと、記事の近くに画像を置けるので、移動後の欠落を減らせます。

## 最後に

公開前チェックは、記事を止めるためのものではありません。安心して公開するための確認リストです。タイトル、概要、導入、締め、タグ、画像、公開状態を順番に見るだけで、投稿前の迷いはかなり減らせます。
"""


_TOPIC_PLANNING_BODY = """
この記事では、来週の発信テーマを決める前に、読者、悩み、結論、具体例を整理する方法をまとめます。まだ構想段階の記事として、アイデアをいきなり本文にする前のメモの作り方を確認できます。

## 読者を一人に絞る

発信テーマを考える時は、最初に読者を広げすぎないことが大切です。「noteを書く人」ではなく、「投稿前に毎回不安になって原稿が増える人」のように具体化します。読者がはっきりすると、必要な説明と不要な説明が分けやすくなります。

読者を一人に絞ることは、読者を減らすことではありません。むしろ、具体的な悩みに届く文章の方が、似た状況にいる人にも伝わります。テーマに迷ったら、最近の自分が困ったこと、読者から聞かれたこと、何度も説明していることを候補にします。

## 結論を先に置く

テーマを選んだら、結論を先に書きます。結論は完璧でなくても構いません。「投稿を続けるには、毎回の気合いよりも確認の型が必要」のように、記事全体の方向がわかる一文を置きます。

結論があると、見出しも作りやすくなります。背景、理由、具体例、手順、まとめのどれが必要かを選べるからです。逆に結論がないまま書き始めると、途中で別の話題に流れてしまうことがあります。

## 具体例を一つ入れる

読者に伝わる記事には、具体例があります。操作手順、失敗した場面、改善前後の違い、チェックリストなど、読者が自分の状況に置き換えられる材料を一つ入れます。具体例は長くなくてもよく、判断の理由が見えることが大切です。

auto-noteのアイデア箱には、まだ本文にする前のテーマを残せます。すぐ記事化しないものも、タイトル、メモ、タグだけ入れておくと、後で見返した時に再開しやすくなります。

## 最後に

テーマ決めで迷った時は、読者、悩み、結論、具体例の四つだけを埋めてみてください。全部を完成させようとせず、次に書き出せる状態にすることが目的です。来週の記事は、このメモをもとに一つだけ原稿へ進めます。
"""
