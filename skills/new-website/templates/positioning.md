<!--
  POSITIONING.md — per-site positioning, worked out FIRST (before SEO, before any
  page copy). Copy into the project root and fill every [BRACKET]. Single source of
  truth for WHAT you offer, FOR WHOM, and the MARKET CATEGORY it sits in. Everything
  downstream reads this: CONTENT_GUIDE.md (voice/EEAT), every page title/description/
  H1, and the schema description. Built on April Dunford's framework (Obviously
  Awesome). Enforced by tests/positioning.spec.ts (the positioning spine).
  Owned by the website-positioning skill — do not restate positioning in CONTENT_GUIDE.md.
  Further reading: https://www.aprildunford.com/books
-->
# [Site name] — positioning

## 1. Competitive alternatives

What would the customer use if this offer did not exist? Include the status quo,
not just direct rivals (a spreadsheet, an in-house team, a generalist agency, doing
nothing).

- [alternative 1] · [alternative 2] · [alternative 3]

## 2. Unique attributes

What do you have that those alternatives do not? Capabilities, assets, model —
facts, not adjectives.

- [attribute 1] · [attribute 2] · [attribute 3]

## 3. Value + proof

The benefit each attribute makes possible that the customer actually cares about,
with proof (a metric, a mechanism, a reference).

| Unique attribute | Value it enables | Proof |
|---|---|---|
| [attribute] | [value the customer cares about] | [metric / mechanism / reference] |

## 4. Target customer

Who cares *a lot* about that value? The best-fit segment, described by traits you
can identify — not "everyone".

- **Best-fit customer:** [who they are]
- **Why they care most:** [the trigger / pain that makes the value matter]
- **Where they are:** [market / geography / channel]

## 5. Market category

The context you place the offer in so the value is obvious. The category frames
expectations — pick the one where your unique value wins.

- **Market category:** [category]
  ← becomes the home page's `body: ['[category]']` entry in tests/positioning.spec.ts
- **Trap test:** [what a search for the category returns; safe, or a trap (the results are a different concept)]
- **Familiar frame, as the foil (optional):** [the frame the customer already holds,
  used only in the statement's "unlike"; never a title, slug or schema value]

## Positioning statement (one paragraph)

> For [target customer] who [need / trigger], [site/brand] is a [market category]
> that [unique value], unlike [competitive alternative], because [unique attribute
> / proof].

**Non-English builds: rewrite this frame as a natural sentence in the target
language** — do not fill the English sentence brackets with translated words.
Fixed articles and pronouns can't agree with an arbitrary filled noun ("ein
[Marktkategorie], das..." breaks the moment the category is feminine: "eine
..., die"). Write the sentence a native marketer would write, then extract the
same fields from it.

- **Human version (optional):** [the same claim in the owner's own voice, for pitches
  and the About page; adds no claim the paragraph above lacks]
- **Core positioning term:** [the short, plain phrase threaded through the home
  `<title>`, `<meta description>` and `<h1>` — keep it the SAME across all three]
- **One-line boilerplate (≤ 12 words):** […]
- **~50-word boilerplate:** [reusable on About / footer / schema description]

## The positioning spine (per-page terms → tests/positioning.spec.ts)

One positioning term per page. Each page must carry its term in its `<title>`,
`<meta description>` and its `<h1>` or the intro sentence right under it. The home page
additionally carries its market category (and core positioning phrase) in the body.
Mirror this table into the `POSITIONING` map in `tests/positioning.spec.ts` — the home
row's market category becomes a `body: [...]` entry (start empty; add a row the moment a
page's term is set). The spec **warns (without failing)** about any `PAGES` route with no
entry that isn't in `POSITIONING_EXEMPT` (legal/utility pages), so an un-positioned content
page is surfaced as a lost opportunity rather than slipping by.

| Page | URL | Positioning term | Market category (home only) |
|---|---|---|---|
| Home | `/` | [core positioning term] | [market category] |
| [Service / offer] | `/[url]` | [service-line positioning term] | — |

Use ONE term per page and repeat it across the three surfaces. Do not pad with
synonyms, and do not chase keyword density — say the thing once, where it belongs.

## Hand-off to the rest of the pipeline

- **Voice + EEAT + page copy:** `website-content-guide` reads this file; it owns
  tone of voice and EEAT, NOT positioning.
- **Keyword / SERP research:** `seo-audit` — positioning leads, keywords follow.
- **AI / answer-engine phrasing (GEO):** `ai-seo`.
- **Schema `description` + head metadata:** `website-seo-geo` (use the 50-word
  boilerplate verbatim so the spine stays consistent).
