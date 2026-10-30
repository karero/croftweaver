# Plan: make check fails when a script is left out of the handoff zip

Status: plan, 2026-10-30. Branch `guard/package-script-coverage`.

## What and why

`scripts/package.sh` names each root script by hand twice: in its `zip -r` line and in its
`REQUIRED` list. The guards name scripts too: `check_cdpath_safe.sh` (SUBJECTS / NOT_RUN must
cover every script `list_shell_scripts.sh` finds) and `test_mktemp_guard.sh` (SCRIPTS / EXEMPT).

On #445, `scripts/test_served_build.sh` went into the guards but not into `package.sh`.
`make check` passed in the checkout. Only CI's `macos-stock-tools` job failed, after the push:
inside the unzipped zip, the CDPATH guard named a script the zip did not hold. Nothing local
catches this.

It has already drifted the other way too: `build_directory_tree.sh` and `publish_directory.sh`
are in the `zip -r` line but not in `REQUIRED` (checked today: 29 scripts in the zip line,
27 in REQUIRED, those two the difference).

## The rule

Every shell script under `scripts/` that `list_shell_scripts.sh` finds is shipped: named in
the `zip -r` line AND in `REQUIRED`, and matched by none of that line's `-x` patterns.

The brief offered a second way out, a `NOT_SHIPPED` list with reasons. Round 1 showed it
cannot work on its own: a script left out of the zip must still sit in CDPATH's SUBJECTS or
NOT_RUN for `make check` in the checkout, and inside the zip that entry is then stale, which
is the #445 failure again. So there is no such list. Nothing under `scripts/` needs one today
(every script there ships). If one ever must stay out, the check fails with a message saying
the guards' lists need teaching first; that is a change of its own.
`list_shell_scripts.sh` is the set the guards are already held to (CDPATH's completeness
check demands exactly that set; the mktemp guard's set is a subset of it), so covering it
covers every script a guard can name. Scripts under `skills/` ship with the whole `skills`
folder and are out of scope.

## Two shapes, and the pick

**A. A new check, `scripts/check_package_scripts.sh`, run by `make check`.** It reads
`package.sh` as text (awk: tokens starting `scripts/` from the `zip -r` line to its
`>/dev/null`; lines starting `scripts/` inside `REQUIRED=( … )`) and compares both with
`list_shell_scripts.sh`. `package.sh` itself changes only by gaining the two missing
REQUIRED rows and the new scripts.

**B. `package.sh` works out the root scripts it ships** from `list_shell_scripts.sh` minus a
not-shipped list, for both the zip and REQUIRED.

**Pick A.** Reasons:
- B changes what goes into a public release. Today the list is explicit on purpose (its
  comment: so nothing unlisted, such as the gitignored `scripts/.clean-denylist`, can leak).
  B would ship any new tracked shell script under `scripts/` by default, and in a folder with
  no git (`list_shell_scripts.sh` falls back to `find`) any untracked one with a shebang.
- B puts nothing into `make check`. `package.sh` only runs in `make check` under
  `test_package_leak.sh`, with zip and unzip stubbed, so the drift would still first show at
  `make package` or in CI. The task is to fail before the push.
- A follows the repo's existing pattern (CDPATH's NOT_RUN, the template-coverage buckets): a
  new script forces a deliberate choice, and the error says which list to add it to.

Cost of A: the check parses another script's text. If `package.sh` is reformatted, the parse
could find nothing. The check refuses that loudly: fewer than 10 scripts from either the zip
line or REQUIRED is a FAIL ("could not read package.sh"), never a pass.

## How

1. **`scripts/check_package_scripts.sh`** (new, read-only, quick). Fails, naming each path,
   when a found script is not in the zip line, or not in REQUIRED; when the zip line or
   REQUIRED names a `scripts/` path the listing does not have (stale, as CDPATH's check
   does); and when any `-x` pattern on the zip line matches a listed script. Every token
   after `-x` (quotes stripped, quoted or not) is tested against each script with bash's `[[ $s == $p ]]`, where `*`
   crosses `/` as zip's does (so `'*/test_served_build.sh'` matches). None of today's
   patterns match a script. Prints the fix: "add it to package.sh's
   zip -r line and REQUIRED".
   Inside the unzipped zip it runs the same way: the listing falls back to `find`, which sees
   the shipped scripts, and `package.sh` is there.
2. **`scripts/test_check_package_scripts.sh`** (new), in the style of
   `test_template_coverage.sh`: copies `scripts/` shell scripts into a throwaway folder (not in
   a git repo, so the listing uses `find`), changes each copy one way, runs the real check from
   the copy, and judges exit status and the path it names. Cases:
   - as is → pass;
   - **#445**: a new `scripts/test_new.sh` added to the copy's `check_cdpath_safe.sh` NOT_RUN,
     not to `package.sh` → fail, names it;
   - in the zip line only → fail; in REQUIRED only → fail;
   - `-x '*/test_served_build.sh'` added to the zip line → fail, names it;
   - `-x scripts/test_served_build.sh` (unquoted) added → fail, names it;
   - `package.sh` names a script that no longer exists → fail, names it;
   - `package.sh` with its `zip -r` line renamed so nothing parses → fail, "could not read".
3. **Wiring**: both scripts into `package.sh` (zip line and REQUIRED), plus the two missing
   REQUIRED rows; the check into CDPATH's SUBJECTS, the test into NOT_RUN with its reason; the
   test into `test_mktemp_guard.sh`'s SCRIPTS (it calls mktemp); both into the Makefile `check`
   target and its help text; a sentence in `clean.yml`'s header (its pattern names every guard);
   two rows in README's scripts table.

## How it is tested

- The new test, through `make check` (the same entry production uses: the real check script,
  found from where it sits).
- Mutation by hand before review: remove the check's zip-line comparison, then its REQUIRED
  comparison, then its `-x` match, and see the matching cases go red.
- `make check` and `make smoke` in the worktree; then unzip `dist/croftweaver.zip` into a
  scratch folder and run `make check` there, as `clean.yml`'s `macos-stock-tools` job does.
- Replay #445: on a scratch copy, add a script to CDPATH's NOT_RUN only; `make check` fails.

## Known limits

- It checks `scripts/` only. A shell script added elsewhere outside `skills/` (none exist
  today) would not be checked.
- It checks the lists as text and the `-x` patterns by bash's glob match, not zip's effective
  selection (zip's own pattern rules differ in corners, such as `\` escapes). `package.sh`'s own REQUIRED
  check still catches a dropped file at build time, as before.
- It reads `package.sh` as text; a reformat that keeps ≥10 matches but drops one script from
  the parse would show as "not shipped" (a false FAIL, loud), not a false pass.

## Review trail

PLAN gate, Normal. Codex alone each round (melious out of balance; owner's rule 2026-10-27).
- Round 1: 2 RISKs. NOT_SHIPPED would recreate #445 inside the zip → list dropped. A `-x`
  exclusion escapes a text check → `-x` patterns checked.
- Round 2: 1 RISK. `'*/name.sh'` escaped a `scripts/`-substring check → glob match instead.
- Round 3: 1 RISK. An unquoted `-x` token escaped a quoted-only parse → every token after
  `-x` is read. Fixed without a fourth round; the DIFF gate checks it.

DIFF gate, Normal. Codex alone each round (melious out of balance).
- Round 1: 1 BUG. A `-x` token with a backslash or a space inside quotes split into a pattern
  that matched nothing → such tokens refused.
- Round 2: 1 BUG. Concatenated quotes (`"a""b"`) still passed → a `-x` token is read only as
  one word, or one word in one pair of matching quotes; anything else is refused.
- Round 3: clean. The script's reply check rejected Codex's answer; counted by hand from the
  raw output (no BUG, RISK or NIT). Its two UNVERIFIABLEs (full test run, stock /bin/bash)
  were settled by running both here.
