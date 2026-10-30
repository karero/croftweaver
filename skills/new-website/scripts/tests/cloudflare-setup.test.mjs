// Tests for cloudflare-setup.mjs. Standard library only; run with
//   node --test skills/new-website/scripts/tests/cloudflare-setup.test.mjs
//
// The scenarios are the plan's (docs/reviews/SKILL-PLAN-cloudflare-setup.md, "Scenarios"), by their
// numbers. Each runs the script as a program, the way an assistant does, in a fixture repository
// whose origin is a GitHub address that the repository's own git config sends to a local folder
// (url.<folder>.insteadOf), against a stub of Cloudflare's API and a stub nameserver on 127.0.0.1
// (cloudflare-stub.mjs). The stub's answers are the trials' captures, cleaned and committed in
// fixtures/cloudflare-api/; the first tests replay the captured calls against the stub and compare.
import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { execFile, execFileSync, spawn } from 'node:child_process';
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { BOT_LINES, LAUNCH_FAIL, aiNotes, LAUNCH_SKIP_IDS, SETTINGS, SKIP_IDS, checkArgs, codeFits, defaultName, failed, fixedText, githubRepo, goodProductionBuild, launchVerdict, nameserverIps, notAsWanted, otherDifferences, running, looksSwapped, parseRecord, pushProof, setupCode, UsageError } from '../cloudflare-setup.mjs';
import { ITEMS as CHECK_ITEMS } from '../cloudflare-check.mjs';
import { ACCOUNT, FIXTURES, OWNER, REPO, TOKEN, ZONE, allFixtures, attachedDomain, deployment, fixture, freshState, handle, project, servedBy, startApi, startDns, startSites, zone } from './cloudflare-stub.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = path.join(HERE, '..', 'cloudflare-setup.mjs');
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
// A site made with the kit: src/config.ts at the head of main, pushed to its origin; two-stage by
// default, with production at the same commit.
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
  const all = { 'tests/placeholders.spec.ts': EMPTY_LIST(STARTER_SPEC), '.github/workflows/ci.yml': STARTER_CI, 'src/pages/index.astro': '<p>Brot</p>\n', 'public/robots.txt': 'User-agent: *\n', ...files };
  for (const [f, text] of Object.entries(all)) {
    if (text === null) continue;
    mkdirSync(path.dirname(path.join(site, f)), { recursive: true });
    writeFileSync(path.join(site, f), text);
  }
  git(site, 'add', ...['src', 'public', 'tests', '.github', '.gitignore'].filter((f) => existsSync(path.join(site, f))));
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

function run(where, args, { api, dns, sites, env = {}, token = TOKEN, stage = 'setup' } = {}) {
  const started = Date.now();
  return new Promise((resolve) => {
    const e = { ...cleanEnv(), ...(token ? { CLOUDFLARE_API_TOKEN: token } : {}), ...(api ? { CLOUDFLARE_SETUP_API: api.origin } : {}), ...(dns ? { CLOUDFLARE_SETUP_RESOLVER: dns.address } : {}),
      ...(sites ? { CLOUDFLARE_SETUP_SITE: sites.site, CLOUDFLARE_SETUP_PAGES: sites.pages } : {}), ...env };
    execFile(process.execPath, [SCRIPT, stage, ...args], { cwd: where.site, env: e, timeout: 75_000 }, (err, stdout, stderr) => {
      // R10: the token is never printed.
      assert.ok(!stdout.includes(TOKEN) && !stderr.includes(TOKEN), 'the token was printed');
      resolve({ code: err ? (err.code ?? `killed: ${err.signal ?? 'timeout'}`) : 0, out: stdout, err: stderr, ms: Date.now() - started });
    });
  });
}
const codeOf = (r) => /--confirm ([0-9a-f]{16})/.exec(r.out)?.[1];

// A scenario: a site, the stub API with `state`, and the stub nameserver serving what the stub holds.
// `state` may be a function of the site's branch heads, for a state that holds deployments of them.
async function scenario(stateOrFn, fn, siteOpts = {}) {
  const where = makeSite(siteOpts);
  const state = typeof stateOrFn === 'function' ? stateOrFn(where.heads) : stateOrFn;
  state.heads = where.heads;
  const api = await startApi(state);
  let silent = false;
  const dns = await startDns(servedBy(state, { silent: () => silent }));
  try {
    return await fn({ where, api, dns, state, setSilent: (v) => { silent = v; }, go: (args = [], o = {}) => run(where, args, { api, dns, ...o }) });
  } finally {
    await api.close();
    await dns.close();
  }
}

// A finished setup: the project as setup leaves it, a good production build of the head, a push
// build, and the zone's settings and Bot Management as the checklist wants them.
function finishedState(heads, over = {}) {
  const s = freshState(over);
  s.heads = heads;
  s.projects = [project()];
  s.deployments = { [REPO]: [
    deployment('push', { commit: heads.main, branch: 'lenas-pr' }),
    deployment('built', { commit: heads.production }),
  ] };
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

test('the deployments the stub serves are the captured ones, and the script reads them as the plan says', () => {
  // A Cloudflare build: clone_repo and build succeeded. An upload: both idle (T1-021). A skipped push: not proof (T2-026).
  const built = fixture('T1-040').response.result[1];
  const upload = fixture('T1-021').response.result.find((d) => d.deployment_trigger.type === 'ad_hoc' && d.environment === 'production' && d.stages.find((s) => s.name === 'build').status === 'idle');
  const skipped = fixture('T2-026').response.result[0];
  const push = fixture('T1-040').response.result[0];
  const sha = built.deployment_trigger.metadata.commit_hash;
  assert.equal(goodProductionBuild(built, sha, 'production'), true, 'a Cloudflare build of the head');
  assert.equal(goodProductionBuild(upload, upload.deployment_trigger.metadata.commit_hash, 'production'), false, 'an upload is no Cloudflare build');
  assert.equal(goodProductionBuild(built, sha, 'main'), false, 'built while another branch was the production branch (capture T1-055)');
  assert.equal(fixture('T1-055').response.result.production_branch, 'main', 'a deployment records the production branch of its time');
  assert.equal(pushProof(push), true);
  assert.equal(pushProof(skipped), false, 'a skipped push was never built');
  assert.equal(pushProof(built), false, 'a build the deployment call started is no proof');
  // Between two stages (build succeeded, deploy not begun) a deployment is still under way, not failed.
  const between = { ...built, latest_stage: { name: 'build', status: 'success' } };
  assert.equal(running(between), true);
  assert.equal(failed(between), false);
  // A deployment records its variables, a secret with its value empty, and its build settings (T1-062).
  assert.deepEqual(fixture('T1-062').response.result.env_vars.SPIKE_SECRET, { type: 'secret_text', value: '' });
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
  /^100000\d$/, /^\d{4}-\d{2}-\d{2}(T[\d:.]+Z)?$/, /^Made-up commit message \d+$/, /^T[1-3]-\d{3}$/];
function notMadeUp(fixtures) {
  const strings = new Set(ALLOWED.strings);
  const tokens = new Set(ALLOWED.tokens);
  const keys = new Set(ALLOWED.keys);
  const numbers = new Set(ALLOWED.numbers);
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
    assert.match(file, /^T[1-3]-\d{3}-[a-z0-9_-]+\.json$/, file);
    assert.doesNotMatch(file, /[0-9a-f]{16}/i, `${file}: a run of hexadecimal digits in a file name`);
  }
  assert.deepEqual(notMadeUp(fixtures), []);
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
  assert.ok(/Zone → DNS → Edit/.test(six), 'section 6\'s table has the DNS row the setup writes records with');
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

test('the owner and repository come from the remote in any of its forms; the project name follows the repository', () => {
  for (const u of [`https://github.com/${OWNER}/${REPO}.git`, `https://lena:secret@github.com/${OWNER}/${REPO}`, `git@github.com:${OWNER}/${REPO}.git`, `ssh://git@github.com/${OWNER}/${REPO}.git`]) {
    assert.deepEqual(githubRepo(u), { owner: OWNER, repo: REPO }, u);
  }
  assert.equal(githubRepo('https://gitlab.com/lena/site.git'), null);
  assert.equal(defaultName('Lenas_Backstube.Site'), 'lenas-backstube-site');
  assert.equal(defaultName(`--${'x'.repeat(70)}`), 'x'.repeat(56), 'cut to 58, then dashes trimmed');
  assert.equal(defaultName('___'), '');
});

test('the code names the end state: the same inputs give the same code, a --skip or a host gives another', () => {
  const base = { account: ACCOUNT.id, project: REPO, repository: `${OWNER}/${REPO}`, productionBranch: 'production', zone: ZONE.id, skip: [], hosts: [HOST], records: [] };
  assert.match(setupCode(base), /^[0-9a-f]{16}$/);
  assert.equal(setupCode(base), setupCode({ ...base, repository: `${OWNER.toUpperCase()}/${REPO}` }), 'GitHub names compare without case');
  assert.notEqual(setupCode(base), setupCode({ ...base, skip: ['tls'] }));
  assert.notEqual(setupCode(base), setupCode({ ...base, hosts: [HOST, `shop.${HOST}`] }));
  assert.equal(setupCode({ ...base, skip: SKIP_IDS, hosts: [] }), setupCode({ ...base, skip: SKIP_IDS, hosts: [HOST] }), 'with every setting left out, no host is named');
  // The list: the code of a question fits what is left of it, never a list with something more.
  const listed = ['setting:email', 'setting:tls', 'build:aaaa'];
  const code = setupCode(base, listed);
  assert.notEqual(code, setupCode(base, ['setting:email']));
  const possible = ['setting:email', 'setting:tls', 'setting:https', 'build:aaaa'];
  assert.equal(codeFits(code, base, ['setting:email'], possible), true, 'tls and the build done since: still fits');
  assert.equal(codeFits(code, base, listed, possible), true);
  assert.equal(codeFits(code, base, ['setting:email', 'setting:https'], possible), false, 'a line the question did not list');
  assert.equal(codeFits(code, base, ['setting:email'], ['setting:email', 'setting:tls', 'build:bbbb']), false, 'a build of another commit');
});

// ================================================================ setup

test('1: a new project: the first run writes nothing and asks; the run with the code creates, builds once, writes the settings, and waits', () =>
  scenario(freshState(), async ({ api, go, state }) => {
    const first = await go();
    assert.equal(first.code, 3, first.out);
    onlyReads(api);
    assert.match(first.out, /Create the Pages project lenas-backstube, connected to lena-example\/lenas-backstube: production branch production, build command npm run build, output folder dist, Fail open on/);
    assert.match(first.out, /Start one build of production/);
    const code = codeOf(first);
    assert.ok(code, 'the question ends with a code');

    const second = await go(['--confirm', code]);
    assert.equal(second.code, 4, second.out);
    const writes = api.writes();
    const create = writes.find((e) => e.method === 'POST' && e.path.endsWith('/pages/projects'));
    assert.deepEqual(create.body, {
      name: REPO, production_branch: 'production', build_config: { build_command: 'npm run build', destination_dir: 'dist', root_dir: '' },
      source: { type: 'github', config: { owner: OWNER, repo_name: REPO, production_branch: 'production', pr_comments_enabled: true, deployments_enabled: true, production_deployments_enabled: true, preview_deployment_setting: 'all' } },
      deployment_configs: { production: { fail_open: true }, preview: { fail_open: true } },
    });
    assert.equal(writes.filter((e) => e.path.endsWith('/deployments')).length, 1, 'one build');
    // The same empty form the trial sent (T1-030), with the script's own boundary.
    const sent = writes.find((e) => e.path.endsWith('/deployments'));
    const trial = fixture('T1-030').request.body.emptyForm;
    const boundary = /boundary=(\S+)/.exec(sent.contentType)[1];
    assert.equal(sent.contentType, trial.contentType.replace('----spike', boundary));
    assert.equal(sent.body, trial.bytes.replace('----spike', boundary));
    assert.deepEqual(state.settings, { always_use_https: 'on', min_tls_version: '1.2', email_obfuscation: 'off', nel: { enabled: false } });
    assert.equal(state.bot.bot_preference_sync_enabled, false);
    assert.ok(!api.log.some((e) => /\/domains/.test(e.path)), 'nothing goes near the domain');
    assert.ok(api.log.every((e) => e.token), 'every call carried the token, and only these went out');
    assert.match(second.out, /waiting\s+Started a build/);
    assert.match(second.out, /pushes one commit to a pull request/);
  }));

test('2: the build has finished and a pull request was built: the same code changes nothing and ends with 0', () =>
  scenario(freshState(), async ({ api, go, state }) => {
    const code = codeOf(await go());
    assert.equal((await go(['--confirm', code])).code, 4);
    api.finish(REPO, 'success');
    state.deployments[REPO].unshift(deployment('push', { commit: state.heads.main, branch: 'lenas-pr' }));
    const before = api.writes().length;
    const r = await go(['--confirm', code]);
    assert.equal(r.code, 0, r.out);
    assert.equal(api.writes().length, before, 'no second create, no second build');
    assert.match(r.out, /Connected to GitHub: Cloudflare started a build from a push: a preview of lenas-pr/);
    assert.match(r.out, /read back through the API only/);
  }));

test('3: the build is still queued: no deployment call, and it waits', () =>
  scenario(freshState(), async ({ api, go }) => {
    const code = codeOf(await go());
    await go(['--confirm', code]);
    const builds = () => api.writes().filter((e) => e.path.endsWith('/deployments')).length;
    assert.equal(builds(), 1);
    const r = await go(['--confirm', code]);
    assert.equal(r.code, 4, r.out);
    assert.equal(builds(), 1, 'none while one is queued');
    assert.match(r.out, /A build is under way/);
  }));

test('4: a connected project publishing main, with no domain: the list says so, and the first write is that PATCH', () =>
  scenario(freshState({ projects: [project({ productionBranch: 'main' })], deployments: { [REPO]: [] } }), async ({ api, go }) => {
    const r = await go();
    assert.equal(r.code, 3);
    assert.match(r.out, /your live address would publish main, the preview; I will set the production branch to production/);
    await go(['--confirm', codeOf(r)]);
    const first = api.writes()[0];
    assert.deepEqual([first.method, first.path, first.body], ['PATCH', `/accounts/${ACCOUNT.id}/pages/projects/${REPO}`, { production_branch: 'production' }]);
  }));

test('5: the same project serving her domain, or another one: it stops and writes nothing', async () => {
  for (const domains of [[HOST], ['lenas-cafe.example']]) {
    await scenario(freshState({ projects: [project({ productionBranch: 'main', domains })] }), async ({ api, go }) => {
      const r = await go();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /does not repair a live site/);
      assert.match(r.out, /section 1 says how to change the production branch/);
      onlyReads(api);
    });
  }
});

test('6: PROD_BRANCH is production and GitHub has no production branch: it stops, and says what each model needs', () =>
  scenario(freshState(), async ({ api, go }) => {
    const r = await go();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /The two signs of the publish model disagree/);
    assert.match(r.out, /Two-stage .* creates it from the reviewed main/);
    assert.match(r.out, /Single-stage .* PROD_BRANCH is "main"/);
    assert.equal(api.log.length, 0);
  }, { production: false }));

test('7: a project of that name with no source is a Direct Upload project: it stops and points the way round', () =>
  scenario(freshState({ projects: [project({ source: null })] }), async ({ api, go }) => {
    const r = await go();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /Direct Upload project\. Cloudflare cannot connect one to GitHub/);
    assert.match(r.out, /website-team-setup §6, item 9/);
    onlyReads(api);
  }));

test('8: adopted by its repository under another name; two projects; --project connected elsewhere; --project new', async () => {
  await scenario(freshState({ projects: [project({ name: 'lenas-shop-site' })], deployments: { 'lenas-shop-site': [] } }), async ({ api, go }) => {
    const r = await go();
    assert.match(r.out, /Project lenas-shop-site \(exists\)/);
    assert.doesNotMatch(r.out, /Create the Pages project/);
    await go(['--confirm', codeOf(r)]);
    assert.ok(!api.writes().some((e) => e.method === 'POST' && e.path.endsWith('/pages/projects')), 'nothing created');
  });
  await scenario(freshState({ projects: [project({ name: 'one' }), project({ name: 'two' })] }), async ({ api, go }) => {
    const r = await go();
    assert.equal(r.code, 1);
    assert.match(r.out, /2 projects are connected to lena-example\/lenas-backstube: one, two/);
    onlyReads(api);
  });
  await scenario(freshState({ projects: [project({ name: 'cafe', source: { owner: OWNER, repo: 'lenas-cafe' } })] }), async ({ api, go }) => {
    const r = await go(['--project', 'cafe']);
    assert.equal(r.code, 1);
    assert.match(r.out, /connected to lena-example\/lenas-cafe, not to lena-example\/lenas-backstube/);
    onlyReads(api);
  });
  await scenario(freshState(), async ({ go }) => {
    const r = await go(['--project', 'lenas-new']);
    assert.equal(r.code, 3);
    assert.match(r.out, /Create the Pages project lenas-new/);
  });
});

test('9: an adopted project with a variable and a secret and Fail open off: one PATCH with Fail open alone; both names stay', () => {
  const p = project({ failOpen: false, envVars: { PLAIN_ONE: { type: 'plain_text', value: 'one' }, A_SECRET: { type: 'secret_text', value: '' } } });
  const s = freshState({ projects: [p], deployments: { [REPO]: [] } });
  return scenario(s, async ({ api, go, state }) => {
    state.deployments[REPO] = [deployment('built', { commit: state.heads.production })];
    const r = await go();
    assert.match(r.out, /Fail open: off for production, off for previews → on for both/);
    const done = await go(['--confirm', codeOf(r)]);
    const patches = api.writes().filter((e) => e.method === 'PATCH' && /pages\/projects/.test(e.path));
    assert.deepEqual(patches.map((e) => e.body), [{ deployment_configs: { production: { fail_open: true }, preview: { fail_open: true } } }]);
    assert.match(done.out, /before: A_SECRET \(production\), PLAIN_ONE \(production\); after: A_SECRET \(production\), PLAIN_ONE \(production\)/);
    assert.match(done.out, /Whether that reaches the build that is live, or only later ones, is not known/);
  });
});

test('9b: a PATCH after which a variable is missing ends the run with 1 and names it', () => {
  // MADE: no trial saw Cloudflare lose a variable; the stub drops it from the PATCH's answer.
  const p = project({ failOpen: false, envVars: { A_SECRET: { type: 'secret_text', value: '' } } });
  return scenario(freshState({ projects: [p], loseOnPatch: ['A_SECRET'] }), async ({ api, go, state }) => {
    state.deployments[REPO] = [deployment('built', { commit: state.heads.production })];
    const r = await go(['--confirm', codeOf(await go())]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /no longer lists A_SECRET \(production\)/);
    assert.ok(!api.writes().some((e) => e.path.includes('/settings/')), 'the run ended there');
  });
});

test('a PATCH answer without the whole project stops the run before anything else is written', () =>
  scenario(freshState({ projects: [project({ failOpen: false })], thinPatchAnswer: 'config' }), async ({ api, go, state }) => {
    state.deployments[REPO] = [deployment('built', { commit: state.heads.production })];
    const r = await go(['--confirm', codeOf(await go())]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /does not read as asked: connected to undefined\/undefined; no preview setting/);
    assert.ok(!api.writes().some((e) => e.path.includes('/settings/')), 'nothing after the PATCH');
  }));

test('an adopted project read without its preview setting stops the run before anything is asked or written', async () => {
  for (const value of [undefined, null, ['all']]) {
    await scenario(freshState({ projects: [project({ failOpen: false })], projectRead: (p) => { if (value === undefined) delete p.source.config.preview_deployment_setting; else p.source.config.preview_deployment_setting = value; return p; } }), async ({ api, go }) => {
      const r = await go();
      assert.equal(r.code, 1, `${JSON.stringify(value)}: ${r.out}`);
      assert.match(r.out, /without its preview setting, so a change to it could not be checked afterwards/);
      onlyReads(api);
    });
  }
});

test('a PATCH answer whose preview setting differs from the one read before stops the run', () =>
  scenario(freshState({ projects: [project({ failOpen: false })], previewInPatchAnswer: 'none' }), async ({ api, go, state }) => {
    state.deployments[REPO] = [deployment('built', { commit: state.heads.production })];
    const r = await go(['--confirm', codeOf(await go())]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /does not read as asked: preview setting none, not all/);
    assert.ok(!api.writes().some((e) => e.path.includes('/settings/')), 'nothing after the PATCH');
  }));

test('a create answer that does not read as asked stops the run: no build, no setting', () =>
  scenario(freshState({ thinCreateAnswer: true }), async ({ api, go }) => {
    const r = await go(['--confirm', codeOf(await go())]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /it does not read as asked: build_command \(none\), not npm run build; destination_dir \(none\), not dist/);
    assert.deepEqual(api.writes().map((e) => e.method), ['POST'], 'the create, and nothing after it');
  }));

test('the check of a returned project names each field that does not hold the end state', () => {
  const want = { gh: { owner: OWNER, repo: REPO }, prodBranch: 'production', preview: 'all' };
  const good = fixture('T1-027').response.result; // the captured create answer, the trial's project
  const asLena = (p) => { const c = JSON.parse(JSON.stringify(p)); c.source.config.owner = OWNER; c.source.config.repo_name = REPO; c.subdomain = `${REPO}.pages.dev`; return c; };
  assert.deepEqual(notAsWanted(asLena(good), want), []);
  const cases = [
    [(p) => { delete p.subdomain; }, /no pages.dev address/],
    [(p) => { p.source.config.repo_name = 'lenas-cafe'; }, /connected to lena-example\/lenas-cafe/],
    [(p) => { p.source = null; }, /not connected to GitHub/],
    [(p) => { p.source.config = []; }, /not connected to GitHub/],
    [(p) => { delete p.source.config.preview_deployment_setting; }, /no preview setting/],
    [(p) => { p.production_branch = 'main'; }, /production branch main, not production/],
    [(p) => { p.build_config = {}; }, /build_command \(none\), not npm run build/],
    [(p) => { p.deployment_configs.preview = {}; }, /Fail open off for preview/],
    [(p) => { p.deployment_configs.production = []; }, /no production settings/],
    [(p) => { p.deployment_configs.production.env_vars = []; }, /the production variables cannot be read/],
    // Review re-gate 3: a value, not only a type. The preview setting asked for, and the names as strings.
    [(p) => { p.source.config.preview_deployment_setting = 'none'; }, /preview setting none, not all/],
    [(p) => { p.source.config.preview_deployment_setting = ''; }, /preview setting , not all/],
    [(p) => { p.source.config.owner = [OWNER]; }, /connected to \["lena-example"\]\/lenas-backstube/],
    [(p) => { delete p.source.config.repo_name; }, /connected to lena-example\/undefined/],
  ];
  for (const [spoil, want2] of cases) {
    const p = asLena(good);
    spoil(p);
    assert.match(notAsWanted(p, want).join('; '), want2);
  }
  assert.deepEqual(notAsWanted(null, want), ['no project in the answer']);
  // Re-gate 4: with no wanted value to compare with, nothing passes.
  for (const preview of [undefined, null, ['all']]) assert.match(notAsWanted(asLena(good), { ...want, preview }).join('; '), /the preview setting wanted is not known/);
  // A repository literally named "undefined" still needs its name in the answer.
  const named = asLena(good);
  delete named.source.config.repo_name;
  assert.match(notAsWanted(named, { ...want, gh: { owner: OWNER, repo: 'undefined' } }).join('; '), /connected to lena-example\/undefined/);
});

test('10: no build Cloudflare started from a push: each run waits and names the causes; a failed push build is proof, said as a failure', () =>
  scenario((h) => finishedState(h), async ({ go, state }) => {
    state.deployments[REPO] = state.deployments[REPO].filter((d) => !pushProof(d));
    for (let i = 0; i < 2; i++) {
      const r = await go();
      assert.equal(r.code, 4, r.out);
      assert.match(r.out, /Not shown yet: that GitHub and Cloudflare are connected/);
      assert.match(r.out, /pushes one commit to a pull request/);
      assert.match(r.out, /the connection was never made or is broken/);
      assert.match(r.out, /builds are paused/);
    }
    state.deployments[REPO].unshift(deployment('failed', { commit: state.heads.main, branch: 'lenas-pr' }));
    const r = await go();
    assert.equal(r.code, 0, r.out);
    assert.match(r.out, /Cloudflare started a build of this commit \([0-9a-f]{7}\) from a push, and it failed/);
  }));

test('11: a project that builds no previews: the production branch\'s push shows the connection; a skipped push is no proof', () =>
  scenario((h) => finishedState(h), async ({ go, state }) => {
    state.projects = [project({ preview: 'none' })];
    state.deployments[REPO] = [deployment('skipped', { commit: state.heads.main, branch: 'lenas-pr' }), deployment('built', { commit: state.heads.production })];
    const r = await go();
    assert.equal(r.code, 4, r.out);
    assert.match(r.out, /does not build previews \(its setting is none\)/);
    assert.match(r.out, /npm run ship, on your word/);
    assert.match(r.out, /skipped it, since this project builds no previews: that is not proof/);
  }));

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
const NOTE = /Training is set to|Training was |Training read |Search is set to|Agent is set to|Search read |Agent read |Block AI bots setting|Bot Preference Sync is off|Bot Preference Sync reads|a value this kit does not know|To refuse AI training/;
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
    for (const st of ['change', 'as-is', 'skipped', 'unread', 'done', 'hand']) assert.deepEqual(aiNotes(botOf(c), st), [], `${c} ${st}`);
  }
  // The same check sees Block, so it cannot pass with no note code: C2's value swapped for C9's.
  assert.ok(aiNotes(botOf(AI.block), 'change').length > 0);
  assert.deepEqual(aiNotes(botOf(AI.block, { ai_training: botOf(AI.allow).ai_training }), 'change'), []);
  for (const c of [AI.allow, 'T2-040']) {
    const r = await aiRun(botOf(c));
    assert.doesNotMatch(r.ask.out + r.done.out, NOTE, c);
  }
});

test('S1 and S3: Training on Block: the ask warns that Google, Bing and Apple go too; the report says it is now Allow; code, PUT and exit as without the note', async () => {
  const blocked = await aiRun(botOf(AI.block));
  const plain = await aiRun(botOf(AI.searchBlock)); // the same change to the ai line, with no note in the ask
  assert.match(blocked.ask.out, /Training is set to Block\. Cloudflare says Block also keeps Googlebot, Bingbot and Applebot out, which affects search\. If you say yes, it becomes Allow \(do not block\)\. To refuse AI training and stay in search, choose Disallow for Training in the dashboard, turn Bot Preference Sync on there too \(choosing Disallow does not turn it on\), and run this with --skip ai\./);
  assert.doesNotMatch(plain.ask.out, NOTE);
  const [a, b] = await twoCodes(botOf(AI.block), botOf(AI.searchBlock));
  assert.equal(a, b);
  assert.equal(blocked.ask.code, plain.ask.code);
  assert.equal(blocked.put.body.ai_training, 'disabled');
  assert.deepEqual({ ...blocked.put.body, ai_training: 'x' }, { ...plain.put.body, ai_training: 'x' });
  assert.match(blocked.done.out, /Training was Block and is now Allow \(do not block\)\. To refuse AI training and stay in search/);
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
  for (const out of [blocked.ask.out, blocked.done.out]) assert.match(out, /Training is set to Block\. Cloudflare says Block also keeps Googlebot, Bingbot and Applebot out, which affects search\. This run leaves it as it is\. To refuse AI training and stay in search, .*and keep running this with --skip ai\./);
  const [a, b] = await twoCodes(botOf(AI.block), botOf(AI.allow), skip);
  assert.equal(a, b);
  assert.equal(blocked.ask.code, allowed.ask.code);
  assert.equal(blocked.done.code, allowed.done.code);
  assert.ok(!blocked.put || blocked.put.body.ai_training === 'block', 'Training is not written');
});

test('S5a: the zone\'s records could not be read: Training is not written, and the warning says this run did not change it, in the ask and after the yes', async () => {
  await scenario(freshState({ bot: botOf(AI.block), refuse: { 'GET dns': 403 } }), async ({ api, go }) => {
    const ask = await go();
    const done = await go(['--confirm', codeOf(ask)]);
    for (const out of [ask.out, done.out]) assert.match(out, /Training is set to Block\. Cloudflare says Block also keeps Googlebot, Bingbot and Applebot out, which affects search\. The zone's records could not be read, so this run did not change it\. To refuse AI training and stay in search, .*and run this with --skip ai\./);
    assert.ok(!api.writes().some((e) => e.method === 'PUT'), 'Bot Management is not written');
    assert.ok(api.writes().length > 0, 'the yes wrote something else, the case "nothing was written" got wrong');
  });
  // Disallow in the same state: the same claim, and S7's note when Sync is off.
  const notes = aiNotes(botOf(AI.disallowSyncOff), 'unread');
  assert.match(notes[0], /^Training is set to Disallow\. The zone's records could not be read, so this run did not change it/);
  assert.match(notes[1], /^Bot Preference Sync is off, so Disallow writes no/);
});

test('S5b: a change Cloudflare did not confirm names what Training read before the run, and claims nothing about now', async () => {
  const unconfirmed = /Training read Block before this run; Cloudflare did not confirm the change, so look at it in the dashboard: .*Configure AI bot policies\.\n.*To refuse AI training and stay in search/;
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
  assert.match(older.ask.out, /The older Block AI bots setting \(no longer shown in the dashboard\) is set to block, and this run leaves it as it is/);
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

// The stub answers the launch day's calls as Cloudflare did.
test('the stub answers attaching, a record PATCH and a comment as Cloudflare did (T1-085 to T1-132, T2-042 to T2-058)', () => {
  const state = freshState({ projects: [project()] });
  const attach = fixture('T1-085');
  const r = handle(state, 'POST', `/accounts/a/pages/projects/${REPO}/domains`, new URLSearchParams(), attach.request.body);
  assert.equal(r.body.result.status, attach.response.result.status, 'initializing, and no record made');
  assert.equal(state.dns.length, 0);
  const pending = handle(state, 'GET', `/accounts/a/pages/projects/${REPO}/domains/${attach.request.body.name}`, new URLSearchParams(), null);
  assert.deepEqual(pending.body.result.verification_data, fixture('T1-086').response.result.verification_data, '"CNAME record not set"');
  // An A record, PATCHed to a proxied CNAME with a comment: same id, and Cloudflare's message (T2-046).
  const a = fixture('T2-042');
  state.dns = [{ ...a.response.result }];
  const patch = fixture('T2-046');
  const p = handle(state, 'PATCH', `/zones/z/dns_records/${a.response.result.id}`, new URLSearchParams(), patch.request.body);
  assert.equal(p.body.result.id, a.response.result.id, 'the PATCH keeps the id');
  assert.deepEqual([p.body.result.type, p.body.result.proxied, p.body.result.comment], [patch.response.result.type, true, patch.response.result.comment]);
  assert.deepEqual(p.body.messages, patch.response.messages, 'changing the type is said to be deprecated');
  assert.equal(patch.response.messages[0].message, 'DNS record type update is deprecated');
  // A comment of 100 characters is kept; 101 is refused, 9313 (T2-057, T2-058).
  assert.equal(fixture('T2-057').request.body.comment.length, 100);
  const long = fixture('T2-058');
  assert.equal(long.request.body.comment.length, 101);
  const refused = handle(state, 'PATCH', `/zones/z/dns_records/${a.response.result.id}`, new URLSearchParams(), long.request.body);
  assert.deepEqual([refused.status, refused.body.errors], [long.status, long.response.errors]);
});

const LIVE = `${REPO}.pages.dev`;
// A site ready for launch day: setup finished (finishedState), its live build recording the project's
// variables, the domain not attached, and the apex holding one A record at the old host.
function launchState(heads, { record = { id: 'apex1', type: 'A', name: HOST, content: '192.0.2.10', proxied: false, comment: null }, ...over } = {}) {
  const s = finishedState(heads, over);
  s.deployments[REPO][1].env_vars = {};
  s.dns = record ? [record] : [];
  return s;
}
async function launchScenario(stateFn, fn, siteOpts = {}) {
  return scenario(stateFn, async (x) => {
    const sites = await startSites(x.state);
    try {
      return await fn({ ...x, sites, launch: (args = [], o = {}) => run(x.where, args, { api: x.api, dns: x.dns, sites, stage: 'launch', ...o }) });
    } finally {
      await sites.close();
    }
  }, siteOpts);
}
// The domain attached already, by hand or by an earlier run: on the project's list and in the stub.
const attachHost = (s, status = 'active') => { s.domains[REPO] = [attachedDomain(HOST, status)]; s.projects[0].domains.push(HOST); return s; };
const domainsCalls = (api) => api.log.filter((e) => /\/domains/.test(e.path));
const activate = (state, status = 'active') => { for (const d of state.domains[REPO] ?? []) d.status = status; };

test('23 and 28: everything holds: the question names it all; the code attaches and points the record; once active, the first request, the forwarding, then 0', () =>
  launchScenario((h) => launchState(h), async ({ api, state, sites, launch }) => {
    const q = await launch();
    assert.equal(q.code, 3, q.out);
    assert.deepEqual(sites.asked.site, [], 'the domain is asked nothing before the yes');
    assert.deepEqual(api.writes(), []);
    const commit = state.heads.production.slice(0, 7);
    assert.match(q.out, new RegExp(`Attach ${HOST} to the project ${REPO}`));
    assert.match(q.out, new RegExp(`now A 192\\.0\\.2\\.10, DNS only; it becomes CNAME ${LIVE}, proxied`));
    assert.match(q.out, new RegExp(`This makes the site public: https://${HOST}/ serves commit ${commit}`));
    assert.match(q.out, /errors for a few minutes/);
    assert.match(q.out, new RegExp(`CANONICAL_URL = https://${HOST} for production`));
    assert.match(q.out, /If the domain still sends the NEL headers: add the checklist's rule "Remove NEL headers"/);
    const code = codeOf(q);

    const first = await launch(['--confirm', code]);
    assert.equal(first.code, 4, first.out);
    assert.deepEqual(api.writes().map((e) => `${e.method} ${e.path.replace(/\/(accounts|zones)\/[^/]+/, '/$1/X')}`), [
      `POST /accounts/X/pages/projects/${REPO}/domains`, 'PATCH /zones/X/dns_records/apex1']);
    assert.deepEqual(api.writes()[1].body, { type: 'CNAME', content: LIVE, proxied: true, comment: 'Was: A 192.0.2.10, DNS only.' });
    assert.deepEqual(sites.asked.site, [], 'still nothing asked of the domain while it is pending');
    assert.match(first.out, /Waiting for Cloudflare to take on lenas-backstube\.example: it says pending \(CNAME record not set\)/);
    assert.match(first.out, /Cloudflare said: DNS record type update is deprecated/);

    activate(state);
    const second = await launch(['--confirm', code]);
    assert.equal(second.code, 4, second.out);
    assert.ok(sites.asked.site.includes('/build.txt'), 'the first request went to the domain, through the check');
    assert.match(second.out, new RegExp(`ok\\s+${HOST} serves ${commit}`));
    const patches = api.writes().filter((e) => e.method === 'PATCH' && /pages\/projects/.test(e.path));
    assert.deepEqual(patches.map((e) => e.body), [{ deployment_configs: { production: { env_vars: { CANONICAL_URL: { type: 'plain_text', value: `https://${HOST}` } } } } }], 'CANONICAL_URL alone');
    assert.equal(api.writes().filter((e) => e.path.endsWith('/deployments')).length, 1, 'one production build');

    api.finish(REPO, 'success');
    const done = await launch(['--confirm', code]);
    assert.equal(done.code, 0, done.out);
    assert.ok(sites.asked.pages.some((x) => x.startsWith('/robots.txt?cb=')), 'the forwarding was asked for a page with a query');
    assert.match(done.out, /Launched\. Status 0\./);
    const again = await launch();
    assert.equal(again.code, 0, again.out);
    assert.doesNotMatch(again.out, /--confirm/, '32: a finished launch asks nothing');
  }));

test('19: the commit that goes live still lists unfilled pages: refused, the entries named, nothing asked or attached', () =>
  launchScenario((h) => launchState(h), async ({ api, sites, launch }) => {
    const r = await launch();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /UNFILLED_UNTIL_LAUNCH in tests\/placeholders\.spec\.ts still lists \/privacy, \/impressum, \/manifest\.webmanifest/);
    assert.doesNotMatch(r.out, /--confirm/);
    assert.deepEqual(domainsCalls(api), [], 'no call to the domains API');
    assert.deepEqual(sites.asked.site, []);
  }, { files: { 'tests/placeholders.spec.ts': STARTER_SPEC } }));

test('20: a draft token in src/, a German site\'s own token, two tokens that differ, no placeholder test: refused, and said which', async () => {
  const german = (spec) => {
    const out = EMPTY_LIST(spec).replace('const DRAFT_TOKEN = /^\\[MISSING:/;', 'const DRAFT_TOKEN = /^\\[FEHLT:/;');
    assert.ok(out.includes('const DRAFT_TOKEN = /^\\[FEHLT:/;'), 'the starter\'s DRAFT_TOKEN line changed');
    return out;
  };
  const cases = [
    [{ 'src/pages/hours.astro': '<p>Open [MISSING: opening hours]</p>\n' }, /the search for "\[MISSING:" in src\/ and public\/ finds src\/pages\/hours\.astro:1/],
    [{ 'tests/placeholders.spec.ts': german(STARTER_SPEC), '.github/workflows/ci.yml': STARTER_CI.replace("grep -rnI '\\[MISSING:' src public", "grep -rnI '\\[FEHLT:' src public"), 'src/pages/zeiten.astro': '<p>\n[FEHLT: Öffnungszeiten]</p>\n' },
      /the search for "\[FEHLT:" in src\/ and public\/ finds src\/pages\/zeiten\.astro:2/],
    [{ 'tests/placeholders.spec.ts': german(STARTER_SPEC) }, /DRAFT_TOKEN in tests\/placeholders\.spec\.ts is "\[FEHLT:" and ci\.yml searches for "\[MISSING:".*cannot tell.*attached by hand/s],
    [{ 'tests/placeholders.spec.ts': null }, /tests\/placeholders\.spec\.ts is missing at that commit.*cannot tell.*attached by hand/s],
  ];
  for (const [files, want] of cases) {
    await launchScenario((h) => launchState(h), async ({ api, launch }) => {
      const r = await launch();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, want);
      assert.deepEqual(domainsCalls(api), []);
    }, { files });
  }
});

test('21: the head has no good production build: queued waits; failed, never built, uploaded, built under main are refused, each named', async () => {
  const cases = [
    [(s, h) => { s.deployments[REPO].unshift(deployment('queued', { commit: h.production })); }, 4, /Waiting for the build under way/],
    [(s, h) => { s.deployments[REPO][1] = deployment('failed', { commit: h.production, env: 'production' }); }, 1, /The build of the head of production failed/],
    [(s) => { s.deployments[REPO][1] = deployment('built', { commit: 'ba5e000000000000000000000000000000000099' }); }, 1, /Cloudflare did not build the head of production \([0-9a-f]{7}\), so the connection to GitHub may be broken/],
    [(s, h) => { s.deployments[REPO][1] = deployment('upload', { commit: h.production }); }, 1, /was uploaded, not built by Cloudflare/],
    [(s, h) => { s.deployments[REPO][1] = deployment('built', { commit: h.production, productionBranch: 'main' }); }, 1, /was built while main was the production branch/],
  ];
  for (const [spoil, code, want] of cases) {
    await launchScenario((h) => { const s = launchState(h); spoil(s, h); return s; }, async ({ api, launch }) => {
      const r = await launch();
      assert.equal(r.code, code, r.out);
      assert.match(r.out, want);
      assert.doesNotMatch(r.out, /npm run ship/, 'no advice to ship');
      assert.deepEqual(domainsCalls(api), []);
    });
  }
});

test('22: no push build of any age is refused; an old one, with launch\'s own forwarding build after it, still stands', async () => {
  await launchScenario((h) => { const s = launchState(h); s.deployments[REPO] = s.deployments[REPO].filter((d) => !pushProof(d)); return s; }, async ({ launch }) => {
    const r = await launch();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /never built this project from a push, so the connection to GitHub was not shown/);
  });
  await launchScenario((h) => {
    const s = launchState(h);
    const forwardingBuild = deployment('built', { commit: h.production });
    forwardingBuild.env_vars = {};
    s.deployments[REPO] = [forwardingBuild, deployment('push', { commit: h.main, branch: 'lenas-pr' }), ...s.deployments[REPO].slice(1)];
    return s;
  }, async ({ launch }) => {
    const r = await launch();
    assert.equal(r.code, 3, r.out);
  });
});

test('24: two address records, a CNAME host that also holds a TXT record, a token that cannot read DNS: refused, nothing attached', async () => {
  const www = `www.${HOST}`;
  const cases = [
    [(s) => { s.dns.push({ id: 'apex6', type: 'AAAA', name: HOST, content: '2001:db8::10', proxied: false }); }, {}, /has 2 address records .*deletes no record/],
    [(s) => { s.dns = [{ id: 'w1', type: 'A', name: www, content: '192.0.2.10', proxied: false }, { id: 'w2', type: 'TXT', name: www, content: '"made-up"', proxied: false }]; }, { url: `https://${www}` }, /also has a TXT record, and a CNAME cannot stand beside a record of another type/],
    [(s) => { s.refuse['GET dns'] = 403; }, {}, /refused to list the zone's records .*Zone → DNS → Edit.*Going live/s],
  ];
  for (const [spoil, siteOpts, want] of cases) {
    await launchScenario((h) => { const s = launchState(h); spoil(s); return s; }, async ({ api, launch }) => {
      const r = await launch();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, want);
      assert.ok(!api.writes().length, 'no attach call');
    }, siteOpts);
  }
});

test('25: Cloudflare says error on a later run: 1 with its words; the domain stays; the old record comes from the comment', () =>
  launchScenario((h) => launchState(h, { record: { id: 'apex1', type: 'A', name: HOST, content: '192.0.2.10', proxied: false, comment: 'old host, until the relaunch' } }), async ({ api, state, launch }) => {
    const code = codeOf(await launch());
    assert.equal((await launch(['--confirm', code])).code, 4);
    assert.equal(state.dns[0].comment, 'Was: A 192.0.2.10, DNS only. old host, until the relaunch', 'the owner\'s comment after the note');
    activate(state, 'error');
    state.domains[REPO][0].verification_data = { status: 'error', error_message: 'MADE: the reason Cloudflare gives' };
    const r = await launch(['--confirm', code]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /Cloudflare says lenas-backstube\.example is error: MADE: the reason Cloudflare gives\. The domain stays attached/);
    assert.match(r.out, /as the script noted it in the record's comment: A 192\.0\.2\.10, DNS only\. old host/);
    assert.ok(!api.log.some((e) => e.method === 'DELETE'), 'nothing detached or deleted');
  }));

test('26: the domain serves another commit, or no build.txt: a failure, and nothing after it', async () => {
  for (const serves of ['ba5e000000000000000000000000000000000077', null]) {
    await launchScenario((h) => { const s = launchState(h); attachHost(s); s.siteServes = serves; return s; }, async ({ api, launch }) => {
      const r = await launch();
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /is active, but the check of its build is not ok/);
      assert.deepEqual(api.writes(), [], 'no forwarding, no rule');
    });
  }
});

test('27: the domain still sends the NEL headers: one rule added beside the others; or a ruleset created; or nothing when the kit\'s rule is there', async () => {
  const other = (n) => ({ id: `c0ffee000000000000000000000001${n}0`, version: '1', action: 'rewrite', expression: 'true', description: `Lena's own rule ${n}`, enabled: true, action_parameters: { headers: { [`x-lena-${n}`]: { operation: 'set', value: '1' } } } });
  const kit = { ...other(9), description: 'Remove NEL headers', action_parameters: { headers: { NEL: { operation: 'remove' }, 'Report-To': { operation: 'remove' } } } };
  const live = (h, ruleset) => { const s = launchState(h); attachHost(s); s.siteSendsNel = true; s.ruleset = ruleset; s.projects[0].deployment_configs.production.env_vars = { CANONICAL_URL: { type: 'plain_text', value: `https://${HOST}` } }; s.deployments[REPO][1].env_vars = { CANONICAL_URL: { type: 'plain_text', value: `https://${HOST}` } }; return s; };
  const ruleWrites = (api) => api.writes().filter((e) => /rulesets/.test(e.path));
  // Two rules there: one call adds the new rule alone; the two keep their ids.
  await launchScenario((h) => live(h, { id: 'rs1', version: '2', rules: [other(1), other(2)] }), async ({ api, state, launch }) => {
    const q = await launch();
    assert.equal(q.code, 3, q.out);
    assert.match(q.out, /The domain still sends the NEL headers: add the checklist's rule/);
    assert.doesNotMatch(q.out, /CANONICAL_URL/, 'the forwarding answers already');
    const r = await launch(['--confirm', codeOf(q)]);
    assert.equal(r.code, 4, r.out);
    assert.deepEqual(ruleWrites(api).map((e) => [e.method, e.path.replace(/\/zones\/[^/]+/, '')]), [['POST', '/rulesets/rs1/rules']]);
    assert.equal(ruleWrites(api)[0].body.description, 'Remove NEL headers');
    assert.deepEqual(state.ruleset.rules.slice(0, 2).map((x) => x.id), [other(1).id, other(2).id]);
    const after = await launch(['--confirm', codeOf(q)]);
    assert.equal(after.code, 0, after.out);
  });
  // No ruleset: one PUT creates it with the rule.
  await launchScenario((h) => live(h, null), async ({ api, launch }) => {
    const r = await launch(['--confirm', codeOf(await launch())]);
    assert.equal(r.code, 4, r.out);
    assert.deepEqual(ruleWrites(api).map((e) => e.method), ['PUT']);
    assert.deepEqual(ruleWrites(api)[0].body.rules.map((x) => x.description), ['Remove NEL headers']);
  });
  // None at the first read, one by the read just before the PUT: the add-rule call, or nothing.
  for (const [appears, method, code] of [[{ id: 'rs2', version: '1', rules: [other(1)] }, 'POST', 4], [{ id: 'rs3', version: '1', rules: [kit] }, null, 1]]) {
    await launchScenario((h) => live(h, null), async ({ api, state, launch }) => {
      const q = await launch();
      let reads = 0;
      state.after = (e) => { if (e.method === 'GET' && /phases/.test(e.path) && ++reads === 1) state.ruleset = JSON.parse(JSON.stringify(appears)); };
      const r = await launch(['--confirm', codeOf(q)]);
      assert.equal(r.code, code, r.out);
      assert.deepEqual(ruleWrites(api).map((e) => e.method), method ? [method] : []);
    });
  }
  // The kit's rule already there and the headers still come: nothing added, 1.
  await launchScenario((h) => live(h, { id: 'rs4', version: '1', rules: [{ ...kit, enabled: false }] }), async ({ api, launch }) => {
    const r = await launch();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /already hold "Remove NEL headers": the rule is there and the headers still come/);
    assert.deepEqual(ruleWrites(api), []);
  });
  // --skip nel-rule: no rule; nel is left to Lena, status 0.
  await launchScenario((h) => live(h, null), async ({ api, launch }) => {
    const r = await launch(['--skip', 'nel-rule']);
    assert.equal(r.code, 0, r.out);
    assert.match(r.out, /Left to you: Network Error Logging \(NEL\): Off fails/);
    assert.deepEqual(api.writes(), []);
  });
});

test('28: an adopted project with another variable and a secret: CANONICAL_URL is saved alone, both stay, one build', () =>
  launchScenario((h) => {
    const s = launchState(h);
    const vars = { PLAIN_ONE: { type: 'plain_text', value: 'one' }, A_SECRET: { type: 'secret_text', value: '' } };
    s.projects[0].deployment_configs.production.env_vars = vars;
    s.deployments[REPO][1].env_vars = JSON.parse(JSON.stringify(vars));
    attachHost(s);
    return s;
  }, async ({ api, state, launch }) => {
    const q = await launch();
    assert.match(q.out, /takes the project's secrets \(A_SECRET\) as they are saved now/);
    const r = await launch(['--confirm', codeOf(q)]);
    assert.equal(r.code, 4, r.out);
    assert.deepEqual(Object.keys(state.projects[0].deployment_configs.production.env_vars).sort(), ['A_SECRET', 'CANONICAL_URL', 'PLAIN_ONE']);
    assert.match(r.out, /before: A_SECRET \(production\), PLAIN_ONE \(production\); after: A_SECRET \(production\), CANONICAL_URL \(production\), PLAIN_ONE \(production\)/);
    assert.equal(api.writes().filter((e) => e.path.endsWith('/deployments')).length, 1);
  }));

test('29: the head is newer than the live build, another variable changed, or the live build was uploaded: saved, no build, and said why', async () => {
  const cases = [
    ['push', /the head of production \([0-9a-f]{7}\) is not the live commit/],
    [(s) => { s.projects[0].deployment_configs.production.env_vars = { PLAIN_ONE: { type: 'plain_text', value: 'two' } }; s.deployments[REPO][1].env_vars = { PLAIN_ONE: { type: 'plain_text', value: 'one' } }; }, /the variable PLAIN_ONE changed since the live build/],
    [(s, h) => { s.deployments[REPO][1] = Object.assign(deployment('upload', { commit: h.production }), { env_vars: {} }); }, /the live build was uploaded, not built by Cloudflare/],
  ];
  for (const [spoil, want] of cases) {
    await launchScenario((h) => { const s = launchState(h); attachHost(s); if (spoil !== 'push') spoil(s, h); return s; }, async ({ api, where, state, launch }) => {
      if (spoil === 'push') { // the production branch moves on after the live build
        writeFileSync(path.join(where.site, 'news.md'), 'new\n');
        git(where.site, 'add', 'news.md');
        git(where.site, 'commit', '-q', '-m', 'news');
        git(where.site, 'push', '-q', 'origin', 'HEAD:production');
      }
      const r = await launch(['--confirm', codeOf(await launch())]);
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /The variable is saved, but no build has picked it up/);
      assert.match(r.out, want);
      assert.equal(state.projects[0].deployment_configs.production.env_vars.CANONICAL_URL.value, `https://${HOST}`);
      assert.ok(!api.writes().some((e) => e.path.endsWith('/deployments')), 'no deployment call');
    });
  }
});

test('30: --skip canonical: the question does not name the forwarding, and CANONICAL_URL is not written', () =>
  launchScenario((h) => launchState(h), async ({ api, state, launch }) => {
    const q = await launch(['--skip', 'canonical']);
    assert.equal(q.code, 3, q.out);
    assert.doesNotMatch(q.out, /CANONICAL_URL/);
    const code = codeOf(q);
    await launch(['--skip', 'canonical', '--confirm', code]);
    activate(state);
    const r = await launch(['--skip', 'canonical', '--confirm', code]);
    assert.equal(r.code, 0, r.out);
    assert.ok(!api.writes().some((e) => e.method === 'PATCH' && /pages\/projects/.test(e.path)), 'no variable written');
    assert.match(r.out, /does not forward to the domain: --skip canonical/);
  }));

test('31: attached by hand and active: no launch condition checked, nothing attached; the question names the forwarding and the commit; a newer queued build waits', async () => {
  // The list of unfilled pages is not checked: the site is public already.
  await launchScenario((h) => { const s = launchState(h); attachHost(s); return s; }, async ({ api, state, launch }) => {
    const q = await launch();
    assert.equal(q.code, 3, q.out);
    assert.match(q.out, new RegExp(`is live and serves commit ${state.heads.production.slice(0, 7)}, the newest production build that succeeded`));
    assert.match(q.out, /Save the variable CANONICAL_URL/);
    assert.doesNotMatch(q.out, /Attach|UNFILLED/);
    assert.ok(!api.writes().length);
  }, { files: { 'tests/placeholders.spec.ts': STARTER_SPEC } });
  await launchScenario((h) => { const s = launchState(h); attachHost(s); s.deployments[REPO].unshift(deployment('queued', { commit: h.production })); return s; }, async ({ launch }) => {
    const r = await launch();
    assert.equal(r.code, 4, r.out);
    assert.match(r.out, /Waiting for the production build under way/);
  });
});

test('42: the live build has CANONICAL_URL and pages.dev still answers 200: no PATCH, no build, the checklist\'s causes, 1', () =>
  launchScenario((h) => {
    const s = launchState(h);
    attachHost(s);
    s.deployments[REPO][1].env_vars = { CANONICAL_URL: { type: 'plain_text', value: `https://${HOST}` } };
    s.pagesStays200 = true;
    return s;
  }, async ({ api, launch }) => {
    const r = await launch();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /The live build has CANONICAL_URL = https:\/\/lenas-backstube\.example, and https:\/\/lenas-backstube\.pages\.dev\/ still does not forward/);
    assert.match(r.out, /the day's Functions allowance ran out/);
    assert.deepEqual(api.writes(), []);
  }));

test('41: --skip bot with Bot Fight Mode on: listed as left to Lena, 0; Always Use HTTPS turned off since, with no --skip: 1', async () => {
  const done = (h) => { const s = launchState(h); attachHost(s); const v = { CANONICAL_URL: { type: 'plain_text', value: `https://${HOST}` } }; s.projects[0].deployment_configs.production.env_vars = v; s.deployments[REPO][1].env_vars = JSON.parse(JSON.stringify(v)); return s; };
  await launchScenario((h) => { const s = done(h); s.bot.fight_mode = true; return s; }, async ({ launch }) => {
    const r = await launch(['--skip', 'bot']);
    assert.equal(r.code, 0, r.out);
    assert.match(r.out, /Left to you: Bot Fight Mode: Off fails/);
  });
  await launchScenario((h) => { const s = done(h); s.settings.always_use_https = 'off'; return s; }, async ({ launch }) => {
    const r = await launch();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /FAIL\s+Always Use HTTPS: On/);
    assert.match(r.out, /its --skip https belongs on the command/);
  });
});

test('36 and 37: the report of a finished launch: two-stage names main\'s preview; single-stage names none', async () => {
  const finished = (h) => { const s = launchState(h); attachHost(s); const v = { CANONICAL_URL: { type: 'plain_text', value: `https://${HOST}` } }; s.projects[0].deployment_configs.production.env_vars = v; s.deployments[REPO][1].env_vars = JSON.parse(JSON.stringify(v)); return s; };
  await launchScenario((h) => { const s = finished(h); s.deployments[REPO].unshift(deployment('push', { commit: h.main, branch: 'main' })); return s; }, async ({ launch }) => {
    const r = await launch();
    assert.equal(r.code, 0, r.out);
    const report = r.out.slice(r.out.indexOf('Live: '));
    assert.match(report, /^Live: https:\/\/lenas-backstube\.example\/ serves [0-9a-f]{7}\./m);
    assert.match(report, /The preview of main, as Cloudflare lists it: https:\/\/main\.lenas-backstube\.pages\.dev/);
    assert.match(report, /https:\/\/lenas-backstube\.pages\.dev\/ forwards to https:\/\/lenas-backstube\.example\//);
    assert.match(report, /As the project reads now through the API: Fail open on for production and on for previews; build command npm run build, output folder dist\. This stage does not read Minimum TLS Version or the AI fields: the setup stage, run again, shows them.*ssllabs/s);
    assert.match(report, /Crawler Hints, the Web Analytics switch, the script monitor's switch/);
    assert.match(report, /HSTS once the site has worked for a few days, not before \d{4}-\d{2}-\d{2}/);
    assert.match(report, /behind a sign-in/);
    assert.match(report, /Delete the token now/);
  });
  await launchScenario((h) => finished(h), async ({ api, launch }) => {
    const r = await launch();
    assert.equal(r.code, 0, r.out);
    assert.ok(!api.log.some((e) => /\/settings\/|bot_management/.test(e.path)), 'launch reads no zone setting, so its report claims no read');
    assert.match(r.out, /main is the live site \(main\); each pull request gets a preview of its own/);
    assert.doesNotMatch(r.out, /preview of main/);
  }, { prodBranch: 'main', production: false });
});

test('launch report: a preview of main with no alias is not called missing either', () =>
  launchScenario((h) => {
    const s = attachHost(launchState(h));
    const v = { CANONICAL_URL: { type: 'plain_text', value: `https://${HOST}` } };
    s.projects[0].deployment_configs.production.env_vars = v;
    s.deployments[REPO][1].env_vars = JSON.parse(JSON.stringify(v));
    const p = deployment('push', { commit: h.main, branch: 'main' });
    p.aliases = null; // as T1-021's deployments have it
    s.deployments[REPO].unshift(p);
    return s;
  }, async ({ launch }) => {
    const r = await launch();
    assert.equal(r.code, 0, r.out);
    assert.doesNotMatch(r.out, /preview of main/i, 'nothing is said about a preview with no address');
  }));

test('launch report: a preview of main further back than the pages read is not called missing', () =>
  launchScenario((h) => {
    const s = attachHost(launchState(h));
    const v = { CANONICAL_URL: { type: 'plain_text', value: `https://${HOST}` } };
    s.projects[0].deployment_configs.production.env_vars = v;
    s.deployments[REPO][1].env_vars = JSON.parse(JSON.stringify(v));
    s.deployments[REPO].push(deployment('push', { commit: h.main, branch: 'main' })); // third, past two pages of one
    s.perPage = { ...s.perPage, deployments: 1 };
    return s;
  }, async ({ launch }) => {
    const r = await launch();
    assert.equal(r.code, 0, r.out);
    assert.doesNotMatch(r.out, /preview of main/i, 'nothing is said about a preview not found among the deployments read');
  }));

test('35 at launch: the record points at the address Cloudflare gave, and no address is made from the name', () =>
  launchScenario((h) => { const s = launchState(h); s.projects = [project({ subdomain: `${REPO}-9x2.pages.dev` })]; return s; }, async ({ api, launch }) => {
    const q = await launch();
    assert.match(q.out, /it becomes CNAME lenas-backstube-9x2\.pages\.dev, proxied/);
    await launch(['--confirm', codeOf(q)]);
    assert.equal(api.writes().find((e) => e.method === 'PATCH').body.content, `${REPO}-9x2.pages.dev`);
    assert.doesNotMatch(q.out, /lenas-backstube\.pages\.dev/);
  }));

test('38 at launch: the check script runs without the token in its environment', async (t) => {
  const record = path.join(scratch, 'check-env.txt');
  const recorder = path.join(scratch, 'record-env.mjs');
  writeFileSync(recorder, `import { appendFileSync } from 'node:fs';\nif ((process.argv[1] ?? '').endsWith('cloudflare-check.mjs')) appendFileSync(${JSON.stringify(record)}, JSON.stringify(process.env) + '\\n');\n`);
  await launchScenario((h) => { const s = launchState(h); attachHost(s); return s; }, async ({ launch }) => {
    const r = await launch([], { env: { NODE_OPTIONS: `--import ${pathToFileURL(recorder).href}`, LENA_TOKEN_COPY: TOKEN } });
    assert.equal(r.code, 3, r.out);
  });
  if (!existsSync(record)) { t.skip('this Node does not take --import in NODE_OPTIONS'); return; }
  const seen = readFileSync(record, 'utf8');
  assert.ok(seen.length > 0, 'the check script ran and was recorded');
  assert.ok(!seen.includes(TOKEN), 'the check script saw no token, under its own name or another');
});

test('39 at launch: a run cut off after the attach call: the next run with the code writes the record and carries on', async (t) => {
  if (process.platform === 'win32') { t.skip('stopping the program mid-run uses a POSIX signal'); return; }
  await launchScenario((h) => launchState(h), async ({ api, where, dns, sites, state, launch }) => {
    const code = codeOf(await launch());
    let release;
    const held = new Promise((r) => { release = r; });
    const child = spawn(process.execPath, [SCRIPT, 'launch', '--confirm', code], {
      cwd: where.site, stdio: 'ignore',
      env: { ...cleanEnv(), CLOUDFLARE_API_TOKEN: TOKEN, CLOUDFLARE_SETUP_API: api.origin, CLOUDFLARE_SETUP_RESOLVER: dns.address, CLOUDFLARE_SETUP_SITE: sites.site, CLOUDFLARE_SETUP_PAGES: sites.pages },
    });
    state.after = (e) => { if (e.method === 'POST' && e.path.endsWith('/domains')) { child.kill('SIGKILL'); release(); } };
    await held;
    await new Promise((r) => child.on('close', r));
    state.after = null;
    assert.equal(state.dns[0].type, 'A', 'the record was not reached');
    const r = await launch(['--confirm', code]);
    assert.equal(r.code, 4, r.out);
    assert.equal(api.writes().filter((e) => e.method === 'POST' && e.path.endsWith('/domains')).length, 1, 'no second attach');
    assert.deepEqual([state.dns[0].type, state.dns[0].content], ['CNAME', LIVE]);
  });
});

test('launch: a code from another commit does not fit: the question again, with a new code, nothing changed', () =>
  launchScenario((h) => launchState(h), async ({ api, where, state, launch }) => {
    const q = await launch();
    writeFileSync(path.join(where.site, 'news.md'), 'new\n');
    git(where.site, 'add', 'news.md');
    git(where.site, 'commit', '-q', '-m', 'news');
    git(where.site, 'push', '-q', 'origin', 'HEAD:main', 'HEAD:production');
    // Cloudflare built the new head, so every launch condition holds and only the code can stop it.
    const built = deployment('built', { commit: git(where.site, 'rev-parse', 'HEAD') });
    built.env_vars = {};
    state.deployments[REPO].unshift(built);
    const r = await launch(['--confirm', codeOf(q)]);
    assert.equal(r.code, 3, r.out);
    assert.match(r.out, /does not fit this question/);
    assert.notEqual(codeOf(r), codeOf(q));
    assert.deepEqual(api.writes(), []);
  }));

test('launch: a pending domain the project\'s list does not name is found through the domains API: no second attach', () =>
  launchScenario((h) => Object.assign(launchState(h), { pendingUnlisted: true }), async ({ api, state, launch }) => {
    const code = codeOf(await launch());
    assert.equal((await launch(['--confirm', code])).code, 4);
    const again = await launch(['--confirm', code]);
    assert.equal(again.code, 4, again.out);
    assert.equal(api.writes().filter((e) => e.method === 'POST' && e.path.endsWith('/domains')).length, 1, 'one attach');
    assert.equal(api.writes().filter((e) => /dns_records/.test(e.path)).length, 1, 'one record write');
    activate(state);
    state.projects[0].deployment_configs.production.env_vars = { CANONICAL_URL: { type: 'plain_text', value: `https://${HOST}` } };
    state.deployments[REPO][1].env_vars = { CANONICAL_URL: { type: 'plain_text', value: `https://${HOST}` } };
    const done = await launch(['--confirm', code]);
    assert.equal(done.code, 0, done.out);
  }));

test('launch: a yes to the forwarding alone is no yes to a NEL rule: the rule asks again', () =>
  launchScenario((h) => attachHost(launchState(h)), async ({ api, state, launch }) => {
    const q = await launch();
    assert.equal(q.code, 3, q.out);
    assert.doesNotMatch(q.out, /NEL/, 'the question lists the forwarding only');
    state.siteSendsNel = true; // the headers appear before the yes
    const r = await launch(['--confirm', codeOf(q)]);
    assert.equal(r.code, 3, r.out);
    assert.match(r.out, /does not fit this question/);
    assert.ok(!api.writes().some((e) => /rulesets/.test(e.path)), 'no rule written on a yes that did not list it');
  }));

test('launch: an answer to the build call that names no commit cannot be checked: said, and 1', () =>
  launchScenario((h) => Object.assign(attachHost(launchState(h)), { deployAnswerNoCommit: true }), async ({ launch }) => {
    const r = await launch(['--confirm', codeOf(await launch())]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /its answer names no commit, so whether it is of the live commit [0-9a-f]{7} could not be checked/);
  }));

test('launch: the production branch gone from GitHub just before the build call: no build, said so', () =>
  launchScenario((h) => attachHost(launchState(h)), async ({ api, where, state, launch }) => {
    const q = await launch();
    state.after = (e) => { if (e.method === 'PATCH' && /pages\/projects/.test(e.path)) git(where.site, 'push', '-q', 'origin', ':production'); };
    const r = await launch(['--confirm', codeOf(q)]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /GitHub has no branch production any more/);
    assert.ok(!api.writes().some((e) => e.path.endsWith('/deployments')));
  }));

test('launch: a failed build that appears after the variable is saved stops the run too, before any build call', () =>
  launchScenario((h) => attachHost(launchState(h)), async ({ api, state, launch }) => {
    const q = await launch();
    state.after = (e) => { if (e.method === 'PATCH' && /pages\/projects/.test(e.path)) state.deployments[REPO].unshift(deployment('failed', { commit: state.heads.production, env: 'production' })); };
    const r = await launch(['--confirm', codeOf(q)]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /CANONICAL_URL is saved, and the newest production build failed/);
    assert.ok(!api.writes().some((e) => e.path.endsWith('/deployments')));
  }));

test('launch: a push to the production branch just before the build call: no build, and said why', () =>
  launchScenario((h) => attachHost(launchState(h)), async ({ api, where, state, launch }) => {
    const q = await launch();
    state.after = (e) => {
      if (e.method === 'PATCH' && /pages\/projects/.test(e.path)) {
        writeFileSync(path.join(where.site, 'late.md'), 'late\n');
        git(where.site, 'add', 'late.md');
        git(where.site, 'commit', '-q', '-m', 'late');
        git(where.site, 'push', '-q', 'origin', 'HEAD:production');
      }
    };
    const r = await launch(['--confirm', codeOf(q)]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /no build was started: production on GitHub is now at [0-9a-f]{7}, not at the live commit/);
    assert.ok(!api.writes().some((e) => e.path.endsWith('/deployments')), 'no build call');
  }));

test('launch: a live build made under another production branch gets no forwarding build', () =>
  launchScenario((h) => { const s = attachHost(launchState(h)); s.deployments[REPO][1].production_branch = 'main'; return s; }, async ({ api, launch }) => {
    const r = await launch(['--confirm', codeOf(await launch())]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /the live build was made while main was the production branch/);
    assert.ok(!api.writes().some((e) => e.path.endsWith('/deployments')));
  }));

test('launch: an attach refused because the domain is there already reads it and carries on', () =>
  launchScenario((h) => { const s = launchState(h, { pendingUnlisted: true }); s.domains[REPO] = [attachedDomain(HOST, 'pending')]; s.pendingUnlisted = true; return s; }, async ({ api, state, launch }) => {
    // Both runs' reads before the attach miss it (so the question lists the attach), the attach is
    // refused as already there, and the read after it finds the domain.
    state.hideDomainReads = 2;
    const q = await launch();
    assert.match(q.out, /Attach lenas-backstube\.example/);
    const r = await launch(['--confirm', codeOf(q)]);
    assert.equal(r.code, 4, r.out);
    assert.match(r.out, /is attached already: Cloudflare says pending/);
    assert.equal(api.writes().filter((e) => /dns_records/.test(e.path)).length, 1, 'the record was still written');
  }));

test('launch: after a failed production build the run stops; it starts no other', () =>
  launchScenario((h) => { const s = attachHost(launchState(h)); s.deployments[REPO].unshift(deployment('failed', { commit: h.production, env: 'production' })); return s; }, async ({ api, launch }) => {
    const r = await launch();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /The newest production build failed/);
    assert.ok(!api.writes().some((e) => e.path.endsWith('/deployments')));
  }));

test('launch: the forwarding build waits for the site\'s own production branch, and says so if the branch moved under it', async () => {
  await launchScenario((h) => { const s = attachHost(launchState(h)); s.projects[0].production_branch = 'main'; s.projects[0].source.config.production_branch = 'main'; return s; }, async ({ api, launch }) => {
    const r = await launch(['--confirm', codeOf(await launch())]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /the project's production branch is main, not production/);
    assert.ok(!api.writes().some((e) => e.path.endsWith('/deployments')), 'no build of the wrong branch');
  });
  await launchScenario((h) => attachHost(launchState(h)), async ({ state, launch }) => {
    const q = await launch();
    state.after = (e) => { if (e.method === 'PATCH' && /pages\/projects/.test(e.path)) state.heads = { ...state.heads, production: 'ba5e000000000000000000000000000000000066' }; };
    const r = await launch(['--confirm', codeOf(q)]);
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /Cloudflare started a production build of ba5e000, not of the live commit/);
  });
});

test('launch: an answer not seen yet waits; a redirect that is not the kit\'s stops', async () => {
  for (const [flag, code, want] of [
    ['siteDown', 4, /did not answer the check yet/],
    ['pagesProbeSilent', 4, /The forwarding could not be judged yet/],
    ['pagesRedirect302', 1, /forwards, but not as the kit's forwarding does/],
  ]) {
    await launchScenario((h) => {
      const s = Object.assign(attachHost(launchState(h)), { [flag]: true });
      // The probe is asked only when / forwards: the live build has the variable.
      if (flag === 'pagesProbeSilent') s.deployments[REPO][1].env_vars = { CANONICAL_URL: { type: 'plain_text', value: `https://${HOST}` } };
      return s;
    }, async ({ api, launch }) => {
      const r = await launch();
      assert.equal(r.code, code, `${flag}: ${r.out}`);
      assert.match(r.out, want);
      assert.deepEqual(api.writes(), []);
    });
  }
});

test('launch: the nameservers\' addresses: looked up one by one; none found is a wait, never a quiet fall back', async () => {
  const clock = { left: () => 30_000 };
  const zoneNs = { name: 'lenas.test', name_servers: ['ns1.lenas.test', 'ns2.lenas.test'] };
  assert.deepEqual(await nameserverIps(zoneNs, { clock, resolve4: async (n) => (n === 'ns1.lenas.test' ? ['192.0.2.53'] : ['192.0.2.53', '192.0.2.54']) }), ['192.0.2.53', '192.0.2.54']);
  assert.deepEqual(await nameserverIps(zoneNs, { clock, resolve4: async (n) => { if (n === 'ns1.lenas.test') throw new Error('no'); return ['192.0.2.54']; } }), ['192.0.2.54']);
  // Every way of finding no address gives the one message, which guesses no cause.
  const none = (e) => e.code === 4 && /This run found no address for the zone's nameservers \(Cloudflare lists: (ns1\.lenas\.test, ns2\.lenas\.test|none)\), and the domain is asked only through them\. Run the same command again in a minute; if this repeats, look them up by hand \(dig NS (lenas\.test|your domain)\)\.$/.test(e.message) && !/time|could not be looked up|undefined/.test(e.message);
  await assert.rejects(nameserverIps(zoneNs, { clock, resolve4: async () => { throw new Error('no'); } }), none);
  await assert.rejects(nameserverIps(zoneNs, { clock: { left: () => 2000 }, resolve4: async () => ['192.0.2.53'] }), none, 'too little time left is a wait too');
  await assert.rejects(nameserverIps({ name: 'lenas.test', name_servers: [] }, { clock, resolve4: async () => ['192.0.2.53'] }), none, 'no nameserver listed');
  await assert.rejects(nameserverIps({}, { clock, resolve4: async () => ['192.0.2.53'] }), none);
  assert.deepEqual(await nameserverIps(zoneNs, { clock, resolverAt: '127.0.0.1:5353' }), ['127.0.0.1:5353']);
});

test('launch: an owner\'s comment that only begins like the script\'s note is not read as the record before', () =>
  launchScenario((h) => launchState(h, { record: { id: 'apex1', type: 'A', name: HOST, content: '192.0.2.10', proxied: false, comment: 'Was: our old shop' } }), async ({ state, launch }) => {
    const code = codeOf(await launch());
    const r = await launch(['--confirm', code]);
    assert.equal(r.code, 4, r.out);
    assert.match(r.out, /The record before: A 192\.0\.2\.10, DNS only\./);
    assert.equal(state.dns[0].comment, 'Was: A 192.0.2.10, DNS only. Was: our old shop');
  }));

test('launch: a record too long to note in the comment is refused before the question', () =>
  launchScenario((h) => launchState(h, { record: { id: 'c9', type: 'CNAME', name: HOST, content: `${'x'.repeat(90)}.example.com`, proxied: false } }), async ({ api, launch }) => {
    const r = await launch();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /too long to note in the comment/);
    assert.deepEqual(api.writes(), []);
  }));

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
  const d = { env_vars: { A: { type: 'plain_text', value: '1' }, S: { type: 'secret_text', value: '' }, CANONICAL_URL: { type: 'plain_text', value: 'x' } }, build_config: { build_command: 'npm run build', destination_dir: 'dist', root_dir: '' } };
  const p = (vars, bc = {}) => ({ deployment_configs: { production: { env_vars: vars } }, build_config: { build_command: 'npm run build', destination_dir: 'dist', root_dir: '', ...bc } });
  assert.deepEqual(otherDifferences(d, p({ A: { type: 'plain_text', value: '1' }, S: { type: 'secret_text', value: '' }, CANONICAL_URL: { type: 'plain_text', value: 'y' } })), [], 'CANONICAL_URL alone; a secret by name');
  assert.deepEqual(otherDifferences(d, p({ A: { type: 'plain_text', value: '2' }, S: { type: 'secret_text', value: '' } })), ['the variable A changed since the live build']);
  assert.deepEqual(otherDifferences(d, p({ A: { type: 'plain_text', value: '1' } }, { destination_dir: 'out' })), ['the variable S is in the live build and no longer saved', 'the build setting destination_dir changed since the live build']);
  const args = checkArgs({ site: HOST, pages: `https://${LIVE}`, commit: 'a'.repeat(40), timeoutS: 9, only: ['build', 'nel'], nameservers: ['192.0.2.53', '192.0.2.54'] });
  assert.deepEqual(args.slice(1), [HOST, '--json', '--timeout', '9', '--project', `https://${LIVE}`, '--build', 'a'.repeat(40), '--only', 'build,nel', '--nameserver', '192.0.2.53,192.0.2.54']);
  assert.ok(!checkArgs({ site: 'http://127.0.0.1:1', pages: 'x', commit: 'a', timeoutS: 1, nameservers: null }).includes('--nameserver'));
  assert.ok(LAUNCH_SKIP_IDS.every((id) => !SKIP_IDS.includes(id)));
});

// ================================================================ every stage

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
    [{ zones: [zone(), zone({ id: 'c0ffee00000000000000000000000003', name: 'lenas-cafe.example' })], perPage: { zones: 1, projects: 10, deployments: 25 } }, /reaches 2 zones\. Make one limited to the site's own zone.*may need a few minutes/],
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

test('35: the project\'s address is the one Cloudflare gives, never one made from its name', () =>
  scenario(freshState({ subdomainFor: (n) => `${n}-9x2.pages.dev` }), async ({ go }) => {
    const r = await go(['--confirm', codeOf(await go())]);
    assert.match(r.out, /https:\/\/lenas-backstube-9x2\.pages\.dev\//);
    assert.doesNotMatch(r.out, /lenas-backstube\.pages\.dev/);
  }));

test('37: a single-stage site: production branch main, and no preview of main is named', () =>
  scenario(freshState(), async ({ api, go }) => {
    const r = await go();
    assert.equal(r.code, 3, r.out);
    assert.match(r.out, /single-stage: main is the live branch/);
    assert.match(r.out, /production branch main/);
    assert.doesNotMatch(r.out, /preview of main|main, the preview/);
    await go(['--confirm', codeOf(r)]);
    assert.equal(api.writes().find((e) => e.path.endsWith('/pages/projects')).body.production_branch, 'main');
  }, { prodBranch: 'main', production: false }));

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

test('39: a run cut off between two writes: the next run with the same code reads what is there and carries on', async (t) => {
  if (process.platform === 'win32') { t.skip('stopping the program mid-run uses a POSIX signal'); return; }
  await scenario(freshState(), async ({ api, where, dns, go, state }) => {
    const code = codeOf(await go());
    // Hold the answer to the first settings write, and kill the run while it waits.
    let release;
    const held = new Promise((r) => { release = r; });
    const child = spawn(process.execPath, [SCRIPT, 'setup', '--confirm', code], {
      cwd: where.site, env: { ...cleanEnv(), CLOUDFLARE_API_TOKEN: TOKEN, CLOUDFLARE_SETUP_API: api.origin, CLOUDFLARE_SETUP_RESOLVER: dns.address }, stdio: 'ignore',
    });
    state.after = (e) => { if (e.method === 'PATCH' && e.path.includes('/settings/')) { child.kill('SIGKILL'); release(); } };
    await held;
    await new Promise((r) => child.on('close', r));
    state.after = null;
    assert.equal(api.writes().filter((e) => e.path.endsWith('/pages/projects')).length, 1, 'the project was created before the cut');
    const r = await go(['--confirm', code]);
    assert.equal(r.code, 4, r.out);
    assert.equal(api.writes().filter((e) => e.path.endsWith('/pages/projects')).length, 1, 'no second create');
    assert.equal(api.writes().filter((e) => e.path.endsWith('/deployments')).length, 1, 'no second build: the first is queued');
    assert.deepEqual(state.settings, { always_use_https: 'on', min_tls_version: '1.2', email_obfuscation: 'off', nel: { enabled: false } });
  });
});

// The two tests that wait out the 55-second deadline run side by side.
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
    const r = await go();
    assert.equal(r.code, 3, r.out);
    assert.doesNotMatch(r.out, /Always Use HTTPS: On \(/, 'no setting line is asked');
    assert.match(r.out, /By hand: Always Use HTTPS: On\. The zone's records could not be read, so the hosts this setting changes cannot be named; the token needs the row Zone → DNS → Edit/);
    const done = await go(['--confirm', codeOf(r)]);
    assert.equal(done.code, 1, done.out);
    assert.ok(!api.writes().some((e) => e.path.includes('/settings/') || e.path.endsWith('/bot_management')), 'no zone-wide write');
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

test('what decides is read from the project itself: a list item without its domains still leaves a live project alone', () =>
  scenario(freshState({ projects: [project({ productionBranch: 'main', domains: [HOST] })], listItem: (p) => { delete p.domains; delete p.deployment_configs; return p; } }), async ({ api, go }) => {
    const r = await go();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /does not repair a live site/);
    assert.ok(api.log.some((e) => e.method === 'GET' && e.path === `/accounts/${ACCOUNT.id}/pages/projects/${REPO}`), 'the project was read');
    onlyReads(api);
  }));

test('the project read by its name must itself be connected to the repository, whatever the list said', () =>
  scenario(freshState({
    projects: [project({ source: { owner: OWNER, repo: 'lenas-cafe' } })],
    listItem: (p) => { p.source.config.repo_name = REPO; return p; }, // the list says connected; the project read says otherwise
  }), async ({ api, go }) => {
    const r = await go();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /The project lenas-backstube, read by its name, is not connected to lena-example\/lenas-backstube/);
    onlyReads(api);
  }));

test('a build of the head that ended in a way no trial saw counts as failed: no new build, and the run says so', () =>
  scenario((h) => {
    const s = finishedState(h);
    const d = deployment('built', { commit: h.production });
    d.latest_stage = { name: 'build', status: 'canceled', started_on: null, ended_on: null };
    s.deployments[REPO] = [deployment('push', { commit: h.main, branch: 'lenas-pr' }), d];
    return s;
  }, async ({ api, go }) => {
    const r = await go();
    assert.equal(r.code, 1, r.out);
    assert.match(r.out, /The newest production build of [0-9a-f]{7} failed: production, commit [0-9a-f]{7} \(build: canceled\)/);
    onlyReads(api);
  }));

test('a list longer than 200 pages is not read in part: the run stops', () =>
  scenario(freshState({ projects: Array.from({ length: 201 }, (_, i) => project({ name: `other-${i}`, source: { owner: 'someone', repo: `r${i}` } })), perPage: { zones: 50, projects: 1, deployments: 25 } }), async ({ api, go }) => {
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

test('R1: a yes to one build setting is not a yes to another', () =>
  scenario((h) => Object.assign(finishedState(h), { projects: [project({ build: { build_command: 'npm run old' } })] }), async ({ api, go, state }) => {
    const q = await go();
    assert.match(q.out, /Build settings: build command npm run old → npm run build\./);
    state.projects[0].build_config.destination_dir = 'public'; // changed by hand after the question
    const r = await go(['--confirm', codeOf(q)]);
    assert.equal(r.code, 3, r.out);
    assert.match(r.out, /does not fit this question/);
    onlyReads(api);
  }));

test('R1: the build the question named is of one commit: once the production branch moves, the code asks again', () =>
  scenario(freshState(), async ({ api, where, go, state }) => {
    const q = await go();
    assert.match(q.out, new RegExp(`Start one build of production \\(commit ${state.heads.production.slice(0, 7)}\\)`));
    writeFileSync(path.join(where.site, 'news.md'), 'new\n');
    git(where.site, 'add', 'news.md');
    git(where.site, 'commit', '-q', '-m', 'news');
    git(where.site, 'push', '-q', 'origin', 'HEAD:production');
    const r = await go(['--confirm', codeOf(q)]);
    assert.equal(r.code, 3, r.out);
    assert.match(r.out, /does not fit this question/);
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
    [['--skip', 'canonical'], {}, /belongs to the launch stage/],
    [['--skip', 'cdn'], {}, /--skip takes one of/],
    [['--confirm', 'yes'], {}, /16-character code/],
    [Array.from({ length: 6 }, (_, i) => ['--record', `TXT r${i} v`]).flat(), {}, /at most five --record/],
    [['--project', 'Lenas_Site'], {}, /not a Pages project name/],
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
    [['--skip', 'cdn'], {}, /--skip takes one of https, tls, email, nel, bot, ai, canonical, nel-rule/],
    [[], { CLOUDFLARE_SETUP_SITE: 'https://lenas-backstube.example' }, /literal loopback address/],
    [[], { CLOUDFLARE_SETUP_PAGES: 'http://stub.example.com:8080' }, /literal loopback address/],
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
