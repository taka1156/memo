<!-- scripts/memo.py build が自動生成。手で編集しない -->

# 認可モデル（RBAC・ABAC・ReBAC）

> 「この人はこれをしてよいか」を決める ACL・RBAC・ABAC・ReBAC の違いと、Zanzibar 型の関係タプル、どこでチェックするか（IDOR 対策・RLS）を図とシミュレーターで整理する

- URL: https://memo.taka1156.site/authorization-models.html
- タグ: セキュリティ, 設計, バックエンド
- 日付: 2026-11-06

---

認証が「あなたは誰？」なら、認可は「あなたはこれをしてよい？」—— 権限の決め方 4 種と、どこで確かめるか

**ざっくり言うと**

- **RBAC** （役割で決める）が基本。「編集者は記事を編集できる」。シンプルだが、「自分の部署の記事だけ」のような条件が増えると役割が爆発する。
- 条件で決めるのが **ABAC** （属性：部署・時刻・状態）、つながりで決めるのが **ReBAC** （関係：「このフォルダの共有相手は中のファイルも見られる」）。Google ドライブ型の共有は ReBAC が得意。
- どのモデルでも、チェックは **サーバー側で、リソースごとに毎回** 行う。画面でボタンを隠すだけ、ログイン済みかを見るだけ、は認可ではない。

## 認証と認可

**認証 (authentication)**

相手が誰かを確かめる。パスワード・ [パスキー](https://memo.taka1156.site/md/passkeys.md) ・ [OIDC](https://memo.taka1156.site/md/oauth-oidc.md) 。結果は「ユーザー ID」。

**認可 (authorization)**

その ID に、その操作を許すかを決める。このページの話。結果は「許可 / 拒否」。

OAuth 2.0 のスコープ（ `read:repo` など）は「アプリにどこまで代理を任せるか」で、アプリ内の細かな権限（どのリポジトリを読めるか）は別に判定する必要がある。

## 4 つのモデル

ACL

RBAC

ABAC

ReBAC

**リソースごとに「誰が何をできるか」の一覧を持つ。** アクセス制御リスト (Access Control List)。Linux の POSIX ACL（ `setfacl` ）、S3 のバケット ACL（新しいバケットでは既定で無効。今はバケットポリシーが推奨）など。

report.pdf: alice=読み書き, bob=読み

得意 1 つ 1 つ確実に指定できる。 苦手 ユーザーやリソースが増えると管理しきれない。「営業部全員に」と言いたくなる。

**ユーザーに役割（ロール）を付け、役割に権限を付ける。** Role-Based Access Control。

ユーザー bob → ロール editor → 権限 article:edit

得意 入退社・異動は「ロールを付け替える」だけ。監査で「誰が何をできるか」を説明しやすい。

苦手 「自分の部署の記事だけ編集」「下書きの間だけ」のような条件。 `editor_sales` ・ `editor_sales_draft` …とロールが増え続ける（ロール爆発）。

**ユーザー・リソース・環境の属性を条件式で評価する。** Attribute-Based Access Control。

```
許可 if  user.department == resource.department
     and resource.status == "draft"
     and env.time in 09:00–18:00
```

得意 細かい条件をロールを増やさず書ける。 苦手 「結局この人は何ができるのか」を一覧しにくい。条件が複雑になるとテストが必須。

**ユーザーとリソースの「関係」をたどって決める。** Relationship-Based Access Control。Google が Drive・YouTube など多くのサービスで共通に使う認可基盤として作った Zanzibar（論文で公開）が代表例。

bob member of 営業チーム editor of フォルダ Q4 parent of 見積.pdf

「見積.pdf を bob は見られる？」→ 関係をたどって **つながれば許可** 。

得意 共有・階層・チーム・組織の入れ子。 苦手 関係データを専用のストアに持ち、アプリの DB と同期させる手間がかかる。

（元のページで操作できます → https://memo.taka1156.site/authorization-models.html#models）

## 同じ質問を各モデルで判定する

ドキュメント「見積.pdf」（営業部・下書き・フォルダ Q4 の中。フォルダ Q4 は営業チームに編集者として共有）に対する操作を、各モデルがどう判定するかを見てください。

ユーザー alice（admin・情シス） bob（editor・営業部・営業チーム） carol（editor・開発部） dave（viewer・社外・個別に共有） 操作 閲覧編集

同じ「carol は編集者」でも、RBAC だけなら他部署の下書きを編集できてしまう。条件や関係を足すと絞り込める。実際のシステムでは RBAC を土台に ABAC や ReBAC の条件を足す組み合わせが多い。

（元のページで操作できます → https://memo.taka1156.site/authorization-models.html#sim）

## Zanzibar 型：関係をタプルで持つ

ReBAC の実装では、関係を **「オブジェクト#関係@主体」** というタプルで保存し、権限の定義（スキーマ）で「viewer には editor も含む」「親フォルダの viewer は子も見られる」と書きます。

folder:q4 # editor @ team:sales#member

doc:estimate # parent @ folder:q4

team:sales # member @ user:bob

```
# OpenFGA 風のスキーマ
type doc
  relations
    define parent: [folder]
    define editor: [user, team#member] or editor from parent
    define viewer: [user] or editor or viewer from parent
```

アプリは「 `check(user:bob, viewer, doc:estimate)` 」と聞くだけ。OpenFGA・SpiceDB などがこの形のオープンソース実装です。

### ポリシーエンジン

| 種類 | 例 | 中身 |
| --- | --- | --- |
| 関係ベース | OpenFGA・SpiceDB | タプルを保存し、関係をたどって判定 |
| ポリシー言語 | OPA（Rego）・Cedar | 属性を入力に、条件式で判定（ABAC 寄り）。データは主に呼び出し側が渡す（OPA はバンドルなどでデータを持たせることもできる） |
| ライブラリ | Casbin など | アプリに組み込み、RBAC / ABAC のモデルを設定ファイルで書く |

判定ロジックをアプリのあちこちの if 文に散らさず 1 か所（ポリシー）にまとめると、テスト・監査・変更がしやすくなる。

## どこでチェックするか

**足りない**

- 画面で編集ボタンを隠す
- 「ログインしているか」だけ確認
- 一覧画面ではチェック、詳細 API ではしない

**必要**

- サーバーの API ごとに、 **そのリソースに対して** 判定
- 何も当てはまらなければ拒否（デフォルト拒否）
- 一覧・検索の SQL にも権限条件を入れる

```
// NG：ログイン済みなら ID さえ変えれば他人の請求書が見える（IDOR）
app.get('/invoices/:id', requireLogin, (req) => db.invoice.find(req.params.id));

// OK：リソースを取ってから、この人に許されているかを判定
app.get('/invoices/:id', requireLogin, async (req) => {
  const inv = await db.invoice.find(req.params.id);
  if (!inv || !(await can(req.user, 'view', inv))) return notFound();
  return inv;
});
```

URL の ID を書き換えるだけで他人のデータが見える脆弱性は IDOR（API では BOLA）と呼ばれ、API の脆弱性で最も多いものの 1 つです（ [実装起因の脆弱性](https://memo.taka1156.site/md/web-vulnerabilities.md) ）。存在を知られたくないリソースは 403 ではなく 404 を返すこともあります。

### マルチテナント：行レベルセキュリティ

SaaS では「他社のデータが見えない」が最重要の認可です。全クエリに `WHERE tenant_id = ?` を書き忘れないよう、PostgreSQL の行レベルセキュリティ (RLS) で DB 側に強制する方法があります。ただしスーパーユーザーとテーブル所有者には通常ポリシーが効かないので、アプリは所有者でないロールで接続するか、 `FORCE ROW LEVEL SECURITY` も設定します。

```
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON invoices
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

### トークンに権限を入れるときの注意

JWT にロールを入れると DB を引かずに判定できて速い反面、 **トークンの有効期限が切れるまで古い権限が残ります** 。権限を剥奪したら即座に効かせたい操作（管理者権限・支払い）はサーバー側で都度確認します（ [JWT とセッション](https://memo.taka1156.site/md/jwt-vs-session.md) ）。

## よくある誤解

管理画面の URL を知られなければ安全

URL は推測・漏洩する。権限のない人が叩いても拒否されるように、サーバーで判定する。

RBAC と ABAC はどちらか一方を選ぶもの

多くの実装はロールを土台に、「自分の部署だけ」のような属性条件を足す。ReBAC も「owner」「editor」のような関係名でロールを表せる。

OAuth のスコープがあれば認可は済んでいる

スコープはアプリに任せた範囲。「このユーザーがこのリソースに触れてよいか」はアプリ側で別に判定する。
