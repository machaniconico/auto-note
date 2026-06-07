# Release Checklist

配布前に確認する項目です。

## 自動チェック

```powershell
python -m compileall src tests
$env:PYTHONPATH='src'; python -m unittest discover -s tests
$env:PYTHONPATH='src'; python -m auto_note setup --project-dir . --create
$env:PYTHONPATH='src'; python -m auto_note repair --project-dir .
$env:PYTHONPATH='src'; python -m auto_note repair --project-dir . --cleanup-privacy --include-releases
$env:PYTHONPATH='src'; python -m auto_note repair --project-dir . --apply
$env:PYTHONPATH='src'; python -m auto_note troubleshoot --project-dir .
$env:PYTHONPATH='src'; python -m auto_note first-run --project-dir . --create --gui-smoke
$env:PYTHONPATH='src'; python -m auto_note acceptance --project-dir . --create --gui-smoke --smoke-helper --report
$env:PYTHONPATH='src'; python -m auto_note commercial-readiness --project-dir . --report
$env:PYTHONPATH='src'; python -m auto_note quickstart --project-dir .
$starter = Join-Path $env:TEMP "auto-note-starter-check"; New-Item -ItemType Directory -Force $starter | Out-Null; $env:PYTHONPATH='src'; python -m auto_note starter-pack --project-dir $starter --no-calendar
$env:PYTHONPATH='src'; python -m auto_note starter-clean --project-dir $starter
$env:PYTHONPATH='src'; python -m auto_note quickstart --project-dir . --smoke-helper
$env:PYTHONPATH='src'; python -m auto_note gui --project-dir . --smoke
$env:PYTHONPATH='src'; python -m auto_note overview --project-dir . --report
$env:PYTHONPATH='src'; python -m auto_note calendar-export --project-dir .
$env:PYTHONPATH='src'; python -m auto_note improve .\articles\post.md --project-dir . --report
$env:PYTHONPATH='src'; python -m auto_note publish-ready .\articles\post.md --smoke-helper
$env:PYTHONPATH='src'; python -m auto_note publish-queue --project-dir . --report
$env:PYTHONPATH='src'; python -m auto_note readiness --project-dir .
$env:PYTHONPATH='src'; python -m auto_note version --project-dir .
$env:PYTHONPATH='src'; python -m auto_note licenses
$env:PYTHONPATH='src'; python -m auto_note licenses --write
$env:PYTHONPATH='src'; python -m auto_note support --project-dir .
$env:PYTHONPATH='src'; python -m auto_note support --project-dir . --bundle
$env:PYTHONPATH='src'; python -m auto_note support --verify .\.auto-note\support\<support-bundle>.zip
$env:PYTHONPATH='src'; python -m auto_note privacy-audit --project-dir .
$env:PYTHONPATH='src'; python -m auto_note backup --project-dir .
$env:PYTHONPATH='src'; python -m auto_note backup --inspect .\.auto-note\backups\<backup-file>.zip
$env:PYTHONPATH='src'; python -m auto_note quality --project-dir .
$env:PYTHONPATH='src'; python -m auto_note quality --project-dir . --product-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-install.ps1
$env:PYTHONPATH='src'; python -m auto_note release --project-dir .
$env:PYTHONPATH='src'; python -m auto_note release --verify .\.auto-note\releases\<release-file>.zip
$env:PYTHONPATH='src'; python -m auto_note self-test --project-dir . --gui-smoke --report
$env:PYTHONPATH='src'; python -m auto_note workflow-smoke --project-dir . --report
$env:PYTHONPATH='src'; python -m auto_note preflight --project-dir . --gui-smoke
$env:PYTHONPATH='src'; python -m auto_note preflight --project-dir . --content-strict
$env:PYTHONPATH='src'; python -m auto_note preflight --project-dir . --create-release
$env:PYTHONPATH='src'; python -m auto_note preflight --project-dir . --create-release --install-smoke --gui-smoke
```

## GUIチェック

- `auto-note.lnk` でGUIが起動する
- `auto-note gui --project-dir . --smoke` でGUI初期化スモークがOKになる
- セットアップウィザードを表示できる
- 診断タブ、ヘルプ、コマンド検索の `自動修復` で、基本修復結果とプライバシー監査NG生成物候補を確認できる
- ホーム、診断タブ、ヘルプ、コマンド検索の `トラブル診断` で、GUIログ、noteログイン案内、プライバシー監査、最新配布ZIP状態を確認できる
- ホーム、初回タブ、診断、コマンド検索から初回チェックを表示できる
- ホーム、初回タブ、診断、ヘルプ、コマンド検索から `受入チェック` と `受入保存` を実行できる
- ホーム、初回タブ、診断、ヘルプ、コマンド検索から `販売準備` と `販売準備保存` を実行できる
- ホーム、初回タブ、診断、ヘルプ、コマンド検索の `スターター一式` で、サンプル記事、予定、アイデアを作成できる
- ホーム、診断、ヘルプ、コマンド検索の `スターター整理` で、スターター由来の記事と未使用アイデアの削除候補を確認できる
- ホームの優先アクション一覧で状態、項目、次の操作を確認でき、`選択を実行` と `CLIコピー` が使える
- ホーム、診断タブ、ヘルプ、コマンド検索の `運用サマリー` で、次の投稿、公開予定、古い下書き、公開URL未記録、アイデア箱を確認できる
- 予定タブまたはコマンド検索の `予定ICS出力` で、公開予定の `.ics` を保存できる
- ホームの優先アクションで投稿キュー対象が出た場合、`選択を実行` から対象記事と投稿準備パネルへ移動できる
- 初回タブで項目を選び、`この項目を実行` と `CLIをコピー` が使える
- 診断タブまたはコマンド検索の `E2E確認` で、簡易E2Eチェックを実行し、レポートを保存できる
- ホームまたは診断タブのクイック確認を表示できる
- ホームまたはコマンド検索の練習記事作成で、初回練習用の記事を作成できる
- チェックタブで記事レビュー一覧、点数、修正/改善件数、詳細項目を確認できる
- チェックタブのレビュー一覧から `記事を編集`、`投稿準備`、`準備OKにする` が使える
- 記事タブの投稿準備パネルで `READY` / `CHECK` / `BLOCKED`、項目別の状態、次アクションを確認できる
- 記事タブまたはチェックタブの投稿準備で、`次を実行`、`詳細`、`準備OK`、`HTML確認`、投稿ヘルパーへの導線が使える
- 記事タブ、チェックタブ、レビュー一覧、コマンド検索の `改善プラン` で、必須修正、仕上げ、投稿前確認をおすすめ順で確認できる
- 記事タブ、診断タブ、ヘルプ、コマンド検索の `投稿キュー` で全記事の `POSTABLE` / `CHECK` / `BLOCKED` / `DONE` と次アクションを確認できる
- 投稿ヘルパー起動前に投稿前チェックが走り、NG/確認項目がある場合は確認ダイアログで止められる
- 診断タブのヘルパー生成確認で投稿ヘルパーHTML生成を確認できる
- ホームの準備度スコアと診断タブの準備度レポートを確認できる
- ホームまたは診断タブの出荷前チェックを確認できる
- 診断タブまたはヘルプタブの出荷ZIP作成で、配布ZIP作成と検証結果を確認できる
- 新規記事を作成できる
- メタ編集でタイトル、概要、タグ、coverを保存できる
- 編集タブで保存できる
- 自動退避を確認、復元、削除できる
- 画像最適化の既定値を設定し、画像挿入で使える
- 投稿ヘルパーを開ける
- バックアップ作成とバックアップ復元を確認できる
- バックアップ確認で復元対象を表示できる
- 診断プレビューを表示できる
- ライセンス表示を確認できる
- ヘルプタブの問い合わせ一式で、問い合わせMarkdown、診断レポートZIP、manifest/checksum入りのzipを作成できる
- ヘルプタブの一式ZIP検証で、最新問い合わせ一式ZIPを検証できる
- 診断タブまたはヘルプタブのプライバシー監査で、問い合わせMarkdownを含む最新生成物に生の個人情報/記事情報が残っていないことを確認できる
- 診断レポートを作成できる
- 配布ZIPを作成できる
- 任意で `shortcuts/install-image-tools.bat` を実行し、画像最適化が使える

## インストールチェック

- 配布ZIPを展開できる
- `shortcuts/install-auto-note.bat` で `%LOCALAPPDATA%\auto-note` にインストールできる
- デスクトップまたはスタートメニューの `auto-note` から起動できる
- 更新時に `.auto-note\install-info.json` と `.auto-note\install-backups` が作成される
- スタートメニューまたは `shortcuts/uninstall-auto-note.bat` からアンインストールできる
- 既存の `articles` と `.auto-note` が削除されない

## 配布ZIPチェック

- `articles/.keep` はある
- `START_HERE.txt` がある
- `FIRST_RUN_CHECKLIST.txt` がある
- `BUYER_ACCEPTANCE_CHECKLIST.txt` がある
- `RELEASE_SUMMARY.txt` がある
- `shortcuts/install-auto-note.bat` がある
- `shortcuts/uninstall-auto-note.bat` がある
- ユーザー記事は含まれていない
- `.venv` は含まれていない
- `.auto-note` は含まれていない
- `RELEASE_MANIFEST.json` がある
- `CHECKSUMS.txt` がある
- `docs/THIRD_PARTY_NOTICES.md` がある
- `auto-note release --verify` でchecksum、manifest、ユーザー記事、`.auto-note`、`.venv` 混入なしを確認できる

## 販売前文書チェック

- `docs\INSTALL.md` を確認した
- `docs\QUICKSTART.md` を確認した
- `docs\UPDATE.md` を確認した
- `docs\SUPPORT.md` を確認した
- `docs\PRIVACY.md` を確認した
- `auto-note commercial-readiness --project-dir . --report` で販売前の残り確認事項を確認した
- `docs\TERMS_DRAFT.md` を販売形態に合わせて確認した
- `docs\COMMERCIAL_POLICY_DRAFT.md` を販売形態に合わせて確認した
- `docs\THIRD_PARTY_NOTICES.md` と `auto-note licenses` の内容を確認した
