# PLAN review — branch `plan/glm-marker-and-failed-reason` — GLM's marker twice, FAILED reason, codex_tokens

Artifact: `docs/reviews/SKILL-PLAN-glm-marker-twice-and-failed-reason.md`. Base `2275e756` · depth:
Normal (a tooling fix to the review script and its cost log; no box, user data, login, money,
deletion or schema, so no red team) · Daniel's go for the gate 2026-11-07. Seats: Codex and GLM 5.3
on melious in one command (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`), fresh-eyes Sonnet in round
1. Evidence: `EVIDENCE-glm-marker-plan.txt` in the session group's shared notes folder (it quotes
private captures, so it stays out of this public repo).

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `708d2ca5` | full plan; evidence E1–E9 (13,748 bytes) | Codex gpt-6.1-sol; melious glm-5.3; fresh-eyes Sonnet | Codex 203 s, 55,137 · melious 213 s, 31,446 · fresh-eyes 116 s, 110,012 | 2 / 6 / 8 before dedup (Codex 2/1/0, melious 0/3/4, fresh-eyes 0/4/2); 11 after |

## Round 1 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| A1 | BUG | Codex | T3 kept the capture's own hex marker, but production asks for a new one each run, so the old regex also passes T3 (no usable marker: kept whole and accepted) and the mutation cannot fail it | fixed: T3 replaces the hex marker at serve time and asserts no no-marker warning and the first finding line |
| A2 | BUG | Codex, fresh-eyes (RISK), melious (NIT) | "every reader already takes a missing field as `-`" is wrong for the counting command: awk reads a missing column 17 as empty; `HEADER` not mentioned | fixed: claim narrowed, command maps empty to `-`, `HEADER` gains `reason`, an old log keeps its header |
| A3 | RISK | Codex, melious, fresh-eyes | "take the last match" for `codex_tokens` rests on one file and on position alone | fixed: survey of 698 real `codex.err` files (691 with one bare footer pair in the last three lines, 7 with none, none with a same-line count); the rule now reads the last bare `tokens used` line followed by a digits-only line; differs from today's code on exactly the 3 quoted runs; T11, T12 added |
| A4 | RISK | melious, fresh-eyes (NIT) | a summary line that itself starts with a label (`BUG: 1, RISK: 5`) would make the second marker usable again | fixed: the finding test is now the review check's own `finding_count` shape (a list, heading or number marker first), so a bare label summary does not count; a `- Totals: 1 BUG` summary still would, pinned KNOWN WRONG (T4) |
| A5 | RISK | fresh-eyes | `test_round_checks.sh:330` asserts a 16-field line, so T4's "all pass unchanged" was wrong | fixed: T9 changes that case to 17 fields |
| A6 | RISK | fresh-eyes, melious (NIT) | the regex accepts less markup than "quote, heading, list or bold" said | fixed with A4: the plan now names the review check's shape and what falls outside it |
| A7 | RISK | melious | the marker cases may not live in the suite E6 ran | refuted: every stub (`leak`, `markdup`, … `markend`) is a `MELIOUS_STUB` case in `test_failed_tier_report.sh` (its `run mleak … MELIOUS_STUB=leak` lines, 1652 on); names corrected in T5 |
| A8 | NIT | melious | no mutation for fix 3 | fixed: restoring the first-match read must fail T10 |
| A9 | NIT | melious | the reason column's spaces vs the outcome's `tr ' ' '-'` unstated | fixed: reason kept word for word, only `clean()` applied |
| A10 | NIT | fresh-eyes | T1/T2 should say the cut keeps the first finding and the summary, and assert no dropped-text note | fixed |
| A11 | NIT | — | (the fresh-eyes "line 172" for the regex is wrong: it is line 112 at `2275e756`; it counted lines of its prompt file) | no change |

UNVERIFIABLE entries: 6 asked (capture history, the 696-check runs, cost-log totals, the
"production entry", PROMPT_CORE's shape, the 59,960 rows); 2 checked by the host and confirmed
(the gate's three Codex rows at 59,960, `grep` on the log; PROMPT_CORE line 861), the rest rest on
the READs sent.
