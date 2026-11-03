<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Ansible 概念図

> Control NodeからManaged Nodesまでの流れと、役割ごとのファイル名の対応を図解。

- URL: https://memo.taka1156.site/ansible.html
- タグ: インフラ
- 日付: 2026-11-01

---

Control Node から Managed Nodes までの流れと、役割ごとのファイル名の対応

**ざっくり言うと**

- Inventory（対象ホスト）と Playbook（手順）はどちらも自分で書く定義ファイル
- Playbook は実行時に Play → Tasks → Modules へと分解される
- Connection Plugin（SSH / WinRM）が Control Node と各サーバーをつなぐ

## 概念図

青＝自分で書く定義ファイル、緑＝実行時に組み立てられる処理、黄＝接続方式。破線は参照・取り込みを表す。

（図: 設定・定義ファイル（YAML / INI） / Managed Nodes（管理対象） / Control Node / ansible / ansible-playbook を実行 / Inventory / 管理対象ホストの定義 / Playbook / 実行手順の定義 / Variables / 設定値 / Roles / 処理の再利用・分割 / Play / 対象ホスト × 実行内容 / Tasks / 1 つ 1 つの操作 / Modules / apt / copy / service など / Connection Plugin / SSH（Linux）/ WinRM（Windows） / Server A / Server B / 読み込む / 実行 / roles: で呼ぶ / vars: / ホストに紐付く / 分解 / Role の tasks / モジュールを転送）

定義ファイル 実行時の処理単位 接続方式 破線＝参照・取り込み

## 役割ごとのファイル名

ファイル名はベストプラクティスとして広く使われる慣例。Play・Tasks・Modules のように独立ファイルを持たず、他ファイルの中に書くものもある。

| 概念 | 種別 | ファイル / 場所 | 役割 |
| --- | --- | --- | --- |
| Control Node 実行環境 | 設定 | `ansible.cfg` `requirements.yml` | Ansible 自体の動作設定。 `requirements.yml` は使う Collection / Role の一覧。 |
| Inventory 管理対象ホスト | 定義 | `inventory/hosts.yml` | どのサーバーを管理するか、どのグループに属するか。 |
| Playbook 実行手順 | 定義 | `site.yml` `playbooks/web.yml` | 1 つ以上の Play を並べたファイル。用途別に分けるのが定番。 |
| Play | 処理 | Playbook 内の `- hosts:` 単位 | 「どのホストに」「何を」するかの組。独立ファイルはない。 |
| Tasks | 処理 | `roles/<名前>/tasks/main.yml` | モジュールを 1 回呼ぶ操作の単位。上から順に実行。 |
| Handlers Task の一種 | 処理 | `roles/<名前>/handlers/main.yml` | 変更があったときだけ動く Task（再起動など）。 `notify:` から呼ぶ。 |
| Modules | 処理 | `ansible.builtin.*` `library/` （自作） | 実際に作業をするプログラム。通常は書かずに使うだけ。 |
| Roles 再利用単位 | 定義 | `roles/<名前>/` | tasks・handlers・templates・変数をひとまとめにしたもの。 |
| Variables グループ/ホスト | 定義 | `group_vars/all.yml` `host_vars/server-a.yml` | Inventory のグループ名・ホスト名と同名にすると自動で読み込まれる。 |
| Variables Role 単位 | 定義 | `roles/<名前>/defaults/main.yml` `roles/<名前>/vars/main.yml` | `defaults` は上書き前提の初期値（優先度最低）。 `vars` は固定値。 |
| Templates / Files | 定義 | `roles/<名前>/templates/*.j2` `roles/<名前>/files/` | `.j2` は Jinja2 テンプレート。 `files/` はそのまま配る静的ファイル。 |
| Secrets | 定義 | `group_vars/all/vault.yml` | `ansible-vault` で暗号化して保存する。 |
| Connection Plugin | 接続 | `ansible.cfg` / `ansible_connection` | 既定は `ssh` 。Windows は `winrm` 、コンテナは `docker` 。 |

## ディレクトリ構成例

構成

inventory

site.yml

```
project/
├── ansible.cfg           # 動作設定
├── inventory/
│   └── hosts.yml         # Inventory
├── group_vars/
│   ├── all.yml
│   └── web.yml
├── host_vars/
│   └── server-a.yml
├── site.yml              # Playbook（入口）
└── roles/
    └── nginx/
        ├── tasks/main.yml
        ├── handlers/main.yml
        ├── templates/nginx.conf.j2
        ├── files/
        ├── defaults/main.yml
        ├── vars/main.yml
        └── meta/main.yml
```

```
all:
  children:
    web:
      hosts:
        server-a:
          ansible_host: 192.168.10.11
        server-b:
          ansible_host: 192.168.10.12
```

```
# ↓ ここから 1 つの Play
- name: Web サーバー構築
  hosts: web          # Inventory のグループ
  become: true
  roles:
    - nginx            # roles/nginx を実行
  tasks:
    - name: パッケージ更新   # Task
      ansible.builtin.apt:  # Module
        update_cache: true
```

## 各要素の考え方

### Control Node 実行する側

Ansible をインストールしてコマンドを打つマシン。管理対象側には Ansible 不要で、SSH と Python があれば動く（エージェントレス）。

### Inventory 誰に

管理するサーバーの一覧とグループ分け。Playbook 側は IP ではなくグループ名（ `web` など）で対象を指すので、サーバーが増えても Inventory を直すだけで済む。

### Playbook と Play 何を

Playbook はファイル、Play はその中の 1 ブロック。対象ごとに Play を分けて 1 つの Playbook に並べる。

### Tasks と Modules どうやって

Task は「nginx をインストールする」という 1 つの操作、Module はそれを実行する部品。モジュールは「あるべき状態」を宣言する作りなので、何度実行しても結果が同じになる（冪等性）。

### Roles まとめて使い回す

Playbook が長くなったら機能単位で Role に切り出す。決まったディレクトリに置くだけで tasks や templates が自動で読み込まれる。

### Connection Plugin どう繋ぐか

Control Node と管理対象の間の通信方法。Ansible はモジュールを一時ファイルとして相手に送り込み、実行して結果を回収し、後片付けする。

## 実行の流れ

`ansible-playbook -i inventory/hosts.yml site.yml` を実行したときの順序。

**設定を読む** `ansible.cfg` を探して読み込む。

**Inventory と変数を読む** ホスト一覧を作り、group_vars / host_vars を紐付ける。

**Playbook を解析する** Play ごとに対象ホストを決め、Roles を展開して Task 一覧を作る。

**事実情報を集める** gather_facts で OS や IP などを取得する。

**Task を順に実行する** Connection Plugin で接続し、モジュールを送って実行する。

**Handler を実行する** changed になった Task から notify された Handler を最後にまとめて実行。

**結果を表示する** PLAY RECAP でホストごとの集計が出る。

## 変数の優先順位（抜粋）

同じ名前の変数が複数箇所にあるときは、上にあるものが勝つ。

コマンドラインの `-e` 最優先

Task / Block の `vars:`

Role の `vars/main.yml`

Play の `vars:`

`host_vars/`

`group_vars/<グループ>`

Role の `defaults/main.yml` 最も弱い
