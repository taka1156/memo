<!-- scripts/memo.py build が自動生成。手で編集しない -->

# 実装起因の脆弱性（リクエストと権限）

> CSRF・セッションハイジャック・SSRF・オープンリダイレクト・認可不備（IDOR）を、攻撃の流れと NG/OK コードで図解。Cookie の自動送信・サーバーからの URL 取得・権限の確認漏れを突く攻撃の防ぎ方。

- URL: https://memo.taka1156.site/request-vulnerabilities.html
- タグ: セキュリティ, バックエンド
- 日付: 2026-11-08

---

ブラウザが自動で送るもの・サーバーが代わりに取りに行くもの・権限の確認漏れを突く攻撃

**ざっくり言うと**

- **CSRF** はブラウザが **自動で送る Cookie** を、 **セッションハイジャック** は Cookie の中の **セッション ID（ログインの鍵）を盗む・固定する** ことを悪用する。SameSite・トークン・ログイン時の ID 再生成で防ぐ
- **SSRF・オープンリダイレクト** は、外から来た URL をサーバーが取りに行く・そのまま転送するのが原因。接続先・転送先を **許可リストで決める**
- **認可不備（IDOR）** は、「このユーザーのデータか」の確認漏れ。ライブラリ任せにできず、毎回の確認を **設計に組み込む**

入力をそのまま解釈させるもの（XSS・SQL インジェクション・OS コマンドインジェクション・ReDoS・パストラバーサル）と、対策の共通の考え方は [実装起因の脆弱性（入力の扱い）](https://memo.taka1156.site/md/web-vulnerabilities.md) にまとめています。

## 全体マップ

入力の中身そのものより、ブラウザ・サーバー・権限の仕組みの穴を突く攻撃です。カードを押すと各セクションへ。

ブラウザが Cookie を自動で付ける

CSRF

セッション ID ＝ ログインの鍵

セッションハイジャック

サーバーが、外から来た URL を取りに行く

SSRF

外から来た URL へ、そのまま転送する

オープンリダイレクト

「誰のデータか」の確認漏れ

認可不備 (IDOR)

| 脆弱性 | 何が起きる | 根本対策 | 補助・多層防御 |
| --- | --- | --- | --- |
| CSRF | ログイン中のユーザーに、意図しない操作をさせる | SameSite Cookie ＋ トークン or Origin / Sec-Fetch-Site 検証 | 重要操作の再認証 |
| セッションハイジャック | 他人としてログインされる | 推測不能な ID、ログイン時に再生成、Secure / HttpOnly | 有効期限、重要操作の再認証 |
| SSRF | サーバー経由で内部ネットワークやクラウドのメタデータにアクセス | 接続先の許可リスト | 内部宛ての遮断、IMDSv2 |
| オープンリダイレクト | 正規ドメインを踏み台にフィッシングへ誘導 | 自サイト内のパスだけ許可 | — |
| IDOR | ID を書き換えて他人のデータを見る・変える | 毎回「このユーザーの持ち物か」を確認 | 推測しにくい ID（それだけでは不十分） |

## CSRF Cross-Site Request Forgery

ブラウザは、どのサイトから送られたリクエストでも、 **宛先サイトの Cookie を自動で付けてきた** 。これを利用して、ログイン中のユーザーに罠サイトから「送金」「パスワード変更」などのリクエストを送らせる攻撃です。攻撃者はレスポンスを読めませんが、 **操作が実行されれば十分** です。

このページの攻撃の流れでは、 **赤い番号の段で攻撃が成立する** （対策はその段を止めること）。

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

（元のページで操作できます → https://memo.taka1156.site/request-vulnerabilities.html#session）

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

✗ 誤解: POST にしたので CSRF は大丈夫

✓ 正しくは: 罠サイトのフォームから POST は送れる。SameSite・トークン・送信元の検証が必要。

✗ 誤解: https なのでセッションは盗まれない

✓ 正しくは: XSS・固定・URL への ID 漏れ・推測しやすい ID は https と関係ない。
