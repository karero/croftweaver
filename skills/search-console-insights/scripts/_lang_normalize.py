"""Shared keyword matching for gsc_query and bing_query: how a reported query
is matched to a target keyword, and which match stands for the keyword.

German searchers type both umlaut and ASCII forms ("münchen" and "muenchen",
"fußball" and "fussball") and GSC/Bing report them as DISTINCT query strings —
matching on .lower() alone reports false "no impressions yet" for whichever
variant the keyword list didn't happen to use. Fold both sides before matching.

str.casefold() already maps ß→ss; the umlaut→digraph mapping is German
orthography (ä→ae, ö→oe, ü→ue), applied after casefold.
"""

import re
import unicodedata

_FOLD = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue"})


def fold(s: str) -> str:
    """Casefold + German umlaut/ß folding, for match comparisons only.

    NFC first: a decomposed umlaut (u + combining diaeresis, e.g. pasted from a
    macOS filename) survives casefold as-is and would miss the translate table.
    Note the deliberate merge: ß→ss folding equates genuinely distinct words
    (Maße/Masse, Buße/Busse) — acceptable for search-intent matching, where
    searchers type both spellings interchangeably anyway.
    """
    return unicodedata.normalize("NFC", s).casefold().translate(_FOLD)


def words_of(s: str) -> list:
    """Folded words, split on anything that isn't a letter or digit — so the
    hyphenated compound "ki-events" yields the same words as "ki events"."""
    return re.findall(r"[^\W_]+", fold(s))


def match_keywords(rows, keywords, text_of, min_impressions):
    """Match each target keyword against reported query rows.

    A row matches when every word of the keyword starts some word of the
    query, so 'AI Events Munich' also catches 'ai events in munich' and
    'ai event' catches 'ai events'. Whole-word prefixes, not substrings:
    the earlier substring rule let 'ai' match inside 'main' and 'train'.
    Two exceptions keep German working: a one- or two-letter word must match
    a whole word ('ki' must not catch 'kino'), and the keyword run together
    also counts, because Germans write compounds solid ('Event Kalender'
    catches 'eventkalender münchen').

    Returns [(keyword, matched_rows)] with the best match first. That first
    row is what the report quotes and the history tracks, so the order is the
    whole point:
      1. rows with at least min_impressions come before thinner ones — the
         trend's own noise floor (a compared side under it earns the `~`
         marker), so the headline is never a row the tracker calls noise
         when a trustworthy one exists;
      2. among those, the keyword itself (same words, any order) beats a
         variant: it is literally the question the owner asked;
      3. then impressions decide — the wording people actually type.
    Volume alone once let an 8-impression fifteen-word query outrank the
    exact phrase (3 impressions), and the history tracked that long-tail
    query under two keywords at once (2026-09-03). Exactness alone would
    flip a keyword between a 2-impression exact row and a 300-impression
    variant whenever GSC's anonymisation drops the thin row for a week; the
    floor keeps the tracked query stable.
    """
    def word_matches(w, t):
        return w == t if len(t) <= 2 else w.startswith(t)

    results = []
    for kw in keywords:
        tokens = words_of(kw)
        if not tokens:
            results.append((kw, []))
            continue
        solid = "".join(tokens)
        ranked = []
        for r in rows:
            words = words_of(text_of(r))
            # The solid form only means something for a multi-word keyword;
            # for one word it would just re-open the short-word loophole.
            if not (all(any(word_matches(w, t) for w in words) for t in tokens)
                    or (len(tokens) > 1 and any(w.startswith(solid) for w in words))):
                continue
            impressions = r["impressions"]
            exact = sorted(words) == sorted(tokens)
            ranked.append(((impressions < min_impressions, not exact, -impressions), r))
        ranked.sort(key=lambda x: x[0])
        results.append((kw, [r for _, r in ranked]))
    return results
