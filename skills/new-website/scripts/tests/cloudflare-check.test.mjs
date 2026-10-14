// Tests for cloudflare-check.mjs. Standard library only; run with
//   node --test skills/new-website/scripts/tests/cloudflare-check.test.mjs
//
// Every test that judges a site starts a small web server on 127.0.0.1 and runs the script as
// a program against it, the way a person or an assistant does: real requests, real exit
// status, real output. The server plays a site behind Cloudflare (it sends a cf-ray header),
// and the script is given its address as an origin ("http://127.0.0.1:PORT"). One test serves
// real TLS with a certificate made for the run, so the https path is exercised too.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import https from 'node:https';
import { execFile, execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdtempSync, symlinkSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ITEMS, evaluate, parseProject, parseTarget, readHtml, UsageError } from '../cloudflare-check.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = path.join(HERE, '..', 'cloudflare-check.mjs');
const CHECKLIST = path.join(HERE, '..', '..', '..', '..', 'docs', 'CLOUDFLARE-CHECKLIST.md');
const SHA = '85ca07f1bb53b7078587bce136ef95288fe5115a';

// ---- a site to ask, and the script to ask it

function send(res, status, type, body, extra = {}) {
  res.writeHead(status, { 'content-type': type, ...extra });
  res.end(body);
}

// A site that is right, behind Cloudflare. `tweak(req, res, url)` may answer first (return true).
async function site(tweak = () => false, { secure } = {}) {
  const handler = (req, res) => {
    res.setHeader('server', 'cloudflare');
    res.setHeader('cf-ray', '8a1b2c3d4e5f6071-AMS');
    const url = new URL(req.url, `http://${req.headers.host}`);
    if (tweak(req, res, url)) return;
    const host = req.headers.host;
    if (url.pathname === '/robots.txt') {
      send(res, 200, 'text/plain', `User-agent: *\nAllow: /\n\nSitemap: https://${host}/sitemap-index.xml\n`);
    } else if (url.pathname === '/build.txt') {
      send(res, 200, 'text/plain', `${SHA}\n`);
    } else if (url.pathname === '/' && !url.searchParams.has('cb')) {
      // The plain request is the script's "http://" probe: a site with Always Use HTTPS on
      // answers it with a 301 to the https address.
      res.writeHead(301, { location: `https://${host}/` });
      res.end();
    } else {
      send(res, 200, 'text/html; charset=utf-8', '<!doctype html><title>Site</title><p>Hello</p>');
    }
  };
  const server = secure ? https.createServer(secure, handler) : http.createServer(handler);
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const { port } = server.address();
  const scheme = secure ? 'https' : 'http';
  return {
    port,
    host: `127.0.0.1:${port}`,
    origin: `${scheme}://127.0.0.1:${port}`,
    close: () => { server.closeAllConnections(); return new Promise((r) => server.close(r)); },
  };
}

function run(args, { script = SCRIPT, env, nodeArgs = [] } = {}) {
  return new Promise((resolve) => {
    execFile(process.execPath, [...nodeArgs, script, ...args], { timeout: 60_000, env: { ...process.env, ...env } }, (err, stdout, stderr) => {
      resolve({ code: err ? err.code : 0, stdout, stderr });
    });
  });
}

async function check(origin, ...extra) {
  const r = await run([origin, '--json', '--timeout', '5', ...extra]);
  const parsed = r.stdout ? JSON.parse(r.stdout) : null;
  const by = parsed ? Object.fromEntries(parsed.results.map((x) => [x.id, x])) : {};
  return { ...r, parsed, by };
}

async function withSite(tweak, fn) {
  const s = await site(tweak);
  try {
    return await fn(s);
  } finally {
    await s.close();
  }
}

const isHome = (url) => url.pathname === '/' && url.searchParams.has('cb');
const isProbe = (url) => url.pathname === '/' && !url.searchParams.has('cb');
const homeWith = (extraHeaders, body = '<p>Hi</p>', type = 'text/html') => (req, res, url) => {
  if (isHome(url)) { send(res, 200, type, body, extraHeaders); return true; }
  return false;
};

// ---- a site that is right

test('a clean site: everything an outside request can judge is ok, the rest says what is left', () =>
  withSite(undefined, async (s) => {
    const r = await check(s.origin, '--build', SHA.slice(0, 9));
    assert.equal(r.code, 0, r.stdout);
    for (const id of ['domain', 'https', 'nel', 'bot', 'analytics', 'email', 'scripts', 'robots', 'build']) {
      assert.equal(r.by[id].state, 'ok', `${id}: ${r.by[id].detail}`);
    }
    for (const id of ['build-settings', 'fail-open', 'tls', 'hints', 'ai']) assert.equal(r.by[id].state, 'hand', id);
    assert.match(r.by.ai.detail, /none of 6 AI crawler names was refused/);
    assert.equal(r.by.hsts.state, 'look', 'HSTS is not on yet, which is not a failure');
    assert.equal(r.by.pages.state, 'skip');
    assert.equal(r.by.canonical.state, 'skip');
    assert.deepEqual(r.parsed.unanswered, []);
    assert.deepEqual(r.parsed.couldNotJudge, []);
    assert.deepEqual(r.parsed.results.map((x) => x.id), ITEMS.map((i) => i.id), 'every item, in the checklist\'s order');
    for (const x of r.parsed.results) {
      if (x.state === 'ok' || x.state === 'skip' || x.state === 'hand') assert.equal('fix' in x, false, `${x.id} carries a fix it never shows`);
    }
  }));

test('without --build the live build is only a look: nothing was compared', () =>
  withSite(undefined, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.build.state, 'look');
    assert.match(r.by.build.detail, /pass --build/);
    assert.equal(r.code, 0);
  }));

test('the plain-text report names every item and ends with a result line', () =>
  withSite(undefined, async (s) => {
    const r = await run([s.origin, '--timeout', '5']);
    assert.equal(r.code, 0);
    for (const item of ITEMS) assert.ok(r.stdout.includes(item.title.replace(/`/g, '')), `missing: ${item.title}`);
    assert.match(r.stdout, /Result: \d+ ok, 0 FAIL, \d+ look, 5 by hand, 2 not run\./);
    assert.match(r.stdout, /Nothing was changed\./);
  }));

// ---- Network Error Logging

test('NEL still on: the item fails and shows how long browsers keep the note', () =>
  withSite(homeWith({
    nel: '{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}',
    'report-to': '{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4"}]}',
  }), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.code, 1);
    assert.equal(r.by.nel.state, 'fail');
    assert.match(r.by.nel.detail, /max_age 604800/);
    assert.equal(r.by.https.state, 'ok', 'a failing item does not spoil the others');
  }));

test('Cloudflare\'s reporting group alone still fails; a group of your own is a "look"', async () => {
  await withSite(homeWith({ 'report-to': '{"group":"cf-nel","max_age":604800}' }), async (s) => {
    assert.equal((await check(s.origin)).by.nel.state, 'fail');
  });
  await withSite(homeWith({ 'report-to': '{"group":"mine"}' }), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.nel.state, 'look');
    assert.equal(r.code, 0);
  });
});

test('a nel header with max_age 0 is the way a policy is withdrawn: a "look", not "on"', () =>
  withSite(homeWith({ nel: '{"max_age":0}' }), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.nel.state, 'look');
    assert.match(r.by.nel.detail, /max_age 0/);
  }));

// ---- an empty answer is never a pass

test('no answer at all: the domain fails, nothing that needs the page reads "ok", exit 1', async () => {
  const s = await site();
  await s.close(); // the port is now closed
  const r = await check(s.origin);
  assert.equal(r.code, 1);
  assert.equal(r.by.domain.state, 'fail');
  assert.equal(r.by.https.state, 'fail');
  for (const id of ['hsts', 'nel', 'bot', 'analytics', 'email', 'scripts', 'ai', 'robots', 'build']) {
    assert.equal(r.by[id].state, 'skip', `${id} must not pass on a dead request`);
  }
  assert.match(r.by.domain.detail, /connection was refused/);
  assert.ok(r.parsed.unanswered.length >= 5, 'the requests that got no answer are listed');
});

test('an answer that is cut off is no answer, whatever its first bytes said', () =>
  withSite((req, res, url) => {
    if (isHome(url)) {
      res.writeHead(200, { 'content-type': 'text/html', 'content-length': '100000' });
      res.write('<html><body><p>partial');
      setTimeout(() => res.socket.destroy(), 50);
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.domain.state, 'fail');
    assert.match(r.by.domain.detail, /cut off/);
    for (const id of ['nel', 'bot', 'analytics', 'email', 'scripts']) assert.equal(r.by[id].state, 'skip', id);
    assert.equal(r.code, 1);
  }));

test('an answer that starts and then stalls times out as no answer', () =>
  withSite((req, res, url) => {
    if (isHome(url)) {
      res.writeHead(200, { 'content-type': 'text/html', 'content-length': '5000' });
      res.write('<html><body>partial'); // and nothing more
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin, '--timeout', '1');
    assert.equal(r.by.domain.state, 'fail');
    assert.match(r.by.domain.detail, /no answer within 1 second\b/);
    assert.equal(r.by.analytics.state, 'skip');
  }));

test('a page larger than what is read is never "ok" on what was read', () =>
  withSite(homeWith({}, `<!doctype html><body>${'x'.repeat(5_200_000)}<script defer src="https://static.cloudflareinsights.com/beacon.min.js"></script></body>`), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.domain.state, 'ok');
    for (const id of ['bot', 'analytics', 'email', 'scripts']) {
      assert.equal(r.by[id].state, 'look', id);
      assert.match(r.by[id].detail, /larger than 5 MB/);
    }
  }));

test('an error page is not judged as the site: a 522 fails the domain and the privacy items are not run', () =>
  withSite((req, res, url) => {
    if (isHome(url)) {
      send(res, 522, 'text/html', '<p>Connection timed out</p>', { 'report-to': '{"group":"cf-nel"}' });
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.domain.state, 'fail');
    assert.match(r.by.domain.detail, /522.*not attached/);
    assert.equal(r.by.nel.state, 'skip');
    assert.equal(r.by.bot.state, 'skip');
    assert.equal(r.code, 1);
  }));

test('a challenge page is named as such, and the site is not judged from it', () =>
  withSite((req, res, url) => {
    if (isHome(url)) {
      send(res, 403, 'text/html', '<p>Just a moment...</p>', { 'cf-mitigated': 'challenge' });
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.domain.state, 'fail');
    assert.match(r.by.domain.detail, /challenge page/);
    assert.equal(r.by.analytics.state, 'skip');
  }));

test('an answer that is not a 200 page cannot be judged: 204 is a look and the items are not run, exit 1', () =>
  withSite((req, res, url) => {
    if (isHome(url)) { res.writeHead(204); res.end(); return true; }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.domain.state, 'look');
    assert.match(r.by.domain.detail, /204, not a 200/);
    for (const id of ['bot', 'analytics', 'email', 'scripts']) assert.equal(r.by[id].state, 'skip', id);
    assert.equal(r.code, 1, 'an assistant reading only the exit status must not take this for a pass');
  }));

test('an answer that did not come through Cloudflare is a "look": any 200 is not the site', () =>
  withSite((req, res) => {
    res.removeHeader('cf-ray');
    res.removeHeader('server');
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.domain.state, 'look');
    assert.match(r.by.domain.detail, /no cf-ray header came with the answer/);
  }));

// ---- redirects on the home page

test('a redirect to the same address is followed and the page is judged where it ends', () =>
  withSite((req, res, url) => {
    if (isHome(url)) {
      res.writeHead(301, { location: '/en/' });
      res.end();
      return true;
    }
    if (url.pathname === '/en/') {
      send(res, 200, 'text/html', '<script defer src="https://static.cloudflareinsights.com/beacon.min.js"></script>', { nel: '{"max_age":604800}' });
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.domain.state, 'look');
    assert.match(r.by.domain.detail, /answered 301 first and sent us to \/en\//);
    assert.equal(r.by.analytics.state, 'fail', 'the page it leads to was read');
    assert.equal(r.by.nel.state, 'fail');
    assert.deepEqual(r.parsed.couldNotJudge, []);
  }));

test('a redirect to another address is not followed: the items are not run, exit 1', () =>
  withSite((req, res, url) => {
    if (isHome(url)) {
      res.writeHead(301, { location: 'https://www.elsewhere.invalid/', nel: '{"max_age":604800}' });
      res.end('<html><head><title>301 Moved Permanently</title></head><body>cloudflare</body></html>');
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.domain.state, 'look');
    assert.match(r.by.domain.detail, /elsewhere\.invalid/);
    for (const id of ['bot', 'analytics', 'email', 'scripts']) assert.equal(r.by[id].state, 'skip', id);
    assert.equal(r.by.nel.state, 'fail', 'the header of a redirect still counts');
    assert.match(r.by.nel.detail, /judged from the 301 answer/);
    assert.equal(r.code, 1);
  }));

// ---- http:// goes to https://

test('the https redirect must lead to the whole address: a longer host is not it', () =>
  withSite((req, res, url) => {
    if (isProbe(url)) {
      res.writeHead(301, { location: `https://${req.headers.host}9/` }); // one digit longer: the ".com.au" slip, on a port
      res.end();
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.https.state, 'fail');
    assert.match(r.by.https.detail, /not to https:\/\//);
  }));

test('the https redirect is judged as an address: another host that quotes ours in a query does not pass', () =>
  withSite((req, res, url) => {
    if (isProbe(url)) {
      res.writeHead(301, { location: `https://evil.invalid/?u=https://${req.headers.host}/` });
      res.end();
      return true;
    }
    return false;
  }, async (s) => {
    assert.equal((await check(s.origin)).by.https.state, 'fail');
  }));

test('the same address written another way is still the https redirect', () =>
  withSite((req, res, url) => {
    if (isProbe(url)) {
      res.writeHead(308, { location: `https://${req.headers.host}` }); // no trailing slash
      res.end();
      return true;
    }
    return false;
  }, async (s) => {
    assert.equal((await check(s.origin)).by.https.state, 'ok');
  }));

test('http:// answering 200 is a failure: Always Use HTTPS is not reaching it', () =>
  withSite((req, res, url) => {
    if (isProbe(url)) { send(res, 200, 'text/html', '<p>Hi</p>'); return true; }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.https.state, 'fail');
    assert.match(r.by.https.detail, /no redirect/);
  }));

test('a 302 to the right place is a "look": visitors arrive, but it is not Always Use HTTPS', () =>
  withSite((req, res, url) => {
    if (isProbe(url)) {
      res.writeHead(302, { location: `https://${req.headers.host}/` });
      res.end();
      return true;
    }
    return false;
  }, async (s) => {
    assert.equal((await check(s.origin)).by.https.state, 'look');
  }));

// ---- what Cloudflare adds to the page

const INJECTED = `<!doctype html><html><body><p>Hello</p>
  <a href="/cdn-cgi/l/email-protection#ab12">[email&#160;protected]</a>
  <script src="/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js"></script>
  <script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "abc"}'></script>
  <script>(function(){var a=document.createElement('script');a.src='/cdn-cgi/challenge-platform/scripts/jsd/main.js';document.head.appendChild(a);})();</script>
</body></html>`;

test('what Cloudflare injects is found: the bot script (inline), the beacon, the address hiding', () =>
  withSite(homeWith({ 'set-cookie': '__cf_bm=abc; path=/; HttpOnly' }, INJECTED), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.code, 1);
    assert.equal(r.by.bot.state, 'fail');
    assert.match(r.by.bot.detail, /__cf_bm/);
    assert.equal(r.by.analytics.state, 'fail');
    assert.equal(r.by.email.state, 'fail');
  }));

test('the bot script alone is found when no cookie was set', () =>
  withSite(homeWith({}, '<script>var a=document.createElement("script");a.src="/cdn-cgi/challenge-platform/scripts/jsd/main.js";</script>'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.bot.state, 'fail');
    assert.match(r.by.bot.detail, /challenge-platform/);
    assert.equal(r.by.analytics.state, 'ok');
  }));

test('words about these scripts are not the scripts: a comment, a paragraph and a code sample pass', () =>
  withSite(homeWith({}, `<!doctype html><body>
    <!-- static.cloudflareinsights.com and /cdn-cgi/challenge-platform and email-decode -->
    <p>We switched off cloudflareinsights and email-decode.min.js, and cdn-cgi/challenge-platform too.</p>
    <pre><code>&lt;script src="/cdn-cgi/scripts/x/email-decode.min.js"&gt;</code></pre></body>`), async (s) => {
    const r = await check(s.origin);
    for (const id of ['bot', 'analytics', 'email', 'scripts']) assert.equal(r.by[id].state, 'ok', `${id}: ${r.by[id].detail}`);
  }));

test('another /cdn-cgi/ feature is a "look" that names it, not a pass', () =>
  withSite(homeWith({}, '<script src="/cdn-cgi/zaraz/i.js"></script><script src="/cdn-cgi/scripts/7d0fa10a/cloudflare-static/rocket-loader.min.js"></script>'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.scripts.state, 'look');
    assert.match(r.by.scripts.detail, /zaraz\/i\.js/);
    assert.match(r.by.scripts.detail, /rocket-loader/);
    assert.equal(r.by.bot.state, 'ok');
    assert.equal(r.code, 0);
  }));

test('a cookie that is not Cloudflare\'s is a "look" that does not blame Bot Fight Mode', () =>
  withSite(homeWith({ 'set-cookie': 'theme=dark; path=/' }), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.bot.state, 'look');
    assert.match(r.by.bot.detail, /not Cloudflare's own: theme/);
  }));

// ---- HSTS

test('HSTS: missing is a "look" until --hsts-on says it should be there', () =>
  withSite(undefined, async (s) => {
    assert.equal((await check(s.origin)).by.hsts.state, 'look');
    const r = await check(s.origin, '--hsts-on');
    assert.equal(r.by.hsts.state, 'fail');
    assert.equal(r.code, 1);
  }));

test('HSTS: read as directives: months, subdomains, preload; a lookalike or a short age is not "on"', async () => {
  const cases = [
    ['max-age=15552000; includeSubDomains', 'ok', /\(about 6 months\), subdomains on, preload off/],
    ['max-age="15552000"', 'ok', /about 6 months\), subdomains off/],
    ['max-age=31536000; includeSubDomains; preload', 'look', /preload/],
    ['not-max-age=15552000; max-age=0', 'look', /max-age of 0/],
    ['x-max-age=15552000', 'look', /max-age of 0, or none/],
    ['max-age=60', 'look', /shorter than the one month/],
  ];
  for (const [value, state, detail] of cases) {
    await withSite(homeWith({ 'strict-transport-security': value }), async (s) => {
      const r = await check(s.origin, '--hsts-on');
      assert.equal(r.by.hsts.state, state, value);
      assert.match(r.by.hsts.detail, detail, value);
    });
  }
});

// ---- robots.txt and AI crawlers

const robotsWith = (body) => (req, res, url) => {
  if (url.pathname === '/robots.txt') { send(res, 200, 'text/plain', body); return true; }
  return false;
};

test('robots.txt that still names the starter\'s example.com is a failure', () =>
  withSite(robotsWith('User-agent: *\nAllow: /\n\n# Set to the real production domain before launch.\nSitemap: https://example.com/sitemap-index.xml\n'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.robots.state, 'fail');
    assert.match(r.by.robots.detail, /example\.com/);
  }));

test('a sitemap on another host is not the placeholder because its name contains "example.com"', async () => {
  await withSite(robotsWith('User-agent: *\nAllow: /\nSitemap: https://myexample.com/sitemap.xml\n'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.robots.state, 'look');
    assert.match(r.by.robots.detail, /names myexample\.com/);
  });
  await withSite((req, res, url) => {
    if (url.pathname === '/robots.txt') {
      send(res, 200, 'text/plain', `User-agent: *\nAllow: /\nSitemap: https://${req.headers.host}/sitemap.xml?ref=example.com\n`);
      return true;
    }
    return false;
  }, async (s) => {
    assert.equal((await check(s.origin)).by.robots.state, 'ok');
  });
});

test('robots.txt that tells every crawler to stay out fails; a private folder does not', async () => {
  await withSite(robotsWith('User-agent: *\nDisallow: /\n'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.robots.state, 'fail');
    assert.match(r.by.robots.detail, /every crawler to stay out/);
    assert.equal(r.by.ai.state, 'look');
  });
  await withSite((req, res, url) => {
    if (url.pathname === '/robots.txt') {
      send(res, 200, 'text/plain', `User-agent: *\nDisallow: /private/\n\nSitemap: https://${req.headers.host}/sitemap.xml\n`);
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.robots.state, 'ok');
    assert.equal(r.by.ai.state, 'hand');
  });
});

test('rules for named crawlers in robots.txt make the AI item a "look"', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/robots.txt') {
      send(res, 200, 'text/plain', `User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /\n\nSitemap: https://${req.headers.host}/sitemap-index.xml\n`);
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.robots.state, 'ok');
    assert.equal(r.by.ai.state, 'look');
    assert.match(r.by.ai.detail, /GPTBot/);
  }));

test('robots.txt that is a web page fails; a comment that mentions html does not', async () => {
  await withSite(robotsWith('<!doctype html><title>Home</title>'), async (s) => {
    assert.equal((await check(s.origin)).by.robots.state, 'fail');
  });
  await withSite((req, res, url) => {
    if (url.pathname === '/robots.txt') {
      send(res, 200, 'text/plain', `# generated for the <html> pages\nUser-agent: *\nAllow: /\nSitemap: https://${req.headers.host}/sitemap.xml\n`);
      return true;
    }
    return false;
  }, async (s) => {
    assert.equal((await check(s.origin)).by.robots.state, 'ok');
  });
});

test('robots.txt that cannot be had: 404 is a look, 500 a failure, no answer a failure and exit 1', async () => {
  await withSite((req, res, url) => {
    if (url.pathname === '/robots.txt') { res.writeHead(404); res.end(); return true; }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.robots.state, 'look');
    assert.equal(r.by.ai.state, 'hand');
    assert.match(r.by.ai.detail, /robots\.txt could not be read/);
  });
  await withSite((req, res, url) => {
    if (url.pathname === '/robots.txt') { res.writeHead(500); res.end(); return true; }
    return false;
  }, async (s) => {
    assert.equal((await check(s.origin)).by.robots.state, 'fail');
  });
  await withSite((req, res, url) => {
    if (url.pathname === '/robots.txt') { req.socket.destroy(); return true; }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.robots.state, 'fail');
    assert.equal(r.code, 1);
  });
});

test('an AI crawler name that is refused is a "look" that names it and its status', () =>
  withSite((req, res, url) => {
    if (isHome(url) && /ClaudeBot/.test(req.headers['user-agent'])) {
      send(res, 403, 'text/html', '<p>Blocked</p>');
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.ai.state, 'look');
    assert.match(r.by.ai.detail, /ClaudeBot \(403\)/);
    assert.equal(r.by.domain.state, 'ok', 'a browser-like request is not refused');
  }));

test('crawler requests that got no answer are not "none refused": a look, and exit 1', () =>
  withSite((req, res, url) => {
    if (isHome(url) && /PerplexityBot|CCBot/.test(req.headers['user-agent'])) { req.socket.destroy(); return true; }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.ai.state, 'look');
    assert.match(r.by.ai.detail, /2 of 6 crawler requests got no answer \(PerplexityBot, CCBot\)/);
    assert.equal(r.parsed.unanswered.length, 2);
    assert.equal(r.code, 1);
  }));

// ---- build.txt

const buildWith = (body, type = 'text/plain') => (req, res, url) => {
  if (url.pathname === '/build.txt') { send(res, 200, type, body); return true; }
  return false;
};

test('--build: the same commit passes, another one fails', () =>
  withSite(undefined, async (s) => {
    const same = await check(s.origin, '--build', SHA.slice(0, 10));
    assert.equal(same.by.build.state, 'ok');
    assert.match(same.by.build.detail, /the one you expected/);
    const other = await check(s.origin, '--build', '1234567');
    assert.equal(other.by.build.state, 'fail');
    assert.equal(other.code, 1);
  }));

test('a build marker that is not a full commit id proves nothing: "dev", a page, a short id', async () => {
  await withSite(buildWith('dev\n'), async (s) => {
    assert.equal((await check(s.origin)).by.build.state, 'look');
  });
  await withSite(buildWith('<!doctype html><p>app</p>', 'text/html'), async (s) => {
    assert.equal((await check(s.origin, '--build', SHA.slice(0, 7))).by.build.state, 'look', 'a page is not a build marker');
  });
  await withSite(buildWith(`${SHA.slice(0, 7)}\n`), async (s) => {
    const r = await check(s.origin, '--build', SHA);
    assert.equal(r.by.build.state, 'look', 'seven characters cannot confirm forty');
    assert.match(r.by.build.detail, /7 characters/);
  });
});

test('build.txt that got no answer, with the domain fine, is a look and a non-zero exit', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/build.txt') { req.socket.destroy(); return true; }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.build.state, 'look');
    assert.equal(r.code, 1);
    assert.equal(r.parsed.unanswered.length, 1);
  }));

// ---- the pages.dev address

test('--project: the alias that forwards to the domain passes the forward, and its NEL note stays beside the domain\'s result', async () => {
  await withSite(undefined, async (live) => {
    await withSite((req, res) => {
      res.writeHead(301, { location: `https://${live.host}/?cb=1`, nel: '{"max_age":604800}', 'report-to': '{"group":"cf-nel"}' });
      res.end();
      return true;
    }, async (alias) => {
      const r = await check(live.origin, '--project', alias.origin);
      assert.equal(r.by.canonical.state, 'ok');
      assert.equal(r.by.pages.state, 'look', 'a local address is not known to be a pages.dev project');
      assert.equal(r.by.nel.state, 'ok');
      assert.match(r.by.nel.detail, /pages\.dev address still sends nel and report-to headers/);
      assert.equal(r.code, 0);
    });
  });
});

test('--project: an alias that answers 200 means the forward is not set, and the causes are listed', async () => {
  await withSite(undefined, async (live) => {
    await withSite((req, res) => { send(res, 200, 'text/html', '<p>Hi</p>', { 'x-robots-tag': 'noindex' }); return true; }, async (alias) => {
      const r = await check(live.origin, '--project', alias.origin);
      assert.equal(r.by.canonical.state, 'fail');
      assert.match(r.by.canonical.detail, /CANONICAL_URL/);
      assert.equal(r.code, 1);
    });
  });
});

test('--project: a forward to another address fails, and a name that does not answer is named', async () => {
  await withSite(undefined, async (live) => {
    await withSite((req, res) => { res.writeHead(301, { location: 'https://elsewhere.invalid/' }); res.end(); return true; }, async (alias) => {
      const r = await check(live.origin, '--project', alias.origin);
      assert.equal(r.by.canonical.state, 'fail');
      assert.match(r.by.canonical.detail, /elsewhere\.invalid/);
    });
  });
  const gone = await site();
  await gone.close();
  await withSite(undefined, async (live) => {
    const r = await check(live.origin, '--project', gone.origin);
    assert.equal(r.by.pages.state, 'fail');
    assert.equal(r.by.canonical.state, 'skip');
    assert.equal(r.code, 1);
  });
});

test('an alias that answers 404, 500 or a challenge is not "a Pages project, ok"', () => {
  const target = parseTarget('example.com');
  const base = (alias) => ({
    home: { url: 'https://example.com/?cb=1', status: 200, headers: { 'content-type': 'text/html', 'cf-ray': 'x' }, body: '<p>Hi</p>', hops: [] },
    robots: { url: 'https://example.com/robots.txt', status: 404, headers: {}, body: '' },
    httpProbe: { url: 'http://example.com/', status: 301, headers: { location: 'https://example.com/' }, body: '' },
    build: { url: 'https://example.com/build.txt?cb=1', status: 404, headers: {}, body: '' },
    crawlers: [], alias, aliasIsPagesDev: true,
  });
  const by = (alias) => Object.fromEntries(evaluate(base(alias), target, { timeoutMs: 5000 }).map((r) => [r.id, r]));
  const at = (status, headers = {}) => ({ url: 'https://shop.pages.dev/?cb=1', status, headers, body: '' });
  assert.equal(by(at(200)).pages.state, 'ok');
  assert.equal(by(at(404)).pages.state, 'fail');
  assert.equal(by(at(500)).pages.state, 'fail');
  assert.equal(by(at(403, { 'cf-mitigated': 'challenge' })).pages.state, 'fail');
  assert.equal(by(at(301, { location: 'https://example.com/?cb=1' })).canonical.state, 'ok');
});

test('--project takes a Pages project, not any address', () => {
  assert.equal(parseProject('shop').origin, 'https://shop.pages.dev');
  assert.equal(parseProject('Shop.pages.dev').host, 'Shop.pages.dev');
  assert.equal(parseProject('https://shop.pages.dev').pagesDev, true);
  assert.equal(parseProject('http://127.0.0.1:8788').pagesDev, false);
  for (const bad of ['https://worker.example', 'http://worker.test.example.com', 'no good!', 'a/b', 'https://x.workers.dev']) {
    assert.throws(() => parseProject(bad), UsageError, bad);
  }
});

// ---- https, for real

test('https: a closed port is "connection refused" through the https path', async () => {
  const s = await site();
  await s.close();
  const r = await check(`https://127.0.0.1:${s.port}`);
  assert.equal(r.by.domain.state, 'fail');
  assert.match(r.by.domain.detail, /connection was refused/);
  assert.equal(r.code, 1);
});

test('https: a site behind a certificate is read over TLS, and an untrusted one is named', async (t) => {
  const dir = mkdtempSync(path.join(tmpdir(), 'cfcheck-tls-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const cnf = path.join(dir, 'openssl.cnf');
  writeFileSync(cnf, '[req]\ndistinguished_name = dn\nx509_extensions = v3\nprompt = no\n[dn]\nCN = 127.0.0.1\n[v3]\nsubjectAltName = IP:127.0.0.1,DNS:localhost\n');
  const key = path.join(dir, 'key.pem');
  const cert = path.join(dir, 'cert.pem');
  try {
    execFileSync('openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', key, '-out', cert, '-days', '1', '-config', cnf], { stdio: 'ignore' });
  } catch {
    t.skip('openssl is not available to make a certificate for this run');
    return;
  }
  const s = await site(undefined, { secure: { key: readFileSync(key), cert: readFileSync(cert) } });
  try {
    const r = await run([s.origin, '--json', '--timeout', '5', '--hsts-on'], { env: { NODE_EXTRA_CA_CERTS: cert } });
    const by = Object.fromEntries(JSON.parse(r.stdout).results.map((x) => [x.id, x]));
    assert.equal(by.domain.state, 'ok', by.domain.detail);
    assert.equal(by.nel.state, 'ok');
    assert.equal(by.hsts.state, 'fail', 'the server sends no HSTS and --hsts-on says it should');
    const untrusted = await run([s.origin, '--json', '--timeout', '5'], { env: { NODE_EXTRA_CA_CERTS: '' } });
    const u = Object.fromEntries(JSON.parse(untrusted.stdout).results.map((x) => [x.id, x]));
    assert.equal(u.domain.state, 'fail');
    assert.match(u.domain.detail, /certificate cannot be trusted/);
  } finally {
    await s.close();
  }
});

// ---- what the fixes of round 1 must not break

test('a header on the way counts: NEL and a Cloudflare cookie on the first answer of a followed redirect', () =>
  withSite((req, res, url) => {
    if (isHome(url) && url.pathname === '/' && !url.searchParams.has('lang')) {
      res.writeHead(301, { location: '/en/', nel: '{"max_age":604800}', 'set-cookie': '__cf_bm=abc; path=/' });
      res.end();
      return true;
    }
    if (url.pathname === '/en/') { send(res, 200, 'text/html', '<p>Clean page</p>'); return true; }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.nel.state, 'fail');
    assert.equal(r.by.bot.state, 'fail');
    assert.match(r.by.bot.detail, /__cf_bm/);
  }));

test('what a tag says about itself is not what it loads: titles, alt text and data attributes pass', () =>
  withSite(homeWith({}, `<!doctype html><body>
    <p title="We disabled cloudflareinsights and email-decode and /cdn-cgi/challenge-platform">Hi</p>
    <img src="/logo.png" alt="cloudflareinsights /cdn-cgi/l/email-protection">
    <div data-note="data-cfemail cdn-cgi/scripts/x/email-decode.min.js"></div></body>`), async (s) => {
    const r = await check(s.origin);
    for (const id of ['bot', 'analytics', 'email', 'scripts']) assert.equal(r.by[id].state, 'ok', `${id}: ${r.by[id].detail}`);
  }));

test('only Cloudflare\'s own paths are excluded from "other scripts": a longer path that quotes one is not', () =>
  withSite(homeWith({}, '<img src="/cdn-cgi/image/width=100/https://site.test/challenge-platform.png"><span data-cfemail="ab12">x</span>'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.scripts.state, 'look');
    assert.match(r.by.scripts.detail, /cdn-cgi\/image\/width=100/);
    assert.equal(r.by.email.state, 'fail', 'data-cfemail as an attribute is Cloudflare\'s');
  }));

test('a reporting group is judged by what it is: one of your own named like Cloudflare\'s is yours', async () => {
  await withSite(homeWith({ 'report-to': '{"group":"my-cf-nel-backup","max_age":86400,"endpoints":[{"url":"https://reports.example.invalid/r"}]}' }), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.nel.state, 'look');
    assert.equal(r.code, 0);
  });
  await withSite(homeWith({ 'report-to': '{"group":"mine","max_age":1,"endpoints":[{"url":"https://r.example.invalid"}]}, {"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4"}]}' }), async (s) => {
    assert.equal((await check(s.origin)).by.nel.state, 'fail', 'Cloudflare\'s group is the second of two');
  });
  await withSite(homeWith({ 'report-to': 'not json at all' }), async (s) => {
    assert.equal((await check(s.origin)).by.nel.state, 'look');
  });
});

// ---- Cloudflare's script monitor (Client-side security): reports to csp-reporting.cloudflare.com

const MONITOR_URL = 'https://csp-reporting.cloudflare.com/cdn-cgi/script_monitor/report?m=abc123';
// The names are spelled as Cloudflare spells them on the wire; Node hands them over in lower case.
const MONITOR = {
  'Content-Security-Policy-Report-Only': `script-src 'unsafe-inline' 'unsafe-eval'; connect-src 'none'; report-uri ${MONITOR_URL}; report-to cf-csp-endpoint`,
  'Report-To': `{"group":"cf-csp-endpoint","max_age":86400,"endpoints":[{"url":"${MONITOR_URL}"}]}`,
  'Reporting-Endpoints': `cf-csp-endpoint="${MONITOR_URL}"`,
};
// Addresses that only look like Cloudflare's reporting host. None of them reports there.
const LOOKALIKES = [
  'https://csp-reporting.cloudflare.com.reports.example.invalid/r',
  'https://not-csp-reporting.cloudflare.com/r',
  'https://csp-reporting.cloudflare.com@reports.example.invalid/r',
  'https://csp-reporting.cloudflare.com_x/r',
  'https://reports.example.invalid/r?u=https://csp-reporting.cloudflare.com/x',
  'https://reports.example.invalid/csp-reporting.cloudflare.com/collect',
];

test('the script monitor is named, with the path to its switch, not shown as a bare report-to header', () =>
  withSite(homeWith(MONITOR), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.nel.state, 'look');
    assert.equal(r.code, 0, 'a look does not fail the run');
    assert.match(r.by.nel.detail, /script monitor is switched on/);
    assert.match(r.by.nel.detail, /csp-reporting\.cloudflare\.com/);
    assert.match(r.by.nel.detail, /sample/);
    assert.doesNotMatch(r.by.nel.detail, /its own reporting groups/, 'not the text for a header that is not known');
    assert.match(r.by.nel.fix, /Client-side abuse/);
    assert.match(r.by.nel.fix, /Continuous script monitoring/);
    assert.match(r.by.nel.fix, /NEL does not remove it/, 'the checklist\'s NEL rule is not the way to remove it');
  }));

test('any one of the script monitor\'s three headers names it, however the address is written', async () => {
  for (const name of Object.keys(MONITOR)) {
    await withSite(homeWith({ [name]: MONITOR[name] }), async (s) => {
      const r = await check(s.origin);
      assert.equal(r.by.nel.state, 'look', name);
      assert.match(r.by.nel.detail, /script monitor is switched on/, name);
    });
  }
  const spellings = {
    'a report-to value that does not parse is judged by the addresses in its text': { 'report-to': `not json, but ${MONITOR_URL}` },
    'a report-to that is a JSON array': { 'report-to': `[{"group":"g","endpoints":[{"url":"${MONITOR_URL}"}]}]` },
    'two groups in one value, the monitor second': { 'report-to': `{"group":"mine","endpoints":[{"url":"https://reports.example.invalid/r"}]}, {"group":"x","endpoints":[{"url":"${MONITOR_URL}"}]}` },
    'a group named something else, reporting to Cloudflare\'s host': { 'report-to': `{"group":"whatever","endpoints":[{"url":"${MONITOR_URL}"}]}` },
    'a sub-host in a report-to group': { 'report-to': '{"group":"g","endpoints":[{"url":"https://a.csp-reporting.cloudflare.com/r"}]}' },
    'a sub-host in a report-only policy': { 'content-security-policy-report-only': "default-src 'self'; report-uri https://a.csp-reporting.cloudflare.com/r" },
    'an upper-case address in a policy': { 'content-security-policy-report-only': "default-src 'self'; report-uri HTTPS://CSP-REPORTING.CLOUDFLARE.COM/R" },
    'a trailing dot on the host': { 'reporting-endpoints': 'g="https://csp-reporting.cloudflare.com./r"' },
    'a port': { 'reporting-endpoints': 'g="https://csp-reporting.cloudflare.com:443/r"' },
  };
  for (const [what, headers] of Object.entries(spellings)) {
    await withSite(homeWith(headers), async (s) => {
      const r = await check(s.origin);
      assert.equal(r.by.nel.state, 'look', what);
      assert.match(r.by.nel.detail, /script monitor is switched on/, what);
    });
  }
});

test('a group or an address of your own is not the script monitor, whatever it is called or quotes', async () => {
  const own = { 'report-to': '{"group":"my-csp-endpoint","max_age":86400,"endpoints":[{"url":"https://reports.example.invalid/csp"}]}' };
  await withSite(homeWith({ ...own, 'content-security-policy-report-only': "default-src 'self'; report-uri https://reports.example.invalid/csp" }), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.nel.state, 'look');
    assert.doesNotMatch(r.by.nel.detail, /script monitor/, 'yours is yours');
    assert.match(r.by.nel.detail, /its own reporting groups/);
  });
  // Cloudflare's group name on an address that is not Cloudflare's: it reports to you, not there.
  await withSite(homeWith({ 'report-to': '{"group":"cf-csp-endpoint","max_age":86400,"endpoints":[{"url":"https://reports.example.invalid/csp"}]}' }), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.nel.state, 'look');
    assert.doesNotMatch(r.by.nel.detail, /script monitor/, 'a group named like Cloudflare\'s is yours when it reports elsewhere');
  });
  for (const url of LOOKALIKES) {
    await withSite(homeWith({ 'report-to': `{"group":"g","max_age":86400,"endpoints":[{"url":"${url}"}]}` }), async (s) => {
      const r = await check(s.origin);
      assert.equal(r.by.nel.state, 'look', url);
      assert.doesNotMatch(r.by.nel.detail, /script monitor/, `report-to: ${url}`);
    });
    for (const [header, value] of [['Reporting-Endpoints', `g="${url}"`], ['Content-Security-Policy-Report-Only', `default-src 'self'; report-uri ${url}`]]) {
      await withSite(homeWith({ [header]: value }), async (s) => {
        const r = await check(s.origin);
        assert.equal(r.by.nel.state, 'ok', `${header}: ${url}`);
      });
    }
  }
  // the host quoted as a NAME, outside any address
  await withSite(homeWith({ 'Reporting-Endpoints': 'csp-reporting.cloudflare.com="https://reports.example.invalid/r"' }), async (s) => {
    assert.equal((await check(s.origin)).by.nel.state, 'ok', 'a name that reads like the host is not an address');
  });
});

test('NEL on still fails beside the script monitor, and the monitor is named there too', async () => {
  await withSite(homeWith({ ...MONITOR, nel: '{"report_to":"cf-nel","max_age":604800}' }), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.nel.state, 'fail');
    assert.equal(r.code, 1);
    assert.match(r.by.nel.detail, /script monitor is switched on as well/);
  });
  const withNelGroup = { ...MONITOR, 'Report-To': `${MONITOR['Report-To']}, {"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4"}]}` };
  await withSite(homeWith(withNelGroup), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.nel.state, 'fail', 'Cloudflare\'s NEL group beside the monitor\'s is still a failure');
    assert.match(r.by.nel.detail, /script monitor is switched on as well/);
  });
  await withSite(homeWith({ ...MONITOR, nel: '{"max_age":0}' }), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.nel.state, 'look');
    assert.match(r.by.nel.detail, /max_age 0/, 'the withdrawal is still said');
    assert.match(r.by.nel.detail, /script monitor is switched on as well/, 'and the monitor is not hidden behind it');
  });
});

test('a clean NEL line says that one answer cannot show the script monitor is off', () =>
  withSite(homeWith({}), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.nel.state, 'ok');
    assert.match(r.by.nel.detail, /sample of pages only/);
  }));

test('a robots.txt or build.txt larger than what is read is not judged whole', async () => {
  const huge = (type) => (req, res, url) => {
    if (url.pathname === '/robots.txt' || url.pathname === '/build.txt') {
      send(res, 200, type, `User-agent: *\nDisallow: /\n${'# padding\n'.repeat(600_000)}`);
      return true;
    }
    return false;
  };
  await withSite(huge('text/plain'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.robots.state, 'look', 'the blanket Disallow in the first bytes is not a verdict on a partial file');
    assert.match(r.by.robots.detail, /larger than 5 MB/);
    assert.equal(r.by.build.state, 'look');
  });
});

test('a 200 page with nothing in it is not the site: the domain fails and the page items are not run', () =>
  withSite(homeWith({}, '', 'text/html'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.domain.state, 'fail');
    assert.match(r.by.domain.detail, /nothing in it/);
    for (const id of ['bot', 'analytics', 'email', 'scripts']) assert.equal(r.by[id].state, 'skip', id);
    assert.equal(r.code, 1);
  }));

// ---- what the fixes of round 2 must not break

test('every spelling of "all of it" in a robots group is a stay-out; allowing it too leaves it open', async () => {
  const cases = [
    ['User-agent: *\nDisallow: /*\n', 'fail'],
    ['User-agent: *\nDisallow: *\n', 'fail'],
    ['User-agent: *\nDisallow: /\nAllow: /\n', 'ok'],
    ['User-agent: *\nDisallow:\n', 'ok'],
  ];
  for (const [body, state] of cases) {
    await withSite((req, res, url) => {
      if (url.pathname === '/robots.txt') {
        send(res, 200, 'text/plain', `${body}Sitemap: https://${req.headers.host}/sitemap.xml\n`);
        return true;
      }
      return false;
    }, async (s) => {
      assert.equal((await check(s.origin)).by.robots.state, state, JSON.stringify(body));
    });
  }
});

test('each of the address-hiding markers is found alone, and the words are not one', async () => {
  const alone = [
    '<script src="/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js"></script>',
    '<a href="/cdn-cgi/l/email-protection#ab12">contact</a>',
    '<span class="__cf_email__" data-cfemail="ab12">x</span>',
  ];
  for (const html of alone) {
    await withSite(homeWith({}, html), async (s) => {
      assert.equal((await check(s.origin)).by.email.state, 'fail', html);
    });
  }
  await withSite(homeWith({}, '<p>Cloudflare shows a hidden address as [email&#160;protected] on the page.</p>'), async (s) => {
    assert.equal((await check(s.origin)).by.email.state, 'ok');
  });
});

test('each of Cloudflare\'s cookie names fails; a cookie of your own is a look', async () => {
  for (const name of ['__cf_bm', 'cf_clearance', '__cflb', '_cfuvid']) {
    await withSite(homeWith({ 'set-cookie': `${name}=abc; path=/` }), async (s) => {
      assert.equal((await check(s.origin)).by.bot.state, 'fail', name);
    });
  }
  await withSite(homeWith({ 'set-cookie': ['theme=dark; path=/', 'lang=en; path=/'] }), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.bot.state, 'look');
    assert.match(r.by.bot.detail, /theme, lang/);
  });
});

test('up to three redirects on the same address are followed; a fourth, or none to go to, is said so', async () => {
  const chain = (hops) => (req, res, url) => {
    const m = /^\/h(\d+)\/$/.exec(url.pathname);
    if (isHome(url)) { res.writeHead(301, { location: '/h1/' }); res.end(); return true; }
    if (m) {
      const n = Number(m[1]);
      if (n < hops) { res.writeHead(302, { location: `/h${n + 1}/` }); res.end(); return true; }
      send(res, 200, 'text/html', '<p>The end of the chain</p>');
      return true;
    }
    return false;
  };
  await withSite(chain(3), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.domain.state, 'look');
    assert.deepEqual(r.parsed.couldNotJudge, [], 'three hops after the first is the limit and the page is judged');
    assert.equal(r.by.nel.state, 'ok');
  });
  await withSite(chain(4), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.domain.state, 'look');
    assert.match(r.by.domain.detail, /redirected 4 times on this address and was still redirecting/);
    assert.equal(r.by.bot.state, 'skip');
    assert.equal(r.code, 1);
  });
  let asked = 0;
  await withSite((req, res, url) => {
    if (isHome(url) && /croftweaver-cloudflare-check\/1\)$/.test(req.headers['user-agent'])) {
      asked += 1;
      res.writeHead(302); // no Location header at all
      res.end();
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.match(r.by.domain.detail, /no Location header/);
    assert.equal(asked, 1, 'a redirect to nowhere is asked once, not three times');
  });
});

test('Content-Signal lines in robots.txt are Cloudflare\'s managed file at work: a look for the AI item', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/robots.txt') {
      send(res, 200, 'text/plain', `User-agent: *\nContent-Signal: search=yes, ai-train=no\nAllow: /\n\nSitemap: https://${req.headers.host}/sitemap.xml\n`);
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.robots.state, 'ok');
    assert.equal(r.by.ai.state, 'look');
    assert.match(r.by.ai.detail, /content-signal/);
  }));

test('a silent crawler is named in the list of requests that got no answer', () =>
  withSite((req, res, url) => {
    if (isHome(url) && /GPTBot/.test(req.headers['user-agent'])) { req.socket.destroy(); return true; }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.deepEqual(r.parsed.unanswered.map((u) => u.split(' ')[0]), ['GPTBot']);
  }));

// ---- what the fixes of round 3 must not break

test('a ">" inside an attribute value does not end the tag: what follows it is still read', () =>
  withSite(homeWith({}, '<p title="a > b" data-cfemail="abc">Hi</p><img src="/cdn-cgi/image/width=1/x.png">'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.email.state, 'fail');
    assert.equal(r.by.scripts.state, 'look');
  }));

test('an attribute\'s value is not an attribute: a title that names data-cfemail or data-cf-beacon is not one', () =>
  withSite(homeWith({}, '<p title="Explains data-cfemail here">Hi</p><img src="/a.png" alt="Explains data-cf-beacon here">'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.email.state, 'ok');
    assert.equal(r.by.analytics.state, 'ok');
  }));

test('headers are read one answer at a time: two withdrawn policies, and two HSTS values, are not corrupted by joining', async () => {
  const twoHops = (first, last) => (req, res, url) => {
    if (isHome(url)) { res.writeHead(301, { location: '/en/', ...first }); res.end(); return true; }
    if (url.pathname === '/en/') { send(res, 200, 'text/html', '<p>Page</p>', last); return true; }
    return false;
  };
  await withSite(twoHops({ nel: '{"max_age":0}' }, { nel: '{"max_age":0}' }), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.nel.state, 'look', 'two withdrawals are two withdrawals, not an unreadable header');
  });
  await withSite(twoHops({ 'strict-transport-security': 'max-age=15552000' }, { 'strict-transport-security': 'max-age=31536000; includeSubDomains' }), async (s) => {
    const r = await check(s.origin, '--hsts-on');
    assert.match(r.by.hsts.detail, /max-age 31536000 \(about 12 months\), subdomains on/);
    assert.notEqual(r.by.hsts.state, 'fail');
  });
});

test('a path that only starts like one of Cloudflare\'s three is another path', () =>
  withSite(homeWith({}, '<img src="/cdn-cgi/l/email-protection-custom.png"><script src="/cdn-cgi/scripts/x/cloudflare-static/email-decode.min.js.backup"></script>'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.email.state, 'ok');
    assert.equal(r.by.scripts.state, 'look');
    assert.match(r.by.scripts.detail, /email-protection-custom\.png/);
    assert.match(r.by.scripts.detail, /email-decode\.min\.js\.backup/);
  }));

test('the longer pattern wins in a robots group: "Disallow: /*" beats "Allow: /", and "Allow: /*" beats "Disallow: /"', async () => {
  const cases = [
    ['User-agent: *\nDisallow: /*\nAllow: /\n', 'fail'],
    ['User-agent: *\nDisallow: /\nAllow: /*\n', 'ok'],
    ['User-agent: *\nDisallow: /\nAllow: /\n', 'ok'],
  ];
  for (const [body, state] of cases) {
    await withSite((req, res, url) => {
      if (url.pathname === '/robots.txt') {
        send(res, 200, 'text/plain', `${body}Sitemap: https://${req.headers.host}/sitemap.xml\n`);
        return true;
      }
      return false;
    }, async (s) => {
      assert.equal((await check(s.origin)).by.robots.state, state, JSON.stringify(body));
    });
  }
});

test('a first-party file or a note in a script that happens to contain the word is not Cloudflare\'s', () =>
  withSite(homeWith({}, '<img src="/img/email-decode.png"><script>// we removed cloudflareinsights last year\nvar x = 1;</script>'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.email.state, 'ok');
    assert.equal(r.by.analytics.state, 'ok');
    assert.equal(r.by.scripts.state, 'ok');
  }));

test('Cloudflare\'s beacon is found by its address, written with or without a scheme', async () => {
  for (const src of ['https://static.cloudflareinsights.com/beacon.min.js', '//static.cloudflareinsights.com/beacon.min.js']) {
    await withSite(homeWith({}, `<script defer src="${src}"></script>`), async (s) => {
      assert.equal((await check(s.origin)).by.analytics.state, 'fail', src);
    });
  }
});

test('a redirect to the page itself is asked once and said so; a Location that is not an address is said so', async () => {
  let asked = 0;
  await withSite((req, res, url) => {
    if (isHome(url) && /croftweaver-cloudflare-check\/1\)$/.test(req.headers['user-agent'])) {
      asked += 1;
      res.writeHead(301, { location: '/' });
      res.end();
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.match(r.by.domain.detail, /redirected once on this address and was still redirecting/);
    assert.equal(asked, 1, 'the page itself is not asked for again');
  });
  await withSite((req, res, url) => {
    if (isHome(url)) { res.writeHead(302, { location: 'http://[::1' }); res.end(); return true; }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.match(r.by.domain.detail, /Location that is not an address/);
    assert.doesNotMatch(r.by.domain.detail, /run the check on it/);
  });
});

// ---- what the fixes of round 4 must not break

test('HSTS on a redirect before the page does not stand for the page: with --hsts-on it fails, and says so', async () => {
  const handler = (req, res, url) => {
    if (isHome(url)) { res.writeHead(301, { location: '/en/', 'strict-transport-security': 'max-age=15552000' }); res.end(); return true; }
    if (url.pathname === '/en/') { send(res, 200, 'text/html', '<p>Page</p>'); return true; }
    return false;
  };
  await withSite(handler, async (s) => {
    const r = await check(s.origin, '--hsts-on');
    assert.equal(r.by.hsts.state, 'fail');
    assert.match(r.by.hsts.detail, /only the redirect before it carried one/);
  });
  await withSite(handler, async (s) => {
    assert.equal((await check(s.origin)).by.hsts.state, 'look');
  });
});

test('an address written in a script between backticks, with a semicolon after it, is read whole', () =>
  withSite(homeWith({}, '<script>var s=document.createElement("script");s.src=`/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js`;document.head.append(s);</script>'), async (s) => {
    assert.equal((await check(s.origin)).by.email.state, 'fail');
  }));

test('a robots.txt with two hundred thousand blanket rules is read, not a crash', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/robots.txt') {
      send(res, 200, 'text/plain', `User-agent: *\n${'Disallow: /*\n'.repeat(200_000)}Sitemap: https://${req.headers.host}/sitemap.xml\n`);
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.ok(r.parsed, `the report was lost: ${r.stderr.slice(0, 200)}`);
    assert.equal(r.by.robots.state, 'fail', 'two hundred thousand ways of saying "stay out" say it');
  }));

test('what the HTML says it is: the text of a textarea or a title is text, a reference is decoded, "</scripture>" does not end a script', async () => {
  await withSite(homeWith({}, '<textarea><script src="/cdn-cgi/scripts/x/cloudflare-static/email-decode.min.js"></script></textarea><title><img src="/cdn-cgi/image/w=1/a.png"></title>'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.email.state, 'ok', 'markup inside a textarea is not a script');
    assert.equal(r.by.scripts.state, 'ok');
  });
  await withSite(homeWith({}, '<script defer src="https://static.&#99;loudflareinsights.com/beacon.min.js"></script>'), async (s) => {
    assert.equal((await check(s.origin)).by.analytics.state, 'fail', 'an address written with a character reference');
  });
  await withSite(homeWith({}, '<script>var a="</scripture>"; var b=document.createElement("script"); b.src="/cdn-cgi/challenge-platform/scripts/jsd/main.js";</script>'), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'fail', 'the script goes on past "</scripture>"');
  });
});

test('what is not a tag is skipped, and a comment that ends abruptly does not swallow the page', async () => {
  await withSite(homeWith({}, '<![CDATA[<script src="/cdn-cgi/zaraz/i.js"></script>]]><?xml-note <img src="/cdn-cgi/image/a.png"> ?><p>Hi</p>'), async (s) => {
    assert.equal((await check(s.origin)).by.scripts.state, 'ok');
  });
  for (const closer of ['<!-->', '<!--->', '<!-- a --!>']) {
    await withSite(homeWith({}, `${closer}<script src="/cdn-cgi/zaraz/i.js"></script>`), async (s) => {
      assert.equal((await check(s.origin)).by.scripts.state, 'look', closer);
    });
  }
});

test('an address is read against the page it is on, and a link to the beacon is not the beacon', async () => {
  await withSite((req, res, url) => {
    if (isHome(url)) { res.writeHead(301, { location: '/blog/' }); res.end(); return true; }
    if (url.pathname === '/blog/') { send(res, 200, 'text/html', '<img src="cdn-cgi/image/a.png"><a href="https://static.cloudflareinsights.com/beacon.min.js">the beacon</a>'); return true; }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.scripts.state, 'ok', 'cdn-cgi/image/a.png on /blog/ is /blog/cdn-cgi/image/a.png');
    assert.equal(r.by.analytics.state, 'ok', 'a link in the text is not a script');
  });
});

test('an empty Location header is said to be empty', () =>
  withSite((req, res, url) => {
    if (isHome(url)) { res.writeHead(301, { location: '' }); res.end(); return true; }
    return false;
  }, async (s) => {
    assert.match((await check(s.origin)).by.domain.detail, /an empty Location header/);
  }));

// ---- what the fixes of round 5 must not break

test('text that changes length when lower-cased does not move what is found after it', () =>
  withSite(homeWith({}, `${'İstanbul '.repeat(12)}<textarea>x</textarea><script src="https://static.cloudflareinsights.com/beacon.min.js"></script>`), async (s) => {
    assert.equal((await check(s.origin)).by.analytics.state, 'fail');
  }));

test('a page of a hundred thousand comments is read in linear time and what follows them is found', () =>
  withSite(homeWith({}, `${'<!--x-->'.repeat(100_000)}<script src="https://static.cloudflareinsights.com/beacon.min.js"></script>`), async (s) => {
    const started = Date.now();
    const r = await check(s.origin);
    assert.equal(r.by.analytics.state, 'fail');
    assert.ok(Date.now() - started < 20_000, 'a quadratic reader would take minutes');
  }));

test('an SVG\'s title holds markup, as in a browser; an HTML title holds text', async () => {
  const script = '<script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script>';
  await withSite(homeWith({}, `<svg><title>${script}</title></svg>`), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'fail');
  });
  await withSite(homeWith({}, `<head><title>${script}</title></head><svg></svg>`), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'ok');
  });
});

test('a named character reference needs its semicolon, as in a browser: "&semi=" in an address is left alone', () =>
  withSite(homeWith({}, '<img src="/cdn-cgi/image/a&semi=b.png"><img src="/cdn-cgi/image/c&semi;d.png">'), async (s) => {
    const r = await check(s.origin);
    assert.match(r.by.scripts.detail, /a&semi=b\.png/);
    assert.match(r.by.scripts.detail, /c;d\.png/);
  }));

// ---- what the fixes of round 6 must not break

test('foreign content is read as a browser reads it: a self-closed svg changes nothing, a foreignObject is HTML again, an svg\'s textarea holds markup', async () => {
  const script = '<script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script>';
  await withSite(homeWith({}, `<svg/><title>${script}</title>`), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'ok', 'after <svg/> a title is HTML text');
  });
  await withSite(homeWith({}, `<svg><foreignObject><title>${script}</title></foreignObject></svg>`), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'ok', 'a foreignObject holds HTML');
  });
  await withSite(homeWith({}, `<svg><foreignObject></foreignObject><title>${script}</title></svg>`), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'fail', 'after the foreignObject it is svg again');
  });
  await withSite(homeWith({}, `<svg><textarea>${script}</textarea></svg>`), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'fail', 'in svg a textarea holds markup');
  });
});

// ---- what the confirmation of round 6 asked for

test('foreign content, edges: an svg\'s inline script is read, a slash inside a value is not a self-closing one, a nested foreignObject end does not end the outer', async () => {
  const jsd = 'var a=document.createElement("script");a.src="/cdn-cgi/challenge-platform/scripts/jsd/main.js";';
  await withSite(homeWith({}, `<svg><script>${jsd}</script></svg>`), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'fail', 'the text of an svg script is still script text');
  });
  const script = '<script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script>';
  await withSite(homeWith({}, `<svg id=x/><title>${script}</title></svg>`), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'fail', '"id=x/" does not close the svg: its title is still markup');
  });
  await withSite(homeWith({}, `<svg><foreignObject><foreignObject></foreignObject><title>${script}</title></foreignObject></svg>`), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'ok', 'the inner end tag does not leave the outer foreignObject');
  });
});

// ---- what the second confirmation of round 6 asked for

test('thousands of unclosed script starts inside an svg: the text taken is bounded by the page, and it is script text', async () => {
  const jsd = 'var a="/cdn-cgi/challenge-platform/scripts/jsd/main.js";';
  const page = `<svg>${'<script>'.repeat(40_000)}${jsd}`;
  const { scripts } = readHtml(page);
  // The first <script> takes the rest of the page, once: one piece, and exactly what follows its start tag.
  assert.equal(scripts.length, 1);
  assert.equal(scripts[0].length, page.length - '<svg><script>'.length);
  await withSite(homeWith({}, page), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'fail');
  });
});

test('an svg script is script text to its end tag: a CDATA section, a nested svg and a foreignObject inside it are part of it', async () => {
  const p = '/cdn-cgi/challenge-platform/scripts/jsd/main.js';
  const cases = [
    `<svg><script><![CDATA[var a="${p}";]]></script></svg>`,
    `<svg><script>var a=1;<foreignObject><svg></svg></foreignObject>var b="${p}";</script></svg>`,
    `<svg><svg><script>var b="${p}";</script></svg><text>x</text></svg>`,
  ];
  for (const html of cases) {
    await withSite(homeWith({}, html), async (s) => {
      assert.equal((await check(s.origin)).by.bot.state, 'fail', html);
    });
  }
  // the words after a closed svg script, in the svg's other elements, are not script text
  await withSite(homeWith({}, `<svg><svg><script>safe</svg><script>safe</script><text>${p}</text></svg>`), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'ok');
  });
  // a self-closed svg script has no text: what follows it is markup
  await withSite(homeWith({}, `<svg><script href="/x.js"/><text>${p}</text></svg>`), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'ok');
  });
});

test('a self-closing slash on script or title does not stop raw text in HTML, as in a browser', async () => {
  const jsd = '/cdn-cgi/challenge-platform/scripts/jsd/main.js';
  await withSite(homeWith({}, `<script/>var a=document.createElement("script");a.src="${jsd}";</script>`), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'fail', '<script/> still opens a script in HTML');
  });
  await withSite(homeWith({}, `<title/><script src="${jsd}"></script></title>`), async (s) => {
    assert.equal((await check(s.origin)).by.bot.state, 'ok', '<title/> still opens a title in HTML');
  });
});

// ---- the command itself

test('a wrong command is exit 2 with the usage text, and --help is exit 0', async () => {
  for (const args of [[], ['a.example', 'b.example'], ['a.example', '--nope'], ['a.example/about'], ['a.example', '--build', 'xyz'], ['a.example', '--timeout', '0'], ['a.example', '--project', 'no good!'], ['http://shop.example.com'], ['a.example', '--project', 'https://worker.example']]) {
    const r = await run(args);
    assert.equal(r.code, 2, JSON.stringify(args));
    assert.match(r.stderr, /Usage: node cloudflare-check\.mjs/);
    assert.equal(r.stdout, '');
  }
  const help = await run(['--help']);
  assert.equal(help.code, 0);
  assert.match(help.stdout, /Usage: node cloudflare-check\.mjs/);
});

test('a fractional timeout is accepted, and a server that never answers fails within it', () =>
  withSite((req, res, url) => (isHome(url) ? true : false), async (s) => {
    const started = Date.now();
    // 1.0001 seconds is 1000.1 milliseconds: not a whole number of them.
    const r = await check(s.origin, '--timeout', '1.0001');
    assert.equal(r.code, 1, r.stderr);
    assert.equal(r.by.domain.state, 'fail');
    assert.match(r.by.domain.detail, /no answer within 1 second\b/);
    assert.ok(Date.now() - started < 10_000);
  }));

test('it runs when started through a symlink, as an installed skill is, also with symlinks kept', async (t) => {
  const dir = mkdtempSync(path.join(tmpdir(), 'cfcheck-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const link = path.join(dir, 'cloudflare-check.mjs');
  try {
    symlinkSync(SCRIPT, link);
  } catch (e) {
    if (e.code === 'EPERM') { t.skip('this machine does not let a plain user make symlinks'); return; }
    throw e;
  }
  const plain = await run(['--help'], { script: link });
  assert.equal(plain.code, 0);
  assert.match(plain.stdout, /Usage: node cloudflare-check\.mjs/, 'a script that does nothing when linked would print nothing');
  const kept = await run(['--help'], { script: link, nodeArgs: ['--preserve-symlinks', '--preserve-symlinks-main'] });
  assert.match(kept.stdout, /Usage: node cloudflare-check\.mjs/);
});

test('parseTarget takes a domain or a local page and refuses a path or a live http:// address', () => {
  assert.deepEqual(parseTarget('Example.com'), {
    host: 'example.com', origin: 'https://example.com',
    httpProbe: 'http://example.com/', httpsOrigin: 'https://example.com',
  });
  assert.equal(parseTarget('http://127.0.0.1:4321').httpsOrigin, 'https://127.0.0.1:4321');
  assert.equal(parseTarget('http://site.localhost:4321').host, 'site.localhost:4321');
  assert.equal(parseTarget('https://www.example.com:8443').httpProbe, 'http://www.example.com/');
  for (const bad of ['example.com/about', 'https://example.com/?q=1', 'ftp://example.com', 'user@example.com', 'http://example.com', 'http://shop.example.org:8080']) {
    assert.throws(() => parseTarget(bad), UsageError, bad);
  }
});

// ---- the script and the checklist say the same things

test('the items are the checklist\'s items, and the paths are its paths', (t) => {
  if (!existsSync(CHECKLIST)) {
    // A copy of the skill outside the toolkit has no docs folder. In the toolkit repo it is
    // there, and CI runs this file there, so the comparison is made where it counts.
    t.skip('docs/CLOUDFLARE-CHECKLIST.md is not next to this skill');
    return;
  }
  const text = readFileSync(CHECKLIST, 'utf8');
  const flat = text.replace(/\*\*|`/g, '').replace(/\s+/g, ' ');
  // The bold lead of each "- [ ] **...**" line, in sections 1 to 4.
  const found = [...text.matchAll(/^- \[ \] \*\*(.+?)\*\*/gm)].map((m) => m[1].replace(/[.:]$/, ''));
  const mine = ITEMS.filter((i) => i.section <= 4).map((i) => i.title);
  assert.deepEqual(mine, found, 'the script lists the checklist\'s items, in its order');
  for (const item of ITEMS.filter((i) => i.path)) {
    const want = item.path.replace(/`/g, '').replace(/\s+/g, ' ');
    assert.ok(flat.includes(want), `the checklist does not say "${want}"`);
  }
  assert.ok(text.includes('**No scripts you didn\'t add:**'), 'section 5 still has the source-search bullet the "scripts" item stands for');
});
