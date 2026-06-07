from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .commercial_setup import commercial_setup_missing_fields, commercial_setup_warnings
from .publish_queue import PublishQueueEntry, build_publish_queue
from .quickstart import QuickstartReport, run_quickstart
from .readiness import ReadinessReport, run_readiness
from .settings import load_settings
from .troubleshoot import run_troubleshoot


@dataclass(frozen=True)
class ActionPlanStep:
    title: str
    reason: str
    action: str
    gui: str = ""
    command: str = ""
    severity: str = "info"
    source: str = ""
    target_path: str = ""


@dataclass(frozen=True)
class ActionPlanReport:
    project_dir: Path
    readiness_score: int
    quickstart_score: int
    status: str
    steps: list[ActionPlanStep]


def build_action_plan(
    project_dir: Path,
    *,
    readiness: ReadinessReport | None = None,
    quickstart: QuickstartReport | None = None,
    include_sales_handoffs: bool = True,
    limit: int = 5,
) -> ActionPlanReport:
    project_dir = project_dir.resolve()
    readiness = readiness or run_readiness(project_dir)
    quickstart = quickstart or run_quickstart(project_dir)
    quick_items = {item.name: item for item in quickstart.items}
    readiness_items = {item.name: item for item in readiness.items}
    candidates: list[tuple[int, ActionPlanStep]] = []
    seen: set[str] = set()

    def add(
        key: str,
        priority: int,
        *,
        severity: str,
        title: str,
        reason: str,
        action: str,
        gui: str = "",
        command: str = "",
        source: str = "",
        target_path: str = "",
    ) -> None:
        if key in seen:
            return
        seen.add(key)
        candidates.append(
            (
                priority,
                ActionPlanStep(
                    title=title,
                    reason=_clean_detail(reason),
                    action=action,
                    gui=gui,
                    command=command,
                    severity=severity,
                    source=source,
                    target_path=target_path,
                ),
            )
        )

    setup_item = quick_items.get("setup")
    readiness_setup = _first_readiness_item(readiness, "setup:", {"fail"})
    if (setup_item and setup_item.status == "fail") or readiness_setup:
        detail = setup_item.detail if setup_item and setup_item.status == "fail" else readiness_setup.detail
        add(
            "setup",
            10,
            severity="blocker",
            title="セットアップを修復する",
            reason=detail,
            action="自動修復で基本フォルダ、設定、アイデア保存を再作成し、残ったWARNを確認してください。",
            gui="診断 > 自動修復",
            command="auto-note repair --project-dir . --apply",
            source="setup",
        )

    product_item = readiness_items.get("product quality")
    if product_item and product_item.status in {"fail", "warn"}:
        add(
            "product_quality",
            20 if product_item.status == "fail" else 75,
            severity="blocker" if product_item.status == "fail" else "warning",
            title="製品品質のNGを確認する",
            reason=product_item.detail,
            action="販売/配布前に品質チェックのNGまたは警告を解消してください。",
            gui="診断 > 品質チェック",
            command="auto-note quality --project-dir .",
            source="readiness",
        )

    troubleshoot = run_troubleshoot(project_dir, include_sales_handoffs=include_sales_handoffs)
    troubleshooting_failures = [item for item in troubleshoot.items if item.status == "fail"]
    troubleshooting_warnings = _serious_troubleshoot_warnings(troubleshoot.items)
    if troubleshooting_failures or troubleshooting_warnings:
        issue = (troubleshooting_failures or troubleshooting_warnings)[0]
        blocked = bool(troubleshooting_failures)
        add(
            "troubleshoot",
            25 if blocked else 72,
            severity="blocker" if blocked else "warning",
            title="トラブル診断のNGを確認する" if blocked else "トラブル診断を確認する",
            reason=issue.detail,
            action=issue.action or "起動ログ、ログイン案内、プライバシー監査、配布ZIP状態を確認してください。",
            gui="診断 > トラブル診断",
            command="auto-note troubleshoot --project-dir .",
            source="troubleshoot",
        )

    settings = load_settings(project_dir)
    commercial_missing = commercial_setup_missing_fields(settings)
    commercial_warnings = commercial_setup_warnings(settings)
    if commercial_missing:
        add(
            "commercial_setup_missing",
            42,
            severity="warning",
            title="販売者情報を埋める",
            reason=f"未入力 {len(commercial_missing)}件: {', '.join(commercial_missing)}",
            action="販売者/屋号、販売ページURL、返金方針URL、サポート連絡先、販売前確認を埋めてください。",
            gui="設定 > 次の不足へ",
            command="auto-note commercial-setup --project-dir . --template",
            source="commercial_setup",
        )
    elif commercial_warnings:
        add(
            "commercial_setup_warnings",
            43,
            severity="warning",
            title="販売者情報の公開URLを確認する",
            reason=f"確認事項 {len(commercial_warnings)}件: {', '.join(commercial_warnings)}",
            action="販売ページURL、返金方針URL、サポート連絡先を購入者が開ける公開URLにしてください。",
            gui="設定 > 次の不足へ",
            command="auto-note commercial-setup --project-dir .",
            source="commercial_setup",
        )

    first_article = quick_items.get("first article")
    has_article = bool(first_article and first_article.status == "pass")
    if first_article and first_article.status != "pass":
        add(
            "first_article",
            30,
            severity="warning",
            title="最初の記事を作る",
            reason=first_article.detail,
            action="スターター一式を作り、記事一覧、予定、投稿キュー、投稿ヘルパーまで一通り試してください。",
            gui="ホーム > スターター一式",
            command="auto-note starter-pack --project-dir .",
            source="quickstart",
        )

    article_check = quick_items.get("article check")
    if has_article and article_check and article_check.status in {"fail", "warn"}:
        add(
            "article_check",
            40 if article_check.status == "fail" else 65,
            severity="blocker" if article_check.status == "fail" else "warning",
            title="公開前チェックを直す",
            reason=article_check.detail,
            action="NGや警告を確認し、投稿前の本文/タグ/状態を整えてください。",
            gui="チェック > 全体チェック",
            command="auto-note check .\\articles",
            source="quickstart",
        )

    article_review = quick_items.get("article review")
    if has_article and article_review and article_review.status in {"fail", "warn"}:
        add(
            "article_review",
            50,
            severity="warning",
            title="記事レビューで仕上げる",
            reason=article_review.detail,
            action="導入、まとめ、タグ、画像、公開状態の改善候補を確認してください。",
            gui="チェック > レビュー更新",
            command="auto-note review .\\articles",
            source="quickstart",
        )

    queue_entry = _next_publish_queue_entry(project_dir)
    if queue_entry and queue_entry.readiness in {"blocked", "error"}:
        add(
            "publish_queue_blocked",
            45,
            severity="warning",
            title="投稿キューの先頭記事を直す",
            reason=f"投稿キューに{_queue_readiness_label(queue_entry.readiness)}の記事があります。",
            action=queue_entry.next_action or "記事タブで投稿準備の詳細を確認してください。",
            gui="記事 > 投稿キュー > 投稿準備",
            command="auto-note publish-queue --project-dir .",
            source="publish_queue",
            target_path=str(queue_entry.source),
        )
    elif queue_entry and queue_entry.readiness == "check":
        add(
            "publish_queue_check",
            62,
            severity="warning",
            title="投稿キューの確認項目を見る",
            reason="投稿キューにCHECKの記事があります。",
            action=queue_entry.next_action or "確認項目を見て、問題なければ投稿へ進めてください。",
            gui="記事 > 投稿キュー > 投稿準備",
            command="auto-note publish-queue --project-dir .",
            source="publish_queue",
            target_path=str(queue_entry.source),
        )
    elif queue_entry and queue_entry.readiness == "postable":
        add(
            "publish_queue_postable",
            98,
            severity="ready",
            title="投稿キューの準備OK記事を投稿する",
            reason="投稿キューにPOSTABLEの記事があります。",
            action="投稿前チェックを確認し、投稿ヘルパーからnoteへ貼り付けてください。",
            gui="記事 > 投稿ヘルパー",
            command="auto-note publish-queue --project-dir .",
            source="publish_queue",
            target_path=str(queue_entry.source),
        )

    content_item = readiness_items.get("article content")
    if has_article and content_item and content_item.action and "article_review" not in seen:
        add(
            "article_content",
            55,
            severity="warning",
            title="記事の仕上げ項目を確認する",
            reason=content_item.detail,
            action="投稿前に読みやすさと公開状態を確認してください。",
            gui="チェック > レビュー更新",
            command="auto-note review .\\articles",
            source="readiness",
        )

    backup_item = readiness_items.get("latest backup") or quick_items.get("backup")
    if backup_item and backup_item.status in {"fail", "warn"}:
        add(
            "backup",
            60 if backup_item.status == "fail" else 70,
            severity="blocker" if backup_item.status == "fail" else "warning",
            title="バックアップを作成する",
            reason=backup_item.detail,
            action="編集や配布前に記事と設定のバックアップを残してください。",
            gui="ホーム > バックアップ作成",
            command="auto-note backup --project-dir .",
            source="readiness",
        )

    privacy_item = readiness_items.get("privacy cleanup")
    if privacy_item and privacy_item.status == "info":
        add(
            "privacy_cleanup",
            80,
            severity="maintenance",
            title="危険生成物を確認する",
            reason=privacy_item.detail,
            action="プライバシー監査NGの古い生成物を一覧で確認してください。",
            gui="診断 > 危険生成物確認",
            command="auto-note cleanup --project-dir . --privacy-failed --include-releases",
            source="readiness",
        )

    release_item = readiness_items.get("release package")
    if release_item and release_item.status in {"fail", "warn"}:
        add(
            "release",
            85 if release_item.status == "fail" else 95,
            severity="blocker" if release_item.status == "fail" else "warning",
            title="配布ZIPを作成/検証する",
            reason=release_item.detail,
            action="販売/配布前にユーザー記事を含まない配布ZIPを作成し、checksumを確認してください。",
            gui="診断 > 出荷ZIP作成",
            command="auto-note preflight --project-dir . --create-release --gui-smoke",
            source="readiness",
        )

    note_login = quick_items.get("note login")
    if note_login:
        add(
            "note_login",
            90,
            severity="info",
            title="noteログインを確認する",
            reason="note側のログイン状態は普段使うブラウザで確認します。",
            action="既定ブラウザでnoteにログインしてから投稿ヘルパーを使ってください。",
            gui="ヘッダー > noteログイン",
            command="auto-note login --default-browser",
            source="quickstart",
        )

    helper_item = quick_items.get("posting helper")
    if has_article and helper_item and helper_item.status == "pass":
        add(
            "posting_helper",
            100,
            severity="ready",
            title="投稿ヘルパーでnoteへ貼り付ける",
            reason="記事とローカル投稿ヘルパーの準備ができています。",
            action="記事を選び、投稿ヘルパーからタイトル/本文/タグをコピーしてください。",
            gui="記事 > 投稿ヘルパー",
            command="auto-note manual .\\articles\\post.md --append-tags",
            source="quickstart",
        )

    if has_article:
        add(
            "published_url",
            120,
            severity="info",
            title="公開後URLを保存する",
            reason="公開済み管理まで完了すると、後から投稿一覧を追いやすくなります。",
            action="noteで公開したらURLを保存し、記事状態を公開済みにしてください。",
            gui="記事 > 公開済みにする",
            command="auto-note published .\\articles\\post.md --url <note-url>",
            source="workflow",
        )

    add(
        "preflight",
        130,
        severity="ready",
        title="出荷前チェックを通す",
        reason="販売/配布前の品質、GUI起動、配布ZIP作成を一括確認できます。",
        action="大きな変更後や配布前に総合チェックを実行してください。",
        gui="診断 > 出荷前チェック",
        command="auto-note preflight --project-dir . --gui-smoke",
        source="readiness",
    )

    steps = [step for _priority, step in sorted(candidates, key=lambda item: item[0])][: max(1, limit)]
    return ActionPlanReport(
        project_dir=project_dir,
        readiness_score=readiness.score,
        quickstart_score=quickstart.score,
        status=_plan_status(readiness, quickstart, steps),
        steps=steps,
    )


def format_action_plan(report: ActionPlanReport) -> str:
    lines = [
        "Action plan / 次の一手",
        f"Status: {report.status}",
        f"Readiness: {report.readiness_score}/100",
        f"Quickstart: {report.quickstart_score}/100",
        "",
        "Priority actions",
    ]
    for index, step in enumerate(report.steps, start=1):
        label = _severity_label(step.severity)
        lines.append(f"{index}. [{label}] {step.title}")
        lines.append(f"   why: {step.reason}")
        lines.append(f"   next: {step.action}")
        if step.gui:
            lines.append(f"   gui: {step.gui}")
        if step.command:
            lines.append(f"   cli: {step.command}")
    return "\n".join(lines)


def _first_readiness_item(report: ReadinessReport, prefix: str, statuses: set[str]):
    for item in report.items:
        if item.name.startswith(prefix) and item.status in statuses:
            return item
    return None


def _next_publish_queue_entry(project_dir: Path) -> PublishQueueEntry | None:
    try:
        report = build_publish_queue(project_dir)
    except Exception:
        return None
    for readiness in ("blocked", "error", "check", "postable"):
        for entry in report.entries:
            if entry.readiness == readiness:
                return entry
    return None


def _queue_readiness_label(readiness: str) -> str:
    return {
        "blocked": "BLOCKED",
        "error": "ERROR",
        "check": "CHECK",
        "postable": "POSTABLE",
    }.get(readiness, readiness.upper())


def _serious_troubleshoot_warnings(items) -> list:
    return [
        item
        for item in items
        if item.status == "warn" and item.name != "privacy cleanup candidates"
    ]


def _plan_status(readiness: ReadinessReport, quickstart: QuickstartReport, steps: list[ActionPlanStep]) -> str:
    if any(step.severity == "blocker" for step in steps):
        return "BLOCKED"
    if any(item.status == "fail" for item in [*readiness.items, *quickstart.items]):
        return "BLOCKED"
    if any(step.severity in {"warning", "maintenance"} for step in steps) or quickstart.has_warnings:
        return "NEEDS ATTENTION"
    return "READY"


def _severity_label(severity: str) -> str:
    return {
        "blocker": "NG",
        "warning": "要確認",
        "maintenance": "保守",
        "ready": "準備OK",
        "info": "案内",
    }.get(severity, severity.upper())


def _clean_detail(detail: str) -> str:
    return " ".join(detail.strip().split()) or "確認が必要です。"
