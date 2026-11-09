# Plan: `review_log.sh add` checks what it logs

Status: plan, 2026-11-09. Not built. The owner's go on the verdict was "Start it", as a small fix.

PLAN gate: skipped as a fix that restores intended behaviour (the log should hold one run's
round, seconds and tokens in their own columns). It goes straight to a DIFF review at Normal.

## What

`skills/independent-review/scripts/review_log.sh add` refuses a value it cannot log correctly,
and says what it logged. `summary` counts the `ok` rows already in the log as OK. This closes
the BUGLOG row of 2026-11-07 on `add` and `summary`.

## Why

`add` checks no value and prints nothing on success. In the local log (about 13,600 rows on
2026-11-09), 10 rows are malformed. All are `fresh-eyes` rows, logged by hand, from three gates
(2026-10-14, 11-02 and 11-09). Each time the host ran, in zsh (the Bash tool's shell):

    for r in "1 263 192375" ...; do set -- $r; review_log.sh add ... --round $1 --seconds $2 --tokens $3; done

zsh does not split `$r`, so `$1` held all three numbers and `$2`, `$3` were empty and vanished.
`--seconds` then took `--tokens` as its value. The rows read round `1 263 192375`, seconds
`--tokens`, tokens `-`. About 1.62 million reviewer tokens never reached a token column, so
those gates' running totals read low, with no warning. In one gate the numbers went in as
tokens first, seconds second, which no check on the shape of a number can catch.

The same function took a lowercase `ok` on 11 rows and `done` on 4. `summary` counts only `OK`.

## How

1. **Check before writing.** After the arguments are read and before anything is written, `add`
   refuses with exit 2, a message on stderr naming the flag and the value, and no line written:
   - `--round`, `--seconds`, `--tokens`: anything but digits, `-` or empty. This refuses
     `1 263 192375`, `--tokens`, `12,000`, `1.5` and `-5`.
   - `--outcome`: anything but `OK`, `FAILED` or `NOT-COUNTED` (the three the script logs; a
     skipped seat is never logged). This refuses `ok` and `done`.
   - any flag's value that starts with `--`: it is almost always the next flag, taken because a
     variable was empty. No reason the script logs starts with `-` (checked: its failure texts,
     and the reason column of every row in the log).

   The message for a `--` value says why it happens: an empty variable, or one zsh did not split.
2. **Say what was logged.** After a line is written, `add` prints one line on stdout, such as
   `logged: round 1, fresh-eyes, 263 s, 192375 tokens, OK, gate <id>`, with `-` for a value not
   given. Labelled fields, not the raw line: they show seconds and tokens swapped. With
   `REVIEW_LOG=off` it prints `not logged: REVIEW_LOG=off`. A failed write keeps its warning.
3. **The script's own calls stay quiet.** `log_seat` in `independent_review.sh` sends `add`'s
   stdout to `/dev/null`, because the script's stdout is the review the host reads. Its stderr
   stays, so a refused value from the script would still show. The values it passes are already
   checked: round 1 to 99 or empty, seconds from shell arithmetic or empty, tokens digits only or
   empty, outcome one of the three. Its exit status is already ignored, so a refusal never fails a
   review.
4. **`summary` counts `ok` as `OK`.** `$13 == "OK" || $13 == "ok"`. Only old rows can be `ok` once
   step 1 is in. The 4 `done` rows stay uncounted: nobody said what they meant.
5. **Old rows stay as they are.** The log is append-only by design (its header comment), and the
   readers already treat a value that is not a number as none. Rewriting the file by script would
   risk every other row to repair 10. The three gates have ended.
6. **Words.** The usage comment at the top of `review_log.sh` lists the accepted values, and its
   line "A failure to log warns and exits 0" becomes: a bad value exits 2 and writes nothing; a
   failure to write warns and exits 0. The BUGLOG row of 2026-11-07 is marked fixed by the PR. The
   PR body carries a release-note line.

Not changed: `SKILL.md` (an open PR edits it; its documented call already passes valid values),
the `gate` and `round-check` readers, and `--gate` and `--depth` (every row holds a documented
value or `-`: checked).

## How it is tested

In `test_failed_tier_report.sh`, section 27, beside the existing `add` and `summary` cases. Every
case calls `bash review_log.sh add` as a host does; each checks the exit status, stderr, and the
log's line count before and after.

- The measured case, as zsh hands it over: `--round "1 263 192375" --seconds --tokens`. Exit 2,
  no line written.
- The same loop run through `zsh -c`, when zsh is on PATH. Without zsh the test prints a `SKIP`
  line for that case and goes on (not checked: whether the CI image has zsh; the PR says which).
- Each numeric flag: `abc`, `1.5`, `12,000`, `-5` and a `--` value refused; empty, `-`, `0` and
  `263` written.
- `--outcome`: `ok`, `done` and `Ok` refused; `OK`, `FAILED` and `NOT-COUNTED` written.
- A text flag given the next flag (`--model --seconds 5`): refused.
- Success prints the labelled line with the values given; `REVIEW_LOG=off` prints `not logged`.
- `summary` on a log with `OK`, `ok` and `done` rows written by hand: the OK column counts two of
  three.
- Through production's entry point: the existing section 27 runs `independent_review.sh` with
  stub seats and checks each seat's line. Add: its stdout holds no `logged:` line, and its stderr
  no refusal, for an OK seat, a FAILED seat, and a run with no `--round` or `--depth`.

Before the review, each guard is reverted alone (`mutation-check`) and must fail at least one test.

## Review and cost

DIFF gate at Normal with the pair (Codex and GLM 5.3): a guard script is never Light. Since
2026-10-15, Normal gates averaged 2.8 rounds, and a round of the pair about 77k tokens (Codex 53k,
GLM 24k), so about 230k tokens. Then the owner's merge go.
