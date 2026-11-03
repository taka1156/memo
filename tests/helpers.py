"""テスト用の共通処理（標準ライブラリのみ）。

テストは本物のリポジトリを書き換えないよう、docs/・scripts/・テンプレートを一時フォルダに
コピーした「作業用リポジトリ」で memo.py を動かす。memo.py は自分の置き場所からリポジトリの
場所を決めるので、コピーした scripts/memo.py はコピー先の docs/ を対象にする。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
TEMPLATE_REL = Path(".claude/skills/memo-style/template.html")

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class Workspace:
    """一時フォルダに作ったリポジトリのコピー。with 文で使う。"""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="memo-test-")
        self.root = Path(self._tmp.name)
        shutil.copytree(REPO / "docs", self.root / "docs")
        shutil.copytree(SCRIPTS, self.root / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (self.root / TEMPLATE_REL).parent.mkdir(parents=True)
        shutil.copy(REPO / TEMPLATE_REL, self.root / TEMPLATE_REL)
        # memo:date が無いメモは git の履歴から日付を取るので、git リポジトリにしておく
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
        for cmd in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "commit", "-qm", "base"]):
            subprocess.run(cmd, cwd=self.root, check=True, env=env)

    def __enter__(self) -> "Workspace":
        return self

    def __exit__(self, *exc) -> None:
        self._tmp.cleanup()

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """コピー先の memo.py を実行する。"""
        p = subprocess.run(
            [sys.executable, "-B", str(self.root / "scripts" / "memo.py"), *args],
            cwd=self.root, capture_output=True, text=True,
        )
        if check and p.returncode != 0:
            raise AssertionError(f"memo.py {' '.join(args)} が失敗 ({p.returncode}):\n{p.stdout}\n{p.stderr}")
        return p

    def snapshot(self) -> dict[str, bytes]:
        """docs/ 以下の全ファイルの中身（比較用）。"""
        return {str(p.relative_to(self.docs)): p.read_bytes()
                for p in sorted(self.docs.rglob("*")) if p.is_file()}


def repo_snapshot() -> dict[str, bytes]:
    docs = REPO / "docs"
    return {str(p.relative_to(docs)): p.read_bytes()
            for p in sorted(docs.rglob("*")) if p.is_file()}


def diff_names(a: dict[str, bytes], b: dict[str, bytes]) -> list[str]:
    return sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
