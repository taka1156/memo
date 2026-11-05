<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Spec Kit の流れと役割

> Spec Kit の仕様駆動開発の流れ、各コマンドと人間・AI の役割、生成ファイルを図解。

- URL: https://memo.taka1156.site/spec-kit.html
- タグ: AI
- 日付: 2026-11-01

---

GitHub 製の仕様駆動開発 (Spec-Driven Development) ツールキットを、流れ・登場人物・成果物で整理

**ざっくり言うと**

- 「いきなりコードを書かせる」代わりに、 **原則 → 仕様 → 計画 → タスク → 実装** の順に Markdown を積み上げ、AI エージェントにそれを読ませて作らせる仕組み。
- `specify` CLI は **土台づくり担当** （テンプレート・スクリプト・スラッシュコマンドを配置）。実際の各工程は AI エージェント上の `/speckit.*` コマンドで進める。
- 人間は **「何を・なぜ」を決めてレビューする係** 、AI は **文書化と実装を担う係** 。各工程の成果物がそのまま次工程の入力になる。

## 全体の流れ

基本工程 品質ゲート（推奨） オプション

0 · SETUP

0

specify init CLI

プロジェクトに Spec Kit を導入。使う AI エージェントを選ぶ。

→ `.specify/` （テンプレート・スクリプト）＋ エージェント用コマンドファイル

1 · PRINCIPLES（プロジェクトに 1 回）

1

/speckit.constitution

守るべき原則（品質・テスト方針・UX・性能など）を「憲法」として定める。

→ `.specify/memory/constitution.md`

2 · WHAT & WHY（機能ごとに繰り返す）

2

/speckit.specify

作りたいものを自然言語で伝え、ユーザーストーリー・要件・受け入れ条件にする。技術の話はまだしない。

→ 機能ブランチ ＋ `specs/001-xxx/spec.md`

3

/speckit.clarify GATE

仕様のあいまいな点を AI が質問し、回答を spec に書き戻す。

→ `spec.md` を更新（Clarifications 節）

3 · HOW

4

/speckit.plan

技術スタック・構成を伝え、実装計画に落とす。憲法に反していないかもチェック。

→ `plan.md` / `research.md` / `data-model.md` / `contracts/` / `quickstart.md`

5

/speckit.checklist OPT

要件の抜け・あいまいさを点検する独自チェックリストを作る（「要件の単体テスト」）。

→ `checklists/*.md`

4 · BREAKDOWN

6

/speckit.tasks

計画を順序付き・テスト可能なタスクに分解。依存関係と並列可能なもの（ `[P]` ）を明示。

→ `tasks.md`

7

/speckit.analyze GATE

spec / plan / tasks の食い違い・抜け・憲法違反を横断チェック（読み取り専用でレポート）。

→ 分析レポート（ファイルは書き換えない）

5 · BUILD

8

/speckit.implement

tasks.md の順にコードを書き、完了したタスクにチェックを付けていく。

→ 実装コード・テスト、 `tasks.md` の進捗

9

/speckit.taskstoissues OPT

タスクを GitHub Issues に起こしてチームで追跡する。

→ GitHub Issues

↻ 次の機能では **2 から** 繰り返す（憲法はプロジェクト共通）。最短ルートは `specify → plan → tasks → implement` 、本番向けは clarify / checklist / analyze も挟むのがおすすめ。

## 登場人物と役割

人間（開発者） 決める・レビューする

- 「何を・なぜ」を言葉にする
- 技術選定・制約を伝える
- clarify の質問に答える
- 各成果物を読んで直す／承認する

AI エージェント 書く・作る

- Claude Code / Copilot / Gemini CLI / Cursor など
- テンプレートに沿って文書を生成
- タスクに従って実装

specify CLI ＋ スクリプト 土台・段取り

- `specify init` で一式を配置
- 機能ブランチと連番フォルダを作るスクリプト
- 環境チェック ( `specify check` )

成果物（Markdown） 契約書・引き継ぎ書

- 工程間の「唯一の正解」
- 前工程の出力 = 次工程の入力
- Git でレビュー・差分管理できる

## コマンド別：誰が何をするか

constitution

specify

clarify

plan

tasks

analyze

implement

役割

以降すべての工程が従う「プロジェクトの憲法」をつくる。

人間がやること

重視する原則を伝える（例: テストファースト、ライブラリ優先、シンプルさ）。

AI がやること

原則を条文化し、関連テンプレートとの整合も確認する。

入力 → 出力

原則の指示 → `.specify/memory/constitution.md`

```
/speckit.constitution コード品質・テスト基準・UX の一貫性・
性能要件を重視する原則を作って
```

役割

「何を・なぜ作るか」を仕様書にする。技術スタックは書かない。

人間がやること

作りたいものとその目的を自然言語で説明する。

AI がやること

機能ブランチと `specs/NNN-name/` を作り、ユーザーストーリー・機能要件・受け入れ基準を書く。不明点は `[NEEDS CLARIFICATION]` で印を付ける。

入力 → 出力

要望 → `spec.md`

```
/speckit.specify 写真をアルバムに整理できるアプリ。
アルバムは日付でまとまり、ドラッグで並べ替えできる
```

役割

計画に入る前に仕様の穴をふさぐ品質ゲート。

人間がやること

AI からの質問（選択式が多い）に答える。

AI がやること

あいまいな箇所を洗い出して順に質問し、回答を spec に追記する。

入力 → 出力

`spec.md` → 更新された `spec.md`

役割

「どう作るか」を決める。仕様を技術設計に翻訳する。

人間がやること

技術スタック・アーキテクチャ・制約を伝え、計画をレビューする。

AI がやること

技術調査、データモデル、API 契約、検証手順をまとめ、憲法チェックを行う。

入力 → 出力

`spec.md` ＋ 技術方針 → `plan.md` , `research.md` , `data-model.md` , `contracts/` , `quickstart.md`

```
/speckit.plan Vite + 素の HTML/CSS/JS。画像はアップロードせず
メタデータはローカルの SQLite に保存
```

役割

計画を実行可能な作業単位に分ける。

人間がやること

粒度・順序が妥当かを確認する。

AI がやること

ユーザーストーリー単位でタスクを並べ、依存関係・並列可能 `[P]` ・対象ファイルパスを付ける。

入力 → 出力

plan 一式 → `tasks.md`

役割

実装前の最終チェック。文書同士の矛盾を見つける。

人間がやること

指摘を見て、どの文書を直すか判断する。

AI がやること

spec ⇔ plan ⇔ tasks のカバレッジ不足・重複・用語ゆれ・憲法違反をレポート（ファイルは変更しない）。

入力 → 出力

3 文書 ＋ 憲法 → 分析レポート

役割

タスクに沿って実際にコードを作る。

人間がやること

動作確認・コードレビュー・必要なら差し戻し。

AI がやること

前提チェック → タスクを順に（並列可能なものはまとめて）実装 → 完了したら `[X]` を付ける。

入力 → 出力

`tasks.md` ほか → ソースコード・テスト

（元のページで操作できます → https://memo.taka1156.site/spec-kit.html#commands）

## できあがるファイル

```
my-project/
├── .specify/
│   ├── memory/
│   │   └── constitution.md   # 憲法
│   ├── scripts/              # ブランチ作成など
│   └── templates/            # spec/plan/tasks の雛形
├── .claude/commands/         # エージェント別に配置
└── specs/
    └── 001-photo-albums/
        ├── spec.md           # 何を・なぜ
        ├── plan.md           # どう作る
        ├── research.md
        ├── data-model.md
        ├── quickstart.md
        ├── contracts/
        ├── checklists/
        └── tasks.md          # 作業リスト
```

| ファイル | 中身 | 作る工程 |
| --- | --- | --- |
| `constitution.md` | 全体の原則 | constitution |
| `spec.md` | ストーリー・要件・受け入れ基準 | specify / clarify |
| `plan.md` | 技術方針・構成・憲法チェック | plan |
| `research.md` | 技術選定の調査メモ | plan |
| `data-model.md` | エンティティと関係 | plan |
| `contracts/` | API などのインターフェース定義 | plan |
| `quickstart.md` | 動作確認シナリオ | plan |
| `tasks.md` | 順序付きタスク | tasks |

エージェント用コマンドの置き場所は選んだエージェントで変わります（Claude Code なら `.claude/commands/` など）。

## コマンド例

```
# 前提: Python 3.11+, Git, uv, AI エージェントのどれか

# 新規プロジェクトに導入（エージェントを指定）
uvx --from git+https://github.com/github/spec-kit.git specify init my-project --ai claude

# 既存ディレクトリに導入
uvx --from git+https://github.com/github/spec-kit.git specify init --here --ai claude

# 必要なツールが揃っているか確認
specify check
```

オプションやコマンド名は更新が速いので、導入時は公式リポジトリ (github/spec-kit) の README を確認してください。

## よくある誤解

specify CLI がコードを生成する

CLI は土台を配るだけ。文書化も実装も AI エージェント上のスラッシュコマンドで行う。

spec.md に技術スタックも書く

spec は「何を・なぜ」だけ。技術の話は plan で初めて出す。分けておくと技術を差し替えても仕様が残る。

一度流せば完成、文書は使い捨て

成果物が「唯一の正解」。変更は spec から直して下流に流し直すのが本来の使い方。

全コマンドを毎回使わないといけない

必須級は specify → plan → tasks → implement。clarify / checklist / analyze は規模や重要度に応じて追加する。

AI に任せればレビュー不要

各工程の間に人間のレビューを挟む前提の設計。特に spec と plan の確認が品質を左右する。
