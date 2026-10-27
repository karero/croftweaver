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
| `MailForm.astro`'s missing-greeting check removed | the build passes without a greeting, so the job's "a form without a greeting was built" error fires | the break-the-build step |
| `signoff` removed from `en` | `npm run check` fails: `ts(2339): Property 'signoff' does not exist` | the type check |
| none (control) | passed | the three specs |
