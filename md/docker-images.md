<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Docker イメージの種類

> slim・alpine・bookworm から distroless 等の本番向け最小イメージまで、分類と glibc・musl・ABI の違いを図解。

- URL: https://memo.taka1156.site/docker-images.html
- タグ: インフラ
- 日付: 2026-11-02

---

slim / alpine / bookworm / trixie / distroless … タグの意味と glibc・musl・ABI の違い

**ざっくり言うと**

- `bookworm` や `trixie` は **Debian のバージョン名** 、 `slim` は **中身を削った版** 、 `alpine` は **別ディストロ** 。軸が違う。
- 一番効く違いは **C ライブラリ (libc)** 。Debian / Ubuntu / distroless は **glibc** 、Alpine は **musl** 。glibc 前提でビルドされたバイナリ（workerd など）は Alpine で動かない。
- Alpine は「小さい → pull が速い」だけで、 **実行が速いわけではない** 。迷ったら `*-slim` （Debian・glibc）が無難。本番の「まっさら」枠は **distroless / Chainguard / Docker Hardened Images / Chiseled Ubuntu / scratch** 。シェルもパッケージ管理も無く、 **ビルドは別ステージ** で行ってコピーする。

## タグの読み方

**node** イメージ名

:

**24** アプリのバージョン

-

**bookworm** ベース OS（Debian 12）

-

**slim** バリアント（削った版）

`node:24` OS 省略 → イメージ側が決めた Debian のフル版（node:24 はいまも bookworm。trixie は `-trixie` で明示）

`node:24-slim` 同じ Debian の slim 版

`node:24-alpine3.24` ベースが Alpine Linux 3.24（musl）

`python:3.13-trixie` Debian 13 を明示。省略すると Debian の世代交代で中身が変わる

Debian のコードネームは映画『トイ・ストーリー』のキャラ名。 **bullseye** = 11、 **bookworm** = 12（2026 年 7 月から LTS 期間。2028 年 6 月まで）、 **trixie** = 13（現行の安定版）。

## 全体の構造：みんな同じカーネルの上、違うのは libc から上

バリアント

フル bookworm / trixie

slim -slim

ubuntu noble / jammy

distroless base / cc / static

alpine -alpine3.24

scratch 空っぽ

ディストロ

Debian apt / dpkg

Ubuntu apt（Debian 系）

Debian 由来 パッケージ管理なし

Alpine apk / busybox

なし

C ライブラリ

(libc)

**glibc** GNU C Library — Linux の事実上の標準

**musl** 小さく単純

なし 静的バイナリのみ

カーネル

ホストの Linux カーネル（コンテナは共有する。イメージには含まれない）

「Alpine だからカーネルが違う」わけではない。システムコール（カーネルとの約束）は全イメージ共通で、差は libc とユーザーランドのツール群。

## イメージごとの特徴

サイズは Docker Hub の圧縮済み・amd64 の目安。 `node:24` 系の場合と OS 単体の場合を併記。アイコンは区別用の簡易バッジです。

すべて

glibc 必須（workerd・Prisma・ネイティブ拡張）

とにかく小さく

中に入ってデバッグしたい

ビルド用ステージ

本番のまっさら枠

D

（元のページで操作できます → https://memo.taka1156.site/docker-images.html#images）

### bookworm / trixie

Debian フル版（buildpack-deps ベース）

glibc 2.36 / 2.41 apt bash

node ≈ 380MB

- gcc・make・git・python3 など一式入り。 `npm install` でネイティブモジュールをビルドできる
- 何でも動く。困ったらここに戻れば解決する
- でかい。pull・push・CI キャッシュが重い
- 不要なパッケージが多く、脆弱性スキャンの指摘件数も多い

workerd ○ 本番 △ ビルド段 ◎

D_s

### *-slim

Debian から開発ツール・ドキュメントを抜いた版

glibc apt bash

node ≈ 75MB / OS ≈ 30MB

- glibc のままなので互換性はフル版と同じ。 **workerd・Prisma・sharp もそのまま動く**
- apt があるので足りないものは後から入れられる
- gcc 等がない。ネイティブモジュールのビルドが必要なら `build-essential` を足すか、マルチステージにする
- curl・ca-certificates・procps すら入っていないことがある

workerd ○ 本番 ◎ 迷ったらコレ

A

### *-alpine

Alpine Linux ベース（BusyBox + musl）

musl 1.2.x apk sh (ash)

node ≈ 55MB / OS ≈ 4MB

- とにかく小さい → pull・デプロイ・コールドスタート（イメージ取得）が速い
- `apk add` が速く、パッケージ数も少なく攻撃面が狭い
- **glibc 前提のバイナリが動かない** （workerd / wrangler dev、一部の Prisma エンジン、配布済み .so など）
- Python は manylinux の wheel が使えず、ソースビルドになりがち → 逆に遅く・大きくなる
- DNS・ロケール・スレッドのスタックサイズなど細かい挙動差でハマる

workerd ✕ Go 静的バイナリ ◎ Node 純 JS ○

U

### ubuntu:noble / jammy

Ubuntu 24.04 / 22.04 LTS

glibc 2.39 / 2.35 apt bash

OS ≈ 30MB

- 開発機・CI ランナーと同じ OS に揃えられる。PPA や公式 .deb が Ubuntu 向けのことが多い
- CUDA など GPU 系の公式イメージは Ubuntu ベースが主流
- 言語ランタイムの公式イメージ（node, python…）は Debian ベースが基本で、Ubuntu 版は少ない

workerd ○ GPU ◎

∅

### distroless

Debian のライブラリだけ残しシェルも消した版

glibc（base / cc） apt なし シェルなし

static ≈ 2MB / base ≈ 20MB

- glibc 互換のまま Alpine 並みに小さい。 **「小さくしたいけど musl は嫌」の答え**
- シェルが無いので侵入されても手が出しにくい。スキャン指摘も少ない
- `docker exec sh` できない。デバッグは `:debug` タグや ephemeral container で
- マルチステージ前提（ビルドは別イメージでやってコピーする）

workerd ○ （cc 系） 本番 ◎

W

### Chainguard (Wolfi)

CVE ゼロを目指して毎日再ビルドされる最小イメージ

glibc（Wolfi） apk（-dev のみ） nonroot 既定

static ≈ 1MB / glibc-dynamic ≈ 数MB

- Alpine と同じ `apk` 文化だが **libc は glibc** 。「Alpine の手軽さ × glibc 互換」
- SBOM・署名付き。脆弱性スキャンがほぼ真っ白になる
- 無料で使えるのは基本 `:latest` / `:latest-dev` のみ。バージョン固定は有償プラン
- ランタイム版はシェルなし。ビルドは `-dev` 版で

workerd ○ 本番 ◎

H

### Docker Hardened Images

Docker 公式の堅牢化イメージ（2025 年末に無料化）

Debian 版 = glibc Alpine 版 = musl Apache 2.0

公式イメージ比で大幅減

- node・python など **いつもの公式イメージの置き換え** として使える。1,000 種以上
- シェル・パッケージ管理を除去、SBOM・署名付き。利用・再配布の制限なし
- Debian 版と Alpine 版がある。 **workerd 等なら Debian 版** を選ぶ
- ビルド用（開発ツール入り）とランタイム用を使い分ける前提

workerd ○ （Debian 版） 本番 ◎

U_c

### Chiseled Ubuntu

Ubuntu のパッケージを「スライス」単位で削り出した distroless

glibc apt なし シェルなし

自己完結型 .NET 向けベース ＜ 6MB（圧縮）

- .NET（Microsoft 公式の chiseled 版）・Java（ `ubuntu/jre` ）で特に定番
- Ubuntu LTS のセキュリティ更新をそのまま受けられる
- 言語の選択肢は distroless より少なめ。自作は `chisel` / Rockcraft で

.NET / Java ◎ 本番 ◎

0

### scratch

空っぽのイメージ（FROM scratch）

libc なし 何もない

0MB + 自分のバイナリ

- 最小。中身は自分の入れたファイルだけ
- Go（ `CGO_ENABLED=0` ）や Rust（musl ターゲット）の静的バイナリと好相性
- 動的リンクのバイナリは一切動かない。CA 証明書・タイムゾーンも自分でコピーが必要

workerd ✕ 静的バイナリ ◎

## 本番向けの「まっさら」イメージ

本番コンテナに必要なのは **アプリと、それが読むライブラリと証明書だけ** 。シェルや apt は「侵入されたときの道具」になるので、最初から入れない、という考え方。

### 何が入っているか（左ほど多い → 右ほどまっさら）

|  | フル | slim | alpine | distroless :debug | distroless base / cc | Chainguard DHI など | distroless static | scratch |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| コンパイラ (gcc) | ● | − | − | − | − | − -dev 版のみ | − | − |
| パッケージ管理 | apt | apt | apk | − | − | − -dev 版のみ | − | − |
| シェル | bash | bash | ash | busybox | − | − | − | − |
| libc | glibc | glibc | musl | glibc | glibc | glibc* | − | − |
| OpenSSL | ● | ● | ● | ● | ● nossl 版は無し | ● | − | − |
| CA 証明書 | ● | ● | ● | ● | ● | ● | ● | 自分で COPY |
| tzdata / passwd | ● | ● | 一部 | ● | ● | ● | ● | 自分で COPY |
| 既定ユーザー | root | root | root | root nonroot 版あり | root nonroot 版あり | nonroot | root nonroot 版あり | − |

* DHI の Alpine 版は musl。Chainguard（Wolfi）は glibc。

### distroless の入れ子構造

言語別 `nodejs24` / `python3` / `java21` … ランタイム本体

`cc` … + libgcc・libstdc++（C++ 製バイナリ、Rust、workerd 系）

`base` … + OpenSSL

`base-nossl` … + glibc（動的リンクの Go / C）

`static` … CA 証明書・tzdata・/etc/passwd だけ（静的バイナリ用・約 2MB）

名前は `gcr.io/distroless/<種類>-debian13` 。各イメージに `:latest` / `:nonroot` / `:debug` （busybox 入り）/ `:debug-nonroot` のタグがある。「自分のバイナリが何にリンクしているか」で一番内側から選ぶ。

### マルチステージで「太く作って、細く出す」

（図: ビルドステージ / node:24-trixie / golang / *-dev / gcc・make・npm・git・シェル / devDependencies・キャッシュ / 成果物 / COPY --from=build / それ以外は捨てる / ランタイムステージ / distroless / chainguard / ＋ libc・証明書だけ → https://memo.taka1156.site/docker-images.html#minimal）

### シェルが無いのにどうデバッグする？

| 方法 | やり方 | 向いている場面 |
| --- | --- | --- |
| `:debug` タグ | 一時的に `...-debian13:debug` に差し替え、 `--entrypoint=sh` | ローカル・ステージング |
| エフェメラルコンテナ | `kubectl debug -it POD --image=busybox --target=app` | 本番 Kubernetes。本体イメージは触らない |
| Docker Debug | `docker debug CONTAINER` （ツール入りのシェルを外から差し込む） | Docker Desktop 環境 |
| ログとメトリクス | そもそも「中に入らない」運用にする | 本番の基本 |

## glibc・musl・ABI の違い

ABI とは

glibc vs musl

なぜ workerd は動かない？

**API** は「ソースコードで呼べる関数の約束」、 **ABI (Application Binary Interface)** は「 **コンパイル済みバイナリ同士** の約束」。関数のシンボル名、引数の渡し方、構造体のレイアウト、どのローダーで起動するか、まで含む。

（図: あなたのアプリ（コンパイル済みバイナリ） / printf() や getaddrinfo() を呼ぶ / ↕ libc の ABI ← ここが glibc と musl で違う / glibc / ld-linux-x86-64.so.2 / memcpy@GLIBC_2.14 / musl / ld-musl-x86_64.so.1 / シンボルのバージョン管理なし / ↕ カーネルの ABI（システムコール）← 全イメージ共通・極めて安定 / Linux カーネル（ホスト） / read / write / clone / mmap … → https://memo.taka1156.site/docker-images.html#libc）

ソース（API）レベルでは glibc も musl もほぼ同じ C 標準関数を提供するので、 **ソースから再ビルドすれば** どちらでも動くことが多い。困るのは「glibc 向けにビルド済みのバイナリ」を musl 環境に持ち込むとき。

| 観点 | glibc | musl |
| --- | --- | --- |
| 採用ディストロ | Debian, Ubuntu, RHEL, distroless など大多数 | Alpine, Void (musl 版) など |
| 設計思想 | 高機能・互換性重視・GNU 拡張多数 | 小さく単純・標準準拠を厳格に |
| 動的ローダー | `/lib64/ld-linux-x86-64.so.2` | `/lib/ld-musl-x86_64.so.1` |
| シンボルのバージョン | あり（ `GLIBC_2.34` など）。 古い glibc では新しい glibc 向けバイナリが動かない | なし |
| 静的リンク | 非推奨（NSS などで問題） | 得意。単一バイナリ配布に向く |
| malloc 性能 | マルチスレッドで速い | 遅めと言われがち（1.2.1 で入った mallocng は堅牢性と省メモリ重視で、速さが目的ではない）。jemalloc や mimalloc に差し替えて回避されることも |
| スレッドの既定スタック | 8MB 程度（ulimit 依存） | 128KB と小さい → 深い再帰でクラッシュすることがある |
| DNS 解決 | NSS / `/etc/nsswitch.conf` に従う | 独自実装。昔は TCP フォールバックなし（1.2.4 で対応）、search の扱いに差 |
| ロケール / iconv | 充実 | 最小限 |
| Python wheel | `manylinux` | `musllinux` （無いパッケージはソースビルド） |
| Node ネイティブ | `linux-x64-gnu` | `linux-x64-musl` （用意されていないパッケージあり） |

npm の optionalDependencies 名や Rust のターゲット名（ `x86_64-unknown-linux-gnu` / `-musl` ）に gnu / musl が入っているのは、まさにこの ABI の違いのため。

workerd（Cloudflare Workers のランタイム、 `wrangler dev` の中身）は npm で **glibc にリンク済みのバイナリ** として配られている。Alpine に持ち込むと:

```
$ npx wrangler dev
exec .../workerd: no such file or directory   ← ファイルはあるのに！
```

1. カーネルが ELF ヘッダを読み、指定のローダー `/lib64/ld-linux-x86-64.so.2` を探す
2. Alpine にはそのファイルが無い（あるのは `ld-musl` ）
3. 「ローダーが無い」ことが `ENOENT` = no such file or directory として返る

確認方法：

```
$ file node_modules/@cloudflare/workerd-linux-64/bin/workerd
... interpreter /lib64/ld-linux-x86-64.so.2 ...   ← glibc 向け
$ ldd ./some-binary                                  ← 足りない .so が出る
```

`apk add gcompat` （glibc 互換の薄いシム）で動く場合もあるが、V8 を抱える workerd のような大きなバイナリでは不完全。 **素直に `node:*-slim` を使う** のが正解。また glibc は新しい方向にしか互換が無いので、 **古い Debian（bullseye など）だと glibc が古すぎて動かない** こともある点にも注意。

## Dockerfile の定番パターン

Node + workerd

Go → distroless

Node → alpine

Node → distroless

```
# ビルドは Debian、本番は distroless の Node（シェルなし・非 root）
FROM node:24-trixie AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .

FROM gcr.io/distroless/nodejs24-debian13:nonroot
WORKDIR /app
COPY --from=build /app /app
# ENTRYPOINT が node なのでファイル名だけ渡す
CMD ["server.js"]
```

```
# glibc 必須なので slim。OS 世代はタグで固定する
FROM node:24-trixie-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npx", "wrangler", "dev", "--ip", "0.0.0.0"]
```

```
# ビルドはフル版、実行は distroless で最小に
FROM golang:1.27-trixie AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /app ./cmd/server

FROM gcr.io/distroless/static-debian13
COPY --from=build /app /app
ENTRYPOINT ["/app"]
```

```
# 純 JS（ネイティブ依存なし）なら alpine でも OK
FROM node:24-alpine3.24
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
CMD ["node", "server.js"]
# ネイティブ依存を足すときは linux-x64-musl 版があるか先に確認
```

（元のページで操作できます → https://memo.taka1156.site/docker-images.html#patterns）

## よくある誤解

✗ 誤解: Alpine は軽いから実行も速い

✓ 正しくは: 速いのは pull と起動前の転送だけ。実行時は malloc やソースビルドの影響でむしろ遅いことがある。

✗ 誤解: slim と alpine は同じようなもの

✓ 正しくは: slim は「Debian（glibc）のダイエット版」、alpine は「別の OS（musl）」。互換性がまったく違う。

✗ 誤解: `node:24` と書けば中身はずっと同じ

✓ 正しくは: OS 部分を省略すると Debian の世代交代（bookworm → trixie）で glibc ごと変わる。本番では `-trixie-slim` まで書いて固定する。

✗ 誤解: distroless = OS が入っていない

✓ 正しくは: Debian 由来の glibc・証明書・tzdata は入っている。無いのはシェルとパッケージ管理。完全に空なのは scratch。

✗ 誤解: まっさらイメージなら脆弱性ゼロで放置できる

✓ 正しくは: 中身が少ないので件数は激減するが、libc や OpenSSL の更新は来る。定期的に再ビルドして取り込む前提。

✗ 誤解: Alpine はカーネルが違うから動かない

✓ 正しくは: カーネルはホストのものを共有。動かない原因は libc（ABI）とローダーの違い。
