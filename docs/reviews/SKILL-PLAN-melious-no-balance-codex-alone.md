# Plan: independent-review — an empty Melious balance means Codex alone, no rerun owed

Base `origin/main` 58e95764 · branch `claude/modest-mestorf-e9719b` · review depth: Normal (a
review script's logic and the docs that describe it; nothing in the High row) · red team: none
(no server, user data, login, money, deletion or schema).

| Step | What | State | Evidence |
|---|---|---|---|
| 1 | Script names an empty balance (by the provider's error code) and says: Codex alone, no rerun owed | built, after the owner's go (2026-10-27, "Yes, build it as planned") | `d55ad455` |
| 2 | Tests read a real capture of the balance error | built; mutations (a), (a2), (b), (c) all killed | `d55ad455` |
| 3 | SKILL.md, setup-guide, `~/.claude/CLAUDE.md`, `HARNESS-CHANGES.md` say the same | done (the last two outside the repo) | `d55ad455` |
| 4 | `make check`, then the DIFF gate at Normal | done: `make check` green at `9d8e5dc0`; DIFF gate CLEAN (1 round, 1 RISK re-sorted as rare) | `docs/reviews/REVIEW-diff-2026-10-27-melious-no-balance.md` |

## What and why

The owner's rule, 2026-10-27, after a Normal round whose Melious seat failed for balance: "No need
for a 2nd reviewer ... that should be in the harness." So when the Melious seat fails because its
balance is empty, Codex alone is enough for that round, and no rerun of Melious is owed later.

Today the script and the docs say the opposite. With `SECOND_SEAT=melious`, a balance failure ends
the round with "once melious can run, rerun with --seat melious and the same --round"
(`independent_review.sh` line 1739). A `--seat melious` run that fails the same way ends with "No
automated reviewer available/succeeded … paste the prompt below into any strong model" and the
whole paste prompt (lines 1882–1903). `~/.claude/CLAUDE.md` (Review before merge) says "its energy
refills within hours: rerun … --seat melious then", and `references/setup-guide.md` lines 174–177
say "once the seat can run, rerun `--seat melious`". `SKILL.md` (lines 58–60) only says the round
"says so and why"; that stays, and one sentence goes under "The standard pair (1 + 2)" (lines
70–71): an empty Melious balance is the owner's standing choice, so that round counts on Codex
alone and no rerun is owed (round 1, Codex: otherwise SKILL.md still calls it degraded). `~/.claude/HARNESS.md` has no rerun advice; it stays as is.

## The real error (checked 2026-10-27)

A run this morning (raw folder `independent-review.0QIYcq`) got HTTP 200 and one stream chunk:

    data: {"type":"error","error":{"message":"Insufficient balance for request. Required: 113, Available: 0","type":"billing_error","param":null,"code":"billing_insufficient_balance"}}

`melious_stream.pl` wrote `Error: HTTP 200: Insufficient balance for request. Required: 113,
Available: 0` to `melious.err`, and the seat's WHY was `error mid-stream (HTTP 200)`. Today
`report_tier` reads that line as quota (`QUOTA_RE`), so the summary says `melious FAILED (error
mid-stream (HTTP 200); quota/rate limit: wait or add credits)`.

## How

1. **`perl/melious_stream.pl`**: at the mid-stream error chunk (today exit 6), when `error` is an
   object whose `code` is the string `billing_insufficient_balance`, print the same `Error:` line
   and exit with a new status 10. The decision reads the provider's structured code field, never
   the message text, so a reviewed artifact quoting "Insufficient balance" cannot set it (round 1,
   Codex). Every other error chunk keeps exit 6, and the non-stream error paths (exit 2, 9) are
   unchanged: no capture shows a balance error there.
2. **`run_melious`**: exit 10 gives `WHY="out of balance (HTTP $code)"`.
3. **`report_tier`**: a new branch, before the quota branch, for the melious seat whose WHY starts
   `out of balance`: it sets `MELIOUS_NO_BALANCE=1` (initialised to 0 with `CODEX_OUTCOME`, since
   the script runs under `set -u`; round 1, Codex) and the outcome `FAILED (out of balance (HTTP
   200))`. Its reason depends on how Melious ran:
   - with `SECOND_SEAT=melious` or `--seat melious`: "the Melious balance is empty. By the owner's
     rule (2026-10-27) no rerun of this seat is owed: if Codex counted in this round, the round
     stands on Codex alone; record that in the trail."
   - as the ollama seat's fallback (`SECOND_SEAT=ollama`): "the Melious balance is empty: add
     credits, or wait for the subscription to refill." That mode keeps today's degraded note: the
     owner's rule is about Melious as the second seat, and ollama no longer stands in by his rule
     of 2026-10-26 (round 1, Codex: the two must not contradict).
4. **`report_round`, `SECOND_SEAT=melious` branch** (Codex OK, Melious not): when
   `MELIOUS_NO_BALANCE=1`, the note becomes "⚠ <GATE> round landed with 1 reviewer(s) counted
   toward the gate: codex alone. melious out of balance. By the owner's rule (2026-10-27) Codex
   alone is enough for this round: no rerun of melious is owed. Record it in the trail as Codex
   alone, melious out of balance." Any other Melious failure keeps today's note and rerun advice.
5. **A `--seat melious` run that fails for balance**: `report_round`'s `--seat` note becomes
   "melious out of balance; no rerun owed (owner's rule, 2026-10-27). If Codex counted in this
   round, the round stands on Codex alone: record that in the trail. If this run was the round's
   only seat (a wording pass), run it with --seat codex." The no-success block then says it was a
   balance failure and skips the "paste the prompt below" text and the paste prompt. Exit stays 4:
   this run counted no reviewer, and callers read a non-zero exit as "no review here".
6. **Not changed**: the cost log. Its "1 run gave no figure" is true (a failed seat reports no
   tokens) and the outcome column still reads `FAILED`. The pair's `--first-success` mode never
   runs Melious once Codex counts, so it needs nothing.

Ordinary cases only (CLAUDE.md, Writing code rule 1): the one input added is the provider's own
balance error, which real runs produced on 2026-10-25, 26 and 27 (raw folders kept in the
maintainer's temp folder).

## How it is tested

All through the script's real entry (`bash independent_review.sh <diff>` with the existing curl
stub), in `test_failed_tier_report.sh`:

- **Real capture.** Commit this morning's `melious.resp` unedited (182 bytes, no key, no personal
  data) as `skills/independent-review/scripts/fixtures/melious-api_2026-10-27_insufficient-balance.sse`.
  The stub's `nobalance` case copies that file instead of its hand-typed copy of the 2026-10-25
  chunk. Expected strings are written by hand.
- **sfall** (pair, balance): reviewers line ends `melious FAILED (out of balance (HTTP 200))`; the gate note holds "no rerun of melious is owed" and lacks "rerun with --seat
  melious"; exit 0.
- **New, sfall429** (pair, Melious 429): keeps "quota/rate limit" and the rerun advice, so the new
  wording cannot spread to every quota failure.
- **New, sseatbal** (`--seat melious`, balance): output holds "no rerun owed" and lacks "paste the
  prompt below" and the prompt's first line; exit 4.
- **mnobalance** (the ollama-fallback path): expectation updated to the new outcome text; it
  lacks "no rerun" and keeps the degraded note.
- **New, mechoed** (pair, a mid-stream error chunk whose message reads "Insufficient balance" but
  whose code is another value): stays `error mid-stream (HTTP 200); quota/rate limit` with the
  rerun advice, so only the structured code grants the rule.
- **New, mcodeonly** (pair, the code `billing_insufficient_balance` with an unrelated message):
  gives `out of balance (HTTP 200)` and the no-rerun note, so a change to the provider's wording
  cannot bring the rerun advice back (round 2, Codex).
- **Mutation check** (`mutation-check` skill), before the DIFF gate: (a) step 1 matches the
  message text instead of the code, (a2) step 1 requires the message text as well as the code, (b) step 3 ignores how Melious ran, (c) step 5 keeps the
  paste text; each must fail a test.
- `make check` green before each review round.

## Docs

- `references/setup-guide.md` lines 174–177: "When the balance is empty, Codex alone is enough for
  the round and no rerun is owed (the owner's rule, 2026-10-27); for any other failure, once the
  seat can run, rerun …" (the rest kept).
- `~/.claude/CLAUDE.md`, Review before merge: replace "If it FAILED for balance, its energy refills
  within hours: rerun … or go on with Codex alone and say so." with "If it FAILED for balance,
  Codex alone is enough for that round: say so in the trail; no rerun of melious is owed (the owner,
  2026-10-27)." Outside the repo; not part of the PR.
- `~/.claude/HARNESS-CHANGES.md`: one entry naming the PR and the CLAUDE.md change.
