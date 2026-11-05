<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Web Components

> Custom Elements・Shadow DOM・slot・template の 4 つの部品と、スタイルの通り方（CSS 変数・::part）、イベントの伝わり方、Declarative Shadow DOM による SSR、フォーム連携とアクセシビリティの注意点を、動くコピーボタン部品で図解。

- URL: https://memo.taka1156.site/web-components.html
- タグ: フロントエンド, JavaScript, 設計
- 日付: 2026-11-03

---

フレームワークに依存しない「ブラウザ標準の部品」。どこでも動くが、どこまで閉じるかが設計の要

**ざっくり言うと**

- Web Components は **Custom Elements** （独自タグとそのふるまい）・ **Shadow DOM** （外から隔離された中身）・ **slot** （外の子要素を差し込む穴）・ **template** の組み合わせ。
- React でも Vue でも素の HTML でも **同じタグとして使える** のが最大の利点。デザインシステムや埋め込みウィジェットのように、使う側の技術が選べない部品に向く。
- Shadow DOM は **スタイルを閉じる** ので、外からのテーマ変更は CSS 変数と `::part` で許可した部分だけ。ID 参照が基本的に境界を越えられないなど、アクセシビリティとフォームには追加の作業が要る。

## 動くデモ：コードのコピーボタン

ドキュメントサイトでよく見る「コードの横にあるコピーボタン」を部品にしたもの。下の 2 つは同じ `<copy-snippet>` で、中に書いたコードがそのまま表示され、ボタンでクリップボードにコピーされる。2 つ目は使う側の CSS で色を変え、ボタンの文字を slot で差し替えている。

npm create vite@latest git clone https://github.com/example/app.git Copy

document で待ち受け中…（ボタンを押すとここに届く）

```
<copy-snippet>npm create vite@latest</copy-snippet>

<copy-snippet class="themed" done-text="Copied!">
  git clone https://github.com/example/app.git
  <span slot="label">Copy</span>        <!-- ボタンの文字を差し替え -->
</copy-snippet>

/* 使う側の CSS：中に届くのは CSS 変数と ::part だけ */
.themed { --snippet-accent: orange; }
copy-snippet::part(button) { font-weight: 700; }

// 部品の外でイベントを受け取る
document.addEventListener('copy-done', e => console.log(e.detail.text));
```

プレビュー環境などでクリップボードへの書き込みが許可されていないと「コピーできません」と表示されるが、イベントはどちらでも外へ届く。

## 定義のしかた

```
class CopySnippet extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' }).innerHTML = `
      <style>
        :host { display: block; }
        button { background: var(--snippet-accent, royalblue); color: white; }
      </style>
      <code part="code"><slot></slot></code>          <!-- 名前なし slot：子要素がここに映る -->
      <button part="button">
        <slot name="label">コピー</slot>              <!-- 差し込まれなければ既定の文字 -->
      </button>`;
  }
  connectedCallback() {
    this.shadowRoot.querySelector('button').onclick = () => this.copy();
  }
  async copy() {
    // 名前なし slot に割り当てられた「使う側が書いた中身」だけを集める
    const text = this.shadowRoot.querySelector('slot:not([name])')
      .assignedNodes().map(n => n.textContent).join('').trim();
    await navigator.clipboard.writeText(text);
    this.#flash(this.getAttribute('done-text') ?? 'コピーしました');  // 属性はその都度読む
    // ホスト要素自身から出すので、外へ届けるには bubbles だけでよい
    this.dispatchEvent(new CustomEvent('copy-done', { detail: { text }, bubbles: true }));
  }
  #flash(msg) { /* ボタンの横に msg を 1.5 秒表示 */ }
}
customElements.define('copy-snippet', CopySnippet);   // 名前には必ずハイフン
```

`constructor` 作られた直後。Shadow DOM を付ける。属性や子要素はまだ揃っていないことがあるので読まない。 `connectedCallback` 文書に入ったとき。イベント登録・データ取得はここで。移動のたびに呼ばれうる。 `disconnectedCallback` 文書から外れたとき。タイマーや外部へのリスナーを片付ける。 `attributeChangedCallback` `observedAttributes` に挙げた属性が変わったとき。

## イベントはどこまで届くか

| どこから出すか | 外の document に届く条件 |
| --- | --- |
| ホスト要素自身（ `this.dispatchEvent` ） | `bubbles: true` だけでよい。ホストはもともと外側（ライト DOM）にいるので、Shadow DOM の境界を通らない。 |
| Shadow DOM の中の要素 | `bubbles: true` と `composed: true` の両方が要る。 `composed` がないと shadow root で止まる。 |

中の要素から境界を越えたイベントは、外から見ると **ホスト要素から来たように見える** （ `event.target` が付け替えられる）。 `click` のような標準の UI イベントは最初から composed なので外まで届く。属性は文字列しか渡せないので、配列やオブジェクトは **プロパティ** で渡す（React 19 以降はカスタム要素へのプロパティ渡しにも対応している）。

## Shadow DOM の中と外

<copy-snippet class="themed" done-text="Copied!">

#shadow-root（中：部品の作者が書く）

<style>…</style> ← 外に漏れない・外から入らない

<code part="code"><slot> ← ① のテキストがここに映る

<button part="button"><slot name="label"> ← ② がここに映る

① git clone https://… （ライト DOM：使う人が書く）

② <span slot="label">Copy</span>

</copy-snippet>

slot に入った要素は **移動せず、ライト DOM にいたまま表示だけ中に映る** 。だから使う側の CSS がそのまま効く（部品側からは `::slotted()` で直下の要素だけ触れる）。部品の JS から中身を読むときは、 `slot.assignedNodes()` で「その slot に割り当てられたもの」を取る。

| 外から | 中に届く？ | 使い方 |
| --- | --- | --- |
| 普通のセレクタ | × 届かない | 隔離されているので `.docs button` は中のボタンに効かない |
| 継承するプロパティ | ○ 届く | `color` ・ `font-family` などは境界を越えて継承される |
| CSS 変数 | ○ 届く | 部品側が `var(--snippet-accent, 既定値)` で受け口を用意。テーマ用の公式 API |
| `::part()` | ○ 指定した要素だけ | 部品側が `part="button"` で公開した要素を外から自由に装飾 |

## SSR：Declarative Shadow DOM

Shadow DOM は JS で `attachShadow` しないと作れなかったので、JS が動くまで中身が見えなかった。 **Declarative Shadow DOM** は HTML に直接書け、パース時点で Shadow DOM になる。

```
<copy-snippet>
  <template shadowrootmode="open">
    <style>…</style>
    <code part="code"><slot></slot></code>
    <button part="button"><slot name="label">コピー</slot></button>
  </template>
  npm create vite@latest
</copy-snippet>
```

主要ブラウザで使える。JS が読み込まれたら、コンストラクタで「すでに `this.shadowRoot` があればそれを使う」ようにすると二重に作らずに済む（Web Components 版のハイドレーション）。JS が来る前からコードもボタンも見えていて、JS が来た時点でボタンが動き出す。

## フォームとアクセシビリティの落とし穴

フォームに参加しない

Shadow DOM の中の `<input>` は外の `<form>` の送信に含まれない。 `static formAssociated = true` と `attachInternals()` の `setFormValue()` ・ `setValidity()` で、部品自体をフォーム部品として振る舞わせる。

ID 参照が境界を越えない

外の `<label for="x">` や `aria-labelledby` は、基本的に Shadow DOM の中の要素を指せない。Chrome / Edge 152 以降は ShadowRoot の `referenceTarget` で中の要素へ転送できるが、Firefox・Safari は未対応（2026 年 11 月時点）。当面は、ラベルを slot で中に入れる、部品側が `ElementInternals` の ARIA プロパティで役割と名前を持つ、などで補う。

中に本物の `<button>` や `<input>` を置くのが一番確実。このデモのボタンも本物の `<button>` なので、Tab で移動して Enter で押せる。 `<div>` にクリックを付けて作るとキーボード操作と読み上げを全部自前で作ることになる。

## フレームワークの部品との違い

|  | Web Components | React / Vue などの部品 |
| --- | --- | --- |
| 動く場所 | どのフレームワークでも、素の HTML でも | そのフレームワークの中だけ |
| スタイル | Shadow DOM で強く隔離 | CSS Modules などで名前を分けるだけ（外から上書き可） |
| 状態と描画 | 自前（Lit などのライブラリで補う） | リアクティビティと差分描画が組み込み |
| SSR | Declarative Shadow DOM で可能、ツールは少なめ | メタフレームワークで成熟 |
| 向いている | デザインシステム、埋め込みウィジェット、ドキュメントの部品（このコピーボタンのような） | アプリ本体の画面 |

アプリ全体を Web Components だけで作ることもできるが、状態管理やルーティングは自分で選んで組む必要がある。Lit は小さなリアクティブ基盤とテンプレートを足して、この部分の手間を減らすライブラリ。

## 関連メモ

[コンポーネント設計](https://memo.taka1156.site/md/component-design.md) [デザイントークン](https://memo.taka1156.site/md/design-tokens.md) [アクセシビリティ](https://memo.taka1156.site/md/a11y-checklist.md) [UI 更新の3つの方式](https://memo.taka1156.site/md/reactivity-models.md) [レンダリング戦略](https://memo.taka1156.site/md/rendering-strategies.md)

## 参考

- [MDN: ウェブコンポーネント](https://developer.mozilla.org/ja/docs/Web/API/Web_components)
- [HTML Standard: Custom elements](https://html.spec.whatwg.org/multipage/custom-elements.html)
- [MDN: Event.composed](https://developer.mozilla.org/docs/Web/API/Event/composed)
- [MDN: ElementInternals](https://developer.mozilla.org/en-US/docs/Web/API/ElementInternals)
- [web.dev: Declarative Shadow DOM](https://web.dev/articles/declarative-shadow-dom)
- [web-features: Reference target](https://web-platform-dx.github.io/web-features-explorer/features/referencetarget)
- [Lit](https://lit.dev/)
