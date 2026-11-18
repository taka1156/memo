<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Python 学習フローと仕組み

> Python をどの順で学ぶかと、バイトコードを解釈して動く CPython、名前と参照、参照カウントと GC、GIL と並行処理、仮想環境とパッケージの仕組みを図解。

- URL: https://memo.taka1156.site/python.html
- タグ: 言語, バックエンド
- 日付: 2026-11-19

---

どの順で学ぶか ＋ CPython が裏で何をしているか

**ざっくり言うと**

- Python は書きやすさを優先した動的型付けの言語で、データ分析・機械学習・自動化・Web の裏側まで広く使われる。
- 標準の処理系 CPython はコードをバイトコードに変えて 1 命令ずつ解釈し、メモリは参照カウントと GC で片づける。
- 学ぶ順は「文法 → データ型と名前の扱い → 関数とクラス → 仮想環境とパッケージ → 並行処理と型ヒント」が基本。

## 学習ロードマップ

フェーズ 1: 入門

1. **環境を作って動かす** 公式の配布物か uv などで Python を入れ、対話モード（REPL）と `python app.py` で動かす。 ゴール: 1 ファイルのスクリプトを書いて実行できる
2. **基本の文法** インデントでブロックを表す。 `if` ・ `for` （何かを順にたどる）・ `while` ・関数（ `def` ）・f 文字列。 ゴール: ファイルを読んで行ごとに集計するスクリプトを書ける
3. **組み込みのデータ型** `list` ・ `dict` ・ `set` ・ `tuple` と内包表記。どれが変更可能（mutable）かを押さえる。 ゴール: 目的に合わせて list と dict と set を選べる

フェーズ 2: Python らしさの中核

1. **名前と参照 ★つまずきやすい** 変数は値の入れ物ではなく、オブジェクトに付けた名札（下の「仕組み 2」）。 ゴール: 関数に渡した list が呼び出し元でも変わる理由を説明できる
2. **クラス・例外・with** クラスと特殊メソッド（ `__init__` ・ `__repr__` ）、 `try` / `except` 、 `with` によるファイルなどの後片づけ。 ゴール: 失敗しうる処理を例外で扱い、リソースを確実に閉じられる
3. **仮想環境とパッケージ** プロジェクトごとに仮想環境を作り、依存は `pyproject.toml` に書く（下の「仕組み 5」）。 ゴール: ほかの人が同じ依存で動かせる形でプロジェクトを渡せる

フェーズ 3: 実践

1. **型ヒントとツール** 型ヒントを付けて mypy や pyright で検査し、Ruff で lint と整形、pytest でテストする。 ゴール: 型の検査とテストを CI で回せる
2. **並行処理** I/O 待ちが多いなら `asyncio` かスレッド、計算が重いなら `multiprocessing` （下の「仕組み 4」）。 ゴール: 多数の HTTP リクエストを並行に投げられ、CPU を使う処理を複数コアに分けられる

## 仕組み 1: コードが動くまで

**.py ファイル** ソースコード

**コンパイル** 構文木を作り、バイトコードに変える

**.pyc** import したモジュールは `__pycache__` に保存

**仮想マシン** バイトコードを 1 命令ずつ解釈して実行

```
>>> import dis
>>> dis.dis(lambda a, b: a + b)   # バイトコードを見る（Python 3.13 の例）
  RESUME                0
  LOAD_FAST_LOAD_FAST   1 (a, b)    # a と b をまとめて読み込む
  BINARY_OP             0 (+)       # 実行するまで a と b の型は分からない
  RETURN_VALUE
```

命令の名前は版によって変わる（3.12 までは `LOAD_FAST` が 2 つ、3.14 以降は `LOAD_FAST_BORROW` 系）。

- **型は実行時に決まる。** `a + b` は、実行のたびに a と b の型を見て、数値の足し算か文字列の連結かを選ぶ。この確認の分だけ、C や Go より遅くなる。
- **重い処理は C で書かれたライブラリに任せる。** NumPy などはループの中身を C で実行するので、Python で 1 要素ずつ回すより桁違いに速い。「Python は遅い」は、Python のループで大量の要素を回したときの話。
- **CPython 以外の処理系もある。** JIT で速くする PyPy など。CPython 自身も 3.13 から実験的な JIT を持つ（既定では無効）。

## 仕組み 2: 変数は名札、代入は名札の付け替え

代入はオブジェクトをコピーせず、同じオブジェクトにもう 1 つ名前を付けるだけ。タブを順に押すと、名前とオブジェクトのつながりが変わる様子が見える。

この行で変わったオブジェクト（太枠）

1. a = [1, 2]
2. b = a
3. b.append(3)
4. b = b + [4]

a 指す → list [1, 2]

list オブジェクトが作られ、 `a` という名前がそれを指す。

a 指す → list [1, 2] b 同じものを指す ↑

コピーはされない。 `a` と `b` は同じ 1 つの list を指していて、 `a is b` は `True` 。

a 指す → list [1, 2, 3] b 同じものを指す ↑

`append` は list そのものを変える。 `b` から変えたのに、 `a` から見ても `[1, 2, 3]` になる。関数に list を渡して中で変えたときも同じことが起きる。

a 指す → list [1, 2, 3] b 指す → 新しい list [1, 2, 3, 4]

`b + [4]` は新しい list を作り、 `b` の名札をそちらに付け替える。 `a` は元の list を指したまま。変更（ `append` ）と再代入（ `=` ）の違いが、Python のバグの定番の原因。

int・str・tuple は変更できない（immutable）ので、 `s += "x"` はいつも新しいオブジェクトを作って名札を付け替える。値が同じかは `==` 、同じオブジェクトかは `is` で比べる（ `is` を使うのは `None` との比較くらい）。

（元のページで操作できます → https://memo.taka1156.site/python.html#names）

## 仕組み 3: メモリは参照カウントと GC で片づける

- **参照カウント** : どのオブジェクトも「いくつの名前・入れ物から指されているか」を数えていて、0 になった瞬間に解放される。 `with` を使わずに開いたファイルが、関数を抜けたときに閉じられるのはこのため（ただし CPython の実装の性質なので、閉じるのは `with` に任せる）。
- **循環を拾う GC** : 互いに指し合うオブジェクトは数が 0 にならないので、別の GC（世代別）がときどき見つけて回収する。

## 仕組み 4: GIL と並行処理

CPython には **GIL（グローバルインタプリタロック）** があり、1 つのプロセスの中で Python のバイトコードを同時に実行できるスレッドは 1 本だけ。ただし I/O を待つ間や、GIL を手放す C のライブラリの計算中は、ほかのスレッドが動ける。

Python のコードを実行中 I/O 待ち（斜線。GIL を手放している）

計算をスレッドで

I/O をスレッドで

計算をプロセスで

スレッド1

スレッド2

どちらのスレッドも計算したいが、GIL を交代で持つので **同時には走らない** 。合計時間は 1 本で計算したときとほぼ同じ（切り替えの分だけ遅いこともある）。

スレッド1

スレッド2

スレッド3

HTTP の応答やディスクを待つ間は GIL を手放すので、待ち時間が重なり合う。I/O が中心の処理なら、スレッドや `asyncio` で十分に速くなる。

プロセス1

プロセス2

プロセスごとに別のインタプリタと GIL を持つので、複数コアで同時に計算できる。代わりに、プロセス間でデータを渡すときにコピー（シリアライズ）の手間がかかる。

| やりたいこと | 選ぶもの |
| --- | --- |
| たくさんの HTTP リクエスト・DB 問い合わせを並行に | `asyncio` （ライブラリが対応していれば）か `concurrent.futures.ThreadPoolExecutor` |
| Python で書いた重い計算を複数コアで | `multiprocessing` か `ProcessPoolExecutor` |
| 配列の計算 | NumPy などに任せる（中で GIL を手放して C で計算する） |

GIL を外したビルド（free-threaded 版）もある。3.13 で実験的に入り、3.14 で正式にサポートされたが、まだ既定のビルドではない。C 拡張のライブラリが対応している必要がある。

（元のページで操作できます → https://memo.taka1156.site/python.html#gil）

## 仕組み 5: 仮想環境とパッケージ

`pip install` は、いま使っている Python の `site-packages` フォルダにパッケージを入れる。プロジェクトごとにバージョンが違う依存を混ぜないよう、 **プロジェクトごとに仮想環境** （専用の `site-packages` を持つフォルダ）を作る。

```
# 標準の道具だけで
python -m venv .venv            # 仮想環境を作る
source .venv/bin/activate       # 有効にする（Windows は .venv\Scripts\activate）
pip install requests            # .venv の中に入る

# uv を使う場合（仮想環境・依存・ロックファイルをまとめて扱う）
uv init                         # pyproject.toml を作る
uv add requests                 # 依存を足し、uv.lock を更新する
uv run app.py                   # 仮想環境の中で実行する
```

- 依存の宣言は `pyproject.toml` に書くのが今の標準（以前は `requirements.txt` や `setup.py` ）。
- 同じバージョンを再現するにはロックファイル（ `uv.lock` など）を使う。 `pyproject.toml` には「この範囲なら動く」を、ロックファイルには「実際に入れた版」を書く。
- OS に最初から入っている Python に `sudo pip install` しない。OS のツールが使うパッケージを壊すことがあり、最近の Linux では拒否される。

### 型ヒントは実行時には検査されない

```
def total(prices: list[int]) -> int:
    return sum(prices)

total(["100", "200"])   # 実行すると sum の中で TypeError。型ヒントだけでは止まらない
                        # mypy / pyright で検査すると、実行前にこの行を指摘できる
```

## Go・TypeScript との比較

|  | Python | Go | TypeScript（Node.js） |
| --- | --- | --- | --- |
| 実行 | バイトコードをインタプリタで実行 | ネイティブの実行ファイル | JS に変換し、JIT で実行 |
| 型 | 動的。型ヒントは別のツールで検査 | 静的 | 静的（実行時に消える） |
| メモリ | 参照カウント ＋ 循環 GC | GC | GC |
| 並列計算 | GIL があるので主にプロセスで | goroutine で複数コア | Worker で複数コア |
| 強い所 | データ分析・機械学習のライブラリ、短いスクリプト | サーバー・CLI・並行処理 | Web のフロントとバックを同じ言語で |

## よくある誤解

✗ 誤解: GIL があるので、Python でスレッドを使っても速くならない

✓ 正しくは: 速くならないのは、Python のコードで計算するときだけ。I/O を待つ間は GIL が手放されるので、ネットワークやファイルを待つ処理はスレッドで並行に進む。

✗ 誤解: 関数の引数の既定値は、呼ぶたびに新しく作られる

✓ 正しくは: 既定値は関数を定義したときに 1 回だけ作られる。 `def add(x, items=[])` と書くと、呼ぶたびに同じ list に追加されていく。変更可能な既定値は `items=None` にして、関数の中で `if items is None: items = []` とする。

✗ 誤解: 型ヒントを書けば、間違った型の値を渡したときに実行時にエラーになる

✓ 正しくは: 型ヒントは実行時には検査されない（記録されるだけ）。実行前に mypy や pyright で検査するか、実行時に確かめたいなら Pydantic などのライブラリを使う。

✗ 誤解: b = a と書けば、a の list のコピーが b に入る

✓ 正しくは: 代入は同じオブジェクトに名前を増やすだけで、コピーしない。コピーが要るなら `a.copy()` や `list(a)` 、入れ子まで丸ごとなら `copy.deepcopy(a)` 。

## よく使うコマンド

```
python -m venv .venv             # 仮想環境を作る
python -m pip install -r requirements.txt
uv sync                          # uv.lock どおりに依存を入れる
python -m pytest                 # テスト
ruff check . && ruff format .    # lint と整形
mypy src/                        # 型の検査
python -m cProfile -s cumtime app.py   # どこで時間を使っているか
python -X importtime app.py      # import の遅い所を探す
```

## 関連メモ

- [メモリ管理](https://memo.taka1156.site/md/memory-management.md) — 参照カウントと GC をほかの言語の方式と比べる
- [並行処理のモデル](https://memo.taka1156.site/md/concurrency-models.md) — asyncio が入るイベントループ型の考え方
- [Go 学習フローと仕組み](https://memo.taka1156.site/md/go.md) ・ [TypeScript 学習フローと仕組み](https://memo.taka1156.site/md/typescript.md) ・ [Rust 学習フローと仕組み](https://memo.taka1156.site/md/rust.md) — 同じ形でまとめたほかの言語
- [浮動小数点と数値表現](https://memo.taka1156.site/md/floating-point.md) — `0.1 + 0.2` が 0.3 にならない理由（Python でも同じ）
- [サプライチェーンセキュリティ](https://memo.taka1156.site/md/supply-chain-security.md) — PyPI から入れる依存の脆弱性とロックファイル

## 参考

- [Python チュートリアル](https://docs.python.org/ja/3/tutorial/)
- [用語集 — グローバルインタプリタロック](https://docs.python.org/ja/3/glossary.html#term-global-interpreter-lock)
- [Python support for free threading](https://docs.python.org/3/howto/free-threading-python.html)
- [venv — 仮想環境の作成](https://docs.python.org/ja/3/library/venv.html)
- [uv のドキュメント](https://docs.astral.sh/uv/)
- [pyproject.toml を書く](https://packaging.python.org/ja/latest/guides/writing-pyproject-toml/)
