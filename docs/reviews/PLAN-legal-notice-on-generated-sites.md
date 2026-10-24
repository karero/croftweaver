# PLAN — the owner of a generated site meets "first draft, not legal advice"

Status: draft for the PLAN gate. No code yet. Written 2026-10-23, after croftweaver-site PR 126.

## What

The imprint and privacy pages that `new-website` scaffolds say "A solid baseline, not legal advice. When in doubt, have it reviewed." only in source comments (`impressum.astro:21`, `privacy.astro:104`, `_datenschutz.astro:116`; `SKILL.md:260`, `:283`). An owner who never opens the source never reads it. Put the same message where the owner looks, once, before launch.

## Where the owner can meet it (checked against the repo)

| Place | Reaches the owner? | Verdict |
|---|---|---|
| (a) Closing summary of `new-website` | There is none: no such section in `SKILL.md` (grep). The nearest owner-facing script is §4b's quoted ask. | Not a place today. |
| (b) `website-launch-check` | Not in the toolkit: no such folder under `skills/`, no trace in git history. It is the maintainer's personal skill. The toolkit's own gate is the §4 item "Imprint/legal + privacy pages present" (`SKILL.md:721`). | Use the §4 item, as the step that clears the notice. |
| (c) Note on the draft pages | Yes, wherever the owner reads the preview. Survives the session, reaches a second reader (partner, lawyer). | **Primary.** |
| (d) Starter README | `templates/astro/README.md` is the agent's assembly manual and is never copied into a site (`SKILL.md:27`, `check_template_coverage.sh`). The site's README is written by the agent. | No. |
| (e) `PUBLISHING.md` | Owner-facing, but about publishing, re-read on every publish. | No. |

## Recommendation

**(c) as the carrier, with one rule in §4 that says who may remove it.** The note leaves with the owner's answer, not with the last filled slot. Without that rule an agent deletes the note to turn a test green (judgment, see below).

Wording on the pages, shaped like the kit's other slots (`[CHOOSE ONE: …]`), directly under the `<h1>`:

- English (`privacy.astro`): `[DRAFT NOTICE, DELETE BEFORE LAUNCH: This page is a first draft, not legal advice. It cannot know your whole situation, and what the law asks of you depends on your country and on what your site does. Ask a lawyer to review it before you publish, or replace it with your own text.]`
- German (`impressum.astro`, `_datenschutz.astro`): `[ENTWURFSHINWEIS, VOR DEM START LÖSCHEN: Diese Seite ist ein erster Entwurf und keine Rechtsberatung. Sie kennt Ihre Lage nicht im Ganzen, und was das Gesetz von Ihnen verlangt, hängt von Ihrem Land und von Ihrer Website ab. Lassen Sie den Text vor der Veröffentlichung von einer Anwältin oder einem Anwalt prüfen, oder ersetzen Sie ihn durch Ihren eigenen.]`

## How

1. The three pages: the note after `<h1>` and one step in each header ("clear the note as `SKILL.md` §4 says"). The existing "solid baseline" lines stay: croftweaver-site's `terms.astro` quotes one.
2. `SKILL.md` §4, in the legal item: once the slots are filled and before the deploy item, ask the owner once, like §4b (`AskUserQuestion` or chat). Text: "Before you publish: the imprint and the privacy page are first drafts, not legal advice. They cannot know your whole situation, and what the law asks of you depends on your country and on what your site does." Options: **A lawyer has reviewed them** / **I use my own texts** / **Publish the drafts as they are**. Record the answer in the site README first (`legal pages: reviewed by a lawyer`, `own texts`, or `published as drafted (owner's decision, <date>)`), then delete the notes. A README line already there means: do not ask again.
3. `templates/AGENTS.md` §4: "The draft notice on the imprint and privacy pages is the owner's to clear. Do not delete it to turn a test green." `AGENTS.md` is drift-tracked, so `whats-new` tells existing sites.
4. One sentence in the starter README's placeholders paragraph: the notice counts as a leftover.

5. One guard in `make check`: each of the three template pages carries exactly one notice (`[DRAFT NOTICE,` or `[ENTWURFSHINWEIS,`). Without it, a reworded or dropped note would stop being gated and no test would say so.

No liability clause, no "as it is" sentence, no promise about liability anywhere in the new text: that stays the owner's open decision (`terms.astro` header, croftweaver-site).

## Status

Update a row when its step is done; the evidence is a commit SHA or a repo-qualified PR.

| Step | State | Evidence |
|---|---|---|
| 1. Notice on the three pages | not started | — |
| 2. `SKILL.md` §4 question | not started | — |
| 3. `templates/AGENTS.md` §4 rule | not started | — |
| 4. Starter README sentence | not started | — |
| 5. `make check` guard | not started | — |

## How it is tested

Verified by running, on a scratch copy of the starter (`npm ci`, Playwright): `placeholders`, `tone`, `a11y`, `seo`, `privacy-host`, `positioning` specs. Unchanged starter: 31 passed, 1 skipped. With the note on all three pages: the same. The notice is reported as a leftover while `/privacy` is listed in `UNFILLED_UNTIL_LAUNCH` ("not ready to launch"), and once delisted the spec fails with the note as its first finding. Run directly: both strings match `UNFILLED_SLOT` once and `toneViolations` is empty for `en` and `de` (an em dash and a contraction are still caught). The starter specs need no edit: the per-page placeholders test reads the rendered page, which is the real entry. The new guard (step 5) is the test that can fail when someone removes the note from a template.

Not run: the full suite, `make check`, the `/datenschutz` swap (the German string was checked with the German rules only), the `astro-i18n-setup` route.

## Handoff and existing sites

A visible note does not break handoff: the handoff item asks for no `[BRACKET]` slot in `AGENTS.md` and `CLAUDE.md`, not in pages. The note blocks a launch only as the slots do. Pages under `src/` are the site's own (`SITE_SOURCE`), so an already scaffolded site gets no new page text; it learns only through `AGENTS.md` drift.

## Judgment, not verified

- (c) over (b) as primary: durable and needs no relay. Strongest counter-argument: the owner may never open `/impressum` in the preview, and the §4 question is what reaches them for certain.
- The note is slot-shaped to reuse the gate; a data attribute plus a new test would be clearer but adds test code.
- "Publish the drafts as they are" is offered: an honest choice, recorded.

## Open questions for the owner

1. Offer the third option, or only "reviewed" and "own texts"?
2. Should the chat question link to croftweaver.com/terms, which carries the MIT "as it is" sentence? Left out here.
3. Existing live sites: accept the `AGENTS.md` route only?
4. The personal `website-launch-check` skill has its own Germany block; add the sentence there too? Not touched.

## Cost of the PLAN gate

Five recent plan-review rounds (`timings:` lines in `docs/reviews/REVIEW-plan-2026-10-2*`): Codex 112 to 379 s and 64k to 103k tokens a round, melious 232 to 340 s and 29k to 39k tokens. This plan edits agent-loaded files, so it is Normal depth at least. Expect 1 to 2 rounds: about 5 to 7 minutes and 100k to 140k tokens a round. No red team (judgment: no user data, logins, money, deletion or schema). Not run.
