import { test, expect } from '@playwright/test';
import { onRequest } from '../functions/_middleware';

// functions/_middleware.ts decides which hosts Google and AI engines may treat as the
// site. `astro preview` never runs it (it is a Cloudflare Pages Function), so these tests
// call onRequest directly the way Cloudflare does: a request, the env, and next() for
// the static page behind it. Why each case matters is in its title.

const PROJECT = 'my-site'; // any project name — the rule is about the host's shape
// A fixed live origin, NOT SITE.url: the middleware never reads SITE.url, and a site
// still on its pages.dev address (no custom domain yet) must not fail these tests.
const LIVE = 'https://example.com';
const BODY = '<!doctype html><title>page</title>';

async function serve(url: string, env: { CANONICAL_URL?: string } = {}) {
  let served = false;
  const res = await onRequest({
    request: new Request(url),
    env,
    next: async () => {
      served = true;
      return new Response(BODY, { status: 200, headers: { 'content-type': 'text/html' } });
    },
  });
  return { res, served };
}

test('before launch (CANONICAL_URL unset) the production alias still serves the site, noindexed', async () => {
  // Pre-launch the alias may be the ONLY working address — a redirect to a domain that
  // is not attached yet, or still shows an old site, would strand visitors.
  const { res, served } = await serve(`https://${PROJECT}.pages.dev/about`);
  expect(served).toBe(true);
  expect(res.status).toBe(200);
  expect(res.headers.get('x-robots-tag')).toBe('noindex, nofollow');
  expect(await res.text()).toBe(BODY);
});

test('after launch the production alias 301s to the live domain, keeping path and query', async () => {
  // noindex did not stop AI search engines citing <project>.pages.dev; a permanent
  // redirect sends anyone following such a link to the real domain.
  const { res, served } = await serve(`https://${PROJECT}.pages.dev/about?ref=ai`, {
    CANONICAL_URL: LIVE,
  });
  expect(served).toBe(false);
  expect(res.status).toBe(301);
  expect(res.headers.get('location')).toBe(`${LIVE}/about?ref=ai`);
});

test('CANONICAL_URL with a trailing slash or path still redirects to the bare live origin', async () => {
  // The docs ask for the origin only, but a pasted https://example.com/ must not
  // produce https://example.com//about.
  for (const value of [`${LIVE}/`, `${LIVE}/some/path`]) {
    const { res } = await serve(`https://${PROJECT}.pages.dev/about`, { CANONICAL_URL: value });
    expect(res.status).toBe(301);
    expect(res.headers.get('location')).toBe(`${LIVE}/about`);
  }
});

test('a CANONICAL_URL written with a trailing dot redirects to the plain host', async () => {
  const { res } = await serve(`https://${PROJECT}.pages.dev/about`, { CANONICAL_URL: `${LIVE}.` });
  expect(res.headers.get('location')).toBe(`${LIVE}/about`);
});

test('the production alias written with a trailing dot is redirected too', async () => {
  // my-site.pages.dev. is the same host; it must not slip past both the redirect and
  // the noindex.
  const { res } = await serve(`https://${PROJECT}.pages.dev./about`, { CANONICAL_URL: LIVE });
  expect(res.status).toBe(301);
});

test('before launch a preview is served, noindexed, as it always was', async () => {
  const { res, served } = await serve(`https://main.${PROJECT}.pages.dev/`);
  expect(served).toBe(true);
  expect(res.headers.get('x-robots-tag')).toBe('noindex, nofollow');
});

for (const preview of [`main.${PROJECT}.pages.dev`, `3f9a1c2e.${PROJECT}.pages.dev`]) {
  test(`after launch the preview ${preview} still serves, noindexed — not redirected`, async () => {
    // Previews are where the owner checks a change before `npm run ship`; redirecting
    // them to the live domain would hide exactly the build they need to see.
    const { res, served } = await serve(`https://${preview}/`, { CANONICAL_URL: LIVE });
    expect(served).toBe(true);
    expect(res.status).toBe(200);
    expect(res.headers.get('x-robots-tag')).toBe('noindex, nofollow');
  });
}

test('the live domain is served unchanged — no redirect, no noindex', async () => {
  const { res, served } = await serve(`${LIVE}/about`, { CANONICAL_URL: LIVE });
  expect(served).toBe(true);
  expect(res.status).toBe(200);
  expect(res.headers.get('x-robots-tag')).toBeNull();
});

for (const bad of [
  `https://${PROJECT}.pages.dev`,
  `https://${PROJECT}.pages.dev.`,
  `https://${PROJECT}.pages.dev..`,
  'https://pages.dev',
  'https://.',
  'https://...',
  'https://example..com',
  'http://example.com',
  'example.com',
]) {
  test(`a CANONICAL_URL of "${bad}" is ignored, never a redirect loop or downgrade`, async () => {
    // A pages.dev value would redirect the alias to itself; plain http or a bare host is
    // a typo. Failing safe keeps the pre-launch behaviour instead of breaking the site.
    const { res, served } = await serve(`https://${PROJECT}.pages.dev/`, { CANONICAL_URL: bad });
    expect(served).toBe(true);
    expect(res.headers.get('x-robots-tag')).toBe('noindex, nofollow');
  });
}
