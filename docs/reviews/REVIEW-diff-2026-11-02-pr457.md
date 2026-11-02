# DIFF review: PR 457, a visible draft notice on the generated legal pages, who clears it, and a test that holds it

Plan: `docs/reviews/PLAN-legal-notice-on-generated-sites.md` (PR 390, PLAN gate clean). Base `9fcce2cc` · depth: High (the build changes what a generated site does and what an assistant is told to do) · verdict: CLEAN at `0aa690c4` · authority used: POST AUTHORITY, WORKTREE-WRITE and BRANCH-COMMIT, each by atom A (this session opened PR 457 and created the worktree and branch).

Sending the diff to Codex and melious.ai: Daniel's words, 2026-11-02, "Yes, send it" in this session, and "Yes, both" to the manager session's question. Scope: this change, every round, those two services.

Seats: Codex (`gpt-6.1-sol`, read-only, effort from config), GLM 5.3 on melious.ai, fresh-eyes (Claude Opus, no shared context, rounds 1 to 3 as High depth asks, and the final full read). "Code that reads another program's output" (rule 5) does not apply: the new code reads the site's own README and its rendered page.

| Round | Head | Artifact | Reviewers | Seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `aea86671` | full, `9fcce2cc` to head, with evidence | Codex; melious out of balance; fresh-eyes | Codex 170 s, 61,685; fresh-eyes 348 s, 191,147 | Codex 0/2/0; fresh-eyes 0/2/5 (the RISKs are F3 and F5) |
| 2 | `b4cc3c56` | delta since `aea86671` | Codex; melious out of balance; fresh-eyes | Codex 211 s, 42,784; fresh-eyes 302 s, 145,978 | Codex 1/1/0; fresh-eyes 0/1/4 (RISK and BUG are the same two findings) |
| 3 | `cf25f4fc` | delta since `b4cc3c56` | Codex; melious out of balance; fresh-eyes | Codex 165 s, 62,704; fresh-eyes 175 s, 133,653 | none, both clean |
| final full read | `cf25f4fc` | whole change | fresh-eyes (a new Opus pass; Codex had seen the change, melious had no balance, ollama never stands in) | 485 s, 212,052 | 0/1/4 |
| 4 | `0aa690c4` | delta since `cf25f4fc` | Codex; melious out of balance | Codex 103 s, 40,547 | none, clean |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | RISK | Codex | 1 | The site's `ci.yml` skips README-only changes, so removing the recorded answer ran no test | fixed, externally_reverified (round 2) | `README.md) run=true` before `*.md)`; classifier cases run by two seats |
| F2 | RISK | Codex | 1 | The browser test said a French note is never seen, against the rule to add translations to `LEGAL_NOTES` | fixed, externally_reverified | the case uses a text in no list |
| F3 | RISK | fresh-eyes | 1 | The per-page test's call site could be switched off with every test green | fixed, externally_reverified (rounds 2, 3, full read) | `template-tests.yml` step; three call-site mutations each turn it red |
| F4 | NIT | fresh-eyes | 1 | The Cloudflare stop named the notice even when only the manifest was listed | fixed, externally_reverified | the clause is conditional; tests 19 and 19b; 19b fails with the condition removed |
| F5 | RISK | fresh-eyes | 1 | `skills/website-launch-check` is in the toolkit (the plan said it is not) and wants a coverage row when a spec changes | deferred, not in this PR | plan decision 4; sent to the manager, who has it in hand; the owner is asked whether the one row joins this PR |
| F6 | NIT | fresh-eyes | 1 | The plan's Status table was "not started" | fixed after the last round | rows filled with this PR |
| F7 | NIT | fresh-eyes | 1 | Evidence lacked `npm run check`, the old-site run and `/de/privacy` | fixed except `/de/privacy` | `npm run check` 0 errors; old-site run red, then green (H5); `/de/privacy` not run |
| F8 | NIT | fresh-eyes | 1 | Em dash in the new test titles | refuted | the file's own title convention, which the launch-check mapping parses |
| F9 | NIT | fresh-eyes | 1 | A record line with trailing spaces or a list marker fails | refuted, then see H1 | strict by design; H1 made the message say so |
| G1 | RISK | Codex, fresh-eyes | 2 | The two `! grep` guards cannot stop a `bash -e` step | fixed, externally_reverified (round 3) | `if grep ...; then exit 1; fi`; run under `bash -e` |
| G2 | BUG | Codex | 2 | The `ci.yml` header comment still said root Markdown skips the tests | fixed, externally_reverified | README.md named as the exception |
| G3 | NIT | fresh-eyes | 2 | The delisting edit changed three lines | fixed, externally_reverified | edit anchored to the declaration |
| G4 | NIT | fresh-eyes | 2 | The Cloudflare clause had no test either way | fixed, externally_reverified | tests 19, 19b |
| G5 | NIT | fresh-eyes | 2 | `red()` could not tell which branch fired | fixed, externally_reverified | takes the branch wording |
| G6 | NIT | fresh-eyes | 2 | Plan decision 4 rests on "not in the toolkit", now false | deferred with F5 | the plan file is not changed here |
| H1 | RISK | fresh-eyes, final read | full read | An assistant may record the answer as a list item or in backticks; the test refuses it and the message does not say why | fixed, externally_reverified (round 4) | "written bare" in AGENTS.md and the failure message; two refused fixtures |
| H2 | NIT | fresh-eyes | full read | The notice bullet and question name the imprint, which an English site deletes | fixed, externally_reverified | |
| H3 | NIT | fresh-eyes | full read | "The new `placeholders.spec.ts`" will go stale | fixed, externally_reverified | |
| H4 | NIT | fresh-eyes | full read | The Cloudflare regex copies `LEGAL_LAST_SEGMENTS` with no link | fixed, externally_reverified | a comment at each place |
| H5 | NIT | fresh-eyes | full read | The plan's old-site scenario was not run | run | scratch copy: no notice, not listed, no record: red with the legal-page message; with a record line: green |

Waivers and deferrals: none by the owner. F5 and G6 are deferred as a follow-up, not as a BUG. Their open question (does the one launch-check table row join this PR?) is Daniel's, put to him by the manager session.

Follow-ups: the launch-check row and its section 3 (F5, G6); the plan's own "not in the toolkit" lines; `/de/privacy` end to end.

Notes:
- Melious (GLM 5.3) failed in every round with an empty balance. By the owner's rule of 2026-10-27 each round stands on Codex alone; no rerun was owed. Codex's chain is unbroken: round 1 saw the whole change, rounds 2 to 4 each saw the delta from the previous head.
- Round 4 is past round 3 and was earned by H1 (kind `record-line-form`), a RISK from the final full read whose fix changed what an assistant is told and what the test prints. The final full read is logged under round 4 in the cost log; it is not a round.
- Totals: 4 rounds and a final full read, 20 findings (1 BUG, 6 RISK, 13 NIT; a finding two seats raised is counted once); 2 deferred (F5, G6), 2 refuted (F8, F9), the rest fixed.
- Tests: spec 11 passed; full suite on the starter 120 passed, 1 skipped (an older positioning skip); mutation check 14 of 14 killed; `make check` exit 0; cloudflare tests 212 pass, 0 skipped. Not run: the new `template-tests.yml` step on GitHub's runner (this PR's CI runs it); `/de/privacy`.
