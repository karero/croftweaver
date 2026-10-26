# Plan: a Melious second seat that never hands over to ollama

One-page plan for `skills/independent-review/scripts/independent_review.sh`, its tests and its
docs. Written against origin/main `7c7d4073`, branch `plan/second-seat-no-fallback`. Nothing is
built before the maintainer's go.

## Status

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ▶ written | this file |
| 2 | PLAN gate (Normal: a plan for a review script's logic) | ▶ rounds 1-3 done: 4 BUG, 8 RISK, 16 NIT; all fixed in this revision but one NIT refuted | trail `REVIEW-plan-2026-10-26-second-seat-no-fallback.md` |
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

The cost, as counted from the cost log for the week to 2026-10-26 (counted in the session that
asked for this plan; not checked again here): 160 of 279 ollama stand-in runs failed, and Melious
failed 214 of 1230 runs, all for an empty balance. Until the script changes, sessions run
`--seat codex` and `--seat melious` as two commands with the same `--round`: it works, but it
doubles the commands, loses the shared summary line, and leans on every session remembering.

## Decision: `SECOND_SEAT=melious` stops falling back

Proposed: **`SECOND_SEAT=melious` means Codex plus Melious (plus Antigravity when opted in), and
no ollama.** A Melious seat that does not count is reported FAILED or SKIPPED, and no ollama call
is made or prepared. No new variable and no new value.

Why this shape rather than a new value (say `SECOND_SEAT=melious-only`) or a new switch:

- **The other order still exists.** `SECOND_SEAT=ollama` with `MELIOUS_MODEL` set is ollama first,
  Melious as its fallback, unchanged. The only combination this removes is Melious first with
  ollama behind it, which is exactly the one the rule forbids.
- **Fewer paths.** A new value keeps the fallback code, its tests and its docs, and adds a third
  mode beside them. Removing the fallback deletes code: the `wait "$melious_pid"` hand-over, the
  `OLLAMA_RAN` variable, and one `--first-success` step.
- **A forgotten flag cannot spend quota.** With a new value, a session that types the old
  `SECOND_SEAT=melious` gets the fallback back.

**The default stays as it is.** With `SECOND_SEAT` unset, the pair is still Codex plus the
auto-detected ollama `:cloud` model, with Melious as a fallback when `MELIOUS_MODEL` is set. That
is the setup a site owner gets from `croftweaver.zip` with no variables at all; the setup guide
leads with ollama for the second seat, so changing the default would cost a reviewer to anyone
who followed it (judgment: the toolkit collects no usage data). The maintainer's rule is his own
setup, carried by his own instructions (see "Follow-ups"), not the public default.

**Who loses what.** Anyone who set `SECOND_SEAT=melious` and relied on ollama behind it no longer
gets a stand-in when Melious fails: the round reports the seats that counted, and when Codex
counted alone the gate line below says why and what to do.
The release note says so. The seat arrived on 2026-10-06; we know of no user of it besides the
maintainer (judgment, not checked).

## Changes

1. **Dispatch** (lines 1827-1862). In the default parallel branch, with `SECOND_SEAT=melious`,
   start Codex and Melious (and Antigravity when opted in), wait for all, report each. Drop the
   hand-over, and remove `OLLAMA_RAN` entirely (its only reader, line 1860, is in the removed
   report branch) `melious_counted` (line 1779; its only caller is the removed hand-over) and `melious_pid`
   (line 1831; read only by that hand-over). In `--first-success` (line 1796), drop step 2b for this seat: Codex, then
   Melious, then Antigravity only if opted in. The default seat's own late start (Melious after
   ollama failed, lines 1847-1853) is unchanged.
2. **No auto-detect where ollama cannot run.** Today the detection block (lines 480-506) runs
   whenever `LOCAL_ONLY != 1` and `OLLAMA_MODEL` is empty. It becomes: those two, and also
   `SEAT = ollama`, or `SEAT` empty with `SECOND_SEAT = ollama`. So `--local-only` keeps no
   auto-detect (with or without `--seat ollama`), and `SECOND_SEAT=melious` or
   `--seat codex|melious|agy` never read `ollama list` or print its notes. (`SECOND_SEAT` is
   already set to `ollama` when unset, line 404, so the default keeps auto-detect.) The other readers of
   `OLLAMA_MODEL` are `run_ollama` and its transports (lines 1273-1420), which these runs never
   call; `OLLAMA_LABEL` (line 1764), which only names a seat that is reported; and the
   `--local-only` cloud-tag guard (line 513), unchanged. So an `OLLAMA_MODEL` left in the
   environment does nothing in those runs.
3. **The gate line.** `report_tier` keeps the Melious outcome in its own variable as it builds it
   (the same text it appends to `SUMMARY`), so nothing parses `SUMMARY`. In `report_round`,
   checked before the generic fewer-than-2 branch: when `SECOND_SEAT=melious`, no `--seat`, no
   `--first-success`, no `--local-only`, Melious did not count (FAILED or SKIPPED; in this mode
   it is always dispatched), and Codex is the only seat that counted, it prints on stdout and stderr, in place of the generic note:

   ```
   ⚠ PLAN round landed with 1 reviewer(s) counted toward the gate: codex alone. melious FAILED (error mid-stream (HTTP 200); quota/rate limit: wait or add credits); SECOND_SEAT=melious has no fallback. Record this round as Codex alone, with that reason, in the trail; to add the second seat, rerun with --seat melious and the same --round once it can run.
   ```

   The Melious part is the text `report_tier` built for that seat, FAILED or SKIPPED with its
   reason. Every other short round keeps today's notes: Codex failed and Melious counted, Antigravity the
   only one counted, nothing counted, and `--first-success` (which stops at Codex by design). The
   generic note names no ollama fallback ("Treat it as degraded … consider --with-antigravity or
   a manual paste round"), so it does not mislead about this seat; its Antigravity advice is
   stale when Antigravity already ran, as today on every seat (left as is). The `reviewers:` line is unchanged
   (`reviewers: codex OK, melious FAILED (…)`). Exit stays as now: 0 when any seat counted
   (Antigravity included), 4 when none did.
4. **Text in the script.** The header (lines 9-14), the `SECOND_SEAT` and `OLLAMA_MODEL` entries
   in the env list (lines 153-157, 171-174) and the no-reviewer help block (line 1883) say that
   Melious as the second seat has no fallback, and that auto-detect runs only when ollama can run.
5. **Skill docs**, in step with the script, changing only the sentences about
   `SECOND_SEAT=melious`: `SKILL.md` line 59 ("ollama standing in when it fails"),
   `references/setup-guide.md` lines 172-173 (including "an `OLLAMA_MODEL` for the fallback, or
   the first `:cloud` tag is used") and 328-329, `references/rationale.md` lines 72-73. Each
   becomes: Melious beside Codex, no fallback; a failed seat is not replaced, and the round reports
   whichever seats counted, named in the trail. Melious as the default seat's fallback (setup-guide lines 112 and 169-170, 315)
   stays as written. The skill names no model and still won't (`check_model_agnostic.sh`). The
   final-full-read advice ("another ollama cloud model") stays: it is public advice, and which
   models the maintainer runs is his own rule.

Size: about 40 lines of script changed, net fewer; about 15 lines of docs.

## Tests

All in `test_failed_tier_report.sh`, which runs the real script (`bash "$SCRIPT"`) with stub
`codex`, `ollama` and `curl` on `PATH`: the same entry point a session uses, through option
parsing, the model list check, auto-detect, dispatch and `report_round`.

**Every check that a hand-over is gone sets `OLLAMA_MODEL` to the stub's `:cloud` tag**
(`sfall`, `sfirstsucc`, `sboth`, `ttpair*`, `t11f`, `t12`, `sagy`). The harness unsets it
(line 342), and with auto-detect off a restored hand-over would call `run_ollama`, which returns 3
before touching the stub: the `ollama-ran` mark would never appear and the check could not fail.
With the model set, a restored hand-over runs the stub, and each check asserts both "no
`ollama-ran` mark" and the exact `reviewers:` line.

Changed, because their expected output encodes the old fallback (found by grepping the suite for
`stood in`, `stands in`, `hand over`, `fallback` and `ollama-cloud OK` under `SECOND_SEAT=melious`; the
build greps again). Comments that state the old behaviour are rewritten with their tests, such as
section 32b's lead ("A refused Melious seat must still hand over", line 1318):

- `sfall` (section 32b): Melious returns the real empty-balance reply (stub `nobalance`, from a
  raw file of 2026-10-25). Expect `reviewers: codex OK, melious FAILED (error mid-stream (HTTP
  200); quota/rate limit: wait or add credits)` with nothing after it, the gate line, exit 0, no
  `ollama-ran` mark.
- `sfirstsucc`: Codex fails, Melious returns 429: `reviewers: codex FAILED (exit 1), melious
  FAILED (HTTP 429; quota/rate limit: wait or add credits)`, exit 4, no `ollama-ran` mark.
- `sboth`: Codex OK, Melious returns 429: now the gate line, not "fewer than the 2".
- `sreuse` is dropped: it guarded a stale Melious OK holding the fallback back, and the fallback
  is gone.
- `ttpair`, `ttpair2`, `ttpair3` (think-tag block), and `t11f` (line 1894) and
  `t12` (line 1977) in the size-limit block: rewritten to expect no ollama seat and Codex alone
  where Codex counts; `ttpair3` still exits 4. `t11f` and `t12` keep their own point (the Melious
  refusal and its reason) and show the gate line with a setup reason, not a quota one.
- `sstop` tested stopping a fallback that starts late. That path stays on the default seat
  (Melious starting after ollama failed), so `sstop` moves there: `SECOND_SEAT` unset,
  `OLLAMA_STUB=429`, a Melious stub that ignores TERM (`stubborn`), which gains a "finished" mark
  written after its sleep. Stopping the script must exit 130, leave its pid dead, and leave no
  "finished" mark: a seat that ran to the end would write it.

New:

- `snodetect`: `SECOND_SEAT=melious` with `OLLAMA_MODEL` unset; the `ollama` stub gains one line
  that marks each `list` call. Melious fails. Expect no `list` mark and no "auto-detected" or
  "auto-using" note. (It cannot test the hand-over: with no model, `run_ollama` returns before
  the stub. The checks above do that.)
- `sseatnodetect`: the same with `--seat codex`: no `list` mark.
- `sseatollama`: `--seat ollama` with `OLLAMA_MODEL` unset (and `SECOND_SEAT=melious` in the
  environment): the `list` mark, and `ollama-cloud OK`. Change 2 makes detection depend on
  `--seat` for the first time, so this run must still find the model.
- `sfirstcodex`: `--first-success`, Codex OK: no gate line and no Melious call. It checks that
  the note stays out of a mode that stops early; it cannot catch a restored hand-over, which
  never runs when Codex counts.
- `sagy`: `WITH_ANTIGRAVITY=1`, Melious fails: with Codex and Antigravity both OK, no gate line
  (two counted) and exit 0; with Codex failing and Antigravity OK, the generic note and exit 0.
- The default still auto-detects: `SECOND_SEAT` unset, `OLLAMA_MODEL` unset; expect the `list`
  mark, the "auto-detected" note and `ollama-cloud OK`. The mark makes it fail if detection
  breaks, even if the note's wording changes.

Before the DIFF gate, each group of checks is broken on purpose once, with the mutation that
should catch it, and the PR records which checks failed for each:

| Mutation | Checks it must fail |
|----------|---------------------|
| restore the parallel hand-over | `sfall`, `sboth`, `ttpair*`, `t11f`, `t12`, `sagy` (first case) |
| restore the `--first-success` step 2b | `sfirstsucc` |
| detect again under `SECOND_SEAT=melious` and `--seat codex` | `snodetect`, `sseatnodetect` |
| detection keyed on `SECOND_SEAT` alone, ignoring `--seat` | `sseatollama` |
| stop detecting in the default | the default auto-detect check |
| drop the gate line | `sfall`, `sboth`, `t11f`, `t12` |
| print the gate line whatever the mode or count | `sfirstcodex`, `sagy` |
| remove the `kill -KILL` in `stop_tiers` | `sstop` |

Live check after `make check`: one real run from the branch, with a Melious URL nothing listens
on (`MELIOUS_BASE_URL=http://127.0.0.1:9`), `SECOND_SEAT=melious MELIOUS_MODEL=<the listed
any-depth model>`, a small diff, real Codex. Record the Melious FAILED reason, the exit status,
the gate line, and the cost-log rows the run added (expected: codex and melious, no ollama). It
costs one small Codex run.

## Follow-ups (not in this change)

- The maintainer's own instructions (`~/.claude/CLAUDE.md`, outside this repo): once merged, the
  stopgap of two `--seat` commands becomes one run with `SECOND_SEAT=melious` and the listed
  model, with no `OLLAMA_MODEL`. His to approve; a harness change.
- A session that forgets `SECOND_SEAT=melious` still gets the public default, and with it the
  auto-picked ollama model. Exporting `SECOND_SEAT` and `MELIOUS_MODEL` where his sessions'
  shells read them would close that; which startup file reaches every way a session runs the
  script is not checked here. His call; outside this repo.

## Cost

PLAN gate at Normal: about 2-3 rounds on Codex plus Melious. Build: about an hour of work, then a
Normal DIFF gate (it changes a review script's logic), likely 2-4 rounds. One small live Codex
run. No red team: it touches no server, user data, money or deletion.
