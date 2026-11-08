<!-- scripts/memo.py build が自動生成。手で編集しない -->

# CORS と同一オリジンポリシー

> オリジンの判定、ブラウザが何を止めているのか、単純リクエストとプリフライト、Cookie 付きの制約までを図解。

- URL: https://memo.taka1156.site/cors-sop.html
- タグ: セキュリティ, フロントエンド
- 日付: 2026-11-02

---

「CORS エラー」の正体は、ブラウザがユーザーを守るための制限

**ざっくり言うと**

- ブラウザは、 **別オリジンから取ってきたレスポンスを JS に読ませない** 。これが同一オリジンポリシー (SOP)
- CORS は、サーバーが「このオリジンからなら読んでいい」と **ヘッダーで許可を出して、その制限を緩める** 仕組み
- 多くの場合、リクエストはサーバーに届いて処理もされている。止められているのは「JS が結果を読むこと」

## オリジンとは

オリジンは **スキーム・ホスト・ポート** の3つの組。1つでも違えば別オリジン。パスやクエリは関係ない。

https スキーム :// app.example.com ホスト : 443 ポート /users?id=1 関係なし

基準： `https://app.example.com` で動いているページから見て、次の URL は同じオリジン？（クリックで判定）

自分で URL を入力して試す：

（元のページで操作できます → https://memo.taka1156.site/cors-sop.html#origin）

## SOP が止めるもの・止めないもの

### 止める：読み取り

- `fetch` / XHR のレスポンスを JS で読む
- 別オリジンの iframe の中身（DOM）を触る
- canvas に描いた別オリジン画像のピクセルを読む

### 止めない：送信・埋め込み

- フォームの送信（別オリジンへの POST）
- `<img>` 、 `<script>` 、 `<link>` での読み込み
- リンクやリダイレクトでの遷移

Web は昔から「他サイトの画像を貼る」「他サイトにフォームを送る」ことで成り立ってきたので、送ること自体は止められない。だから **SOP があっても CSRF は起きる** 。SOP が守るのは「ログイン中のユーザーの画面やデータを、悪意あるサイトの JS が盗み読むこと」。

## どこで止まっているのか

（図: ページの JS / app.example.com / ブラウザ / CORS をチェック / API サーバー / api.other.com / ① fetch() → リクエストは届く / ② 処理して 200 を返す / 許可ヘッダーなし / ③ JS には渡さない → https://memo.taka1156.site/cors-sop.html#where）

このため、単純リクエストの POST などは **サーバー側で処理が完了している** こともある。「CORS で失敗したから何も起きていない」とは限らない。プリフライトが必要なリクエストだけは、許可が出るまで本番のリクエスト自体が送られない。

## 単純リクエストとプリフライト

「昔からフォームでも送れた種類のリクエスト」は、そのまま送られる（単純リクエスト）。それ以外は、先に `OPTIONS` で「送っていい？」と確認する（プリフライト）。条件を選ぶと、どちらになるか判定できる。

メソッド GETPOSTHEADPUTDELETEPATCH

Content-Type （なし） application/x-www-form-urlencoded multipart/form-data text/plain application/json

追加ヘッダー （なし） Accept-Language Authorization X-Requested-With

（元のページで操作できます → https://memo.taka1156.site/cors-sop.html#preflight）

### プリフライトのやり取り

```
① ブラウザ → サーバー（自動で送られる）
OPTIONS /api/items HTTP/1.1
Origin: https://app.example.com
Access-Control-Request-Method: PUT
Access-Control-Request-Headers: authorization, content-type

② サーバー → ブラウザ
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: authorization, content-type
Access-Control-Max-Age: 600

③ 許可が出たので、本番のリクエストを送る
PUT /api/items/42 HTTP/1.1
Origin: https://app.example.com
Authorization: Bearer ...
```

`Max-Age` の間はプリフライトの結果がキャッシュされ、毎回 OPTIONS が飛ぶのを防げる（ブラウザごとに上限あり）。

## CORS のヘッダー一覧

| ヘッダー | 向き | 意味 |
| --- | --- | --- |
| `Origin` | 要求 | リクエスト元のオリジン。ブラウザが自動で付け、JS からは変えられない |
| `Access-Control-Request-Method` | 要求 | （プリフライト）本番で使いたいメソッド |
| `Access-Control-Request-Headers` | 要求 | （プリフライト）本番で付けたいヘッダー |
| `Access-Control-Allow-Origin` | 応答 | 読んでいいオリジン。1つだけか `*` 。複数許可したいときは、サーバーが `Origin` を見て返し分ける |
| `Access-Control-Allow-Methods` | 応答 | 許可するメソッド |
| `Access-Control-Allow-Headers` | 応答 | 許可するリクエストヘッダー |
| `Access-Control-Allow-Credentials` | 応答 | `true` なら Cookie 付きのレスポンスも読ませる |
| `Access-Control-Expose-Headers` | 応答 | JS から読めるレスポンスヘッダーを追加する（標準ではごく一部しか読めない） |
| `Access-Control-Max-Age` | 応答 | プリフライト結果のキャッシュ秒数 |
| `Vary: Origin` | 応答 | Origin によって返し分けるときに付ける。忘れると CDN が別オリジン向けの応答をキャッシュして配ってしまう |

## Cookie を送るときの制約

別オリジンへの `fetch` は、標準では Cookie を送らない。送るには両側の設定が要る。

```
// フロント
fetch('https://api.example.com/me', { credentials: 'include' })

// サーバーの応答
Access-Control-Allow-Origin: https://app.example.com   ← * は不可
Access-Control-Allow-Credentials: true
```

Cookie 付きのときは、 `Allow-Origin` ・ `Allow-Headers` ・ `Allow-Methods` に `*` が使えず、具体的な値を書く必要がある。「全オリジンから Cookie 付きで読める」状態を作らせないため。

### 「オリジン」と「サイト」は違う

オリジン（CORS の単位）

スキーム＋ホスト＋ポート。 `app.example.com` と `api.example.com` は **別オリジン** 。

サイト（Cookie の SameSite の単位）

スキーム＋登録可能ドメイン（ `example.com` の部分）。上の2つは **同じサイト** 。

そのため「サブドメイン違いの API」は、CORS の設定は必要だが、 `SameSite=Lax` の Cookie はそのまま送れる。CSRF 対策との関係は [JWT とセッション](https://memo.taka1156.site/md/jwt-vs-session.md) を参照。

## ハマったときの確認ポイント

エラーの読み方

よくある原因

開発中の回避

コンソールのメッセージに「どのヘッダーが足りないか」が書いてある。ネットワークタブでは、 **OPTIONS のリクエストが別の行** として出ているので、そちらの応答ヘッダーとステータスを見る。

- サーバーが **500 などのエラー** を返し、エラー応答に CORS ヘッダーが付いていない（本当の原因はサーバーエラー）
- OPTIONS を認証ミドルウェアが弾いて 401 を返している（プリフライトには認証情報が付かない）
- `credentials: 'include'` なのに `Allow-Origin: *`
- オリジンの末尾に `/` を付けて登録している（ `https://app.example.com/` は一致しない）

開発サーバーのプロキシを使うと、ブラウザから見て同じオリジンになるので CORS 自体が発生しない。

```
// vite.config.ts
export default {
  server: {
    proxy: { '/api': 'http://localhost:8080' }
  }
}
```

本番でも、フロントと API を同じドメインの配下に置く（リバースプロキシ）と CORS 設定が不要になる。 [Vite ツールチェーン](https://memo.taka1156.site/md/vite-toolchain.md) も参照。

（元のページで操作できます → https://memo.taka1156.site/cors-sop.html#debug）

## よくある誤解

✗ 誤解: CORS はサーバーを攻撃から守る仕組み

✓ 正しくは: 守っているのは **ユーザー** 。curl やサーバー間通信には何の制限もかからないので、API 自体の認証・認可は別に必要。

✗ 誤解: curl だと通るのに CORS エラーになるのはサーバーのバグ

✓ 正しくは: CORS はブラウザだけが行うチェック。curl は許可ヘッダーを見ないので通って当然。

✗ 誤解: `mode: 'no-cors'` にすれば直る

✓ 正しくは: エラーは消えるが、レスポンスは中身の読めない「opaque」になる。データを使いたいなら意味がない。CORS はフロントだけでは直せず、サーバーの設定が必要。

✗ 誤解: CORS を設定していれば CSRF は防げる

✓ 正しくは: 単純リクエスト（フォーム送信と同じ形）は CORS と関係なく送られ、サーバーで処理される。CSRF は SameSite Cookie や CSRF トークンで防ぐ。

## 関連メモ

[JWT とセッション（CSRF と SameSite）→](https://memo.taka1156.site/md/jwt-vs-session.md) [Vite ツールチェーン →](https://memo.taka1156.site/md/vite-toolchain.md)
