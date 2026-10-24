// Cloudflare Pages middleware. Two jobs on Cloudflare's *.pages.dev hosts, and one on the
// live custom domain, whose pages are otherwise always served unchanged:
//
// 1. Preview hosts (<branch>.<project>.pages.dev, <hash>.<project>.pages.dev) get
//    `X-Robots-Tag: noindex` so Google never indexes a staging copy.
// 2. The project's production alias <project>.pages.dev 301-redirects to the live
//    domain — but ONLY once the CANONICAL_URL environment variable is set (Cloudflare
//    dashboard → the project → Settings → Variables and Secrets → Production, e.g.
//    https://example.com, then redeploy). Why: noindex alone did not keep the alias out
//    of AI answers — AI search engines were seen citing <project>.pages.dev instead of
//    the real domain (2026-09). A 301 at least sends every visitor who follows such a
//    link to the real domain, and tells crawlers which host is canonical.
//    Why a variable instead of SITE.url: SITE.url is set before launch, when the domain
//    may not serve this site yet (not attached, or still the old site), and a redirect
//    then would send visitors nowhere useful. Unset, the alias is noindexed like any
//    preview, exactly as before.
//
// 3. Analytics in server mode (ANALYTICS.mode in src/config.ts) only: on the live domain,
//    one page view per page request is sent to Plausible's Events API without the page
//    waiting for it (waitUntil), so no analytics code runs in the visitor's browser.
//    It runs only when the Production variables PLAUSIBLE_HOST and PLAUSIBLE_DOMAIN are
//    set; this file cannot read src/config.ts (that file reads process.env, which a
//    Pages Function does not have), so those two variables are the switch. Previews,
//    the pages.dev alias and local hosts never count. What counts as a page view is
//    pageviewSkip() below; functions/go/email.ts uses navigationSkip() and requires a
//    same-origin click for "Email Tap".
//
// Project names cannot contain dots, so the production alias is the only three-label
// *.pages.dev host; every preview has four. (If that ever changed, a dotted alias would
// simply stay noindexed — the safe side.)
//
// Typed with a minimal local interface so it compiles under the project's strict
// tsconfig WITHOUT depending on @cloudflare/workers-types. (Cloudflare provides
// the real `PagesFunction`/`EventContext` globals at deploy time; this is a
// structural subset of what this handler actually uses.)
export interface AnalyticsEnv {
  PLAUSIBLE_HOST?: string; // e.g. https://analytics.example.com or https://plausible.io
  PLAUSIBLE_DOMAIN?: string; // the site's domain as added in Plausible
}

interface MiddlewareContext {
  request: Request;
  env: { CANONICAL_URL?: string } & AnalyticsEnv;
  next: () => Promise<Response>;
  // Cloudflare always passes it; optional so a test that omits it counts nothing.
  waitUntil?: (promise: Promise<unknown>) => void;
}

// Hostnames may carry trailing dots (example.com.) and still be the same host.
function bareHost(url: URL): string {
  return url.hostname.replace(/\.+$/, '');
}

function isPagesDev(host: string): boolean {
  return host === 'pages.dev' || host.endsWith('.pages.dev');
}

// The live origin from CANONICAL_URL, or null when unset or unusable. A pages.dev value
// would redirect the alias to itself or to a preview, so it counts as unusable too.
function liveOrigin(value: string | undefined): string | null {
  if (!value) return null;
  let url: URL | null = null;
  try {
    url = new URL(value);
  } catch {
    // not a URL at all — reported below with the other unusable values
  }
  const host = url ? bareHost(url) : '';
  const emptyLabel = host.split('.').some((label) => !label); // '', '.x', 'x..y'
  if (!url || url.protocol !== 'https:' || emptyLabel || isPagesDev(host)) {
    console.error(`CANONICAL_URL is not an https live-domain URL, not redirecting: ${value}`);
    return null;
  }
  return `https://${host}${url.port ? `:${url.port}` : ''}`;
}

// --- Analytics in server mode -------------------------------------------------------

function isLocal(host: string): boolean {
  return host === 'localhost' || host.endsWith('.localhost') || host === '127.0.0.1' || host === '[::1]';
}

// The Events API address when this request may be counted, else null: a live host (not
// pages.dev, not local) and both variables set, PLAUSIBLE_HOST an https URL.
export function eventsUrl(env: AnalyticsEnv, host: string): string | null {
  if (!env.PLAUSIBLE_HOST || !env.PLAUSIBLE_DOMAIN || isPagesDev(host) || isLocal(host)) return null;
  let base: URL;
  try {
    base = new URL(env.PLAUSIBLE_HOST);
  } catch {
    console.error(`PLAUSIBLE_HOST is not a URL, not counting: ${env.PLAUSIBLE_HOST}`);
    return null;
  }
  if (base.protocol !== 'https:') {
    console.error(`PLAUSIBLE_HOST is not https, not counting: ${env.PLAUSIBLE_HOST}`);
    return null;
  }
  return `${base.origin}/api/event`;
}

// Why a request is not a visitor's own top-level navigation, or null when it is. Every
// current browser marks one with Sec-Fetch-Dest: document and Sec-Fetch-Mode: navigate
// (Sec-Fetch-Dest since Chrome 80, Firefox 90, Safari 16.4); curl, scripts, scanners and
// most crawlers send neither. Plausible itself drops declared bots by user agent, but not
// curl or python-requests (trial, 2026-10-15). Prefetch and prerender name themselves in
// Sec-Purpose (Chrome), Purpose (Safari, older Chrome), X-Purpose or X-Moz (Firefox).
export function navigationSkip(request: Request): string | null {
  const h = request.headers;
  if (request.method !== 'GET') return 'method';
  const purpose = [h.get('Sec-Purpose'), h.get('Purpose'), h.get('X-Purpose'), h.get('X-Moz')].join(' ');
  if (/prefetch|preview|prerender/i.test(purpose)) return 'prefetch';
  const dest = h.get('Sec-Fetch-Dest');
  if (dest !== 'document') return dest ? 'not-document' : 'no-sec-fetch';
  const mode = h.get('Sec-Fetch-Mode');
  if (mode && mode !== 'navigate') return 'not-navigate';
  if (!h.get('User-Agent')) return 'no-user-agent';
  return null;
}

// Why this response is not a page view, or null when it is: a navigation (above) to a
// page, answered with the page (200), the 404 page (the script counts there too), or a
// 304 for a reload. A 304 carries no Content-Type, so it counts only for a page address:
// no file extension, or .html (the build writes pages as /about, served from about.html).
// A page address with a dot in its last part (/posts/v1.2) is then skipped on a reload.
// /go/ routes count their own events.
export function pageviewSkip(request: Request, path: string, res: Response): string | null {
  const skip = navigationSkip(request);
  if (skip) return skip;
  if (path.startsWith('/go/')) return 'go-route';
  if (res.status === 304) return /\.(?!html$)[^/.]+$/i.test(path) ? 'not-a-page' : null;
  if (res.status !== 200 && res.status !== 404) return 'status';
  if (!(res.headers.get('Content-Type') ?? '').startsWith('text/html')) return 'not-html';
  return null;
}

// One event to the Events API, carrying what the visitor's browser would have sent:
// the page, the referrer, the user agent and the IP. Plausible reads the IP from
// X-Plausible-IP before CF-Connecting-IP and X-Forwarded-For; an instance behind
// Cloudflare would otherwise see Cloudflare's own address (trial, 2026-10-15).
// Plausible Cloud's documentation names X-Forwarded-For, so both are sent. Plausible
// answers 202 even when it drops an event; a drop is logged, never retried.
export async function sendEvent(endpoint: string, env: AnalyticsEnv, request: Request, name: string, page: string): Promise<void> {
  const ip = request.headers.get('CF-Connecting-IP') ?? '';
  const body: Record<string, string> = { name, url: page, domain: env.PLAUSIBLE_DOMAIN ?? '' };
  const referrer = request.headers.get('Referer');
  if (referrer && name === 'pageview') body.referrer = referrer;
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': request.headers.get('User-Agent') ?? '',
        'X-Plausible-IP': ip,
        'X-Forwarded-For': ip,
      },
      body: JSON.stringify(body),
    });
    if (!res.ok || res.headers.get('x-plausible-dropped')) {
      console.error(`Plausible did not take the ${name} event: ${res.status}, dropped ${res.headers.get('x-plausible-dropped') ?? 0}`);
    }
  } catch (err) {
    console.error(`Plausible unreachable, ${name} event lost: ${String(err)}`);
  }
}

// The mode lives in src/config.ts and the switch here is the two variables, which nothing
// makes agree: with them set in script mode every page view is counted twice. Telling a
// script-mode page from its HTML was tried and cut in review (a text scan cannot tell a
// script element from the same text in a comment or attribute); the docs carry the rule.
function countPageview(context: MiddlewareContext, url: URL, host: string, res: Response): void {
  const endpoint = eventsUrl(context.env, host);
  if (!endpoint || !context.waitUntil) return;
  if (pageviewSkip(context.request, url.pathname, res)) return;
  context.waitUntil(sendEvent(endpoint, context.env, context.request, 'pageview', context.request.url));
}

export const onRequest = async (context: MiddlewareContext): Promise<Response> => {
  const url = new URL(context.request.url);
  const host = bareHost(url);
  if (!isPagesDev(host)) {
    const res = await context.next();
    countPageview(context, url, host, res);
    return res;
  }

  const live = liveOrigin(context.env.CANONICAL_URL);
  if (live && host.split('.').length === 3) {
    return Response.redirect(live + url.pathname + url.search, 301);
  }

  const res = await context.next();
  const headers = new Headers(res.headers);
  headers.set('X-Robots-Tag', 'noindex, nofollow');
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers });
};
