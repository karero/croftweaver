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
| 1 | e1ab9d7 | codex (gpt-6.1-sol, config effort) 293 s 91k tok; melious glm-5.3 261 s 21k tok; fresh-eyes (claude-opus-5-5) 204 s 127k tok | 1 / 5 / 6 | one wording BUG fixed; payload and delivery claims measured; next round owed by the fixes |

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

Round 1 also asked (UNVERIFIABLE, not findings): self-hosted CE goal behaviour (open, advice safe either way); whether "Form submissions" would count the press (open, docs say untick); the author's test records (kept in the scratchpad; summarised in the brief).
