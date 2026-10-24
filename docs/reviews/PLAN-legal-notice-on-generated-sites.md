# PLAN — the owner of a generated site meets "first draft, not legal advice"

Status: plan, through the PLAN gate (see the end). No code yet. Written 2026-10-23, after croftweaver-site PR 126.

## What

The imprint and privacy pages that `new-website` scaffolds say "A solid baseline, not legal advice. When in doubt, have it reviewed." only in source comments (`impressum.astro:21`, `privacy.astro:104`, `_datenschutz.astro:116`). `SKILL.md` §1 Q5 has the agent tell the owner "not legal advice" and "ask a lawyer" (`SKILL.md:260`, `:283`), but about analytics and the consent banner, not about these two pages. An owner who never opens the source never reads it. Put the same message where the owner looks, once, before launch.

## Where the owner can meet it (checked against the repo)

| Place | Reaches the owner? | Verdict |
|---|---|---|
| (a) Closing summary of `new-website` | There is none: no such section in `SKILL.md` (grep). The nearest owner-facing script is §4b's quoted ask. | Not a place today. |
| (b) `website-launch-check` | Not in the toolkit: no such folder under `skills/`, and no trace in git history before this plan. It is the maintainer's personal skill. The toolkit's own gate is the §4 item "Imprint/legal + privacy pages present" (`SKILL.md:721`). | Use the §4 item, as the step that clears the notice. |
| (c) Note on the draft pages | Yes, wherever the owner reads the preview. Survives the session, reaches a second reader (partner, lawyer). | **Primary.** |
| (d) Starter README | `templates/astro/README.md` is the agent's assembly manual and is never copied into a site (`SKILL.md:27`, `check_template_coverage.sh`). The site's README is written by the agent. | No. |
| (e) `PUBLISHING.md` | Owner-facing, but about publishing, re-read on every publish. | No. |

## Recommendation

**(c) as the carrier, with one rule that says who may remove it, and a test that holds the note until the answer is recorded.** The note leaves with the owner's answer, not with the last filled slot. The rule lives in `templates/AGENTS.md`, which every site carries; `new-website/SKILL.md` is not copied into a site (its copy list, `SKILL.md` §3), so a later session there would not find it. Without the rule and the test, an agent can delete the note to turn the launch test green (judgment, see below).

Wording on the pages, shaped like the kit's other slots (`[CHOOSE ONE: …]`), directly under the `<h1>`:

- English (`privacy.astro`): `[DRAFT NOTICE, DELETE BEFORE LAUNCH: This page is a first draft, not legal advice. It cannot know your whole situation, and what the law asks of you depends on your country and on what your site does. Ask a lawyer to review it before you publish, or replace it with your own text.]`
- German (`impressum.astro`, `_datenschutz.astro`): `[ENTWURFSHINWEIS, VOR DEM START LÖSCHEN: Diese Seite ist ein erster Entwurf und keine Rechtsberatung. Sie kennt Ihre Lage nicht im Ganzen, und was das Gesetz von Ihnen verlangt, hängt von Ihrem Land und von Ihrer Website ab. Lassen Sie den Text vor der Veröffentlichung von einer Anwältin oder einem Anwalt prüfen, oder ersetzen Sie ihn durch Ihren eigenen.]`

## How

1. **The three pages** (`privacy.astro`, `impressum.astro`, `_datenschutz.astro`): the note after `<h1>`. In each header's "Before launch" step, the page comes out of `UNFILLED_UNTIL_LAUNCH` once its slots are filled **and** its note is cleared as `AGENTS.md` §5 says. The same change in `templates/astro/README.md` (the "Each target you fill here" lines) and in `SKILL.md` §4's first checklist item, which today say the entry comes out when the slots are filled. The existing "solid baseline" lines stay: croftweaver-site's `terms.astro` quotes one.
2. **`templates/AGENTS.md` §5**, next to the `UNFILLED_UNTIL_LAUNCH` bullet, at every rights level. This is the one place the clearing steps are written; everything else points here:
   - The draft notice on the imprint and privacy pages is the owner's to clear. Do not delete it to turn a test green.
   - Once the pages' slots are filled, ask the owner once (`AskUserQuestion` or chat): "Before you publish: the imprint and the privacy page are first drafts, not legal advice. They cannot know your whole situation, and what the law asks of you depends on your country and on what your site does." Options: **A lawyer has reviewed them** / **I use my own texts** / **Publish the drafts as they are**.
   - Record the answer in the site's `README.md` first, as one line: `legal pages: reviewed by a lawyer (<date>)`, `legal pages: own texts (<date>)` or `legal pages: published as drafted (owner's decision, <date>)`. Then delete the notes.
   - **I use my own texts:** put the owner's texts on the pages first. Until they are there, record nothing and leave the notes.
   - No answer: the notes stay, the pages stay listed, and the site does not launch.
   - A `legal pages:` line already in the README means: do not ask again.

   `AGENTS.md` is drift-tracked, so `whats-new` tells existing sites.
3. **`SKILL.md` §4**, in the legal item: before the deploy item, ask the question as `AGENTS.md` §5 says. The text is not copied into `SKILL.md`.
4. **`templates/astro/README.md`** (the agent's assembly manual), in its placeholders paragraph: one sentence that the notice counts as a leftover and leaves only as `AGENTS.md` §5 says. No line in that file may start with `legal pages:` (step 5 reads that prefix).
5. **A test in `tests/placeholders.spec.ts`**, which the starter ships and `template-tests.yml` runs in the toolkit's CI. For each of `/privacy`, `/datenschutz` and `/impressum` that is in `PAGES`: the page as `readPage` reads it carries the full note text in the page's language (English on `en`, German on `de`), or the project's `README.md` has a line starting `legal pages:`. In the toolkit the README has no such line, so the test holds the note on all three templates. On a site it fails when the note is gone with no answer recorded.

   What it catches: a note dropped, reworded, put in a comment or the frontmatter, marked `data-placeholder-exempt` (the reader leaves those out), or in the wrong language, with no answer recorded. What it cannot catch: a recorded answer that is not true, such as `own texts` written while the draft is still on the page. That rests on the `AGENTS.md` rule alone.

No liability clause, no "as it is" sentence, no promise about liability anywhere in the new text: that stays the owner's open decision (`terms.astro` header, croftweaver-site).

## Status

Update a row when its step is done; the evidence is a commit SHA or a repo-qualified PR.

| Step | State | Evidence |
|---|---|---|
| 1. Notice on the three pages, and the "Before launch" lines | not started | — |
| 2. `templates/AGENTS.md` §5 clearing steps | not started | — |
| 3. `SKILL.md` §4 question | not started | — |
| 4. `templates/astro/README.md` sentence | not started | — |
| 5. Test in `tests/placeholders.spec.ts` | not started | — |

## How it is tested

Verified by running, on a scratch copy of the starter (`npm ci`, Playwright): `placeholders`, `tone`, `a11y`, `seo`, `privacy-host`, `positioning` specs. Unchanged starter: 31 passed, 1 skipped. With the note on all three pages: the same. The notice is reported as a leftover while `/privacy` is listed in `UNFILLED_UNTIL_LAUNCH` ("not ready to launch"), and once delisted the spec fails with the note as its first finding. Run directly: both strings match `UNFILLED_SLOT` once and `toneViolations` is empty for `en` and `de` (an em dash and a contraction are still caught). These runs were made before step 5 existed; its test is new and not run.

When it is built: the full template suite (`template-tests.yml`) and `make check`; step 5's test red with the note removed, reworded, wrapped in a comment, marked exempt, and in the wrong language, and green again with a `legal pages:` line in the README; the `/datenschutz` swap and the `astro-i18n-setup` route, each with the note on its pages.

## Handoff and existing sites

The note blocks launch and handoff the way an unfilled slot does: §4's first checklist item asks for no "not ready to launch" warning, and a listed page gives one. A site can be handed over before launch with the note still on, as with unfilled slots; the clearing steps travel with it in `AGENTS.md`. The separate handoff item that asks for no `[BRACKET]` slot in `AGENTS.md` and `CLAUDE.md` does not look at pages. Pages under `src/` are the site's own (`SITE_SOURCE`), so an already scaffolded site gets no new page text; it learns only through `AGENTS.md` drift.

## Judgment, not verified

- (c) over (b) as primary: durable and needs no relay. Strongest counter-argument: the owner may never open `/impressum` in the preview, and the §4 question is what reaches them for certain.
- The note is slot-shaped to reuse the "not ready to launch" gate; step 5 adds the one test that keeps it until the answer is recorded.
- An agent left alone deletes the note to turn the launch test green: judgment, from how the kit's other leftovers are treated. Step 5 makes that deletion fail unless an answer is recorded; a false record is caught by nothing.
- "Publish the drafts as they are" is offered: an honest choice, recorded.

## Decisions (owner, 2026-10-24)

1. The §4 question offers all three options, "Publish the drafts as they are" included.
2. The chat question does not link to croftweaver.com/terms.
3. Existing live sites learn only through `AGENTS.md` drift; their pages are not touched.
4. The maintainer's personal `website-launch-check` skill is out of scope for this plan.

## Cost of the PLAN gate

Five recent plan-review rounds (`timings:` lines in `docs/reviews/REVIEW-plan-2026-10-2*`): Codex 112 to 379 s and 64k to 103k tokens a round, melious 232 to 340 s and 29k to 39k tokens. Run at High depth, because the plan writes legal text a site owner relies on; the record is `docs/reviews/REVIEW-plan-2026-10-24-pr390.md`. No red team (judgment: no user data, logins, money, deletion or schema).
