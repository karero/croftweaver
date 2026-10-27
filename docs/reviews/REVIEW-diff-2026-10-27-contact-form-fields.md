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

| Round | Seats | Findings | Time, tokens |
|-------|-------|----------|--------------|
| 1 | Codex alone (melious out of balance) | 1 RISK; 5 UNVERIFIABLE groups, all looked at | Codex 189 s, 61,195 |
| 2 | Codex alone (`--verify`, raw run lines as evidence) | 1 RISK; D1, U1, U2 confirmed | Codex 99 s, 41,833 |

## Round 1

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| D1 | RISK | Codex | A list (`select`) always has an entry chosen, so an untouched one adds a line and the template's message-alone tests fail; `ADDED` cannot fix that | fixed: SKILL.md says every added field starts empty and drops the list (a list sends an answer the visitor never gave) | SKILL.md "Every added field starts empty" |
| U1 | — | Codex | Astro scope and `:global` reach unverified | answered: the look test and its mutation, raw output sent as round-2 evidence | evidence file, round 2 |
| U2 | — | Codex | Browser behaviour and mutations: no raw output | answered: the job log and mutation log lines sent as round-2 evidence | the same |
| U3 | — | Codex | Screen-reader speech not shown | narrowed: SKILL.md now claims the accessible description, which the tests check, not speech | SKILL.md "Adding fields" |
| U4 | — | Codex | Cited quotes not checked (no network) | answered: each read on its page 2026-10-27 (plan trail U3) | plan trail |
| U5 | — | Codex | Run provenance | answered: raw lines with the commit they ran on, round-2 evidence | the same |

## Round 2

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| D2 | RISK | Codex | "which screen readers announce with it" still promises speech the tests do not show | fixed: SKILL.md says only that the hint becomes the box's accessible description | SKILL.md "Adding fields" |
| U6 | — | Codex | "a list always has an entry chosen" is too broad (`multiple`) | fixed: narrowed to a single-choice list | the same |
