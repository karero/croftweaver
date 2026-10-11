# DIFF review — PR #257 — facts-check: fewer false ties (nearest fact wins, whole-word terms, more date forms)
Base `c495d93` · depth: Normal (the diff changes `facts_check.py`, a script that reads the open web, and `SKILL.md`, an instruction file agents follow) · verdict: CLEAN; two NITs (F4, F7) waived by the owner on 2026-10-11 · authority used: POST AUTHORITY — atom B (the owner's "Finish it" for the false-tie item, 2026-10-11); WORKTREE-WRITE — atom A (this session's own checkout); BRANCH-COMMIT — atom A (this session created `fix/facts-check-false-ties`)

Data consent: the artifact is a public diff of one script, its tests and two public text files. A grep of the diff for keys, tokens and passwords found nothing. Melious (GLM 5.3) was used on this repo for the PR #230 rounds; no new quoted OK was asked in this session. Codex was not available in this container; ollama-cloud answered HTTP 429 and received nothing; Antigravity was not used.

Seats: the standard pair could not run. Round 1 had GLM 5.3 on Melious and a Sonnet fresh-eyes pass; rounds 2 and 3 had GLM alone. No Codex seat counted in any round, so the change was not read by a cross-family second reviewer after round 1.

| Round | Head | Artifact | Reviewers: model, seat | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `1c53f11` | full: `origin/main...1c53f11`, 4 files (docs/reviews excluded) | melious glm-5.3, HTTP API, text only; fresh-eyes: Claude Sonnet through the Agent tool, read-only by instruction | melious 172 s / 29,439; fresh-eyes 256 s / 84,748 | 0/2/4 (GLM), 0/1/3 (fresh eyes); 0/3/6 after dedup |
| 2 | `6b3e09e` | delta `1c53f11..6b3e09e`, with round 1's dispositions (`--verify`) | melious glm-5.3 | melious 588 s / 35,593 | 0/1/1 |
| 3 | `3df3e8d` | delta `6b3e09e..3df3e8d`, with round 2's dispositions (`--verify`) | melious glm-5.3 | melious 75 s / 9,808 | 0/1/0 |

Round 1 ran with `codex SKIPPED (not available), ollama-cloud FAILED (HTTP 429)` and exit 4 from the script; GLM was then run alone with `--seat melious`, and counted.

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | RISK | glm | 1 | Another fact's `before` phrase did not stop this fact's term from tying: "an NPS of 72 clients" still tied 72 to a clients fact | fixed — externally_reverified (round 2) | `a7c3d7c`: a rival's before phrase ending right before the number claims it; `FindMentions.test_the_nearest_term_after_the_number_wins` |
| F2 | RISK | glm | 1 | `parse_number` is called with a match object in the new helper; its signature is unverified | refuted | `def parse_number(m: "re.Match")` in `facts_check.py`; the date tests run through it |
| F3 | NIT | glm, fresh-eyes | 1 | Date forms left the year as a count: "September 4th, 2026", "10 March, 2026", "September 4-6, 2026", "4 September, 2026", "4. Sept. 2026" | fixed — externally_reverified (round 2) | `a7c3d7c`, `6b3e09e`: `_ends_a_date`; probes before the fix gave `MISMATCH 2026` for each; `FindMentions.test_a_year_after_month_and_day_is_a_year` |
| F4 | NIT | glm | 1 | A rival's multi-word term cut by the window does not block | waived by the owner, 2026-10-11 | it needs a multi-word rival term longer than the window; no real facts file has one; the other fact then keeps the number, which is the old behaviour |
| F5 | NIT | glm | 1 | SKILL.md said the first term "decides"; two terms at the same word tie both | fixed — externally_reverified (round 2) | `a7c3d7c`: SKILL.md says so |
| F6 | RISK | fresh-eyes | 1 | A rival's term was searched in this fact's window, not its own: a rival with window 1 claimed a number it never ties, and the number appeared nowhere | fixed — externally_reverified (round 2) | `6b3e09e`: each rival is checked in `after_words[:win]`; probe "500 vetted countries agents" gave `[]` before, `[500]` after |
| F7 | NIT | fresh-eyes | 1 | Term parsing for every rival is repeated per fact, location and page (3x slower at 60 facts; 3.8 s against 1.2 s on a synthetic page set) | waived by the owner, 2026-10-11 | real facts lists hold 10 to 30 facts; the extra cost is milliseconds per page against a 0.5 s delay between requests |
| F8 | NIT | fresh-eyes | 1 | One very long line in SKILL.md | fixed — externally_reverified (round 2) | `6b3e09e`: rewrapped |
| F9 | RISK | glm | 2 | The "September 4-6" guard cannot fire if the tokenizer emits a token for the hyphen | refuted, then pinned | `fc.tokenize("September 4-6, 2026")` gives word, num, num, stop, num (no token for the hyphen); the date subTests assert `[]`, so a hyphen token would give `MISMATCH 2026` and fail; round 3 asked for a direct pin (F11) |
| F10 | NIT | glm | 2 | `_before_ends_at` walked back 8 words for every term-tied number even when no rival has a before phrase | fixed — externally_reverified (round 3) | `3df3e8d`: `if not befores: return False` first |
| F11 | RISK | glm | 3 | F9's refutation rests on a tokenizer run only the author saw | fixed, not re-reviewed | `4c2dc2a`: `test_a_day_range_is_two_numbers_with_no_token_for_the_hyphen` pins the token stream for the hyphen and the spaced en dash. A test-only change that pins behaviour already shown |

11 findings (0 BUG, 5 RISK, 6 NIT) in 3 rounds: 7 fixed, 2 refuted (F2, F9), 2 waived by the owner (F4, F7).

Waivers and deferrals: F4 and F7 are NITs with a reason each. The owner waived both on 2026-10-11, in the session that prepared the 0.30 release: "F7 (speed): waive outright. F4 (a far-fetched false tie): waive, and keep a BUGLOG row." The row is in `docs/BUGLOG.md` (`facts_check.py`, `find_mentions`).

Follow-ups: none.

Gaps stated:
- The last commit, `4c2dc2a`, is a test that pins existing behaviour and a BUGLOG line-number update; no outside reviewer read it.
- No Codex seat counted in any round (not available here; Ollama quota). Rounds 2 and 3 had one seat, GLM.
- The date handling covers month names in English and German (`MONTHS`); other languages' months are not read as dates.
- A pasted live-run report was the source of the false ties; the run itself is not repeated with the new rules, because the site is not reachable from this container. The next owner run should show the difference.

Notes: Checked with 108 tests on Python 3.11 here (`make test-facts`); CI runs 3.9 and 3.12. `make check` in this container fails only in `test_git_stand_hook` (two ssh cases), which fails the same way on a clean main.
