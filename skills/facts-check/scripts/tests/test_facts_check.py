"""facts_check.py: number parsing, tying numbers to facts, and a full run against a
stub site served on 127.0.0.1 (no real network calls).

Run:  python3 -m unittest discover -s skills/facts-check/scripts/tests
"""

import contextlib
import http.client
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import facts_check as fc  # noqa: E402


def first_num(text):
    for kind, m in fc.tokenize(text):
        if kind == "num":
            return fc.parse_number(m)
    return None


def fact(**kw):
    base = {"id": "f", "value": 27000, "terms": ["agent"], "before": []}
    base.update(kw)
    return base


class ParseNumber(unittest.TestCase):
    def test_formats(self):
        cases = {
            "27,000+ agents": 27000, "27.000 Agenten": 27000, "27\u202f000 agents": 27000,
            "27 000 agents": 27000, "27k agents": 27000, "2,5 Mio. Nutzer": 2.5e6,
            "1.5 million users": 1.5e6, "100M revenue": 1e8, "1,234.5 units": 1234.5,
            "1.234,5 Einheiten": 1234.5, "3.14 ratio": 3.14, "72% NPS": 72,
        }
        for text, want in cases.items():
            with self.subTest(text=text):
                got, _ = first_num(text)
                self.assertTrue(fc.same(got, want), "%s -> %s" % (text, got))

    def test_unit_letters_are_not_multipliers(self):
        got, _ = first_num("5 km away")
        self.assertEqual(got, 5)
        got, _ = first_num("100 Mitarbeiter")
        self.assertEqual(got, 100)

    def test_only_a_plain_number_can_be_a_year(self):
        self.assertTrue(first_num("since 2016")[1])
        self.assertFalse(first_num("2,016 agents")[1])
        self.assertFalse(first_num("2016+ agents")[1])

    def test_a_plain_space_does_not_group_thousands(self):
        # review finding: "our 5 120 clients" was read as 5120
        self.assertEqual(first_num("5 120 clients")[0], 5)

    def test_no_match_inside_words_or_codes(self):
        self.assertIsNone(first_num("model X7 and ISO9001"))


class FindMentions(unittest.TestCase):
    def statuses(self, text, f):
        return [(h["status"], h["found_value"]) for h in fc.find_mentions(text, f)]

    def test_term_after_the_number(self):
        f = fact(also_accept=[25000.0], retired=[8500])
        self.assertEqual(self.statuses("27,000+ vetted freelance agents", f), [("OK", 27000)])
        self.assertEqual(self.statuses("over 25.000 Agenten", f), [("OK", 25000)])
        self.assertEqual(self.statuses("8,500 agents", f), [("OUTDATED", 8500)])
        self.assertEqual(self.statuses("30,000 agents", f), [("MISMATCH", 30000)])

    def test_other_numbers_near_the_term_are_not_tied(self):
        # 60 sits after "agents", not before a term: it is a country count.
        f = fact()
        self.assertEqual(self.statuses("27,000 agents in 60 countries", f), [("OK", 27000)])

    def test_window_and_sentence_end_limit_the_search(self):
        f = fact()
        self.assertEqual(self.statuses("27,000 of the very best trained agents", f), [])
        self.assertEqual(self.statuses("We grew 30,000. Our agents are great", f), [])
        self.assertEqual(self.statuses("27,000 of the very best trained agents", fact(window=6)),
                         [("OK", 27000)])

    def test_a_comma_ends_the_search(self):
        # review finding: 60 was tied to clients across the comma
        f = fact(value=120, terms=["client"])
        self.assertEqual(self.statuses("in 60 countries, clients love us", f), [])
        self.assertEqual(self.statuses("Our 5 120 clients", f), [("OK", 120)])

    def test_a_plain_four_digit_count_is_not_taken_for_a_year(self):
        # review finding: "Über 2000 Kunden" was skipped as a year
        f = fact(value=1800, terms=["Kunden"])
        self.assertEqual(self.statuses("Über 2000 Kunden vertrauen uns", f), [("MISMATCH", 2000)])
        self.assertEqual(self.statuses("seit 2010 Kunden", f), [])
        # found on a real site: a date right before the term
        self.assertEqual(self.statuses("launched on 27 March 2026 with these Kunden", f), [])
        self.assertEqual(self.statuses("im Herbst 2025 Kunden", f), [])
        self.assertEqual(self.statuses("\u00a9 2024 Kunden GmbH", f), [])

    def test_years_and_zero_are_ignored_unless_the_fact_is_one(self):
        f = fact(value=120, terms=["client"])
        self.assertEqual(self.statuses("Founded in 2016 clients first", f), [])
        self.assertEqual(self.statuses("0 clients", f), [])
        founded = fact(value=2016, terms=[], before=["founded in"])
        self.assertEqual(self.statuses("Founded in 2016 in Munich", founded), [("OK", 2016)])
        self.assertEqual(self.statuses("founded in 2015", founded), [("MISMATCH", 2015)])

    def test_a_minus_sign_is_part_of_the_number(self):
        # round 2 (Codex): "NPS of -5" read as 5, so it matched an approved 5
        nps = fact(value=5, terms=[], before=["NPS of"])
        self.assertEqual(self.statuses("an NPS of -5", nps), [("MISMATCH", -5)])
        self.assertEqual(self.statuses("an NPS of \u22125", nps), [("MISMATCH", -5)])
        self.assertEqual(self.statuses("an NPS of -5", fact(value=-5, terms=[], before=["NPS of"])), [("OK", -5)])
        self.assertEqual(self.statuses("an NPS of -5", fact(value=5, terms=[], before=["NPS of"], also_accept=[-5])),
                         [("OK", -5)])
        # a hyphen or dash between things is no sign: a range, a date, a product name
        self.assertEqual(self.statuses("an NPS of 5-10, on 2024-10-09 and in COVID-19", nps), [("OK", 5)])
        self.assertEqual(self.statuses("an NPS of 5\u201310", nps), [("OK", 5)])
        self.assertEqual(self.statuses("an NPS of +/-5, or an NPS of \u00b1-5", nps), [("OK", 5), ("OK", 5)])
        # a signed number is not a plain one, so it is never taken for a year
        self.assertFalse(first_num("-2016")[1])

    def test_before_phrase_and_percent_unit(self):
        nps = fact(value=72, terms=[], before=["NPS of"])
        self.assertEqual(self.statuses("an NPS of 72 last year", nps), [("OK", 72)])
        self.assertEqual(self.statuses("an NPS of 68 last year", nps), [("MISMATCH", 68)])
        self.assertEqual(self.statuses("NPS of 72%", nps), [])  # unit "" ignores percentages
        pct = fact(value=30, unit="%", terms=["faster"], before=[])
        self.assertEqual(self.statuses("30% faster replies and 40 faster", pct), [("OK", 30)])

    def test_multiword_term(self):
        f = fact(value=35, terms=["languages spoken"])
        self.assertEqual(self.statuses("35 languages spoken", f), [("OK", 35)])
        self.assertEqual(self.statuses("35 languages", f), [])

    def test_snippet_marks_the_number(self):
        hit = fc.find_mentions("We work with 30,000 agents worldwide.", fact())[0]
        self.assertIn("**30,000**", hit["snippet"])


class CheckPage(unittest.TestCase):
    def test_a_repeated_description_is_one_finding(self):
        html = ('<html><head><meta property="og:description" content="We have 30,000 agents.">'
                '<meta name="twitter:description" content="We have 30,000 agents."></head></html>')
        p = fc.PageText()
        p.feed(html)
        rows = fc.check_page("u", p.locations(), [fact()], [])
        self.assertEqual([r["status"] for r in rows], ["MISMATCH"])


    def locations(self, html, ctype=""):
        p = fc.PageText()
        p.feed(fc.decode(html, ctype) if isinstance(html, bytes) else html)
        return p.locations()

    def test_inline_formatting_does_not_split_numbers_or_words(self):
        # review finding: "<b>27</b>,000" became "27 ,000" and gave MISMATCH 27
        loc = self.locations("<p><b>27</b>,000 clients. Tr<i>u</i>sted.</p>")
        self.assertEqual(loc["page text"], "27,000 clients. Trusted.")
        rows = fc.check_page("u", loc, [fact(value=27000, terms=["client"])],
                             [{"text": "Trusted"}])
        self.assertEqual(sorted(r["status"] for r in rows), ["OK", "RETIRED"])

    def test_a_span_does_not_split_a_number_but_still_separates_a_number_from_its_label(self):
        # round 2 (Codex): "<span>27</span>,000 clients" became "27 ,000 clients" and gave MISMATCH 27
        cases = {
            "<p><span>27</span>,000 clients</p>": "27,000 clients",
            "<p><a href='/x'>27</a>,000 clients</p>": "27,000 clients",
            "<p><span>29</span><span>.99</span> euros</p>": "29.99 euros",
            "<p><span>27,</span><span>000</span> clients</p>": "27,000 clients",
            "<div><span>27.000+</span><span>Agenten</span></div>": "27.000+ Agenten",   # number and label stay apart
            "<p><span>big</span><span>clients</span></p>": "big clients",
            "<p><span>2024</span><span>10</span></p>": "2024 10",                        # two numbers stay two
            "<p><span>Total</span> 27</p><p>,000 more</p>": "Total 27 ,000 more",        # a block ends the number
        }
        for html, want in cases.items():
            with self.subTest(html=html):
                self.assertEqual(self.locations(html)["page text"], want)
        loc = self.locations("<p><span>27</span>,000 clients</p>")
        rows = fc.check_page("u", loc, [fact(value=27000, terms=["client"])], [])
        self.assertEqual([r["status"] for r in rows], ["OK"])
        loc = self.locations("<p><span>1</span><span>,234</span><span>,567</span> clients</p>")
        rows = fc.check_page("u", loc, [fact(value=1234567, terms=["client"])], [])
        self.assertEqual([r["status"] for r in rows], ["OK"])
        # the positioning check reads the same text
        p = fc.PageText()
        p.feed("<p><span>27</span>,000 clients</p>")
        self.assertEqual(p.surfaces()["body"], "27,000 clients")

    def test_structured_data_inside_a_template_or_noscript_is_not_read(self):
        # round 2 (Codex): JSON-LD was collected before the skip check
        ld = '<script type="application/ld+json">{"description": "30,000 agents"}</script>'
        for wrap in ("template", "noscript", "svg"):
            with self.subTest(wrap=wrap):
                self.assertNotIn("structured data", self.locations("<%s>%s</%s><p>ok</p>" % (wrap, ld, wrap)))
        self.assertIn("structured data", self.locations(ld + "<p>ok</p>"))   # outside, it still counts

    def test_a_charset_that_cannot_decode_text_falls_back_to_utf8(self):
        # round 3 (Codex): charset="idna" raised UnicodeError out of decode(), which also reads /llms.txt outside any try
        for ctype in ('text/plain; charset="idna"', "text/plain; charset=idna", "text/plain; charset=base64",
                      "text/plain; charset=no-such-charset"):
            with self.subTest(ctype=ctype):
                self.assertEqual(fc.decode(b"abc \xc3\xa9", ctype), "abc \u00e9")

    def test_a_separator_or_a_sign_in_a_span_of_its_own_still_belongs_to_the_number(self):
        # round 3 (Codex): "<span>27</span>,<span>000</span>" and "NPS of <span>-</span><span>5</span>"
        cases = {
            "<p><span>27</span>,<span>000</span> clients</p>": "27,000 clients",
            "<p><span>27</span><span>,</span><span>000</span> clients</p>": "27,000 clients",
            "<p>NPS of <span>-</span><span>5</span></p>": "NPS of -5",
            "<p>NPS of <span>\u2212</span><span>5</span></p>": "NPS of \u22125",
            "<p>5<span>-</span><span>10</span> clients</p>": "5 - 10 clients",          # a dash between things, no sign
            "<p><span>5</span><span>-10</span> clients</p>": "5-10 clients",           # round 4 (Codex): a range, not minus ten
            "<p><span>1,234</span><span>-10</span> clients</p>": "1,234-10 clients",
            "<p><span>Q2</span><span>-5</span> clients</p>": "Q2 -5 clients",          # round 5 (Codex): digits inside a word end no range
            "<p><span>Q2</span><span>,000</span> clients</p>": "Q2 ,000 clients",      # round 6 (GLM): nor a number with a separator
            "<p><span>X1</span><span>.5</span> clients</p>": "X1 .5 clients",
            "<p><span>1,234</span><span>,567</span> clients</p>": "1,234,567 clients",
            "<p><span>1</span><span>,234</span><span>,567</span> clients</p>": "1,234,567 clients",   # round 7 (Codex)
            "<p><span>27</span><span>,000</span><span>.50</span> clients</p>": "27,000.50 clients",
            "<p><span>1</span><span>,</span><span>234</span><span>,</span><span>567</span> clients</p>": "1,234,567 clients",
            "<p>Total<span>-</span><span>5</span></p>": "Total - 5",
        }
        for html, want in cases.items():
            with self.subTest(html=html):
                self.assertEqual(self.locations(html)["page text"], want)
        loc = self.locations("<p>NPS of <span>-</span><span>5</span></p>")
        rows = fc.check_page("u", loc, [fact(value=5, terms=[], before=["NPS of"])], [])
        self.assertEqual([(r["status"], r["found_value"]) for r in rows], [("MISMATCH", -5)])

    def test_resolving_soft_spaces_takes_linear_time(self):
        # round 4 (Codex): sign() copied the whole text before each match: 120,000 of them took 6 seconds.
        # 200,000 matches take about 0.2 s as written; the old code needed over 10 s
        import time
        unit = "NPS of %s-%s%s5%s " % ((fc.SOFT,) * 4)
        text = unit * 200000
        started = time.monotonic()
        out = fc.resolve_soft(text)
        self.assertLess(time.monotonic() - started, 3.0)
        self.assertEqual(out[:12], "NPS of  -5  ")
        self.assertNotIn(fc.SOFT, out)
        # round 8 (GLM): the rule that joins a split number (1, ,234, ,567) is timed too
        text = ("1%s,%s234%s,%s567 " % ((fc.SOFT,) * 4)) * 200000
        started = time.monotonic()
        out = fc.resolve_soft(text)
        self.assertLess(time.monotonic() - started, 3.0)
        self.assertEqual(out[:20], "1,234,567 1,234,567 ")
        self.assertNotIn(fc.SOFT, out)

    def test_numbers_in_structured_data_carry_their_property_name(self):
        # review finding: numeric JSON-LD values were dropped
        loc = self.locations('<script type="application/ld+json">{"@type": "Organization", '
                             '"numberOfEmployees": {"@type": "QuantitativeValue", "value": 30000}}'
                             '</script>')
        self.assertIn("30,000 number of employees", loc["structured data"])
        rows = fc.check_page("u", loc, [fact(value=27000, terms=["employee"])], [])
        self.assertEqual([(r["status"], r["found_value"]) for r in rows], [("MISMATCH", 30000)])

    def test_meta_charset_is_used_when_the_header_names_none(self):
        # review finding: a Latin-1 page was read as UTF-8
        html = '<html><head><meta charset="iso-8859-1"></head><p>27\xa0000 Agenten, Müller GmbH</p>'
        loc = self.locations(html.encode("iso-8859-1"), "text/html")
        self.assertIn("Müller GmbH", loc["page text"])
        rows = fc.check_page("u", loc, [fact(terms=["Agenten"])], [])
        self.assertEqual([r["status"] for r in rows], ["OK"])


class Positioning(unittest.TestCase):
    def surfaces(self, html):
        p = fc.PageText()
        p.feed(html)
        return p.surfaces()

    PAGE = ('<html><head><title>CX outsourcing | Acme</title>'
            '<meta name="description" content="Flexible CX outsourcing for retailers.">'
            '<meta property="og:description" content="Something else"></head><body>'
            '<header><p>Skip to content</p></header><main><h1>Help when <em>you</em> need it</h1>'
            '<p>On-demand <b>CX outsourcing</b> for retail.</p><p>Second paragraph.</p></main>'
            '<footer>Careers at Acme</footer></body></html>')

    def test_surfaces_as_the_starter_test_reads_them(self):
        s = self.surfaces(self.PAGE)
        self.assertEqual(s["title"], "CX outsourcing | Acme")
        self.assertEqual(s["desc"], "Flexible CX outsourcing for retailers.")
        # all h1s, then the intro: the first <p> of <main>, not the header's
        self.assertEqual(s["h1"], "Help when you need it \u00b7 On-demand CX outsourcing for retail.")
        self.assertIn("Careers at Acme", s["body"])

    def test_intro_falls_back_to_article_then_page(self):
        self.assertTrue(self.surfaces("<article><p>A</p></article><p>B</p>")["h1"].endswith("A"))
        self.assertTrue(self.surfaces("<div><p>B<div>x</div></div>")["h1"].endswith("B"))
        # a <main> without a <p> gives no intro, as in the starter test
        self.assertEqual(self.surfaces("<p>B</p><main><h1>H</h1></main>")["h1"], "H \u00b7 ")

    def test_a_paragraph_ends_where_the_browser_ends_it(self):
        # review findings: the intro ran on past a </div> or a new <li> that closes the <p>
        self.assertEqual(self.surfaces("<main><div><p>Short intro</div><a>term</a></main>")["h1"],
                         " \u00b7 Short intro")
        self.assertEqual(self.surfaces("<main><ul><li><p>first<li>term</ul></main>")["h1"], " \u00b7 first")
        self.assertEqual(self.surfaces("<main><p>one<pre>term</pre></main>")["h1"], " \u00b7 one")
        # inline markup inside the paragraph stays part of it
        self.assertEqual(self.surfaces("<main><p>a <a>b</a> <span>c</span></p></main>")["h1"],
                         " \u00b7 a b c")

    def test_only_the_first_main_counts(self):
        # review finding: a later <main> supplied the intro the starter test would not see
        html = "<main><h1>H</h1></main><dialog><main><p>term</p></main></dialog>"
        self.assertEqual(self.surfaces(html)["h1"], "H \u00b7 ")

    def test_title_is_the_first_title_and_keeps_no_break_spaces(self):
        # review finding: every <title> was joined and no-break spaces collapsed
        s = self.surfaces("<head><title>\n  Acme\u00a0Pro  </title></head><body><title>term</title></body>")
        self.assertEqual(s["title"], "Acme\u00a0Pro")
        self.assertEqual(fc.check_positioning(s, {"title": ["Acme Pro"]}),
                         ["<title> needs \u201cAcme Pro\u201d"])

    def test_term_rule_needs_title_description_and_h1_or_intro(self):
        s = self.surfaces(self.PAGE)
        self.assertEqual(fc.check_positioning(s, {"term": "cx outsourcing"}), [])
        missing = fc.check_positioning(s, {"term": "contact center"})
        self.assertEqual([m.split(" needs")[0] for m in missing],
                         ["<title>", "<meta description>", "<h1>/intro"])

    def test_surface_rules_alternatives_and_body(self):
        s = self.surfaces(self.PAGE)
        rule = {"title": [["contact center", "CX outsourcing"]], "body": ["careers"], "desc": ["retail"]}
        self.assertEqual(fc.check_positioning(s, rule), [])
        self.assertEqual(fc.check_positioning(s, {"h1": [["call center", "BPO"]]}),
                         ["<h1>/intro needs one of [call center | BPO]"])

    def test_paths_and_first_matching_rule(self):
        for u, want in (("https://x.com/en/about/", "/en/about"), ("https://x.com/en/about.html", "/en/about"),
                        ("https://x.com/en/about/index.html", "/en/about"), ("https://x.com/", "/"),
                        ("https://x.com/index.html", "/"), ("https://x.com/%C3%BCber", "/\u00fcber")):
            self.assertEqual(fc.norm_path(u), want, u)
        rules = [{"pages": "/en/business/pricing", "term": "a"}, {"pages": "/en/business/*", "term": "b"},
                 {"pages": ["/", "/en"], "term": "c"}]
        self.assertEqual(fc.find_rule("/en/business/pricing", rules)["term"], "a")
        self.assertEqual(fc.find_rule("/en/business/telco/retail", rules)["term"], "b")
        self.assertEqual(fc.find_rule("/en", rules)["term"], "c")
        self.assertIsNone(fc.find_rule("/en/business", rules))  # "/*" needs something after it


class MorePlaces(unittest.TestCase):
    PAGE = ('<html><head><title>Acme</title>'
            '<meta property="og:title" content="Old Name GmbH: 30,000 agents">'
            '<meta property="og:url" content="https://oldname.example/en/">'
            '<link rel="canonical" href="https://oldname.example/en/"></head><body>'
            '<img src="team.jpg" alt="Our 30,000 agents at the Old Name GmbH summit">'
            '<a href="/blog/2024/30000-agents">read more</a>'
            '<template><p>Old Name GmbH</p></template><main><p>Intro text.</p></main></body></html>')

    def rows(self, fact_list, phrases):
        p = fc.PageText()
        p.feed(self.PAGE)
        return p, fc.check_page("u", p.locations(), fact_list, phrases)

    def test_retired_phrases_in_alt_text_share_tags_and_addresses(self):
        # the gap found in the eval run: these places were never searched
        _, rows = self.rows([], [{"text": "Old Name GmbH"}, {"text": "oldname.example"}])
        where = sorted((r["phrase"], r["where"]) for r in rows)
        self.assertEqual(where, [("Old Name GmbH", "image alt text"), ("Old Name GmbH", "share title"),
                                 ("oldname.example", "link addresses")])

    def test_facts_in_alt_text_and_share_title_but_not_in_addresses(self):
        _, rows = self.rows([fact()], [])
        self.assertEqual(sorted(r["where"] for r in rows), ["image alt text", "share title"])

    def test_template_and_noscript_content_is_not_page_structure(self):
        # outside review finding: a <p> inside <template> took the intro's place
        p, _ = self.rows([], [])
        self.assertEqual(p.surfaces()["h1"], " \u00b7 Intro text.")
        q = fc.PageText()
        q.feed("<noscript><p>Enable JS</p><img alt='Old Name GmbH'></noscript><p>Real intro</p>")
        self.assertTrue(q.surfaces()["h1"].endswith("Real intro"))
        self.assertNotIn("image alt text", q.locations())


class RobotsMatcher(unittest.TestCase):
    """robots.txt as RFC 9309 reads it, in this script's own matcher, so that the result does not depend on the Python that
    runs it (round 13: the standard parser of 3.9, the stock python3 of macOS, takes the first matching rule, ignores * and $,
    decodes %2F, ignores a second group for the same agent and loses a group that starts with a BOM)."""

    URL = "https://x.com"

    def allowed(self, robots, path):
        rules = fc.RobotsRules()
        rules.parse(robots)
        return rules.allowed(self.URL + path)

    def test_the_path_matching_table_of_googles_documentation(self):
        # developers.google.com/search/docs/crawling-indexing/robots/robots_txt, "URL matching based on path values"
        # (read 9 October 2026): rule -> (paths it matches, paths it does not)
        table = {
            "/": (["/", "/any", "/any/lower/level?q=1"], []),
            "/*": (["/", "/any"], []),
            "/$": (["/"], ["/any", "/?q=1"]),
            "/fish": (["/fish", "/fish.html", "/fish/salmon.html", "/fishheads", "/fishheads/yummy.html", "/fish.php?id=anything"],
                      ["/Fish.asp", "/catfish", "/?id=fish", "/desert/fish"]),
            "/fish*": (["/fish", "/fish.html", "/fish/salmon.html", "/fishheads", "/fishheads/yummy.html", "/fish.php?id=anything"],
                       ["/Fish.asp", "/catfish", "/?id=fish", "/desert/fish"]),
            "/fish/": (["/fish/", "/fish/?id=anything", "/fish/salmon.htm"], ["/fish", "/fish.html", "/animals/fish/", "/Fish/Salmon.asp"]),
            "/*.php": (["/index.php", "/filename.php", "/folder/filename.php", "/folder/filename.php?parameters",
                        "/folder/any.php.file.html", "/filename.php/"], ["/", "/windows.PHP"]),
            "/*.php$": (["/filename.php", "/folder/filename.php"], ["/filename.php?parameters", "/filename.php/", "/filename.php5", "/windows.PHP"]),
            "/fish*.php": (["/fish.php", "/fishheads/catfish.php?parameters"], ["/Fish.PHP"]),
            # RFC 9309, 5.2: the longer rule is the one that counts
            "/example/page/disallowed.gif": (["/example/page/disallowed.gif"], ["/example/page/", "/example/page/other.gif"]),
        }
        for pattern, (hit, miss) in table.items():
            robots = "User-agent: *\nDisallow: %s\n" % pattern
            for path in hit:
                with self.subTest(pattern=pattern, hit=path):
                    self.assertFalse(self.allowed(robots, path))
            for path in miss:
                with self.subTest(pattern=pattern, miss=path):
                    self.assertTrue(self.allowed(robots, path))

    def test_a_rule_that_ends_in_dollar_needs_its_last_piece_after_the_others(self):
        # "/a*ab$" asks for "/a", anything, then "ab" at the end: "/ab" has only the one "a" for both
        robots = "User-agent: *\nDisallow: /a*ab$\n"
        for path, want in (("/ab", True), ("/aab", False), ("/axab", False), ("/aab/", True), ("/aabx", True)):
            with self.subTest(path=path):
                self.assertEqual(self.allowed(robots, path), want)

    def test_the_longest_matching_rule_wins_and_allow_wins_a_tie(self):
        # RFC 9309, 2.2.2. The first six are the table "Order of precedence for rules" of Google's documentation (read
        # 9 October 2026): the rule path's length counts, as written. "/*.ph" is as long as "/page", so the Allow wins (it
        # would not if what a rule matched were measured: "/page.ph" is longer than "/page")
        cases = [("Allow: /p\nDisallow: /", "/page", True), ("Allow: /folder\nDisallow: /folder", "/folder/page", True),
                 ("Allow: /page\nDisallow: /*.htm", "/page.htm", False), ("Allow: /page\nDisallow: /*.ph", "/page.php5", True),
                 ("Allow: /$\nDisallow: /", "/", True), ("Allow: /$\nDisallow: /", "/page.htm", False),
                 ("Disallow: /folder\nAllow: /folder", "/folder/page", True),
                 ("Allow: /public/\nDisallow: /public/secret", "/public/secret", False),
                 ("Disallow: /public/secret\nAllow: /public/", "/public/secret", False),
                 ("Allow: /public/\nDisallow: /public/secret", "/public/open", True),
                 # a real file (the New York Times, October 2026): an Allow for a folder beats a wildcard Disallow that matches more
                 ("Disallow: /athletic/*/discuss/*\nAllow: /athletic/live-blogs/discuss/", "/athletic/live-blogs/discuss/x", True)]
        for rules, path, want in cases:
            with self.subTest(rules=rules, path=path):
                self.assertEqual(self.allowed("User-agent: *\n" + rules + "\n", path), want)

    def test_groups(self):
        # RFC 9309, 2.2.1: the group of the product token, else the group of "*"; groups of one agent are combined
        robots = ("User-agent: *\nDisallow: /everyone\n\nUser-agent: facts-check\nDisallow: /mine\n\n"
                  "User-agent: other\nUser-agent: Facts-Check\nDisallow: /both\n")
        self.assertFalse(self.allowed(robots, "/mine"))
        self.assertFalse(self.allowed(robots, "/both"))          # the agent lines are case-insensitive
        self.assertTrue(self.allowed(robots, "/everyone"))        # the "*" group does not apply: ours exists
        # other lines belong to no group and end none (Google's documentation: "a" and "b" share the one group)
        self.assertFalse(self.allowed("User-agent: facts-check\nSitemap: https://x.com/s.xml\nUser-agent: other\nDisallow: /\n", "/x"))
        # the name at the start of the value counts, so a pasted "facts-check/1.0" names this tool, "facts-check-bot" does not
        self.assertFalse(self.allowed("User-agent: facts-check/1.0\nDisallow: /\n\nUser-agent: *\nDisallow:\n", "/x"))
        self.assertTrue(self.allowed("User-agent: facts-check-bot\nDisallow: /\n", "/x"))
        two_stars = "User-agent: *\nDisallow: /a\n\nUser-agent: *\nDisallow: /b\n"
        self.assertFalse(self.allowed(two_stars, "/a"))
        self.assertFalse(self.allowed(two_stars, "/b"))           # round 13: Python 3.9's parser reads the first group only
        self.assertTrue(self.allowed("User-agent: other\nDisallow: /\n", "/x"))   # no group for us and none for "*": allowed
        self.assertTrue(self.allowed("Disallow: /\n", "/x"))     # a rule before any User-agent line belongs to no group
        self.assertTrue(self.allowed("User-agent: *\nDisallow:\n", "/x"))         # an empty Disallow allows everything
        # round 13 (GLM): an empty Allow says nothing, whatever stands next to it
        self.assertFalse(self.allowed("User-agent: *\nAllow:\nDisallow: /\n", "/x"))
        self.assertFalse(self.allowed("User-agent: *\nDisallow: /\nAllow:\n", "/x"))
        # a group that names the tool shuts out the "*" group even when its own rules are empty
        self.assertTrue(self.allowed("User-agent: facts-check\nDisallow:\n\nUser-agent: *\nDisallow: /\n", "/x"))

    def test_the_file_as_the_lines_it_has(self):
        for sep in ("\n", "\r\n", "\r"):
            with self.subTest(sep=repr(sep)):
                robots = sep.join(["# a comment", "USER-AGENT : *   # all", "disallow:/private/", "Sitemap: https://x.com/s.xml", "Crawl-delay: 5", ""])
                self.assertFalse(self.allowed(robots, "/private/x"))
                self.assertTrue(self.allowed(robots, "/open"))
        # round 12 (GLM): a BOM before the first line must not lose its group; round 13 (GLM): nor one after blank lines
        # or white space, nor one at the head of a later line (two files with a BOM each, put together)
        for head in ("\ufeff", "\ufeff\ufeff", "\n\n\ufeff", "  \ufeff", "\ufeff \t"):
            with self.subTest(head=head):
                self.assertFalse(self.allowed(head + "User-agent: *\nDisallow: /private/\n", "/private/x"))
        self.assertFalse(self.allowed("User-agent: other\nDisallow: /x\n\ufeffUser-agent: *\nDisallow: /private/\n", "/private/x"))

    def test_percent_escapes_as_the_rfc_has_them(self):
        # unreserved characters are the same encoded or not; a reserved one (%2F) is not the character it encodes
        robots = ("User-agent: *\nDisallow: /~user\nDisallow: /a%20b\nAllow: /public/\nDisallow: /public%2Fsecret\n"
                  "Disallow: /caf%C3%A9\nDisallow: /x-y\nDisallow: /p%61th\n")
        for path, want in (("/%7Euser/page", False), ("/~user/page", False), ("/a%20b", False), ("/a b", False),
                           ("/public/secret", True), ("/public%2Fsecret", False), ("/public%2fsecret", False),
                           ("/caf\u00e9", False), ("/caf%c3%a9", False), ("/cafe", True),
                           ("/x%2Dy", False), ("/x%2dy", False), ("/path", False), ("/p%61th", False), ("/pAth", True)):
            with self.subTest(path=path):
                self.assertEqual(self.allowed(robots, path), want)
        # RFC 9309, Figure 4 (rows 3 to 5): a raw UTF-8 rule and its escaped form are one rule, and so are "baz" and "%62%61%7A"
        for rule in ("/foo/bar/\u30c4", "/foo/bar/%E3%83%84", "/foo/bar/%e3%83%84"):
            for path in ("/foo/bar/%E3%83%84", "/foo/bar/\u30c4", "/foo/bar/%e3%83%84"):
                with self.subTest(rule=rule, path=path):
                    self.assertFalse(self.allowed("User-agent: *\nDisallow: %s\n" % rule, path))
        for path in ("/foo/bar/baz", "/foo/bar/%62%61%7A"):
            with self.subTest(path=path):
                self.assertFalse(self.allowed("User-agent: *\nDisallow: /foo/bar/%62%61%7A\n", path))
        # round 10 (Codex): "Disallow: /a" and "Allow: /a%2Fb" - the Allow rule names an encoded slash, which "/a/b" is not
        self.assertFalse(self.allowed("User-agent: *\nDisallow: /a\nAllow: /a%2Fb\n", "/a/b"))
        self.assertTrue(self.allowed("User-agent: *\nDisallow: /a\nAllow: /a%2Fb\n", "/a%2Fb"))

    def test_the_robots_txt_file_itself_is_always_allowed(self):
        # RFC 9309, 2.2.2
        self.assertTrue(self.allowed("User-agent: *\nDisallow: /\n", "/robots.txt"))
        self.assertFalse(self.allowed("User-agent: *\nDisallow: /\n", "/robots.txt/x"))
        self.assertFalse(self.allowed("User-agent: *\nDisallow: /\n", "/robots.txtx"))

    def test_the_path_that_is_requested(self):
        # round 10 (Codex): "http://x.test?private" is requested as "/?private"
        rules = fc.RobotsRules()
        rules.parse("User-agent: *\nDisallow: /?private\n")
        self.assertFalse(rules.allowed("http://x.test?private"))
        self.assertTrue(rules.allowed("http://x.test?public"))
        self.assertTrue(rules.allowed("http://x.test/"))

    def test_an_empty_query_is_part_of_the_path_that_is_requested(self):
        # round 14 (Codex, older code): urllib sends "GET /a?" for "http://x.test/a?" and "GET /?" for "http://x.test?"
        rules = fc.RobotsRules()
        rules.parse("User-agent: *\nDisallow: /a?\nDisallow: /?\n")
        for url, want in (("http://x.test/a?", False), ("http://x.test/a?x=1", False), ("http://x.test/a", True), ("http://x.test/a?#frag", False),
                          ("http://x.test?", False), ("http://x.test/", True), ("http://x.test/b", True)):
            with self.subTest(url=url):
                self.assertEqual(rules.allowed(url), want)

    def test_a_path_with_leading_slashes_is_judged_as_it_is_requested(self):
        # round 15 (Codex, GLM-checked by hand): urlunsplit() wrote "http://x.test//a?" as "////a?", urllib sends "GET //a?"
        rules = fc.RobotsRules()
        rules.parse("User-agent: *\nDisallow: //a\n")
        for url, want in (("http://x.test//a?", False), ("http://x.test//a", False), ("http://x.test//a/b", False),
                          ("http://x.test/a", True), ("http://x.test///a", True), ("http://x.test/", True)):
            with self.subTest(url=url):
                self.assertEqual(rules.allowed(url), want)

    def test_a_rule_is_measured_after_its_escapes_are_normalised(self):
        # round 14 (Codex, GLM): "/p%61th" is the rule "/path", five characters and not seven; with the "$" the other rule has six
        self.assertFalse(self.allowed("User-agent: *\nAllow: /p%61th\nDisallow: /path$\n", "/path"))
        self.assertTrue(self.allowed("User-agent: *\nAllow: /path\nDisallow: /p%61th\n", "/path"))

    def test_every_spelling_of_the_robots_txt_address_is_allowed(self):
        # round 14 (GLM): "/robots%2Etxt" is the same address once an escape of an unreserved character is read as the character
        for path in ("/robots.txt", "/robots%2Etxt", "/robots.tx%74"):
            with self.subTest(path=path):
                self.assertTrue(self.allowed("User-agent: *\nDisallow: /\n", path))

    def test_a_hostile_pattern_costs_little_time(self):
        # a robots.txt is written by the site we read: twelve * against a long path must not take exponential time
        import time
        robots = "User-agent: *\nDisallow: /" + "*a" * 12 + "b\n"
        started = time.monotonic()
        self.assertTrue(self.allowed(robots, "/" + "a" * 5000))
        self.assertLess(time.monotonic() - started, 3.0)
        started = time.monotonic()
        blanks = "\n" * 500000 + "User-agent: *\nDisallow: /x\n"
        self.assertTrue(self.allowed(blanks, "/y"))
        self.assertFalse(self.allowed(blanks, "/x"))   # round 14 (Codex): a parse() that did nothing would pass the line above
        self.assertLess(time.monotonic() - started, 3.0)
        # round 14 (Codex): 40,000 rules against the longest address that is read take tenths of a second, not seconds
        started = time.monotonic()
        self.assertTrue(self.allowed("User-agent: *\n" + "Disallow: /*b\n" * 40000, "/" + "a" * 7990))
        self.assertLess(time.monotonic() - started, 3.0)
        # ... and the longest address of the worst kind that is accepted: 665 emoji, 7,980 characters once escaped
        started = time.monotonic()
        self.assertTrue(self.allowed("User-agent: *\n" + "Disallow: /*b\n" * 40000, "/" + "\U0001F600" * 665))
        self.assertLess(time.monotonic() - started, 3.0)

    def test_the_flags_of_a_robots_txt_that_cannot_be_read(self):
        rules = fc.RobotsRules()
        rules.disallow_all = True
        self.assertFalse(rules.allowed("https://x.com/"))
        rules = fc.RobotsRules()
        rules.allow_all = True
        self.assertTrue(rules.allowed("https://x.com/"))


class FetcherRules(unittest.TestCase):
    class Fake(fc.Fetcher):
        def __init__(self, answers):
            super().__init__(timeout=1, delay=0, respect_robots=True)
            self.answers = answers

        def get(self, url, limit=fc.MAX_BYTES, guard_redirects=False):
            status, ctype, body = self.answers.get(url, (404, "", b""))
            return status, ctype, body[:limit], url

    def test_a_robots_txt_that_cannot_be_read_keeps_the_site_out(self):
        # outside review finding: a 503 on robots.txt meant "everything allowed"
        f = self.Fake({"https://x.com/robots.txt": (503, "", b"")})
        self.assertIn("could not be read (503)", f.blocked("https://x.com/a"))
        self.assertEqual(self.Fake({}).blocked("https://x.com/a"), "")  # a 404 allows all

    def test_an_address_that_cannot_be_read_is_not_matched_against_robots_txt(self):
        # round 15 (Codex, GLM): site + "/llms.txt" reached blocked() without the check, nine characters over the limit, and an
        # address of emoji is three times longer once escaped. blocked() leaves such an address to get(), which refuses it
        f = self.Fake({"https://x.com/robots.txt": (200, "text/plain", b"User-agent: *\nDisallow: /\n")})
        self.assertEqual(f.blocked("https://x.com/a"), "robots.txt")
        self.assertEqual(f.blocked("https://x.com/" + "a" * 8000), "")
        self.assertEqual(f.blocked("https://x.com/" + "\U0001F600" * 2000), "")

    def test_the_fetcher_reads_only_web_addresses(self):
        # round 3: a sitemap lists whatever it likes; file: and ftp: are not pages
        f = fc.Fetcher(timeout=1, delay=0, respect_robots=True)
        for url in ("file:///etc/hostname", "ftp://127.0.0.1:9/x", "gopher://example.com/"):
            with self.subTest(url=url):
                status, why, body, _ = f.get(url)
                self.assertEqual((status, body), (0, b""))
                self.assertIn("only web addresses", why)

    def test_a_malformed_address_is_no_page_and_no_crash(self):
        # round 4 (Codex, found in the old code): "ftp://[" in a sitemap raised ValueError out of main()
        f = fc.Fetcher(timeout=1, delay=0, respect_robots=True)
        for url in ("ftp://[", "http://[::1", "http://127.0.0.1:99999/x", "http:///nohost", "http://:80/x", "http://@/",
                    "http://user@:80/x", "x.com/p", "", "http:// /x", "https://x.com/a b", "https://x.com/a\tb"):
            with self.subTest(url=url):
                status, why, body, _ = f.get(url)
                self.assertEqual((status, body), (0, b""))
                self.assertTrue(why.startswith("not a valid address"), why)

    def test_clean_address_is_the_address_as_a_request_sends_it(self):
        self.assertEqual(fc.clean_address(" http://x/a#b c#d \n"), "http://x/a")
        self.assertEqual(fc.clean_address("http://x/a?q=1#"), "http://x/a?q=1")
        self.assertEqual(fc.clean_address("#only"), "")
        # round 9 (Codex): the fragment goes first, then the ends, so that nothing is left to strip twice
        self.assertEqual(fc.clean_address("http://x.test/about #fragment"), "http://x.test/about")
        for url in (" http://x/a #b \n", "http://x/a \t#b#c", "\thttp://x/a\n", "http://x/a b #c", "# #", "  ", ""):
            with self.subTest(url=url):
                self.assertEqual(fc.clean_address(fc.clean_address(url)), fc.clean_address(url))

    def test_robots_txt_judges_the_address_that_is_requested(self):
        # round 9 (Codex): "/about #fragment" was judged as "/about%20" (allowed) and fetched as "/about" (disallowed)
        robots = b"User-agent: *\nAllow: /about%20\nDisallow: /about\n"
        f = self.Fake({"https://x.com/robots.txt": (200, "text/plain", robots),
                       "https://x.com/about": (200, "text/html", b"<html><body><p>We have 27,000 agents</p></body></html>")})
        result = fc.run({"site": "https://x.com", "pages": ["https://x.com/about #fragment"], "facts": [
            {"id": "f", "value": 1, "terms": ["agent"]}]}, 10, 0, 1, "", True, f)
        self.assertEqual(result["read"], [])
        self.assertEqual([(s["url"], s["why"]) for s in result["skipped"]], [("https://x.com/about", "robots.txt")])

    def test_robots_txt_judges_the_path_that_is_requested_for_an_empty_path(self):
        # round 10 (Codex, older code): "http://x.test?private" was judged as "?private" and requested as "/?private"
        robots = b"User-agent: *\nDisallow: /?private\nDisallow: /a%20\nDisallow: /~user\n"
        f = self.Fake({"http://x.test/robots.txt": (200, "text/plain", robots)})
        for url in ("http://x.test?private", "http://x.test/a%20b", "http://x.test/%7Euser/page", "http://x.test/~user/page"):
            with self.subTest(blocked=url):
                self.assertEqual(f.blocked(url), "robots.txt")
        for url in ("http://x.test/", "http://x.test?public", "http://x.test/about", "http://x.test/a%2Db"):
            with self.subTest(allowed=url):
                self.assertEqual(f.blocked(url), "")

    def test_a_byte_order_mark_does_not_lose_the_first_group_of_robots_txt(self):
        # round 12 (GLM, checked on Python 3.9.6 and 3.13.16): "\ufeffUser-agent: *" is not "user-agent" to the standard
        # parser, so the group was dropped and every page was allowed
        robots = b"\xef\xbb\xbfUser-agent: *\nDisallow: /private/\n"
        f = self.Fake({"https://x.com/robots.txt": (200, "text/plain", robots)})
        self.assertEqual(f.blocked("https://x.com/private/x"), "robots.txt")
        self.assertEqual(f.blocked("https://x.com/public"), "")

    def test_sitemap_entries_differing_only_in_the_fragment_are_one_page(self):
        sm = ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
              "<url><loc>https://x.com/p#a b#c</loc></url><url><loc>https://x.com/p#other</loc></url></urlset>").encode()
        notes = []
        pages = fc.sitemap_urls(self.Fake({"https://x.com/sm.xml": (200, "application/xml", sm)}), ["https://x.com/sm.xml"], 10, notes)
        self.assertEqual((pages, notes), (["https://x.com/p"], []))

    def test_bad_address_ignores_the_fragment_and_the_ends(self):
        # round 7 (Codex, GLM): urllib drops the fragment and strips the ends; http.client refuses a space or a control
        # character in the part it sends. test_what_is_requested_is_the_cleaned_address sends real requests
        for ok in ("http://x.test/a#section 2", "http://x.test/a#section 2#end", " https://x.com/a \n", "https://x.com/a%20b", "HTTPS://X.COM/", "http://[::1]:8080/x",
                   "https://user@x.com/", "https://m\u00fcnchen.example/"):
            with self.subTest(ok=ok):
                self.assertEqual(fc.bad_address(ok), "")
        for bad in ("https://x.com/a b#c", "https://x.com/a\tb", "https://x.com/\x00", "http://x.com/ a"):
            with self.subTest(bad=bad):
                self.assertTrue(fc.bad_address(bad).startswith("not a valid address"), bad)

    def test_a_sitemap_with_a_malformed_entry_still_checks_the_other_pages(self):
        sm = ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
              "<url><loc>ftp://[</loc></url><url><loc>http:// /x</loc></url><url><loc>https://x.com/p</loc></url></urlset>").encode()
        f = self.Fake({"https://x.com/sm.xml": (200, "application/xml", sm),
                       "https://x.com/p": (200, "text/html", b"<html><body><p>We have 27,000 agents</p></body></html>")})
        result = fc.run({"site": "https://x.com", "sitemap": "https://x.com/sm.xml", "facts": [
            {"id": "f", "value": 1, "terms": ["agent"]}]}, 1, 0, 1, "", True, f)   # a budget of ONE page
        self.assertEqual([p["url"] for p in result["read"]], ["https://x.com/p"])
        self.assertEqual(result["failed"], [])
        self.assertEqual(result["pages_listed"], 1)   # a left-out entry takes none of the page budget
        self.assertIn("sitemap entries that are not web addresses were left out: 2 (the first: ftp://[)", result["notes"])

    def test_a_robots_txt_that_redirects_without_end_keeps_the_site_out(self):
        # round 3 (Codex, found in the old code): a redirect loop surfaced as status 302, which meant "allow all"
        f = self.Fake({"https://x.com/robots.txt": (302, "", b"")})
        self.assertIn("could not be read (302)", f.blocked("https://x.com/a"))

    def test_a_llms_txt_that_redirects_into_a_disallowed_path_is_noted(self):
        # round 3 (GLM): it was skipped without a word
        f = self.Fake({"https://x.com/p": (200, "text/html", b"<html><body><p>We have 27,000 agents</p></body></html>"),
                       "https://x.com/llms.txt": (fc.REDIRECT_BLOCKED, "redirects to https://x.com/private/llms.txt, "
                                                  "which robots.txt does not allow", b"")})
        # a fixed page list reads no llms.txt, so go through the sitemap
        sm = ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
              "<url><loc>https://x.com/p</loc></url></urlset>").encode()
        f.answers["https://x.com/sm.xml"] = (200, "application/xml", sm)
        result = fc.run({"site": "https://x.com", "sitemap": "https://x.com/sm.xml", "facts": [
            {"id": "f", "value": 1, "terms": ["agent"]}]}, 10, 0, 1, "", True, f)
        self.assertIn("/llms.txt: redirects to https://x.com/private/llms.txt, which robots.txt does not allow",
                      result["notes"])

    def test_a_page_over_5_mb_is_reported_as_cut(self):
        # outside review finding: the cut was silent
        big = b"<html><body><p>" + b"x " * (3 * 1024 * 1024) + b"</p></body></html>"
        f = self.Fake({"https://x.com/big": (200, "text/html", big)})
        result = fc.run({"site": "https://x.com", "pages": ["https://x.com/big"], "facts": [],
                         "retired_phrases": [{"text": "Old Name"}]},
                        10, 0, 1, "", True, f)
        self.assertEqual(len(result["read"]), 1)
        self.assertIn("only the first 5 MB were read", " ".join(result["notes"]))


class SitemapFileLimit(unittest.TestCase):
    SM = '<?xml version="1.0"?><%s xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</%s>'

    def site(self, children):
        answers = {"https://x.com/sitemap.xml": (200, "application/xml", (self.SM % (
            "sitemapindex", "".join("<sitemap><loc>https://x.com/s%d.xml</loc></sitemap>" % i
                                    for i in range(children)), "sitemapindex")).encode())}
        for i in range(children):
            answers["https://x.com/s%d.xml" % i] = (200, "application/xml", (self.SM % (
                "urlset", "<url><loc>https://x.com/p%d</loc></url>" % i, "urlset")).encode())
        return FetcherRules.Fake(answers)

    def result(self, children):
        data = {"site": "https://x.com", "sitemap": "https://x.com/sitemap.xml",
                "facts": [{"id": "f", "value": 1, "terms": ["agent"]}]}
        return fc.run(data, 1000, 0, 1, "", True, self.site(children))

    def test_an_index_cut_by_the_file_limit_says_so(self):
        # round 2 (Codex): 201 child sitemaps gave 199 pages and no word about the other two
        result = self.result(201)
        self.assertEqual(result["pages_listed"], 199)
        self.assertIn("stopped after 200 sitemap files; 2 more were not read", " ".join(result["notes"]))

    def test_an_index_within_the_limit_says_nothing(self):
        result = self.result(3)
        self.assertEqual(result["pages_listed"], 3)
        self.assertNotIn("stopped after", " ".join(result["notes"]))


class LoadFacts(unittest.TestCase):
    def write(self, obj):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            f.write(obj if isinstance(obj, str) else json.dumps(obj))
        self.addCleanup(os.remove, path)
        return path

    def test_a_pasted_address_is_read_without_the_space_or_line_break_at_its_ends(self):
        # round 8 (host seat): "https://x.com/a \n" in the page list was read as a redirect to /a and
        # left out of the positioning check; " https://x.com/b" was refused
        path = self.write({"site": "https://x.com", "pages": ["https://x.com/a \n", " https://x.com/b"],
                           "extra_urls": ["\thttps://y.com/c "], "retired_phrases": [{"text": "Old Name"}]})
        data = fc.load_facts(path)
        self.assertEqual(data["pages"], ["https://x.com/a", "https://x.com/b"])
        self.assertEqual(data["extra_urls"], ["https://y.com/c"])
        path = self.write({"site": "https://x.com", "pages": ["   "], "retired_phrases": [{"text": "Old Name"}]})
        with self.assertRaises(fc.FactsError):
            fc.load_facts(path)

    def test_problems_are_listed_together(self):
        path = self.write({"site": "example.com", "facts": [
            {"id": "a", "value": "27,000+", "terms": []},
            {"id": "a", "value": 5, "terms": ["x"], "retired": [5], "unit": "pct"},
        ]})
        with self.assertRaises(fc.FactsError) as cm:
            fc.load_facts(path)
        msg = str(cm.exception)
        for part in ('"site"', "numeric", 'needs "terms" or "before"', "appears twice",
                     "also listed as retired", '"unit"'):
            self.assertIn(part, msg)

    def test_a_malformed_positioning_block_is_a_message_not_a_crash(self):
        # review finding: a list here raised AttributeError (exit 1, read as "findings")
        for bad in (["x"], "x", {"rules": "x"}):
            with self.subTest(bad=bad):
                with self.assertRaises(fc.FactsError) as cm:
                    fc.load_facts(self.write({"site": "https://x.com", "positioning": bad}))
                self.assertIn('"positioning" must be an object', str(cm.exception))

    def test_positioning_rules_are_validated(self):
        path = self.write({"site": "https://x.com", "positioning": {"rules": [
            {"pages": "en/*", "term": "a"},
            {"pages": "/", "term": "a", "title": ["b"]},
            {"pages": "/x"},
            {"pages": "/y", "h1": [[]]},
        ], "exempt": ["privacy"]}})
        with self.assertRaises(fc.FactsError) as cm:
            fc.load_facts(path)
        msg = str(cm.exception)
        for part in ('starting with "/"', "not both", 'needs a "term"', '"h1" must be', '"exempt"'):
            self.assertIn(part, msg)

    def test_wrong_types_in_the_positioning_block_are_messages_too(self):
        # round 3 (GLM asked): a rule's "pages" and "exempt" of the wrong type, and a rule that is no object
        for bad in ({"rules": [{"pages": 3, "term": "x"}]}, {"rules": [3]},
                    {"rules": [{"pages": "/", "term": "x"}], "exempt": 3},
                    {"rules": [{"pages": "http://[", "term": "x"}]},                    # round 7 (GLM): no "/" first
                    {"rules": [{"pages": "/", "term": "x"}], "exempt": ["a://["]}):
            with self.subTest(bad=bad):
                path = self.write({"site": "https://x.com", "positioning": bad})
                with self.assertRaises(fc.FactsError):
                    fc.load_facts(path)
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(fc.main([path]), 2)

    def test_a_wrong_type_is_a_message_not_a_crash(self):
        # round 2 (Codex): "retired": 3 and "retired_phrases": 3 raised TypeError (a traceback, exit 1)
        cases = {
            '"retired" must be a list of numbers': {"site": "https://x.com", "facts": [
                {"id": "a", "value": 5, "terms": ["x"], "retired": 3}]},
            '"retired_phrases" must be a list': {"site": "https://x.com", "retired_phrases": 3,
                                                 "facts": [{"id": "a", "value": 5, "terms": ["x"]}]},
            '"sitemap" must be a full address': {"site": "https://x.com", "sitemap": 3,
                                                 "facts": [{"id": "a", "value": 5, "terms": ["x"]}]},
            '"site" must be the site': {"site": "http://[", "sitemap": "https://x.com/sm.xml",
                                        "facts": [{"id": "a", "value": 5, "terms": ["x"]}]},
            '"sitemap" must be a full address (https://...)': {"site": "https://x.com", "sitemap": "http://[",
                                                              "facts": [{"id": "a", "value": 5, "terms": ["x"]}]},
        }
        for want, obj in cases.items():
            with self.subTest(want=want):
                path = self.write(obj)
                with self.assertRaises(fc.FactsError) as cm:
                    fc.load_facts(path)
                self.assertIn(want, str(cm.exception))
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    self.assertEqual(fc.main([path]), 2)   # the command line: exit 2, no traceback
                self.assertIn(want, err.getvalue())

    def test_positioning_alone_is_enough(self):
        path = self.write({"site": "https://x.com", "positioning": {"rules": [{"pages": "/", "term": "a"}]}})
        self.assertEqual(fc.load_facts(path)["facts"], [])
        with self.assertRaises(fc.FactsError) as cm:
            fc.load_facts(self.write({"site": "https://x.com"}))
        self.assertIn("nothing to check", str(cm.exception))

    def test_starter_file_is_valid(self):
        path = self.write(fc.STARTER)
        self.assertEqual(fc.load_facts(path)["site"], "https://example.com")

    def test_bad_json(self):
        with self.assertRaises(fc.FactsError):
            fc.load_facts(self.write("{not json"))


# ---------------------------------------------------------------------------
# A stub site
# ---------------------------------------------------------------------------

PAGES = {
    "/robots.txt": ("text/plain", "User-agent: *\nDisallow: /private/\nSitemap: {base}/sitemap-index.xml\n"),
    "/sitemap-index.xml": ("application/xml",
        '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<sitemap><loc>{base}/sitemap-0.xml</loc></sitemap></sitemapindex>"),
    "/sitemap-0.xml": ("application/xml",
        '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        '<url><loc>{base}/</loc><image:image xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
        "<image:loc>{base}/hero.jpg</image:loc></image:image></url><url><loc>{base}/about</loc></url>"
        "<url><loc>{base}/private/x</loc></url><url><loc>{base}/gone</loc></url>"
        "<url><loc>{base}/brochure.pdf</loc></url></urlset>"),
    "/": ("text/html; charset=utf-8",
        "<html><head><title>Acme: 27,000+ agents</title>"
        '<meta name="description" content="Over 25,000 agents in 60 countries.">'
        '<script type="application/ld+json">{"@type":"Organization","description":"30,000 agents"}</script>'
        "<style>.x{width:2000px}</style><script>var agents = 99999;</script></head>"
        '<body><div class="stat"><span>27.000+</span><span>Agenten</span></div>'
        "<p>Trusted by 120 clients. Founded in 2016.</p>"
        "<p>We were the Old Name GmbH.</p></body></html>"),
    "/about": ("text/html",
        "<html><head><title>About</title></head><body>"
        "<h2>70+</h2><p>clients from startups to large firms</p>"
        "<p>An NPS of 72.</p></body></html>"),
    "/brochure.pdf": ("application/pdf", "%PDF-1.4"),
    "/llms.txt": ("text/plain; charset=utf-8", "# Acme\n> Formerly Old Name GmbH. 30,000 agents.\n"),
    # round 2, end to end: a minus sign, a number cut by a span, JSON-LD inside a template
    "/round2": ("text/html", "<html><head><title>Round 2</title></head><body>"
        "<p>An NPS of -5.</p><p><span>27</span>,000 agents</p><p><span>Q2</span><span>-5</span> clients</p>"
        '<template><script type="application/ld+json">{"description": "30,000 agents"}</script></template>'
        "</body></html>"),
    # robots.txt keeps /private/ out; /via-redirect leads there (round 2: a redirect must not get around robots.txt)
    "/private/secret": ("text/html", "<html><head><title>Secret</title></head><body><p>We have 9,999 agents.</p></body></html>"),
}
REDIRECTS = {"/old-offer": "/", "/via-redirect": "/private/secret", "/to-ftp": "ftp://127.0.0.1:9/page.html",
             "/with-fragment": "/about#a b#c"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requestlines.append(self.requestline)   # round 8: tests look at what was actually sent
        if self.path in REDIRECTS:
            self.send_response(301)
            target = REDIRECTS[self.path]
            self.send_header("Location", target if "://" in target else self.server.base + target)
            self.end_headers()
            return
        if self.path == "/cut-off":
            # round 2: a chunked body that ends inside a chunk (the chunk says 256 bytes, 41 come)
            self.protocol_version = "HTTP/1.1"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            self.wfile.write(b"100\r\n<html><body><p>We have 1,234 agents")
            self.close_connection = True
            return
        if self.path == "/short":
            # round 3 (Codex): the header promises 500 bytes, 40 come, and http.client reads a short body without complaint
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", "500")
            self.end_headers()
            self.wfile.write(b"<html><body><p>We have 27,000 agents")
            self.close_connection = True
            return
        if self.path == "/latin1":
            # round 2: a quoted charset parameter, which RFC 9110 allows
            data = "<html><body><p>30 employés</p></body></html>".encode("iso-8859-1")
            self.send_response(200)
            self.send_header("Content-Type", 'text/html; charset="iso-8859-1"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        page = PAGES.get(self.path)
        if page is None:
            self.send_response(404)
            self.end_headers()
            return
        ctype, body = page
        data = body.replace("{base}", self.server.base).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


FACTS = {
    "facts": [
        {"id": "agents", "label": "Agents in the network", "value": 27000,
         "terms": ["agent", "Agenten"], "retired": [25000], "source": "HR system",
         "owner": "Workforce planning", "checked": "[date]"},
        {"id": "clients", "label": "Clients", "value": 120, "terms": ["client"],
         "retired": [70]},
        {"id": "nps", "label": "Customer NPS", "value": 72, "terms": [], "before": ["NPS of"]},
        {"id": "languages", "label": "Languages", "value": 35, "terms": ["language"]},
    ],
    "retired_phrases": [{"text": "Old Name GmbH", "note": "renamed in 2024"}],
}


class FullRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["no_proxy"] = os.environ["NO_PROXY"] = "127.0.0.1,localhost"
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.base = "http://127.0.0.1:%d" % cls.server.server_address[1]
        cls.server.requestlines = []
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def run_check(self, facts, *extra):
        tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: [os.remove(os.path.join(tmp, f)) for f in os.listdir(tmp)] and os.rmdir(tmp))
        path = os.path.join(tmp, "facts.json")
        with open(path, "w") as f:
            json.dump(facts, f)
        out, js, hist = (os.path.join(tmp, n) for n in ("r.md", "r.json", "h.csv"))
        argv = [path, "--out", out, "--json", js, "--history", hist, "--delay", "0", "--timeout", "5"]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = fc.main(argv + list(extra))
        with open(out) as f:
            md = f.read()
        with open(js) as f:
            result = json.load(f)
        history = ""
        if os.path.exists(hist):  # a run that checked nothing writes no history line
            with open(hist) as f:
                history = f.read()
        return code, md, result, history

    def facts(self, **kw):
        d = dict(FACTS, site=self.server.base)
        d.update(kw)
        return d

    def test_finds_every_kind_of_finding(self):
        code, md, result, history = self.run_check(self.facts())
        self.assertEqual(code, 1)
        rows = result["rows"]

        def find(status, value=None, where=None):
            return [r for r in rows if r["status"] == status
                    and (value is None or r.get("found_value") == value)
                    and (where is None or r["where"] == where)]

        # agents: title OK, page text OK (German grouping, number and label in two spans),
        # meta description outdated, structured data mismatch; the inline script is not read
        self.assertTrue(find("OK", 27000, "title"))
        self.assertTrue(find("OK", 27000, "page text"))
        self.assertTrue(find("OUTDATED", 25000, "meta description"))
        self.assertTrue(find("MISMATCH", 30000, "structured data"))
        self.assertFalse([r for r in rows if r.get("found_value") == 99999])
        # 60 countries is not an agent count; 2016 is not a client count
        self.assertFalse([r for r in rows if r.get("found_value") in (60, 2016)])
        # clients: 120 OK on the home page, 70+ outdated on /about across a heading and a paragraph
        self.assertTrue(find("OK", 120))
        # /llms.txt is read too: its old name and its figure count
        llms = [r for r in rows if r["where"] == "llms.txt"]
        self.assertEqual(sorted(r["status"] for r in llms), ["MISMATCH", "RETIRED"])
        self.assertIn("Also read: %s/llms.txt." % self.server.base, md)
        about = find("OUTDATED", 70)
        self.assertEqual(len(about), 1)
        self.assertTrue(about[0]["url"].endswith("/about"))
        self.assertTrue(find("OK", 72))
        self.assertEqual(len(find("RETIRED")), 2)  # the page text and /llms.txt
        # what was not read, and why
        self.assertTrue(any(s["url"].endswith("/private/x") and s["why"] == "robots.txt"
                            for s in result["skipped"]))
        self.assertTrue(any(s["url"].endswith("/brochure.pdf") for s in result["skipped"]))
        self.assertTrue(any(f["url"].endswith("/gone") and f["why"] == "404" for f in result["failed"]))
        # the report names it all
        for part in ("## Mismatches", "## Outdated values", "## Retired phrases still in use",
                     "Source: HR system. Owner: Workforce planning.",
                     "## Facts no page names", "- Languages", "Source: HR system.",
                     "**30,000**", "skipped (robots.txt)", "could not be read (404)"):
            self.assertIn(part, md)
        lines = history.strip().splitlines()
        self.assertEqual(lines[0].split(",")[4], "mismatches")
        self.assertEqual(lines[1].split(",")[2:7], ["2", "3", "2", "2", "2"])

    def test_image_entries_in_the_sitemap_are_not_pages(self):
        # review finding: image:loc was fetched as a page
        _, _, result, _ = self.run_check(self.facts())
        self.assertEqual(result["pages_listed"], 5)
        listed = [p["url"] for p in result["read"] + result["failed"] + result["skipped"]]
        self.assertFalse([u for u in listed if u.endswith(".jpg")])

    def test_a_run_that_reads_no_page_is_never_clean(self):
        # review finding: all pages failing gave a clean headline and a 0/0/0 history line
        facts = self.facts(pages=[self.server.base + "/gone", self.server.base + "/also-gone"])
        tmp = tempfile.mkdtemp()
        path, out, hist = (os.path.join(tmp, n) for n in ("f.json", "r.md", "h.csv"))
        try:
            with open(path, "w") as f:
                json.dump(facts, f)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
                code = fc.main([path, "--out", out, "--history", hist, "--delay", "0"])
            with open(out) as f:
                md = f.read()
            self.assertEqual(code, 2)
            self.assertIn("No page of the site could be read, so nothing was checked", md)
            self.assertFalse(os.path.exists(hist))
            self.assertIn("history was not updated", err.getvalue())
        finally:
            for n in os.listdir(tmp):
                os.remove(os.path.join(tmp, n))
            os.rmdir(tmp)

    def test_only_is_applied_while_the_sitemap_is_read(self):
        # review finding: --only filtered after the list was cut to max_pages * 4
        # The brochure is the sitemap's last entry, past the old cut-off of 4 x 1 entries.
        _, _, result, _ = self.run_check(self.facts(), "--only", "brochure", "--max-pages", "1")
        self.assertEqual(result["pages_listed"], 1)
        self.assertEqual([p["url"] for p in result["skipped"]], [self.server.base + "/brochure.pdf"])

    def test_positioning_on_the_stub_site(self):
        facts = self.facts(facts=[], retired_phrases=[], positioning={
            "rules": [{"pages": "/", "audience": "buyers",  # no h1 here: the intro counts
                       "title": ["agents"], "desc": ["agents"], "h1": [["clients", "customers"]]},
                      {"pages": "/about", "audience": "buyers", "term": "clients"}],
            "exempt": ["/private/*"]})
        code, md, result, history = self.run_check(facts)
        self.assertEqual(code, 1)
        pages = {p["path"]: p["missing"] for p in result["positioning"]["pages"]}
        # "/" meets its per-surface rule; /about has no description and "About" as title
        self.assertEqual(pages["/"], [])
        self.assertEqual([m.split(" needs")[0] for m in pages["/about"]], ["<title>", "<meta description>"])
        self.assertIn("**1 page lost its positioning term**, of 2 with a rule; 0 pages with no rule.", md)
        self.assertNotIn("mismatches", md)  # no facts were checked, so no fact counts
        self.assertIn("| buyers | 2 | 1 | 1 |", md)
        self.assertIn("rule /about: <title> needs", md)
        self.assertEqual(history.strip().splitlines()[1].split(",")[-1], "1")

    def test_exempt_wins_over_a_wildcard_rule_and_redirects_are_listed(self):
        # review findings: an exempt page under "/*" was still checked; an old address
        # that redirects to "/" was checked as the home page and counted twice
        base = self.server.base
        facts = self.facts(facts=[], retired_phrases=[], pages=[base + "/", base + "/about", base + "/old-offer"],
                           positioning={"rules": [{"pages": ["/", "/*"], "term": "agents"}],
                                        "exempt": ["/about"]})
        code, md, result, _ = self.run_check(facts)
        pos = result["positioning"]
        self.assertEqual([p["path"] for p in pos["pages"]], ["/"])
        self.assertEqual(pos["uncovered"], [])
        self.assertEqual([r["url"] for r in pos["redirected"]], [base + "/old-offer"])
        self.assertIn("### Addresses that redirect", md)

    def test_clean_site_exits_zero(self):
        facts = self.facts(pages=[self.server.base + "/"], retired_phrases=[],
                           facts=[{"id": "clients", "value": 120, "terms": ["client"]}])
        code, md, result, _ = self.run_check(facts)
        self.assertEqual(code, 0)
        self.assertIn("**0 mismatches, 0 outdated values, 0 retired phrases**", md)

    def test_ignore_robots_reads_disallowed_pages(self):
        code, _, result, _ = self.run_check(self.facts(), "--ignore-robots")
        self.assertTrue(any(f["url"].endswith("/private/x") and f["why"] == "404"
                            for f in result["failed"]))

    def test_only_and_extra_urls(self):
        facts = self.facts(extra_urls=[self.server.base + "/about"])
        code, md, result, _ = self.run_check(facts, "--only", "/about")
        own = [p["url"] for p in result["read"] if p["origin"] == "own"]
        self.assertEqual(len(own), 1)
        self.assertTrue(own[0].endswith("/about"))
        self.assertIn("(not your site)", md)

    def test_a_redirect_into_a_page_robots_txt_disallows_is_not_followed(self):
        # round 2 (Codex): /via-redirect is allowed, /private/ is not, and the fetch followed the redirect
        base = self.server.base
        facts = self.facts(pages=[base + "/via-redirect", base + "/"], retired_phrases=[])
        code, md, result, _ = self.run_check(facts)
        self.assertFalse([r for r in result["rows"] if r.get("found_value") == 9999])
        skipped = [s for s in result["skipped"] if s["url"].endswith("/via-redirect")]
        self.assertEqual(len(skipped), 1)
        self.assertIn("redirects to " + base + "/private/secret", skipped[0]["why"])
        self.assertIn("robots.txt does not allow", skipped[0]["why"])
        self.assertIn("skipped (redirects to", md)
        # the owner of the site can still read it all
        _, _, result, _ = self.run_check(facts, "--ignore-robots")
        self.assertTrue([r for r in result["rows"] if r.get("found_value") == 9999])

    def test_a_sign_a_split_number_and_a_template_through_a_full_run(self):
        # round 2 (Codex), end to end: -5 is not 5, <span>27</span>,000 is 27,000, and JSON-LD in a
        # <template> says nothing the page shows
        facts = self.facts(pages=[self.server.base + "/round2"], retired_phrases=[], facts=[
            {"id": "nps", "value": 5, "terms": [], "before": ["NPS of"]},
            {"id": "agents", "value": 27000, "terms": ["agent"]},
            {"id": "clients", "value": 5, "terms": ["client"]}])
        code, md, result, _ = self.run_check(facts)
        got = sorted((r["fact"], r["status"], r["found_value"], r["where"]) for r in result["rows"])
        # "Q2" and "-5" in two spans are a quarter and minus five, not the range "Q2-5" (round 5, Codex)
        self.assertEqual(got, [("agents", "OK", 27000, "page text"), ("clients", "MISMATCH", -5, "page text"),
                               ("nps", "MISMATCH", -5, "page text")])
        self.assertEqual(code, 1)

    def test_a_redirect_to_a_non_web_address_is_not_followed(self):
        # round 3 (Codex): with a readable ftp robots.txt, the robots check raised TypeError (an ftp response has no status)
        base = self.server.base
        facts = self.facts(pages=[base + "/to-ftp", base + "/"], retired_phrases=[])
        code, md, result, _ = self.run_check(facts)
        bad = [f for f in result["failed"] if f["url"].endswith("/to-ftp")]
        self.assertEqual(len(bad), 1)
        self.assertIn("only web addresses (http, https) are read", bad[0]["why"])
        self.assertIn(base + "/", [p["url"] for p in result["read"]])

    def test_a_positioning_rule_path_is_a_path_even_with_a_scheme_in_it(self):
        # round 6 (Codex, found in the old code): "//[://x" passed the rule check and then raised ValueError in norm_path
        base = self.server.base
        facts = self.facts(facts=[], retired_phrases=[], pages=[base + "/"],
                           positioning={"rules": [{"pages": "//[://x", "term": "x"}], "exempt": ["/a://[b"]})
        code, md, result, _ = self.run_check(facts)
        self.assertEqual(result["positioning"]["uncovered"], [base + "/"])   # no rule matches the home page
        self.assertEqual(code, 0)

    def test_what_is_requested_is_the_cleaned_address(self):
        # round 8 (Codex, GLM): the validator and the request must agree about the #fragment and the ends. urllib splits
        # the fragment at the LAST "#", so "...#a b#c" kept "a b" in what it sent
        base = self.server.base
        f = fc.Fetcher(timeout=2, delay=0, respect_robots=False)
        for url in (base + "/about#frag with space", " " + base + "/about \n", base + "/about#a b#c", base + "/about#x#y z"):
            with self.subTest(url=url):
                self.server.requestlines.clear()
                status, _, body, _ = f.get(url)
                self.assertEqual(status, 200)
                self.assertEqual(self.server.requestlines, ["GET /about HTTP/1.1"])
        # a redirect whose Location carries such a fragment is followed to the page, not to a request that cannot be sent
        self.server.requestlines.clear()
        status, _, body, final = f.get(base + "/with-fragment", guard_redirects=True)
        self.assertEqual((status, final), (200, base + "/about"))
        self.assertEqual(self.server.requestlines, ["GET /with-fragment HTTP/1.1", "GET /about HTTP/1.1"])
        # a space in what would be sent is refused before anything is sent ...
        self.server.requestlines.clear()
        status, why, _, _ = f.get(base + "/about b")
        self.assertEqual((status, self.server.requestlines), (0, []))
        self.assertTrue(why.startswith("not a valid address"), why)
        # ... because http.client would refuse it, which is the claim the check rests on
        with self.assertRaises(http.client.InvalidURL):
            urllib.request.urlopen(base + "/about b", timeout=2)

    def test_an_address_longer_than_8000_bytes_is_not_requested(self):
        # round 14 (Codex): matching a robots.txt takes time in proportion to the address (6.7 s for one of ten million
        # characters), and servers refuse such requests anyway; RFC 9110 (4.1) asks recipients for 8000 octets at least.
        # Round 15 (Codex, GLM): bytes, not characters: one emoji is 4 bytes and 12 characters once escaped
        base = self.server.base
        longest = base + "/" + "a" * (8000 - len(base) - 1)
        self.assertEqual((len(longest), fc.bad_address(longest)), (8000, ""))
        too_long = longest + "a"
        f = fc.Fetcher(timeout=2, delay=0, respect_robots=False)
        self.server.requestlines.clear()
        status, why, _, _ = f.get(too_long)
        self.assertEqual((status, self.server.requestlines), (0, []))
        self.assertTrue(why.startswith("not a valid address") and "8,000 bytes" in why, why)
        # the limit is the address as it travels, every byte beyond ASCII sent as %XX: 14 for "http://x.test/", 12 per emoji
        emoji = "http://x.test/" + "\U0001F600" * 665
        self.assertEqual((len(fc.robots_form(emoji)), fc.bad_address(emoji)), (14 + 12 * 665, ""))
        self.assertIn("8,000 bytes", fc.bad_address(emoji + "\U0001F600"))
        # a raw address of 8,001 characters is refused without being counted further
        self.assertIn("8,000 bytes", fc.bad_address("http://x.test/" + "%41" * 2663))
        # in a run, the listed page is reported as not read and the others are read
        code, md, result, _ = self.run_check(self.facts(pages=[too_long, base + "/"], retired_phrases=[]))
        self.assertEqual([(f["url"], "8,000 bytes" in f["why"]) for f in result["failed"]], [(too_long, True)])
        self.assertEqual([p["url"] for p in result["read"]], [base + "/"])

    def test_an_address_with_letters_beyond_ascii_is_sent_as_a_browser_sends_it(self):
        # round 16 (Codex): http.client refuses a character beyond ASCII in the request line ("ordinal not in range(128)"),
        # so a sitemap that lists "/über-uns" as written had that page reported as not read. It is sent as a browser
        # sends it, each such character as the %XX of its UTF-8 bytes; the host keeps its letters (http.client sends IDNA)
        base = self.server.base
        f = fc.Fetcher(timeout=2, delay=0, respect_robots=False)
        for url, line in ((base + "/\u00fcber-uns", "GET /%C3%BCber-uns HTTP/1.1"),
                          (base + "/about?q=\u00fc#\u00e4", "GET /about?q=%C3%BC HTTP/1.1"),
                          (base + "/\U0001F600", "GET /%F0%9F%98%80 HTTP/1.1"),
                          (base + "/%C3%BCber-uns", "GET /%C3%BCber-uns HTTP/1.1")):
            with self.subTest(url=url):
                self.server.requestlines.clear()
                status, why, _, _ = f.get(url)
                self.assertNotEqual(status, 0, why)
                self.assertEqual(self.server.requestlines, [line])
        self.assertEqual(fc.clean_address("https://m\u00fcnchen.example/\u00fc?\u00e4=1#x"), "https://m\u00fcnchen.example/%C3%BC?%C3%A4=1")
        # the positioning rules still read such a page by the path a person writes
        self.assertEqual(fc.norm_path(fc.clean_address("https://x.test/\u00fcber-uns/")), "/\u00fcber-uns")

    def test_the_limit_holds_for_the_address_as_the_robots_matcher_reads_it(self):
        # round 16 (Codex): a lone surrogate is no character; quote() made it "?" and robots_form() "%3F", so 7,986 of them
        # passed the 8,000 limit and gave the matcher a path of 23,959 characters. A surrogate makes no address now, and the
        # limit is measured on the address as the matcher reads it
        self.assertTrue(fc.bad_address("http://x.test/" + "\ud800" * 7986).startswith("not a valid address"))
        self.assertTrue(fc.bad_address("http://x.test/a\udfffb").startswith("not a valid address"))
        braces = "http://x.test/" + "{" * 3000      # 3,014 characters as sent, 9,014 as the matcher reads it
        self.assertIn("8,000 bytes", fc.bad_address(braces))
        self.assertEqual(fc.bad_address("http://x.test/" + "{" * 2600), "")

    def test_the_path_robots_txt_is_judged_on_is_the_path_the_request_sends(self):
        # round 15 (Codex): "Disallow: //a" did not hold for "http://x.test//a?" because the path was rebuilt from its parts.
        # The judged path is urllib's own selector now, so it cannot differ from what the server receives
        base = self.server.base
        f = fc.Fetcher(timeout=2, delay=0, respect_robots=False)
        for tail in ("", "/", "/about", "/about?", "?", "?x=1", "//about", "//about?", "///about", "/about;p=1?q", "/about?#frag",
                     "/about%20b", "/%7Eabout", "/about#?"):
            with self.subTest(tail=tail):
                self.server.requestlines.clear()
                f.get(base + tail)
                self.assertEqual(fc.request_target(base + tail), self.server.requestlines[0].split(" ")[1])

    def test_a_padded_site_address_is_cleaned_once_for_every_address_built_from_it(self):
        # round 8 (Codex): "http://x.test:80 \n" passed the check, then run() built "http://x.test:80 \n/sitemap.xml"
        code, md, result, _ = self.run_check(self.facts(site=self.server.base + " \n"))
        self.assertEqual(result["pages_listed"], 5)   # the stub's sitemap lists five
        self.assertEqual(result["site"], self.server.base)
        self.assertIn(code, (0, 1))

    def test_an_address_with_a_space_before_its_fragment_is_the_page_it_names(self):
        # round 9 (Codex): "/about #fragment" was fetched as /about but labelled a redirect to itself, and left out of
        # the positioning check
        base = self.server.base
        facts = self.facts(facts=[], retired_phrases=[], pages=[base + "/about #fragment"],
                           positioning={"rules": [{"pages": "/about", "term": "clients"}]})
        code, md, result, _ = self.run_check(facts)
        pos = result["positioning"]
        self.assertEqual([p["url"] for p in pos["pages"]], [base + "/about"])
        self.assertEqual(pos["redirected"], [])

    def test_a_malformed_address_in_the_page_list_does_not_stop_the_run(self):
        # round 4 (Codex): the page list takes http(s):// text, and "http://[::1" is not an address
        base = self.server.base
        facts = self.facts(pages=["http://[::1", "http://127.0.0.1:99999/x", base + "/"], retired_phrases=[])
        code, md, result, _ = self.run_check(facts)
        self.assertEqual(len(result["failed"]), 2)
        self.assertTrue(all(f["why"].startswith("not a valid address") for f in result["failed"]))
        self.assertEqual([p["url"] for p in result["read"]], [base + "/"])

    def test_a_body_shorter_than_its_content_length_is_not_a_page(self):
        # round 3 (Codex, found in the old code): a cut-off body was read as the whole page and could exit clean
        base = self.server.base
        facts = self.facts(pages=[base + "/short"], retired_phrases=[])
        code, md, result, _ = self.run_check(facts)
        self.assertEqual(code, 2)   # nothing could be read, and that is never clean
        self.assertEqual(result["rows"], [])
        self.assertIn("ended before it was complete", result["failed"][0]["why"])

    def test_a_response_that_ends_in_the_middle_does_not_stop_the_run(self):
        # round 2 (Codex): http.client.IncompleteRead escaped get() and ended the whole run
        base = self.server.base
        facts = self.facts(pages=[base + "/cut-off", base + "/"], retired_phrases=[])
        code, md, result, _ = self.run_check(facts)
        self.assertEqual(code, 1)
        cut = [f for f in result["failed"] if f["url"].endswith("/cut-off")]
        self.assertEqual(len(cut), 1)
        self.assertIn("ended before it was complete", cut[0]["why"])
        self.assertIn(base + "/", [p["url"] for p in result["read"]])

    def test_a_quoted_charset_in_the_header_is_honoured(self):
        # round 2 (Codex): charset="iso-8859-1" turned the accent into a replacement character
        facts = self.facts(pages=[self.server.base + "/latin1"], retired_phrases=[],
                           facts=[{"id": "staff", "value": 25, "terms": ["employ\u00e9"]}])
        _, _, result, _ = self.run_check(facts)
        self.assertEqual([(r["status"], r["found_value"]) for r in result["rows"]], [("MISMATCH", 30)])

    def test_no_pages_is_an_error_not_a_pass(self):
        facts = self.facts(sitemap=self.server.base + "/nothing.xml")
        code, md, result, history = self.run_check(facts)
        self.assertEqual(code, 2)
        self.assertIn("No pages were found", md)
        self.assertEqual(history, "")


class LargeSitemap(unittest.TestCase):
    def test_a_sitemap_over_5_mb_is_read_in_full(self):
        # review finding: every response was cut at 5 MB, so a large sitemap failed to parse
        import gzip
        urls = "".join("<url><loc>https://example.com/p/%06d-%s</loc></url>" % (i, "x" * 60)
                       for i in range(70000))
        xml = ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               + urls + "</urlset>").encode()
        self.assertGreater(len(xml), 5 * 1024 * 1024)

        class Fake:
            def get(self, url, limit=fc.MAX_BYTES, guard_redirects=False):
                body = gzip.compress(xml) if url.endswith(".gz") else xml
                return 200, "application/xml", body[:limit], url

        for name in ("sitemap.xml", "sitemap.xml.gz"):
            with self.subTest(name=name):
                notes = []
                pages = fc.sitemap_urls(Fake(), ["https://example.com/" + name], 100000, notes)
                self.assertEqual((len(pages), notes), (70000, []))


class Cli(unittest.TestCase):
    def test_init_writes_once(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "facts.json")
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(fc.main([path, "--init"]), 0)
                self.assertEqual(fc.main([path, "--init"]), 2)
            self.assertEqual(fc.load_facts(path)["facts"][0]["id"], "clients")
        finally:
            os.remove(path)
            os.rmdir(tmp)

    def test_bad_facts_file_exits_two(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(fc.main(["/nonexistent/facts.json"]), 2)
        self.assertIn("--init", err.getvalue())


if __name__ == "__main__":
    unittest.main()
