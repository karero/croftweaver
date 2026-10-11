#!/usr/bin/env python3
"""
geo_check.py — weekly "does AI name you?" check (GEO), next to the GSC + Bing tracker.

Asks up to four AI engines — plus, if switched on per site, Google's AI Mode and AI Overview
via SerpApi — the owner's confirmed buyer questions, in two modes:
  knows  — no web tools: what the model learned in training (the long-term goal)
  finds  — web search on: what a buyer gets today, plus which sites were cited (Perplexity: which
          search results it returned)
and counts, in code, how often the business is named. Each answer is saved verbatim;
one row per engine x mode x question lands in geo_history.csv; --trend prints the
week-over-week movement and --report a readable page. The plan and its review trail:
docs/reviews/SKILL-PLAN-geo-check.md in the Croftweaver repo.

  geo_check.py <domain>                          weekly run (track.sh calls this)
  geo_check.py <domain> --init --name N --domain D --lang de --country DE [--legal-name L] [--alias A]...
  geo_check.py <domain> --set-names [--name N] [--legal-name L] [--alias A]... [--domain D]... [--lang L] [--country C]
  geo_check.py <domain> --set-question --slot broad|narrow|branded --text-file PATH|-
  geo_check.py <domain> --check-drift            homepage vs. the confirmed questions, no engine calls
  geo_check.py <domain> --confirm --expect CODE  save the previewed homepage (CODE from --check-drift)
  geo_check.py <domain> --google on|off          Google AI Mode + AI Overview for this site (paid searches)
  geo_check.py <domain> --trend | --report
  geo_check.py <domain> --engines gemini,openai  a run limited to some engines
  geo_check.py --keys | --prepare-env            which keys are set (never shown) / add the empty lines

Keys: GEO_OPENROUTER_API_KEY (the default route: one prepaid key for all four chat assistants),
or direct GEO_GEMINI_API_KEY, GEO_OPENAI_API_KEY, GEO_ANTHROPIC_API_KEY, GEO_PERPLEXITY_API_KEY
(GEO_DIRECT_ENGINES=gemini,perplexity sends just those through their direct keys); and
the skill's SERPAPI_KEY (used only for sites with --google on); plus optional GEO_<ENGINE>_MODEL /
GEO_<ENGINE>_OPENROUTER_MODEL overrides — from the environment or ~/.config/gsc-insights/.env. The generic OPENAI_API_KEY etc.
are never read, so a key exported in a developer shell is never billed by accident.

Exit (weekly run): 0 no problems · 1 problems (each printed as a ⚠ line) · 3 not set up.
Homepage warnings are never problems: the owner is asked about them in the next Claude session.
"""
import argparse
import csv
import fcntl
import hashlib
import html
import html.parser
import ipaddress
import json
import os
import random
import re
import shlex
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _history import normalize_site  # noqa: E402
from _lang_normalize import fold  # noqa: E402

try:
    import requests
except ImportError:  # pragma: no cover — the venv from SKILL.md setup has it
    print("✗ 'requests' is not installed — run the venv setup in SKILL.md.", file=sys.stderr)
    sys.exit(2)

# Bump when detection or normalization changes: it is part of config_rev, so the trend
# marks the first comparison across the change instead of showing it as a real move.
DETECTOR_VERSION = "1"

ENGINES = ["gemini", "openai", "anthropic", "perplexity", "google-ai-mode", "google-overview"]
# Google's two AI surfaces come through SerpApi and share the key the skill's Top-10 check
# (serp_check.py) already uses; the chat engines get GEO_* names of their own.
SERP_ENGINES = {"google-ai-mode", "google-overview"}
# Engines whose captured answers come with a source list longer than what the answer marks, so
# that "cited" would overstate (tests/fixtures/perplexity-finds.json, openrouter-perplexity-finds.json):
# Perplexity's own API sends 15 search results with no annotations, no [n] markers and no source
# links in the text; through OpenRouter the text marks 10 sources with [n] (they index the list)
# while the annotation list holds 18 different pages, none with an offset into the text. Their
# count is how often the owner's site was among the results, and is worded that way. The others
# keep "cited": ChatGPT's annotations all point into the text, and Claude's own-key citations are
# a selection of what it searched. Claude through OpenRouter (13 entries over 6 pages, every offset
# 0) and Google's AI Overview (8 references, no block tagged) come with a source list nothing can
# check against the text, and Google's AI Mode tags only 2 of its 6 blocks with the references
# they use. Whether those lists hold only quoted sources is unverified either way: they keep the
# old wording, the docs say so, and a paired capture would settle it. test_real_responses.py pins
# the captures behind all of this (not every other way an answer could name its sources); if a
# refresh changes one, a test fails: revisit this set.
RESULTS_ONLY = {"perplexity"}


def cite_word(engine: str) -> str:
    return "in its results" if engine in RESULTS_ONLY else "cited"


KEY_VARS = {e: ("SERPAPI_KEY" if e in SERP_ENGINES else f"GEO_{e.upper()}_API_KEY") for e in ENGINES}
CHAT_ENGINES = [e for e in ENGINES if e not in SERP_ENGINES]
# The default route: one OpenRouter key and one prepaid balance for all four chat assistants.
# OpenRouter uses each provider's OWN web search for these models ("native"), so "ChatGPT with
# web search on" is still ChatGPT's search. A direct provider key is used without it, or for the
# assistants GEO_DIRECT_ENGINES names (below).
ROUTER_VAR = "GEO_OPENROUTER_API_KEY"
SAMPLES = {"broad": 3, "narrow": 3, "branded": 1}
SLOTS = list(SAMPLES)
MODES = ["knows", "finds"]
FIELDS = ["date", "run_id", "site", "engine", "mode", "slot", "rev", "query",
          "model_requested", "models_reported", "config_rev", "ok", "named",
          "cited_own", "cited_domains", "searched", "status", "route"]

CALL_TIMEOUT = 120      # seconds per engine call — web search answers can take a while
# Per engine, so a slow engine early in the list can't starve the ones after it.
ENGINE_BUDGET = int(os.environ.get("GEO_ENGINE_BUDGET", "400"))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def base_dir() -> Path:
    return Path(os.path.expanduser("~")) / ".config" / "gsc-insights"


def geo_dir() -> Path:
    return base_dir() / "geo"


def config_path(domain: str) -> Path:
    return geo_dir() / f"{normalize_site(domain)}.json"


def history_path() -> Path:
    return geo_dir() / "geo_history.csv"


def eprint(*a):
    print(*a, file=sys.stderr)


# ─── keys ─────────────────────────────────────────────────────────────────────

def setting(name: str) -> str:
    """One of this tool's own settings (GEO_*_API_KEY, SERPAPI_KEY, GEO_*_MODEL): the process
    environment first (track.sh sources .env), else the shared .env itself, so a direct run
    in a Claude session sees the same values. Only these names are ever read — never the
    generic OPENAI_API_KEY and friends."""
    val = os.environ.get(name, "").strip()
    if val:
        return val
    env = base_dir() / ".env"
    if not env.exists():
        return ""
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s*(?:export\s+)?([A-Z_]+)\s*=(.*)$", line)
        if not m or m.group(1) != name:
            continue
        if re.match(r"\s+#", m.group(2)):
            val = ""                                    # "KEY= # later" is empty, as in bash
            continue
        raw = m.group(2).strip()
        if raw and raw[0] in "\"'":
            q = raw[0]                                  # quoted: up to the closing quote (if any)
            val = raw[1:raw.index(q, 1)] if q in raw[1:] else raw[1:].strip()
        else:
            val = re.split(r"\s+#", raw, maxsplit=1)[0].strip()  # unquoted: an inline "# note" ends it, as in bash
    return val


def load_keys() -> dict:
    return {e: setting(v) for e, v in KEY_VARS.items()}


# Chat assistants the owner sends through their own key even with OpenRouter set, e.g.
# GEO_DIRECT_ENGINES=gemini,perplexity: Gemini on a free direct key instead of paid credit, and
# Perplexity with a "from memory" column and the site's country sent with its search, neither of
# which this tool can get through OpenRouter.
DIRECT_VAR = "GEO_DIRECT_ENGINES"


def direct_engines() -> set:
    return {e.strip().lower() for e in setting(DIRECT_VAR).split(",") if e.strip()}


def route_for(engine: str, keys: dict, router_key: str):
    """("openrouter" | "direct" | None, key): OpenRouter first for the chat assistants, except
    the ones GEO_DIRECT_ENGINES names that have their own key."""
    if engine in CHAT_ENGINES and router_key and not (engine in direct_engines() and keys.get(engine)):
        return "openrouter", router_key
    if keys.get(engine):
        return "direct", keys[engine]
    return None, ""


def redact(msg: str, keys) -> str:
    """Every configured key value out of a message, raw and URL-encoded."""
    for k in keys:
        if k:
            msg = msg.replace(k, "<redacted>").replace(quote_plus(k), "<redacted>")
    return msg


def _is_loopback(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def override(var: str, default: str) -> str:
    """Test-only URL override: honoured only with GEO_TEST_MODE=1 AND a loopback host,
    so a stray line in .env can never send a real key somewhere else."""
    val = os.environ.get(var, "")
    if val and os.environ.get("GEO_TEST_MODE") == "1" and _is_loopback(val):
        return val.rstrip("/")
    return default


# ─── detection (code, never an LLM) ───────────────────────────────────────────

_QUOTES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "´": "'", "`": "'"})
_DASHES = re.compile(r"[-‐‑‒–—―]+")


def _strip(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.translate(_QUOTES)
    s = _DASHES.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def forms(s: str):
    """The two comparison forms. German folding first (ä→ae) catches 'Baeckerei';
    plain casefold first catches 'Muller' for 'Müller'. The same form is always
    applied to both the name and the answer."""
    return (_strip(fold(s)), _strip(unicodedata.normalize("NFC", s).casefold()))


def is_named(answer: str, names) -> bool:
    a_forms = forms(answer)
    for name in names:
        for a, n in zip(a_forms, forms(name)):
            if n and re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", a):
                return True
    return False


def norm_host(h: str) -> str:
    h = (h or "").strip().lower()
    h = re.sub(r"^[a-z][a-z0-9+.-]*://", "", h)   # a full URL was passed
    h = h.split("/")[0].split("@")[-1]
    h = re.sub(r":\d+$", "", h).rstrip(".")
    if h.startswith("www."):
        h = h[4:]
    try:
        h = h.encode("idna").decode("ascii")
    except UnicodeError:
        pass
    return h


def host_matches(host: str, domains) -> bool:
    h = norm_host(host)
    return any(h == d or h.endswith("." + d) for d in (norm_host(x) for x in domains) if d)


# ─── homepage fingerprint (a warning, never a failure) ────────────────────────

class _Extract(html.parser.HTMLParser):
    """Title, meta description, first H1, and the page's text (script/style contents excluded).
    Kept deliberately simple: a stricter "only what a visitor sees" parser (hidden elements,
    <head>) misread real homepages in review round 3 — omitted </head>, aria-hidden split
    headings. A person previews the page with --check-drift before --confirm instead."""

    _SKIP = ("script", "style", "noscript", "template")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.desc, self.h1 = "", "", ""
        self.text = []
        self._in = None
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip += 1
        if self._skip:          # a <meta> or <h1> inside <template>/<noscript> isn't the page's
            return
        a = dict(attrs)
        if tag == "title" and not self.title:
            self._in = "title"
        elif tag == "h1" and not self.h1:
            self._in = "h1"
        elif tag == "meta" and (a.get("name") or "").lower() == "description" and not self.desc:
            self.desc = a.get("content") or ""

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip:
            self._skip -= 1
            return
        if self._skip:
            return
        if tag == self._in:
            self._in = None

    def handle_data(self, data):
        if self._skip:
            return
        self.text.append(data)
        if self._in == "title":
            self.title += data
        elif self._in == "h1":
            self.h1 += data


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()


def read_homepage(domain: str, cfg: dict):
    """(text, None) with the normalized title/description/H1, or (None, reason) when the
    page can't be read, or its text names neither the business nor its domain.
    Deliberately no guessing at bot walls from their wording (tried over five review rounds:
    it rejected real pages and missed localized walls). A strange page instead shows up as
    "changed"; a person reads the --check-drift preview, and --confirm --expect <page code>
    saves only if the page's title, description and main heading still match that preview."""
    url = override("GEO_HOMEPAGE_URL", f"https://{normalize_site(domain)}/")
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": UA,
                                                   "Accept-Language": f"{cfg.get('lang', 'en')},en;q=0.5"})
    except requests.RequestException as e:
        return None, type(e).__name__
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    p = _Extract()
    p.feed(r.text)
    text = "\n".join(_norm_text(x) for x in (p.title, p.desc, p.h1))
    page_text = _norm_text(" ".join(p.text))
    if not (is_named(page_text, cfg["names"]) or any(norm_host(d) in page_text.lower() for d in cfg["domains"])):
        return None, "the page's text names neither the business nor its domain (bot wall or consent page?)"
    return text, None


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.casefold().encode()).hexdigest()[:16]


def drift(domain: str, cfg: dict):
    """('same'|'changed'|'unreadable'|'unconfirmed', current_text_or_reason)."""
    text, reason = read_homepage(domain, cfg)
    if text is None:
        return "unreadable", reason
    fp = cfg.get("fingerprint")
    if not fp:
        return "unconfirmed", text
    if fp != fingerprint(text):
        return "changed", text
    confirmed = cfg.get("confirmed_questions")
    if confirmed is not None and confirmed != _question_set(cfg):
        return "unconfirmed", text
    return "same", text


def _question_set(cfg) -> dict:
    return {q["slot"]: q["rev"] for q in cfg.get("queries", [])}


# ─── config ───────────────────────────────────────────────────────────────────

def config_rev(cfg: dict) -> str:
    basis = json.dumps({k: cfg.get(k) for k in ("names", "domains", "lang", "country")}
                       | {"detector": DETECTOR_VERSION}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(basis.encode()).hexdigest()[:10]


def load_config(domain: str):
    p = config_path(domain)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save_config(domain: str, cfg: dict):
    cfg["config_rev"] = config_rev(cfg)
    p = config_path(domain)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def _country(c: str) -> str:
    c = (c or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", c):
        raise SystemExit(f"✗ --country must be a 2-letter ISO code like DE or AT, got {c!r}")
    return c


# ─── engines ──────────────────────────────────────────────────────────────────
# One adapter per engine: build the request; parse the answer text, the reported model,
# the cited URLs and whether a web search actually ran. Shapes follow each provider's
# docs as of 2026-09 — references/geo-check.md "Engines" names them. Every default model
# is overridable (GEO_<ENGINE>_MODEL) because providers retire models.

DEFAULT_MODELS = {
    "gemini": "gemini-3.5-flash-lite",
    "openai": "gpt-6-luna",
    "anthropic": "claude-sonnet-5",
    "perplexity": "perplexity/sonar",
    "google-ai-mode": "serpapi:google_ai_mode",    # Google's own AI; no model to choose
    "google-overview": "serpapi:google",
}
# Gemini's terms forbid analysing or storing search-grounded answers ("You will not ...
# cache, frame, syndicate, resell, analyze, train on, or otherwise learn from Grounded
# Results"), and counting mentions is analysis — so Gemini answers only without search.
FINDS_SUPPORTED = {"gemini": False, "openai": True, "anthropic": True, "perplexity": True,
                   "google-ai-mode": True, "google-overview": True}
# Google's AI answers are search by nature: there is no "knows you" for them.
KNOWS_SUPPORTED = {e: e not in SERP_ENGINES for e in ENGINES}


OPENROUTER_MODELS = {"gemini": "google/gemini-3.5-flash-lite", "openai": "openai/gpt-6-luna",
                     "anthropic": "anthropic/claude-sonnet-5", "perplexity": "perplexity/sonar"}


def model_for(engine: str, route: str = "direct") -> str:
    if engine in SERP_ENGINES:
        return DEFAULT_MODELS[engine]
    if route == "openrouter":
        return setting(f"GEO_{engine.upper()}_OPENROUTER_MODEL") or OPENROUTER_MODELS[engine]
    return setting(f"GEO_{engine.upper()}_MODEL") or DEFAULT_MODELS[engine]


def modes_for(engine: str, route: str = "direct"):
    """Through OpenRouter, Perplexity's Sonar always searches: no "from memory" there."""
    knows = KNOWS_SUPPORTED[engine] and not (route == "openrouter" and engine == "perplexity")
    return [m for m in MODES if (knows if m == "knows" else FINDS_SUPPORTED[engine])]


def samples_for(engine: str, slot: str) -> int:
    """Chat engines vary answer to answer, so unbranded questions get 3 samples. Google's
    engines get 1: every SerpApi call spends a paid search. A cost choice — one Google
    answer per question per week is a thinner signal, and the docs say so."""
    return 1 if engine in SERP_ENGINES else SAMPLES[slot]


def _openrouter_request(engine, mode, question, key):
    """OpenRouter's OpenAI-compatible chat call. With web search on, the "web" plugin with
    engine "native" makes OpenRouter use the provider's own search (never a substitute)."""
    if mode == "finds" and not FINDS_SUPPORTED[engine]:
        raise ValueError(f"{engine} is never asked with search (see FINDS_SUPPORTED)")
    base = override("GEO_OPENROUTER_BASE_URL", "https://openrouter.ai")
    body = {"model": model_for(engine, "openrouter"),
            "messages": [{"role": "user", "content": question}],
            # Without a cap OpenRouter reserves credit for the model's longest possible answer
            # (65k tokens) and refuses the call on a small balance; these answers need far less.
            "max_tokens": 4000,          # includes the model's hidden reasoning; answers need far less
            "usage": {"include": True}}          # the response then carries the call's real cost
    # Perplexity's Sonar searches by itself and has no "native" search option on OpenRouter
    # (verified 2026-09-26: HTTP 404 "does not support native web search"), so it gets no plugin.
    if mode == "finds" and engine != "perplexity":
        body["plugins"] = [{"id": "web", "engine": "native"}]
    return ("POST", f"{base}/api/v1/chat/completions",
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
             "X-Title": "Croftweaver AI check"}, body)


def _openrouter_parse(data):
    """(text, model, cited URLs, searched, cost) from an OpenRouter chat completion."""
    choice = (data.get("choices") or [{}])[0]
    if choice.get("finish_reason") in ("length", "content_filter"):
        usage_cost = (data.get("usage") or {}).get("cost")    # charged all the same
        raise EngineError(f"incomplete answer ({choice['finish_reason']})",
                          cost=usage_cost if isinstance(usage_cost, (int, float)) else None, billed=True)
    msg = choice.get("message") or {}
    text = msg.get("content") or ""
    urls = [a.get("url_citation", {}).get("url", "") for a in msg.get("annotations") or []
            if isinstance(a, dict) and a.get("type") == "url_citation"]
    if not urls:   # some replies list their sources only at the top level
        urls = [u for u in data.get("citations") or [] if isinstance(u, str)]
    usage = data.get("usage") or {}
    searches = (usage.get("server_tool_use_details") or {}).get("web_search_requests")
    # The reply's own search counter when it has one (seen in real replies, not documented);
    # otherwise "it cited a web page".
    searched = searches > 0 if isinstance(searches, int) else bool(urls)
    cost = usage.get("cost")
    return text, data.get("model", ""), urls, searched, cost if isinstance(cost, (int, float)) else None


def build_request(engine, mode, question, cfg, key, route="direct"):
    if route == "openrouter":
        return _openrouter_request(engine, mode, question, key)
    model = model_for(engine)
    country = cfg.get("country")
    finds = mode == "finds"
    if engine == "gemini":
        if finds:
            raise ValueError("Gemini is never asked with search (its terms; see FINDS_SUPPORTED)")
        base = override("GEO_GEMINI_BASE_URL", "https://generativelanguage.googleapis.com")
        body = {"contents": [{"role": "user", "parts": [{"text": question}]}]}
        return ("POST", f"{base}/v1beta/models/{model}:generateContent",
                {"x-goog-api-key": key, "Content-Type": "application/json"}, body)
    if engine == "openai":
        base = override("GEO_OPENAI_BASE_URL", "https://api.openai.com")
        body = {"model": model, "input": question, "store": False}
        if finds:
            # Without a location OpenAI silently searches as if from the United States.
            loc = {"type": "approximate"} | ({"country": country} if country else {})
            body["tools"] = [{"type": "web_search", "user_location": loc}]
            body["tool_choice"] = "required"
        return ("POST", f"{base}/v1/responses",
                {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, body)
    if engine == "anthropic":
        base = override("GEO_ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        body = {"model": model, "max_tokens": 4000,
                "messages": [{"role": "user", "content": question}]}
        if finds:
            tool = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}
            if country:
                tool["user_location"] = {"type": "approximate", "country": country}
            body["tools"] = [tool]
        return ("POST", f"{base}/v1/messages",
                {"x-api-key": key, "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"}, body)
    if engine == "perplexity":
        base = override("GEO_PERPLEXITY_BASE_URL", "https://api.perplexity.ai")
        # A model named directly (no preset) searches only when given the web_search tool.
        body = {"model": model, "input": question, "store": False}
        if finds:
            tool = {"type": "web_search"}
            if country:
                tool["user_location"] = {"country": country}
            body["tools"] = [tool]
        return ("POST", f"{base}/v1/agent",
                {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, body)
    if engine in SERP_ENGINES:
        base = override("GEO_SERPAPI_BASE_URL", "https://serpapi.com")
        # SerpApi takes its key as a query parameter, so errors are redacted in call_engine.
        # no_cache: a cached answer is free but could be days old.
        params = {"engine": "google_ai_mode" if engine == "google-ai-mode" else "google",
                  "q": question, "api_key": key, "hl": cfg.get("lang", "en"), "no_cache": "true"}
        if country:
            params["gl"] = country.lower()
        return ("GET", f"{base}/search", {}, params)
    raise ValueError(engine)


def _flatten_blocks(blocks) -> list:
    """Text of SerpApi's AI text_blocks: paragraphs, headings, lists, nested blocks."""
    out = []
    for b in blocks or []:
        if not isinstance(b, dict):
            continue
        for k in ("title", "snippet"):
            if b.get(k):
                out.append(b[k])
        out += _flatten_blocks(b.get("list"))
        out += _flatten_blocks(b.get("text_blocks"))
    return out


def _output_texts(data):
    """Text of the Responses-style `output` list (OpenAI and Perplexity's Agent API)."""
    return [c.get("text", "") for item in data.get("output", []) or []
            if item.get("type") == "message"
            for c in item.get("content", []) or [] if c.get("type") == "output_text"]


def parse_response(engine, data):
    """(answer_text, reported_model, [cited URL or host, ...], searched: bool)."""
    if engine == "gemini":
        cand = (data.get("candidates") or [{}])[0]
        reason = cand.get("finishReason") or (data.get("promptFeedback") or {}).get("blockReason")
        if reason and reason not in ("STOP", "FINISH_REASON_UNSPECIFIED"):
            raise EngineError(f"incomplete answer ({reason})")
        text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []))
        return text, data.get("modelVersion", ""), [], False
    if engine == "openai":
        if data.get("status") == "incomplete":
            raise EngineError(f"incomplete answer ({(data.get('incomplete_details') or {}).get('reason', '?')})")
        out = data.get("output", []) or []
        sources = [a.get("url", "") for item in out if item.get("type") == "message"
                   for c in item.get("content", []) or []
                   for a in c.get("annotations", []) or [] if a.get("type") == "url_citation"]
        searched = any(item.get("type") == "web_search_call" for item in out)
        return "\n".join(_output_texts(data)), data.get("model", ""), sources, searched
    if engine == "anthropic":
        if data.get("stop_reason") in ("max_tokens", "pause_turn", "refusal"):
            raise EngineError(f"incomplete answer ({data['stop_reason']})")
        texts, sources = [], []
        for b in data.get("content", []) or []:
            if b.get("type") == "text":
                texts.append(b.get("text", ""))
                sources += [c.get("url", "") for c in b.get("citations", []) or [] if c.get("url")]
        uses = ((data.get("usage") or {}).get("server_tool_use") or {}).get("web_search_requests", 0)
        return "".join(texts), data.get("model", ""), sources, bool(uses)
    if engine == "perplexity":
        if data.get("status") == "incomplete":
            raise EngineError(f"incomplete answer ({(data.get('incomplete_details') or {}).get('reason', '?')})")
        results = [r.get("url", "") for item in data.get("output", []) or []
                   if item.get("type") == "search_results"
                   for r in item.get("results", []) or [] if r.get("url")]
        calls = (((data.get("usage") or {}).get("tool_calls_details") or {})
                 .get("search_web") or {}).get("invocation", 0)
        # The answer says nothing about which of these results it quotes (no annotations, no [n]
        # markers in the captured answers), so they are results, not citations: see RESULTS_ONLY.
        return "\n".join(_output_texts(data)), data.get("model", ""), results, bool(results or calls)
    if engine == "google-ai-mode":
        text = data.get("reconstructed_markdown") or "\n".join(_flatten_blocks(data.get("text_blocks")))
        refs = [r.get("link", "") for r in data.get("references", []) or [] if r.get("link")]
        if data.get("_no_results"):
            return NO_AI_MODE, "google-ai-mode", [], True
        return text, "google-ai-mode", refs, True   # an empty 200 is a failed call (format change?)
    if engine == "google-overview":
        ov = data.get("ai_overview") or data   # the follow-up call returns the block at the top
        text = "\n".join(_flatten_blocks(ov.get("text_blocks")))
        refs = [r.get("link", "") for r in ov.get("references", []) or [] if r.get("link")]
        if not text:
            text = NO_OVERVIEW
        return text, "google-overview", refs, True
    raise ValueError(engine)


NO_OVERVIEW = "(Google showed no AI Overview for this question.)"
NO_AI_MODE = "(Google's AI Mode gave no answer for this question.)"
NO_GOOGLE_ANSWER = {NO_OVERVIEW: "no AI Overview shown", NO_AI_MODE: "no AI Mode answer"}
NO_ANSWER_SAYS = {"no AI Overview shown": "Google showed no AI Overview",
                  "no AI Mode answer": "Google's AI Mode gave no answer"}


class EngineError(Exception):
    """A failed call. `fatal` = retrying this engine this run can't help (bad key, missing
    permission, no credit, a request the API rejects), so the run stops asking it."""
    def __init__(self, message, fatal=False, status=None, cost=None, billed=False):
        super().__init__(message)
        self.fatal = fatal
        self.status = status   # the HTTP status, when the failure was an HTTP answer
        self.cost = cost       # what the call cost even though its answer is unusable (OpenRouter)
        # A reply came back but can't be used (cut off, empty, unreadable): it may have been charged,
        # so it counts in the run's cost, as "cost unknown" when the reply gives no price.
        # A price in the reply is proof of the charge, so it sets this too.
        self.billed = billed or cost is not None


def _error_obj(r):
    try:
        j = r.json()
    except ValueError:
        return {}
    err = j.get("error", j) if isinstance(j, dict) else {}
    if err is None:
        return {}
    return err if isinstance(err, dict) else {"message": str(err)}


def _out_of_credit(r) -> bool:
    """A 429 that waiting won't fix: no prepaid credit (OpenAI) or a used-up DAILY quota
    (Gemini). Decided from the error's structured fields, not its wording: Gemini's
    ordinary per-minute 429 also says "check your plan and billing details"."""
    err = _error_obj(r)
    if err.get("code") in ("insufficient_quota", "credit_balance_exhausted") \
            or err.get("type") == "insufficient_quota":
        return True
    for d in err.get("details") or []:
        for v in (d.get("violations") or []) if isinstance(d, dict) else []:
            if "PerDay" in str(v.get("quotaId", "")):
                return True
    return False


def _error_line(r, all_keys) -> str:
    """One readable line from an error response: the API's own message when it has one.
    Redacted BEFORE it is shortened, so a key cut in half can't slip past the redaction."""
    msg = _error_obj(r).get("message") or r.text or r.reason or ""
    msg = re.sub(r"\s+", " ", redact(str(msg), all_keys)).strip()
    return f"HTTP {r.status_code}: {msg[:240]}"


def _send(method, url, headers, payload, all_keys, deadline):
    """One HTTP call with bounded backoff on 429 and 408 (a timeout). Returns the parsed JSON body."""
    delay = 0 if os.environ.get("GEO_TEST_MODE") == "1" else 5
    for attempt in range(3):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise EngineError("time budget used up before this call")
        kw = {"json": payload} if method == "POST" else {"params": payload}
        try:
            r = requests.request(method, url, headers=headers,
                                 timeout=min(CALL_TIMEOUT, max(1, remaining)), **kw)
        except requests.RequestException as e:
            # SerpApi's key is a query parameter, so a transport error's URL carries it.
            raise EngineError(redact(f"{type(e).__name__}: {e}", all_keys)) from None
        if r.status_code == 429 and _out_of_credit(r):
            raise EngineError(_error_line(r, all_keys), fatal=True, status=r.status_code)
        if r.status_code in (408, 429) and attempt < 2:
            time.sleep(delay * (attempt + 1))
            continue
        if r.status_code != 200:
            # An error answer is no reply, so it stays out of the run's cost (an assumption: no
            # OpenRouter record seen here shows a charge for one).
            fatal = 400 <= r.status_code < 500 and r.status_code not in (408, 429)   # 408 = timeout
            raise EngineError(_error_line(r, all_keys), fatal=fatal, status=r.status_code)
        try:
            return r.json()
        except (ValueError, RecursionError):      # RecursionError: nested too deep to read
            # A reply came back, so it may have been charged: on OpenRouter it counts as "cost unknown".
            raise EngineError("unexpected response: not JSON", billed=True) from None
    raise EngineError("HTTP 429: rate limited after retries")


_SERP_NO_RESULT = re.compile(r"hasn't returned any results|no results", re.IGNORECASE)
_SERP_FATAL = re.compile(r"api key|run out of searches|plan|account", re.IGNORECASE)


def call_engine(engine, mode, question, cfg, key, all_keys, deadline, route="direct"):
    """(text, model, sources, searched, cost) — cost in USD when the route reports it, else None."""
    method, url, headers, payload = build_request(engine, mode, question, cfg, key, route)
    data = _serp_checked(engine, _send(method, url, headers, payload, all_keys, deadline), all_keys)
    cost = None
    if engine == "google-overview":
        ov = (data or {}).get("ai_overview") or {}
        if ov.get("page_token") and not ov.get("text_blocks"):
            # Google sometimes serves the overview through a second request; its token
            # expires within minutes, so fetch it right away.
            base = override("GEO_SERPAPI_BASE_URL", "https://serpapi.com")
            data = _serp_checked(engine, _send(
                "GET", f"{base}/search", {},
                {"engine": "google_ai_overview", "page_token": ov["page_token"], "api_key": key},
                all_keys, deadline), all_keys)
    # The price is read on its own first, so a reply too malformed to read still keeps it.
    usage = data.get("usage") if isinstance(data, dict) else None
    reply_cost = usage.get("cost") if isinstance(usage, dict) else None
    reply_cost = reply_cost if isinstance(reply_cost, (int, float)) and not isinstance(reply_cost, bool) else None
    try:
        if route == "openrouter":
            text, model, sources, searched, cost = _openrouter_parse(data or {})
        else:
            text, model, sources, searched = parse_response(engine, data or {})
    except (ValueError, AttributeError, TypeError, KeyError, IndexError) as e:
        # Any shape we don't expect is a failed call, never a crash of the whole run.
        raise EngineError(f"unexpected response shape: {type(e).__name__}",
                          cost=reply_cost if route == "openrouter" else None, billed=True) from None
    # Provider JSON is outside input: only strings go on to be counted, so a malformed
    # citation (an object where a URL should be) can't crash the run after the call.
    # A reply we can't use may still have been charged on OpenRouter: its price goes with the error.
    if not isinstance(text, str):
        raise EngineError("unexpected response shape: answer is not text", cost=cost, billed=True)
    # A snippet cut mid-emoji arrives as a lone surrogate, which can't be written as UTF-8.
    text = text.encode("utf-8", "replace").decode("utf-8")
    sources = [x.encode("utf-8", "replace").decode("utf-8") for x in sources if isinstance(x, str)] \
        if isinstance(sources, list) else []
    if not text.strip():
        # An answer we couldn't read is a failed call, not "the business wasn't named".
        raise EngineError("empty answer (nothing to read in the response)", cost=cost, billed=True)
    sources = [x for x in (sources if isinstance(sources, list) else []) if isinstance(x, str) and x]
    model = (model if isinstance(model, str) else str(model or "")).encode("utf-8", "replace").decode("utf-8")
    return text, model, sources, bool(searched), cost


def _serp_checked(engine, data, all_keys):
    """SerpApi reports some failures inside an HTTP 200 — after every call, the follow-up
    included. "Google showed nothing" arrives that way too and is not a failure."""
    if engine in SERP_ENGINES and isinstance(data, dict) and data.get("error"):
        msg = redact(str(data["error"]), all_keys)
        if not _SERP_NO_RESULT.search(msg):
            raise EngineError(f"SerpApi: {msg[:240]}", fatal=bool(_SERP_FATAL.search(msg)))
        return {"_no_results": True}   # Google itself had nothing; only this maps to "no answer"
    return data


# ─── history ──────────────────────────────────────────────────────────────────

def _key(r):
    return (r["date"], r["site"], r["engine"], r["mode"], r["slot"], str(r["rev"]), r["config_rev"])


def _ok(r) -> int:
    try:
        return int(r.get("ok") or 0)
    except ValueError:
        return 0


def append_history(path: Path, rows):
    """Same lock + temp-file + os.replace pattern as _history.append_rows (which is
    tied to the keyword schema). A same-day rerun replaces its row — unless the new
    row has fewer successful samples, so a failed rerun can't erase a good morning."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + ".lock", "a") as lockf:
        fcntl.flock(lockf, fcntl.LOCK_EX)
        try:
            old = []
            if path.exists() and path.stat().st_size:
                with open(path, newline="", encoding="utf-8-sig") as f:
                    old = list(csv.DictReader(f))
            by_key = {_key(r): r for r in old}
            for r in rows:
                r = {k: str(r.get(k, "")) for k in FIELDS}
                prev = by_key.get(_key(r))
                if prev is None or _ok(r) >= _ok(prev):
                    by_key[_key(r)] = r
            tmp = Path(str(path) + ".tmp")
            try:
                with open(tmp, "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
                    w.writeheader()
                    for r in by_key.values():
                        w.writerow({k: r.get(k, "") for k in FIELDS})
                os.replace(tmp, path)
            except BaseException:
                tmp.unlink(missing_ok=True)
                raise
        finally:
            fcntl.flock(lockf, fcntl.LOCK_UN)


# ─── weekly run ───────────────────────────────────────────────────────────────

_last_run_stamp = ""


def new_run_id() -> str:
    """Sorts in run order, which "latest answer" relies on. Two runs in the same second used to
    sort by process id and a random suffix, so the older could win; microseconds fix that across
    processes, and within one process each new ID is forced to sort after the previous one."""
    global _last_run_stamp
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ") + f"-{now.microsecond:06d}"
    if stamp <= _last_run_stamp:                      # the same microsecond (or a clock step back)
        stamp = _last_run_stamp[:-6] + f"{int(_last_run_stamp[-6:]) + 1:06d}"
    _last_run_stamp = stamp
    return f"{stamp}-{os.getpid()}-{random.getrandbits(16):04x}"


def run(domain: str, only=None) -> int:
    cfg = load_config(domain)
    if cfg is None:
        print("AI check: not set up (ask Claude: 'set up the weekly AI check')")
        return 3
    site = normalize_site(domain)
    problems = []

    state, detail = drift(domain, cfg)
    if state == "changed":
        print("⚠ Your homepage looks different from when your AI-check questions were confirmed "
              "(a real change, or a cookie/bot page this time).")
        print(f"  was: {cfg.get('fingerprint_text', '').replace(chr(10), ' | ')}")
        print(f"  now: {detail.replace(chr(10), ' | ')}")
        print("  Ask Claude to review the questions next time (it will ask you first).")
    elif state == "unreadable":
        print(f"⚠ Couldn't read your homepage ({detail}) — the questions still ran.")
    elif state == "unconfirmed":
        print("⚠ The questions changed (or were never confirmed) since they were last checked against "
              "the homepage — ask Claude to review them (--check-drift, then --confirm --expect <page code>).")

    keys = load_keys()
    router_key = setting(ROUTER_VAR)
    all_keys = [k for k in [*keys.values(), router_key] if k]
    usable = [e for e in ENGINES if route_for(e, keys, router_key)[0] and (e not in SERP_ENGINES or cfg.get("google"))]
    queries = [q for q in cfg.get("queries", []) if q.get("text")]
    if not usable and keys.get("google-ai-mode") and not cfg.get("google"):
        problems.append(f"the AI check has no engine it may ask: SERPAPI_KEY is set but Google is off "
                        f"for this site (turn on with --google on, or add {ROUTER_VAR}: one key for all four assistants)")
    elif not usable:
        problems.append("the AI check is set up but has no engine key "
                        f"(add {ROUTER_VAR}=... to {base_dir() / '.env'}: one key for all four assistants)")
    if not queries:
        problems.append("the AI check has no questions yet (ask Claude to draft them)")

    run_id = new_run_id()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    answers = geo_dir() / "answers" / site / run_id
    pause = 0 if os.environ.get("GEO_TEST_MODE") == "1" else 1.0
    rows, checked, failed, not_set_up = [], [], [], []
    write_errors = set()
    run_cost = []
    route_dead = {}   # a fatal error on a shared route (no OpenRouter credit) stops every engine on it

    for engine in ENGINES:
        if only and engine not in only:
            continue
        if engine in SERP_ENGINES and not cfg.get("google"):
            print(f"  {engine}: off for this site — it spends SerpApi searches; "
                  f"turn on with: {shlex.quote(sys.executable)} {shlex.quote(os.path.abspath(__file__))} {site} --google on")
            not_set_up.append(engine)
            continue
        route, key = route_for(engine, keys, router_key)
        deadline = time.monotonic() + ENGINE_BUDGET
        if not key:
            hint = f"{ROUTER_VAR} (one key for all four) or {KEY_VARS[engine]}" if engine in CHAT_ENGINES else KEY_VARS[engine]
            print(f"  {engine}: skipped — no {hint} (add it to {base_dir() / '.env'})")
            not_set_up.append(engine)
            continue
        if not queries:
            continue
        engine_ok = 0
        engine_err = None
        dead = route_dead.get(route) if route == "openrouter" else None  # the rest of the calls are skipped
        for mode in modes_for(engine, route):
            for q in queries:
                slot, n = q["slot"], samples_for(engine, q["slot"])
                ok = named = cited = searched = no_overview = 0
                no_answer_status = ""
                models, domains, errors = set(), set(), []
                for i in range(1, n + 1):
                    if dead:
                        errors.append(dead)
                        continue
                    try:
                        text, model, sources, did_search, cost = call_engine(
                            engine, mode, q["text"], cfg, key, all_keys, deadline, route)
                        if route == "openrouter":
                            run_cost.append(cost)          # None = OpenRouter reported no price
                    except EngineError as e:
                        errors.append(str(e))
                        if route == "openrouter" and e.billed:
                            run_cost.append(e.cost)          # charged all the same; None = no price given
                        if e.fatal:
                            dead = f"{e} (not retried)"
                            # Only account-wide answers stop the other assistants on the route:
                            # a bad key (401) or no credit (402). A per-model error (e.g. 404
                            # "no native search" for one model) stops that assistant alone.
                            if route == "openrouter" and e.status in (401, 402):
                                route_dead[route] = dead
                        continue
                    except Exception as e:  # noqa: BLE001 — keep the run's other rows (Rule 12: still reported)
                        errors.append(redact(f"unexpected {type(e).__name__}: {e}", all_keys)[:240])
                        continue
                    finally:
                        time.sleep(pause)
                    ok += 1
                    searched += did_search
                    no_overview += text in NO_GOOGLE_ANSWER
                    no_answer_status = NO_GOOGLE_ANSWER.get(text, "")
                    models.add(model or "?")
                    hosts = [norm_host(s) for s in sources if s]
                    domains.update(h for h in hosts if h)
                    if is_named(text, cfg["names"]):
                        named += 1
                    if any(host_matches(h, cfg["domains"]) for h in hosts):
                        cited += 1
                    try:
                        answers.mkdir(parents=True, exist_ok=True)
                        (answers / f"{engine}-{mode}-{slot}-{i}.txt").write_text(
                            f"# engine={engine} mode={mode} slot={slot} rev={q['rev']} "
                            f"model={model} searched={'yes' if did_search else 'no'} route={route}\n"
                            f"# question: {q['text']}\n\n{text}\n\n# sources:\n"
                            + "".join(f"{s}\n" for s in sources), encoding="utf-8")
                    except (OSError, UnicodeError) as e:
                        write_errors.add(f"couldn't save answer files in {answers} "
                                         f"({getattr(e, 'strerror', None) or type(e).__name__})")
                engine_ok += ok
                if errors:
                    engine_err = errors[-1]
                branded = slot == "branded"
                rows.append({
                    "date": today, "run_id": run_id, "site": site, "engine": engine,
                    "mode": mode, "slot": slot, "rev": q["rev"], "query": q["text"],
                    "model_requested": model_for(engine, route),
                    "models_reported": "|".join(sorted(models)),
                    "config_rev": config_rev(cfg), "ok": ok,
                    "named": "" if branded else named,
                    "cited_own": "" if (branded or mode == "knows") else cited,
                    "cited_domains": "|".join(sorted(domains)) if mode == "finds" else "",
                    # Engines may answer from memory even with search on; this shows how often.
                    "searched": searched if mode == "finds" else "",
                    "status": (f"{len(errors)} of {n} failed" if errors else
                               no_answer_status if no_overview and no_overview == ok else "ok"),
                    "route": route,
                })
        if engine_err:
            failed.append(engine)
            problems.append(f"{engine} FAILED: {engine_err}")
        if engine_ok:
            checked.append(engine)

    problems += sorted(write_errors)
    if rows:
        try:
            append_history(history_path(), rows)
        except OSError as e:
            problems.append(f"history write failed ({e}) — this run added nothing to the trend")

    print(f"  engines: {len(checked)} checked, {len(failed)} failed, {len(not_set_up)} not set up")
    if run_cost:
        priced = [c for c in run_cost if c is not None]
        unknown = len(run_cost) - len(priced)
        # Replies, not answers: a cut-off or empty reply is billed but is not an answer.
        print(f"  cost of this run via OpenRouter: ${sum(priced):.3f} ({len(priced)} replies"
              + (f"; cost unknown for {unknown} more)" if unknown else ")"))
    if rows:
        print(f"  answers: {answers}")
        try:
            report = build_report(domain, run_id)
            if report:
                print(f"  report:  {report}   (open it in a browser)")
        except OSError as e:
            print(f"  (couldn't write the report page: {e})")
    for p in problems:
        print(f"⚠ {p}")
    return 1 if problems else 0


# ─── trend ────────────────────────────────────────────────────────────────────

def _ratio(r):
    ok = _ok(r)
    return (int(r["named"] or 0) / ok) if ok else 0.0


def trend(domain: str) -> int:
    path, site = history_path(), normalize_site(domain)
    if not path.exists():
        print("AI check: no history yet.")
        return 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("site") == site]
    if not rows:
        print("AI check: no history for this site yet.")
        return 0
    rows.sort(key=lambda r: r["run_id"])
    # Each engine's most recent run, so a run limited with --engines doesn't hide the others;
    # the header counts only engines that are on now (key set; Google switched on).
    last_run = {}
    for r in rows:
        last_run[r["engine"]] = r["run_id"]
    last = [r for r in rows if last_run[r["engine"]] == r["run_id"]]
    cfg = load_config(domain) or {}
    keys = load_keys()
    on = {e for e in ENGINES if route_for(e, keys, setting(ROUTER_VAR))[0] and (e not in SERP_ENGINES or cfg.get("google"))}
    eng_ok = {r["engine"] for r in last if _ok(r)} & on
    eng_failed = {r["engine"] for r in last if "failed" in r.get("status", "")} & on
    print(f"═══ Does AI name you? — named / answers; ▲ = named more often ═══")
    print(f"  engines on now: {len(on)} of {len(ENGINES)}; in their latest run {len(eng_ok)} answered, "
          f"{len(eng_failed)} had failures")

    groups = {}
    for r in rows:
        groups.setdefault((r["engine"], r["mode"], r["slot"]), []).append(r)
    label = {"knows": "knows you", "finds": "finds you"}
    for (engine, mode, slot), rs in sorted(groups.items(),
                                           key=lambda kv: (ENGINES.index(kv[0][0]) if kv[0][0] in ENGINES else 9,
                                                           kv[0][1], SLOTS.index(kv[0][2]) if kv[0][2] in SLOTS else 9)):
        head = f"  {engine:<15} {label.get(mode, mode):<9} {slot:<7}"
        latest = rs[-1]
        good = [r for r in rs if _ok(r)]
        note = "" if _ok(latest) else f"  (latest attempt {latest['date']} failed: {latest['status']})"
        if slot == "branded":
            when = good[-1]["date"] if good else "never"
            print(f"{head} last answer {when} — see the answer file{note}")
            continue
        if not good:
            print(f"{head} no successful answer yet{note}")
            continue
        now = good[-1]
        if now.get("status") in NO_GOOGLE_ANSWER.values():
            print(f"{head} {NO_ANSWER_SAYS[now['status']]} ({now['date']}){note}")
            continue
        cite = f", {cite_word(now['engine'])} {now['cited_own']}/{_ok(now)}" if now.get("cited_own") not in ("", None) else ""
        if now.get("searched") not in ("", None) and int(now["searched"]) < _ok(now):
            cite += f", searched only {now['searched']}/{_ok(now)}"
        if len(good) == 1:
            print(f"{head} named {now['named']}/{_ok(now)}{cite} ({now['date']}, first){note}")
            continue
        comparable = [r for r in good[:-1] if r.get("status") not in NO_GOOGLE_ANSWER.values()]
        if not comparable:
            print(f"{head} named {now['named']}/{_ok(now)}{cite} ({now['date']}, first){note}")
            continue
        prev = comparable[-1]
        a, b = _ratio(prev), _ratio(now)
        mark = "▲" if b > a else "▼" if b < a else "→"
        causes = []
        if prev["rev"] != now["rev"] or prev["query"] != now["query"]:
            causes.append("question changed")
        if prev["models_reported"] != now["models_reported"]:
            causes.append("model changed")
        if prev["config_rev"] != now["config_rev"]:
            causes.append("settings changed")
        if (prev.get("route") or "direct") != (now.get("route") or "direct"):   # older rows had no column: all direct
            causes.append("route changed")
        dagger = f"  ‡ {', '.join(causes)} — not directly comparable" if causes else ""
        print(f"{head} named {prev['named']}/{_ok(prev)} ({prev['date']}) → "
              f"{now['named']}/{_ok(now)}{cite} ({now['date']}) {mark}{dagger}{note}")
    return 0


# ─── report (a readable page per run) ─────────────────────────────────────────

ENGINE_LABEL = {"gemini": "Gemini", "openai": "ChatGPT", "anthropic": "Claude",
                "perplexity": "Perplexity", "google-ai-mode": "Google AI Mode",
                "google-overview": "Google AI Overview"}
ENGINE_MAKER = {"gemini": "Google", "openai": "OpenAI", "anthropic": "Anthropic",
                "perplexity": "Perplexity", "google-ai-mode": "Google search",
                "google-overview": "the box above Google's results"}
MODE_LABEL = {"finds": "With web search on", "knows": "From memory"}
QUESTION_LABEL = {"broad": ("Question 1", "The everyday question"),
                  "narrow": ("Question 2", "The more specific question")}


def read_answer(path: Path):
    """(header dict, answer text, [sources]) from one saved answer file."""
    raw = path.read_text(encoding="utf-8")
    head, _, rest = raw.partition("\n\n")
    body, _, src = rest.rpartition("\n\n# sources:\n")
    if not _:
        body, src = rest, ""
    meta = dict(re.findall(r"(\w+)=(\S+)", head.splitlines()[0])) if head else {}
    return meta, body.strip(), [s for s in src.splitlines() if s.strip()]


def _light_markdown(text: str) -> str:
    """Escape an answer, then render the little markdown engines use: headings, **bold**,
    and [text](http links). Anything else stays plain text — answers are untrusted input."""
    out = []
    for line in html.escape(text.replace("\\(", "(").replace("\\)", ")")).split("\n"):
        m = re.match(r"\s*#{1,6}\s+(.*)", line)
        line = f"<strong>{m.group(1)}</strong>" if m else line
        line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
        line = re.sub(r"\[([^\]]+)\]\((https?://[^)\s\"]+)\)",
                      r'<a href="\2" rel="noopener noreferrer" target="_blank">\1</a>', line)
        out.append(line)
    return "\n".join(out)


def _mark_names(rendered: str, names) -> str:
    """Highlight the business names (case-insensitive) in the visible text only — never
    inside a tag, where "example" in href="https://example.com" would break the link."""
    alts = [re.escape(html.escape(n)) for n in sorted(names, key=len, reverse=True) if n]
    if not alts:
        return rendered
    # One pass over all names, longest first, so "Bäckerei Example" is never re-marked
    # inside by a shorter alias such as "Example".
    pat = re.compile(r"(?<!\w)(" + "|".join(alts) + r")(?!\w)", re.IGNORECASE)
    parts = [p if p.startswith("<") else pat.sub(r"<mark>\1</mark>", p)
             for p in re.split(r"(<[^>]+>)", rendered)]
    return "".join(parts)


def _link(s: str) -> str:
    e = html.escape(s)
    if re.match(r"https?://", s):
        return f'<a href="{e}" rel="noopener noreferrer" target="_blank">{html.escape(norm_host(s)) or e}</a>'
    return e


_CSS = """
:root{--bg:#f6f3ec;--card:#fffdf8;--ink:#1d1b16;--muted:#6b665c;--line:#e4ddcf;--yes:#2f6b3f;--yesbg:#e3f0e4;
--some:#8a5a00;--somebg:#fbefd4;--no:#9a3b2f;--nobg:#f6e3df;--na:#6b665c;--nabg:#efebe2;--mark:#fbe7a1}
@media (prefers-color-scheme:dark){:root{--bg:#171613;--card:#211f1b;--ink:#eee9df;--muted:#a59e90;--line:#37332c;
--yes:#8fd19e;--yesbg:#1f3325;--some:#f2c46b;--somebg:#3a2f16;--no:#f0a092;--nobg:#3a2320;--na:#a59e90;--nabg:#2a2723;
--mark:#5c4a12}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,system-ui,sans-serif}
main{max-width:920px;margin:0 auto;padding:28px 16px 64px}h1{font-size:30px;line-height:1.2;margin:0 0 6px}
h2{font-size:21px;margin:44px 0 2px}.muted{color:var(--muted)}.small{font-size:14px}
.lead{font-size:19px;margin:18px 0 6px}.q{font-size:18px;font-style:italic;margin:4px 0 14px}
.scores{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin:18px 0}
.score{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.score b{display:block;font-size:34px;line-height:1.1}.score span{color:var(--muted)}
.how{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:6px 18px;margin:18px 0}
.how li{margin:8px 0}
table{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:14px}td small{display:block;color:var(--muted);font-size:13px}
.cell{display:inline-block;padding:2px 8px;border-radius:7px;font-weight:600;font-size:14px}
.yes{background:var(--yesbg);color:var(--yes)}.some{background:var(--somebg);color:var(--some)}
.no{background:var(--nobg);color:var(--no)}.na{background:var(--nabg);color:var(--na)}
details{margin-top:10px}summary{cursor:pointer;color:var(--muted)}
.answers{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:6px 16px 14px;margin-top:8px}
.answer{white-space:pre-wrap;font-size:14px;max-height:340px;overflow:auto;border-left:3px solid var(--line);padding-left:10px;margin-top:6px}
mark{background:var(--mark);color:inherit;padding:0 2px;border-radius:3px}.sources{font-size:13px;margin-top:6px}
.sources a{color:inherit;margin-right:8px}
@media (max-width:560px){th,td{padding:8px}.score b{font-size:28px}}
"""


def _stale(r, q) -> bool:
    return q is not None and (str(r.get("rev")) != str(q["rev"]) or r.get("query") != q["text"])


def _counts(r):
    """(answered, named) for a row that counts: answered, and not Google's "no AI answer"."""
    if r is None or not _ok(r) or r.get("status") in NO_ANSWER_SAYS:
        return None
    return _ok(r), int(r.get("named") or 0)


def _cell(r, engine, mode, route=None):
    """(css class, main words, small print) for one assistant x mode on one question."""
    if r is None:
        if mode == "finds" and engine == "gemini":
            return "na", "— not asked", "Google's rules don't allow checking Gemini's web answers"
        if mode == "knows" and (engine in SERP_ENGINES or (engine == "perplexity" and route == "openrouter")):
            return "na", "—", "always searches the web"
        return "na", "—", "not checked yet"
    ok, planned = _ok(r), samples_for(engine, r["slot"])
    failed_note = f"{planned - ok} of {planned} answers failed" if "failed" in r.get("status", "") else ""
    if not ok:
        return "no", "! No answer this time", "the check couldn't get an answer; the weekly log says why"
    if r.get("status") in NO_ANSWER_SAYS:
        return "na", "— Google showed no AI answer", ""
    n = int(r["named"] or 0)
    of = f" ({n} of {ok})" if planned > 1 else ""
    if n == ok:
        cls, main = "yes", (f"✓ Named in every answer{of}" if planned > 1 else "✓ Named")
    elif n == 0:
        cls, main = "no", f"✗ Not named{of}"
    else:
        cls, main = "some", f"◐ Sometimes{of}"
    notes = [x for x in [failed_note] if x]
    if r.get("cited_own") not in ("", None) and int(r["cited_own"]):
        c = int(r["cited_own"])
        notes.append(("your website was among its search results" if engine in RESULTS_ONLY
                      else "your website was a source") + (f" ({c} of {ok})" if planned > 1 else ""))
    if r.get("searched") not in ("", None) and int(r["searched"]) < ok:
        notes.append(f"it only searched {r['searched']} of {ok} times")
    return cls, main, "; ".join(notes)


def build_report(domain: str, run_id=None):
    """Write the owner's report page (each assistant's latest answers) and return its path.

    Written for the business owner: one plain answer at the top, a short "how to read this"
    (including why each question is asked several times), one table per question, and the
    verbatim answers folded away. What counts at the top, stated once so the headline can't
    overstate: an answer to the CURRENT question, from an assistant that is ON now, that
    actually came back. "At least once" = named in at least one such answer; "every time" =
    every current question answered, and named in every answer."""
    site = normalize_site(domain)
    cfg = load_config(domain) or {"names": [site], "queries": []}
    path = history_path()
    if not path.exists():
        return None
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("site") == site]
    if not rows:
        return None
    # Each assistant's latest answer to each question, whichever run it came from: a run
    # limited with --engines must not hide the other assistants' most recent results.
    latest = {}
    for r in sorted(rows, key=lambda r: r["run_id"]):
        latest[(r["engine"], r["mode"], r["slot"])] = r
    run_id = run_id or max(r["run_id"] for r in latest.values())
    keys = load_keys()
    router = setting(ROUTER_VAR)
    # An answer in a mode the current route can't ask (Perplexity "from memory" after a switch to
    # OpenRouter) is history, not a current result.
    latest = {k: r for k, r in latest.items()
              if k[1] in modes_for(k[0], route_for(k[0], keys, router)[0] or "direct")}
    names = cfg.get("names", [])
    name = names[0] if names else site
    h = html.escape
    queries = {q["slot"]: q for q in cfg.get("queries", [])}
    scored = [s for s in QUESTION_LABEL if s in queries]
    on = [e for e in ENGINES if route_for(e, keys, router)[0] and (e not in SERP_ENGINES or cfg.get("google"))]
    engines = [e for e in on if any(k[0] == e for k in latest)]
    any_stale = False

    def answers_html(r):
        adir = geo_dir() / "answers" / site / r["run_id"]
        files = sorted(adir.glob(f"{r['engine']}-{r['mode']}-{r['slot']}-*.txt"))
        parts = []
        for i, fp in enumerate(files, 1):
            _, text, sources = read_answer(fp)
            uniq = list(dict.fromkeys(sources))           # a reply may cite the same page several times
            # The owner's own pages first: the note above this list says whether the site was in it,
            # so the list must show it even when the cap cuts the rest.
            own = [s for s in uniq if host_matches(norm_host(s), cfg.get("domains", []))]
            shown = (own + [s for s in uniq if s not in own])[:12]
            caption = "Search results returned" if r["engine"] in RESULTS_ONLY else "Sources"
            if len(uniq) > len(shown):
                caption += f" (first {len(shown)} of {len(uniq)})"
            uniq = shown
            src = (f"<div class='sources'>{caption}: " + " ".join(_link(s) for s in uniq) + "</div>") if uniq else ""
            label = f"Answer {i} of {len(files)}" if len(files) > 1 else "The answer"
            parts.append(f"<details><summary>{label}</summary>"
                         f"<div class='answer'>{_mark_names(_light_markdown(text), names)}</div>{src}</details>")
        return "".join(parts) or "<p class='muted small'>No answer saved.</p>"

    def earlier_note(r, q):
        return (f"<p class='muted small'>* Answer from {h(r['date'])} to an earlier version of the question: "
                f"“{h(r.get('query', ''))}”</p>") if _stale(r, q) else ""

    # ── the plain answer at the top ──
    def tally(mode):
        """(named at least once, named every time for every question, assistants with an answer)."""
        at_least, every, answering = 0, 0, 0
        for e in engines:
            counts = [None if r is None or _stale(r, queries[s]) else _counts(r)
                      for s in scored for r in [latest.get((e, mode, s))]]
            known = [c for c in counts if c]
            if not known:
                continue
            answering += 1
            at_least += any(n > 0 for _, n in known)
            every += len(known) == len(scored) and all(n == ok for ok, n in known)
        return at_least, every, answering
    f_any, f_all, f_m = tally("finds")
    k_any, _, k_m = tally("knows")
    scores, lines = [], []
    if f_m:
        scores.append(f"<div class='score'><b>{f_any} of {f_m}</b><span>AI assistants named you at least once "
                      f"<strong>with web search on</strong>" + ("" if f_all == f_any else
                      f"; {f_all} in every answer to every question") + "</span></div>")
        lines.append("With web search on, none of them named you yet. The tables below show who they named instead."
                     if f_any == 0 else
                     "With web search on, all of them named you in every answer to every question."
                     if f_all == f_m else
                     "With web search on, they named you, but not always and not for every question. "
                     "The tables below show where you're missing.")
    if k_m:
        scores.append(f"<div class='score'><b>{k_any} of {k_m}</b><span>named you at least once "
                      f"<strong>from memory</strong>, without looking anything up</span></div>")
        lines.append("From memory, none of them named you yet. That's normal for most small businesses, and it "
                     "changes slowly." if k_any == 0 else
                     f"From memory, {k_any} of {k_m} named you at least once: that's the long-term goal.")

    # ── one table per scored question ──
    sections = []
    for slot in scored:
        title, kind = QUESTION_LABEL[slot]
        q = queries[slot]
        rows_html, reads = [], []
        for e in engines:
            cells = []
            for mode in ("finds", "knows"):
                r = latest.get((e, mode, slot))
                cls, main, note = _cell(r, e, mode, route_for(e, keys, router)[0])
                star = ""
                if r is not None and _stale(r, q):
                    star, any_stale = " *", True
                cells.append(f"<td><span class='cell {cls}'>{h(main)}{star}</span>"
                             + (f"<small>{h(note)}</small>" if note else "") + "</td>")
                if r is not None and _ok(r):
                    reads.append(f"<details><summary>{h(ENGINE_LABEL[e])} · {h(MODE_LABEL[mode].lower())}</summary>"
                                 f"{earlier_note(r, q)}{answers_html(r)}</details>")
            maker = ENGINE_MAKER[e] if ENGINE_MAKER[e] != ENGINE_LABEL[e] else ""
            rows_html.append(f"<tr><td><strong>{h(ENGINE_LABEL[e])}</strong>"
                             + (f"<small>{h(maker)}</small>" if maker else "") + f"</td>{''.join(cells)}</tr>")
        sections.append(
            f"<h2>{h(title)}</h2><p class='muted small'>{h(kind)}</p><p class='q'>“{h(q['text'])}”</p>"
            f"<table><tr><th>AI assistant</th><th>{h(MODE_LABEL['finds'])}</th><th>{h(MODE_LABEL['knows'])}</th></tr>"
            f"{''.join(rows_html)}</table>"
            + (f"<details><summary><strong>Read what they said</strong></summary><div class='answers'>"
               f"{''.join(reads)}</div></details>" if reads else ""))

    # ── the branded question: read, not scored ──
    branded = queries.get("branded")
    if branded:
        reads = [f"<details><summary>{h(ENGINE_LABEL[e])} · {h(MODE_LABEL[m].lower())}</summary>"
                 f"{earlier_note(r, branded)}{answers_html(r)}</details>"
                 for e in engines for m in ("finds", "knows")
                 for r in [latest.get((e, m, "branded"))] if r is not None and _ok(r)]
        if reads:
            sections.append(
                f"<h2>Do they describe you correctly?</h2><p class='q'>“{h(branded['text'])}”</p>"
                f"<p class='small'>Here your name is in the question, so these answers don't count toward the "
                f"numbers above. Read them to see whether each assistant gets your business right.</p>"
                f"<div class='answers'>{''.join(reads)}</div>")

    dates = sorted({r["date"] for r in latest.values()})
    when = dates[-1] if len(dates) == 1 else f"{dates[0]} to {dates[-1]}"
    not_set_up = [ENGINE_LABEL[e] for e in ENGINES if e not in engines]
    via_router = [ENGINE_LABEL[e] for e in engines
                  if any(r.get("route") == "openrouter" for k, r in latest.items() if k[0] == e)]
    n_ask = SAMPLES["broad"]
    google_line = (" Google's AI is asked once per question, because each lookup costs a paid search."
                   if any(e in SERP_ENGINES for e in engines) else "")
    # The Google & Bing report (search_report.py) lives beside this folder; link to it when it
    # exists. search_report.py rebuilds the newest AI page after writing its own, so the link
    # appears without waiting for the next AI check.
    google_link = ""
    if (base_dir() / "reports" / site / "google.html").exists():
        google_link = (f'<p>Also see: <a href="../../../reports/{h(site)}/google.html">How people find you '
                       f'on Google</a> — visits, positions and searches, week by week.</p>')
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Do AI assistants name {h(name)}?</title>
<style>{_CSS}</style></head><body><main>
<h1>Do AI assistants name {h(name)}?</h1>
<p class="muted">{h(site)} · answers from {h(when)}</p>
<div class="scores">{''.join(scores)}</div>
{''.join(f'<p class="lead">{h(l)}</p>' for l in lines)}
<div class="how"><p><strong>How to read this</strong></p><ul>
<li>We asked each AI assistant the kind of question a new customer would ask, <strong>without your name in it</strong>,
and checked whether your name appears in the answer.</li>
<li><strong>With web search on</strong>: the assistant may look things up first, as most do today.
<strong>From memory</strong>: it answers only from what it learned in training.</li>
<li>AI assistants can write a <strong>different answer each time</strong>, even to the same question. So we ask each one
<strong>{n_ask} times</strong>: “{n_ask} of {n_ask}” means you were named in every answer, “1 of {n_ask}” only
sometimes.{google_line}</li>
</ul></div>
{''.join(sections)}
{google_link}
<h2>What next?</h2>
<p>Want AI assistants to name you more often? Ask Claude: <em>“How can I get AI assistants to recommend my
business?”</em></p>
<p class="muted small">{'* = this answer was to an earlier version of the question; the next weekly check asks the new one. ' if any_stale else ''}{('Not set up: ' + ', '.join(not_set_up) + '. ') if not_set_up else ''}{('Asked through OpenRouter, which uses each assistant’s own web search: ' + ', '.join(via_router) + '. ') if via_router else ''}Each weekly check writes a new page like this one. To see the latest,
ask Claude: “Show me my AI report for {h(site)}.” Every answer is also saved as a text file under {h(str(geo_dir() / "answers" / site))}.</p>
</main></body></html>"""
    out = geo_dir() / "reports" / site / f"{run_id}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


# ─── CLI ──────────────────────────────────────────────────────────────────────

ROUTER_HINT = "openrouter.ai → Credits: prepay 5–10 USD/EUR → Keys → Create Key (one key for all four)"
ENV_HINTS = {
    "gemini": "aistudio.google.com → Get API key (free; in the EU/UK/CH also turn on billing)",
    "openai": "platform.openai.com → add credit under Billing → API keys → Create",
    "anthropic": "console.anthropic.com → add credit under Billing → API Keys → Create Key",
    "perplexity": "perplexity.ai → Settings → API → add credit → Generate API key",
    "google-ai-mode": "serpapi.com → Dashboard → Your Private API Key (shared with the Top-10 check)",
    "google-overview": "the same SERPAPI_KEY as google-ai-mode",
}


def show_keys() -> int:
    """Which engines have a key — never the values. For the owner walkthrough."""
    keys = load_keys()
    router = setting(ROUTER_VAR)
    print(f"Key file: {base_dir() / '.env'}")
    print(f"  {ROUTER_VAR:<24} {'set ✓' if router else 'empty — ' + ROUTER_HINT}  "
          f"(the default route for {', '.join(CHAT_ENGINES)})")
    direct = direct_engines()
    if direct:
        unknown = sorted(direct - set(CHAT_ENGINES))
        named = [e for e in CHAT_ENGINES if e in direct]
        own = [e for e in named if route_for(e, keys, router)[0] == "direct"]
        print(f"  {DIRECT_VAR:<24} {', '.join(named) or '—'} named; using their own key: {', '.join(own) or 'none'}"
              + (f"  ⚠ not a chat assistant: {', '.join(unknown)}" if unknown else ""))
    for var in dict.fromkeys(KEY_VARS.values()):          # SERPAPI_KEY serves two engines
        engines = [e for e in ENGINES if KEY_VARS[e] == var]
        if router and engines[0] in direct and engines[0] in CHAT_ENGINES:
            state = ("set ✓, used instead of OpenRouter" if keys[engines[0]]
                     else f"empty — named in {DIRECT_VAR}, so OpenRouter is used until a key is added")
        elif router and engines[0] in CHAT_ENGINES:
            state = ("set, not used: OpenRouter is set" if keys[engines[0]] else "not needed: OpenRouter is set")
        else:
            state = "set ✓" if keys[engines[0]] else f"empty — {ENV_HINTS[engines[0]]}"
        print(f"  {var:<24} {state}  ({', '.join(engines)})")
    return 0


def prepare_env() -> int:
    """Add the empty GEO_* lines to the shared .env (never touching existing lines),
    so the owner only pastes each key after its = sign."""
    env = base_dir() / ".env"
    env.parent.mkdir(parents=True, exist_ok=True)
    text = env.read_text(encoding="utf-8") if env.exists() else ""
    names = [ROUTER_VAR, "SERPAPI_KEY", KEY_VARS["gemini"]]   # the default route, Google's AI, the free Gemini option
    missing = [v for v in names
               if not re.search(r"(?m)^\s*(?:export\s+)?" + v + r"\s*=", text)]
    if missing:
        block = ("\n# Weekly AI check (does AI name you?) — paste each key after the = sign,\n"
                 "# no spaces, no quotes. GEO_OPENROUTER_API_KEY is one key for ChatGPT, Claude,\n"
                 "# Gemini and Perplexity; SERPAPI_KEY is only for Google's AI (optional);\n"
                 "# GEO_GEMINI_API_KEY is the free way to start (Gemini 'from memory' only).\n"
                 + "".join(f"{v}=\n" for v in missing))
        with open(env, "a", encoding="utf-8") as f:
            f.write(("" if not text or text.endswith("\n") else "\n") + block)
        os.chmod(env, 0o600)
    print(f"Key file: {env}")
    print("  (the folder .config is hidden in Finder: Go → Go to Folder… → ~/.config/gsc-insights)")
    print(f"  {'added' if missing else 'already has'} the lines: {', '.join(names)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("domain", nargs="?")
    cmd = ap.add_mutually_exclusive_group()
    for c in ("init", "set-names", "set-question", "check-drift", "confirm", "trend",
              "keys", "prepare-env", "report"):
        cmd.add_argument(f"--{c}", action="store_true")
    ap.add_argument("--name")
    ap.add_argument("--legal-name")
    ap.add_argument("--alias", action="append", default=None)
    ap.add_argument("--domain", dest="domains", action="append", default=None)
    ap.add_argument("--lang")
    ap.add_argument("--country")
    ap.add_argument("--slot", choices=SLOTS)
    ap.add_argument("--expect", help="with --confirm: the page code --check-drift printed")
    ap.add_argument("--text-file")
    cmd.add_argument("--google", choices=["on", "off"],
                    help="ask Google's AI Mode + AI Overview for this site (spends SerpApi searches)")
    ap.add_argument("--engines", help="comma-separated: ask only these engines this run "
                    f"(of {', '.join(ENGINES)})")
    args = ap.parse_args(argv)
    if args.expect and not args.confirm:
        ap.error("--expect only goes with --confirm")
    if args.keys:
        return show_keys()
    if args.prepare_env:
        return prepare_env()
    domain = args.domain
    if not domain:
        ap.error("a domain is required (e.g. example.com)")

    if args.trend:
        return trend(domain)

    if args.report:
        out = build_report(domain)
        if not out:
            print("AI check: no results yet for this site — run it first.")
            return 3
        print(f"Report: {out}")
        if sys.platform == "darwin" and os.environ.get("GEO_TEST_MODE") != "1":
            subprocess.run(["open", str(out)], check=False)
        return 0

    if args.init:
        if load_config(domain):
            print(f"✗ Already set up: {config_path(domain)} — use --set-names to change it.")
            return 1
        if not (args.name and args.lang and args.country):
            ap.error("--init needs --name, --lang and --country")
        cfg = {"names": [n for n in [args.name, args.legal_name, *(args.alias or [])] if n],
               "domains": sorted({norm_host(d) for d in (args.domains or [domain])}),
               "lang": args.lang, "country": _country(args.country), "queries": [],
               "google": False}   # Google's paid checks start off; --google on after asking
        save_config(domain, cfg)
        print(f"✓ AI check set up for {normalize_site(domain)}: {config_path(domain)}")
        print("  Next: add the questions with --set-question, then --check-drift and --confirm --expect <page code>.")
        return 0

    cfg = load_config(domain)
    if cfg is None:
        print("AI check: not set up (ask Claude: 'set up the weekly AI check')")
        return 3

    if args.google:
        cfg["google"] = args.google == "on"
        save_config(domain, cfg)
        print(f"✓ Google AI Mode + AI Overview {'on' if cfg['google'] else 'off'} for {normalize_site(domain)}"
              + (" — each weekly run spends 6–9 SerpApi searches." if cfg["google"] else "."))
        return 0

    if args.set_names:
        if args.name:  # a new main name replaces the list: name, legal name, aliases
            cfg["names"] = [n for n in [args.name, args.legal_name, *(args.alias or [])] if n]
        else:          # otherwise --legal-name/--alias ADD to the names already there
            for n in [args.legal_name, *(args.alias or [])]:
                if n and n not in cfg["names"]:
                    cfg["names"].append(n)
        if args.domains:
            cfg["domains"] = sorted({norm_host(d) for d in args.domains})
        if args.lang:
            cfg["lang"] = args.lang
        if args.country:
            cfg["country"] = _country(args.country)
        save_config(domain, cfg)
        print(f"✓ Updated. The next trend line marks this as 'settings changed'.")
        return 0

    if args.set_question:
        if not (args.slot and args.text_file):
            ap.error("--set-question needs --slot and --text-file (a path, or - for stdin)")
        text = (sys.stdin.read() if args.text_file == "-" else
                Path(args.text_file).read_text(encoding="utf-8")).strip()
        if not text:
            ap.error("the question text is empty")
        qs = [q for q in cfg.get("queries", []) if q["slot"] != args.slot]
        old = next((q for q in cfg.get("queries", []) if q["slot"] == args.slot), None)
        rev = (old["rev"] + 1) if old else 1
        qs.append({"slot": args.slot, "rev": rev, "text": text,
                   "saved": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
        cfg["queries"] = sorted(qs, key=lambda q: SLOTS.index(q["slot"]))
        save_config(domain, cfg)
        print(f"✓ {args.slot} question saved (rev {rev}): {text}")
        print("  When all questions are reviewed: --check-drift, then --confirm --expect <page code>.")
        return 0

    if args.check_drift or args.confirm:
        state, detail = drift(domain, cfg)
        if state == "unreadable":
            print(f"⚠ Couldn't read the homepage: {detail}")
            if args.confirm:
                print("✗ Not saved — confirm only against the real page.")
                return 1
            return 0
        print("Homepage (title | description | H1):")
        print("  " + detail.replace("\n", " | "))
        if args.check_drift:
            if state == "changed":
                print(f"Confirmed on: {cfg.get('fingerprint_text', '').replace(chr(10), ' | ')}")
            print(f"State: {state}")
            for q in cfg.get("queries", []):
                print(f"  {q['slot']:<7} rev {q['rev']}: {q['text']}")
            print(f"Page code: {fingerprint(detail)}  (to save this title/description/heading: "
                  f"--confirm --expect {fingerprint(detail)})")
            return 0
        # Save only the page a person previewed with --check-drift: its code must still match,
        # so an intermittent bot wall can't slip in between the preview and the save.
        if args.expect != fingerprint(detail):
            print(f"✗ Not saved — {'no --expect code given' if not args.expect else 'the code does not match the current page (it changed since the preview, or the code was mistyped)'}. "
                  f"Run --check-drift, read the text with the owner, then --confirm --expect <its page code>.")
            return 1
        cfg["fingerprint"] = fingerprint(detail)
        cfg["fingerprint_text"] = detail
        cfg["confirmed_questions"] = _question_set(cfg)   # the set this homepage was checked against
        cfg["confirmed"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        save_config(domain, cfg)
        print("✓ Confirmed — these questions now match this homepage.")
        return 0

    only = None
    if args.engines:
        only = {e.strip() for e in args.engines.split(",") if e.strip()}
        unknown = only - set(ENGINES)
        if unknown:
            ap.error(f"unknown engine(s): {', '.join(sorted(unknown))} — choose from {', '.join(ENGINES)}")
    return run(domain, only)


if __name__ == "__main__":
    sys.exit(main())
