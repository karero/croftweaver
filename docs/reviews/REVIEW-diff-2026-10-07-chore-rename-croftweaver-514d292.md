# DIFF review — chore/rename-croftweaver — website-builder becomes Croftweaver

Base `f812647` · depth: Normal (mostly names and prose, plus the self-link rule of the
private-name check, which decides what may reach a public repo; mutation-tested) · verdict:
CLEAN in code; F2 open on a missing prerequisite (the GitHub rename) · authority used: the
owner in this session — "bring #147 up to date with main, review that update again ... do it
now" (2026-10-06) and "yes" to sending the diff to Melious (2026-10-08).

This carries over the reviewed Webcroft version of the rename (#147; its rounds are in
`REVIEW-diff-2026-10-04-rename-webcroft.md`) with the name changed to Croftweaver, onto a main
whose private-name check had been rewritten since. That part was redone by hand.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `514d292` | full, 34 KB | Codex CLI (gpt-6.1-sol, config effort, read-only) | 536 s, 84k | 0 / 2 / 0 |
| 1 | `514d292` | full | fresh-eyes agent (sonnet, read-only, ran the leak-check tests) | 149 s, 108k | 0 / 2 / 4 |
| 1 | `bf76317` | full, + F1's comment | Melious (glm-5.3, HTTP API, text only) | 128 s, 29k | 0 / 1 / 2 |
| 2 | `608f85e` | delta since `514d292`, `--verify` | Codex (medium) · Melious (glm-5.3) | 90 s, 29k · 31 s, 7k | 0 / 1 / 1 (same RISK from both) |
| prose re-gate | `9de3b79` | delta since `608f85e` (two comments) | Codex (medium) | — | 0 / 0 / 0 |
| extra, owner-requested | `d067172` | full, 34 KB | Antigravity (`agy`, CLI default model unconfirmed, plan mode, no tools) | 399 s | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | RISK | fresh-eyes | 1 | the old-name allowance goes by name, not by what the link leads to | kept by design; comment states it (locally_verified) | `bf76317`, reworded in `608f85e` and the closing commit |
| F2 | RISK | all three | 1 | badge, clone, security-report and zip links and the redirect claim hold only after the rename and the next release | open on a missing prerequisite: checked live right after the rename | order: rename → merge → v0.31 |
| F3 | NIT | Melious | 1 | `make package` left a pre-rename `dist/website-builder.zip` | fixed (locally_verified, externally_reverified r2 by both) | `3773743`; an empty old zip is gone after `make smoke` |
| F4 | RISK | Codex | 1 | "100% compatible" in `docs/ANTIGRAVITY.md` | follow-up: older than this change | — |
| F5 | NIT | fresh-eyes | 1 | the new tagline is not a rename | refuted: part of #147's reviewed edits | README |
| F6 | NIT | fresh-eyes, Melious | 1 | the unzip line is a fix, not a rename | fixed in text: the commit and PR say so | `514d292` message |
| F7 | NIT | fresh-eyes | 1 | old name in an eval fixture and a test label | refuted: generic noun / historical reference | — |
| F8 | NIT | fresh-eyes | 1 | `..` right after a self-link fails closed | refuted: intended, the `..x` case must fail | test "joined by two dots" |
| F9 | RISK | Codex, Melious | 2 | the comment's "only its owner could ever" lacked support | fixed: claim removed, the accepted trade-off stated (externally_reverified, prose re-gate) | `9de3b79` |
| F10 | NIT | Melious | 2 | `package.sh` comment outlives its subject | fixed (externally_reverified, prose re-gate) | `9de3b79` |

Waivers and deferrals: none.
Follow-ups: F4.
Notes: round 1 ran its seats on two heads, `bf76317` adding one comment line; Melious had not
been given this repo before and the owner said yes first. My own `bf76317` comment named the
account and the check reported it: caught by `make smoke`, not by a reviewer, fixed in
`608f85e`. Checks at the closing head: `make check` (names read), `make test` 191,
`make smoke` 320 files, `scripts/test_clean_denylist.sh` all pass; four mutations of the
self-link rule each fail at least one case.
Antigravity (2026-10-08, the owner asked for it): no findings. Its open questions were settled
here: the exact two-rule `sed` chain on macOS `/usr/bin/sed` blanks both self-links and keeps
`..x`; CI's `clean` job ran `scripts/test_clean_denylist.sh` on ubuntu (GNU sed) for this
branch and passed; `unzip croftweaver.zip -d croftweaver` creates the folder (exit 0).

## Round 3, 2026-10-11: the change on today's main, after the GitHub rename

Taken over by the session that released 0.30, on the owner's word ("yes to: May I take over
#212?", 2026-10-11): the session that wrote rounds 1 and 2 was no longer running. Authority
used for this section: POST, WORKTREE-WRITE and BRANCH-COMMIT — atom B, that sentence;
GATED-THIS-DIFF — atom A, the full round below.

Why a full round and not a merge link: `main` had gained about 50 pull requests since round 2
(old merge-base `f812647`, new `cf2955b`). The merge link came to 75 KB, the whole change against
today's `main` to 37 KB, so every seat read the whole change. `b027165` merges `main`; three
conflicts were resolved by hand (the starter prompt in `README.md` and
`docs/GETTING-STARTED.md`, and the README's unzip line), each taking main's newer text with the
new name. The repository was renamed on GitHub that day, before the round.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 3 | `b027165` | full: `origin/main...b027165` (`docs/reviews/` left out), 19 files, with context excerpts and the live link checks | codex-cli 0.162.1, gpt-6.1-sol, config effort, read-only; melious glm-5.3, HTTP API, text only; fresh-eyes: Claude Sonnet through the Agent tool, read-only by instruction, ran the two test scripts and HEAD requests | codex 205 s / 85,952; melious 488 s / 38,632; fresh-eyes 141 s / 112,128 | 0/0/0 (codex), 0/1/1 (melious), 0/2/2 (fresh-eyes); 0/2/3 after dedup |

`reviewers: codex OK, melious OK`. Unverifiable entries: 10 asked, none confirmed as a finding.
The ones about GitHub were looked at: the old web address answers 301 to the new one, `git
fetch` over the old address works from a clone that still uses it, the old
`latest/download/website-builder.zip` link delivers the 0.30 zip, the security link reaches the
new address, and the badge answers 200.

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F2 | RISK | all three, round 1 | 1 | the links hold only after the rename | closed: checked live after the rename | the checks above; `latest/download/croftweaver.zip` answers 404 until 0.31 exists, which is F11 |
| F11 | RISK | fresh-eyes, melious | 3 | between the merge and the 0.31 release the README names a `croftweaver.zip` that the latest release does not have | open for the owner: closed by releasing straight after the merge, as the merge order says | `README.md` "Prefer a download?" and the manual install; the old-name download link keeps working in that window |
| F12 | RISK | fresh-eyes | 3 | the README's new tagline and its sentence on weekly SEO and GEO are copy changes, not a rename | fixed in text: the pull request says so; the owner was asked whether the tagline ships | same finding as F5, which was refuted as part of #147's reviewed edits; the owner's answer is recorded in the pull request |
| F13 | NIT | fresh-eyes | 3 | `skills/website-story/evals/files/POSITIONING.md` says "the website builder itself" | refuted | a generic noun in a fixture comment, lower case and unhyphenated, as F7 ruled |
| F14 | NIT | fresh-eyes | 3 | a self-link followed by two dots and nothing else (an ellipsis) is no longer blanked; no test for that case | refuted | intended: the `..private` case must fail, and the tests assert it; the reviewer asked for no fix |
| F15 | NIT | melious | 3 | `make package` deletes a `dist/website-builder.zip`, so the hand-made copy for 0.31 must be made last | fixed in text | the pull request's merge order says the copy is made right before the upload; `package.sh` is unchanged |

Round 3: 5 findings (0 BUG, 2 RISK, 3 NIT): 2 fixed in text, 2 refuted, 1 open for the owner
(F11). No fix changed what runs, so no further round is owed. Whole gate: 3 rounds and a prose
re-check, 20 findings, no BUG.

Checked by the author at `b027165`: `make smoke` passes and builds `dist/croftweaver.zip` (329
files); the two starter-prompt copies are identical; outside `docs/reviews/` and the two
trackers the old name remains only in the places the pull request lists.

The commit that adds this section changes nothing outside `docs/reviews/`; the stamp names it,
and the reviewed scope is the one at `b027165`.

After round 3, `main` gained #262 (one doc file and its trail). It is merged in at `ae9a125`; the merge link over the change's own files is empty, so the reviewed scope is unchanged. My first wording of row F14 quoted the two-dot form with the account name in front, and the private-name check reported it, as it should: caught by `scripts/check_clean.sh`, reworded.
