<!-- scripts/memo.py build が自動生成。手で編集しない -->

# React と Solid

> 見た目はそっくりな JSX で、中身は正反対。React の再レンダーと Fiber、Solid のシグナルとコンパイル結果を、同じカウンターで比較。

- URL: https://memo.taka1156.site/react-vs-solid.html
- タグ: JavaScript, フロントエンド
- 日付: 2026-11-02

---

同じ JSX、正反対の実行モデル

**ざっくり言うと**

- どちらも JSX でコンポーネントを書くが、 **コンポーネント関数の扱い** がまったく違う
- **React** は状態が変わるたびにコンポーネント関数を **丸ごと再実行** し、仮想 DOM の差分で DOM を更新する
- **Solid** はコンポーネント関数を **最初の1回だけ** 実行して DOM を組み立て、以後はシグナルに依存する箇所だけを直接書き換える

方式そのものの説明は [UI 更新の3つの方式](https://memo.taka1156.site/md/reactivity-models.md) にまとめてある。このページは2つのフレームワークの内部に絞る。

## 同じカウンターを書く

React

```
function Counter() {
  const [count, setCount] = useState(0);
  console.log('Counter 実行');

  return (
    <button onClick={() => setCount(count + 1)}>
      {count}
    </button>
  );
}
```

`count` はただの数値。毎回の実行で、その時点の値が入った新しい変数になる。

Solid

```
function Counter() {
  const [count, setCount] = createSignal(0);
  console.log('Counter 実行');

  return (
    <button onClick={() => setCount(count() + 1)}>
      {count()}
    </button>
  );
}
```

`count` は **値を返す関数** （ゲッター）。呼び出した場所が「count に依存する場所」として記録される。

## ボタンを押すと何が起きるか

上のコードを動かしたときのコンソールを再現している。それぞれのボタンを何回か押してみる。

React

クリック

0

Counter の実行回数： **1**

Solid

クリック

0

Counter の実行回数： **1**

React ではクリックのたびに「Counter 実行」が出る。Solid では最初の1回きりで、以後はテキストノードを書き換える処理だけが動く。Solid のコンポーネントは **「DOM を組み立てて、更新の配線をするセットアップ関数」** であって、描画関数ではない。

## React の内部

### 更新の3段階

**① Render** コンポーネント関数を呼び、新しい要素の木（仮想 DOM）を作る。純粋な計算で、DOM には触らない

**② Commit** 前回との差分（reconciliation）を本物の DOM に反映する。ここは中断しない

**③ Effects** 描画後に `useLayoutEffect` 、続いて `useEffect` を実行する

Fiber

Hooks の正体

React Compiler

React はコンポーネントの木を **Fiber** というノードの連結リストで管理する。Render フェーズは Fiber を1つずつ処理する小さな仕事に分かれているので、途中で中断して、ユーザー入力のような急ぎの更新を先に処理できる。

`startTransition` で「急がない更新」と印を付けると、入力欄の反応を保ったまま重いリストの再描画を後回しにできる（並行レンダリング）。

`useState` の値は、コンポーネントに対応する Fiber の中に **呼び出し順で** 並んだリストとして保存されている。関数は毎回最初から実行されるので、React は「1番目の useState、2番目の useState…」という順番で値を取り出す。

だから **Hooks を if やループの中で呼んではいけない** （Rules of Hooks）。順番がずれると、別の state を取り出してしまう。

再実行モデルの弱点は「変化と関係ない子コンポーネントや計算まで毎回やり直す」こと。これまでは `memo` ・ `useMemo` ・ `useCallback` を手で書いて防いでいた。

**React Compiler** （1.0 で安定版）はビルド時にコードを解析し、これらのメモ化を自動で挿入する。手書きのメモ化はほぼ不要になる。ただし「状態が変わったらコンポーネントを再実行する」というモデル自体は変わらない。

## Solid の内部

### JSX はこうコンパイルされる

Solid の JSX は仮想 DOM を作らない。コンパイラが「HTML のテンプレート」と「どのノードに effect を張るか」に分解する。

```
// コンパイル後（簡略化したイメージ）
const tmpl = template(`<button></button>`);

function Counter() {
  const [count, setCount] = createSignal(0);
  console.log('Counter 実行');

  const el = tmpl();                          // テンプレートを複製
  el.onclick = () => setCount(count() + 1);
  insert(el, () => count());                  // ← ここが effect。count が変わると中身だけ更新
  return el;                                  // 本物の DOM ノードを返す
}
```

コンポーネント関数は DOM ノードを作って返したら役目が終わる。以後の更新は、 `insert` の中で張られた effect が担う。

### 制御フローはコンポーネントで書く

REACT

```
{user ? <Profile /> : <Login />}
{items.map(i => <Row item={i} />)}
```

SOLID

```
<Show when={user()} fallback={<Login />}>
  <Profile />
</Show>
<For each={items()}>{i => <Row item={i} />}</For>
```

Solid のコンポーネントは再実行されないので、三項演算子や `map` を素で書くと「その時点の結果」で固定されてしまう（実際はコンパイラが式を関数で包むので多くは動くが、リストの効率的な差分更新には `<For>` が必要）。

### Solid 2.0

2026年にリリース候補 (RC) に到達した次のメジャー版。リアクティブの核を作り直した。このページのコード例は、現行の安定版である 1.x の書き方。

- **非同期が第一級** ：計算が Promise を返してよく、グラフ自体が待機・再開する。 `Suspense` は `<Loading>` に置き換え
- **更新はマイクロタスクでまとめて反映** ： `set` した直後に読んでも、まとめて反映されるまで古い値（すぐ反映したいときは `flush()` ）
- ** `createEffect` が「計算」と「反映」の2段に分割** 、 `onMount` は `onSettled` に
- 楽観的更新の `createOptimisticStore` 、ミューテーション用の `action` など
- API の整理： `splitProps` → `omit` 、 `mergeProps` → `merge` 、 `Index` は `<For keyed={false}>` に統合

## 比較表

| 観点 | React | Solid |
| --- | --- | --- |
| 更新の単位 | コンポーネント（＋子孫） | シグナルに依存する式・DOM ノード |
| コンポーネントの実行 | 状態が変わるたび | 最初の1回だけ |
| 状態の読み方 | `count` （値） | `count()` （関数呼び出し） |
| 仮想 DOM | あり | なし（本物の DOM を直接返す） |
| 副作用の依存 | `useEffect` の依存配列を手で書く | 自動追跡（読んだシグナルが依存になる） |
| メモ化 | React Compiler が自動化（手書きなら useMemo など） | 基本不要。派生値は `createMemo` |
| 条件分岐・リスト | 普通の JS（三項演算子、map） | `<Show>` ・ `<For>` を推奨 |
| props の分割代入 | 問題なし | リアクティブ性が切れる（2.0 では開発時に警告） |
| フルスタックの枠組み | Next.js、React Router など | SolidStart |
| エコシステム | 圧倒的に大きい | 小さいが、必要な部品は揃う |

## それぞれのハマりどころ

React

Solid

- **古いクロージャ** ： `setInterval` の中の `count` は、その回のレンダーの値で固定される。更新関数 `setCount(c => c + 1)` を使う
- **useEffect の依存配列** ：書き漏れると古い値を使い、多すぎると無限ループ。そもそも effect が要らない場面も多い
- **Hooks の呼び出し順** ：条件分岐の中で呼ぶと壊れる
- **props の分割代入** ： `function Row({ item })` と書くと、その瞬間の値を取り出して追跡が切れる。 `props.item` のまま使うか `splitProps` （2.0 では `omit` に改名）を使う。2.0 では開発時に警告が出る
- **コンポーネント内での早期 return** ： `if (!user()) return <Login />` は一度しか評価されないので、後から user が変わっても切り替わらない。 `<Show>` を使う
- **追跡の外で読む** ：イベントハンドラや `setTimeout` の中で読んだシグナルは依存にならない（意図通りのことも多い）

## よくある誤解

✕ 「Solid は React の軽量版」

○ JSX と Hooks に似た API で見た目は近いが、実行モデルが根本から違う。React の感覚で書くと、分割代入や早期 return でつまずく。

✕ 「React Compiler を使えば React も細粒度更新になる」

○ 減るのは「不要な再実行」で、更新の単位はコンポーネントのまま。仮想 DOM の差分計算もなくならない。

✕ 「速い Solid のほうが常に良い」

○ 多くのアプリでは React の速度で十分で、採用・ライブラリ・情報量の差のほうが効く。Solid が活きるのは、更新頻度が高く大量の要素を扱う UI や、ランタイムを小さくしたい場面。

## 関連メモ

[← UI 更新の3つの方式](https://memo.taka1156.site/md/reactivity-models.md) [Vue と Svelte →](https://memo.taka1156.site/md/vue-vs-svelte.md)
