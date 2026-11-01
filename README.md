# MEMO

Claude に作ってもらった解説ページ (HTML) を貯めておくリポジトリ。

- トップページ: `index.html`（メモ一覧・検索・タグ絞り込み）
- Pages: https://taka1156.github.io/memo/

## Claude に頼むとき

このリポジトリで作業している Claude（claude.ai でリポジトリを繋いだ会話、または Claude Code）は、`.claude/skills/` のスキルを使います。

| 言い方の例 | スキル | やること |
| --- | --- | --- |
| 「この HTML を MEMO に入れて」 | `memo-publish` | 崩れ修正 → タイトル・説明・タグ付け → 一覧更新 → push |
| 「〜の図解ページを作って」 | `memo-style` | デザイン規約とテンプレートに沿って新規作成 |
| 「さっきの説明を MEMO にして」 | `memo-from-chat` | 会話内容をページ化して登録まで |

新しい会話では最初に「taka1156/memo リポジトリで作業して」と伝えるとスキルが効きます。

## 仕組み

- メモ = リポジトリ直下の `*.html`（`index.html` 以外）
- 一覧の情報は各メモの `<head>` から読みます

  ```html
  <title>Docker 動作原理</title>
  <meta name="description" content="1 文の説明">
  <meta name="memo:tags" content="Docker, Linux">
  <meta name="memo:date" content="2026-10-31">
  ```

- `index.html` の `// MEMOS:BEGIN`〜`// MEMOS:END` は自動生成です。手で編集しません
- master に `*.html` が push されると、GitHub Actions が一覧を再生成します（GitHub の画面から HTML を直接アップロードしても載ります）

## 手でやる場合

```bash
python3 scripts/memo.py lint new.html --fix --backlink   # 崩れチェック・修正
python3 scripts/memo.py meta new.html --title "…" --desc "…" --tags "a,b" --date
python3 scripts/memo.py build                            # 一覧を再生成
python3 scripts/memo.py list                             # 一覧を表示
```

`lint` が直すもの: CSS 内の全角クォート、`* {` の化け、DOCTYPE / charset / viewport の欠落、トップへ戻るリンクの追加。
