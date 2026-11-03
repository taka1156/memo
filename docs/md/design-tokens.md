<!-- scripts/memo.py build が自動生成。手で編集しない -->

# デザイントークン

> 色・余白・文字サイズなどの決定を名前付きの変数（デザイントークン）で管理する考え方を、3 階層の構造・CSS 変数での実装・テーマ切り替えのデモで説明する

- URL: https://memo.taka1156.site/design-tokens.html
- タグ: デザイン, フロントエンド
- 日付: 2026-11-03

---

「#0077b6」ではなく「アクセント色」と呼ぶ。デザインの決定に名前をつけて一元管理する

**ざっくり言うと**

- デザイントークンは、色・余白・文字サイズ・角丸・影などの **デザイン上の決定に名前をつけた最小単位** 。コードでは CSS 変数などになる。
- 「生の値（ **プリミティブ** ）」→「意味（ **セマンティック** ）」→「部品（ **コンポーネント** ）」の 3 階層にすると、ダークモードやブランド変更が **セマンティック層の差し替えだけ** で済む。
- デザインシステム ＝ トークン ＋ コンポーネント ＋ 使い方のルール。トークンはその土台。

## 3 つの階層

上の層は下の層を参照（エイリアス）します。コンポーネントは **セマンティックだけ** を見て、生の色コードを直接知らないのがポイント。

TIER 1

### プリミティブ primitive / global

使える値の一覧（パレット）。名前は「見た目」そのもの。

--blue-500: #0077b6

--cyan-400: #00d4ff

--gray-900: #1c2230

--space-4: 16px

TIER 2

### セマンティック semantic / alias

「何に使うか」の名前。 **テーマ切り替えはこの層だけ** を差し替える。

--color-accent → blue-500

--color-text → gray-900

--color-danger → red-600

--space-inset-md → space-4

TIER 3

### コンポーネント component

特定の部品専用。必要なときだけ作る（なくてもよい）。

--button-bg → color-accent

--button-padding → space-inset-md

--card-radius → radius-md

## テーマ切り替えのデモ

下のプレビューは 3 階層の CSS 変数で組んであります。テーマを切り替えると、 **セマンティック層の対応先だけ** が変わり、部品の CSS は一切変わりません。

ライト

ダーク

別ブランド

別ブランド × ダーク

NEW

#### プランをアップグレード

部品は --button-bg や --card-bg しか知らない。色コードはどこにも書いていない。

申し込む

詳細

## CSS 変数での書き方

```
/* 1. プリミティブ：パレット。ここ以外に色コードを書かない */
:root {
  --blue-500: #0077b6;
  --cyan-400: #00d4ff;
  --gray-0:   #ffffff;
  --gray-900: #1c2230;
  --ink-0:    #0a0e14;
  --ink-800:  #cdd9e5;
  --space-2: 8px;  --space-4: 16px;
}

/* 2. セマンティック：テーマごとに対応先を変える */
:root {
  --color-bg:     var(--gray-0);
  --color-text:   var(--gray-900);
  --color-accent: var(--blue-500);
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg:     var(--ink-0);
    --color-text:   var(--ink-800);
    --color-accent: var(--cyan-400);
  }
}

/* 3. コンポーネント：セマンティックだけを参照 */
.button {
  --button-bg: var(--color-accent);
  background: var(--button-bg);
  padding: var(--space-2) var(--space-4);
}
```

ライトとダークで値を 1 行にまとめる `light-dark()` 関数も主要ブラウザで使える（ `color-scheme: light dark;` の指定が必要）。例： `--color-bg: light-dark(var(--gray-0), var(--ink-0));`

### 実例：この MEMO のトークン

このサイトの全ページも同じ考え方で、 `--bg` `--surface` `--fg` `--fg-2` `--line` `--accent` `--chip` の 7 つを基本のセマンティックトークンにし、成功・エラー・注意などの状態色（ `--c-ok` `--c-ng` `--c-warn` など）をページごとに少し足して色を決めています。ダークモードはこれらの値を差し替えているだけです（プリミティブ層は省略した、小さな構成）。

## 余白と文字サイズはスケールで決める

値を自由に書けると 13px・15px・17px…と増殖します。 **決まった段階（スケール）から選ぶ** ことで、見た目に一貫したリズムが生まれます。

**余白：4 / 8 の倍数**

`--space-1`

4px

`--space-2`

8px

`--space-3`

12px

`--space-4`

16px

`--space-6`

24px

`--space-8`

32px

`--space-12`

48px

番号を「4px の何倍か」にしておくと、間に値を足したくなっても名前が崩れない。

**文字サイズ：比率で並べる**

`--text-xs` 12px あア

`--text-sm` 14px あア

`--text-md` 16px あア

`--text-lg` 20px あア

`--text-xl` 25px あア

`--text-2xl` 31px あア

16px から約 1.25 倍ずつ（モジュラースケール）。見出しの段差が自然になる。

## 名前のつけ方

よく使われるのは「 **カテゴリ → 対象 → 種類 → 状態** 」の順に並べる形です。

color - bg - accent - hover

**良い名前**

- `--color-text-muted` （用途がわかる）
- `--color-border-danger`
- `--space-inset-md`

**避けたい名前**

- `--color-light-blue` （セマンティック層に見た目の名前。ダークで「light」が濃い色になる）
- `--color-header-2` （何が 2 なのか不明）
- `--margin-13` （スケール外の値）

## ツールとフォーマット

| やりたいこと | 手段 |
| --- | --- |
| Web だけで使う | CSS 変数を手で書く。小〜中規模ならこれで十分 |
| Tailwind CSS v4 | `@theme { --color-brand-500: …; }` と書くと、トークンがそのまま `bg-brand-500` などのクラスになる |
| iOS / Android とも共有 | トークンを JSON で 1 か所に書き、Style Dictionary などで CSS・Swift・Kotlin に変換する |
| Figma と同期 | Figma の Variables をトークンとして使い、プラグインや API で JSON に書き出す |

ツール間の共通フォーマットとして、W3C のコミュニティグループ（DTCG）が JSON の書式を定めています。 `$value` と `$type` を持ち、 `{…}` で別のトークンを参照します。

```
{
  "space": {
    "4": { "$type": "dimension", "$value": { "value": 16, "unit": "px" } }
  },
  "button": {
    "padding-x": { "$value": "{space.4}" }
  }
}
```

`"{space.4}"` が別のトークンを参照するエイリアス（JSON にはコメントを書けないので、注記はコードの外に置いています）。この書式は 2025 年 10 月に安定版（Design Tokens Format Module 2025.10）が公開されています。

## デザインシステムの中での位置

トークン（値と名前） → コンポーネント（ボタン・カード…） → パターン（フォーム・一覧画面…） ＋ ガイドライン（いつ何を使うか）

コンポーネントの作り方は [コンポーネント設計](https://memo.taka1156.site/md/component-design.md) 、色そのものの選び方は [色の基礎](https://memo.taka1156.site/md/color-basics.md) 、見た目のスタイルの種類は [UI デザインスタイル早見表](https://memo.taka1156.site/md/ui-design-styles.md) へ。

## よくある誤解

トークン ＝ CSS 変数のこと

トークンは「デザインの決定」という考え方で、CSS 変数はその出力先の 1 つ。同じトークンから Swift や Kotlin の定数、Figma の変数も作れる。

ダークモードは全コンポーネントに dark 用の色を書く

セマンティック層を差し替えれば部品側は何も変えなくてよい。部品ごとに dark を書いているなら、生の色を直接参照しているサイン。

コンポーネントトークンは全部品に必須

部品ごとに上書きしたい事情があるときだけ作る。最初はプリミティブ＋セマンティックの 2 層で十分なことが多い。

セマンティック名は見た目で付けてもよい（--color-blue など）

ブランド色が変わったら「blue なのにオレンジ」になる。セマンティック層は用途（accent・danger・muted）で名付ける。
