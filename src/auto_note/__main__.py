from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import asyncio
import os
import sys
import time
import webbrowser

from .article import ArticleError, body_with_tags, hashtags_for, load_article, text_bundle, write_text_atomic


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "login":
            if args.default_browser:
                from .manual import open_note_login

                open_note_login()
            else:
                browser = _load_browser()
                options = _browser_options(args)
                asyncio.run(browser.open_login(options))
            return 0

        if args.command == "manual":
            from .manual import open_manual_post_helper

            article = load_article(args.file)
            path = open_manual_post_helper(
                article,
                append_tags=args.append_tags,
                output_dir=args.output_dir.expanduser(),
                open_note=not args.no_open_note,
                open_helper=not args.write_only,
            )
            print(f"opened helper: {path}")
            return 0

        if args.command == "dashboard":
            from .manual import open_manual_dashboard

            path = open_manual_dashboard(
                args.path,
                pattern=args.glob,
                append_tags=args.append_tags,
                output_dir=args.output_dir.expanduser(),
                open_note=args.open_note,
                open_dashboard=not args.write_only,
            )
            print(f"opened dashboard: {path}")
            return 0

        if args.command == "new":
            from .scaffold import create_article, list_article_templates

            if args.list_templates:
                for key, label in list_article_templates():
                    print(f"{key}: {label}")
                return 0
            if not args.title:
                raise ArticleError("new には記事タイトルが必要です。")

            path = create_article(
                args.title,
                articles_dir=args.dir,
                tags=args.tags or [],
                slug=args.slug,
                force=args.force,
                template=args.template,
            )
            print(f"created: {path}")
            if args.open:
                _open_path(path)
            return 0

        if args.command == "practice":
            from .scaffold import create_practice_article

            articles_dir = args.dir if args.dir.is_absolute() else args.project_dir.resolve() / args.dir
            path = create_practice_article(articles_dir=articles_dir, force=args.force)
            print(f"created practice article: {path}")
            if args.open:
                _open_path(path)
            return 0

        if args.command == "starter-pack":
            from .starter import create_starter_pack, format_starter_pack_result

            articles_dir = args.dir if args.dir.is_absolute() else args.project_dir.resolve() / args.dir
            result = create_starter_pack(
                args.project_dir.resolve(),
                articles_dir=articles_dir,
                include_calendar=not args.no_calendar,
            )
            print(format_starter_pack_result(result))
            if args.open_folder:
                _open_path(articles_dir)
            return 0

        if args.command == "starter-clean":
            from .starter import cleanup_starter_pack, format_starter_cleanup_result

            articles_dir = args.dir if args.dir.is_absolute() else args.project_dir.resolve() / args.dir
            result = cleanup_starter_pack(
                args.project_dir.resolve(),
                articles_dir=articles_dir,
                dry_run=not args.apply,
            )
            print(format_starter_cleanup_result(result))
            return 0

        if args.command == "check":
            from .inspect import format_reports, inspect_path

            reports = inspect_path(args.path, pattern=args.glob, append_tags=args.append_tags)
            print(format_reports(reports))
            has_error = any(not report.ok for report in reports)
            has_warning = any(issue.level == "warn" for report in reports for issue in report.issues)
            if has_error or (args.strict and has_warning):
                return 1
            return 0

        if args.command == "review":
            from .review import format_review_report, has_review_blockers, review_path

            reviews = review_path(args.path, pattern=args.glob, append_tags=args.append_tags)
            print(format_review_report(reviews))
            return 1 if has_review_blockers(reviews, strict=args.strict) else 0

        if args.command == "publish-ready":
            from .publish_ready import (
                format_publish_ready_report,
                has_publish_ready_blockers,
                run_publish_ready,
            )

            report = run_publish_ready(
                args.file,
                append_tags=args.append_tags,
                smoke_helper=args.smoke_helper,
                output_dir=args.output_dir or args.project_dir.resolve() / ".auto-note" / "publish-ready",
                mark_ready=args.mark_ready,
            )
            print(format_publish_ready_report(report))
            return 1 if has_publish_ready_blockers(report, strict=args.strict) else 0

        if args.command == "improve":
            from .improvement_plan import (
                build_improvement_plan,
                format_improvement_plan,
                has_improvement_plan_blockers,
                write_improvement_plan_report,
            )

            plan = build_improvement_plan(
                args.file,
                append_tags=args.append_tags,
                limit=args.limit,
            )
            print(format_improvement_plan(plan, include_private=not args.public))
            if args.report:
                path = write_improvement_plan_report(
                    args.project_dir.resolve(),
                    plan=plan,
                    include_private=args.include_private_report,
                )
                print()
                print(f"improvement plan report created: {path}")
            return 1 if has_improvement_plan_blockers(plan, strict=args.strict) else 0

        if args.command == "publish-queue":
            from .publish_queue import (
                build_publish_queue,
                format_publish_queue_report,
                has_publish_queue_blockers,
                write_publish_queue_report,
            )

            report = build_publish_queue(
                args.project_dir.resolve(),
                pattern=args.glob,
                append_tags=args.append_tags,
            )
            print(format_publish_queue_report(report, include_private=not args.public))
            if args.report:
                path = write_publish_queue_report(
                    args.project_dir.resolve(),
                    report=report,
                    include_private=args.include_private_report,
                )
                print()
                print(f"publish queue report created: {path}")
            return 1 if has_publish_queue_blockers(report, strict=args.strict) else 0

        if args.command == "copy":
            from .clipboard import write_clipboard

            article = load_article(args.file)
            if args.part == "title":
                value = article.title
            elif args.part == "body":
                value = body_with_tags(article) if args.append_tags else article.body
            elif args.part == "tags":
                value = hashtags_for(article)
            else:
                value = text_bundle(article, append_tags=args.append_tags, include_title=True)
            write_clipboard(value)
            print(f"copied {args.part}: {article.source}")
            return 0

        if args.command == "menu":
            from .menu import run_menu

            return run_menu(args.project_dir, initial_file=args.file)

        if args.command == "gui":
            from .gui import launch_gui, smoke_gui

            if args.smoke:
                print(smoke_gui(args.project_dir, safe_display=args.safe_display))
                return 0
            return launch_gui(args.project_dir, safe_display=args.safe_display)

        if args.command == "diagnose":
            from .diagnostics import (
                create_diagnostic_report,
                format_diagnostics,
                preview_diagnostic_report,
                run_diagnostics,
            )

            project_dir = args.project_dir.resolve()
            if args.preview:
                print(preview_diagnostic_report(project_dir, include_private=args.include_private))
            elif args.report:
                path = create_diagnostic_report(project_dir, include_private=args.include_private)
                print(f"diagnostic report created: {path}")
            else:
                print(format_diagnostics(run_diagnostics(project_dir)))
            return 0

        if args.command == "support":
            from .privacy import format_privacy_audit_report, has_privacy_audit_blockers, run_privacy_audit
            from .support import (
                create_support_bundle,
                create_support_request,
                format_support_bundle_verification,
                verify_support_bundle,
            )

            if args.verify:
                errors = verify_support_bundle(args.verify.resolve())
                print(format_support_bundle_verification(args.verify, errors))
                return 1 if errors else 0
            project_dir = args.project_dir.resolve()
            privacy_blocked = False
            if args.bundle:
                path = create_support_bundle(project_dir, include_private=args.include_private)
                print(f"support bundle created: {path}")
                errors = verify_support_bundle(path)
                print(format_support_bundle_verification(path, errors))
                if args.include_private:
                    print("privacy audit skipped because --include-private was used.")
                else:
                    privacy = run_privacy_audit(project_dir)
                    privacy_blocked = has_privacy_audit_blockers(privacy)
                    print()
                    print(format_privacy_audit_report(privacy))
                if errors or privacy_blocked:
                    return 1
            else:
                path = create_support_request(project_dir, include_private=args.include_private)
                print(f"support request created: {path}")
                if args.include_private:
                    print("privacy audit skipped because --include-private was used.")
                else:
                    privacy = run_privacy_audit(project_dir)
                    privacy_blocked = has_privacy_audit_blockers(privacy)
                    print()
                    print(format_privacy_audit_report(privacy))
                if privacy_blocked:
                    return 1
            if args.open:
                _open_path(path)
            return 0

        if args.command == "privacy-audit":
            from .privacy import format_privacy_audit_report, has_privacy_audit_blockers, run_privacy_audit

            report = run_privacy_audit(args.project_dir.resolve(), all_artifacts=args.all)
            print(format_privacy_audit_report(report))
            return 1 if has_privacy_audit_blockers(report, strict=args.strict) else 0

        if args.command == "version":
            from .app_info import collect_app_info, format_app_info

            print(format_app_info(collect_app_info(args.project_dir.resolve())))
            return 0

        if args.command == "licenses":
            from .licenses import collect_dependency_notices, format_dependency_notices, write_dependency_notices

            notices = collect_dependency_notices()
            if args.write:
                path = write_dependency_notices(args.write, notices)
                print(f"dependency notices written: {path}")
            else:
                print(format_dependency_notices(notices))
            return 0

        if args.command == "readiness":
            from .readiness import format_readiness_report, run_readiness

            print(format_readiness_report(run_readiness(args.project_dir.resolve())))
            return 0

        if args.command == "repair":
            from .repair import format_repair_report, has_repair_blockers, run_repair

            report = run_repair(
                args.project_dir.resolve(),
                apply=args.apply,
                cleanup_privacy=args.cleanup_privacy,
                cleanup_old=args.cleanup_old,
                include_releases=args.include_releases,
                days=args.days,
                keep_latest=args.keep_latest,
            )
            print(format_repair_report(report))
            return 1 if has_repair_blockers(report, strict=args.strict) else 0

        if args.command == "recovery-kit":
            from .repair import (
                format_recovery_kit_report,
                has_recovery_kit_blockers,
                run_recovery_kit,
                write_recovery_kit_report,
            )

            project_dir = args.project_dir.resolve()
            report = run_recovery_kit(
                project_dir,
                create_bundle_on_issue=not args.no_support_bundle,
            )
            print(format_recovery_kit_report(report))
            if args.report:
                path = write_recovery_kit_report(project_dir, report=report)
                try:
                    display_path = path.resolve().relative_to(project_dir)
                except ValueError:
                    display_path = Path(path.name)
                print(f"recovery kit report saved: {display_path}")
            return 1 if has_recovery_kit_blockers(report, strict=args.strict) else 0

        if args.command == "troubleshoot":
            from .troubleshoot import (
                format_troubleshoot_report,
                has_troubleshoot_blockers,
                run_troubleshoot,
            )

            report = run_troubleshoot(
                args.project_dir.resolve(),
                include_releases=args.include_releases,
            )
            print(format_troubleshoot_report(report))
            return 1 if has_troubleshoot_blockers(report, strict=args.strict) else 0

        if args.command == "quickstart":
            from .quickstart import format_quickstart_report, has_quickstart_blockers, run_quickstart

            report = run_quickstart(args.project_dir.resolve(), smoke_helper=args.smoke_helper)
            print(format_quickstart_report(report))
            return 1 if has_quickstart_blockers(report, strict=args.strict) else 0

        if args.command == "action-plan":
            from .action_plan import build_action_plan, format_action_plan

            print(format_action_plan(build_action_plan(args.project_dir.resolve(), limit=args.limit)))
            return 0

        if args.command == "overview":
            from .overview import (
                build_overview,
                format_overview_report,
                has_overview_blockers,
                write_overview_report,
            )

            report = build_overview(
                args.project_dir.resolve(),
                days=args.days,
                stale_days=args.stale_days,
                pattern=args.glob,
            )
            print(format_overview_report(report, include_private=not args.public))
            if args.report:
                path = write_overview_report(
                    args.project_dir.resolve(),
                    report=report,
                    include_private=args.include_private_report,
                )
                print()
                print(f"overview report created: {path}")
            return 1 if has_overview_blockers(report, strict=args.strict) else 0

        if args.command == "first-run":
            from .first_run import format_first_run_report, has_first_run_blockers, run_first_run_checklist

            report = run_first_run_checklist(
                args.project_dir.resolve(),
                create=args.create,
                gui_smoke=args.gui_smoke,
                smoke_helper=args.smoke_helper,
            )
            print(format_first_run_report(report))
            return 1 if has_first_run_blockers(report, strict=args.strict) else 0

        if args.command == "acceptance":
            from .acceptance import (
                format_acceptance_report,
                has_acceptance_blockers,
                run_acceptance_check,
                write_acceptance_report,
            )

            full = args.full
            report = run_acceptance_check(
                args.project_dir.resolve(),
                create=args.create or full,
                gui_smoke=args.gui_smoke or full,
                smoke_helper=args.smoke_helper or full,
            )
            print(format_acceptance_report(report))
            if args.report or full:
                path = write_acceptance_report(args.project_dir.resolve(), report=report)
                print()
                print(f"acceptance report created: {path}")
            return 1 if has_acceptance_blockers(report, strict=args.strict) else 0

        if args.command == "commercial-readiness":
            from .commercial import (
                format_commercial_readiness_report,
                has_commercial_readiness_blockers,
                run_commercial_readiness,
                write_commercial_readiness_report,
                write_commercial_policy_review,
            )

            report = run_commercial_readiness(args.project_dir.resolve())
            print(format_commercial_readiness_report(report))
            if args.report:
                path = write_commercial_readiness_report(args.project_dir.resolve(), report=report)
                print()
                print(f"commercial readiness report created: {path}")
            if args.policy_review:
                path = write_commercial_policy_review(args.project_dir.resolve())
                print()
                print(f"commercial policy review created: {path}")
            return 1 if has_commercial_readiness_blockers(report, strict=args.strict) else 0

        if args.command == "commercial-setup":
            from .commercial_setup import (
                apply_commercial_setup_template,
                create_commercial_setup_template,
                format_commercial_setup_apply_result,
                format_commercial_settings,
                list_commercial_setup_templates,
                update_commercial_settings,
            )
            from .settings import load_settings

            project_dir = args.project_dir.resolve()
            if args.list_templates:
                templates = list_commercial_setup_templates(project_dir)
                print("\n".join(str(path) for path in templates) if templates else "No commercial setup templates.")
                return 0
            apply_path = args.apply_template
            if args.apply_latest_template:
                templates = list_commercial_setup_templates(project_dir)
                if not templates:
                    raise ArticleError("適用できる販売者テンプレートがありません。先に --template で作成してください。")
                apply_path = templates[0]
            if apply_path:
                result = apply_commercial_setup_template(project_dir, apply_path)
                print(format_commercial_setup_apply_result(result))
                settings = result.settings
            else:
                settings = load_settings(project_dir)
            should_update = (
                args.seller_name is not None
                or args.sales_url is not None
                or args.refund_url is not None
                or args.support_contact is not None
                or args.terms_reviewed
                or args.support_scope_confirmed
                or args.clear_review
            )
            if should_update:
                settings = update_commercial_settings(
                    project_dir,
                    seller_name=args.seller_name,
                    sales_channel_url=args.sales_url,
                    refund_policy_url=args.refund_url,
                    support_contact=args.support_contact,
                    terms_reviewed=True if args.terms_reviewed else None,
                    support_scope_confirmed=True if args.support_scope_confirmed else None,
                    clear_review=args.clear_review,
                )
                print("commercial setup saved")
            if args.template:
                result = create_commercial_setup_template(project_dir)
                print(f"commercial setup template created: {result.path}")
                print(f"missing: {result.missing}")
            print(format_commercial_settings(settings))
            return 0

        if args.command == "sales-handoff":
            from .sales_handoff import (
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

            project_dir = args.project_dir.resolve()
            if args.extract_buyer:
                try:
                    result = extract_buyer_delivery(args.extract_buyer, output_dir=args.output_dir)
                except (OSError, ValueError) as exc:
                    print(f"error: {exc}")
                    return 1
                print(format_buyer_delivery_result(result))
                return 0
            if args.package_buyer:
                try:
                    package_path = package_buyer_delivery(args.package_buyer, output_path=args.output_package)
                except (OSError, ValueError) as exc:
                    print(f"error: {exc}")
                    return 1
                errors = verify_buyer_delivery_package(package_path)
                print(format_buyer_delivery_package_verification(package_path, errors))
                return 1 if errors else 0
            if args.verify_buyer_package:
                errors = verify_buyer_delivery_package(args.verify_buyer_package)
                print(format_buyer_delivery_package_verification(args.verify_buyer_package, errors))
                return 1 if errors else 0
            if args.verify_buyer:
                if args.verify_buyer.suffix.casefold() == ".zip":
                    errors = verify_buyer_delivery_package(args.verify_buyer)
                    print(format_buyer_delivery_package_verification(args.verify_buyer, errors))
                else:
                    errors = verify_buyer_delivery(args.verify_buyer)
                    print(format_buyer_delivery_verification(args.verify_buyer, errors))
                return 1 if errors else 0
            if args.verify:
                errors = verify_sales_handoff(args.verify)
                print(format_sales_handoff_verification(args.verify, errors))
                return 1 if errors else 0
            if args.list:
                handoffs = list_sales_handoffs(project_dir)
                print("\n".join(str(path) for path in handoffs) if handoffs else "No sales handoffs.")
                return 0
            if args.list_buyer:
                deliveries = list_buyer_deliveries(project_dir)
                print("\n".join(str(path) for path in deliveries) if deliveries else "No buyer delivery folders.")
                return 0
            if args.list_buyer_package:
                packages = list_buyer_delivery_packages(project_dir)
                print("\n".join(str(path) for path in packages) if packages else "No buyer delivery zips.")
                return 0
            try:
                result = create_sales_handoff(project_dir, strict=args.strict)
            except ValueError as exc:
                print(f"error: {exc}")
                return 1
            print(f"sales handoff created: {result.path}")
            print(f"release package: {result.release_path.name}")
            print(f"readiness warnings: {result.warnings}")
            errors = verify_sales_handoff(result.path)
            print(format_sales_handoff_verification(result.path, errors))
            return 1 if errors else 0

        if args.command == "sales-materials":
            from .sales_materials import (
                create_sales_materials,
                format_sales_materials_verification,
                list_sales_materials,
                verify_sales_materials,
            )

            project_dir = args.project_dir.resolve()
            if args.verify:
                errors = verify_sales_materials(args.verify, strict=args.strict, project_dir=project_dir)
                print(format_sales_materials_verification(args.verify, errors, strict=args.strict))
                return 1 if errors else 0
            if args.list:
                materials = list_sales_materials(project_dir)
                print("\n".join(str(path) for path in materials) if materials else "No sales materials.")
                return 0
            result = create_sales_materials(project_dir)
            print(f"sales materials created: {result.path}")
            print(f"placeholders: {result.placeholders}")
            errors = verify_sales_materials(result.path, strict=args.strict, project_dir=project_dir)
            print(format_sales_materials_verification(result.path, errors, strict=args.strict))
            return 1 if errors else 0

        if args.command == "sales-finalize":
            from .sales_finalize import (
                create_sales_finalize,
                format_buyer_send_readiness_report,
                format_sales_finalize_report,
                has_buyer_send_readiness_blockers,
                has_sales_finalize_blockers,
                run_buyer_send_readiness,
                write_buyer_send_readiness_report,
                write_seller_delivery_receipt,
            )

            project_dir = args.project_dir.resolve()
            if args.send_check or args.send_check_report or args.delivery_receipt:
                from dataclasses import replace

                report = run_buyer_send_readiness(project_dir)
                saved_path = None
                receipt_path = None
                if args.send_check_report or args.delivery_receipt:
                    saved_path = write_buyer_send_readiness_report(project_dir, report=report)
                    report = replace(report, report_path=saved_path)
                if args.delivery_receipt and not has_buyer_send_readiness_blockers(report, strict=args.strict):
                    receipt_path = write_seller_delivery_receipt(project_dir, report=report)
                print(format_buyer_send_readiness_report(report))
                if saved_path is not None:
                    print()
                    print(f"buyer send readiness report created: {saved_path}")
                if receipt_path is not None:
                    print(f"seller delivery receipt created: {receipt_path}")
                elif args.delivery_receipt and has_buyer_send_readiness_blockers(report, strict=args.strict):
                    print()
                    print("seller delivery receipt not created because buyer send readiness has blockers.")
                return 1 if has_buyer_send_readiness_blockers(report, strict=args.strict) else 0

            report = create_sales_finalize(
                project_dir,
                strict=args.strict,
                content_strict=args.content_strict,
                gui_smoke=args.gui_smoke,
                install_smoke=args.install_smoke,
                apply_latest_template=args.apply_latest_template,
                save_report=not args.no_report,
            )
            print(format_sales_finalize_report(report))
            return 1 if has_sales_finalize_blockers(report, strict=args.strict) else 0

        if args.command == "sales-plan":
            from .sales_plan import build_sales_plan, format_sales_plan, has_sales_plan_blockers, write_sales_plan_report

            report = build_sales_plan(args.project_dir.resolve())
            print(format_sales_plan(report))
            if args.report:
                path = write_sales_plan_report(args.project_dir.resolve(), report=report)
                print()
                print(f"sales plan report created: {path}")
            return 1 if has_sales_plan_blockers(report, strict=args.strict) else 0

        if args.command == "sales-review":
            from .sales_review import format_sales_review, has_sales_review_blockers, run_sales_review, write_sales_review_report

            report = run_sales_review(args.project_dir.resolve())
            print(format_sales_review(report))
            if args.report:
                path = write_sales_review_report(args.project_dir.resolve(), report=report)
                print()
                print(f"sales review report created: {path}")
            return 1 if has_sales_review_blockers(report, strict=args.strict) else 0

        if args.command == "sales-launch":
            from .sales_launch import (
                format_sales_launch_checklist,
                has_sales_launch_blockers,
                run_sales_launch_check,
                write_sales_launch_checklist,
            )

            report = run_sales_launch_check(args.project_dir.resolve())
            print(format_sales_launch_checklist(report))
            if args.report:
                path = write_sales_launch_checklist(args.project_dir.resolve(), report=report)
                print()
                print(f"sales launch checklist created: {path}")
            return 1 if has_sales_launch_blockers(report, strict=args.strict) else 0

        if args.command == "self-test":
            from .selftest import format_self_test_report, has_self_test_blockers, run_self_test, write_self_test_report

            report = run_self_test(
                args.project_dir.resolve(),
                create=args.create,
                gui_smoke=args.gui_smoke,
            )
            print(format_self_test_report(report))
            if args.report:
                path = write_self_test_report(args.project_dir.resolve(), report=report)
                print()
                print(f"self-test report created: {path}")
            return 1 if has_self_test_blockers(report, strict=args.strict) else 0

        if args.command == "workflow-smoke":
            from .workflow_smoke import (
                format_workflow_smoke_report,
                has_workflow_smoke_blockers,
                run_workflow_smoke,
                write_workflow_smoke_report,
            )

            report = run_workflow_smoke(
                args.project_dir.resolve(),
                gui_smoke=args.gui_smoke,
                keep=args.keep,
            )
            print(format_workflow_smoke_report(report))
            if args.report:
                path = write_workflow_smoke_report(args.project_dir.resolve(), report=report)
                print()
                print(f"workflow smoke report created: {path}")
            return 1 if has_workflow_smoke_blockers(report, strict=args.strict) else 0

        if args.command == "preflight":
            from .preflight import format_preflight_report, has_preflight_blockers, run_preflight

            report = run_preflight(
                args.project_dir.resolve(),
                create_release=args.create_release,
                install_smoke=args.install_smoke,
                gui_smoke=args.gui_smoke,
                content_strict=args.content_strict,
            )
            print(format_preflight_report(report))
            return 1 if has_preflight_blockers(report, strict=args.strict) else 0

        if args.command == "backup":
            from .backup import create_backup, format_backup_inspection, inspect_backup, list_backups, restore_backup

            if args.inspect:
                print(format_backup_inspection(inspect_backup(args.inspect)))
            elif args.restore:
                result = restore_backup(
                    args.project_dir.resolve(),
                    args.restore,
                    create_safety_backup=not args.no_safety_backup,
                )
                print(f"backup restored: {result.backup}")
                if result.safety_backup:
                    print(f"safety backup created: {result.safety_backup}")
                print(f"restored files: {len(result.restored_files)}")
            elif args.list:
                backups = list_backups(args.project_dir.resolve())
                print("\n".join(str(path) for path in backups) if backups else "No backups.")
            else:
                path = create_backup(args.project_dir.resolve())
                print(f"backup created: {path}")
            return 0

        if args.command == "release":
            from .release import (
                create_release_package,
                format_release_verification,
                list_releases,
                verify_release_package,
            )

            if args.verify:
                errors = verify_release_package(args.verify)
                print(format_release_verification(args.verify, errors))
                return 1 if errors else 0
            if args.list:
                releases = list_releases(args.project_dir.resolve())
                print("\n".join(str(path) for path in releases) if releases else "No releases.")
            else:
                path = create_release_package(args.project_dir.resolve())
                print(f"release package created: {path}")
            return 0

        if args.command == "images":
            from .images import format_image_report, inspect_images_path, missing_images

            refs = inspect_images_path(args.path, pattern=args.glob)
            print(format_image_report(refs))
            if args.strict and missing_images(refs):
                return 1
            return 0

        if args.command == "image-import":
            from .history import create_revision
            from .images import import_image_for_article, set_article_cover

            imported = import_image_for_article(
                args.file,
                args.image,
                alt_text=args.alt or "",
                optimize=args.optimize,
                max_width=args.max_width,
                quality=args.quality,
            )
            if args.insert or args.cover:
                create_revision(args.project_dir.resolve(), args.file, label="before-image-insert")
            if args.cover:
                set_article_cover(args.file, imported.relative_path)
                print(f"set cover: {imported.relative_path}")
            if args.insert:
                current = args.file.read_text(encoding="utf-8")
                write_text_atomic(args.file, current.rstrip() + "\n\n" + imported.markdown + "\n")
                print(f"inserted image markdown: {imported.markdown}")
            else:
                print(imported.markdown)
            print(f"copied image: {imported.target}")
            return 0

        if args.command == "quality":
            from .quality import format_quality_report, has_failures, run_quality_checks

            checks = run_quality_checks(args.project_dir.resolve(), include_articles=not args.product_only)
            print(format_quality_report(checks))
            return 1 if has_failures(checks, strict=args.strict) else 0

        if args.command == "cleanup":
            from .maintenance import cleanup_generated_files, format_cleanup_report

            result = cleanup_generated_files(
                args.project_dir.resolve(),
                older_than_days=args.days,
                dry_run=not args.apply,
                include_reports=not args.helpers_only,
                include_releases=args.include_releases,
                keep_latest=args.keep_latest,
                privacy_failed=args.privacy_failed,
            )
            print(format_cleanup_report(result, dry_run=not args.apply))
            return 0

        if args.command == "export":
            from .export import export_article_inventory, list_reports

            project_dir = args.project_dir.resolve()
            if args.list:
                reports = list_reports(project_dir)
                print("\n".join(str(path) for path in reports) if reports else "No reports.")
            else:
                path = export_article_inventory(project_dir)
                print(f"article inventory exported: {path}")
            return 0

        if args.command == "history":
            from .history import format_revisions, list_revisions, restore_revision

            project_dir = args.project_dir.resolve()
            if args.restore:
                restored = restore_revision(project_dir, args.file, args.restore)
                print(f"restored: {restored}")
            else:
                print(format_revisions(list_revisions(project_dir, args.file)))
            return 0

        if args.command == "setup":
            from .setup_check import format_setup_report, run_setup_check

            print(format_setup_report(run_setup_check(args.project_dir.resolve(), create=args.create)))
            return 0

        if args.command == "plan":
            from .workflow import format_plan

            print(format_plan(args.path, pattern=args.glob))
            return 0

        if args.command == "calendar":
            from .workflow import format_calendar

            print(format_calendar(args.path, pattern=args.glob, days=args.days))
            return 0

        if args.command == "calendar-export":
            from .settings import load_settings
            from .workflow import export_calendar, format_calendar_export

            project_dir = args.project_dir.resolve()
            settings = load_settings(project_dir)
            source = args.path or (project_dir / "articles")
            result = export_calendar(
                project_dir,
                source,
                pattern=args.glob or settings.article_glob,
                days=args.days,
                output_path=args.output,
                include_private=args.include_private,
            )
            print(format_calendar_export(result))
            return 0

        if args.command == "status":
            from .workflow import set_article_status

            set_article_status(args.file, args.status)
            print(f"status updated: {args.file} -> {args.status}")
            return 0

        if args.command == "schedule":
            from .workflow import clear_article_schedule, set_article_schedule

            if args.clear:
                clear_article_schedule(args.file)
                print(f"schedule cleared: {args.file}")
            else:
                if not args.at:
                    raise ArticleError("schedule には --at 'YYYY-MM-DD HH:MM' が必要です。")
                set_article_schedule(args.file, args.at)
                print(f"scheduled: {args.file} -> {args.at}")
            return 0

        if args.command == "published":
            from .workflow import mark_article_published

            mark_article_published(args.file, url=args.url or "")
            print(f"marked published: {args.file}")
            return 0

        if args.command == "idea":
            from .workflow import add_idea, format_ideas, promote_idea

            project_dir = args.project_dir.resolve()
            if args.idea_command == "add":
                idea = add_idea(project_dir, args.title, note=args.note or "", tags=args.tags or [])
                print(f"idea added: {idea.id}. {idea.title}")
                return 0
            if args.idea_command == "list":
                print(format_ideas(project_dir, include_done=args.all))
                return 0
            if args.idea_command == "promote":
                path = promote_idea(project_dir, args.id, articles_dir=args.dir)
                print(f"idea promoted: {path}")
                if args.open:
                    _open_path(path)
                return 0

        if args.command == "post":
            browser = _load_browser()

            _wait_until(args.at)
            article = load_article(args.file)
            publish = args.publish or (article.publish is True and not args.draft)
            asyncio.run(
                browser.post_article(
                    article,
                    publish=publish,
                    append_tags=args.append_tags,
                    keep_open=args.keep_open,
                    options=_browser_options(args),
                )
            )
            return 0

        if args.command == "batch":
            browser = _load_browser()

            _wait_until(args.at)
            files = _collect_files(args.path, args.glob)
            if not files:
                raise ArticleError(f"No markdown files found in {args.path}.")
            for index, file in enumerate(files):
                article = load_article(file)
                publish = args.publish or (article.publish is True and not args.draft)
                asyncio.run(
                    browser.post_article(
                        article,
                        publish=publish,
                        append_tags=args.append_tags,
                        keep_open=False,
                        options=_browser_options(args),
                    )
                )
                if index < len(files) - 1 and args.interval > 0:
                    time.sleep(args.interval)
            return 0

    except (ArticleError, RuntimeError, KeyboardInterrupt) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auto-note",
        description="Markdown articles to note.com drafts/posts via a logged-in browser.",
    )
    subparsers = parser.add_subparsers(dest="command")

    login = subparsers.add_parser("login", help="Open note.com login.")
    login.add_argument(
        "--default-browser",
        action="store_true",
        help="Open note.com login in the normal default browser instead of an automated browser.",
    )
    _add_browser_options(login)

    manual = subparsers.add_parser(
        "manual",
        help="Open note.com in the default browser and show copy buttons for one markdown article.",
    )
    manual.add_argument("file", type=Path, help="Markdown file to prepare.")
    manual.add_argument("--append-tags", action="store_true", help="Append frontmatter tags as hashtags to the body.")
    manual.add_argument("--no-open-note", action="store_true", help="Only open the helper HTML.")
    manual.add_argument("--write-only", action="store_true", help="Write helper HTML without opening a browser.")
    manual.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / ".auto-note",
        help="Directory for the local helper HTML.",
    )

    dashboard = subparsers.add_parser("dashboard", help="Open a local dashboard for markdown articles.")
    dashboard.add_argument("path", type=Path, nargs="?", default=Path("articles"), help="Markdown file or directory.")
    dashboard.add_argument("--glob", default="*.md", help="Glob used when path is a directory.")
    dashboard.add_argument("--append-tags", action="store_true", help="Append frontmatter tags as hashtags.")
    dashboard.add_argument("--open-note", action="store_true", help="Also open note.com's new post page.")
    dashboard.add_argument("--write-only", action="store_true", help="Write dashboard HTML without opening a browser.")
    dashboard.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / ".auto-note",
        help="Directory for generated dashboard files.",
    )

    new = subparsers.add_parser("new", help="Create a new markdown article from a template.")
    new.add_argument("title", nargs="?", help="Article title.")
    new.add_argument("--dir", type=Path, default=Path("articles"), help="Directory for new articles.")
    new.add_argument("--tag", dest="tags", action="append", help="Tag to add. Can be used multiple times.")
    new.add_argument("--slug", help="Filename slug.")
    new.add_argument("--force", action="store_true", help="Overwrite if the target filename exists.")
    new.add_argument("--open", action="store_true", help="Open the created markdown file.")
    new.add_argument("--template", default="standard", help="Article template key. Use --list-templates to see keys.")
    new.add_argument("--list-templates", action="store_true", help="List available article templates.")

    practice = subparsers.add_parser("practice", help="Create a polished practice article for first-run testing.")
    practice.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    practice.add_argument("--dir", type=Path, default=Path("articles"), help="Directory for the practice article.")
    practice.add_argument("--force", action="store_true", help="Overwrite today's practice article if it exists.")
    practice.add_argument("--open", action="store_true", help="Open the created markdown file.")

    starter_pack = subparsers.add_parser(
        "starter-pack",
        help="Create demo-ready starter articles, an idea, and an optional calendar export.",
    )
    starter_pack.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    starter_pack.add_argument("--dir", type=Path, default=Path("articles"), help="Directory for starter articles.")
    starter_pack.add_argument("--no-calendar", action="store_true", help="Skip privacy-safe .ics calendar export.")
    starter_pack.add_argument("--open-folder", action="store_true", help="Open the articles folder after creation.")

    starter_clean = subparsers.add_parser(
        "starter-clean",
        help="Preview or remove the demo starter articles and unused starter idea.",
    )
    starter_clean.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    starter_clean.add_argument("--dir", type=Path, default=Path("articles"), help="Directory for starter articles.")
    starter_clean.add_argument("--apply", action="store_true", help="Actually remove starter files. Default is preview only.")

    check = subparsers.add_parser("check", help="Check articles before posting.")
    check.add_argument("path", type=Path, nargs="?", default=Path("articles"), help="Markdown file or directory.")
    check.add_argument("--glob", default="*.md", help="Glob used when path is a directory.")
    check.add_argument("--append-tags", action="store_true", help="Include appended hashtags in body stats.")
    check.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")

    review = subparsers.add_parser("review", help="Score articles and show improvement suggestions.")
    review.add_argument("path", type=Path, nargs="?", default=Path("articles"), help="Markdown file or directory.")
    review.add_argument("--glob", default="*.md", help="Glob used when path is a directory.")
    review.add_argument("--append-tags", action="store_true", help="Include appended hashtags in body review.")
    review.add_argument("--strict", action="store_true", help="Exit with an error on improvement suggestions too.")

    publish_ready = subparsers.add_parser("publish-ready", help="Run a one-article readiness report before posting.")
    publish_ready.add_argument("file", type=Path, help="Markdown article file to check.")
    publish_ready.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    publish_ready.add_argument("--append-tags", action="store_true", help="Include appended hashtags in body checks.")
    publish_ready.add_argument(
        "--smoke-helper",
        action="store_true",
        help="Generate the local posting helper HTML without opening a browser.",
    )
    publish_ready.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for helper HTML generated by --smoke-helper.",
    )
    publish_ready.add_argument("--mark-ready", action="store_true", help="Set status to ready when no blockers remain.")
    publish_ready.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")

    improve = subparsers.add_parser("improve", help="Show a prioritized improvement plan for one article.")
    improve.add_argument("file", type=Path, help="Markdown article file to improve.")
    improve.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    improve.add_argument("--append-tags", action="store_true", help="Include appended hashtags in body review.")
    improve.add_argument("--limit", type=int, default=10, help="Maximum number of improvement steps to show.")
    improve.add_argument("--public", action="store_true", help="Mask article titles and file names in output.")
    improve.add_argument(
        "--report",
        action="store_true",
        help="Save a privacy-safe improvement plan report under .auto-note/reports.",
    )
    improve.add_argument(
        "--include-private-report",
        action="store_true",
        help="Save raw title and file name in the report. Use only for private storage.",
    )
    improve.add_argument("--strict", action="store_true", help="Exit with an error on warnings/improvements too.")

    publish_queue = subparsers.add_parser("publish-queue", help="Show all articles ordered by posting readiness.")
    publish_queue.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    publish_queue.add_argument("--glob", default=None, help="Article glob. Defaults to the saved setting.")
    publish_queue.add_argument(
        "--append-tags",
        action="store_true",
        default=None,
        help="Include appended hashtags in body checks. Defaults to the saved setting when omitted.",
    )
    publish_queue.add_argument("--public", action="store_true", help="Mask article titles and file names in output.")
    publish_queue.add_argument(
        "--report",
        action="store_true",
        help="Save a privacy-safe publish queue report under .auto-note/reports.",
    )
    publish_queue.add_argument(
        "--include-private-report",
        action="store_true",
        help="Save raw titles and file names in the report. Use only for private storage.",
    )
    publish_queue.add_argument("--strict", action="store_true", help="Exit with an error on CHECK items too.")

    copy = subparsers.add_parser("copy", help="Copy article text to the clipboard.")
    copy.add_argument("file", type=Path, help="Markdown file to copy.")
    copy.add_argument("--part", choices=("title", "body", "tags", "all"), default="body")
    copy.add_argument("--append-tags", action="store_true", help="Append frontmatter tags to body/all.")

    menu = subparsers.add_parser("menu", help="Open the interactive launcher menu.")
    menu.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    menu.add_argument("--file", type=Path, help="Open helper for this markdown file immediately.")

    gui = subparsers.add_parser("gui", help="Open the desktop GUI.")
    gui.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    gui.add_argument(
        "--smoke",
        action="store_true",
        help="Start and immediately close the GUI to verify it can initialize.",
    )
    gui.add_argument(
        "--safe-display",
        action="store_true",
        help="Start the GUI with large readable spacing for display/font issues.",
    )

    diagnose = subparsers.add_parser("diagnose", help="Run environment diagnostics.")
    diagnose.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    diagnose.add_argument("--report", action="store_true", help="Create a support diagnostic zip report.")
    diagnose.add_argument("--preview", action="store_true", help="Preview the support diagnostic report contents.")
    diagnose.add_argument(
        "--include-private",
        action="store_true",
        help="Include raw paths/settings in diagnostic report. Use only for trusted support.",
    )

    support = subparsers.add_parser("support", help="Create a support request markdown template.")
    support.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    support.add_argument("--open", action="store_true", help="Open the generated support request or bundle.")
    support.add_argument("--bundle", action="store_true", help="Create one zip with the request and diagnostic report.")
    support.add_argument("--verify", type=Path, help="Verify a support bundle zip created with --bundle.")
    support.add_argument(
        "--include-private",
        action="store_true",
        help="Include raw paths in the generated request/report. Use only for trusted support.",
    )

    privacy_audit = subparsers.add_parser(
        "privacy-audit",
        help="Check generated diagnostic/support/release artifacts for raw private markers.",
    )
    privacy_audit.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    privacy_audit.add_argument("--all", action="store_true", help="Scan all generated artifacts instead of latest only.")
    privacy_audit.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")

    version = subparsers.add_parser("version", help="Show auto-note version and environment summary.")
    version.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")

    licenses = subparsers.add_parser("licenses", help="Show third-party dependency notices.")
    licenses.add_argument(
        "--write",
        nargs="?",
        const=Path("docs") / "THIRD_PARTY_NOTICES.md",
        type=Path,
        help="Write notices to a Markdown file. Defaults to docs/THIRD_PARTY_NOTICES.md.",
    )

    readiness = subparsers.add_parser("readiness", help="Show a user-facing readiness score and next actions.")
    readiness.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")

    repair = subparsers.add_parser("repair", help="Preview or apply safe project repairs.")
    repair.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    repair.add_argument("--apply", action="store_true", help="Apply safe setup repairs. Default is preview only.")
    repair.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")
    repair.add_argument(
        "--cleanup-privacy",
        action="store_true",
        help="Also target generated artifacts that fail privacy-audit --all.",
    )
    repair.add_argument(
        "--cleanup-old",
        action="store_true",
        help="Also target old generated helper/report artifacts.",
    )
    repair.add_argument("--days", type=int, default=7, help="Age threshold for --cleanup-old.")
    repair.add_argument("--keep-latest", type=int, default=3, help="Newest report artifacts to keep for --cleanup-old.")
    repair.add_argument(
        "--include-releases",
        action="store_true",
        help="Allow cleanup options to include release packages.",
    )

    recovery_kit = subparsers.add_parser(
        "recovery-kit",
        help="Apply safe setup repair, rerun troubleshooting, and create a support bundle when issues remain.",
    )
    recovery_kit.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    recovery_kit.add_argument(
        "--no-support-bundle",
        action="store_true",
        help="Do not create a support bundle when troubleshooting still reports issues.",
    )
    recovery_kit.add_argument("--report", action="store_true", help="Save the recovery kit report under .auto-note/reports.")
    recovery_kit.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")

    troubleshoot = subparsers.add_parser("troubleshoot", help="Diagnose common startup/login/support/privacy issues.")
    troubleshoot.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    troubleshoot.add_argument(
        "--include-releases",
        action="store_true",
        help="Also include release packages when summarizing privacy cleanup candidates.",
    )
    troubleshoot.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")

    quickstart = subparsers.add_parser("quickstart", help="Check the first publish path for a new user.")
    quickstart.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    quickstart.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")
    quickstart.add_argument(
        "--smoke-helper",
        action="store_true",
        help="Generate a local posting helper HTML without opening a browser.",
    )

    action_plan = subparsers.add_parser("action-plan", help="Show prioritized next actions for the current project.")
    action_plan.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    action_plan.add_argument("--limit", type=int, default=5, help="Maximum number of actions to show.")

    overview = subparsers.add_parser("overview", help="Show a daily operations summary for articles.")
    overview.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    overview.add_argument("--glob", default=None, help="Article glob. Defaults to the saved setting.")
    overview.add_argument("--days", type=int, default=14, help="Calendar window for upcoming scheduled articles.")
    overview.add_argument("--stale-days", type=int, default=14, help="Warn about drafts older than this many days.")
    overview.add_argument("--public", action="store_true", help="Mask article titles and file names in output.")
    overview.add_argument(
        "--report",
        action="store_true",
        help="Save a privacy-safe operations summary under .auto-note/reports.",
    )
    overview.add_argument(
        "--include-private-report",
        action="store_true",
        help="Save raw article titles and file names in the report. Use only for private storage.",
    )
    overview.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")

    first_run = subparsers.add_parser("first-run", help="Show the buyer-facing first-run checklist.")
    first_run.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    first_run.add_argument("--create", action="store_true", help="Create basic folders/settings before checking.")
    first_run.add_argument("--gui-smoke", action="store_true", help="Verify GUI initialization in a subprocess.")
    first_run.add_argument(
        "--smoke-helper",
        action="store_true",
        help="Generate a local posting helper HTML without opening a browser.",
    )
    first_run.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")

    acceptance = subparsers.add_parser("acceptance", help="Run a buyer-facing acceptance check after install.")
    acceptance.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    acceptance.add_argument(
        "--full",
        action="store_true",
        help="Run the complete buyer acceptance path: create setup, GUI smoke, helper smoke, and save a report.",
    )
    acceptance.add_argument("--create", action="store_true", help="Create basic folders/settings before checking.")
    acceptance.add_argument("--gui-smoke", action="store_true", help="Verify GUI initialization in a subprocess.")
    acceptance.add_argument(
        "--smoke-helper",
        action="store_true",
        help="Generate a local posting helper HTML without opening a browser.",
    )
    acceptance.add_argument("--report", action="store_true", help="Save the acceptance report under .auto-note/reports.")
    acceptance.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")

    commercial_readiness = subparsers.add_parser(
        "commercial-readiness",
        help="Show seller-facing commercial readiness before sale.",
    )
    commercial_readiness.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    commercial_readiness.add_argument(
        "--report",
        action="store_true",
        help="Save the commercial readiness report under .auto-note/reports.",
    )
    commercial_readiness.add_argument(
        "--policy-review",
        action="store_true",
        help="Save a seller-only refund/license/support policy review under .auto-note/sales.",
    )
    commercial_readiness.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")

    commercial_setup = subparsers.add_parser(
        "commercial-setup",
        help="View or save seller-facing commercial setup values.",
    )
    commercial_setup.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    commercial_setup.add_argument("--seller-name", help="Seller or shop name shown in sale/support context.")
    commercial_setup.add_argument("--sales-url", help="Sales page, marketplace, or checkout URL.")
    commercial_setup.add_argument("--refund-url", help="Refund/cancellation policy URL or document URL.")
    commercial_setup.add_argument("--support-contact", help="Support contact shown to buyers.")
    commercial_setup.add_argument(
        "--template",
        action="store_true",
        help="Create a seller profile fill-in template under .auto-note/sales.",
    )
    commercial_setup.add_argument(
        "--apply-template",
        type=Path,
        help="Read a filled seller profile template Markdown file and save its values.",
    )
    commercial_setup.add_argument(
        "--apply-latest-template",
        action="store_true",
        help="Read the latest seller profile template Markdown file and save its values.",
    )
    commercial_setup.add_argument("--list-templates", action="store_true", help="List saved seller profile templates.")
    commercial_setup.add_argument("--terms-reviewed", action="store_true", help="Mark terms/commercial policy reviewed.")
    commercial_setup.add_argument(
        "--support-scope-confirmed",
        action="store_true",
        help="Mark support scope/refund scope as confirmed on the sales page.",
    )
    commercial_setup.add_argument("--clear-review", action="store_true", help="Clear the saved commercial review flags.")

    sales_handoff = subparsers.add_parser(
        "sales-handoff",
        help="Create or verify a seller-facing sales handoff evidence zip.",
    )
    sales_handoff.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    sales_handoff.add_argument("--list", action="store_true", help="List existing sales handoff zips.")
    sales_handoff.add_argument("--verify", type=Path, help="Verify a sales handoff zip.")
    sales_handoff.add_argument(
        "--extract-buyer",
        type=Path,
        help="Extract the buyer-facing release zip, START_HERE_FOR_BUYER.txt, buyer handoff/support notes, BUYER_DELIVERY_MANIFEST.json, SHA256SUMS.txt, and buyer delivery zip from a sales handoff zip.",
    )
    sales_handoff.add_argument(
        "--package-buyer",
        type=Path,
        help="Create a buyer delivery zip from a verified buyer delivery folder.",
    )
    sales_handoff.add_argument("--verify-buyer", type=Path, help="Verify a buyer delivery folder or buyer delivery zip.")
    sales_handoff.add_argument("--verify-buyer-package", type=Path, help="Verify a buyer delivery zip created by --package-buyer.")
    sales_handoff.add_argument("--list-buyer", action="store_true", help="List buyer delivery folders.")
    sales_handoff.add_argument("--list-buyer-package", action="store_true", help="List buyer delivery zips.")
    sales_handoff.add_argument("--output-dir", type=Path, help="Directory for --extract-buyer output.")
    sales_handoff.add_argument("--output-package", type=Path, help="Zip file path for --package-buyer output.")
    sales_handoff.add_argument(
        "--strict",
        action="store_true",
        help="Refuse to create the handoff while commercial-readiness has warnings.",
    )

    sales_materials = subparsers.add_parser(
        "sales-materials",
        help="Generate marketplace listing, delivery, FAQ, and support copy drafts.",
    )
    sales_materials.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    sales_materials.add_argument("--list", action="store_true", help="List existing sales materials markdown files.")
    sales_materials.add_argument("--verify", type=Path, help="Verify a sales materials markdown file.")
    sales_materials.add_argument(
        "--strict",
        action="store_true",
        help="Fail while unresolved placeholders, raw emails, or a stale release name remain.",
    )

    sales_finalize = subparsers.add_parser(
        "sales-finalize",
        help="Create a release, sales materials, sales handoff zip, diagnostics, and final checks in one run.",
    )
    sales_finalize.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    sales_finalize.add_argument("--strict", action="store_true", help="Exit with an error while warnings remain.")
    sales_finalize.add_argument(
        "--content-strict",
        action="store_true",
        help="Treat article review improvement suggestions as preflight warnings.",
    )
    sales_finalize.add_argument("--gui-smoke", action="store_true", help="Verify GUI initialization during preflight.")
    sales_finalize.add_argument(
        "--install-smoke",
        action="store_true",
        help="Run the temporary install/update/uninstall smoke test during preflight.",
    )
    sales_finalize.add_argument(
        "--apply-latest-template",
        action="store_true",
        help="Apply the latest seller profile template before finalizing sales artifacts.",
    )
    sales_finalize.add_argument(
        "--send-check",
        action="store_true",
        help="Only check the latest buyer ZIP, delivery message, checklist, and evidence manifest before sending.",
    )
    sales_finalize.add_argument(
        "--send-check-report",
        action="store_true",
        help="Save the buyer send readiness report under .auto-note/sales. Implies --send-check.",
    )
    sales_finalize.add_argument(
        "--delivery-receipt",
        action="store_true",
        help="Save a seller delivery receipt template after buyer send readiness passes. Implies --send-check-report.",
    )
    sales_finalize.add_argument("--no-report", action="store_true", help="Do not save sales-finalize-*.txt.")

    sales_plan = subparsers.add_parser(
        "sales-plan",
        help="Show prioritized seller-side next actions before listing or delivery.",
    )
    sales_plan.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    sales_plan.add_argument("--strict", action="store_true", help="Exit with an error while warnings remain.")
    sales_plan.add_argument("--report", action="store_true", help="Save the sales plan report under .auto-note/sales.")

    sales_review = subparsers.add_parser(
        "sales-review",
        help="Review marketplace listing copy, buyer delivery message, and seller evidence before selling.",
    )
    sales_review.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    sales_review.add_argument("--strict", action="store_true", help="Exit with an error while warnings remain.")
    sales_review.add_argument("--report", action="store_true", help="Save the sales final review under .auto-note/sales.")

    sales_launch = subparsers.add_parser(
        "sales-launch",
        help="Create a final marketplace launch checklist after sales review and buyer delivery checks.",
    )
    sales_launch.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    sales_launch.add_argument("--strict", action="store_true", help="Exit with an error while warnings remain.")
    sales_launch.add_argument("--report", action="store_true", help="Save the sales launch checklist under .auto-note/sales.")

    self_test = subparsers.add_parser("self-test", help="Run a user-facing local health check after install.")
    self_test.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    self_test.add_argument("--create", action="store_true", help="Create basic folders/settings before checking.")
    self_test.add_argument("--gui-smoke", action="store_true", help="Verify GUI initialization in a subprocess.")
    self_test.add_argument("--report", action="store_true", help="Save the self-test report under .auto-note/reports.")
    self_test.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")

    workflow_smoke = subparsers.add_parser(
        "workflow-smoke",
        help="Run a temporary end-to-end workflow smoke test without touching user articles.",
    )
    workflow_smoke.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    workflow_smoke.add_argument("--gui-smoke", action="store_true", help="Also verify GUI initialization.")
    workflow_smoke.add_argument(
        "--keep",
        action="store_true",
        help="Keep the temporary smoke project under .auto-note/workflow-smoke for inspection.",
    )
    workflow_smoke.add_argument(
        "--report",
        action="store_true",
        help="Save the workflow smoke report under .auto-note/reports.",
    )
    workflow_smoke.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")

    preflight = subparsers.add_parser("preflight", help="Run a release preflight report before selling/distribution.")
    preflight.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    preflight.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")
    preflight.add_argument(
        "--content-strict",
        action="store_true",
        help="Treat article review improvement suggestions as preflight warnings.",
    )
    preflight.add_argument("--create-release", action="store_true", help="Create and verify a fresh release zip first.")
    preflight.add_argument(
        "--install-smoke",
        action="store_true",
        help="Run scripts/smoke-install.ps1 to test temp install/update/uninstall.",
    )
    preflight.add_argument(
        "--gui-smoke",
        action="store_true",
        help="Start and immediately close the GUI to verify it can initialize.",
    )

    backup = subparsers.add_parser("backup", help="Create or list project backups.")
    backup.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    backup.add_argument("--list", action="store_true", help="List existing backups instead of creating one.")
    backup.add_argument("--inspect", type=Path, help="Inspect a backup zip before restoring it.")
    backup.add_argument("--restore", type=Path, help="Restore articles/settings from a backup zip.")
    backup.add_argument(
        "--no-safety-backup",
        action="store_true",
        help="Do not create a safety backup before restore.",
    )

    release = subparsers.add_parser("release", help="Create or list distribution zip packages.")
    release.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    release.add_argument("--list", action="store_true", help="List existing releases instead of creating one.")
    release.add_argument("--verify", type=Path, help="Verify a release zip using CHECKSUMS.txt.")

    images = subparsers.add_parser("images", help="Check local images referenced by articles.")
    images.add_argument("path", type=Path, nargs="?", default=Path("articles"), help="Markdown file or directory.")
    images.add_argument("--glob", default="*.md", help="Glob used when path is a directory.")
    images.add_argument("--strict", action="store_true", help="Exit with an error when local images are missing.")

    image_import = subparsers.add_parser("image-import", help="Copy an image beside an article and print Markdown.")
    image_import.add_argument("file", type=Path, help="Markdown article file.")
    image_import.add_argument("image", type=Path, help="Image file to copy.")
    image_import.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    image_import.add_argument("--alt", help="Image alt text.")
    image_import.add_argument("--insert", action="store_true", help="Append the Markdown image to the article.")
    image_import.add_argument("--cover", action="store_true", help="Set the imported image as article cover.")
    image_import.add_argument("--optimize", action="store_true", help="Resize/compress the imported image with Pillow.")
    image_import.add_argument("--max-width", type=int, default=1600, help="Maximum image width for --optimize.")
    image_import.add_argument("--quality", type=int, default=85, help="JPEG/WebP quality for --optimize.")

    quality = subparsers.add_parser("quality", help="Run product-readiness checks.")
    quality.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    quality.add_argument("--strict", action="store_true", help="Exit with an error on warnings too.")
    quality.add_argument("--product-only", action="store_true", help="Skip user article/content checks.")

    cleanup = subparsers.add_parser("cleanup", help="Preview or delete old generated helper/report artifacts.")
    cleanup.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    cleanup.add_argument("--days", type=int, default=7, help="Only include generated files older than this many days.")
    cleanup.add_argument("--keep-latest", type=int, default=3, help="Keep this many newest report artifacts per type.")
    cleanup.add_argument("--helpers-only", action="store_true", help="Only target generated helper HTML files.")
    cleanup.add_argument(
        "--privacy-failed",
        action="store_true",
        help="Target generated artifacts that fail privacy-audit --all. Release packages still require --include-releases.",
    )
    cleanup.add_argument(
        "--include-releases",
        action="store_true",
        help="Also target old release packages. Newest packages are kept by --keep-latest.",
    )
    cleanup.add_argument("--apply", action="store_true", help="Delete the listed generated files.")

    export = subparsers.add_parser("export", help="Export article inventory CSV.")
    export.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    export.add_argument("--list", action="store_true", help="List existing CSV reports instead of exporting.")

    history = subparsers.add_parser("history", help="List or restore article save history.")
    history.add_argument("file", type=Path, help="Markdown article file.")
    history.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    history.add_argument("--restore", type=Path, help="Revision file to restore.")

    setup = subparsers.add_parser("setup", help="Check first-run setup and show next steps.")
    setup.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    setup.add_argument("--create", action="store_true", help="Create basic folders/settings if missing.")

    plan = subparsers.add_parser("plan", help="Show articles grouped by workflow status.")
    plan.add_argument("path", type=Path, nargs="?", default=Path("articles"), help="Markdown file or directory.")
    plan.add_argument("--glob", default="*.md", help="Glob used when path is a directory.")

    calendar = subparsers.add_parser("calendar", help="Show scheduled articles.")
    calendar.add_argument("path", type=Path, nargs="?", default=Path("articles"), help="Markdown file or directory.")
    calendar.add_argument("--glob", default="*.md", help="Glob used when path is a directory.")
    calendar.add_argument("--days", type=int, default=30, help="Show this many days ahead.")

    calendar_export = subparsers.add_parser(
        "calendar-export",
        help="Export scheduled articles as an .ics calendar file.",
    )
    calendar_export.add_argument("path", type=Path, nargs="?", help="Markdown file or directory.")
    calendar_export.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    calendar_export.add_argument("--glob", default=None, help="Article glob. Defaults to the saved setting.")
    calendar_export.add_argument("--days", type=int, default=90, help="Export scheduled articles in this window.")
    calendar_export.add_argument("--output", type=Path, help="Output .ics path.")
    calendar_export.add_argument(
        "--include-private",
        action="store_true",
        help="Include raw article titles and file names. Use only for your own calendar.",
    )

    status = subparsers.add_parser("status", help="Set article workflow status.")
    status.add_argument("file", type=Path, help="Markdown file to update.")
    status.add_argument("status", choices=("draft", "ready", "scheduled", "published"))

    schedule = subparsers.add_parser("schedule", help="Set or clear an article schedule.")
    schedule.add_argument("file", type=Path, help="Markdown file to update.")
    schedule.add_argument("--at", help="Scheduled local time, e.g. '2026-06-06 09:00'.")
    schedule.add_argument("--clear", action="store_true", help="Clear the schedule.")

    published = subparsers.add_parser("published", help="Mark an article as published.")
    published.add_argument("file", type=Path, help="Markdown file to update.")
    published.add_argument("--url", help="Published note URL.")

    idea = subparsers.add_parser("idea", help="Capture, list, or promote article ideas.")
    idea.add_argument("--project-dir", type=Path, default=Path.cwd(), help="auto-note project directory.")
    idea_subparsers = idea.add_subparsers(dest="idea_command", required=True)
    idea_add = idea_subparsers.add_parser("add", help="Add an idea.")
    idea_add.add_argument("title", help="Idea title.")
    idea_add.add_argument("--note", help="Short note or angle.")
    idea_add.add_argument("--tag", dest="tags", action="append", help="Tag to add. Can be used multiple times.")
    idea_list = idea_subparsers.add_parser("list", help="List ideas.")
    idea_list.add_argument("--all", action="store_true", help="Include promoted ideas.")
    idea_promote = idea_subparsers.add_parser("promote", help="Turn an idea into a markdown article.")
    idea_promote.add_argument("id", type=int, help="Idea id.")
    idea_promote.add_argument("--dir", type=Path, default=Path("articles"), help="Article output directory.")
    idea_promote.add_argument("--open", action="store_true", help="Open the created markdown file.")

    post = subparsers.add_parser("post", help="Fill or publish one markdown article.")
    post.add_argument("file", type=Path, help="Markdown file to post.")
    post.add_argument("--publish", action="store_true", help="Click note.com's publish flow after filling.")
    post.add_argument("--draft", action="store_true", help="Force draft mode even if frontmatter says publish: true.")
    post.add_argument("--append-tags", action="store_true", help="Append frontmatter tags as hashtags to the body.")
    post.add_argument(
        "--close-after-fill",
        dest="keep_open",
        action="store_false",
        help="Close the browser after filling a draft.",
    )
    post.set_defaults(keep_open=True)
    post.add_argument("--at", help="Wait until local time, e.g. '2026-06-06 09:00'.")
    _add_browser_options(post)

    batch = subparsers.add_parser("batch", help="Post markdown files in a directory.")
    batch.add_argument("path", type=Path, help="Markdown file or directory.")
    batch.add_argument("--glob", default="*.md", help="Glob used when path is a directory.")
    batch.add_argument("--interval", type=int, default=60, help="Seconds to wait between files.")
    batch.add_argument("--publish", action="store_true", help="Click note.com's publish flow for each article.")
    batch.add_argument("--draft", action="store_true", help="Force draft mode even if frontmatter says publish: true.")
    batch.add_argument("--append-tags", action="store_true", help="Append frontmatter tags as hashtags to the body.")
    batch.add_argument("--at", help="Wait until local time, e.g. '2026-06-06 09:00'.")
    _add_browser_options(batch)

    return parser


def _add_browser_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=Path.home() / ".auto-note" / "browser",
        help="Persistent browser profile directory. Defaults to ~/.auto-note/browser.",
    )
    parser.add_argument("--headless", action="store_true", help="Run Chromium without showing a browser window.")
    parser.add_argument(
        "--browser",
        choices=("chromium", "chrome", "msedge"),
        default="chromium",
        help="Browser engine to launch. Use chrome or msedge if OAuth login blocks bundled Chromium.",
    )
    parser.add_argument("--timeout", type=int, default=45, help="Page action timeout in seconds.")
    parser.add_argument("--slow-mo", type=int, default=0, help="Delay browser actions by this many milliseconds.")


def _browser_options(args: argparse.Namespace) -> BrowserOptions:
    browser = _load_browser()

    return browser.BrowserOptions(
        profile_dir=args.profile_dir.expanduser(),
        headless=args.headless,
        timeout_ms=args.timeout * 1000,
        slow_mo_ms=args.slow_mo,
        browser_channel=args.browser,
    )


def _load_browser():
    try:
        from . import browser
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("playwright"):
            raise RuntimeError(
                "Playwright が見つかりません。`python -m pip install -e .` と "
                "`python -m playwright install chromium` を実行してください。"
            ) from exc
        raise
    return browser


def _collect_files(path: Path, pattern: str) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(file for file in path.glob(pattern) if file.is_file())


def _wait_until(value: str | None) -> None:
    if not value:
        return

    target = _parse_local_datetime(value)
    now = datetime.now()
    seconds = (target - now).total_seconds()
    if seconds <= 0:
        return

    print(f"waiting until {target:%Y-%m-%d %H:%M:%S} local time...")
    while seconds > 0:
        sleep_for = min(seconds, 60)
        time.sleep(sleep_for)
        seconds = (target - datetime.now()).total_seconds()


def _parse_local_datetime(value: str) -> datetime:
    normalized = value.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            pass
    raise ArticleError("--at は 'YYYY-MM-DD HH:MM' の形式で指定してください。")


def _open_path(path: Path) -> None:
    resolved = path.resolve()
    if sys.platform.startswith("win"):
        os.startfile(resolved)  # type: ignore[attr-defined]
    else:
        webbrowser.open(resolved.as_uri())


if __name__ == "__main__":
    raise SystemExit(main())
