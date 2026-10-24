<!--
  STORY.md — the home page told as the customer's story. OPTIONAL layer, used only
  when the owner opted in (new-website §2a) or asked for it later. Copy next to
  POSITIONING.md (repo root or docs/) and fill every [BRACKET].
  Derived from POSITIONING.md, which is the source of truth for WHAT is claimed
  (target customer, competitive alternatives, unique attributes + proof, value,
  market category). This file decides only HOW the home page narrates it. On any
  conflict POSITIONING.md wins and this file is corrected. Do not restate the
  positioning here; cite it.
  Owned by the website-story skill. Inspired by Donald Miller's StoryBrand
  framework, in this suite's own words. Opt-in enforcement: tests/story.spec.ts.
  Further reading: https://storybrand.com/building-a-storybrand-book-new/
-->
# [Site name] — story layer

## Source map (every line below cites POSITIONING.md)

The full rules per row are in the website-story skill, §2.

| Story element | From POSITIONING.md |
|---|---|
| Character + want | §4 Target customer, "why they care most" |
| Problem / villain | §1 Competitive alternatives + §4 "why they care most" |
| Guide: empathy / authority | §4 (situation) / §2 Unique attributes + §3 Proof |
| Plan | §2 how the attributes are delivered |
| Calls to action | the owner's decision (not in positioning); name it here |
| Stakes | §1, the cost of staying with the alternatives |
| Success | §3 Value |
| Market category | §5, unchanged |
| One-liner, controlling idea | Positioning statement + core positioning term |

## 1. Character (the hero is the visitor)

- **Who:** [the best-fit customer, in their own words]
- **What they want (one thing):** [the outcome they are after]

## 2. Problem

- **Villain:** [the situation or status quo that stands in the way; never a named competitor]
- **External:** [the practical problem]
- **Internal:** [how it makes them feel]
- **Philosophical:** [why it is simply wrong that they have to put up with it]

## 3. Guide (the brand)

- **Empathy (one sentence):** [we know what it is like to…]
- **Authority (one sentence, proof from POSITIONING.md §3 only):** [metric / mechanism / reference]

## 4. Plan

**Title:** [Your plan in three words]

1. [Verb] → [what they get]
2. [Verb] → [what they get]
3. [Verb] → [what they get]

- **Promise (optional):** [the guarantee or commitment that removes the fear]

## 5. Calls to action

- **Direct CTA (one label, verbatim everywhere):** `[Get a quote]` → `[/contact]`
- **Transitional CTA (lead generator):** `[5 mistakes to avoid when…]` → `[/guide]`
  Leave blank rather than invent one.

## 6. Stakes (what stays wrong if nothing changes)

- [cost 1]
- [cost 2]

## 7. Success (life after)

- [concrete change 1]
- [concrete change 2]

## One-liner (at most 30 words)

> [When you [the visitor's situation], you [the problem, felt]. [Brand] [plan, in one
> verb phrase]. [Success, as what they do next].]

Open on the visitor's own moment, second person, present tense. Stranger test: does someone who has never heard of you understand what you do and
for whom? No em dashes (the tone test). **Non-English builds:** write a native
sentence; do not fill this English frame with translated words.

## Controlling idea (at most ten words)

> [the one thought every section reinforces]

Must agree with the **core positioning term** in POSITIONING.md; it narrows that
term, never replaces it.

## Home page map (seven sections → src/pages/index.astro)

| # | Section | Carries | Direct CTA |
|---|---|---|---|
| 1 | Header | `<h1>` with the positioning term, the one-liner as first paragraph, up to three outcomes (one per §7 success line; never invent one), customer image | yes |
| 2 | Stakes | §6, one to three lines in the "what you keep missing" register, then a one-line pivot to the guide | no |
| 3 | Plan | §4 as an `<ol>` | yes |
| 4 | Value stack | §7 success lines, as many as §7 has, up to three | no |
| 5 | Explanatory paragraph | §3 guide, top objections, "read more" link | no |
| 6 | Lead generator | §5 transitional CTA (omit if blank) | no |
| 7 | Junk drawer | FAQ, everything else | yes |

## → tests/story.spec.ts CONFIG (copy across when the site adopts the guard)

- `directCta`: [the direct CTA label from §5]
- `keyLine`: [the one-liner or the controlling idea, verbatim]
- `planList`: [selector for the plan container, e.g. `#plan ol`]
- `planStep`: [`li` for a list; the card class for a numbered card grid]
