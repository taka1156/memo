# MEMO

Claude に作ってもらった解説ページ (HTML) を貯めておくリポジトリ。
仕組み（`scripts/`・スキル・ワークフロー・テスト・`branding/` など）は [memo-kit](https://github.com/taka1156/memo-kit) と同じ構成で、このリポジトリはその実運用（ドッグフーディング）を兼ねています。

- トップページ: `src/index.html`（メモ一覧・検索・タグ絞り込み・ランダムクイズ）
- クイズページ: `src/quiz.html`（ランダム 10 問・カテゴリ別 10 問（カテゴリは複数選べる）。最後にスコアと正答一覧、本文へのリンク。タイムアタックは制限時間 30 秒／1 分／3 分で、ランダムかカテゴリ（複数可）を選んで何問正解できるかを競い、答えるとすぐ次へ進んで解説は結果にまとめて出す）
- ロードマップ: `src/roadmap.html`（トップページのいちばん下の「ロードマップ」から開ける。書いたメモとこれから書くテーマのチェックリストで、メモを公開すると自動でチェックが付く。項目はページ内の `ROADMAP` に書く。memo-kit ではオプションで、このサイトは `memo.config.json` の `"roadmap": true` で有効にしている）
- 設定ページ: https://memo.taka1156.site/settings.html  （トップページのいちばん下の「設定」から開ける。アクセント色を試して、Actions の `Set accent color` で全ページに固定する。手順は memo-kit の README の「アクセント色を変える」）
- 公開 URL: https://memo.taka1156.site/  
  （`src/CNAME` の独自ドメイン。OGP の URL もここから自動で決まります）
- 公開のしくみ: `main` には原本（HTML・スクリプト）だけを置き、push すると GitHub Actions（Deploy MEMO）が `memo.py build` で `dist/` に公開用のサイト一式を作って **dist ブランチ**にコミットします。GitHub Pages の公開元は dist ブランチです（生成物が `main` に混ざらない）
- 設定: `memo.config.json`（サイト名・説明・リポジトリ・ブランチ・タイムゾーン・クイズとロードマップを使うか・アクセント色とアイコン/OGP 画像の文字。コードやスキルには直接書かない。このサイトは `"quiz": true`・`"roadmap": true`）
- アイコン・OGP 画像: `memo.config.json` の `branding`（`icon: "lines"` で今の横線のアイコン）から `branding/render.py` で作る。設定ページから色を固定すると、Actions が画像も同じ色で作り直す

## Claude に頼むとき

このリポジトリで作業している Claude（claude.ai でリポジトリを繋いだ会話、または Claude Code）は、`.claude/skills/` のスキルを使います。

| 言い方の例 | スキル | やること |
| --- | --- | --- |
| 「この HTML を MEMO に入れて」 | `memo-publish` | 崩れ修正 → タイトル・説明・タグ付け → 一覧更新 → ファクトチェック → push |
| 「〜の図解ページを作って」 | `memo-style` | デザイン規約とテンプレートに沿って新規作成 |
| 「さっきの説明を MEMO にして」 | `memo-from-chat` | 会話内容をページ化して、ファクトチェックを通して登録まで |
| 「〇〇をファクトチェックして」 | `memo-factcheck` | サブエージェントで独立に事実確認 → 指摘を報告 → 確認後に修正・push |
| 「前に〜のメモ書いたよね」「〜のメモのここを直して」 | `memo-reference` | Markdown 版（build で作る `dist/md/`）で探して読む／直すときは HTML の該当箇所だけ編集 → 変えた箇所をファクトチェック → push |
| 「ロードマップを作って」「次のメモを書いて」「ロードマップを見直して」 | `memo-roadmap` | ロードマップ（オプション）の項目を相談して決める／優先度の順に 1 本ずつ書いて登録 → 項目を更新 → push |
| 「memo.py を直して」「コマンドを追加して」「リファクタして」 | `memo-maintain` | テストを流す → 変更 → 出力の前後比較・テスト → memo-detail.md を更新 → push |

新しい会話では最初に「taka1156/memo リポジトリで作業して」と伝えるとスキルが効きます。

## アプリ（claude.ai）から使うとき

アプリ側に置くのは「このリポジトリを取ってきて、ここのスキルに従う」だけの入口スキルです。手順やデザイン規約はすべてこのリポジトリが唯一の情報源で、アプリ側には書きません。
入口スキルの中身は `memo.py build` が `memo.config.json` のリポジトリ名とブランチから `dist/entry-skill/SKILL.md` に作ります（dist ブランチと公開サイトの `/entry-skill/SKILL.md` にもあります）。設定を変えたらアプリ側に貼り直してください。

入口スキルは依頼に応じて次のように振り分けます（上の表と同じ対応で、違いは保存のタイミングだけ）。

| 依頼 | 使うスキル | 保存 |
| --- | --- | --- |
| 「〇〇を HTML で（図とともに）まとめて」「図解ページにして」 | `memo-style` で作り、`memo.py preview` で 1 枚にまとめた HTML を会話内でプレビューする（`memo.py new` は使わずテンプレートをコピー） | **しない**。「保存して」と言われたら `memo-publish` で登録 |
| 「保存して」「MEMO に入れて」 | `memo-publish` | する |
| 「さっきの説明を MEMO にして」 | `memo-from-chat` | する |
| 「ファクトチェックして」 | `memo-factcheck` | 指摘を確認してもらってから修正・push |
| 「前に〜のメモ書いたよね」「MEMO に〜ってある？」 | `memo-reference` | しない（参照だけ） |
| 「〜のメモのここを直して」 | `memo-reference`（部分修正） | する |
| 「ロードマップを作って」「見直して」 | `memo-roadmap` | 項目を確認してもらってから push |
| 「次のメモを書いて」 | `memo-roadmap`（ロードマップの順に `memo-style` で作り `memo-publish` で登録） | する |
| 「memo.py を直して」「仕組みを変えて」 | `memo-maintain` | テストが通ってから push |

メモの本文を変えて push するときは、どの流れでも push の前に `memo-factcheck` でファクトチェックします（仕組みだけの変更やタイトル・タグだけの変更は除く）。

スキルを追加したら、上の表とこの表に 1 行足せば入口スキル側の変更は不要です。

## 仕組みと memo.py

ファイルの構成（原本と生成物）、`scripts/memo.py` の各コマンド、自動生成ブロック、確認クイズのデータの流れ、AI 向けの Markdown 版（`llms.txt`）、サイトごとの設定（`memo.config.json`）、表示の確認とプレビュー、GitHub Actions は、図つきで [memo-detail.md](memo-detail.md) にまとめています。

## memo-kit との関係

仕組みのファイルは memo-kit と同じ内容に揃えています。仕組みを直すときは memo-kit 側を直してこちらに持ってくる（またはこちらで試してから memo-kit に戻す）ことで、両方を同じに保ちます。

このリポジトリにだけあるもの（memo-kit に持っていかないもの）:

| ファイル | 内容 |
| --- | --- |
| `src/` 直下のメモ | メモ本体（原本。生成物は build が `dist/` に作り、dist ブランチで公開する） |
| `src/CNAME` | 独自ドメイン（memo.taka1156.site） |
| `src/roadmap.html` の `ROADMAP` の中身 | このサイトで書く予定のテーマ（ページの作りは仕組み側） |
| `src/assets/` の画像 | このサイトのアイコン・OGP 画像 |
| `branding/source.png` | アイコンの元画像 |
| `memo.config.json` の値 | このサイトの設定 |
| `README.md` | この説明 |

仕組みの詳細は [memo-detail.md](memo-detail.md)、新しく始める手順は memo-kit の README にあります。
