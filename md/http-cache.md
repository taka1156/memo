<!-- scripts/memo.py build が自動生成。手で編集しない -->

# HTTP キャッシュ

> Cache-Control の読み方、鮮度と再検証（ETag・304）、ブラウザと CDN の二段構え、用途別のおすすめ設定までを図解。

- URL: https://memo.taka1156.site/http-cache.html
- タグ: インフラ, フロントエンド
- 日付: 2026-11-03

---

「いつまで聞かずに使うか」と「聞くときに何を送るか」の2段階

**ざっくり言うと**

- キャッシュは **新鮮（fresh）なうちは通信せずに使い** 、古く（stale）なったら **サーバーに「まだ同じ？」と確認（再検証）** する。
- 確認には ETag などの検証子を使う。変わっていなければ本文なしの `304 Not Modified` が返り、転送量がほぼゼロになる。
- 全部 `Cache-Control` ヘッダーで決まる。ブラウザ（自分専用）と CDN（みんなで共有）の2か所にキャッシュがあることを意識する。

## キャッシュは2か所にある

ブラウザ private cache：その人専用

→

CDN / プロキシ shared cache：全員で共有

→

オリジン アプリのサーバー

ログイン後の画面など **人によって中身が違うレスポンスを共有キャッシュに入れると、他人に見える** 。そういうレスポンスには `private` （ブラウザだけ可）か `no-store` を付ける。

## リクエストの流れ

新鮮なうち

ブラウザ：キャッシュを確認 max-age の範囲内

↓ 通信しない

そのまま表示 DevTools では「(disk cache)」「(memory cache)」

古くなったら（再検証）

If-None-Match: "v42" 手元の ETag を付けて問い合わせ

↓ サーバーが比較

304 同じ → 本文なし、手元を使う 鮮度もリセットされる

200 変わった → 新しい本文と ETag

検証子は2種類。 `ETag` （中身の識別子）→ 問い合わせは `If-None-Match` 。 `Last-Modified` （更新日時）→ `If-Modified-Since` 。両方あれば ETag が優先される。

## 鮮度のタイムライン

レスポンスを受け取ってからの経過時間を動かしてみる。

Cache-Control: max-age=60, stale-while-revalidate=120

fresh

SWR

stale

0s 60s 180s 300s

（元のページで操作できます → https://memo.taka1156.site/http-cache.html#sim）

## Cache-Control の主な指定

| 指定 | 意味 |
| --- | --- |
| `max-age=N` | N 秒間は新鮮。その間は確認なしで使ってよい。 |
| `s-maxage=N` | 共有キャッシュ（CDN）だけに効く max-age。ブラウザは短く、CDN は長く、ができる。 |
| `no-cache` | 保存はしてよいが、使う前に毎回再検証 。「キャッシュしない」ではない。 |
| `no-store` | どこにも保存しない。本当にキャッシュさせたくないのはこれ。 |
| `private` | ブラウザだけ保存可。CDN などの共有キャッシュは保存しない。 |
| `public` | 共有キャッシュも保存可（Authorization 付きリクエストの応答でも）。 |
| `must-revalidate` | 古くなったら必ず再検証。サーバーに繋がらなくても古いものを使わない（504 になる）。 |
| `immutable` | 新鮮な間は中身が絶対に変わらない。リロード時の再検証も省いてよい。 |
| `stale-while-revalidate=N` | 古くなってから N 秒間は、古いものを即返しつつ裏で更新する。 |
| `stale-if-error=N` | オリジンがエラーのとき、古くなってから N 秒間は古いものを返してよい。 |

古い `Expires` （日時指定）もあるが、 `Cache-Control: max-age` があればそちらが優先される。 `Pragma: no-cache` は HTTP/1.0 時代のリクエスト用ヘッダーで、レスポンスに付けたときの動作は決まっていない（非推奨）。新しく書くなら Cache-Control だけでよい。

## 用途別のおすすめ

ハッシュ付き JS/CSS

HTML

ログイン後の API

公開 API を CDN で

Cache-Control: public, max-age=31536000, immutable

`app.3f9a1c.js` のように **ファイル名に中身のハッシュが入っている** なら、中身が変われば URL も変わる。だから同じ URL は永遠に同じ中身＝1年キャッシュして問題ない。Vite などのビルドツールが自動でやってくれる。

Cache-Control: no-cache

ETag: "…"

HTML は URL が固定（ `/` など）なので長くキャッシュすると更新が届かない。 **毎回再検証** にしておけば、変わっていなければ 304 で軽く、デプロイ後はすぐ新しい HTML（＝新しいハッシュ付きアセットへの参照）が届く。

Cache-Control: private, no-cache

ユーザーごとに違う応答は `private` で CDN に乗せない。口座残高や個人情報など、端末に残ることすら避けたいものは `no-store` 。

Cache-Control: public, max-age=0, s-maxage=60, stale-while-revalidate=300

ブラウザは max-age=0 なのですぐ古くなり、CDN は 60 秒間オリジンに聞かない。 `stale-while-revalidate` はブラウザと CDN の両方に効くので、期限切れ後も5分間はどちらも古い値を即返しつつ裏で取り直す。 **オリジンの負荷と応答の速さを両立** できる（ブラウザには毎回確認を待たせたいなら、SWR を `CDN-Cache-Control` など CDN 専用のヘッダーに分ける）。

（元のページで操作できます → https://memo.taka1156.site/http-cache.html#recipes）

## Vary：同じ URL でも中身が変わるとき

同じ URL でも、リクエストヘッダーによって返す中身が違うことがある（圧縮形式、言語など）。 `Vary` に「どのヘッダーで中身が変わるか」を書くと、キャッシュはそのヘッダーの値ごとに別々に保存する。

```
Vary: Accept-Encoding        # gzip 版と br 版を別々に保存
Vary: Accept-Language        # 日本語版と英語版を別々に保存
```

`Vary: Cookie` や `Vary: User-Agent` は値の種類が多すぎて、共有キャッシュがほぼ効かなくなる。人によって変わるなら `private` にする方が素直。

## よくある誤解・ハマりどころ

`no-cache` を付ければキャッシュされない

no-cache は「使う前に毎回確認」。保存はされる。保存させたくないなら `no-store` 。

Cache-Control を付けなければキャッシュされない

指定が無くても、 `Last-Modified` があればブラウザや CDN が鮮度を推測して（ヒューリスティック）キャッシュすることがある。意図があるなら必ず明示する。

CDN をパージすれば全員に新しいものが届く

パージで消えるのは CDN の分だけ。ブラウザに長い max-age で残っている分は消せない。更新があり得るものは URL を変える（ファイル名ハッシュ）か、max-age を短くしておく。

Service Worker のキャッシュも Cache-Control で制御される

Service Worker の Cache API は別物で、コードで明示的に出し入れする。HTTP キャッシュとは二重に存在する（ [PWA](https://memo.taka1156.site/md/pwa.md) 参照）。

## 確認のしかた

```
curl -sI https://example.com/app.js     # Cache-Control / ETag / Age を見る
curl -sI https://example.com/ -H 'If-None-Match: "v42"'   # 304 が返るか
```

`Age` ヘッダーは「オリジンで生成（または最後に再検証）されてから何秒たったか」の見積もり。0 より大きければ、どこかのキャッシュから返ってきたとわかる。CDN の `X-Cache: HIT` や `CF-Cache-Status` などと合わせて見ると、どこで返ってきたかがわかる。DevTools の「Disable cache」はブラウザ側だけを無効にする。

## 関連

[Cloudflare サービス](https://memo.taka1156.site/md/cloudflare-services.md) [PWA の仕組み](https://memo.taka1156.site/md/pwa.md) [CORS と同一オリジンポリシー](https://memo.taka1156.site/md/cors-sop.md) [Vite ツールチェーン](https://memo.taka1156.site/md/vite-toolchain.md)

## 参考

- [RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111)
- [RFC 5861: stale-while-revalidate / stale-if-error](https://www.rfc-editor.org/rfc/rfc5861)
- [MDN: HTTP キャッシュ](https://developer.mozilla.org/ja/docs/Web/HTTP/Caching)
