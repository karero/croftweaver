<!--
  CONTENT_GUIDE.md — per-site voice & content guide (tone of voice + EEAT).
  Copy this into the project root and fill every [BRACKET]. Single source of truth
  for HOW the site says things. POSITIONING (what you offer, for whom, the market
  category) lives in POSITIONING.md — owned by website-positioning and worked out
  first; read it, do not restate it here. Pairs with BRAND.md (how it looks) and is
  enforced by the tone test (tests/tone.spec.ts). Build after POSITIONING.md,
  before any page copy — per the new-website pipeline.
-->
# [Site name] — content guide

## Positioning (owned by website-positioning — read, do not restate)

The positioning statement, target customer, market category and boilerplate live
in **POSITIONING.md** (worked out first, via `website-positioning`). Read them from
there; do not duplicate them here. This guide covers voice, EEAT, and the
page-level content that hangs off that positioning.

- **Top 3 jobs-to-be-done (for copy):** [1] · [2] · [3]
- **Primary action we want:** [book a call / sign up / download / contact]

## Tone of voice

Write like [persona, e.g. "a senior practitioner talking to a smart peer"]:
[3–5 adjectives]. Proof over claims. Active voice.

**Content language:** [English / German / other] — the hard rules below are
lexical (specific words/mechanisms) and differ by language; fill in only the
subsection that matches, delete the other.

**Shared rules (enforced by the tone test — run after every copy change):**
- **No em dashes (—).** Use a comma, period, or colon.
- Genuine quoted customer/human voice is exempt: wrap in `<blockquote>`, `<q>`,
  or add `data-tov-exempt`.

**If English:**
- Speak to the reader as "you".
- **No contractions.** Long form: "cannot", "it is", "you are", "we are".
- **No buzzwords:** supercharge, world-class, leverage, unlock, seamless, robust,
  cutting-edge, empower, holistic, revolutionary, synergy, next-level. [trim/add]

**If German:** no direct equivalent to "no contractions" — the real formality
lever is register, not contraction.
- **Register:** [du / Sie] — pick one per brand and hold it for the whole
  site; mixing du/Sie mid-page reads as a translation error, not a style
  choice. This settles "speak to the reader as you" for German copy.
  tone.spec.ts machine-checks the unambiguous cases (lowercase du-family
  words vs. capitalized "Kontaktieren Sie ..."-style imperatives on one
  page); subtler mixing still needs a human read.
- **No buzzwords:** ganzheitlich, nahtlos, Synergie(n), Synergieeffekt(e/en),
  bahnbrechend, revolutionär, wegweisend, erstklassig, hochmodern,
  maßgeschneidert (Swiss "massgeschneidert" also caught — the enforced test
  doesn't fold ß↔ss), zukunftsweisend, transformativ, unschlagbar,
  entfesseln/entfesselt, Spitzenreiter. [trim/add]

**Do / don't examples**
- Do: "[on-brand sentence]"
- Don't: "[off-brand sentence and why]"

## EEAT signals (build in from the start)

Search + AI answer engines reward Experience, Expertise, Authoritativeness,
Trust. Ship these, not just claims:
- **Experience / Expertise:** named authors with a real bio + `@id`; first-hand
  detail, specifics, dates; cite primary sources inline for claim-heavy copy.
- **Authoritativeness:** real `sameAs` profiles (LinkedIn, GitHub, register
  entry) that resolve; corroborating external mentions; Organization schema.
- **Trust:** legal entity / imprint page; clear contact; privacy page;
  last-updated timestamps on substantive pages; HTTPS; no broken links.

## Page inventory

| Page | URL | Purpose | Primary keyword | Target `<title>` (≤60) | Status |
|---|---|---|---|---|---|
| Home | `/` | [why it exists] | [kw] | [title] | [ ] |
| [About] | `/about` | … | … | … | [ ] |

## Per-page-type copy template

For each repeated page type (service, post, case study), define:
- **Section order:** [hero → … → CTA]
  (Home on a story-led site: the seven sections in `STORY.md`, optional `website-story`.)
- **Hero:** H1 [reader-benefit], subhead [1 sentence], primary CTA.
- **Body sections:** [bullets of what each must cover]
- **Proof block:** [logos / metrics / quotes — verbatim only]
- **CTA:** [single, repeated]

## New-page checklist

- [ ] Positioning term threaded (positioning.spec.ts) + ToV applied; tone + positioning tests green
- [ ] One `<h1>`; headings nest without skips
- [ ] `<title>` 50–60 chars, `<meta description>` 120–160 (see website-seo-geo)
- [ ] og/twitter inherit title/description; canonical set
- [ ] Required JSON-LD present (WebPage + page-specific)
- [ ] Images: WebP, sized to display, descriptive alt, lazy below the fold
- [ ] Any linked PDF in `public/` has a descriptive doc-title set via
      `scripts/set_pdf_title.py` — not the authoring placeholder (see website-seo-geo)
- [ ] In sitemap; internal links clean (no `.html`)
- [ ] EEAT: author/date where relevant; sources cited
