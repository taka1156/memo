<!-- scripts/memo.py build が自動生成。手で編集しない -->

# GCC と Clang の構成比較

> GCC（GENERIC・GIMPLE・RTL の一体型）と Clang/LLVM（ライブラリ型・LLVM IR）の内部構成の違いを、同じ C コードのダンプを並べて比べる

- URL: https://memo.taka1156.site/gcc-vs-clang.html
- タグ: 言語, 開発ツール
- 日付: 2026-11-06

---

同じ「フロント → 中間表現 → バックエンド」でも、部品の切り方がまるで違う

シリーズ: [← LLVM の構成と仕組み](https://memo.taka1156.site/md/llvm.md) **GCC と Clang の構成比較**

**ざっくり言うと**

- **GCC** は 1 つの製品として作られたコンパイラ。言語ごとの `cc1` などのプログラムの中で、GENERIC → GIMPLE → RTL と中間表現を乗り換えながら、アセンブリのテキストまで出す。
- **Clang** は LLVM のライブラリを使うフロントエンド。中間表現は公開された LLVM IR に一本化され、最適化・コード生成・アセンブラは LLVM 側の部品が受け持つ。
- コマンドの使い勝手はほぼ互換だが、「中身を部品として再利用できるか」「1 つのバイナリで複数 CPU を狙えるか」で差が出る。

## 全体の流れを並べる

どちらもコマンド ( `gcc` / `clang` ) は **ドライバ** で、実際のコンパイルは別のプロセスに任せている。点線の枠が 1 つのプロセス、実線の枠は外部のプログラム。段にカーソルを乗せる（タップする）と、反対側の対応する段が光る。

フロントエンド ミドルエンド（CPU 非依存の最適化） バックエンド 外部ツール

### gcc x.c

cc1（C 用。C++ は cc1plus）

**前処理・構文解析** 手書きの再帰下降パーサ

**GENERIC** 言語共通の木。C 固有の木から変換

↓ gimplify

**GIMPLE** 3 番地コード（タプル表現）。ここから SSA 化

**GIMPLE パス群 (tree-ssa)** インライン化・定数伝播・ベクトル化など

↓ expand

**RTL** CPU 命令に近い式。machine description (.md) と照合

**RTL パス・IRA / LRA** 命令の組み合わせ・スケジュール・レジスタ割付

**final** アセンブリのテキスト (.s) を書く

↓ .s ファイル

as（GNU binutils）

**アセンブル** .s → .o

↓

collect2 → ld

**リンク** GNU ld / mold / lld など（gold は binutils 2.44 で非推奨）

### clang x.c

clang -cc1（同じバイナリを別モードで起動）

**前処理・構文解析** 手書きの再帰下降パーサ

**Clang AST ＋ Sema** ソースに忠実な木。位置情報を細かく持つ

↓ CodeGen

**LLVM IR** 最初から SSA。外に出せる公開フォーマット

**LLVM パス群 (opt)** mem2reg・inline・instcombine・ベクトル化など

↓ 命令選択

**SelectionDAG / GlobalISel → MIR** TableGen (.td) から生成した表と照合

**MIR パス・レジスタ割付** スケジュール・greedy アロケータ

**MC 層** 機械語を直接書く

**統合アセンブラ** 外部の as を呼ばずに .o を出力

↓ .o ファイル

ld / lld

**リンク** システムの ld か、-fuse-ld=lld

実際に呼ばれるプロセスは `gcc -### x.c` / `clang -### x.c` で見られる（GCC 13 では cc1 → as → collect2、clang 18 では clang -cc1 -emit-obj → ld だった）。

## 中間表現を実物で比べる

同じ C コードを GCC 13 と clang 18 (x86-64 Linux, `-O2` ) に通し、それぞれのダンプを並べた。LLVM IR は見やすさのため `dso_local` ・ `noundef` ・属性 `#0` などを省略した。

```
static int sq(int x) { return x * x; }
int f(void) { int a = 3; return sq(a) + 1; }
int add(int a, int b) { int c = a + b; return c; }
int max(int a, int b) { int r; if (a > b) r = a; else r = b; return r; }
```

最適化前

最適化後

機械寄りの IR

GCC: GIMPLE (-fdump-tree-gimple)

```
int add (int a, int b)
{
  int D.2760;
  int c;

  c = a + b;
  D.2760 = c;
  return D.2760;
}
```

Clang: LLVM IR (-O0 -emit-llvm)

```
define i32 @add(i32 %a, i32 %b) {
entry:
  %a.addr = alloca i32, align 4
  %b.addr = alloca i32, align 4
  %c = alloca i32, align 4
  store i32 %a, ptr %a.addr, align 4
  store i32 %b, ptr %b.addr, align 4
  %0 = load i32, ptr %a.addr, align 4
  %1 = load i32, ptr %b.addr, align 4
  %add = add nsw i32 %0, %1
  store i32 %add, ptr %c, align 4
  %2 = load i32, ptr %c, align 4
  ret i32 %2
}
```

GIMPLE はまだ C っぽい見た目で、変数は変数のまま（ `D.2760` は GCC が足した一時変数）。LLVM IR は最初から「メモリの箱と load/store」で書かれ、型とアラインメントが明示される。

GCC: GIMPLE SSA (-fdump-tree-optimized)

```
int f ()
{
  <bb 2> [local count: 1073741824]:
  return 10;
}

int add (int a, int b)
{
  <bb 2> [local count: 1073741824]:
  c_3 = a_1(D) + b_2(D);
  return c_3;
}

int max (int a, int b)
{
  <bb 2> [local count: 1073741824]:
  _3 = MAX_EXPR <a_1(D), b_2(D)>;
  return _3;
}
```

Clang: LLVM IR (-O2 -emit-llvm)

```
define noundef i32 @f() {
entry:
  ret i32 10
}

define i32 @add(i32 %a, i32 %b) {
entry:
  %add = add nsw i32 %b, %a
  ret i32 %add
}

define noundef i32 @max(i32 %a, i32 %b) {
entry:
  %a.b = tail call i32 @llvm.smax.i32(i32 %a, i32 %b)
  ret i32 %a.b
}
```

結論はそっくり: どちらも f をインライン化して `10` に畳み、max を分岐のない「最大値」の 1 命令にした（GCC は `MAX_EXPR` 、LLVM は組み込み関数 `llvm.smax` ）。GCC の SSA は `a_1` のように変数名＋版数で書き、 `(D)` は「関数に入ったときの値」。

GCC: RTL (-fdump-rtl-final, add の本体)

```
(insn:TI 18 4 13 2 (set (reg:SI 0 ax [orig:85 c ] [85])
        (plus:SI (reg:SI 5 di [86])
            (reg:SI 4 si [87]))) "add.c":3:29 240 {*leasi}
     (expr_list:REG_DEAD (reg:SI 5 di [86])
        (expr_list:REG_DEAD (reg:SI 4 si [87])
            (nil))))
```

最終的なアセンブリ (x86-64)

```
# GCC 13 -O2
add:
	endbr64
	leal	(%rdi,%rsi), %eax
	ret

# clang 18 -O2
add:
	leal	(%rdi,%rsi), %eax
	retq
```

RTL は Lisp 風の式で「ax ← di + si」を表し、 `{*leasi}` は machine description のどのパターン（ここでは lea 命令）に当てはまったかを示す。LLVM 側でこれに当たるのが MIR（ `llc -print-after-isel` などで見られる）。GCC の `endbr64` は Ubuntu の GCC が既定で `-fcf-protection` を有効にしているため。

（元のページで操作できます → https://memo.taka1156.site/gcc-vs-clang.html#ir）

## 設計の違いを表で

| 観点 | GCC | Clang / LLVM |
| --- | --- | --- |
| 作りの単位 | 言語ごとのコンパイラ本体（cc1・cc1plus・f951 など）に、フロントからバックエンドまでが一体でリンクされている | LLVM はライブラリの集まり。clang・rustc・swiftc がそれぞれ必要な部品をリンクして使う |
| 中間表現 | GENERIC → GIMPLE → RTL の 3 種類。GCC の内部形式で、外部向けの安定した仕様ではない | LLVM IR に一本化（バックエンド内は MIR）。仕様書 (LangRef) があり、テキスト・ビットコードで外に出せる |
| CPU の記述 | machine description ( `.md` )。RTL のパターンで命令を書く | TableGen ( `.td` )。そこから命令選択表・レジスタ情報などを生成 |
| 対象 CPU の選び方 | コンパイラを作るときに 1 つ決める。クロスコンパイルには `aarch64-linux-gnu-gcc` のような専用ビルドが要る | 1 つの clang に複数のバックエンドが入る。 `--target=aarch64-linux-gnu` で切り替え（ヘッダやライブラリは別に要る） |
| アセンブラ | .s を書き、外部の GNU as を呼ぶ | 統合アセンブラで直接 .o を書く（ `-fno-integrated-as` で外部も可） |
| LTO | `-flto` : .o に GIMPLE を入れ、リンク時に分割して並列最適化 (WHOPR) | `-flto` （フル）と `-flto=thin` 。.o に LLVM ビットコードを入れる |
| 拡張・再利用 | プラグイン API、 `libgccjit` （GCC をライブラリとして JIT・AOT に使う） | libclang・LibTooling で AST を使うツールを作れる（clangd・clang-tidy など。clang-format は字句解析ベースの libFormat） |
| 対応言語 | C・C++・Fortran・Ada・D・Go・Modula-2・COBOL など。Rust (gccrs) は実験的 | Clang は C・C++・Objective-C/C++・OpenCL・CUDA。他の言語は別のフロントエンドが LLVM を使う（LLVM プロジェクト内の Flang、外部の rustc・swiftc など） |
| 標準ライブラリ | libstdc++・libgcc | libc++・compiler-rt があるが、Linux の clang は既定で GCC の libstdc++・libgcc を使う |
| ライセンス | GPLv3 以降（ランタイムライブラリ例外つき。生成したプログラムに GPL は及ばない） | Apache License 2.0 with LLVM Exceptions |

ライセンスの違いは、コンパイラ自体を改造して配る・製品に組み込む場合に効く。どちらでコンパイルしても、できたプログラムのライセンスは自分で決められる。

## 互換性: clang は「GCC のふり」をする

同じオプションがだいたい通る

`-O2` ・ `-Wall` ・ `-std=c17` ・ `-march` ・ `-fPIC` など主なオプションは共通。 `__attribute__` や statement expression（ `({ ... })` ）などの GNU 拡張も Clang がほぼ受け付けるので、Makefile の `CC=clang` だけで切り替わることが多い。

マクロでも名乗る

Clang は既定で `__GNUC__` を定義する（GCC 4.2.1 相当を名乗る）。 `#ifdef __GNUC__` だけでは GCC か Clang か区別できないので、Clang を見分けたいときは `__clang__` を先に調べる。

```
#if defined(__clang__)
  /* Clang */
#elif defined(__GNUC__)
  /* 本物の GCC */
#endif
```

それでも完全一致ではない: 警告の種類と既定値、 `-O3` などで行う最適化の中身、未定義動作に対する振る舞い、インラインアセンブリの細部、GCC だけにあるオプション（例: `-fanalyzer` ）などは違う。両方でビルドして警告を見比べると、移植性の低いコードが見つかりやすい。

## こんなときはどっち？

1 台の開発マシンから x86-64・AArch64・RISC-V 向けにビルドしたい

Clang が楽。1 つのバイナリで `--target` を切り替えられる（各ターゲット用の sysroot は必要）。GCC はターゲットごとのクロスコンパイラを用意する。

エディタの補完・リファクタ・静的解析ツールを自作・導入したい

Clang。AST をライブラリ (libclang / LibTooling) として使え、clangd・clang-tidy がそのまま使える。

マイナーな組込み CPU や古いアーキテクチャ向けにビルドしたい

GCC のほうが対応ターゲットが広い場面が多い。ベンダの SDK も GCC ベースのことがある。まず公式に対応しているかを確認する。

新しい言語を作って、最適化つきで機械語を出したい

LLVM を使うのが定番（Rust・Swift・Julia など）。IR が公開仕様なので、フロントエンドを書いて IR を出すだけでよい。GCC にも libgccjit や GCC のフロントエンドとして組み込む道はあるが、例は少ない。

どちらのほうが速いコードを出すか知りたい

一般論では決まらない。コードと CPU とオプションで勝ち負けが入れ替わる。自分のコードで両方ビルドしてベンチマークを取る。

（元のページで操作できます → https://memo.taka1156.site/gcc-vs-clang.html#choose）

## よくある誤解

Clang は GCC のコードを一切使っていない

コンパイラ本体は独立しているが、Linux の clang は既定で GCC が入れたディレクトリを探し、libstdc++ のヘッダ、libgcc、 `crtbegin.o` などのスタートアップファイルを使う（ `clang++ -v` の「Selected GCC installation」で見える）。Clang だけで完結させたいなら `-stdlib=libc++ -rtlib=compiler-rt` などを指定する。

GCC には中間表現がない（ソースから直接アセンブリを出す）

GCC も GENERIC・GIMPLE・RTL と 3 段の中間表現を持ち、SSA ベースの最適化をする。違いは、それが GCC の内部形式で、外部のツールが入出力するための安定したフォーマットとして公開されていないこと。

GCC は 1 つの巨大なプログラム、Clang はたくさんのプログラム

プロセスの数で見るとむしろ逆に近い。GCC は cc1 → as → collect2/ld と別プログラムを順に呼び、Clang は clang -cc1 の中でアセンブルまで済ませてからリンカを呼ぶ。違いは「プロセスの数」ではなく「中身がライブラリとして切り出されているか」。

## 手元で比べるコマンド

```
# 裏で呼ばれるプロセスを表示（実行はしない）
gcc   -### x.c
clang -### x.c

# 中間表現を見る
gcc -O2 -c x.c -fdump-tree-gimple -fdump-tree-optimized   # x.c.*.gimple / x.c.*.optimized
gcc -O2 -c x.c -fdump-rtl-final                            # RTL の最終形
clang -O2 -S -emit-llvm x.c -o x.ll                        # LLVM IR

# 最適化の報告
gcc   -O2 -fopt-info-vec-missed -c x.c
clang -O2 -Rpass-missed=loop-vectorize -c x.c

# クロスコンパイル
aarch64-linux-gnu-gcc -O2 -S x.c          # GCC: ターゲット専用のコンパイラ
clang --target=aarch64-linux-gnu -O2 -S x.c   # Clang: 同じ clang で切り替え
```

## 関連メモ

[LLVM の構成と仕組み](https://memo.taka1156.site/md/llvm.md) [Rust](https://memo.taka1156.site/md/rust.md) [WebAssembly](https://memo.taka1156.site/md/webassembly.md) [Linux のプロセス](https://memo.taka1156.site/md/linux-process.md) [プログラミング言語の系譜](https://memo.taka1156.site/md/language-genealogy.md)

## 参考

- [GNU Compiler Collection (GCC) Internals](https://gcc.gnu.org/onlinedocs/gccint/)
- [GCC Internals: GIMPLE](https://gcc.gnu.org/onlinedocs/gccint/GIMPLE.html)
- [GCC Internals: RTL Representation](https://gcc.gnu.org/onlinedocs/gccint/RTL.html)
- [libgccjit](https://gcc.gnu.org/onlinedocs/jit/)
- [Clang Internals Manual](https://clang.llvm.org/docs/InternalsManual.html)
- [Clang: Cross-compilation using Clang](https://clang.llvm.org/docs/CrossCompilation.html)
- [LLVM Language Reference Manual](https://llvm.org/docs/LangRef.html)
- [GCC Runtime Library Exception](https://www.gnu.org/licenses/gcc-exception-3.1.html)
- [LLVM License (Apache 2.0 with LLVM Exceptions)](https://llvm.org/LICENSE.txt)
