# Plan: keep GLM's review when it writes the marker twice; log why a seat failed

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-11-07 | this file |
| 2 | Plan review gate (Normal: a tooling fix, no red team) | 🔄 rounds 1–4 done; Daniel's go for the gate 2026-11-07 | `REVIEW-plan-2026-11-07-glm-marker-and-failed-reason.md` |
| 3 | Build, tests, DIFF gate, one pull request | ⬜ | — |
| 4 | `HARNESS-CHANGES.md` entry in `~/.claude` | ⬜ | — |

Raised by the session that fixed the refusal check (karero/croftweaver#476). Scope 3 was added by
Daniel on 2026-11-07 ("Same PR"), so the three fixes ship as one pull request.

## 1. GLM's marker written twice

**What happens.** The melious seat asks for a line `=== FINAL REVIEW <hex> ===` before the final
answer. `perl/melious_stream.pl` keeps what follows the LAST marker line with "findings after it",
where findings means the words BUG, RISK or NIT anywhere in the text (line 112). In two runs GLM
5.3 wrote the marker at the top, then the review, then the marker again and a one-line summary
such as "(Findings above: 1 BUG, 5 RISK, 6 NIT; …)". The summary holds the words, so the second
marker wins, the review is cut away, and `looks_like_review` rejects the summary: "output is not a
review". How many of the cost log's other melious FAILED lines are this fault is not known; step 2
is what lets that be counted from now on.

**Evidence, re-run 2026-11-07.** Two live runs, kept in the shared notes folder
(`glm-double-marker-captures/independent-review.{ctiPcY,hsNCTK}`):

| Run | Reply (`melious.full`) | Markers at | Section kept today | Review check |
|-----|------|------|------|------|
| ctiPcY, 2026-11-06 | 10,002 bytes | lines 1 and 31 | 335 bytes: the dropped-text note and the summary | reject |
| hsNCTK, 2026-11-07 | 7,203 bytes | lines 1 and 28 | 643 bytes: the same | reject |

Running today's `melious_stream.pl` on each `melious.resp` gives a section byte-identical to that
run's `melious.out`, so the fault is reproduced and is in the reader, not the model's transport.

**Fix.** A marker counts as having findings after it only when a line after it is one the review
check would also count as a finding. That check is `finding_count` in `looks_like_review`
(`independent_review.sh:1102`): grep `'^[[:space:]]*([#*-]|[0-9]+\.).*\b(BUG|RISK|NIT)\b'` with
`-i`. The reader does not copy that pattern, because it matches the DECODED reply, where Perl's
whitespace, word and case rules are Unicode's and grep's are not: rounds 2–4 found three ways the
copy counted a line the grep does not (form feed, NEL, `RIſK` / the Kelvin sign), each making a
marker usable whose section the check then rejects. So line 112 becomes a strict rule that counts a
line only in a shape the grep surely counts too:

`my $findings = qr/^[ \t\f\x0B\r]*(?:[#*-]|[0-9]+\.)[\t\x20-\x7E]*?(?<![A-Za-z0-9_])(?aai:BUG|RISK|NIT)(?![A-Za-z0-9_\x{80}-\x{10FFFF}])|No BUG\/RISK\/NIT findings/m;`

In words: ASCII whitespace, then `#`, `*`, `-` or a number and a dot, then printable ASCII only, up
to the label BUG, RISK or NIT in ASCII letters, any case, with no ASCII word character before it
and neither a word character nor any non-ASCII character after it. Each piece is ASCII and is
inside what the grep takes, so the reader never counts a line the check does not. The clean
verdict "No BUG/RISK/NIT findings" still counts anywhere, as now.

What the strict rule does not count, the grep may: a finding-shaped line with a non-ASCII character
before its label ("1. Dash guard — codex BUG …"). On the decoded text of every `codex.out`,
`melious.out`, `ollama.out` and `melious.full` under `$TMPDIR` (1,786 files), the rule counts no
line the grep does not, and misses 970 lines the grep counts, in 609 files; the ones sampled are
prose that names a label after a dash or a curly quote. That costs nothing in practice: replaying
every real `melious.resp` there through the reader with its run's own marker (525 runs), the
section is byte-identical to round 3's regex in every run; the 19 runs whose prompt holds more
than one marker give the same section under each of them (42 run and marker pairs). Had it mattered, the
loss goes the loud way: the walk tries the earlier markers, and only when none qualifies is the
reply kept whole with the no-marker warning.

So a summary line that does not start like a finding ("(Findings above: …", "The findings above
…", "BUG: 1, RISK: 5") cannot make a marker usable. The walk from the last marker, the quote skips
and the notes stay as they are. On both captures, with only that line changed, the reader keeps
everything after the first marker (9,973 and 7,174 bytes: a lead-in line and the findings in
ctiPcY, the findings at once in hsNCTK) and `looks_like_review` accepts it. The second marker and
the summary stay at the end of the section; nothing strips them. With that line changed in this
worktree, `test_failed_tier_report.sh` passed all 696 checks, the same count as on `origin/main`
(`2275e756`).


**What it gives up.** A reply whose findings are in no line the strict rule counts (a table, a
bare `RISK 1 — …`, a `> - NIT` quote, a label after a non-ASCII character) no longer makes its
marker usable. The walk then tries the earlier markers; when none qualifies, the reply is kept
whole with the no-marker warning, as any reply without a usable marker is today, and the review
check decides. **Still wrong after
the fix:** a summary after the second marker that does start like a finding ("- Totals: 1 BUG, 5
RISK") makes that marker usable again. The section is then the reader's note ("the marker came 2
times …, so check that the section starts with the review") and the summary, and the review check
ACCEPTS it: one finding line, no refusal. The seat counts as OK on a summary, and the note is the
only warning. Today's code does the same with that reply. Not seen; the build pins it as a KNOWN
WRONG test case.

**Rejected.** Taking the FIRST usable marker: a leaked trace can restate the ask, marker and all,
before the real one (#165, cases `leak` and `echoglued` in `test_failed_tier_report.sh`).
Choosing the marker with the most finding lines after it: more code for a case not seen.

## 2. A FAILED seat logs no reason

**What happens.** `log_seat` in `independent_review.sh` cuts the outcome at its first " (" before
calling `review_log.sh add --outcome`, so "FAILED (output is not a review)", a quota failure
("FAILED (<why>; quota/rate limit: …)") and a seat over its size limit are all logged as `FAILED`.
The cost log holds 1,348 FAILED lines (1,030 of them melious) and cannot say which were false
rejects.

**Fix.** A 17th column, `reason`: the text inside the outcome's outer parentheses, word for word
as the round's summary line shows it, spaces kept. In `log_seat` that is everything after the
first " (" with the final ")" cut, so inner parentheses stay whole. Every FAILED outcome
`report_tier` builds has them (`independent_review.sh:1712–1733`), the size limit's included:
"FAILED (a prompt of N bytes, over the … this seat took whole (seat_limits.txt); nothing was
sent)"; so does NOT COUNTED (line 1693). The outcome's `tr ' ' '-'` is not applied to the reason; `review_log.sh`'s `clean()` still turns tabs, newlines and carriage returns into spaces. `-`
for an outcome with no parentheses (OK). `review_log.sh add` takes `--reason`; `log_seat` passes
it. Column 13 is written as today, so `summary`'s OK count is unchanged (11 older lines hold a
lowercase `ok`, which it does not count, as now). `HEADER` gains
`reason`, so a new log names the column; an existing log keeps the header it was started with, as
it did when columns 15 and 16 came. Older lines have no column 17: awk reads it as empty, so the
usage text's counting command maps empty to `-`:
`awk -F'\t' '$13=="FAILED"{print ($17=="" ? "-" : $17)}' runs.tsv | sort | uniq -c`. No new report.

## 3. `codex_tokens()` reads a quoted count, not Codex's own

`codex_tokens()` takes the first line starting "tokens used" in `codex.err` and reads a number
from that line or the next. Codex echoes what it read into that file, so a quoted line can come
first. In `status-line-gate-r3-raw/codex.err` (shared notes folder), line 317 is a quoted
`tokens used: 59,960`, and Codex's own count, 72,315, is at lines 2904–2905. That gate's three
Codex rows are all logged at 59,960; their footers say 85,286, 55,115 and 72,315.

**Codex's own footer, surveyed 2026-11-07** over the 698 run folders in `$TMPDIR` with a
`codex.err`: 691 hold exactly one line that is `tokens used` alone followed by a line of only
digits and commas, the `tokens used` line always among the file's last three; the other 7 hold
none. Two of the 691 end with a Codex `ERROR … failed to record rollout items` line after the
footer. No file's last five lines hold a count on the `tokens used` line itself.

**Fix.** Read the LAST `tokens used` line that is alone on its line and whose next line holds only
digits and commas; nothing else counts, so a quoted `tokens used: N` never does. No such pair: no
figure, as now. Against today's code on the same 698 folders, this changes exactly the three
quoted-count runs above and keeps every other figure. Still wrong after the fix: a quoted bare
pair logs the quote when it comes after Codex's footer, or when the run has no footer. Not seen:
in every file the footer is within the last three lines.

## How it is tested

Captures: committed under `scripts/fixtures/`, named for the tool, model and date, trimmed by
cutting whole lines only (the reviews are about private plans; lines that name private code are
cut). The cut keeps, in order: the first marker, the first finding line, at least one more finding
line, the closing marker and the summary line. The real hex marker stays in the file. The codex
capture keeps the quoted line at 317 and the footer pair. Expected values are written by hand.

| Id | Given | When | Then |
|----|-------|------|------|
| T1 | the trimmed ctiPcY reply, as an SSE stream, with its own hex marker | `melious_stream.pl` reads it, given that marker | exit 0; the section's first non-blank line is the capture's first line after its first marker; its first finding line and its summary line are in it; neither the "marker came 2 times" note, the dropped-text note nor the no-marker warning is in it |
| T2 | the same for hsNCTK | the same | the same, with that capture's lines |
| T3 | the T1 reply served by the curl stub, its hex marker replaced at serve time by the marker the run asked for | `independent_review.sh` with `SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3` (the pair as REVIEW-RULES.md runs it) | the summary reads `melious OK`; the section holds the first finding line; no no-marker warning |
| T4 | two markers, two finding lines between them, then a closing summary that starts like a finding (`- Totals: 1 BUG, 1 RISK`) | `melious_stream.pl` | labelled KNOWN WRONG: exit 0; the section is the note "(text before the final-review marker dropped, … the marker came 2 times …)", a blank line and the summary; neither finding line is in it |
| T5 | the existing marker cases (`leak`, `markdup`, `markfence`, `markwrap`, `glued`, `echoglued`, `fencequote`, `afterfence`, `topecho`, `quotemark`, `oldmark`, `markend`, …), all in `test_failed_tier_report.sh` | the suite runs | all pass unchanged |
| T6 | a stub reply the review check rejects, and an empty log | `independent_review.sh`, with `REVIEW_LOG` set | the new log's header ends in `cut` then `reason`; that seat's line has `FAILED` in column 13 and `output is not a review` in column 17 |
| T7 | the existing `costfail` case (ollama 429), and the size-limit case `t11c` (codex over its limit) | the same | column 17 holds the reason each summary line shows, spaces kept; for `t11c`, its inner `(seat_limits.txt)` and the closing "nothing was sent" included |
| T8 | an OK seat | the same | column 17 is `-`; `summary`'s ok count is what it was |
| T9 | `test_round_checks.sh:330` (an old 14-column log: `add` appends a 16-field line) | the suite runs | changed to 17 fields, column 17 `-`; the old header still kept |
| T10 | the trimmed r3 `codex.err` | `codex_tokens` | prints 72315 |
| T11 | the same with the footer removed | `codex_tokens` | prints nothing |
| T12 | a real `codex.err` whose footer is followed by the rollout ERROR line | `codex_tokens` | prints that footer's number, written by hand |
| T13 | `independent_review.sh` | a check in `test_round_checks.sh` lists every `outcome="` assignment | each one but `OK` holds " (", so no outcome can reach `log_seat` without a reason; a new branch without one fails the suite |
| T14 | two real findings, a second marker, then a footer led by NEL, by a no-break space, or naming `RIſK` or `RIS` + Kelvin sign, each served by the curl stub with the run's own marker | `independent_review.sh` with the melious seat | `melious OK`; both findings in the section, every case |

Mutation check (the `mutation-check` skill): revert the regex and T1–T3 must fail; put back round 3's regex (`(?i:.*\b(?:BUG|RISK|NIT)\b)` after the ASCII class) and T14's `RIſK` and Kelvin cases must fail; drop
`--reason` from `log_seat` and T6–T7 must fail; restore the first-match read in `codex_tokens` and
T10 must fail.

The repo's own checks (`test_failed_tier_report.sh`, `test_looks_like_review.sh`,
`test_round_checks.sh`, `test_base_check.sh`, `test_sweep_claims.sh`) run before each review round
and after the last edit.
