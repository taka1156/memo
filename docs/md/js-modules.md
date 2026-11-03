<!-- scripts/memo.py build が自動生成。手で編集しない -->

# JS のモジュールと依存管理

> ESM と CommonJS の違い、package.json の exports と条件による解決（動くデモつき）、import maps、npm・pnpm・Bun のインストール方式とロックファイル、モノレポのワークスペースを図解。

- URL: https://memo.taka1156.site/js-modules.html
- タグ: JavaScript, 開発ツール
- 日付: 2026-11-03

---

「どのファイルが読み込まれるか」は、書き方・実行環境・package.json の 3 つで決まる

**ざっくり言うと**

- JS のモジュールは 2 種類。標準の **ESM** （ `import` / `export` ）と、Node.js 由来の **CommonJS** （ `require` / `module.exports` ）。新しく書くなら ESM。
- パッケージのどのファイルが使われるかは、package.json の ** `exports` ** に書いた条件（ `import` ・ `require` ・ `browser` ・ `types` など）を **上から順に** 見て、最初に合ったもので決まる。
- npm・pnpm・Bun は「 `node_modules` をどう作るか」が違う。どれを使っても **ロックファイルをコミット** し、CI では `ci` / `--frozen-lockfile` で入れる。

## ESM と CommonJS

ESM（標準）

```
import { readFile } from 'node:fs/promises';
export function load(p) { … }
export default load;
```

- **静的** ：import はファイルの先頭で決まり、実行前に依存関係がわかる → 未使用コードを削れる（tree shaking）
- 読み込みは **非同期** 。トップレベル `await` が使える
- ブラウザ・Node.js・Deno・Bun・Workers の **どこでも動く**
- import は **生きた参照** （元のモジュールで値が変わると見える）

CommonJS（Node.js 由来）

```
const { readFile } = require('node:fs/promises');
module.exports = { load };
```

- **動的** ：require はただの関数呼び出し。条件分岐の中でも呼べる
- 読み込みは **同期** 。トップレベル await は使えない
- ブラウザではそのまま動かない（バンドラーが変換する）
- require した時点の値の **コピー** （オブジェクトなら同じ参照）

| Node.js がどちらとして読むか | 判定 |
| --- | --- |
| `.mjs` / `.cjs` | 拡張子で決まる（ESM / CommonJS）。package.json より優先 |
| `.js` | いちばん近い package.json の `"type"` 。 `"module"` なら ESM、 `"commonjs"` なら CommonJS。 `"type"` がないときは CommonJS として読み、ESM の構文で失敗したら ESM として読み直す（Node.js 22.7 以降の自動判定。判定のコストを避けるため `"type"` は明示する） |
| ESM から CommonJS を import | できる。 `module.exports` が default として見える |
| CommonJS から ESM を require | Node.js 22.12 以降（20 系は 20.19 以降）では、トップレベル await を使っていない ESM なら require できる。それより古い版では `await import()` が必要 |

ESM では `__dirname` や `require` がない。代わりに `import.meta.dirname` ・ `import.meta.url` 、JSON は `import data from './a.json' with { type: 'json' }` 。相対パスは **拡張子まで書く** （ `'./util.js'` ）のが Node.js の ESM の決まり。TypeScript でも出力後の `.js` を書く。

## package.json の exports：どのファイルが選ばれるか

同じ `import 'my-lib'` でも、実行環境によって読まれるファイルが変わる。環境を選ぶと、どの条件に合ったかが色で出る。

Node.js で import

Node.js で require

Vite（ブラウザ向け）

TypeScript の型チェック

Cloudflare Workers

**順番が意味を持つ** 。上から見て最初に合った条件が使われるので、 `types` は先頭、 `default` は最後に置く。 `exports` を書くと、そこに **書いていないパスは外から import できなくなる** （ `my-lib/src/internal.js` などを隠せる）。

```
// サブパスも公開するときの書き方
"exports": {
  ".":         { "types": "./dist/index.d.ts", "import": "./dist/index.js", "require": "./dist/index.cjs" },
  "./react":   { "types": "./dist/react.d.ts", "import": "./dist/react.js" },
  "./package.json": "./package.json"
}
```

同じパッケージを ESM 版と CJS 版の 2 つで配ると、両方が読み込まれて **状態が 2 つできる** （シングルトンが 2 個になる、 `instanceof` が外れる）事故が起きうる（デュアルパッケージハザード）。新しく作るライブラリは ESM だけにし、require(esm) に任せる選択肢も増えている。

（元のページで操作できます → https://memo.taka1156.site/js-modules.html#exports）

## import maps：ブラウザで「名前だけ」の import を解決する

ブラウザは `import { h } from 'preact'` のような **パッケージ名だけの指定（ベア指定子）を解決できない** 。バンドラーがない環境では、import map で名前と URL の対応を教える。

```
<script type="importmap">
{
  "imports": {
    "preact": "https://esm.sh/preact@10",
    "app/": "/js/"
  }
}
</script>
<script type="module">
  import { h } from 'preact';        // → https://esm.sh/preact@10
  import { route } from 'app/router.js';  // → /js/router.js
</script>
```

主要ブラウザで使える。小さなサイトやプロトタイプではバンドラーなしで済む。ただし依存が多いと import の往復が段々に重なる（ウォーターフォール）ので、本番の大きなアプリはバンドルするのが今も基本。

## パッケージマネージャーの違い

npm

pnpm

Bun

node_modules/ ├── my-app が使う express/ ├── express が使う body-parser/ ← 依存の依存も「平らに」並ぶ └── …

依存の依存までなるべく **平らに** （hoisting）並べる。そのため package.json に書いていないパッケージも import できてしまう（ **幽霊依存** ）。ある日、間接依存が外れて壊れる原因になる。ロックファイルは `package-lock.json` 。

node_modules/ ├── react → .pnpm/react@19…/node_modules/react ← 直接の依存だけ見える └── .pnpm/ ← 実体。ストアからハードリンク ~/.local/share/pnpm/store ← 全プロジェクト共通の置き場

ファイルの実体は PC に 1 つだけ置き（内容で管理するストア）、各プロジェクトにはハードリンクとシンボリックリンクで見せる。 **ディスクと時間を節約** でき、 **package.json に書いたものしか import できない** ので幽霊依存が起きない。ロックファイルは `pnpm-lock.yaml` 。

Bun のランタイムに付いてくるパッケージマネージャー。npm と互換の `node_modules` を作り、インストールが速い。ロックファイルは現在テキスト形式の `bun.lock` （以前はバイナリの `bun.lockb` ）。Bun で実行しないプロジェクトでも、インストーラーとしてだけ使える。

ロックファイルの扱い

- package.json の `"^1.2.0"` は「1.x の最新」なので、日によって入るものが変わる。 **ロックファイルが実際の版を固定** する。だから **必ずコミット** する。
- CI や本番では `npm ci` / `pnpm install --frozen-lockfile` / `bun install --frozen-lockfile` 。ロックファイルと package.json が食い違っていたら **失敗させる** 。
- 1 つのリポジトリでマネージャーを混ぜない。 `package.json` の `"packageManager"` に版を書き、Corepack などで揃える（Node.js 25 以降は Corepack が同梱されないので `npm i -g corepack` で入れる）。
- インストール時に依存のスクリプト（ `postinstall` ）が走る。乗っ取られたパッケージの攻撃経路になるので、pnpm や Bun のように **許可したものだけ実行する** 設定も検討する。

（元のページで操作できます → https://memo.taka1156.site/js-modules.html#pm）

## モノレポ：ワークスペース

my-repo/ ├── package.json ← "workspaces": ["apps/*", "packages/*"]（pnpm は pnpm-workspace.yaml） ├── apps/ │ ├── web/ ← "dependencies": { "@acme/ui": "workspace:*" }（pnpm・Bun） │ └── api/ └── packages/ ├── ui/ ← name: "@acme/ui" └── config/

ワークスペースにすると、 **同じリポジトリ内のパッケージがリンクされ** 、公開しなくても `import '@acme/ui'` で使える。依存のインストールは 1 回で済み、ロックファイルも 1 つ。 `workspace:*` は pnpm・Bun（・Yarn）の書き方で「リポジトリ内のものを使う」という指定。公開時に実際の版番号へ置き換わる。 **npm はこの書き方に対応していない** （install がエラーになる）ので、 `"^1.0.0"` のような普通の版指定を書く。ワークスペース内にあればリンクされる。

パッケージが増えたら、変更のあったものだけをビルド・テストするタスクランナー（Turborepo・Nx など）を足す。内部パッケージは **ビルドせずにソースの TypeScript を直接 exports する** （アプリ側のバンドラーに任せる）と設定が軽くなる。

## よくある誤解

「"type": "module" にすれば全部 ESM になる」

そのパッケージ内の `.js` が ESM として読まれるだけ。 `.cjs` は CommonJS のまま、依存パッケージはそれぞれの package.json に従う。設定ファイル（ `eslint.config.cjs` など）が壊れることがあるので拡張子で明示する。

「main を書いておけば exports はいらない」

`main` は 1 つの入口しか表せず、条件分岐もサブパスの公開・非公開もできない。新しいパッケージは `exports` を書き、古いツール向けに `main` も残す。

「ロックファイルは衝突が面倒だから .gitignore」

入れないと、開発者・CI・本番で違う版が入り、「手元では動く」が起きる。衝突したら手で直さず、マネージャーにもう一度 install させて作り直す。

## 関連メモ

[Vite ツールチェーン](https://memo.taka1156.site/md/vite-toolchain.md) [JS ランタイム比較](https://memo.taka1156.site/md/js-runtimes.md) [TypeScript](https://memo.taka1156.site/md/typescript.md) [JS と Web 標準の決まり方](https://memo.taka1156.site/md/js-web-standards.md) [テスト戦略](https://memo.taka1156.site/md/testing-strategy.md)

## 参考

- [Node.js: ECMAScript modules](https://nodejs.org/api/esm.html)
- [Node.js: Packages（type・exports・条件）](https://nodejs.org/api/packages.html)
- [Node.js: require で ESM を読み込む](https://nodejs.org/api/modules.html#loading-ecmascript-modules-using-require)
- [MDN: import map](https://developer.mozilla.org/ja/docs/Web/HTML/Element/script/type/importmap)
- [pnpm: Motivation](https://pnpm.io/motivation)
- [Bun: Lockfile](https://bun.sh/docs/install/lockfile)
- [TypeScript: Modules Reference](https://www.typescriptlang.org/docs/handbook/modules/reference.html)
