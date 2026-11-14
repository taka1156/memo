<!-- scripts/memo.py build が自動生成。手で編集しない -->

# D1 と Hyperdrive＋PlanetScale

> Cloudflare Workers から使う DB を、SQLite ベースの D1 と、Hyperdrive 経由の PlanetScale（Postgres / MySQL）で比較。仕組み・得意不得意・選び方を図解。

- URL: https://memo.taka1156.site/cloudflare-databases.html
- タグ: インフラ, データベース
- 日付: 2026-11-03

---

Workers から使う DB は「SQLite を大量に」か「Postgres / MySQL を1つ大きく」か

**ざっくり言うと**

- **D1** は Cloudflare の中で動く **SQLite** 。1つの DB は小さく（最大 10GB）書き込みは1本ずつだが、 **DB を大量に作って分ける** 前提で横に広げる。
- **Hyperdrive** は DB ではなく、Workers から **既存の Postgres / MySQL へ速くつなぐための接続プール＋キャッシュ** 。PlanetScale はその先に置く本格的な DB で、Cloudflare のダッシュボードから作れて請求もまとめられる。
- テナントごとに分けられる・SQLite で足りるなら D1。 **1つの大きなデータを全員で共有** する、Postgres の機能や既存資産を使いたいなら Hyperdrive＋PlanetScale。

## 構成の違い

D1

ユーザー

↓ 最寄りのデータセンター

Worker

↓ バインディング（env.DB）

D1 プライマリ 中身は SQLite。書き込みはここに集まる

読み取りレプリカ ベータ

読み取りレプリカ

DB も Cloudflare の網の中にある。接続文字列も接続プールも要らない。

Hyperdrive ＋ PlanetScale

ユーザー

↓

Worker Placement で DB の近くで動かせる

↓ 普通の Postgres / MySQL ドライバ

Hyperdrive 接続プール＋読み取りクエリのキャッシュ

↓ 使い回す接続

PlanetScale Postgres または MySQL（Vitess）。AWS / GCP のリージョンで動く

DB は外のクラウドにある。Hyperdrive はその「距離」と「接続の重さ」を吸収する役。

## なぜ Hyperdrive が要る？

Postgres や MySQL は、つなぐたびに TCP・TLS・認証の往復が何回も要る。普通のサーバーは接続を張りっぱなしにして使い回すが、 **Worker はリクエストごとに起動して終わる** ので、毎回この往復をやり直すことになる。

直接つなぐ

1. TCP 接続（1往復）
2. TLS ハンドシェイク（1〜2往復）
3. DB の認証（数往復）
4. やっとクエリ（1往復）

遠い DB だと、これを毎リクエスト

Hyperdrive 経由

1. Worker → 近くの Hyperdrive（すぐ）
2. Hyperdrive は DB への接続を **張りっぱなしでプール** している
3. クエリだけを DB に送る。よく使う読み取りはキャッシュから返す

重い往復は最初の1回だけ

Hyperdrive は無料プランでも使える。PlanetScale 以外の Postgres / MySQL（AWS RDS、Supabase、Neon など）にもつなげられ、ドライバや ORM はいつものものが使える。

## 比較表

|  | D1 | Hyperdrive ＋ PlanetScale |
| --- | --- | --- |
| DB エンジン | SQLite | Postgres / MySQL（Vitess） |
| 広げ方 | DB を分けて横に 増やす（アカウントあたり最大 100 万 DB） | 1つの DB を大きく する（MySQL は Vitess でシャーディングも） |
| 1 DB の大きさ | 最大 10GB（有料プラン） | 実質ほぼ気にしなくてよい規模まで |
| 書き込み | 1 DB はシングルスレッドで1つずつ | 多数の接続から同時に書ける |
| SQL の機能 | SQLite の範囲（FTS5・JSON・数学関数などの組み込み拡張のみ。Postgres の拡張や行レベルセキュリティは無い） | Postgres の拡張・RLS・複雑な JOIN・ストアドなど |
| Worker からの接続 | バインディングで呼ぶだけ | Hyperdrive の接続文字列を普通のドライバに渡す |
| Workers 以外から | HTTP API（主に管理・バッチ向け） | 普通の DB としてどこからでも |
| 遅延の考え方 | DB の場所＋読み取りレプリカ | DB のリージョン＋Placement で Worker を近くに＋キャッシュ |
| 復旧 | Time Travel（直近 30 日の任意の分。無料プランは 7 日） | PlanetScale のバックアップ・ブランチ |
| 料金の入口 | 無料枠あり | Postgres 単一ノードで月 $5〜（Cloudflare の請求にまとめられる） |
| 持ち出しやすさ | SQLite なのでファイルとしては持ち出せるが、サービスは Cloudflare 専用 | 標準の Postgres / MySQL なので他へ移しやすい |

## どっちにする？

当てはまるものにチェック。

D1

Hyperdrive＋PS

## 組み合わせる

どちらか一方にしなくてよい。Workers からは両方を同時にバインドできる。

- **本体は PlanetScale、利用者ごとの状態は D1** ：会員・注文・決済のように全員で共有するデータは Postgres、ユーザーごとの下書きや設定、AI エージェントの作業メモは D1 に1人1 DB。
- **Durable Objects の SQLite** ：チャットルームや共同編集の部屋のように「1つの単位に1つの状態」で、しかも即時に同期したいものは、Durable Objects に内蔵された SQLite（2025年4月に正式提供）が向く。
- **KV・R2 は別枠** ：設定値や読み込み中心の小さな値は KV、画像やファイルは R2（ [Cloudflare サービス](https://memo.taka1156.site/md/cloudflare-services.md) 参照）。

## よくある誤解

✗ 誤解: Hyperdrive は Cloudflare の Postgres サービス

✓ 正しくは: Hyperdrive 自体はデータを持たない。外にある Postgres / MySQL へのつなぎ役（接続プール＋キャッシュ）。DB 本体は PlanetScale などで別に用意する。

✗ 誤解: Hyperdrive を挟めば書き込みも速くなる

✓ 正しくは: 速くなるのは接続の確立と、キャッシュできる読み取り。書き込みは毎回 DB まで届く。DB のリージョンが遠いなら、Placement で Worker を DB の近くで動かす方が効く。キャッシュは書き込みで消えない。既定では `max_age` 60 秒に再検証中の 15 秒が加わり、最長で 75 秒ほど古い値を返し得る。書いた直後の読み取りや認証・権限まわりは、 **キャッシュを無効にした別の Hyperdrive 設定（バインディング）** から読む。

✗ 誤解: D1 は Postgres と同じように使える

✓ 正しくは: SQL の方言は SQLite。型がゆるい、使えない関数や構文がある、などの違いがあり、Postgres 向けの ORM 設定やマイグレーションはそのまま流用できないことが多い。

✗ 誤解: D1 も読み取りレプリカを増やせば書き込みが捌ける

✓ 正しくは: レプリカは読み取り専用。書き込みが詰まるなら DB を分ける。

## 関連メモ

- [Cloudflare サービス](https://memo.taka1156.site/md/cloudflare-services.md) — D1・Hyperdrive 以外のサービスとの組み合わせ
- [DB のしくみ](https://memo.taka1156.site/md/db-internals.md) — D1 の中の SQLite の仕組み
- [インデックスとトランザクション](https://memo.taka1156.site/md/db-index-transaction.md) — インデックスと分離レベル

## 参考

- [Cloudflare D1](https://developers.cloudflare.com/d1/) / [D1 Limits](https://developers.cloudflare.com/d1/platform/limits/)
- [Cloudflare Hyperdrive](https://developers.cloudflare.com/hyperdrive/) / [Query caching](https://developers.cloudflare.com/hyperdrive/concepts/query-caching/)
- [Deploy Postgres and MySQL databases with PlanetScale + Workers（2026-04）](https://blog.cloudflare.com/deploy-planetscale-postgres-with-workers)
- [Create PlanetScale Postgres and MySQL databases, billed to your Cloudflare account（2026-06）](https://developers.cloudflare.com/changelog/post/2026-06-18-planetscale-databases-cloudflare-billing/)
- [SQLite in Durable Objects GA（2025-04）](https://developers.cloudflare.com/changelog/2025-04-07-sqlite-in-durable-objects-ga)
