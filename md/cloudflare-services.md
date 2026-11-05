<!-- scripts/memo.py build が自動生成。手で編集しない -->

# Cloudflare サービス

> Workers・Pages・R2・D1 など Cloudflare の 9 サービスを、リクエストの流れに沿った図と使い分けで整理。

- URL: https://memo.taka1156.site/cloudflare-services.html
- タグ: インフラ
- 日付: 2026-11-01

---

個人開発で使っている Cloudflare の 9 サービスを、リクエストが通る順に整理したリファレンス

**ざっくり言うと**

- DNS → 防御 → 実行・配信 → データ の 4 層で考えると、9 サービスの役割が整理しやすい
- 実行の中心は **Workers** 。API も静的サイトも動かせ、KV・R2・D1 と直接つながる（ **Pages** の機能は Workers 側に寄ってきている）
- データの置き場は中身で選ぶ: 読み中心の小さな値は KV、ファイルは R2、表形式のデータは D1

## リクエストの流れで見る

ユーザーのリクエストは左から右（スマホでは上から下）へ通る。サービスを押すと下に詳細が開く。

## サービス詳細

## 使い分け：データをどこに置くか

## ページ内のデータ（JavaScript で描画される部分）

```js
// ── データ ──────────────────────────────────────────
// サービスを追加するときは SERVICES に 1 件足し、STAGES のどこかに id を入れる。
const SERVICES = [
  {
    "id": "workers",
    "name": "Cloudflare Workers",
    "category": "Compute",
    "tagline": "サーバーレスコードをエッジで実行",
    "description": "Cloudflareのネットワーク（世界300都市以上）でJavaScript/TypeScript/WASMのコードを実行できるサーバーレスプラットフォーム。V8 isolateで動くためコールドスタートがほぼなく、負荷に応じて自動でスケールします。静的アセットの配信にも対応し、フロントエンドからAPIまで1つのWorkerで動かせます。",
    "features": [
      "V8 isolateで軽量に実行",
      "コールドスタートがほぼない",
      "静的アセット配信（Pagesの機能を統合）",
      "KV・R2・D1・Durable Objectsとのバインディング",
      "Cron Triggersによるスケジュール実行"
    ],
    "useCases": [
      "フルスタックWebアプリ",
      "API・プロキシ",
      "認証ミドルウェア",
      "エッジレンダリング",
      "定期バッチ処理"
    ],
    "docsUrl": "https://developers.cloudflare.com/workers/",
    "color": "#F6821F"
  },
  {
    "id": "pages",
    "name": "Cloudflare Pages",
    "category": "Hosting",
    "tagline": "Git連携でサイトを手軽にデプロイ",
    "description": "GitリポジトリからWebサイトを自動ビルド・デプロイ。静的サイトに加え、Pages Functionsでサーバー側の処理も書けます。現在はWorkers（静的アセット対応）のほうが使える機能が広く、Cloudflareは既存のPagesプロジェクト向けにWorkersへの移行ガイドを用意しています。",
    "features": [
      "Git連携で自動デプロイ",
      "プレビューデプロイ",
      "カスタムドメイン・SSL",
      "Pages Functions（Workersベース）",
      "静的アセットの帯域無制限"
    ],
    "useCases": [
      "静的サイト",
      "Next.js/Nuxt/Astroサイト",
      "ランディングページ",
      "ドキュメントサイト",
      "ポートフォリオ"
    ],
    "docsUrl": "https://developers.cloudflare.com/pages/",
    "color": "#FBAD41"
  },
  {
    "id": "r2",
    "name": "Cloudflare R2",
    "category": "Storage",
    "tagline": "エグレス無料のオブジェクトストレージ",
    "description": "S3互換のオブジェクトストレージ。Amazon S3と違ってエグレス（外への転送）料金が無料なので、画像や動画など配信量の多いファイルを置いてもコストが膨らみにくいのが特徴です。",
    "features": [
      "S3互換API",
      "エグレス料金ゼロ",
      "Workersからバインディングで直接アクセス",
      "公開バケット・カスタムドメイン",
      "ロケーションヒント・管轄区域の指定"
    ],
    "useCases": [
      "メディアファイル保存",
      "バックアップ",
      "静的アセット配信",
      "データレイク",
      "ログアーカイブ"
    ],
    "docsUrl": "https://developers.cloudflare.com/r2/",
    "color": "#F6821F"
  },
  {
    "id": "d1",
    "name": "Cloudflare D1",
    "category": "Database",
    "tagline": "エッジで動くサーバーレスSQLite",
    "description": "SQLiteベースのサーバーレスデータベース。Workersからバインディング経由でクエリを実行できます。読み取りレプリカ（ベータ）を有効にすると、Sessions APIを通じて世界各地のレプリカから読み取れます。",
    "features": [
      "SQLite互換",
      "Time Travel（過去の時点に復元）",
      "読み取りレプリカ（ベータ・Sessions API）",
      "Workersバインディング",
      "マイグレーション対応"
    ],
    "useCases": [
      "ユーザーデータ管理",
      "コンテンツDB",
      "セッションストア",
      "設定データ",
      "カタログデータ"
    ],
    "docsUrl": "https://developers.cloudflare.com/d1/",
    "color": "#FBAD41"
  },
  {
    "id": "kv",
    "name": "Workers KV",
    "category": "Storage",
    "tagline": "グローバル低レイテンシKVストア",
    "description": "世界中のエッジにレプリケートされるキー・バリューストア。読み取りが多いワークロードに向いています。書き込みが各地に反映されるまで最大60秒ほどかかる最終的一貫性なので、カウンターのように頻繁に書き換える値はDurable Objectsのほうが適しています。",
    "features": [
      "最終的一貫性",
      "グローバルレプリケーション",
      "TTL（有効期限）サポート",
      "大きな値も保存可能（最大25MiB）",
      "高速な読み取り"
    ],
    "useCases": [
      "設定値キャッシュ",
      "フィーチャーフラグ",
      "セッションデータ",
      "A/Bテスト設定",
      "リダイレクト・ルーティング表"
    ],
    "docsUrl": "https://developers.cloudflare.com/kv/",
    "color": "#F6821F"
  },
  {
    "id": "zero-trust",
    "name": "Cloudflare Zero Trust",
    "category": "Security",
    "tagline": "VPNなしの安全なアクセス制御",
    "description": "従来のVPNを置き換えるゼロトラストのアクセス制御。Cloudflare One（SASEプラットフォーム）の中核で、社内アプリや自宅サーバーへのアクセスをIDベースで管理します。50ユーザーまでは無料プランで使えます。",
    "features": [
      "Access（ZTNA）によるアプリ単位の認証",
      "Tunnel（cloudflared）で公開ポートなしに接続",
      "Gateway（SWG）によるWebフィルタリング",
      "SSO/IdP統合",
      "デバイス状態のチェック"
    ],
    "useCases": [
      "自宅サーバーの安全な公開",
      "社内ツールへのアクセス",
      "管理画面の保護",
      "SaaSアクセス制御",
      "リモートワーク環境"
    ],
    "docsUrl": "https://developers.cloudflare.com/cloudflare-one/",
    "color": "#FBAD41"
  },
  {
    "id": "waf",
    "name": "WAF / DDoS Protection",
    "category": "Security",
    "tagline": "L3〜L7の包括的攻撃防御",
    "description": "Webアプリケーションファイアウォールと自動DDoS緩和。OWASPルールセット、カスタムルール、ボット管理で多層防御を実現します。",
    "features": [
      "マネージドルール（OWASP含む）",
      "カスタムWAFルール",
      "L3/L4/L7 DDoS緩和（常時・無料）",
      "ボット対策（Bot Fight Mode／Bot Management）",
      "レート制限"
    ],
    "useCases": [
      "Webアプリ保護",
      "API保護",
      "大規模攻撃対策",
      "スクレイピング防止",
      "不正ログイン対策"
    ],
    "docsUrl": "https://developers.cloudflare.com/waf/",
    "color": "#F6821F"
  },
  {
    "id": "dns",
    "name": "Cloudflare DNS",
    "category": "Networking",
    "tagline": "Anycastで高速・高可用な権威DNS",
    "description": "Anycastネットワークを活用した権威DNSサービス。無料プランで使え、プロキシ（オレンジの雲）を有効にしたレコードはCloudflareのCDN・WAFを経由するようになります。DNSSECやAPIによる自動化にも対応します。",
    "features": [
      "Anycastによる高速応答",
      "DNSSEC対応",
      "ワイルドカードレコード",
      "ゾーンファイルの一括インポート",
      "API・Terraformで管理"
    ],
    "useCases": [
      "ドメイン管理",
      "プロキシ経由でCDN・WAFを有効化",
      "DNSSECによる改ざん対策",
      "IaCでのレコード管理",
      "負荷分散・フェイルオーバー（Load Balancing・有料）"
    ],
    "docsUrl": "https://developers.cloudflare.com/dns/",
    "color": "#FBAD41"
  },
  {
    "id": "stream",
    "name": "Cloudflare Stream",
    "category": "Media",
    "tagline": "動画配信インフラを丸ごと委託",
    "description": "動画のアップロード・エンコード・ストレージ・配信をワンストップで提供。HLSストリーミングとABRを自動で処理します。",
    "features": [
      "自動エンコード",
      "アダプティブビットレート",
      "HLS/MPEG-DASH配信",
      "サムネイル生成",
      "分析ダッシュボード"
    ],
    "useCases": [
      "教育プラットフォーム",
      "OTT/VODサービス",
      "企業内動画",
      "UGCプラットフォーム",
      "ライブ配信"
    ],
    "docsUrl": "https://developers.cloudflare.com/stream/",
    "color": "#F6821F"
  }
];

// 流れ図の段（左から順）。services は SERVICES の id。
const STAGES = [
  {
    "name": "名前解決",
    "role": "どこへ行くか決める",
    "services": [
      "dns"
    ]
  },
  {
    "name": "防御",
    "role": "通してよいか判断する",
    "services": [
      "waf",
      "zero-trust"
    ]
  },
  {
    "name": "実行・配信",
    "role": "処理して返す",
    "services": [
      "workers",
      "pages",
      "stream"
    ]
  },
  {
    "name": "データ",
    "role": "保存して読み出す",
    "services": [
      "kv",
      "r2",
      "d1"
    ]
  }
];

// 使い分けの比較（id, 置くもの/届けるもの, 向いている用途）
const COMPARE_HEAD = ["", "置くもの", "向いている用途"];
const COMPARE = [
  [
    "kv",
    "キーと値（設定・小さなデータ）",
    "読み込みが多く、更新が少ないもの。世界中で低レイテンシに読める"
  ],
  [
    "r2",
    "ファイル（画像・動画・バックアップ）",
    "大きなファイルの配信や保管。外への転送料（エグレス）が無料"
  ],
  [
    "d1",
    "表形式のデータ（SQLite）",
    "SQL で検索・結合したいアプリのデータ"
  ]
];

// ── 描画 ──────────────────────────────────────────
const byId = Object.fromEntries(SERVICES.map(s => [s.id, s]));
const order = STAGES.flatMap(st => st.services);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const shortName = s => s.name.replace(/^(Cloudflare|GitHub)\s+/, '');

function renderFlow() {
  document.getElementById('flow').innerHTML = STAGES.map((st, i) => `
    ${i ? '<div class="arrow" aria-hidden="true">→</div>' : ''}
    <div class="stage">
      <div class="stage-name">${esc(st.name)}</div>
      <div class="stage-role">${esc(st.role)}</div>
      ${st.services.map(id => `
        <button class="svc" type="button" data-id="${id}" aria-pressed="false">
          ${esc(shortName(byId[id]))}<small>${esc(byId[id].category)}</small>
        </button>`).join('')}
    </div>`).join('');
}

function renderDetail(id, scroll) {
  const s = byId[id];
  const i = order.indexOf(id);
  const prev = byId[order[(i - 1 + order.length) % order.length]];
  const next = byId[order[(i + 1) % order.length]];
  const el = document.getElementById('detail');
  el.style.setProperty('--svc', s.color);
  el.innerHTML = `
    <div class="detail-top"><span class="chip">${esc(s.category)}</span></div>
    <h3>${esc(s.name)}</h3>
    <p class="tagline">${esc(s.tagline)}</p>
    <p>${esc(s.description)}</p>
    <div class="cols">
      <div class="box"><h4>主な機能</h4><ul>${s.features.map(f => `<li>${esc(f)}</li>`).join('')}</ul></div>
      <div class="box"><h4>ユースケース</h4><ul>${s.useCases.map(u => `<li>${esc(u)}</li>`).join('')}</ul></div>
    </div>
    <div class="detail-foot">
      <a class="docs-link" href="${esc(s.docsUrl)}" target="_blank" rel="noopener noreferrer">公式ドキュメント →</a>
      <div class="pager">
        <button type="button" data-id="${prev.id}">← ${esc(shortName(prev))}</button>
        <button type="button" data-id="${next.id}">${esc(shortName(next))} →</button>
      </div>
    </div>`;
  document.querySelectorAll('.svc').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.id === id)));
  try { history.replaceState(null, '', '#' + id); } catch (e) {}
  if (scroll) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderCompare() {
  const head = `<div class="compare-row head">${COMPARE_HEAD.map(h => `<span>${esc(h)}</span>`).join('')}</div>`;
  document.getElementById('compare').innerHTML = head + COMPARE.map(([id, what, use]) => `
    <div class="card compare-row">
      <span class="name">${esc(shortName(byId[id]))}</span>
      <span class="what">${esc(what)}</span>
      <span class="use">${esc(use)}</span>
    </div>`).join('');
}

renderFlow();
renderCompare();
const initial = byId[location.hash.slice(1)] ? location.hash.slice(1) : order[0];
renderDetail(initial, false);

document.getElementById('flow').addEventListener('click', e => {
  const b = e.target.closest('.svc');
  if (b) renderDetail(b.dataset.id, true);
});
document.getElementById('detail').addEventListener('click', e => {
  const b = e.target.closest('.pager button');
  if (b) renderDetail(b.dataset.id, false);
});
```
