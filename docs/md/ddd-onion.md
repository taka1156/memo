<!-- scripts/memo.py build が自動生成。手で編集しない -->

# DDD とオニオンアーキテクチャ

> DDD の要素と依存の向きを図解し、Hono・Void での構成例と AI 時代向けの軽量版を比較。

- URL: https://memo.taka1156.site/ddd-onion.html
- タグ: 設計
- 日付: 2026-11-03

---

# DDD × Onion Architecture

ドメイン駆動設計とオニオンアーキテクチャを、Hono と Void のタスク管理 API で具体的に

**ざっくり言うと**

- **DDD** は「業務のルール（ドメイン）をコードの中心に置く」設計の考え方。用語を揃え、ルールをエンティティや値オブジェクトに閉じ込める。
- **オニオンアーキテクチャ** は DDD を実装するための層の切り方。依存は **必ず外 → 内** の一方向で、中心のドメインは DB も Hono も知らない。
- DB などの外側に向かう依存は、ドメインに置いた **インターフェース** で逆転させる（依存性逆転）。Hono は一番外側の「入口」にすぎない。

## DDD（ドメイン駆動設計 / Domain-Driven Design）とは

DDD は大きく 2 つの面があります。「何をどう分けるか」を決める **戦略的設計** と、「コードでどう表すか」を決める **戦術的設計** です。アーキテクチャの話と結びつくのは主に後者です。

戦術的設計（コード）

戦略的設計（分け方）

クリックで説明と、このページのサンプルでの対応を表示します。

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

「タスクが完了した」のようなドメインで起きた出来事。通知や集計などの後続処理を、本体の集約から切り離すのに使う。本ページのサンプルでは省略。

ファクトリ domain Factory

複雑な生成手順をまとめる役。小さなうちは `Task.create()` のような静的メソッドで十分。

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

（図: Domain / Model / Domain Services / Application / Repository IF はここ / Presentation / Hono routes / Infrastructure / D1 / 外部 API / Tests / 依存）

- Domain Model
  エンティティ・値オブジェクト。 **何にも依存しない** 純粋な TypeScript。
- Domain Services
  集約をまたぐルール、リポジトリの **インターフェース** 。
- Application
  ユースケース。ドメインを組み合わせて 1 つの操作を実現する。
- Presentation / Infra / Tests
  Hono、D1、外部 API、テスト。 **差し替え可能な外側** 。

### 肝は「依存性逆転 (Dependency Inversion)」

ユースケースは DB に保存したい。でも Application が Infrastructure を import したら矢印が外向きになってしまう。そこで:

（図: CompleteTaskUseCase / application / «interface» / TaskRepository / domain / D1TaskRepository / infrastructure / 使う（import） / implements / どちらの矢印も内側（domain）を向く → D1 を Postgres やメモリに替えても内側は無傷）

### import してよい方向（Hono プロジェクトでのルール）

| import する側 ＼ される側 | domain | application | infrastructure | presentation | hono / D1 型 |
| --- | --- | --- | --- | --- | --- |
| domain | ○ | ✕ | ✕ | ✕ | ✕ |
| application | ○ | ○ | ✕ | ✕ | ✕ |
| infrastructure | ○ | ○ | ○ | ✕ | ○ |
| presentation | ○ | ○ | ✕ ※ | ○ | ○ |

※ presentation と infrastructure を結びつけるのは Composition Root（ `container.ts` ）だけ。ルールは dependency-cruiser や eslint-plugin-boundaries などで機械的にチェックできます。

### 似ているアーキテクチャとの違い

|  | レイヤード | オニオン | ヘキサゴナル / クリーン |
| --- | --- | --- | --- |
| 依存の向き | 上 → 下（UI → ロジック → DB ） | 外 → 内（中心は ドメイン ） | 外 → 内（同じ思想） |
| DB の位置 | 一番下＝ロジックが DB に依存 | 一番外＝差し替え可能 | アダプタ＝差し替え可能 |
| 特徴 | シンプルだが DB 都合がロジックに漏れやすい | ドメインの層を細かく描く（Model / Services） | Port & Adapter、Entities / UseCases など呼び名が違う |

オニオン・ヘキサゴナル・クリーンは「ドメインを中心にして、依存は内向き」という本質は同じ。図の描き方と用語が違う程度に考えてよいです。

## ディレクトリ構成とサンプルコード

題材は Cloudflare Workers + D1 で動く **タスク管理 API** 。ルールは「タイトルは 1〜100 文字」「完了済みのタスクはもう一度完了できない」「完了済みのタスクは名前を変えられない」の 3 つです。同じアプリを **Hono** と **Void** の 2 通りで作っています。上のボタンで切り替えてください。

Hono ルーティングを自分で組む

Void VoidZero のフルスタック FW

### Hono 版のディレクトリ構成

すべてを `src/` の下に置き、 `index.ts` でルートを組み立てます。D1 は `c.env.DB` で受け取り、SQL を直接書きます。

```
src/
├─ domain/                         # 最内層。外部ライブラリ禁止
│  ├─ shared/
│  │  └─ domain-error.ts
│  └─ task/                         # Task 集約
│     ├─ task.ts                    # エンティティ（集約ルート）
│     ├─ task-id.ts                 # 値オブジェクト
│     ├─ task-title.ts              # 値オブジェクト
│     └─ task-repository.ts         # リポジトリ IF
├─ application/
│  ├─ errors.ts                     # NotFoundError など
│  └─ task/
│     ├─ task-dto.ts
│     ├─ create-task.ts             # 1 ファイル = 1 ユースケース
│     ├─ complete-task.ts
│     └─ list-tasks.ts
├─ infrastructure/
│  ├─ d1/
│  │  └─ d1-task-repository.ts      # 本番用
│  └─ memory/
│     └─ in-memory-task-repository.ts # テスト用
├─ presentation/
│  ├─ routes/
│  │  └─ tasks.ts                   # Hono のルート定義
│  └─ middleware/
│     └─ di.ts                      # ユースケースを c.var に注入
├─ container.ts                     # Composition Root（唯一すべてを知る場所）
├─ env.ts                           # Hono の型 (Bindings / Variables)
└─ index.ts                         # エントリポイント
test/
└─ complete-task.test.ts
migrations/
└─ 0001_create_tasks.sql
wrangler.jsonc                      # D1 バインディングを手で書く
```

### Hono 版のサンプルコード

内側から順に見ていきます。タブで層を切り替えてください。

① domain

② application

③ infrastructure

④ presentation

⑤ 組み立て

⑥ テスト

domain src/domain/shared/domain-error.ts

```
export class DomainError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'DomainError'
  }
}
```

domain src/domain/task/task-id.ts

```
export class TaskId {
  private constructor(readonly value: string) {}

  static create(): TaskId {
    return new TaskId(crypto.randomUUID())
  }
  // DB などから復元するとき用
  static reconstruct(value: string): TaskId {
    return new TaskId(value)
  }
  equals(other: TaskId): boolean {
    return this.value === other.value
  }
}
```

domain src/domain/task/task-title.ts

```
import { DomainError } from '../shared/domain-error'

export class TaskTitle {
  private constructor(readonly value: string) {}

  // 作れた時点で「1〜100 文字」が保証される
  static of(raw: string): TaskTitle {
    const v = raw.trim()
    if (v.length === 0 || v.length > 100) {
      throw new DomainError('タイトルは 1〜100 文字で入力してください')
    }
    return new TaskTitle(v)
  }
}
```

domain src/domain/task/task.ts（エンティティ / 集約ルート）

```
import { DomainError } from '../shared/domain-error'
import { TaskId } from './task-id'
import { TaskTitle } from './task-title'

export type TaskStatus = 'todo' | 'done'

export class Task {
  private constructor(
    readonly id: TaskId,
    private _title: TaskTitle,
    private _status: TaskStatus,
    readonly createdAt: Date,
  ) {}

  // 新規作成：必ず未完了から始まる
  static create(title: TaskTitle): Task {
    return new Task(TaskId.create(), title, 'todo', new Date())
  }

  // 永続化層からの復元：ルール検証はしない
  static reconstruct(p: {
    id: TaskId; title: TaskTitle; status: TaskStatus; createdAt: Date
  }): Task {
    return new Task(p.id, p.title, p.status, p.createdAt)
  }

  get title() { return this._title }
  get status() { return this._status }

  // 業務ルールはエンティティのメソッドに閉じ込める
  complete(): void {
    if (this._status === 'done') {
      throw new DomainError('このタスクはすでに完了しています')
    }
    this._status = 'done'
  }

  rename(title: TaskTitle): void {
    if (this._status === 'done') {
      throw new DomainError('完了済みのタスクは名前を変更できません')
    }
    this._title = title
  }
}
```

domain src/domain/task/task-repository.ts（インターフェースだけ）

```
import type { Task } from './task'
import type { TaskId } from './task-id'

// D1 も SQL も出てこない。「集約を出し入れする箱」としての約束だけ
export interface TaskRepository {
  findById(id: TaskId): Promise<Task | null>
  findAll(): Promise<Task[]>
  save(task: Task): Promise<void>
}
```

ここまで `hono` も `D1Database` も一度も出てきません。これが「ドメインは何にも依存しない」の実際の姿です。

application src/application/errors.ts

```
export class NotFoundError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'NotFoundError'
  }
}
```

application src/application/task/task-dto.ts

```
import type { Task, TaskStatus } from '../../domain/task/task'

// 外へ返す形。エンティティをそのまま外に出さない
export type TaskDto = {
  id: string
  title: string
  status: TaskStatus
  createdAt: string
}

export const toTaskDto = (t: Task): TaskDto => ({
  id: t.id.value,
  title: t.title.value,
  status: t.status,
  createdAt: t.createdAt.toISOString(),
})
```

application src/application/task/create-task.ts

```
import { Task } from '../../domain/task/task'
import { TaskTitle } from '../../domain/task/task-title'
import type { TaskRepository } from '../../domain/task/task-repository'
import { toTaskDto, type TaskDto } from './task-dto'

export type CreateTaskInput = { title: string }

export class CreateTaskUseCase {
  // 受け取るのはインターフェース。D1 かどうかは知らない
  constructor(private readonly repo: TaskRepository) {}

  async execute(input: CreateTaskInput): Promise<TaskDto> {
    const task = Task.create(TaskTitle.of(input.title))
    await this.repo.save(task)
    return toTaskDto(task)
  }
}
```

application src/application/task/complete-task.ts

```
import { TaskId } from '../../domain/task/task-id'
import type { TaskRepository } from '../../domain/task/task-repository'
import { NotFoundError } from '../errors'
import { toTaskDto, type TaskDto } from './task-dto'

export class CompleteTaskUseCase {
  constructor(private readonly repo: TaskRepository) {}

  // 取り出す → ドメインに頼む → 保存する。段取りだけ
  async execute(id: string): Promise<TaskDto> {
    const task = await this.repo.findById(TaskId.reconstruct(id))
    if (!task) throw new NotFoundError('タスクが見つかりません')

    task.complete() // 「完了済みなら NG」はここではなく Task が判断

    await this.repo.save(task)
    return toTaskDto(task)
  }
}
```

application src/application/task/list-tasks.ts

```
import type { TaskRepository } from '../../domain/task/task-repository'
import { toTaskDto, type TaskDto } from './task-dto'

export class ListTasksUseCase {
  constructor(private readonly repo: TaskRepository) {}

  async execute(): Promise<TaskDto[]> {
    const tasks = await this.repo.findAll()
    return tasks.map(toTaskDto)
  }
}
```

migrations/0001_create_tasks.sql

```
CREATE TABLE tasks (
  id         TEXT PRIMARY KEY,
  title      TEXT NOT NULL,
  status     TEXT NOT NULL CHECK (status IN ('todo', 'done')),
  created_at TEXT NOT NULL
);
```

infrastructure src/infrastructure/d1/d1-task-repository.ts

```
import { Task, type TaskStatus } from '../../domain/task/task'
import { TaskId } from '../../domain/task/task-id'
import { TaskTitle } from '../../domain/task/task-title'
import type { TaskRepository } from '../../domain/task/task-repository'

type TaskRow = {
  id: string
  title: string
  status: TaskStatus
  created_at: string
}

// DB の行 ⇄ エンティティの変換はインフラの責務
const toEntity = (r: TaskRow): Task =>
  Task.reconstruct({
    id: TaskId.reconstruct(r.id),
    title: TaskTitle.of(r.title),
    status: r.status,
    createdAt: new Date(r.created_at),
  })

export class D1TaskRepository implements TaskRepository {
  constructor(private readonly db: D1Database) {}

  async findById(id: TaskId): Promise<Task | null> {
    const row = await this.db
      .prepare('SELECT * FROM tasks WHERE id = ?')
      .bind(id.value)
      .first<TaskRow>()
    return row ? toEntity(row) : null
  }

  async findAll(): Promise<Task[]> {
    const { results } = await this.db
      .prepare('SELECT * FROM tasks ORDER BY created_at DESC')
      .all<TaskRow>()
    return results.map(toEntity)
  }

  // 集約単位で丸ごと保存（upsert）
  async save(task: Task): Promise<void> {
    await this.db
      .prepare(
        `INSERT INTO tasks (id, title, status, created_at)
         VALUES (?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET
           title = excluded.title,
           status = excluded.status`,
      )
      .bind(task.id.value, task.title.value, task.status, task.createdAt.toISOString())
      .run()
  }
}
```

infrastructure src/infrastructure/memory/in-memory-task-repository.ts

```
import type { Task } from '../../domain/task/task'
import type { TaskId } from '../../domain/task/task-id'
import type { TaskRepository } from '../../domain/task/task-repository'

// 同じ IF を満たすので、テストではこちらに差し替えられる
export class InMemoryTaskRepository implements TaskRepository {
  private store = new Map<string, Task>()

  async findById(id: TaskId) {
    return this.store.get(id.value) ?? null
  }
  async findAll() {
    return [...this.store.values()]
  }
  async save(task: Task) {
    this.store.set(task.id.value, task)
  }
}
```

ORM（Drizzle や Prisma）を使う場合も、置き場所はここ。ORM の型やクエリが domain / application に漏れないようにします。

presentation src/env.ts（Hono の型定義）

```
import type { CreateTaskUseCase } from './application/task/create-task'
import type { CompleteTaskUseCase } from './application/task/complete-task'
import type { ListTasksUseCase } from './application/task/list-tasks'

export type UseCases = {
  createTask: CreateTaskUseCase
  completeTask: CompleteTaskUseCase
  listTasks: ListTasksUseCase
}

export type AppEnv = {
  Bindings: { DB: D1Database }     // wrangler の D1 バインディング
  Variables: { useCases: UseCases } // c.var.useCases で取り出す
}
```

presentation src/presentation/routes/tasks.ts

```
import { Hono } from 'hono'
import { zValidator } from '@hono/zod-validator'
import { z } from 'zod'
import type { AppEnv } from '../../env'

// ここで見るのは「リクエストの形」だけ。
// 「1〜100 文字」は業務ルールなので TaskTitle に任せる
const createTaskSchema = z.object({ title: z.string() })

export const taskRoutes = new Hono<AppEnv>()
  .get('/', async (c) => {
    const tasks = await c.var.useCases.listTasks.execute()
    return c.json(tasks)
  })
  .post('/', zValidator('json', createTaskSchema), async (c) => {
    const task = await c.var.useCases.createTask.execute(c.req.valid('json'))
    return c.json(task, 201)
  })
  .post('/:id/complete', async (c) => {
    const task = await c.var.useCases.completeTask.execute(c.req.param('id'))
    return c.json(task)
  })
```

ハンドラは「HTTP → ユースケースの入力」「ユースケースの出力 → HTTP」の変換だけ。 `if` で業務判断を始めたら、それはドメインに移すサインです。

src/container.ts（Composition Root）

```
import { D1TaskRepository } from './infrastructure/d1/d1-task-repository'
import { CreateTaskUseCase } from './application/task/create-task'
import { CompleteTaskUseCase } from './application/task/complete-task'
import { ListTasksUseCase } from './application/task/list-tasks'
import type { UseCases } from './env'

// 具象クラス（D1）とユースケースを結びつける、唯一の場所
export const buildUseCases = (db: D1Database): UseCases => {
  const taskRepo = new D1TaskRepository(db)
  return {
    createTask: new CreateTaskUseCase(taskRepo),
    completeTask: new CompleteTaskUseCase(taskRepo),
    listTasks: new ListTasksUseCase(taskRepo),
  }
}
```

presentation src/presentation/middleware/di.ts

```
import { createMiddleware } from 'hono/factory'
import { buildUseCases } from '../../container'
import type { AppEnv } from '../../env'

// Workers では env（DB）がリクエストごとに渡されるので、
// ミドルウェアでユースケースを組み立てて c.var に載せる
export const di = createMiddleware<AppEnv>(async (c, next) => {
  c.set('useCases', buildUseCases(c.env.DB))
  await next()
})
```

src/index.ts

```
import { Hono } from 'hono'
import { DomainError } from './domain/shared/domain-error'
import { NotFoundError } from './application/errors'
import { di } from './presentation/middleware/di'
import { taskRoutes } from './presentation/routes/tasks'
import type { AppEnv } from './env'

const app = new Hono<AppEnv>()

app.use('*', di)
app.route('/tasks', taskRoutes)

// ドメインの例外 → HTTP ステータスの対応は一番外側で
app.onError((err, c) => {
  if (err instanceof DomainError) return c.json({ message: err.message }, 400)
  if (err instanceof NotFoundError) return c.json({ message: err.message }, 404)
  console.error(err)
  return c.json({ message: 'Internal Server Error' }, 500)
})

export default app
```

tests test/complete-task.test.ts（Vitest）

```
import { describe, expect, test } from 'vitest'
import { CreateTaskUseCase } from '../src/application/task/create-task'
import { CompleteTaskUseCase } from '../src/application/task/complete-task'
import { DomainError } from '../src/domain/shared/domain-error'
import { InMemoryTaskRepository } from '../src/infrastructure/memory/in-memory-task-repository'

describe('CompleteTaskUseCase', () => {
  test('完了済みのタスクはもう一度完了できない', async () => {
    // D1 も Hono も起動しない。リポジトリを差し替えるだけ
    const repo = new InMemoryTaskRepository()
    const created = await new CreateTaskUseCase(repo).execute({ title: '牛乳を買う' })
    const complete = new CompleteTaskUseCase(repo)

    await complete.execute(created.id)

    await expect(complete.execute(created.id)).rejects.toThrow(DomainError)
  })
})
```

HTTP まで含めて確かめたいときは、Hono の `app.request('/tasks', { method: 'POST', ... })` でテストできます。その場合も DI ミドルウェアを差し替えれば D1 なしで動かせます。

### Void とは

Void は、Vite・Vitest・Rolldown などを開発する VoidZero（2026 年に Cloudflare に合流）が出している、オープンソースのフルスタックフレームワーク兼デプロイ CLI です。中身のルーティングとミドルウェアは **Hono** で、Cloudflare Workers に向けて動きます。主な特徴は次の 3 つです。

- `routes/` の **ファイル配置がそのまま URL** になる（ファイルベースルーティング）
- `void/db` から **Drizzle の `db` ** をそのまま import できる
- コードの import を見て D1 などのバインディングを **自動で用意** する。 `wrangler.jsonc` は手書きしなくてよい

ここでは 2026 年 11 月時点の void 1.5.0 の同梱ドキュメントに沿って書いています。

### Void 版のディレクトリ構成

`routes/` ・ `middleware/` ・ `db/` は Void が意味を持たせているフォルダです。一方 `src/` には規約がないので、 **オニオンの内側（domain / application / infrastructure）をここに置きます** 。

```
my-app/
├─ routes/                         # presentation（Void の規約）
│  └─ api/
│     └─ tasks/
│        ├─ index.ts                # GET・POST /api/tasks
│        └─ [id]/
│           └─ complete.ts          # POST /api/tasks/:id/complete
├─ middleware/                     # presentation（番号順に実行）
│  ├─ 01.error.ts                   # 例外 → HTTP ステータス
│  └─ 02.di.ts                      # ユースケースを c.var に注入
├─ db/                             # infrastructure（Void の規約）
│  ├─ schema.ts                     # Drizzle のテーブル定義
│  └─ migrations/                   # void db generate で生成
├─ src/                             # 規約なし＝オニオンの内側を置く
│  ├─ domain/                      # Hono 版と 1 行も変わらない
│  │  ├─ shared/domain-error.ts
│  │  └─ task/
│  │     ├─ task.ts
│  │     ├─ task-id.ts
│  │     ├─ task-title.ts
│  │     └─ task-repository.ts
│  ├─ application/                 # Hono 版と 1 行も変わらない
│  │  ├─ errors.ts
│  │  └─ task/
│  │     ├─ task-dto.ts
│  │     ├─ create-task.ts
│  │     ├─ complete-task.ts
│  │     └─ list-tasks.ts
│  ├─ infrastructure/
│  │  ├─ drizzle/
│  │  │  └─ drizzle-task-repository.ts # void/db を使うのはここだけ
│  │  └─ memory/
│  │     └─ in-memory-task-repository.ts
│  └─ container.ts                  # Composition Root
├─ test/
│  └─ complete-task.test.ts
├─ vite.config.ts                   # voidPlugin() を登録
└─ void.config.ts                   # 任意
```

`void.config.ts` で `{ "sourceDir": "src" }` とすると、 `routes/` などの規約フォルダも `src/` の下に移せます。ただしその場合も、domain / application は規約フォルダの外に置きます。

### Void 版のサンプルコード

変わるのは外側の層だけです。タブで切り替えてください。

① domain・application

② infrastructure

③ routes

④ middleware・組み立て

⑤ テスト

domain application **Hono 版のコードをそのまま `src/` にコピーするだけです。**

`Task` ・ `TaskTitle` ・ `TaskRepository` ・ `CompleteTaskUseCase` などは、Hono も Void も import していません。だからフレームワークを替えても 1 行も書き換えずに済みます。これがオニオンアーキテクチャのいちばん分かりやすい利点です。

コードは Hono 版のタブ「① domain」「② application」を参照してください。

infrastructure db/schema.ts（Void の規約フォルダ）

```
import { sqliteTable, text } from 'void/schema-d1'

// DB の形の定義。ドメインの Task とは別物として扱う
export const tasks = sqliteTable('tasks', {
  id: text('id').primaryKey(),
  title: text('title').notNull(),
  status: text('status', { enum: ['todo', 'done'] }).notNull(),
  createdAt: text('created_at').notNull(),
})
```

マイグレーションは `void db generate` で `db/migrations/` に作られ、 `void deploy` のときに適用されます。

infrastructure src/infrastructure/drizzle/drizzle-task-repository.ts

```
import { tasks } from '@schema'          // Void が用意する db/schema.ts への別名
import { db, desc, eq } from 'void/db'   // Drizzle の db と演算子
import { Task } from '../../domain/task/task'
import { TaskId } from '../../domain/task/task-id'
import { TaskTitle } from '../../domain/task/task-title'
import type { TaskRepository } from '../../domain/task/task-repository'

type TaskRow = typeof tasks.$inferSelect

const toEntity = (r: TaskRow): Task =>
  Task.reconstruct({
    id: TaskId.reconstruct(r.id),
    title: TaskTitle.of(r.title),
    status: r.status,
    createdAt: new Date(r.createdAt),
  })

// Hono 版の D1TaskRepository と同じ IF を、Drizzle で実装したもの
export class DrizzleTaskRepository implements TaskRepository {
  async findById(id: TaskId): Promise<Task | null> {
    const row = await db.select().from(tasks).where(eq(tasks.id, id.value)).get()
    return row ? toEntity(row) : null
  }

  async findAll(): Promise<Task[]> {
    const rows = await db.select().from(tasks).orderBy(desc(tasks.createdAt)).all()
    return rows.map(toEntity)
  }

  async save(task: Task): Promise<void> {
    await db
      .insert(tasks)
      .values({
        id: task.id.value,
        title: task.title.value,
        status: task.status,
        createdAt: task.createdAt.toISOString(),
      })
      .onConflictDoUpdate({
        target: tasks.id,
        set: { title: task.title.value, status: task.status },
      })
  }
}
```

`void/db` を import したことが手がかりになって、Void が D1 の `DB` バインディングを自動で用意します（ `src/` も検出の対象）。 `in-memory-task-repository.ts` は Hono 版と同じです。

presentation routes/api/tasks/index.ts → `GET・POST /api/tasks`

```
import { defineHandler } from 'void'
import { z } from 'zod'

// 見るのは「リクエストの形」だけ。1〜100 文字のルールは TaskTitle に任せる
const createTaskSchema = z.object({ title: z.string() })

// 戻り値のオブジェクトは自動で JSON になる
export const GET = defineHandler((c) => c.get('useCases').listTasks.execute())

export const POST = defineHandler.withValidator({ body: createTaskSchema })(
  async (c, { body }) => {
    const task = await c.get('useCases').createTask.execute(body)
    return c.json(task, 201)
  },
)
```

presentation routes/api/tasks/[id]/complete.ts → `POST /api/tasks/:id/complete`

```
import { defineHandler } from 'void'

// [id] フォルダが :id パラメータになる
export const POST = defineHandler((c) =>
  c.get('useCases').completeTask.execute(c.req.param('id')),
)
```

Hono 版の `app.route('/tasks', taskRoutes)` にあたる組み立てはありません。ファイルを置いた場所がそのまま URL になります。 `withValidator` は Standard Schema 対応なので、Zod の代わりに Valibot なども使えます。

src/container.ts（Composition Root）

```
import { DrizzleTaskRepository } from './infrastructure/drizzle/drizzle-task-repository'
import { CreateTaskUseCase } from './application/task/create-task'
import { CompleteTaskUseCase } from './application/task/complete-task'
import { ListTasksUseCase } from './application/task/list-tasks'

export type UseCases = {
  createTask: CreateTaskUseCase
  completeTask: CompleteTaskUseCase
  listTasks: ListTasksUseCase
}

// D1 の受け渡しは void/db が引き受けるので、引数は要らない
export const buildUseCases = (): UseCases => {
  const taskRepo = new DrizzleTaskRepository()
  return {
    createTask: new CreateTaskUseCase(taskRepo),
    completeTask: new CompleteTaskUseCase(taskRepo),
    listTasks: new ListTasksUseCase(taskRepo),
  }
}
```

presentation middleware/02.di.ts

```
import { defineMiddleware } from 'void'
import { buildUseCases, type UseCases } from '../src/container'

// Hono 版の AppEnv['Variables'] にあたる型を、Void の型に追加する
declare module 'void' {
  interface CloudContextVariables {
    useCases: UseCases
  }
}

export default defineMiddleware(async (c, next) => {
  c.set('useCases', buildUseCases())
  await next()
})
```

presentation middleware/01.error.ts

```
import { defineMiddleware } from 'void'
import { DomainError } from '../src/domain/shared/domain-error'
import { NotFoundError } from '../src/application/errors'

// Void では Hono の app を直接触らないので、app.onError の代わりに
// ミドルウェアで c.error（ハンドラで投げられた例外）を見て応答を差し替える
export default defineMiddleware(async (c, next) => {
  await next()
  const err = c.error
  if (err instanceof DomainError) {
    c.res = c.json({ message: err.message }, 400)
  } else if (err instanceof NotFoundError) {
    c.res = c.json({ message: err.message }, 404)
  }
})
```

Void の標準のエラー処理は、 `HTTPException` ならその応答を返し、それ以外は 500 にしてログに出します。上のミドルウェアはその 500 を 400・404 に置き換えるもので、ドメインに HTTP の知識（ `HTTPException` ）を持ち込まずに済みます。

vite.config.ts

```
import { defineConfig } from 'vite'
import { voidPlugin } from 'void'

export default defineConfig({
  plugins: [voidPlugin()],
})
```

tests **Hono 版の `test/complete-task.test.ts` がそのまま動きます。**

テストが触るのは application と InMemory リポジトリだけで、Void も Drizzle も読み込みません。フレームワークを移しても、ユースケースのテストは書き直さずに済みます。

### Hono と Void で変わるもの・変わらないもの

| 項目 | Hono | Void |
| --- | --- | --- |
| domain application | 同じコード （どちらも FW を import しない） |  |
| ルーティング | `index.ts` で `app.route()` を組む | `routes/` のファイル配置＝URL |
| 入力の形の検証 | `zValidator('json', schema)` | `defineHandler.withValidator({ body })` |
| DI（ユースケース注入） | `createMiddleware` ＋ `AppEnv` 型 | `middleware/` ＋ `CloudContextVariables` の型拡張 |
| 例外 → HTTP | `app.onError` | ミドルウェアで `c.error` を見る |
| DB アクセス | `c.env.DB` を受け取り SQL を書く | `void/db` の Drizzle を使う |
| Cloudflare の設定 | `wrangler.jsonc` を手で書く | import から自動で決まる（ `void deploy` ） |

差は外側の層（presentation / infrastructure）に集まっています。依存の向きを守っていれば、フレームワークは「外側の差し替え部品」として扱えます。

## 1 リクエストの流れ

`POST /tasks/:id/complete` が来たとき、各層がやることは次のとおりです。

**Route** Hono のルート／Void の `routes/` 。パスから id を取り出し、ユースケースを呼ぶ

→

**UseCase** リポジトリ IF で Task を取得

→

**Task.complete()** 「完了済みなら NG」を判定し状態を変える

→

**Repository 実装** D1 の SQL（Hono 版）または Drizzle（Void 版）で保存

→

**Response** DTO を JSON で返す／例外は 400・404 に変換

## 軽量版：AI 時代の落としどころ

ここまでの構成は教科書どおりですが、ファイルが 17 個あります。AI 時代のコストは「書く量」より **「読む量」** です。AI に渡すコンテキストも、人がレビューする差分も、ファイル数に比例して増えます。そこで、 **思想は残して儀式を削った版** を作ります。

**残すのはこの 3 つだけ**

- 業務ルールは `task.ts` の中にしか書かない
- `task.ts` は Hono・Void・DB を import しない（依存は内向き）
- DB アクセスは `task.repo.ts` に閉じ込める

### ディレクトリ構成（層ごと → 機能ごと）

層でフォルダを分けるのをやめ、 **機能ごとのフォルダ** に全部入れます。AI に「タスク機能を直して」と頼むとき、渡すのは `features/task/` の 1 フォルダだけで済みます。

```
src/
├─ features/
│  └─ task/
│     ├─ task.ts             # ドメイン：型・ルール・リポジトリの型
│     ├─ task.usecases.ts    # ユースケース（関数）
│     ├─ task.repo.ts        # DB アクセス
│     ├─ task.routes.ts      # Hono のルート（Void なら routes/ に置く）
│     └─ task.test.ts
├─ shared/
│  └─ errors.ts             # DomainError / NotFoundError
└─ index.ts                 # Hono 版のみ。app.route と onError
```

ファイル名の接頭辞の色は、フル版と同じ層の色です。フォルダはまとめても、ファイル単位で層を分けています。

### サンプルコード

task.ts

task.usecases.ts

task.repo.ts

ルート

テスト

domain src/shared/errors.ts

```
export class DomainError extends Error {}
export class NotFoundError extends Error {}
```

domain src/features/task/task.ts

```
import { DomainError } from '../../shared/errors'

// 値オブジェクトはクラスにせず「ブランド型＋生成関数」で。
// TaskTitle 型の値は、この関数を通らないと作れない
export type TaskTitle = string & { readonly __brand: 'TaskTitle' }
export const TaskTitle = (raw: string): TaskTitle => {
  const v = raw.trim()
  if (v.length === 0 || v.length > 100) {
    throw new DomainError('タイトルは 1〜100 文字で入力してください')
  }
  return v as TaskTitle
}

// エンティティは「読み取り専用のデータ＋純粋関数」。
// プレーンなデータなので、そのまま JSON で返せる（DTO が要らない）
export type Task = Readonly<{
  id: string
  title: TaskTitle
  status: 'todo' | 'done'
  createdAt: string
}>

export const createTask = (title: TaskTitle): Task => ({
  id: crypto.randomUUID(),
  title,
  status: 'todo',
  createdAt: new Date().toISOString(),
})

export const completeTask = (t: Task): Task => {
  if (t.status === 'done') throw new DomainError('このタスクはすでに完了しています')
  return { ...t, status: 'done' }
}

export const renameTask = (t: Task, title: TaskTitle): Task => {
  if (t.status === 'done') throw new DomainError('完了済みのタスクは名前を変更できません')
  return { ...t, title }
}

// リポジトリの型はドメイン側に 5 行だけ。依存の向きはフル版と同じ
export type TaskRepo = {
  find(id: string): Promise<Task | null>
  list(): Promise<Task[]>
  save(t: Task): Promise<void>
}
```

フル版の `task.ts` ・ `task-id.ts` ・ `task-title.ts` ・ `task-repository.ts` ・ `task-dto.ts` の 5 ファイルが、この 1 ファイルにまとまりました。

application src/features/task/task.usecases.ts

```
import { NotFoundError } from '../../shared/errors'
import { completeTask, createTask, TaskTitle, type TaskRepo } from './task'

// ユースケースはクラス 3 つではなく、関数を返す関数 1 つ
export const taskUseCases = (repo: TaskRepo) => ({
  list: () => repo.list(),

  create: async (title: string) => {
    const task = createTask(TaskTitle(title))
    await repo.save(task)
    return task
  },

  complete: async (id: string) => {
    const task = await repo.find(id)
    if (!task) throw new NotFoundError('タスクが見つかりません')
    const done = completeTask(task) // ルールの判断は task.ts に任せる
    await repo.save(done)
    return done
  },
})
```

infrastructure src/features/task/task.repo.ts（Hono 版：D1 を直接）

```
import type { Task, TaskRepo } from './task'

export const taskRepo = (db: D1Database): TaskRepo => ({
  find: (id) =>
    db.prepare('SELECT id, title, status, created_at AS createdAt FROM tasks WHERE id = ?')
      .bind(id).first<Task>(),

  list: async () => {
    const { results } = await db
      .prepare('SELECT id, title, status, created_at AS createdAt FROM tasks ORDER BY created_at DESC')
      .all<Task>()
    return results
  },

  save: async (t) => {
    await db.prepare(
      `INSERT INTO tasks (id, title, status, created_at) VALUES (?, ?, ?, ?)
       ON CONFLICT(id) DO UPDATE SET title = excluded.title, status = excluded.status`,
    ).bind(t.id, t.title, t.status, t.createdAt).run()
  },
})
```

infrastructure src/features/task/task.repo.ts（Void 版：void/db の Drizzle）

```
import { tasks } from '@schema'
import { db, desc, eq } from 'void/db'
import type { Task, TaskRepo } from './task'

// DB に入っているのは検証済みの値なので、読み出しは型を付けるだけ
const toTask = (r: typeof tasks.$inferSelect) => r as Task

export const taskRepo: TaskRepo = {
  find: async (id) => {
    const r = await db.select().from(tasks).where(eq(tasks.id, id)).get()
    return r ? toTask(r) : null
  },
  list: async () =>
    (await db.select().from(tasks).orderBy(desc(tasks.createdAt)).all()).map(toTask),
  save: async (t) => {
    await db.insert(tasks).values(t).onConflictDoUpdate({
      target: tasks.id,
      set: { title: t.title, status: t.status },
    })
  },
}
```

「実装が 1 つしかないうちはインターフェースを作らない」も選べますが、ここでは型を 5 行だけ `task.ts` に残しました。テストで Map に差し替えられるのと、 `task.usecases.ts` が DB を一切 import しないで済むためです。

presentation src/features/task/task.routes.ts（Hono 版）

```
import { Hono, type Context } from 'hono'
import { zValidator } from '@hono/zod-validator'
import { z } from 'zod'
import { taskRepo } from './task.repo'
import { taskUseCases } from './task.usecases'

type Env = { Bindings: { DB: D1Database } }

// container.ts も DI ミドルウェアもなし。組み立ては 1 行
const uc = (c: Context<Env>) => taskUseCases(taskRepo(c.env.DB))

export const taskRoutes = new Hono<Env>()
  .get('/', async (c) => c.json(await uc(c).list()))
  .post('/', zValidator('json', z.object({ title: z.string() })), async (c) =>
    c.json(await uc(c).create(c.req.valid('json').title), 201))
  .post('/:id/complete', async (c) =>
    c.json(await uc(c).complete(c.req.param('id'))))
```

`index.ts` の `app.route('/tasks', taskRoutes)` と `app.onError` はフル版と同じです。

presentation routes/api/tasks/index.ts（Void 版）

```
import { defineHandler } from 'void'
import { z } from 'zod'
import { taskRepo } from '../../../src/features/task/task.repo'
import { taskUseCases } from '../../../src/features/task/task.usecases'

const uc = taskUseCases(taskRepo)

export const GET = defineHandler(() => uc.list())

export const POST = defineHandler.withValidator({ body: z.object({ title: z.string() }) })(
  async (c, { body }) => c.json(await uc.create(body.title), 201),
)
```

presentation routes/api/tasks/[id]/complete.ts（Void 版）

```
import { defineHandler } from 'void'
import { taskRepo } from '../../../../src/features/task/task.repo'
import { taskUseCases } from '../../../../src/features/task/task.usecases'

export const POST = defineHandler((c) =>
  taskUseCases(taskRepo).complete(c.req.param('id')))
```

Void 版では `task.routes.ts` の代わりに `routes/` を使います。例外の変換はフル版の `middleware/01.error.ts` と同じです。

src/features/task/task.test.ts（Vitest）

```
import { describe, expect, test } from 'vitest'
import { DomainError } from '../../shared/errors'
import { completeTask, createTask, TaskTitle, type Task, type TaskRepo } from './task'
import { taskUseCases } from './task.usecases'

// ルールは純粋関数なので、リポジトリすら要らない
test('完了済みのタスクはもう一度完了できない', () => {
  const done = completeTask(createTask(TaskTitle('牛乳を買う')))
  expect(() => completeTask(done)).toThrow(DomainError)
})

// InMemory リポジトリのファイルは作らず、テストの中で数行で用意する
const memoryRepo = (): TaskRepo => {
  const m = new Map<string, Task>()
  return {
    find: async (id) => m.get(id) ?? null,
    list: async () => [...m.values()],
    save: async (t) => { m.set(t.id, t) },
  }
}

describe('taskUseCases', () => {
  test('作成して完了できる', async () => {
    const uc = taskUseCases(memoryRepo())
    const task = await uc.create('牛乳を買う')
    expect((await uc.complete(task.id)).status).toBe('done')
  })
})
```

### 削ったもの・戻す目安

| フル版 | 軽量版 | こうなったらフル版に戻す |
| --- | --- | --- |
| 層ごとのフォルダ | 機能ごとのフォルダ | 複数の機能で共有するドメインが増えてきた |
| `TaskId` 値オブジェクト | ただの `string` | ID の形式にルールができた、別の ID と取り違える事故が起きた |
| エンティティのクラス | 読み取り専用の型＋純粋関数 | 状態の組み合わせが複雑になり、メソッドでまとめたほうが読みやすくなった |
| DTO と変換関数 | なし（Task をそのまま返す） | 外に出したくない項目や、API だけの形が出てきた |
| ユースケースのクラス ×3 | 関数 1 ファイル | ユースケースごとに依存がばらばらになってきた |
| `container.ts` ・DI ミドルウェア | ルートで 1 行 | 依存が増え、組み立てを 1 か所にまとめたくなった |
| InMemory リポジトリのファイル | テスト内の Map | 複数のテストファイルで使い回すようになった |

ファイル数は 17 → 7（Hono 版）。最初から完成形を作らず、痛みが出た部分だけフル版に寄せていけば十分です。

### AI に守らせるルールを書いておく

ファイルを減らした分、境界は「ルール」で守ります。 `CLAUDE.md` や `AGENTS.md` （Void は `void init` で作成）に、たとえば次のように書いておきます。

```
## アーキテクチャ
- 機能は src/features/<name>/ に置く
- 業務ルールは <name>.ts の関数にだけ書く。ルートやリポジトリに if で判断を書かない
- <name>.ts は hono / void / DB を import しない
- ルールを足したら <name>.test.ts にテストを足す
```

「どこに何を書くか」が決まっていれば、AI は読む範囲を絞れ、人はレビューで見る場所を絞れます。コード量を減らしつつ、DDD の効き目はここで残ります。

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

CRUD 中心でルールが少ないなら、ファイル数が増えるコストのほうが大きい。業務ルールが多い・長く育てる・チームで触る、といった条件がそろうほど効いてくる。まずは「軽量版」で始めて、ルールが増えた部分からフル版に寄せていけばよい。
