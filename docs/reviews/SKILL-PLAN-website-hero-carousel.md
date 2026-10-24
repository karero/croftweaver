# Skill plan — `website-hero-carousel` (an auto-rotating photo place with dots)

> **Status 2026-10-23: PLAN, not built.** Asked for by the maintainer the same day, after two sites
> built the same thing in a week. Nothing below exists yet; the sources are the two
> implementations named under "Sources".

| Step | State | Evidence |
|---|---|---|
| 1 Plan written | done | this file |
| 2 PLAN review (independent-review, High) | open | — |
| 3 The maintainer's go | open | — |
| 4 Skill built (component, script, spec, SKILL.md) | open | — |
| 5 Installed into a scaffolded site and the spec green there (CI job) | open | — |
| 6 DIFF review | open | — |
| 7 README, `new-website`, `website-qa`, `WHAT-THE-SKILLS-RUN` hooks | open | — |

## Why

Two sites built by the maintainers each built "photos that rotate by themselves, with dots at
the bottom". The two differ (cross-fade vs instant swap; slides link to projects vs not; a Pause
button vs none) and each found things the other missed:

- **The second site** (the one with the project carousel) found that a phone downloaded every slide at full width, that its 10 px dots failed the touch
  target minimum (WCAG 2.5.8, Level AA: 24 by 24 CSS px, unless undersized targets are spaced clear of each
  other; read on w3.org 2026-10-23) until each sat in a 28 px button, and that hidden slides must not compete
  with the first for the connection.
- **The first site** (the one with the stage) found that a caption under only one photo makes the page jump when the photo
  changes, that white dots vanish on a pale part of a photo (measured 1.8:1 on the real picture)
  and need a dark pill, that a dot's "selected" look must survive forced colours, and that a
  frozen clock is the only way to test timing without flaking.

The expensive part was the tests, not the markup. A third site would redo about a day of it.

## What the skill adds to a site (four files, like `website-contact-form`)

| File | What it is |
|---|---|
| `src/components/HeroCarousel.astro` | the static markup (all slides, in order, with their alt text), the dots, and the styles |
| `public/js/hero-carousel.js` | a script of the site's own (no inline script: a strict `script-src 'self'` holds) |
| `tests/hero-carousel.spec.ts` | the behaviour as a visitor meets it (list below) |
| the skill's `SKILL.md` | when to use it, the choices below, the install steps, the way back |

### Contract (what the component promises)

1. **Without JavaScript** the slides stand one under the other, nothing is hidden, no control is shown.
2. **With the script ready** the slides share one grid cell: the box is as tall as the tallest slide, so the
   page cannot jump when the photo changes (this was the bug on the first site). A slide not on show is
   `visibility: hidden` (not in the tab order, not announced), so a link on it cannot be focused; the spec
   checks, among the slides' own links, that Tab reaches only the visible slide's (the dots and the Pause
   button are tabbable separately), and, in the accessibility tree (`ariaSnapshot`), that the content of a slide
   not on show is absent.
3. **Dots** on the bottom edge of the photo, on a dark pill (white on the pill is at least 3:1 even over a white
   photo, computed in the test and read from rendered pixels), 32 px targets, 44 px on touch screens; the
   dot on show differs by a thick border as well as the fill, so it survives forced colours.
4. **Rotation rules:** starts by itself (default 6 s); holds while the pointer is over it and while the tab is
   hidden; keyboard focus entering from outside stops it, and it stays stopped until the visitor presses Weiter
   (button mode) or reloads (dots mode: it never resumes by itself); reduced motion starts it stopped; a slide is shown
   only when its image is complete (a late or failed second image never leaves a blank slide).
5. **Pause setting `pause`:**
   - `"button"` — **the default**: a visible Pause / Weiter button (the text in the site's language). WCAG 2.2.2
     (Level A) asks, for moving content that starts by itself, lasts more than five seconds and is shown beside
     other content, for "a mechanism for the user to pause, stop, or hide it". Its definitions, read at
     https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html on 2026-10-23: *pause* is "stopped by user
     request and not resumed until requested by user"; a *mechanism* is a "process or technique for achieving a
     result" that may be in the content or in the user agent; the page does not say it must be visible, and it
     does not discuss slide indicators at all. A visible button is the reading nobody can dispute and the one a
     visitor finds;
   - `"dots"` — no button; choosing a dot stops the rotation until the visitor reloads. That is likely a
     mechanism in the sense of 2.2.2 ("stopped by user request and not resumed until requested"), but it is
     **not discoverable** (nothing says that a dot stops it), so the SKILL.md says plainly that the owner trades
     a visible control for a cleaner photo, and chooses it knowingly (the first site to use it did). I told that
     site's owner it "fails 2.2.2 in its letter"; that was too strong, and is corrected there. **This plan draws no
     conformance conclusion**: whether a dot that stops the rotation is accepted is for the owner's auditor; what
     the plan fixes is the default (a visible button) and the plain sentence in SKILL.md.
6. **Swap setting `swap`:** `"instant"` (default) or `"fade"` (about 1 s; none under reduced motion).
7. **Images:** `Picture` with AVIF and a WebP fallback in four widths, `sizes="100vw"`; the first slide eager and
   high priority, the others eager with `fetchpriority="low"` (they must keep their space). A hint, not a
   guarantee: the spec asserts the attributes, and says in its comment that it cannot assert the network order.
8. **Optional `href` per slide** (the second site's slides link to projects). The link is the photo; the dots are buttons
   in their own box that is not inside the link, so a tap on a dot cannot open the project and a tap beside
   the dots does. The spec clicks: a dot changes the slide and leaves the address as it was; a click on the
   photo away from the dots goes to the slide's `href`; inactive slides' links are not reachable by keyboard.
9. **No captions or credits on the slides** in v1 (they were what made the page jump). A credit belongs in the
   site's image-credit page; the SKILL.md says so.

### Not in v1 (said so, so nobody assumes)

Prev/next arrows (the second site has them), swipe, a caption overlay, video slides, more than one carousel per page (ids are
fixed, as in the contact form), lazy loading of later slides.

## Tests the spec carries (taken from the first site's, made site-neutral)

Timing with a frozen clock (6 s, 12 s, not at 5,999 ms); `pause` modes (button pauses and resumes with the label
changing and no `aria-pressed`; dots stop for good); keyboard focus stops it, moving between controls does
not restart it, and focus leaving the carousel entirely leaves it stopped after more than an interval (Weiter resumes it in button mode); pointer hold and a fresh 6 s after leaving; reduced motion starts stopped; hidden tab; a late
second image; a failed second image; a pick for a late image waits for it; no JavaScript and `stage.js`-style
blocked script show every slide and no control; **no height jump** at 1280, 768 and 390 px, mutation-checked; targets
at 32 / 44 px; rendered dot-on-pill contrast over every slide's real photo at 390, 1280 and 1920 px; forced colours
(the dot on show differs, a focused dot shows a ring); axe at WCAG 2.1 A and AA in both themes; no storage, no
cookies, no request to another origin while it rotates; no horizontal scroll on a phone; strict CSP (the script is
a file of the site's own).

## How it is tested in the toolkit

**The photos in the CI page** are generated by the workflow step (three plain JPEGs made with the tools the
scaffold already has: one pale, one dark, one in 4:3), not committed, with **at least one slide that has an `href` to a known page of the scaffold** (so the link tests have a link to run against), so the contrast test meets a worst-case pale photo
every time and never passes only because the fixture was dark.

Like the contact form: a step in `.github/workflows/template-tests.yml` copies the templates into a freshly
scaffolded site, sets `PAGE`, the pause mode and the swap with `sed`, asserts the `sed` took, and runs the spec,
three times, so that every setting and the pairing the mid-fade assertions need are run: (`button`, `instant`), (`dots`, `fade`) and (`button`, `fade`). Two things the workflow needs
besides the step (a reviewer ran the existing selector with the skill's path and it answered "run = false"): the
path `skills/website-hero-carousel/` goes into the change selector at the top of the workflow, and the job joins
the final job's dependencies, results and count. The fade run adds: a rendered frame part-way through
shows both slides at an opacity strictly between 0 and 1, and the transition completes at about one second (the
outgoing slide ends at 0, the incoming at 1); a dot pressed mid-fade shows its slide at once; in the (`button`, `fade`) run, a pause or focus-stop mid-fade leaves one settled, correct slide; with reduced motion there is no
transition at all. Mutation-checked: with the transition removed the part-way assertion fails. A mutation check is run by hand once and recorded in the PR
(without the grid rules the no-jump test fails; without the pill the contrast test fails; without the thick border
the forced-colours test fails).

## Registration (the places a new skill must appear)

`README.md` (the setup-skills list and the paragraph under it), `skills/new-website/SKILL.md` (not an interview
question: an opt-in line in the home-page step and, if the owner asks, in the copy list), `skills/website-qa/SKILL.md`
(the row for a rotating hero, with one clause: in `dots` mode a dot choice stops the rotation until reload (keyboard focus entering also stops it, and reduced motion starts it stopped), and the 2.2.2 trade-off is described in `website-hero-carousel`'s SKILL.md, section "Pause", which is where an audit looks), `docs/WHAT-THE-SKILLS-RUN.md` (it runs `npm run check` and `npm test`, so it joins the list of skills
that run commands); `scripts/check_skill_budgets.sh` discovers skills by `FILES=(skills/*/SKILL.md)` (line 555) and
`for d in skills/*/` (line 563) and needs no edit (description under 1024 characters; the build ran it: 38 skills
checked, no hard-budget failure). `make check` runs `check_clean.sh`, which searches the files, binary ones included, for the maintainers' names,
contact details and credential patterns, and cannot establish an image's content or provenance: the skill's `templates/` hold **no image file at all** (the component takes the slides as props, the
spec reads them from the page), checked by listing the folder in the DIFF review.

## Sources

The first site's stage component, its script, its stage tests and its plan notes; the second site's hero carousel
component. Both are private repos: the skill is rewritten site-neutral, not copied.

## Judgment calls, flagged

- **Verified:** both implementations were read in full; the first site's tests pass (338 at the last run); the contrast
  and no-jump findings were measured in a real browser, not argued.
- **Judgment:** that a skill (and not a short note) pays off with only two instances, and that the default should
  be the Pause button. **Strongest counter-argument:** the two instances differ so much (fade, links, arrows)
  that v1 may freeze the wrong shape; the settings above are the hedge, and "not in v1" is the list of what may
  need a v2.
- **Open question for the maintainer:** the name. `website-hero-carousel` fits the other `website-*` skills; "carousel"
  is the word for a stage that rotates, but the owners of these sites say "key visual".

## Cost (my estimate)

PLAN review at High depth: 1 to 2 rounds, about 0.2 to 0.3 million tokens. Build: about 0.5 million (most of it
the spec, which exists and is being generalised). DIFF review at High: 2 to 3 rounds, 0.3 to 0.5 million.
