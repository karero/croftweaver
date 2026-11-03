// A stand-in for the three places move-to-workers.mjs talks to: Cloudflare's API, GitHub's check runs
// and the site's own hosts, in one world that the tests change step by step. Standard library only.
//
// Cloudflare's lists, the zone, the project and the DNS records have the shapes of the captures in
// fixtures/cloudflare-api/ (through cloudflare-stub.mjs). The Worker domains, the Worker's
// deployments and its workers.dev subdomain have no capture (they need a live token): those answers
// are MADE from Cloudflare's API reference, and test 5, the throwaway run, settles them.
// GitHub's check runs are the capture in fixtures/github-api/ (gh 2.103.3); an unfinished run is MADE.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ACCOUNT, OWNER, REPO, ZONE, fixture, project, zone } from './cloudflare-stub.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const GH_CHECKS = JSON.parse(readFileSync(path.join(HERE, 'fixtures', 'github-api', 'gh-2.103.3-check-runs.json'), 'utf8'));
export const WORKER = 'lenas-backstube-site';
export const HOSTS = ['lenas-backstube.example', 'www.lenas-backstube.example'];
export const SUBDOMAIN = `${REPO}.pages.dev`;
export const WORKERS_DEV = 'lenas-backstube';
export const VERSION = 'abcdef12-0000-4000-8000-000000000000';
export const VERSION_HOST = `abcdef12-${WORKER}.${WORKERS_DEV}.workers.dev`;

// The site's files, as the build writes them to dist/ (build.txt and build-state.txt follow the commit).
export const SITE = {
  'index.html': '<h1>Lena\'s Backstube</h1>',
  'about/index.html': '<h1>About</h1>',
  'app.js': 'console.log("hi")',
  'photo.avif': 'avif-bytes',
  '_headers': '/*\n  X-Frame-Options: DENY\n',
  '_redirects': '/old /about/ 301\n',
};

const copy = (o) => JSON.parse(JSON.stringify(o));
const json = (status, body) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
const cf = (result, extra = {}) => json(200, { success: true, errors: [], messages: [], result, ...extra });
const cfFail = (status, message) => json(status, { success: false, errors: [{ code: 10000, message }], messages: [], result: null });


export function makeWorld(over = {}) {
  const w = {
    token: { status: 'active', expires_on: new Date(Date.now() + 2 * 86_400_000).toISOString().replace(/\.\d+Z$/, 'Z') },
    zones: [zone()],
    project: project({ domains: HOSTS, subdomain: SUBDOMAIN }),
    dns: HOSTS.map((h, i) => ({ id: `f${String(i + 1).padStart(31, '0')}`, type: 'CNAME', name: h, content: SUBDOMAIN, proxied: true, ttl: 1 })),
    workerDomains: [],
    pagesCommit: null, // what Pages serves; set by the test to the frozen commit
    workerCommit: null, // what the Worker serves (domains and version URL)
    versionId: VERSION,
    dnsExport: `; zone export\n${ZONE.name}. 3600 IN SOA ns1.example. admin.example. 1 7200 3600 86400 3600\n`,
    checkRuns: {}, // sha → check runs
    pagesDeployments: [],
    refuse: {}, // "<METHOD> <route-pattern>" → status
    calls: [], // every Cloudflare call: { method, path, body }
    siteCalls: [], // every site and GitHub call: url
    extraZones: 0,
    nextId: 1,
    ...over,
  };
  return w;
}

// What a host serves right now: pages, worker or nothing (off both).
export function platformOf(w, host) {
  if (host === VERSION_HOST) return 'worker';
  const pages = w.project.domains.includes(host) && w.dns.some((r) => r.type === 'CNAME' && r.name === host && String(r.content).toLowerCase() === SUBDOMAIN);
  const worker = w.workerDomains.some((d) => d.hostname === host);
  return worker ? 'worker' : pages ? 'pages' : null;
}

function served(w, host, urlPath) {
  const platform = platformOf(w, host);
  if (!platform) return new Response('', { status: 522 });
  const shown = w.stale?.[host] ?? platform; // a stale answer from the platform a host just left
  const commit = shown === 'pages' ? w.pagesCommit : w.workerCommit;
  const headers = { 'content-type': 'text/html; charset=utf-8', 'x-frame-options': 'DENY' };
  if (shown === 'pages') headers['access-control-allow-origin'] = '*';
  if (host === VERSION_HOST || w.noindexHosts?.has(host)) headers['x-robots-tag'] = 'noindex';
  else { headers.nel = '{"max_age":0}'; headers['report-to'] = '{}'; headers['strict-transport-security'] = 'max-age=31536000'; }
  const p = urlPath.split('?')[0];
  if (p === '/build.txt') return new Response(`${commit}\n`, { status: 200, headers: { ...headers, 'content-type': 'text/plain' } });
  if (p === '/build-state.txt') return new Response(`${commit}\nbuilt ${Math.random()}\n`, { status: 200, headers: { ...headers, 'content-type': 'text/plain' } });
  if (p === '/old') return new Response('', { status: 301, headers: { ...headers, location: '/about/' } });
  if (p === '/about') return new Response('', { status: platform === 'pages' ? 308 : 307, headers: { ...headers, location: '/about/' } });
  const file = p === '/' ? 'index.html' : p.endsWith('/') ? `${p.slice(1)}index.html` : p.slice(1);
  if (file in SITE && !file.startsWith('_')) {
    const type = file.endsWith('.js') ? (platform === 'pages' ? 'application/javascript' : 'text/javascript') : file.endsWith('.avif') ? 'image/avif' : 'text/html; charset=utf-8';
    const body = file === 'photo.avif' ? `${SITE[file]}-${platform}` : SITE[file]; // the Worker's AVIF differs in bytes
    return new Response(body, { status: 200, headers: { ...headers, 'content-type': type } });
  }
  return new Response('not found', { status: 404, headers });
}

// The stub of `fetch`. Cloudflare's API, GitHub's, and every other URL as a site host.
export function makeFetch(w) {
  return async (url, init = {}) => {
    const u = new URL(url);
    const method = init.method ?? 'GET';
    if (u.hostname === 'api.cloudflare.com') {
      const body = init.body ? JSON.parse(init.body) : undefined;
      const hang = w.hang?.find((h) => h.key === keyOf(method, u.pathname.replace(/^\/client\/v4/, '')) && !h.done);
      if (!hang) return cloudflare(w, method, u, body);
      hang.done = true; // one answer is lost: the change is made first or not, as `applied` says
      const answer = hang.applied ? cloudflare(w, method, u, body) : null;
      await new Promise((_, rej) => init.signal?.addEventListener('abort', () => rej(Object.assign(new Error('aborted'), { name: 'TimeoutError' }))));
      return answer;
    }
    w.siteCalls.push(url);
    if (u.hostname === 'api.github.com') return github(w, u);
    if (u.protocol === 'http:' && w.httpPlain) return new Response('plain', { status: 200 });
    if (u.protocol === 'http:') return new Response('', { status: 301, headers: { location: `https://${u.host}${u.pathname}` } });
    if (w.slowHosts?.has(u.hostname)) await new Promise((r, rej) => { const t = setTimeout(r, 60_000); init.signal?.addEventListener('abort', () => { clearTimeout(t); rej(Object.assign(new Error('aborted'), { name: 'TimeoutError' })); }); });
    return served(w, u.hostname, u.pathname + u.search);
  };
}

function github(w, u) {
  const m = /^\/repos\/([^/]+)\/([^/]+)\/commits\/([0-9a-f]{40})\/check-runs$/.exec(u.pathname);
  if (w.githubPrivate) return json(404, { message: 'Not Found' });
  if (u.pathname === `/repos/${OWNER}/${REPO}`) return json(200, { full_name: `${OWNER}/${REPO}` });
  if (!m) return json(404, { message: 'Not Found' });
  const runs = w.checkRuns[m[3]] ?? copy(GH_CHECKS.check_runs).map((c) => ({ ...c, head_sha: m[3] }));
  return json(200, { total_count: runs.length, check_runs: runs });
}

// MADE: a Workers Builds check run that has not finished (GitHub's API reference: status in_progress, no conclusion).
export function unfinishedWorkersRun(sha) {
  return copy(GH_CHECKS.check_runs).map((c) => (c.name.startsWith('Workers Builds') ? { ...c, head_sha: sha, status: 'in_progress', conclusion: null, completed_at: null } : { ...c, head_sha: sha }));
}

const keyOf = (method, p) => `${method} ${p.replace(/[0-9a-f]{32}/g, ':id').replace(/\/domains\/[^/]+$/, '/domains/:x')}`;

function cloudflare(w, method, u, body) {
  const p = u.pathname.replace(/^\/client\/v4/, '');
  w.calls.push({ method, path: p, body });
  const key = keyOf(method, p);
  if (w.refuse[key]) return cfFail(w.refuse[key], w.refuseMessage ?? 'MADE: refused by the test');
  const A = `/accounts/${ACCOUNT.id}`;
  const Z = `/zones/${ZONE.id}`;
  const page = (items) => cf(items, { result_info: { page: 1, per_page: 100, count: items.length, total_count: items.length, total_pages: 1 } });
  if (method === 'GET' && p === '/user/tokens/verify') return cf({ id: 'c0ffee00000000000000000000000021', status: w.token.status, expires_on: w.token.expires_on });
  if (method === 'GET' && p === '/zones') {
    const extra = Array.from({ length: w.extraZones }, (_, i) => zone({ id: `c0ffee0000000000000000000000009${i}`, name: `extra${i}.example` }));
    return page([...w.zones, ...extra]);
  }
  if (method === 'GET' && p === `${Z}/dns_records/export`) return new Response(w.dnsExport, { status: 200, headers: { 'content-type': 'text/plain' } });
  if (method === 'GET' && p === `${Z}/dns_records`) return page(copy(w.dns));
  if (method === 'POST' && p === `${Z}/dns_records`) {
    const r = { id: `f${String(100 + w.nextId++).padStart(31, '0')}`, ...body };
    w.dns.push(r);
    return cf(r);
  }
  let m = new RegExp(`^${Z}/dns_records/([0-9a-f]{32})$`).exec(p);
  if (m && method === 'DELETE') { w.dns = w.dns.filter((r) => r.id !== m[1]); return cf({ id: m[1] }); }
  if (method === 'GET' && p === `${A}/pages/projects`) return page([copy(w.project)]);
  if (method === 'GET' && p === `${A}/pages/projects/${REPO}`) return cf(copy(w.project));
  if (method === 'GET' && p === `${A}/pages/projects/${REPO}/deployments`) return page(copy(w.pagesDeployments));
  if (method === 'POST' && p === `${A}/pages/projects/${REPO}/domains`) { w.project.domains.push(body.name); return cf({ name: body.name, status: 'initializing' }); }
  m = new RegExp(`^${A}/pages/projects/${REPO}/domains/([^/]+)$`).exec(p);
  if (m && method === 'DELETE') { w.project.domains = w.project.domains.filter((d) => d !== m[1]); return cf(null); }
  if (method === 'GET' && p === `${A}/workers/domains`) return cf(copy(w.workerDomains));
  if (method === 'PUT' && p === `${A}/workers/domains`) {
    const d = { id: `${String(w.nextId++).padStart(8, '0')}-0000-4000-8000-000000000000`, hostname: body.hostname, service: body.service, zone_id: body.zone_id, zone_name: ZONE.name, environment: body.environment };
    w.workerDomains = w.workerDomains.filter((x) => x.hostname !== body.hostname);
    w.workerDomains.push(d);
    return cf(d);
  }
  m = new RegExp(`^${A}/workers/domains/([0-9A-Za-z-]+)$`).exec(p);
  if (m && method === 'DELETE') { w.workerDomains = w.workerDomains.filter((d) => d.id !== m[1]); return cf(null); }
  if (method === 'GET' && p === `${A}/workers/scripts/${WORKER}/deployments`) {
    return cf({ deployments: [{ id: 'd0000001-0000-4000-8000-000000000000', source: 'api', strategy: 'percentage', versions: [{ version_id: w.versionId, percentage: 100 }] }] });
  }
  if (method === 'GET' && p === `${A}/workers/subdomain`) return cf({ subdomain: WORKERS_DEV });
  return cfFail(404, `MADE: the stub holds no ${method} ${p}`);
}

export { ACCOUNT, OWNER, REPO, ZONE, fixture };
