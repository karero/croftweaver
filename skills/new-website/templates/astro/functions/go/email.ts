// /go/email: the email link's target in analytics server mode (ANALYTICS.mode in
// src/config.ts). EmailLink.astro points here only on the live build; everywhere else its
// link is a plain mailto: link and this route is never asked.
//
// A visitor's click on the link (a navigation from a page of this site) is answered with
// `302 Location: mailto:<address>?subject=…`, and on the live domain one "Email Tap" event
// goes to Plausible for the page the click came from (functions/_middleware.ts has the
// rules and the sending; a goal named exactly "Email Tap" must exist in Plausible).
//
// Anything else gets a small page with the "name [at] domain" hint, never the address:
// - a crawler following the link would otherwise read the address from the redirect,
//   which is what EmailLink's encoding exists to prevent (robots.txt also disallows /go/);
// - a link to this route planted on another site arrives as cross-site, so the route
//   cannot be used to open a stranger's address under this site's name;
// - a browser too old to send Sec-Fetch headers (Safari before 16.4) still shows the
//   visitor how to write.
// Sec-Fetch-User is NOT required: Safari never sends it (MDN browser-compat-data, read
// 2026-10-16), and requiring it sent every Safari visitor to the hint page.
// The route only ever answers with mailto:, never a web address.
import { eventsUrl, navigationSkip, sendEvent, type AnalyticsEnv } from '../_middleware';
import { emailHint } from '../../src/lib/obfuscate';

interface RouteContext {
  request: Request;
  env: AnalyticsEnv;
  waitUntil?: (promise: Promise<unknown>) => void;
}

// The same pattern encodeEmail (src/lib/obfuscate.ts) accepts at build time.
const ADDRESS = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
// CHANGES IN LOCKSTEP with the build-time check in EmailLink.astro.
const MAX_SUBJECT = 200;

// encodeEmail reverses the address and base64-encodes it; this undoes it. CHANGES IN
// LOCKSTEP with encodeEmail and with the decode script in EmailLink.astro.
function decodeAddress(encoded: string | null): string | null {
  if (!encoded) return null;
  try {
    const address = atob(encoded).split('').reverse().join('');
    return ADDRESS.test(address) ? address : null;
  } catch {
    return null;
  }
}

function clicked(request: Request): boolean {
  const h = request.headers;
  return navigationSkip(request) === null && h.get('Sec-Fetch-Site') === 'same-origin';
}

const NO_STORE = { 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex, nofollow' };

function hintPage(address: string, lang: string): Response {
  const de = lang.toLowerCase().startsWith('de');
  const title = de ? 'E-Mail schreiben' : 'Write an email';
  const lead = de ? 'Schreiben Sie an:' : 'Write to:';
  const back = de ? 'Zurück zur Startseite' : 'Back to the home page';
  // The hint holds only letters, digits, ._%+- and the bracketed words: nothing to escape.
  const html = `<!doctype html><html lang="${de ? 'de' : 'en'}"><head><meta charset="utf-8">`
    + `<meta name="viewport" content="width=device-width, initial-scale=1"><title>${title}</title></head>`
    + `<body><p>${lead} ${emailHint(address, de ? 'de' : 'en')}</p><p><a href="/">${back}</a></p></body></html>`;
  return new Response(html, { status: 200, headers: { ...NO_STORE, 'Content-Type': 'text/html; charset=utf-8' } });
}

export const onRequestGet = async (context: RouteContext): Promise<Response> => {
  const { request, env } = context;
  const url = new URL(request.url);
  const address = decodeAddress(url.searchParams.get('e'));
  const subject = url.searchParams.get('s') ?? '';
  if (!address || subject.length > MAX_SUBJECT) {
    return new Response('This email link is not valid.', { status: 400, headers: { ...NO_STORE, 'Content-Type': 'text/plain; charset=utf-8' } });
  }
  if (!clicked(request)) return hintPage(address, url.searchParams.get('l') ?? 'en');

  const endpoint = eventsUrl(env, url.hostname.replace(/\.+$/, ''));
  if (endpoint && context.waitUntil) {
    // Same-origin, so the browser sends the full page address as the Referer.
    const page = request.headers.get('Referer') ?? `${url.origin}/`;
    context.waitUntil(sendEvent(endpoint, env, request, 'Email Tap', page));
  }
  // encodeEmail allows a % in the address, which a mailto: link must escape.
  const target = `mailto:${address.replace(/%/g, '%25')}${subject ? `?subject=${encodeURIComponent(subject)}` : ''}`;
  return new Response(null, { status: 302, headers: { ...NO_STORE, Location: target } });
};
