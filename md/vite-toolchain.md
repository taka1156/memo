<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Vite ツールチェーン図解

> Vite 8 を支える Rolldown・Oxc・Lightning CSS と、Vitest・Oxlint・Oxfmt を束ねる Vite+ の構成を図解。

- URL: https://memo.taka1156.site/vite-toolchain.html
- タグ: JavaScript, 開発ツール
- 日付: 2026-11-01

---

# Vite / Rolldown / Oxc / Lightning CSS

Vite 8 を支える Rust 製ツールチェーンの役割分担と、Vitest・Oxlint・Oxfmt まで束ねる Vite+

**ざっくり言うと**

- **Vite** は司令塔（開発サーバー・HMR・プラグイン・設定）。実作業は下の層に任せる。
- **Rolldown** がバンドラー、 **Oxc** が JS/TS の解析・変換・圧縮、 **Lightning CSS** が CSS の変換・圧縮。どれも Rust 製。
- Vite 8（2026-03）で、従来の「開発は esbuild／本番は Rollup」の二本立てが Rolldown に一本化された。さらに **Vite+** （1.0）が Vitest・Oxlint・Oxfmt まで `vp` コマンドと `vite.config.ts` 1 枚に統合している。

## 全体像：誰が何をしているか

Vite ビルドツール（司令塔）

dev サーバー HMR プラグイン API vite.config フレームワーク連携

▼ 呼び出す

Rolldown バンドラー

依存グラフ構築 Tree shaking チャンク分割 Rollup 互換プラグイン

Lightning CSS CSS 処理系

CSS 解析 圧縮 (minify) ベンダープレフィックス ネスト等を古いブラウザー向けに変換（トランスパイル） CSS Modules

▼ Rolldown が言語処理を委託

Oxc JavaScript Oxidation Compiler（部品集）

Parser Resolver Transformer（TS/JSX 除去・構文変換） Minifier Oxlint Oxfmt

開発元：Vite・Rolldown・Oxc は VoidZero（Evan You の会社）が中心。Lightning CSS は Parcel チームの Devon Govett 作で、別プロジェクト。

## ビルドの流れ（ `vite build` ）

（図: .ts .tsx / .js .vue … / .css / import された CSS / Rolldown / 解析・解決 / Oxc parser / + resolver / 変換 / Oxc / transformer / 結合・分割 / tree shaking / chunking / 圧縮 / minifier / 前処理（任意） / PostCSS / Sass / 変換・圧縮 / Lightning CSS / dist/ / .js .css / 緑枠 = Oxc の部品 ／ 青枠 = Rolldown 本体 ／ 桃枠 = Lightning CSS → https://memo.taka1156.site/vite-toolchain.html#build-flow）

dev サーバーでも同じ部品が使われる（ファイルを個別に変換して配信）。将来の「Full Bundle Mode」では dev でも Rolldown でバンドルする方向で、Vite 8 時点では実験的機能。

## Vite 7 → Vite 8 で何が変わったか

### Vite 7 まで 二本立て

Vite

esbuild

dev の変換・依存事前バンドル（Go 製）

Rollup

本番バンドル（JS 製）

CSS 圧縮

esbuild（Lightning CSS は任意の追加依存）

dev と本番で処理系が違うため、挙動のズレや二重の設定が起きやすかった。

### Vite 8 一本化

Vite

Rolldown

dev の依存事前バンドルも本番ビルドも

Oxc

TS/JSX 変換・JS 圧縮

Lightning CSS

通常依存に昇格、CSS 圧縮を担当

既存の `esbuild` / `rollupOptions` 設定は互換レイヤーで自動変換される。

## Vite+：テスト・リント・整形まで統合

同じ土台（Vite のパイプライン、Rolldown、Oxc）の上に **Vitest** ・ **Oxlint** ・ **Oxfmt** が載っている。これを 1 つの CLI `vp` と 1 つの設定ファイルにまとめたのが **Vite+** （MIT、2026-09 時点で 1.0）。

（図: Vite+ （vp） / vp check = lint + fmt + 型チェック / vp dev/build / vp test / vp pack / vp lint / vp fmt / Vite / dev サーバー / 本番ビルド / Vitest / テスト / Jest 互換 API / tsdown / ライブラリ用 / ビルド / Oxlint / リンター / 型: tsgolint / Oxfmt / フォーマッター / Prettier 互換 / Vite のプラグイン・変換処理 / Rolldown / Oxc / parser · transformer · minifier · resolver（全員の共通部品） / vite.config.ts 1 枚に設定を集約 / server · build · test · pack · lint · fmt · run · staged / Oxc の / パーサーを / 直接使う → https://memo.taka1156.site/vite-toolchain.html#vite-plus）

ほかに `vp create` （雛形作成）、 `vp run` （モノレポのタスク実行＋キャッシュ）、Node.js とパッケージマネージャーの管理も担う。

### それぞれ Vite とどうつながっているか

- `Vitest` Vite の **設定・プラグイン・変換処理をそのまま再利用** してテストを実行する。 `vite.config.ts` の `resolve.alias` や React／Vue プラグインがテストにも効くので、二重設定がいらない。Vite+ なしでも単体で使える。
- `Oxlint` ESLint の代替。Oxc のパーサーで動くので高速。型を使うルールは tsgolint（TypeScript の Go 移植版を利用）が担当。単体なら `.oxlintrc.json` 、Vite+ では `vite.config.ts` の `lint` に書く。
- `Oxfmt` Prettier 互換のフォーマッター。JS/TS に加え CSS・JSON・YAML なども整形。単体なら独自の設定ファイル、Vite+ では `fmt` に書く。
- `tsdown` Rolldown ベースのライブラリ向けビルドツール（型定義 .d.ts も出力）。アプリは `vp build` 、npm に公開するパッケージは `vp pack` 。

個別に使う

Vite+ で使う

```
# それぞれインストールして、それぞれ設定
npm i -D vite vitest oxlint oxfmt

vite            # dev サーバー   … vite.config.ts
vitest          # テスト         … vite.config.ts を共有
oxlint          # リント         … .oxlintrc.json
oxfmt           # 整形           … 独自の設定ファイル
```

Vite と Vitest はもともと設定を共有できる。Oxlint／Oxfmt は Vite と無関係に、どんなプロジェクトでも使える。

```
// vite.config.ts
import { defineConfig } from 'vite-plus'

export default defineConfig({
  server: { port: 5173 },          // Vite
  test:   { environment: 'jsdom' }, // Vitest
  lint:   { options: { typeAware: true, typeCheck: true } }, // Oxlint + tsgolint
  fmt:    {},                       // Oxfmt
})
```

```
vp dev      vp build     vp test
vp check    # Oxfmt → Oxlint → 型チェック をまとめて実行
```

（元のページで操作できます → https://memo.taka1156.site/vite-toolchain.html#vite-plus）

## ツール比較

一覧表

速さの目安

設定例

| ツール | 種類 | 担当 | 置き換えた／比べられる相手 | 単体で使える？ |
| --- | --- | --- | --- | --- |
| Vite | ビルドツール | dev サーバー・HMR・プラグイン・全体の段取り | webpack, Parcel | — |
| Rolldown | バンドラー | モジュールを束ねてチャンクを出力 | Rollup, esbuild | 使える（1.0：2026-05） |
| Oxc | JS/TS ツール群 | パース・解決・変換・圧縮、リンター・フォーマッター | Babel, SWC, Terser, ESLint, Prettier | 使える（Oxlint など） |
| Lightning CSS | CSS 処理系 | CSS のパース・変換・圧縮・プレフィックス | cssnano, Autoprefixer, postcss-preset-env | 使える |
| Vitest | テストランナー | Vite のパイプラインでテスト実行 | Jest | 使える（5：2026-09） |
| Oxlint | リンター | 静的解析（型対応ルールは tsgolint） | ESLint, typescript-eslint | 使える |
| Oxfmt | フォーマッター | コード整形 | Prettier | 使える |
| Vite+ | 統合 CLI | 上の全部を `vp` と設定 1 枚に束ねる | 個別ツールの寄せ集め | —（1.0：2026-09 時点） |

公式発表の数字（環境で変わるので目安として）：

- Rolldown は Rollup より **10〜30 倍** 速く、esbuild と同程度。
- 導入事例：Linear の本番ビルド 46 秒 → 6 秒、Ramp で 57%短縮、Beehiiv で 64%短縮。
- 代わりに Vite 8 のインストールサイズは約 15MB 増（Lightning CSS 分が約 10MB）。

Vite 8 では基本的に設定不要。意図的に切り替える場合の例：

```
// vite.config.ts
export default defineConfig({
  css: {
    // CSS の変換を PostCSS ではなく Lightning CSS に任せる（任意）
    transformer: 'lightningcss',
  },
  build: {
    cssMinify: 'lightningcss',
    // rollupOptions は互換のため残っているが、Rolldown 向けの設定に移行していく
  },
})
```

Oxc は Vite／Rolldown の内部部品として動くので、普段は直接設定しない。リンターとして使うなら `npx oxlint` で単体実行できる。

（元のページで操作できます → https://memo.taka1156.site/vite-toolchain.html#tools）

## よくある誤解

✗ 誤解: Rolldown は Vite の新しい名前

✓ 正しくは: Vite はそのまま。中で使うバンドラーが Rollup／esbuild から Rolldown に入れ替わっただけ。

✗ 誤解: Oxc はリンター（Oxlint）のこと

✓ 正しくは: Oxlint は Oxc の一部。本体はパーサー・変換器・圧縮器などの部品集で、Rolldown の言語処理を支えている。

✗ 誤解: Lightning CSS が入ったので PostCSS は不要

✓ 正しくは: Vite 8 で Lightning CSS が担当するのは主に CSS 圧縮。

css.transformer

の既定は PostCSS のままで、Tailwind などの PostCSS プラグインもそのまま動く。

✗ 誤解: Oxlint・Oxfmt・Vitest を使うには Vite+ が必須

✓ 正しくは: どれも単体で使える。Vite+ は「まとめて入れて、設定を 1 枚にする」ための選択肢。Oxlint／Oxfmt は Vite を使っていないプロジェクトでも動く。

✗ 誤解: Oxlint が入れば ESLint のプラグインは全部捨てる

✓ 正しくは: ネイティブルールに加えて ESLint 互換の JS プラグイン機構（現時点では alpha）がある。ただし Vue／Svelte テンプレートのような独自パーサーが必要なプラグインはまだ対応していないので、移行前に対応状況を確認する。

✗ 誤解: Rollup プラグインはもう使えない

✓ 正しくは: Rolldown は Rollup 互換のプラグイン API を持つので、多くの Vite／Rollup プラグインはそのまま動く。
