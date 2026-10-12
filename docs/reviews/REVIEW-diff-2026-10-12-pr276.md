# DIFF review — PR #276 — Croftweaver as a Claude Code plugin; skills name their files relative to their own folder
Base `714516a` · depth: Normal (instruction files eleven skills load, and the lines the orchestrator runs to find the suite; no user data, no deploy path) · verdict: OPEN · authority used: POST AUTHORITY — atom A (this session opened #276); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch)

Seats: Codex and GLM 5.3 on melious (`SECOND_SEAT=melious`), and in round 1 a fresh-eyes pass on a mid-tier model of the host's family. The owner's words, in this session on 2026-10-12: "push it and open the PR, then run the review"; both services were cleared for this repo the same day for #268 ("yes to all three").

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `7e7dcb2` | full: `714516a...7e7dcb2` without `docs/reviews/`, plus the plan `docs/reviews/SKILL-PLAN-capability-gaps.md`; in front of it, marked as context, the scaffold steps of `new-website` that use the lookup, the documentation passages relied on, what was observed with the CLI, and the test record | codex-cli 0.162.1, gpt-6.1-sol, config effort, read-only · melious HTTP API, glm-5.3, text only · fresh-eyes: a sub-agent on the host family's mid-tier model, read-only by instruction | codex 288 s / 90,530 · melious 188 s / 33,827 · fresh-eyes 193 s / 142,821 | codex 2/3/0 · melious 0/2/4 · fresh-eyes 0/5/5 · after dedup 2/5/7 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| P1 | BUG | codex, fresh-eyes (as RISK) | 1 | `website-permissions`: the reworded commands look for `new-website` beside the skill, which the copy inside a site lacks, and that copy is the one the step serves | fixed — locally_verified | `4b79a42`: the lines look beside the skill, then in the installed suite (`SKILLS_ROOT`, or `~/.claude/skills`). Tests run them: from a plugin's folder with a space in its path; from a site's copy with a home install; unfilled with `SKILLS_ROOT`, in a strict shell too; with no suite (fails, writes nothing). Codex proposed moving the two templates into this skill; not done, they would then exist twice |
| P2 | BUG | codex, fresh-eyes (as RISK), melious (as NIT) | 1 | `new-website`: left unfilled, the first candidate was read as a variable: a shell with unset variables as errors stops (`CLAUDE_SKILL_DIR: unbound variable`), and any other turns it into `/..`, so a folder `/new-website` would pass for the suite | fixed — locally_verified | `4b79a42`: the candidate is in single quotes; unfilled it is a folder name that does not exist. Invariant: an unfilled name changes nothing for an assistant that fills nothing in. Tested with `bash -u` for an `.agents` install and for nothing installed; a test holds the quoting; putting double quotes back fails two tests |
| P3 | RISK | codex, melious, fresh-eyes | 1 | That Claude Code replaces the name by the skill's folder, in a fenced block and for a plugin's skill, is its documentation's word; no session observed it | open on a prerequisite: a signed-in session | the building session cannot start one (`claude -p`: "OAuth session expired and could not be refreshed") and does not pick up a skill added while it runs. If false, the scaffold falls back to `~/.claude/skills` and its first `cp` fails, loudly |
| P4 | RISK | codex, melious | 1 | A release that leaves both values at the last release passes `make test-plugin`, and plugin users stay behind | fixed — locally_verified | `4b79a42`: `.github/workflows/release-tag.yml` runs the tests on a pushed `v*` tag with the tag to compare; `RELEASE_TAG=v0.33` fails locally, `v0.32` passes. It reports after the tag exists and stops nothing |
| P5 | RISK | fresh-eyes | 1 | From the merge of a release's pull request until its tag is pushed, main names a tag that does not exist, and installing or updating fails, for users on the release before too | open — the owner's decision | `4b79a42` says so in the README and asks for the tag in the same sitting. The other way is an entry that names a branch the release moves |
| P6 | RISK | codex | 1 | `scripts/check_clean.sh` does not read `.claude-plugin/` | open — the owner's decision | a row in `docs/BUGLOG.md`, beside the one for `packages/`, whose fix is under way in another pull request |
| P7 | RISK | fresh-eyes | 1 | `plugin-tests` is not a required check | open — the owner's decision | the ruleset is the owner's |
| P8 | NIT | melious, fresh-eyes | 1 | The home-folder guard missed `${HOME}`, names not starting with a letter, and files without one of ten extensions | fixed — locally_verified | `4b79a42`: every tracked text file under `skills/`, `$HOME` with or without braces, anything after the folder; a mutation in `templates/.gitignore` with `${HOME}` is caught |
| P9 | NIT | melious | 1 | The test needs a newer Node than "needs node" says (`Dirent.parentPath`) | fixed | `4b79a42`: files come from `git ls-files`; the Makefile and the header say node 20 or newer, git and bash |
| P10 | NIT | melious, fresh-eyes | 1 | Once merged, the README shows install commands that fail until the tag `v0.32` exists | open — the owner's decision | when to merge is the owner's |
| P11 | NIT | fresh-eyes | 1 | The name spelled out in prose is replaced there too, so the sentence explains a path instead of a name | fixed | `4b79a42`: prose says "the name in braces" |
| P12 | NIT | fresh-eyes | 1 | The README warns of doubled skills only in a site; a home install beside the plugin doubles them too | fixed | `4b79a42`: "Use one route" |
| P13 | NIT | fresh-eyes | 1 | The test takes the first lookup block it finds; a second one would be run instead, unnoticed | fixed | `4b79a42`: each marker must be there exactly once |
| P14 | NIT | fresh-eyes | 1 | `docs/CODEX-TEST.md` and `docs/ANTIGRAVITY-TEST.md` repeat the old lookup as "the exact logic the scaffold runs" | fixed — locally_verified | `4b79a42`: both carry the new lines, and a test holds them to SKILL.md's |

UNVERIFIABLE entries, round 1: 12 asked across the three seats; one became a finding in all three (P3), one was looked at and settled: all 13 tests run on Node 24 in CI's `plugin-tests` job. The rest (update behaviour between two releases, the GitHub source at a tag, the single-command install) cannot be observed before a release exists and are in the plan's known limits.

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
