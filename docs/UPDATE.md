# Update

auto-note の更新手順です。

## 推奨手順

1. GUIの `ヘルプ` で `アプリ情報` を開き、現在のバージョンを確認する
2. 必要なら `診断` の `バックアップ作成` でバックアップを作成する
3. 新しい配布ZIPを展開する
4. 展開先の `shortcuts\install-auto-note.bat` を実行する
5. デスクトップまたはスタートメニューの `auto-note` を開く
6. 文字や行高が潰れて見える場合は `auto-note safe display` を開く
7. `ヘルプ` の `アプリ情報` でバージョンを確認する

インストーラーは既存の `articles` と `.auto-note` を削除しません。既存の記事や設定がある場合は、更新前に `.auto-note\install-backups` へバックアップを作成し、`.auto-note\install-info.json` に記録します。

## CLIで確認する

```powershell
auto-note version --project-dir .
auto-note backup --project-dir .
auto-note backup --inspect .\.auto-note\backups\<backup-file>.zip
```

## ロールバック

更新後に問題が起きた場合は、古い配布ZIPを展開して `shortcuts\install-auto-note.bat` を実行します。記事ファイルは残りますが、念のため更新前にバックアップを作成してください。

記事や設定をバックアップZIPから戻す場合は、先にGUIの `診断 > バックアップ確認`、または `auto-note backup --inspect` で復元対象を確認してください。

復元はGUIの `診断 > バックアップ復元`、または次のCLIを使います。復元前には現在状態の安全バックアップが作成されます。

```powershell
auto-note backup --inspect .\.auto-note\backups\<backup-file>.zip
auto-note backup --restore .\.auto-note\backups\<backup-file>.zip
```

## サポートに送るもの

```powershell
auto-note support --project-dir . --bundle
auto-note diagnose --preview
```
