<!-- scripts/memo.py build が自動生成。手で編集しない -->

# RSS と Atom

> RSS と Atom のフィードの仕組み、XML の書き方の違い、配信と取得の流れ、実装でつまずく点がわかる

- URL: https://memo.taka1156.site/rss-atom.html
- タグ: フロントエンド, バックエンド, ネットワーク
- 日付: 2026-11-23

---

サイトの更新を XML の一覧として配る「フィード」の 2 つの形式

**ざっくり言うと**

- RSS と Atom は、記事の一覧（タイトル・URL・日時・本文）を決まった形の XML で配るフィードの形式。
- 読む側（フィードリーダー）が定期的にフィードの URL を取りに行き、前回になかった項目を新着として扱う。
- 新しく作るなら仕様が厳密な Atom が扱いやすいが、Podcast など RSS 2.0 前提の世界では RSS を使う。

## 配信と取得の流れ

フィードは「サイトが置いておく XML ファイル」にすぎない。届け方の基本はプル型（読む側が取りに行く）で、それを補うプッシュ型の仕組みとして WebSub がある。

ポーリング

WebSub（プッシュ）

**サイト** 記事を公開すると

feed.xml を作り直す

置く

**feed.xml** 最新 N 件の

item / entry

条件付き

GET

**フィードリーダー** 数十分〜数時間おきに

取得して新着を判定

1. **前回の値を付けて取りに行く** リーダーは前回の応答の `ETag` と `Last-Modified` を覚えておき、 `If-None-Match` ・ `If-Modified-Since` を付けて GET する。
2. **変わっていなければ 304** サーバーは本文なしの `304 Not Modified` を返す。帯域とサーバーの負荷がほぼかからない。
3. **変わっていれば 200 と新しい XML** リーダーは各項目の ID（RSS の `guid` 、Atom の `id` ）を既読の一覧と比べ、知らない ID を新着として表示する。

**サイト** 記事を公開したら

ハブに知らせる

更新を

通知

**ハブ** フィードを取得して

購読者に配る

POST で

届ける

**購読者** あらかじめ

コールバック URL を登録

WebSub（旧称 PubSubHubbub）は W3C の勧告。フィードに `<link rel="hub">` と `<link rel="self">` を書いておくと、対応する購読者はハブに購読を申し込み、更新があるとハブから POST で受け取れる。ポーリングの間隔を待たずに届くのが利点。

プッシュに対応していないリーダーも多いので、WebSub を入れてもフィード自体は普通に GET できるようにしておく。

（元のページで操作できます → https://memo.taka1156.site/rss-atom.html#flow）

## 形式の系譜

「RSS」は 1 つの仕様ではなく、名前を共有する別々の系統がある。いま実際に出会うのはほぼ **RSS 2.0** と **Atom 1.0** の 2 つ。

| 形式 | 正式名・位置づけ | いまの扱い |
| --- | --- | --- |
| `RSS 0.9x` | Netscape が始めた初期の形式 | 過去のもの。読めるリーダーは多いが新しく出す理由はない |
| `RSS 1.0` | RDF Site Summary。RDF（意味づけの枠組み）に基づく別系統 | ほぼ使われない |
| `RSS 2.0` | Really Simple Syndication。0.9x の後継で、仕様は凍結されている | 最も広く使われる。Podcast の配信はこれが前提 |
| `Atom 1.0` | RSS のあいまいさをなくすため有志が設計し、IETF で RFC 4287 として標準化 | ブログ基盤・GitHub・YouTube などが配信。新規なら第一候補 |
| `JSON Feed` | 同じ考え方を JSON で書く形式（1.1 版） | 対応するリーダーは増えたが、XML の 2 つほど普及していない |

## XML の書き方を比べる

同じ記事 1 件を、それぞれの形式で書くとこうなる。外側の入れ物（チャンネル／フィード）と、記事 1 件（item／entry）の 2 段構えなのは同じ。

RSS 2.0

Atom 1.0

```
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Example Blog</title>
    <link>https://example.com/</link>
    <description>技術メモ</description>
    <atom:link rel="self" type="application/rss+xml"
               href="https://example.com/feed.xml"/>
    <item>
      <title>RSS を書いてみた</title>
      <link>https://example.com/posts/rss</link>
      <guid isPermaLink="true">https://example.com/posts/rss</guid>
      <pubDate>Mon, 23 Nov 2026 09:00:00 +0900</pubDate>
      <description><![CDATA[<p>本文の要約</p>]]></description>
    </item>
  </channel>
</rss>
```

- チャンネルの必須は `title` ・ `link` ・ `description` の 3 つ。item は `title` か `description` のどちらかがあればよい。
- 日付は RFC 822 形式（ `Mon, 23 Nov 2026 …` ）。
- 本文が HTML なのかプレーンテキストなのかを示す決まりがない。実際には HTML として扱われることが多い。
- フィード自身の URL を書く要素がないので、Atom の名前空間を借りて `atom:link rel="self"` を書くのが定番。

```
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Blog</title>
  <id>https://example.com/</id>
  <updated>2026-11-23T09:00:00+09:00</updated>
  <author><name>Taro</name></author>
  <link rel="self" href="https://example.com/atom.xml"/>
  <link rel="alternate" href="https://example.com/"/>
  <entry>
    <title>Atom を書いてみた</title>
    <id>tag:example.com,2026:posts/atom</id>
    <updated>2026-11-23T09:00:00+09:00</updated>
    <link rel="alternate" href="https://example.com/posts/atom"/>
    <summary type="text">本文の要約</summary>
    <content type="html">&lt;p&gt;本文&lt;/p&gt;</content>
  </entry>
</feed>
```

- フィードと entry の両方で `id` ・ `title` ・ `updated` が必須。著者（ `author` ）はフィードか、すべての entry のどちらかに要る。
- 日付は RFC 3339 形式（ `2026-11-23T09:00:00+09:00` ）。
- 本文の種類を `type` 属性（ `text` ・ `html` ・ `xhtml` ）で明示する。
- `link` は `rel` で役割を分ける（ `alternate` は記事の HTML、 `self` はフィード自身）。

（元のページで操作できます → https://memo.taka1156.site/rss-atom.html#xml）

### 要素の対応表

| 意味 | RSS 2.0 | Atom 1.0 |
| --- | --- | --- |
| 入れ物 / 1 件 | `channel` / `item` | `feed` / `entry` |
| 一意な ID | `guid` （任意） | `id` （必須・IRI） |
| 記事の URL | `link` | `link rel="alternate"` |
| 日時 | `pubDate` （公開日・任意） | `updated` （必須）・ `published` （任意） |
| 要約 / 本文 | `description` （本文は拡張の `content:encoded` ） | `summary` / `content` |
| 添付ファイル | `enclosure` （仕様に上限はないが、1 件に 1 つが推奨） | `link rel="enclosure"` （複数可） |
| MIME タイプ | `application/rss+xml` （慣習） | `application/atom+xml` （IANA 登録） |

## どちらを選ぶか

### Atom を選ぶ場面

- 新しくブログやサービスのフィードを作る
- 本文が HTML かテキストかを、読む側に誤解なく伝えたい
- 記事の更新日時を正しく伝えたい（ `updated` が必須）
- IETF の標準として仕様に従いたい

### RSS 2.0 を選ぶ場面

- Podcast を配信する（Apple Podcasts などは RSS 2.0 と `enclosure` が前提）
- 連携先のサービスが RSS しか受け付けない
- 既存の RSS フィードがあり、URL や形式を変えて購読者を失いたくない

主要なフィードリーダーは両方を読めるので、一般の読者向けならどちらでも届く。両方出すなら中身をそろえる。下の自動検出に載せるのは 1 形式だけにするのが望ましく、複数書くなら主に読んでほしいフィードを先に書く（RSS Advisory Board の自動検出仕様の推奨）。

## フィードの見つけ方（自動検出）

読む人がフィードの URL を知らなくても、サイトの URL をリーダーに入れれば見つかるように、HTML の `<head>` に案内を書く。

```
<link rel="alternate" type="application/atom+xml"
      title="Example Blog" href="/atom.xml">
```

リーダーは HTML を取得して `rel="alternate"` かつフィードの `type` を持つ `link` を探す。見つからなければ `/feed` ・ `/rss.xml` などのよくあるパスを試すリーダーもある。

## 静的サイトでの作り方

ブログやドキュメントサイトでは、フィードをサーバーで毎回組み立てるより、 **ビルドのときに XML ファイルとして書き出し、ほかのページと一緒に静的配信する** ことが多い。フィードは中身が記事の一覧だけなので、静的ファイルと相性がよい。

**記事の原稿** Markdown と

front matter（日付など）

ビルド

**dist/feed.xml** HTML と一緒に

書き出す

デプロイ

**CDN・静的ホスティング** リーダーの

条件付き GET に応える

1. **ビルドで生成する** 主な静的サイトジェネレーターには生成の仕組みがある（Hugo は標準で RSS を出力、Astro は `@astrojs/rss` 、Eleventy は `@11ty/eleventy-plugin-rss` ）。自前で書くなら、記事の一覧から XML を組み立てる小さなスクリプトで足りる。
2. **サイトの URL を設定から渡す** 静的ファイルには「いまのホスト名」がないので、記事の絶対 URL・フィードの `self` は、設定に書いたサイトの URL から組み立てる。プレビュー環境の URL がそのまま入らないよう注意する。
3. **日時は原稿から取る** `updated` ・ `pubDate` にビルドした時刻を入れると、ビルドのたびに全記事が「更新」に見える。front matter の日付（とタイムゾーン）を使う。
4. **キャッシュはホスティングに任せられる** 多くの CDN・静的ホスティングは、静的ファイルに `ETag` や `Last-Modified` を付け、条件付き GET に 304 を返す。自分で実装する前に、実際の応答ヘッダーを確かめる。
5. **WebSub の通知は CI から送る** サーバーがないので、記事を公開したことは、デプロイが終わったあとに CI からハブへ知らせる。通知の送り方はハブごとに決まっていて、多くの公開ハブは `hub.mode=publish` と `hub.url` （フィードの URL）を POST で受け取る。

## 実装でつまずく点

1. **ID を変えない** ID（ `guid` ・ `id` ）はその記事の名前。ドメイン移転や URL 設計の変更で ID が変わると、全記事が新着として出直す。URL とは別に、変えない ID を持たせると安全（Atom の `tag:` URI など）。
2. **相対 URL を使わない** フィードは元のページから切り離されて読まれる。本文中の `<img src="/a.png">` は壊れやすいので、絶対 URL にして出す。
3. **日付の形式とタイムゾーン** RSS は RFC 822、Atom は RFC 3339 と形式が違う。タイムゾーンを省くと 9 時間ずれた新着順になる。生成時に必ずオフセットを付ける。
4. **HTML のエスケープ** 本文の HTML は `&lt;` にエスケープするか CDATA で包む。 `&nbsp;` のような HTML 固有の実体参照は XML では未定義でエラーになる。
5. **件数を絞り、キャッシュを効かせる** 全記事を毎回出さず最新 10〜50 件にし、 `ETag` ・ `Last-Modified` を返す。多くのリーダーに頻繁に取られるので、304 で返せるかが負荷を大きく左右する（静的配信ならホスティングが返すことが多い。 静的サイトでの作り方 ）。
6. **読む側では無害化する** フィードの HTML は他人が書いたもの。リーダーやアグリゲーターを作るときは、表示前に `script` やイベント属性を除く（XSS 対策）。

出したフィードは W3C Feed Validation Service で検証でき、上の多くの誤りを指摘してくれる。

## よくある誤解

✗ 誤解: RSS は廃れた技術で、もう誰も使っていない

✓ 正しくは: 個人向けのリーダー市場は縮んだが、Podcast の配信、ニュースやブログの連携、GitHub のリリース通知、検索エンジンや自動化ツールへの更新の受け渡しなど、裏側では今も広く使われている。

✗ 誤解: Atom は RSS の新しいバージョンだ

✓ 正しくは: Atom は RSS とは別の仕様で、RSS 2.0 のあいまいさを避けるために 2003 年に有志のコミュニティが一から設計し、のちに IETF で RFC 4287（2005 年）として標準化された。要素名も日付の形式も違い、互換ではない。

✗ 誤解: フィードを置けば、更新は読者にすぐ届く

✓ 正しくは: 基本はリーダーが定期的に取りに来るポーリングなので、届くまでにリーダーの取得間隔ぶんの遅れがある。すぐ届けたいなら WebSub に対応する。

✗ 誤解: RSS の guid には記事の URL を入れなければならない

✓ 正しくは: `guid` は一意であればよい。URL でない値を入れるときは `isPermaLink="false"` を付ける（省略すると URL として扱われる）。

## 関連メモ

- [HTTP キャッシュ](https://memo.taka1156.site/md/http-cache.md) — フィードの条件付き GET（ETag・304）の仕組み
- [実装起因の脆弱性（入力の扱い）](https://memo.taka1156.site/md/web-vulnerabilities.md) — フィードの HTML を表示するときの XSS 対策
- [リアルタイム通信](https://memo.taka1156.site/md/realtime-comm.md) — ポーリングとプッシュの使い分け

## 参考

- [RSS 2.0 Specification](https://www.rssboard.org/rss-specification) （RSS Advisory Board）
- [RFC 4287: The Atom Syndication Format](https://www.rfc-editor.org/rfc/rfc4287)
- [WebSub](https://www.w3.org/TR/websub/) （W3C Recommendation）
- [JSON Feed Version 1.1](https://www.jsonfeed.org/version/1.1/)
- [W3C Feed Validation Service](https://validator.w3.org/feed/)
