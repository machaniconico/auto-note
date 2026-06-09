from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

from .article import ArticleError
from .diagnostics import run_diagnostics
from .images import inspect_images_path, missing_images
from .inspect import inspect_path
from .review import review_path
from .settings import load_settings


VALID_STATUSES = {"draft", "ready", "scheduled", "published"}


@dataclass(frozen=True)
class QualityCheck:
    name: str
    status: str
    detail: str

    @property
    def ok(self) -> bool:
        return self.status != "fail"


def run_quality_checks(project_dir: Path, *, include_articles: bool = True) -> list[QualityCheck]:
    settings = load_settings(project_dir)
    checks: list[QualityCheck] = []

    checks.append(_path_check(project_dir / "README.md", "README"))
    checks.append(_path_check(project_dir / "docs" / "QUICKSTART.md", "quickstart guide"))
    checks.append(_path_check(project_dir / "docs" / "PRODUCT_READINESS.md", "product readiness memo"))
    checks.append(_path_check(project_dir / "docs" / "INSTALL.md", "install guide"))
    checks.append(_path_check(project_dir / "docs" / "UPDATE.md", "update guide"))
    checks.append(_path_check(project_dir / "docs" / "SUPPORT.md", "support guide"))
    checks.append(_path_check(project_dir / "docs" / "PRIVACY.md", "privacy guide"))
    checks.append(_path_check(project_dir / "docs" / "TERMS_DRAFT.md", "terms draft"))
    checks.append(_path_check(project_dir / "docs" / "COMMERCIAL_POLICY_DRAFT.md", "commercial policy draft"))
    checks.append(_path_check(project_dir / "docs" / "THIRD_PARTY_NOTICES.md", "third-party notices"))
    checks.append(_path_check(project_dir / "docs" / "CHANGELOG.md", "changelog"))
    checks.append(_path_check(project_dir / "docs" / "RELEASE_CHECKLIST.md", "release checklist"))
    checks.append(_path_check(project_dir / "docs" / "RC_HANDOFF.md", "release candidate handoff"))
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "RC_HANDOFF.md",
            "RC handoff release check",
            "check-release.ps1 -Full",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "RC_HANDOFF.md",
            "RC handoff sales evidence",
            "sales-finalize --project-dir . --strict --gui-smoke",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "RC_HANDOFF.md",
            "RC handoff stop conditions",
            "止める条件",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "RELEASE_CHECKLIST.md",
            "release checklist RC handoff guidance",
            "docs\\RC_HANDOFF.md",
        )
    )
    checks.append(_path_check(project_dir / ".github" / "workflows" / "ci.yml", "GitHub Actions CI"))
    checks.append(
        _text_contains_check(
            project_dir / ".github" / "workflows" / "ci.yml",
            "CI Windows runner",
            "windows-latest",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / ".github" / "workflows" / "ci.yml",
            "CI unit tests",
            "python -m unittest discover -s tests",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / ".github" / "workflows" / "ci.yml",
            "CI product quality gate",
            "python -m auto_note quality --project-dir . --product-only",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / ".github" / "workflows" / "ci.yml",
            "CI hidden launcher syntax check",
            "AUTO_NOTE_LAUNCHER_CHECK",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / ".github" / "workflows" / "ci.yml",
            "CI GUI smoke",
            "python -m auto_note gui --project-dir . --smoke",
        )
    )
    checks.append(_version_consistency_check(project_dir / "pyproject.toml", project_dir / "src" / "auto_note" / "__init__.py"))
    checks.append(_path_check(project_dir / "auto-note-gui.bat", "GUI launcher"))
    checks.append(
        _text_contains_check(
            project_dir / "auto-note-gui.bat",
            "GUI launcher smoke check",
            "--smoke",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "auto-note-gui.bat",
            "GUI launcher support bundle guidance",
            "support --project-dir",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "auto-note-gui.bat",
            "GUI launcher recovery kit guidance",
            "recovery-kit --project-dir",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "auto-note-gui.bat",
            "GUI launcher recovery kit report guidance",
            "--report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "support.py",
            "support bundle send checklist",
            "SUPPORT_SEND_CHECKLIST.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "support.py",
            "support bundle GUI log summary",
            "GUI_LOG_SUMMARY.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "support.py",
            "support bundle GUI log privacy mask",
            "mask_text(text, project_dir)",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "support.py",
            "support bundle GUI log verification detail",
            "GUI_LOG_SUMMARY.txt: present",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "support.py",
            "support bundle GUI log summary reader",
            "read_support_gui_log_summary",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "support.py",
            "support bundle send-only guidance",
            "Send this ZIP only",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "repair.py",
            "recovery kit workflow",
            "run_recovery_kit",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "repair.py",
            "recovery kit support bundle fallback",
            "create_bundle_on_issue",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "repair.py",
            "recovery kit report writer",
            "write_recovery_kit_report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "repair.py",
            "recovery kit report lister",
            "list_recovery_kit_reports",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI recovery kit action",
            "run_recovery_kit_to_tab",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI recovery kit saves report",
            "write_recovery_kit_report(self.project_dir, report=report)",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI recovery kit button",
            "復旧セット",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI recovery report display action",
            "show_latest_recovery_kit_report_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI recovery report copy action",
            "copy_latest_recovery_kit_report_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI recovery report folder action",
            "open_recovery_kit_reports_folder_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI recovery report display button",
            "最新復旧レポート",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI recovery report copy button",
            "復旧レポートコピー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI recovery report folder button",
            "復旧レポート場所",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI recovery report empty state",
            "復旧レポートはまだありません",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports panel",
            "直近レポート",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports tree",
            "home_reports_tree",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports refresh",
            "_refresh_home_reports",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports display action",
            "show_selected_home_report_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports location action",
            "open_selected_home_report_location_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports status tags",
            "_configure_home_reports_tree_tags",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports row tags",
            "tags=(_home_report_status_tag(status),)",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports selection summary",
            "on_select_home_report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports NG action summary",
            "表示で詳細確認",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports empty state",
            "まだ保存レポートがありません",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports status column",
            'heading("status", text="状態")',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports copy path action",
            "copy_selected_home_report_path_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports copy path clipboard",
            "self.clipboard_append(str(path.resolve()))",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports verification status",
            "_home_report_status",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports buyer ZIP verification status",
            "verify_buyer_delivery_package(path)",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports buyer ZIP verification preview",
            "format_buyer_delivery_package_verification(path",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports buyer delivery ZIP",
            "購入者ZIP",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports buyer delivery message",
            "購入者送付文",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recent reports seller receipt",
            "送付記録",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke recent reports count",
            "home_report_items=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README recovery kit guidance",
            "復旧セット",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README recovery kit CLI guidance",
            "auto-note recovery-kit",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README recovery kit report guidance",
            "recovery-kit-*.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README recovery kit GUI report guidance",
            "最新復旧レポート",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README self-test launcher health guidance",
            "ランチャー健康チェック",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home recent reports guidance",
            "直近レポート",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home recent reports copy guidance",
            "パスコピー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home recent reports buyer delivery guidance",
            "購入者ZIP、購入者送付文、送付記録",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home progress lane guidance",
            "作業進行",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home compact snapshot guidance",
            "コンパクト概要",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home progress direct open guidance",
            "作業進行レーンの各工程の `開く`",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home progress command palette guidance",
            "作業進行: 初回",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home first-run setup guidance",
            "初回セットアップのスコアと次項目",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README command palette result state guidance",
            "一致するコマンドがない時",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README command palette keyboard guidance",
            "上下キーで候補を選び",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README command palette multi-word search guidance",
            "スペース区切りの複数語",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README first-run actionable filter guidance",
            "要対応だけ",
        )
    )
    checks.append(_path_check(project_dir / "scripts" / "launch-gui.vbs", "hidden GUI launcher"))
    checks.append(
        _text_contains_check(
            project_dir / "scripts" / "launch-gui.vbs",
            "hidden GUI launcher target",
            "auto-note-gui.bat",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "scripts" / "launch-gui.vbs",
            "hidden GUI launcher no console",
            "shell.Run(command, 0, True)",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "scripts" / "launch-gui.vbs",
            "hidden GUI launcher check mode",
            "AUTO_NOTE_LAUNCHER_CHECK",
        )
    )
    checks.append(_path_check(project_dir / "shortcuts" / "create-gui-shortcut.bat", "shortcut helper"))
    checks.append(
        _text_contains_check(
            project_dir / "scripts" / "create-gui-shortcut.ps1",
            "shortcut uses hidden launcher",
            "launch-gui.vbs",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "scripts" / "create-gui-shortcut.ps1",
            "shortcut icon",
            "IconLocation",
        )
    )
    checks.append(_path_check(project_dir / "scripts" / "install-auto-note.ps1", "installer script"))
    checks.append(_path_check(project_dir / "shortcuts" / "install-auto-note.bat", "installer launcher"))
    checks.append(_path_check(project_dir / "scripts" / "uninstall-auto-note.ps1", "uninstaller script"))
    checks.append(_path_check(project_dir / "shortcuts" / "uninstall-auto-note.bat", "uninstaller launcher"))
    checks.append(_path_check(project_dir / "scripts" / "check-release.ps1", "release check script"))
    checks.append(
        _text_contains_check(
            project_dir / "scripts" / "check-release.ps1",
            "release check unit tests",
            "python -m unittest discover -s tests",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "scripts" / "check-release.ps1",
            "release check product quality",
            "auto_note quality --project-dir",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "scripts" / "check-release.ps1",
            "release check launcher syntax",
            "AUTO_NOTE_LAUNCHER_CHECK",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "scripts" / "check-release.ps1",
            "release check full install smoke",
            "smoke-install.ps1",
        )
    )
    checks.append(_path_check(project_dir / "scripts" / "smoke-install.ps1", "install smoke test"))
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "release.py",
            "release first-run checklist",
            "FIRST_RUN_CHECKLIST.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI starter pack command",
            "starter-pack",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI starter cleanup command",
            "starter-clean",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI repair command",
            "repair",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI recovery kit command",
            "recovery-kit",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI recovery kit report option",
            "--report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "selftest.py",
            "self-test launcher health item",
            "_launcher_health_item",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "selftest.py",
            "self-test launcher health included",
            "_launcher_health_item(project_dir)",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "selftest.py",
            "self-test hidden launcher syntax check",
            "_hidden_launcher_syntax_warning",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "selftest.py",
            "self-test direct launcher fallback",
            "auto-note-gui.bat を直接",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI troubleshoot command",
            "troubleshoot",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI acceptance command",
            "acceptance",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI acceptance full command",
            "--full",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI commercial readiness command",
            "commercial-readiness",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI commercial policy review command",
            "--policy-review",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "commercial.py",
            "commercial policy review writer",
            "write_commercial_policy_review",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "commercial.py",
            "commercial policy review lister",
            "list_commercial_policy_reviews",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI commercial setup command",
            "commercial-setup",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI commercial setup template command",
            "Create a seller profile fill-in template",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI commercial setup template apply command",
            "--apply-template",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "commercial_setup.py",
            "commercial setup URL/contact warnings",
            "commercial_setup_warnings",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "commercial_setup.py",
            "commercial setup next actions",
            "commercial_setup_next_actions",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "commercial_setup.py",
            "commercial setup completion progress",
            "commercial_setup_completion",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "commercial_setup.py",
            "commercial setup next field helper",
            "commercial_setup_next_field",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "commercial_setup.py",
            "commercial setup safe template apply",
            "Safe Apply / 編集後の保存",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "commercial_setup.py",
            "commercial setup sales finalize followup",
            "sales-finalize --project-dir . --apply-latest-template",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "commercial_setup.py",
            "commercial setup sales plan followup",
            "auto-note sales-plan --project-dir .",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "action_plan.py",
            "action plan commercial setup guidance",
            "commercial_setup_missing_fields",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "action_plan.py",
            "action plan commercial setup next missing GUI guidance",
            "設定 > 次の不足へ",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI sales handoff command",
            "sales-handoff",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI sales materials command",
            "sales-materials",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI sales materials verify command",
            "Verify a sales materials markdown file.",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_materials.py",
            "sales materials commercial setup warnings",
            "commercial setup warning:",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_materials.py",
            "sales materials buyer first 10 minutes",
            "Buyer First 10 Minutes",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_handoff.py",
            "sales handoff buyer first 10 minutes",
            "購入者の最初の10分",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_handoff.py",
            "sales handoff delivery checklist",
            "DELIVERY_CHECKLIST.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_handoff.py",
            "sales handoff seller delivery receipt",
            "SELLER_DELIVERY_RECEIPT.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI sales handoff buyer extract command",
            "--extract-buyer",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI sales handoff buyer verify command",
            "--verify-buyer",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI sales handoff buyer package command",
            "--package-buyer",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI sales handoff buyer package verify command",
            "--verify-buyer-package",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_handoff.py",
            "sales handoff buyer delivery extractor",
            "extract_buyer_delivery",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_handoff.py",
            "sales handoff buyer delivery verifier",
            "verify_buyer_delivery",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_handoff.py",
            "sales handoff buyer delivery checksums",
            "SHA256SUMS.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_handoff.py",
            "sales handoff buyer support guide",
            "BUYER_SUPPORT_GUIDE.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_handoff.py",
            "sales handoff buyer start guide",
            "START_HERE_FOR_BUYER.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_handoff.py",
            "sales handoff buyer delivery manifest",
            "BUYER_DELIVERY_MANIFEST.json",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_handoff.py",
            "sales handoff buyer delivery manifest verifier",
            "_verify_buyer_delivery_manifest",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_handoff.py",
            "sales handoff buyer delivery package",
            "package_buyer_delivery",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_handoff.py",
            "sales handoff buyer delivery package verifier",
            "verify_buyer_delivery_package",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_handoff.py",
            "sales handoff buyer delivery package SHA-256",
            "Package SHA-256",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI sales finalize command",
            "sales-finalize",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI sales finalize template apply command",
            "Apply the latest seller profile template before finalizing sales artifacts.",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI buyer send readiness command",
            "--send-check",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI buyer send readiness report command",
            "--send-check-report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI seller delivery receipt command",
            "--delivery-receipt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales finalize ignores stale handoffs during preflight",
            "include_sales_handoffs=False",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales finalize creates acceptance evidence",
            "write_acceptance_report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales finalize creates buyer delivery",
            "extract_buyer_delivery",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales finalize verifies buyer delivery",
            "verify_buyer_delivery",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales finalize verifies buyer delivery zip",
            "verify_buyer_delivery_package",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales finalize buyer delivery message",
            "_write_buyer_delivery_message",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales finalize buyer delivery message lister",
            "list_buyer_delivery_messages",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "buyer send readiness runner",
            "run_buyer_send_readiness",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "buyer send readiness formatter",
            "format_buyer_send_readiness_report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "buyer send readiness report writer",
            "write_buyer_send_readiness_report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "buyer send readiness report lister",
            "list_buyer_send_readiness_reports",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "seller delivery receipt writer",
            "write_seller_delivery_receipt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "seller delivery receipt formatter",
            "format_seller_delivery_receipt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "seller delivery receipt lister",
            "list_seller_delivery_receipts",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "buyer delivery message package matcher",
            "find_buyer_delivery_package_for_message",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales finalize seller send checklist",
            "_write_seller_send_checklist",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "privacy.py",
            "privacy audit seller send checklist",
            "seller send checklist privacy",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "privacy.py",
            "privacy audit buyer delivery message",
            "buyer delivery message privacy",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "privacy.py",
            "privacy audit buyer delivery message lister",
            "list_buyer_delivery_messages",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "privacy.py",
            "privacy audit buyer send readiness report",
            "buyer send readiness report privacy",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "privacy.py",
            "privacy audit commercial policy review",
            "commercial policy review privacy",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "privacy.py",
            "privacy audit seller delivery receipt",
            "seller delivery receipt privacy",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "diagnostic seller send checklist",
            "seller-send-checklist.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "diagnostic report verifier",
            "verify_diagnostic_report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "diagnostic report verification formatter",
            "format_diagnostic_report_verification",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "diagnostic preview bounded sections",
            "DIAGNOSTIC_PREVIEW_SECTION_LIMIT",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "diagnostic preview section formatter",
            "_format_preview_section",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "diagnostic preview truncation notice",
            "full content is in diagnostic-report.zip",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "diagnostic preview heavyweight omission",
            "Preview omitted for speed",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "diagnostic buyer delivery message summary",
            "buyer_delivery_messages",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "diagnostic buyer send readiness report summary",
            "buyer_send_readiness_reports",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "diagnostic seller delivery receipt summary",
            "seller_delivery_receipts",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "maintenance.py",
            "cleanup seller send checklist",
            "seller-send-checklist-*.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "maintenance.py",
            "cleanup buyer delivery message",
            "buyer-delivery-message-*.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "maintenance.py",
            "cleanup buyer send readiness report",
            "buyer-send-readiness-*.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "maintenance.py",
            "cleanup seller delivery receipt",
            "seller-delivery-receipt-*.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "maintenance.py",
            "cleanup commercial policy review",
            "commercial-policy-review-*.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales finalize delivery verification SHA-256",
            "_delivery_verification_lines",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI sales plan command",
            "sales-plan",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "__main__.py",
            "CLI sales plan report command",
            "sales plan report created",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_plan.py",
            "sales plan buyer delivery package list",
            "list_buyer_delivery_packages",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_plan.py",
            "sales plan buyer delivery package verifier",
            "verify_buyer_delivery_package",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_plan.py",
            "sales plan buyer delivery package summary",
            "Latest buyer delivery zip",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_plan.py",
            "sales plan buyer delivery readiness summary",
            "Buyer delivery readiness",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_plan.py",
            "sales plan seller setup remaining summary",
            "Seller setup remaining",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_plan.py",
            "sales plan tool artifact remaining summary",
            "Tool/artifact actions remaining",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_plan.py",
            "sales plan upload guidance",
            "Upload guidance",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_plan.py",
            "sales plan buyer delivery package freshness",
            "_buyer_delivery_package_release_name",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_plan.py",
            "sales plan report writer",
            "write_sales_plan_report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_plan.py",
            "sales plan report lister",
            "list_sales_plan_reports",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_plan.py",
            "sales plan relative verify command",
            "_project_relative_path",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "privacy.py",
            "privacy audit sales plan report",
            "sales plan report privacy",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "maintenance.py",
            "cleanup sales plan report",
            "sales-plan-*.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "maintenance sales plan report summary",
            "sales_plan_reports",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "diagnostic sales evidence manifest",
            "sales-evidence-manifest.json",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "diagnostic commercial setup summary",
            "_commercial_setup_item",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "diagnostic commercial policy review summary",
            "commercial_policy_reviews",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "diagnostics.py",
            "maintenance sales evidence manifest summary",
            "sales_evidence_manifests",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales finalize creates sales plan report",
            "write_sales_plan_report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales finalize artifacts sales plan report",
            "sales plan report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales finalize seller checklist sales plan evidence",
            "Sales plan evidence",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales evidence manifest writer",
            "_write_sales_evidence_manifest",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales evidence manifest lister",
            "list_sales_evidence_manifests",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "sales finalize artifacts sales evidence manifest",
            "sales evidence manifest",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "sales_finalize.py",
            "seller checklist sales evidence manifest",
            "Sales evidence manifest",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "privacy.py",
            "privacy audit sales evidence manifest",
            "sales evidence manifest privacy",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "maintenance.py",
            "cleanup sales evidence manifest",
            "sales-evidence-manifest-*.json",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI starter pack action",
            "スターター一式",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI starter cleanup action",
            "スターター整理",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI repair action",
            "自動修復",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI troubleshoot action",
            "トラブル診断",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI acceptance action",
            "受入チェック",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI acceptance full action",
            "受入フル保存",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI commercial readiness action",
            "販売準備",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI commercial policy review action",
            "create_commercial_policy_review_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI commercial setup fields",
            "販売者/屋号",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI commercial setup template action",
            "販売者テンプレ",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI commercial setup template apply action",
            "テンプレ適用",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI commercial setup status action",
            "販売者情報確認",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI commercial setup save feedback",
            "_notify_settings_saved",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI commercial setup progress panel",
            "commercial_progress_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI commercial setup checklist",
            "commercial_setup_tree",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI commercial setup checklist helper",
            "_commercial_setup_field_rows",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI commercial setup selected focus",
            "focus_selected_commercial_setup_item",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke commercial setup checklist",
            "commercial_setup_items=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI commercial setup next missing action",
            "focus_next_commercial_missing_field",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI commercial setup command palette action",
            "販売者情報へ",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home sales summary panel",
            "home_sales_status_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home sales status pill",
            "home_sales_status_pill",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home sales stage indicators",
            "home_sales_stage_vars",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke home sales includes buyer send",
            "home_buyer_send_var.get()",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home support send stage",
            '"support", "サポート"',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home support send readiness helper",
            "_home_support_send_readiness",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home support send detail",
            "サポート {support_text}",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home support send action",
            "show_support_send_panel_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home support send next action",
            "run_home_support_next_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home support send next button",
            "home_support_next_button_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home support send next delegates",
            "self.run_support_next_action()",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home support send next button label helper",
            "_home_support_next_button_label",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home support send next syncs support state",
            "home_button_var.set(_home_support_next_button_label(text))",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home support send next message label",
            '"送付文コピー": "サポート: 送付文"',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home support send next preserves message action",
            'self.support_next_action_var.get() != "送付文コピー"',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home support send feedback",
            "サポート送付の状態を表示しました",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home sales indicator style",
            "_home_sales_indicator_style",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress lane",
            "作業進行",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress summary",
            "home_progress_summary_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress stage indicators",
            "home_progress_vars",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress refresh",
            "_refresh_home_progress_lane",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress stage setter",
            "_set_home_progress_stage",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress summary helper",
            "_home_progress_summary",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home primary dynamic button",
            "home_primary_button_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home primary button label helper",
            "_home_primary_button_label",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home first-run setup lane",
            "初回セットアップ",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home first-run summary helper",
            "_home_first_run_summary",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home first-run opener",
            "open_home_first_run_status",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke home progress count",
            "home_progress_chars=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke home first-run count",
            "home_first_run_chars=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress action buttons",
            "home_progress_buttons",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress state rails",
            "home_progress_rails",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress state rail helper",
            "_home_state_accent_color",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress stage opener",
            "open_home_progress_stage",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress article route",
            "_select_home_progress_tab",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke home progress action count",
            "home_progress_action_items=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke home status badge",
            "home_status_badge_chars=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke home freshness",
            "home_updated_chars=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke home primary button label",
            "home_primary_button_chars=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress command palette setup",
            "作業進行: 初回",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress command palette support",
            "作業進行: サポート",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home progress command palette opener",
            'open_home_progress_stage("support")',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI command palette status label",
            "command_palette_status_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI command palette UI density large action",
            "表示サイズ: 大きめ",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI command palette UI density quick apply",
            "set_ui_density_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI command palette UI density settings focus",
            "focus_ui_density_setting_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI command palette empty state",
            "一致するコマンドがありません",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI command palette match count helper",
            "_command_palette_status",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI command palette multi-word matcher",
            "_command_palette_matches",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI command palette all token matching",
            "all(token in haystack for token in tokens)",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI command palette keyboard navigation",
            "move_command_palette_selection",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI command palette keyboard selector helper",
            "_command_palette_selection_index",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI command palette listbox return binding",
            'listbox.bind("<Return>", run_selected)',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI command palette arrow key binding",
            'entry.bind("<Down>", lambda _event: move_command_palette_selection(1))',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern chrome style",
            "Chrome.TFrame",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern app title style",
            "AppTitle.TLabel",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern KPI typography",
            "KpiValue.TLabel",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern design tokens",
            "UI_COLORS",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern text area styling",
            "_style_text_widget",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI readable Japanese font",
            '"Yu Gothic UI"',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI readable text size tokens",
            "UI_TEXT_SIZE = 10",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI readable badge font size",
            "UI_BADGE_FONT_SIZE = 9",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI readable tree row height",
            "UI_TREE_ROW_HEIGHT = 38",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI readable tab padding",
            "UI_NOTEBOOK_TAB_PADDING = (18, 12)",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI readable button padding",
            "UI_BUTTON_PADDING = (14, 10)",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI readable text line spacing",
            "UI_TEXT_SPACING_BOTTOM = 4",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "settings.py",
            "settings UI density field",
            "ui_density: str",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "settings.py",
            "settings UI density options",
            "UI_DENSITY_OPTIONS",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "settings.py",
            "settings UI density normalization",
            "_normalise_ui_density",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI UI density selector",
            "ui_density_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI header UI density selector",
            "header_ui_density_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI header UI density combobox",
            "header_ui_density_combo",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI header UI density binding",
            "<<ComboboxSelected>>",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI header UI density action",
            "on_header_ui_density_selected",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI UI density style apply",
            "_apply_ui_density",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI UI density text refresh",
            "_refresh_text_widget_readability",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke readable style metrics",
            "readability_style_chars=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke UI density metrics",
            "ui_density_chars=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke header UI density metrics",
            "header_ui_density_chars=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke UI density command metrics",
            "command_palette_ui_density_actions=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI Japanese font fallback",
            "UI_FONT_CANDIDATES",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI resolved font family",
            "_resolve_font_family",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI Windows DPI awareness",
            "_enable_windows_dpi_awareness",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI Windows DPI API",
            "SetProcessDpiAwareness",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern input styling",
            '"TEntry"',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern workspace chips",
            "ChromeChip.TLabel",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern command palette surface",
            "selectbackground=UI_COLORS[\"accent\"]",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern quiet header action",
            "Quiet.TButton",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern command search header",
            "コマンド検索",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern header UI density style",
            "Chrome.TCombobox",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern KPI accent rail",
            'UI_COLORS["accent"] if index == 0 else UI_COLORS["line"]',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern home lead panel",
            "HomeLead.TFrame",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern home title typography",
            "HomeTitle.TLabel",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern home status badge",
            "home_status_badge",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern home freshness",
            "home_updated_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern home overview badge helper",
            "_home_overview_badge",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern home compact snapshot strip",
            "home_snapshot_vars",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern home compact snapshot refresh",
            "_refresh_home_snapshot_strip",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern home compact snapshot helper",
            "_home_snapshot_values",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke home compact snapshot",
            "home_snapshot_chars=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern article focus panel",
            "article_focus_summary_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern article focus next action",
            "run_article_focus_next_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern article focus helper",
            "_article_focus_summary",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke article focus",
            "article_focus_chars=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI review detail action rail",
            "review_detail_buttons",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI review detail editor action",
            "open_selected_review_article_editor",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI review detail selected item helper",
            "_selected_review_detail_item",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI article editor tab selector",
            "_select_article_editor_tab",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI smoke review detail actions",
            "review_detail_action_items=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README article focus inspector guidance",
            "選択記事フォーカス",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern first-run subtitle",
            "初回起動、販売前チェック",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern settings subtitle",
            "投稿補助、表示サイズ",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README UI density guidance",
            "表示サイズ",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README UI density command guidance",
            "表示サイズ: 大きめ",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README UI density header guidance",
            "ヘッダーの `表示`",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern diagnostics subtitle",
            "品質チェック、配布ZIP",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI modern help subtitle",
            "購入者向け案内",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI log display action",
            "show_gui_log_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI log copy action",
            "copy_gui_log_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI log folder action",
            "open_gui_log_folder_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI log display button",
            "GUIログ表示",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI log copy button",
            "GUIログコピー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI log folder button",
            "GUIログ場所",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI diagnostic ZIP folder button",
            "診断ZIP場所",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI diagnostic ZIP verify button",
            "診断ZIP検証",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI diagnostic ZIP verify action",
            "verify_latest_diagnostic_report_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI diagnostic ZIP path button",
            "診断ZIPパス",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI diagnostic ZIP location action",
            "open_latest_diagnostic_report_location_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI diagnostic ZIP path action",
            "copy_latest_diagnostic_report_path_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI diagnostic ZIP path clipboard",
            "self.clipboard_append(str(latest.resolve()))",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI log preview content",
            "GUI log / GUIログ",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI runtime error actionable helper",
            "_gui_runtime_error_message",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI runtime error recovery guidance",
            "GUIログ表示または復旧セット",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI runtime error support bundle guidance",
            "問い合わせ一式",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recovery status lane",
            "復旧ステータス",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recovery log status helper",
            "_home_gui_log_status",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recovery log status refresh",
            "_refresh_home_gui_log_status",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home recovery status smoke",
            "home_gui_log_chars=",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI log clipboard",
            "self.clipboard_append(text)",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README GUI log folder guidance",
            "GUIログ場所",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README runtime error recovery guidance",
            "GUI操作中にエラー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README runtime error command palette guidance",
            "`Ctrl+K` のコマンド検索",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home recovery status guidance",
            "ホームの `復旧ステータス`",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README diagnostic ZIP path guidance",
            "診断ZIPパス",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README diagnostic ZIP verification guidance",
            "診断ZIP検証",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send checklist action",
            "送付前リスト",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send log summary action",
            "show_support_gui_log_summary_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send log summary button",
            "ZIPログ要約",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send log summary reader",
            "read_support_gui_log_summary",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send next action runner",
            "run_support_next_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send next action palette",
            "サポート送付の現在の次アクションを実行",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send dynamic next button",
            "support_next_button_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send next button label",
            "_support_next_button_label",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send next message runner",
            'if action == "送付文コピー":',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send next message delegates",
            "self.copy_support_send_message_action()",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send next message label",
            '"送付文コピー": "次: 送付文"',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send open latest location action",
            "open_latest_support_bundle_location_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send open latest location feedback",
            "最新問い合わせ一式ZIPの場所を開きました",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send copy latest path action",
            "copy_latest_support_bundle_path_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send copy latest path feedback",
            "最新問い合わせ一式ZIPのパスをコピーしました",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send copy latest path clipboard",
            "self.clipboard_append(str(latest.resolve()))",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send copy contact action",
            "copy_support_contact_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send copy contact feedback",
            "サポート連絡先をコピーしました",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send copy contact clipboard",
            "self.clipboard_append(contact)",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send copy message action",
            "copy_support_send_message_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send copy message feedback",
            "サポート送付メモをコピーしました",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send copy message clipboard",
            "self.clipboard_append(message)",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send copy message contents",
            "問い合わせ一式ZIP:",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send contact focus action",
            "focus_support_contact_field",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send contact next action",
            "サポート連絡先を設定",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send contact focus feedback",
            "サポート連絡先を入力して保存してください",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send contact status pill",
            "support_contact_status_pill",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send contact status style",
            "_support_contact_indicator_style",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send verify refreshes summary",
            "self._refresh_support_summary()\n        self._set_text(self.help_text, format_support_bundle_verification",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send checklist refreshes summary",
            "self._refresh_support_summary()\n        try:\n            send_checklist",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send checklist advances next",
            'self._set_support_next_action("送付文コピー")',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send checklist reader",
            "read_support_send_checklist",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send summary panel",
            "サポート送付",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send status summary",
            "support_bundle_status_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send readiness summary",
            "support_send_readiness_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send readiness pill",
            "support_send_readiness_status_pill",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send readiness updater",
            "_set_support_send_readiness",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send readiness style",
            "_support_send_readiness_indicator_style",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send ready status",
            "準備OK",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send missing contact status",
            "連絡先未設定",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send freshness summary",
            "support_bundle_freshness_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send freshness warning",
            "SUPPORT_BUNDLE_FRESHNESS_WARNING_HOURS",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send stale status",
            "要更新",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send unknown freshness status",
            "確認不可",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send status pill",
            "support_bundle_status_pill",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send status style",
            "_support_bundle_indicator_style",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI support send status updater",
            "_set_support_bundle_status",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI first-run KPI typography",
            "first_run_count_vars",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI first-run actionable filter",
            "first_run_action_filter_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI first-run actionable filter renderer",
            "_populate_first_run_tree",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI first-run actionable empty state",
            "要対応項目はありません",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home sales next action",
            "run_home_sales_next_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home sales lightweight summary",
            "_home_sales_lightweight_next_step",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home sales buyer delivery message summary",
            "buyer_messages",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home sales seller delivery receipt summary",
            "seller_receipts",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home buyer send status row",
            "home_buyer_send_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home buyer send summary helper",
            "_home_buyer_send_summary",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home buyer send package verification",
            "buyer_package_errors =",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home buyer send package verification summary",
            "package_errors=buyer_package_errors",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home buyer send package verification warning",
            "ZIP検証NG",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home buyer send next action",
            "home_buyer_send_next_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home buyer send dynamic button",
            "home_buyer_send_button_var",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home buyer send action helper",
            "_home_buyer_send_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home buyer send package verification action",
            '"購入者ZIP検証": "購入者送付: ZIP検証"',
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home buyer send package match helper",
            "_home_buyer_send_message_matches_package",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home buyer send receipt match helper",
            "_home_buyer_send_receipt_matches_delivery",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI home buyer send next runner",
            "run_home_buyer_send_next_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales handoff action",
            "販売一式作成",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales handoff buyer extract action",
            "購入者ZIP抽出",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales handoff buyer verify action",
            "購入者ZIP検証",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales materials action",
            "販売素材作成",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales materials verify action",
            "販売素材検証",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales finalize action",
            "販売一括作成",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales finalize opens buyer delivery",
            "buyer_delivery_dir",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales finalize opens buyer delivery zip",
            "buyer_delivery_package_path",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales finalize opens buyer delivery message",
            "buyer_delivery_message_path",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI buyer delivery message copy action",
            "copy_latest_buyer_delivery_message_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI buyer send readiness action",
            "run_buyer_send_readiness_to_tab",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI buyer send readiness report action",
            "create_buyer_send_readiness_report_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI seller delivery receipt action",
            "create_seller_delivery_receipt_action",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales finalize opens sales plan report",
            "sales_plan_report_path",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales finalize opens seller send checklist",
            "seller_send_checklist_path",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales finalize opens sales evidence manifest",
            "sales_evidence_manifest_path",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales finalize template apply action",
            "テンプレ取込一括",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales plan action",
            "販売ナビ",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales plan report action",
            "販売ナビ保存",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI RC handoff help action",
            "RC引き渡し",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI RC handoff opener",
            "open_rc_handoff",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "gui.py",
            "GUI sales vertical action rail",
            "sales_action_items",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README starter pack guidance",
            "starter-pack",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README repair guidance",
            "auto-note repair",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README troubleshoot guidance",
            "auto-note troubleshoot",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README acceptance guidance",
            "auto-note acceptance",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README acceptance full guidance",
            "auto-note acceptance --project-dir . --full",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README commercial readiness guidance",
            "auto-note commercial-readiness",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README commercial policy review guidance",
            "commercial-readiness --project-dir . --policy-review",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README commercial setup guidance",
            "auto-note commercial-setup",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home sales summary guidance",
            "販売準備サマリー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home buyer send status guidance",
            "購入者ZIP/送付文/送付記録",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home buyer send next button guidance",
            "状態に応じた購入者送付ボタン",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home buyer send ZIP/message match guidance",
            "送付文と最新ZIP名/SHA-256の照合",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README home buyer send receipt match guidance",
            "送付記録と最新ZIP/送付文の照合",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README commercial setup template guidance",
            "commercial-setup --project-dir . --template",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README commercial setup template apply guidance",
            "commercial-setup --project-dir . --apply-latest-template",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README commercial setup safe template guidance",
            "未入力のプレースホルダー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README commercial setup GUI next missing guidance",
            "次の不足へ",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README privacy audit commercial setup template guidance",
            "販売者テンプレート",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README sales handoff guidance",
            "auto-note sales-handoff",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README sales handoff buyer extract guidance",
            "sales-handoff --project-dir . --extract-buyer",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README sales handoff buyer verify guidance",
            "sales-handoff --project-dir . --verify-buyer",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README sales handoff buyer package guidance",
            "sales-handoff --project-dir . --package-buyer",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README sales handoff buyer package verify guidance",
            "sales-handoff --project-dir . --verify-buyer-package",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README sales materials guidance",
            "auto-note sales-materials",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README sales materials verify guidance",
            "sales-materials --project-dir . --verify",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README sales finalize guidance",
            "auto-note sales-finalize",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README sales finalize template apply guidance",
            "sales-finalize --project-dir . --apply-latest-template",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README buyer delivery message copy guidance",
            "送付文コピー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README buyer send readiness guidance",
            "送付前チェック",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README buyer send readiness CLI report guidance",
            "sales-finalize --project-dir . --send-check --send-check-report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README seller delivery receipt guidance",
            "sales-finalize --project-dir . --delivery-receipt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README sales plan guidance",
            "auto-note sales-plan",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README sales plan upload guidance",
            "Upload guidance",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README sales plan report guidance",
            "sales-plan --project-dir . --report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README sales evidence manifest guidance",
            "sales-evidence-manifest",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README RC handoff guidance",
            "docs\\RC_HANDOFF.md",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "README.md",
            "README support send checklist guidance",
            "SUPPORT_SEND_CHECKLIST.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "SUPPORT.md",
            "support guide send checklist guidance",
            "SUPPORT_SEND_CHECKLIST.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "SUPPORT.md",
            "support guide GUI log display guidance",
            "GUIログ表示",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "SUPPORT.md",
            "support guide GUI log copy guidance",
            "GUIログコピー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "SUPPORT.md",
            "support guide GUI log folder guidance",
            "GUIログ場所",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "SUPPORT.md",
            "support guide diagnostic ZIP path guidance",
            "診断ZIPパス",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "SUPPORT.md",
            "support guide diagnostic ZIP verification guidance",
            "診断ZIP検証",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "SUPPORT.md",
            "support guide GUI log summary guidance",
            "GUI_LOG_SUMMARY.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "SUPPORT.md",
            "support guide ZIP log summary action guidance",
            "ZIPログ要約",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "SUPPORT.md",
            "support guide recovery report guidance",
            "復旧レポートコピー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "SUPPORT.md",
            "support guide home recent reports guidance",
            "直近レポート",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "SUPPORT.md",
            "support guide home recent reports copy guidance",
            "パスコピー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "SUPPORT.md",
            "support guide self-test launcher health guidance",
            "launcher health",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRIVACY.md",
            "privacy guide support send checklist guidance",
            "SUPPORT_SEND_CHECKLIST.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness acceptance full command",
            "auto-note acceptance --project-dir . --full",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness commercial command",
            "commercial-readiness",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness commercial policy review command",
            "commercial-readiness --project-dir . --policy-review",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness commercial setup command",
            "commercial-setup",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness home sales summary guidance",
            "販売準備サマリー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness home sales lightweight guidance",
            "軽量判定",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness home sales buyer message guidance",
            "送付文有無",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness recovery report guidance",
            "最新復旧レポート",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness home recent reports guidance",
            "直近レポート",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness home recent reports copy guidance",
            "パスコピー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness first-run actionable filter guidance",
            "要対応だけ",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness self-test launcher health guidance",
            "ランチャー健康チェック",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness commercial setup template command",
            "commercial-setup --project-dir . --template",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness commercial setup template apply command",
            "commercial-setup --project-dir . --apply-latest-template",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness commercial setup safe template guidance",
            "未入力プレースホルダー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness commercial setup GUI next missing guidance",
            "次の不足へ",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness sales handoff command",
            "sales-handoff",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness sales handoff buyer extract command",
            "--extract-buyer",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness sales handoff buyer verify command",
            "--verify-buyer",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness sales handoff buyer package command",
            "--package-buyer",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness sales handoff buyer package verify command",
            "--verify-buyer-package",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness sales materials command",
            "sales-materials",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness sales materials verify command",
            "sales-materials --project-dir . --verify",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness sales finalize command",
            "sales-finalize",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness sales finalize template apply command",
            "sales-finalize --project-dir . --apply-latest-template",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness buyer delivery message copy guidance",
            "送付文コピー",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness buyer send readiness guidance",
            "送付前チェック",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness buyer send readiness CLI report guidance",
            "sales-finalize --project-dir . --send-check --send-check-report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness seller delivery receipt guidance",
            "sales-finalize --project-dir . --delivery-receipt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness sales plan command",
            "sales-plan",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness sales plan upload guidance",
            "Upload guidance",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness sales plan report guidance",
            "sales-plan --project-dir . --report",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "docs" / "PRODUCT_READINESS.md",
            "product readiness sales evidence manifest guidance",
            "sales-evidence-manifest",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "release.py",
            "release starter pack guidance",
            "starter-pack",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "release.py",
            "release repair guidance",
            "auto-note repair",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "release.py",
            "release troubleshoot guidance",
            "auto-note troubleshoot",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "release.py",
            "release buyer acceptance checklist",
            "BUYER_ACCEPTANCE_CHECKLIST.txt",
        )
    )
    checks.append(
        _text_contains_check(
            project_dir / "src" / "auto_note" / "release.py",
            "release buyer acceptance full guidance",
            "auto-note acceptance --project-dir . --full",
        )
    )

    for item in run_diagnostics(project_dir):
        checks.append(QualityCheck(f"diagnostic: {item.name}", "pass" if item.ok else "fail", item.detail))

    if not include_articles:
        return checks

    try:
        reports = inspect_path(project_dir / "articles", pattern=settings.article_glob, append_tags=settings.append_tags_by_default)
    except ArticleError as exc:
        checks.append(QualityCheck("article check", "warn", str(exc)))
    else:
        errors = sum(1 for report in reports if not report.ok)
        warnings = sum(len([issue for issue in report.issues if issue.level == "warn"]) for report in reports)
        if errors:
            checks.append(QualityCheck("article check", "fail", f"{errors} article(s) have errors"))
        elif warnings:
            checks.append(QualityCheck("article check", "warn", f"{warnings} warning(s)"))
        else:
            checks.append(QualityCheck("article check", "pass", f"{len(reports)} article(s) OK"))
        checks.extend(_workflow_checks(reports))

    try:
        refs = inspect_images_path(project_dir / "articles", pattern=settings.article_glob)
    except ArticleError as exc:
        checks.append(QualityCheck("image check", "warn", str(exc)))
    else:
        missing = missing_images(refs)
        large = [ref for ref in refs if ref.large]
        if missing:
            checks.append(QualityCheck("image check", "fail", f"{len(missing)} missing image(s)"))
        elif large:
            checks.append(QualityCheck("image check", "warn", f"{len(large)} large image(s)"))
        else:
            checks.append(QualityCheck("image check", "pass", f"{len(refs)} image reference(s) OK"))

    try:
        reviews = review_path(
            project_dir / "articles",
            pattern=settings.article_glob,
            append_tags=settings.append_tags_by_default,
        )
    except ArticleError as exc:
        checks.append(QualityCheck("article review", "warn", str(exc)))
    else:
        average = round(sum(review.score for review in reviews) / len(reviews)) if reviews else 0
        blockers = sum(1 for review in reviews if review.needs_fix)
        ready = sum(1 for review in reviews if review.ready)
        if blockers:
            status = "warn"
            detail = f"average {average}/100, {blockers} article(s) need fixes, {ready} ready"
        elif ready == len(reviews):
            status = "pass"
            detail = f"average {average}/100, all {len(reviews)} article(s) ready"
        else:
            status = "warn"
            detail = f"average {average}/100, no blockers, {ready}/{len(reviews)} ready"
        checks.append(QualityCheck("article review", status, detail))

    return checks


def format_quality_report(checks: list[QualityCheck]) -> str:
    lines = []
    for check in checks:
        label = {"pass": "OK", "warn": "WARN", "fail": "NG"}.get(check.status, check.status.upper())
        lines.append(f"[{label}] {check.name}: {check.detail}")
    return "\n".join(lines)


def has_failures(checks: list[QualityCheck], *, strict: bool = False) -> bool:
    if any(check.status == "fail" for check in checks):
        return True
    return strict and any(check.status == "warn" for check in checks)


def _path_check(path: Path, name: str) -> QualityCheck:
    return QualityCheck(name, "pass" if path.exists() else "fail", str(path))


def _text_contains_check(path: Path, name: str, needle: str) -> QualityCheck:
    if not path.exists():
        return QualityCheck(name, "fail", f"file not found: {path}")
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return QualityCheck(name, "fail", str(exc))
    if needle not in text:
        return QualityCheck(name, "fail", f"missing text: {needle}")
    return QualityCheck(name, "pass", "present")


def _version_consistency_check(pyproject: Path, init_file: Path) -> QualityCheck:
    try:
        pyproject_text = pyproject.read_text(encoding="utf-8", errors="replace")
        init_text = init_file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return QualityCheck("version consistency", "fail", str(exc))
    pyproject_version = _first_match(pyproject_text, r'(?m)^\s*version\s*=\s*["\']([^"\']+)["\']')
    package_version = _first_match(init_text, r'(?m)^\s*__version__\s*=\s*["\']([^"\']+)["\']')
    if not pyproject_version or not package_version:
        return QualityCheck("version consistency", "fail", "version value missing")
    if pyproject_version != package_version:
        return QualityCheck(
            "version consistency",
            "fail",
            f"pyproject={pyproject_version}, package={package_version}",
        )
    return QualityCheck("version consistency", "pass", pyproject_version)


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _workflow_checks(reports) -> list[QualityCheck]:
    checks: list[QualityCheck] = []
    titles: dict[str, int] = {}
    invalid_statuses: list[str] = []
    invalid_schedules: list[str] = []
    for report in reports:
        article = report.article
        normalized_title = article.title.strip().lower()
        titles[normalized_title] = titles.get(normalized_title, 0) + 1
        if article.status and article.status not in VALID_STATUSES:
            invalid_statuses.append(article.source.name)
        if article.scheduled and not _valid_schedule(article.scheduled):
            invalid_schedules.append(article.source.name)

    duplicates = [title for title, count in titles.items() if title and count > 1]
    if duplicates:
        checks.append(QualityCheck("duplicate titles", "warn", f"{len(duplicates)} duplicate title(s)"))
    else:
        checks.append(QualityCheck("duplicate titles", "pass", "none"))

    if invalid_statuses:
        checks.append(QualityCheck("workflow status", "fail", f"{len(invalid_statuses)} invalid status value(s)"))
    else:
        checks.append(QualityCheck("workflow status", "pass", "all status values are known"))

    if invalid_schedules:
        checks.append(QualityCheck("schedule format", "fail", f"{len(invalid_schedules)} invalid schedule value(s)"))
    else:
        checks.append(QualityCheck("schedule format", "pass", "all schedule values are parseable"))
    return checks


def _valid_schedule(value: str) -> bool:
    normalized = value.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S"):
        try:
            datetime.strptime(normalized, fmt)
            return True
        except ValueError:
            pass
    return False
