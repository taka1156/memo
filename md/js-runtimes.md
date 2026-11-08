<!-- scripts/memo.py build が自動生成。手で編集しない -->

# JS ランタイム比較

> Node.js・Bun・Cloudflare Workers の内部構造、プロセス型と isolate 型の違い、API・互換性・制限を比較。

- URL: https://memo.taka1156.site/js-runtimes.html
- タグ: JavaScript, バックエンド
- 日付: 2026-11-02

---

Node.js / Bun / Cloudflare Workers — 同じ JavaScript を、違う仕組みで動かす

**ざっくり言うと**

- 3つとも JS を実行するが、 **JS エンジン** と **周りを支える層** が違う。Node は V8 ＋ libuv、Bun は JavaScriptCore ＋ Rust 製の本体、Workers は V8 ＋ workerd
- Node と Bun はサーバー上で **プロセスとして常駐** する。Workers は世界中のエッジで、1つのプロセスの中に **何千もの isolate（軽い隔離区画）** を並べて動かす
- Workers は起動が数ミリ秒と速い代わりに、ファイルを残しておけるディスクがなく、CPU 時間やメモリに制限がある。用途で選ぶもので、上下関係ではない

## 内部の層構造

Node.js

あなたのコード

Node.js のコア API fs、http、stream、Buffer ＋ fetch など Web 標準

C++ のバインディング

libuv イベントループ・非同期 I/O・スレッドプール

V8 Chrome と同じエンジン

Bun

あなたのコード

Bun API ＋ Node 互換 ＋ Web 標準 Bun.serve、Bun.file、node:fs など

Rust 製の本体 1.4 から。それ以前は Zig

独自のイベントループ Linux は epoll、macOS は kqueue を直接使う（Windows では libuv）

JavaScriptCore Safari と同じエンジン

Workers

あなたのコード

Web 標準 ＋ バインディング fetch、Request / Response、env.KV など。Node.js の API は互換性日付 2026-08-04 以降なら標準で有効（それより前は `nodejs_compat` フラグが必要）

workerd C++ 製。オープンソース

isolate ごとのサンドボックス 1プロセスに多数のテナント

V8 Chrome と同じエンジン

JS エンジンは「JS を解析して機械語にする部分」だけを担う。ファイルを読む、ネットワークを待つといった機能は、その外側の層がランタイムごとに用意している。

## プロセス型と isolate 型

NODE / BUN：プロセス型

サーバー（VM・コンテナ）

**アプリ A** メモリ数十 MB〜 V8 一式

**アプリ B** メモリ数十 MB〜 JSC 一式

- アプリごとに OS のプロセスを立ち上げ、常駐させる
- 起動に数十〜数百ミリ秒。一度起動すれば状態をメモリに持ち続けられる
- OS の機能（ファイル、子プロセス、任意のポート）を自由に使える

WORKERS：ISOLATE 型

エッジのサーバー（世界中の拠点）

**workerd プロセス 1つ**

A社

B社

C社

…

V8 を共有

- 1つのプロセスの中で、テナントごとに **isolate** （メモリが完全に分かれた V8 の実行区画）を作る
- エンジンの起動は済んでいるので、isolate の作成は数ミリ秒。コールドスタートがほぼない
- OS の機能は使えず、外とのやり取りは fetch とバインディングだけ

AWS Lambda などの多くのサーバーレスは「リクエストに応じてコンテナやマイクロ VM を起動する」方式で、Workers とは隔離の単位が違う。

## 同じ HTTP サーバーを書くと

Node.js

Bun

Workers

```
import { createServer } from 'node:http';

createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'text/plain' });
  res.end('hello');
}).listen(3000);
```

Node 独自の `req` / `res` オブジェクト。 `fetch` などの Web 標準も使えるが、サーバー側の標準 API は歴史的な独自形式のまま。

```
Bun.serve({
  port: 3000,
  fetch(req) {
    return new Response('hello');
  },
});
```

Web 標準の `Request` を受けて `Response` を返す形。 `node:http` の書き方もそのまま動く。

```
export default {
  async fetch(request, env, ctx) {
    // env.MY_KV.get('key') のようにバインディングを使う
    return new Response('hello');
  },
};
```

ポートを listen しない。リクエストが来たら `fetch` が呼ばれるだけ。 `env` から KV・R2・D1 などのリソースにアクセスする。

Bun と Workers は **Request → Response** という Web 標準の形に揃っている。Hono のようなフレームワークは、この共通の形の上に作られているので、アプリ本体のコードはどのランタイムでも共通にできる（Node.js では `@hono/node-server` などのアダプターを使う）。

（元のページで操作できます → https://memo.taka1156.site/js-runtimes.html#code）

## 比較表

| 観点 | Node.js | Bun | Workers |
| --- | --- | --- | --- |
| JS エンジン | V8 | JavaScriptCore | V8 |
| 本体の言語 | C++ | Rust（1.3 までは Zig） | C++（workerd） |
| 現行バージョン | 26 が LTS（2026年10月〜） | 1.4 系 | 互換性日付（compatibility date）で管理 |
| TypeScript | 型注釈を取り除いて直接実行（enum など一部の構文は不可） | そのまま実行 | wrangler がビルド時に変換 |
| パッケージ管理 | npm（pnpm、yarn も） | `bun install` を内蔵 | npm などで入れて、ビルド時にバンドル |
| 付属ツール | テストランナー、ウォッチモード | バンドラー、テストランナー、SQLite など全部入り | wrangler（開発・デプロイ CLI） |
| Node 互換性 | 本家 | 高い（大半の npm パッケージが動く） | 主要モジュールに対応（互換性日付 2026-08-04 以降は標準で有効。それより前は `nodejs_compat` フラグが必要） |
| ファイルシステム | あり | あり | メモリ上の仮想ファイルシステムだけ（ `node:fs` で読み書きできるが、 `/tmp` に書いた内容はそのリクエストが終わると消える。残すなら R2・KV などを使う） |
| 制限 | サーバー次第 | サーバー次第 | メモリ 128 MB／リクエストあたり CPU 時間：無料 10 ms、有料は既定 30 秒（最大 5 分） |
| どこで動く | 自分で用意したサーバー、コンテナ、Lambda など | 同左 | Cloudflare のエッジ（ローカルでは workerd で再現） |

Workers の CPU 時間は「計算している時間」だけを数え、fetch の応答待ちなどの待ち時間は含まない。

## それぞれの特徴

Node.js

Bun

Workers

**基準となる存在** 。npm のエコシステムはすべて Node を前提に作られている。2026年10月に LTS になった 26 では、新しい日時 API の Temporal が標準で有効になった。

（元のページで操作できます → https://memo.taka1156.site/js-runtimes.html#features）

### イベントループ（簡略版）

同期コードを実行 → timers → poll（I/O 待ち） → check（setImmediate） → close ↺

JS を実行するのは1スレッドだが、ファイル I/O や DNS などは libuv のスレッドプールが裏で並列に処理する。Promise のコールバック（マイクロタスク）は、コールバックを 1 つ実行し終えるたびに、溜まっている分がまとめて実行される（Node 11 以降。ブラウザと同じ順序）。

**全部入りで速い** 。ランタイム・パッケージマネージャー・バンドラー・テストランナーが1つのバイナリに入っている。 `bun install` の速さから、パッケージマネージャーとしてだけ使う人も多い。

2025年12月に Anthropic が買収（MIT ライセンスのオープンソースのまま）。2026年5月に本体を Zig から Rust に書き直し、1.4 から Rust 版になった。

**エッジで動く軽量ランタイム** 。デプロイすると世界中の拠点に配られ、ユーザーに近い場所で応答する。

状態はバインディングで扱う： **KV** （読み込み中心のキーバリュー）、 **R2** （オブジェクトストレージ）、 **D1** （SQLite ベースの DB）、 **Durable Objects** （1つの場所で状態を持ち続けるオブジェクト）。グローバル変数は同じ isolate が再利用されれば残るが、残る保証はない。

[Cloudflare サービスのメモ](https://memo.taka1156.site/md/cloudflare-services.md) も参照。

## どれを選ぶか

Node.js

- 既存の大きなアプリ
- ネイティブアドオンや特殊なライブラリを使う
- 長く安定して運用したい

Bun

- 開発体験と速度を重視
- ツールを1つにまとめたい
- 新規の API サーバーや CLI

Workers

- 世界中から低遅延で応答したい
- サーバー管理をしたくない
- 短い処理の API、配信の前処理

重い計算・長時間の処理・大きなファイル処理は Node.js か Bun 向き。Workers で扱うなら、キューや Containers と組み合わせる。

## よくある誤解

Bun は Node の完全な代替。置き換えれば全部速くなる

互換性は高いが 100% ではなく、ネイティブアドオンや細かい挙動で差が出ることがある。速さもベンチマークほどの差が実アプリで出るとは限らない（DB やネットワークの待ちが支配的なことが多い）。

Workers でも npm のパッケージは何でも動く

ディスクにファイルが残ることを前提にしたものや、子プロセス、ネイティブアドオンに依存するものは動かない。Node 互換（2026-08-04 以降の互換性日付では標準で有効）で動く範囲は広がったが、すべてではない。

Node はシングルスレッドだから CPU を1つしか使えない

JS の実行スレッドは1つだが、I/O は裏のスレッドプールで並列に動く。CPU を使う処理は `worker_threads` や、プロセスを複数立てて分散できる。

## 関連メモ

[Cloudflare サービス →](https://memo.taka1156.site/md/cloudflare-services.md) [Vite ツールチェーン →](https://memo.taka1156.site/md/vite-toolchain.md)
