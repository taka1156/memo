<!-- scripts/memo.py build が自動生成。手で編集しない -->

# DDD とオニオンアーキテクチャ

> DDD の要素（ユビキタス言語・境界づけられたコンテキスト・エンティティ・値オブジェクトなど）とオニオンアーキテクチャの依存の向きを、タスク管理 API の例で図解。

- URL: https://memo.taka1156.site/ddd-onion.html
- タグ: 設計, バックエンド
- 日付: 2026-11-03

---

# DDD × Onion Architecture

ドメイン駆動設計とオニオンアーキテクチャの考え方を、タスク管理 API の例で

**ざっくり言うと**

- **DDD** は「業務のルール（ドメイン）をコードの中心に置く」設計の考え方。用語を揃え、ルールをエンティティや値オブジェクトに閉じ込める。
- **オニオンアーキテクチャ** は DDD と相性のよい層の切り方（DDD 専用ではない）。依存は **必ず外 → 内** の一方向で、中心のドメインは DB も Hono も知らない。
- DB などの外側に向かう依存は、ドメインに置いた **インターフェース** で逆転させる（依存性逆転）。Hono などの Web フレームワークは一番外側の「入口」にすぎない。

## DDD（ドメイン駆動設計 / Domain-Driven Design）とは

DDD は大きく 2 つの面があります。「何をどう分けるか」を決める **戦略的設計** と、「コードでどう表すか」を決める **戦術的設計** です。アーキテクチャの話と結びつくのは主に後者です。

戦術的設計（コード）

戦略的設計（分け方）

クリックで説明と、タスク管理 API の例での対応を表示します。

値オブジェクト domain Value Object

値そのものに意味がある不変のオブジェクト。生成時にルールを検証するので、作れた時点で「正しい値」であることが保証される。同じ値なら同じものとして扱う。

例: `TaskTitle` （1〜100 文字）、 `TaskId`

エンティティ domain Entity

ID で識別され、状態が変わっても同一とみなされるもの。状態を変える操作はメソッドとして持ち、その中で業務ルールを守る。

例: `Task` （ `complete()` は完了済みなら例外）

集約 domain Aggregate

一緒に整合性を守るべきエンティティ・値オブジェクトのまとまり。外からは代表の **集約ルート** 経由でしか触らせない。保存・取得の単位にもなる。

例: `Task` 集約（ルートは Task 自身）

リポジトリ domain infra Repository

集約を保存・復元する窓口。 **インターフェースはドメイン層** に、 **実装はインフラ層** に置く。これがオニオンでの依存性逆転の要。

例: `TaskRepository` （IF）／ `D1TaskRepository` （実装）

ドメインサービス domain Domain Service

どのエンティティにも自然に属さないドメインのルール。例:「同じタイトルのタスクは作れない」のように複数の集約をまたぐ判定。乱用するとエンティティが空っぽになるので最後の手段。

アプリケーションサービス application Application Service / UseCase

ユースケース 1 つ＝1 クラス（または関数）。リポジトリから集約を取り出し、ドメインのメソッドを呼び、保存する「段取り役」。 **業務ルールそのものは書かない** 。

例: `CreateTaskUseCase` , `CompleteTaskUseCase`

ドメインイベント domain Domain Event

「タスクが完了した」のようなドメインで起きた出来事。通知や集計などの後続処理を、本体の集約から切り離すのに使う。

ファクトリ domain Factory

複雑な生成手順をまとめる役。小さなうちは `Task.create()` のような静的メソッドで十分。

（元のページで操作できます → https://memo.taka1156.site/ddd-onion.html#ddd）

### ユビキタス言語 (Ubiquitous Language)

業務の人と開発者が同じ言葉を使い、その言葉をそのままクラス名・メソッド名にする。「タスクを完了する」と話すなら `task.complete()` 。 `updateStatus(2)` のような名前は避ける。

### 境界づけられたコンテキスト (Bounded Context)

同じ単語でも部署によって意味が違う。無理に 1 つのモデルにまとめず、意味が通じる範囲（コンテキスト）ごとにモデルを分ける。

#### 販売コンテキスト

「商品」= 価格・説明文・在庫数を持つもの

`Product { price, description }`

#### 配送コンテキスト

「商品」= 重さ・サイズを持つ荷物

`Parcel { weight, size }`

### コンテキストマップ (Context Map)

コンテキスト同士がどう連携するか（どちらが上流か、変換層を挟むか等）を描いた地図。マイクロサービスやモジュールの分割を考えるときの土台になる。

Hono のプロジェクトでは、コンテキストが増えたら `src/` 直下を `src/sales/` , `src/shipping/` のように分け、それぞれの中にオニオンの層を持たせる構成がよく使われます。

## オニオンアーキテクチャ (Onion Architecture)

Jeffrey Palermo が 2008 年に提唱した層構造。玉ねぎのように同心円で層を重ね、 **依存は外側から内側へだけ** 向かいます。

（図: Domain / Model / Domain Services / Application / Repository IF はここ / Presentation / Hono routes / Infrastructure / D1 / 外部 API / Tests / 依存 → https://memo.taka1156.site/ddd-onion.html#onion）

- Domain Model
  エンティティ・値オブジェクト。 **何にも依存しない** 純粋な TypeScript。
- Domain Services
  集約をまたぐルール、リポジトリの **インターフェース** 。
- Application
  ユースケース。ドメインを組み合わせて 1 つの操作を実現する。
- Presentation / Infra / Tests
  Hono、D1、外部 API、テスト。 **差し替え可能な外側** 。

### 肝は「依存性逆転 (Dependency Inversion)」

原則そのものの説明は [SOLID と依存性逆転](https://memo.taka1156.site/md/solid.md) にあります。ここではオニオンでの使い方だけを見ます。

ユースケースは DB に保存したい。でも Application が Infrastructure を import したら矢印が外向きになってしまう。そこで:

（図: CompleteTaskUseCase / application / «interface» / TaskRepository / domain / D1TaskRepository / infrastructure / 使う（import） / implements / どちらの矢印も内側（domain）を向く → D1 を Postgres やメモリに替えても内側は無傷 → https://memo.taka1156.site/ddd-onion.html#onion）

### import してよい方向

| import する側 ＼ される側 | domain | application | infrastructure | presentation | Web フレームワーク / DB の型 |
| --- | --- | --- | --- | --- | --- |
| domain | ○ | ✕ | ✕ | ✕ | ✕ |
| application | ○ | ○ | ✕ | ✕ | ✕ |
| infrastructure | ○ | ○ | ○ | ✕ | ○ |
| presentation | ○ | ○ | ✕ ※ | ○ | ○ |

※ presentation と infrastructure を結びつけるのは Composition Root（例: `container.ts` のような、依存を組み立てる起点のファイル）だけ。ルールは dependency-cruiser や eslint-plugin-boundaries などで機械的にチェックできます。

### 似ているアーキテクチャとの違い

オニオン・ヘキサゴナル・クリーンは「ドメインを中心にして、依存は内向き」という本質は同じで、図の描き方と用語が違う程度です。レイヤードを含めた比較は [アーキテクチャ比較](https://memo.taka1156.site/md/architecture-compare.md) にまとめています。

## 1 リクエストの流れ

`POST /tasks/:id/complete` が来たとき、各層がやることは次のとおりです。

**Route** Hono などのルート。パスから id を取り出し、ユースケースを呼ぶ

→

**UseCase** リポジトリ IF で Task を取得

→

**Task.complete()** 「完了済みなら NG」を判定し状態を変える

→

**Repository 実装** D1 などの DB に、SQL や ORM（Drizzle など）で保存

→

**Response** DTO を JSON で返す／例外は 400・404 に変換

## よくある誤解

フォルダを domain / application / infrastructure に分ければ DDD になる

フォルダは入れ物。 `Task` がゲッター・セッターだけで、ルールが全部ユースケースに書かれていたら、それは「ドメインモデル貧血症」。ルールをエンティティや値オブジェクトに入れて初めて意味がある。

Zod でバリデーションしているから値オブジェクトは要らない

Zod は「HTTP の入力の形」を守る係、値オブジェクトは「業務ルール」を守る係。CLI やバッチなど別の入口から来ても、 `TaskTitle` を通れば必ず 1〜100 文字になる。

リポジトリはテーブルごとに 1 つ作る

リポジトリは **集約ごと** 。注文と注文明細が 1 つの集約なら、 `OrderRepository` 1 つで両方のテーブルを扱う。

Hono の Context ( `c` ) をユースケースに渡せば楽

それをすると application が Hono に依存し、テストにも Context が必要になる。ハンドラで必要な値だけ取り出してプレーンな引数で渡す。

どんなプロジェクトでもこの構成にすべき

CRUD 中心でルールが少ないなら、ファイル数が増えるコストのほうが大きい。業務ルールが多い・長く育てる・チームで触る、といった条件がそろうほど効いてくる。まずは「業務ルールはエンティティに、DB アクセスはリポジトリに」だけを分けて始め、ルールが増えた部分から層を分けていけばよい。
