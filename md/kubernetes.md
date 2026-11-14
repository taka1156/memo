<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Kubernetes の全体像

> Kubernetes が「あるべき状態」を宣言して保ち続ける仕組みを、コントロールプレーンとノードの部品、Pod・Deployment・Service・Ingress / Gateway の関係、ヘルスチェックとリソース指定まで図で整理する。

- URL: https://memo.taka1156.site/kubernetes.html
- タグ: インフラ, Linux
- 日付: 2026-11-07

---

宣言と調整ループ / コントロールプレーンとノード / Pod・Deployment・Service / Ingress と Gateway API / プローブとリソース

**ざっくり言うと**

- Kubernetes には「何をどう動かせ」ではなく **「こうなっていてほしい」という状態** （レプリカ 3 つ、このイメージ、このポート）を YAML で渡す。
- たくさんの **コントローラ** が「あるべき状態」と「今の状態」を見比べ、差を埋める操作を延々と繰り返す（調整ループ）。Pod が落ちても勝手に作り直されるのはこのため。
- コンテナを動かす単位は **Pod** 。Pod は使い捨てで IP も変わるので、安定した入口として **Service** 、HTTP の振り分けに **Ingress / Gateway** を前に置く。

前提: コンテナそのものの仕組みは [Docker 動作原理](https://memo.taka1156.site/md/docker.md) 、イメージの作り方は [Dockerfile と Compose](https://memo.taka1156.site/md/docker-files.md) 。Kubernetes はそのコンテナを「複数台のマシンで、止まらないように」動かすための仕組み。

## Docker Compose との違い

|  | Docker Compose | Kubernetes |
| --- | --- | --- |
| 動かす場所 | 1 台のマシン | 複数台のマシン（ノード）をまとめた 1 つのクラスタ |
| 書くもの | 起動するコンテナの一覧 | あるべき状態（オブジェクト）の集まり |
| コンテナが落ちたら | `restart:` で同じマシン上で再起動 | 別のノードに作り直す。ノードごと落ちても移る |
| 更新 | 止めて作り直す | 少しずつ入れ替える（ローリングアップデート）、問題があれば戻す |
| 入口・名前解決 | サービス名で DNS、ポートを公開 | Service・Ingress / Gateway・クラスタ内 DNS |
| 向いている規模 | 開発環境・小さな 1 台の本番 | 複数のサービスを複数台で、止めずに運用したいとき |

## クラスタの部品と、Deployment を作ったときの流れ

**kubectl（クラスタの外: 利用者・CI）** YAML を API サーバーに送る

CONTROL PLANE

**kube-apiserver** 唯一の窓口。認証・認可・検証して保存

**etcd** 全オブジェクトを保存する分散 KVS

**controller-manager** Deployment・ReplicaSet などのコントローラの集まり

**scheduler** 未割り当ての Pod を置くノードを決める

WORKER NODES

node-1

**kubelet** 自ノードの Pod を起動・監視

**containerd** CRI ランタイム

**kube-proxy** Service の転送規則

node-2

**kubelet** 自ノードの Pod を起動・監視

**containerd** CRI ランタイム

**kube-proxy** Service の転送規則

← 前へ

次へ →

最初から

ポイントは、部品どうしが直接命令し合わないこと。全員が API サーバーを **監視（watch）** して、自分の担当の差分を見つけたら動く。だから 1 つの部品が一時的に止まっても、戻れば続きから追いつける。

（元のページで操作できます → https://memo.taka1156.site/kubernetes.html#arch）

## 主なオブジェクト

動かす

つなぐ

設定・保存

Deployment web # 「web を 3 つ、イメージは v2」。更新の方法も持つ └─ ReplicaSet web-7d9f # 「このテンプレートの Pod を 3 つ」。版ごとに 1 つ ├─ Pod web-7d9f-abc # 1 つ以上のコンテナ。同じ IP・同じボリュームを共有 ├─ Pod web-7d9f-def └─ Pod web-7d9f-ghi

| 種類 | 使いどころ |
| --- | --- |
| Deployment | 状態を持たない Web・API。ほとんどのアプリはこれ |
| StatefulSet | DB など。Pod に固定の名前（db-0, db-1）と専用のボリュームを持たせ、順番に起動する |
| DaemonSet | 全ノードに 1 つずつ。ログ収集・監視エージェント・ネットワークプラグイン |
| Job / CronJob | 終わる処理。バッチ、マイグレーション、定期実行 |

Pod を直接作ることはほぼない。直接作った Pod は落ちても誰も作り直さないので、必ず上のどれかに作らせる。

Gateway / Ingress # 外からの HTTP を、ホスト名やパスで Service へ └─ Service web # 変わらない仮想 IP と DNS 名。ラベルで Pod を選ぶ └─ EndpointSlice # 今 Ready な Pod の IP 一覧（自動で更新） ├─ 10.244.1.5:8080 └─ 10.244.2.9:8080

Service は `selector: {app: web}` のように **ラベル** で Pod を選ぶ。Pod が入れ替わっても、ラベルが同じなら自動で行き先に入る。 下で詳しく 。

| 種類 | 使いどころ |
| --- | --- |
| ConfigMap | 設定値。環境変数やファイルとして Pod に渡す |
| Secret | パスワード・トークン。渡し方は ConfigMap と同じ。 中身は base64 で、それ自体は暗号化ではない （ 誤解 ） |
| PersistentVolumeClaim | 「10GiB のディスクが欲しい」という要求。StorageClass に従ってクラウドのディスクなどが割り当てられる |
| Namespace | オブジェクトを区切る名前の空間。チームや環境ごとに分け、権限やリソース上限をかける単位 |

（元のページで操作できます → https://memo.taka1156.site/kubernetes.html#objects）

## Service: 消える Pod に変わらない入口を付ける

**ClusterIP**

既定。クラスタ内だけで使える仮想 IP。 `web.shop.svc.cluster.local` （同じ Namespace なら `web` ）で引ける

**NodePort**

全ノードの同じポート（30000〜32767）で受けて Service へ。検証用や、外の LB から入れるとき

**LoadBalancer**

クラウドの LB を自動で作って外部 IP を付ける。Service ごとに LB が 1 つできる

- Service の仮想 IP に届いたパケットは、各ノードの **kube-proxy** が書いた iptables / nftables の規則（または Cilium などの eBPF）で、Ready な Pod の 1 つに書き換えられる。L4 の振り分けなので、HTTP の中身は見ない（ [L4 と L7](https://memo.taka1156.site/md/lb-proxy-cdn.md) ）。
- Pod どうしは、別ノードでも NAT なしで直接 IP で通信できる前提。これを実現するのが CNI プラグイン（Calico・Cilium・クラウド専用のものなど）。

### 外からの HTTP: Ingress と Gateway API

#### Ingress

- ホスト名・パス → Service の対応表。 **書くだけでは何も起きず** 、Ingress コントローラ（nginx・Traefik・クラウドの LB 連携など）を別に入れる必要がある
- 仕様が小さく、ヘッダー操作や重み付き振り分けはコントローラ独自のアノテーション頼みになり、移行しにくい
- API は残るが、機能追加は止まっている

#### Gateway API

- Ingress の後継。 `GatewayClass` （基盤の種類）・ `Gateway` （入口）・ `HTTPRoute` （振り分け）に分かれ、基盤担当とアプリ担当が別々に書ける
- ヘッダーでの振り分け、重み付き（カナリア）、gRPC・TCP のルートが標準の仕様に入っている
- これも実装（Envoy Gateway・Istio・Cilium・クラウドなど）を入れて使う

広く使われていた Ingress コントローラの ingress-nginx（Kubernetes プロジェクト版）は、2026 年 3 月で保守を終えた。既存の環境は動き続けるがセキュリティ修正は出ないため、Kubernetes プロジェクトは Gateway API か別のコントローラへの移行を勧めている。F5 社の「NGINX Ingress Controller」は別物。

## 最小の YAML

```
apiVersion: apps/v1
kind: Deployment
metadata: { name: web }
spec:
  replicas: 3
  selector: { matchLabels: { app: web } }     # どの Pod を自分のものとみなすか
  template:                                   # 作る Pod のひな形
    metadata: { labels: { app: web } }
    spec:
      containers:
        - name: web
          image: ghcr.io/example/web:2.4.1    # latest ではなく版を固定
          ports: [{ containerPort: 8080 }]
          resources:
            requests: { cpu: 250m, memory: 256Mi }   # 置き場所を決める目安
            limits:   { memory: 512Mi }              # 超えたら OOMKilled
          readinessProbe: { httpGet: { path: /ready, port: 8080 } }
          livenessProbe:  { httpGet: { path: /healthz, port: 8080 }, periodSeconds: 10 }
---
apiVersion: v1
kind: Service
metadata: { name: web }
spec:
  selector: { app: web }                      # このラベルの Pod へ
  ports: [{ port: 80, targetPort: 8080 }]
```

## プローブとリソース: 「動いている」をどう判断するか

| プローブ | 失敗したら | 何を確かめるか |
| --- | --- | --- |
| readiness | Service の行き先から外す（再起動はしない） | 今リクエストを受けられるか。起動直後のウォームアップ中や、一時的に過負荷のとき false |
| liveness | コンテナを再起動する | プロセスが固まっていないか。 DB など外部の依存は見ない （DB が落ちると全 Pod が再起動を繰り返す） |
| startup | 成功するまで他の 2 つを始めない | 起動に時間がかかるアプリが、起動中に liveness で殺されないように |

#### requests

scheduler はノードの空きを requests の合計で計算して Pod を置く。実際の使用量ではない。小さすぎると 1 台に詰め込まれて取り合いになる。

#### limits

CPU は超えると **絞られる** （遅くなるだけ）。メモリは超えると **強制終了** （OOMKilled）。メモリの limit は必ず、CPU の limit は遅延が問題になるなら付けない選択もある。

ローリングアップデートでは、新しい Pod が readiness に通ってから古い Pod を減らす。readiness が無いと、起動途中の Pod にリクエストが流れて更新のたびにエラーが出る。

## よくある誤解

✗ 誤解: Pod はコンテナの別名

✓ 正しくは: Pod は 1 つ以上のコンテナのまとまり。同じ Pod のコンテナはネットワーク名前空間（同じ IP・localhost で通じる）とボリュームを共有し、必ず同じノードに置かれる。ログ転送やプロキシを横に添えるサイドカーはこの性質を使う。

✗ 誤解: Secret に入れれば暗号化される

✓ 正しくは: Secret の値は base64 で書かれているだけで、誰でも元に戻せる。守っているのは RBAC（誰が読めるか）で、etcd に保存するときの暗号化はクラスタの設定で有効にする必要がある。外部のシークレット管理（クラウドの KMS・Vault など）と連携することも多い。

✗ 誤解: Ingress を書けば外からつながる

✓ 正しくは: Ingress は設定データでしかない。それを読んで実際にトラフィックを受けるコントローラがクラスタに入っていなければ、何も起きない。Gateway API も同じ。

✗ 誤解: kubectl で Pod を直したら、それで直る

✓ 正しくは: Deployment が管理している Pod を手で変えても、コントローラが「あるべき状態」に戻す（または作り直したときに消える）。直すのは Deployment の定義の方。定義を Git に置いて自動で適用する（GitOps）と、手で変えた差分が残らない。

## よく使うコマンド

```
kubectl get pods -o wide                   # どのノードで動いているか・Pod の IP
kubectl describe pod web-7d9f-abc          # 下の Events に Pending・再起動の理由が出る
kubectl logs web-7d9f-abc --previous       # 再起動する前のコンテナのログ
kubectl get endpointslices -l kubernetes.io/service-name=web   # Service の行き先に入っている Pod
kubectl rollout status deploy/web          # ローリングアップデートの進み具合
kubectl rollout undo deploy/web            # 1 つ前の ReplicaSet に戻す
kubectl port-forward svc/web 8080:80       # 手元から Service に直接つなぐ
kubectl diff -f web.yaml                   # 適用したら何が変わるか（apply の前に）
```

## 関連メモ

- [Docker 動作原理](https://memo.taka1156.site/md/docker.md) — Pod の中で動くコンテナの仕組み
- [Docker イメージの種類](https://memo.taka1156.site/md/docker-images.md) — Pod に載せるイメージの選び方
- [ロードバランサ・リバースプロキシ・CDN](https://memo.taka1156.site/md/lb-proxy-cdn.md) — Service・Ingress の外側にある入口
- [CI/CD と GitHub Actions](https://memo.taka1156.site/md/ci-cd.md) — マニフェストを適用するまでのパイプライン
- [オブザーバビリティと OpenTelemetry](https://memo.taka1156.site/md/observability.md) — クラスタの中を追うログ・メトリクス・トレース
- [分散システムの基本](https://memo.taka1156.site/md/distributed-basics.md) — レプリカと整合性の前提
- [OpenTofu 概念図](https://memo.taka1156.site/md/opentofu.md) — クラスタそのものをコードで作る
