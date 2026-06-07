from pathlib import Path
from contextlib import redirect_stdout
from datetime import datetime, timedelta
import io
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from auto_note.__main__ import main as cli_main
from auto_note.action_plan import ActionPlanReport, ActionPlanStep, build_action_plan, format_action_plan
from auto_note.acceptance import (
    format_acceptance_report,
    has_acceptance_blockers,
    list_acceptance_reports,
    run_acceptance_check,
    write_acceptance_report,
)
from auto_note.article import ArticleError, body_with_tags, load_article, write_markdown, write_text_atomic
from auto_note.autosave import autosave_state, clear_autosave, has_newer_autosave, read_autosave, write_autosave
from auto_note.backup import create_backup, format_backup_inspection, inspect_backup, restore_backup, verify_backup
from auto_note.app_info import collect_app_info, format_app_info
from auto_note.commercial import (
    format_commercial_readiness_report,
    has_commercial_readiness_blockers,
    list_commercial_policy_reviews,
    list_commercial_readiness_reports,
    run_commercial_readiness,
    write_commercial_policy_review,
    write_commercial_readiness_report,
)
from auto_note.commercial_setup import (
    apply_commercial_setup_template,
    commercial_setup_next_field,
    create_commercial_setup_template,
    format_commercial_setup_apply_result,
    format_commercial_settings,
    list_commercial_setup_templates,
    update_commercial_settings,
)
from auto_note.diagnostics import create_diagnostic_report, preview_diagnostic_report, run_diagnostics
from auto_note.export import export_article_inventory
from auto_note.first_run import _top_action_item, format_first_run_report, has_first_run_blockers, run_first_run_checklist
from auto_note.gui import smoke_gui
from auto_note.gui_errors import append_gui_error, gui_error_log_path
from auto_note.history import create_revision, list_revisions, restore_revision
from auto_note.images import (
    format_image_report,
    image_info,
    import_image_for_article,
    inspect_images_path,
    missing_images,
    set_article_cover,
)
from auto_note.inspect import inspect_article
from auto_note.improvement_plan import (
    build_improvement_plan,
    format_improvement_plan,
    has_improvement_plan_blockers,
    write_improvement_plan_report,
)
from auto_note.licenses import collect_dependency_notices, format_dependency_notices, write_dependency_notices
from auto_note.maintenance import cleanup_generated_files, format_cleanup_report
from auto_note.manual import write_manual_post_helper
from auto_note.overview import (
    build_overview,
    format_overview_report,
    has_overview_blockers,
    write_overview_report,
)
from auto_note.paths import unique_path
from auto_note.preflight import (
    PreflightItem,
    PreflightReport,
    format_preflight_report,
    has_preflight_blockers,
    run_preflight,
)
from auto_note.privacy import format_privacy_audit_report, has_privacy_audit_blockers, run_privacy_audit
from auto_note.publish_ready import (
    format_publish_ready_report,
    has_publish_ready_blockers,
    run_publish_ready,
)
from auto_note.publish_queue import (
    build_publish_queue,
    format_publish_queue_report,
    has_publish_queue_blockers,
    write_publish_queue_report,
)
from auto_note.quality import has_failures, run_quality_checks
from auto_note.quickstart import QuickstartItem, QuickstartReport, format_quickstart_report, has_quickstart_blockers, run_quickstart
from auto_note.readiness import format_readiness_report, run_readiness
from auto_note.repair import format_repair_report, has_repair_blockers, run_repair
from auto_note.release import create_release_package, format_release_verification, verify_release_package
from auto_note.review import format_review_report, has_review_blockers, review_article, review_path
from auto_note.sales_handoff import (
    create_sales_handoff,
    extract_buyer_delivery,
    format_buyer_delivery_package_verification,
    format_buyer_delivery_result,
    format_buyer_delivery_verification,
    format_sales_handoff_verification,
    list_buyer_deliveries,
    list_buyer_delivery_packages,
    list_sales_handoffs,
    package_buyer_delivery,
    verify_buyer_delivery,
    verify_buyer_delivery_package,
    verify_sales_handoff,
)
from auto_note.sales_finalize import (
    create_sales_finalize,
    format_buyer_send_readiness_report,
    format_sales_finalize_details,
    format_sales_finalize_report,
    has_buyer_send_readiness_blockers,
    has_sales_finalize_blockers,
    list_buyer_delivery_messages,
    list_buyer_send_readiness_reports,
    list_sales_evidence_manifests,
    list_sales_finalize_reports,
    list_seller_delivery_receipts,
    run_buyer_send_readiness,
)
from auto_note.sales_materials import (
    create_sales_materials,
    format_sales_materials_verification,
    list_sales_materials,
    verify_sales_materials,
)
from auto_note.sales_plan import (
    build_sales_plan,
    format_sales_plan,
    has_sales_plan_blockers,
    list_sales_plan_reports,
    write_sales_plan_report,
)
from auto_note.scaffold import create_article, create_practice_article, list_article_templates
from auto_note.settings import AppSettings, inspect_settings, list_settings_recovery_files, load_settings, save_settings
from auto_note.selftest import _self_test_quickstart_item, format_self_test_report, run_self_test, write_self_test_report
from auto_note.setup_check import format_setup_report, run_setup_check
from auto_note.starter import (
    cleanup_starter_pack,
    create_starter_pack,
    format_starter_cleanup_result,
    format_starter_pack_result,
)
from auto_note.support import (
    build_support_request,
    create_support_bundle,
    create_support_request,
    format_support_bundle_verification,
    verify_support_bundle,
)
from auto_note.troubleshoot import format_troubleshoot_report, has_troubleshoot_blockers, run_troubleshoot
from auto_note.workflow import (
    add_idea,
    export_calendar,
    format_calendar,
    format_calendar_export,
    inspect_ideas,
    list_calendar_exports,
    list_idea_recovery_files,
    load_ideas,
    mark_article_published,
    promote_idea,
    set_article_status,
    set_article_schedule,
    update_article_metadata,
)
from auto_note.workflow_smoke import (
    format_workflow_smoke_report,
    has_workflow_smoke_blockers,
    run_workflow_smoke,
    write_workflow_smoke_report,
)


class ArticleTests(unittest.TestCase):
    def test_loads_frontmatter_title_and_tags(self) -> None:
        article = _write_and_load(
            """---
title: テスト記事
tags:
  - note
  - 自動 投稿
publish: true
---

本文です。
"""
        )

        self.assertEqual(article.title, "テスト記事")
        self.assertEqual(article.tags, ["note", "自動 投稿"])
        self.assertTrue(article.publish)
        self.assertIn("#自動投稿", body_with_tags(article))

    def test_uses_first_heading_as_title(self) -> None:
        article = _write_and_load(
            """# 見出しタイトル

本文です。
"""
        )

        self.assertEqual(article.title, "見出しタイトル")
        self.assertEqual(article.body, "本文です。")

    def test_loads_summary_and_cover_aliases(self) -> None:
        article = _write_and_load(
            """---
title: テスト記事
description: これは概要です
image: cover.png
---

本文です。
"""
        )

        self.assertEqual(article.summary, "これは概要です")
        self.assertEqual(article.cover, "cover.png")

    def test_inspect_reports_missing_local_image(self) -> None:
        article = _write_and_load(
            """---
title: 画像記事
tags: note
---

![alt](missing.png)
"""
        )

        report = inspect_article(article)
        self.assertFalse(report.ok)
        self.assertTrue(any(issue.level == "error" for issue in report.issues))

    def test_create_article_template_can_be_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = create_article("タイトル: テスト", articles_dir=Path(tmp), tags=["note", "自動化"])
            article = load_article(path)

        self.assertEqual(article.title, "タイトル: テスト")
        self.assertEqual(article.tags, ["note", "自動化"])
        self.assertEqual(article.status, "draft")

    def test_create_article_with_named_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = create_article("レビュー記事", articles_dir=Path(tmp), tags=["note"], template="review")
            text = path.read_text(encoding="utf-8")
            templates = dict(list_article_templates())

        self.assertIn("review", templates)
        self.assertIn("## よかった点", text)
        self.assertIn("## 気になった点", text)

    def test_article_writes_are_atomic_and_leave_no_temp_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp) / "articles"
            path = create_article("安全保存記事", articles_dir=articles_dir, tags=["note"])
            write_markdown(
                path,
                {
                    "title": "安全保存記事",
                    "tags": ["note"],
                    "status": "ready",
                    "publish": False,
                },
                "本文を安全に保存します。",
            )
            write_text_atomic(path, path.read_text(encoding="utf-8") + "\n追記します。\n")
            article = load_article(path)
            temp_files = list(articles_dir.glob("*.tmp")) + list(articles_dir.glob(".*.tmp"))

        self.assertEqual(article.status, "ready")
        self.assertIn("追記します。", article.body)
        self.assertEqual(temp_files, [])

    def test_schedule_and_mark_published_update_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = create_article("予定記事", articles_dir=Path(tmp), tags=["note"])
            scheduled = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d 09:00")
            set_article_schedule(path, scheduled)
            article = load_article(path)
            self.assertEqual(article.status, "scheduled")
            self.assertEqual(article.scheduled, scheduled)
            self.assertIn("予定記事", format_calendar(Path(tmp), days=7))

            mark_article_published(path, url="https://note.com/example/n/n123")
            article = load_article(path)

        self.assertEqual(article.status, "published")
        self.assertEqual(article.published_url, "https://note.com/example/n/n123")

    def test_idea_can_be_promoted_to_article(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            idea = add_idea(project, "アイデア記事", note="概要", tags=["note"])
            path = promote_idea(project, idea.id, articles_dir=project / "articles")
            article = load_article(path)

        self.assertEqual(article.title, "アイデア記事")
        self.assertEqual(article.summary, "概要")
        self.assertEqual(article.tags, ["note"])

    def test_corrupt_ideas_fall_back_and_are_backed_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            ideas_file = project / ".auto-note" / "ideas.json"
            ideas_file.parent.mkdir(parents=True)
            ideas_file.write_text("{not json", encoding="utf-8")

            ideas = load_ideas(project)
            status = inspect_ideas(project)
            diagnostics = run_diagnostics(project)
            setup_items = run_setup_check(project, create=False)
            repaired_setup = run_setup_check(project, create=True)
            repaired_status = inspect_ideas(project)
            recovery_files = list_idea_recovery_files(project)
            recovery_text = recovery_files[0].read_text(encoding="utf-8") if recovery_files else ""
            added = add_idea(project, "復旧後のアイデア", note="メモ", tags=["note"])
            temp_files = list((project / ".auto-note").glob("*ideas.json*.tmp"))

        self.assertEqual(ideas, [])
        self.assertFalse(status.ok)
        self.assertIn("invalid ideas.json", status.detail)
        self.assertTrue(any(item.name == "ideas file" and not item.ok for item in diagnostics))
        self.assertTrue(any(item.name == "ideas readable" and not item.ok for item in setup_items))
        self.assertTrue(any(item.name == "ideas recovery backup" for item in repaired_setup))
        self.assertEqual(added.id, 1)
        self.assertTrue(repaired_status.ok)
        self.assertEqual(len(recovery_files), 1)
        self.assertEqual(recovery_text, "{not json")
        self.assertEqual(temp_files, [])

    def test_settings_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            settings = AppSettings(
                default_tags=["note", "仕事"],
                default_status="ready",
                append_tags_by_default=False,
                open_note_with_helper=False,
                article_glob="*.md",
                onboarding_seen=True,
                support_contact="support@example.com",
                seller_name="Auto Note Shop",
                sales_channel_url="https://example.com/auto-note",
                refund_policy_url="https://example.com/refund",
                commercial_terms_reviewed=True,
                commercial_support_scope_confirmed=True,
                commercial_reviewed_at="2026-06-06 10:00:00",
                image_optimize_by_default=True,
                image_max_width=1200,
                image_quality=80,
            )
            save_settings(project, settings)
            loaded = load_settings(project)

        self.assertEqual(loaded.default_tags, ["note", "仕事"])
        self.assertEqual(loaded.default_status, "ready")
        self.assertFalse(loaded.append_tags_by_default)
        self.assertTrue(loaded.onboarding_seen)
        self.assertEqual(loaded.support_contact, "support@example.com")
        self.assertEqual(loaded.seller_name, "Auto Note Shop")
        self.assertEqual(loaded.sales_channel_url, "https://example.com/auto-note")
        self.assertEqual(loaded.refund_policy_url, "https://example.com/refund")
        self.assertTrue(loaded.commercial_terms_reviewed)
        self.assertTrue(loaded.commercial_support_scope_confirmed)
        self.assertEqual(loaded.commercial_reviewed_at, "2026-06-06 10:00:00")
        self.assertTrue(loaded.image_optimize_by_default)
        self.assertEqual(loaded.image_max_width, 1200)
        self.assertEqual(loaded.image_quality, 80)

    def test_settings_ignore_unknown_keys_and_clamp_image_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            settings_file = project / ".auto-note" / "settings.json"
            settings_file.parent.mkdir(parents=True)
            settings_file.write_text(
                '{"unknown": true, "image_max_width": 99999, "image_quality": 10}',
                encoding="utf-8",
            )

            loaded = load_settings(project)

        self.assertEqual(loaded.image_max_width, 4000)
        self.assertEqual(loaded.image_quality, 30)
        self.assertEqual(loaded.seller_name, "")
        self.assertFalse(loaded.commercial_terms_reviewed)

    def test_commercial_setup_updates_seller_settings_and_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            missing_text = format_commercial_settings(load_settings(project))
            initial_next_field = commercial_setup_next_field(load_settings(project))
            empty_template = create_commercial_setup_template(project)
            empty_template_text = empty_template.path.read_text(encoding="utf-8")
            updated = update_commercial_settings(
                project,
                seller_name="Auto Note Shop",
                sales_channel_url="https://example.com/auto-note",
                refund_policy_url="https://example.com/refund",
                support_contact="https://example.com/support",
                terms_reviewed=True,
                support_scope_confirmed=True,
            )
            updated_next_field = commercial_setup_next_field(updated)
            text = format_commercial_settings(updated)
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(
                    [
                        "commercial-setup",
                        "--project-dir",
                        str(project),
                        "--seller-name",
                        "CLI Shop",
                        "--sales-url",
                        "https://example.com/sales",
                        "--refund-url",
                        "https://example.com/policy",
                        "--support-contact",
                        "https://example.com/help",
                        "--terms-reviewed",
                        "--support-scope-confirmed",
                    ]
                )
            template = create_commercial_setup_template(project)
            template_text = template.path.read_text(encoding="utf-8")
            template_output = io.StringIO()
            with redirect_stdout(template_output):
                template_code = cli_main(["commercial-setup", "--project-dir", str(project), "--template"])
            template_list_output = io.StringIO()
            with redirect_stdout(template_list_output):
                template_list_code = cli_main(["commercial-setup", "--project-dir", str(project), "--list-templates"])
            templates = list_commercial_setup_templates(project)
            clear_output = io.StringIO()
            with redirect_stdout(clear_output):
                clear_code = cli_main(["commercial-setup", "--project-dir", str(project), "--clear-review"])
            cleared = load_settings(project)
            template_to_apply = templates[0]
            template_to_apply_text = template_to_apply.read_text(encoding="utf-8")
            filled_text = (
                template_to_apply_text.replace("seller_name: CLI Shop", "seller_name: Applied Shop")
                .replace("sales_url: https://example.com/sales", "sales_url: https://example.com/applied")
                .replace("refund_url: https://example.com/policy", "refund_url: https://example.com/applied-refund")
                .replace("support_contact: https://example.com/help", "support_contact: https://example.com/applied-support")
            )
            template_to_apply.write_text(filled_text, encoding="utf-8")
            applied = apply_commercial_setup_template(project, template_to_apply)
            apply_text = format_commercial_setup_apply_result(applied)
            apply_output = io.StringIO()
            with redirect_stdout(apply_output):
                apply_code = cli_main(["commercial-setup", "--project-dir", str(project), "--apply-template", str(template_to_apply)])
            latest_apply_output = io.StringIO()
            with redirect_stdout(latest_apply_output):
                latest_apply_code = cli_main(["commercial-setup", "--project-dir", str(project), "--apply-latest-template"])
            loaded = load_settings(project)

        self.assertIn("missing fields: seller name / 販売者・屋号", missing_text)
        self.assertIn("sales page URL / 販売ページURL", missing_text)
        self.assertIn("refund policy URL / 返金方針URL", missing_text)
        self.assertIn("support contact / サポート連絡先", missing_text)
        self.assertIn("terms reviewed / 利用条件・商用方針確認", missing_text)
        self.assertIn("support scope confirmed / サポート範囲確認", missing_text)
        self.assertIn("completion: 0/6", missing_text)
        self.assertIn("next actions:", missing_text)
        self.assertIn('CLI: --seller-name "Your Shop"', missing_text)
        self.assertIn("CLI: --support-scope-confirmed", missing_text)
        self.assertEqual(initial_next_field, "seller_name")
        self.assertIn("Completion: 0/6", empty_template_text)
        self.assertIn("--apply-latest-template", empty_template_text)
        self.assertIn("Field Guide / 入力の目安", empty_template_text)
        self.assertNotIn('--seller-name "[販売者/屋号]"', empty_template_text)
        self.assertIn("seller name: Auto Note Shop", text)
        self.assertIn("completion: 6/6", text)
        self.assertIn("missing fields: (none)", text)
        self.assertIn("terms reviewed: yes", text)
        self.assertIn("販売素材へ反映する: auto-note sales-materials --project-dir .", text)
        self.assertIn("販売ナビで最終確認する: auto-note sales-plan --project-dir .", text)
        self.assertEqual(updated_next_field, "")
        self.assertEqual(code, 0)
        self.assertIn("commercial setup saved", cli_output.getvalue())
        self.assertIn("seller name: CLI Shop", cli_output.getvalue())
        self.assertIn("missing fields: (none)", cli_output.getvalue())
        self.assertEqual(template.missing, 0)
        self.assertIn("Commercial Setup Template", template_text)
        self.assertIn("Completion: 6/6", template_text)
        self.assertIn("Direct CLI Command", template_text)
        self.assertIn("--apply-latest-template", template_text)
        self.assertIn("CLI Shop", template_text)
        self.assertIn("python -m auto_note commercial-setup", template_text)
        self.assertEqual(template_code, 0)
        self.assertIn("commercial setup template created:", template_output.getvalue())
        self.assertIn("missing: 0", template_output.getvalue())
        self.assertEqual(template_list_code, 0)
        self.assertGreaterEqual(len(templates), 2)
        self.assertIn("commercial-setup-template-", template_list_output.getvalue())
        self.assertEqual(clear_code, 0)
        self.assertFalse(cleared.commercial_terms_reviewed)
        self.assertFalse(cleared.commercial_support_scope_confirmed)
        self.assertEqual(cleared.commercial_reviewed_at, "")
        self.assertEqual(applied.missing, 0)
        self.assertIn("updated: seller_name", apply_text)
        self.assertIn("販売素材へ反映する: auto-note sales-materials --project-dir .", apply_text)
        self.assertIn("missing fields: (none)", apply_text)
        self.assertEqual(apply_code, 0)
        self.assertEqual(latest_apply_code, 0)
        self.assertIn("Commercial setup template applied", apply_output.getvalue())
        self.assertIn("Commercial setup template applied", latest_apply_output.getvalue())
        self.assertEqual(loaded.seller_name, "Applied Shop")
        self.assertEqual(loaded.sales_channel_url, "https://example.com/applied")
        self.assertEqual(loaded.refund_policy_url, "https://example.com/applied-refund")
        self.assertEqual(loaded.support_contact, "https://example.com/applied-support")
        self.assertTrue(loaded.commercial_terms_reviewed)
        self.assertTrue(loaded.commercial_support_scope_confirmed)
        self.assertNotEqual(loaded.commercial_reviewed_at, "")

    def test_commercial_setup_warns_about_non_public_sales_contacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            update_commercial_settings(
                project,
                seller_name="Risky Shop",
                sales_channel_url="example sales page",
                refund_policy_url="refund policy",
                support_contact="help@example.com",
                terms_reviewed=True,
                support_scope_confirmed=True,
            )

            settings_text = format_commercial_settings(load_settings(project))
            next_field = commercial_setup_next_field(load_settings(project))
            readiness = run_commercial_readiness(project)
            readiness_text = format_commercial_readiness_report(readiness)
            materials = create_sales_materials(project)
            material_errors = verify_sales_materials(materials.path, strict=True, project_dir=project)
            verification_text = format_sales_materials_verification(materials.path, material_errors, strict=True)

        statuses = {item.name: item.status for item in readiness.items}
        self.assertIn("sales page URL should start with http:// or https://", settings_text)
        self.assertIn("refund policy URL should start with http:// or https://", settings_text)
        self.assertIn("support contact is a raw email address", settings_text)
        self.assertEqual(next_field, "sales_channel_url")
        self.assertEqual(statuses["販売者プロフィール"], "warn")
        self.assertEqual(statuses["サポート連絡先"], "warn")
        self.assertIn("warnings:", readiness_text)
        self.assertIn("commercial setup warning: sales page URL should start", verification_text)
        self.assertIn("commercial setup warning: support contact is a raw email address", verification_text)

    def test_corrupt_settings_fall_back_and_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            settings_file = project / ".auto-note" / "settings.json"
            settings_file.parent.mkdir(parents=True)
            settings_file.write_text("{not json", encoding="utf-8")

            loaded = load_settings(project)
            status = inspect_settings(project)
            diagnostics = run_diagnostics(project)
            setup_items = run_setup_check(project, create=False)
            repaired = run_setup_check(project, create=True)
            repaired_status = inspect_settings(project)
            recovery_files = list_settings_recovery_files(project)
            recovery_text = recovery_files[0].read_text(encoding="utf-8") if recovery_files else ""
            temp_files = list((project / ".auto-note").glob("*settings.json*.tmp"))

        self.assertEqual(loaded.default_tags, ["note"])
        self.assertFalse(status.ok)
        self.assertIn("invalid settings.json", status.detail)
        self.assertTrue(any(item.name == "settings file" and not item.ok for item in diagnostics))
        self.assertTrue(any(item.name == "settings readable" and not item.ok for item in setup_items))
        self.assertTrue(any(item.name == "settings readable" and item.ok for item in repaired))
        self.assertTrue(any(item.name == "settings recovery backup" for item in repaired))
        self.assertTrue(repaired_status.ok)
        self.assertEqual(len(recovery_files), 1)
        self.assertEqual(recovery_text, "{not json")
        self.assertEqual(temp_files, [])

    def test_backup_and_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article_path = create_article("バックアップ記事", articles_dir=project / "articles", tags=["note"])
            install_info = project / ".auto-note" / "install-info.json"
            install_info.parent.mkdir(parents=True, exist_ok=True)
            install_info.write_text(
                '{"installed_at":"2026-06-06T10:00:00","version":"0.1.0","preinstall_backup":"backup.zip"}',
                encoding="utf-8",
            )
            backup = create_backup(project)
            inspection = inspect_backup(backup)
            backup_errors = verify_backup(backup)
            inspection_text = format_backup_inspection(inspection)
            diagnostics = run_diagnostics(project)
            self.assertTrue(backup.exists())
            self.assertTrue(inspection.ok)
            self.assertEqual(backup_errors, [])
            self.assertEqual(len(inspection.article_files), 1)
            self.assertIn("Backup inspection", inspection_text)
            self.assertTrue(any(item.name == "project directory" and item.ok for item in diagnostics))
            self.assertTrue(any(item.name == "auto-note version" and item.ok for item in diagnostics))
            self.assertTrue(
                any(
                    item.name == "commercial setup"
                    and item.ok
                    and "completion 0/6" in item.detail
                    and "next field seller_name" in item.detail
                    for item in diagnostics
                )
            )
            self.assertTrue(any(item.name == "install info" and "backup.zip" in item.detail for item in diagnostics))

            create_commercial_setup_template(project)
            write_sales_plan_report(project)
            report = create_diagnostic_report(project)
            preview = preview_diagnostic_report(project)
            self.assertTrue(report.exists())
            with zipfile.ZipFile(report) as archive:
                names = archive.namelist()
                self.assertIn("diagnostics.txt", names)
                self.assertIn("article-index.txt", names)
                self.assertIn("article-review.txt", names)
                self.assertIn("first-run.txt", names)
                self.assertIn("acceptance.txt", names)
                self.assertIn("self-test.txt", names)
                self.assertIn("action-plan.txt", names)
                self.assertIn("overview.txt", names)
                self.assertIn("calendar.txt", names)
                self.assertIn("quickstart.txt", names)
                self.assertIn("publish-ready.txt", names)
                self.assertIn("improvement-plan.txt", names)
                self.assertIn("publish-queue.txt", names)
                self.assertIn("gui-smoke.txt", names)
                self.assertIn("preflight.txt", names)
                self.assertIn("troubleshoot.txt", names)
                self.assertIn("readiness.txt", names)
                self.assertIn("commercial-readiness.txt", names)
                self.assertIn("commercial-setup-template.txt", names)
                self.assertIn("sales-plan.txt", names)
                self.assertIn("sales-materials.txt", names)
                self.assertIn("sales-finalize.txt", names)
                self.assertIn("seller-send-checklist.txt", names)
                self.assertIn("sales-evidence-manifest.json", names)
                self.assertIn("product-quality.txt", names)
                self.assertIn("quality.txt", names)
                self.assertIn("maintenance-summary.txt", names)
                diagnostics_text = archive.read("diagnostics.txt").decode("utf-8")
                article_index = archive.read("article-index.txt").decode("utf-8")
                article_review = archive.read("article-review.txt").decode("utf-8")
                first_run_text = archive.read("first-run.txt").decode("utf-8")
                acceptance_text = archive.read("acceptance.txt").decode("utf-8")
                self_test_text = archive.read("self-test.txt").decode("utf-8")
                action_plan_text = archive.read("action-plan.txt").decode("utf-8")
                overview_text = archive.read("overview.txt").decode("utf-8")
                calendar_text = archive.read("calendar.txt").decode("utf-8")
                quickstart_text = archive.read("quickstart.txt").decode("utf-8")
                publish_ready_text = archive.read("publish-ready.txt").decode("utf-8")
                improvement_plan_text = archive.read("improvement-plan.txt").decode("utf-8")
                publish_queue_text = archive.read("publish-queue.txt").decode("utf-8")
                gui_smoke_text = archive.read("gui-smoke.txt").decode("utf-8")
                preflight_text = archive.read("preflight.txt").decode("utf-8")
                troubleshoot_text = archive.read("troubleshoot.txt").decode("utf-8")
                readiness_text = archive.read("readiness.txt").decode("utf-8")
                commercial_readiness_text = archive.read("commercial-readiness.txt").decode("utf-8")
                commercial_setup_template_text = archive.read("commercial-setup-template.txt").decode("utf-8")
                sales_plan_text = archive.read("sales-plan.txt").decode("utf-8")
                sales_materials_text = archive.read("sales-materials.txt").decode("utf-8")
                sales_finalize_text = archive.read("sales-finalize.txt").decode("utf-8")
                seller_send_checklist_text = archive.read("seller-send-checklist.txt").decode("utf-8")
                sales_evidence_manifest_text = archive.read("sales-evidence-manifest.json").decode("utf-8")
                product_quality_text = archive.read("product-quality.txt").decode("utf-8")
                quality_text = archive.read("quality.txt").decode("utf-8")
                maintenance_text = archive.read("maintenance-summary.txt").decode("utf-8")
            self.assertNotIn(str(project), diagnostics_text)
            self.assertIn("commercial setup: completion 0/6", diagnostics_text)
            self.assertIn("next field seller_name", diagnostics_text)
            self.assertNotIn(str(project), article_review)
            self.assertNotIn(str(project), first_run_text)
            self.assertNotIn(str(project), acceptance_text)
            self.assertNotIn(str(project), self_test_text)
            self.assertNotIn(str(project), action_plan_text)
            self.assertNotIn(str(project), overview_text)
            self.assertNotIn(str(project), calendar_text)
            self.assertNotIn(str(project), quickstart_text)
            self.assertNotIn(str(project), publish_ready_text)
            self.assertNotIn(str(project), improvement_plan_text)
            self.assertNotIn(str(project), publish_queue_text)
            self.assertNotIn(str(project), gui_smoke_text)
            self.assertNotIn(str(project), preflight_text)
            self.assertNotIn(str(project), troubleshoot_text)
            self.assertNotIn(str(project), readiness_text)
            self.assertNotIn(str(project), commercial_readiness_text)
            self.assertNotIn(str(project), commercial_setup_template_text)
            self.assertNotIn(str(project), sales_plan_text)
            self.assertNotIn(str(project), sales_materials_text)
            self.assertNotIn(str(project), sales_finalize_text)
            self.assertNotIn(str(project), seller_send_checklist_text)
            self.assertNotIn(str(project), sales_evidence_manifest_text)
            self.assertNotIn(str(project), product_quality_text)
            self.assertNotIn(str(project), quality_text)
            self.assertNotIn(str(project), maintenance_text)
            self.assertIn("latest_backup_verified: yes", maintenance_text)
            self.assertIn("Troubleshooting report", troubleshoot_text)
            self.assertIn("Acceptance check", acceptance_text)
            self.assertIn("Commercial readiness", commercial_readiness_text)
            self.assertIn("Commercial Setup Template", commercial_setup_template_text)
            self.assertIn("Sales plan / 販売ナビ", sales_plan_text)
            self.assertIn("Sales materials / 販売素材", sales_materials_text)
            self.assertIn("Sales finalize / 販売準備一括", sales_finalize_text)
            self.assertIn("Seller send checklist", seller_send_checklist_text)
            self.assertIn("No sales evidence manifests found", sales_evidence_manifest_text)
            self.assertIn("latest_backup_restorable_files: 1", maintenance_text)
            self.assertIn("acceptance_reports:", maintenance_text)
            self.assertIn("commercial_readiness_reports:", maintenance_text)
            self.assertIn("commercial_policy_reviews:", maintenance_text)
            self.assertIn("commercial_setup_templates:", maintenance_text)
            self.assertIn("sales_handoffs:", maintenance_text)
            self.assertIn("sales_materials:", maintenance_text)
            self.assertIn("sales_plan_reports:", maintenance_text)
            self.assertIn("sales_finalize_reports:", maintenance_text)
            self.assertIn("seller_send_checklists:", maintenance_text)
            self.assertIn("buyer_delivery_messages:", maintenance_text)
            self.assertIn("buyer_send_readiness_reports:", maintenance_text)
            self.assertIn("seller_delivery_receipts:", maintenance_text)
            self.assertIn("sales_evidence_manifests:", maintenance_text)
            self.assertIn("privacy_failed_cleanup_candidates: 0", maintenance_text)
            self.assertIn("privacy_failed_cleanup_candidates_including_releases: 0", maintenance_text)
            self.assertIn("calendar_exports:", maintenance_text)
            self.assertNotIn("バックアップ記事", article_index)
            self.assertNotIn("バックアップ記事", article_review)
            self.assertNotIn("バックアップ記事", first_run_text)
            self.assertNotIn("バックアップ記事", acceptance_text)
            self.assertNotIn("バックアップ記事", commercial_readiness_text)
            self.assertNotIn("バックアップ記事", sales_plan_text)
            self.assertNotIn("バックアップ記事", sales_materials_text)
            self.assertNotIn("バックアップ記事", sales_finalize_text)
            self.assertNotIn("バックアップ記事", seller_send_checklist_text)
            self.assertNotIn("バックアップ記事", sales_evidence_manifest_text)
            self.assertNotIn("バックアップ記事", self_test_text)
            self.assertNotIn("バックアップ記事", action_plan_text)
            self.assertNotIn("バックアップ記事", overview_text)
            self.assertNotIn("バックアップ記事", calendar_text)
            self.assertNotIn("バックアップ記事", publish_ready_text)
            self.assertNotIn("バックアップ記事", improvement_plan_text)
            self.assertNotIn("バックアップ記事", publish_queue_text)
            self.assertNotIn(article_path.name, publish_ready_text)
            self.assertNotIn(article_path.name, improvement_plan_text)
            self.assertNotIn(article_path.name, overview_text)
            self.assertNotIn(article_path.name, calendar_text)
            self.assertNotIn(article_path.name, publish_queue_text)
            self.assertNotIn(article_path.name, quickstart_text)
            self.assertNotIn(article_path.name, commercial_readiness_text)
            self.assertNotIn(article_path.name, commercial_setup_template_text)
            self.assertNotIn(article_path.name, sales_plan_text)
            self.assertNotIn(article_path.name, sales_materials_text)
            self.assertNotIn(article_path.name, sales_finalize_text)
            self.assertNotIn(article_path.name, seller_send_checklist_text)
            self.assertIn("Diagnostic report preview", preview)
            self.assertIn("- article-review.txt", preview)
            self.assertIn("- first-run.txt", preview)
            self.assertIn("- acceptance.txt", preview)
            self.assertIn("- self-test.txt", preview)
            self.assertIn("- action-plan.txt", preview)
            self.assertIn("- overview.txt", preview)
            self.assertIn("- calendar.txt", preview)
            self.assertIn("- quickstart.txt", preview)
            self.assertIn("- publish-ready.txt", preview)
            self.assertIn("- improvement-plan.txt", preview)
            self.assertIn("- publish-queue.txt", preview)
            self.assertIn("- gui-smoke.txt", preview)
            self.assertIn("- preflight.txt", preview)
            self.assertIn("- troubleshoot.txt", preview)
            self.assertIn("- readiness.txt", preview)
            self.assertIn("- commercial-readiness.txt", preview)
            self.assertIn("- commercial-setup-template.txt", preview)
            self.assertIn("- sales-plan.txt", preview)
            self.assertIn("- sales-materials.txt", preview)
            self.assertIn("- sales-finalize.txt", preview)
            self.assertIn("- seller-send-checklist.txt", preview)
            self.assertIn("- sales-evidence-manifest.json", preview)
            self.assertIn("- product-quality.txt", preview)
            self.assertIn("- quality.txt", preview)
            self.assertIn("Article review", preview)
            self.assertIn("First-run checklist", preview)
            self.assertIn("Acceptance check", preview)
            self.assertIn("Self-test report", preview)
            self.assertIn("Action plan", preview)
            self.assertIn("Overview / 運用サマリー", preview)
            self.assertIn("Calendar / 公開予定", preview)
            self.assertIn("Quickstart report", preview)
            self.assertIn("Publish readiness report", preview)
            self.assertIn("Improvement plan / 改善プラン", preview)
            self.assertIn("Publish queue", preview)
            self.assertIn("GUI smoke", preview)
            self.assertIn("Preflight report", preview)
            self.assertIn("Commercial readiness", preview)
            self.assertIn("Commercial Setup Template", preview)
            self.assertIn("Sales plan / 販売ナビ", preview)
            self.assertIn("Sales materials / 販売素材", preview)
            self.assertIn("Sales finalize / 販売準備一括", preview)
            self.assertIn("Seller send checklist", preview)
            self.assertIn("No sales evidence manifests found", preview)
            self.assertIn("Maintenance summary", preview)
            self.assertNotIn(str(project), preview)
            self.assertNotIn(article_path.name, preview)

    def test_quickstart_reports_first_publish_path_and_helper_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            article = create_article("クイック確認記事", articles_dir=project / "articles", tags=["note"])
            body = article.read_text(encoding="utf-8")
            article.write_text(body + "\n本文を少し追記します。\n", encoding="utf-8")

            run_setup_check(project, create=True)
            report = run_quickstart(project, smoke_helper=True)
            text = format_quickstart_report(report)
            public_text = format_quickstart_report(report, include_private=False)
            helper_path = report.helper_path
            helper_exists = bool(helper_path and helper_path.exists())

        self.assertFalse(any(item.status == "fail" for item in report.items))
        self.assertFalse(has_quickstart_blockers(report))
        self.assertIsNotNone(helper_path)
        self.assertTrue(helper_exists)
        self.assertIn("Quickstart report", text)
        self.assertIn("posting helper", text)
        self.assertIn("Generated helper", text)
        self.assertIn(article.name, text)
        self.assertNotIn(article.name, public_text)
        self.assertIn("article-001.md", public_text)
        self.assertNotIn(str(helper_path), public_text)

    def test_first_run_checklist_guides_initial_setup_and_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            run_setup_check(project, create=True)

            report = run_first_run_checklist(project)
            text = format_first_run_report(report)
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["first-run", "--project-dir", str(project)])
            strict_output = io.StringIO()
            with redirect_stdout(strict_output):
                strict_code = cli_main(["first-run", "--project-dir", str(project), "--strict"])

        item_names = [item.name for item in report.items]
        self.assertEqual(code, 0)
        self.assertEqual(strict_code, 1)
        self.assertTrue(report.ok)
        self.assertTrue(report.has_warnings)
        self.assertTrue(has_first_run_blockers(report, strict=True))
        self.assertIn("First-run checklist", text)
        self.assertIn("セルフテスト保存", item_names)
        self.assertIn("最初の記事", item_names)
        self.assertIn("投稿ヘルパー", item_names)
        self.assertIn("問い合わせ一式", item_names)
        self.assertIn("auto-note self-test --project-dir . --report", text)
        self.assertNotIn(str(project), text)
        self.assertIn("First-run checklist", cli_output.getvalue())

    def test_buyer_onboarding_keeps_content_polish_as_info(self) -> None:
        quickstart = QuickstartReport(
            project_dir=Path("project"),
            score=87,
            items=[
                QuickstartItem("setup", "pass", "ready"),
                QuickstartItem("first article", "pass", "1 article(s)"),
                QuickstartItem("article check", "warn", "1 warning(s)"),
                QuickstartItem("article review", "warn", "average 72/100"),
                QuickstartItem("posting helper", "pass", "ready"),
            ],
        )
        content_action_plan = ActionPlanReport(
            project_dir=Path("project"),
            readiness_score=90,
            quickstart_score=87,
            status="NEEDS ATTENTION",
            steps=[
                ActionPlanStep(
                    title="公開前チェックを直す",
                    reason="1 warning(s)",
                    action="投稿前の本文/タグ/状態を整えてください。",
                    severity="warning",
                    source="quickstart",
                )
            ],
        )
        commercial_action_plan = ActionPlanReport(
            project_dir=Path("project"),
            readiness_score=90,
            quickstart_score=100,
            status="NEEDS ATTENTION",
            steps=[
                ActionPlanStep(
                    title="販売者情報を埋める",
                    reason="未入力があります。",
                    action="販売者情報を埋めてください。",
                    severity="warning",
                    source="commercial_setup",
                )
            ],
        )

        self_item = _self_test_quickstart_item(quickstart)
        content_top_action = _top_action_item(content_action_plan)
        commercial_top_action = _top_action_item(commercial_action_plan)

        self.assertEqual(self_item.status, "info")
        self.assertEqual(content_top_action.status, "info")
        self.assertEqual(commercial_top_action.status, "info")

    def test_acceptance_check_summarizes_buyer_handoff_and_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            run_setup_check(project, create=True)
            create_practice_article(articles_dir=project / "articles")

            report = run_acceptance_check(project, smoke_helper=True)
            text = format_acceptance_report(report)
            saved = write_acceptance_report(project, report=report)
            saved_exists = saved.exists()
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["acceptance", "--project-dir", str(project), "--smoke-helper", "--report"])
            full_cli_output = io.StringIO()
            with redirect_stdout(full_cli_output):
                full_code = cli_main(["acceptance", "--project-dir", str(project), "--full"])
            reports = list_acceptance_reports(project)
            privacy = run_privacy_audit(project)
            privacy_text = format_privacy_audit_report(privacy)

        item_names = [item.name for item in report.items]
        full_output = full_cli_output.getvalue()
        self.assertEqual(code, 0)
        self.assertEqual(full_code, 0)
        self.assertTrue(report.ok)
        self.assertFalse(has_acceptance_blockers(report))
        self.assertIn("Acceptance check / 受入チェック", text)
        self.assertIn("初回チェック", item_names)
        self.assertIn("セルフテスト", item_names)
        self.assertIn("トラブル診断", item_names)
        self.assertIn("投稿ヘルパー", item_names)
        self.assertIn("GUI初期化", item_names)
        self.assertIn("問い合わせ一式", item_names)
        self.assertTrue(saved_exists)
        self.assertGreaterEqual(len(reports), 3)
        self.assertIn("acceptance report created:", cli_output.getvalue())
        self.assertIn("acceptance report created:", full_output)
        self.assertIn("投稿ヘルパー", full_output)
        self.assertIn("GUI初期化", full_output)
        self.assertFalse(has_privacy_audit_blockers(privacy))
        self.assertIn("acceptance report privacy", privacy_text)

    def test_commercial_readiness_summarizes_sale_handoff_and_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "src" / "auto_note").mkdir(parents=True)
            (project / "scripts").mkdir()
            (project / "shortcuts").mkdir()
            (project / "docs").mkdir()
            (project / "src" / "auto_note" / "__init__.py").write_text("", encoding="utf-8")
            (project / "scripts" / "ensure-env.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "scripts" / "install-auto-note.ps1").write_text("Write-Host install\n", encoding="utf-8")
            (project / "scripts" / "uninstall-auto-note.ps1").write_text("Write-Host uninstall\n", encoding="utf-8")
            (project / "scripts" / "smoke-install.ps1").write_text("Write-Host smoke\n", encoding="utf-8")
            (project / "shortcuts" / "install-auto-note.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "shortcuts" / "uninstall-auto-note.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "README.md").write_text("auto-note commercial-readiness\n", encoding="utf-8")
            (project / "pyproject.toml").write_text("[project]\nname='auto-note'\n", encoding="utf-8")
            for name in (
                "INSTALL.md",
                "QUICKSTART.md",
                "SUPPORT.md",
                "PRIVACY.md",
                "THIRD_PARTY_NOTICES.md",
                "CHANGELOG.md",
                "RELEASE_CHECKLIST.md",
            ):
                (project / "docs" / name).write_text(f"{name}\n", encoding="utf-8")
            (project / "docs" / "TERMS_DRAFT.md").write_text("Draft terms\n", encoding="utf-8")
            (project / "docs" / "COMMERCIAL_POLICY_DRAFT.md").write_text("販売前レビュー\n", encoding="utf-8")
            run_setup_check(project, create=True)
            create_practice_article(articles_dir=project / "articles")
            create_release_package(project)
            write_acceptance_report(project, report=run_acceptance_check(project, smoke_helper=True))

            report = run_commercial_readiness(project)
            text = format_commercial_readiness_report(report)
            saved = write_commercial_readiness_report(project, report=report)
            saved_exists = saved.exists()
            policy_review = write_commercial_policy_review(project)
            policy_review_exists = policy_review.exists()
            policy_review_text = policy_review.read_text(encoding="utf-8")
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["commercial-readiness", "--project-dir", str(project), "--report", "--policy-review"])
            strict_output = io.StringIO()
            with redirect_stdout(strict_output):
                strict_code = cli_main(["commercial-readiness", "--project-dir", str(project), "--strict"])
            reports = list_commercial_readiness_reports(project)
            policy_reviews = list_commercial_policy_reviews(project)
            privacy = run_privacy_audit(project)
            privacy_text = format_privacy_audit_report(privacy)
            update_commercial_settings(
                project,
                seller_name="Auto Note Shop",
                sales_channel_url="https://example.com/auto-note",
                refund_policy_url="https://example.com/refund",
                support_contact="https://example.com/support",
                terms_reviewed=True,
                support_scope_confirmed=True,
            )
            configured_report = run_commercial_readiness(project)
            configured_text = format_commercial_readiness_report(configured_report)

        item_names = [item.name for item in report.items]
        configured_statuses = {item.name: item.status for item in configured_report.items}
        self.assertEqual(code, 0)
        self.assertEqual(strict_code, 1)
        self.assertTrue(report.ok)
        self.assertTrue(report.has_warnings)
        self.assertFalse(has_commercial_readiness_blockers(report))
        self.assertTrue(has_commercial_readiness_blockers(report, strict=True))
        self.assertIn("Commercial readiness / 販売準備", text)
        self.assertIn("配布ZIP", item_names)
        self.assertIn("プライバシー監査", item_names)
        self.assertIn("受入チェック", item_names)
        self.assertIn("販売者プロフィール", item_names)
        self.assertIn("販売文書", item_names)
        self.assertIn("利用条件/商用方針", item_names)
        self.assertIn("販売最終確認", item_names)
        self.assertIn("サポート連絡先", item_names)
        self.assertIn("インストール導線", item_names)
        self.assertIn("draft markers", text)
        self.assertIn("support contact", text)
        self.assertIn("missing: seller name", text)
        self.assertEqual(configured_statuses["販売者プロフィール"], "pass")
        self.assertEqual(configured_statuses["利用条件/商用方針"], "pass")
        self.assertEqual(configured_statuses["販売最終確認"], "pass")
        self.assertEqual(configured_statuses["サポート連絡先"], "pass")
        self.assertIn("seller profile is set", configured_text)
        self.assertIn("draft markers acknowledged", configured_text)
        self.assertTrue(saved_exists)
        self.assertGreaterEqual(len(reports), 2)
        self.assertTrue(policy_review_exists)
        self.assertGreaterEqual(len(policy_reviews), 2)
        self.assertIn("Commercial policy review", policy_review_text)
        self.assertIn("返金/キャンセル条件", policy_review_text)
        self.assertIn("ライセンス/利用条件", policy_review_text)
        self.assertIn("commercial readiness report created:", cli_output.getvalue())
        self.assertIn("commercial policy review created:", cli_output.getvalue())
        self.assertFalse(has_privacy_audit_blockers(privacy))
        self.assertIn("commercial readiness report privacy", privacy_text)
        self.assertIn("commercial policy review privacy", privacy_text)

    def test_sales_handoff_packages_release_and_seller_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "src" / "auto_note").mkdir(parents=True)
            (project / "scripts").mkdir()
            (project / "shortcuts").mkdir()
            (project / "docs").mkdir()
            (project / "src" / "auto_note" / "__init__.py").write_text("", encoding="utf-8")
            (project / "scripts" / "ensure-env.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "scripts" / "install-auto-note.ps1").write_text("Write-Host install\n", encoding="utf-8")
            (project / "scripts" / "uninstall-auto-note.ps1").write_text("Write-Host uninstall\n", encoding="utf-8")
            (project / "scripts" / "smoke-install.ps1").write_text("Write-Host smoke\n", encoding="utf-8")
            (project / "shortcuts" / "install-auto-note.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "shortcuts" / "uninstall-auto-note.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "README.md").write_text("auto-note sales-handoff\n", encoding="utf-8")
            (project / "pyproject.toml").write_text("[project]\nname='auto-note'\n", encoding="utf-8")
            for name in (
                "INSTALL.md",
                "QUICKSTART.md",
                "SUPPORT.md",
                "PRIVACY.md",
                "THIRD_PARTY_NOTICES.md",
                "CHANGELOG.md",
                "RELEASE_CHECKLIST.md",
                "TERMS_DRAFT.md",
                "COMMERCIAL_POLICY_DRAFT.md",
            ):
                (project / "docs" / name).write_text(f"{name}\n", encoding="utf-8")
            run_setup_check(project, create=True)
            create_practice_article(articles_dir=project / "articles")
            update_commercial_settings(
                project,
                seller_name="Auto Note Shop",
                sales_channel_url="https://example.com/auto-note",
                refund_policy_url="https://example.com/refund",
                support_contact="https://example.com/support",
                terms_reviewed=True,
                support_scope_confirmed=True,
            )
            create_release_package(project)
            write_acceptance_report(project, report=run_acceptance_check(project, smoke_helper=True))

            result = create_sales_handoff(project)
            broken = project / ".auto-note" / "sales" / "auto-note-sales-handoff-broken.zip"
            broken.write_text("not a zip", encoding="utf-8")
            future_time = (datetime.now() + timedelta(days=1)).timestamp()
            os.utime(broken, (future_time, future_time))
            recreated = create_sales_handoff(project)
            recreated_errors = verify_sales_handoff(recreated.path)
            old_time = (datetime.now() - timedelta(days=1)).timestamp()
            os.utime(broken, (old_time, old_time))
            errors = verify_sales_handoff(result.path)
            verification_text = format_sales_handoff_verification(result.path, errors)
            with zipfile.ZipFile(result.path) as archive:
                names = set(archive.namelist())
                manifest = archive.read("SALES_HANDOFF_MANIFEST.json").decode("utf-8")
                buyer_handoff = archive.read("BUYER_HANDOFF.txt").decode("utf-8")
                buyer_support_guide = archive.read("BUYER_SUPPORT_GUIDE.txt").decode("utf-8")
                delivery_checklist = archive.read("DELIVERY_CHECKLIST.txt").decode("utf-8")
                seller_receipt = archive.read("SELLER_DELIVERY_RECEIPT.txt").decode("utf-8")
                seller_checklist = archive.read("SELLER_FINAL_CHECKLIST.txt").decode("utf-8")
                support_template = archive.read("SUPPORT_RESPONSE_TEMPLATE.txt").decode("utf-8")
                handoff_materials = archive.read("SALES_MATERIALS.md").decode("utf-8")
                commercial_readiness = archive.read("COMMERCIAL_READINESS.txt").decode("utf-8")
            buyer_delivery = extract_buyer_delivery(result.path)
            buyer_delivery_text = format_buyer_delivery_result(buyer_delivery)
            buyer_start = buyer_delivery.buyer_start_path.read_text(encoding="utf-8")
            buyer_delivery_names = {path.name for path in buyer_delivery.directory.iterdir()}
            buyer_delivery_errors = verify_buyer_delivery(buyer_delivery.directory)
            buyer_delivery_verification = format_buyer_delivery_verification(
                buyer_delivery.directory,
                buyer_delivery_errors,
            )
            buyer_package_names: set[str] = set()
            buyer_package_manifest: dict[str, object] = {}
            buyer_package_start = ""
            with zipfile.ZipFile(buyer_delivery.package_path) as archive:
                buyer_package_names = set(archive.namelist())
                buyer_package_manifest = json.loads(archive.read("BUYER_DELIVERY_MANIFEST.json").decode("utf-8"))
                buyer_package_start = archive.read("START_HERE_FOR_BUYER.txt").decode("utf-8")
            buyer_package_errors = verify_buyer_delivery_package(buyer_delivery.package_path)
            buyer_package_verification = format_buyer_delivery_package_verification(
                buyer_delivery.package_path,
                buyer_package_errors,
            )
            manual_buyer_package = package_buyer_delivery(
                buyer_delivery.directory,
                output_path=buyer_delivery.directory.parent / "manual-buyer-delivery.zip",
            )
            manual_buyer_package_errors = verify_buyer_delivery_package(manual_buyer_package)
            (buyer_delivery.directory / "seller-evidence.zip").write_text("wrong file", encoding="utf-8")
            dirty_buyer_delivery_errors = verify_buyer_delivery(buyer_delivery.directory)
            (buyer_delivery.directory / "seller-evidence.zip").unlink()
            buyer_delivery.buyer_handoff_path.write_text("tampered", encoding="utf-8")
            tampered_buyer_delivery_errors = verify_buyer_delivery(buyer_delivery.directory)
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["sales-handoff", "--project-dir", str(project)])
            verify_output = io.StringIO()
            with redirect_stdout(verify_output):
                verify_code = cli_main(["sales-handoff", "--verify", str(result.path)])
            list_output = io.StringIO()
            with redirect_stdout(list_output):
                list_code = cli_main(["sales-handoff", "--project-dir", str(project), "--list"])
            buyer_cli_dir = project / ".auto-note" / "sales" / "buyer-delivery-cli"
            buyer_cli_output = io.StringIO()
            with redirect_stdout(buyer_cli_output):
                buyer_cli_code = cli_main(
                    [
                        "sales-handoff",
                        "--extract-buyer",
                        str(result.path),
                        "--output-dir",
                        str(buyer_cli_dir),
                    ]
                )
            buyer_cli_names = {path.name for path in buyer_cli_dir.iterdir()}
            buyer_cli_package_exists = any(
                path.name.startswith("auto-note-buyer-delivery-cli")
                for path in list_buyer_delivery_packages(project)
            )
            buyer_verify_output = io.StringIO()
            with redirect_stdout(buyer_verify_output):
                buyer_verify_code = cli_main(["sales-handoff", "--verify-buyer", str(buyer_cli_dir)])
            buyer_package_cli_path = buyer_cli_dir.parent / "buyer-cli-upload.zip"
            buyer_package_output = io.StringIO()
            with redirect_stdout(buyer_package_output):
                buyer_package_code = cli_main(
                    [
                        "sales-handoff",
                        "--package-buyer",
                        str(buyer_cli_dir),
                        "--output-package",
                        str(buyer_package_cli_path),
                    ]
                )
            buyer_package_cli_exists = buyer_package_cli_path.exists()
            buyer_verify_package_output = io.StringIO()
            with redirect_stdout(buyer_verify_package_output):
                buyer_verify_package_code = cli_main(
                    ["sales-handoff", "--verify-buyer-package", str(buyer_package_cli_path)]
                )
            buyer_list_output = io.StringIO()
            with redirect_stdout(buyer_list_output):
                buyer_list_code = cli_main(["sales-handoff", "--project-dir", str(project), "--list-buyer"])
            buyer_package_list_output = io.StringIO()
            with redirect_stdout(buyer_package_list_output):
                buyer_package_list_code = cli_main(["sales-handoff", "--project-dir", str(project), "--list-buyer-package"])
            materials_result = create_sales_materials(project)
            materials_text = materials_result.path.read_text(encoding="utf-8")
            materials_errors = verify_sales_materials(materials_result.path, strict=True, project_dir=project)
            materials_verification_text = format_sales_materials_verification(
                materials_result.path,
                materials_errors,
                strict=True,
            )
            materials_output = io.StringIO()
            with redirect_stdout(materials_output):
                materials_code = cli_main(["sales-materials", "--project-dir", str(project)])
            materials_verify_output = io.StringIO()
            with redirect_stdout(materials_verify_output):
                materials_verify_code = cli_main(
                    [
                        "sales-materials",
                        "--project-dir",
                        str(project),
                        "--verify",
                        str(materials_result.path),
                        "--strict",
                    ]
                )
            materials_list_output = io.StringIO()
            with redirect_stdout(materials_list_output):
                materials_list_code = cli_main(["sales-materials", "--project-dir", str(project), "--list"])
            sales_plan_output = io.StringIO()
            with redirect_stdout(sales_plan_output):
                sales_plan_code = cli_main(["sales-plan", "--project-dir", str(project)])
            sales_plan_report_output = io.StringIO()
            with redirect_stdout(sales_plan_report_output):
                sales_plan_report_code = cli_main(["sales-plan", "--project-dir", str(project), "--report"])
            handoffs = list_sales_handoffs(project)
            buyer_deliveries = list_buyer_deliveries(project)
            buyer_packages = list_buyer_delivery_packages(project)
            materials = list_sales_materials(project)
            sales_plan = build_sales_plan(project)
            sales_plan_text = format_sales_plan(sales_plan)
            sales_plan_report_path = write_sales_plan_report(project, report=sales_plan)
            sales_plan_reports = list_sales_plan_reports(project)
            sales_plan_report_exists = sales_plan_report_path.exists()
            sales_plan_report_name = sales_plan_report_path.name
            sales_plan_report_text = sales_plan_report_path.read_text(encoding="utf-8")
            sales_plan_report_count = len(sales_plan_reports)
            privacy = run_privacy_audit(project)
            privacy_text = format_privacy_audit_report(privacy)

        self.assertEqual(errors, [])
        self.assertEqual(recreated_errors, [])
        self.assertIn("[OK] sales handoff verified", verification_text)
        self.assertIn("README.txt", names)
        self.assertIn("BUYER_HANDOFF.txt", names)
        self.assertIn("BUYER_SUPPORT_GUIDE.txt", names)
        self.assertIn("DELIVERY_CHECKLIST.txt", names)
        self.assertIn("SELLER_DELIVERY_RECEIPT.txt", names)
        self.assertIn("SELLER_FINAL_CHECKLIST.txt", names)
        self.assertIn("SUPPORT_RESPONSE_TEMPLATE.txt", names)
        self.assertIn("SALES_MATERIALS.md", names)
        self.assertIn("COMMERCIAL_READINESS.txt", names)
        self.assertTrue(any(name.startswith("release/auto-note-release-") for name in names))
        self.assertIn('"includes_user_articles": false', manifest)
        self.assertIn("DELIVERY_CHECKLIST.txt", manifest)
        self.assertIn("SELLER_DELIVERY_RECEIPT.txt", manifest)
        self.assertIn("SALES_MATERIALS.md", manifest)
        self.assertIn("Attached release package", buyer_handoff)
        self.assertIn("Buyer first 10 minutes", buyer_handoff)
        self.assertIn("購入者の最初の10分", buyer_handoff)
        self.assertIn("auto-note buyer support guide", buyer_support_guide)
        self.assertIn("auto-note support --project-dir . --bundle", buyer_support_guide)
        self.assertIn("auto-note buyer start here", buyer_start)
        self.assertIn(result.release_path.name, buyer_start)
        self.assertIn("START_HERE.txt", buyer_start)
        self.assertIn("shortcuts\\install-auto-note.bat", buyer_start)
        self.assertIn("BUYER_SUPPORT_GUIDE.txt", buyer_start)
        self.assertIn("auto-note buyer start here", buyer_package_start)
        self.assertIn("Buyer delivery", delivery_checklist)
        self.assertIn("購入者に送るもの", delivery_checklist)
        self.assertIn("START_HERE_FOR_BUYER.txt", delivery_checklist)
        self.assertIn("Seller evidence", delivery_checklist)
        self.assertIn("SELLER_DELIVERY_RECEIPT.txt", delivery_checklist)
        self.assertIn("通常は送らないもの", delivery_checklist)
        self.assertIn("auto-note seller delivery receipt", seller_receipt)
        self.assertIn(result.release_path.name, seller_receipt)
        self.assertIn("Buyer delivery ZIP", seller_receipt)
        self.assertIn("Order ID", seller_receipt)
        self.assertIn("SHA-256", seller_receipt)
        self.assertEqual(
            buyer_delivery_names,
            {
                result.release_path.name,
                "START_HERE_FOR_BUYER.txt",
                "BUYER_HANDOFF.txt",
                "BUYER_SUPPORT_GUIDE.txt",
                "BUYER_DELIVERY_MANIFEST.json",
                "SHA256SUMS.txt",
            },
        )
        self.assertEqual(buyer_delivery_errors, [])
        self.assertIn("[OK] buyer delivery verified", buyer_delivery_verification)
        self.assertIn("BUYER_DELIVERY_MANIFEST.json", buyer_delivery_verification)
        self.assertIn("SHA256SUMS.txt", buyer_delivery_verification)
        self.assertIn("Tell the buyer to open START_HERE_FOR_BUYER.txt first.", buyer_delivery_verification)
        self.assertEqual(
            buyer_package_names,
            {
                result.release_path.name,
                "START_HERE_FOR_BUYER.txt",
                "BUYER_HANDOFF.txt",
                "BUYER_SUPPORT_GUIDE.txt",
                "BUYER_DELIVERY_MANIFEST.json",
                "SHA256SUMS.txt",
            },
        )
        self.assertEqual(buyer_package_manifest["name"], "auto-note buyer delivery")
        self.assertEqual(buyer_package_manifest["release_package"], result.release_path.name)
        self.assertIn(
            "START_HERE_FOR_BUYER.txt",
            {str(item["path"]) for item in buyer_package_manifest["files"] if isinstance(item, dict)},
        )
        self.assertEqual(buyer_package_errors, [])
        self.assertEqual(manual_buyer_package_errors, [])
        self.assertTrue(buyer_delivery.package_path.name.startswith("auto-note-buyer-delivery-"))
        self.assertIn("[OK] buyer delivery zip verified", buyer_package_verification)
        self.assertIn("Package bytes:", buyer_package_verification)
        self.assertIn("Package SHA-256:", buyer_package_verification)
        self.assertIn("Tell the buyer to open START_HERE_FOR_BUYER.txt first.", buyer_package_verification)
        self.assertIn("buyer delivery zip", buyer_delivery_text)
        self.assertIn("buyer start guide", buyer_delivery_text)
        self.assertIn("buyer support guide", buyer_delivery_text)
        self.assertTrue(any("unexpected file" in error for error in dirty_buyer_delivery_errors))
        self.assertTrue(any("buyer checksum mismatch: BUYER_HANDOFF.txt" in error for error in tampered_buyer_delivery_errors))
        self.assertIn("release package to send", buyer_delivery_text)
        self.assertIn("manifest file", buyer_delivery_text)
        self.assertIn("checksum file", buyer_delivery_text)
        self.assertEqual(
            buyer_cli_names,
            {
                result.release_path.name,
                "START_HERE_FOR_BUYER.txt",
                "BUYER_HANDOFF.txt",
                "BUYER_SUPPORT_GUIDE.txt",
                "BUYER_DELIVERY_MANIFEST.json",
                "SHA256SUMS.txt",
            },
        )
        self.assertTrue(buyer_cli_package_exists)
        self.assertTrue(buyer_package_cli_exists)
        self.assertIn("Remaining seller actions", seller_checklist)
        self.assertIn("support bundle", support_template)
        self.assertIn("Feature Bullets", handoff_materials)
        self.assertIn("Buyer First 10 Minutes", handoff_materials)
        self.assertIn("Commercial readiness", commercial_readiness)
        self.assertEqual(code, 0)
        self.assertEqual(verify_code, 0)
        self.assertEqual(list_code, 0)
        self.assertEqual(buyer_cli_code, 0)
        self.assertEqual(buyer_verify_code, 0)
        self.assertEqual(buyer_package_code, 0)
        self.assertEqual(buyer_verify_package_code, 0)
        self.assertEqual(buyer_list_code, 0)
        self.assertEqual(buyer_package_list_code, 0)
        self.assertEqual(materials_code, 0)
        self.assertEqual(materials_verify_code, 0)
        self.assertEqual(materials_list_code, 0)
        self.assertEqual(sales_plan_code, 0)
        self.assertEqual(sales_plan_report_code, 0)
        self.assertIn("sales handoff created:", cli_output.getvalue())
        self.assertIn("[OK] sales handoff verified", verify_output.getvalue())
        self.assertIn("buyer delivery extracted:", buyer_cli_output.getvalue())
        self.assertIn("[OK] buyer delivery verified", buyer_verify_output.getvalue())
        self.assertIn("[OK] buyer delivery zip verified", buyer_package_output.getvalue())
        self.assertIn("[OK] buyer delivery zip verified", buyer_verify_package_output.getvalue())
        self.assertIn("buyer-delivery-", buyer_list_output.getvalue())
        self.assertIn("auto-note-buyer-delivery-", buyer_package_list_output.getvalue())
        self.assertEqual(materials_errors, [])
        self.assertIn("[OK] sales materials verified", materials_verification_text)
        self.assertIn("[OK] sales materials verified", materials_verify_output.getvalue())
        self.assertGreaterEqual(len(handoffs), 2)
        self.assertGreaterEqual(len(buyer_deliveries), 2)
        self.assertGreaterEqual(len(buyer_packages), 2)
        self.assertGreaterEqual(len(materials), 2)
        self.assertIn("auto-note-sales-handoff-", list_output.getvalue())
        self.assertIn("sales materials created:", materials_output.getvalue())
        self.assertIn("auto-note-sales-materials-", materials_list_output.getvalue())
        self.assertIn("Feature Bullets", materials_text)
        self.assertIn("Buyer First 10 Minutes", materials_text)
        self.assertIn("購入者の最初の10分", materials_text)
        self.assertIn("Delivery Message", materials_text)
        self.assertIn("Support Scope", materials_text)
        self.assertIn("Sales plan / 販売ナビ", sales_plan_text)
        self.assertEqual(sales_plan.buyer_delivery_status, "READY")
        self.assertIn("Buyer delivery readiness: READY", sales_plan_text)
        self.assertIn("Seller setup remaining: 0", sales_plan_text)
        self.assertIn("Tool/artifact actions remaining:", sales_plan_text)
        self.assertIn("Upload guidance:", sales_plan_text)
        self.assertIn("SHA-256", sales_plan_text)
        self.assertIn("Latest sales handoff", sales_plan_text)
        self.assertIn("Latest buyer delivery zip", sales_plan_text)
        self.assertIn("auto-note-buyer-delivery-", sales_plan_text)
        self.assertIn("Latest sales materials", sales_plan_text)
        self.assertIn("Sales plan / 販売ナビ", sales_plan_output.getvalue())
        self.assertIn("Buyer delivery readiness: READY", sales_plan_output.getvalue())
        self.assertIn("Seller setup remaining: 0", sales_plan_output.getvalue())
        self.assertIn("Tool/artifact actions remaining:", sales_plan_output.getvalue())
        self.assertIn("Upload guidance:", sales_plan_output.getvalue())
        self.assertIn("Latest buyer delivery zip", sales_plan_output.getvalue())
        self.assertTrue(sales_plan_report_exists)
        self.assertTrue(sales_plan_report_name.startswith("sales-plan-"))
        self.assertGreaterEqual(sales_plan_report_count, 2)
        self.assertIn("sales plan report created:", sales_plan_report_output.getvalue())
        self.assertIn("Sales plan / 販売ナビ", sales_plan_report_text)
        self.assertNotIn(str(project), sales_plan_report_text)
        self.assertFalse(has_sales_plan_blockers(sales_plan))
        self.assertFalse(has_privacy_audit_blockers(privacy))
        self.assertIn("sales plan report privacy", privacy_text)
        self.assertIn("sales materials privacy", privacy_text)
        self.assertIn("sales handoff privacy", privacy_text)
        self.assertIn("buyer delivery zip privacy", privacy_text)

    def test_sales_finalize_saves_blocked_report_and_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            run_setup_check(project, create=True)

            report = create_sales_finalize(project)
            text = format_sales_finalize_report(report)
            report_saved = bool(report.report_path and report.report_path.exists())
            reports = list_sales_finalize_reports(project)
            privacy = run_privacy_audit(project)
            privacy_text = format_privacy_audit_report(privacy)
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["sales-finalize", "--project-dir", str(project)])

        self.assertTrue(has_sales_finalize_blockers(report))
        self.assertIsNotNone(report.commercial_template_path)
        self.assertIsNotNone(report.report_path)
        self.assertTrue(report_saved)
        self.assertIsNone(report.sales_handoff_path)
        self.assertIsNone(report.buyer_delivery_dir)
        self.assertGreaterEqual(len(reports), 1)
        self.assertIn("Sales finalize / 販売準備一括", text)
        self.assertIn("support contact / サポート連絡先", text)
        self.assertIn("[NG] release preflight", text)
        self.assertIn("sales finalize report privacy", privacy_text)
        self.assertEqual(code, 1)
        self.assertIn("Sales finalize / 販売準備一括", cli_output.getvalue())

    def test_sales_finalize_can_apply_latest_commercial_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            run_setup_check(project, create=True)
            sales_dir = project / ".auto-note" / "sales"
            sales_dir.mkdir(parents=True)
            template = sales_dir / "commercial-setup-template-20260607-000000.md"
            template.write_text(
                "\n".join(
                    [
                        "# seller setup",
                        "- seller_name: Demo Shop",
                        "- sales_url: https://example.com/sales",
                        "- refund_url: https://example.com/refund",
                        "- support_contact: https://example.com/support",
                        "- terms_reviewed: yes",
                        "- support_scope_confirmed: yes",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            report = create_sales_finalize(project, apply_latest_template=True, save_report=False)
            text = format_sales_finalize_report(report)
            settings = load_settings(project)
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["sales-finalize", "--project-dir", str(project), "--apply-latest-template", "--no-report"])

        self.assertEqual(settings.seller_name, "Demo Shop")
        self.assertEqual(settings.sales_channel_url, "https://example.com/sales")
        self.assertEqual(settings.refund_policy_url, "https://example.com/refund")
        self.assertEqual(settings.support_contact, "https://example.com/support")
        self.assertTrue(settings.commercial_terms_reviewed)
        self.assertTrue(settings.commercial_support_scope_confirmed)
        self.assertIn("[OK] commercial setup template apply", text)
        self.assertIn("updated seller_name", text)
        self.assertEqual(code, 1)
        self.assertIn("commercial setup template apply", cli_output.getvalue())

    def test_sales_finalize_creates_and_verifies_buyer_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "src" / "auto_note").mkdir(parents=True)
            (project / "scripts").mkdir()
            (project / "shortcuts").mkdir()
            (project / "docs").mkdir()
            (project / "src" / "auto_note" / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")
            (project / "scripts" / "ensure-env.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "scripts" / "install-auto-note.ps1").write_text("Write-Host install\n", encoding="utf-8")
            (project / "scripts" / "uninstall-auto-note.ps1").write_text("Write-Host uninstall\n", encoding="utf-8")
            (project / "scripts" / "smoke-install.ps1").write_text("Write-Host smoke\n", encoding="utf-8")
            (project / "shortcuts" / "install-auto-note.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "shortcuts" / "uninstall-auto-note.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "README.md").write_text("auto-note sales-finalize\n", encoding="utf-8")
            (project / "pyproject.toml").write_text("[project]\nname='auto-note'\n", encoding="utf-8")
            for name in (
                "INSTALL.md",
                "QUICKSTART.md",
                "SUPPORT.md",
                "PRIVACY.md",
                "THIRD_PARTY_NOTICES.md",
                "CHANGELOG.md",
                "RELEASE_CHECKLIST.md",
                "TERMS_DRAFT.md",
                "COMMERCIAL_POLICY_DRAFT.md",
            ):
                (project / "docs" / name).write_text(f"{name}\n", encoding="utf-8")
            run_setup_check(project, create=True)
            create_practice_article(articles_dir=project / "articles")
            update_commercial_settings(
                project,
                seller_name="Auto Note Shop",
                sales_channel_url="https://example.com/auto-note",
                refund_policy_url="https://example.com/refund",
                support_contact="https://example.com/support",
                terms_reviewed=True,
                support_scope_confirmed=True,
            )
            release_path = create_release_package(project)
            write_acceptance_report(project, report=run_acceptance_check(project, smoke_helper=True))
            preflight = PreflightReport(
                project_dir=project,
                status="pass",
                readiness_score=100,
                items=[PreflightItem("readiness", "pass", "100/100")],
                created_release=release_path,
            )

            with patch("auto_note.sales_finalize.run_preflight", return_value=preflight):
                report = create_sales_finalize(project, save_report=False)
                text = format_sales_finalize_report(report)
                details = format_sales_finalize_details(report)
            delivery_names = {path.name for path in report.buyer_delivery_dir.iterdir()} if report.buyer_delivery_dir else set()
            buyer_delivery_errors = (
                verify_buyer_delivery(report.buyer_delivery_dir) if report.buyer_delivery_dir else ["missing buyer delivery"]
            )
            buyer_package_errors = (
                verify_buyer_delivery_package(report.buyer_delivery_package_path)
                if report.buyer_delivery_package_path
                else ["missing buyer delivery zip"]
            )
            privacy = run_privacy_audit(project)
            privacy_text = format_privacy_audit_report(privacy)
            buyer_delivery_message_text = (
                report.buyer_delivery_message_path.read_text(encoding="utf-8")
                if report.buyer_delivery_message_path
                else ""
            )
            buyer_delivery_message_exists = bool(
                report.buyer_delivery_message_path and report.buyer_delivery_message_path.exists()
            )
            seller_send_checklist_text = (
                report.seller_send_checklist_path.read_text(encoding="utf-8")
                if report.seller_send_checklist_path
                else ""
            )
            seller_send_checklist_exists = bool(
                report.seller_send_checklist_path and report.seller_send_checklist_path.exists()
            )
            sales_plan_report_text = (
                report.sales_plan_report_path.read_text(encoding="utf-8")
                if report.sales_plan_report_path
                else ""
            )
            sales_plan_report_exists = bool(report.sales_plan_report_path and report.sales_plan_report_path.exists())
            sales_evidence_manifest_text = (
                report.sales_evidence_manifest_path.read_text(encoding="utf-8")
                if report.sales_evidence_manifest_path
                else ""
            )
            sales_evidence_manifest = json.loads(sales_evidence_manifest_text) if sales_evidence_manifest_text else {}
            sales_evidence_manifest_exists = bool(
                report.sales_evidence_manifest_path and report.sales_evidence_manifest_path.exists()
            )
            sales_evidence_manifest_count = len(list_sales_evidence_manifests(project))
            buyer_delivery_messages = list_buyer_delivery_messages(project)
            buyer_delivery_message_names = [path.name for path in buyer_delivery_messages]
            buyer_send_readiness = run_buyer_send_readiness(project)
            buyer_send_readiness_text = format_buyer_send_readiness_report(buyer_send_readiness)
            buyer_send_cli_output = io.StringIO()
            with redirect_stdout(buyer_send_cli_output):
                buyer_send_cli_code = cli_main(
                    [
                        "sales-finalize",
                        "--project-dir",
                        str(project),
                        "--send-check",
                        "--send-check-report",
                        "--delivery-receipt",
                    ]
                )
            buyer_send_reports = list_buyer_send_readiness_reports(project)
            buyer_send_report_text = buyer_send_reports[0].read_text(encoding="utf-8") if buyer_send_reports else ""
            seller_delivery_receipts = list_seller_delivery_receipts(project)
            seller_delivery_receipt_text = (
                seller_delivery_receipts[0].read_text(encoding="utf-8") if seller_delivery_receipts else ""
            )
            acceptance_report_exists = bool(report.acceptance_report_path and report.acceptance_report_path.exists())

        self.assertFalse(has_sales_finalize_blockers(report))
        self.assertIsNotNone(report.sales_handoff_path)
        self.assertIsNotNone(report.buyer_delivery_dir)
        self.assertIsNotNone(report.buyer_delivery_package_path)
        self.assertIsNotNone(report.buyer_delivery_message_path)
        self.assertTrue(buyer_delivery_message_exists)
        self.assertGreaterEqual(len(buyer_delivery_messages), 1)
        self.assertEqual(buyer_delivery_messages[0], report.buyer_delivery_message_path)
        self.assertIn(report.buyer_delivery_message_path.name, buyer_delivery_message_names)
        self.assertFalse(has_buyer_send_readiness_blockers(buyer_send_readiness))
        self.assertEqual(buyer_send_readiness.status, "pass")
        self.assertEqual(buyer_send_readiness.buyer_delivery_package_path, report.buyer_delivery_package_path)
        self.assertEqual(buyer_send_readiness.buyer_delivery_message_path, report.buyer_delivery_message_path)
        self.assertEqual(buyer_send_readiness.sales_evidence_manifest_path, report.sales_evidence_manifest_path)
        self.assertIn("Buyer send readiness", buyer_send_readiness_text)
        self.assertIn("Verdict: READY", buyer_send_readiness_text)
        self.assertIn("buyer delivery zip", buyer_send_readiness_text)
        self.assertIn("sales evidence manifest", buyer_send_readiness_text)
        self.assertIn("送付文コピー", buyer_send_readiness_text)
        self.assertEqual(buyer_send_cli_code, 0)
        self.assertGreaterEqual(len(buyer_send_reports), 1)
        self.assertIn("Buyer send readiness", buyer_send_cli_output.getvalue())
        self.assertIn("buyer send readiness report created:", buyer_send_cli_output.getvalue())
        self.assertIn("seller delivery receipt created:", buyer_send_cli_output.getvalue())
        self.assertIn(str(buyer_send_reports[0]), buyer_send_cli_output.getvalue())
        self.assertGreaterEqual(len(seller_delivery_receipts), 1)
        self.assertIn(str(seller_delivery_receipts[0]), buyer_send_cli_output.getvalue())
        self.assertNotIn("(not created)", buyer_send_cli_output.getvalue())
        self.assertIn("Verdict: READY", buyer_send_report_text)
        self.assertIn("buyer send readiness report:", buyer_send_report_text)
        self.assertIn("auto-note seller delivery receipt", seller_delivery_receipt_text)
        self.assertIn("Order ID", seller_delivery_receipt_text)
        self.assertIn("Buyer delivery ZIP:", seller_delivery_receipt_text)
        self.assertIn(report.buyer_delivery_package_path.name, seller_delivery_receipt_text)
        self.assertIn("SHA-256", seller_delivery_receipt_text)
        self.assertIsNotNone(report.seller_send_checklist_path)
        self.assertTrue(seller_send_checklist_exists)
        self.assertIsNotNone(report.sales_plan_report_path)
        self.assertTrue(sales_plan_report_exists)
        self.assertIsNotNone(report.sales_evidence_manifest_path)
        self.assertTrue(sales_evidence_manifest_exists)
        self.assertGreaterEqual(sales_evidence_manifest_count, 1)
        self.assertIsNotNone(report.acceptance_report_path)
        self.assertTrue(acceptance_report_exists)
        self.assertEqual(buyer_delivery_errors, [])
        self.assertEqual(buyer_package_errors, [])
        self.assertEqual(
            delivery_names,
            {
                release_path.name,
                "START_HERE_FOR_BUYER.txt",
                "BUYER_HANDOFF.txt",
                "BUYER_SUPPORT_GUIDE.txt",
                "BUYER_DELIVERY_MANIFEST.json",
                "SHA256SUMS.txt",
            },
        )
        self.assertIn("[OK] buyer delivery", text)
        self.assertIn("[OK] buyer delivery zip", text)
        self.assertIn("buyer delivery:", text)
        self.assertIn("buyer delivery zip:", text)
        self.assertIn("buyer delivery message:", text)
        self.assertIn("sales plan report:", text)
        self.assertIn("seller send checklist:", text)
        self.assertIn("sales evidence manifest:", text)
        self.assertIn("acceptance report:", text)
        self.assertIn("buyer acceptance", text)
        self.assertIn("[OK] sales plan report", text)
        self.assertIn("[OK] sales evidence manifest", text)
        self.assertIn("Buyer delivery contents", text)
        self.assertIn("Delivery verification", text)
        self.assertIn("SHA-256", text)
        self.assertIn("START_HERE_FOR_BUYER.txt", text)
        self.assertIn("BUYER_DELIVERY_MANIFEST.json", text)
        self.assertIn("購入者には", text)
        self.assertIn("delivery message:", text)
        self.assertIn("auto-note-buyer-delivery-", text)
        self.assertIn("auto-note buyer delivery message", buyer_delivery_message_text)
        self.assertIn("貼り付け用文", buyer_delivery_message_text)
        self.assertIn("START_HERE_FOR_BUYER.txt", buyer_delivery_message_text)
        self.assertIn("BUYER_SUPPORT_GUIDE.txt", buyer_delivery_message_text)
        self.assertIn("SHA-256", buyer_delivery_message_text)
        self.assertIn("パスワード", buyer_delivery_message_text)
        self.assertIn("auto-note seller send checklist", seller_send_checklist_text)
        self.assertIn("Attach exactly this ZIP", seller_send_checklist_text)
        self.assertIn("Sales plan evidence", seller_send_checklist_text)
        self.assertIn("Sales evidence manifest", seller_send_checklist_text)
        self.assertIn("Do not attach auto-note-sales-handoff-*.zip", seller_send_checklist_text)
        self.assertIn("Remaining seller actions", seller_send_checklist_text)
        self.assertIn("Sales plan / 販売ナビ", sales_plan_report_text)
        self.assertIn("Buyer delivery readiness", sales_plan_report_text)
        self.assertNotIn(str(project), sales_plan_report_text)
        self.assertEqual(sales_evidence_manifest["schema"], "auto-note.sales-evidence-manifest.v1")
        self.assertEqual(
            sales_evidence_manifest["artifacts"]["buyer_delivery_zip"]["file_name"],
            report.buyer_delivery_package_path.name,
        )
        self.assertEqual(
            sales_evidence_manifest["artifacts"]["sales_plan_report"]["file_name"],
            report.sales_plan_report_path.name,
        )
        self.assertIn("sha256", sales_evidence_manifest["artifacts"]["buyer_delivery_zip"])
        self.assertIn("BUYER_DELIVERY_MANIFEST.json", sales_evidence_manifest["buyer_delivery_contents"])
        self.assertIn("buyer delivery zip", {item["name"] for item in sales_evidence_manifest["checks"]})
        self.assertIn("sales plan report", {item["name"] for item in sales_evidence_manifest["checks"]})
        self.assertNotIn(str(project), sales_evidence_manifest_text)
        self.assertFalse(has_privacy_audit_blockers(privacy))
        self.assertIn("sales plan report privacy", privacy_text)
        self.assertIn("sales evidence manifest privacy", privacy_text)
        self.assertIn("seller send checklist privacy", privacy_text)
        self.assertIn("buyer delivery message privacy", privacy_text)
        self.assertIn("buyer send readiness report privacy", privacy_text)
        self.assertIn("seller delivery receipt privacy", privacy_text)
        self.assertIn("[OK] buyer delivery verified", details)
        self.assertIn("[OK] buyer delivery zip verified", details)
        self.assertIn("auto-note buyer delivery message", details)
        self.assertIn("Sales plan / 販売ナビ", details)
        self.assertIn("auto-note seller send checklist", details)
        self.assertIn("auto-note.sales-evidence-manifest.v1", details)
        self.assertIn("Acceptance check / 受入チェック", details)

    def test_sales_finalize_skips_unfilled_latest_commercial_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            run_setup_check(project, create=True)
            update_commercial_settings(
                project,
                seller_name="Kept Shop",
                sales_channel_url="https://example.com/sales",
                refund_policy_url="https://example.com/refund",
                support_contact="https://example.com/support",
                terms_reviewed=True,
                support_scope_confirmed=True,
            )
            sales_dir = project / ".auto-note" / "sales"
            sales_dir.mkdir(parents=True)
            template = sales_dir / "commercial-setup-template-20260607-000000.md"
            template.write_text(
                "\n".join(
                    [
                        "# empty seller setup",
                        "- seller_name: [販売者/屋号]",
                        "- sales_url: [販売ページURL]",
                        "- refund_url: [返金方針URL]",
                        "- support_contact: [サポート連絡先]",
                        "- terms_reviewed: no",
                        "- support_scope_confirmed: no",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            report = create_sales_finalize(project, apply_latest_template=True, save_report=False)
            text = format_sales_finalize_report(report)
            settings = load_settings(project)

        self.assertEqual(settings.seller_name, "Kept Shop")
        self.assertTrue(settings.commercial_terms_reviewed)
        self.assertTrue(settings.commercial_support_scope_confirmed)
        self.assertIn("no filled seller values; skipped", text)

    def test_action_plan_guides_first_run_and_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            run_setup_check(project, create=True)

            report = build_action_plan(project, limit=6)
            text = format_action_plan(report)
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["action-plan", "--project-dir", str(project), "--limit", "6"])

        titles = [step.title for step in report.steps]
        self.assertEqual(code, 0)
        self.assertIn("最初の記事を作る", titles)
        self.assertIn("販売者情報を埋める", titles)
        self.assertIn("Action plan", text)
        self.assertIn("auto-note starter-pack --project-dir .", text)
        self.assertIn("auto-note commercial-setup --project-dir . --template", text)
        self.assertIn("設定 > 次の不足へ", text)
        self.assertIn("最初の記事を作る", cli_output.getvalue())

    def test_action_plan_surfaces_commercial_setup_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            run_setup_check(project, create=True)
            update_commercial_settings(
                project,
                seller_name="Risky Shop",
                sales_channel_url="shop page",
                refund_policy_url="refund page",
                support_contact="help@example.com",
                terms_reviewed=True,
                support_scope_confirmed=True,
            )

            report = build_action_plan(project, limit=8)
            text = format_action_plan(report)

        titles = [step.title for step in report.steps]
        self.assertIn("販売者情報の公開URLを確認する", titles)
        self.assertIn("support contact is a raw email address", text)
        self.assertIn("設定 > 次の不足へ", text)

    def test_action_plan_surfaces_troubleshoot_when_gui_log_has_crash_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            run_setup_check(project, create=True)
            append_gui_error(project, "GUI", "Traceback\nRuntimeError: broken\n")

            report = build_action_plan(project, limit=5)
            text = format_action_plan(report)

        titles = [step.title for step in report.steps]
        self.assertIn("トラブル診断を確認する", titles)
        self.assertIn("auto-note troubleshoot --project-dir .", text)
        self.assertIn("診断 > トラブル診断", text)

    def test_action_plan_surfaces_publish_queue_target_without_leaking_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            run_setup_check(project, create=True)
            article = create_article("仮タイトル", articles_dir=project / "articles", tags=[])
            text = article.read_text(encoding="utf-8")
            article.write_text(text + "\nTODO\n![missing](missing.png)\n", encoding="utf-8")

            report = build_action_plan(project, limit=8)
            rendered = format_action_plan(report)

        queue_steps = [step for step in report.steps if step.source == "publish_queue"]
        self.assertTrue(queue_steps)
        self.assertEqual(queue_steps[0].title, "投稿キューの先頭記事を直す")
        self.assertEqual(queue_steps[0].target_path, str(article))
        self.assertIn("auto-note publish-queue --project-dir .", rendered)
        self.assertNotIn(str(project), rendered)
        self.assertNotIn(article.name, rendered)

    def test_self_test_summarizes_local_health_and_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            run_setup_check(project, create=True)

            report = run_self_test(project)
            text = format_self_test_report(report)
            saved = write_self_test_report(project, report=report)
            saved_exists = saved.exists()
            saved_text = saved.read_text(encoding="utf-8")
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["self-test", "--project-dir", str(project)])
            cli_report_output = io.StringIO()
            with redirect_stdout(cli_report_output):
                report_code = cli_main(["self-test", "--project-dir", str(project), "--report"])
            saved_reports = list((project / ".auto-note" / "reports").glob("self-test-*.txt"))

        item_names = [item.name for item in report.items]
        self.assertEqual(code, 0)
        self.assertEqual(report_code, 0)
        self.assertIn("Self-test report", text)
        self.assertIn("Generated:", text)
        self.assertTrue(saved_exists)
        self.assertIn("Self-test report", saved_text)
        self.assertNotIn(str(project), saved_text)
        self.assertGreaterEqual(len(saved_reports), 2)
        self.assertIn("setup", item_names)
        self.assertIn("quickstart", item_names)
        self.assertIn("action plan", item_names)
        self.assertIn("privacy audit", item_names)
        self.assertIn("Self-test report", cli_output.getvalue())
        self.assertIn("self-test report created:", cli_report_output.getvalue())

    def test_workflow_smoke_runs_temporary_publish_flow_and_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "auto-note.lnk").write_text("shortcut\n", encoding="utf-8")

            report = run_workflow_smoke(project)
            text = format_workflow_smoke_report(report)
            saved = write_workflow_smoke_report(project, report=report)
            saved_text = saved.read_text(encoding="utf-8")
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["workflow-smoke", "--project-dir", str(project), "--report"])
            saved_reports = list((project / ".auto-note" / "reports").glob("workflow-smoke-*.txt"))

        item_names = [item.name for item in report.items]
        self.assertEqual(code, 0)
        self.assertTrue(report.ok)
        self.assertFalse(has_workflow_smoke_blockers(report))
        self.assertIn("Workflow smoke", text)
        self.assertIn("practice article", item_names)
        self.assertIn("article check", item_names)
        self.assertIn("article review", item_names)
        self.assertIn("publish ready", item_names)
        self.assertIn("quickstart", item_names)
        self.assertIn("backup", item_names)
        self.assertIn("action plan", item_names)
        self.assertIn("Workflow smoke", saved_text)
        self.assertNotIn(str(project), saved_text)
        self.assertGreaterEqual(len(saved_reports), 2)
        self.assertIn("workflow smoke report created:", cli_output.getvalue())

    def test_action_plan_surfaces_privacy_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            article = create_article(
                "秘密のアクションプラン記事",
                articles_dir=project / "articles",
                tags=["note"],
                slug="private-action-plan-991",
            )
            support_dir = project / ".auto-note" / "support"
            support_dir.mkdir(parents=True)
            (support_dir / "support-request-leaked.md").write_text(
                f"{project}\n{article.name}\n秘密のアクションプラン記事\n",
                encoding="utf-8",
            )
            run_setup_check(project, create=True)

            report = build_action_plan(project, limit=8)
            text = format_action_plan(report)

        self.assertTrue(any(step.title == "危険生成物を確認する" for step in report.steps))
        self.assertIn("auto-note cleanup --project-dir . --privacy-failed --include-releases", text)

    def test_restore_backup_restores_articles_and_creates_safety_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article = create_article("復元記事", articles_dir=project / "articles", tags=["note"])
            original = article.read_text(encoding="utf-8")
            backup = create_backup(project)
            article.write_text("changed", encoding="utf-8")
            extra = project / "articles" / "extra.md"
            extra.write_text("extra", encoding="utf-8")

            result = restore_backup(project, backup)

            self.assertEqual(article.read_text(encoding="utf-8"), original)
            self.assertFalse(extra.exists())
            self.assertTrue(result.safety_backup and result.safety_backup.exists())
            self.assertIn(f"articles/{article.name}", result.restored_files)

    def test_restore_backup_rejects_unsafe_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            backup = project / "unsafe.zip"
            with zipfile.ZipFile(backup, "w") as archive:
                archive.writestr("articles/good.md", "ok")
                archive.writestr("../evil.md", "bad")
            backups_dir = project / ".auto-note" / "backups"
            backups_dir.mkdir(parents=True)
            tracked_backup = backups_dir / "auto-note-backup-unsafe.zip"
            shutil.copy2(backup, tracked_backup)

            inspection = inspect_backup(backup)
            backup_errors = verify_backup(backup)
            readiness = run_readiness(project)

            self.assertFalse(inspection.ok)
            self.assertIn("../evil.md", inspection.unsafe_files)
            self.assertIn("1 unsafe file(s)", backup_errors)
            self.assertTrue(any(item.name == "latest backup" and item.status == "fail" for item in readiness.items))
            with self.assertRaises(ValueError):
                restore_backup(project, backup, create_safety_backup=False)

    def test_support_request_and_app_info(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            create_article("問い合わせ記事", articles_dir=project / "articles", tags=["note"])

            request = create_support_request(project)
            request_exists = request.exists()
            text = request.read_text(encoding="utf-8")
            template = build_support_request(project)
            private_template = build_support_request(project, include_private=True)
            bundle = create_support_bundle(project)
            bundle_errors = verify_support_bundle(bundle)
            bundle_verification_text = format_support_bundle_verification(bundle, bundle_errors)
            with zipfile.ZipFile(bundle) as archive:
                bundle_names = set(archive.namelist())
                bundle_readme = archive.read("README.txt").decode("utf-8")
                bundled_request = archive.read("support-request.md").decode("utf-8")
                diagnostic_bytes = archive.read("diagnostic-report.zip")
                bundle_manifest = json.loads(archive.read("SUPPORT_BUNDLE_MANIFEST.json").decode("utf-8"))
                checksums = archive.read("CHECKSUMS.txt").decode("utf-8")
            with zipfile.ZipFile(io.BytesIO(diagnostic_bytes)) as nested:
                diagnostic_names = set(nested.namelist())
            maintenance_preview = preview_diagnostic_report(project)
            install_info = project / ".auto-note" / "install-info.json"
            install_info.write_text(
                '{"installed_at":"2026-06-06T10:00:00","version":"0.1.0","preinstall_backup":"backup.zip"}',
                encoding="utf-8",
            )
            info = format_app_info(collect_app_info(project))
            privacy = run_privacy_audit(project)
            privacy_text = format_privacy_audit_report(privacy)
            temp_files = list((project / ".auto-note" / "support").glob("*.tmp"))

        self.assertTrue(request_exists)
        self.assertIn("auto-note support request", text)
        self.assertIn("Steps to reproduce / 再現手順", text)
        self.assertIn("Privacy note / プライバシー", text)
        self.assertIn("Diagnostic preview", text)
        self.assertNotIn(str(project), text)
        self.assertNotIn("問い合わせ記事", text)
        self.assertEqual(temp_files, [])
        self.assertIn("auto-note support request", template)
        self.assertIn(str(project), private_template)
        self.assertIn("問い合わせ記事", private_template)
        self.assertEqual(
            bundle_names,
            {
                "README.txt",
                "support-request.md",
                "diagnostic-report.zip",
                "SUPPORT_BUNDLE_MANIFEST.json",
                "CHECKSUMS.txt",
            },
        )
        self.assertEqual(bundle_errors, [])
        self.assertIn("[OK] support bundle verified", bundle_verification_text)
        self.assertIn("privacy-safe", bundle_readme)
        self.assertIn("auto-note support request", bundled_request)
        self.assertNotIn(str(project), bundled_request)
        self.assertNotIn("問い合わせ記事", bundled_request)
        self.assertEqual(bundle_manifest["file_count"], 3)
        self.assertFalse(bundle_manifest["privacy"]["includes_raw_details"])
        self.assertIn("diagnostic-report.zip", checksums)
        self.assertIn("SUPPORT_BUNDLE_MANIFEST.json", checksums)
        self.assertIn("diagnostics.txt", diagnostic_names)
        self.assertIn("first-run.txt", diagnostic_names)
        self.assertIn("commercial-readiness.txt", diagnostic_names)
        self.assertIn("sales-plan.txt", diagnostic_names)
        self.assertIn("sales-materials.txt", diagnostic_names)
        self.assertIn("sales-finalize.txt", diagnostic_names)
        self.assertIn("sales-evidence-manifest.json", diagnostic_names)
        self.assertIn("publish-ready.txt", diagnostic_names)
        self.assertIn("gui-smoke.txt", diagnostic_names)
        self.assertIn("support_requests: 1", maintenance_preview)
        self.assertIn("support_bundles: 1", maintenance_preview)
        self.assertIn("latest_support_bundle_verified: yes", maintenance_preview)
        self.assertIn("privacy_failed_cleanup_candidates: 0", maintenance_preview)
        self.assertFalse(has_privacy_audit_blockers(privacy))
        self.assertIn("Privacy audit report", privacy_text)
        self.assertIn("support request privacy", privacy_text)
        self.assertIn("support bundle privacy", privacy_text)
        self.assertIn("auto-note:", info)
        self.assertIn("Installed at: 2026-06-06T10:00:00", info)
        self.assertIn("Pre-install backup: backup.zip", info)

    def test_support_cli_runs_delivery_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            create_article("CLI問い合わせ記事", articles_dir=project / "articles", tags=["note"])

            request_output = io.StringIO()
            with redirect_stdout(request_output):
                request_code = cli_main(["support", "--project-dir", str(project)])

            bundle_output = io.StringIO()
            with redirect_stdout(bundle_output):
                bundle_code = cli_main(["support", "--project-dir", str(project), "--bundle"])

        request_text = request_output.getvalue()
        bundle_text = bundle_output.getvalue()
        self.assertEqual(request_code, 0)
        self.assertIn("support request created:", request_text)
        self.assertIn("Privacy audit report", request_text)
        self.assertIn("support request privacy", request_text)
        self.assertEqual(bundle_code, 0)
        self.assertIn("support bundle created:", bundle_text)
        self.assertIn("[OK] support bundle verified", bundle_text)
        self.assertIn("Privacy audit report", bundle_text)
        self.assertIn("support bundle privacy", bundle_text)

    def test_unique_path_adds_suffix_when_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "report.zip"
            base.write_text("first", encoding="utf-8")
            second = Path(tmp) / "report-02.zip"
            second.write_text("second", encoding="utf-8")

            path = unique_path(base)

        self.assertEqual(path.name, "report-03.zip")

    def test_support_bundle_verification_detects_checksum_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "support.zip"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("README.txt", "changed")
                archive.writestr("support-request.md", "request")
                archive.writestr("diagnostic-report.zip", b"zip")
                archive.writestr(
                    "SUPPORT_BUNDLE_MANIFEST.json",
                    json.dumps(
                        {
                            "version": "0.1.0",
                            "privacy": {"includes_raw_details": False},
                            "files": [{"path": "README.txt"}],
                        }
                    ),
                )
                archive.writestr("CHECKSUMS.txt", "0" * 64 + "  README.txt\n")

            errors = verify_support_bundle(bundle)

        self.assertIn("checksum mismatch: README.txt", errors)

    def test_privacy_audit_detects_raw_private_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article = create_article("秘密の販売記事タイトル", articles_dir=project / "articles", tags=["note"])
            reports = project / ".auto-note" / "diagnostics"
            reports.mkdir(parents=True)
            leaked = reports / "auto-note-diagnostic-leak.zip"
            with zipfile.ZipFile(leaked, "w") as archive:
                archive.writestr(
                    "diagnostics.txt",
                    f"path={project}\nfile={article.name}\ntitle=秘密の販売記事タイトル\n",
                )

            report = run_privacy_audit(project)
            text = format_privacy_audit_report(report)

        self.assertTrue(has_privacy_audit_blockers(report))
        self.assertIn("raw project path", text)
        self.assertIn("raw article file name", text)
        self.assertIn("raw article title", text)

    def test_privacy_audit_detects_raw_support_request_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article = create_article("秘密の問い合わせ記事", articles_dir=project / "articles", tags=["note"])
            support_dir = project / ".auto-note" / "support"
            support_dir.mkdir(parents=True)
            request = support_dir / "support-request-leak.md"
            request.write_text(
                f"path={project}\nfile={article.name}\ntitle=秘密の問い合わせ記事\n",
                encoding="utf-8",
            )

            report = run_privacy_audit(project)
            text = format_privacy_audit_report(report)

        self.assertTrue(has_privacy_audit_blockers(report))
        self.assertIn("support request privacy", text)
        self.assertIn("raw project path", text)
        self.assertIn("raw article file name", text)
        self.assertIn("raw article title", text)

    def test_privacy_audit_detects_raw_commercial_setup_template_email(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            update_commercial_settings(
                project,
                seller_name="Auto Note Shop",
                sales_channel_url="https://example.com/auto-note",
                refund_policy_url="https://example.com/refund",
                support_contact="help@example.com",
                terms_reviewed=True,
                support_scope_confirmed=True,
            )
            template = create_commercial_setup_template(project)

            report = run_privacy_audit(project)
            text = format_privacy_audit_report(report)
            cleanup = cleanup_generated_files(project, dry_run=True, privacy_failed=True)

        cleanup_names = {item.path.name for item in cleanup.items}
        self.assertTrue(has_privacy_audit_blockers(report))
        self.assertIn("commercial setup template privacy", text)
        self.assertIn("raw email address", text)
        self.assertIn(template.path.name, cleanup_names)

    def test_privacy_audit_scans_verified_release_package_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "src" / "auto_note").mkdir(parents=True)
            (project / "src" / "auto_note" / "__init__.py").write_text("", encoding="utf-8")
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "pyproject.toml").write_text("[project]\nname='auto-note'\n", encoding="utf-8")
            article = create_article(
                "秘密の配布記事タイトル",
                articles_dir=project / "articles",
                tags=["note"],
                slug="private-launch-draft-991",
            )
            (project / "README.md").write_text(
                f"path={project}\nfile={article.name}\ntitle=秘密の配布記事タイトル\n",
                encoding="utf-8",
            )

            package = create_release_package(project)
            release_errors = verify_release_package(package)
            report = run_privacy_audit(project)
            text = format_privacy_audit_report(report)

        self.assertEqual(release_errors, [])
        self.assertTrue(has_privacy_audit_blockers(report))
        self.assertIn("release package privacy", text)
        self.assertIn("raw project path", text)
        self.assertIn("raw article file name", text)
        self.assertIn("raw article title", text)

    def test_privacy_audit_reports_unreadable_release_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            releases = project / ".auto-note" / "releases"
            releases.mkdir(parents=True)
            broken = releases / "auto-note-release-broken.zip"
            broken.write_text("not a zip yet", encoding="utf-8")

            report = run_privacy_audit(project)
            text = format_privacy_audit_report(report)

        self.assertTrue(has_privacy_audit_blockers(report))
        self.assertIn("release package privacy", text)
        self.assertIn("unreadable package", text)

    def test_gui_error_log_appends_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            path = append_gui_error(project, "test error", "Traceback line")
            append_gui_error(project, "second error", "Second traceback")
            text = gui_error_log_path(project).read_text(encoding="utf-8")

        self.assertEqual(path.name, "gui-error.log")
        self.assertIn("test error", text)
        self.assertIn("Traceback line", text)
        self.assertIn("second error", text)

    def test_gui_smoke_initializes_when_desktop_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            create_article("GUIスモーク記事", articles_dir=project / "articles", tags=["note"])
            try:
                text = smoke_gui(project)
            except RuntimeError as exc:
                self.skipTest(f"GUI smoke unavailable: {exc}")

        self.assertIn("GUI smoke OK", text)
        self.assertIn("tabs=", text)
        self.assertIn("articles=", text)
        self.assertIn("first_run_items=", text)
        self.assertIn("home_action_items=", text)
        self.assertIn("review_items=", text)
        self.assertIn("publish_ready_items=", text)
        self.assertIn("home_sales_chars=", text)

    def test_dependency_notices_include_known_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            notices = collect_dependency_notices()
            packages = {notice.package.lower(): notice for notice in notices}
            text = format_dependency_notices(notices)
            written = write_dependency_notices(Path(tmp) / "THIRD_PARTY_NOTICES.md", notices)

            self.assertIn("pyyaml", packages)
            self.assertIn("pillow", packages)
            self.assertIn("playwright", packages)
            self.assertIn("Third-party notices", text)
            self.assertIn("Read article frontmatter metadata", text)
            self.assertTrue(written.exists())
            self.assertIn("Third-party notices", written.read_text(encoding="utf-8"))

    def test_image_report_and_quality_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article_path = project / "articles" / "image.md"
            article_path.parent.mkdir(parents=True)
            article_path.write_text(
                """---
title: 画像記事
cover: cover.png
tags:
  - note
---

本文です。

![missing](missing.png)
""",
                encoding="utf-8",
            )
            (article_path.parent / "cover.png").write_bytes(b"png")

            refs = inspect_images_path(project / "articles")
            report = format_image_report(refs)
            checks = run_quality_checks(project)

        self.assertEqual(len(missing_images(refs)), 1)
        self.assertIn("欠落 1件", report)
        self.assertTrue(has_failures(checks))

    def test_image_import_creates_asset_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article = create_article("画像取り込み", articles_dir=project / "articles", tags=["note"])
            image = project / "source image.PNG"
            image.write_bytes(_png_bytes(width=2, height=3))

            imported = import_image_for_article(article, image, alt_text="説明")
            set_article_cover(article, imported.relative_path)
            loaded = load_article(article)
            info = image_info(imported.target)

            expected = f"{article.stem}-assets/source-image.png"
            self.assertTrue(imported.target.exists())
            self.assertEqual(imported.relative_path, expected)
            self.assertEqual(imported.markdown, f"![説明]({expected})")
            self.assertEqual(loaded.cover, expected)
            self.assertEqual((info.width, info.height, info.image_type), (2, 3, "PNG"))

    def test_image_import_optimize_is_optional(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article = create_article("画像最適化", articles_dir=project / "articles", tags=["note"])
            image = project / "image.png"

            try:
                from PIL import Image
            except ModuleNotFoundError:
                image.write_bytes(_png_bytes(width=2, height=3))
                with self.assertRaises(ArticleError):
                    import_image_for_article(article, image, optimize=True)
                return

            pil_image = Image.new("RGB", (640, 320), color=(255, 0, 0))
            pil_image.save(image)
            imported = import_image_for_article(article, image, optimize=True, max_width=320, quality=80)
            info = image_info(imported.target)

            self.assertEqual(info.width, 320)
            self.assertEqual(info.height, 160)

    def test_history_revision_and_restore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article = create_article("履歴記事", articles_dir=project / "articles", tags=["note"])
            original = article.read_text(encoding="utf-8")
            revision = create_revision(project, article)
            article.write_text("changed", encoding="utf-8")
            revisions = list_revisions(project, article)
            restore_revision(project, article, revision)

            restored = article.read_text(encoding="utf-8")

            self.assertTrue(revision.exists())
            self.assertGreaterEqual(len(revisions), 1)
        self.assertEqual(restored, original)

    def test_autosave_write_detect_read_and_clear(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article = create_article("自動退避記事", articles_dir=project / "articles", tags=["note"])
            os.utime(article, (0, 0))

            autosave = write_autosave(project, article, "unsaved draft")
            state = autosave_state(project, article)

            self.assertTrue(autosave.exists())
            self.assertTrue(state.exists)
            self.assertTrue(state.newer_than_article)
            self.assertTrue(has_newer_autosave(project, article))
            self.assertEqual(read_autosave(project, article), "unsaved draft")
            self.assertTrue(clear_autosave(project, article))
            self.assertFalse(autosave_state(project, article).exists)

    def test_quality_checks_workflow_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            articles = project / "articles"
            create_article("重複タイトル", articles_dir=articles, tags=["note"])
            second = create_article("重複タイトル", articles_dir=articles, tags=["note"])
            text = second.read_text(encoding="utf-8").replace("status: draft", "status: unknown")
            text = text.replace("scheduled: ", "scheduled: tomorrow")
            second.write_text(text, encoding="utf-8")

            checks = run_quality_checks(project)
            product_checks = run_quality_checks(project, include_articles=False)
            (project / "auto-note-gui.bat").write_text(
                "python -m auto_note gui --smoke\npython -m auto_note support --project-dir . --bundle\n",
                encoding="utf-8",
            )
            (project / "scripts").mkdir(exist_ok=True)
            (project / "scripts" / "launch-gui.vbs").write_text(
                'batPath = fso.BuildPath(projectDir, "auto-note-gui.bat")\n'
                "AUTO_NOTE_LAUNCHER_CHECK\n"
                "exitCode = shell.Run(command, 0, True)\n",
                encoding="utf-8",
            )
            (project / ".github" / "workflows").mkdir(parents=True)
            (project / ".github" / "workflows" / "ci.yml").write_text(
                "windows-latest\n"
                "python -m unittest discover -s tests\n"
                "python -m auto_note quality --project-dir . --product-only\n"
                "AUTO_NOTE_LAUNCHER_CHECK\n"
                "python -m auto_note gui --project-dir . --smoke\n",
                encoding="utf-8",
            )
            (project / "scripts" / "create-gui-shortcut.ps1").write_text(
                '$launcher = Join-Path $project "scripts\\launch-gui.vbs"\n'
                '$shortcut.TargetPath = "$env:SystemRoot\\System32\\wscript.exe"\n'
                '$shortcut.IconLocation = "$env:SystemRoot\\System32\\imageres.dll,101"\n',
                encoding="utf-8",
            )
            (project / "src" / "auto_note").mkdir(parents=True)
            (project / "src" / "auto_note" / "__init__.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
            (project / "src" / "auto_note" / "__main__.py").write_text(
                "starter-pack\nstarter-clean\nrepair\ntroubleshoot\nacceptance\n--full\ncommercial-readiness\n--policy-review\ncommercial-setup\nCreate a seller profile fill-in template\n--apply-template\nsales-handoff\n--extract-buyer\n--verify-buyer\n--package-buyer\n--verify-buyer-package\nsales-materials\nVerify a sales materials markdown file.\nsales-finalize\nApply the latest seller profile template before finalizing sales artifacts.\n--send-check\n--send-check-report\n--delivery-receipt\nsales-plan\nsales plan report created\n",
                encoding="utf-8",
            )
            (project / "src" / "auto_note" / "commercial.py").write_text(
                "write_commercial_policy_review\nlist_commercial_policy_reviews\n",
                encoding="utf-8",
            )
            (project / "src" / "auto_note" / "commercial_setup.py").write_text(
                "commercial_setup_warnings\ncommercial_setup_next_actions\ncommercial_setup_completion\ncommercial_setup_next_field\nSafe Apply / 編集後の保存\nsales-finalize --project-dir . --apply-latest-template\nauto-note sales-plan --project-dir .\n",
                encoding="utf-8",
            )
            (project / "src" / "auto_note" / "action_plan.py").write_text(
                "commercial_setup_missing_fields\n設定 > 次の不足へ\n",
                encoding="utf-8",
            )
            (project / "src" / "auto_note" / "sales_materials.py").write_text(
                "commercial setup warning:\nBuyer First 10 Minutes\n",
                encoding="utf-8",
            )
            (project / "src" / "auto_note" / "sales_handoff.py").write_text(
                "購入者の最初の10分\nDELIVERY_CHECKLIST.txt\nSELLER_DELIVERY_RECEIPT.txt\nextract_buyer_delivery\nverify_buyer_delivery\nSHA256SUMS.txt\nPackage SHA-256\nSTART_HERE_FOR_BUYER.txt\nBUYER_SUPPORT_GUIDE.txt\nBUYER_DELIVERY_MANIFEST.json\n_verify_buyer_delivery_manifest\npackage_buyer_delivery\nverify_buyer_delivery_package\n",
                encoding="utf-8",
            )
            (project / "src" / "auto_note" / "sales_finalize.py").write_text(
                "include_sales_handoffs=False\nwrite_acceptance_report\nextract_buyer_delivery\nverify_buyer_delivery\nverify_buyer_delivery_package\n_write_buyer_delivery_message\nlist_buyer_delivery_messages\nrun_buyer_send_readiness\nformat_buyer_send_readiness_report\nwrite_buyer_send_readiness_report\nlist_buyer_send_readiness_reports\nwrite_seller_delivery_receipt\nformat_seller_delivery_receipt\nlist_seller_delivery_receipts\nfind_buyer_delivery_package_for_message\n_write_seller_send_checklist\nlist_seller_send_checklists\n_delivery_verification_lines\nwrite_sales_plan_report\nsales plan report\nSales plan evidence\nsales_plan_report_path\n_write_sales_evidence_manifest\nlist_sales_evidence_manifests\nsales evidence manifest\nSales evidence manifest\nsales_evidence_manifest_path\n",
                encoding="utf-8",
            )
            (project / "src" / "auto_note" / "privacy.py").write_text(
                "seller send checklist privacy\nlist_seller_send_checklists\nbuyer delivery message privacy\nlist_buyer_delivery_messages\nbuyer send readiness report privacy\nseller delivery receipt privacy\nlist_seller_delivery_receipts\nsales plan report privacy\ncommercial policy review privacy\nsales evidence manifest privacy\n",
                encoding="utf-8",
            )
            (project / "src" / "auto_note" / "diagnostics.py").write_text(
                "seller-send-checklist.txt\nseller_send_checklists\nbuyer_delivery_messages\nbuyer_send_readiness_reports\nseller_delivery_receipts\nsales_plan_reports\ncommercial_policy_reviews\nsales-evidence-manifest.json\n_commercial_setup_item\nsales_evidence_manifests\n",
                encoding="utf-8",
            )
            (project / "src" / "auto_note" / "maintenance.py").write_text(
                "seller-send-checklist-*.txt\nbuyer-delivery-message-*.txt\nbuyer-send-readiness-*.txt\nseller-delivery-receipt-*.txt\nsales-plan-*.txt\ncommercial-policy-review-*.txt\nsales-evidence-manifest-*.json\n",
                encoding="utf-8",
            )
            (project / "src" / "auto_note" / "sales_plan.py").write_text(
                "list_buyer_delivery_packages\nverify_buyer_delivery_package\nLatest buyer delivery zip\nBuyer delivery readiness\nSeller setup remaining\nTool/artifact actions remaining\nUpload guidance\n_buyer_delivery_package_release_name\nwrite_sales_plan_report\nlist_sales_plan_reports\n_project_relative_path\n",
                encoding="utf-8",
            )
            (project / "src" / "auto_note" / "gui.py").write_text(
                "スターター一式\nスターター整理\n自動修復\nトラブル診断\n受入チェック\n受入フル保存\n販売準備\n方針レビュー\ncreate_commercial_policy_review_action\n販売者/屋号\n販売者情報確認\n_notify_settings_saved\ncommercial_progress_var\nfocus_next_commercial_missing_field\n販売者情報へ\nhome_sales_status_var\nrun_home_sales_next_action\n_home_sales_lightweight_next_step\nbuyer_messages\nseller_receipts\n販売者テンプレ\nテンプレ適用\n販売一式作成\n購入者ZIP抽出\n購入者ZIP検証\n送付前チェック\nrun_buyer_send_readiness_to_tab\n送付前保存\ncreate_buyer_send_readiness_report_action\n送付記録\ncreate_seller_delivery_receipt_action\n送付文コピー\ncopy_latest_buyer_delivery_message_action\n販売素材作成\n販売素材検証\nテンプレ取込一括\n販売一括作成\nbuyer_delivery_dir\nbuyer_delivery_package_path\nbuyer_delivery_message_path\nsales_plan_report_path\nseller_send_checklist_path\nsales_evidence_manifest_path\n販売ナビ\n販売ナビ保存\n",
                encoding="utf-8",
            )
            (project / "src" / "auto_note" / "release.py").write_text(
                "FIRST_RUN_CHECKLIST.txt\nBUYER_ACCEPTANCE_CHECKLIST.txt\nstarter-pack\nauto-note repair\nauto-note troubleshoot\nauto-note acceptance\nauto-note acceptance --project-dir . --full\n",
                encoding="utf-8",
            )
            (project / "README.md").write_text(
                "starter-pack\nauto-note repair\nauto-note troubleshoot\nauto-note acceptance\nauto-note acceptance --project-dir . --full\nauto-note commercial-readiness\ncommercial-readiness --project-dir . --policy-review\nauto-note commercial-setup\n販売準備サマリー\ncommercial-setup --project-dir . --template\ncommercial-setup --project-dir . --apply-latest-template\n未入力のプレースホルダー\n次の不足へ\n販売者テンプレート\nauto-note sales-handoff\nsales-handoff --project-dir . --extract-buyer\nsales-handoff --project-dir . --verify-buyer\nsales-handoff --project-dir . --package-buyer\nsales-handoff --project-dir . --verify-buyer-package\nauto-note sales-materials\nsales-materials --project-dir . --verify\nauto-note sales-finalize\nsales-finalize --project-dir . --apply-latest-template\nsales-finalize --project-dir . --send-check --send-check-report\nsales-finalize --project-dir . --delivery-receipt\n送付前チェック\n送付記録\n送付文コピー\nauto-note sales-plan\nUpload guidance\nsales-plan --project-dir . --report\nsales-evidence-manifest\n",
                encoding="utf-8",
            )
            (project / "docs").mkdir(exist_ok=True)
            (project / "docs" / "PRODUCT_READINESS.md").write_text(
                "auto-note acceptance --project-dir . --full\ncommercial-readiness\ncommercial-readiness --project-dir . --policy-review\ncommercial-setup\n販売準備サマリー\n軽量判定\n送付文有無\ncommercial-setup --project-dir . --template\ncommercial-setup --project-dir . --apply-latest-template\n未入力プレースホルダー\n次の不足へ\nsales-handoff\n--extract-buyer\n--verify-buyer\n--package-buyer\n--verify-buyer-package\nsales-materials\nsales-materials --project-dir . --verify\nsales-finalize\nsales-finalize --project-dir . --apply-latest-template\nsales-finalize --project-dir . --send-check --send-check-report\nsales-finalize --project-dir . --delivery-receipt\n送付前チェック\n送付記録\n送付文コピー\nsales-plan\nUpload guidance\nsales-plan --project-dir . --report\nsales-evidence-manifest\n",
                encoding="utf-8",
            )
            (project / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n', encoding="utf-8")
            launcher_checks = run_quality_checks(project, include_articles=False)

        details = "\n".join(f"{check.name}:{check.status}" for check in checks)
        product_details = "\n".join(f"{check.name}:{check.status}" for check in product_checks)
        launcher_details = "\n".join(f"{check.name}:{check.status}" for check in launcher_checks)
        self.assertIn("duplicate titles:warn", details)
        self.assertIn("workflow status:fail", details)
        self.assertIn("schedule format:fail", details)
        self.assertTrue(any(check.name == "article review" for check in checks))
        self.assertIn("GUI launcher smoke check:fail", product_details)
        self.assertIn("GUI launcher support bundle guidance:fail", product_details)
        self.assertIn("hidden GUI launcher check mode:fail", product_details)
        self.assertIn("version consistency:fail", product_details)
        self.assertIn("GitHub Actions CI:fail", product_details)
        self.assertIn("CI Windows runner:fail", product_details)
        self.assertIn("CI unit tests:fail", product_details)
        self.assertIn("CI product quality gate:fail", product_details)
        self.assertIn("CI hidden launcher syntax check:fail", product_details)
        self.assertIn("CI GUI smoke:fail", product_details)
        self.assertIn("release first-run checklist:fail", product_details)
        self.assertIn("CLI starter pack command:fail", product_details)
        self.assertIn("CLI starter cleanup command:fail", product_details)
        self.assertIn("CLI repair command:fail", product_details)
        self.assertIn("CLI troubleshoot command:fail", product_details)
        self.assertIn("CLI acceptance command:fail", product_details)
        self.assertIn("CLI acceptance full command:fail", product_details)
        self.assertIn("CLI commercial readiness command:fail", product_details)
        self.assertIn("CLI commercial policy review command:fail", product_details)
        self.assertIn("commercial policy review writer:fail", product_details)
        self.assertIn("commercial policy review lister:fail", product_details)
        self.assertIn("CLI commercial setup command:fail", product_details)
        self.assertIn("CLI commercial setup template command:fail", product_details)
        self.assertIn("CLI commercial setup template apply command:fail", product_details)
        self.assertIn("commercial setup URL/contact warnings:fail", product_details)
        self.assertIn("commercial setup next actions:fail", product_details)
        self.assertIn("commercial setup completion progress:fail", product_details)
        self.assertIn("commercial setup next field helper:fail", product_details)
        self.assertIn("commercial setup safe template apply:fail", product_details)
        self.assertIn("commercial setup sales finalize followup:fail", product_details)
        self.assertIn("commercial setup sales plan followup:fail", product_details)
        self.assertIn("action plan commercial setup guidance:fail", product_details)
        self.assertIn("action plan commercial setup next missing GUI guidance:fail", product_details)
        self.assertIn("CLI sales handoff command:fail", product_details)
        self.assertIn("CLI sales materials command:fail", product_details)
        self.assertIn("CLI sales materials verify command:fail", product_details)
        self.assertIn("sales materials commercial setup warnings:fail", product_details)
        self.assertIn("sales materials buyer first 10 minutes:fail", product_details)
        self.assertIn("sales handoff buyer first 10 minutes:fail", product_details)
        self.assertIn("sales handoff delivery checklist:fail", product_details)
        self.assertIn("CLI sales handoff buyer extract command:fail", product_details)
        self.assertIn("CLI sales handoff buyer verify command:fail", product_details)
        self.assertIn("CLI sales handoff buyer package command:fail", product_details)
        self.assertIn("CLI sales handoff buyer package verify command:fail", product_details)
        self.assertIn("sales handoff buyer delivery extractor:fail", product_details)
        self.assertIn("sales handoff buyer delivery verifier:fail", product_details)
        self.assertIn("sales handoff buyer support guide:fail", product_details)
        self.assertIn("sales handoff buyer delivery manifest:fail", product_details)
        self.assertIn("sales handoff buyer delivery manifest verifier:fail", product_details)
        self.assertIn("sales handoff buyer delivery package:fail", product_details)
        self.assertIn("sales handoff buyer delivery package verifier:fail", product_details)
        self.assertIn("CLI sales finalize command:fail", product_details)
        self.assertIn("CLI sales finalize template apply command:fail", product_details)
        self.assertIn("sales finalize ignores stale handoffs during preflight:fail", product_details)
        self.assertIn("sales finalize creates buyer delivery:fail", product_details)
        self.assertIn("sales finalize verifies buyer delivery:fail", product_details)
        self.assertIn("sales finalize verifies buyer delivery zip:fail", product_details)
        self.assertIn("sales finalize seller send checklist:fail", product_details)
        self.assertIn("privacy audit seller send checklist:fail", product_details)
        self.assertIn("diagnostic seller send checklist:fail", product_details)
        self.assertIn("cleanup seller send checklist:fail", product_details)
        self.assertIn("CLI sales plan command:fail", product_details)
        self.assertIn("CLI sales plan report command:fail", product_details)
        self.assertIn("sales plan buyer delivery package list:fail", product_details)
        self.assertIn("sales plan buyer delivery package verifier:fail", product_details)
        self.assertIn("sales plan buyer delivery package summary:fail", product_details)
        self.assertIn("sales plan buyer delivery readiness summary:fail", product_details)
        self.assertIn("sales plan seller setup remaining summary:fail", product_details)
        self.assertIn("sales plan tool artifact remaining summary:fail", product_details)
        self.assertIn("sales plan upload guidance:fail", product_details)
        self.assertIn("sales plan buyer delivery package freshness:fail", product_details)
        self.assertIn("sales plan report writer:fail", product_details)
        self.assertIn("sales plan report lister:fail", product_details)
        self.assertIn("sales plan relative verify command:fail", product_details)
        self.assertIn("privacy audit sales plan report:fail", product_details)
        self.assertIn("privacy audit commercial policy review:fail", product_details)
        self.assertIn("cleanup sales plan report:fail", product_details)
        self.assertIn("cleanup commercial policy review:fail", product_details)
        self.assertIn("maintenance sales plan report summary:fail", product_details)
        self.assertIn("diagnostic sales evidence manifest:fail", product_details)
        self.assertIn("diagnostic commercial setup summary:fail", product_details)
        self.assertIn("diagnostic commercial policy review summary:fail", product_details)
        self.assertIn("maintenance sales evidence manifest summary:fail", product_details)
        self.assertIn("sales finalize creates sales plan report:fail", product_details)
        self.assertIn("sales finalize artifacts sales plan report:fail", product_details)
        self.assertIn("sales finalize seller checklist sales plan evidence:fail", product_details)
        self.assertIn("sales evidence manifest writer:fail", product_details)
        self.assertIn("sales evidence manifest lister:fail", product_details)
        self.assertIn("sales finalize artifacts sales evidence manifest:fail", product_details)
        self.assertIn("seller checklist sales evidence manifest:fail", product_details)
        self.assertIn("privacy audit sales evidence manifest:fail", product_details)
        self.assertIn("cleanup sales evidence manifest:fail", product_details)
        self.assertIn("GUI starter pack action:fail", product_details)
        self.assertIn("GUI starter cleanup action:fail", product_details)
        self.assertIn("GUI repair action:fail", product_details)
        self.assertIn("GUI troubleshoot action:fail", product_details)
        self.assertIn("GUI acceptance action:fail", product_details)
        self.assertIn("GUI acceptance full action:fail", product_details)
        self.assertIn("GUI commercial readiness action:fail", product_details)
        self.assertIn("GUI commercial policy review action:fail", product_details)
        self.assertIn("GUI commercial setup fields:fail", product_details)
        self.assertIn("GUI commercial setup template action:fail", product_details)
        self.assertIn("GUI commercial setup template apply action:fail", product_details)
        self.assertIn("GUI commercial setup status action:fail", product_details)
        self.assertIn("GUI commercial setup save feedback:fail", product_details)
        self.assertIn("GUI commercial setup progress panel:fail", product_details)
        self.assertIn("GUI commercial setup next missing action:fail", product_details)
        self.assertIn("GUI commercial setup command palette action:fail", product_details)
        self.assertIn("GUI home sales summary panel:fail", product_details)
        self.assertIn("GUI home sales next action:fail", product_details)
        self.assertIn("GUI home sales lightweight summary:fail", product_details)
        self.assertIn("GUI sales handoff action:fail", product_details)
        self.assertIn("GUI sales handoff buyer extract action:fail", product_details)
        self.assertIn("GUI sales handoff buyer verify action:fail", product_details)
        self.assertIn("GUI sales materials action:fail", product_details)
        self.assertIn("GUI sales materials verify action:fail", product_details)
        self.assertIn("GUI sales finalize action:fail", product_details)
        self.assertIn("GUI sales finalize template apply action:fail", product_details)
        self.assertIn("GUI sales finalize opens buyer delivery:fail", product_details)
        self.assertIn("GUI sales finalize opens buyer delivery zip:fail", product_details)
        self.assertIn("GUI sales finalize opens sales plan report:fail", product_details)
        self.assertIn("GUI sales finalize opens seller send checklist:fail", product_details)
        self.assertIn("GUI sales finalize opens sales evidence manifest:fail", product_details)
        self.assertIn("GUI sales plan action:fail", product_details)
        self.assertIn("GUI sales plan report action:fail", product_details)
        self.assertIn("README starter pack guidance:fail", product_details)
        self.assertIn("README repair guidance:fail", product_details)
        self.assertIn("README troubleshoot guidance:fail", product_details)
        self.assertIn("README acceptance guidance:fail", product_details)
        self.assertIn("README acceptance full guidance:fail", product_details)
        self.assertIn("README commercial readiness guidance:fail", product_details)
        self.assertIn("README commercial policy review guidance:fail", product_details)
        self.assertIn("README commercial setup guidance:fail", product_details)
        self.assertIn("README home sales summary guidance:fail", product_details)
        self.assertIn("README commercial setup template guidance:fail", product_details)
        self.assertIn("README commercial setup template apply guidance:fail", product_details)
        self.assertIn("README commercial setup safe template guidance:fail", product_details)
        self.assertIn("README commercial setup GUI next missing guidance:fail", product_details)
        self.assertIn("README privacy audit commercial setup template guidance:fail", product_details)
        self.assertIn("README sales handoff guidance:fail", product_details)
        self.assertIn("README sales handoff buyer extract guidance:fail", product_details)
        self.assertIn("README sales handoff buyer verify guidance:fail", product_details)
        self.assertIn("README sales handoff buyer package guidance:fail", product_details)
        self.assertIn("README sales handoff buyer package verify guidance:fail", product_details)
        self.assertIn("README sales materials guidance:fail", product_details)
        self.assertIn("README sales materials verify guidance:fail", product_details)
        self.assertIn("README sales finalize guidance:fail", product_details)
        self.assertIn("README sales finalize template apply guidance:fail", product_details)
        self.assertIn("README sales plan guidance:fail", product_details)
        self.assertIn("README sales plan upload guidance:fail", product_details)
        self.assertIn("README sales plan report guidance:fail", product_details)
        self.assertIn("README sales evidence manifest guidance:fail", product_details)
        self.assertIn("product readiness acceptance full command:fail", product_details)
        self.assertIn("product readiness commercial command:fail", product_details)
        self.assertIn("product readiness commercial policy review command:fail", product_details)
        self.assertIn("product readiness commercial setup command:fail", product_details)
        self.assertIn("product readiness home sales summary guidance:fail", product_details)
        self.assertIn("product readiness home sales lightweight guidance:fail", product_details)
        self.assertIn("product readiness commercial setup template command:fail", product_details)
        self.assertIn("product readiness commercial setup template apply command:fail", product_details)
        self.assertIn("product readiness commercial setup safe template guidance:fail", product_details)
        self.assertIn("product readiness commercial setup GUI next missing guidance:fail", product_details)
        self.assertIn("product readiness sales handoff command:fail", product_details)
        self.assertIn("product readiness sales handoff buyer extract command:fail", product_details)
        self.assertIn("product readiness sales handoff buyer verify command:fail", product_details)
        self.assertIn("product readiness sales handoff buyer package command:fail", product_details)
        self.assertIn("product readiness sales handoff buyer package verify command:fail", product_details)
        self.assertIn("product readiness sales materials command:fail", product_details)
        self.assertIn("product readiness sales materials verify command:fail", product_details)
        self.assertIn("product readiness sales finalize command:fail", product_details)
        self.assertIn("product readiness sales finalize template apply command:fail", product_details)
        self.assertIn("product readiness sales plan command:fail", product_details)
        self.assertIn("product readiness sales plan upload guidance:fail", product_details)
        self.assertIn("product readiness sales plan report guidance:fail", product_details)
        self.assertIn("product readiness sales evidence manifest guidance:fail", product_details)
        self.assertIn("release starter pack guidance:fail", product_details)
        self.assertIn("release repair guidance:fail", product_details)
        self.assertIn("release troubleshoot guidance:fail", product_details)
        self.assertIn("release buyer acceptance checklist:fail", product_details)
        self.assertIn("release buyer acceptance full guidance:fail", product_details)
        self.assertIn("version consistency:pass", launcher_details)
        self.assertIn("GitHub Actions CI:pass", launcher_details)
        self.assertIn("CI Windows runner:pass", launcher_details)
        self.assertIn("CI unit tests:pass", launcher_details)
        self.assertIn("CI product quality gate:pass", launcher_details)
        self.assertIn("CI hidden launcher syntax check:pass", launcher_details)
        self.assertIn("CI GUI smoke:pass", launcher_details)
        self.assertIn("release first-run checklist:pass", launcher_details)
        self.assertIn("CLI starter pack command:pass", launcher_details)
        self.assertIn("CLI starter cleanup command:pass", launcher_details)
        self.assertIn("CLI repair command:pass", launcher_details)
        self.assertIn("CLI troubleshoot command:pass", launcher_details)
        self.assertIn("CLI acceptance command:pass", launcher_details)
        self.assertIn("CLI acceptance full command:pass", launcher_details)
        self.assertIn("CLI commercial readiness command:pass", launcher_details)
        self.assertIn("CLI commercial policy review command:pass", launcher_details)
        self.assertIn("commercial policy review writer:pass", launcher_details)
        self.assertIn("commercial policy review lister:pass", launcher_details)
        self.assertIn("CLI commercial setup command:pass", launcher_details)
        self.assertIn("CLI commercial setup template command:pass", launcher_details)
        self.assertIn("CLI commercial setup template apply command:pass", launcher_details)
        self.assertIn("commercial setup URL/contact warnings:pass", launcher_details)
        self.assertIn("commercial setup next actions:pass", launcher_details)
        self.assertIn("commercial setup completion progress:pass", launcher_details)
        self.assertIn("commercial setup next field helper:pass", launcher_details)
        self.assertIn("commercial setup safe template apply:pass", launcher_details)
        self.assertIn("commercial setup sales finalize followup:pass", launcher_details)
        self.assertIn("commercial setup sales plan followup:pass", launcher_details)
        self.assertIn("action plan commercial setup guidance:pass", launcher_details)
        self.assertIn("action plan commercial setup next missing GUI guidance:pass", launcher_details)
        self.assertIn("CLI sales handoff command:pass", launcher_details)
        self.assertIn("CLI sales materials command:pass", launcher_details)
        self.assertIn("CLI sales materials verify command:pass", launcher_details)
        self.assertIn("sales materials commercial setup warnings:pass", launcher_details)
        self.assertIn("sales materials buyer first 10 minutes:pass", launcher_details)
        self.assertIn("sales handoff buyer first 10 minutes:pass", launcher_details)
        self.assertIn("sales handoff delivery checklist:pass", launcher_details)
        self.assertIn("CLI sales handoff buyer extract command:pass", launcher_details)
        self.assertIn("CLI sales handoff buyer verify command:pass", launcher_details)
        self.assertIn("CLI sales handoff buyer package command:pass", launcher_details)
        self.assertIn("CLI sales handoff buyer package verify command:pass", launcher_details)
        self.assertIn("sales handoff buyer delivery extractor:pass", launcher_details)
        self.assertIn("sales handoff buyer delivery verifier:pass", launcher_details)
        self.assertIn("sales handoff buyer support guide:pass", launcher_details)
        self.assertIn("sales handoff buyer delivery manifest:pass", launcher_details)
        self.assertIn("sales handoff buyer delivery manifest verifier:pass", launcher_details)
        self.assertIn("sales handoff buyer delivery package:pass", launcher_details)
        self.assertIn("sales handoff buyer delivery package verifier:pass", launcher_details)
        self.assertIn("CLI sales finalize command:pass", launcher_details)
        self.assertIn("CLI sales finalize template apply command:pass", launcher_details)
        self.assertIn("sales finalize ignores stale handoffs during preflight:pass", launcher_details)
        self.assertIn("sales finalize creates buyer delivery:pass", launcher_details)
        self.assertIn("sales finalize verifies buyer delivery:pass", launcher_details)
        self.assertIn("sales finalize verifies buyer delivery zip:pass", launcher_details)
        self.assertIn("sales finalize seller send checklist:pass", launcher_details)
        self.assertIn("privacy audit seller send checklist:pass", launcher_details)
        self.assertIn("diagnostic seller send checklist:pass", launcher_details)
        self.assertIn("cleanup seller send checklist:pass", launcher_details)
        self.assertIn("CLI sales plan command:pass", launcher_details)
        self.assertIn("CLI sales plan report command:pass", launcher_details)
        self.assertIn("sales plan buyer delivery package list:pass", launcher_details)
        self.assertIn("sales plan buyer delivery package verifier:pass", launcher_details)
        self.assertIn("sales plan buyer delivery package summary:pass", launcher_details)
        self.assertIn("sales plan buyer delivery readiness summary:pass", launcher_details)
        self.assertIn("sales plan seller setup remaining summary:pass", launcher_details)
        self.assertIn("sales plan tool artifact remaining summary:pass", launcher_details)
        self.assertIn("sales plan upload guidance:pass", launcher_details)
        self.assertIn("sales plan buyer delivery package freshness:pass", launcher_details)
        self.assertIn("sales plan report writer:pass", launcher_details)
        self.assertIn("sales plan report lister:pass", launcher_details)
        self.assertIn("sales plan relative verify command:pass", launcher_details)
        self.assertIn("privacy audit sales plan report:pass", launcher_details)
        self.assertIn("privacy audit commercial policy review:pass", launcher_details)
        self.assertIn("cleanup sales plan report:pass", launcher_details)
        self.assertIn("cleanup commercial policy review:pass", launcher_details)
        self.assertIn("maintenance sales plan report summary:pass", launcher_details)
        self.assertIn("diagnostic sales evidence manifest:pass", launcher_details)
        self.assertIn("diagnostic commercial setup summary:pass", launcher_details)
        self.assertIn("diagnostic commercial policy review summary:pass", launcher_details)
        self.assertIn("maintenance sales evidence manifest summary:pass", launcher_details)
        self.assertIn("sales finalize creates sales plan report:pass", launcher_details)
        self.assertIn("sales finalize artifacts sales plan report:pass", launcher_details)
        self.assertIn("sales finalize seller checklist sales plan evidence:pass", launcher_details)
        self.assertIn("sales evidence manifest writer:pass", launcher_details)
        self.assertIn("sales evidence manifest lister:pass", launcher_details)
        self.assertIn("sales finalize artifacts sales evidence manifest:pass", launcher_details)
        self.assertIn("seller checklist sales evidence manifest:pass", launcher_details)
        self.assertIn("privacy audit sales evidence manifest:pass", launcher_details)
        self.assertIn("cleanup sales evidence manifest:pass", launcher_details)
        self.assertIn("GUI starter pack action:pass", launcher_details)
        self.assertIn("GUI starter cleanup action:pass", launcher_details)
        self.assertIn("GUI repair action:pass", launcher_details)
        self.assertIn("GUI troubleshoot action:pass", launcher_details)
        self.assertIn("GUI acceptance action:pass", launcher_details)
        self.assertIn("GUI acceptance full action:pass", launcher_details)
        self.assertIn("GUI commercial readiness action:pass", launcher_details)
        self.assertIn("GUI commercial policy review action:pass", launcher_details)
        self.assertIn("GUI commercial setup fields:pass", launcher_details)
        self.assertIn("GUI commercial setup template action:pass", launcher_details)
        self.assertIn("GUI commercial setup template apply action:pass", launcher_details)
        self.assertIn("GUI commercial setup status action:pass", launcher_details)
        self.assertIn("GUI commercial setup save feedback:pass", launcher_details)
        self.assertIn("GUI commercial setup progress panel:pass", launcher_details)
        self.assertIn("GUI commercial setup next missing action:pass", launcher_details)
        self.assertIn("GUI commercial setup command palette action:pass", launcher_details)
        self.assertIn("GUI home sales summary panel:pass", launcher_details)
        self.assertIn("GUI home sales next action:pass", launcher_details)
        self.assertIn("GUI home sales lightweight summary:pass", launcher_details)
        self.assertIn("GUI sales handoff action:pass", launcher_details)
        self.assertIn("GUI sales handoff buyer extract action:pass", launcher_details)
        self.assertIn("GUI sales handoff buyer verify action:pass", launcher_details)
        self.assertIn("GUI sales materials action:pass", launcher_details)
        self.assertIn("GUI sales materials verify action:pass", launcher_details)
        self.assertIn("GUI sales finalize action:pass", launcher_details)
        self.assertIn("GUI sales finalize template apply action:pass", launcher_details)
        self.assertIn("GUI sales finalize opens buyer delivery:pass", launcher_details)
        self.assertIn("GUI sales finalize opens buyer delivery zip:pass", launcher_details)
        self.assertIn("GUI sales finalize opens sales plan report:pass", launcher_details)
        self.assertIn("GUI sales finalize opens seller send checklist:pass", launcher_details)
        self.assertIn("GUI sales finalize opens sales evidence manifest:pass", launcher_details)
        self.assertIn("GUI sales plan action:pass", launcher_details)
        self.assertIn("GUI sales plan report action:pass", launcher_details)
        self.assertIn("README starter pack guidance:pass", launcher_details)
        self.assertIn("README repair guidance:pass", launcher_details)
        self.assertIn("README troubleshoot guidance:pass", launcher_details)
        self.assertIn("README acceptance guidance:pass", launcher_details)
        self.assertIn("README acceptance full guidance:pass", launcher_details)
        self.assertIn("README commercial readiness guidance:pass", launcher_details)
        self.assertIn("README commercial policy review guidance:pass", launcher_details)
        self.assertIn("README commercial setup guidance:pass", launcher_details)
        self.assertIn("README home sales summary guidance:pass", launcher_details)
        self.assertIn("README commercial setup template guidance:pass", launcher_details)
        self.assertIn("README commercial setup template apply guidance:pass", launcher_details)
        self.assertIn("README commercial setup safe template guidance:pass", launcher_details)
        self.assertIn("README commercial setup GUI next missing guidance:pass", launcher_details)
        self.assertIn("README privacy audit commercial setup template guidance:pass", launcher_details)
        self.assertIn("README sales handoff guidance:pass", launcher_details)
        self.assertIn("README sales handoff buyer extract guidance:pass", launcher_details)
        self.assertIn("README sales handoff buyer verify guidance:pass", launcher_details)
        self.assertIn("README sales handoff buyer package guidance:pass", launcher_details)
        self.assertIn("README sales handoff buyer package verify guidance:pass", launcher_details)
        self.assertIn("README sales materials guidance:pass", launcher_details)
        self.assertIn("README sales materials verify guidance:pass", launcher_details)
        self.assertIn("README sales finalize guidance:pass", launcher_details)
        self.assertIn("README sales finalize template apply guidance:pass", launcher_details)
        self.assertIn("README sales plan guidance:pass", launcher_details)
        self.assertIn("README sales plan upload guidance:pass", launcher_details)
        self.assertIn("README sales plan report guidance:pass", launcher_details)
        self.assertIn("README sales evidence manifest guidance:pass", launcher_details)
        self.assertIn("product readiness acceptance full command:pass", launcher_details)
        self.assertIn("product readiness commercial command:pass", launcher_details)
        self.assertIn("product readiness commercial policy review command:pass", launcher_details)
        self.assertIn("product readiness commercial setup command:pass", launcher_details)
        self.assertIn("product readiness home sales summary guidance:pass", launcher_details)
        self.assertIn("product readiness home sales lightweight guidance:pass", launcher_details)
        self.assertIn("product readiness commercial setup template command:pass", launcher_details)
        self.assertIn("product readiness commercial setup template apply command:pass", launcher_details)
        self.assertIn("product readiness commercial setup safe template guidance:pass", launcher_details)
        self.assertIn("product readiness commercial setup GUI next missing guidance:pass", launcher_details)
        self.assertIn("product readiness sales handoff command:pass", launcher_details)
        self.assertIn("product readiness sales handoff buyer extract command:pass", launcher_details)
        self.assertIn("product readiness sales handoff buyer verify command:pass", launcher_details)
        self.assertIn("product readiness sales handoff buyer package command:pass", launcher_details)
        self.assertIn("product readiness sales handoff buyer package verify command:pass", launcher_details)
        self.assertIn("product readiness sales materials command:pass", launcher_details)
        self.assertIn("product readiness sales materials verify command:pass", launcher_details)
        self.assertIn("product readiness sales finalize command:pass", launcher_details)
        self.assertIn("product readiness sales finalize template apply command:pass", launcher_details)
        self.assertIn("product readiness sales plan command:pass", launcher_details)
        self.assertIn("product readiness sales plan upload guidance:pass", launcher_details)
        self.assertIn("product readiness sales plan report guidance:pass", launcher_details)
        self.assertIn("product readiness sales evidence manifest guidance:pass", launcher_details)
        self.assertIn("release starter pack guidance:pass", launcher_details)
        self.assertIn("release repair guidance:pass", launcher_details)
        self.assertIn("release troubleshoot guidance:pass", launcher_details)
        self.assertIn("release buyer acceptance checklist:pass", launcher_details)
        self.assertIn("release buyer acceptance full guidance:pass", launcher_details)
        self.assertIn("GUI launcher smoke check:pass", launcher_details)
        self.assertIn("GUI launcher support bundle guidance:pass", launcher_details)
        self.assertIn("hidden GUI launcher target:pass", launcher_details)
        self.assertIn("hidden GUI launcher no console:pass", launcher_details)
        self.assertIn("hidden GUI launcher check mode:pass", launcher_details)
        self.assertIn("shortcut uses hidden launcher:pass", launcher_details)
        self.assertIn("shortcut icon:pass", launcher_details)
        self.assertNotIn("article check", product_details)
        self.assertNotIn("article review", product_details)

    def test_update_article_metadata_preserves_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article = create_article("旧タイトル", articles_dir=project / "articles", tags=["old"])
            original_body = load_article(article).body

            update_article_metadata(
                article,
                title="新タイトル",
                summary="概要です",
                tags=["note", "#自動化", "note"],
                cover="cover.png",
            )
            loaded = load_article(article)

            self.assertEqual(loaded.title, "新タイトル")
            self.assertEqual(loaded.summary, "概要です")
            self.assertEqual(loaded.tags, ["note", "自動化"])
            self.assertEqual(loaded.cover, "cover.png")
            self.assertEqual(loaded.body, original_body)

    def test_cleanup_generated_files_targets_old_helper_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            output_dir = project / ".auto-note"
            helper_dir = output_dir / "helpers"
            helper_dir.mkdir(parents=True)
            old_file = output_dir / "manual-post.html"
            nested_old_file = helper_dir / "post.html"
            keep_file = output_dir / "gui-error.log"
            old_file.write_text("old", encoding="utf-8")
            nested_old_file.write_text("old", encoding="utf-8")
            keep_file.write_text("keep", encoding="utf-8")
            old_time = (datetime.now() - timedelta(days=10)).timestamp()
            os.utime(old_file, (old_time, old_time))
            os.utime(nested_old_file, (old_time, old_time))

            preview = cleanup_generated_files(project, older_than_days=7, dry_run=True)
            report = format_cleanup_report(preview, dry_run=True)
            result = cleanup_generated_files(project, older_than_days=7, dry_run=False)

            self.assertEqual(len(preview.items), 2)
            self.assertIn("生成物整理: 削除候補 2件", report)
            self.assertEqual(result.deleted, 2)
            self.assertFalse(old_file.exists())
            self.assertFalse(nested_old_file.exists())
            self.assertTrue(keep_file.exists())

    def test_cleanup_generated_files_keeps_latest_reports_and_requires_release_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            diagnostics_dir = project / ".auto-note" / "diagnostics"
            support_dir = project / ".auto-note" / "support"
            sales_dir = project / ".auto-note" / "sales"
            reports_dir = project / ".auto-note" / "reports"
            releases_dir = project / ".auto-note" / "releases"
            for directory in (diagnostics_dir, support_dir, sales_dir, reports_dir, releases_dir):
                directory.mkdir(parents=True, exist_ok=True)
            old_time = (datetime.now() - timedelta(days=10)).timestamp()
            report_paths = [
                diagnostics_dir / f"auto-note-diagnostic-20260606-12000{index}.zip"
                for index in range(3)
            ]
            support_paths = [
                support_dir / f"auto-note-support-bundle-20260606-12000{index}.zip"
                for index in range(3)
            ]
            sales_paths = [
                sales_dir / f"auto-note-sales-handoff-20260606-12000{index}.zip"
                for index in range(3)
            ]
            sales_material_paths = [
                sales_dir / f"auto-note-sales-materials-20260606-12000{index}.md"
                for index in range(3)
            ]
            commercial_template_paths = [
                sales_dir / f"commercial-setup-template-20260606-12000{index}.md"
                for index in range(3)
            ]
            commercial_policy_review_paths = [
                sales_dir / f"commercial-policy-review-20260606-12000{index}.txt"
                for index in range(3)
            ]
            sales_finalize_paths = [
                sales_dir / f"sales-finalize-20260606-12000{index}.txt"
                for index in range(3)
            ]
            sales_plan_paths = [
                sales_dir / f"sales-plan-20260606-12000{index}.txt"
                for index in range(3)
            ]
            seller_checklist_paths = [
                sales_dir / f"seller-send-checklist-20260606-12000{index}.txt"
                for index in range(3)
            ]
            sales_evidence_manifest_paths = [
                sales_dir / f"sales-evidence-manifest-20260606-12000{index}.json"
                for index in range(3)
            ]
            csv_paths = [reports_dir / f"article-inventory-20260606-12000{index}.csv" for index in range(3)]
            acceptance_paths = [reports_dir / f"acceptance-20260606-12000{index}.txt" for index in range(3)]
            commercial_paths = [reports_dir / f"commercial-readiness-20260606-12000{index}.txt" for index in range(3)]
            release_paths = [releases_dir / f"auto-note-release-20260606-12000{index}.zip" for index in range(3)]
            for index, path in enumerate(
                [*report_paths, *support_paths, *csv_paths, *acceptance_paths, *commercial_paths, *release_paths]
                + sales_paths
                + sales_material_paths
                + commercial_template_paths
                + commercial_policy_review_paths
                + sales_plan_paths
                + sales_finalize_paths
                + seller_checklist_paths
                + sales_evidence_manifest_paths
            ):
                path.write_text(f"old {index}", encoding="utf-8")
                stamp = old_time + index
                os.utime(path, (stamp, stamp))

            preview = cleanup_generated_files(project, older_than_days=7, dry_run=True, keep_latest=1)
            result = cleanup_generated_files(project, older_than_days=7, dry_run=False, keep_latest=1)
            release_preview = cleanup_generated_files(
                project,
                older_than_days=7,
                dry_run=True,
                include_releases=True,
                keep_latest=1,
            )
            latest_report_kept = report_paths[-1].exists()
            latest_support_kept = support_paths[-1].exists()
            latest_sales_kept = sales_paths[-1].exists()
            latest_sales_materials_kept = sales_material_paths[-1].exists()
            latest_commercial_template_kept = commercial_template_paths[-1].exists()
            latest_commercial_policy_review_kept = commercial_policy_review_paths[-1].exists()
            latest_sales_plan_kept = sales_plan_paths[-1].exists()
            latest_sales_finalize_kept = sales_finalize_paths[-1].exists()
            latest_seller_checklist_kept = seller_checklist_paths[-1].exists()
            latest_sales_evidence_manifest_kept = sales_evidence_manifest_paths[-1].exists()
            latest_csv_kept = csv_paths[-1].exists()
            latest_acceptance_kept = acceptance_paths[-1].exists()
            latest_commercial_kept = commercial_paths[-1].exists()
            releases_kept = all(path.exists() for path in release_paths)

            self.assertEqual(len(preview.items), 26)
            self.assertTrue(all(item.reason != "release package ZIP" for item in preview.items))
            self.assertEqual(result.deleted, 26)
            self.assertEqual(len(release_preview.items), 2)
            self.assertTrue(all(item.reason == "release package ZIP" for item in release_preview.items))
            self.assertTrue(latest_report_kept)
            self.assertTrue(latest_support_kept)
            self.assertTrue(latest_sales_kept)
            self.assertTrue(latest_sales_materials_kept)
            self.assertTrue(latest_commercial_template_kept)
            self.assertTrue(latest_commercial_policy_review_kept)
            self.assertTrue(latest_sales_plan_kept)
            self.assertTrue(latest_sales_finalize_kept)
            self.assertTrue(latest_seller_checklist_kept)
            self.assertTrue(latest_sales_evidence_manifest_kept)
            self.assertTrue(latest_csv_kept)
            self.assertTrue(latest_acceptance_kept)
            self.assertTrue(latest_commercial_kept)
            self.assertTrue(releases_kept)

    def test_cleanup_can_target_privacy_failed_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article = create_article(
                "秘密の整理対象記事タイトル",
                articles_dir=project / "articles",
                tags=["note"],
                slug="private-cleanup-target-991",
            )
            diagnostics_dir = project / ".auto-note" / "diagnostics"
            support_dir = project / ".auto-note" / "support"
            diagnostics_dir.mkdir(parents=True)
            support_dir.mkdir(parents=True)
            leaked_diagnostic = diagnostics_dir / "auto-note-diagnostic-leak.zip"
            with zipfile.ZipFile(leaked_diagnostic, "w") as archive:
                archive.writestr("diagnostics.txt", f"path={project}\nfile={article.name}\n")
            leaked_request = support_dir / "support-request-leak.md"
            leaked_request.write_text(f"title=秘密の整理対象記事タイトル\n", encoding="utf-8")
            (project / "src" / "auto_note").mkdir(parents=True)
            (project / "src" / "auto_note" / "__init__.py").write_text("", encoding="utf-8")
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "pyproject.toml").write_text("[project]\nname='auto-note'\n", encoding="utf-8")
            (project / "README.md").write_text(f"title=秘密の整理対象記事タイトル\n", encoding="utf-8")
            release = create_release_package(project)

            preview = cleanup_generated_files(project, dry_run=True, privacy_failed=True)
            release_preview = cleanup_generated_files(
                project,
                dry_run=True,
                privacy_failed=True,
                include_releases=True,
            )
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(
                    [
                        "cleanup",
                        "--project-dir",
                        str(project),
                        "--privacy-failed",
                        "--include-releases",
                    ]
                )
            readiness = run_readiness(project)
            readiness_text = format_readiness_report(readiness)
            result = cleanup_generated_files(project, dry_run=False, privacy_failed=True, include_releases=True)
            diagnostic_deleted = not leaked_diagnostic.exists()
            request_deleted = not leaked_request.exists()
            release_deleted = not release.exists()

        preview_paths = {item.path.name for item in preview.items}
        release_preview_paths = {item.path.name for item in release_preview.items}
        self.assertIn(leaked_diagnostic.name, preview_paths)
        self.assertIn(leaked_request.name, preview_paths)
        self.assertNotIn(release.name, preview_paths)
        self.assertIn(release.name, release_preview_paths)
        self.assertTrue(all("privacy audit NG" in item.reason for item in release_preview.items))
        self.assertEqual(code, 0)
        self.assertIn("privacy audit NG", cli_output.getvalue())
        self.assertTrue(any(item.name == "privacy cleanup" and item.status == "info" for item in readiness.items))
        self.assertIn("privacy cleanup", readiness_text)
        self.assertEqual(result.deleted, 3)
        self.assertTrue(diagnostic_deleted)
        self.assertTrue(request_deleted)
        self.assertTrue(release_deleted)

    def test_export_article_inventory_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            create_article("CSV記事", articles_dir=project / "articles", tags=["note"])
            report = export_article_inventory(project)
            text = report.read_text(encoding="utf-8-sig")

        self.assertIn("title,status,scheduled", text)
        self.assertIn("CSV記事", text)

    def test_setup_check_can_create_basic_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            items = run_setup_check(project, create=True)
            report = format_setup_report(items)

            self.assertTrue((project / "articles").exists())
            self.assertTrue((project / ".auto-note" / "settings.json").exists())
            self.assertIn("セットアップ確認", report)

    def test_practice_article_is_ready_for_first_run_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            path = create_practice_article(articles_dir=project / "articles")
            article = load_article(path)
            inspection = inspect_article(article, append_tags=True)
            review = review_article(article, append_tags=True)
            helper = write_manual_post_helper(
                article,
                append_tags=True,
                output_dir=project / ".auto-note" / "practice-test",
            )
            helper_exists = helper.exists()
            text = path.read_text(encoding="utf-8")

        self.assertTrue(path.name.endswith("auto-note-practice.md"))
        self.assertFalse(inspection.issues)
        self.assertGreaterEqual(review.score, 80)
        self.assertTrue(review.ready)
        self.assertTrue(helper_exists)
        self.assertNotIn("ここに", text)
        self.assertNotIn("TODO", text)

    def test_starter_pack_creates_demo_ready_project_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            result = create_starter_pack(project)
            second = create_starter_pack(project, include_calendar=False)
            created_exists = all(path.exists() for path in result.articles)
            articles = [load_article(path) for path in result.articles]
            reviews = [review_article(article) for article in articles]
            ideas = load_ideas(project)
            calendar_text = result.calendar_path.read_text(encoding="utf-8") if result.calendar_path else ""
            report_text = format_starter_pack_result(result)
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["starter-pack", "--project-dir", str(project), "--no-calendar"])
            privacy = run_privacy_audit(project)
            statuses = {article.status for article in articles}
            has_schedule = any(article.scheduled for article in articles)
            scores = [review.score for review in reviews]
            needs_fix = any(review.needs_fix for review in reviews)
            has_idea = any(idea.title == result.idea_title for idea in ideas)
            scheduled_title = next(article.title for article in articles if article.status == "scheduled")

        self.assertEqual(len(result.articles), 3)
        self.assertEqual(len(result.skipped_articles), 0)
        self.assertEqual(len(second.articles), 0)
        self.assertEqual(len(second.skipped_articles), 3)
        self.assertTrue(created_exists)
        self.assertEqual(statuses, {"ready", "scheduled", "draft"})
        self.assertTrue(has_schedule)
        self.assertTrue(all(score >= 85 for score in scores))
        self.assertFalse(needs_fix)
        self.assertTrue(has_idea)
        self.assertTrue(result.idea_added)
        self.assertFalse(second.idea_added)
        self.assertIsNotNone(result.calendar_path)
        self.assertEqual(result.calendar_events, 1)
        self.assertIn("BEGIN:VCALENDAR", calendar_text)
        self.assertIn("SUMMARY:note投稿予定 001", calendar_text)
        self.assertNotIn(scheduled_title, calendar_text)
        self.assertIn("Starter pack / スターター一式", report_text)
        self.assertIn("3 created, 0 already present", report_text)
        self.assertEqual(code, 0)
        self.assertIn("Starter pack / スターター一式", cli_output.getvalue())
        self.assertIn("0 created, 3 already present", cli_output.getvalue())
        self.assertFalse(has_privacy_audit_blockers(privacy))

    def test_starter_clean_previews_and_removes_only_starter_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            keep_path = create_article("通常の記事", articles_dir=project / "articles", tags=["note"])
            create_starter_pack(project, include_calendar=False)

            preview = cleanup_starter_pack(project)
            preview_text = format_starter_cleanup_result(preview)
            still_exists_after_preview = all(path.exists() for path in preview.articles)
            cli_preview = io.StringIO()
            with redirect_stdout(cli_preview):
                preview_code = cli_main(["starter-clean", "--project-dir", str(project)])
            cli_apply = io.StringIO()
            with redirect_stdout(cli_apply):
                apply_code = cli_main(["starter-clean", "--project-dir", str(project), "--apply"])
            remaining_articles = sorted((project / "articles").glob("*.md"))
            remaining_ideas = load_ideas(project)

        self.assertEqual(len(preview.articles), 3)
        self.assertTrue(preview.idea_matched)
        self.assertTrue(still_exists_after_preview)
        self.assertIn("Starter cleanup / スターター整理 (Preview)", preview_text)
        self.assertEqual(preview_code, 0)
        self.assertIn("would be removed", cli_preview.getvalue())
        self.assertEqual(apply_code, 0)
        self.assertIn("removed", cli_apply.getvalue())
        self.assertEqual(remaining_articles, [keep_path])
        self.assertEqual(remaining_ideas, [])

    def test_readiness_report_scores_and_lists_next_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            create_article("準備度記事", articles_dir=project / "articles", tags=["note"])
            backup = create_backup(project)

            report = run_readiness(project)
            text = format_readiness_report(report)

            self.assertGreaterEqual(report.score, 0)
            self.assertLessEqual(report.score, 100)
            self.assertTrue(any(item.name == "latest backup" and item.status == "pass" for item in report.items))
            self.assertTrue(any(item.name == "privacy cleanup" and item.status == "pass" for item in report.items))
            self.assertIn(backup.name, text)
            self.assertIn("privacy cleanup", text)
        self.assertIn("Readiness report", text)
        self.assertIn("Score:", text)

    def test_repair_previews_and_applies_safe_setup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            preview = run_repair(project)
            preview_text = format_repair_report(preview)
            created_during_preview = (project / "articles").exists() or (project / ".auto-note" / "settings.json").exists()
            applied = run_repair(project, apply=True)
            applied_text = format_repair_report(applied)
            articles_exists = (project / "articles").exists()
            settings_exists = (project / ".auto-note" / "settings.json").exists()
            ideas_exists = (project / ".auto-note" / "ideas.json").exists()
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["repair", "--project-dir", str(project)])

        self.assertFalse(created_during_preview)
        self.assertFalse(has_repair_blockers(preview))
        self.assertEqual(preview.applied, False)
        self.assertIn("Repair report / 自動修復", preview_text)
        self.assertIn("Mode: PREVIEW", preview_text)
        self.assertEqual(applied.applied, True)
        self.assertTrue(articles_exists)
        self.assertTrue(settings_exists)
        self.assertTrue(ideas_exists)
        self.assertIn("Mode: APPLY", applied_text)
        self.assertEqual(code, 0)
        self.assertIn("Repair report / 自動修復", cli_output.getvalue())

    def test_repair_privacy_cleanup_summarizes_release_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            release_dir = project / ".auto-note" / "releases"
            release_dir.mkdir(parents=True)
            package = release_dir / "auto-note-release-20990101-000000.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("README.md", "unsafe placeholder")

            report = run_repair(project, cleanup_privacy=True, include_releases=True)
            text = format_repair_report(report)
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["repair", "--project-dir", str(project), "--cleanup-privacy", "--include-releases"])

        self.assertEqual(code, 0)
        self.assertIn("privacy-failed cleanup candidate(s)", text)
        self.assertIn("release 1", text)
        self.assertIn("--cleanup-privacy --include-releases --apply", text)
        self.assertIn("release 1", cli_output.getvalue())
        self.assertIn("--cleanup-privacy --include-releases --apply", cli_output.getvalue())

    def test_troubleshoot_summarizes_gui_log_and_login_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            run_setup_check(project, create=True)
            append_gui_error(
                project,
                "GUI startup",
                f"Traceback (most recent call last):\nOSError: [WinError 123] bad path: {project}\n",
            )

            report = run_troubleshoot(project)
            text = format_troubleshoot_report(report)
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["troubleshoot", "--project-dir", str(project)])

        self.assertEqual(code, 0)
        self.assertFalse(has_troubleshoot_blockers(report))
        self.assertEqual(report.status, "warn")
        self.assertIn("Troubleshooting report / トラブル診断", text)
        self.assertIn("[WARN] GUI log", text)
        self.assertIn("Traceback", text)
        self.assertIn("note login", text)
        self.assertIn("auto-note login --default-browser", text)
        self.assertNotIn(str(project), text)
        self.assertIn("Troubleshooting report / トラブル診断", cli_output.getvalue())

    def test_article_review_scores_and_suggests_next_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article_path = project / "articles" / "review.md"
            article_path.parent.mkdir(parents=True)
            article_path.write_text(
                """---
title: "読者に届くnote記事を仕上げるための実践チェック"
summary: "公開前に見落としやすい構成、導入、締め、タグを確認し、読者に届く記事へ整える手順をまとめます。"
tags:
  - note
  - 文章術
  - 発信
status: ready
publish: false
---

この記事では、公開前のnote記事を短時間で整えるための見直し手順を紹介します。書いたあとに何を確認すればよいか迷う人が、本文を読み返しながら使える形にしています。

## 読者の約束を先に置く

記事の冒頭では、誰が何を得られるのかを先に示します。たとえば、経験談を書く場合でも、単なる出来事ではなく、読者が自分の仕事や生活に持ち帰れる視点を明らかにします。これだけで読み始める理由ができます。

## 本文に具体例を入れる

本文では、抽象的な主張だけで終わらせず、実際に使った場面、うまくいかなかった場面、改善したあとに変わったことを入れます。具体例があると、読者は自分の状況に置き換えて読みやすくなります。

## 公開前に整える

最後に、タイトル、概要、タグ、画像、公開状態を確認します。読み終えた人が次に何を試せばいいかを一文で残すと、記事の余韻が行動につながります。まずは今回の記事に、読者への質問を一つ足してみてください。
""",
                encoding="utf-8",
            )

            review = review_article(load_article(article_path))
            text = format_review_report([review])

        self.assertGreaterEqual(review.score, 80)
        self.assertTrue(review.ready)
        self.assertFalse(has_review_blockers([review]))
        self.assertIn("Article review", text)
        self.assertIn("[OK] 構成", text)

    def test_article_review_flags_unfinished_articles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            articles = project / "articles"
            articles.mkdir(parents=True)
            article = articles / "unfinished.md"
            article.write_text(
                """---
title: 仮タイトル
tags: []
status: draft
publish: false
---

ここに本文を書きます。
""",
                encoding="utf-8",
            )
            reviews = review_path(project / "articles")
            text = format_review_report(reviews)

        self.assertTrue(has_review_blockers(reviews))
        self.assertIn("[FIX] タイトル", text)
        self.assertIn("[FIX] 本文", text)
        self.assertIn("[FIX] タグ", text)
        self.assertLess(reviews[0].score, 80)

    def test_publish_ready_report_checks_one_article_and_can_mark_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            articles = project / "articles"
            articles.mkdir(parents=True)
            article_path = articles / "ready.md"
            article_path.write_text(
                """---
title: 公開前チェックで記事を整える具体手順
summary: 公開前に確認すべきタイトル、本文、タグ、導入、締めを短時間で整えるための実践手順です。
tags:
  - note
  - 執筆
  - チェックリスト
status: ready
publish: false
---

この記事では、公開前のnote記事を短時間で整えるための見直し手順を紹介します。書いたあとに何を確認すればよいか迷う人が、本文を読み返しながら使える形にしています。

## 読者の約束を先に置く

記事の冒頭では、誰が何を得られるのかを先に示します。たとえば、経験談を書く場合でも、単なる出来事ではなく、読者が自分の仕事や生活に持ち帰れる視点を明らかにします。これだけで読み始める理由ができます。

## 本文に具体例を入れる

本文では、抽象的な主張だけで終わらせず、実際に使った場面、うまくいかなかった場面、改善したあとに変わったことを入れます。具体例があると、読者は自分の状況に置き換えて読みやすくなります。

## 公開前に整える

最後に、タイトル、概要、タグ、画像、公開状態を確認します。読み終えた人が次に何を試せばいいかを一文で残すと、記事の余韻が行動につながります。まずは今回の記事に、読者への質問を一つ足してみてください。
""",
                encoding="utf-8",
            )

            report = run_publish_ready(
                article_path,
                smoke_helper=True,
                output_dir=project / ".auto-note" / "publish-ready",
            )
            text = format_publish_ready_report(report)
            helper_exists = bool(report.helper_path and report.helper_path.exists())
            draft = article_path.read_text(encoding="utf-8").replace("status: ready", "status: draft")
            article_path.write_text(draft, encoding="utf-8")
            marked = run_publish_ready(article_path, mark_ready=True)
            reloaded = load_article(article_path)

        self.assertFalse(has_publish_ready_blockers(report))
        self.assertEqual(report.status, "pass")
        self.assertTrue(helper_exists)
        self.assertIn("Verdict: READY TO POST", text)
        self.assertTrue(marked.marked_ready)
        self.assertEqual(reloaded.status, "ready")

    def test_publish_ready_report_blocks_unfinished_articles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article = create_article("仮タイトル", articles_dir=project / "articles", tags=[])
            text = article.read_text(encoding="utf-8")
            article.write_text(text + "\nTODO\n![missing](missing.png)\n", encoding="utf-8")

            report = run_publish_ready(article, mark_ready=True)
            rendered = format_publish_ready_report(report)

        self.assertTrue(has_publish_ready_blockers(report))
        self.assertEqual(report.status, "fail")
        self.assertFalse(report.marked_ready)
        self.assertIn("Verdict: BLOCKED", rendered)
        self.assertIn("[NG] mark ready", rendered)

    def test_improvement_plan_prioritizes_article_fixes_and_saves_private_safe_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            article = create_article(
                "秘密の改善対象タイトル",
                articles_dir=project / "articles",
                tags=[],
                slug="private-improvement-target-991",
            )
            text = article.read_text(encoding="utf-8")
            article.write_text(text + "\nTODO\n![missing](missing.png)\n", encoding="utf-8")

            plan = build_improvement_plan(article, append_tags=True, limit=6)
            rendered = format_improvement_plan(plan)
            public = format_improvement_plan(plan, include_private=False)
            saved = write_improvement_plan_report(project, plan=plan)
            saved_text = saved.read_text(encoding="utf-8")
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["improve", str(article), "--project-dir", str(project), "--report"])
            privacy = run_privacy_audit(project)

        self.assertTrue(has_improvement_plan_blockers(plan))
        self.assertEqual(plan.status, "blocked")
        self.assertIn("Improvement plan / 改善プラン", rendered)
        self.assertIn("[FIX] 必須修正", rendered)
        self.assertIn("タイトル", rendered)
        self.assertIn("本文", rendered)
        self.assertIn("タグ", rendered)
        self.assertIn("<article>.md", public)
        self.assertNotIn("秘密の改善対象タイトル", saved_text)
        self.assertNotIn(article.name, saved_text)
        self.assertEqual(code, 1)
        self.assertIn("improvement plan report created", cli_output.getvalue())
        self.assertFalse(has_privacy_audit_blockers(privacy))

    def test_overview_summarizes_daily_operations_and_saves_private_safe_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            ready = create_practice_article(articles_dir=project / "articles")
            set_article_status(ready, "ready")
            overdue = create_article(
                "秘密の遅延予定記事タイトル",
                articles_dir=project / "articles",
                tags=["note"],
                slug="private-overdue-overview-991",
            )
            set_article_schedule(overdue, (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"))
            stale = create_article(
                "秘密の古い下書きタイトル",
                articles_dir=project / "articles",
                tags=["note"],
                slug="private-stale-overview-991",
            )
            old_time = (datetime.now() - timedelta(days=20)).timestamp()
            os.utime(stale, (old_time, old_time))
            published = create_article(
                "秘密の公開済みURLなしタイトル",
                articles_dir=project / "articles",
                tags=["note"],
                slug="private-published-overview-991",
            )
            mark_article_published(published)

            report = build_overview(project, stale_days=7)
            text = format_overview_report(report)
            public_text = format_overview_report(report, include_private=False)
            saved = write_overview_report(project, report=report)
            saved_text = saved.read_text(encoding="utf-8")
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["overview", "--project-dir", str(project), "--stale-days", "7", "--report"])
            privacy = run_privacy_audit(project)

        self.assertEqual(report.status, "check")
        self.assertFalse(has_overview_blockers(report))
        self.assertIn("Overview / 運用サマリー", text)
        self.assertIn("[OK] next publish", text)
        self.assertIn("[WARN] schedule", text)
        self.assertIn("[WARN] stale drafts", text)
        self.assertIn("[WARN] published URLs", text)
        self.assertIn("<article>.md", public_text)
        self.assertIn("<title:", public_text)
        self.assertNotIn("秘密", saved_text)
        self.assertNotIn(stale.name, saved_text)
        self.assertEqual(code, 0)
        self.assertIn("overview report created", cli_output.getvalue())
        self.assertFalse(has_privacy_audit_blockers(privacy))

    def test_calendar_export_writes_ics_and_defaults_to_privacy_safe_titles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            scheduled = create_article(
                "秘密の予定記事タイトル",
                articles_dir=project / "articles",
                tags=["note"],
                slug="private-calendar-export-991",
            )
            set_article_schedule(scheduled, (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"))

            result = export_calendar(project, project / "articles", days=30)
            text = result.path.read_text(encoding="utf-8")
            public_calendar = format_calendar(project / "articles", days=30, include_private=False)
            safe_privacy = run_privacy_audit(project)
            private_result = export_calendar(project, project / "articles", days=30, include_private=True)
            private_text = private_result.path.read_text(encoding="utf-8")
            private_unfolded = private_text.replace("\n ", "")
            private_privacy = run_privacy_audit(project)
            formatted = format_calendar_export(result)
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["calendar-export", "--project-dir", str(project), "--days", "30"])
            exports = list_calendar_exports(project)

        self.assertEqual(result.event_count, 1)
        self.assertIn("BEGIN:VCALENDAR", text)
        self.assertIn("BEGIN:VEVENT", text)
        self.assertIn("SUMMARY:note投稿予定 001", text)
        self.assertNotIn("秘密", text)
        self.assertNotIn(scheduled.name, text)
        self.assertIn("article-001.md", public_calendar)
        self.assertNotIn("秘密", public_calendar)
        self.assertIn("秘密の予定記事タイトル", private_text)
        self.assertIn(scheduled.name, private_unfolded)
        self.assertTrue(has_privacy_audit_blockers(private_privacy))
        self.assertFalse(has_privacy_audit_blockers(safe_privacy))
        self.assertIn("Calendar export / 予定ICS", formatted)
        self.assertIn("privacy-safe titles", formatted)
        self.assertEqual(code, 0)
        self.assertIn("Calendar export / 予定ICS", cli_output.getvalue())
        self.assertTrue(exports)

    def test_publish_queue_orders_articles_and_saves_privacy_safe_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            ready = create_practice_article(articles_dir=project / "articles")
            set_article_status(ready, "ready")
            blocked = create_article("仮タイトル", articles_dir=project / "articles", tags=[])
            blocked_text = blocked.read_text(encoding="utf-8")
            blocked.write_text(blocked_text + "\nTODO\n![missing](missing.png)\n", encoding="utf-8")
            ready_title = load_article(ready).title

            report = build_publish_queue(project, append_tags=True)
            text = format_publish_queue_report(report)
            public_text = format_publish_queue_report(report, include_private=False)
            saved = write_publish_queue_report(project, report=report)
            saved_text = saved.read_text(encoding="utf-8")
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["publish-queue", "--project-dir", str(project), "--report"])
            privacy = run_privacy_audit(project)

        self.assertTrue(has_publish_queue_blockers(report))
        self.assertGreaterEqual(report.ready_count, 1)
        self.assertGreaterEqual(report.blocked_count, 1)
        self.assertEqual(report.entries[0].readiness, "postable")
        self.assertIn("Publish queue / 投稿キュー", text)
        self.assertIn("[POSTABLE]", text)
        self.assertIn("[BLOCKED]", text)
        self.assertIn("article-001.md", public_text)
        self.assertNotIn(ready_title, saved_text)
        self.assertNotIn(blocked.name, saved_text)
        self.assertEqual(code, 1)
        self.assertIn("publish queue report created", cli_output.getvalue())
        self.assertFalse(has_privacy_audit_blockers(privacy))

    def test_preflight_report_summarizes_release_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            create_article("出荷前チェック記事", articles_dir=project / "articles", tags=["note"])

            report = run_preflight(project, create_release=True)
            text = format_preflight_report(report)
            created_exists = bool(report.created_release and report.created_release.exists())

        self.assertTrue(created_exists)
        self.assertIn("Preflight report", text)
        self.assertIn("Verdict:", text)
        self.assertIn("action plan", text)
        self.assertIn("troubleshoot", text)
        self.assertIn("created release", text)
        self.assertTrue(has_preflight_blockers(report))

    def test_preflight_can_ignore_stale_sales_handoffs_for_regeneration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            run_setup_check(project, create=True)
            sales_dir = project / ".auto-note" / "sales"
            sales_dir.mkdir(parents=True)
            stale = sales_dir / "auto-note-sales-handoff-20260607-000000.zip"
            with zipfile.ZipFile(stale, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("SALES_MATERIALS.md", "# old sales materials\n")

            strict_report = run_preflight(project)
            ignored_report = run_preflight(project, include_sales_handoffs=False)

        strict_items = {item.name: item for item in strict_report.items}
        ignored_items = {item.name: item for item in ignored_report.items}
        self.assertEqual(strict_items["privacy audit"].status, "fail")
        self.assertEqual(strict_items["troubleshoot"].status, "fail")
        self.assertNotEqual(ignored_items["privacy audit"].status, "fail")
        self.assertNotEqual(ignored_items["troubleshoot"].status, "fail")

    def test_preflight_surfaces_action_plan_without_blocking_info(self) -> None:
        report = PreflightReport(
            project_dir=Path.cwd(),
            status="pass",
            readiness_score=100,
            items=[
                PreflightItem("readiness", "pass", "100/100"),
                PreflightItem("action plan", "info", "NEEDS ATTENTION, top: 記事レビューで仕上げる"),
                PreflightItem("article review", "info", "average 40/100, 1 article(s) need fixes"),
            ],
        )
        text = format_preflight_report(report)

        self.assertFalse(report.has_warnings)
        self.assertFalse(has_preflight_blockers(report, strict=True))
        self.assertIn("2 INFO", text)
        self.assertIn("[INFO] action plan", text)

    def test_preflight_info_items_do_not_block_or_warn(self) -> None:
        report = PreflightReport(
            project_dir=Path.cwd(),
            status="pass",
            readiness_score=100,
            items=[
                PreflightItem("readiness", "pass", "100/100"),
                PreflightItem("article review", "info", "average 40/100, 1 article(s) need fixes"),
            ],
        )
        text = format_preflight_report(report)

        self.assertFalse(report.has_warnings)
        self.assertFalse(has_preflight_blockers(report, strict=True))
        self.assertIn("Verdict: READY", text)
        self.assertIn("1 INFO", text)
        self.assertIn("[INFO] article review", text)

    def test_preflight_install_smoke_reports_missing_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            report = run_preflight(project, install_smoke=True)
            text = format_preflight_report(report)

        self.assertTrue(has_preflight_blockers(report))
        self.assertIn("[NG] install smoke", text)
        self.assertIn("script not found", text)

    def test_release_package_excludes_user_articles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "src" / "auto_note").mkdir(parents=True)
            (project / "scripts").mkdir()
            (project / "shortcuts").mkdir()
            (project / "docs").mkdir()
            (project / "src" / "auto_note" / "__init__.py").write_text("", encoding="utf-8")
            (project / "scripts" / "ensure-env.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "scripts" / "install-auto-note.ps1").write_text("Write-Host install\n", encoding="utf-8")
            (project / "scripts" / "uninstall-auto-note.ps1").write_text("Write-Host uninstall\n", encoding="utf-8")
            (project / "scripts" / "smoke-install.ps1").write_text("Write-Host smoke\n", encoding="utf-8")
            (project / "shortcuts" / "install-auto-note.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "shortcuts" / "uninstall-auto-note.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "docs" / "PRODUCT_READINESS.md").write_text("ready\n", encoding="utf-8")
            (project / "docs" / "INSTALL.md").write_text("install\n", encoding="utf-8")
            (project / "docs" / "UPDATE.md").write_text("update\n", encoding="utf-8")
            (project / "docs" / "SUPPORT.md").write_text("support\n", encoding="utf-8")
            (project / "docs" / "TERMS_DRAFT.md").write_text("terms\n", encoding="utf-8")
            (project / "docs" / "COMMERCIAL_POLICY_DRAFT.md").write_text("commercial\n", encoding="utf-8")
            (project / "docs" / "THIRD_PARTY_NOTICES.md").write_text("notices\n", encoding="utf-8")
            (project / "auto-note-gui.bat").write_text("@echo off\n", encoding="utf-8")
            (project / "README.md").write_text("readme\n", encoding="utf-8")
            (project / "pyproject.toml").write_text("[project]\nname='auto-note'\n", encoding="utf-8")
            article_path = create_article("秘密の記事", articles_dir=project / "articles", tags=["private"])

            package = create_release_package(project)

            self.assertTrue(package.exists())
            with zipfile.ZipFile(package) as archive:
                names = set(archive.namelist())
            self.assertIn("README.md", names)
            self.assertIn("scripts/ensure-env.bat", names)
            self.assertIn("scripts/install-auto-note.ps1", names)
            self.assertIn("scripts/uninstall-auto-note.ps1", names)
            self.assertIn("scripts/smoke-install.ps1", names)
            self.assertIn("shortcuts/install-auto-note.bat", names)
            self.assertIn("shortcuts/uninstall-auto-note.bat", names)
            self.assertIn("articles/.keep", names)
            self.assertIn("RELEASE_MANIFEST.json", names)
            self.assertIn("CHECKSUMS.txt", names)
            self.assertIn("START_HERE.txt", names)
            self.assertIn("FIRST_RUN_CHECKLIST.txt", names)
            self.assertIn("BUYER_ACCEPTANCE_CHECKLIST.txt", names)
            self.assertIn("RELEASE_SUMMARY.txt", names)
            self.assertIn("docs/SUPPORT.md", names)
            self.assertIn("docs/UPDATE.md", names)
            self.assertIn("docs/TERMS_DRAFT.md", names)
            self.assertIn("docs/COMMERCIAL_POLICY_DRAFT.md", names)
            self.assertIn("docs/THIRD_PARTY_NOTICES.md", names)
            self.assertNotIn(f"articles/{article_path.name}", names)
            with zipfile.ZipFile(package) as archive:
                manifest = archive.read("RELEASE_MANIFEST.json").decode("utf-8")
                checksums = archive.read("CHECKSUMS.txt").decode("utf-8")
                start_here = archive.read("START_HERE.txt").decode("utf-8")
                first_run = archive.read("FIRST_RUN_CHECKLIST.txt").decode("utf-8")
                buyer_acceptance = archive.read("BUYER_ACCEPTANCE_CHECKLIST.txt").decode("utf-8")
                release_summary = archive.read("RELEASE_SUMMARY.txt").decode("utf-8")
            verification_text = format_release_verification(package, verify_release_package(package))
            self.assertIn('"includes_user_articles": false', manifest)
            self.assertIn("README.md", checksums)
            self.assertIn("shortcuts\\install-auto-note.bat", start_here)
            self.assertIn("shortcuts\\uninstall-auto-note.bat", start_here)
            self.assertIn("出荷ZIP作成", start_here)
            self.assertIn("FIRST_RUN_CHECKLIST.txt", start_here)
            self.assertIn("BUYER_ACCEPTANCE_CHECKLIST.txt", start_here)
            self.assertIn("RELEASE_SUMMARY.txt", start_here)
            self.assertIn("CHECKSUMS.txt", start_here)
            self.assertIn("auto-note troubleshoot --project-dir .", start_here)
            self.assertIn("auto-note acceptance --project-dir . --full", start_here)
            self.assertIn("auto-note acceptance --project-dir . --full", first_run)
            self.assertIn("auto-note first-run --project-dir . --create --gui-smoke --smoke-helper", first_run)
            self.assertIn("auto-note self-test --project-dir . --create --gui-smoke --report", first_run)
            self.assertIn("auto-note troubleshoot --project-dir .", first_run)
            self.assertIn("auto-note acceptance --project-dir . --full", buyer_acceptance)
            self.assertIn("受入チェック", buyer_acceptance)
            self.assertIn("初回チェック", first_run)
            self.assertIn("セルフテスト保存", first_run)
            self.assertIn("auto-note action-plan --project-dir .", first_run)
            self.assertIn("問い合わせ一式", first_run)
            self.assertIn("User articles are not included.", release_summary)
            self.assertIn("FIRST_RUN_CHECKLIST.txt", release_summary)
            self.assertIn("BUYER_ACCEPTANCE_CHECKLIST.txt", release_summary)
            self.assertIn("CHECKSUMS.txt", release_summary)
            self.assertIn("Package summary", verification_text)
            self.assertIn("first run: START_HERE.txt, FIRST_RUN_CHECKLIST.txt, BUYER_ACCEPTANCE_CHECKLIST.txt", verification_text)
            self.assertEqual(verify_release_package(package), [])

    def test_release_verify_rejects_private_and_unsafe_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "unsafe-release.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr(
                    "RELEASE_MANIFEST.json",
                    """{
  "privacy": {
    "includes_user_articles": true,
    "includes_generated_helpers": true,
    "includes_virtualenv": true
  },
  "entrypoint": "auto-note-gui.bat",
  "file_count": 0,
  "files": []
}
""",
                )
                archive.writestr("CHECKSUMS.txt", "")
                archive.writestr("START_HERE.txt", "")
                archive.writestr("RELEASE_SUMMARY.txt", "")
                archive.writestr("auto-note-gui.bat", "")
                archive.writestr("articles/.keep", "")
                archive.writestr("articles/private.md", "secret")
                archive.writestr(".auto-note/settings.json", "{}")
                archive.writestr(".venv/pyvenv.cfg", "")
                archive.writestr("desktop.lnk", "")
                archive.writestr("../evil.txt", "")

            errors = verify_release_package(package)
            text = "\n".join(errors)

        self.assertIn("user article must not be included", text)
        self.assertIn("excluded path must not be included", text)
        self.assertIn("excluded file suffix must not be included", text)
        self.assertIn("unsafe archive path", text)
        self.assertIn("manifest privacy flag must be false: includes_user_articles", text)
        self.assertIn("manifest privacy flag must be false: includes_generated_helpers", text)
        self.assertIn("manifest privacy flag must be false: includes_virtualenv", text)

    def test_release_verify_reports_unreadable_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "broken-release.zip"
            package.write_text("not a zip yet", encoding="utf-8")
            errors = verify_release_package(package)
            cli_output = io.StringIO()
            with redirect_stdout(cli_output):
                code = cli_main(["release", "--verify", str(package)])

        error_text = "\n".join(errors)
        output = cli_output.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("unreadable package", error_text)
        self.assertIn("unreadable package", output)


def _write_and_load(text: str):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "article.md"
        path.write_text(text, encoding="utf-8")
        return load_article(path)


def _png_bytes(*, width: int, height: int) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\r"
        + b"IHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )


if __name__ == "__main__":
    unittest.main()
