# DIFF review — fix/site-copy-without-brand-kit-tests — the brand kit's scripts/tests stays out of sites

Base `661ec0e` · depth: Normal (a copy step in an instruction file, and a script a person runs) · verdict: CLEAN, with one owner decision (F13); the two follow-ups F18–F19 fixed in the pre-0.32 sweep, Light review

Files in the change: `skills/new-website/SKILL.md`, `scripts/whats-new.sh`, `scripts/test_whats_new_removed_skill.sh`, `README.md`, and this trail.

The rule, decided by the maintainer after the brand-kit merge (karero/croftweaver#283): only `website-brand-kit/scripts/tests` stays behind. Tests in general still travel, because wordpress-inspector's SKILL.md runs its own (`python3 -m unittest discover -s "${CLAUDE_SKILL_DIR}/scripts/tests"`).

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `f15ef7b` | full diff, brief, `process_dir()` excerpt, test record (22,653 bytes) | Codex (gpt-6.1-sol, config effort, read-only); melious (glm-5.3, HTTP API, text only) | codex 259 s, 62,709; melious 249 s, 21,919 | 0 / 2 / 3 (Codex clean) |
| 2 | `14f28a1` | delta since `f15ef7b`, caller excerpt, test record; round 1 as `--verify` | same, Codex at medium | codex 209 s, 63,439; melious 288 s, 21,862 | 0 / 2 / 2 |
| 3 | `1040a8a` | delta since `14f28a1`, test record; rounds 1–2 as `--verify` | same | codex 181 s, 41,621; melious 435 s, 25,063 | 1 / 1 / 1 (Codex's RISK folded into F11) |
| 4 | `fe6a904` | delta since `1040a8a`, pattern check, test record; rounds 1–3 as `--verify` | same | codex 131 s, 46,241; melious 519 s, 32,203 | 2 / 0 / 3 |
| 5 | `91fae8a` | delta since `fe6a904`, pattern and name checks, test record; rounds 1–4 as `--verify` | same | codex 165 s, 47,948; melious 287 s, 17,944 | 0 / 0 / 0 (two outside-scope NITs, F18–F19) |

Five rounds, 17 findings (3 BUG, 5 RISK, 9 NIT), plus two follow-ups. The copy change itself did not move after round 1; rounds 2–5 hardened the test's guard against brand-kit code needing the folder, a guard added in answer to F1.

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | RISK | melious | 1 | the guard read only `*.md`; a script needing `scripts/tests` would pass and break in sites | fixed (round 1: import each module; replaced in rounds 2–4, see F6–F14) | case 10's code check |
| F2 | RISK | melious | 1 | a git without `:(exclude)` support: `process_dir` runs under `process_dir \|\| FAIL=1`, which switches `set -e` off, so a failed change list read "Up to date" | fixed, externally_reverified (rounds 2, 5) | `changed=…` now ends `\|\| { echo "error: git could not list …"; return 1; }`; a `git` wrapper refusing the exclude makes the report fail; on round 0's script the same case printed "Up to date" |
| F3 | NIT | melious | 1 | broaden the md pattern (`tests/`, `tox`, `make test`) | refuted, reverified (round 2) | `tests/` hits a maintainer note in `templates/palette-prompt.md`; `tox` and `make test` appear in no skill |
| F4 | NIT | melious | 1 | rename detection could hide a move into `scripts/tests` | refuted, reverified by Codex (round 2) | on git 2.33, after `git mv …/scripts/x.py …/scripts/tests/x.py` the excluded diff still lists `…/scripts/x.py` and the log lists the commit |
| F5 | NIT | melious | 1 | README note spliced mid-paragraph | fixed, reverified (round 2) | own paragraph after "Plain `make whats-new` …" |
| F6 | RISK | Codex | 2 | importing modules misses an import inside a function | fixed with F7 | — |
| F7 | RISK | melious | 2 | importing runs top-level code, so a missing third-party package would fail the check | fixed, reverified (round 3) | the check reads files and runs nothing |
| F8 | NIT | melious | 2 | non-Python files (render.mjs) unchecked | fixed, reverified (round 3) | the grep reads every file of the copy |
| F9 | NIT | melious | 2 | a missing folder passed vacuously | fixed, reverified (round 3) | grep must exit 1; 2 fails |
| F10 | BUG | Codex | 3 | `import os, _testutil` passed; the "complete" claim was wrong | fixed, reverified (round 4) | import arm matches any line starting `import`/`from` that names a test module before a `#` |
| F11 | RISK | melious, Codex | 3 | path forms missed: `'./tests'`, `Path("tests")`, `folder = 'tests'`, relative imports, `require` | fixed, reverified (round 4) | a `tests` segment after a quote, slash or dot; a `require(` arm |
| F12 | NIT | melious | 3 | module names spliced raw into the ERE | fixed, reverified (rounds 4–5) | a `case` rejects any character but letters, digits, `_` and the separator (written backslash-pipe in the bracket), and fails a check; under bash 3.2 it rejects `a.b`, `a+b` and a backslash |
| F13 | BUG | Codex | 4 | still misses an import continued on the next line, and a `["tests"]` list joined later | owner decision: keep a tripwire, say so plainly; reverified (round 5) | the comment calls it a tripwire, lists what it catches, names both misses. Codex verified in round 1 that no brand-kit code needs `scripts/tests` today |
| F14 | BUG | melious | 4 | the round-3 rewrite dropped the plain `scripts/tests` match (`unittest discover -s scripts/tests` passed) | fixed, reverified (round 5) | `scripts/tests` is its own alternative again |
| F15 | NIT | melious | 4 | the backslash before the pipe in that bracket would admit a backslash | refuted, reverified by Codex (round 5) | under bash it rejects a backslash; the suggested bare pipe splits the case pattern in two, and then nothing is rejected, not even `a.b` |
| F16 | NIT | melious | 4 | `["tests"]` as an assigned value passes | covered by F13 | named in the comment |
| F17 | NIT | melious | 4 | `require('./x'); // tests` is a false alarm | accepted | fails closed; costs a rewording |

Waivers and deferrals: F13, by the maintainer's choice in chat after round 4 (tripwire, not a parser).

Follow-ups (round 5, outside its delta). Logged as BUGLOG rows, then fixed in this PR on the maintainer's word (the pre-0.32 sweep), with a Light review (Codex, medium) of the rows and of the fix:

- F18 NIT — the `*.md` instruction check (`runs="$(grep -rlE … 2>/dev/null)"`) discards grep's exit status, so an unreadable folder would pass it; the arrival checks catch a missing one, and the code check below fails on it too. FIXED: both greps go through `finds_none`, true only on grep's exit 1; a missing folder stands in for an unreadable one in the test (both make BSD grep exit 2, measured with a `chmod 000` folder).
- F19 NIT — the module names come from top-level `*.py` in `scripts/tests` only; a module in its `fixtures/` folder would not be named (the path arms still catch written-out paths). FIXED: `test_modules` reads every `*.py` under the folder; a test names a module in a subfolder.

## Test records (author's machine)

- `bash scripts/test_whats_new_removed_skill.sh` at `91fae8a`: all cases passed, exit 0.
- `make check` at `91fae8a`: exit 0, "all checks passed". Skipped on this Mac: Perl::MinimumVersion not installed, and the six `/proc` cases; CI runs both.
- Each new check was broken on purpose and failed: on `origin/main`'s `whats-new.sh` and SKILL.md (round 0); with a `unittest discover` line added to the brand kit's SKILL.md; with `from tests import _testutil` in a function, a bare `import _testutil`, `os.path.join(HERE, "tests", "x")`, `new URL('tests/x.json', …)` in render.mjs, and SKILL.md deleting the whole brand kit (round 2, through the full script). From round 3 the session's safety check refused to run copies of the test script, so later forms were checked by running the committed `mods`, `W` and `PAT` lines on 18 sample lines under bash 3.2 and `/usr/bin/grep` (BSD 2.6.0): 17 as intended, the 18th is F17. GNU grep was not run locally; CI runs the test on Linux.
