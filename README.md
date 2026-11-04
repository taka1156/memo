# MEMO

Claude に作ってもらった解説ページ (HTML) を貯めておくリポジトリ。
仕組み（`scripts/`・スキル・ワークフロー・テスト・`branding/` など）は [memo-kit](https://github.com/taka1156/memo-kit) と同じ構成で、このリポジトリはその実運用（ドッグフーディング）を兼ねています。

- トップページ: `docs/index.html`（メモ一覧・検索・タグ絞り込み・ランダムクイズ）
- クイズページ: `docs/quiz.html`（ランダム 10 問・カテゴリ別 10 問。最後にスコアと正答一覧、本文へのリンク）
- 公開 URL: https://memo.taka1156.site/
  （`docs/CNAME` の独自ドメイン。OGP の URL もここから自動で決まります）
- 設定: `memo.config.json`（サイト名・説明・リポジトリ・ブランチ・タイムゾーン・アクセント色とアイコン/OGP 画像の文字。コードやスキルには直接書かない）
- アイコン・OGP 画像: `docs/assets/` の今の画像をそのまま使う（`branding/render.py` を実行すると memo-kit のデザインで作り直されるので、変えたいときだけ実行する）

## Claude に頼むとき

このリポジトリで作業している Claude（claude.ai でリポジトリを繋いだ会話、または Claude Code）は、`.claude/skills/` のスキルを使います。

| 言い方の例 | スキル | やること |
| --- | --- | --- |
| 「この HTML を MEMO に入れて」 | `memo-publish` | 崩れ修正 → タイトル・説明・タグ付け → 一覧更新 → push |
| 「〜の図解ページを作って」 | `memo-style` | デザイン規約とテンプレートに沿って新規作成 |
| 「さっきの説明を MEMO にして」 | `memo-from-chat` | 会話内容をページ化して登録まで |
| 「〇〇をファクトチェックして」 | `memo-factcheck` | サブエージェントで独立に事実確認 → 指摘を報告 → 確認後に修正・push |
| 「前に〜のメモ書いたよね」「〜のメモのここを直して」 | `memo-reference` | Markdown 版（`docs/md/`）で探して読む／直すときは HTML の該当箇所だけ編集 → push |
| 「memo.py を直して」「コマンドを追加して」「リファクタして」 | `memo-maintain` | テストを流す → 変更 → 出力の前後比較・テスト → memo-detail.md を更新 → push |

新しい会話では最初に「taka1156/memo リポジトリで作業して」と伝えるとスキルが効きます。

## アプリ（claude.ai）から使うとき

アプリ側に置くのは「このリポジトリを取ってきて、ここのスキルに従う」だけの入口スキルです。手順やデザイン規約はすべてこのリポジトリが唯一の情報源で、アプリ側には書きません。
入口スキルの中身は `entry-skill/SKILL.md` にあり、`memo.py build` が `memo.config.json` のリポジトリ名とブランチから作ります。設定を変えたらアプリ側に貼り直してください。

入口スキルは依頼に応じて次のように振り分けます（上の表と同じ対応で、違いは保存のタイミングだけ）。

| 依頼 | 使うスキル | 保存 |
| --- | --- | --- |
| 「〇〇を HTML で（図とともに）まとめて」「図解ページにして」 | `memo-style` で作り、`memo.py preview` で 1 枚にまとめた HTML を会話内でプレビューする（`memo.py new` は使わずテンプレートをコピー） | **しない**。「保存して」と言われたら `memo-publish` で登録 |
| 「保存して」「MEMO に入れて」 | `memo-publish` | する |
| 「さっきの説明を MEMO にして」 | `memo-from-chat` | する |
| 「ファクトチェックして」 | `memo-factcheck` | 指摘を確認してもらってから修正・push |
| 「前に〜のメモ書いたよね」「MEMO に〜ってある？」 | `memo-reference` | しない（参照だけ） |
| 「〜のメモのここを直して」 | `memo-reference`（部分修正） | する |
| 「memo.py を直して」「仕組みを変えて」 | `memo-maintain` | テストが通ってから push |

スキルを追加したら、上の表とこの表に 1 行足せば入口スキル側の変更は不要です。

## 仕組みと memo.py

ファイルの構成（原本と生成物）、`scripts/memo.py` の各コマンド、自動生成ブロック、確認クイズのデータの流れ、AI 向けの Markdown 版（`llms.txt`）、サイトごとの設定（`memo.config.json`）、表示の確認とプレビュー、GitHub Actions は、図つきで [memo-detail.md](memo-detail.md) にまとめています。

## memo-kit との関係

仕組みのファイルは memo-kit と同じ内容に揃えています。仕組みを直すときは memo-kit 側を直してこちらに持ってくる（またはこちらで試してから memo-kit に戻す）ことで、両方を同じに保ちます。

このリポジトリにだけあるもの（memo-kit に持っていかないもの）:

| ファイル | 内容 |
| --- | --- |
| `docs/` 直下のメモ・`docs/md/`・`memos.json`・`quizzes.json`・`llms.txt` | メモ本体と生成物 |
| `docs/CNAME` | 独自ドメイン（memo.taka1156.site） |
| `docs/assets/` の画像 | このサイトのアイコン・OGP 画像 |
| `branding/source.png` | アイコンの元画像 |
| `memo.config.json` の値 | このサイトの設定 |
| `README.md` | この説明 |

仕組みの詳細は [memo-detail.md](memo-detail.md)、新しく始める手順は memo-kit の README にあります。
