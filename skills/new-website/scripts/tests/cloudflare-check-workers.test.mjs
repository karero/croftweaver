// Tests for the Workers items of cloudflare-check.mjs: --site, --config and --preview, the
// workers-dev and previews items, and a build.txt of more than one line. Standard library only; run with
//   node --test skills/new-website/scripts/tests/cloudflare-check-workers.test.mjs
//
// Each case runs the script as a program, the way a person or an assistant does, against two servers on
// 127.0.0.1: the domain (a site behind Cloudflare, as in cloudflare-check.test.mjs) and one that plays
// Cloudflare's workers.dev: it answers by Host, with the answers Cloudflare gave (fixtures/workers-dev-answers).
// The Worker's address and its links are names ending in .workers.dev.test, which a preloaded module
// (resolve-test-names.cjs) maps to this machine. The expected results are written by hand.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { execFile } from 'node:child_process';
import { readFileSync, writeFileSync, mkdtempSync, mkdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseJsonc, parsePreview, UsageError } from '../cloudflare-check.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = path.join(HERE, '..', 'cloudflare-check.mjs');
const PRELOAD = ['--require', path.join(HERE, 'resolve-test-names.cjs')];
const SHA = '85ca07f1bb53b7078587bce136ef95288fe5115a';
const CAP = JSON.parse(readFileSync(path.join(HERE, 'fixtures', 'workers-dev-answers', 'answers-2026-11-06.json'), 'utf8'));
const KIT_301 = JSON.parse(readFileSync(path.join(HERE, 'fixtures', 'pages-vs-worker-headers', 'redirect-old-page-2026-11-05.json'), 'utf8')).version_url_of_the_worker;

// Captures of a version link and a Preview alias (2026-11-13, curl 8.7.1): with the starter's NEL rule in
// _headers, and without it. `answerOf` takes the answer to one path from the first host that has it.
function answerOf(file, pathname) {
  const text = readFileSync(path.join(HERE, 'fixtures', 'l59-nel', file), 'utf8');
  const block = text.split(/^## /m).slice(1).find((b) => b.split('\n')[0].replace(/^https:\/\/[^/]+/, '') === pathname);
  const [, ...rest] = block.trimEnd().split('\n');
  const headers = {};
  for (const line of rest.slice(1)) headers[line.slice(0, line.indexOf(':'))] = line.slice(line.indexOf(':') + 2);
  return { status: Number(rest[0].split(' ')[1]), headers, body: '<!doctype html><title>Site</title>' };
}
const WITH_RULE = 'curl-8.7.1-version-and-alias-with-nel-rule-2026-11-13.txt';
const WITHOUT_RULE = 'curl-8.7.1-version-without-rule-2026-11-13.txt';
const RULE_HOME = answerOf(WITH_RULE, '/');
const RULE_REDIRECT = answerOf(WITH_RULE, '/a');
const NO_RULE_HOME = answerOf(WITHOUT_RULE, '/');
const STARTER_HEADERS = readFileSync(path.join(HERE, '..', '..', 'templates', 'astro', 'public', '_headers'), 'utf8');

const WORKER = 'lenas-site';
const ACCOUNT = 'example-sub.workers.dev.test';
const VERSION = '0a1b2c3d';
const ADDRESS_HOST = `${WORKER}.${ACCOUNT}`;
const VERSION_HOST = `${VERSION}-${WORKER}.${ACCOUNT}`;
const ALIAS_HOST = `preview-test-${WORKER}.${ACCOUNT}`;
const DEAD_HOST = `cfcheck-nope-${WORKER}.${ACCOUNT}`;

// ---- the domain, and Cloudflare's workers.dev

function send(res, status, type, body, extra = {}) {
  res.writeHead(status, { 'content-type': type, ...extra });
  res.end(body);
}

// A site that is right, behind Cloudflare; `buildTxt` is what /build.txt holds.
async function domain({ buildTxt = `${SHA}\n`, tweak = () => false } = {}) {
  const server = http.createServer((req, res) => {
    res.setHeader('server', 'cloudflare');
    res.setHeader('cf-ray', '8a1b2c3d4e5f6071-AMS');
    const url = new URL(req.url, `http://${req.headers.host}`);
    if (tweak(req, res, url)) return;
    if (url.pathname === '/robots.txt') send(res, 200, 'text/plain', `User-agent: *\nAllow: /\n\nSitemap: https://${req.headers.host}/sitemap-index.xml\n`);
    else if (url.pathname === '/build.txt') send(res, 200, 'text/plain', buildTxt);
    else if (url.pathname === '/' && !url.searchParams.has('cb')) { res.writeHead(301, { location: `https://${req.headers.host}/` }); res.end(); }
    else send(res, 200, 'text/html; charset=utf-8', '<!doctype html><title>Site</title><p>Hello</p>');
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const { port } = server.address();
  return { port, host: `127.0.0.1:${port}`, origin: `http://127.0.0.1:${port}`, close: () => { server.closeAllConnections(); return new Promise((r) => server.close(r)); } };
}

function answerWith(res, cap, extra = {}) {
  res.writeHead(cap.status, { ...cap.headers, ...extra });
  res.end(cap.body);
}

// Cloudflare's workers.dev as the captures show it: `rules(host, req, res)` may answer first (return true).
// Asked without accept-encoding, the Worker's address answers as an address that is off does; asked
// with one it answers a 404 page instead; a version link or an alias serves the site as it does with the
// starter's NEL rule (noindex, nel with max_age 0, no report-to); an alias that is not there answers 404
// with x-preview-user-error.
async function workersDev(rules = () => false) {
  const asked = [];
  const server = http.createServer((req, res) => {
    const host = (req.headers.host ?? '').split(':')[0];
    asked.push({ host, url: req.url, acceptEncoding: req.headers['accept-encoding'] });
    if (rules(host, req, res)) return;
    if (host === ADDRESS_HOST) answerWith(res, req.headers['accept-encoding'] === undefined ? CAP.address_off_no_accept_encoding : CAP.address_off_accept_encoding_identity);
    else if (host === VERSION_HOST || host === ALIAS_HOST) answerWith(res, RULE_HOME);
    else answerWith(res, CAP.preview_alias_dead);
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const { port } = server.address();
  const link = (host) => `http://${host}:${port}`;
  return { port, asked, link, close: () => { server.closeAllConnections(); return new Promise((r) => server.close(r)); } };
}

// ---- a site folder

const WORKERS_CONFIG = `{
  // the Worker
  "name": "${WORKER}",
  "compatibility_date": "2026-10-20",
  "workers_dev": false, /* the address is off */
  "preview_urls": true,
  "assets": { "directory": "./dist", },
}
`;
const PAGES_TOML = 'name = "lenas-pages"\npages_build_output_dir = "dist"\n';

function folder(t, files) {
  const dir = mkdtempSync(path.join(tmpdir(), 'cfcheck-site-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  for (const [name, text] of Object.entries(files)) {
    const file = path.join(dir, name);
    mkdirSync(path.dirname(file), { recursive: true });
    writeFileSync(file, text);
  }
  return dir;
}

function run(args) {
  return new Promise((resolve) => {
    execFile(process.execPath, [...PRELOAD, SCRIPT, ...args], { timeout: 60_000 }, (err, stdout, stderr) => resolve({ code: err ? err.code : 0, stdout, stderr }));
  });
}

async function check(origin, ...extra) {
  const r = await run([origin, '--json', '--timeout', '5', ...extra]);
  const parsed = r.stdout ? JSON.parse(r.stdout) : null;
  return { ...r, parsed, by: parsed ? Object.fromEntries(parsed.results.map((x) => [x.id, x])) : {} };
}

// The domain and the workers.dev stand-in, around one case.
async function withBoth(options, fn) {
  const live = await domain(options.domain);
  const wd = await workersDev(options.rules);
  try {
    return await fn(live, wd);
  } finally {
    await live.close();
    await wd.close();
  }
}

const sameStates = (by, ids, want) => ids.map((id) => `${id}=${by[id].state}`).join(' ') === want;

// ---- CW1: a Worker after its move

test('CW1: a Workers-only site with the address off and a live version link: both Workers items ok, the Pages items do not count', (t) =>
  withBoth({ domain: { buildTxt: `${SHA}\nplatform=worker\n` } }, async (live, wd) => {
    const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG, 'package.json': '{ "name": "not-the-worker", "assets": { "directory": "x" } }' });
    const r = await check(live.origin, '--site', dir, '--preview', wd.link(VERSION_HOST), '--build', SHA.slice(0, 9));
    assert.equal(r.code, 0, r.stdout);
    assert.equal(r.by['workers-dev'].state, 'ok', r.by['workers-dev'].detail);
    assert.equal(r.by.previews.state, 'ok', r.by.previews.detail);
    assert.match(r.by['workers-dev'].detail, /error code: 1042/);
    assert.equal(r.by.build.state, 'ok');
    assert.match(r.by.build.detail, /build\.txt also says platform=worker\./);
    for (const id of ['pages', 'canonical', 'build-settings']) {
      assert.equal(r.by[id].state, 'skip', id);
      assert.equal(r.by[id].detail, 'not run: a Workers site, with no Pages project.');
      assert.equal(r.by[id].blocked, undefined, `${id} must not count as a failure`);
    }
    assert.equal(r.by['fail-open'].state, 'hand');
    assert.deepEqual(r.parsed.couldNotJudge, []);
    assert.deepEqual(r.parsed.unanswered, []);
    assert.equal(r.parsed.site.platform, 'workers');
    assert.match(r.parsed.site.note, /wrangler\.jsonc is a Workers config for lenas-site\. Checked as a Workers site\./);
    // The address was asked without accept-encoding, the links with it.
    assert.deepEqual(wd.asked.filter((a) => a.host === ADDRESS_HOST).map((a) => a.acceptEncoding), [undefined]);
    assert.deepEqual(wd.asked.filter((a) => a.host === VERSION_HOST).map((a) => a.acceptEncoding), ['identity']);
  }));

test('CW1: a site with a Workers config and a Pages marker gets both sets of checks', (t) =>
  withBoth({}, async (live, wd) => {
    const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG, 'functions/_middleware.ts': 'export {};\n' });
    await withAlias(live, async (alias) => {
      const r = await check(live.origin, '--site', dir, '--preview', wd.link(VERSION_HOST), '--project', alias.origin);
      assert.equal(r.parsed.site.platform, 'both');
      assert.equal(r.by['workers-dev'].state, 'ok');
      assert.equal(r.by.previews.state, 'ok');
      assert.equal(r.by.canonical.state, 'ok', 'the pages.dev address is judged as for a Pages site');
      assert.equal(r.by.pages.state, 'look');
      assert.equal(r.by['build-settings'].state, 'hand', 'a Pages site still gets the dashboard item');
      assert.match(r.parsed.site.note, /functions\/ is a Pages marker\. Checked as a Workers site and a Pages site\./);
      assert.equal(r.code, 0, r.stdout);
    });
  }));

async function withAlias(live, fn) {
  const server = http.createServer((req, res) => { res.writeHead(301, { location: `https://${live.host}${req.url}` }); res.end(); });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  try {
    return await fn({ origin: `http://127.0.0.1:${server.address().port}` });
  } finally {
    server.closeAllConnections();
    await new Promise((r) => server.close(r));
  }
}

test('--config: a Workers config with another name beside a Pages wrangler.toml gets both sets of checks', (t) =>
  withBoth({}, async (live, wd) => {
    const dir = folder(t, { 'wrangler.toml': PAGES_TOML, 'workers.jsonc': WORKERS_CONFIG });
    const r = await check(live.origin, '--site', dir, '--config', 'workers.jsonc', '--preview', wd.link(VERSION_HOST));
    assert.equal(r.parsed.site.platform, 'both');
    assert.equal(r.by['workers-dev'].state, 'ok');
    assert.match(r.parsed.site.note, /workers\.jsonc is a Workers config for lenas-site, and wrangler\.toml is a Pages marker/);
    // Without --config the same folder is a Pages site: workers.jsonc is not a name Wrangler looks for.
    const plain = await check(live.origin, '--site', dir);
    assert.equal(plain.parsed.site.platform, 'pages');
    assert.equal(plain.by['workers-dev'].state, 'skip');
    assert.equal(plain.by['workers-dev'].blocked, undefined);
  }));

// ---- the address

test('CW2: the address left on, as Cloudflare answered it (capture), is FAIL, says how to turn it off, and exits 1', async (t) => {
  const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG });
  assert.equal(CAP.address_on_no_accept_encoding.status, 200, 'the capture: an address that is on serves the site, not the 1042 text');
  await withBoth({ rules: (host, req, res) => host === ADDRESS_HOST && (answerWith(res, CAP.address_on_no_accept_encoding), true) }, async (live, wd) => {
    const r = await check(live.origin, '--site', dir, '--preview', wd.link(VERSION_HOST));
    assert.equal(r.by['workers-dev'].state, 'fail');
    assert.match(r.by['workers-dev'].detail, /answers 200 and serves something, not 404 "error code: 1042": the address is on\./);
    assert.equal(r.by['workers-dev'].fix, 'Set "workers_dev": false in the Worker\'s config and deploy again.');
    assert.equal(r.code, 1);
  });
});

test('the address answers something other than the off answer: FAIL, each with its status, exit 1', async (t) => {
  const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG });
  const cases = [
    ['a 404 with another body', (res) => send(res, 404, 'text/plain', 'Not here'), /answers 404, not 404 "error code: 1042".*may be an address that is off/],
    ['a 503', (res) => send(res, 503, 'text/plain', 'error code: 1042'), /answers 503/],
    ['a 301', (res) => { res.writeHead(301, { location: '/elsewhere' }); res.end(); }, /answers 301 and serves something/],
    ['the site itself', (res) => send(res, 200, 'text/html', '<p>Hi</p>'), /answers 200 and serves something/],
  ];
  for (const [label, answer, detail] of cases) {
    await withBoth({ rules: (host, req, res) => { if (host === ADDRESS_HOST) { answer(res); return true; } return false; } }, async (live, wd) => {
      const r = await check(live.origin, '--site', dir, '--preview', wd.link(VERSION_HOST));
      assert.equal(r.by['workers-dev'].state, 'fail', label);
      assert.match(r.by['workers-dev'].detail, detail, label);
      assert.match(r.by['workers-dev'].fix, /"workers_dev": false/, label);
      assert.equal(r.code, 1, label);
    });
  }
});

test('the address answers the 1042 text, but no version link of the Worker serves: not checked, which counts as a failure', async (t) => {
  const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG });
  // CW3: the only link is a Preview that no longer exists.
  await withBoth({}, async (live, wd) => {
    const r = await check(live.origin, '--site', dir, '--preview', wd.link(DEAD_HOST));
    assert.equal(r.by.previews.state, 'look');
    assert.match(r.by.previews.detail, new RegExp(`${DEAD_HOST.replace(/\./g, '\\.')}:\\d+ does not serve the site`));
    assert.equal(r.by['workers-dev'].state, 'skip');
    assert.equal(r.by['workers-dev'].blocked, true);
    assert.match(r.by['workers-dev'].detail, /^not checked: .*Give a live version link\. A version link comes from `node move-to-workers\.mjs check`.*wrangler versions upload.*dashboard/);
    assert.equal(r.code, 1);
    assert.deepEqual(r.parsed.couldNotJudge, ['workers-dev']);
  });
  // Only aliases, all served: an alias may hold hyphens, so a served alias shows no Worker for certain.
  await withBoth({}, async (live, wd) => {
    const r = await check(live.origin, '--site', dir, '--preview', wd.link(ALIAS_HOST));
    assert.equal(r.by.previews.state, 'ok');
    assert.equal(r.by['workers-dev'].state, 'skip');
    assert.equal(r.by['workers-dev'].blocked, true);
    assert.equal(r.code, 1);
  });
  // A Worker named `site` and the link of another Worker, `lenas-site`: its prefix is not 8 hexadecimal characters.
  const other = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG.replace(`"${WORKER}"`, '"site"') });
  const offAddress = (host, req, res) => host === `site.${ACCOUNT}` && (answerWith(res, CAP.address_off_no_accept_encoding), true);
  await withBoth({ rules: offAddress }, async (live, wd) => {
    const r = await check(live.origin, '--site', other, '--preview', wd.link(`${VERSION}-lenas-site.${ACCOUNT}`));
    assert.equal(r.by['workers-dev'].state, 'skip', 'a link that ends in -site is not shown to be a version link of the Worker site');
    assert.equal(r.by['workers-dev'].blocked, true);
    assert.equal(r.code, 1);
  });
});

test('no --preview: both Workers items are not checked, which counts as a failure, and nothing is asked of workers.dev', (t) =>
  withBoth({}, async (live, wd) => {
    const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG });
    const r = await check(live.origin, '--site', dir);
    assert.equal(r.by['workers-dev'].blocked, true);
    assert.equal(r.by.previews.blocked, true);
    assert.match(r.by.previews.detail, /^not checked: no --preview link was given\./);
    assert.deepEqual(r.parsed.couldNotJudge.sort(), ['previews', 'workers-dev']);
    assert.equal(r.code, 1);
    assert.deepEqual(wd.asked, []);
  }));

test('preview_urls not true (false, or not set) in the config is a hint when no link serves, and does not replace the answers', async (t) => {
  const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG.replace('"preview_urls": true', '"preview_urls": false') });
  await withBoth({}, async (live, wd) => {
    const r = await check(live.origin, '--site', dir, '--preview', wd.link(VERSION_HOST.replace('0a1b2c3d', '0a1b2c3e')));
    assert.equal(r.by.previews.state, 'look');
    assert.match(r.by.previews.detail, /0a1b2c3e-lenas-site\.example-sub\.workers\.dev\.test:\d+ does not serve the site/);
    assert.equal(r.by['workers-dev'].blocked, true);
    assert.match(r.by['workers-dev'].detail, /does not set "preview_urls": true.*which may be why no link serves/);
    assert.equal(r.code, 1);
  });
  // The key left out is the same hint.
  const unset = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG.replace('  "preview_urls": true,\n', '') });
  await withBoth({}, async (live, wd) => {
    const r = await check(live.origin, '--site', unset, '--preview', wd.link(VERSION_HOST.replace('0a1b2c3d', '0a1b2c3e')));
    assert.match(r.by['workers-dev'].detail, /does not set "preview_urls": true/);
  });
  // A version link that serves with noindex: the link and the address are both asked, and judged on the answers.
  await withBoth({}, async (live, wd) => {
    const r = await check(live.origin, '--site', dir, '--preview', wd.link(VERSION_HOST));
    assert.equal(r.by.previews.state, 'ok');
    assert.equal(r.by['workers-dev'].state, 'ok');
    assert.doesNotMatch(r.by['workers-dev'].detail, /preview_urls/);
    assert.equal(r.code, 0, r.stdout);
    assert.deepEqual(wd.asked.map((a) => a.host).sort(), [VERSION_HOST, ADDRESS_HOST].sort());
  });
});

// ---- the links

test('a link without noindex is FAIL, named; a version link whose home page redirects is judged on the redirect itself', async (t) => {
  const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG });
  await withBoth({ rules: (host, req, res) => { if (host === ALIAS_HOST) { send(res, 200, 'text/html', '<p>Hi</p>'); return true; } return false; } }, async (live, wd) => {
    const r = await check(live.origin, '--site', dir, '--preview', `${wd.link(VERSION_HOST)},${wd.link(ALIAS_HOST)}`);
    assert.equal(r.by.previews.state, 'fail');
    assert.match(r.by.previews.detail, /preview-test-lenas-site\.example-sub\.workers\.dev\.test:\d+ answers 200 without noindex/);
    assert.doesNotMatch(r.by.previews.detail, /0a1b2c3d/, 'the link that is fine is not in the failure');
    assert.equal(r.code, 1);
  });
  // A version link whose home page redirects (the 307 of the with-rule capture, replayed on the home page; the
  // real redirect led from /a) is judged on the redirect itself, which is not followed; where it leads answers
  // 200 without noindex.
  const seen = [];
  await withBoth({ rules: (host, req, res) => {
    if (host !== VERSION_HOST) return false;
    seen.push(req.url);
    if (req.url === '/') { res.writeHead(RULE_REDIRECT.status, RULE_REDIRECT.headers); res.end(); } else send(res, 200, 'text/html', '<p>Privacy</p>');
    return true;
  } }, async (live, wd) => {
    const r = await check(live.origin, '--site', dir, '--preview', wd.link(VERSION_HOST));
    assert.equal(r.by.previews.state, 'ok', r.by.previews.detail);
    assert.equal(r.by['workers-dev'].state, 'ok');
    assert.deepEqual(seen, ['/'], 'the redirect is not followed');
    assert.equal(r.code, 0, r.stdout);
  });
});

// The links as Cloudflare answered them before the starter's rule: they carry Cloudflare's own NEL and Report-To,
// so each is a FAIL now, though the same answers were ok before 2026-11-13. The fixtures are as captured.
test('the version link, the Preview alias and a version link\'s 301, as captured without the rule, are FAIL for the NEL policy', async (t) => {
  const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG });
  const cases = [
    ['version link, 200 (2026-11-06)', VERSION_HOST, CAP.version_link_live],
    ['Preview alias, 200 (2026-11-06)', ALIAS_HOST, CAP.preview_alias_live],
    ['version link, 301 with noindex (2026-11-05)', VERSION_HOST, KIT_301],
  ];
  for (const [label, host, cap] of cases) {
    const rules = (h, req, res) => h === host && (cap.status === 200 ? answerWith(res, cap) : (res.writeHead(cap.status, cap.headers), res.end()), true);
    await withBoth({ rules }, async (live, wd) => {
      const r = await check(live.origin, '--site', dir, '--preview', wd.link(host));
      assert.equal(r.by.previews.state, 'fail', label);
      assert.match(r.by.previews.detail, /with a nel header that sets a policy \(\{"report_to":"cf-nel","success_fraction":0\.0,"max_age":604800\}\)/, label);
      assert.match(r.by.previews.detail, /with a report-to header/, label);
      assert.doesNotMatch(r.by.previews.detail, /without noindex/, `${label}: the noindex is there`);
      assert.equal(r.code, 1, label);
    });
  }
});

// The NEL half of the previews item: each way to fail has a test of its own.
const RULE_LINES = ['https://:version.:sub.workers.dev/*', '  NEL: {"max_age":0}'];
async function previewsFor(t, answer) {
  const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG });
  let r;
  await withBoth({ rules: (host, req, res) => host === VERSION_HOST && (answerWith(res, answer), true) }, async (live, wd) => {
    r = await check(live.origin, '--site', dir, '--preview', wd.link(VERSION_HOST));
  });
  return r;
}

test('a link answered as with the starter\'s rule (capture: noindex, nel max_age 0, no report-to) is ok', async (t) => {
  const r = await previewsFor(t, RULE_HOME);
  assert.equal(r.by.previews.state, 'ok', r.by.previews.detail);
  assert.match(r.by.previews.detail, /answers 200 with noindex and no active NEL policy\.$/);
  assert.equal(r.code, 0, r.stdout);
});

test('a link answered without the rule (capture: Cloudflare\'s nel and report-to) is FAIL, and the fix names the rule', async (t) => {
  const r = await previewsFor(t, NO_RULE_HOME);
  assert.equal(r.by.previews.state, 'fail');
  assert.match(r.by.previews.detail, /with a nel header that sets a policy .*"max_age":604800.*; and with a report-to header/);
  for (const line of RULE_LINES) assert.ok(r.by.previews.fix.includes(line.trim()), `the fix does not carry "${line.trim()}"`);
  assert.match(r.by.previews.fix, /site's own public\/_headers/);
  assert.equal(r.code, 1);
});

test('noindex with a nel policy of max_age 604800 and no report-to is FAIL, for the nel alone', async (t) => {
  const r = await previewsFor(t, { status: 200, headers: { 'x-robots-tag': 'noindex', nel: '{"max_age":604800}' }, body: 'x' });
  assert.equal(r.by.previews.state, 'fail');
  assert.match(r.by.previews.detail, /answers 200 with a nel header that sets a policy \(\{"max_age":604800\}\)/);
  assert.doesNotMatch(r.by.previews.detail, /report-to/);
  assert.ok(r.by.previews.fix.includes('NEL: {"max_age":0}'));
  assert.equal(r.code, 1);
});

test('noindex with nel max_age 0 but a report-to header is FAIL, for the report-to alone', async (t) => {
  const r = await previewsFor(t, { status: 200, headers: { 'x-robots-tag': 'noindex', nel: '{"max_age":0}', 'report-to': '{"group":"g","max_age":10,"endpoints":[{"url":"https://reports.example.invalid/r"}]}' }, body: 'x' });
  assert.equal(r.by.previews.state, 'fail');
  assert.match(r.by.previews.detail, /answers 200 with a report-to header, which sets up network error reporting\.$/);
  assert.doesNotMatch(r.by.previews.detail, /nel header/);
  assert.ok(r.by.previews.fix.includes('public/_headers'));
  assert.equal(r.code, 1);
});

test('a nel header that is not JSON is FAIL; so is one with no max_age of 0 (a string, or none)', async (t) => {
  for (const nel of ['max_age=0', '{"max_age":"0"}', '{"report_to":"cf-nel"}', 'null']) {
    const r = await previewsFor(t, { status: 200, headers: { 'x-robots-tag': 'noindex', nel }, body: 'x' });
    assert.equal(r.by.previews.state, 'fail', nel);
    assert.match(r.by.previews.detail, nel === 'max_age=0' ? /with a nel header that is not JSON \(max_age=0\)/ : /with a nel header that sets a policy/, nel);
    assert.equal(r.code, 1, nel);
  }
});

test('noindex with no nel and no report-to header is ok: nothing sets a policy', async (t) => {
  const r = await previewsFor(t, { status: 200, headers: { 'x-robots-tag': 'noindex' }, body: 'x' });
  assert.equal(r.by.previews.state, 'ok', r.by.previews.detail);
  assert.equal(r.code, 0, r.stdout);
});

test('a link with no noindex and a NEL policy gets both problems named, and a missing noindex alone keeps the old fix', async (t) => {
  const both = await previewsFor(t, { status: 200, headers: { nel: '{"max_age":604800}' }, body: 'x' });
  assert.match(both.by.previews.detail, /without noindex in x-robots-tag .*; and with a nel header/);
  const plain = await previewsFor(t, { status: 200, headers: {}, body: 'x' });
  assert.equal(plain.by.previews.state, 'fail');
  assert.doesNotMatch(plain.by.previews.detail, /nel/);
  assert.equal(plain.by.previews.fix, 'See section 1 of the Cloudflare checklist.');
});

// The checker reads "/" only, so this test is what keeps the rule in the starter.
test('the starter\'s public/_headers holds the NEL rule for version and Preview links, the two lines as the spike ran them', () => {
  const lines = STARTER_HEADERS.split('\n');
  const at = lines.indexOf(RULE_LINES[0]);
  assert.ok(at >= 0, 'the rule\'s host line is missing');
  assert.equal(lines[at + 1], RULE_LINES[1], 'the line under it is not NEL: {"max_age":0}');
  assert.ok(lines.indexOf('/*') < at, 'the rule comes after the /* block');
});

test('noindex counts as a bare directive of x-robots-tag, not as a piece of another word or a value for one crawler', async (t) => {
  const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG });
  const want = { 'noindex, nofollow': 'ok', 'NOINDEX': 'ok', 'nofollow,noindex': 'ok', noindexing: 'fail', 'notnoindex': 'fail', 'nofollow': 'fail', 'googlebot: noindex': 'fail', 'googlebot: nofollow, noindex': 'fail' };
  for (const [value, state] of Object.entries(want)) {
    const rules = (host, req, res) => host === VERSION_HOST && (answerWith(res, RULE_HOME, { 'x-robots-tag': value }), true);
    await withBoth({ rules }, async (live, wd) => {
      const r = await check(live.origin, '--site', dir, '--preview', wd.link(VERSION_HOST));
      assert.equal(r.by.previews.state, state, `x-robots-tag: ${value}`);
    });
  }
});

test('a Worker name that was never created answers as an address that is off does (capture)', () => {
  assert.equal(CAP.address_never_created_no_accept_encoding.status, CAP.address_off_no_accept_encoding.status);
  assert.equal(CAP.address_never_created_no_accept_encoding.body, CAP.address_off_no_accept_encoding.body);
});

test('three links in three states: previews takes the worst, and the link with no answer is named in both places', async (t) => {
  const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG });
  const silent = `silent-${WORKER}.${ACCOUNT}`;
  await withBoth({ rules: (host, req, res) => {
    if (host === silent) { req.socket.destroy(); return true; }
    if (host === ALIAS_HOST) { send(res, 200, 'text/html', '<p>Hi</p>'); return true; }
    return false;
  } }, async (live, wd) => {
    for (const order of [[VERSION_HOST, ALIAS_HOST, silent], [silent, ALIAS_HOST, VERSION_HOST]]) {
      const r = await check(live.origin, '--site', dir, '--preview', order.map((h) => wd.link(h)).join(','));
      assert.equal(r.by.previews.state, 'fail', order[0]);
      assert.match(r.by.previews.detail, /silent-lenas-site\.example-sub\.workers\.dev\.test:\d+: /);
      assert.match(r.by.previews.detail, /preview-test-lenas-site\.[^ ]+ answers 200 without noindex/);
      assert.ok(r.parsed.unanswered.some((u) => u.includes(silent)), 'the no-answer line names the link');
      assert.equal(r.code, 1);
    }
  });
});

test('a link and an address that get no answer are named in the no-answer line, and the exit status is 1', async (t) => {
  const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG });
  const wd = await workersDev();
  const link = wd.link(VERSION_HOST);
  await wd.close(); // the port is now closed
  const live = await domain();
  try {
    const r = await check(live.origin, '--site', dir, '--preview', link);
    assert.equal(r.code, 1);
    assert.deepEqual(r.parsed.unanswered.filter((u) => u.includes('workers.dev')).sort(), [`${link}/`, link.replace(VERSION_HOST, ADDRESS_HOST) + '/'].sort());
    assert.equal(r.by.previews.state, 'fail');
    assert.equal(r.by['workers-dev'].state, 'fail');
  } finally {
    await live.close();
  }
});

test('--only previews sends nothing to the address; --only workers-dev asks both', async (t) => {
  const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG });
  await withBoth({}, async (live, wd) => {
    const r = await check(live.origin, '--site', dir, '--preview', wd.link(VERSION_HOST), '--only', 'previews');
    assert.deepEqual(r.parsed.results.map((x) => x.id), ['previews']);
    assert.deepEqual(wd.asked.map((a) => a.host), [VERSION_HOST]);
    wd.asked.length = 0;
    const both = await check(live.origin, '--site', dir, '--preview', wd.link(VERSION_HOST), '--only', 'workers-dev');
    assert.deepEqual(both.parsed.results.map((x) => x.id), ['workers-dev']);
    assert.deepEqual(wd.asked.map((a) => a.host).sort(), [VERSION_HOST, ADDRESS_HOST].sort());
    assert.equal(both.code, 0, both.stdout);
  });
});

// ---- Pages sites keep what they had (S7)

test('CW4: a Pages site gets the results it had, with or without --site; the Workers items are not run and do not count', async (t) => {
  const old = 'domain=ok https=ok hsts=look nel=ok bot=ok analytics=ok email=ok scripts=ok robots=ok build=look pages=skip canonical=skip';
  const ids = ['domain', 'https', 'hsts', 'nel', 'bot', 'analytics', 'email', 'scripts', 'robots', 'build', 'pages', 'canonical'];
  const withFunctions = folder(t, { 'functions/_middleware.ts': 'export {};\n' });
  const withToml = folder(t, { 'wrangler.toml': PAGES_TOML });
  const neither = folder(t, { 'README.md': 'hello\n' });
  const runs = [[], ['--site', withFunctions], ['--site', withToml], ['--site', neither]];
  await withBoth({}, async (live) => {
    for (const extra of runs) {
      const r = await check(live.origin, ...extra);
      assert.ok(sameStates(r.by, ids, old), `${extra.join(' ')}: ${ids.map((id) => `${id}=${r.by[id].state}`).join(' ')}`);
      assert.equal(r.by['build-settings'].state, 'hand', 'a Pages site keeps its dashboard item');
      for (const id of ['workers-dev', 'previews']) {
        assert.equal(r.by[id].state, 'skip', id);
        assert.match(r.by[id].detail, /^not run: /);
        assert.equal(r.by[id].blocked, undefined, `${id} must not count as a failure`);
      }
      assert.deepEqual(r.parsed.couldNotJudge, []);
      assert.equal(r.code, 0, r.stdout);
    }
    const nothing = await check(live.origin, '--site', neither);
    assert.match(nothing.parsed.site.note, /no Wrangler file and no functions\/ folder was found, so it was checked as a Pages site/);
    assert.match(nothing.by['workers-dev'].detail, /no Wrangler file and no functions\/ folder was found/);
    const text = await run([live.origin, '--timeout', '5', '--site', neither]);
    assert.match(text.stdout, /no Wrangler file and no functions\/ folder was found/);
    assert.match(text.stdout, /Result: \d+ ok, 0 FAIL, \d+ look, 5 by hand, 4 not run\./);
  });
});

// ---- build.txt

test('CW5: line 1 of build.txt is the commit; a platform line is named, not judged; CRLF is the same', async () => {
  for (const [label, text] of [['LF', `${SHA}\nplatform=pages\n`], ['CRLF', `${SHA}\r\nplatform=pages\r\n`]]) {
    await withBoth({ domain: { buildTxt: text } }, async (live) => {
      const ok = await check(live.origin, '--build', SHA.slice(0, 7));
      assert.equal(ok.by.build.state, 'ok', `${label}: ${ok.by.build.detail}`);
      assert.match(ok.by.build.detail, /build\.txt also says platform=pages\./);
      const none = await check(live.origin);
      assert.equal(none.by.build.state, 'look');
      assert.match(none.by.build.detail, /Nothing was compared.*build\.txt also says platform=pages\./);
      const wrong = await check(live.origin, '--build', 'abcdef1');
      assert.equal(wrong.by.build.state, 'fail');
    });
  }
  // Another second line is ignored and not printed; a first line that is not a commit is still no marker.
  await withBoth({ domain: { buildTxt: `${SHA}\nsomething else\n` } }, async (live) => {
    const r = await check(live.origin, '--build', SHA.slice(0, 7));
    assert.equal(r.by.build.state, 'ok');
    assert.doesNotMatch(r.by.build.detail, /something else|also says/);
  });
  await withBoth({ domain: { buildTxt: 'platform=pages\n' } }, async (live) => {
    assert.equal((await check(live.origin)).by.build.state, 'look');
  });
});

// ---- the site's files

test('wrangler.toml: with pages_build_output_dir it is a Pages config; without it the run is refused; the name under [vars] is taken as Pages', async (t) => {
  await withBoth({}, async (live) => {
    const pages = await check(live.origin, '--site', folder(t, { 'wrangler.toml': PAGES_TOML }));
    assert.equal(pages.parsed.site.platform, 'pages');
    assert.match(pages.parsed.site.note, /wrangler\.toml is a Pages marker/);
    const vars = await check(live.origin, '--site', folder(t, { 'wrangler.toml': 'pages_build_output_dir = "dist"\n[vars]\nname = "lenas-site"\n' }));
    assert.equal(vars.parsed.site.platform, 'pages', 'a presence check, not a parse');
    const commented = await run([live.origin, '--site', folder(t, { 'wrangler.toml': '# pages_build_output_dir = "dist"\nname = "lenas-site"\n' })]);
    assert.equal(commented.code, 2, 'a commented-out key is not a Pages marker');
    const refused = await run([live.origin, '--site', folder(t, { 'wrangler.toml': 'name = "lenas-site"\n[assets]\ndirectory = "./dist"\n' })]);
    assert.equal(refused.code, 2);
    assert.match(refused.stderr, /wrangler\.toml holds no pages_build_output_dir, and the check reads a Workers config only from a \.json or \.jsonc file/);
  });
});

test('a Wrangler file the check cannot place is refused by name; a file it does not look for is not read', async (t) => {
  await withBoth({}, async (live) => {
    for (const [label, files, want] of [
      ['a Worker with no static assets', { 'wrangler.jsonc': '{ "name": "lenas-site", "main": "src/index.ts" }' }, /wrangler\.jsonc is neither a Pages config .* nor a Workers config/],
      ['not JSON', { 'wrangler.json': 'name = lenas' }, /wrangler\.json cannot be read as JSON/],
      ['a list', { 'wrangler.json': '[]' }, /wrangler\.json is not a JSON object/],
      ['a name that is not a host label', { 'wrangler.jsonc': WORKERS_CONFIG.replace(WORKER, 'lenas/site') }, /"lenas\/site" is not a Worker name/],
      ['two Workers', { 'wrangler.json': WORKERS_CONFIG, 'wrangler.jsonc': WORKERS_CONFIG.replace(WORKER, 'another') }, /wrangler\.json names the Worker lenas-site, wrangler\.jsonc names the Worker another: one site, one Worker/],
    ]) {
      const r = await run([live.origin, '--site', folder(t, files)]);
      assert.equal(r.code, 2, label);
      assert.match(r.stderr, want, label);
      assert.equal(r.stdout, '', label);
    }
    // A package.json with a name and assets.directory beside the config is no Wrangler file; the same two configs
    // under one name are one Worker.
    const same = await check(live.origin, '--site', folder(t, { 'wrangler.json': WORKERS_CONFIG, 'wrangler.jsonc': WORKERS_CONFIG, 'package.json': '{ "name": "other", "assets": { "directory": "x" } }' }));
    assert.equal(same.parsed.site.platform, 'workers');
  });
});

test('the run is refused with exit 2, and no request is sent, for each wrong command', async (t) => {
  await withBoth({}, async (live, wd) => {
    const dir = folder(t, { 'wrangler.jsonc': WORKERS_CONFIG });
    const pagesDir = folder(t, { 'wrangler.toml': PAGES_TOML });
    const file = path.join(dir, 'wrangler.jsonc');
    const ok = wd.link(VERSION_HOST);
    const cases = [
      ['--site names a folder that does not exist', ['--site', path.join(dir, 'nope')], /is not a folder/],
      ['--site names a file', ['--site', file], /is not a folder/],
      ['a Worker name over 63 characters', ['--site', folder(t, { 'wrangler.jsonc': WORKERS_CONFIG.replace(`"${WORKER}"`, `"${'a'.repeat(64)}"`) })], /is not a Worker name \(1 to 63 letters/],
      ['--config names no file', ['--site', dir, '--config', 'nope.jsonc'], /--config "nope\.jsonc" is not a file/],
      ['--config without --site', ['--config', 'wrangler.jsonc'], /--config goes with --site/],
      ['--preview without --site', ['--preview', ok], /--preview goes with --site/],
      ['--preview on a Pages site', ['--site', pagesDir, '--preview', ok], /--preview is for a Worker/],
      ['a link of another Worker', ['--site', dir, '--preview', wd.link(`0a1b2c3d-other.${ACCOUNT}`)], /its first label must be a prefix, a hyphen and the Worker's name \(lenas-site, from wrangler\.jsonc\)/],
      ['a link with no prefix', ['--site', dir, '--preview', wd.link(ADDRESS_HOST)], /its first label must be a prefix/],
      ['links of two accounts', ['--site', dir, '--preview', `${ok},${ok.replace('example-sub', 'another-sub')}`], /name two accounts/],
      ['a link with a path', ['--site', dir, '--preview', `${ok}/home`], /with no path/],
      ['a link that is not on workers.dev', ['--site', dir, '--preview', 'https://0a1b2c3d-lenas-site.pages.dev'], /form https:\/\/<prefix>-<worker>\.<account>\.workers\.dev/],
      ['a live name over http', ['--site', dir, '--preview', 'http://0a1b2c3d-lenas-site.example-sub.workers.dev'], /form https:/],
    ];
    for (const [label, args, want] of cases) {
      const r = await run([live.origin, ...args]);
      assert.equal(r.code, 2, label);
      assert.match(r.stderr, want, label);
      assert.match(r.stderr, /Usage: node cloudflare-check\.mjs/, label);
      assert.equal(r.stdout, '', label);
    }
    assert.deepEqual(wd.asked, []);
  });
});

// ---- the readers

test('the JSONC reader: both comment forms, trailing commas, and // or /* inside a string', () => {
  assert.deepEqual(parseJsonc('{ // one\n "a": 1, /* two */ "b": [1, 2, ], }'), { a: 1, b: [1, 2] });
  assert.deepEqual(parseJsonc('{ "url": "https://x.test/a//b", "c": "/* not a comment */", "d": "a\\"//b" }'), { url: 'https://x.test/a//b', c: '/* not a comment */', d: 'a"//b' });
  assert.deepEqual(parseJsonc('\ufeff{"a": [ // c\n 1, ], }'), { a: [1] });
  assert.deepEqual(parseJsonc('{"a": "x,}"}'), { a: 'x,}' }, 'a comma inside a string is a comma');
  assert.throws(() => parseJsonc('{ /* never closed }'), SyntaxError);
  assert.throws(() => parseJsonc('{ "a": 1 "b": 2 }'), SyntaxError);
});

test('the link parser: a Worker name with hyphens, an alias with hyphens, an 8-hex version prefix', () => {
  const at = (...links) => parsePreview(links.join(','), 'lenas-site');
  const one = at('https://0a1b2c3d-lenas-site.example-sub.workers.dev');
  assert.deepEqual(one.links, [{ url: 'https://0a1b2c3d-lenas-site.example-sub.workers.dev/', origin: 'https://0a1b2c3d-lenas-site.example-sub.workers.dev', version: true }]);
  assert.equal(one.address, 'https://lenas-site.example-sub.workers.dev');
  const aliases = at('https://preview-lenas-site.example-sub.workers.dev', 'https://my-feature-lenas-site.example-sub.workers.dev/', 'https://0a1b2c3-lenas-site.example-sub.workers.dev', 'https://0A1B2C3D-lenas-site.example-sub.workers.dev', 'https://0a1b2c3g-lenas-site.example-sub.workers.dev');
  assert.deepEqual(aliases.links.map((l) => l.version), [false, false, false, true, false], 'an alias is not a version link, even with hyphens; 8 hexadecimal characters exactly');
  // Another Worker whose name ends the same way is told apart by the name, not guessed.
  assert.throws(() => at('https://0a1b2c3d-lenas-shop.example-sub.workers.dev'), UsageError);
  // A name that is itself hyphenated can still be a prefix of the Worker's name.
  assert.equal(parsePreview('https://x-y-site.example-sub.workers.dev', 'site').links[0].version, false);
  assert.equal(parsePreview('http://0a1b2c3d-site.acct.workers.dev.test:8080', 'site').address, 'http://site.acct.workers.dev.test:8080');
  assert.throws(() => parsePreview('https://0a1b2c3d-site.acct.workers.dev.test', 'site'), UsageError, 'a test name is for http only');
  assert.equal(at('https://0a1b2c3d-lenas-site.example-sub.workers.dev', 'https://0a1b2c3d-lenas-site.example-sub.workers.dev').links.length, 1, 'a link given twice counts once');
});
