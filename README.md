# MEMO

Claude に作ってもらった解説ページ (HTML) を貯めておくリポジトリ。

トップページ: `index.html` (メモ一覧・検索・タグ絞り込み)

## メモの追加方法

1. 生成された HTML をリポジトリ直下に置く (例: `kubernetes.html`)
2. `index.html` の `MEMOS` 配列に 1 件追加する

```js
{
  file: 'kubernetes.html',
  title: 'Kubernetes の仕組み',
  desc: 'Pod / Service / Deployment の関係を図解。',
  tags: ['Kubernetes'],
  date: '2026-11-01',
},
```

一覧は日付の新しい順に並びます。

## 収録メモ

| ファイル | 内容 |
| --- | --- |
| `docker.html` | Docker 動作原理 |
| `ecma.html` | Ecma TC 一覧 |
