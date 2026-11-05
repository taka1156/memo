<!-- scripts/memo.py build が自動生成。手で編集しない -->

# ブラウザのレンダリング

> HTML と CSS が DOM・CSSOM・レイアウト・ペイント・合成を経て画面になるまでと、どの CSS 変更がどこからやり直しになるか、ブロッキングとレイアウトスラッシングを図解。

- URL: https://memo.taka1156.site/browser-rendering.html
- タグ: フロントエンド, JavaScript
- 日付: 2026-11-03

---

「どの段からやり直すか」がわかると、速い CSS・遅い JS の理由が見える

**ざっくり言うと**

- 画面は **DOM＋CSSOM → スタイル計算 → レイアウト → ペイント → 合成** の順で作られる。変更があると、影響する段から後ろだけやり直す。
- `width` や `top` を変えるとレイアウトから、 `color` ならペイントから、 ** `transform` と `opacity` は合成だけ** で済む。アニメーションはこの 2 つで作る。
- JS で「書く → 読む」を交互にするとレイアウトが何度も強制される（レイアウトスラッシング）。読むのをまとめてから書く。

## パイプライン

**Parse** HTML → DOM

CSS → CSSOM

**Style** 要素ごとに最終的な値を計算

**Layout** 位置と大きさを決める

**Paint** 描画命令のリストを作る

**Composite** レイヤーを重ねて GPU で表示

← メインスレッド（JS と同じスレッド） コンポジタースレッド / GPU →

`display: none` の要素はレイアウト以降に出てこない。 `visibility: hidden` は場所を取るのでレイアウトには参加する。

## どの変更がどこからやり直しになるか

CSS プロパティを選ぶと、やり直しになる段が赤くなる。

width

top / left

font-size

DOM に要素を追加

color

background

box-shadow

transform

opacity

**Style**

**Layout**

**Paint**

**Composite**

transform / opacity が合成だけで済むのは、その要素が独立したレイヤーになっているとき。アニメーション中はブラウザが自動で昇格させる。 `will-change: transform` で事前に昇格できるが、付けすぎるとレイヤーごとに GPU メモリを使うので、動かす要素だけに付ける。

（元のページで操作できます → https://memo.taka1156.site/browser-rendering.html#cost）

## 何が描画を止めるか

CSS はレンダリングをブロック

`<head>` の CSS が届くまで、ブラウザは画面を描かない（スタイルなしの一瞬を見せないため）。重要な CSS は小さく、残りは遅らせる。

同期 script はパースをブロック

`<script src>` に出会うと、取得と実行が終わるまで HTML の解析が止まる。スクリプトが `document.write` する可能性があるため。

HTML の解析（緑）と、スクリプトの取得（紫）・実行（赤）の関係。

<script>

解析 取得 実行 解析

async

解析 実行 解析

defer

解析（裏で取得） 実行

type=module

解析（裏で取得） 実行

**async** ：取れしだい実行。順番は保証されない（広告・計測向け）。 **defer** ：解析が終わってから書いた順に実行（アプリ本体向け）。 **module** は既定で defer と同じ動き。どれも取得自体は解析と並行して進む。さらにブラウザは本解析の先を読む **プリロードスキャナー** で画像や CSS を早めに取りに行く。JS で後から差し込んだ `<img>` はこれに見つけてもらえない。

## レイアウトスラッシング

レイアウトは通常「次のフレームの前に 1 回」まとめて行われる。ところが JS が **サイズや位置を読む** と、ブラウザは最新の値を返すためにその場でレイアウトを実行する（強制同期レイアウト）。

NG：書く・読むを交互に

```
for (const el of items) {
  el.style.width = box.offsetWidth + 'px';
  // ↑ 読む → 直前の書き込みのせいで毎回レイアウト
}
```

OK：まとめて読んでから書く

```
const w = box.offsetWidth;   // 読むのは 1 回
for (const el of items) {
  el.style.width = w + 'px'; // 書くだけ
}
```

レイアウトを強制する読み取りの例： `offsetWidth/Height` ・ `getBoundingClientRect()` ・ `scrollTop` ・ `getComputedStyle()` 。ループの中に読みがあったら疑う。

## 1 フレームの中身

入力イベント

→

JS（タスク）

→

requestAnimationFrame

→

Style・Layout

→

Paint

→

Composite

60Hz の画面なら 1 フレームは約 16.7ms。 **メインスレッドで 50ms を超えて走る処理はロングタスク** と呼ばれ、その間クリックへの反応も描画も止まる。重い処理は分割して合間に描画を挟むか、Web Worker に逃がす。

見た目を JS で毎フレーム動かすなら `setTimeout` ではなく `requestAnimationFrame` 。描画の直前に呼ばれるので、無駄なフレームやズレが出ない。

## 描画を軽くする CSS

| 書き方 | 効果 |
| --- | --- |
| `content-visibility: auto` | 画面外のセクションのレイアウト・ペイントを省く。長いページに。 `contain-intrinsic-size` で仮の高さを与えないとスクロールバーが跳ねる。 |
| `contain: layout paint` | 中の変更が外に影響しないと宣言し、やり直しの範囲を狭める。 |
| `transform` でアニメーション | 位置を `left` ではなく `translate` で動かす。合成だけで済む。 |
| アニメーションに `height` を使わない | 毎フレームレイアウトが走る。レイアウトを避けたいなら `transform: scale` で開閉する。中身の高さが決まらないときの `grid-template-rows: 0fr → 1fr` は書きやすいが、これもレイアウトが走るので、中の要素が少ない箇所に限って使う。 |

確認は DevTools の Performance パネル。紫（Layout）が細かく何本も並んでいたらスラッシング、Rendering タブの「Paint flashing」で再ペイント範囲が光る。

## 関連メモ

[Core Web Vitals](https://memo.taka1156.site/md/web-performance.md) [UI 更新の3つの方式](https://memo.taka1156.site/md/reactivity-models.md) [CSS レイアウト](https://memo.taka1156.site/md/css-layout.md) [JS ランタイム比較](https://memo.taka1156.site/md/js-runtimes.md)

## 参考

- [MDN: ブラウザーはどのように動作するか](https://developer.mozilla.org/ja/docs/Web/Performance/Guides/How_browsers_work)
- [web.dev: Rendering performance](https://web.dev/articles/rendering-performance)
- [HTML Standard: script の async / defer](https://html.spec.whatwg.org/multipage/scripting.html#attr-script-defer)
