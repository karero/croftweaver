# DIFF review — PR #277 (`fix/check-clean-scans-packages`) — check_clean: scan packages/ where it exists
Base `8696da0` · depth: Normal (the logic of a guard script changes, so not Light; nothing in the High row) · verdict: no BUG in 2 rounds, 7 findings; one RISK (F2) waits on the owner, so NOT CLEAN yet · authority used: WORKTREE-WRITE and BRANCH-COMMIT, atom A (this session made the worktree and the branch). POST AUTHORITY, atom A (this session opened #277 on 2026-10-13).

Data consent: the owner named the seats for this change in his task message of 2026-10-12, quoted: "Normal depth with the `independent-review` skill: Codex plus GLM 5.3 on melious". Fresh-eyes runs in round 1 only, on a mid-tier model of the host's family.

## What the change is

Three files: `scripts/check_clean.sh`, `scripts/test_clean_denylist.sh`, `README.md`.

- `packages/` is scanned when it exists: by the name check, by the generic checks (home paths, e-mail addresses, credentials, secret-looking assignments) and by the `find` that refuses odd file names. It is not a required target, because the handoff zip, where `make check` also runs, does not hold it.
- `packages/create-croftweaver/LICENSE` is a byte-for-byte copy of the root `LICENSE`, which the name check leaves out. The copy's lines are dropped from the name hits by exact path, unless a file named like it plus a colon is present. Since round 1 (F1), also only while `cmp` finds the copy identical to the root file.
- New cases in `scripts/test_clean_denylist.sh`: eight at round 1, ten after it.
- The README's paragraph on what the check covers says the same.

Not in the reviewed diff: the status cell of the `docs/BUGLOG.md` row of 2026-10-12 (Where: `scripts/check_clean.sh`, `SCAN_BASE`). It takes the fixing PR's number, which does not exist before the PR is opened. It is set after the last round.

## Run records, before round 1

Each run was saved whole to a file: the command, everything it printed, its exit status. Head `04b9120`, macOS, bash 3.2, BSD grep. The files are not committed; the reviewers got them with the diff.

| Run | Where | Exit | Result |
|---|---|---|---|
| `/bin/bash scripts/test_clean_denylist.sh` | checkout | 0 | 85 `ok` lines, no `FAIL`, no `SKIP`; "test_clean_denylist: all passed". 77 cases before this change, 8 new |
| `bash scripts/check_clean.sh` | checkout | 0 | `OK — no private names in: skills README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile docs scripts packages; no contact info or credentials in: skills README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile docs LICENSE packages` |
| `CLEAN_MASK_NAMES=1 bash scripts/check_clean.sh` | checkout | 0 | the same line |
| `make check` | checkout | 0 | 1,137 lines; 1,102 `ok` lines, no `FAIL`; "all checks passed". One skip: the minimum-Perl check (`Perl::MinimumVersion` is not installed here; CI runs it) |
| `bash scripts/package.sh` | checkout | 0 | 345 files; "zip integrity OK" |
| `unzip -q dist/croftweaver.zip` into an empty folder outside any git checkout | | 0 | the copy has no `packages/` and no git |
| `bash scripts/check_clean.sh` | unzipped copy | 0 | `OK — no contact info or credentials in: skills README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile docs LICENSE (private-name check SKIPPED: no scripts/.clean-denylist)` |
| `make check` | unzipped copy | 0 | 1,133 lines; 1,095 `ok` lines, no `FAIL`; "all checks passed". Skips, each one the zip's own: two `whats-new.sh` cases and the LF check (no git clone), the CI step cases (no `.github/`), the minimum-Perl check |

## Each new line, broken in turn

The fixed script with one line taken out, then `/bin/bash scripts/test_clean_denylist.sh`. Every run exits 1.

| Taken out | Cases that fail |
|---|---|
| M0: the whole change (the script as on `8696da0`) | 6: the clean `packages/` OK line, the name, the email, the odd file name, the file beside the LICENSE copy, the colon name |
| M1: `packages` added to the name scan | 4: the OK line, the name, the file beside the copy, the colon name |
| M2: `packages` added to the generic scans | 2: the OK line, the email |
| M3: `packages` added to the `find` | 1: the odd file name |
| M4: the LICENSE copy's exemption | 2: "a listed name in the installer's copy of LICENSE: passes", and the copy is reported beside the file that holds a name |
| M5: the condition on a file named like the copy plus a colon | 1: the colon name |

The trap on the real tree: the fixed script without the exemption (M4), run masked on this checkout, exits 1 with "✗ personal/site identifier:" and one withheld line. With the exemption it passes (the records above).

## Run records, before round 2

The same runs on head `5b45e56`, saved the same way. All exit 0.

| Run | Result |
|---|---|
| `/bin/bash scripts/test_clean_denylist.sh` | 87 `ok` lines, no `FAIL`, no `SKIP` |
| `bash scripts/check_clean.sh`, plain and masked | the OK line as above, naming `packages` in both lists |
| `make check`, checkout | 1,139 lines; 1,104 `ok` lines, no `FAIL`; the one skip as above |
| `bash scripts/package.sh` | 345 files; "zip integrity OK" |
| `bash scripts/check_clean.sh`, unzipped copy | the OK line as above, names skipped, no `packages` |
| `make check`, unzipped copy | 1,135 lines; 1,097 `ok` lines, no `FAIL`; the skips as above |

Mutations on `5b45e56`, each exits 1: M1 (no name scan) fails 6 cases, the masked one among them; M4 (no exemption) fails 2; M5 (no colon condition) fails 1; M6 (the `cmp` taken out) fails 1, "a copy of LICENSE that differs from the root file: scanned, and fails".

## Rounds

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `04b9120` | full: `8696da0...04b9120`, 3 files, with the changed script whole and the run records | codex-cli 0.162.1, gpt-6.1-sol, config effort (high), read-only: OK · melious, glm-5.3, text only: OK · fresh-eyes, a sub-agent on the host family's mid-tier model, read-only, no shared context: OK | 317 s / 79,450 · 230 s / 38,084 · 261 s / 130,386 | 0/2/5 |
| 2 | `5b45e56` | delta: `04b9120..5b45e56`, 3 files, with the author's record of round 1 (`--verify`), excerpts and the new run records | codex-cli 0.162.1, gpt-6.1-sol, medium, read-only: OK · melious, glm-5.3, text only: OK | 166 s / 45,275 · 209 s / 29,947 | 0/1/0 (F2 again; nothing new) |

Round 2 had no BUG and no RISK that calls for a change to the code, so no third round is owed. `c617d43`, between the two heads, adds only this file.

## Findings

| Id | Severity | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | RISK | melious; fresh-eyes as NIT | 1 | The LICENSE copy was left out of the name check by its path alone: a copy that had drifted and gained a name passed `make check` | fixed in `5b45e56`, locally_verified, externally_reverified (both seats, round 2) | the copy's lines are dropped only while `cmp -s LICENSE packages/create-croftweaver/LICENSE` succeeds; the drift case fails without it (M6). One part refuted: "the installer test's wiring into CI is nowhere". It runs in `.github/workflows/clean.yml`, job `create-croftweaver-tests`, on three systems; Codex read the lines in both rounds |
| F2 | RISK | melious (1); Codex (2) | 1, 2 | Coverage hangs on the literal folder name `packages`: a renamed folder, or another new top-level one, is unscanned again | waived by the owner, 2026-10-13, with a bug-log row | not introduced here: the check has always scanned a fixed list (`SCAN_BASE`). The fix proposed in round 1 (require the folder when `git ls-files -- packages/` lists files) cannot see a rename. A check that every tracked top-level path is scanned or named as left out would be a new guard |
| F3 | NIT | melious | 1 | `[ -e packages ]` should be `[ -d packages ]` | refuted; both seats agreed in round 2 | in a throwaway tree, a plain file named `packages` that holds a listed name is reported as `packages:1:…` and the run exits 1; with `-d` it would not be read. A dangling symlink is skipped under either test |
| F4 | NIT | melious | 1 | README: "skips only `LICENSE`" forgets the list's own lines | refuted; both seats agreed in round 2 | the same paragraph says "unless the file is gitignored", and `.gitignore` names `scripts/.clean-denylist` |
| F5 | NIT | fresh-eyes | 1 | README: the new sentence sat on one long line | fixed in `5b45e56`, externally_reverified | wrapped |
| F6 | NIT | fresh-eyes | 1 | No masked-mode case with a hit in `packages/` | fixed in `5b45e56`, externally_reverified | "masked: a listed name in packages/ fails, and only a count is printed"; M1 fails it |
| F7 | NIT | fresh-eyes | 1 | The exemption names one path; a second package with its own copy would puzzle a reader | fixed in `5b45e56`, externally_reverified | the comment says another package with a copy of its own needs its path there |

Waiver: F2, the owner's sign-off in this session on 2026-10-13, quoted: "Waive F2 with the BUGLOG row, push and open the PR". The row is the one dated 2026-10-13 in `docs/BUGLOG.md` (Where: `scripts/check_clean.sh`, `SCAN_BASE` and `SCAN_PRESENT`).

Questions the seats could not settle (UNVERIFIABLE entries, not findings): round 1 asked 8, round 2 asked 6; none became a finding. Still open, and settled only by CI on the pushed branch: the new pattern under GNU grep, and CI's own name list against `packages/`. Codex did not re-run the full suites in either round (its sandbox is read-only and the suites write temp files); fresh-eyes re-ran the test, the masked check, M0 and M4 in round 1.
