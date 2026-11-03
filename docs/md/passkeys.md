<!-- scripts/memo.py build が自動生成。手で編集しない -->

# パスキー（WebAuthn）

> 公開鍵で署名するパスキーの登録・ログインの流れ、フィッシングに強い理由、同期型と端末固定型の違い、実装時のチェックリストまでを図解。

- URL: https://memo.taka1156.site/passkeys.html
- タグ: セキュリティ
- 日付: 2026-11-03

---

「秘密を送る」ログインから「秘密で署名する」ログインへ

**ざっくり言うと**

- パスキーは **サイトごとの公開鍵ペア** 。秘密鍵は端末（やパスワードマネージャー）から出ず、サーバーには公開鍵しか置かない。
- ログインは「サーバーが出した使い捨ての問題（チャレンジ）に秘密鍵で署名する」だけ。 **送るものは毎回違い、盗まれても使い回せない** 。
- ブラウザが **本物のドメインにしか署名させない** ので、偽サイトに誘導されても渡すものが無い。これがパスワード＋SMS との最大の違い。

## 登録の流れ

認証器

端末・鍵マネージャー

ブラウザ

サーバー（RP）

← チャレンジ・RP ID・ユーザー情報

登録オプションを作る

← create()

`navigator.credentials.create()`

本人確認（指紋・顔・PIN）→ **鍵ペアを生成** 、秘密鍵は保管

公開鍵・ID →

オリジンを添えて送る

**公開鍵** と credential ID を保存

RP（Relying Party）＝ログインさせる側のサイト。RP ID は通常そのドメイン（例: `example.com` ）で、鍵はこの RP ID に紐づけて作られる。

## ログインの流れ

認証器

ブラウザ

サーバー（RP）

← 使い捨てのチャレンジ

ランダム値を発行

← get()

`navigator.credentials.get()`

今のオリジンと RP ID を確認

本人確認 → チャレンジ＋オリジン情報に **秘密鍵で署名**

署名 →

署名を送る

保存した **公開鍵で検証** 。チャレンジ・オリジン・RP ID が一致すれば OK

指紋や顔のデータは端末の中で「本人か」を確かめるのに使うだけで、サーバーには送られない。サーバーが受け取るのは「本人確認した」という印（UV フラグ）と署名だけ。

## なぜフィッシングに強い？

メールのリンクを踏んだ先がどちらかで、何が起きるかを比べる。

本物 example.com

偽物 examp1e.com

（元のページで操作できます → https://memo.taka1156.site/passkeys.html#phishing）

## 同期型と端末固定型

同期パスキー（synced）

iCloud キーチェーン、Google パスワードマネージャー、1Password などに保存され、 **同じアカウントの端末間で同期** される。機種変更しても使え、一般ユーザー向けの主流。

安全性はそのマネージャーのアカウント保護に依存する。

端末固定パスキー（device-bound）

YubiKey などのセキュリティキーや、管理された業務端末の中だけにあり、 **コピーできない** 。管理者アカウントや厳しい社内要件向け。

失くすと使えないので、予備のキーを必ず登録しておく。

手元にパスキーが無い PC でも、画面の QR コードをスマホで読むと、Bluetooth で近くにあることを確かめたうえでスマホのパスキーでログインできる（ハイブリッド方式）。

## ほかの方式との比較

| 方式 | フィッシング | サーバー漏えい時 | 使い回し | 手間 |
| --- | --- | --- | --- | --- |
| パスワードのみ | 弱い | ハッシュが解かれる恐れ | 起きがち | 覚える・打つ |
| ＋ SMS コード | 弱い（コードも中継される） | パスワード分は残る | パスワード次第 | 届くのを待つ |
| ＋ TOTP アプリ | 弱い（6桁も中継される） | 共有シークレットが漏れる | パスワード次第 | アプリを開いて打つ |
| パスキー | 強い（ドメインに紐づく） | 公開鍵だけ＝無害 | 構造上できない | 指紋・顔・PIN だけ |

SMS や TOTP は「本物そっくりの偽サイトが、入力されたコードをその場で本物に転送する」中継型フィッシングに負ける。パスキーは署名に本物のオリジンが入るので中継しても通らない。

## 実装するときのチェックリスト

- **ライブラリを使う** ：署名・CBOR・各種フラグの検証は自前で書かない（例: SimpleWebAuthn、各言語の WebAuthn ライブラリ）。
- **チャレンジはサーバーで毎回生成** し、セッションに紐づけて一度だけ受け付ける。
- **オートフィルに出す** ：ユーザー名欄に `autocomplete="username webauthn"` を付け、 `get({ mediation: 'conditional' })` を呼ぶと、入力欄の候補にパスキーが並ぶ。
- **1 アカウントに複数のパスキー** を登録できるようにする（スマホ・PC・予備のキー）。一覧で名前を付けて削除できるように。
- **復旧手段を設計する** ：全部の端末を失ったときの道（メール確認＋再登録、サポート窓口など）。ここが弱いと結局そこが狙われる。
- **パスワードはすぐ消さない** ：まずは「追加のログイン方法」として導入し、パスキーでログインした人に促して段階的に移す。
- **ドメインを決めてから始める** ：パスキーは RP ID（ドメイン）に紐づく。複数ドメインで共有したいなら Related Origin Requests（ `/.well-known/webauthn` ）を使う。

```
// ログイン画面：オートフィルにパスキーを出す
const options = await fetch('/webauthn/login-options').then(r => r.json());
const cred = await navigator.credentials.get({
  publicKey: PublicKeyCredential.parseRequestOptionsFromJSON(options),
  mediation: 'conditional',
});
await fetch('/webauthn/verify', { method: 'POST', body: JSON.stringify(cred) });
```

## よくある誤解

✕ 指紋や顔のデータがサーバーに送られる

○ 生体情報は端末内で本人確認に使うだけ。サーバーに届くのは署名と「本人確認済み」のフラグ。

✕ パスキー対応サイトがハッキングされたら、パスキーも盗まれる

○ サーバーにあるのは公開鍵だけ。公開鍵では署名できないので、漏れても他人がログインすることはできない。

✕ スマホを失くしたらログインできなくなる

○ 同期パスキーなら、同じアカウントの別端末や新しい端末に戻ってくる。端末固定型は予備を登録しておくのが前提。

## いまの動き（2026年）

- **WebAuthn Level 3** ：2026年8月に W3C 勧告（正式な標準）になった。オートフィル中にパスキーを作る conditional create、削除などをマネージャーに伝える Signal API、対応機能を問い合わせる `getClientCapabilities()` 、JSON 変換ヘルパーなどが入り、主要ブラウザで実装が進んでいる。
- **パスキーの引っ越し（CXP / CXF）** ：FIDO Alliance が、パスワードマネージャー間でパスキーを安全に移す仕組みを作っている。データ形式の CXF は 2025年8月に Proposed Standard になったが、受け渡しの手順を決める CXP はまだ草案の段階。Apple は OS 26 系で対応を始めているが、マネージャー間の自由な移行はまだ広がりつつある段階。

## 関連

[OAuth 2.0 / OIDC のフロー](https://memo.taka1156.site/md/oauth-oidc.md) [JWT とセッション](https://memo.taka1156.site/md/jwt-vs-session.md) [CORS と同一オリジンポリシー](https://memo.taka1156.site/md/cors-sop.md)

## 参考

- [W3C: Web Authentication Level 3](https://www.w3.org/TR/webauthn-3/)
- [passkeys.dev（実装ガイド）](https://passkeys.dev/)
- [FIDO Alliance: Passkeys](https://fidoalliance.org/passkeys/)
- [WebAuthn Level 3 is now a W3C Recommendation（FIDO Alliance, 2026-08）](https://fidoalliance.org/webauthn-level-3-is-now-a-w3c-recommendation/)
- [Credential Exchange Format v1.0（Proposed Standard）](https://fidoalliance.org/specs/cx/cxf-v1.0-ps-20250814.html)
- [WebAuthn Level 3: What's New in the Passkey Standard](https://guptadeepak.com/webauthn-level-3-whats-new-in-the-passkey-standard/)
- [Credential Exchange Protocol (CXP) / Format (CXF)（Corbado）](https://www.corbado.com/blog/credential-exchange-protocol-cxp-credential-exchange-format-cxf)
