# Plan: keep GLM's review when it writes the marker twice; log why a seat failed

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-11-07 | this file |
| 2 | Plan review gate (Normal: a tooling fix, no red team) | 🔄 Daniel's go 2026-11-07 | — |
| 3 | Build, tests, DIFF gate, one pull request | ⬜ | — |
| 4 | `HARNESS-CHANGES.md` entry in `~/.claude` | ⬜ | — |

Raised by the session that fixed the refusal check (karero/croftweaver#476). Scope 3 was added by
Daniel on 2026-11-07 ("Same PR"), so the three fixes ship as one pull request.

## 1. GLM's marker written twice

**What happens.** The melious seat asks for a line `=== FINAL REVIEW <hex> ===` before the final
answer. `perl/melious_stream.pl` keeps what follows the LAST marker line with "findings after it",
where findings means the words BUG, RISK or NIT anywhere in the text (line 112). GLM 5.3 has
started writing the marker at the top, then the review, then the marker again and a one-line
summary such as "(Findings above: 1 BUG, 5 RISK, 6 NIT; …)". The summary holds the words, so the
second marker wins, the review is cut away, and `looks_like_review` rejects the summary:
"output is not a review".

**Evidence, re-run 2026-11-07.** Two live runs, kept in the shared notes folder
(`glm-double-marker-captures/independent-review.{ctiPcY,hsNCTK}`):

| Run | Reply (`melious.full`) | Markers at | Section kept today | Review check |
|-----|------|------|------|------|
| ctiPcY, 2026-11-06 | 10,002 bytes | lines 1 and 31 | 335 bytes: the dropped-text note and the summary | reject |
| hsNCTK, 2026-11-07 | 7,203 bytes | lines 1 and 28 | 643 bytes: the same | reject |

Running today's `melious_stream.pl` on each `melious.resp` gives a section byte-identical to that
run's `melious.out`, so the fault is reproduced and is in the reader, not the model's transport.

**Fix.** A marker counts as having findings after it only when a line after it starts with a
finding: `BUG`, `RISK` or `NIT`, after optional quote, heading, list or bold markup, the shape
PROMPT_CORE asks for ("each on its own line starting '- BUG' …"); or the clean verdict
"No BUG/RISK/NIT findings" anywhere, as now. One regex changes (line 112); the walk from the last
marker, the quote skips and the notes stay as they are. On both captures, with only that line
changed, the reader keeps everything after the first marker (9,973 and 7,174 bytes: a heading line and the findings in ctiPcY, the findings at once in hsNCTK)
and `looks_like_review` accepts it. The second marker and the summary stay at the end of the
section; nothing strips them. With that line changed in this worktree, `test_failed_tier_report.sh`
passed all 696 checks, the same count as on `origin/main` (`2275e756`), the marker
cases (`mleak` to `mmarkend`) among them.

**What it gives up.** A review whose findings sit only in a table (`| BUG | … |`) or only in prose
no longer makes its marker usable: the reply is then kept whole with the no-marker warning, as
any reply without a usable marker is today, and the review check decides. How often a seat answers that way was not checked;
PROMPT_CORE asks for line-start findings. Still wrong after the fix: a second marker followed by a
repeat of the finding lines keeps the repeat, which is a review all the same.

**Rejected.** Taking the FIRST usable marker: a leaked trace can restate the ask, marker and all,
before the real one (#165, cases `mleak` and `mechoglued`). Choosing the marker with the most
finding lines after it: more code for a case not seen.

## 2. A FAILED seat logs no reason

**What happens.** `log_seat` in `independent_review.sh` cuts the outcome at its first " (" before
calling `review_log.sh add --outcome`, so "FAILED (output is not a review)", a quota failure ("FAILED (<why>; quota/rate limit: …)")
and a seat over its size limit are all logged as `FAILED`. The cost log holds 1,348 FAILED lines
(1,030 of them melious) and cannot say which were false rejects.

**Fix.** A 17th column, `reason`: the text inside the outcome's outer parentheses, as the round's
summary line shows it (`-` for OK). `review_log.sh add` takes `--reason`; `log_seat` passes it.
Column 13 keeps its values (OK, FAILED, NOT-COUNTED), so `summary`'s OK count is unchanged. Older
lines have no column 17; every reader already takes a missing field as `-`, as for columns 15 and
16. The usage text names the column and how to count reasons
(`awk -F'\t' '$13=="FAILED"{print $17}' runs.tsv | sort | uniq -c`). No new report.

## 3. `codex_tokens()` reads the first count, not Codex's own

`codex_tokens()` takes the first line starting "tokens used" in `codex.err`. Codex echoes what it
read into that file, so a quoted line can come first: in `status-line-gate-r3-raw/codex.err` (shared
notes folder), line 317 is a quoted `tokens used: 59,960` and Codex's own count, 72,315, is at lines
2904–2905; every Codex row of that gate was logged at 59,960. Fix: take the last match. Same file,
same cost log; a separate PR would cost its own gate.

## How it is tested

Captures: committed under `scripts/fixtures/`, named for the tool and date, trimmed by cutting
whole lines only (the review is about a private plan; lines that name private code are cut). Each
keeps the structure that matters: marker, at least two finding lines, the closing marker, the
summary line. The real hex marker stays as it is; the test passes that marker to the reader.
Expected values are written by hand.

| Id | Given | When | Then |
|----|-------|------|------|
| T1 | the trimmed ctiPcY reply, as an SSE stream | `melious_stream.pl` reads it | exit 0; the section starts with the capture's first line after its first marker; its first finding line and its summary line are in it; no "marker came 2 times" note |
| T2 | the same for hsNCTK | the same | the same, with that capture's lines |
| T3 | the T1 reply served by the curl stub | `independent_review.sh` with `SECOND_SEAT=melious` (the production entry) | the summary reads `melious OK`, not `FAILED` |
| T4 | the existing marker cases (`mleak`, `mmarkdup`, `mmarkfence`, `mglued`, `mechoglued`, `mtopecho`, `mafterfence`, `mquotemark`, `moldmark`, …) | the suite runs | all pass unchanged |
| T5 | a stub reply the review check rejects | `independent_review.sh`, with `REVIEW_LOG` set | that seat's line has `FAILED` in column 13 and `output is not a review` in column 17 |
| T6 | the existing `costfail` case (ollama 429) | the same | column 17 holds the quota reason the summary shows |
| T7 | an OK seat | the same | column 17 is `-`; `summary`'s ok count is what it was |
| T8 | the r3 `codex.err`, trimmed to the quoted line and the real count | `codex_tokens` | prints 72315 |

Mutation check (the `mutation-check` skill): revert the regex and T1–T3 must fail; drop
`--reason` from `log_seat` and T5–T6 must fail.

The repo's own checks (`test_failed_tier_report.sh`, `test_looks_like_review.sh`,
`test_round_checks.sh`, `test_base_check.sh`, `test_sweep_claims.sh`) run before each review round
and after the last edit.
