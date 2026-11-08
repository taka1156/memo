<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Git の内部構造

> blob・tree・commit・ref の4つで Git を理解し、merge と rebase の違い、reset の3種類、reflog での復旧までを図解。

- URL: https://memo.taka1156.site/git-internals.html
- タグ: 開発ツール
- 日付: 2026-11-03

---

オブジェクト4種類とポインタだけで、ほぼ全部が説明できる

**ざっくり言うと**

- Git の中身は **中身のハッシュを名前にしたファイル（オブジェクト）** の山。blob・tree・commit の3種類（＋タグ）が主役。
- ブランチや HEAD は、 **コミットを指すだけの小さなポインタ（ref）** 。作るのも消すのも一瞬で、消してもコミット自体は残る。
- merge・rebase・reset は「新しいコミットを作るか」「ポインタをどこへ動かすか」の違い。困ったら `reflog` でほぼ取り戻せる。

## 4種類のオブジェクト

BLOB

ファイルの **中身だけ** 。ファイル名も権限も持たない。同じ中身なら何ファイルあっても blob は1つ。

TREE

ディレクトリ1つ分の一覧。「名前・モード → blob か tree のハッシュ」を並べたもの。サブディレクトリは入れ子の tree。

COMMIT

ルート tree のハッシュ ＋ 親コミット ＋ 作者・日時・メッセージ。 **差分ではなく、その時点の全体のスナップショット** を指す。

TAG（注釈付き）

コミットに名前・署名・メッセージを付けたオブジェクト。軽量タグは下の ref と同じただのポインタ。

どのオブジェクトも名前は中身のハッシュ（今は既定で SHA-1、40 桁）。中身が1バイトでも変われば別の名前になるので、過去のコミットを「こっそり書き換える」ことはできない。

## つながり方

（図: HEAD / main / C2 / commit / C1 / parent / tree / README / app.js v2 / app.js v1 → https://memo.taka1156.site/git-internals.html#graph）

ref（ポインタ） commit tree blob

README は変更していないので、C1 と C2 の tree は **同じ blob を共有** している。毎回スナップショットでも容量が膨らまないのはこのため（さらに pack ファイルで差分圧縮される）。

### 自分の目で見る

```
# HEAD が指している先（ブランチ名が書いてあるだけ）
cat .git/HEAD                  # ref: refs/heads/main
git rev-parse main             # main が指すコミットのハッシュ

# オブジェクトの種類と中身
git cat-file -t HEAD           # commit
git cat-file -p HEAD           # tree ... / parent ... / author ...
git cat-file -p 'HEAD^{tree}'  # 100644 blob 3b18e5... README.md
```

## 3つの置き場所

作業ツリー いま編集しているファイル

インデックス 次のコミットの下書き（staging）

リポジトリ .git/objects のコミット

`git add` →

`git commit` →

← `git restore`

`git add` した時点で blob はもう作られている。インデックスは「どのパスにどの blob を置くか」の一覧で、 `commit` はそれを tree にして固めるだけ。

## git commit で起きること

1. **インデックスから tree を作る** ディレクトリごとに tree オブジェクトを書き出す（変わっていない部分は既存の tree をそのまま使う）。
2. **commit オブジェクトを作る** ルート tree・親（今の HEAD が指すコミット）・作者・メッセージを書き、ハッシュを計算して保存。
3. **今のブランチを新しいコミットに動かす** `refs/heads/main` の中身を新しいハッシュに書き換える。HEAD は main を指したままなので、結果的に HEAD も進む。

HEAD がブランチではなくコミットを直接指している状態が「detached HEAD」。ここでコミットすると、どのブランチからも辿れないコミットができる（ブランチを作れば救える）。

## merge・rebase・squash

同じ「feature を main に取り込む」でも、履歴の形が変わる。

取り込む前

merge

rebase

squash merge

（図: A / B / C / D / E / main / feature → https://memo.taka1156.site/git-internals.html#merge-rebase）

B から分岐したあと、main にも C が入った状態。

（図: A / B / C / D / E / M / main → https://memo.taka1156.site/git-internals.html#merge-rebase）

**親を2つ持つマージコミット M** を作る。既存のコミットは一切書き換えないので、共有ブランチでも安全。分岐した事実が履歴に残る。

（図: A / B / C / D' / E' / D / E / feature / 参照なし（reflog には残る） → https://memo.taka1156.site/git-internals.html#merge-rebase）

D・E の変更を C の後ろに **新しいコミット D'・E' として作り直す** 。親が変わるのでハッシュも別物。履歴は一直線になるが、元の D・E を持っている人とは食い違う。 **push 済みの共有ブランチでは使わない** のが原則。

（図: A / B / C / S / D / E / main → https://memo.taka1156.site/git-internals.html#merge-rebase）

D＋E の変更をまとめた **親が1つだけの普通のコミット S** を作る（GitHub の「Squash and merge」）。main はきれいだが、feature の D・E とはつながっていないので、Git は「feature は取り込み済み」と判定できない。feature ブランチはそのまま使い続けず消す。

## reset の3種類

`git reset <コミット>` は「 **今のブランチ** をそのコミットへ動かす」。どこまで巻き戻すかがオプションで変わる。

| オプション | ブランチ（HEAD） | インデックス | 作業ツリー | 使いどころ |
| --- | --- | --- | --- | --- |
| `--soft` | 動く | そのまま | そのまま | 直前のコミットをやり直す（変更は add 済みで残る） |
| `--mixed` （既定） | 動く | 戻る | そのまま | add をやり直したい |
| `--hard` | 動く | 戻る | 戻る | 変更ごと捨てる。 未コミットの変更は戻せない |

共有ブランチの過去を取り消したいときは、履歴を書き換える reset ではなく、打ち消しコミットを足す `git revert` を使う。

## reflog で取り戻す

ブランチを消しても、rebase や reset --hard で「消えた」ように見えても、 **コミットオブジェクトはしばらく残っている** 。HEAD やブランチが過去にどこを指していたかは reflog（ローカルだけの移動履歴）に記録されている。ただし **ブランチを削除するとそのブランチ自身の reflog も消える** ので、消したブランチの先端は HEAD の reflog（そのブランチで作業していたときの記録）から探す。

```
git reflog
# a1b2c3d HEAD@{0}: rebase (finish): returning to refs/heads/feature
# 9f8e7d6 HEAD@{3}: commit: E を追加   ← rebase 前の E

git branch rescue 9f8e7d6      # そこにブランチを立てれば復活
git reset --hard ORIG_HEAD     # 直前の rebase / merge / reset を丸ごと取り消す
```

どこからも参照されないコミットは、reflog の期限（既定で 30〜90 日）を過ぎたあと `git gc` で消える。 **一度もコミットしていない変更は reflog にも無い** ので、reset --hard の前は `git stash` しておくと安全。

## よくある誤解

✗ 誤解: コミットは前回からの差分を保存している

✓ 正しくは: コミットは全体のスナップショット（tree）を指す。差分は表示のたびに2つの tree を比べて計算している。保存時の差分圧縮は pack ファイルの別の仕組み。

✗ 誤解: ブランチを削除するとそのコミットも消える

✓ 正しくは: 消えるのはポインタだけ。コミットは reflog から辿れるうちは復元できる。

✗ 誤解: rebase はコミットを移動する

✓ 正しくは: 同じ変更内容の **新しいコミットを作り直す** 。元のコミットは残ったまま、ブランチが新しい方を指し直すだけ。

## これからの変更（Git 3.0）

- **ハッシュが SHA-256 に** ：新規リポジトリの既定が SHA-1 から SHA-256 へ。オブジェクト名が 64 桁になる。ホスティング側の対応が鍵で、GitLab は対応済み、GitHub はベータ段階と案内されている。
- **ref の保存形式が reftable に** ：ブランチ1本＝ファイル1つの方式から、まとめて保存する形式へ。ブランチやタグが大量にあるリポジトリで速く、更新も壊れにくい。
- **既定のブランチ名が main に** ： `git init` で作られるブランチ名が master から main へ。

予定では 2.56（2026年9月）→ 2.98（2026年12月）→ 2.99 と 3.0（2027年春）。3.0 は 2.99 と機能が同じで、破壊的変更のスイッチだけが切り替わる。オブジェクトと ref の考え方自体は変わらない。

## 関連

[GitHub サービス](https://memo.taka1156.site/md/github-services.md) [DB のしくみ（WAL も「先に記録」）](https://memo.taka1156.site/md/db-internals.md)

## 参考

- [Pro Git「Git Internals - Git Objects」](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)
- [git-reset ドキュメント](https://git-scm.com/docs/git-reset) / [git-reflog ドキュメント](https://git-scm.com/docs/git-reflog)
- [What's new in Git 2.56.0（GitLab, 2026-09）](https://about.gitlab.com/blog/whats-new-in-git-2-56-0/)
- [Git 3.0 will use main as the default branch（thoughtbot）](https://thoughtbot.com/blog/git-3-0-will-use-main-as-the-default-branch)
