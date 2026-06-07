from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .article import Article, ArticleError, body_with_tags, load_article
from .images import collect_article_images


LEVEL_ORDER = {"fix": 0, "improve": 1, "ok": 2}


@dataclass(frozen=True)
class ReviewItem:
    category: str
    level: str
    message: str
    action: str
    penalty: int = 0


@dataclass(frozen=True)
class ArticleReview:
    article: Article
    score: int
    items: list[ReviewItem]

    @property
    def ready(self) -> bool:
        return self.score >= 80 and not any(item.level == "fix" for item in self.items)

    @property
    def needs_fix(self) -> bool:
        return any(item.level == "fix" for item in self.items)


def review_article(article: Article, *, append_tags: bool = False) -> ArticleReview:
    body = body_with_tags(article) if append_tags else article.body
    items: list[ReviewItem] = []

    _review_title(article, items)
    _review_summary(article, items)
    _review_body(article, body, items)
    _review_structure(body, items)
    _review_opening(body, items)
    _review_ending(body, items)
    _review_tags(article, items)
    _review_images(article, items)
    _review_workflow(article, items)

    score = max(0, 100 - sum(item.penalty for item in items))
    items.sort(key=lambda item: (LEVEL_ORDER.get(item.level, 9), item.category))
    return ArticleReview(article=article, score=score, items=items)


def review_path(path: Path, *, pattern: str = "*.md", append_tags: bool = False) -> list[ArticleReview]:
    files = _collect_markdown_files(path, pattern)
    if not files:
        raise ArticleError(f"No markdown files found in {path}.")
    return [review_article(load_article(file), append_tags=append_tags) for file in files]


def format_review_report(reviews: list[ArticleReview], *, include_private: bool = True) -> str:
    if not reviews:
        return "記事レビュー対象がありません。"

    lines: list[str] = []
    if len(reviews) > 1:
        average = round(sum(review.score for review in reviews) / len(reviews))
        fix_count = sum(1 for review in reviews if review.needs_fix)
        ready_count = sum(1 for review in reviews if review.ready)
        lines.append("Article review summary")
        lines.append(f"Average score: {average}/100")
        lines.append(f"Ready: {ready_count} / Needs fix: {fix_count} / Total: {len(reviews)}")
        lines.append("")

    for index, review in enumerate(reviews, start=1):
        article = review.article
        state = "READY" if review.ready else "NEEDS WORK"
        if include_private:
            source = str(article.source)
            title = article.title
            tags = ", ".join(article.tags) if article.tags else "(none)"
        else:
            source = f"article-{index:03d}.md"
            title = f"<title:{len(article.title)} chars>"
            tags = f"{len(article.tags)} tag(s)"
        lines.append(f"Article review: {source}")
        lines.append(f"Score: {review.score}/100 [{state}]")
        lines.append(f"Title: {title}")
        lines.append(f"Status: {article.status} / Tags: {tags}")
        lines.append("")
        for item in review.items:
            label = {"fix": "FIX", "improve": "IMPROVE", "ok": "OK"}.get(item.level, item.level.upper())
            lines.append(f"[{label}] {item.category}: {item.message}")
            if item.action:
                lines.append(f"  next: {item.action}")
        lines.append("")
    return "\n".join(lines).rstrip()


def has_review_blockers(reviews: list[ArticleReview], *, strict: bool = False) -> bool:
    if any(review.needs_fix for review in reviews):
        return True
    return strict and any(item.level == "improve" for review in reviews for item in review.items)


def _review_title(article: Article, items: list[ReviewItem]) -> None:
    title = article.title.strip()
    if _looks_placeholder(title):
        _add(items, "タイトル", "fix", "仮タイトルのように見えます。", "読者が得られる変化や具体テーマを入れます。", 16)
    elif len(title) < 12:
        _add(items, "タイトル", "improve", "タイトルが短めです。", "誰向けか、何が得られるかを1語足します。", 7)
    elif len(title) > 60:
        _add(items, "タイトル", "improve", "タイトルが長めです。", "note一覧で読めるよう、主語と約束を絞ります。", 7)
    else:
        _add(items, "タイトル", "ok", "一覧で内容を想像しやすい長さです。", "")


def _review_summary(article: Article, items: list[ReviewItem]) -> None:
    summary = article.summary.strip()
    if not summary:
        _add(items, "概要", "improve", "概要が未設定です。", "40-120文字で、誰に何を届ける記事かを書きます。", 8)
    elif len(summary) > 140:
        _add(items, "概要", "improve", "概要が長めです。", "検索や共有で見える前提で、結論を1文に圧縮します。", 4)
    else:
        _add(items, "概要", "ok", "共有時に使いやすい概要があります。", "")


def _review_body(article: Article, body: str, items: list[ReviewItem]) -> None:
    length = len(_plain_text(body))
    if _looks_placeholder(body):
        _add(items, "本文", "fix", "本文にテンプレート文や未処理メモが残っています。", "「ここに」「TODO」「要確認」などを本文に置き換えます。", 18)
    elif length < 400:
        _add(items, "本文", "fix", "本文量がかなり少なめです。", "背景、具体例、読者が次にできることを足します。", 18)
    elif length < 800:
        _add(items, "本文", "improve", "本文量がやや少なめです。", "体験談、比較、失敗例、チェックリストのどれかを足します。", 8)
    else:
        _add(items, "本文", "ok", "本文量は公開前レビューに耐える水準です。", "")


def _review_structure(body: str, items: list[ReviewItem]) -> None:
    headings = re.findall(r"^#{2,3}\s+(.+?)\s*$", body, flags=re.MULTILINE)
    if not headings:
        _add(items, "構成", "improve", "本文見出しがありません。", "2-4個の見出しに分けて、流し読みできる形にします。", 10)
    elif len(headings) == 1:
        _add(items, "構成", "improve", "本文見出しが1つだけです。", "導入、具体例、まとめなどに分けます。", 5)
    else:
        _add(items, "構成", "ok", f"見出しが{len(headings)}個あり、読み進めやすい構成です。", "")


def _review_opening(body: str, items: list[ReviewItem]) -> None:
    opening = _first_paragraph(body)
    if len(opening) < 35:
        _add(items, "導入", "improve", "冒頭のつかみが短めです。", "読者の悩み、結論、この記事で得られることを冒頭に置きます。", 6)
    elif re.search(r"(この記事|今回は|本記事).*(わかる|紹介|解説|まとめ)", opening):
        _add(items, "導入", "ok", "冒頭で記事の約束が伝わります。", "")
    else:
        _add(items, "導入", "improve", "冒頭の約束が少し弱いかもしれません。", "最初の段落に「誰が何を得られるか」を明記します。", 5)


def _review_ending(body: str, items: list[ReviewItem]) -> None:
    tail = _plain_text(body[-900:])
    if re.search(r"(まとめ|最後に|結論|次に|試して|コメント|フォロー|スキ|シェア|相談|登録|購入|参加)", tail):
        _add(items, "締め", "ok", "締めに要約または次の行動が入っています。", "")
    else:
        _add(items, "締め", "improve", "読後の行動が弱めです。", "最後に要点の再掲、質問、次に試す行動のどれかを入れます。", 6)


def _review_tags(article: Article, items: list[ReviewItem]) -> None:
    count = len(article.tags)
    if count == 0:
        _add(items, "タグ", "fix", "タグがありません。", "読者が探す言葉を2-5個入れます。", 10)
    elif count == 1:
        _add(items, "タグ", "improve", "タグが1個だけです。", "テーマ、読者、用途をそれぞれ1つずつ足します。", 5)
    elif count > 8:
        _add(items, "タグ", "improve", "タグが多めです。", "主題に近いタグを5-8個程度に絞ります。", 5)
    else:
        _add(items, "タグ", "ok", f"タグが{count}個あり、発見されやすい状態です。", "")


def _review_images(article: Article, items: list[ReviewItem]) -> None:
    refs = collect_article_images(article)
    missing = [ref for ref in refs if not ref.ok]
    large = [ref for ref in refs if ref.large]
    if missing:
        _add(items, "画像", "fix", f"見つからない画像が{len(missing)}件あります。", "画像パスを直すか、画像挿入機能で取り込み直します。", 20)
    elif large:
        _add(items, "画像", "improve", f"大きめの画像が{len(large)}件あります。", "画像最適化を使って表示とアップロードを軽くします。", 5)
    elif refs:
        _add(items, "画像", "ok", f"画像参照が{len(refs)}件あり、欠落はありません。", "")
    else:
        _add(items, "画像", "improve", "カバー画像や本文画像がありません。", "一覧で目に留まるカバー画像を1枚用意すると強くなります。", 5)


def _review_workflow(article: Article, items: list[ReviewItem]) -> None:
    if article.status == "scheduled" and not article.scheduled:
        _add(items, "公開状態", "fix", "予定ありなのに公開予定日時が空です。", "予定タブで日時を入れるか、状態を下書きに戻します。", 12)
    elif article.status == "published" and not article.published_url:
        _add(items, "公開状態", "improve", "公開済みですがURLが未記録です。", "公開後のnote URLを保存して管理しやすくします。", 4)
    elif article.status in {"ready", "scheduled", "published"}:
        _add(items, "公開状態", "ok", f"状態が {article.status} に整理されています。", "")
    else:
        _add(items, "公開状態", "improve", "まだ下書き状態です。", "レビュー後に問題なければ「準備OK」へ進めます。", 5)


def _add(
    items: list[ReviewItem],
    category: str,
    level: str,
    message: str,
    action: str,
    penalty: int = 0,
) -> None:
    items.append(ReviewItem(category=category, level=level, message=message, action=action, penalty=penalty))


def _collect_markdown_files(path: Path, pattern: str) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(file for file in path.glob(pattern) if file.is_file())


def _plain_text(markdown: str) -> str:
    text = re.sub(r"```.*?```", "", markdown, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*]\([^)]+\)", "", text)
    text = re.sub(r"\[[^\]]+]\([^)]+\)", "", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_`>#-]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _first_paragraph(body: str) -> str:
    cleaned: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            if cleaned:
                break
            continue
        if stripped.startswith("#"):
            continue
        cleaned.append(stripped)
    return _plain_text(" ".join(cleaned))


def _looks_placeholder(text: str) -> bool:
    return bool(re.search(r"(TODO|FIXME|ここに|下書き|要確認|仮タイトル|未定)", text, flags=re.IGNORECASE))
