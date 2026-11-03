"""置き場所・公開 URL・日付など、リポジトリ全体で共有する設定。

置き場所（docs/ やテンプレートの場所）を知っているのはこのモジュールだけ。
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # scripts/memolib/ の 2 つ上
DOCS = ROOT / "docs"  # GitHub Pages の公開元
INDEX = DOCS / "index.html"
QUIZ_PAGE = DOCS / "quiz.html"  # 全メモの問題から 10 問解くページ
# メモではない特別なページ（一覧に載せない・メモ名に使えない）。一覧データは memos.json などから読み込む
SPECIAL_PAGES = (INDEX, QUIZ_PAGE)
SPECIAL_NAMES = {p.name for p in SPECIAL_PAGES}
FALLBACK_URL = "https://taka1156.github.io/memo/"
# 「今日」は日本時間で決める（実行環境の時計が UTC でも日付がずれないように）
JST = dt.timezone(dt.timedelta(hours=9), "JST")


def today_jst() -> str:
    return dt.datetime.now(JST).date().isoformat()


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

ASSETS = DOCS / "assets"
