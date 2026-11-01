---
name: memo-publish
description: Claude が作った HTML（貼り付け・添付・アーティファクト・既存ファイル）を MEMO リポジトリに登録する。「MEMO に入れて」「メモに追加」「これ保存して」と言われたとき、または memo-from-chat の最後の工程で使う。崩れチェック・メタ情報付与・一覧更新・commit/push まで行う。
---

# memo-publish

HTML 1 枚を MEMO として登録する手順。ツールはすべて `scripts/memo.py`（標準ライブラリのみ）。
リポジトリのルートで実行すること。

## 1. HTML を受け取る

- 貼り付け / 添付 / アーティファクト（`Artifact` の read）/ リポジトリ内の既存ファイル、のどれか。
- **中身を最後まで読んでから**次に進む。中身を見ずに登録しない。
- Markdown のコードブロック（```html …```）で渡された場合は、囲いを外して HTML 部分だけを使う。

## 2. ファイル名を決める

- 英小文字・数字・ハイフンの短い名前 + `.html`（例: `docker.html`, `git-rebase.html`, `tcp-handshake.html`）。
- 内容を一言で表す英単語を選ぶ。日付や `memo-` などの接頭辞は付けない。
- リポジトリ直下に置く（サブフォルダは使わない。トップページはルートの *.html を一覧にする）。
- 同名ファイルがある場合:
  - 同じテーマの改訂版ならユーザーに「上書きするか、別名にするか」を確認。
  - 別テーマなら名前を変える。
- `index.html` は絶対に上書きしない。

## 3. 崩れチェックと修正（memo-lint）

```bash
python3 scripts/memo.py lint FILE.html --fix --backlink
```

自動で直すもの:
- `<style>` 内の全角クォート `‘ ’ “ ”`（コピペで化けて font-family 等が効かなくなる）
- `* {` が `- {` / `\*` に化けたもの（Markdown 経由のコピペで起きる）
- `<!DOCTYPE html>` / charset / viewport の欠落
- 右下に「← MEMO」のトップへ戻るリンクを追加（`--backlink`）

報告だけのもの（`[要対応]`）:
- JS 内の全角クォート疑い → 該当箇所を読んで、文字列の区切りに使われていれば半角に直す。日本語の文中の使用ならそのまま。
- タイトル・説明・タグ・日付の欠落 → 次の手順で付ける。

ほかにも明らかな崩れ（閉じタグ欠落、Markdown 記号の混入など）に気づいたら、内容は変えずに直す。

## 4. メタ情報を付ける

中身を読んで考える。ユーザーが指定していればそれに従う。

```bash
python3 scripts/memo.py meta FILE.html \
  --title "Docker 動作原理" \
  --desc "イメージのレイヤー構造、名前空間、cgroups などコンテナが動く仕組みを図解。" \
  --tags "Docker,Linux" \
  --date
```

- **title**: 日本語で短く（〜20 字）。既存の `<title>` が適切ならそのまま（`--title` 省略）。
- **desc**: 何がわかるページかを 1 文（40〜60 字）。
- **tags**: 1〜3 個。表記ゆれを防ぐため、まず `python3 scripts/memo.py list` で既存タグを見て、合うものがあれば再利用する（例: `Docker` と `docker` を混在させない）。
- **date**: `--date` を値なしで渡すと今日。

## 5. 一覧を更新して確認

```bash
python3 scripts/memo.py lint FILE.html   # OK になること
python3 scripts/memo.py build            # index.html の MEMOS を再生成
python3 scripts/memo.py list
```

`index.html` の `// MEMOS:BEGIN` 〜 `// MEMOS:END` は自動生成なので手で編集しない。

## 6. commit / push

```bash
git add FILE.html index.html
git commit -m "Add memo: <タイトル>"
git push origin HEAD:master
```

- push の前に `git fetch origin master` して、遅れていれば rebase。
- push 後、GitHub Actions も一覧を再生成するが、ローカルで build 済みなら差分は出ない。

## 7. 報告

ユーザーには短く:
- 追加したファイル名とタイトル・タグ
- lint で直した点（あれば 1 行で）
- GitHub Pages の URL: `https://taka1156.github.io/memo/FILE.html`
