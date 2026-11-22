# Key visuals: reading a photo style and writing it down

What to look for in a site's pictures, how to check a line, and one example. The steps are in
the "Key visuals" section of `SKILL.md`.

## The six headings

Write one to three lines under each, read off the pictures, not off what the owner wishes.

| Heading | Look for | Often wrong when |
|---|---|---|
| **Scene** | The kind of place, what is going on | one picture is somewhere else (outdoors) |
| **People** | How many, what they do, where they look | "never at the camera" and one looks into it; "standing" and one pair sits |
| **Clothes and props** | What they wear and hold | it lists what one picture has |
| **Light and colour** | Daylight or lamps, warm or cool, how strong | "window light" and one is outdoors |
| **Framing and shape** | Distance, camera height, the shape of the slot | one slot's shape is written as the style's |
| **Avoid** | What the pictures leave out; what must never appear | a readable brand name in one picture is not listed |

The shape belongs to the page's slot (its component or CSS), not to the style: the template
carries the usual shape as its default.

## Checking a line against a picture

For every line and every picture, in writing: is this true of this picture? Yes or no, never
"mostly". A line a picture breaks is changed, or the picture is named in it as an exception
("except `photo-4`, outdoors"). Look in each picture for text, logos, liveries and faces: a
readable real brand goes under **Avoid**, and an exception never lets it onto a page; faces are asked
about once (real people? then her confirmed consent) before the style is written.

## Example

Made up: a bakery, `baeckerei-petra.de`, three key visuals.

```markdown
### Photo style
- **Scene:** inside the shop and the back kitchen, early morning; `photo-2` (the market stall,
  outdoors) is an exception.
- **People:** one or two staff at work, looking at the bread or at each other, not at the
  camera; `photo-3` (a customer smiling into it) is an exception.
- **Clothes and props:** white aprons, flour on hands, wooden boards, baskets, paper bags.
- **Light and colour:** soft window light from the left, warm, slightly muted; no flash.
- **Framing and shape:** medium shot at eye level; landscape, 3:2, where the page gives
  no other shape.
- **Avoid:** posed stock smiles; readable text or logos (flour sacks and vans included); real
  people without their consent.

### Prompt template for a key visual
> Candid documentary-style photo, [shape, default 3:2 landscape]. [Place in the shop or kitchen]
> in the early morning. [One or two staff, what they do], aprons, flour on their hands. Soft warm
> window light from the left, slightly muted colour, medium shot at eye level. No text, no logos,
> no one looking into the camera.
```

The blanks are the only words that change. For the opening-hours page: "the shop counter" and
"one assistant turning the sign on the door", shape left alone. A page with a tall card slot
fills the shape with "4:5 portrait".
