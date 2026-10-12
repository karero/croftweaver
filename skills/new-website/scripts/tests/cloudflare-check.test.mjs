// Tests for cloudflare-check.mjs. Standard library only; run with
//   node --test skills/new-website/scripts/tests/cloudflare-check.test.mjs
//
// Every test that judges a site starts a small web server on 127.0.0.1 and runs the script as
// a program against it, the way a person or an assistant does: real requests, real exit
// status, real output. The server plays a site behind Cloudflare, and the script is given its
// address as an origin ("http://127.0.0.1:PORT").
import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { execFile } from 'node:child_process';
import { readFileSync, mkdtempSync, symlinkSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ITEMS, parseTarget, UsageError } from '../cloudflare-check.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = path.join(HERE, '..', 'cloudflare-check.mjs');
const CHECKLIST = path.join(HERE, '..', '..', '..', '..', 'docs', 'CLOUDFLARE-CHECKLIST.md');
const SHA = '85ca07f1bb53b7078587bce136ef95288fe5115a';

// ---- a site to ask, and the script to ask it

function send(res, status, type, body, extra = {}) {
  res.writeHead(status, { 'content-type': type, ...extra });
  res.end(body);
}

// A clean site: nothing Cloudflare adds. `tweak(req, res, url)` may answer first (return true).
async function site(tweak = () => false) {
  const server = http.createServer((req, res) => {
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
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const { port } = server.address();
  return {
    port,
    host: `127.0.0.1:${port}`,
    origin: `http://127.0.0.1:${port}`,
    close: () => { server.closeAllConnections(); return new Promise((r) => server.close(r)); },
  };
}

function run(args, script = SCRIPT) {
  return new Promise((resolve) => {
    execFile(process.execPath, [script, ...args], { timeout: 60_000 }, (err, stdout, stderr) => {
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

// ---- a site that is right

test('a clean site passes every check that can be made from outside, and says what is by hand', () =>
  withSite(undefined, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.code, 0, r.stdout);
    for (const id of ['domain', 'https', 'nel', 'bot', 'analytics', 'email', 'ai', 'robots', 'build']) {
      assert.equal(r.by[id].state, 'ok', `${id}: ${r.by[id].detail}`);
    }
    for (const id of ['build-settings', 'fail-open', 'tls', 'hints']) assert.equal(r.by[id].state, 'hand', id);
    assert.equal(r.by.hsts.state, 'look', 'HSTS is not on yet, which is not a failure');
    assert.equal(r.by.pages.state, 'skip');
    assert.equal(r.by.canonical.state, 'skip');
    assert.deepEqual(r.parsed.results.map((x) => x.id), ITEMS.map((i) => i.id), 'every item, in the checklist\'s order');
  }));

test('the plain-text report names every item and ends with a result line', () =>
  withSite(undefined, async (s) => {
    const r = await run([s.origin, '--timeout', '5']);
    assert.equal(r.code, 0);
    for (const item of ITEMS) assert.ok(r.stdout.includes(item.title.replace(/`/g, '')), `missing: ${item.title}`);
    assert.match(r.stdout, /Result: \d+ ok, 0 FAIL, \d+ look, 4 by hand, 2 not run\./);
    assert.match(r.stdout, /Nothing was changed\./);
  }));

// ---- Network Error Logging

test('NEL still on: the item fails and shows how long browsers keep the note', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/' && url.searchParams.has('cb')) {
      send(res, 200, 'text/html', '<p>Hi</p>', {
        nel: '{"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}',
        'report-to': '{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4"}]}',
      });
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.code, 1);
    assert.equal(r.by.nel.state, 'fail');
    assert.match(r.by.nel.detail, /max_age 604800/);
    assert.equal(r.by.https.state, 'ok', 'a failing item does not spoil the others');
  }));

test('a report-to header alone is a "look", not a pass and not a failure', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/' && url.searchParams.has('cb')) {
      send(res, 200, 'text/html', '<p>Hi</p>', { 'report-to': '{"group":"mine"}' });
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.nel.state, 'look');
    assert.equal(r.code, 0);
  }));

// ---- an empty answer is never a pass

test('no answer at all: the domain fails and nothing that needs the page reads "ok"', async () => {
  const s = await site();
  await s.close(); // the port is now closed
  const r = await check(s.origin);
  assert.equal(r.code, 1);
  assert.equal(r.by.domain.state, 'fail');
  assert.equal(r.by.https.state, 'fail');
  for (const id of ['hsts', 'nel', 'bot', 'analytics', 'email', 'ai', 'robots', 'build']) {
    assert.equal(r.by[id].state, 'skip', `${id} must not pass on a dead request`);
  }
  assert.match(r.by.domain.detail, /connection was refused/);
});

test('an error page is not judged as the site: a 522 fails the domain and the privacy items are not run', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/' && url.searchParams.has('cb')) {
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
  }));

test('a challenge page is named as such, and the site is not judged from it', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/' && url.searchParams.has('cb')) {
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

// ---- http:// goes to https://

test('the https redirect must start with the whole address: a longer host is not it', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/' && !url.searchParams.has('cb')) {
      // the same prefix, one digit longer: the ".com.au" slip, on a port
      res.writeHead(301, { location: `https://${req.headers.host}9/` });
      res.end();
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.https.state, 'fail');
    assert.match(r.by.https.detail, /not to https:\/\//);
  }));

test('http:// answering 200 is a failure: Always Use HTTPS is not reaching it', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/' && !url.searchParams.has('cb')) {
      send(res, 200, 'text/html', '<p>Hi</p>');
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.https.state, 'fail');
    assert.match(r.by.https.detail, /no redirect/);
  }));

test('a 302 to the right place is a "look": visitors arrive, but it is not Always Use HTTPS', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/' && !url.searchParams.has('cb')) {
      res.writeHead(302, { location: `https://${req.headers.host}/` });
      res.end();
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.https.state, 'look');
  }));

// ---- what Cloudflare adds to the page

test('scripts and cookies Cloudflare adds are found, one item each', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/' && url.searchParams.has('cb')) {
      send(res, 200, 'text/html; charset=utf-8', `<!doctype html><html><body>
        <a href="/cdn-cgi/l/email-protection#ab">[email&#160;protected]</a>
        <script src="/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js"></script>
        <script defer src="https://static.cloudflareinsights.com/beacon.min.js"></script>
        <script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script>
      </body></html>`, { 'set-cookie': '__cf_bm=abc; path=/; HttpOnly' });
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.code, 1);
    assert.equal(r.by.bot.state, 'fail');
    assert.match(r.by.bot.detail, /__cf_bm/);
    assert.equal(r.by.analytics.state, 'fail');
    assert.equal(r.by.email.state, 'fail');
  }));

test('the bot script alone is found when no cookie was set', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/' && url.searchParams.has('cb')) {
      send(res, 200, 'text/html', '<script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script>');
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.bot.state, 'fail');
    assert.match(r.by.bot.detail, /challenge-platform/);
    assert.equal(r.by.analytics.state, 'ok');
  }));

test('a redirecting home page is not scanned: the source items are "not run", never "ok"', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/' && url.searchParams.has('cb')) {
      // Cloudflare's own redirect pages carry a small HTML body: it must not read as the site.
      res.writeHead(302, { location: '/en/', 'content-type': 'text/html', nel: '{"max_age":604800}' });
      res.end('<html><head><title>302 Found</title></head><body><center><h1>302 Found</h1></center><hr><center>cloudflare</center></body></html>');
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.domain.state, 'look');
    for (const id of ['bot', 'analytics', 'email']) assert.equal(r.by[id].state, 'skip', id);
    assert.equal(r.by.nel.state, 'fail', 'headers of a redirect still count');
  }));

// ---- HSTS

test('HSTS: missing is a "look" until --hsts-on says it should be there', () =>
  withSite(undefined, async (s) => {
    assert.equal((await check(s.origin)).by.hsts.state, 'look');
    const r = await check(s.origin, '--hsts-on');
    assert.equal(r.by.hsts.state, 'fail');
    assert.equal(r.code, 1);
  }));

test('HSTS: a six-month header is read in months; preload is a "look"', async () => {
  const withHeader = (value) => (req, res, url) => {
    if (url.pathname === '/' && url.searchParams.has('cb')) {
      send(res, 200, 'text/html', '<p>Hi</p>', { 'strict-transport-security': value });
      return true;
    }
    return false;
  };
  await withSite(withHeader('max-age=15552000; includeSubDomains'), async (s) => {
    const r = await check(s.origin, '--hsts-on');
    assert.equal(r.by.hsts.state, 'ok');
    assert.match(r.by.hsts.detail, /\(about 6 months\), subdomains on, preload off/);
  });
  await withSite(withHeader('max-age=31536000; includeSubDomains; preload'), async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.hsts.state, 'look');
    assert.match(r.by.hsts.detail, /preload/);
  });
});

// ---- robots.txt and AI crawlers

test('robots.txt that still names example.com is a failure', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/robots.txt') {
      send(res, 200, 'text/plain', 'User-agent: *\nAllow: /\n\n# Set to the real production domain before launch.\nSitemap: https://example.com/sitemap-index.xml\n');
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.robots.state, 'fail');
    assert.match(r.by.robots.detail, /example\.com/);
  }));

test('rules for named crawlers in robots.txt are a "look"', () =>
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

test('a robots.txt that is a web page is a failure, not a file', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/robots.txt') {
      send(res, 200, 'text/html', '<!doctype html><title>Home</title>');
      return true;
    }
    return false;
  }, async (s) => {
    const r = await check(s.origin);
    assert.equal(r.by.robots.state, 'fail');
  }));

test('an AI crawler name that is refused is a "look" that names it and its status', () =>
  withSite((req, res, url) => {
    if (url.pathname === '/' && url.searchParams.has('cb') && /ClaudeBot/.test(req.headers['user-agent'])) {
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

// ---- build.txt

test('--build: the same commit passes, another one fails, and "dev" is only a look', async () => {
  await withSite(undefined, async (s) => {
    const same = await check(s.origin, '--build', SHA.slice(0, 10));
    assert.equal(same.by.build.state, 'ok');
    assert.match(same.by.build.detail, /the one you expected/);
    const other = await check(s.origin, '--build', '1234567');
    assert.equal(other.by.build.state, 'fail');
    assert.equal(other.code, 1);
  });
  await withSite((req, res, url) => {
    if (url.pathname === '/build.txt') { send(res, 200, 'text/plain', 'dev\n'); return true; }
    return false;
  }, async (s) => {
    assert.equal((await check(s.origin)).by.build.state, 'look');
  });
  await withSite((req, res, url) => {
    if (url.pathname === '/build.txt') { send(res, 200, 'text/html', '<!doctype html><p>app</p>'); return true; }
    return false;
  }, async (s) => {
    assert.equal((await check(s.origin, '--build', SHA.slice(0, 7))).by.build.state, 'look', 'a page is not a build marker');
  });
});

// ---- the pages.dev address

test('--project: the alias that forwards to the domain passes, and keeps the NEL note out of the domain\'s result', async () => {
  await withSite(undefined, async (live) => {
    await withSite((req, res) => {
      res.writeHead(301, { location: `https://${live.host}/?cb=1`, nel: '{"max_age":604800}', 'report-to': '{"group":"cf-nel"}' });
      res.end();
      return true;
    }, async (alias) => {
      const r = await check(live.origin, '--project', alias.origin);
      assert.equal(r.by.pages.state, 'ok');
      assert.equal(r.by.canonical.state, 'ok');
      assert.equal(r.by.nel.state, 'ok');
      assert.match(r.by.nel.detail, /pages\.dev address still sends them/);
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

test('--project: a forward to another address fails, and a name that does not exist is named', async () => {
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
  });
});

// ---- the command itself

test('a wrong command is exit 2 with the usage text, and --help is exit 0', async () => {
  for (const args of [[], ['a.example', 'b.example'], ['a.example', '--nope'], ['a.example/about'], ['a.example', '--build', 'xyz'], ['a.example', '--timeout', '0'], ['a.example', '--project', 'no good!']]) {
    const r = await run(args);
    assert.equal(r.code, 2, JSON.stringify(args));
    assert.match(r.stderr, /Usage: node cloudflare-check\.mjs/);
    assert.equal(r.stdout, '');
  }
  const help = await run(['--help']);
  assert.equal(help.code, 0);
  assert.match(help.stdout, /Usage: node cloudflare-check\.mjs/);
});

test('it runs when started through a symlink, as an installed skill is', async () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'cfcheck-'));
  const link = path.join(dir, 'cloudflare-check.mjs');
  symlinkSync(SCRIPT, link);
  const r = await run(['--help'], link);
  assert.equal(r.code, 0);
  assert.match(r.stdout, /Usage: node cloudflare-check\.mjs/, 'a script that does nothing when linked would print nothing');
});

test('parseTarget takes a domain or an origin and refuses a path', () => {
  assert.deepEqual(parseTarget('Example.com'), {
    host: 'example.com', origin: 'https://example.com',
    httpProbe: 'http://example.com/', httpsPrefix: 'https://example.com/',
  });
  assert.equal(parseTarget('http://127.0.0.1:4321').httpsPrefix, 'https://127.0.0.1:4321/');
  assert.equal(parseTarget('https://www.example.com:8443').httpProbe, 'http://www.example.com/');
  for (const bad of ['example.com/about', 'https://example.com/?q=1', 'ftp://example.com', 'user@example.com']) {
    assert.throws(() => parseTarget(bad), UsageError, bad);
  }
});

// ---- the script and the checklist say the same things

test('the items are the checklist\'s items, and the paths are its paths', (t) => {
  if (!existsSync(CHECKLIST)) {
    // A site's bundled copy of the skill has no docs folder. In the toolkit repo it is there,
    // and CI runs this file there, so the comparison is made where it counts.
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
});
