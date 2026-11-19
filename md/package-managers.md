<!-- scripts/memo.py build が自動生成。手で編集しない -->

# パッケージマネージャとロックファイル

> npm・pnpm・uv・pip・Cargo・Go modules を並べて、マニフェスト・ロックファイル・キャッシュの 3 層、版の範囲の書き方、依存がぶつかったときの解決（複数版の共存・単一版・最小バージョン選択）、CI で固定して入れるコマンドを比べる。

- URL: https://memo.taka1156.site/package-managers.html
- タグ: 開発ツール, 言語
- 日付: 2026-11-19

---

npm・pnpm・uv・Cargo・Go modules を並べて見る。違うのは「依存がぶつかったときにどう決めるか」

**ざっくり言うと**

- どの言語のパッケージマネージャも、マニフェスト（欲しい範囲）・ロックファイル（実際の版）・キャッシュの 3 層でできている。
- 大きく違うのは依存がぶつかったときで、npm は複数版を並べ、Python は 1 つに絞り、Go は全員の要求を満たす最も古い版（下限のうち最大）を選ぶ。
- アプリはロックファイルをコミットし、CI では「ロックファイルと食い違ったら失敗する」コマンドで入れる。

## 3 つの層

### マニフェスト

人が書く。「この範囲なら動く」

- `package.json`
- `pyproject.toml`
- `Cargo.toml`
- `go.mod`

### ロックファイル

ツールが書く。「実際にこの版を入れた」＋ハッシュ

- `package-lock.json` ・ `pnpm-lock.yaml`
- `uv.lock` ・ `poetry.lock`
- `Cargo.lock`
- `go.sum` （ハッシュだけ）

### キャッシュ・ストア

PC に 1 つ。ダウンロード済みの実体

- npm: `~/.npm` からコピー
- pnpm・uv: 共通の置き場からリンク
- Cargo: `~/.cargo/registry`
- Go: `$GOPATH/pkg/mod` （読み取り専用）

マニフェストの範囲（ `^1.2.0` など）だけだと、入る版が日によって変わります。 **解決** （resolution: 範囲を満たす具体的な版の組み合わせを決める作業）の結果をロックファイルに書き残し、次からはそれをそのまま使うことで、開発者・CI・本番で同じものが入ります。JavaScript の `node_modules` の作り方（npm の平らな並べ方と pnpm のリンク）は [JS のモジュールと依存管理](https://memo.taka1156.site/md/js-modules.md) にあります。

## 版の範囲の書き方

多くのエコシステムがセマンティック バージョニング（SemVer: `メジャー.マイナー.パッチ` 。メジャーが上がると互換性が壊れる）を前提に、「互換の範囲なら上がってよい」と書きます。書き方と既定の意味がエコシステムで少しずつ違います。

| やりたいこと | npm | Cargo | Python（PEP 440） | Go |
| --- | --- | --- | --- | --- |
| 1.2.3 以上・2 未満 | `^1.2.3` | `"1.2.3"` （何も付けないとこの意味） | `>=1.2.3,<2` | `require … v1.2.3` （下限だけ書く） |
| 1.2.3 以上・1.3 未満 | `~1.2.3` | `"~1.2.3"` | `~=1.2.3` | — |
| 1.2 以上・2 未満 | `^1.2` | `"1.2"` | `~=1.2` | — |
| ちょうどこの版 | `1.2.3` | `"=1.2.3"` | `==1.2.3` | —（下限が選ばれやすい。 解決 を参照） |

npm と Cargo では、 `0.x` の間はマイナーが上がると互換が壊れる扱いになり、 `^0.2.3` は「0.2.3 以上・0.3 未満」になる。Python の `~=` は compatible release（互換リリース）と呼ばれ、最後の桁だけを上げてよいという意味。Go では v2 以上は `example.com/lib/v2` のように **別のモジュールパス** になる。

## 依存がぶつかったときの解決

アプリが A と B に依存し、A と B がそれぞれ同じ `lib` の別の範囲を要求している場面で比べます。 `lib` は 1.2.0・1.5.0・1.9.0・2.0.0 が公開されているとします。

メジャーが同じ

メジャーが違う

（図: app / A / B / lib / 1.2 以上・2 未満 / 1.5 以上・2 未満 → https://memo.taka1156.site/package-managers.html#resolve）

| エコシステム | 入る lib | 決め方 |
| --- | --- | --- |
| npm・pnpm | 1.9.0 を 1 つ | 両方を満たす中で 最新 を選び、重複を 1 つにまとめる |
| Cargo | 1.9.0 を 1 つ | 互換の範囲（同じメジャー）は 1 つにまとめ、最新を選ぶ |
| Python（pip・uv） | 1.9.0 を 1 つ | 環境に 1 版しか置けない。両方を満たす最新を探す |
| Go | 1.5.0 | 要求された下限（1.2.0 と 1.5.0）の 大きいほう 。1.9.0 が出ていても上げない（最小バージョン選択, MVS） |

Go だけ結果が違います。最新を選ぶ方式は「今日解決すると明日と違う結果になる」のでロックファイルが要りますが、MVS は `go.mod` の下限だけで結果が 1 つに決まります。そのため Go には版を固定するためのロックファイルが無く、 `go.sum` はダウンロードした中身が改ざんされていないかを確かめるハッシュの一覧です。

（図: app / A / B / lib / 1.2 以上・2 未満 / 2.0 以上・3 未満 → https://memo.taka1156.site/package-managers.html#resolve）

| エコシステム | 結果 | しくみ・注意 |
| --- | --- | --- |
| npm・pnpm | 1.9.0 と 2.0.0 が共存 | A の下に 1.x、B の下に 2.x を置く（入れ子の `node_modules` ）。React のように 1 つだけでないと壊れる ものは `peerDependencies` で「使う側が入れたものを共有する」と宣言する |
| Cargo | 1.9.0 と 2.0.0 が共存 | 互換でない版は別物としてビルドされる。両方の型は 別の型 なので、A が返した `lib` の値を B に渡すとコンパイルエラーになる |
| Python（pip・uv） | 解決できずエラー | 1 つの環境に同じ名前は 1 版だけ。A か B の古い版で両立する組み合わせを探し（バックトラック）、無ければ失敗する |
| Go | v1.2.0 と v2.0.0 が共存 | v2 は `lib/v2` という別のモジュールなので、そもそもぶつからない。v1 側は A の下限 v1.2.0 がそのまま選ばれる（MVS） |

緑は共存して動く、赤はインストールの時点で失敗するエコシステムです。共存できるほうが楽に見えますが、同じライブラリが 2 つ入ると、サイズが増え、グローバルな状態（シングルトン）や型が分かれて実行時・コンパイル時の問題になります。1 つに絞る Python は、ぶつかりを **インストールの時点で必ず知らせる** とも言えます。

## ロックファイルと CI でのコマンド

| ツール | ロックファイル | CI で固定して入れる | 依存を上げる |
| --- | --- | --- | --- |
| npm | `package-lock.json` | `npm ci` | `npm update` ・ `npm install lib@latest` |
| pnpm | `pnpm-lock.yaml` | `pnpm install --frozen-lockfile` （CI では既定） | `pnpm update` |
| Yarn（v2 以降） | `yarn.lock` | `yarn install --immutable` | `yarn up lib` |
| Bun | `bun.lock` | `bun install --frozen-lockfile` | `bun update` |
| uv | `uv.lock` | `uv sync --locked` | `uv lock --upgrade` ・ `--upgrade-package lib` |
| Poetry | `poetry.lock` | `poetry check --lock` のあと `poetry install` | `poetry update` |
| pip | 版を固定した `requirements.txt` （pip-tools などで作る） | `pip install --require-hashes -r requirements.txt` | 固定ファイルを作り直す |
| Cargo | `Cargo.lock` | `cargo build --locked` | `cargo update` |
| Go | `go.sum` （版は `go.mod` ） | そのまま `go build` （ `go.mod` の書き換えが要ると失敗するのが既定） | `go get -u` ・ `go get lib@v1.9.0` |

uv の `--locked` は「ロックファイルが古ければ失敗」、 `--frozen` は「古いかどうか確かめずにそのまま使う」。Python の共通のロックファイル形式として `pylock.toml` （PEP 751）も決まり、pip は `pip lock` での書き出しと `pip install -r pylock.toml` でのインストールに（実験的に）対応した。uv も読み書きできるが、主に使うのは `uv.lock` 。

### コミットするか

1. **アプリ・サービス** 必ずコミットする。入れたら動いた組み合わせを、そのまま本番に届けるため。
2. **ライブラリ** コミットしてよい（Cargo も 2023 年に、ライブラリでもコミットを判断の出発点として勧め、 `cargo new` が `Cargo.lock` を無視しないように変えた）。ただし、ライブラリのロックファイルは使う側には効かない。使う側では、マニフェストの範囲をもとに、使う側のロックファイルで決め直される。
3. **衝突したら** ロックファイルを手で直さない。マニフェストの変更を取り込んでから、ツールにもう一度解決させて作り直す。

ライブラリでロックファイルをコミットしたときは、範囲の中で最新の依存でも動くかを CI で定期的に確かめると、使う側で初めて壊れるのを防げます（Dependabot などで更新を自動で出す）。

## 言語本体の版も固定する

依存を固定しても、Node.js や Python 自体の版が違うと結果が変わります。言語の版も、リポジトリのファイルに書いておきます。

| 言語 | 書く場所 | 読んで切り替えるもの |
| --- | --- | --- |
| Node.js | `.nvmrc` ・ `.node-version` 、 `package.json` の `engines` | nvm・fnm・mise など。パッケージマネージャ自体の版は `packageManager` で揃える |
| Python | `.python-version` 、 `pyproject.toml` の `requires-python` | uv（Python 本体の取得もする）・pyenv |
| Rust | `rust-toolchain.toml` | rustup が自動で切り替える |
| Go | `go.mod` の `go` ・ `toolchain` の行 | `go` コマンド自身（足りなければ新しいツールチェーンを取得する） |

## よくある誤解

✗ 誤解: ロックファイルがあれば、マニフェストの範囲はどう書いてもよい

✓ 正しくは: 範囲は「上げるときにどこまで上がってよいか」を決めます。さらにライブラリでは、使う側がその範囲をもとに解決するので、範囲が狭すぎると使う側でぶつかりやすく、広すぎると動かない版が選ばれます。

✗ 誤解: Go も npm と同じく、範囲の中の最新版を入れる

✓ 正しくは: Go は要求された下限の中で最も大きいもの（＝全員の要求を満たす最も古い版）を選びます。新しい版が出ても、 `go get -u` などで明示しない限り上がりません。

✗ 誤解: npm install と npm ci は、入るものが同じ

✓ 正しくは: `npm install` は `package.json` に合わせてロックファイルを書き換えることがあります。 `npm ci` は `node_modules` を消してロックファイルどおりに入れ、 `package.json` と食い違えば失敗します。CI では `npm ci` を使います。

✗ 誤解: Python でも依存ごとに別の版を入れれば、ぶつかりは避けられる

✓ 正しくは: 1 つの仮想環境の `site-packages` には同じ名前のパッケージを 1 版しか置けません。どうしても両立しないなら、環境を分ける（別のサービス・別の仮想環境）か、どちらかの依存を上げ下げします。

## 関連メモ

- [JS のモジュールと依存管理](https://memo.taka1156.site/md/js-modules.md) — npm・pnpm・Bun が `node_modules` をどう作るか、ワークスペース
- [サプライチェーンセキュリティ](https://memo.taka1156.site/md/supply-chain-security.md) — ロックファイル・インストールスクリプトの停止・公開直後の版を待つ設定
- [Python 学習フローと仕組み](https://memo.taka1156.site/md/python.md) ・ [Go 学習フローと仕組み](https://memo.taka1156.site/md/go.md) ・ [Rust 学習フローと仕組み](https://memo.taka1156.site/md/rust.md) — それぞれの言語でのプロジェクトの始め方
- [CI/CD と GitHub Actions](https://memo.taka1156.site/md/ci-cd.md) — 固定したインストールとキャッシュを CI に組み込む

## 参考

- [npm Docs: npm ci](https://docs.npmjs.com/cli/commands/npm-ci) ・ [node-semver](https://github.com/npm/node-semver) （範囲の書き方）
- [pnpm: pnpm install](https://pnpm.io/cli/install)
- [uv: Locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
- [Python Packaging: Version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/) ・ [PEP 751](https://peps.python.org/pep-0751/)
- [Cargo: Specifying Dependencies](https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html) ・ [Dependency Resolution](https://doc.rust-lang.org/cargo/reference/resolver.html)
- [Rust Blog: Change in Guidance on Committing Lockfiles](https://blog.rust-lang.org/2023/08/29/committing-lockfiles/)
- [Go Modules Reference](https://go.dev/ref/mod) （MVS・go.sum・toolchain）
