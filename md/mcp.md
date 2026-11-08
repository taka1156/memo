<!-- scripts/memo.py build が自動生成。手で編集しない -->

# MCP の仕組み

> AI アプリと外部ツールをつなぐ Model Context Protocol の構成、3つのプリミティブ、通信方式、2026-07-28 版の変更点を図解。

- URL: https://memo.taka1156.site/mcp.html
- タグ: AI
- 日付: 2026-11-02

---

Model Context Protocol — AI アプリと外部ツールをつなぐ共通の差し込み口

**ざっくり言うと**

- AI アプリ（ホスト）が、ファイル・DB・SaaS などの外部機能を **同じ作法で呼び出す** ためのプロトコル。「AI 用の USB-C」と例えられる
- MCP サーバーは **Tools・Resources・Prompts** の3種類を提供し、通信は JSON-RPC で、ローカルなら **stdio** 、リモートなら **Streamable HTTP** を使う
- LLM がサーバーと直接話すのではない。ホストが道具の一覧を LLM に見せ、LLM が選んだ呼び出しをホストが代わりに実行する

## なぜ共通規格が要るのか

MCP 以前：N × M

（図: アプリA / アプリB / アプリC / GitHub / Slack / DB / Drive → https://memo.taka1156.site/mcp.html#why）

3 × 4 = 12 通りの専用連携を、各社がばらばらに作る。

MCP 以後：N ＋ M

（図: アプリA / アプリB / アプリC / MCP / GitHub / Slack / DB / Drive → https://memo.taka1156.site/mcp.html#why）

3 ＋ 4 = 7 。アプリはクライアントを1回、サービスはサーバーを1回作れば、どの組み合わせでも動く。

## 登場人物と構成

（図: ホスト（AI アプリ） / Claude、Claude Code、IDE など / LLM / クライアント 1 / クライアント 2 / クライアント 3 / stdio / HTTP / ファイル系 / DB 系 / SaaS 系 / MCP サーバー / ローカルの FS / PostgreSQL / 外部の API → https://memo.taka1156.site/mcp.html#actors）

stdio（同じマシンの子プロセス） Streamable HTTP（ネットワーク越し）

**ホスト**

ユーザーが触る AI アプリ。どのサーバーに繋ぐか、どの呼び出しを許可するかを決める。

**クライアント**

ホストの中の接続部品。 **サーバー1つにつき1つ** 作られる。

**サーバー**

機能を提供するプログラム。中身は既存 API の薄いラッパーであることが多い。

**LLM**

サーバーとは直接話さない。ホストが見せた道具の説明を読んで、使うかどうかを決めるだけ。

## サーバーが提供する3つのもの

違いは「 **誰が使うと決めるか** 」にある。

### Tools モデルが決める

実行できる関数。「Issue を作る」「SQL を実行する」など。LLM が会話の流れから自分で選んで呼ぶ。副作用があるものは、ホストがユーザーに確認を求めるのが一般的。

### Resources アプリが決める

読み取り用のデータ。URI で指す（ `file:///…` 、 `postgres://…/schema` など）。ホストが「添付」のような形でコンテキストに入れる。

### Prompts ユーザーが決める

定型の指示テンプレート。ホストの UI でスラッシュコマンドなどとして見え、ユーザーが選んで使う。

### 拡張 任意

本体とは別に、任意で使える「拡張」の枠組みがある。ツールから UI を返す **MCP Apps** （2026 年 1 月に最初の公式拡張になった）や企業向け認可がこれにあたる。2026-07-28 版では長時間処理の **Tasks** も本体から拡張に移った。

## 通信方式（トランスポート）

| 方式 | stdio | Streamable HTTP |
| --- | --- | --- |
| どこで動く | 同じマシン。ホストがサーバーを子プロセスとして起動する | ネットワーク越し（社内・クラウド） |
| やり取り | 標準入出力に JSON-RPC のメッセージを1行ずつ流す | HTTP POST。応答は単発の JSON か、SSE のストリーム |
| 認証 | MCP の認可は不要（OS のユーザー権限で動く。API キーなどは環境変数で渡す） | OAuth 2.1 ベース。MCP サーバーは「リソースサーバー」になる |
| 向いているもの | ローカルファイル、Git、開発ツール | SaaS 連携、複数人で共有するサーバー |
| 設定例 | `"command": "npx", "args": ["-y", "some-mcp"]` | `"url": "https://mcp.example.com/mcp"` |

古い「HTTP+SSE」方式（GET で SSE、POST で送信の2本立て）は非推奨で、Streamable HTTP への移行期間中。

## ツールが呼ばれるまで

1. ホスト → サーバー
   **一覧を取得する** 。サーバーは名前・説明・入力の JSON Schema を返す。この説明文が LLM への「取扱説明書」になる。

```
// tools/list の結果（抜粋）
{
  "tools": [{
    "name": "create_issue",
    "description": "GitHub リポジトリに Issue を作成する",
    "inputSchema": {
      "type": "object",
      "properties": {
        "repo":  { "type": "string" },
        "title": { "type": "string" }
      },
      "required": ["repo", "title"]
    }
  }],
  "resultType": "complete",
  "ttlMs": 300000,
  "cacheScope": "private"
}
```

2. ホスト → LLM
   **道具の説明をプロンプトに載せる** 。LLM API の「ツール使用（function calling）」の形式に変換して渡す。
3. LLM → ホスト
   **LLM が「このツールをこの引数で使いたい」と返す** 。ホストは必要ならユーザーに許可を求める。
4. ホスト → サーバー
   **ツールを実行する** 。

```
{ "jsonrpc": "2.0", "id": 7, "method": "tools/call",
  "params": {
    "name": "create_issue",
    "arguments": { "repo": "taka1156/memo", "title": "MCP のメモを追加" },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  } }
```

5. サーバー → ホスト → LLM
   **結果を LLM に返す** 。LLM はそれを読んで、次のツールを呼ぶか、ユーザーに答える。

## 2026-07-28 版で変わったこと

2025 年までの解説記事とは前提が大きく違うので注意。

- **セッションの廃止** ：接続直後の initialize ハンドシェイクと Mcp-Session-Id ヘッダーがなくなり、各リクエストがプロトコルバージョンや機能を `_meta` に持つ **ステートレス** な形になった。状態が要るサーバーは、ツールが「ハンドル」を発行し、モデルがそれを次の引数で渡し返す
- ** `server/discover` ** ：サーバーの対応バージョンや機能を事前に問い合わせる仕組み（呼ぶかどうかはクライアント次第）
- **MRTR（Multi Round-Trip Requests）** ：サーバーがユーザーに質問したいときは、結果として「入力が必要」を返し、クライアントが答えを付けて同じリクエストをやり直す。サーバー側から呼びかける elicitation/create などはこれに置き換え
- **非推奨** ：Sampling（サーバーがホストの LLM を借りる）、Roots、Logging、HTTP+SSE。最低12か月は動き続ける
- **ルーティング用ヘッダー** ：HTTP では `Mcp-Method` と `Mcp-Name` が必須になり、ゲートウェイが本文を読まずに振り分け・認可できる
- **認可** ：クライアントの登録方式が、動的登録 (DCR) から Client ID Metadata Documents (CIMD) に移行中

## 似ているものとの違い

function calling

普通の API

Skills

**function calling（ツール使用）** は LLM API の機能で、「モデルが関数を呼びたいと言える」仕組み。関数の実体はアプリごとに自前で書く。

MCP はその **関数の提供側** を標準化したもの。MCP のツールは、最終的に function calling の形に変換されて LLM に渡される。対立ではなく、上下の関係。

REST などの API は人間の開発者向けで、呼び方はサービスごとにばらばら。MCP サーバーは多くの場合 **既存 API を包んで、LLM が使いやすい粒度と説明に整えたもの** 。API を置き換えるわけではない。

**Skills** は「手順書とスクリプトの束」で、必要なときに読み込まれる **知識** 。MCP は外部システムへの **接続** 。「Slack に繋ぐ」のが MCP、「うちのチームの週報の書き方」が Skill。

[CLAUDE.md / AGENTS.md / Skills のメモ →](https://memo.taka1156.site/md/agent-instructions.md)

（元のページで操作できます → https://memo.taka1156.site/mcp.html#compare）

## セキュリティの注意点

**ローカルサーバーはあなたの権限で動く**

stdio のサーバーは任意のコードを実行できる。 `npx` 1行で入るものほど、出どころを確認する。

**ツールの結果もプロンプトになる**

取得した Web ページや Issue 本文に「〇〇を実行せよ」と書かれていると、LLM が従ってしまう（プロンプトインジェクション）。書き込み系ツールは確認を挟む。

**ツールの説明文を悪用される**

悪意あるサーバーが説明文に隠し指示を仕込む「ツールポイズニング」がある。

**トークンの使い回し禁止**

リモートサーバーは、自分宛てに発行されたトークンだけを受け付ける。受け取ったトークンをそのまま上流 API に流すのは仕様で禁止されている。

## よくある誤解

✕ 「MCP サーバーの中で AI が動いている」

○ サーバーは普通のプログラムで、LLM は入っていない。考えるのはホスト側の LLM。

✕ 「ツールは多いほど賢くなる」

○ ツールの説明はすべてコンテキストを消費し、選択肢が増えるほど誤選択も増える。必要なサーバーだけ有効にする。

✕ 「MCP は Anthropic 専用」

○ Anthropic が 2024 年に公開したオープンな仕様で、2025 年 12 月からは Linux Foundation 傘下の Agentic AI Foundation が管理している。他社の AI アプリや IDE も対応している。SDK も TypeScript、Python、Go、C# などがある。

## 関連メモ

[CLAUDE.md / AGENTS.md / Skills →](https://memo.taka1156.site/md/agent-instructions.md) [OAuth 2.0 / OIDC（リモート MCP の認可）→](https://memo.taka1156.site/md/oauth-oidc.md)
