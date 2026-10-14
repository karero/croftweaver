#!/usr/bin/env python3
"""
fix_proposal.py — the weekly fix proposal: choosing it, the owner's answers, following it.

    fix_proposal.py show <site>
    fix_proposal.py decline <site> [--reason owner|positioning] [--page <address>]
    fix_proposal.py acted <site> --pr <pull request address> --new-title "<the built page's whole <title>>" [--page <address>]
    fix_proposal.py set <site> brand "<spelling>, <spelling>"
    fix_proposal.py set <site> pr_figures yes|no

The rules are in docs/reviews/SKILL-PLAN-scheduled-search-fixes.md (the requirements, R1 to R6,
scenarios 1 to 9) and docs/reviews/DESIGN-weekly-fix-proposal.md (§3). In short: code picks at
most one proposal per report, from the numbers (striking distance, T1); the owner's assistant
makes the edit and records it here with these commands, never by editing the file; the report
then follows the pull request and the live page, and measures one search before and after.

State lives in ~/.config/gsc-insights/sites/<site>-proposals.json, beside the settings file the
weekly job rewrites on every run (so nothing of the owner's is kept there). Every write is
atomic. This file calls no model and makes no network request except `gh` in gh_pr_state().
"""
import argparse
import contextlib
import datetime as dt
import fcntl
import html.parser
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _history import NOISE_IMPRESSIONS, normalize_site  # noqa: E402
from _lang_normalize import fold, words_of  # noqa: E402

T1_MIN_IMPRESSIONS = 50             # D3
T1_POSITION = (8.0, 20.0)           # striking distance, both ends included
DECLINE_DAYS = 12 * 7               # D3: a "no" holds for 12 weeks
WINDOW_DAYS = 28                    # four full weeks, Monday to Sunday

# Left out of the "already on the page" word check (design §3.2). Folded, so "für" is "fuer".
STOP_WORDS = frozenset(fold(w) for w in (
    "der die das den dem des ein eine und oder in im am an auf für mit von zu bei "
    "the a an and or in on at for of to with near").split())


# ─── state ─────────────────────────────────────────────────────────────────────────────────

def _today() -> dt.date:
    """Today's date; one place, so a test can hold the clock still."""
    return dt.date.today()


def base_dir() -> Path:
    return Path(os.path.expanduser("~")) / ".config" / "gsc-insights"


# A bare domain: labels of letters, digits and inner hyphens, at least one dot. Anything else
# (a path, "..", a slash) is refused, so the state file can only land in sites/.
_DOMAIN = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+")


def state_path(site: str) -> Path:
    name = normalize_site(site)
    if not _DOMAIN.fullmatch(name):
        raise ValueError(f"not a bare domain: {site!r}")
    return base_dir() / "sites" / f"{name}-proposals.json"


@contextlib.contextmanager
def locked(site: str):
    """Hold the site's lock while its state is read, changed and written, so the weekly report
    and the assistant's commands never write over each other's changes (a "no" lost that way
    would bring the proposal back)."""
    p = state_path(site)
    base_dir().mkdir(parents=True, exist_ok=True)
    # Beside the settings, not in sites/: a site that never had a proposal gets no file there.
    with open(base_dir() / f".{p.name[:-len('.json')]}.lock", "a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Waiting for the weekly report to finish with this site …", file=sys.stderr)
            fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def empty_state(site: str) -> dict:
    return {"version": 1, "site": normalize_site(site), "brand": None, "pr_figures": "unasked",
            "current": None, "proposals": {}, "done": []}


def load_state(site: str) -> dict:
    """The site's state, or a fresh one. A file that cannot be read as a state is an error, not a
    fresh start: starting over would forget the owner's "no" and re-propose what they turned down."""
    p = state_path(site)
    if not p.exists():
        return empty_state(site)
    s = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(s, dict) or not isinstance(s.get("proposals"), dict):
        raise ValueError(f"{p} is not a proposals file")
    base = empty_state(site)
    base.update(s)
    return base


def save_state(site: str, state: dict) -> Path:
    p = state_path(site)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".proposals-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as o:
            json.dump(state, o, ensure_ascii=False, indent=1)
        os.replace(tmp, p)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return p


# ─── brand ─────────────────────────────────────────────────────────────────────────────────

def default_brand(site: str) -> list:
    """The guess shown until the owner confirms spellings (DD5): the domain's first label with
    hyphens as spaces and as nothing ("radwerk-plagwitz.example" → "radwerk plagwitz",
    "radwerkplagwitz")."""
    label = normalize_site(site).split("/")[0]
    if label.startswith("www."):
        label = label[4:]
    parts = [p for p in label.split(".")[0].split("-") if p]
    out = []
    for s in (" ".join(parts), "".join(parts)):
        if s and s not in out:
            out.append(s)
    return out


def brand_spellings(state: dict, site: str) -> tuple:
    """(spellings, confirmed)."""
    b = state.get("brand")
    if isinstance(b, list) and b:
        return b, True
    return default_brand(site), False


def is_brand(query: str, spellings) -> bool:
    """A query names the business when a spelling's words appear in it in order, or when the
    spelling run together (at least 6 letters, so short names cannot match by accident) appears
    in the query run together: "radwerk-plagwitz öffnungszeiten" and "radwerkplagwitz" both match
    "radwerk plagwitz"."""
    qw = words_of(query)
    qsolid = "".join(qw)
    for sp in spellings:
        sw = words_of(sp)
        if not sw:
            continue
        n = len(sw)
        if any(qw[i:i + n] == sw for i in range(len(qw) - n + 1)):
            return True
        solid = "".join(sw)
        if len(solid) >= 6 and solid in qsolid:
            return True
    return False


# ─── the page ──────────────────────────────────────────────────────────────────────────────

class _PageParser(html.parser.HTMLParser):
    """The page's <title>, its first <h1> and its first paragraph with text, as plain text.
    The first paragraph inside <main> wins when the page has one, so a cookie or header
    paragraph does not stand in for the page's own first paragraph."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = self.h1 = None
        self.p_main = self.p_any = None
        self._open = None          # "title" | "h1" | "p"
        self._buf = []
        self._main = 0

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self._main += 1
        elif tag in ("title", "h1", "p") and self._open is None:
            self._open, self._buf, self._in_main = tag, [], self._main > 0

    def handle_endtag(self, tag):
        if tag == "main":
            self._main = max(0, self._main - 1)
        elif tag == self._open:
            text = " ".join("".join(self._buf).split())
            if tag == "title" and self.title is None:
                self.title = text
            elif tag == "h1" and self.h1 is None:
                self.h1 = text
            elif tag == "p" and text:
                if self._in_main and self.p_main is None:
                    self.p_main = text
                if self.p_any is None:
                    self.p_any = text
            self._open = None

    def handle_data(self, data):
        if self._open:
            self._buf.append(data)


def parse_page(text: str) -> dict:
    """{"title", "h1", "first_paragraph"}; any of them may be None."""
    p = _PageParser()
    p.feed(text or "")
    p.close()
    return {"title": p.title, "h1": p.h1, "first_paragraph": p.p_main or p.p_any}


def query_on_page(query: str, page: dict) -> bool:
    """True when every word of the query appears in the title, the H1 and the first paragraph
    taken together (design §3.2): as a whole word, folded, or written together with its
    neighbours as one word, the way German writes compounds ("fahrrad reparatur" is on a page
    that says "Fahrradreparatur"). Short words count ("ki"); only STOP_WORDS are left out. A
    query with no word left is never "already on the page"."""
    want = [w for w in words_of(query) if w not in STOP_WORDS]
    if not want:
        return False
    have = set(words_of(" ".join(page.get(k) or "" for k in ("title", "h1", "first_paragraph"))))
    # covered[i]: the first i words are carried, each alone or run together with its neighbours.
    # Every split is tried, so a page that has both "fahrrad" and "fahrradreparatur" still counts.
    covered = [True] + [False] * len(want)
    for i in range(len(want)):
        if covered[i]:
            for j in range(i + 1, len(want) + 1):
                if "".join(want[i:j]) in have:
                    covered[j] = True
    return covered[-1]


def norm_title(t) -> str:
    return " ".join(fold(t or "").split())


def classify_title(fetched, old: str, new: str) -> str:
    """One weekly look at the live page (design §3.4): "new", "old", "other" (a readable title
    that is neither) or "unreadable" (pass None for a timeout, an error, a non-200 answer or a
    page without a <title>). Whole titles are compared, folded, spaces collapsed."""
    if fetched is None:
        return "unreadable"
    f = norm_title(fetched)
    if f == norm_title(new):
        return "new"
    if f == norm_title(old):
        return "old"
    return "other"


# ─── choosing (T1) ─────────────────────────────────────────────────────────────────────────

def proposal_key(page: str, query: str) -> str:
    return f"T1|{page}|{query}"


def t1_candidates(query_rows, query_page_rows, spellings) -> list:
    """Striking-distance searches, strongest first. `query_rows` are the window's ["query"] rows
    (position by property), `query_page_rows` its ["query", "page"] rows. A search whose page
    cannot be proved from the rows is left out: it is never guessed."""
    pages, page_total = {}, {}
    for r in query_page_rows:
        q, page = r["keys"][0], r["keys"][1]
        imp = r.get("impressions", 0)
        if q not in pages or imp > pages[q][1]:
            pages[q] = (page, imp)
        if not is_brand(q, spellings):
            page_total[page] = page_total.get(page, 0) + imp
    out = []
    for r in query_rows:
        q = r["keys"][0]
        pos, imp = r.get("position"), r.get("impressions", 0)
        if pos is None or not (T1_POSITION[0] <= pos <= T1_POSITION[1]) or imp < T1_MIN_IMPRESSIONS:
            continue
        if is_brand(q, spellings) or q not in pages:
            continue
        page, on_page = pages[q]
        if page_total.get(page, 0) < NOISE_IMPRESSIONS:   # R1: the page's own non-brand floor
            continue
        out.append({"kind": "T1", "query": q, "page": page, "position": pos, "impressions": imp,
                    "clicks": r.get("clicks", 0), "page_impressions": on_page})
    out.sort(key=lambda c: (-c["impressions"], c["query"]))
    return out


def _date(s):
    return dt.date.fromisoformat(s) if s else None


def has_check(rec, outcome) -> bool:
    return any(c.get("outcome") == outcome for c in rec.get("checks", []))


def page_block(rec: dict) -> str:
    """Why this record keeps its page out of new proposals, or "" (R1: an open pull request, one
    merged but not seen live, a measuring not finished). Nothing here is released by a timer."""
    pr = rec.get("pr")
    if not pr or rec.get("declined_on"):
        return ""          # a "no" (in words or by closing the pull request) frees the page
    state = (pr.get("state") or "").upper()
    if state == "OPEN":
        return "pull request open"      # R1 holds even after a result, while it is still open
    if rec.get("result"):
        return ""
    if has_check(rec, "new"):
        return "measuring"
    if state == "MERGED":
        return "merged, not seen live yet"
    return "pull request open"


def declined_until(rec: dict):
    d = _date(rec.get("declined_on"))
    return d + dt.timedelta(days=DECLINE_DAYS) if d else None


def blocked(state: dict, cand: dict, today: dt.date) -> str:
    """Why `cand` may not be proposed today, or ""."""
    for key, rec in state["proposals"].items():
        if rec.get("page") == cand["page"]:
            why = page_block(rec)
            if why:
                return why
    rec = state["proposals"].get(proposal_key(cand["page"], cand["query"]))
    if rec:
        until = declined_until(rec)
        if until and today < until:
            return f"turned down until {until.isoformat()}"
    return ""


def choose(candidates, state: dict, today: dt.date, read_page):
    """The one proposal for this report, and a note per candidate passed over.

    `read_page(url)` returns parse_page()'s dict, or None when the page could not be read (a
    timeout, an error, a non-200 answer, no <title>). Only the first candidate that survives
    every check is fetched beyond it, so a report reads at most a few of the owner's pages."""
    notes = []
    for c in candidates:
        why = blocked(state, c, today)
        if why:
            notes.append((c["query"], why))
            continue
        page = read_page(c["page"])
        if page is None or not page.get("title"):
            notes.append((c["query"], "the page could not be read"))
            continue
        if query_on_page(c["query"], page):
            notes.append((c["query"], "already on the page"))
            continue
        return dict(c, old_title=page["title"]), notes
    return None, notes


def record_shown(state: dict, proposal: dict, window, today: dt.date) -> dict:
    """Keep the report's proposal as the current one. The choosing counts as the first look at
    the live page: the title was the old one on that day."""
    key = proposal_key(proposal["page"], proposal["query"])
    rec = state["proposals"].get(key) or {}
    if rec.get("result") or rec.get("declined_on"):
        # The same search, proposed again after an earlier round finished (measured, or turned
        # down and its 12 weeks over): that round keeps its own record, this one starts fresh.
        state.setdefault("done", []).append(rec)
        rec = {}
    rec.update({k: proposal[k] for k in ("kind", "query", "page", "position", "impressions",
                                          "clicks", "page_impressions", "old_title")})
    rec.setdefault("shown", today.isoformat())
    rec["last_shown"] = today.isoformat()
    rec["window"] = [window[0].isoformat(), window[1].isoformat()]
    if not rec.get("pr"):
        rec["checks"] = [{"date": today.isoformat(), "outcome": "old"}]
    state["proposals"][key] = rec
    state["current"] = key
    return rec


def sentence(proposal: dict) -> str:
    """What the owner says to their assistant (design §3.3): the skill's slash command first, then
    the search, every place and the page. The slash form, because a cold Claude Code session given
    the plain name went straight to the page files without loading the skill (2026-10-14); Codex
    loaded it either way."""
    return (f"/search-console-insights work '{proposal['query']}' into the title, heading and "
            f"first paragraph of {proposal['page']}")


# ─── following the pull request ────────────────────────────────────────────────────────────

_PR_URL = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/pull/([0-9]+)/?")


def parse_pr_url(url: str):
    """("owner/name", number) from a GitHub pull request address; ValueError otherwise."""
    m = _PR_URL.fullmatch((url or "").strip())
    if not m:
        raise ValueError(f"not a GitHub pull request address: {url!r}")
    return m.group(1), int(m.group(2))


def gh_pr_state(repo: str, number: int, run=subprocess.run):
    """GitHub's answer for one pull request ({"state", "mergedAt", "closedAt"}), or None when `gh`
    is missing, not signed in, or answers with something else. None changes nothing."""
    try:
        p = run(["gh", "pr", "view", str(number), "--repo", repo, "--json", "state,mergedAt,closedAt"],
                capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    try:
        j = json.loads(p.stdout)
    except ValueError:
        return None
    return j if isinstance(j, dict) and j.get("state") in ("OPEN", "CLOSED", "MERGED") else None


def apply_pr_state(rec: dict, gh, today=None) -> dict:
    """Fold GitHub's answer into the record (design §3.4). Closed without merging is the owner's
    "not this one" from the day it closed (today when GitHub gives no day); reopened or merged
    after all takes that back; merged waits to go live. No answer (None) keeps the last known
    state and marks this week's check as failed, so the page can say so."""
    pr = rec.setdefault("pr", {})
    if not gh:
        pr["last_check_ok"] = False
        return rec
    pr["last_check_ok"] = True
    pr["state"] = gh["state"]
    if gh["state"] in ("OPEN", "MERGED") and rec.get("decline_reason") == "closed":
        rec.pop("declined_on", None)
        rec.pop("decline_reason", None)
    if gh["state"] == "MERGED":
        pr["merged_at"] = gh.get("mergedAt")
    elif gh["state"] == "CLOSED" and rec.get("decline_reason") != "closed":
        closed = (gh.get("closedAt") or "")[:10] or (today or _today()).isoformat()
        rec["declined_on"], rec["decline_reason"] = closed, "closed"
    return rec


# ─── live, and the windows ─────────────────────────────────────────────────────────────────

def last_sunday_before(d: dt.date) -> dt.date:
    """The last Sunday strictly before `d`."""
    back = (d.weekday() + 1) % 7 or 7
    return d - dt.timedelta(days=back)


def first_monday_on_or_after(d: dt.date) -> dt.date:
    return d + dt.timedelta(days=(7 - d.weekday()) % 7)


def windows(checks) -> dict:
    """The before and after windows from the weekly looks at the live page (DD8), or None until
    the page has been seen with its new title.

    Both edges are fixed at the first "new" check: before = the four full weeks ending on the last
    Sunday before the last "old" check that came before it; after = the four full weeks starting on
    the first Monday on or after it. A later "old" or "other" interrupts: the after-window then
    ends on the last Sunday before that check, and `weeks` says how many full weeks are left (0 =
    none, nothing to show). "unreadable" checks change nothing."""
    # Sorted by day; checks of the same day keep the order they were made in (sorted is stable),
    # so an "old" look in the morning and a "new" one after the change went live both count.
    cs = sorted((c for c in checks if c.get("outcome") in ("old", "new", "other")),
                key=lambda c: c["date"])
    i_new = next((i for i, c in enumerate(cs) if c["outcome"] == "new"), None)
    if i_new is None:
        return None
    fn = _date(cs[i_new]["date"])
    olds = [_date(c["date"]) for c in cs[:i_new] if c["outcome"] == "old"]
    if not olds:
        return None
    b_end = last_sunday_before(max(olds))
    a_start = first_monday_on_or_after(fn)
    a_end = a_start + dt.timedelta(days=WINDOW_DAYS - 1)
    interrupted = next((_date(c["date"]) for c in cs[i_new + 1:] if c["outcome"] in ("old", "other")), None)
    if interrupted:
        a_end = min(a_end, last_sunday_before(interrupted))
    weeks = max(0, ((a_end - a_start).days + 1) // 7)
    return {"before": (b_end - dt.timedelta(days=WINDOW_DAYS - 1), b_end),
            "after": (a_start, a_start + dt.timedelta(days=weeks * 7 - 1)) if weeks else None,
            "weeks": weeks, "interrupted": interrupted.isoformat() if interrupted else None}


def ready_to_measure(w: dict, finished: dt.date) -> bool:
    """The comparison is fetched once Google's complete data (R1) reaches the after-window's end."""
    return bool(w and w["after"] and finished >= w["after"][1])


# ─── the commands ──────────────────────────────────────────────────────────────────────────

def _target(state: dict, page=None):
    """The record a command acts on: the one for `page` when given (the newest shown), else the
    report's current proposal, else the newest one still in progress (acted on, not measured, not
    turned down). After the owner acts, the next report has no current proposal for that page, so
    a later "no" or a corrected title still finds its record."""
    recs = state["proposals"]
    if page:
        found = [(k, r) for k, r in recs.items() if r.get("page") == page.strip()]
        if not found:
            raise SystemExit(f"No proposal for {page} on record.")
        return max(found, key=lambda kr: kr[1].get("last_shown") or "")
    key = state.get("current")
    if key and recs.get(key):
        return key, recs[key]
    waiting = [(k, r) for k, r in recs.items() if r.get("pr") and not r.get("result") and not r.get("declined_on")]
    if waiting:
        return max(waiting, key=lambda kr: kr[1].get("last_shown") or "")
    raise SystemExit("There is no proposal for this site yet. Open the weekly report first.")


def cmd_show(site, args):
    state = load_state(site)
    spellings, confirmed = brand_spellings(state, site)
    try:
        key, rec = _target(state)
    except SystemExit:
        rec = None
    print(f"Site: {normalize_site(site)}")
    print(f"Counted as your business name: {', '.join(spellings)}" + ("" if confirmed else " (a guess, not confirmed)"))
    print(f"Search figures in pull requests: {state.get('pr_figures', 'unasked')}")
    if not rec:
        print("Proposal: none")
        return 0
    print(f"Proposal: work '{rec['query']}' into the title, heading and first paragraph of {rec['page']}")
    print(f"Window: {rec['window'][0]} to {rec['window'][1]}")
    print(f"Figures: average position {rec['position']:.1f}, {rec['impressions']} impressions, "
          f"{rec['page_impressions']} of them on this page")
    print(f"Current title: {rec['old_title']}")
    if rec.get("pr"):
        print(f"Pull request: {rec['pr']['url']} ({rec['pr'].get('state') or 'state not checked yet'})")
    until = declined_until(rec)
    if until and _today() < until:
        print(f"Turned down until: {until.isoformat()}")
    return 0


def cmd_decline(site, args):
    state = load_state(site)
    key, rec = _target(state, args.page)
    rec["declined_on"] = _today().isoformat()
    rec["decline_reason"] = args.reason
    save_state(site, state)
    print(f"Turned down; not proposed again before {declined_until(rec).isoformat()}.")
    return 0


def cmd_acted(site, args):
    state = load_state(site)
    key, rec = _target(state, args.page)
    try:
        repo, number = parse_pr_url(args.pr)
    except ValueError as e:
        raise SystemExit(str(e))
    if norm_title(args.new_title) == norm_title(rec.get("old_title")):
        raise SystemExit("The new title is the same as the current one, so the live page could not "
                         "show whether the change is out. Record the built page's new <title>.")
    rec["pr"] = {"url": args.pr.strip(), "repo": repo, "number": number, "state": None}
    rec["new_title"] = " ".join(args.new_title.split())
    rec.pop("declined_on", None)
    rec.pop("decline_reason", None)
    save_state(site, state)
    print(f"Recorded pull request {number} in {repo}; the weekly report will follow it.")
    return 0


def cmd_set(site, args):
    state = load_state(site)
    if args.name == "brand":
        spellings = [s.strip() for s in args.value.split(",") if s.strip()]
        if not spellings:
            raise SystemExit("Give at least one spelling, e.g. \"radwerk, rad werk\".")
        state["brand"] = spellings
    elif args.name == "pr_figures":
        if args.value not in ("yes", "no"):
            raise SystemExit("pr_figures takes yes or no.")
        state["pr_figures"] = args.value
    save_state(site, state)
    print(f"Saved {args.name}.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="The weekly fix proposal: show it and record what the owner decided.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show", help="Print this site's current proposal and answers.")
    s.add_argument("site")
    s = sub.add_parser("decline", help="The owner turned the current proposal down.")
    s.add_argument("site")
    s.add_argument("--reason", choices=("owner", "positioning"), default="owner")
    s.add_argument("--page", help="The page's address, for a proposal that is no longer the report's current one.")
    s = sub.add_parser("acted", help="Record the pull request made for the current proposal.")
    s.add_argument("site")
    s.add_argument("--pr", required=True, help="The pull request's address on GitHub.")
    s.add_argument("--new-title", required=True, help="The built page's whole new <title>.")
    s.add_argument("--page", help="The page's address, to correct the record of an earlier proposal.")
    s = sub.add_parser("set", help="Record one of the owner's answers.")
    s.add_argument("site")
    s.add_argument("name", choices=("brand", "pr_figures"))
    s.add_argument("value")
    args = ap.parse_args(argv)
    cmd = {"show": cmd_show, "decline": cmd_decline, "acted": cmd_acted, "set": cmd_set}[args.cmd]
    try:
        if args.cmd == "show":
            return cmd(args.site, args)
        with locked(args.site):          # read, change and write as one step (see locked())
            return cmd(args.site, args)
    except (ValueError, OSError) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
