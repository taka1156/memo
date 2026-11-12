<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Durable Objects と celld

> 名前で呼べる「状態を持つ 1 つの実体」Durable Objects の仕組み・ライフサイクル・設計と課金のツボ、自前のサーバーで同じコードを動かす celld の仕組みと違いを図解。

- URL: https://memo.taka1156.site/durable-objects.html
- タグ: インフラ, バックエンド, 設計
- 日付: 2026-11-13

---

名前で呼べる「状態を持つ 1 つの実体」と、それを自前のサーバーで動かすしくみ

**ざっくり言うと**

- Durable Objects は、名前ごとに世界で 1 つだけ存在し、専用の SQLite を持つ Worker の一種。
- 1 オブジェクトは 1 スレッドで動き、使われないと休止してメモリを捨て、呼ばれると起き直す。
- celld は同じコードを自前のサーバーとバケットで動かす OSS。配置・エッジ機能は自分で持つ。

## なぜ必要か

普通の Worker は **ステートレス** で、同じユーザーのリクエストでも世界中の別々の場所・別々のインスタンスで動きます。そのため「チャットルームの参加者一覧」「残り 3 席の座席」のように、 **全員が同じ 1 つの状態を見て、順番に更新したいもの** を置く場所がありません。KV は書き込みが各地に届くまで時間がかかり、外部 DB に置くとロックや競合の扱いが必要になります。

Durable Object (DO) はその「1 か所」を作るしくみです。 `room-42` という名前で呼べば、東京からでもロンドンからでも **同じ 1 つのオブジェクト** に届き、そのオブジェクトだけが自分の SQLite を読み書きします。

（図: Worker（東京） / ステートレス / Worker（ロンドン） / Worker（NY） / getByName / "room-42" / Durable Object / room-42 / JS クラス＋メモリ / 1 スレッドで 1 件ずつ / 専用の SQLite / 他のオブジェクトからは見えない → https://memo.taka1156.site/durable-objects.html#why）

注目: 名前で決まる 1 つの実体

アクターモデルとしての性質（1 件ずつ処理・入力ゲートと出力ゲート）は [並行処理のモデル](https://memo.taka1156.site/md/concurrency-models.md) 、KV・D1 との整合性の比較は [分散システムの基本](https://memo.taka1156.site/md/distributed-basics.md) にまとめています。

## 名前で呼ぶ：ID・stub・RPC

DO は「クラス（種類）」と「インスタンス（1 つ 1 つ）」の 2 段です。Worker にはクラスごとの **名前空間 (namespace)** がバインディングとして渡され、そこから ID を作って **stub** （そのオブジェクトへの窓口）を得ます。インスタンスは最初に呼ばれたときに自動で作られるので、作成・削除の API を呼ぶ必要はありません。

| 作り方 | 何が決まるか | 向く場面 |
| --- | --- | --- |
| `getByName("room-42")` `idFromName()` → `get()` | 同じ名前なら必ず同じオブジェクト | 部屋 ID・ユーザー ID・ドキュメント ID など、すでに名前があるもの |
| `newUniqueId()` | ランダムな ID。 `toString()` を保存しておかないと二度と届かない | 新しく作るセッションやジョブなど、名前を付ける必要がないもの |

```
// src/index.ts
import { DurableObject } from "cloudflare:workers";

export class ChatRoom extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    // 起動のたびに走る。テーブルが無ければ作る
    ctx.storage.sql.exec(
      "CREATE TABLE IF NOT EXISTS msgs (id INTEGER PRIMARY KEY, body TEXT)");
  }
  async post(body) {                      // RPC メソッド
    this.ctx.storage.sql.exec("INSERT INTO msgs (body) VALUES (?)", body);
    return this.ctx.storage.sql.exec("SELECT count(*) AS n FROM msgs").one().n;
  }
}

export default {
  async fetch(req, env) {
    const room = env.CHAT_ROOM.getByName("room-42");  // stub
    const n = await room.post(await req.text());      // 別の場所で動くオブジェクトを呼ぶ
    return new Response(`${n} 件目`);
  },
};
```

```
// wrangler.jsonc（抜粋）
{
  "durable_objects": {
    "bindings": [{ "name": "CHAT_ROOM", "class_name": "ChatRoom" }]
  },
  "migrations": [{ "tag": "v1", "new_sqlite_classes": ["ChatRoom"] }]
}
```

stub のメソッドを呼ぶ形が **RPC** 。HTTP で受けたいなら DO 側に `fetch()` を書き、 `stub.fetch(req)` で渡す。新しいクラスは `migrations` の `new_sqlite_classes` で宣言する（SQLite を使う形）。

## ライフサイクル：起きる・休む・起き直す

DO は常に動き続けるサーバーではありません。リクエストが来たら起き、しばらく何もなければ **休止 (hibernation)** してメモリを手放します。

1. **最初の呼び出し** オブジェクトが作られ、最初のリクエストに近いデータセンターに置かれる（ロケーションヒントで地域を指定することもできる）。 `constructor` が走る。
2. **処理中** リクエスト・RPC・WebSocket のメッセージ・アラームを 1 スレッドで順に処理する。メンバー変数をキャッシュとして使える。
3. **アイドル** 何もない状態が約 10 秒続くと休止する。タイマー・終わっていない I/O・標準 API の WebSocket があって休止できないときも、70〜140 秒ほどでメモリから追い出される。 **どちらでもメモリ上の状態は消える** 。デプロイなどで予告なく止まることもあるので、残したいものはその都度ストレージに書いておく。
4. **また呼ばれる** 同じ名前で呼ばれると起き直し、 `constructor` がもう一度走る。ストレージの中身はそのまま残っている。
5. **アラーム** `ctx.storage.setAlarm(時刻)` で、誰からも呼ばれなくても決めた時刻に起こせる（ `alarm()` ハンドラが呼ばれる）。1 オブジェクトに 1 つ。期限切れの掃除や定期集計に使う。

## ストレージ：オブジェクト専用の SQLite

各オブジェクトは自分専用のストレージを持ち、 **トランザクションがあり、強い整合性** （書いた直後の読み取りに必ず反映される）です。他のオブジェクトからは直接読めません。

- **SQL API** : `ctx.storage.sql.exec(sql, ...params)` 。テーブル・インデックス・JOIN が使える。いまの標準（新しいクラスはこちら）。
- **KV API** : `ctx.storage.get / put / delete / list` 。SQLite を使うクラスでも同じメソッドが使える。
- **まとめて書く** : `ctx.storage.transactionSync(() => { ... })` 。中で例外が出たら全部取り消し。
- **大きさ** : 有料プランで 1 オブジェクト 10 GB まで。それを超えそうなら、オブジェクトを分けるか D1 / R2 に逃がす。

SQLite はオブジェクトと同じスレッド・同じマシンで動くので、 `sql.exec()` は同期的に呼べて非常に速く、ネットワーク越しの DB のような往復の待ちがありません。書き込みの確定を待たずにコードが進んでも、 **出力ゲート** が確定するまで応答を止めるので「保存できていないのに成功を返す」ことは起きません（詳しくは [入力ゲートと出力ゲート](https://memo.taka1156.site/md/concurrency-models.md) ）。

## WebSocket は休止できる形で受ける

チャットや共同編集では、DO が部屋の全員の WebSocket を持ち、届いたメッセージを他の全員に配ります。受け方は 2 通りあり、課金が大きく変わります。

### ws.accept()（標準 API）

接続を開いている間、オブジェクトはずっと起きている。誰も話していなくても **接続中はずっと実行時間が課金される** 。

### ctx.acceptWebSocket(ws)（Hibernation API）

接続は Cloudflare 側が保ったまま、オブジェクトは休止できる。メッセージが来たら起きて `webSocketMessage()` が呼ばれる。 **静かな時間は課金されない** 。

```
export class ChatRoom extends DurableObject {
  async fetch(req) {
    const [client, server] = Object.values(new WebSocketPair());
    this.ctx.acceptWebSocket(server);              // 休止できる形で受ける
    return new Response(null, { status: 101, webSocket: client });
  }
  async webSocketMessage(ws, msg) {                 // 起きるたびに呼ばれる
    for (const peer of this.ctx.getWebSockets()) peer.send(msg);
  }
}
```

休止から起きるとメモリは空なので、接続ごとの情報（ユーザー名など）は `ws.serializeAttachment()` で接続に付けておく。通信方式の比較は [リアルタイム通信](https://memo.taka1156.site/md/realtime-comm.md) 。

## 設計：どう分けるか

1 オブジェクトは 1 スレッドなので、処理できる量に上限があります（目安は 1 秒あたり 1,000 リクエストほどのソフトリミットで、超えると overloaded エラー）。速くしたいときは 1 つを強くするのではなく、 **同時に触られる単位でオブジェクトを細かく分けます** 。オブジェクトの数に上限はありません。

良い分け方

失敗しやすい分け方

- **チャットルーム 1 つ = 1 オブジェクト** : 部屋の中のメッセージ順と参加者一覧を 1 か所で決められる。
- **公演 1 つ（または座席ブロック 1 つ）= 1 オブジェクト** : 同じ席の二重予約を、ロックなしで防げる。
- **ドキュメント 1 つ = 1 オブジェクト** : 共同編集の操作をここで順番に並べ、全員に配る。
- **ユーザー 1 人 = 1 オブジェクト** : レート制限・AI エージェントの会話状態など、その人だけのもの。
- **全ユーザー共通のカウンターを 1 オブジェクトに** : 全リクエストが 1 本のスレッドに集まり、詰まる。必要なら分割して後で合計する。
- **オブジェクトをまたぐ集計を毎回する** : 「全部屋の発言数ランキング」を毎回全オブジェクトに聞きに行くと遅い。集計用の DB（D1 など）へ書き出しておく。
- **メモリだけに状態を持つ** : 休止や再起動で消える。正しさに関わる値は必ずストレージに書く。
- **外部 API の `await` をまたいで読み書き** : その間に別のリクエストが割り込める。前後で読み直すか、待ちの前に書き込みを済ませる。

（元のページで操作できます → https://memo.taka1156.site/durable-objects.html#design）

### いつ DO を選ぶか

| やりたいこと | 向くもの |
| --- | --- |
| 部屋・在庫・座席など、同時更新を 1 か所で正しく | Durable Objects |
| WebSocket で多人数をつなぐ | Durable Objects（Hibernation API） |
| 全データを横断して検索・集計する普通のテーブル | D1 や外部 DB（ [D1 と Hyperdrive](https://memo.taka1156.site/md/cloudflare-databases.md) ） |
| 読み込み中心の設定値・キャッシュ | KV |
| 画像・ファイル | R2 |

## 課金のツボ

料金は「リクエスト数」「実行時間 (duration)」「ストレージ（読んだ行・書いた行・保存量）」の組み合わせです。単価より、 **何が課金対象になるか** を押さえておくと設計で困りません。

- **実行時間は壁時計で数える** : CPU を使っていなくても、オブジェクトが起きていて休止できない間は課金される（メモリ 128 MB 分）。
- **休止できない原因を作らない** : `ws.accept()` した WebSocket、終わっていない `fetch` やタイマーはオブジェクトを起こしたままにする。
- **WebSocket の受信メッセージは割安** : 20 件で 1 リクエストとして数える。送信は数えない。
- **ストレージは行単位** : 読んだ行・書いた行で課金される。インデックスの無い全件スキャンは読んだ行が増える。

無料プランでも SQLite を使う DO は使える（無料枠を超えるとその種類の操作がエラーになる）。正確な単価と無料枠は Cloudflare の料金ページで確認する。

## celld：同じコードを自前のサーバーで

**celld** は、Deno 社（Node.js・Deno の作者 Ryan Dahl）が 2026 年 8 月に公開したオープンソース (Apache-2.0) のデーモンです。Workers と Durable Objects のアプリを、 **手持ちの `wrangler.json` のまま自分のマシンで動かします** 。KV・Queues・D1・R2・Workflows・Cron Triggers・静的アセットにも対応します。2026 年 10 月時点の版は v0.6.3 で、ベータ版の扱いです。なお 2026 年 10 月、Deno のチームが Cloudflare に加わり、celld のコードと考え方を Workers のランタイム workerd に取り込んで、workerd を自前で動かせるようにしていく方針が発表されました。今後は workerd 側の動きもあわせて確認してください。

celld では 1 つのオブジェクトを **セル (cell)** と呼びます。KV の名前空間やキューはそれぞれ 1 つのセルで、Workflow はインスタンスごとに 1 つのセルとして動きます。D1 のデータベースもセルの中の SQLite として持たれ、どれも DO と同じしくみで複製・引き継ぎされます。

### しくみ：バケットが「誰の担当か」を決める

（図: ロードバランサ（TLS 終端） / ノード A / room-42 / 担当（SQLite） / ノード B / B に来た room-42 宛ては / A に転送 / ノード C / 別のセルを担当 / ／空きなら予備 / ① 他ノード 1〜2 台のディスクへ → 確定 / ② あとでアップロード / バケット（S3 互換・GCS・Azure Blob） / …/room-42/own.json / 担当と epoch（条件付きで取る） / …/room-42/ltx/… / DB の中身（長期の正本） → https://memo.taka1156.site/durable-objects.html#celld-arch）

自前のサーバー（celld ノード） 注目しているセル 書き込みが確定する経路

1. **ノードとフリート** 1 台のマシンで 1 つの `celld` プロセス（ノード）を動かす。同じバケットを共有するノードの集まりが **フリート (fleet)** 。各ノードは V8 を内蔵する。 `celld deploy` が Wrangler 形式のプロジェクトを esbuild でバンドルしてバケットに置き、各ノードがそれを読み込んで実行する。
2. **担当を取る** セルごとの担当記録 `own.json` を、バケットの **条件付き書き込み** （「無ければ作る」「読んだときから変わっていなければ上書き」）で取り合う。成功するのは 1 ノードだけなので、 **1 つのセルを同時に 2 台が担当することがない** 。合意プロトコル（Raft など）や管理サーバーは要らない。
3. **epoch で古い担当を締め出す** セルを起動するたびに（別ノードへの引き継ぎでも、同じノードで起き直すときでも）番号 (epoch) が進み、書き込み先のパスに入る。担当を失った古いノードがまだ書いても、もう使われない場所に書くだけになる（フェンシング）。
4. **書き込みを確定させる** SQLite への書き込みは LTX という形式で記録される。2 台以上のフリートでは他の 1〜2 台のディスクに届いた時点で確定し、バケットへはその後で上げる。 **1 台だけだと毎回バケットへの書き込みを待つので、かなり遅い** 。
5. **引き継ぐ** ノードが止まったり、休止中のセルを別のノードが起こしたりすると、新しい担当がバケットから DB を復元して続きを動かす。ノードは使い捨てで、バケットが正本。

要は「バケットの条件付き書き込みが正しく動くこと」が全体の土台です。S3 互換ストレージの違いは [S3 互換ストレージの仕組み](https://memo.taka1156.site/md/s3-compatible.md) 。

### Cloudflare との違い

|  | Cloudflare DO | celld |
| --- | --- | --- |
| どこで動くか | Cloudflare の世界中のデータセンター。最初の利用者の近くに自動で置く | 自分のフリートのどれかのノード。配置・地域の指定（jurisdiction など）はない |
| 運用 | マシン・ルーティング・障害時の切り替えは Cloudflare が持つ | ノードの監視・再起動（systemd・Kubernetes など）、TLS 終端、内部ネットワークの保護は自分で持つ |
| 保存先 | Cloudflare 内部のストレージ | 自分のバケット。条件付き書き込みに対応したもの（S3・R2・Tigris・GCS・Azure Blob）が必要 |
| 使えるサービス | Workers AI・Vectorize・Hyperdrive・Browser Rendering なども含む全部 | Workers・DO・KV・Queues・D1・R2・Workflows・Cron など。ネットワークや GPU が要るものは対象外 |
| Cache API | エッジの共有キャッシュ | 共有キャッシュが無いので常にミス |
| WebSocket | 休止しても接続は保たれる | 同じノードでの休止は保たれるが、 セルが別ノードに移ると切れる 。クライアント側で再接続が必要 |
| 設定ファイル | `wrangler.toml / .json / .jsonc` | `wrangler.json / .jsonc` のみ。 `routes` など未対応のキーがあるとデプロイが止まる |
| コスト | リクエスト・実行時間・ストレージの従量課金 | ノードのマシン代とバケット代。動いていないセルはバケットに置いてあるだけなので、ほぼかからない |

### 試す

```
# ローカルで 1 ノード（バケットなし。状態は .celld/dev に残る）
celld dev

# 本番: バケットにデプロイして、各マシンでノードを起動
celld deploy . --bucket s3://my-cells-bucket
celld --bucket s3://my-cells-bucket --listen 0.0.0.0:8080 \
  --internal-listen 10.0.0.12:8081 --advertise 10.0.0.12:8081

# バケットが条件付き書き込みに対応しているかを確かめる
celld diagnose --bucket s3://my-cells-bucket
```

8080 はロードバランサ経由で公開し、8081（ノード同士の通信）はプライベートネットワークか WireGuard・Tailscale などの暗号化された経路だけに置く。ノード同士の通信は TLS なしの平文 HTTP。HMAC で確かめるのはトンネルの確立と制御リクエストだけで、トンネル内の通信には署名がなく、内部リスナーの運用 API にも認証のない経路がある。

### どちらを選ぶか

- **Cloudflare DO** : 運用を持ちたくない、世界中のユーザーの近くで動かしたい、Workers AI などのサービスも使いたい。
- **celld** : データを自分のクラウド・自分のバケットに置きたい、常時動くオブジェクトが多く従量課金が重い、Cloudflare 以外の場所でも同じコードを動かせるようにしておきたい。ただしベータ版で、ノードとネットワークの運用は自分の仕事になる。

## よくある誤解

✗ 誤解: Durable Object はずっとメモリに載っている常駐サーバーだ

✓ 正しくは: 使われていなければ十数秒で休止し（休止できなくても数分以内に追い出され）、メモリ上の値は消える。起き直すと `constructor` から作り直されるので、残したい値はストレージに書く。

✗ 誤解: Durable Objects を使えばどれだけアクセスが集中しても大丈夫

✓ 正しくは: 1 オブジェクトは 1 スレッドなので、1 つに集中すると詰まる。部屋・ユーザー・ドキュメントなど、同時に触られる単位でオブジェクトを分ける。

✗ 誤解: WebSocket をつないでいれば、どちらの API で受けても料金は同じ

✓ 正しくは: `ws.accept()` は接続中ずっとオブジェクトを起こしておくので、静かな時間も実行時間が課金される。 `ctx.acceptWebSocket()` （Hibernation API）なら静かな間は休止できる。

✗ 誤解: celld なら Cloudflare と同じく世界中のエッジで動く

✓ 正しくは: celld が動くのは自分で用意したノードだけ。世界中に置くならその分のノードを用意し、配置や地域の制御もない。Cloudflare のネットワークが必要なサービス（Workers AI など）も使えない。

✗ 誤解: S3 互換ストレージならどれでも celld のバケットに使える

✓ 正しくは: 担当の取り合いに条件付き書き込みを使うので、それを正しく実装したストレージが必要。対応していないものでは 2 台が同じセルを担当してしまう恐れがあり、 `celld diagnose` で確かめる。
