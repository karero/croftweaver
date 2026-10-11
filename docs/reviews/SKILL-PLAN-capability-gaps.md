# Skill plan — closing five capability gaps

A comparison with other website kits (2026-10-03) found five things this toolkit does
not do yet. This document is the requirements record: the build order, where each step
stands, and scenarios the owner can check without reading code. Where it and the
shipped files disagree, the files win. Names of sites and people stay out of this
public repo on purpose.

## Status

Rebuild this table from `git log`, live branches and open pull requests before trusting
it; a row is only as good as its evidence.

| # | Step | State | Evidence |
|---|---|---|---|
| A1 | Checks: leftovers on the rendered site (`placeholders.spec.ts`) | built and reviewed; catching the starter's example values decided 2026-10-06, not built | karero/website-builder#145, the pull request that carries this row |
| A2 | Checks: the publish gate holds on GitHub's side (`production` ruleset) | not built: probe repo created 2026-10-06, probe not run yet | the owner's `webcroft-production-gate-probe` repo |
| A3 | Checks: deeper message checks | not built: rules chosen 2026-10-06 | — |
| B | Proof: a scorecard each site can publish (`website-scorecard`) | built; verified in a scratch copy of the starter; a CI job installs and runs it on every change | the pull request that carries this row, and its `scorecard-skill` check |
| C | Forms: a contact form with a submission test (`website-forms`) | **dropped 2026-10-08**: the skill and its CI job were removed; a mail-app contact form skill replaces it, planned separately. Section C below is kept as the record of what was built | the pull request that removed it |
| D | Import: bring an existing site under the gate | scenarios only | — |
| E | Install: one-line install, marketplace listing | blocked on the rename; both names claimed on npm 2026-10-06 with placeholder packages | `npm view webcroft`, `npm view create-webcroft` |

## Build order, and why

1. **Checks (A).** Smallest, and everything else leans on it: the proof publishes the
   checks' results, and an import brings a site "under the gate". A gate with holes
   makes both worth less.
2. **Proof (B).** The gap that matters most for trust, and mostly not a building
   problem: several sites already exist, what is missing is a repeatable report and
   each owner's consent to be shown. Second because the report should show the checks
   from step 1.
3. **Forms (C).** Moved ahead of import, because an import needs it: nearly every
   existing site has a contact form, and an import that drops it loses a working
   feature.
4. **Import (D).** The largest piece. Needs A and C.
5. **Install (E).** Last only because it is blocked, not because it matters least: the
   package name depends on a rename that has not landed in this repo, and publishing
   to a registry or a marketplace is the owner's own action. Once the name is settled
   it is small, and worth pulling forward.

The strongest argument against this order: install first, because nobody benefits
from better checks in a kit they did not install, and the packaging could ship under
the current name.

## A. Checks

### A1. Leftovers on the rendered site (built)

Until now only the token `[MISSING:` was caught, and only in the source of `src/` and
`public/`. The starter's own `[BRACKET]` slots on the legal pages and in the manifest
were left to the launch checklist.

| # | Given | Then, when the tests run |
|---|---|---|
| 1 | a freshly scaffolded site, nothing filled | green; privacy page, imprint and manifest are each reported as "not ready to launch" |
| 2 | the home page says "TODO: add the prices", has "Lorem ipsum" inside a closed fold-out, and an image described as "[ALT TEXT]" | red, naming all three; a `[YOUR_API_KEY]` shown as code on the same page is left alone |
| 3 | a "[MISSING: what it offers]" sits in the site description in `src/config.ts` | found on the home page (it reaches the search-result text): red in CI, a warning on the author's own machine (rows 15 and 16) |
| 4 | the company name in the settings is still "Musterfirma GmbH" and shows up only in the structured data | red |
| 5 | the owner empties the exemption list to launch, but the legal pages are not filled | red on all three, each slot listed |
| 6 | the owner fills the privacy page and forgets the list | red: "nothing left to fill but still listed", until the entry is deleted |
| 7 | the entry is deleted | green; the privacy page is checked for good from now on |
| 8 | a German site renames `/privacy` to `/datenschutz` and forgets the list | red: the list names a page that is not checked |
| 9 | the manifest file is removed while still listed | red until the entry is deleted |
| 10 | a form field's hint says "[YOUR NAME]" and the send button is labelled "TODO" | red, naming both |
| 11 | filler text with a line break in it shows up only in the structured data | red |
| 12 | a slot is partly in bold, another is broken across two lines, "Lorem ipsum" is partly in italics | red, naming all three |
| 13 | the manifest file is damaged (not valid JSON) | red: "not checked", instead of passing as "nothing found" |
| 14 | a site scaffolded earlier, whose privacy page still has a slot that starts with a small letter; the owner fills every slot the test reports | red: the page carries a slot the test cannot see |
| 15 | an assistant lacks a fact and writes "[MISSING: year built]" on a page, on its own branch | on that machine: green, with a warning naming the placeholder, so the branch can be pushed and a draft pull request opened |
| 16 | the same branch on GitHub | red, so nothing merges until the placeholder is filled |
| 17 | a "[MISSING: …]" next to a "FIXME" on the same page | red everywhere, for the FIXME |
| 18 | "Regards, [your name]" on a finished page | red |
| 19 | "VER TODO INCLUIDO" on an English page | red: "TODO" in capitals is an author's note |
| 20 | the same words on a Spanish page | green: "todo" is an everyday word there; "TODO:" with a colon is still caught |
| 21 | a form field that says "Type your text here", and the sentence "Request a free sample copy" | green: genuine copy |
| 22 | the push check on the author's machine, pushing the branch from row 15 | lets the push through |
| 23 | the same check where CI is set | refuses |

All 23 were run on 2026-10-04 against a scratch copy of the starter, each failing or
passing for the reason in the table, plus the whole suite (61 passed, on the author's
machine and with CI set), the type check, and the German-only swap following
`_datenschutz.astro`'s own header. The test also checks itself on every run: its rules
and verdicts are pinned by example, and one test plants a leftover on each place the
reading covers, inside a real browser, next to the places that must stay out. 51
deliberate breakages of the test's own logic were each caught and named by it. Run
without exemptions against a copy of one real site built with the toolkit, the first
version found two unfilled slots on each legal page and raised no false alarm.

Rows 10 to 23 come from the review. So do three corrections:
- The starter itself served two slots that start with a small letter (the analytics
  hosting choice on the privacy page and in the German draft), which the rule could
  not see. Both now start with a capital word, and while a page is still listed the
  test fails on any slot of that shape.
- The first version failed on "[MISSING: …]" everywhere, which broke the draft flow in
  `AGENTS.md`: the push check refused the very branch a draft pull request needs.
  Rows 15, 16, 22 and 23 are the fix.
- Several rules flagged genuine copy ("TODO" in Spanish, "Type your text here" in a
  form, "sample copy"). They are narrower now; rows 19 to 21.

Known limits, on purpose:
- A target still listed at launch only produces a warning. The list empties itself as
  pages are filled, and the launch checklist requires it empty, but nothing blocks a
  launch with an entry left. **Waived by the owner on 2026-10-04 until step A2**: the
  publish step is where a hard stop can live.
- A "[MISSING: …]" only warns on the author's machine, so a direct push of `main`
  that still carries one is not refused there (CI turns red afterwards). That was so
  before this test; the hard stop belongs to the same publish step.
- The starter's own example values (the name "Example", `hello@example.com`) and the
  bracket slots in `public/llms.txt` are not caught (a leftover `example.com` in
  `llms.txt` already fails in `tests/seo.spec.ts`). Both would put one more entry on the
  exemption list from the first commit. **Decided 2026-10-06:** catch them once
  `SITE.url` is no longer `example.com`, exact values only, the legal name "Example GmbH"
  and the starter's default home title and description included (decision row). Not built.
- The rule for slots is "an opening bracket followed by a capital letter", plus
  brackets opening with a typical slot word in small letters ("[your name]"). Genuine
  text of that shape (a "[PDF]" label, an editor's note in a quote) has to be
  allow-listed by the site. Other small-letter brackets pass on a finished page.
- Not read: pages outside the page list (the 404 page), other files in `public/`,
  PDFs, text inside images.

### A2. The publish gate holds on GitHub's side (not built)

Today a two-stage site publishes with `npm run ship`, which pushes `main` to
`production`. The pre-push hook can be skipped with `--no-verify`, and nothing on
GitHub's side checks what arrives on `production`.

| # | Given | When | Then |
|---|---|---|---|
| 1 | the rule is on, and a commit that never went through the checks | someone pushes it to `production` | GitHub refuses; the live site is unchanged |
| 2 | the rule is on, and a commit whose check is red | someone pushes it to `production` | GitHub refuses |
| 3 | `main` is green | the owner runs `npm run ship` | it publishes as before |
| 4 | the check on `main` is still running | the owner runs `npm run ship` | refused, and `ship.sh` says in plain words to wait for the green tick and run it again |
| 5 | a private repo on a free plan | the skill tries to create the rule | GitHub answers 403; the skill says plainly that this plan offers no server-side gate and what still protects the site |

Done when row 2 has been seen on a real site. The rule is a repository setting:
`website-team-setup` guides it, the site owner applies it.

Not built yet for two reasons. GitHub's exact refusal message is needed for row 4
(`ship.sh` today recognises a rejected push only in its non-fast-forward wording), and
a runbook for the live branch should not ship on documentation alone. **Decided
2026-10-06:** the message comes from a throwaway public repo the owner creates, with
the same ruleset; the probe also pushes a green `main` and checks that `production`
moved (row 3). Row 2 on a real site still closes the step.

### A3. Deeper message checks (rules chosen 2026-10-06, not built)

- Two pages share the same title or the same description: a hard test, over the page
  list, comparing pages within one language, with an exempt set as the social-card
  test has.
- A content page has no positioning term: a warning in the test run, a hard stop in
  the publish step (A2). Not in CI: a live site's preview already carries the real
  `SITE.url`, so a URL switch cannot tell a draft from a launch. A site with no
  positioning terms declared stays exempt, as today.
- The home page's headline is a greeting ("Welcome", "Willkommen") instead of the
  offer: stays a warning, because a word list misfires across languages.

## B. Proof

Built as the opt-in skill `website-scorecard`: a script, a page component and a test
that a site adds when its owner wants to show the results. Never run unasked.

| # | Given | When | Then |
|---|---|---|---|
| 1 | a site whose tests are green, everything committed | the owner asks for a scorecard and `npm run scorecard` runs | a file with the result: 61 checks passed on 3 pages, by area, with the date and the tested version. Nothing is public until the change is merged like any other |
| 2 | uncommitted changes | the same command | it refuses: the card has to describe a commit |
| 3 | one test is red | the same command | it writes nothing, names the area, and stops |
| 4 | a test that does not apply yet (no positioning terms declared) | the same command | counted and shown as "1 not applicable yet", not hidden |
| 5 | the owner ran Google's PageSpeed test on the live site on 4 October: 98, 100, 100, 100 | the scores are recorded | the section shows them with that date and a link to run the same test |
| 6 | three numbers instead of four, or a score of 101 | the scores are recorded | refused, with the reason |
| 7 | the card is on the site, and a page or a setting of the site is edited afterwards | the site is built again | the section says "The site has been edited since. A new test run is due." An edit to a document such as the README does not count |
| 8 | a German site | the section is shown | German text, which passes the tone and placeholder checks |
| 9 | a build environment without git | the site is built | results and date are shown; it claims neither "edited" nor "not edited" |
| 10 | no scorecard file | the site is built | the section is not rendered; its test skips and says why |
| 11 | a test file is so broken it cannot run | `npm run scorecard` | treated as red: nothing is written |
| 12 | an old card that is wrong (its own check fails) | `npm run scorecard` | the new card is written anyway; a wrong card cannot block its own repair |
| 13 | the card file is damaged (not readable) | the site is built, the tests run, `npm run scorecard` | the page shows no card, the test says the file cannot be read, and the command writes a new one |
| 14 | "30 February" or a day in the future as the date of the PageSpeed run | the scores are recorded | refused, with the reason |
| 15 | a page is edited on the author's machine and not yet committed | the site is built there | the section already says "edited since" |
| 16 | a test is accidentally marked to run alone | `npm run scorecard` | treated as red: nothing is written |
| 17 | a site with several languages, or `<Scorecard lang="de" />` on an English site | the section is shown | it speaks the page's language |

All seventeen were run on 2026-10-04 in a scratch copy of the starter with the skill
installed by its own steps (row 17: the `lang` override; a full several-language site was
not built); with the card in place the full suite passes (64 passed, 1 skip). The first
commit's message says "ten scenarios": two more were added before it was amended, and rows
13 to 17 come from the review.

Decided while building, and why:
- **Lighthouse scores are typed in, not fetched.** Google's PageSpeed API refused an
  unkeyed request with "quota exceeded" when tried. The section links to the same test,
  so anyone can check the numbers.
- **An old card is labelled, not forbidden.** Forcing a new run after every edit would
  put a step on every change. The label keeps it honest without that.
- **A red run writes nothing**, where the earlier scenario said "the report says so". A
  public page should not carry a red card the push check would have stopped anyway.

Open: which sites the toolkit's own site may name (each owner's consent). That is for
the toolkit's site, not for this skill. This repo's CI now installs the skill into the
starter and runs it (`template-tests`, job `scorecard-skill`), so a change to the starter
that breaks the three template files turns red here.

## C. Forms

Built as the opt-in skill `website-forms`: one small function on the site's own
Cloudflare account, a form component, a privacy paragraph and a test. Copied into a site
when the interview says it needs a form that emails the owner, or later on request.

| # | Given | When | Then |
|---|---|---|---|
| 1 | a contact page | a visitor sends name, email and a message | they see a thank-you in the form; the owner gets the message by email, and pressing Reply writes to the visitor |
| 2 | an empty message, a missing name, or "ada@example" as the address | the visitor presses send | the browser stops an empty field. "ada@example" passes the browser, which allows an address with no dot after the @; the function refuses it and names the field, as it does any field that is posted anyway. Nothing is sent. An ordinary address with an apostrophe (o'brien@…) is accepted |
| 3 | a bot fills the field people never see | it submits | it gets the same thank-you; nothing is sent |
| 4 | Cloudflare's mail service refuses the message, cannot be reached, or does not answer within ten seconds | a visitor sends | the form says the message could not be sent and points to the address under it, in the line a screen reader is told to read out, and keeps what was typed. The owner's log shows the status and Cloudflare's numeric error codes, never the token, the message, the visitor's address, or any text Cloudflare or the runtime wrote |
| 5 | a site with the form | the tests run | red unless the privacy page carries one passage marked as being about the form, at least 15 words long, that names Cloudflare. What the passage says beyond that is the skill's text, not a test. Red too while the test file does not say which page has the form and which is the privacy page |
| 6 | a site where the owner has not entered the four settings yet | a visitor sends | "could not be sent", as in row 4. Never a pretended success. The log names the settings that are missing |
| 7 | a name with a line break and "Bcc:" in it, or two addresses in the email field | it is sent | the line break is removed from the subject; the two addresses are refused |
| 8 | a form on another website posts to this site's endpoint through a visitor's browser | it submits | refused whenever the browser names where the post comes from, also when the other site hides its name or uses http for this site's name. A post that names no origin at all is let through on purpose, so that an older browser's visitor does not lose a message |
| 9 | a visitor whose browser runs no JavaScript, or whose browser failed to load the form's script | they send the form | they get a small page with the same answer, in the site's language, and a link back that cannot lead to another site. The address to write to is under the form for every visitor, always |
| 10 | a German site | the form is shown | German texts with no "du" or "Sie", so it fits either kind of site |
| 11 | a visitor whose browser or password manager fills in fields by itself | they send a real message | it is sent unless that tool filled the hidden field too. The field's name and marking give it no reason to; that was not measured. A dropped submission leaves a line in the owner's log |
| 12 | a site with several languages | the form is put on a page without saying where the privacy page is | the build stops and says what to pass |
| 13 | a visitor using only the keyboard | they tab through the form | name, email, message, send. The hidden field is never reached |
| 14 | a two-stage site with the four settings entered for the live site only | the owner tries the form on the preview address | "could not be sent", and the log names the four settings. The skill says this is expected and that the first real message is sent on the live address |
| 15 | a script posts a file as the name, a name made of control characters, or a post of 200 KB, whether or not it declares its length | it arrives | refused; nothing is sent |
| 16 | the owner tries their own form and reads "could not be sent" | they open the function's log and send again | the mailbox first: "could not be sent" means no clear yes, and the message can have gone out all the same. Then one line says why: a setting is missing, Cloudflare's answer was not a clear yes (status and numeric codes), the call ended in an error, or the post named another origin. No line at all means the function wrote nothing: the post never reached it, or the message went out, or the form reported a field as missing or not valid. The skill has one table: what each line means and what to do |

Rows 1 to 9, 11, 13, 15 and the log lines of row 16 are pinned by `tests/forms.spec.ts`,
run on 2026-10-04 in a scratch copy of the starter with the skill installed by its own
steps: 20 form tests, and the full suite with the form in place (81 passed, 1 skip). A fresh
copy of the starter, set up the same way, ran on 2026-10-06, once the limit also counted the bytes of a post that
declares no length: 117 passed, 1 skip. One of
the tests enters the function the way a deployment does, through the export Cloudflare
calls, with only the network call underneath replaced. Three rows are pinned more narrowly
than they read. Row 2: the browser test presses send on an empty form only; the
function's refusals, "ada@example" among them, are tested. Row 4: the test
checks that the mail call carries a signal to stop it, not that it ends within ten
seconds. Row 13: the test starts on the name field and checks that Tab reaches email and
then message and never the hidden field; it does not check that send comes next. Row 15's
200 KB post without a declared length was added on 2026-10-06, after a review that day
sent 200,062 bytes with no length and it went through. The 88 deliberate breakages of the
function, the form or the privacy text, each caught by the tests, date from 2026-10-04,
before that counted read existed. Row 10 was read
against the tone rules by hand. Row 12 was tried in a scratch site with English and German
routes: the build stops on whichever page leaves the privacy address out, the default
language's included, and with it the German page gets the German form. Row 14 is the
skill's text, not a test.

Rows 11 to 15, and much of rows 4 to 9, come from the review: the first version did not
announce a failure to screen readers, left visitors without JavaScript with no address,
logged nothing when Cloudflare refused a message, and used a hidden field named "website",
which a browser may fill in for a real visitor. The second round found that the log could
carry the token inside an error text, and that the link back to the form could be made to
point at another site. The third found that the form could say "could not be sent" while
the log said nothing, and that the advice for one log line pointed the owner at Cloudflare
when the cause can be a badly pasted token. The fourth and fifth found sentences in the
troubleshooting text that claimed more than the code shows; that text is now one table,
one row for each line the function can write. A reader who had seen none of it then read
the whole change once and found that no test entered the function through the export
Cloudflare calls.

**Not verified, and why.** No real email has been sent: that needs a Cloudflare account
with a domain onboarded for sending, which only an owner has. The skill's last step is
that first real message, and the form is not done before it. The function also has not
run inside Cloudflare's own runtime, only in the test runner; the pieces it uses (form
data, fetch, responses) are standard in both. That Cloudflare's build accepts the
function file was read in its source, not run: it makes a route for each export named
like a request handler and skips the rest. Nobody listened with a screen reader: the
tests check the text of the line a screen reader is told to read out. Nobody measured
what browsers and password managers fill in by themselves.

Decided while building, and why:
- **A token and Cloudflare's web API, not a binding.** Cloudflare's documentation lists no
  email binding for Pages Functions. The owner creates the token and enters it as a
  secret; the assistant never sees it.
- **Mail goes to the owner only.** Sending to a mailbox confirmed in the account is free
  on every plan; a copy to the visitor would need Cloudflare's paid plan.
- **A hidden field against bots, nothing more.** Turnstile and a rate limit are the next
  step if spam arrives; the skill says so and does not build them.
- **It works without JavaScript.** A plain form post gets a small page back.
- **The owner's address is always shown under the form.** The first version showed it only
  after a failed send, which left a visitor with nothing when the form's script did not
  load. Shown always, nothing has to work for a visitor to find it. The address is in the
  page either way, in a form crawlers do not read as an address.

## D. Import

| # | Given | When | Then |
|---|---|---|---|
| 1 | an existing site with 12 pages | the owner says "bring my site over" | first an inventory: every address, title, description, headline, images, forms. Nothing is built yet |
| 2 | an old address that changes | the new site is built | the old address redirects to the new one, and a test checks every old address |
| 3 | the old copy | it is carried over | word for word first; what the tone and positioning checks reject is listed for the owner to decide, not rewritten silently |
| 4 | an image without a description | it is carried over | it gets a "[MISSING: …]" placeholder, which the gate then holds back |

Done when the imported site passes the whole suite with every old address accounted for.

## E. Install

| # | Given | When | Then |
|---|---|---|---|
| 1 | Claude Code, nothing installed | the user adds the plugin with one command | all skills are available, no clone and no script |
| 2 | no assistant-specific setup | the user runs the `npm create` command | the skills are installed and the first step is explained |
