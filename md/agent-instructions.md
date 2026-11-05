<!-- scripts/memo.py build が自動生成。手で編集しない -->

# CLAUDE.md / AGENTS.md / Skills

> AI コーディングエージェントへの指示ファイルと Skills の違いを、コンテキストに載るタイミングと置き場所から図解。

- URL: https://memo.taka1156.site/agent-instructions.html
- タグ: AI
- 日付: 2026-11-02

---

AI エージェントに「何を・いつ」読ませるかの設計

**ざっくり言うと**

- エージェントへの追加情報は「 **常に読む指示** 」「 **必要なときだけ読む手順** 」「 **外部とつなぐ道具** 」の3種類
- それぞれ **CLAUDE.md・AGENTS.md** 、 **Skills** 、 **MCP** が担当する
- 違いの本質は、限られたコンテキスト（作業記憶）に **いつ・どれだけ載るか** 。常に載るものほど短くする

## 3つの役割

### CLAUDE.md / AGENTS.md

**常に読む指示**

セッション開始時に毎回読み込まれる「このプロジェクトの決まりごと」。ビルド方法、規約、やってはいけないこと。

### Skills

**必要なときだけ読む手順書**

普段は名前と説明だけが見えていて、該当する作業になったときに本文や同梱スクリプトを読む。

### MCP

**外部とつなぐ道具**

GitHub、Slack、DB など外部システムを操作するツール群。 [MCP のメモ](https://memo.taka1156.site/md/mcp.md) で詳しく扱う。

## コンテキストに載るタイミング

ボタンで場面を切り替えると、コンテキストの中身がどう変わるかがわかる（幅は大まかなイメージ）。

システム

CLAUDE.md

説明

MCP ツール定義

SKILL.md 本文

同梱ファイル

会話・作業

システムプロンプト 指示ファイル（常駐） Skill の name / description（常駐・小さい） MCP のツール定義（常駐） Skill 本文・同梱ファイル（必要時のみ） 会話・作業に使える残り

① 会話開始

② スキルが該当

③ 同梱ファイルも読む

CLAUDE.md と MCP のツール定義は **毎回** 場所を取る。CLAUDE.md を長くしたり MCP サーバーを入れすぎたりすると、肝心の作業に使える領域が減り、指示も埋もれる。

（元のページで操作できます → https://memo.taka1156.site/agent-instructions.html#context）

## CLAUDE.md

書くもの

- ビルド・テスト・lint のコマンド
- コードを読んでもわからない規約や判断基準
- ハマりどころ（「この API は v1 を使う」など）
- やってはいけないこと

書かないもの

- コードを読めばわかること（ディレクトリ構成の丸写しなど）
- linter やフォーマッターが強制できること
- 特定の作業でしか要らない長い手順（→ Skill へ）
- 秘密情報（リポジトリにコミットされる）

### 置き場所と読み込まれ方（Claude Code）

ユーザー全体 `~/.claude/CLAUDE.md` — 全プロジェクト共通の個人の好み

プロジェクト `./CLAUDE.md` — リポジトリにコミットしてチームで共有。起動したフォルダから上にたどって読む

サブフォルダ `packages/api/CLAUDE.md` など — そのフォルダのファイルを扱うときに追加で読まれる

取り込み 本文中の `@docs/style.md` のような記述で、別ファイルを読み込める

`/init` でリポジトリを解析して雛形を作れる。生成されたものは長くなりがちなので、削る前提で使う。

## AGENTS.md

特定のツールに依存しない、 **エージェント向け README** の共通フォーマット。中身はただの Markdown で、決まった項目はない。OpenAI の Codex から広まり、今は Linux Foundation 傘下の Agentic AI Foundation が管理している。Cursor、GitHub Copilot など多くのツールが読む。

**Claude Code の扱い** ：バージョン 2.1.277（2026年9月）から、フォルダに **CLAUDE.md がないときに限り AGENTS.md を読む** ようになった。どちらを読むかは `/config` で変えられる。

### 両方使うときの3パターン

AGENTS.md だけ

CLAUDE.md から取り込む

シンボリックリンク

CLAUDE.md を置かず、AGENTS.md に一本化する。Claude Code はフォールバックで読む。

一番シンプル。ただし、フォールバックは機能フラグ経由で有効になるため、Bedrock / Vertex 経由やテレメトリ無効の環境では効かないことがある。

```
# CLAUDE.md
@AGENTS.md

## Claude Code 固有
- サブエージェントで探索してから編集する
```

共通部分は AGENTS.md、Claude 固有の追記だけ CLAUDE.md に書く。どの環境でも確実に読まれる。

```
ln -s AGENTS.md CLAUDE.md
```

中身は完全に同じになる。Windows では扱いに注意。

（元のページで操作できます → https://memo.taka1156.site/agent-instructions.html#agents-md）

### ツールごとの指示ファイル

| ツール | 主な指示ファイル |
| --- | --- |
| Claude Code | `CLAUDE.md` （なければ `AGENTS.md` ） |
| OpenAI Codex | `AGENTS.md` |
| GitHub Copilot | `.github/copilot-instructions.md` 、 `AGENTS.md` |
| Cursor | `.cursor/rules/` 、 `AGENTS.md` |
| Gemini CLI | `GEMINI.md` |

## Skills

フォルダ1つが1スキル。中心の `SKILL.md` に、YAML のフロントマター（名前と説明）と本文（手順）を書く。2025年12月に **Agent Skills** としてオープン標準化され（agentskills.io）、Claude Code 以外に Codex、Copilot、Cursor、Gemini CLI なども対応している。

memo-style/ ├── SKILL.md # 必須。フロントマター＋手順 ├── template.html # 同梱ファイル。本文から参照されたときだけ読む └── scripts/ └── check.py # 実行するだけなら中身はコンテキストに載らない

```
---
name: memo-style
description: MEMO リポジトリ用の解説ページを新しく作るときのデザイン規約。
  「〜の図解ページを作って」と言われたときに必ず読む。
---

# memo-style
1. テンプレートから作る: python3 scripts/memo.py new NAME
2. ...
```

### 段階的な読み込み（progressive disclosure）

1

**name と description**

起動時に全スキル分が常駐。数行なので、何十個あっても軽い。

2

**SKILL.md 本文**

description から「今の作業に該当する」と判断されたときに読む。

3

**同梱ファイル**

本文の指示で必要になったものだけ読む・実行する。

**description がスイッチ** になっている。「何をするか」だけでなく「 **どんな頼まれ方をしたときに使うか** 」まで書かないと、呼ばれるべき場面で呼ばれない。

### 置き場所

| 場所 | 範囲 |
| --- | --- |
| `.claude/skills/` | プロジェクト（コミットして共有） |
| `~/.claude/skills/` | 個人（全プロジェクト） |
| プラグイン | 配布用。組織でまとめて配れる |
| `.agents/skills/` | ツール横断で使われ始めている共通の置き場所 |

### 実例：この MEMO

このサイト自体がスキルで運用されている。リポジトリの `.claude/skills/` に **memo-style** （デザイン規約とテンプレート）、 **memo-publish** （登録手順）、 **memo-from-chat** （会話をページ化）の3つがあり、claude.ai 側の入口スキルが毎回リポジトリから最新の規約を取りに行く。規約を1か所で管理し、どこから頼んでも同じ見た目になる。

## どれを使うか

| やりたいこと | 使うもの |
| --- | --- |
| どの作業でも毎回守ってほしい決まり | CLAUDE.md / AGENTS.md |
| 特定の作業のときだけ要る手順・テンプレート・スクリプト | Skill |
| 外部システムを読み書きしたい | MCP |
| 「編集後は必ず formatter」のように、AI の判断に任せず確実に実行したい | Hooks |
| 調査などを本筋のコンテキストから切り離して任せたい | サブエージェント |

指示ファイルや Skill は「お願い」なので、守られないこともある。絶対に実行させたいことは Hooks のような仕組み側で強制する。

## よくある誤解

✕ 「CLAUDE.md に全部書いておけば安心」

○ 長いほど毎回のコンテキストを圧迫し、大事な指示が埋もれる。特定作業の手順は Skill に逃がし、CLAUDE.md は短く保つ。

✕ 「Skill と MCP は同じようなもの」

○ Skill は **知識と手順** 、MCP は **外部への接続** 。「Slack のツールを使って、チームの週報フォーマットで投稿する」なら、両方を組み合わせる。

✕ 「AGENTS.md は OpenAI 製品専用」

○ ツール中立の共通フォーマットで、Claude Code も CLAUDE.md がなければ読む。

## 関連メモ

[← MCP の仕組み](https://memo.taka1156.site/md/mcp.md)
