// Central site configuration. Edit company facts / analytics HERE only — Base.astro,
// schema, llms.txt and the tests all read from this single source. Keep SITE.url in
// sync with `site:` in astro.config.mjs.

export const SITE = {
  url: 'https://example.com',          // production origin, no trailing slash
  name: 'Example',
  legalName: 'Example GmbH',
  locale: 'en',
  themeColor: '#000000',               // matches the brand primary + manifest
  // Home <title> is special-cased (NOT "Example | Example"). Keep ≤ 60 chars.
  titleHome: 'Example: clear, keyword-tuned home page title',
  tagline: 'One-line positioning.',
  // 120–160 chars: default meta description + Organization/WebPage schema text.
  description:
    'Example is a short, specific description of what this site offers and who ' +
    'it is for, written plainly and within the 120 to 160 character window.',
} as const;

// og:locale derivation — ONE implementation shared by Base.astro (emission)
// and tests/seo.spec.ts (assertion), so they can't drift: 'de' → de_DE via
// the map; regioned tags use base + region ('de-AT' → de_AT); unmapped bases
// return undefined (og:locale is optional; a wrong en_US would contradict
// inLanguage).
export const OG_LOCALES: Record<string, string | undefined> = { en: 'en_US', de: 'de_DE', fr: 'fr_FR', es: 'es_ES', it: 'it_IT' };
export function ogLocaleFor(lang: string): string | undefined {
  const [base = '', ...rest] = lang.toLowerCase().split('-');
  const region = rest.at(-1);
  return region && region.length === 2 ? `${base}_${region.toUpperCase()}` : OG_LOCALES[base];
}

export const COMPANY = {
  legalName: 'Example GmbH',
  logo: '/images/logo.png',            // resolved against SITE.url for schema
} as const;

// External profiles that corroborate the entity (EEAT). Only ship URLs that
// resolve — a broken sameAs is worse than none. .filter(Boolean) drops the slots.
export const SAME_AS: string[] = [
  // 'https://www.linkedin.com/company/…',
  // 'https://github.com/…',
].filter(Boolean);

// Topics the site is authoritative on (schema knowsAbout).
export const KNOWS_ABOUT: string[] = [];

// Plausible (cookieless; scriptHost is https://plausible.io for the paid cloud
// version, or your own self-hosted instance). Fire only on the production
// deploy: Cloudflare Pages sets CF_PAGES_BRANCH to the branch being built.
//
// The starter ships with analytics OFF (USE_ANALYTICS = false): no build, the live one
// included, writes the script or the stub, and nothing on the page sends anything to an
// analytics host. A site without analytics keeps it that way and deletes the analytics
// paragraphs of section 3 of the privacy page.
//
// To switch Plausible on: set USE_ANALYTICS to true, fill in scriptHost and scriptId
// below, and add the same host to script-src and connect-src in public/_headers. Keep the
// privacy page's analytics paragraphs and fill their slots. Then run
// `bash tests/check_analytics_gate.sh` (a site's CI does not): it checks the builds and
// the headers, either way. Off or on, leave scriptHost and scriptId in place: Base.astro
// and tests/privacy-host.spec.ts read them. Email links and the contact form work either
// way. They count a tap only with analytics on: in script mode through the script on the
// page; in server mode email links through functions/go/email.ts, and the contact form's
// button not at all (the mode is described below). Left off by mistake,
// Plausible gets no data and nothing says so.
//
// scriptId is the per-site script Plausible's installer shows (the site's installation
// page, <scriptHost>/<your domain>/installation): in <script src=".../js/pa-AbC123.js"> it is
// the part between "/js/" and ".js", here 'pa-AbC123'. The domain and the optional
// measurements (outbound links, file downloads, form submissions) are switched in
// Plausible, not here. Section 3 of the privacy page has one slot sentence for each:
// keep a sentence only if its own measurement is ticked. A scriptHost or scriptId left
// as the placeholder loads nothing (the browser reports a failed request; the build
// does not).
// With analytics on, changing scriptHost also means changing script-src and connect-src
// in public/_headers; tests/check_analytics_gate.sh checks both against this file. It
// also means changing the host named in section 3 of the privacy page, in the
// sentence on refusing the measurement; tests/privacy-host.spec.ts checks that one
// once its slot is filled.
// Base.astro writes two tags (script mode; none in server mode): the script, and the short
// stub that calls plausible.init(); without the stub the script never starts.
//
// The site's one conversion, the "Email Tap" event, is sent (script mode; in server mode by
// functions/go/email.ts) from src/components/EmailLink.astro (and, in script mode only, public/js/mail-form.js when
// the contact form is installed). It needs a goal named exactly "Email Tap" in Plausible before launch. Plausible
// counts a custom event as interaction, so a visit with a tap is not a bounce (its default,
// kept on purpose). Another analytics tool means changing those two calls and section 3 of
// the privacy page.
//
// IMPORTANT: PROD_BRANCH must equal the branch Cloudflare Pages calls "Production"
// for THIS project (house convention: 'production'; Cloudflare's default is 'main').
// A mismatch means analytics silently never loads — no error, no data.
//
// mode, once USE_ANALYTICS is true: 'script' (the default) loads Plausible's script in the browser, as described
// above. 'server' loads nothing in the browser: functions/_middleware.ts sends one page
// view per page request to Plausible's Events API, and on the live build EmailLink.astro
// links to /go/email, where functions/go/email.ts counts the "Email Tap" and opens the
// mail program. Server mode needs two Production variables in Cloudflare (Settings >
// Variables and Secrets): PLAUSIBLE_HOST (the Plausible instance's https origin, usually
// scriptHost's value, never a proxy on this site's own domain) and PLAUSIBLE_DOMAIN (the
// site's domain as added in Plausible); scriptId is not used. It loses scroll depth,
// engaged time and the optional measurements, and the contact form's button is not
// counted. Set those two variables ONLY with USE_ANALYTICS true and mode 'server': the
// Function cannot read this file, so with them set in script mode every page view is
// counted twice, and with analytics off the Function counts anyway.
export const PROD_BRANCH = 'production';

// Keep the value on one line: tests/check_analytics_gate.sh reads it.
export const USE_ANALYTICS = false;

export const ANALYTICS = {
  enabled: USE_ANALYTICS && process.env.CF_PAGES_BRANCH === PROD_BRANCH,
  mode: 'script' as 'script' | 'server', // keep on one line: tests/check_analytics_gate.sh reads it
  scriptHost: 'https://analytics.example.com',
  scriptId: 'pa-XXXXXXXXXXXXXXXXXXXX',
} as const;
