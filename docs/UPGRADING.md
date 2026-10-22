# Upgrading this site's Astro version

**For your AI assistant.** If you're a person reading this: just tell your AI assistant
"upgrade my site to Astro 7" — it will follow the checklist below. You don't need to run any
of these commands yourself.

## When this applies

Check `package.json` in the site root. If `"astro"` is pinned below `^7.0.0`, this checklist
applies. (Sites scaffolded via `npm create astro@latest` after ~2026-07 already got Astro 7
automatically and don't need this.)

## Before starting

Tell the site owner what you're about to do and why (a build-tooling version bump, not a
content or design change), and confirm they want it now rather than later.

Check the computer's Node first: `node --version` must be 22.23.4 or newer, which is what this version of the starter needs, and on Node 24 or 26 the fixed
version of that line. SETUP.md lists them; update Node before the bump when it is older.

## Steps

1. **Bump the dependency.** In `package.json`, change `"astro": "^6.0.0"` (or whatever's
   currently pinned) to `"astro": "^7.4.2"` (the floor the template currently ships). Run
   `npm install` to regenerate
   `package-lock.json`. Commit the lockfile — CI uses `npm ci`, which needs it.

2. **Do NOT bump `typescript` to `^7` in the same change.** Astro's own type-checker
   (`@astrojs/check`) doesn't support TypeScript 7 yet — its peer range caps at
   `typescript: "^5.0.0 || ^6.0.0"` (tracked at
   [withastro/roadmap#1321](https://github.com/withastro/roadmap/discussions/1321)). If a
   separate dependency update bumps `typescript` around the same time, don't merge both
   together — `npm run check` will break.

3. **Build first, before running the test suite.** `npm run build` (or `astro build`). Astro
   7's compiler is stricter about malformed HTML — unclosed tags/attributes now throw instead
   of being silently auto-corrected. If something's genuinely broken, this is where it
   surfaces, with an exact file:line. Fix the real problem; don't work around it.

4. **Set `compressHTML: true` in `astro.config.mjs`.** Astro 7 changed how whitespace
   between inline elements renders by default (`compressHTML` now defaults to `'jsx'` — it
   collapses whitespace using JSX rules instead of the old lossless behavior). This isn't
   just a layout edge case: a source line-break between two inline elements, OR inside a
   paragraph where a sentence wraps around a link or `<strong>` tag, collapses to ZERO
   characters instead of a space — a completely normal way to write prose, confirmed to
   break real body text (not just footers/nav) on a live site during this toolkit's own
   Astro 6→7 migration (2026-07-16). Setting `compressHTML: true` restores the old
   "lossless" behavior (still compresses, just keeps a rendered space where one exists in
   source) and eliminates the whole bug class at the config level — a source-level fix,
   not per-paragraph patching that a future content edit can silently undo. Sites scaffolded
   from this toolkit after 2026-07-16 already have this set; this step is for existing sites
   upgrading in place.
   - Belt-and-suspenders: build the OLD version to a SEPARATE directory before touching
     anything (e.g. `npm run build && mv dist dist-before-upgrade`, or use a git worktree) —
     the upgrade build will overwrite `dist/` otherwise, and you need something to diff
     against.
   - After the upgrade build (with `compressHTML: true` set), spot-check rendered pages —
     footer, nav, AND body prose with inline links — against `dist-before-upgrade` to
     confirm nothing runs together. `compressHTML: true` should make this a formality, not
     a hunt.
   - If the site uses `scripts/anchor-ids.mjs` (heading auto-ids), re-run it and diff the
     generated `id`s against the pre-upgrade `dist/`. A shifted id silently breaks any
     hand-authored `#fragment` link elsewhere on the site or from outside it.

5. **Check for double-escaped HTML entities in JSX-style string props.** Astro 7's compiler
   no longer decodes an HTML entity written inside a quoted string attribute value before it
   reaches an auto-escaping `{expr}` — so `<PageHero title="Partners &amp; Jobs">` (which
   round-tripped correctly under Astro 6: entity decoded on parse, then re-escaped on render)
   now double-escapes to literal `Partners &amp;amp; Jobs` text on the page. Confirmed on a
   real site during this toolkit's own migration (2026-07-17) — 3 page `<h1>`s silently showed
   raw `&amp;` in the browser after the bump.
   - Grep the whole `src/` tree BEFORE building:
     `grep -rnE "=['\"][^'\"]*&(amp|lt|gt|quot|#39|apos);" src/`. Any hit is a component prop
     value (not raw HTML markup — those don't need this fix) — replace the entity with the
     literal character (`&amp;` → `&`, `&lt;` → `<`, etc.); Astro's `{expr}` re-escapes it
     correctly on render regardless of version.
   - This bug is easy to miss because the page still builds and every automated test still
     passes — it's a rendering-correctness issue, not an error.

6. **Diff the full rendered text of every page against the pre-upgrade build.** The
   before/after technique from step 4 (`dist-before-upgrade/` vs the new `dist/`) is worth
   running as one systematic pass rather than a footer/nav spot-check — it catches BOTH the
   whitespace-collapse class (step 4) and the entity double-escape class (step 5) for free,
   and scales to every page instead of the ones you thought to look at. Strip tags/scripts/
   styles from each page in both builds and diff the extracted text; any page that differs
   needs a manual look. On a 32-page real site this caught 3 pages step 5's grep also found
   independently — cross-checking both ways is what surfaced the full picture.

7. **Smoke-test the sitemap.** As of this writing, `@astrojs/sitemap` hasn't been separately
   re-certified against Astro 7 by its own maintainers. Confirm `dist/sitemap.xml` (or
   `dist/sitemap-index.xml`) still generates, with the expected URL count.

8. **Run the full test suite.** `npm test`. A pass here does NOT substitute for steps 3–6 —
   none of the a11y/seo/navigation/anchors/orphans/images/tone/positioning/placeholders/email/
   links/llms-coverage/middleware specs do visual-regression or before/after diffing, so they structurally
   cannot catch the whitespace-collapse or entity-escaping risks above.

9. **Using Keystatic as a CMS?** Its Astro integration's compatibility with Astro 7 hasn't
   been separately verified. Check `@keystatic/astro`'s current release notes before assuming
   it still works, rather than finding out from a broken build.

10. **Report back to the owner in plain language**: what changed, what you checked, and
    anything that needs a human look (e.g. "the footer looked right, but double-check the nav
    on your phone" if you couldn't verify something visually).

## Why these specific steps

This checklist reflects issues actually found and verified during this toolkit's own Astro
6→7 migration (2026-07-16) and two subsequent real-site upgrades (2026-07-16/17) — it's not
generic upgrade advice. If Astro ships another major version later, this file should be
rewritten for that transition rather
than assumed to still apply as-is.
