# DIFF review — PR #276 — Croftweaver as a Claude Code plugin; skills name their files relative to their own folder
Base `714516a` · depth: Normal (instruction files eleven skills load, and the lines the orchestrator runs to find the suite; no user data, no deploy path) · verdict: OPEN · authority used: POST AUTHORITY — atom A (this session opened #276); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch)

Seats: Codex and GLM 5.3 on melious (`SECOND_SEAT=melious`), and in round 1 a fresh-eyes pass on a mid-tier model of the host's family. The owner's words, in this session on 2026-10-12: "push it and open the PR, then run the review"; both services were cleared for this repo the same day for #268 ("yes to all three").

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|

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
