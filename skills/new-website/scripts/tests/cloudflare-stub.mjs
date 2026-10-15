// A stand-in for Cloudflare's API, for the tests of cloudflare-setup.mjs, and a stand-in for a zone's
// nameservers. Standard library only.
//
// Every answer is built from a fixture in fixtures/cloudflare-api/: the cleaned captures of the two
// trials (docs/reviews/SKILL-PLAN-cloudflare-setup.md, "What is known, and how"), cited by their
// capture number. The stub copies a captured answer and puts its own state in it: the project it
// holds, the settings it holds. Where the trials have no capture (a failed build, a refused token,
// a slow answer, an unknown path), the answer is made from Cloudflare's API
// reference, and the code says so with MADE. The test file replays the captured requests against
// this stub and compares its answers with the captured ones, so the stub cannot drift from them.
import http from 'node:http';
import dgram from 'node:dgram';
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const FIXTURES = path.join(HERE, 'fixtures', 'cloudflare-api');
const files = readdirSync(FIXTURES).filter((f) => f.endsWith('.json') && f !== 'allowed-values.json'); // every capture, of any trial
// fixture('T1-048') is the cleaned capture T1-048, as written by fixtures/cloudflare-api/clean-captures.mjs.
export function fixture(capture) {
  const f = files.find((x) => x.startsWith(`${capture}-`));
  if (!f) throw new Error(`no fixture ${capture}`);
  return JSON.parse(readFileSync(path.join(FIXTURES, f), 'utf8'));
}
// Each fixture file with its name beside it, never merged into it: a check walks `data` whole.
export const allFixtures = () => files.map((f) => ({ file: f, data: JSON.parse(readFileSync(path.join(FIXTURES, f), 'utf8')) }));
const copy = (o) => JSON.parse(JSON.stringify(o));
const answer = (capture) => copy(fixture(capture).response);

// The made-up values of the scenarios: the bakery's account, zone and repository.
export const TOKEN = 'lena-made-up-test-token-not-a-real-one-0000';
export const ACCOUNT = { id: 'c0ffee00000000000000000000000001', name: "Lena's Account" };
export const ZONE = { id: 'c0ffee00000000000000000000000002', name: 'lenas-backstube.example' };
export const OWNER = 'lena-example';
export const REPO = 'lenas-backstube';

let serial = 0;
const newUuid = () => `e${String(++serial).padStart(7, '0')}-0000-4000-8000-000000000000`;
const newId = () => `e0ffee${String(++serial).padStart(26, '0')}`;

// ---------------------------------------------------------------- the things the stub holds

export function zone(over = {}) {
  const z = copy(fixture('T1-002').response.result[0]);
  return Object.assign(z, { id: ZONE.id, name: ZONE.name, status: 'active', account: { ...ACCOUNT } }, over);
}

// A project as Cloudflare returns it (T1-027), connected to the bakery's repository unless `source`
// says otherwise (null: a Direct Upload project, which has none).
export function project({ name = REPO, productionBranch = 'production', failOpen = true, envVars = null, previewVars = null,
  domains = [], subdomain = `${name}.pages.dev`, source, preview = 'all', build = {} } = {}) {
  const p = copy(fixture('T1-027').response.result);
  p.id = newUuid();
  p.name = name;
  p.subdomain = subdomain;
  p.domains = [subdomain, ...domains];
  p.production_branch = productionBranch;
  if (source === null) delete p.source;
  else {
    p.source.config.owner = source?.owner ?? OWNER;
    p.source.config.repo_name = source?.repo ?? REPO;
    p.source.config.production_branch = productionBranch;
    p.source.config.preview_deployment_setting = preview;
  }
  Object.assign(p.build_config, build);
  p.deployment_configs.production.fail_open = failOpen;
  p.deployment_configs.preview.fail_open = failOpen;
  p.deployment_configs.production.env_vars = envVars;
  p.deployment_configs.preview.env_vars = previewVars;
  return p;
}

// Deployments, each a captured one with the bakery's names put in. `kind`:
//   built     production, built by Cloudflare from the deployment call, succeeded   (T1-040, second)
//   upload    production, uploaded: clone_repo and build idle                       (T1-021, an upload)
//   push      a preview Cloudflare built from a push to a pull request             (T1-040, first)
//   push-prod production, built from a push to the production branch               (T2-029, first)
//   skipped   a push Cloudflare skipped: previews are off                           (T2-026)
//   queued    the deployment call's answer: queued, nothing run                     (T1-030)
//   building  production, built from a push, in its build stage                     (T2-028, first)
//   failed    MADE: a push build whose build stage failed (no trial saw one; the stage's status
//             "failure" is from Cloudflare's API reference)
export function deployment(kind, { commit, branch, env, productionBranch = 'production', name = REPO } = {}) {
  const pick = {
    built: () => fixture('T1-040').response.result[1],
    upload: () => fixture('T1-021').response.result.find((d) => d.environment === 'production' && d.deployment_trigger.type === 'ad_hoc' && d.stages.find((s) => s.name === 'build').status === 'idle'),
    push: () => fixture('T1-040').response.result[0],
    'push-prod': () => fixture('T2-029').response.result[0],
    skipped: () => fixture('T2-026').response.result[0],
    queued: () => fixture('T1-030').response.result,
    building: () => fixture('T2-028').response.result[0],
    failed: () => {
      const d = fixture('T1-040').response.result[0];
      d.stages.find((s) => s.name === 'build').status = 'failure';
      d.stages.find((s) => s.name === 'deploy').status = 'idle';
      d.latest_stage = { ...d.stages.find((s) => s.name === 'build') };
      return d;
    },
  }[kind];
  if (!pick) throw new Error(`no deployment kind ${kind}`);
  const d = copy(pick());
  d.id = newUuid();
  d.short_id = d.id.slice(0, 8);
  d.project_name = name;
  d.url = `https://${d.short_id}.${name}.pages.dev`;
  d.production_branch = productionBranch;
  if (env) d.environment = env;
  const meta = d.deployment_trigger.metadata;
  if (commit) meta.commit_hash = commit;
  if (branch) meta.branch = branch;
  else if (d.environment === 'production') meta.branch = productionBranch;
  if (d.aliases) d.aliases = [`https://${meta.branch.replace(/\//g, '-')}.${name}.pages.dev`];
  return d;
}

// A Cloudflare build that is over, from the deployment call (T1-040's second, which T1-030 became).
function finish(d, outcome) {
  for (const s of d.stages) s.status = outcome === 'success' || s.name === 'queued' || s.name === 'initialize' || s.name === 'clone_repo' ? 'success' : s.name === 'build' ? 'failure' : 'idle';
  d.latest_stage = { ...(outcome === 'success' ? d.stages.find((s) => s.name === 'deploy') : d.stages.find((s) => s.name === 'build')) };
}

// The starting point of most scenarios: a zone with Cloudflare's defaults for a new one (T2-036 to
// T2-039: HTTPS off, TLS 1.0, obfuscation on, NEL on) and Bot Management as the spare zone read
// (T2-040: everything allowed, Bot Preference Sync on), no records, no project.
export function freshState(over = {}) {
  return {
    token: { status: 'active', expires_on: new Date(Date.now() + 2 * 86_400_000).toISOString().replace(/\.\d+Z$/, 'Z') },
    zones: [zone()],
    settings: Object.fromEntries(['036', '037', '038', '039'].map((n) => {
      const r = fixture(`T2-${n}`).response.result;
      return [r.id, r.value];
    })),
    bot: copy(fixture('T2-040').response.result),
    dns: [],
    projects: [],
    deployments: {},
    heads: {}, // branch → commit: what the deployment call builds
    domains: {}, // project → the custom domains attached to it, with their status
    ruleset: null, // the zone's ruleset for the response header phase, or none
    refuse: {}, // "<METHOD> <route>" → status
    delayMs: 0,
    perPage: { zones: 50, projects: 10, deployments: 25 },
    ...over,
  };
}

// ---------------------------------------------------------------- the API

const ROUTES = [
  ['GET', /^\/user\/tokens\/verify$/, 'verify'],
  ['GET', /^\/zones$/, 'zones'],
  ['GET', /^\/zones\/([^/]+)\/settings\/([a-z_]+)$/, 'setting'],
  ['PATCH', /^\/zones\/([^/]+)\/settings\/([a-z_]+)$/, 'setting'],
  ['GET', /^\/zones\/([^/]+)\/bot_management$/, 'bot'],
  ['PUT', /^\/zones\/([^/]+)\/bot_management$/, 'bot'],
  ['GET', /^\/zones\/([^/]+)\/dns_records$/, 'dns'],
  ['POST', /^\/zones\/([^/]+)\/dns_records$/, 'dns'],
  ['GET', /^\/zones\/([^/]+)\/dns_records\/([^/]+)$/, 'record'],
  ['PATCH', /^\/zones\/([^/]+)\/dns_records\/([^/]+)$/, 'record'],
  ['GET', /^\/zones\/([^/]+)\/rulesets\/phases\/http_response_headers_transform\/entrypoint$/, 'phase'],
  ['PUT', /^\/zones\/([^/]+)\/rulesets\/phases\/http_response_headers_transform\/entrypoint$/, 'phase'],
  ['POST', /^\/zones\/([^/]+)\/rulesets\/([^/]+)\/rules$/, 'rules'],
  ['GET', /^\/accounts\/([^/]+)\/pages\/projects\/([^/]+)\/domains\/([^/]+)$/, 'domain'],
  ['POST', /^\/accounts\/([^/]+)\/pages\/projects\/([^/]+)\/domains$/, 'domains'],
  ['GET', /^\/accounts\/([^/]+)\/pages\/projects$/, 'projects'],
  ['POST', /^\/accounts\/([^/]+)\/pages\/projects$/, 'projects'],
  ['GET', /^\/accounts\/([^/]+)\/pages\/projects\/([^/]+)$/, 'project'],
  ['PATCH', /^\/accounts\/([^/]+)\/pages\/projects\/([^/]+)$/, 'project'],
  ['GET', /^\/accounts\/([^/]+)\/pages\/projects\/([^/]+)\/deployments$/, 'deployments'],
  ['POST', /^\/accounts\/([^/]+)\/pages\/projects\/([^/]+)\/deployments$/, 'deployments'],
  ['GET', /^\/accounts\/([^/]+)\/pages\/projects\/([^/]+)\/deployments\/([^/]+)$/, 'deployment'],
];

// A refusal as Cloudflare words it: 403, code 10000 (T1-014), whatever the row was.
const refused = () => ({ status: 403, body: answer('T1-014') });
// MADE: a 404 for a path the stub does not know, and for a project or record it does not hold.
const notFound = (what) => ({ status: 404, body: { success: false, errors: [{ code: 8000007, message: `${what} not found` }], messages: [], result: null } });
const listOf = (items, page, perPage, template) => {
  const body = template;
  const pages = Math.max(1, Math.ceil(items.length / perPage));
  body.result = items.slice((page - 1) * perPage, page * perPage);
  body.result_info = { page, per_page: perPage, count: body.result.length, total_count: items.length, total_pages: pages };
  return { status: 200, body };
};
const secretBlank = (vars) => (vars ? Object.fromEntries(Object.entries(vars).map(([k, v]) => [k, v.type === 'secret_text' ? { type: v.type, value: '' } : { ...v }])) : vars);

export function handle(state, method, p, query, body, contentType) {
  const route = ROUTES.find(([m, re]) => m === method && re.test(p));
  if (!route) return notFound(`${method} ${p}`);
  const [, re, name] = route;
  const args = re.exec(p).slice(1);
  const key = `${method} ${name}${name === 'setting' ? `:${args[1]}` : ''}`;
  if (state.refuse[key]) return state.refuse[key] === 403 ? refused() : { status: state.refuse[key], body: { success: false, errors: [{ code: 10000, message: 'MADE: refused by the test' }], messages: [] } };
  const page = Number(query.get('page') ?? 1);

  switch (key.split(':')[0]) {
    case 'GET verify': {
      // With an end date (T1-003) or without one (T1-001), which omits expires_on.
      const b = answer(state.token.expires_on ? 'T1-003' : 'T1-001');
      b.result.status = state.token.status;
      if (state.token.expires_on) b.result.expires_on = state.token.expires_on;
      return { status: 200, body: b };
    }
    case 'GET zones': // a page holds what was asked for, at most state.perPage.zones
      return listOf(state.zones, page, Math.min(Number(query.get('per_page') ?? 50), state.perPage.zones), answer('T1-002'));
    case 'GET setting': {
      const b = answer('T1-067');
      if (!(args[1] in state.settings)) return notFound(args[1]);
      b.result = { id: args[1], value: copy(state.settings[args[1]]), editable: true };
      return { status: 200, body: b };
    }
    case 'PATCH setting': { // a PATCH of {"value": …}, answered with the setting (T1-071 to T1-077)
      state.settings[args[1]] = copy(body.value);
      const b = answer('T1-071');
      b.result = { id: args[1], value: copy(body.value), editable: true };
      return { status: 200, body: b };
    }
    case 'GET bot': {
      const b = answer('T2-040');
      b.result = copy(state.bot);
      return { status: 200, body: b };
    }
    case 'PUT bot': {
      // is_robots_txt_managed true with cf_robots_variant policy_only is refused (T2-059, T2-065), as
      // Cloudflare's message says; a field left out keeps its value (T2-061, T2-062); the answer is
      // the whole object (T2-061).
      const variant = body.cf_robots_variant ?? state.bot.cf_robots_variant;
      if (body.is_robots_txt_managed === true && variant === 'policy_only') return { status: 400, body: answer('T2-065') };
      Object.assign(state.bot, copy(body));
      const b = answer('T2-061');
      b.result = copy(state.bot);
      return { status: 200, body: b };
    }
    case 'GET dns':
      return listOf(state.dns, page, Number(query.get('per_page') ?? 100), answer('T2-035'));
    case 'POST dns': {
      if ((body.comment ?? '').length > 100) return { status: 400, body: answer('T2-058') };
      const name = body.name === '@' ? ZONE.name : body.name.endsWith(ZONE.name) ? body.name : `${body.name}.${ZONE.name}`;
      if (state.dns.some((r) => r.name === name && r.type === body.type && r.content === body.content)) return { status: 400, body: answer('T1-145') };
      const address = ['A', 'AAAA', 'CNAME'];
      if (address.includes(body.type) && state.dns.some((r) => r.name === name && address.includes(r.type))) return { status: 400, body: answer('T1-146') };
      const b = answer('T1-143');
      b.result = { ...b.result, id: newId(), type: body.type, name, content: body.content, proxied: body.proxied ?? false, ttl: body.ttl ?? 1, comment: body.comment ?? null };
      state.dns.push(copy(b.result));
      return { status: 200, body: b };
    }
    case 'GET record': {
      const r = state.dns.find((x) => x.id === args[1]);
      if (!r) return notFound('record');
      const b = answer('T1-143');
      b.result = copy(r);
      return { status: 200, body: b };
    }
    case 'PATCH record': {
      // One PATCH changes a record and keeps its id (T1-132, T2-046); a comment over 100 characters is
      // refused, 9313 (T2-058). Changing the type is accepted with a message that it is deprecated.
      const r = state.dns.find((x) => x.id === args[1]);
      if (!r) return notFound('record');
      if ((body.comment ?? '').length > 100) return { status: 400, body: answer('T2-058') };
      const b = answer('T2-046');
      if (!('type' in body) || body.type === r.type) b.messages = [];
      Object.assign(r, copy(body));
      b.result = { ...b.result, ...copy(r) };
      return { status: 200, body: b };
    }
    case 'GET phase': // none: 404, code 10003 (T2-018); else the ruleset (T2-025)
      if (!state.ruleset) return { status: 404, body: answer('T2-018') };
      return { status: 200, body: Object.assign(answer('T2-025'), { result: copy(state.ruleset) }) };
    case 'PUT phase': { // the whole ruleset, as sent, each rule given an id (T2-023)
      const b = answer('T2-023');
      state.ruleset = { ...b.result, id: newId(), version: '1', rules: body.rules.map((x) => ({ ...copy(x), id: newId(), version: '1' })) };
      b.result = copy(state.ruleset);
      return { status: 200, body: b };
    }
    case 'POST rules': { // one rule appended; the rules there keep their ids and versions (T2-024)
      if (!state.ruleset || state.ruleset.id !== args[1]) return notFound('ruleset');
      state.ruleset.rules.push({ ...copy(body), id: newId(), version: '1' });
      state.ruleset.version = String(Number(state.ruleset.version) + 1);
      return { status: 200, body: Object.assign(answer('T2-024'), { result: copy(state.ruleset) }) };
    }
    case 'POST domains': {
      // Attaching creates no record: the answer says initializing (T1-085), the next read pending
      // with "CNAME record not set" (T1-086). The test turns it active, as a record would.
      const p = state.projects.find((x) => x.name === args[1]);
      if (!p) return notFound('project');
      const b = answer('T1-085');
      b.result = { ...b.result, id: newUuid(), domain_id: undefined, name: body.name, zone_tag: ZONE.id };
      b.result.domain_id = b.result.id;
      if ((state.domains[p.name] ?? []).some((d) => d.name === body.name)) return { status: 409, body: { success: false, errors: [{ code: 8000018, message: 'MADE: the domain is already attached' }], messages: [] } };
      (state.domains[p.name] ??= []).push({ ...copy(b.result), status: 'pending', verification_data: copy(answer('T1-086').result.verification_data), validation_data: copy(answer('T1-086').result.validation_data) });
      // Whether the project's list names a pending domain was not captured (plan, Not verified 12):
      // `state.pendingUnlisted` plays the case where it does not.
      if (!state.pendingUnlisted) p.domains.push(body.name);
      return { status: 200, body: b };
    }
    case 'GET domain': {
      // MADE: a domain not attached answers 404 (no trial asked for one; Cloudflare's reference).
      const d = (state.domains[args[1]] ?? []).find((x) => x.name === args[2]);
      if (!d) return notFound('domain');
      const b = answer(d.status === 'active' ? 'T1-127' : 'T1-086');
      b.result = { ...b.result, ...copy(d) };
      if (d.status === 'active') b.result.verification_data = { status: 'active' };
      return { status: 200, body: b };
    }
    case 'GET projects':
      // The account's list (T1-019): whole projects, ten to a page. With `state.listItem`, each item
      // is cut down, to show the script decides from the project it reads by name.
      return listOf(state.projects.map((x) => (state.listItem ? state.listItem(copy(x)) : copy(x))), page, state.perPage.projects, answer('T1-019'));
    case 'POST projects': {
      // The project as created (T1-027): Cloudflare fills in the ids and the defaults.
      const p = project({ name: body.name, productionBranch: body.production_branch, failOpen: body.deployment_configs?.production?.fail_open ?? false,
        subdomain: state.subdomainFor?.(body.name) ?? `${body.name}.pages.dev`, source: body.source ? { owner: body.source.config.owner, repo: body.source.config.repo_name } : null,
        preview: body.source?.config?.preview_deployment_setting ?? 'all' });
      p.build_config = { ...p.build_config, ...body.build_config };
      p.deployment_configs.preview.fail_open = body.deployment_configs?.preview?.fail_open ?? false;
      state.projects.push(p);
      state.deployments[p.name] = [];
      const b = answer('T1-027');
      b.result = copy(p);
      if (state.thinCreateAnswer) b.result.build_config = {}; // MADE: an answer thinner than any captured one
      return { status: 200, body: b };
    }
    case 'GET project': {
      const p = state.projects.find((x) => x.name === args[1]);
      if (!p) return notFound('project');
      const b = answer('T1-054');
      b.result = state.projectRead ? state.projectRead(copy(p)) : copy(p); // MADE when cut down by a test
      return { status: 200, body: b };
    }
    case 'PATCH project': {
      const p = state.projects.find((x) => x.name === args[1]);
      if (!p) return notFound('project');
      return patchProject(state, p, body);
    }
    case 'GET deployments': {
      const list = state.deployments[args[1]] ?? [];
      return listOf(list.map(copy), page, state.perPage.deployments, answer('T1-040'));
    }
    case 'POST deployments': {
      // An empty form builds the head of the production branch, as production, ad_hoc (T1-030, whose
      // request is that empty form); a second call while one is queued starts a second build (T1-031).
      // MADE: anything but an empty form is refused here, since no trial sent another.
      const p = state.projects.find((x) => x.name === args[1]);
      if (!p) return notFound('project');
      const boundary = /boundary=(\S+)/.exec(contentType ?? '')?.[1];
      if (!boundary || body !== `--${boundary}--\r\n`) return { status: 400, body: { success: false, errors: [{ code: 8000000, message: 'MADE: the stub takes only an empty form' }], messages: [] } };
      const d = deployment('queued', { commit: state.heads[p.production_branch], productionBranch: p.production_branch, name: p.name });
      d.env_vars = secretBlank(p.deployment_configs.production.env_vars);
      d.build_config = { ...d.build_config, ...p.build_config };
      state.deployments[p.name].unshift(d);
      const b = answer('T1-030');
      b.result = copy(d);
      return { status: 200, body: b };
    }
    case 'GET deployment': {
      const d = (state.deployments[args[1]] ?? []).find((x) => x.id === args[2]);
      if (!d) return notFound('deployment');
      const b = answer('T1-030');
      b.result = copy(d);
      return { status: 200, body: b };
    }
    default:
      return notFound(key);
  }
}

// A PATCH keeps what it does not name (T1-048 to T1-061): variables and secrets by name, the build
// settings, Fail open. Fail open for one environment alone is refused, 8000066 (T1-050). The
// production branch is also the source's (T1-052). A secret reads back empty (T1-048).
function patchProject(state, p, body) {
  const dc = body.deployment_configs ?? {};
  const fo = ['production', 'preview'].map((e) => Boolean(dc[e] && 'fail_open' in dc[e]));
  if (fo[0] !== fo[1]) return { status: 400, body: answer('T1-050') };
  if ('production_branch' in body) {
    p.production_branch = body.production_branch;
    if (p.source) p.source.config.production_branch = body.production_branch;
  }
  if (body.build_config) Object.assign(p.build_config, body.build_config);
  for (const env of ['production', 'preview']) {
    const c = dc[env];
    if (!c) continue;
    if ('fail_open' in c) p.deployment_configs[env].fail_open = c.fail_open;
    if (c.env_vars) {
      p.deployment_configs[env].env_vars ??= {};
      for (const [k, v] of Object.entries(c.env_vars)) p.deployment_configs[env].env_vars[k] = secretBlank({ [k]: v })[k];
    }
  }
  const b = answer('T1-048');
  b.result = copy(p);
  for (const k of state.loseOnPatch ?? []) delete b.result.deployment_configs.production.env_vars?.[k];
  if (state.thinPatchAnswer) b.result.source.config = {}; // MADE: an answer thinner than any captured one
  if (state.previewInPatchAnswer) b.result.source.config.preview_deployment_setting = state.previewInPatchAnswer; // MADE: another value
  return { status: 200, body: b };
}

// The stub as a server on 127.0.0.1. Every request is logged with its method, path, body and
// whether it carried the token. `state.hold` may name a route ("<METHOD> <route>") whose answer
// waits until released, so a test can stop the script between two writes.
export async function startApi(state) {
  const log = [];
  const server = http.createServer((req, res) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', async () => {
      const url = new URL(req.url, 'http://stub');
      const p = url.pathname.replace(/^\/client\/v4/, '');
      const text = Buffer.concat(chunks).toString('utf8');
      let body = null;
      if (/json/.test(req.headers['content-type'] ?? '')) { try { body = JSON.parse(text); } catch { body = text; } } else if (text) body = text;
      const entry = { method: req.method, path: p, query: url.search, body, token: req.headers.authorization === `Bearer ${TOKEN}`, contentType: req.headers['content-type'] ?? '' };
      log.push(entry);
      if (state.delayMs) await new Promise((r) => setTimeout(r, state.delayMs).unref());
      let out;
      if (req.headers.authorization !== `Bearer ${TOKEN}`) out = { status: 401, body: answer('T1-014') };
      else out = handle(state, req.method, p, url.searchParams, body, req.headers['content-type']);
      entry.status = out.status;
      if (state.after) state.after(entry);
      res.writeHead(out.status, { 'content-type': 'application/json' });
      res.end(JSON.stringify(out.body));
    });
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const { port } = server.address();
  return {
    origin: `http://127.0.0.1:${port}`,
    state,
    log,
    writes: () => log.filter((e) => e.method !== 'GET'),
    finish: (name, outcome = 'success') => { const d = state.deployments[name].find((x) => x.latest_stage.status !== 'success' && !x.is_skipped); finish(d, outcome); return d; },
    close: () => { server.closeAllConnections?.(); return new Promise((r) => server.close(r)); },
  };
}

// A custom domain as Cloudflare holds it once attached (T1-085 to T1-127): `status` is pending,
// active, or, MADE from Cloudflare's reference, error, blocked or deactivated.
export function attachedDomain(name, status = 'active') {
  const d = copy(fixture(status === 'active' ? 'T1-127' : 'T1-086').response.result);
  return Object.assign(d, { id: newUuid(), name, zone_tag: ZONE.id, status },
    ['error', 'blocked', 'deactivated'].includes(status) ? { verification_data: { status, error_message: 'MADE: the reason Cloudflare gives' } } : {});
}

// ---------------------------------------------------------------- the domain and pages.dev, played

// Two small sites on 127.0.0.1 that answer as the stub API's state says, the way Cloudflare would
// serve the project: the domain serves the newest production build that succeeded (its build.txt),
// sends the NEL headers while `state.siteSendsNel` holds and no rule removes them, redirects http://
// while Always Use HTTPS is on, and sets Bot Fight Mode's cookie while it is on. The pages.dev address
// forwards every page, path and query, as functions/_middleware.ts does, once the live build has
// CANONICAL_URL (unless `state.pagesStays200`). Each records the requests it gets.
export async function startSites(state, project = REPO) {
  const asked = { site: [], pages: [] };
  const liveBuild = () => (state.deployments[project] ?? []).find((d) => d.environment === 'production' && d.latest_stage?.name === 'deploy' && d.latest_stage.status === 'success');
  const ruleRemovesNel = () => state.ruleset?.rules?.some((r) => r.enabled !== false && r.action_parameters?.headers?.NEL?.operation === 'remove');
  let siteHost;
  const site = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://x');
    asked.site.push(`${url.pathname}`);
    const headers = { server: 'cloudflare', 'cf-ray': '8a1b2c3d4e5f6071-AMS' };
    if (state.siteSendsNel && !ruleRemovesNel()) Object.assign(headers, { nel: '{"report_to":"cf-nel","max_age":604800}', 'report-to': '{"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4"}]}' });
    if (state.bot.fight_mode) headers['set-cookie'] = '__cf_bm=made-up; path=/';
    if (state.siteDown) { req.socket.destroy(); return; } // MADE: the edge does not answer yet
    // The check's http:// probe is "/" with no cache-buster (cloudflare-check.mjs, observe): only
    // that request gets Always Use HTTPS's redirect here.
    if (url.pathname === '/' && !url.searchParams.has('cb')) {
      if (state.settings.always_use_https === 'on') { res.writeHead(301, { ...headers, location: `https://${siteHost}/` }); res.end(); return; }
    }
    if (url.pathname === '/build.txt') {
      if (state.siteServes === null) { res.writeHead(404, headers); res.end(); return; }
      res.writeHead(200, { ...headers, 'content-type': 'text/plain' });
      res.end(`${state.siteServes ?? liveBuild()?.deployment_trigger?.metadata?.commit_hash ?? 'dev'}
`);
      return;
    }
    if (url.pathname === '/robots.txt') {
      res.writeHead(200, { ...headers, 'content-type': 'text/plain' });
      res.end(`User-agent: *
Allow: /

Sitemap: https://${siteHost}/sitemap-index.xml
`);
      return;
    }
    res.writeHead(200, { ...headers, 'content-type': 'text/html; charset=utf-8' });
    res.end(`<!doctype html><title>Lenas Backstube</title><p>${state.settings.email_obfuscation === 'on' ? '<a href="/cdn-cgi/l/email-protection" data-cfemail="00">mail</a>' : 'Brot'}</p>`);
  });
  const pages = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://x');
    asked.pages.push(`${url.pathname}${url.search}`);
    const saved = liveBuild()?.env_vars?.CANONICAL_URL?.value;
    if (state.pagesProbeSilent && url.pathname !== '/') { req.socket.destroy(); return; }
    if (state.pagesRedirect302) { res.writeHead(302, { location: `https://${siteHost}${url.pathname}${url.search}` }); res.end(); return; }
    if (saved && !state.pagesStays200) { res.writeHead(301, { location: `https://${siteHost}${url.pathname}${url.search}` }); res.end(); return; }
    res.writeHead(200, { 'content-type': 'text/html', 'x-robots-tag': 'noindex, nofollow' });
    res.end('<p>Brot</p>');
  });
  await Promise.all([site, pages].map((x) => new Promise((r) => x.listen(0, '127.0.0.1', r))));
  siteHost = `127.0.0.1:${site.address().port}`;
  return {
    site: `http://${siteHost}`, pages: `http://127.0.0.1:${pages.address().port}`, asked,
    close: () => Promise.all([site, pages].map((x) => { x.closeAllConnections?.(); return new Promise((r) => x.close(r)); })),
  };
}

// ---------------------------------------------------------------- the nameservers

// A nameserver on 127.0.0.1 over UDP that answers A, TXT and CNAME questions from `lookup(name, type)`
// (an array of answers, or null for "no such name"). Enough of RFC 1035 for Node's resolver.
const TYPES = { 1: 'A', 5: 'CNAME', 16: 'TXT' };
const encodeName = (name) => Buffer.concat([...name.replace(/\.$/, '').split('.').map((l) => Buffer.concat([Buffer.from([l.length]), Buffer.from(l)])), Buffer.from([0])]);
export async function startDns(lookup) {
  const asked = [];
  const socket = dgram.createSocket('udp4');
  socket.on('message', (msg, rinfo) => {
    let i = 12;
    const labels = [];
    while (msg[i] !== 0) { labels.push(msg.subarray(i + 1, i + 1 + msg[i]).toString()); i += msg[i] + 1; }
    i++;
    const qtype = msg.readUInt16BE(i);
    const question = msg.subarray(12, i + 4);
    const name = labels.join('.').toLowerCase();
    const type = TYPES[qtype] ?? String(qtype);
    asked.push({ name, type });
    const answers = lookup(name, type) ?? null;
    const header = Buffer.alloc(12);
    header.writeUInt16BE(msg.readUInt16BE(0), 0);
    header.writeUInt16BE(0x8180 | (answers === null ? 3 : 0), 2); // a response; 3 is "no such name"
    header.writeUInt16BE(1, 4);
    header.writeUInt16BE(answers?.length ?? 0, 6);
    const records = (answers ?? []).map((a) => {
      let rdata;
      if (type === 'TXT') rdata = Buffer.concat(String(a).match(/.{1,255}/gs).map((s) => Buffer.concat([Buffer.from([Buffer.byteLength(s)]), Buffer.from(s)])));
      else if (type === 'CNAME') rdata = encodeName(a);
      else rdata = Buffer.from(String(a).split('.').map(Number));
      const rr = Buffer.alloc(12);
      rr.writeUInt16BE(0xc00c, 0);
      rr.writeUInt16BE(qtype, 2);
      rr.writeUInt16BE(1, 4);
      rr.writeUInt32BE(60, 6);
      rr.writeUInt16BE(rdata.length, 10);
      return Buffer.concat([rr, rdata]);
    });
    socket.send(Buffer.concat([header, question, ...records]), rinfo.port, rinfo.address);
  });
  await new Promise((r) => socket.bind(0, '127.0.0.1', r));
  return { address: `127.0.0.1:${socket.address().port}`, asked, close: () => new Promise((r) => socket.close(r)) };
}

// The nameservers of a stub zone: they serve what the stub API holds, or nothing while `silent`.
export const servedBy = (state, { silent = () => false } = {}) => (name, type) => {
  if (silent()) return null;
  const here = state.dns.filter((r) => r.name === name && r.type === type);
  if (!here.length) return null;
  return here.map((r) => (type === 'TXT' ? r.content.replace(/^"(.*)"$/s, '$1') : r.content));
};
