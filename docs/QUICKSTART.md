# Quickstart

auto-noteを初めて使う時の最短手順です。

## 購入/納品後の最初の3分

1. 配布ZIPを展開し、`shortcuts\install-auto-note.bat` を実行する
2. デスクトップまたはスタートメニューの `auto-note.lnk` を開く
3. 文字や行高が潰れて見える場合は `auto-note safe display.lnk` を開く
4. ホームまたは `初回` タブの `受入チェック` を実行し、NGがないことを確認する
5. 見え方の相談が必要な場合は `表示診断` / `表示診断コピー` と `問い合わせ一式` を作る
6. 投稿時は `投稿ヘルパー` からコピーし、普段使うブラウザのnote投稿画面へ貼り付ける

## GUIで始める

1. `auto-note.lnk` を開く
2. セットアップウィザードで既定タグと投稿設定を確認する
3. 不足や設定破損がありそうな場合は `自動修復` で基本フォルダ/設定を安全に再作成する
4. 起動、ログイン、問い合わせ前の切り分けが必要な場合は `トラブル診断` を開く
5. `初回` タブの `初回チェック` で、スコアと次の操作を確認する
6. 購入/納品後の確認では `受入チェック` を実行し、必要なら `受入保存` でレポートを残す
7. 販売前の確認では `設定` タブで販売者情報と最終確認チェックを保存してから `販売準備` を実行し、必要なら `販売準備保存` で残り確認事項を保存する
8. 販売前に迷ったら `販売ナビ` で、残タスク、GUI位置、CLIコマンドを優先順で確認する
9. 販売ページを書く時は `販売素材作成` で、販売文案、納品文、FAQ、サポート方針のMarkdownを作る
10. 販売直前は `販売一式作成` で、最新配布ZIP、販売準備、監査、検証結果、購入者向け納品文をまとめる
11. 初めて触る場合は `スターター一式` で、サンプル記事、予定、アイデア、匿名ICSを作る
12. ホームの `運用サマリー` と `優先アクション` で上位項目を確認し、`選択を実行` または `CLIコピー` で次の操作へ進む
13. 本番記事を書く場合は `新規記事`、単発で練習する場合は `練習記事作成` で記事を作成する
14. 記事を書いたら記事タブの `改善プラン` と `投稿準備` パネルで修正順、`READY` / `CHECK` / `BLOCKED`、次アクションを確認し、複数記事がある時は `投稿キュー` で投稿できる順に見る
15. `投稿ヘルパー` を開き、投稿前チェックの確認ダイアログを通してから、普段使うブラウザのnote投稿画面へ貼り付ける
16. 公開後に記事の公開URLを保存し、必要ならバックアップを作成する

## CLIで確認する

```powershell
auto-note setup --project-dir . --create
auto-note repair --project-dir .
auto-note repair --project-dir . --apply
auto-note troubleshoot --project-dir .
auto-note first-run --project-dir . --create
auto-note acceptance --project-dir . --create --smoke-helper --report
auto-note commercial-setup --project-dir . --seller-name "Your Shop" --sales-url "https://example.com" --refund-url "https://example.com/refund" --support-contact "https://example.com/support" --terms-reviewed --support-scope-confirmed
auto-note commercial-readiness --project-dir . --report
auto-note sales-plan --project-dir .
auto-note sales-materials --project-dir .
auto-note sales-handoff --project-dir .
auto-note quickstart --project-dir .
auto-note starter-pack --project-dir .
auto-note starter-clean --project-dir .
auto-note practice --project-dir . --open
auto-note workflow-smoke --project-dir . --report
auto-note quickstart --project-dir . --smoke-helper
auto-note new "記事タイトル" --tag note --open
auto-note overview --project-dir . --report
auto-note check .\articles --append-tags
auto-note review .\articles --append-tags
auto-note improve .\articles\post.md --append-tags --report
auto-note publish-ready .\articles\post.md --append-tags --smoke-helper
auto-note publish-queue --project-dir . --report
auto-note calendar-export --project-dir .
```

`auto-note first-run` は導入後10分の確認を、セットアップ、セルフテスト保存、最初の記事、投稿ヘルパー、バックアップ、問い合わせ一式の順番で表示します。GUIでは `初回` タブで同じ項目を確認し、その場で次の操作へ進めます。

`auto-note acceptance --project-dir . --create --smoke-helper --report` は、購入/納品後の受入確認を1枚のテキストレポートに保存します。GUIではホーム、初回、診断、ヘルプ、コマンド検索の `受入チェック` / `受入保存` から実行できます。

`auto-note commercial-setup --project-dir .` は、販売者/屋号、販売ページURL、返金方針URL、サポート連絡先、利用条件/商用方針レビュー、サポート範囲確認を保存します。GUIでは `設定` タブから編集できます。

`auto-note commercial-readiness --project-dir . --report` は、販売前に配布ZIP、プライバシー監査、受入チェック証跡、販売者プロフィール、販売文書、利用条件/商用方針、販売最終確認、サポート連絡先、インストール導線をまとめて確認します。GUIではホーム、初回、診断、ヘルプ、コマンド検索の `販売準備` / `販売準備保存` から実行できます。

`auto-note sales-plan --project-dir .` は、販売前に残る作業を優先順に並べ、GUIで押す場所とCLIコマンドを一緒に表示します。GUIでは `販売ナビ` から同じ内容を確認できます。

`auto-note sales-materials --project-dir .` は、販売ページ文案、納品メッセージ、FAQ、サポート範囲、返金方針要約、掲載前チェックリストを `.auto-note\sales` のMarkdownに生成します。GUIでは `販売素材作成` から同じ内容を作成できます。

`auto-note sales-handoff --project-dir .` は、最新の配布ZIP、販売準備レポート、プライバシー監査、配布ZIP検証結果、購入者向け納品文、販売者最終チェックリスト、サポート返信テンプレを `.auto-note\sales` の販売用一式ZIPにまとめます。購入者にはZIP内の `release\auto-note-release-*.zip` を渡し、販売用一式ZIPは販売者側の証跡として保管します。

`auto-note repair --project-dir .` は、基本フォルダ、設定、アイデア保存の修復プレビューと、プライバシー監査NG生成物候補を表示します。基本修復を実行する場合だけ `--apply` を付けます。記事本文は変更しません。古い配布ZIPまで整理候補に含める時だけ `--include-releases` を追加します。

`auto-note troubleshoot --project-dir .` は、セットアップ、GUIエラーログ、noteログイン詰まり、最新生成物のプライバシー監査、危険生成物候補、最新配布ZIPをまとめて確認します。困った時に最初に実行し、修復や問い合わせ一式作成へ進むか判断できます。

`auto-note starter-pack --project-dir .` は、サンプル記事3本、アイデア1件、匿名の予定ICSを作ります。既存の記事は上書きせず、二回目以降は既存スターター記事をスキップします。初回デモでは、これを作ってから運用サマリー、投稿キュー、予定タブを見ると、主要機能の価値がすぐわかります。

スターターを片付ける場合は `auto-note starter-clean --project-dir .` で削除候補を確認し、問題なければ `--apply` を付けます。通常の記事や昇格済みアイデアは対象外です。GUIでは `スターター整理` から同じ操作ができます。

GUIのホームに出る `優先アクション` は投稿キューも見ています。`投稿キューの先頭記事を直す` が出た場合は、`選択を実行` で対象記事と投稿準備パネルへ移動できます。

日々の確認には `auto-note overview --project-dir .` を使います。次に投稿する記事、期限超過の公開予定、古い下書き、公開URL未記録、アイデア箱をまとめて確認でき、`--report` で匿名化済みレポートを保存できます。

公開予定を外部カレンダーへ入れる場合は `auto-note calendar-export --project-dir .` を使います。標準では記事タイトルとファイル名を匿名化した `.ics` を `.auto-note\reports` に保存します。自分のGoogle/Outlookカレンダー用にタイトル入りで取り込む場合だけ `--include-private` を付けます。GUIでは `予定` タブの `ICS出力`、またはコマンド検索の `予定ICS出力` から実行できます。

`auto-note quickstart` は初回投稿までの導線を確認します。

- セットアップ状態
- 最初の記事の有無
- 記事の基本チェック
- 記事レビュー
- 投稿ヘルパーHTMLを生成できる状態か
- noteログイン導線
- バックアップの有無

`--smoke-helper` を付けると、ブラウザを開かずに `.auto-note\quickstart` へ投稿ヘルパーHTMLを生成します。

`auto-note workflow-smoke --report` は、一時プロジェクトで練習記事作成から投稿準備、投稿ヘルパーHTML生成、バックアップまでをまとめて確認し、結果を `.auto-note\reports` に保存します。GUIでは診断タブの `E2E確認` から実行できます。

特定の記事を仕上げる場合は `auto-note improve <file>` を使います。必須修正、仕上げ、投稿前確認をおすすめ順に並べ、`--report` で匿名化済みの改善プランを `.auto-note\reports` に保存できます。

投稿直前に確認する場合は `auto-note publish-ready <file>` を使います。チェック、記事レビュー、工程状態、投稿ヘルパーHTML生成確認を1つのレポートで見られ、`--mark-ready` を付けるとNGがない場合だけ状態を `ready` に更新できます。

複数の記事から次に投稿するものを選ぶ場合は `auto-note publish-queue --project-dir .` を使います。`POSTABLE` / `CHECK` / `BLOCKED` / `DONE` に分けて表示し、`--report` で保存するレポートは標準で記事タイトルとファイル名を匿名化します。

GUIでは記事タブで記事を選ぶだけで `投稿準備` パネルが更新されます。`改善プラン` を押すと、直す順番と所要時間の目安をチェックタブに表示します。項目を選んで `次を実行` すると、チェック、レビュー、HTML確認、準備OK化など、その項目に合う操作へ進めます。`チェック` タブのレビュー一覧からも `記事を編集`、`改善プラン`、`投稿準備`、`準備OKにする` に進めます。

## ログインで弾かれる場合

自動操作ブラウザで `安全ではない可能性がある` と表示される場合は、普段使っているChromeやEdgeでnote.comにログインし、auto-noteの投稿ヘルパーからコピーして貼り付けてください。ログイン回避や非公式APIは使いません。
