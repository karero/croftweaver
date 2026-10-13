# DIFF review — `fix/check-clean-scans-packages` — check_clean: scan packages/ where it exists
Base `8696da0` · depth: Normal (the logic of a guard script changes, so not Light; nothing in the High row) · verdict: PENDING (round 1 not run yet) · authority used: WORKTREE-WRITE and BRANCH-COMMIT, atom A (this session made the worktree and the branch). No PR yet, so POST AUTHORITY does not apply yet.

Data consent: the owner named the seats for this change in his task message of 2026-10-12, quoted: "Normal depth with the `independent-review` skill: Codex plus GLM 5.3 on melious". Fresh-eyes runs in round 1 only, on a mid-tier model of the host's family.

## What the change is

Three files: `scripts/check_clean.sh`, `scripts/test_clean_denylist.sh`, `README.md`.

- `packages/` is scanned when it exists: by the name check, by the generic checks (home paths, e-mail addresses, credentials, secret-looking assignments) and by the `find` that refuses odd file names. It is not a required target, because the handoff zip, where `make check` also runs, does not hold it.
- `packages/create-croftweaver/LICENSE` is a byte-for-byte copy of the root `LICENSE`, which the name check leaves out. The copy's lines are dropped from the name hits by exact path, unless a file named like it plus a colon is present.
- Eight new cases in `scripts/test_clean_denylist.sh`.
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

## Rounds

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|

## Findings

None yet.
