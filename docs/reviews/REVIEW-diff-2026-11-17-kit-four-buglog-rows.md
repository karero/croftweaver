# DIFF review — branch fix/kit-four-buglog-rows — four BUGLOG rows from the guide's 0.35 update (deploy.sh, ship.sh, the Workers config test, the Playwright fallback)

Base `5a0b3010` · depth: Normal (deploy scripts and their tests; no user data, auth or money) ·
reviewers: Codex alone (REVIEW-RULES), plus a fresh-eyes Claude sub-agent in round 1 · verdict: CLEAN
after round 5 · authority used: WORKTREE-WRITE and BRANCH-COMMIT. This session (kit-four-fixes)
created the worktree and the branch. Gate id 20261117T103847Z-97380.

Artifact: round 1 `git diff 5a0b3010..b2218490`; each later round the delta from the last reviewed
head, with `--base` that head and `--verify` the prior findings and dispositions; all with
`':(exclude)docs/reviews/'`. The final read (`--wording-pass` over `git diff 5a0b3010..d1d83fc1`) ran
Codex alone.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `b2218490` | full | Codex; fresh-eyes (Opus sub-agent, read-only) | codex 6,546 s, 108,298; fresh-eyes not recorded | 2 / 2 / 3 (+ unverifiable claims) |
| 2 | `698e87e5` | delta, verify of round 1 | Codex (medium) | codex 214 s, 51,596 | 1 / 0 / 1 |
| 3 | `b72bb61d` | delta, verify of round 2 | Codex (medium) | codex 126 s, 37,617 | 1 / 0 / 0 |
| 4 | `cf45218f` | delta, verify of round 3 (cut) | Codex (medium) | codex 123 s, 45,025 | 0 / 1 / 0 |
| final read | `d1d83fc1` | whole diff, `--wording-pass` | Codex (medium) | codex 189 s, 44,908 | 0 / 1 / 0 |
| 5 | `61fda93c` | delta, verify (cut) | Codex (medium) | codex 179 s, 50,110 | 0 / 0 / 0 |

Logged total 337,554 tokens over 6 reviewer seat runs (the gate's line); fresh-eyes is not in it.

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex | 1 | The new live-check tests assumed the site's address is https://example.com. | fixed | The expected address is read from the copy's own `site:` line by a reader deploy.sh does not use. |
| F2 | BUG | Codex | 1 | The test's discovery step read wrangler.jsonc with strict JSON.parse: a trailing comma made every deploy check skip as "Cloudflare Pages". | fixed | A copy with trailing commas runs the deploy cases; with strict parse put back it printed "Skipped". |
| F3 | RISK | fresh-eyes | 1 | The comma pass in workers-config.spec.ts had no test of its own. | fixed | Two tests; cutting the pass fails the comma test. |
| F4 | RISK | fresh-eyes | 1 | The drift guard skipped silently when only one script had `site_count()`. | fixed | `bad` if exactly one has it. |
| F5 | NIT | fresh-eyes | 1 | The comma pass accepts `{,}` and `[,]`. | no change | Harmless; Wrangler's reader was not run on that input (said to the reviewers each round). |
| F6 | NIT | fresh-eyes | 1 | The `.bin` loop assumed relative symlinks. | fixed (F10 finished it) | |
| F7 | NIT | fresh-eyes | 1 | The Playwright gate checks that the shell folder exists, not its executable. | no change | A wrong folder fails loudly at launch. |
| F8 | — | Codex | 1 | Unverifiable: arrays in Wrangler's reader, the Playwright launch, a truncated test log. | settled | Evidence file holds the array run (exit 0, and CommaExpected exit 1 for a missing comma), the launch trace, the gate matrix for full-only, shell-only and both installs, whole test records. |
| F9 | BUG | Codex | 2 | The comment-only test rewrite handled single quotes only. | fixed | New case site-dq; a single-quote-only rewrite stops the run. |
| F10 | NIT | Codex | 2 | An absolute symlink target in `.bin` got the `.bin/` prefix. | fixed | Probe printed the absolute and the relative target correctly. |
| F11 | BUG | Codex | 3 | A site already double-quoted left site-dq with nothing to commit and the suite stopped. | fixed, then cut | Commit only on a change; then the rewrites became whole-line writes from the address read, so no case reads quoting. Both a single- and a double-quoted site run all four cases. |
| F12 | RISK | Codex | 4 | The whole-line rewrites delete code after `site:` on the same line. | fixed | The cases need a line holding only `site: '…',`, else a note and a skip. |
| F13 | RISK | Codex (final read) | — | The guard checked one `site:` line but the rewrites touched every such line. | fixed | The cases run only when exactly one line starts with `site:`; a second such line skips with the note. |
| F14 | — | Codex | 2 to 5 | Unverifiable: that the NEL rule alone suppresses Report-To; the two previews differ by the whole `_headers` file. | not settled | Stated in the evidence and in BUGLOG row 346 as judgment. A third deploy would isolate it. |

Re-sorted: none. Kind `site-quote-fixture` earned rounds 4 and 5; the fixes were cuts (whole-line writes; exactly one `site:` line), with the cut text in the gate's running-total line.

Mutations (new tests against the old code): old ship.sh fails W5 (trailing comma in a string and an object); old deploy.sh site reader fails site-comment (curl asked the commented address); old spec fails the trailing-comma test (a spec run with the comma pass cut); old discovery prints "Skipped".

Checks: `make check` passed (exit 0) on the head after the round 1 fixes; the final head's run is below.
