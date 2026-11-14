<!-- scripts/memo.py build が自動生成。手で編集しない -->

# グラフ探索と最短経路

> グラフの表し方、BFS と DFS の違い、依存関係を並べるトポロジカルソート、ダイクストラ法の動きを迷路や手順の図で解説し、問題ごとの使い分けをまとめる。

- URL: https://memo.taka1156.site/graph-algorithms.html
- タグ: CS基礎
- 日付: 2026-11-07

---

表し方 / BFS と DFS / トポロジカルソート / ダイクストラ法 / 問題ごとの使い分け

[データ構造と計算量](https://memo.taka1156.site/md/data-structures.md) [設計手法の全体像](https://memo.taka1156.site/md/algorithm-paradigms.md) [動的計画法](https://memo.taka1156.site/md/dynamic-programming.md) グラフ探索と最短経路

**ざっくり言うと**

- **グラフ** は「点（頂点）と、点どうしをつなぐ線（辺）」。道路、ネットワーク、パッケージの依存、コミットの履歴、迷路のマス目もグラフとして扱える。
- 探索の基本は 2 つ。 **BFS（幅優先）** は近い順に広がるので、辺の重みがなければ最短経路が求まる。 **DFS（深さ優先）** は行けるところまで進んで戻り、つながり・ループの検出・依存の順番づけに使う。
- 辺に距離やコストがあるときの最短経路は **ダイクストラ法** （負の重みがない場合）。問題の形で使う方法が決まる（ 使い分けの表 ）。

## グラフの表し方

ADJACENCY LIST ** 隣接リスト**

頂点ごとに「つながっている先」の一覧を持つ。メモリは O(V + E) （V: 頂点数、E: 辺の数）。隣をたどるのが速いので、 **探索ではまずこれ** 。

ADJACENCY MATRIX ** 隣接行列**

V × V の表で「i から j に辺があるか（重みはいくつか）」を持つ。辺の有無を O(1) で調べられるが、メモリは O(V²) 。頂点が数百程度で辺が多いとき向け。

```
# 隣接リスト（有向・重みつき）: g[u] = [(行き先, 重み), ...]
g = [[] for _ in range(n)]
for u, v, w in edges:
    g[u].append((v, w))
    # 無向グラフなら逆向きも足す: g[v].append((u, w))
```

辺に向きがあるものを **有向グラフ** 、ないものを **無向グラフ** という。迷路のマス目のようにグラフを作らなくても、「隣のマス」をその場で計算して探索してよい。

## BFS と DFS — 迷路で比べる

左上 S から右下 G まで。マスの数字は **訪れた順番** 、緑は見つけた道。

BFS（キュー）

DFS（スタック）

▶ 動かす

BFS のコード

DFS のコード

```
from collections import deque

dist = [-1] * n            # -1 = まだ訪れていない
dist[s] = 0
q = deque([s])
while q:
    u = q.popleft()        # 先に入れたものから取り出す（近い順）
    for v in g[u]:
        if dist[v] == -1:
            dist[v] = dist[u] + 1
            q.append(v)
# dist[v] が s から v までの最少の辺の数。O(V + E)
```

```
seen = [False] * n

def dfs(u):
    seen[u] = True
    for v in g[u]:
        if not seen[v]:
            dfs(v)         # 行けるところまで進み、行き止まりで戻る

dfs(s)
# seen[v] が True なら s から v に行ける。O(V + E)
# 深いグラフでは再帰の上限に注意（自分でスタックを持つ書き方にする）
```

- BFS は **キュー** （先入れ先出し）で、距離 1 のマスを全部 → 距離 2 を全部…の順に訪れる。最初に G に着いた道が、 **辺の数が最少の道** 。
- DFS は **スタック** （後入れ先出し、または再帰）で、1 本の道を突き進む。G には着けるが、最短とは限らない。
- どちらも「訪れたか」の記録が必須。ないとループのあるグラフで同じ所を回り続ける。

（元のページで操作できます → https://memo.taka1156.site/graph-algorithms.html#bfs-dfs）

## トポロジカルソート — 依存の順に並べる

矢印を「先に済ませる必要がある」と読むと、作業の順番を決める問題になる。ループのない有向グラフ (DAG) なら、どの矢印にも逆らわない並べ方がある。

1 手進む

最初から

循環する依存を足す

```
# Kahn のアルゴリズム: 入ってくる矢印が 0 本のものから取り出す
indeg = [0] * n
for u in range(n):
    for v in g[u]: indeg[v] += 1
q = deque(u for u in range(n) if indeg[u] == 0)
order = []
while q:
    u = q.popleft(); order.append(u)
    for v in g[u]:
        indeg[v] -= 1
        if indeg[v] == 0: q.append(v)
if len(order) < n: print("循環する依存がある")
```

- DFS で、戻るとき（その先を全部訪れ終えたとき）に頂点を記録し、最後に逆順にしても求まる。
- 実例: ビルドツールの実行順、パッケージのインストール順、表計算ソフトのセルの再計算順。 `git log --topo-order` は、子コミットが親より先に出るようにコミットを並べる（ [Git の内部構造](https://memo.taka1156.site/md/git-internals.md) ）。
- 並べ終わる前に取り出せるものがなくなったら、 **循環する依存** がある。

（元のページで操作できます → https://memo.taka1156.site/graph-algorithms.html#topo）

## ダイクストラ法 — 重みつきの最短経路

辺に距離がある場合、BFS の「近い順」を「 **今わかっている距離が最小の頂点から確定する** 」に置き換える。確定した頂点から出る辺で、隣の距離を短くできれば更新する（緩和）。

1 手進む

最後まで

最初から

```
import heapq
INF = float("inf")
dist = [INF] * n
dist[s] = 0
pq = [(0, s)]                        # (距離, 頂点) のヒープ
while pq:
    d, u = heapq.heappop(pq)         # 距離が最小のものを取り出す
    if d > dist[u]: continue         # 古い情報は捨てる
    for v, w in g[u]:
        if dist[u] + w < dist[v]:    # 緩和
            dist[v] = dist[u] + w
            heapq.heappush(pq, (dist[v], v))
# O((V + E) log V)
```

- 最小を取り出すのに **ヒープ（優先度付きキュー）** を使う（ [データ構造](https://memo.taka1156.site/md/data-structures.md) ）。毎回の選択が「その場で最小」なので貪欲法の一種（ [設計手法](https://memo.taka1156.site/md/algorithm-paradigms.md) ）。
- 前提は **負の重みがない** こと。負の辺があると「確定した距離」が後から縮むことがあり、答えが狂う。そのときはベルマン–フォード法。
- ルーター同士が経路を決める OSPF は、各ルーターがネットワーク全体の地図を持ち、ダイクストラ法で最短経路を計算する（ [TCP/IP のルーティング](https://memo.taka1156.site/md/tcp-ip.md) ）。

（元のページで操作できます → https://memo.taka1156.site/graph-algorithms.html#dijkstra）

## 問題ごとの使い分け

| やりたいこと | 方法 | 計算量 |
| --- | --- | --- |
| 辺の重みがない最短経路（迷路、乗り換え回数） | BFS | O(V + E) |
| 重みが 0 か 1 だけの最短経路 | 0-1 BFS（両端キューで、0 の辺は前、1 の辺は後ろに入れる） | O(V + E) |
| 重みが 0 以上の最短経路 | ダイクストラ法 | O((V + E) log V) |
| 負の重みがある最短経路・負閉路（重みの合計が負になる閉路）の検出 | ベルマン–フォード法 | O(VE) |
| 全部の頂点の組の最短距離（V が数百まで） | ワーシャル–フロイド法 | O(V³) |
| DAG 上の最短・最長経路 | トポロジカル順に DP（ [動的計画法](https://memo.taka1156.site/md/dynamic-programming.md) ） | O(V + E) |
| つながっているか・グループ分け | BFS / DFS、辺が後から増えるなら Union-Find | O(V + E) |
| 全部の頂点を最小コストでつなぐ | 最小全域木（クラスカル法・プリム法） | O(E log E) |

## よくある誤解

✗ 誤解: DFS でも最短経路が求まる

✓ 正しくは: DFS は最初に見つけた道を返すだけで、遠回りのことがある。重みなしの最短経路は BFS。

✗ 誤解: ダイクストラ法は負の重みがあっても使える

✓ 正しくは: 「一度確定した距離はもう縮まない」ことに頼っているので、負の辺があると誤った答えになりうる。ベルマン–フォード法を使う。

✗ 誤解: 木と同じように、訪れた記録なしで探索してよい

✓ 正しくは: 木にはループがないが、一般のグラフにはある。記録なしだと同じ頂点を何度も訪れ、終わらないか指数的に遅くなる。

## 関連メモ

- [アルゴリズム設計手法の全体像](https://memo.taka1156.site/md/algorithm-paradigms.md) — 他の設計手法との使い分け
- [動的計画法（DP）](https://memo.taka1156.site/md/dynamic-programming.md) — 重なる部分問題を表で解く手法
- [データ構造と計算量の早見表](https://memo.taka1156.site/md/data-structures.md) — BFS・DFS・ダイクストラで使うキュー・スタック・ヒープの計算量
- [TCP/IP とネットワーク基礎](https://memo.taka1156.site/md/tcp-ip.md) — ルーティングテーブルでパケットの次の渡し先を決める仕組み
- [Git の内部構造](https://memo.taka1156.site/md/git-internals.md) — コミットの履歴は有向非巡回グラフ
