<!-- scripts/memo.py build が自動生成。手で編集しない -->

# OpenTofu 概念図

> 設定ファイル(.tf)からState・Providerを経てインフラに反映されるまでの流れと、役割ごとのファイル名を図解。

- URL: https://memo.taka1156.site/opentofu.html
- タグ: インフラ
- 日付: 2026-11-01

---

設定ファイルから State・Provider を経てインフラに反映されるまでの流れと、役割ごとのファイル名の対応

**ざっくり言うと**

- `*.tf` ファイル（設定）に「あるべき状態」を書く。手順ではなく結果を書く点が Ansible と違う
- `tofu plan` は State（前回の実行結果の記録）と設定を比べて変更点だけを洗い出す
- 実際のクラウド API を叩くのは Provider（プラグイン）。 `tofu apply` が Provider 経由でインフラに反映する

## 概念図

青＝自分で書く定義ファイル、緑＝実行時の処理ステップ、紫＝State（実行結果の記録）、黄＝外部との接続。破線は参照・取り込みを表す。

（図: 設定ファイル（*.tf / HCL） / Managed Infrastructure（クラウド上の実体） / Local / CI 環境 / tofu コマンドを実行 / Provider 設定 / 使う API・バージョンの宣言 / Resource / 作りたいインフラの定義 / Variables / 入力値 / Module / Resource のまとめ・再利用 / tofu init / Provider・Module を取得 / tofu plan / 設定と State の差分を計算 / tofu apply / 差分を実行 / State / 現在管理している実体の記録 / Provider Plugin / クラウド API を実際に呼ぶ / Resource A / Resource B / 読み込む / 実行 / module で呼ぶ / var. / 参照される / 読み込み / 差分の比較 / 実行させる / 結果を保存 / API 呼び出し → https://memo.taka1156.site/opentofu.html#overview）

定義ファイル 実行ステップ State（記録） 外部との接続 破線＝参照・取り込み

## 役割ごとのファイル名

ファイル名は 1 ファイルにまとめても動くが、慣例として役割ごとに分けることが多い。同じディレクトリ内の `.tf` ファイルはすべてまとめて 1 つの「設定」として読み込まれる。

| 概念 | 種別 | ファイル / 場所 | 役割 |
| --- | --- | --- | --- |
| Terraform Block 全体設定 | 設定 | `versions.tf` | OpenTofu 自体のバージョン制約、 `required_providers` （使う Provider とそのバージョン）を書く。 |
| Provider 設定 | 定義 | `providers.tf` | どの Provider をどの認証情報・リージョンで使うか（ `provider "aws" { region = ... }` ）。 |
| Resource | 定義 | `main.tf` | 作りたいインフラの「あるべき状態」。 `resource "aws_instance" "web" { ... }` のように書く。 |
| Variables 入力値 | 定義 | `variables.tf` | `variable "name" { type = ... }` で入力項目を宣言する（値そのものではなく器）。 |
| Variables 値 | 定義 | `terraform.tfvars` `*.auto.tfvars` | variables.tf で宣言した変数に実際の値を入れる。環境ごとに分けられる。 |
| Outputs | 定義 | `outputs.tf` | apply 後に表示・他の仕組みから参照したい値（IP アドレスなど）を定義する。 |
| Locals | 定義 | `locals.tf` | 設定内だけで使う計算済みの値。変数のように外からは渡せない。 |
| Module | 定義 | `modules/<名前>/` | Resource 群をひとまとめにした再利用部品。自前でも Registry 公開のものでも可。 |
| Backend 設定 | 接続 | `backend.tf` | State をどこに保存するか（ `backend "s3" { ... }` など）。チームで共有する場合は必須。 |
| State | 記録 | `terraform.tfstate` | 最後に apply した時点の実体の記録。手で編集しない。Backend 未設定時はローカルに作られる。 |
| Lock File 依存関係 | 設定 | `.terraform.lock.hcl` | init 時に決まった Provider の正確なバージョンを固定する。Git にコミットする。 |
| キャッシュ | 生成物 | `.terraform/` | init でダウンロードされた Provider 本体・Module の実体。 `.gitignore` に入れる。 |

## ディレクトリ構成例

構成

main.tf

variables.tf

```
project/
├── versions.tf           # OpenTofu / Provider バージョン
├── providers.tf          # Provider 設定
├── backend.tf            # State の保存先
├── main.tf                # Resource 定義
├── variables.tf          # 入力変数の宣言
├── outputs.tf             # 出力値
├── locals.tf               # 内部変数
├── terraform.tfvars      # 変数の値
├── .terraform.lock.hcl  # 依存バージョンの固定
├── .terraform/            # init の生成物（Git 管理外）
└── modules/
    └── web-server/
        ├── main.tf
        ├── variables.tf
        └── outputs.tf
```

```
# main.tf
resource "aws_instance" "web" {
  ami           = "ami-0abcd1234"
  instance_type = var.instance_type   # variables.tf を参照

  tags = {
    Name = "server-${var.env}"
  }
}
```

```
# variables.tf（器の宣言）
variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "env" {
  type = string
}

# terraform.tfvars（実際の値）
env = "staging"
```

（元のページで操作できます → https://memo.taka1156.site/opentofu.html）

## 各要素の考え方

### Resource 何を作るか

手順ではなく「こうあってほしい」という結果を宣言する（宣言的）。同じ Resource ブロックを何度 apply しても、既に望む状態ならなにも変わらない。

### State 今の状態の記録

OpenTofu が「前回自分が何を作ったか」を知っている唯一の手がかり。plan はこの State と設定ファイルを比較して差分を出す。壊れたり他人と競合したりすると大きな事故につながるため、チームでは Backend（S3 など）で共有しロックをかける。

### Provider 誰が実行するか

AWS・GCP・Azure など、クラウドごとの API 呼び出しを引き受けるプラグイン。 `init` でダウンロードされ、 `apply` 時に実際の作成・変更・削除リクエストを送る。Ansible の Connection Plugin に近い役割だが、対象は「サーバーへの接続」ではなく「API」。

### Module まとめて使い回す

複数の Resource をまとめた部品。呼び出し元からは Resource と同じ感覚で `module "web" { source = "./modules/web-server" }` のように使う。

### Plan と Apply 安全に反映する

`plan` は「何が変わるか」を事前に見せるだけで何も実行しない。内容を確認してから `apply` で実際に反映する、という 2 段階が事故を防ぐ仕組みになっている。

## 実行の流れ

初めてのディレクトリで `tofu apply` までを行う場合の順序。

**tofu init** 設定を解析し、必要な Provider と Module をダウンロードする。 `.terraform.lock.hcl` を書く（または検証する）。

**tofu plan** State（なければ空として扱う）と設定ファイルを比較し、作成・変更・削除される Resource の一覧（実行計画）を作る。

**内容を確認する** plan の出力（+ 追加 / ~ 変更 / - 削除）を見て、意図通りか確認する。

**tofu apply** 承認後、計画どおりに Provider 経由で API を呼び、実際にインフラを作成・変更する。

**State を更新する** 成功した Resource の情報を State に書き込む。次回の plan はこの新しい State を基準にする。

## よくある誤解

OpenTofu と Terraform は別の言語？ いいえ

State を手で直接編集してよい？ 非推奨

`.terraform/` は Git にコミットする？ しない

`.terraform.lock.hcl` は Git にコミットする？ する

OpenTofu は Terraform からオープンソースの運営団体（Linux Foundation 配下）としてフォークされたプロジェクトで、HCL 構文・State 形式・Provider エコシステムに高い互換性がある。コマンド名が `terraform` から `tofu` に変わる点が主な違い。State を直接編集したい場合は `tofu state` コマンド群（ `mv` / `rm` / `import` など）を使う。
