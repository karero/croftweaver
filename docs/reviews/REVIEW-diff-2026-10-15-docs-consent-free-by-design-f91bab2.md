# DIFF review — docs/consent-free-by-design — when a kit site needs no consent banner; DNT and refusal sentences
Base `8f7c98b` · depth: High (privacy and legal texts) · verdict: CLEAN (5 rounds, a final full read and a wording pass; 33 findings, 3 BUG, all fixed) · authority used: POST AUTHORITY — atom B (the owner's brief asked for a pull request with one review comment) and atom A (this session opens the PR); WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch)

Seats: Codex (config effort; medium for the wording pass), GLM 5.3 on melious, a fresh-eyes sub-agent on the host's model in rounds 1 to 3. Final full read: Kimi on ollama FAILED (quota), so a fresh host-model reader that had not seen the change read the whole diff.

| Round | Head | New findings (BUG/RISK/NIT) | Seats |
|---|---|---|---|
| 1 | `f91bab2` | 1/9/8 | codex 238 s / 83,121; melious 246 s / 11,775; fresh-eyes 334 s / 150,005 |
| 2 | `e115ab8` | 0/2/3 | codex 194 s / 76,138; melious 442 s / 22,041; fresh-eyes 216 s / 119,644 |
| 3 | `66379d6` | 1/1/2 | codex 206 s / 67,877; melious 332 s / 16,980; fresh-eyes 125 s / 106,790 |
| 4 (earned by host-parse) | `4cd4e12` | 1/0/0 | codex 181 s / 73,902; melious 109 s / 6,689 |
| 5 (earned by host-parse; cut) | `597f28f` | 0/0/0 | codex 236 s / 75,041 (none); melious 114 s / 6,603 (1 follow-up) |
| final full read | `597f28f` | 0/3/2 | host model 219 s / 146,351; ollama kimi-k3 FAILED (quota) |
| wording pass | `75b520c` | 0/0/0 | codex 60 s / 40,284 |

**BUGs (all fixed).**
- Round 1: the CCPA's 100,000 threshold counts consumers whose data a business buys, sells or shares, not whose data it processes (Civ. Code § 1798.140(d)(1)(B)).
- Rounds 3 and 4, one kind (host-parse): the refusal sentence read the analytics host from `ANALYTICS.scriptHost`, and some values gave an empty host on a legal page. A try/catch fallback in round 2 and a fail-the-build read in round 3 each left a case open. Round 4 cut the parsing: the host is now a `[BRACKET]` launch slot, which `tests/placeholders.spec.ts` reports until launch (10 leftovers on `/privacy`, 9 before).

**Owner decision (2026-10-15).** Round 1 asked whether "in Switzerland and California it holds" claims too much (the Swiss regulator's cookie guideline v1.1 asks for more than a notice by some readings; CalOPPA only governs disclosure). The owner chose: keep "no banner needed" for a site without analytics; with Plausible, all four markets get "a defensible position, not a settled one".

**Refuted.**
- "Handles every visit the same way, with or without [DNT/GPC]" lacked support: plausible/analytics `tracker/src/track.js` at `598928e7db` skips sending only for localhost, an automated browser, the `plausible_ignore` flag, exclusion rules and `transformRequest`; no file in `tracker/src` mentions doNotTrack, globalPrivacyControl, gpc or dnt; a code search of the repo finds no server handling either.
- "No other third party" implies the named providers may collect across websites: kept on purpose. Cloudflare serves many sites and nothing read for this change shows otherwise; the page already says Plausible cannot recognise the browser on another website.
- A dated, closed row in `docs/BUGLOG.md` quotes the old opt-out sentence: history, left as it is.

**Fixed RISK and NIT, in short.** The third-party sentence narrowed to what the page says of its providers; refusal by content blocker only (browsers have no per-source script setting); the Art. 45c FMG paraphrase now includes the purpose; CalOPPA's DNT disclosure stated as owed only by a site that itself tracks across websites; the revenue figure marked as adjusted every two years; a proxied same-domain analytics host noted in both headers; the skill now says the headers set out the sources on both sides and ask you to record who accepted the position; a theme toggle that stores the choice named as needing a look; `src/config.ts` says a new `scriptHost` means a new host in the privacy page's sentence; wording and line wraps.

**Follow-ups for the owner (not done here).** A test that the host in the refusal sentence matches `ANALYTICS.scriptHost`'s host (GLM, rounds 2 and 5); the CCPA sentence leaves out "in excess of" and "in the preceding calendar year" (fresh-eyes, round 2).

Sources checked: Art. 45c FMG (SR 784.10) via the droit-bilingue.ch mirror (fedlex serves only a JavaScript shell); CPPA CPI adjustment page (USD 26,625,000 from 1 January 2025); CalOPPA § 22575(b)(5)–(6) and CCPA § 1798.140(d) via FindLaw (leginfo returned 403). Tests on every head: the starter's `npm test` 69 passed, 1 skipped (the unfilled positioning spine, as on main), `tests/check_analytics_gate.sh` green; the German draft built once as `/datenschutz` in a scratch copy; `scripts/check_clean.sh` and `scripts/check_skill_budgets.sh` OK on a clean checkout.
