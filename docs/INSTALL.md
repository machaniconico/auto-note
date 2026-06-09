# Install

auto-note は管理者権限なしで使えるポータブルアプリとして配布できます。

## 推奨手順

1. 配布ZIPを展開する
2. まず `START_HERE.txt`, `FIRST_RUN_CHECKLIST.txt`, `BUYER_ACCEPTANCE_CHECKLIST.txt`, `RELEASE_SUMMARY.txt` を確認する
3. `shortcuts\install-auto-note.bat` を実行する
4. デスクトップまたはスタートメニューの `auto-note` を開く
5. 文字や行高が潰れて見える場合は `auto-note safe display` を開く
6. GUIの `セットアップ` で基本設定を確認する
7. 不足や設定破損がありそうな場合は `自動修復` で基本フォルダ/設定を再作成する
8. 起動、ログイン、問い合わせ前の切り分けが必要な場合は `トラブル診断` を開く
9. `初回` タブまたはヘッダーの `初回チェック` で、導入後の基本確認と初回投稿までの導線を確認する
10. 購入/納品後の確認では `受入チェック` を実行し、必要なら `受入保存` でレポートを残す
11. 販売前の確認では `販売準備` を実行し、必要なら `販売準備保存` で残り確認事項を保存する
12. 初めて触る場合は `スターター一式` で記事一覧、予定、アイデア、投稿キューを試す

標準のインストール先は `%LOCALAPPDATA%\auto-note` です。

CLIで確認する場合は、インストール先で次を実行します。

```powershell
auto-note self-test --project-dir . --create --gui-smoke --report
auto-note first-run --project-dir . --create --gui-smoke --smoke-helper
auto-note acceptance --project-dir . --create --gui-smoke --smoke-helper --report
auto-note commercial-readiness --project-dir . --report
auto-note repair --project-dir .
auto-note repair --project-dir . --apply
auto-note troubleshoot --project-dir .
auto-note quickstart --project-dir .
auto-note starter-pack --project-dir .
auto-note starter-clean --project-dir .
auto-note practice --project-dir . --open
auto-note quickstart --project-dir . --smoke-helper
auto-note gui --project-dir . --smoke
auto-note gui --project-dir . --safe-display
```

## インストールせず試す

ZIPを展開したフォルダで `auto-note-gui.bat` を直接開きます。
文字や行高が潰れて見える場合は、PowerShellで `auto-note-gui.bat --safe-display` を実行します。

## ZIP直下の確認ファイル

- `START_HERE.txt`: 最初に押すファイルと基本の使い方
- `FIRST_RUN_CHECKLIST.txt`: インストール後10分で確認する起動、投稿ヘルパー、バックアップ、問い合わせ一式のチェックリスト
- `BUYER_ACCEPTANCE_CHECKLIST.txt`: 購入者が受け取り後に確認する受入チェックリスト
- `RELEASE_SUMMARY.txt`: バージョン、作成日時、含まれないデータ、確認用ファイル
- `RELEASE_MANIFEST.json`: 同梱ファイル一覧とプライバシーフラグ
- `CHECKSUMS.txt`: 同梱ファイルのSHA-256 checksum

配布ZIPは `auto-note release --verify <zip>` で検証できます。checksumだけでなく、ユーザー記事、`.auto-note`、`.venv`、危険なパスが混ざっていないことも確認し、manifestの概要も表示します。

## インストーラーが行うこと

- アプリ本体を `%LOCALAPPDATA%\auto-note` にコピー
- `articles` と `.auto-note` フォルダを作成
- 既存の記事や設定がある場合は `.auto-note\install-backups` に更新前バックアップを作成
- `.auto-note\install-info.json` にインストール日時、バージョン、更新前バックアップ名を記録
- デスクトップとスタートメニューに `auto-note.lnk` と `auto-note safe display.lnk` を作成
- `.venv` を作成し、GUIに必要な依存関係を準備

既存の `articles` と `.auto-note` は削除しません。

## アンインストール

スタートメニューの `auto-note uninstall`、またはインストール先の `shortcuts\uninstall-auto-note.bat` を実行します。

標準ではアプリ本体、仮想環境、ショートカットだけを削除し、`articles` と `.auto-note` は残します。記事と設定も削除する場合だけ、PowerShellで次を実行します。

```powershell
& "$env:LOCALAPPDATA\auto-note\scripts\uninstall-auto-note.ps1" -RemoveUserData
```
