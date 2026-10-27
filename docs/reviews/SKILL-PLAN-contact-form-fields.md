# Plan: website-contact-form takes a page's own fields and a hint

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-10-27 | this file |
| 2 | Plan review gate (Normal: a SKILL.md, a shipped component and test) | ✅ 2026-10-27: 3 rounds, Codex alone (melious out of balance), 2 BUG and 5 RISK, none open | `docs/reviews/REVIEW-plan-2026-10-27-contact-form-fields.md` |
| 3 | The maintainer's go | ✅ 2026-10-27, in chat: "Go: build the contact-form upgrade from the reviewed plan, Codex-alone review is fine." | — |
| 4 | Build: component, spec, SKILL.md, CI job, BUGLOG row (one PR) | ✅ built 2026-10-27: DIFF review 5 rounds, Codex alone, 2 BUG and 4 RISK, none open | branch `feat/contact-form-fields`, `docs/reviews/REVIEW-diff-2026-10-27-contact-form-fields.md` |

## What and why

A client site (an architecture office; the repo keeps client names out) rebuilt its contact page
on 2026-10-27. The visitor says whether it is a new or a running project (optional), may add the
place and a phone number, and writes the message; a hint above the message box says what helps,
and changes with the choice. Building it needed three things the skill does not give today:

1. **A place for fields.** `MailForm.astro` has no slot, so a page cannot add a field without
   editing the component. The site added two slots. `mail-form.js` already sends a filled text
   field as "Label: value" and a ticked radio button or checkbox as its label alone, so for the
   fields this plan recommends the script needs no change. A list (`select`) sends its chosen
   option's text, so an empty "Please choose" entry would arrive as an answer (round 1 BUG):
   SKILL.md says to ask a choice with radio buttons and to use no list at all (DIFF round 1: a list always has an entry chosen, so an untouched one sends an answer).
2. **Guidance on asking for more.** §2 step 5 says where a field goes, not how to ask. The site
   followed a short research pass (below); the skill should carry it so the next site does not
   redo it.
3. **A spec that fits a form with fields.** The template's label-and-Tab test counts exactly two
   controls, so any added field turns it red and each site edits the test by hand.

Research the guidance rests on, each line read on the live page on 2026-10-27:

- GOV.UK Design System, radios (https://design-system.service.gov.uk/components/radios/): "Do
  not pre-select radio options", and "Users cannot go back to having no option selected once
  they have selected one, without refreshing their browser window." Also: "Group radios together
  in a `<fieldset>` with a `<legend>`".
- GOV.UK, question pages (https://design-system.service.gov.uk/patterns/question-pages/): add
  "(optional)" to the labels of optional fields, to the legend for radios; "Never mark mandatory
  fields with asterisks."
- W3C WAI, grouping controls (https://www.w3.org/WAI/tutorials/forms/grouping/): "Radio button
  groups should always be grouped using `<fieldset>`."
- Nielsen Norman Group, "Placeholders in Form Fields Are Harmful"
  (https://www.nngroup.com/articles/form-design-placeholders/): clear, visible labels outside
  empty fields.

A survey of nine German architecture and site-management contact pages was done by the session
that built the client page; it is not re-checked here and is not quoted in SKILL.md.

The one place the skill departs from GOV.UK: it puts "(optional)" beside the label, not in it,
because the script uses the label's text in the mail ("Town: Berlin", not "Town (optional):
Berlin"). A radio group keeps it in the `legend`, which the mail never shows. Once an optional
radio is picked it cannot be unpicked; here that costs one line the visitor can delete in their
mail program, and SKILL.md says so.

## How

**`templates/MailForm.astro`.** A default slot right after `<form>` for fields before the
message, and a named slot `hint`, rendered only when used, as
`<span class="mail-form-hint" id="mail-form-hint">` between the message's label and its box; the
box gets `aria-describedby="mail-form-hint"` then, and none otherwise. Astro scopes a component's
styles to its own elements, and slotted fields carry the page's scope. Checked on the client
site's build (`dist/kontakt.html`, 2026-10-27): `<input id="ort" … data-astro-cid-657w5j3a>`
(the page's) against `<textarea id="mail-form-message" … data-astro-cid-yaw7alfq>` (the
form's). The build checks it again on the starter (see "How it is tested"). So the
form's field rules become `.mail-form :global(…)` rules: an added text field, select, radio
group (`fieldset`, `legend`) and an "(optional)" note (class `mail-form-optional`) look like the
message field with no page CSS. The page styles only what is its own, such as a hint that
switches.

**`templates/mail-form.spec.ts`.** A new constant `ADDED`: the labels of the fields a page adds,
one per Tab stop, in order (a radio group by its first option; empty by default). The Tab test
starts from a focus point placed just before the form (a `tabindex="-1"` element the test
inserts), so the first Tab lands on the form's first stop and a field left out of `ADDED`, at
the front or anywhere, fails it (round 1: starting on `order[0]` hid a missing first field).
It walks `ADDED`, then the message, then the button. Its count of exactly two controls becomes
"every control in the form has a label", which is what the count was for. One new test, run only
when the page fills the `hint` slot: the message box's accessible description is the hint's
visible text. A site that fills the slot makes sure the hint is there by its page spec (below);
the template cannot know. Nothing else in the spec changes.

**`SKILL.md`.** §2 step 5 becomes a short section "Adding fields": the slot, with an example in
English (an optional radio group, an optional text field, a hint); the rules from the research,
each with its source: ask only what the mail program does not already carry (no name or email
fields); a choice as radio buttons in a `fieldset` with a `legend`, none preselected, each option's
label readable alone, since the mail shows the label without the legend; "(optional)" outside the
`<label>` and tied to the field with `aria-describedby`, so the mail line stays "Town: …"; no
asterisks; a visible hint above the box, not a placeholder; a hint that follows a choice can be
CSS alone (`:has(#id:checked)`); no promise the owner has not made (a reply time, a free first
talk). Then a page-level spec pattern: enter through the button and check the exact mail body
with the fields filled, and the message alone with none. The privacy note in §4 stays as is (an
added field that asks for more personal data is named there).

**CI (`contact-form-skill` job).** The German form (on `/impressum`) gets the SKILL.md example in
German (a radio group, an optional field, a hint), and its spec copy sets `ADDED`. The English
form on the home page stays bare and self-closing, so its greps and the job's last step, which
edits that tag to break the build three ways, keep working unchanged (round 1). The German
page's install line and its grep (`<MailForm … subject="Anfrage Bauvorhaben" />`) change to
the paired form with the example inside, and the grep checks the opening tag and one slotted
field (round 2). The job also
installs the page-level spec pattern from SKILL.md for the German page: it ticks a radio,
fills the field and the message, presses the button and checks the exact mail body; then the
message alone with nothing chosen; then the hint's text before and after each choice. So both
shapes run, a form with no slot used and one with all of them. Built: the CI page and spec are
the SKILL.md example and spec translated to German (the English home form must stay bare), plus
one test that a slotted field takes the form's look (computed border and display equal to the
message box's).

**`docs/BUGLOG.md`.** A "next release notes" row: existing sites with the form keep their own
`MailForm.astro` and spec; to add fields they take the new component and set `ADDED` in place of
editing the Tab test. Closes when the line is in a release's notes.

## Not in scope

No change to `mail-form.js` or `mail-form-text.ts`. No required extra fields (the site made its
choice optional: guides say ask only what is needed, and a required choice would add a refusal
path the script does not have). No new template file: the page example and page-spec pattern
live in SKILL.md.

## How it is tested

- CI's `contact-form-skill` job: `npm run check` and the whole starter suite with both forms, so
  the bare form proves nothing changed for an existing install, and the filled one proves the
  slots, the labels check, the Tab order through `ADDED` and the hint's description.
- Before round 1 of the DIFF review: the same job run by hand on a copy of the starter, and the
  tests shown to fail once each: the first entry of `ADDED` left out, two entries swapped, a
  field without a label, the hint not wired to the box, and (page spec) the radio line dropped
  from the expected body. The built page is read once for the scope attributes and for the
  `:global` rules reaching a slotted input (its computed border and display).
- The client site's page and specs use the same two slots (its PR, not re-run here); the
  component this PR ships is checked by CI, not by that site.
- `make check` (skill budgets, template coverage, clean names).
