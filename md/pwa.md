<!-- scripts/memo.py build が自動生成。手で編集しない -->

# PWA の仕組みとチェックリスト

> HTTPS・Manifest・Service Worker の役割、キャッシュ戦略、インストール条件と実装項目を図解。

- URL: https://memo.taka1156.site/pwa.html
- タグ: フロントエンド
- 日付: 2026-11-03

---

# PWA の仕組み

Web アプリを「インストールできて、オフラインでも動く」アプリにするための構成と実装チェックリスト

**ざっくり言うと**

- PWA (Progressive Web App) は **HTTPS・Manifest・Service Worker** の 3 つでできている
- Manifest が「アプリとしての見た目」、Service Worker が「通信の間に入る代理人」を担う
- オフラインで動くのは、Service Worker が **キャッシュしたものだけ**

## 必須の 3 要素

01 / HTTPS **安全な配信**

Service Worker は通信を書き換えられるため、HTTPS でしか動かない。開発中の `localhost` は例外。

02 / MANIFEST **アプリの名刺**

`manifest.webmanifest` に名前・アイコン・起動 URL・表示モードを書く。インストール可否の判定材料になる。

03 / SERVICE WORKER **通信の代理人**

ページとネットワークの間に立つ JS。リクエストを横取りしてキャッシュから返したり、プッシュ通知を受け取ったりする。

## 全体の構成図

（図: HTTPS / キャッシュ / Cache Storage / ページ / main.js / Service Worker / sw.js / ネットワーク / サーバー / Manifest / .webmanifest / ホーム画面 / install / fetch / ① 確認 / ② なければ / link で読込 → https://memo.taka1156.site/pwa.html#overview）

ページの通信はすべて Service Worker を通る。SW はキャッシュにあればそれを返し、なければネットワークに取りに行く（どちらを先にするかは「キャッシュ戦略」で決める）。

## Service Worker のライフサイクル

**1. register**

ページが `sw.js` を登録する

**2. install**

必要なファイルを先にキャッシュしておく

**3. waiting**

旧 SW が動いている間は待機する

**4. activate**

古いキャッシュを掃除して有効になる

**5. fetch**

以降の通信を横取りして応答する

更新時に 3 で止まるのがつまずきやすい点。タブをすべて閉じるか、 `skipWaiting()` を呼ぶまで新しい SW は有効にならない。

## キャッシュ戦略

Cache First

Network First

Stale-While-Revalidate

リクエスト → キャッシュ → なければ ネットワーク

**向いているもの：** CSS・JS・画像・フォントなど、ファイル名にバージョンが付いて中身が変わらない静的ファイル。

速くてオフラインに強い。そのかわり、更新はキャッシュ名やファイル名を変えないと反映されない。

リクエスト → ネットワーク → 失敗したら キャッシュ

**向いているもの：** API のレスポンスや HTML など、常に最新を見せたいもの。

オンライン時は常に最新。そのかわり、回線が遅いとタイムアウトまで待たされる。

リクエスト → キャッシュを即返す ＋ 裏で ネットワークで更新

**向いているもの：** アバター画像やニュース一覧など、多少古くてもすぐ表示したいもの。

表示は速く、次回には新しくなる。そのかわり、今回表示する内容は 1 つ前の版になる。

（元のページで操作できます → https://memo.taka1156.site/pwa.html#cache）

## 最小構成のコード

manifest

HTML

sw.js

```
{
  "name": "My App",
  "short_name": "MyApp",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#1a73e8",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/maskable-512.png", "sizes": "512x512",
      "type": "image/png", "purpose": "maskable" }
  ]
}
```

```
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#1a73e8">
<link rel="apple-touch-icon" href="/icons/icon-180.png">

<script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js');
  }
</script>
```

```
const CACHE = 'v1';
const ASSETS = ['/', '/index.html', '/style.css', '/main.js', '/offline.html'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
});

self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request)
      .then(r => r || fetch(e.request))
      .catch(() => caches.match('/offline.html'))
  );
});
```

手書きが大変なら Workbox、Vite なら `vite-plugin-pwa` 、Next.js なら `@serwist/next` で生成できる。

（元のページで操作できます → https://memo.taka1156.site/pwa.html#code）

## プラットフォームごとの違い

| 項目 | Chrome / Edge（Android・PC） | iOS / iPadOS Safari |
| --- | --- | --- |
| インストール導線 | 条件を満たすとインストールの案内が出る（ページを 1 回以上クリックし、30 秒以上閲覧していることも条件）。 `beforeinstallprompt` で独自ボタンも作れる | 自動のプロンプトも `beforeinstallprompt` もなし（macOS の Safari も同様）。「共有 → ホーム画面に追加」を案内する |
| アイコン | manifest の `icons` | manifest の `icons` も使える（iOS 15.4 以降）。 `apple-touch-icon` があればそちらが優先される |
| Web Push | ブラウザ上でも使える | ホーム画面に追加した PWA のみ（iOS 16.4 以降）。通知の許可はボタンのタップなどユーザー操作から求める必要がある |

## 実装チェックリスト

0 / 0

### 必須

- 必須 HTTPS で配信している 開発時は localhost で可
- 必須 manifest を `<link rel="manifest">` で読み込んでいる
- 必須 `name` または `short_name` がある
- 必須 192px と 512px のアイコンがある
- 必須 `start_url` を指定している
- 必須 `display` が `standalone` / `fullscreen` / `minimal-ui` / `window-controls-overlay` のいずれか
- 必須 `prefer_related_applications` が未指定か `false` true だとネイティブアプリへの誘導が優先され、インストール対象にならない
- 必須 Service Worker を登録している 現在の Chrome のインストール判定には含まれないが、オフライン対応に必要
- 必須 `sw.js` をサイトのルートに置いている 置いた場所以下しか制御できない（スコープ）。広げるにはサーバーが `Service-Worker-Allowed` ヘッダーを返す必要がある

（元のページで操作できます → https://memo.taka1156.site/pwa.html#checklist）

### オフラインとキャッシュ

- 推奨 install で主要ファイルを事前キャッシュしている
- 推奨 オフライン用のフォールバックページを返せる
- 推奨 静的ファイルと API でキャッシュ戦略を分けている
- 推奨 activate で古いキャッシュを削除している

（元のページで操作できます → https://memo.taka1156.site/pwa.html#checklist）

### 更新

- 推奨 `sw.js` と `importScripts` で読むファイルに `Cache-Control: no-cache` （または `max-age=0` ）を付けている 今のブラウザは既定で sw.js 本体の更新確認に HTTP キャッシュを使わないが、importScripts で読むファイルには HTTP キャッシュが効く。古いブラウザ向けにも sw.js に付けておく
- 推奨 新しい版を検知したら「更新があります」と知らせ、 `skipWaiting()` で切り替えられる

（元のページで操作できます → https://memo.taka1156.site/pwa.html#checklist）

### 見た目と端末対応

- 推奨 viewport の meta タグがある
- 推奨 `theme-color` を指定している
- 推奨 maskable アイコンを用意している Android で丸や角丸に切り抜かれても欠けない
- 推奨 `apple-touch-icon` を指定している
- 推奨 iOS 向けに「ホーム画面に追加」の案内がある

（元のページで操作できます → https://memo.taka1156.site/pwa.html#checklist）

### 確認

- 推奨 DevTools の Application タブで Manifest・SW・Cache を確認した
- 推奨 Network タブを Offline にして動作を確認した
- 推奨 DevTools の Application タブ → Manifest で、インストールできない理由（エラー・警告）がないか確認した Lighthouse の PWA 監査は v12 で廃止

（元のページで操作できます → https://memo.taka1156.site/pwa.html#checklist）

## よくある誤解

✗ 誤解: Service Worker を入れれば、アプリ全体がオフラインで動く

✓ 正しくは: 動くのはキャッシュしてあるものだけ。API の結果や未訪問のページは、自分でキャッシュしない限りオフラインでは表示できない。

✗ 誤解: `sw.js` を書き換えればすぐ反映される

✓ 正しくは: 新しい SW は waiting 状態で止まる。すべてのタブを閉じるか、 `skipWaiting()` を呼ぶまで古い SW が動き続ける。

✗ 誤解: `sw.js` は `/js/` などに置いてもよい

✓ 正しくは: SW が制御できるのは置いた場所以下だけ。 `/js/sw.js` だと `/js/` 配下しか制御できない。サーバーが `Service-Worker-Allowed` ヘッダーを返せば広げられるが、通常はルートに置くのが簡単。

✗ 誤解: fetch ハンドラがないとインストールできない

✓ 正しくは: 以前の Chrome では必須だった。Chrome 108（モバイル）／112（デスクトップ）でメニューからのインストールには不要になり、現在の Chrome のインストール基準にも Service Worker の条件は載っていない。ただし他のブラウザでは基準が異なることがあり、オフライン対応のためにも実装するのが普通。

✗ 誤解: iPhone でもインストールボタンが自動で出る

✓ 正しくは: iOS の Safari には自動のプロンプトも `beforeinstallprompt` もない（Firefox も非対応）。ユーザーに共有メニューから追加してもらう必要がある。

## 参考

- [What does it take to be installable?（web.dev）](https://web.dev/install-criteria/)
- [Revisiting Chrome's installability criteria（Chrome for Developers）](https://developer.chrome.com/blog/update-install-criteria)
- [Web Push for Web Apps on iOS and iPadOS（WebKit）](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)
- [ServiceWorkerContainer: register()（MDN）](https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerContainer/register)
- [beforeinstallprompt（Can I use）](https://caniuse.com/wf-beforeinstallprompt)

2026-11-03 時点で確認。
