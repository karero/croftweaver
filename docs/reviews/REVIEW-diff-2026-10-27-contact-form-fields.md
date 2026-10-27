# Review trail: diff, contact form takes a page's own fields and a hint

Plan: `docs/reviews/SKILL-PLAN-contact-form-fields.md` (PLAN gate: 3 rounds, Codex alone, no BUG
open). DIFF gate, Normal depth (a SKILL.md, a shipped component and spec, a CI job). Seat: Codex;
GLM 5.3 on melious was out of balance all day, and the maintainer approved Codex alone in chat
("Codex-alone review is fine").

## Before round 1: the CI job run by hand

The `contact-form-skill` job's own steps, taken from the workflow file and run in a
`node:24-bookworm` container (Linux and Node 24, as CI uses), on this branch's files.

- Install, type check and the whole starter suite: `0 errors`; `149 passed`, `2 skipped`
  (`mail-form.spec.ts` "a hint above the message", skipped as meant on the English form, which
  has no hint; `positioning.spec.ts`, which skips on every fresh starter). Both new page tests,
  the `ADDED` Tab test and the hint test passed on the German form.
- The break-the-build step (no subject, no language, a language with no texts): passed.
- Settles the plan's pending U1 and U2: slotted fields take the form's look through the
  `:global` rules (the computed-style test, and its mutation below); the radio group is one Tab
  stop; the hint's accessible description follows the choice.

Mutations, each applied to the installed site, the named spec run, then put back:

| Mutation | Result | Caught by |
|---|---|---|
| `ADDED` misses its first entry (`['Ort']`) | KILLED | `mail-form.de.spec.ts` Tab test |
| `ADDED` in the wrong order | KILLED | the same |
| an unlabelled input in the slot | KILLED | the same (it also adds a Tab stop, so the run does not show which of the test's two checks fired) |
| `aria-describedby` dropped from the message box | KILLED | `mail-form.de.spec.ts` hint test; `kontakt.de.spec.ts` hint test |
| the form's field rules back to scoped (no `:global`) | KILLED | `kontakt.de.spec.ts` look test |
| `mail-form.js` stops sending a ticked radio's label | KILLED | `kontakt.de.spec.ts` body test |
| none (control) | passed | both specs |
