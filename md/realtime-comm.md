<!-- scripts/memo.py build が自動生成。手で編集しない -->

# リアルタイム通信

> ポーリング・ロングポーリング・SSE・WebSocket・WebTransport・WebRTC を、通信の向き・再接続・スケールのしかたで比較し、場面ごとの選び方と落とし穴を図解。

- URL: https://memo.taka1156.site/realtime-comm.html
- タグ: ネットワーク, フロントエンド, インフラ
- 日付: 2026-11-03

---

「サーバーから押したい」を叶える 6 つの方法と、それぞれの向き不向き

**ざっくり言うと**

- HTTP は本来「聞かれたら答える」だけ。サーバーから送るには、 **聞き続ける（ポーリング）** ・ **開いたままにする（SSE）** ・ **別の双方向チャネルを張る（WebSocket など）** のどれか。
- 通知・進捗・AI の逐次出力のような **サーバー → クライアントだけ** なら SSE が手軽（自動再接続つき、普通の HTTP）。チャットや共同編集のような **双方向・高頻度** なら WebSocket。
- 接続を張りっぱなしにする方式は、 **サーバーが接続を覚えている** ので、台数を増やすときに「別のサーバーにいる相手へどう届けるか」が課題になる。

## 6 つの方式

ポーリング

ロングポーリング

SSE

WebSocket

WebTransport

WebRTC

（図: Client / Server / 新着ある？ → ない / 新着ある？ → あった → https://memo.taka1156.site/realtime-comm.html#methods）

一定間隔でリクエストする。 **一番単純で、どこでも動き、キャッシュや認証も普通の HTTP のまま** 。ただし更新は最大で間隔ぶん遅れ、何もなくても通信が発生する。数十秒〜分単位で十分なダッシュボードならこれでよい。

```
setInterval(async () => render(await (await fetch('/api/status')).json()), 30_000);
```

（図: Client / Server / 新着が出るまで待たせて / 保留… / 来た！ / すぐ次の「待たせて」 → https://memo.taka1156.site/realtime-comm.html#methods）

サーバーは新着が出るまでレスポンスを返さずに保留する。返ったらクライアントはすぐ次を投げる。遅延はほぼない一方、 **保留中のリクエストがサーバーの接続とメモリを占有** し、プロキシのタイムアウトとの戦いになる。SSE と WebSocket が使える今は、古い環境向けのフォールバック。

（図: Client / Server / GET /events (Accept: text/event-stream) / data: 1件目 / data: 2件目 / …レスポンスが終わらない → https://memo.taka1156.site/realtime-comm.html#methods）

**Server-Sent Events** 。1 つの HTTP レスポンスを閉じずに、テキストの行を流し続ける。ブラウザの `EventSource` は切れたら **自動で再接続** し、最後に受け取った `id` を `Last-Event-ID` ヘッダーで送ってくれるので、取りこぼしの再送も作りやすい。

```
// クライアント
const es = new EventSource('/events');
es.addEventListener('progress', e => update(JSON.parse(e.data)));

// サーバーが流すテキスト（空行が 1 件の区切り）
id: 42
event: progress
data: {"done": 3, "total": 10}
```

送れるのはテキストだけで、サーバー → クライアントの片方向。 `EventSource` はカスタムヘッダーを付けられないので、認証は Cookie で行う（ヘッダーが必要なら `fetch` でストリームを読む）。HTTP/1.1 では同じオリジンへの接続が 6 本程度に制限され、タブをたくさん開くと詰まる。HTTP/2 以降なら多重化されるので問題になりにくい。LLM の逐次出力（ストリーミング応答）もこの形式が多い。

（図: Client / Server / GET + Upgrade: websocket / 101 Switching Protocols / ここから HTTP ではなくフレーム → https://memo.taka1156.site/realtime-comm.html#methods）

HTTP で始めて `101` で別プロトコルに切り替え、 **1 本の TCP の上で双方向にメッセージ（テキスト／バイナリ）を送り合う** 。ヘッダーのやり取りがない分、小さいメッセージを高頻度に送るのに向く。

```
const ws = new WebSocket('wss://example.com/chat');
ws.onmessage = e => append(JSON.parse(e.data));
ws.onclose = () => setTimeout(connect, backoff());   // 再接続は自分で書く
ws.send(JSON.stringify({ type: 'say', text: 'hi' }));
```

**自動再接続も、届いたかの確認も、取りこぼしの再送もない** ので、アプリ側で作る（Socket.IO などのライブラリはここを埋める）。送信側が速すぎるとバッファが膨らむ（ `bufferedAmount` を見る）。Cookie で認証する場合はハンドシェイクの `Origin` を必ず検証する（他サイトからつながれる CSWSH 攻撃）。

**WebTransport** は HTTP/3（QUIC）の上で、 **複数の独立したストリーム** と、 **届かなくてもよいデータグラム** （UDP のような送りっぱなし）を使える。1 つのメッセージが詰まっても他が待たされず、ゲームの位置情報やライブ配信のように「古いデータは要らない」用途に向く。

```
const wt = new WebTransport('https://example.com:4433/game');
await wt.ready;
const writable = typeof wt.datagrams.createWritable === 'function'
  ? wt.datagrams.createWritable()   // 新しい API（writable は非推奨）
  : wt.datagrams.writable;          // 未対応のブラウザ（Chrome など）は旧 API
const w = writable.getWriter();
w.write(new Uint8Array([x, y]));   // 落ちても再送しない
```

サーバー側は HTTP/3 対応が必要。ブラウザは 2026 年 3 月の Safari 26.4 で主要ブラウザがすべて対応した（Baseline 新規）が、古い OS やブラウザの利用者がいるなら WebSocket へのフォールバックを用意する。社内ネットワークなどで UDP が塞がれている場合も同じ。

**WebRTC** はブラウザ同士を **直接（P2P）** つなぐ。映像・音声の通話と、任意のデータを送る DataChannel がある。NAT を越えるために STUN（自分の外向きアドレスを知る）と TURN（直結できないときの中継）を使い、接続の準備（シグナリング）には別途 WebSocket などが要る。

参加者が多い会議では全員が全員に送ると回線が持たないので、SFU という中継サーバーで束ねる。サーバーとクライアントのやり取りだけなら WebSocket か WebTransport のほうが単純。

## 比較

| 方式 | 向き | データ | 再接続 | 土台 | 向いている |
| --- | --- | --- | --- | --- | --- |
| ポーリング | C→S（応答で受信） | 何でも | 不要 | HTTP | 分単位の更新で十分なもの |
| ロングポーリング | 同上 | 何でも | 自前 | HTTP | 古い環境のフォールバック |
| SSE | S→C | テキスト | 自動 | HTTP | 通知・進捗・AI の逐次出力 |
| WebSocket | 双方向 | テキスト／バイナリ | 自前 | TCP | チャット・共同編集・ゲームのロビー |
| WebTransport | 双方向・複数ストリーム | バイナリ＋データグラム | 自前 | QUIC | ゲーム・低遅延配信 |
| WebRTC | ピア同士 | 映像・音声・データ | 自前 | UDP（ICE） | 通話・画面共有 |

## 台数を増やすときの問題

（図: Alice / Bob / Server 1 / Server 2 / Pub/Sub / Redis / NATS など / ① publish / ② 購読中の全員へ → https://memo.taka1156.site/realtime-comm.html#scale）

Alice と Bob が別のサーバーにつながっていると、Server 1 は Bob に直接送れない。 **全サーバーが共通のメッセージ基盤を購読** して中継するか、同じ部屋の人を同じサーバーに集める（スティッキーセッション、Cloudflare の Durable Objects のように「部屋＝1 つのオブジェクト」にする）。

デプロイで全接続が一斉に切れると、全員が同時に再接続してサーバーを叩く。再接続の待ち時間に **ランダムな揺らぎ（ジッター）付きの指数バックオフ** を入れる。

## 選び方

1. **数十秒遅れても困らない？** はい → ポーリング。インフラもキャッシュもそのまま使える。
2. **サーバーから送るだけ？** はい → SSE。自動再接続が標準でついてくる。再接続時に最後のイベント ID が届くので、サーバー側で差分を送れば取りこぼしも防げる。
3. **クライアントからも高頻度に送る？** はい → WebSocket。
4. **古いデータを捨ててでも遅延を減らしたい／ブラウザ同士でつなぎたい** WebTransport ／ WebRTC。

## 関連メモ

- [HTTP/1.1・2・3 と TLS・DNS](https://memo.taka1156.site/md/web-protocols.md) — HTTP/2・3 と QUIC の土台
- [Redis と Valkey の仕組み](https://memo.taka1156.site/md/redis-valkey.md) — 複数サーバーへ配る Pub/Sub
- [分散システムの基本](https://memo.taka1156.site/md/distributed-basics.md) — 再接続のバックオフ＋ジッターと、重複に備える冪等処理
- [Durable Objects と celld](https://memo.taka1156.site/md/durable-objects.md) — 部屋ごとの WebSocket を Durable Objects で持つ
- [実装起因の脆弱性（入力の扱い）](https://memo.taka1156.site/md/web-vulnerabilities.md) — 受け取ったメッセージを画面に出すときの XSS
- [実装起因の脆弱性（リクエストと権限）](https://memo.taka1156.site/md/request-vulnerabilities.md) — CSWSH の土台になる CSRF と Origin の確認

## 参考

- [HTML Standard: Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/rfc/rfc6455)
- [MDN: WebTransport API](https://developer.mozilla.org/en-US/docs/Web/API/WebTransport_API)
- [MDN: WebRTC API](https://developer.mozilla.org/ja/docs/Web/API/WebRTC_API)
