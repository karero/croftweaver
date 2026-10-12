# Astro starter overlay (the `new-website` kit)

A complete, opinionated overlay you drop on top of a fresh Astro project: the SEO +
theme spine, the test suite, security headers, the preview-noindex function, and CI.
Copy-and-go for an Astro → GitHub → Cloudflare Pages site. The `new-website` skill
drives assembly; this README is the manual reference.

## What's here

```
package.json  tsconfig.json  astro.config.mjs  playwright.config.ts
.nvmrc                        # Node 24 — Astro needs >=22.12 (Cloudflare Pages reads it)
.gitattributes                # LF line endings for *.sh and scripts/hooks/*, so the pre-push hook runs on Windows
src/config.ts                 # single source of truth (URL, name, analytics, EEAT)
src/layouts/Base.astro        # title/OG/Twitter/canonical/JSON-LD/no-FOUC theme spine
src/styles/global.css         # light/dark theme tokens (mirror BRAND.md)
src/pages/index.astro         # minimal home so the suite is green from commit 1
src/pages/privacy.astro       # GDPR privacy draft (fill [BRACKET] slots before launch)
public/{robots.txt,llms.txt,_headers,manifest.webmanifest}
functions/_middleware.ts      # noindex *.pages.dev previews; 301 <project>.pages.dev once CANONICAL_URL is set
.github/workflows/ci.yml      # astro check + the suite on push/PR
scripts/check_external_links.sh  # warn-only outgoing-link liveness sweep (network; not in CI)
scripts/check_internal_links.sh  # warn-only internal-link audit: orphan / thin / deep pages (offline; not in CI)
scripts/generate_og_cards.py     # branded 1200×630 OG share cards, one per page (npm run og)
scripts/run_og.mjs               # cross-platform launcher for the generator (forwards --check)
scripts/anchor-ids.mjs           # post-build: stable slug id on every h2/h3 (runs in `npm run build`)
scripts/build-marker.mjs         # post-build: the commit SHA into dist/build.txt, so `npm run ship` can check the live site has it
scripts/set_pdf_title.py         # sets a hosted PDF's title (Info dict and XMP), the fix when the SEO test flags one (needs pypdf)
scripts/ship.sh                  # `npm run ship`: two-stage sites only, promotes `main` (preview) to `production` (live)
scripts/hooks/pre-push           # blocks a push when the site's checks fail
scripts/wire-hooks.mjs           # run by "prepare" on every `npm install`, which fails without it: wires the pre-push hook
scripts/verify.mjs               # `npm run verify`: CI's install, check, build and test in one command; the pre-push hook runs it
tests/_helpers.ts  tests/{a11y,seo,navigation,anchors,orphans,images,tone,positioning,placeholders,email,links,llms-coverage,middleware}.spec.ts
tests/check_ship_push.sh      # offline gate: ship.sh's publish-failure diagnosis (pre-push hook + CI)
tests/check_analytics_gate.sh # counter self-test, CSP check, four builds: analytics on only when CF_PAGES_BRANCH is PROD_BRANCH (the suite's own CI)
```
Sibling files in the parent `templates/`: `.gitignore`, `SETUP.md`,
`claude/settings.json` (permission allowlist), `content-guide.md`, `brand.md`.

## Bootstrap a new project

1. **Git first** (see SETUP.md): `mkdir <site> && cd <site> && git init`, copy the
   `templates/.gitignore`, commit.
2. `npm create astro@latest .` → Empty, TypeScript **Strict**. Requires **Node ≥22.12**
   (Astro's own floor); the committed `.nvmrc` pins 24 for local + Cloudflare Pages builds.
3. Copy this overlay over the scaffold (the files above) + `tests/`, then:
   ```bash
   npm i -D @playwright/test @axe-core/playwright @astrojs/check typescript @types/node
   npm i @astrojs/sitemap node-html-parser
   npx playwright install chromium
   ```
   (Or copy this `package.json` and run `npm install`.) **Commit the
   `package-lock.json`** — CI uses `npm ci`, which fails without it.
   On **npm ≥11.16**, `install` prints "packages have install scripts not yet covered"
   for scripts it hasn't been told to trust — per npm's own docs this is currently
   advisory only (the scripts still run; a future npm release will start blocking them),
   but approve the one Astro needs now to silence the warning and be ready ahead of that:
   `npm approve-scripts esbuild`. (sharp no longer has an install script — since 0.35 it
   ships prebuilt binaries, so it needs no approval.)
4. Set the real domain in `astro.config.mjs` (`site:`) and `src/config.ts`
   (`SITE.url`, name, theme color, analytics: `scriptHost` and the per-site `scriptId`
   from Plausible's Site installation page — and check `PROD_BRANCH` matches the
   branch Cloudflare Pages will call "Production", or analytics never loads).
   Add `public/` icons; edit the placeholder `manifest.webmanifest`. Set the BRAND
   block in `scripts/generate_og_cards.py` and run `npm run og` to regenerate the
   1200×630 share cards (`public/images/og/`; the starter ships a default).
   Fill the `[BRACKET]` slots in `src/pages/privacy.astro`
   (controller, date, analytics wording — see the comment block in that file).
   In Plausible's installer, untick the optional measurements (outbound links,
   file downloads, form submissions), or keep the page's sentence for each one you leave ticked.
   For a ticked one, click such a link on the live site once and look for its address in the
   instance's report: the sentence says the address is sent and stored.
   Each target you fill here (privacy page, manifest) then comes out of
   `UNFILLED_UNTIL_LAUNCH` in `tests/placeholders.spec.ts`; the test is red until it does.
5. `npm run verify` (`npm run check`, then the tests, which build once) — the overlay passes strict TS +
   a11y/seo/navigation/anchors/orphans/images/tone/positioning/placeholders/email/links/llms-coverage/middleware out of the box. Then build pages
   test-first (`<Base title="…" description="…">`).

> `links.spec.ts` is the **offline** guard: it only blocks domains you've already
> retired (its `STALE_DOMAINS` list, empty at start) from creeping back in — it makes
> no network calls, so it stays in CI. The **liveness** sweep of the links you keep
> (are they still 200? did one rebrand?) is network-dependent and lives in
> `scripts/check_external_links.sh` + the `outgoing-link-audit` skill — run monthly /
> pre-launch, never in CI.

> `orphans.spec.ts` is the **internal**-link counterpart: it fails if any page in
> `PAGES` is unreachable from the home page by following internal links (a page in the
> sitemap that nothing links to). It's offline and in CI. The richer report — inbound
> link COUNT per page, "thin" pages with a single nav-only link, "deep" pages >3 clicks
> from home, and WHERE to add the missing contextual links per the `site-architecture`
> internal-linking strategy — is `scripts/check_internal_links.sh` + the
> `internal-link-audit` skill. Deliberately-unlinked pages (a paid-ad landing page) go
> in `ORPHAN_EXEMPT` with a reason rather than loosening the test.

> `llms-coverage.spec.ts` keeps `public/llms.txt` (the curated GEO page map) in sync
> both ways: every route in `PAGES` must appear in it as a markdown link to its full
> production URL, and every same-site page link in it must map back to a `PAGES`
> route (no stale entry after a page is removed or renamed). The file is
> hand-maintained, so it drifts silently otherwise. Deliberately-hidden pages (a
> paid-ad landing page — llms.txt is public, listing one would expose it to AI
> engines) go in `LLMS_EXEMPT` with a reason. Whether an entry's *wording* still
> matches the page stays a `website-review` / `website-seo-geo` judgment item.

> `placeholders.spec.ts` reads the **rendered** site for leftovers: each page's copy,
> head metadata, alt texts, aria-labels and JSON-LD, plus the web manifest. It fails on
> an unfilled `[SLOT]` (the `"[MISSING: …]"` content token and the starter's
> `[BRACKET]` slots alike), filler text, an author note (`TODO`), an unrendered
> template expression or a dummy name. The CI grep for `[MISSING:` is the fast
> source-side half; this is the half that reads what a page serves. The starter's
> privacy page, imprint and manifest are listed in its `UNFILLED_UNTIL_LAUNCH`, so
> they are reported on every run instead of failing. That list empties itself (a
> filled page fails until its entry is deleted) and must be empty at launch. A
> `"[MISSING: …]"` on a page only warns on your own machine, so a draft branch can be
> pushed, and fails in CI. Not read, so still a human check: the 404 page, `llms.txt`
> (it has slots of its own), and the starter's example values (the name `Example`,
> `hello@example.com`).

## Section anchors

`scripts/anchor-ids.mjs` runs as the second half of `npm run build`: it walks the
built `dist/` HTML and gives every `h2`/`h3` a short slug `id`, so any section is
linkable from an external site with no per-page work. The id is the heading's first
**two meaningful words** (filler words like "the/with/how" dropped), e.g. `<h2>The
outcomes we deliver</h2>` → `id="outcomes-deliver"`; a third word is appended only
to break a clash with another heading on the page, before falling back to a numeric
suffix. A hyphenated name or domain (e.g. `acme-corp`) counts as one word, keeping its
own hyphen. Change the word count via `ID_WORDS` at the top of the script. The ids are written into the **static** HTML (no runtime JS), so crawlers,
AI answer engines and the browser's on-load scroll all see them. `h1` is skipped —
one per page, so its fragment would just duplicate the page URL. `anchors.spec.ts`
proves every internal `#fragment` you write resolves to a real id.

Two kinds of heading are **left alone** (never auto-id'd), so a generated id can
never collide with or fragment a hand-curated one:
- a heading that already has an explicit `id` (`<h2 id="pricing">`) — curated wins;
- a heading inside a `<section>`/`<article>` that has an `id` — that wrapper is
  already the section's anchor (e.g. `<section id="pricing"><h2>…`).

Caveat for links you publish elsewhere: an auto-slug tracks the heading text, so
rewording the heading changes its id and breaks the old link. For any anchor you
hand out externally, **set an explicit `id`** (on the heading or its section) — it
wins over the auto-slug and never drifts.

Deploy: Cloudflare Pages, build `npm run build`, output `dist/`. In the Pages
project settings set the **production branch to `production`** (must equal
`PROD_BRANCH` in `src/config.ts`). On a site connected to GitHub in Cloudflare, `main`
stays the preview. A site deployed by command has no automatic preview: a deploy to any
branch other than the production branch is a preview, and `PUBLISHING.md`, "Deploy by
command", has the steps for the live site. Every preview `*.pages.dev` host is noindexed
by the function. Once the live domain serves the
site, set the Production variable `CANONICAL_URL` (e.g. `https://example.com`) and
redeploy: the project alias `<project>.pages.dev` then 301s to the live domain, so
people following an AI answer that cites the alias land on the real domain. Until then the alias is noindexed
like a preview. Steps, and how a site built before this change picks it up (new
middleware + redeploy): `new-website/references/CLOUDFLARE_FIRST_DEPLOY.md`, "After
go-live". AI assistant deploying or announcing a
deploy: read `PUBLISHING.md` § "For AI assistants — deploy-time guardrails"
first (preview-vs-live announcements + the cached-404 rule) — every time, not
just the first.
