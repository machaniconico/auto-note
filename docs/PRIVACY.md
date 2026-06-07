# Privacy

auto-note は、記事データをローカルのプロジェクトフォルダ内で扱います。

## 保存する主なデータ

- `articles`: Markdown記事
- `.auto-note/settings.json`: GUI設定
- `.auto-note/settings.invalid-*.json`: 壊れた設定を修復する前の退避コピー
- `.auto-note/ideas.json`: アイデア
- `.auto-note/ideas.invalid-*.json`: 壊れたアイデアデータを修復する前の退避コピー
- `.auto-note/autosaves`: GUI編集中の未保存Markdown退避
- `.auto-note/backups`: バックアップZIP
- `.auto-note/install-info.json`: インストール日時、バージョン、更新前バックアップ名
- `.auto-note/install-backups`: インストール/更新前の安全バックアップZIP
- `.auto-note/diagnostics`: 診断レポートZIP
- `.auto-note/support`: 問い合わせテンプレートMarkdown
- `.auto-note/history`: GUI保存前のMarkdown履歴
- `.auto-note/reports`: 記事一覧CSV、セルフテスト保存レポート、受入チェック保存レポート、販売準備レポート、改善プランレポート、運用サマリーレポート、予定ICS、投稿キューレポート、E2E確認レポート
- `.auto-note/releases`: 配布ZIP
- `.auto-note/sales`: 販売用一式ZIP、購入者向け送付文、送付前チェックレポート、販売者向け納品記録、販売方針レビュー

## 診断レポート

`auto-note diagnose --report` とGUIの `診断レポート` は、標準で次の情報を隠します。

- プロジェクトの絶対パス
- ホームフォルダ名とユーザー名
- メールアドレス
- 記事タイトルと記事ファイル名

診断ZIPには、環境診断、記事インデックス、記事レビュー、改善プラン、運用サマリー、公開予定、初回チェック、受入チェック、販売準備、セルフテスト、クイックスタート確認、最新記事の投稿準備レポート、GUI起動スモーク、出荷前チェック、トラブル診断、設定概要、準備度、製品品質、品質チェック、保守一覧、GUIログが入ります。標準モードでは、記事レビュー、改善プラン、運用サマリー、公開予定、初回チェック、受入チェック、販売準備、セルフテスト、クイックスタート確認、投稿準備レポートのファイル名、タイトル、タグ名、GUI起動スモーク、出荷前チェック、トラブル診断、準備度、製品品質、品質チェック、保守一覧、GUIログ内のパスも匿名化します。

詳細な生データが必要な場合のみ、信頼できる相手に対して `--include-private` を使います。

送付前に `auto-note privacy-audit --project-dir .`、またはGUIの `プライバシー監査` を実行すると、最新の診断ZIP、セルフテスト保存レポート、受入チェック保存レポート、販売準備レポート、販売方針レビュー、改善プランレポート、運用サマリーレポート、予定ICS、投稿キューレポート、E2E確認レポート、問い合わせMarkdown、問い合わせ一式ZIP、販売用一式ZIP、購入者向け送付文、送付前チェックレポート、販売者向け納品記録、配布ZIPに生のパス、ユーザー名、記事ファイル名、記事タイトル、メールアドレスが残っていないか確認できます。古い生成物もまとめて確認する場合は `--all` を使います。

`seller-delivery-receipt-*.txt` は販売者専用の注文記録です。注文IDや購入者表示名を追記した場合は、問い合わせ一式や購入者向け送付物には含めず、販売者側の注文管理記録として保管してください。

`commercial-policy-review-*.txt` は返金/キャンセル条件、ライセンス/利用条件、サポート範囲、送付前証跡を確認する販売者専用メモです。販売ページや注文情報を追記した場合は、購入者向けZIPや問い合わせ一式には含めず、販売者側だけで保管してください。

## 予定ICS

`auto-note calendar-export` とGUIの `予定ICS出力` は、公開予定を `.auto-note/reports/calendar-*.ics` に保存します。CLIの標準出力は記事タイトルとファイル名を匿名化します。自分のカレンダーに取り込むためタイトル入りで保存した場合は、そのICSを外部共有しないでください。タイトル入りICSは `privacy-audit` の対象になるため、送付前の確認で検出できます。

## 問い合わせテンプレート

`auto-note support` とGUIの `問い合わせ作成` は、`.auto-note/support` に問い合わせ用Markdownを作成します。標準では診断プレビューを匿名化した状態で埋め込みます。`auto-note support --bundle` とGUIの `問い合わせ一式` は、問い合わせMarkdownと診断レポートZIPを1つのzipにまとめ、manifest/checksumも同梱します。

送付前に本文を確認し、記事本文、個人名、メールアドレス、購入情報など、問い合わせに不要な情報が入っていないか確認してください。

生のパスや記事名が必要な調査の場合だけ、信頼できる相手に対して `auto-note support --include-private` を使います。

## note.com との関係

通常の投稿導線では、普段使っているブラウザで note.com を開き、ローカルヘルパーからコピーして貼り付けます。note.com のパスワードや認証情報を auto-note に保存する設計ではありません。

## 配布ZIP

`auto-note release` で作成する配布ZIPには、ユーザー記事、`.auto-note`、`.venv`、生成ヘルパーを含めません。`auto-note release --verify <zip>` は、checksumに加えてこれらの混入がないことも確認します。

## 画像最適化

画像最適化は任意依存の Pillow を使います。処理はローカルで行われ、画像を外部サービスへ送信しません。
