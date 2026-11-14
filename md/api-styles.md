<!-- scripts/memo.py build が自動生成。手で編集しない -->

# REST・GraphQL・gRPC・tRPC

> 同じ「ユーザーと最新の投稿を取る」API を REST・GraphQL・gRPC・tRPC で書き比べ、契約の持ち方・キャッシュ・型共有の違いと、REST 設計の基本（冪等性・ステータス・ページング・エラー形式）を図解。

- URL: https://memo.taka1156.site/api-styles.html
- タグ: 設計, フロントエンド, バックエンド
- 日付: 2026-11-03

---

「何で契約を決めるか」と「誰が呼ぶか」で選ぶ

**ざっくり言うと**

- **REST** は URL（リソース）と HTTP メソッドで表す。HTTP のキャッシュや仕組みがそのまま使え、 **誰が呼ぶかわからない公開 API** の標準。
- **GraphQL** は 1 つのエンドポイントに「欲しい形」を送る。画面ごとに欲しいデータが違う **多様なクライアント** に強い。代わりにキャッシュと負荷の管理が難しい。
- **gRPC** は Protocol Buffers の定義から型付きのコードを生成し HTTP/2 で話す。 **サービス間通信** 向け。 **tRPC** は TypeScript の型をそのまま共有する、 **同じリポジトリのフロントとバック** 専用の手段。

## 同じ要求を 4 通りで

「ユーザー 42 の名前と、最新の投稿 3 件のタイトル」を取る。

REST

GraphQL

gRPC

tRPC

```
GET /users/42                    → { id, name, email, avatar, createdAt, … }
GET /users/42/posts?limit=3      → [{ id, title, body, tags, … }, …]
```

2 往復かかり、使わない項目（email・body など）も返る（ **オーバーフェッチ** ）。画面に合わせた `?fields=` や専用エンドポイント（BFF）で補うことが多い。一方、 **どの URL も GET なので CDN やブラウザのキャッシュがそのまま効く** 。契約は OpenAPI で書くのが一般的で、そこからクライアントの型を生成できる。

```
POST /graphql
query {
  user(id: 42) {
    name
    posts(last: 3) { title }
  }
}
→ { "data": { "user": { "name": "…", "posts": [{ "title": "…" }, …] } } }
```

1 往復で、欲しい項目だけが返る。スキーマ（型）が契約になり、ツールが補完や型生成をしてくれる。

落とし穴：① **POST 1 本なので HTTP キャッシュが効きにくい** （Persisted Queries＝永続クエリで GET にする、クライアント側の正規化キャッシュを使う）。② 投稿ごとに著者を取ると DB 問い合わせが N+1 回になる → DataLoader でまとめる。③ 深い入れ子のクエリで重い処理をさせられる → 深さ・コストの上限を設ける。④ 一部のフィールドだけが失敗した部分成功は HTTP 2xx で返る（従来の `application/json` では、エラーでも 200 を返すサーバーが多い）。新しい `application/graphql-response+json` では、検証エラーなどで実行できなかったときは 400 などになる。監視は HTTP ステータスだけでなく `errors` 配列でも見る。

```
// user.proto（契約）
service UserService {
  rpc GetUserWithPosts (GetUserReq) returns (UserWithPosts);
  rpc WatchPosts (WatchReq) returns (stream Post);   // サーバーストリーミング
}
message GetUserReq { int64 id = 1; int32 post_limit = 2; }
```

`.proto` から各言語のクライアント・サーバーのコードを生成する。データはバイナリ（Protocol Buffers）で小さく速く、HTTP/2 上で **双方向ストリーミング** もできる。フィールド番号で互換性を保つので、項目の追加に強い。

ブラウザから素の gRPC は呼べない（HTTP/2 のトレーラーなどを JS から扱えない）。gRPC-Web や Connect のような変換・互換プロトコルを使う。人間が curl で気軽に叩けないのも REST との違い。

```
// サーバー
export const appRouter = router({
  userWithPosts: publicProcedure
    .input(z.object({ id: z.number() }))
    .query(({ input }) => db.user.findWithPosts(input.id, 3)),
});
export type AppRouter = typeof appRouter;

// クライアント（型だけ import。コード生成なし）
const data = await trpc.userWithPosts.query({ id: 42 });
//    ^? { name: string; posts: { title: string }[] }
```

スキーマ定義もコード生成もなく、 **サーバー関数の型がそのままクライアントの型になる** 。サーバーの戻り値を変えると、使っている画面が即座に型エラーになる。

前提は「両方 TypeScript で、型を import できる（モノレポなど）」。他言語や外部の利用者には向かない。実体は HTTP + JSON なので、外に公開する必要が出たら REST / OpenAPI を別に用意する。

（元のページで操作できます → https://memo.taka1156.site/api-styles.html#same）

## 比較

|  | REST | GraphQL | gRPC | tRPC |
| --- | --- | --- | --- | --- |
| 契約 | OpenAPI（任意） | スキーマ（必須） | .proto（必須） | TS の型 |
| データ形式 | JSON が多い | JSON | Protobuf（バイナリ） | JSON |
| 取得範囲 | サーバーが決める | クライアントが決める | サーバーが決める | サーバーが決める |
| HTTP キャッシュ | ◎ そのまま | △ 工夫が要る | × ほぼ使わない | ○ GET の query なら |
| ブラウザ | ◎ | ◎ | △ gRPC-Web 等 | ◎ |
| ストリーミング | SSE を併用 | Subscription | ◎ 双方向 | Subscription |
| 他言語 | ◎ | ◎ | ◎ コード生成 | × TS のみ |

## 誰が呼ぶかで選ぶ

### 外部の開発者

REST + OpenAPI。学習コストが低く、どの言語からも呼べ、キャッシュも効く。

### 自社の複数アプリ

Web・iOS・Android で欲しいデータが違うなら GraphQL。画面単位の BFF を REST で作る手もある。

### マイクロサービス間

gRPC。型付きのコード生成、小さいペイロード、ストリーミング、タイムアウトの伝播。

### 自分の TS フロント

tRPC（や Hono RPC のような型共有の仕組み）。開発速度が最速。外部公開は別口で。

## REST 設計の基本

| メソッド | 用途 | 安全 | 冪等 |
| --- | --- | --- | --- |
| GET | 取得 | ○ | ○ |
| POST | 作成・その他の処理 | × | × |
| PUT | 丸ごと置き換え | × | ○ |
| PATCH | 一部更新 | × | 保証なし |
| DELETE | 削除 | × | ○ |

**安全** ＝サーバーの状態を変えない。 **冪等** ＝同じリクエストを何回送っても、サーバーの状態への効果が 1 回送ったときと同じ（レスポンスは変わってもよい。2 回目の DELETE が 404 になるなど）。冪等なものはタイムアウト時に安心してリトライできる。POST をリトライ可能にしたいときは `Idempotency-Key` ヘッダーを付け、同じキーの 2 回目には処理をせず 1 回目の結果を返させる（決済 API でよく使う。IETF で標準化が進行中）。

ステータスコードの使い分け

- `400` リクエストの形が不正 / `422` 形は正しいが内容がダメ
- `401` 認証されていない / `403` 認証済みだが権限がない
- `404` ない（権限がないことを隠すためにも使う）
- `409` 競合（同時更新・重複）/ `429` レート制限
- `201` 作成した（ `Location` に URL）/ `204` 本文なしで成功

ページング

**オフセット** （ `?page=3` ）は単純だが、深いページほど DB が遅く、途中で追加があると重複・抜けが出る。 **カーソル** （ `?after=eyJpZCI6MTIzfQ` ）は「最後に見た位置の続き」を指すので速く、ずれない。無限スクロールやフィードはカーソル。

```
// エラーの形は RFC 9457 Problem Details に揃えると、クライアントが共通処理しやすい
HTTP/1.1 422 Unprocessable Content
Content-Type: application/problem+json

{
  "type": "https://example.com/problems/invalid-email",
  "title": "メールアドレスの形式が正しくありません",
  "status": 422,
  "detail": "user@ の後ろにドメインがありません",
  "instance": "/users"
}
```

## よくある誤解

✗ 誤解: GraphQL は REST の上位互換

✓ 正しくは: 柔軟さと引き換えに、キャッシュ・認可（項目ごと）・負荷制御を自分で設計する必要がある。クライアントが 1 つで画面も固定なら、REST のほうが単純で速いことが多い。

✗ 誤解: URL に動詞を入れたら REST じゃない

✓ 正しくは: リソースで表しにくい操作（ `POST /orders/42/cancel` ）は現実によくある。大事なのはメソッドの安全性・冪等性を守ることと、一貫した規則。

✗ 誤解: gRPC はブラウザから使えない

✓ 正しくは: そのままでは使えないが、gRPC-Web や Connect で同じ .proto から呼べる。ただし双方向ストリーミングはブラウザでは制限がある。

## 関連メモ

- [HTTP キャッシュ](https://memo.taka1156.site/md/http-cache.md) — REST の GET が効かせられる HTTP キャッシュ
- [リアルタイム通信](https://memo.taka1156.site/md/realtime-comm.md) — サーバーから送る通信（SSE・WebSocket）の選び方
- [DDD とオニオンアーキテクチャ](https://memo.taka1156.site/md/ddd-onion.md) — API の裏側のドメインの組み立て方
- [分散システムの基本](https://memo.taka1156.site/md/distributed-basics.md) — 冪等性とリトライの考え方
- [TypeScript 学習フローと仕組み](https://memo.taka1156.site/md/typescript.md) — tRPC が頼る TypeScript の型

## 参考

- [RFC 9110: メソッドの定義（安全・冪等）](https://www.rfc-editor.org/rfc/rfc9110#name-method-definitions)
- [RFC 9457: Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457)
- [GraphQL: Learn](https://graphql.org/learn/)
- [gRPC: Introduction](https://grpc.io/docs/what-is-grpc/introduction/)
- [tRPC Docs](https://trpc.io/docs)
- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)
