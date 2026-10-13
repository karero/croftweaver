<!--
  Logo prompt (the question to put to a design tool for five variations of a simple mark).

  Written AFTER the palette is chosen, because it carries those colours. The assistant fills every
  [BRACKET] and gives the owner ONLY the text between the two marker comments, in the language she
  writes in. It names no tool and says nothing about what a tool can or cannot do.

  Where the slots come from:
    [WHAT THE BUSINESS DOES], [WHO IT IS FOR], [WHAT MAKES IT DIFFERENT]  POSITIONING.md (and STORY.md, if the owner chose it)
    [THE FEEL]                                                             the owner's own answers
    [PRIMARY], [ACCENT], [LIGHT BACKGROUND], [DARK BACKGROUND]             the chosen palette (BRAND.md's tables): Primary, the LIGHT
                                                                           theme's Accent, and the two themes' Background rows; where
                                                                           she brought her own colours, hers; where she wants no help
                                                                           with colours, the site's current ones (SKILL.md §0)
  The mark has no words in it: letters drawn by a font are left out on purpose (the intake refuses a
  file that depends on a font).
-->

<!-- prompt:start -->
I need a logo mark for a website. Please design FIVE different variations.

About the business
- What it does: [WHAT THE BUSINESS DOES]
- Who it is for: [WHO IT IS FOR]
- What makes it different: [WHAT MAKES IT DIFFERENT]
- The feel: [THE FEEL]

The colours to use
Draw the mark with these colours and no others:
- [PRIMARY] (the brand colour)
- [ACCENT]

The mark will sit on two pages: [LIGHT BACKGROUND] in the light theme and [DARK BACKGROUND] in the dark theme. Do not paint any shape in those two colours, and do not put a background shape behind the mark: the page shows through. Choose shapes that can be seen on both pages.

What each variation must be
1. A simple vector mark, drawn as an SVG file. If you cannot draw a vector (SVG), tell me so now instead of making a picture; I will get an SVG from someone who can.
2. Flat shapes only, each one written out in the file: no gradients, no shadows, no transparency, no blur, no masks, no dashed or dotted outlines, no reused shapes (`<use>`), no photos, no embedded pictures. Put each colour directly on its shape: no style sheet in the file, and no DOCTYPE line at its top.
3. No text of any kind, and no letters that depend on a font. If letters are wanted, draw them as shapes.
4. A square drawing with a viewBox, with the mark filling most of the square. Write every size and position as a plain number (no mm, pt or em) and every colour as a hex value such as `#1a2b3c`.
5. It must still read at 16 pixels wide, so keep it bold and simple, with few parts.
6. Each variation comes in two versions: one in the colours above, and one in a single colour (the brand colour) only.
7. Number the variations 1 to 5 and name each file with its number.

Please do not copy or imitate an existing logo.
<!-- prompt:end -->

## Words for the owner

Say these in her language, in your own warm words, when you hand her the prompt:

1. **Rights.** Before you rely on a mark, check the tool's terms for commercial use, and look for a lookalike. This is not legal advice.
2. **If the tool cannot draw a vector (SVG).** Do not settle for a picture. Use a tool that can draw one, or ask someone who can for an SVG.
3. **What comes next.** Look at the five variations. Which one do you like best? (The assistant then gives her the words to ask for the download package: `templates/handover-prompt.md`.)
