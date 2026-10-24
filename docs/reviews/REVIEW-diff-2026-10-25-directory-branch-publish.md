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
