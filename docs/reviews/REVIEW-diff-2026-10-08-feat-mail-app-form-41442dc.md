# DIFF review — feat/mail-app-form — website-contact-form, a contact form the visitor's own mail program sends

Base `fd3ba44` (the head of #214, which merged as `cc6f1f2` with the same tree, so the reviewed diff is the diff against `main`) · depth: **Normal** (code that ships into sites plus a job behind the required check `template-tests-ok`; no auth, personal data store, secrets or deploy; it adds no privacy text and advises none beyond the starter's) · verdict: **CLEAN** — every BUG fixed (one in the starter's `EmailLink`, which this change now calls), every RISK fixed or refuted. 5 rounds and a re-gate, 29 findings after dedup. Authority used: WORKTREE-WRITE and BRANCH-COMMIT (this session created the worktree and branch at the owner's instruction in this session); GATED-THIS-DIFF (seen pairs below). Send consent: the owner's message in this session, "the independent-review gate before merge (Codex + GLM 5.3 on melious, per the owner's CLAUDE.md)".

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `41442dc` | full: `git diff fd3ba44...41442dc -- . ':(exclude)docs/reviews/'` | Codex 0.161.0 `gpt-6.1-sol` (config effort), read-only; Melious `glm-5.3`; fresh-eyes Sonnet sub-agent | codex 304 s/75,753; glm 340 s/34,381; fresh-eyes 457 s/160,981 | 1 / 4 / 7 |
| 2 | `499acec` | delta `41442dc..499acec` | Codex (medium); Melious glm-5.3 | codex 198 s/51,333; glm 243 s/25,354 | 0 / 1 (re-raise) / 4 |
| re-gate | `a3623e1` | delta `499acec..a3623e1` (round 2's NIT fixes) | Codex (medium); Melious glm-5.3 | codex 106 s/33,758; glm 48 s/7,194 | 0 / 0 / 2 |
| 3 | `ffda286` | delta `a3623e1..ffda286`: the owner's request that each site choose its subject line | Codex (medium); Melious glm-5.3 | codex 189 s/47,553; glm 243 s/13,887 | 1 / 1 / 2 |
| 4 | `64c36fe` | delta `ffda286..64c36fe` | Codex (medium); Melious glm-5.3 | codex 178 s/41,228; glm 863 s/19,361 | 1 / 1 / 1 |
| 5 | `b518882` | delta `64c36fe..b518882` | Codex (medium); Melious glm-5.3 | codex 119 s/38,244; glm 187 s/9,763 | 0 / 1 / 2 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| C2 | BUG | codex | 1 | a `<select multiple>` sent only its first chosen entry | fixed `31d2db5`; externally_reverified (2) | spec selects two entries, asserts "Days: Monday, Friday"; reverting the fix fails it |
| C1 | RISK | codex | 1, 2 | Playwright may not see a `location.href` `mailto:` navigation as a request | refuted | reproduced in Chromium by the author and by fresh-eyes (`waitForRequest` returns the full URL); 89 tests green; breaking the link's address, encoding or body fails them |
| C3 | RISK | codex | 1 | "almost no spam" promised more than the form gives | fixed `31d2db5`; externally_reverified (2) | SKILL.md now: no spam through the form; spam to the address is as for any address |
| M1 | RISK | glm | 1 | the address charset claim is enforced nowhere | refuted | `encodeEmail` in `src/lib/obfuscate.ts` tests `/^[A-Za-z0-9._%+-]+@…/` and throws at build |
| F1 | RISK | fresh-eyes | 1 | the 2,000 cap counts typed characters; the link is 2,800–12,000 | fixed in wording `499acec`; externally_reverified (2) | comment, SKILL.md §5 and BUGLOG row say the cap is tied to no measured limit |
| M2 | NIT | glm | 1 | a decode failure was silent | fixed `31d2db5`; externally_reverified (2) | status line first, `console.error` |
| M3 | NIT | glm | 1 | whats-new note drops `forms.spec.ts` | refuted | `git ls-tree v0.29` holds no `website-forms`; the skill never shipped in a release |
| F2 | NIT | fresh-eyes | 1 | a named `<fieldset>` threw in the field loop | fixed `499acec`; externally_reverified (2) | spec injects one; removing the guard fails it |
| F3 | NIT | fresh-eyes | 1 | a field of spaces passed `required` | fixed `499acec`; externally_reverified (2) | new test; removing the check fails it |
| F4 | NIT | fresh-eyes | 1 | page-wide, inexact selectors in the spec | fixed `499acec`, `a3623e1`; externally_reverified (re-gate) | — |
| F5 | NIT | fresh-eyes | 1 | `%` in the address not escaped in the link | fixed `499acec`; test `a3623e1`; externally_reverified (re-gate) | removing the escape fails the new test |
| F6 | NIT | fresh-eyes | 1 | stale "external bundle" comment in the starter's `email.spec.ts` | follow-up | added to the BUGLOG row on the inline decoder |
| R2-2 | NIT | glm | 2 | a lone surrogate made encoding throw | fixed `a3623e1`; externally_reverified (re-gate) | try/catch, `console.error` |
| R2-3/4 | NIT | glm | 2 | the `%` escape untested; `encodedAddress` unused | fixed `a3623e1`; externally_reverified (re-gate) | — |
| G1 | NIT | glm | re-gate | no on-page feedback when encoding fails | refuted | the status line is set before encoding and says to write to the address below if nothing opened |
| G2 | NIT | glm | re-gate | no test reaches the encoding `catch` | follow-up | a confirmation's other findings are follow-ups |
| S2 | BUG | codex (outside scope, reached by this change) | 3 | the starter's `EmailLink` put a `%` address into `mailto:` unescaped (`a%41@` opened a mail to `aA@`) | fixed `64c36fe`; externally_reverified (4) | new test in the starter's `tests/email.spec.ts` through EmailLink's own script; reverting the fix fails it |
| S1 | RISK | codex + glm | 3 | the address-link check assumed one exact encoding | fixed `64c36fe`; externally_reverified (4) | the link is parsed as a mail program reads it; a changed address or subject fails it |
| S3 | NIT | glm | 3 | CI never proved a form without a subject stops the build | fixed `64c36fe`; externally_reverified (4) | last CI step |
| S4 | NIT | glm | 3 | an over-long line in SKILL.md step 4 | fixed `64c36fe`; externally_reverified (4) | — |
| P1 | BUG | codex | 4 | the spec's link reader cut 7 characters blindly, so an `http://` link passed | fixed `b518882`; externally_reverified (5) | `parse()` asserts `mailto:`; an EmailLink building `http://` links fails the test |
| P2 | RISK | codex | 4 | the `%` test assumed `/` carries an EmailLink | fixed `b518882`; externally_reverified (5) | it uses the first page that shows an address; ran on `/impressum` with the home page's removed |
| P3 | NIT | glm | 4 | EmailLink's subject may not be encoded | refuted | `EmailLink.astro` line 23: `encodeURIComponent(subject)` |
| Q1 | RISK | glm | 5 | `data-email` may be written only in the browser, so the `%` test would always skip | refuted | the starter's no-JS test reads `a.email-link[data-email]` with scripts off; the test ran, not skipped, on `/` and `/impressum` |
| Q2 | NIT | glm | 5 | routing an exact URL misses a redirect | refuted | `trailingSlash: 'never'`, `PAGES` without slashes; the test ran on `/impressum` |
| Q3 | NIT | glm | 5 | `baseURL!` may be unset | refuted | the same file's existing tests use `baseURL!` (line 18) |

Waivers: none. Deferrals: none. Follow-ups: F6 (BUGLOG), G2.

Notes: rounds 3 to 5 review a change the owner asked for after the gate first closed (each site chooses its subject line); round 4 was earned by round 3's BUG S2, round 5 by round 4's BUG P1, and round 5 called for no fix (stop condition a2). The ollama seat was absent by design (Melious is the second seat; CLI hidden from `PATH`). Round 2 had no new BUG or in-scope RISK (stop condition a2); its NITs were fixed and passed a re-gate by both seats, which the script logged as round 3 but is not a round. Both cross-model seats hold an unbroken chain `41442dc` → `499acec` → `a3623e1` → `ffda286` → `64c36fe` → `b518882`; fresh-eyes' chain ends at round 1 by design. No PR exists yet: the PR comment is posted when the owner allows the push.
