<!-- scripts/memo.py build が自動生成。手で編集しない -->

# キー入力から Ctrl+C まで：端末・シェル・カーネルの流れ

> キー入力や Ctrl+C が、ターミナル・擬似端末・ラインディシプリン・シェル・カーネルをどう通ってプロセスに届くかを、OS の層の図とステップで 1 本の流れとしてたどる。

- URL: https://memo.taka1156.site/linux-process-signal.html
- タグ: Linux
- 日付: 2026-11-06

---

# キー入力から Ctrl+C まで

端末・シェル・カーネルを通って、キー入力とシグナルがプロセスに届く流れ

[キー入力の流れ](https://memo.taka1156.site/md/linux-process-signal.md) [端末とシェル](https://memo.taka1156.site/md/linux-terminal.md) [プロセス](https://memo.taka1156.site/md/linux-process.md) [シグナルとジョブ制御](https://memo.taka1156.site/md/linux-signal.md)

**ざっくり言うと**

- ターミナルは「画面とキーボード」、シェルは「コマンドを起動するプログラム」。どちらも普通のプロセスで、間をつなぐ **端末デバイス（擬似端末）とラインディシプリンはカーネルの中** にある。
- プロセスは `fork` （自分を複製）→ `exec` （中身を別のプログラムに入れ替え）→ `wait` （親が終了を回収）で生まれて消える。
- シグナルはカーネルがプロセスに付ける「割り込みの印」。Ctrl+C も `kill` も、カーネルが印を付け、プロセスが次に動くときに既定動作・ハンドラ・無視のどれかで処理される。

## OS の層とシステムコール

Linux は大きく **ユーザー空間** と **カーネル空間** に分かれる。アプリはハードウェアを直接触れず、必ず **システムコール (system call)** でカーネルに頼む。シェルもターミナルも、ユーザー空間で動くただのプロセス。

**ユーザー空間 (user space)** — 普通のプロセス。互いのメモリは見えない

ターミナルエミュレータ シェル (bash / zsh) ls・vim・python … sshd systemd (PID 1)

↕ システムコール: read write fork execve wait4 kill ioctl …

**カーネル (kernel)** — 全プロセスの管理者。特権モードで動く

プロセス管理・スケジューラ シグナル配送 メモリ管理 VFS・ファイル TTY / PTY・ラインディシプリン デバイスドライバ ネットワーク

↕ 割り込み・I/O

**ハードウェア**

CPU メモリ ディスク キーボード・画面 NIC

システムコールの入口と出口は、カーネルがシグナルを処理する大事なタイミングでもある（後述）。

## キー入力の旅（ステップで追う）

シナリオを選んで「次へ」を押すと、そのとき関わる部品が光る。

ls ⏎ を打つ

sleep 中に Ctrl+C

ウィンドウを閉じる

HARDWARE

**キーボード / 画面** キー入力は GUI（X11 / Wayland）経由でターミナルへ届く

↕

USER SPACE

**ターミナルエミュレータ** キー → バイト列、バイト列 → 描画。PTY マスターの fd を持つ

↕ write / read

KERNEL

**PTY マスター**

↕

**ラインディシプリン (n_tty)** 行編集・エコー・改行変換・特殊文字 → シグナル

↕

**PTY スレーブ /dev/pts/3**

**プロセス管理・シグナル** 対象を選んで処理待ち (pending) に印を付け、動くときに処理させる

↕ read / write（fd 0, 1, 2）

USER SPACE

**シェル bash** セッションリーダー。プロンプトを出し、行を読み、コマンドを起動する

**コマンド ls / sleep** bash の子。同じ /dev/pts/3 を stdin/stdout/stderr として受け継ぐ

← 前へ

次へ →

最初から

それぞれの部品の詳細は、 [端末とシェル](https://memo.taka1156.site/md/linux-terminal.md) ・ [プロセス](https://memo.taka1156.site/md/linux-process.md) ・ [シグナルとジョブ制御](https://memo.taka1156.site/md/linux-signal.md) で。

（元のページで操作できます → https://memo.taka1156.site/linux-process-signal.html#path）
