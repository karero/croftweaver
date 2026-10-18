# PLAN review — one site's AI check at a time
Base `89f965b5` · depth: Normal (a plan for shipped code; it touches no user data, login, money or deletion, so no red team) · verdict: CLEAN (2026-10-18). Three rounds (2 BUG, both in round 1), a final full read, a wording pass and one confirmation; 47 findings in the rounds and the final read; no BUG open; nothing waived; closing edits after round 3 not externally re-verified except by the wording pass

Artifact: `docs/reviews/SKILL-PLAN-ai-check-lock.md`, whole. Destinations: Codex and melious.ai, as the global working rules name them (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`); this repository is public and its content has gone to both before. Heads named here from before `1c4f9b41` were folded into that one commit on the maintainer's OK (an earlier commit named the owner's sites), so they are not in the pushed history; the reviewed content is. Claims sweep run before round 1 (25 sentences); two claims corrected from it (which runs failed on 2026-10-12, and why GSC and Bing are out of scope).

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `89f965b5` + the plan, uncommitted | full | Codex CLI 0.162.1, gpt-6.1-sol, config effort, read-only · Melious HTTP API, glm-5.3, text only · fresh-eyes sub-agent, sonnet, read-only | Codex 208 s, 71,576 · Melious 137 s, 14,633 · fresh-eyes 164 s, 125,263 | 2 / 5 / 8 after merging duplicates (Codex 2/1/0, Melious 0/2/6, fresh-eyes 1/3/6; fresh-eyes' BUG on the stale status row merged into A14 as a NIT: a status cell, nothing anyone builds from). Unverifiable entries: Codex 3, Melious 5 groups, fresh-eyes 2; one (launchd) led to the quote now in the plan |
| 2 | `1bc10dd8` | full, as a verification round (prior findings A1 to A15) | Codex (medium) · Melious glm-5.3 | Codex 185 s, 56,645 · Melious 189 s, 21,278 | 0 / 3 / 2 (Codex 0/2/0, Melious 0/1/2). A1 to A15 confirmed, A3 and A4 in part (B1, B2) |
| 3 | `a82aaa22` | full, as a verification round (prior findings B1 to B5) | Codex (medium) · Melious glm-5.3 | Codex 73 s, 40,233 · Melious 214 s, 23,551 | 0 / 2 / 3, plus 2 NIT outside scope (Codex 0/2/0: both re-raise B2, B3 asking for more evidence; Melious 0/0/3+2). No substantive BUG: the rounds end (stop condition a2) |
| final full read (not a round) | `74e97912` | full | fresh sub-agent, claude-opus-5-5, read-only (ollama cloud out of quota, so no Kimi; nothing else sent to melious in its place) | 476 s, 175,995 | 2 / 4 / 8 (F1 to F14); both BUGs wording or a table cell, not substantive |
| wording pass (not a round) | `12195712` | delta since `74e97912` | Codex (medium) | 79 s, 36,223 | 1 contradiction (W1: "at least 5 minutes apart" false past twelve sites), fixed; 2 RISK re-raising F6 and F13 without new evidence, refuted |
| confirmation (not a round) | `15df8486` | that fix's delta | Codex (medium) | 40 s, 18,174 | 1 contradiction ("5 minutes apart" exact), fixed |
| confirmation of that fix (not a round) | `84d28dd2` | that fix's delta | Codex (medium) | 43 s, 29,313 | No BUG/RISK/NIT findings |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | BUG | Codex | 1 | the "at most about 40 minutes" ceiling is false: `_send`'s timeout limits each read, so a call can run past its engine's deadline | fixed, locally_verified | Codex measured 2.8 s past a 1 s deadline; the plan drops the ceiling and says there is no hard upper bound |
| A2 | BUG | Codex | 1 | `--only` is not a command-line option; it is `--engines` | fixed, locally_verified | `geo_check.py` main(): `--engines`; "Where" names it |
| A3 | RISK | Codex, Melious, fresh-eyes | 1 | the no-wait test ignored `--engines`; the no-key and no-question cases had no test | fixed, locally_verified | "Where" and T4 |
| A4 | RISK | Melious, fresh-eyes | 1 | 60 minutes was too low, and based on runs that were failing | fixed, locally_verified | 90 minutes; croftweaver.com 2026-10-18 ran alone in 12 min with every engine "ok" (`geo_history.csv`, run `20261018T065901Z…`); runs 2026-10-04 to 10-12 took 7 to 13 min (answer-folder file times) |
| A5 | RISK | fresh-eyes | 1 | under launchd stdout is a file, so the waiting line would be held back until the run ends | fixed, locally_verified | "Waiting": flushed; T6 |
| A6 | RISK | fresh-eyes | 1 | the assistant's run by hand may time out while it waits | fixed, locally_verified | step 5: a note in `references/geo-check.md`; a `--no-wait` flag out of scope |
| A7 | RISK | Melious | 1 | the lock-order claim had no support in the plan | fixed, locally_verified | "How it locks" states the order and a code comment pins it; Codex and fresh-eyes read `geo_check.py`: the history lock is taken only after the engine loop |
| A8 | NIT | fresh-eyes | 1 | the run-anyway line would print twice | fixed, locally_verified | added to the problems only |
| A9 | NIT | fresh-eyes | 1 | only `BlockingIOError` means held; create `geo/` first | fixed, locally_verified | "How it locks", "When the wait runs out" |
| A10 | NIT | fresh-eyes | 1 | test helpers hard-code one domain; `hits` tuples are read by index | fixed, locally_verified | "How it is tested": a separate `spans` list, one shared HOME |
| A11 | NIT | fresh-eyes | 1 | the BUGLOG row should name the PR | fixed, locally_verified | step 5 |
| A12 | NIT | Melious | 1 | the waiting line hard-coded 60 | fixed, locally_verified | "Waiting": N is the real limit |
| A13 | NIT | Melious | 1 | T5 depended on an unstated open mode | fixed, locally_verified | `open(path, "a")`; fresh-eyes confirmed `IsADirectoryError` |
| A14 | NIT | Melious, fresh-eyes | 1 | status row 3 was stale, and the edit targets exist only on the stagger branch | fixed, locally_verified | row 3 names karero/croftweaver#354; the edits moved to step 5, after merging main |
| A15 | NIT | Melious | 1 | "as launchd does" had no support | fixed, locally_verified | `schedule_tracking.sh` line 87: the plist runs `/bin/bash` |
| B1 | RISK | Codex | 2 | T4's `--engines` case would pass even if the selection were ignored | fixed, locally_verified, externally_reverified (round 3) | T4 now has a usable key for an unselected engine |
| B2 | RISK | Codex | 2 | the measurements had no records | fixed, locally_verified | the table of run ids, times, statuses and overlaps; Codex re-raised it in round 3 and the wording pass without new evidence (refuted: the raw files are on the maintainer's Mac and name private sites, so the table is the committable extract; the final full read reopened those files and confirmed the table apart from F2 and F13) |
| B3 | RISK | Melious | 2 | `time.monotonic` not counting sleep was unsupported | fixed, locally_verified | Apple's data file for `mach_absolute_time`: "Returns current value of a clock that increments monotonically in tick units (starting at an arbitrary point), this clock does not increment while the system is asleep." Re-raised by Codex (no network) in round 3, the final read (F6) and the wording pass: refuted on that quote |
| B4 | NIT | Melious | 2 | stdout-to-a-file uncited | fixed, locally_verified | `StandardOutPath`, `schedule_tracking.sh` line 103 |
| B5 | NIT | Melious | 2 | status row counts | fixed, locally_verified | — |
| C1 | NIT | Melious | 3 | sub-minute durations would print "0 min" | fixed, locally_verified | "Waiting": seconds under a minute |
| C2 | NIT | Melious | 3 | "about seven runs" | fixed, locally_verified | "six to nine" |
| C3 | NIT | Melious | 3 | status row 2 names a different file from the verification record | refuted | the record named the artifact, the row names the trail; both are right |
| C4 | NIT | Melious (outside scope) | 3 | T1's `/bin/bash` sentence | fixed, locally_verified | T1 cites `ProgramArguments` |
| C5 | NIT | Melious (outside scope) | 3 | "a run can outlast its slot" leaned on unstated spacing | fixed, locally_verified | "What and why" states the slots (then F1, W1) |
| F1 | BUG | final read | final | "15 minutes apart" is false past four sites | fixed, locally_verified, externally_reverified (confirmation) | — |
| F2 | BUG | final read | final | the 10-04 site A run also overlapped site B | fixed, locally_verified | table |
| F3 | RISK | final read | final | an earlier local commit names the owner's sites; `check_clean.sh` scans only the tree | fixed, locally_verified | step 7: fold the commits before the first push, check `git log -p` |
| F4 | RISK | final read | final | T3 could pass with the child already dead | fixed, locally_verified | T3 waits for "locked" and its own failed try first |
| F5 | RISK | final read | final | a second hand run while the first waits doubles the engine calls | fixed, locally_verified | step 5's note |
| F6 | RISK | final read | final | Apple citation not followed | refuted | B3's quote |
| F7 | NIT | final read | final | the run id and date were set before the wait | fixed, locally_verified | "Where" |
| F8 to F14 | NIT | final read | final | budget ceiling, duration format, "another AI check run", T4/T5 timeouts, status rows, table details, anchors and the `SHIM` import | fixed, locally_verified | — |
| W1 | BUG (contradiction) | wording pass | — | "at least 5 minutes apart" false past twelve sites; then "5 minutes apart" exact | fixed, externally_reverified (second confirmation: clean) | — |

Cost: rounds 1 to 3 and the final read, about 1,690 s of reviewer time and 610,000 tokens; the wording pass and confirmations 162 s, 83,708 tokens. The plan's cost was not announced to the maintainer before round 1, as the global rules ask; it is reported here instead.
