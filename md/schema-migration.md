<!-- scripts/memo.py build が自動生成。手で編集しない -->

# スキーマ設計とマイグレーション

> 正規化と制約でテーブルを設計し、ORM とマイグレーションツールで変更を管理し、拡張→移行→縮小の手順とロックの少ない DDL で、サービスを止めずにスキーマを変える方法を図解する。

- URL: https://memo.taka1156.site/schema-migration.html
- タグ: データベース, バックエンド, 設計
- 日付: 2026-11-14

---

テーブルを作り、サービスを止めずに変えていく

**ざっくり言うと**

- スキーマ設計は、同じ事実を 1 か所にだけ置く（正規化）ことと、守りたい決まりを制約で DB に持たせることが土台。
- 変更は番号付きのマイグレーションファイルにして順に適用し、どこまで適用したかを DB の中の履歴表で管理する。
- 止めずに変えるには、新旧のコードが同時に動いても壊れない「拡張 → 移行 → 縮小」に分け、重いロックを取る DDL を避ける。

## 正規化: 同じ事実は 1 か所に

注文を 1 枚の表にまとめると書くのは楽だが、同じ顧客や商品の情報が何行にも複製される。複製があると、直し漏れや消しすぎが起きる（ **更新時異常** ）。正規化は、表を「何についての事実か」ごとに分けて、複製をなくす作業。

正規化前

正規化後

orders（1 枚にまとめた表）

| 注文 ID | 顧客名 | 顧客メール | 商品名 | 単価 | 数量 |
| --- | --- | --- | --- | --- | --- |
| 1001 | 佐藤 | sato@example.com | ノート | 300 | 2 |
| 1001 | 佐藤 | sato@example.com | ペン | 120 | 5 |
| 1002 | 佐藤 | sato@old.example.com | ノート | 300 | 1 |
| 1003 | 鈴木 | suzuki@example.com | 消しゴム | 100 | 3 |

同じ事実の複製 直し漏れで食い違った値

**更新の異常** 佐藤さんがメールを変えたら全行を直す必要がある。1 行でも漏れると、どれが正しいか分からなくなる。

**挿入の異常** まだ誰も注文していない新商品は、注文の行がないので登録できない。

**削除の異常** 鈴木さんの注文 1003 を消すと、鈴木さんという顧客の情報まで消える。

customers

| id | 名前 | メール |
| --- | --- | --- |
| 1 | 佐藤 | sato@example.com |
| 2 | 鈴木 | suzuki@example.com |

products

| id | 名前 | 単価 |
| --- | --- | --- |
| 10 | ノート | 300 |
| 11 | ペン | 120 |
| 12 | 消しゴム | 100 |

orders

| id | customer_id | 注文日時 |
| --- | --- | --- |
| 1001 | 1 | … |
| 1002 | 1 | … |
| 1003 | 2 | … |

order_items

| order_id | product_id | 数量 | 注文時の単価 |
| --- | --- | --- | --- |
| 1001 | 10 | 2 | 300 |
| 1001 | 11 | 5 | 120 |
| 1002 | 10 | 1 | 300 |
| 1003 | 12 | 3 | 100 |

🔑 主キー 点線の下線 外部キー（ほかの表の主キーを指す）

メールは customers の 1 行を直せば済み、新商品は products に足せ、注文を消しても顧客は残る。

実務では「 **第 3 正規形** （主キー以外の列が、主キーにだけ依存している状態）まで分けて、必要なら意図して崩す」が目安になる。

- **注文時の単価・送り先住所は複製ではない。** 「その注文のときの値」という別の事実なので、order_items や orders に持つのが正しい。products の単価を後で変えても、過去の注文の金額は変わってはいけない。
- **非正規化 (denormalization)** は、読み込みを速くするためにわざと複製を持つこと（注文件数を顧客の表に持つ、など）。どこで値を更新するかを決め、ずれたら作り直せるようにしておく。

（元のページで操作できます → https://memo.taka1156.site/schema-migration.html#normalize）

## 主キー・型・制約

| 決めること | よくある選び方 | 理由・注意 |
| --- | --- | --- |
| 主キー | 業務の値（メールなど）ではなく、意味を持たない ID（代理キー）。 `bigint` の自動採番か UUID | メールや社員番号は変わることがある。ID を URL に出して推測されたくないなら UUID（推測しにくくなるだけで、認可チェックの代わりにはならない。 [実装起因の脆弱性](https://memo.taka1156.site/md/request-vulnerabilities.md) ）。B 木のインデックスには、時刻順に並ぶ UUIDv7 のほうが挿入位置が散らばらず向く |
| 金額 | `numeric` （ `decimal` ）か、最小単位の整数（円・セント） | `float` は 0.1 を正確に表せない（ [浮動小数点](https://memo.taka1156.site/md/floating-point.md) ） |
| 日時 | PostgreSQL なら `timestamptz` 。UTC で保存し、表示で変換 | タイムゾーンなしの型に入れると、どの時刻か分からなくなる（ [日付・時刻・タイムゾーン](https://memo.taka1156.site/md/datetime-timezone.md) ） |
| 制約 | `NOT NULL` ・ `UNIQUE` ・ `FOREIGN KEY` ・ `CHECK` を DB に付ける | アプリの検証だけだと、同時に 2 つのリクエストが来たときや、別のアプリ・手作業の SQL からの書き込みで破られる |

```
-- 「同じメールで二重登録しない」はアプリで SELECT してから INSERT では防げない（同時に 2 件来ると両方通る）
CREATE TABLE customers (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email      text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE order_items (
  order_id   bigint NOT NULL REFERENCES orders(id),
  product_id bigint NOT NULL REFERENCES products(id),
  quantity   integer NOT NULL CHECK (quantity > 0),
  unit_price numeric(10, 0) NOT NULL,
  PRIMARY KEY (order_id, product_id)
);
```

分散 SQL では、連番や時刻順の主キーが 1 台に書き込みを集めるホットスポットになる（ [NewSQL・分散 SQL](https://memo.taka1156.site/md/newsql.md) ）。1 台の RDB とは向くキーが違う。

## ORM・クエリビルダー・生の SQL

アプリから DB を触る道具は、SQL をどれだけ隠すかで並べられる。どれを使っても、DB で実際に走る SQL を確かめられるようにしておく（ログに出す・ `EXPLAIN` する）。

**生の SQL**

```
SELECT * FROM orders
WHERE customer_id = $1
```

DB の機能をすべて使え、速さも読める。結果の型付けや組み立ては自分で（sqlc のように SQL から型付きコードを生成する道具もある）。

**クエリビルダー**

```
db.select().from(orders)
  .where(eq(orders.customerId, id))
```

SQL とほぼ 1 対 1 の関数で組み立て、型の補完が効く。例: Kysely、Drizzle、Knex。

**ORM**

```
customer.orders  // 関連を辿るだけ
```

表をオブジェクトとして扱い、関連の読み込みや保存を任せる。例: Prisma、Active Record（Rails）、Django ORM、Hibernate。

← SQL がそのまま見える SQL が隠れる →

ORM でいちばん多い事故は **N+1 問題** : 注文 100 件を取ってから、ループの中で 1 件ずつ顧客を取ると、クエリが 1 + 100 回走る。関連をまとめて読む指定（Prisma の `include` 、Rails の `includes` など）か JOIN で 1〜2 回にする（ [インデックスとトランザクション](https://memo.taka1156.site/md/db-index-transaction.md) ）。

## マイグレーションの仕組み

スキーマの変更を、 **順番の付いたファイル** としてコードと一緒にバージョン管理する。ツールは DB の中に「どのファイルまで適用したか」の履歴表を持ち、まだのファイルだけを順に流す。

001_create_customers.sql 適用済み

002_create_orders.sql 適用済み

003_add_orders_status.sql 適用済み

004_add_customers_full_name.sql 未適用

migrate

**履歴表**

001・002・003 を記録済み。今回は 004 だけを流して記録する。

名前の例: `schema_migrations` （Rails）、 `flyway_schema_history` （Flyway）、 `_prisma_migrations` （Prisma）

| 書き方 | やること | 例 |
| --- | --- | --- |
| バージョン管理型（versioned） | 変更の手順（ `ALTER TABLE …` ）を 1 ファイルずつ書く。ORM のスキーマから差分を生成して、出来たファイルを見直すことも多い | Flyway、Liquibase、Rails、Django、Prisma Migrate、drizzle-kit generate |
| 宣言型 | あるべき最終形のスキーマだけを書き、ツールが今の DB との差分から手順を計算する | Atlas、sqldef、drizzle-kit push |

- **適用済みのファイルは書き換えない。** 直したいときは新しいファイルを足す。本番と開発で中身が食い違う原因になる。
- CI で空の DB に全ファイルを流すテストをし、デプロイの手順の中で適用する（ [CI/CD と GitHub Actions](https://memo.taka1156.site/md/ci-cd.md) ）。
- 差分の自動生成は「列の名前変更」を「削除して追加」と解釈することがある。生成されたファイルは必ず読む。

## 止めずに変える: 拡張 → 移行 → 縮小

ローリングデプロイでは、しばらく **古いコードと新しいコードが同時に動く** 。いきなり `RENAME COLUMN` すると、まだ動いている古いコードが古い列名を探してエラーになる。そこで変更を、どの時点でも新旧両方が動く小さな段に分ける（拡張と縮小、expand and contract）。例として `customers.name` を `full_name` に変える。

DB の列

name

full_name

動いているアプリ

**v1** 読む name 書く name

**v2** 読む name 書く 両方

**v3** 読む full_name 書く 両方

**v4** 読む full_name 書く full_name

古い列 新しい列 まだない・消した列

← 前へ

次へ →

最初から

1. 0 / 6 いま アプリ v1 は `name` を読み書きしている。
2. 1 / 6 拡張 新しい列を **NULL を許して** 足す。古いコードは新しい列を知らないので、何も壊れない。

```
ALTER TABLE customers ADD COLUMN full_name text;
```

   戻すなら: 列を消すだけ
3. 2 / 6 両方に書く v2 をデプロイ。v2 は両方の列に書き、読むのは `name` のまま。デプロイ中は v1 と v2 が混ざるが、どちらも `name` を正として読むので食い違わない。 戻すなら: v1 に戻すだけ（ `name` は常に最新）
4. 3 / 6 埋め戻し 既存の行に値を写す。1 回の UPDATE で全行を書くと、長いロックと大量の WAL・レプリカの遅れを生むので、数千行ずつ区切って流す。

```
UPDATE customers SET full_name = name
WHERE id BETWEEN 1 AND 5000 AND full_name IS NULL;  -- 範囲をずらして繰り返す
```

   戻すなら: まだ誰も full_name を読んでいないので、そのまま v1 に戻せる
5. 4 / 6 読み先を切り替え v3 をデプロイ。読むのは `full_name` 、書くのはまだ両方。v2 と v3 が混ざっても、両方の列は同じ値に保たれている。必要ならここで `full_name` に `NOT NULL` を付ける（下の表の手順で）。 戻すなら: v2 に戻せる（両方に書き続けているので）
6. 5 / 6 古い列への書き込みをやめる v4 をデプロイ。 `name` にはもう書かない。古い列を参照するコードがどこにも残っていないこと（バッチ・管理画面・分析の SQL も）を確かめる。 戻すなら: v3 には戻せるが、その間の name は古いまま
7. 6 / 6 縮小 古い列を消す。 **ここだけは戻せない** ので、しばらく置いてから行い、消す前にバックアップを取る。

```
ALTER TABLE customers DROP COLUMN name;
```

   戻すなら: バックアップから復元するしかない

表の分割・型の変更・テーブル名の変更も同じ形でできる。手数は増えるが、各段が小さく戻せるので、デプロイのたびに安全に止められる。

（元のページで操作できます → https://memo.taka1156.site/schema-migration.html#expand-contract）

## 重いロックを取る DDL を避ける

DDL は表にロックをかける。速く終わる DDL でも、 **長いトランザクションがその表を使っていると、ロックを待つ間に後ろの読み書きが全部並んで止まる** 。PostgreSQL では、マイグレーションの前に `SET lock_timeout = '5s';` のように待ち時間の上限を決め、取れなければ失敗させてやり直す。

| やりたいこと | 危ない書き方 | 止めにくい書き方 |
| --- | --- | --- |
| 列を足す | PostgreSQL で `clock_timestamp()` や `random()` のような毎回値が変わる（volatile な）既定値を付ける → 表全体の書き直し | PostgreSQL 11 以降は、既定値なしか定数の既定値なら定義の変更だけで済む。MySQL は 8.0.29 以降（現行の 8.4 LTS も同じ）、 `ALGORITHM=INSTANT` で任意の位置に足せる |
| インデックスを作る | PostgreSQL の普通の `CREATE INDEX` → 作り終わるまで表への書き込みが止まる | `CREATE INDEX CONCURRENTLY` （トランザクションの中では実行できない。失敗すると無効なインデックスが残るので消して作り直す）。MySQL InnoDB は `ALGORITHM=INPLACE, LOCK=NONE` で書き込みを止めずに作れる |
| 既存の列を `NOT NULL` に | PostgreSQL の `SET NOT NULL` をそのまま → 最も強いロックのまま全行を確かめる | PostgreSQL 18 以降は `ADD CONSTRAINT 名前 NOT NULL 列 NOT VALID` → `VALIDATE CONSTRAINT` （書き込みを止めずに確認）で済む。17 以前は `CHECK (列 IS NOT NULL) NOT VALID` を足す → `VALIDATE CONSTRAINT` → `SET NOT NULL` （12 以降は確認を省く）→ CHECK を消す |
| 外部キーを足す | そのまま `ADD FOREIGN KEY` → 全行の確認中、両方の表の書き込みが止まる | `NOT VALID` で足してから、別のトランザクションで `VALIDATE CONSTRAINT` |
| 列の型を変える | `ALTER COLUMN … TYPE` → 多くの場合、表全体の書き直し | 新しい型の列を足して、上の「拡張 → 移行 → 縮小」で移す |

MySQL で大きな表を作り直す変更は、gh-ost や pt-online-schema-change のように、空のコピー表（gh-ost では「ゴーストテーブル」）に行を写してから差し替える道具を使うことが多い。どの DDL が危ないかは DB とバージョンで変わるので、本番と同じ版で、同じくらいの大きさのデータで試してから流す。

## よくある誤解

✗ 誤解: アプリで入力チェックしているので、DB の制約は要らない

✓ 正しくは: アプリの「確かめてから書く」は、同時に来た 2 つのリクエストの両方を通してしまう。別のサービス・バッチ・手作業の SQL も DB に書く。 `UNIQUE` や外部キーは、どこから書かれても守られる最後の砦になる。

✗ 誤解: down マイグレーションを書いておけば、いつでも元に戻せる

✓ 正しくは: 列や表を消す変更を戻しても、構造が戻るだけで消えたデータは戻らない。新しい列に書かれたデータも、戻すと消える。戻せる範囲は「拡張 → 移行 → 縮小」の小さな段で作り、縮小の前にはバックアップを取る。

✗ 誤解: 速く終わる ALTER TABLE なら、本番でいつ流しても安全

✓ 正しくは: DDL そのものは一瞬でも、表のロックを取れるまで待つ間、後ろのクエリが全部並んで止まる。長いトランザクションや重いバッチが走っていない時間を選び、 `lock_timeout` で待ちすぎないようにする。

## 関連メモ

- [DB のしくみ](https://memo.taka1156.site/md/db-internals.md) — ページ・WAL・ACID
- [インデックスとトランザクション](https://memo.taka1156.site/md/db-index-transaction.md) — B 木インデックス・分離レベル・ロック
- [CI/CD と GitHub Actions](https://memo.taka1156.site/md/ci-cd.md) — デプロイ方式とマイグレーションの順番
- [DDD とオニオンアーキテクチャ](https://memo.taka1156.site/md/ddd-onion.md) — Repository で DB の詳細を閉じ込める
