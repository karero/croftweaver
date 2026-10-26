# PLAN — docs/BUGLOG.md merges with git's union driver, and a guard catches a row kept twice

Status: done. Built and merged in karero/croftweaver#416 (2026-10-26). Owner's words (2026-10-26): "docs/BUGLOG.md
merge=union in .gitattributes, plus a make check guard that fails on a duplicated row. Plan first."

## Status

| Step | State | Evidence |
|---|---|---|
| Plan, PLAN gate | done: clean at round 7 (Codex); GLM reviewed rounds 1–4 only (no quota for 5–7) | `docs/reviews/REVIEW-plan-2026-10-26-buglog-union.md` |
| Owner's go | given 2026-10-26, in chat | — |
| Build: attribute, guard, test, duplicate removed, intro sentence | done | 20ea6973, e2640881; review fixes f7405ae3, c3a77850, 173253a2, 6a5e2076 |
| DIFF gate, PR, merge | done: DIFF gate clean (3 rounds and a full read); karero/croftweaver#416 merged at 6a5e2076, merge commit 4b5b927c | `docs/reviews/REVIEW-diff-2026-10-26-buglog-union.md` |
| Owner: `buglog-rows` added to the ruleset's required checks | done 2026-10-26 (ruleset 24584953 updated 13:28 +01:00, read back with `gh api`: 38 required checks) | — |

## What

1. `.gitattributes` gets one line: `docs/BUGLOG.md merge=union`, with a two-line comment.
2. A new guard, `scripts/check_buglog_rows.sh`, in `make check` (so in CI too): it fails when two
   rows of `docs/BUGLOG.md` look like two versions of one row.
3. A new test, `scripts/test_buglog_rows.sh`, in `make check`.
4. The duplicate already on main is removed (see Why), so the guard starts green.
5. One sentence in the BUGLOG's intro, where everyone who adds a row reads it.

## Why

Measured 2026-10-26 on `origin/main` (428b7ba1), over the 282 merges since 2026-10-12. In 57 the
BUGLOG differs from both parents (`git diff-tree --cc`). Replaying each with
`git merge-file -p <first parent's file> <merge base's file> <second parent's file>`: 12 merge cleanly (separate hunks),
45 conflict, about three a day. Those 45 replayed with `--union`, comparing rows as a multiset
with the recorded result:
- 33 give the same rows. Union alone would have done the person's work in 32. The 33rd is
  1641021d, where the person kept a row twice, as union does (below).
- 2 (7c75855e, 3c402741) differ only by a row the person reworded during the merge, a wording
  neither side had. No driver can produce that; union keeps one side's wording and the guard
  stays silent. Today the conflict makes the person reread the row; with union nothing does.
  Accepted cost: the row keeps one side's wording until someone rereads it.
- 10 keep stale versions of rows one side edited (afa35e65, 75d5287c, f5359943, 89341c56,
  007faae6, 285f9a80, d0e3b21e, 3584e3c6, 361a75de, 11b00231): 1 to 7 rows each. The guard's two
  rules below, run over each union result, flag every one of those rows.

So with union and the guard: 32 of the 45 conflicts need nothing; 11 (the 10, and 1641021d) need
the stale rows the guard names deleted. 4 lose a wording the person wrote during the merge: the 2
above, and d0e3b21e and 11b00231 among the 10, where deleting the stale row still leaves one
side's wording.

Why stale versions appear: when one side edits a row near the end (closing it, or rewording) and
the other appends after it, git sees one conflict hunk, and union keeps both sides. Merge
1641021d did exactly that by hand on 2026-10-26: `docs/BUGLOG.md` on main holds two versions of
the row "Next release notes, for the phone-image test", the edited one at line 185 and the merge
base's at line 189. Replaying that merge with `--union` keeps the same two rows.

## How

**The attribute and where it works.** It is a merge attribute, read from the `.gitattributes` of
the checkout being merged into. This plan relies on it in a local `git merge`, and in a
`git pull` that merges (not one set to rebase); that is how sessions resolve these today
("Merge branch 'main' of …"), and test case 9 runs that path. Rebase and cherry-pick are not
claimed. Limits:
- A branch cut before this lands has no such line, so its first merge of `main` can still conflict.
  Once that merge is done, later ones use union.
- GitHub: the repo has "Update branch" switched off (`allow_update_branch: false`) and its ruleset
  does not require an up-to-date branch (`strict_required_status_checks_policy: false`), both read
  with `gh api` on 2026-10-26. So the only server-side merge is the PR's own. Whether GitHub's merge
  honours `merge=union` was not checked. If it does not, a PR shows a conflict as it does today and
  the session merges `origin/main` locally. If it does, the PR's merge commit itself can keep a row
  twice when `main` moved after the PR's last CI run. `clean.yml` runs `make check` on every push to
  `main` (`on: push: branches: [main]`), so the guard reports it on that merge, after the fact, and
  the next session's `make check` fails until a row is deleted.
- No script or CI job in the searched files merges this repo's BUGLOG: `git grep -E '\b(merge|pull)\b'` over `Makefile`,
  `scripts/`, `.github/` and every `.sh`, `.mjs` and `.py` file, keeping lines that mention git,
  finds messages telling a person to pull, merge-base checks, site templates' own docs, and
  merges inside throwaway repos that hold no BUGLOG: `test_failed_tier_report.sh`, and the site
  template's `tests/check_ship_push.sh` (`git -C "$C" pull -q --ff-only`, line 976). A merge
  named on a line without "git", or in another file type, would not show; the guard in `make check`
  still reports what it leaves behind.
- The line ships in the handoff zip and on the `directory` branch with the rest of
  `.gitattributes`. Neither holds `docs/BUGLOG.md`, so it does nothing there.

What a session still does: merge `origin/main` locally (not on GitHub), then run `make check`,
and delete any stale row the guard names. The BUGLOG intro gets one sentence saying so.

**The guard.** It reads `docs/BUGLOG.md` from the repo root it sits under (as
`check_template_coverage.sh` does). A row is a line starting `| YYYY-MM-DD |`. Cells split on
` | `: the first is Found, the second Where, the third What. A row that does not split into
exactly 7 parts, one per column, is a FAIL naming the line: a bare ` | ` inside a
cell, which GitHub's table splits too, so the author writes `\|`. Every row in every version of the
file since 2026-09-20 splits into 7. So an added or removed ` | ` cannot shift the guard's cells
(Codex, round 3: Where changed from `alpha beta` to `alpha | beta` made both rules miss). A
separator moved between two cells keeps 7 parts; that is an edit changing Where and the opening of
What, inside the miss set under Not in scope.
Words are runs of non-blank characters (`split` with `" "`). Two rows are reported when
(a) they have the same Found date and the same Where cell, or (b) the first 20 words of their What
cell (all its words, if it has fewer) are the same, whatever the dates. Why:
- Over every version of the file since 2026-09-20, Found+Where matched two pairs: the phone-image
  pair (a real duplicate) and, on 2026-10-12, two `SCAN_BASE` rows about different folders
  (`packages/`, `.claude-plugin/`), a false alarm. On 428b7ba1 the second of those has Where
  `` `scripts/check_clean.sh`, `SCAN_PRESENT` ``, and the phone-image pair is the only one either
  rule matches (checked here, and by Codex in rounds 1 and 2). The first 20 words of What told the
  `SCAN_BASE` rows apart (the first 8 did not); the phone-image pair's What agrees for 63 words.
- Rule (b) across dates: over the same versions, the only What openings shared by two rows were
  the phone-image pair. So (b) costs no false alarm there, and catches an edit that changed only
  the Found date.
- In the non-merge commits since 2026-10-12, 153 row edits kept their date and Where (paired on
  those two cells), and 20 of them changed the first 20 words of What: (b) alone would miss those,
  (a) catches them. At most 8 more rows lost their Where, by an edit or a removal: (a) alone would
  miss those that were edits, (b) catches them unless the opening changed too.
- A third rule on shared words was tried and dropped: versions of one row share as few as 32% of
  their What words (63b16c41), while different rows of one day share up to 62%. No threshold
  separates them.
- The longest What opening two different rows have shared, in any version since 2026-09-20, is 9
  words (final full read), so the window of 20 has room.
- Cost: two different rows written the same day about the same Where, or opening with the same 20
  words, must be worded apart. The `SCAN_BASE` pair is the one case in two weeks. The message says how.

Message, exit 1:

    FAIL — docs/BUGLOG.md holds two rows that look like two versions of one row
           (same Found date and Where, or the same first 20 words of What):
      line 185: | 2026-10-25 | Next release notes, for the phone-image test (branch …
      line 189: | 2026-10-25 | Next release notes, for the phone-image test (branch …
    A merge probably kept both sides of an edited row (docs/BUGLOG.md merges with git's union
    driver; see .gitattributes). Make it one row: keep what each side changed, delete the rest.
    To see the file as it was before either side changed it, run right after the merge:
      git show "$(git merge-base HEAD^1 HEAD^2)":docs/BUGLOG.md
    If they really are two different rows, give them different Where cells and a different start
    to What.

Union keeps the two versions in either order (the final full read saw both), and when both
branches edited the row neither version is the merge base's (Codex, round 5). So the message names
no version to delete, and no search for the row (a branch may have renamed its Where; Codex,
round 6): it says what the one row must hold and how to see the file before either change. Each row is shown cut to 100 characters. All pairs are listed, not just the first. Also:
- No rows found: FAIL, so a reformatted file cannot pass by matching nothing.
- Built (DIFF round 1, Codex): any other line starting `|` that is not the header or its `|---|`
  line is a FAIL too (a row written without spaces, a mistyped date), and trailing blanks after a
  row's last bar are ignored.
- No `docs/BUGLOG.md` and nothing named `.git` (folder, or a worktree's file) at the repo root:
  the handoff zip. `package.sh` zips named paths only, none of them `.git`, and excludes
  `docs/BUGLOG.md`. Print `skip — no docs/BUGLOG.md (the handoff zip leaves it out)` and exit 0.
  With `.git` there, a missing file is a FAIL.
- Pass: `ok   docs/BUGLOG.md: N rows, none twice`.

**The test** (`scripts/test_buglog_rows.sh`) enters as `make check` does: it copies the guard into
throwaway folders laid out like the repo and runs `bash scripts/check_buglog_rows.sh` there.
Cases:
1. The repo's own `docs/BUGLOG.md` passes (after step 4). In the handoff zip, which has no BUGLOG,
   this case says `skip` and the others run.
2. A row repeated with only its Status changed, and a second such pair elsewhere in the file:
   fails, and names all four line numbers (every pair is listed).
3. The phone-image shape (same date and Where, What differs after word 20): fails.
4. Same date and Where, What differs early: fails (rule a).
5. Different date and Where; What agrees for exactly 20 words and differs at word 21: fails
   (rule b). The same with What differing at word 20: passes (pins the window from both sides).
   Two rows whose whole What is the same 12 words: fails.
6. The `SCAN_BASE` shape, Where worded apart, What agreeing for 8 words: passes.
7. Same date, different Where, different What opening: passes. Same Where on different dates,
   different What opening: passes.
8. A row with a bare ` | ` in a cell: fails, naming its line. A file with no rows: fails. No file with `.git`: fails. No file, no `.git`: skip, exit 0.
9. Replay, with real `git merge` in a throwaway repo whose `.gitattributes` is copied from this
   repo: base has a header and three rows; branch `a` appends one row, branch `b` another. The
   merge exits 0, leaves no conflict markers, keeps both rows, and the guard passes. Control: the
   same merge with that `.gitattributes` removed conflicts, so the case fails if the line is lost.
10. Replay of the incident: `a` sets the Status of the last row, `b` appends one. The merge exits 0
    and the guard fails, naming the two versions.
11. Replay of a row edited on both sides: `a` and `b` set the last row's Status to different
    values. The merge exits 0, keeps both edited rows and neither base row, and the guard fails,
    naming both.
Git runs hermetic. As in `test_whats_new_removed_skill.sh`: `GIT_CONFIG_GLOBAL` and
`GIT_CONFIG_SYSTEM` point at `/dev/null`, and each call sets `user.name`, `user.email`,
`init.defaultBranch`, `commit.gpgsign=false` and `core.hooksPath=/dev/null`. Added here, because
attributes decide this test: `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT` and its
`GIT_CONFIG_KEY_n`/`GIT_CONFIG_VALUE_n` are unset; each call sets `core.attributesFile=/dev/null`
(the user's attributes file) and `init.templateDir=` (no template hooks or info/attributes);
`GIT_ATTR_NOSYSTEM=1` (the system attributes file). Without git, cases 9–11 skip and say so; the
rest still run. The test makes its folder with `mktemp -d` in the house pattern and is added to
`SCRIPTS` in `scripts/test_mktemp_guard.sh`.

**Wiring.** Both scripts go into:
- the Makefile's `check:` (its help text gets the guard and the test's need for git);
- `scripts/package.sh`: the zip's input list and its `REQUIRED` list, since the zip's own
  `make check` calls them (CI's `macos-stock-tools` job runs it there);
- a `buglog-rows` job in `.github/workflows/clean.yml` running both, as every guard has its own
  job (`template-coverage`, `whats-new`, …), so a failure names the guard and runs on Ubuntu too;
- `scripts/check_cdpath_safe.sh`: the guard in `SUBJECTS`, the test in `NOT_RUN` (it builds
  throwaway repos), or `make check` fails;
- `scripts/test_mktemp_guard.sh`: the test in `SCRIPTS`.
The owner's step after the merge: add `buglog-rows` to the required checks of the "main checks"
ruleset (24584953), as the other guards are. A repository setting, so the owner's.
The `.gitattributes` comment must not hold the word "filter": `scripts/plugin.test.mjs` refuses
`export-ignore|export-subst|filter` anywhere in the file the `directory` branch keeps.

**Step 4.** In the build's first commit, delete the older of the two phone-image rows (line 189,
the version the merge base held), keeping the edited one at line 185. A separate commit, so it
reads on its own.

## Not in scope

- What the guard misses: an edited row whose versions differ in Where and in the opening of What
  (any date), or in Found date and in the opening of What. Union can keep both. Seen: two of the
  edits since 2026-10-12 changed Where and the opening of What together (7ab51d43, 63b16c41); a
  missed row needs such an edit while the other branch changes the same row or a row next to it.
  None of the 10 stale-version merges above had that shape.
- Two other things union does that the guard cannot see: a row one side deleted comes back if the
  other side changed a row next to it (rows are closed by Status, so deletions are rare; 836cfdb2
  is one), and an intro paragraph edited on both sides is kept twice. Follow-ups if they occur.
- Reordering, or checking rows beyond the cell count. Other tools read the table as it is.

## Other repos with a bug log (not changed here)

The owner's other repos keep a bug log in the same format; several of them, on GitLab, hand-merge
theirs often too. Their names and counts are in the owner's own notes, not in this public repo.
Whether GitLab's merge honours the attribute was not checked.

## Review

PLAN gate, Normal: Codex + GLM 5.3. Melious was out of credit in rounds 1 to 3, so GLM 5.3 ran
on ollama (`glm-5.3:cloud`) in its place; the trail records each round. DIFF gate after the build, Normal at least (a guard
script's logic is never Light). `make check` green before each round.
