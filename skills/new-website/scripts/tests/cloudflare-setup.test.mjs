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
import { fileURLToPath } from 'node:url';
import { BOT_LINES, SETTINGS, SKIP_IDS, codeFits, defaultName, githubRepo, goodProductionBuild, looksSwapped, parseRecord, pushProof, setupCode, UsageError } from '../cloudflare-setup.mjs';
import { ACCOUNT, OWNER, REPO, TOKEN, ZONE, allFixtures, deployment, fixture, freshState, handle, project, servedBy, startApi, startDns, zone } from './cloudflare-stub.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = path.join(HERE, '..', 'cloudflare-setup.mjs');
const CHECKLIST = path.join(HERE, '..', '..', '..', '..', 'docs', 'CLOUDFLARE-CHECKLIST.md');
const REMOTE = `https://github.com/${OWNER}/${REPO}.git`;
const HOST = ZONE.name;

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
function makeSite({ prodBranch = 'production', production = true, url = `https://${HOST}`, ignoreDevVars = true, devVars = null, trackDevVars = false } = {}) {
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
  git(site, 'add', 'src', '.gitignore');
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

function run(where, args, { api, dns, env = {}, token = TOKEN } = {}) {
  const started = Date.now();
  return new Promise((resolve) => {
    const e = { ...cleanEnv(), ...(token ? { CLOUDFLARE_API_TOKEN: token } : {}), ...(api ? { CLOUDFLARE_SETUP_API: api.origin } : {}), ...(dns ? { CLOUDFLARE_SETUP_RESOLVER: dns.address } : {}), ...env };
    execFile(process.execPath, [SCRIPT, 'setup', ...args], { cwd: where.site, env: e, timeout: 75_000 }, (err, stdout, stderr) => {
      // R10: the token is never printed.
      assert.ok(!stdout.includes(TOKEN) && !stderr.includes(TOKEN), 'the token was printed');
      resolve({ code: err ? err.code : 0, out: stdout, err: stderr, ms: Date.now() - started });
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
  // A deployment records its variables, a secret with its value empty, and its build settings (T1-062).
  assert.deepEqual(fixture('T1-062').response.result.env_vars.SPIKE_SECRET, { type: 'secret_text', value: '' });
});

// ================================================================ the fixtures hold made-up values only

// Follow-up W5 of the plan's second gate: the fixtures come from real accounts, and check_clean.sh
// looks for listed names, emails and secrets, not ids. Every id, address, host name, commit hash,
// account name, repository, project and commit message in them must be one of the made-up ones. A
// made-up id is mostly zeros (fixtures/cloudflare-api/clean-captures.mjs), which no real one is.
const MADE_UP = {
  domains: ['lenas-backstube.example', 'lenas-cafe.example', 'lenas-backstube.pages.dev', 'lenas-backstube-2.pages.dev', 'lenas-old-site.pages.dev',
    'ada.ns.example', 'bert.ns.example', 'cleo.ns.example', 'dora.ns.example', ...[1, 2, 3, 4, 5, 6].map((n) => `other-${n}.example`)],
  publicHosts: ['api.cloudflare.com', 'developers.cloudflare.com', 'github.com', 'verify.bing.com', 'example.com'],
  accounts: ["Lena's Account", "Lena's Second Account"],
  owners: [OWNER],
  repos: [REPO, 'lenas-old-site'],
  projects: [REPO, 'lenas-backstube-2', 'lenas-old'],
  hex32: /^c0ffee0{16}\d{10}$/,
  hex40: /^ba5e0{26}\d{10}$/,
  uuid: /^d\d{7}-0000-4000-8000-000000000000$/,
  short: /^d\d{7}$/,
  number: /^100000\d$/,
  commitMessage: /^Made-up commit message \d+$/,
  // Every other string with a space or a capital letter in it, keys included: Cloudflare's words,
  // the trials' own labels, and the cleaner's notes. A sentence the private map missed fails.
  freeText: new Set([
    "Lena's Account", "Lena's Second Account", 'Free Website', 'USD', 'GET', 'PATCH', 'POST', 'PUT', 'CNAME', 'TXT', 'npm run build',
    'This API Token is valid and active', 'Authentication error', 'Bad Request', 'An identical record already exists.',
    'An A, AAAA, or CNAME record with that host already exists. For more details, refer to <https://developers.cloudflare.com/dns/manage-dns-records/troubleshooting/records-with-same-name/>.',
    'You must set the `fail_open` property value equally for production and preview environments.',
    'cf_robots_variant cannot be set to policy_only with is_robots_txt_managed set to true',
    'could not find entrypoint ruleset in the http_response_headers_transform phase',
    'Remove NEL headers', 'Trial: a second rule', 'Trial of a setup script; remove when the trial ends',
    'multipart/form-data; boundary=----spike', '------spike--\r\n', '@SECRET@',
    'CANONICAL_URL', 'NEL', 'Report-To', 'SPIKE_PLAIN', 'SPIKE_SECRET', 'contentType', 'emptyForm',
  ]),
  freeTextPattern: /^every ad_hoc deployment \(\d+ uploads, with clone_repo and build idle, and \d+ built by Cloudflare\) and the newest push build of each environment, of \d+ deployments on the six pages T1-021 to T1-026$/,
};
test('every id, address, host, account, repository, project and commit message in the fixtures is a made-up one', () => {
  const bad = [];
  const fixtures = allFixtures();
  assert.ok(fixtures.length > 50, 'the fixtures are there');
  const check = (where, key, v) => {
    if (typeof v !== 'string') return;
    const no = (what) => bad.push(`${where} ${key}: ${what} "${v.slice(0, 60)}"`);
    for (const m of v.matchAll(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi)) if (!MADE_UP.uuid.test(m[0])) no('an id');
    const noUuid = v.replace(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi, '');
    for (const m of noUuid.matchAll(/\b[0-9a-f]{40}\b/gi)) if (!MADE_UP.hex40.test(m[0])) no('a commit hash');
    for (const m of noUuid.matchAll(/\b[0-9a-f]{32}\b/gi)) if (!MADE_UP.hex32.test(m[0])) no('an id');
    for (const m of v.matchAll(/\b\d{1,3}(?:\.\d{1,3}){3}\b/g)) if (!/^192\.0\.2\./.test(m[0])) no('an IP address');
    for (const m of v.matchAll(/(?:^|[^0-9a-f:])((?:[0-9a-f]{1,4}:){3,7}[0-9a-f]{1,4})(?![0-9a-f:])/gi)) if (!/^2001:db8:/i.test(m[1]) && !/^\d{2}:\d{2}:\d{2}$/.test(m[1])) no('an IPv6 address');
    if (/[^\s@"]+@[^\s@"]+\.[a-z]{2,}/i.test(v)) no('an email address');
    for (const m of v.matchAll(/(?:[a-z0-9-]+\.)+[a-z][a-z0-9-]*[a-z]/gi)) {
      const h = m[0].toLowerCase();
      if (MADE_UP.publicHosts.includes(h)) continue;
      if (!MADE_UP.domains.some((d) => h === d || h.endsWith(`.${d}`))) no('a host');
      const first = h.split('.')[0];
      if (/^[0-9a-f]{8}$/.test(first) && !MADE_UP.short.test(first)) no('a deployment id in a host');
    }
    if (key === 'short_id' && !MADE_UP.short.test(v)) no('a deployment id');
    if ((key === 'owner_id' || key === 'repo_id') && !MADE_UP.number.test(v)) no('a GitHub id');
    if (key === 'commit_message' && !MADE_UP.commitMessage.test(v)) no('a commit message');
    if (key === 'owner' && !MADE_UP.owners.includes(v)) no('a GitHub owner');
    if (key === 'repo_name' && !MADE_UP.repos.includes(v)) no('a repository');
    if (key === 'project_name' && !MADE_UP.projects.includes(v)) no('a project');
    const freeText = /\s|[A-Z]/.test(v) && !/^\d{4}-\d{2}-\d{2}T[\d:.]+Z$/.test(v) && !MADE_UP.commitMessage.test(v) && !/^T[12]-\d{3}$/.test(v);
    if (freeText && !MADE_UP.freeText.has(v) && !MADE_UP.freeTextPattern.test(v)) no('free text not on the list');
  };
  const walk = (where, o, key = '') => {
    if (Array.isArray(o)) { o.forEach((x) => walk(where, x, key)); return; }
    if (o && typeof o === 'object') {
      for (const [k, v] of Object.entries(o)) {
        check(where, 'a key', k);
        if (k === 'name' && key === 'account' && !MADE_UP.accounts.includes(v)) bad.push(`${where}: an account name "${v}"`);
        walk(where, v, k);
      }
      return;
    }
    check(where, key, o);
  };
  for (const { file, ...f } of fixtures) {
    walk(file, f);
    for (const p of [f.response?.result].flat()) {
      if (p && typeof p === 'object' && 'subdomain' in p && !MADE_UP.projects.includes(p.name)) bad.push(`${file}: a project "${p.name}"`);
    }
  }
  assert.deepEqual(bad, []);
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
  const blocked = () => Object.assign(freshState().bot, { fight_mode: true, enable_js: true, cf_robots_variant: 'off', ai_training: 'block', bot_preference_sync_enabled: true, crawler_protection: 'enabled' });
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
    if (over.perPage) s.perPage = over.perPage;
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
    state.delayMs = 0;
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

  test('a git that never ends, with a program of its own holding the output open: stopped at the deadline, said as git, before 60 seconds', async (t) => {
    if (process.platform === 'win32') { t.skip('the stand-in git is a shell script'); return; }
    const bin = path.join(scratch, 'bin-hang');
    mkdirSync(bin, { recursive: true });
    const realGit = execFileSync('sh', ['-c', 'command -v git'], { encoding: 'utf8' }).trim();
    // ls-remote starts a child that keeps stdout open, as ssh would, and waits.
    writeFileSync(path.join(bin, 'git'), `#!/bin/sh\nfor a in "$@"; do [ "$a" = ls-remote ] && { sleep 300 & wait; }; done\nexec "${realGit}" "$@"\n`);
    chmodSync(path.join(bin, 'git'), 0o755);
    await scenario((h) => finishedState(h), async ({ api, go }) => {
      const r = await go([], { env: { PATH: `${bin}${path.delimiter}${process.env.PATH}` } });
      assert.equal(r.code, 1, r.out);
      assert.match(r.out, /git did not finish reading the branches/);
      assert.ok(r.ms < 60_000, `took ${r.ms} ms`);
      onlyReads(api);
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
    assert.match(r.out, /By hand: Always Use HTTPS: On\. the zone's records could not be read, so the hosts this setting changes cannot be named; the token needs the row Zone → DNS → Edit/);
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

test('a wrong command is status 2; launch is not in this version; the overrides take loopback addresses only', async () => {
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
  const launch = await new Promise((resolve) => execFile(process.execPath, [SCRIPT, 'launch'], { cwd: where.site, env: cleanEnv() }, (err, stdout, stderr) => resolve({ code: err ? err.code : 0, stderr })));
  assert.equal(launch.code, 2);
  assert.match(launch.stderr, /launch stage is not in this version/);
});

test('the overrides are said out loud while they are in effect', () =>
  scenario((h) => finishedState(h), async ({ go }) => {
    const r = await go();
    assert.match(r.out, /^Test mode: Cloudflare's API is replaced by http:\/\/127\.0\.0\.1:\d+\.$/m);
    assert.match(r.out, /^Test mode: the zone's nameservers are replaced by 127\.0\.0\.1:\d+\.$/m);
  }));
