# auto-note

Markdown ファイルから note 投稿作業を半自動化するツールです。

note 公式ヘルプでは、2025-05-08 更新時点で公式公開 API は提供されていないと案内されています。そのため、通常利用は未公開 API やログイン回避ではなく、普段のブラウザで note を開き、ローカルのコピー用ヘルパーから貼り付ける方式にしています。

## まず使うファイル

基本は `auto-note.lnk` だけ使えば大丈夫です。ダブルクリックすると、スターター一式、記事作成、フォルダを開く、公開前チェック、改善プラン、投稿準備、投稿キュー、運用サマリー、ダッシュボード、投稿ヘルパー、noteログイン、予定管理、予定ICS出力、アイデア箱、復旧セット、自動修復、トラブル診断、受入チェック、販売準備、販売用一式、販売直前チェックを一画面で操作できます。初回は `セットアップ` と `初回チェック`、購入/納品後の確認は `受入チェック`、起動や設定で詰まった時は `復旧セット`、販売前の最終確認は `販売準備`、販売直前の目視証跡は `販売直前` / `直前保存`、迷った時は `コマンド` または `Ctrl+K` から主要操作を検索できます。

トップ直下の起動ファイルはこの3つです。

- `auto-note.lnk`: アイコン付きGUIショートカット
- `auto-note-gui.bat`: GUIショートカットの実体
- `auto-note GUI.lnk`: 互換用のアイコン付きGUIショートカット

`auto-note.lnk` はコンソールを出さずにGUIを起動します。起動前にGUI初期化スモークを実行し、GUIが起動しない場合だけ、エラー内容、ログ位置、復旧レポート、問い合わせ一式ZIPの場所/作成コマンドをメッセージ表示します。可能な場合は `.auto-note\reports\recovery-kit-*.txt` と `.auto-note\support` の問い合わせ一式ZIPも自動作成します。ログは `.auto-note\gui-error.log` にも残ります。
GUI操作中にエラーが出た場合も、画面には `GUIログ表示`、`復旧セット`、`問い合わせ一式` の次アクションを表示します。`Ctrl+K` のコマンド検索から同じ操作をすぐ開けます。
ホームの `復旧ステータス` でも最新GUIログの有無、更新時刻、サイズを確認でき、`GUIログ表示`、`復旧セット`、`問い合わせ一式` へ直接進めます。

配布ZIPから使う場合は、展開後に `shortcuts\install-auto-note.bat` を実行すると、管理者権限なしで `%LOCALAPPDATA%\auto-note` に配置し、デスクトップとスタートメニューに `auto-note` ショートカットを作成します。インストールせずに試す場合は `auto-note-gui.bat` を直接開けます。アンインストールは `shortcuts\uninstall-auto-note.bat` から実行でき、標準では記事と設定を残します。

GUIは9つのタブに分かれています。ホームには準備度、次の一手、初回/復旧、販売/送付を1行で見られるコンパクト概要、作業進行レーン、初回セットアップのスコアと次項目、アクションプランの最優先項目、上位の優先アクション一覧、直近レポートが表示され、`実行` / `選択を実行` でその操作へ直接進めます。作業進行レーンの各工程の `開く` から、初回、記事、仕上げ、投稿、販売、サポートの該当画面へ直接移動できます。`初回セットアップ` の `初回を開く` では、初回チェックの未完了項目を選んだ状態で確認できます。ホームの `販売準備` には `購入者送付` の状態も表示され、購入者ZIP、送付文、送付記録、送付文と最新ZIP名/SHA-256の照合結果、送付記録と最新ZIP/送付文の照合結果を確認できます。状態に応じた購入者送付ボタンから、ZIP作成、送付文作成、送付記録、最終レビュー、販売直前チェックへ直接進めます。ヘッダーの `コマンド` または `Ctrl+K` からも `作業進行: 初回` などで各工程へ移動でき、検索結果の件数と一致するコマンドがない時の案内も表示します。`投稿 準備` のようにスペース区切りの複数語でも探せ、上下キーで候補を選び、Enterで実行できます。必要な時は選択中のCLIもコピーでき、直近レポートでは問い合わせZIP、復旧レポート、診断ZIP、配布ZIP、購入者ZIP、購入者送付文、送付記録、販売直前チェック、投稿キューなどの最新ファイルの状態を見ながら、表示、保存場所の確認、パスコピーができます。

- `ホーム`: 今日の状態、初回/記事/仕上げ/投稿/販売/サポートを横断する作業進行、初回セットアップのスコアと次項目、優先アクション一覧、購入者送付ファイルまで開ける直近レポート、購入者ZIP/送付文/送付記録まで見える販売準備サマリー、スターター一式、運用サマリー、次の作業、公開予定の概要
- `初回`: 導入直後の準備状態、初回チェックと受入チェックのスコア、要対応だけ表示、項目別の次アクション
- `記事`: 表形式の記事一覧、検索/状態フィルター、選択記事フォーカス、改善プラン、投稿準備パネル、投稿キュー、投稿ヘルパー、コピー、本文編集、メタ編集、画像挿入、保存履歴、自動退避、状態/予定/公開URL管理
- `アイデア`: ネタの追加、一覧、記事化
- `予定`: 工程一覧、公開予定の確認、Google/Outlook向け予定ICS出力
- `チェック`: 記事レビュー一覧、スコア、修正/改善項目、レビュー詳細からの本文編集/改善プラン/投稿準備、選択記事または全体の公開前チェック、投稿準備
- `設定`: 既定タグ、既定状態、表示サイズ、投稿ヘルパーの挙動、販売者情報チェックリスト、販売前の最終確認
- `診断`: 初回チェック、受入チェック、販売準備、販売用一式、販売直前チェック、運用サマリー、環境チェック、復旧セット、自動修復、トラブル診断、出荷前チェック、出荷ZIP作成、ログ表示、GUIログ場所、バックアップ、診断レポート、診断ZIP検証、診断ZIP場所、診断ZIPパス、配布ZIP作成
- `ヘルプ`: README、サポート文書、プライバシー文書、アプリ情報、初回チェック、受入チェック、販売準備、問い合わせテンプレート、診断レポート、診断ZIP検証、診断ZIP場所、診断ZIPパス、出荷ZIP、配布ZIP、保守フォルダへの導線

記事一覧は `下書き`, `準備OK`, `予定あり`, `公開済み` の状態ごとに色分けされ、`確認` 列で公開前チェックのOK/警告/NGを見られます。記事を選ぶと `選択記事フォーカス` にレビュー点数、投稿前判定、修正件数、目安時間、次に直す内容が表示され、そのまま改善プラン、投稿準備、HTML確認へ進めます。`投稿準備` パネルには `READY` / `CHECK` / `BLOCKED`、項目別の状態、次アクションが表示され、`改善プラン` では必須修正、仕上げ、投稿前確認をおすすめ順で確認できます。`次を実行` からチェック、レビュー、HTML確認、準備OK化へ進めます。`投稿キュー` は全記事を投稿できる順に並べ、どれを次に仕上げるかを一覧できます。投稿ヘルパーを開く前には投稿前チェックが走り、NGや確認項目がある場合は確認ダイアログで止められます。チェックタブでは記事ごとのレビュー点数、修正/改善件数、具体的な次アクションを一覧でき、レビュー詳細の `本文を編集` から該当記事の編集タブへ直接移動できます。画面下部には、コピーや保存などの結果が通知として表示されます。

主なショートカット:

- `Ctrl+N`: 新規記事
- `Ctrl+S`: 編集中の記事を保存
- `Ctrl+K`: コマンド検索
- `F5`: 更新
- `Ctrl+Enter`: 投稿ヘルパー
- `Ctrl+Shift+C`: 本文コピー

## 安心機能

- 設定は `.auto-note\settings.json` に保存されます。
- GUIは読みやすさ優先の `ゆったり` 表示で起動し、日本語が潰れにくい Meiryo UI 優先、DPIぼけを抑える表示設定、広めの行高/ボタン高にしています。文字や行高が潰れて見える場合は、ヘッダーの `表示` で `大きめ` を選ぶとすぐ拡大できます。`Ctrl+K` から `表示サイズ: 大きめ` を実行することもできます。表示やウィンドウ位置が扱いにくい時はヘッダーの `リセット` または `Ctrl+K` の `表示リセット` で既定の見やすい状態に戻せます。細かく選びたい場合は `設定` の `表示サイズ` で `標準` / `ゆったり` / `大きめ` を選んで保存します。見え方の相談時は `診断` の `表示診断`、または `Ctrl+K` の `表示診断` / `表示診断コピー` でフォント、倍率、画面サイズ、可読性判定を確認・コピーできます。
- 初回起動時やヘッダーの `セットアップ` から、セットアップ確認、既定タグ、投稿ヘルパー設定をまとめて確認できます。
- `settings.json` が壊れていても既定値で起動し、`auto-note diagnose`、`auto-note setup --create`、`auto-note repair --apply` で検知/修復できます。修復前の破損設定は `.auto-note\settings.invalid-*.json` に退避されます。
- `ideas.json` が壊れていてもアイデア箱は空として起動し、`auto-note setup --create`、`auto-note repair --apply`、または次のアイデア保存時に `.auto-note\ideas.invalid-*.json` へ退避して修復できます。
- 記事Markdownの新規作成、メタ更新、GUI本文保存、画像挿入は一時ファイル経由で置き換え、保存途中の中途半端なファイルを残しにくくしています。
- バックアップは `.auto-note\backups` にzip形式で作成されます。
- GUI起動ログと操作中エラーは `.auto-note\gui-error.log` に残ります。GUIの `GUIログ表示` / `GUIログコピー` / `GUIログ場所` から確認、コピー、保存フォルダ表示ができます。
- GUIの `問い合わせ一式` で作成したZIPに含まれる表示診断は、ヘルプの `ZIP表示診断` から送付前に確認できます。
- インストール/更新時は `.auto-note\install-info.json` に記録が残り、既存記事や設定がある場合は `.auto-note\install-backups` に更新前バックアップが作られます。
- GUIで編集中の未保存本文は `.auto-note\autosaves` に自動退避されます。保存すると退避は削除され、必要な時は `記事` タブの `自動退避` から復元できます。
- `auto-note diagnose` で環境診断を表示できます。
- `auto-note setup --create` で初回セットアップ状態を確認し、基本フォルダ/設定を作成できます。
- `復旧セット` はGUIの診断、ヘルプ、コマンド検索から実行でき、安全な基本修復、再診断、必要時の問い合わせ一式ZIP作成までを1回で行います。GUI実行時も結果を保存し、`最新復旧レポート` / `復旧レポートコピー` / `復旧レポート場所` から確認できます。GUIが起動しない時は `auto-note recovery-kit --project-dir . --report` でも同じ復旧セットを実行でき、結果は `.auto-note\reports\recovery-kit-*.txt` に残せます。記事や古い生成物は変更/削除しません。
- `auto-note repair` で基本フォルダ/設定/アイデア保存の修復プレビューと、プライバシー監査NG生成物候補を確認できます。`--apply` を付けると基本修復を実行します。削除系は `--cleanup-privacy` や `--cleanup-old` を明示した時だけ対象になります。配布ZIPまで整理候補に含める場合は `--include-releases` も必要です。GUIの診断、ヘルプ、コマンド検索の `自動修復` からも実行できます。
- `auto-note troubleshoot` で、起動ログ、セットアップ、noteログイン詰まり、最新生成物のプライバシー監査、危険生成物候補、最新配布ZIPをまとめて確認できます。GUIのホーム、診断、ヘルプ、コマンド検索の `トラブル診断` からも実行できます。
- `auto-note first-run` で、購入/導入直後に見るべきセットアップ、セルフテスト保存、最初の記事、投稿ヘルパー、バックアップ、問い合わせ一式を順番に確認できます。GUIの `初回` タブでは `要対応だけ` でWARN/NGだけに絞り込めます。記事の仕上げや販売者情報など投稿/販売前のTODOはINFOとして見せ、初回起動確認のWARNと分けて扱います。
- `auto-note acceptance` で、購入/納品後の受入チェックを1枚のレポートにまとめられます。初回チェック、セルフテスト、トラブル診断、投稿ヘルパー、GUI初期化、問い合わせ一式を確認し、`--report` で `.auto-note\reports\acceptance-*.txt` に保存できます。`--full` を付けると、基本セットアップ作成、GUI初期化、投稿ヘルパーHTML生成、レポート保存までまとめて実行します。記事本文の改善提案は投稿前確認として残しつつ、GUI起動や配布物受入のブロッカーとは分けます。GUIのホーム、初回、診断、ヘルプ、コマンド検索の `受入チェック` / `受入保存` / `受入フル保存` からも実行できます。
- `auto-note commercial-setup` で、販売者/屋号、販売ページURL、返金方針URL、サポート連絡先、利用条件/商用方針の最終確認、サポート範囲の確認を `.auto-note\settings.json` に保存できます。未入力項目は項目名付きで表示され、販売ページ/返金方針/サポート連絡先が公開URL形式でない場合やメールアドレス直書きの場合は警告します。GUIの `設定` タブでも同じ項目を編集でき、販売者情報チェックリストで6項目のOK/未入力/確認、現在値の状態、次の操作を一覧できます。`次の不足へ`、`選択項目へ`、またはコマンド検索の `販売者情報へ` で未入力または確認が必要な欄へ移動でき、保存時にも不足/警告件数を通知します。`販売者情報確認` では未保存の入力欄も含めた不足項目、確認事項、次に入力するGUI位置、CLIフラグ、販売素材/販売ナビへの次アクションを診断タブに表示できます。
- `auto-note commercial-setup --project-dir . --template` で、販売者情報、販売ページURL、返金方針、サポート連絡先、販売前確認を埋めるMarkdownテンプレートを `.auto-note\sales` に作成できます。未入力のプレースホルダーが残る場合は直接保存コマンドを出さず、編集後にテンプレート適用する安全な導線を表示します。GUIの `販売者テンプレ` からも実行できます。
- 作成した販売者テンプレートを編集した後は、`auto-note commercial-setup --project-dir . --apply-latest-template` で最新テンプレートの値を設定へ取り込めます。任意のファイルを指定する場合は `--apply-template <path>` を使います。GUIの `テンプレ適用` からも最新テンプレートを取り込めます。テンプレート内の `terms_reviewed` と `support_scope_confirmed` は、利用条件、商用方針、サポート範囲、返金条件を販売ページに合わせて確認してから `yes` にします。
- `auto-note commercial-readiness` で、販売前に見るべき配布ZIP、プライバシー監査、受入チェック証跡、販売者プロフィール、販売文書、利用条件/商用方針、販売最終確認、サポート連絡先、インストール導線を1枚にまとめられます。`--report` で `.auto-note\reports\commercial-readiness-*.txt` に保存でき、GUIのホーム、初回、診断、ヘルプ、コマンド検索の `販売準備` / `販売準備保存` からも実行できます。
- `auto-note commercial-readiness --project-dir . --policy-review` またはGUIの `方針レビュー` で、返金/キャンセル条件、ライセンス/利用条件、サポート範囲、送付前証跡の販売者向け最終確認を `.auto-note\sales\commercial-policy-review-*.txt` に保存できます。このファイルは販売者専用の確認メモとして保管し、購入者向けZIPや問い合わせ一式には含めません。
- `auto-note sales-plan` で、販売前に残っているタスク、最新の配布ZIP/販売用一式ZIP/購入者向けZIP/販売素材のそろい具合を優先順、GUI位置、CLIコマンド付きで確認できます。購入者向けZIPは `Buyer delivery readiness` として検証状態、サイズ、SHA-256を販売者TODOとは別に表示し、`Seller setup remaining`、`Tool/artifact actions remaining`、`Upload guidance` で「販売者が決める残件」と「ツール側の再生成残件」を分けて確認できます。`auto-note sales-plan --project-dir . --report` またはGUIの `販売ナビ保存` で `.auto-note\sales\sales-plan-*.txt` に証跡として保存できます。GUIの `販売ナビ` からも同じ内容を表示できます。
- `auto-note sales-review` で、最新販売素材、販売者設定、購入者向け送付文、購入者ZIP、送付記録を販売ページ/決済後メッセージ目線で照合できます。GUIの `最終レビュー` で表示し、`auto-note sales-review --project-dir . --report` またはGUIの `レビュー保存` で `.auto-note\sales\sales-review-*.txt` に販売者用の最終確認証跡を保存できます。
- `auto-note sales-launch` で、最終レビュー後に販売ページ公開直前の決済後メッセージ、添付ZIP、返金/サポート表示、販売者専用証跡をまとめて確認できます。販売ページURLから note / BOOTH / Gumroad / STORES / 汎用販売ページ向けの目視項目も出し分けます。GUIの `販売直前` で表示し、`auto-note sales-launch --project-dir . --report` またはGUIの `直前保存` で `.auto-note\sales\sales-launch-checklist-*.txt` に販売者専用の目視チェックリストを保存できます。このチェックリストは購入者向けZIPや問い合わせ一式には添付しません。
- `auto-note sales-materials` で、販売ページ文案、購入者の最初の10分、納品メッセージ、FAQ、サポート範囲、返金方針要約、掲載前チェックリストを `.auto-note\sales` のMarkdownに生成できます。`--verify <path> --strict` で未設定の販売者情報や古いZIP名を検出でき、GUIの `販売素材作成` / `販売素材検証` からも実行できます。
- `auto-note sales-handoff` で、最新の配布ZIP、販売素材Markdown、販売準備レポート、プライバシー監査、配布ZIP検証結果、購入者向け納品文、購入者の最初の10分、購入者へ送るもの/販売者が保管するものを分けた納品チェックリスト、販売者向け納品記録テンプレ、販売者最終チェックリスト、サポート返信テンプレを1つの販売用一式ZIPにまとめられます。GUIの診断、ヘルプ、コマンド検索の `販売一式作成` / `販売一式検証` からも実行できます。販売者はこのZIPを証跡として保管します。GUIの `購入者ZIP抽出` または `sales-handoff --project-dir . --extract-buyer <販売一式ZIP>` で、購入者へ送る配布ZIP、`START_HERE_FOR_BUYER.txt`、納品メモ、購入者向けサポートガイド、`BUYER_DELIVERY_MANIFEST.json`、`SHA256SUMS.txt` だけを別フォルダへ取り出し、同時に `auto-note-buyer-delivery-*.zip` を作成できます。GUIの `購入者ZIP検証`、`sales-handoff --project-dir . --verify-buyer <抽出フォルダ>`、`sales-handoff --project-dir . --verify-buyer-package <購入者向けZIP>` で、送付前に余計なファイル混入、配布ZIP破損、最初に読むメモ不足、manifest不一致、チェックサム不一致を確認できます。既存フォルダから作り直す場合は `sales-handoff --project-dir . --package-buyer <抽出フォルダ>` を使います。
- `auto-note sales-finalize` で、新しい配布ZIP、販売者テンプレート、販売素材Markdown、販売用一式ZIP、チェックサム付き購入者向け抽出フォルダ、購入者へそのまま添付できる `auto-note-buyer-delivery-*.zip`、最新ZIP名/サイズ/SHA-256入りの購入者向け送付文、販売ナビレポート、販売者送付前チェックリスト、販売証跡JSONマニフェスト `sales-evidence-manifest-*.json`、受入チェック証跡、診断ZIP、プライバシー監査、最終出荷前チェックを一括作成できます。古い販売一式ZIPが残っていても作り直せます。結果は `.auto-note\sales\sales-finalize-*.txt` に保存され、販売ナビは `.auto-note\sales\sales-plan-*.txt` にも保存され、購入者向けZIP/販売者証跡ZIP/配布ZIPのサイズとSHA-256も残ります。販売者送付前チェックリストでは、購入者へ送るZIP、販売者が保管するZIP、販売ナビ証跡、販売証跡JSON、通常送ってはいけないファイルを確認できます。GUIの `販売一括作成` からも実行できます。GUIの `送付前チェック` では最新送付文、購入者向けZIP、販売者チェックリスト、販売証跡JSONを照合し、GUIの `送付文コピー` では対応ZIPを検証してからクリップボードへコピーできます。GUIの `送付記録` またはCLIの `sales-finalize --project-dir . --delivery-receipt` では、送付前チェック証跡と、注文管理へ控える `seller-delivery-receipt-*.txt` を保存できます。CLIでは `sales-finalize --project-dir . --send-check --send-check-report` で同じ照合だけを行い、`.auto-note\sales\buyer-send-readiness-*.txt` に送付前証跡を保存できます。編集済みの最新販売者テンプレートを先に取り込む場合は `sales-finalize --project-dir . --apply-latest-template`、GUIでは `テンプレ取込一括` を使います。未入力の販売者情報や受入チェックのWARN/NGは項目名付きで表示され、`--strict` を付けると警告を本番前のNGとして扱えます。
- `auto-note self-test` で、セットアップ、ランチャー健康チェック、クイック確認、アクションプラン、プライバシー監査、最新配布ZIP検証をまとめて確認できます。ランチャー健康チェックでは `auto-note-gui.bat`、隠しGUIランチャー、ショートカット、起動ログ/復旧導線を確認し、ショートカットで起動しない場合は `auto-note-gui.bat` を直接開く案内を出します。クイック確認のWARNが記事チェック/レビューだけの場合はINFOに整理し、投稿前の磨き込みとして表示します。`--gui-smoke` を付けるとGUI初期化も確認し、`--report` を付けると `.auto-note\reports` にテキスト保存できます。
- `auto-note workflow-smoke` で、一時プロジェクトに練習記事を作り、公開前チェック、記事レビュー、投稿準備、投稿ヘルパーHTML生成、バックアップまでの簡易E2Eを確認できます。GUIの診断タブの `E2E確認` からも実行でき、結果は `.auto-note\reports` に保存されます。
- `auto-note quickstart` で初回投稿までの導線を確認できます。`--smoke-helper` を付けるとブラウザを開かず投稿ヘルパーHTML生成まで確認します。
- `auto-note action-plan` で、準備度、クイック確認、投稿キュー、販売者情報の不足/公開URL警告、危険生成物候補から「いま優先すべき操作」を順位付きで表示できます。GUIのホームでは上位アクションを一覧し、投稿キューの対象記事や販売者情報確認へ直接移動、またはCLIコピーできます。
- `auto-note starter-pack` で、サンプル記事3本、アイデア1件、匿名の予定ICSを作成し、記事一覧、予定、投稿キュー、運用サマリーをすぐ試せる状態にできます。既存の記事は上書きせず、二回目以降は既存スターター記事をスキップします。試した後は `auto-note starter-clean --project-dir .` で削除候補を確認し、`--apply` でスターター由来の記事と未使用アイデアだけ整理できます。GUIのホーム、初回、診断、ヘルプ、コマンド検索の `スターター一式` / `スターター整理` からも実行できます。
- `auto-note overview` で、次に投稿する記事、期限超過の公開予定、古い下書き、公開URL未記録、アイデア箱をまとめた運用サマリーを表示できます。GUIのホーム、診断タブ、ヘルプ、コマンド検索の `運用サマリー` からも確認でき、`--report` で保存するレポートは標準で記事タイトルとファイル名を匿名化します。
- `auto-note calendar-export` で、公開予定をGoogle Calendar/Outlook/Apple Calendarに取り込める `.ics` として `.auto-note\reports` に保存できます。標準では記事タイトルとファイル名を匿名化し、GUIの `予定ICS出力` では自分のカレンダー用にタイトル入りで保存するか確認できます。
- `auto-note practice` で、初回操作を試すための完成寄り練習記事を作成できます。
- `auto-note publish-ready <file>` で、選択記事のチェック、記事レビュー、工程状態、投稿ヘルパー生成確認を1つの投稿準備レポートにまとめられます。GUIの記事タブでも同じ内容を一覧でき、項目を選んで `次を実行`、`詳細`、`準備OK`、`HTML確認` に進めます。`--mark-ready` を付けるとNGがない場合だけ状態を `ready` にできます。
- `auto-note improve <file>` で、1記事の必須修正、仕上げ、投稿前確認をおすすめ順にまとめた改善プランを表示できます。GUIの記事タブ、チェックタブ、レビュー一覧、コマンド検索の `改善プラン` からも開けます。`--report` で保存するレポートは標準で記事タイトルとファイル名を匿名化します。
- `auto-note publish-queue` で、全記事を `POSTABLE` / `CHECK` / `BLOCKED` / `DONE` に分けて、投稿できる順に表示できます。GUIの記事タブ、診断タブ、ヘルプ、コマンド検索の `投稿キュー` からも確認できます。`--report` で保存するレポートは標準で記事タイトルとファイル名を匿名化します。
- `auto-note readiness` で準備度スコアと次に直す項目を表示できます。プライバシー監査NGの古い生成物候補もINFOとして確認できます。
- `auto-note preflight` で販売/配布前の総合チェックを表示できます。トラブル診断も含め、記事レビューとアクションプランは通常INFO扱いで、`--content-strict` を付けると記事の改善項目も警告として扱います。`--create-release` を付けると新しい配布ZIPの作成と検証までまとめて行います。
- `auto-note preflight --install-smoke` で、一時フォルダへのインストール、更新、アンインストール導線も確認できます。
- `auto-note gui --project-dir . --smoke` で、GUIを表示せずに初期化できるか確認できます。`auto-note preflight --gui-smoke` を付けると出荷前チェックにも含められます。
- GUIの `出荷ZIP作成` でも、出荷前チェック、新しい配布ZIP作成、checksum検証をまとめて実行できます。
- `auto-note diagnose --preview` で診断レポートの内容を作成前に確認できます。
- `auto-note diagnose --report` でサポート用診断ZIPを作成できます。GUIでは `診断レポート` で作成し、`診断ZIP検証` で必須ファイルと破損を確認し、`診断ZIP場所` で保存フォルダを開き、`診断ZIPパス` で最新ZIPの絶対パスをコピーできます。標準ではパス、ユーザー名、メール、記事タイトル、記事ファイル名を隠し、記事レビュー、初回チェック、`acceptance.txt` の受入チェック、`commercial-readiness.txt` の販売準備、`sales-launch.txt` の販売直前チェック、販売者情報の完了数/不足数/確認数だけの匿名サマリー、アクションプラン、`overview.txt` の運用サマリー、`calendar.txt` の公開予定、クイック確認、`publish-ready.txt` の最新記事投稿準備、`improvement-plan.txt` の改善プラン、`publish-queue.txt` の投稿キュー、`gui-smoke.txt` のGUI起動スモーク、出荷前チェック、`troubleshoot.txt` のトラブル診断、準備度、製品品質、品質チェック、危険生成物候補を含む保守一覧も同梱します。
- `auto-note support` で、再現手順、直近の変更、添付物、匿名化済み診断プレビュー入りのサポート依頼Markdownを `.auto-note\support` に作成できます。通常作成時は送付前のプライバシー監査も表示します。`--bundle` を付けると、依頼文、診断ZIP、`SUPPORT_SEND_CHECKLIST.txt` を1つの問い合わせ一式ZIPにまとめ、manifest/checksum検証とプライバシー監査まで行います。`--verify <zip>` で問い合わせ一式ZIPを検証できます。
- `auto-note privacy-audit` で、最新の診断ZIP、セルフテスト保存レポート、受入チェック保存レポート、販売準備レポート、販売者テンプレート、販売方針レビュー、販売ページ・納品最終レビューレポート、販売直前チェックリスト、販売素材、販売一式ZIP、購入者向け単体ZIP、購入者向け送付文、購入者送付前チェックレポート、販売者向け納品記録、販売者送付前チェックリスト、改善プランレポート、運用サマリーレポート、予定ICS、投稿キューレポート、E2E確認レポート、問い合わせMarkdown、問い合わせ一式ZIP、配布ZIPに生のパス、ユーザー名、記事名、記事タイトル、メールアドレスが残っていないか確認できます。`--all` を付けると古い生成物も含めて監査します。
- `auto-note review` で記事のタイトル、概要、構成、導入、締め、タグ、画像、公開状態をスコア化し、次に直す項目を表示できます。
- `auto-note version` でバージョンと環境概要を表示できます。
- `auto-note licenses` で依存ライブラリの第三者表記と現在のインストール状況を表示できます。
- `auto-note licenses --write` で `docs\THIRD_PARTY_NOTICES.md` を現在の環境情報で更新できます。
- 更新時は新しい配布ZIPの `shortcuts\install-auto-note.bat` を実行します。既存の `articles` と `.auto-note` は残ります。
- `auto-note backup` で手動バックアップを作成できます。
- `auto-note backup --inspect <zip>` で復元前にバックアップZIPの中身と危険な項目を確認できます。
- `auto-note backup --restore <zip>` で記事、設定、アイデアを復元できます。復元前には安全バックアップを自動作成します。
- `auto-note readiness` と診断レポートの保守一覧では、最新バックアップが読めるか、危険エントリがないか、復元対象があるか、プライバシー監査NG生成物候補があるかも確認します。
- `auto-note release` でユーザー記事を含めない配布ZIPを作成できます。
- 配布ZIPには `START_HERE.txt`, `FIRST_RUN_CHECKLIST.txt`, `BUYER_ACCEPTANCE_CHECKLIST.txt`, `RELEASE_SUMMARY.txt`, `RELEASE_MANIFEST.json`, `CHECKSUMS.txt` が入ります。
- `auto-note release --verify <zip>` で配布ZIPのchecksum、manifest、ユーザー記事や `.auto-note` / `.venv` の混入がないことを検証し、manifest概要を表示できます。
- `shortcuts\install-auto-note.bat` で、管理者権限なしのローカルインストールとショートカット作成ができます。
- `shortcuts\uninstall-auto-note.bat` で、記事と設定を残したままアプリ本体を削除できます。
- `scripts\check-release.ps1` で、Python構文チェック、全unittest、製品品質ゲート、VBSランチャー構文チェック、GUI smokeを手元で一括確認できます。販売直前は `-Full` を付けると、プライバシー監査、販売準備、preflight、インストール/アンインストールスモーク、販売一括/購入者送付/販売直前チェック保存スモークまで確認できます。
- `scripts\smoke-install.ps1` で、インストール/アンインストール導線だけを一時フォルダで検証できます。`scripts\smoke-sales-delivery.ps1` では、クリーンな一時コピー上の販売一括作成、購入者向けZIP検証、送付前チェック保存、販売者向け送付記録作成、販売直前チェックリスト保存を確認できます。
- `docs\RC_HANDOFF.md` で、販売候補版として固定するタグ、実機確認、販売者が埋める項目、販売直前の証跡、止める条件を1枚で確認できます。
- `auto-note quality` で配布前の品質チェックを実行できます。
  通常は README、サポート文書、起動ファイル、起動batのスモーク/サポート導線、診断、記事、記事レビュー、画像、重複タイトル、状態値、公開予定形式を確認します。`--product-only` を付けるとユーザー記事を除いたアプリ/配布物だけを確認できます。
- GitHub Actions の `CI` では、Windows上でPython構文チェック、全unittest、`auto-note quality --project-dir . --product-only`、隠しGUIランチャーのVBS構文チェック、`scripts\smoke-install.ps1` によるインストール/更新/アンインストールスモーク、出荷ZIPの作成と `auto-note release --verify`、`scripts\smoke-sales-delivery.ps1` による販売一括/購入者ZIP/送付前チェック/送付記録スモーク、`auto-note gui --project-dir . --smoke` をpush/PRごとに実行します。
- `auto-note cleanup` で古い投稿ヘルパーHTML、診断ZIP、問い合わせ一式、記事CSV、セルフテスト保存レポート、受入チェック保存レポート、販売準備レポート、販売方針レビュー、販売ページ・納品最終レビューレポート、販売直前チェックリスト、購入者向け送付文、購入者送付前チェックレポート、販売者向け納品記録、改善プランレポート、運用サマリーレポート、予定ICS、投稿キューレポート、E2E確認レポートをプレビューし、`--apply` で整理できます。配布ZIPを含める場合だけ `--include-releases` を付けます。`privacy-audit --all` で古い生成物がNGになった時は、`--privacy-failed` でNG生成物だけを確認できます。
- `auto-note export` で記事一覧CSVを `.auto-note\reports` に出力できます。
- GUIの `画像挿入` は画像を記事専用フォルダへコピーし、Markdownをカーソル位置へ挿入します。必要なら同じ画像を `cover` にも設定できます。
- 画像挿入時の最適化ON/OFF、最大幅、品質はGUIの `設定` に保存できます。
- GUIの `メタ編集` から、タイトル、概要、タグ、coverを本文Markdownを直接触らず更新できます。
- 画像最適化は任意機能です。使う場合は `shortcuts\install-image-tools.bat`、または `.\.venv\Scripts\python.exe -m pip install -e .[images]` を実行します。
- GUI保存時は変更前のMarkdownを `.auto-note\history` に退避します。

古い個別起動ファイルは `shortcuts` フォルダに退避しています。軽い番号メニューや、チェックだけ、本文コピーだけを直接起動したい場合はそちらを使ってください。

アイコン付きショートカットを作り直したい場合は `shortcuts\create-gui-shortcut.bat` を実行してください。Windowsでは `.bat` ファイル自体に個別アイコンを付けるのではなく、ショートカット側にアイコンを付けるのが安定です。

初回起動時に `.venv` の作成と依存パッケージのインストールを自動で行います。

## おすすめの流れ

1. `auto-note.lnk` を開く
2. `セットアップ` で既定タグと投稿ヘルパー設定を確認する
3. 初回は `スターター一式` で記事一覧、予定、アイデア、投稿キューの見え方を確認する
4. 自分の記事を書く時は `新規記事` でテンプレートを選び、GUIの `編集` タブ、または `記事フォルダ` から編集する
5. 記事タブの `改善プラン`、`投稿準備` パネル、`投稿キュー`、または `全体チェック` / `選択記事チェック` で確認する
6. 予定があれば `公開予定` に日時を入れて `予定保存`。外部カレンダーに入れる場合は `予定ICS出力`
7. `投稿ヘルパー` で投稿前チェックを確認してから、note とヘルパーを開く
8. ヘルパーのコピー操作で note に貼り付ける
9. note 画面で公開する
10. GUIの `公開URL` にURLを入れて `公開済みにする`

Googleログインなどで「このブラウザまたはアプリは安全ではない可能性があります」と表示される場合があるため、ダブルクリック版は普段使っている既定ブラウザを使います。

## 投稿ヘルパー

GUIで記事を選んで `投稿ヘルパー` を押すと、note 投稿画面とローカルのヘルパー画面が開きます。

ヘルパー画面では次のことができます。

- タイトル、本文、タグ、全文のコピー
- 文字数、行数、読了目安の確認
- Markdownの簡易プレビュー
- 概要、カバー画像メモ、チェック結果の確認
- note投稿画面、ログイン画面への移動

## CLI

CLIで使う場合:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

主なコマンド:

```powershell
auto-note new "記事タイトル" --tag note --open
auto-note new --list-templates
auto-note new "レビュー記事" --template review --tag note --open
auto-note starter-pack --project-dir .
auto-note starter-clean --project-dir .
auto-note practice --project-dir . --open
auto-note check .\articles --append-tags
auto-note review .\articles --append-tags
auto-note improve .\articles\post.md --append-tags
auto-note improve .\articles\post.md --project-dir . --report
auto-note publish-ready .\articles\post.md --append-tags --smoke-helper
auto-note publish-ready .\articles\post.md --mark-ready
auto-note publish-queue --project-dir .
auto-note publish-queue --project-dir . --report
auto-note calendar-export --project-dir .
auto-note calendar-export --project-dir . --include-private
auto-note dashboard .\articles --append-tags
auto-note manual .\articles\post.md --append-tags
auto-note copy .\articles\post.md --part body --append-tags
auto-note gui
auto-note gui --project-dir . --smoke
auto-note setup --project-dir . --create
auto-note repair --project-dir .
auto-note repair --project-dir . --apply
auto-note repair --project-dir . --cleanup-privacy --include-releases
auto-note troubleshoot --project-dir .
auto-note first-run --project-dir . --create --gui-smoke --smoke-helper
auto-note acceptance --project-dir . --full
auto-note commercial-setup --project-dir . --seller-name "Your Shop" --sales-url "https://example.com" --refund-url "https://example.com/refund" --support-contact "https://example.com/support" --terms-reviewed --support-scope-confirmed
auto-note commercial-setup --project-dir . --template
auto-note commercial-setup --project-dir . --apply-latest-template
auto-note commercial-readiness --project-dir . --report
auto-note commercial-readiness --project-dir . --policy-review
auto-note sales-plan --project-dir .
auto-note sales-plan --project-dir . --report
auto-note sales-review --project-dir .
auto-note sales-review --project-dir . --report
auto-note sales-launch --project-dir .
auto-note sales-launch --project-dir . --report
auto-note sales-materials --project-dir .
auto-note sales-materials --project-dir . --verify ".auto-note\sales\auto-note-sales-materials-YYYYMMDD-HHMMSS.md" --strict
auto-note sales-handoff --project-dir .
auto-note sales-handoff --project-dir . --extract-buyer ".auto-note\sales\auto-note-sales-handoff-YYYYMMDD-HHMMSS.zip"
auto-note sales-handoff --project-dir . --verify-buyer ".auto-note\sales\buyer-delivery-YYYYMMDD-HHMMSS"
auto-note sales-handoff --project-dir . --package-buyer ".auto-note\sales\buyer-delivery-YYYYMMDD-HHMMSS"
auto-note sales-handoff --project-dir . --verify-buyer-package ".auto-note\sales\auto-note-buyer-delivery-YYYYMMDD-HHMMSS.zip"
auto-note sales-finalize --project-dir .
auto-note sales-finalize --project-dir . --apply-latest-template
auto-note sales-finalize --project-dir . --send-check --send-check-report
auto-note sales-finalize --project-dir . --delivery-receipt
auto-note sales-finalize --project-dir . --strict --gui-smoke
auto-note quickstart --project-dir .
auto-note quickstart --project-dir . --smoke-helper
auto-note action-plan --project-dir .
auto-note starter-pack --project-dir .
auto-note overview --project-dir .
auto-note overview --project-dir . --report
auto-note practice --project-dir . --open
auto-note readiness --project-dir .
auto-note preflight --project-dir .
auto-note preflight --project-dir . --gui-smoke
auto-note preflight --project-dir . --content-strict
auto-note preflight --project-dir . --create-release
auto-note preflight --project-dir . --create-release --install-smoke --gui-smoke
auto-note diagnose
auto-note diagnose --preview
auto-note diagnose --report
auto-note self-test --project-dir .
auto-note self-test --project-dir . --create --gui-smoke --report
auto-note workflow-smoke --project-dir . --report
auto-note support --project-dir .
auto-note support --project-dir . --bundle
auto-note support --verify .\.auto-note\support\<support-bundle>.zip
auto-note privacy-audit --project-dir .
auto-note privacy-audit --project-dir . --all
auto-note version --project-dir .
auto-note licenses
auto-note licenses --write
auto-note backup
auto-note backup --inspect .\.auto-note\backups\auto-note-backup-YYYYMMDD-HHMMSS.zip
auto-note backup --restore .\.auto-note\backups\auto-note-backup-YYYYMMDD-HHMMSS.zip
auto-note release
auto-note release --verify .\.auto-note\releases\auto-note-release-YYYYMMDD-HHMMSS.zip
auto-note images .\articles
auto-note quality
auto-note quality --product-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-release.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-release.ps1 -Full
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-sales-delivery.ps1 -SourceDir .
$env:AUTO_NOTE_LAUNCHER_CHECK='1'; cscript.exe //nologo .\scripts\launch-gui.vbs
auto-note cleanup --project-dir .
auto-note cleanup --project-dir . --apply
auto-note cleanup --project-dir . --include-releases
auto-note cleanup --project-dir . --days 0 --include-releases
auto-note cleanup --project-dir . --privacy-failed
auto-note cleanup --project-dir . --privacy-failed --include-releases
auto-note export --project-dir .
auto-note image-import .\articles\post.md .\cover.png --alt "カバー画像" --insert --cover --optimize
auto-note history .\articles\post.md
auto-note history .\articles\post.md --restore .\.auto-note\history\...\revision.md
auto-note plan .\articles
auto-note calendar .\articles --days 30
auto-note calendar-export --project-dir . --days 90
auto-note schedule .\articles\post.md --at "2026-06-06 09:00"
auto-note published .\articles\post.md --url "https://note.com/..."
```

アイデア箱:

```powershell
auto-note idea add "書きたいテーマ" --note "切り口メモ" --tag note
auto-note idea list
auto-note idea promote 1 --open
```

自動操作ブラウザを使える環境だけ、以下も使えます。

```powershell
python -m pip install -e .[browser]
python -m playwright install chromium
auto-note login --browser msedge
auto-note post .\articles\post.md --publish --append-tags
```

今回の環境ではログインが弾かれやすいので、基本は手動ログイン対応モードを使ってください。

## Markdown 形式

```markdown
---
title: "記事タイトル"
summary: "記事の短い概要"
cover: "cover.png"
tags:
  - note
  - 自動化
status: draft
scheduled:
publish: false
---

本文を書きます。
```

`title` がない場合は最初の `# 見出し` をタイトルとして使います。`--append-tags` を付けると frontmatter の `tags` を本文末尾にハッシュタグとして追加します。

`status` は `draft`, `ready`, `scheduled`, `published` を使います。公開予定は `scheduled: "2026-06-06 09:00"` の形式で保存され、公開後は `published_url` と `published_at` を控えられます。

## 公開前チェック

GUIの `全体チェック` / `選択記事チェック`、または `auto-note check` は、以下を確認します。

- タイトルの長さ
- 本文の短さ
- タグの有無や多すぎ
- TODO、FIXME、下書き、要確認などの残り
- frontmatterのcover画像とMarkdown内のローカル画像ファイル存在
- 大きめの画像ファイル

GUIの `チェック` タブのレビュー一覧、または `auto-note review` は、記事そのものの仕上がりを100点満点で見ます。GUIでは記事ごとの点数、修正/改善件数、詳細項目を見ながら、本文編集、改善プラン、投稿準備、準備OK化へ進めます。

- タイトルが読者に伝わる長さか
- 概要が共有時に使いやすいか
- 本文量、見出し、導入、締めが整っているか
- タグ数が発見されやすい範囲か
- カバー画像や本文画像に欠落がないか
- 公開状態や予定日時が整理されているか

## 注意

- note画面への貼り付けと公開操作は、普段のブラウザ上で行います。
- 自動公開版 `shortcuts\post-note-publish-auto.bat` は、自動操作ブラウザ内でログインできる環境だけ使えます。
- 二要素認証やCAPTCHAは手動で対応してください。

## サポート文書

- `docs\SUPPORT.md`: サポート時に確認する項目
- `docs\INSTALL.md`: 配布ZIPからのインストール手順
- `docs\UPDATE.md`: 更新とロールバック手順
- `docs\PRIVACY.md`: 保存データと診断レポートの匿名化
- `docs\TERMS_DRAFT.md`: 利用条件と免責の販売前ドラフト
- `docs\COMMERCIAL_POLICY_DRAFT.md`: ライセンス、返金、サポート方針の販売前ドラフト
- `docs\THIRD_PARTY_NOTICES.md`: 依存ライブラリの第三者表記
- `docs\CHANGELOG.md`: 変更履歴
- `docs\RELEASE_CHECKLIST.md`: 配布前チェックリスト
