"""置き場所・公開 URL・日付など、リポジトリ全体で共有する設定。

置き場所（docs/ やテンプレートの場所）を知っているのはこのモジュールだけ。
サイトごとに変わる値（サイト名・リポジトリ・ブランチ・タイムゾーンなど）は
リポジトリ直下の memo.config.json に書き、ここで読み込む。コードやスキルに直接書かない。
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # scripts/memolib/ の 2 つ上
CONFIG_FILE = ROOT / "memo.config.json"
DOCS = ROOT / "docs"  # GitHub Pages の公開元
INDEX = DOCS / "index.html"
QUIZ_PAGE = DOCS / "quiz.html"  # 全メモの問題から 10 問解くページ
# メモではない特別なページ（一覧に載せない・メモ名に使えない）。一覧データは memos.json などから読み込む
SPECIAL_PAGES = (INDEX, QUIZ_PAGE)
SPECIAL_NAMES = {p.name for p in SPECIAL_PAGES}

# memo.config.json の項目と、書かれていないときの値
DEFAULTS: dict = {
    "site_name": "MEMO",          # <title>・OGP・llms.txt の見出しなどに使うサイト名
    "description": "",            # トップページの説明（index.html と OGP）
    "llms_description": "",       # llms.txt の冒頭の説明
    "repository": "",             # GitHub の owner/name。公開 URL の既定値とリンクに使う
    "branch": "main",             # push 先のブランチ（スキルは `memo.py config branch` で読む）
    "utc_offset_hours": 0,        # 「今日」を決めるタイムゾーン（日本なら 9）
}


def load_config(path: Path = CONFIG_FILE) -> dict:
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    unknown = sorted(set(data) - set(DEFAULTS))
    if unknown:
        raise SystemExit(f"{path.name}: 知らない項目があります: {', '.join(unknown)}")
    return {**DEFAULTS, **data}


CONFIG = load_config()
SITE_NAME: str = CONFIG["site_name"]
REPOSITORY: str = CONFIG["repository"]
BRANCH: str = CONFIG["branch"]
# 「今日」は設定のタイムゾーンで決める（実行環境の時計が UTC でも日付がずれないように）
TZ = dt.timezone(dt.timedelta(hours=CONFIG["utc_offset_hours"]))


def today() -> str:
    return dt.datetime.now(TZ).date().isoformat()


def pages_url(repository: str) -> str:
    """GitHub Pages の既定の URL（独自ドメインがないとき）。"""
    if not repository or "/" not in repository:
        return ""
    owner, name = repository.split("/", 1)
    if name.lower() == f"{owner.lower()}.github.io":
        return f"https://{owner.lower()}.github.io/"
    return f"https://{owner.lower()}.github.io/{name}/"


def site_url() -> str:
    """公開 URL（末尾 /）。docs/CNAME があればその独自ドメイン、なければ GitHub Pages の URL。"""
    cname = DOCS / "CNAME"
    if cname.is_file():
        lines = cname.read_text(encoding="utf-8").strip().splitlines()
        if lines and lines[0].strip():
            return f"https://{lines[0].strip()}/"
    return pages_url(REPOSITORY)


SITE_URL = site_url()  # og:url / og:image の絶対 URL に使う


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
# claude.ai のアプリ側に置く入口スキル（build が memo.config.json から生成する）
ENTRY_SKILL = ROOT / "entry-skill" / "SKILL.md"
