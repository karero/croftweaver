#!/usr/bin/env python3
"""
_history.py — tiny append-only history + trend for the tracker.

gsc_query.py / bing_query.py / insights.py call `append_rows()` with one row per
target keyword each run; `track.sh` (or `python _history.py <csv>`) prints the
week-over-week position movement. Position is "lower = better", so a DROP in the
number is an improvement (shown ▲). This is what turns the low-volume playbook's
"track position week-over-week" from a manual eyeball into one command.

CSV columns: date, site, source, keyword, query, position, impressions, clicks,
window, country. `site` (added 2026-09-02, alongside auto-appending becoming the
default) is a bare, normalized domain -- normalize_site() strips sc-domain:/
https:// / a trailing slash so GSC's and Bing's different --site formats, and
insights.py's already-bare --domain, all land on the same key. Before this
column existed, every site sharing one default history file was indistinguishable
by keyword alone -- two sites' trends for the same keyword string would silently
merge. `window`/`country` record the pull's configuration so the trend can flag a
move that compares two different configs; they were appended to the schema on
2026-08-29. append_rows() migrates an older header CSV in place before appending
(temp file + atomic replace, whole operation under a file lock) -- without that,
columns added later land past an old header and DictReader silently drops them,
killing the relevant flag for every pre-existing history. A row's full key —
date+site+source+keyword+window+country — also dedupes same-day re-runs (see
append_rows()'s docstring for why window/country are part of that key, not just
date/site/source/keyword).
"""
import csv
import collections
import fcntl
import os
import re
import sys

# Under this many impressions a compared side is noise: the trend marks the move
# `~`, and the keyword matcher won't headline such a row over a trustworthy one.
NOISE_IMPRESSIONS = 10

FIELDS = ["date", "site", "source", "keyword", "query", "position", "impressions",
          "clicks", "window", "country"]
# The two header shapes this tool has ever written, oldest first -- each one
# migrates forward to current, so a file several versions behind climbs the
# whole chain in one append_rows() call instead of needing repeated runs.
_LEGACY_HEADERS = [
    FIELDS[:1] + FIELDS[2:8],  # date,source,keyword,query,position,impressions,clicks (pre window/country)
    FIELDS[:1] + FIELDS[2:],   # date,source,keyword,...,window,country (pre site)
]


def normalize_site(raw):
    """A bare, lowercase domain from any of this skill's --site/--domain forms:
    'sc-domain:example.com', 'https://example.com/', or already-bare 'example.com'
    all become 'example.com', so the same site groups together regardless of
    which script (GSC's sc-domain: prefix, Bing's https:// prefix, insights.py's
    bare --domain) recorded the row. Only unifies these three forms this skill's
    own scripts actually produce for a whole-domain property -- it does NOT strip
    a path, so a URL-prefix GSC property scoped to a subpath (e.g.
    'https://example.com/blog/' -> 'example.com/blog') stays distinct from the
    domain-wide property, which is correct (they're different scopes) but means
    a caller passing a path-scoped --site won't merge with a bare-domain history
    for the same site. This skill's own onboarding only asks for a bare domain."""
    s = (raw or "").strip().lower()
    s = re.sub(r"^sc-domain:", "", s)
    s = re.sub(r"^https?://", "", s)
    return s.rstrip("/")


def append_rows(csv_path, items):
    """Append rows (list of dicts keyed by FIELDS) — write the header if new.

    An existing file carrying any header this tool has ever written
    (`_LEGACY_HEADERS`) is migrated first (rows re-keyed onto the current
    `FIELDS`, missing columns filled blank) — read with utf-8-sig so a BOM
    from a spreadsheet re-save can't break the header match. The migration is
    generic (dict access by field name, not column position), so the same
    code climbs a file several versions behind in one call. Any OTHER
    unrecognized header is left untouched (never rewritten — it isn't ours to
    reshape): a plain append with no dedup, plus a stderr note; a zero-byte
    file counts as new.

    Same-day re-runs are common now that auto-append is the default on every
    ad-hoc pull as well as the weekly scheduled job — without handling that,
    two runs on one date would leave print_trend()'s "last two rows" compare
    today's morning pull against today's afternoon one instead of the prior
    week's, silently breaking the trend. So a new row REPLACES any existing
    row with the same (date, site, source, keyword, window, country) key
    rather than adding a duplicate — window/country are part of the key, not
    just date/site/source/keyword, so an ad-hoc pull with a different window
    (e.g. the default 90 days) landing on the same day as the scheduled
    28-day job adds a second row instead of silently erasing the scheduled
    one; only a genuine same-config re-run collapses. The same key is also
    deduped WITHIN one call's own `items` (last occurrence wins) — a
    `--keywords` list with an accidental duplicate must not defeat this on
    its own. The whole file is rewritten via a temp file + atomic replace
    (the temp file is unlinked if anything fails before the replace, so a
    write error doesn't litter a stale `.tmp`), the entire operation (read,
    dedupe, write, replace) held under an exclusive lock on a sidecar
    `.lock` file so a concurrent writer (an ad-hoc pull overlapping the
    scheduled job) can't interleave with this read-modify-write and corrupt
    or lose rows.

    Returns the number of rows actually written (post within-call dedup) --
    smaller than len(items) when the caller passed duplicate keywords, so a
    caller's own "appended N rows" message stays accurate."""
    csv_path = os.path.expanduser(csv_path)
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)

    new_rows = []
    for it in items:
        # str()'d here, once: callers pass window as an int (e.g. args.days)
        # or bing's literal "~180", and every OTHER field already round-trips
        # as a string through the CSV -- an un-stringified int would silently
        # never equal the "28" a re-read of the same file produces, breaking
        # the dedupe key below against anything already on disk.
        row = {k: str(it.get(k, "")) for k in FIELDS}
        # Normalized here, once, rather than trusting every caller to call
        # normalize_site() itself -- a caller that forgets and passes the
        # raw sc-domain:/https:// form would otherwise split one site's
        # history into two never-matching groups.
        row["site"] = normalize_site(row["site"])
        new_rows.append(row)
    deduped = {}
    for r in new_rows:
        key = (r["date"], r["site"], r["source"], r["keyword"], r["window"], r["country"])
        deduped[key] = r  # last occurrence wins
    new_rows = list(deduped.values())
    new_keys = set(deduped.keys())

    lock_path = csv_path + ".lock"
    with open(lock_path, "a") as lockf:
        fcntl.flock(lockf, fcntl.LOCK_EX)
        try:
            new = not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0
            old_rows = []
            if not new:
                with open(csv_path, newline="", encoding="utf-8-sig") as f:
                    header = next(csv.reader(f), None)
                if header in _LEGACY_HEADERS:
                    with open(csv_path, newline="", encoding="utf-8-sig") as f:
                        old_rows = [{k: (r.get(k) or "") for k in FIELDS}
                                    for r in csv.DictReader(f)]
                elif header == FIELDS:
                    with open(csv_path, newline="", encoding="utf-8-sig") as f:
                        old_rows = list(csv.DictReader(f))
                else:
                    print(f"note: unrecognized history header in {csv_path} — file "
                          f"left as-is; the appended columns may not be readable "
                          f"there, and same-day re-runs will duplicate rather than "
                          f"replace", file=sys.stderr)
                    with open(csv_path, "a", newline="") as f:
                        w = csv.DictWriter(f, fieldnames=FIELDS)
                        for row in new_rows:
                            w.writerow(row)
                    return len(new_rows)

            kept = [r for r in old_rows
                    if (r.get("date", ""), normalize_site(r.get("site") or ""),
                        r.get("source", ""), r.get("keyword", ""),
                        r.get("window", ""), r.get("country", "")) not in new_keys]

            tmp = csv_path + ".tmp"
            try:
                with open(tmp, "w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
                    w.writeheader()
                    for r in kept:
                        w.writerow({k: (r.get(k) or "") for k in FIELDS})
                    for r in new_rows:
                        w.writerow(r)
                os.replace(tmp, csv_path)
            except BaseException:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
            return len(new_rows)
        finally:
            fcntl.flock(lockf, fcntl.LOCK_UN)


def _pos(row):
    v = row.get("position", "")
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _impr(row):
    """Parsed impressions, or None when the cell is blank/absent/garbled —
    None must stay distinct from a genuine 0 so legacy rows without a value
    never earn the thin-noise marker by coercion."""
    v = row.get("impressions", "")
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def print_trend(csv_path):
    csv_path = os.path.expanduser(csv_path)
    if not os.path.exists(csv_path):
        print("No history yet — this is the first run. Re-run in 1–2 weeks to see movement.")
        return
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    groups = collections.defaultdict(list)
    for r in rows:
        src, kw = r.get("source"), r.get("keyword")
        if not src or not kw:
            continue  # skip a malformed/partial row instead of crashing the whole trend
        # site defaults to "" for rows written before the site column existed
        # (migrated legacy rows) -- they group together as before rather than
        # crashing; only rows that actually recorded a site get split by it.
        site = normalize_site(r.get("site") or "")
        groups[(site, src, kw)].append(r)

    legend = {}
    print(f"{'site':28}  {'source':5}  {'keyword':30}  {'prev':>5}  {'now':>5}  move")
    print(f"{'-'*28}  {'-'*5}  {'-'*30}  {'-'*5}  {'-'*5}  {'-'*10}")
    for (site, src, kw), rs in sorted(groups.items()):
        rs.sort(key=lambda r: r.get("date", ""))
        now = rs[-1]
        # "prev" prefers the most recent EARLIER row with the SAME
        # window/country as "now" over a blind rs[-2] -- otherwise an
        # ad-hoc pull at a different window landing on the same day as the
        # scheduled job (kept as a separate row by append_rows' dedupe, see
        # its docstring) could become "now" or "prev" and get compared
        # against the wrong config, understating/overstating a move that
        # isn't real (an actual case: an intervening 90-day pull made a
        # 28-day weekly series read 8.0->9.0 instead of the real 10.0->9.0).
        # Falls back to the plain preceding row when no same-config match
        # exists (e.g. right after a genuine window/country change, or a
        # migrated pre-schema row) -- ‡ still flags that comparison.
        cfg_now = (now.get("window") or "", now.get("country") or "")
        prev = next((r for r in reversed(rs[:-1])
                     if (r.get("window") or "", r.get("country") or "") == cfg_now),
                    None)
        if prev is None and len(rs) > 1:
            prev = rs[-2]
        n, p = _pos(now), (_pos(prev) if prev else None)
        nf = f"{n:.1f}" if n is not None else "—"
        pf = f"{p:.1f}" if p is not None else "—"
        if prev is None:
            move = "(new)"
        elif n is not None and p is not None:
            d = p - n  # positive => position number went down => improved
            move = f"▲ +{d:.1f}" if d > 0.05 else (f"▼ {d:.1f}" if d < -0.05 else "→ 0")
        elif n is not None and p is None:
            move = "▲ now ranking"
        elif n is None and p is not None:
            move = "▼ dropped out"
        else:
            move = "—"
        # A "movement" that compares two DIFFERENT matched queries, or leans on
        # a handful of impressions on EITHER side, is not a rank change — mark
        # it so the arrow can't be over-read (the "AI Resources dropped -3.1"
        # class of misread: the matcher had switched queries, on 2-5
        # impressions). min() over the position-bearing sides, not max(): a
        # fat-prev/thin-now move is exactly the case the marker exists for.
        q_now, q_prev = (now.get("query") or ""), ((prev or {}).get("query") or "")
        if prev is not None and q_now and q_prev and q_now != q_prev:
            move += " ≠"
            legend["≠"] = ("≠ best-matching query changed between runs — "
                           "not the same query's movement")
        imprs = [i for i in (_impr(r) for r in (now, prev)
                             if r is not None and _pos(r) is not None)
                 if i is not None]
        if prev is not None and imprs and min(imprs) < NOISE_IMPRESSIONS:
            move += " ~"
            legend["~"] = (f"~ a compared side has under {NOISE_IMPRESSIONS} impressions — "
                           "movement is noise at this volume")
        cfg_now = (now.get("window") or "", now.get("country") or "")
        cfg_prev = (((prev or {}).get("window")) or "", ((prev or {}).get("country")) or "")
        # Unequal tuples imply at least one non-empty side, so inequality
        # alone is the whole test — an unknown (legacy-blank) config vs a
        # recorded one deliberately counts as a change.
        if prev is not None and cfg_now != cfg_prev:
            move += " ‡"
            legend["‡"] = ("‡ the tracked window/country changed — or the earlier "
                           "row predates the config columns (previously "
                           "unrecorded); positions not comparable across it")
        if src == "bing" and prev is not None:
            legend["bing"] = ("bing rows: positions are ~6-month aggregates — "
                              "week-over-week moves are damped and lag")
        print(f"{site[:28] or '(unknown)':28}  {src:5}  {kw[:30]:30}  {pf:>5}  {nf:>5}  {move}")
    for note in legend.values():
        print(f"  {note}")


if __name__ == "__main__":
    print_trend(sys.argv[1] if len(sys.argv) > 1 else "history.csv")
