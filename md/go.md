<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Go 学習フローと仕組み

> Go をどの順で学ぶかと、1 つのバイナリになるビルド、goroutine を動かすスケジューラ（G・M・P）、チャネル、インターフェースとエラー、GC とモジュールの仕組みを図解。

- URL: https://memo.taka1156.site/go.html
- タグ: 言語, バックエンド
- 日付: 2026-11-19

---

どの順で学ぶか ＋ ランタイムが裏で何をしているか

**ざっくり言うと**

- Go は文法を小さく保ち、 **速いビルド・1 つの実行ファイル・軽い並行処理** を重視した言語。サーバーや CLI ツールでよく使われる。
- 実行ファイルには GC と goroutine のスケジューラを含むランタイムが入っていて、少数の OS スレッドで大量の goroutine を回す。
- 学ぶ順は「文法 → 構造体とインターフェース → エラー処理 → goroutine とチャネル → テストとモジュール」が基本。

## 学習ロードマップ

フェーズ 1: 入門

1. **環境を作って動かす** `go mod init example.com/hello` → `go run .` 。エディタには gopls（公式の言語サーバー）を入れる。 ゴール: 1 ファイルのプログラムを実行し、 `go build` で実行ファイルを作れる
2. **基本の文法** 変数（ `:=` ）・関数（戻り値は複数）・ `for` （ループはこれだけ）・ `if` ・ `switch` ・スライスとマップ。 ゴール: スライスの長さと容量の違いを説明でき、 `append` の戻り値を受け取る理由が分かる

フェーズ 2: Go らしさの中核

1. **構造体・メソッド・インターフェース** クラスも継承もない。構造体にメソッドを付け、インターフェースは **宣言なしで** 満たす（下の「仕組み 3」）。 ゴール: 小さなインターフェース（ `io.Reader` など）を受け取る関数を書ける
2. **エラーは値** 例外はなく、関数が `error` を返す。 `fmt.Errorf("...: %w", err)` で包み、 `errors.Is` ・ `errors.As` で調べる。 ゴール: どの層で何が失敗したか分かるエラーメッセージを返せる
3. **goroutine とチャネル** `go f()` で並行に動かし、チャネル・ `sync.WaitGroup` ・ `context` で待ち合わせと中断をする。 ゴール: 複数の HTTP リクエストを並行に投げ、タイムアウトで全部止められる

フェーズ 3: 実践

1. **テスト・ツール** `go test` （テーブル駆動テスト）・ `go test -race` ・ `go vet` ・ `gofmt` 。 ゴール: データ競合を `-race` で見つけて直せる
2. **標準ライブラリで作る** `net/http` ・ `encoding/json` ・ `database/sql` で小さな API サーバーを作る。外部のフレームワークは後から。 ゴール: JSON を返す API を 1 つの実行ファイルにしてコンテナで動かせる

## 仕組み 1: ビルドすると 1 つの実行ファイルになる

**.go ファイル** パッケージ単位

**go build** 依存を含めてコンパイル（結果はキャッシュ）

**リンク** 自分のコード ＋ 依存 ＋ ランタイム

**実行ファイル 1 つ** コピーすれば動く

- **ランタイムが同梱される。** GC・goroutine のスケジューラ・メモリの割り当ては実行ファイルの中にある。JVM や Node.js のような別の実行環境を入れなくてよい。
- **クロスコンパイルが環境変数だけでできる。** `GOOS=linux GOARCH=arm64 go build` で、Mac から Linux ARM 向けの実行ファイルが作れる。
- **静的リンクが基本。** C のライブラリを使う cgo を切れば（ `CGO_ENABLED=0` ）、libc にも頼らない実行ファイルになり、 `scratch` や distroless のイメージにそのまま載る。 `scratch` に載せるなら、HTTPS 用の CA 証明書（必要ならタイムゾーンのデータも）は別に入れる。cgo が有効だと、 `net` パッケージなどが libc を動的にリンクすることがある。

## 仕組み 2: goroutine を動かすスケジューラ（G・M・P）

goroutine は OS スレッドではなく、ランタイムが管理する軽い実行単位。スタックは数 KB から始まり、必要に応じて伸びるので、10 万個作っても動く。ランタイムは次の 3 つで goroutine を OS スレッドに載せる（M:N スケジューリング）。

| 記号 | 正体 | 数 |
| --- | --- | --- |
| G | goroutine。実行する関数とスタック | いくつでも |
| M | machine。OS スレッド | 必要に応じて増える |
| P | processor。G を実行する権利と、実行待ちの G の列を持つ | `GOMAXPROCS` 個（既定は使える CPU 数） |

M は P を 1 つ持っているときだけ Go のコードを実行できる。だから同時に Go のコードを実行する数は `GOMAXPROCS` 個まで。場面ごとの動き:

実行中の G（太枠） 待っている G（点線）

ふだん

チャネルで待つ

システムコールで止まる

列が空になる

P0

実行 M0 G1

待ち行列 G3 G4

P1

実行 M1 G2

待ち行列 G5

各 P が自分の待ち行列から G を取り出して、自分の M で実行する。1 つの G が長く走り続けると、ランタイムが割り込んで（プリエンプション）列の次の G に替える。

P0

実行 M0 G3

待ち行列 G4

P1

実行 M1 G2

待ち行列 G5

**チャネルの待ち** : G1 （受信待ち）

G1 がまだ値の来ないチャネルを受信すると、G1 は P から外れてそのチャネルの待ちに入り、M0 はすぐ次の G3 を実行する。OS スレッドは止まらない。値が送られると G1 はどこかの P の待ち行列に戻る。

P0

実行 M2 G3

待ち行列 G4

P1

実行 M1 G2

待ち行列 G5

**システムコール中** : M0 ＋ G1 （ファイルの読み込みなどで OS の中で止まっている）

G1 がブロックするシステムコールに入ると M0 ごと止まる。ランタイムは P0 を M0 から外し、別の M2（なければ新しく作る）に渡して、残りの G を動かし続ける。M の数が `GOMAXPROCS` より多くなるのはこのため。ネットワークの読み書きはここに入らず、ランタイムが OS の通知（epoll など）で待つので、チャネルと同じく G だけが待ちに入る。

P0

実行 M0 G3

待ち行列 G6 G7

P1

実行 M1 G4

待ち行列 （空 → P0 から半分もらった）

自分の待ち行列が空になった P は、全体の待ち行列やほかの P の行列から G を盗んでくる（ワークスティーリング）。偏りがあっても CPU が遊ばない。

コンテナで CPU の上限（limit）を付けたときは、Go 1.25 以降で `go.mod` の `go` の行が 1.25 以上なら、Linux の cgroup の上限に合わせて `GOMAXPROCS` が自動で決まる（端数は切り上げ、上限が変われば追従する）。それより前はマシンの論理 CPU 数になるので、上限より多くのスレッドが CPU を取り合っていた。

（元のページで操作できます → https://memo.taka1156.site/go.html#scheduler）

## 仕組み 3: チャネルとインターフェース

### チャネル：値を渡しながら待ち合わせる

```
results := make(chan string)        // バッファなし: 送り手と受け手がそろうまで両方待つ
jobs := make(chan int, 100)         // バッファあり: 100 個までは受け手を待たずに送れる

ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
defer cancel()
select {                            // 先に準備できた方を実行
case r := <-results:
    fmt.Println(r)
case <-ctx.Done():                  // タイムアウト・キャンセル
    return ctx.Err()
}
```

- 送り手が「もう送らない」ときは `close(ch)` 。受け手は `for v := range ch` で閉じられるまで読む。閉じたチャネルに送ると panic になる。
- 全部の goroutine が待ちに入って誰も進めないと、ランタイムが「all goroutines are asleep - deadlock!」で止める。一部だけが永遠に待つ場合は検出されず、goroutine のリーク（溜まり続ける）になる。待つ所には必ず `ctx.Done()` の出口を作る。

### インターフェース：宣言せずに満たす

```
type Reader interface { Read(p []byte) (n int, err error) }

type File struct{ /* ... */ }
func (f *File) Read(p []byte) (int, error) { /* ... */ }  // "implements" と書かなくても *File は Reader になる
```

必要なメソッドを持っていれば、どの型でもそのインターフェースとして使える（構造的部分型）。だから **使う側** が、自分に要るメソッドだけの小さなインターフェースを定義するのが Go の流儀。テストでは同じメソッドを持つ偽物を渡せばよい。

## 仕組み 4: GC とモジュール

| GC | プログラムを止めずに並行して印を付け、使われていないメモリを回収する（並行マーク＆スイープ）。止まる時間はふつう 1 ミリ秒を大きく下回る。回収の頻度は `GOGC` 、メモリの上限は `GOMEMLIMIT` で調整する。 |
| --- | --- |
| エスケープ解析 | 関数の外に出ない値はスタックに置かれ、GC の対象にならない。 `go build -gcflags=-m` で、どの値がヒープに逃げたか見られる。 |
| モジュール | `go.mod` に依存とバージョン、 `go.sum` にハッシュを書く。取得はモジュールプロキシ（既定は `proxy.golang.org` ）経由で、ハッシュはチェックサムデータベースと照合される。 |
| バージョンの選び方 | 各依存が「このバージョン以上」と要求する中で、 いちばん高いもの を選ぶ（＝要求をすべて満たす最も古い版。最小バージョン選択、MVS）。新しい版が出ても勝手には上がらず、 `go get -u` で明示的に上げる。 |

## TypeScript・Rust との比較

|  | Go | TypeScript（Node.js） | Rust |
| --- | --- | --- | --- |
| メモリ | GC | GC | 所有権（GC なし） |
| 並行処理 | goroutine（複数コアで並列） | イベントループ（1 スレッド）＋ Worker | スレッド・async（ランタイムは選ぶ） |
| エラー | `error` を値で返す | 例外（ `throw` ） | `Result<T, E>` と `?` |
| 型 | 静的・構造的なインターフェース・ジェネリクスは控えめ | 静的（実行時に消える）・構造的 | 静的・トレイト・強力なジェネリクス |
| 配布 | 1 つの実行ファイル | ランタイム ＋ `node_modules` | 1 つの実行ファイル |
| 学ぶ量 | 少ない（言語仕様が小さい） | 型の機能が多い | 多い（所有権・ライフタイム） |

## よくある誤解

✗ 誤解: goroutine は OS スレッドの別名なので、たくさん作ると重い

✓ 正しくは: goroutine はランタイムが管理する軽い実行単位で、少数の OS スレッドに載せて動かす。スタックも小さく始まるので、数万〜数十万個でも動く。重くなるのは、終わらない goroutine が溜まり続けるリークのとき。

✗ 誤解: GOMAXPROCS は作れる goroutine の数の上限である

✓ 正しくは: GOMAXPROCS は同時に Go のコードを実行できる P の数。goroutine はいくつでも作れ、OS スレッド（M）もシステムコールで止まった分だけ増える。

✗ 誤解: 中身が nil のポインタを error として返せば、呼び出し元の err != nil は false になる

✓ 正しくは: インターフェースの値は「型」と「値」の組で、両方が空のときだけ nil になる。 `var e *MyErr = nil; return e` は型が入っているので `err != nil` が true になる。エラーがないときは `return nil` と書く。

✗ 誤解: for ループの変数を goroutine の中で使うと、全部の goroutine が最後の値を見る

✓ 正しくは: Go 1.22 から、ループ変数は繰り返しごとに新しく作られるようになり、この問題は起きない（ `go.mod` の `go` の行が 1.22 以上のとき）。古いコードに `v := v` と書いてあるのは、この対策の名残。

## よく使うコマンド

```
go mod init example.com/app     # モジュールを作る
go get example.com/lib@v1.4.0   # 依存を足す・上げる
go mod tidy                     # 使っていない依存を消し、足りないものを足す
go run .                        # ビルドして実行
go build -o app .               # 実行ファイルを作る
go test ./...                   # 全パッケージのテスト
go test -race ./...             # データ競合の検出つき
go vet ./...                    # よくある間違いの静的チェック
gofmt -w .                      # 書式をそろえる（議論の余地なし）
go tool pprof cpu.out           # CPU・メモリのプロファイルを見る
```

## 関連メモ

- [並行処理のモデル](https://memo.taka1156.site/md/concurrency-models.md) — goroutine 型をスレッド・イベントループ・アクターと比べる
- [OS のスケジューリング](https://memo.taka1156.site/md/os-scheduling.md) — G・M・P の下で OS がスレッドを切り替えるしくみ
- [メモリ管理](https://memo.taka1156.site/md/memory-management.md) — GC・所有権・参照カウントの中での Go の GC の位置
- [TypeScript 学習フローと仕組み](https://memo.taka1156.site/md/typescript.md) ・ [Rust 学習フローと仕組み](https://memo.taka1156.site/md/rust.md) — 同じ形でまとめたほかの言語
- [Docker イメージの種類](https://memo.taka1156.site/md/docker-images.md) — 静的リンクの実行ファイルを小さなイメージに載せる

## 参考

- [A Tour of Go](https://go.dev/tour/) （ブラウザで動かしながら文法を一周できる）
- [Effective Go](https://go.dev/doc/effective_go)
- [A Guide to the Go Garbage Collector](https://go.dev/doc/gc-guide)
- [Go Modules Reference](https://go.dev/ref/mod)
- [Fixing For Loops in Go 1.22](https://go.dev/blog/loopvar-preview)
- [Container-aware GOMAXPROCS](https://go.dev/blog/container-aware-gomaxprocs)
