# DIFF review — branch fix/move-prep-036 — the move script's preparation, six fixes for release 0.36

Base `c838cb69` (merge base with origin's HEAD) · depth: High (the move script changes what a User's
live domain does) · verdict: CLEAN at round 9 on the last change, after the manager chose to make
the lastmod scan a warning · authority used: WORKTREE-WRITE and
BRANCH-COMMIT. This session (the 0.36 move-prep build) created the worktree and the branch.

Seats: Codex (gpt-6.1-sol, read-only) alone in every round. The melious seat (glm-5.3) failed each
round with "out of balance"; by the owner's rule (2026-10-27) no rerun is owed, so each round stands
on Codex alone. Rounds 1 to 3 also had a fresh-eyes host pass (an Opus sub-agent, read-only), whose
tokens were not kept. Gate id 20261116T230248Z-74626: 9 rounds, 468,929 tokens logged for the seats.
Plan: the 0.36 move-prep plan, kept in the maintainer's private plan folder.

Fixes 1, 3 and 6 are prose or one-line wording; their gate is the builder's read of each changed
sentence against the code line it cites, plus Codex's read of the diff in round 1.

| Round | Reviewed head | Artifact | Codex seconds, tokens | BUG / RISK / NIT |
|---|---|---|---|---|
| 1 | `1234683f` | full diff against `c838cb69` | 208 s, 80,375 | 2 / 4 / 0 (+ 3 NIT from fresh-eyes) |
| 2 | `8aeea763` | delta, verify of round 1 | 180 s, 65,005 | 2 / 1 / 0 (+ 1 RISK, 1 NIT from fresh-eyes) |
| 3 | `f773cbb1` | delta, verify of round 2 | 119 s, 38,959 | 1 / 0 / 0 (+ 1 RISK, 3 NIT from fresh-eyes) |
| 4 | `15342f80` | delta | 130 s, 44,090 | 2 / 0 / 0 |
| 5 | `050042cb` | delta | 137 s, 52,141 | 1 / 0 / 0 |
| 6 | `c399d0de` | delta | 161 s, 37,369 | 1 / 0 / 0 |
| 7 | `d481229f` | delta | 97 s, 49,061 | 1 / 0 / 0 |
| 8 | `0fcce419` | delta of the warning change | 191 s, 59,628 | 1 / 0 / 0 |
| 9 | `e6d65456` | delta of the round 8 fix | 110 s, 42,301 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex | 1 | The lastmod scan counted a line inside a block comment, and cut a line at a URL's `//`. | fixed in `8aeea763` | Tests 2b: block comment (no gap), URL before lastmod (gap). |
| F2 | BUG | Codex | 1 | "After 10 minutes I ask you again" contradicted the 15-minute guard. | fixed in `8aeea763` | The line says "Please say yes within 10 minutes. After 15 minutes I have to ask you again, unless an address is left down, which I finish first." Tests 4 and 4u. |
| F3 | RISK | Codex | 1 | The sitemap claim had no read of the library. | fixed in `8aeea763` | Evidence file holds file and line excerpts of `@astrojs/sitemap` 3.7.4 and 3.7.5 (the starter locks 3.7.5): the `lastmod` Date is written as an ISO time in the entries and the index. |
| F4 | RISK | Codex | 1 | "Read passes check" had no run behind it. | fixed in `8aeea763` | Reworded to "is not refused by `check` (read from the code, not run)". |
| F5 | RISK | Codex | 1 | The CORS header was shown as proof of Pages. | fixed in `8aeea763` | A `platform=` line is believed first; the header case says "likely". Test 5f. |
| F6 | RISK | Codex | 1 | "63 to 98 seconds" and "a few seconds" lacked logs. | no change | Both sentences are on origin/main in `docs/MOVE-TO-WORKERS.md` (section 3 and line 41); the new text keeps "in the tests". |
| F7 | NIT | fresh-eyes | 1 | The ready list's last box told the owner to look for a "Next:" line that `check` does not print. | fixed in `8aeea763` | It says the status page names `record` under "What to do next". |
| F8 | NIT | fresh-eyes | 1 | A comment said "that run's check". | fixed in `8aeea763` | "the plain run's check". |
| F9 | NIT | fresh-eyes | 1 | `makeApi` errors carry no `cause.code`. | no change | The PR text says site fetches only. |
| F10 | BUG | Codex | 2 | `sitemap(),// lastmod: new Date()` still read as a gap; a string holding `/*` hid a real lastmod. | fixed in `f773cbb1` | One pass cuts comments and blanks strings. Tests 2b. |
| F11 | BUG | Codex | 2 | `platform=unknown` printed "the Worker". | fixed in `f773cbb1` | Only `pages` and `worker` are named; other values are quoted. Test 5g. |
| F12 | RISK | Codex | 2 | Evidence read sitemap 3.7.4, the starter locks 3.7.5. | fixed in `f773cbb1` | The 3.7.5 read was added to the evidence. |
| F13 | RISK | fresh-eyes | 2 | Test 4's wrong-code assertion could not fire. | fixed in `f773cbb1` | `doesNotMatch(/say yes within/i)`. |
| F14 | NIT | fresh-eyes | 2 | A comment named only the CORS header; a doc line was too wide. | fixed in `f773cbb1` | Both. |
| F15 | BUG | Codex | 3 | A regex literal holding `//` hid a real lastmod. | fixed in `15342f80`; then made moot by F21 | The scan cuts regex literals. |
| F16 | RISK | fresh-eyes | 3 | `platformOf` counts `platform=staging` as the Worker while `check` quotes it. | deferred | BUGLOG row 2026-11-17; nothing in the kit writes a `platform=` line (re-sorted: rare). |
| F17 | NIT | fresh-eyes | 3 | Two near-copy comment/string regexes. | deferred | BUGLOG row 2026-11-17. |
| F18 | NIT | fresh-eyes | 3 | No test of the string blanking; a value over 20 characters was cut without a mark. | fixed in `15342f80` | A test; an ellipsis. |
| F19 | BUG | Codex | 4 | A regex literal after `return`, and a division split over two lines, hid a real lastmod. | fixed in `050042cb`, later changed by F20 | Tests 2b. |
| F20 | BUG | Codex | 5, 6, 7 | Each new rule for `return` produced a false gap somewhere else: `weights.return / 2`, `weights. return / 2`, a name ending in `return`, then `return /'/` followed by a string that spells the setting. | superseded by F21 | The scan is a guess; every rule moved the false gap. |
| F21 | decision | the manager | 7 | Cut, don't patch: the lastmod scan becomes a warning in `check` (a plain line naming the file and the fix, exit code unchanged). `record`'s refusal still names the cause. The regex was left as it was. | done in `0fcce419` | Tests 2a and 2b assert exit 0 and the warning line; entered through `main()`. |
| F22 | BUG | Codex | 8 | The new git reads in the warning scan could still stop `check` with exit 1. | fixed in `e6d65456` | `cmdCheck` catches that stop and prints "Could not look for a sitemap lastmod set to the build time in astro.config: …". Test 2a with a gitlink named `astro.config.mjs` (listed by `ls-tree`, unreadable by `git show`); with the catch removed the test fails. |

Round 9 found nothing. Codex's UNVERIFIABLE entries throughout (the sitemap library's behaviour in a
real build, Cloudflare's permission responses, the timing figures, the earlier test results) stay
unverified by a run; the code marks the first two "read, not run" and the third "in the tests".

Not built, on purpose: the click-by-click token text (fix 3's dashboard part). The maintainer decided
on 2026-11-17 to ship without it; the BUGLOG row "The move token's set-up" stays open and says the
clicks follow after a signed-in look and come before 0.36 ships.

Final checks on `e6d65456`: `node --test skills/new-website/scripts/tests/move-to-workers.test.mjs`
and `make check`; their results are in the PR.
