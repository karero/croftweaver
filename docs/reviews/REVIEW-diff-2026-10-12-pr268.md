# DIFF review — PR #268 — `npm create croftweaver`, a one-line install of the skills
Base `e58d3ae` · depth: Normal (an install script: it deletes and moves folders in the place an assistant takes its instructions from, and unpacks a download) · verdict: OPEN · authority used: POST AUTHORITY — atom A (this session opened #268); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch)

Seats: Codex and GLM 5.3 on melious (`SECOND_SEAT=melious`), and in round 1 a fresh-eyes pass on a mid-tier model of the host's family. The owner's OK for both services, given in this session on 2026-10-12 to the question "shall I run the review pair (Codex and GLM 5.3 on melious, Normal depth), then push and open the PR?": "yes to all three, npm half is right".

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|

## Before round 1

Found by the author's own checks and by CI, before any reviewer ran; both are in the reviewed diff:

- A failed first run left an empty skills folder behind, against the README's "changes nothing" (found by the claims sweep; `9b51b4d`).
- That fix removed one folder too many on Windows, where `fs.mkdirSync`'s return value is spelled differently from the destination; the new test failed on the Windows runner (run 38275840632, job 114900979567) and `75b3e19` fixed it. The same run's macOS and Node 22.12.0 legs were cancelled by fail-fast, not failed; `75b3e19` turns fail-fast off.

## Test records

Run at `75b3e198824c67cb26125b73a2a0998b49f99ab8`, the head before the commit that adds this file. That commit takes this file and nothing else.

`make test-create`, the whole output:

```
✔ a first run installs every skill of the latest release, and nothing else from the zip (128.784417ms)
✔ a second run makes the folder match the new release: changed, added and dropped skills (239.600667ms)
✔ a folder someone else put under a skill's name is moved beside the skills folder, not lost and not left to load twice (127.317208ms)
✔ skills linked from a toolkit folder are left alone, and --force swaps the link for a copy without touching that folder (247.581625ms)
✔ a link whose folder is gone is replaced: keeping it would keep a skill that cannot load (127.506625ms)
✔ each assistant gets its own folder, and the two overrides of the shell installers hold here too (498.60125ms)
▶ a download that cannot be used changes nothing in an install that works
  ✔ the server has no such file (158.516583ms)
  ✔ the zip is cut short (131.513584ms)
  ✔ the zip points past its own end (132.105833ms)
  ✔ a file fails its checksum (125.881292ms)
  ✔ a path climbs out of the skills folder (138.211625ms)
  ✔ a path climbs out the Windows way (127.882375ms)
  ✔ a skill name is not a plain name (128.014875ms)
  ✔ the zip holds a link (124.402ms)
  ✔ the zip is not a Croftweaver release (123.879459ms)
  ✔ on a computer without the skills, a failed run leaves no empty folder behind (273.635667ms)
  ✔ nothing answers at the address (104.382375ms)
✔ a download that cannot be used changes nothing in an install that works (1696.7495ms)
✔ an argument it does not know stops it before anything is downloaded or written (230.953625ms)
✔ the real skills, zipped the way a release is, arrive file for file with their executable bits (474.242333ms)
ℹ tests 20
ℹ suites 0
ℹ pass 20
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 3988.047208
exit status: 0
```

`make check`: 1084 lines of output, last line `exit status: 0`. The lines that start with `OK` or `all`, or hold `passed`, and the exit status (a selection by that rule; the same checks run as CI jobs on the pull request):

```
OK — no private names in: skills README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile docs scripts; no contact info or credentials in: skills README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile docs LICENSE
OK — all 11 subjects behave identically with and without an exported CDPATH.
OK — whats-new.sh resolves a relative <project_dir> to the real one, not a CDPATH decoy.
OK — no early-exit pipe under pipefail in 20 scripts (2 exempt, each with a reason in scripts/check_pipefail_pipes.sh).
OK — independent-review stays model-agnostic (no concrete model names/tags in its 23 pipeline files)
OK — all 53 files under skills/new-website/templates/astro are accounted for (TEMPLATE_TRACKED, SITE_OWNED, or SITE_SOURCE).
OK (with warnings) — no skill over a hard budget; see the warn lines above (34 skills checked).
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

CI on `75b3e19` (run 38277105136): `create-croftweaver-tests` passed on ubuntu-latest, macos-latest, windows-latest and on ubuntu-latest with Node 22.12.0. The Windows leg skips, by name, the one test that needs the `zip` tool.

Checked by hand, not by a test:

- Each of 17 guards in `index.mjs` was removed once; `node --test` failed every time. The list is in the pull request's comment.
- `npm pack`, then `npm exec --package=<the tarball> -- create-croftweaver` against the stub, serving the real skills: exit 0, 34 skill folders. The tarball holds `README.md`, `index.mjs`, `package.json`.
- One real run against the v0.31 release on GitHub, `HOME` set to an empty scratch folder: exit 0, 34 skill folders; `diff -rq` against `git archive v0.31 skills` reports only `.croftweaver.json` as extra; 15 executable files on both sides. Run at `963c3be`, not repeated since: the two commits after it list the missing folders before `mkdirSync` and try to remove them, if empty, at the end of every run.
- Not tested: the refusal on a Node older than 22.12.
