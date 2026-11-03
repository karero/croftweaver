// Tests for move-to-workers.mjs. Standard library only; run with
//   node --test skills/new-website/scripts/tests/move-to-workers.test.mjs
//
// The numbers are the plan's tests (workers-for-new-sites/PLAN-move-script.md, "How it is tested"):
//   1  the gate and the token rules      2  recorded captures, hand-written expectations
//   3  the commands, run through main()  4  the status page
// Test 5, the throwaway run on a real account, is not here: it needs a token. Each scenario runs
// main() the way the program does, in a fixture repository whose origin is a GitHub address that the
// repository's own git config sends to a local folder, against the stub in move-stub.mjs.
import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { execFile, execFileSync } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Stop, blankJsonc, compare, confirmCode, esc, gate, headerNames, main, makeApi, runProgram, makeSiteFetch, parseJsonc, pathList, renderStatus, routesOf, setRoutes } from '../move-to-workers.mjs';
import { ACCOUNT, OWNER, REPO, TOKEN, ZONE, deployment } from './cloudflare-stub.mjs';
import { HOSTS, SITE, SUBDOMAIN, VERSION_HOST, WORKER, fillerRuns, makeFetch, makeWorld, unfinishedWorkersRun, withoutWorkersRun } from './move-stub.mjs';

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
      sleep: async () => {}, say: (...l) => { out.push(...l); }, ...extra,
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
  test('a token that reaches two zones is refused', async () => {
    const s = scenario({ world: { extraZones: 1 } });
    const r = await s.go(['check']);
    assert.equal(r.code, 1);
    assert.match(r.text, /reaches 2 zones/);
    assert.ok(!s.w.calls.some((c) => c.method !== 'GET'));
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
    assert.match((await eight.go(['check'])).text, /reaches 8 zones/);
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

  test('a lock held by a live run refuses every command and stays; a stale one is reported, not removed', async () => {
    const s = await recorded();
    const lock = path.join(path.dirname(s.stateFile()), 'lock');
    writeFileSync(lock, `${process.pid}\nabc\n`);
    for (const cmd of [['move'], ['undo'], ['after']]) {
      const r = await s.go(cmd);
      assert.equal(r.code, 1, cmd.join(' '));
      assert.match(r.text, /Another run \(process \d+\) holds/);
      assert.ok(existsSync(lock), 'the other run\'s lock was removed');
    }
    writeFileSync(lock, '2147483646\nabc\n');
    const stale = await s.go(['move']);
    assert.match(stale.text, /was left by a run that no longer exists/);
    assert.ok(existsSync(lock));
    rmSync(lock);
    assert.equal((await s.go(['move'])).code, 3, 'it goes on once the file is deleted');
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
    assert.equal(s.state().route.commit, s.site.frozen, 'after must expect HEAD');
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
  const q = await s.go(['move']);
  const g = await s.go(['move', '--confirm', codeOf(q)]);
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
  const q = await s.go(['move']);
  s.w.delay = { 'PUT /accounts/:id/workers/domains': 2000 };
  const r = await s.go(['move', '--confirm', codeOf(q)], { runMs: 5000, reserveMs: 3500 });
  delete s.w.delay;
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
  test('B6: a route commit that changes anything but the routes is refused, for move and for undo', async () => {
    const s = await recorded();
    const file = path.join(s.site.work, 'workers.jsonc');
    writeFileSync(file, setRoutes(readFileSync(file, 'utf8'), HOSTS).replace('2026-01-01', '2026-02-02'));
    git(s.site.work, 'commit', '-q', '-am', 'routes and a compatibility date');
    const r = await s.go(['move']);
    assert.equal(r.code, 1, r.text);
    assert.match(r.text, /HEAD is not the frozen commit/);

    const u = await recorded();
    await moveAll(u);
    const f = path.join(u.site.work, 'workers.jsonc');
    writeFileSync(f, setRoutes(readFileSync(f, 'utf8'), []).replace('2026-01-01', '2026-02-02'));
    git(u.site.work, 'commit', '-q', '-am', 'no routes and a compatibility date');
    const q = await u.go(['undo']);
    assert.equal(q.code, 1, q.text);
    assert.match(q.text, /not the commit this script wrote/);
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
    const stopped = await s.go(['undo', '--confirm', codeOf(uq)], { reserveMs: 10 * 60_000 });
    assert.equal(stopped.code, 4, stopped.text);
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
    assert.equal(s.state().route.commit, git(clone, 'rev-parse', 'HEAD'));
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
    const stopped = await s.go(['undo', '--confirm', codeOf(uq)], { reserveMs: 10 * 60_000 });
    assert.equal(stopped.code, 4, stopped.text);
    const fwd = await s.go(['move']); // go forward: every host is still on the Worker
    assert.equal(fwd.code, 3, fwd.text);
    const done = await pushAndAfter(s, git(s.site.work, 'rev-parse', 'HEAD'));
    assert.equal(done.code, 0, done.text);
    assert.ok(s.state().open && s.state().passed, 'the move stays open and passed');
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
