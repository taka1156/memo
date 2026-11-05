<!-- scripts/memo.py build が自動生成。手で編集しない -->

# DB のしくみ

> SQL が結果になるまでの流れ、ページとバッファプール、WAL によるクラッシュ復旧、行指向と列指向、そして D1 などクラウドでも使われるようになった SQLite を図解。

- URL: https://memo.taka1156.site/db-internals.html
- タグ: データベース
- 日付: 2026-11-03

---

SQL を投げてから、結果が返り、データが確実に残るまで

**ざっくり言うと**

- SQL は **「何が欲しいか」を書くだけ** 。どう取ってくるか（実行計画）は DB のプランナが統計情報をもとに決める。
- データは **ページ** （数 KB の固定サイズの塊）単位でディスクに置かれ、よく使うページはメモリ（ **バッファプール** ）に載せて使い回す。
- COMMIT の瞬間に確実に書くのは **WAL（変更ログ）だけ** 。本体のデータは後でまとめて書き、落ちても WAL を再生して復旧する。
- **SQLite** は同じ部品をサーバー無しでアプリに組み込んだもの。今では D1 や Turso のように **クラウドの DB サービスの中身** としても使われ、単なるローカル DB ではなくなっている。

## SQL が結果になるまで

各段階を押すと説明が出る。例： `SELECT name FROM users WHERE email = 'a@example.com';`

Parser 構文解析

Analyzer 意味解析

Planner 実行計画

Executor 実行

Storage ページ読み書き

（元のページで操作できます → https://memo.taka1156.site/db-internals.html#pipeline）

## ページとテーブルの置き方

DB は行を1件ずつではなく、 **ページ** （PostgreSQL は 8KB、MySQL の InnoDB は 16KB）単位で読み書きする。1行だけ欲しくても、その行が入ったページ丸ごとを読む。

PostgreSQL（ヒープ）

MySQL InnoDB（クラスタ化）

テーブル本体（ヒープ）は **行を空いているページに順不同で詰める** 。主キーも含め、インデックスは全部「キー → 行の場所（ページ番号＋位置）」を指す別の構造。

更新すると新しい版の行が別の場所に書かれ、古い版は後で VACUUM が片付ける（MVCC。 [次のページ](https://memo.taka1156.site/md/db-index-transaction.md) で詳しく）。

テーブル本体そのものが **主キー順に並んだ B木** （クラスタ化インデックス）。主キーで探すと、そのまま行にたどり着く。セカンダリインデックスは「キー → 主キーの値」を持ち、そこから本体の B木をもう一度たどる。

ランダムな UUID v4 を主キーにすると挿入位置がばらばらになり、ページ分割が増えやすい。時刻順に並ぶ UUID v7 や連番が好まれる理由。

（元のページで操作できます → https://memo.taka1156.site/db-internals.html#pages）

## バッファプールと WAL

メモリ（バッファプール）

p1

p7*

p12

p30*

ページを読むときはまずここを見る。無ければディスクから読み込む。更新はここで行い、まだディスクに書いていないページが dirty 。

ディスク

WAL：…→ p7 変更 → p30 変更 → COMMIT

p1

p7

p12

p30

…

WAL は末尾に追記するだけのログ。データファイルは場所がばらばらなので書くのが遅い。

### UPDATE して COMMIT するまで

1. **メモリ上のページを書き換える** 対象ページをバッファプールに読み込み、そこで行を更新する。ページは dirty になるが、ディスクにはまだ書かない。
2. **変更内容を WAL に追記する** 「どのページのどこをどう変えたか」をログとして書く。追記なので速い。
3. **COMMIT で WAL をディスクに確定（fsync）** WAL がディスクに届いた時点で「コミット完了」をクライアントに返す。 **データファイルはまだ古いまま** でよい。
4. **あとでチェックポイントがまとめて書く** dirty ページは定期的に（チェックポイントで）データファイルへ書き出される。書き終えた分の WAL は不要になる。

### 落ちたらどうなる？

電源が落ちてメモリ上の dirty ページが消えても、 **COMMIT 済みの変更は必ず WAL に残っている** 。再起動時に最後のチェックポイントから WAL を読み直し（REDO）、データファイルを最新に戻す。COMMIT していない変更は反映しない。

同じ WAL をネットワーク越しに送り続けて別サーバーで再生すれば、それがレプリケーション（ストリーミングレプリケーション）。バックアップからの任意時点復旧（PITR）も WAL の再生で行う。

## ACID はどの仕組みが守っている？

| 性質 | 意味 | 主な仕組み |
| --- | --- | --- |
| Atomicity 原子性 | 全部反映か、全く反映しないか | WAL / undo ログ。未コミット分は復旧時に捨てる |
| Consistency 一貫性 | 制約を破った状態にならない | 主キー・外部キー・CHECK などの制約 |
| Isolation 独立性 | 同時に動くトランザクションが干渉しない | ロック・MVCC・分離レベル（ [次のページ](https://memo.taka1156.site/md/db-index-transaction.md) ） |
| Durability 永続性 | COMMIT したら落ちても消えない | WAL の fsync |

## 行指向と列指向

行指向（PostgreSQL, MySQL など）

id 1

山田

東京

¥980

id 2

佐藤

大阪

¥120

1行分がまとまって並ぶ。 **1件を読む・書く** のが速い。注文処理のような日々の業務（OLTP）向け。

列指向（BigQuery, ClickHouse, DuckDB など）

id 1

山田

東京

¥980

id 2

佐藤

大阪

¥120

同じ列の値がまとまって並ぶ。「全注文の金額の合計」のように **少数の列を大量の行で集計** するのが速く、圧縮も効く。分析（OLAP）向け。

## SQLite：組み込み DB からクラウドの DB まで

PostgreSQL や MySQL は **別プロセスのサーバー** にネットワーク越しで問い合わせる。SQLite は **ライブラリとしてアプリの中に組み込まれ、ファイル1つを直接読み書きする** 。中にあるパーサ・プランナ・B木のページ・ログ（WAL）といった部品は、ここまでの話とほぼ同じ。この「小さくて軽いエンジン」という性質が、後で見るようにクラウドでも活かされている。

クライアント・サーバー型

アプリ

⇄ ネットワーク

DB サーバー 別プロセス

→

データファイル群

クエリ1回ごとに往復の通信がかかる。接続数の管理、ユーザー権限、複数台からの同時書き込みが得意。

組み込み型（SQLite）

アプリ ＋ SQLite 同じプロセス内の関数呼び出し

→

app.db ファイル1つ

通信が無いのでクエリ1回はマイクロ秒単位。小さなクエリを何十回も投げる（N+1）書き方でもあまり困らない。バックアップはファイルのコピーに近い。

### 書き込みは同時に1つだけ

SQLite はデータベースファイル単位でロックするので、 **書き込みトランザクションは常に1つずつ** 。既定（rollback journal）では書いている間は読み込みも止まるが、 **WAL モード** にすると変更を別ファイル（ `app.db-wal` ）に追記するので、 **書き込み中も読み込みは止まらない** 。

書き込み1回が速い（特に WAL モードで `synchronous = NORMAL` にすると、COMMIT のたびに fsync しないので大きく速くなる）ので、「1台のサーバーのアプリ」なら書き込み1本でも足りることが多い。足りなくなるのは、高頻度の書き込みが長いトランザクションで詰まるときや、複数のサーバーから同じ DB に書きたいとき。

### なぜ今また注目されている？

- **ハードウェアが速くなった** ：NVMe SSD と大きなメモリで、1台・1ファイルで捌ける量が大きく増えた。
- **弱点を補う道具がそろった** ：Litestream（WAL を S3 などに送り続ける継続バックアップ）、libSQL / Turso（SQLite のフォークと Rust での書き直し。Rust 版の Turso エンジンでは、 `BEGIN CONCURRENT` で複数の書き込みを並行させる MVCC が 2026年8月から Turso Cloud でアーリープレビュー中。本番向けではない）。
- **クラウドの DB エンジンになった** ：Cloudflare D1 や Turso Cloud は、SQLite をサーバー側で動かして API 越しに提供する。詳しくは 次の項 。
- **フレームワークや実行環境が標準で抱えた** ：Rails 8 は SQLite を本番でも使える前提にし、ジョブキュー・キャッシュ・WebSocket まで SQLite で動く構成を用意した。Node.js は `node:sqlite` を内蔵し（v25.7 で Release Candidate に昇格）、Bun にも `bun:sqlite` がある。
- **「1ユーザー（1テナント・1エージェント）に1つの DB」** ：ファイル1つなので、大量の小さな DB を作って捨てる使い方と相性が良い。AI エージェントごとに DB を持たせる用途も増え、2026年10月には Supabase が Turso の買収に合意した。

### 単なるローカル DB ではなくなった

SQLite の使われ方は大きく3つに広がっている。どれも中身は同じ SQLite で、 **「書き込みは1 DB につき1本」という性質も同じ** 。違うのは、誰がそのファイルを持ち、どこから使うか。

① アプリに組み込む

アプリ ＋ SQLite

→

app.db

従来の使い方。スマホ・デスクトップ・1台のサーバー。ファイルの管理（バックアップ・複製）は自分で行う。

② DB サービスの中身にする

Worker / アプリ

→ API

D1・Turso Cloud 中で SQLite が動く

ファイルの置き場所・複製・バックアップをサービスが引き受ける。アプリからは普通のリモート DB に見え、複数のサーバーやエッジから使える。

③ 小さな DB を大量に

テナント A

テナント B

エージェント C

…

1つの巨大 DB ではなく、利用者ごとに独立した DB を持たせる。SQLite は1つあたりが軽いので、数十万〜数百万個でも成り立つ。

CLOUDFLARE D1 の場合

- Workers から SQL を投げるサーバーレス DB で、中身は SQLite。 **1つの DB はシングルスレッドで、最大 10GB** 。大きくするより DB を分けて増やす（アカウントあたり最大 100 万 DB）。
- 読み取りレプリカ（ベータ）や、直近 30 日の任意の時点に戻せる Time Travel をサービス側が用意している。

Hyperdrive＋PlanetScale（Postgres / MySQL）との比較は [D1 と Hyperdrive＋PlanetScale](https://memo.taka1156.site/md/cloudflare-databases.md) にまとめた。

TURSO（libSQL）の場合

- SQLite フォークの libSQL をサーバーとして動かし、HTTP・WebSocket 越しに提供する。
- **埋め込みレプリカ** ：アプリの手元に SQLite ファイルのコピーを持ち、読み込みはローカルの速さ、書き込みはリモートのプライマリへ送って同期する。①と②のいいとこ取り。
- 「エージェントごとに DB」を売りにしていて、2026年10月に Supabase が買収に合意した。

つまり「SQLite＝ローカル専用」ではなく、 **「SQLite＝軽くて大量に作れる DB エンジン」** として、置き場所はアプリの中にもクラウドにもなった。ただし1 DB への書き込みが1本なのは変わらないので、書き込みが集中するなら **DB を分ける設計** がセットになる。

### 向く・向かない

向く

- 1台のサーバーで動く Web アプリ・社内ツール（読み込みが多いと特に有利）
- スマホ・デスクトップアプリ、ブラウザ（WASM）、組み込み機器
- テナントごと・ユーザーごとに分けた DB
- テストや開発環境、CLI ツール、データの受け渡し用ファイル

向かない

- 1つの DB に、全利用者の書き込みが集中し続ける構成（D1 などサービス経由でも、1 DB の書き込みは1本）
- 書き込みが非常に多く、長いトランザクションが混ざる処理
- 複数台から、NFS などの共有ディスク上の同じファイルを **直接** 開く構成（ロックが信用できず壊れ得る。複数台から使うなら D1・Turso のようなサービス経由かサーバー型 DB に）
- DB 側で細かいユーザー権限や行単位のアクセス制御をしたい

### 本番で使うときの定番設定

```
PRAGMA journal_mode = WAL;     -- 書き込み中も読める（ファイルに保存される設定）
PRAGMA busy_timeout = 5000;    -- ロック中なら即エラーにせず最大 5 秒待つ
PRAGMA synchronous = NORMAL;   -- WAL なら壊れない。電源断で直前の COMMIT が消える可能性と引き換えに速い
PRAGMA foreign_keys = ON;      -- 外部キー制約は既定で無効！接続ごとに有効にする
```

- 書き込むトランザクションは `BEGIN IMMEDIATE` で始める。 `BEGIN` （DEFERRED）で読んでから書こうとすると、途中で書き込みロックが取れず `SQLITE_BUSY` になりやすい。
- 型は既定ではゆるい（INTEGER 列に文字列が入る）。厳しくしたいなら `CREATE TABLE ... STRICT` 。
- バックアップは稼働中のファイルを `cp` せず、 `VACUUM INTO` ・ `.backup` ・Litestream を使う（WAL ファイルとの整合が取れないため）。

```
// Node.js 内蔵の SQLite（追加のパッケージ不要）
import { DatabaseSync } from 'node:sqlite';

const db = new DatabaseSync('app.db');
db.exec('PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;');
db.exec('CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY, title TEXT NOT NULL) STRICT');
db.prepare('INSERT INTO todos (title) VALUES (?)').run('牛乳を買う');
console.log(db.prepare('SELECT * FROM todos').all());
```

## よくある誤解

✕ SQLite はテスト用のおもちゃで、本番には使えない

○ スマホやブラウザの中で最も多く動いている DB で、1台構成の Web アプリなら本番でも十分に使える。限界は性能ではなく「書き込みが1本」「1台のマシン」という構造の方。

✕ COMMIT が返った時点で、テーブルのデータファイルは更新済み

○ 確実に書かれているのは WAL だけ。データファイルへの反映はチェックポイントで後から行われる。それでも WAL があるので永続性は守られる。

✕ SQL を書いた順番どおりに処理される

○ JOIN の順番や使うインデックスはプランナが決める。同じ SQL でもデータ量や統計情報が変わると実行計画が変わり、急に遅くなることがある。

✕ メモリを増やせば DB は無限に速くなる

○ 効くのは「よく使うページがバッファプールに収まるまで」。それ以降は実行計画（インデックスの有無）や書き込み量の方が支配的になる。

## 関連

[インデックスとトランザクション](https://memo.taka1156.site/md/db-index-transaction.md) [Git の内部構造](https://memo.taka1156.site/md/git-internals.md)

## 参考

- [PostgreSQL: The Path of a Query](https://www.postgresql.org/docs/current/query-path.html)
- [PostgreSQL: Write-Ahead Logging (WAL)](https://www.postgresql.org/docs/current/wal-intro.html)
- [MySQL: Clustered and Secondary Indexes](https://dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html)
- [SQLite: Write-Ahead Logging](https://www.sqlite.org/wal.html) / [Appropriate Uses For SQLite](https://www.sqlite.org/whentouse.html)
- [Node.js: node:sqlite](https://nodejs.org/api/sqlite.html)
- [Cloudflare D1](https://developers.cloudflare.com/d1/) / [D1 Limits](https://developers.cloudflare.com/d1/platform/limits/) / [SQLite in Durable Objects GA](https://developers.cloudflare.com/changelog/2025-04-07-sqlite-in-durable-objects-ga)
- [Rails 8.0: No PaaS Required](https://rubyonrails.org/2024/11/7/rails-8-no-paas-required)
- [Turso: Concurrent Writes in Practice（2026-08）](https://turso.tech/blog/concurrent-writes-in-practice)
- [What is Turso](https://turso.tech/what-is-turso) / [Supabase raises $150M and agrees to acquire Turso（2026-10）](https://runtimewire.com/article/supabase-raises-150m-acquires-turso)
- [The SQLite Renaissance（DEV Community）](https://dev.to/pockit_tools/the-sqlite-renaissance-why-the-worlds-most-deployed-database-is-taking-over-production-in-2026-3jcc)
