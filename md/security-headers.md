<!-- scripts/memo.py build が自動生成。手で編集しない -->

# セキュリティヘッダー

> CSP・HSTS・nosniff・frame-ancestors・Referrer-Policy・Permissions-Policy から COOP/CORP、Cookie 属性、使わなくなったヘッダーまで、何を防ぐか・推奨値・導入時の落とし穴を図解。

- URL: https://memo.taka1156.site/security-headers.html
- タグ: セキュリティ, フロントエンド
- 日付: 2026-11-03

---

レスポンスに数行足すだけで、ブラウザが攻撃の一部を代わりに止めてくれる

**ざっくり言うと**

- セキュリティヘッダーは **ブラウザへの指示** 。アプリの脆弱性そのものは直さないが、悪用されたときの被害を小さくする「多層防御」の 1 枚
- 最優先は **CSP・HSTS・nosniff・frame-ancestors** 。そこに Referrer-Policy と Permissions-Policy で情報漏れと権限を絞る
- Cookie の属性（ `HttpOnly` / `Secure` / `SameSite` ）と COOP / CORP も同じ発想。 `X-XSS-Protection` のような古いヘッダーは今は **使わない**

## 全体像: どのヘッダーが何を防ぐか

カードを押すと各セクションへ飛びます。 必須 はどのサイトでも入れる、 推奨 は入れておきたい、 用途次第 は必要なときに入れる、の目安です。

Content-Security-Policy 必須

**防ぐ** XSS で注入されたスクリプトの実行、データの外部送信

Strict-Transport-Security 必須

**防ぐ** HTTP への格下げ（SSL ストリップ）・盗聴

X-Content-Type-Options 必須

**防ぐ** MIME スニッフィングで画像やテキストがスクリプト扱いされる

frame-ancestors / X-Frame-Options 必須

**防ぐ** クリックジャッキング（透明 iframe で押させる）

Referrer-Policy 推奨

**防ぐ** URL に含まれるトークンや個人情報が外部サイトへ漏れる

Permissions-Policy 推奨

**防ぐ** カメラ・位置情報などを、注入されたコードや埋め込みに使われる

COOP / CORP / COEP 推奨

**防ぐ** 別タブからの window 操作、XS-Leaks、Spectre 型の読み取り

Set-Cookie の属性 必須

**防ぐ** Cookie の盗聴・JS からの窃取・クロスサイト送信 (CSRF)

Cache-Control / Clear-Site-Data など 用途次第

**防ぐ** 個人情報のキャッシュ残り、ログアウト後のデータ残り

### ヘッダーが効く場所

どれも **ブラウザが守るルール** です。 `curl` やサーバー間通信、攻撃者が自分で書いたスクリプトには関係ありません。「サーバーの入力チェック」の代わりにはならず、 **アプリに穴があったときに、ブラウザ上での悪用を難しくする** ものだと考えます。実装側の対策は [実装起因の脆弱性（入力の扱い）](https://memo.taka1156.site/md/web-vulnerabilities.md) と [実装起因の脆弱性（リクエストと権限）](https://memo.taka1156.site/md/request-vulnerabilities.md) のページへ。

## まず入れるセット

一般的な Web アプリ（自前のフロント＋API、外部に iframe で埋め込ませない）の出発点です。各値の意味は下のセクションで説明します。

生ヘッダー

nginx

Express (helmet)

```
Content-Security-Policy: default-src 'self'; script-src 'nonce-{毎回ランダム}' 'strict-dynamic';
  object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
Set-Cookie: __Host-sid=…; Path=/; Secure; HttpOnly; SameSite=Lax
```

CSP は実際には 1 行で書きます（見やすさのため改行）。 `default-src 'self'` のままだと外部フォントやインライン `style` も止まるので、使うものに合わせて `style-src` や `font-src` などを足します。

```
# server ブロックに書く。always を付けないとエラー応答 (4xx/5xx) に付かない
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'" always;
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
add_header Cross-Origin-Opener-Policy "same-origin" always;
add_header Cross-Origin-Resource-Policy "same-origin" always;
server_tokens off;   # Server ヘッダーからバージョンを消す
```

**nginx の落とし穴:** `location` の中で 1 つでも `add_header` を書くと、既定では親（ `server` ）の `add_header` は **その location では全部消えます** （継承されない）。nginx 1.29.3 以降なら `add_header_inherit merge;` で親の値を引き継げます。それより古い版では、共通部分を include ファイルにまとめ、各 location で読み込むのが安全です。静的サイトでは毎回 nonce を作れないので、 `script-src 'self'` （インライン script を書かない）か、ハッシュ `'sha256-…'` を使います。

```
import crypto from 'node:crypto';
import helmet from 'helmet';

// リクエストごとに nonce を作り、テンプレートからも使えるようにする
app.use((req, res, next) => {
  res.locals.nonce = crypto.randomBytes(16).toString('base64');
  next();
});

app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      scriptSrc: [(req, res) => `'nonce-${res.locals.nonce}'`, "'strict-dynamic'"],
      objectSrc: ["'none'"],
      baseUri: ["'none'"],
      frameAncestors: ["'none'"],
    },
  },
  strictTransportSecurity: { maxAge: 63072000, includeSubDomains: true, preload: true },
}));

// テンプレート側: <script nonce="<%= nonce %>">…</script>
```

helmet は既定で nosniff・X-Frame-Options・Referrer-Policy・COOP/CORP などを付け、 `X-Powered-By` を外し、 `X-XSS-Protection: 0` を返します。Permissions-Policy は helmet に含まれないので、必要なら自分で `res.setHeader` します。

（元のページで操作できます → https://memo.taka1156.site/security-headers.html#recommended）

## Content-Security-Policy (CSP)

「このページで **どこから来たスクリプト・画像・通信先なら使ってよいか** 」をブラウザに伝えるヘッダー。XSS でタグを差し込まれても、許可されていないスクリプトは実行されません。XSS 対策の **2 枚目の壁** です（1 枚目は出力時のエスケープ）。

主なディレクティブ

nonce 方式

導入の手順

| ディレクティブ | 決めること | よく使う値 |
| --- | --- | --- |
| `default-src` | 個別指定がない種類の既定値（フォールバック） | `'self'` |
| `script-src` | 実行してよいスクリプト。 CSP の本体 | `'nonce-…' 'strict-dynamic'` |
| `style-src` | CSS の読み込み元・インライン style | `'self'` （必要なら `'unsafe-inline'` ） |
| `img-src` / `font-src` / `media-src` | 画像・フォント・音声動画の取得元 | `'self' data:` など |
| `connect-src` | fetch / XHR / WebSocket の接続先。 盗んだデータの送り先を絞る | `'self' https://api.example.com` |
| `object-src` | <object> / <embed>（古いプラグイン） | `'none'` |
| `base-uri` | <base href> の書き換え（相対 URL の乗っ取り） | `'none'` か `'self'` |
| `form-action` | フォームの送信先 | `'self'` |
| `frame-ancestors` | 自分を iframe に埋め込めるサイト（ クリックジャッキング ） | `'none'` |
| `upgrade-insecure-requests` | ページ内の http:// のサブリソースを https に読み替える | 値なし |
| `report-to` | 違反レポートの送り先（ `Reporting-Endpoints` ヘッダーで名前を定義） | `csp` |

`default-src` がフォールバックするのは「取得元」系のディレクティブだけです。 `frame-ancestors` ・ `base-uri` ・ `form-action` は `default-src` では埋まらないので、個別に書きます。

ホスト名を並べる「許可リスト方式」（ `script-src 'self' https://cdn.example.com` ）は、その CDN に JSONP や古いライブラリがあると回避されやすく、実際によく破られてきました。今の推奨は **nonce（またはハッシュ）方式の strict CSP** です。

1. サーバーが **レスポンスごとに** 推測できない乱数（nonce）を作る
2. ヘッダーに `script-src 'nonce-R4nd0m'` 、自分の `<script nonce="R4nd0m">` にも同じ値を入れる
3. XSS で差し込まれた `<script>` や `onclick=` は nonce を知らない → **実行されない**
4. `'strict-dynamic'` があれば、nonce 付きスクリプトが動的に読み込んだスクリプトも許可（バンドラーやタグマネージャーが動く）

```
Content-Security-Policy:
  script-src 'nonce-R4nd0m' 'strict-dynamic' https: 'unsafe-inline';
  object-src 'none'; base-uri 'none'
```

末尾の `https: 'unsafe-inline'` は **古いブラウザ向けのフォールバック** 。nonce を理解するブラウザは `'unsafe-inline'` を、 `'strict-dynamic'` を理解するブラウザはホスト指定（ `https:` ）を無視するので、新しいブラウザでは厳しいまま動きます。

- nonce は **毎回変える** 。固定値やキャッシュされた HTML に埋まった値は、攻撃者に読まれたら終わり
- 静的 HTML（CDN 配信の SPA など）で nonce が使えないなら、インラインスクリプトの **ハッシュ** （ `'sha256-…'` ）を使う
- `'unsafe-eval'` は `eval` / `new Function` を許すので、できるだけ外す

いきなり本番で強制すると、見落としていたインラインスクリプトや外部タグが止まって画面が壊れます。 **Report-Only で様子を見てから強制** が定石です。

1. `Content-Security-Policy-Report-Only` で配信（ブロックせず違反を報告するだけ）
2. レポートを集め、正当な違反（自前のインライン JS、計測タグなど）を潰す
3. 違反が落ち着いたら `Content-Security-Policy` に切り替えて強制
4. 強制後もレポートを残し、新機能で壊れていないか監視する

```
Reporting-Endpoints: csp="https://example.com/csp-report"
Content-Security-Policy-Report-Only: script-src 'nonce-R4nd0m' 'strict-dynamic'; object-src 'none'; base-uri 'none'; report-to csp
```

古い `report-uri` は非推奨ですが、まだ対応ブラウザが多いので `report-to` と併記されることもあります。

**<meta> で書く CSP の制限:** `<meta http-equiv="Content-Security-Policy">` でも CSP は書けますが、 `frame-ancestors` ・ `report-to` / `report-uri` ・ `sandbox` は **無視されます** 。Report-Only も meta では使えません。可能な限りレスポンスヘッダーで送ります。

もう一歩: Trusted Types

`require-trusted-types-for 'script'` を CSP に足すと、 `innerHTML` や `eval` などの危険な API に **素の文字列を渡すとエラー** になり、DOM ベース XSS の入口を強制的に塞げます。サニタイザーを通した値（TrustedHTML）だけが通ります。Chromium 系が先行し、Safari 26・Firefox 148 も対応したので、2026 年 2 月から主要ブラウザすべてで使えます（Baseline 2026）。古いブラウザも対象なら、まず Report-Only で試すのがおすすめです。

（元のページで操作できます → https://memo.taka1156.site/security-headers.html#csp）

## Strict-Transport-Security (HSTS)

「このサイトには **今後 https でしかつながない** で」とブラウザに覚えさせるヘッダー。http → https のリダイレクトだけだと、 **最初の http リクエスト** が平文で飛ぶので、公衆 Wi-Fi などで書き換えられます（SSL ストリップ）。

リダイレクトだけ

HSTS あり

preload

1. ユーザーがアドレスバーに `example.com` と入力 → `http://` で送信
2. 同じ Wi-Fi の攻撃者が通信を横取りし、https へのリダイレクトを握りつぶす
3. 攻撃者がサーバーとは https、ユーザーとは http で中継 → ログイン情報や Cookie が丸見え
1. 一度 https でアクセスしたとき、 `Strict-Transport-Security` を受け取る
2. 以降 `max-age` の間、ブラウザは http の URL を **送信前に内部で https に書き換える**
3. 証明書エラーが出ても「無視して進む」を許さない

弱点: **初回アクセス** （またはキャッシュが切れた後の最初の 1 回）は守れない。

1. `max-age` 1 年以上・ `includeSubDomains` ・ `preload` を付けて配信
2. hstspreload.org から申請 → ブラウザに組み込まれるリストに載る
3. ブラウザは **初回から** https でしかつながない

リストから外すのは時間がかかります（ブラウザの更新が行き渡るまで）。全サブドメインが https 化できているか確認してから申請します。

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

**導入時の注意:** `includeSubDomains` を付けると、http でしか動かない社内サブドメイン（古い管理画面など）が **開けなくなります** 。最初は `max-age=300` 程度の短い値で試し、問題がなければ伸ばします。HSTS は https のレスポンスに付けたものだけが有効です（http のレスポンスの HSTS は無視される）。

（元のページで操作できます → https://memo.taka1156.site/security-headers.html#hsts）

## X-Content-Type-Options: nosniff

ブラウザには、 `Content-Type` が怪しいときに中身を見て種類を推測する **MIME スニッフィング** という機能があります。これを止めるヘッダーです。

1. 攻撃者が「プロフィール画像」や `.txt` として、中身が JavaScript のファイルをアップロード
2. 別のページで `<script src="/uploads/evil.txt">` と読み込ませる
3. nosniff なし: 推測でスクリプトとして実行されうる（自ドメインなので CSP の `'self'` も通る）
4. nosniff あり: `script` / `style` は MIME タイプが合わなければブロック

```
X-Content-Type-Options: nosniff
```

値は `nosniff` だけ。前提として、サーバーが正しい `Content-Type` （ `; charset=utf-8` 込み）を返していることが大事です。ユーザーのアップロードファイルは、できれば **別ドメイン** から `Content-Disposition: attachment` で配ると、さらに安全です。

## frame-ancestors / X-Frame-Options（クリックジャッキング）

攻撃者のページが、あなたのサイトを **透明な iframe** で重ね、ユーザーに見えているボタン（罠）を押させて、実際には下に隠れたあなたのサイトのボタンを押させる攻撃です。

（図: 罠サイト（ユーザーに見えている） / 🎉 おめでとうございます！ / 賞品を受け取る / 透明な iframe（opacity: 0） / 本物の「送金を確定」 / クリックは / いちばん上の / iframe に届く / ログイン中なら / 本当に送金される → https://memo.taka1156.site/security-headers.html#framing）

見えている罠のボタンと、見えない本物のボタンの位置を合わせておく

| 書き方 | 意味 |
| --- | --- |
| `Content-Security-Policy: frame-ancestors 'none'` | どこからも埋め込ませない（推奨） |
| `frame-ancestors 'self'` | 同じオリジンからだけ許可 |
| `frame-ancestors https://partner.example` | 特定サイトだけ許可（複数書ける） |
| `X-Frame-Options: DENY` / `SAMEORIGIN` | 旧方式。古いブラウザ向けに併記してよい |

両方あるとき、対応ブラウザは `frame-ancestors` を優先します。 `X-Frame-Options: ALLOW-FROM` は今のブラウザでは効かないので、特定サイトを許可したいときは `frame-ancestors` を使います。どちらも **<meta> では効きません** 。

## Referrer-Policy

リンクや画像の読み込み時に、 **直前のページの URL** を `Referer` ヘッダーで送るかどうかを決めます。パスワード再設定 URL（ `/reset?token=…` ）や検索語などが、外部の画像・広告・解析サービスに漏れるのを防ぎます。

| 値 | 同じオリジンへ | 別オリジン (https→https) | https→http |
| --- | --- | --- | --- |
| `no-referrer` | 送らない | 送らない | 送らない |
| `same-origin` | 完全な URL | 送らない | 送らない |
| `strict-origin-when-cross-origin` 推奨 | 完全な URL | オリジンだけ | 送らない |
| `unsafe-url` 避ける | 完全な URL | 完全な URL | 完全な URL |

`strict-origin-when-cross-origin` は今のブラウザの既定値ですが、明示しておけば古い環境や設定の違いに左右されません。トークンを URL に載せる画面だけは `no-referrer` にすると安心です（そもそも秘密は URL に載せないのが原則）。

## Permissions-Policy

カメラ・マイク・位置情報・決済などの **強い機能を、このページ（と埋め込み先）が使えるかどうか** を決めます。使わない機能を切っておけば、XSS や埋め込んだ広告・ウィジェットに悪用されません。

```
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
# () = 誰にも許可しない / (self) = 自分だけ / (self "https://maps.example") = 自分と指定先
```

iframe 側でも `<iframe allow="camera">` のように許可が必要で、ヘッダーで禁止した機能は iframe の `allow` でも有効になりません。旧名の `Feature-Policy` は書き方が違うので、今は Permissions-Policy で書きます。

## COOP / CORP / COEP（クロスオリジン分離）

Spectre（CPU の投機実行を使ってメモリを読む攻撃）や XS-Leaks（別サイトの状態を間接的に盗み見る攻撃）への対策として加わった 3 つのヘッダーです。名前が似ているので、 **誰との関係を切るのか** で覚えます。

| ヘッダー | 切る関係 | 推奨値 | 注意 |
| --- | --- | --- | --- |
| `Cross-Origin-Opener-Policy` (COOP) | 自分を `window.open` した／された 別サイトのウィンドウ との参照（ `window.opener` ） | `same-origin` | OAuth や決済のポップアップで opener を使うなら `same-origin-allow-popups` |
| `Cross-Origin-Resource-Policy` (CORP) | 自分のリソース （画像・JS・API レスポンス）を、別サイトが <img> や <script> で読み込むこと | `same-origin` か `same-site` | 他サイトに配る画像・CDN の資産は `cross-origin` |
| `Cross-Origin-Embedder-Policy` (COEP) | 自分のページ が、許可のない別サイトのリソースを読み込むこと | 必要なときだけ `require-corp` / `credentialless` | COOP と合わせると `crossOriginIsolated` になり `SharedArrayBuffer` などが使える。外部リソースが壊れやすい |

CORS（ `Access-Control-Allow-Origin` ）は逆に **制限を緩める** ヘッダーです。詳しくは [CORS と同一オリジンポリシー](https://memo.taka1156.site/md/cors-sop.md) へ。

## Set-Cookie の属性

セッション ID を入れた Cookie は「盗まれたらそのままログインされる鍵」です。属性で、 **どこへ・いつ・誰に** 送られるかを絞ります。

```
Set-Cookie: __Host-sid=8f3a…; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=3600
```

| 属性 | 効果 | 防ぐもの |
| --- | --- | --- |
| `Secure` | https の通信でだけ送る | 平文通信での盗聴 |
| `HttpOnly` | JS（ `document.cookie` ）から読めない | XSS による Cookie の持ち出し |
| `SameSite=Lax` | 別サイトからのリクエストには、トップレベルの GET 遷移（リンククリック）でだけ送る | CSRF の大半 |
| `SameSite=Strict` | 別サイト経由では一切送らない | CSRF。ただし外部リンクから来ると未ログイン表示になる |
| `SameSite=None` | 常に送る（ `Secure` 必須） | なし。埋め込みウィジェットなど本当に必要なときだけ |
| `__Host-` 接頭辞 | `Secure` ・ `Path=/` ・ `Domain` なしでないと ブラウザが受け付けない | サブドメインからの Cookie 上書き（セッション固定） |

Chrome 系は `SameSite` 未指定を `Lax` 扱いにしますが、ブラウザによって挙動が違うので **必ず明示** します。 `Domain=example.com` を付けると全サブドメインに送られるので、付けない方が安全です。

## その他、場面によって使うもの

| ヘッダー | 使う場面 |
| --- | --- |
| `Cache-Control: no-store` | マイページ・明細など個人情報を含むレスポンス。共有 PC のブラウザキャッシュや、設定ミスの CDN に残さない（ [HTTP キャッシュ](https://memo.taka1156.site/md/http-cache.md) ） |
| `Clear-Site-Data: "cache", "cookies", "storage"` | ログアウト時に、そのサイトの Cookie・ストレージ・キャッシュをブラウザに消させる |
| `Server` / `X-Powered-By` を消す | 使っているソフトとバージョンの宣伝をやめる（効果は小さいが手間もない） |
| `Access-Control-Allow-*` | 別オリジンの JS に API を読ませたいときだけ。 `*` と Cookie 付きの組み合わせに注意（ [CORS](https://memo.taka1156.site/md/cors-sop.md) ） |

## もう使わない・古いヘッダー

古い記事やチェックツールに出てくるが、今は入れない（または無効化する）ものです。

| ヘッダー | 状況 | どうする |
| --- | --- | --- |
| `X-XSS-Protection` | ブラウザ内蔵の XSS フィルタ用。主要ブラウザでフィルタは廃止され、フィルタ自体が情報漏れの原因にもなった | `0` にするか、送らない。代わりに CSP |
| `Public-Key-Pins` (HPKP) | 証明書の固定。設定ミスでサイトを長期間開けなくする事故が多く、廃止 | 送らない |
| `Expect-CT` | Certificate Transparency の強制。CT が標準で必須になり不要に | 送らない |
| `Feature-Policy` | Permissions-Policy の旧名 | Permissions-Policy に置き換える |
| `X-Frame-Options: ALLOW-FROM` | 今のブラウザは無視（＝保護なし） | `frame-ancestors` を使う |

## ヘッダーをチェックしてみる

ターミナルで `curl -sI https://自分のサイト` を実行し、出てきたレスポンスヘッダーを貼り付けてください。このページの中だけで判定し、どこにも送信しません。

チェックする

よくある設定例を入れる

| 項目 | 判定 | 内容 |
| --- | --- | --- |

簡易チェックです。CSP の中身が実際に安全かは、ページの作りによって変わります。

（元のページで操作できます → https://memo.taka1156.site/security-headers.html#checker）

## よくある誤解

✗ 誤解: CSP を入れたので、出力のエスケープは手を抜いていい

✓ 正しくは: CSP は 2 枚目の壁。 `'unsafe-inline'` が残っていたり、許可したドメインに抜け道があったりすると素通りする。エスケープが 1 枚目。

✗ 誤解: http → https のリダイレクトがあれば HSTS はいらない

✓ 正しくは: リダイレクト前の最初の http リクエストが書き換えられる。HSTS（できれば preload）で、ブラウザが最初から https を使うようにする。

✗ 誤解: ヘッダーは HTML ページにだけ付ければいい

✓ 正しくは: API の JSON やアップロードファイルにも nosniff・CORP は必要。エラーページ（404 / 500）にも付くよう、サーバーやフレームワーク全体で設定する。

✗ 誤解: HttpOnly にしたので XSS されても大丈夫

✓ 正しくは: Cookie は読まれないが、XSS したスクリプトはそのページ上で **ユーザーとしてリクエストを送れる** 。被害が減るだけで、XSS 自体は防げない。
