<!-- scripts/memo.py build が自動生成。手で編集しない -->

# CSS レイアウト

> Flexbox（1 次元）と Grid（2 次元）の使い分けを触って比べられるデモつきで整理し、subgrid・コンテナクエリ・カスケードレイヤー・:has()・論理プロパティなど今どきの CSS と定番レシピをまとめる。

- URL: https://memo.taka1156.site/css-layout.html
- タグ: フロントエンド, デザイン
- 日付: 2026-11-03

---

「1 列に並べる」は Flex、「縦横の格子に置く」は Grid。あとは部品が自分の幅で決まるか

**ざっくり言うと**

- **Flexbox は 1 方向** に並べて、余った空間を分け合う。中身の大きさが主役（ナビ、ボタン列、カードの中身）。
- **Grid は縦横の格子** を先に決めて、そこに置く。枠が主役（ページ全体、カード一覧、フォーム）。
- 部品の見た目は画面幅ではなく **置かれた場所の幅** で変えたい → コンテナクエリ。CSS の上書き合戦は **カスケードレイヤー** で順位を明示して止める。

## Flexbox を触る

flex-directionrowcolumnrow-reverse justify-contentflex-startcenterspace-betweenspace-aroundflex-end align-itemsstretchflex-startcenterflex-endbaseline flex-wrapnowrapwrap 2 番目の flex0 1 auto（既定）1（余白を全部もらう）

A

B

C

D

E

```

```

枠の右下の角をドラッグすると幅を変えられる。狭くすると `nowrap` は縮んで 1 行に詰め込み、 `wrap` は折り返す。黄色い枠が「2 番目」の B。

**justify-content は主軸** （row なら横）、 **align-items は交差軸** （row なら縦）。direction を column にすると入れ替わる。 `flex: 1` は「残りを分け合う」、 `flex: 0 0 200px` は「200px 固定」。

（元のページで操作できます → https://memo.taka1156.site/css-layout.html#flex）

## Grid を触る

レイアウト ヘッダー・サイド・本文・フッター サイドなし スマホ（1 列）

head

side

main

foot

```

```

`grid-template-areas` は格子を文字で描ける。HTML の順番を変えずに配置だけ変えられるが、 **見た目の順とフォーカス・読み上げの順がずれる** とアクセシビリティ上の問題になるので、並べ替えすぎない。

（元のページで操作できます → https://memo.taka1156.site/css-layout.html#grid）

## どっちを使う？

| やりたいこと | 選ぶもの | 書き方 |
| --- | --- | --- |
| 上下左右の中央寄せ | Grid | `display:grid; place-items:center` |
| ナビの左にロゴ、右にメニュー | Flex | `display:flex; justify-content:space-between` |
| ロゴは左、メニューとボタンはまとめて右 | Flex | 右に寄せたい最初の要素に `margin-left:auto` （余りを全部その左に入れる） |
| カードを入るだけ並べて自動で折り返す | Grid | `grid-template-columns: repeat(auto-fill, minmax(220px, 1fr))` |
| フッターを画面下に固定（中身が少なくても） | Grid | `min-height:100dvh; grid-template-rows: auto 1fr auto` |
| タグを並べて折り返す（幅はまちまち） | Flex | `display:flex; flex-wrap:wrap; gap:6px` |
| カード内のボタンを下端に揃える | Flex | 縦 flex にして、ボタンに `margin-top:auto` |
| 並んだカードのタイトル・本文の高さを揃える | Grid + subgrid | カードを `grid-row: span 3; grid-template-rows: subgrid` |

`auto-fill` は列を作れるだけ作る（空列も残る）、 `auto-fit` は空列を潰して既存の列を伸ばす。アイテムが少ないときに差が出る。

## コンテナクエリ

右下の角をドラッグして枠の幅を変えると、カードが **自分の置き場所の幅** で横並びに切り替わる（画面幅は関係ない）。

**記事カード**

サイドバーに置けば縦、本文に置けば横。同じ部品のまま。

```
.card-slot { container-type: inline-size; }   /* 親を「測れる箱」にする */
@container (min-width: 380px) {
  .card { grid-template-columns: 140px 1fr; }
}
```

メディアクエリは **ページのレイアウト** （サイドバーを出すか）に、コンテナクエリは **部品** に使う。コンテナ幅に対する単位 `cqi` もある（ `font-size: clamp(1rem, 4cqi, 1.5rem)` ）。

## どのルールが勝つか（カスケード）

**1** オリジン（出どころ）と重要度（ブラウザ既定 < 作者 < 作者の !important）

**2** カスケードレイヤー（ `@layer` で後に宣言した層が勝つ。通常の宣言では、レイヤー外のスタイルがどの層よりも強い（ `style` 属性はさらに上）。ただし `!important` では順位が逆になり、先に宣言した層が勝つ）

**3** 詳細度（ID > クラス・属性・疑似クラス > 要素）

**4** 書いた順（後が勝つ）

```
@layer reset, base, components, utilities;   /* 順位をここで宣言 */

@layer components { #nav .link { color: gray; } }   /* 詳細度が高くても */
@layer utilities  { .text-red  { color: red;  } }   /* 後の層が勝つ */
```

外部ライブラリの CSS を `@import url(lib.css) layer(vendor);` で低い層に入れれば、自分のクラス 1 つで上書きでき、 `!important` 合戦が不要になる。詳細度を上げずに書くには `:where()` （詳細度 0）が便利。

## 押さえておきたい今どきの CSS

| 機能 | 何ができる |
| --- | --- |
| `:has()` | 子や後続の状態で親を選ぶ。 `.field:has(input:invalid)` でエラー時に枠を赤く、JS なし。 |
| CSS ネスト | Sass なしで `.card { &:hover { … } }` と書ける。 |
| 論理プロパティ | `margin-inline` ・ `padding-block` ・ `inset-inline-start` 。縦書きや右から左の言語でも正しく効く。 |
| `clamp()` | `font-size: clamp(1rem, 2.5vw, 1.5rem)` で最小・最大つきの可変サイズ。 |
| `dvh` / `svh` | スマホのアドレスバーの出入りを考慮した高さ。 `100vh` がはみ出す問題を避ける。 |
| `aspect-ratio` | 縦横比を保つ。動画の埋め込みや画像の場所取り（CLS 対策）に。 |
| View Transitions | 画面の切り替えをアニメーションでつなぐ。同一ドキュメント内に加え、ページ遷移でも使えるようになってきている。 |
| アンカー位置指定（anchor positioning） | ツールチップやメニューを、別の要素の位置に合わせて CSS だけで置く。2026 年 1 月の Firefox 147 で主要ブラウザがそろって対応した（Baseline）。古いブラウザも対象なら、代わりの表示を用意する。 |

## よくある誤解

✗ 誤解: Grid が出たから Flexbox はもう要らない

✓ 正しくは: 役割が違う。中身の大きさに合わせて 1 列に流す（折り返し位置も中身次第）なら Flex のほうが自然。ページ骨格は Grid、その中の部品は Flex、という組み合わせが普通。

✗ 誤解: margin で間隔を空ける

✓ 正しくは: 並びの間隔は親の `gap` で。子の margin だと先頭・末尾の余計な余白を消す工夫が要る。gap は Flex でも Grid でも使える。

✗ 誤解: z-index を大きくすれば前に出る

✓ 正しくは: z-index は同じ **重ね合わせコンテキスト** の中でしか比べられない。親に `transform` ・ `opacity < 1` ・ `position + z-index` などがあると、そこで新しいコンテキストができ、子をいくら大きくしても親の外には勝てない。

## 関連メモ

- [デザイントークン](https://memo.taka1156.site/md/design-tokens.md) — 余白・色を変数で管理する
- [コンポーネント設計](https://memo.taka1156.site/md/component-design.md) — レイアウトを部品に分ける考え方
- [ブラウザのレンダリング](https://memo.taka1156.site/md/browser-rendering.md) — どの CSS 変更がレイアウトからやり直しになるか
- [アクセシビリティ チェックリスト](https://memo.taka1156.site/md/a11y-checklist.md) — 見た目の順と Tab 順をそろえる・拡大や狭い幅でも崩さない
- [UI デザインスタイル早見表](https://memo.taka1156.site/md/ui-design-styles.md) — 見た目のスタイルの実例と CSS

## 参考

- [MDN: CSS レイアウト](https://developer.mozilla.org/ja/docs/Learn/CSS/CSS_layout)
- [MDN: コンテナークエリー](https://developer.mozilla.org/ja/docs/Web/CSS/CSS_containment/Container_queries)
- [MDN: @layer](https://developer.mozilla.org/ja/docs/Web/CSS/@layer)
- [CSS Cascading and Inheritance Level 5](https://www.w3.org/TR/css-cascade-5/)
