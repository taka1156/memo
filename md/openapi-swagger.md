<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Swagger と OpenAPI

> OpenAPI（旧 Swagger）の文書の構造と、そこから作れるドキュメント・型・モック・テスト、Swagger UI の動き方を図解。

- URL: https://memo.taka1156.site/openapi-swagger.html
- タグ: バックエンド, 設計, 開発ツール
- 日付: 2026-11-19

---

HTTP API の契約を 1 つの文書に書き、そこからドキュメント・型・モック・テストを作る

**ざっくり言うと**

- OpenAPI は HTTP API の入出力を YAML / JSON で書く仕様で、Swagger は元の名前であり、今は SmartBear 社の道具の名前。
- エンドポイント・引数・レスポンスの型を機械が読める形で 1 か所に書くので、そこから画面・型・モック・検証を作れる。
- 文書は書くだけでは実装を縛らない。CI で lint し、生成や検証に使って、実装とずれないようにする。

## 名前の整理：仕様と道具

「Swagger」は 2 つの意味で使われる。もとは仕様の名前だったが、2015 年に仕様が Linux Foundation 配下の OpenAPI Initiative に移り、2016 年に **OpenAPI Specification（OAS）** と改名された。今「Swagger」と言えば、多くは SmartBear 社の道具群（Swagger UI など）のこと。

SPEC ― 仕様

### OpenAPI Specification

API の契約の **書き方** の決まり。文書の先頭の `openapi: 3.1.0` で、どの版の書き方かを示す。2.0 の文書だけは `swagger: "2.0"` と書く（Swagger 2.0 = OpenAPI 2.0）。

TOOLS ― 道具

### Swagger UI / Editor / Codegen

OpenAPI の文書を **読んで使う** 道具。画面表示の Swagger UI、編集の Swagger Editor、コード生成の Swagger Codegen など。OpenAPI の文書を扱う道具は Swagger 以外にもたくさんある。

| 版 | 先頭の書き方 | 押さえておく違い |
| --- | --- | --- |
| 2.0 | `swagger: "2.0"` | 型は `definitions` 、URL は `host` ＋ `basePath` 、本文は `in: body` の引数 |
| 3.0 | `openapi: 3.0.x` | 再利用する部品を `components` にまとめ、 `servers` ・ `requestBody` ができた。null は `nullable: true` |
| 3.1 | `openapi: 3.1.x` | スキーマが JSON Schema（2020-12）とそろった。null は `type: [string, "null"]` 。 `webhooks` を書ける |
| 3.2 | `openapi: 3.2.0` | 3.1 の上に機能を足した版。タグの階層・ストリーミングの応答（1 件ずつの型）・ `QUERY` メソッドなど |

3.0 → 3.1 はマイナー版の番号でも、スキーマの書き方が変わったため、そのままでは通らない文書や道具がある。3.1 → 3.2 は書き換えなしで上がれる。

## 文書の構造

1 つのエンドポイント（ToDo を 1 件取る）を書いた例。トップの数個のキーで全体ができている。

```
openapi: 3.1.0            # 仕様の版
info:
  title: Todo API
  version: 1.2.0          # この API 自身の版（仕様の版ではない）
servers:
  - url: https://api.example.com/v1
paths:
  /todos/{id}:
    get:
      operationId: getTodo   # 生成されるクライアントの関数名になる
      tags: [todos]
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: string }
      responses:
        '200':
          description: 見つかった
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Todo' }
        '404':
          description: 無い
      security:
        - bearerAuth: []
components:
  schemas:
    Todo:
      type: object
      required: [id, title, done]
      properties:
        id:    { type: string }
        title: { type: string, maxLength: 100 }
        done:  { type: boolean }
        dueAt: { type: [string, "null"], format: date-time }
  securitySchemes:
    bearerAuth: { type: http, scheme: bearer }
```

info・servers

paths

components・$ref

security

`info` は API の名前と説明、 `info.version` は **この API の版** 。先頭の `openapi` （仕様の版）とは別物で、API を変えたらこちらを上げる。

`servers` は呼び出し先のベース URL。 `paths` のパスはここにつなげて解釈される（例: `https://api.example.com/v1/todos/42` ）。本番・ステージングなど複数並べてよい。

`paths` の下に「パス → HTTP メソッド → 操作（operation）」の順で書く。操作ごとに引数（ `parameters` の `in` は `path` ・ `query` ・ `header` ・ `cookie` 。3.2 ではクエリ文字列全体を 1 つとして扱う `querystring` も使える）、本文（ `requestBody` ）、ステータスコードごとのレスポンスを書く。

`operationId` は操作の一意な名前で、コード生成ではクライアントの関数名（ `getTodo()` ）になる。省くと道具がパスから名前を作り、読みにくい名前になりやすい。

`components` は再利用する部品の置き場。 `schemas` （データの型）のほか、 `parameters` ・ `responses` ・ `securitySchemes` などを置ける。

使う側は `$ref: '#/components/schemas/Todo'` のように参照する。同じ型を何か所にも書かないので、型を 1 か所直せば全部の操作に効き、生成される型も 1 つ（ `Todo` ）になる。 `$ref` は別ファイルも指せるので、大きな API はファイルを分けて書き、配るときに 1 枚にまとめる（bundle）。

`components.securitySchemes` で認証の方式（Bearer トークン・API キー・OAuth 2.0 など）を定義し、操作の `security` （または文書全体のトップの `security` ）でどれを要求するかを書く。

ここに書くのは「どの方式で送るか」だけで、トークンの検証はサーバーの実装がする。Swagger UI はこれを読んで「Authorize」ボタンを出す。

（元のページで操作できます → https://memo.taka1156.site/openapi-swagger.html#anatomy）

## 1 つの文書から作れるもの

OpenAPI の価値は「機械が読める契約」であること。文書を中心に、いろいろな道具が同じ情報を使う。

openapi.yaml API の契約（1 か所）

▼

### ドキュメント

エンドポイント一覧と型を画面にし、その場で試せる

Swagger UI・Redoc・Scalar

### クライアントの型・SDK

手書きの型やリクエスト関数がいらなくなる

OpenAPI Generator・openapi-typescript

### サーバーのひな形

ルーティングと型だけ作り、中身を実装する

OpenAPI Generator・oapi-codegen

### モックサーバー

実装の前に、例の値を返すサーバーで画面を作り始める

Prism

### lint

命名・説明漏れ・壊す変更を CI で止める

Spectral・Redocly CLI

### 検証・契約テスト

実際のリクエスト・レスポンスが文書どおりかを確かめる

検証ミドルウェア・Schemathesis

道具の名前は代表例。Swagger Codegen をフォークしたのが OpenAPI Generator で、今はこちらを使うことが多い。

## デザインファーストとコードファースト

文書と実装のどちらを「正」にするかで、進め方が 2 つに分かれる。どちらでも、文書と実装がずれない仕組み（生成か検証）を CI に入れるのが要点。

### デザインファースト（文書が先）

1. **文書を書いてレビュー** 実装の前に、使う側と契約を決める
2. **モックで並行開発** フロントはモック、バックは実装を同時に進める
3. **生成と検証** 型を生成し、実装が文書に合うかをテストで確かめる

### コードファースト（実装が先）

1. **実装に型と注釈を書く** ルート定義・型・デコレータなど
2. **文書を生成** FastAPI・NestJS・springdoc などが実装から出力する
3. **生成物を配る** 出力した文書から UI やクライアントを作る

|  | デザインファースト | コードファースト |
| --- | --- | --- |
| 向く場面 | 外部公開の API・複数チームで使う API・先に合意が要るとき | 社内向けで、1 チームが速く作って直すとき |
| ずれ方 | 実装が文書に追いつかない（検証で止める） | 注釈が足りず、文書が実際より粗くなる（エラー応答の書き漏れなど） |
| 手間 | YAML を書く手間・レビューの時間 | フレームワークの機能に縛られる。細かい表現は注釈を足す |

## Swagger UI の「Try it out」の流れ

Swagger UI はブラウザで動く静的なページで、文書を読んで画面を作る。試しに送るリクエストも、 **ブラウザから API へ直接** 出る。

1. **文書を取りに行く** Swagger UI のページが `openapi.yaml` （または JSON）を fetch して、操作の一覧と型を描く
2. **Authorize で認証情報を入れる** `securitySchemes` に合わせた入力欄が出る。入れたトークンはブラウザの中で保持され、以後のリクエストに付く
3. **Try it out で送信** `servers` の URL へブラウザが直接リクエストする。Swagger UI と API のオリジンが違えば、API 側の CORS 設定が要る
4. **結果を表示** ステータス・ヘッダー・本文と、同じリクエストを再現する `curl` コマンドが出る

3 番目だけ注意の色にしているのは、ここで「Swagger UI からは通らないのに curl では通る」という CORS の詰まりが起きやすいため。サーバー同士の通信ではないので、ブラウザの制約がそのまま効く。

## よくある誤解

✗ 誤解: Swagger と OpenAPI は別々の競合する仕様だ

✓ 正しくは: 同じ仕様の旧名と新名。Swagger 2.0 が OpenAPI 2.0 にあたり、3.0 以降は OpenAPI の名前だけで出ている。今の「Swagger」は主に道具（Swagger UI など）の名前。

✗ 誤解: OpenAPI に型を書けば、サーバーは文書と違うリクエストを自動で拒否する

✓ 正しくは: 文書はただのファイルで、置いただけでは実装に何も起きない。拒否させたいなら、文書を読んで検証するミドルウェアを入れるか、文書から生成した型・バリデーションを実装で使う。レスポンスが文書どおりかも、テストで別に確かめる。

✗ 誤解: 3.0 から 3.1 はマイナー版の更新なので、版の番号を書き換えるだけでよい

✓ 正しくは: 3.1 でスキーマが JSON Schema 2020-12 にそろい、 `nullable` がなくなる（ `type` に `"null"` を含める）など書き方が変わった。道具の対応状況も違うので、上げる前に使っている生成器・UI・lint が 3.1 を読めるか確かめる。

✗ 誤解: コードから生成した文書は、実装から作ったのだから常に正確だ

✓ 正しくは: フレームワークが読み取れるのは型と注釈まで。コードの中で例外として返す 404、ミドルウェアが返す 401、実際の文字数の制限などは、注釈を書かないと文書に出ない（入力検証の 422 のように自動で載るものもあるが、中身が実際の応答と同じとは限らない）。生成した文書でも、契約テストで実際の応答と突き合わせる。

✗ 誤解: Swagger UI は読むだけの画面なので、本番環境でそのまま公開しても害はない

✓ 正しくは: 社内向けや管理用のエンドポイントまで一覧になり、Try it out で本物のリクエストも送れる。公開 API のドキュメント以外は、認証の内側に置く・本番では出さない・公開用の文書から内部の操作を外す、のどれかにする。

## 関連メモ

- [REST・GraphQL・gRPC・tRPC](https://memo.taka1156.site/md/api-styles.md) — OpenAPI は REST の契約を書く手段。ほかの方式の契約（スキーマ・.proto・TS の型）との比較
- [API のバージョニングと後方互換](https://memo.taka1156.site/md/api-versioning.md) — 文書の差分で壊す変更を見つけ、 `info.version` とどう対応させるか
- [テスト戦略](https://memo.taka1156.site/md/testing-strategy.md) — 文書を使った契約テストの位置づけ
- [CORS と同一オリジンポリシー](https://memo.taka1156.site/md/cors-sop.md) — Swagger UI の Try it out が通らないときの原因
- [フォームとバリデーション](https://memo.taka1156.site/md/forms-validation.md) — スキーマの制約（ `maxLength` など）を画面とサーバーの検証にどう使うか

## 参考

- [OpenAPI Specification（最新版）](https://spec.openapis.org/oas/latest.html)
- [OpenAPI Documentation（OpenAPI Initiative の入門）](https://learn.openapis.org/)
- [Upgrading from OpenAPI 3.0 to 3.1](https://learn.openapis.org/upgrading/v3.0-to-v3.1.html)
- [Swagger UI のドキュメント](https://swagger.io/docs/open-source-tools/swagger-ui/usage/installation/)
- [OpenAPI Generator](https://openapi-generator.tech/)
