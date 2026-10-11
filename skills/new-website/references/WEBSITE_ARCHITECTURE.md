# House Standard: Architecture for Content Websites (up to ~50 pages)

Reusable decision framework for building a new website on **GitHub + Cloudflare**.
Drop this file into any new site repo. Grounded in a portfolio of real builds
spanning the full static-to-SSR spectrum.

---

## TL;DR

> **For a content site up to ~50 pages: Astro (static output) → GitHub → Cloudflare Pages.
> Clone the static-Astro reference architecture. Stay static until a *specific feature* forces you up
> a tier — and even then, add only that feature (Pages Functions / server islands), don't
> change frameworks.**

GitHub + Cloudflare is the right backbone — nothing is meaningfully *better* for this class
of site; the credible alternatives (Netlify, Vercel) are *similar* with different trade-offs.
Astro is the right framework. The real decision isn't *which host* or *which framework* —
it's **which rendering tier** your features demand. Going higher than you need is the mistake.

**What the portfolio proves:** the *best* outcome (the static Astro site — Lighthouse 99/100/100/100,
0 a11y violations, 120 tests) is the *simplest* stack that met the requirement. The heaviest
build (an SSR site — Next.js 16, 2.4 GB build, OpenNext shim) is ~80% static content dragging
a full SSR framework for one live page. That asymmetry is the whole thesis.

| Project | Stack | Hosting | Verdict |
|---|---|---|---|
| Early static site | Hand-written HTML | CF Pages | Works, but duplicated `<head>`/nav/footer, manual sitemap. Doesn't scale to 50. |
| Static + test gate | Hand-written HTML + Node tests | CF Pages | Same, stronger test gate. |
| **Static Astro site** | **Astro (static)** | CF Pages (2-branch) | ⭐ Gold standard. ~23 pages, Lighthouse 99/100/100/100. |
| Full-stack app | SvelteKit + D1 | CF Pages + Workers | Full-stack (DB) — justified by dynamic data. |
| Over-built SSR site | Next.js + React (SSR) | CF Workers (OpenNext) + bare-metal | Cautionary tale: ~40/41 pages static, only the stats route + API routes need SSR. |

---

## Part 1 — Is GitHub + Cloudflare the right backbone? (Yes)

The flow already in use is the modern best practice:
`push to GitHub → Cloudflare auto-builds → global edge CDN → live in ~60s`.

| Capability | Cloudflare Pages/Workers | Netlify | Vercel |
|---|---|---|---|
| Static + global CDN | ✅ free, **unlimited static requests** | ✅ (metered) | ✅ (metered) |
| Edge functions | ✅ Workers/Pages Functions | ✅ | ✅ |
| Free-tier generosity | ★ best | good | good |
| Next.js SSR ergonomics | ⚠️ needs OpenNext adapter | ✅ | ★ native |
| DB/KV/storage at edge | ✅ D1, KV, R2, Durable Objects | partial | partial |
| Lock-in | low | low | medium (Next features) |

**Verdict:** For static + light-dynamic, **Cloudflare is the best of the three**. The only
case for switching is heavy Next.js SSR → Vercel (no OpenNext friction). The over-built SSR site is the
living proof of that tax (`@opennextjs/cloudflare`, `.open-next/worker.js`, dual output modes).
Astro avoids the tax entirely (first-class CF adapter). **Stay on Cloudflare for content sites.**

**Pages or Workers?** Cloudflare's Pages docs now open with "Start new projects with Workers";
[Pages](https://developers.cloudflare.com/pages/) is still listed as available on all plans,
and the docs name no end date (read 2026-10-07). The kit stays on Pages for now. It is written
for Pages: the middleware's `*.pages.dev` host rules, the `CF_PAGES_*` build variables that
gate analytics and stamp `build.txt`, and the deploy and preview steps in these docs. And when
the free plan's daily Functions requests run out, a Pages project can still serve the static
site ("Fail open", `CLOUDFLARE_FIRST_DEPLOY.md`), whereas a Worker set to run before its static
files answers 429 instead ([Workers static
assets](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/)).
Moving the kit to Workers is one decision for the whole kit, not one to make per site.

---

## Part 2 — Why Astro, and current best practices (2026)

### Advantages
- **Zero JS by default.** Opt into JavaScript per component. Biggest lever for Core Web Vitals/SEO.
- **Islands architecture.** Interactive bits hydrate in isolation; the rest stays static HTML.
- **Components without a framework runtime.** Layouts/partials/props/slots kill the duplicated
  `<head>`/nav/footer problem — nothing shipped to the browser.
- **Content Collections / Content Layer (Astro 5+).** Type-safe Markdown/MDX or external data
  (CMS/API/DB) as a schema-validated store. How a 50-page or blog site stays maintainable.
- **Build-time SEO.** `@astrojs/sitemap` auto-generates the sitemap, `astro:assets` optimizes
  images, canonical/OG/JSON-LD live once in `Base.astro`.
- **First-class Cloudflare adapter.** Static by default; flip to `@astrojs/cloudflare` only when
  you need SSR/server islands — same repo, same host.

### Current best practices (Astro 7, 2026)
1. **Static-first.** Assume plain HTML. Only add a `client:*` directive if the user benefits.
   Avoid the 3 classic mistakes: mapping large arrays into client islands, wrapping a whole
   layout in a framework component, defaulting to `client:load`. Prefer `client:visible` / `client:idle`.
2. **Content Layer for any repeated content type** (blog, events, team, case studies) with a Zod schema.
3. **Server Islands (`server:defer`) for the rare dynamic fragment.** Render the page static +
   cacheable, defer just the live bit (price, next event) with a static fallback. Pass minimal,
   serializable props. *This is what would have kept that SSR site ~95% static instead of full SSR.*
4. **One `Base.astro` layout owns the SEO spine** — canonical, OG/Twitter, JSON-LD, analytics gating.
5. **Centralize site facts in one `config.ts`** — address, nav, schema metadata, analytics toggle.
6. **Inline CSS + self-hosted woff2 fonts** for render-blocking-free first paint.

---

## Part 3 — The Decision Tree (which tier, and the limits of each)

Walk down the tiers; stop at the first that covers your features. **Going higher than you
need is the actual mistake.**

### Tier 1 — Static Astro on Cloudflare Pages  ← default, ~90% of sites
**Use for:** marketing, info, blog/news, events, docs, portfolio. Content that changes when
*you* change it, not per-request.
**Dynamic via:** an email link / a contact form that opens the visitor's own mail program (the
`website-contact-form` skill, our suggestion: no server, no account, no third party) / a form
service (Formspree/Web3Forms; a third party then handles the messages and is named on the
privacy page) / client-side `fetch()` for the odd live number.
**This is the static-Astro tier.** 50 pages is trivial — Astro builds ~23 pages in ~0.5s; static scales to thousands.

**Cloudflare Pages limits (where it breaks):** 20,000 files/deploy, 25 MiB/file, 500 builds/mo
(free). → You will *never* hit these at 50 pages. Requests for static files are free and
unlimited, but only while no Function runs: the kit's `functions/_middleware.ts` runs on
every request, so a kit site's requests count against Tier 2's Functions limit below (100K a
day on the free plan; `CLOUDFLARE_FIRST_DEPLOY.md` says what to set for when it runs out).

### Tier 2 — Static Astro + Cloudflare Pages Functions / Server Islands  ← light dynamic
**Use for:** a few server endpoints or per-request fragments — a form that must send through a
server (no skill builds one; a contact form is Tier 1 above),
site search, live-stats widget, gated content, webhook receiver, proxy to hide an API key, light A/B.
**How:** keep the site static; add `functions/*.ts` (Pages Functions) or Astro **server islands**
for just the dynamic fragment. Add **Workers KV** for tiny state (flags, counters, cached responses).

**Cloudflare Workers/Functions limits (where it breaks):**
- **CPU time: 30s max** (configurable) — fine for an API call/DB query, not video/heavy compute.
- **Memory: 128 MB** per isolate — not for large datasets/models in memory.
- **Bundle: ~3 MB free / 10 MB paid** compressed — big native deps won't fit.
- **Subrequests: 50 free / 1000 paid** per request.
- **No persistent in-process state**, no long-running processes; **WebSockets only via Durable Objects**.
- Free: **100K requests/day**; Paid ($5/mo): **10M req/mo + 30M CPU-ms/mo** included.

### Tier 3 — SSR + Database on Cloudflare Workers (Astro SSR or SvelteKit + D1/KV/R2)
**Use for:** real app behavior — accounts/auth, a database, e-commerce/checkout, dashboards,
user-generated content, per-request SSR. **This is the full-stack tier** (SvelteKit + D1).

**D1 (SQLite) + Workers limits (where it breaks):**
- **D1: 5 GB free / ~10 GB per DB paid.** SQLite: **single-region primary for writes** (reads
  replicate). Great for read-heavy moderate apps; not for write-heavy/multi-region-write/very large relational.
- **6 simultaneous DB connections** per Worker invocation.
- Same Workers CPU/memory ceilings per rendered page.
- External Postgres/MySQL → use **Hyperdrive** to pool connections from Workers.

### 🚪 When Cloudflare stops being the right answer (leave the platform)
Move to a VPS/container, Fly.io/Render, or managed Postgres + Vercel when you hit:
- **Long-running/heavy compute:** jobs >30s CPU, video transcoding, large ML inference, big batch.
  *(the over-built SSR site runs a parallel bare-metal Node origin partly for this.)*
- **A real relational DB with write scale / multi-region writes / Postgres extensions / >10 GB.**
- **Full Node/PHP/Ruby runtime or native binaries** not supported by `workerd`.
- **Per-request memory > 128 MB** or large in-memory caches.
- **Persistent connections at scale** beyond what Durable Objects comfortably handle.
- **Heavy Next.js SSR** where OpenNext friction isn't worth it → Vercel.

**Rule of thumb:** *Static → Cloudflare forever. Light dynamic → Functions/Islands. Small app +
DB → Workers + D1. Heavy compute / big SQL / full server → a VPS/dedicated box or managed platform.*

---

## Part 4 — Content editing: Claude Code as the interface (and when Keystatic)

**Primary interface = Claude Code editing repo files directly.** Strong modern choice:
- **No CMS needed for dev/Claude-driven editing.** Content lives in the repo as `.astro` +
  Markdown/MDX content collections. Claude edits files → commits → push → Cloudflare deploys.
  Git history *is* the audit log.
- **Use Content Collections** so even Claude-edited content is schema-validated front-matter +
  body, not hand-built `<head>` tags.

**Add Keystatic / Decap (git-based CMS) only when:**
- A **non-technical client** must self-edit without git/Claude Code.
- Frequent publishing (e.g. weekly blog) where a visual editor + preview earns its keep.
- **Keystatic** is the pick: git-based, commits to the same repo, no DB, no extra hosting,
  works perfectly with Astro + Cloudflare. (Decap is the alternative; hosted Sanity/Contentful
  only if structured content is reused across many surfaces.)
- **Default: skip the CMS.** Add it only when a human-who-isn't-you needs the keys.
- **When chosen, run the `keystatic-setup` skill** — it wires local mode (edit in the dev
  server, commit/push) and documents the GitHub cloud-mode upgrade for browser editing.

---

## Part 5 — The Starter Recipe (the static-Astro reference)

- **`astro.config.mjs`**: `site` URL, `trailingSlash: 'never'` + `build.format: 'file'`
  (convention: clean URLs with **no trailing slash** — `/about`, not `/about/`),
  `build.inlineStylesheets: 'always'`, `@astrojs/sitemap`.
- **`src/config.ts`**: single source of truth — facts, nav, schema metadata, analytics gating
  (`process.env.CF_PAGES_BRANCH === 'production'`).
- **`src/layouts/Base.astro`**: canonical, OG/Twitter, JSON-LD, analytics script.
- **`src/components/`**: `Header`, `Footer`, `PageHero`, `Subnav`, `EmailLink` (build-time obfuscated).
- **`src/content/`** (if blog/events/team): Content Collections + Zod schema.
- **`public/_headers`**: CSP, HSTS, `X-Content-Type-Options`, cache (`/_astro/* immutable`, `/images/* 30d`).
- **`public/_redirects`**: legacy → clean-URL 301s.
- **`functions/_middleware.ts`**: `noindex` the `*.pages.dev` preview deploys; after go-live,
  301 the project alias `<project>.pages.dev` to the live domain (Production variable
  `CANONICAL_URL`, see `CLOUDFLARE_FIRST_DEPLOY.md`).
- **2-branch deploy:** `main` → Preview (noindex), `production` → live.
- **Analytics (optional):** Plausible — cookieless, GDPR-clean — needs a paid license (from
  €9/mo, https://plausible.io/#pricing). For many small sites, **Google Search Console** alone
  (free) covers search & referral traffic. Add it only if you'll act on the numbers; gate the
  script to production.
- **Test gate (Playwright + axe):** per-page a11y light *and* dark, route 200s, button contrast,
  tone-of-voice spec. Run in GitHub Actions on every push.

---

## Part 6 — Alternatives to Astro (and when they'd win)

| Alternative | Wins when | For a 50-page site? |
|---|---|---|
| Hand-written HTML | <5 pages, no repetition, zero tooling | ❌ doesn't scale |
| Eleventy (11ty) | pure static + templating, no client framework | ✅ viable, but Astro adds islands + content layer + images for ~same effort |
| Hugo | thousands of pages, build speed paramount | ⚠️ overkill at 50, steeper templating |
| SvelteKit | app-like, needs DB/auth/SSR | only at Tier 3 |
| Next.js | heavy SSR/ISR, big React app, hosting on Vercel | ❌ for content (SSR bloat) |

**Conclusion:** For content up to ~50 pages, **Astro is the sweet spot** — more capable than
11ty/Hugo where it matters, without the SSR-framework weight of Next/SvelteKit.

---

## Part 7 — Standard "New Site" Kickoff Questions

1. **How many pages, and what content types?** (flat pages vs. repeated collections → Content Collections.)
2. **Any dynamic/backend features?** → pick the tier:
   - None, or a contact form that opens the visitor's mail program (`website-contact-form`) →
     **Tier 1** static.
   - A form that must send through a server / search / hide-an-API-key / one live widget →
     **Tier 2** (Functions / server islands).
   - Accounts / DB / checkout / per-request SSR → **Tier 3** (Workers + D1) — or off-platform if it
     trips a Part-3 escape hatch.
3. **Who edits content after launch?** You/Claude Code (default, no CMS) vs. non-technical client
   (add **Keystatic** via the **`keystatic-setup`** skill) vs. mix.
4. **Languages?** One → skip i18n entirely. Multiple from day one → run the
   **`astro-i18n-setup`** skill (Astro i18n routing, self-referencing hreflang + `x-default`,
   sitemap alternates, per-locale content + test harness). (A half-finished i18n retrofit is a
   real, avoidable tax.)
5. **Analytics? (optional)** Plausible (cookieless, paid license from €9/mo —
   https://plausible.io/#pricing) or, for many small sites, just Google Search Console (free).
6. **Domain + DNS** on Cloudflare; **2-branch** Pages deploy (preview noindex / production live).

---

## Verification (does a new site meet the standard?)

1. `npm run build` → static `dist/`; git push (or `npx wrangler pages deploy`) serves a `*.pages.dev` preview.
2. **Lighthouse** (mobile, prod build): Perf ≥95, A11y 100, Best Practices 100, SEO 100.
3. **Playwright + axe** green: 0 a11y violations all routes light *and* dark; all routes 200;
   button contrast ≥4.5:1; tone-of-voice spec passes.
4. `@astrojs/sitemap` emits a clean sitemap (no `.html`); `robots.txt` allows production; previews `noindex`.
5. CSP/HSTS headers (`public/_headers`); legacy URLs 301 (`public/_redirects`).
6. Tier 2/3: endpoint/DB works on the preview deploy, within the Part-3 CPU/memory/connection limits.

---

*Limits cited from Cloudflare Workers/D1 docs and Astro 5 docs (June 2026); verify exact
free/paid thresholds at build time as Cloudflare adjusts them.*
*Sources: [Workers limits](https://developers.cloudflare.com/workers/platform/limits/),
[Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/),
[D1 limits](https://developers.cloudflare.com/d1/platform/limits/),
[Astro 5](https://astro.build/blog/astro-5/),
[Server islands](https://docs.astro.build/en/guides/server-islands/).*
