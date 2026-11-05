// Tests for move-to-workers.mjs. Standard library only; run with
//   node --test skills/new-website/scripts/tests/move-to-workers.test.mjs
//
// The numbers are the plan's tests (workers-for-new-sites/PLAN-move-script.md, "How it is tested"):
//   1  the gate and the token rules      2  recorded captures, hand-written expectations
//   3  the commands, run through main()  4  the status page
// Test 5, the throwaway run on a real account, is not here: it needs a token. Each scenario runs
// main() the way the program does, in a fixture repository whose origin is a GitHub address that the
// repository's own git config sends to a local folder, against the stub in move-stub.mjs.
import { describe, test as nodeTest } from 'node:test';
import assert from 'node:assert/strict';
import { execFile, execFileSync, spawnSync } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { EMPTY_BODY, Stop, blankJsonc, compare, confirmCode, esc, gate, headerNames, main, makeApi, runProgram, makeSiteFetch, parseJsonc, pathList, renderStatus, routesOf, setRoutes } from '../move-to-workers.mjs';
import { ACCOUNT, OWNER, REPO, TOKEN, ZONE, deployment } from './cloudflare-stub.mjs';
import { HOSTS, SITE, SUBDOMAIN, VERSION_HOST, WORKER, fillerRuns, makeFetch, makeWorld, platformOf, spend, unfinishedWorkersRun, withoutWorkersRun } from './move-stub.mjs';

// A scenario whose clock stands still can loop for ever if serving breaks: no test runs past two minutes.
const test = (name, fn) => nodeTest(name, { timeout: 120_000 }, fn);

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCRIPTS = path.join(HERE, '..');
const REMOTE = `https://github.com/${OWNER}/${REPO}.git`;

const scratch = mkdtempSync(path.join(tmpdir(), 'move-test-'));
process.on('exit', () => rmSync(scratch, { recursive: true, force: true }));
const GIT_ISOLATION = { GIT_CONFIG_GLOBAL: path.join(scratch, 'empty-gitconfig'), GIT_CONFIG_NOSYSTEM: '1' };
writeFileSync(GIT_ISOLATION.GIT_CONFIG_GLOBAL, '');
const WHEN = '2026-11-03T10:00:00Z'; // fixed dates: every fixture site has the same commits
const gitEnv = { ...process.env, ...GIT_ISOLATION, GIT_AUTHOR_NAME: 'Lena', GIT_AUTHOR_EMAIL: 'lena@example.com', GIT_COMMITTER_NAME: 'Lena', GIT_COMMITTER_EMAIL: 'lena@example.com', GIT_AUTHOR_DATE: WHEN, GIT_COMMITTER_DATE: WHEN };
delete gitEnv.CLOUDFLARE_API_TOKEN;
const git = (cwd, ...args) => execFileSync('git', args, { cwd, env: gitEnv, encoding: 'utf8' }).trim();
const slash = (p) => p.replace(/\\/g, '/');

// ---------------------------------------------------------------- the site and its origin

let serial = 0;
// A two-stage site made with the kit, with a Pages wrangler.toml beside workers.jsonc; origin holds
// main and production at the same commit. `files` adds or replaces files (null removes one).
function makeSite({ files = {}, prodBranch = 'production' } = {}) {
  const dir = path.join(scratch, `s${++serial}`);
  const origin = path.join(dir, 'origin.git');
  const work = path.join(dir, 'work');
  mkdirSync(work, { recursive: true });
  git(dir, 'init', '-q', '--bare', origin);
  git(work, 'init', '-q');
  git(work, 'checkout', '-q', '-b', prodBranch === 'main' ? 'main' : 'production');
  const all = {
    'src/config.ts': `export const SITE = { name: 'Lenas Backstube' };\nexport const PROD_BRANCH = '${prodBranch}';\nexport const analytics = {\n  mode: 'script' as 'script' | 'server',\n};\n`,
    'workers.jsonc': `{\n  // The Worker that serves the built site\n  "name": "${WORKER}",\n  "compatibility_date": "2026-01-01",\n  "assets": { "directory": "./dist" },\n}\n`,
    'wrangler.toml': 'name = "lenas-backstube"\npages_build_output_dir = "dist"\n',
    'package.json': JSON.stringify({ name: 'lenas-backstube', private: true, scripts: { build: 'node build.mjs' } }),
    'package-lock.json': JSON.stringify({ name: 'lenas-backstube', lockfileVersion: 3, requires: true, packages: { '': { name: 'lenas-backstube' } } }),
    'build.mjs': "import { cpSync, mkdirSync, writeFileSync } from 'node:fs';\nmkdirSync('dist', { recursive: true });\ncpSync('site', 'dist', { recursive: true });\nif (process.env.CLOUDFLARE_API_TOKEN) process.exit(9); // the build never sees the token\nconst sha = process.env.CF_PAGES_COMMIT_SHA;\nwriteFileSync('dist/build.txt', `${sha}\\n`);\nwriteFileSync('dist/build-state.txt', `${sha}\\nbuilt ${Date.now()}\\n`);\n",
    '.gitignore': 'node_modules/\ndist/\n.dev.vars\n',
    ...Object.fromEntries(Object.entries(SITE).map(([f, t]) => [`site/${f}`, t])),
    ...files,
  };
  for (const [f, text] of Object.entries(all)) {
    if (text === null) continue;
    mkdirSync(path.dirname(path.join(work, f)), { recursive: true });
    writeFileSync(path.join(work, f), text);
  }
  git(work, 'add', '-A');
  git(work, 'commit', '-q', '-m', "Lena's site");
  git(work, 'remote', 'add', 'origin', REMOTE);
  git(work, 'config', `url.${slash(origin)}.insteadOf`, REMOTE);
  if (prodBranch === 'main') git(work, 'push', '-q', 'origin', 'main');
  else git(work, 'push', '-q', 'origin', 'production', 'production:main');
  return { dir, origin, work, frozen: git(work, 'rev-parse', 'HEAD') };
}

// A scenario: a site, a world, a home for the state file, and `go` to run a command in it.
function scenario({ site = makeSite(), world = {}, tokenValue = TOKEN } = {}) {
  const w = makeWorld(world);
  w.pagesCommit = site.frozen;
  w.workerCommit = site.frozen;
  const home = path.join(site.dir, 'home');
  mkdirSync(home, { recursive: true });
  const out = [];
  const go = async (args, extra = {}) => {
    out.length = 0;
    const fetchStub = makeFetch(w);
    const io = {
      cwd: site.work, env: { ...gitEnv, CLOUDFLARE_API_TOKEN: tokenValue }, home, apiFetch: fetchStub, siteFetch: fetchStub, useGh: false, pollMs: 0, goodGapMs: 1,
      sleep: yielding, say: (...l) => { out.push(...l); }, ...extra,
    };
    const code = await main(args, io);
    const text = out.join('\n');
    assert.ok(!text.includes(TOKEN), 'the token was printed');
    return { code, text, out: [...out] };
  };
  const stateFile = () => path.join(home, '.config', 'croftweaver', 'moves', ZONE.name, `${OWNER}-${REPO}`, 'state.json');
  const state = () => JSON.parse(readFileSync(stateFile(), 'utf8'));
  const dirty = () => git(site.work, 'status', '--porcelain');
  const push = () => git(site.work, 'push', '-q', 'origin', 'HEAD:production', 'HEAD:main');
  return { site, w, home, go, stateFile, state, dirty, push, text: () => out.join('\n') };
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
// A simulated sleep that lets the event loop turn, so a test's timeout can fire while a run spins.
const yielding = () => new Promise((r) => setImmediate(r));
// record runs until the build, which takes longer than a run, has finished.
async function recordDone(s) {
  for (let i = 0; i < 120; i++) {
    const r = await s.go(['record']);
    if (r.code !== 4) return r;
    await wait(250);
  }
  throw new Error('the build did not finish');
}

// One real record, made once; every scenario that needs "recorded" starts from a copy of its files.
let recordedOnce;
async function recorded(over = {}) {
  recordedOnce ??= (async () => {
    const s = scenario();
    const r = await recordDone(s);
    assert.equal(r.code, 0, r.text);
    return { state: readFileSync(s.stateFile(), 'utf8'), site: s.site };
  })();
  const base = await recordedOnce;
  const s = scenario(over);
  assert.equal(s.site.frozen, base.site.frozen, 'fixture sites share their commits');
  mkdirSync(path.dirname(s.stateFile()), { recursive: true });
  writeFileSync(s.stateFile(), base.state);
  return s;
}
const codeOf = (r) => /--confirm ([0-9a-f]{16})/.exec(r.text)?.[1];

// ---------------------------------------------------------------- test 1: the gate and the token

const CTX = () => ({
  accountId: ACCOUNT.id, zoneId: ZONE.id, zoneName: ZONE.name, project: REPO, worker: WORKER, subdomain: SUBDOMAIN,
  hosts: new Set(HOSTS), cnames: new Map([['f'.padEnd(32, '1'), { name: HOSTS[0], content: SUBDOMAIN }]]), workerDomainIds: new Map([['00000001-0000-4000-8000-000000000000', HOSTS[0]]]),
});
const A = `/accounts/${ACCOUNT.id}`;
const Z = `/zones/${ZONE.id}`;

describe('1: the gate', () => {
  test('it lets through the calls the move makes', () => {
    const c = CTX();
    for (const [m, p, b] of [
      ['GET', '/user/tokens/verify'], ['GET', '/zones?per_page=50&page=1'], ['GET', `${Z}/dns_records?per_page=100&page=1`], ['GET', `${Z}/dns_records/export`],
      ['GET', `${A}/pages/projects/${REPO}`], ['GET', `${A}/workers/domains`], ['GET', `${A}/workers/scripts/${WORKER}/deployments`], ['GET', `${A}/workers/subdomain`],
      ['POST', `${A}/pages/projects/${REPO}/domains`, { name: HOSTS[1] }], ['DELETE', `${A}/pages/projects/${REPO}/domains/${HOSTS[0]}`],
      ['POST', `${Z}/dns_records`, { type: 'CNAME', name: HOSTS[0], content: SUBDOMAIN, proxied: true }], ['DELETE', `${Z}/dns_records/${'f'.padEnd(32, '1')}`],
      ['PUT', `${A}/workers/domains`, { hostname: HOSTS[0], service: WORKER, zone_id: ZONE.id, environment: 'production' }],
      ['DELETE', `${A}/workers/domains/00000001-0000-4000-8000-000000000000`],
    ]) assert.doesNotThrow(() => gate(m, p, b, c), `${m} ${p}`);
  });

  test('it refuses every call outside that list', () => {
    const c = CTX();
    const nope = (m, p, b, why) => assert.throws(() => gate(m, p, b, c), (e) => e instanceof Stop && /gate: refused/.test(e.message), why ?? `${m} ${p}`);
    nope('POST', `${Z}/dns_records`, { type: 'MX', name: HOSTS[0], content: 'mail.example', priority: 10 }, 'an MX record on the apex');
    nope('POST', `${Z}/dns_records`, { type: 'CNAME', name: 'mail.lenas-backstube.example', content: SUBDOMAIN, proxied: true }, 'a host outside the list');
    nope('POST', `${Z}/dns_records`, { type: 'CNAME', name: HOSTS[0], content: 'evil.example', proxied: true }, 'a CNAME to somewhere else');
    nope('POST', `${Z}/dns_records`, { type: 'CNAME', name: HOSTS[0], content: SUBDOMAIN, proxied: false }, 'an unproxied CNAME');
    nope('PATCH', `${Z}/dns_records/${'f'.padEnd(32, '1')}`, { content: 'x.example' }, 'a PATCH');
    nope('DELETE', `${Z}/dns_records/${'e'.padEnd(32, '2')}`, undefined, 'a record no read showed');
    nope('PUT', `${A}/workers/domains`, { hostname: HOSTS[0], service: 'another-worker', zone_id: ZONE.id, environment: 'production' }, 'another Worker');
    nope('PUT', `${A}/workers/domains`, { hostname: 'mail.lenas-backstube.example', service: WORKER, zone_id: ZONE.id, environment: 'production' }, 'another host');
    nope('PUT', `${A}/workers/domains`, { hostname: HOSTS[0], service: WORKER, zone_id: 'c0ffee00000000000000000000000099', environment: 'production' }, 'another zone');
    nope('PUT', `${A}/workers/domains`, { hostname: HOSTS[0], service: WORKER, zone_id: ZONE.id, environment: 'staging' }, 'another environment');
    nope('DELETE', `${A}/workers/domains/99999999-0000-4000-8000-000000000000`, undefined, "another Worker's domain id");
    nope('DELETE', `${A}/pages/projects/${REPO}/domains/${REPO}.pages.dev`, undefined, 'the project address');
    nope('DELETE', `${A}/pages/projects/${REPO}`, undefined, 'the whole project');
    nope('POST', `${A}/pages/projects/other/domains`, { name: HOSTS[0] }, 'another project');
    nope('GET', `${A}/workers/scripts/another-worker/deployments`, undefined, "another Worker's deployments");
    nope('GET', `${Z}/settings/ssl`, undefined, 'a read nobody listed');
    nope('GET', `${A}/pages/projects/${REPO}/../x`, undefined, 'a dot-dot path');
  });

  test('a refused call is never sent', async () => {
    let sent = 0;
    const api = makeApi(async () => { sent++; throw new Error('sent'); }, TOKEN, CTX());
    await assert.rejects(api('POST', `${Z}/dns_records`, { json: { type: 'MX', name: HOSTS[0], content: 'x.example' } }), Stop);
    await assert.rejects(api('PUT', `${A}/workers/domains`, { json: { hostname: HOSTS[0], service: 'another-worker', zone_id: ZONE.id, environment: 'production' } }), Stop);
    assert.equal(sent, 0);
  });

  test('the second fetch function refuses Cloudflare\'s API and every host outside its list', async () => {
    let sent = 0;
    const f = makeSiteFetch(async () => { sent++; return new Response(''); }, new Set([HOSTS[0], 'api.github.com']));
    await assert.rejects(f('https://api.cloudflare.com/client/v4/zones'), Stop);
    await assert.rejects(f('https://elsewhere.example/x'), Stop);
    await assert.doesNotReject(f(`https://${HOSTS[0]}/`));
    assert.equal(sent, 1);
    const g = makeSiteFetch(async () => new Response(''), new Set(['api.cloudflare.com']));
    await assert.rejects(g('https://api.cloudflare.com/client/v4/zones'), Stop, 'even when someone adds it to the list');
  });
});

describe('1: the token', () => {
  test('a token whose DNS reaches two zones is refused, and names them', async () => {
    const s = scenario({ world: { extraZones: 1 } });
    const r = await s.go(['check']);
    assert.equal(r.code, 1);
    assert.match(r.text, /DNS or settings of 2 zones \(lenas-backstube\.example, extra0\.example\)/);
    assert.ok(!s.w.calls.some((c) => c.method !== 'GET'));
  });

  // The token CLOUDFLARE_MOVE.md tells a User to make is listed with every zone of the account, because
  // the account-wide Workers permission shows them all; only the site's zone carries DNS permissions.
  // The capture is Cloudflare's real answer (see its .md). Its site zone gets the stub's zone id by hand.
  const TOKEN_ZONES = path.join(HERE, 'fixtures', 'cloudflare-token', 'cloudflare-api-zones-list-move-token-2026-11-04.json');
  const tokenZones = () => {
    const zones = JSON.parse(readFileSync(TOKEN_ZONES, 'utf8')).result;
    const site = zones.find((z) => z.permissions.includes('#dns_records:edit'));
    site.id = ZONE.id;
    site.name = ZONE.name;
    site.account = { ...ACCOUNT };
    return { zones, site };
  };
  test('the token the recipe makes is accepted although the account lists three zones', async () => {
    const { zones } = tokenZones();
    assert.equal(zones.length, 3);
    assert.equal(zones.filter((z) => z.permissions.includes('#dns_records:edit')).length, 1, 'by hand: one zone of the three has DNS Edit');
    assert.notEqual(zones[0].name, ZONE.name, 'the site zone is not first in the list');
    const s = scenario({ world: { zones } });
    const r = await s.go(['check']);
    assert.equal(r.code, 0, r.text);
    assert.ok(!s.w.calls.some((c) => c.method !== 'GET'));
  });
  test('a token listed with account-only zones in front of the site zone is accepted too', async () => {
    const s = scenario({ world: { accountOnlyZones: 4 } });
    const r = await s.go(['check']);
    assert.equal(r.code, 0, r.text);
  });
  test('a second zone with DNS Edit refuses, and so does one with only DNS Read or zone settings', async () => {
    for (const extra of [['#dns_records:edit', '#dns_records:read', '#zone:read'], ['#dns_records:read'], ['#zone_settings:read', '#zone:read']]) {
      const { zones } = tokenZones();
      zones[0].permissions = [...zones[0].permissions, ...extra];
      const r = await scenario({ world: { zones } }).go(['check']);
      assert.equal(r.code, 1, `${extra}: ${r.text}`);
      assert.match(r.text, /DNS or settings of 2 zones \(other-1\.example, lenas-backstube\.example\)/, extra.join());
    }
  });
  test('a token with DNS Edit in no zone refuses and says what to make', async () => {
    const { zones, site } = tokenZones();
    site.permissions = site.permissions.filter((p) => p !== '#dns_records:edit');
    const r = await scenario({ world: { zones } }).go(['check']);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /cannot edit the DNS of any zone it lists.*Zone Read and DNS Edit/);
    const none = tokenZones();
    for (const z of none.zones) z.permissions = z.permissions.filter((p) => !/^#(dns_records|zone_settings):/.test(p));
    assert.match((await scenario({ world: { zones: none.zones } }).go(['check'])).text, /cannot edit the DNS of any zone it lists/);
  });
  test('a zone that does not say what the token may do refuses', async () => {
    const { zones } = tokenZones();
    delete zones[0].permissions;
    const r = await scenario({ world: { zones } }).go(['check']);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /did not say what this token may do in the zone other-1\.example/);
  });
  test('a token that ends more than eight days out is refused; one with no end is too', async () => {
    const far = scenario({ world: { token: { status: 'active', expires_on: new Date(Date.now() + 10 * 86_400_000).toISOString() } } });
    assert.match((await far.go(['check'])).text, /A week at most/);
    const none = scenario({ world: { token: { status: 'active' } } });
    assert.match((await none.go(['check'])).text, /no end date/);
  });
  test('a first move and a first undo refuse with under an hour left; a later run only warns', async () => {
    const soon = { token: { status: 'active', expires_on: new Date(Date.now() + 30 * 60_000).toISOString() } };
    const s = await recorded({ world: soon });
    const r = await s.go(['move']);
    assert.equal(r.code, 1);
    assert.match(r.text, /less than an hour left/);
    // A move that is open: the first undo refuses, a repeated move only warns.
    const open = await recorded();
    const q = await open.go(['move']);
    assert.equal((await open.go(['move', '--confirm', codeOf(q)])).code, 0, open.text());
    open.w.token = soon.token;
    const u = await open.go(['undo']);
    assert.equal(u.code, 1);
    assert.match(u.text, /less than an hour left/);
    const again = await open.go(['move']);
    assert.match(again.text, /Warning: the token has \d+ minutes left/);
  });
});

// ---------------------------------------------------------------- test 2: recorded captures

describe('2: real captures, expected values written by hand', () => {
  test('a real Pages-versus-Worker file comparison: only the AVIF rows differ, and they are known', () => {
    const rows = readFileSync(path.join(HERE, 'fixtures', 'row-0.6', 'wrangler-4.156.0-pages-vs-worker.txt'), 'utf8').split('\n').filter((l) => /^(SAME|KNOWN) /.test(l) && !/ - pages=/.test(l)); // a row with no content type is left out
    const was = {};
    const now = {};
    const type = (t) => (t === '-' ? null : t.split(';')[0].trim());
    for (const l of rows) {
      const m = /^(?:SAME|KNOWN) (\S+) worker=(\d+) (\S+) (\S+) pages=(\d+) ([^ ;]+(?:; [^ ]+)?|-) (\S+)/.exec(l);
      assert.ok(m, l);
      const [, p, ws, wt, wh, ps, pt, ph] = m;
      const isBuild = p.startsWith('/build');
      was[p] = { s: Number(ps), t: type(pt), l: null, h: ph, hd: {}, ...(isBuild ? { c: 'c' } : {}) };
      now[p] = { s: Number(ws), t: type(wt === '-' ? '-' : wt), l: null, h: wh, hd: {}, ...(isBuild ? { c: 'c' } : {}) };
    }
    assert.equal(Object.keys(was).length, 8, 'the excerpt holds eight rows with a content type');
    const diffs = compare(was, now, { change: true, onVersion: false, expect: 'c' });
    // By hand: two .avif rows have a different body hash; the build-state row differs by its hash
    // but is compared by its commit line only; the content types differ only by parameters.
    assert.deepEqual(diffs.map((d) => `${d.path} ${d.field} ${d.known ? 'known' : 'UNKNOWN'}`).sort(), [
      '/_astro/bread-counter.BliTCe4I_2hHVpn.avif body known',
      '/_astro/bread-counter.BliTCe4I_Z1JD8Vd.avif body known',
    ]);
    // The same two rows are unknown when the platform did not change (after an undo).
    assert.equal(compare(was, now, { change: false, onVersion: false, expect: 'c' }).filter((d) => !d.known).length, 2);
  });

  test("the version URL's noindex and missing zone headers are known; on the domain they are not", () => {
    const base = { s: 200, t: 'text/html', l: null, h: 'aa', hd: { 'x-robots-tag': null, nel: 'present', 'strict-transport-security': 'max-age=1' } };
    const ver = { ...base, hd: { 'x-robots-tag': 'noindex', nel: null, 'strict-transport-security': null } };
    const onVersion = compare({ '/': base }, { '/': ver }, { change: true, onVersion: true, expect: 'c' });
    assert.equal(onVersion.length, 3);
    assert.ok(onVersion.every((d) => d.known));
    const onDomain = compare({ '/': base }, { '/': { ...base, hd: { ...base.hd, 'x-robots-tag': 'noindex' } } }, { change: true, onVersion: false, expect: 'c' });
    assert.deepEqual(onDomain.map((d) => [d.field, !!d.known]), [['header x-robots-tag', false]], 'a noindex on the domain is a failure');
  });

  test('a captured GitHub answer: three runs, only the Workers Builds one counts, and it is finished', async () => {
    // The capture (gh 2.103.3, the public trial repository) holds one "Workers Builds: croftweaver-trial"
    // (the stub renames it to the site's Worker) and two Pages runs, all completed. By hand: nothing is
    // unfinished, so the move is not held back.
    const s = await recorded();
    const r = await s.go(['move']);
    assert.equal(r.code, 3, r.text);
    assert.ok(s.w.siteCalls.some((u) => /\/check-runs\?per_page=100&page=1$/.test(u)));
  });

  test('a captured list of one zone and a captured list of eight', async () => {
    const eight = scenario({ world: { zones: JSON.parse(readFileSync(path.join(HERE, 'fixtures', 'cloudflare-api', 'T2-002-zones-list.json'), 'utf8')).response.result } });
    assert.match((await eight.go(['check'])).text, /DNS or settings of 8 zones/);
  });

  test('the Worker-domain answers are made from the API reference, not captured', () => {
    // MADE: see move-stub.mjs. Test 5 settles them against a real account; this test only keeps the
    // statement where the next reader looks.
    assert.match(readFileSync(path.join(HERE, 'move-stub.mjs'), 'utf8'), /Worker domains, the Worker's\n\/\/ deployments and its workers.dev subdomain have no capture/);
  });

  test('the path list holds each page in its other forms, the redirect sources and one missing address', () => {
    const dist = path.join(scratch, 'paths');
    for (const [f, t] of Object.entries(SITE)) { mkdirSync(path.dirname(path.join(dist, f)), { recursive: true }); writeFileSync(path.join(dist, f), t); }
    // By hand from SITE: the home page, /index.html, the about page in three forms, the script, the
    // image, the redirect's source and the address that does not exist.
    assert.deepEqual(pathList(dist), ['/', '/about', '/about/', '/about/index.html', '/app.js', '/croftweaver-move-check-no-such-page', '/index.html', '/old', '/photo.avif']);
    assert.deepEqual(headerNames('/*\n  X-Frame-Options: DENY\n  Content-Security-Policy: x\n'), ['access-control-allow-origin', 'content-security-policy', 'nel', 'report-to', 'strict-transport-security', 'x-frame-options', 'x-robots-tag']);
  });
});

// ---------------------------------------------------------------- test 3: the commands

describe('3: check and record', () => {
  test('check reads and changes nothing, and says where each host is', async () => {
    const s = scenario();
    const r = await s.go(['check']);
    assert.equal(r.code, 0, r.text);
    for (const h of HOSTS) assert.match(r.text, new RegExp(`${h.replace(/\./g, '\\.')}: on Pages`));
    assert.ok(s.w.calls.every((c) => c.method === 'GET'), 'check made a change');
    assert.equal(s.dirty(), '');
    assert.ok(!existsSync(s.stateFile()));
  });

  test('record freezes, builds, compares and keeps the state; the site folder stays clean', async () => {
    const s = scenario();
    const r = await recordDone(s);
    assert.equal(r.code, 0, r.text);
    const st = s.state();
    assert.equal(st.frozen, s.site.frozen);
    assert.deepEqual(st.hosts, HOSTS);
    assert.equal(st.recording.status, 'done');
    assert.equal(st.recording.paths.length, 11, 'the nine addresses of the site and its two build files');
    assert.ok(s.w.calls.every((c) => c.method === 'GET'), 'record made a change');
    assert.equal(s.dirty(), '');
    assert.ok(existsSync(path.join(s.site.work, 'move-run', 'status.html')));
    assert.ok(!existsSync(path.join(path.dirname(s.stateFile()), 'lock')), 'the lock is gone');
  });

  const refusing = [
    ['a Worker that already has a domain', { world: { workerDomains: [{ id: '00000001-0000-4000-8000-000000000000', hostname: 'x.lenas-backstube.example', service: WORKER, zone_id: ZONE.id }] } }, /already has a domain/],
    ['a Direct Upload project', { world: null, mutate: (w) => { delete w.project.source; } }, /No Pages project is built from|Direct Upload/],
    ['an unknown file in functions/', { files: { 'functions/api/x.ts': 'export {}\n' } }, /functions\//],
    ['public/_worker.js', { files: { 'public/_worker.js': 'export default {}\n' } }, /_worker\.js/],
    ['analytics server mode', { files: { 'src/config.ts': "export const PROD_BRANCH = 'production';\nexport const analytics = {\n  mode: 'server',\n};\n" } }, /server mode/],
    ['two Workers configs', { files: { 'other.jsonc': '{ "name": "second", "assets": { "directory": "./dist" } }\n' } }, /2 Workers configs/],
  ];
  for (const [name, o, re] of refusing) {
    test(`record refuses ${name}`, async () => {
      const s = scenario({ site: makeSite({ files: o.files }), world: o.world ?? {} });
      o.mutate?.(s.w);
      const r = await s.go(['record']);
      assert.equal(r.code, 1);
      assert.match(r.text, re);
      assert.ok(s.w.calls.every((c) => c.method === 'GET'));
      assert.ok(!existsSync(s.stateFile()));
    });
  }

  test('record refuses a host with no CNAME to the project, and while main and production differ', async () => {
    const s = scenario();
    s.w.dns = s.w.dns.filter((r) => r.name !== HOSTS[1]);
    const r = await s.go(['record']);
    assert.equal(r.code, 1);
    assert.match(r.text, new RegExp(`${HOSTS[1].replace(/\./g, '\\.')} is on Pages without a CNAME`));
    const t = scenario();
    git(t.site.work, 'commit', '-q', '--allow-empty', '-m', 'ahead');
    git(t.site.work, 'push', '-q', 'origin', 'HEAD:main');
    assert.match((await t.go(['record'])).text, /are not the same commit/);
  });

  test('record refuses while a move is open, and with no state while a host is on the Worker', async () => {
    const open = await recorded();
    const q = await open.go(['move']);
    await open.go(['move', '--confirm', codeOf(q)]);
    const r = await open.go(['record']);
    assert.equal(r.code, 1);
    assert.match(r.text, /A move is open/);
    const bare = scenario();
    bare.w.workerDomains.push({ id: '00000002-0000-4000-8000-000000000000', hostname: HOSTS[0], service: WORKER, zone_id: ZONE.id });
    bare.w.project.domains = bare.w.project.domains.filter((d) => d !== HOSTS[0]);
    bare.w.dns = bare.w.dns.filter((x) => x.name !== HOSTS[0]);
    const b = await bare.go(['record']);
    assert.equal(b.code, 1);
    assert.match(b.text, /already has a domain/);
  });
});

describe('3: move, after and undo', () => {
  test('the whole way: move, push, after passes, undo, push, after closes it', async () => {
    const s = await recorded();
    // The question: nothing changes, a code is printed, the route commit is written and not pushed.
    const q = await s.go(['move']);
    assert.equal(q.code, 3, q.text);
    assert.ok(s.w.calls.every((c) => c.method === 'GET' || c.path.endsWith('/dns_records/export')), 'the question changed something');
    const code = codeOf(q);
    assert.match(code, /^[0-9a-f]{16}$/);
    const route = git(s.site.work, 'rev-parse', 'HEAD');
    assert.notEqual(route, s.site.frozen);
    const cfg = parseJsonc(git(s.site.work, 'show', 'HEAD:workers.jsonc'));
    assert.deepEqual(routesOf(cfg, 'workers.jsonc'), HOSTS);
    assert.match(git(s.site.work, 'show', 'HEAD:workers.jsonc'), /The Worker that serves the built site/, 'the comment survived');
    assert.equal(git(s.site.work, 'rev-parse', 'origin/production'), s.site.frozen, 'the script pushed');
    assert.equal(s.dirty(), '');

    // A wrong code changes nothing.
    const wrong = await s.go(['move', '--confirm', '0'.repeat(16)]);
    assert.equal(wrong.code, 3);
    assert.match(wrong.text, /does not fit this question/);
    assert.equal(s.w.workerDomains.length, 0);

    const go = await s.go(['move', '--confirm', code]);
    assert.equal(go.code, 0, go.text);
    assert.deepEqual(s.w.workerDomains.map((d) => d.hostname).sort(), HOSTS);
    assert.deepEqual(s.w.project.domains, [SUBDOMAIN], 'the hosts left the Pages project');
    assert.equal(s.w.dns.filter((r) => r.type === 'CNAME' && HOSTS.includes(r.name)).length, 0, 'their CNAMEs are gone');
    assert.ok(s.w.calls.filter((c) => c.method !== 'GET').every((c) => ['DELETE', 'PUT'].includes(c.method)));
    assert.equal(s.dirty(), '');

    // after before the push: the tips on GitHub are the frozen commit.
    const early = await s.go(['after']);
    assert.equal(early.code, 1);
    assert.match(early.text, /not the route commit/);
    s.push();
    s.w.pagesCommit = s.w.workerCommit = route;
    const ok = await s.go(['after']);
    assert.equal(ok.code, 0, ok.text);
    assert.match(ok.text, /After passed/);
    assert.equal(s.state().open, true, 'the move stays open so undo works');

    // check in the middle of an open move: the first-move refusals are lifted.
    assert.equal((await s.go(['check'])).code, 0);

    // The way back.
    const uq = await s.go(['undo']);
    assert.equal(uq.code, 3, uq.text);
    const undoCommit = git(s.site.work, 'rev-parse', 'HEAD');
    assert.deepEqual(routesOf(parseJsonc(git(s.site.work, 'show', 'HEAD:workers.jsonc')), 'workers.jsonc'), []);
    const ug = await s.go(['undo', '--confirm', codeOf(uq)]);
    assert.equal(ug.code, 0, ug.text);
    assert.equal(s.w.workerDomains.length, 0);
    assert.deepEqual(s.w.project.domains.filter((d) => HOSTS.includes(d)).sort(), HOSTS);
    assert.deepEqual(s.w.dns.filter((r) => r.type === 'CNAME' && HOSTS.includes(r.name)).map((r) => [r.type, r.content, r.proxied]), [['CNAME', SUBDOMAIN, true], ['CNAME', SUBDOMAIN, true]]);
    assert.deepEqual(s.w.dns.filter((r) => ['MX', 'TXT'].includes(r.type)).map((r) => r.type), ['MX', 'TXT'], 'the apex mail and text records were not touched');
    s.push();
    s.w.pagesCommit = s.w.workerCommit = undoCommit;
    const closed = await s.go(['after']);
    assert.equal(closed.code, 0, closed.text);
    assert.ok(!existsSync(s.stateFile()), 'the state file was renamed when after passed on Pages');
    assert.ok(readdirSync(path.dirname(s.stateFile())).some((f) => /^state-closed-/.test(f)));
    // With the move closed, nothing runs without a new recording.
    for (const cmd of ['move', 'undo', 'after']) {
      const r = await s.go([cmd]);
      assert.equal(r.code, 1);
      assert.match(r.text, /no state file/i);
    }
  });

  // The host list takes a singular or a plural verb. Every message that joins hosts to a verb is read
  // for one host and for two, on the way there and the way back.
  for (const [label, hosts] of [['one host', [HOSTS[0]]], ['two hosts', HOSTS]]) {
    test(`the host list's verbs agree with the number of hosts: ${label}`, async () => {
      const s = scenario();
      s.w.project.domains = s.w.project.domains.filter((d) => d === SUBDOMAIN || hosts.includes(d));
      s.w.dns = s.w.dns.filter((r) => !HOSTS.includes(r.name) || hosts.includes(r.name));
      const rec = await recordDone(s);
      assert.equal(rec.code, 0, rec.text);
      const list = hosts.join(', ');
      const [serve, match, isAre] = hosts.length > 1 ? ['serve', 'match', 'are'] : ['serves', 'matches', 'is'];
      const wrong = hosts.length > 1 ? /\b(serves|matches) /: /\bserve |\bmatch |\bare back\b|\bboth hosts\b/;

      const q = await s.go(['move']);
      assert.equal(q.code, 3, q.text);
      const route = git(s.site.work, 'rev-parse', 'HEAD');
      const go = await s.go(['move', '--confirm', codeOf(q)]);
      assert.equal(go.code, 0, go.text);
      assert.match(go.text, new RegExp(`Done: ${list.replace(/\./g, '\\.')} ${serve} the Worker \\(`));
      assert.doesNotMatch(go.text.split('\n').find((l) => l.startsWith('Done:')), wrong);
      s.push();
      s.w.pagesCommit = s.w.workerCommit = route;
      const ok = await s.go(['after']);
      assert.equal(ok.code, 0, ok.text);
      const passed = ok.text.split('\n').find((l) => l.startsWith('After passed:'));
      assert.equal(passed, `After passed: ${list} ${serve} the Worker and ${match} the recording. The move stays open, so undo works until the Pages project is retired.`);
      // The move stays open, so the token line must not tell her to delete it without a word about undo.
      assert.match(ok.text, /If you will not undo soon, delete the API token now: https:\/\/dash\.cloudflare\.com\/profile\/api-tokens\. An undo later needs a new token, made the same way\./);

      const uq = await s.go(['undo']);
      assert.equal(uq.code, 3, uq.text);
      const undoCommit = git(s.site.work, 'rev-parse', 'HEAD');
      const ug = await s.go(['undo', '--confirm', codeOf(uq)]);
      assert.equal(ug.code, 0, ug.text);
      const done = ug.text.split('\n').find((l) => l.startsWith('Done:'));
      assert.equal(done.replace(/ \(\d+ seconds.*$/, ''), `Done: ${list} ${serve} Pages again`);
      s.push();
      s.w.pagesCommit = s.w.workerCommit = undoCommit;
      const closed = await s.go(['after']);
      assert.equal(closed.code, 0, closed.text);
      assert.match(closed.text, new RegExp(`After passed: ${list.replace(/\./g, '\\.')} ${isAre} back on Pages and ${match} the recording\\. The move is closed`));
      assert.match(closed.text, /Delete the API token now: https:\/\/dash\.cloudflare\.com\/profile\/api-tokens\./);
    });
  }

  test('an unfinished Workers Builds run, or a Pages build in progress, holds move back', async () => {
    const s = await recorded();
    s.w.checkRuns[s.site.frozen] = unfinishedWorkersRun(s.site.frozen);
    const r = await s.go(['move']);
    assert.equal(r.code, 1);
    assert.match(r.text, /Workers Builds is building/);
    s.w.checkRuns = {};
    s.w.pagesDeployments = [deployment('building', { commit: s.site.frozen })];
    const p = await s.go(['move']);
    assert.equal(p.code, 1);
    assert.match(p.text, /Pages is building/);
  });

  test('a private repository without gh stops with a reason, and check says so first', async () => {
    const s = scenario({ world: { githubPrivate: true } });
    const c = await s.go(['check']);
    assert.equal(c.code, 1);
    assert.match(c.text, /private/);
    const m = await recorded({ world: { githubPrivate: true } });
    const r = await m.go(['move']);
    assert.equal(r.code, 1);
    assert.match(r.text, /private/);
  });

  test('a dirty tree, staged or not, refuses move and undo', async () => {
    const s = await recorded();
    writeFileSync(path.join(s.site.work, 'site', 'index.html'), 'changed');
    assert.match((await s.go(['move'])).text, /working tree has changes/);
    git(s.site.work, 'add', 'site/index.html');
    assert.match((await s.go(['move'])).text, /working tree has changes/);
    git(s.site.work, 'reset', '-q', '--hard');
    writeFileSync(path.join(s.site.work, 'notes.txt'), 'untracked');
    assert.match((await s.go(['move'])).text, /working tree has changes/);
  });

  test('a host that is off both is reported first; the same command finishes it', async () => {
    const s = await recorded();
    const q = await s.go(['move']);
    s.w.refuse['PUT /accounts/:id/workers/domains'] = 500;
    const bad = await s.go(['move', '--confirm', codeOf(q)]);
    assert.equal(bad.code, 1);
    assert.match(bad.text, new RegExp(`${HOSTS[0].replace(/\./g, '\\.')} is now on neither`));
    assert.match(bad.text, /run the same command again at once/i);
    delete s.w.refuse['PUT /accounts/:id/workers/domains'];
    const ok = await s.go(['move', '--confirm', codeOf(q)]);
    assert.equal(ok.code, 0, ok.text);
    assert.deepEqual(s.w.workerDomains.map((d) => d.hostname).sort(), HOSTS);
  });

  // The run stops at once when a change fails or its answer is lost, reads the host back and says where
  // it is; the same command again finishes. Each of a host's three changes, lost before and after it was made.
  // [change, request, where the host is when its answer was lost before the change / after it]
  for (const [what, key, before, after] of [
    ['taking it off Pages', `DELETE /accounts/:id/pages/projects/${REPO}/domains/:x`, 'on Pages', 'on neither'],
    ['deleting its CNAME', 'DELETE /zones/:id/dns_records/:id', 'on neither', 'on neither'],
    ['attaching it to the Worker', 'PUT /accounts/:id/workers/domains', 'on neither', 'on the Worker'],
  ]) {
    for (const applied of [false, true]) {
      test(`a lost answer while ${what}${applied ? ' (the change was made)' : ' (it was not)'}: the report names where the host is, and the same command goes on`, async () => {
        const s = await recorded();
        const q = await s.go(['move']);
        s.w.hang = [{ key, applied }];
        const bad = await s.go(['move', '--confirm', codeOf(q)], { requestMs: 150 });
        assert.equal(bad.code, 1, bad.text);
        assert.ok(bad.text.includes(`${HOSTS[0]} is now ${applied ? after : before}`), bad.text);
        assert.match(bad.text, /run the same command again at once/i);
        const ok = await s.go(['move', '--confirm', codeOf(q)]);
        assert.equal(ok.code, 0, ok.text);
        assert.deepEqual(s.w.workerDomains.map((d) => d.hostname).sort(), HOSTS);
        assert.equal(s.w.dns.filter((r) => r.type === 'CNAME' && HOSTS.includes(r.name)).length, 0);
      });
    }
  }

  test('a host that does not serve in time ends a run with status 4; past 15 minutes it says undo', async () => {
    const s = await recorded();
    const q = await s.go(['move']);
    s.w.slowHosts = new Set([HOSTS[0]]);
    const slow = { runMs: 2500, reserveMs: 100, requestMs: 150 };
    const r = await s.go(['move', '--confirm', codeOf(q)], slow);
    assert.equal(r.code, 4, r.text);
    assert.match(r.text, /Run the same command again/);
    const st = s.state();
    st.track.move[HOSTS[0]].leftAt = new Date(Date.now() - 16 * 60_000).toISOString();
    writeFileSync(s.stateFile(), JSON.stringify(st));
    const late = await s.go(['move', '--confirm', codeOf(q)], slow);
    assert.equal(late.code, 1);
    assert.match(late.text, /past the 15-minute target: undo/);
  });

  test('a host still answered by the platform it left is not counted as served', async () => {
    const s = await recorded();
    const q = await s.go(['move']);
    s.w.stale = { [HOSTS[0]]: 'pages' };
    const r = await s.go(['move', '--confirm', codeOf(q)], { runMs: 6500, reserveMs: 100 });
    assert.equal(r.code, 4, r.text);
    assert.match(r.text, /not every host serves the Worker yet/);
    delete s.w.stale;
    assert.equal((await s.go(['move', '--confirm', codeOf(q)])).code, 0);
  });

  test('after fails on a noindex and on a plain-http answer that is not a redirect', async () => {
    const s = await recorded();
    const q = await s.go(['move']);
    await s.go(['move', '--confirm', codeOf(q)]);
    const route = git(s.site.work, 'rev-parse', 'HEAD');
    s.push();
    s.w.pagesCommit = s.w.workerCommit = route;
    s.w.noindexHosts = new Set([HOSTS[1]]);
    const n = await s.go(['after']);
    assert.equal(n.code, 1);
    assert.match(n.text, /x-robots-tag/);
    delete s.w.noindexHosts;
    s.w.httpPlain = true;
    const h = await s.go(['after']);
    assert.equal(h.code, 1);
    assert.match(h.text, /redirect to https|http:\/\//);
  });
});

describe('3: the state file, the lock and a second checkout', () => {
  test('a state file for another zone, repository, project or Worker is refused', async () => {
    for (const [what, edit, re] of [
      ['zone', (st) => { st.zone.id = 'c0ffee00000000000000000000000099'; }, /belongs to another site/],
      ['repository', (st) => { st.repository = 'someone/else'; }, /belongs to another site/],
      ['Pages project', (st) => { st.pages.name = 'another'; }, /is for the Pages project another/],
      ['Worker', (st) => { st.worker = 'another-worker'; }, /the Worker another-worker/],
    ]) {
      const s = await recorded();
      const st = s.state();
      edit(st);
      writeFileSync(s.stateFile(), JSON.stringify(st));
      const r = await s.go(['move']);
      assert.equal(r.code, 1, what);
      assert.match(r.text, re, what);
      assert.equal(s.w.workerDomains.length, 0);
    }
  });

  test('a lock held by a live run refuses every command and stays', async () => {
    const s = await recorded();
    const lock = path.join(path.dirname(s.stateFile()), 'lock');
    writeFileSync(lock, `${process.pid}\nabc\n`);
    for (const cmd of [['move'], ['undo'], ['after']]) {
      const r = await s.go(cmd);
      assert.equal(r.code, 1, cmd.join(' '));
      assert.match(r.text, /Another run \(process \d+\) holds/);
      assert.ok(existsSync(lock), 'the other run\'s lock was removed');
    }
    assert.equal(readFileSync(lock, 'utf8'), `${process.pid}\nabc\n`, 'the live run\'s lock is untouched');
  });

  test('BUG B: the lock of a run that was killed is taken over, with one line, and the same command goes on', async () => {
    const s = await recorded();
    const lock = path.join(path.dirname(s.stateFile()), 'lock');
    const dead = spawnSync(process.execPath, ['-e', '']).pid; // a process that has ended
    for (const body of [`${dead}\nabc\n`, '']) { // a killed run's lock, and one cut off before it wrote its pid
      writeFileSync(lock, body);
      const r = await s.go(['move']);
      assert.equal(r.code, 3, r.text);
      assert.equal(r.out.filter((l) => /^Took over the lock of a run that no longer exists/.test(l)).length, 1);
      assert.ok(!existsSync(lock), 'the run released the lock it took');
    }
  });

  test('G1: a lock is never visible without its pid, so a second run cannot take a live lock for a dead one', async () => {
    const mod = path.join(HERE, '..', 'move-to-workers.mjs');
    const dir = mkdtempSync(path.join(tmpdir(), 'move-lock-'));
    const file = path.join(dir, 'lock');
    const run = (src) => new Promise((resolve) => execFile(process.execPath, ['--input-type=module', '-e', src], (err, out) => resolve(out.trim())));
    // One process takes and drops the lock over and over; another reads the file as fast as it can and counts empty reads.
    const taker = run(`import(${JSON.stringify(mod)}).then(async (m) => { const run = {}; for (let i = 0; i < 1500; i++) { m.takeLock(${JSON.stringify(dir)}, run, () => {}); run.release(); } console.log('end'); });`);
    const reader = run(`import { readFileSync } from 'node:fs'; let empty = 0, seen = 0; const until = Date.now() + 4000; while (Date.now() < until) { try { if (readFileSync(${JSON.stringify(file)}, 'utf8') === '') empty++; else seen++; } catch {} } console.log(empty + ' ' + seen);`);
    const [, counts] = await Promise.all([taker, reader]);
    rmSync(dir, { recursive: true, force: true });
    const [empty, seen] = counts.split(' ').map(Number);
    assert.ok(seen > 0, 'the reader never saw the lock: the test proves nothing');
    assert.equal(empty, 0, `the lock was read empty ${empty} times`);
  });

  test('G1: runs that start at the same instant on a dead lock: exactly one takes it', async () => {
    const mod = path.join(HERE, '..', 'move-to-workers.mjs');
    const dead = spawnSync(process.execPath, ['-e', '']).pid;
    // Each child waits for a shared start time, then takes the lock and stays alive, so a lock taken is a lock held.
    const child = (dir, at) => new Promise((resolve) => {
      const src = `import(${JSON.stringify(mod)}).then((m) => { while (Date.now() < ${at}); let got = false; try { m.takeLock(${JSON.stringify(dir)}, {}, () => {}); got = true; } catch {} console.log(got ? 'GOT' : 'NO'); setTimeout(() => {}, 1500); });`;
      execFile(process.execPath, ['--input-type=module', '-e', src], (err, out) => resolve(out.trim()));
    });
    for (let round = 0; round < 4; round++) {
      const dir = mkdtempSync(path.join(tmpdir(), 'move-lock-'));
      writeFileSync(path.join(dir, 'lock'), `${dead}\nabc\n`);
      const outs = await Promise.all(Array.from({ length: 6 }, () => child(dir, Date.now() + 1500)));
      assert.equal(outs.filter((o) => o === 'GOT').length, 1, `round ${round}: ${outs.join(' ')}`);
      assert.deepEqual(readdirSync(dir).filter((n) => n !== 'lock'), [], 'no stale file is left behind');
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("a run never removes a lock that another run put in its place", async () => {
    const s = await recorded();
    const lock = path.join(path.dirname(s.stateFile()), 'lock');
    let tampered = false;
    const spy = (cmd, args, o) => { if (!tampered && existsSync(lock)) { writeFileSync(lock, '999999\nsomeone-else\n'); tampered = true; } return runProgram(cmd, args, o); };
    await s.go(['move'], { run: spy });
    assert.ok(tampered, 'the spy never saw the lock');
    assert.equal(readFileSync(lock, 'utf8'), '999999\nsomeone-else\n');
  });

  test('the route commit is written once, and a plain undo in a clone with no routes writes nothing', async () => {
    const s = await recorded();
    const q = await s.go(['move']);
    const head = git(s.site.work, 'rev-parse', 'HEAD');
    await s.go(['move']);
    assert.equal(git(s.site.work, 'rev-parse', 'HEAD'), head, 'a second plain move wrote another commit');
    assert.equal(git(s.site.work, 'rev-list', '--count', `${s.site.frozen}..HEAD`), '1');
    assert.match(s.text(), /already has the right routes/);
    await s.go(['move', '--confirm', codeOf(q)]);
    const clone = path.join(s.site.dir, 'clone2');
    git(s.site.dir, 'clone', '-q', slash(s.site.origin), clone);
    git(clone, 'remote', 'set-url', 'origin', REMOTE);
    git(clone, 'config', `url.${slash(s.site.origin)}.insteadOf`, REMOTE);
    git(clone, 'checkout', '-q', 'production');
    const u = await s.go(['undo'], { cwd: clone });
    assert.equal(u.code, 3, u.text);
    assert.equal(git(clone, 'rev-parse', 'HEAD'), s.site.frozen, 'plain undo wrote a commit where HEAD had no routes');
    assert.match(u.text, /already has the right routes/);
    assert.equal(s.state().asked.commit, s.site.frozen, 'the run records the commit it points at as asked, not confirmed');
    assert.equal(s.state().route.kind, 'route', 'after still goes by the last confirmed direction');
  });

  test('deleting move-run/ changes nothing: after still works', async () => {
    const s = await recorded();
    const q = await s.go(['move']);
    await s.go(['move', '--confirm', codeOf(q)]);
    s.push();
    s.w.pagesCommit = s.w.workerCommit = git(s.site.work, 'rev-parse', 'HEAD');
    rmSync(path.join(s.site.work, 'move-run'), { recursive: true, force: true });
    const r = await s.go(['after']);
    assert.equal(r.code, 0, r.text);
  });

  test('in a fresh clone the state is found; --confirm refuses until that checkout has the route commit', async () => {
    const s = await recorded();
    const q = await s.go(['move']);
    const code = codeOf(q);
    const clone = path.join(s.site.dir, 'clone');
    git(s.site.dir, 'clone', '-q', slash(s.site.origin), clone);
    git(clone, 'remote', 'set-url', 'origin', REMOTE);
    git(clone, 'config', `url.${slash(s.site.origin)}.insteadOf`, REMOTE);
    git(clone, 'checkout', '-q', 'production');
    const there = await s.go(['move', '--confirm', code], { cwd: clone });
    assert.equal(there.code, 1);
    assert.match(there.text, /does not list exactly the hosts/);
    assert.equal(s.w.workerDomains.length, 0, 'nothing changed');
  });

  test('undo and after with no state say so; undo before any move is refused', async () => {
    const s = scenario();
    for (const cmd of ['undo', 'after', 'move']) {
      const r = await s.go([cmd]);
      assert.equal(r.code, 1);
      assert.match(r.text, /no state file/i);
    }
    const rec = await recorded();
    assert.match((await rec.go(['undo'])).text, /No move is open/);
  });

  test('no program the script starts gets the token, and the build runs without it', async () => {
    const s = scenario();
    const seen = [];
    const spy = (cmd, args, o) => { seen.push({ cmd, env: o.env }); return runProgram(cmd, args, o); };
    const r = await recordDone({ ...s, go: (a) => s.go(a, { run: spy }) });
    assert.equal(r.code, 0, r.text);
    assert.ok(seen.length > 5, 'git was run through the spy');
    for (const { cmd, env } of seen) {
      assert.ok(!('CLOUDFLARE_API_TOKEN' in env), `${cmd} got CLOUDFLARE_API_TOKEN`);
      assert.ok(!Object.values(env).includes(TOKEN), `${cmd} got the token under another name`);
    }
    // The detached build ran the site's build.mjs, which exits 9 when the token is in its environment.
    assert.equal(s.state().recording.status, 'done');
  });

  test('the program as the assistant runs it: --help, a wrong command, and the exit codes', async () => {
    const run = (args, cwd) => new Promise((resolve) => execFile(process.execPath, [path.join(SCRIPTS, 'move-to-workers.mjs'), ...args], { cwd, env: { ...gitEnv, CLOUDFLARE_API_TOKEN: '' } }, (err, stdout, stderr) => resolve({ code: err ? err.code : 0, stdout, stderr })));
    const real = await run(['--help'], scratch);
    assert.equal(real.code, 0);
    assert.match(real.stdout, /Usage: node move-to-workers\.mjs/);
    assert.equal((await run(['frobnicate'], scratch)).code, 2);
    const outside = await run(['check'], scratch);
    assert.equal(outside.code, 1);
    assert.match(outside.stdout, /not a git repository/);
    const s = scenario();
    assert.equal((await s.go(['--help'])).code, 0);
    assert.equal((await s.go(['frobnicate'])).code, 2);
    assert.equal((await s.go(['check', '--confirm', 'abc'])).code, 2);
    assert.equal((await s.go(['move', '--confirm'])).code, 2);
  });
});

describe('3: the confirm code and the config edit', () => {
  test('the confirm code follows the end state, not the time', () => {
    const a = { kind: 'move', hosts: HOSTS, commit: 'abc' };
    assert.equal(confirmCode(a), confirmCode({ ...a }));
    assert.notEqual(confirmCode(a), confirmCode({ ...a, commit: 'abd' }));
    assert.notEqual(confirmCode(a), confirmCode({ ...a, kind: 'undo' }));
  });

  test('routes are written as custom domains, comments and trailing commas survive, and the edit can be undone', () => {
    const text = '{\n  // keep me\n  "name": "w",\n  "assets": { "directory": "./dist" }, /* and me */\n}\n';
    const routed = setRoutes(text, HOSTS);
    assert.match(routed, /keep me/);
    assert.match(routed, /and me/);
    assert.deepEqual(routesOf(parseJsonc(routed), 'w.jsonc'), HOSTS);
    const back = setRoutes(routed, []);
    assert.deepEqual(parseJsonc(back).routes, []);
    assert.deepEqual(parseJsonc(blankJsonc(text)), parseJsonc(text));
    assert.throws(() => routesOf({ routes: ['lenas-backstube.example/*'] }, 'w.jsonc'), Stop);
  });
});

// ---------------------------------------------------------------- test 4: the status page

describe('4: the status page', () => {
  const template = readFileSync(path.join(SCRIPTS, 'move-status.html'), 'utf8');
  const hostile = '<script>alert(1)</script> " onmouseover=x \' onmouseover=y &amp;';
  const model = (over = {}) => ({
    stages: [['Prepare', 'a'], ['Freeze', 'b'], ['Switch', 'c'], ['Check', 'd'], ['Clean up', 'e']], stage: 3, site: 'lenas-backstube.example: lena-example/lenas-backstube', updated: '2026-11-03T10:00:00Z',
    command: 'node move-to-workers.mjs move', result: 'finished', hosts: [{ name: HOSTS[0], where: 'on the Worker', since: null }], checks: [{ ok: true, text: 'fine' }, { ok: false, text: 'broken' }],
    differences: [], next: 'node move-to-workers.mjs after', undo: 'Undo works.', ...over,
  });

  test('every stage and host state renders, with the current stage marked', () => {
    for (let stage = 1; stage <= 5; stage++) {
      const html = renderStatus(template, model({ stage }));
      assert.equal((html.match(/you are here/g) ?? []).length, 1);
      assert.match(html, new RegExp(`<li class="now"><strong>${stage}\\. `));
    }
    for (const where of ['on Pages', 'on the Worker', 'on neither (down)', 'on both (inconsistent)']) assert.ok(renderStatus(template, model({ hosts: [{ name: HOSTS[0], where, since: null }] })).includes(esc(where)), where);
    assert.match(renderStatus(template, model({ hosts: [] })), /No host is known yet/);
    assert.ok(!/\{\{/.test(renderStatus(template, model())), 'a placeholder was left');
  });

  test('values with markup, quotes and entities are escaped in text and in attributes', () => {
    const html = renderStatus(template, model({
      result: `stopped: ${hostile}`, next: hostile, undo: hostile, site: hostile, command: hostile,
      hosts: [{ name: hostile, where: hostile, since: hostile }], checks: [{ ok: false, text: hostile }],
      differences: [{ host: HOSTS[0], path: `/a"b'c<d>&amp;`, field: hostile, expected: hostile, got: hostile }],
    }));
    assert.ok(!/<script/i.test(html), 'a script tag got through');
    assert.ok([...html.matchAll(/<[^>]*>/g)].every((m) => !/onmouseover/.test(m[0])), 'an attribute got through');
    assert.ok(html.includes('&lt;script&gt;'));
    assert.ok(html.includes('&amp;amp;'), 'an existing &amp; is shown as typed, not decoded');
    assert.ok(html.includes('title="/a&quot;b&#39;c&lt;d&gt;&amp;amp;"'));
  });

  test('a run that stops writes the page, with the stopped reason escaped', async () => {
    const s = await recorded();
    const q = await s.go(['move']);
    s.w.refuse['PUT /accounts/:id/workers/domains'] = 500;
    s.w.refuseMessage = hostile;
    const r = await s.go(['move', '--confirm', codeOf(q)]);
    assert.equal(r.code, 1);
    const html = readFileSync(path.join(s.site.work, 'move-run', 'status.html'), 'utf8');
    assert.match(html, /you are here/);
    assert.ok(!html.includes('<script>alert'));
    assert.match(html, /neither/);
  });
});

// ---------------------------------------------------------------- the DIFF review's findings (ids B1-B15, R1-R6, N1-N7)

const SRC = readFileSync(path.join(SCRIPTS, 'move-to-workers.mjs'), 'utf8');
const entry = (over = {}) => ({ s: 200, t: 'text/plain', l: null, h: 'aaaa', hd: { 'x-frame-options': 'DENY' }, c: 'abc', ...over });
const statusPage = (s) => readFileSync(path.join(s.site.work, 'move-run', 'status.html'), 'utf8');
const nowStage = (s) => /<li class="now"><strong>(\d)\./.exec(statusPage(s))?.[1];

// move, then --confirm; the commit the move wrote
async function moveAll(s) {
  const T = Date.now(); // a clock that stands still: a slow machine cannot use up the run's time
  const q = await s.go(['move'], { now: () => T });
  const g = await s.go(['move', '--confirm', codeOf(q)], { now: () => T });
  assert.equal(g.code, 0, g.text);
  return git(s.site.work, 'rev-parse', 'HEAD');
}
// push the commit, let both platforms serve it, run after
async function pushAndAfter(s, commit) {
  s.push();
  s.w.pagesCommit = s.w.workerCommit = commit;
  return s.go(['after']);
}
// A move that stops after the first host, because the run has too little time left for the second.
async function halfMoved() {
  const s = await recorded();
  let T = Date.now();
  const q = await s.go(['move'], { now: () => T });
  s.w.onCall = (key) => { if (key === 'PUT /accounts/:id/workers/domains') T += 3000; }; // the first host's last change takes 3 seconds
  const r = await s.go(['move', '--confirm', codeOf(q)], { runMs: 5000, reserveMs: 3500, now: () => T });
  delete s.w.onCall;
  return { s, r };
}
const cloneOf = (s, name) => {
  const clone = path.join(s.site.dir, name);
  git(s.site.dir, 'clone', '-q', slash(s.site.origin), clone);
  git(clone, 'remote', 'set-url', 'origin', REMOTE);
  git(clone, 'config', `url.${slash(s.site.origin)}.insteadOf`, REMOTE);
  git(clone, 'checkout', '-q', 'production');
  return clone;
};

describe('review: records, state and the lock', () => {
  test('B3: a recording that ended unknown, or was made against another Worker version, starts again', async () => {
    const stale = scenario();
    stale.w.pagesCommit = 'a'.repeat(40); // the domain serves a commit that is not the frozen one
    const bad = await recordDone(stale);
    assert.equal(bad.code, 1, bad.text);
    stale.w.pagesCommit = stale.site.frozen;
    const good = await recordDone(stale);
    assert.equal(good.code, 0, good.text);

    const other = scenario();
    other.w.workerCommit = 'b'.repeat(40); // the Worker was built from the wrong commit
    assert.equal((await recordDone(other)).code, 1);
    other.w.versionId = 'bbbbbbbb-0000-4000-8000-000000000000'; // the right build is deployed: a new version
    other.w.workerCommit = other.site.frozen;
    const fixed = await recordDone(other);
    assert.equal(fixed.code, 0, fixed.text);
    assert.equal(other.state().recording.workerVersion, other.w.versionId);
  });

  test('B4: the lock comes before the state file is read', async () => {
    for (const cmd of ['move', 'record']) {
      const s = await recorded();
      writeFileSync(s.stateFile(), 'not json');
      const lock = path.join(path.dirname(s.stateFile()), 'lock');
      writeFileSync(lock, `${process.pid}\nabc\n`);
      const r = await s.go([cmd]);
      assert.equal(r.code, 1, cmd);
      assert.match(r.text, /Another run \(process \d+\) holds/, cmd);
      assert.ok(!/not readable JSON/.test(r.text), `${cmd} read the state before it took the lock`);
    }
  });

  test('N2: the hosts of an open move are checked against the zone again', async () => {
    const s = await recorded();
    const st = s.state();
    st.open = true;
    st.hosts = [...st.hosts, 'evil.example.org'];
    writeFileSync(s.stateFile(), JSON.stringify(st));
    const r = await s.go(['check']);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /not in the zone/);
  });

  test('B11: the GitHub pause survives into the next run', async () => {
    const s = await recorded();
    const T = Date.now();
    const first = await s.go(['move'], { pollMs: 60_000, now: () => T });
    assert.equal(first.code, 3, first.text);
    const second = await s.go(['move'], { pollMs: 60_000, now: () => T + 1_000 });
    assert.equal(second.code, 4, second.text);
    assert.match(second.text, /no more than every/);
    assert.equal((await s.go(['move'], { pollMs: 60_000, now: () => T + 61_000 })).code, 3);
  });
});

describe('review: builds on GitHub and Cloudflare', () => {
  test('B5: a Pages build on the second page of deployments holds move back', async () => {
    const s = await recorded();
    s.w.pagesDeployments = [...Array.from({ length: 25 }, () => deployment('built', { commit: s.site.frozen })), deployment('building', { commit: s.site.frozen })];
    const r = await s.go(['move']);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /Pages is building/);
  });

  test('B5: a Workers Builds run on the second page of check runs holds move back', async () => {
    const s = await recorded();
    s.w.checkRuns[s.site.frozen] = [...fillerRuns(s.site.frozen, 110), ...unfinishedWorkersRun(s.site.frozen).filter((c) => c.name.startsWith('Workers Builds'))];
    const r = await s.go(['move']);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /Workers Builds is building/);
  });

  test('R5: where Workers Builds is connected, a pushed commit it has not reported on is unfinished', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    s.push();
    s.w.pagesCommit = s.w.workerCommit = route;
    s.w.checkRuns[route] = withoutWorkersRun(route);
    const r = await s.go(['after']);
    assert.equal(r.code, 4, r.text);
    assert.match(r.text, /has not reported/);
    delete s.w.checkRuns[route];
    assert.equal((await s.go(['after'])).code, 0);

    const by_hand = await recorded();
    by_hand.w.checkRuns[by_hand.site.frozen] = withoutWorkersRun(by_hand.site.frozen); // the Worker is deployed by hand
    const route2 = await moveAll(by_hand);
    by_hand.w.checkRuns[route2] = withoutWorkersRun(route2);
    const ok = await pushAndAfter(by_hand, route2);
    assert.equal(ok.code, 0, ok.text);
  });

  test('R2: undo works after a passed move and many commits of ordinary shipping', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    assert.equal((await pushAndAfter(s, route)).code, 0);
    for (let i = 0; i < 25; i++) git(s.site.work, 'commit', '-q', '--allow-empty', '-m', `ship ${i}`);
    s.push();
    s.w.pagesCommit = s.w.workerCommit = git(s.site.work, 'rev-parse', 'HEAD');
    s.w.siteCalls = [];
    const u = await s.go(['undo']);
    assert.equal(u.code, 3, u.text);
    assert.ok(s.w.siteCalls.filter((x) => x.includes('/check-runs')).length <= 21, 'it asked GitHub about every commit');
  });
});

describe('review: the route commit and the question', () => {
  test('B6/B25: a route or undo commit that changes anything but the routes (against its parent) is refused', async () => {
    const s = await recorded();
    const file = path.join(s.site.work, 'workers.jsonc');
    writeFileSync(file, setRoutes(readFileSync(file, 'utf8'), HOSTS).replace('2026-01-01', '2026-02-02'));
    git(s.site.work, 'commit', '-q', '-am', 'routes and a compatibility date');
    const r = await s.go(['move']);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /changes more in workers\.jsonc than the custom-domain routes/);

    const u = await recorded();
    await moveAll(u);
    const f = path.join(u.site.work, 'workers.jsonc');
    writeFileSync(f, setRoutes(readFileSync(f, 'utf8'), []).replace('2026-01-01', '2026-02-02'));
    git(u.site.work, 'commit', '-q', '-am', 'no routes and a compatibility date');
    const q = await u.go(['undo']);
    assert.equal(q.code, 1, q.text);
    assert.match(q.text, /changes more in workers\.jsonc than the custom-domain routes/);
  });

  test('B12 and B14: the question says Cloudflare is unchanged, and calls 15 minutes a target', async () => {
    const s = await recorded();
    const q = await s.go(['move']);
    assert.equal(q.code, 3);
    assert.match(q.text, /Cloudflare has not been changed yet/);
    assert.match(q.text, /Wrote the route commit/);
    assert.match(q.text, /nothing on Cloudflare has changed/);
    assert.ok(!/Nothing has been changed yet/.test(q.text));
    assert.match(q.text, /target/);
    assert.ok(!/15 minutes at most/.test(q.text));
  });
});

describe('review: partial moves and undo', () => {
  test('R3: a run that stops between hosts says which host has already left its platform', async () => {
    const { s, r } = await halfMoved();
    assert.equal(r.code, 4, r.text);
    assert.ok(r.text.includes(`${HOSTS[0]} has left Pages`), r.text);
    assert.deepEqual(s.w.workerDomains.map((d) => d.hostname), [HOSTS[0]]);
  });

  test('B2: undo after only one host moved finishes, with a track of its own', async () => {
    const { s } = await halfMoved();
    const q = await s.go(['undo']);
    assert.equal(q.code, 3, q.text);
    const u = await s.go(['undo', '--confirm', codeOf(q)]);
    assert.equal(u.code, 0, u.text);
    assert.equal(s.w.workerDomains.length, 0);
    const st = s.state();
    assert.ok(st.track.undo[HOSTS[0]].leftAt && st.track.move[HOSTS[0]].leftAt, 'each direction keeps its own times');
    assert.equal(st.track.undo[HOSTS[1]]?.leftAt, undefined, 'the host that never left has no time');
  });

  test('R6: an undo that stopped before any host moved back still refuses a token with under an hour left', async () => {
    const s = await recorded();
    await moveAll(s);
    const uq = await s.go(['undo']);
    s.w.refuse['DELETE /accounts/:id/workers/domains/:x'] = 500; // the first change fails: no host has moved back
    const stopped = await s.go(['undo', '--confirm', codeOf(uq)]);
    assert.equal(stopped.code, 1, stopped.text);
    delete s.w.refuse['DELETE /accounts/:id/workers/domains/:x'];
    s.w.token.expires_on = new Date(Date.now() + 30 * 60_000).toISOString().replace(/\.\d+Z$/, 'Z');
    const again = await s.go(['undo', '--confirm', codeOf(uq)]);
    assert.equal(again.code, 1, again.text);
    assert.match(again.text, /less than an hour/);
  });

  test('N7: a plain move in a fresh clone writes the route commit there', async () => {
    const s = await recorded();
    const clone = cloneOf(s, 'clone3');
    const q = await s.go(['move'], { cwd: clone });
    assert.equal(q.code, 3, q.text);
    assert.notEqual(git(clone, 'rev-parse', 'HEAD'), s.site.frozen);
    assert.deepEqual(routesOf(parseJsonc(git(clone, 'show', 'HEAD:workers.jsonc')), 'workers.jsonc'), HOSTS);
    assert.equal(s.state().asked.commit, git(clone, 'rev-parse', 'HEAD'));
  });
});

describe('review: undo and the way a host is counted', () => {
  test('B15: a www that the zone redirects is recorded and checked against itself, never against the version URL', async () => {
    const s = scenario({ world: { wwwRedirect: { from: HOSTS[1], to: HOSTS[0] } } });
    const rec = await recordDone(s);
    assert.equal(rec.code, 0, rec.text);
    assert.equal(s.state().recording.entries[HOSTS[1]]['/build.txt'].s, 301);
    const route = await moveAll(s);
    const a = await pushAndAfter(s, route);
    assert.equal(a.code, 0, a.text);
    s.w.httpTo = { [HOSTS[1]]: HOSTS[1] }; // B8: plain http on www no longer goes where the recording went
    const h = await s.go(['after']);
    assert.equal(h.code, 1, h.text);
    assert.match(h.text, /redirect to https/);
    s.w.httpTo = null;
    assert.equal((await s.go(['after'])).code, 0, 'the recorded zone redirect of http is accepted');
    s.w.wwwRedirect = null; // the redirect stops: www now serves the site, which the recording did not
    const b = await s.go(['after']);
    assert.equal(b.code, 1, b.text);
  });

  test('B13: a host the Workers API puts on the Worker but that Pages still answers fails after', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    s.push();
    s.w.pagesCommit = s.w.workerCommit = route;
    s.w.stale = { [HOSTS[0]]: 'pages' };
    const r = await s.go(['after']);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /answered by Pages/);
  });

  test('B8: after fails when plain http answers 200 as it did when recorded, or goes to another host', async () => {
    const plain = scenario({ world: { httpPlain: true } });
    assert.equal((await recordDone(plain)).code, 0);
    const route = await moveAll(plain);
    const r = await pushAndAfter(plain, route);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /redirect to https/);

    const elsewhere = await recorded();
    const route2 = await moveAll(elsewhere);
    elsewhere.w.httpElsewhere = true;
    assert.equal((await pushAndAfter(elsewhere, route2)).code, 1);
  });

  test('R1: after keeps its answers across runs that end at the time limit', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    s.push();
    s.w.pagesCommit = s.w.workerCommit = route;
    s.w.siteCalls = [];
    s.w.stallAfter = 14;
    const a = await s.go(['after'], { runMs: 1500, requestMs: 5000 });
    assert.equal(a.code, 4, a.text);
    const kept = Object.values(s.state().after.entries).reduce((n, e) => n + Object.keys(e).length, 0);
    assert.ok(kept >= 1, 'nothing was kept');
    s.w.stallAfter = null;
    s.w.siteCalls = [];
    const b = await s.go(['after']);
    assert.equal(b.code, 0, b.text);
    const paths = s.state().recording.paths;
    const fetched = s.w.siteCalls.filter((x) => { const u = new URL(x); return u.protocol === 'https:' && HOSTS.includes(u.hostname) && paths.includes(u.pathname + u.search); }).length;
    assert.equal(fetched + kept, paths.length * HOSTS.length, 'a kept answer was fetched again');
    assert.equal(s.state().after, undefined, 'a finished comparison leaves nothing behind');
  });
});

describe('review: which way after checks, and what it waits for', () => {
  test('B16: a move that stopped, then undone with plain undo and hand steps, closes', async () => {
    const { s } = await halfMoved();
    const q = await s.go(['undo']); // the question: writes the undo commit, changes nothing on Cloudflare
    assert.equal(q.code, 3, q.text);
    s.w.workerDomains = []; // by hand: the host back on Pages, with its CNAME
    s.w.project.domains.push(HOSTS[0]);
    s.w.dns.push({ id: 'd'.padEnd(32, '4'), type: 'CNAME', name: HOSTS[0], content: SUBDOMAIN, proxied: true, ttl: 1 });
    const done = await pushAndAfter(s, git(s.site.work, 'rev-parse', 'HEAD'));
    assert.equal(done.code, 0, done.text);
    assert.ok(readdirSync(path.dirname(s.stateFile())).some((f) => f.startsWith('state-closed-')), 'the move was closed');
  });

  test('B16: an undo that stopped, then a plain move, ends with after checking the Worker', async () => {
    const s = await recorded();
    await moveAll(s);
    const uq = await s.go(['undo']);
    s.w.refuse['DELETE /accounts/:id/workers/domains/:x'] = 500; // the first change fails: every host is still on the Worker
    const stopped = await s.go(['undo', '--confirm', codeOf(uq)]);
    assert.equal(stopped.code, 1, stopped.text);
    delete s.w.refuse['DELETE /accounts/:id/workers/domains/:x'];
    const fwd = await s.go(['move']); // go forward: every host is still on the Worker
    assert.equal(fwd.code, 3, fwd.text);
    const done = await pushAndAfter(s, git(s.site.work, 'rev-parse', 'HEAD'));
    assert.equal(done.code, 0, done.text);
    assert.ok(s.state().open && s.state().base === s.state().route.commit, 'the move stays open and passed');
  });

  test('R5: an undo commit pushed over a route commit that was never pushed is not held for the route commit', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    const uq = await s.go(['undo']);
    assert.equal((await s.go(['undo', '--confirm', codeOf(uq)])).code, 0);
    s.w.checkRuns[route] = withoutWorkersRun(route); // the route commit was never built: it was never pushed alone
    const r = await pushAndAfter(s, git(s.site.work, 'rev-parse', 'HEAD'));
    assert.equal(r.code, 0, r.text);
  });
});

describe('review: the status page and check', () => {
  test('B10: the status page shows where the hosts are now, not where they were last tracked', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    s.push();
    s.w.pagesCommit = s.w.workerCommit = route;
    s.w.workerDomains = s.w.workerDomains.filter((d) => d.hostname !== HOSTS[0]); // someone put the host back on Pages
    s.w.project.domains.push(HOSTS[0]);
    s.w.dns.push({ id: 'd'.padEnd(32, '3'), type: 'CNAME', name: HOSTS[0], content: SUBDOMAIN, proxied: true, ttl: 1 });
    const r = await s.go(['after']);
    assert.equal(r.code, 1, r.text);
    assert.ok(statusPage(s).includes(`<td>${HOSTS[0]}</td><td>on Pages</td>`), 'the page shows the old tracking');
  });

  test('N3: the stage the page marks follows the move', async () => {
    const s = await recorded();
    await s.go(['move']);
    assert.equal(nowStage(s), '2', 'a question changes nothing yet');
    const route = await moveAll(s);
    assert.equal(nowStage(s), '3');
    await s.go(['after']);
    assert.equal(nowStage(s), '4', 'after was run and failed');
    assert.equal((await pushAndAfter(s, route)).code, 0);
    assert.equal(nowStage(s), '5', 'a passed move leaves clean-up');
  });

  test('N4: check names a private repository first, and in an open move points to after', async () => {
    const s = scenario({ world: { githubPrivate: true, workerDomains: [{ id: '00000001-0000-4000-8000-000000000000', hostname: 'x.lenas-backstube.example', service: WORKER, zone_id: ZONE.id }] } });
    const c = await s.go(['check']);
    assert.equal(c.code, 1);
    assert.match(c.text, /private/);
    assert.ok(!/already has a domain/.test(c.text), 'the private repository came second');

    const o = await recorded();
    await moveAll(o);
    const open = await o.go(['check']);
    assert.equal(open.code, 0);
    assert.match(open.text, /expects the route commit [0-9a-f]{7}/, 'B17: check names the commit the open move waits for');
    assert.ok(statusPage(o).includes('node move-to-workers.mjs after'), 'the next step of an open move is after');
  });

  test('N5: a run that stops before the state was read marks no stage on the page', async () => {
    const s = await recorded();
    await moveAll(s);
    s.w.token.expires_on = new Date(Date.now() + 10 * 86_400_000).toISOString().replace(/\.\d+Z$/, 'Z');
    const r = await s.go(['check']);
    assert.equal(r.code, 1, r.text);
    assert.ok(!statusPage(s).includes('class="now"'), 'the page says "you are here" for a move it never read');
  });

  test('B8: the status page links an http difference to its http address', () => {
    const template = readFileSync(path.join(SCRIPTS, 'move-status.html'), 'utf8');
    const html = renderStatus(template, {
      stages: [['Prepare', 'a']], stage: 1, site: 'x', updated: 'y', command: 'z', result: 'r', hosts: [], checks: [], next: 'n', undo: 'u',
      differences: [{ host: HOSTS[0], path: 'http://', field: 'redirect to https', expected: '301', got: '200' }],
    });
    assert.ok(html.includes(`href="http://${HOSTS[0]}/"`), html);
    assert.ok(!html.includes(`https://${HOSTS[0]}http://`));
  });
});

describe('review: comparing', () => {
  const OPTS = { change: false, onVersion: false, expect: 'abc' };

  test('B7: the build files differ in their body only; everything else is compared', () => {
    const was = { '/build.txt': entry() };
    assert.deepEqual(compare(was, { '/build.txt': entry({ h: 'bbbb' }) }, OPTS), [], 'the body of a build file differs by design');
    for (const [what, over, field] of [['media type', { t: 'text/html' }, 'media type'], ['Location', { l: '/x' }, 'Location'], ['a header', { hd: { 'x-frame-options': null } }, 'header x-frame-options'], ['status', { s: 404 }, 'status'], ['commit line', { c: 'zzz' }, 'commit line']]) {
      const d = compare(was, { '/build.txt': entry(over) }, OPTS);
      assert.ok(d.some((x) => x.field === field && !x.known), what);
    }
  });

  test('B9: access-control-allow-origin is a known difference when the platform changed, and nowhere else', () => {
    assert.ok(headerNames('').includes('access-control-allow-origin'));
    const pages = { '/a': entry({ hd: { 'access-control-allow-origin': '*' } }) };
    const worker = { '/a': entry({ hd: { 'access-control-allow-origin': null } }) };
    const moved = compare(pages, worker, { ...OPTS, change: true });
    assert.equal(moved.length, 1);
    assert.ok(moved[0].known);
    const same = compare(pages, worker, OPTS);
    assert.ok(same.length === 1 && !same[0].known, 'the platform did not change');
    const more = compare(pages, { '/a': entry({ t: 'text/html', hd: { 'access-control-allow-origin': null } }) }, { ...OPTS, change: true });
    assert.ok(more.some((d) => d.field === 'media type' && !d.known), 'only that field is excused');
  });

  test('N1: no regular expression is built from a variable', () => {
    assert.ok(!/new RegExp\(/.test(SRC));
  });
});

// ---------------------------------------------------------------- round 2 of the DIFF review

// A clock the test moves: `sleep` advances it, and nothing else does.
const mockClock = () => { const c = { t: Date.now(), now: () => c.t, sleep: async (ms) => { await yielding(); c.t += ms; } }; return c; };
// A run that ends in a few seconds of that clock when a host does not serve.
const shortRun = (c) => ({ now: c.now, sleep: c.sleep, runMs: 4000, goodGapMs: 1000, reserveMs: 100 });
const frozenClock = () => { const T = Date.now(); return { now: () => T }; };
// push HEAD and let both platforms serve it
function shipHead(s) {
  s.push();
  const tip = git(s.site.work, 'rev-parse', 'HEAD');
  s.w.pagesCommit = s.w.workerCommit = tip;
  return tip;
}
function ship(s, n) {
  for (let i = 0; i < n; i++) git(s.site.work, 'commit', '-q', '--allow-empty', '-m', `ship ${i}`);
  return shipHead(s);
}
const dotted = (h) => h.replace(/\./g, '\\.');
// A confirm run whose first change takes 40 seconds of the run's 55: the host in hand is finished, and
// the next has not the 20 seconds a host needs here. The hook stays on the stub until deleted.
function slowFirstHost(s) {
  let T = Date.now();
  let jumped = false;
  s.w.onCall = (key) => { if (!jumped && !key.startsWith('GET')) { jumped = true; T += 40_000; } };
  return { now: () => T, reserveMs: 20_000 };
}

describe('test 5: what the throwaway showed (the version URL\'s NEL, a redirect\'s body)', () => {
  const CAPTURE = JSON.parse(readFileSync(path.join(HERE, 'fixtures', 'pages-vs-worker-headers', 'redirect-old-page-2026-11-05.json'), 'utf8'));
  const answer = (a) => ({ status: a.status, headers: a.headers, body: a.body });
  const kit = (world = {}) => scenario({
    site: makeSite({ files: { 'site/_redirects': `${CAPTURE.path} /privacy 301\n` } }),
    world: { domainNoNel: true, captured: { pages: { [CAPTURE.path]: answer(CAPTURE.domain_on_pages) }, version: { [CAPTURE.path]: answer(CAPTURE.version_url_of_the_worker) }, worker: { [CAPTURE.path]: answer(CAPTURE.domain_on_the_worker) } }, ...world },
  });
  // record, move, push the route commit, let both platforms serve it, then run `after`
  async function moved(s) {
    assert.equal((await recordDone(s)).code, 0, s.text());
    const q = await s.go(['move']);
    assert.equal((await s.go(['move', '--confirm', codeOf(q)])).code, 0, s.text());
    s.push();
    s.w.pagesCommit = s.w.workerCommit = git(s.site.work, 'rev-parse', 'HEAD');
  }

  test('record accepts the captured redirect: NEL only on the version URL, and a body only from Pages', async () => {
    // By hand, from the capture: Pages sends text/plain and 23 bytes, the Worker none; only the version
    // URL has nel and report-to; status 301 and Location /privacy on both.
    assert.equal(CAPTURE.domain_on_pages.headers['content-type'], 'text/plain;charset=UTF-8');
    assert.equal(CAPTURE.version_url_of_the_worker.headers['content-type'], undefined);
    assert.ok(!('nel' in CAPTURE.domain_on_pages.headers) && 'nel' in CAPTURE.version_url_of_the_worker.headers);
    const s = kit();
    const r = await recordDone(s);
    assert.equal(r.code, 0, r.text);
    assert.match(r.text, /, 0 unknown\./);
    assert.ok(!('unknown' in s.state().recording), 'nothing is left unknown in the state file');
  });

  test('after accepts the Worker\'s captured redirect on the domain: no body, no type, same Location, noindex on both', async () => {
    // By hand, from the capture: on the domain the Worker sends the same 301 and Location as Pages, with
    // content-length 0 and no content-type (Pages: text/plain, 23 bytes), and no NEL; x-robots-tag
    // noindex is on Pages' answer too, so it is no change.
    const dom = CAPTURE.domain_on_the_worker;
    assert.equal(dom.status, CAPTURE.domain_on_pages.status);
    assert.equal(dom.headers.location, '/privacy');
    assert.equal(dom.headers['content-length'], '0');
    assert.ok(!('content-type' in dom.headers) && !('nel' in dom.headers));
    assert.equal(dom.headers['x-robots-tag'], 'noindex');
    assert.equal(CAPTURE.domain_on_pages.headers['x-robots-tag'], 'noindex');
    const s = kit();
    await moved(s);
    const r = await s.go(['after']);
    assert.equal(r.code, 0, r.text);
    assert.doesNotMatch(r.text, /unknown:/);
  });

  test('after: the same captured redirect with another Location on the domain is a failure', async () => {
    const wrong = answer(CAPTURE.domain_on_the_worker);
    wrong.headers = { ...wrong.headers, location: '/somewhere-else' };
    const s = kit({ captured: { pages: { [CAPTURE.path]: answer(CAPTURE.domain_on_pages) }, version: { [CAPTURE.path]: answer(CAPTURE.version_url_of_the_worker) }, worker: { [CAPTURE.path]: wrong } } });
    await moved(s);
    const r = await s.go(['after']);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /unknown: \S+\/old-page Location: \/privacy ≠ \/somewhere-else/);
  });

  test('a redirect whose Location differs on the Worker stays unknown, with its body and type', async () => {
    const wrong = answer(CAPTURE.version_url_of_the_worker);
    wrong.headers = { ...wrong.headers, location: '/somewhere-else' };
    const s = kit({ captured: { pages: { [CAPTURE.path]: answer(CAPTURE.domain_on_pages) }, version: { [CAPTURE.path]: wrong } } });
    const r = await recordDone(s);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /unknown: \S+\/old-page Location: \/privacy ≠ \/somewhere-else/);
    assert.match(r.text, /unknown: \S+\/old-page body/);
  });

  test('compare: the rules are narrow', () => {
    const redirect = (over = {}) => ({ s: 301, t: 'text/plain', l: '/privacy', h: 'aa', hd: { nel: null, 'report-to': null }, ...over });
    const OPT = { change: true, onVersion: true, expect: 'c' };
    const worker = redirect({ t: null, h: EMPTY_BODY, hd: { nel: 'present', 'report-to': 'present' } });
    const known = compare({ '/r': redirect() }, { '/r': worker }, OPT);
    assert.deepEqual(known.map((d) => `${d.field} ${d.known ? 'known' : 'UNKNOWN'}`).sort(), ['body known', 'header nel known', 'header report-to known', 'media type known']);
    // The platform did not change (after an undo): a redirect body is not excused.
    assert.ok(compare({ '/r': redirect() }, { '/r': worker }, { ...OPT, change: false, onVersion: false }).every((d) => !d.known));
    // On the domain NEL is a failure: after a move the zone's setting must still be what it was.
    const onDomain = compare({ '/r': redirect() }, { '/r': redirect({ hd: { nel: 'present', 'report-to': null } }) }, { ...OPT, onVersion: false });
    assert.deepEqual(onDomain.map((d) => [d.field, !!d.known]), [['header nel', false]]);
    // A page with a body is not a redirect: its body and type differences stay unknown.
    const page = (over = {}) => ({ s: 200, t: 'text/html', l: null, h: 'aa', hd: {}, ...over });
    assert.deepEqual(compare({ '/p': page() }, { '/p': page({ t: 'text/plain', h: 'bb' }) }, OPT).map((d) => !!d.known), [false, false]);
    // A redirect that became a page, or went to another place, is not excused.
    assert.ok(compare({ '/r': redirect() }, { '/r': page({ t: null, h: 'bb' }) }, OPT).every((d) => !d.known));
    assert.ok(compare({ '/r': redirect() }, { '/r': redirect({ t: null, h: EMPTY_BODY, l: '/x' }) }, OPT).filter((d) => d.field !== 'Location').every((d) => !d.known));
    // C1: no Location on either side is not "the same redirect", whatever the bodies are.
    const bare = (over = {}) => redirect({ l: null, ...over });
    assert.ok(compare({ '/r': bare() }, { '/r': bare({ t: null, h: EMPTY_BODY }) }, OPT).filter((d) => d.field === 'body' || d.field === 'media type').length === 2);
    assert.ok(compare({ '/r': bare() }, { '/r': bare({ t: null, h: EMPTY_BODY }) }, OPT).every((d) => !d.known), 'no Location: nothing is excused');
    // The excuse is the transition seen: the Worker side has an empty body and no media type. A body, or a type, on the Worker side is unknown.
    const withBody = compare({ '/r': redirect() }, { '/r': redirect({ t: null, h: 'bb' }) }, OPT).filter((d) => d.field === 'body' || d.field === 'media type');
    assert.ok(withBody.length === 2 && withBody.every((d) => !d.known), 'a Worker body is not excused');
    const withType = compare({ '/r': redirect() }, { '/r': redirect({ t: 'text/html', h: EMPTY_BODY }) }, OPT);
    assert.deepEqual(withType.map((d) => `${d.field} ${d.known ? 'known' : 'UNKNOWN'}`).sort(), ['body known', 'media type UNKNOWN']);
    // Pages with an empty body too: there is no transition to excuse.
    assert.ok(compare({ '/r': redirect({ h: EMPTY_BODY }) }, { '/r': redirect({ t: null, h: 'bb' }) }, OPT).every((d) => !d.known));
  });

  test('after a move the redirect has no body and the zone sends no NEL, and after passes; a NEL that appeared is a failure', async () => {
    const s = scenario({ world: { domainNoNel: true } });
    assert.equal((await recordDone(s)).code, 0, s.text());
    assert.ok(Object.values(s.state().recording.entries[HOSTS[0]]).some((e) => e.s === 301 && e.t === 'text/plain'), "the recording holds Pages' redirect with its text");
    const q = await s.go(['move']);
    assert.equal((await s.go(['move', '--confirm', codeOf(q)])).code, 0, s.text());
    s.push();
    const route = git(s.site.work, 'rev-parse', 'HEAD');
    s.w.pagesCommit = s.w.workerCommit = route;
    const ok = await s.go(['after']);
    assert.equal(ok.code, 0, ok.text);
    s.w.domainNoNel = false; // the zone starts to send NEL: nothing about the Worker excuses it
    const bad = await s.go(['after']);
    assert.equal(bad.code, 1, bad.text);
    assert.match(bad.text, /unknown: \S+\/ header nel: null ≠ present/);
  });
});

describe('review round 2: time', () => {
  test('B19 and R15: a quick --confirm run does not meet GitHub\'s pause: it reads none, so it neither waits nor stops', async () => {
    const s = await recorded();
    const c = mockClock();
    const io = { pollMs: 30_000, now: c.now, sleep: c.sleep };
    const q = await s.go(['move'], io);
    assert.equal(q.code, 3, q.text);
    c.t += 1_000; // a quick yes
    const t0 = c.t;
    const quick = await s.go(['move', '--confirm', codeOf(q)], io);
    assert.equal(quick.code, 0, quick.text);
    assert.ok(c.t - t0 < 5_000, `it waited ${(c.t - t0) / 1000} seconds`);
    assert.deepEqual(s.w.workerDomains.map((d) => d.hostname).sort(), HOSTS);
  });

  test('B19: a run begun 30 seconds after the last GitHub read has its whole time for a fresh host', async () => {
    const s = await recorded();
    const c = mockClock();
    const io = { pollMs: 30_000, now: c.now, sleep: c.sleep };
    const q = await s.go(['move'], io);
    c.t += 30_000;
    const go = await s.go(['move', '--confirm', codeOf(q)], io);
    assert.equal(go.code, 0, go.text);
  });
});

describe('review round 2: serving, the way a host is counted, the tracks', () => {
  test('B20: after ordinary shipping, undo counts Pages serving a shipped commit as served', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    assert.equal((await pushAndAfter(s, route)).code, 0);
    ship(s, 2); // Pages builds what is shipped, so it now serves a commit the script never wrote
    const q = await s.go(['undo']);
    assert.equal(q.code, 3, q.text);
    const c = mockClock();
    const u = await s.go(['undo', '--confirm', codeOf(q)], shortRun(c));
    assert.equal(u.code, 0, u.text);
  });

  test('B21: a first change that fails leaves no leftAt, so the token rule for a first undo still holds', async () => {
    const s = await recorded();
    await moveAll(s);
    const uq = await s.go(['undo']);
    s.w.refuse['DELETE /accounts/:id/workers/domains/:x'] = 500;
    const bad = await s.go(['undo', '--confirm', codeOf(uq)]);
    assert.equal(bad.code, 1, bad.text);
    assert.equal(s.state().track.undo[HOSTS[0]]?.leftAt, undefined, 'nothing had left the Worker');
    delete s.w.refuse['DELETE /accounts/:id/workers/domains/:x'];
    s.w.token.expires_on = new Date(Date.now() + 30 * 60_000).toISOString().replace(/\.\d+Z$/, 'Z');
    const again = await s.go(['undo', '--confirm', codeOf(uq)]);
    assert.equal(again.code, 1, again.text);
    assert.match(again.text, /less than an hour/);
  });

  test('B22: a www redirect that adds its own parameter and keeps the request\'s is still counted as served', async () => {
    const s = scenario({ world: { wwwRedirect: { from: HOSTS[1], to: HOSTS[0], query: 'source=www', keepQuery: true } } });
    const rec = await recordDone(s);
    assert.equal(rec.code, 0, rec.text);
    assert.equal(s.state().recording.entries[HOSTS[1]]['/build.txt'].l, `https://${HOSTS[0]}/build.txt?source=www`);
    const c = mockClock();
    const q = await s.go(['move'], { now: c.now });
    const g = await s.go(['move', '--confirm', codeOf(q)], shortRun(c));
    assert.equal(g.code, 0, g.text);
    const commit = git(s.site.work, 'rev-parse', 'HEAD');
    const a = await pushAndAfter(s, commit);
    assert.equal(a.code, 0, a.text);
  });

  test('B24: a resumed run that stops before the switch still names a host that has left its platform', async () => {
    const s = await recorded();
    const q = await s.go(['move']);
    s.w.refuse['PUT /accounts/:id/workers/domains'] = 500;
    const bad = await s.go(['move', '--confirm', codeOf(q)]);
    assert.equal(bad.code, 1, bad.text);
    delete s.w.refuse['PUT /accounts/:id/workers/domains'];
    writeFileSync(path.join(s.site.work, 'site', 'index.html'), '<h1>edited</h1>'); // a dirty tree stops the run before the switch
    const held = await s.go(['move', '--confirm', codeOf(q)]);
    assert.equal(held.code, 1, held.text);
    assert.match(held.text, /working tree has changes/);
    assert.ok(held.text.includes(`${HOSTS[0]} has left Pages; last read: on neither`), held.text);
  });

  test('N12: when the read-back after a failed change fails too, the page says unknown, not the earlier read', async () => {
    const s = await recorded();
    const q = await s.go(['move']);
    const put = 'PUT /accounts/:id/workers/domains';
    s.w.hang = [{ key: put, applied: true }]; // the answer is lost, the change was made
    s.w.onCall = (key) => { if (key === put) s.w.refuse['GET /accounts/:id/workers/domains'] = 500; }; // and the read-back fails
    const bad = await s.go(['move', '--confirm', codeOf(q)], { requestMs: 150 });
    assert.equal(bad.code, 1, bad.text);
    assert.ok(bad.text.includes('it could not be read back'), bad.text);
    assert.ok(new RegExp(`${dotted(HOSTS[0])}</td><td>unknown`).test(statusPage(s)), 'the page does not show the earlier read');
  });
});

describe('review round 2: lists and counts', () => {
  test('B23: a later page that comes back empty before the count is reached refuses, for deployments and for check runs', async () => {
    const s = await recorded();
    s.w.pagesDeployments = Array.from({ length: 30 }, () => deployment('built', { commit: s.site.frozen }));
    s.w.depEmptyAfterFirst = true;
    const d = await s.go(['move']);
    assert.equal(d.code, 1, d.text);
    assert.match(d.text, /came back empty at page 2/);
    const g = await recorded();
    g.w.checkRuns[g.site.frozen] = fillerRuns(g.site.frozen, 150);
    g.w.ghEmptyAfterFirst = true;
    const c = await g.go(['move']);
    assert.equal(c.code, 1, c.text);
    assert.match(c.text, /ended at 100 of 150/);
  });

  test('N14: a zone list that does not say how many pages it has refuses', async () => {
    const s = scenario({ world: { extraZones: 1, zonesNoPageCount: true } });
    const r = await s.go(['check']);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /how many pages/);
  });

  test('R11: Workers Builds counts as connected when any commit in the range has a run, not only the first', async () => {
    const s = await recorded();
    s.w.checkRuns[s.site.frozen] = withoutWorkersRun(s.site.frozen); // the frozen commit predates Workers Builds
    const route = await moveAll(s);
    s.push();
    s.w.pagesCommit = s.w.workerCommit = route;
    git(s.site.work, 'commit', '-q', '--allow-empty', '-m', 'a later push');
    const c2 = shipHead(s);
    s.w.checkRuns[c2] = withoutWorkersRun(c2); // Workers Builds has not reported on the newest push yet
    const q = await s.go(['undo']);
    assert.equal(q.code, 1, q.text);
    assert.match(q.text, /Workers Builds has not reported on/);
  });

  test('R9: a go-forward after an undo of a long passed move keeps its range base', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    assert.equal((await pushAndAfter(s, route)).code, 0);
    for (let i = 0; i < 25; i++) git(s.site.work, 'commit', '-q', '--allow-empty', '-m', `ship ${i}`);
    s.push(); // the platforms still serve the route commit: that is a commit the script knows
    const uq = await s.go(['undo']);
    assert.equal((await s.go(['undo', '--confirm', codeOf(uq)], frozenClock())).code, 0);
    const mq = await s.go(['move']);
    assert.equal(mq.code, 3, mq.text);
    s.w.stale = { [HOSTS[0]]: 'pages' };
    const c = mockClock();
    const stalled = await s.go(['move', '--confirm', codeOf(mq)], shortRun(c));
    assert.equal(stalled.code, 4, stalled.text);
    delete s.w.stale;
    const again = await s.go(['move', '--confirm', codeOf(mq)], frozenClock());
    assert.equal(again.code, 0, again.text);
  });

  test('N11: an address that got no answer in the run that finishes a recording is asked again, not made a difference', async () => {
    const s = scenario();
    s.w.dropOnce = new Set(['/about']);
    const texts = [];
    let code;
    for (let i = 0; i < 120; i++) {
      const r = await s.go(['record']);
      texts.push(r.text);
      code = r.code;
      if (code !== 4) break;
      await wait(250);
    }
    assert.equal(code, 0, texts.at(-1));
    assert.ok(texts.some((t) => /did not answer/.test(t)), 'one run said so and stopped with status 4');
  });

  test('N11: the same in after', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    s.w.dropOnce = new Set(['/about']);
    const first = await pushAndAfter(s, route);
    assert.equal(first.code, 4, first.text);
    assert.match(first.text, /did not answer/);
    const second = await s.go(['after']);
    assert.equal(second.code, 0, second.text);
  });
});

describe('review round 2: the route commit and which way after checks', () => {
  test('B25: an ordinary edit to workers.jsonc shipped after the move blocks neither undo nor a go-forward', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    assert.equal((await pushAndAfter(s, route)).code, 0);
    const file = path.join(s.site.work, 'workers.jsonc');
    writeFileSync(file, readFileSync(file, 'utf8').replace('2026-01-01', '2026-02-02'));
    git(s.site.work, 'commit', '-q', '-am', 'a newer compatibility date');
    shipHead(s);
    const q = await s.go(['undo']);
    assert.equal(q.code, 3, q.text);
    assert.equal((await s.go(['undo', '--confirm', codeOf(q)], frozenClock())).code, 0);
    const f = await s.go(['move']); // the undo commit sits on top of the edit
    assert.equal(f.code, 3, f.text);
    assert.match(f.text, /Wrote the route commit/);
  });

  test('R12: a declined plain undo does not change which way after checks', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    assert.equal((await pushAndAfter(s, route)).code, 0);
    const q = await s.go(['undo']); // asked, and the User said no
    assert.equal(q.code, 3, q.text);
    const again = await s.go(['after']);
    assert.equal(again.code, 0, again.text);
    assert.equal(s.state().route.kind, 'route');
  });

  test('N10: check in an open move points to after only when every host is where the move ends', async () => {
    const { s } = await halfMoved(); // one host on the Worker, one still on Pages
    const c = await s.go(['check']);
    assert.equal(c.code, 0, c.text);
    assert.ok(!statusPage(s).includes('node move-to-workers.mjs after'), 'a split move is finished first');
    assert.ok(statusPage(s).includes('node move-to-workers.mjs move'));
  });

  test('N15: during an open undo the page says move goes forward, not that there is nothing to undo', async () => {
    const s = await recorded();
    await moveAll(s);
    const uq = await s.go(['undo']);
    s.w.refuse['DELETE /accounts/:id/workers/domains/:x'] = 500;
    const stopped = await s.go(['undo', '--confirm', codeOf(uq)]);
    assert.equal(stopped.code, 1, stopped.text);
    assert.ok(!statusPage(s).includes('There is nothing to undo yet'));
    assert.match(statusPage(s), /move\s+goes forward/);
  });
});

describe('review round 2: check and GitHub', () => {
  test('N9: with gh missing, a private repository is reported as that, with where to get gh', async () => {
    const s = scenario({ world: { githubPrivate: true } });
    const noGh = (cmd, args, o) => runProgram(cmd === 'gh' ? 'croftweaver-no-such-gh' : cmd, args, o);
    const r = await s.go(['check'], { useGh: true, run: noGh });
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /private/);
    assert.match(r.text, /gh \(the GitHub command line\) is not installed/);
    assert.match(r.text, /cli\.github\.com/);
  });
});

// ---------------------------------------------------------------- round 3 of the DIFF review

// T2 (replaces T1): the stub's clock moves with every request, so the run's 55 seconds are spent as
// they are on a real network. A scenario must reach its end in few runs, and no host may stay down
// for two runs in a row.
function lagging(s, c, ms) {
  s.w.latency = { clock: c, ms };
  const lagRun = async (cmd, args, o) => { // a git command that goes to the network takes as long as a request
    if (cmd === 'git' && args[0] === 'ls-remote') await spend(s.w.latency);
    return runProgram(cmd, args, o);
  };
  return { now: c.now, sleep: c.sleep, pollMs: 30_000, run: lagRun };
}
const manyDeployments = (s, n) => { s.w.pagesDeployments = Array.from({ length: n }, (_, i) => ({ ...deployment('built', { commit: s.site.frozen }), id: `d${String(i).padStart(7, '0')}-0000-4000-8000-000000000000` })); };
// Runs a command as a person would: again whenever it says so, after the wait it names.
async function drive(s, c, args, ms, max = 6) {
  const io = lagging(s, c, ms);
  const runs = [];
  for (let i = 0; i < max; i++) {
    const t0 = c.t;
    let firstChange = null;
    s.w.onCall = (key) => { if (firstChange === null && !key.startsWith('GET')) firstChange = c.t - t0; };
    const r = await s.go(args, io);
    delete s.w.onCall;
    runs.push({ code: r.code, took: c.t - t0, setup: firstChange, down: HOSTS.filter((h) => platformOf(s.w, h) === null), text: r.text });
    if (r.code !== 4) return { runs, last: r };
    c.t += 1000 * Number(/in (\d+) seconds/.exec(r.text)?.[1] ?? 1);
  }
  return { runs, last: null };
}
function finishes(d, atMost) {
  assert.ok(d.last, `still asking for another run after ${d.runs.length}: ${d.runs.map((r) => `${r.code} in ${r.took / 1000}s, down [${r.down}]`).join(' | ')}\n${d.runs.at(-1).text}`);
  assert.equal(d.last.code, 0, d.last.text);
  assert.ok(d.runs.length <= atMost, `${d.runs.length} runs, at most ${atMost}`);
  d.runs.forEach((r, i) => {
    assert.ok(r.took <= 55_000, `run ${i + 1} took ${r.took / 1000} seconds`);
    for (const h of r.down) assert.ok(!d.runs[i + 1]?.down.includes(h), `${h} was down at the end of two runs in a row`);
  });
}

for (const ms of [600, 1500]) {
  describe(`review round 4: the run budget, ${ms} ms a request`, () => {
    test('T2: a first move of apex and www takes at most one confirm run per host, with 300 Pages deployments', async () => {
      const s = await recorded();
      manyDeployments(s, 300);
      const c = mockClock();
      const q = await s.go(['move'], lagging(s, c, ms));
      assert.equal(q.code, 3, q.text);
      c.t += 40_000; // the person reads the question and answers
      const d = await drive(s, c, ['move', '--confirm', codeOf(q)], ms);
      finishes(d, 2);
      assert.deepEqual(s.w.workerDomains.map((x) => x.hostname).sort(), HOSTS);
    });

    test('T2: a move resumed after a stopped host takes one confirm run, with 300 Pages deployments', async () => {
      const { s } = await halfMoved();
      manyDeployments(s, 300);
      const c = mockClock();
      const q = await s.go(['move'], lagging(s, c, ms));
      assert.equal(q.code, 3, q.text);
      c.t += 40_000;
      const d = await drive(s, c, ['move', '--confirm', codeOf(q)], ms);
      finishes(d, 1);
      assert.deepEqual(s.w.workerDomains.map((x) => x.hostname).sort(), HOSTS);
    });

    test('T2: an undo after a passed move and 20 shipped commits takes at most one confirm run per host, with 300 Pages deployments', async () => {
      const s = await recorded();
      const route = await moveAll(s);
      assert.equal((await pushAndAfter(s, route)).code, 0);
      ship(s, 20);
      manyDeployments(s, 300);
      const c = mockClock();
      const q = await s.go(['undo'], lagging(s, c, ms));
      assert.equal(q.code, 3, q.text);
      c.t += 40_000;
      const d = await drive(s, c, ['undo', '--confirm', codeOf(q)], ms);
      finishes(d, 2);
      assert.equal(s.w.workerDomains.length, 0);
    });
  });
}

describe('review round 3: the reserve and the pause', () => {
  test('R15: a plain run still sits through the pause', async () => {
    const s = await recorded();
    const c = mockClock();
    const io = { pollMs: 30_000, now: c.now, sleep: c.sleep };
    assert.equal((await s.go(['move'], io)).code, 3);
    c.t += 1_000;
    const t0 = c.t;
    assert.equal((await s.go(['move'], io)).code, 3);
    assert.ok(c.t - t0 >= 28_000, 'the second plain run waited out the pause');
  });

  test('N16: a run that has no time left for the second host says "at once", and the very next run finishes it', async () => {
    const s = await recorded();
    const q = await s.go(['move']);
    const r = await s.go(['move', '--confirm', codeOf(q)], slowFirstHost(s));
    assert.equal(r.code, 4, r.text);
    assert.match(r.text, /Run the same command again at once/);
    assert.equal(s.w.workerDomains.length, 1, 'one host moved');
    delete s.w.onCall;
    const next = await s.go(['move', '--confirm', codeOf(q)]);
    assert.equal(next.code, 0, next.text);
    assert.deepEqual(s.w.workerDomains.map((d) => d.hostname).sort(), HOSTS);
  });
});

describe('review round 3: the commit a run accepts', () => {
  test('B28: an ordinary edit of workers.jsonc on top of the route commit does not block the move', async () => {
    const s = await recorded();
    await moveAll(s); // the route commit is HEAD
    const file = path.join(s.site.work, 'workers.jsonc');
    writeFileSync(file, readFileSync(file, 'utf8').replace('2026-01-01', '2026-02-02'));
    git(s.site.work, 'commit', '-q', '-am', 'a newer compatibility date');
    const r = await s.go(['move']);
    assert.equal(r.code, 3, r.text);
    assert.ok(!/changes more/.test(r.text), r.text);
  });

  test('B29: a commit that changes the routes and a site file is refused; so is one that brings workers.jsonc back with routes and more', async () => {
    const s = await recorded();
    await moveAll(s);
    const file = path.join(s.site.work, 'workers.jsonc');
    writeFileSync(file, setRoutes(readFileSync(file, 'utf8'), []));
    writeFileSync(path.join(s.site.work, 'site', 'index.html'), '<h1>Changed</h1>');
    git(s.site.work, 'commit', '-q', '-am', 'no routes, and a page changed');
    const u = await s.go(['undo']);
    assert.equal(u.code, 1, u.text);
    assert.match(u.text, /changes more in workers\.jsonc than the custom-domain routes/);

    const g = await recorded();
    await moveAll(g);
    git(g.site.work, 'rm', '-q', 'workers.jsonc');
    git(g.site.work, 'commit', '-q', '-m', 'the config is gone');
    writeFileSync(path.join(g.site.work, 'workers.jsonc'), setRoutes(`{\n  "name": "${WORKER}",\n  "compatibility_date": "2026-05-05",\n  "assets": { "directory": "./dist" },\n}\n`, HOSTS));
    git(g.site.work, 'add', 'workers.jsonc');
    git(g.site.work, 'commit', '-q', '-m', 'the config is back, with routes and more');
    const m = await g.go(['move']);
    assert.equal(m.code, 1, m.text);
    assert.match(m.text, /changes more in workers\.jsonc than the custom-domain routes/);
  });
});

describe('review round 3: what a stopped run says, and the probe', () => {
  const breakPrepare = (s, edit = () => {}) => { // a stop inside prepare, after the state was read
    const st = s.state();
    edit(st);
    st.worker = 'another-worker';
    writeFileSync(s.stateFile(), JSON.stringify(st));
  };

  test('B30: a stop inside prepare, after the state was read, still names a host that has left its platform', async () => {
    const { s } = await halfMoved();
    breakPrepare(s);
    const r = await s.go(['move']);
    assert.equal(r.code, 1, r.text);
    assert.ok(r.text.includes(`${HOSTS[0]} has left Pages`), r.text);
  });

  test('B30: a host the other direction left on neither is named too, and so is one this run reads on neither', async () => {
    const s = await recorded();
    await moveAll(s);
    breakPrepare(s, (st) => { st.track.undo = { [HOSTS[1]]: { leftAt: new Date().toISOString(), where: 'neither' } }; });
    const r = await s.go(['move']);
    assert.ok(r.text.includes(`${HOSTS[1]} is on neither platform`), r.text);

    const live = await recorded();
    await moveAll(live);
    live.w.workerDomains = live.w.workerDomains.filter((d) => d.hostname !== HOSTS[1]); // taken off by hand
    const a = await live.go(['after']);
    assert.equal(a.code, 1, a.text); // the commit is not pushed, but the run read the hosts first
    assert.ok(a.text.includes(`${HOSTS[1]} has left Pages; last read: on neither`), a.text);
    assert.ok(!new RegExp(`^${dotted(HOSTS[0])} is on neither`, 'm').test(a.text), a.text);
  });

  test('B32: after a clean move, an after that stops on a build does not say the hosts were "not read yet"', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    s.push();
    s.w.pagesCommit = s.w.workerCommit = route;
    s.w.checkRuns[route] = unfinishedWorkersRun(route);
    const a = await s.go(['after']);
    assert.equal(a.code, 4, a.text);
    assert.ok(!/not read yet/.test(a.text), a.text);
    const tr = s.state().track.move;
    assert.deepEqual(HOSTS.map((h) => tr[h].where), ['worker', 'worker'], 'every successful read-back is kept');
  });

  test('B32: a host that was already where the move ends, and so was skipped, has its place kept too', async () => {
    const { s } = await halfMoved(); // the apex has moved; the run now finishes www, and skips the apex
    const q = await s.go(['move']);
    const st0 = s.state();
    delete st0.track.move[HOSTS[0]].where; // as if an earlier run never wrote it
    writeFileSync(s.stateFile(), JSON.stringify(st0));
    const g = await s.go(['move', '--confirm', codeOf(q)]);
    assert.equal(g.code, 0, g.text);
    assert.equal(s.state().track.move[HOSTS[0]].where, 'worker');
  });

  test('B31: a zone rule whose Location carries a "t" parameter of its own is compared with it, not with the probe\'s', async () => {
    const s = scenario({ world: { wwwRedirect: { from: HOSTS[1], to: HOSTS[0], query: 't=7', keepQuery: true } } });
    assert.equal((await recordDone(s)).code, 0);
    const c = mockClock();
    const q = await s.go(['move'], { now: c.now });
    s.w.wwwRedirect = { ...s.w.wwwRedirect, query: 't=8' }; // a different redirect now
    const g = await s.go(['move', '--confirm', codeOf(q)], shortRun(c));
    assert.equal(g.code, 4, g.text);
    assert.match(g.text, /not every host serves the Worker yet/);
    s.w.wwwRedirect = { ...s.w.wwwRedirect, query: 't=7' }; // the recorded one again
    const again = await s.go(['move', '--confirm', codeOf(q)], shortRun(c));
    assert.equal(again.code, 0, again.text);
  });
});

// ---------------------------------------------------------------- round 4 of the DIFF review

const changes = (s) => s.w.calls.filter((x) => x.method !== 'GET');
const dnsReads = (s) => s.w.calls.filter((x) => x.method === 'GET' && x.path.endsWith('/dns_records'));
const someDeployments = (s, n = 3) => manyDeployments(s, n);
const countLsRemote = (counter) => async (cmd, args, o) => { if (cmd === 'git' && args[0] === 'ls-remote') counter.n++; return runProgram(cmd, args, o); };
// apex back on Pages, www on neither platform: down
function wwwDown(s) {
  s.w.workerDomains = [];
  s.w.project.domains = [HOSTS[0]];
  s.w.dns = s.w.dns.filter((r) => !(r.type === 'CNAME' && r.name === HOSTS[1]));
  s.w.dns.push({ id: 'a'.padEnd(32, '7'), type: 'CNAME', name: HOSTS[0], content: SUBDOMAIN, proxied: true, ttl: 1 });
}

describe('review round 4: what a --confirm run reads, and what it compares (A1, A2)', () => {
  test('A1: the plain run saves what it checked: the deployments\' total and newest, the branch tips, the time and the command', async () => {
    const s = await recorded();
    manyDeployments(s, 300);
    const T = Date.now();
    assert.equal((await s.go(['move'], { now: () => T })).code, 3);
    const k = s.state().checked;
    assert.equal(k.kind, 'move');
    assert.equal(k.total, 300);
    assert.equal(k.newest, 'd0000000-0000-4000-8000-000000000000');
    assert.equal(k.tip, s.site.frozen);
    assert.equal(k.main, s.site.frozen);
    assert.equal(k.at, T);
  });

  test('A2: a --confirm run reads page 1 of the deployments and nothing else of GitHub or Pages history: one ls-remote, no check run, no second page', async () => {
    const s = await recorded();
    manyDeployments(s, 300);
    const q = await s.go(['move']);
    s.w.calls.length = 0;
    s.w.siteCalls.length = 0;
    const ls = { n: 0 };
    const g = await s.go(['move', '--confirm', codeOf(q)], { run: countLsRemote(ls) });
    assert.equal(g.code, 0, g.text);
    const dep = s.w.calls.filter((x) => x.method === 'GET' && x.path.endsWith('/deployments') && x.path.includes('/pages/'));
    assert.equal(dep.length, 1, 'one read of the deployments');
    assert.equal(dep[0].query, '?page=1');
    assert.equal(s.w.siteCalls.filter((u) => u.includes('api.github.com')).length, 0, 'no GitHub request');
    assert.equal(ls.n, 1, 'one ls-remote');
  });

  const refused = async (s, q, io = {}) => {
    const g = await s.go(['move', '--confirm', codeOf(q)], io);
    assert.equal(g.code, 1, g.text);
    assert.match(g.text, /run the plain command again/);
    assert.equal(changes(s).length, 0, 'nothing on Cloudflare changed');
    assert.ok(!s.state().open, 'and the move was not opened');
    return g;
  };

  test('A2: a deployment that arrived since the plain run (the total differs) is refused', async () => {
    const s = await recorded();
    someDeployments(s);
    const q = await s.go(['move']);
    s.w.pagesDeployments.push(deployment('built', { commit: s.site.frozen }));
    assert.match((await refused(s, q)).text, /deployments/);
  });

  test('A2: a deployment swapped for another (the newest id differs, the total does not) is refused', async () => {
    const s = await recorded();
    someDeployments(s);
    const q = await s.go(['move']);
    s.w.pagesDeployments[0].id = 'eeeeeeee-0000-4000-8000-000000000000';
    assert.match((await refused(s, q)).text, /newest/);
  });

  test('A2: a push to the branch since the plain run (the tip differs) is refused', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    assert.equal((await pushAndAfter(s, route)).code, 0);
    const q = await s.go(['undo']);
    assert.equal(q.code, 3, q.text);
    s.push(); // the undo commit goes up before the yes
    s.w.calls.length = 0;
    const g = await s.go(['undo', '--confirm', codeOf(q)]);
    assert.equal(g.code, 1, g.text);
    assert.match(g.text, /run the plain command again/);
    assert.match(g.text, /branch/);
    assert.equal(changes(s).length, 0, 'nothing on Cloudflare changed');
  });

  test('A2: a plain run more than 15 minutes old is refused', async () => {
    const s = await recorded();
    const c = mockClock();
    const q = await s.go(['move'], { now: c.now });
    c.t += 14 * 60_000;
    const near = await s.go(['move', '--confirm', codeOf(q)], { now: c.now, runMs: 55_000 });
    assert.equal(near.code, 0, near.text);
    const s2 = await recorded();
    const c2 = mockClock();
    const q2 = await s2.go(['move'], { now: c2.now });
    c2.t += 16 * 60_000;
    assert.match((await refused(s2, q2, { now: c2.now })).text, /15 minutes/);
  });

  test('A2: a host on neither platform is finished first, however old the plain run is; the run refuses after it', async () => {
    const { s } = await halfMoved();
    wwwDown(s);
    const c = mockClock();
    const q = await s.go(['move'], { now: c.now });
    assert.equal(q.code, 3, q.text);
    c.t += 20 * 60_000;
    const g = await s.go(['move', '--confirm', codeOf(q)], { now: c.now });
    assert.equal(g.code, 1, g.text);
    assert.match(g.text, /run the plain command again/);
    assert.deepEqual(s.w.workerDomains.map((d) => d.hostname), [HOSTS[1]], 'the down host was attached');
    assert.ok(s.w.project.domains.includes(HOSTS[0]), 'the fresh host was left alone');
  });
});

describe('review round 4: the time a host needs (A3, A4, A5)', () => {
  test('A3: every read of a host\'s records asks for that host by name, so a long zone costs nothing', async () => {
    const s = await recorded();
    for (let i = 0; i < 150; i++) s.w.dns.push({ id: `b${String(i).padStart(31, '0')}`, type: 'TXT', name: `t${i}.${ZONE.name}`, content: 'v=x', ttl: 3600 });
    const q = await s.go(['move']);
    assert.equal(q.code, 3, q.text);
    const g = await s.go(['move', '--confirm', codeOf(q)]);
    assert.equal(g.code, 0, g.text);
    const reads = dnsReads(s);
    assert.ok(reads.length >= 4, 'the zone was read');
    for (const r of reads) assert.match(r.query, /[?&]name=(lenas-backstube\.example|www\.lenas-backstube\.example)(&|$)/, `a zone-wide read: ${r.query}`);
    assert.ok(reads.every((r) => !/page=2/.test(r.query)), 'one page each');
  });

  test('A3: an answer that holds records of other names is not trusted: the filter may be ignored, and the run stops', async () => {
    const s = await recorded();
    for (let i = 0; i < 150; i++) s.w.dns.push({ id: `b${String(i).padStart(31, '0')}`, type: 'TXT', name: `t${i}.${ZONE.name}`, content: 'v=x', ttl: 3600 });
    s.w.dnsIgnoresName = true;
    const r = await s.go(['move']);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /name/);
  });

  test('A3: the gate lets a host\'s records be asked for by name, and nobody else\'s', () => {
    const c = CTX();
    assert.doesNotThrow(() => gate('GET', `${Z}/dns_records?name=${HOSTS[0]}&per_page=100&page=1`, undefined, c));
    const nope = (p) => assert.throws(() => gate('GET', p, undefined, c), (e) => e instanceof Stop && /gate: refused/.test(e.message), p);
    nope(`${Z}/dns_records?name=mail.${ZONE.name}&page=1`);
    nope(`${Z}/dns_records?name=${HOSTS[0]}&type=TXT`);
    nope(`${Z}/dns_records?name=${HOSTS[0]}&name=${HOSTS[1]}x`);
  });

  test('A4: a run whose own reading leaves no room for one host refuses before any host leaves, and says what took the time', async () => {
    const s = await recorded();
    someDeployments(s);
    const q = await s.go(['move'], { runMs: 600_000 });
    assert.equal(q.code, 3, q.text);
    const c = mockClock();
    const slow = { ...lagging(s, c, 6000), requestMs: 8000 }; // six reads, one after the other, at six seconds each
    const r = await s.go(['move', '--confirm', codeOf(q)], slow);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /reading what the move needs took \d+ seconds of this run's 55/i);
    assert.match(r.text, /a host needs 45 seconds/);
    assert.match(r.text, /by hand/);
    assert.equal(changes(s).length, 0, 'no host left');
    assert.ok(!s.state().open, 'and the move was not opened');
  });

  test('A4: the same run with room for one host goes ahead', async () => {
    const s = await recorded();
    const T = Date.now();
    const q = await s.go(['move'], { now: () => T });
    const tight = await s.go(['move', '--confirm', codeOf(q)], { now: () => T, runMs: 44_000, reserveMs: 45_000 });
    assert.equal(tight.code, 1, tight.text);
    assert.equal(s.w.workerDomains.length, 0, 'no host was started');
    const roomy = await s.go(['move', '--confirm', codeOf(q)], { now: () => T, runMs: 46_000, reserveMs: 45_000 });
    assert.equal(roomy.code, 0, roomy.text);
  });

  test('A5: a host on neither platform that does not fit the time left ends the run at once with exit 4, naming what to do if it repeats', async () => {
    const { s } = await halfMoved();
    wwwDown(s);
    const q = await s.go(['move']);
    assert.equal(q.code, 3, q.text);
    const r = await s.go(['move', '--confirm', codeOf(q)], { reserveMs: 100_000 });
    assert.equal(r.code, 4, r.text);
    assert.match(r.text, /Run the same command again at once/);
    assert.match(r.text, /by hand/);
    assert.equal(s.w.workerDomains.length, 0, 'nothing was attached: the next run starts it with its whole time');
  });

  test('A5 and B27: a host on neither platform is finished first; a fresh host that does not fit after it waits for the next run', async () => {
    const { s } = await halfMoved();
    wwwDown(s);
    const q = await s.go(['move']);
    let T = Date.now();
    s.w.onCall = (key) => { if (key === 'PUT /accounts/:id/workers/domains') T += 40_000; }; // the down host's attach takes long
    const r = await s.go(['move', '--confirm', codeOf(q)], { now: () => T, reserveMs: 20_000 });
    assert.equal(r.code, 4, r.text);
    assert.deepEqual(s.w.workerDomains.map((d) => d.hostname), [HOSTS[1]], 'the down host was attached');
    assert.ok(s.w.project.domains.includes(HOSTS[0]), 'the fresh host was left alone');
    assert.match(r.text, /Not enough of this run is left to move lenas-backstube\.example/);
  });

  test('B33: a --confirm run whose only host to finish is on neither platform does not sit through GitHub\'s pause', async () => {
    const { s } = await halfMoved(); // the apex is on the Worker
    s.w.project.domains = [];
    s.w.dns = s.w.dns.filter((r) => !(r.type === 'CNAME' && r.name === HOSTS[1])); // www is on neither
    const c = mockClock();
    const io = { pollMs: 30_000, now: c.now, sleep: c.sleep };
    const q = await s.go(['move'], io);
    assert.equal(q.code, 3, q.text);
    c.t += 1_000;
    const t0 = c.t;
    const g = await s.go(['move', '--confirm', codeOf(q)], io);
    assert.equal(g.code, 0, g.text);
    assert.ok(c.t - t0 < 5_000, `the run waited ${(c.t - t0) / 1000} seconds`);
    assert.deepEqual(s.w.workerDomains.map((d) => d.hostname).sort(), HOSTS);
  });
});

// A --confirm run whose Worker never serves the commit it waits for, on a clock that stands still, so
// it only spins. A 20 ms timer starts with the first sleep. Resolves whether it fired while the run was
// still spinning: the spin is let go when the timer fires, or after `cap` sleeps.
async function timerFiresWhileSpinning(s, sleepFor, cap) {
  const T = Date.now();
  const q = await s.go(['move'], { now: () => T });
  const real = s.w.workerCommit;
  s.w.workerCommit = 'f'.repeat(40);
  let fired = false;
  let n = 0;
  const sleep = () => {
    if (n++ === 0) setTimeout(() => { fired = true; }, 20);
    if (fired || n > cap) s.w.workerCommit = real;
    return sleepFor();
  };
  const g = await s.go(['move', '--confirm', codeOf(q)], { now: () => T, sleep });
  assert.equal(g.code, 0, g.text);
  assert.ok(n > 0, 'the run never slept: it did not spin');
  return fired;
}

describe('review round 4: lists, stopped runs, the test clock and the stage', () => {
  test('B36: a page that holds fewer items than it should, and is not empty, stops the run', async () => {
    const s = await recorded();
    manyDeployments(s, 100);
    s.w.depShort = { page: 2, size: 10 };
    const r = await s.go(['move']);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /does not decide from part of a list/);
    assert.equal(s.state().asked, undefined, 'and no question was asked');
  });

  test('B36: a list that grows while it is read stops the run', async () => {
    const s = await recorded();
    manyDeployments(s, 100);
    let n = 0;
    s.w.onCall = (key) => { if (key.includes('/pages/projects/') && key.endsWith('/deployments') && ++n === 2) s.w.pagesDeployments.unshift(deployment('built', { commit: s.site.frozen })); };
    const r = await s.go(['move']);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /does not decide from part of a list/);
  });

  test('B34: this run\'s read of a host on neither wins over an older saved "on Pages"', async () => {
    const { s } = await halfMoved();
    const st = s.state();
    st.track.move[HOSTS[1]] = { leftAt: new Date().toISOString(), where: 'pages' }; // the older read
    writeFileSync(s.stateFile(), JSON.stringify(st));
    s.w.project.domains = [HOSTS[0]]; // www has since gone from Pages and is not on the Worker
    s.w.dns = s.w.dns.filter((r) => !(r.type === 'CNAME' && r.name === HOSTS[1]));
    writeFileSync(path.join(s.site.work, 'site', 'index.html'), '<h1>edited</h1>'); // a dirty tree stops the run after its read
    const r = await s.go(['move']);
    assert.equal(r.code, 1, r.text);
    assert.ok(r.text.includes(`${HOSTS[1]} has left Pages; last read: on neither`), r.text);
    assert.ok(!r.text.includes('last read: on Pages'), r.text);
    assert.match(statusPage(s), /on neither \(down\)/);
  });

  test('B35: a run that spins on a frozen clock lets a 20 ms timer fire', async () => {
    const s = await recorded();
    assert.equal(await timerFiresWhileSpinning(s, yielding, 100_000), true);
  });

  test('N24: the same spin with a sleep that does not yield starves the timer, so the test above can fail', async () => {
    const s = await recorded();
    assert.equal(await timerFiresWhileSpinning(s, () => Promise.resolve(), 3_000), false);
  });

  test('N20: a go-forward that writes no new route commit does not show "after passed"', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    assert.equal((await pushAndAfter(s, route)).code, 0);
    assert.equal(nowStage(s), '5');
    const T = Date.now();
    const q = await s.go(['undo'], { now: () => T });
    assert.equal((await s.go(['undo', '--confirm', codeOf(q)], { now: () => T })).code, 0);
    git(s.site.work, 'reset', '-q', '--hard', route); // the route commit is HEAD again: no new commit is written
    const m = await s.go(['move'], { now: () => T });
    assert.equal(m.code, 3, m.text);
    const g = await s.go(['move', '--confirm', codeOf(m)], { now: () => T });
    assert.equal(g.code, 0, g.text);
    assert.equal(nowStage(s), '3', 'the hosts moved again and have not been checked');
  });
});

describe('review round 5: stale confirms, re-runs of a build, and what a confirm reads (B38, R16, N22-N25)', () => {
  // the apex is on the Worker, www on neither platform: the only host left to change is down
  async function onlyDownHostLeft() {
    const { s } = await halfMoved();
    s.w.project.domains = [];
    s.w.dns = s.w.dns.filter((r) => !(r.type === 'CNAME' && r.name === HOSTS[1]));
    return s;
  }

  test('B38: a stale --confirm with no fresh host left finishes the down host, exits 0 and prints the drift as a warning', async () => {
    const s = await onlyDownHostLeft();
    const c = mockClock();
    const q = await s.go(['move'], { now: c.now });
    assert.equal(q.code, 3, q.text);
    c.t += 20 * 60_000;
    const g = await s.go(['move', '--confirm', codeOf(q)], { now: c.now });
    assert.equal(g.code, 0, g.text);
    assert.match(g.text, /Warning: .*more than 15 minutes/);
    assert.match(g.text, /node move-to-workers\.mjs after/);
    assert.deepEqual(s.w.workerDomains.map((d) => d.hostname).sort(), HOSTS, 'the down host was attached');
  });

  test('B38: a stale --confirm with a fresh host left finishes the down host and then refuses (the A2 test above holds the host checks)', async () => {
    const { s } = await halfMoved();
    wwwDown(s); // the apex is fresh again, www is down
    const c = mockClock();
    const q = await s.go(['move'], { now: c.now });
    c.t += 20 * 60_000;
    const g = await s.go(['move', '--confirm', codeOf(q)], { now: c.now });
    assert.equal(g.code, 1, g.text);
    assert.ok(g.text.includes(`${HOSTS[1]} was finished first`), g.text);
    assert.match(g.text, /run the plain command again/);
  });

  test('B38: a --confirm run on a check that still holds prints no warning', async () => {
    const s = await onlyDownHostLeft();
    const q = await s.go(['move']);
    const g = await s.go(['move', '--confirm', codeOf(q)]);
    assert.equal(g.code, 0, g.text);
    assert.ok(!/Warning: /.test(g.text), g.text);
  });

  test('R16: after an undo, a Workers Builds re-run of the route commit that attaches the hosts to the Worker again makes after fail', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    assert.equal((await pushAndAfter(s, route)).code, 0);
    const uq = await s.go(['undo']);
    assert.equal((await s.go(['undo', '--confirm', codeOf(uq)], frozenClock())).code, 0);
    const undo = git(s.site.work, 'rev-parse', 'HEAD');
    s.push();
    s.w.pagesCommit = s.w.workerCommit = undo;
    // the re-run of the route commit's build puts both hosts back on the Worker
    s.w.project.domains = [];
    s.w.dns = s.w.dns.filter((r) => r.type !== 'CNAME' || !HOSTS.includes(r.name));
    s.w.workerDomains = HOSTS.map((h, i) => ({ id: `0000009${i}-0000-4000-8000-000000000000`, hostname: h, service: WORKER, zone_id: ZONE.id, zone_name: ZONE.name, environment: 'production' }));
    const a = await s.go(['after']);
    assert.equal(a.code, 1, a.text);
    assert.match(a.text, new RegExp(`${dotted(HOSTS[0])} is on the Worker`));
    assert.match(a.text, /Run undo again/);
    assert.ok(s.state().open, 'the move was not closed');
  });

  test('R16: a check run that starts after the confirm holds after back (exit 4) until it ends', async () => {
    const s = await recorded();
    const route = await moveAll(s);
    s.push();
    s.w.pagesCommit = s.w.workerCommit = route;
    s.w.checkRuns[route] = unfinishedWorkersRun(route); // a rebuild began once the confirm run was over
    const waiting = await s.go(['after']);
    assert.equal(waiting.code, 4, waiting.text);
    assert.match(waiting.text, /Builds are unfinished/);
    delete s.w.checkRuns[route];
    const done = await s.go(['after']);
    assert.equal(done.code, 0, done.text);
  });

  // N22: a standing test for every --confirm path. Each makes no request to GitHub's API.
  const githubCalls = (s) => s.w.siteCalls.filter((u) => u.includes('api.github.com')).length;
  async function confirmWithoutGithub(s, dir, q, io = {}) {
    s.w.siteCalls.length = 0;
    const g = await s.go([dir, '--confirm', codeOf(q)], io);
    return { g, n: githubCalls(s) };
  }
  // an undo stopped after its first host: the run's time ran out
  async function halfUndone() {
    const s = await recorded();
    await moveAll(s);
    let T = Date.now();
    const q = await s.go(['undo'], { now: () => T });
    s.w.onCall = (key) => { if (key === 'POST /zones/:id/dns_records') T += 3000; };
    const r = await s.go(['undo', '--confirm', codeOf(q)], { runMs: 5000, reserveMs: 3500, now: () => T });
    assert.equal(r.code, 4, r.text);
    delete s.w.onCall;
    return s;
  }

  test('N22: a first move --confirm reads no GitHub (the plain run before it does, so the count can move)', async () => {
    const s = await recorded();
    s.w.siteCalls.length = 0;
    const q = await s.go(['move']);
    assert.ok(githubCalls(s) > 0, 'the plain run reads GitHub');
    const { g, n } = await confirmWithoutGithub(s, 'move', q);
    assert.equal(g.code, 0, g.text);
    assert.equal(n, 0);
  });

  test('N22: a resumed move --confirm reads no GitHub', async () => {
    const { s } = await halfMoved();
    const q = await s.go(['move']);
    const { g, n } = await confirmWithoutGithub(s, 'move', q);
    assert.equal(g.code, 0, g.text);
    assert.equal(n, 0);
  });

  test('N22: a first undo --confirm reads no GitHub', async () => {
    const s = await recorded();
    await moveAll(s);
    const q = await s.go(['undo']);
    const { g, n } = await confirmWithoutGithub(s, 'undo', q, frozenClock());
    assert.equal(g.code, 0, g.text);
    assert.equal(n, 0);
  });

  test('N22: a resumed undo --confirm reads no GitHub', async () => {
    const s = await halfUndone();
    const q = await s.go(['undo']);
    const { g, n } = await confirmWithoutGithub(s, 'undo', q);
    assert.equal(g.code, 0, g.text);
    assert.equal(n, 0);
  });

  test('N23: a host on both platforms is named as that when the time is short, not called down', async () => {
    const { s } = await halfMoved(); // the apex is on the Worker; www is still on Pages
    s.w.workerDomains.push({ id: '00000099-0000-4000-8000-000000000000', hostname: HOSTS[1], service: WORKER, zone_id: ZONE.id, zone_name: ZONE.name, environment: 'production' });
    const q = await s.go(['move']);
    assert.equal(q.code, 3, q.text);
    const g = await s.go(['move', '--confirm', codeOf(q)], { reserveMs: 100_000 });
    assert.equal(g.code, 1, g.text);
    assert.match(g.text, new RegExp(`${dotted(HOSTS[1])} is on both the Pages project and the Worker`));
    assert.ok(!/is down/.test(g.text), g.text);
  });

  test('N25: an exit-4 stop before any host moved back, then a token with under an hour left, still refuses the undo', async () => {
    const s = await recorded();
    await moveAll(s);
    const T = Date.now();
    const q = await s.go(['undo'], { now: () => T });
    s.w.workerDomains = s.w.workerDomains.filter((d) => d.hostname !== HOSTS[1]); // www is on neither platform: down
    s.w.calls.length = 0;
    const stopped = await s.go(['undo', '--confirm', codeOf(q)], { now: () => T, reserveMs: 100_000 });
    assert.equal(stopped.code, 4, stopped.text);
    assert.equal(changes(s).length, 0, 'no host had left its platform');
    s.w.token.expires_on = new Date(Date.now() + 30 * 60_000).toISOString().replace(/\.\d+Z$/, 'Z');
    const again = await s.go(['undo', '--confirm', codeOf(q)], { now: () => T });
    assert.equal(again.code, 1, again.text);
    assert.match(again.text, /less than an hour/);
  });
});

// ---------------------------------------------------------------- the Pages domain list (kit undo test, 2026-11-05)

// A move done and pushed, ready for an undo: every host is on the Worker and after has passed.
async function movedAndPassed(s) {
  const rec = await recordDone(s);
  assert.equal(rec.code, 0, rec.text);
  const q = await s.go(['move']);
  const route = git(s.site.work, 'rev-parse', 'HEAD');
  assert.equal((await s.go(['move', '--confirm', codeOf(q)])).code, 0);
  s.push();
  s.w.pagesCommit = s.w.workerCommit = route;
  assert.equal((await s.go(['after'])).code, 0);
}

describe('review: Pages membership comes from the project\'s domain list (BUG A)', () => {
  test('an undo whose added domain is missing from the project\'s own list for a while finishes without adding it twice', async () => {
    const s = scenario();
    await movedAndPassed(s);
    const uq = await s.go(['undo']);
    const undoCommit = git(s.site.work, 'rev-parse', 'HEAD');
    s.w.projectLag = 4; // the project's own list shows a new domain only after four reads; /domains shows it at once
    s.w.calls.length = 0;
    let r;
    for (let i = 0; i < 12; i++) {
      r = await s.go(['undo', '--confirm', codeOf(uq)]);
      if (r.code === 0) break;
      assert.equal(r.code, 4, `run ${i + 1} ended with ${r.code}, not asking for another run:\n${r.text}`);
    }
    assert.equal(r.code, 0, r.text);
    const adds = s.w.calls.filter((c) => c.method === 'POST' && c.path.endsWith('/pages/projects/' + REPO + '/domains'));
    assert.equal(adds.length, HOSTS.length, 'each host was added to Pages once, never again');
    assert.ok(!r.text.includes('on neither'), 'the host was never called down while Pages held it');
    s.push();
    s.w.pagesCommit = s.w.workerCommit = undoCommit;
    assert.equal((await s.go(['after'])).code, 0);
  });

  test('"already added" (8000018) on the add is taken as "already there", not as a failure', async () => {
    const s = scenario();
    await movedAndPassed(s);
    const uq = await s.go(['undo']);
    s.w.addAlwaysAlready = true;
    const r = await s.go(['undo', '--confirm', codeOf(uq)]);
    assert.equal(r.code, 0, r.text);
    assert.match(r.text, /already on the Pages project/);
  });

  test('"already added" with neither list showing the domain (C2): the host counts as on Pages, the run is not stopped "on neither"', async () => {
    const s = scenario();
    await movedAndPassed(s);
    const uq = await s.go(['undo']);
    s.w.addAlreadyUnseen = true; // Cloudflare says "already added"; the project's list and /domains both lag
    const r = await s.go(['undo', '--confirm', codeOf(uq)]);
    assert.doesNotMatch(r.text, /on neither/, r.text);
    assert.doesNotMatch(r.text, /reads .* after its changes/, r.text);
    assert.match(r.text, /already on the Pages project/);
    assert.match(r.text, /CNAME written/, 'the run went on to the host\'s CNAME');
  });

  test('a Pages domain that is not active yet is not "on Pages" for after', async () => {
    const s = scenario();
    await movedAndPassed(s);
    const uq = await s.go(['undo']);
    const undoCommit = git(s.site.work, 'rev-parse', 'HEAD');
    assert.equal((await s.go(['undo', '--confirm', codeOf(uq)])).code, 0);
    s.push();
    s.w.pagesCommit = s.w.workerCommit = undoCommit;
    s.w.pagesStatus = { [HOSTS[0]]: 'pending' };
    const pending = await s.go(['after']);
    assert.equal(pending.code, 4, pending.text); // G4: coming up is "run again", not a failure
    assert.match(pending.text, /Cloudflare shows the domain as pending/);
    assert.match(pending.text, /Run the same command again in a minute/);
    s.w.pagesStatus = { [HOSTS[0]]: 'blocked' };
    const blocked = await s.go(['after']);
    assert.equal(blocked.code, 1, 'a status that is not on its way up is a failure');
    assert.match(blocked.text, /Cloudflare shows the domain as blocked/);
    s.w.pagesStatus = {};
    assert.equal((await s.go(['after'])).code, 0);
  });
});

describe('review: status 4 is said once', () => {
  test('a run that asks for another run prints "Status 4." once', async () => {
    const s = scenario();
    const r = await s.go(['record']); // the build takes longer than one run
    assert.equal(r.code, 4, r.text);
    assert.match(r.text, /The build is not finished\. Run the same command again in a minute\./);
    assert.equal(r.text.match(/Status 4\./g).length, 1, r.text);
    assert.ok(await recordDone(s).then((x) => x.code === 0), 'the record still finishes');
  });
});

describe('review: the Pages domain list as Cloudflare sends it (BUG A, test 2)', () => {
  const CAPTURE = JSON.parse(readFileSync(path.join(HERE, 'fixtures', 'cloudflare-pages', 'cloudflare-api-pages-domains-2026-11-05.json'), 'utf8'));

  test('the captured answer: both hosts are on Pages, read from each entry\'s own status', async () => {
    const s = scenario({ world: { pagesDomainsAnswer: CAPTURE } });
    const r = await s.go(['check']);
    assert.equal(r.code, 0, r.text);
    // Written by hand from the capture: two entries, both "active"; the DNS CNAMEs are the stub's.
    assert.match(r.text, /^ {2}lenas-backstube\.example: on Pages; DNS CNAME /m);
    assert.match(r.text, /^ {2}www\.lenas-backstube\.example: on Pages; DNS CNAME /m);
    assert.doesNotMatch(r.text, /Cloudflare shows the domain as/);
    // The same answer with the top-level status of one entry changed: the script reads that field,
    // not the nested verification_data.status or validation_data.status, which stay "active".
    const pending = JSON.parse(JSON.stringify(CAPTURE));
    pending.result[1].status = 'pending';
    s.w.pagesDomainsAnswer = pending;
    const p = await s.go(['check']);
    assert.match(p.text, /^ {2}www\.lenas-backstube\.example: on Pages \(Cloudflare shows the domain as pending\); DNS /m);
    assert.match(p.text, /^ {2}lenas-backstube\.example: on Pages; DNS /m, 'the entry that stayed active is unchanged');
  });

  test('an answer that does not say how many domains there are is refused (G5)', async () => {
    const { result_info: _gone, ...noInfo } = CAPTURE;
    const s = scenario({ world: { pagesDomainsAnswer: noInfo } });
    for (const cmd of ['check', 'record']) {
      const r = await s.go([cmd]);
      assert.equal(r.code, 1, `${cmd}: ${r.text}`);
      assert.match(r.text, /did not say how many domains the project has/);
    }
  });

  test('an entry with no status reads as "unknown", not as active (N2)', async () => {
    const odd = JSON.parse(JSON.stringify(CAPTURE));
    delete odd.result[0].status;
    const s = scenario({ world: { pagesDomainsAnswer: odd } });
    const r = await s.go(['check']);
    assert.match(r.text, /^ {2}lenas-backstube\.example: on Pages \(Cloudflare shows the domain as unknown\); DNS /m, r.text);
  });

  test('an answer with more than one page is refused, before anything is decided from it', async () => {
    for (const info of [{ page: 1, per_page: 20, count: 20, total_count: 41, total_pages: 3 }, { page: 1, per_page: 20, count: 2, total_count: 2, total_pages: 2 }]) {
      const s = scenario({ world: { pagesDomainsAnswer: { ...CAPTURE, result_info: info } } });
      for (const cmd of ['check', 'record']) {
        const r = await s.go([cmd]);
        assert.equal(r.code, 1, `${cmd}: ${r.text}`);
        assert.match(r.text, /more than 20 domains.*do the move in the Cloudflare dashboard/s);
      }
      assert.ok(s.w.calls.every((c) => c.method === 'GET'), 'nothing was changed');
    }
  });
});

describe('review: the undo says to deploy as well (kit undo test, 2026-11-05)', () => {
  test('move --confirm and undo --confirm both tell her to deploy the commit where the Worker has no Workers Builds', async () => {
    const s = scenario();
    assert.equal((await recordDone(s)).code, 0);
    const q = await s.go(['move']);
    const route = git(s.site.work, 'rev-parse', 'HEAD');
    const go = await s.go(['move', '--confirm', codeOf(q)]);
    assert.match(go.text, /Now push commit [0-9a-f]+ to .*, deploy it if the Worker has no Workers Builds, and run: node move-to-workers\.mjs after/);
    s.push();
    s.w.pagesCommit = s.w.workerCommit = route;
    assert.equal((await s.go(['after'])).code, 0);
    const uq = await s.go(['undo']);
    const back = await s.go(['undo', '--confirm', codeOf(uq)]);
    assert.match(back.text, /Now push commit [0-9a-f]+ to .*, deploy it if the Worker has no Workers Builds, and run: node move-to-workers\.mjs after/);
  });
});
