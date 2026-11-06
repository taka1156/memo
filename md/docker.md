<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Docker 動作原理

> イメージのレイヤー構造、名前空間、cgroups などコンテナが動く仕組みを図解。

- URL: https://memo.taka1156.site/docker.html
- タグ: インフラ, Linux
- 日付: 2026-11-03

---

コンテナは「隔離と制限をかけた、ただの Linux プロセス」

**ざっくり言うと**

- イメージは **読み取り専用のレイヤーの積み重ね** 。コンテナはその上に薄い書き込み層を 1 枚のせて動く（OverlayFS + Copy-on-Write）。
- 「見える範囲」を分けるのが **名前空間 (namespace)** 、「使える量」を抑えるのが **cgroups** 。
- カーネルはホストと共有。だから VM より軽く速いが、Linux コンテナは Linux カーネルの上でしか動かない。

## レイヤー構造

各層をタップすると説明が出ます（上ほど新しい層）。

コンテナ実行時

**コンテナ（実行中プロセス）** CMD / ENTRYPOINT が PID 1 として動く PROCESS

**Container Layer** 書き込みの差分だけが入る（CoW） READ / WRITE

イメージレイヤー（読み取り専用・コンテナ間で共有）

**Layer 3: アプリケーション** COPY app/ /app ・ RUN pip install READ ONLY

**Layer 2: 依存パッケージ** RUN apt-get install python3 curl READ ONLY

**Layer 1: OS 設定** RUN useradd app など READ ONLY

**Base Image (ubuntu:22.04)** FROM ubuntu:22.04 ・ 基底のファイルシステム READ ONLY

ホスト

**Linux Kernel（共有）** namespaces ・ cgroups ・ OverlayFS SHARED

**層を選んでください** どの層が何を持っているかを表示します。

（元のページで操作できます → https://memo.taka1156.site/docker.html#layers）

## OverlayFS と Copy-on-Write

**upperdir** 読み書きできる層（コンテナ専用） `…/overlay2/<id>/diff`

＋

**lowerdir** 読み取り専用の層（イメージレイヤー群）

▼ カーネルが重ねてマウント

**merged** コンテナから見えるファイルシステム（ルート /） `…/overlay2/<id>/merged`

パスは overlay2 ストレージドライバーの例。containerd の image store を使う設定では置き場所が変わるが、重ね方の考え方は同じ。

### ファイルを書き換えたときの動き

1. **読むだけなら下の層をそのまま見る** コンテナが `/etc/nginx/nginx.conf` を読む → lowerdir のファイルが透過的に見える。
2. **書き込んだ瞬間に上の層へコピー** カーネルがそのファイルを lowerdir から upperdir にコピーする（copy-up）。
3. **変更は upperdir のコピーにだけ入る** 元の lowerdir（イメージ）は一切変わらない。
4. **コンテナを消すと upperdir だけ消える** イメージはそのまま残り、次のコンテナで再利用される。

```
# 実際のマウントを確認（overlay2 の場合）
$ docker inspect <container> --format '{{json .GraphDriver.Data}}'
# → LowerDir / UpperDir / MergedDir / WorkDir が見える
```

## 名前空間（namespace）— 見える範囲を分ける

**PID** Process ID

コンテナ専用のプロセス番号の空間。コンテナの最初のプロセスは PID 1 に見え、ホストのプロセスは見えない。

**NET** Network

NIC・ルーティングテーブル・ポートを独立させる。外とは veth ペアでつなぐ。

**MNT** Mount

マウントポイントを独立させる。ここに OverlayFS をマウントして専用のファイルシステムにする。

**IPC** Inter-Process Communication

共有メモリ・セマフォなどをコンテナ間で分け、意図しない通信を防ぐ。

**UTS** UNIX Time-Sharing

ホスト名・ドメイン名を独立させる。コンテナごとに別のホスト名を持てる。

**USER** User ID

コンテナ内の root をホストの一般ユーザーに対応づける（userns-remap や rootless モード）。

## cgroups — 使える量を抑える

リソース割り当ての例（cgroups v2）

CPU

0.6 コア

`--cpus="0.6"` Memory

512MB

`-m 512m` Block I/O

重み低

`--blkio-weight`

cgroups は **制限** だけでなく、使用量の **計測** や **優先度付け** もする。設定は `/sys/fs/cgroup/` 以下にファイルとして見える。メモリ上限を超えるとコンテナ内のプロセスが OOM で止められる。

## docker run の流れ

```
$ docker run -it ubuntu:22.04 bash
```

1. **CLI → dockerd Docker ** Docker CLI が Unix ソケット経由で dockerd（デーモン）に API リクエストを送る。
2. **イメージの確認・取得 Docker ** ローカルにイメージがなければレジストリ（Docker Hub など）からレイヤーを pull して展開する。
3. **containerd → shim → runc に委譲 containerd ** dockerd が containerd に指示し、containerd はコンテナごとの shim を立てて OCI ランタイムの **runc** を呼ぶ。
4. **名前空間を作る カーネル ** runc が `clone()` / `unshare()` で PID・NET・MNT・UTS・IPC などの名前空間を作り、プロセスをその中に置く。
5. **OverlayFS をマウント カーネル ** lowerdir（イメージ層）と upperdir（書き込み層）を merged に重ね、コンテナのルートファイルシステムにする。
6. **cgroups を設定 カーネル ** `/sys/fs/cgroup/` にコンテナ用のグループを作り、CPU・メモリなどの上限を書き込む。
7. **pivot_root → PID 1 を起動 runc ** `pivot_root()` で merged をルートに切り替え、CMD / ENTRYPOINT を exec。ここでは bash がコンテナ内の PID 1 になる。runc は起動後に抜け、以降は shim がプロセスを見守る。

## コンテナと VM の違い

|  | コンテナ | 仮想マシン (VM) |
| --- | --- | --- |
| カーネル | ホストのカーネルを共有 | ゲスト OS のカーネルを丸ごと起動 |
| 隔離の仕組み | 名前空間 + cgroups（プロセス単位） | ハイパーバイザーによるハードウェア仮想化 |
| 起動 | プロセスを起動するだけなので速い | OS のブートが必要で遅め |
| Mac / Windows | Linux コンテナは裏で軽量な Linux VM の上で動く | そのまま動く |

関連: [Docker イメージの種類](https://memo.taka1156.site/md/docker-images.md) （ベースイメージの選び方）
