# Plan: logo exports the brand kit refuses, and has no way out of

Plan for six open rows of `docs/BUGLOG.md` dated 2026-10-13 (`_svg.py`: clip-path ids, the DOCTYPE
refusal, refused exports with no way out, pasted SVG code; `_css.py`: class names; `_install.py`: the
`currentColor` note), and a seventh, "refused exports" (`_svg.py`), that it leaves open. Written against
origin/main `5c379979`, branch `fix/brand-kit-refusals-035`. Release 0.35 wants a clean plate (the
maintainer, 2026-11-09: "Yes, sweep first").

## Status

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ▶ revised after PLAN round 1 and the red team | this file |
| 2 | PLAN gate (Normal) | ▶ round 1: 4 BUG, 5 RISK; round 2: 2 BUG, 9 RISK, 5 NIT; round 3: 1 BUG (a wording slip), 2 RISK, 4 NIT; all answered here | 122,048 + 126,490 tokens |
| 3 | Red team (an Opus subagent told to attack the plan) | ✅ 10 findings, answered here | 211,159 tokens |
| 4 | The maintainer's go to build (it widens what a sanitizer of untrusted files accepts) | ✅ 2026-11-09, "Build + matplotlib" | his answer in the building session |
| 5 | Build, tests, `make check` | ✅ full suite 1,106 tests (with sharp 0.35.5): all pass but timing tests that failed under a load average of 95–190 and pass alone; `make check` passes; Chromium 152 draws 59 original/cleaned pairs the same | this PR |
| 6 | DIFF gate (Normal: shipped code and skill text) | ✅ round 1: 3 BUG (one a 14 s backtracking hex escape), 1 RISK, 2 NIT, all answered; round 2: 0 BUG, 1 RISK (answered by a sharp comparison), 2 NIT; fresh-eyes (Sonnet): 0 BUG, 3 RISK, 6 NIT, the cheap ones fixed. The last commit changes one error sentence and tests only; no external round of its own, see the trail | `docs/reviews/REVIEW-diff-2026-11-09-brand-kit-refusals.md` |
| 7 | PR, merge go, merge | ⏸ | — |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked

## What and why

An owner's real logo export is refused, and for some the refusal gives no way out. Each row was re-run on
origin/main first (a probe file per row; the output goes in the PR).

| Row | Holds on main? | Decision |
|---|---|---|
| clip-path ids with a digit first | No: `_IDENT` takes a digit first, and `test_svg_safety.py:162` has the case | Close the row with the PR's probe output (a digit-first id passes on main) and the existing test as the regression guard. No code. |
| DOCTYPE | Yes: the standard SVG 1.1 DOCTYPE is refused | **Widen, narrowly** (A). |
| class names, `.sm\:flex` | Yes: any backslash outside quotes is refused | **Widen, narrowly** (B). |
| no way out: `image-rendering`, `-webkit-print-color-adjust`, `overflow`, `isolation`, `stop-color` in a style; a `fill-opacity: 0` path | Yes (as an attribute, `overflow` is already left out) | Drop the five (and two near siblings, `print-color-adjust` and `color-adjust`) where they cannot change the drawing (C); a drawing element with `fill-opacity: 0` paints no fill (D). |
| pasted code, undeclared prefix | Yes: "not readable as an SVG (unbound prefix)" | The message names the prefix and says to paste the whole drawing (E). |
| `currentColor` note | Yes: a `currentColor` group holding `<g color="#7a2e0b">` is read under `#7a2e0b` and refused `colour-current` under `#2255aa` (probe, 2026-11-09) | The note says what really helps (F). |
| refused exports (`<use>`, `<mask>`, opacity) | Yes | **Not in this PR**: see "Left out". |

## How

**A. DOCTYPE.** Before the parse, `_svg` takes off ONE declaration. Expat then parses the file as if the
declaration had never been written, which is what the old refusal told the owner to do by hand. So the
parser's hardening is untouched: `StartDoctypeDeclHandler` still refuses every other DOCTYPE,
`SetParamEntityParsing(NEVER)` and `UseForeignDTD(False)` stay. (Measured 2026-11-09, Python 3.13 / expat
2.7.4: if the declaration is KEPT and expat accepts it, `fill="&brand;"` is read as `fill=""` with no error and
no skipped-entity call. That is why it is taken off and not accepted.)
- The pattern is a byte regex, case-sensitive, no flags, anchored at the start. The prolog it skips is
  written EXACTLY as XML writes it, because a looser comment lets the match run across the root and strip a
  declaration that comes after it (red team, ran): `\A` + optional BOM + optional
  `<\?xml[ \t\r\n][^>]*\?>` + `(?:[ \t\r\n]|<!--(?:[^-]|-[^-])*-->)*` +
  `<!DOCTYPE[ \t\r\n]+svg[ \t\r\n]+PUBLIC[ \t\r\n]+` + one of two quoted public ids + `[ \t\r\n]+` + the
  quoted address that goes with it + `[ \t\r\n]*>`. Blanks are XML's four, never `\s` (that takes a form
  feed). Each repeated group's alternatives start with different bytes, so a failed match costs one pass; the
  first draft in the red team's hands (`+` on the blank alternative) took 64 seconds on 27 bytes.
- The two pairs, each in double or in single quotes: SVG 1.1 `-//W3C//DTD SVG 1.1//EN` with
  `http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd`, and SVG 1.0 `-//W3C//DTD SVG 1.0//EN` with
  `http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd`. Both answered 200 on 2026-11-09 and name that
  public id; neither holds a general entity (`<!ENTITY` not followed by `%`: 0 and 0). Older Illustrator's
  `SVG 20010904` id, Basic and Tiny stay refused, with the old message.
- A comment is consumed as a comment, so a declaration written inside one is never matched or changed. UTF-16
  files, a declaration after the root, `<!doctype`, another address, SYSTEM alone and square brackets are
  not matched and keep the old refusal.
- `clean_svg` strips into a local name and keeps `data` as it came, so the package file name stays in
  every refusal (`isinstance(data, Member)`). Expat's error positions are those of the stripped text; the
  prefix message (E) reads the same text, and no message quotes a position.
- When a file was stripped and then meets "a name nothing defines" (`&nbsp;` in a title), the message says
  what is true: this check reads the standard DOCTYPE without definitions, so put the character in its place
  or take the name out. It does not say a declaration "was deleted". Unstripped files keep the old sentence.
- Stated limit, not measured in a browser: neither a browser nor this check reads the DTD's attribute defaults.

**B. Escaped class names.** `_css.parse_stylesheet` reads an escape only in a CLASS part of a selector (the
text before `{`).
- Order, which matters: comments are taken out first (`check_text` already returns the text with them
  blanked, and a backslash means nothing inside a comment: `/* a\*/ .b{...}` still applies `.b`). Then the
  escapes are masked, then the existing checks run on the masked text.
- After a backslash there may be one of these 17 characters, or a hex escape of 1 to 6 digits and one
  optional blank: `:` `/` `.` `%` `!` `#` `+` `=` `~` `*` `&` `$` `<` `>` `?` `^` `|`. Every other backslash
  is refused as now: `{ } ; , ( ) " ' [ ] @`, the backslash, the backtick, `-`, `_`, letters and digits
  that are not hex. A backslash in a tag name or an id part is refused as now (a browser reads `p\61 th` as
  `path`; this reader would not): the escape-aware pattern accepts it in `.class` parts only. Each masked
  escape is replaced by underscores of the same length, so braces, quotes and backslashes are checked
  everywhere else (declarations, values, ids, attributes) as before, and the positions line up.
- The selector is read from the original text, token by token: each escape is decoded INSIDE its name and
  the decoded text is never split or parsed again (`.a\2e b` is the one class `a.b`, not `a` and `b`). A
  decoded name is visible ASCII, 1 to `MAX_CLASS` (200, the `class` attribute's own cap); a decoded `"`, `\`
  or `{` is a character of a name that is only compared as a string. `_classes` keeps every name of the
  `class` value, where it kept only names a selector could spell. A rule that would not match is dropped,
  never applied wider. The output never holds a stylesheet. A mis-cut selector can change more than colour: the
  cascade also carries `display`, `visibility`, clipping and stroke geometry, so the worst case is a shape that
  disappears or clips wrongly. Hence the tests below for those properties.
- The BUGLOG row names exactly which escapes now pass (the 17 characters, and hex escapes that decode to a visible ASCII character); a class with an escaped
  space, `\-`, `\_` or `\)` keeps the old refusal, and the row says so.
- `_palette.py` has its own stylesheet reader and is not touched; the `.sm\:flex` tests in
  `test_cli_palette.py` belong to it.

**C. Properties that cannot change a drawing of shapes.** In `_accept`, after `NO_EFFECT` (which stays as it
is: `auto` stays silent), these are left out of a style with ONE note, any value, as `PROPS_DROP` does:
`image-rendering` (pictures only; `<image>` is refused), `print-color-adjust` and `-webkit-print-color-adjust`
(print only), `overflow` (as the attribute already is), `isolation` (matters only beside `mix-blend-mode`,
`filter`, `mask` or opacity, each refused or removed), `stop-color` (only in `<stop>`, refused), and `color-adjust` (the old name of `print-color-adjust`). Checked:
the cleaned file is used as `<link rel="icon" href="/favicon.svg">` (`Base.astro:148`) and drawn into PNGs,
never inlined (grep of this repo: the only use is the starter's `<link rel="icon">`, `Base.astro:148`), and the red team drew a root `overflow` of none, visible and hidden in Chromium (`<img>`) and
librsvg 2.63.4: no pixel differs. `ALLOWED_ELEMENTS` is `DRAWING | CONTAINERS | {style}`; `REFUSED_ELEMENTS`
holds `image`, nested `svg`, `marker`, `pattern`, `foreignObject`, `mask`, the filters, `stop` and the
gradients. Two guards: a test that `ALLOWED_ELEMENTS` equals the exact expected set (any addition fails and
says to re-read this paragraph), and a nested `<svg>` run through `clean_svg` inside an accepted root `<svg>`
is still refused.

**D. `fill-opacity: 0`.** In `_paint.resolve_paints`, on an element whose tag is in `DRAWING` (`path`, `rect`,
`circle`, `ellipse`, `line`, `polyline`, `polygon`: leaf shapes, no text and no children to override the fill; not "has no
children": an empty `<g/>` has none), `fill-opacity` of exactly 0 makes the written fill `none`: the cleaned
file paints what the original did and the fill's colour is not counted. A stroke on it is untouched. Any other
value but 1, and any `fill-opacity` on a group, stays `colour-alpha` (an inherited 0 would need the children
rewritten). `opacity: 0` and `stroke-opacity: 0` are not read. Precedence is already right: the cascade runs
before `resolve_paints` (`_svg.py` `_finish`; style, then rule, over attribute), and two tests pin it: an attribute `fill-opacity="0"` overridden by an inline style, and by a stylesheet rule on the same shape, both stay painted. The red team found a child with `fill-opacity: 0`
clips as one without in librsvg (identical PNG bytes).

**E. Unbound prefix.** On expat's unbound-prefix error, a second small parse of the same (stripped) text
records the prefixes in scope with expat's own `StartNamespaceDeclHandler`/`EndNamespaceDeclHandler`, so scope
is expat's, not a search of the file (measured 2026-11-09: a declaration on an ended sibling is gone; one on
an open ancestor is there; one on the failing tag itself is not yet recorded). The start tag at the reported
place is split into names with a quote-aware pattern (values skipped whole, a `>` inside quotes included, so
`data-x="foo:bar="` and `data-x="a>b"` are no names). The prefixes are those of the element name and the
attribute names, minus `xml`, `xmlns`, those in scope and those the failing tag declares itself (`xmlns:NAME`
among its own names). The first left is named; the message says to copy the whole drawing, from `<svg` to
`</svg>`, because the opening tag holds the declarations. None left, or a tag that does not split cleanly: the
sentence without a name.

**F. The `currentColor` note.** A mark whose `currentColor` group sets `color` to the Primary reads only
under that Primary, so `_given_in_current` reports it as given in `currentColor` with a colour of its own.
Run again with the package under another Primary it is refused `colour-current`, though the note said to.
The red team ran the refusal's own advice, "every colour written out": it cleans to the OLD colour, so it is
no way out either. The note keeps its sentence and adds one that is true: if that run is refused over
`color` set inside a group painted with `currentColor`, this logo cannot be drawn in another Primary from that
file; ask the design tool for the mark in the new colour with every colour written out, or in `currentColor`
alone. It is added under the one variable that line is written and read back with (`own_too`, from `_given_in_current`'s
`its_own`), so the sentence and the line cannot disagree; the note of a mark without it is unchanged. That line also marks a legitimate mark (a
part in `currentColor` beside a part written in the Primary), whose package run works; the sentence is
conditional ("if that run is refused"), so it is true for both. The refusal's own text in `_paint.py` is not
changed here.

**Words that become false, changed in the same PR.** `_svg.py` lines 11–12 (module docstring) and 788–797 (the
DOCTYPE comment), the `DOCTYPE`, `DOCTYPE_DEFINES` and `NO_SUCH_NAME` sentences, the `NO_EFFECT` comment
(363–365) and the grammar paragraph at 148–151; `_css.py` line 9 and the `_classes` docstring; SKILL.md's
DOCTYPE bullet (and no more lines: it is 549 by `wc -l` today, the BUGLOG row's 526 is out of date); and one
"changed since" line in `docs/reviews/SKILL-PLAN-website-brand-kit.md` where it says every DOCTYPE is
refused (two places, lines 501 and 525; each gets the same short line). The old trail is history and stays.

## Tests

Each says WHY. Entries are the ones production uses: `clean_svg` on file bytes, and the command
(`brand_intake.py install --input` through the existing `intake` helper; `through_the_command` only
dry-runs).
- A, reads: both pairs, both quote kinds, XML's four blanks, with the XML declaration and Illustrator's
  comment in front: the cleaned text is byte-equal to that of the same file with no declaration (the
  invariant), and the command installs it. A package file keeps its "In the package, the file ..." name when
  refused after the strip. The standard-DOCTYPE file with `&nbsp;` gets the new sentence.
- A, refuses (each must still be refused as before): right id with another address; SYSTEM alone; square
  brackets (with `&ns_svg;` as in the existing cases); a second declaration; one after the root, including
  `<!-- a --><svg ...>...</svg><!-- b --><!DOCTYPE ...>` (the red team's file); `<!doctype`; a form feed or a
  no-break space between words; UTF-16; `<?xml-stylesheet?>` before a standard declaration; `&brand;` after the
  strip. Read as before: a declaration inside a comment or a `<style>` CDATA.
- A, time: the pattern on inputs that do NOT match (the case the first draft failed): 100,000 blanks then
  junk, 60,000 comments then junk, an unterminated comment, an unterminated declaration, a 512 KB file of each;
  each under a second. A file that matches at once proves nothing.
- B, reads: `.sm\:flex` and `.sm\3a flex` paint `class="sm:flex"`, not `class="smflex"`; `.sm\3aflex` matches
  nothing (the `\3af` is one escape); `.a\2e b` matches `class="a.b"`, not `class="a b"`; `\22`, `\5c`, `\7b`
  are names; `/* a\*/ .b{fill:#00ff00}` still applies `.b`; a 65-character class paints. Compared with
  Chromium for each of these (the red team's method); drawn both ways at 32 and 512 pixels.
- B, other properties: `.a\:b{display:none}` hides exactly `class="a:b"` and nothing else; an escaped rule that sets `clip-path` or a stroke width applies to that element only.
- B, refuses: a backslash in a declaration, a value, an id or a tag part (`p\61 th{...}`); `\{ \} \; \, \( \" \[ \@
  \\ \`` and `\-`, `\_`; a trailing backslash; a hex escape to a blank, a line break or a control; a name over 200.
- C: each of the five, any value, is left out with one note and the drawing renders the same as without it
  (`test_render.py` harness, 32 and 512 pixels; the `overflow` fixture has geometry OUTSIDE the root viewport, e.g. a rect at -20,-20 sized 104 on a 64 viewBox, with the rule `svg{overflow:visible}`, else the check passes vacuously); `auto` stays silent; `isolation` beside `mix-blend-mode` is
  still refused; the viewport guard above. The existing rows that expect these refused move (below).
- D: `fill="red" fill-opacity="0" style="fill-opacity:1"` stays red (the style wins); a page-sized path with `fill-opacity: 0` and a real mark beside it: colours and pixels are the mark's
  alone; the same path WITH a stroke keeps the stroke in both; `.5`, `0` on a `<g>`, and `0` set by a rule
  on a group still give `colour-alpha`.
- E: `<g xmlns:xlink="urn:x"/><rect xlink:href="#a"/>` names `xlink` (a sibling's declaration is out of scope); a declaration on an open ancestor, or on the failing tag, does not suppress other prefixes; `data-x="a>b"`; names `xlink` and `inkscape`; not `xml` in `<svg ... xml:space="preserve" inkscape:version="1"/>`; not a
  declared `xlink` in `... xmlns:xlink=... xlink:title="a" sodipodi:docname="x"`; not `foo` in
  `<rect data-x="foo:bar=" xlink:href="#a"/>`; the same file with a standard DOCTYPE in front names the same prefix.
- F, both branches: a mark with a `currentColor` group that sets `color` to the Primary is installed, the
  palette changed, the run printed: the note carries the new sentence; the run with the package under the new
  Primary is refused `colour-current`. A mark without the favicon line's "own" sentence gets the note unchanged.

**Tests that encode the old rule move, not weaken.** Found by the red team (grep): `test_svg_safety.py`
163/168/169 (201–203), 273, 323 (a safety-table row, "a plain public DOCTYPE with no entity at all"), 409–420
(the `plain` forms), 493; `test_input_forms.py` 446–476, 482–510, 1437; `test_svg_safety.py` 2851 and 2878
(`-webkit-print-color-adjust`, `isolation`, `image-rendering` refused). Each moves to a non-standard DOCTYPE
or to the new behaviour with its new reason; none is deleted, and the refusal they guarded keeps a test.

**Evidence kept.** The reviewers cannot see the red team's runs, so the PR carries them: the probe files and
results (Chromium `<img>` and librsvg 2.63.4 renders, B's browser comparison, the DTD fetches with their
`<!ENTITY` counts, the expat snippet). The librsvg comparisons for C and D also run as tests in the
`test_render.py` harness, so they are re-run by CI. The Chromium ones are by hand at build.

**Real captures (Rule 5).** DOCTYPE: a real export is wanted. No Inkscape or Illustrator is installed;
matplotlib is not installed either, and its SVG writer is expected to write this DOCTYPE (confirmed only when the capture is made). The plan is to ask
the maintainer for leave to install matplotlib in a throwaway virtual environment (one download from PyPI),
save one trimmed plot, and commit it as `matplotlib-<version>-svg11-doctype.svg`; if he says no, the PR says
a capture was not made and why. B, D and E are built from the rows' words: no tool that writes them is at
hand, and the PR says so.

## Left out, with reasons (the manager has the first; the rest are told in the PR)

- **Row "refused exports"** (transparency, `<use>`, `<mask>`): its own fix line says to count them on real
  exports first, and none are at hand. Each refusal already names its way out (re-export flat). `<use>` needs a
  cycle and expansion cap, `<mask>` a second rendering model: a different plan. The row exists (2026-10-13,
  "refused exports"); this PR rewrites its text with what was decided and why and adds no second row, which
  `scripts/check_buglog_rows.sh` would refuse. The clip-path row is closed in the same PR with its evidence.
  The six rows this PR fixes are closed in it.
- `opacity: 0`, `stroke-opacity: 0`, escaped ids and tags in selectors, Basic and Tiny DOCTYPEs.

## Risks and how this fails

- A: the parse is of the file minus one literal declaration, so a file hostile with it is hostile
  without it. The one new input is the pattern, so its exactness and its time are tested above.
- B is the widest: a mis-cut selector applies a rule to the wrong element (wrong colours, or a shape hidden or clipped wrongly). The order (comments,
  mask, existing checks), the 17-character list, `.class`-only escapes and Chromium comparison are the guards.
- Churn: nine or more test sites change (above); expect review rounds there.
- Rollback: one PR, nothing stored, `git revert`.

## Cost

Steps 2 and 3 together were estimated at 150,000 to 400,000 review tokens. Spent so far: PLAN round 1
122,048 (Codex 94,836, GLM 27,212), the red team 211,159 (one Opus subagent, 39 tool calls, 18 minutes) and
PLAN round 2 126,490 (Codex 92,643, GLM 33,847): 459,697, past the top of the estimate. Round 3 is a
confirmation of the fixes below.
