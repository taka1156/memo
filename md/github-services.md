<!-- scripts/memo.py build が自動生成。手で編集しない -->

# GitHub サービス

> Actions・Pages・Codespaces など GitHub の 9 サービスを、開発の流れに沿った図と使い分けで整理。

- URL: https://memo.taka1156.site/github-services.html
- タグ: 開発ツール
- 日付: 2026-11-01

---

個人開発で使っている GitHub の 9 サービスを、開発の流れに沿って整理したリファレンス

**ざっくり言うと**

- 計画 → 開発 → 検査・自動化 → 配布・公開 の順に並べると、9 サービスの役割が整理しやすい
- 中心は **Actions** 。テスト・セキュリティ検査・デプロイ・リリースをつなぐ自動化の土台になる
- 配布先は中身で選ぶ: ライブラリやイメージは Packages、バイナリは Releases、Web サイトは Pages

## 開発の流れで見る

左から右（スマホでは上から下）へ進む開発の流れ。サービスを押すと下に詳細が開く。

## サービス詳細

## 使い分け：どこから配布するか

## ページ内のデータ（JavaScript で描画される部分）

```js
// ── データ ──────────────────────────────────────────
// サービスを追加するときは SERVICES に 1 件足し、STAGES のどこかに id を入れる。
const SERVICES = [
  {
    "id": "actions",
    "name": "GitHub Actions",
    "category": "CI/CD",
    "tagline": "コードに直結した自動化ワークフロー",
    "description": "GitHubリポジトリ内でCI/CDパイプラインを構築できる自動化プラットフォーム。YAMLで定義したワークフローがPush・PR・スケジュールで自動実行されます。",
    "features": [
      "YAML定義のワークフロー",
      "マトリクスビルド・並列ジョブ",
      "Marketplaceのアクション",
      "再利用可能なワークフロー",
      "セルフホストランナー・シークレット管理"
    ],
    "useCases": [
      "テスト自動化",
      "デプロイパイプライン",
      "PRのチェック・ラベル付け",
      "リリース自動化",
      "定期バッチ処理"
    ],
    "docsUrl": "https://docs.github.com/actions",
    "color": "#2088FF"
  },
  {
    "id": "pages",
    "name": "GitHub Pages",
    "category": "Hosting",
    "tagline": "リポジトリから静的サイトを即公開",
    "description": "GitHubリポジトリのコンテンツを静的Webサイトとして公開できるホスティングサービス。Jekyllのほか、Actionsのワークフローを使えばAstroやHugoなど任意のツールでビルドして公開できます。公開リポジトリなら無料です（プライベートリポジトリは有料プラン）。",
    "features": [
      "公開リポジトリは無料",
      "カスタムドメイン対応",
      "HTTPS自動設定",
      "Jekyll標準対応",
      "Actionsでのカスタムビルド・デプロイ"
    ],
    "useCases": [
      "プロジェクトドキュメント",
      "個人ブログ",
      "ポートフォリオ",
      "OSSプロジェクトサイト",
      "ランディングページ"
    ],
    "docsUrl": "https://docs.github.com/pages",
    "color": "#79B8FF"
  },
  {
    "id": "packages",
    "name": "GitHub Packages",
    "category": "Registry",
    "tagline": "コードとパッケージを同じ場所で管理",
    "description": "npm・コンテナ（ghcr.io）・Maven/Gradle・NuGet・RubyGemsに対応するパッケージレジストリ。Maven/Gradleはリポジトリの権限をそのまま使います。コンテナやnpmなどは公開範囲とアクセス権をリポジトリとは別に設定でき、リポジトリに紐付ければ権限を引き継ぐこともできます。",
    "features": [
      "Container registry（ghcr.io）",
      "npm/Maven/Gradle/NuGet/RubyGems対応",
      "GITHUB_TOKEN認証",
      "パブリック/プライベート公開",
      "Actionsとの統合"
    ],
    "useCases": [
      "社内npmパッケージ配布",
      "Dockerイメージ管理",
      "ライブラリ公開",
      "モノレポのパッケージ管理",
      "プライベートレジストリ"
    ],
    "docsUrl": "https://docs.github.com/packages",
    "color": "#2088FF"
  },
  {
    "id": "copilot",
    "name": "GitHub Copilot",
    "category": "AI",
    "tagline": "補完からエージェントまで、AIが開発に並走",
    "description": "IDEやGitHub上で使えるAIコーディングアシスタント。OpenAI・Anthropic・Googleなど複数のモデルから選べます。補完やチャットに加え、IDE内で編集・実行まで進めるエージェントモードや、Issueやタスクを任せるとクラウド上のブランチで作業し、必要に応じてPRまで作るクラウドエージェント（旧称：コーディングエージェント）も提供しています。無料プランもあります。",
    "features": [
      "コード補完",
      "チャット（複数モデルから選択）",
      "エージェントモード（IDE内）",
      "クラウドエージェント（旧コーディングエージェント、Issue→ブランチ/PR）",
      "PRのコードレビュー"
    ],
    "useCases": [
      "ボイラープレート生成",
      "リファクタリング",
      "バグ修正支援",
      "小さなIssueの委任",
      "新しい言語・ライブラリの学習"
    ],
    "docsUrl": "https://docs.github.com/copilot",
    "color": "#79B8FF"
  },
  {
    "id": "security",
    "name": "GitHub Advanced Security",
    "category": "Security",
    "tagline": "コードの脆弱性をシフトレフト検出",
    "description": "コードの脆弱性と秘密情報の漏洩を検出するセキュリティ機能群。2025年4月からSecret Protection（シークレットスキャン・プッシュ保護）とCode Security（CodeQLのコードスキャン・Copilot Autofix・依存関係レビュー）の2製品に分かれ、Teamプランでも個別に購入できます。公開リポジトリでは多くの機能が無料で、依存パッケージの更新PRを作るDependabotは全リポジトリで無料です。",
    "features": [
      "CodeQLによるコードスキャン",
      "Copilot Autofix（修正案の提案）",
      "シークレットスキャン・プッシュ保護",
      "依存関係レビュー",
      "SARIFでの外部ツール結果の取り込み"
    ],
    "useCases": [
      "セキュリティ脆弱性検出",
      "資格情報漏洩防止",
      "依存パッケージ更新",
      "コンプライアンス対応",
      "SAST統合"
    ],
    "docsUrl": "https://docs.github.com/code-security",
    "color": "#2088FF"
  },
  {
    "id": "projects",
    "name": "GitHub Projects",
    "category": "Planning",
    "tagline": "Issueとコードを繋ぐプロジェクト管理",
    "description": "カンバン・テーブル・ロードマップビューでプロジェクトを管理。IssueやPRと直接リンクし、開発の進捗をリアルタイムで追跡します。",
    "features": [
      "カンバン/テーブル/ロードマップ",
      "カスタムフィールド",
      "自動化ルール",
      "フィルター・グループ",
      "複数リポジトリ横断"
    ],
    "useCases": [
      "スプリント計画",
      "バックログ管理",
      "リリース追跡",
      "チーム進捗管理",
      "OKR管理"
    ],
    "docsUrl": "https://docs.github.com/issues/planning-and-tracking-with-projects",
    "color": "#79B8FF"
  },
  {
    "id": "releases",
    "name": "GitHub Releases",
    "category": "Distribution",
    "tagline": "バイナリとリリースノートを一元配布",
    "description": "タグと紐付いたリリースページでバイナリ・ソースコード・リリースノートを配布。Actionsと連携した自動リリースフローを構築できます。",
    "features": [
      "タグベースリリース",
      "バイナリアップロード",
      "自動生成リリースノート",
      "プレリリース対応",
      "API経由の作成"
    ],
    "useCases": [
      "アプリ配布",
      "CLIツール配布",
      "変更履歴公開",
      "バージョン管理",
      "自動リリースパイプライン"
    ],
    "docsUrl": "https://docs.github.com/repositories/releasing-projects-on-github",
    "color": "#2088FF"
  },
  {
    "id": "codespaces",
    "name": "GitHub Codespaces",
    "category": "Development",
    "tagline": "ブラウザですぐ使えるクラウドIDE",
    "description": "クラウド上に開発環境を即座に立ち上げ、ブラウザやVS Code・JetBrainsから接続できます。devcontainerで環境定義を共有するので、誰でも同じ環境で開発できます。個人アカウントには毎月の無料枠があります。",
    "features": [
      "ブラウザ/VS Code/JetBrainsから接続",
      "devcontainer対応",
      "マシンスペックの選択",
      "ポートフォワーディング",
      "Prebuilds"
    ],
    "useCases": [
      "オンボーディング高速化",
      "コントリビューター環境",
      "一時的なデバッグ",
      "デモ環境",
      "ローカル環境依存解消"
    ],
    "docsUrl": "https://docs.github.com/codespaces",
    "color": "#79B8FF"
  },
  {
    "id": "discussions",
    "name": "GitHub Discussions",
    "category": "Community",
    "tagline": "コミュニティの対話をリポジトリに集約",
    "description": "Q&A・アイデア・アナウンスメントをリポジトリ内で管理できるフォーラム機能。Issueと分離することでコミュニティ運営がしやすくなります。",
    "features": [
      "Q&A/アイデア/お知らせなどのカテゴリ",
      "ベストアンサー選択",
      "投票（Polls）・賛成票",
      "Issueとの相互変換",
      "通知管理"
    ],
    "useCases": [
      "OSSコミュニティ運営",
      "ユーザーサポート",
      "フィードバック収集",
      "ロードマップ議論",
      "ナレッジベース構築"
    ],
    "docsUrl": "https://docs.github.com/discussions",
    "color": "#2088FF"
  }
];

// 流れ図の段（左から順）。services は SERVICES の id。
const STAGES = [
  {
    "name": "計画",
    "role": "何を作るか決める",
    "services": [
      "projects",
      "discussions"
    ]
  },
  {
    "name": "開発",
    "role": "コードを書く",
    "services": [
      "codespaces",
      "copilot"
    ]
  },
  {
    "name": "検査・自動化",
    "role": "確かめて流す",
    "services": [
      "security",
      "actions"
    ]
  },
  {
    "name": "配布・公開",
    "role": "使える形で届ける",
    "services": [
      "packages",
      "releases",
      "pages"
    ]
  }
];

// 使い分けの比較（id, 置くもの/届けるもの, 向いている用途）
const COMPARE_HEAD = ["", "届けるもの", "向いている用途"];
const COMPARE = [
  [
    "packages",
    "パッケージ（npm・Docker イメージなど）",
    "ほかのプロジェクトから依存として取り込んでもらうもの"
  ],
  [
    "releases",
    "バイナリ・アーカイブ＋リリースノート",
    "バージョンごとに配布物と変更点をまとめて出すもの"
  ],
  [
    "pages",
    "静的 Web サイト",
    "ドキュメントやポートフォリオなど、ブラウザで見てもらうもの"
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
