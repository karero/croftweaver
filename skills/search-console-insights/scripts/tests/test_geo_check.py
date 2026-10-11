"""geo_check.py — the weekly "does AI name you?" check.

Why these tests matter: the owner reads the trend as "is AI naming my business more
often?". A detector that misses 'Baeckerei' for 'Bäckerei', a failed rerun that wipes
a good week, a ‡ that never fires when the question changed, or a key that leaks into
the launchd log would each make that answer quietly wrong. Scenario ids (S1…S9) refer
to docs/reviews/SKILL-PLAN-geo-check.md.

Most tests enter through geo_check.main() — the same call the CLI and track.sh make —
against a local stub server (_geo_stub.py), with HOME pointed at a temp dir.

Run:  python3 -m unittest discover -s skills/search-console-insights/scripts/tests
"""
import contextlib
import csv
import html
import json
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import geo_check  # noqa: E402
import _geo_stub as stub  # noqa: E402

DOMAIN = "example-bakery.de"
# Placeholders that no real-key pattern matches (check_clean.sh scans the repo).
GKEY, OKEY = "test-gemini-placeholder", "test-openai-placeholder"
BROAD = "Where can I buy sourdough bread in Munich-Schwabing?"


class GeoTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.base = stub.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        stub.reset()
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        # An allowlist, so no key or setting exported in the developer's shell (SERPAPI_KEY,
        # GEO_*_MODEL, OPENAI_API_KEY…) can reach the code under test.
        env = {k: os.environ[k] for k in ("PATH", "LANG", "TMPDIR") if k in os.environ}
        env.update(stub.env_for(self.base))
        env["HOME"] = str(self.home)
        self.env = mock.patch.dict(os.environ, env, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def cli(self, *args, stdin=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            if stdin is not None:
                with mock.patch("sys.stdin", io.StringIO(stdin)):
                    rc = geo_check.main([DOMAIN, *args])
            else:
                rc = geo_check.main([DOMAIN, *args])
        return rc, out.getvalue()

    def setup_site(self, questions=(("broad", BROAD),), confirm=True):
        rc, out = self.cli("--init", "--name", "Bäckerei Example", "--domain", "www.example-bakery.de",
                           "--lang", "de", "--country", "DE")
        self.assertEqual(rc, 0, out)
        for slot, text in questions:
            rc, out = self.cli("--set-question", "--slot", slot, "--text-file", "-", stdin=text)
            self.assertEqual(rc, 0, out)
        if confirm:
            rc, out = self.confirm()
            self.assertEqual(rc, 0, out)

    def confirm(self):
        """The documented flow: preview with --check-drift, then save exactly that page."""
        rc, out = self.cli("--check-drift")
        m = re.search(r"Page code: (\w+)", out)
        return self.cli("--confirm", "--expect", m.group(1) if m else "none")

    def history(self):
        p = self.home / ".config/gsc-insights/geo/geo_history.csv"
        with open(p, newline="") as f:
            return list(csv.DictReader(f))


class Detection(unittest.TestCase):
    """S3 — the name counts however the engine spells it, and only as a whole name."""

    def test_spellings_that_must_count(self):
        cases = [
            ("Bäckerei Example", "Try Baeckerei Example on Hohenzollernstraße."),
            ("Bäckerei Example", "BÄCKEREI EXAMPLE is the best known."),
            ("Bäckerei Example", "Bäckerei-Example bakes daily."),
            ("Café Müller", "Cafe Mueller is nearby."),
            ("Café Müller", "Cafe Muller is nearby."),
            ("Café Müller", "CAFE MUELLER is nearby."),
            ("Bäckerei Café", "Baeckerei Cafe opens at 7."),
            ("Luigi's Pizza", "Luigi’s Pizza has a stone oven."),
            ("C&A", "Shops like C&A sell basics."),
            ("Bäckerei Example", "Bäckerei Example (decomposed)".replace("ä", "ä")),
        ]
        for name, answer in cases:
            with self.subTest(name=name, answer=answer):
                self.assertTrue(geo_check.is_named(answer, [name]))

    def test_near_misses_that_must_not_count(self):
        cases = [
            ("Example", "There are many examples of good bakeries."),
            ("Bäckerei Example", "Bäckerei Examples list is long."),  # genitive-s: documented limitation
            ("Muster", "Mustermann Bakery"),
        ]
        for name, answer in cases:
            with self.subTest(name=name, answer=answer):
                self.assertFalse(geo_check.is_named(answer, [name]))


class HostMatching(unittest.TestCase):
    """S2 — 'cited your site' means the host really is yours."""

    def test_own_hosts(self):
        for h in ["example-bakery.de", "www.example-bakery.de", "https://www.example-bakery.de/brot",
                  "shop.example-bakery.de", "EXAMPLE-BAKERY.DE.", "example-bakery.de:443"]:
            with self.subTest(h=h):
                self.assertTrue(geo_check.host_matches(h, ["www.example-bakery.de"]))

    def test_lookalikes(self):
        for h in ["example-bakery.de.evil.test", "notexample-bakery.de",
                  "other.test/?url=example-bakery.de"]:
            with self.subTest(h=h):
                self.assertFalse(geo_check.host_matches(h, ["example-bakery.de"]))

    def test_idna(self):
        self.assertTrue(geo_check.host_matches("xn--bckerei-example-0kb.de", ["bäckerei-example.de"]))


class WeeklyRun(GeoTestCase):
    def test_s1_gemini_only(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "Bäckerei Example is great.", sources=["https://www.example-bakery.de/"])
        rc, out = self.cli()
        self.assertEqual(rc, 0, out)
        self.assertIn("skipped — no GEO_OPENROUTER_API_KEY (one key for all four) or GEO_OPENAI_API_KEY", out)
        self.assertIn("engines: 1 checked, 0 failed, 5 not set up", out)
        rows = self.history()
        # Gemini answers only without search: its terms forbid analysing grounded answers.
        self.assertEqual({(r["engine"], r["mode"]) for r in rows}, {("gemini", "knows")})
        posts = [h for h in stub.STATE["hits"] if h[0] == "POST"]
        self.assertEqual(len(posts), 3)  # 3 samples of the broad question
        self.assertTrue(all("tools" not in h[3] for h in posts))
        # The key travels as a header, never in the URL, and the bare question is all that's sent.
        self.assertTrue(all(h[2].get("x-goog-api-key") == GKEY and GKEY not in h[1] for h in posts))
        self.assertEqual(posts[0][3]["contents"][0]["parts"][0]["text"], BROAD)
        self.assertNotIn("systemInstruction", posts[0][3])

    def test_s2_counts(self):
        self.setup_site()
        os.environ["GEO_OPENAI_API_KEY"] = OKEY
        stub.engine_reply("openai", "Go to Bäckerei Example.", sources=["https://www.example-bakery.de/"])
        self.cli()
        finds = next(r for r in self.history() if r["mode"] == "finds")
        self.assertEqual((finds["ok"], finds["named"], finds["cited_own"], finds["searched"]),
                         ("3", "3", "3", "3"))
        tool = next(h[3] for h in stub.STATE["hits"] if h[0] == "POST" and h[3].get("tools"))
        self.assertEqual(tool["tools"][0]["user_location"], {"type": "approximate", "country": "DE"})
        self.assertEqual((tool["tool_choice"], tool["store"]), ("required", False))
        self.assertIn("example-bakery.de", finds["cited_domains"])
        knows = next(r for r in self.history() if r["mode"] == "knows")
        self.assertEqual(knows["cited_own"], "")  # no web tools, nothing to cite

    def test_branded_is_never_scored(self):
        self.setup_site(questions=(("broad", BROAD), ("branded", "What is Bäckerei Example?")))
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "I have no information about Bäckerei Example.")
        self.cli()
        branded = [r for r in self.history() if r["slot"] == "branded"]
        self.assertTrue(branded and all(r["named"] == "" for r in branded))

    def test_s7_not_set_up(self):
        rc, out = self.cli()
        self.assertEqual(rc, 3)
        self.assertIn("not set up", out)

    def test_s7b_config_without_keys_is_a_problem(self):
        self.setup_site()
        rc, out = self.cli()
        self.assertEqual(rc, 1)
        self.assertIn("has no engine key", out)

    def test_generic_openai_key_is_never_used(self):
        self.setup_site()
        os.environ["OPENAI_API_KEY"] = "someone-elses-key"
        rc, out = self.cli()
        self.assertEqual(rc, 1)
        self.assertFalse([h for h in stub.STATE["hits"] if h[0] == "POST"])

    def test_keys_are_read_from_the_env_file(self):
        self.setup_site()
        env = self.home / ".config/gsc-insights/.env"
        env.write_text(f'GEO_GEMINI_API_KEY="{GKEY}"\nOPENAI_API_KEY=ignored\n')
        stub.engine_reply("gemini", "Bäckerei Example.")
        rc, out = self.cli()
        self.assertEqual(rc, 0, out)
        self.assertIn("engines: 1 checked", out)

    def test_s8_failed_engine_is_a_problem_and_redacted(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        os.environ["GEO_OPENAI_API_KEY"] = OKEY
        stub.engine_reply("gemini", "", status=403, body=f'{{"error": "API key {GKEY} not valid"}}')
        stub.engine_reply("openai", "Bäckerei Example.", sources=["https://example-bakery.de"])
        rc, out = self.cli()
        self.assertEqual(rc, 1)
        self.assertIn("gemini FAILED", out)
        self.assertNotIn(GKEY, out)
        self.assertIn("engines: 1 checked, 1 failed, 4 not set up", out)
        g = [r for r in self.history() if r["engine"] == "gemini"]
        self.assertTrue(g and all(r["ok"] == "0" and r["named"] == "0" for r in g))
        self.assertTrue(all(r["ok"] == "3" for r in self.history() if r["engine"] == "openai"))

    def test_no_credit_stops_asking_that_engine(self):
        # The live smoke test: OpenAI answered every call with this 429, the run retried each
        # one with pauses and took 9 minutes. Waiting doesn't add credit.
        self.setup_site()
        os.environ["GEO_OPENAI_API_KEY"] = OKEY
        os.environ["GEO_ANTHROPIC_API_KEY"] = "test-anthropic-placeholder"
        stub.engine_reply("openai", "", status=429, body=(
            '{"error": {"message": "You have no credits remaining. Add credits to continue.",'
            ' "type": "insufficient_quota", "code": "credit_balance_exhausted"}}'))
        stub.engine_reply("anthropic", "Bäckerei Example.")
        rc, out = self.cli()
        self.assertEqual(rc, 1)
        openai_calls = [h for h in stub.STATE["hits"] if h[1] == "/v1/responses"]
        self.assertEqual(len(openai_calls), 1)
        self.assertIn("openai FAILED: HTTP 429: You have no credits remaining. Add credits to continue."
                      " (not retried)", out)
        self.assertTrue(any(h[1] == "/v1/messages" for h in stub.STATE["hits"]))  # others still asked

    def test_plain_rate_limit_is_retried(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "", status=429, body='{"error": {"message": "Resource exhausted, slow down"}}')
        self.cli()
        self.assertEqual(len([h for h in stub.STATE["hits"] if h[0] == "POST"]), 9)  # 3 samples x 3 tries

    def test_failed_rerun_does_not_erase_a_good_row(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "Bäckerei Example.")
        self.cli()
        stub.engine_reply("gemini", "", status=429)
        self.cli()
        self.assertTrue(all(r["ok"] == "3" for r in self.history()))
        self.assertEqual(len(self.history()), 1)

    def test_same_day_rerun_replaces(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "nothing relevant")
        self.cli()
        stub.engine_reply("gemini", "Bäckerei Example.")
        self.cli()
        rows = self.history()
        self.assertEqual(len(rows), 1)
        self.assertTrue(all(r["named"] == "3" for r in rows))

    def test_answers_saved_verbatim(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "Line one.\nBäckerei Example, line two.")
        self.cli()
        files = list((self.home / ".config/gsc-insights/geo/answers/example-bakery.de").rglob("*.txt"))
        self.assertEqual(len(files), 3)
        self.assertIn("Line one.\nBäckerei Example, line two.", files[0].read_text())

    def test_perplexity_knows_mode_sends_no_search_tool(self):
        self.setup_site()
        os.environ["GEO_PERPLEXITY_API_KEY"] = "test-pplx-placeholder"
        stub.engine_reply("perplexity", "Bäckerei Example.", sources=["https://example-bakery.de"])
        rc, out = self.cli()
        self.assertEqual(rc, 0, out)
        self.assertEqual({r["mode"] for r in self.history()}, {"knows", "finds"})
        bodies = [h[3] for h in stub.STATE["hits"] if h[0] == "POST"]
        self.assertTrue(all("preset" not in b for b in bodies))  # a preset keeps search on
        self.assertEqual(sum(1 for b in bodies if "tools" not in b), 3)

    def test_finds_answer_without_a_search_is_visible(self):
        self.setup_site()
        os.environ["GEO_ANTHROPIC_API_KEY"] = "test-anthropic-placeholder"
        stub.engine_reply("anthropic", "Bäckerei Example.", searched=False)
        self.cli()
        finds = next(r for r in self.history() if r["mode"] == "finds")
        self.assertEqual(finds["searched"], "0")
        rc, out = self.cli("--trend")
        self.assertIn("searched only 0/3", out)


class ViaOpenRouter(GeoTestCase):
    """The default route: one OpenRouter key for ChatGPT, Claude, Gemini and Perplexity, with each
    provider's OWN web search ("native") — so the measurement is the same as with direct keys."""

    RKEY = "test-openrouter-placeholder"

    def setUp(self):
        super().setUp()
        self.setup_site()
        os.environ["GEO_OPENROUTER_API_KEY"] = self.RKEY
        for e in ("gemini", "openai", "anthropic", "perplexity"):
            stub.engine_reply(e, "Bäckerei Example is the one.", sources=["https://www.example-bakery.de/"])

    def posts(self):
        return [h for h in stub.STATE["hits"] if h[0] == "POST"]

    def test_one_key_asks_all_four_with_native_search(self):
        rc, out = self.cli()
        self.assertEqual(rc, 0, out)
        posts = self.posts()
        self.assertTrue(posts and all(h[1] == "/api/v1/chat/completions" for h in posts))
        models = {h[3]["model"] for h in posts}
        self.assertEqual(models, set(geo_check.OPENROUTER_MODELS.values()))
        for h in posts:
            finds = "plugins" in h[3]
            if finds:
                self.assertEqual(h[3]["plugins"], [{"id": "web", "engine": "native"}])
            self.assertEqual(h[2].get("Authorization"), f"Bearer {self.RKEY}")
        # Gemini is never asked with search, whichever route (Google's terms).
        self.assertFalse([h for h in posts if h[3]["model"].startswith("google/") and "plugins" in h[3]])
        # Sonar always searches and has no native-search option on OpenRouter: no plugin, and
        # no "from memory" rows for Perplexity on this route.
        self.assertFalse([h for h in posts if h[3]["model"].startswith("perplexity/") and "plugins" in h[3]])
        self.assertTrue(all(h[3]["max_tokens"] == 4000 for h in posts))
        self.assertEqual({r["mode"] for r in self.history() if r["engine"] == "perplexity"}, {"finds"})
        rows = self.history()
        self.assertTrue(rows and all(r["route"] == "openrouter" for r in rows))
        finds = next(r for r in rows if r["engine"] == "openai" and r["mode"] == "finds" and r["slot"] == "broad")
        self.assertEqual((finds["named"], finds["cited_own"], finds["searched"]), ("3", "3", "3"))
        self.assertIn("cost of this run via OpenRouter: $", out)
        self.assertIn("engines: 4 checked, 0 failed, 2 not set up", out)

    def test_openrouter_wins_over_direct_keys(self):
        os.environ["GEO_OPENAI_API_KEY"] = OKEY
        self.cli()
        self.assertFalse([h for h in self.posts() if h[1] == "/v1/responses"])
        rc, out = self.cli_bare("--keys")
        self.assertIn("set, not used: OpenRouter is set", out)
        self.assertIn("not needed: OpenRouter is set", out)

    def test_direct_engines_bypass_openrouter_only_for_those_named(self):
        # The owner wants Gemini and Perplexity on their own keys (Gemini's "from memory"
        # column; Perplexity's country-aware search) and the other two on OpenRouter.
        os.environ["GEO_DIRECT_ENGINES"] = "gemini, Perplexity"
        os.environ["GEO_GEMINI_API_KEY"] = "test-gemini-placeholder"
        os.environ["GEO_PERPLEXITY_API_KEY"] = "test-perplexity-placeholder"
        os.environ["GEO_OPENAI_API_KEY"] = OKEY        # set but not named: stays on OpenRouter
        self.cli()
        direct = {stub._engine_of(h[1]) for h in self.posts() if h[1] != "/api/v1/chat/completions"}
        self.assertEqual(direct, {"gemini", "perplexity"})
        routed = {h[3]["model"].split("/")[0] for h in self.posts() if h[1] == "/api/v1/chat/completions"}
        self.assertEqual(routed, {"openai", "anthropic"})
        routes = {r["engine"]: r["route"] for r in self.history()}
        self.assertEqual(routes, {"gemini": "direct", "perplexity": "direct", "openai": "openrouter", "anthropic": "openrouter"})
        rc, out = self.cli_bare("--keys")
        self.assertIn("set ✓, used instead of OpenRouter", out)
        self.assertIn("gemini, perplexity named; using their own key: gemini, perplexity", out)
        self.assertIn("set, not used: OpenRouter is set", out)    # the OpenAI key

    def test_direct_engine_without_its_key_stays_on_openrouter(self):
        os.environ["GEO_DIRECT_ENGINES"] = "perplexity"
        self.cli()
        self.assertFalse([h for h in self.posts() if h[1] != "/api/v1/chat/completions"])
        rc, out = self.cli_bare("--keys")
        self.assertIn("named in GEO_DIRECT_ENGINES, so OpenRouter is used until a key is added", out)
        # The summary line must not claim a key that is not there (Codex, PR #152 round 1).
        self.assertIn("perplexity named; using their own key: none", out)

    def test_no_credit_stops_the_whole_route_after_one_call(self):
        stub.STATE["engines"].clear()
        stub.STATE["router_error"] = {"status": 402, "body": '{"error": {"message": "Insufficient credits. Add more using https://openrouter.ai/credits", "code": 402}}'}
        rc, out = self.cli()
        self.assertEqual(rc, 1)
        self.assertEqual(len(self.posts()), 1)
        self.assertIn("Insufficient credits", out)
        self.assertNotIn(self.RKEY, out)

    def test_one_model_error_does_not_stop_the_others(self):
        # Gemini runs FIRST: a 404 for its model (e.g. a retired slug) must not blank the week
        # for the three assistants after it. Only 401/402 are account-wide.
        stub.engine_reply("gemini", "", status=404, body='{"error": {"message": "No endpoints found for this model."}}')
        rc, out = self.cli()
        self.assertEqual(rc, 1)
        self.assertIn("gemini FAILED", out)
        answered = {r["engine"] for r in self.history() if int(r["ok"] or 0)}
        self.assertEqual(answered, {"openai", "anthropic", "perplexity"})
        self.assertGreater(len(self.posts()), 1)

    def test_request_details_cost_and_redaction(self):
        stub.STATE["engines"]["anthropic"]["status"] = 400
        stub.STATE["engines"]["anthropic"]["body"] = '{"error": {"message": "bad request for ' + self.RKEY + '"}}'
        rc, out = self.cli()
        self.assertNotIn(self.RKEY, out)                             # the router key is redacted
        rows = self.history()
        self.assertEqual({r["model_requested"] for r in rows if r["engine"] == "openai"}, {"openai/gpt-6-luna"})
        # One question, 3 answers each: Gemini 3 + ChatGPT 6 + Perplexity 3 = 12 at the stub's
        # $0.0012; Claude's refused calls carry no cost.
        self.assertIn("cost of this run via OpenRouter: $0.014 (12 replies)", out)

    def test_cut_off_answer_is_a_failure_but_its_cost_counts(self):
        cut = geo_check.EngineError
        with self.assertRaises(cut) as cm:
            geo_check._openrouter_parse({"choices": [{"finish_reason": "length", "message": {"content": "Bäck"}}],
                                         "usage": {"cost": 0.04}})
        self.assertEqual(cm.exception.cost, 0.04)

    def test_a_timeout_is_retried_and_stops_only_that_call(self):
        """Review round 2: round 1 made 408 non-fatal but never retried it. One question: Gemini
        is asked 3 times, so 3 attempts each is 9; the other assistants still answer."""
        stub.engine_reply("gemini", "", status=408, body='{"error": {"message": "Request timeout"}}')
        rc, out = self.cli()
        self.assertEqual(rc, 1, out)
        gemini = [h for h in self.posts() if h[3]["model"] == geo_check.OPENROUTER_MODELS["gemini"]]
        self.assertEqual(len(gemini), 9)
        answered = {r["engine"] for r in self.history() if int(r["ok"] or 0)}
        self.assertEqual(answered, {"openai", "anthropic", "perplexity"})

    def test_billed_replies_that_are_not_answers_count_in_the_run_cost(self):
        """Review round 2: the cut-off test above only called the parser, so the run could drop a
        billed failure's cost unnoticed; and an empty billed reply was dropped already. Through
        the command line: Claude cut off ($0.50 each), Gemini empty ($0.25 each), ChatGPT and
        Perplexity normal ($0.0012 each)."""
        def reply(content, finish, cost=None):
            usage = {"cost": cost} if cost is not None else {}
            return {"model": "m", "choices": [{"finish_reason": finish, "message": {"content": content}}],
                    "usage": usage}
        stub.engine_reply("anthropic", "", raw=reply("Bäck", "length", 0.5))
        stub.engine_reply("gemini", "", raw=reply("", "stop", 0.25))
        rc, out = self.cli()
        self.assertEqual(rc, 1, out)
        calls = {e: sum(1 for h in self.posts() if h[3]["model"] == m)
                 for e, m in geo_check.OPENROUTER_MODELS.items()}
        total = calls["anthropic"] * 0.5 + calls["gemini"] * 0.25 + (calls["openai"] + calls["perplexity"]) * 0.0012
        self.assertIn(f"cost of this run via OpenRouter: ${total:.3f} ({sum(calls.values())} replies)", out)

    def test_a_billed_reply_without_a_price_counts_as_cost_unknown(self):
        """Follow-up from review round 2: a cut-off reply with no price was left out of the cost
        line entirely, so the total looked complete. An HTTP error is not a reply and not billed:
        it stays out. Perplexity cut off without a price; Claude refused (HTTP 400)."""
        stub.engine_reply("perplexity", "", raw={"model": "m", "choices": [
            {"finish_reason": "length", "message": {"content": "Bäck"}}]})
        stub.engine_reply("anthropic", "", status=400, body='{"error": {"message": "bad request"}}')
        rc, out = self.cli()
        self.assertEqual(rc, 1, out)
        calls = {e: sum(1 for h in self.posts() if h[3]["model"] == m)
                 for e, m in geo_check.OPENROUTER_MODELS.items()}
        priced = calls["gemini"] + calls["openai"]
        self.assertIn(f"cost of this run via OpenRouter: ${priced * 0.0012:.3f} ({priced} replies; "
                      f"cost unknown for {calls['perplexity']} more)", out)

    def test_malformed_replies_keep_their_price_and_never_stop_the_run(self):
        """Review round 2 (Codex): a malformed reply with a price lost it ("unknown"); a reply that
        is not JSON left the cost line; `choices` as an object raised a KeyError nothing caught.
        Claude: priced but malformed ($0.25 each). Gemini: not JSON. Perplexity: choices an object."""
        stub.engine_reply("anthropic", "", raw={"model": "m", "usage": {"cost": 0.25},
                                                "choices": [{"finish_reason": "stop", "message": {
                                                    "content": "Bäckerei", "annotations": [
                                                        {"type": "url_citation", "url_citation": None}]}}]})
        stub.engine_reply("gemini", "", raw="not json at all")
        # Codex round 3: nested too deep to read raised RecursionError, and no cost line came out.
        stub.engine_reply("openai", "", raw="[" * 10000 + "0" + "]" * 10000)
        stub.engine_reply("perplexity", "", raw={"model": "m", "choices": {"unexpected": {}}})
        rc, out = self.cli()
        self.assertEqual(rc, 1, out)
        calls = {e: sum(1 for h in self.posts() if h[3]["model"] == m)
                 for e, m in geo_check.OPENROUTER_MODELS.items()}
        unknown = calls["gemini"] + calls["openai"] + calls["perplexity"]
        self.assertIn(f"cost of this run via OpenRouter: ${calls['anthropic'] * 0.25:.3f} "
                      f"({calls['anthropic']} replies; cost unknown for {unknown} more)", out)

    def test_searched_follows_the_reply_s_own_search_counter(self):
        base = {"choices": [{"finish_reason": "stop", "message": {"content": "An answer.", "annotations": []}}]}
        self.assertTrue(geo_check._openrouter_parse({**base, "usage": {"server_tool_use_details": {"web_search_requests": 2}}})[3])
        self.assertFalse(geo_check._openrouter_parse({**base, "usage": {"server_tool_use_details": {"web_search_requests": 0}}})[3])
        self.assertFalse(geo_check._openrouter_parse(base)[3])      # no counter, no citations

    def test_old_perplexity_memory_answer_is_not_current_after_the_switch(self):
        del os.environ["GEO_OPENROUTER_API_KEY"]
        os.environ["GEO_PERPLEXITY_API_KEY"] = "test-placeholder-pplx"
        self.cli("--engines", "perplexity")                        # direct: knows + finds
        os.environ["GEO_OPENROUTER_API_KEY"] = self.RKEY
        self.cli("--engines", "perplexity")                        # OpenRouter: finds only
        rc, out = self.cli("--report")
        page = html.unescape(Path(out.split("Report: ")[1].strip()).read_text())
        self.assertIn("always searches the web", page)
        self.assertNotIn("named you at least once <strong>from memory</strong>", page)

    def test_rows_from_before_the_route_column_count_as_direct(self):
        del os.environ["GEO_OPENROUTER_API_KEY"]
        os.environ["GEO_OPENAI_API_KEY"] = OKEY
        self.cli("--engines", "openai")
        Trend.age_history(self)
        p = geo_check.history_path()
        rows = self.history()
        with open(p, "w", newline="") as f:                          # write them in the old schema
            old = [x for x in geo_check.FIELDS if x != "route"]
            w = csv.DictWriter(f, fieldnames=old, extrasaction="ignore")
            w.writeheader(); w.writerows(rows)
        os.environ["GEO_OPENROUTER_API_KEY"] = self.RKEY
        self.cli("--engines", "openai")
        rc, out = self.cli("--trend")
        self.assertIn("route changed", out)

    def test_no_key_message_points_to_openrouter(self):
        del os.environ["GEO_OPENROUTER_API_KEY"]
        rc, out = self.cli()
        self.assertIn("add GEO_OPENROUTER_API_KEY=...", out)

    def test_route_switch_is_marked_in_the_trend(self):
        del os.environ["GEO_OPENROUTER_API_KEY"]
        os.environ["GEO_OPENAI_API_KEY"] = OKEY
        self.cli("--engines", "openai")
        Trend.age_history(self)
        os.environ["GEO_OPENROUTER_API_KEY"] = self.RKEY
        self.cli("--engines", "openai")
        rc, out = self.cli("--trend")
        self.assertIn("route changed", out)

    def test_report_says_which_assistants_went_through_openrouter(self):
        self.cli()
        rc, out = self.cli("--report")
        page = html.unescape(Path(out.split("Report: ")[1].strip()).read_text())
        self.assertIn("Asked through OpenRouter, which uses each assistant’s own web search: Gemini, ChatGPT, Claude, Perplexity", page)
        self.assertIn("always searches the web", page)            # Perplexity's "from memory" cell

    def cli_bare(self, *args):
        o = io.StringIO()
        with contextlib.redirect_stdout(o), contextlib.redirect_stderr(o):
            rc = geo_check.main(list(args))
        return rc, o.getvalue()


class GoogleViaSerpApi(GeoTestCase):
    """Google's own AI answers (AI Mode, AI Overview) through the owner's SerpApi key."""

    def setUp(self):
        super().setUp()
        self.setup_site()
        os.environ["SERPAPI_KEY"] = "test-serpapi-placeholder"
        rc, out = self.cli("--google", "on")
        self.assertEqual(rc, 0, out)

    def rows(self, engine):
        return [r for r in self.history() if r["engine"] == engine]

    def test_ai_mode_named_and_cited(self):
        stub.STATE["serp"]["google_ai_mode"] = (200, {
            "reconstructed_markdown": "Try **Bäckerei Example** in Schwabing.",
            "references": [{"link": "https://www.example-bakery.de/brot", "title": "t"}]})
        rc, out = self.cli()
        self.assertEqual(rc, 1, out)  # google-overview has no stub → it fails, AI Mode still counts
        r = next(r for r in self.rows("google-ai-mode") if r["slot"] == "broad")
        self.assertEqual((r["mode"], r["ok"], r["named"], r["cited_own"]), ("finds", "1", "1", "1"))
        call = next(h[3] for h in stub.STATE["hits"] if h[1] == "/search")
        self.assertEqual((call["engine"], call["gl"], call["hl"], call["no_cache"]),
                         ("google_ai_mode", "de", "de", "true"))
        self.assertEqual(call["q"], BROAD)

    def test_overview_inline_and_via_follow_up(self):
        stub.STATE["serp"]["google_ai_mode"] = (200, {"text_blocks": [{"type": "paragraph", "snippet": "x"}]})
        stub.STATE["serp"]["google"] = (200, {"ai_overview": {"page_token": "tok123"}})
        stub.STATE["serp"]["google_ai_overview"] = (200, {"text_blocks": [
            {"type": "list", "list": [{"title": "Bäckerei Example", "snippet": "sourdough"}]}],
            "references": [{"link": "https://example-bakery.de"}]})
        rc, out = self.cli()
        self.assertEqual(rc, 0, out)
        r = next(r for r in self.rows("google-overview") if r["slot"] == "broad")
        self.assertEqual((r["named"], r["cited_own"]), ("1", "1"))
        follow = [h[3] for h in stub.STATE["hits"] if h[1] == "/search" and h[3]["engine"] == "google_ai_overview"]
        self.assertTrue(follow and follow[0]["page_token"] == "tok123")

    def test_no_overview_is_its_own_state(self):
        stub.STATE["serp"]["google_ai_mode"] = (200, {"text_blocks": []})
        stub.STATE["serp"]["google"] = (200, {"organic_results": []})
        self.cli()
        r = next(r for r in self.rows("google-overview") if r["slot"] == "broad")
        self.assertEqual((r["ok"], r["named"], r["status"]), ("1", "0", "no AI Overview shown"))
        rc, out = self.cli("--trend")
        self.assertIn("Google showed no AI Overview", out)

    def test_engines_option_asks_only_those(self):
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "Bäckerei Example.")
        stub.STATE["serp"]["google_ai_mode"] = (200, {"reconstructed_markdown": "Bäckerei Example"})
        rc, out = self.cli("--engines", "google-ai-mode")
        self.assertEqual(rc, 0, out)
        self.assertEqual({r["engine"] for r in self.history()}, {"google-ai-mode"})
        self.assertFalse([h for h in stub.STATE["hits"] if h[0] == "POST"])
        with self.assertRaises(SystemExit):
            self.cli("--engines", "bing-chat")

    def test_invalid_key_stops_and_never_prints_the_key(self):
        stub.STATE["serp"]["google_ai_mode"] = (401, {"error": "Invalid API key. Your API key should be here: https://serpapi.com/manage-api-key"})
        stub.STATE["serp"]["google"] = (200, {"error": "Invalid API key for test-serpapi-placeholder"})
        rc, out = self.cli()
        self.assertEqual(rc, 1)
        self.assertIn("google-ai-mode FAILED", out)
        self.assertIn("google-overview FAILED: SerpApi: Invalid API key", out)
        self.assertNotIn("test-serpapi-placeholder", out)
        ai_mode_calls = [h for h in stub.STATE["hits"] if h[1] == "/search" and h[3]["engine"] == "google_ai_mode"]
        self.assertEqual(len(ai_mode_calls), 1)


class ReviewFindings(GeoTestCase):
    """Regression tests for the DIFF-gate round-1 findings (docs/reviews trail)."""

    def test_serpapi_key_alone_does_not_switch_google_on(self):
        # An owner with SERPAPI_KEY for the Top-10 check must not start paying for Google AI
        # checks without saying yes: off until --google on, and no key counts until then.
        self.setup_site()
        os.environ["SERPAPI_KEY"] = "test-serpapi-placeholder"
        rc, out = self.cli()
        self.assertEqual(rc, 1)
        self.assertIn("SERPAPI_KEY is set but Google is off for this site", out)
        self.assertIn("off for this site", out)
        self.assertFalse([h for h in stub.STATE["hits"] if h[1] == "/search"])

    def test_gemini_per_minute_limit_is_retried_not_treated_as_no_credit(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        # Gemini's real per-minute 429 also mentions "plan and billing details".
        stub.engine_reply("gemini", "", status=429, body=(
            '{"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "You exceeded your current '
            'quota, please check your plan and billing details.", "details": [{"@type": '
            '"type.googleapis.com/google.rpc.QuotaFailure", "violations": [{"quotaId": '
            '"GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}]}]}}'))
        self.cli()
        self.assertEqual(len([h for h in stub.STATE["hits"] if h[0] == "POST"]), 9)  # 3 samples x 3 tries

    def test_gemini_daily_quota_stops_that_engine(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "", status=429, body=(
            '{"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "Quota exceeded", '
            '"details": [{"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}}'))
        rc, out = self.cli()
        self.assertEqual(len([h for h in stub.STATE["hits"] if h[0] == "POST"]), 1)
        self.assertIn("(not retried)", out)

    def test_key_is_redacted_even_where_the_message_is_cut(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "", status=400,
                          body='{"error": {"message": "' + "x" * 230 + GKEY + '"}}')
        rc, out = self.cli()
        self.assertNotIn(GKEY[:8], out)

    def test_empty_or_cut_off_answers_are_failures_not_misses(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "   ")
        rc, out = self.cli()
        self.assertEqual(rc, 1)
        self.assertIn("empty answer", out)
        self.assertTrue(all(r["ok"] == "0" for r in self.history()))

    def test_anthropic_answer_cut_at_max_tokens_is_a_failure(self):
        self.assertRaises(geo_check.EngineError, geo_check.parse_response, "anthropic",
                          {"stop_reason": "max_tokens", "content": [{"type": "text", "text": "Bäckerei"}]})
        self.assertRaises(geo_check.EngineError, geo_check.parse_response, "openai",
                          {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}})
        self.assertRaises(geo_check.EngineError, geo_check.parse_response, "gemini",
                          {"candidates": [{"finishReason": "SAFETY", "content": {"parts": []}}]})

    def test_model_override_from_env_file_with_inline_comment(self):
        env = self.home / ".config/gsc-insights/.env"
        env.parent.mkdir(parents=True, exist_ok=True)
        env.write_text("GEO_OPENAI_MODEL=replacement-model   # set 2026-10\n"
                       "GEO_OPENAI_API_KEY=\"quoted-key # not a comment\"\n")
        self.assertEqual(geo_check.model_for("openai"), "replacement-model")
        self.assertEqual(geo_check.load_keys()["openai"], "quoted-key # not a comment")

    def test_detector_version_bump_marks_the_trend(self):
        # End to end: a run under the old detector, a run under a bumped one, and the trend
        # must refuse to compare them as like with like.
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "Bäckerei Example.")
        self.cli()
        Trend.age_history(self)
        with mock.patch.object(geo_check, "DETECTOR_VERSION", "99"):
            self.cli()
            rc, out = self.cli("--trend")
        revs = {r["config_rev"] for r in self.history()}
        self.assertEqual(len(revs), 2)
        self.assertIn("settings changed", out)

    def test_set_names_alias_adds_and_name_replaces(self):
        self.setup_site()
        self.cli("--set-names", "--alias", "Example Bakery")
        self.assertEqual(geo_check.load_config(DOMAIN)["names"], ["Bäckerei Example", "Example Bakery"])
        self.cli("--set-names", "--name", "Neue Bäckerei")
        self.assertEqual(geo_check.load_config(DOMAIN)["names"], ["Neue Bäckerei"])

    def test_strange_page_is_shown_for_review_not_guessed(self):
        # No keyword guessing at bot walls (it rejected real pages and missed localized walls).
        # A page that names the business is read, and --confirm prints it for a person to judge.
        self.setup_site()
        stub.STATE["homepage"] = ("<html><head><title>Einen Moment bitte...</title></head>"
                                  "<body><h1>www.example-bakery.de</h1></body></html>")
        rc, out = self.cli("--check-drift")
        self.assertIn("State: changed", out)
        self.assertIn("Einen Moment bitte", out)

    def test_ordinary_page_with_security_check_headline_is_read(self):
        self.setup_site()
        stub.STATE["homepage"] = ("<html><head><title>IT-Security Check für KMU</title></head><body>"
                                  "<h1>Free security check</h1><p>Bäckerei Example IT</p></body></html>")
        rc, out = self.confirm()
        self.assertEqual(rc, 0, out)

    def test_domain_only_in_markup_is_not_enough(self):
        self.setup_site()
        stub.STATE["homepage"] = ("<html><head><title>Cookie settings</title>"
                                  "<link rel=canonical href='https://example-bakery.de/'></head>"
                                  "<body><h1>We value your privacy</h1></body></html>")
        rc, out = self.cli("--check-drift")
        self.assertIn("Couldn't read the homepage", out)

    def test_new_question_without_confirm_is_flagged(self):
        self.setup_site()
        self.cli("--set-question", "--slot", "narrow", "--text-file", "-", stdin="Sourdough on Sunday?")
        rc, out = self.cli("--check-drift")
        self.assertIn("State: unconfirmed", out)

    def test_set_question_reads_a_file_path(self):
        self.setup_site()
        qf = self.home / "q.txt"
        qf.write_text("Where is the best sourdough in Schwabing?\n")
        rc, out = self.cli("--set-question", "--slot", "narrow", "--text-file", str(qf))
        self.assertEqual(rc, 0, out)
        self.assertEqual(geo_check.load_config(DOMAIN)["queries"][1]["text"],
                         "Where is the best sourdough in Schwabing?")

    def test_report_labels_answers_to_an_earlier_question(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "Bäckerei Example.")
        self.cli()
        self.cli("--set-question", "--slot", "broad", "--text-file", "-", stdin="Best cake in Schwabing?")
        rc, out = self.cli("--report")
        page = Path(out.split("Report: ")[1].strip()).read_text()
        self.assertIn("an earlier version of the question", page)
        self.assertIn("✓ Named in every answer (3 of 3) *</span>", page)
        self.assertIn(html.escape(BROAD), page)

    def test_follow_up_overview_error_is_a_failure(self):
        self.setup_site()
        os.environ["SERPAPI_KEY"] = "test-serpapi-placeholder"
        self.cli("--google", "on")
        stub.STATE["serp"]["google_ai_mode"] = (200, {"reconstructed_markdown": "x"})
        stub.STATE["serp"]["google"] = (200, {"ai_overview": {"page_token": "tok"}})
        stub.STATE["serp"]["google_ai_overview"] = (200, {"error": "Invalid API key."})
        rc, out = self.cli()
        self.assertIn("google-overview FAILED: SerpApi: Invalid API key", out)
        r = next(r for r in self.history() if r["engine"] == "google-overview" and r["slot"] == "broad")
        self.assertNotEqual(r["status"], "no AI Overview shown")


class ReviewRound2(GeoTestCase):
    """Regression tests for DIFF-gate round-2 findings."""

    def test_malformed_citation_does_not_lose_the_run(self):
        self.setup_site()
        os.environ["GEO_OPENAI_API_KEY"] = OKEY
        os.environ["GEO_ANTHROPIC_API_KEY"] = "test-anthropic-placeholder"
        stub.engine_reply("openai", "Bäckerei Example.", sources=[{"not": "a url"}])
        stub.engine_reply("anthropic", "Bäckerei Example.")
        rc, out = self.cli()
        self.assertEqual({r["engine"] for r in self.history()}, {"openai", "anthropic"})
        self.assertTrue(all(r["ok"] == "3" for r in self.history() if r["engine"] == "openai"))

    def test_confirm_saves_only_the_previewed_page(self):
        # A person judges the page (no keyword guessing); the save must be the page they saw.
        self.setup_site()
        before = geo_check.load_config(DOMAIN)["fingerprint"]
        stub.STATE["homepage"] = stub.STATE["homepage"].replace("Sourdough", "Cakes")
        rc, out = self.cli("--check-drift")
        code = re.search(r"Page code: (\w+)", out).group(1)
        stub.STATE["homepage"] = ("<html><head><title>Bäckerei Example</title></head>"
                                  "<body><h1>We value your privacy</h1><p>Accept all</p></body></html>")
        rc, out = self.cli("--confirm", "--expect", code)
        self.assertEqual(rc, 1, out)
        self.assertIn("does not match the current page", out)
        self.assertEqual(geo_check.load_config(DOMAIN)["fingerprint"], before)
        rc, out = self.cli("--confirm")
        self.assertEqual(rc, 1, out)
        self.assertIn("no --expect code given", out)

    def test_page_without_closing_head_is_read(self):
        # Round 3: a "visible text only" parser read this valid page as empty.
        self.setup_site()
        stub.STATE["homepage"] = ("<html><head><title>Sourdough</title><h1>Fresh bread</h1>"
                                  "<p>Bäckerei Example bakes daily.</p></html>")
        rc, out = self.confirm()
        self.assertEqual(rc, 0, out)

    def test_real_homepage_still_reads(self):
        # The stricter check must not reject an ordinary page that names the business in its body.
        self.setup_site()
        stub.STATE["homepage"] = ("<html><head><title>Sourdough | Bäckerei Example</title><script>var x='hidden'</script>"
                                  "</head><body><nav hidden>menu</nav><h1>Fresh bread daily</h1>"
                                  "<p>Bäckerei Example bakes in Schwabing. <img src=a.jpg> Cookies welcome.</p></body></html>")
        rc, out = self.confirm()
        self.assertEqual(rc, 0, out)

    def test_ai_mode_no_results_is_not_a_failure(self):
        self.setup_site()
        os.environ["SERPAPI_KEY"] = "test-serpapi-placeholder"
        self.cli("--google", "on")
        for eng in ("google_ai_mode", "google"):
            stub.STATE["serp"][eng] = (200, {"error": "Google hasn't returned any results for this query."})
        rc, out = self.cli()
        self.assertEqual(rc, 0, out)
        statuses = {r["engine"]: r["status"] for r in self.history() if r["slot"] == "broad"}
        self.assertEqual(statuses, {"google-ai-mode": "no AI Mode answer",
                                    "google-overview": "no AI Overview shown"})
        rc, out = self.cli("--trend")
        self.assertIn("Google's AI Mode gave no answer", out)

    def test_trend_header_counts_only_engines_on_now(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        os.environ["SERPAPI_KEY"] = "test-serpapi-placeholder"
        stub.engine_reply("gemini", "Bäckerei Example.")
        stub.STATE["serp"]["google_ai_mode"] = (200, {"reconstructed_markdown": "x"})
        stub.STATE["serp"]["google"] = (200, {})
        self.cli("--google", "on")
        self.cli()
        self.cli("--google", "off")
        rc, out = self.cli("--trend")
        self.assertIn("engines on now: 1 of 6; in their latest run 1 answered", out)

    def test_legacy_config_still_reports_homepage_changes(self):
        self.setup_site()
        cfg = geo_check.load_config(DOMAIN)
        del cfg["confirmed_questions"]                     # confirmed before that field existed
        geo_check.save_config(DOMAIN, cfg)
        stub.STATE["homepage"] = stub.STATE["homepage"].replace("Sourdough", "Cakes")
        rc, out = self.cli("--check-drift")
        self.assertIn("State: changed", out)

    def test_slow_engine_does_not_starve_the_next(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        os.environ["GEO_OPENAI_API_KEY"] = OKEY
        stub.engine_reply("gemini", "Bäckerei Example.")
        stub.engine_reply("openai", "Bäckerei Example.")
        stub.STATE["delay"] = {"gemini": 1.5}
        with mock.patch.object(geo_check, "ENGINE_BUDGET", 1):
            rc, out = self.cli()
        self.assertIn("gemini FAILED", out)
        self.assertTrue(all(r["ok"] == "3" for r in self.history() if r["engine"] == "openai"))

    def test_stale_marker_on_failed_and_no_answer_cells(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        os.environ["SERPAPI_KEY"] = "test-serpapi-placeholder"
        self.cli("--google", "on")
        stub.engine_reply("gemini", "", status=500)
        stub.STATE["serp"]["google_ai_mode"] = (200, {"error": "Google hasn't returned any results."})
        stub.STATE["serp"]["google"] = (200, {})
        self.cli()
        self.cli("--set-question", "--slot", "broad", "--text-file", "-", stdin="Best cake in Schwabing?")
        rc, out = self.cli("--report")
        page = Path(out.split("Report: ")[1].strip()).read_text()
        self.assertIn("! No answer this time *</span>", page)
        self.assertIn("— Google showed no AI answer *</span>", page)

    def test_cut_emoji_in_an_answer_does_not_crash_the_run(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        os.environ["GEO_OPENAI_API_KEY"] = OKEY
        stub.engine_reply("gemini", "Bäckerei Example \ud83d")   # a lone surrogate, as in a cut snippet
        stub.engine_reply("openai", "Bäckerei Example.")
        rc, out = self.cli()
        self.assertEqual(rc, 0, out)
        self.assertEqual({r["engine"] for r in self.history()}, {"gemini", "openai"})

    def test_ai_mode_empty_200_is_a_failure_not_no_answer(self):
        # Only SerpApi's own "no results" means Google had nothing; an unreadable 200 may be a
        # format change and must show as FAILED.
        self.setup_site()
        os.environ["SERPAPI_KEY"] = "test-serpapi-placeholder"
        self.cli("--google", "on")
        stub.STATE["serp"]["google_ai_mode"] = (200, {"renamed_blocks": [{"snippet": "x"}]})
        stub.STATE["serp"]["google"] = (200, {})
        rc, out = self.cli()
        self.assertIn("google-ai-mode FAILED: empty answer", out)

    def test_perplexity_incomplete_and_null_error_and_unclosed_quote(self):
        self.assertRaises(geo_check.EngineError, geo_check.parse_response, "perplexity",
                          {"status": "incomplete", "output": []})
        r = mock.Mock(status_code=500, text='{"error": null}', reason="Server Error")
        r.json.return_value = {"error": None}
        self.assertEqual(geo_check._error_line(r, []), "HTTP 500: {\"error\": null}")
        env = self.home / ".config/gsc-insights/.env"
        env.parent.mkdir(parents=True, exist_ok=True)
        env.write_text('GEO_OPENAI_API_KEY="placeholder1\nGEO_GEMINI_API_KEY=#abc\n')   # unclosed quote
        self.assertEqual(geo_check.load_keys()["openai"], "placeholder1")
        self.assertEqual(geo_check.load_keys()["gemini"], "#abc")      # bash keeps a leading #

    def test_google_switch_cannot_be_combined_with_other_commands(self):
        self.setup_site()
        with self.assertRaises(SystemExit):
            self.cli("--google", "on", "--set-names", "--alias", "X")

    def test_legacy_config_with_unchanged_homepage_reads_same(self):
        self.setup_site()
        cfg = geo_check.load_config(DOMAIN)
        del cfg["confirmed_questions"]
        geo_check.save_config(DOMAIN, cfg)
        rc, out = self.cli("--check-drift")
        self.assertIn("State: same", out)

    def test_template_contents_do_not_change_the_fingerprint(self):
        p = geo_check._Extract()
        # The template comes FIRST, so without the guard its <meta>/<h1> would win.
        p.feed("<html><head><template><meta name='description' content='TEMPLATE'><h1>T</h1></template>"
               "<meta name='description' content='REAL'></head><body><h1>Real <template><h1>x</h1>"
               "</template>heading</h1><p>Bäckerei Example</p></body></html>")
        self.assertEqual((p.desc, geo_check._norm_text(p.h1)), ("REAL", "Real heading"))

    def test_expect_without_confirm_is_an_error(self):
        self.setup_site()
        with self.assertRaises(SystemExit):
            self.cli("--check-drift", "--expect", "abc")

    def test_gemini_answer_in_several_parts_is_read_whole(self):
        text, *_ = geo_check.parse_response("gemini", {"candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"text": "First part. "}, {"text": "Bäckerei Example is in the second part."}]}}]})
        self.assertTrue(geo_check.is_named(text, ["Bäckerei Example"]))

    def test_commented_empty_key_is_empty(self):
        env = self.home / ".config/gsc-insights/.env"
        env.parent.mkdir(parents=True, exist_ok=True)
        env.write_text("GEO_OPENAI_API_KEY= # add key later\nGEO_GEMINI_MODEL=   # none yet\n")
        self.assertEqual(geo_check.load_keys()["openai"], "")
        self.assertEqual(geo_check.model_for("gemini"), geo_check.DEFAULT_MODELS["gemini"])


class RealReplay(GeoTestCase):
    """Rule 9: one REAL captured response through the production entry point (main()), not
    just through the parser."""

    def test_real_anthropic_answer_through_the_weekly_run(self):
        fixture = json.loads((Path(__file__).parent / "fixtures" / "anthropic-finds.json").read_text())
        for args in (["--init", "--name", "Hofpfisterei", "--domain", "hofpfisterei.de",
                      "--lang", "en", "--country", "DE"],):
            rc, out = self.cli(*args)
            self.assertEqual(rc, 0, out)
        self.cli("--set-question", "--slot", "broad", "--text-file", "-",
                 stdin="Which bakeries in Munich sell sourdough bread?")
        stub.STATE["homepage"] = "<html><body><h1>Hofpfisterei</h1></body></html>"
        rc, out = self.confirm()
        self.assertEqual(rc, 0, out)
        os.environ["GEO_ANTHROPIC_API_KEY"] = "test-anthropic-placeholder"
        stub.engine_reply("anthropic", "", raw=fixture)
        rc, out = self.cli()
        self.assertEqual(rc, 0, out)
        finds = next(r for r in self.history() if r["mode"] == "finds")
        self.assertEqual((finds["ok"], finds["named"], finds["searched"]), ("3", "3", "3"))
        self.assertTrue(finds["cited_domains"])
        # A name from a LATE text block reaches the saved answer (not just the first block).
        saved = next((self.home / ".config/gsc-insights/geo/answers/example-bakery.de").rglob("anthropic-finds-broad-1.txt"))
        self.assertIn("Riedmair", saved.read_text())


class Homepage(GeoTestCase):
    def test_s4_changed_warns_but_never_fails(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "Bäckerei Example.")
        stub.STATE["homepage"] = stub.STATE["homepage"].replace("Sourdough", "Cakes and coffee")
        rc, out = self.cli()
        self.assertEqual(rc, 0, out)
        self.assertIn("homepage looks different", out)
        self.assertIn("Cakes and coffee", out)

    def test_s4b_unreadable_warns_and_confirm_refuses(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "Bäckerei Example.")
        stub.STATE["homepage"] = "<html><title>Just a moment...</title><h1>Checking your browser</h1></html>"
        rc, out = self.cli()
        self.assertEqual(rc, 0, out)
        self.assertIn("Couldn't read your homepage", out)
        before = geo_check.load_config(DOMAIN)["fingerprint"]
        rc, out = self.cli("--confirm")
        self.assertEqual(rc, 1)
        self.assertEqual(geo_check.load_config(DOMAIN)["fingerprint"], before)
        stub.STATE["homepage_status"] = 503
        rc, out = self.cli()
        self.assertIn("HTTP 503", out)

    def test_s5_check_drift_then_keep_or_change(self):
        self.setup_site()
        stub.STATE["homepage"] = stub.STATE["homepage"].replace("Sourdough", "Cakes")
        rc, out = self.cli("--check-drift")
        self.assertIn("State: changed", out)
        self.assertIn(BROAD, out)
        # "keep my question": re-fingerprint only, the rev stays
        self.confirm()
        cfg = geo_check.load_config(DOMAIN)
        self.assertEqual(cfg["queries"][0]["rev"], 1)
        rc, out = self.cli("--check-drift")
        self.assertIn("State: same", out)
        # "use the new one": rev bumps
        self.cli("--set-question", "--slot", "broad", "--text-file", "-", stdin="Where can I buy cake in Schwabing?")
        self.assertEqual(geo_check.load_config(DOMAIN)["queries"][0]["rev"], 2)


class Trend(GeoTestCase):
    def run_week(self, text, model="m-1"):
        stub.engine_reply("gemini", text, model=model)
        rc, out = self.cli()
        self.assertIn(rc, (0, 1), out)

    def age_history(self):
        """Pretend the rows so far were written a week ago (dates and run ids)."""
        p = self.home / ".config/gsc-insights/geo/geo_history.csv"
        rows = self.history()
        for r in rows:
            r["date"], r["run_id"] = "2026-01-01", "20260101T000000Z-" + r["run_id"][17:]
        with open(p, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=geo_check.FIELDS)
            w.writeheader()
            w.writerows(rows)

    def trend(self):
        rc, out = self.cli("--trend")
        self.assertEqual(rc, 0)
        return out

    def test_improvement_shows_up(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        self.run_week("nothing relevant")
        self.age_history()
        self.run_week("Bäckerei Example.")
        out = self.trend()
        self.assertRegex(out, r"gemini\s+knows you\s+broad\s+named 0/3 .*→ 3/3.* ▲")
        self.assertNotIn("‡", out)

    def test_s6_model_change_is_marked(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        self.run_week("Bäckerei Example.", model="m-1")
        self.age_history()
        self.run_week("Bäckerei Example.", model="m-2")
        self.assertIn("‡ model changed", self.trend())

    def test_s5_question_change_is_marked_per_slot(self):
        self.setup_site(questions=(("broad", BROAD), ("narrow", "Sourdough bakery Schwabing open Sunday?")))
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        self.run_week("Bäckerei Example.")
        self.age_history()
        self.cli("--set-question", "--slot", "broad", "--text-file", "-", stdin="Best bakery in Schwabing?")
        self.run_week("Bäckerei Example.")
        lines = self.trend().splitlines()
        broad = [l for l in lines if " broad " in l]
        narrow = [l for l in lines if " narrow " in l]
        self.assertTrue(broad and all("question changed" in l for l in broad))
        self.assertTrue(narrow and not any("‡" in l for l in narrow))

    def test_settings_change_is_marked(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        self.run_week("Bäckerei Example.")
        self.age_history()
        self.cli("--set-names", "--alias", "Example Bakery", "--name", "Bäckerei Example")
        self.run_week("Bäckerei Example.")
        self.assertIn("settings changed", self.trend())

    def test_failed_latest_is_shown_not_hidden(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        self.run_week("Bäckerei Example.")
        self.age_history()
        stub.engine_reply("gemini", "", status=500)
        self.cli()
        out = self.trend()
        self.assertIn("latest attempt", out)
        self.assertIn("named 3/3", out)


class KeySetup(GeoTestCase):
    """The owner walkthrough: prepare the key file, then check what's set — never show a key."""

    def env_file(self):
        return self.home / ".config/gsc-insights/.env"

    def cli_bare(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            rc = geo_check.main(list(args))
        return rc, out.getvalue()

    def test_prepare_env_appends_once_and_keeps_existing_lines(self):
        self.env_file().parent.mkdir(parents=True)
        self.env_file().write_text("BING_API_KEY=keepme")  # no trailing newline
        rc, out = self.cli_bare("--prepare-env")
        self.assertEqual(rc, 0, out)
        text = self.env_file().read_text()
        self.assertTrue(text.startswith("BING_API_KEY=keepme\n"))
        self.assertIn("GEO_OPENROUTER_API_KEY=\n", text)
        self.assertIn("GEO_GEMINI_API_KEY=\n", text)      # the free Gemini line the guide points at
        self.cli_bare("--prepare-env")
        self.assertEqual(self.env_file().read_text(), text)  # a second run adds nothing
        self.assertEqual(self.env_file().stat().st_mode & 0o777, 0o600)

    def test_keys_never_prints_a_value(self):
        self.env_file().parent.mkdir(parents=True)
        self.env_file().write_text(f"GEO_GEMINI_API_KEY={GKEY}\nGEO_OPENAI_API_KEY=\n")
        rc, out = self.cli_bare("--keys")
        self.assertNotIn(GKEY, out)
        self.assertRegex(out, r"GEO_GEMINI_API_KEY\s+set")
        self.assertRegex(out, r"GEO_OPENAI_API_KEY\s+empty")


class Report(GeoTestCase):
    """The owner-facing page. Answers are untrusted text from outside: they must never run
    as code in the owner's browser, and highlighting the name must not break links."""

    def test_markdown_is_rendered_safely(self):
        html_out = geo_check._mark_names(geo_check._light_markdown(
            "### Top\nTry **Bäckerei Example** at [site](https://example-bakery.de/x)"
            " <script>alert(1)</script> [bad](javascript:alert(1))"), ["Bäckerei Example", "example"])
        self.assertIn("<strong>Top</strong>", html_out)
        self.assertIn("<strong><mark>Bäckerei Example</mark></strong>", html_out)
        self.assertIn('href="https://example-bakery.de/x"', html_out)  # no <mark> inside the href
        self.assertIn("&lt;script&gt;", html_out)
        self.assertNotIn("<script>", html_out)
        self.assertNotIn('href="javascript', html_out)

    def test_report_shows_latest_answers_of_every_engine(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "Nothing about bakeries.")
        self.cli()
        os.environ["SERPAPI_KEY"] = "test-serpapi-placeholder"
        self.cli("--google", "on")
        stub.STATE["serp"]["google_ai_mode"] = (200, {"reconstructed_markdown": "Go to **Bäckerei Example**.",
                                                       "references": [{"link": "https://example-bakery.de"}]})
        stub.STATE["serp"]["google"] = (200, {})
        self.cli("--engines", "google-ai-mode,google-overview")  # a later run with only Google
        rc, out = self.cli("--report")
        self.assertEqual(rc, 0, out)
        page = Path(out.split("Report: ")[1].strip()).read_text()
        self.assertIn("Gemini", page)                      # the earlier run is not hidden
        self.assertIn("Google AI Mode", page)
        self.assertIn("✓ Named</span>", page)                # Google: one answer per question
        self.assertIn("✗ Not named (0 of 3)", page)           # a chat engine: three answers
        self.assertIn("Google showed no AI answer", page)
        self.assertIn(html.escape(BROAD), page)

    def test_weekly_run_writes_the_report(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "Bäckerei Example.")
        rc, out = self.cli()
        self.assertIn("report:", out)


class RunOrder(unittest.TestCase):
    def test_run_ids_sort_in_the_order_they_were_made(self):
        # Many IDs within the same second must still sort chronologically ("latest" depends on it).
        ids = [geo_check.new_run_id() for _ in range(200)]
        self.assertEqual(ids, sorted(ids))


class OwnerReport(GeoTestCase):
    """The report is for the business owner. Its numbers must never overstate, every cell state
    must read plainly, and the branded question must never count. Rows go into the real history
    file and the page comes from --report, the call Claude makes (Rule 9)."""

    BROAD2, NARROW = BROAD, "Sourdough bakery open on Sunday in Schwabing?"

    def site(self, engines=("GEO_OPENAI_API_KEY",), google=False):
        self.setup_site(questions=(("broad", self.BROAD2), ("narrow", self.NARROW),
                                   ("branded", "What is Bäckerei Example?")))
        for k in engines:
            os.environ[k] = "test-placeholder-" + k.lower()
        if google:
            self.cli("--google", "on")

    def rows(self, *specs):
        cfg = geo_check.load_config(DOMAIN)
        text = {q["slot"]: q["text"] for q in cfg["queries"]}
        rows = []
        for spec in specs:
            r = {"date": "2026-09-26", "run_id": geo_check.new_run_id(), "site": DOMAIN, "rev": 1,
                 "model_requested": "m", "models_reported": "m", "config_rev": geo_check.config_rev(cfg),
                 "cited_own": "", "cited_domains": "", "searched": "", "status": "ok"}
            r.update(spec)
            r.setdefault("query", text[r["slot"]])
            rows.append(r)
        geo_check.append_history(geo_check.history_path(), rows)

    def page(self):
        rc, out = self.cli("--report")
        self.assertEqual(rc, 0, out)
        return html.unescape(Path(out.split("Report: ")[1].strip()).read_text())

    def test_every_cell_state_reads_plainly(self):
        self.site(engines=("GEO_OPENAI_API_KEY", "GEO_PERPLEXITY_API_KEY", "GEO_GEMINI_API_KEY"), google=True)
        os.environ["SERPAPI_KEY"] = "test-placeholder-serp"
        self.rows(
            {"engine": "openai", "mode": "finds", "slot": "broad", "ok": 3, "named": 3, "cited_own": 2, "searched": 3},
            {"engine": "openai", "mode": "finds", "slot": "narrow", "ok": 3, "named": 1, "searched": 1},
            {"engine": "openai", "mode": "knows", "slot": "broad", "ok": 0, "named": 0, "status": "3 of 3 failed"},
            {"engine": "perplexity", "mode": "finds", "slot": "broad", "ok": 1, "named": 1, "status": "2 of 3 failed"},
            {"engine": "gemini", "mode": "knows", "slot": "broad", "ok": 3, "named": 0},
            {"engine": "google-ai-mode", "mode": "finds", "slot": "broad", "ok": 1, "named": 1},
            {"engine": "google-overview", "mode": "finds", "slot": "broad", "ok": 1, "named": 0,
             "status": "no AI Overview shown"})
        page = self.page()
        for expected in ["✓ Named in every answer (3 of 3)", "your website was a source (2 of 3)",
                         "◐ Sometimes (1 of 3)", "it only searched 1 of 3 times",
                         "! No answer this time", "2 of 3 answers failed", "✗ Not named (0 of 3)",
                         "— not asked", "Google's rules don't allow checking Gemini's web answers",
                         "always searches the web", "not checked yet", "— Google showed no AI answer",
                         "✓ Named</span>", "Not set up: Claude.", "asked once per question"]:
            with self.subTest(expected=expected):
                self.assertIn(expected, page)

    def test_headline_counts_only_what_really_answered(self):
        # Named in every answer to broad, but narrow FAILED: that is not "every question".
        self.site()
        self.rows({"engine": "openai", "mode": "finds", "slot": "broad", "ok": 3, "named": 3},
                  {"engine": "openai", "mode": "finds", "slot": "narrow", "ok": 0, "named": 0, "status": "3 of 3 failed"})
        page = self.page()
        self.assertIn("<b>1 of 1</b>", page)
        self.assertIn("0 in every answer to every question", page)
        self.assertNotIn("all of them named you in every answer", page)

    def test_headline_sometimes_is_not_every_time(self):
        self.site()
        self.rows({"engine": "openai", "mode": "finds", "slot": "broad", "ok": 3, "named": 1},
                  {"engine": "openai", "mode": "finds", "slot": "narrow", "ok": 3, "named": 1})
        page = self.page()
        self.assertIn("not always and not for every question", page)
        self.assertNotIn("all of them named you in every answer", page)

    def test_headline_all_and_none(self):
        self.site()
        self.rows({"engine": "openai", "mode": "finds", "slot": "broad", "ok": 3, "named": 3},
                  {"engine": "openai", "mode": "finds", "slot": "narrow", "ok": 3, "named": 3},
                  {"engine": "openai", "mode": "knows", "slot": "broad", "ok": 3, "named": 0},
                  {"engine": "openai", "mode": "knows", "slot": "narrow", "ok": 3, "named": 0})
        page = self.page()
        self.assertIn("all of them named you in every answer to every question", page)
        self.assertIn("From memory, none of them named you yet", page)

    def test_no_google_answer_is_not_a_miss(self):
        # Google showing no AI Overview says nothing about the business: it must not count as
        # "not named" and pull the headline down.
        self.site(google=True)
        os.environ["SERPAPI_KEY"] = "test-placeholder-serp"
        self.rows({"engine": "openai", "mode": "finds", "slot": "broad", "ok": 3, "named": 3},
                  {"engine": "openai", "mode": "finds", "slot": "narrow", "ok": 3, "named": 3},
                  {"engine": "google-overview", "mode": "finds", "slot": "broad", "ok": 1, "named": 0,
                   "status": "no AI Overview shown"},
                  {"engine": "google-overview", "mode": "finds", "slot": "narrow", "ok": 1, "named": 0,
                   "status": "no AI Overview shown"})
        page = self.page()
        self.assertIn("<b>1 of 1</b>", page)
        self.assertIn("all of them named you in every answer to every question", page)

    def test_branded_answers_never_count(self):
        # Named in every scored answer; the branded row (named "") must not spoil "every question".
        self.site()
        self.rows({"engine": "openai", "mode": "finds", "slot": "broad", "ok": 3, "named": 3},
                  {"engine": "openai", "mode": "finds", "slot": "narrow", "ok": 3, "named": 3},
                  {"engine": "openai", "mode": "finds", "slot": "branded", "ok": 1, "named": ""})
        page = self.page()
        self.assertIn("all of them named you in every answer to every question", page)
        self.assertIn("Do they describe you correctly?", page)
        self.assertIn("don't count toward the numbers above", page)

    def test_answers_to_an_old_question_or_from_a_removed_engine_do_not_count(self):
        self.site()
        self.rows({"engine": "openai", "mode": "finds", "slot": "broad", "ok": 3, "named": 3},
                  {"engine": "openai", "mode": "finds", "slot": "narrow", "ok": 3, "named": 3},
                  {"engine": "anthropic", "mode": "finds", "slot": "broad", "ok": 3, "named": 0})  # no key now
        self.cli("--set-question", "--slot", "narrow", "--text-file", "-", stdin="Rye bread in Schwabing?")
        page = self.page()
        self.assertIn("<b>1 of 1</b>", page)                      # Claude has no key now: not counted
        self.assertIn("0 in every answer to every question", page)  # narrow's answer is to the old question
        self.assertIn("✓ Named in every answer (3 of 3) *", page)
        self.assertIn("to an earlier version of the question", page)

    def test_explains_the_repeat_count_from_the_code(self):
        self.site()
        self.rows({"engine": "openai", "mode": "finds", "slot": "broad", "ok": 3, "named": 0})
        page = self.page()
        n = geo_check.SAMPLES["broad"]
        self.assertIn(f"<strong>{n} times</strong>", page)
        self.assertIn(f"“{n} of {n}” means you were named in every answer", page)
        self.assertIn("different answer each time", page)
        self.assertNotIn("asked once per question", page)       # Google is off for this site
        self.assertIn("Show me my AI report for example-bakery.de", page)
        self.assertIn("Each weekly check writes a new page", page)


class Safety(GeoTestCase):
    def test_override_needs_test_mode_and_loopback(self):
        os.environ["GEO_TEST_MODE"] = "0"
        self.assertEqual(geo_check.override("GEO_OPENAI_BASE_URL", "https://api.openai.com"),
                         "https://api.openai.com")
        os.environ["GEO_TEST_MODE"] = "1"
        os.environ["GEO_OPENAI_BASE_URL"] = "https://evil.test"
        self.assertEqual(geo_check.override("GEO_OPENAI_BASE_URL", "https://api.openai.com"),
                         "https://api.openai.com")

    def test_redaction_covers_every_key_and_encoding(self):
        keys = ["abc def", "plainkey123"]
        msg = geo_check.redact("url?k=abc+def&x=plainkey123 and abc def", keys)
        self.assertNotIn("plainkey123", msg)
        self.assertNotIn("abc def", msg)
        self.assertNotIn("abc+def", msg)

    def test_country_must_be_alpha2(self):
        with self.assertRaises(SystemExit):
            self.cli("--init", "--name", "X", "--lang", "de", "--country", "deu")



class LinkToGoogleReport(GeoTestCase):
    """The AI report links to the Google & Bing report (docs/reviews/SKILL-PLAN-gsc-report.md, D2),
    only when that page exists, and search_report.py's local rebuild makes the link appear without
    another AI request."""

    def test_link_appears_only_when_the_google_page_exists(self):
        self.setup_site()
        os.environ["GEO_GEMINI_API_KEY"] = GKEY
        stub.engine_reply("gemini", "Bäckerei Example.")
        self.cli()
        first = geo_check.build_report(DOMAIN).read_text()
        self.assertNotIn("google.html", first)
        google = geo_check.base_dir() / "reports" / DOMAIN / "google.html"
        google.parent.mkdir(parents=True)
        google.write_text("<p>x</p>")
        hits_before = len(stub.STATE["hits"])
        self.assertGreater(hits_before, 0)                 # the AI run above did reach the stub
        page = geo_check.build_report(DOMAIN)
        self.assertIn(f'href="../../../reports/{DOMAIN}/google.html"', page.read_text())
        self.assertEqual((page.parent / "../../../reports" / DOMAIN / "google.html").resolve(), google.resolve())
        self.assertEqual(len(stub.STATE["hits"]), hits_before)    # the rebuild made no AI request


class ResultsAreNotCitations(GeoTestCase):
    """Perplexity's API returns the search results it retrieved, not which of them the answer
    quotes. Saying the owner's site was "cited" because it was among them overstated the
    result; the trend, the report and the saved-answer captions must say "results" for such an
    engine and keep "cited" and "a source" for the others (geo_check.RESULTS_ONLY says what is
    known about each)."""

    OWN = "https://www.example-bakery.de/brot"

    def setUp(self):
        super().setUp()
        self.setup_site()
        os.environ["GEO_OPENAI_API_KEY"] = OKEY
        os.environ["GEO_PERPLEXITY_API_KEY"] = "test-pplx-placeholder"
        stub.engine_reply("openai", "Bäckerei Example.", sources=[self.OWN])
        stub.engine_reply("perplexity", "Bäckerei Example.", sources=[self.OWN, "https://other.example/"])
        rc, out = self.cli("--engines", "openai,perplexity")
        self.assertEqual(rc, 0, out)

    def finds_line(self, out, engine):
        return next(l for l in out.splitlines() if l.strip().startswith(engine) and "finds you" in l)

    def test_the_count_is_unchanged_only_the_word_differs(self):
        by_engine = {r["engine"]: r for r in self.history() if r["mode"] == "finds"}
        self.assertEqual(by_engine["perplexity"]["cited_own"], "3")      # still: own site among the results
        self.assertEqual(by_engine["openai"]["cited_own"], "3")

    def test_trend_calls_perplexity_results_and_openai_citations(self):
        rc, out = self.cli("--trend")
        self.assertIn("in its results 3/3", self.finds_line(out, "perplexity"))
        self.assertNotIn("cited", self.finds_line(out, "perplexity"))
        self.assertIn("cited 3/3", self.finds_line(out, "openai"))

    def report_page(self):
        rc, out = self.cli("--report")
        return html.unescape(Path(out.split("Report: ")[1].strip()).read_text())

    def part(self, page, pattern):
        m = re.search(pattern, page, re.S)
        self.assertTrue(m, pattern)
        return m.group(0)

    def test_report_says_results_for_perplexity_and_source_for_chatgpt_in_their_own_places(self):
        page = self.report_page()
        for engine, here, other in (("Perplexity", "among its search results", "was a source"),
                                    ("ChatGPT", "was a source", "among its search results")):
            row = self.part(page, rf"<tr><td><strong>{engine}</strong>.*?</tr>")
            self.assertIn(here, row)
            self.assertNotIn(other, row)
        pplx = self.part(page, r"<summary>Perplexity · [^<]*</summary>.*?</details>")
        gpt = self.part(page, r"<summary>ChatGPT · [^<]*</summary>.*?</details>")
        self.assertIn("Search results returned:", pplx)
        self.assertNotIn("Sources:", pplx)
        self.assertIn("Sources:", gpt)
        self.assertNotIn("Search results returned", gpt)

    def test_the_owners_site_shows_in_the_list_even_past_the_twelve_link_cap(self):
        others = [f"https://other{i}.example/" for i in range(14)]
        stub.engine_reply("perplexity", "Bäckerei Example.", sources=others + [self.OWN])   # own site is no. 15
        rc, out = self.cli("--engines", "perplexity")
        self.assertEqual(rc, 0, out)
        pplx = self.part(self.report_page(), r"<summary>Perplexity · [^<]*</summary>.*?</details>")
        self.assertIn("example-bakery.de", pplx)          # the note above the list says it was there
        self.assertIn("first 12 of 15", pplx)             # and the caption says the list is cut

    def test_site_missing_from_the_results_reads_zero_in_its_results(self):
        stub.engine_reply("perplexity", "Bäckerei Example.", sources=["https://other.example/"])
        rc, out = self.cli("--engines", "perplexity")
        self.assertEqual(rc, 0, out)
        rc, out = self.cli("--trend")
        self.assertIn("in its results 0/3", self.finds_line(out, "perplexity"))


if __name__ == "__main__":
    unittest.main()
