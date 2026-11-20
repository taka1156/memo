<!-- scripts/memo.py build が自動生成。手で編集しない -->

# SAML 2.0

> SAML 2.0 の SP 起点フロー、アサーションの中身、SP が検証すべきこと、OIDC との使い分けを図解。

- URL: https://memo.taka1156.site/saml.html
- タグ: セキュリティ, バックエンド
- 日付: 2026-11-20

---

署名付き XML でログイン結果を渡すフェデレーションと、SP が確かめること

[SSO の方式](https://memo.taka1156.site/md/sso-methods.md) SAML 2.0 [OAuth 2.0 / OIDC](https://memo.taka1156.site/md/oauth-oidc.md)

**ざっくり言うと**

- SAML は SSO のフェデレーション方式の 1 つで、ログインは IdP が受け持ち、アプリ（SP）は結果を信用する
- IdP は署名した XML（アサーション）を、ブラウザ経由で SP に POST して渡す
- アサーションは利用者の手元を通るので、SP は署名・宛先・期限・使い回しを必ず検証する

## SAML の位置づけ

SAML (Security Assertion Markup Language) 2.0 は OASIS が定めた、SSO の **フェデレーション方式** のプロトコル。ログインは **IdP** (Identity Provider：Okta、Microsoft Entra ID、Google Workspace、Keycloak など) だけが受け持ち、各アプリ（SAML では **SP** ：Service Provider）は IdP が署名した「この人は誰か」の証明を検証してログインさせる。SP にパスワードは一切渡らない。

SSO を実現するほかの方式（リバースプロキシ・代理認証など）との違いと、2 回目のログインが要らない理由は [SSO の方式](https://memo.taka1156.site/md/sso-methods.md) を参照。

## SAML の用語

| 用語 | 何か |
| --- | --- |
| アサーション (Assertion) | IdP が発行する「誰が・いつ・どう認証されたか」の XML。署名付き。SAML の中身そのもの |
| AuthnRequest | SP から IdP への「この人を認証して」という要求 |
| SAMLResponse | IdP から SP への応答。中にアサーションが入る |
| Entity ID | IdP・SP それぞれを識別する名前（URL の形が多い） |
| ACS URL | Assertion Consumer Service。SP が SAMLResponse を受け取る URL |
| NameID | アサーション内のユーザー識別子。メールアドレス形式や、IdP が振る固定の ID など |
| メタデータ | Entity ID・エンドポイント・署名用の証明書をまとめた XML。IdP と SP は事前にこれを交換して信頼関係を作る |
| RelayState | ログイン後に戻したいページなどを運ぶ値。SAML 自体は中身を解釈しない |

## SP 起点のフロー

利用者がまずアプリを開くいちばん普通の流れ。SP から IdP へは **HTTP-Redirect** （要求を圧縮して URL のクエリに載せる）、IdP から SP へは **HTTP-POST** （自動送信される HTML フォーム）で運ぶ組み合わせが多い。 **どのメッセージもブラウザを経由する** のがポイントで、SP と IdP がサーバー同士で直接話すことは基本的にない（例外は、応答を SP が IdP へ取りに行く Artifact binding）。

（図: ブラウザ / SP（アプリ） / IdP / 1 / アプリを開く / 2 / AuthnRequest / 3 / SAMLRequest を IdP へ / 4 / ログイン（パスワード・MFA） / 5 / SAMLResponse（フォーム） / 6 / POST ACS URL / 7 / 検証 → ログイン → https://memo.taka1156.site/saml.html#flow）

← 前へ

次へ →

全体を見る

全体

### 全体

矢印をタップするか「次へ」で 1 ステップずつ見られる。IdP にすでにログイン済みなら、手順 4 は飛ばされて 3 のあとすぐ 5 になる（ [2 段のセッション](https://memo.taka1156.site/md/sso-methods.md) ）。

### 1. アプリを開く

SP は自分のセッション Cookie が無いので、未ログインと判断する。開こうとしたページは RelayState などに覚えておく。

### 2. IdP へリダイレクト

SP は `AuthnRequest` を作り、その `ID` を手元に保存する（手順 7 の `InResponseTo` 照合に使う）。XML を DEFLATE 圧縮・Base64 化して、IdP の SSO URL へのリダイレクトに載せる。

### 3. IdP が要求を受け取る

IdP は要求元の Entity ID と ACS URL が、事前に登録された SP のものかを確かめる。未登録の ACS URL に応答を送ると、アサーションが第三者に渡ってしまうため。

### 4. ログイン（IdP のセッションが無いときだけ）

パスワード・MFA・パスキーなど、認証の方法は IdP が決める。SP はパスワードを一切見ない。成功すると IdP 自身のセッション Cookie が発行される。

### 5. 署名付きの応答を返す

IdP は自分の秘密鍵で署名したアサーションを `SAMLResponse` に入れ、ACS URL に自動送信される HTML フォームとして返す。アサーションは URL に収まらないほど大きいので、POST で運ぶ。

### 6. ブラウザが SP に POST する

ここで応答は **利用者の手元を通っている** 。開発者ツールで中身を見たり、書き換えて送ったりできる。だから次の検証が欠かせない。

### 7. SP が検証してログインさせる

署名・発行者・宛先・期限・要求との対応を確かめ（ SP が検証すること ）、通ったら SP 自身のセッション Cookie を発行して、覚えておいたページへ戻す。

### IdP 起点のフロー

IdP のポータル（アプリのタイル一覧）から始める流れ。手順 1〜3 が無く、IdP がいきなり手順 5 の応答を SP に送る。SP は要求を出していないので `InResponseTo` で照合できず、 **盗んだ応答や攻撃者自身の応答を差し込まれても見分けにくい** （攻撃者のアカウントで被害者をログインさせる、など）。

対応できるなら SP 起点に寄せる。ポータルのタイルを SP のログイン開始 URL へのリンクにすれば、利用者の操作は同じまま SP 起点になる。

## アサーションの中身

要点だけに絞った例。実物はもっと長く、名前空間や署名の XML が付く。

```
<saml:Assertion ID="_a75adf55" IssueInstant="2026-11-20T00:00:00Z">
  <saml:Issuer>https://idp.example.com</saml:Issuer>     <!-- 発行した IdP -->
  <ds:Signature>…</ds:Signature>                        <!-- IdP の署名 -->
  <saml:Subject>
    <saml:NameID>00u1a2b3c4</saml:NameID>               <!-- 誰か -->
    <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
      <!-- InResponseTo: どの要求への応答か / Recipient: 届け先 / NotOnOrAfter: この時刻より前に使う -->
      <saml:SubjectConfirmationData
        InResponseTo="_req_9f2c"
        Recipient="https://kintai.example.com/saml/acs"
        NotOnOrAfter="2026-11-20T00:05:00Z"/>
    </saml:SubjectConfirmation>
  </saml:Subject>
  <saml:Conditions NotBefore="…" NotOnOrAfter="…">
    <saml:AudienceRestriction>
      <saml:Audience>https://kintai.example.com</saml:Audience>  <!-- 誰向けか -->
    </saml:AudienceRestriction>
  </saml:Conditions>
  <saml:AuthnStatement AuthnInstant="2026-11-20T00:00:00Z"/>   <!-- いつ認証したか -->
  <saml:AttributeStatement>…メール・部署・グループ…</saml:AttributeStatement>
</saml:Assertion>
```

`bearer` は「持っている人を本人とみなす」という意味。お札と同じで、盗まれればそのまま使われるので、期限を短くし、使い回しを拒否する。

ユーザーを識別するキーは、変わらない `NameID` （と IdP の Issuer の組）にする。メールアドレスは改姓や異動で変わりうるので主キーにしない。属性（部署・グループ）は IdP から届くが、それで **何をしてよいか** を決めるのは SP 側の [認可](https://memo.taka1156.site/md/authorization-models.md) の仕事。

## SP が検証すること

ライブラリが多くをやってくれるが、設定次第で抜けるものもある。抜けると、他人になりすましてログインされうる。

1. **署名を、登録済みの証明書で検証する** メタデータで事前に受け取った IdP の証明書を使う。応答の中（ `KeyInfo` ）に入っている証明書を信用すると、攻撃者が自分の鍵で署名した応答も通ってしまう。署名の無い応答・アサーションは拒否する
2. **署名された要素そのものを読む** XML は署名済みの要素の隣に偽の要素を足せる。「どこかに正しい署名がある」と確かめたあと別の要素を読むと、偽の中身でログインされる（XML 署名ラッピング攻撃、XSW）
3. **発行者と宛先を照合する** `Issuer` が信頼する IdP、 `Audience` が自分の Entity ID、 `Recipient` ・ `Destination` が自分の ACS URL であること。別のアプリ向けに発行されたアサーションの流用を防ぐ
4. **期限を確かめる** `NotBefore` ・ `NotOnOrAfter` の範囲内か。サーバーの時計がずれていると正しい応答も弾くので、許容は数分程度にとどめる
5. **自分が出した要求への応答か確かめる** SP 起点なら `InResponseTo` が手順 2 で保存した ID と一致すること
6. **使い回しを拒否する** アサーションの `ID` を期限まで記録し、同じものが 2 度来たら拒否する（リプレイ対策）

アサーションを暗号化して応答に入れる `EncryptedAssertion` もある。中身（属性）をブラウザから隠せるが、改ざん対策はあくまで署名の検証が担う。

## SAML と OIDC の使い分け

どちらも「IdP が認証し、アプリはその結果を検証して信用する」点は同じ。違いは運び方と、得意な場面。OIDC の流れは [OAuth 2.0 / OIDC のフロー](https://memo.taka1156.site/md/oauth-oidc.md) を参照。

|  | SAML 2.0 | OIDC |
| --- | --- | --- |
| 認証結果の形 | 署名付き XML（アサーション） | 署名付き JSON（ID トークン、JWT） |
| 運び方 | アサーションそのものをブラウザ経由で POST | 認可コードフロー（今の推奨）では、ブラウザで運ぶのは認可コードだけ。トークンはサーバー同士で受け取る |
| 得意な場面 | ブラウザで使う業務 SaaS・社内システム | Web に加えてスマホアプリ・SPA |
| API の呼び出し | 仕組みに含まれない（ログインのため） | OAuth のアクセストークンで API を呼べる |
| 設定・鍵の更新 | メタデータ XML を交換。証明書の期限切れで手作業の差し替えが起きやすい | Discovery と JWKS の URL から自動で取れ、鍵の入れ替えも追従しやすい |
| 実装の注意 | XML 署名の検証が難しく、自前実装は避ける | JWT の検証（署名・ `aud` ・ `exp` ・ `nonce` ）を怠らない |

目安として、 **取引先の企業 IdP と SAML でつなぐことを求められる** （企業向け SaaS で「SAML SSO 対応」が必須条件、など）なら SAML。新しく作るアプリで、スマホや API まで含めて考えるなら OIDC。多くの IdP はどちらも話せるので、1 つの IdP が SAML と OIDC のアプリを同時に受け持つのも普通。

## ログアウト（SLO）

SAML には各 SP をまとめてログアウトさせる **SLO** (Single Logout) がある。ただ対応していない SP も多い。よく使われるのはブラウザで各 SP を順に回る方式（フロントチャネル）で、1 つが応答しないとそこで止まる。サーバー同士で SOAP を使う方式もあるが、対応はさらに少ない。IdP でログアウトしても **各 SP のセッションは残る** と考えて設計する。退職者の扱いは [SSO の方式](https://memo.taka1156.site/md/sso-methods.md) を参照。

## よくある誤解

✗ 誤解: SAMLResponse は HTTPS で届くので、中身をそのまま信じてよい

✓ 正しくは: HTTPS が守るのは通信路だけで、応答は利用者のブラウザを通って届く。利用者（攻撃者）は中身を書き換えて送れるので、登録済みの証明書での署名検証が必須。

✗ 誤解: 署名が付いていることを確かめれば安全

✓ 正しくは: どの鍵で署名されたか（登録済みの IdP の証明書か）と、署名された要素を実際に読んでいるか（XSW）まで確かめないと、攻撃者が作った応答が通る。XML 署名の検証は自前で書かず、保守されているライブラリに任せる。

✗ 誤解: アサーションを暗号化していれば、署名の検証は省いてよい

✓ 正しくは: 暗号化は SP の公開鍵で行うので、SP の公開鍵を知っている人なら誰でも暗号化したアサーションを作れる。暗号化が隠すのは中身だけで、IdP が発行したことの証明は署名の検証にしかできない。

✗ 誤解: IdP でログアウトすれば、すべての SP からログアウトされる

✓ 正しくは: SLO に対応していない SP や、途中で失敗した SP のセッションは残る。共用 PC などでは、各 SP のセッションを短くする・ブラウザを閉じさせるなどの手当てが要る。

## 関連メモ

- [SSO の方式](https://memo.taka1156.site/md/sso-methods.md) — SAML 以外の SSO の方式と、どれを選ぶか
- [OAuth 2.0 / OIDC のフロー](https://memo.taka1156.site/md/oauth-oidc.md) — フェデレーションのもう一つの主流のプロトコル
- [JWT とセッション](https://memo.taka1156.site/md/jwt-vs-session.md) — SSO のあと各アプリが持つセッションの作り方
- [PKI と証明書チェーン](https://memo.taka1156.site/md/pki-certificates.md) ・ [暗号の基礎](https://memo.taka1156.site/md/crypto-basics.md) — アサーションの署名と、IdP の証明書を信頼する仕組み
- [認可モデル（RBAC・ABAC・ReBAC）](https://memo.taka1156.site/md/authorization-models.md) — IdP から届いたグループ・属性で、何を許可するかを決める
- [パスキー（WebAuthn）](https://memo.taka1156.site/md/passkeys.md) — IdP のログイン手段として組み合わせる

## 参考

- [SAML V2.0 Technical Overview](https://docs.oasis-open.org/security/saml/Post2.0/sstc-saml-tech-overview-2.0.html) （OASIS。SP 起点・IdP 起点のフローとバインディング）
- [Assertions and Protocols for SAML V2.0](https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf) （OASIS。アサーションの要素）
- [SAML Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SAML_Security_Cheat_Sheet.html) （OWASP。SP の検証項目・XSW）

2026-11-20 時点の内容。
