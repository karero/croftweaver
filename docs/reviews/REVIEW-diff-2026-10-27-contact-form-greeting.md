# Review trail: diff, greeting and sign-off in the contact form's mail

Plan: `docs/reviews/SKILL-PLAN-contact-form-greeting.md` (PLAN gate: 2 rounds, Codex alone,
3 RISK, none open). DIFF gate, Normal depth. Seat: Codex; GLM 5.3 on melious out of balance,
Codex alone approved by the maintainer in chat for the fields PR this builds on; the same
holds here, and the PR says so.

## Before round 1: the CI job run by hand

The `contact-form-skill` job's own steps in `node:24-bookworm`, on this branch's files:
`npm run check` 0 errors; `151 passed`, `2 skipped` (the hint test on the English form, which
has no hint; `positioning.spec.ts`, as on every fresh starter); the break-the-build step,
now with a form without a greeting, passed.

| Mutation | Result | Caught by |
|---|---|---|
| greeting dropped from the body (`mail-form.js`) | KILLED | `mail-form.spec.ts` main body test; `kontakt.de.spec.ts` both body tests |
| sign-off dropped | KILLED | the same |
| sign-off placed before the fields | KILLED | `mail-form.spec.ts` added-fields test; `kontakt.de.spec.ts` body test |
| `MailForm.astro`'s missing-greeting check removed, and `greeting.trim()` made `greeting?.trim()` so nothing else stops the build | the build passes without a greeting, so the job's "a form without a greeting was built" error fires | the break-the-build step. With the check removed alone, the build fails on a `TypeError` instead, and the step's grep for `MailForm: pass greeting="…"` fires ("the build failed, but not on the missing greeting"): not run, read from the step (round 1, G4) |
| `signoff` removed from `en` | `npm run check` fails: `ts(2339): Property 'signoff' does not exist` | the type check |
| none (control) | passed | the three specs |

| Round | Seats | Findings | Time, tokens |
|-------|-------|----------|--------------|
| 1 | Codex, GLM 5.3 (melious had balance again) | 1 BUG (evidence), 3 NIT | Codex 170 s, 62,229; GLM 396 s, 35,163 |

## Round 1

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| G4 | BUG | Codex | The evidence row for the removed greeting check is wrong as written: removing the check alone leaves `greeting.trim()`, which throws | fixed: the row says the mutation also made `.trim()` optional, and what the step does in the other case | trail, mutation table |
| G5 | NIT | GLM | The new script with an old component writes "undefined" for greeting and sign-off | fixed: the BUGLOG release-notes row says the three files go together and why (corrected in round 2: blank lines, not "undefined", G8) | BUGLOG row |
| G6 | NIT | GLM | `g` unannotated in the encoding test | fixed: `g: string` | spec |
| G7 | NIT | GLM | CI greps every injected setting but the page spec's `greeting` | fixed: one grep line | workflow |
