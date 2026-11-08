<!-- scripts/memo.py build が自動生成。手で編集しない -->

# JS と Web 標準の決まり方

> JavaScript の言語は TC39、ブラウザ API は WHATWG と W3C、サーバー側ランタイムの共通 API は TC55（WinterTC）。4 つの団体の分担と、仕様が決まるまでの流れを図解。

- URL: https://memo.taka1156.site/js-web-standards.html
- タグ: JavaScript, フロントエンド
- 日付: 2026-11-03

---

TC39・WHATWG・W3C・TC55（WinterTC）は、それぞれ何を決めているのか

**ざっくり言うと**

- **言語そのもの** （構文・ `Promise` ・ `Array` ）は Ecma の **TC39** が決める。
- **ブラウザの API** は **WHATWG** （HTML・DOM・Fetch など）と **W3C** （CSS・Web Crypto など）が分担。 `setTimeout` も言語ではなく HTML の仕様。
- **サーバー側ランタイム** （Node.js・Cloudflare Workers など）で共通に使える Web API の範囲は、Ecma の **TC55（WinterTC）** が決める。

## このコード、どこが決めている？

ふだん書くコードを 1 行ずつ見ると、決めている団体がばらばらです。ボタンで絞り込めます。

全部

TC39

WHATWG

W3C

TC55

`class Cart { #items = []; }` 言語の構文（ECMA-262） TC39

`const data = JSON.parse(text);` 組み込みオブジェクト（ECMA-262） TC39

`new Intl.DateTimeFormat('ja-JP')` 国際化 API（ECMA-402） TC39

`const res = await fetch('/api/items');` Fetch Standard WHATWG

`new URL('./img.png', import.meta.url)` URL Standard WHATWG

`document.querySelector('#out')` DOM Standard WHATWG

`setTimeout(tick, 1000);` HTML Standard（タイマー・イベントループ） WHATWG

`await crypto.subtle.digest('SHA-256', buf)` Web Cryptography API W3C

`const t0 = performance.now();` High Resolution Time W3C

`.list { display: grid; }` CSS W3C

`export default { fetch: (req) => new Response('ok') }` サーバーで `Request` / `Response` が使えること（ECMA-429） TC55

TC55 の行に注目。 `Response` そのものの仕様は WHATWG の Fetch ですが、「サーバー側のランタイムでもこれを用意する」と決めているのが TC55 です。

（元のページで操作できます → https://memo.taka1156.site/js-web-standards.html#who）

## 4 つの団体

TC39

Ecma International の技術委員会

決めるもの

言語仕様 ECMAScript（ECMA-262）、国際化 API（ECMA-402）

成果物の形

毎年の版（ES2025、ES2026…）

決め方

提案ごとにステージを進める。会議での合意（consensus）で決定

WHATWG

ブラウザ開発企業が運営するコミュニティ

決めるもの

HTML、DOM、Fetch、URL、Streams、Encoding、Console など

成果物の形

Living Standard（版番号なしで随時更新）

決め方

複数のブラウザ実装者が支持した変更を取り込む

W3C

会員制の Web 標準化団体

決めるもの

CSS、Web Crypto、File API、WebAuthn、WebAssembly、WCAG など

成果物の形

勧告（Recommendation）。草案から段階を踏んで確定

HTML / DOM

WHATWG の版を勧告として承認する役

TC55

Ecma の技術委員会。通称 WinterTC

決めるもの

サーバー側ランタイムが共通で持つ Web API の範囲

成果物の形

ECMA-429 Minimum Common Web API（毎年のスナップショット）

やり方

API を新しく作るより、既存の Web API から選ぶのが中心

## ブラウザとサーバーで比べると

どちらも土台は同じ ECMAScript。その上に載る API の範囲が違います。

ブラウザ

**W3C** CSS・Web Crypto・File API・WebAuthn など

**WHATWG** HTML・DOM・Fetch・URL・Streams setTimeout、イベントループ、document、localStorage も

**TC39** ECMAScript 構文・Promise・Array・JSON・Intl

サーバー（Node.js・Workers など）

**各ランタイム独自** node:fs、Workers のバインディング 標準の外。ランタイムを変えると書き直しになる部分

**TC55** Minimum Common API WHATWG と W3C の API から、サーバーでも使えるものを選んだ共通セット（fetch・URL・Streams・crypto など）

**TC39** ECMAScript ブラウザと同じ

ECMAScript には「いつ非同期処理を実行するか」の仕組みは書かれていません。それを用意するのは実行環境（ホスト）の役目で、ブラウザでは HTML 仕様のイベントループ、Node は libuv を使った自前の実装です。 `setTimeout` の細かい挙動がブラウザと Node で違うことがあるのはこのためです。

## TC39：提案が仕様になるまで

新しい機能は「提案（proposal）」として出され、ステージを 1 つずつ進みます。ステージを押すと条件が出ます。

Candidate・Finished などの英語の呼び名は旧版のもので、今の公式プロセス文書は主に番号と目的で説明しています（Stage 0 だけは今も strawperson と呼ばれます）。

### 年 1 回の版

Stage 4 の提案 3 月の会議までに揃ったもの

→

候補ドラフト 2〜3 月に確定作業

→

Ecma 総会で承認 夏

→

ES20XX その年の版

「ES2026 の新機能」は、その年の版に入った Stage 4 の提案のこと。ブラウザは版の発行を待たず、Stage 3 の段階から順に実装していきます。

## WHATWG と W3C の関係

HTML と DOM は、2019 年の合意から **WHATWG の Living Standard が唯一の本体** です。W3C は別の HTML を書くのではなく、その一時点のコピーに「勧告」という承認を付けます。

Living Standard WHATWG が随時更新

→ 約半年ごと →

Review Draft その時点のスナップショット

→

W3C の勧告 同じ文書に承認を付ける

| 見たいもの | どこを見る |
| --- | --- |
| HTML・DOM・Fetch の最新の仕様 | WHATWG の Living Standard（ `*.spec.whatwg.org` ） |
| CSS・Web Crypto・WCAG の仕様 | W3C の仕様（ `w3.org/TR/` ） |
| 実際にどのブラウザで動くか | MDN の互換性表、Can I use、web-platform-tests の結果（wpt.fyi） |

web-platform-tests（WPT）は両団体とブラウザが共有するテスト集。仕様どおりに実装されているかはここで確かめます。

## TC55（WinterTC）：サーバー側の共通 API

WinterCG 2022 年。W3C のコミュニティグループ

→

Ecma TC55（WinterTC） 2025 年 1 月に移行

→

ECMA-429 第 1 版 2025 年 12 月採択

W3C のコミュニティグループは正式な標準を発行できないため、標準を出せる Ecma に移りました。W3C とは引き続き連携しています。

### Minimum Common API に入っている主な API

準拠するランタイムはこれらをすべて実装する決まりです。出どころの団体ごとに分けると、ほとんどが WHATWG と W3C の API だとわかります。

WHATWG Fetch・URL・URL Pattern・Streams・Encoding・Compression・XHR（FormData）・DOM・HTML・Console

`fetch` `Request` `Response` `Headers` `FormData` `URL` `URLSearchParams` `URLPattern` `ReadableStream` `TransformStream` `TextEncoder` `TextDecoder` `CompressionStream` `AbortController` `EventTarget` `setTimeout` `queueMicrotask` `structuredClone` `atob` `console`

W3C Web Crypto・File API・High Resolution Time・WebAssembly

`crypto.subtle` `CryptoKey` `Blob` `File` `performance` `WebAssembly`

入っていない（画面やブラウザ前提のもの）

`document` `window` `localStorage` `alert` `XMLHttpRequest`

### サーバーでは仕様どおりにいかない部分

サーバーには「今開いているページ」がありません。そのため Fetch の一部はブラウザと違う動きになり、ECMA-429 でも違いを文書化することを求めています。

- ページのオリジンがないので、ブラウザのように `Origin` ヘッダーを自動では付けない
- Cookie の保存場所（cookie jar）がないので、Cookie は自動で送られない
- CORS のようなブラウザ向けの保護も、サーバー同士の通信では前提にならない

TC55 はこうした違いを Fetch の仕様側（WHATWG）に反映してもらう方向で調整しています。ほかに、TCP/TLS ソケット、環境変数や引数を読む CLI 向け API、HTTP サーバーの API なども検討中です。

### 実際のコードでの意味

複数のランタイムで動かしたいライブラリは、 **Minimum Common API の範囲で書く** のが目安になります。Hono のように `Request` を受けて `Response` を返す形のフレームワークが Node.js でも Workers でも動くのは、この共通部分の上に乗っているからです。

TC55 には Deno・Igalia（共同議長）、Cloudflare、Bloomberg などが関わっています。Bun は正式なメンバーではありません。Bun にも `fetch` や `Response` はありますが、ECMA-429 に沿うことを約束しているわけではないので、Bun でも動くかは個別に確かめます。

## よくある誤解

✗ 誤解: `setTimeout` や `console` は JavaScript の言語機能

✓ 正しくは: HTML Standard と Console Standard（WHATWG）で決まっている。ECMAScript には入っていない

✗ 誤解: HTML の仕様は W3C が作っている

✓ 正しくは: 本体は WHATWG の Living Standard。W3C はそのスナップショットを勧告として承認する

✗ 誤解: Stage 3 になった機能はどのブラウザでも使える

✓ 正しくは: Stage 3 は「実装を始めてよい」段階。使えるかどうかは各ブラウザの実装状況で確かめる

✗ 誤解: TC55 はサーバー専用の新しい API を作る団体

✓ 正しくは: 中心は既存の Web API から共通セットを選ぶこと。サーバーで違う動きが必要な点は WHATWG や W3C の仕様に戻して直す

## 関連メモ

[JS ランタイム比較 →](https://memo.taka1156.site/md/js-runtimes.md) [CORS と同一オリジンポリシー →](https://memo.taka1156.site/md/cors-sop.md) [TypeScript 学習フローと仕組み →](https://memo.taka1156.site/md/typescript.md)

出典: [The TC39 Process](https://tc39.es/process-document/) ／ [W3C と WHATWG の覚書（2019）](https://www.w3.org/2019/04/WHATWG-W3C-MOU.html) ／ [W3C ブログ：WinterTC について（2025）](https://www.w3.org/blog/2025/collaborating-across-w3c-and-ecma-for-web-interoperable-server-runtimes-through-wintertc/) ／ [ECMA-429](https://ecma-international.org/publications-and-standards/standards/ecma-429/) ／ [Minimum common web API](https://min-common-api.proposal.wintertc.org/) ／ [WinterTC の TPAC 2025 発表資料](https://people.igalia.com/abotella/pub/TPAC-2025-WinterTC/) （2026 年 11 月 3 日時点）
