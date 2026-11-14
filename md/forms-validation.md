<!-- scripts/memo.py build が自動生成。手で編集しない -->

# フォームとバリデーション

> フォームの制御・非制御と React 19 の form action、ブラウザ標準の検証（制約検証 API・:user-invalid）、エラーを出すタイミング、クライアントとサーバーでスキーマを共有する方法（Zod・Standard Schema）、エラーの伝え方と送信時の注意を図解する

- URL: https://memo.taka1156.site/forms-validation.html
- タグ: フロントエンド, JavaScript, バックエンド
- 日付: 2026-11-14

---

制御・非制御、ブラウザ標準の検証、エラーを出すタイミング、スキーマの共有

**ざっくり言うと**

- フォームの検証は 2 層で、ブラウザ側は「早く気づかせる」ため、サーバー側は「不正な値を入れさせない」ためにあり、サーバー側は省けない。
- 同じスキーマ（Zod など）を両側で使えばルールがずれず、サーバーでしか分からない誤り（重複など）は項目ごとのエラーとして返す。
- エラーは入力中ではなく、欄を離れたときか送信時に出し、文字で「どこが・なぜ・どう直すか」を欄に紐づけて伝える。

## 検証は 2 層、役割が違う

ブラウザ側（クライアント） **早く気づかせる＝使いやすさのため**

- 送信前に直せるので、往復を待たなくてよい
- 開発者ツールや curl で簡単に飛ばせる
- なくても安全性は変わらない

サーバー側 **不正な値を入れさせない＝安全のため**

- どこから来たリクエストでも必ず通る最後の関門
- DB の重複や在庫など、サーバーでしか分からないことも確かめる
- 省くと、画面を通らない直接のリクエストで壊れる

外から来る値はすべて信用しない、というのがサーバー側の原則です。型は実行時には消えるので、TypeScript の型があっても入力の検証は別に要ります（ [TypeScript 学習フローと仕組み](https://memo.taka1156.site/md/typescript.md) ）。入力をそのまま SQL や HTML に入れたときの危険は [実装起因の脆弱性（入力の扱い）](https://memo.taka1156.site/md/web-vulnerabilities.md) にあります。

## 制御と非制御：値を誰が持つか

|  | 制御（controlled） | 非制御（uncontrolled） |
| --- | --- | --- |
| 値の持ち主 | JavaScript の状態。 `value` と `onChange` で毎回同期する | DOM（入力欄そのもの）。送信時に `FormData` などで読む |
| 描き直し | 1 文字打つたびに部品が描き直される | 入力中は描き直さない |
| 得意なこと | 入力に合わせて即座に整形する（カード番号の区切りなど）、ほかの欄と連動する | 項目が多いフォーム、ファイル入力、JS が動く前でも送れるフォーム |
| 例 | React の `useState` ＋ `value` | React 19 の form action、React Hook Form（既定は非制御） |

React 19 では `<form action={関数}>` に関数を渡せるようになり、送信時に `FormData` を受け取れます。送信中かどうかは `useActionState` や `useFormStatus` で読めるので、非制御のままでも送信まわりを書けます。

```
const [state, formAction, isPending] = useActionState(signup, { errors: {}, values: {} });

<form action={formAction}>
  <input name="email" type="email" required defaultValue={state.values.email} />
  {state.errors.email && <p id="email-err">{state.errors.email}</p>}
  <button disabled={isPending}>登録</button>
</form>
```

React 19 は、form action が例外を投げずに終わると、非制御の欄を初期値に戻す。エラーを返したときに入力を残したいなら、上のように受け取った値を state で返し、 `defaultValue` に入れ直す。

## ブラウザ標準の検証

HTML の属性だけで、ブラウザはかなりの検証をしてくれます。JavaScript が動く前でも働き、スマホでは入力に合ったキーボードも出ます。

| 属性 | 確かめること | 注意 |
| --- | --- | --- |
| `required` | 空でないか | 空白だけの入力は通る（前後の空白はサーバーでも取り除く） |
| `type="email"` ・ `"url"` | 大まかな形式 | 形式だけ。届くアドレスかは確認メールでしか分からない |
| `minlength` ・ `maxlength` | 文字数 | 数え方は UTF-16 の単位。絵文字は 2 以上に数えられる（ [文字コードと Unicode](https://memo.taka1156.site/md/unicode-text.md) ） |
| `min` ・ `max` ・ `step` | 数値・日付の範囲 | `type="number"` は値が文字列で届く |
| `pattern` | 正規表現に全体が一致するか | ルールを `title` や説明文にも書く |

独自のルールは **制約検証 API** （Constraint Validation API）で足せます。 `setCustomValidity('メッセージ')` で欄を不正な状態にし、空文字を渡すと戻ります。 `input.validity` で、どの条件に引っかかったか（ `valueMissing` ・ `typeMismatch` など）を調べられます。

見た目では、 `:invalid` は **ページを開いた瞬間から** 空の必須欄に当たってしまいます。 `:user-invalid` は、利用者が値を変えて欄を離れた後（または送信しようとした後）にだけ当たるので、エラーの色付けにはこちらを使います。2023 年 11 月に主要ブラウザがそろって対応しました。

エラーの表示を自前の文言とデザインにしたいときは、 `<form novalidate>` でブラウザの吹き出しだけを止め、属性と `checkValidity()` はそのまま使う。

## エラーを出すタイミング

同じルールでも、いつ出すかで使い心地が大きく変わります。下の欄にメールアドレスを入れてみて、タイミングを切り替えて比べてください。

入力のたび

欄を離れたとき

送信時だけ

1 文字目から「形式が正しくありません」と出る。まだ打っている途中なのに責められているように感じる。

欄を離れたときに初めて確かめる。一度エラーが出た後は、打つたびに確かめ直し、直った瞬間に消す。多くの場面でこれがよい。

送信を押すまで何も言わない。短いフォームならよいが、長いフォームでは最後にまとめて直すことになる。

メールアドレス

形式が正しくありません。「@」の後ろにドメイン名を入れてください（例: you@example.com）

送信

送信できる形式です

「欄を離れたら確かめ、エラーが出た後は打つたびに確かめ直す」という組み合わせは、 **遅く叱り、早く褒める** と覚えられます。間違いの指摘は打ち終わるまで待ち、直ったことはすぐに伝えます。

（元のページで操作できます → https://memo.taka1156.site/forms-validation.html#timing）

## スキーマを 1 つにして両側で使う

同じルールをブラウザ側とサーバー側で別々に書くと、片方だけ変えてずれます。 **スキーマ** （値の形とルールの定義）を 1 つ書き、両方から使います。

```
// schema.ts — ブラウザとサーバーの両方から import する
import * as z from 'zod';
export const Signup = z.object({
  email: z.string().trim().pipe(z.email('メールアドレスの形式が正しくありません')),
  password: z.string().min(12, '12 文字以上にしてください'),
});

// サーバー側（form action・API のハンドラー）
export async function signup(prev, formData) {
  const values = Object.fromEntries(formData);
  const { password, ...safeValues } = values;   // パスワードは返さない
  const r = Signup.safeParse(values);
  if (!r.success) return { errors: z.flattenError(r.error).fieldErrors, values: safeValues };   // 項目ごとのエラー
  if (await userExists(r.data.email))
    return { errors: { email: ['このアドレスは登録済みです'] }, values: safeValues };  // サーバーでしか分からない誤り
  await createUser(r.data);
  return { errors: {}, values: {} };
}
```

- **サーバーでしか分からない誤りも、項目ごとのエラーとして返す** : 「登録済み」「在庫切れ」を画面上部の 1 行にまとめず、どの欄の問題かを示す。
- **パスワードを返さない** : エラー時に入力を返すときも、パスワードやカード番号は戻さない。
- **ライブラリを選びやすくする Standard Schema** : Zod・Valibot・ArkType などが共通のインターフェースを実装していて、対応するフォームライブラリやフレームワークは、どのスキーマライブラリでもそのまま受け付ける。

入力の形を守るスキーマと、業務のルール（「タスク名は 1〜100 文字」など）を守る値オブジェクトは役割が違う。スキーマは HTTP の入口の係（ [DDD とオニオンアーキテクチャ](https://memo.taka1156.site/md/ddd-onion.md) ）。

### サーバーに聞かないと分からない検証

「このユーザー名は空いているか」を入力中に知らせたいときは、打つたびに問い合わせず、 **打ち終わってから少し待って（デバウンス）** 問い合わせます。古い問い合わせの答えが後から届いて新しい表示を上書きしないよう、最後の問い合わせの答えだけを使います。ただし、確認と送信の間にほかの人が同じ名前を取ることもあるので、 **送信時にサーバーで必ずもう一度確かめ** 、DB の一意制約でも守ります。

## エラーの伝え方

1. **欄ごとにラベルを付ける** `<label for>` で結びつける。placeholder は入力すると消えるので、ラベルの代わりにならない。
2. **エラー文を欄に紐づける** エラーの要素に id を付け、欄の `aria-describedby` で指す。欄には `aria-invalid="true"` を付ける。読み上げソフトが欄に入ったときにエラーも読む。
3. **色だけで伝えない** 赤い枠に加えて、記号と文字で「どこが・なぜ・どう直すか」を書く。
4. **送信で失敗したら最初のエラーへフォーカスを移す** 長いフォームでは、上部にエラーの一覧と各欄へのリンクを置く。

詳しいチェック項目は [アクセシビリティ チェックリスト](https://memo.taka1156.site/md/a11y-checklist.md) の「フォーム」にあります。

## 送信のときに気をつけること

- **二重送信** : 送信中はボタンを押せなくし、送信中であることを表示する。ただしそれだけでは自動リトライや再読み込みは防げないので、注文や決済はサーバー側で冪等にする（ [冪等キーとリトライ](https://memo.taka1156.site/md/api-idempotency.md) ）。
- **失敗しても入力を消さない** : エラー時に入力し直させない。長いフォームは下書きを保存する（ [ブラウザのストレージ](https://memo.taka1156.site/md/browser-storage.md) ）。
- **自動入力とキーボードを助ける** : `autocomplete="email"` ・ `"new-password"` ・ `"one-time-code"` などを付け、数字だけの欄は `inputmode="numeric"` にする。
- **受け付ける形を広くする** : 電話番号のハイフンや全角数字、前後の空白は、エラーにせずサーバー側で整える。

## よくある誤解

✗ 誤解: ブラウザ側で検証していれば、サーバー側の検証は省ける

✓ 正しくは: ブラウザ側の検証は、開発者ツールや curl で簡単に飛ばせる。サーバー側は、どこから来たリクエストにも必ず通る最後の関門なので省けない。

✗ 誤解: type="email" を付ければメールアドレスの検証は十分

✓ 正しくは: 確かめているのは大まかな形式だけ。実在して届くかは、確認メールのリンクを踏んでもらうまで分からない。

✗ 誤解: 入力のたびにエラーを出すのがいちばん親切

✓ 正しくは: 打ち終わる前から誤りを指摘され続けて、かえって使いにくい。欄を離れたときに初めて確かめ、エラーが出た後だけ打つたびに確かめ直すとよい。

✗ 誤解: placeholder があればラベルは要らない

✓ 正しくは: 入力すると消えるので、何の欄だったか分からなくなる。読み上げソフトでもラベルとして扱われないことがある。ラベルは常に表示する。

## 関連メモ

- [アクセシビリティ チェックリスト](https://memo.taka1156.site/md/a11y-checklist.md) — ラベル・エラー文・フォーカスの基準
- [実装起因の脆弱性（入力の扱い）](https://memo.taka1156.site/md/web-vulnerabilities.md) — サーバー側で入力を信用しない理由
- [冪等キーとリトライ](https://memo.taka1156.site/md/api-idempotency.md) — 二重送信をサーバー側で防ぐ
- [TypeScript 学習フローと仕組み](https://memo.taka1156.site/md/typescript.md) — 型は実行時に消えるので、入力は実行時に検証する
- [DDD とオニオンアーキテクチャ](https://memo.taka1156.site/md/ddd-onion.md) — 入力のスキーマと業務ルールの分け方
- [文字コードと Unicode](https://memo.taka1156.site/md/unicode-text.md) — 文字数の数え方と全角・半角

## 参考

- [React: useActionState](https://react.dev/reference/react/useActionState)
- [MDN: Constraint validation](https://developer.mozilla.org/en-US/docs/Web/HTML/Guides/Constraint_validation)
- [MDN: :user-invalid](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Selectors/:user-invalid)
- [Standard Schema](https://standardschema.dev/)
- [W3C WAI: Forms Tutorial](https://www.w3.org/WAI/tutorials/forms/)

2026 年 11 月に確認。
