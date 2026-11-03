<!-- scripts/memo.py build が自動生成。手で編集しない -->

# コンポーネント設計

> Atomic Design がなぜ下火になったかを踏まえ、デザイントークン・Headless UI・機能単位の配置で組む今どきの UI コンポーネント設計を図とコードで整理する

- URL: https://memo.taka1156.site/component-design.html
- タグ: 設計, デザイン, フロントエンド
- 日付: 2026-11-03

---

Atomic Design のあと —— トークン × Headless UI × 機能単位で組む

**ざっくり言うと**

- **Atomic Design** （原子・分子・有機体…）は「部品を組み合わせて画面を作る」発想を広めたが、 **粒度の分類で揉める** ・ **機能のコードが散らばる** ことから、そのままの形では使われなくなった。
- 今の主流は **「見た目（トークン）」「振る舞い（Headless UI）」「機能（feature）」を分ける** こと。キーボード操作や ARIA などの難しい部分はライブラリに任せ、見た目は自分で持つ。
- フォルダは粒度ではなく **機能ごと** に分け、本当に共通の部品だけを薄い `ui/` に置く。

## Atomic Design はなぜ下火になったか

部品を Atoms → Molecules → Organisms → Templates → Pages の 5 段階に分類する方法論。考え方自体は正しかったものの、実務では次の問題が目立ちました。

**分類で揉める**

検索ボックスは？ Molecule **?** Organism **?**

境界に正解がなく、レビューのたびに議論になる。部品が育つと別の階層へ引っ越しが必要になる。

**機能が散らばる**

「カート」の部品が atoms/ molecules/ organisms/ に分かれて置かれ、1 つの機能を直すのに 3 つのフォルダを行き来する。

**変更の理由と合わない**

分け方は「大きさ」で、変更の理由（どの機能の都合か）とは無関係。 [単一責任](https://memo.taka1156.site/md/solid.md) の観点でも筋が悪い。

残った功績：「画面をページ単位でなく部品の組み合わせとして設計する」考え方と、Storybook で部品単体を開発・確認する文化。

## 今どきの層の分け方

粒度ではなく **「何を担当するか」** で分けます。下の 2 層は外部の仕組みに任せ、上の層ほど自分のアプリ固有になります。

ページ routes / app

データを取ってきて、機能の部品を並べる。 レイアウトとデータの受け渡しだけ。

機能の部品 features/*

`CartSummary` `LoginForm` など、業務の言葉を持つ部品。 そのアプリにしかない。

UI 部品 ui/

`Button` `Dialog` `Tabs` など、業務を知らない見た目つきの部品。 Headless にスタイルを当てたもの。

振る舞い Headless UI

開閉状態・キーボード操作・フォーカス管理・ARIA 属性。 見た目は持たない。ライブラリに任せる。

見た目の値 デザイントークン

色・余白・角丸・文字サイズ。 → [デザイントークン](https://memo.taka1156.site/md/design-tokens.md)

## Headless UI とは

「見た目なしの部品」。ダイアログやタブ、メニューなどの **作るのが難しい部分（振る舞いとアクセシビリティ）だけ** を提供し、HTML 構造とスタイルは使う側が決めます。

**ライブラリが持つもの**

- 開いている／選ばれているなどの状態
- 矢印キー・Esc・Tab の操作
- フォーカスの閉じ込めと復帰（モーダル）
- `role` / `aria-*` 属性の付与
- 画面端での位置調整（ポップオーバー）

**自分が持つもの**

- HTML の構造（どこに何を置くか）
- スタイル（Tailwind・CSS Modules など何でも）
- アニメーション
- 業務のロジック

### 主なライブラリ

| ライブラリ | 対応 | 特徴 |
| --- | --- | --- |
| Radix Primitives | React | 部品の種類が多く、shadcn/ui の土台として広く使われている |
| React Aria | React | Adobe 製。アクセシビリティと国際化（日付・数値など）の作り込みが特に厚い。フック単位でも使える |
| Base UI | React | Radix・Floating UI・MUI の開発者による。2025 年 12 月に v1.0。shadcn/ui でも Radix の代わりに選べる |
| Ark UI | React / Solid / Vue / Svelte | 状態機械（Zag.js）で振る舞いを実装し、複数のフレームワークに同じ部品を提供 |
| Kobalte / Bits UI / Reka UI | Solid / Svelte / Vue | 各フレームワーク向けの代表的な選択肢 |

ネイティブ要素で足りる場面も増えている。モーダルは `<dialog>` 、ポップオーバーは `popover` 属性、開閉は `<details>` 。まずこれで足りるか考え、足りない部分だけライブラリを使う。

## コード例：Headless にスタイルを当てる

ui/Dialog

機能から使う

バリエーション

```
// ui/dialog.tsx — Radix の振る舞いに、トークンを使った見た目を当てる
import * as D from '@radix-ui/react-dialog';

export const Dialog = D.Root;
export const DialogTrigger = D.Trigger;

export function DialogContent({ title, children }: Props) {
  return (
    <D.Portal>
      <D.Overlay className="fixed inset-0 bg-black/50" />
      <D.Content className="fixed left-1/2 top-1/2 -translate-1/2
                            rounded-(--radius-lg) bg-(--color-surface) p-6">
        <D.Title className="text-lg font-bold">{title}</D.Title>
        {children}
        <D.Close aria-label="閉じる">×</D.Close>
      </D.Content>
    </D.Portal>
  );
}
// Esc で閉じる・フォーカスの閉じ込め・背景のスクロール止め・
// role="dialog" などは Radix が面倒を見る
```

```
// features/cart/components/clear-cart-button.tsx
import { Dialog, DialogTrigger, DialogContent } from '@/ui/dialog';
import { Button } from '@/ui/button';
import { useClearCart } from '../hooks/use-clear-cart';

export function ClearCartButton() {
  const clear = useClearCart();           // 業務ロジックは機能側
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="danger">カートを空にする</Button>
      </DialogTrigger>
      <DialogContent title="本当に空にしますか？">
        <Button variant="danger" onClick={clear}>空にする</Button>
      </DialogContent>
    </Dialog>
  );
}
```

`ui/` の部品は「カート」を知らない。業務の言葉が出てくるのは `features/` から。

NG：真偽値 props が増殖

```
<Button
  primary
  small
  outline
  danger      // primary と同時に true だと？
  fullWidth
  iconLeft={…}
/>
```

OK：排他的な variant と合成

```
<Button variant="danger" size="sm">
  <TrashIcon aria-hidden />
  削除
</Button>

// variant: 'primary' | 'secondary' | 'danger'
// size:    'sm' | 'md' | 'lg'
// アイコンは props でなく子要素で渡す
```

同時に成り立たない選択肢は 1 つの union 型にまとめる。中身の差し込みは props より children（合成）のほうが拡張に強い。

## 合成で作る（コンパウンドコンポーネント）

1 つの部品に設定用 props を詰め込む代わりに、 **小さな部品を組み合わせて使う** 形。Headless ライブラリの多くがこの形です。

設定オブジェクト型

```
<Tabs
  items={[
    { label: '概要', content: <A /> },
    { label: '詳細', content: <B />,
      badge: 3, disabled: false },
  ]}
  tabListClassName="…"
/>
// 要望が来るたびに props が増える
```

コンパウンド型

```
<Tabs.Root defaultValue="a">
  <Tabs.List>
    <Tabs.Trigger value="a">概要</Tabs.Trigger>
    <Tabs.Trigger value="b">
      詳細 <Badge>3</Badge>
    </Tabs.Trigger>
  </Tabs.List>
  <Tabs.Content value="a"><A /></Tabs.Content>
  <Tabs.Content value="b"><B /></Tabs.Content>
</Tabs.Root>
```

## フォルダ構成：機能ごとに置く

**粒度で分ける（Atomic 型）**

components/ atoms/ Button, PriceText … molecules/ CartItemRow, SearchBox … organisms/ CartSummary, Header … templates/ → カートの修正が 3 フォルダにまたがる

**機能で分ける（feature 型）**

ui/ Button, Dialog, Tabs（業務を知らない） features/ cart/ components/ CartSummary, CartItemRow hooks/ useCart api.ts search/ components/ SearchBox → カートの修正は cart/ の中で完結

**まず機能の中に**

新しい部品は、使う機能のフォルダに置く。

**2 か所目で様子見**

別の機能でも欲しくなったら、まずはコピーか import でしのぐ。

**3 か所目で昇格**

形が安定したら、業務の言葉を抜いて `ui/` に移す。

## 部品を「持つ」か「借りる」か

| 方式 | 例 | 良いところ | 気をつけること |
| --- | --- | --- | --- |
| パッケージを入れる | MUI、Chakra UI など | すぐ揃う。更新は npm update で入る | 見た目を大きく変えるのが大変。ライブラリの上書きと戦いがち |
| コードをコピーして持つ | shadcn/ui 方式 | 自分のリポジトリのコードなので自由に変えられる | 上流の修正は自分で取り込む。持ったコードの保守責任は自分 |
| Headless を直接使う | Radix / Ark UI ＋自前スタイル | 振る舞いは借りて、見た目は完全に自分のもの | 最初に `ui/` を作る手間がかかる |

shadcn/ui は「Headless（Radix など）＋ Tailwind のスタイル」を雛形としてコピーする仕組み。つまり上の 3 つ目を楽に始める方法とも言える。

## よくある誤解

Headless UI を使えばアクセシビリティは完璧

振る舞いと ARIA は面倒を見てくれるが、コントラスト・ラベルの文言・見出し構造・フォーカスの見た目は使う側の責任（ [チェックリスト](https://memo.taka1156.site/md/a11y-checklist.md) ）。

共通化は早いほど良い

1 か所でしか使っていない段階で汎用化すると、想像上の要件で props が膨らむ。3 か所目で形が見えてから `ui/` に上げるほうが結局速い。

Atomic Design の考え方は全部間違いだった

「部品の組み合わせで画面を作る」「部品単体で開発・確認する」は今も主流。廃れたのは 5 段階の分類とそれに沿ったフォルダ構成。

shadcn/ui はコンポーネントライブラリ

npm から部品を import して使うのではなく、コードを自分のリポジトリに書き出して所有する方式。更新も自分の判断で取り込む。
