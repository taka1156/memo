<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Core Web Vitals

> LCP・INP・CLS の意味と基準値、それぞれを分解して遅い原因を見つける方法、画像・フォント・JS の具体的な改善策と、ラボデータとフィールドデータの違いを図解。

- URL: https://memo.taka1156.site/web-performance.html
- タグ: フロントエンド, JavaScript
- 日付: 2026-11-03

---

「表示が速いか・反応が速いか・ズレないか」を 3 つの数字で測って直す

**ざっくり言うと**

- **LCP** （一番大きい要素が表示されるまで）・ **INP** （操作してから画面が反応するまで）・ **CLS** （レイアウトのズレ）の 3 つ。実ユーザーの **75 パーセンタイル** で判定する。
- 数字が悪いときは分解する。LCP は「TTFB・リソース読み込みの遅延・リソースの読み込み時間・要素のレンダリングの遅延」の 4 つ、INP は「待ち・処理・描画」の 3 つのどこが長いかを見る。
- Lighthouse（ラボ）は手元の 1 回の計測、CrUX や RUM（フィールド）は実ユーザーの集計。 **合否はフィールドで決まる** 。INP は操作しないと出ないので、読み込むだけのラボ計測では測れない。

## 3 つの指標と基準値

### LCP

Largest Contentful Paint

画面内で一番大きい画像やテキストブロックが描かれた時刻。「メインの中身が見えた」の代わり。

良好 2.5s 4.0s 不良

### INP

Interaction to Next Paint

クリック・タップ・キー入力から、次に画面が描かれるまで。ページ滞在中の操作のうちほぼ最悪のもの。

良好 200ms 500ms 不良

### CLS

Cumulative Layout Shift

予期しないレイアウトのズレの大きさ。ズレた面積 × 移動距離の割合で、一番ひどいまとまり（5 秒の窓）の合計。

良好 0.1 0.25 不良

ユーザー操作の直後 0.5 秒以内のズレ（アコーディオンを開いたなど）は CLS に数えない。INP は 2024 年に FID（最初の入力の待ち時間だけを測る指標）を置き換えた。

## 判定してみる

実ユーザーの値を動かしてみる。3 つとも 75 パーセンタイルで「良好」なら合格。

LCP

INP

CLS

（元のページで操作できます → https://memo.taka1156.site/web-performance.html#judge）

## LCP を分解する

TTFB

読み込み開始の遅れ

読み込み時間

描画の遅れ

| 部分 | 長いときの原因 | 対策 |
| --- | --- | --- |
| TTFB（最初のバイトまでの時間） | サーバー処理・DB・距離・リダイレクト | CDN キャッシュ、HTML のストリーミング、リダイレクトをなくす |
| 読み込み開始の遅れ（リソース読み込みの遅延） | LCP 画像が CSS 背景や JS で後から入る、 `loading="lazy"` が付いている | `<img>` で HTML に直接書く、 `fetchpriority="high"` 、必要なら `preload` |
| 読み込み時間（リソースの読み込み時間） | 画像が重い・大きすぎる | AVIF / WebP、 `srcset` と `sizes` で画面に合ったサイズ |
| 描画の遅れ（要素のレンダリングの遅延） | レンダリングをブロックする CSS / JS、Web フォント待ち、クライアント描画 | 重要な CSS を小さく、JS は defer、SSR / SSG |

```
<!-- LCP になるヒーロー画像：遅延読み込みしない・優先度を上げる・サイズを予約する -->
<img src="hero-1200.avif"
     srcset="hero-600.avif 600w, hero-1200.avif 1200w"
     sizes="(max-width: 600px) 100vw, 1200px"
     width="1200" height="600" fetchpriority="high" alt="…">

<!-- それ以外の画面外の画像 -->
<img src="card.avif" width="400" height="300" loading="lazy" decoding="async" alt="…">
```

## INP を分解する

入力の遅延

処理時間

表示の遅延

- **入力の遅延** ：クリックした時点で別の JS（読み込み直後のハイドレーション、計測タグなど）が走っていて待たされる。→ ロングタスクを減らす、サードパーティを遅らせる。
- **処理時間** ：イベントハンドラーそのものが重い。→ 見た目の更新だけ先にして、重い処理は後回し。
- **表示の遅延** ：更新した DOM が大きく、スタイル・レイアウトに時間がかかる。→ DOM を小さく、 `content-visibility` 。

```
// 先に「押された」表示を描かせてから、重い処理を続ける
button.addEventListener('click', async () => {
  button.classList.add('loading');        // 1. 見た目をすぐ変える
  await yieldToMain();                    // 2. ここで一度ブラウザに描画させる
  runHeavyFilter();                       // 3. 重い処理
});

function yieldToMain() {
  if (globalThis.scheduler?.yield) return scheduler.yield();   // 対応ブラウザ
  return new Promise(r => setTimeout(r, 0));
}
```

## CLS の主な原因

サイズのない画像・動画・iframe

`width` / `height` 属性か CSS の `aspect-ratio` で場所を確保する。CSS で `width:100%; height:auto` にしても属性の比率は使われる。

後から差し込む広告・バナー

出る場所に `min-height` を確保しておく。上に差し込まず、下か重ねて表示する。

Web フォントの切り替え

代替フォントと字幅が違うと行が折り返し直される。 `size-adjust` などで代替フォントの字幅を合わせる、重要なフォントは `preload` 。

レイアウトを動かすアニメーション

`top` や `margin` を動かすとズレとして数えられる。 `transform` で動かす。

## ラボとフィールド

|  | ラボ（Lighthouse・DevTools） | フィールド（CrUX・RUM） |
| --- | --- | --- |
| 誰の値 | 自分の端末・決めた回線での 1 回 | 実ユーザー全体の分布（28 日間など） |
| INP | 読み込むだけの計測では出ない（代わりに TBT）。DevTools の Local metrics や Lighthouse の timespan モードなら、自分で操作した分だけ測れる | 測れる |
| 向いている用途 | 原因の調査、修正前後の比較、CI での退行検知 | 合否の判定、本当に困っているページ・端末の特定 |

```
// 自前で実ユーザーの値を集める（web-vitals ライブラリ）
import { onLCP, onINP, onCLS } from 'web-vitals/attribution';
const send = (m) => navigator.sendBeacon('/rum', JSON.stringify({
  name: m.name, value: m.value, rating: m.rating, attribution: m.attribution,
}));
onLCP(send); onINP(send); onCLS(send);
```

`attribution` 付きで集めると、LCP の要素や 4 分割の内訳、INP を起こした操作の対象まで送れる。数字だけ集めても直す場所がわからない。

## 関連メモ

- [ブラウザのレンダリング](https://memo.taka1156.site/md/browser-rendering.md) — 描画の流れのどこが遅いか
- [レンダリング戦略](https://memo.taka1156.site/md/rendering-strategies.md) — HTML をいつ作るかで LCP が変わる
- [HTTP キャッシュ](https://memo.taka1156.site/md/http-cache.md) — 2 回目以降を速くするキャッシュ
- [HTTP/1.1・2・3 と TLS・DNS](https://memo.taka1156.site/md/web-protocols.md) — 最初のバイトが届くまでの DNS・TLS・HTTP

## 参考

- [web.dev: Web Vitals](https://web.dev/articles/vitals)
- [web.dev: Optimize LCP](https://web.dev/articles/optimize-lcp)
- [web.dev: Interaction to Next Paint](https://web.dev/articles/inp)
- [web.dev: Cumulative Layout Shift](https://web.dev/articles/cls)
- [GoogleChrome/web-vitals](https://github.com/GoogleChrome/web-vitals)
