# DIFF review — branch fix/clean-plate-icons-whatsnew — four BUGLOG rows (icons `--setup`, icons spec, whats-new removal, whats-new no stamp)

Base `c1538949` · depth: Normal (shipped starter code, a script that removes a folder on a site; no user data, auth or deploy path) · verdict: CLEAN after round 2 and two re-gates of the wording edits · authority used: WORKTREE-WRITE and BRANCH-COMMIT.
This session (the clean-plate fixes, started by the coordinator for the Croftweaver manager) created the worktree and the branch.

Seats (REVIEW-RULES): round 1 Codex alone, as the brief said, plus a fresh-eyes Sonnet sub-agent (read-only). The `rm -rf` runs on an owner's site, so the manager asked for GLM 5.3 on melious beside Codex from round 2 on: round 2 ran the pair. The re-gates: Codex alone (a one-line message edit).
Gate id 20261118T111750Z-74764.

Artifact: round 1 `git diff origin/main...5621919c -- . ':(exclude)docs/reviews/'`; round 2 `git diff 5621919c..f4d099f8` with `--base 5621919c`, `--verify`, `--evidence`. Re-gates (not rounds): `git diff f4d099f8..3b1847b6` and `git diff 3b1847b6..7f9502d3`, each with its first commit as `--base`. Evidence: the test records, the old-code failures, and the manager's check of the favicon hashes (below).

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `5621919c` | full | Codex (gpt-6.1-sol, medium, read-only); fresh-eyes (Claude Sonnet, read-only) | codex 140 s, 92,422; fresh-eyes 382 s, 116,453 | 1 / 2 / 4 after dedup |
| 2 | `f4d099f8` | delta from `5621919c`, verify of F1-F7 | Codex (medium); melious (glm-5.3) | codex 234 s, 57,714; melious 136 s, 11,912 | 0 / 2 / 0 (both RISKs: F2 re-raised, and F8) |
| re-gate | `3b1847b6` | the wording edit | Codex (medium) | codex 107 s, 33,489 | 1 / 0 / 0 (F8) |
| re-gate | `7f9502d3` | the cut | Codex (medium) | codex 69 s, 29,239 | 0 / 0 / 0 |

Gate total after the last run: 341,229 tokens logged.

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex | 1 | `sitePath` in `icons.spec.ts` took the manifest's address as both base and own host, so a manifest on another host made its icon paths look like this site's files. | fixed in `f4d099f8` | `sitePath(href, base, own)`: `base` only resolves a link, `own` (the server under test, `SITE.url`) is the only host that counts. The old helper gives `/icon-192.png` for that case, the new one the whole CDN address (node, same inputs). New assertions for a manifest on another host and on this site. In a scratch copy of the starter: the two unit tests pass, the whole spec (11) passes after `make-icons --setup`, and the favicon-link mutation of the CI step is red with the CDN address in the failure. |
| F2 | RISK | Codex, fresh-eyes (re-raised in round 2) | 1 | The two favicon hashes are not shown to match what create-astro writes today. | refuted, with a limit | The manager's read of GitHub (`gh api repos/withastro/astro/contents/examples/minimal/public/<file>`, 2026-11-18, not re-run here) gives blob `f157bd1c…` (favicon.svg) and `7f48a94d…` (favicon.ico). Re-checked here: `git cat-file blob <id> \| shasum -a 256` in an existing local repo gives `2d7a3102…203f` and `09d2ac08…3d67`, the hashes in `make-icons.mjs` and `_site.py`. Not checked, and a judgment: that create-astro 5.3.2 copies `examples/minimal` unchanged. A wrong hash is a loud refusal on a new site, and `--replace` is the way out. |
| F3 | RISK | fresh-eyes | 1 | The no-baseline message printed `--before="$(first-commit date)"`: an empty date gave the suite's HEAD, a first commit made days after scaffolding gave a too-new commit. | fixed in `f4d099f8` | The message now prints `git -C <suite> log --format='%H %cs %s'` and says to pick a commit from before the site was made. Test asserts the line; the old message fails the new test. |
| F4 | NIT | fresh-eyes | 1 | The message said "holds template-test copies" for any `tests/` folder. | fixed in `f4d099f8` | Reworded ("tests exists, but …"). |
| F5 | NIT | fresh-eyes | 1 | The tests-only path exits before the Astro-major note. | refuted | `git show origin/main:scripts/whats-new.sh`: the old code exited 1 there, before that line. Not a regression. |
| F6 | NIT | fresh-eyes | 1 | A `SITE.url` with no scheme makes all seven icon tests throw "Invalid URL". | left | Loud; the starter's `SITE.url` is a full URL (`src/config.ts`). |
| F7 | NIT | fresh-eyes | 1 | The README clause lengthens a wrapped line. | left | No wrap rule in the README. |
| F8 | RISK | Codex | 2 | "Take an older one when unsure … hides none" in the no-baseline message: for a history A, B, A an older baseline can hide a change that was later reverted. | fixed by a cut in `7f9502d3` | The first re-gate found the softer wording ("lists more of the suite's changes") still wrong, so the claim was cut, not patched: the message says only to pick a commit from before the site was made. The second re-gate found nothing. |

Not checked: "newest first" for the printed `git log` (the default order of `git log`, one local run shows it newest first); the CI step "The icons spec fails on a favicon link on another host" itself (its equivalent was run by hand). Codex and fresh-eyes did not run the Playwright and make-icons suites (no dependencies in their sandbox); the author's runs are in the evidence. UNVERIFIABLE entries: about 6 asked over both rounds, none confirmed as a finding.
