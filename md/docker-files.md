<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Dockerfile と Compose の書き方

> Dockerfile・マルチステージビルド・compose.yaml・devcontainer.json の書き方を、注釈付きの例と落とし穴で整理。

- URL: https://memo.taka1156.site/docker-files.html
- タグ: インフラ, 開発ツール
- 日付: 2026-11-03

---

Dockerfile ・ マルチステージ ・ compose.yaml ・ devcontainer.json を「書く側」から整理

**ざっくり言うと**

- **Dockerfile** は「イメージの作り方」。変わりにくいものを上、変わりやすいものを下に書くとビルドキャッシュが効く。
- **マルチステージ** で「ビルド用」と「実行用」を分け、本番イメージには成果物だけをコピーする。
- **compose.yaml** は「複数コンテナの並べ方」、 **devcontainer.json** は「エディタがどのコンテナに入って開発するか」。後者は前者を呼び出せる。

## 4 つのファイルの役割

**.dockerignore**

ビルドに **送らない** ファイル。 `COPY . .` の範囲を絞る。

**Dockerfile**

**1 つのイメージ** の作り方。 `docker build` が読む。

**compose.yaml**

**複数のコンテナ** （app・db…）の起動設定。 `docker compose up` が読む。

**devcontainer.json**

VS Code などが **開発環境として入るコンテナ** の設定。上の 2 つを参照できる。

devcontainer.json

→ 使う

compose.yaml

→ build:

Dockerfile

→ COPY

ソース .dockerignore で除外

## Dockerfile の基本形

Dockerfile

```
# syntax=docker/dockerfile:1
# ↑ 最新の Dockerfile 構文を使う宣言（任意）。ディレクティブ行には何も書き足さない
# ベースイメージ。タグは必ず固定（latest にしない）
FROM node:22-slim
# 以降の作業ディレクトリ。なければ作られる
WORKDIR /app

# ① 依存の定義だけ先にコピー
COPY package.json package-lock.json ./
# ② 依存をインストール（↑が変わらない限りキャッシュ）
RUN npm ci

# ③ ソースは最後にコピー
COPY . .

# 実行時にも残る環境変数
ENV NODE_ENV=production
# root で動かさない
USER node
# ドキュメント。これだけでは公開されない
EXPOSE 3000
# exec 形式（JSON 配列）で書く
CMD ["node", "server.js"]
```

Dockerfile と .dockerignore のコメントは行頭の `#` だけ。命令の後ろに書いた `#` は引数（パターン）の一部になる。

| 命令 | 何をする | 書くときの注意 |
| --- | --- | --- |
| FROM | 土台のイメージを選ぶ | タグを固定する。 `AS 名前` でステージに名前を付けられる |
| RUN | ビルド中にコマンドを実行（層ができる） | `apt-get update && apt-get install …` は 1 つの RUN にまとめる（別にすると古い一覧がキャッシュされる） |
| COPY / ADD | ファイルをイメージに入れる（層ができる） | 基本は COPY。ADD は URL 取得や tar 展開もするので、それが要るときだけ |
| ARG / ENV | ARG はビルド時だけ、ENV は実行時にも残る | どちらもイメージの履歴に残るので 秘密情報を入れない （ `RUN --mount=type=secret` を使う） |
| USER | 以降を実行するユーザー | 最後に一般ユーザーへ切り替える |
| CMD | 起動時の既定コマンド | `docker run イメージ 引数` で丸ごと置き換わる |
| ENTRYPOINT | 必ず実行される本体 | CMD と併用すると CMD が「既定の引数」になる |
| HEALTHCHECK | 動いているかの確認方法 | compose の `healthcheck:` で書いてもよい |

### CMD は exec 形式で書く

シェル形式

```
CMD node server.js
```

`/bin/sh -c` が PID 1 になり、 `docker stop` の SIGTERM がアプリに届かない。10 秒待って強制終了される。

exec 形式

```
CMD ["node", "server.js"]
```

アプリ自身が PID 1 になり、SIGTERM を直接受け取れる。ただし PID 1 には既定の終了動作がないので、アプリ側で SIGTERM を処理するか、 `docker run --init` （compose なら `init: true` ）を使う。

## キャッシュが効く順番

Docker は上から 1 行ずつ「前回と同じか」を見て、変わった行 **以降はすべて作り直す** 。COPY は中身のファイルが変わると「変わった」扱い。

遅い

```
COPY . .
# ↓ ソース 1 行の変更でも毎回走る
RUN npm ci
```

速い

```
COPY package*.json ./
# ↓ 依存が変わったときだけ走る
RUN npm ci
COPY . .
```

さらに速くするなら、パッケージのダウンロードキャッシュをビルド間で使い回す: `RUN --mount=type=cache,target=/root/.npm npm ci` （BuildKit。今の Docker では標準）。

### .dockerignore

.dockerignore

```
# ホストの node_modules を持ち込まない（OS 違いで壊れる）
node_modules
.git
# 秘密情報をイメージに焼き込まない
.env
dist
*.log
```

書かないと `COPY . .` がこれらまで送り、ビルドが遅くなるうえ、 `.env` がイメージに入る事故が起きる。

## マルチステージビルド

**build ステージ**

- コンパイラ・devDependencies
- ソース一式
- テスト・ビルドを実行

COPY --from=build

成果物だけ →

**runtime ステージ（最終イメージ）**

- 実行に要るものだけ
- 小さい・攻撃対象領域（アタックサーフェス）が小さい

最後の `FROM` 以降だけが最終イメージになる。途中のステージは捨てられるので、ビルド道具が本番に残らない。

Node.js

Go

Dockerfile

```
# syntax=docker/dockerfile:1
FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

# 開発用（compose や devcontainer から target: dev で使う）
FROM deps AS dev
COPY . .
CMD ["npm", "run", "dev"]

# ビルド用
FROM deps AS build
COPY . .
RUN npm run build

# 本番用（最後のステージ = 既定でビルドされる）
FROM node:22-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json ./
# 本番の依存だけ
RUN npm ci --omit=dev
# 成果物だけ持ってくる
COPY --from=build /app/dist ./dist
USER node
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

Dockerfile

```
# syntax=docker/dockerfile:1
FROM golang:1.27 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
# 静的リンクのバイナリ 1 つ
RUN CGO_ENABLED=0 go build -o /out/app ./cmd/app

# シェルもパッケージマネージャーもない最小イメージ
FROM gcr.io/distroless/static-debian13:nonroot
COPY --from=build /out/app /app
ENTRYPOINT ["/app"]
```

ベースイメージの選び方は [Docker イメージの種類](https://memo.taka1156.site/md/docker-images.md) を参照。

```
# 途中のステージまでで止める（開発用イメージなど）
$ docker build --target dev -t myapp:dev .
# 指定なしなら最後のステージ（runtime）
$ docker build -t myapp .
```

（元のページで操作できます → https://memo.taka1156.site/docker-files.html#multistage）

## compose.yaml

compose.yaml

```
# version: は不要（書いても無視される）。ファイル名は compose.yaml が推奨
services:
  app:
    build:
      context: .
      target: dev                    # マルチステージの dev ステージを使う
    ports:
      - "3000:3000"                  # "ホスト:コンテナ"。引用符で囲む
    env_file: .env
    environment:
      DATABASE_URL: postgres://app:app@db:5432/app   # ホスト名 = サービス名
    volumes:
      - .:/app                       # bind mount: ソースの変更がすぐ反映
      - node_modules:/app/node_modules   # ↑で上書きされないよう named volume で守る
    depends_on:
      db:
        condition: service_healthy   # db の healthcheck が通るまで待つ

  db:
    image: postgres:17
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    volumes:
      - db-data:/var/lib/postgresql/data   # データを残す
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      retries: 10

volumes:                             # named volume の宣言
  db-data:
  node_modules:
```

つなぎ方

- 同じ compose のコンテナ同士は **サービス名** で通信する（ `db:5432` ）。コンテナ内の `localhost` は自分自身。
- `ports` はホストに公開。コンテナ同士の通信だけなら不要。

待ち合わせ

- `depends_on: [db]` だけだと「起動した順」しか保証しない。DB が接続を受け付けるまで待つなら `condition: service_healthy` と healthcheck を組み合わせる。

ボリューム

- **bind mount** （ `./src:/app` ）: ホストのフォルダを見せる。開発向け。
- **named volume** （ `db-data:/…` ）: Docker が管理。DB データ向け。 `down -v` で消える。

環境ごとの差分

- `compose.override.yaml` は自動で重ねて読まれる。開発専用の設定はここへ。
- `profiles: [debug]` を付けたサービスは `--profile debug` のときだけ起動。

```
$ docker compose up -d --build   # ビルドして裏で起動
$ docker compose logs -f app     # ログを追う
$ docker compose exec app sh     # 動いているコンテナに入る
$ docker compose down            # 停止・削除（-v で named volume も消す）
$ docker compose config          # 展開後の最終的な設定を確認
```

## devcontainer.json

VS Code（Dev Containers 拡張）や GitHub Codespaces が読む。 `.devcontainer/devcontainer.json` に置き、 **コメントが書ける JSON（JSONC）** 。ベースの決め方は 3 通り。

compose を使う

Dockerfile から

イメージだけ

.devcontainer/devcontainer.json

```
{
  "name": "my-app",
  "dockerComposeFile": ["../compose.yaml", "compose.devcontainer.yaml"],  // このファイルからの相対パス
  "service": "app",                 // エディタが入るサービス
  "workspaceFolder": "/app",
  "shutdownAction": "stopCompose",  // ウィンドウを閉じたら compose ごと止める

  "features": {                     // 追加ツールを宣言だけで入れる
    "ghcr.io/devcontainers/features/github-cli:1": {}
  },
  "forwardPorts": [3000],
  "postCreateCommand": "npm ci",     // コンテナ作成後に 1 回
  "customizations": {
    "vscode": {
      "extensions": ["dbaeumer.vscode-eslint", "esbenp.prettier-vscode"]
    }
  },
  "remoteUser": "node"
}
```

.devcontainer/compose.devcontainer.yaml

```
services:
  app:
    command: sleep infinity   # 開発中はアプリを自動起動せず、コンテナを生かしておく
```

compose の設定はそのままアプリ用に使い、エディタ用の差分だけ 2 つ目のファイルで重ねる。

.devcontainer/devcontainer.json

```
{
  "name": "my-app",
  "build": {
    "dockerfile": "../Dockerfile",
    "context": "..",
    "target": "deps"                // マルチステージの途中を開発環境にする
  },
  "forwardPorts": [3000],
  "postCreateCommand": "npm ci",
  "remoteUser": "node"
}
```

DB などの相棒コンテナが要らない、単体のアプリ向け。ソースは自動でマウントされる。

.devcontainer/devcontainer.json

```
{
  "name": "my-app",
  "image": "mcr.microsoft.com/devcontainers/typescript-node:22",
  "features": {
    "ghcr.io/devcontainers/features/docker-outside-of-docker:1": {}
  },
  "postCreateCommand": "npm ci"
}
```

いちばん手軽。開発用に作り込まれた公式の devcontainers イメージ＋ features で足りるならこれ。

（元のページで操作できます → https://memo.taka1156.site/docker-files.html#devcontainer）

### いつ実行されるか

initializeCommand ホスト側で実行

→

onCreateCommand 作成時 1 回

→

updateContentCommand 作成時に最低 1 回。ソース更新時（プレビルドなど）

→

postCreateCommand 作成時 1 回（依存インストール向き）

→

postStartCommand 起動のたび

→

postAttachCommand エディタが接続するたび

Dockerfile にツールを書き足すか features にするか迷ったら: アプリの実行に要るものは Dockerfile、開発時だけ要るもの（gh・リンター等）は features や devcontainer 側に寄せると本番イメージが太らない。

## よくある誤解

✗ 誤解: EXPOSE を書けば外からアクセスできる

✓ 正しくは: EXPOSE は「このポートを使う」というメモにすぎない。ホストに公開するのは `docker run -p` や compose の `ports` 。

✗ 誤解: ENV や ARG なら API キーを書いても大丈夫

✓ 正しくは: どちらも `docker history` やイメージの設定から読める。ビルド時に必要なら `RUN --mount=type=secret` 、実行時なら compose の `env_file` などで外から渡す。

✗ 誤解: depends_on を書けば DB の準備完了まで待ってくれる

✓ 正しくは: 素の depends_on はコンテナの起動順だけ。接続を受け付けるまで待つには `condition: service_healthy` ＋ healthcheck が要る。

✗ 誤解: devcontainer.json は VS Code 専用

✓ 正しくは: Dev Container は公開された仕様で、Codespaces・JetBrains・CLI（ `devcontainer up` ）でも読める。エディタ固有の部分は `customizations` の中に分けて書く。

関連: [Docker 動作原理](https://memo.taka1156.site/md/docker.md) ／ [Docker イメージの種類](https://memo.taka1156.site/md/docker-images.md)
