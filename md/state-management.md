<!-- scripts/memo.py build が自動生成。手で編集しない -->

# 状態管理の比較

> フロントエンドの状態を、サーバー状態・URL・フォーム・ローカル・グローバルに分けて置き場所を決める考え方と、TanStack Query のキャッシュと無効化、Context・Zustand・Jotai・Redux Toolkit・Signals の違い、派生状態を持たない書き方を図解する

- URL: https://memo.taka1156.site/state-management.html
- タグ: フロントエンド, JavaScript, 設計
- 日付: 2026-11-14

---

データをどこに置くか ── サーバー状態とクライアント状態、TanStack Query・Zustand・Signals

**ざっくり言うと**

- 状態は「サーバーにある元データの写し」「URL」「フォームの入力中の値」「画面の中だけの値」「アプリ全体で共有する値」に分けると置き場所が決まる。
- サーバーの写しはデータ取得ライブラリのキャッシュに任せ、古くなったら取り直す・更新したら無効化する、を宣言するだけにする。
- アプリ全体で共有するクライアントの値は意外と少なく、そこだけを Zustand・Jotai・Signals などで持ち、計算で出せる値は持たない。

「値が変わったら画面をどう描き直すか」（仮想 DOM・シグナル・コンパイラ）は [UI 更新の3つの方式](https://memo.taka1156.site/md/reactivity-models.md) にあります。このメモはその手前の、 **どのデータをどこに置き、誰が持ち主になるか** の話です。

## 状態の 5 つの種類

**サーバー状態** 商品一覧、ログイン中のユーザー情報

本当の持ち主はサーバー。手元にあるのは写しで、ほかの人の操作でいつの間にか古くなる。

→ データ取得ライブラリのキャッシュ

**URL の状態** 検索語、絞り込み、ページ番号、開いているタブ

リンクで共有したい、再読み込みや「戻る」で元に戻したい値。

→ パス・クエリ文字列

**フォームの状態** 入力中の値、エラー、送信中かどうか

送信するまでの一時的な下書き。確定したらサーバー状態になる。

→ フォームの仕組み・ライブラリ

**ローカルの UI 状態** 開いているメニュー、ホバー中の行

1 つの部品とその子だけが使う。ほかから知る必要がない。

→ 部品の中（useState・ref など）

**グローバルなクライアント状態** テーマ、未保存の下書き、カートの中身（未ログイン時）

サーバーにはなく、離れた複数の部品が読み書きする。

→ ストア（Zustand・Jotai・Signals など）

かつては「とりあえず全部グローバルストアへ」という設計がよくありました。サーバーの写しやフォームの値まで 1 か所に集めると、取り直しのタイミングやローディング表示を全部手で書くことになり、ストアが肥大化します。種類ごとに専用の置き場所を使うと、 **本当にストアに置くべき値はかなり少なく** なります。

### 置き場所を決める

その値の本当の持ち主はサーバー？（DB にある、API から取ってくる）

はい

いいえ

リンクで共有したり、「戻る」で元に戻したりしたい？

はい

いいえ

送信前の入力中の値？

はい

いいえ

ほかの値から計算で出せる？（合計、絞り込んだ一覧など）

はい

いいえ

使うのは 1 つの部品とその子だけ？

はい

いいえ

**サーバー状態**

TanStack Query・SWR などのキャッシュに任せる。ストアにコピーしない。

**URL の状態**

クエリ文字列に置き、ルーターから読む。再読み込みしても残り、リンクで共有できる。

**フォームの状態**

フォームの仕組み（React の form action、React Hook Form など）に持たせる。

**状態にしない**

元の値から描画のたびに計算する（重ければメモ化）。持つと元の値とずれる。

**ローカルの UI 状態**

その部品の中に持つ。必要になったら、そのとき親へ持ち上げる。

**グローバルなクライアント状態**

ストアに置く。ここに来る値が少ないほど、設計がうまくいっている。

最初から

（元のページで操作できます → https://memo.taka1156.site/state-management.html#decide）

## サーバー状態：キャッシュに任せる

サーバーの写しを手で管理すると、「いつ取り直すか」「ローディング中・エラーの表示」「同じデータを 2 つの部品が同時に頼んだら」「更新したらどこを取り直すか」を全部自分で書くことになります。TanStack Query（旧 React Query）や SWR は、これを **キー付きのキャッシュ** として引き受けます。

```
// 読む: キーが同じなら、どの部品から呼んでも 1 回の通信とキャッシュを共有する
const { data, isPending, error } = useQuery({
  queryKey: ['todos', { done: false }],
  queryFn: () => fetchTodos({ done: false }),
  staleTime: 30_000,          // 30 秒は新しいとみなして取り直さない（既定は 0）
});

// 書く: 成功したら関係するキーを無効化 → 表示中なら裏で取り直す
const qc = useQueryClient();
const add = useMutation({
  mutationFn: createTodo,
  onSuccess: () => qc.invalidateQueries({ queryKey: ['todos'] }),
});
```

1. **キャッシュにあればすぐ表示** 古いかもしれないが、まず手元の写しを見せる。
2. **古ければ裏で取り直す** TanStack Query v5 の既定では取得した直後から「古い」扱いで、部品が表示されたとき・タブに戻ったとき・ネットにつながり直したときに取り直す。 `staleTime` を延ばすと、その間は取り直さない。
3. **使われなくなったら捨てる** どの部品も使わなくなったキャッシュは、既定で 5 分後（ `gcTime` ）に消える。
4. **更新したら無効化する** どのデータが変わったかをキーで宣言するだけで、表示中のものは自動で取り直される。

この「古い写しを見せつつ裏で取り直す」は、HTTP の `stale-while-revalidate` と同じ考え方です（ [HTTP キャッシュ](https://memo.taka1156.site/md/http-cache.md) ）。押した瞬間に画面へ反映したいときは、成功を待たずにキャッシュを書き換え、失敗したら戻す **楽観的更新** （optimistic update）も使えます。

Next.js などのサーバーコンポーネントで描く画面では、データの取得をサーバー側で済ませるので、クライアントにキャッシュを持たない構成も増えている。どちらでも「サーバーの写しをクライアントのストアにコピーしない」点は同じ（ [レンダリング戦略](https://memo.taka1156.site/md/rendering-strategies.md) ）。

## グローバルなクライアント状態：道具の違い

| 道具 | 形 | 描き直される範囲 | 向いている場面 |
| --- | --- | --- | --- |
| React Context | 値を木の下へ配る仕組み（状態管理ではなく受け渡し） | その Context を使う部品すべて | めったに変わらない値（テーマ、言語、ログイン中のユーザー） |
| Zustand | 1 つのストア＋必要な部分だけを選んで読む関数（セレクター） | 選んだ値が変わった部品だけ | 小さく始めたい。Provider なしでどこからでも使える |
| Jotai | 小さな値（atom）を組み合わせる。atom から atom を計算できる | その atom を読む部品だけ | 独立した値がたくさんあり、依存関係で組み立てたい |
| Redux Toolkit | 1 つのストア、変更は「アクション」を送って reducer で行う | セレクターで選んだ値が変わった部品 | 変更の履歴を追いたい（DevTools）、大人数で決まりごとをそろえたい |
| Signals | 値そのものが読んだ場所を覚えていて、変わると直接そこを更新する | その値を読んでいる箇所だけ（部品単位でもない） | Solid・Vue・Svelte 5・Angular では標準の書き方（Preact は公式パッケージ @preact/signals で使える） |

Context でよくある落とし穴は、 **変わりやすい値を大きなオブジェクトにまとめて配る** ことです。その一部だけが変わっても、Context を使う部品が全部描き直されます。変わりやすい値は分けるか、セレクターのある道具に移します。

```
// Zustand: 選んだ値（count）が変わったときだけ、この部品が描き直される
const useCart = create((set) => ({
  items: [],
  add: (item) => set((s) => ({ items: [...s.items, item] })),
}));
const count = useCart((s) => s.items.length);
```

Signals を JavaScript の標準に入れる提案（TC39 Signals）があるが、2026 年 11 月の時点ではまだ Stage 1 で、仕様は固まっていない。今使うなら各フレームワークやライブラリのシグナルを使う。

## URL の状態：共有と「戻る」

検索結果の絞り込みやページ番号をストアに置くと、リンクを送っても相手には同じ画面が出ず、再読み込みで消え、ブラウザの「戻る」も効きません。 `?q=react&page=2&sort=new` のように URL に置けば、全部が自然に解決します。

- 持ち主は URL なので、部品は URL から読み、変えるときは URL を書き換える（コピーをストアに持たない）。
- 入力のたびに書き換えると履歴が埋まるので、検索語は確定時に、または履歴を置き換える形（replace）で書く。
- URL の値は文字列なので、数値や配列は読むときに検証・変換する（フォームの入力と同じく、外から来る値として扱う）。

## 計算で出せる値は持たない

いちばんよくある不具合の 1 つが、 **元の値から計算できるものを別の状態として持ち、同期を取ろうとする** ことです。

同期する（ずれる）

計算する

```
const [items, setItems] = useState([]);
const [total, setTotal] = useState(0);
useEffect(() => {                 // items が変わったら total を合わせる
  setTotal(items.reduce((s, i) => s + i.price, 0));
}, [items]);
```

描画が 1 回余分に走り、その間は合計が古い値のまま見えます。 `setItems` を呼ぶ場所が増えると、合わせ忘れも起きます。

```
const [items, setItems] = useState([]);
const total = items.reduce((s, i) => s + i.price, 0);   // 描画のたびに計算
// 重い計算なら useMemo、シグナルなら computed / derived で同じことができる
```

持ち主は `items` だけになり、ずれようがありません。「この値を状態にする前に、ほかの値から出せないか」を毎回確かめます。

（元のページで操作できます → https://memo.taka1156.site/state-management.html#derived）

## よくある誤解

✗ 誤解: ある程度の規模になったら Redux のようなグローバルストアが必須

✓ 正しくは: サーバー状態をデータ取得ライブラリに、URL・フォーム・ローカルの値をそれぞれの場所に置くと、グローバルに残る値は少ない。必要になってから小さなストアを足せば足りることが多い。

✗ 誤解: React Context を使えば状態管理ライブラリは要らない

✓ 正しくは: Context は値を下へ配る仕組みで、変わったときは使う部品が全部描き直される。めったに変わらない値には十分だが、頻繁に変わる値を広く配るならセレクターのある道具のほうが向く。

✗ 誤解: API から取ったデータはストアにコピーしておくと扱いやすい

✓ 正しくは: コピーした瞬間から、サーバーとのずれを自分で管理することになる。取り直し・無効化・ローディング表示はデータ取得ライブラリに任せ、コピーしない。

✗ 誤解: Signals は JavaScript の標準になった

✓ 正しくは: 標準化の提案はまだ Stage 1 で、仕様は固まっていない。今使われているのは、各フレームワークが自分で実装したシグナル。

## 関連メモ

- [UI 更新の3つの方式](https://memo.taka1156.site/md/reactivity-models.md) — 値が変わったあと画面をどう描き直すか（仮想 DOM・シグナル・コンパイラ）
- [React と Solid](https://memo.taka1156.site/md/react-vs-solid.md) ・ [Vue と Svelte](https://memo.taka1156.site/md/vue-vs-svelte.md) — 各フレームワークの状態の持ち方
- [HTTP キャッシュ](https://memo.taka1156.site/md/http-cache.md) — stale-while-revalidate の元の考え方
- [キャッシュ戦略](https://memo.taka1156.site/md/cache-strategies.md) — 更新したら無効化する、というキャッシュの基本
- [レンダリング戦略](https://memo.taka1156.site/md/rendering-strategies.md) — サーバー側でデータを取って描く構成
- [ブラウザのストレージ](https://memo.taka1156.site/md/browser-storage.md) — 再読み込み後も残したい値の置き場所

## 参考

- [TanStack Query: Important Defaults](https://tanstack.com/query/v5/docs/framework/react/guides/important-defaults)
- [React: Choosing the State Structure](https://react.dev/learn/choosing-the-state-structure)
- [React: You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect)
- [TC39: Proposal Signals](https://github.com/tc39/proposal-signals)

2026 年 11 月に確認。
