# Release Candidate Handoff

販売候補版を大きく作り替えず、実機確認と販売者情報の穴埋めへ移るためのメモです。

## 固定点

- `v0.1.0-rc3`: 販売直前チェックと販売スモーク拡張込みの販売候補版
- `v0.1.0-rc2`: UI改善込みの販売候補版
- `v0.1.0-rc1`: 販売前一括チェック追加時点の候補版
- 以後の新機能追加は原則 `v0.2` に回します。

## 実機確認

販売前に、実際に販売者が使うWindows環境で確認します。

```powershell
.\auto-note-gui.bat
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-release.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-release.ps1 -Full
```

確認すること:

- `auto-note.lnk` または `auto-note-gui.bat` でGUIが起動する
- ホームの販売準備で `販売者情報`, `配布ZIP`, `購入者ZIP`, `送付準備` の4工程が読める
- GUIの `販売前一括チェック` から `check-release.ps1 -Full` 相当をバックグラウンド実行でき、`.auto-note\reports\release-check-*.txt` がホームの `直近レポート` に残る
- `noteログイン` が普段使う既定ブラウザで開く
- `診断` タブの `トラブル診断`, `出荷前チェック`, `出荷ZIP作成` が実行できる
- GUIが起動しない場合、エラー内容と `.auto-note\gui-error.log` が残る

## 販売者が埋める項目

GUIの `設定` タブ、または `auto-note commercial-setup` で保存します。

- 販売者/屋号
- 販売ページURL
- 返金方針URL
- サポート連絡先
- 利用条件/商用方針の最終確認
- サポート範囲の確認

これらが未入力でもアプリ自体は動きますが、`販売準備`, `販売ナビ`, `check-release.ps1 -Full` では販売前の警告として残ります。

## 販売直前の証跡

販売ページに掲載または購入者へ送付する前に、GUIまたはCLIで以下を作成します。

```powershell
auto-note commercial-readiness --project-dir . --report
auto-note sales-plan --project-dir . --report
auto-note sales-finalize --project-dir . --strict --gui-smoke
auto-note sales-finalize --project-dir . --send-check --send-check-report
auto-note sales-finalize --project-dir . --delivery-receipt
auto-note sales-launch --project-dir . --report
```

残すもの:

- 配布ZIP
- 販売素材Markdown
- 販売用一式ZIP
- 購入者向けZIP
- 購入者向け送付文
- 購入者送付前チェックレポート
- 販売者向け納品記録
- 販売証跡JSON
- 販売直前チェックリスト
- 販売前一括チェックレポート `release-check-*.txt`

## 止める条件

以下が出た場合は販売せず、該当箇所だけ修正します。

- `check-release.ps1` が失敗する
- GUIが起動しない
- `privacy-audit` がNGを出す
- 購入者向けZIP検証が失敗する
- 送付前チェックがNGを出す
- 販売直前チェックがNGを出す
- 販売者情報や利用条件が未確認のまま本番販売しようとしている

## 次版へ回すもの

RC中は新機能を増やしすぎないようにします。以下は `v0.2` 候補です。

- ホームの販売準備をさらに詳細なタイムラインにする
- 販売ページ向けスクリーンショット生成を自動化する
- 購入者向け初回ウィザードを別画面として磨く
