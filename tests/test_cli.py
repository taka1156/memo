"""memo.py をコマンドとして外から動かす結合テスト。

中身の作りを変えても（リファクタリングしても）通るように、コマンドの入出力と
生成されるファイルだけを見る。
"""
from __future__ import annotations

import json
import re
import unittest

from helpers import REPO, Workspace, diff_names, repo_snapshot

GENERATED_BLOCKS = (r"<!-- memo:head.*?<!-- /memo:head -->\n?", r"<!-- memo:quiz.*?<!-- /memo:quiz -->\n?")


class BuildTest(unittest.TestCase):
    def test_committed_outputs_are_up_to_date(self):
        """リポジトリにコミットされている生成物が最新であること（build --check）。"""
        with Workspace() as ws:
            p = ws.run("build", "--check", check=False)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_rebuild_from_sources_matches_repository(self):
        """自動生成ブロックと生成物をすべて消してから build すると、リポジトリと同じ中身に戻ること。"""
        with Workspace() as ws:
            for page in ws.docs.glob("*.html"):
                text = page.read_text(encoding="utf-8")
                for pat in GENERATED_BLOCKS:
                    text = re.sub(pat, "", text, flags=re.S)
                page.write_text(text, encoding="utf-8")
            for name in ("memos.json", "quizzes.json", "llms.txt"):
                (ws.docs / name).unlink()
            for md in (ws.docs / "md").glob("*.md"):
                md.unlink()
            ws.run("build")
            self.assertEqual(diff_names(ws.snapshot(), repo_snapshot()), [])

    def test_build_is_idempotent(self):
        with Workspace() as ws:
            ws.run("build")
            before = ws.snapshot()
            p = ws.run("build")
            self.assertIn("変更なし", p.stdout)
            self.assertEqual(diff_names(before, ws.snapshot()), [])

    def test_memos_json_matches_list(self):
        with Workspace() as ws:
            memos = json.loads((ws.docs / "memos.json").read_text(encoding="utf-8"))
            quizzes = json.loads((ws.docs / "quizzes.json").read_text(encoding="utf-8"))
            listed = ws.run("list").stdout.splitlines()
            self.assertEqual(len(memos), len(listed))
            self.assertEqual(sum(m["quizzes"] for m in memos), len(quizzes))
            dates = [m["date"] for m in memos]
            self.assertEqual(dates, sorted(dates, reverse=True), "memos.json は日付の新しい順")
            files = {m["file"] for m in memos}
            self.assertTrue({q["file"] for q in quizzes} <= files)
            self.assertNotIn("index.html", files)
            self.assertNotIn("quiz.html", files)

    def test_removed_memo_disappears_from_outputs(self):
        with Workspace() as ws:
            (ws.docs / "docker.html").unlink()
            ws.run("build")
            self.assertFalse((ws.docs / "md" / "docker.md").exists())
            memos = json.loads((ws.docs / "memos.json").read_text(encoding="utf-8"))
            self.assertNotIn("docker.html", {m["file"] for m in memos})
            self.assertNotIn("docker.html", (ws.docs / "quizzes.json").read_text(encoding="utf-8"))
            self.assertNotIn("md/docker.md", (ws.docs / "llms.txt").read_text(encoding="utf-8"))

    def test_check_reports_stale_without_writing(self):
        with Workspace() as ws:
            (ws.docs / "memos.json").write_text("[]\n", encoding="utf-8")
            before = ws.snapshot()
            p = ws.run("build", "--check", check=False)
            self.assertEqual(p.returncode, 1)
            self.assertIn("memos.json", p.stdout)
            self.assertEqual(diff_names(before, ws.snapshot()), [])


class NewAddMetaTest(unittest.TestCase):
    def test_new_copies_template_and_refuses_existing(self):
        with Workspace() as ws:
            ws.run("new", "zz-sample")
            self.assertEqual((ws.docs / "zz-sample.html").read_text(encoding="utf-8"),
                             (REPO / ".claude/skills/memo-style/template.html").read_text(encoding="utf-8"))
            self.assertNotEqual(ws.run("new", "zz-sample", check=False).returncode, 0)

    def test_invalid_and_reserved_names_are_rejected(self):
        with Workspace() as ws:
            before = ws.snapshot()
            for name in ("Bad_Name", "index", "quiz", "a--b"):
                with self.subTest(name=name):
                    p = ws.run("new", name, check=False)
                    self.assertNotEqual(p.returncode, 0)
            self.assertEqual(diff_names(before, ws.snapshot()), [])  # index.html などを上書きしていない

    def test_add_strips_code_fence_and_needs_force_to_overwrite(self):
        with Workspace() as ws:
            src = ws.root / "pasted.md"
            src.write_text("```html\n<!DOCTYPE html>\n<html><body>x</body></html>\n```\n", encoding="utf-8")
            ws.run("add", str(src), "zz-pasted")
            self.assertEqual((ws.docs / "zz-pasted.html").read_text(encoding="utf-8"),
                             "<!DOCTYPE html>\n<html><body>x</body></html>")
            self.assertNotEqual(ws.run("add", str(src), "zz-pasted", check=False).returncode, 0)
            ws.run("add", str(src), "zz-pasted", "--force")

    def test_meta_sets_fields_escapes_and_normalizes_tags(self):
        with Workspace() as ws:
            ws.run("add", str(ws.docs / "docker.html"), "zz-meta")
            out = json.loads(ws.run("meta", "zz-meta", "--title", "T <x>", "--desc", 'D "q"',
                                    "--tags", " a, b ,,", "--date", "2026-01-02").stdout)
            self.assertEqual(out, {"file": "zz-meta.html", "title": "T <x>", "desc": 'D "q"',
                                   "tags": ["a", "b"], "date": "2026-01-02"})
            text = (ws.docs / "zz-meta.html").read_text(encoding="utf-8")
            self.assertIn("<title>T &lt;x&gt;</title>", text)
            self.assertIn('<meta name="description" content="D &quot;q&quot;">', text)
            self.assertIn('<meta property="og:title" content="T &lt;x&gt;">', text)

    def test_meta_rejects_bad_date(self):
        with Workspace() as ws:
            self.assertNotEqual(ws.run("meta", "docker", "--date", "2026-13-40", check=False).returncode, 0)


class LintTest(unittest.TestCase):
    def test_all_memos_pass_lint(self):
        with Workspace() as ws:
            names = [p.stem for p in ws.docs.glob("*.html") if p.name not in ("index.html", "quiz.html")]
            p = ws.run("lint", *names, check=False)
            self.assertEqual(p.returncode, 0, p.stdout)

    def test_fix_on_broken_draft_then_clean(self):
        with Workspace() as ws:
            draft = ws.root / "draft.html"
            draft.write_text(
                "<html><head><title>T</title>"
                '<meta name="description" content="d"><meta name="memo:tags" content="a">'
                '<meta name="memo:date" content="2026-01-01">'
                "<style>\n- { margin: 0 }\nbody { font-family: “Noto Sans JP” }\n</style></head>"
                '<body><h2 id="s">S</h2>'
                '<script type="application/json" id="memo-quiz">'
                '[{"q":"Q","choices":["a","b"],"answer":1,"ref":"#s"}]</script></body></html>',
                encoding="utf-8")
            p = ws.run("lint", str(draft), "--fix", "--backlink", check=False)
            self.assertIn("[修正]", p.stdout)
            text = draft.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("<!DOCTYPE html>"))
            self.assertIn("* { margin: 0 }", text)
            self.assertIn('"Noto Sans JP"', text)
            for needle in ('<meta charset="UTF-8">', 'name="viewport"', 'id="memo-backlink"',
                           "<!-- memo:head", "<!-- memo:quiz", "assets/memo-quiz.js"):
                self.assertIn(needle, text)
            again = ws.run("lint", str(draft), check=False)
            self.assertEqual(again.returncode, 0, again.stdout)
            self.assertIn("OK", again.stdout)

    def test_lint_reports_quiz_problems(self):
        with Workspace() as ws:
            draft = ws.root / "draft.html"
            draft.write_text(
                '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>T</title></head><body>'
                '<a href="index.html">x</a>'
                '<script type="application/json" id="memo-quiz">'
                '[{"q":"Q","choices":["a","b"],"answer":0,"ref":"#nowhere"}]</script></body></html>',
                encoding="utf-8")
            p = ws.run("lint", str(draft), check=False)
            self.assertEqual(p.returncode, 1)
            self.assertIn("#nowhere", p.stdout)
            self.assertIn("説明", p.stdout)


class PreviewTest(unittest.TestCase):
    def test_memo_preview_inlines_quiz_assets(self):
        with Workspace() as ws:
            src_before = (ws.docs / "docker.html").read_bytes()
            out = ws.root / "out" / "docker.html"
            ws.run("preview", "docker", "-o", str(out))
            text = out.read_text(encoding="utf-8")
            self.assertNotIn("assets/memo-quiz.css", text)
            self.assertNotIn("assets/memo-quiz.js", text)
            self.assertIn("#memo-quiz-ui", text)  # CSS の中身
            self.assertIn("function refLink", text)  # JS の中身
            self.assertEqual((ws.docs / "docker.html").read_bytes(), src_before)

    def test_index_and_quiz_preview_embed_data(self):
        with Workspace() as ws:
            memos = json.loads((ws.docs / "memos.json").read_text(encoding="utf-8"))
            for page in ("index", "quiz"):
                with self.subTest(page=page):
                    out = ws.root / f"{page}.html"
                    ws.run("preview", page, "-o", str(out))
                    text = out.read_text(encoding="utf-8")
                    m = re.search(r"window\.MEMO_DATA = (.*?);\n</script>", text, re.S)
                    self.assertIsNotNone(m)
                    data = json.loads(m.group(1))
                    self.assertEqual(data["memos.json"], memos)
                    self.assertLess(text.index("window.MEMO_DATA"), text.index("loadJSON"))

    def test_preview_refuses_to_overwrite_source(self):
        with Workspace() as ws:
            p = ws.run("preview", "docker", "-o", str(ws.docs / "docker.html"), check=False)
            self.assertNotEqual(p.returncode, 0)


class PathUrlTest(unittest.TestCase):
    def test_path_and_url(self):
        with Workspace() as ws:
            self.assertEqual(ws.run("path", "docker").stdout.strip(), str(ws.docs / "docker.html"))
            self.assertEqual(ws.run("path", "docker", "--md").stdout.strip(), str(ws.docs / "md" / "docker.md"))
            cname = (ws.docs / "CNAME").read_text(encoding="utf-8").strip()
            self.assertEqual(ws.run("url", "docker").stdout.strip(), f"https://{cname}/docker.html")
            self.assertEqual(ws.run("url").stdout.strip(), f"https://{cname}/")


if __name__ == "__main__":
    unittest.main()
