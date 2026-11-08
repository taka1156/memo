<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Vue と Svelte

> Vue の Proxy リアクティブと仮想 DOM、Vapor Mode、Svelte のコンパイラと runes を、コンパイル結果と依存追跡のデモで比較。

- URL: https://memo.taka1156.site/vue-vs-svelte.html
- タグ: JavaScript, フロントエンド
- 日付: 2026-11-02

---

ランタイムで賢く追跡する Vue、ビルド時に書き出す Svelte

**ざっくり言うと**

- **Vue** は Proxy による依存追跡でどのコンポーネントを更新するかを決め、その中は仮想 DOM で差分を取る。コンパイラが「変わりうる場所」に印を付けて差分を絞り込む
- **Svelte** は「コンパイラが本体」。 `.svelte` ファイルを、DOM を直接操作する JS に変換する。仮想 DOM はない
- 両者は近づいている。Svelte 5 は runes でシグナルに移り、Vue は 3.6 の **Vapor Mode** で仮想 DOM なしのコンパイルを選べるようになる

方式そのものの説明は [UI 更新の3つの方式](https://memo.taka1156.site/md/reactivity-models.md) にまとめてある。

## 同じカウンターを書く

Vue（Counter.vue）

```
<script setup>
import { ref, computed } from 'vue'
const count = ref(0)
const doubled = computed(() => count.value * 2)
</script>

<template>
  <button @click="count++">
    {{ count }}（×2 = {{ doubled }}）
  </button>
</template>
```

script では `count.value` 、テンプレートでは自動で `.value` が外れる。

Svelte 5（Counter.svelte）

```
<script>
  let count = $state(0)
  let doubled = $derived(count * 2)
</script>

<button onclick={() => count++}>
  {count}（×2 = {doubled}）
</button>
```

`$state` などの **runes** はコンパイラへの目印。普通の変数のように読み書きでき、裏でシグナルに変換される。

## 仕事をいつするか

同じ「更新を最小にする」でも、どれだけをビルド時に前倒しするかが違う（幅はイメージ）。

Vue（従来モード）

テンプレート解析・印付け

依存追跡 ＋ 仮想 DOM の差分

Vue Vapor Mode

DOM 操作コードを生成

依存追跡

Svelte 5

DOM 操作コードを生成

シグナル

ビルド時（コンパイラ） 実行時（ランタイム）

## Vue の内部

### Proxy による依存追跡

`reactive()` や `ref()` は値を Proxy（またはゲッター・セッター）で包む。 **読まれたとき（get）** に「今どの処理が読んだか」を記録し、 **書かれたとき（set）** にその処理だけを再実行する。ボタンで値を変えて、どの処理が動くか確かめる。

state.count++

state.name を変更

state.unused++

unused はどの処理からも読まれていないので、変えても何も起きない。

**Counter の描画** 読む：state.count

実行回数 1

**Greeting の描画** 読む：state.name

実行回数 1

**computed: summary** 読む：state.count、state.name

実行回数 1

Vue 3.6 では、このリアクティブの仕組みが alien-signals という高速なシグナル実装をもとに作り直された。

（元のページで操作できます → https://memo.taka1156.site/vue-vs-svelte.html#vue-internals）

### コンパイラによる最適化

Vue の仮想 DOM は「素朴に全部比べる」わけではない。テンプレートをコンパイルするときに、動的な部分に **パッチフラグ** を付け、静的な部分は使い回す。

```
// <div><h1>Todo</h1><p>{{ count }}</p></div> のコンパイル結果（Vue 3.5、簡略）
function render(ctx, _cache) {
  return (openBlock(), createElementBlock("div", null, [
    _cache[0] || (_cache[0] = createElementVNode("h1", null, "Todo", -1 /* CACHED */)), // 静的：初回だけ作ってキャッシュ
    createElementVNode("p", null, toDisplayString(ctx.count), 1 /* TEXT */)
  ]))
}
```

差分計算のときは、印の付いたノード（ここでは `p` のテキストだけ）を見ればよい。これにより、仮想 DOM を使いながら比較の量を大きく減らしている。

### Vapor Mode

コンポーネント単位で選べる、 **仮想 DOM を使わない** コンパイルモード。Solid や Svelte 5 と同じく、テンプレートを直接 DOM 操作するコードに変換する。

```
<script setup vapor>
// 書き方は同じ。vapor を付けたコンポーネントだけが新方式でコンパイルされる
</script>
```

Vue 3.6 で導入。2026年7月にリリース候補 (RC) 段階に入り、Vapor Mode に予定していた機能がそろった。従来のコンポーネントと混在でき、少しずつ移行できるのが特徴。 `<script setup>` （または template だけの SFC）で使い、Options API や `v-memo` には対応しない。

## Svelte の内部

### Svelte 4 と 5 の違い

Svelte 5（runes）

Svelte 4 まで

```
let count = $state(0)
let doubled = $derived(count * 2)
$effect(() => { console.log(count) })
let { title } = $props()
```

runes は明示的な目印なので、 **.svelte.js / .svelte.ts ファイル** の中でも使え、コンポーネントの外にリアクティブな状態を切り出せる。オブジェクトや配列の `$state` は Proxy で深く追跡される。

```
let count = 0               // トップレベルの let は自動でリアクティブ
$: doubled = count * 2      // $: ラベルで派生値
export let title            // export let で props
```

コンパイラが「代入文」を見つけて更新コードを差し込む方式。手軽だった反面、 `arr.push()` のような代入を伴わない変更は検知されない、コンポーネントの外では使えない、といった制約があった。

（元のページで操作できます → https://memo.taka1156.site/vue-vs-svelte.html#svelte-internals）

### コンパイル結果（イメージ）

```
// Counter.svelte → JS（Svelte 5、簡略化）
import * as $ from 'svelte/internal/client'
const root = $.from_html(`<button> </button>`)

export default function Counter($$anchor) {
  let count = $.state(0)                              // シグナルに変換
  let doubled = $.derived(() => $.get(count) * 2)

  const button = root()
  const text = button.firstChild
  $.delegated('click', button, () => $.set(count, $.get(count) + 1))  // クリックは document に委譲
  $.template_effect(() =>                             // このテキストだけを更新する effect
    $.set_text(text, `${$.get(count)}（×2 = ${$.get(doubled)}）`))
  $.append($$anchor, button)
}
$.delegate(['click'])
```

普通の変数に見えた `count` が、コンパイル後はシグナルの読み書き（ `$.get` / `$.set` ）になっている。構造は [Solid のコンパイル結果](https://memo.taka1156.site/md/react-vs-solid.md) とほぼ同じ。

## 比較表

| 観点 | Vue | Svelte 5 |
| --- | --- | --- |
| リアクティブ | ref / reactive（Proxy）。3.6 で alien-signals ベースに | runes（$state、$derived）→ シグナル |
| 仮想 DOM | あり（Vapor Mode を選べばなし） | なし |
| 状態の読み書き | script では `.value` が必要 | 普通の変数として書ける |
| テンプレート | HTML ＋ `v-if` 、 `v-for` 、 `{{ }}` （JSX も可） | HTML ＋ `{#if}` 、 `{#each}` 、 `{}` |
| 更新の単位 | コンポーネント（中は差分を絞った仮想 DOM） | DOM ノード |
| ランタイムの大きさ | 中程度（仮想 DOM を含む）。Vapor のみなら小さい | 小さい。コンポーネントが増えると生成コードが増える |
| フルスタックの枠組み | Nuxt | SvelteKit |
| 非同期 | `<Suspense>` （実験的） | テンプレート内の `await` など（実験的機能として提供） |

## よくある誤解

✕ 「Svelte はランタイムがゼロ」

○ シグナルや DOM ヘルパーなどの小さなランタイムはある（上のコンパイル結果の `svelte/internal/client` ）。「仮想 DOM のような大きなランタイムがない」が正確。

✕ 「Vue は仮想 DOM だから遅い」

○ 依存追跡で更新するコンポーネントを絞り、パッチフラグで比較対象も絞っているので、素朴な仮想 DOM よりずっと効率的。Vapor Mode ではベンチマーク上 Solid や Svelte 5 と並ぶ。

✕ 「Svelte 5 は Svelte 4 の書き方を少し変えただけ」

○ 「代入の検知」から「シグナル」へと、内部の仕組みが丸ごと作り直された。書き方の変化はその結果。

## 関連メモ

[← UI 更新の3つの方式](https://memo.taka1156.site/md/reactivity-models.md) [← React と Solid](https://memo.taka1156.site/md/react-vs-solid.md)
