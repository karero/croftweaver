# Astro starter overlay (the `new-website` kit)

A complete, opinionated overlay you drop on top of a fresh Astro project: the SEO +
theme spine, the test suite, security headers, the preview-noindex function, and CI.
Copy-and-go for an Astro → GitHub → Cloudflare Pages site. The `new-website` skill
drives assembly; this README is the manual reference.

## What's here

```
package.json  tsconfig.json  astro.config.mjs  playwright.config.ts
.nvmrc                        # Node 24 — the starter needs >=22.23.4 (Cloudflare Pages reads it)
.gitattributes                # LF line endings for *.sh and scripts/hooks/*, so the pre-push hook runs on Windows
src/config.ts                 # single source of truth (URL, name, analytics, EEAT)
src/layouts/Base.astro        # title/OG/Twitter/canonical/JSON-LD/no-FOUC theme spine
src/styles/global.css         # light/dark theme tokens (mirror BRAND.md)
src/styles/tables.css         # the table style (website-design-system, "Tables")
src/pages/index.astro         # minimal home so the suite is green from commit 1
src/pages/privacy.astro       # GDPR privacy draft (fill [BRACKET] slots before launch)
public/{robots.txt,llms.txt,_headers,manifest.webmanifest}
functions/_middleware.ts      # noindex *.pages.dev previews; 301 <project>.pages.dev once CANONICAL_URL is set; page views in analytics server mode
functions/go/email.ts         # analytics server mode: counts the email tap, then opens the mail program
.github/workflows/ci.yml      # astro check + the suite on push/PR
.github/dependabot.yml        # monthly grouped npm + Actions version updates (delete it if nobody will merge them)
scripts/check_external_links.sh  # warn-only outgoing-link liveness sweep (network; not in CI)
scripts/check_internal_links.sh  # warn-only internal-link audit: orphan / thin / deep pages (offline; not in CI)
scripts/generate_og_cards.py     # branded 1200×630 OG share cards, one per page (npm run og)
scripts/run_og.mjs               # cross-platform launcher for the generator (forwards --check)
scripts/anchor-ids.mjs           # post-build: stable slug id on every h2/h3 (runs in `npm run build`)
scripts/build-marker.mjs         # post-build: the commit SHA into dist/build.txt, so `npm run ship` can check the live site has it; in test builds also dist/test-build-id.txt
scripts/set_pdf_title.py         # sets a hosted PDF's title (Info dict and XMP), the fix when the SEO test flags one (needs pypdf)
scripts/ship.sh                  # `npm run ship`: two-stage sites only, promotes `main` (preview) to `production` (live)
scripts/hooks/pre-push           # blocks a push when the site's checks fail
scripts/wire-hooks.mjs           # run by "prepare" on every `npm install`, which fails without it: wires the pre-push hook
scripts/verify.mjs               # `npm run verify`: CI's install, check, build and test in one command; the pre-push hook runs it
tests/_helpers.ts  tests/{a11y,seo,navigation,anchors,orphans,images,tone,positioning,placeholders,privacy-host,email,links,llms-coverage,middleware,analytics-server,tables,served-build}.spec.ts
tests/check_ship_push.sh      # offline gate: ship.sh's publish-failure diagnosis, and its ship.fromGitHub mode on throwaway local repos (pre-push hook + CI)
tests/check_analytics_gate.sh # counter self-test, CSP check, four builds: off in all four with USE_ANALYTICS = false (as shipped), or on only when CF_PAGES_BRANCH is PROD_BRANCH; in server mode no script and email links to /go/email on the live build only (the suite's own CI)
```
Sibling files in the parent `templates/`: `.gitignore`, `SETUP.md`,
`claude/settings.json` (permission allowlist), `content-guide.md`, `brand.md`.

## Bootstrap a new project

1. **Git first** (see SETUP.md): `mkdir <site> && cd <site> && git init`, copy the
   `templates/.gitignore`, commit.
2. `npm create astro@latest .` → Empty, TypeScript **Strict**. Requires **Node ≥22.23.4**
   (this starter's floor, never below Astro's own); keep Node current: SETUP.md lists the fixed version of
   each line. The committed `.nvmrc` pins 24 for local + Cloudflare Pages builds.
3. Copy this overlay over the scaffold (the files above, `package.json` included: it carries `engines`,
   which makes npm warn when Node is older than the fixed version of its line) + `tests/`, then:
   ```bash
   npm install
   npx playwright install chromium
   ```
   **Commit the
   `package-lock.json`** — CI uses `npm ci`, which fails without it.
   On **npm ≥11.16**, `install` prints "packages have install scripts not yet covered"
   for scripts it hasn't been told to trust — per npm's own docs this is currently
   advisory only (the scripts still run; a future npm release will start blocking them).
   This `package.json` already approves the one package that still has an install script,
   `fsevents` (macOS only), so there is nothing to approve. (Until 7.3.8, Astro installed
   `esbuild`, which needed approving; since 0.35, sharp needs nothing.) If a later
   update brings a package with an install script, the warning names it: approve it with
   `npm approve-scripts <name>`.
4. Set the real domain in `astro.config.mjs` (`site:`) and `src/config.ts`
   (`SITE.url`, name, theme color). Analytics ships off (`USE_ANALYTICS = false`). For
   Plausible, switch it on as the analytics comment in that file says: `USE_ANALYTICS = true`,
   `scriptHost` and the per-site `scriptId` from the site's installation page in Plausible
   (`<scriptHost>/<your domain>/installation`), the
   same host in `script-src` and `connect-src` of `public/_headers`, and a `PROD_BRANCH`
   that matches the branch Cloudflare Pages will call "Production", or analytics never
   loads. No analytics: leave it off and delete the privacy page's analytics paragraphs.
   Add `public/` icons; edit the placeholder `manifest.webmanifest`. Set the BRAND
   block in `scripts/generate_og_cards.py` and run `npm run og` to regenerate the
   1200×630 share cards (`public/images/og/`; the starter ships a default).
   Fill the `[BRACKET]` slots in `src/pages/privacy.astro`
   (controller, date, analytics wording — see the comment block in that file).
   In Plausible's installer, untick the optional measurements (outbound links,
   file downloads, form submissions), or keep the page's sentence for each one you leave ticked.
   For a ticked one, click such a link on the live site once and look for its address in the
   instance's report: the sentence says the address is sent and stored.
   Before launch, add the enquiry goal on the site's goals page in Plausible,
   `<scriptHost>/<your domain>/settings/goals` (Settings > Goals; open that address directly,
   owners find the page hard to reach from the dashboard): Add goal, type
   "Custom event", name `Email Tap` (exactly); the form asks for an Event name and a Display name (seen on a self-hosted instance). A click on an email address
   or the contact form's button sends that event; Plausible's documentation says it shows
   only once the goal exists, and earlier ones are not counted. Once a test tap has
   reached Plausible, the goals page offers `Email Tap` to add in one click (seen on a
   self-hosted instance). To see a test tap, choose
   Today or Realtime: Plausible's "Last 7, 28, 30 and 91 days" views end yesterday
   (checked on self-hosted version 3.2.1; the cloud version may differ). On a site just added
   to Plausible, tap again a few minutes later if the
   first tap does not show.
   **Server mode instead** (`USE_ANALYTICS = true` and `ANALYTICS.mode: 'server'` in
   `src/config.ts`): no Plausible script in the browser; the Pages Function sends each page
   view and email tap. Leave `scriptId` as it is, and leave the host out of
   `public/_headers` (no script loads). In Cloudflare, the project's Settings > Variables and Secrets >
   Production, add `PLAUSIBLE_HOST` (the instance, e.g. `https://analytics.example.com`, or
   `https://plausible.io`) and `PLAUSIBLE_DOMAIN` (the site's domain exactly as added in
   Plausible; if `PLAUSIBLE_DOMAIN` and the site's name in Plausible differ by one letter, Plausible answers 202 and silently drops every
   event: no error, nothing counted; seen on self-hosted Community Edition 3.2.1), then redeploy; set them only in server mode, or every page view counts
   twice. Add the site and the `Email Tap` goal in Plausible by hand as above; the
   installer's optional measurements do not apply (no script runs). In
   `src/pages/privacy.astro`, keep the server-mode slots. An existing site also takes from
   this starter what `whats-new` does not report, because the site owns it: the `mode`
   line in `src/config.ts`, `src/layouts/Base.astro`, `src/components/EmailLink.astro`, the
   privacy slots and `Disallow: /go/` in `public/robots.txt`; then runs
   `bash tests/check_analytics_gate.sh`. Without the mode line and `Base.astro`, its old
   layout keeps loading the script and every page view counts twice; without
   `EmailLink.astro`, email taps are not counted. Lost compared with the script:
   scroll depth, engaged time, the optional measurements, excluding your own visits (the
   `plausible_ignore` flag), and the contact form's button (not counted); also pages a browser prefetched or prerendered, and visitors whose
   browser sends no Fetch Metadata headers (Safari before 16.4, some in-app browsers),
   who get the "name [at] domain" hint instead of their mail program when they tap the
   email link. Test on the live domain, not a `pages.dev` address: the Function skips every `*.pages.dev` host, previews and the project's own `<project>.pages.dev` address alike, whatever the site is called in Plausible; a subdomain you control (for example `e2e.example.com`) on a throwaway project is enough, added in Plausible as its own site and set as that deployment's `PLAUSIBLE_DOMAIN`.
   A server-mode build has no Plausible script in its page and its email links go to `/go/email`.
   **If nothing arrives, check in this order:**
   - The site's name in Plausible must match `PLAUSIBLE_DOMAIN` exactly: a one-letter difference drops every event.
   - You edited the variables since the last deployment: redeploy. Dashboard edits take effect only on deployments made after the save (seen on a live site; Cloudflare's bindings page says to redeploy for a binding to take effect).
   - The page has a Plausible script or a plain `mailto:` link instead of the `/go/email` link: the build is not the server-mode build; check `USE_ANALYTICS`, `ANALYTICS.mode` and the branch the deployment was built from.
   - A click on the email link shows the "name [at] domain" page instead of opening the mail program: the request was not a same-origin click in a browser (a crawler, a prefetch, a link from another site, a browser without Fetch Metadata), or the deployed build is older than the starter you mean to test. Redeploy from the current starter and reload the page without its cache.
   - The variable rows in Cloudflare's dashboard cannot be edited: a Wrangler config file in the project defines them, and Cloudflare's documentation says the dashboard then shows those fields but does not let you change them. Change the file and deploy again with `CF_PAGES_BRANCH=<PROD_BRANCH> npm run build && npx wrangler pages deploy dist --project-name <project> --branch <PROD_BRANCH>` (the build needs the branch name, or the page is written without the `/go/email` links), or delete the file and deploy again the same way; Cloudflare says the values of the last deployment then stay in effect and become editable in the dashboard, but check that both `PLAUSIBLE_HOST` and `PLAUSIBLE_DOMAIN` are still listed, and enter them again if not.
   Each target you fill here (privacy page, manifest) then comes out of
   `UNFILLED_UNTIL_LAUNCH` in `tests/placeholders.spec.ts`; the test is red until it does.
5. `npm run verify` (`npm run check`, then the tests, which build once) — the overlay passes strict TS +
   a11y/seo/navigation/anchors/orphans/images/tone/positioning/placeholders/email/links/llms-coverage/middleware/analytics-server out of the box. Then build pages
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

Shared computers: where several people or AI assistants work in one checkout of a
two-stage site, `npm run ship` stops on any unsaved file and on any branch but `main`,
though none of that would be published. `git config ship.fromGitHub true` in that clone
makes it publish GitHub's `main` from a throwaway git worktree instead: nothing in the
folder is built or published, and its unsaved files are only listed. The setting is read
from the clone's own config, never the global one, so a fresh clone keeps the folder check.
`PUBLISHING.md`, "On a shared computer", has the details.
