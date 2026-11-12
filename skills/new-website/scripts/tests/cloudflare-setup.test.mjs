// Tests for cloudflare-setup.mjs. Standard library only; run with
//   node --test skills/new-website/scripts/tests/cloudflare-setup.test.mjs
//
// Each scenario runs the script as a program, the way an assistant does, in a fixture repository
// whose origin is a GitHub address that the repository's own git config sends to a local folder
// (url.<folder>.insteadOf), against a stub of Cloudflare's API, a stub nameserver and a stub of the
// Worker's version link on 127.0.0.1 (cloudflare-stub.mjs). The zone, settings and Bot Management
// answers are the trials' captures (fixtures/cloudflare-api/); the Workers answers are row 0.4's
// (fixtures/workers-api/). The Workers plan's scenarios are TS1 to TS6 (setup) and TL1 to TL8 (launch).
import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { execFile, execFileSync } from 'node:child_process';
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { BOT_LINES, LAUNCH_FAIL, aiNotes, LAUNCH_SKIP_IDS, SETTINGS, SKIP_IDS, checkArgs, codeFits, fixedText, gate, githubRepo, launchVerdict, makeApi, looksSwapped, parseRecord, setupCode, UsageError } from '../cloudflare-setup.mjs';
import { Stop } from '../move-to-workers.mjs';
import { ITEMS as CHECK_ITEMS } from '../cloudflare-check.mjs';
import { ACCOUNT, FIXTURES, OWNER, REPO, TOKEN, VERSION, WORKER, ZONE, WORKERS_FIXTURES, allFixtures, allWorkersFixtures, fixture, freshState, handle, project, servedBy, startApi, startDns, startPreview, startSites, versionHost, worker, zone } from './cloudflare-stub.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = path.join(HERE, '..', 'cloudflare-setup.mjs');
const NAMES = path.join(HERE, 'resolve-test-names.cjs');
const CHECKLIST = path.join(HERE, '..', '..', '..', '..', 'docs', 'CLOUDFLARE-CHECKLIST.md');
const REMOTE = `https://github.com/${OWNER}/${REPO}.git`;
const HOST = ZONE.name;
const TEMPLATE = path.join(HERE, '..', '..', 'templates', 'astro');
// The starter's own placeholder test and CI file: the launch stage reads them in the starter's form.
const STARTER_SPEC = readFileSync(path.join(TEMPLATE, 'tests', 'placeholders.spec.ts'), 'utf8');
const STARTER_CI = readFileSync(path.join(TEMPLATE, '.github', 'workflows', 'ci.yml'), 'utf8');
const EMPTY_LIST = (spec) => {
  const out = spec.replace(/^const UNFILLED_UNTIL_LAUNCH = new Set<string>\(\[.*\]\);$/m, 'const UNFILLED_UNTIL_LAUNCH = new Set<string>([]);');
  // A starter that writes the list another way would leave it as it was: say so here, not in 40 tests.
  assert.ok(out.includes('const UNFILLED_UNTIL_LAUNCH = new Set<string>([]);'), 'the starter\'s UNFILLED_UNTIL_LAUNCH line is no longer on one line');
  return out;
};
// The site's Worker config: one Worker that serves the built folder, with its workers.dev address off
// and its version links on, as the kit's starter has it.
const WRANGLER = `{
  // Lena's site: one Worker that serves the built folder.
  "name": "${WORKER}",
  "compatibility_date": "2026-01-01",
  "workers_dev": false,
  "preview_urls": true,
  "assets": { "directory": "./dist" }
}
`;

// ---------------------------------------------------------------- the site and its origin

const scratch = mkdtempSync(path.join(tmpdir(), 'cf-setup-test-'));
process.on('exit', () => rmSync(scratch, { recursive: true, force: true }));
// git sees no global or system config of the machine the tests run on (a global insteadOf, say).
const GIT_ISOLATION = { GIT_CONFIG_GLOBAL: path.join(scratch, 'empty-gitconfig'), GIT_CONFIG_NOSYSTEM: '1' };
writeFileSync(GIT_ISOLATION.GIT_CONFIG_GLOBAL, '');
const gitEnv = { ...process.env, ...GIT_ISOLATION, GIT_AUTHOR_NAME: 'Lena', GIT_AUTHOR_EMAIL: 'lena@example.com', GIT_COMMITTER_NAME: 'Lena', GIT_COMMITTER_EMAIL: 'lena@example.com' };
const git = (cwd, ...args) => execFileSync('git', args, { cwd, env: gitEnv, encoding: 'utf8' }).trim();
const slash = (p) => p.replace(/\\/g, '/');

let sites = 0;
// A site made with the kit: src/config.ts and wrangler.jsonc at the head of main, pushed to its origin;
// two-stage by default, with production at the same commit.
// The launch stage reads tests/placeholders.spec.ts and .github/workflows/ci.yml: by default the
// starter's, with its list of unfilled pages emptied, as on a finished site. `files` adds or replaces
// files (null removes one).
function makeSite({ prodBranch = 'production', production = true, url = `https://${HOST}`, ignoreDevVars = true, devVars = null, trackDevVars = false, files = {} } = {}) {
  const dir = path.join(scratch, `site-${++sites}`);
  const origin = path.join(dir, 'origin.git');
  const site = path.join(dir, 'lenas-backstube');
  mkdirSync(path.join(site, 'src'), { recursive: true });
  git(dir, 'init', '-q', '--bare', origin);
  git(site, 'init', '-q');
  git(site, 'checkout', '-q', '-b', 'main');
  writeFileSync(path.join(site, 'src', 'config.ts'), `export const SITE = {\n  url: '${url}',          // production origin\n  name: 'Lenas Backstube',\n};\n\nexport const PROD_BRANCH = '${prodBranch}';\n`);
  writeFileSync(path.join(site, '.gitignore'), `node_modules/\n${ignoreDevVars ? '.dev.vars\n' : ''}`);
  if (devVars !== null) writeFileSync(path.join(site, '.dev.vars'), devVars);
  const all = { 'wrangler.jsonc': WRANGLER, 'tests/placeholders.spec.ts': EMPTY_LIST(STARTER_SPEC), '.github/workflows/ci.yml': STARTER_CI, 'src/pages/index.astro': '<p>Brot</p>\n', 'public/robots.txt': 'User-agent: *\n', ...files };
  for (const [f, text] of Object.entries(all)) {
    if (text === null) continue;
    mkdirSync(path.dirname(path.join(site, f)), { recursive: true });
    writeFileSync(path.join(site, f), text);
  }
  git(site, 'add', ...['src', 'public', 'tests', '.github', '.gitignore', 'wrangler.jsonc', 'workers.jsonc'].filter((f) => existsSync(path.join(site, f))));
  if (trackDevVars) git(site, 'add', '-f', '.dev.vars');
  git(site, 'commit', '-q', '-m', 'Lena\'s site');
  git(site, 'remote', 'add', 'origin', REMOTE);
  git(site, 'config', `url.${slash(origin)}.insteadOf`, REMOTE);
  git(site, 'push', '-q', 'origin', 'main');
  if (production) git(site, 'push', '-q', 'origin', 'main:production');
  const sha = git(site, 'rev-parse', 'HEAD');
  return { site, origin, heads: { main: sha, ...(production ? { production: sha } : {}) } };
}

// ---------------------------------------------------------------- running the script

function cleanEnv() {
  const env = { ...process.env, ...GIT_ISOLATION };
  for (const k of Object.keys(env)) if (k === 'CLOUDFLARE_API_TOKEN' || k.startsWith('CLOUDFLARE_SETUP_')) delete env[k];
  return env;
}
// Names ending in .workers.dev.test resolve to this machine, in the script and in the check it starts.
const withNames = (extra = '') => `--require ${NAMES}${extra ? ` ${extra}` : ''}`;

function run(where, args, { api, dns, sites, preview, env = {}, token = TOKEN, stage = 'setup' } = {}) {
  const started = Date.now();
  return new Promise((resolve) => {
    const e = { ...cleanEnv(), NODE_OPTIONS: withNames(), ...(token ? { CLOUDFLARE_API_TOKEN: token } : {}), ...(api ? { CLOUDFLARE_SETUP_API: api.origin } : {}), ...(dns ? { CLOUDFLARE_SETUP_RESOLVER: dns.address } : {}),
      ...(sites ? { CLOUDFLARE_SETUP_SITE: sites.site } : {}), ...(preview ? { CLOUDFLARE_SETUP_PREVIEW: preview.origin } : {}), ...env };
    execFile(process.execPath, [SCRIPT, stage, ...args], { cwd: where.site, env: e, timeout: 75_000 }, (err, stdout, stderr) => {
      // R10: the token is never printed.
      assert.ok(!stdout.includes(TOKEN) && !stderr.includes(TOKEN), 'the token was printed');
      resolve({ code: err ? (err.code ?? `killed: ${err.signal ?? 'timeout'}`) : 0, out: stdout, err: stderr, ms: Date.now() - started });
    });
  });
}
const codeOf = (r) => /--confirm ([0-9a-f]{16})/.exec(r.out)?.[1];

// A scenario: a site, the stub API with `state`, the stub nameserver serving what the stub holds, and
// the Worker's version link. `state` may be a function of the site's branch heads. Unless the test
// says `worker: 'none'` (or puts its own in state.workers), the Worker is there and serves main's head.
async function scenario(stateOrFn, fn, siteOpts = {}) {
  const where = makeSite(siteOpts);
  const state = typeof stateOrFn === 'function' ? stateOrFn(where.heads) : stateOrFn;
  state.heads = where.heads;
  if (siteOpts.worker !== 'none' && !state.workers[WORKER]) state.workers[WORKER] = worker({ serves: where.heads.main });
  const api = await startApi(state);
  const preview = await startPreview(state);
  let silent = false;
  const dns = await startDns(servedBy(state, { silent: () => silent }));
  try {
    return await fn({ where, api, dns, preview, state, setSilent: (v) => { silent = v; }, go: (args = [], o = {}) => run(where, args, { api, dns, preview, ...o }) });
  } finally {
    await api.close();
    await dns.close();
    await preview.close();
  }
}

// A finished setup: the zone's settings and Bot Management as the checklist wants them, and the Worker
// serving the head of main.
function finishedState(heads, over = {}) {
  const s = freshState(over);
  s.heads = heads;
  s.workers[WORKER] = worker({ serves: heads.main });
  s.settings = { always_use_https: 'on', min_tls_version: '1.2', email_obfuscation: 'off', nel: { enabled: false } };
  Object.assign(s.bot, { fight_mode: false, bot_preference_sync_enabled: false });
  return s;
}
const onlyReads = (api) => assert.deepEqual(api.writes().map((e) => `${e.method} ${e.path}`), [], 'nothing may be written');

// ================================================================ the stub is the captures

test('the stub answers a project PATCH as Cloudflare did: what a PATCH leaves out stays (T1-048 to T1-061)', () => {
  const state = freshState();
  const p = fixture('T1-027').response.result;
  state.projects = [JSON.parse(JSON.stringify(p))];
  for (const n of ['048', '049', '050', '051', '052', '053', '061']) {
    const f = fixture(`T1-${n}`);
    const r = handle(state, f.request.method, f.request.path.replace(/^\/accounts\/[^/]+\/pages\/projects\/([^/]+)$/, '/accounts/a/pages/projects/$1'), new URLSearchParams(), f.request.body);
    assert.equal(r.status, f.status, `T1-${n}: status`);
    if (f.status !== 200) {
      assert.deepEqual(r.body.errors, f.response.errors, `T1-${n}: Cloudflare's words`);
      continue;
    }
    const pick = (x) => ({
      production_branch: x.production_branch, source_branch: x.source.config.production_branch, build_config: x.build_config,
      production: { env_vars: x.deployment_configs.production.env_vars, fail_open: x.deployment_configs.production.fail_open },
      preview: { env_vars: x.deployment_configs.preview.env_vars, fail_open: x.deployment_configs.preview.fail_open },
    });
    assert.deepEqual(pick(r.body.result), pick(f.response.result), `T1-${n}: the project after the PATCH`);
  }
});

test('the stub answers Bot Management as Cloudflare did: refusals, fields left out kept (T2-059 to T2-077)', () => {
  const state = freshState();
  state.bot = fixture('T2-040').response.result;
  const call = (capture) => {
    const f = fixture(capture);
    return { f, r: handle(state, f.request.method, '/zones/z/bot_management', new URLSearchParams(), f.request.body) };
  };
  for (const [put, after] of [['T2-059', 'T2-060'], ['T2-061', 'T2-062'], ['T2-063', 'T2-064'], ['T2-065', 'T2-066'], ['T2-073', 'T2-077']]) {
    const { f, r } = call(put);
    assert.equal(r.status, f.status, `${put}: status`);
    if (f.status !== 200) assert.deepEqual(r.body.messages, f.response.messages, `${put}: Cloudflare's words`);
    const { f: g, r: back } = call(after);
    assert.deepEqual(back.body.result, g.response.result, `${after}: Bot Management read back after ${put}`);
  }
  // Every PUT of the trials sent is_robots_txt_managed; the script never does (T2-065 refused it true).
  for (const c of ['T1-080', 'T2-059', 'T2-061', 'T2-063', 'T2-065', 'T2-073']) assert.ok('is_robots_txt_managed' in fixture(c).request.body, c);
});

test('G: the stub replays the fourth trial: a partial ai_agents is merged per key, as Cloudflare did (T4-001 to T4-011)', () => {
  const state = freshState();
  state.bot = fixture('T4-001').response.result;
  const call = (capture) => {
    const f = fixture(capture);
    return { f, r: handle(state, f.request.method, '/zones/z/bot_management', new URLSearchParams(), f.request.body) };
  };
  for (const [put, after] of [['T4-002', 'T4-003'], ['T4-004', 'T4-005'], ['T4-006', 'T4-007'], ['T4-008', 'T4-009'], ['T4-010', 'T4-011']]) {
    const { f, r } = call(put);
    assert.equal(r.status, f.status, `${put}: status`);
    assert.deepEqual(r.body.result, f.response.result, `${put}: the answer to the PUT`);
    const { f: g, r: back } = call(after);
    assert.equal(back.status, g.status, `${after}: status`);
    assert.deepEqual(back.body.result, g.response.result, `${after}: Bot Management read back after ${put}`);
  }
  // Written out by hand, so the loop above cannot pass by comparing the stub with itself: T4-008 sent
  // only google_agent, and anthropic_agent, blocked at T4-002, stayed blocked.
  assert.deepEqual(fixture('T4-008').request.body.ai_agents, { google_agent: 'block' });
  assert.deepEqual(fixture('T4-009').response.result.ai_agents, { anthropic_agent: 'block', google_agent: 'block', instinct: 'disabled', muse: 'disabled', openai_agent: 'disabled' });
});

test('the stub answers zone settings and records as Cloudflare did (T1-067 to T1-078, T1-143 to T1-146)', () => {
  const state = freshState();
  for (const n of ['067', '068', '069', '070']) {
    const r = fixture(`T1-${n}`).response.result;
    state.settings[r.id] = r.value;
  }
  for (const [write, back] of [['071', '072'], ['073', '074'], ['075', '076'], ['077', '078']]) {
    const f = fixture(`T1-${write}`);
    const id = f.request.path.split('/').pop();
    assert.equal(handle(state, 'PATCH', `/zones/z/settings/${id}`, new URLSearchParams(), f.request.body).status, 200);
    const r = handle(state, 'GET', `/zones/z/settings/${id}`, new URLSearchParams(), null);
    assert.deepEqual(r.body.result.value, fixture(`T1-${back}`).response.result.value, `T1-${back}`);
  }
  // A record: the trial's host had a CNAME (www here), so a second address record there is refused.
  state.dns = [{ id: 'r1', type: 'CNAME', name: `spike.${ZONE.name}`, content: `${REPO}.pages.dev`, proxied: true }];
  for (const n of ['143', '144', '145', '146']) {
    const f = fixture(`T1-${n}`);
    const r = handle(state, 'POST', '/zones/z/dns_records', new URLSearchParams(), f.request.body);
    assert.equal(r.status, f.status, `T1-${n}: status`);
    if (f.status === 200) assert.equal(r.body.result.content, f.response.result.content, `T1-${n}: stored as sent, quotes and all`);
    else assert.deepEqual(r.body.errors, f.response.errors, `T1-${n}: Cloudflare's words`);
  }
});

test('the list of projects carries what the script reads from it, and the deployment call\'s form is the trial helper\'s (T1-019, T1-030)', () => {
  // T1-019: every item has its source (owner and repository), domains and settings; a Direct Upload
  // project has no source at all. The script picks the project from the list and decides from a read of it.
  const items = fixture('T1-019').response.result;
  for (const p of items) for (const k of ['name', 'subdomain', 'domains', 'deployment_configs', 'production_branch']) assert.ok(k in p, `${p.name}: ${k}`);
  assert.deepEqual(items.filter((p) => !p.source).map((p) => p.name), ['other-site-3'], 'the Direct Upload project has no source');
  for (const p of items.filter((x) => x.source)) assert.ok(p.source.config.owner && p.source.config.repo_name, p.name);
  assert.ok(items.some((p) => p.name !== p.subdomain.replace(/\.pages\.dev$/, '')), 'a name is not always the first part of the address');
  // T1-030's form is what the helper's "@form" branch sent, read from the helper itself.
  const helper = readFileSync(path.join(FIXTURES, 'trial-helper.txt'), 'utf8');
  const line = /-H 'Content-Type: (multipart\/form-data; boundary=[^']+)' --data-binary \$'([^']*)'/.exec(helper);
  assert.ok(line && /\[ "\$n_f" -eq 0 \]/.test(helper), 'the helper sends an empty form when "@form" has no fields');
  assert.deepEqual(fixture('T1-030').request.body.emptyForm, { contentType: line[1], bytes: line[2].replace(/\\r\\n/g, '\r\n') });
});

// ================================================================ the fixtures hold made-up values only

// Follow-up W5 of the plan's second gate: the fixtures come from real accounts, and check_clean.sh
// looks for listed names, emails and secrets, not ids. So every string and every key in them must be
// a made-up id, hash, date or commit message (matched by pattern: a made-up id is mostly zeros,
// clean-captures.mjs), or be on fixtures/cloudflare-api/allowed-values.json, and so must every number.
// A host, an address or a request path passes when each of its parts does (a number only in a request
// path). Nothing passes
// for looking harmless: a value not on the list fails, and is added only after a person has looked.
const ALLOWED = JSON.parse(readFileSync(path.join(FIXTURES, 'allowed-values.json'), 'utf8'));
const MADE_UP = [/^c0ffee0{16}\d{10}$/, /^ba5e0{26}\d{10}$/, /^f00d0{50}\d{10}$/, /^d\d{7}-0000-4000-8000-000000000000$/, /^d\d{7}$/,
  /^100000\d$/, /^\d{4}-\d{2}-\d{2}(T[\d:.]+Z)?$/, /^Made-up commit message \d+$/, /^T[1-4]-\d{3}$/, /^R04-\d{3}$/];
function notMadeUp(fixtures, allowed = ALLOWED) {
  const strings = new Set(allowed.strings);
  const tokens = new Set(allowed.tokens);
  const keys = new Set(allowed.keys);
  const numbers = new Set(allowed.numbers);
  const madeUp = (v) => MADE_UP.some((re) => re.test(v));
  const bad = [];
  const string = (where, v) => {
    if (madeUp(v) || strings.has(v)) return;
    if (!/\s/.test(v) && /[/.]/.test(v) && /[a-z]/i.test(v)) {
      const parts = v.split(/[/.:?&=]+/).filter(Boolean);
      if (parts.every((t) => madeUp(t) || tokens.has(t) || (v.startsWith('/') && /^\d{1,3}$/.test(t)))) return;
    }
    bad.push(`${where}: "${v.slice(0, 80)}"`);
  };
  const walk = (where, o) => {
    if (typeof o === 'string') string(where, o);
    else if (typeof o === 'number' && !numbers.has(o)) bad.push(`${where}: number ${o}`);
    else if (Array.isArray(o)) o.forEach((x) => walk(where, x));
    else if (o && typeof o === 'object') {
      for (const [k, v] of Object.entries(o)) {
        if (!madeUp(k) && !keys.has(k)) bad.push(`${where}: key "${k}"`);
        walk(where, v);
      }
    }
  };
  for (const { file, data } of fixtures) walk(file, data);
  return bad;
}

test('every string, key and number in the fixtures is a made-up value or on the list of allowed values', () => {
  const fixtures = allFixtures();
  assert.ok(fixtures.length > 50, 'the fixtures are there');
  // A file's name is the capture's number and the trial's own label for the call, nothing else.
  for (const { file } of fixtures) {
    assert.match(file, /^T[1-4]-\d{3}-[a-z0-9_-]+\.json$/, file);
    assert.doesNotMatch(file, /[0-9a-f]{16}/i, `${file}: a run of hexadecimal digits in a file name`);
  }
  assert.deepEqual(notMadeUp(fixtures), []);
});

test('every string, key and number in the Workers fixtures is a made-up value or on their own list', () => {
  const fixtures = allWorkersFixtures();
  assert.equal(fixtures.length, 12, 'the twelve captures of row 0.4 are there');
  for (const { file } of fixtures) {
    assert.match(file, /^R04-\d{3}-[a-z0-9_-]+\.json$/, file);
    assert.doesNotMatch(file, /[0-9a-f]{16}/i, `${file}: a run of hexadecimal digits in a file name`);
  }
  const allowed = JSON.parse(readFileSync(path.join(WORKERS_FIXTURES, 'allowed-values.json'), 'utf8'));
  assert.deepEqual(notMadeUp(fixtures, allowed), []);
  // The check can fail here too: a real-looking account id, a name and an address are each caught.
  const plants = [
    ['an account id', (f) => { f.request.path = '/client/v4/accounts/5f3a9c1e2b4d6f8091a2b3c4d5e6f708/workers/subdomain'; }, 'R04-001'],
    ['a Worker\'s name', (f) => { f.response.result[0].service = 'elodies-shop'; }, 'R04-005'],
    ['an IP address', (f) => { f.response.result[0].content = '203.0.113.7'; }, 'R04-010'],
  ];
  for (const [what, plant, capture] of plants) {
    const planted = allWorkersFixtures();
    plant(planted.find((x) => x.data.capture === capture).data);
    assert.notDeepEqual(notMadeUp(planted, allowed), [], `${what} (${capture}) passed the check`);
  }
});

test('the fixture check catches what earlier versions let through, wherever it is put', () => {
  // Each plant is one value a review round showed a looser check would miss.
  const plants = [
    ['a name in a rule description', (f) => { f.response.result.rules[0].description = 'Élodie'; }, 'T1-082'],
    ['a lower-case name in a description', (f) => { f.response.result.rules[0].description = 'elodie'; }, 'T1-082'],
    ['a branch a person named', (f) => { f.response.result[0].deployment_trigger.metadata.branch = 'anna-fixes-imprint'; }, 'T1-040'],
    ['a production branch', (f) => { f.response.result[0].production_branch = 'relaunch'; }, 'T1-019'],
    ['a preview branch rule', (f) => { f.response.result[0].source.config.preview_branch_includes = ['relaunch']; }, 'T1-019'],
    ['a root folder', (f) => { f.response.result[0].build_config.root_dir = 'elodie'; }, 'T1-019'],
    ['a 64-hex hash', (f) => { f.response.result[1].deployment_configs.production.wrangler_config_hash = 'c0ba9c31764c1405b2d3396e77b5cd0c3402e8a19529b926be73cd0b5aab5f3d'; }, 'T1-019'],
    ['a host label under a made-up domain', (f) => { f.response.result.name = 'elodie.lenas-backstube.example'; }, 'T1-143'],
    ['a random-looking id', (f) => { f.response.result.id = '5f3a9c1e2b4d6f8091a2b3c4d5e6f708'; }, 'T1-018'],
    ['an id beside an underscore', (f) => { f.response.result.name = 'prefix_5f3a9c1e2b4d6f8091a2b3c4d5e6f708'; }, 'T1-018'],
    ['an IP address', (f) => { f.response.result.content = '203.0.113.7'; }, 'T1-143'],
    ['an email address', (f) => { f.response.result.comment = 'lena@example.com'; }, 'T1-143'],
    ['an account name', (f) => { f.response.result[0].account.name = "Bakery Mueller's Account"; }, 'T1-002'],
    ['a variable a person named', (f) => { f.response.result.deployment_configs.production.env_vars = { ANNA_TOKEN: { type: 'secret_text', value: '' } }; }, 'T1-027'],
    ['a top-level field named like the loader\'s own', (f) => { f.file = 'review-plant-private-person'; }, 'T1-001'],
    ['a number no capture had', (f) => { f.response.result.ttl = 4242424; }, 'T1-143'],
  ];
  for (const [what, plant, capture] of plants) {
    const fixtures = allFixtures();
    const f = fixtures.find((x) => x.data.capture === capture).data;
    plant(f);
    assert.notDeepEqual(notMadeUp(fixtures), [], `${what} (${capture}) passed the check`);
  }
});

// ================================================================ the checklist stays the one list

test('decision 2: each line the script writes is the checklist\'s item, with its path, and its value is the checklist\'s', (t) => {
  if (!existsSync(CHECKLIST)) {
    // A copy of the skill outside the toolkit has no docs folder; CI runs this file in the toolkit.
    t.skip('docs/CLOUDFLARE-CHECKLIST.md is not next to this skill');
    return;
  }
  const text = readFileSync(CHECKLIST, 'utf8');
  const flat = text.replace(/\*\*|`/g, '').replace(/\s+/g, ' ');
  const items = [...text.matchAll(/^- \[ \] \*\*(.+?)\*\*/gm)].map((m) => m[1].replace(/[.:]$/, ''));
  for (const line of [...SETTINGS, ...BOT_LINES]) {
    assert.ok(items.includes(line.title), `the checklist has no item "${line.title}"`);
    assert.ok(flat.includes(line.path), `the checklist does not say "${line.path}"`);
  }
  // Section 6's table of what is written: "| <setting> | <call> `field`, `field` | `<value as JSON>` |".
  const six = text.slice(text.indexOf('## 6.'));
  const rows = six.split('\n').filter((l) => /^\|.*`/.test(l)).map((l) => l.split('|').map((c) => c.trim()));
  const valueIn = (field) => {
    const row = rows.find((cells) => cells.some((c, i) => i < cells.length - 2 && c.includes(`\`${field}\``)));
    if (!row) return undefined;
    const v = /`([^`]+)`/.exec(row[row.length - 2])?.[1];
    return v === undefined ? undefined : JSON.parse(v);
  };
  for (const s of SETTINGS) assert.deepEqual(valueIn(s.api), s.value, `section 6 gives ${s.api} another value, or none`);
  for (const b of BOT_LINES) for (const [field, v] of Object.entries(b.fields)) assert.deepEqual(valueIn(field), v, `section 6 gives ${field} another value, or none`);
  assert.deepEqual(valueIn('ai_agents'), 'disabled', 'section 6 gives ai_agents another value, or none (each agent the first read lists)');
  assert.ok(/Zone → DNS → Edit/.test(six), 'section 6\'s table has the DNS row the setup writes records with');
  assert.ok(/\| Account → Workers Scripts → Edit \|/.test(six), 'section 6\'s table has the Workers row the setup reads and attaches with');
  assert.ok(!/Cloudflare Pages → Edit/.test(six), 'section 6 asks for no Pages permission any more');
});

// ================================================================ small parts

test('15: a record given with name and target swapped is refused before anything is asked', async () => {
  // Bing's record is a CNAME from 32 hexadecimal characters to verify.bing.com; the launch day's had them the other way round.
  assert.throws(() => parseRecord('CNAME verify.bing.com 0123456789abcdef0123456789abcdef'), /look swapped/);
  assert.equal(looksSwapped({ type: 'CNAME', name: '0123456789abcdef0123456789abcdef', content: 'verify.bing.com' }), null);
  assert.match(looksSwapped({ type: 'CNAME', name: 'www', content: 'pagesdev' }), /has no dot/);
  assert.deepEqual(parseRecord('TXT @ google-site-verification=abc def'), { type: 'TXT', name: '@', content: 'google-site-verification=abc def' });
  assert.throws(() => parseRecord('MX @ 10 mail.example.com'), UsageError);
  await scenario(freshState(), async ({ api, go }) => {
    const r = await go(['--record', 'CNAME verify.bing.com 0123456789abcdef0123456789abcdef']);
    assert.equal(r.code, 2);
    assert.match(r.err, /name and target look swapped/);
    assert.equal(api.log.length, 0, 'nothing was asked of Cloudflare');
  });
});

test('the owner and repository come from the remote in any of its forms', () => {
  for (const u of [`https://github.com/${OWNER}/${REPO}.git`, `https://lena:secret@github.com/${OWNER}/${REPO}`, `git@github.com:${OWNER}/${REPO}.git`, `ssh://git@github.com/${OWNER}/${REPO}.git`]) {
    assert.deepEqual(githubRepo(u), { owner: OWNER, repo: REPO }, u);
  }
  assert.equal(githubRepo('https://gitlab.com/lena/site.git'), null);
});

test('the code names the end state: the same inputs give the same code, a --skip or a host gives another', () => {
  const base = { account: ACCOUNT.id, worker: WORKER, repository: `${OWNER}/${REPO}`, productionBranch: 'production', zone: ZONE.id, skip: [], hosts: [HOST], records: [] };
  assert.match(setupCode(base), /^[0-9a-f]{16}$/);
  assert.equal(setupCode(base), setupCode({ ...base, repository: `${OWNER.toUpperCase()}/${REPO}` }), 'GitHub names compare without case');
  assert.notEqual(setupCode(base), setupCode({ ...base, skip: ['tls'] }));
  assert.notEqual(setupCode(base), setupCode({ ...base, hosts: [HOST, `shop.${HOST}`] }));
  assert.equal(setupCode({ ...base, skip: SKIP_IDS, hosts: [] }), setupCode({ ...base, skip: SKIP_IDS, hosts: [HOST] }), 'with every setting left out, no host is named');
  // The list: the code of a question fits what is left of it, never a list with something more.
  const listed = ['setting:email', 'setting:tls', 'record:aaaa'];
  const code = setupCode(base, listed);
  assert.notEqual(code, setupCode(base, ['setting:email']));
  const possible = ['setting:email', 'setting:tls', 'setting:https', 'record:aaaa'];
  assert.equal(codeFits(code, base, ['setting:email'], possible), true, 'tls and the record done since: still fits');
  assert.equal(codeFits(code, base, listed, possible), true);
  assert.equal(codeFits(code, base, ['setting:email', 'setting:https'], possible), false, 'a line the question did not list');
  assert.notEqual(setupCode(base), setupCode({ ...base, worker: 'another-worker' }), 'the Worker is in the end state');
});


test('12: two proxied hosts: every setting line names both; --skip tls leaves TLS out, gives another code, and is not written', () => {
  const s = freshState();
  s.dns = [
    { id: 'a1', type: 'A', name: HOST, content: '192.0.2.10', proxied: true },
    { id: 'a2', type: 'CNAME', name: `shop.${HOST}`, content: 'shops.example.com', proxied: true },
  ];
  return scenario(s, async ({ api, go, state }) => {
    const r = await go();
    for (const title of ['Always Use HTTPS', 'Minimum TLS Version', 'Email Address Obfuscation', 'Network Error Logging']) {
      const block = r.out.slice(r.out.indexOf(title)).split(/\n {2}\s?\d+\. /)[0];
      assert.match(block, /the hosts that run through Cloudflare are lenas-backstube\.example, shop\.lenas-backstube\.example/, title);
      assert.match(block, /For a visitor there:/, title);
    }
    const skipped = await go(['--skip', 'tls']);
    assert.doesNotMatch(skipped.out.split('Left out')[0], /Minimum TLS Version/);
    assert.match(skipped.out, /Left out on purpose \(--skip\): Minimum TLS Version stays 1\.0/);
    assert.notEqual(codeOf(skipped), codeOf(r));
    assert.equal((await go(['--confirm', codeOf(r), '--skip', 'tls'])).code, 3, 'the old code changes nothing');
    onlyReads(api);
    await go(['--skip', 'tls', '--confirm', codeOf(skipped)]);
    assert.equal(state.settings.min_tls_version, '1.0', 'TLS was not written');
    assert.equal(state.settings.always_use_https, 'on');
    assert.ok(!api.writes().some((e) => e.path.endsWith('/min_tls_version')));
  });
});

test('13: Bot Fight Mode on and training blocked: one PUT sets the checklist\'s values; with --skip ai the AI fields go as read', async () => {
  // enable_js and cf_robots_variant are no line of the checklist: they go as read, whatever they are.
  const blocked = () => Object.assign(freshState().bot, { fight_mode: true, enable_js: true, cf_robots_variant: 'off', ai_training: botOf(AI.block).ai_training, bot_preference_sync_enabled: true, crawler_protection: 'enabled' });
  await scenario(freshState({ bot: blocked() }), async ({ api, go }) => {
    await go(['--confirm', codeOf(await go())]);
    const put = api.writes().find((e) => e.method === 'PUT');
    assert.deepEqual(put.body, {
      fight_mode: false, enable_js: true, ai_bots_protection: 'disabled', ai_search: 'disabled', ai_user: 'disabled', ai_training: 'disabled',
      crawler_protection: 'disabled', content_bots_protection: 'disabled', cf_robots_variant: 'off', bot_preference_sync_enabled: false,
    });
  });
  await scenario(freshState({ bot: blocked() }), async ({ api, go }) => {
    await go(['--skip', 'ai', '--confirm', codeOf(await go(['--skip', 'ai']))]);
    const put = api.writes().find((e) => e.method === 'PUT');
    assert.deepEqual(put.body, {
      fight_mode: false, enable_js: true, ai_bots_protection: 'disabled', ai_search: 'disabled', ai_user: 'disabled', ai_training: 'block',
      crawler_protection: 'enabled', content_bots_protection: 'disabled', cf_robots_variant: 'off',
    });
  });
});

test('13b: a field the PUT did not mean to change that reads back otherwise makes that line "by hand", with 1', () =>
  scenario(freshState({ bot: Object.assign(freshState().bot, { fight_mode: true }) }), async ({ go, state }) => {
    const code = codeOf(await go());
    state.after = (e) => { if (e.method === 'PUT') state.bot.is_robots_txt_managed = true; };
    const r = await go(['--confirm', code]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /by hand\s+Bot Fight Mode: Off: Cloudflare accepted the change, but is_robots_txt_managed reads true, not false/);
  }));

// ---------------------------------------------------------------- the AI bot policies' notes
// The plan's scenarios S1 to S10 (docs/reviews/SKILL-PLAN-cloudflare-training-warning.md). Each
// zone's Bot Management is the third trial's read after one choice in the dashboard.
const AI = {
  allow: 'T3-010', block: 'T3-002', adsBlock: 'T3-003', disallowSyncOff: 'T3-007', disallowSyncOn: 'T3-006',
  searchBlock: 'T3-008', agentAdsBlock: 'T3-009',
};
const botOf = (capture, over = {}) => Object.assign(fixture(capture).response.result, over);
// Any line a note opens with; a run that prints none of these printed no note.
const NOTE = /Training is set to|Training was |Training read |Search is set to|Agent is set to|Search read |Agent read |Block AI bots setting|Bot Preference Sync is off|Bot Preference Sync reads|a value this kit does not know|Cloudflare's way to refuse AI training/;
// The ask, then the yes, for a zone holding `bot`: both outputs and the PUT, if any.
const aiRun = (bot, args = [], { before } = {}) => scenario(freshState({ bot }), async ({ api, go, state }) => {
  const ask = await go(args);
  if (before) before(state);
  const done = await go([...args, '--confirm', codeOf(ask)]);
  return { ask, done, put: api.writes().find((e) => e.method === 'PUT'), state };
});
// The question code a zone holding `bot` gets, and the one it gets holding `other`, on the same site
// (a code names the commit, so two sites never share one).
const twoCodes = (bot, other, args = []) => scenario(freshState({ bot }), async ({ go, state }) => {
  const first = codeOf(await go(args));
  state.bot = other;
  return [first, codeOf(await go(args))];
});

test('S9: Allow everywhere, as captured or as the kit leaves it, gives no note in any state', async () => {
  for (const c of ['T3-001', 'T3-010', 'T3-013', 'T2-040']) {
    for (const st of ['change', 'as-is', 'skipped', 'unread', 'done', 'hand', 'launch']) assert.deepEqual(aiNotes(botOf(c), st), [], `${c} ${st}`);
  }
  // The same check sees Block, so it cannot pass with no note code: C2's value swapped for C9's.
  assert.ok(aiNotes(botOf(AI.block), 'change').length > 0);
  assert.deepEqual(aiNotes(botOf(AI.block, { ai_training: botOf(AI.allow).ai_training }), 'change'), []);
  for (const c of [AI.allow, 'T2-040']) {
    const r = await aiRun(botOf(c));
    assert.doesNotMatch(r.ask.out + r.done.out, NOTE, c);
  }
});

// Cloudflare is retiring Managed robots.txt (BUGLOG 2026-10-30): once it drops the field from both
// reads, the change must still read back as done, not "by hand".
test('a Bot Management answer with no is_robots_txt_managed: the ai line is written and reads back done', async () => {
  const bot = botOf(AI.block);
  delete bot.is_robots_txt_managed;
  const r = await aiRun(bot);
  const withField = await aiRun(botOf(AI.block));
  assert.equal(r.done.code, withField.done.code, r.done.out);
  assert.ok(!('is_robots_txt_managed' in r.put.body), 'the PUT does not send the field');
  assert.ok(!('is_robots_txt_managed' in r.state.bot), 'the stub, as Cloudflare, does not return it');
  assert.match(r.done.out, /done\s+AI crawlers: allow/);
  assert.match(r.done.out, /Training was Block and is now Allow \(do not block\)/);
  assert.doesNotMatch(r.done.out, /by hand|is_robots_txt_managed/);
});

test('S1 and S3: Training on Block: the ask warns that Google, Bing and Apple go too; the report says it is now Allow; code, PUT and exit as without the note', async () => {
  const blocked = await aiRun(botOf(AI.block));
  const plain = await aiRun(botOf(AI.searchBlock)); // the same change to the ai line, with no note in the ask
  assert.match(blocked.ask.out, /Training is set to Block\. Cloudflare says Block also keeps Googlebot, Bingbot and Applebot out, which affects search\. If you say yes, it becomes Allow \(do not block\)\. Cloudflare's way to refuse AI training and stay in Google, Bing and Apple search \(the kit has not tested how crawlers are treated\): choose Disallow for Training in the dashboard, turn Bot Preference Sync on there too \(choosing Disallow does not turn it on\), and run this with --skip ai\./);
  assert.doesNotMatch(plain.ask.out, NOTE);
  const [a, b] = await twoCodes(botOf(AI.block), botOf(AI.searchBlock));
  assert.equal(a, b);
  assert.equal(blocked.ask.code, plain.ask.code);
  assert.equal(blocked.put.body.ai_training, 'disabled');
  assert.deepEqual({ ...blocked.put.body, ai_training: 'x' }, { ...plain.put.body, ai_training: 'x' });
  assert.match(blocked.done.out, /Training was Block and is now Allow \(do not block\)\. Cloudflare's way to refuse AI training and stay in Google, Bing and Apple search/);
  assert.doesNotMatch(blocked.done.out, /Training is set to/);
  assert.equal(blocked.done.code, plain.done.code);
});

test('S2: Training on Block on pages with ads: the same warning, for pages that show ads', async () => {
  const r = await aiRun(botOf(AI.adsBlock));
  const plain = await aiRun(botOf(AI.searchBlock));
  const [a, b] = await twoCodes(botOf(AI.adsBlock), botOf(AI.searchBlock));
  assert.equal(a, b);
  assert.equal(r.ask.code, plain.ask.code);
  assert.equal(r.done.code, plain.done.code);
  assert.deepEqual(r.put.body, plain.put.body);
  assert.match(r.ask.out, /Training is set to Block on pages with ads\. Cloudflare says Block on pages with ads also keeps Googlebot, Bingbot and Applebot out on pages that show ads, which affects search\. If you say yes/);
  assert.match(r.done.out, /Training was Block on pages with ads and is now Allow/);
});

test('S4: Training on Block with --skip ai: the warning says this run leaves it; the code is the one Allow gives', async () => {
  const skip = ['--skip', 'ai'];
  const blocked = await aiRun(botOf(AI.block), skip);
  const allowed = await aiRun(botOf(AI.allow), skip);
  for (const out of [blocked.ask.out, blocked.done.out]) assert.match(out, /Training is set to Block\. Cloudflare says Block also keeps Googlebot, Bingbot and Applebot out, which affects search\. This run leaves it as it is\. Cloudflare's way to refuse AI training and stay in Google, Bing and Apple search \(the kit has not tested how crawlers are treated\): .*and keep running this with --skip ai\./);
  const [a, b] = await twoCodes(botOf(AI.block), botOf(AI.allow), skip);
  assert.equal(a, b);
  assert.equal(blocked.ask.code, allowed.ask.code);
  assert.equal(blocked.done.code, allowed.done.code);
  assert.ok(!blocked.put || blocked.put.body.ai_training === 'block', 'Training is not written');
});

test('S5a: the zone\'s records could not be read: Training is not written, and the warning says this run did not change it', async () => {
  // Every line is "by hand" then, so nothing is asked and nothing written: the one run says it all.
  await scenario(freshState({ bot: botOf(AI.block), refuse: { 'GET dns': 403 } }), async ({ api, go }) => {
    const r = await go();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /Training is set to Block\. Cloudflare says Block also keeps Googlebot, Bingbot and Applebot out, which affects search\. This run could not change it; the AI crawlers line says why\. Cloudflare's way to refuse AI training and stay in Google, Bing and Apple search \(the kit has not tested how crawlers are treated\): .*and run this with --skip ai\./);
    assert.deepEqual(api.writes(), [], 'Bot Management is not written, nor anything else');
  });
  // Disallow in the same state: the same claim, and S7's note when Sync is off.
  const notes = aiNotes(botOf(AI.disallowSyncOff), 'unread');
  assert.match(notes[0], /^Training is set to Disallow\. This run could not change it; the AI crawlers line says why\./);
  assert.match(notes[1], /^Bot Preference Sync is off, so Disallow writes no/);
});

test('S5b: a change Cloudflare did not confirm names what Training read before the run, and claims nothing about now', async () => {
  const unconfirmed = /Training read Block before this run; Cloudflare did not confirm the change, so look at it in the dashboard: .*AI Crawler and Agent access policies\.\n.*Cloudflare's way to refuse AI training and stay in Google, Bing and Apple search/;
  const cases = {
    'a refused PUT': (s) => { s.refuse['PUT bot'] = 403; },
    'a 502 to the PUT': (s) => { s.refuse['PUT bot'] = 502; },
    'a read-back that fails': (s) => { s.after = (e) => { if (e.method === 'PUT') s.refuse['GET bot'] = 503; }; },
    'a read-back that differs (13b)': (s) => { s.after = (e) => { if (e.method === 'PUT') s.bot.is_robots_txt_managed = true; }; },
  };
  for (const [name, before] of Object.entries(cases)) {
    const r = await aiRun(botOf(AI.block), [], { before });
    assert.equal(r.done.code, 1, name);
    assert.match(r.done.out, unconfirmed, name);
    assert.doesNotMatch(r.done.out, /Training was Block and is now Allow|Training is set to Block/, name);
  }
});

test('S6: Training on Disallow: the ask says the yes lets training crawlers in, and how to keep Disallow', async () => {
  const r = await aiRun(botOf(AI.disallowSyncOff));
  const plain = await aiRun(botOf(AI.searchBlock));
  const [a, b] = await twoCodes(botOf(AI.disallowSyncOff), botOf(AI.searchBlock));
  assert.equal(a, b);
  assert.equal(r.ask.code, plain.ask.code);
  assert.equal(r.done.code, plain.done.code);
  assert.deepEqual(r.put.body, plain.put.body);
  assert.match(r.ask.out, /Training is set to Disallow\. If you say yes, it becomes Allow \(do not block\), and AI training crawlers are let in\. To keep Disallow, run this with --skip ai\./);
  assert.match(r.done.out, /Training was Disallow and is now Allow \(do not block\)\./);
});

test('S7 and S9b: Disallow kept with --skip ai: with Sync off robots.txt carries no preference, said; with Sync on, no note', async () => {
  const off = await aiRun(botOf(AI.disallowSyncOff), ['--skip', 'ai']);
  for (const out of [off.ask.out, off.done.out]) assert.match(out, /Bot Preference Sync is off, so Disallow writes no no-training preference into robots\.txt\. To publish it there, turn Sync on in the dashboard/);
  const on = await aiRun(botOf(AI.disallowSyncOn), ['--skip', 'ai']);
  assert.doesNotMatch(on.ask.out + on.done.out, NOTE);
});

test('S8: Search, Agent or the older switch left as they are: one note each; in the ask the list already shows them', async () => {
  const search = await aiRun(botOf(AI.searchBlock), ['--skip', 'ai']);
  assert.match(search.ask.out, /Search is set to Block, and this run leaves it as it is\. Section 4 of the Cloudflare checklist/);
  const agent = await aiRun(botOf(AI.agentAdsBlock), ['--skip', 'ai']);
  assert.match(agent.ask.out, /Agent is set to Block on pages with ads, and this run leaves it as it is/);
  const older = await aiRun(fixture('T2-016').response.result, ['--skip', 'ai']);
  assert.match(older.ask.out, /The older Block AI bots setting is set to block, and this run leaves it as it is/);
  assert.match(older.ask.out, /Bot Preference Sync is off, so Disallow writes no/);
  const listed = await aiRun(botOf(AI.searchBlock));
  assert.match(listed.ask.out, /ai_search block → disabled/);
  assert.doesNotMatch(listed.ask.out + listed.done.out, NOTE);
});

test('S10: a value no capture showed, or a missing field: a note that the kit does not know it, in place of a guess', async () => {
  const odd = await aiRun(botOf(AI.block, { ai_training: 'block_everything' }));
  assert.match(odd.ask.out, /Training reads block_everything at the start of this run: a value this kit does not know, so it cannot say what it means for search/);
  assert.doesNotMatch(odd.ask.out, /Training is set to/);
  const bot = botOf(AI.allow);
  delete bot.ai_search;
  assert.match(aiNotes(bot, 'skipped').join('\n'), /^Search was missing from what Cloudflare returned at the start of this run: a value this kit does not know/);
  const noSync = botOf(AI.disallowSyncOff);
  delete noSync.bot_preference_sync_enabled;
  assert.deepEqual(aiNotes(noSync, 'skipped').map((n) => n.split(':')[0]), ['Bot Preference Sync was missing from what Cloudflare returned at the start of this run']);
  // Agent's "Block" counts as known only because a capture showed it in that field (T3-012).
  assert.deepEqual(aiNotes(botOf('T3-012'), 'skipped'), ['Agent is set to Block, and this run leaves it as it is. Section 4 of the Cloudflare checklist says what the kit sets there, and why.']);
  assert.match(aiNotes(botOf('T3-011'), 'skipped').join(), /^Search is set to Block on pages with ads/);
});

test('14: the token reads zone settings but may not change them: each refused one is "by hand" with its row; the rest ran; 1', () =>
  scenario(freshState({ refuse: { 'PATCH setting:always_use_https': 403, 'PATCH setting:min_tls_version': 403 } }), async ({ go, state }) => {
    const r = await go(['--confirm', codeOf(await go())]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /by hand\s+Always Use HTTPS: On: Cloudflare refused it \(403, code 10000\): the token needs the row Zone → Zone Settings → Edit/);
    assert.match(r.out, /by hand\s+Minimum TLS Version: TLS 1\.2: Cloudflare refused it/);
    assert.equal(state.settings.email_obfuscation, 'off');
    assert.deepEqual(state.settings.nel, { enabled: false });
    assert.equal(state.bot.bot_preference_sync_enabled, false);
  }));

test('16: Google\'s TXT at the apex goes beside the SPF record, which stays; a second run writes nothing', () => {
  const s = (h) => Object.assign(finishedState(h), { dns: [{ id: 'spf', type: 'TXT', name: HOST, content: '"v=spf1 include:_spf.example.com ~all"', proxied: false }] });
  return scenario(s, async ({ api, go, state }) => {
    const rec = ['--record', 'TXT @ google-site-verification=made-up-code-for-lena'];
    const q = await go(rec);
    assert.equal(q.code, 3, q.out);
    assert.match(q.out, /Write the record TXT lenas-backstube\.example → google-site-verification=made-up-code-for-lena, DNS only/);
    assert.match(q.out, /It goes beside the TXT records already there, which stay: "v=spf1 include:_spf\.example\.com ~all"/);
    const r = await go([...rec, '--confirm', codeOf(q)]);
    assert.equal(r.code, 0, r.out);
    const writes = api.writes();
    assert.deepEqual(writes.map((e) => `${e.method} ${e.path.replace(/\/zones\/[^/]+/, '/zones/Z')}`), ['POST /zones/Z/dns_records'], 'a create, never an update');
    assert.deepEqual(writes[0].body, { type: 'TXT', name: HOST, ttl: 1, proxied: false, content: '"google-site-verification=made-up-code-for-lena"' });
    assert.equal(state.dns.length, 2, 'the SPF record stays');
    assert.match(r.out, /done\s+TXT lenas-backstube\.example → google-site-verification=made-up-code-for-lena, DNS only\. Read back through the API; the nameservers show it/);
    const again = await go(rec);
    assert.equal(again.code, 0, again.out);
    assert.equal(api.writes().length, 1);
  });
});

test('17: a CNAME of the wanted name already points elsewhere: nothing is written, the line is "by hand" with both targets', () => {
  const s = (h) => Object.assign(finishedState(h), { dns: [{ id: 'c1', type: 'CNAME', name: `abcdef0123456789abcdef0123456789.${HOST}`, content: 'elsewhere.example.com', proxied: false }] });
  return scenario(s, async ({ api, go }) => {
    const r = await go(['--record', 'CNAME abcdef0123456789abcdef0123456789 verify.bing.com']);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /already has CNAME elsewhere\.example\.com; this one would point it to verify\.bing\.com/);
    onlyReads(api);
  });
});

test('17b: a --record CNAME at the site\'s own host, with no address record there, is asked and written as before the Workers change', () =>
  scenario((h) => finishedState(h), async ({ api, go }) => {
    const q = await go(['--record', 'CNAME @ verify.bing.com']);
    assert.equal(q.code, 3, q.out);
    assert.doesNotMatch(q.out, /gate: refused/);
    const r = await go(['--record', 'CNAME @ verify.bing.com', '--confirm', codeOf(q)]);
    assert.equal(r.code, 0, r.out);
    assert.deepEqual(writesOf(api).filter((e) => e.method === 'POST' && /dns_records$/.test(e.path)).map((e) => [e.body.type, e.body.name, e.body.content]), [['CNAME', HOST, 'verify.bing.com']]);
  }));

test('18: a record written that the nameservers do not show within the run: "written; the nameservers do not show it yet", status 0', () =>
  scenario((h) => finishedState(h), async ({ go, dns, setSilent }) => {
    setSilent(true);
    const rec = ['--record', 'TXT @ google-site-verification=lena'];
    const r = await go([...rec, '--confirm', codeOf(await go(rec))]);
    assert.equal(r.code, 0, r.out);
    assert.match(r.out, /written; the nameservers do not show it yet/);
    assert.ok(dns.asked.some((q) => q.name === HOST && q.type === 'TXT'), 'the nameserver was asked');
  }));

// ================================================================ launch

// The site's Worker config once the host is on the Worker: the route is committed.
const ROUTED = WRANGLER.replace('"workers_dev": false,', `"workers_dev": false,\n  "routes": [{ "pattern": "${HOST}", "custom_domain": true }],`);
// The apex's record before launch, as Cloudflare lists a record (R04-012's shape, made-up values).
const A_RECORD = { id: 'c0ffee00000000000000000000000050', type: 'A', name: HOST, content: '192.0.2.10', proxiable: true, proxied: false, ttl: 1, settings: {}, meta: {}, comment: null, tags: [] };
const clone = (o) => JSON.parse(JSON.stringify(o));
// A site ready for launch day: setup finished, the Worker serving main's head, the host not attached,
// and the apex holding one A record at the old host.
function launchState(heads, { record = A_RECORD, ...over } = {}) {
  const s = finishedState(heads, over);
  s.dns = record ? [clone(record)] : [];
  return s;
}
// The host attached to the Worker, as the attach leaves it: the domain, and Cloudflare's own record.
function attachHost(s) {
  s.dns = s.dns.filter((r) => r.name !== HOST);
  const r = handle(s, 'PUT', `/accounts/${ACCOUNT.id}/workers/domains`, new URLSearchParams(), { hostname: HOST, service: WORKER, zone_id: ZONE.id, environment: 'production' });
  assert.equal(r.status, 200);
  return s;
}
// A launch scenario: setup's, and the domain's own stub site. By default the config already has the
// route (a host already attached, as on a later run); `routed: false` is a site before its launch.
async function launchScenario(stateFn, fn, siteOpts = {}) {
  const { routed = true, ...rest } = siteOpts;
  return scenario(stateFn, async (x) => {
    const domain = await startSites(x.state);
    try {
      return await fn({ ...x, sites: domain, launch: (args = [], o = {}) => run(x.where, args, { api: x.api, dns: x.dns, preview: x.preview, sites: domain, stage: 'launch', ...o }) });
    } finally {
      await domain.close();
    }
  }, { ...rest, files: { ...(routed ? { 'wrangler.jsonc': ROUTED } : {}), ...(rest.files ?? {}) } });
}
// A finished launch: attached, the route committed, setup's settings in place; `bot` replaces the zone's.
const finishedLaunch = (h, bot) => {
  const s = attachHost(launchState(h));
  if (bot) s.bot = Object.assign(bot, { fight_mode: false });
  return s;
};
const botCalls = (api) => api.log.filter((e) => /bot_management/.test(e.path)).map((e) => e.method);
const AI_HEADING = 'The AI bot policies, as Cloudflare reads them now:';

// ---------------------------------------------------------------- personal agents (ai_agents)
// Release 0.35 PR 4. T4-001 is a zone with every agent disabled, T4-003 the same with anthropic_agent
// on block: Cloudflare's own captures of 2026-11-09, where changing ai_user left ai_agents alone.
// other_agent is made up, to catch code that knows only the five names Cloudflare listed that day.
const ALL_DISABLED = { anthropic_agent: 'disabled', google_agent: 'disabled', instinct: 'disabled', muse: 'disabled', openai_agent: 'disabled' };
const agentBot = (agents = {}, over = {}) => {
  const b = botOf('T4-003');
  b.ai_agents = { ...b.ai_agents, ...agents };
  return Object.assign(b, over);
};
// What setup sends for T4-003 with the ai line changed and nothing else: the fields as read, the
// ai line's own, and only the agent that changes.
const PUT_ONE_AGENT = {
  fight_mode: false, enable_js: false, ai_bots_protection: 'disabled', ai_search: 'disabled', ai_user: 'disabled', ai_training: 'disabled',
  crawler_protection: 'disabled', content_bots_protection: 'disabled', cf_robots_variant: 'policy_only', bot_preference_sync_enabled: false,
  ai_agents: { anthropic_agent: 'disabled' },
};
// The ask, then the yes, for a zone holding `bot`: both outputs, every PUT, and the stub.
const agentsRun = (bot, args = [], { before } = {}) => scenario(freshState({ bot }), async ({ api, go, state }) => {
  const ask = await go(args);
  if (before) before(state);
  const done = await go([...args, '--confirm', codeOf(ask)]);
  return { ask, done, puts: api.writes().filter((e) => e.method === 'PUT').map((e) => e.body), state };
});
const ASK_NOT_KNOWN_FORM = /By hand: AI crawlers: allow\. Cloudflare's ai_agents reads .*, a form this kit does not know\. Dashboard: /;
const DONE_NOT_KNOWN_FORM = /by hand\s+AI crawlers: allow: Cloudflare's ai_agents reads .*, a form this kit does not know\. Dashboard: /;

test('A: one agent on block, everything else allowed: the ask lists it, the PUT sends only it, the line reads back done and the report names it', async () => {
  const r = await agentsRun(agentBot());
  assert.match(r.ask.out, /\d+\. AI crawlers: allow \(ai_agents\.anthropic_agent block → disabled\)\./);
  assert.match(r.ask.out, /each personal AI agent Cloudflare lists is set to the API's disabled/);
  assert.match(r.ask.out, /Every personal agent ends disabled\./);
  assert.doesNotMatch(r.ask.out, /ai_agents\.google_agent|Already as the checklist wants: .*AI crawlers: allow/);
  assert.deepEqual(r.puts, [PUT_ONE_AGENT]);
  assert.deepEqual(r.state.bot.ai_agents, ALL_DISABLED);
  assert.match(r.done.out, /done\s+AI crawlers: allow \(personal agents were: anthropic_agent block\)\. Read back through the API only\./);
  assert.doesNotMatch(r.done.out, /by hand\s+AI crawlers/);
});

test('A0: every agent disabled and every other AI field allowed: the ai line reads "as is", with no ask and no PUT', async () => {
  const r = await agentsRun(botOf('T4-001'));
  assert.match(r.ask.out, /Already as the checklist wants: .*AI crawlers: allow/);
  assert.doesNotMatch(r.ask.out, /\d+\. AI crawlers: allow|ai_agents\./);
  assert.deepEqual(r.puts, []);
  assert.match(r.done.out, /as is\s+AI crawlers: allow\./);
});

test('B: the blocked agent with --skip ai: no ai_agents in the PUT, the agent stays, and the notes name it', async () => {
  const r = await agentsRun(agentBot({}, { fight_mode: true }), ['--skip', 'ai']);
  assert.equal(r.puts.length, 1);
  assert.ok(!('ai_agents' in r.puts[0]), JSON.stringify(r.puts[0]));
  assert.equal(r.state.bot.ai_agents.anthropic_agent, 'block');
  for (const out of [r.ask.out, r.done.out]) assert.match(out, /Personal agent anthropic_agent read block at the start of this run, and this run leaves it as it is\. Section 4 of the Cloudflare checklist/);
});

test('C: a zone whose Bot Management has no ai_agents: the PUT is the one test 13 pins, with none, and the line reads back done', async () => {
  const r = await aiRun(botOf(AI.block));
  assert.deepEqual(r.put.body, {
    fight_mode: false, enable_js: false, ai_bots_protection: 'disabled', ai_search: 'disabled', ai_user: 'disabled', ai_training: 'disabled',
    crawler_protection: 'disabled', content_bots_protection: 'disabled', cf_robots_variant: 'policy_only', bot_preference_sync_enabled: false,
  });
  assert.match(r.done.out, /done\s+AI crawlers: allow\. Read back/);
  assert.doesNotMatch(r.done.out, /personal agent|Personal agent|by hand/);
});

test('C2: Bot Fight Mode is "as is" when off, whatever ai_agents holds', async () => {
  for (const bot of [agentBot(), botOf('T4-001'), agentBot({}, { ai_agents: 'block' })]) {
    const r = await agentsRun(bot);
    assert.match(r.ask.out, /Already as the checklist wants: .*Bot Fight Mode: Off/, JSON.stringify(bot.ai_agents));
  }
});

test('D, I and M: an ai_agents that is not a plain object of strings: the ai line is "by hand" before any write, and no PUT carries ai_agents', async () => {
  const forms = { string: 'block', null: null, array: [], nested: { anthropic_agent: { x: 'block' } }, number: { anthropic_agent: 1 } };
  for (const [what, value] of Object.entries(forms)) {
    const r = await agentsRun(agentBot({}, { fight_mode: true, ai_agents: value }));
    assert.match(r.ask.out, ASK_NOT_KNOWN_FORM, what);
    assert.match(r.done.out, DONE_NOT_KNOWN_FORM, what);
    assert.match(r.done.out, /done\s+Bot Fight Mode: Off/, `${what}: the other line goes on`);
    assert.equal(r.puts.length, 1, what);
    assert.ok(!('ai_agents' in r.puts[0]), `${what}: ${JSON.stringify(r.puts[0])}`);
    assert.equal(r.done.code, 1, what);
    assert.match(r.done.out, /Personal agents \(ai_agents\) read .* at the start of this run: a value this kit does not know/, what);
  }
  // --skip ai wins over the refusal; the note names the unknown form.
  const skipped = await agentsRun(agentBot({}, { fight_mode: true, ai_agents: 'block' }), ['--skip', 'ai']);
  assert.doesNotMatch(skipped.ask.out + skipped.done.out, /a form this kit does not know\. Dashboard/);
  assert.match(skipped.done.out, /Personal agents \(ai_agents\) read block at the start of this run: a value this kit does not know/);
});

test('D2: ai_agents null with Training on Block: the notes do not blame the records, and the line says the ai_agents reason', async () => {
  // The "unread" state has several causes; here the zone's records were read fine.
  const bot = agentBot({}, { ai_training: botOf(AI.block).ai_training, ai_agents: null });
  const r = await agentsRun(bot);
  for (const out of [r.ask.out, r.done.out]) {
    assert.match(out, /Training is set to Block\. Cloudflare says Block also keeps Googlebot, Bingbot and Applebot out, which affects search\. This run could not change it; the AI crawlers line says why\./);
    assert.doesNotMatch(out, /records could not be read/);
  }
  assert.match(r.ask.out, ASK_NOT_KNOWN_FORM);
  assert.match(r.done.out, DONE_NOT_KNOWN_FORM);
});

test('M: an empty map has nothing to do and gives no note; an unknown string value gets a note, and the yes sets it to disabled', async () => {
  const empty = await agentsRun(agentBot({}, { ai_agents: {} }));
  assert.match(empty.ask.out, /Already as the checklist wants: .*AI crawlers: allow/);
  assert.deepEqual(empty.puts, []);
  assert.doesNotMatch(empty.ask.out + empty.done.out, /[Pp]ersonal agent/);
  const odd = await agentsRun(agentBot({ anthropic_agent: 'challenge' }));
  assert.match(odd.ask.out, /Personal agent anthropic_agent reads challenge at the start of this run: a value this kit does not know/);
  assert.match(odd.ask.out, /ai_agents\.anthropic_agent challenge → disabled/);
  assert.deepEqual(odd.puts, [PUT_ONE_AGENT]);
  assert.deepEqual(odd.state.bot.ai_agents, ALL_DISABLED);
});

test('E, E2 and E3: the PUT is accepted but ai_agents reads back otherwise: the ai line is "by hand" and names what it read', async () => {
  const wanted = '{"anthropic_agent":"disabled","google_agent":"disabled","instinct":"disabled","muse":"disabled","openai_agent":"disabled"}';
  const cases = {
    'E: one agent still on block': [(s) => { s.bot.ai_agents.anthropic_agent = 'block'; }, `ai_agents reads {"anthropic_agent":"block","google_agent":"disabled","instinct":"disabled","muse":"disabled","openai_agent":"disabled"}, not ${wanted}`],
    'E2: an agent the first read listed is gone': [(s) => { delete s.bot.ai_agents.google_agent; }, `ai_agents reads {"anthropic_agent":"disabled","instinct":"disabled","muse":"disabled","openai_agent":"disabled"}, not ${wanted}`],
    'E3: an array': [(s) => { s.bot.ai_agents = []; }, `ai_agents reads [], not ${wanted}`],
  };
  for (const [name, [set, words]] of Object.entries(cases)) {
    const r = await agentsRun(agentBot(), [], { before: (s) => { s.after = (e) => { if (e.method === 'PUT') set(s); }; } });
    assert.equal(r.done.code, 1, name);
    assert.ok(r.done.out.includes(`by hand  AI crawlers: allow: Cloudflare accepted the change, but ${words}.`), `${name}: ${r.done.out}`);
  }
});


test('H: a sixth agent the kit has never heard of: the ask, the PUT, the done line, the skip note and the launch note all name it', async () => {
  const bot = () => agentBot({ other_agent: 'block' });
  const r = await agentsRun(bot());
  assert.match(r.ask.out, /\(ai_agents\.anthropic_agent block → disabled, ai_agents\.other_agent block → disabled\)\./);
  assert.deepEqual(r.puts, [{ ...PUT_ONE_AGENT, ai_agents: { anthropic_agent: 'disabled', other_agent: 'disabled' } }]);
  assert.equal(r.state.bot.ai_agents.other_agent, 'disabled');
  assert.match(r.done.out, /\(personal agents were: anthropic_agent block, other_agent block\)/);
  const skipped = await agentsRun(bot(), ['--skip', 'ai']);
  assert.match(skipped.done.out, /Personal agent other_agent read block at the start of this run, and this run leaves it as it is/);
  await launchScenario((h) => finishedLaunch(h, bot()), async ({ launch }) => {
    const l = await launch();
    assert.match(l.out, /Personal agent other_agent read block at the start of this run, and launch day leaves it as it is/);
  });
});

test('J: an agent added between the ask and the yes makes a new code: the old one writes nothing, and the new question lists both', () =>
  scenario(freshState({ bot: agentBot() }), async ({ api, go, state }) => {
    const first = codeOf(await go());
    state.bot.ai_agents.other_agent = 'block';
    const r = await go(['--confirm', first]);
    assert.match(r.out, /does not fit this question/);
    assert.deepEqual(api.writes(), []);
    assert.notEqual(codeOf(r), first);
    assert.match(r.out, /ai_agents\.anthropic_agent block → disabled, ai_agents\.other_agent block → disabled/);
  }));

test('J2: another listed agent blocked between the ask and the yes: the yes still sets it, the end state the question named', () =>
  scenario(freshState({ bot: agentBot() }), async ({ api, go, state }) => {
    const first = codeOf(await go());
    state.bot.ai_agents.google_agent = 'block';
    const r = await go(['--confirm', first]);
    assert.doesNotMatch(r.out, /does not fit this question/);
    assert.deepEqual(api.writes().find((e) => e.method === 'PUT').body.ai_agents, { anthropic_agent: 'disabled', google_agent: 'disabled' });
    assert.deepEqual(state.bot.ai_agents, ALL_DISABLED);
    assert.match(r.out, /\(personal agents were: anthropic_agent block, google_agent block\)/);
  }));

test('K: the owner blocks another agent between the run\'s read and its PUT: the PUT leaves it out, nothing overwrites it, and the line is "by hand"', () =>
  scenario(freshState({ bot: agentBot() }), async ({ api, go, state }) => {
    const code = codeOf(await go());
    let hit = false;
    state.after = (e) => { if (!hit && e.method === 'GET' && /bot_management/.test(e.path)) { hit = true; state.bot.ai_agents.google_agent = 'block'; } };
    const r = await go(['--confirm', code]);
    assert.deepEqual(api.writes().find((e) => e.method === 'PUT').body.ai_agents, { anthropic_agent: 'disabled' });
    assert.equal(state.bot.ai_agents.google_agent, 'block');
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /by hand\s+AI crawlers: allow: Cloudflare accepted the change, but ai_agents reads \{"anthropic_agent":"disabled","google_agent":"block"/);
  }));

test('L: no ai_agents in the first read, but one agent blocked in the read-back: the ai line is "by hand" and names it', async () => {
  const r = await aiRun(botOf(AI.block), [], { before: (s) => { s.after = (e) => { if (e.method === 'PUT') s.bot.ai_agents = { anthropic_agent: 'block' }; }; } });
  assert.equal(r.done.code, 1, r.done.out);
  assert.ok(r.done.out.includes('Cloudflare accepted the change, but ai_agents reads {"anthropic_agent":"block"}, not {"anthropic_agent":"disabled"}.'), r.done.out);
});

test('N: Bot Fight Mode on and one agent blocked, the PUT refused: both bot lines are "by hand" with the refusal, and the note names the agent', async () => {
  const r = await agentsRun(agentBot({}, { fight_mode: true }), [], { before: (s) => { s.refuse['PUT bot'] = 403; } });
  assert.equal(r.done.code, 1, r.done.out);
  assert.match(r.done.out, /by hand\s+Bot Fight Mode: Off: Cloudflare refused it \(403/);
  assert.match(r.done.out, /by hand\s+AI crawlers: allow: Cloudflare refused it \(403/);
  assert.match(r.done.out, /Personal agent anthropic_agent read block at the start of this run; Cloudflare did not confirm the change, so look at it in the dashboard/);
  assert.equal(r.state.bot.ai_agents.anthropic_agent, 'block');
});

test('aiNotes for personal agents: a blocked, an ads-only and an unknown-valued agent, per state', () => {
  const where = BOT_LINES.find((b) => b.id === 'ai').path;
  const now = (agents) => ({ ...botOf('T4-001'), ai_agents: agents });
  const leaves = (v, who) => `Personal agent ${v[0]} read ${v[1]} at the start of this run, and ${who} leaves it as it is. Section 4 of the Cloudflare checklist says what the kit sets there, and why.`;
  for (const value of ['block', 'only_on_ad_pages']) {
    const n = now({ anthropic_agent: value, google_agent: 'disabled' });
    assert.deepEqual(aiNotes(n, 'skipped'), [leaves(['anthropic_agent', value], 'this run')]);
    assert.deepEqual(aiNotes(n, 'unread'), [leaves(['anthropic_agent', value], 'this run')]);
    assert.deepEqual(aiNotes(n, 'launch'), [leaves(['anthropic_agent', value], 'launch day')]);
    assert.deepEqual(aiNotes(n, 'hand'), [`Personal agent anthropic_agent read ${value} at the start of this run; Cloudflare did not confirm the change, so look at it in the dashboard: ${where}.`]);
    for (const st of ['change', 'done', 'as-is']) assert.deepEqual(aiNotes(n, st), [], `${value} ${st}`);
  }
  const unknown = now({ anthropic_agent: 'challenge', google_agent: 'block' });
  for (const st of ['change', 'done', 'skipped', 'hand']) {
    assert.ok(aiNotes(unknown, st).includes(`Personal agent anthropic_agent reads challenge at the start of this run: a value this kit does not know, so it cannot say what it means for search. Look at it in the dashboard: ${where}.`), st);
  }
  assert.deepEqual(aiNotes(now(null), 'change'), [`Personal agents (ai_agents) read null at the start of this run: a value this kit does not know, so it cannot say what it means for search. Look at it in the dashboard: ${where}.`]);
  const absent = botOf('T4-001');
  delete absent.ai_agents;
  assert.deepEqual(aiNotes(absent, 'skipped'), []);
  assert.deepEqual(aiNotes(now({}), 'skipped'), []);
});

test('LA1: Training on Block at launch: the report says what Block costs and how to keep a choice; nothing written', () =>
  launchScenario((h) => finishedLaunch(h, botOf(AI.block)), async ({ api, launch }) => {
    const r = await launch();
    assert.equal(r.code, 0, r.out);
    const notes = r.out.slice(r.out.indexOf(AI_HEADING), r.out.indexOf('Live: '));
    assert.ok(r.out.indexOf('The check of') < r.out.indexOf(AI_HEADING) && r.out.indexOf(AI_HEADING) < r.out.indexOf('Live: '), r.out);
    assert.match(notes, /Training is set to Block\. Cloudflare says Block also keeps Googlebot, Bingbot and Applebot out, which affects search\. Launch day changes no AI setting\. Cloudflare's way to refuse AI training and stay in Google, Bing and Apple search \(the kit has not tested how crawlers are treated\): choose Disallow for Training in the dashboard, turn Bot Preference Sync on there too \(choosing Disallow does not turn it on\), and run the setup stage with --skip ai from then on\./);
    assert.deepEqual(botCalls(api), ['GET']);
    assert.ok(!api.writes().some((e) => /bot_management/.test(e.path)));
  }));

test('LA2: Allow everywhere at launch: no AI note and no heading', () =>
  launchScenario((h) => finishedLaunch(h, botOf(AI.allow)), async ({ api, launch }) => {
    const r = await launch();
    assert.equal(r.code, 0, r.out);
    assert.ok(!r.out.includes(AI_HEADING), r.out);
    assert.doesNotMatch(r.out, NOTE);
    assert.deepEqual(botCalls(api), ['GET']);
  }));

test('LA2b: a launch that ends in 1 (Bot Fight Mode still on) still carries the Block note, from one read', () =>
  launchScenario((h) => { const s = finishedLaunch(h, botOf(AI.block)); s.bot.fight_mode = true; return s; }, async ({ api, launch }) => {
    const r = await launch();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /Training is set to Block\. .*Launch day changes no AI setting\./);
    assert.deepEqual(botCalls(api), ['GET']);
    assert.deepEqual(api.writes().filter((e) => /bot_management/.test(e.path)), []);
  }));

test('LA3: Disallow with Sync off at launch: the Sync note', () =>
  launchScenario((h) => finishedLaunch(h, botOf(AI.disallowSyncOff)), async ({ launch }) => {
    const r = await launch();
    assert.equal(r.code, 0, r.out);
    assert.match(r.out, /Bot Preference Sync is off, so Disallow writes no no-training preference into robots\.txt\./);
  }));

test('LA4: a refused or dropped Bot Management read at launch: one line, the same status, no note', async () => {
  for (const [what, set, words] of [
    ['403', (s) => { s.refuse['GET bot'] = 403; }, /Cloudflare refused it \(403.*Zone → Bot Management → Edit/],
    ['503', (s) => { s.refuse['GET bot'] = 503; }, /Cloudflare refused it: MADE: refused by the test/],
    ['a dropped connection', (s) => { s.drop['GET bot'] = 'reset'; }, /Cloudflare's API did not answer/],
  ]) {
    await launchScenario((h) => { const s = finishedLaunch(h, botOf(AI.block)); set(s); return s; }, async ({ launch }) => {
      const r = await launch();
      assert.equal(r.code, 0, `${what}: ${r.out}`);
      assert.match(r.out, /Bot Management could not be read: .*\. The notes on the AI bot policies are not shown; the setup stage, run again, shows them\./, what);
      assert.match(r.out, words, what);
      assert.doesNotMatch(r.out, /Training is set to/, what);
      assert.match(r.out, /Launched\. Status 0\./, what);
    });
  }
});

test('LA5: the question (3) and a wait for the domain (4) read no Bot Management', () =>
  launchScenario((h) => launchState(h, { bot: botOf(AI.block), siteDown: true }), async ({ api, launch }) => {
    const q = await launch();
    assert.equal(q.code, 3, q.out);
    const first = await launch(['--confirm', codeOf(q)]);
    assert.equal(first.code, 4, first.out);
    assert.deepEqual(botCalls(api), []);
    assert.doesNotMatch(q.out + first.out, NOTE);
  }, { routed: false }));

// The test's own timeout fails a read made outside the run's deadline instead of hanging the suite.
test('LA6: a Bot Management read that never answers ends the run with 4 at its deadline, before any report', { timeout: 90_000 }, () =>
  launchScenario((h) => { const s = finishedLaunch(h, botOf(AI.block)); s.drop['GET bot'] = 'silent'; return s; }, async ({ launch }) => {
    const r = await launch();
    assert.equal(r.code, 4, r.out);
    assert.match(r.out, /reached its time limit/);
    assert.ok(r.ms < 60_000, `took ${r.ms} ms`);
    assert.ok(!r.out.includes('The check of') && !r.out.includes('Live: '), r.out);
  }));

test("aiNotes at launch: one note per branch, each saying launch day changes nothing", () => {
  const one = (bot) => aiNotes(bot, 'launch');
  const tail = /Launch day changes no AI setting\. .*run the setup stage with --skip ai from then on\.$/;
  assert.match(one(botOf(AI.block))[0], tail);
  assert.match(one(botOf(AI.adsBlock))[0], /^Training is set to Block on pages with ads\. Cloudflare says Block on pages with ads also keeps Googlebot, Bingbot and Applebot out on pages that show ads, which affects search\. Launch day changes no AI setting\./);
  assert.deepEqual(one(botOf(AI.disallowSyncOff)), [`Bot Preference Sync is off, so Disallow writes no no-training preference into robots.txt. To publish it there, turn Sync on in the dashboard: ${BOT_LINES.find((b) => b.id === 'ai').path}.`]);
  assert.deepEqual(one(botOf(AI.disallowSyncOn)), []);
  assert.deepEqual(one(botOf(AI.searchBlock)), ['Search is set to Block, and launch day leaves it as it is. Section 4 of the Cloudflare checklist says what the kit sets there, and why.']);
  assert.deepEqual(one(botOf(AI.agentAdsBlock)), ['Agent is set to Block on pages with ads, and launch day leaves it as it is. Section 4 of the Cloudflare checklist says what the kit sets there, and why.']);
  assert.deepEqual(one(botOf(AI.allow)), []);
  assert.ok(one(botOf('T2-016')).includes('The older Block AI bots setting is set to block, and launch day leaves it as it is. Section 4 of the Cloudflare checklist says what the kit sets there, and why.'));
  // Hand-built from T3-010, since no capture has them.
  const missing = botOf(AI.allow); delete missing.ai_training;
  assert.match(one(missing)[0], /^Training was missing from what Cloudflare returned at the start of this run: a value this kit does not know/);
  assert.match(one(botOf(AI.allow, { ai_search: 'x' }))[0], /^Search reads x at the start of this run: a value this kit does not know/);
  assert.match(one(botOf(AI.disallowSyncOff, { bot_preference_sync_enabled: 'x' }))[0], /^Bot Preference Sync reads x at the start of this run: a value this kit does not know/);
});


// ================================================================ the launch's parts

test('the launch status table is the plan\'s, and covers every item of the check', (t) => {
  assert.deepEqual(Object.keys(LAUNCH_FAIL).sort(), CHECK_ITEMS.map((i) => i.id).sort(), 'one row per check item');
  const plan = path.join(HERE, '..', '..', '..', '..', 'docs', 'reviews', 'SKILL-PLAN-cloudflare-setup.md');
  if (!existsSync(plan)) { t.skip('the plan is not next to this skill'); return; }
  const rows = [...readFileSync(plan, 'utf8').matchAll(/^\| `([a-z-]+)` \| [^|]+ \| ([^|]+) \|$/gm)].map((m) => [m[1], m[2].trim()]);
  const read = (cell) => (/^1; 0 with `--skip ([a-z-]+)`$/.exec(cell)?.[1]) ?? (cell === '1' || cell.startsWith('1:') ? 1 : cell === '0' ? 0 : cell.startsWith('never') ? null : `?${cell}`);
  assert.deepEqual(Object.fromEntries(rows.map(([id, cell]) => [id, read(cell)])), LAUNCH_FAIL);
});

test('the launch\'s verdict follows the plan\'s order: no answer, then a counted failure, then 0', () => {
  const r = (id, state, extra = {}) => ({ id, state, ...extra });
  assert.equal(launchVerdict({ unanswered: [], results: [r('bot', 'fail'), r('analytics', 'fail')] }, ['bot']).code, 0);
  assert.equal(launchVerdict({ unanswered: [], results: [r('bot', 'fail')] }, ['nel']).code, 1);
  assert.equal(launchVerdict({ unanswered: [], results: [r('nel', 'fail')] }, ['nel']).code, 1, 'the switch\'s --skip is not the rule\'s');
  assert.equal(launchVerdict({ unanswered: [], results: [r('nel', 'fail')] }, ['nel-rule']).code, 0);
  assert.equal(launchVerdict({ unanswered: ['GPTBot x'], results: [r('domain', 'ok')] }, []).code, 1, 'an empty answer is never a pass');
  assert.equal(launchVerdict({ unanswered: [], results: [r('build', 'skip', { blocked: true })] }, []).code, 1);
  assert.equal(launchVerdict({ unanswered: [], results: [r('scripts', 'fail')] }, []).code, 1, 'an item that never fails gives 1 if it does');
});

test('the launch\'s small parts: a fixed text from a pattern, the differences that stop a build, the check\'s arguments', () => {
  assert.equal(fixedText('\\[MISSING:'), '[MISSING:');
  assert.equal(fixedText('\\[FEHLT:'), '[FEHLT:');
  assert.equal(fixedText('\\[MISS.*:'), null);
  assert.equal(fixedText('[A-Z]'), null);
  const args = checkArgs({ site: HOST, preview: `https://${versionHost(VERSION, WORKER)}`, commit: 'a'.repeat(40), timeoutS: 9, only: ['build', 'nel'], nameservers: ['192.0.2.53', '192.0.2.54'], configFile: 'workers.jsonc' });
  assert.deepEqual(args.slice(1), [HOST, '--json', '--timeout', '9', '--site', '.', '--config', 'workers.jsonc', '--preview', `https://${versionHost(VERSION, WORKER)}`, '--build', 'a'.repeat(40), '--only', 'build,nel', '--nameserver', '192.0.2.53,192.0.2.54']);
  assert.ok(!checkArgs({ site: 'http://127.0.0.1:1', preview: 'x', commit: 'a', timeoutS: 1, nameservers: null, configFile: 'wrangler.jsonc' }).includes('--nameserver'));
  assert.ok(LAUNCH_SKIP_IDS.every((id) => !SKIP_IDS.includes(id)));
});


test('32: a finished setup: no write, no question, status 0', () =>
  scenario((h) => finishedState(h), async ({ api, go }) => {
    const r = await go();
    assert.equal(r.code, 0, r.out);
    assert.doesNotMatch(r.out, /--confirm/);
    onlyReads(api);
  }));


test('33: a token with no end date, one reaching a second zone (on page 2), a refused verify, a refused zone list: refused before any write', async () => {
  const cases = [
    [{ token: { status: 'active', expires_on: null } }, /no end date\. Make one with an end date/],
    [{ zones: [zone(), zone({ id: 'c0ffee00000000000000000000000003', name: 'lenas-cafe.example' })], perPage: { zones: 1, projects: 10, deployments: 25 } }, /has DNS Edit in 2 zones \(lenas-backstube\.example, lenas-cafe\.example\)\. Make one limited to the site's own zone.*may need a few minutes/],
    [{ refuse: { 'GET verify': 403 } }, /did not accept the token .*revoked, or not valid yet/],
    [{ refuse: { 'GET zones': 403 } }, /refused to list the token's zones .*Zone → Zone → Read/],
  ];
  for (const [over, want] of cases) {
    const s = freshState(over);
    await scenario(s, async ({ api, go }) => {
      const r = await go();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, want);
      onlyReads(api);
      if (over.perPage) assert.ok(api.log.some((e) => e.path === '/zones' && /[?&]page=2\b/.test(e.query)), 'the second zone was on page 2, and page 2 was read');
    });
  }
});

test('34: the token in .dev.vars, tracked by git or not ignored: it stops before reading the file', async () => {
  for (const site of [{ devVars: `CLOUDFLARE_API_TOKEN=${TOKEN}\n`, trackDevVars: true }, { devVars: `CLOUDFLARE_API_TOKEN=${TOKEN}\n`, ignoreDevVars: false }]) {
    await scenario(freshState(), async ({ api, go }) => {
      const r = await go([], { token: null });
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, site.trackDevVars ? /git tracks \.dev\.vars.*The file was not read/ : /\.dev\.vars is not ignored by git.*The file was not read/);
      assert.equal(api.log.length, 0, 'the token went nowhere');
    }, site);
  }
  // Ignored and untracked: it is read, and used.
  await scenario((h) => finishedState(h), async ({ go }) => {
    const r = await go([], { token: null });
    assert.equal(r.code, 0, r.out);
  }, { devVars: `CLOUDFLARE_API_TOKEN=${TOKEN}\n` });
});


test('38: git runs without the token in its environment', async (t) => {
  if (process.platform === 'win32') { t.skip('the recording git is a shell script'); return; }
  const bin = path.join(scratch, 'bin');
  mkdirSync(bin, { recursive: true });
  const record = path.join(scratch, 'git-env.txt');
  const realGit = execFileSync('sh', ['-c', 'command -v git'], { encoding: 'utf8' }).trim();
  writeFileSync(path.join(bin, 'git'), `#!/bin/sh\nenv >> "${record}"\necho "--" >> "${record}"\nexec "${realGit}" "$@"\n`);
  chmodSync(path.join(bin, 'git'), 0o755);
  await scenario((h) => finishedState(h), async ({ go }) => {
    const r = await go([], { env: { PATH: `${bin}${path.delimiter}${process.env.PATH}`, LENA_TOKEN_COPY: TOKEN } });
    assert.equal(r.code, 0, r.out);
  });
  const seen = readFileSync(record, 'utf8');
  assert.ok(seen.includes('GIT_TERMINAL_PROMPT=0'), 'git ran through the recorder, told never to prompt');
  assert.ok(!seen.includes(TOKEN), 'no git saw the token, under its own name or another');
});


describe('the deadline', { concurrency: true }, () => {
  test('39: a stub that answers slowly: the run ends with 4 at its deadline, before 60 seconds', () =>
    scenario(freshState({ delayMs: 30_000 }), async ({ go }) => {
      const r = await go();
      assert.equal(r.code, 4, r.out);
      assert.match(r.out, /reached its time limit/);
      assert.ok(r.ms < 60_000, `took ${r.ms} ms`);
    }));

  test('39 at launch: a stub that answers slowly: the run ends with 4 at its deadline, before 60 seconds', () =>
    launchScenario((h) => Object.assign(launchState(h), { delayMs: 30_000 }), async ({ launch }) => {
      const r = await launch();
      assert.equal(r.code, 4, r.out);
      assert.match(r.out, /reached its time limit/);
      assert.ok(r.ms < 60_000, `took ${r.ms} ms`);
    }));

  test('a git that never ends, with a program of its own holding the output open: stopped at the deadline, said as git, before 60 seconds', async (t) => {
    if (process.platform === 'win32') { t.skip('the stand-in git is a shell script'); return; }
    const bin = path.join(scratch, 'bin-hang');
    mkdirSync(bin, { recursive: true });
    const realGit = execFileSync('sh', ['-c', 'command -v git'], { encoding: 'utf8' }).trim();
    // ls-remote starts a child that keeps stdout open, as ssh would, and one that ignores SIGTERM with
    // its output closed (review round 3: a grace period ended by the parent's exit spared it). Both
    // must be gone when the run ends.
    const pidFile = path.join(scratch, 'hang-pid');
    writeFileSync(path.join(bin, 'git'), `#!/bin/sh\nfor a in "$@"; do [ "$a" = ls-remote ] && { (trap '' TERM; exec sleep 300) >/dev/null 2>&1 & echo $! > "${pidFile}"; sleep 300 & wait; }; done\nexec "${realGit}" "$@"\n`);
    chmodSync(path.join(bin, 'git'), 0o755);
    await scenario((h) => finishedState(h), async ({ api, go }) => {
      const r = await go([], { env: { PATH: `${bin}${path.delimiter}${process.env.PATH}` } });
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /git did not finish reading the branches/);
      assert.ok(r.ms < 60_000, `took ${r.ms} ms`);
      onlyReads(api);
      const pid = Number(readFileSync(pidFile, 'utf8'));
      const gone = () => { try { process.kill(pid, 0); return false; } catch (e) { return e.code === 'ESRCH'; } };
      for (let i = 0; i < 50 && !gone(); i++) await new Promise((res) => setTimeout(res, 100)); // reaped within 5 s
      assert.ok(gone(), 'the child that ignores SIGTERM was killed with the rest');
    });
  });
});


test('40: a token that ends in 30 days is refused: the checklist says a week at most', () =>
  scenario(freshState({ token: { status: 'active', expires_on: new Date(Date.now() + 30 * 86_400_000).toISOString() } }), async ({ api, go }) => {
    const r = await go();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /The checklist says a week at most/);
    onlyReads(api);
  }));

test('the zone\'s records cannot be read: no zone-wide setting is changed, since its hosts cannot be named (R5)', () =>
  scenario(freshState({ refuse: { 'GET dns': 403 } }), async ({ api, go }) => {
    // Every line is "by hand": nothing is asked, nothing is written, and the run ends with 1.
    const r = await go();
    assert.equal(r.code, 1, r.out);
    assert.doesNotMatch(r.out, /--confirm/, 'nothing to ask');
    for (const title of ['Always Use HTTPS: On', 'Minimum TLS Version: TLS 1.2', 'Email Address Obfuscation: Off', 'Network Error Logging \\(NEL\\): Off']) {
      assert.match(r.out, new RegExp(`by hand\\s+${title}: The zone's records could not be read, so the hosts this setting changes cannot be named; the token needs the row Zone → DNS → Edit`), title);
    }
    assert.deepEqual(api.writes(), []);
  }));

test('a CNAME that already points where it should, but proxied, is not "there already": it is by hand, and nothing is written', () =>
  scenario((h) => Object.assign(finishedState(h), { dns: [{ id: 'c2', type: 'CNAME', name: `abcdef0123456789abcdef0123456789.${HOST}`, content: 'verify.bing.com', proxied: true }] }), async ({ api, go }) => {
    const r = await go(['--record', 'CNAME abcdef0123456789abcdef0123456789 verify.bing.com']);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /but through Cloudflare \(proxied\); a verification record must be DNS only/);
    onlyReads(api);
  }));

test('run from a folder inside the site, a tracked .dev.vars at the site\'s root is still refused before it is read', async () => {
  await scenario(freshState(), async ({ api, where, dns }) => {
    mkdirSync(path.join(where.site, 'src', 'pages'), { recursive: true });
    const r = await run({ site: path.join(where.site, 'src', 'pages') }, [], { api, dns, token: null });
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /git tracks \.dev\.vars/);
    assert.equal(api.log.length, 0);
  }, { devVars: `CLOUDFLARE_API_TOKEN=${TOKEN}\n`, trackDevVars: true });
});


test('a list longer than 200 pages is not read in part: the run stops', () =>
  scenario(freshState({ zones: Array.from({ length: 201 }, (_, i) => zone({ id: `c0ffee0000000000000000${String(i).padStart(10, '0')}`, name: `other-${i}.example` })), perPage: { zones: 1, projects: 10, deployments: 25 } }), async ({ api, go }) => {
    const r = await go();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /runs past 200 pages/);
    onlyReads(api);
  }));

test('R1: a yes covers only the list it answered: a setting someone changed since needs a new yes', () =>
  scenario((h) => {
    const s = finishedState(h);
    s.settings.email_obfuscation = 'on'; // the one line the question lists
    return s;
  }, async ({ api, go, state }) => {
    const q = await go();
    assert.equal(q.code, 3, q.out);
    assert.doesNotMatch(q.out.split('If you say yes')[1].split('Already as')[0], /Minimum TLS Version/, 'TLS is not in the list');
    state.settings.min_tls_version = '1.0'; // changed by hand after the question
    const r = await go(['--confirm', codeOf(q)]);
    assert.equal(r.code, 3, r.out);
    assert.match(r.out, /does not fit this question: it lists something the question you said yes to did not/);
    assert.match(r.out.split('If you say yes')[1].split('Already as')[0], /Minimum TLS Version: TLS 1\.2 \(1\.0 → 1\.2\)/, 'the new question lists it');
    onlyReads(api);
  }));


test('a code that does not fit the question changes nothing and asks again', () =>
  scenario(freshState(), async ({ api, go }) => {
    const r = await go(['--confirm', '0123456789abcdef']);
    assert.equal(r.code, 3, r.out);
    assert.match(r.out, /does not fit this question/);
    onlyReads(api);
  }));

test('a wrong command is status 2; the launch ids belong to launch; the overrides take loopback addresses only', async () => {
  const where = makeSite();
  const closed = 'http://127.0.0.1:9'; // so a run that got past its checks could reach no real API
  for (const [args, env, want] of [
    [['--skip', 'nel-rule'], {}, /belongs to the launch stage/],
    [['--skip', 'canonical'], {}, /--skip takes one of https, tls, email, nel, bot, ai \(got "canonical"\)/],
    [['--skip', 'cdn'], {}, /--skip takes one of/],
    [['--confirm', 'yes'], {}, /16-character code/],
    [Array.from({ length: 6 }, (_, i) => ['--record', `TXT r${i} v`]).flat(), {}, /at most five --record/],
    [['--project', 'lenas-site'], {}, /unknown option --project/], // the Worker's name is in wrangler.jsonc, not an option
    [[], { CLOUDFLARE_SETUP_PREVIEW: 'http://stub.example.com:8080' }, /literal loopback address/],
    [[], { CLOUDFLARE_SETUP_RUN_MS: '60000' }, /CLOUDFLARE_SETUP_RUN_MS must be a whole number of milliseconds below 55000/],
    [[], { CLOUDFLARE_SETUP_API: 'http://stub.example.com:8080' }, /literal loopback address/],
    [[], { CLOUDFLARE_SETUP_RESOLVER: '8.8.8.8:53' }, /literal loopback address/],
    [[], { CLOUDFLARE_SETUP_RESOLVER: '127.0.0.1:99999' }, /literal loopback address/],
  ]) {
    const r = await run(where, args, { env: { CLOUDFLARE_SETUP_API: closed, ...env } });
    assert.equal(r.code, 2, `${args.join(' ')} ${JSON.stringify(env)}: ${r.err}`);
    assert.match(r.err, want);
  }
  for (const [args, env, want] of [
    [['--record', 'TXT @ v'], {}, /--record belongs to the setup stage/],
    [['--skip', 'cdn'], {}, /--skip takes one of https, tls, email, nel, bot, ai, nel-rule/],
    [[], { CLOUDFLARE_SETUP_SITE: 'https://lenas-backstube.example' }, /literal loopback address/],
    [[], { CLOUDFLARE_SETUP_PREVIEW: 'http://stub.example.com:8080' }, /literal loopback address/],
  ]) {
    const r = await run(where, args, { stage: 'launch', env: { CLOUDFLARE_SETUP_API: closed, ...env } });
    assert.equal(r.code, 2, `launch ${args.join(' ')} ${JSON.stringify(env)}: ${r.err}`);
    assert.match(r.err, want);
  }
});

test('the overrides are said out loud while they are in effect', () =>
  scenario((h) => finishedState(h), async ({ go }) => {
    const r = await go();
    assert.match(r.out, /^Test mode: Cloudflare's API is replaced by http:\/\/127\.0\.0\.1:\d+\.$/m);
    assert.match(r.out, /^Test mode: the zone's nameservers are replaced by 127\.0\.0\.1:\d+\.$/m);
  }));


// ================================================================ row 2.2: Workers instead of Pages
// Expected values below are written by hand from the plan (PLAN-setup-workers.md, TS1 to TS6, TL1 to TL8).

const noPagesCall = (api) => assert.ok(!api.log.some((e) => /\/pages(\/|$)/.test(e.path)), 'a /pages/ request was sent');
const writesOf = (api) => api.log.filter((e) => e.method !== 'GET');
const RUN_DIR_OF = (where) => path.join(where.site, 'setup-run');
const keptFiles = (where) => (existsSync(RUN_DIR_OF(where)) ? readdirSync(RUN_DIR_OF(where)).filter((f) => f.startsWith('replaced-')).sort() : []);
const pendingOf = (where) => path.join(RUN_DIR_OF(where), 'pending.json');
// The record at the apex before the launch, written out: what the owner had.
const NOTE_A = { type: 'A', name: HOST, content: '192.0.2.10', proxied: false, ttl: 1, comment: null, tags: [], settings: {} };
const capturedZones = (name) => JSON.parse(readFileSync(path.join(HERE, 'fixtures', 'cloudflare-token', name), 'utf8')).result;
// Cloudflare's own list of zones for a token, with one zone made the site's and all of them one account's.
const siteZoneOf = (zones, pick) => {
  zones.forEach((z) => { z.account = { ...ACCOUNT }; });
  Object.assign(zones[pick], { id: ZONE.id, name: ZONE.name, status: 'active' });
  return zones;
};

// The deployments of a Worker that Builds made from its template, as the first build's test saw them (C4,
// newest first). The capture is read as it is; the stub fills in the ids and versions it lacks (MADE).
const BUILDS_FIRST = JSON.parse(readFileSync(path.join(HERE, 'fixtures', 'builds-deployments', 'c4-builds-first-deployments-2026-11-12-cloudflare-api-v4.json'), 'utf8'));

describe('TS: the setup stage, at a Worker', { concurrency: true }, () => {
  test('TS1: the token the move guide makes (DNS Edit in one zone of three) picks the site\'s zone', () => {
    const zones = siteZoneOf(capturedZones('cloudflare-api-zones-list-move-token-2026-11-04.json'), 2);
    assert.equal(zones.filter((z) => z.permissions.includes('#dns_records:edit')).length, 1, 'by hand: one of the three lists DNS Edit');
    return scenario((h) => Object.assign(finishedState(h), { zones }), async ({ api, go }) => {
      const r = await go();
      assert.equal(r.code, 0, r.out);
      assert.match(r.out, /Cloudflare setup for lenas-backstube\.example \(zone lenas-backstube\.example, account Lena's Account\)/);
      onlyReads(api);
      noPagesCall(api);
    });
  });

  test('TS2: the token made for the account alone (DNS Edit in every zone) is refused, and no write is sent', () => {
    const zones = siteZoneOf(capturedZones('cloudflare-api-zones-list-account-only-token-2026-11-08.json'), 2);
    assert.equal(zones.filter((z) => z.permissions.includes('#dns_records:edit')).length, 3, 'by hand: all three list DNS Edit');
    return scenario((h) => Object.assign(finishedState(h), { zones }), async ({ api, go }) => {
      const r = await go();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /This token has DNS Edit in 3 zones \(other-1\.example, other-2\.example, lenas-backstube\.example\)\. Make one limited to the site's own zone/);
      assert.equal(writesOf(api).length, 0);
    });
  });

  test('TS3: zones from two accounts are refused: the script works in one account', () => {
    const second = zone({ id: 'c0ffee00000000000000000000000003', name: 'lenas-cafe.example', account: { id: 'c0ffee00000000000000000000000004', name: 'Cafe' } });
    return scenario((h) => Object.assign(finishedState(h), { zones: [zone(), second] }), async ({ api, go }) => {
      const r = await go();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /The zones this token lists belong to 2 accounts\. The script works in one account/);
      assert.equal(writesOf(api).length, 0);
    });
  });

  test('TS4: a Worker of the name whose version link serves a commit this repository does not have is not the site\'s: refused, no write', () =>
    scenario((h) => Object.assign(finishedState(h), { workers: { [WORKER]: worker({ serves: 'd'.repeat(40) }) } }), async ({ api, go }) => {
      const r = await go();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /A Worker named lenas-backstube exists, and its version link serves the commit ddddddd, which this repository does not have: it is not this site's/);
      assert.equal(writesOf(api).length, 0);
    }));

  test('TS5: no Worker yet: the zone lines run on the yes, the run ends with 4, and no /pages/ request is ever sent', () =>
    scenario(freshState(), async ({ api, go }) => {
      const q = await go();
      assert.equal(q.code, 3, q.out);
      assert.match(q.out, /The Worker lenas-backstube is not on Cloudflare yet\. The script makes none; the first deploy does\./);
      const done = await go(['--confirm', codeOf(q)]);
      assert.equal(done.code, 4, done.out);
      assert.ok(writesOf(api).some((e) => e.method === 'PATCH' && /\/settings\/always_use_https$/.test(e.path)), 'the zone lines were written');
      noPagesCall(api);
    }, { worker: 'none' }));

  test('TS7: a Worker Builds made from its template (every deployment a dash_template) is pending: setup ends with 4 after its zone lines; launch ends with 4 and writes nothing', () =>
    scenario((h) => Object.assign(freshState(), { workers: { [WORKER]: worker({ sources: BUILDS_FIRST.slice(1).map((d) => d.source), serves: null }) } }), async ({ where, api, dns, preview, go }) => {
      assert.deepEqual(BUILDS_FIRST.slice(1).map((d) => d.source), ['dash_template', 'dash_template'], 'by hand: the capture\'s two older deployments are the template\'s');
      const q = await go();
      assert.equal(q.code, 3, q.out);
      assert.match(q.out, /The Worker lenas-backstube exists, and Cloudflare's Builds has uploaded only its template so far: no build of this site has passed\. .*If Builds shows no repository connected, this Worker is not this site's: rename it in wrangler\.jsonc\./);
      const done = await go(['--confirm', codeOf(q)]);
      assert.equal(done.code, 4, done.out);
      assert.ok(writesOf(api).length > 0, 'the zone lines were written');
      const before = writesOf(api).length;
      const launched = await run(where, [], { api, dns, preview, stage: 'launch' });
      assert.equal(launched.code, 4, launched.out);
      assert.match(launched.out, /Nothing was changed\. Status 4\./);
      assert.equal(writesOf(api).length, before, 'launch wrote nothing');
    }));

  test('TS9: a template upload followed by a wrangler deploy (the whole C4 capture, no build.txt) is not pending: refused, no write', () =>
    scenario((h) => Object.assign(freshState(), { workers: { [WORKER]: worker({ sources: BUILDS_FIRST.map((d) => d.source), serves: null }) } }), async ({ api, go }) => {
      assert.deepEqual(BUILDS_FIRST.map((d) => d.source), ['wrangler', 'dash_template', 'dash_template'], 'by hand: the capture, newest first');
      const r = await go();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /serves no build\.txt that names a commit: it is not this site's/);
      assert.equal(writesOf(api).length, 0);
    }));

  test('TS8: a Worker of the name that is neither this repository\'s nor a Builds template (a stranger\'s, uploaded by wrangler) is refused, no write', () =>
    scenario((h) => Object.assign(freshState(), { workers: { [WORKER]: worker({ sources: ['wrangler'], serves: null }) } }), async ({ api, go }) => {
      const r = await go();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /A Worker named lenas-backstube exists, and its version link serves no build\.txt that names a commit: it is not this site's\./);
      assert.equal(writesOf(api).length, 0);
    }));

  test('TS6: the deployments read refused for want of the Workers row is a failure (1), not a missing Worker (4), and it names the row', () =>
    scenario((h) => Object.assign(finishedState(h), { refuse: { 'GET wdeployments': 403 } }), async ({ api, go }) => {
      const r = await go();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /did not return the deployments of the Worker lenas-backstube: .*Account → Workers Scripts → Edit/);
      assert.equal(writesOf(api).length, 0);
    }));
});

describe('TL: the launch stage, at a Worker', { concurrency: true }, () => {
  const before = (h) => launchState(h);
  const site = { routed: false };

  test('TL0: the host already on another Worker of the account is refused: the script moves no domain between Workers, and writes nothing', () =>
    launchScenario(before, async ({ api, state, launch }) => {
      state.workerDomains.push({ id: 'c0ffee00000000000000000000000070', hostname: HOST, service: 'lenas-shop', zone_id: ZONE.id, zone_name: ZONE.name, environment: 'production' });
      const r = await launch();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /lenas-backstube\.example is attached to the Worker lenas-shop, not to lenas-backstube\. The script moves no domain from one Worker to another/);
      assert.equal(writesOf(api).length, 0);
    }, site));

  test('TL1: one A record: kept and noted before the DELETE, then the PUT, then a local route commit; nothing pushed; the check gets --site and --preview', () =>
    launchScenario(before, async ({ where, api, state, launch }) => {
      let atDelete = null;
      state.before = (e) => {
        if (e.method !== 'DELETE' || !/\/dns_records\//.test(e.path)) return;
        const name = readdirSync(RUN_DIR_OF(where)).find((f) => f.startsWith('replaced-'));
        atDelete = { name, kept: name && JSON.parse(readFileSync(path.join(RUN_DIR_OF(where), name), 'utf8')), pending: existsSync(pendingOf(where)) && JSON.parse(readFileSync(pendingOf(where), 'utf8')) };
      };
      const q = await launch();
      assert.equal(q.code, 3, q.out);
      assert.equal(writesOf(api).length, 0, 'the question writes nothing');
      const pushed = git(where.site, 'ls-remote', 'origin', 'main').split('\t')[0];
      const r = await launch(['--confirm', codeOf(q)]);
      assert.equal(r.code, 0, r.out);
      assert.ok(atDelete, 'the DELETE was sent');
      assert.match(atDelete.name, /^replaced-lenas-backstube\.example-\d{8}T\d{6}Z\.json$/);
      assert.deepEqual(atDelete.kept.record, { ...NOTE_A, id: 'c0ffee00000000000000000000000050', proxiable: true, meta: {} }, 'the kept file holds the record as read');
      assert.match(atDelete.kept.export, /\sIN\s+SOA\s/, 'and the zone\'s export');
      assert.deepEqual(atDelete.pending, { host: HOST, file: atDelete.name });
      assert.deepEqual(writesOf(api).map((e) => `${e.method} ${e.path.replace(/\/[0-9a-f]{32}/g, '/…')}`), ['DELETE /zones/…/dns_records/…', 'PUT /accounts/…/workers/domains']);
      assert.deepEqual(writesOf(api)[1].body, { hostname: HOST, service: WORKER, zone_id: ZONE.id, environment: 'production' });
      assert.match(git(where.site, 'log', '-1', '--format=%s'), /^Attach lenas-backstube\.example to the Worker lenas-backstube \(launch commit\)$/);
      assert.equal(git(where.site, 'ls-remote', 'origin', 'main').split('\t')[0], pushed, 'nothing was pushed');
      assert.ok(!existsSync(pendingOf(where)), 'pending.json is gone once the attach worked');
      assert.match(r.out, /a Workers site, with no Pages project/, 'the check was given --site');
      assert.match(r.out, /Preview links carry noindex: http:\/\/d0000099-lenas-backstube\.lenas-backstube\.workers\.dev\.test:\d+ answers 200 with noindex/, 'and --preview');
      assert.ok(r.out.includes(`setup-run/${atDelete.name}`), 'the kept file\'s path is printed');
      assert.match(r.out, /"content": "192\.0\.2\.10"/, 'the replaced record is printed');
      assert.match(r.out, /To undo the launch: remove the domain from the Worker .* add the record back \(DNS → Records → Add record, with the values above\), and take lenas-backstube\.example out of "routes" in wrangler\.jsonc in a new commit\./);
      noPagesCall(api);
    }, site));

  test('TL2: the attach refused with 100117: the record is put back as the stub served it, exit 1, the kept file stays, pending.json is gone', () =>
    launchScenario(before, async ({ where, api, state, launch }) => {
      state.attachRefused = true;
      const q = await launch();
      const r = await launch(['--confirm', codeOf(q)]);
      assert.equal(r.code, 1, r.out);
      const post = writesOf(api).find((e) => e.method === 'POST');
      assert.deepEqual(post.body, NOTE_A, 'the POST is the record the stub served, as written out here');
      assert.match(r.out, /The record is back as it was \(kept in setup-run\/replaced-/);
      assert.equal(keptFiles(where).length, 1);
      assert.ok(!existsSync(pendingOf(where)));
      assert.ok(state.dns.some((x) => x.name === HOST && x.type === 'A' && x.content === '192.0.2.10'), 'the host has its record again');
    }, site));

  test('TL3: two address records, or a CNAME to a pages.dev address, are refused before any write (the CNAME names the move guide)', async () => {
    const two = (h) => { const s = launchState(h); s.dns.push({ ...A_RECORD, id: 'c0ffee00000000000000000000000051', content: '192.0.2.11' }); return s; };
    await launchScenario(two, async ({ api, launch }) => {
      const r = await launch();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /lenas-backstube\.example has 2 address records \(A 192\.0\.2\.10, A 192\.0\.2\.11\)\. The script replaces one record and deletes no other/);
      assert.equal(writesOf(api).length, 0);
    }, site);
    const cname = (h) => launchState(h, { record: { ...A_RECORD, type: 'CNAME', content: 'lenas-backstube.pages.dev' } });
    await launchScenario(cname, async ({ api, launch }) => {
      const r = await launch();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /is a CNAME to lenas-backstube\.pages\.dev: the site is live on Cloudflare Pages\. This script does not move a live Pages site: docs\/MOVE-TO-WORKERS\.md says how\./);
      assert.equal(writesOf(api).length, 0);
    }, site);
  });

  test('TL4: a dirty tree, a HEAD ahead of GitHub\'s main, another run\'s lock: each refused before any write', async () => {
    const refused = async (prepare, want) => launchScenario(before, async ({ where, api, launch }) => {
      prepare(where);
      const r = await launch();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, want);
      assert.equal(writesOf(api).length, 0);
      assert.equal(keptFiles(where).length, 0, 'no file was kept');
    }, site);
    await refused((w) => writeFileSync(path.join(w.site, 'notes.txt'), 'x\n'), /The working tree has changes \(\?\? notes\.txt\)/);
    await refused((w) => git(w.site, 'commit', '-q', '--allow-empty', '-m', 'one ahead'), /HEAD \([0-9a-f]{7}\) is not the head of main on GitHub \([0-9a-f]{7}\)/);
    await refused((w) => { mkdirSync(RUN_DIR_OF(w), { recursive: true }); writeFileSync(path.join(RUN_DIR_OF(w), 'lock'), `${process.pid}\nabc\n`); }, /Another run \(process \d+\) holds .*setup-run\/lock/);
  });

  test('TL1b: a site whose Workers config has another name (workers.jsonc): the check is told which file, and the route commit is made in it', () =>
    launchScenario(before, async ({ where, launch }) => {
      const q = await launch();
      assert.equal(q.code, 3, q.out);
      const r = await launch(['--confirm', codeOf(q)]);
      assert.equal(r.code, 0, r.out);
      assert.match(r.out, /as a custom-domain route in workers\.jsonc/);
      assert.match(readFileSync(path.join(where.site, 'workers.jsonc'), 'utf8'), /lenas-backstube\.example/);
    }, { routed: false, files: { 'wrangler.jsonc': null, 'workers.jsonc': WRANGLER } }));

  test('TL5: a PUT that is never answered after the DELETE: the next run prints the noted record, re-checks step 1, and attaches on the same code; with too little time, nothing is written', async () => {
    await launchScenario(before, async ({ where, api, state, launch }) => {
      const q = await launch();
      const code = codeOf(q);
      state.drop['PUT wdomains'] = 'silent';
      const hung = await launch(['--confirm', code]);
      assert.equal(hung.code, 4, hung.out);
      assert.match(hung.out, /The attach got no answer, so lenas-backstube\.example may have no record now\. The record is kept in setup-run\/replaced-/);
      assert.ok(existsSync(pendingOf(where)) && keptFiles(where).length === 1, 'the note stays');
      assert.equal(writesOf(api).filter((e) => e.method === 'DELETE').length, 1);
      delete state.drop['PUT wdomains'];
      const asked = await launch();
      assert.equal(asked.code, 3, asked.out);
      assert.match(asked.out, /The record of lenas-backstube\.example is already deleted and kept in setup-run\//);
      assert.doesNotMatch(asked.out, /Delete the record of/);
      const again = await launch(['--confirm', code]);
      assert.equal(again.code, 0, again.out);
      assert.match(again.out, /A launch stopped after it deleted the record of lenas-backstube\.example, and the host has no record\. The record is kept in setup-run\/replaced-/);
      assert.match(again.out, /"content": "192\.0\.2\.10"/);
      assert.equal(keptFiles(where).length, 1, 'no second file: the run attached from the note');
      assert.ok(!existsSync(pendingOf(where)));
      assert.equal(writesOf(api).filter((e) => e.method === 'DELETE').length, 1, 'no second DELETE');
    }, site);

    // The PUT was applied and its answer lost: the next run finds the host attached, clears the note, and sends no second PUT.
    await launchScenario(before, async ({ where, api, state, launch }) => {
      const q = await launch();
      state.drop['PUT wdomains'] = 'lost';
      const hung = await launch(['--confirm', codeOf(q)]);
      assert.equal(hung.code, 4, hung.out);
      delete state.drop['PUT wdomains'];
      const again = await launch(['--confirm', codeOf(q)]);
      assert.equal(again.code, 0, again.out);
      assert.ok(!existsSync(pendingOf(where)), 'the note is cleared');
      assert.equal(writesOf(api).filter((e) => e.method === 'PUT').length, 1, 'no second PUT');
      assert.equal(writesOf(api).filter((e) => e.method === 'DELETE').length, 1, 'no second DELETE');
    }, site);

    // Step 1's conditions hold on a recovery run: a draft added to production in between refuses it.
    await launchScenario(before, async ({ where, api, state, launch }) => {
      const q = await launch();
      state.drop['PUT wdomains'] = 'silent';
      await launch(['--confirm', codeOf(q)]);
      delete state.drop['PUT wdomains'];
      const spec = readFileSync(path.join(where.site, 'tests', 'placeholders.spec.ts'), 'utf8').replace('new Set<string>([])', "new Set<string>(['/about'])");
      writeFileSync(path.join(where.site, 'tests', 'placeholders.spec.ts'), spec);
      git(where.site, 'commit', '-q', '-am', 'a page still to fill');
      git(where.site, 'push', '-q', 'origin', 'main', 'main:production');
      const writes = writesOf(api).length;
      const r = await launch(['--confirm', codeOf(q)]);
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /UNFILLED_UNTIL_LAUNCH in tests\/placeholders\.spec\.ts still lists \/about/);
      assert.equal(writesOf(api).length, writes, 'refused before any write');
      assert.ok(existsSync(pendingOf(where)), 'the note is untouched');
    }, site);

    // The PUT refused on the next run: the record is put back.
    await launchScenario(before, async ({ where, api, state, launch }) => {
      const q = await launch();
      state.drop['PUT wdomains'] = 'silent';
      await launch(['--confirm', codeOf(q)]);
      delete state.drop['PUT wdomains'];
      state.attachRefused = true;
      const r = await launch(['--confirm', codeOf(q)]);
      assert.equal(r.code, 1, r.out);
      assert.deepEqual(writesOf(api).filter((e) => e.method === 'POST').map((e) => e.body), [NOTE_A]);
      assert.ok(!existsSync(pendingOf(where)) && keptFiles(where).length === 1);
    }, site);

    // Too little time: no file, no DELETE, status 4.
    await launchScenario(before, async ({ where, api, launch }) => {
      const q = await launch([], { env: { CLOUDFLARE_SETUP_RUN_MS: '40000' } });
      assert.equal(q.code, 3, q.out);
      const r = await launch(['--confirm', codeOf(q)], { env: { CLOUDFLARE_SETUP_RUN_MS: '40000' } });
      assert.equal(r.code, 4, r.out);
      assert.match(r.out, /needs 45\. Nothing was written\. Run the same command again\. Status 4\./);
      assert.equal(writesOf(api).length, 0);
      assert.equal(keptFiles(where).length, 0);
      assert.ok(!existsSync(pendingOf(where)));
    }, site);
  });

  test('TL6: the gate refuses what the launch must never send, allows what it sends, and makeApi sends nothing the gate refused', async () => {
    const g = { hosts: new Set([HOST]), worker: WORKER, accountId: ACCOUNT.id, zoneId: ZONE.id, recordId: 'c0ffee00000000000000000000000050', note: NOTE_A };
    const Z = `/zones/${ZONE.id}`;
    const W = `/accounts/${ACCOUNT.id}/workers`;
    const refuse = (method, url, body, what) => assert.throws(() => gate(method, url, body, g), (e) => e instanceof Stop && /^gate: refused/.test(e.lines?.[0] ?? e.message), what);
    const allow = (method, url, body, what) => assert.doesNotThrow(() => gate(method, url, body, g), what);
    // What the launch sends.
    allow('DELETE', `${Z}/dns_records/${g.recordId}`);
    allow('POST', `${Z}/dns_records`, { ...NOTE_A });
    allow('PUT', `${W}/domains`, { hostname: HOST, service: WORKER, zone_id: ZONE.id, environment: 'production' });
    allow('GET', `${W}/scripts/${WORKER}/deployments`);
    allow('GET', `${Z}/dns_records/export`);
    // What it must not.
    refuse('DELETE', `${Z}/dns_records/c0ffee00000000000000000000000099`, undefined, 'another record id');
    refuse('POST', `${Z}/dns_records`, { ...NOTE_A, content: '192.0.2.99' }, 'a POST that differs from the note');
    refuse('PUT', `${W}/domains`, { hostname: `www.${HOST}`, service: WORKER, zone_id: ZONE.id, environment: 'production' }, 'the attach naming another host');
    refuse('POST', `${Z}/dns_records`, { ...NOTE_A, name: `www.${HOST}` }, 'a POST naming another host');
    refuse('POST', `${W}/scripts/${WORKER}`, { x: 1 }, 'a POST under workers/scripts');
    refuse('GET', `${W}/scripts/other-worker/deployments`, undefined, 'another script\'s deployments');
    refuse('DELETE', `${W}/domains/c0ffee00000000000000000000000060`, undefined, 'a domain DELETE');
    // The zone is part of the path: another zone's settings and rules are refused, and so is a setting no line writes.
    const other = '/zones/c0ffee00000000000000000000000077';
    allow('PATCH', `${Z}/settings/always_use_https`, { value: 'on' });
    allow('POST', `${Z}/rulesets/c0ffee00000000000000000000000078/rules`, { x: 1 });
    refuse('PATCH', `${other}/settings/always_use_https`, { value: 'on' }, 'another zone\'s setting');
    refuse('POST', `${other}/rulesets/c0ffee00000000000000000000000078/rules`, { x: 1 }, 'another zone\'s ruleset');
    refuse('PATCH', `${Z}/settings/ssl`, { value: 'off' }, 'a setting no line writes');
    // Setup's --record may write a CNAME at the host (as before); the launch may not, nor may setup write an address.
    const none = { ...g, note: null };
    assert.doesNotThrow(() => gate('POST', `${Z}/dns_records`, { type: 'CNAME', name: HOST, content: 'verify.bing.com' }, { ...none, stage: 'setup' }), 'setup: a CNAME at the host');
    assert.throws(() => gate('POST', `${Z}/dns_records`, { type: 'CNAME', name: HOST, content: 'verify.bing.com' }, { ...none, stage: 'launch' }), /gate: refused/, 'launch: a CNAME at the host');
    assert.throws(() => gate('POST', `${Z}/dns_records`, { type: 'A', name: HOST, content: '192.0.2.1' }, { ...none, stage: 'setup' }), /gate: refused/, 'setup: an A at the host');
    // makeApi runs the gate before it opens a socket: a stub that records its requests sees none.
    await scenario(freshState(), async ({ api }) => {
      const call = makeApi(api.origin, TOKEN, { left: () => 10_000 }, g);
      await assert.rejects(() => call('DELETE', `${Z}/dns_records/c0ffee00000000000000000000000099`), (e) => e instanceof Stop && /^gate: refused/.test(e.lines?.[0] ?? e.message));
      assert.equal(api.log.length, 0, 'the stub saw no request');
      const sent = await call('GET', '/user/tokens/verify');
      assert.equal(sent.status, 200);
      assert.equal(api.log.length, 1, 'and an allowed call does arrive');
    });
  });

  test('TL7: an attach refused and the record put back leaves the kept file; when the owner changes the record, the next run notes the new one in a new file and asks a new yes', () =>
    launchScenario(before, async ({ where, state, launch }) => {
      state.attachRefused = true;
      const q = await launch();
      const refused = await launch(['--confirm', codeOf(q)]);
      assert.equal(refused.code, 1, refused.out);
      assert.ok(!existsSync(pendingOf(where)));
      const first = keptFiles(where);
      assert.equal(first.length, 1);
      // The owner changes the record; the stub no longer refuses the attach.
      state.attachRefused = false;
      state.dns.find((x) => x.name === HOST && x.type === 'A').content = '192.0.2.77';
      await new Promise((r) => setTimeout(r, 1100)); // a new second, so a new file name
      const q2 = await launch();
      assert.equal(q2.code, 3, q2.out);
      assert.notEqual(codeOf(q2), codeOf(q), 'the record is another, so the code is another');
      assert.match(q2.out, /"content": "192\.0\.2\.77"/);
      const r = await launch(['--confirm', codeOf(q2)]);
      assert.equal(r.code, 0, r.out);
      const all = keptFiles(where);
      assert.equal(all.length, 2, 'a new file, the first one kept');
      assert.equal(all[0], first[0]);
      assert.equal(JSON.parse(readFileSync(path.join(RUN_DIR_OF(where), all[0]), 'utf8')).record.content, '192.0.2.10');
      assert.equal(JSON.parse(readFileSync(path.join(RUN_DIR_OF(where), all[1]), 'utf8')).record.content, '192.0.2.77');
    }, site));

  test('TL8: the put-back refused after a refused attach: exit 1, the whole record and the way by hand are printed, and the next run prints them again', () =>
    launchScenario(before, async ({ where, state, launch }) => {
      state.attachRefused = true;
      state.refuse['POST dns'] = 500;
      const q = await launch();
      const r = await launch(['--confirm', codeOf(q)]);
      assert.equal(r.code, 1, r.out);
      for (const want of ['"type": "A"', `"name": "${HOST}"`, '"content": "192.0.2.10"', '"proxied": false', '"ttl": 1', '"comment": null', '"tags": []', '"settings": {}', 'DNS → Records → Add record']) {
        assert.ok(r.out.includes(want), `${want}\n${r.out}`);
      }
      assert.ok(existsSync(pendingOf(where)), 'pending.json stays until the host has a record');
      assert.equal(keptFiles(where).length, 1);
      state.refuse = {};
      const again = await launch();
      assert.match(again.out, /A launch stopped after it deleted the record of lenas-backstube\.example, and the host has no record\./);
      assert.match(again.out, /"content": "192\.0\.2\.10"/);
      assert.match(again.out, /DNS → Records → Add record/);
    }, site));
});
