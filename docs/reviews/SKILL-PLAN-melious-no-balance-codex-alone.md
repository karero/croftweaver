# Plan: independent-review — an empty Melious balance means Codex alone, no rerun owed

Base `origin/main` 58e95764 · branch `claude/modest-mestorf-e9719b` · review depth: Normal (a
review script's logic and the docs that describe it; nothing in the High row) · red team: none
(no server, user data, login, money, deletion or schema).

| Step | What | State | Evidence |
|---|---|---|---|
| 1 | Script names an empty balance and says: Codex alone, no rerun owed | planned | — |
| 2 | Tests read a real capture of the balance error | planned | — |
| 3 | setup-guide, `~/.claude/CLAUDE.md`, `HARNESS-CHANGES.md` say the same | planned | — |
| 4 | `make check`, then the DIFF gate at Normal | planned | — |

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
"says so and why"; it stays as is. `~/.claude/HARNESS.md` has no rerun advice; it stays as is.

## The real error (checked 2026-10-27)

A run this morning (raw folder `independent-review.0QIYcq`) got HTTP 200 and one stream chunk:

    data: {"type":"error","error":{"message":"Insufficient balance for request. Required: 113, Available: 0","type":"billing_error","param":null,"code":"billing_insufficient_balance"}}

`melious_stream.pl` wrote `Error: HTTP 200: Insufficient balance for request. Required: 113,
Available: 0` to `melious.err`, and the seat's WHY was `error mid-stream (HTTP 200)`. Today
`report_tier` reads that line as quota (`QUOTA_RE`), so the summary says `melious FAILED (error
mid-stream (HTTP 200); quota/rate limit: wait or add credits)`.

## How

1. **`report_tier`**: inside the existing quota branch, when the seat is melious and the
   error-shaped lines match `insufficient[ _]balance` (case-insensitive), set
   `MELIOUS_NO_BALANCE=1`, make the outcome `FAILED (<why>; out of balance)` and the reason "the
   Melious balance is empty. By the owner's rule (2026-10-27) no rerun of this seat is owed: if
   Codex counted in this round, the round stands on Codex alone; record that in the trail." Only
   the error-shaped lines are read, as for quota today, so text in the reviewed artifact cannot set
   it. A 429 or any other quota text keeps today's wording.
2. **`report_round`, `SECOND_SEAT=melious` branch** (Codex OK, Melious not): when
   `MELIOUS_NO_BALANCE=1`, the note becomes "⚠ <GATE> round landed with 1 reviewer(s) counted
   toward the gate: codex alone. melious out of balance. By the owner's rule (2026-10-27) Codex
   alone is enough for this round: no rerun of melious is owed. Record it in the trail as Codex
   alone, melious out of balance." Any other Melious failure keeps today's note and rerun advice.
3. **`--seat melious` run that fails for balance**: `report_round`'s `--seat` note becomes "melious
   out of balance; no rerun owed (owner's rule, 2026-10-27). If Codex counted in this round, the
   round stands on Codex alone: record that in the trail. If this run was the round's only seat
   (a wording pass), run it with --seat codex." The no-success block then prints that it was a
   balance failure and skips the "paste the prompt below" text and the paste prompt. Exit stays 4:
   this run counted no reviewer, and callers read a non-zero exit as "no review here".
4. **Not changed**: the cost log. Its "1 run gave no figure" is true (a failed seat reports no
   tokens) and the outcome column still reads `FAILED`. The pair's `--first-success` mode never
   runs Melious once Codex counts, so it needs nothing. The `SECOND_SEAT=ollama` fallback gets the
   new outcome text from step 1 but keeps its own note.

Ordinary cases only (CLAUDE.md, Writing code rule 1): the one input added is the provider's own
balance message, which real runs produce several times a day while the balance is empty.

## How it is tested

All through the script's real entry (`bash independent_review.sh <diff>` with the existing curl
stub), in `test_failed_tier_report.sh`:

- **Real capture.** Commit this morning's `melious.resp` unedited (182 bytes, no key, no personal
  data) as `skills/independent-review/scripts/fixtures/melious-api_2026-10-27_insufficient-balance.sse`.
  The stub's `nobalance` case copies that file instead of its hand-typed copy of the 2026-10-25
  chunk. Expected strings are written by hand.
- **sfall** (pair, balance): reviewers line ends `melious FAILED (error mid-stream (HTTP 200); out
  of balance)`; the gate note holds "no rerun of melious is owed" and lacks "rerun with --seat
  melious"; exit 0.
- **New, sfall429** (pair, Melious 429): keeps "quota/rate limit" and the rerun advice, so the new
  wording cannot spread to every quota failure.
- **New, sseatbal** (`--seat melious`, balance): output holds "no rerun owed" and lacks "paste the
  prompt below" and the prompt's first line; exit 4.
- **mnobalance** (the ollama-fallback path): expectation updated to the new outcome text.
- **Mutation check** (`mutation-check` skill), before round 1: drop the `insufficient[ _]balance`
  test from step 1, and separately drop step 3's skip of the paste text; each must fail a test.
- `make check` green before each review round.

## Docs

- `references/setup-guide.md` lines 174–177: "When the balance is empty, Codex alone is enough for
  the round and no rerun is owed (the owner's rule, 2026-10-27); for any other failure, once the
  seat can run, rerun …" (the rest kept).
- `~/.claude/CLAUDE.md`, Review before merge: replace "If it FAILED for balance, its energy refills
  within hours: rerun … or go on with Codex alone and say so." with "If it FAILED for balance,
  Codex alone is enough for that round: say so in the trail; no rerun of melious is owed (Daniel,
  2026-10-27)." Outside the repo; not part of the PR.
- `~/.claude/HARNESS-CHANGES.md`: one entry naming the PR and the CLAUDE.md change.
