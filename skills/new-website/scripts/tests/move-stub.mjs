// A stand-in for the three places move-to-workers.mjs talks to: Cloudflare's API, GitHub's check runs
// and the site's own hosts, in one world that the tests change step by step. Standard library only.
//
// Cloudflare's lists, the zone, the project and the DNS records have the shapes of the captures in
// fixtures/cloudflare-api/ (through cloudflare-stub.mjs). The Worker domains, the Worker's
// deployments and its workers.dev subdomain have no capture (they need a live token): those answers
// are MADE from Cloudflare's API reference, and test 5, the throwaway run, settles them.
// GitHub's check runs are the capture in fixtures/github-api/ (gh 2.103.3, a public repository's real
// Workers Builds and Pages runs); the Worker's name in it is replaced by this site's, and an unfinished
// run is MADE.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ACCOUNT, OWNER, REPO, ZONE, fixture, project, zone } from './cloudflare-stub.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const GH_CHECKS = JSON.parse(readFileSync(path.join(HERE, 'fixtures', 'github-api', 'gh-2.103.3-workers-builds-trial-check-runs.json'), 'utf8'));
export const WORKER = 'lenas-backstube-site';
export const HOSTS = ['lenas-backstube.example', 'www.lenas-backstube.example'];
export const SUBDOMAIN = `${REPO}.pages.dev`;
export const WORKERS_DEV = 'lenas-backstube';
export const VERSION = 'abcdef12-0000-4000-8000-000000000000';
export const versionHost = (id) => `${id.slice(0, 8)}-${WORKER}.${WORKERS_DEV}.workers.dev`;
export const VERSION_HOST = versionHost(VERSION);

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
// The capture's runs, for a commit, with the capture's Worker name replaced by this site's.
const captured = (sha) => copy(GH_CHECKS.check_runs).map((c) => ({ ...c, head_sha: sha, name: c.name.replace('croftweaver-trial', WORKER) }));
const json = (status, body) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
const cf = (result, extra = {}) => json(200, { success: true, errors: [], messages: [], result, ...extra });
const cfFail = (status, message) => json(status, { success: false, errors: [{ code: 10000, message }], messages: [], result: null });


// Waits for the request's abort. The abort timer alone does not keep an older Node alive, so a pending
// answer would end the test run early; this holds the event loop open until the abort.
function untilAborted(signal) {
  return new Promise((_, rej) => {
    const keep = setTimeout(() => {}, 120_000);
    signal?.addEventListener('abort', () => { clearTimeout(keep); rej(Object.assign(new Error('aborted'), { name: 'TimeoutError' })); });
  });
}

export function makeWorld(over = {}) {
  const w = {
    token: { status: 'active', expires_on: new Date(Date.now() + 2 * 86_400_000).toISOString().replace(/\.\d+Z$/, 'Z') },
    zones: [zone()],
    project: project({ domains: HOSTS, subdomain: SUBDOMAIN }),
    dns: [
      ...HOSTS.map((h, i) => ({ id: `f${String(i + 1).padStart(31, '0')}`, type: 'CNAME', name: h, content: SUBDOMAIN, proxied: true, ttl: 1 })),
      // an apex has mail and a verification text next to its address record
      { id: 'e'.padEnd(32, '1'), type: 'MX', name: HOSTS[0], content: 'mail.example.net', priority: 10, ttl: 3600 },
      { id: 'e'.padEnd(32, '2'), type: 'TXT', name: HOSTS[0], content: 'v=spf1 -all', ttl: 3600 },
    ],
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
    extraZones: 0, // more zones whose permissions reach DNS, as a wider token would
    accountOnlyZones: 0, // more zones listed only through the account's Workers permission (see fixtures/cloudflare-token)
    nextId: 1,
    ...over,
  };
  return w;
}

// What a host serves right now: pages, worker or nothing (off both).
export function platformOf(w, host) {
  if (host.endsWith('.workers.dev')) return 'worker';
  const pages = w.project.domains.includes(host) && w.dns.some((r) => r.type === 'CNAME' && r.name === host && String(r.content).toLowerCase() === SUBDOMAIN);
  const worker = w.workerDomains.some((d) => d.hostname === host);
  return worker ? 'worker' : pages ? 'pages' : null;
}

function served(w, host, urlPath) {
  const platform = platformOf(w, host);
  if (!platform) return new Response('', { status: 522 });
  const shown = w.stale?.[host] ?? platform; // a stale answer from the platform a host just left
  if (w.wwwRedirect && host === w.wwwRedirect.from) { // a zone Redirect Rule answers before either platform
    const [bare, query] = urlPath.split('?'); // `query` is a rule that adds its own parameter; `keepQuery` one that keeps the request's
    const kept = [w.wwwRedirect.query, w.wwwRedirect.keepQuery ? query : null].filter(Boolean).join('&');
    return new Response('', { status: 301, headers: { location: `https://${w.wwwRedirect.to}${bare}${kept ? `?${kept}` : ''}`, nel: '{"max_age":0}', 'report-to': '{}', 'strict-transport-security': 'max-age=31536000' } });
  }
  const commit = shown === 'pages' ? w.pagesCommit : w.workerCommit;
  const headers = { 'content-type': 'text/html; charset=utf-8', 'x-frame-options': 'DENY' };
  if (shown === 'pages') headers['access-control-allow-origin'] = '*';
  if (host.endsWith('.workers.dev') || w.noindexHosts?.has(host)) headers['x-robots-tag'] = 'noindex';
  else { headers.nel = '{"max_age":0}'; headers['report-to'] = '{}'; headers['strict-transport-security'] = 'max-age=31536000'; }
  const p = urlPath.split('?')[0];
  if (p === '/build.txt') return new Response(`${commit}\n`, { status: 200, headers: { ...headers, 'content-type': platform === 'worker' && w.buildTxtWorkerType ? w.buildTxtWorkerType : 'text/plain' } });
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

// A request that takes `ms` on the injected clock `clock` (an object with a settable `t`). Requests
// begun together overlap: the clock moves to the latest end, not by the sum.
export async function spend({ clock, ms }) {
  const start = clock.t;
  await new Promise((r) => setImmediate(r));
  clock.t = Math.max(clock.t, start + ms);
}

// The stub of `fetch`. Cloudflare's API, GitHub's, and every other URL as a site host.
// `w.latency = { clock, ms }` makes every request take that long on the test's clock.
export function makeFetch(w) {
  return async (url, init = {}) => {
    const u = new URL(url);
    if (w.latency) await spend(w.latency);
    const method = init.method ?? 'GET';
    if (u.hostname === 'api.cloudflare.com') {
      const body = init.body ? JSON.parse(init.body) : undefined;
      const slow = w.delay?.[keyOf(method, u.pathname.replace(/^\/client\/v4/, ''))];
      if (slow) await new Promise((r) => setTimeout(r, slow));
      const hang = w.hang?.find((h) => h.key === keyOf(method, u.pathname.replace(/^\/client\/v4/, '')) && !h.done);
      if (!hang) return cloudflare(w, method, u, body);
      hang.done = true; // one answer is lost: the change is made first or not, as `applied` says
      const answer = hang.applied ? cloudflare(w, method, u, body) : null;
      await untilAborted(init.signal);
      return answer;
    }
    w.siteCalls.push(url);
    if (u.hostname === 'api.github.com') return github(w, u);
    if (u.protocol === 'http:' && w.httpPlain) return new Response('plain', { status: 200 });
    if (u.protocol === 'http:' && w.httpElsewhere) return new Response('', { status: 301, headers: { location: `https://elsewhere.example${u.pathname}` } });
    if (u.protocol === 'http:') { // plain http goes to https, on the same host unless a zone rule sends it to another
      const to = w.httpTo?.[u.hostname] ?? (w.wwwRedirect?.from === u.hostname ? w.wwwRedirect.to : u.host);
      return new Response('', { status: 301, headers: { location: `https://${to}${u.pathname}` } });
    }
    if (w.stallAfter !== undefined && w.stallAfter !== null && w.siteCalls.length > w.stallAfter) { // every later answer waits for the abort
      await untilAborted(init.signal);
    }
    if (w.slowHosts?.has(u.hostname)) await new Promise((r, rej) => { const t = setTimeout(r, 60_000); init.signal?.addEventListener('abort', () => { clearTimeout(t); rej(Object.assign(new Error('aborted'), { name: 'TimeoutError' })); }); });
    if (w.dropOnce?.has(u.pathname)) { w.dropOnce.delete(u.pathname); throw new Error('MADE: connection reset'); } // one lost answer for an address
    return served(w, u.hostname, u.pathname + u.search);
  };
}

function github(w, u) {
  const m = /^\/repos\/([^/]+)\/([^/]+)\/commits\/([0-9a-f]{40})\/check-runs$/.exec(u.pathname);
  if (w.githubPrivate) return json(404, { message: 'Not Found' });
  if (u.pathname === `/repos/${OWNER}/${REPO}`) return json(200, { full_name: `${OWNER}/${REPO}` });
  if (!m) return json(404, { message: 'Not Found' });
  const runs = w.checkRuns[m[3]] ?? captured(m[3]);
  const size = Math.min(100, Number(u.searchParams.get('per_page') ?? w.ghDefaultPage ?? 30)); // GitHub's default page is 30, its largest 100
  const at = (Number(u.searchParams.get('page') ?? 1) - 1) * size;
  if (w.ghEmptyAfterFirst && at > 0) return json(200, { total_count: runs.length, check_runs: [] }); // a later page that comes back empty
  return json(200, { total_count: runs.length, check_runs: runs.slice(at, at + size) });
}

// The capture's runs without the Workers Builds one (a repository whose Worker has no Workers Builds, or a push it has not reported on yet).
export const withoutWorkersRun = (sha) => captured(sha).filter((c) => !c.name.startsWith('Workers Builds'));

// MADE: n finished runs of some other app, to push a run onto a later page.
export const fillerRuns = (sha, n) => Array.from({ length: n }, (_, i) => ({ id: 900000 + i, head_sha: sha, name: `filler ${i}`, status: 'completed', conclusion: 'success', app: { slug: 'github-actions', name: 'GitHub Actions' } }));

// MADE: a Workers Builds check run that has not finished (GitHub's API reference: status in_progress, no conclusion).
export function unfinishedWorkersRun(sha) {
  return captured(sha).map((c) => (c.name.startsWith('Workers Builds') ? { ...c, status: 'in_progress', conclusion: null, completed_at: null } : c));
}

const keyOf = (method, p) => `${method} ${p.replace(/[0-9a-f]{32}/g, ':id').replace(/\/domains\/[^/]+$/, '/domains/:x')}`;

function cloudflare(w, method, u, body) {
  const p = u.pathname.replace(/^\/client\/v4/, '');
  w.calls.push({ method, path: p, body, query: u.search });
  const key = keyOf(method, p);
  w.onCall?.(key); // a test's hook: change the world, or the clock, when this call arrives
  if (w.refuse[key]) return cfFail(w.refuse[key], w.refuseMessage ?? 'MADE: refused by the test');
  const A = `/accounts/${ACCOUNT.id}`;
  const Z = `/zones/${ZONE.id}`;
  const page = (items) => cf(items, { result_info: { page: 1, per_page: 100, count: items.length, total_count: items.length, total_pages: 1 } });
  if (method === 'GET' && p === '/user/tokens/verify') return cf({ id: 'c0ffee00000000000000000000000021', status: w.token.status, expires_on: w.token.expires_on });
  if (method === 'GET' && p === '/zones') {
    const extra = Array.from({ length: w.extraZones }, (_, i) => zone({ id: `c0ffee0000000000000000000000009${i}`, name: `extra${i}.example` }));
    if (w.zonesNoPageCount) return cf([...w.zones, ...extra].slice(0, 1), { result_info: { page: 1, per_page: 50, count: 1 } }); // one zone a page, and no page count
    const wide = Array.from({ length: w.accountOnlyZones }, (_, i) => zone({ id: `c0ffee0000000000000000000000008${i}`, name: `account${i}.example`, permissions: ['#worker:edit', '#worker:read', '#analytics:read', '#organization:edit', '#zone:read', '#organization:read'] }));
    return page([...wide, ...w.zones, ...extra]);
  }
  if (method === 'GET' && p === `${Z}/dns_records/export`) return new Response(w.dnsExport, { status: 200, headers: { 'content-type': 'text/plain' } });
  if (method === 'GET' && p === `${Z}/dns_records`) { // pages of `per_page` records, as Cloudflare's list has them
    const size = Math.min(100, Number(u.searchParams.get('per_page') ?? 100));
    const n = Number(u.searchParams.get('page') ?? 1);
    const named = u.searchParams.get('name');
    const all = named && !w.dnsIgnoresName ? w.dns.filter((r) => r.name === named) : w.dns; // `dnsIgnoresName`: a filter the API does not know
    const items = copy(all).slice((n - 1) * size, n * size);
    return cf(items, { result_info: { page: n, per_page: size, count: items.length, total_count: all.length, total_pages: Math.max(1, Math.ceil(all.length / size)) } });
  }
  if (method === 'POST' && p === `${Z}/dns_records`) {
    const r = { id: `f${String(100 + w.nextId++).padStart(31, '0')}`, ...body };
    w.dns.push(r);
    return cf(r);
  }
  const tail = (prefix, re) => (p.startsWith(prefix) ? re.exec(p.slice(prefix.length)) : null);
  let m = tail(`${Z}/dns_records/`, /^([0-9a-f]{32})$/);
  if (m && method === 'DELETE') { w.dns = w.dns.filter((r) => r.id !== m[1]); return cf({ id: m[1] }); }
  if (method === 'GET' && p === `${A}/pages/projects`) return page([copy(w.project)]);
  if (method === 'GET' && p === `${A}/pages/projects/${REPO}`) return cf(copy(w.project));
  if (method === 'GET' && p === `${A}/pages/projects/${REPO}/deployments`) {
    const size = Math.min(100, Number(u.searchParams.get('per_page') ?? w.depDefaultPage ?? 25));
    const n = Number(u.searchParams.get('page') ?? 1);
    const cut = w.depShort && n === w.depShort.page ? w.depShort.size : size; // a page that holds fewer than it should, and is not empty
    const items = w.depEmptyAfterFirst && n > 1 ? [] : copy(w.pagesDeployments).slice((n - 1) * size, (n - 1) * size + cut); // a later page may come back empty
    return cf(items, { result_info: { page: n, per_page: size, count: items.length, total_count: w.pagesDeployments.length, total_pages: Math.max(1, Math.ceil(w.pagesDeployments.length / size)) } });
  }
  if (method === 'POST' && p === `${A}/pages/projects/${REPO}/domains`) { w.project.domains.push(body.name); return cf({ name: body.name, status: 'initializing' }); }
  m = tail(`${A}/pages/projects/${REPO}/domains/`, /^([^/]+)$/);
  if (m && method === 'DELETE') { w.project.domains = w.project.domains.filter((d) => d !== m[1]); return cf(null); }
  if (method === 'GET' && p === `${A}/workers/domains`) return cf(copy(w.workerDomains));
  if (method === 'PUT' && p === `${A}/workers/domains`) {
    const d = { id: `${String(w.nextId++).padStart(8, '0')}-0000-4000-8000-000000000000`, hostname: body.hostname, service: body.service, zone_id: body.zone_id, zone_name: ZONE.name, environment: body.environment };
    w.workerDomains = w.workerDomains.filter((x) => x.hostname !== body.hostname);
    w.workerDomains.push(d);
    return cf(d);
  }
  m = tail(`${A}/workers/domains/`, /^([0-9A-Za-z-]+)$/);
  if (m && method === 'DELETE') { w.workerDomains = w.workerDomains.filter((d) => d.id !== m[1]); return cf(null); }
  if (method === 'GET' && p === `${A}/workers/scripts/${WORKER}/deployments`) {
    return cf({ deployments: [{ id: 'd0000001-0000-4000-8000-000000000000', source: 'api', strategy: 'percentage', versions: [{ version_id: w.versionId, percentage: 100 }] }] });
  }
  if (method === 'GET' && p === `${A}/workers/subdomain`) return cf({ subdomain: WORKERS_DEV });
  return cfFail(404, `MADE: the stub holds no ${method} ${p}`);
}

export { ACCOUNT, OWNER, REPO, ZONE, fixture };
