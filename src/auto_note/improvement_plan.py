from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .article import Article, load_article
from .paths import unique_path
from .publish_ready import PublishReadyReport, run_publish_ready
from .review import ArticleReview, review_article


SEVERITY_ORDER = {"fix": 0, "warn": 1, "improve": 2, "info": 3}


@dataclass(frozen=True)
class ImprovementPlanStep:
    priority: int
    severity: str
    stage: str
    category: str
    problem: str
    action: str
    source: str
    estimated_minutes: int = 5


@dataclass(frozen=True)
class ImprovementPlan:
    article: Article
    review: ArticleReview
    publish_ready: PublishReadyReport
    generated_at: datetime
    steps: list[ImprovementPlanStep]

    @property
    def status(self) -> str:
        if any(step.severity == "fix" for step in self.steps):
            return "blocked"
        if any(step.severity in {"warn", "improve"} for step in self.steps):
            return "check"
        return "ready"

    @property
    def fix_count(self) -> int:
        return sum(1 for step in self.steps if step.severity == "fix")

    @property
    def warn_count(self) -> int:
        return sum(1 for step in self.steps if step.severity == "warn")

    @property
    def improve_count(self) -> int:
        return sum(1 for step in self.steps if step.severity == "improve")

    @property
    def total_minutes(self) -> int:
        return sum(step.estimated_minutes for step in self.steps if step.severity != "info")


def build_improvement_plan(
    file: Path,
    *,
    append_tags: bool = False,
    limit: int = 10,
) -> ImprovementPlan:
    article = load_article(file)
    review = review_article(article, append_tags=append_tags)
    publish_ready = run_publish_ready(file, append_tags=append_tags, smoke_helper=False)
    steps = _steps_from_review(review)
    steps.extend(_steps_from_publish_ready(publish_ready))
    steps.sort(key=lambda step: (SEVERITY_ORDER.get(step.severity, 9), step.priority, step.category))
    steps = _renumber(steps[: max(1, limit)])
    if not steps:
        steps = [
            ImprovementPlanStep(
                priority=1,
                severity="info",
                stage="投稿",
                category="投稿準備",
                problem="投稿前チェックは通っています。",
                action="投稿ヘルパーを開き、noteに転記して公開してください。",
                source="publish-ready",
                estimated_minutes=3,
            )
        ]
    return ImprovementPlan(
        article=article,
        review=review,
        publish_ready=publish_ready,
        generated_at=datetime.now(),
        steps=steps,
    )


def format_improvement_plan(plan: ImprovementPlan, *, include_private: bool = True) -> str:
    article_label = str(plan.article.source) if include_private else "<article>.md"
    title = plan.article.title if include_private else f"<title:{len(plan.article.title)} chars>"
    verdict = {"ready": "READY", "check": "CHECK", "blocked": "BLOCKED"}[plan.status]
    readiness = {
        "pass": "READY TO POST",
        "warn": "NEEDS REVIEW",
        "fail": "BLOCKED",
    }[plan.publish_ready.status]
    lines = [
        "Improvement plan / 改善プラン",
        f"Generated: {plan.generated_at:%Y-%m-%d %H:%M:%S}",
        f"Verdict: {verdict}",
        f"Article: {article_label}",
        f"Title: {title}",
        f"Review score: {plan.review.score}/100",
        f"Publish readiness: {readiness}",
        (
            "Focus: "
            f"{plan.fix_count} FIX, "
            f"{plan.warn_count} WARN, "
            f"{plan.improve_count} IMPROVE, "
            f"about {plan.total_minutes} min"
        ),
        "",
        "Recommended order / おすすめ順",
    ]
    for step in plan.steps:
        label = {"fix": "FIX", "warn": "WARN", "improve": "IMPROVE", "info": "INFO"}.get(
            step.severity,
            step.severity.upper(),
        )
        problem = _mask_private(step.problem, plan) if not include_private else step.problem
        action = _mask_private(step.action, plan) if not include_private else step.action
        lines.append(f"{step.priority}. [{label}] {step.stage} / {step.category}: {problem}")
        if action:
            lines.append(f"   do: {action}")
        lines.append(f"   source: {step.source}, estimate: {step.estimated_minutes} min")
    if plan.status == "ready":
        lines.extend(
            [
                "",
                "Next",
                "- 投稿ヘルパーを開いてnoteへ貼り付け、公開後にURLを保存します。",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "After fixing",
                "- `auto-note publish-ready <file> --smoke-helper` で投稿ヘルパー生成まで確認します。",
                "- NGがなくなったら `--mark-ready`、またはGUIの `準備OK` に進みます。",
            ]
        )
    return "\n".join(lines)


def has_improvement_plan_blockers(plan: ImprovementPlan, *, strict: bool = False) -> bool:
    if any(step.severity == "fix" for step in plan.steps):
        return True
    return strict and any(step.severity in {"warn", "improve"} for step in plan.steps)


def write_improvement_plan_report(
    project_dir: Path,
    *,
    plan: ImprovementPlan,
    include_private: bool = False,
) -> Path:
    reports_dir = project_dir.resolve() / ".auto-note" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = unique_path(reports_dir / f"improvement-plan-{plan.generated_at:%Y%m%d-%H%M%S}.txt")
    path.write_text(format_improvement_plan(plan, include_private=include_private) + "\n", encoding="utf-8")
    return path


def list_improvement_plan_reports(project_dir: Path) -> list[Path]:
    reports_dir = project_dir / ".auto-note" / "reports"
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("improvement-plan-*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)


def _steps_from_review(review: ArticleReview) -> list[ImprovementPlanStep]:
    steps: list[ImprovementPlanStep] = []
    for index, item in enumerate(review.items, start=1):
        if item.level not in {"fix", "improve"}:
            continue
        stage = "必須修正" if item.level == "fix" else "仕上げ"
        steps.append(
            ImprovementPlanStep(
                priority=index,
                severity=item.level,
                stage=stage,
                category=item.category,
                problem=item.message,
                action=item.action,
                source="article review",
                estimated_minutes=_estimated_minutes(item.category, item.level),
            )
        )
    return steps


def _steps_from_publish_ready(report: PublishReadyReport) -> list[ImprovementPlanStep]:
    steps: list[ImprovementPlanStep] = []
    offset = 100
    for index, item in enumerate(report.items, start=1):
        if item.name == "article review":
            continue
        if item.status not in {"fail", "warn"}:
            continue
        severity = "fix" if item.status == "fail" else "warn"
        steps.append(
            ImprovementPlanStep(
                priority=offset + index,
                severity=severity,
                stage="投稿前確認",
                category=item.name,
                problem=item.detail,
                action=item.action,
                source="publish-ready",
                estimated_minutes=5 if severity == "warn" else 8,
            )
        )
    return steps


def _renumber(steps: list[ImprovementPlanStep]) -> list[ImprovementPlanStep]:
    return [
        ImprovementPlanStep(
            priority=index,
            severity=step.severity,
            stage=step.stage,
            category=step.category,
            problem=step.problem,
            action=step.action,
            source=step.source,
            estimated_minutes=step.estimated_minutes,
        )
        for index, step in enumerate(steps, start=1)
    ]


def _estimated_minutes(category: str, level: str) -> int:
    if category in {"本文", "構成"}:
        return 12 if level == "fix" else 8
    if category in {"タイトル", "概要", "タグ"}:
        return 5
    if category == "画像":
        return 8
    return 6 if level == "fix" else 5


def _mask_private(text: str, plan: ImprovementPlan) -> str:
    masked = text
    source = plan.article.source
    for value, replacement in (
        (str(source), "<article>.md"),
        (source.as_posix(), "<article>.md"),
        (source.name, "<article>.md"),
    ):
        if value:
            masked = masked.replace(value, replacement)
    if len(plan.article.title.strip()) >= 6:
        masked = masked.replace(plan.article.title, f"<title:{len(plan.article.title)} chars>")
    return masked
