# Review trail: publish each release to the branch `directory` (DIFF gate, High)

Change: `scripts/build_directory_tree.sh`, `scripts/publish_directory.sh`, the last step of
`.github/workflows/release-tag.yml`, tests in `scripts/plugin.test.mjs`, the README's release
steps, `.claude-plugin/icon.png`, guard lists, BUGLOG rows, one line in
`skills/website-review/SKILL.md`. Plan: `docs/reviews/SKILL-PLAN-directory-plugin-folder.md`
(#401, merged as 8ec4cb88). Depth High: a release workflow that pushes what users install.

Seats: Codex (`CODEX_EFFORT=config`) and fresh-eyes (Opus 5.5) in rounds 1 to 3. **Degraded
pair:** GLM 5.3 on melious could not run ("Insufficient balance … Available: 0", 2026-10-25)
and ollama's weekly quota was used up (429), so Codex was the only cross-model seat.

Checks before round 1: `make check` exit 0; `make test-plugin` 30 tests, 29 pass, 1 skipped
(the RELEASE_TAG test, which needs a tag). Seven hand mutations each made one new test fail:
drop list without facts-check, no ancestry check, a forced push, no `Source:` refusal, an `if:`
without `steps.move`, no re-run guard, no main check.

## Round 1 (diff 11a13e2d..d5cf422f)

timings: codex 279s (79,882 tokens), fresh-eyes 289s (117,213 tokens).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| D1 | fresh-eyes | BUG | Run from a subfolder, `ls-tree` reads paths from there: the tree is empty and the publish script pushes it, saying it succeeded. Reproduced. | Fixed: the build works from `git rev-parse --show-toplevel` and refuses a commit without `.claude-plugin/plugin.json` or `skills`; a test runs it from `skills/` and on a commit with no plugin (fails with the `cd` removed). |
| D2 | codex | BUG | `website-review/SKILL.md` tells a user to copy `independent-review` "from the Croftweaver suite", which a directory install lacks. | Fixed: it names https://github.com/karero/croftweaver for that case; the BUGLOG row is dropped. `seo-reposition` defers to `website-review`'s section. |
| D3 | codex | BUG | README and workflow header: "a red run means plugin users are on the release before" is no longer true when only the last step fails. | Fixed: both say which step failed means what. |
| D4 | codex | RISK | Whether the directory follows `directory` and accepts this payload is unverified. | Partly checked: the trial's Validate passed on `directory` and Anthropic's publish page says the listing follows the tracked branch (plan trail). Seen end to end only after the listing; open until then. |
| D5 | fresh-eyes | RISK | A `stable` moved back to an older release by hand turns the run red and leaves `directory` ahead. | Re-sorted: rare (rolling a release back by hand). The refusal is loud; no code. |
| D6 | fresh-eyes | RISK | A hand run with `commit.gpgSign=true` signs the bot's commit or waits on a pinentry. | Fixed: `git -c commit.gpgSign=false commit-tree`. |
| D7 | fresh-eyes | NIT | The README names the script but not the `commit-tree` line the plan named. | Refuted: the script is that line and its refusals together (the plan's F42/F45 follow-up, done). |
| D8 | fresh-eyes | NIT | A `Source:` commit missing from the clone reads as "a later release". | Fixed: `git cat-file -e` first, with its own message. |
| D9 | fresh-eyes | NIT | A third queued run in the concurrency group cancels the waiting one. | Re-sorted: rare (three release runs within minutes); a cancelled run shows as such. |
| D10 | fresh-eyes | NIT | The workflow and force tests match text. | Accepted: the tests say so; the real guard against a force push is a branch rule (the maintainer's setting). |

After the fixes: `make check` exit 0; `make test-plugin` 31 tests, 30 pass, 1 skipped.
Round 2 is earned by D1 to D3.

## Round 2 (verification, diff d5cf422f..836cfdb2)

timings: codex 304s (76,951 tokens), fresh-eyes 182s (105,216 tokens). D1, D2, D8 confirmed.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| D11 | codex (BUG), fresh-eyes (RISK) | BUG | The D1 `cd` moved a relative `--out` folder to the clone's top. Reproduced by both. | Fixed: no `cd`; `ls-tree --full-tree` counts paths from the top. Testing that found more: `git archive` from a subfolder wrote only that folder (214 of 224 files), so the archive runs with `-C` the top. The subfolder test now also unpacks with a relative `--out` and counts the files (fails without `-C`). |
| D12 | codex | BUG | D3 half-fixed: the header's advice fits a tag run only; a hand-moved `stable` has already moved; the last step can fail after its push went through. | Fixed: the header says "on a tag run" and points to the README; the README and header say the script reports when `directory` already holds the release (re-running is how to tell). |
| D13 | fresh-eyes | NIT | D6's premise is false: `commit-tree` does not read `commit.gpgSign` (git 2.9.1 on), shown with `gpg.program=false`. | D6 re-marked Refuted; the harmless `-c` stays. |
| D14 | fresh-eyes | NIT | The website-review sentence was hard to read and "it" was unclear. | Fixed: re-worded; the URL clause names "that folder". |
| D15 | fresh-eyes | NIT | A bare repo fails at `--show-toplevel`. | Fixed by D11 (no `--show-toplevel` before `--out`). |

After the fixes: `make check` exit 0; `make test-plugin` 31 tests, 30 pass, 1 skipped.
Round 3 is earned by D11 and D12.

## Round 3 (verification, diff 836cfdb2..51ed074c)

timings: codex 310s (72,231 tokens), fresh-eyes 333s (100,581 tokens). D11, D14, D15 confirmed by both; fresh-eyes confirmed D12, Codex did not (D16).
Fresh-eyes ran against 51ed074c while the D16 fix below was being written in the same
checkout; its D12 confirmation is of the earlier wording, which D16 replaced.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| D16 | codex | BUG | D3/D12 again: a failed run does not tell which branches moved (a retried tag after an earlier attempt moved `stable`; an older tag refused while `stable` is newer). | Cut, not patched (kind failure-wording, third round): the README and header no longer infer state from the failed step. The README says to look first with `git ls-remote origin stable directory`, then gives the command for each step that can fail. |
| D17 | codex | RISK | D4 restated: the listing's behaviour after release is unseen. | Open until the listing exists; checked then (first release after listing: the version Anthropic serves names the new commit). |
| D18 | fresh-eyes | NIT | `--out` in a bare repo prints a stray git error while succeeding. | Fixed: `--show-toplevel` quiet, falling back to `.`. |
| D19 | fresh-eyes | NIT | The header promised the README covers "each step". | Fixed: "see README.md". |

## Round 4 (verification, Codex alone, diff 51ed074c..d12bd0c8)

timings: codex 224s (65,262 tokens). "No BUG/RISK/NIT findings." It confirmed D16's cut, D11,
D15/D18, D2/D14, D8 and D10. Still unverifiable, as before: D4/D17 (the listing), D9 (three
overlapping runs), whether `directory` gets a no-force rule (the maintainer's setting). The
rounds end here.

## Final full read (whole change 11a13e2d..a40b8be2)

Kimi on ollama could not run (weekly quota used up), so a fresh host-model pass that had not
seen the change (Opus 5.5), 343s, 117,675 tokens. No BUG.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| D20 | full read | RISK | `grep … \|\| true` hid a grep error (exit 2): the build printed the empty tree and exited 0, so publishing would push it. Reproduced with a stub grep. | Fixed: `\|\| [ $? -eq 1 ]` lets only "nothing matched" through; the build also refuses a tree without `.claude-plugin/plugin.json` (with `--full-tree`: written without it at first, the subfolder test caught that). A test with a failing stub grep; it fails with both guards removed. Counted though rare: a silent wrong result. |
| D21 | full read | RISK | Nothing on GitHub stops a force push to or deletion of `directory`, and no file carried that to-do. | Fixed as a record: a BUGLOG row; the setting is the maintainer's. |
| D22 | full read | NIT | The plan lists an "A, B, then late C" case; the test covers an older tag run late, the same check. | Accepted: the same ancestor check; the test names it. |
| D23 | full read | NIT | The plan said the README gains the `commit-tree` line too. | Fixed in the plan: the script holds that line and its refusals. |
| D24 | full read | NIT | A hand rollback of `stable` turns the branch run red, unmentioned in the README. | Re-sorted: rare (D5); the error says why. |
| D25 | full read | NIT | The plugin.json test refuses any new key, stricter than "no component paths". | Intended: a new key gets a look before it ships. |
| D26 | full read | NIT | Plan status row 4 and the "255 entries" note were stale. | Fixed. |

Round 5 (pair seat Codex alone) is earned by D20.

## Round 5 (verification, Codex alone, diff 73337223..4370b4eb)

timings: codex 213s (64,634 tokens). D22, D24, D25 confirmed.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| D27 | codex | BUG | D20's test could pass with both guards removed: the stub grep closed its input, so `git ls-tree` died of SIGPIPE (141) with empty output. Reproduced six times. My own mutation run had failed the test by luck of timing. | Fixed: the stub reads all its input first; the test asserts exit 1 and the stub's message. Three runs pass; three runs with both guards removed fail. |

After the fix: `make check` exit 0; `make test-plugin` 31 tests, 30 pass, 1 skipped.
Round 6 is earned by D27 (a test that could not fire).

## Round 6 (verification, Codex alone, diff 4370b4eb..a1775b95)

timings: codex 197s (46,884 tokens). "No BUG/RISK/NIT findings." The rounds end here.
Checks at a1775b95: `make check` exit 0; `make test-plugin` 31 tests, 30 pass, 1 skipped.

Gate total: 6 rounds and a final full read, 27 findings (D1-D27), every BUG fixed; open:
D4/D17 (the listing, checked after the first release once listed) and D21's branch rule
(the maintainer's setting, BUGLOG). Reviewer tokens about 846,000 (the cost log's 766,647
for rounds 1-6 with fresh-eyes and the full read, plus round 1's first Codex run, 79,882,
logged under an earlier gate id). Degraded pair throughout: no GLM 5.3 (melious balance 0).
