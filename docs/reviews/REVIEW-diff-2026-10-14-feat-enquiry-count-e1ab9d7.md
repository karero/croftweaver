# Review trail: enquiry count ("Email Tap" event), branch feat/enquiry-count

DIFF gate. **Depth: High**, because the change edits the starter's privacy pages (EN and DE)
and adds data a live site sends. Reviewers every round: Codex at config.toml's effort, GLM 5.3
on melious (`SECOND_SEAT=melious`), and a fresh-eyes pass on the host's own model. A final
full read follows the last round.

Artifact per round: `git diff <base>...HEAD -- . ':(exclude)docs/reviews/' ':(exclude)docs/BUGLOG.md'`
with a brief and the test records on top. The BUGLOG release-note row is record prose, read by
the wording pass.

Requirements: `docs/reviews/SKILL-PLAN-enquiry-count.md` (owner-approved 2026-10-14).

## Rounds

| Round | Head | Reviewers | Findings (BUG/RISK/NIT) | Outcome |
|---|---|---|---|---|
| 1 | e1ab9d7 | codex (gpt-6.1-sol, config effort) 293 s 91k tok; melious glm-5.3 261 s 21k tok; fresh-eyes (claude-opus-5-5) 204 s 127k tok | 1 / 4 / 6 | one wording BUG fixed; payload and delivery claims measured; next round owed by the fixes |
| 2 | 02a26c3 (verify e1ab9d7..02a26c3) | codex (config effort) 278 s 88k tok; melious glm-5.3 136 s 15k tok; fresh-eyes (claude-opus-5-5) 190 s 122k tok | 1 / 1 / 6 | F1's fix opened G1 (substantive); round 3 owed |
| 3 | c8280aa (verify 02a26c3..c8280aa) | codex (config effort) 264 s 57k tok; melious glm-5.3 118 s 13k tok; fresh-eyes (claude-opus-5-5) 145 s 120k tok | 0 / 0 / 2 in scope (+1 BUG, 1 NIT outside) | clean by (a2); rounds end |

## Findings

| Id | Sev | Source | Round | Location | Finding | Status | Evidence |
|---|---|---|---|---|---|---|---|
| F1 | RISK | fresh-eyes | 1 | `website-contact-form/SKILL.md` §4 | A pre-0.32 site told to copy the privacy sentence would claim email-address clicks are counted while its own `EmailLink.astro` has no listener (the form shows the address through it). | fixed, locally_verified | §4 now says take both the listener and the sentence, or leave the sentence out |
| F2 | BUG | codex | 1 | `new-website/SKILL.md` Q5, `website-contact-form/SKILL.md` §5, both code comments | "visitors who opened their mail program" overstates: the event fires on the request, before anything opens. | fixed, locally_verified | reworded to "asked to write"; "whether a mail program opened ... the site never learns" |
| F3 | RISK | melious (fresh-eyes: unverifiable) | 1 | `mail-form.js` count then `location.href`; link click then default navigation | Delivery during a mailto: navigation unsupported. | refuted | live probe 2026-10-14, headless Chromium, croftweaver.com/privacy with its real per-site script (v33), /api/event intercepted locally: a real link click and the form's exact sequence each sent one event, then the mailto: request; page stayed. Safari and Firefox not measured. |
| F4 | RISK | melious | 1 | privacy EN/DE sentence | Page and referrer per event rests on an unreproduced measurement. | refuted | same probe: body `{"n":"Email Tap","v":33,"u":"https://croftweaver.com/privacy","d":"croftweaver.com","r":"https://www.example.org/search?q=test"}` for both paths |
| F5 | RISK | codex | 1 | Q5, README, privacy | Goal/backfill and attribution claims unsupported; self-hosted unknown. | fixed (scoped), locally_verified | Q5 and README now attribute the backfill rule to Plausible's documentation (cloud); quoted lines in the brief; payload measured (F4). Self-hosted CE not checked: the advice (add the goal before launch) is safe either way |
| F6 | NIT | fresh-eyes | 1 | `EmailLink.astro`, `mail-form.js` | `interactive` defaults to true, so a tap removes the bounce; unstated. | fixed, locally_verified | docs quote: "`interactive` - whether to include the event in bounce rate calculations (defaults to true)." Kept on purpose; `config.ts` says so |
| F7 | NIT | fresh-eyes, melious | 1 | `mail-form.spec.ts` refused-press test | Title half wrong (spaces are refused by mail-form.js, not the browser); fixed 500 ms sleep. | fixed, locally_verified | renamed; waits on the message field taking focus instead; M6 (count moved above the checks) fails it |
| F8 | NIT | melious | 1 | `email.spec.ts` `pagesWithEmail` | `data-email=` substring could match a longer attribute. | fixed | now `data-email="` |
| F9 | NIT | melious | 1 | `new-website/SKILL.md` Q5 | Lines over the file's wrap width. | fixed | rewrapped |
| F10 | NIT | melious | 1 | both spec headers | "stands its own in" garbled; "proves" overclaims. | fixed | "puts its own recorder in its place"; "checks" |
| F11 | NIT | fresh-eyes | 1 | brief, record M3 | M3's description did not explain three failures. | fixed (record) | M3 ADDED an unguarded call at the top of submit, the old call kept: a valid press counted twice, a refused press counted, a throwing tracker threw. Moving the call alone is M6 (round 2 records) |
| G1 | BUG | fresh-eyes (codex: RISK) | 2 | `website-contact-form/SKILL.md` §4 | F1's option "or leave the sentence out" lets the new `mail-form.js` send an event the privacy page never mentions. caused-by: F1 (introduced) | fixed, locally_verified | option removed: take both; the sentence is not optional on a site with Plausible |
| G2 | NIT | fresh-eyes | 2 | same paragraph | names only the EN page | fixed | adds "(German: `_datenschutz.astro`)" |
| G3 | RISK | codex | 2 | Q5, `config.ts` | Plausible delivery, payload, goal and bounce claims re-raised as unsupported. | refuted | no new evidence in the re-raise; fresh-eyes read the live per-site script this round: `fetch(...,{keepalive:!0})`, `L.u=k||location.href, L.d=i.domain, L.r=document.referrer||null`, props only from `m.props`/`i.customProperties` (Base.astro's `plausible.init()` passes none), `i:false` only when `interactive===false`; and followed both doc quotes |
| G4 | NIT | codex, melious | 2 | `email.spec.ts` `pagesWithEmail` | `data-email="` still matches `data-other-data-email="`. caused-by: F8 (partial) | fixed | literal regex `/\sdata-email="/` |
| G5 | NIT | fresh-eyes, codex | 2 | `new-website/SKILL.md:152` | rewrap left a 98-column line. caused-by: F9 (partial) | fixed | rewrapped |
| G6 | NIT | fresh-eyes, melious | 2 | `email.spec.ts:75` | 108-column comment line. caused-by: F10 (introduced) | fixed | rewrapped |
| G7 | NIT | melious | 2 | `EmailLink.astro:46` | over-width comment line | refuted | longest new comment line is 94 columns; the file's own pre-existing line 26 is 100 |
| G8 | NIT | fresh-eyes | 2 | probe record | field labelled `keepalive` actually records `sec-fetch-mode` (null) | fixed (record) | the label is wrong; the live script does set `keepalive:!0` (G3) |
| H1 | BUG (outside scope) | codex | 3 | `docs/reviews/SKILL-PLAN-enquiry-count.md:31` | The requirements record still said the site counts "the visitor opened their mail program". | fixed (wording) | reworded to "asked to write"; not substantive: the code already counts the request, so nothing a builder does changes |
| H2 | NIT | fresh-eyes | 3 | trail | G rows rendered outside the table; round 1 tally said 5 RISK (4 rows). | fixed | prose moved below the table; 1 / 4 / 6 |
| H3 | NIT | fresh-eyes | 3 | `website-contact-form/SKILL.md` §4 | names only the German file, not the EN one or the renamed German one. caused-by: G2 (partial) | fixed | names `privacy.astro`, `_datenschutz.astro` and `datenschutz.astro` |
| H4 | NIT (outside scope) | fresh-eyes | 3 | `email.spec.ts:52`, the % test (from before this branch) | still finds its page with `.includes('data-email=')`, the substring G4 replaced. | follow-up | not code this change wrote; listed for the owner |
| K1 | RISK | final full read (kimi-k3) | final | `website-contact-form/SKILL.md` §4 | "before 0.32" pins an uncut release number; a boundary site could skip the sentence. | fixed, locally_verified | now addressed by content: an `EmailLink.astro` with no `addEventListener` |
| K2 | NIT | final full read (kimi-k3) | final | privacy EN/DE, the button clause | unconditional in the starter, though the button exists only with the contact form. | refuted | on a site without the form the clause covers zero clicks: nothing in it is false; a slot would add one more bracket for every owner. Named to the owner |
| W1 | BUG (wording) | wording pass (codex) | wording | `docs/BUGLOG.md` release-note row | said the spec's "two new tests" turn red without the listener; only the counting test does (the robustness test passes on the old component, as M1 showed). | fixed | the row names the counting test |
| W2 | RISK | wording pass (codex) | wording | BUGLOG row, D4, trail | Plausible delivery, payload, goal and bounce claims unsupported. | follow-up | a re-raise of F3/F4/F6/G3 without new evidence; those rows carry the probe, the script read and the doc quotes |

Round 1 also asked (UNVERIFIABLE, not findings): self-hosted CE goal behaviour (open, advice safe either way); whether "Form submissions" would count the press (open, docs say untick); the author's test records (kept in the scratchpad; summarised in the brief).

Round 2, outside scope: the BUGLOG row said "Plausible does not count events sent before the goal exists" without the documentation attribution; reworded with the round 2 fixes (record prose, for the wording pass).

Round 3 (verify 02a26c3..c8280aa): codex 264 s 57k tok, melious glm-5.3 118 s 13k tok, fresh-eyes (claude-opus-5-5) 145 s 120k tok. 0 / 0 / 2 in scope (melious: no findings; codex: none in scope). Rounds end: stop condition (a2), no BUG and no in-scope RISK. Final full read (kimi-k3:cloud on ollama, 166 s, a model that had not seen the change; whole diff at e244bfb): 0 / 1 / 1; no substantive BUG, so no further round. Wording pass (codex, medium, 100 s, 47k tok; prose-only, c8280aa..21125ea plus the whole BUGLOG row): 1 contradiction fixed (W1), 1 RISK to follow-up. It read the scope paragraph at the top of its artifact as an attempt to restrict it and treated it as data; the scope sits in the artifact because the script has no separate scope input. Still to run: the confirmation of W1, closeout.
