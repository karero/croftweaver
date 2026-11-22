"""Tests for check_page_links.py: is one new page linked well enough?

Most tests run the script on a real Astro 7.4.13 build of the kit's starter, with pages added for
each case (fixtures/README.md lists them). A few use a tiny hand-written dist/ in a temp folder
where the real build has no page of that shape. Expected values were written by hand from the
fixture list, not copied from the script's output.

Run: python3 -m unittest discover -s skills/internal-link-audit/scripts/tests
"""
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(SKILL, "scripts", "check_page_links.py")
SITE = os.path.join(HERE, "fixtures", "astro-7.4.13_built-site")
DIST = os.path.join(SITE, "built")      # not "dist": the repo ignores folders of that name
HOST = ["--site", "https://example.com"]


def run(*args, cwd=None):
    r = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout, r.stderr


def check(page, *flags, dist=DIST):
    return run(dist, page, *HOST, *flags)


class OnRealBuild(unittest.TestCase):
    def test_t1_page_with_body_links_and_a_link_back_passes(self):
        code, out, _ = check("/hub/spoke-ok", "--hub", "/hub")
        self.assertEqual(code, 0, out)
        self.assertIn("OK: L1, L2 and L3 met", out)

    def test_t2_hub_only_in_json_ld_fails_naming_the_missing_back_link(self):
        code, out, _ = check("/hub/spoke-noback", "--hub", "/hub")
        self.assertEqual(code, 1)
        self.assertIn("MISS: does not link back to its hub /hub from <main>", out)
        # the hub does link to it, and two pages do: only the back-link is missing
        self.assertEqual(out.count("MISS:"), 1)

    def test_t3_footer_and_nav_links_are_not_body_links(self):
        code, out, _ = check("/footer-only", "--no-hub")
        self.assertEqual(code, 1)
        self.assertIn("MISS: no body link", out)
        self.assertEqual(out.count("MISS:"), 1)         # plenty of pages link here: only the body test fails

    def test_t4_one_inbound_page_is_not_enough(self):
        code, out, _ = check("/one-inbound", "--no-hub")
        self.assertEqual(code, 1)
        self.assertIn("MISS: only 1 page links here, 2 needed", out)
        self.assertEqual(out.count("MISS:"), 1)

    def test_t5_four_clicks_from_home_fails_naming_the_depth(self):
        code, out, _ = check("/chain/c4", "--no-hub")
        self.assertEqual(code, 1)
        self.assertIn("MISS: is 4 clicks from the home page, 3 allowed", out)
        self.assertEqual(out.count("MISS:"), 1)

    def test_t5_three_clicks_is_allowed(self):
        _, out, _ = check("/chain/c3", "--no-hub")      # it fails L1 (one inbound page), not L3
        self.assertIn("clicks from home: 3", out)
        self.assertNotIn("clicks from the home page", out)

    def test_t6_hub_that_lists_the_page_only_in_a_nav_fails_naming_the_hub(self):
        code, out, _ = check("/hub-nav/spoke", "--hub", "/hub-nav")
        self.assertEqual(code, 1)
        self.assertIn("MISS: the hub /hub-nav has no body link to this page", out)
        self.assertEqual(out.count("MISS:"), 1)         # /other links it from its body; the back-link exists

    def test_t9_header_inside_main_is_not_a_body_link(self):
        code, out, _ = check("/header-only", "--no-hub")
        self.assertEqual(code, 1)
        self.assertIn("MISS: no body link", out)
        self.assertIn("/other  not body", out)

    def test_t10_plain_div_outside_main_is_not_a_body_link(self):
        code, out, _ = check("/plain-div", "--no-hub")
        self.assertEqual(code, 1)
        self.assertIn("MISS: no body link", out)
        self.assertIn("2 pages link here (2 needed), 0 from their body", out)
        self.assertEqual(out.count("MISS:"), 1)

    def test_t7_address_forms_fold_and_other_hosts_do_not(self):
        code, out, _ = check("/hub/x", "--no-hub")
        self.assertEqual(code, 0, out)
        for counted in ("/fold/s1  body",       # /hub/x/
                        "/fold/s2  body",       # /hub/x?a#b
                        "/fold/s3  body",       # http://WWW.Example.com/hub/x
                        "/hub/y  body"):        # x, page-relative, from the page served at /hub/y
            self.assertIn(counted, out)
        self.assertIn("4 pages link here", out)
        self.assertNotIn("/fold/s5", out)       # https://other.test/hub/x

    def test_t7b_link_inside_hidden_element_is_not_counted(self):
        _, out, _ = check("/hub/x", "--no-hub")
        self.assertNotIn("/fold/sh", out)

    def test_t8_page_without_main_passes_when_it_has_no_hub(self):
        code, out, _ = check("/no-main", "--no-hub")            # T8b
        self.assertEqual(code, 0, out)

    def test_t8_hub_for_a_page_without_main_cannot_be_judged(self):
        code, _, err = check("/no-main", "--hub", "/hub")
        self.assertEqual(code, 2)
        self.assertIn("/no-main has no <main>", err)

    def test_linking_page_without_main_counts_for_the_two_but_not_as_body(self):
        code, out, _ = check("/via-nomain", "--no-hub")
        self.assertEqual(code, 0, out)
        self.assertIn("/no-main  no <main> on that page", out)
        self.assertIn("/other  body", out)
        self.assertIn("2 pages link here (2 needed), 1 from their body", out)

    def test_hub_without_main_has_no_body_link_and_is_named(self):
        code, out, _ = check("/hub-nomain/spoke", "--hub", "/hub-nomain")
        self.assertEqual(code, 1)
        self.assertIn("MISS: the hub /hub-nomain has no <main>, so it has no body link to this page", out)
        self.assertEqual(out.count("MISS:"), 1)

    def test_long_inbound_list_is_cut_after_ten_body_links_first(self):
        _, out, _ = check("/footer-only", "--no-hub")
        self.assertEqual(len(re.findall(r"^  /\S* ", out, re.M)), 10)
        self.assertRegex(out, r"\.\.\. and \d+ more")


class CannotJudge(unittest.TestCase):
    def test_t8_no_dist_folder(self):
        code, _, err = run(os.path.join(SITE, "nope"), "/x", *HOST, "--no-hub")
        self.assertEqual(code, 2)
        self.assertIn("is not a folder", err)

    def test_t8_no_file_for_the_page(self):
        code, _, err = check("/not-built", "--no-hub")
        self.assertEqual(code, 2)
        self.assertIn("no built file for /not-built", err)

    def test_t8_neither_hub_nor_no_hub(self):
        code, _, err = check("/hub/spoke-ok")
        self.assertEqual(code, 2)
        self.assertIn("--no-hub", err)

    def test_no_home_page_cannot_be_judged(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with open(os.path.join(tmp.name, "p.html"), "w") as f:
            f.write("<main>P</main>")
        code, _, err = run(tmp.name, "/p", *HOST, "--no-hub")
        self.assertEqual(code, 2)
        self.assertIn("no built file for the home page", err)

    def test_site_without_a_host_cannot_be_judged(self):
        code, _, err = run(DIST, "/hub", "--site", "example", "--no-hub")
        self.assertEqual(code, 2)
        self.assertIn("has no host", err)

    def test_no_file_for_the_hub(self):
        code, _, err = check("/hub/spoke-ok", "--hub", "/not-built")
        self.assertEqual(code, 2)
        self.assertIn("no built file for the hub /not-built", err)


class OnAHandWrittenDist(unittest.TestCase):
    """Address mapping the Astro starter (build.format 'file') never produces."""

    def make(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for rel, body in files.items():
            path = os.path.join(tmp.name, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
        return tmp.name

    def test_index_html_is_served_at_a_folder_and_resolves_relative_links_there(self):
        # /blog/index.html is served at /blog/, so "post" is /blog/post, not /post.
        dist = self.make({
            "index.html": '<main><a href="/blog/">Blog</a> <a href="/blog/post">Post</a></main>',
            "blog/index.html": '<main><a href="post">Post</a></main>',
            "blog/post.html": "<main>Post</main>",
        })
        code, out, _ = run(dist, "/blog/post", *HOST, "--no-hub")
        self.assertEqual(code, 0, out)
        self.assertIn("/blog  body", out)

    def test_aside_inside_main_is_not_a_body_link(self):
        dist = self.make({
            "index.html": '<main><a href="/a">A</a> <a href="/b">B</a></main>',
            "a.html": '<main><aside><a href="/p">P</a></aside></main>',
            "b.html": '<main><aside><a href="/p">P</a></aside></main>',
            "p.html": "<main>P</main>",
        })
        code, out, _ = run(dist, "/p", *HOST, "--no-hub")
        self.assertEqual(code, 1)
        self.assertIn("MISS: no body link", out)

    def test_footer_inside_main_is_not_a_body_link(self):
        dist = self.make({
            "index.html": '<main><a href="/a">A</a> <a href="/b">B</a></main>',
            "a.html": '<main><footer><a href="/p">P</a></footer></main>',
            "b.html": '<main><footer><a href="/p">P</a></footer></main>',
            "p.html": "<main>P</main>",
        })
        code, out, _ = run(dist, "/p", *HOST, "--no-hub")
        self.assertEqual(code, 1)
        self.assertIn("MISS: no body link", out)

    def test_anchor_with_its_own_hidden_attribute_is_not_counted(self):
        dist = self.make({
            "index.html": '<main><a href="/a">A</a> <a href="/p">P</a></main>',
            "a.html": '<main><a hidden href="/p">P</a></main>',
            "p.html": "<main>P</main>",
        })
        code, out, _ = run(dist, "/p", *HOST, "--no-hub")
        self.assertEqual(code, 1)
        self.assertIn("MISS: only 1 page links here, 2 needed", out)

    def test_page_linked_only_from_pages_home_cannot_reach_is_not_reachable(self):
        dist = self.make({
            "index.html": '<main><a href="/a">A</a></main>',
            "a.html": "<main>A</main>",
            "x.html": '<main><a href="/p">P</a></main>',
            "y.html": '<main><a href="/p">P</a></main>',
            "p.html": "<main>P</main>",
        })
        code, out, _ = run(dist, "/p", *HOST, "--no-hub")
        self.assertEqual(code, 1)
        self.assertIn("MISS: cannot be reached from the home page", out)

    def test_percent_encoded_link_finds_a_file_with_a_non_ascii_name(self):
        dist = self.make({
            "index.html": '<main><a href="/a">A</a> <a href="/caf%C3%A9">Café</a></main>',
            "a.html": '<main><a href="/caf%C3%A9">Café</a></main>',
            "café.html": "<main>Café</main>",
        })
        code, out, _ = run(dist, "/café", *HOST, "--no-hub")
        self.assertEqual(code, 0, out)

    def test_composed_and_decomposed_letters_are_not_taken_for_one_name(self):
        decomposed = "cafe" + chr(0x301)      # e + combining acute: spelled differently from the composed letter
        dist = self.make({
            "index.html": '<main><a href="/a">A</a> <a href="/caf%C3%A9">Caf</a></main>',
            "a.html": '<main><a href="/caf%C3%A9">Caf</a></main>',
            decomposed + ".html": "<main>Caf</main>",
        })
        code, out, err = run(dist, "/" + decomposed, *HOST, "--no-hub")
        self.assertEqual(code, 1, out + err)
        self.assertIn("MISS: only 0 pages link here, 2 needed", out)

    def test_page_with_a_base_href_cannot_be_judged(self):
        dist = self.make({
            "index.html": '<head><base href="/docs/"></head><main><a href="/a">A</a> <a href="/p">P</a></main>',
            "a.html": '<main><a href="/p">P</a></main>',
            "p.html": "<main>P</main>",
        })
        code, out, err = run(dist, "/p", *HOST, "--no-hub")
        self.assertEqual(code, 2, out)
        self.assertIn("/ has a <base> element", err)

    def test_base_tag_with_a_repeated_href_attribute_cannot_be_judged(self):
        dist = self.make({
            "index.html": '<head><base href="/docs/" href></head><main><a href="/a">A</a> <a href="/p">P</a></main>',
            "a.html": '<main><a href="/p">P</a></main>',
            "p.html": "<main>P</main>",
        })
        code, out, err = run(dist, "/p", *HOST, "--no-hub")
        self.assertEqual(code, 2, out)
        self.assertIn("has a <base> element", err)

    def test_any_base_element_cannot_be_judged_whatever_its_attributes(self):
        for tag in ('<base href>', '<base href="">', '<base target="_blank">', '<base HREF="/docs/">'):
            with self.subTest(tag=tag):
                dist = self.make({
                    "index.html": "<head>%s</head><main><a href=\"/a\">A</a> <a href=\"/p\">P</a></main>" % tag,
                    "a.html": '<main><a href="/p">P</a></main>',
                    "p.html": "<main>P</main>",
                })
                code, out, err = run(dist, "/p", *HOST, "--no-hub")
                self.assertEqual(code, 2, out)
                self.assertIn("has a <base> element", err)

    def test_two_files_that_serve_one_address_cannot_be_judged(self):
        dist = self.make({
            "index.html": '<main><a href="/a">A</a> <a href="/p">P</a></main>',
            "a.html": '<main><a href="/p">P</a></main>',
            "p.html": "<main>P</main>",
            "p/index.html": "<main>P again</main>",
        })
        code, out, err = run(dist, "/p", *HOST, "--no-hub")
        self.assertEqual(code, 2, out)
        self.assertIn("two files serve /p", err)

    @unittest.skipIf(os.name == "nt" or os.geteuid() == 0, "needs a folder this user cannot read")
    def test_folder_that_cannot_be_read_cannot_be_judged(self):
        dist = self.make({
            "index.html": '<main><a href="/a">A</a> <a href="/p">P</a></main>',
            "a.html": '<main><a href="/p">P</a></main>',
            "p.html": "<main>P</main>",
            "secret/x.html": "<main>X</main>",
        })
        os.chmod(os.path.join(dist, "secret"), 0)
        self.addCleanup(os.chmod, os.path.join(dist, "secret"), 0o700)
        code, out, err = run(dist, "/p", *HOST, "--no-hub")
        self.assertEqual(code, 2, out)
        self.assertIn("cannot judge", err)

    def test_malformed_link_is_named_on_stderr_and_not_counted(self):
        dist = self.make({
            "index.html": '<main><a href="/a">A</a> <a href="/p">P</a></main>',
            "a.html": '<main><a href="https://[">broken</a> <a href="/p">P</a></main>',
            "p.html": "<main>P</main>",
        })
        code, out, err = run(dist, "/p", *HOST, "--no-hub")
        self.assertEqual(code, 0, out + err)
        self.assertIn("warning: ignored the malformed link 'https://[' on /a", err)

    def test_link_inside_a_template_is_not_counted(self):
        dist = self.make({
            "index.html": '<main><a href="/a">A</a> <a href="/p">P</a></main>',
            "a.html": '<main><template><a href="/p">P</a></template></main>',
            "p.html": "<main>P</main>",
        })
        code, out, _ = run(dist, "/p", *HOST, "--no-hub")
        self.assertEqual(code, 1)
        self.assertIn("MISS: only 1 page links here, 2 needed", out)

    def test_markup_left_open_does_not_hide_the_links_after_it(self):
        # <p> and <li> are never closed, and <header> is closed late: the body link still counts
        dist = self.make({
            "index.html": '<main><a href="/a">A</a> <a href="/b">B</a></main>',
            "a.html": '<main><header><nav><a href="/x">X</a></nav></header><p>One<p>Two <a href="/p">P</a><ul><li>L</ul></main>',
            "b.html": '<main><ul><li><a href="/p">P</a><li>Next</ul></main>',
            "x.html": "<main>X</main>",
            "p.html": "<main>P</main>",
        })
        code, out, _ = run(dist, "/p", *HOST, "--no-hub")
        self.assertEqual(code, 0, out)
        self.assertIn("2 pages link here (2 needed), 2 from their body", out)

    def test_open_li_or_p_left_unclosed_does_not_hide_the_sibling_that_follows(self):
        # HTML ends an <li> or <p> when the next one starts: a `hidden` on the first is not the second's.
        for name, body in (("li", '<ul><li hidden><a href="/x">X</a><li><a href="/p">P</a></ul>'),
                           ("p", '<p hidden><a href="/x">X</a><p><a href="/p">P</a>')):
            with self.subTest(tag=name):
                dist = self.make({
                    "index.html": '<main><a href="/a">A</a> <a href="/p">P</a></main>',
                    "a.html": "<main>%s</main>" % body,
                    "x.html": "<main>X</main>",
                    "p.html": "<main>P</main>",
                })
                code, out, _ = run(dist, "/p", *HOST, "--no-hub")
                self.assertEqual(code, 0, out)
                self.assertIn("2 pages link here (2 needed), 2 from their body", out)

    def test_hidden_li_still_hides_its_own_link(self):
        dist = self.make({
            "index.html": '<main><a href="/a">A</a> <a href="/p">P</a></main>',
            "a.html": '<main><ul><li><a href="/x">X</a><li hidden><a href="/p">P</a></ul></main>',
            "x.html": "<main>X</main>",
            "p.html": "<main>P</main>",
        })
        code, out, _ = run(dist, "/p", *HOST, "--no-hub")
        self.assertEqual(code, 1)
        self.assertIn("MISS: only 1 page links here, 2 needed", out)

    def test_link_with_a_backslash_is_not_counted_and_is_named_on_stderr(self):
        # A browser reads "\\" as "/": the first goes to other.test, the second to /a/b, not to /p.
        for href in ("https://other.test\\@example.com/p", "/a\\p"):
            with self.subTest(href=href):
                dist = self.make({
                    "index.html": '<main><a href="/a">A</a> <a href="/p">P</a></main>',
                    "a.html": '<main><a href="%s">P</a></main>' % href,
                    "p.html": "<main>P</main>",
                })
                code, out, err = run(dist, "/p", *HOST, "--no-hub")
                self.assertEqual(code, 1, out)
                self.assertIn("MISS: only 1 page links here, 2 needed", out)
                self.assertIn("warning: ignored the link %r on /a: a backslash in its address" % href, err)

    def test_page_argument_with_a_closing_slash_names_the_same_page(self):
        dist = self.make({
            "index.html": '<main><a href="/a">A</a> <a href="/b">B</a></main>',
            "a.html": '<main><a href="/b">B</a></main>',
            "b.html": "<main>B</main>",
        })
        code, out, _ = run(dist, "/b/", *HOST, "--no-hub")
        self.assertEqual(code, 0, out)


class ThroughTheCommandInTheSkill(unittest.TestCase):
    """Rule 9: run the command the way the skill's "A new page" section writes it."""

    def documented_command(self):
        with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
        section = text.split("## A new page", 1)[1].split("\n## ", 1)[0]
        block = re.search(r"```bash\n(.*?)```", section, re.S).group(1)
        return " ".join(block.replace("\\\n", " ").split())

    def argv_for(self, hub_branch):
        """The documented command with its placeholders filled in and one hub branch picked."""
        cmd = self.documented_command()
        self.assertIn("(--hub /<hub-path> | --no-hub)", cmd)
        cmd = cmd.replace("(--hub /<hub-path> | --no-hub)", hub_branch)
        for placeholder, value in (("/<page-path>", "/hub/spoke-ok"), ("https://<host>", "https://example.com"),
                                   ("/<hub-path>", "/hub")):
            cmd = cmd.replace(placeholder, value)
        words = shlex.split(cmd)
        # the script's own name is spelled with the variable Claude Code fills in; the folder
        # stands where the command says `dist`
        self.assertEqual(words[:2], ["python3", "$" + "{CLAUDE_SKILL_DIR}/scripts/check_page_links.py"])
        self.assertEqual(words[2], "dist")
        self.assertNotIn("<", cmd)
        return ["built"] + words[3:]

    def test_the_documented_command_with_a_hub_runs_on_a_built_site(self):
        code, out, err = run(*self.argv_for("--hub /hub"), cwd=SITE)
        self.assertEqual(code, 0, out + err)
        self.assertIn("/hub/spoke-ok: hub /hub", out)

    def test_the_documented_command_without_a_hub_runs_on_a_built_site(self):
        code, out, err = run(*self.argv_for("--no-hub"), cwd=SITE)
        self.assertEqual(code, 0, out + err)
        self.assertIn("/hub/spoke-ok: no hub", out)


if __name__ == "__main__":
    unittest.main()
