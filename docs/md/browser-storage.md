<!-- scripts/memo.py build が自動生成。手で編集しない -->

# ブラウザのストレージ

> Cookie・localStorage・sessionStorage・IndexedDB・Cache API・OPFS を、容量・同期か非同期か・サーバーに送られるか・いつ消えるかで比べ、用途別の選び方と、実際に書き込んで確かめられるデモで図解。

- URL: https://memo.taka1156.site/browser-storage.html
- タグ: フロントエンド, セキュリティ, JavaScript
- 日付: 2026-11-03

---

「どこに置くか」は、量・形・誰が読むか・どれだけ残したいかで決まる

**ざっくり言うと**

- **Cookie はサーバーに毎回送られる** 小さなデータ（ログイン状態など）。ブラウザの中だけで使うデータを Cookie に入れると、全リクエストが重くなる。
- 小さな設定は **localStorage** （同期・文字列のみ）、大きなデータやオブジェクトは **IndexedDB** （非同期）、オフライン用のレスポンスは **Cache API** 、大きなファイルは **OPFS** 。
- どれも **オリジンごと** に分かれていて、 **ブラウザの判断で消されうる** 。消えて困るものはサーバーにも持つか、 `navigator.storage.persist()` で保護を頼む。

## 一覧で比べる

|  | 容量の目安 | API | 形 | サーバーに送る | Worker から |
| --- | --- | --- | --- | --- | --- |
| Cookie | 1 個 約 4KB | 同期（ `document.cookie` ） | 文字列 | 毎リクエスト自動 | ×（Service Worker からは Cookie Store API で可） |
| localStorage | オリジンごとに約 5MB | 同期 | 文字列 | × | × |
| sessionStorage | 約 5MB | 同期 | 文字列 | × | × |
| IndexedDB | ディスクの空きに応じて大きい | 非同期 | オブジェクト・Blob（構造化複製） | × | ○ |
| Cache API | 同上（共有の枠） | 非同期 | Request → Response | × | ○（Service Worker の主役） |
| OPFS | 同上（共有の枠） | 非同期（Worker 内は同期ハンドルも） | ファイル | × | ○ |

IndexedDB・Cache API・OPFS は同じ「オリジンの枠」を分け合う。上限はブラウザとディスクの空きで変わるので、数字を決め打ちせず `navigator.storage.estimate()` で確かめる（下のデモ参照）。localStorage の値は UTF-16 で数えられるので、日本語は 1 文字 2 バイト程度になる。

## 実際に書いて確かめる

localStorage に書く

sessionStorage に書く

IndexedDB にオブジェクトを書く

全部読む

消す

ボタンを押すと、ここに結果が出る。

このオリジンの使用量（navigator.storage.estimate）

—

書いたあとにページを再読み込みすると、localStorage と IndexedDB は残り、sessionStorage は同じタブなら残る（タブを閉じると消える）。プレビュー環境やプライベートウィンドウでは、保存が拒否されたり閉じると消えたりする。

（元のページで操作できます → https://memo.taka1156.site/browser-storage.html#lab）

## Cookie：サーバーと共有する小さな札

```
Set-Cookie: session=abc123; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=604800
```

| 属性 | 意味 |
| --- | --- |
| `HttpOnly` | JS（ `document.cookie` ）から読めない。XSS でセッションを盗まれにくくする。ログイン用は必ず付ける |
| `Secure` | HTTPS のときだけ送る |
| `SameSite=Lax` | 他サイトから来たリクエストでは、トップレベルの遷移（リンクで来た GET）以外は送らない。CSRF 対策の土台 |
| `Max-Age` / `Expires` | 付けないと セッション Cookie （ブラウザを閉じると消える、はずだが「前回のタブを復元」で残ることがある） |
| `Partitioned` | 埋め込み先のサイトごとに別の Cookie にする（CHIPS）。サードパーティとして埋め込まれるチャットや地図向け |

サードパーティ Cookie（埋め込み先から見た別サイトの Cookie）は、Safari が既定でブロックしている。Firefox は既定で埋め込み先のサイトごとに Cookie を分ける（Total Cookie Protection）ので、サイトをまたいだ共有はできない。Chrome は既定では許可したままにする方針に変わったが、ユーザーが制限できる。どのブラウザでも動かしたいなら、サードパーティ Cookie に頼らない設計にする。

## localStorage と sessionStorage

向いている

テーマ（ライト／ダーク）、閉じたパネル、未送信の下書きなど、 **小さくて、消えても困らない** 設定。読み書きが簡単で、別タブの変更は `storage` イベントで受け取れる。

向いていない

**同期 API** なのでメインスレッドを止める（大きな JSON の読み書きは INP を悪化させる）。 **XSS があれば全部読まれる** ので、トークンなど秘密の置き場には向かない。数値やオブジェクトは文字列化が必要。

```
// 失敗する前提で書く（容量超過・プライベートモード・保存禁止の設定）
function save(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); return true; }
  catch { return false; }   // QuotaExceededError や SecurityError
}
```

**sessionStorage はタブごと** 。同じサイトを 2 つのタブで開くと別々の中身になる。タブを複製すると中身もコピーされる。

## IndexedDB：ブラウザの中のデータベース

キーと値（オブジェクト・配列・Date・Blob・ArrayBuffer など、構造化複製できるもの）を保存し、 **インデックスで検索** でき、 **トランザクション** がある。オフラインで動くアプリのデータ、大きな一覧のキャッシュ、メール本文や画像の保存に使う。

```
// 素の API はイベント方式で冗長なので、薄いラッパー（idb など）を使うことが多い
import { openDB } from 'idb';
const db = await openDB('notes', 1, {
  upgrade(db) {                                  // 版を上げたときだけ呼ばれる（スキーマ変更）
    const s = db.createObjectStore('notes', { keyPath: 'id' });
    s.createIndex('byUpdated', 'updatedAt');
  },
});
await db.put('notes', { id: 'n1', body: 'メモ', updatedAt: Date.now() });
const recent = await db.getAllFromIndex('notes', 'byUpdated');
```

スキーマを変えるときは版番号を上げ、 `upgrade` で移行する。古い版を開いたままの別タブがあると `blocked` になるので、 `versionchange` で古い接続を閉じる処理も書く。

## Cache API と OPFS

Cache API

`Request` をキーに `Response` を丸ごと保存する。Service Worker でオフライン時に返すのが主な用途。HTTP キャッシュとは別物で、 **自分で入れて自分で消す** （期限は自動で切れない）。

OPFS（Origin Private File System）

オリジン専用のファイルシステム。ユーザーには見えない。Worker 内の同期アクセスハンドルで高速に読み書きでき、 **ブラウザで SQLite を動かすときの保存先** などに使われる。

## いつ消えるか

**容量が足りない** ディスクが逼迫すると、ブラウザが「しばらく使っていないオリジン」から丸ごと消す（best-effort）。

**ユーザーが消す** 「サイトデータを削除」「閲覧履歴を消去」。プライベートウィンドウは閉じると全部消える。

**Safari の 7 日ルール** Safari（トラッキング防止が有効なとき）は、Safari を使った日で数えて 7 日間そのサイトをクリックやタップで操作しないと、JS で書いたストレージを消す。サーバーが送った Cookie は対象外。ホーム画面に追加した Web アプリは使用日数を別に数えるので、使っていれば消されない。

**サーバーから消す** ログアウト時などに `Clear-Site-Data: "cache", "cookies", "storage"` ヘッダーで一括削除できる。

```
// 消されにくくしてほしいと頼む（認められるかはブラウザが決める）
if (navigator.storage?.persist) {
  const granted = await navigator.storage.persist();
  console.log(granted ? '永続化された' : 'best-effort のまま');
}
```

## 用途別の置き場所

| 置きたいもの | 置き場所 | 理由 |
| --- | --- | --- |
| ログインセッション | Cookie（HttpOnly・Secure・SameSite） | JS から読めない場所に置き、サーバーが自動で受け取れる |
| テーマ・表示設定 | localStorage | 小さく、消えても困らない。サーバー描画にも反映したいなら Cookie |
| フォームの下書き（このタブだけ） | sessionStorage | タブを閉じたら要らない |
| オフラインで見るデータ・大きな一覧 | IndexedDB | 非同期で大容量、検索できる |
| オフライン用の HTML・JS・画像 | Cache API（Service Worker） | レスポンスをそのまま返せる |
| ブラウザ内 DB の実体・大きなファイル | OPFS | ファイルとして高速に読み書き |
| アクセストークン（SPA） | メモリ（変数）が基本 | 永続化するなら XSS で読まれる前提で、寿命を短くする |

## 関連メモ

[JWT とセッション](https://memo.taka1156.site/md/jwt-vs-session.md) [PWA](https://memo.taka1156.site/md/pwa.md) [セキュリティヘッダー](https://memo.taka1156.site/md/security-headers.md) [実装起因の脆弱性](https://memo.taka1156.site/md/web-vulnerabilities.md) [HTTP キャッシュ](https://memo.taka1156.site/md/http-cache.md) [Core Web Vitals](https://memo.taka1156.site/md/web-performance.md)

## 参考

- [MDN: ストレージの割り当てと削除基準](https://developer.mozilla.org/ja/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria)
- [web.dev: Storage for the web](https://web.dev/articles/storage-for-the-web)
- [MDN: HTTP Cookie](https://developer.mozilla.org/ja/docs/Web/HTTP/Cookies)
- [MDN: IndexedDB API](https://developer.mozilla.org/ja/docs/Web/API/IndexedDB_API)
- [MDN: Origin private file system](https://developer.mozilla.org/en-US/docs/Web/API/File_System_API/Origin_private_file_system)
- [WebKit: Tracking Prevention](https://webkit.org/tracking-prevention/)
