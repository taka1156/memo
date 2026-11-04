<!-- scripts/memo.py build が自動生成。手で編集しない -->

# BigQuery と BI の SQL

> BigQuery を BI でどう使うか、データの流れ・コスト・SQL・GA4 エクスポート・Looker を図解。

- URL: https://memo.taka1156.site/bigquery-bi.html
- タグ: データベース, BI, SQL
- 日付: 2026-11-04

---

# BigQuery × BI × SQL

データを集めて、SQL で整えて、ダッシュボードで見るまで — GA4 と Looker もあわせて

**ざっくり言うと**

- BigQuery は **列指向** のサーバーレス DWH。オンデマンド料金は「読んだ列 × 読んだ範囲」で決まり、 `LIMIT` では基本的に減らない（クラスタ化テーブルでは減ることもある）。
- BI では生データを **raw → staging → mart** と SQL で整え、BI ツールは集計しやすい mart を読む。
- GA4 は「1 行 = 1 イベント」でネストした形のまま入る。Looker は指標の定義（LookML）を 1 か所にまとめて SQL を自動生成する。

## BI のデータの流れ

BI の仕事の大半は「バラバラな元データを、誰が集計しても同じ答えになる形に整える」こと。BigQuery はその置き場と変換エンジンを兼ねる。

#### ① ソース

業務 DB 注文・顧客 (MySQL / PostgreSQL)

GA4 Web / アプリの行動ログ

SaaS・広告 CRM、広告費、スプレッドシート

→

#### ② 取り込み

GA4 エクスポート GA4 から直接連携

Data Transfer / Datastream 定期転送・DB の変更を同期

ELT ツール Fivetran など

→

#### ③ BigQuery（SQL で変換）

**raw** 届いたまま。触らない・消さない

**staging** 型・名前・重複・タイムゾーンを揃える

**mart** 指標ごとに集計しやすい形（ファクト + ディメンション）

変換は dbt / Dataform / スケジュールクエリで SQL として管理

→

#### ④ BI

Looker LookML で指標を一元定義

Data Studio 旧 Looker Studio。手軽なレポート

Tableau・Sheets など コネクテッドシート含む

取り込んでから変換する「ELT」が主流。変換を DWH 内の SQL でやるので、やり直し・履歴管理がしやすい。

## 列指向とスキャン量（触って確かめる）

BigQuery はデータを **列ごと** に保存し、計算資源（スロット）とストレージを分けて持つ。クエリは **使う列だけ** を、 **パーティションで絞った範囲だけ** 読む。下は 1 年分・約 1 TB の `events` テーブル（ `event_date` で日別パーティション）で「直近 7 日の国別ユーザー数」を出す例。

SELECT する列

`SELECT *` 必要な列だけ（date, user_id, country）

期間の絞り込み

WHERE なし（全期間） `event_date` で直近 7 日

クラスタリング

country でクラスタ化 ＋ `WHERE country = 'JP'`

結果の件数

`LIMIT 100` を付ける

読む（課金対象） クラスタでブロック単位に一部スキップ 読まない

```

```

スキャン量 1000 GB

列サイズ・JP の割合（2 割）は説明用の例。クラスタによる削減はブロック単位なので実際は目安。実行前の正確な量はドライラン（コンソールの「このクエリは ○○ を処理します」）で見られる。

（元のページで操作できます → https://memo.taka1156.site/bigquery-bi.html#scan）

## コストの考え方

オンデマンド

容量（Editions）

ガードレール

**読んだバイト数（TiB 単位）で課金。** 毎月 1 TiB までは無料枠がある。

- エラーになったクエリ・キャッシュから返ったクエリは課金されない
- 参照するテーブルごと・クエリごとに最低 10 MB として数える
- 減らす手段は「列を絞る」「パーティション・クラスタで範囲を絞る」「集計済みテーブルを読む」

向いている: 利用量に波がある・まだ小さいチーム。単価は変わるので公式の料金ページで確認する。

**計算資源（スロット）を時間で買う。** Standard / Enterprise / Enterprise Plus のエディションがあり、オートスケールや年単位のコミットを選べる。

- スキャン量ではなく「スロット × 時間」で課金される
- 重いクエリはスロットを使い切って遅くなる（お金ではなく時間で効いてくる）
- ストレージ料金は計算とは別（90 日更新のないテーブル・パーティションは長期保存として安くなる）

向いている: クエリ量が多く定常的・予算を固定したい組織。

- **最大課金バイト数** （maximum bytes billed）: 超えそうなクエリを実行前に失敗させる
- **カスタム割り当て** : プロジェクト単位・ユーザー単位で 1 日のクエリ量に上限
- ** `require_partition_filter` ** : パーティション列で絞らないクエリを拒否するテーブル設定
- **テーブルのプレビュー** : 中身を見るだけなら `SELECT * LIMIT` ではなくプレビュー（無料）

（元のページで操作できます → https://memo.taka1156.site/bigquery-bi.html#cost）

## データモデリング：スター・スキーマとネスト

スター・スキーマ

ネスト（STRUCT / ARRAY）

（図: fct_orders / 1 行 = 1 注文明細 / 金額・数量（足せる数値） / ＋ 各ディメンションのキー / dim_date / 年・月・曜日・祝日 / dim_customer / 会員ランク・地域 / dim_product / カテゴリ・ブランド / dim_store / 店舗・チャネル → https://memo.taka1156.site/bigquery-bi.html#model）

**ファクト** （出来事と足せる数値）の周りに **ディメンション** （切り口）を置く。BI ツールで「月 × カテゴリ別の売上」がドラッグだけで作れる形。 **ファクトの粒度（1 行が何か）** を最初に決めて名前やドキュメントに残すのが一番大事。

BigQuery は JOIN より「大きなテーブル 1 つを読む」方が得意なので、関連データを **行の中に入れ子** で持たせることも多い。GA4 のエクスポートもこの形。

```
-- 1 行 = 1 注文。明細は ARRAY<STRUCT> で中に持つ
order_id   STRING
ordered_at TIMESTAMP
customer   STRUCT<id STRING, rank STRING>
items      ARRAY<STRUCT<sku STRING, qty INT64, price NUMERIC>>

-- 明細単位で集計するときは UNNEST で行に展開する
SELECT i.sku, SUM(i.qty * i.price) AS sales
FROM `proj.mart.orders_nested`, UNNEST(items) AS i
GROUP BY i.sku;
```

BI ツールによってはネストを扱いにくいので、BI 向けの mart はフラットにしておくことが多い。

## SQL はこの順で評価される

FROM / JOIN → WHERE → GROUP BY → HAVING → ウィンドウ関数 OVER → QUALIFY → SELECT → ORDER BY → LIMIT

- **WHERE** は集計前の行を絞る、 **HAVING** は集計後のグループを絞る。
- ウィンドウ関数（ `ROW_NUMBER()` など）の結果は WHERE では使えない。BigQuery では ** `QUALIFY` ** で直接絞れる。
- `LIMIT` は最後。読む量（＝課金）は FROM〜WHERE の段階で決まっているので、LIMIT では基本的に減らない（クラスタ化テーブルだけは途中でスキャンが止まり減ることがある）。

## BI でよく使う SQL（GoogleSQL）

期間集計

移動平均・累計

前年比

最新の 1 行

```
SELECT
  DATE_TRUNC(order_date, MONTH)                      AS month,
  COUNT(DISTINCT customer_id)                        AS buyers,
  SUM(amount)                                       AS revenue,
  SAFE_DIVIDE(SUM(amount), COUNT(DISTINCT order_id)) AS aov  -- 0 除算で NULL
FROM `proj.mart.fct_orders`
WHERE order_date BETWEEN '2026-01-01' AND '2026-10-31'  -- パーティション列で絞る
GROUP BY month
ORDER BY month;
```

`SAFE_DIVIDE` は分母 0 でエラーにせず NULL を返す。比率は「合計 ÷ 合計」で出す（ 下の誤解 ）。

```
WITH daily AS (
  SELECT order_date, SUM(amount) AS revenue
  FROM `proj.mart.fct_orders`
  GROUP BY order_date
)
SELECT
  order_date,
  revenue,
  AVG(revenue) OVER (ORDER BY order_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)             AS ma7,  -- 7 日移動平均
  SUM(revenue) OVER (PARTITION BY DATE_TRUNC(order_date, MONTH)
    ORDER BY order_date)                                   AS mtd   -- 月初からの累計
FROM daily;
```

売上ゼロの日が行ごと欠けていると「7 行前」が 7 日前にならない。日付の連番（ `GENERATE_DATE_ARRAY` ）と LEFT JOIN して欠けを埋めてから計算する。

```
WITH monthly AS (
  SELECT DATE_TRUNC(order_date, MONTH) AS month, SUM(amount) AS revenue
  FROM `proj.mart.fct_orders`
  GROUP BY month
)
SELECT
  cur.month,
  cur.revenue,
  prev.revenue                                           AS revenue_ly,
  SAFE_DIVIDE(cur.revenue, prev.revenue) - 1             AS yoy
FROM monthly AS cur
LEFT JOIN monthly AS prev
  ON prev.month = DATE_SUB(cur.month, INTERVAL 1 YEAR);
```

`LAG(revenue, 12)` でも書けるが、欠けた月があるとずれる。日付で JOIN する方が安全。

```
-- 顧客ごとに最新の 1 行だけ残す（履歴テーブル → 現在の状態）
SELECT customer_id, rank, prefecture, updated_at
FROM `proj.staging.customers_history`
WHERE customer_id IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY customer_id ORDER BY updated_at DESC) = 1;
```

重複排除（取り込みで同じ行が 2 回入った）にも同じ形が使える。サブクエリで包まずに済む。

（元のページで操作できます → https://memo.taka1156.site/bigquery-bi.html#patterns）

## GA4 の BigQuery エクスポート

GA4 の管理画面から BigQuery にリンクすると、 **サンプリングなしの生イベント** が毎日テーブルとして届く。画面のレポートでは出せない切り口（独自のセッション定義・広告費との結合・ユーザー単位の分析）ができるようになる。

### テーブルの並び（日付シャード）

（図: analytics_123456789（データセット） / events_20261101 / events_20261102 / events_20261103 / events_intraday_20261104 / 日次: 前日分の / 確定版 / 当日速報 / ※ 日次版ができると intraday は消える → https://memo.taka1156.site/bigquery-bi.html#ga4）

- **日次** `events_YYYYMMDD` : 前日分。数日は遅れて届いたイベントで更新されることがある
- **ストリーミング** `events_intraday_YYYYMMDD` : 数分遅れの当日分。欠けうる・新規ユーザーの参照元が入らない（追加料金あり）
- 標準プロパティの日次エクスポートは **1 日 100 万イベント** まで（GA4 360 は別枠）

### 1 行 = 1 イベント（パラメータは入れ子）

event_date "20261103" event_timestamp 1793…（UTC μ秒） event_name "page_view" user_pseudo_id

event_params ARRAY

key "ga_session_id" → value.int_value 1793…

key "page_location" → value.string_value "https://…"

key "engagement_time_msec" → value.int_value 5300

device STRUCT geo STRUCT traffic_source STRUCT items ARRAY

- `event_date` はプロパティのタイムゾーンの日付（文字列）、 `event_timestamp` は UTC のマイクロ秒
- 欲しいパラメータはサブクエリで `UNNEST(event_params)` して key で取り出す
- `traffic_source` は **ユーザーの初回** の参照元。セッションの参照元とは別物

ページ別 PV

セッション数

画面と数字が合わない

```
SELECT
  PARSE_DATE('%Y%m%d', event_date) AS day,
  (SELECT value.string_value FROM UNNEST(event_params)
    WHERE key = 'page_location')     AS page,
  COUNT(*)                          AS page_views
FROM `proj.analytics_123456789.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20261001' AND '20261031'  -- 読むテーブルを絞る
  AND event_name = 'page_view'
GROUP BY day, page;
```

`events_*` のワイルドカードは `_TABLE_SUFFIX` で絞らないと全期間を読む（日付シャードなのでパーティションの代わり）。 `events_*` は `events_intraday_*` にもマッチするので、数字の範囲で絞ると日次版だけになり二重計上を避けられる。

```
-- セッション = user_pseudo_id と ga_session_id の組
SELECT
  event_date,
  COUNT(DISTINCT CONCAT(user_pseudo_id, '-',
    CAST((SELECT value.int_value FROM UNNEST(event_params)
          WHERE key = 'ga_session_id') AS STRING))) AS sessions
FROM `proj.analytics_123456789.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20261001' AND '20261031'
GROUP BY event_date;
```

`ga_session_id` はセッション開始時刻由来の値で、ユーザーをまたぐと重なりうる。必ず `user_pseudo_id` と組で数える。

エクスポートは **加工前の生データ** なので、GA4 の画面と完全には一致しないのが普通。

- 画面の一部の指標（ユーザー数など）は推定アルゴリズムやモデリング・しきい値が入っている
- エクスポートの参照元はラストクリックでモデリングなし。画面のアトリビューション設定とは違う
- 日付の区切り（プロパティのタイムゾーン）、遅れて届いたイベント、ストリーミングの欠けでずれる

運用では「BigQuery の数字を正とし、定義をドキュメント化する」と決めておくと揉めにくい。

（元のページで操作できます → https://memo.taka1156.site/bigquery-bi.html#ga4）

## Looker：指標の定義を 1 か所にまとめる

Looker は BigQuery のデータをコピーせず、 **LookML** （指標と JOIN の定義）から **その都度 SQL を生成して BigQuery に投げる** BI。「売上とは何か」を LookML に 1 回書けば、全員のダッシュボードが同じ定義を使う（ **セマンティックレイヤー** ）。

（図: 利用者 / Explore で「月」と / 「売上」を選ぶ / Looker / LookML / dimension / measure / join / 定義を組み合わせて / SQL を生成 / BigQuery / mart のテーブルを / その場で集計 / SQL / 結果 → https://memo.taka1156.site/bigquery-bi.html#looker）

LookML

生成される SQL

便利な機能

Data Studio との違い

```
view: orders {
  sql_table_name: `proj.mart.fct_orders` ;;

  dimension: order_id    { primary_key: yes  sql: ${TABLE}.order_id ;; }
  dimension: customer_id { sql: ${TABLE}.customer_id ;; }

  dimension_group: ordered {          # 日・週・月… をまとめて作る
    type: time
    timeframes: [date, week, month]
    sql: ${TABLE}.ordered_at ;;
  }

  measure: revenue { type: sum             sql: ${TABLE}.amount ;; }
  measure: buyers  { type: count_distinct  sql: ${customer_id} ;; }
}

explore: orders {                    # 利用者が触る入口と JOIN の定義
  join: customers {
    sql_on: ${orders.customer_id} = ${customers.customer_id} ;;
    relationship: many_to_one
  }
}
```

**dimension** = 切り口（GROUP BY される列）、 **measure** = 集計値（SUM・COUNT など）、 **explore** = どのビューをどう JOIN して見せるか。Git で管理し、レビューしてから本番に出せる。

利用者が「Ordered Month」と「Revenue」を選ぶと、おおよそ次のような SQL が作られる（イメージ。実際の形は設定で変わる）。

```
SELECT
  FORMAT_TIMESTAMP('%Y-%m', orders.ordered_at) AS orders_ordered_month,
  COALESCE(SUM(orders.amount), 0)            AS orders_revenue
FROM `proj.mart.fct_orders` AS orders
GROUP BY 1
ORDER BY 1 DESC
LIMIT 500
```

SQL は毎回 BigQuery で実行されるので、 スキャン量 の話がそのまま効く。Looker の下に置くテーブルこそパーティション・クラスタ・集計済み mart を整える。

- **対称集計 (symmetric aggregates)** : `primary_key` と `relationship` を正しく書くと、JOIN で行が増えても SUM・COUNT が二重計上されないよう SQL を工夫してくれる（ ファンアウト 対策）
- **PDT（永続派生テーブル）** : 重い集計を BigQuery 上のテーブルとして作っておき、datagroup のタイミングで作り直す
- **集計認識 (aggregate awareness)** : 粗い粒度で足りる質問は自動で小さい集計テーブルを読み、スキャン量を減らす
- **キャッシュと datagroup** : 「データが更新されるまでは同じ結果を使う」を定義できる
- **行レベルの権限** : `access_filter` などで「自分の地域の数字だけ見える」を実現

|  | Looker | Data Studio（旧 Looker Studio） |
| --- | --- | --- |
| 位置づけ | 全社の指標を統制するエンタープライズ BI | 個人・チームの手軽なレポートとダッシュボード |
| 指標の定義 | LookML に一元化（Git・レビュー） | データソースやグラフごとの計算フィールド |
| 始めやすさ | モデリングの設計と開発者が必要 | ブラウザですぐ作れる。無料版あり |
| 向く場面 | 部署ごとに「売上」の定義がずれて困っている | GA4・広告・BigQuery の数字をさっと共有したい |

Looker Studio は 2026 年に Data Studio の名前に戻った（中身・既存レポートはそのまま）。Looker とは別製品という整理がはっきりした。

## BI ツールへの出し方

| 出し方 | 中身 | 向いている場面 |
| --- | --- | --- |
| ビュー | SQL を保存するだけ。読むたびに元テーブルを集計 | 小さいデータ・常に最新が欲しい |
| 集計テーブル | dbt / Dataform / スケジュールクエリで定期的に作る mart | 毎日多くの人が開くダッシュボード |
| マテリアライズドビュー | BigQuery が差分を自動で反映する集計結果（使える SQL に制限あり） | 単純な集計を新鮮かつ安く |
| Looker の PDT | Looker が BigQuery 上に作って管理する派生テーブル | Looker 中心の運用 |
| BI Engine | BigQuery の前段にあるメモリ上の高速化レイヤー | ダッシュボードの応答を速くしたい |
| クエリキャッシュ | 同じクエリ・元データ不変なら結果を再利用（約 24 時間・課金なし） | 自動。 `CURRENT_TIMESTAMP()` などを含むと効かない |

## よくある誤解・落とし穴

LIMIT 10 を付ければ安くなる

課金は読んだ列と範囲で決まり、LIMIT では基本的に減らない（クラスタ化テーブルだけは途中でスキャンが止まって減ることがある）。列を絞り、パーティション・クラスタ列で WHERE する。中身を見るだけならプレビュー。

日別 CVR の平均が月の CVR

比率の平均は、日ごとの母数の違いを無視する。月の CVR は `SUM(cv) / SUM(sessions)` 。BI ツールでも比率は「合計 ÷ 合計」の計算フィールドにする。

日別ユニークユーザー数を足せば月間ユーザー数

複数日に来た人を重複して数えてしまう。 `COUNT(DISTINCT)` は足し算できないので、元データから月単位で数え直す（集計テーブルを作るなら月別も別に持つ）。

注文と明細を JOIN してから送料を SUM すればよい

明細の行数ぶん注文が複製され、送料が何倍にもなる（ファンアウト）。集計してから JOIN するか、粒度をそろえる。Looker なら対称集計が守ってくれる。

`DATE(created_at)` で日本の日付になる

TIMESTAMP は UTC 基準なので、日本時間 0〜9 時のデータが前日扱いになる。 `DATE(created_at, 'Asia/Tokyo')` のようにタイムゾーンを明示する。
