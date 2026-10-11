# DIFF review — fix/mail-form-signoff — the contact form's mail is the visitor's message as typed, and the form speaks its page's language

Base `origin/main` (`ae190f7`, #215 merged) · depth: **Normal** (template code that ships into sites, the starter's `Base.astro`, a CI job behind `template-tests-ok`; no auth, data store, secrets or deploy) · verdict: **CLEAN** — every BUG fixed, every RISK fixed or refuted. 5 rounds, a re-gate and a confirmation, 29 findings after dedup. Authority used: WORKTREE-WRITE and BRANCH-COMMIT (this session created the worktree and branch, for the owner's two requests relayed by the "Release 0.30 preparation" session and his answers in this session); send consent: the owner's standing instruction in this session, "Codex + GLM 5.3 on melious".

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `8f14c7f` | full: `git diff origin/main...8f14c7f -- . ':(exclude)docs/reviews/'` | Codex 0.161.0 `gpt-6.1-sol` (config effort), read-only; Melious `glm-5.3`; fresh-eyes Sonnet sub-agent | codex 270 s/75,514; glm 125 s/17,854; fresh-eyes 214 s/125,418 | 2 / 4 / 9 |
| 2 | `0b58772` | delta `8f14c7f..0b58772` | Codex (medium); Melious glm-5.3 | codex 171 s/45,894; glm 87 s/18,789 | 1 / 1 / 2 |
| 3 | `74841c9` | delta `0b58772..74841c9` (round 2's fixes, and the owner's switch to "Freundliche Grüße") | Codex (medium); Melious glm-5.3 | codex 119 s/42,029; glm 28 s/8,529 | 0 / 2 / 0 |
| 4 | `656114f` | delta `8139f00..656114f`: the owner's second request, the mail is the visitor's message only (no greeting, no closing line, no Name field) | Codex (medium); Melious glm-5.3 | codex 90 s/46,640; glm 37 s/11,387 | 1 / 0 / 0 |
| 5 | `d125533` | delta `656114f..d125533` | Codex (medium); Melious glm-5.3 | codex 67 s/30,618; glm 33 s/7,316 | 1 / 1 / 0 |
| re-gate | `4e8ff2e` | delta `d125533..4e8ff2e` | Codex (medium); Melious glm-5.3 | codex 103 s/34,211; glm 36 s/6,723 | 0 / 0 / 1 |
| confirmation | `8a326c6` | delta `4e8ff2e..8a326c6`, one comment rewrapped | Codex (medium) | codex 55 s/17,655 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | BUG | codex; RISK glm, fresh-eyes | 1 | the spec's "form language = page language" check rejected the documented `lang` override | fixed `0b58772`, completed `74841c9`; externally_reverified (2, 3) | spec `LANG`; `lang="en"` on the German page fails without it, passes with it |
| A2 | BUG | codex; NIT glm | 1 | "an older starter stops the build" was false where `lang` or `Astro.currentLocale` supplies the language | fixed `0b58772`, `74841c9`; externally_reverified (2, 3) | scoped to a site without Astro's language routing and a form without `lang` |
| B1 | BUG | codex; NIT glm | 2 | `LANG` compared as typed while the form shortens the code (`en-GB`) | fixed `74841c9`; externally_reverified (3) | `lang="en-GB"` with `LANG='en-GB'`: 12 of 12 pass |
| A3 | RISK | codex, glm | 1 | `Astro.locals` set in `Base` may not reach the slotted form | refuted | fresh-eyes read `astro/dist/core/fetch/fetch-state.js` (one locals object per render state); built `impressum.html` has `<form lang="de">` with no `lang` prop; German spec copy green |
| A4 | RISK | glm | 1 | a language without `closing` writes "undefined" | refuted | `Array.prototype.join` renders undefined as ""; `satisfies Record<string, Texts>` fails `npm run check` |
| A5 | RISK | fresh-eyes | 1 | "copy the starter's `src/env.d.ts`" would overwrite a site's own | fixed `0b58772`; externally_reverified (2) | add the declaration; create the file only if absent |
| B2 | RISK | glm | 2 | the build stop mis-scoped for a site with i18n routing | fixed `74841c9`; externally_reverified (3) | "with routing, the page's locale stands in" |
| C1 | RISK | codex | 3 | the routed-locale fallback is untested | refuted | `fetch-state.js`: `currentLocale` is undefined only `if (!i18n \|\| !routeData)`, read by fresh-eyes in round 1; astro-i18n-setup relies on it for every page |
| C2 | RISK | glm | 3 | the form may not shorten `en-GB` before rendering | refuted | `MailForm.astro`: `pageLang.toLowerCase().split('-')[0]`; the `en-GB` run rendered `lang="en"` |
| D1 | BUG | codex; NIT glm | 4 | "the message exactly as typed" was false: the script trims the message's edges | fixed `d125533`, `4e8ff2e`; externally_reverified (5, re-gate) | the docs say outer empty space is dropped; the spec types a blank line, spaces and tabs around the message; removing the trim fails it |
| E1 | BUG | codex; RISK glm | 5 | "spaces and blank lines" understated the trim, which drops tabs too | fixed `4e8ff2e`; externally_reverified (re-gate) | "any empty space (spaces, tabs, blank lines)" |
| E2 | RISK | codex (outside scope) | 5 | Playwright may not see the `mailto:` navigation | refuted | a re-raise with no new evidence: reproduced in Chromium in #215's gate; the suite is green and breaking the link fails it |
| F1 | NIT | glm | re-gate | an over-long comment line in `mail-form.js` | fixed `8a326c6`; externally_reverified (confirmation) | — |
| A6 | NIT | fresh-eyes | 1 | the "no language" build error had no CI test | fixed `0b58772`; externally_reverified (2) | last CI step |
| A7 | NIT | fresh-eyes | 1 | astro-i18n-setup prose did not name the replaced line | fixed `0b58772`; externally_reverified (2) | — |
| A8 | NIT | fresh-eyes, glm | 1 | over-long lines | fixed `0b58772`; externally_reverified (2) | — |
| A9 | NIT | glm | 1 | `env.d.ts` lacks an `astro/client` reference | refuted | the starter's tsconfig includes `.astro/types.d.ts` |
| A10 | NIT | fresh-eyes | 1 | the starter README tree omits `env.d.ts` | refuted | the tree is partial by design |
| B3 | NIT | glm | 2 | an over-long CI comment line | fixed `74841c9`; externally_reverified (3) | — |
| B4 | NIT | glm | 2 | astro-i18n-setup §3 prose may point at a line the code lacks | refuted | `heavy-path-code.md` line 130 |

Waivers: none. Deferrals: none. Follow-ups: none.

Notes: the ollama seat was absent by design (Melious is the second seat). Round 3 called for no fix (stop condition a2); rounds 4 and 5 review the owner's second request, made after testing the form in his own mail program, and round 5 was earned by round 4's BUG D1. Round 5's BUG E1 was wording plus a stricter test, so it earned no round: a re-gate by both seats and a one-seat confirmation of the comment rewrap closed it. The sign-off from rounds 1 to 3 ("Regards" / "Freundliche Grüße") was removed again in round 4. The owner first chose "Viele Grüße" in this session, then "Freundliche Grüße" (relayed by the release session, confirmed by the owner here); the change rode in round 3's delta. The heavy i18n path's `Astro.locals.lang = currentLocale;` line was read, not built: no CI job applies `heavy-path-code.md`. Both cross-model seats hold an unbroken chain `8f14c7f` → `0b58772` → `74841c9`; fresh-eyes' chain ends at round 1 by design. Round 3's head `74841c9` was recommitted as `1bee901` before the push, only to take a personal name out of its message: same tree, byte-identical diff.
