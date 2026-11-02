# MEMO

Claude に作ってもらった解説ページ (HTML) を貯めておくリポジトリ。

- トップページ: `docs/index.html`（メモ一覧・検索・タグ絞り込み）
- 公開 URL: https://memo.taka1156.site/
  （`docs/CNAME` の独自ドメイン。OGP の URL もここから自動で決まります）

## Claude に頼むとき

このリポジトリで作業している Claude（claude.ai でリポジトリを繋いだ会話、または Claude Code）は、`.claude/skills/` のスキルを使います。

| 言い方の例 | スキル | やること |
| --- | --- | --- |
| 「この HTML を MEMO に入れて」 | `memo-publish` | 崩れ修正 → タイトル・説明・タグ付け → 一覧更新 → push |
| 「〜の図解ページを作って」 | `memo-style` | デザイン規約とテンプレートに沿って新規作成 |
| 「さっきの説明を MEMO にして」 | `memo-from-chat` | 会話内容をページ化して登録まで |
| 「〇〇をファクトチェックして」 | `memo-factcheck` | サブエージェントで独立に事実確認 → 指摘を報告 → 確認後に修正・push |

新しい会話では最初に「taka1156/memo リポジトリで作業して」と伝えるとスキルが効きます。

## アプリ（claude.ai）から使うとき

アプリ側に置くのは「このリポジトリを取ってきて、ここのスキルに従う」だけの入口スキルです。手順やデザイン規約はすべてこのリポジトリが唯一の情報源で、アプリ側には書きません。

入口スキルは依頼に応じて次のように振り分けます（上の表と同じ対応で、違いは保存のタイミングだけ）。

| 依頼 | 使うスキル | 保存 |
| --- | --- | --- |
| 「〇〇を HTML で（図とともに）まとめて」「図解ページにして」 | `memo-style` で作り、HTML ファイルとして会話内でプレビューする（`memo.py new` は使わずテンプレートをコピー） | **しない**。「保存して」と言われたら `memo-publish` で登録 |
| 「保存して」「MEMO に入れて」 | `memo-publish` | する |
| 「さっきの説明を MEMO にして」 | `memo-from-chat` | する |
| 「ファクトチェックして」 | `memo-factcheck` | 指摘を確認してもらってから修正・push |

スキルを追加したら、上の表とこの表に 1 行足せば入口スキル側の変更は不要です。

## 仕組み

- メモ = `docs/` 直下の `*.html`（`index.html` 以外）。GitHub Pages は `docs/` だけを公開するので、README やスクリプトは公開されません
- 一覧の情報は各メモの `<head>` から読みます

  ```html
  <title>Docker 動作原理</title>
  <meta name="description" content="1 文の説明">
  <meta name="memo:tags" content="Docker, Linux">
  <meta name="memo:date" content="2026-10-31">
  ```

- `docs/index.html` の `// MEMOS:BEGIN`〜`// MEMOS:END` は自動生成です。手で編集しません
- 全ページの `<!-- memo:head -->` ブロック（ファビコン・iOS アイコン・OGP）も自動生成です。og:title / og:description は各ページの title / description から作られます
- 画像は `docs/assets/`（`favicon.ico`, `icon-32.png`, `icon-192.png`, `apple-touch-icon.png`, `og.png`）。生成元は `branding/`（`og.html`・`icon.html` を `python3 branding/render.py` で書き出し。非公開）
- master に `docs/*.html` が push されると、GitHub Actions が一覧を再生成します（GitHub の画面から HTML を直接アップロードしても載ります）

## 手でやる場合

```bash
python3 scripts/memo.py add ~/Downloads/foo.html foo   # docs/foo.html として取り込む
python3 scripts/memo.py new foo                        # またはテンプレートから新規作成
python3 scripts/memo.py lint foo --fix --backlink      # 崩れチェック・修正
python3 scripts/memo.py meta foo --title "…" --desc "…" --tags "a,b" --date
python3 scripts/memo.py build                          # 一覧を再生成
python3 scripts/memo.py list                           # 一覧を表示
```

`lint` が直すもの: CSS 内の全角クォート、`* {` の化け、DOCTYPE / charset / viewport の欠落、フッターへの「一覧に戻る」リンクの追加、アイコン・OGP タグの追加／更新。
