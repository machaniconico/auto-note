# Support

auto-note のサポート時に確認する情報と、ユーザーに依頼する内容です。

## 最初に確認すること

- `auto-note.lnk` または `auto-note-gui.bat` から起動できるか
- GUIの `診断` タブの `初回チェック` と `セルフテスト保存`、または `auto-note first-run --project-dir . --gui-smoke` と `auto-note self-test --project-dir . --gui-smoke --report` を実行できるか。セルフテストの `launcher health` では `auto-note-gui.bat`、隠しGUIランチャー、ショートカット、起動ログ/復旧導線をまとめて確認できます
- GUIのホーム/初回/診断/ヘルプ/コマンド検索の `受入チェック` と `受入保存`、または `auto-note acceptance --project-dir . --create --gui-smoke --smoke-helper --report` を実行できるか
- GUIのホーム/初回/診断/ヘルプ/コマンド検索の `販売準備` と `販売準備保存`、または `auto-note commercial-readiness --project-dir . --report` を実行できるか
- GUIの `販売ナビ`、または `auto-note sales-plan --project-dir .` で販売前の残タスクを確認できるか
- GUIの `販売素材作成`、または `auto-note sales-materials --project-dir .` で販売ページ文案、納品文、FAQを作成できるか
- GUIの `診断` タブの `E2E確認`、または `auto-note workflow-smoke --project-dir . --report` で一時プロジェクトの簡易E2Eを実行できるか
- GUIのホーム/初回/診断/ヘルプ/コマンド検索の `スターター一式`、または `auto-note starter-pack --project-dir .` でサンプル記事、予定、アイデア、匿名ICSを作成できるか
- GUIのホーム/診断/ヘルプ/コマンド検索の `スターター整理`、または `auto-note starter-clean --project-dir .` で削除候補を確認し、必要時だけ `--apply` でサンプル由来の内容を整理できるか
- GUIの記事タブまたはチェックタブの `改善プラン`、または `auto-note improve .\articles\post.md --project-dir . --report` を実行できるか
- GUIのホーム/診断/ヘルプの `運用サマリー`、または `auto-note overview --project-dir . --report` を実行できるか
- GUIの予定タブまたはコマンド検索の `予定ICS出力`、または `auto-note calendar-export --project-dir .` を実行できるか
- GUIの記事タブ、診断タブ、ヘルプ、コマンド検索の `投稿キュー`、または `auto-note publish-queue --project-dir . --report` を実行できるか
- `auto-note gui --project-dir . --smoke` でGUI初期化だけを確認できるか
- 配布ZIP利用時は `shortcuts\install-auto-note.bat` でインストールできるか
- GUIの `診断` タブで `品質チェック` が実行できるか
- GUIの `ホーム` または `診断` タブで `クイック確認` が実行できるか
- GUIの `練習記事作成`、または `auto-note practice --project-dir . --open` で練習用記事を作成できるか
- GUIの `診断` タブで `出荷前チェック` が実行できるか
- GUIの `診断` タブまたは `ヘルプ` タブで `出荷ZIP作成` が実行できるか
- GUIの `診断` タブで `準備度` が実行できるか
- GUIの `診断` タブで `セットアップ確認` が実行できるか
- GUIの `診断` タブ、`ヘルプ` タブ、コマンド検索の `自動修復`、または `auto-note repair --project-dir .` で基本修復プレビューを確認できるか
- GUIのホーム/診断/ヘルプ/コマンド検索の `トラブル診断`、または `auto-note troubleshoot --project-dir .` で起動ログ、noteログイン、プライバシー監査、最新配布ZIPの状態を確認できるか
- `.auto-note/settings.json` が壊れている場合は、GUIが既定値で起動し、診断の `settings file` とセットアップ確認の `settings readable` にNGが出るか
- `.auto-note/ideas.json` が壊れている場合は、アイデア箱が空として起動し、診断の `ideas file` とセットアップ確認の `ideas readable` にNGが出るか
- GUI操作中にエラーが出た場合は `.auto-note/gui-error.log` が更新されているか。GUIの `診断` / `ヘルプ` / コマンド検索の `GUIログ表示` で内容を確認し、`GUIログコピー` で問い合わせ用にコピーし、`GUIログ場所` で保存フォルダを開けます。復旧セットを実行した後は `最新復旧レポート` で内容を確認し、`復旧レポートコピー` で共有用にコピーできます
- GUIのホームにある `直近レポート` で、問い合わせ一式ZIP、復旧レポート、診断ZIP、配布ZIP、投稿キューレポートの最新ファイルの状態を確認し、表示、保存場所、パスコピーを使えるか
- note.com へのログインは普段使っているブラウザでできるか
- 記事ファイルが `articles` フォルダにあるか

## ユーザーに送ってもらうもの

1. GUIの `問い合わせ一式` で作成したzip（トップ階層の `GUI_LOG_SUMMARY.txt` に最新GUIログ要約が入り、GUIの `ZIPログ要約` でも確認できます）
2. GUIの `診断プレビュー` 画面の内容
3. GUIの `問い合わせ作成` で作成したMarkdown
4. GUIの `診断レポート` で作成したzip（`診断ZIP検証` で送付前に確認し、`診断ZIP場所` で保存場所を開き、`診断ZIPパス` で絶対パスをコピーできます）
5. GUIの `セルフテスト保存` で作成した `.auto-note/reports/self-test-*.txt`
6. GUIの `受入保存` で作成した `.auto-note/reports/acceptance-*.txt`
7. GUIの `販売準備保存` で作成した `.auto-note/reports/commercial-readiness-*.txt`
8. GUIの `復旧セット` またはCLIの `auto-note recovery-kit --project-dir . --report` で作成した `.auto-note/reports/recovery-kit-*.txt`
9. 問題が起きた操作手順
10. 表示されたエラーメッセージ

迷った場合は、GUIホームの `直近レポート` で最新の問い合わせ一式ZIP、復旧レポート、診断ZIPを確認し、必要なものだけ表示またはパスコピーして送付してください。診断ZIPだけを送る場合は、GUIの `診断ZIP検証` / `診断ZIP場所` / `診断ZIPパス` から直接たどれます。

問い合わせMarkdownには、概要、再現手順、直近の変更、添付物、匿名化状態、診断プレビューが入ります。標準では診断プレビュー内のパス、ユーザー名、メールアドレス、記事タイトル、記事ファイル名を匿名化し、作成直後に送付前のプライバシー監査も表示します。生のパスや設定が必要な場合だけ、信頼できる相手に対して `auto-note support --include-private` を使います。

`auto-note support --bundle` またはGUIの `問い合わせ一式` は、問い合わせMarkdown、最新GUIログ要約 `GUI_LOG_SUMMARY.txt`、診断レポートZIP、送付前チェックリスト `SUPPORT_SEND_CHECKLIST.txt` を1つのzipにまとめます。作成直後にmanifest/checksum検証とプライバシー監査を行い、問題がある場合はGUIではファイルを開かずに結果を表示します。問い合わせ一式ZIPには `SUPPORT_BUNDLE_MANIFEST.json` と `CHECKSUMS.txt` も入り、GUIの `一式ZIP検証` または `auto-note support --verify <zip>` で検証できます。

診断レポートZIPも標準でパス、ユーザー名、メールアドレス、記事タイトル、記事ファイル名を匿名化します。ZIPには `diagnostics.txt`, `article-index.txt`, `article-review.txt`, `first-run.txt`, `acceptance.txt`, `commercial-readiness.txt`, `sales-plan.txt`, `sales-materials.txt`, `self-test.txt`, `action-plan.txt`, `overview.txt`, `calendar.txt`, `quickstart.txt`, `publish-ready.txt`, `improvement-plan.txt`, `publish-queue.txt`, `gui-smoke.txt`, `preflight.txt`, `troubleshoot.txt`, `settings-summary.txt`, `readiness.txt`, `product-quality.txt`, `quality.txt`, `maintenance-summary.txt` が含まれます。`maintenance-summary.txt` では、セルフテスト保存レポート数、受入チェック保存レポート数、販売準備レポート数、販売素材数、改善プランレポート数、運用サマリーレポート数、予定ICS数、投稿キューレポート数、E2E確認レポート数、プライバシー監査NG生成物の整理候補数も確認できます。

## ログと生成物

- `.auto-note/gui-error.log`: GUI起動ログと操作中エラー
- `.auto-note/diagnostics`: 診断レポート
- `.auto-note/support`: 問い合わせテンプレート。GUI起動失敗時は、可能なら問い合わせ一式ZIPも自動作成されます。
- `.auto-note/backups`: バックアップ
- `.auto-note/install-info.json`: インストール/更新記録
- `.auto-note/install-backups`: インストール/更新前バックアップ
- `.auto-note/autosaves`: GUI編集中の未保存Markdown退避
- `.auto-note/history`: GUI保存前のMarkdown履歴
- `.auto-note/reports`: 記事一覧CSV、セルフテスト保存レポート、受入チェック保存レポート、販売準備レポート、復旧レポート、改善プランレポート、運用サマリーレポート、予定ICS、投稿キューレポート、E2E確認レポート
- `.auto-note/reports/acceptance-*.txt`: 購入/納品後の受入チェック結果
- `.auto-note/reports/commercial-readiness-*.txt`: 販売前の配布ZIP、監査、受入証跡、文書、連絡先、インストール導線の確認結果
- `.auto-note/reports/recovery-kit-*.txt`: 復旧セットの実行結果。GUIの `最新復旧レポート` / `復旧レポートコピー` / `復旧レポート場所` から確認できます。
- `.auto-note/sales/auto-note-sales-materials-*.md`: 販売ページ文案、納品メッセージ、FAQ、サポート範囲、返金方針要約、掲載前チェックリスト
- `.auto-note/reports/improvement-plan-*.txt`: 1記事の改善プラン結果。標準CLI保存では記事タイトルとファイル名を匿名化します。
- `.auto-note/reports/overview-*.txt`: 次に投稿する記事、予定遅れ、古い下書き、公開URL未記録、アイデア箱の運用サマリー。標準CLI/GUI保存では記事タイトルとファイル名を匿名化します。
- `.auto-note/reports/calendar-*.ics`: 公開予定の外部カレンダー取り込み用ICS。標準CLI保存では記事タイトルとファイル名を匿名化します。タイトル入りで作ったICSは送付しないでください。
- `.auto-note/reports/publish-queue-*.txt`: 全記事の投稿キュー結果。標準CLI保存では記事タイトルとファイル名を匿名化します。
- `.auto-note/reports/workflow-smoke-*.txt`: 一時プロジェクトでの簡易E2Eチェック結果
- `.auto-note/releases`: 配布ZIP
- 診断レポートの `maintenance-summary.txt`: バックアップ、診断ZIP、問い合わせ一式、販売一式、販売素材、セルフテスト保存レポート、受入チェック保存レポート、販売準備レポート、改善プランレポート、運用サマリーレポート、予定ICS、投稿キューレポート、E2E確認レポート、配布ZIP、プライバシー監査NG生成物候補の件数
- `auto-note cleanup --project-dir .`: 古い投稿ヘルパーHTML、診断ZIP、問い合わせ一式、販売一式、販売素材、記事CSV、セルフテスト保存レポート、受入チェック保存レポート、販売準備レポート、改善プランレポート、運用サマリーレポート、予定ICS、投稿キューレポート、E2E確認レポートの整理候補を表示
- `auto-note support --project-dir .`: 問い合わせテンプレートを作成
- `auto-note support --project-dir . --bundle`: 問い合わせテンプレートと診断レポートZIPを1つにまとめる
- `auto-note support --verify <zip>`: 問い合わせ一式ZIPのmanifest/checksumを検証
- `auto-note privacy-audit --project-dir .`: 最新の診断ZIP、セルフテスト保存レポート、受入チェック保存レポート、販売準備レポート、改善プランレポート、運用サマリーレポート、予定ICS、投稿キューレポート、E2E確認レポート、問い合わせMarkdown、問い合わせ一式ZIP、配布ZIPに生の個人情報/記事情報が残っていないか確認
- `auto-note privacy-audit --project-dir . --all`: 古い生成物も含めて監査。NGが古い生成物なら `auto-note cleanup --project-dir . --privacy-failed --include-releases` で該当候補だけを確認
- `auto-note cleanup --project-dir . --privacy-failed --apply`: プレビューで確認したプライバシーNG生成物だけを削除。配布ZIPも対象にする場合は `--include-releases` を追加
- `auto-note version --project-dir .`: バージョンと環境概要を表示
- `auto-note first-run --project-dir . --gui-smoke`: 導入後10分の確認項目を順番に表示
- `auto-note acceptance --project-dir . --create --gui-smoke --smoke-helper --report`: 購入/納品後の受入チェックを保存
- `auto-note commercial-readiness --project-dir . --report`: 販売前の配布ZIP、監査、受入証跡、文書、連絡先、インストール導線を確認して保存
- `auto-note sales-plan --project-dir .`: 販売前に残るタスクを優先順、GUI位置、CLIコマンド付きで確認
- `auto-note sales-materials --project-dir .`: 販売ページ文案、納品メッセージ、FAQ、サポート範囲、返金方針要約、掲載前チェックリストをMarkdown生成
- `auto-note self-test --project-dir . --gui-smoke --report`: 導入後の基本動作、次アクション、プライバシー監査、GUI初期化をまとめて確認して保存
- `auto-note workflow-smoke --project-dir . --report`: 一時プロジェクトで練習記事、公開前チェック、記事レビュー、投稿準備、投稿ヘルパーHTML生成、バックアップまでを確認して保存
- `auto-note quickstart --project-dir .`: 初回投稿までの導線を確認
- `auto-note starter-pack --project-dir .`: サンプル記事3本、アイデア1件、匿名の予定ICSを作成
- `auto-note starter-clean --project-dir .`: スターター由来の記事と未使用アイデアの削除候補を表示。削除する場合は `--apply` を追加
- `auto-note practice --project-dir . --open`: 投稿ヘルパー確認用の練習記事を作成
- `auto-note quickstart --project-dir . --smoke-helper`: ブラウザを開かずに投稿ヘルパーHTML生成まで確認
- `auto-note gui --project-dir . --smoke`: GUIを表示せず、初期化途中で落ちないか確認
- `auto-note troubleshoot --project-dir .`: セットアップ、GUIログ、noteログイン詰まり、プライバシー監査、最新配布ZIPをまとめて確認
- `auto-note readiness --project-dir .`: 準備度スコアと次の対応を表示
- `auto-note preflight --project-dir .`: 販売/配布前の総合チェックを表示。トラブル診断を含め、記事レビューは通常INFOとして表示
- `auto-note preflight --project-dir . --gui-smoke`: 総合チェックにGUI初期化スモークを含める
- `auto-note preflight --project-dir . --content-strict`: 記事レビューの改善項目も警告扱いで確認
- `auto-note preflight --project-dir . --create-release`: 総合チェック、新しい配布ZIP作成、checksum検証をまとめて実行
- `auto-note preflight --project-dir . --create-release --install-smoke`: 一時フォルダでインストール/更新/アンインストールも確認
- `auto-note review .\articles`: 記事レビューのスコアと改善項目を表示
- `auto-note improve .\articles\post.md --project-dir . --report`: 1記事の必須修正、仕上げ、投稿前確認を匿名化レポートとして保存
- `auto-note overview --project-dir . --report`: 次の投稿、公開予定、古い下書き、公開URL未記録、アイデア箱を匿名化レポートとして保存
- `auto-note calendar-export --project-dir .`: 公開予定を匿名ICSとして保存
- `auto-note calendar-export --project-dir . --include-private`: 自分の外部カレンダー用に記事タイトル入りICSを保存
- `auto-note publish-ready .\articles\post.md --smoke-helper`: 1記事の投稿準備、記事レビュー、工程状態、投稿ヘルパー生成をまとめて確認
- `auto-note publish-queue --project-dir . --report`: 全記事の投稿可否と次アクションを匿名化レポートとして保存
- `auto-note quality --product-only`: ユーザー記事を除いたアプリ/配布物の品質だけを表示
- `auto-note release --verify .\.auto-note\releases\<release-file>.zip`: 配布ZIPのchecksum、manifest、不要データ混入を検証
- `auto-note setup --project-dir . --create`: 初回セットアップ状態を確認し、壊れた `settings.json` や `ideas.json` を `.auto-note\*.invalid-*.json` に退避してから既定値で書き直す
- `auto-note repair --project-dir .`: 基本フォルダ/設定/アイデア保存の修復プレビューと、プライバシー監査NG生成物候補を表示。配布ZIPまで含める場合は `--include-releases` を追加
- `auto-note repair --project-dir . --apply`: 記事本文を変更せず、基本フォルダ/設定/アイデア保存を再作成
- `auto-note backup --inspect <zip>`: バックアップZIPの復元対象と危険な項目を確認
- `auto-note backup --restore <zip>`: 記事、設定、アイデアを復元
- `shortcuts/install-image-tools.bat`: 画像最適化用Pillowをインストール
- `shortcuts/install-auto-note.bat`: ローカルインストールとショートカット作成
- `shortcuts/uninstall-auto-note.bat`: ユーザーデータを残してアプリ本体を削除

## サポート範囲

- Markdown記事の作成、チェック、コピー補助
- note投稿画面への手動貼り付け補助
- GUI起動、GUI操作中エラーのログ確認、ローカルインストール/アンインストール、設定、バックアップ、診断、配布ZIP作成
- 基本フォルダ、設定、アイデア保存の安全な自動修復
- 起動、ログイン、問い合わせ前のトラブル診断
- バックアップ内容の確認と、バックアップからの記事、設定、アイデア復元
- 古い投稿ヘルパーHTML、診断ZIP、問い合わせ一式、記事CSV、セルフテスト保存レポート、受入チェック保存レポート、販売準備レポート、改善プランレポート、運用サマリーレポート、予定ICS、投稿キューレポート、E2E確認レポートの整理
- 保存履歴の確認とCLI復元
- 自動退避の確認、復元、削除
- 画像取り込みと画像参照チェック
- 初回デモ用スターター記事、予定、アイデア、匿名ICSの作成と、スターター由来データの安全な整理
- 任意依存のPillowを使った画像最適化

## サポート範囲外

- note.com 側の仕様変更そのもの
- note.com のログイン制限、二要素認証、CAPTCHA の解除
- 非公式APIやログイン回避を使った自動投稿
