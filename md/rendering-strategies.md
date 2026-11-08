<!-- scripts/memo.py build が自動生成。手で編集しない -->

# レンダリング戦略

> CSR・SSR・SSG・ISR・ストリーミング・Server Components・アイランドを「HTML をいつ・どこで作るか」と「JS をどこまで送るか」で比較し、ハイドレーションの仕組みと選び方を図解。

- URL: https://memo.taka1156.site/rendering-strategies.html
- タグ: フロントエンド, JavaScript, 設計
- 日付: 2026-11-03

---

「HTML をいつ作るか」と「どこまで JS で動かすか」の 2 軸で整理する

**ざっくり言うと**

- HTML を作るのが **ブラウザ（CSR）** か、 **リクエストごとのサーバー（SSR）** か、 **ビルド時（SSG）** か。ISR は SSG を期限付きで作り直す折衷。
- SSR / SSG でも、操作できるようにするには同じコンポーネントの JS を送ってイベントをつなぎ直す（ **ハイドレーション** ）。ここが重いと「見えるのに押せない」。
- 最近は「 **動く部分にだけ JS を送る** 」方向。アイランド（Astro）、Server Components（React）、resumability（再開可能性、Qwik）はその実現方法の違い。

## 2 軸の地図

ビルド時 サーバー ブラウザ 送る JS が多い ↑

CSR / SPA 全部ブラウザ

SSR + 全体ハイドレーション 従来の Next / Nuxt

SSG + ハイドレーション

ISR 期限付き SSG

Server Components サーバー専用部品は JS ゼロ

アイランド 動く島だけ JS

MPA（素の SSR）

横軸は「HTML をどこで作るか」、縦軸は「ブラウザに送る JS の量」。下に行くほど初回は軽いが、画面遷移や細かい操作の作り込みはサーバーとのやり取りが増える。

## 表示までの流れ

CSR

SSR

SSG / ISR

ストリーミング

アイランド

サーバー

空

ブラウザ

JS 取得 実行 API 表示＝操作可

**最初は空白** 。JS を取ってから API を呼ぶので往復が直列に重なる。その代わり一度読めば画面遷移は速く、サーバーは静的ファイルを配るだけ。ログイン後の管理画面向き。検索エンジン・SNS のプレビューには中身が見えにくい。

サーバー

データ取得＋HTML 生成

ブラウザ

表示 JS 取得 hydrate 操作可

**中身入りの HTML がすぐ見える** 。ただし表示から操作可能までに隙間があり、その間のクリックは効かない。リクエストごとにサーバー処理が走るので、遅いデータ取得があると TTFB が伸びる。

ビルド

デプロイ前に全ページの HTML を生成（ユーザーは待たない）

CDN

HTML

ブラウザ

表示 JS hydrate 操作可

**最速で安い** が、内容はビルド時点のもの。ページ数が多いとビルドが長い。 **ISR** は「生成から N 秒たったら、次のアクセスで古いものを返しつつ裏で作り直す」（HTTP の stale-while-revalidate と同じ考え方）。初回アクセス時に作る設定もできる。

サーバー

枠 A B

ブラウザ

枠＋読み込み中 A 表示 B 表示

**遅いデータを待たずに先頭から流す** 。ヘッダーやレイアウトをすぐ送り、遅い部分は「読み込み中」を置いて、準備できたら同じレスポンスの続きとして差し込む。React の `<Suspense>` 境界が区切りになる。TTFB と FCP（最初に何かが表示されるまで）を短くできる。LCP は、最大の要素が先に送る枠の側にあるときだけ早まる。

サーバー

HTML

ブラウザ

表示（大半は静的 HTML のまま）

島だけ

JS hydrate

**ページは静的な海、動く部品だけが島** 。島ごとに「すぐ」「見えたら」「アイドル時」などハイドレーションの時期を選べる（Astro の `client:visible` など）。ブログ・ドキュメント・LP のように大半が読むだけのページで JS を大きく減らせる。

（元のページで操作できます → https://memo.taka1156.site/rendering-strategies.html#timeline）

## ハイドレーションとは

サーバーで描画 コンポーネント → HTML 文字列

→

ブラウザで表示 見えるがイベントはない

→

同じコンポーネントを再実行 仮想的に描画し直す

→

既存 DOM と突き合わせ イベントをつなぐ

サーバーとブラウザで **同じ結果** にならないと不一致（hydration mismatch）になり、警告やちらつきが出る。典型は描画中に `Date.now()` ・ `Math.random()` ・ `window` の値・ロケール依存の日付書式を使うこと。ブラウザでしかわからない値は、マウント後（ `useEffect` ・ `onMount` ）に入れる。

Server Components はサーバー専用の部品をハイドレーションの対象から外し、JS を送らない。Qwik の resumability（再開可能性）はハイドレーションの再実行自体をやめ、HTML に状態を書き込んでおき、操作されたハンドラーだけを遅延読み込みする。

## 比較表

| 方式 | HTML の生成 | データの新しさ | サーバー負荷 | 向いている |
| --- | --- | --- | --- | --- |
| CSR | ブラウザ | 常に最新 | 静的配信のみ | ログイン後のアプリ |
| SSR | 毎リクエスト | 常に最新 | 高い | 個人ごと・頻繁に変わる公開ページ |
| SSG | ビルド時 | デプロイ時点 | ほぼゼロ | ドキュメント・ブログ・LP |
| ISR | ビルド時＋期限で再生成 | N 秒遅れ | 低い | EC 商品ページ・ニュース |
| ストリーミング SSR | 毎リクエスト（分割送信） | 常に最新 | 高い | 遅い API を含むページ |
| アイランド | ビルド時 or リクエスト時 | 方式による | 低〜中 | 読む中心で一部だけ動くサイト |

1 つのアプリで混ぜられるのが今のメタフレームワーク（Next.js・Nuxt・SvelteKit・Astro など）。ページやルートごとに決める。

## 選び方

1. **検索・SNS に中身を見せる必要がある？** いいえ（管理画面・ログイン後）→ CSR で十分。サーバーを持たずに済む。
2. **内容はユーザーごとに違う？** 違わない → SSG。更新頻度が高ければ ISR か、HTML は SSG にしてデータ部分だけ後から取得。
3. **ユーザーごと・常に最新が必要** SSR。遅いデータがあるならストリーミングで枠を先に出す。
4. **操作できる部分は一部だけ？** アイランドや Server Components で、その部分にだけ JS を送る。

## 関連メモ

[vinext と Next.js](https://memo.taka1156.site/md/vinext.md) [React と Solid](https://memo.taka1156.site/md/react-vs-solid.md) [Core Web Vitals](https://memo.taka1156.site/md/web-performance.md) [HTTP キャッシュ](https://memo.taka1156.site/md/http-cache.md) [PWA](https://memo.taka1156.site/md/pwa.md)

## 参考

- [web.dev: Rendering on the Web](https://web.dev/articles/rendering-on-the-web)
- [React: Server Components](https://react.dev/reference/rsc/server-components)
- [Astro: Islands architecture](https://docs.astro.build/en/concepts/islands/)
- [Qwik: Resumable](https://qwik.dev/docs/concepts/resumable/)
