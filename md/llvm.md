<!-- scripts/memo.py build が自動生成。手で編集しない -->

# LLVM の構成と仕組み

> LLVM がフロントエンド・LLVM IR・最適化パス・バックエンドの 3 段でどう機械語を作るかを、実際の IR とアセンブリの出力で図解する

- URL: https://memo.taka1156.site/llvm.html
- タグ: 言語, 開発ツール
- 日付: 2026-11-06

---

ソースコードが「共通の中間表現」を通って機械語になるまで

シリーズ: **LLVM の構成と仕組み** [GCC と Clang の構成比較 →](https://memo.taka1156.site/md/gcc-vs-clang.md)

**ざっくり言うと**

- LLVM は 1 つのコンパイラではなく、コンパイラを作るための **部品（ライブラリ）の集まり** 。C/C++ 用の Clang、Rust、Swift などが土台に使う。
- 真ん中に **LLVM IR** という共通の中間表現があり、「言語ごとのフロントエンド」と「CPU ごとのバックエンド」を切り離している。
- 最適化は LLVM IR に対する **パス (pass)** の積み重ね。どの言語から来ても同じ最適化がかかる。

## 3 段構成: なぜ真ん中に IR を置くのか

言語が M 個、CPU が N 種類あるとき、それぞれを直接つなぐと M×N 個の変換器が要る。間に共通の IR を挟めば、フロントエンド M 個とバックエンド N 個、合わせて M+N 個で済む。最適化も IR の上に 1 回書けば全言語・全 CPU で効く。

共通 IR なし

LLVM IR あり

線 1 本が「誰かが作って保守する変換器」。言語や CPU を 1 つ足したときに増える線の数を比べるとわかりやすい。

（元のページで操作できます → https://memo.taka1156.site/llvm.html#three-phase）

## clang で C をコンパイルしたときの流れ

各段をクリック（タップ）すると、何をしているかと、その段の出力を見るコマンドが出る。

フロントエンド（Clang） ミドルエンド（LLVM IR の最適化） バックエンド（コード生成）

**前処理** #include・マクロ

**構文解析** 字句 → AST

**意味解析** 型チェック (Sema)

**IR 生成** AST → LLVM IR

**最適化** パスの列

**命令選択** IR → 機械命令

**レジスタ割付** 仮想 → 物理

**MC** .s / .o を出力

**リンク** ld / lld

（元のページで操作できます → https://memo.taka1156.site/llvm.html#pipeline）

## LLVM IR の中身

LLVM IR は「型付きで、レジスタを無限に使えるアセンブリ」のような言語。テキスト形式 ( `.ll` )、バイナリ形式のビットコード ( `.bc` )、メモリ上のデータ構造の 3 つの姿があり、相互に変換できる。

入れ子の構造

Module 1 ファイル分。target triple・datalayout

Function @add など。引数と戻り値の型

BasicBlock entry: など。途中で分岐しない命令の列

Instruction add・load・br…。最後は必ず終端命令（ret・br・switch・unreachable など）

GlobalVariable @g など

読むときの 4 つのルール

- `@` はグローバル（関数・大域変数）、 `%` はローカルの値。
- 値には必ず型がつく: `i32` （32bit 整数）、 `i1` （真偽）、 `ptr` （ポインタ）。
- **SSA** (静的単一代入): 各 `%値` は 1 回だけ代入される。再代入したいときは新しい名前を作る。
- 合流点で「どこから来たか」で値を選ぶのが `phi` 命令。

### SSA と phi: 変数 r が 2 か所で代入されるとき

C のソース

-O0 の IR

mem2reg 後

```
int max(int a, int b) {
  int r;
  if (a > b) r = a;
  else       r = b;
  return r;
}
```

```
define dso_local i32 @max(i32 noundef %a, i32 noundef %b) {
entry:
  %a.addr = alloca i32, align 4      ; 変数はまずスタック上の箱 (alloca)
  %b.addr = alloca i32, align 4
  %r = alloca i32, align 4
  store i32 %a, ptr %a.addr, align 4
  store i32 %b, ptr %b.addr, align 4
  %0 = load i32, ptr %a.addr, align 4
  %1 = load i32, ptr %b.addr, align 4
  %cmp = icmp sgt i32 %0, %1         ; signed greater than
  br i1 %cmp, label %if.then, label %if.else

if.then:
  %2 = load i32, ptr %a.addr, align 4
  store i32 %2, ptr %r, align 4
  br label %if.end

if.else:
  %3 = load i32, ptr %b.addr, align 4
  store i32 %3, ptr %r, align 4
  br label %if.end

if.end:
  %4 = load i32, ptr %r, align 4
  ret i32 %4
}
```

フロントエンドは「変数 = メモリの箱」として素直に出す。SSA を守るために変数を 1 回代入に直す仕事は、最適化側 (mem2reg) に任せている。

```
define dso_local i32 @max(i32 noundef %a, i32 noundef %b) {
entry:
  %cmp = icmp sgt i32 %a, %b
  br i1 %cmp, label %if.then, label %if.else

if.then:
  br label %if.end

if.else:
  br label %if.end

if.end:
  %r.0 = phi i32 [ %a, %if.then ], [ %b, %if.else ]
  ret i32 %r.0
}
```

alloca・load・store が消え、r は `phi` 1 つになった。「if.then から来たら %a、if.else から来たら %b」。

clang 18 (x86-64 Linux) の実際の出力。読みやすさのため関数属性 ( `#0` )・メタデータ・ `; preds` コメントは省いた。リリース版の clang は既定で値の名前を捨てる（ `%0` などの番号になる）ので、名前を残すには `-fno-discard-value-names` をつける。

（元のページで操作できます → https://memo.taka1156.site/llvm.html#ssa）

## 最適化 = パスを順に当てていく

LLVM の最適化は、IR を受け取って IR を返す小さな変換（パス）の列。 `-O2` はそのレシピ（パイプライン）に名前をつけたもの。 `opt` コマンドでパスを 1 つずつ当てると、何が起きているかが見える。

← 前

次のパス →

```

```

元のソース: `static int sq(int x) { return x * x; }` と `int f(void) { int a = 3; return sq(a) + 1; }` 。各段は opt 18 で実際に当てた結果（関数 f の部分だけ抜粋）。-O0 の IR には `noinline` が付くので、inline の段は `-force-remove-attribute=sq:noinline` と `forceattrs` パス のように noinline を外してから当てている。

（元のページで操作できます → https://memo.taka1156.site/llvm.html#passes）

### よく出てくるパス

| パス | やること | 効く場面 |
| --- | --- | --- |
| `mem2reg` / `sroa` | スタック上の変数を SSA の値に置き換える | ほぼすべての関数。以降のパスの前提を作る |
| `inline` | 呼び出し先の本体を埋め込む | 小さな関数・ゲッター。定数が伝わり、他の最適化の入口になる |
| `instcombine` | 命令の組み合わせを簡単な形に書き換える（覗き穴最適化） | `x*2` → `x<<1` 、比較＋選択 → `smax` など |
| `simplifycfg` | 空のブロックや不要な分岐をまとめる | if/else が単純なときは `select` （分岐なし）に変える |
| `gvn` | 同じ計算を 2 回しない（共通部分式の除去） | 同じ式・同じ load の繰り返し |
| `licm` | ループ内で変わらない計算をループの外に出す | ループ内の `strlen(s)` や配列の長さ |
| `loop-vectorize` / `slp-vectorizer` | SIMD 命令でまとめて計算する | 配列の一括処理 |

パスには、IR を読んで情報を出すだけの **解析パス** （支配木、ループ情報、エイリアス解析など）と、IR を書き換える **変換パス** がある。今の LLVM は「新しいパスマネージャ (new pass manager)」が解析結果をキャッシュし、変換で壊れたものだけを計算し直す。

## バックエンド: IR から CPU の命令へ

同じ IR でも、どの CPU 向けかでここから先が分かれる。各 CPU の命令・レジスタ・呼び出し規約は **TableGen** という記述言語 ( `.td` ファイル) で書かれ、そこから命令選択の表などが自動生成される。

1. 命令選択

IR の命令を、その CPU の命令に当てはめる。SelectionDAG（基本ブロックをグラフにして照合）、-O0 向けの高速な FastISel、GlobalISel（関数単位で段階的に変換）の 3 方式がある。

2. MIR とスケジューリング

CPU 命令の形になったが、レジスタはまだ仮想 (Machine IR)。命令の並び順を CPU のパイプラインに合わせて調整する。

3. レジスタ割付

無限にあった値を、実際のレジスタ（x86-64 なら汎用 16 本）に割り当てる。入りきらない値はスタックに退避 (spill)。

4. MC 層

命令をアセンブリ文字列か機械語バイト列に変える。 **アセンブラを内蔵** しているので、外部の `as` を呼ばずに直接 `.o` を書ける。

### 同じ IR、違う CPU

上の `add` と `max` の IR（-O2 後）を、 `--target` だけ変えて出力した結果。

LLVM IR (-O2)

x86-64

AArch64

```
define dso_local i32 @add(i32 noundef %a, i32 noundef %b) {
entry:
  %add = add nsw i32 %b, %a
  ret i32 %add
}

define dso_local noundef i32 @max(i32 noundef %a, i32 noundef %b) {
entry:
  %a.b = tail call i32 @llvm.smax.i32(i32 %a, i32 %b)   ; 組み込み関数 (intrinsic)
  ret i32 %a.b
}
```

```
add:
	leal	(%rdi,%rsi), %eax     # アドレス計算命令で足し算
	retq

max:
	movl	%esi, %eax
	cmpl	%esi, %edi
	cmovgl	%edi, %eax        # 条件付き移動 (分岐なし)
	retq
```

```
add:
	add	w0, w1, w0
	ret

max:
	cmp	w0, w1
	csel	w0, w0, w1, gt    // 条件付き選択 (分岐なし)
	ret
```

clang 18 の出力から `.cfi_*` などのディレクティブを省いた。引数の入るレジスタ（x86-64 は `edi` / `esi` 、AArch64 は `w0` / `w1` ）は各 OS の呼び出し規約で決まっている。

（元のページで操作できます → https://memo.taka1156.site/llvm.html#targets）

## LLVM プロジェクトの部品と、使っている言語

llvm-project に入っている主な部品

| `clang` | C / C++ / Objective-C のフロントエンド。 `clang-format` もここ。 `clangd` ・ `clang-tidy` は隣の `clang-tools-extra` に入っている |
| --- | --- |
| `lld` | リンカ。GNU ld より速いことが多い |
| `lldb` | デバッガ |
| `libc++` | C++ 標準ライブラリ |
| `compiler-rt` | ランタイム補助と sanitizer（ASan・UBSan など） |
| `MLIR` | IR を何層も重ねるための枠組み。機械学習コンパイラ等が使う |
| `flang` | Fortran のフロントエンド |

LLVM をバックエンドに使う言語・ツール

C / C++ (Clang) Rust Swift Julia Kotlin/Native Zig（リリースビルド） Emscripten (C→Wasm) GPU シェーダ・CUDA 系

どれも「自分の言語の解析と、言語固有の中間表現」までを自前で持ち、その先を LLVM IR にして渡す。Rust なら HIR・MIR で借用チェックを済ませてから LLVM IR にする（ [Rust のメモ](https://memo.taka1156.site/md/rust.md) ）。

LLVM の最適化は強力な反面、コンパイルが遅くなりがち。Zig は x86-64 向けのデバッグビルドを自前のバックエンドに切り替え（0.15 以降。Windows などを除く）、Rust も Cranelift バックエンドを試験提供している。「速く出すのは自前、よく最適化するのは LLVM」という使い分け。

## LTO と JIT: IR を「後で」使う

LTO

ThinLTO

JIT

普通は `.c` 1 つずつ最適化するので、別ファイルの関数はインライン化できない。 `-flto` をつけると `.o` の中身が機械語ではなく **ビットコード** になり、リンク時に全ファイルの IR をまとめて最適化する。

効果は大きいが、リンクが 1 か所に集中して遅く、メモリも食う。

`-flto=thin` 。各ファイルの要約（どの関数をどこから呼ぶか）だけを全体で見て、「このファイルにはあのファイルの関数を取り込む」と決めたら、最適化はファイルごとに並列で行う。フル LTO に近い効果で、並列化とインクリメンタルビルドが効く。

IR を実行時に機械語にしてすぐ動かす。LLVM には **ORC JIT** という JIT 用の API があり、Julia などが使う。コンパイル時間がそのまま待ち時間になるので、JavaScript エンジンのような「とにかく早く動かす」用途では、LLVM より軽い自前の JIT を使うことが多い。

（元のページで操作できます → https://memo.taka1156.site/llvm.html#lto）

## よくある誤解

✗ 誤解: LLVM は仮想マシン (VM) である

✓ 正しくは: 元は Low Level Virtual Machine の略だったが、今は正式に略語ではなく、JVM のような実行環境でもない。LLVM IR は「仮想的な命令セット」として設計されたが、普段は事前コンパイル (AOT) で機械語にしてから配る。

✗ 誤解: LLVM IR はどの CPU でも動く共通フォーマット

✓ 正しくは: IR の命令自体は CPU に依存しないが、フロントエンドが出す IR には `target triple` ・データレイアウト（ポインタの大きさ、アライメント）・呼び出し規約が埋め込まれ、 `sizeof` などは IR 生成の時点で数値になっている。x86-64 向けに出した IR を AArch64 向けに使い回すことは基本的にできない。CPU に依存しない配布形式が欲しいなら [WebAssembly](https://memo.taka1156.site/md/webassembly.md) のような、そのために設計された形式を使う。

✗ 誤解: Clang = LLVM

✓ 正しくは: Clang は LLVM を使う C 系言語のフロントエンド（とドライバ）で、LLVM の利用者の 1 つ。 `clang` コマンドが内部で LLVM のライブラリを呼んでいる。GCC と比べた構成の違いは [GCC と Clang の構成比較](https://memo.taka1156.site/md/gcc-vs-clang.md) へ。

✗ 誤解: -O3 にすれば必ず速くなる

✓ 正しくは: -O3 はより積極的なインライン化・ループ変換を足すが、コードが大きくなって命令キャッシュに乗らず、かえって遅くなることもある。速さを決めるのは計測。サイズ優先なら `-Os` / `-Oz` 。

## 手元で各段を見るコマンド

```
# C → LLVM IR（テキスト）。名前を残し、-O0 でも後から opt を当てられるようにする
# （ただし noinline は残るので、inline を試すときは下のように外す）
clang -S -emit-llvm -O0 -Xclang -disable-O0-optnone -fno-discard-value-names x.c -o x.ll

# パスを指定して当てる（new pass manager の書き方）
opt -S -passes='mem2reg,instcombine' x.ll -o x2.ll
opt -S -force-remove-attribute=sq:noinline -passes='forceattrs,function(mem2reg),cgscc(inline)' x.ll
opt -S -passes='default<O2>' x.ll -o x-o2.ll     # -O2 と同じレシピ

# IR → アセンブリ / オブジェクト
llc x-o2.ll -o x.s
llc -mtriple=aarch64-linux-gnu x-o2.ll -o x-arm.s

# clang が裏で何を呼んでいるか（-cc1 と リンカ）
clang -### x.c

# 最適化で何が起きたか / 起きなかったかの報告
clang -O2 -Rpass=inline -Rpass-missed=loop-vectorize -c x.c
```

## 関連メモ

- [GCC と Clang の構成比較](https://memo.taka1156.site/md/gcc-vs-clang.md) — GCC との構成の違い
- [Rust 学習フローと仕組み](https://memo.taka1156.site/md/rust.md) — LLVM を使う言語の例
- [WebAssembly](https://memo.taka1156.site/md/webassembly.md) — LLVM が出力できる先の 1 つ
- [メモリ管理](https://memo.taka1156.site/md/memory-management.md) — 言語ごとのメモリの解放方式
- [プログラミング言語の系譜](https://memo.taka1156.site/md/language-genealogy.md) — Rust・Swift など LLVM を使う言語の親子関係

## 参考

- [The LLVM Compiler Infrastructure](https://llvm.org/)
- [LLVM Language Reference Manual](https://llvm.org/docs/LangRef.html)
- [Using the New Pass Manager](https://llvm.org/docs/NewPassManager.html)
- [The LLVM Target-Independent Code Generator](https://llvm.org/docs/CodeGenerator.html)
- [TableGen Overview](https://llvm.org/docs/TableGen/)
- [Clang: ThinLTO](https://clang.llvm.org/docs/ThinLTO.html)
- [The Architecture of Open Source Applications: LLVM (Chris Lattner)](https://aosabook.org/en/v1/llvm.html)
