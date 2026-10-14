<!--
  Palette prompt (the question to put to a design tool or an assistant for three palettes).

  The assistant fills every [BRACKET] and gives the owner ONLY the text between the two marker
  comments, to paste where she likes (references/where-to-paste.md). It writes the prompt in the
  language the owner writes in, EXCEPT the three table headings, the header row `| Token | Hex |`
  and the row names: those stay in English exactly as below, because the check reads those words. It names no tool and says nothing
  about what a tool can or cannot do.

  Where the slots come from:
    [WHAT THE BUSINESS DOES], [WHO IT IS FOR], [WHAT MAKES IT DIFFERENT]  POSITIONING.md (and STORY.md, if the owner chose it)
    [THE FEEL], [COLOURS I LIKE], [COLOURS TO AVOID], [A BRAND OR PLACE]   the owner's own answers (SKILL.md §2)
  A slot she gave no answer for is left out with its line, never invented ("surprise me" is an answer).

  The table below is the one in BRAND.md. Its row names are what `brand_intake.py palette` reads,
  so the owner can paste the chosen table straight back without anyone re-typing it. A test
  (tests/test_templates.py) keeps the two in step.
-->

<!-- prompt:start -->
I am choosing the colours for a website. Please design THREE different colour palettes for it.

About the business
- What it does: [WHAT THE BUSINESS DOES]
- Who it is for: [WHO IT IS FOR]
- What makes it different: [WHAT MAKES IT DIFFERENT]

The feel I want
- Overall: [THE FEEL]
- Colours I like: [COLOURS I LIKE]
- Colours to avoid: [COLOURS TO AVOID]
- A brand or place whose colours I admire: [A BRAND OR PLACE]

How to answer
Give each palette a short name and one sentence on the mood it carries. Then give each palette as exactly the three tables below, one table per heading, with every `#...` replaced by a hex colour. Keep the three headings, the header row of each table (`| Token | Hex |`) and the row names exactly as they are, in English, so that I can copy the tables of the palette I choose and paste them somewhere else.

### Brand (fixed, theme-independent)
| Token | Hex | Use |
|---|---|---|
| Primary | `#...` | buttons, brand surfaces |

### Light theme
| Token | Hex |
|---|---|
| Heading | `#...` |
| Body (ink) | `#...` |
| Muted | `#...` |
| Accent | `#...` |
| Link | `#...` |
| Hairline | `#...` |
| Background | `#...` |
| Soft background | `#...` |
| Surface (cards) | `#...` |

### Dark theme
| Token | Hex |
|---|---|
| Heading | `#...` |
| Body (ink) | `#...` |
| Muted | `#...` |
| Accent | `#...` |
| Link | `#...` |
| Hairline | `#...` |
| Background | `#...` |
| Soft background | `#...` |
| Surface (cards) | `#...` |

Rules for every palette
1. Write every colour as a six-digit hex value such as `#1a2b3c`. No colour names, no transparency.
2. The text colours (Heading, Body, Muted, Accent, Link) must each reach a contrast of at least 4.5 to 1 against all three backgrounds (Background, Soft background, Surface), in the light theme and in the dark theme. Work the contrast out with the WCAG formula and check every pair; a palette that misses one is not a palette I can use.
3. Primary is one brand colour, the same in both themes. Accent is for links and highlights and may be lighter in the dark theme.
4. The dark theme is its own design for the same brand, not the light theme turned upside down.
5. Hairline is a quiet line colour for borders and dividers; it needs no text contrast.
6. The three palettes must look clearly different from one another, not three shades of the same idea.
<!-- prompt:end -->

## Words for the owner

When you hand her the prompt, say in a sentence or two what it does: it asks for three palettes, and she picks the one that feels like her business. Then tell her what to do with the answer: copy the three tables of the palette she likes best and paste them back here. You then check every text colour on every background and say plainly if one pair is too faint to read.
