# PLAN review — karero/croftweaver#390 — where the owner of a generated site meets "first draft, not legal advice"
Base `36fdafef` · depth: High (the plan writes legal text a site owner relies on) · verdict: CLEAN · authority used: POST AUTHORITY and BRANCH-COMMIT — atom B, the maintainer's request to finish and merge this PR (2026-10-24, relayed by the starting session); WORKTREE-WRITE — atom A, this session created the worktree

Host preconditions: (1) no status table → host RISK H1, fixed before round 1 (table added); (2) four open owner questions → asked before round 1, answered "all as recommended" (2026-10-24), written into the plan's Decisions; (3) no separate spec; (4) no code.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | 97d6bc35 | full plan | codex-cli 0.164.0, gpt-6.1-sol, config effort (high), read-only · melious glm-5.3, text only · fresh-eyes claude-opus-5-5 sub-agent, read-only | codex 315 s, 107,560 · melious 91 s, 13,483 · fresh-eyes 209 s, 144,490 | 2/5/7 (after dedup) |
| 2 | a42bd423 | full plan, --verify (changed sections named) | same three seats | codex 330 s, 80,526 · melious 196 s, 23,817 · fresh-eyes 219 s, 143,210 | 1/7/4 (after dedup) |
| 3 | 9b52fcc6 | full plan, --verify | same three seats; the prior-findings file lost the R2 rows (a blank line in this table), so melious checked round 1's rows only; codex and fresh-eyes read the R2 rows from this trail | codex 686 s, 77,829 · melious 221 s, 28,644 · fresh-eyes 219 s, 140,989 | 1/5/8 (after dedup) |
| 4 | 31a7e9b8 | full plan, --verify, `--earned-by owner-identity` | codex, melious (fresh-eyes ends at round 3 at High) | codex 347 s, 79,267 · melious 123 s, 19,972 | 0/2/2 |
| final full read | 449a5fd1 | whole plan | claude-fable-5-1 sub-agent, read-only (kimi-k3:cloud on ollama FAILED: weekly quota, 429) | 776 s, 218,245 | 1/0/5 |
| 5 | 568f7c96 | full plan, --verify, `--earned-by note-language` | codex, melious | codex 298 s, 106,319 · melious 187 s, 31,209 | 1/1/3 |
| wording pass | da47ee36 | delta 568f7c96..da47ee36 (prose) | codex, config effort | 217 s, 61,408 | 0/0/0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| H1 | RISK | host | pre | Plan had no per-step status | fixed, locally_verified | `## Status` table, commit 2616c0d3 |
| F1 | BUG | fresh-eyes | 1 | "only in source comments" also cited `SKILL.md:260/:283`, which are §1 Q5's owner-facing analytics/banner lines | fixed, locally_verified | What rewritten; `sed -n 250,290p SKILL.md` shows both lines in Q5's "Tell the owner plainly" |
| F2 | BUG | codex | 1 | "A visible note does not break handoff" contradicts §4's first item (no "not ready to launch" warning) | fixed, locally_verified | Handoff section rewritten; SKILL.md §4 first item quoted |
| F3 | RISK | fresh-eyes, codex | 1 | Clearing steps only in `new-website/SKILL.md`, which a site does not carry | fixed, locally_verified | Steps now in `templates/AGENTS.md` §5 (How 2); SKILL.md §3 copy list omits new-website |
| F4 | RISK | fresh-eyes, melious | 1 | "I use my own texts" deletes the note before the texts are on the page | fixed, locally_verified | How 2: texts first, else record nothing |
| F5 | RISK | fresh-eyes, codex, melious | 1 | Source-prefix guard credited with catching rewording; misses gutted body, comment-wrap, exempt attribute, wrong language | fixed, locally_verified | Guard replaced by a rendered-page test in `placeholders.spec.ts` (How 5), claim narrowed to what it catches; `template-tests.yml` runs that suite |
| F6 | RISK | melious | 1 | Deleting the note on a site with no recorded answer is caught by nothing | fixed, locally_verified | How 5: note or a `legal pages:` README line |
| F7 | NIT | fresh-eyes | 1 | Header/README "test turns red until you do" lines become untrue | fixed | How 1 edits them |
| F8 | NIT | fresh-eyes | 1 | Rule belongs next to AGENTS.md §5's UNFILLED bullet, not §4 | fixed | How 2 |
| F9 | NIT | fresh-eyes | 1 | No-answer default unstated | fixed | How 2 |
| F10 | NIT | fresh-eyes | 1 | "reviewed by a lawyer" line undated | fixed | How 2: every line dated |
| F11 | NIT | fresh-eyes, codex | 1 | Cited trail file did not exist | fixed | this file |
| F12 | NIT | melious | 1 | "starter README's placeholders paragraph" ambiguous | fixed | How 4 names `templates/astro/README.md` |
| F13 | NIT | melious | 1 | `/datenschutz` swap and i18n route untested | fixed | moved into the build's test list (How it is tested) |
| F14 | NIT | melious | 1 | "(judgment, see below)" dangled | fixed | Judgment list has the item |
| R2-1 | BUG | fresh-eyes, codex | 2 | "holds the note on all three templates": `/datenschutz` is not in `PAGES` (`_helpers.ts:4`), so CI never renders `_datenschutz.astro` | fixed, locally_verified | How 5 "Where it does not look" narrows the claim; a site that swaps it in is checked |
| R2-2 | RISK | fresh-eyes, codex | 2 | Route list misses `/de/privacy` (`astro-i18n-setup/SKILL.md:304`) | fixed, locally_verified | How 5 selects by last path segment under any locale prefix |
| R2-3 | RISK | fresh-eyes | 2 | Languages other than en/de undefined | fixed, locally_verified | How 5: map by `lang`; a missing language fails with the fix named |
| R2-4 | RISK | fresh-eyes, codex | 2 | `whats-new` also drift-tracks tests, so an existing site taking the spec turns red | fixed, locally_verified | Handoff section states it as how a live site meets the question; a pre-change site copy is in the build's test list |
| R2-5 | RISK | fresh-eyes, melious | 2 | README-prefix rule unenforced; an indented or reworded line could open the escape | fixed, locally_verified | How 5 matches only the three dated forms at a line start; the prose rule in How 4 dropped |
| R2-6 | RISK | codex | 2 | `readPage` also reads metadata and attributes, so a note moved into `<Base description>` passes | fixed, locally_verified | How 5 asks for the note text to be visible (`toBeVisible`); description move added to the build's red list |
| R2-7 | RISK | melious | 2 | No run point named on a site | fixed, locally_verified | How 5 names `npm test` and §4's first checklist item |
| R2-8 | RISK | melious | 2 | Handoff item's scope unsupported | refuted | `SKILL.md:791`: "`AGENTS.md` + `CLAUDE.md` (no `[BRACKET]` slot left …)"; now cited in the plan |
| R2-9 | NIT | fresh-eyes, melious | 2 | Handoff paragraph contradicted itself | fixed | rewritten: blocks launch; a pre-launch handover carries it |
| R2-10 | NIT | melious | 2 | Which README the test reads was not pinned | fixed | "the `README.md` at the project root"; toolkit CI root named |
| R2-11 | NIT | fresh-eyes | 2 | A collaborator could answer for the owner | fixed | How 2 clause |
| R2-12 | NIT | fresh-eyes | 2 | F7 partial: AGENTS.md §5 bullet and `astro-i18n-setup` lines also say "filled" only | fixed | How 1 lists both |
| R3-1 | BUG | fresh-eyes, codex | 3 | The R2-11 clause points at "the owner named in §5"; §5 names no owner | fixed, locally_verified | How 2: the answer is the owner's; with collaborators listed in §5, ask whether the person is the owner (`templates/AGENTS.md` §5 lists collaborators and says who publishes) |
| R3-2 | RISK | fresh-eyes | 3 | Exact `lang` lookup fails `en-GB`, `de-AT` | fixed, locally_verified | How 5 keys by primary subtag, as `toneViolations` does (`_helpers.ts:124`); both added to the build's green list |
| R3-3 | RISK | fresh-eyes, codex | 3 | "hidden" over-credited: `toBeVisible` passes `opacity: 0` and off-screen; an exempt note could be both | fixed, locally_verified | How 5 names the three hiding forms it catches and the two it cannot; listed-page condition added, so an exempt note on a delisted page fails |
| R3-4 | RISK | fresh-eyes | 3 | A record covers legal pages added after its date | fixed, locally_verified | How 2: ask again for a page added later, new dated line |
| R3-5 | RISK | codex, melious | 3 | "do not ask again" took any `legal pages:` line; the test takes three exact forms | fixed, locally_verified | How 2 and How 5 use the same three forms; YYYY-MM-DD pinned, malformed date in the build's red list |
| R3-6 | NIT | fresh-eyes | 3 | More "entry comes out when filled" places: `website-qa`, README placeholders paragraph, `cloudflare-setup.mjs` stop message | fixed | How 1 lists them and says to grep for others |
| R3-7 | NIT | fresh-eyes | 3 | `_datenschutz.astro`'s steps are headed "HOW TO USE" | fixed | How 1 |
| R3-8 | NIT | fresh-eyes | 3 | Failure message should name `AGENTS.md` §5 for a site that has the spec but not the new `AGENTS.md` | fixed | How 5 |
| R3-9 | NIT | melious | 3 | Date format unpinned | fixed | with R3-5 |
| R3-10 | NIT | melious | 3 | Exempt hole closable with the listed condition | fixed | with R3-3 |
| R3-11 | NIT | melious | 3 | `astro-i18n-setup` should say to extend the map | fixed | How 1 |
| R3-12 | NIT | fresh-eyes (outside scope) | 3 | A legal route not ending in privacy/datenschutz/impressum is skipped silently | fixed | named under "What it cannot catch" |
| R3-13 | NIT | fresh-eyes (outside scope) | 3 | The prior-findings file lost the R2 rows | fixed | blank line removed; round 4's file carries every row |
| R4-1 | RISK | codex | 4 | `toBeVisible` checks the matched element; part of the note in a hidden child would pass | fixed, locally_verified, not externally re-verified | "What it cannot catch" names it |
| R4-2 | RISK | melious | 4 | R3-4 half fixed: the README arm accepts one dated line for every later page, so ask-again is enforced by nothing | fixed, locally_verified, not externally re-verified | named under "What it cannot catch"; Recommendation narrowed to "a first answer" |
| R4-3 | NIT | melious | 4 | "step 5's map" points nowhere inside `astro-i18n-setup` | fixed | names `tests/placeholders.spec.ts` |
| R4-4 | NIT | melious | 4 | The grep for others finds only marker-named sentences | fixed | claim narrowed, two more phrases |
| FR-1 | BUG | final full read | ffr | A non-en/de site renders the English draft with `lang="fr"`; a note keyed by page `lang` fails from commit 1 and the pre-push hook refuses the first push (`Base.astro:38`, `placeholders.spec.ts:95-96`) | fixed (a cut), locally_verified | Language matching removed: any known note counts on any page; How 5 and the build list rewritten |
| FR-2 | NIT | final full read | ffr | "malformed date" undefined | fixed | "YYYY-MM-DD shape (shape only)" |
| FR-3 | NIT | final full read | ffr | "project root" ambiguous for a site in a subfolder; missing README | fixed | "the folder that holds `package.json`"; missing README counts as no record |
| FR-4 | NIT | final full read | ffr | `website-review/SKILL.md` `npm test` item and `cloudflare-setup.test.mjs` pins | fixed | How 1 names both |
| FR-5 | NIT | final full read | ffr | Decision 3 vs Handoff (tests drift too) | fixed | parenthetical under Decision 3; the decision's words unchanged |
| FR-6 | NIT | final full read | ffr | `SKILL.md:791` should be `:792` | fixed | |
| R5-1 | BUG | codex | 5 | "pins both": `cloudflare-setup.test.mjs:859` pins the list shape and the message's start, not its advice | fixed, locally_verified; judged not substantive (what is built is unchanged), so it earned no round and went to the wording pass | How 1 narrowed: read the advice by hand |
| R5-2 | RISK | melious | 5 | Nothing says the `/datenschutz` swap puts the route in `PAGES` | refuted | `_datenschutz.astro` HOW TO USE step 2: "Swap '/privacy' for '/datenschutz' in: tests/_helpers.ts PAGES"; `astro-i18n-setup/SKILL.md:218` generates `PAGES` from its route registry; now cited in How 5 |
| R5-3 | NIT | codex, melious | 5 | How 2 still said "project root" | fixed | How 2 uses the `package.json` folder |
| R5-4 | NIT | melious | 5 | How 2 allowed trailing text; How 5 asks for the exact form | fixed | "the form and nothing else on that line" |
| R5-5 | NIT | melious | 5 | `en-GB`/`de-AT` build cases test nothing after FR-1 | fixed | kept the `fr` case only |
UNVERIFIABLE asked in round 1: 6 (Playwright totals, croftweaver-site `terms.astro`, scaffold copying, trail, tone/slot rules, drift); confirmed as findings: 1 (trail → F11). The Playwright totals and `terms.astro` stay the plan author's claims; the plan says the runs predate step 5.

UNVERIFIABLE asked in round 2: 7 (the same runs and the external file, readPage scope, run point, handoff scope, language mapping); confirmed as findings: 2 (R2-6 readPage scope, R2-7 run point); the handoff scope was refuted (R2-8).

UNVERIFIABLE asked in round 3: codex 3, melious 8, fresh-eyes 2 (Playwright visibility rule, Astro underscore routing, the external file, the earlier runs, file contents melious could not open); confirmed as findings: 1 (Playwright visibility, R3-3, by fresh-eyes reading playwright-core's `computeBox`).

Follow-ups: none.
Notes: round 4 earned by R3-1 (kind: owner-identity, first time); it found no BUG, so the rounds ended (6(b)) and its RISK/NIT were fixed locally. Final full read on Fable (ollama out of quota, no Kimi; melious is GLM only); its BUG FR-1 earned round 5 (kind: note-language), fixed by a cut. Round 5 had no substantive BUG: the rounds ended (6(b)). Wording pass clean. Totals: 5 rounds + final full read + wording pass, 55 findings (6 BUG, 19 RISK, 30 NIT, H1 included); 1,276,968 tokens logged across all seats (fresh-eyes and the final full read included); the host's own fixing not counted. "no trace in git history" corrected to "before this plan" (fresh-eyes, letter only).
