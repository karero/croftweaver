# Plan: the contact form's mail starts with a greeting and ends with a sign-off

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-10-27 | this file |
| 2 | Plan review gate (Normal: a SKILL.md, a shipped component, script and spec) | ✅ 2026-10-27: 2 rounds, Codex alone (melious out of balance), 3 RISK, none open | `docs/reviews/REVIEW-plan-2026-10-27-contact-form-greeting.md` |
| 3 | Build (one PR, on top of karero/croftweaver#431) | 🔄 the maintainer's go in chat: "Do this immediately after" (#431) | branch `feat/contact-form-greeting` |

## What and why

The maintainer, 2026-10-27, in chat: the form's mail should carry a greeting and a sign-off,
and the skill should ask the owner for the greeting. His answers to three questions: the
greeting is set by the owner, once per form ("Sehr geehrte Frau Muster,"); the sign-off is
the line alone, without a comma and without a name ("Freundliche Grüße"); in English "Dear
Mr Smith," and "Kind regards". The visitor's name comes from their mail program and
signature, as today: no name field.

This reverses a rule the skill states today (§1 and §2 step 5: "they greet and sign as they
like"). Why it helps: a visitor who writes a two-line message still sends a mail that reads
as a letter, and most visitors write no greeting of their own in a form.

## How

**The mail body.** In this order, lines joined with `\r\n` as now:

```
<greeting>

<message as typed, trimmed>

<added fields, one per line, if any>

<sign-off>
```

The sign-off comes last, after the added fields, so the mail ends the way a letter ends
(the maintainer chose this over the sign-off under the message, 2026-10-27).

**`MailForm.astro`.** A new required prop `greeting`, the mail's first line, with its
punctuation as the owner wants it ("Sehr geehrte Frau Muster,", "Hallo Anna,", "Dear Mr
Smith,"). The build stops without it, with a message naming the skill's step, as it does
for `subject`. It goes into the HTML as `data-greeting`, like `data-subject`. A missing
greeting is not defaulted: a generic line would go out unnoticed on every mail.

**`mail-form-text.ts`.** A new text `signoff` per language: `de: 'Freundliche Grüße'`, `en:
'Kind regards'`. No comma, in either language: the maintainer's choice (2026-10-27), so the
two languages match. `npm run
check` fails while a language lacks it, as for every text. A site that wants "Viele Grüße"
edits its own copy.

**`mail-form.js`.** Builds the body as above from `data-greeting`, the message, the fields
and `data-signoff` (rendered by the component from `TEXT`). Nothing else changes: the empty
message check, the encoding, the event.

**The visitor sees it.** The mail program opens the mail as a draft, so the visitor sees the
greeting and the sign-off before pressing Send. Which mail programs then add the visitor's
own signature, and whether a very long message arrives cut at the end (which would cut the
sign-off first), was not measured: BUGLOG row "`LIMITS.message`" already holds the length
question, and SKILL.md §5 says so. The note under the box (`TEXT.note`) is read against the
new behaviour; if its wording no longer fits, it changes in both languages.

**`SKILL.md`.** §2 step 2 asks the owner for the greeting next to the subject: whom the
visitor addresses, in the site's form of address (Sie or du), with the punctuation it wants.
Propose one ("Sehr geehrte Frau Muster," for a Sie site with one named owner; "Sehr geehrte
Damen und Herren," for a firm with no one person; "Hallo Anna," on a du site) and let the
owner choose. §1's "how it works" and step 5's "they greet and sign as they like" are
rewritten. Step 4 adds `GREETING` beside `PAGE`, `TO` and `SUBJECT`. Every example gets the
prop: the install example in step 2 and the one in "Adding fields". The page spec in "Adding
fields" expects the new body (greeting, message, fields, sign-off; and greeting, message,
sign-off with nothing added). The `EmailLink` under the form (a blank mail) stays without a
greeting: not in scope.

**`mail-form.spec.ts`.** A new constant `GREETING`, set like `SUBJECT`; the install test
fails while it is empty. Every exact-body expectation becomes greeting, message, fields,
sign-off. One new test: a greeting with characters that need encoding (`&`, `,`, umlauts)
arrives as written. The tone test already covers the new `signoff` text.

**CI.** Each `<MailForm>` in the `contact-form-skill` job gets a `greeting`, each spec copy
its `GREETING`; the break-the-build step gains one case: a form without a greeting stops the
build with its message. The German page spec's expected bodies change.

**BUGLOG.** A "next release notes" row: existing sites keep their form. One that wants the
greeting takes the new `MailForm.astro`, `mail-form.js` and `mail-form-text.ts` (keeping any
language or text of its own), and sets `greeting` on each form. Its spec is merged by hand,
not copied over: keep the site's `PAGE`, `TO`, `SUBJECT`, `LANG`, `ADDED` and any edits, add
`GREETING`, and take the new expected bodies. A site's own page spec takes the new bodies
too. The spec and the script go together: the new spec fails on the old script.

## How it is tested

- CI's `contact-form-skill` job run by hand in a Linux container before round 1, as for the
  fields PR, with mutations shown to fail once each: greeting dropped from the body,
  sign-off dropped, the sign-off placed before the fields, the build check for a missing
  `greeting` removed; and `signoff` removed from one language once, to see `npm run check`
  fail.
- `make check`.
