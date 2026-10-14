# Review trail: the weekly fix proposal (build)

Artifact: branch `feat/weekly-fix-proposal`, the diff against `main` (`fix_proposal.py`, the
report's proposal section in `search_report.py`, `references/fix-proposal.md`, one SKILL.md row,
four evals, their tests, and the design plan's notes). Gate: Normal, DIFF (runtime code that reads
the owner's live pages and writes local state, so never Light). Reviewers: Codex and GLM 5.3 on
melious (`SECOND_SEAT=melious`).

Severity bar, agreed before round 1 (as for the design plan, #297): claims about Google and
Serper that the design plan §1 quotes or measured are not re-raised; the owner's decisions
(D0 to D11, DD0 to DD8) are settled. Rounds stop after one without a BUG, then one wording pass.

## Test records before round 1 (at a81b72b, 2026-10-14)

- `~/.config/gsc-insights/venv/bin/python -m unittest discover -s skills/search-console-insights/scripts/tests`:
  308 tests, OK, exit 0.
- `make check`: all checks passed, exit 0. One soft warning is new: SKILL.md is 501 lines, over
  the 500-line soft budget.
- Behaviour checks already run (design plan §4): rules broken on purpose in a copy, all caught
  (step 2: 11, step 3: 9 plus the word check); eval iteration 1, with the skill 18 of 18, without
  12 of 18; cold starts in Claude Code and Codex (design §3.3).

## Round 1 — reviewed at 4088661, 2026-10-14

Codex 16 findings (15 BUG, 1 RISK), GLM 8 NIT; two overlaps merged: 22 findings, 15 BUG,
1 RISK, 6 NIT. 21 fixed, 1 refuted. 323 tests after the fixes (15 new), and each new guard was
broken once in a copy to see a test fail.

| # | Seat | Kind | Finding | Disposition |
|---|---|---|---|---|
| 1 | Codex | BUG | The live-page reader checked the first address but followed redirects anywhere | Fixed: a redirect is followed only to the site's own pages; local-server test |
| 2 | Codex | BUG | `state_path("../../outside")` wrote outside `sites/` | Fixed: only a bare domain is taken |
| 3 | Codex | BUG | A damaged `result` crashed the page | Fixed: a damaged record costs its line; the whole section has its own error boundary |
| 4 | Codex | BUG | A second report on the same day replaced the "old" look, so windows never formed | Fixed: same-day looks are kept in order; `windows` reads them by order |
| 5 | Codex | BUG | A failed comparison request aborted before saving the week's look | Fixed: caught per record, tried again next run |
| 6 | Codex | RISK | The report and the commands could overwrite each other's changes | Fixed: one lock per site around every read, change and write |
| 7 | Codex | BUG | CLOSED, then MERGED kept the closure's "no" | Fixed: merged after all takes it back |
| 8 | Codex | BUG | A stored result freed a page whose pull request was still open | Fixed: an open pull request blocks first |
| 9 | Codex | BUG | A search whose page had under 10 impressions could be proposed | Fixed: R1's noise floor on the page's share |
| 10 | Codex | BUG | Greedy word matching missed "Fahrrad und Fahrradreparatur" | Fixed: every split is tried |
| 11 | Codex | BUG | A failed GitHub check after an earlier answer was not shown | Fixed: the line says the state is the last one GitHub gave |
| 12 | Codex | BUG | A third title before going live got the "run npm run ship" line | Fixed: its own line, asking for a check |
| 13 | Codex | BUG | The "no answer changes nothing" test compared an object with itself | Fixed: compared with a deep copy |
| 14 | Codex, GLM | BUG + NIT | "Too little data" on a busy site with nothing in striking distance | Fixed: its own wording, on the page and in the log |
| 15 | Codex | BUG | The sentence names three places, the reference and report four | Fixed: three places; the description only if the new title leaves it wrong (reference, report, evals) |
| 16 | Codex, GLM | BUG + NIT | A search turned down in words came back with its old dates | Fixed: a finished or expired round is archived; a new one starts fresh |
| 17 | GLM | NIT | `show` said "none" while a proposal was in progress | Fixed: `show` falls back as `decline` and `acted` do |
| 18 | GLM | NIT | CLOSED without a day kept the page blocked as "open" | Fixed: the day defaults to today |
| 19 | GLM | NIT | A closed round read "could not be checked" | Fixed: "you closed pull request N; not proposed again before …" |
| 20 | GLM | NIT | ISO dates on the owner's page | Fixed |
| 21 | GLM | NIT | The status row said "not pushed" | Fixed |
| 22 | GLM | NIT | Scenario 6's test depends on the real date | Refuted: it fails only on a clock before 17 August 2026; the clock only moves on |

## Round 2 — verification at 1e7ea82, 2026-10-14

Codex 5 findings (4 BUG, 1 NIT), GLM 3 NIT; one overlap merged: 7 findings, 4 BUG, 3 NIT.
Both seats confirmed the other round-1 fixes landed. 5 fixed, 1 fixed by a cut, 1 refuted.

| # | Seat | Kind | Finding | Disposition |
|---|---|---|---|---|
| 1 | Codex | BUG | Round 1's "open blocks first" left a measured page blocked for good: measured records were no longer asked about | Fixed: a measured record whose last state is OPEN is still asked; report test |
| 2 | Codex | BUG | The page floor counted only this search's share of the page | Fixed: the page's own non-brand total, over all its searches |
| 3 | Codex | BUG | The sentence still did not name the description the reference allowed | Fixed by a cut: v1 never changes the description, so sentence and edit name the same three places (reference, report, evals, design §3.1) |
| 4 | Codex | BUG | The busy-site wording claimed a page check that had not happened | Fixed: it lists the conditions instead |
| 5 | Codex, GLM | NIT | Scenario 6's test still depends on the real clock | Fixed after all: the clock is held still through `fix_proposal._today` |
| 6 | GLM | NIT | A command waiting for the lock gave no sign | Fixed: it says it is waiting for the weekly report |
| 7 | GLM | NIT | `import fcntl` breaks the commands on Windows | Refuted: `_history.py`, imported for `normalize_site`, already imports `fcntl` at the top, and native Windows is out of scope (requirements R6) |

## Round 3 — verification at c7872e5, 2026-10-14

Codex 2 BUG, GLM 2 RISK and 2 NIT; one overlap merged: 5 findings, 2 BUG, 2 RISK, 1 NIT.
3 fixed, 2 refuted.

| # | Seat | Kind | Finding | Disposition |
|---|---|---|---|---|
| 1 | Codex | BUG | Eval 13 still said "four places" | Fixed: title, H1 and first paragraph, never the description |
| 2 | Codex, GLM | BUG + NIT | A measured round with an unknown or CLOSED last answer was never asked again | Fixed: one rule, a measured round is asked until GitHub says merged; test for both |
| 3 | GLM | RISK | The busy-site sentence wrote 50 and 10 as text while the code holds them as constants | Fixed: the sentence takes them from the constants; the test checks the numbers |
| 4 | GLM | RISK | The scenario 6 clock fix works only if the command runs in the test's process | Refuted: `assistant()` calls `fp.main` in-process (test_fix_proposal_report.py, `assistant`) |
| 5 | GLM | NIT | A "changed again too soon" result is never measured again | Refuted: by design, R3 says the report then states it changed too soon to measure |

Round 3 had BUGs, so round 4 follows (the script's rule: kinds named, and a cut for each kind
that earned an earlier round).

## Round 4 — verification at e6e477d, 2026-10-14 (`--earned-by pr-state-refresh,three-places`, cut named)

Codex 1 BUG and 1 RISK, GLM 1 NIT: 3 findings. 1 fixed, 1 settled by a cut, 1 refuted. The two
round-3 fixes verified landed.

| # | Seat | Kind | Finding | Disposition |
|---|---|---|---|---|
| 1 | Codex | BUG | An archived round's closed pull request, reopened later, is never asked about, so its page is not blocked | Cut, not patched: the third fix of the same kind (following pull requests) would have meant asking GitHub about every archived pull request every week. The report follows a pull request only while its round is in progress; design §3.4 and the reference say so, and that a reopened old pull request is the owner's to mention |
| 2 | Codex | RISK | The thin-data sentence still wrote "8 to 20" as text | Fixed: from `T1_POSITION` |
| 3 | GLM | NIT | "4 weeks" is written out, not taken from a constant | Refuted: the four-week window is the report page's own, written the same way across the whole page (`fetch_google`, the headline, the tables); a change to it would be page-wide, not this feature's |
