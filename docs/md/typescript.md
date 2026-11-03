<!-- scripts/memo.py build が自動生成。手で編集しない -->

# TypeScript 学習フローと仕組み

> TypeScript を学ぶ6ステップと、型チェック・型消去・コンパイルの流れを図で整理。

- URL: https://memo.taka1156.site/typescript.html
- タグ: 言語, JavaScript
- 日付: 2026-11-02

---

何から順に学ぶか ／ 型はどこでチェックされ、どこで消えるのか

**ざっくり言うと**

- TypeScript ＝ JavaScript ＋ 型 。型は **開発時だけ** 働き、実行前に全部消える（型消去 / type erasure）。
- 仕組みは「 **型チェック** 」と「 **JS への変換** 」の 2 つの仕事。最近はこの 2 つを別ツールで分担するのが主流。
- 学ぶ順番は **JS 基礎 → 基本の型 → 型の合成・絞り込み → ジェネリクス → 設定とツール → 型レベル** 。

## 仕組み：TypeScript が JavaScript になるまで

TypeScript のコンパイラ（ `tsc` ）の中では、ソースコードが次の順に処理されます。 紫の点線 は「型の情報」の流れで、 **出力される JS には届きません** 。

（図: app.ts / ソースコード / ① Scanner / 文字 → トークン / ② Parser / トークン → 構文木 / AST / 抽象構文木 / 型の世界（実行時には存在しない） / ③ Binder / 名前とスコープを結びつけ / ④ Checker / 型を推論・照合しエラー検出 / エラー表示 / エディタの赤波線 / tsc の出力 / app.d.ts / 型だけを書き出した宣言 / ⑤ Emitter / 型注釈を削って出力 / app.js / 型エラーがあっても JS は出る / （noEmitOnError で止められる））

型の情報（JS に残らない） 実行される JS 開発者へのフィードバック

## 型消去：書いたコードと実行されるコード

app.ts（書くもの）

```
type User = {
  id: number;
  name: string;
};

function greet(u: User): string {
  return `Hi, ${u.name}`;
}

greet({ id: 1, name: "Ann" });
```

app.js（動くもの）

```
function greet(u) {
  return `Hi, ${u.name}`;
}

greet({ id: 1, name: "Ann" });
```

型定義と `: User` などの注釈が消えただけ。ロジックはそのまま。

だから「実行時に型で分岐する」ことはできない。外部から来るデータ（API レスポンスなど）は `zod` などで実行時に検証する必要がある。

## 2 つの仕事を誰がやるか

「型チェック」と「JS への変換」は分けられる。今はツールごとに担当が違う。

tsc 単体

バンドラ併用

ランタイム直実行

### tsc が両方やる（基本形）

`tsc` が型チェックしてから JS を出力。ライブラリの公開（ `.d.ts` も必要）や学習の最初はこれ。

```
npx tsc --init   # tsconfig.json を作る
npx tsc          # チェック ＋ 出力
npx tsc --noEmit # チェックだけ（CI でよく使う）
```

TypeScript 7 では tsc 自体が Go で書き直され（ネイティブ版）、大規模プロジェクトのビルドが大幅に速くなった。

### 変換は高速ツール、チェックは tsc / エディタ

Vite は内部の Oxc 、Next.js は SWC で **型を削るだけ** 。どちらも型を「理解」しないので速く、型エラーがあっても画面は動く。

```
開発中: エディタ(言語サーバ)が型エラーを表示
ビルド: vite build        ← 型は見ない
CI    : tsc --noEmit      ← ここで型を検査
```

### ランタイムがそのまま実行

Deno・Bun は `.ts` を直接実行できる。Node.js も最近のバージョンでは **型注釈を取り除いて** そのまま実行できる（type stripping）。

```
node app.ts   # 型を削って実行（チェックはしない）
```

Node の型除去は「消すだけ」なので、 `enum` など JS コードを生成する構文は既定では使えない。 `erasableSyntaxOnly` オプションで事前に検出できる。

## 型チェックの考え方：構造的型付け

TypeScript は「名前」ではなく「 **形（持っているプロパティ）** 」で型の互換性を判断する（構造的型付け / structural typing）。

（図: type Point / x: number / y: number / { x, y, z } / x, y を持つ / ＋ 余分な z / ◯ Point として渡せる / { x } / y が足りない / ✕ 型エラー）

※ オブジェクトリテラルを直接書いた場合だけは、余分なプロパティもエラーになる（excess property check）。

## 学習フロー：6 ステップ

各ステップをタップすると、学ぶ項目と「次に進む目安」が開きます。

1. 0
   **JavaScript の基礎** 前提 TS は JS の上に乗っている。ここが曖昧だと型も曖昧になる
   let / const 関数・アロー関数 オブジェクト・配列 分割代入・スプレッド Promise / async-await ES Modules
   **目安：** fetch でデータを取ってきて配列を加工する小さなスクリプトが書ける。
2. 1
   **基本の型** 入門 変数・関数に型を付け、推論に任せる感覚をつかむ
   string / number / boolean 配列 T[] オブジェクト型 関数の引数・戻り値 型推論 any と unknown

```
let count = 0;            // number と推論される
const add = (a: number, b: number) => a + b; // 戻り値も推論
```

   **目安：** 「全部に型を書く」のではなく、 **引数には書き、あとは推論** が自然にできる。
3. 2
   **型を組み立てる・絞り込む** 基礎 現実のデータの形を型で表現する
   type / interface ユニオン A | B リテラル型 オプショナル ? narrowing (typeof / in) 判別可能なユニオン null / undefined

```
type Result =
  | { ok: true;  data: string }
  | { ok: false; error: Error };

function show(r: Result) {
  if (r.ok) r.data;   // ここでは data がある
  else      r.error;  // ここでは error がある
}
```

   **目安：** if 文で型が絞り込まれていく様子をエディタのホバーで確認できる。
4. 3
   **ジェネリクスと組み込みユーティリティ** 中級 型を引数にとって再利用する
   <T> 制約 extends Partial / Required Pick / Omit Record ReturnType keyof / typeof

```
function first<T>(arr: T[]): T | undefined {
  return arr[0];
}
first([1, 2]);      // number | undefined
first(["a"]);       // string | undefined
```

   **目安：** ライブラリの型定義（ `.d.ts` ）を読んで、だいたい意味がわかる。
5. 4
   **設定とツールチェーン** 実践 実プロジェクトで型の恩恵を最大にする
   tsconfig.json strict: true noUncheckedIndexedAccess tsc --noEmit Vite / Next.js ESLint (typescript-eslint) @types/* zod 等の実行時検証

```
{
  "compilerOptions": {
    "strict": true,
    "target": "ES2022",
    "module": "nodenext",
    "noEmit": true
  }
}
```

   **目安：** 新規プロジェクトを `strict` で立ち上げ、CI で型チェックを回せる。
6. 5
   **型レベルプログラミング** 上級 型で型を計算する。ライブラリ作者向け
   Conditional Types infer Mapped Types Template Literal Types satisfies 型の分配

```
type Unwrap<T> = T extends Promise<infer U> ? U : T;
type A = Unwrap<Promise<string>>; // string
```

   **目安：** 必要になってから学べば十分。アプリ開発ではステップ 4 までで大半が足りる。

## 学び方の比較

| 方法 | 向いている段階 | ポイント |
| --- | --- | --- |
| 公式 Playground | ステップ 1〜3 | ブラウザで書いて、右側に出る JS とエラーを即確認。型消去を目で見られる |
| 公式 Handbook | ステップ 1〜5 | 体系的。迷ったときの一次情報 |
| 既存 JS を TS 化 | ステップ 2〜4 | 拡張子を .ts にして赤線を 1 つずつ消す。実務に一番近い |
| type-challenges | ステップ 5 | 型パズル集。型レベルの練習用 |

## よくある誤解

型を書けば実行時にもチェックされる

型はコンパイル時に消える。外部入力は実行時に検証する（zod など）。

型エラーがあると JS が出力されない

tsc は既定でエラーがあっても JS を出す。esbuild や Node の型除去はそもそもチェックしない。

TypeScript にすると実行が速くなる / 遅くなる

実行されるのはただの JS なので、速度は変わらない。変わるのはビルド時間と開発体験。

とりあえず any で逃げればいい

any はチェックを止める。型がわからないときは `unknown` にして、絞り込んでから使う。

全部の変数に型注釈を書くべき

推論できるところは任せる。書くのは関数の引数・公開 API・推論が広すぎるところ。
