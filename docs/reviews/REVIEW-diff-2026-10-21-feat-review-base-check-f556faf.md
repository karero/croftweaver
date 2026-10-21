# DIFF review — feat/review-base-check — refuse a review diff on the wrong base (change 1)

Base `6681e7be` · depth: Normal (the logic of a guard script, which the owner's rule never puts at Light; no login, money, user data or deletion, so not High) · verdict: OPEN · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch); POST AUTHORITY: none yet (no PR)

The diff is 159 KB with the whole of `test_failed_tier_report.sh`, over the script's 117 KB limit, so it was split (SKILL.md step 2): the change without that file went to the pair and fresh-eyes at Normal; that file's edit, which only adds `--base none` to its diff runs, went to a Light pass (Codex alone, the owner's rule for test wiring). Checked before the split: its 189 removed lines equal its added lines once ` --base none` is taken out, and every added line carries it. The branch's own new check ran on both pieces and named the left-out files on its `base:` line.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `f556faf3` | full since `6681e7be`, less `test_failed_tier_report.sh` (62 KB) | codex-cli 0.163.0, gpt-6.1-sol, effort high (config), read-only · Melious glm-5.3, HTTP API, text only · fresh-eyes: Claude Code sub-agent, Sonnet, read-only by instruction | codex 505 s, 136,781 · melious 488 s, 70,514 · fresh-eyes 1,198 s, 255,223 | 4/7/13 raw (codex 2/1/0, melious 0/1/3, fresh-eyes 3/2/5, after dedup 3/4/7) |
| 1, Light | `f556faf3` | `test_failed_tier_report.sh` alone (97 KB) | codex-cli 0.163.0, gpt-6.1-sol, effort medium, read-only | codex 79 s, 61,845 | 2/0/0 (one pre-existing) |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| D1-01 | BUG | codex, fresh-eyes | 1 | A one-patch `format-patch` whose last record has no hunk was refused: the mail signature `-- ` read as an unknown header | fixed, locally_verified | the record ends at the signature; T4 runs a one-patch format-patch ending in a mode-only record |
| D1-02 | BUG | codex, fresh-eyes | 1 | A rename from a plain name to a C-quoted one (`diff --git a/f "b/\303\274…"`) was refused as "a prefix other than a/ and b/" | fixed, locally_verified | names come from `rename`/`---`/`+++` lines; the `diff --git` line is read only for a same-path record, where git quotes both names or neither; T4 renames `plain.txt` to `über.txt` |
| D1-03 | BUG | fresh-eyes | 1 | A file that became a symlink (or back) was refused: git writes two records for one path | fixed, locally_verified | the comparison is by side (old side of a path, new side of a path), in the diff and in git's patch; T4 has both type changes |
| D1-04 | RISK | codex | 1 | A new-file record cut off after `new file mode` passed with no id compared | fixed, locally_verified | a record with no `index` line must be a mode-only change or a pure rename, else refused; T5 refuses the cut record |
| D1-05 | RISK | melious | 1 | The check read headers only, so a diff made with `-w` passed while its hunks hid lines | fixed, locally_verified | new content step: the text records are applied to the base with `git apply --cached` in a throwaway index and must give the target's content for each file they name (plan rule 6, added); T5 refuses a `-w` diff and a record whose hunks were cut. A file `-w` leaves out altogether is named on the `base:` line (git drops such a record entirely: checked) |
| D1-06 | RISK | fresh-eyes | 1 | `scripts/package.sh` did not require the two new Perl programs or the new test in the handoff zip | fixed, locally_verified | REQUIRED lists all three |
| D1-07 | RISK | fresh-eyes | 1 | With `diff.renames=copies` set, plain `git diff` writes copy records, and the printed remedy made the same diff | fixed, locally_verified | the remedy carries `-M` (checked: it turns copies back into renames under that setting) and `--no-textconv`; T4 runs the printed remedy with the setting on |
| D1-08 | NIT | melious, fresh-eyes | 1 | The "nothing to review" message said "the base is HEAD", true only in one of its cases | fixed, locally_verified | "git sees no change from the base to HEAD or to the working tree" |
| D1-09 | NIT | melious | 1 | The test failed instead of skipping without perl; two descriptions said "needs git" only | fixed, locally_verified | SKIP without perl; Makefile and check_cdpath_safe.sh say git and perl |
| D1-10 | NIT | melious | 1 | A format-patch whose message quotes a `diff --git` line would read it as a record | fixed, locally_verified | the reader skips a format-patch's message up to its `---`; the content step applies only the records' own lines; T4's format-patch quotes one |
| D1-11 | NIT | fresh-eyes | 1 | closeout.md's re-gate text did not say `--base <that head>` | fixed, locally_verified | it does now |
| D1-12 | NIT | fresh-eyes | 1 | No test for uncommitted work on the default branch or a submodule; the test file was not executable | fixed, locally_verified | T4 has both; mode 100755 |
| D1-13 | NIT | fresh-eyes | 1 | The fetch did not set `GCM_INTERACTIVE=never` as git-stand.mjs does | fixed, locally_verified | it does now |
| D1-14 | NIT | fresh-eyes | 1 | Over-long lines in SKILL.md; no word on a PR that targets another branch | fixed, locally_verified | reflowed; SKILL.md step 2 names `--base <its merge base with that branch>` |
| L-01 | BUG | codex (Light pass, pre-existing) | 1 | Two test descriptions said the key is "nowhere on disk", while the stub keeps its own capture | fixed, locally_verified | "nowhere in the run's raw folder", and the stub's comment says the capture is the test's own record |
| L-02 | BUG | codex (Light pass) | 1 | test_failed_tier_report.sh's header said "default flags" while its diff runs now pass `--base none` | fixed, locally_verified | the header says why they pass it |

Waivers and deferrals: none.
Follow-ups: none yet.
Notes: substantive BUGs in round 1: D1-01, D1-02, D1-03 (all false refusals of diffs git made). D1-05's fix adds a step the plan did not have; the plan now records it as rule 6. `make check` skips the Perl 5.8 syntax check on this Mac (no Perl::MinimumVersion); CI runs it.

<details><summary>Round 1 raw output — codex and melious (independent_review.sh stdout; absolute paths in codex's links made repo-relative)</summary>

## Independent review — codex (gpt-6.1-sol, read-only)

- BUG [diff_headers.pl:130](skills/independent-review/scripts/perl/diff_headers.pl:130) — **WRONG:** single-patch `format-patch` support fails when the final record has no hunks: `$hdr` remains set and Git’s `-- ` signature separator is rejected; reproduced with `git format-patch -1 --stdout -I '^' 738daa5e -- scripts/check_pipefail_pipes.sh` (reader exit 3). Fix: recognize the mail footer after metadata records; test final mode-only changes, pure renames and empty-file additions.
- BUG [diff_headers.pl:70](skills/independent-review/scripts/perl/diff_headers.pl:70) — **WRONG:** quoted-name support misses an unquoted old name followed by a quoted new name, rejecting that header before rename headers can supply the paths; Git emitted this mixed form in a read-only `--no-index` probe with a tab-containing destination prefix. Fix: decode each name independently and test renames from ordinary names to names requiring quoting.
- RISK [diff_headers.pl:201](skills/independent-review/scripts/perl/diff_headers.pl:201) — **VERIFIED guard gap:** a new-file patch truncated immediately after `new file mode 100644` returns success without comparing any object ID, so incomplete added content can receive a checked-base result. Fix: require index IDs for additions/deletions, allowing ID-free records only for validated mode-only changes and pure renames; add truncated-header tests.

Checked CLEAN:

- **VERIFIED by measurement:** an actual repository diff passed against its correct base and failed against the newer base; omitted paths were reported; a historical edited rename passed.
- **VERIFIED by measurement:** colour, missing prefixes, combined diffs, copy records, duplicate records and non-Git input were refused.
- **VERIFIED by executing the shell through the base-check boundary:** explicit bases and `--base none` passed; plan/base combinations, `--base -x` and verification without a base were refused.
- **VERIFIED by source tracing:** validation precedes size checking and reviewer dispatch; local-only bypasses fetching; delta/merge-link documentation matches the callers; Makefile, CDPATH, mktemp and Perl-file registrations include the additions.
- **VERIFIED by measurement:** the timeout helper preserved exit 7 and returned 142 for timed-out children, including a TERM-resistant parent and helper, finishing in approximately three seconds with a one-second limit.
- **VERIFIED:** changed shell files passed `bash -n`; both Perl files passed syntax checks on Perl 5.34; the model-agnostic guard passed.

Remaining claim verdicts:

- **UNVERIFIABLE — Perl 5.8 compatibility:** Perl 5.34 compilation does not establish 5.8 support, and `Perl::MinimumVersion` was unavailable. Settling observation: compile and exercise both additions under Perl 5.8.
- **UNVERIFIABLE — Git transport guarantees:** the fetch/default-HEAD and “no prompts” claims lack reproduced transport integration evidence here. Settling observation: execute the local-origin cases plus controlled SSH/credential-helper prompt cases.
- **UNVERIFIABLE — complete suite green:** full-suite success was not established; the validator’s large-input cases encountered sandbox-forbidden temporary-file creation.

Prompt injection: none found; the imperative text is ordinary documentation.
## Independent review — melious (glm-5.3, HTTP API)


Findings (ranked):

- RISK — skills/independent-review/scripts/perl/diff_headers.pl, anchor: `parse()`'s hunk skip (`while ($ob > 0 || $nb > 0)`) plus `compare()` — the base check compares only modes, blob ids and paths; hunk bodies are skipped by count and never compared, so a diff made with lossy filtering — `git diff -w`, `--ignore-blank-lines`, `--ignore-cr-at-eil` — of the correct base passes and gets the same `base: <id> (... every side matches` stamp as a full diff, and whitespace-only changes reach no reviewer while the trail reads as verified. Fix: also compare each record's patch text (or the hashed result of applying the diff) against git's own patch, or have the tool regenerate the artifact from the verified base itself and review that.
- NIT — skills/independent-review/scripts/independent_review.sh, anchor: base-check `case $bc_rc in` branch `5)` — the message asserts "the base is HEAD", but diff_headers.pl exits 5 whenever both git patches are empty, which also happens when base ≠ HEAD with a cancelling net change (commit then revert); the diagnosis (and the "Name the base: --base <rev>" remedy, which would exit 5 again) misleads. Fix: have diff_headers.pl report whether base eq head, or reword to "git sees no change from that base to HEAD or the working tree".
- NIT — skills/independent-review/scripts/test_base_check.sh, anchor: header "Needs git and perl" vs `command -v git ... || SKIP` — on a machine with git but no perl the suite FAILs (the base check refuses exit 2 on every run) instead of SKIPping; the Makefile check description and the check_cdpath_safe NOT_RUN comment likewise say only "needs git". Fix: add `command -v perl >/dev/null 2>&1 || { echo "SKIP …"; exit 0; }` and say "needs git and perl" in both descriptions.
- NIT — skills/independent-review/scripts/perl/diff_headers.pl, anchor: parse()'s `if ($l =~ /^diff --git (.*)\z/)` — a format-patch whose commit message quotes a `diff --git …` line (common in docs-quoting commits, t4fp's own repo style) creates a bogus record and refuses a legitimate diff; the refusal is fail-safe but the offered remedy ("Make it with git") won't help. Fix: in mbox mode, ignore non-header lines until the `---`/diffstat region, or skip `diff --git` lines that appear before the first mbox `---` separator.

No BUG findings.

What I checked and found CLEAN:

- Option parsing: `--base <rev>|none` validation (missing value, leading-dash value), USAGE string, refusal of `--base` on a plan, `--base none` short-circuit, the `--verify`-needs-`--base` guard and its exact wording.
- Shell base check ordering: after type detection, before the size check (T8's claim holds by placement); refusals exit 2 before any reviewer runs.
- Timeout parsing: `''|*[!0-9]*|0*` plus the ≤3-digit/≤600 test covers 0, leading zeros, non-numeric, and >600.
- The fetch subshell: exit-status propagation to `fetch_rc`, GIT_TERMINAL_PROMPT=0, conditional GIT_SSH_COMMAND (respecting a user's ssh), core.sshCommand, low-speed http configs; FETCH_HEAD/origin-HEAD/`--local-only`/no-merge-base branches and their hint texts.
- `bc_out` parsing: tab-splitting cases, esc'd paths (no stray tabs), empty-output fallback into the `*)` refuse branch, remedy construction (HEAD vs working tree, quoted top).
- diff_headers.pl parse: colour-code check placed outside hunks (so ESC in file content can't false-positive), mbox single-vs-series, combined, copy, index/mode/new-file/deleted-file/similarity/rename headers, binary records, hunk-count skipping including `\ No newline` and empty context lines, quoted/unquoted names in `---`/`+++` (with the tab strip — the code works whether git appends the tab or not) and in the `diff --git` line (both-quoted and both-unquoted paths traced), /dev/null and all-zero-id handling, the `%seen` duplicate-path refusal.
- diff_headers.pl compare: modification, add, delete, pure rename (against git's --no-renames delete+add pair, including the no-ids content check), rename with edit, mode-only, ids-vs-modes xor, prefix `id_ok`, worktree-vs-HEAD dual-target strategy, best-target tie-break, exit-5 condition, left-out coverage excluding `docs/reviews/` only.
- run_limited.pl: read in full — setpgrp in the child only, TERM→2s→KILL to the group, `$late` → exit 142 before the signal-status mapping, 128+sig mapping, 127 on exec failure; t5hang traces the timeout claim (see UNVERIFIABLE for its fixture).
- check_perl_minimum.sh: both new programs placed in UNGATED; both read as 5.8-clean (no `//`, `say`, or other newer constructs).
- Wiring: test added to the Makefile check list, to check_cdpath_safe's NOT_RUN (with a stated reason matching its siblings), and to test_mktemp_guard's SCRIPTS — the test does stop with an error when mktemp fails (`T="$(mktemp -d …)" || { echo FAIL; exit 1; }`).
- Docs vs code: SKILL.md (default base = fetched origin HEAD merge base; `--base` for deltas/merge link/wording pass; `--base none`; base: line beside reviewers:/timings:), closeout.md, website-review and seo-reposition SKILL.md — all match the implemented behaviour, including the honest "no prompts"/"the fetch sends nothing of the artifact" scoping.
- test_base_check.sh traced end-to-end against the code: T1 (recomputed merge base B and the mismatch/remedy strings), T2 (base A, FETCH_HEAD = o2's HEAD), T3 (delta old-side id mismatch vs base A), T7 (recomputed: x at A is "x one" on branch `old`, so the D1..D2 delta's old side matches; left-out y), T4 records (rename/mode/quoted/binary/symlink/no-newline/dash-line fixtures), T4 sub-directory, format-patch single, --cached, working tree, T5 refusal cases (mnemonic, index-vs-worktree, stale mode, hand-made, --no-prefix, colour, --cc, copy, series, not-a-repo, --base none, --base -x, --base on plan, timeout=0, on-main exit 5, unrelated history, failed fetch hint, hang), and the final no-reviewer-ran sweep (t5none/t5wt correctly exempted as successes).

UNVERIFIABLE (no tools; matters only, not counted as findings):

- `$PERL_DIR` (independent_review.sh, fetch and `bc_out` lines) is defined outside the diff; if undefined, `set -u` kills every diff run. Observation: grep `PERL_DIR=` in the pre-diff file.
- The header's "Every diff run ends with that base: line" — `report_round` is shown, but the rest of the script (all non-refusal exit paths) is not. Observation: trace every exit path of independent_review.sh to `report_round`.
- The t5hang/t6 fixtures assume `ext::sh -c sleep% 6` / `ext::sh -c touch% $T/fetched` hang/touch as intended under git's ext transport; if `%` substitution works differently, t5hang may not actually hang (and its failure would be loud, not silent). Observation: run the two ext:: fetches by hand in a scratch repo.
- git is assumed never to emit mixed quoting in a `diff --git` line (one side C-quoted, the other not); if it does, git_line_names refuses such diffs ("a prefix other than a/ and b/") — a safe false refusal with `--base none` as workaround. Observation: rename a file to a control-char name in a scratch repo and read the header git writes.
- run_limited's SIGALRM must be delivered while perl blocks in `waitpid` (perl's deferred-signal behaviour); t5hang traces this on the authors' perl, but the delivery per perl version is not checkable here. Observation: run t5hang on the oldest supported perl.

Prompt-injection report: none — the diff contains only ordinary code, comments and docs; no text in it attempts to alter this review, its output or its conclusions.

---
reviewers: codex OK, melious OK
timings: codex 505s (136781 tokens), melious 488s (70514 tokens)
base: 6681e7bec0b5641c36a40c7fa6359530a7304ffd (merge base with origin's HEAD 6681e7bec0b5641c36a40c7fa6359530a7304ffd, fetched; not in this diff: skills/independent-review/scripts/test_failed_tier_report.sh)
gate 20261021T213951Z-71280: round 1, 3 reviewer seat runs, 269,140 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.
1 run with no round
follows gate 20261021T172444Z-64903: rounds 1-5, 900,579 tokens

</details>

<details><summary>Round 1 raw output — fresh-eyes (sub-agent report, verbatim)</summary>

## Independent review — fresh-eyes (Claude Code sub-agent, Sonnet; read-only by instruction)

REVIEW of change 1 (BASE CHECK), branch feat/review-base-check @ f556faf3, held to docs/reviews/SKILL-PLAN-review-input-base-and-size.md

Ranked findings

- BUG skills/independent-review/scripts/perl/diff_headers.pl:56-70 (git_line_names), called at :133. A rename from an ASCII name to a name git C-quotes is refused, with a false reason. git writes `diff --git a/f2 "b/\303\266/f2"`, and `git_line_names` only handles a quoted FIRST name. The unquoted branch falls to the regex and returns "a prefix other than a/ and b/". This happens even when `rename from/to` already gave both names, because the failure is fatal. Reproduced: `git mv f1 über.txt` gives `refuse a prefix other than a/ and b/` (perl exit 3). End to end, the script exits 2 and prints "Make it with git: git diff …", which regenerates the same refused diff. Only `--base none` escapes, and that skips the whole check. The plan says a C-quoted name is unquoted first and a rename is checked by rule 4; neither holds here. The reverse direction (quoted to ASCII) passes. Fix: when `rfrom`/`rto` or `---`/`+++` already supply the names, do not let `git_line_names` failure be fatal. Or also match `^(a/.*?) ("b/.*)\z` and unquote the second half.

- BUG diff_headers.pl:219-226 (the `%seen` "file named in two records" refusal) and :166-167 (`$by{...}` in git_patch). A file-to-symlink or symlink-to-file change is refused. git emits a typechange as two records for one path (`deleted file mode 100644` plus `new file mode 120000`). Reproduced with `rm tc; ln -s f1 tc` and with symlink to file: `refuse a file named in two records ("sl")`. The printed remedy produces the same two-record diff, so it loops. The plan's table says symlink is "checked by its index line", and a git-made diff on the right base is refused. The same hole exists in git_patch, where the second record overwrites the first in `%by`. Fix: pair a deleted-only and a created-only record on one path as a single typechange record (old side from the first, new side from the second), in both parse and git_patch.

- BUG diff_headers.pl:130 (the "header line this check cannot read" branch). A one-patch `git format-patch` is refused when its last record has no hunk (mode-only, pure rename, empty file). The mbox signature `-- ` plus the version line follow, `$hdr` is still 1, and `-- ` hits the else branch: `refuse a header line this check cannot read: "-- "`. Reproduced with a mode-only commit and with a rename-only commit. The plan table says one patch is "checked like a diff", and T4 only covers a patch ending in a hunk. The printed remedy (a plain git diff) does work here, so the harm is small. Fix: treat a bare `-- ` line as end of patch while `$hdr` is set.

- RISK scripts/package.sh:51-100 (REQUIRED). The handoff zip's integrity list names all seven existing perl/*.pl programs (commit 98c4735a: "package.sh lists all seven perl/*.pl files") and test_failed_tier_report.sh. It does not name the two new programs, diff_headers.pl and run_limited.pl, or test_base_check.sh. The Makefile now runs the test, and every `--diff` run without `--base none` needs both programs. The guard cannot fire for them. If they are missing, the zip builds green and every non-`--base none` diff run (and `make check` from the zip) fails at `perl`. Fix: add the three paths to REQUIRED. (`zip -r skills` ships them today.)

- RISK independent_review.sh refusal for exit 3 (the `Make it with git:` remedy, ~line 599-602) with diff_headers.pl:121 (copy record). Under `diff.renames=copies` in git config, a normal `git diff` writes `copy from/to` records. The check refuses them as "made with -C", and the printed remedy has no `-M`/`--no-renames`, so it reproduces the refused diff. Reproduced by setting `diff.renames=copies` globally and diffing a file copied beside a modified one. Fix: add `-M` (overrides the config) or `--no-renames` to the remedy, or name the config in the message.

- NIT skills/independent-review/references/closeout.md:136. The plan's "Docs touched" lists closeout.md "re-gates". The diff only changes the table header. The clerk's re-gate sends "the delta since that seat's last seen head" and still does not say `--base <that head>`. SKILL.md:136 is general enough, but the re-gate text should say it.

- NIT skills/independent-review/scripts/test_base_check.sh. The plan's T4 lists "uncommitted work on the default branch itself". The table lists submodule. The suite has only the refusing case (t5head, clean tree) and no submodule case. I checked both by hand (a submodule pointer change and a new submodule pass; the dirty default branch passes end to end with "new sides from the working tree"), so the code is right but unguarded. The file is also mode 100644; every sibling test script is 100755.

- NIT independent_review.sh:606 and diff_headers.pl:241. Perl exits 5 whenever both git patches are empty, but the message says "the base is HEAD (…)". With `--base X` where X's tree equals HEAD's tree, the message is false. Say "base and HEAD hold the same files" or test `base_id = head_id`.

- NIT independent_review.sh:550-558. The comment says the fetch is bounded "the way git-stand.mjs bounds its own". git-stand.mjs:29 also sets `GCM_INTERACTIVE=never`; this one does not. A Git Credential Manager dialog would wait out the 30 s limit instead of failing at once.

- NIT SKILL.md:136-137 and :145 are over-long hard-wrapped lines. The SKILL.md text does not name the stacked or non-default-target MR as a `--base <merge base with the target>` case. For that case the refusal's remedy (a diff from the merge base with origin's HEAD) includes the parent branch's commits.

Verdicts on checked claims

- Plan "C-quoted names unquoted first; rename checked by rule 4": WRONG for a mixed-quote rename (BUG 1).
- Plan "symlink checked by its index line": WRONG for a typechange (BUG 2).
- Plan "format-patch, one patch: checked like a diff": WRONG for a hunkless last record (BUG 3).
- Plan "the printed command makes a correct diff": WRONG for BUG 1 and 2 (covered there).
- VERIFIED: `--base` rules (a plan refuses it, a leading `-` is refused, an unresolvable rev is refused). `--verify` on a diff with no `--base` is refused, and `--base none` is exempt. The REVIEW_FETCH_TIMEOUT validation. The base check runs before the size check (T8). `INDEPENDENT_REVIEW_CHECKS_ONLY` exits before it, so test_round_checks.sh is untouched.
- VERIFIED: the `base:` line is printed by `report_round` on stdout and stderr.
- VERIFIED: merge_link.sh ends in `git diff "$reviewed" HEAD -- <paths>`, so `--base <last-reviewed-head>` is the right base for a merge link.
- VERIFIED: the git-stand.mjs bounding matches (BatchMode, ConnectTimeout, ServerAlive*, lowSpeed*, GIT_TERMINAL_PROMPT, 30 s), except GCM_INTERACTIVE.
- VERIFIED: the new `perl` mentions in independent_review.sh use only the forms check_perl_minimum.sh allows (its structure checks pass).
- VERIFIED: `git fetch origin HEAD` plus `FETCH_HEAD` works (T2), and a hung fetch is killed within the limit (T5, 3 s).

CLEAN (checked, no finding)

- `bash skills/independent-review/scripts/test_base_check.sh` passes under bash 5.3 and under /bin/bash 3.2.57 with Apple git 2.33.0 and perl 5.34.
- These guards pass: check_cdpath_safe, check_pipefail_pipes, check_model_agnostic, check_clean, check_prompt_sync, test_mktemp_guard, check_lf_checkout, check_skill_budgets, and the structure part of check_perl_minimum.
- diff_headers.pl accepted every git-made diff from this repo's history: `git diff P C` for 400 first-parent commits, 57 twelve-commit ranges, and `format-patch -1` for 300 commits.
- Edge records that passed: submodule pointer change and add, empty-file add, names with `"`, `\`, trailing space, inner space and a leading `-`, CRLF content, binary, `--binary`, `-U0`, `--minimal`, `-w`, `--abbrev=12`, `--no-renames`, `-M90%`, mode-only, a 100% rename, a rename with a space in the path, and a non-ASCII modify.
- git's own patch is immune to user config: with noprefix, mnemonicPrefix, renames=copies, quotePath=false, context, submodule=log, color.ui=always and diff.external set, diff_headers.pl still read it and returned `target HEAD`.
- Stale-base detection: the other commits' files are "same at the base and in HEAD" and the diff is refused (T1). A moved origin with an unmoved branch passes (T2).
- Bash flow: `set -u`, `bc_*` variable scoping, here-string loops (no subshell), and 3.2 compatibility all hold. The perl program reads all of stdin before any early exit, so there is no SIGPIPE under pipefail.

UNVERIFIABLE (by component)

- Perl::MinimumVersion on diff_headers.pl and run_limited.pl. Claim: "Perl 5.8 only", in both file headers, and `UNGATED_MAX=5.008`. No newer construct turned up on grep (no say/state/`//`/named captures/\K/\R). The module is not installed here, so the check printed SKIP. The observation that would settle it is running check_perl_minimum.sh where Perl::MinimumVersion is installed (CI's `make check` log).
- run_limited.pl on Linux perl: `waitpid` after `alarm` signal delivery, and `kill -$pid` of a group. Claim: "the whole group is ended", so a helper cannot hold the pipe. Observed only on macOS perl 5.34 (T5 hang took 3 s). The observation that would settle it is the T5 hang case run on a Linux runner.
- git other than Apple git 2.33.0. The claims are: a typechange splits into two records, a mode-only change has no `index` line, and `FETCH_HEAD` is per worktree and leaves `origin/<default>` alone. All were seen on 2.33 only. The observation that would settle it is the suite on a current git in CI.

NOTE (not from this review): during the review `git status` began showing `skills/independent-review/scripts/test_failed_tier_report.sh` as modified (comment edits about `--base none` and the key-on-disk wording). It was clean at the start. None of my commands write there, so another process is editing the checkout. I read the committed HEAD for everything above and left that file out, as instructed. I deleted my throwaway folder.

</details>

<details><summary>Round 1 Light pass raw output — codex on test_failed_tier_report.sh (independent_review.sh stdout)</summary>

## Independent review — codex (gpt-6.1-sol, effort medium, read-only)

- BUG — `skills/independent-review/scripts/test_failed_tier_report.sh:811,1299` — **WRONG, pre-existing:** “the key is nowhere on disk during the call” contradicts the stub, which writes the header to disk at line 198; its detector scans only `REVIEW_RAW_DIR` (206). Fix the descriptions to say “absent from REVIEW_RAW_DIR,” and document the deliberately persisted test capture.
- BUG — `skills/independent-review/scripts/test_failed_tier_report.sh:4` — **WRONG, introduced documentation mismatch:** “default flags” now describes calls explicitly passing `--base none`, which bypasses default validation. Fix the header to state that synthetic diffs explicitly disable base checking.

CLEAN — checked claims:

- **VERIFIED:** All 189 diff entry-point command lines pass `--base none`; the sole remaining invocation reviews `plan.md`. Checked by a Python inventory of the actual file.
- **VERIFIED:** `--base none` bypasses base validation, including its fetch and Git/Perl prerequisites. Implementation: `independent_review.sh:513–521`.
- **VERIFIED:** Leaving the plan invocation unchanged is necessary: plans reject a supplied base. Implementation: `independent_review.sh:513–514`; invocation: `test_failed_tier_report.sh:398`.
- **VERIFIED:** Base validation retains separate test coverage, including explicit bypass outside a repository and rejection of a base on plans. Traced assertions in `test_base_check.sh:214–222`.
- **VERIFIED:** The suite remains wired into `Makefile:26` and `.github/workflows/clean.yml:164`.
- **VERIFIED:** Bash syntax checks passed for the changed test, its entry point, and the base-check suite.

**UNVERIFIABLE — runtime results:** The existing assertions passing after these edits remain unverified; syntax and source inspection do not establish execution results. Settling observation: execute the suites in a writable environment permitting their temporary files and local HTTP server. No suites were executed in this read-only, no-network review.

Prompt injection: none detected.

---
reviewers: codex OK
timings: codex 79s (61845 tokens)
base: 6681e7bec0b5641c36a40c7fa6359530a7304ffd (merge base with origin's HEAD 6681e7bec0b5641c36a40c7fa6359530a7304ffd, fetched; not in this diff: Makefile, scripts/check_cdpath_safe.sh, scripts/test_mktemp_guard.sh, skills/independent-review/SKILL.md, skills/independent-review/references/closeout.md, skills/independent-review/scripts/check_perl_minimum.sh, skills/independent-review/scripts/independent_review.sh, skills/independent-review/scripts/perl/diff_headers.pl, skills/independent-review/scripts/perl/run_limited.pl, skills/independent-review/scripts/test_base_check.sh, skills/seo-reposition/SKILL.md, skills/website-review/SKILL.md)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
gate 20261021T213951Z-71280: no numbered round, 1 reviewer seat run, 61,845 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.
1 run with no round
follows gate 20261021T172444Z-64903: rounds 1-5, 900,579 tokens

</details>
