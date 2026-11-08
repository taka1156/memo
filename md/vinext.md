<!-- scripts/memo.py build が自動生成。手で編集しない -->

# vinext と Next.js の比較

> Cloudflare の vinext と本家 Next.js の違いと、Workers・Node.js・SSG の 3 つのデプロイパターンを図解。

- URL: https://memo.taka1156.site/vinext.html
- タグ: JavaScript, フロントエンド
- 日付: 2026-11-03

---

# vinext vs Next.js

同じ API、違うエンジン — Cloudflare 製の Next.js 再実装と、3 つのデプロイパターン

**ざっくり言うと**

- vinext は Next.js のフォークではなく、 **Next.js の公開 API を Vite プラグインとして作り直したもの** 。 `app/` ・ `pages/` ・ `next.config.js` はそのまま使える。
- メリットはビルドの速さとバンドルの小ささ、Cloudflare Workers への素直なデプロイ。代わりに API カバー率は約 94% で、細かい挙動の差が残る。
- 本家は「ビルド時に静的生成してサーブを速く」、vinext は「リクエスト時に描画してキャッシュで速く」が基本の考え方。

## Next.js との比較

Next.js（本家）

vinext

作り

Vercel によるオリジナル実装

公開 API をゼロから再実装（フォークではない）

ビルドツール

Turbopack / webpack

Vite 8（Rolldown・Oxc）

互換範囲

全機能（基準）

Next.js 16 API の約 94%（公開時点の数字）。16.x のみ対象、古い非推奨 API は非対応

描画の既定

静的ページはビルド時に事前生成

リクエスト時描画＋キャッシュ寄り（SSG・ISR も可）

画像・フォント

画像はリクエスト時に最適化（静的 import はビルド時に寸法・プレースホルダーを生成）、フォントはビルド時に自己ホスト

実行時最適化（Workers）、フォントは CDN／実行時注入

新機能

Cache Components・PPR が完全

`"use cache"` は部分対応、PPR は未完

設定・周辺

webpack 設定、 `next/jest` 、create-next-app

Vite プラグイン、Vitest、create-vinext-app

成熟度

本番実績が豊富

2026 年 9 月に 1.0 を公開し、公式は本番利用可としている。ただし README は今も互換性の差に注意して評価するよう求めている

### 公式ベンチマーク（33 ルートの App Router アプリ、公開時の数値）

本番ビルド時間（短いほど良い）

Next.js 16 7.38s

vinext 1.67s

クライアントバンドル gzip（小さいほど良い）

Next.js 16 168.9KB

vinext 72.9KB

測っているのはビルドとバンドルだけで、本番の配信速度ではない。公平にするため Next.js 側の静的事前生成は無効化している。公式も「方向性を示す参考値」としている。

## vinext アーキテクチャ：3 つのデプロイパターン

**あなたの Next.js コード** app/ · pages/ · next.config.js

→

**vinext（Vite プラグイン）** next/* シム · ルーター · plugin-rsc

→

**Vite 8 マルチ環境ビルド** rsc（RSC 生成）→ ssr（HTML 生成）→ client

↓

Cloudflare Workers

Node.js

SSG

**Cloudflare Workers** 第一級のネイティブ統合

**Node.js サーバー** standalone か Nitro

**SSG（静的エクスポート）** サーバーなしでファイル配信

設定

**vinext init** --platform=cloudflare

**vinext init --platform=node** output: "standalone"（任意）

**output: "export"** next.config で指定

追加プラグイン

**@cloudflare/vite-plugin** RSC 環境を workerd で実行

**Nitro（他プラットフォーム向け）** standalone 出力なら不要

**不要 ※** CF プラグイン・Nitro とも不要

実行環境

**workerd（V8 isolate）** エッジでサーバー実行

**Node.js プロセス** VM・Docker・自前サーバー

**実行時サーバーなし** ビルド済み HTML/JSON を配信

データ連携

**cloudflare:workers の env** D1・R2・KV・DO など

**process.env + 任意の DB** バインディングはなし

**ビルド時に取得して固定** 実行時の取得は不可

キャッシュ

**KV + Workers Cache** ISR も CDN 側から配信

**MemoryCacheHandler（既定）** 本番は自前実装を差し込む

**ホスティング/CDN 側に依存** 再生成なし

デプロイ

**npx @vinext/cloudflare deploy** ワンコマンド

**node dist/standalone/server.js** PORT・HOST で設定

**任意の静的ホスト** S3・GitHub Pages・Nginx など

使える機能

**SSR・Server Actions** middleware・ISR すべて可

**SSR・Server Actions** middleware・ISR すべて可

**静的ページのみ** SSR・ISR・Server Actions・middleware は不可

※ SSG で追加プラグイン不要という点は、README の記述からの推論（静的エクスポートのみでの動作は未検証）。

（元のページで操作できます → https://memo.taka1156.site/vinext.html#deploy）

## よくある誤解

✗ 誤解: vinext は Next.js のフォーク

✓ 正しくは: フォークではなく API 表面の再実装。Next.js パッケージが無くても動く。

✗ 誤解: ビルドが 4 倍速いので、サイトも 4 倍速くなる

✓ 正しくは: ベンチはビルドとバンドルだけ。配信速度は、本家が事前生成する静的ページではむしろ本家が有利な場面もある。

✗ 誤解: Cloudflare で Next.js を動かすなら vinext 一択

✓ 正しくは: README 自身が「成熟していて安全なのは OpenNext」と書いている。互換性重視なら OpenNext、軽さと Vite 系ツールを取るなら vinext。

✗ 誤解: 静的エクスポートでも Server Actions が使える

✓ 正しくは: 使えない。サーバーが無い構成なので、フォーム送信などは外部 API に向ける必要がある（上の表の SSG 列参照）。

## 移行を試すなら

```
npx vinext check   # 互換性の問題を事前にスキャン
npx vinext init    # 非破壊で移行（既存の next dev もそのまま動く）
npm run dev:vinext # ポート 3001 で vinext 版を起動して見比べる
```

## 出典

- [cloudflare/vinext README（GitHub）](https://github.com/cloudflare/vinext)
- [How we rebuilt Next.js with AI in one week（Cloudflare Blog）](https://blog.cloudflare.com/vinext/)
- [vinext: Cloudflare's Vite-based Next.js replacement（LogRocket）](https://blog.logrocket.com/vinext-cloudflares-vite-based-next-js-replacement/)
- [Cloudflare unveils vinext（IT Brief）](https://itbrief.co.uk/story/cloudflare-unveils-vinext-a-vite-based-next-js-rival)
