<!--
  Handover prompt (the words to ask a tool for the download package of ONE chosen variation).

  Only after the owner has picked her favourite, never before. The assistant fills [N] and gives
  the owner ONLY the text between the two marker comments, in her language. It names no tool.
  The package is asked for in the chat: she saves it wherever she likes and tells the assistant
  where (the path is recorded with her other choices; the intake copies it into brand-handoff).
-->

<!-- prompt:start -->
I have chosen variation [N]. Please give me a download package (a zip file) of that one variation only. It should hold:
- its SVG file in the colours,
- its SVG file in a single colour,
- and a short README that says what each file is.

Both SVG files should be plain: a square drawing with a viewBox, flat shapes each written out with its colour directly on it as a hex value, sizes as plain numbers (no mm, pt or em), no gradients, no masks, no dashed or dotted outlines, no reused shapes, no scripts, no embedded pictures, no style sheet, no DOCTYPE line at the top and no text that depends on a font.
<!-- prompt:end -->

## Words for the owner

Tell her, in her language: ask for the package with the words above, save the file wherever she likes (the Desktop is fine), and tell you the full path of the file (or drag the file into the conversation). Then wait for it. The file is checked when it is put into the site, so she should keep the conversation with the tool open until then.

If she says it is saved but the path holds nothing, say so, and ask her for the path again. Never search her Downloads folder, or any other folder, on your own.

If the tool gives her no package, or she cannot find it, ask her to paste the code of that one variation's two SVG files instead. Save each, unchanged, as a file ending in `.svg`, and put the two into one zip (SKILL.md §5 has the command): the one-colour version can only be handed over inside a package.
