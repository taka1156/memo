<!-- scripts/memo.py build が自動生成。手で編集しない -->

# JS のイベントループと非同期

> コールスタック・タスクキュー・マイクロタスクキューの関係を、実行順をステップ実行で追いながら図解。await の正体、描画との関係、長いタスクの分け方、Node.js との違いまで。

- URL: https://memo.taka1156.site/event-loop.html
- タグ: JavaScript, フロントエンド
- 日付: 2026-11-04

---

シングルスレッドの JS が「同時に」いろいろできる仕組み

**ざっくり言うと**

- JS の実行は **1 本のスレッド** 。待ち時間のかかる処理（タイマー・通信）はブラウザや Node.js 側に任せ、終わったらコールバックが **キュー** に並ぶ。
- ループの 1 周は「 **タスクを 1 つ** → **マイクロタスクを全部** → （ブラウザなら） **描画** 」。Promise の `then` や `await` の続きはマイクロタスク、 `setTimeout` はタスク。
- 1 つのタスクが長いと、その間は描画もクリック処理も止まる。重い処理は **分割して譲る** か **Worker** に逃がす。

## 登場人物

CALL STACK

コールスタック

いま実行中の関数の積み重ね。ここが空にならないと、次のものは動けない。

WEB API / RUNTIME

ブラウザ・Node.js 側

タイマー、fetch、ファイル I/O などを JS の外で待つ。終わったらコールバックをキューへ。

TASK QUEUE

タスクキュー

`setTimeout` 、イベントハンドラ、メッセージ受信など。1 周に 1 つずつ取り出す。

MICROTASK QUEUE

マイクロタスクキュー

`Promise.then` 、 `await` の続き、 `queueMicrotask` 。タスクの直後に **空になるまで** 全部実行。

## ループの 1 周

**タスクを 1 つ実行** 最初のスクリプト全体も 1 つのタスク

**マイクロタスクを全部実行** 途中で追加された分も含めて空になるまで

**requestAnimationFrame** 描画する周だけ。画面更新の直前に呼ばれる

**スタイル計算・レイアウト・ペイント** ブラウザが必要と判断したとき（通常 60Hz なら約 16.7ms ごと）

**次のタスクへ** キューが空なら、何か来るまで待つ

描画は毎周ではなく、画面の更新タイミングに合わせて行われる。

## ステップ実行で順番を追う

次のコードの出力順を予想してから、ステップを進めてみる。

← 戻る

次へ →

最初から

（元のページで操作できます → https://memo.taka1156.site/event-loop.html#order）

#### CALL STACK

#### WEB API

#### TASK QUEUE

#### MICROTASK

#### CONSOLE

結果は `A D F C E B` 。 `setTimeout(…, 0)` が最後になるのは、0ms でも「次以降のタスク」になり、その前に今のタスクとマイクロタスクがすべて終わるから。

## await の正体

`async` 関数は Promise を返す関数、 `await` は「残りを `then` に登録して、いったん関数から抜ける」の書き換えと考えるとよい。

```
async function load() {
  console.log(1);
  const r = await fetch(url);
  console.log(2, r.status);
}
```

```
function load() {
  console.log(1);
  return fetch(url).then(r => {
    console.log(2, r.status);
  });
}
```

- `await` の前までは **同期的に** 実行される（上の例の `D` ）。
- `await` で止まっている間、スレッドは空いていて他のタスクが動ける。 **ブロックではなく中断** 。
- 直列に `await` を並べると待ち時間が足し算になる。独立した処理は `Promise.all([a(), b()])` で同時に待つ。

## 長いタスクは画面を止める

同じ 1.5 秒分の計算を、一気にやる場合と、細かく分けて間に譲る場合。ボールの動き（requestAnimationFrame で動かしている）を見比べる。

— fps

一気に計算（1.5 秒）

分割して計算（1.5 秒分）

ボタンを押すと計算を始める

- 50ms を超えるタスクは「長いタスク」と呼ばれ、クリックへの反応（INP）を悪化させる。
- 分割の方法: 対応ブラウザでは `await scheduler.yield()` 、なければ `await new Promise(r => setTimeout(r, 0))` でタスクを区切る。
- **マイクロタスクでは譲れない** 。 `await Promise.resolve()` を挟んでも同じタスクの続きとして空になるまで実行されるので、描画の機会は来ない。
- 本当に重い計算（画像処理・パースなど）は **Web Worker** へ。別スレッドで動き、結果は `postMessage` で受け取る（受け取りはタスク）。

[Core Web Vitals](https://memo.taka1156.site/md/web-performance.md) [ブラウザのレンダリング](https://memo.taka1156.site/md/browser-rendering.md)

（元のページで操作できます → https://memo.taka1156.site/event-loop.html#block）

## Node.js のイベントループ

考え方は同じだが、タスク側が **フェーズ** に分かれている（libuv）。

timers setTimeout / setInterval → pending 持ち越された I/O コールバック → poll I/O の完了を受け取る → check setImmediate → close close イベント ↺

※内部用の idle / prepare フェーズは省略

- 各コールバックの後に、 `process.nextTick` のキュー → Promise のマイクロタスクの順で空にする。CommonJS では **nextTick が Promise より先** 。ただし ES Modules ではモジュール本体がマイクロタスクとして動いているため、同期処理の中で登録した Promise / `queueMicrotask` の方が先になる。
- メインのスクリプトから呼んだ `setTimeout(fn, 0)` と `setImmediate` の順は不定。I/O コールバックの中からなら `setImmediate` が必ず先。
- 同期 API（ `fs.readFileSync` など）や重い JSON 処理は、サーバー全体のリクエスト処理を止める。

[JS ランタイム比較](https://memo.taka1156.site/md/js-runtimes.md)

## よくある誤解

✗ `setTimeout(fn, 0)` はすぐに実行される

✓ 早くても「今のタスクとマイクロタスクが全部終わった後」。入れ子が深くなると最低 4ms に切り上げられ、バックグラウンドのタブではさらに間引かれる。

✗ async 関数にすれば別スレッドで並列に動く

✓ 同じスレッドで、待ち時間の間に他の処理を進めるだけ。CPU を使う計算は速くならない（Worker が必要）。

✗ DOM を書き換えた直後に画面へ反映されている

✓ 画面に出るのは、今のタスクとマイクロタスクが終わった後の描画タイミング。ただし直後に `offsetHeight` などを読むと、レイアウトだけはその場で強制的に計算される。
