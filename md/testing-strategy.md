<!-- scripts/memo.py build が自動生成。手で編集しない -->

# テスト戦略

> 静的チェック・単体・結合・E2E の役割分担と、場面ごとにどの層で書くかを選べるデモ、Vitest・Testing Library・Playwright・MSW の使いどころ、モックの境界、E2E の不安定さ（flaky）対策、ビジュアルリグレッションを図解。

- URL: https://memo.taka1156.site/testing-strategy.html
- タグ: 開発ツール, JavaScript, 設計
- 日付: 2026-11-03

---

「速くて安い層で大半を、遅くて高い層で要所だけ」を、何を守りたいかから決める

**ざっくり言うと**

- テストは **速く安く・壊れにくい** ほど数を書ける。型チェックとリンター → 単体 → 結合 → E2E の順に遅く・高く・不安定になる。
- フロントエンドでは「関数単体」より **部品をユーザーと同じ操作で動かす結合テスト** が費用対効果が高い。E2E は **お金や登録に関わる主要な流れだけ** に絞る。
- モックは **境界（ネットワーク・時刻・乱数）** で差し替える。自分のコードの内部をモックすると、テストは通るのに本番で壊れる。

## 層の形：ピラミッドとトロフィー

テストピラミッド

E2E 少し

結合 中くらい

単体 たくさん

テスティングトロフィー

E2E 少し

結合 いちばん多く

単体 ロジックだけ

静的 型・リンターで常に

ピラミッドは「単体を一番多く」。トロフィーは UI 開発向けに、 **部品同士を組み合わせた結合テストを主役** にし、土台に型とリンターを置く。どちらも「上ほど少なく」は同じで、違うのは **何を一番厚くするか** 。純粋な計算が多いライブラリはピラミッド、画面が中心のアプリはトロフィーに寄る。

## 各層が捕まえるもの

| 層 | 捕まえるバグ | 速さ | 主な道具 |
| --- | --- | --- | --- |
| 静的 | 型の不一致、未定義の変数、使っていない import、危険な書き方 | 保存するたび | TypeScript、ESLint / Oxlint |
| 単体 | 計算・変換・判定のロジックの誤り、境界値 | 1 件ミリ秒 | Vitest |
| 結合 | 部品の組み合わせ、表示とイベント、API 応答の扱い | 1 件数十〜数百ミリ秒 | Vitest ＋ Testing Library、MSW |
| E2E | 本物のブラウザ・サーバー・DB を通した流れ、ルーティング、認証 | 1 件数秒〜 | Playwright |
| 見た目 | CSS の崩れ、意図しない見た目の変化 | 1 件数秒 | Playwright のスクリーンショット比較など |

## どの層で書く？

守りたいものを選ぶと、書くべき層と理由が出る。

税込み価格と端数処理の計算

フォームのエラー表示と送信ボタンの無効化

一覧画面が API の空・エラー・遅延で正しく表示されるか

ログイン → カート → 購入完了の流れ

ボタンのデザインが崩れていないか

外部の決済サービスとの連携

API の型が変わったときに画面が追従しているか

（元のページで操作できます → https://memo.taka1156.site/testing-strategy.html#pick）

## 道具の使いどころ

Vitest

Testing Library

MSW

Playwright

```
import { describe, it, expect } from 'vitest';
import { priceWithTax } from './price';

describe('priceWithTax', () => {
  it.each([
    [100, 110], [99, 108], [0, 0],     // 端数と境界値を表で並べる
  ])('%i 円 → %i 円', (base, want) => {
    expect(priceWithTax(base)).toBe(want);
  });
});
```

Vite の設定をそのまま使えるテストランナー。DOM が必要なテストは jsdom / happy-dom（Node.js 上の疑似 DOM）で速く回すか、 **ブラウザモード** で本物のブラウザ上で動かす。疑似 DOM はレイアウトを計算しないので、サイズや表示位置に依存するテストはブラウザモードか E2E で。

```
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

it('メールが空なら送信できない', async () => {
  render(<SignupForm />);
  const submit = screen.getByRole('button', { name: '登録' });
  await userEvent.click(submit);
  expect(screen.getByRole('alert')).toHaveTextContent('メールを入力してください');
  expect(submit).toBeDisabled();
});
```

**ユーザーと同じ手がかりで要素を探す** （役割と名前、ラベル、表示テキスト）。クラス名や内部の state を見ないので、見た目の実装を変えてもテストが壊れない。 `getByRole` で見つからないなら、スクリーンリーダーにも見つけにくい部品になっているというアクセシビリティの警告にもなる。

```
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  http.get('/api/items', () => HttpResponse.json([{ id: 1, name: 'りんご' }])),
);
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

it('API が 500 ならエラー表示', async () => {
  server.use(http.get('/api/items', () => new HttpResponse(null, { status: 500 })));
  render(<ItemList />);
  expect(await screen.findByRole('alert')).toBeVisible();
});
```

**ネットワークの境界でモックする** 道具。 `fetch` 関数や API クライアントを差し替えるのではなく、リクエストを横取りして応答を返すので、アプリのコードは本番と同じ経路を通る。同じハンドラーをテスト・Storybook・開発中のブラウザで使い回せる。

```
import { test, expect } from '@playwright/test';

test('購入できる', async ({ page }) => {
  await page.goto('/products/1');
  await page.getByRole('button', { name: 'カートに入れる' }).click();
  await page.getByRole('link', { name: 'カート' }).click();
  await page.getByRole('button', { name: '購入する' }).click();
  await expect(page.getByRole('heading', { name: 'ご注文ありがとうございます' })).toBeVisible();
});
```

Chromium・Firefox・WebKit を操作する E2E ツール。 `expect(...).toBeVisible()` などは **条件を満たすまで自動で待つ** ので、固定時間の待ちが要らない。失敗時のトレース（操作ごとの DOM・ネットワーク・スクリーンショット）で原因を追える。

（元のページで操作できます → https://memo.taka1156.site/testing-strategy.html#tools）

## 何をモックするか

差し替えてよい（境界）

- 外部 API・決済・メール送信（MSW、テスト用の口座）
- 時刻（ `vi.useFakeTimers()` ・ `vi.setSystemTime()` ）
- 乱数・ID 生成
- 遅い・お金がかかる・副作用が外に出るもの

差し替えない（内部）

- 自分で書いた子コンポーネントやフック
- 同じアプリ内のサービス関数
- 状態管理ライブラリ
- 「呼ばれた回数」の検証だけで終わるテスト

内部をモックすると、テストは「実装がこう呼んでいる」ことを確かめるだけになり、リファクタリングのたびに壊れるのに、本当の不具合（組み合わせたときのズレ）は見逃す。DB は可能なら **本物を使い捨てで** （Docker のコンテナ、SQLite のメモリ DB、テストごとのトランザクションのロールバック）。

## E2E が不安定になる原因と対策

| 原因 | 症状 | 対策 |
| --- | --- | --- |
| 固定時間の待ち | `waitForTimeout(1000)` が遅い CI で足りない | 表示や URL など 状態を待つ アサーションにする |
| テスト間でデータを共有 | 実行順や並列化で結果が変わる | テストごとにユーザー・データを作る。API で下準備し、UI 操作は確かめたい部分だけ |
| 壊れやすいセレクタ | クラス名やデザイン変更で落ちる | 役割と名前（ `getByRole` ）、最後の手段で `data-testid` |
| 外部サービス | 相手の障害や遅延で落ちる | E2E では外部をスタブにし、本物との接続は別の少数のテストで |
| アニメーション・時刻 | 途中の状態を掴む、日付で表示が変わる | アニメーションを止める設定、時刻を固定する |

CI での自動リトライは **応急処置** 。リトライで通ったテストは flaky として記録し、原因を直す。放置すると「赤くても気にしない」文化になり、本物の失敗も見逃す。

## 見た目のテスト（ビジュアルリグレッション）

```
await expect(page).toHaveScreenshot('pricing.png', { maxDiffPixelRatio: 0.01 });
```

前回承認した画像と比べて、差分があれば失敗させる。CSS の変更が **意図しない別の画面** を崩していないかを見つけるのに強い。

OS やフォントの違いで 1px ずれるだけで差分が出るので、 **基準画像の作成と比較を同じ環境（CI のコンテナ）で** 行う。日付・広告・アニメーションなど毎回変わる部分は隠すか固定する。画面全体より、部品単位（Storybook のストーリーごと）で撮るほうが差分の原因を追いやすい。

## CI での回し方

1. **静的チェック** 型チェックとリンター。数十秒で終わり、一番多くのミスを止める。
2. **単体・結合** 変更のあったパッケージだけ実行できると速い。並列で回す。
3. **E2E（主要な流れ）** プレビュー環境にデプロイしたものに対して実行。ブラウザ・シャードで並列化。
4. **見た目** 差分が出たら人が確認して承認する（自動で基準を更新しない）。

## よくある誤解

✗ 誤解: カバレッジ 100% なら安心

✓ 正しくは: カバレッジは「実行された行」であって「確かめた振る舞い」ではない。アサーションのないテストでも上がる。下限の目安（急に下がったら気づく）には使えるが、目標にすると意味の薄いテストが増える。

✗ 誤解: E2E で全部確かめれば単体テストは要らない

✓ 正しくは: E2E は遅く、組み合わせの数を網羅できない（端数処理の 20 パターンを画面から入力するのは非現実的）。失敗しても原因の場所がわかりにくい。細かい分岐は下の層で。

✗ 誤解: スナップショットテストで UI を守れる

✓ 正しくは: HTML の文字列スナップショットは差分が大きく、レビューされずに更新されがち。守りたい振る舞い（表示される文言、無効になるボタン）を直接アサーションするほうが壊れにくく意図も伝わる。

## 関連メモ

- [Vite ツールチェーン図解](https://memo.taka1156.site/md/vite-toolchain.md) — Vitest を動かす Vite のパイプライン
- [アクセシビリティ チェックリスト](https://memo.taka1156.site/md/a11y-checklist.md) — 自動テストで拾えるアクセシビリティ
- [GitHub サービス](https://memo.taka1156.site/md/github-services.md) — CI でテストを回す Actions
- [REST・GraphQL・gRPC・tRPC](https://memo.taka1156.site/md/api-styles.md) — テストの前提になる API の契約（OpenAPI・スキーマ・型）
- [JS のモジュールと依存管理](https://memo.taka1156.site/md/js-modules.md) — テスト対象が読み込むモジュールの仕組み（ESM・exports の解決）
- [DDD とオニオンアーキテクチャ](https://memo.taka1156.site/md/ddd-onion.md) — 依存の向きでテストしやすくする

## 参考

- [Vitest: Guide](https://vitest.dev/guide/)
- [Vitest: Browser Mode](https://vitest.dev/guide/browser/)
- [Testing Library: Guiding Principles](https://testing-library.com/docs/guiding-principles)
- [Testing Library: クエリの優先順位](https://testing-library.com/docs/queries/about#priority)
- [Mock Service Worker](https://mswjs.io/docs/)
- [Playwright: Best Practices](https://playwright.dev/docs/best-practices)
- [Playwright: Visual comparisons](https://playwright.dev/docs/test-snapshots)
- [The Testing Trophy and Testing Classifications](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications)
