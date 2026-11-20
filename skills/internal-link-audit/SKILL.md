---
name: internal-link-audit
description: >
  Internal-linking tool for an Astro site built with the new-website kit.
  Builds the site's inbound-link graph from dist/ and reports which pages are
  ORPHANED (in the sitemap but no internal link points at them), THIN (a
  single inbound link, no contextual in-body link), or DEEP (more than ~3
  clicks from home), then suggests WHERE to add the missing links using
  `site-architecture`'s internal-linking strategy. The judgment-side
  complement to the offline `tests/orphans.spec.ts` gate. Run before a
  release, after adding pages, to check one new page, or when GSC reports
  orphaned/low-coverage pages. Trigger phrases: "internal link audit", "orphaned pages", "are any
  pages orphaned", "internal linking", "which pages link to nothing", "fix
  orphan pages", "improve internal links", "cross-link the comparison pages".
---

# Internal Link Audit

Pages rot in the OTHER direction too: not the links that go dead, but the pages that
nothing links TO. A page can be in the sitemap, pass every QA spec, and still be
**orphaned** — reachable by no internal link, so crawlers find it late (or never) and
no human browsing the site ever lands on it. The classic cause: a footer/nav link
group that lists only ONE of a sibling set (e.g. one `acme-vs-<competitor>` comparison),
leaving the rest linked from nowhere.

This is the internal-link twin of `outgoing-link-audit`:

| | offline CI gate | active sweep (this) |
|---|---|---|
| **outgoing** (dead/rebranded) | `tests/links.spec.ts` | `outgoing-link-audit` |
| **internal** (orphan/thin) | `tests/orphans.spec.ts` | **`internal-link-audit`** |

Read-only with respect to the site: it diagnoses and suggests. You apply fixes only
after the user confirms.

## The strategy it enforces

This skill does not invent its own linking rules — it **measures the built site against
the strategy in `site-architecture`** (its "Internal Linking Strategy" section, plus its
"3-Click Rule"; read them before suggesting fixes). The strategies, and how this audit
checks each:

| Strategy (from `site-architecture`) | How the audit enforces it |
|---|---|
| **No orphan pages** — every page has ≥1 inbound internal link | ORPHANS list (0 inbound) — the hard gate `tests/orphans.spec.ts` also fails on this |
| **Hub-and-spoke / topic clusters** — hub links all spokes, spokes link the hub and each other | sibling sets that don't cross-link surface as orphans/thin; suggest the hub + cross-links |
| **Important pages get the most inbound links** — home, pricing, key features | the inbound COUNT ranking shows whether your money pages actually lead |
| **Descriptive, keyword-bearing anchor text** — not "click here" | judgment: read the anchor text of the links you add/keep (see `website-seo-geo`) |
| **3-Click Rule** — important pages within ~3 clicks of home | DEEP list (>3 clicks from home, computed by BFS) |
| **Contextual links beat boilerplate** — in-body editorial links > nav/footer | THIN list flags pages held up only by the global nav/footer |

(Linking to the clean canonical URL — no `.html`, no redirect/trailing-slash hop — is link
hygiene the `navigation` spec already guards; apply it to every link you add, step 4.)

## When to run

Before a release / launch, after adding any batch of pages (the moment a set of
siblings gets created but only some get linked), or when Google Search Console flags
"Crawled - currently not indexed" / "Discovered - not indexed" / orphaned pages.

Unlike `outgoing-link-audit`, this makes **no network calls** — it reads the local
build — so it's cheap to run any time.

## Shortcut: the shared script does the graph

`scripts/check_internal_links.sh` builds (if needed), extracts every internal anchor
from `dist/`, and prints the inbound-link graph grouped as **ORPHANS / THIN / OK**.
Run it first:

```bash
bash scripts/check_internal_links.sh
```

Then apply **judgment** to its output (the part a script can't do — *which* related
page should link to each orphan, and with what anchor text) and hand off the fixes.

## Procedure

### 1. Build the inbound-link graph

Audit the built `dist/` so it matches what Cloudflare serves. For every page, the
script counts the **distinct other pages** that link to it (self-links and the home
root excluded; query/fragment/`www`/trailing-slash variants collapse to one target,
matching the test) and its **click depth** from home (BFS). Classify each page:

- **ORPHAN** — 0 inbound internal links. The high-value finding: a page no one can
  reach by browsing. This is exactly what `tests/orphans.spec.ts` fails on.
- **THIN** — exactly 1 inbound link, and that link is the global nav/footer (no
  contextual in-body link). Not broken, but weakly connected: little internal
  PageRank flows to it (the "contextual links beat boilerplate" strategy).
- **DEEP** — more than ~3 clicks from home. Crawlers spend less budget on deep pages
  and pass them less equity (the "shallow crawl depth" strategy). Orthogonal to inbound
  count — a page can be both THIN and DEEP.
- **OK** — ≥2 inbound links and within 3 clicks.

Then sanity-check the inbound RANKING against intent: your most important pages
(home, pricing, primary feature/conversion pages) should be among the most-linked. A
key conversion page sitting at 1 inbound link is a strategy miss even though it isn't
technically orphaned.

### 2. Suggest WHERE to add the links (the judgment step)

For each orphan/thin page, the fix is not "link it from anywhere" — it's to add a link
where it's *topically* earned, so the link helps a real reader:

- **Sibling sets cross-link.** If `/acme-vs-crm`, `/acme-vs-chat`, `/acme-vs-calendar`, …
  exist, every comparison page should link to its siblings (a "Compare with other
  tools" block), and a hub/overview page should list them all. A footer "Product"
  group that names only `acme-vs-crm` is the bug — add the siblings to that
  group in `src/config.ts`, or build the hub page.
- **Contextual in-body links beat nav links.** A sentence on a related page that
  links the orphan in context ("see how we compare to a CRM") is worth more than a
  footer entry, to both readers and crawlers.
- **Pick anchor text that carries the target's keyword**, not "click here"/"read more"
  — it's a ranking signal for the target page (see `website-seo-geo`). Vary it
  naturally across links; don't paste the exact-match phrase every time.
- **Pull DEEP pages shallower.** Link a >3-click page from a hub or section page that
  itself sits near home, so it lands within ~3 clicks.
- **Feed the important pages.** If a money/conversion page is under-linked relative to
  its importance, add links to it from high-traffic related pages — important pages
  should have the most inbound links, not the fewest.
- **Use the free links.** Breadcrumbs and a "related pages" block are inbound links on
  every page at no editorial cost — a structural fix for whole clusters at once.
- **Always link the canonical URL** — clean path, no `.html`, no trailing slash, no
  redirect hop (so equity isn't lost to a 301 and `navigation.spec` stays green).

> Judgment, not just counts: a deliberately-unlinked page (a paid-campaign landing
> page reached only from an ad, a print-QR page) is *correctly* orphaned — it should
> go in `orphan-exempt.txt` with a reason, not get a forced
> link. Use the model to tell a real orphan from an intentional one.

### 3. Report

Group by severity. Lead with ORPHANS (the actionable ones), then THIN, then DEEP, then
OK as a count. For each orphan/thin/deep page, name the specific page(s) that should link to it and
the suggested anchor text.

### 4. Hand off the fixes

For each finding, after the user confirms:

1. Add the link in the source page (`src/pages/*.astro`, a content-collection entry,
   or a nav/footer group in `src/config.ts`). Use keyword-bearing anchor text and the
   clean URL (no `.html`, no trailing slash).
2. For a deliberately-unlinked page, add its address to `orphan-exempt.txt`, on its own
   line, with the reason after a `#` instead.
3. Re-run `npm run build && npm test` to confirm green (`orphans.spec.ts` must pass),
   then commit.

## A new page

`website-new-page` step 8 hands a freshly built page to this skill. A new page must meet three
points, which `scripts/check_page_links.py` counts from `dist/` for that one page, from the
site's pages as built (it needs nothing else from the site):

- **L1** At least 2 other pages link to it, and at least 1 of them from its **body**: inside that
  page's `<main>`, and not inside a `<header>`, `<nav>`, `<footer>` or `<aside>`.
- **L2** If the page has a hub: the hub links to it from the hub's body, and the page links back
  to the hub with an `<a>` inside its own `<main>` (a breadcrumb `<nav>` inside `<main>` counts;
  JSON-LD does not). A breadcrumb outside `<main>` is a miss the owner may accept.
- **L3** It is at most 3 clicks from the home page.

Run it after a fresh `npm run build`, with the page's path, the site's address from
`astro.config.mjs`, and `--hub` with the hub's path, or `--no-hub` where the owner's brief says
the page has none:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/check_page_links.py" dist /<page-path> \
  --site https://<host> (--hub /<hub-path> | --no-hub)
```

Exit 0: met. Exit 1: each miss is listed, with the pages that link here: fix the links, or put the
miss in the PR with the owner's reason to accept it. Exit 2: it cannot judge (no `dist/`, no file
for the page or hub, neither flag, `--hub` for a page with no `<main>`, a page with a
`<base href>`, two files for one address, or a folder it cannot read); say so in the PR.
It cannot see CSS, so whether a counted link is visible and reads naturally is yours to judge,
and to write in the PR. Also judge, never counted: sibling pages link each other where it helps
a reader; anchor text names the target's topic; high-traffic pages (home, FAQ) link to it where
it fits; about 5 to 10 internal links per 1,000 words.

Where the site has `scripts/check_internal_links.sh`, run it too, after the same fresh build (it
reuses an existing `dist/`), for the orphans the new page caused elsewhere: it exits 0 whatever it
finds, so exit 1 means it could not run. Put its message in the PR as printed and count the
report as not run. Where the site has no such script, say so in one line in the PR, and that this
skill can bring the site's link checks up to the kit's version in a PR of its own: the page PR
does not add them.

## Scope notes

- Audits the **active branch** you're on; `dist/` is the build of `src/`, which is
  what Cloudflare serves.
- **Internal** links only. Outgoing (external) link liveness is `outgoing-link-audit`;
  dead in-site links and `#fragment` integrity are the `navigation` + `anchors` specs
  in `website-qa`. This skill answers the orthogonal question: *is every page a link
  target, linked the way the strategy says?*
- **Strategy lives in `site-architecture`** (its Internal Linking Strategy section) —
  this skill is its enforcement arm against the built site, not a second rulebook. When
  the two could drift, `site-architecture` wins; flag the gap rather than re-deciding here.
- The hard gate (`tests/orphans.spec.ts`) only knows pass/fail on reachability-from-
  home; this skill is the richer report (inbound COUNT per page, THIN pages, link
  suggestions) you act on to keep it green.
- **Page-relative links:** `scripts/check_internal_links.sh` resolves only root-relative
  (`/about`) and absolute-on-host links — the kit's convention. It does **not** resolve
  page-relative hrefs (`about`, `./team`, `../pricing`), so a page reachable only via one
  is over-reported as ORPHAN/THIN by the script. The gate `tests/orphans.spec.ts` *does*
  resolve them and is authoritative — trust the gate over the script for those, and prefer
  root-relative links so the two never diverge.
