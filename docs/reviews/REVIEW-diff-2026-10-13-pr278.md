# DIFF review — PR #278 — Template privacy page: an open visit continues as the same visit (EN and DE)
Base `0bd1b34` · depth: High (privacy text) · verdict: CLEAN for the content; two edits made after the last review are named below and were not read by a reviewer

This pull request had no gate of its own. Its two files went through ONE combined High gate with the same sentence on four live sites, and the findings that touched these files are listed here, because nowhere else lists them. The combined gate's own record is the four site pull requests' bodies.

Data check: this repository is public and the diff holds no key, token or password. Seats: Codex, GLM 5.3 (melious.ai, and ollama cloud when melious timed out at 300 s), and a fresh-eyes read of the Plausible v3.2.1 source.

| Round | Template head | Seats | BUG/RISK/NIT touching these files |
|---|---|---|---|
| 1 | `5a45620` (fixes `5338225`, `185ccea`) | Codex, GLM 5.3 (melious), fresh-eyes | 0/3/3 |
| 2 | `185ccea` (fixes `f8a1a99`) | Codex, GLM 5.3 (ollama), fresh-eyes | 0/1/2 |
| 3 | `f8a1a99` | the same | 0/0/0 |
| 4 | `f8a1a99`, then `ed5edfe` for the accuracy batch | the same | 0/0/1 |
| Wording pass | `ed5edfe` | one pass on the final artifact | its one point was about a backup sentence, which is not in the template |

Across the five repositories the gate found about 60 findings. BUGs were raised in rounds 1 to 3 (the "Last updated" dates, a backup bullet on another site, a README sentence); none was in these files, and round 4 had none. The 10 below are the ones that touched these two files: 0 BUG, 4 RISK, 6 NIT.

| id | Sev | Round | Finding, one line | Status |
|---|---|---|---|---|
| H3 | RISK | 1 | the carry-over claim (a visit still going continues under the previous value) was not traced to the source | refuted with evidence: `find_session` in `cache_store.ex`, `previous_user_id` in `event.ex`, `salts.ex`, the 30-minute session TTL and the midnight rotation were read at the v3.2.1 tag by two seats |
| H5 | RISK | 1 | the template might carry facts that belong to one owner | refuted for the backup sentence (it is not in the template); for the clause, the header note was added (H12) |
| H12 | RISK | 1 | the clause is unverified for Plausible Cloud | fixed: header note says to keep it with Cloud only if Plausible confirms the same, and to delete it with another analytics tool |
| H6 | NIT | 1 | "still open" reads as "the tab is still open" | fixed: "still going at that moment (one with activity in …)"; German analogue |
| H14 | NIT | 1 | "It cannot recognise it on another website": two "it"s | fixed: "Nor can the tool recognise that browser on another website." / "Auch auf einer anderen Website erkennt es diesen Browser nicht." |
| H15 | NIT | 1 | the new sentences were 200-character lines in hard-wrapped files | fixed by wrapping; the stray breaks that wrapping left are cleaned up below |
| P3 | RISK | 2 | the re-check list named files that cannot fire for the previous-day identifier | fixed: both header notes name `on_event` and `find_session`, `register_session`, `salts.ex` and the `RotateSalts` cron |
| N2 | NIT | 2 | the German draft's header lacked the note | fixed |
| N3 | NIT | 2 | "the last 30 minutes" is slightly narrower than the code | fixed in round 4 (S8) |
| S8 | NIT | 4 | the code truncates to whole minutes, so 30 minutes is not exact | fixed: "about the last 30 minutes" / "rund 30 Minuten" |

## After the last review (not read by a reviewer)

- `0bd7801` merged `origin/main` (56 commits, none under the template). The pull request's own diff is byte-identical before and after: `git diff <old base> ed5edfe` and `git diff origin/main 0bd7801` over the two pages give the same hash.
- `e5efda5` re-wrapped two paragraphs ("Nor / can" and "Auch" had been left alone on a line). The text is identical apart from line breaks: both files hash the same with all whitespace collapsed, before and after.

## Notes

- No consolidated marker is posted. The pair did not read this head as a pull request of its own, and the clerk procedure does not stamp on a say-so.
- No test in the template pins the clause (a search of its tests found none).
- The clause is a claim about one Plausible version. Nothing re-checks it when Plausible changes its session lookup; the header note names the files to re-read.
