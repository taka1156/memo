<!-- scripts/memo.py build が自動生成。手で編集しない -->

# インデックスとトランザクション

> B木インデックスが効く条件・効かない条件（複合インデックスの順序、関数、LIKE）と、分離レベルで防げる異常、MVCC、更新の取りこぼし対策までを図解。

- URL: https://memo.taka1156.site/db-index-transaction.html
- タグ: データベース
- 日付: 2026-11-03

---

「速く探す」と「同時に動いても壊れない」の2本柱

**ざっくり言うと**

- インデックスは **値の順に並べた索引（B木）** 。並び順を使える条件（等号・範囲・前方一致・その順での並べ替え）でだけ効く。
- 複合インデックスは **左の列から順に** 使える。列に関数をかけたり、先頭列を飛ばしたりすると使えない。
- 分離レベルは「同時実行でどの異常まで許すか」の設定。 **READ COMMITTED でも更新の取りこぼしは起きる** ので、原子的な UPDATE や行ロックで防ぐ。

前提として、ページ・バッファプール・WAL の話は [DB のしくみ](https://memo.taka1156.site/md/db-internals.md) にある。

## B木インデックス

（図: 30 | 60 / ルート / 10 | 20 / 40 | 50 / 70 | 80 / 3 7 / 22 28 / 33 38 / 42 47 / 55 58 / 71 75 / 葉は値の順に横につながっている → 範囲検索や ORDER BY はたどるだけ）

42 を探すとき、ルートで「30 以上 60 未満」の枝、次に「40 以上 50 未満」の枝…と **数回ページを読むだけ** で葉に着く。100 万行でも 3〜4 段程度。葉には「値 → 行の場所」が入っている。

## そのインデックス、使える？

次の複合インデックスがあるとき、各クエリで使えるかを選んでみる。

CREATE INDEX ON orders (user_id, created_at);

### ほかの「効かない」パターン

| 条件 | 使える？ | 理由・対策 |
| --- | --- | --- |
| `name LIKE 'yam%'` | ○ | 前方一致は「yam 以上 yan 未満」の範囲検索になる（PostgreSQL では照合順序によって `text_pattern_ops` が必要） |
| `name LIKE '%da'` | ✕ | 先頭が決まらないので並び順を使えない。全文検索やトライグラム索引を検討 |
| `lower(email) = …` | ✕ | 列に関数をかけると元の並び順と別物。 `lower(email)` の式インデックスを作る |
| `status = 'active'` （9割が active） | △ | ほとんどの行が当たるなら全件読む方が安い。プランナはインデックスを使わないことを選ぶ |
| `code = 5` （列は文字列） | △ | 文字列の列を数値と比べると、列側が数値に変換されてインデックスを使えない（MySQL など）。 `code = '5'` のように型を合わせる |

### インデックスのコスト

書き込みが遅くなる

INSERT・UPDATE・DELETE のたびに全インデックスを更新する。10 本あれば 10 か所書く。使っていないインデックスは消す。

カバリングインデックス

SELECT する列が全部インデックスに入っていれば、テーブル本体を読まずに済む（Index Only Scan）。 `INCLUDE (列)` で葉に列を足せる DB もある。

```
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 5 ORDER BY created_at DESC LIMIT 20;
-- Limit
--   -> Index Scan Backward using orders_user_id_created_at_idx on orders
--        Index Cond: (user_id = 5)        ← Sort が出ていない＝並べ替え不要
```

## 同時に動くと何が起きる？

2つのトランザクション T1・T2 が同時に動いたときの代表的な異常。

ダーティリード

反復不能読み取り

ファントム

更新の取りこぼし

T1

T2

`UPDATE 残高 = 0`

`SELECT 残高` → 0

`ROLLBACK`

T2 は **結局取り消された値** を読んでしまった。READ COMMITTED 以上なら起きない（PostgreSQL ではどのレベルでも起きない）。

T1

T2

`SELECT 価格` → 100

`UPDATE 価格 = 120; COMMIT`

`SELECT 価格` → 120

同じトランザクション内で **同じ行を2回読んだら値が違う** 。REPEATABLE READ 以上で防げる。

T1

T2

`SELECT count(*) WHERE 部署=営業` → 5

`INSERT 営業の新人; COMMIT`

`SELECT count(*) WHERE 部署=営業` → 6

同じ条件で検索したら **行が増えた（減った）** 。標準 SQL では SERIALIZABLE で防ぐが、PostgreSQL の REPEATABLE READ はスナップショットなのでここでも起きない。

T1

T2

`SELECT 在庫` → 10

`SELECT 在庫` → 10

`UPDATE 在庫 = 9; COMMIT`

`UPDATE 在庫 = 9; COMMIT`

2個売れたのに在庫は 9。 **読んだ値をアプリで計算して書き戻す** と、READ COMMITTED では普通に起きる。対策は 下 。

## 分離レベルと防げる異常

| 分離レベル | ダーティリード | 反復不能読み取り | ファントム |
| --- | --- | --- | --- |
| READ UNCOMMITTED | 起きる | 起きる | 起きる |
| READ COMMITTED | 防ぐ | 起きる | 起きる |
| REPEATABLE READ | 防ぐ | 防ぐ | 起きる※ |
| SERIALIZABLE | 防ぐ | 防ぐ | 防ぐ |

これは SQL 標準の最低ラインで、実際の挙動は DB ごとに違う。※PostgreSQL と MySQL InnoDB の REPEATABLE READ は、通常の SELECT ではファントムも起きない。 **既定** は PostgreSQL・Oracle・SQL Server が READ COMMITTED、MySQL InnoDB が REPEATABLE READ。PostgreSQL の SERIALIZABLE は直列化できない組み合わせを **エラーにし** 、MySQL InnoDB の SERIALIZABLE は読み取りにも共有ロックをかけるのでロック待ちやデッドロックが増える。どちらもアプリ側でトランザクションのリトライが必要。

## MVCC：読む人と書く人がぶつからない仕組み

多くの DB は、更新しても **古い版を残しておく** （PostgreSQL は新しい行の版を追加し、InnoDB は行を上書きして古い版を undo ログに残す）。各トランザクションは開始時点（または文の開始時点）のスナップショットに見える版だけを読む。

版1

在庫 = 10

T100 が作成、T105 が更新して終了

版2（最新）

在庫 = 9

T105 が作成

誰に何が見える？

T105 より前に始まった T103 → **版1**

後から始まった T110 → **版2**

おかげで SELECT は UPDATE の完了を待たない。代わりに古い版が溜まるので、PostgreSQL は VACUUM、InnoDB は undo ログの purge で片付ける。長時間開いたままのトランザクションがあると古い版を消せず、テーブルが膨らむ。

## 更新の取りこぼしを防ぐ3つの方法

原子的な UPDATE

行ロック

楽観ロック

```
UPDATE items SET stock = stock - 1 WHERE id = 7 AND stock > 0;
-- 更新件数が 0 なら在庫切れ
```

計算を DB に任せる。 **一番シンプルで速い** 。単純な増減ならまずこれ。

```
BEGIN;
SELECT stock FROM items WHERE id = 7 FOR UPDATE;   -- 他の人はここで待つ
-- アプリで複雑な判定
UPDATE items SET stock = 9 WHERE id = 7;
COMMIT;
```

読んだ時点で行をロックする（悲観ロック）。判定が複雑なとき向け。ロックの順番がトランザクションごとに違うとデッドロックになるので、 **常に同じ順で取る** 。

```
UPDATE items SET stock = 9, version = version + 1
 WHERE id = 7 AND version = 3;
-- 0 件なら誰かが先に更新した → 読み直してやり直す
```

ロックせず、書くときに「読んだときから変わっていないか」を確かめる。競合が少なく、画面を開いてから保存するまでが長い編集フォームなどに向く。

## よくある誤解

✕ WHERE に出てくる列全部にインデックスを張れば速くなる

○ 書き込みが遅くなり、プランナが使うのは通常1クエリにつき一部だけ。よく使う検索条件の組み合わせに合わせた複合インデックスを少数作る方が効く。

✕ トランザクションで囲めば同時実行の問題は全部防げる

○ 防げる範囲は分離レベル次第。既定の READ COMMITTED では、読んでから書き戻す処理の取りこぼしは防げない。

## 関連

[DB のしくみ](https://memo.taka1156.site/md/db-internals.md) [JWT とセッション](https://memo.taka1156.site/md/jwt-vs-session.md)

## 参考

- [PostgreSQL: Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL: Multicolumn Indexes](https://www.postgresql.org/docs/current/indexes-multicolumn.html)
- [MySQL: Transaction Isolation Levels](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html)
- [Use The Index, Luke!（日本語版）](https://use-the-index-luke.com/ja)
