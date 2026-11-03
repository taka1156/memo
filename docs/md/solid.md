<!-- scripts/memo.py build が自動生成。手で編集しない -->

# SOLID と依存性逆転

> SOLID の 5 原則を「どんな症状を防ぐか」で整理し、オニオン／クリーンで内側に依存させる理由＝依存性逆転 (DIP) を図で説明する

- URL: https://memo.taka1156.site/solid.html
- タグ: 設計
- 日付: 2026-11-03

---

5 原則を「防ぎたい症状」で覚える。DIP はオニオンが内側を向く理由そのもの

**ざっくり言うと**

- SOLID は「変更したら別の場所が壊れる」「直すたびに同じファイルを触る」を防ぐための 5 つの経験則。
- 一番効くのは **D（依存性逆転）** 。ビジネスルールが DB や API の都合に引きずられないよう、 **インターフェースを内側（ドメイン側）が持ち、外側がそれを実装する** 。
- オニオン／クリーン／ヘキサゴナルの「依存は内側へ」は、この DIP を層全体に適用したもの。

## 5 つの原則と防ぐ症状

名前を暗記するより「どんな痛みを防ぐか」で覚えるほうが使えます。コードは TypeScript。

S 単一責任

O 開放閉鎖

L リスコフ置換

I インターフェース分離

D 依存性逆転

S **単一責任の原則** Single Responsibility Principle

「1 つのクラスは 1 つのことだけ」ではなく、正確には **「変更する理由（＝依頼してくる人・部署）が 1 つだけ」** になるように分ける。

**防ぐ症状:** 経理の依頼で給与計算を直したら、人事向けの勤怠レポートが壊れた。

NG

```
class Employee {
  calcPay() {}      // 経理の都合
  reportHours() {}  // 人事の都合
  save() {}         // DBA の都合
}
```

OK

```
class PayCalculator { calc(e: Employee) {} }
class HourReporter  { report(e: Employee) {} }
class EmployeeRepo  { save(e: Employee) {} }
```

関数を細かく割ること自体が目的ではない。「誰の都合で変わるか」が同じものはまとめたままでよい。

O **開放閉鎖の原則** Open/Closed Principle

機能追加に対しては **開いて** いて（足せる）、既存コードの修正に対しては **閉じて** いる（触らなくて済む）。

**防ぐ症状:** 支払い方法を 1 つ足すたびに、同じ `switch` 文をあちこち直す。

NG

```
function pay(kind: string, amt: number) {
  switch (kind) {
    case 'card':   /* … */ break;
    case 'paypay': /* … */ break;
    // 追加のたびにここを修正
  }
}
```

OK

```
interface PaymentMethod { pay(amt: number): void }
class Card   implements PaymentMethod { … }
class PayPay implements PaymentMethod { … }
// 追加は新しいクラスを足すだけ
function pay(m: PaymentMethod, amt: number) {
  m.pay(amt);
}
```

増える見込みがない分岐まで抽象化する必要はない。「2 回目の追加が来たら」切り出すくらいでちょうどいい。

L **リスコフの置換原則** Liskov Substitution Principle

親の型（インターフェース）を使っているコードに、どの子・どの実装を渡しても **期待どおりに動く** こと。「型が合う」だけでなく「約束（振る舞い）が守られる」ことが条件。

**防ぐ症状:** 呼び出し側に `if (x instanceof 特定の実装)` の分岐が増えていく。

NG

```
interface Storage { save(k: string, v: string): void }
class ReadOnlyStorage implements Storage {
  save() { throw new Error('read only'); }
}
// Storage を受け取る側は落ちる
```

OK

```
interface Reader { get(k: string): string }
interface Writer { save(k: string, v: string): void }
class ReadOnlyStorage implements Reader { … }
// できないことは型で表す
```

DIP で実装を差し替える設計は、LSP が守られていて初めて安全になる（テスト用のフェイクも同じ約束を守る）。

I **インターフェース分離の原則** Interface Segregation Principle

使う側が **使わないメソッドに依存させない** 。大きなインターフェースは、使う側ごとに小さく分ける。

**防ぐ症状:** 一覧表示しかしないのに、テスト用のフェイクで `delete` や `bulkImport` まで実装させられる。

NG

```
interface UserRepo {
  find(id: string): User;
  list(): User[];
  save(u: User): void;
  delete(id: string): void;
  bulkImport(csv: string): void;
}
```

OK

```
// 使う側（ユースケース）ごとに定義
interface UserFinder { find(id: string): User }
interface UserLister { list(): User[] }
// 実装は 1 クラスで両方満たしてよい
class PgUserRepo implements UserFinder, UserLister { … }
```

TypeScript は構造的型付けなので、 `Pick<UserRepo, 'find'>` のように必要な部分だけを受け取る書き方でも同じ効果になる。

D **依存性逆転の原則** Dependency Inversion Principle

上位（ビジネスルール）は下位（DB・外部 API などの詳細）に依存しない。 **両方が抽象（インターフェース）に依存し、その抽象は上位側が持つ** 。

**防ぐ症状:** DB を変えたら、注文の計算ロジックまで書き直しになる／テストのたびに本物の DB が要る。

詳しくは次のセクションで図にしています → 依存性逆転を図で見る

（元のページで操作できます → https://memo.taka1156.site/solid.html#principles）

## 依存性逆転を図で見る

矢印は「知っている（import している）」方向。 **処理が流れる向き** と **依存の向き** を分けて考えるのがポイントです。

### 逆転前 ：上が下を直接知っている

（図: OrderService / ビジネスルール（上位） / import / MySqlOrderRepo / DB の詳細（下位） → https://memo.taka1156.site/solid.html#dip）

処理の流れも依存も上→下で同じ向き。DB を変えると上位まで修正が波及する。

### 逆転後 ：下が上の約束に合わせる

（図: ドメイン側が所有 / OrderService / ビジネスルール / «interface» / OrderRepository / implements / MySqlOrderRepo / インフラ層 → https://memo.taka1156.site/solid.html#dip）

処理は上→下に流れるが、依存の矢印は下→上に **逆転** 。DB を変えても枠の中は無傷。

```
// domain/order-repository.ts  ← ドメイン側に置く
export interface OrderRepository {
  findById(id: OrderId): Promise<Order | null>;
  save(order: Order): Promise<void>;
}

// application/place-order.ts
export class PlaceOrder {
  constructor(private repo: OrderRepository) {}   // 抽象だけを知る
}

// infra/mysql-order-repository.ts  ← 外側がドメインを import
import type { OrderRepository } from '../domain/order-repository';
export class MySqlOrderRepository implements OrderRepository { … }

// main.ts（組み立て役＝コンポジションルート）だけが両方を知る
const placeOrder = new PlaceOrder(new MySqlOrderRepository(pool));
```

### 「インターフェースを誰が持つか」が本体

インターフェースを作っても、それが `infra/` に置かれていたら依存はまだ下向きです。DIP の肝は **使う側（上位）の言葉で約束を書き、使う側のフォルダに置く** こと。メソッド名も `executeQuery` ではなく `findById` のようにドメインの言葉になります。

## オニオンが「内側に依存」する理由

DIP を 1 か所ではなく層の境界すべてに適用すると、依存の矢印がすべて中心を向きます。これがオニオン／クリーン／ヘキサゴナルの共通ルールです。

インフラ（DB・HTTP） → アプリケーション（ユースケース） → ドメイン（エンティティ・リポジトリの interface）

**変わりにくいものを中心に**

業務ルールは DB やフレームワークより長生き。変わりやすい側が変わりにくい側に合わせるほうが、修正の波及が小さい。

**テストが速くなる**

中心はインターフェースしか知らないので、インメモリのフェイクを渡すだけでユースケースをテストできる。

**決定を遅らせられる**

DB や外部サービスの選定前でも、約束（interface）さえあれば中心のロジックを書き始められる。

層ごとの構成は [DDD とオニオンアーキテクチャ](https://memo.taka1156.site/md/ddd-onion.md) 、ほかの方式との違いは [アーキテクチャ比較](https://memo.taka1156.site/md/architecture-compare.md) へ。

## DIP・DI・IoC の違い

名前が似ていて混同しやすい 3 つ。DIP が「設計の原則」、DI はそれを実現する「手段」です。

| 名前 | 種類 | 中身 |
| --- | --- | --- |
| DIP Dependency Inversion | 原則 | 依存の向きを「詳細 → 抽象」にする。抽象は上位が所有する。 |
| DI Dependency Injection | 手段 | 使う物を自分で `new` せず、コンストラクタ引数などで外から渡してもらう。 |
| IoC Inversion of Control | 考え方 | 処理の主導権をフレームワーク側に渡す（呼ぶのではなく呼ばれる）。DI コンテナはその一例。 |

DI していても、渡している型が具体クラス（ `MySqlOrderRepository` ）なら DIP はできていない。逆に DI コンテナがなくても、 `main.ts` で手で組み立てれば DIP は成立する。

## どこまでやるか

**抽象化する価値が高い**

- DB・外部 API・メール送信・決済など I/O の境界
- 現在時刻・乱数（テストで固定したいもの）
- 複数の実装が実際にある／近く増える箇所

**やりすぎになりやすい**

- 実装が 1 つしかなく、テストでも差し替えない純粋なロジック
- 全クラスに `IFoo` と `FooImpl` を機械的に作る
- 小さなスクリプトや使い捨てのツール

## よくある誤解

インターフェースを作れば DIP になる

インターフェースが下位（infra）側に置かれ、下位の言葉で書かれていれば依存は下向きのまま。上位が所有して初めて「逆転」になる。

DI コンテナを入れれば SOLID になる

DI コンテナは組み立てを自動化する道具にすぎない。具体クラスを注入していれば DIP にはならないし、手で組み立てても DIP は成立する。

単一責任 ＝ メソッドが 1 つのクラス

基準は「変更の理由が 1 つか」。同じ人・同じ理由で一緒に変わるものは、まとめておいたほうが変更が楽。

SOLID はオブジェクト指向（クラス）専用

関数型でも「関数を引数で受け取る」「型で必要な形だけを要求する」ことで同じ効果が得られる。考え方は言語やパラダイムを選ばない。
