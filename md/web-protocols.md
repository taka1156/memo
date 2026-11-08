<!-- scripts/memo.py build が自動生成。手で編集しない -->

# HTTP/1.1・2・3 と TLS・DNS

> URL を入れてから最初のバイトが届くまでの DNS・TCP・TLS・HTTP の流れと、HTTP/1.1→2→3 で何が解決されたか（多重化・ヘッドオブライン・QUIC）を図解。

- URL: https://memo.taka1156.site/web-protocols.html
- タグ: ネットワーク, インフラ, フロントエンド
- 日付: 2026-11-03

---

「名前を引く → つなぐ → 暗号化 → 頼む」の 4 段と、その往復回数を減らしてきた歴史

**ざっくり言うと**

- ページを開くには **DNS で IP を引く → TCP でつなぐ → TLS で暗号化 → HTTP で頼む** 。遅さの多くは「データ量」ではなく **往復（RTT）の回数** で決まる。
- HTTP/2 は 1 本の接続に複数のリクエストを **多重化** した。ただし TCP の上なので、パケットが 1 つ落ちると全部が待たされる（ヘッドオブライン・ブロッキング）。
- HTTP/3 は UDP 上の **QUIC** に乗り換え、接続と暗号化を 1 往復にまとめ、落ちたパケットの影響をそのストリームだけに閉じ込めた。

## 最初のバイトが届くまで

サーバーまでの往復を 1 RTT とすると、初回アクセスでリクエストを送れるまでにかかる往復はこうなる（DNS はキャッシュがない場合）。

HTTP/1.1, 2

+ TLS 1.2

DNS TCP 1RTT TLS 2RTT リクエスト

HTTP/1.1, 2

+ TLS 1.3

DNS TCP 1RTT TLS 1RTT リクエスト

HTTP/3

DNS QUIC+TLS 1RTT リクエスト

HTTP/3

再接続 0-RTT

DNS 最初のパケットでリクエスト

名前解決 TCP ハンドシェイク TLS ハンドシェイク QUIC（接続と暗号化を同時に） HTTP

東京↔米国西海岸なら 1 RTT は 100ms 前後。往復が 1 回減るだけで、画像を数百 KB 削るより効くことがある。CDN でサーバーを近くに置くのも「RTT を短くする」対策。

## DNS：名前から IP を引く

（図: ブラウザ / OS / キャッシュを先に見る / フルリゾルバ / ISP・1.1.1.1・8.8.8.8 など / ルート (.) / 「.com は あっち」 / TLD (.com) / 「example.com は あっち」 / 権威サーバー / 「A = 203.0.113.5」 / 各段の答えは / TTL の間キャッシュ → https://memo.taka1156.site/web-protocols.html#dns）

実際はリゾルバがルートや TLD の答えをキャッシュしているので、毎回 3 段たどるわけではない。DNS を切り替えるときは **事前に TTL を短くしておく** と、古い IP を引かれ続ける時間を減らせる。

| レコード | 中身 | 使いどころ |
| --- | --- | --- |
| A / AAAA | IPv4 / IPv6 アドレス | 名前 → サーバーの住所 |
| CNAME | 別名（ほかの名前を指す） | `www` を CDN のホスト名に向ける。ゾーンの頂点（ `example.com` 自体）には置けない |
| HTTPS (SVCB) | 対応プロトコル（h3 など）・別ポート・ECH 設定 | 最初から HTTP/3 で接続してもらう。頂点でも別名を指せる |
| TXT | 任意の文字列 | ドメイン所有の確認、SPF などメールの認証 |
| MX | メールの受け取り先 | メールサーバー |
| CAA | 証明書を発行してよい CA | 関係ない CA による誤発行を防ぐ |

## HTTP/1.1 → 2 → 3

HTTP/1.1

HTTP/2

HTTP/3

テキストで 1 本ずつ

```
GET /app.js HTTP/1.1
Host: example.com
Accept-Encoding: gzip, br
```

1 本の接続では **レスポンスがリクエストの順番どおりにしか返らない** 。仕様上はレスポンスを待たずに続けて送れる（パイプライン）が、先頭が遅いと後ろも待たされるため主要ブラウザは使っておらず、実質 1 本につき 1 リクエストずつになる。そこでブラウザは同じオリジンに **最大 6 本程度** の接続を張って並列化する。画像をスプライトにまとめる、ドメインを分ける（シャーディング）、JS を 1 ファイルに結合する、といった昔の最適化はこの制限への対策。

1 本の TCP に多重化

メッセージを **バイナリのフレーム** に分け、ストリーム ID を付けて 1 本の接続に混ぜて流す。リクエストを好きなだけ並べられ、ヘッダーは HPACK で圧縮される。

弱点は下の TCP。TCP は「バイト列を順番どおりに渡す」約束なので、 **パケットが 1 つ欠けると、その後ろの全ストリームのデータが届いていても待たされる** （TCP レベルのヘッドオブライン・ブロッキング）。回線の悪いモバイルでは 1.1 の 6 本より遅くなることもある。

サーバープッシュは仕様にあったが、効果が出にくく主要ブラウザでは使われなくなった。代わりに `103 Early Hints` と `<link rel="preload">` を使う。

UDP の上の QUIC

QUIC はストリームの区別を **トランスポート層で** 持つので、欠けたパケットが待たせるのはそのストリームだけ。TLS 1.3 が組み込まれていて、接続と暗号化が 1 往復で済む。

接続を IP とポートではなく **コネクション ID** で識別するため、Wi-Fi からモバイル回線に切り替わっても張り直さずに続けられる（コネクション・マイグレーション）。

HTTP/3 が使えることをブラウザが知る方法は 2 つ。 `Alt-Svc` ヘッダーだけに頼る場合は、最初に HTTP/2 で接続し、そのレスポンスで「h3 も使える」と知ってから次の接続を HTTP/3 にする。DNS の HTTPS レコードに h3 があれば、 **初回から HTTP/3 を試せる** （対応はブラウザによって異なり、HTTP/2 と並行して試すなどの実装がある）。UDP が社内ネットワークなどで塞がれていれば HTTP/2 に戻る。

（元のページで操作できます → https://memo.taka1156.site/web-protocols.html#versions）

## ヘッドオブライン・ブロッキングの違い

（図: HTTP/2 (TCP) / 1 列に並んだバイト列 / A1 / B1 欠 / C1 / A2 / C2 / B1 の再送が届くまで / A も C も渡せない / HTTP/3 (QUIC) / ストリームごとに独立 / A / B / C / 待つのは B だけ。A と C は先にアプリへ渡る → https://memo.taka1156.site/web-protocols.html#hol）

## TLS 1.3：何を確かめ、何を守るか

1. **ClientHello** 使える暗号方式、鍵交換の材料（key share）、接続先の名前（SNI）、使いたいプロトコル（ALPN: h2 / http/1.1）を送る。
2. **ServerHello ＋ 証明書 ＋ Finished** サーバーも鍵交換の材料を返し、ここから先は暗号化される。証明書と、その秘密鍵を持っている証拠の署名もこの中で送る。
3. **クライアントが検証** 証明書が信頼できる CA までつながるか、 **名前がアクセス先と一致するか** 、期限内かを確認。OK なら Finished を返し、同時に HTTP リクエストを送れる。

守れるもの

盗聴（中身は見えない）、改ざん（途中で書き換えると検出される）、なりすまし（証明書の名前が一致しないと接続しない）。

守れないもの

接続先のドメイン名は SNI と DNS で見えうる（ECH・暗号化 DNS で隠す取り組みがある）。 **サーバー自体が悪意を持っている場合** は防げない。鍵マークは「正しい相手と暗号化できた」だけを意味する。

0-RTT（再接続時に最初のパケットでデータを送る）は速い代わりに、 **攻撃者が同じパケットを再送できる（リプレイ）** 。そのため GET など何度実行しても結果が同じリクエストだけに使うのが原則。

## 自分のサイトで確かめる

**DevTools → Network** の列ヘッダーを右クリックして「Protocol」を出すと `http/1.1` ・ `h2` ・ `h3` が見える。各リクエストの **Timing** タブには DNS Lookup・Initial connection・SSL の時間が並ぶ。

```
# 名前解決（どのレコードが、何秒の TTL で返るか）
dig example.com A +noall +answer
dig example.com HTTPS +short

# どのプロトコルで話しているか・TLS の情報
curl -sI --http2 https://example.com -o /dev/null -w '%{http_version}\n'
openssl s_client -connect example.com:443 -servername example.com </dev/null | head
```

## よくある誤解

HTTPS にすると遅くなる

TLS 1.3 なら追加は 1 往復だけで、再接続はさらに短い。しかも HTTP/2・3 はブラウザでは HTTPS でしか使えないので、多重化の恩恵まで考えるとむしろ速くなることが多い。

HTTP/2 なら JS を 1 ファイルに結合しなくていい

接続の制限はなくなったが、リクエストごとのオーバーヘッドや、import が深くつながると往復が重なる問題（ウォーターフォール）は残る。ほどよく分割してまとめる、が今のバンドラーの方針。

HTTP/3 は常に HTTP/2 より速い

効くのは主に RTT が長い・パケットロスが多い・回線が切り替わる環境。安定した有線では差が小さく、UDP の処理が重い環境では逆に遅いこともある。

## 関連メモ

[HTTP キャッシュ](https://memo.taka1156.site/md/http-cache.md) [セキュリティヘッダー](https://memo.taka1156.site/md/security-headers.md) [リアルタイム通信](https://memo.taka1156.site/md/realtime-comm.md) [Core Web Vitals](https://memo.taka1156.site/md/web-performance.md) [Cloudflare サービス](https://memo.taka1156.site/md/cloudflare-services.md)

## 参考

- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110)
- [RFC 9113: HTTP/2](https://www.rfc-editor.org/rfc/rfc9113)
- [RFC 9114: HTTP/3](https://www.rfc-editor.org/rfc/rfc9114)
- [RFC 9000: QUIC](https://www.rfc-editor.org/rfc/rfc9000)
- [RFC 8446: TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446)
- [RFC 9460: SVCB / HTTPS レコード](https://www.rfc-editor.org/rfc/rfc9460)
