# PLAN review — branch `plan/glm-marker-and-failed-reason` — GLM's marker twice, FAILED reason, codex_tokens

Artifact: `docs/reviews/SKILL-PLAN-glm-marker-twice-and-failed-reason.md`. Base `2275e756` · depth:
Normal (a tooling fix to the review script and its cost log; no box, user data, login, money,
deletion or schema, so no red team) · Daniel's go for the gate 2026-11-07. Seats: Codex and GLM 5.3
on melious in one command (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`), fresh-eyes Sonnet in round
1. Evidence: `EVIDENCE-glm-marker-plan.txt` in the session group's shared notes folder (it quotes
private captures, so it stays out of this public repo).

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `708d2ca5` | full plan; evidence E1–E9 (13,748 bytes) | Codex gpt-6.1-sol; melious glm-5.3; fresh-eyes Sonnet | Codex 203 s, 55,137 · melious 213 s, 31,446 · fresh-eyes 116 s, 110,012 | 2 / 6 / 8 before dedup (Codex 2/1/0, melious 0/3/4, fresh-eyes 0/4/2); 11 after |
| 2 | `10385968` | verify: full plan, PRIOR round 1, evidence E1–E13 (18,123 bytes) | Codex gpt-6.1-sol; melious glm-5.3 | Codex 159 s, 54,161 · melious 333 s, 47,617 | 2 / 0 / 4 (Codex 2/0/0, melious 0/0/4); 6 after dedup |
| 3 | `6d389c87` | verify: full plan, PRIOR round 2, evidence E1–E14 (20,186 bytes) | Codex gpt-6.1-sol; melious glm-5.3 | Codex 158 s, 54,161 · melious 355 s, 45,530 | 1 / 1 / 3 (Codex 1/0/0, melious 0/1/3); 5 after dedup |
| 4 | `c30648cc` | verify, `--earned-by finding-regex`: full plan, PRIOR round 3, evidence E1–E15 (23,025 bytes) | Codex gpt-6.1-sol; melious glm-5.3 | Codex 186 s, 54,161 · melious 327 s, 44,410 | 2 / 2 / 1 (Codex 2/0/0, melious 0/2/1); 4 after dedup |
| 5 | `e32d69a3` | verify, `--earned-by finding-regex --cut "line 112's copy of the grep replaced by a strict ASCII-only rule"`: full plan, PRIOR round 4, evidence E1–E16 (26,317 bytes) | Codex gpt-6.1-sol; melious glm-5.3 | Codex 161 s, 54,161 · melious 312 s, 50,141 | 0 / 3 / 3 (Codex 0/2/0, melious 0/1/3); 5 after dedup |
| 6 | `5430cc7e` | verify, `--earned-by finding-regex --cut "case folding removed"`: full plan, PRIOR round 5, evidence E1–E17 (29,741 bytes) | Codex gpt-6.1-sol; melious glm-5.3 | Codex 166 s, 54,161 · melious 676 s, 92,624 | 0 / 1 / 3 (Codex 0/1/0, melious 0/0/3) |
| 7 | `ab673cbb` | verify, `--earned-by finding-regex --cut "lookahead replaced by a whitelist of what may follow the label"`: full plan, PRIOR final full read, evidence E1–E19 (32,803 bytes) | Codex gpt-6.1-sol; melious glm-5.3 | Codex 198 s, 54,161 · melious 327 s, 54,569 | 0 / 0 / 2 (Codex 0/0/0, melious 0/0/2) |

## Round 1 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| A1 | BUG | Codex | T3 kept the capture's own hex marker, but production asks for a new one each run, so the old regex also passes T3 (no usable marker: kept whole and accepted) and the mutation cannot fail it | fixed: T3 replaces the hex marker at serve time and asserts no no-marker warning and the first finding line |
| A2 | BUG | Codex, fresh-eyes (RISK), melious (NIT) | "every reader already takes a missing field as `-`" is wrong for the counting command: awk reads a missing column 17 as empty; `HEADER` not mentioned | fixed: claim narrowed, command maps empty to `-`, `HEADER` gains `reason`, an old log keeps its header |
| A3 | RISK | Codex, melious, fresh-eyes | "take the last match" for `codex_tokens` rests on one file and on position alone | fixed: survey of 698 real `codex.err` files (691 with one bare footer pair in the last three lines, 7 with none, none with a same-line count); the rule now reads the last bare `tokens used` line followed by a digits-only line; differs from today's code on exactly the 3 quoted runs; T11, T12 added |
| A4 | RISK | melious, fresh-eyes (NIT) | a summary line that itself starts with a label (`BUG: 1, RISK: 5`) would make the second marker usable again | fixed: the finding test is now the review check's own `finding_count` shape (a list, heading or number marker first), so a bare label summary does not count; a `- Totals: 1 BUG` summary still would, pinned KNOWN WRONG (T4) |
| A5 | RISK | fresh-eyes | `test_round_checks.sh:330` asserts a 16-field line, so T4's "all pass unchanged" was wrong | fixed: T9 changes that case to 17 fields |
| A6 | RISK | fresh-eyes, melious (NIT) | the regex accepts less markup than "quote, heading, list or bold" said | fixed with A4: the plan now names the review check's shape and what falls outside it |
| A7 | RISK | melious | the marker cases may not live in the suite E6 ran | refuted: every stub (`leak`, `markdup`, … `markend`) is a `MELIOUS_STUB` case in `test_failed_tier_report.sh` (its `run mleak … MELIOUS_STUB=leak` lines, 1652 on); names corrected in T5 |
| A8 | NIT | melious | no mutation for fix 3 | fixed: restoring the first-match read must fail T10 |
| A9 | NIT | melious | the reason column's spaces vs the outcome's `tr ' ' '-'` unstated | fixed: reason kept word for word, only `clean()` applied |
| A10 | NIT | fresh-eyes | T1/T2 should say the cut keeps the first finding and the summary, and assert no dropped-text note | fixed |
| A11 | NIT | — | (the fresh-eyes "line 172" for the regex is wrong: it is line 112 at `2275e756`; it counted lines of its prompt file) | no change |

UNVERIFIABLE entries: 6 asked (capture history, the 696-check runs, cost-log totals, the
"production entry", PROMPT_CORE's shape, the 59,960 rows); 2 checked by the host and confirmed
(the gate's three Codex rows at 59,960, `grep` on the log; PROMPT_CORE line 861), the rest rest on
the READs sent.

## Round 2 findings

Both seats confirmed A1–A11 as landed. New:

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| B1 | BUG | Codex | "the same shape as `finding_count`" was wrong: the plan's regex used `[ \t]*`, grep uses `[[:space:]]*`, so `\f- BUG` counts in the review check but not in the reader | fixed: the regex now uses `[^\S\n]*` and `[0-9]+`; the exact line is in §1; on 1,753 real replies it and the grep pick the same lines in every file; the `\f` / `\v` / CRLF case counts 4 in both (E14) |
| B2 | BUG | Codex | T4's "the section is that summary alone" was wrong: the reader prints its note first | fixed: T4 states the replayed output (note, blank line, summary) and that neither finding line is in it (E14) |
| B3 | NIT | melious | E5 headlines candidate 1, not the plan's regex | fixed: the exact regex is in §1; E5 marked superseded |
| B4 | NIT | melious | 85,286 had no support in the evidence | fixed: E11 now shows the third file, 7iym1u, 59,960 → 85,286 |
| B5 | NIT | melious | column 13's values listed without the 11 lowercase `ok` lines | fixed: §2 says column 13 is written as today and names those lines |
| B6 | NIT | melious | "a heading line" in ctiPcY is a lead-in line | fixed |

Host checks of round 2's UNVERIFIABLE entries (E14): every stub named in T5 and `costfail` is in
`test_failed_tier_report.sh`; `clean()` also maps carriage returns (§2 now says so); no test but
`test_round_checks.sh:329–330` asserts a header or field count, and none asserts a new log's header,
so T6 now does. Codex's capture and corpus entries rest on the READs; the captures stay in the
notes folder because they quote private plans. Outside scope (melious): where the 11 lowercase `ok`
lines came from; not this plan's fault, no row raised.

Round 3 was owed: B1 and B2 were fixed BUGs.

## Round 3 findings

Both seats confirmed B1–B6 as landed, apart from C1's part of B1.

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| C1 | BUG | Codex, melious (NIT) | B1 only partly fixed: the reader matches the decoded reply, where Perl's `\s` takes NEL and U+2028 and grep's `[[:space:]]` does not, so a NEL-led footer makes the second marker usable and the check then rejects the summary; E14 compared raw bytes, not decoded text | fixed: the leading class is now ASCII whitespace only, `[ \t\f\x0B\r]`; on decoded text it never takes a space grep does not (grep takes a few non-ASCII spaces it does not: the loud way, kept whole with the warning); the line check re-run on decoded text, 1,774 files, none differing; Codex's NEL case now keeps both findings (E15) |
| C2 | RISK | melious | the size-limit outcome's string was not shown, so it might carry no parentheses and log reason `-`, untested | fixed: every FAILED outcome `report_tier` builds is parenthesized, the size limit's included (`independent_review.sh:1712–1733`, `:781`); §2 says how inner parentheses stay whole; T7 adds the size-limit case `t11c` (E15) |
| C3 | NIT | melious | "every reviewer reply" named more than the four file kinds compared | fixed: §1 names `codex.out`, `melious.out`, `ollama.out`, `melious.full`; no other `*.out` kind is present (E15) |
| C4 | NIT | melious | §3's residual case missed a quoted bare pair after the footer | fixed: §3 names both |
| C5 | NIT | host | while checking C1: T4's section (note plus a `- Totals: 1 BUG, 1 RISK` summary) is ACCEPTED by `looks_like_review`, so that KNOWN WRONG case counts the seat OK on a summary, with the reader's note as the only warning; the plan had said "brings the fault back" | fixed: §1 says so; today's code does the same with that reply, so the fix does not widen it (E15) |

Codex's UNVERIFIABLE entries ask for the captures, corpus and cost log, which stay in the notes
folder (private plans); its local `test_looks_like_review.sh` run failed in its sandbox (no temp
files), not on the code. Melious's "Codex echoes what it read into codex.err" is supported by E8's
quoted line, not by a planted run; nothing rests on it beyond §3's survey.

Round 4 is earned only by a substantive BUG or an earning RISK (SKILL.md, after round 3): C1 is a
substantive BUG in the reader's finding test, so round 4 runs with `--earned-by finding-regex`. That kind
earned no earlier round (rounds 2 and 3 were owed), so no cut is due; the fix is a strict rule
anyway: ASCII whitespace only. C2 is wording (the outcomes already had their parentheses; the fix
adds a test, not a change), so it earns nothing.

## Round 4 findings

Both seats confirmed C2–C5 as landed; C1 only for its NEL case.

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| D1 | BUG | Codex, melious (RISK) | the finding test still counts lines the grep does not, now through Unicode case folding: `- RIſK: footer` and the Kelvin sign match Perl's `/i` on decoded text, not grep; the second marker wins and the check rejects | fixed by a cut: line 112 no longer copies the grep. It is a strict rule, every piece ASCII and inside what the grep takes (ASCII spaces, marker, printable ASCII, an ASCII label with `/aa`, no word or non-ASCII character after it), so it can count only lines the grep counts. On 1,786 decoded replies it counts no extra line and misses 970 grep lines (prose after a dash or curly quote); replaying all 525 real melious replies, and the 19 multi-marker ones under each of 42 markers, every section is byte-identical to round 3's regex. `RIſK` and Kelvin probes keep both findings (E16); T14 pins them, and putting back round 3's regex must fail it |
| D2 | BUG | Codex | "kept whole with the no-marker warning" was wrong where an earlier marker stays usable: the walk cuts there | fixed: §1 says the walk tries the earlier markers, and only when none qualifies keeps the whole reply with the warning |
| D3 | RISK | melious | the reason extraction rests on every outcome keeping its parentheses, which nothing enforces; a new branch without them would log `-` | fixed: T13 lists every `outcome="` assignment and fails on one without " (" (today: all but `OK`, lines 1689–1733) |
| D4 | NIT | melious | no committed test tells the ASCII class from round 2's `[^\S\n]`; only a hand replay did | fixed: T14 includes the NEL-led footer |

Host checks of round 4's UNVERIFIABLE entries (E16): `$findings` is used only at
`melious_stream.pl:113` and `:118`; `review_log.sh` reads no `NF` and no column past `$16`
(lines 61–306). Codex's entries again ask for the private corpus and log, which stay in the notes
folder.

Round 5 is earned: D1 is a substantive BUG of the kind `finding-regex`, which earned round 4 too, so
round 5 runs with `--earned-by finding-regex --cut "line 112's copy of the review check's grep
replaced by a strict ASCII-only rule that counts only lines the grep counts"`. D3 is a RISK whose
fix adds a check and changes nothing that runs, so it earns nothing.

## Round 5 findings

No BUG. Both seats confirmed D1, D2 and D4 as landed, and Codex's replay reproduced D1's fix on
`RIſK` and the Kelvin sign; D3 only in part (E1).

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| E1 | RISK | Codex, melious | T13 reads only literal `outcome="` assignments, so an outcome built any other way gets past it; the plan credited it with "no outcome can reach `log_seat` without a reason" | fixed as wording: T13's claim narrowed to what it reads; the cost of a miss is a visible `-` in the count, and all nine assignments today are literal |
| E2 | RISK | Codex | `(?aai:…)` needs Perl 5.14; the script requires 5.10 (`independent_review.sh:1371`), and its Perl files say so (`ollama_stream.pl:23`: "the API transports need Perl 5.10, not 5.14") | fixed by a cut: case folding taken out; the labels are spelled `[Bb][Uu][Gg]`, `[Rr][Ii][Ss][Kk]`, `[Nn][Ii][Tt]`, no `/i` at all; probes, the replay of every real reply and the suite give the same results as round 4's spelling (E17). Not run on Perl 5.10 itself. An earning RISK (it changed what runs), so round 6 runs |
| E3 | NIT | melious | the unanchored clean verdict "No BUG/RISK/NIT findings" in a summary makes a second marker usable too | fixed: named beside the `- Totals` case in §1's "Still wrong" |
| E4 | NIT | melious | T14 pinned only the whitespace and case-folding ways in; widening the middle, or dropping the lookbehind or the lookahead's non-ASCII range, passed it | fixed: T14 adds `- éBUG:`, `- BUGé:`, `- xBUG:`; each of the three mutations is caught by exactly one of them (E17) |
| E5 | NIT | melious (outside scope) | D3's row cites 1689–1733, but 1689 is "a test invocation" | refuted: `independent_review.sh:1689` is `outcome="OK"` (E17) |

Codex's "byte-identical to round 3's regex" UNVERIFIABLE entry read round 3 as candidate 3; §1
now names the regex compared (the one this plan held after round 3, candidate 4).

Round 6 was earned by E2 (`finding-regex`, cut: case folding removed).

## Round 6 findings

No BUG. Both seats confirmed E1–E5; Codex replayed all seven T14 probes and the three mutations
through the reader and the check.

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| F1 | RISK | Codex | Perl 5.10 support still rests on a 5.34 run | fixed as evidence, nothing that runs changed: §1 cites Perl 5.10.0's perlre for every construct the rule uses, and that it has no `/a` (E18); still not run on 5.10, which §1 says. Not an earning RISK |
| F2 | NIT | melious | "three ways the copy counted a line the grep does not" was wrong for form feed: round 2's copy missed those lines | fixed: §1 says which way each one went |
| F3 | NIT | melious | T14 did not pin the bullet set or the lookahead's ASCII half | fixed: T14 adds `+ BUG:` and `- BUGx:`; widening the bullets and dropping `[A-Za-z0-9_]` from the lookahead are each caught by one of them (E18) |
| F4 | NIT | melious | "printable ASCII only" left out the tab the class holds | fixed: "only tabs and printable ASCII" |

The rounds end here (stop condition (a2): no BUG, no earning RISK). F1–F4 are `locally_verified`,
closing edits not externally re-verified. Still due: the final full read (a PLAN gate), then the
wording pass (rounds 1–5 found substantive BUGs).

## Final full read

On `a49c8ab5`, by a fresh Opus 5.5 subagent new to the plan: the plan, the evidence and the
scripts, with its own fuzz of 218,400 built lines through the rule and through the check as bash
feeds it. 200,755 tokens; seconds not recorded. 1 BUG, 1 RISK, 6 NIT.

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| G1 | BUG | full read | a footer `- BUG`, NUL, `x: footer` passes round 5's lookahead (NUL is not in its list); bash drops the NUL in `"$(cat …)"` (line 1608), so the grep sees `- BUGx:` and does not count it; the second marker wins, the section holds no finding and the seat is rejected. The fuzz found 1,470 such lines, all a label, a NUL and a word character | fixed by a cut: the lookahead now lists what may follow the label (end of line, tab, CR, space, ASCII punctuation) instead of what may not. The fuzz finds 0; captures, probes, corpus and replay as E19; T14 gains the NUL case and three mutations. Same kind as rounds 4–6 (`finding-regex`), so round 7 runs with `--cut` |
| G2 | RISK | full read | the plan's check list leaves out `check_prompt_sync.sh` and `check_perl_minimum.sh`, which CI runs (`.github/workflows/clean.yml:205,215`) | fixed as wording: both added to the list. Not an earning RISK: nothing that runs changed |
| G3 | NIT | full read | T1's "first line after its first marker" may be a blank line | fixed: "first non-blank line" |
| G4 | NIT | full read | the plan did not say the fixture is the reply text of `melious.full`, wrapped into SSE at test time | fixed: said under "Captures" |
| G5 | NIT | full read | the 970 / 609 corpus figures were measured on candidate 5, not the spelling the plan shows | fixed: re-measured with the new spelling, 1,810 files, 0 extra, 984 lost in 619 (E19) |
| G6 | NIT | full read | §3 described the codex rule in words only | fixed: §3 quotes the awk the survey ran (E11) |
| G7 | NIT | full read | "What it gives up" named a non-ASCII character before the label, not after it | fixed: both, with `BUG—` |
| G8 | NIT | full read | §2 did not name the text that states the column count: `review_log.sh` usage (7–9) and column note (41–43), `test_round_checks.sh:66` `NEW_HEADER` | fixed: named in §2 |

Round 7 is earned by G1 (`finding-regex`, cut: lookahead replaced by a whitelist of what may
follow the label).

## Round 7 findings

No BUG, no RISK. Both seats confirmed G1–G8; Codex ran the NUL, `BUGé` and `BUGx` cases and their
mutations through the reader and the check, and 420 more character probes with no line the rule
counts that the grep does not.

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| H1 | NIT | melious | T12's input was "a real `codex.err`" with the ERROR line after the footer, but no committed fixture held one | fixed: a second capture, f5jNZ6's last three lines (footer pair, ERROR line); T12 expects 54161 |
| H2 | NIT | melious | the check list credited `check_perl_minimum.sh` locally, where it skips (Perl::MinimumVersion not installed, E19) | fixed: the plan says it skips here and only CI checks the Perl minimum |

Two claims melious could not check, checked here: bash 3.2.57 (`/bin/bash`) and 5.3.20 (the
`bash` on `PATH`) both drop a NUL in `"$(cat …)"` rather than cutting the text at it
(`a`, NUL, `b` comes back `ab`); and `.github/workflows/clean.yml` lines 205 and 215 run
`check_prompt_sync.sh` and `check_perl_minimum.sh`.

The rounds end here (stop condition (a2): no BUG, no earning RISK). H1 and H2 are
`locally_verified`. Still due: the wording pass.

## Wording pass

Over `ab673cbb..a5dfdd9e` (prose only), `--wording-pass --seat codex --base ab673cbb`: Codex 82 s,
54,161 tokens. It reproduced the bash NUL claim and checked the CI lines, the local skip of
`check_perl_minimum.sh` and T12's 54161.

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| W1 | BUG | Codex | the plan's status row still said "round 7 … next" after this record closed round 7 | fixed: a contradiction with the record; the row says round 7, the full read and the wording pass are done |
