# DIFF review — PR #276 — Croftweaver as a Claude Code plugin; skills name their files relative to their own folder
Base `714516a` · depth: Normal (instruction files eleven skills load, and the lines the orchestrator runs to find the suite; no user data, no deploy path) · verdict: OPEN · authority used: POST AUTHORITY — atom A (this session opened #276); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch)

Seats: Codex and GLM 5.3 on melious (`SECOND_SEAT=melious`), and in round 1 a fresh-eyes pass on a mid-tier model of the host's family. The owner's words, in this session on 2026-10-12: "push it and open the PR, then run the review"; both services were cleared for this repo the same day for #268 ("yes to all three").

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `7e7dcb2` | full: `714516a...7e7dcb2` without `docs/reviews/`, plus the plan `docs/reviews/SKILL-PLAN-capability-gaps.md`; in front of it, marked as context, the scaffold steps of `new-website` that use the lookup, the documentation passages relied on, what was observed with the CLI, and the test record | codex-cli 0.162.1, gpt-6.1-sol, config effort, read-only · melious HTTP API, glm-5.3, text only · fresh-eyes: a sub-agent on the host family's mid-tier model, read-only by instruction | codex 288 s / 90,530 · melious 188 s / 33,827 · fresh-eyes 193 s / 142,821 | codex 2/3/0 · melious 0/2/4 · fresh-eyes 0/5/5 · after dedup 2/5/7 |
| 2 | `b8a917c` | delta `7e7dcb2..b8a917c` without `docs/reviews/`, plus the plan's delta, with round 1's dispositions (`--verify`); as context the lookup, the permissions section, the whole test file, the test record and the live observation | codex-cli 0.162.1, gpt-6.1-sol, medium, read-only · melious HTTP API, glm-5.3, text only | codex 242 s / 59,242 · melious 214 s / 40,836 | codex 2/2/0 · melious 0/2/3 · after dedup 2/3/3 |
| 3 | `b85e728` | delta `b8a917c..b85e728` without `docs/reviews/`, plus the plan's delta, with round 2's dispositions (`--verify`); as context the lookup, the permissions section, the workflow and the test file whole, the test record and the two observations | same two seats, codex at medium | codex 314 s / 58,830 · melious 365 s / 45,261 | codex 2/2/0 · melious 0/2/2 · after dedup 2/2/2 |
| 4 | `02a9225` | delta `b85e728..02a9225` without `docs/reviews/`, plus the plan's delta, with round 3's dispositions (`--verify`); as context the permissions section, the README's release steps, the workflow and the test file whole, the test record and the `github` install | same two seats, codex at medium | codex 142 s / 52,529 · melious 321 s / 45,278 | codex 0/1/0 · melious 0/2/1 · after dedup 0/2/1 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| P1 | BUG | codex, fresh-eyes (as RISK) | 1 | `website-permissions`: the reworded commands look for `new-website` beside the skill, which the copy inside a site lacks, and that copy is the one the step serves | fixed — externally_reverified in part (round 2: melious clean; codex found it incomplete, P15) | `4b79a42`: the lines look beside the skill, then in the installed suite (`SKILLS_ROOT`, or `~/.claude/skills`). Tests run them: from a plugin's folder with a space in its path; from a site's copy with a home install; unfilled with `SKILLS_ROOT`, in a strict shell too; with no suite (fails, writes nothing). Codex proposed moving the two templates into this skill; not done, they would then exist twice |
| P2 | BUG | codex, fresh-eyes (as RISK), melious (as NIT) | 1 | `new-website`: left unfilled, the first candidate was read as a variable: a shell with unset variables as errors stops (`CLAUDE_SKILL_DIR: unbound variable`), and any other turns it into `/..`, so a folder `/new-website` would pass for the suite | fixed — externally_reverified (round 2, both seats, for the strict shell), then reworked for P16 | `4b79a42`: the candidate is in single quotes; unfilled it is a folder name that does not exist. Invariant: an unfilled name changes nothing for an assistant that fills nothing in. Tested with `bash -u` for an `.agents` install and for nothing installed; a test holds the quoting; putting double quotes back fails two tests |
| P3 | RISK | codex, melious, fresh-eyes | 1 | That Claude Code replaces the name by the skill's folder, in a fenced block and for a plugin's skill, is its documentation's word; no session observed it | fixed for a skill in a project, open for a plugin's skill until release 0.32 | Observed on 2026-10-13 in the building session, signed in, with a probe skill in a project's `.claude/skills/` (since deleted): a line `'${CLAUDE_SKILL_DIR}/..'` inside a fenced block arrived as `'<project>/.claude/skills/zz-croftweaver-probe/..'`, and the same in prose and in double quotes; `"${CLAUDE_SKILL_DIR:-}/.."` and `: "${CLAUDE_SKILL_DIR:=}"` arrived as written. For a plugin's skill the documentation says the same; the plan's "Done when" asks for that run after release 0.32. If false there, the scaffold falls back to `~/.claude/skills` and its first `cp` fails, loudly |
| P4 | RISK | codex, melious | 1 | A release that leaves both values at the last release passes `make test-plugin`, and plugin users stay behind | fixed — externally_reverified (round 2, both seats) | `4b79a42`: `.github/workflows/release-tag.yml` runs the tests on a pushed `v*` tag with the tag to compare; `RELEASE_TAG=v0.33` fails locally, `v0.32` passes. It reports after the tag exists and stops nothing. Since the switch to `stable` (P5) it compares the version alone, and also runs when `stable` moves |
| P5 | RISK | fresh-eyes | 1 | From the merge of a release's pull request until its tag is pushed, main names a tag that does not exist, and installing or updating fails, for users on the release before too | fixed — externally_reverified (round 2, both seats) | asked how a release should work, the owner chose "A 'stable' branch (Recommended)" on 2026-10-12. The entry installs from the branch `stable`, which a release moves to its tag after the tag is pushed; main never names what is not there. A test holds the entry to `stable`; the `release-tag` workflow checks the version against the pushed tag and against the tag `stable` is moved to |
| P6 | RISK | codex | 1 | `scripts/check_clean.sh` does not read `.claude-plugin/` | waived for this pull request — the owner, 2026-10-12 | asked how to handle it here, the owner chose "Leave to the follow-up (Recommended)"; the row in `docs/BUGLOG.md` stays open |
| P7 | RISK | fresh-eyes | 1 | `plugin-tests` is not a required check | accepted — to be done after the merge | asked whether it should be required, the owner chose "Yes, after merge (Recommended)" on 2026-10-12; a check cannot be required before its job is on main without holding every other pull request |
| P8 | NIT | melious, fresh-eyes | 1 | The home-folder guard missed `${HOME}`, names not starting with a letter, and files without one of ten extensions | fixed — externally_reverified (round 2, both seats) | `4b79a42`: every tracked text file under `skills/`, `$HOME` with or without braces, anything after the folder; a mutation in `templates/.gitignore` with `${HOME}` is caught |
| P9 | NIT | melious | 1 | The test needs a newer Node than "needs node" says (`Dirent.parentPath`) | fixed | `4b79a42`: files come from `git ls-files`; the Makefile and the header say node 20 or newer, git and bash |
| P10 | NIT | melious, fresh-eyes | 1 | Once merged, the README shows install commands that fail until release 0.32 exists | waived as it stands — the owner, 2026-10-12 | asked when it should merge, the owner chose "With release 0.32 (Recommended)": the pull request waits and merges as part of cutting that release |
| P11 | NIT | fresh-eyes | 1 | The name spelled out in prose is replaced there too, so the sentence explains a path instead of a name | fixed | `4b79a42`: prose says "the name in braces" |
| P12 | NIT | fresh-eyes | 1 | The README warns of doubled skills only in a site; a home install beside the plugin doubles them too | fixed | `4b79a42`: "Use one route" |
| P13 | NIT | fresh-eyes | 1 | The test takes the first lookup block it finds; a second one would be run instead, unnoticed | fixed | `4b79a42`: each marker must be there exactly once |
| P14 | NIT | fresh-eyes | 1 | `docs/CODEX-TEST.md` and `docs/ANTIGRAVITY-TEST.md` repeat the old lookup as "the exact logic the scaffold runs" | fixed — externally_reverified (round 2, both seats) | `4b79a42`: both carry the new lines, and a test holds them to SKILL.md's |
| P15 | BUG | codex | 2 | P1's fix stops short: a site's copy of `website-permissions` on a computer with the suite only as a plugin, and no `SKILLS_ROOT`, still finds nothing | fixed, then replaced: the lookup is gone (P24) | the lines now also look in the plugin's folder under Claude Code's configuration folder, `CLAUDE_CONFIG_DIR` honoured. Tested from a site folder named `Sam's Bakery`, strict and not, and with a moved configuration folder. Round 1's version said to set `SKILLS_ROOT` by hand there. Codex again proposed keeping the two templates in this skill; not done, for the reason under P1. caused-by: P1 (partial) |
| P16 | BUG | codex | 2 | P2's single quotes break on a folder with an apostrophe in its name: filled in, the string ends early and the shell cannot read the line | fixed — externally_reverified (round 3, both seats, for `new-website`); for `website-permissions` see P24 | double quotes again, and before them the line `: "${CLAUDE_SKILL_DIR:=}"`, which Claude Code leaves as written (seen in the live session, P3): unfilled, the name is then an empty value, not an unset variable, and the lookup passes over the candidate `/..`. Invariant: the lines run whatever is filled in, and unfilled change nothing. Variants tested: a folder `owner's suite` (space and apostrophe), strict and not; unfilled, strict and not, with an `.agents` install and with none. Not covered: a folder name with a double quote, dollar sign, backtick or backslash (the plan's known limits). caused-by: P2 (introduced) |
| P17 | RISK | codex, melious | 2 | That Claude Code installs from a branch named in the entry, and updates by the version, is not shown | fixed for a git source by URL — observed; `github` as the source type not tried | a throwaway repository and configuration folder, 2026-10-13, Claude Code 2.1.287: installed from `stable` without main's later file; `claude plugin update`: "already at the latest version (0.32.0)" with main moved, the same with 0.33 tagged and `stable` not moved, then "updated from 0.32.0 to 0.33.0" once `stable` was moved. The record is in the plan |
| P18 | RISK | codex | 2 | The `release-tag` workflow has never run: its two triggers and the tag lookup on a branch push are not shown | open on a prerequisite: the first release with this file on main | it cannot run before it is merged, and the owner chose to merge with release 0.32, whose tag push and `stable` push are its first runs. If it does not trigger, `stable` does not move and plugin users stay on the release before; the README's release steps give the command to move it by hand. The steps' shell is tested (P19); that GitHub starts the workflow and lets it push is what the first release shows |
| P19 | RISK | melious | 2 | A release that pushes its tag and never moves `stable` is green everywhere, and plugin users stay behind | fixed — externally_reverified (round 3, both seats, at the scope of the shell steps) | asked how to close it, the owner chose "The workflow moves it (Recommended)" on 2026-10-13. On a release tag the `release-tag` workflow checks the number and then pushes `stable` itself, if the tag is on main, without force; the job has `contents: write` for that push. Tests run the workflow's two shell steps, taken from the file, against a throwaway repository: first release creates the branch, the next moves it, a tag off main and an older release pushed again leave it where it is |
| P20 | NIT | melious | 2 | The home-folder guard cannot fire on a path behind the closing brace of a default, the shape round 1's fallback had | fixed — externally_reverified (round 3) | the pattern takes `skills}/…` too; a mutation with that shape is caught. The fallback itself no longer has it |
| P21 | NIT | melious | 2 | A tag such as `v0.33-rc1` triggers the workflow and fails it though nothing is wrong | fixed — externally_reverified (round 3) | only a tag of the form `v0.32` is compared; any other ends the step with a notice. Tried on six names |
| P22 | NIT | melious | 2 | The assertion's message is wrong when the name is missing from the lookup altogether | fixed — externally_reverified (round 3) | "must stand in the lookup exactly once" |
| P23 | BUG | codex | 3 | The README's way out of a red run moves `stable` to the tagged commit, which still carries the old number after it was put right in a later commit | fixed — externally_reverified (round 4, both seats) | the release steps take the tag's name from `plugin.json`'s number, so a number that was not raised names a tag that exists and git refuses it; a test runs that line. The way out is told apart: a failed move, push `stable` by hand; a failed check of the number, leave `stable`, plugin users get the next release |
| P24 | BUG | codex | 3 | `website-permissions`: with the name unfilled the first place looked in is `/new-website/templates/claude`, which wins if it exists, against "it names no folder" | fixed — externally_reverified (round 4, both seats) | the lookup is gone: asked how to end the chain, the owner chose "Keep copies in the skill (Recommended)" on 2026-10-13. The skill carries the two files and copies from its own folder; the sentence is the same instruction `facts-check` has. Tested from a copy of the skill in a folder `Sam's Bakery`, strict and not. caused-by: P16 (introduced) |
| P25 | RISK | codex, melious | 3 | The plugin-folder fallback takes the first cached version by name, the oldest, so an update can copy stale files into a site | fixed — externally_reverified (round 4, both seats) | no fallback any more (P24). caused-by: P15 (introduced) |
| P26 | RISK | codex, melious | 3 | The branch experiment used `"source": "url"`; the entry ships `"source": "github"` | fixed for the install — observed; the update question became P29 | 2026-10-13, Claude Code 2.1.287, a marketplace folder whose entry is `{"source": "github", "repo": "karero/croftweaver", "ref": "feat/claude-plugin"}`, a throwaway configuration folder: installed, version 0.32.0, 35 skills, with `scripts/plugin.test.mjs` and the workflow, which main does not have. The update by version was seen with the `url` type (P17) |
| P27 | NIT | melious | 3 | On a run for `stable` any tag starting with `v` counted, so a trial tag beside the release's made the run red | fixed — externally_reverified (round 4, both seats) | one filter for both paths; tested with a trial tag beside a release's, a trial tag alone, and two releases' tags |
| P28 | NIT | melious | 3 | The fallback list lacked Codex's and Antigravity's folders | fixed — externally_reverified (round 4, both seats) | no fallback any more (P24) |
| P29 | RISK | codex, melious | 4 | An update through the shipped `"source": "github"` was never observed | fixed — locally_verified, read by the closing pass only | the entry no longer uses that type. It is `"source": "url"` with the repo's https address, the type whose update by version was observed (P17); an install from GitHub through it, with this pull request's branch as the `ref`, gave version 0.32.0 and 35 skills on 2026-10-13. Reading Claude Code's documentation for this showed why it matters: `github` is fetched over SSH where possible, and an update does not fall back to https. An update from GitHub itself needs two releases and is in the plan's known limits |
| P30 | RISK | melious | 4 | The run on `stable` rests on the checkout having fetched tags, which `fetch-depth: 0` alone is only assumed to do | fixed — read by the closing pass only | `fetch-tags: true` on the checkout step. The first run remains P18's |
| P31 | NIT | melious | 4 | `website-permissions`' commands lost the line that keeps a strict shell from stopping on the unfilled name, and no test ran them unfilled | fixed — locally_verified, read by the closing pass only | the line is back as the block's first; a test runs the block unfilled, strict and not: it fails for want of the files, not on an unset name, and writes nothing |

UNVERIFIABLE entries, round 1: 12 asked across the three seats; one became a finding in all three (P3), one was looked at and settled: all 13 tests run on Node 24 in CI's `plugin-tests` job. The rest (update behaviour between two releases, the GitHub source at a tag, the single-command install) cannot be observed before a release exists and are in the plan's known limits.

UNVERIFIABLE entries, round 2: 7 asked; two were looked at: `skills/new-website/templates/astro/.nvmrc` exists and holds 24, and `fetch-depth: 0` is what the checkout action documents for all history and tags, which the first run on `stable` will show (P18).

Fix chain: P1 → P15 → P24, P25, P28, three links on how `website-permissions` finds its two files (P2 → P16 fed into it). The owner was told once, with three ways out, and chose the copies in the skill; the lookup is gone.

UNVERIFIABLE entries, round 3: 7 asked, one confirmed and filed (the `github` source type, P26). The rest wait for the first release (P3, P18) or are the owner's to do after the merge (P7, P10).

UNVERIFIABLE entries, round 4: 8 asked. Two were looked at and settled: the tester guides hold nothing of the removed lookup (`grep` for `for root in` and `CLAUDE_CONFIG_DIR` finds none), and git refuses a tag that exists (now a line in the tests). One became P30. The rest wait for the first release.

Notes:
- Round 4 is past the three the budget gives: round 3 found two BUGs in what someone runs or follows (P23, P24), which earn it.
- Round 4 found no BUG, so the rounds end there. Its two RISKs and one NIT went to the owner as one decision on 2026-10-13: "Fix all three, closing pass (Recommended)". The fixes are checked by the author and read once by codex in the closing pass, not by both seats.

## Test records

Run on the tree that became `a713a36`, before it was committed; the commit that adds this file takes this file and nothing else.

`make test-plugin`, the whole output:

```
✔ the plugin and the marketplace entry name the same plugin and the same release (2.693ms)
✔ no file of a skill sends the reader to the home skills folder for a skill's files (89.64525ms)
✔ the name Claude Code fills in stands only where it is filled in, and every path built on it exists (32.909417ms)
✔ new-website finds the suite where it was loaded from: a plugin's folder, which is none of the home folders (30.942084ms)
✔ the copy that is running wins over another install of the suite on the same computer (29.090125ms)
✔ an assistant that fills nothing in still finds its own install, and the unfilled name does no harm (22.588541ms)
✔ an explicit SKILLS_ROOT is honoured, and with nothing installed the default is unchanged (33.589125ms)
ℹ tests 7
ℹ suites 0
ℹ pass 7
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 532.3425
exit status: 0
```

`make check`: 1126 lines of output, last line `exit status: 0`. The lines that start with `OK` or `all`, or hold `passed`, and the exit status (a selection by that rule; the same checks run as CI jobs on the pull request):

```
OK — no private names in: skills README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile docs scripts; no contact info or credentials in: skills README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile docs LICENSE
OK — all 11 subjects behave identically with and without an exported CDPATH.
OK — whats-new.sh resolves a relative <project_dir> to the real one, not a CDPATH decoy.
OK — no early-exit pipe under pipefail in 20 scripts (2 exempt, each with a reason in scripts/check_pipefail_pipes.sh).
OK — independent-review stays model-agnostic (no concrete model names/tags in its 23 pipeline files)
OK — all 53 files under skills/new-website/templates/astro are accounted for (TEMPLATE_TRACKED, SITE_OWNED, or SITE_SOURCE).
OK (with warnings) — no skill over a hard budget; see the warn lines above (35 skills checked).
ok   suggest: a path already passed after -- is not suggested again
ok   thinkfailhelp: the flag is not passed
ok   thinklongword: the flag is not passed
all checks passed
all checks passed
all checks passed
test_whats_new_removed_skill: all cases passed
all checks passed
all checks passed
all checks passed
test_clean_denylist: all passed
test_git_stand_hook: all passed
all whats-new missing-file tests passed
all checks passed
exit status: 0
```

Checked by hand, not by a test:

- `claude plugin validate --strict .` (Claude Code 2.1.287): "✔ Validation passed".
- A copy of the tree, its marketplace entry's source changed to `./` because the tag `v0.32` does not exist yet, added as a local marketplace and installed with `CLAUDE_CONFIG_DIR` set to an empty scratch folder: "Successfully installed plugin: croftweaver@croftweaver (scope: user)"; `claude plugin list --json` gives version 0.32.0 and an install path ending `plugins/cache/croftweaver/croftweaver/0.32.0`; 35 folders under its `skills/`; every skill in the scaffold's copy list has its `SKILL.md` there, and `new-website/templates/.gitignore`, `SETUP.md`, `claude/settings.json`, `claude/hooks/git-stand.mjs` and `facts-check/scripts/facts_check.py` are present. The user's real configuration was not touched.
- Eight things were broken once each (the lookup's first candidate removed; its result not made absolute; a home-folder path put back; a command pointed at a missing file; the name used in a reference file; version and tag made to differ; the entry's ref set to `main`; entry and plugin named differently): `node --test scripts/plugin.test.mjs` failed every time.
- Not run: any signed-in Claude Code session that loads the plugin. `claude -p` from the building session answered "Failed to authenticate: OAuth session expired and could not be refreshed".
