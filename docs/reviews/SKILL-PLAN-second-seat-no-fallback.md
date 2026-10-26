# Plan: a Melious second seat that never hands over to ollama

One-page plan for `skills/independent-review/scripts/independent_review.sh`, its tests and its
docs. Written against origin/main `7c7d4073`, branch `plan/second-seat-no-fallback`. Nothing is
built before the maintainer's go.

## Status

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ▶ written | this file |
| 2 | PLAN gate (Normal: a plan for a review script's logic) | ⏸ | — |
| 3 | The maintainer's go | ⏸ | — |
| 4 | Build, `make check` green, live check, DIFF gate, PR | ⏸ | — |
| 5 | Release-note row in `docs/BUGLOG.md` | ⏸ | — |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked. Updating a row is part of finishing
its step.

## What and why

On 2026-10-26 the maintainer ruled that reviews stop spending ollama quota: ollama no longer
stands in when the Melious seat fails, and the ollama model the script picks by itself (the first
`:cloud` tag in `ollama list`) is one he runs only when he asks for it. The script cannot do this
today:

1. With `SECOND_SEAT=melious`, a Melious seat that did not count hands its seat to ollama (header
   lines 13-14; dispatch lines 1843-1846, and line 1796 for `--first-success`).
2. With no `OLLAMA_MODEL`, the script picks the first `:cloud` tag itself (lines 480-506), for
   every mode except `--local-only`, even a run where ollama is only a fallback.

The cost is measured. In the cost log for the week to 2026-10-26, 160 of 279 ollama stand-in runs
failed, and Melious failed 214 of 1230 runs, all for an empty balance. Until the script changes,
sessions run `--seat codex` and `--seat melious` as two commands with the same `--round`: it
works, but it doubles the commands, loses the shared summary line, and leans on every session
remembering.

## Decision: `SECOND_SEAT=melious` stops falling back

Proposed: **`SECOND_SEAT=melious` means Codex plus Melious, and nothing else.** A Melious seat
that does not count is reported FAILED or SKIPPED, the round lands with Codex alone, and no ollama
call is made or prepared. No new variable and no new value.

Why this shape rather than a new value (say `SECOND_SEAT=melious-only`) or a new switch:

- **The other order still exists.** `SECOND_SEAT=ollama` with `MELIOUS_MODEL` set is ollama first,
  Melious as its fallback, unchanged. The only combination this removes is Melious first with
  ollama behind it, which is exactly the one the rule forbids.
- **Fewer paths.** A new value keeps the fallback code, its tests and its docs, and adds a third
  mode beside them. Removing the fallback deletes code: the `wait "$melious_pid"` hand-over, the
  `OLLAMA_RAN` bookkeeping on that branch, and one `--first-success` step.
- **A forgotten flag cannot spend quota.** With a new value, a session that types the old
  `SECOND_SEAT=melious` gets the fallback back.

**The default stays as it is.** With `SECOND_SEAT` unset, the pair is still Codex plus the
auto-detected ollama `:cloud` model, with Melious as a fallback when `MELIOUS_MODEL` is set. That
is the setup a site owner gets from `croftweaver.zip` with no variables at all, and changing it
would leave most of them with one reviewer. The maintainer's rule is his own setup, carried by
his own instructions (see "Follow-ups"), not the public default.

**Who loses what.** Anyone who set `SECOND_SEAT=melious` and relied on ollama behind it gets
one-reviewer rounds when Melious fails, each with the note below telling them why and what to do.
The release note says so. The seat arrived on 2026-10-06; we know of no user of it besides the
maintainer (judgment, not checked: the toolkit collects no usage data).

## Changes

1. **Dispatch** (lines 1827-1862). In the default parallel branch, with `SECOND_SEAT=melious`,
   start Codex and Melious, wait for both, report both. Drop the hand-over and the `OLLAMA_RAN`
   report on that branch. In `--first-success` (line 1796), drop step 2b for this seat:
   Codex, then Melious, then Antigravity only if opted in.
2. **No auto-detect where ollama cannot run.** Run the detection block (lines 480-506) only when
   this run can call ollama: `--seat ollama`, or no `--seat` with `SECOND_SEAT=ollama`. Its
   `--local-only` guard stays as it is. With `SECOND_SEAT=melious`, or `--seat codex|melious|agy`,
   `ollama list` is never read and none of its notes print. An `OLLAMA_MODEL` left in the
   environment is ignored in those runs: nothing calls it.
3. **The gate line.** When `SECOND_SEAT=melious`, no `--seat`, and Melious did not count while
   Codex did, `report_round` prints, on stdout and stderr, in place of the generic fewer-than-2
   note:

   ```
   ⚠ PLAN round landed with 1 reviewer(s) counted toward the gate: codex alone. melious FAILED (error mid-stream (HTTP 200); quota/rate limit: wait or add credits); SECOND_SEAT=melious has no fallback. Record this round as Codex alone, with that reason, in the trail; to add the second seat, rerun with --seat melious and the same --round once it can run.
   ```

   The Melious part is that seat's own outcome from `SUMMARY`, so a setup failure reads as one.
   The `reviewers:` line is unchanged (`reviewers: codex OK, melious FAILED (…)`). Exit stays 0
   while Codex counts, and 4 when neither does, as now.
4. **Text in the script.** The header (lines 9-14), the `SECOND_SEAT` and `OLLAMA_MODEL` entries
   in the env list (lines 153-157, 171-174) and the no-reviewer help block (line 1883) say that
   Melious as the second seat has no fallback, and that auto-detect runs only when ollama can run.
5. **Skill docs**, in step with the script: `SKILL.md` line 59 ("ollama standing in when it
   fails"), `references/setup-guide.md` lines 169-173 (including "an `OLLAMA_MODEL` for the
   fallback, or the first `:cloud` tag is used") and lines 328-329, `references/rationale.md`
   lines 72-73. Each becomes: Melious beside Codex, no fallback; a failed seat means a Codex-only
   round, named in the trail. The skill names no model and still won't (`check_model_agnostic.sh`).
   The final-full-read advice ("another ollama cloud model") stays: it is public advice, and
   which models the maintainer runs is his own rule.

Size: about 40 lines of script changed, net fewer; about 15 lines of docs.

## Tests

All in `test_failed_tier_report.sh`, which runs the real script (`bash "$SCRIPT"`) with stub
`codex`, `ollama` and `curl` on `PATH`: the same entry point a session uses, through option
parsing, the model list check, auto-detect, dispatch and `report_round`.

Changed, in section 32b and the think-tag block, because their expected output encodes the old
fallback:

- `sfall`: Melious returns the real empty-balance reply (stub `nobalance`, from a raw file of
  2026-10-25). Expect `reviewers: codex OK, melious FAILED (error mid-stream (HTTP 200); quota/rate
  limit: wait or add credits)` with nothing after it, the gate line above, exit 0, and no
  `ollama-ran` mark.
- `sfirstsucc`: Codex fails, Melious refused: exit 4, no `ollama-ran` mark.
- `sboth`, `sreuse`, `ttpair`, `ttpair2`, `ttpair3`: rewritten to expect no ollama seat; `ttpair3`
  still exits 4.
- `sstop` tested stopping the ollama fallback started after Melious failed. That path is gone, so
  it becomes: stopping the script stops a Melious seat that ignores TERM (stub `stubborn`), while
  Codex is still running.

New:

- `snodetect`: `SECOND_SEAT=melious`, the existing `ollama` stub (its `list` shows a `:cloud` tag),
  which gains one line marking that `list` was called. Expect no `ollama list` call, no "auto-detected" or "auto-using" note
  on stderr, and no `ollama-ran` mark, for a run where Melious fails.
- `sseatnodetect`: the same stub with `--seat codex`: no `ollama list` call.
- The default still auto-detects: `incident` and most other runs leave `OLLAMA_MODEL` unset and
  get an `ollama-cloud` seat only because the tag was read from the stub's `ollama list`; a
  check that the "auto-detected" note prints is added beside them.

Each new check is broken on purpose once before the DIFF gate (restore the hand-over; restore
detection), to show it fails.

Live check after `make check`: one real run from the branch, with a Melious URL that cannot be
reached (`MELIOUS_BASE_URL=http://127.0.0.1:9`), `SECOND_SEAT=melious MELIOUS_MODEL=<the listed
any-depth model>`, a small diff, real Codex. Expect the gate line, exit 0, and no new ollama row
in the cost log. It costs one small Codex run.

## Follow-ups (not in this change)

- The maintainer's own instructions (`~/.claude/CLAUDE.md`, outside this repo): once merged, the
  stopgap of two `--seat` commands becomes one run with `SECOND_SEAT=melious` and the listed
  model, with no `OLLAMA_MODEL`. His to approve; a harness change.
- A session that forgets `SECOND_SEAT=melious` still gets the public default, and with it the
  auto-picked ollama model. Exporting `SECOND_SEAT` and `MELIOUS_MODEL` in his shell profile
  would close that for sessions (background shells skip the profile). His call; outside this
  repo.

## Cost

PLAN gate at Normal: about 2-3 rounds on Codex plus Melious. Build: about an hour of work, then a
Normal DIFF gate (it changes a review script's logic), likely 2-4 rounds. One small live Codex
run. No red team: it touches no server, user data, money or deletion.
