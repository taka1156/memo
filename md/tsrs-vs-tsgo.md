<!-- scripts/memo.py build が自動生成。手で編集しない -->

# tsrs と tsgo の比較

> TypeScript のネイティブ実装 tsgo（Go）と tsrs（Rust）の仕組み・性能・使い分けを図で比較。

- URL: https://memo.taka1156.site/tsrs-vs-tsgo.html
- タグ: 言語, 開発ツール
- 日付: 2026-11-02

---

# tsrs vs tsgo

TypeScript コンパイラのネイティブ移植 2 系統 ― Go 版と Rust 版の仕組みと違い（2026 年 11 月時点）

**ざっくり言うと**

- tsgo は Microsoft 公式の Go 移植で、 **TypeScript 7 の正式な `tsc` ** 。旧 JS 版より約 10 倍速い。
- tsrs はその Go 実装を **関数単位で Rust に移植** した実験版（Oxc 傘下、Cloudflare / VoidZero ほか）。同じワーカー数で最大 8 倍速・メモリ約 70% 減と主張。
- どちらも型チェックを **省略しない** 本物のコンパイラ。違いは主に **メモリ管理（GC か所有権＋アリーナか）** と **Wasm 適性** 、そして成熟度。

## 系譜: 同じ設計を言語ごとに写している

TypeScript / JS

tsc（〜6.x）

元祖。Node.js 上で 1 スレッド実行。言語仕様の基準。

→ 忠実移植

(port)

Go ・ Microsoft

tsgo（TS 7）

Project Corsa。2025/3 発表 → 7.0 で正式版。 `typescript` パッケージそのもの。

→ 関数単位で

移植

Rust ・ Oxc

tsrs

2026/10 発表の実験版。fork ではなく、言語設計は TS チームに従う。

「書き直し (rewrite)」ではなく「移植 (port)」なので、どれも同じ構造・同じ型チェックの挙動を目指す。tsrs の最適化の一部は TS 7.1 beta に逆輸入されている。

## 共通のパイプライン

① config

tsconfig を読み対象ファイルを決定

② parse

テキスト → AST（構文木）

ファイル単位で並列

③ bind

名前とシンボル（宣言）を結びつける

並列

④ check

型を計算しエラーを出す。一番重い

checker プール

⑤ emit

.js / .d.ts / source map 出力

並列

旧 tsc は ①〜⑤ をすべて 1 スレッドで処理していた。ネイティブ版は「共有メモリ上のマルチスレッド」で ②〜⑤ を並列化するのが速さの源。 `--singleThreaded` で並列化を全部オフにできる点も両者共通。

## 仕組みの違い

tsgo の内部

tsrs の内部

メモリと Wasm

（元のページで操作できます → https://memo.taka1156.site/tsrs-vs-tsgo.html#internals）

### checker プール（既定 4 個）

import 関係をグラフとみなし、 **関係の深いファイルを同じ checker に寄せつつ負荷を均す** ように分割（FENNEL 系のグラフ分割を重み付きで応用）。ファイルの重さは構文ノード数・文字数・import 数から見積もる。

checker #1

a.ts b.ts c.ts

型キャッシュ（専用）

checker #2

d.ts e.ts

型キャッシュ（専用）

checker #3

f.ts g.ts

型キャッシュ（専用）

checker #4

h.ts i.ts j.ts

型キャッシュ（専用）

**AST・シンボル** （parse / bind 済み）は全 checker から参照される ― Go の goroutine が同じヒープを共有

- 各 checker が **独自の型キャッシュ** を持つ → 同じ型を別々に計算する重複が出る。checker を増やすと速くなるがメモリも増える。
- 診断はファイル番号の「スロット」に格納 → 処理の終わる順番に関係なく **出力は決定的** 。
- 調整用フラグ: `--checkers N` （上限 256）、モノレポ用 `--builders N` （掛け算で効く）。
- メモリ回収は Go の **GC** 任せ。

### 同じ骨格 + Rust ならではの最適化

tsgo の関数を 1 つずつ Rust に写しているので、パイプラインや checker プールの考え方は同じ。そのうえで次を足している。

checker × 16（既定例）

マシンに応じて適応的に設定。メモリを多めに使う代わりに速い

ポインタ圧縮

参照をアリーナ内の小さな番号（ハンドル）にして、参照だらけの構造を縮める。番号→アドレス変換のコストとのトレードオフ

葉ファイルの早期解放

もう誰も参照しない「葉」のファイルの構文データを途中で捨てる（import・宣言マージ等の条件付き）

PGO ビルド

実行プロファイルを使った最適化でリリースバイナリをビルド

- 独自フラグ: `--maxMemory` （目標値）、 `--checkerCostCache` 、Go と割り当てを揃える `--checkerAssignment go` など。
- メモリは所有権 + アリーナで管理し、 **GC が無い** 。
- tsc-rs（ping.gg 発）と統合予定。LSP や content mapper（Vue/Svelte 等）を統合版で整える計画。

#### tsgo: GC 付きヒープ

Node Node Symbol Type Node

GC が定期的に走査して回収

- 書きやすく移植しやすい（JS の構造に近い）
- Wasm にするとランタイムと GC も同梱する必要がある

#### tsrs: 所有権 + アリーナ

arena[0] Node [1] Node [2] Type

leaf.ts の AST ← 不要になった時点で解放

- 参照は小さな番号、寿命はコンパイル時に確定
- Wasm でホスト（JS）とメモリを直接やり取りしやすい

### Wasm 版 `@tsrs/wasm` の制約

- Node / ブラウザで動く。仮想ファイルシステムを渡し、標準ライブラリの型定義を同梱。
- **シングルスレッド** 。 `--watch` ・LSP・API サーバーモードは無し。
- 線形メモリ上限 4 GiB。深い再帰型でスタックを使い切ることがある。インクリメンタル状態は呼び出し側で持ち回す。

## 速さの比較（ベンダー計測）

型チェック時間。 **両方 checker 4 個** に揃えた条件（16 vCPU / 63 GB RAM）。短いほど速い。

VS Code

tsgo

10.94s

tsrs

2.21s

Supabase Studio

tsgo

7.24s

tsrs

1.31s

webpack

tsgo

1.46s

tsrs

0.29s

tsrs 側が出した初期の数字で、ワークロード次第。参考までに tsgo 自体は旧 JS 版 tsc 比で 8〜12 倍（VS Code: 125.7s → 10.6s）。TS 7.1 beta は 7.0 比で最大 2.5 倍速くなっており、差は縮みつつある。

## 比較表

| 項目 | tsgo（TypeScript 7） | tsrs |
| --- | --- | --- |
| 開発 | Microsoft（TypeScript チーム） | Oxc 傘下。Cloudflare・VoidZero・Owner.com、TS チームと協力 |
| 言語 | Go | Rust |
| 移植元 | JS 版 tsc | Go 版 tsgo（関数単位） |
| 位置づけ | 正式版。 `npm i -D typescript` で入る | 実験版。 `npm i -D tsrs` |
| メモリ管理 | GC | 所有権 + アリーナ、ポインタ圧縮、早期解放 |
| checker 既定数 | 4 | マシン適応（ベンチ例 16） |
| LSP | あり（マルチスレッド） | `--lsp` はあるが既知の欠落あり |
| プログラム API | 7.0 は安定 API なし → 7.1 で予定 | 統合版で整備予定 |
| Wasm | 不向き（GC 同梱） | `@tsrs/wasm` あり（単一スレッド） |
| 互換性 | 基準そのもの（差分は CHANGES.md） | 診断の順序・位置などに差異あり。差は「バグ」扱い。目標は 7.1 完全準拠 |

## よくある誤解

tsrs は TypeScript の fork（別言語）

fork ではない。言語設計は TypeScript チームが握り、tsrs は upstream に追従する実装の 1 つ。

「8 倍速」は旧 tsc と比べた数字

比較相手は **TypeScript 7.0（tsgo）** で、checker 数を揃えた条件。旧 tsc 比の「約 10 倍」は tsgo の話。

swc / esbuild / Biome の仲間

それらは型を剥がすだけで型チェックはしない。tsgo も tsrs も **型チェックまでやる本物の tsc** 。

Wasm 版ならブラウザでも本番同等に動く

Wasm 版はシングルスレッドで watch / LSP なし。ネイティブ版のベンチ数値は当てはまらない。

TS 7 にすれば typescript-eslint や Vue ツールもすぐ速くなる

7.0 には安定したプログラム API が無く、API 依存のツールは 7.1 待ち。当面は `@typescript/typescript6` （ `tsc6` ）と併用する。

## 使い分けの目安

#### tsgo を選ぶ

- CI・本番ビルド・普段のエディタ
- 公式サポートと互換性が最優先
- まずは 6.0 → 7.0 の段階移行

#### tsrs を試す

- 巨大リポジトリで CI 時間・メモリを詰めたい（結果は tsgo と突き合わせる）
- ブラウザ・サンドボックス・エッジで型チェックを動かしたい

### コマンド例

```
# tsgo（TypeScript 7）
npm i -D typescript
npx tsc -p . --noEmit --checkers 8

# tsrs
npm i -D tsrs
npx tsrs -p . --noEmit
npx tsrs -p . --noEmit --checkerAssignment go   # Go 版と割り当てを揃えて比較
npx tsrs --lsp -stdio                            # 言語サーバー（実験的）
```

## 出典

- [Introducing tsrs: a Port of TypeScript to Rust（Cloudflare Blog, 2026-10-20）](https://blog.cloudflare.com/typescript-rust-port/)
- [A deep dive into tsrs（flaviocopes.com）](https://flaviocopes.com/tsrs/)
- [TypeScript 7 released（InfoQ, 2026-08）](https://infoq.com/news/2026/08/typescript-7-released/)
- [Inside TypeScript 7: Parallel Type Checking Without Giving Up Determinism（DEV Community）](https://dev.to/puffball1567/inside-typescript-7-parallel-type-checking-without-giving-up-determinism-2l0m)
