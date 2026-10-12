# DIFF review — the rename from website-builder to Webcroft — 2026-10-04

> **Superseded 2026-10-07:** the name changed again, to Croftweaver, before this merged. The
> Croftweaver pull request carries these edits over; its own review is in
> `REVIEW-diff-2026-10-07-chore-rename-croftweaver-514d292.md`.

Branch `chore/rename-webcroft`, from `origin/main` (`4bddcad`) to the PR head. The change
renames the product, its addresses and the handoff zip everywhere outside this folder, and
teaches the private-name check (`scripts/check_clean.sh`) the repository's new name. The
pull request stays a draft until the repository is renamed on GitHub: its links point at
the new address.

Depth: **Normal** (mostly prose and names, plus one line of a guard that decides whether
private names reach a public repo). Seats: Codex CLI (its default model, read-only) in
rounds 1 and 2; a fresh-context reviewer agent of the host, on a different model than the
authoring session, in round 1. ollama-cloud (`kimi-k3`) was started for round 1 and failed:
the account was at its weekly usage limit, and a second cloud tag gave the same answer, so
no review came from that tier. Consent: the owner, this session ("prepare the toolkit
rename PR as a draft").

| Round | Head reviewed | Seat | BUG / RISK / NIT | What it found, in short |
|---|---|---|---|---|
| 1 | `de7962a` | Codex | 1 / 2 / 0 | a longer name joined by two dots (`<owner>/webcroft..x`) blanked as a self-link (older than this branch); no test noticed a wrong back-reference in the replacement; the README names `webcroft.zip` before a release carries it |
| 1 | `de7962a` | fresh-context agent | 1 / 2 / 6 | the first commit's message said all four new cases failed against the old pattern (one did); the same back-reference and zip findings; the "formerly" note overstated what keeps working; any host or path accepted in front of the name; "the builder" in a worked example; "webcroft clone" in `whats-new.sh`; rename-only skill updates for earlier sites; unzipping over an older folder |
| 2 | `e42b14e` | Codex | 0 / 0 / 1 | a test comment still said "four cases" |
| 3 (merge link) | `1e93f62` | Codex (gpt-6.1-sol, medium, read-only, 175 s, 77k tokens); ollama-cloud (`kimi-k2.7-code`, 241 s, counted by hand: the script rejected its terminal-garbled reply, which is a complete review) | 0 / 0 / 0 in scope; outside scope 1 BUG (Codex), 1 RISK + 1 NIT (ollama), all in code main added | the rebase kept every rename edit; README's leak-check note now names the new repo |

13 findings over 2 rounds, two of them reported by both seats, so 11 distinct. Round 3 found
nothing in the rename itself.

## Dispositions

- **Fixed, each with a case in `scripts/test_clean_denylist.sh`:** the two-dot name (the
  pattern no longer accepts a second dot after the name); the back-reference (a listed name
  right after a self-link must still be reported). Each of the four new cases fails when the
  pattern is broken in the way it guards against: second dot allowed again, or the
  replacement keeping group 2 or 3 instead of 4.
- **Fixed in text:** the first commit's message (rewritten before the branch was pushed);
  the README note (it now says what GitHub redirects and how to point a clone at the new
  address); `whats-new.sh` says "suite clone", because a clone made before the rename sits
  in a folder with the old name; the stale test comment.
- **Comment only — any host or path in front of the name.** Older than this branch, and the
  README badge needs a path in front (`.../release/<this repo>`). Tightening it would need an
  exception for that URL. The comment in `check_clean.sh` now says what is not checked.
- **No code change — the zip name.** The pull request states the order: rename the
  repository, merge, cut 0.30 with `webcroft.zip` straight after, and update any release
  runbook that still names the old zip.
- **For the release notes — rename-only skill updates.** `whats-new` will list `copywriting`,
  `search-console-insights` and `website-review` for sites built earlier; the pull request
  carries the sentence.
- **Declined:** "the builder" in the `website-story` worked example (a generic noun, not the
  product name; changing a skill for it would flag one more skill in every built site);
  unzipping a newer zip over an older folder merges both (older than this branch, and the
  README already says to use a newer unzipped copy).

## Evidence

- `make check` passes in the worktree with the name list read (no "skipped" line), and
  inside the unzipped zip outside any git repository.
- `make smoke` builds `dist/webcroft.zip` (286 files) and its integrity check passes; the zip
  has no top-level folder, which is why the README now unzips into one.
- `make test`: 187 tests pass, none skipped.
- `scripts/test_clean_denylist.sh`: 21 cases pass with `/bin/bash` 3.2 and BSD `sed`, `grep`
  and `awk`. Run against the check as it was on `origin/main`, the case that expects a
  self-link under the new name to pass fails.
- Not run by any seat or locally: the GNU tools. CI on the pull request covers them.
- `git grep -n -i 'website-builder' -- ':!docs/reviews'` shows only the deliberate leftovers
  (the installers' backup suffix and its test, the template comment in `ship.sh`, a German
  example title), the README's "formerly" note, and the name check with its test.

**Verdict:** clean after round 2. The fix for round 2's nit was not sent for a third round.

## Round 3 — after the rebase onto main (2026-10-06)

Another session took the branch over and rebased it onto `origin/main` at `b55b66b`, 142 commits
past the old base `4bddcad`. The rebase had no conflicts. One leftover came with it: a README
paragraph that main gained in #169 still called `karero/website-builder` this repo's own reference.
Commit `1e93f62` names the repository under its new name and the former one. Artifact: the merge link
(`scripts/merge_link.sh 4bddcad e42b14e b55b66b`), 38 KB, sent with the prior findings via
`--verify`. Consent: the owner, this session ("bring #147 up to date with main, review that
update again ... do it now").

- **In scope: clean.** Codex compared the rename's edits in all 19 files before and after the
  rebase: 17 match exactly, README and the denylist test kept theirs and gained the fixes. It
  ran the self-link `sed` against both names and the two-dot and back-reference cases.
- **Refuted — RISK, `actions/*@v7` may not exist** (ollama). `gh api repos/actions/{checkout,
  setup-node,setup-python}/git/ref/tags/v7` returns each tag, and `clean` is green on main at
  `b55b66b`.
- **Follow-up — NIT, a `clean.yml` comment** says the Python 3.9 leg tests macOS's stock python3,
  but it runs on `ubuntu-latest` (ollama). Main's text, not this change's.
- **Follow-up — BUG outside this change, `geo_check.py:698`** (Codex): `{"ai_overview":[{}]}`
  raises an uncaught `AttributeError` before the response-shape guard. The rename touches two
  strings in that file and neither is on that path; the defect is on `origin/main`. Reported to
  the owner for its own fix, not deferred into this gate.

Checks at `1e93f62`: `make test` 191 pass; `scripts/test_clean_denylist.sh` all pass. `make check`
and `make smoke` fail with the private name list read, on two review trails main gained on
2026-10-05/06 (`REVIEW-diff-2026-10-05-pr166.md`, `REVIEW-diff-2026-10-06-pr175.md`); `origin/main`
fails the same way. #180 removes those names. CI does not see it: it has no copy of the list.

**Verdict:** clean after round 3.
