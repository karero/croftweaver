# Review trail: design plan for the weekly fix proposal

Artifact: `docs/reviews/DESIGN-weekly-fix-proposal.md` and the probe
`docs/reviews/fix-proposal-probe/fix_probe.py` (PR #297). Gate: Normal, PLAN. Reviewers:
Codex and GLM 5.3 on melious. A severity bar was agreed in the brief before round 1:
claims about Google and Serper that the plan quotes or measured are not re-raised, and
the owner's decisions are settled.

## Round 1 — reviewed at 95faa83, 2026-10-14

Codex 14 findings, GLM 9; merged, 21: 9 BUG, 9 RISK, 3 NIT. All fixed.

| # | Seat | Kind | Finding | Disposition |
|---|---|---|---|---|
| 1 | Codex | BUG | `track.sh` and `schedule_tracking.sh` rewrite `sites/<site>.json` whole, so `brand`, `repo`, `pr_figures` stored there would be lost | Fixed: the owner's answers live in the new state file |
| 2 | Codex | BUG | The control ignored shared files outside `src/` and `public/` (`astro.config.mjs`) | Fixed: any commit outside the starter's documentation-only rule voids the control |
| 3 | Codex, GLM | BUG + NIT | The live-detection windows did not give scenario 8's dates, and "the Sunday before / Monday after" a run was ambiguous | Fixed: last Sunday before the last "old" observation; first Monday on or after the first "new" one; scenario 8 worked through |
| 4 | Codex, GLM | BUG + RISK | A closed pull request was never noticed, so the page could stay blocked | Fixed: `gh pr view` each run; closed = "not this one"; without `gh`, a 6-week release |
| 5 | Codex | BUG | Words under 3 letters were skipped, so "ki" made every page "already" match | Fixed: every word counts, whole words, a short stop-word list; an empty set never matches |
| 6 | Codex | BUG | `serp_check.py` expects a two-letter country, the settings hold three | Fixed in §1 for T2 later |
| 7 | Codex | BUG | The probe's window lacked the report's Sunday alignment | Fixed; rerun gave the same output (the finished day was a Sunday) |
| 8 | Codex | BUG | P2 called Serper's text "what Google keeps" before the by-eye half | Fixed: worded as Serper's result, conditional on the owner's check |
| 9 | Codex | BUG | T1 is the playbook's second item, not its first | Fixed |
| 10 | Codex | RISK | `git log` on a stale local checkout can miss other people's changes | Fixed: `git fetch`, then the remote default branch; a failed fetch means no comparison |
| 11 | Codex | RISK | A failed page fetch counted as "not live yet" | Fixed: three outcomes, unknown moves nothing |
| 12 | Codex | RISK | Saved data after a Google failure could still produce a proposal | Fixed: proposals only from fresh data; a test for it |
| 13 | Codex | RISK | Whether the owner's sentence loads the skill cold is unproven | Fixed as a step: tried cold in Claude Code and Codex in step 4 |
| 14 | Codex | RISK | The review step did not wait for the reference and evals | Fixed: step 6 waits for 4 and 5 |
| 15 | GLM | RISK | No rule for which commits are the proposal's own | Fixed: commits naming the pull request number |
| 16 | GLM | RISK | "Already on the page" was not in the exclusion list | Fixed |
| 17 | GLM | RISK | `--title` could be read as the pull request's title | Fixed: `--new-title`, the page's `<title>`, folded substring match |
| 18 | GLM | RISK | No command wrote the owner's answers | Fixed: `fix_proposal.py set` |
| 19 | GLM | NIT | The four places were not listed | Fixed |
| 20 | GLM | NIT | Scenario 3 had no test and no reason | Fixed: T2 waits |
| 21 | GLM | NIT | "One more request" could be read as unpaged | Fixed |

## Round 2 — verification at 8bd8516, 2026-10-14

Codex 7 findings, GLM 8; merged, 13: 4 BUG, 5 RISK, 4 NIT. Ten concerned the measuring,
which had drawn BUGs in round 1 too. The owner cut it down (DD7: before and after only,
no comparison against the rest of the site; DD8: windows from the weekly checks), and
the requirements' R3 and scenario 8 were amended to match.

| # | Seat | Kind | Finding | Disposition |
|---|---|---|---|---|
| 1 | Codex, GLM | BUG | The 6-week release could free a page whose pull request is still open, or cut a 12-week decline short | Fixed: no timer; the page stays excluded while open or merged-not-live, and each report says what is waiting |
| 2 | Codex | BUG | Windows from observations still differ from R3's exact live day | Fixed by amending R3 (DD8, owner) |
| 3 | Codex | BUG | The probe's fallback without metadata did not match the report's | Fixed: same fallback (last final-data day, else three days back) |
| 4 | Codex | BUG | The control's documentation rule left out `.claude/` | Moot: the control is out of v1 (DD7) |
| 5 | Codex | RISK | A shortened new title can sit inside the old one and fake "live" | Fixed: the old title is kept; "new" requires a title that is not the old one |
| 6 | Codex | RISK | `git log` on the default branch does not show what was published on a two-stage site | Moot (DD7) |
| 7 | Codex, GLM | RISK | "#31" in a commit message is no proof of the proposal's own commit | Moot (DD7) |
| 8 | GLM | RISK | A merged change never seen live had no exit | Fixed: it stays excluded and the report says "merged, not seen live yet", with the `npm run ship` hint; the owner can turn it down |
| 9 | GLM | RISK | `gh pr view` with an address was untested | Fixed: number and repository stored; a stub `gh` in the command-line tests |
| 10 | GLM | NIT | The brand list's command syntax was missing | Fixed |
| 11 | GLM | NIT | How the default branch is found was missing | Moot (DD7) |
| 12 | GLM | NIT | What "reopened" does was missing | Fixed: it cancels the decline |
| 13 | GLM | NIT | The stop-word list was not named | Fixed: listed in §3.2 |

## Round 3 — verification at fa5343b, 2026-10-14

Codex and GLM 5.3 on melious. Both confirmed round 2's fixes landed, and that the moots
under DD7 are real (the machinery is gone). Codex 4 findings, GLM 4; merged, 6: 2 BUG,
1 RISK, 3 NIT. All fixed.

| # | Seat | Kind | Finding | Disposition |
|---|---|---|---|---|
| 1 | Codex, GLM | BUG + RISK | The probe's fallback looked back 40 days, the report's about 16 months | Fixed: the probe imports the report's `HISTORY_DAYS` |
| 2 | Codex, GLM | BUG + RISK | A rollback to the old title after the first "new" check moved the before-window onto new-page days | Fixed: both edges fixed at the first new check; any later title other than the new one interrupts the measuring |
| 3 | Codex | RISK | The old title with a new layout suffix could pass as "new" when the new title is a shortening | Fixed: the whole rendered title is recorded and compared whole |
| 4 | Codex | NIT | R1 still said "anchored on the date the change went live" | Fixed |
| 5 | GLM | NIT | DD6's row still had P2 with the owner | Fixed |
| 6 | GLM | NIT | §1, §2 and DD0 did not state one reason why T2 waits | Fixed: a trustworthy page figure (P1) |

Round 3 had BUGs, both residues of earlier fixes; a Codex fix check and the wording pass
follow in one full read.

## Final full read and wording pass — Codex at 8b7de92, 2026-10-14

Round 3's fixes verified landed. 6 findings: 2 BUG, 4 RISK. 5 fixed, 1 refuted.

| # | Kind | Finding | Disposition |
|---|---|---|---|
| 1 | BUG | A third title was "unknown, changes nothing" in one place and "interrupts the measuring" in another | Fixed: four outcomes; "other" (readable, neither title) is told apart from "unreadable" |
| 2 | BUG | The owner's sentence had lost the search, the places and the page that R1 asks for | Fixed: the sentence starts with the skill's name and names all three |
| 3 | RISK | An unchanged or case-only title could match old and new at once | Fixed: `acted` refuses a new title equal to the old one |
| 4 | RISK | A closure between two weekly checks started the 12 weeks late | Fixed: `closedAt` is read and used |
| 5 | RISK | The measuring windows had no fetch of their own | Fixed: two query-filtered requests, one per window, with the report's country and property, made once the data is complete |
| 6 | RISK | Google's behaviour (completeness, position, omissions, limits) not proven | Refuted: outside the agreed severity bar; §1 cites the documentation, and probe P1 captured both the metadata-present and the metadata-absent case on a real site |

## Fix check — Codex at c323c93, 2026-10-14

Four of the final read's five fixes verified. 2 findings:

| # | Kind | Finding | Disposition |
|---|---|---|---|
| 1 | BUG | An interrupted measuring had no fetch rule for its shortened window | Fixed: the after-window ends on the last Sunday before the interrupting check, is fetched once complete, stored as interrupted and shown with its number of weeks; no full week means no figures |
| 2 | RISK | Google's behaviour, again (fifth time) | Refuted, as in the final read: outside the agreed bar; §1's sources and probe P1 |

Gate closed after this fix, 2026-10-14: 3 rounds, a final read and a fix check, 48
findings: 40 fixed, 6 moot after DD7, 2 refuted. The last fix (one paragraph) was not
sent through another round.
