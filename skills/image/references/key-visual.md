# Key visuals: reading a photo style and writing it down

How to find the photo style in a site's pictures, check it, and keep it in `BRAND.md`. The steps
are in the "Key visuals" section of `SKILL.md`; this file holds what to look for and one example.

---

## The six headings

Write the style under these headings, one to three lines each. Read each off the pictures, not
off what the owner says she wants.

| Heading | Look for | Typical way to get it wrong |
|---|---|---|
| **Scene** | The kind of place, and what is going on there | Naming the place most pictures show; one picture is somewhere else |
| **People** | How many, what they do, where they look | "Never at the camera" when one picture looks into it; "standing" when one pair sits |
| **Clothes and props** | What they wear and hold; what lies around | Listing what one picture has |
| **Light and colour** | Daylight or lamps, warm or cool, how strong the colour is | "Window light" when one picture is outdoors |
| **Framing and shape** | Distance, height of the camera, and the shape the slot gives the picture (a wide strip, a square, a tall card) | Writing the shape of one slot as the shape of the style |
| **Avoid** | What the pictures leave out, and what must never appear | Leaving out a readable brand name that one picture shows |

The shape belongs to the slot, not to the style. Take it from the component or the CSS of the
page that shows the picture, and write the usual shape as the template's default.

## Checking a line against a picture

Do it in writing, for every line and every picture, not from an impression of the set:

1. Open the pictures one at a time.
2. For each line of the style, ask: is this true of this picture? Yes or no, never "mostly".
3. A line a picture breaks is fixed (make it less specific, or say what holds for most) or the
   picture is named in the line as an exception ("except `photo-4`, outdoors").
4. Look in each picture for text, logos, liveries and faces. A readable real brand goes under
   **Avoid** whatever the other pictures show. A face that may belong to a real, recognizable
   person is asked about before the style is written down.

An exception in a line is for a style the owner still likes. It never lets a readable real
brand onto a page.

## Where it goes

In the site's `BRAND.md`, under `## Imagery style (do / don't)` (the kit's template has it; add it
if the site has none), as two subsections: `### Photo style` and `### Prompt template for a key
visual`. Read the heading's own Do and Don't lines first and the rest of the file for older
prompts. Where a new line disagrees with them, ask the owner which holds and write only that.

For a site with no pictures yet, the first steps are the ones in the Batch Generation Workflow of
[ai-image-prompting.md](ai-image-prompting.md): make three or four, pick one. Then write the style
from the picture picked and mark it "from one picture".

## Worked example

Made up: a bakery, `baeckerei-petra.de`, three key visuals.

```markdown
### Photo style
- **Scene:** inside the shop and the back kitchen, in the early morning; nothing outdoors
  except `photo-2` (the market stall, an exception).
- **People:** one or two staff at work, looking at the bread or at each other, not at the
  camera (`photo-3`, a customer smiling into it, is an exception).
- **Clothes and props:** white aprons, flour on hands, wooden boards, baskets, paper bags.
- **Light and colour:** soft window light from the left, warm, slightly muted; no flash.
- **Framing and shape:** medium shot at eye level; wide strip, about 3:2, where the page
  gives no other shape.
- **Avoid:** posed stock smiles, any readable text or logo (flour sacks and delivery vans
  included), real people without their written consent.

### Prompt template for a key visual
> Candid documentary-style photo, [shape, default 3:2 landscape]. [Place in the shop or
> kitchen] in the early morning. [One or two staff, what they do], aprons, flour on their
> hands. Soft warm window light from the left, slightly muted colour, medium shot at eye
> level. No text, no logos, no one looking into the camera.
```

The blanks are the only words that change from page to page. A picture for the opening-hours
page fills `[Place in the shop or kitchen]` with "the shop counter" and `[One or two staff, what
they do]` with "one assistant turning the sign on the door", and leaves the shape alone. A page
whose slot is a tall card fills the shape with "4:5 portrait".
