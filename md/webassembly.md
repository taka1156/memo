<!-- scripts/memo.py build が自動生成。手で編集しない -->

# WebAssembly

> Wasm が何で、どうやって JS から呼ばれ、なぜ速い場面と速くない場面があるのかを、線形メモリ・サンドボックス・境界のコストで図解。WasmGC、WASI とコンポーネントモデルによるブラウザ外での利用まで。

- URL: https://memo.taka1156.site/webassembly.html
- タグ: フロントエンド, 言語, JavaScript
- 日付: 2026-11-03

---

「JS の代わり」ではなく「JS が呼び出す、速くて安全な計算部品」

**ざっくり言うと**

- WebAssembly（Wasm）は、ブラウザなどで動く **コンパクトなバイナリ形式の命令セット** 。Rust・C/C++・Go・Zig などからコンパイルして作る。
- 速いのは **計算が詰まった処理** （画像・動画・圧縮・暗号・物理演算・既存の C ライブラリ）。DOM 操作は JS を経由するので、細かく行き来すると **境界のコスト** でむしろ遅くなる。
- Wasm は自分の **線形メモリ** の外に触れず、使えるのは渡された関数だけ（サンドボックス）。この性質を活かして、ブラウザ外（サーバー・エッジ・プラグイン）でも WASI とコンポーネントモデルで使われている。

## 作られ方と動き方

Rust / C++ / Go… ソースコード

→

コンパイラ LLVM・wasm-pack・Emscripten

→

.wasm バイナリ＋JS のグルーコード

→

ブラウザ 検証 → 機械語にコンパイル

JS はまず文字列を構文解析し、実行しながら型を推測して最適化する。Wasm は **型が最初から決まった低レベルの命令** なので、読み込みながら（ストリーミングで）すぐ機械語にでき、速度のぶれも小さい。ただし「JS の何倍も速い」とは限らず、最適化の効いた JS とは同程度のことも多い。差が出るのは、メモリの配置を細かく制御できる処理や、JS の最適化が外れやすい処理。

```
// .wasm を読み込んで関数を呼ぶ（ストリーミングでコンパイル）
const { instance } = await WebAssembly.instantiateStreaming(
  fetch('/blur.wasm'),
  { env: { log: (n) => console.log(n) } }   // Wasm に渡す関数（imports）
);
instance.exports.blur(ptr, width, height);   // Wasm が公開した関数（exports）
```

サーバーは `Content-Type: application/wasm` で返す必要がある（instantiateStreaming の条件）。Rust なら wasm-bindgen が文字列や配列の受け渡し用の JS を生成してくれるので、上のような低レベルの呼び方を直接書くことは少ない。

## 線形メモリと境界のコスト

**JS の世界** オブジェクト・文字列・DOM・GC

文字列・配列はコピー

数値・参照は素通り

**Wasm の世界** 数値・参照と線形メモリ

Wasm の関数がやり取りする値は、基本的に **数値** （i32 / i64 / f32 / f64 など）と **参照** （ `externref` など）だけ。文字列や配列の中身を Wasm で処理するときは、Wasm の線形メモリ（1 本の大きなバイト配列）に書き込んで、その **位置（ポインタ）と長さ** を渡すのが一般的。JS のオブジェクトや DOM 要素は `externref` で参照のまま受け渡せるが、Wasm から中身は読めず、JS の関数に渡し返して操作する。

0 … h e l l o … px px px px …

青は文字列 "hello" を UTF-8 で書き込んだ場所、紫は画像のピクセル。JS 側からは `new Uint8Array(memory.buffer)` で同じバイト列が見える。

遅くなる使い方

ピクセル 1 つごとに JS から Wasm の関数を呼ぶ。DOM の要素 1 つごとに Wasm から JS を呼ぶ。毎回の呼び出しと変換のコストが計算より大きくなる。

速くなる使い方

画像全体を 1 回線形メモリにコピーし、Wasm の中でループを回し、結果を 1 回で返す。 **境界を越える回数を減らし、中で長く計算させる** 。

## 安全性：何から守られているか

守られる

Wasm は自分の線形メモリの外（ブラウザのメモリ、JS のオブジェクト）を読み書きできない。ファイル・ネットワーク・DOM には、 **呼び出し側が imports で渡した関数を通してしか** 触れない（ケイパビリティベース。渡された権限＝ケイパビリティにだけ触れられる）。ブラウザの同一オリジンポリシーや CSP もそのまま効く。

守られない

C/C++ のバッファオーバーフローは **線形メモリの中では普通に起きる** 。外には出られないが、同じモジュール内のデータは壊れうる。信頼できない入力を古い C ライブラリに渡すなら、Wasm 化しても入力検証は必要。

## 実際の使われ方

| 分野 | 例 | Wasm を使う理由 |
| --- | --- | --- |
| 既存ライブラリの移植 | SQLite・FFmpeg・画像コーデック・PDF 描画 | C/C++ の資産をそのままブラウザで動かせる |
| 重い計算 | デザインツール、CAD、動画編集、ゲームエンジン | メモリ配置を制御でき、速度が安定する |
| 開発ツール | ブラウザ上で動くコンパイラ・リンター・プレイグラウンド | サーバーなしで同じツールを配れる |
| 他言語の UI | Kotlin・Dart（Flutter）などの Web 版 | WasmGC で GC 付き言語も自前の GC を同梱せず、ブラウザの GC を使って動く |
| サーバー・エッジ | エッジの関数、プロキシのフィルター、プラグイン | 起動が速く、隔離が強く、言語を選ばない |

**WasmGC** ：もとの Wasm は GC を持たず、GC が必要な言語はランタイムごと同梱していた。WasmGC は Wasm に構造体や配列の型を追加し、 **ブラウザの GC にオブジェクトを管理させる** ので、出力が小さくなり JS とのオブジェクト共有もしやすくなった。主要ブラウザで使える。

## ブラウザの外：WASI とコンポーネントモデル

**コンポーネント A** Rust 製

**コンポーネント B** Go や Python 製

↕ WIT で型付きのインターフェースを定義し、言語をまたいで呼び合う

**WASI** ファイル・時計・乱数・ソケット・HTTP などの標準 API

↓

**ランタイム** Wasmtime・WasmEdge・エッジ基盤など

**ケイパビリティベース** 「/data だけ読める」「この宛先だけ通信できる」といった権限をホストが渡す。渡されていないものには触れない。

**WASI** はブラウザ以外で Wasm が OS の機能を使うための標準インターフェース。 **コンポーネントモデル** は、文字列やリストなどの高水準な型（WIT で定義）でモジュール同士をつなぐ仕組みで、別言語で書いた部品を組み合わせられる。WASI の新しい版はこのコンポーネントモデルの上に定義されている。

「コンテナの次」と言われることがあるが、置き換えというより用途が違う。Wasm は起動がミリ秒単位で小さく隔離が強いので、 **リクエストごとに起動する関数やプラグイン** に向く。既存の Linux アプリをそのまま動かすならコンテナ。WASI はまだ版を重ねている途中なので、使うランタイムがどの版に対応しているかを確認する。

## 使うべきか

1. **ボトルネックは計算か？** まず DevTools で測る。遅いのが DOM 更新やネットワーク待ちなら Wasm は効かない。
2. **既存の C/C++/Rust ライブラリがあるか？** あるなら移植の価値が高い。JS で書き直すより正確で速いことが多い。
3. **境界をまたぐ回数を減らせる設計か？** 大きなデータを 1 回渡して中で処理できるなら効果が出る。
4. **ダウンロードサイズは許容できるか？** .wasm は数百 KB〜数 MB になることがある。必要になったときに遅延読み込みし、Worker で動かしてメインスレッドを空ける。

## 関連メモ

[Rust](https://memo.taka1156.site/md/rust.md) [JS ランタイム比較](https://memo.taka1156.site/md/js-runtimes.md) [JS と Web 標準の決まり方](https://memo.taka1156.site/md/js-web-standards.md) [Cloudflare サービス](https://memo.taka1156.site/md/cloudflare-services.md) [ブラウザのレンダリング](https://memo.taka1156.site/md/browser-rendering.md)

## 参考

- [WebAssembly](https://webassembly.org/)
- [MDN: WebAssembly](https://developer.mozilla.org/ja/docs/WebAssembly)
- [WASI](https://wasi.dev/)
- [The WebAssembly Component Model](https://component-model.bytecodealliance.org/)
- [wasm-bindgen（rustwasm org の終了後、wasm-bindgen org に移った）](https://github.com/wasm-bindgen/wasm-bindgen)
- [MDN: externref](https://developer.mozilla.org/en-US/docs/WebAssembly/Reference/Value_types/externref)
