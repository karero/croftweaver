import { test, expect } from '@playwright/test';
import { onRequest } from '../functions/_middleware';
import { onRequestGet as goEmail } from '../functions/go/email';
import { encodeEmail } from '../src/lib/obfuscate';

// Analytics in server mode (ANALYTICS.mode in src/config.ts): the Pages Function, not the
// browser, sends Plausible one event per page view and per email tap. `astro preview` never
// runs Functions, so these tests call them the way Cloudflare does: a request, the env, next()
// for the static page, and waitUntil for work after the answer. fetch is replaced by a
// recorder, so nothing reaches a real Plausible. Why each case matters is in its title.

const LIVE = 'https://oakandpine.example';
const ENV = { PLAUSIBLE_HOST: 'https://analytics.example.com', PLAUSIBLE_DOMAIN: 'oakandpine.example' };
const VISITOR_IP = '203.0.113.7';
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15';
// What a browser sends when its visitor opens a page.
const NAVIGATION = {
  'Sec-Fetch-Dest': 'document',
  'Sec-Fetch-Mode': 'navigate',
  'Sec-Fetch-Site': 'none',
  'User-Agent': UA,
  'CF-Connecting-IP': VISITOR_IP,
};
// What a browser sends when its visitor clicks a link on this site. Safari sends no
// Sec-Fetch-User (MDN browser-compat-data); Chrome and Firefox add 'Sec-Fetch-User: ?1'.
const CLICK = { ...NAVIGATION, 'Sec-Fetch-Site': 'same-origin', Referer: `${LIVE}/contact` };
const CHROME_CLICK = { ...CLICK, 'Sec-Fetch-User': '?1' };
const HTML = { 'content-type': 'text/html; charset=utf-8' };

type Sent = { url: string; headers: Headers; body: Record<string, string> };

// Replaces fetch for one test: records what would go to Plausible and answers like it does.
function plausible(answer: () => Promise<Response> = async () => new Response('ok', { status: 202 })) {
  const sent: Sent[] = [];
  const real = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    sent.push({ url: String(input), headers: new Headers(init?.headers), body: JSON.parse(String(init?.body)) });
    return answer();
  }) as typeof fetch;
  return { sent, restore: () => { globalThis.fetch = real; } };
}

// Cloudflare's call to the middleware, with waitUntil collected so a test can wait for it.
async function page(
  url: string,
  headers: Record<string, string> = NAVIGATION,
  answer: { status?: number; headers?: Record<string, string> } = {},
  env: Record<string, string> = ENV,
  method = 'GET',
) {
  const pending: Promise<unknown>[] = [];
  const res = await onRequest({
    request: new Request(url, { method, headers }),
    env,
    next: async () => new Response(answer.status === 304 ? null : '<!doctype html><title>page</title>', {
      status: answer.status ?? 200,
      headers: answer.headers ?? HTML,
    }),
    waitUntil: (p) => { pending.push(p); },
  });
  await Promise.all(pending);
  return res;
}

async function tap(query: string, headers: Record<string, string> = CLICK, env: Record<string, string> = ENV, origin = LIVE) {
  const pending: Promise<unknown>[] = [];
  const res = await goEmail({
    request: new Request(`${origin}/go/email?${query}`, { headers }),
    env,
    waitUntil: (p) => { pending.push(p); },
  });
  await Promise.all(pending);
  return res;
}

const ADDRESS = 'hello@oakandpine.example';
const LINK = new URLSearchParams({ e: encodeEmail(ADDRESS), s: 'Kitchen & table', l: 'en' }).toString();

test.describe('page views (S1–S8)', () => {
  test('a visitor opening a page is counted once, with what their browser would have sent: page, referrer, user agent, IP', async () => {
    const p = plausible();
    try {
      const res = await page(`${LIVE}/about?utm_source=newsletter`, { ...NAVIGATION, Referer: 'https://www.google.com/' });
      expect(res.status).toBe(200);
      expect(p.sent).toHaveLength(1);
      const [e] = p.sent;
      expect(e.url).toBe('https://analytics.example.com/api/event');
      expect(e.body).toEqual({
        name: 'pageview',
        url: `${LIVE}/about?utm_source=newsletter`,
        domain: 'oakandpine.example',
        referrer: 'https://www.google.com/',
      });
      expect(e.headers.get('User-Agent')).toBe(UA);
      // Plausible behind Cloudflare reads X-Plausible-IP first; without it, it would count
      // every visitor as Cloudflare's own address, one visitor per browser type.
      expect(e.headers.get('X-Plausible-IP')).toBe(VISITOR_IP);
      expect(e.headers.get('X-Forwarded-For')).toBe(VISITOR_IP);
    } finally {
      p.restore();
    }
  });

  test('a reload answered 304 counts, as the script counts a reload; the 404 page counts too; a server error does not', async () => {
    const p = plausible();
    try {
      await page(`${LIVE}/about`, NAVIGATION, { status: 304, headers: {} });
      await page(`${LIVE}/about.html`, NAVIGATION, { status: 304, headers: {} });
      await page(`${LIVE}/no-such-page`, NAVIGATION, { status: 404 });
      await page(`${LIVE}/about`, NAVIGATION, { status: 500 });
      // A 304 has no Content-Type: a reload of a file opened on its own is not a page view.
      await page(`${LIVE}/images/oak.svg`, NAVIGATION, { status: 304, headers: {} });
      await page(`${LIVE}/build.txt`, NAVIGATION, { status: 304, headers: {} });
      expect(p.sent.map((e) => e.body.url)).toEqual([`${LIVE}/about`, `${LIVE}/about.html`, `${LIVE}/no-such-page`]);
    } finally {
      p.restore();
    }
  });

  test('requests that are not a visitor opening a page are not counted: assets, HEAD, prefetch, frames, and anything without browser headers', async () => {
    const p = plausible();
    try {
      // An image or the build marker ship.sh polls, even as a navigation.
      await page(`${LIVE}/images/oak.webp`, NAVIGATION, { headers: { 'content-type': 'image/webp' } });
      await page(`${LIVE}/build.txt`, NAVIGATION, { headers: { 'content-type': 'text/plain' } });
      await page(`${LIVE}/about`, NAVIGATION, {}, ENV, 'HEAD');
      await page(`${LIVE}/about`, { ...NAVIGATION, 'Sec-Purpose': 'prefetch;prerender' });
      await page(`${LIVE}/about`, { ...NAVIGATION, Purpose: 'prefetch' });
      await page(`${LIVE}/about`, { ...NAVIGATION, 'Sec-Fetch-Dest': 'iframe' });
      // curl, python-requests and scanners send no Sec-Fetch headers; Plausible does not
      // drop them itself (trial 2026-10-15: a scanner found a new host within minutes).
      await page(`${LIVE}/about`, { 'User-Agent': 'curl/8.7.1', 'CF-Connecting-IP': VISITOR_IP });
      await page(`${LIVE}/about`, { 'User-Agent': 'python-requests/2.34.2' });
      expect(p.sent).toEqual([]);
    } finally {
      p.restore();
    }
  });

  test('the email route is not also counted as a page view', async () => {
    const p = plausible();
    try {
      await page(`${LIVE}/go/email?${LINK}`, CLICK, { status: 302, headers: { Location: 'mailto:x@y.z' } });
      await page(`${LIVE}/go/email?${LINK}`, CLICK);
      expect(p.sent).toEqual([]);
    } finally {
      p.restore();
    }
  });

  test('previews, the pages.dev alias, local hosts and a site without both variables never count', async () => {
    const p = plausible();
    try {
      await page('https://my-site.pages.dev/about');
      await page('https://main.my-site.pages.dev/about');
      await page('https://a1b2c3d4.my-site.pages.dev/about');
      await page('http://localhost:8788/about');
      await page('http://127.0.0.1:8788/about');
      await page(`${LIVE}/about`, NAVIGATION, {}, { PLAUSIBLE_HOST: ENV.PLAUSIBLE_HOST });
      await page(`${LIVE}/about`, NAVIGATION, {}, { PLAUSIBLE_DOMAIN: ENV.PLAUSIBLE_DOMAIN });
      await page(`${LIVE}/about`, NAVIGATION, {}, {});
      // Script mode leaves both variables unset: the middleware then sends nothing.
      expect(p.sent).toEqual([]);
    } finally {
      p.restore();
    }
  });

  test('a page that only mentions plausible.init() in its text or a code sample is still counted', async () => {
    const p = plausible();
    try {
      for (const body of [
        '<!doctype html><p>Call plausible.init() once the script has loaded.</p>',
        '<!doctype html><pre><code>&lt;script&gt;window.plausible=window.plausible||function(){};plausible.init()&lt;/script&gt;</code></pre>',
        '<!doctype html><script type="application/ld+json">{"text":"plausible.init()"}</script>',
      ]) {
        const pending: Promise<unknown>[] = [];
        await onRequest({
          request: new Request(`${LIVE}/blog/analytics`, { headers: NAVIGATION }),
          env: ENV,
          next: async () => new Response(body, { status: 200, headers: HTML }),
          waitUntil: (pr) => { pending.push(pr); },
        });
        await Promise.all(pending);
      }
      expect(p.sent).toHaveLength(3);
    } finally {
      p.restore();
    }
  });

  test('a PLAUSIBLE_HOST that is not an https URL counts nothing instead of sending visitor data in the clear', async () => {
    const p = plausible();
    try {
      await page(`${LIVE}/about`, NAVIGATION, {}, { ...ENV, PLAUSIBLE_HOST: 'http://analytics.example.com' });
      await page(`${LIVE}/about`, NAVIGATION, {}, { ...ENV, PLAUSIBLE_HOST: 'analytics.example.com' });
      expect(p.sent).toEqual([]);
    } finally {
      p.restore();
    }
  });

  test('Plausible down, failing or dropping the event never changes the page the visitor gets', async () => {
    for (const answer of [
      async () => { throw new Error('connection refused'); },
      async () => new Response('error', { status: 500 }),
      async () => new Response('ok', { status: 202, headers: { 'x-plausible-dropped': '1' } }),
    ]) {
      const p = plausible(answer);
      try {
        const res = await page(`${LIVE}/about`);
        expect(res.status).toBe(200);
        expect(await res.text()).toBe('<!doctype html><title>page</title>');
        expect(p.sent).toHaveLength(1);
      } finally {
        p.restore();
      }
    }
  });

  test('the page does not wait for Plausible: the answer is complete while Plausible has not replied', async () => {
    let release!: () => void;
    let asked!: () => void;
    const wasAsked = new Promise<void>((resolve) => { asked = resolve; });
    const p = plausible(() => {
      asked();
      return new Promise((resolve) => { release = () => resolve(new Response('ok', { status: 202 })); });
    });
    try {
      const pending: Promise<unknown>[] = [];
      const res = await onRequest({
        request: new Request(`${LIVE}/about`, { headers: NAVIGATION }),
        env: ENV,
        next: async () => new Response('<!doctype html>', { status: 200, headers: HTML }),
        waitUntil: (pr) => { pending.push(pr); },
      });
      // The visitor's answer is complete, body and all, while Plausible has not replied.
      expect(res.status).toBe(200);
      expect(await res.text()).toBe('<!doctype html>');
      expect(pending).toHaveLength(1);
      await wasAsked;
      release();
      await Promise.all(pending);
      expect(p.sent).toHaveLength(1);
    } finally {
      p.restore();
    }
  });
});

test.describe('the email route (S9–S12)', () => {
  test('a click on the email link opens the mail program with the subject, and counts one Email Tap for the page it was on, without the address', async () => {
    const p = plausible();
    try {
      const res = await tap(LINK);
      expect(res.status).toBe(302);
      expect(res.headers.get('Location')).toBe(`mailto:${ADDRESS}?subject=Kitchen%20%26%20table`);
      expect(p.sent).toHaveLength(1);
      expect(p.sent[0].body).toEqual({ name: 'Email Tap', url: `${LIVE}/contact`, domain: 'oakandpine.example' });
      expect(JSON.stringify(p.sent[0].body)).not.toContain(ADDRESS);
      expect(p.sent[0].headers.get('X-Plausible-IP')).toBe(VISITOR_IP);
    } finally {
      p.restore();
    }
  });

  test('a click in Safari, which sends no Sec-Fetch-User, and one in Chrome both open the mail program and count once each', async () => {
    const p = plausible();
    try {
      for (const headers of [CLICK, CHROME_CLICK]) {
        const res = await tap(LINK, headers);
        expect(res.status).toBe(302);
        expect(res.headers.get('Location')).toMatch(/^mailto:/);
      }
      expect(p.sent.map((e) => e.body.name)).toEqual(['Email Tap', 'Email Tap']);
    } finally {
      p.restore();
    }
  });

  test('a % in the address is escaped in the mailto: link, as EmailLink does in script mode', async () => {
    const p = plausible();
    try {
      const res = await tap(new URLSearchParams({ e: encodeEmail('a%41@example.com') }).toString());
      expect(res.headers.get('Location')).toBe('mailto:a%2541@example.com');
    } finally {
      p.restore();
    }
  });

  test('a crawler following the link gets the "[at]" hint, never the address, and counts nothing', async () => {
    const p = plausible();
    try {
      for (const headers of [
        { 'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1)' },
        { 'User-Agent': 'curl/8.7.1' },
        { ...NAVIGATION }, // a typed or pasted address: not a click on this site
      ]) {
        const res = await tap(LINK, headers);
        expect(res.status).toBe(200);
        expect(res.headers.get('Location')).toBeNull();
        const body = await res.text();
        expect(body).toContain('hello [at] oakandpine [dot] example');
        expect(body).not.toContain(ADDRESS);
        expect(res.headers.get('X-Robots-Tag')).toContain('noindex');
      }
      expect(p.sent).toEqual([]);
    } finally {
      p.restore();
    }
  });

  test('a link to the route planted on another site cannot open a mail to a stranger under this site\'s name', async () => {
    const p = plausible();
    try {
      const stranger = new URLSearchParams({ e: encodeEmail('stranger@example.org') }).toString();
      const res = await tap(stranger, { ...CLICK, 'Sec-Fetch-Site': 'cross-site', Referer: 'https://evil.example/' });
      expect(res.status).toBe(200);
      expect(res.headers.get('Location')).toBeNull();
      expect(p.sent).toEqual([]);
    } finally {
      p.restore();
    }
  });

  test('the hint page speaks German for a German page', async () => {
    const res = await tap(new URLSearchParams({ e: encodeEmail(ADDRESS), l: 'de' }).toString(), { 'User-Agent': 'curl/8.7.1' });
    const body = await res.text();
    expect(body).toContain('Schreiben Sie an: hello [at] oakandpine [punkt] example');
    expect(body).toContain('lang="de"');
  });

  test('a broken or forged link gets 400 and no event: no address, a mangled one, a subject too long to be ours', async () => {
    const p = plausible();
    try {
      for (const query of [
        '',
        'e=%%%',
        `e=${encodeURIComponent(btoa('not-an-address'))}`,
        `e=${encodeURIComponent(btoa('moc.elpmaxe@a\r\nbcc:x@y.z'))}`,
        new URLSearchParams({ e: encodeEmail(ADDRESS), s: 'x'.repeat(201) }).toString(),
      ]) {
        const res = await tap(query);
        expect(res.status, query).toBe(400);
        expect(res.headers.get('Location')).toBeNull();
      }
      expect(p.sent).toEqual([]);
    } finally {
      p.restore();
    }
  });

  test('on a preview host the link still opens the mail program, and nothing is counted', async () => {
    const p = plausible();
    try {
      const res = await tap(LINK, { ...CLICK, Referer: 'https://main.my-site.pages.dev/contact' }, ENV, 'https://main.my-site.pages.dev');
      expect(res.status).toBe(302);
      expect(res.headers.get('Location')).toMatch(/^mailto:/);
      expect(p.sent).toEqual([]);
    } finally {
      p.restore();
    }
  });

  test('without the two variables (script mode) the link still opens the mail program, and nothing is counted', async () => {
    const p = plausible();
    try {
      const res = await tap(LINK, CLICK, {});
      expect(res.status).toBe(302);
      expect(p.sent).toEqual([]);
    } finally {
      p.restore();
    }
  });
});
