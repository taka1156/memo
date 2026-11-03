"""memolib の関数ごとの単体テスト。

多くの関数は「文字列を受け取って文字列を返す」だけなので、ファイルを使わずに確かめる。
"""
from __future__ import annotations

import datetime as dt
import json
import unittest
from html.parser import HTMLParser

import helpers  # noqa: F401  scripts/ を import できるようにする
from memolib import blocks, config, lint, markdown, meta, site


def page(head: str = "", body: str = "") -> str:
    return f"<!DOCTYPE html>\n<html><head>\n{head}</head>\n<body>\n{body}</body>\n</html>\n"


QUIZ_OK = [{"q": "Q1", "choices": ["a", "b"], "answer": 0},
           {"q": "Q2", "choices": ["a", "b", "c"], "answer": 2, "explain": "e", "ref": "#s"}]


def quiz_script(data) -> str:
    body = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f'<script type="application/json" id="memo-quiz">{body}</script>\n'


class ConfigTest(unittest.TestCase):
    def test_today_uses_configured_timezone(self):
        tz = dt.timezone(dt.timedelta(hours=config.CONFIG["utc_offset_hours"]))
        self.assertEqual(config.today(), dt.datetime.now(tz).date().isoformat())

    def test_site_url_comes_from_cname_or_repository(self):
        cname = config.DOCS / "CNAME"
        if cname.is_file():
            self.assertEqual(config.SITE_URL, f"https://{cname.read_text(encoding='utf-8').strip()}/")
        else:
            self.assertEqual(config.SITE_URL, config.pages_url(config.REPOSITORY))

    def test_pages_url(self):
        self.assertEqual(config.pages_url("Alice/notes"), "https://alice.github.io/notes/")
        self.assertEqual(config.pages_url("alice/alice.github.io"), "https://alice.github.io/")
        self.assertEqual(config.pages_url(""), "")

    def test_load_config_fills_defaults_and_rejects_unknown_keys(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "memo.config.json"
            self.assertEqual(config.load_config(f), config.DEFAULTS)  # ファイルがなくても既定値で動く
            f.write_text('{"site_name": "X"}', encoding="utf-8")
            self.assertEqual(config.load_config(f)["site_name"], "X")
            self.assertEqual(config.load_config(f)["branch"], config.DEFAULTS["branch"])
            f.write_text('{"sitename": "X"}', encoding="utf-8")
            with self.assertRaises(SystemExit):
                config.load_config(f)

    def test_name_rule(self):
        for ok in ("docker", "git-rebase", "a1-b2"):
            self.assertRegex(ok, config.NAME_RE)
        for ng in ("Docker", "a_b", "a--b", "-a", "a-", ""):
            self.assertNotRegex(ng, config.NAME_RE)


class MetaTest(unittest.TestCase):
    def test_parse_meta_ignores_generated_head_block(self):
        text = page('<title>本物</title>\n<meta name="description" content="説明">\n'
                    + blocks.head_block(page("<title>古い</title>"), "x.html"))
        m, title = meta.parse_meta(text)
        self.assertEqual(title, "本物")
        self.assertEqual(m["description"], "説明")

    def test_set_meta_replaces_or_inserts_and_escapes(self):
        text = page('<title>T</title>\n<meta name="memo:tags" content="old">\n')
        text = meta.set_meta(text, "memo:tags", "a, b")
        text = meta.set_meta(text, "description", 'x "y" <z>')
        self.assertEqual(text.count('name="memo:tags"'), 1)
        self.assertIn('<meta name="memo:tags" content="a, b">', text)
        self.assertIn('<meta name="description" content="x &quot;y&quot; &lt;z&gt;">', text)
        self.assertLess(text.index('name="description"'), text.index("</head>"))

    def test_memo_path_resolves_names(self):
        target = config.DOCS / "sample.html"
        for arg in ("sample", "sample.html", "docs/sample.html"):
            self.assertEqual(meta.memo_path(arg, must_exist=False), target)

    def test_memo_path_rejects_reserved_and_bad_names(self):
        for arg in ("index", "quiz.html", "Bad_Name"):
            with self.assertRaises(SystemExit):
                meta.memo_path(arg, must_exist=False)

    def test_memo_files_excludes_special_pages(self):
        names = {p.name for p in meta.memo_files()}  # 仕組みだけのリポジトリでは空でもよい
        self.assertFalse(names & config.SPECIAL_NAMES)


class HeadBlockTest(unittest.TestCase):
    def test_head_block_uses_title_and_description(self):
        b = blocks.head_block(page('<title>A &amp; B</title><meta name="description" content="説明">'), "foo.html")
        self.assertIn('<meta property="og:title" content="A &amp; B">', b)
        self.assertIn('<meta property="og:description" content="説明">', b)
        self.assertIn(f'<meta property="og:url" content="{config.SITE_URL}foo.html">', b)
        self.assertIn('content="article"', b)
        self.assertIn('content="website"', blocks.head_block(page("<title>x</title>"), "index.html"))

    def test_apply_head_is_idempotent_and_single(self):
        text = page("<title>T</title>")
        once = blocks.apply_head(text, "t.html")
        self.assertEqual(blocks.apply_head(once, "t.html"), once)
        self.assertEqual(once.count(config.HEAD_BEGIN), 1)
        self.assertLess(once.index(config.HEAD_BEGIN), once.index("</head>"))


class QuizTest(unittest.TestCase):
    def test_validate_accepts_good_data(self):
        self.assertEqual(blocks.validate_quiz(QUIZ_OK), [])

    def test_validate_reports_each_problem(self):
        bad = [
            {"choices": ["a", "b"], "answer": 0},                      # q がない
            {"q": "Q", "choices": ["a"], "answer": 0},                  # 選択肢が 1 個
            {"q": "Q", "choices": ["a", "b"], "answer": 2},             # 範囲外
            {"q": "Q", "choices": ["a", "b"], "answer": True},          # bool は番号ではない
            {"q": "Q", "choices": ["a", "b"], "answer": 0, "ref": "s"},  # # がない
            "文字列",
        ]
        probs = blocks.validate_quiz(bad)
        for i in range(1, len(bad) + 1):
            self.assertTrue(any(p.startswith(f"Q{i}:") for p in probs), (i, probs))
        self.assertTrue(blocks.validate_quiz([]))

    def test_read_quiz_checks_json_refs_and_answer_spread(self):
        qs, probs = blocks.read_quiz(page(body='<h2 id="s">S</h2>' + quiz_script(QUIZ_OK)))
        self.assertEqual((qs, probs), (QUIZ_OK, []))

        _, probs = blocks.read_quiz(page(body=quiz_script(QUIZ_OK)))  # #s がページにない
        self.assertTrue(any("#s" in p for p in probs))

        _, probs = blocks.read_quiz(page(body=quiz_script("[{broken")))
        self.assertTrue(any("JSON" in p for p in probs))

        same = [{"q": f"Q{i}", "choices": ["a", "b"], "answer": 1} for i in range(3)]
        _, probs = blocks.read_quiz(page(body=quiz_script(same)))
        self.assertTrue(any("answer" in p for p in probs))

        self.assertEqual(blocks.read_quiz(page(body="<p>なし</p>")), (None, []))

    def test_apply_quiz_inserts_before_footer_once_and_removes_when_no_data(self):
        text = page(body="<p>本文</p>\n" + blocks.BACKLINK + "\n" + quiz_script(QUIZ_OK))
        once = blocks.apply_quiz(text)
        self.assertEqual(blocks.apply_quiz(once), once)
        self.assertEqual(once.count(blocks.QUIZ_BEGIN), 1)
        self.assertLess(once.index(blocks.QUIZ_BEGIN), once.index(blocks.BACKLINK_ID))
        self.assertIn(blocks.QUIZ_JS_TAG, once)
        without = once.replace(quiz_script(QUIZ_OK), "")
        self.assertNotIn(blocks.QUIZ_BEGIN, blocks.apply_quiz(without))

    def test_special_pages_get_no_quiz_block(self):
        text = page("<title>T</title>", quiz_script(QUIZ_OK))
        self.assertNotIn(blocks.QUIZ_BEGIN, blocks.apply_generated(text, "index.html"))
        self.assertIn(blocks.QUIZ_BEGIN, blocks.apply_generated(text, "memo.html"))

    def test_quiz_assets_exist(self):
        self.assertTrue(blocks.QUIZ_CSS.is_file())
        self.assertTrue(blocks.QUIZ_JS.is_file())


class LintTest(unittest.TestCase):
    def test_fixes_broken_css(self):
        text = page("<title>T</title><style>\n- { margin: 0 }\n\\* { padding: 0 }\n"
                    "body { font-family: ‘Noto’, “X” }\n</style>")
        fixed, notes, _ = lint.lint_text(text, backlink=False)
        self.assertIn("* { margin: 0 }", fixed)
        self.assertIn("\n* { padding: 0 }", fixed)
        self.assertIn("font-family: 'Noto', \"X\"", fixed)
        self.assertEqual(len([n for n in notes if "CSS" in n]), 3)

    def test_adds_doctype_charset_viewport_and_backlink(self):
        fixed, notes, _ = lint.lint_text("<html><head><title>T</title></head><body></body></html>", backlink=True)
        self.assertTrue(fixed.startswith("<!DOCTYPE html>"))
        self.assertIn('<meta charset="UTF-8">', fixed)
        self.assertIn('name="viewport"', fixed)
        self.assertIn(blocks.BACKLINK_ID, fixed)
        self.assertEqual(lint.lint_text(fixed, backlink=True)[1], [])  # 2 回目は直すものがない

    def test_reports_missing_meta_and_curly_quotes_in_js(self):
        text = page("<title>T</title>", "<script>const a = “x”;</script>")
        _, _, probs = lint.lint_text(text, backlink=False)
        joined = " / ".join(probs)
        for word in ("説明", "タグ", "日付", "全角クォート", "index.html"):
            self.assertIn(word, joined)


class MarkdownTest(unittest.TestCase):
    HTML = page("<title>T</title><style>.a{}</style>", """
<h2 id="s1">見出し</h2>
<p>本文 <b>強調</b> と <code>c</code>。<a href="docker.html#x">別メモ</a> <a href="index.html">一覧</a> <a href="https://e.com">外</a></p>
<ul><li>一</li><li>二</li></ul>
<svg><text>ラベルA</text><text>ラベルB</text></svg>
<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>
<pre>code
  line</pre>
""" + blocks.BACKLINK + quiz_script([{"q": "秘密の問題", "choices": ["a", "b"], "answer": 0}]))

    def test_converts_body(self):
        md = markdown.html_to_markdown(blocks.apply_quiz(self.HTML), "https://ex.com/p.html")
        self.assertIn("## 見出し", md)
        self.assertIn("**強調**", md)
        self.assertIn("`c`", md)
        self.assertIn(f"[別メモ]({config.SITE_URL}md/docker.md)", md)
        self.assertIn("[外](https://e.com)", md)
        self.assertNotIn("](index.html", md)
        self.assertIn("- 一\n- 二", md)
        self.assertIn("（図: ラベルA / ラベルB → https://ex.com/p.html#s1）", md)
        self.assertIn("| A | B |\n| --- | --- |\n| 1 | 2 |", md)
        self.assertIn("```\ncode\n  line\n```", md)
        for hidden in (".a{}", "秘密の問題", "確認クイズ", "一覧に戻る"):
            self.assertNotIn(hidden, md)

    def test_memo_markdown_has_header_and_no_duplicate_title(self):
        m = {"file": "p.html", "title": "見出し", "desc": "説明", "tags": ["a"], "date": "2026-01-01"}
        md = markdown.memo_markdown(page(body="<h1>見出し</h1><p>本文</p>"), m)
        self.assertTrue(md.startswith(markdown.MD_NOTE))
        self.assertEqual(md.count("# 見出し"), 1)
        for line in ("> 説明", f"- URL: {config.SITE_URL}p.html", "- タグ: a", "- 日付: 2026-01-01"):
            self.assertIn(line, md)

    def test_llms_txt_lists_markdown_links(self):
        txt = markdown.llms_txt([{"file": "p.html", "title": "T", "desc": "D", "tags": ["a", "b"], "date": "2026-01-01"}])
        self.assertIn(f"- [T]({config.SITE_URL}md/p.md): D（a, b / 2026-01-01）", txt)


class _TagCounter(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.starts: dict[str, int] = {}

    def handle_starttag(self, tag, attrs):
        self.starts[tag] = self.starts.get(tag, 0) + 1


class SiteTest(unittest.TestCase):
    def test_json_writers(self):
        memos = [{"file": "a.html", "title": "A", "desc": "", "tags": [], "date": "2026-01-01"},
                 {"file": "b.html", "title": "B", "desc": "", "tags": [], "date": "2026-01-01"}]
        quizzes = [{"file": "a.html", "q": "Q"}, {"file": "a.html", "q": "Q2"}]
        rows = json.loads(site.memos_json(memos, quizzes))
        self.assertEqual([r["quizzes"] for r in rows], [2, 0])
        self.assertEqual(json.loads(site.quizzes_json(quizzes)), quizzes)
        self.assertEqual(site.quizzes_json([]), "[]\n")
        self.assertEqual(site.quizzes_json(quizzes).count("\n"), 4, "1 問 1 行")

    def test_strip_fence(self):
        self.assertEqual(site.strip_fence("```html\n<p>x</p>\n```"), "<p>x</p>")
        self.assertEqual(site.strip_fence("<p>x</p>"), "<p>x</p>")
        self.assertEqual(site.strip_fence("```\nnot html\n```"), "```\nnot html\n```")

    def test_preview_inlines_assets_and_escapes_closing_tags(self):
        text = page("<title>T</title>", '<h2 id="s">S</h2>' + quiz_script(QUIZ_OK))
        out = site.preview_text(text, "t.html")
        self.assertNotIn(blocks.QUIZ_CSS_TAG, out)
        self.assertNotIn(blocks.QUIZ_JS_TAG, out)
        # ブラウザと同じく <script> の中身は解釈せずに数える。埋め込んだ JS が途中でタグを閉じていれば数が増える
        counter = _TagCounter()
        counter.feed(out)
        self.assertEqual(counter.starts.get("script"), 2)  # 埋め込んだクイズの JS と問題データ
        self.assertIn(blocks.QUIZ_JS.read_text(encoding="utf-8").strip()[:40], out)

    def test_inline_tag_escapes_its_closing_tag(self):
        self.assertEqual(site._inline_tag("script", "a</script>b"), "<script>\na<\\/script>b\n</script>")

    @unittest.skipUnless(helpers.repo_has_memos(), "本物のメモがない（仕組みだけのリポジトリ）")
    def test_collect_quizzes_from_repository_are_valid(self):
        qs = site.collect_quizzes(site.site_data()[0])
        self.assertTrue(qs)
        self.assertEqual(blocks.validate_quiz(qs and [{k: q[k] for k in ("q", "choices", "answer")} for q in qs]), [])


class SiteFieldsTest(unittest.TestCase):
    def fields(self):
        return blocks.site_fields()

    def test_text_and_attributes_are_filled(self):
        f = self.fields()
        src = ('<title data-memo-site="{site_name} クイズ">古い</title>\n'
               '<meta name="description" content="古い" data-memo-site-content="{description}">\n'
               '<a href="x" data-memo-site="github.com/{repository}" data-memo-site-href="https://github.com/{repository}">古い</a>\n'
               '<p>そのまま</p>')
        out = blocks.apply_site(src)
        self.assertIn(f'>{f["site_name"]} クイズ</title>', out)
        self.assertIn(f'content="{f["description"]}" data-memo-site-content="{{description}}"', out)
        self.assertIn(f'<a href="https://github.com/{f["repository"]}"', out)
        self.assertIn(f'>github.com/{f["repository"]}</a>', out)
        self.assertIn("<p>そのまま</p>", out)
        self.assertEqual(blocks.apply_site(out), out)  # 何度やっても同じ

    def test_missing_attribute_is_added(self):
        out = blocks.apply_site('<a data-memo-site-href="https://github.com/{repository}">x</a>')
        self.assertIn(f'href="https://github.com/{self.fields()["repository"]}"', out)

    def test_values_are_escaped(self):
        orig = dict(blocks.CONFIG)
        try:
            blocks.CONFIG["site_name"] = 'A & "B" <C>'
            out = blocks.apply_site('<h1 data-memo-site="{site_name}">x</h1><meta content="" data-memo-site-content="{site_name}">')
            self.assertIn('>A &amp; "B" &lt;C&gt;</h1>', out)
            self.assertIn('content="A &amp; &quot;B&quot; &lt;C&gt;"', out)
        finally:
            blocks.CONFIG.clear()
            blocks.CONFIG.update(orig)

    def test_unknown_field_is_an_error(self):
        with self.assertRaises(SystemExit):
            blocks.apply_site('<h1 data-memo-site="{nope}">x</h1>')


if __name__ == "__main__":
    unittest.main()
