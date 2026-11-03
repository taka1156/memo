#!/usr/bin/env python3
"""MEMO リポジトリ用ツール（標準ライブラリのみ）

使い方（どのディレクトリから実行してもよい）:
  python3 scripts/memo.py new   NAME                  テンプレートから docs/NAME.html を作る
  python3 scripts/memo.py add   SRC NAME [--force]    外部の HTML を docs/NAME.html として取り込む
  python3 scripts/memo.py path  NAME                  docs/NAME.html の絶対パスを表示
  python3 scripts/memo.py url   [NAME]                公開 URL を表示（docs/CNAME の独自ドメイン）
  python3 scripts/memo.py lint  MEMO... [--fix] [--backlink]
  python3 scripts/memo.py meta  MEMO [--title T] [--desc D] [--tags a,b] [--date YYYY-MM-DD]
  python3 scripts/memo.py build [--check]
  python3 scripts/memo.py list

MEMO / NAME は「docker」「docker.html」「docs/docker.html」のどれでもよい
（既存のファイルパスを渡した場合はそのファイルを対象にする）。
置き場所（docs/）やテンプレートの場所はこのスクリプトだけが知っている。

メモ = docs/ 直下の *.html（index.html・quiz.html 以外）。docs/ が GitHub Pages で公開される。
一覧情報は各メモの <head> 内の次のタグから読み取る:
  <title>                         タイトル（memo:title があればそちら優先）
  <meta name="description">       説明
  <meta name="memo:tags">         カンマ区切りのタグ
  <meta name="memo:date">         YYYY-MM-DD

確認クイズ（任意）は <script type="application/json" id="memo-quiz"> に問題データだけを書く。
表示用の UI はページ末尾に、トップのランダムクイズ用データは build で自動生成する。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"  # GitHub Pages の公開元
INDEX = DOCS / "index.html"
QUIZ_PAGE = DOCS / "quiz.html"  # 全メモの問題から 10 問解くページ
# メモではない特別なページ（一覧に載せない・メモ名に使えない）。build が一覧データを埋め込む
SPECIAL_PAGES = (INDEX, QUIZ_PAGE)
SPECIAL_NAMES = {p.name for p in SPECIAL_PAGES}
FALLBACK_URL = "https://taka1156.github.io/memo/"


def site_url() -> str:
    """公開 URL（末尾 /）。docs/CNAME があればその独自ドメインを使う。"""
    cname = DOCS / "CNAME"
    if cname.is_file():
        domain = cname.read_text(encoding="utf-8").strip().splitlines()[0].strip()
        if domain:
            return f"https://{domain}/"
    return FALLBACK_URL


SITE_URL = site_url()  # og:url / og:image の絶対 URL に使う
SITE_NAME = "MEMO"


def asset_version(name: str) -> str:
    """画像の中身から短いハッシュを作る。画像を差し替えると URL が変わり、
    Discord などの画像キャッシュが古いまま残るのを防ぐ。"""
    f = DOCS / "assets" / name
    return hashlib.sha256(f.read_bytes()).hexdigest()[:8] if f.is_file() else ""


OG_VERSION = asset_version("og.png")
HEAD_BEGIN = "<!-- memo:head（scripts/memo.py が自動生成。手で編集しない） -->"
HEAD_END = "<!-- /memo:head -->"
HEAD_RE = re.compile(r"<!-- memo:head.*?<!-- /memo:head -->\n?", re.S)
TEMPLATE = ROOT / ".claude" / "skills" / "memo-style" / "template.html"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BEGIN = "// MEMOS:BEGIN"
END = "// MEMOS:END"
BACKLINK_ID = "memo-backlink"
# ページ下部のフッターに置く「一覧に戻る」リンク。どのページの CSS にも依存しないよう、
# スタイルはすべてインラインで完結させる（独自の CSS 変数を参照しない）。
BACKLINK = (
    f'<footer id="{BACKLINK_ID}" '
    'style="max-width:880px;margin:40px auto 0;padding:16px;text-align:center">'
    '<a href="index.html" style="display:inline-block;padding:6px 14px;border-radius:999px;'
    "background:rgba(127,127,127,.15);color:inherit;font:600 12px/1.4 ui-monospace,Menlo,monospace;"
    'letter-spacing:.08em;text-decoration:none;opacity:.85">&larr; 一覧に戻る</a></footer>'
)

CURLY = "‘’“”"


# ---------------------------------------------------------------- 解析

class _Meta(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title" and not self.title:
            self._in_title = True
        elif tag == "meta" and "name" in a:
            self.meta.setdefault(a["name"].lower(), a.get("content", ""))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def parse_meta(text: str) -> tuple[dict, str]:
    p = _Meta()
    p.feed(HEAD_RE.sub("", text))
    return p.meta, p.title.strip()


def read_meta(path: Path) -> dict:
    p = _Meta()
    p.feed(HEAD_RE.sub("", path.read_text(encoding="utf-8")))
    m = p.meta
    tags = [t.strip() for t in m.get("memo:tags", "").split(",") if t.strip()]
    return {
        "file": path.name,
        "title": (m.get("memo:title") or p.title).strip() or path.stem,
        "desc": m.get("description", "").strip(),
        "tags": tags,
        "date": m.get("memo:date", "").strip() or git_added_date(path),
    }


def git_added_date(path: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--follow", "--format=%cs", "--",
             str(path.resolve().relative_to(ROOT))],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.split()
        return out[-1] if out else ""
    except Exception:
        return ""


def memo_path(arg: str, must_exist: bool = True) -> Path:
    """名前やパスを docs/ 内のメモのパスに解決する。"""
    p = Path(arg)
    if p.is_file():
        return p.resolve()
    name = p.name[:-5] if p.name.endswith(".html") else p.name
    if not NAME_RE.match(name):
        sys.exit(f"ファイル名は英小文字・数字・ハイフンのみ: {name!r}")
    if f"{name}.html" in SPECIAL_NAMES:
        sys.exit(f"{name}.html は特別なページです（{'トップ' if name == 'index' else 'クイズ'}）。メモ名に使えません")
    target = DOCS / f"{name}.html"
    if must_exist and not target.is_file():
        sys.exit(f"見つかりません: {target.relative_to(ROOT)}")
    return target


def memo_files() -> list[Path]:
    return sorted(p for p in DOCS.glob("*.html") if p.name not in SPECIAL_NAMES)


# ---------------------------------------------------------------- head（アイコン・OGP）

def head_block(text: str, filename: str) -> str:
    m, title = parse_meta(text)
    title = (m.get("memo:title") or title or SITE_NAME).strip()
    desc = m.get("description", "").strip()
    is_index = filename == "index.html"
    url = SITE_URL + ("" if is_index else filename)
    e = lambda v: html.escape(v, quote=True)
    lines = [
        HEAD_BEGIN,
        '<link rel="icon" href="assets/favicon.ico" sizes="any">',
        '<link rel="icon" type="image/png" sizes="32x32" href="assets/icon-32.png">',
        '<link rel="icon" type="image/png" sizes="192x192" href="assets/icon-192.png">',
        '<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">',
        f'<meta name="apple-mobile-web-app-title" content="{SITE_NAME}">',
        f'<meta property="og:type" content="{"website" if is_index else "article"}">',
        f'<meta property="og:site_name" content="{SITE_NAME}">',
        f'<meta property="og:title" content="{e(title)}">',
    ]
    if desc:
        lines.append(f'<meta property="og:description" content="{e(desc)}">')
    lines += [
        f'<meta property="og:url" content="{e(url)}">',
        f'<meta property="og:image" content="{SITE_URL}assets/og.png' + (f'?v={OG_VERSION}' if OG_VERSION else '') + '">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">',
        HEAD_END,
    ]
    return "\n".join(lines) + "\n"


def apply_head(text: str, filename: str) -> str:
    block = head_block(text, filename)
    if HEAD_RE.search(text):
        return HEAD_RE.sub(lambda _: block, text, count=1)
    m = re.search(r"</head>", text, re.I)
    if m:
        return text[: m.start()] + block + text[m.start():]
    m = re.search(r"<head[^>]*>", text, re.I)
    pos = m.end() if m else 0
    return text[:pos] + "\n" + block + text[pos:]


def refresh_head(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    new = apply_generated(text, path.name)
    if new != text:
        path.write_text(new, encoding="utf-8")
        return True
    return False


# ---------------------------------------------------------------- クイズ
#
# 各メモは問題データだけを持つ:
#   <script type="application/json" id="memo-quiz">
#   [{"q": "問題文", "choices": ["A", "B", "C"], "answer": 0,
#     "explain": "解説", "ref": "#本文の見出しなどの id"}]
#   explain / ref は任意。ref があると、間違えたときに本文の該当箇所へ飛ぶリンクが出る。
#   </script>
# 表示用の UI（<!-- memo:quiz --> ブロック）は memo.py がページ末尾に自動で入れる。
# build は全メモの問題を集めてトップページの QUIZZES に埋め込む（ランダムクイズ用）。

QUIZ_BEGIN = "<!-- memo:quiz（scripts/memo.py が自動生成。手で編集しない） -->"
QUIZ_END = "<!-- /memo:quiz -->"
QUIZ_RE = re.compile(r"<!-- memo:quiz.*?<!-- /memo:quiz -->\n?", re.S)
QUIZ_DATA_RE = re.compile(
    r"<script\b[^>]*\bid=[\"']memo-quiz[\"'][^>]*>(.*?)</script>", re.S | re.I)

# どのページの CSS にも依存しないよう、スタイルは #memo-quiz-ui の中で完結させる。
# ページ側の CSS 変数（memo-style のトークン）があれば使い、なければ代わりの色にする。
QUIZ_BLOCK = QUIZ_BEGIN + r"""
<section id="memo-quiz-ui" hidden aria-labelledby="memo-quiz-title">
<style>
#memo-quiz-ui{--mq-ok:#1a7f37;--mq-ng:#cf222e;max-width:880px;margin:48px auto 0;padding:0 0 8px;color:var(--fg,inherit);font-size:15px;line-height:1.7}
@media (prefers-color-scheme:dark){#memo-quiz-ui{--mq-ok:#3fb950;--mq-ng:#f85149}}
#memo-quiz-ui *{box-sizing:border-box}
#memo-quiz-ui h2{display:flex;align-items:baseline;gap:10px;margin:0 0 14px;padding:0 0 0 10px;border:0;border-left:3px solid var(--accent,currentColor);font-size:1.1rem;font-weight:700;color:inherit;background:none}
#memo-quiz-ui h2 small{font-size:.75rem;font-weight:400;color:var(--fg-2,inherit);opacity:.9}
#memo-quiz-ui .mq-q{margin:0 0 12px;padding:14px 16px;background:var(--surface,rgba(127,127,127,.06));border:1px solid var(--line,rgba(127,127,127,.3));border-radius:10px}
#memo-quiz-ui .mq-prompt{margin:0 0 10px;font-weight:700}
#memo-quiz-ui .mq-choices{display:flex;flex-direction:column;gap:6px}
#memo-quiz-ui .mq-c{display:block;width:100%;text-align:left;padding:8px 12px;border:1px solid var(--line,rgba(127,127,127,.3));border-radius:8px;background:var(--chip,rgba(127,127,127,.1));color:inherit;font:inherit;font-size:.9rem;line-height:1.5;cursor:pointer}
#memo-quiz-ui .mq-c:hover:not(:disabled){border-color:var(--accent,currentColor)}
#memo-quiz-ui .mq-c:disabled{cursor:default;opacity:.6}
#memo-quiz-ui .mq-c.mq-ok{opacity:1;border-color:var(--mq-ok);box-shadow:inset 3px 0 0 var(--mq-ok)}
#memo-quiz-ui .mq-c.mq-ng{opacity:1;border-color:var(--mq-ng);box-shadow:inset 3px 0 0 var(--mq-ng)}
#memo-quiz-ui .mq-fb{margin:10px 0 0;font-size:.85rem;color:var(--fg-2,inherit)}
#memo-quiz-ui .mq-ref{color:var(--accent,inherit);font-weight:700;text-decoration:none;white-space:nowrap}
#memo-quiz-ui .mq-ref:hover{text-decoration:underline}
#memo-quiz-ui .mq-result{margin:4px 0 12px;padding:16px 18px;background:var(--surface,rgba(127,127,127,.06));border:1px solid var(--accent,rgba(127,127,127,.3));border-radius:10px}
#memo-quiz-ui .mq-score{margin:0 0 10px;font-size:.9rem;color:var(--fg-2,inherit)}
#memo-quiz-ui .mq-score b{font:700 1.4rem/1.2 ui-monospace,Menlo,monospace;color:var(--accent,inherit)}
#memo-quiz-ui .mq-review{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:8px}
#memo-quiz-ui .mq-review li{padding:8px 0 0;border-top:1px solid var(--line,rgba(127,127,127,.3));font-size:.85rem}
#memo-quiz-ui .mq-rv-q{font-weight:700}
#memo-quiz-ui .mq-rv-a{color:var(--fg-2,inherit)}
#memo-quiz-ui b.ok{color:var(--mq-ok)}
#memo-quiz-ui b.ng{color:var(--mq-ng)}
.mq-flash{outline:3px solid var(--accent,#0077b6)!important;outline-offset:4px;border-radius:4px}
#memo-quiz-ui .mq-reset{margin-top:4px;padding:4px 12px;border:1px solid var(--line,rgba(127,127,127,.3));border-radius:999px;background:none;color:var(--fg-2,inherit);font:600 12px/1.4 ui-monospace,Menlo,monospace;cursor:pointer}
#memo-quiz-ui .mq-reset:hover{color:var(--accent,inherit);border-color:var(--accent,currentColor)}
</style>
<h2 id="memo-quiz-title">確認クイズ <small></small></h2>
<div class="mq-list"></div>
<div class="mq-result" hidden aria-live="polite"></div>
<button type="button" class="mq-reset">やり直す</button>
</section>
<script>
// 問題データ（#memo-quiz）がこのブロックより後ろにあってもよいよう、読み込み後に実行する
(function (run) {
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
})(function () {
  var data = document.getElementById('memo-quiz');
  var ui = document.getElementById('memo-quiz-ui');
  if (!data || !ui) return;
  var qs;
  try { qs = JSON.parse(data.textContent); } catch (e) { return; }
  if (!Array.isArray(qs)) return;
  qs = qs.filter(function (q) {
    return q && typeof q.q === 'string' && Array.isArray(q.choices) &&
      typeof q.answer === 'number' && q.choices[q.answer] !== undefined;
  });
  if (!qs.length) return;
  var list = ui.querySelector('.mq-list');
  var score = ui.querySelector('h2 small');
  var result = ui.querySelector('.mq-result');
  var picks = [];
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  // ---- 本文の該当箇所へ移動する。飛び先が閉じたタブや <details> の中なら先に開く
  function isShown(e) { return !!(e.offsetParent || e.getClientRects().length); }
  function controlFor(id) {
    var esc = window.CSS && CSS.escape ? CSS.escape(id) : id;
    var c = document.querySelector('[data-panel="' + esc + '"],[aria-controls="' + esc + '"],[data-target="#' + esc + '"],[href="#' + esc + '"]:not(.mq-ref)');
    if (c) return c;
    // onclick="switchTab('layers')" のように id の一部を渡すタブにも対応
    var keys = [id, id.replace(/^(panel|tab)[-_]/, '')];
    var all = document.querySelectorAll('[onclick]');
    for (var i = 0; i < all.length; i++) {
      var code = all[i].getAttribute('onclick');
      for (var k = 0; k < keys.length; k++) {
        if (code.indexOf("'" + keys[k] + "'") >= 0 || code.indexOf('"' + keys[k] + '"') >= 0) return all[i];
      }
    }
    return null;
  }
  function reveal(target) {
    var chain = [];
    for (var e = target; e && e !== document.body; e = e.parentElement) chain.unshift(e);
    chain.forEach(function (e) {
      if (e.tagName === 'DETAILS' && !e.open && e !== target) e.open = true;
      if (isShown(e)) return;
      var c = e.id && controlFor(e.id);
      if (c) c.click();
      if (!isShown(e) && e.hidden) e.hidden = false;
    });
  }
  function jump(id, smooth) {
    var target = document.getElementById(id);
    if (!target) return false;
    reveal(target);
    // 遠い飛び先までゆっくりスクロールすると待たされるので、画面 2 枚分より遠ければ一気に移動する
    var far = Math.abs(target.getBoundingClientRect().top) > innerHeight * 2;
    target.scrollIntoView({ behavior: smooth && !far ? 'smooth' : 'auto', block: 'start' });
    target.classList.add('mq-flash');
    setTimeout(function () { target.classList.remove('mq-flash'); }, 1800);
    return true;
  }
  // 本文の該当箇所（ref = "#id"）へのリンク
  function refLink(q, label) {
    if (typeof q.ref !== 'string' || !/^#[\w-]+$/.test(q.ref)) return null;
    var id = q.ref.slice(1);
    if (!document.getElementById(id)) return null;
    var a = el('a', 'mq-ref', label);
    a.href = q.ref;
    a.addEventListener('click', function (ev) {
      ev.preventDefault();
      if (history.replaceState) history.replaceState(null, '', q.ref);
      jump(id, true);
    });
    return a;
  }
  // クイズページなど他のページから page.html#id で来たとき
  if (/^#[\w-]+$/.test(location.hash) && location.hash !== '#memo-quiz-ui') {
    var initial = location.hash.slice(1);
    setTimeout(function () { jump(initial, false); }, 0);
  }
  function count() {
    var done = 0, ok = 0;
    picks.forEach(function (p, i) { if (p != null) { done++; if (p === qs[i].answer) ok++; } });
    return { done: done, ok: ok };
  }
  function showResult() {
    var c = count();
    result.textContent = '';
    var head = el('p', 'mq-score');
    head.appendChild(el('b', null, c.ok + ' / ' + qs.length));
    head.appendChild(document.createTextNode(' 問正解' +
      (c.ok === qs.length ? ' 🎉 全問正解！' : '（間違えた問題は本文で確認できます）')));
    result.appendChild(head);
    var ol = el('ol', 'mq-review');
    qs.forEach(function (q, i) {
      var ok = picks[i] === q.answer;
      var li = el('li', ok ? 'ok' : 'ng');
      var top = el('div', 'mq-rv-q');
      top.appendChild(el('b', ok ? 'ok' : 'ng', ok ? '⭕' : '❌'));
      top.appendChild(document.createTextNode(' Q' + (i + 1) + '. ' + q.q));
      li.appendChild(top);
      var ans = el('div', 'mq-rv-a');
      ans.appendChild(document.createTextNode('正解: ' + q.choices[q.answer]));
      if (!ok) ans.appendChild(document.createTextNode(' ／ あなたの答え: ' + q.choices[picks[i]]));
      li.appendChild(ans);
      if (!ok) {
        var link = refLink(q, '本文で確認する →');
        if (link) li.appendChild(link);
      }
      ol.appendChild(li);
    });
    result.appendChild(ol);
    result.hidden = false;
  }
  function update() {
    var c = count();
    score.textContent = c.done ? c.ok + ' / ' + c.done + ' 問正解' + (c.done < qs.length ? '（残り ' + (qs.length - c.done) + ' 問）' : '') : '全 ' + qs.length + ' 問';
    if (c.done === qs.length) showResult();
  }
  function render() {
    list.textContent = '';
    result.hidden = true;
    picks = qs.map(function () { return null; });
    qs.forEach(function (q, i) {
      var box = el('div', 'mq-q');
      box.appendChild(el('p', 'mq-prompt', 'Q' + (i + 1) + '. ' + q.q));
      var ch = el('div', 'mq-choices');
      var fb = el('p', 'mq-fb');
      fb.hidden = true;
      q.choices.forEach(function (c, j) {
        var b = el('button', 'mq-c', c);
        b.type = 'button';
        b.addEventListener('click', function () {
          var ok = j === q.answer;
          Array.prototype.forEach.call(ch.children, function (x, k) {
            x.disabled = true;
            if (k === q.answer) x.classList.add('mq-ok');
          });
          if (!ok) b.classList.add('mq-ng');
          fb.textContent = '';
          fb.appendChild(el('b', ok ? 'ok' : 'ng', ok ? '⭕ 正解' : '❌ 不正解'));
          fb.appendChild(document.createTextNode(
            (ok ? '' : '（正解: ' + q.choices[q.answer] + '）') + (q.explain ? ' ' + q.explain : '')));
          if (!ok) {
            var link = refLink(q, '本文で確認する →');
            if (link) { fb.appendChild(document.createTextNode(' ')); fb.appendChild(link); }
          }
          fb.hidden = false;
          picks[i] = j;
          update();
        });
        ch.appendChild(b);
      });
      box.appendChild(ch);
      box.appendChild(fb);
      list.appendChild(box);
    });
    update();
  }
  ui.querySelector('.mq-reset').addEventListener('click', function () {
    render();
    ui.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  render();
  ui.hidden = false;
});
</script>
""" + QUIZ_END + "\n"


def validate_quiz(qs) -> list[str]:
    """問題データの形をチェックし、問題点のリストを返す（空なら OK）。"""
    if not isinstance(qs, list) or not qs:
        return ["クイズは 1 問以上の配列にする"]
    probs = []
    for i, q in enumerate(qs, 1):
        if not isinstance(q, dict):
            probs.append(f"Q{i}: オブジェクトではない")
            continue
        if not isinstance(q.get("q"), str) or not q["q"].strip():
            probs.append(f"Q{i}: q（問題文）がない")
        ch = q.get("choices")
        if not (isinstance(ch, list) and 2 <= len(ch) <= 5
                and all(isinstance(c, str) and c.strip() for c in ch)):
            probs.append(f"Q{i}: choices は 2〜5 個の文字列にする")
            continue
        a = q.get("answer")
        if isinstance(a, bool) or not isinstance(a, int) or not 0 <= a < len(ch):
            probs.append(f"Q{i}: answer は choices の番号（0 始まり）にする")
        if "explain" in q and not isinstance(q["explain"], str):
            probs.append(f"Q{i}: explain は文字列にする")
        if "ref" in q and not (isinstance(q["ref"], str) and re.fullmatch(r"#[\w-]+", q["ref"])):
            probs.append(f"Q{i}: ref は \"#id\" の形にする")
    return probs


def read_quiz(text: str) -> tuple[list | None, list[str]]:
    """(問題リスト or None（データなし）, 問題点) を返す。"""
    m = QUIZ_DATA_RE.search(QUIZ_RE.sub("", text))
    if not m:
        return None, []
    try:
        qs = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        return None, [f"クイズの JSON が壊れている（{e.msg}, {e.lineno} 行目）"]
    probs = validate_quiz(qs)
    if not probs and len(qs) >= 3 and len({q["answer"] for q in qs}) == 1:
        probs.append("正解の位置（answer）が全問同じ。選択肢の順番を入れ替えて散らす")
    if not probs:
        for i, q in enumerate(qs, 1):
            ref = q.get("ref")
            if ref and not re.search(rf"\bid=[\"']?{re.escape(ref[1:])}[\"'\s>]", text):
                probs.append(f"Q{i}: ref の飛び先 {ref} がページ内にない")
    return qs, probs


def apply_quiz(text: str) -> str:
    """問題データがあれば表示用ブロックを入れる／更新する。なければ取り除く。"""
    if not QUIZ_DATA_RE.search(QUIZ_RE.sub("", text)):
        return QUIZ_RE.sub("", text)
    if QUIZ_RE.search(text):
        return QUIZ_RE.sub(lambda _: QUIZ_BLOCK, text, count=1)
    m = re.search(rf"<footer[^>]*\bid=[\"']?{BACKLINK_ID}", text)
    if not m:
        bodies = list(re.finditer(r"</body>", text, re.I))
        m = bodies[-1] if bodies else None
    pos = m.start() if m else len(text)
    return text[:pos] + QUIZ_BLOCK + text[pos:]


def apply_generated(text: str, filename: str) -> str:
    """自動生成ブロック（head・クイズ）をすべて最新にする。"""
    text = apply_head(text, filename)
    return text if filename in SPECIAL_NAMES else apply_quiz(text)


# ---------------------------------------------------------------- lint

STYLE_RE = re.compile(r"(<style\b[^>]*>)(.*?)(</style>)", re.S | re.I)
SCRIPT_RE = re.compile(r"<script\b[^>]*>(.*?)</script>", re.S | re.I)


def _fix_css(css: str) -> tuple[str, list[str]]:
    notes = []
    n = sum(css.count(c) for c in CURLY)
    if n:
        css = css.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
        notes.append(f"CSS 内の全角クォート {n} 個を半角に修正")
    css2, k = re.subn(r"(^|\n)([ \t]*)- \{", r"\1\2* {", css)
    if k:
        css = css2
        notes.append("CSS の `- {`（`* {` の化け）を修正")
    css2, k = re.subn(r"(^|\n)([ \t]*)\\\*", r"\1\2*", css)
    if k:
        css = css2
        notes.append("CSS の `\\*`（エスケープ化け）を修正")
    return css, notes


def lint_text(text: str, backlink: bool, filename: str = "") -> tuple[str, list[str], list[str]]:
    """returns (fixed_text, fixed_notes, problems_remaining)"""
    fixed: list[str] = []
    problems: list[str] = []

    # CSS の化け
    def repl(m):
        css, notes = _fix_css(m.group(2))
        fixed.extend(notes)
        return m.group(1) + css + m.group(3)
    text = STYLE_RE.sub(repl, text)

    # JS 内の全角クォート（文字列内の正当な使用もあり得るので警告のみ）
    for js in SCRIPT_RE.findall(text):
        if re.search(r"[=(,:\[]\s*[‘“]", js):
            problems.append("JS 内で全角クォートが文字列の区切りに使われている疑い（手動確認）")
            break

    low = text.lower()
    if not low.lstrip().startswith("<!doctype"):
        text = "<!DOCTYPE html>\n" + text
        fixed.append("<!DOCTYPE html> を追加")

    def ensure_head(snippet: str, test: str, label: str):
        nonlocal text
        if re.search(test, text, re.I):
            return
        m = re.search(r"<head[^>]*>", text, re.I)
        if m:
            text = text[: m.end()] + "\n" + snippet + text[m.end():]
        else:
            m = re.search(r"<html[^>]*>", text, re.I)
            pos = m.end() if m else text.find("\n") + 1
            text = text[:pos] + "\n" + snippet + text[pos:]
        fixed.append(f"{label} を追加")

    ensure_head('<meta charset="UTF-8">', r"<meta[^>]+charset", "charset")
    ensure_head('<meta name="viewport" content="width=device-width, initial-scale=1.0">',
                r"<meta[^>]+name=[\"']?viewport", "viewport")

    if not re.search(r"<title>\s*\S", text, re.I):
        problems.append("<title> がない（memo.py meta --title で追加）")
    for name, label in (("description", "説明"), ("memo:tags", "タグ"), ("memo:date", "日付")):
        if not re.search(rf"<meta[^>]+name=[\"']?{re.escape(name)}[\"'\s]", text, re.I):
            problems.append(f"{label}（meta {name}）がない（memo.py meta で追加）")

    if backlink and BACKLINK_ID not in text:
        m = list(re.finditer(r"</body>", text, re.I))
        if m:
            i = m[-1].start()
            text = text[:i] + BACKLINK + "\n" + text[i:]
        else:
            text = text.rstrip() + "\n" + BACKLINK + "\n"
        fixed.append("フッターに「一覧に戻る」リンクを追加")
    elif BACKLINK_ID not in text and "index.html" not in text:
        problems.append("一覧（index.html）へのリンクがない（--backlink で追加）")

    if filename:
        new = apply_head(text, filename)
        if new != text:
            fixed.append("アイコン・OGP の head タグを追加／更新")
            text = new
        new = apply_quiz(text)
        if new != text:
            fixed.append("クイズの表示ブロック（memo:quiz）を追加／更新")
            text = new

    _qs, quiz_problems = read_quiz(text)
    problems.extend(f"クイズ: {p}" for p in quiz_problems)

    return text, fixed, problems


def cmd_lint(args) -> int:
    bad = 0
    for f in args.files:
        path = memo_path(f)
        text = path.read_text(encoding="utf-8")
        new, fixed, problems = lint_text(text, args.backlink, path.name)
        print(f"== {path.name}")
        if fixed:
            verb = "修正" if args.fix else "修正可能"
            for n in fixed:
                print(f"  [{verb}] {n}")
        for p in problems:
            print(f"  [要対応] {p}")
        if not fixed and not problems:
            print("  OK")
        if args.fix and new != text:
            path.write_text(new, encoding="utf-8")
        if problems or (fixed and not args.fix):
            bad = 1
    return bad


# ---------------------------------------------------------------- meta

def _set_meta(text: str, name: str, value: str) -> str:
    tag = f'<meta name="{name}" content="{html.escape(value, quote=True)}">'
    pat = re.compile(rf"<meta[^>]+name=[\"']?{re.escape(name)}[\"'\s][^>]*>", re.I)
    if pat.search(text):
        return pat.sub(lambda _: tag, text, count=1)
    m = re.search(r"</head>", text, re.I)
    if m:
        return text[: m.start()] + tag + "\n" + text[m.start():]
    m = re.search(r"<title>.*?</title>", text, re.I | re.S)
    if m:
        return text[: m.end()] + "\n" + tag + text[m.end():]
    m = re.search(r"<html[^>]*>", text, re.I)
    pos = m.end() if m else 0
    return text[:pos] + "\n" + tag + text[pos:]


def cmd_meta(args) -> int:
    path = memo_path(args.file)
    text = path.read_text(encoding="utf-8")
    if args.title is not None:
        t = html.escape(args.title, quote=False)
        if re.search(r"<title>.*?</title>", text, re.I | re.S):
            text = re.sub(r"<title>.*?</title>", lambda _: f"<title>{t}</title>", text,
                          count=1, flags=re.I | re.S)
        else:
            m = re.search(r"<head[^>]*>", text, re.I)
            pos = m.end() if m else 0
            text = text[:pos] + f"\n<title>{t}</title>" + text[pos:]
    if args.desc is not None:
        text = _set_meta(text, "description", args.desc)
    if args.tags is not None:
        tags = ", ".join(t.strip() for t in args.tags.split(",") if t.strip())
        text = _set_meta(text, "memo:tags", tags)
    if args.date is not None:
        date = args.date or dt.date.today().isoformat()
        dt.date.fromisoformat(date)  # 形式チェック
        text = _set_meta(text, "memo:date", date)
    path.write_text(apply_generated(text, path.name), encoding="utf-8")
    print(json.dumps(read_meta(path), ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------- Markdown 版（AI 向け）
#
# build は各メモの本文を Markdown にして docs/md/NAME.md に、全メモの目次を docs/llms.txt に書き出す。
# Claude などが HTML（CSS・SVG 込みで重い）を読まずに中身を把握できるようにするため。
# 変換はファイルを触らない純粋関数（html_to_markdown）にしてあり、他の環境からも使い回せる。

MD_DIR = DOCS / "md"
LLMS_TXT = DOCS / "llms.txt"
MD_NOTE = "<!-- scripts/memo.py build が自動生成。手で編集しない -->"

_MD_SKIP_TAGS = {"head", "style", "script", "noscript", "template"}
_MD_SKIP_IDS = {"memo-quiz-ui", BACKLINK_ID}
_MD_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
            "source", "track", "wbr"}
_MD_BLOCKS = {"p", "div", "section", "article", "main", "header", "footer", "nav", "aside",
              "figure", "figcaption", "blockquote", "dl", "dt", "dd", "details", "summary",
              "ul", "ol", "li", "form", "fieldset", "legend", "caption", "hr", "br", "button"}
_MD_SPACED = {"b", "strong", "small", "span", "label", "em", "i", "code", "kbd", "mark"}
_WS_RE = re.compile(r"\s+")
_MD_LIST_RE = re.compile(r"^(?:\s*(?:- |\d+\. )|\s{2,}\S)")
_MD_SCRIPT_RE = re.compile(
    r"<script\b(?![^>]*\bsrc=)(?![^>]*application/json)[^>]*>(.*?)</script>", re.S | re.I)


class _ToMarkdown(HTMLParser):
    """HTML の本文を Markdown に近いテキストにする（見た目の再現ではなく、読むための抽出）。"""

    def __init__(self, page_url: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url  # 図へのリンクに使う元ページの URL（空ならリンクを付けない）
        self.anchor = ""  # いま読んでいる節の見出しの id
        self.interactive = False  # この節に操作できるパーツ（ボタンなど）があったか
        self.linked = False  # この節で図へのリンクをもう出したか
        self.blocks: list[str] = []
        self.line: list[str] = []
        self.prefix = ""
        self.cont = ""  # li の 2 行目以降に付ける字下げ
        self.skip_tag = ""
        self.skip_depth = 0
        self.lists: list[list] = []  # [種類, 番号]
        self.pre = 0
        self.pre_buf: list[str] = []
        self.links: list[tuple[int, str]] = []
        self.svg = 0
        self.svg_texts: list[str] = []
        self.svg_cur: list[str] | None = None
        self.table: list[list[str]] | None = None
        self.cell: list[str] | None = None
        self.saved_line: list[str] | None = None

    # -- 出力
    def flush(self) -> None:
        if self.cell is not None:  # 表のセルの中では改行せずに空白でつなぐ
            self.line.append(" ")
            return
        text = _WS_RE.sub(" ", "".join(self.line)).replace("****", "").strip()
        self.line = []
        if text:
            self.blocks.append(self.prefix + text)
            if self.cont:
                self.prefix = self.cont

    def emit(self, block: str) -> None:
        self.flush()
        self.blocks.append(block)

    def space(self) -> None:
        if self.line and not self.line[-1].endswith((" ", "\n")):
            self.line.append(" ")

    def here(self) -> str:
        """いまの節を元ページで開く URL。"""
        return self.page_url + (f"#{self.anchor}" if self.anchor else "")

    def close_section(self) -> None:
        """節の終わり。操作できる図解があったのに図のリンクを出していなければ案内を出す。"""
        if self.page_url and self.interactive and not self.linked:
            self.emit(f"（元のページで操作できます → {self.here()}）")
        self.interactive = self.linked = False

    # -- タグ
    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_depth += 1
            return
        if tag in _MD_SKIP_TAGS or a.get("id") in _MD_SKIP_IDS:
            if tag not in _MD_VOID:
                self.skip_tag, self.skip_depth = tag, 1
            return
        if self.svg:
            if tag == "svg":
                self.svg += 1
            elif tag in ("text", "title") and self.svg_cur is None:
                self.svg_cur = []
            return
        if tag in ("button", "select", "textarea") or "onclick" in a or (
                tag == "input" and a.get("type") != "hidden"):
            self.interactive = True
        if tag == "svg":
            self.flush()
            self.svg, self.svg_texts = 1, []
            return
        if self.pre:
            return
        if tag == "pre":
            self.flush()
            self.pre, self.pre_buf = 1, []
        elif re.fullmatch(r"h[1-6]", tag):
            self.close_section()
            if a.get("id"):
                self.anchor = a["id"]
            elif int(tag[1]) <= 2:  # id のない大見出しはページ先頭へのリンクにする
                self.anchor = ""
            self.prefix, self.cont = "#" * int(tag[1]) + " ", ""
        elif tag == "table":
            self.flush()
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.table.append([])
        elif tag in ("td", "th") and self.table is not None:
            self.saved_line, self.line, self.cell = self.line, [], []
        elif tag in ("ul", "ol"):
            self.flush()
            self.lists.append([tag, 0])
        elif tag == "li":
            self.flush()
            depth = max(len(self.lists) - 1, 0)
            kind = self.lists[-1] if self.lists else ["ul", 0]
            kind[1] += 1
            mark = f"{kind[1]}. " if kind[0] == "ol" else "- "
            if self.cell is None:
                self.prefix = "  " * depth + mark
                self.cont = "  " * depth + " " * len(mark)
        elif tag == "img":
            if a.get("alt"):
                self.space()
                self.line.append(f"（画像: {a['alt']}）")
        elif tag == "a":
            self.space()
            self.links.append((len(self.line), a.get("href", "")))
        elif tag in _MD_BLOCKS:
            self.flush()
        elif tag in _MD_SPACED:
            self.space()
            if tag in ("b", "strong") and self.cell is None:
                self.line.append("**")
            elif tag in ("code", "kbd"):
                self.line.append("`")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _MD_VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_depth -= 1
                if not self.skip_depth:
                    self.skip_tag = ""
            return
        if self.svg:
            if tag in ("text", "title") and self.svg_cur is not None:
                t = _WS_RE.sub(" ", "".join(self.svg_cur)).strip()
                if t and t not in self.svg_texts:
                    self.svg_texts.append(t)
                self.svg_cur = None
            elif tag == "svg":
                self.svg -= 1
                if not self.svg and self.svg_texts:
                    link = f" → {self.here()}" if self.page_url else ""
                    self.emit("（図: " + " / ".join(self.svg_texts) + link + "）")
                    self.linked = bool(link)
            return
        if self.pre:
            if tag == "pre":
                self.pre = 0
                code = "".join(self.pre_buf).strip("\n")
                fence = "````" if "```" in code else "```"
                self.emit(f"{fence}\n{code}\n{fence}")
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.flush()
            self.prefix = self.cont = ""
        elif tag in ("td", "th") and self.cell is not None:
            text = _WS_RE.sub(" ", "".join(self.line)).strip().replace("|", "\\|")
            self.line, self.cell = self.saved_line or [], None
            if self.table is not None:
                if not self.table:
                    self.table.append([])
                self.table[-1].append(text)
        elif tag == "table" and self.table is not None:
            rows = [r for r in self.table if any(c for c in r)]
            self.table = None
            if rows:
                n = max(len(r) for r in rows)
                rows = [r + [""] * (n - len(r)) for r in rows]
                md = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * n]
                md += ["| " + " | ".join(r) + " |" for r in rows[1:]]
                self.emit("\n".join(md))
        elif tag in ("ul", "ol"):
            self.flush()
            if self.lists:
                self.lists.pop()
            if self.cell is None:
                self.prefix = self.cont = ""
        elif tag == "li":
            self.flush()
            if self.cell is None:
                self.prefix = self.cont = ""
        elif tag == "a":
            if self.links:
                start, href = self.links.pop()
                text = "".join(self.line[start:]).strip()
                url = _md_link(href)
                if url and text:
                    self.line[start:] = [f"[{text}]({url})"]
            self.space()
        elif tag in _MD_BLOCKS:
            self.flush()
        elif tag in _MD_SPACED:
            if tag in ("b", "strong") and self.cell is None:
                self.line.append("**")
            elif tag in ("code", "kbd"):
                self.line.append("`")
            self.space()

    def handle_data(self, data):
        if self.skip_tag:
            return
        if self.svg:
            if self.svg_cur is not None:
                self.svg_cur.append(data)
            return
        if self.pre:
            self.pre_buf.append(data)
            return
        self.line.append(data)

    def result(self) -> str:
        self.close()
        self.close_section()
        self.flush()
        out = ""
        for i, b in enumerate(self.blocks):  # リストの項目どうしは空行を挟まずにつなぐ
            if i:
                same_list = _MD_LIST_RE.match(b) and _MD_LIST_RE.match(self.blocks[i - 1])
                out += "\n" if same_list else "\n\n"
            out += b
        return out


def _md_link(href: str) -> str:
    """リンク先を Markdown 版から辿れる URL にする。ページ内リンクや一覧へのリンクは捨てる。"""
    if re.match(r"https?://", href):
        return href
    m = re.fullmatch(r"(?:\./)?([a-z0-9-]+)\.html(#[\w-]+)?", href)
    if m and f"{m.group(1)}.html" not in SPECIAL_NAMES:
        return f"{SITE_URL}md/{m.group(1)}.md"  # 別のメモ → その Markdown 版
    return ""


def html_to_markdown(text: str, page_url: str = "") -> str:
    """メモの HTML から本文を Markdown として取り出す（<head>・CSS・JS・クイズ UI は除く）。

    本文の大半を JavaScript のデータから描画するページは、HTML だけでは中身が取れない。
    page_url を渡すと、図や操作できるパーツのある節に、元ページのその節へのリンクを付ける。
    取れた本文がごく短く、ページ内に大きなスクリプトがあるときは、そのスクリプトを
    （データ配列ごと）コードブロックとして末尾に付ける。"""
    text = QUIZ_RE.sub("", HEAD_RE.sub("", text))
    p = _ToMarkdown(page_url)
    p.feed(text)
    body = p.result()
    scripts = [s.strip() for s in _MD_SCRIPT_RE.findall(text) if s.strip()]
    if len(body) < 1000 and sum(map(len, scripts)) > 2000:
        body += "\n\n## ページ内のデータ（JavaScript で描画される部分）\n\n" + "\n\n".join(
            f"```js\n{s}\n```" for s in scripts)
    return body


def memo_markdown(text: str, meta: dict) -> str:
    """1 本のメモの Markdown 版（メタ情報＋本文）。"""
    body = html_to_markdown(text, SITE_URL + meta["file"])
    title = meta["title"]
    # 本文の先頭がページタイトルの h1 なら重複するので落とす
    body = re.sub(rf"\A#\s+{re.escape(title)}\s*(\n+|\Z)", "", body)
    head = [f"# {title}", ""]
    if meta["desc"]:
        head += [f"> {meta['desc']}", ""]
    head.append(f"- URL: {SITE_URL}{meta['file']}")
    if meta["tags"]:
        head.append(f"- タグ: {', '.join(meta['tags'])}")
    if meta["date"]:
        head.append(f"- 日付: {meta['date']}")
    return "\n".join([MD_NOTE, ""] + head + ["", "---", "", body.strip(), ""])


def llms_txt(memos: list[dict]) -> str:
    """全メモの目次（llms.txt の形式）。"""
    lines = [
        f"# {SITE_NAME}",
        "",
        "> Claude に作ってもらった技術解説ページ（図解つき HTML）の集まり。"
        "各リンク先は本文を Markdown にしたもので、元のページへの URL も含む。",
        "",
        "## Memos",
        "",
    ]
    for m in memos:
        name = m["file"][:-5]
        extra = " / ".join(x for x in (", ".join(m["tags"]), m["date"]) if x)
        line = f"- [{m['title']}]({SITE_URL}md/{name}.md)"
        if m["desc"]:
            line += f": {m['desc']}"
        if extra:
            line += f"（{extra}）"
        lines.append(line)
    return "\n".join(lines) + "\n"


def build_markdown(memos: list[dict], check: bool) -> list[str]:
    """docs/md/*.md と docs/llms.txt を書き出し、変わった（check なら古い）ファイル名を返す。"""
    want = {MD_DIR / f"{m['file'][:-5]}.md": memo_markdown(
        (DOCS / m["file"]).read_text(encoding="utf-8"), m) for m in memos}
    want[LLMS_TXT] = llms_txt(memos)
    changed = []
    for path, content in want.items():
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            changed.append(str(path.relative_to(DOCS)))
            if not check:
                path.parent.mkdir(exist_ok=True)
                path.write_text(content, encoding="utf-8")
    for path in sorted(MD_DIR.glob("*.md")) if MD_DIR.is_dir() else []:
        if path not in want:  # 消されたメモの Markdown 版
            changed.append(str(path.relative_to(DOCS)) + "（削除）")
            if not check:
                path.unlink()
    return changed


# ---------------------------------------------------------------- build

def render_block(memos: list[dict], quizzes: list[dict]) -> str:
    body = json.dumps(memos, ensure_ascii=False, indent=2)
    qbody = "[\n" + ",\n".join("  " + json.dumps(q, ensure_ascii=False) for q in quizzes) + "\n]" if quizzes else "[]"
    return (f"{BEGIN}（scripts/memo.py build が自動生成。手で編集しない）\n"
            f"const MEMOS = {body};\nconst QUIZZES = {qbody};\n{END}").replace("</", "<\\/")


def collect_quizzes(memos: list[dict]) -> list[dict]:
    """全メモの問題を集める（形の崩れた問題は飛ばして警告）。"""
    out = []
    for m in memos:
        qs, probs = read_quiz((DOCS / m["file"]).read_text(encoding="utf-8"))
        if probs:
            print(f"{m['file']}: クイズに問題あり（lint で確認）: " + " / ".join(probs), file=sys.stderr)
        if not isinstance(qs, list):
            continue
        for q in qs:
            if validate_quiz([q]):
                continue
            item = {"file": m["file"], "title": m["title"], "q": q["q"],
                    "choices": q["choices"], "answer": q["answer"]}
            for k in ("explain", "ref"):
                if q.get(k):
                    item[k] = q[k]
            out.append(item)
    return out


def cmd_build(args) -> int:
    stale = []
    for p in memo_files():
        text = p.read_text(encoding="utf-8")
        new = apply_generated(text, p.name)
        if new != text:
            stale.append(p.name)
            if not args.check:
                p.write_text(new, encoding="utf-8")
    if stale:
        print(("自動生成ブロックが古い: " if args.check else "自動生成ブロックを更新: ") + ", ".join(stale))
    memos = sorted((read_meta(p) for p in memo_files()),
                   key=lambda m: (m["date"], m["file"]), reverse=True)
    quizzes = collect_quizzes(memos)
    pat = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    outdated = []
    for page in SPECIAL_PAGES:
        if not page.is_file():
            continue
        src = page.read_text(encoding="utf-8")
        if not pat.search(src):
            print(f"docs/{page.name} に {BEGIN} / {END} マーカーがありません", file=sys.stderr)
            return 2
        new = apply_head(pat.sub(lambda _: render_block(memos, quizzes), src, count=1), page.name)
        if new != src:
            outdated.append(page.name)
            if not args.check:
                page.write_text(new, encoding="utf-8")
    md_changed = build_markdown(memos, args.check)
    if args.check:
        if outdated or stale or md_changed:
            names = [f"docs/{n}" for n in outdated + md_changed] or ["docs/index.html"]
            print(", ".join(names) + " が古いです（python3 scripts/memo.py build を実行）")
            return 1
        print("一覧データは最新です")
        return 0
    if md_changed:
        print(f"Markdown 版を更新: {len(md_changed)} ファイル（docs/md/, docs/llms.txt）")
    if outdated:
        print(f"{', '.join(outdated)} を更新（{len(memos)} 件、クイズ {len(quizzes)} 問）")
    elif not md_changed:
        print(f"変更なし（{len(memos)} 件、クイズ {len(quizzes)} 問）")
    return 0


def _strip_fence(text: str) -> str:
    m = re.search(r"```(?:html)?\s*\n(.*?)\n```", text, re.S | re.I)
    return m.group(1) if m and "<" in m.group(1) else text


def cmd_new(args) -> int:
    target = memo_path(args.name, must_exist=False)
    if target.exists():
        sys.exit(f"すでにあります: {target.relative_to(ROOT)}")
    target.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    print(target)
    return 0


def cmd_add(args) -> int:
    src = Path(args.src)
    if not src.is_file():
        sys.exit(f"見つかりません: {src}")
    target = memo_path(args.name, must_exist=False)
    if target.exists() and not args.force:
        sys.exit(f"すでにあります: {target.relative_to(ROOT)}（上書きは --force）")
    if src.resolve() != target.resolve():
        target.write_text(_strip_fence(src.read_text(encoding="utf-8")), encoding="utf-8")
    print(target)
    return 0


def cmd_path(args) -> int:
    print(memo_path(args.name, must_exist=False))
    return 0


def cmd_url(args) -> int:
    name = memo_path(args.name, must_exist=False).name if args.name else ""
    print(SITE_URL + ("" if name in ("", "index.html") else name))
    return 0


def cmd_list(_args) -> int:
    for p in memo_files():
        m = read_meta(p)
        print(f"{m['date'] or '----------'}  {m['file']:<28} {m['title']}  [{', '.join(m['tags'])}]")
    return 0


# ----------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="MEMO リポジトリ用ツール")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="テンプレートから新しいメモを作る")
    p.add_argument("name")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("add", help="外部の HTML を docs/ に取り込む")
    p.add_argument("src")
    p.add_argument("name")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("path", help="メモの絶対パスを表示")
    p.add_argument("name")
    p.set_defaults(func=cmd_path)

    p = sub.add_parser("url", help="公開 URL を表示（docs/CNAME から決まる）")
    p.add_argument("name", nargs="?")
    p.set_defaults(func=cmd_url)

    p = sub.add_parser("lint", help="崩れチェック（--fix で修正）")
    p.add_argument("files", nargs="+")
    p.add_argument("--fix", action="store_true")
    p.add_argument("--backlink", action="store_true", help="フッターに「一覧に戻る」リンクを追加")
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("meta", help="タイトル・説明・タグ・日付を設定")
    p.add_argument("file")
    p.add_argument("--title")
    p.add_argument("--desc")
    p.add_argument("--tags", help="カンマ区切り")
    p.add_argument("--date", nargs="?", const="", help="YYYY-MM-DD（値なしで今日）")
    p.set_defaults(func=cmd_meta)

    p = sub.add_parser("build", help="index.html・quiz.html の一覧データを再生成")
    p.add_argument("--check", action="store_true")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("list", help="メモ一覧を表示")
    p.set_defaults(func=cmd_list)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
