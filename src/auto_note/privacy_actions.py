from __future__ import annotations


PRIVACY_FAILED_CLEANUP_GUI = "診断 > 危険生成物確認"
PRIVACY_FAILED_CLEANUP_RC_RECHECK = "auto-note commercial-readiness --project-dir ."


def privacy_failed_cleanup_command(*, include_releases: bool = False) -> str:
    command = "auto-note cleanup --project-dir . --privacy-failed"
    if include_releases:
        command += " --include-releases"
    return command


def privacy_failed_cleanup_apply_command(*, include_releases: bool = False) -> str:
    return f"{privacy_failed_cleanup_command(include_releases=include_releases)} --apply"


def privacy_failed_cleanup_target(
    action: str = "",
    *,
    include_releases: bool = False,
) -> tuple[str, str]:
    source = action or ""
    return (
        PRIVACY_FAILED_CLEANUP_GUI,
        privacy_failed_cleanup_command(
            include_releases=include_releases or "--include-releases" in source
        ),
    )


def privacy_failed_cleanup_action(
    action: str = "",
    *,
    include_releases: bool = False,
    fallback: str = "",
) -> str:
    source = action or ""
    include_releases = include_releases or "--include-releases" in source
    command = privacy_failed_cleanup_command(include_releases=include_releases)
    message = (
        f"`{command}` でNG生成物だけを削除前に確認してください。"
        f"GUIでは「{PRIVACY_FAILED_CLEANUP_GUI}」を開いてください。"
        f"削除する時だけ同じコマンドに `--apply` を追加します"
        f"（実行例: `{privacy_failed_cleanup_apply_command(include_releases=include_releases)}`）。"
        f"削除後は `{PRIVACY_FAILED_CLEANUP_RC_RECHECK}` で販売RC目途を再判定してください。"
    )
    if "sales-handoff --project-dir ." in source:
        message += "必要なら `auto-note sales-handoff --project-dir .` で販売用一式を作り直してください。"
    elif source and "--privacy-failed" not in source:
        message += source
    return message or fallback
