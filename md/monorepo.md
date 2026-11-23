<!-- scripts/memo.py build が自動生成。手で編集しない -->

# モノレポ

> 複数のアプリとパッケージを 1 つのリポジトリに置くモノレポを、ワークスペース（npm・pnpm・Cargo・uv）とタスクランナー（Turborepo・Nx）の 2 層で解説。変更の影響範囲を図で試し、タスクの順番・キャッシュ・内部パッケージの作り方・CI の注意点まで。

- URL: https://memo.taka1156.site/monorepo.html
- タグ: 開発ツール, JavaScript
- 日付: 2026-11-19

---

複数のアプリとパッケージを 1 つのリポジトリに置く。ワークスペースでつなぎ、タスクランナーで「変わったところだけ」動かす

**ざっくり言うと**

- モノレポは、複数のアプリとライブラリを 1 つのリポジトリに置き、内部のパッケージを公開せずに直接使う構成。
- パッケージマネージャのワークスペースがリンクとロックファイルを、Turborepo・Nx がタスクの順番・キャッシュ・影響範囲を受け持つ。
- 速さは依存関係の宣言が正しいことが前提で、宣言が漏れると、壊れた変更が CI をすり抜けたり、古いキャッシュが使われたりする。

## モノレポとポリレポ

アプリやライブラリごとにリポジトリを分けるのが **ポリレポ** （polyrepo）、1 つにまとめるのが **モノレポ** （monorepo）です。モノレポは「1 つの大きなアプリ（モノリス）」とは別の話で、中のアプリは別々にデプロイできます。

| 観点 | モノレポ | ポリレポ |
| --- | --- | --- |
| 共有コードの変更 | ライブラリと使う側を 1 つのプルリクエストで同時に直せる | ライブラリを公開 → 各リポジトリで版を上げる、の順に何度も回す |
| 依存の版 | ロックファイルが 1 つで、そろえやすい | リポジトリごとにばらつく |
| 設定・ツール | lint・tsconfig・CI を共通にできる | リポジトリごとに複製して、ずれていく |
| CI の時間 | 何もしないと全部を毎回ビルドして遅くなる。影響範囲とキャッシュが要る | リポジトリが小さいので自然に速い |
| 権限 | リポジトリ単位では分けられない。CODEOWNERS などでディレクトリごとにレビュー担当を決める | リポジトリごとに分けられる |

## 2 つの層：ワークスペースとタスクランナー

### ワークスペース（パッケージマネージャ）

- リポジトリ内のパッケージを互いに **リンク** する（公開しなくても import できる）
- 依存のインストールが 1 回、 **ロックファイルが 1 つ**
- 「全パッケージで `test` を実行」のような一括実行はできるが、賢くはない

### タスクランナー（Turborepo・Nx など）

- パッケージの依存関係から **実行の順番** を決め、並列に動かす
- 入力が同じタスクは **キャッシュ** から結果を戻して飛ばす
- 変更から **影響範囲** を出し、そこだけ動かす

JavaScript の `workspaces` と `workspace:*` の書き方は [JS のモジュールと依存管理](https://memo.taka1156.site/md/js-modules.md) にあります。ほかの言語もワークスペースの仕組みを持っています。

| ツール | どこに書くか | まとめてくれるもの |
| --- | --- | --- |
| npm・Yarn・Bun | ルートの `package.json` の `"workspaces"` | ロックファイル・ `node_modules` |
| pnpm | `pnpm-workspace.yaml` | ロックファイル。 `catalog:` で依存の版を 1 か所にまとめられる |
| Cargo | ルートの `Cargo.toml` の `[workspace]` | `Cargo.lock` とビルド結果の `target/` |
| uv | ルートの `pyproject.toml` の `[tool.uv.workspace]` | `uv.lock` |
| Go | 1 つのモジュールに複数のパッケージを置くのが基本。 `go.work` は手元で複数モジュールを同時に触るためのもの | Go のドキュメントは `go.work` をコミットすることを一般には勧めていない |

## 変更の影響範囲（affected）

下の図は、3 つのアプリ（上の段）が内部パッケージを使っているモノレポです。矢印は「使っている」向きです。パッケージを押すと、そこを変えたときに **ビルド・テストし直すもの** が分かります。影響は矢印を **逆向き** にたどって広がります。

utils

ui

db

web

admin

api

（図: apps/ / web / admin / api / ui / db / utils / packages/ → https://memo.taka1156.site/monorepo.html#affected）

変更した（紫の太枠） 影響を受けて動き直す（青緑の点線枠） 動かさない（キャッシュのまま）

上のボタンでパッケージを選ぶと、影響範囲が光ります。

**utils を変更** → ui・db が使っており、その先の web・admin・api もすべて動き直す。土台のパッケージの変更は全体に効くので、CI の時間がいちばん長くなる。

**ui を変更** → 使っている web・admin だけが動き直す。api・db・utils はキャッシュのまま。

**db を変更** → 使っている admin・api だけが動き直す。web は db を使っていないので動かさない。

**web を変更** → web だけ。web に依存するものは無いので、ほかは全部キャッシュのまま。

**admin を変更** → admin だけ。ui と db を使っていても、使われる側には影響しない（影響は矢印の逆向きにしか広がらない）。

**api を変更** → api だけ。admin と同じ db を使っていても、api を使う側がいなければ影響しない。

この計算は、各パッケージの `package.json` （や `Cargo.toml` ）に書いた依存関係だけを頼りにしています。 `import` しているのに依存として書いていないと、変更しても影響範囲に入らず、 **壊れた変更がテストされないまま通ります** 。

```
# Git の比較元（main など）から変わったパッケージと、それに依存するものだけ
turbo run test --affected
nx affected -t test
pnpm --filter "...[origin/main]" test   # 先頭の ... = そのパッケージに依存している側も含める
```

## タスクの順番とキャッシュ

タスクランナーには、タスク同士の関係を書きます。Turborepo なら `turbo.json` です。

```
{
  "tasks": {
    "build": {
      "dependsOn": ["^build"],          // ^ = 依存しているパッケージの build を先に
      "outputs": ["dist/**"],           // キャッシュに保存して戻すもの
      "env": ["API_URL"]               // 値が変わったら別の結果として扱う
    },
    "test": { "dependsOn": ["build"] },  // ^ なし = 同じパッケージの build を先に
    "dev":  { "cache": false, "persistent": true }
  }
}
```

1. **入力のハッシュを取る** パッケージのファイル、依存しているパッケージの結果、タスクの設定、指定した環境変数などをまとめてハッシュにする。
2. **キャッシュを探す** 同じハッシュの結果が手元かリモートキャッシュ（チーム・CI で共有する置き場）にあれば、 `outputs` のファイルとログを戻して、タスク自体は実行しない。
3. **無ければ実行して保存** 実行し、 `outputs` とログをハッシュの名前で保存する。次に同じ入力で動かす人は、手順 2 で終わる。

キャッシュが正しいのは、 **結果に効くものが全部入力に入っているとき** だけです。ビルドが読む環境変数や `.env` ファイルが入力に入っていないと、値が変わっても同じ入力と見なされ、本番用の値で作るべきところに開発用の結果が戻ってきます（Turborepo 2 の既定の strict モードでは、 `env` に書いていない環境変数はタスクからそもそも見えない）。逆に `outputs` を書き忘れると、キャッシュに当たったのに `dist/` が空のまま、ということが起きます。

## 内部パッケージの作り方

アプリから使うだけの内部パッケージは、ビルドするかどうかで 2 通りあります。

| 方式 | やること | 向いている場面 | 注意 |
| --- | --- | --- | --- |
| ソースのまま渡す （Just-in-Time Packages） | `exports` で `.ts` を直接指し、アプリ側のバンドラーにまとめてトランスパイルさせる | Vite・Next.js などのアプリからだけ使う | パッケージ単位のビルドキャッシュが効かない。使う側すべてが TypeScript を読める必要がある |
| ビルドして渡す （Compiled Packages） | `tsc` などで `dist/` に JS と型定義を出し、それを `exports` で指す | Node.js で直接動かす・数が多い・外にも公開する | 設定が増える。 `^build` の順番とキャッシュの設定が要る |

外に公開するパッケージは、版の番号と変更履歴も要ります。Changesets のように、プルリクエストごとに「どのパッケージをどれだけ上げるか」を書いておき、リリース時にまとめて版を上げて公開するツールを使うのが定番です。

## CI と運用の注意

1. **比較元の履歴を取る** 影響範囲は Git の差分で決まる。 `actions/checkout` の既定（直近 1 コミットだけ）では比較元が無いので、 `fetch-depth: 0` などで比較元のコミットまで取る。
2. **リモートキャッシュをつなぐ** CI のジョブ同士・開発者と CI でキャッシュを共有すると、誰かが一度ビルドしたものは二度とビルドしない。トークンは CI のシークレットに置く。
3. **Docker イメージは必要な分だけ** アプリ 1 つのイメージにリポジトリ全体を入れない。 `turbo prune --docker` などで、そのアプリと依存するパッケージだけを切り出してからビルドする。
4. **担当をディレクトリで決める** `CODEOWNERS` で `packages/ui/` はデザインシステムのチーム、のようにレビュー担当を割り当てる。

## よくある誤解

✗ 誤解: モノレポにすると、アプリも 1 つにまとめてデプロイすることになる

✓ 正しくは: モノレポはリポジトリの置き方で、デプロイの単位とは別です。web・admin・api はそれぞれ別のタイミングで、別の場所にデプロイできます。

✗ 誤解: Turborepo や Nx を入れれば、設定しなくても速くなる

✓ 正しくは: 速くなるのは、依存関係・ `outputs` ・ `env` を正しく宣言したときだけです。宣言が漏れると、必要なタスクが飛ばされたり、古い結果がキャッシュから戻ったりします。

✗ 誤解: モノレポなら、全パッケージの依存の版が自然にそろう

✓ 正しくは: ロックファイルは 1 つでも、パッケージごとの `package.json` に別の範囲を書けば、同じライブラリの複数版が入ります。そろえたいなら pnpm の `catalog:` のように版を 1 か所に書く仕組みや、版のずれを検査するツールを使います。

## 関連メモ

- [JS のモジュールと依存管理](https://memo.taka1156.site/md/js-modules.md) — `workspaces` と `workspace:*` 、 `exports` の書き方
- [パッケージマネージャとロックファイル](https://memo.taka1156.site/md/package-managers.md) — ワークスペース全体で 1 つになるロックファイルと依存の解決
- [CI/CD と GitHub Actions](https://memo.taka1156.site/md/ci-cd.md) — 影響範囲だけを動かすジョブとキャッシュの置き場
- [グラフ探索と最短経路](https://memo.taka1156.site/md/graph-algorithms.md) — タスクの順番はトポロジカルソート、影響範囲は逆向きの探索

## 参考

- [Turborepo Docs](https://turborepo.dev/docs) （tasks・caching・ `--affected` ・ `prune` ・internal packages）
- [Nx Docs](https://nx.dev/docs) （affected・task pipeline）
- [pnpm: Workspace](https://pnpm.io/workspaces) ・ [Filtering](https://pnpm.io/filtering) ・ [Catalogs](https://pnpm.io/catalogs)
- [npm Docs: workspaces](https://docs.npmjs.com/cli/using-npm/workspaces)
- [Cargo: Workspaces](https://doc.rust-lang.org/cargo/reference/workspaces.html)
- [uv: Using workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/)
- [Go Modules Reference: Workspaces](https://go.dev/ref/mod#workspaces) ・ [Proposal: Multi-Module Workspaces](https://go.googlesource.com/proposal/+/master/design/45713-workspace.md) （go.work をコミットしない方針）
- [Changesets](https://github.com/changesets/changesets)
