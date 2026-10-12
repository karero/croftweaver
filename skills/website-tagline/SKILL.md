---
name: website-tagline
description: >
  OPTIONAL: find the one short line that sits under the logo (the tagline; a
  German-speaking owner calls it the "Claim"). Leads with purpose: starts from
  what the business is there to do for its customer, taken from POSITIONING.md,
  not from clever wording. Shows the owner six to eight candidate lines in three
  or four different directions, asks which direction sounds like them, then
  refines on the owner's feedback until they pick ONE. Records it in TAGLINE.md
  and writes SITE.tagline. Adds no claim POSITIONING.md lacks and loses every
  conflict with it. Never runs unasked. Trigger phrases: "tagline", "claim",
  "Claim", "strapline", "slogan", "motto", "the line under the logo", "a line
  for under our logo", "what do we stand for in five words". Not for
  positioning itself, the page headline, or the story one-liner.
---

# Website tagline

The tagline is the short line under the logo. Someone who sees only the logo and
that line should know what the business is there for. Positioning
(`website-positioning`, `POSITIONING.md`) decides **what** the site claims; this
skill finds the few words that carry it, together with the owner. Optional, never
part of the default build.

**The governing rule: the tagline says nothing `POSITIONING.md` does not already
say. On any conflict, positioning wins and the tagline is rewritten.**

The work has four moves, in this order: lead with purpose (§2), show six to eight
variations (§3), ask the owner for a direction (§4), ask for feedback and refine
until one line is picked (§5). The owner decides at every step; the assistant
proposes.

## Explain it first (what to say to the owner)

Most owners have never chosen a tagline and expect to be handed "the answer". Say
how it will go before the first line, in the language the owner writes in (per
`new-website` §1), roughly:

> A tagline is the short line under your logo. In a few words it says what you
> are there for. We start from your purpose, not from clever wording. I will show
> you six to eight lines in a few different directions. You tell me which
> direction sounds like you, I work on that one, and you tell me what to change
> until one line is right. Nothing goes on the site until you say so, and it does
> not change your positioning.

## 0. When it runs

- **When the owner asks** ("we need a tagline", "what goes under the logo", "a
  Claim for the site"), on a new site or an existing one.
- **Prerequisite:** a filled `POSITIONING.md` (repo root, or `docs/` on a site that
  keeps its strategy documents there; look in both). If it is missing or
  half-filled, run `website-positioning` first. A tagline written before the
  positioning is a guess with good rhythm.
- **Also read, when present:** `STORY.md` (the character's want, the success lines
  and the controlling idea are the closest neighbours of a tagline) and any
  voice-of-customer notes from `customer-research`. The best lines are usually
  words a customer already said.

## 1. Outputs

- **`TAGLINE.md`** (from this skill's `templates/tagline.md`), next to
  `POSITIONING.md`: the purpose sentence, the chosen line, what the owner said
  about direction and wording, and the lines not chosen, so a later session does
  not propose them again.
- **`SITE.tagline`** in `src/config.ts`: the chosen line, verbatim.
- **The line on the site**, under the logo, read from `SITE.tagline` (§6).

Explicitly **not** touched: `POSITIONING.md`, `tests/positioning.spec.ts`, any
`<title>` or `<h1>`, and `STORY.md`. The positioning term stays where the
positioning test expects it; the tagline is an extra line, not a replacement.

## 2. Lead with purpose

Before any tagline, write the **purpose sentence**: what the business is there to
do for its customer, in one plain sentence.

> We are here so that [the customer, `POSITIONING.md` §4] can [the value they get, §3].

Show it to the owner and ask: *"Is this what you are here for? If not, say it in
your own words."* Their wording wins. If their answer changes **who** it is for or
**what** they get, that is a positioning change: fix `POSITIONING.md` via
`website-positioning`, then come back. Do not write a single candidate until the
owner has agreed to the sentence.

Every candidate must then lead with that purpose: it says what the business is
**for**. Three kinds of line fail this, however good they sound:

| Fails because it leads with | Example |
|---|---|
| the category (what the business *is*) | "Bookkeeping services since 2019" |
| adjectives (how it would like to be seen) | "Reliable. Personal. Digital." |
| the company itself | "We love numbers" |

The test for each line: read the purpose sentence, then the line. Is the line a
shorter way of saying it? If it could sit unchanged under the logo of a business
with a different purpose, rewrite it.

## 3. Round one: six to eight variations

Write **six to eight** lines, never fewer and never more: fewer gives the owner
nothing to compare, more is a list nobody reads to the end. Spread them over
**three or four directions**, two lines each, so that the owner's choice of
direction means something. All four lead with purpose; they differ in which side
of it they show:

| Direction | The line says | Leans on `POSITIONING.md` |
|---|---|---|
| **The outcome** | what the customer has afterwards | §3 Value |
| **The customer** | who it is for, in their own words | §4 Target customer |
| **The contrast** | what they can stop doing or putting up with | §1 Competitive alternatives (the situation, never a named competitor) |
| **The promise** | the one thing they can count on | §2 Unique attributes + §3 Proof |

Rules for every line:

- **Short enough for its place.** At most eight words and about 50 characters. It
  has to fit under a logo on a phone.
- **Reads after the name.** Say "[Name]. [Line]." aloud. If it stumbles, or
  repeats a word from the name, rewrite it.
- **No new claim.** Each line names the `POSITIONING.md` section it leans on. A
  number, a superlative or an "every" needs its proof in §3; without proof, the
  line goes.
- **Plain words the customer uses.** No word the owner would not say to a customer
  across a table. No em dashes, so the line survives the tone test wherever it is
  pasted.
- **Not a second headline.** It is not the `<title>`, not the `<h1>` and not the
  story one-liner; it may agree with the controlling idea in `STORY.md` and must
  never contradict it.
- **Non-English builds:** write native lines. A translated English tagline is
  the most common bad tagline.

Show the round to the owner as a plain numbered list, grouped under the
directions in everyday words, with no table and no section numbers. The trace to
`POSITIONING.md` goes into `TAGLINE.md`, not into the chat.

**Worked example** (a made-up business; reuse the shape, not the words):

- From `POSITIONING.md`: target = freelancers who dread the quarterly tax return;
  alternatives = doing the books themselves at night, a large accountancy firm;
  unique attributes = a fixed monthly price, one named contact; proof = every
  return filed on time since 2019.
- Purpose sentence, agreed by the owner: "We are here so that freelancers can
  stop worrying about their books and get on with their work."
- Round one, as the owner sees it:

  > **What you have afterwards**
  > 1. Your books done. Your evenings back.
  > 2. Tax season without the dread.
  >
  > **Who it is for**
  > 3. Work for yourself, not for your books.
  > 4. For freelancers who would rather be working.
  >
  > **What you can stop doing**
  > 5. No more Sunday-night spreadsheets.
  > 6. Stop doing your books at midnight.
  >
  > **What you can count on**
  > 7. Every deadline met. None on your mind.
  > 8. One person who knows your books.

  Line 7 may say *every* only because the proof says every return was on time.

## 4. Ask the owner for a direction

Do not ask for the winner yet. Ask for a direction:

> Which of these sounds most like you? You do not have to choose the final line
> yet. Tell me the one or two you are drawn to and what you like about them. If
> none fits, tell me what is missing.

Use a structured user-input tool if the platform offers one (Claude Code's
**`AskUserQuestion`**, with the three or four directions as the options and the
free answer for "none of these"), otherwise ask in chat. Then:

- **One direction named** → round two stays inside it.
- **Two lines from different directions** → round two combines what the owner
  liked about each. Ask what they liked if they did not say.
- **"None"** → ask what is missing, and check the purpose sentence again before
  writing more lines. Eight misses usually mean the purpose is off, not the wording.
- **No answer** → stop. Change nothing on the site.

Round two: **four to six** new lines in that direction. Keep any line or phrase
the owner liked word for word, and drop every word they pushed back on.

**Worked example, continued:**

- The owner answers: "1 and 5. 'Evenings back' is what my clients say to me, and
  the Sunday-night spreadsheet is exactly their week. Not 2: 'dread' is too dark
  for us."
- Two lines from different directions, so round two combines them. Every line is
  built from the words the owner liked, and none says "dread":

  > 1. No Sunday-night spreadsheets. Your evenings back.
  > 2. Your evenings back from the spreadsheet.
  > 3. Evenings back. Spreadsheets gone.
  > 4. Your books done. Your Sunday nights back.

## 5. Ask for feedback, refine, pick one

After round two, and after every later round, ask for feedback with questions the
owner can answer, never "what do you think?":

> Read each line aloud after your business name. Which words would you really say
> to a customer? Which word feels off? Is anything too bold, too modest or too long?

Then change **only** what the feedback names, show at most four lines, and ask
again. The loop ends in one of three ways:

- **The owner picks one line.** Before it is final, search the exact line in
  quotation marks. If another business in the same market already uses it, say so
  and go back one round. This is a courtesy search, not a trademark check; say
  that too, and leave the legal question to the owner.
- **Three rounds without a pick.** Stop and say so plainly. The purpose sentence
  or the positioning is probably not settled; go back to §2 or to
  `website-positioning`. More wording will not fix it.
- **The owner decides against a tagline.** A valid answer; a site does not need
  one. Record it (§6) and change nothing else.

Only the owner picks. Never choose for them, and never set a line because the
conversation ended.

**Worked example, the end:**

- Asked the three feedback questions, the owner says: "The fourth is nearly it. I
  would say 'Sunday evenings', not 'Sunday nights'. Can it be shorter? And 'gone'
  in the third sounds like an advert."
- Only those three things change. Round three is two lines:

  > 1. Your books done. Your Sunday evenings back.
  > 2. Books done. Sunday evenings back.

- The owner picks line 1: "The short one sounds like a telegram." A search for the
  exact line in quotation marks finds no other bookkeeper using it, and the owner
  is told that this was a courtesy search, not a trademark check.
- `TAGLINE.md` records the line, "evenings back" as words to keep, "dread" and
  "gone" as words to avoid, and the thirteen lines not chosen. `SITE.tagline` gets
  the line verbatim.

## 6. Record it and place it

1. **`TAGLINE.md`**: copy `templates/tagline.md` next to `POSITIONING.md` and fill
   it: the purpose sentence, the chosen line with its direction and the section it
   leans on, the owner's direction and feedback in their words, and every line not
   chosen.
2. **`SITE.tagline`** in `src/config.ts`: the chosen line, verbatim.
3. **Under the logo.** Where the site's header shows the logo or the name, add the
   line beneath it as a `<p>` that reads `SITE.tagline`. Never type the line a
   second time, and never make it a heading: the page keeps its one `<h1>`. A
   site with no logo or name in its header yet gets steps 1 and 2 only; tell the
   owner the line is stored and not shown yet.
4. **Run the site's tests** (`npm test`). The line must pass the contrast check in
   light and dark, and the tone and positioning tests must still be green. Look at
   the header at phone width as well.
5. **Record the choice** in the project README next to the decision-interview
   answers ("tagline: see TAGLINE.md", or "tagline: declined"), so a later session
   does not ask again.

## 7. Gotchas

- A line the assistant likes is not a line the owner would say. When they
  disagree, the owner is right.
- Rhyme, puns and alliteration are decoration. A plain line that says the purpose
  beats a clever one that needs explaining.
- Do not show more than eight lines "to be safe", and do not show three to save
  time. The count is the method.
- Changing the tagline later is cheap; changing it every month teaches visitors
  nothing. Rerun this skill when the positioning changes, not when the line feels old.
- Answer the question that was asked. "Is this line too long?" wants a yes or no
  and a reason, not a new round.

## Boundaries (do not duplicate)

- **Positioning, the per-page spine** → `website-positioning`.
- **The home page as the customer's story, the one-liner, the controlling idea**
  → `website-story`.
- **Tone of voice, EEAT** → `website-content-guide`.
- **Page headlines and body copy** → `copywriting`.

## Done means

The owner agreed to the purpose sentence, saw six to eight lines in three or four
directions, named a direction, gave feedback, and picked one line themselves (or
declined). `TAGLINE.md` is filled, `SITE.tagline` holds the line verbatim, the
line shows under the logo where the site has one, and the site's tests are green.
