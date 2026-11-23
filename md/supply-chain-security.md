<!-- scripts/memo.py build が自動生成。手で編集しない -->

# サプライチェーンセキュリティ

> 依存パッケージ・CI・公開の経路から悪意あるコードが入る手口（タイポスクワッティング・依存関係かく乱・アカウント乗っ取り・xz・tj-actions・Shai-Hulud）と、インストール時の守り（ロックファイル・スクリプト停止・公開後の待ち時間）、SBOM、署名と来歴（Sigstore・SLSA・trusted publishing）を図解する

- URL: https://memo.taka1156.site/supply-chain-security.html
- タグ: セキュリティ, 開発ツール, JavaScript
- 日付: 2026-11-14

---

自分で書いていないコードから入る攻撃 ── 依存・CI・公開の経路と、その守り方

**ざっくり言うと**

- アプリのコードの大半は他人が書いた依存パッケージで、その作者のアカウントや CI が乗っ取られると、自分のコードを変えなくても攻撃が入る。
- 入口のほとんどはインストールの瞬間なので、ロックファイル・依存のスクリプトの停止・公開直後の版を待つ設定でまず防ぐ。
- SBOM で中身を把握し、署名と来歴で出どころを確かめるが、来歴は「どこで作られたか」を示すだけで中身が安全とは言わない。

## 攻撃の通り道

ソフトウェアは、作者のコードが依存パッケージと一緒にビルドされ、レジストリに公開され、利用者の手元でインストールされて動きます。 **この途中のどこか 1 か所** でも乗っ取られれば、下流の全員に届きます。

**ソースコード**

リポジトリ・メンテナ

悪意ある人がメンテナになる（xz）

**依存パッケージ**

直接の依存と、その先の依存

似た名前・同じ名前の偽物

**ビルド・CI**

Actions・ビルドサーバー

使っている Action の乗っ取り（tj-actions）

**公開・レジストリ**

npm・PyPI・コンテナレジストリ

盗んだトークンで悪意ある版を公開

**インストール・実行**

開発者の PC・CI・本番

postinstall で秘密を盗む（Shai-Hulud）

## 主な手口

| 手口 | しくみ | 実例 |
| --- | --- | --- |
| タイポスクワッティング | 人気パッケージに似た名前（ `reqeusts` など）で偽物を公開し、打ち間違いや AI の提案ミスで入れさせる | 各レジストリで繰り返し見つかっている |
| 依存関係かく乱（dependency confusion） | 社内専用パッケージと同じ名前を公開レジストリに高い版番号で出し、パッケージマネージャーに公開側を選ばせる | 2021 年に Alex Birsan が Apple・Microsoft などで実証 |
| メンテナのアカウント乗っ取り | フィッシングなどで公開用のトークンや 2FA を奪い、正規のパッケージに悪意ある版を出す | 2025 年 9 月の Shai-Hulud は、盗んだトークンで自分を別のパッケージにも広げるワームだった |
| 悪意あるメンテナ | 何年も貢献して信頼を得てから、共同メンテナとしてバックドアを入れる | 2024 年 3 月に見つかった xz Utils 5.6.0・5.6.1 のバックドア（CVE-2024-3094） |
| CI の部品の乗っ取り | 多くのリポジトリが使う Action などを改ざんし、それを使うワークフローの秘密を盗む | 2025 年 3 月、2 万 3,000 以上のリポジトリが使う tj-actions/changed-files の版タグが書き換えられた |
| ビルド環境の改ざん | ソースは正しいまま、ビルドの途中で悪意あるコードを差し込む | 2020 年に発覚した SolarWinds Orion の事件 |

どの手口も、利用者側から見ると「いつもどおり依存を入れた・CI を回した」だけです。だから守りは、 **入れるときに勝手に動かさない・知らない版をすぐ入れない・何が入っているかを把握する** 、という利用者側の仕組みが中心になります。

## インストールの瞬間を守る

悪意あるパッケージの多くは、 `preinstall` ・ `postinstall` などのインストール時のスクリプトで動きます。コードを import する前、インストールしただけで、開発者の PC や CI のトークンが盗まれます。

1. **ロックファイルをコミットし、CI は固定のまま入れる** `npm ci` ・ `pnpm install --frozen-lockfile` で、レビュー済みの版だけを入れる。勝手に新しい版に上がらない（ [JS のモジュールと依存管理](https://memo.taka1156.site/md/js-modules.md) ）。
2. **依存のインストールスクリプトを止める** 実行を許すのは、ビルドが本当に要るパッケージ（esbuild・sharp など）だけにし、許可の一覧をコミットする。
3. **公開されたばかりの版を入れない** 悪意ある版は、たいてい数時間〜数日で見つかって消される。公開から一定時間たった版だけを入れる設定にすると、その間に避けられる。
4. **社内パッケージはスコープとレジストリを固定する** `@acme/*` は社内レジストリからだけ取る、と `.npmrc` で決めておくと、同じ名前の公開パッケージに置き換わらない。

| パッケージマネージャー | 依存のスクリプト | 公開直後の版を待つ |
| --- | --- | --- |
| pnpm | v10（2025 年 1 月）から既定で止める。許可は `allowBuilds` （v10 当初は `onlyBuiltDependencies` ） | v11（2026 年 4 月）から既定で 1 日待つ（ `minimumReleaseAge` ） |
| npm | v12（2026 年 7 月）から既定で止める。許可は `npm approve-scripts` で作る一覧 | `min-release-age` で設定できるが、既定では無効 |
| Bun | 既定で止める。許可は `trustedDependencies` （npm 由来の人気パッケージの一部は既定で許可済み） | `minimumReleaseAge` （bunfig.toml・秒で指定）で設定できるが、既定では無効 |

待つ設定にすると、脆弱性の修正版もすぐには入らない。急ぐ修正だけを例外にできる設定（pnpm の `minimumReleaseAgeExclude` など）を使う。

## 何が入っているかを知る：SBOM と脆弱性スキャン

**SBOM** （Software Bill of Materials、ソフトウェア部品表）は、ソフトウェアに含まれるパッケージとその版を機械が読める形で並べた一覧です。形式は SPDX と CycloneDX が主流で、ビルド時に作ってイメージやリリースに添付します。新しい脆弱性が発表されたときに「うちのどの製品に入っているか」をすぐ引けるのが利点です。

脆弱性スキャン（ `npm audit` 、OSV-Scanner、Dependabot など）は、SBOM や依存の一覧を脆弱性データベースと照らし合わせます。ただし見つけられるのは **報告済みの脆弱性** です。公開されたばかりの悪意あるパッケージは、データベースに載るまで素通りします。悪意あるパッケージの検出には、パッケージの振る舞い（インストール時の通信、難読化されたコードなど）を見るサービスが別にあります。

## 出どころを確かめる：署名と来歴

レジストリから落としたパッケージが、 **本当にそのリポジトリのそのコミットから、そのビルド環境で作られたものか** を確かめるしくみです。鍵を長く保管しなくてよい署名の基盤として Sigstore が広く使われています。

**1. CI の身元で証明書をもらう** Fulcio

ビルドのジョブが OIDC トークンを見せ、その身元（リポジトリ・ワークフロー）を書いた数分で切れる証明書をもらう。

**2. 成果物と来歴に署名する** provenance

「どのソースから、どの手順で作ったか」を書いた来歴（in-toto 形式）に署名する。鍵はその場で捨てる。

**3. 公開ログに記録する** Rekor

署名を追記専用の公開ログに載せる。証明書が切れた後でも、署名した時点で有効だったことを確かめられる。

**4. 利用者が検証する** verify

`npm audit signatures` や `cosign verify` で、期待したリポジトリ・ワークフローで作られたかを確かめる。

**SLSA** （Supply-chain Levels for Software Artifacts）は、来歴がどれだけ信用できるかを段階で表す枠組みです。Build L1 は来歴があること、L2 はホストされたビルド環境が署名した来歴であること、L3 はビルドどうしが互いに干渉できない堅いビルド環境であることを求めます。npm の trusted publishing（CI から OIDC で公開し、来歴を自動で付ける）は Build L2 に当たります。

2026 年 5 月には、CI のキャッシュを汚して正規のワークフローの中で悪意ある版を作らせる攻撃があり、正しいリポジトリとワークフローを指す本物の来歴付きで公開された。来歴は「どこで作られたか」の証明であって、中身が安全だという証明ではない。SLSA は、L3 のビルド環境ならこの手口は防げたと説明している。

## 公開する側がすること

- **トークンで公開しない** : CI からは trusted publishing（OIDC）で公開する。npm は 2025 年の Shai-Hulud を受けて、古い形式のトークンを廃止し、公開用のトークンの期限を短くし、FIDO（パスキー・セキュリティキー）の 2FA へ移した。
- **CI の部品をコミット SHA で固定する** : Action をタグで参照すると、タグを付け替えられたときにそのまま悪意あるコードが動く。SHA で固定し、更新は Dependabot の PR で受ける（ [CI/CD と GitHub Actions](https://memo.taka1156.site/md/ci-cd.md) ）。
- **ワークフローの権限を絞る** : `permissions` を必要なものだけにし、公開のジョブは保護されたブランチと Environment からだけ動かす。
- **依存を減らす** : 数行で書ける機能のために依存を足さない。依存の数だけ、乗っ取られうる人とアカウントが増える。

## 点検リスト

0 / 10

### 使う側

- ロックファイルをコミットし、CI は frozen で入れている 勝手に新しい版に上がらない
- 依存のインストールスクリプトを止め、許可の一覧をコミットしている インストールしただけで動くコードをなくす
- 公開直後の版を待つ設定にしている 悪意ある版が見つかって消されるまでの時間を稼ぐ
- 社内パッケージのスコープを社内レジストリに固定している 依存関係かく乱を防ぐ
- 依存の更新を PR で受け、差分を見てからマージしている Dependabot・Renovate など
- リリースごとに SBOM を作って保存している 新しい脆弱性の影響範囲をすぐ引ける

（元のページで操作できます → https://memo.taka1156.site/supply-chain-security.html#checklist）

### 作る・公開する側

- Action をコミット SHA で固定している タグの付け替えで乗っ取られない
- ワークフローの permissions を最小にしている 盗まれても使える権限が小さい
- トークンではなく trusted publishing で公開している 盗まれる長期のトークンがない
- 公開するアカウントに FIDO の 2FA を設定している フィッシングで 2FA を突破されにくい

チェックはこのページを開いている間だけ保たれる（保存しない）。

（元のページで操作できます → https://memo.taka1156.site/supply-chain-security.html#checklist）

## よくある誤解

✗ 誤解: 脆弱性スキャンが通れば、悪意あるパッケージは入っていない

✓ 正しくは: スキャンが見るのは報告済みの脆弱性のデータベース。公開されたばかりの悪意ある版は、見つかって登録されるまで引っかからない。スクリプトの停止や公開後の待ち時間と組み合わせる。

✗ 誤解: 来歴（provenance）付きのパッケージなら安全

✓ 正しくは: 来歴が示すのは「このリポジトリのこのワークフローで作られた」こと。そのリポジトリや CI 自体が乗っ取られていれば、本物の来歴付きで悪意ある版が出る。タイポスクワッティングの偽物も、自分のリポジトリから来歴を付けられる。

✗ 誤解: ダウンロード数の多い有名なパッケージなら安全

✓ 正しくは: 攻撃者にとっては、利用者が多いほど狙う価値がある。xz Utils も tj-actions も広く使われていた。有名かどうかより、入れ方（固定・待ち時間・スクリプトの停止）で守る。

✗ 誤解: import していない依存なら、悪さはできない

✓ 正しくは: インストール時のスクリプトは、import する前のインストールの時点で動く。開発者の PC や CI の秘密は、そこで盗まれる。

## 関連メモ

- [JS のモジュールと依存管理](https://memo.taka1156.site/md/js-modules.md) — ロックファイルと、npm・pnpm・Bun のインストール方式
- [CI/CD と GitHub Actions](https://memo.taka1156.site/md/ci-cd.md) — Action の SHA 固定、権限、OIDC
- [GitHub サービス](https://memo.taka1156.site/md/github-services.md) — Dependabot と依存関係レビュー
- [Docker イメージの種類](https://memo.taka1156.site/md/docker-images.md) — SBOM・署名付きの最小イメージ
- [暗号の基礎](https://memo.taka1156.site/md/crypto-basics.md) — 署名と証明書の土台

## 参考

- [SLSA: Security levels](https://slsa.dev/spec/v1.1/levels)
- [SLSA Blog: Mini Shai-Hulud: what SLSA can and cannot do](https://slsa.dev/blog/2026/05/mini-shai-hulud-what-slsa-can-and-cannot-do)
- [GitHub Blog: Our plan for a more secure npm supply chain](https://github.blog/security/supply-chain-security/our-plan-for-a-more-secure-npm-supply-chain/)
- [pnpm: Supply Chain Security](https://pnpm.io/supply-chain-security)
- [Unit 42: GitHub Actions Supply Chain Attack（tj-actions/changed-files）](https://unit42.paloaltonetworks.com/github-actions-supply-chain-attack/)
- [CNCF TAG Security: Malicious maintainer introduces sophisticated backdoor in xz](https://tag-security.cncf.io/community/catalog/compromises/2024/xz/)

2026 年 11 月に確認。
