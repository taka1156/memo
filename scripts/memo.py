#!/usr/bin/env python3
"""MEMO リポジトリ用ツール（標準ライブラリのみ）

使い方（どのディレクトリから実行してもよい）:
  python3 scripts/memo.py new   NAME                  テンプレートから docs/NAME.html を作る
  python3 scripts/memo.py add   SRC NAME [--force]    外部の HTML を docs/NAME.html として取り込む
  python3 scripts/memo.py path  NAME                  docs/NAME.html の絶対パスを表示
  python3 scripts/memo.py lint  MEMO... [--fix] [--backlink]
  python3 scripts/memo.py meta  MEMO [--title T] [--desc D] [--tags a,b] [--date YYYY-MM-DD]
  python3 scripts/memo.py build [--check]
  python3 scripts/memo.py list

MEMO / NAME は「docker」「docker.html」「docs/docker.html」のどれでもよい
（既存のファイルパスを渡した場合はそのファイルを対象にする）。
置き場所（docs/）やテンプレートの場所はこのスクリプトだけが知っている。

メモ = docs/ 直下の *.html（index.html 以外）。docs/ が GitHub Pages で公開される。
一覧情報は各メモの <head> 内の次のタグから読み取る:
  <title>                         タイトル（memo:title があればそちら優先）
  <meta name="description">       説明
  <meta name="memo:tags">         カンマ区切りのタグ
  <meta name="memo:date">         YYYY-MM-DD
"""
from __future__ import annotations

import argparse
import datetime as dt
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
TEMPLATE = ROOT / ".claude" / "skills" / "memo-style" / "template.html"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BEGIN = "// MEMOS:BEGIN"
END = "// MEMOS:END"
BACKLINK_ID = "memo-backlink"
BACKLINK = (
    f'<a id="{BACKLINK_ID}" href="index.html" '
    'style="position:fixed;right:12px;bottom:12px;z-index:2147483647;'
    "padding:6px 12px;border-radius:999px;background:rgba(20,26,36,.85);color:#fff;"
    "font:600 12px/1.4 ui-monospace,Menlo,monospace;letter-spacing:.08em;"
    'text-decoration:none;box-shadow:0 2px 8px rgba(0,0,0,.3)">&larr; MEMO</a>'
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


def read_meta(path: Path) -> dict:
    p = _Meta()
    p.feed(path.read_text(encoding="utf-8"))
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
    if name == "index":
        sys.exit("index.html はトップページです。メモ名に使えません")
    target = DOCS / f"{name}.html"
    if must_exist and not target.is_file():
        sys.exit(f"見つかりません: {target.relative_to(ROOT)}")
    return target


def memo_files() -> list[Path]:
    return sorted(p for p in DOCS.glob("*.html") if p.name != "index.html")


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


def lint_text(text: str, backlink: bool) -> tuple[str, list[str], list[str]]:
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
        fixed.append("トップへ戻るリンクを追加")
    elif BACKLINK_ID not in text and "index.html" not in text:
        problems.append("トップ（index.html）へのリンクがない（--backlink で追加）")

    return text, fixed, problems


def cmd_lint(args) -> int:
    bad = 0
    for f in args.files:
        path = memo_path(f)
        text = path.read_text(encoding="utf-8")
        new, fixed, problems = lint_text(text, args.backlink)
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
    path.write_text(text, encoding="utf-8")
    print(json.dumps(read_meta(path), ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------- build

def render_block(memos: list[dict]) -> str:
    body = json.dumps(memos, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f"{BEGIN}（scripts/memo.py build が自動生成。手で編集しない）\nconst MEMOS = {body};\n{END}"


def cmd_build(args) -> int:
    memos = sorted((read_meta(p) for p in memo_files()),
                   key=lambda m: (m["date"], m["file"]), reverse=True)
    src = INDEX.read_text(encoding="utf-8")
    pat = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if not pat.search(src):
        print(f"docs/index.html に {BEGIN} / {END} マーカーがありません", file=sys.stderr)
        return 2
    new = pat.sub(lambda _: render_block(memos), src, count=1)
    if args.check:
        if new != src:
            print("docs/index.html が古いです（python3 scripts/memo.py build を実行）")
            return 1
        print("docs/index.html は最新です")
        return 0
    if new != src:
        INDEX.write_text(new, encoding="utf-8")
        print(f"docs/index.html を更新（{len(memos)} 件）")
    else:
        print(f"変更なし（{len(memos)} 件）")
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

    p = sub.add_parser("lint", help="崩れチェック（--fix で修正）")
    p.add_argument("files", nargs="+")
    p.add_argument("--fix", action="store_true")
    p.add_argument("--backlink", action="store_true", help="トップへ戻るリンクを追加")
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("meta", help="タイトル・説明・タグ・日付を設定")
    p.add_argument("file")
    p.add_argument("--title")
    p.add_argument("--desc")
    p.add_argument("--tags", help="カンマ区切り")
    p.add_argument("--date", nargs="?", const="", help="YYYY-MM-DD（値なしで今日）")
    p.set_defaults(func=cmd_meta)

    p = sub.add_parser("build", help="index.html の一覧を再生成")
    p.add_argument("--check", action="store_true")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("list", help="メモ一覧を表示")
    p.set_defaults(func=cmd_list)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
