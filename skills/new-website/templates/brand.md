<!--
  BRAND.md — per-site brand & visual guide.
  Copy into the project root and fill every [BRACKET]. Pairs with
  CONTENT_GUIDE.md (what it says). The colour source of truth is the theme-token
  block in the stylesheet — src/styles/global.css (in the kit:
  templates/astro/src/styles/global.css); keep this file and that block in sync.
-->
# [Site name] — brand & style guide

## Brand in one line

[Positioning + the visual feel in one sentence: palette mood, one accent,
whitespace, shape language. No clichéd stock photography.]

## Logo

- File: `[path]` ([dimensions]).
- Clearspace: keep free space ≥ [30%] of the logo height around it.
- Minimum size: [24]px tall (favicon excepted).
- On dark backgrounds: [usage].

## Colour palette

Mirror these into the theme-token block. Every text/background pair MUST pass
**WCAG AA (4.5:1 body, 3:1 large)** in BOTH themes — the a11y test checks this.
The rows are the stylesheet's own colour tokens, one row each. Accent and Link have a
value per theme, so that each can be chosen for its own background. Keep the headings,
the header row `| Token | Hex |` and the row names: the optional `website-brand-kit` reads these tables to check every
text colour on every background and to write the values into the stylesheet.

### Brand (fixed, theme-independent)
| Token | Hex | Use |
|---|---|---|
| Primary | `#[…]` | buttons, brand surfaces |

### Light theme
| Token | Hex |
|---|---|
| Heading | `#[…]` |
| Body (ink) | `#[…]` |
| Muted | `#[…]` |
| Accent | `#[…]` |
| Link | `#[…]` |
| Hairline | `#[…]` |
| Background | `#[…]` |
| Soft background | `#[…]` |
| Surface (cards) | `#[…]` |

### Dark theme
| Token | Hex |
|---|---|
| Heading | `#[…]` |
| Body (ink) | `#[…]` |
| Muted | `#[…]` |
| Accent | `#[…]` |
| Link | `#[…]` |
| Hairline | `#[…]` |
| Background | `#[…]` |
| Soft background | `#[…]` |
| Surface (cards) | `#[…]` |

## Typography

- Family: [system stack or self-hosted woff2 + fallback]. Self-host fonts
  (`font-display: swap`); preload the two used above the fold.
- Headings: weight [700–800], tracking [≈ −0.02em].
- Body: weight 400, line-height ≈ 1.6.

## Shape & spacing

- Corner radius: [12]px. Soft shadow: `[0 8px 24px rgba(...,0.06)]`.
- Max content width: [72rem].

## Mobile & graphics rules (the website-design-system skill)

- **Responsive images:** serve WebP (or AVIF); generate width variants and use
  `srcset`/`sizes` (or `<picture>`); render at display size, never ship a
  2000px source into an 80px slot. Set explicit `width`/`height` to reserve
  space (no layout shift / CLS).
- **Lazy-load** below-the-fold images (`loading="lazy"`); eager-load the LCP
  image and `fetchpriority="high"` it.
- **Every image has descriptive `alt`** (or `alt=""` if purely decorative).
- **Mobile first:** design at 360px up; tap targets ≥ 44px; no horizontal
  scroll; test at 360 / 768 / 1280.

## OG / share image spec (1200 × 630)

This drives `scripts/generate_og_cards.py` (run `npm run og`). Fill its BRAND block
from the tokens below so `public/images/og/default.jpg` + the per-page cards stay on-brand:
1. Canvas 1200×630, [background / gradient].
2. Logo [position, size].
3. Wordmark [text, position, size, colour].
4. Headline [text, position, size, colour].
5. Footer URL [text, position].

Per-page variants: change only the headline; keep everything else identical.

**Weight + format (hard rule — messengers enforce it):**
- **≤ 300 KB.** WhatsApp silently drops the preview image above ~300 KB (Teams/Slack
  also prefer small); the link then shares with no picture. Compress to fit.
- **Extension must match the bytes.** A PNG renamed `.jpg` (or vice-versa) trips strict
  scrapers. Use **JPEG** for photographic cards (e.g. a speaker headshot), PNG only for
  flat logo/gradient cards that still come in under 300 KB.
- Never ship a **square** image as `og:image` — it gets cropped to 1.91:1 on X/Teams.
- **Generate cards with the shipped script, not by hand** — `npm run og`
  (`scripts/generate_og_cards.py`) renders a 1200×630 JPEG ≤ 300 KB per page you list,
  keeping them consistent and re-runnable. Edit its BRAND + PAGES blocks; `tests/seo.spec.ts`
  then enforces that every page's card exists at the right size. See the **og-images** skill.
  For photo-driven cards (e.g. per-event speaker headshots), extend the script to read
  frontmatter and composite the portrait — one card per content-collection entry.
- **Logo on a dark card needs a light variant.** Most logo lockups ship a dark wordmark
  that vanishes on a dark OG background. Composite a **transparent PNG** (never a JPG — it
  boxes the logo) and use a white/light wordmark version; if only a dark one exists, recolour
  the wordmark region to white at build time (a build-time recolour step does this).

## Imagery style (do / don't)

- **Do:** [palette, motifs, real people if used, breathing room; legible in both
  themes].
- **Don't:** [rainbow palettes, busy gradients, AI "robot/brain" clichés,
  low-contrast text on images].
