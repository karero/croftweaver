#!/usr/bin/env node
// move-to-workers.mjs: move a live site's domain from its Cloudflare Pages project to its Worker,
// check that nothing a visitor sees changed, and undo the move on request. Run it in the site's
// folder; references/CLOUDFLARE_MOVE.md says when to run which command.
//
//   node move-to-workers.mjs check | record | after
//   node move-to-workers.mjs move | undo [--confirm <code>]
//
// `move` and `undo` print their question and a code and end with 3; the same command with
// --confirm <code> makes the changes. Needs Node 18 or newer and nothing from npm. Exit status: 0
// finished, 1 failed or refused, 2 the command was wrong, 3 waiting for a yes, 4 run the same
// command again.
import { spawn } from 'node:child_process';
import { createHash, randomBytes } from 'node:crypto';
import { existsSync, linkSync, mkdirSync, openSync, readFileSync, readdirSync, realpathSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { githubRepo, running } from './cloudflare-setup.mjs';

const API_HOST = 'https://api.cloudflare.com';
const API_PREFIX = '/client/v4';
const RUN_MS = 55_000; // one deadline per run, as the setup script has
const REQUEST_MS = 8_000;
const GIT_NET_MS = 15_000; // a git read of GitHub gets this long, not the whole run
const MAX_RETRIES = 3; // runs that ask again for addresses that got no answer
const MAX_TOKEN_MS = 8 * 86_400_000; // the setup script's limit: the dashboard sets an end date, not a time
const MIN_LEFT_MS = 3_600_000;
const TARGET_MS = 15 * 60_000;
const POLL_MS = 30_000; // GitHub is read no more often than this
const GOOD_GAP_MS = 2_000;
const MAX_PATHS = 2000;
const MAX_COMMITS = 20;
const READ_WIDTH = 6; // pages and commits read together, so a long list does not use the run up before a host
const UA = 'croftweaver-move-to-workers/1';
const NOT_THERE = '/croftweaver-move-check-no-such-page';
const ZONE_HEADERS = ['nel', 'report-to', 'strict-transport-security'];
const NEVER_COMPARED = ['date', 'age', 'cf-ray', 'cf-cache-status', 'server-timing', 'etag', 'cache-control'];
const BUILD_FILES = ['/build.txt', '/build-state.txt'];
const ADDRESS_TYPES = ['A', 'AAAA', 'CNAME']; // the records a host's address can be, as opposed to mail and text
const REDIRECTS = [301, 302, 303, 307, 308];

export class UsageError extends Error {}
export class Stop extends Error { // the run ends here with `code`; `lines` say why
  constructor(code, ...lines) { super(lines[0]); this.code = code; this.lines = lines; }
}
// The run's deadline. `waiting`: a call was sent or running when it came (false: it came before the
// next call). `place` and `call` name that call; the code that makes or starts the call sets them.
class Deadline extends Error {
  constructor(waiting, place = null, call = null) { super('deadline'); Object.assign(this, { waiting, place, call }); }
}

const USAGE = `Usage: node move-to-workers.mjs check|record|move|undo|after [--confirm <code>]

Run it in the site's folder, with the token in CLOUDFLARE_API_TOKEN or in .dev.vars (a file git
ignores). The order is check, record, move (twice: the question, then --confirm), push the route
commit, after. undo is the way back.

  check                  read-only: what the move would touch, and what is there now
  record                 freeze the content and record what the live site serves
  move                   attach the hosts to the Worker; with --confirm <code> it makes the changes
  undo                   give the hosts back to the Pages project; with --confirm <code> likewise
  after                  check the live site against the recording once the commit is pushed
  --confirm <code>       the code of the question the owner said yes to
  -h, --help             this text

Exit status: 0 finished; 1 something failed or was refused (the report says what); 2 the command
was wrong; 3 waiting for a yes; 4 run the same command again. After every run, move-run/status.html
says where the move stands.
`;

export function parseArgs(argv) {
  const opts = { cmd: null, confirm: null, help: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '-h' || a === '--help') opts.help = true;
    else if (a === '--confirm') {
      const v = argv[++i];
      if (v === undefined || v.startsWith('-')) throw new UsageError('--confirm needs a value');
      opts.confirm = v;
    } else if (a.startsWith('-')) throw new UsageError(`unknown option ${a}`);
    else if (opts.cmd === null) opts.cmd = a;
    else throw new UsageError(`unexpected "${a}": give one command`);
  }
  if (opts.help) return opts;
  if (!['check', 'record', 'move', 'undo', 'after'].includes(opts.cmd)) throw new UsageError(opts.cmd ? `unknown command "${opts.cmd}"` : 'give the command: check, record, move, undo or after');
  if (opts.confirm !== null && !['move', 'undo'].includes(opts.cmd)) throw new UsageError('--confirm belongs to move and undo');
  if (opts.confirm !== null && !/^[0-9a-f]{16}$/.test(opts.confirm)) throw new UsageError('--confirm takes the 16-character code the question printed');
  return opts;
}

// ---------------------------------------------------------------- the gate

// Every request to api.cloudflare.com passes here and is checked before it is sent. `ctx` holds what
// this run has learned: the account, zone, Pages project, Worker and hosts, and the ids a read in
// this run showed (`cnames`, `workerDomainIds`).
export function gate(method, url, body, ctx) {
  const [route, query = ''] = url.split('?');
  const refuse = (why) => { throw new Stop(1, `gate: refused ${method} ${route}${why ? ` (${why})` : ''}`); };
  if (/\.\.|%|\\|\/\/|[^\x21-\x7e]/.test(url)) refuse('odd path');
  const paged = /^(?:(?:page|per_page)=\d{1,4})?(?:&(?:page|per_page)=\d{1,4})*$/.test(query.replace(/^&/, ''));
  // A host's own records: name=<a host of this move>, with the page words and nothing else.
  const pairs = query.split('&');
  const byHost = pairs.some((q) => q.startsWith('name='))
    && pairs.every((q) => /^(?:page|per_page)=\d{1,4}$/.test(q) || (q.startsWith('name=') && (ctx.hosts ?? new Set()).has(q.slice(5))));
  const A = ctx.accountId ? `/accounts/${ctx.accountId}` : null;
  const Z = ctx.zoneId ? `/zones/${ctx.zoneId}` : null;
  const P = A && ctx.project ? `${A}/pages/projects/${ctx.project}` : null;
  const W = A && ctx.worker ? `${A}/workers/scripts/${ctx.worker}` : null;
  const hosts = ctx.hosts ?? new Set();
  if (method === 'GET') {
    if (route === '/user/tokens/verify' && !query) return;
    if (route === '/zones' && paged) return;
    if (Z && (route === Z || route === `${Z}/dns_records/export`) && !query) return;
    if (Z && route === `${Z}/dns_records` && (paged || byHost)) return;
    if (A && route === `${A}/pages/projects` && paged) return;
    if (P && (route === P || route === `${P}/domains`) && !query) return;
    if (P && route === `${P}/deployments` && paged) return;
    if (W && route === `${W}/deployments` && !query) return;
    if (A && route === `${A}/workers/subdomain` && !query) return;
    if (A && route === `${A}/workers/domains` && (!query || query === `service=${ctx.worker}`)) return;
    refuse();
  }
  if (P && route === `${P}/domains` && method === 'POST' && !query
    && body && Object.keys(body).join() === 'name' && hosts.has(body.name)) return;
  const tail = (prefix) => (prefix && route.startsWith(`${prefix}/`) ? route.slice(prefix.length + 1) : null);
  const pd = tail(P && `${P}/domains`);
  if (pd && /^[^/]+$/.test(pd) && method === 'DELETE' && !query && hosts.has(pd)) return;
  if (Z && route === `${Z}/dns_records` && method === 'POST' && !query && body
    && Object.keys(body).every((k) => ['type', 'name', 'content', 'proxied', 'ttl'].includes(k))
    && body.type === 'CNAME' && hosts.has(body.name) && body.content === ctx.subdomain
    && body.proxied === true && (body.ttl === undefined || body.ttl === 1)) return;
  const dr = tail(Z && `${Z}/dns_records`);
  if (dr !== null && /^[0-9a-f]{32}$/.test(dr) && method === 'DELETE' && !query) {
    const seen = ctx.cnames?.get(dr);
    if (seen && hosts.has(seen.name) && seen.content === ctx.subdomain) return;
    refuse('not a CNAME to the project that a read in this run showed');
  }
  if (A && route === `${A}/workers/domains` && method === 'PUT' && !query && body
    && Object.keys(body).every((k) => ['hostname', 'service', 'zone_id', 'zone_name', 'environment'].includes(k))
    && hosts.has(body.hostname) && body.service === ctx.worker && body.zone_id === ctx.zoneId
    && (body.zone_name === undefined || body.zone_name === ctx.zoneName) && body.environment === 'production') return;
  const wd = tail(A && `${A}/workers/domains`);
  if (wd !== null && /^[0-9A-Za-z-]{8,64}$/.test(wd) && method === 'DELETE' && !query) {
    const seen = ctx.workerDomainIds?.get(wd);
    if (seen && hosts.has(seen)) return;
    refuse('not one of the hosts on this Worker, as a read in this run showed');
  }
  refuse();
}

// A call to Cloudflare's API, given only the time left. It answers { status, body, text }; an HTTP
// status never rejects, and a connection that fails or times out answers status 0.
export function makeApi(send, token, ctx, { clock = null, requestMs = REQUEST_MS } = {}) {
  return async (method, p, { json } = {}) => {
    const wire = json === undefined ? undefined : JSON.stringify(json);
    gate(method, p, wire === undefined ? undefined : JSON.parse(wire), ctx); // the gate sees what is sent
    const call = apiCall(method, p);
    const left = clock ? clock.left() : Infinity;
    if (left <= 0) throw new Deadline(false, 'Cloudflare', call);
    const headers = { authorization: `Bearer ${token}`, accept: 'application/json', 'user-agent': UA };
    if (wire !== undefined) headers['content-type'] = 'application/json';
    try {
      const r = await send(`${API_HOST}${API_PREFIX}${p}`, { method, headers, body: wire, signal: AbortSignal.timeout(Math.min(requestMs, left)) });
      const text = await r.text();
      let body = null;
      try { body = text ? JSON.parse(text) : null; } catch { body = null; }
      return { status: r.status, body, text };
    } catch (e) {
      if (clock && clock.left() <= 0) throw new Deadline(true, 'Cloudflare', call);
      return { status: 0, body: null, text: '', error: e?.name === 'TimeoutError' || e?.name === 'AbortError' ? 'timed out' : String(e?.message ?? e) };
    }
  };
}

// A Cloudflare call as a stop names it: no query, and the ids after these segments cut, for a readable line.
const apiCall = (method, p) => `${method} ${p.split('?')[0].replace(/\/(accounts|zones|dns_records|domains)\/[^/]+/g, '/$1/…')}`;

// The site, the Worker's version URL and GitHub: every host but those is refused, and so is
// api.cloudflare.com. Redirects are never followed.
export function makeSiteFetch(send, allowed, { clock = null, requestMs = REQUEST_MS } = {}) {
  return async (url, { method = 'GET', headers = {} } = {}) => {
    const u = new URL(url);
    if (u.hostname === 'api.cloudflare.com' || !allowed.has(u.hostname)) throw new Stop(1, `gate: refused fetch of ${u.hostname}`);
    if (u.protocol !== 'https:' && !(u.protocol === 'http:' && u.hostname !== 'api.github.com')) throw new Stop(1, `gate: refused ${u.protocol} fetch`);
    const left = clock ? clock.left() : Infinity;
    if (left <= 0) throw new Deadline(false, u.hostname, u.pathname);
    try {
      const r = await send(url, { method, headers: { 'user-agent': UA, ...headers }, redirect: 'manual', signal: AbortSignal.timeout(Math.min(requestMs, left)) });
      return { status: r.status, headers: r.headers, body: Buffer.from(await r.arrayBuffer()) };
    } catch (e) {
      if (clock && clock.left() <= 0) throw new Deadline(true, u.hostname, u.pathname);
      return { status: 0, headers: new Headers(), body: Buffer.alloc(0), error: e?.name === 'TimeoutError' || e?.name === 'AbortError' ? 'timed out' : String(e?.message ?? e) };
    }
  };
}

const ok = (r) => r.status >= 200 && r.status < 300 && r.body?.success !== false;
function cfWords(r) {
  const all = [...(r.body?.errors ?? []), ...(r.body?.messages ?? [])].filter((e) => e && e.message)
    .map((e) => (e.code ? `${e.message} (code ${e.code})` : e.message));
  return all.length ? [...new Set(all)].join('; ') : (r.error ?? `HTTP ${r.status}`);
}

// A difference in words. A commit line names who serves what (d.who, "the site" after the move) and what is expected; the rest keep "expected ≠ got".
const diffWords = (d) => (d.field === 'commit line' ? `${d.who ?? 'the site'} serves ${d.got ?? 'no commit line'}; ${d.expected} is expected` : `${d.expected} ≠ ${d.got}`);

// A bounded number of calls at a time; the first failure ends the pool and is thrown.
async function pool(items, width, fn) {
  const out = new Array(items.length);
  let next = 0;
  let failed = null;
  const worker = async () => {
    while (!failed && next < items.length) {
      const i = next++;
      try { out[i] = await fn(items[i]); } catch (e) { failed ??= { e }; }
    }
  };
  await Promise.all(Array.from({ length: Math.min(width, items.length) }, worker));
  if (failed) throw failed.e;
  return out;
}

// `totals`: the lists whose every page matters refuse an answer that does not say how many pages.
// `width` above 1 reads pages 2 to the last together, that many at a time, once page 1 has said
// how many there are. Whatever pages were read, the items collected must equal the largest
// total_count any page reported. Answers { r, items, requests, total }: the requests made, for the
// run's budget, and that largest total (null when no page gave one).
async function allPages(api, p, perPage = null, { totals = false, width = 1 } = {}) {
  const items = [];
  const at = (page) => api('GET', `${p}${p.includes('?') ? '&' : '?'}${perPage ? `per_page=${perPage}&` : ''}page=${page}`);
  const where = p.split('?')[0];
  let requests = 0;
  let maxTotal = null;
  const seen = (r) => {
    const t = r.body?.result_info?.total_count;
    if (Number.isInteger(t) && (maxTotal === null || t > maxTotal)) maxTotal = t;
  };
  const done = (r) => {
    if (maxTotal !== null && items.length !== maxTotal) throw new Stop(1, `Cloudflare's list at ${where} gave ${items.length} items but said it holds ${maxTotal}; the script does not decide from part of a list.`);
    return { r, items, requests, total: maxTotal };
  };
  for (let page = 1; page <= 200; page++) {
    const r = await at(page);
    requests++;
    if (!ok(r)) return { r, items: null, requests, total: null };
    seen(r);
    const got = Array.isArray(r.body?.result) ? r.body.result : [];
    items.push(...got);
    const pages = r.body?.result_info?.total_pages;
    const total = r.body?.result_info?.total_count;
    if (totals && got.length && !pages) throw new Stop(1, `Cloudflare's list at ${where} does not say how many pages it has; the script does not decide from part of a list.`);
    if (!got.length) {
      if ((pages && page < pages) || (Number.isInteger(total) && items.length < total)) throw new Stop(1, `Cloudflare's list at ${where} came back empty at page ${page} with ${items.length} of ${total ?? 'an unknown number of'} items; the script does not decide from part of a list.`);
      return done(r);
    }
    if (!pages || page >= pages) return done(r);
    if (width > 1 && page === 1) {
      if (pages > 200) throw new Stop(1, `Cloudflare's list at ${where} runs past 200 pages; the script does not decide from part of a list.`);
      const rest = await pool(Array.from({ length: pages - 1 }, (_, i) => i + 2), width, at);
      requests += rest.length;
      for (const [i, rr] of rest.entries()) {
        if (!ok(rr)) return { r: rr, items: null, requests, total: null };
        seen(rr);
        const more = Array.isArray(rr.body?.result) ? rr.body.result : [];
        if (!more.length) throw new Stop(1, `Cloudflare's list at ${where} came back empty at page ${i + 2} with ${items.length} of ${total ?? 'an unknown number of'} items; the script does not decide from part of a list.`);
        items.push(...more);
      }
      return done(r);
    }
  }
  throw new Stop(1, `Cloudflare's list at ${where} runs past 200 pages; the script does not decide from part of a list.`);
}

// ---------------------------------------------------------------- escaping

// The one function every value passes on its way into the status page.
export const esc = (v) => String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

// ---------------------------------------------------------------- the clock, programs, git

function makeClock(ms, now = () => Date.now()) {
  const end = now() + ms;
  return { left: () => end - now() };
}

// The environment every program the script starts gets: the token removed, git told never to ask.
function childEnv(env, token) {
  const out = {};
  for (const [k, v] of Object.entries(env)) {
    if (k === 'CLOUDFLARE_API_TOKEN' || (token && v === token)) continue;
    out[k] = v;
  }
  out.GIT_TERMINAL_PROMPT = '0';
  return out;
}

// A program with its input closed, given only the time left; at the deadline its group is killed.
export function runProgram(cmd, args, { cwd, env, clock }) {
  return new Promise((resolve, reject) => {
    const ms = clock.left();
    if (ms <= 0) { reject(new Deadline(false)); return; }
    const posix = process.platform !== 'win32';
    let out = '';
    let err = '';
    let settled = false;
    let child;
    try {
      child = spawn(cmd, args, { cwd, env, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, detached: posix });
    } catch (e) { reject(new Stop(1, `could not run ${cmd}: ${e.message}`)); return; }
    const settle = (fn) => { if (settled) return; settled = true; clearTimeout(timer); fn(); };
    const timer = setTimeout(() => {
      try { if (posix) process.kill(-child.pid, 'SIGKILL'); else child.kill('SIGKILL'); } catch { /* it has ended */ }
      child.stdout.destroy();
      child.stderr.destroy();
      settle(() => reject(new Deadline(true)));
    }, ms);
    child.stdout.on('data', (c) => { out += c; });
    child.stderr.on('data', (c) => { err += c; });
    child.on('error', (e) => settle(() => reject(new Stop(1, e.code === 'ENOENT' ? `${cmd} is not installed, or not on the PATH` : `could not run ${cmd}: ${e.message}`))));
    child.on('close', (code) => settle(() => resolve({ code, stdout: out, stderr: err })));
  });
}

// A program's deadline, named where the real command is known (a test may hand runProgram a stand-in).
function named(e, place, call) {
  if (e instanceof Deadline && !e.place) Object.assign(e, { place, call });
  return e;
}

const short = (sha) => String(sha).slice(0, 7);
const sha256 = (buf) => createHash('sha256').update(buf).digest('hex').slice(0, 16);
export const EMPTY_BODY = sha256(Buffer.alloc(0));
// The body Pages sent with a _redirects 301 in the 2026-11-05 capture: "Redirecting to /privacy" for Location /privacy.
export const pagesRedirectBody = (location) => sha256(Buffer.from(`Redirecting to ${location}`));
const HOSTNAME = /^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/;

// ---------------------------------------------------------------- JSONC (the Workers config)

// The text with comments and trailing commas blanked to spaces, so every offset is the original's.
export function blankJsonc(text) {
  let s = '';
  for (let i = 0; i < text.length;) {
    const c = text[i];
    if (c === '"') {
      let j = i + 1;
      while (j < text.length && text[j] !== '"') j += text[j] === '\\' ? 2 : 1;
      s += text.slice(i, j + 1);
      i = j + 1;
    } else if (c === '/' && text[i + 1] === '/') {
      let j = i;
      while (j < text.length && text[j] !== '\n') j++;
      s += ' '.repeat(j - i);
      i = j;
    } else if (c === '/' && text[i + 1] === '*') {
      const k = text.indexOf('*/', i + 2);
      const end = k < 0 ? text.length : k + 2;
      s += text.slice(i, end).replace(/[^\n]/g, ' ');
      i = end;
    } else { s += c; i++; }
  }
  let out = '';
  for (let i = 0; i < s.length;) {
    const c = s[i];
    if (c === '"') {
      let j = i + 1;
      while (j < s.length && s[j] !== '"') j += s[j] === '\\' ? 2 : 1;
      out += s.slice(i, j + 1);
      i = j + 1;
    } else if (c === ',') {
      let j = i + 1;
      while (j < s.length && /\s/.test(s[j])) j++;
      out += s[j] === '}' || s[j] === ']' ? ' ' : ',';
      i++;
    } else { out += c; i++; }
  }
  return out;
}
export const parseJsonc = (text) => JSON.parse(blankJsonc(text));

// Where the top-level key's value starts and ends in blanked text.
function findTop(S, key) {
  let depth = 0;
  for (let i = 0; i < S.length; i++) {
    const c = S[i];
    if (c === '"') {
      let j = i + 1;
      while (j < S.length && S[j] !== '"') j += S[j] === '\\' ? 2 : 1;
      if (depth === 1) {
        let m = j + 1;
        while (/\s/.test(S[m] ?? 'x')) m++;
        if (S[m] === ':' && JSON.parse(S.slice(i, j + 1)) === key) {
          let v = m + 1;
          while (/\s/.test(S[v])) v++;
          let end = v;
          if (S[v] === '[' || S[v] === '{') {
            let d = 0;
            for (end = v; end < S.length; end++) {
              if (S[end] === '"') { end++; while (S[end] !== '"') end += S[end] === '\\' ? 2 : 1; } else if (S[end] === '[' || S[end] === '{') d++;
              else if (S[end] === ']' || S[end] === '}') { d--; if (d === 0) { end++; break; } }
            }
          } else while (end < S.length && !/[,}\]\n]/.test(S[end])) end++;
          return { valueStart: v, valueEnd: end };
        }
      }
      i = j;
    } else if (c === '{' || c === '[') depth++;
    else if (c === '}' || c === ']') depth--;
  }
  return null;
}

// The config's text with its `routes` set to exactly these hosts as custom domains (none: an empty
// list), comments and the rest untouched.
export function setRoutes(text, patterns) {
  const S = blankJsonc(text);
  const value = patterns.length ? `[\n${patterns.map((p) => `    { "pattern": "${p}", "custom_domain": true }`).join(',\n')}\n  ]` : '[]';
  const at = findTop(S, 'routes');
  if (at) return text.slice(0, at.valueStart) + value + text.slice(at.valueEnd);
  if (!patterns.length) return text;
  const head = S.slice(0, S.lastIndexOf('}')).trimEnd();
  const comma = head.endsWith('{') || head.endsWith(',') ? '' : ',';
  return `${text.slice(0, head.length)}${comma}\n  "routes": ${value}${text.slice(head.length)}`;
}

// The hosts the config routes as custom domains; a route of any other kind stops the run.
export function routesOf(cfg, file) {
  const out = [];
  for (const r of cfg.routes ?? []) {
    if (typeof r !== 'object' || r === null || r.custom_domain !== true || typeof r.pattern !== 'string') {
      throw new Stop(1, `${file} has a route that is not a custom domain. The script manages custom-domain routes only: take the other route out, or move this site by hand.`);
    }
    out.push(r.pattern);
  }
  return out.sort();
}

// ---------------------------------------------------------------- the state file and its lock

const stateDir = (io, zone, repository) => path.join(io.home ?? homedir(), '.config', 'croftweaver', 'moves', zone, repository.replace('/', '-').toLowerCase());

function loadState(dir) {
  const f = path.join(dir, 'state.json');
  if (!existsSync(f)) return null;
  try { return JSON.parse(readFileSync(f, 'utf8')); } catch { throw new Stop(1, `${f} is not readable JSON. The script does not guess: move it away only if no move is open, and run record again.`); }
}

// Written to a temporary file and renamed, so a stop never leaves half a file.
function saveState(dir, st) {
  mkdirSync(dir, { recursive: true, mode: 0o700 });
  const f = path.join(dir, 'state.json');
  const tmp = `${f}.${process.pid}.tmp`;
  writeFileSync(tmp, JSON.stringify(st, null, 2), { mode: 0o600 });
  renameSync(tmp, f);
}

const alive = (pid) => { try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; } };

// Created exclusively; a run removes only the lock it created and never another run's. A lock
// whose process has gone (a killed run) is taken over, because the host it left may be down and
// the next run must start at once; a live process's lock is never touched. Takeovers are
// serialised by `lock.claim`, so a live lock is never moved aside, even for a moment.
export function takeLock(dir, run, say) {
  mkdirSync(dir, { recursive: true, mode: 0o700 });
  const f = path.join(dir, 'lock');
  const mine = `${process.pid}\n${randomBytes(8).toString('hex')}\n`;
  // The lock appears with its pid already in it (a hard link to a finished file), so no run sees it empty.
  const create = () => {
    const tmp = `${f}.new-${process.pid}-${randomBytes(4).toString('hex')}`;
    writeFileSync(tmp, mine, { flag: 'wx', mode: 0o600 });
    try { linkSync(tmp, f); return true; } catch (e) { if (e.code === 'EEXIST') return false; throw e; } finally { rmSync(tmp, { force: true }); }
  };
  let tookOver = null;
  if (!create()) {
    const claim = `${f}.claim`;
    try { writeFileSync(claim, `${process.pid}\n`, { flag: 'wx', mode: 0o600 }); } catch (e) {
      if (e.code !== 'EEXIST') throw e;
      let other = NaN;
      try { other = Number(readFileSync(claim, 'utf8').split('\n')[0]); } catch { /* gone, or being written */ }
      if (Number.isInteger(other) && other > 0 && !alive(other)) throw new Stop(1, `${claim} was left by a run (process ${other}) that stopped while taking over the lock. Delete that file, then run this again.`);
      throw new Stop(1, `Another run is taking over ${f}. Wait for it to end, then run this again.`);
    }
    try {
      let before = null;
      try { before = readFileSync(f, 'utf8'); } catch (e) { if (e.code !== 'ENOENT') throw e; }
      if (before !== null) {
        const pid = Number(before.split('\n')[0]);
        if (Number.isInteger(pid) && pid > 0 && alive(pid)) throw new Stop(1, `Another run (process ${pid}) holds ${f}. Wait for it to end, then run this again.`);
        rmSync(f, { force: true });
        tookOver = Number.isInteger(pid) && pid > 0 ? `process ${pid}` : 'no process named';
      }
      if (!create()) throw new Stop(1, `${f} was taken by another run while this one took over a dead run's lock. Run this again.`);
    } finally {
      rmSync(claim, { force: true });
    }
  }
  if (tookOver) say(`Took over the lock of a run that no longer exists (${tookOver}).`);
  run.release = () => {
    try { if (readFileSync(f, 'utf8') === mine) rmSync(f); } catch { /* already gone */ }
    run.release = null;
  };
}

// ---------------------------------------------------------------- reading the site and GitHub

async function readToken(root, git, env) {
  const fromEnv = (env.CLOUDFLARE_API_TOKEN ?? '').trim();
  if (fromEnv) return fromEnv;
  const file = path.join(root, '.dev.vars');
  if (!existsSync(file)) throw new Stop(1, 'No token: set CLOUDFLARE_API_TOKEN for this session, or put CLOUDFLARE_API_TOKEN=… in .dev.vars (a file git ignores). The move section says how to make it.');
  if ((await git('ls-files', '--error-unmatch', '--', '.dev.vars')).code === 0) throw new Stop(1, 'git tracks .dev.vars, so a token in it would be committed. The file was not read. Stop tracking it (git rm --cached .dev.vars) and make a new token.');
  if ((await git('check-ignore', '-q', '--', '.dev.vars')).code !== 0) throw new Stop(1, '.dev.vars is not ignored by git, so the next commit could take the token with it. The file was not read. Add .dev.vars to .gitignore, then run this again.');
  const m = /^\s*CLOUDFLARE_API_TOKEN\s*=\s*["']?([^"'\s]+)["']?\s*$/m.exec(readFileSync(file, 'utf8'));
  if (!m) throw new Stop(1, '.dev.vars has no line CLOUDFLARE_API_TOKEN=….');
  return m[1];
}

// The enabled: line of the 0.35 release notes, which reads Workers Builds' branch variable.
export const ENABLED_LINE = 'enabled: USE_ANALYTICS && (process.env.CF_PAGES_BRANCH ?? process.env.WORKERS_CI_BRANCH) === PROD_BRANCH,';

// src/config.ts at a commit: PROD_BRANCH, the analytics mode, whether analytics is on (read as
// tests/check_analytics_gate.sh reads it; null unless USE_ANALYTICS is unnamed or named in exactly
// one line of its one-line form), and whether its one enabled: line is ENABLED_LINE as it stands.
async function readSiteConfig(git, sha) {
  const r = await git('show', `${sha}:src/config.ts`);
  if (r.code !== 0) throw new Stop(1, `src/config.ts is missing at ${short(sha)}: is this a site made with the kit?`);
  const prodBranch = /^export const PROD_BRANCH = ['"]([^'"]*)['"];?/m.exec(r.stdout)?.[1];
  if (!prodBranch) throw new Stop(1, `src/config.ts at ${short(sha)} has no line "export const PROD_BRANCH = '…';".`);
  const uses = [...r.stdout.matchAll(/^export const USE_ANALYTICS = (true|false);?[ \t]*(\/\/.*)?$/gm)];
  const analyticsOn = uses.length === 1 ? uses[0][1] === 'true' : uses.length === 0 && !r.stdout.includes('USE_ANALYTICS') ? true : null;
  const enabled = r.stdout.split(/\r?\n/).filter((l) => /^\s*enabled:/.test(l));
  const enabledLine = enabled.length === 1 && enabled[0].trim() === ENABLED_LINE;
  return { prodBranch, serverMode: /^\s*mode:\s*['"]server['"]/m.test(r.stdout), analyticsOn, enabledLine };
}

// The one Workers config at a commit: a .json or .jsonc file in the root with `assets` and no
// `pages_build_output_dir` (D17).
async function readWorkersConfig(git, sha) {
  const tree = await git('ls-tree', '--name-only', sha);
  if (tree.code !== 0) throw new Stop(1, `git could not list ${short(sha)}.`);
  const found = [];
  for (const f of tree.stdout.split('\n').filter((x) => /\.jsonc?$/.test(x) && x !== 'package.json' && x !== 'package-lock.json')) {
    const t = await git('show', `${sha}:${f}`);
    let cfg;
    try { cfg = parseJsonc(t.stdout); } catch { continue; }
    if (cfg && typeof cfg === 'object' && cfg.assets !== undefined && cfg.pages_build_output_dir === undefined) found.push({ file: f, cfg, text: t.stdout });
  }
  if (found.length > 1) throw new Stop(1, `${found.length} Workers configs at ${short(sha)} (${found.map((x) => x.file).join(', ')}): a build would deploy from the other. Keep one.`);
  if (!found.length) throw new Stop(1, `No Workers config at ${short(sha)}: a .json or .jsonc file in the root with "assets" and no "pages_build_output_dir". Stage 1 of the move section is not done.`);
  if (typeof found[0].cfg.name !== 'string') throw new Stop(1, `${found[0].file} names no Worker.`);
  return found[0];
}

// GitHub's API: through `gh` when it is logged in, else without a token. `pass()` keeps a pass over
// the commits no closer than 30 seconds to the last one; the time of the last one is in the state file.
function makeGithub(io, ctx) {
  let gh; // undefined: not asked yet
  let missing = false; // gh is not installed
  let last = 0;
  const get = async (p) => {
    if (io.useGh !== false && gh === undefined) {
      const a = await ctx.run('gh', ['auth', 'status']).catch((e) => { if (e instanceof Deadline) throw e; missing = e instanceof Stop && /is not installed/.test(e.message); return { code: 1 }; });
      gh = a.code === 0;
    }
    if (gh) {
      const r = await ctx.run('gh', ['api', p]);
      if (r.code === 0) return { status: 200, body: JSON.parse(r.stdout) };
      const status = Number(/HTTP (\d{3})/.exec(r.stderr)?.[1] ?? 0);
      return { status, body: null, rate: /rate limit/i.test(r.stderr) };
    }
    const r = await ctx.siteFetch(`https://api.github.com${p}`, { headers: { accept: 'application/vnd.github+json' } });
    let body = null;
    try { body = JSON.parse(r.body.toString('utf8')); } catch { body = null; }
    return { status: r.status, body, rate: r.status === 429 || (r.status === 403 && r.headers.get('x-ratelimit-remaining') === '0') };
  };
  // The pause: a run waits it out, unless it has not the time left. A --confirm run reads no GitHub at all.
  get.pass = async () => {
    const at = ctx.state?.ghPolledAt ?? last;
    const wait = at + (io.pollMs ?? POLL_MS) - ctx.now();
    if (at && wait > 0) {
      const secs = Math.ceil(wait / 1000);
      if (wait >= ctx.clock.left()) throw new Stop(4, `GitHub is read no more than every 30 seconds, and this run has not the time left to wait. Run the same command again in ${secs} seconds.`);
      await ctx.sleep(wait);
    }
    last = ctx.now();
    if (ctx.state) { ctx.state.ghPolledAt = last; saveState(ctx.stateDir, ctx.state); }
  };
  get.missing = () => missing;
  return get;
}

// What to do about a repository GitHub does not show without a login.
const loginHint = (ctx) => (ctx.github.missing()
  ? 'gh (the GitHub command line) is not installed: get it from https://cli.github.com, run gh auth login, then run this again.'
  : 'Log in with gh (gh auth login), then run this again.');

// ---------------------------------------------------------------- what the run knows

// Step 1 of every command: the repository, the token, the zone, the site's publish model, the
// state file, the Worker's config, the Pages project and the hosts.
async function prepare(opts, io, run) {
  const env = io.env ?? process.env;
  const now = io.now ?? (() => Date.now());
  const clock = makeClock(io.runMs ?? RUN_MS, now);
  const ctx = { opts, io, clock, say: io.say, sleep: io.sleep ?? ((ms) => new Promise((r) => setTimeout(r, ms))), now };
  let cenv = childEnv(env, (env.CLOUDFLARE_API_TOKEN ?? '').trim() || null);
  ctx.run = async (cmd, args, extra = {}) => {
    try { return await (io.run ?? runProgram)(cmd, args, { cwd: extra.cwd ?? ctx.root ?? io.cwd, env: cenv, clock }); } catch (e) { throw named(e, cmd === 'gh' ? 'GitHub' : 'git', `${cmd} ${args[0]}`); }
  };
  const git = (...args) => ctx.run('git', args);
  ctx.git = git;
  // A git read of GitHub, with its own short limit: a connection that hangs (SSH to GitHub does) ends here with a plain
  // message, not at the run's deadline. The run's own deadline still wins when it comes first.
  ctx.gitNet = async (...args) => {
    const cap = io.gitNetMs ?? GIT_NET_MS;
    const sub = { left: () => Math.min(clock.left(), cap) };
    try { return await (io.run ?? runProgram)('git', args, { cwd: ctx.root ?? io.cwd, env: cenv, clock: sub }); } catch (e) {
      if (e instanceof Deadline && clock.left() > 0) throw new Stop(1, `GitHub could not be reached: git got no answer from ${ctx.repository ?? 'it'} in ${Math.round(cap / 1000)} s. Nothing was changed. Check this computer's connection to GitHub, or try again later.`);
      throw named(e, 'GitHub', `git ${args[0]}`);
    }
  };
  const gitOut = async (...args) => {
    const r = await git(...args);
    if (r.code !== 0) throw new Stop(1, `git ${args[0]} failed: ${(r.stderr || r.stdout).trim().split('\n')[0]}`);
    return r.stdout.trim();
  };
  ctx.gitOut = gitOut;

  const top = await ctx.run('git', ['rev-parse', '--show-toplevel'], { cwd: io.cwd });
  if (top.code !== 0) throw new Stop(1, "This folder is not a git repository. Run the script in the site's folder.");
  ctx.root = top.stdout.trim();
  run.root = ctx.root;
  const remote = await git('config', '--get', 'remote.origin.url');
  const gh = remote.code === 0 ? githubRepo(remote.stdout) : null;
  if (!gh) throw new Stop(1, 'The remote "origin" is not a repository on GitHub, so Cloudflare cannot build from it.');
  ctx.repository = `${gh.owner}/${gh.repo}`;
  ctx.gh = gh;

  // The site's folder holds only the status page, in a folder git ignores. Written first.
  const runDir = path.join(ctx.root, 'move-run');
  mkdirSync(runDir, { recursive: true });
  const ignore = path.join(runDir, '.gitignore');
  if (!existsSync(ignore)) writeFileSync(ignore, '*\n');
  if ((await gitOut('ls-files', '--', 'move-run'))) throw new Stop(1, 'git tracks a file in move-run/. Nothing there may be committed: run git rm --cached on it, then run this again.');
  ctx.runDir = runDir;

  const token = await readToken(ctx.root, git, env);
  cenv = childEnv(env, token);
  ctx.token = token;
  ctx.gate = { hosts: new Set(), cnames: new Map(), workerDomainIds: new Map() };
  ctx.assumedPages = new Set();
  const apiOpts = { clock, requestMs: io.requestMs ?? REQUEST_MS };
  ctx.api = makeApi(io.apiFetch ?? globalThis.fetch, token, ctx.gate, apiOpts);
  ctx.allowed = new Set(['api.github.com']);
  ctx.siteFetch = makeSiteFetch(io.siteFetch ?? globalThis.fetch, ctx.allowed, apiOpts);
  ctx.github = makeGithub(io, ctx);
  ctx.report = run;

  const lsStarted = ctx.gitNet('ls-remote', '--heads', 'origin'); // beside the token check: neither needs the other
  lsStarted.catch(() => {}); // awaited below; a stop before that must not leave it unhandled
  let zone;
  try { zone = await checkToken(ctx); } catch (e) {
    if (!(e instanceof Stop) || opts.cmd !== 'check') throw e;
    throw await withStageOne(ctx, e, lsStarted); // a refused token would hide the stage 1 gaps
  }
  await readBranches(ctx, lsStarted);

  // The state file: only the one for this zone and repository, and the same site.
  ctx.stateDir = stateDir(io, zone.name, ctx.repository);
  if (opts.cmd !== 'check') takeLock(ctx.stateDir, run, io.say); // before the state is read: every decision below depends on it
  const st = loadState(ctx.stateDir);
  run.stateRead = true;
  run.state = st; // a stop later in prepare still knows the state
  ctx.state = st;
  if (st && (st.zone?.id !== zone.id || st.repository !== ctx.repository)) {
    throw new Stop(1, `${path.join(ctx.stateDir, 'state.json')} belongs to another site (zone ${st.zone?.name}, repository ${st.repository}). The script reads only the file for this one: look at it, and move it away if it is stale.`);
  }
  ctx.open = Boolean(st?.open);

  // The Worker's config: at the frozen commit of an open move or a recorded one, else at the live tip.
  ctx.sha = st && (st.open || st.recording?.status === 'done') && !['record', 'check'].includes(opts.cmd) ? st.frozen : ctx.tip;
  if (ctx.sha !== ctx.tip) await ctx.haveCommit(ctx.sha, 'the frozen commit');
  let wc;
  try { wc = await readWorkersConfig(git, ctx.sha); } catch (e) {
    if (!(e instanceof Stop) || ctx.open) throw e; // an open move's checks are lifted: only this one stops it
    const gaps = await stageOneGaps(git, ctx.sha);
    throw gaps.length ? gapsStop(ctx.sha, gaps) : e;
  }
  ctx.worker = wc.cfg.name;
  ctx.configFile = wc.file;
  ctx.workerConfig = wc;
  ctx.gate.worker = ctx.worker;
  if (wc.cfg.account_id && wc.cfg.account_id !== ctx.account.id) throw new Stop(1, `${wc.file} names account ${wc.cfg.account_id}, and the zone is in ${ctx.account.id}.`);
  if (!/^[a-z0-9][a-z0-9-]{0,62}$/.test(ctx.worker)) throw new Stop(1, `The Worker name "${ctx.worker}" is not one this script handles.`);

  // The Pages project: the account's project whose source is this repository.
  const projects = await allPages(ctx.api, `/accounts/${ctx.account.id}/pages/projects`);
  if (!projects.items) throw new Stop(1, `Cloudflare refused to list the account's Pages projects: ${cfWords(projects.r)}. The token needs Cloudflare Pages Edit.`);
  const mine = projects.items.filter((p) => p.source?.type === 'github'
    && String(p.source.config?.owner).toLowerCase() === gh.owner.toLowerCase() && String(p.source.config?.repo_name).toLowerCase() === gh.repo.toLowerCase());
  if (mine.length > 1) throw new Stop(1, `${mine.length} Pages projects are built from ${ctx.repository}: ${mine.map((p) => p.name).join(', ')}. The script moves a site with one.`);
  if (!mine.length) {
    const direct = projects.items.filter((p) => !p.source && p.domains?.some((d) => d === zone.name || d.endsWith(`.${zone.name}`)));
    if (direct.length) throw new Stop(1, `The Pages project ${direct[0].name} serves this zone but is a Direct Upload project, not built from Git. The script moves Git-connected projects only: move this site by hand.`);
    throw new Stop(1, `No Pages project is built from ${ctx.repository} in account ${ctx.account.name}. There is nothing for the script to move.`);
  }
  ctx.gate.project = mine[0].name;
  const one = await ctx.api('GET', `/accounts/${ctx.account.id}/pages/projects/${mine[0].name}`);
  if (!ok(one) || !one.body?.result || !Array.isArray(one.body.result.domains) || typeof one.body.result.subdomain !== 'string') {
    throw new Stop(1, `Cloudflare did not return the Pages project ${mine[0].name} with its domains and address: ${cfWords(one)}.`);
  }
  ctx.project = one.body.result;
  ctx.gate.subdomain = ctx.project.subdomain;
  if (st && (st.pages?.name !== ctx.project.name || st.worker !== ctx.worker)) {
    throw new Stop(1, `${path.join(ctx.stateDir, 'state.json')} is for the Pages project ${st.pages?.name} and the Worker ${st.worker}; this site's are ${ctx.project.name} and ${ctx.worker}. The script reads only the file for this site.`);
  }

  // The hosts: an open move keeps its own; else the project's custom domains in the zone.
  const inZone = (d) => d === zone.name || d.endsWith(`.${zone.name}`);
  ctx.hosts = ctx.open ? [...st.hosts] : ctx.project.domains.filter((d) => d !== ctx.project.subdomain && inZone(d)).sort();
  for (const h of ctx.hosts) if (!HOSTNAME.test(h)) throw new Stop(1, `The host "${h}" is not a name this script handles.`);
  for (const h of ctx.hosts) if (!inZone(h)) throw new Stop(1, `The host "${h}" is not in the zone ${zone.name}. The script touches hosts of that zone only.`);
  for (const h of ctx.hosts) { ctx.gate.hosts.add(h); ctx.allowed.add(h); }
  if (!ctx.hosts.length) throw new Stop(1, `The Pages project ${ctx.project.name} has no custom domain in ${zone.name}: there is nothing to move.`);
  return ctx;
}

// SITE.url in src/config.ts at the local HEAD, or null (missing, unreadable, the template's own).
// It chooses the words of a zone refusal only, never the zone.
async function siteAddress(git) {
  const r = await git('show', 'HEAD:src/config.ts');
  if (r.code !== 0) return null;
  const site = /^export const SITE\s*=\s*\{([^]*?)^\}/m.exec(r.stdout)?.[1];
  if (site === undefined || /[{}`]/.test(site)) return null; // only the template's flat form; a nested or one-line SITE, or a template string, gives the old words
  const url = /^[ \t]*url:[ \t]*['"]([^'"\n]+)['"]/m.exec(site)?.[1];
  let host;
  try { host = new URL(url).hostname.toLowerCase().replace(/\.$/, ''); } catch { return null; }
  return host && host !== 'example.com' ? { host } : null;
}

// A refused token: what was found, the permissions that reach (when more than one zone does), and
// what to make, by the address src/config.ts gives. `reaching` is empty when no zone has DNS Edit.
async function zoneRefusal(ctx, zones, reaching) {
  const lines = reaching.length
    ? [`This token can reach the DNS or settings of ${reaching.length} zones (${reaching.map((z) => z.name).join(', ')}).`,
      `Cloudflare lists these permissions in them: ${[...new Set(reaching.flatMap((z) => z.permissions.filter((p) => /^#(dns_records|zone_settings):/.test(p))
        .map((p) => (/^[a-z0-9_:#.-]+$/.test(p) ? p : '(a permission this script does not show)'))))].join(', ')}.`]
    : [];
  const a = await siteAddress(ctx.git);
  const own = a && zones.map((z) => z.name).filter((n) => a.host === n || a.host.endsWith(`.${n}`)).sort((x, y) => y.length - x.length)[0];
  if (a && !own && /\.(pages|workers)\.dev$/.test(a.host)) {
    lines.push(`${reaching.length ? '' : 'This token cannot edit the DNS of any zone it lists. '}src/config.ts gives the address https://${a.host}, which is not a domain of its own. If the site has no domain yet, it launches first, as CLOUDFLARE_FIRST_DEPLOY.md says (the kit has no guide yet for launching straight onto a Worker); if it has one, put it in SITE.url.`);
  } else if (a && !own) {
    lines.push(`${reaching.length ? '' : 'This token cannot edit the DNS of any zone it lists. '}src/config.ts gives the address ${a.host}, and no zone this token lists is that domain or a parent of it. The domain may not be on Cloudflare yet, or it is in an account this token cannot see. If it is not on Cloudflare yet, put it there first. Then make the token with Zone Read and DNS Edit, Zone Resources set to it.`);
  } else if (reaching.length) {
    lines.push(`Make one limited to ${own ?? "the site's own zone"} (Zone Resources: ${own ? 'that one domain' : 'your one domain'}). A token narrowed just now may need a few minutes before Cloudflare shows the change.`);
  } else {
    lines.push(`This token cannot edit the DNS of any zone it lists. Make one with the permissions Zone Read and DNS Edit, with Zone Resources set to ${own ?? "the site's own domain"}.`);
  }
  return new Stop(1, ...lines);
}

// The token: verified, a week away at most, with DNS reach in one zone. Returns that zone.
async function checkToken(ctx) {
  const verify = await ctx.api('GET', '/user/tokens/verify');
  if (verify.status === 0) throw new Stop(1, `Cloudflare did not answer the token check (${verify.error ?? 'no answer'}). That is the connection, not the token: check this computer's connection, then run this again.`);
  if (!ok(verify) || verify.body?.result?.status !== 'active') throw new Stop(1, `Cloudflare did not accept the token (${ok(verify) ? `its status is ${verify.body?.result?.status}` : cfWords(verify)}). It may be revoked, or have ended: make a new one from the same link.`);
  const ends = Date.parse(verify.body.result.expires_on ?? '');
  if (!Number.isFinite(ends)) throw new Stop(1, 'This token has no end date. Make one with an end date a week out, and delete this one.');
  if (ends - ctx.now() > MAX_TOKEN_MS) throw new Stop(1, `This token ends on ${verify.body.result.expires_on.slice(0, 10)}. A week at most: make one that ends within the week, and delete this one.`);
  ctx.tokenLeftMs = ends - ctx.now();
  if (ctx.tokenLeftMs <= 0) throw new Stop(1, 'This token has ended. Make a new one from the same link.');
  const zones = await allPages(ctx.api, '/zones', 50, { totals: true });
  if (!zones.items) throw new Stop(1, `Cloudflare refused to list the token's zones (${cfWords(zones.r)}). Make a new token from the link.`);
  // The Workers permission lists every zone of the account, so the zone count says nothing. The site's
  // zone is the one whose `permissions` reach DNS or zone settings; it must be exactly one, with DNS Edit.
  for (const z of zones.items) if (!Array.isArray(z.permissions)) throw new Stop(1, `Cloudflare did not say what this token may do in the zone ${z.name}. Make a new token from the link.`);
  const reaching = zones.items.filter((z) => z.permissions.some((p) => /^#(dns_records|zone_settings):/.test(p)));
  if (reaching.length > 1) throw await zoneRefusal(ctx, zones.items, reaching);
  const zone = reaching[0];
  if (!zone?.permissions.includes('#dns_records:edit')) throw await zoneRefusal(ctx, zones.items, []);
  if (zone.status !== 'active') throw new Stop(1, `The zone ${zone.name} is ${zone.status} on Cloudflare, not active.`);
  if (!zone.account?.id) throw new Stop(1, 'Cloudflare did not say which account the zone belongs to.');
  if (!/^[a-z0-9.-]+$/.test(zone.name)) throw new Stop(1, `The zone name "${zone.name}" is not one this script handles.`);
  ctx.zone = zone;
  ctx.account = { id: zone.account.id, name: zone.account.name ?? zone.account.id };
  Object.assign(ctx.gate, { accountId: ctx.account.id, zoneId: zone.id, zoneName: zone.name });
  return zone;
}

// The branches on GitHub and the publish model, as the setup script reads them.
async function readBranches(ctx, lsStarted) {
  const { git } = ctx;
  const lsAll = await lsStarted;
  if (lsAll.code !== 0) throw new Stop(1, `git could not read the branches of ${ctx.repository} on GitHub. Check that this computer can reach it, then run again.`);
  const heads = new Map(lsAll.stdout.split('\n').map((l) => l.split('\t')).filter((p) => p.length === 2).map(([s, r]) => [r.replace(/^refs\/heads\//, ''), s]));
  const mainSha = heads.get('main');
  if (!mainSha) throw new Stop(1, `${ctx.repository} has no branch main on GitHub.`);
  ctx.haveCommit = async (sha, where) => {
    if ((await git('cat-file', '-e', `${sha}^{commit}`)).code !== 0) throw new Stop(1, `The head of ${where} on GitHub (${short(sha)}) is not in this folder yet. Run git fetch origin, then run this again.`);
  };
  await ctx.haveCommit(mainSha, 'main');
  const { prodBranch } = await readSiteConfig(git, mainSha);
  if (prodBranch === 'main' && !heads.has('production')) ctx.twoStage = false;
  else if (prodBranch === 'production' && heads.has('production')) ctx.twoStage = true;
  else throw new Stop(1, `The two signs of the publish model disagree: src/config.ts says PROD_BRANCH is "${prodBranch}", and GitHub has ${heads.has('production') ? 'a' : 'no'} branch production.`);
  ctx.prodBranch = prodBranch;
  ctx.tip = heads.get(prodBranch);
  ctx.mainSha = mainSha;
  await ctx.haveCommit(ctx.tip, prodBranch);
  if (ctx.twoStage && ctx.mainSha !== ctx.tip) ctx.mainDiffers = true;
}

// check only: a refused token comes with the stage 1 gaps at the live tip, which it would hide.
async function withStageOne(ctx, stop, lsStarted) {
  let gaps;
  try {
    await readBranches(ctx, lsStarted);
    gaps = await stageOneGaps(ctx.git, ctx.tip);
  } catch (e) {
    if (!(e instanceof Stop)) throw e;
    return new Stop(stop.code, ...stop.lines, 'Stage 1 could not be checked:', ...e.lines);
  }
  return gaps.length ? new Stop(stop.code, ...stop.lines, 'If no move is open, stage 1 is not done either:', ...gaps.map((g) => `- ${g}`)) : stop;
}

// What Cloudflare says now, for the hosts: the project's domains, the Worker's domains, and each
// host's own records, asked for by name (one page, whatever the zone holds). The ids a gated write
// may name are those of this read.
async function readLive(ctx) {
  const A = `/accounts/${ctx.account.id}`;
  const [pr, pd, wd, ...dns] = await Promise.all([
    ctx.api('GET', `${A}/pages/projects/${ctx.project.name}`),
    ctx.api('GET', `${A}/pages/projects/${ctx.project.name}/domains`),
    ctx.api('GET', `${A}/workers/domains`),
    ...ctx.hosts.map((h) => allPages(ctx.api, `/zones/${ctx.zone.id}/dns_records?name=${h}`, 100)),
  ]);
  if (!ok(pr) || !Array.isArray(pr.body?.result?.domains)) throw new Stop(1, `Cloudflare did not return the Pages project: ${cfWords(pr)}.`);
  if (!ok(pd) || !Array.isArray(pd.body?.result)) throw new Stop(1, `Cloudflare did not list the Pages project's domains: ${cfWords(pd)}.`);
  const info = pd.body.result_info; // the answer is paged (20 a page); the script reads page 1 only and does not decide from part of a list
  if (!info || !Number.isInteger(info.total_count) || !Number.isInteger(info.total_pages)) throw new Stop(1, "Cloudflare's list of the Pages project's domains did not say how many domains the project has. The script does not decide from a list it cannot size: do the move in the Cloudflare dashboard.");
  if (info.total_pages > 1) throw new Stop(1, `The Pages project has more than ${info.per_page ?? 20} domains. The script reads one page of them and does not decide from part of a list: do the move in the Cloudflare dashboard.`);
  // One page: the list must hold every domain the answer counts, and its own count must match what it holds.
  const held = pd.body.result.length;
  if (held !== info.total_count || (info.count !== undefined && info.count !== held)) throw new Stop(1, `Cloudflare's list of the Pages project's domains holds ${held} domains but says it counts ${info.count ?? 'none'} on this page and ${info.total_count} in all. The script does not decide from a list that disagrees with itself: do the move in the Cloudflare dashboard.`);
  if (!ok(wd) || !Array.isArray(wd.body?.result)) throw new Stop(1, `Cloudflare did not list the Worker domains: ${cfWords(wd)}. The token needs the Workers permission the move section names.`);
  const records = [];
  for (const [i, d] of dns.entries()) {
    const h = ctx.hosts[i];
    if (!d.items) throw new Stop(1, `Cloudflare did not list the records named ${h}: ${cfWords(d.r)}.`);
    const stray = d.items.find((r) => String(r.name).toLowerCase() !== h);
    if (stray) throw new Stop(1, `Cloudflare's list of the records named ${h} holds a record named ${stray.name}: the name filter was not applied, and the script does not decide from an answer it cannot trust. Nothing was changed.`);
    if (d.requests > 1) throw new Stop(1, `${h} has more than 100 DNS records. The script reads one page of a host's records and does not decide from part of a list: do the move by hand in the Cloudflare dashboard.`);
    records.push(...d.items);
  }
  ctx.project = pr.body.result;
  // The project's own `domains` holds a domain only once it is active, minutes after the add; its domain list shows it at once, as initializing, then pending, then active.
  const pagesDomains = new Map(pd.body.result.map((d) => [String(d.name).toLowerCase(), String(d.status ?? 'unknown')]));
  ctx.gate.cnames.clear();
  ctx.gate.workerDomainIds.clear();
  for (const r of records) if (r.type === 'CNAME' && ctx.gate.hosts.has(r.name)) ctx.gate.cnames.set(r.id, { name: r.name, content: String(r.content).toLowerCase() });
  const mineWd = wd.body.result.filter((d) => d.service === ctx.worker);
  for (const d of mineWd) if (ctx.gate.hosts.has(d.hostname)) ctx.gate.workerDomainIds.set(d.id, d.hostname);
  if (ctx.report) { // what this run saw, for the status page
    ctx.report.where = Object.fromEntries(ctx.hosts.map((h) => {
      const pages = pagesDomains.has(h) || ctx.assumedPages.has(h);
      const worker = mineWd.some((d) => d.hostname === h);
      return [h, pages && worker ? 'both' : pages ? 'pages' : worker ? 'worker' : 'neither'];
    }));
  }
  return { project: ctx.project, pagesDomains, workerDomains: wd.body.result, mineWd, records };
}

function hostState(ctx, live, h) {
  const other = live.workerDomains.find((d) => d.hostname === h && d.service !== ctx.worker);
  if (other) throw new Stop(1, `${h} is attached to another Worker (${other.service}). The script does not touch it.`);
  // Cloudflare said "already added" this run: the domain is on Pages whichever list lags.
  const assumed = !live.pagesDomains.has(h) && ctx.assumedPages.has(h);
  const pages = live.pagesDomains.has(h) || assumed;
  const pagesStatus = live.pagesDomains.get(h) ?? (assumed ? 'unknown' : null);
  const worker = live.mineWd.some((d) => d.hostname === h);
  const recs = live.records.filter((r) => r.name === h && ADDRESS_TYPES.includes(r.type));
  const cname = recs.find((r) => r.type === 'CNAME' && String(r.content).toLowerCase() === ctx.project.subdomain);
  return { pages, pagesStatus, pagesActive: pagesStatus === 'active', worker, recs, cname, where: pages && worker ? 'both' : pages ? 'pages' : worker ? 'worker' : 'neither' };
}

// Where the move ends: on the Worker, or on Pages with its CNAME and an active domain.
const settled = (hs, toWorker) => (toWorker ? hs.where === 'worker' : hs.where === 'pages' && Boolean(hs.cname) && hs.pagesActive);

// Cloudflare's answer to adding a Pages domain that the project already holds.
const ALREADY_ADDED = 8000018;

// A Pages domain that is listed but not active yet says so next to where it is.
// Statuses Cloudflare shows while it brings a Pages domain up; any other that is not active (blocked, error, deactivated) is a failure.
const COMING_UP = ['initializing', 'pending'];

const notActive = (hs) => (hs.where === 'pages' && !hs.pagesActive ? ` (Cloudflare shows the domain as ${hs.pagesStatus})` : '');

const WHERE_WORDS = { pages: 'on Pages', worker: 'on the Worker', neither: 'on neither (down)', both: 'on both (inconsistent)' };

// ---------------------------------------------------------------- the refusals of a first move

// What stage 1 still lacks at a commit, one line each: the Workers config, functions/, public/_worker.js
// analytics server mode and, with analytics on, the 0.35 enabled: line as written. Read from git only, so a run lists all of them at once.
async function stageOneGaps(git, sha) {
  const gaps = [];
  const asLines = async (fn) => { try { await fn(); } catch (e) { if (!(e instanceof Stop)) throw e; gaps.push(...e.lines); } };
  await asLines(() => readWorkersConfig(git, sha));
  const tree = await git('ls-tree', '-r', '--name-only', sha);
  if (tree.code !== 0) throw new Stop(1, `git could not list ${short(sha)}.`);
  const files = tree.stdout.split('\n');
  const fns = files.filter((f) => f.startsWith('functions/') && f !== 'functions/_middleware.ts');
  if (fns.length) gaps.push(`${short(sha)} holds ${fns.slice(0, 3).join(', ')}${fns.length > 3 ? ' and more' : ''} in functions/. The Worker would not run that code. Stage 1 of the move section takes functions/go/ out.`);
  if (files.includes('public/_worker.js')) gaps.push(`${short(sha)} holds public/_worker.js: code the Worker would not run.`);
  await asLines(async () => {
    const cfg = await readSiteConfig(git, sha);
    if (cfg.serverMode) gaps.push('This site counts visits in analytics server mode, which needs Pages Functions. The script moves script-mode sites only.');
    if (cfg.analyticsOn === null) gaps.push(`src/config.ts at ${short(sha)} names USE_ANALYTICS, but not as exactly one line "export const USE_ANALYTICS = true;" or "= false;", so the script cannot tell whether analytics is on.`);
    else if (cfg.analyticsOn && !cfg.enabledLine) gaps.push(`Analytics is on, but src/config.ts at ${short(sha)} lacks this enabled: line, exactly as written: ${ENABLED_LINE} Workers Builds sets WORKERS_CI_BRANCH, not CF_PAGES_BRANCH; without that line the Worker's pages have no analytics. The script compares the text, so use this line even if yours works.`);
  });
  return gaps;
}
// One gap stops as it always has; more are listed under one line.
const gapsStop = (sha, gaps) => (gaps.length === 1 ? new Stop(1, gaps[0])
  : new Stop(1, `Stage 1 of the move section is not done at ${short(sha)}:`, ...gaps.map((g) => `- ${g}`)));

async function firstMoveRefusals(ctx, live) {
  const mineOnWorker = live.mineWd;
  if (mineOnWorker.length) throw new Stop(1, `The Worker ${ctx.worker} already has a domain (${mineOnWorker.map((d) => d.hostname).join(', ')}). A first move needs a Worker with none: take it off by hand or finish the move it belongs to.`);
  const gaps = await stageOneGaps(ctx.git, ctx.sha);
  if (gaps.length) throw gapsStop(ctx.sha, gaps);
}

// ---------------------------------------------------------------- GitHub and builds

async function tipOf(ctx, branch) {
  const r = await ctx.gitNet('ls-remote', 'origin', `refs/heads/${branch}`);
  const sha = r.stdout.split('\t')[0].trim();
  if (r.code !== 0 || !/^[0-9a-f]{40}$/.test(sha)) throw new Stop(1, `git could not read ${branch} on GitHub.`);
  return sha;
}

// Every check run of a commit, all pages of them.
async function checkRunsOf(ctx, sha) {
  const all = [];
  for (let page = 1; page <= 50; page++) {
    const r = await ctx.github(`/repos/${ctx.repository}/commits/${sha}/check-runs?per_page=100&page=${page}`);
    if (r.rate) throw new Stop(1, `GitHub's rate limit is used up. ${loginHint(ctx)}`);
    if (r.status === 404) throw new Stop(1, `GitHub does not show ${ctx.repository}'s check runs without a login: the repository is private. ${loginHint(ctx)}`);
    if (r.status !== 200 || !Array.isArray(r.body?.check_runs) || !Number.isInteger(r.body.total_count)) throw new Stop(1, `GitHub's check runs of ${short(sha)} could not be read (HTTP ${r.status}).`);
    all.push(...r.body.check_runs);
    if (all.length >= r.body.total_count) return all;
    if (!r.body.check_runs.length) throw new Stop(1, `GitHub's check runs of ${short(sha)} ended at ${all.length} of ${r.body.total_count}; the script does not decide from part of a list.`);
  }
  throw new Stop(1, `${short(sha)} has more than 5000 check runs; the script does not decide from part of a list.`);
}

// The commits from `from` to the tip, from the local clone. After a passed move (`newest`) only the
// newest ones: older builds are done.
async function rangeOf(ctx, from, tip, newest) {
  const since = tip === from ? [] : (await ctx.gitOut('rev-list', ...(newest ? ['-n', String(MAX_COMMITS)] : []), `${from}..${tip}`)).split('\n').filter(Boolean);
  if (!newest && since.length > MAX_COMMITS) throw new Stop(1, `${since.length} commits lie between the frozen commit and ${short(tip)}; the freeze was not kept. Stop and look.`);
  return [from, ...since];
}

// The builds that would change what the Worker or the domains serve, still unfinished: a Pages
// production deployment, or a Workers Builds check run on a commit from `from` to the tip. Where
// any of those commits has a Workers Builds run, Builds is connected and a pushed branch tip
// (`tips`) without one is unfinished; a commit that was never pushed has none, and is not waited for.
// Answers { list, range, total, newest }: what is unfinished, the commits that were looked at, and
// the deployments' count and newest id, which a plain run keeps for the confirm run to compare.
// Every page of deployments is read, and every commit's check runs, several at a time: no capture
// shows that the first page holds the newest, and one after another they would use the run up.
async function unfinishedBuilds(ctx, from, tip, { newest = false, tips = [] } = {}) {
  const out = [];
  await ctx.github.pass();
  const dep = await allPages(ctx.api, `/accounts/${ctx.account.id}/pages/projects/${ctx.project.name}/deployments`, null, { totals: true, width: READ_WIDTH });
  if (!dep.items) throw new Stop(1, `Cloudflare did not list the project's deployments: ${cfWords(dep.r)}.`);
  for (const d of dep.items) if (d.environment === 'production' && running(d)) out.push(`Pages is building ${short(d.deployment_trigger?.metadata?.commit_hash ?? '')}`);
  const range = await rangeOf(ctx, from, tip, newest);
  const runs = new Map(); // commit → its Workers Builds check runs
  const all = await pool(range, READ_WIDTH, (sha) => checkRunsOf(ctx, sha));
  range.forEach((sha, i) => runs.set(sha, all[i].filter((c) => c.app?.slug === 'cloudflare-workers-and-pages' && c.name === `Workers Builds: ${ctx.worker}`)));
  const connected = [...runs.values()].some((b) => b.length > 0);
  for (const [sha, builds] of runs) {
    if (sha !== from && connected && tips.includes(sha) && !builds.length) out.push(`Workers Builds has not reported on ${short(sha)} yet`);
    for (const c of builds) if (c.status !== 'completed') out.push(`Workers Builds is building ${short(sha)}`);
  }
  return { list: out, range, total: dep.total, newest: dep.items[0]?.id ?? null };
}

// A --confirm run reads page 1 of the deployments only: their count and the newest id, to compare
// with what the plain run saw. Answers { total, newest } or { problem }.
async function lightDeployments(ctx) {
  const r = await ctx.api('GET', `/accounts/${ctx.account.id}/pages/projects/${ctx.project.name}/deployments?page=1`);
  if (!ok(r)) return { problem: `Cloudflare did not list the project's deployments: ${cfWords(r)}` };
  if (!Array.isArray(r.body?.result) || !Number.isInteger(r.body?.result_info?.total_count)) return { problem: "Cloudflare's list of the project's deployments does not say how many there are" };
  return { total: r.body.result_info.total_count, newest: r.body.result[0]?.id ?? null };
}

// ---------------------------------------------------------------- the Worker's version

async function workerVersion(ctx) {
  const A = `/accounts/${ctx.account.id}`;
  const [dep, sub] = await Promise.all([ctx.api('GET', `${A}/workers/scripts/${ctx.worker}/deployments`), ctx.api('GET', `${A}/workers/subdomain`)]);
  if (!ok(dep)) throw new Stop(1, `Cloudflare did not return the Worker's deployments: ${cfWords(dep)}. Is the Worker ${ctx.worker} deployed?`);
  const latest = dep.body.result?.deployments?.[0];
  const v = latest?.versions ?? [];
  if (v.length !== 1 || v[0].percentage !== 100 || !/^[0-9a-f-]{36}$/.test(v[0].version_id)) throw new Stop(1, `The Worker ${ctx.worker}'s live deployment is not one version at 100%. The script reads only that.`);
  const subdomain = sub.body?.result?.subdomain;
  if (!ok(sub) || !/^[a-z0-9-]+$/.test(subdomain ?? '')) throw new Stop(1, `Cloudflare did not return the account's workers.dev subdomain: ${cfWords(sub)}.`);
  const host = `${v[0].version_id.slice(0, 8)}-${ctx.worker}.${subdomain}.workers.dev`;
  ctx.allowed.add(host);
  return { id: v[0].version_id, host };
}

// ---------------------------------------------------------------- fetching and comparing the site

// Headers compared: those the site's _headers sets, x-robots-tag, strict-transport-security and
// access-control-allow-origin; nel and report-to by presence only.
export function headerNames(headersText) {
  const names = new Set(['x-robots-tag', 'strict-transport-security', 'nel', 'report-to', 'access-control-allow-origin']);
  for (const line of (headersText ?? '').split('\n')) {
    const m = /^[ \t]+([A-Za-z0-9-]+)[ \t]*:/.exec(line);
    if (m) names.add(m[1].toLowerCase());
  }
  for (const n of NEVER_COMPARED) names.delete(n);
  return [...names].sort();
}

function walk(dir, base = '') {
  const out = [];
  for (const e of readdirSync(path.join(dir, base), { withFileTypes: true })) {
    const rel = base ? `${base}/${e.name}` : e.name;
    if (e.isDirectory()) out.push(...walk(dir, rel));
    else out.push(rel);
  }
  return out;
}

// Every address the site answers, from the built dist/: each file, the other forms of each page,
// the sources of the plain redirects, and one that does not exist.
export function pathList(dist) {
  const files = walk(dist);
  const set = new Set([NOT_THERE]);
  const enc = (p) => p.split('/').map(encodeURIComponent).join('/');
  for (const f of files) {
    if (['_headers', '_redirects', '_routes.json', '_worker.js', '.assetsignore'].includes(f)) continue;
    const p = `/${enc(f)}`;
    set.add(p);
    if (f === 'index.html') { set.add('/'); } else if (f.endsWith('/index.html')) {
      const dir = `/${enc(f.slice(0, -'/index.html'.length))}`;
      set.add(dir); set.add(`${dir}/`);
    } else if (f.endsWith('.html')) {
      const bare = p.slice(0, -'.html'.length);
      set.add(bare); set.add(`${bare}/`);
    }
  }
  if (existsSync(path.join(dist, '_redirects'))) {
    for (const line of readFileSync(path.join(dist, '_redirects'), 'utf8').split('\n')) {
      const from = line.trim().split(/\s+/)[0];
      if (from && !from.startsWith('#') && from.startsWith('/') && !/[*:]/.test(from)) set.add(from);
    }
  }
  if (set.size > MAX_PATHS) throw new Stop(1, `The site answers ${set.size} addresses; the script records at most ${MAX_PATHS}.`);
  return [...set].sort();
}

// One address, recorded: status, media type, redirect target, body hash and the compared headers.
// build.txt and build-state.txt also keep their commit line.
async function fetchEntry(ctx, base, p, names) {
  const r = await ctx.siteFetch(`${base}${p}`);
  if (r.status === 0) return { s: 0, err: r.error };
  const hd = {};
  for (const n of names) {
    const v = r.headers.get(n);
    hd[n] = n === 'nel' || n === 'report-to' ? (v === null ? null : 'present') : v;
  }
  const e = { s: r.status, t: (r.headers.get('content-type') ?? '').split(';')[0].trim().toLowerCase() || null, l: r.headers.get('location'), h: sha256(r.body), hd };
  if (BUILD_FILES.includes(p)) e.c = r.body.toString('utf8').split('\n')[0].trim();
  return e;
}

// Addresses that got no answer are asked for again in the next run, MAX_RETRIES times at most;
// after that they count as differences. Answers how many are to be asked for again.
function unanswered(bag, lists) {
  const n = lists.reduce((a, l) => a + Object.values(l).filter((e) => e.s === 0).length, 0);
  if (!n || (bag.retried ?? 0) >= MAX_RETRIES) return 0;
  bag.retried = (bag.retried ?? 0) + 1;
  return n;
}

// The first error stops handing out addresses; the calls already sent are waited for, then the state
// is saved, so a stop at the deadline can say how many answers the saved state holds.
async function fetchAll(ctx, base, paths, names, into, save) {
  const todo = paths.filter((p) => !into[p] || into[p].s === 0);
  let n = 0;
  let failed = null;
  const worker = async () => {
    while (!failed && todo.length) {
      const p = todo.shift();
      try {
        into[p] = await fetchEntry(ctx, base, p, names);
        if (++n % 40 === 0) save();
      } catch (e) { failed ??= e; return; }
    }
  };
  await Promise.all(Array.from({ length: 6 }, worker));
  save();
  if (failed instanceof Deadline) failed.kept = { n: paths.filter((p) => into[p] && into[p].s !== 0).length, of: paths.length, host: new URL(base).hostname };
  if (failed) throw failed;
}

// The differences between what a platform answered when recorded (`was`) and now. `change` says the
// platform changed (Pages to Worker); `onVersion` that `now` is the Worker's version URL, not a
// domain. A known difference carries its reason; anything else is unknown.
export function compare(was, now, { change, onVersion, expect }) {
  const diffs = [];
  const add = (p, field, a, b, known) => diffs.push({ path: p, field, expected: a, got: b, known: known ?? null });
  for (const p of Object.keys(was)) {
    const a = was[p];
    const b = now[p];
    if (!b || b.s === 0) { add(p, 'answer', 'an answer', b?.err ?? 'none'); continue; }
    const build = BUILD_FILES.includes(p); // a build file's body names the build; its commit line stands for it
    if (build && b.s === 200 && b.c !== expect) add(p, 'commit line', expect, b.c);
    if (a.s !== b.s) {
      add(p, 'status', a.s, b.s, change && a.s === 308 && b.s === 307 && a.l === b.l ? '307 where Pages answers 308' : null);
    }
    if (a.l !== b.l) add(p, 'Location', a.l, b.l);
    // Seen once: Pages sends text/plain "Redirecting to <Location>" with a redirect, the Worker an empty body and no media type. Any other Pages body or type stays unknown.
    const sameRedirect = change && REDIRECTS.includes(a.s) && REDIRECTS.includes(b.s) && Boolean(a.l) && a.l === b.l && a.t === 'text/plain' && a.h === pagesRedirectBody(a.l) && b.h === EMPTY_BODY;
    if (a.t !== b.t) add(p, 'media type', a.t, b.t, change && a.t === 'application/javascript' && b.t === 'text/javascript' ? 'text/javascript where Pages sends application/javascript' : sameRedirect && b.t === null ? 'Pages sends a short text with a redirect; the Worker sends none' : null);
    if (!build && a.h !== b.h) add(p, 'body', a.h, b.h, change && p.endsWith('.avif') ? 'AVIF output differs by build machine' : sameRedirect ? 'Pages sends a short text with a redirect; the Worker sends none' : null);
    for (const n of Object.keys(a.hd ?? {})) {
      const x = a.hd[n];
      const y = b.hd?.[n] ?? null;
      if (x === y) continue;
      let known = null;
      if (onVersion && ZONE_HEADERS.includes(n) && y === null) known = 'the version URL has no zone headers';
      if (onVersion && (n === 'nel' || n === 'report-to') && x === null && y !== null) known = "Cloudflare's workers.dev zone adds NEL to the version URL; the domain's zone setting is checked by after";
      if (onVersion && n === 'x-robots-tag' && /noindex/i.test(y ?? '')) known = 'the version URL is noindex';
      if (change && n === 'access-control-allow-origin' && x !== null && y === null) known = 'Pages sends access-control-allow-origin; the Worker does not';
      add(p, `header ${n}`, x, y, known);
    }
  }
  return diffs;
}

const unknownOf = (diffs) => diffs.filter((d) => !d.known);

// Where a host's build.txt says it is served from: the build's own platform line when it has one,
// else Pages' access-control-allow-origin header.
function platformOf(r, text) {
  const line = /^platform=(\S+)/m.exec(text)?.[1];
  if (line) return line === 'pages' ? 'pages' : 'worker';
  return r.headers.get('access-control-allow-origin') !== null ? 'pages' : 'worker';
}

// A host that a zone Redirect Rule answers before either platform does: its recording is a redirect
// on every address. It is compared with itself, never with the version URL.
const redirectedAtZone = (rec, h) => {
  const e = Object.values(rec?.entries?.[h] ?? {});
  return e.length > 0 && e.every((x) => REDIRECTS.includes(x.s) && x.l);
};
// The probe added to a request so that no cache answers it: a name no site uses. A zone rule may keep
// the request's query in its Location; that one occurrence is taken out of the answer, nothing else.
const PROBE = '__move_t';
const withoutProbe = (l, probe) => {
  if (l === null || l === undefined) return null;
  const text = String(l);
  const q = text.indexOf('?');
  if (q < 0) return text;
  const parts = text.slice(q + 1).split('&');
  const i = parts.indexOf(`${PROBE}=${probe}`);
  if (i < 0) return text;
  parts.splice(i, 1);
  return parts.length ? `${text.slice(0, q)}?${parts.join('&')}` : text.slice(0, q);
};

// Two good answers in a row from every host. A host the zone redirects is good when it answers its
// recorded status and Location; any other from the wanted platform with a commit the script knows.
async function waitServing(ctx, hosts, wanted, commits, rec) {
  const streak = Object.fromEntries(hosts.map((h) => [h, 0]));
  const gap = ctx.io.goodGapMs ?? GOOD_GAP_MS;
  for (;;) {
    for (const h of hosts) {
      if (streak[h] >= 2) continue;
      const probe = ctx.now();
      const r = await ctx.siteFetch(`https://${h}/build.txt?${PROBE}=${probe}`, { headers: { 'cache-control': 'no-cache' } });
      const was = rec.entries[h]['/build.txt'];
      const good = redirectedAtZone(rec, h)
        ? r.status === was.s && withoutProbe(r.headers.get('location'), probe) === was.l
        : r.status === 200 && commits.includes(r.body.toString('utf8').split('\n')[0].trim()) && platformOf(r, r.body.toString('utf8')) === wanted;
      streak[h] = good ? streak[h] + 1 : 0;
    }
    if (hosts.every((h) => streak[h] >= 2)) return true;
    if (ctx.clock.left() < gap + 3_000) return false;
    await ctx.sleep(gap);
  }
}

// ---------------------------------------------------------------- snapshots

async function snapshot(ctx, live, why, started = null) {
  const exp = await (started ?? ctx.api('GET', `/zones/${ctx.zone.id}/dns_records/export`));
  if (exp.status !== 200 || !/^\S+\s+\d+\s+IN\s+SOA\s+\S+/m.test(exp.text)) throw new Stop(1, `The zone's DNS export has no SOA record (${exp.error ?? `HTTP ${exp.status}`}); not going on without a snapshot.`);
  return {
    at: new Date(ctx.now()).toISOString(), why, dnsExport: exp.text,
    dnsRecords: live.records.filter((r) => ctx.gate.hosts.has(r.name)),
    pagesDomains: live.project.domains, workerDomains: live.mineWd.map((d) => ({ id: d.id, hostname: d.hostname, service: d.service })),
  };
}

// ---------------------------------------------------------------- the confirm code

// Made from the end state a question names; a run with the same state accepts the same code.
export function confirmCode(input) {
  return createHash('sha256').update(JSON.stringify(input)).digest('hex').slice(0, 16);
}

function askOrGo(ctx, kind, input, lines, run) {
  const code = confirmCode(input);
  if (ctx.opts.confirm === code) return true;
  if (ctx.opts.confirm) ctx.say('', `The code ${ctx.opts.confirm} does not fit this question: something it covered has changed. Nothing was changed. Here is the question as it stands now.`);
  ctx.say('', 'Cloudflare has not been changed yet. If you say yes, I will:');
  lines.forEach((l, i) => ctx.say(`  ${i + 1}. ${l}`));
  ctx.say('', `To go ahead, run the same command again with: --confirm ${code}`);
  run.next = `node move-to-workers.mjs ${kind} --confirm ${code}`;
  run.asking = true;
  return false;
}

// ---------------------------------------------------------------- the route and undo commits

async function cleanTreeOrStop(ctx) {
  const st = await ctx.gitOut('status', '--porcelain');
  if (st) throw new Stop(1, `The working tree has changes (${st.split('\n')[0].trim()}${st.includes('\n') ? ', …' : ''}). Commit them or put them away: the route and undo commits are written on a clean tree.`);
}

// HEAD's Workers config, and whether it lists exactly `want`.
async function headConfig(ctx) {
  const t = await ctx.gitOut('show', `HEAD:${ctx.configFile}`);
  return { text: t, routes: routesOf(parseJsonc(t), ctx.configFile) };
}

// Writes the commit that sets the config's routes to `want`, on top of HEAD, unless HEAD's already do.
async function ensureRouteCommit(ctx, want, kind) {
  await cleanTreeOrStop(ctx);
  const head = await headConfig(ctx);
  if (JSON.stringify(head.routes) === JSON.stringify([...want].sort())) return { commit: await ctx.gitOut('rev-parse', 'HEAD'), wrote: false };
  const file = path.join(ctx.root, ctx.configFile);
  writeFileSync(file, setRoutes(readFileSync(file, 'utf8'), want));
  await ctx.gitOut('add', '--', ctx.configFile);
  const msg = want.length ? `Attach ${want.join(', ')} to the Worker ${ctx.worker}` : `Give ${ctx.hosts.join(', ')} back to Pages: take the custom-domain routes out of ${ctx.configFile}`;
  await ctx.gitOut('commit', '-q', '-m', `${msg} (${kind} commit)`);
  return { commit: await ctx.gitOut('rev-parse', 'HEAD'), wrote: true };
}

// ---------------------------------------------------------------- the commands

function note(run, ok_, text) { run.checks.push({ ok: ok_, text }); } // ok_: true, false, or 'wait' (not wrong, not finished)

async function cmdCheck(ctx, run) {
  const { say } = ctx;
  const gh = await ctx.github(`/repos/${ctx.repository}`); // first: a private repository or a missing gh explains the rest
  if (gh.status === 404) throw new Stop(1, `GitHub does not show ${ctx.repository} without a login: the repository is private. ${loginHint(ctx)}`);
  const live = await readLive(ctx);
  if (!ctx.open) await firstMoveRefusals(ctx, live);
  say(`Move check for ${ctx.hosts.join(', ')} (zone ${ctx.zone.name}, account ${ctx.account.name})`);
  say(`Repository ${ctx.repository}, ${ctx.twoStage ? 'two-stage: production is the live branch, main the preview' : 'single-stage: main is the live branch'}. Pages project ${ctx.project.name} (${ctx.project.subdomain}); Worker ${ctx.worker} (config ${ctx.configFile}).`);
  if (ctx.open && ctx.state.route) say(`A move is open. It expects the ${ctx.state.route.kind} commit ${short(ctx.state.route.commit)} on ${ctx.twoStage ? `${ctx.prodBranch} and main` : ctx.prodBranch}; after checks the hosts ${ctx.state.route.kind === 'route' ? 'on the Worker' : 'back on Pages'}.`);
  for (const h of ctx.hosts) {
    const hs = hostState(ctx, live, h);
    say(`  ${h}: ${WHERE_WORDS[hs.where]}${notActive(hs)}; DNS ${hs.recs.map((r) => `${r.type} ${r.content}${r.proxied ? ' (proxied)' : ''}`).join('; ') || 'no record'}`);
    note(run, settled(hs, false), `${h} is ${WHERE_WORDS[hs.where]}${notActive(hs)}, DNS ${hs.recs.map((r) => `${r.type} ${r.content}`).join('; ') || 'none'}`);
  }
  say(`The live branch ${ctx.prodBranch} on GitHub is ${short(ctx.tip)}${ctx.twoStage ? `; main is ${short(ctx.mainSha)}${ctx.mainDiffers ? ' (it differs: they must be the same before record)' : ''}` : ''}.`);
  note(run, !ctx.mainDiffers, `GitHub's ${ctx.prodBranch} is ${short(ctx.tip)}`);
  const v = await workerVersion(ctx);
  const r = await ctx.siteFetch(`https://${v.host}/build.txt`);
  const served = r.body.toString('utf8').split('\n')[0].trim();
  say(`The Worker's live version ${v.id.slice(0, 8)} serves ${r.status === 200 ? short(served) : `nothing at https://${v.host}/build.txt (${r.status || r.error})`}: ${served === ctx.tip ? 'the live branch\'s commit.' : 'not the live branch\'s commit; stage 1 of the move section is not finished.'}`);
  say(`Its link, for the Cloudflare check's --preview: https://${v.host}/`);
  note(run, served === ctx.tip, `The Worker's live version serves ${r.status === 200 ? short(served) : 'nothing'}, GitHub's ${ctx.prodBranch} is ${short(ctx.tip)}`);
  say('Nothing was changed.');
  if (ctx.open) { // an open move waits for after only when every host is where the move ends
    const target = ctx.state.direction === 'to-pages' ? 'pages' : 'worker';
    const there = ctx.hosts.every((h) => { const hs = hostState(ctx, live, h); return settled(hs, target === 'worker'); });
    run.next = there ? 'node move-to-workers.mjs after' : `node move-to-workers.mjs ${target === 'pages' ? 'undo' : 'move'}`;
    return 0;
  }
  run.next = ctx.mainDiffers || served !== ctx.tip ? 'Finish stage 1 of the move section, then run check again.' : 'node move-to-workers.mjs record';
  return 0;
}

// The build of the frozen commit, in a copy of its files under move-run/build/, started apart from
// this run: it takes longer than 55 seconds. Returns 'running' or the dist/ folder.
async function ensureBuild(ctx, sha, run) {
  const dir = path.join(ctx.runDir, 'build', sha.slice(0, 12));
  const dist = path.join(dir, 'src', 'dist');
  const exit = path.join(dir, 'exit.txt');
  if (existsSync(exit)) {
    const code = readFileSync(exit, 'utf8').trim();
    if (code !== '0') throw new Stop(1, `The build of ${short(sha)} failed (exit ${code}); its log is ${path.join(dir, 'build.log')}. Fix the site, or delete ${dir} to try again.`);
    return dist;
  }
  const pidFile = path.join(dir, 'pid.txt');
  if (existsSync(pidFile) && alive(Number(readFileSync(pidFile, 'utf8')))) return 'running';
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(path.join(dir, 'src'), { recursive: true });
  const idx = path.join(dir, 'index');
  const gitEnv = { ...childEnv(ctx.io.env ?? process.env, ctx.token), GIT_INDEX_FILE: idx };
  const sh = async (args) => {
    try { return await (ctx.io.run ?? runProgram)('git', args, { cwd: ctx.root, env: gitEnv, clock: ctx.clock }); } catch (e) { throw named(e, 'git', `git ${args[0]}`); }
  };
  const rt = await sh(['read-tree', sha]);
  const co = rt.code === 0 ? await sh(['checkout-index', '-a', '-f', `--prefix=${path.join(dir, 'src')}${path.sep}`]) : rt;
  if (co.code !== 0) throw new Stop(1, `git could not copy ${short(sha)} to build it: ${(co.stderr || co.stdout).trim().split('\n')[0]}`);
  const script = `const {spawnSync}=require('node:child_process');const fs=require('node:fs');const o=fs.openSync(${JSON.stringify(path.join(dir, 'build.log'))},'w');const sh=process.platform==='win32';const lock=fs.existsSync('package-lock.json');let r=spawnSync(lock?'npm ci':'npm install',{shell:true,stdio:['ignore',o,o]});if(r.status===0)r=spawnSync('npm run build',{shell:true,stdio:['ignore',o,o]});fs.writeFileSync(${JSON.stringify(exit)},String(r.status===null?1:r.status));`;
  const env = { ...childEnv(ctx.io.env ?? process.env, ctx.token), CF_PAGES_COMMIT_SHA: sha, WORKERS_CI_COMMIT_SHA: sha, CI: 'true' };
  const child = spawn(process.execPath, ['-e', script], { cwd: path.join(dir, 'src'), env, stdio: 'ignore', detached: true, windowsHide: true });
  child.unref();
  writeFileSync(pidFile, String(child.pid));
  return 'running';
}

async function cmdRecord(ctx, run) {
  const { say } = ctx;
  if (ctx.open) throw new Stop(1, 'A move is open, so there is nothing to record: the recording belongs to the move. Finish it, or undo it and let after pass, then record again.');
  const live = await readLive(ctx);
  await firstMoveRefusals(ctx, live);
  if (ctx.mainDiffers) throw new Stop(1, `main (${short(ctx.mainSha)}) and ${ctx.prodBranch} (${short(ctx.tip)}) are not the same commit. The freeze needs them the same (D18): publish main first.`);
  for (const h of ctx.hosts) {
    const hs = hostState(ctx, live, h);
    if (hs.where !== 'pages' || !hs.cname) throw new Stop(1, `${h} is ${WHERE_WORDS[hs.where]}${hs.where === 'pages' ? ` without a CNAME to ${ctx.project.subdomain}` : ''}. A recording is made while every host is on Pages with its CNAME to the project.`);
  }
  const frozen = ctx.tip;
  const v = await workerVersion(ctx);
  let st = ctx.state;
  // A recording resumes only while it is the same freeze, building against the same Worker version;
  // one that ended unknown, or saw another version, starts again so no old capture stays.
  const resume = st && st.frozen === frozen && st.recording?.status === 'building' && st.recording.workerVersion === v.id && st.recording.hosts?.join() === ctx.hosts.join();
  if (!resume) {
    st = {
      version: 1, zone: { id: ctx.zone.id, name: ctx.zone.name }, repository: ctx.repository, pages: { name: ctx.project.name, subdomain: ctx.project.subdomain },
      worker: ctx.worker, configFile: ctx.configFile, prodBranch: ctx.prodBranch, twoStage: ctx.twoStage, hosts: ctx.hosts, frozen,
      open: false, direction: null, track: { move: {}, undo: {} }, route: null, snapshots: [], recording: { status: 'building', hosts: ctx.hosts, workerVersion: v.id, entries: {} },
    };
  }
  const keep = () => saveState(ctx.stateDir, st);
  st.recording.at = new Date(ctx.now()).toISOString();
  keep();
  ctx.state = st;
  say(`Freeze: ${ctx.prodBranch} on GitHub is ${short(frozen)}. Nothing is merged or shipped until after passes.`);

  const dist = await ensureBuild(ctx, frozen, run);
  if (dist === 'running') {
    keep();
    say(`The build of ${short(frozen)} is running (its log: move-run/build/${frozen.slice(0, 12)}/build.log).`);
    run.next = 'node move-to-workers.mjs record';
    throw new Stop(4, 'The build is not finished. Run the same command again in a minute.');
  }
  if (!existsSync(path.join(dist, 'build.txt'))) throw new Stop(1, `The build of ${short(frozen)} wrote no dist/build.txt.`);
  const marker = readFileSync(path.join(dist, 'build.txt'), 'utf8').split('\n')[0].trim();
  if (marker !== frozen) throw new Stop(1, `dist/build.txt names ${marker}, not the frozen commit ${frozen}: the site's build marker does not follow the commit it is built from.`);
  note(run, true, `A build of ${short(frozen)} names that commit in build.txt`);
  const paths = pathList(dist);
  const names = headerNames(existsSync(path.join(dist, '_headers')) ? readFileSync(path.join(dist, '_headers'), 'utf8') : '');
  st.recording.names = names;
  st.recording.paths = paths;
  const targets = [...ctx.hosts.map((h) => [h, `https://${h}`]), ['version', `https://${v.host}`]];
  for (const [key, base] of targets) {
    st.recording.entries[key] ??= {};
    await fetchAll(ctx, base, paths, names, st.recording.entries[key], keep);
  }
  const lost = unanswered(st.recording, targets.map(([key]) => st.recording.entries[key]));
  if (lost) {
    keep();
    run.next = 'node move-to-workers.mjs record';
    throw new Stop(4, `${lost} addresses did not answer; they are asked for again. Run the same command again.`);
  }
  // The domain's plain-http answer, for after.
  st.recording.http = {};
  for (const h of ctx.hosts) {
    const r = await ctx.siteFetch(`http://${h}/`);
    st.recording.http[h] = { s: r.status, l: r.headers.get('location') };
    if (!REDIRECTS.includes(r.status) || !/^https:\/\//.test(r.headers.get('location') ?? '')) say(`Note: http://${h}/ answers ${r.status} now, not a redirect to https; after will report that.`);
  }

  // The domain (Pages) against the Worker's version URL, and each host's build.txt.
  const unknown = [];
  const redirected = ctx.hosts.filter((h) => redirectedAtZone(st.recording, h));
  if (redirected.length === ctx.hosts.length) throw new Stop(1, "Every host is redirected at the zone, so the Worker's version URL could not be compared with anything. Look at it by hand.");
  for (const h of ctx.hosts) {
    if (redirected.includes(h)) {
      const e = st.recording.entries[h]['/build.txt'];
      say(`${h} is redirected at the zone (${e.s} to ${e.l}): it is compared with itself after the move, never with the Worker's version URL.`);
      note(run, true, `${h} is redirected at the zone on every address; compared with itself after the move`);
      continue;
    }
    const diffs = compare(st.recording.entries[h], st.recording.entries.version, { change: true, onVersion: true, expect: frozen });
    run.diffs.push(...diffs.map((d) => ({ ...d, host: h, who: "the Worker's version URL" })));
    unknown.push(...unknownOf(diffs).map((d) => ({ ...d, host: h, who: "the Worker's version URL" })));
    const b = st.recording.entries[h]['/build.txt'];
    if (b?.c !== frozen) unknown.push({ host: h, path: '/build.txt', field: 'commit line', expected: frozen, got: b?.c, who: 'the domain' });
  }
  const checked = paths.length * (ctx.hosts.length + 1);
  say(`Recorded ${paths.length} addresses on ${ctx.hosts.join(', ')} and on the Worker's version URL (${checked} answers); ${run.diffs.filter((d) => d.known).length} known differences, ${unknown.length} unknown.`);
  if (unknown.length) {
    st.recording.status = 'unknown';
    st.recording.unknown = unknown.slice(0, 50);
    keep();
    note(run, false, `${unknown.length} differences the script does not know between the domain and the Worker's version`);
    for (const d of unknown.slice(0, 20)) say(`  unknown: ${d.host}${d.path} ${d.field}: ${diffWords(d)}`);
    throw new Stop(1, `${unknown.length} unknown differences: the Worker would not serve what the domain serves now. Fix the site (stage 1), then record again. Nothing was changed.`);
  }
  st.snapshots.push(await snapshot(ctx, live, 'record'));
  st.recording.status = 'done';
  delete st.recording.unknown;
  keep();
  note(run, true, `${paths.length} addresses recorded on each host; the Worker's version matches apart from the known differences`);
  say('The recording is clean and kept. Next: node move-to-workers.mjs move');
  run.next = 'node move-to-workers.mjs move';
  return 0;
}

// A host's changes (three) and the two read-backs around them: five requests, each at its longest,
// and some slack. A run starts a host only if that much is left.
const bothWords = (h) => `${h} is on both the Pages project and the Worker. The script does not decide that: look at it in the dashboard.`;
const hostReserve = (ctx) => ctx.io.reserveMs ?? 5 * (ctx.io.requestMs ?? REQUEST_MS) + 5_000;

// Why the plain run's check no longer holds, or null. A --confirm run goes ahead only on a check that
// is under 15 minutes old and still describes the deployments and the branch tips.
const CHECK_MAX_MS = 15 * 60_000;
function driftOf(ctx, st, dir, light) {
  const c = st.checked;
  if (!c || c.kind !== dir) return `No plain ${dir} has checked this since the last change of direction, so there is nothing to compare with.`;
  if (ctx.now() - c.at > CHECK_MAX_MS) return `The plain ${dir} was run more than ${CHECK_MAX_MS / 60_000} minutes ago, and a --confirm run goes ahead only on a check no older than that.`;
  if (light.problem) return `${light.problem}.`;
  if (light.total !== c.total) return `The Pages project has ${light.total} deployments now; the plain ${dir} saw ${c.total}.`;
  if (light.newest !== c.newest) return `The newest Pages deployment is not the one the plain ${dir} saw.`;
  if (ctx.tip !== c.tip) return `The branch ${ctx.prodBranch} on GitHub is ${short(ctx.tip)} now; the plain ${dir} saw ${short(c.tip)}.`;
  if (ctx.mainSha !== c.main) return `The branch main on GitHub is ${short(ctx.mainSha)} now; the plain ${dir} saw ${short(c.main)}.`;
  return null;
}

async function ensureOpenState(ctx, need) {
  if (!ctx.state) throw new Stop(1, `There is no state file (${path.join(ctx.stateDir, 'state.json')}), so there is no recording to move on. ${need}`);
  return ctx.state;
}

async function switchCommand(ctx, run, dir) { // dir: 'move' | 'undo'
  const { say } = ctx;
  const toWorker = dir === 'move';
  const st = await ensureOpenState(ctx, toWorker ? 'Run record first.' : 'An undo needs the state of the move it undoes.');
  st.track ??= { move: {}, undo: {} };
  const first = !Object.values(st.track[dir] ?? {}).some((t) => t.leftAt); // first until a host has left its platform
  if (!toWorker && !st.open) throw new Stop(1, 'No move is open, so there is nothing to undo.');
  if (first && ctx.tokenLeftMs < MIN_LEFT_MS) throw new Stop(1, `The token has less than an hour left (${Math.round(ctx.tokenLeftMs / 60_000)} minutes), too little for a ${dir}. Make a new one from the same link.`);
  if (!first && ctx.tokenLeftMs < MIN_LEFT_MS) say(`Warning: the token has ${Math.round(ctx.tokenLeftMs / 60_000)} minutes left.`);
  const confirming = ctx.opts.confirm !== null;
  const firstMove = toWorker && !st.open;
  if (firstMove && st.recording?.status !== 'done') throw new Stop(1, 'There is no clean recording of the frozen commit. Run record first.');
  // The reads that do not wait for each other. A --confirm run reads page 1 of the deployments only,
  // to compare with what the plain run saw, and asks for the DNS export while it reads the rest.
  const exportStarted = confirming ? ctx.api('GET', `/zones/${ctx.zone.id}/dns_records/export`) : null;
  exportStarted?.catch(() => {}); // awaited by the snapshot; a stop before that must not leave it unhandled
  const [firstLive, version, light] = await Promise.all([readLive(ctx), firstMove ? workerVersion(ctx) : null, confirming ? lightDeployments(ctx) : null]);
  let live = firstLive;
  const hostsNow = ctx.hosts.map((h) => [h, hostState(ctx, live, h)]);
  const todo = hostsNow.filter(([, hs]) => (toWorker ? hs.where !== 'worker' : hs.where !== 'pages' || !hs.cname));
  const reserve = hostReserve(ctx);
  if (firstMove) {
    await firstMoveRefusals(ctx, live);
    if (JSON.stringify(st.hosts) !== JSON.stringify(ctx.hosts)) throw new Stop(1, `The Pages project's domains (${ctx.hosts.join(', ')}) are not the recorded hosts (${st.hosts.join(', ')}). Record again.`);
    for (const [h, hs] of hostsNow) if (hs.where !== 'pages' || !hs.cname) throw new Stop(1, `${h} is ${WHERE_WORDS[hs.where]}, not on Pages with its CNAME: a first move starts with every host on Pages.`);
    for (const [b, tip] of ctx.twoStage ? [[ctx.prodBranch, ctx.tip], ['main', ctx.mainSha]] : [[ctx.prodBranch, ctx.tip]]) { // read at the start of this run
      if (tip !== st.frozen) throw new Stop(1, `${b} on GitHub is ${short(tip)}, not the frozen commit ${short(st.frozen)}. The freeze was broken: record again.`);
    }
    if (version.id !== st.recording.workerVersion) throw new Stop(1, `The Worker's live version is ${version.id.slice(0, 8)}, not the recorded ${st.recording.workerVersion.slice(0, 8)}. Something deployed during the freeze: record again.`);
  }
  // Both modes: the working tree, and HEAD's Workers config the frozen one but for its routes.
  await cleanTreeOrStop(ctx);
  const head = await ctx.gitOut('rev-parse', 'HEAD');
  const want = toWorker ? [...ctx.hosts] : [];
  const cfg = await headConfig(ctx);
  const fits = JSON.stringify(cfg.routes) === JSON.stringify([...want].sort());
  if (firstMove && head !== st.frozen) { // the first route commit is HEAD itself: right on the frozen commit, touching nothing but the Workers config
    const parent = (await ctx.git('rev-parse', 'HEAD~1')).stdout.trim();
    const changed = (await ctx.gitOut('diff', '--name-only', 'HEAD~1', 'HEAD')).split('\n').filter(Boolean);
    if (!fits || parent !== st.frozen || changed.join() !== ctx.configFile) throw new Stop(1, `HEAD is not the frozen commit ${short(st.frozen)} with one route commit on top. Check out the branch the site was frozen on.`);
  }
  if (fits && head !== st.frozen) { // a commit that already has the right routes: if it changed the routes, it changed nothing else
    const was = await ctx.git('show', `HEAD~1:${ctx.configFile}`); // no parent config counts as no routes and nothing else
    const noRoutes = (c) => { const { routes, ...rest } = c; return JSON.stringify(rest); };
    const before = was.code === 0 ? parseJsonc(was.stdout) : {};
    const now = parseJsonc(cfg.text);
    if (JSON.stringify(routesOf(before, ctx.configFile)) !== JSON.stringify(cfg.routes)) {
      const files = await ctx.git('diff', '--name-only', 'HEAD~1', 'HEAD');
      if (files.code !== 0 || files.stdout.trim() !== ctx.configFile || noRoutes(before) !== noRoutes(now)) {
        throw new Stop(1, `HEAD (${short(head)}) changes more in ${ctx.configFile} than the custom-domain routes, so it is not a commit this script wrote. Check out the commit before it and run ${dir} again: the script writes the ${toWorker ? 'route' : 'undo'} commit itself.`);
      }
    }
  }
  // The plain run reads everything and keeps what it found; a --confirm run compares page 1 and the
  // branch tips with that, and does not read GitHub at all.
  const base = st.base ?? st.frozen;
  let range;
  if (!confirming) {
    const checked = await unfinishedBuilds(ctx, base, ctx.tip, { newest: Boolean(st.base), tips: [ctx.tip, ctx.mainSha] });
    if (checked.list.length) throw new Stop(1, `A build is unfinished (${checked.list.join('; ')}). Wait for it to end, then run this again: it could change what the Worker serves during the ${dir}.`);
    range = checked.range;
    st.checked = { kind: dir, total: checked.total, newest: checked.newest, tip: ctx.tip, main: ctx.mainSha, at: ctx.now() };
  } else range = await rangeOf(ctx, base, ctx.tip, Boolean(st.base));
  const drift = confirming ? driftOf(ctx, st, dir, light) : null;
  const plainAgain = `run the plain command again (node move-to-workers.mjs ${dir}), then confirm`;

  // Plain: write the commit. With --confirm: it must already fit.
  if (ctx.opts.confirm === null) {
    const c = await ensureRouteCommit(ctx, want, toWorker ? 'route' : 'undo');
    st.asked = { commit: c.commit, kind: toWorker ? 'route' : 'undo' }; // not yet confirmed: after goes by st.route
    ctx.state = st;
    saveState(ctx.stateDir, st);
    say(c.wrote ? `Wrote the ${st.asked.kind} commit ${short(c.commit)} (${ctx.configFile}): ${toWorker ? 'the hosts as custom_domain routes' : 'no custom-domain routes'}. It is on your branch, not pushed, and nothing on Cloudflare has changed.` : `HEAD (${short(c.commit)}) already has the right routes; no commit was written.`);
  } else if (!fits) {
    throw new Stop(1, `${ctx.configFile} at HEAD does not ${toWorker ? 'list exactly the hosts' : 'list none of them'} as custom_domain routes: a build of HEAD would reverse this run. Run plain "${dir}" first (it writes the commit).`);
  }
  const commit = await ctx.gitOut('rev-parse', 'HEAD');
  const lines = [];
  lines.push(toWorker
    ? `Take ${ctx.hosts.join(', ')} off the Pages project ${ctx.project.name}, delete each host's CNAME to ${ctx.project.subdomain}, and attach each to the Worker ${ctx.worker} (account ${ctx.account.name}, zone ${ctx.zone.name}).`
    : `Take ${ctx.hosts.join(', ')} off the Worker ${ctx.worker}, add each back to the Pages project ${ctx.project.name} with its CNAME to ${ctx.project.subdomain} (account ${ctx.account.name}, zone ${ctx.zone.name}).`);
  lines.push(`Each host is down from the moment it leaves its platform until the other one serves it: about a minute. The target is ${TARGET_MS / 60_000} minutes; past it, the run tells you to go back.`);
  lines.push(`Push commit ${short(commit)} to ${ctx.twoStage ? 'both main and production' : 'main'} afterwards (you do that, not the script); then run after.`);
  const input = { kind: dir, account: ctx.account.id, zone: ctx.zone.id, repository: ctx.repository.toLowerCase(), project: ctx.project.name, worker: ctx.worker, hosts: [...ctx.hosts].sort(), commit, frozen: st.frozen };
  if (!todo.length && ctx.opts.confirm === null) say(`Every host is already ${toWorker ? 'on the Worker' : 'back on Pages'}.`);
  if (!askOrGo(ctx, dir, input, lines, run)) return 3;

  // --- With the yes.
  // Before anything is changed: a record that no longer fits, and a run too short for the next host.
  const isFresh = (hs) => (toWorker ? hs.where === 'pages' : hs.where === 'worker');
  const needsWork = (hs) => !(toWorker ? hs.where === 'worker' : hs.where === 'pages' && hs.cname);
  const downNow = (h) => hostState(ctx, live, h).where === 'neither';
  const order = [...ctx.hosts].sort((x, y) => Number(downNow(y)) - Number(downNow(x))); // a host on neither is down: first
  const waiting = order.map((h) => [h, hostState(ctx, live, h)]).find(([, hs]) => needsWork(hs));
  if (drift && hostsNow.some(([, hs]) => isFresh(hs)) && !hostsNow.some(([, hs]) => needsWork(hs) && !isFresh(hs))) {
    run.next = `node move-to-workers.mjs ${dir}`;
    throw new Stop(1, `${drift} Nothing was changed: ${plainAgain}.`);
  }
  if (waiting && waiting[1].where === 'both') throw new Stop(1, bothWords(waiting[0]));
  if (drift && !hostsNow.some(([, hs]) => isFresh(hs))) say(`Warning: ${drift} No fresh host is left to start; after reads the builds again before it compares.`);
  if (waiting && ctx.clock.left() < reserve) {
    const spent = Math.round(((ctx.io.runMs ?? RUN_MS) - ctx.clock.left()) / 1000);
    if (isFresh(waiting[1])) {
      throw new Stop(1, `Reading what the move needs took ${spent} seconds of this run's ${Math.round((ctx.io.runMs ?? RUN_MS) / 1000)}, and a host needs ${Math.round(reserve / 1000)} seconds beside that, so no run could move one from here. Nothing was changed. Do the ${dir} by hand in the Cloudflare dashboard.`);
    }
    run.next = `node move-to-workers.mjs ${dir} --confirm ${ctx.opts.confirm}`;
    throw new Stop(4, `${waiting[0]} is down, and the ${spent} seconds of this run that reading took leave less than the ${Math.round(reserve / 1000)} a host needs, so nothing was started. Run the same command again at once: the next run starts with its whole time. If this repeats, finish ${waiting[0]} by hand in the Cloudflare dashboard; it stays down until then.`);
  }
  st.snapshots.push(await snapshot(ctx, live, dir, exportStarted));
  const prev = st.direction;
  if (toWorker) { // a go-forward after an undo starts both tracks again
    st.open = true; st.direction = 'to-worker'; st.track.undo = {};
    if (prev === 'to-pages') st.track.move = {};
  } else st.direction = 'to-pages';
  run.switching = true;
  const tr = (st.track[dir] ??= {});
  st.route = { commit, kind: toWorker ? 'route' : 'undo' };
  delete st.asked;
  delete st.passed;
  st.commits = [...new Set([...(st.commits ?? []), commit])];
  ctx.state = st;
  saveState(ctx.stateDir, st);
  const A = `/accounts/${ctx.account.id}`;
  // A host has left its platform once a change was made, or a read-back shows it gone.
  const markLeft = (h) => {
    if (!tr[h]?.leftAt) { tr[h] = { ...tr[h], leftAt: new Date(ctx.now()).toISOString() }; saveState(ctx.stateDir, st); }
  };
  const startedOn = {};
  // Every successful read shows where each host is; the track keeps it for a run that stops early.
  const seen = (l) => { for (const x of ctx.hosts) tr[x] = { ...tr[x], where: hostState(ctx, l, x).where }; saveState(ctx.stateDir, st); };
  const stopOn = async (h, what, r) => {
    live = await readLive(ctx).catch(() => null);
    const now = live ? hostState(ctx, live, h).where : null;
    if (now && now !== startedOn[h]) markLeft(h);
    if (!now) ctx.report.where[h] = 'unknown';
    const where = now ? WHERE_WORDS[now] : 'unknown (it could not be read back)';
    if (live) seen(live);
    tr[h] = { ...tr[h], where: now ?? 'unknown' };
    saveState(ctx.stateDir, st);
    throw new Stop(1, `${what} for ${h} failed: ${cfWords(r)}. ${h} is now ${where}. Run the same command again at once${toWorker ? ' (undo takes it back)' : ' (move goes forward)'}.`);
  };
  seen(live); // read moments ago in this run; each host's own read-back below keeps it current
  // A host that is on neither platform comes first (above): it is down until this run finishes it. A
  // host that does not fit the time left is skipped, and the run ends asking for another.
  const skipped = [];
  const finished = [];
  for (const h of order) {
    let hs = hostState(ctx, live, h);
    const done = settled(hs, toWorker);
    if (done) { say(`${h} is already ${toWorker ? 'on the Worker' : 'back on Pages'}; skipped.`); continue; }
    if (hs.where === 'both') throw new Stop(1, bothWords(h));
    if (isFresh(hs) && drift) { // the down hosts were finished above; nothing fresh starts on a check that no longer fits
      run.next = `node move-to-workers.mjs ${dir}`;
      throw new Stop(1, `${drift} ${finished.length ? `${finished.join(' and ')} ${finished.length > 1 ? 'were' : 'was'} finished first; no other host was started` : 'No further host was started'}: ${plainAgain}.`);
    }
    if (ctx.clock.left() < reserve) {
      skipped.push(h);
      continue;
    }
    if (hs.where === 'neither') say(`${h} is on neither platform right now: it is down until this run finishes it.`);
    startedOn[h] = hs.where;
    if (toWorker) {
      if (hs.pages) {
        const r = await ctx.api('DELETE', `${A}/pages/projects/${ctx.project.name}/domains/${h}`);
        if (!ok(r)) await stopOn(h, 'Taking it off the Pages project', r);
        markLeft(h);
        say(`${h}: left the Pages project.`);
        live = await readLive(ctx); hs = hostState(ctx, live, h);
      }
      if (hs.cname) {
        const r = await ctx.api('DELETE', `/zones/${ctx.zone.id}/dns_records/${hs.cname.id}`);
        if (!ok(r)) await stopOn(h, "Deleting its CNAME", r);
        markLeft(h);
        say(`${h}: CNAME deleted.`);
      }
      const r = await ctx.api('PUT', `${A}/workers/domains`, { json: { hostname: h, service: ctx.worker, zone_id: ctx.zone.id, environment: 'production' } });
      if (!ok(r)) await stopOn(h, 'Attaching it to the Worker', r);
      markLeft(h);
      say(`${h}: attached to the Worker.`);
    } else {
      if (hs.worker) {
        const id = live.mineWd.find((d) => d.hostname === h).id;
        const r = await ctx.api('DELETE', `${A}/workers/domains/${id}`);
        if (!ok(r)) await stopOn(h, 'Taking it off the Worker', r);
        markLeft(h);
        say(`${h}: left the Worker.`);
        live = await readLive(ctx); hs = hostState(ctx, live, h);
      }
      if (hs.recs.length && !hs.cname) throw new Stop(1, `${h} still has a DNS record (${hs.recs.map((x) => `${x.type} ${x.content}`).join('; ')}) that is not a CNAME to ${ctx.project.subdomain}. The script touches no other record: delete it by hand, then run undo again.`);
      if (!hs.pages) {
        const r = await ctx.api('POST', `${A}/pages/projects/${ctx.project.name}/domains`, { json: { name: h } });
        const already = !ok(r) && r.body?.errors?.some?.((e) => e.code === ALREADY_ADDED); // an earlier run added it; the read-back below shows its status
        if (!ok(r) && !already) await stopOn(h, 'Adding it to the Pages project', r);
        if (already) ctx.assumedPages.add(h);
        markLeft(h);
        say(already ? `${h}: already on the Pages project.` : `${h}: added to the Pages project.`);
      }
      if (!hs.cname) {
        const r = await ctx.api('POST', `/zones/${ctx.zone.id}/dns_records`, { json: { type: 'CNAME', name: h, content: ctx.project.subdomain, proxied: true } });
        if (!ok(r)) await stopOn(h, 'Writing its CNAME', r);
        markLeft(h);
        say(`${h}: CNAME written.`);
      }
    }
    live = await readLive(ctx);
    seen(live);
    const after = hostState(ctx, live, h);
    if (after.where !== (toWorker ? 'worker' : 'pages')) throw new Stop(1, `${h} reads ${WHERE_WORDS[after.where]} after its changes, not ${toWorker ? 'on the Worker' : 'on Pages'}. Run the same command again, or the other one to go back.`);
    if (!toWorker && !after.pagesActive) say(`${h}: Cloudflare shows its Pages domain as ${after.pagesStatus}; the run waits for it to serve.`);
    finished.push(h);
  }
  if (skipped.length) {
    run.next = `node move-to-workers.mjs ${dir} --confirm ${ctx.opts.confirm}`;
    throw new Stop(4, `Not enough of this run is left to move ${skipped.join(' and ')} (${skipped.length > 1 ? 'each needs' : 'it needs'} ${Math.round(reserve / 1000)} seconds), so ${skipped.length > 1 ? 'they were' : 'it was'} not started. Run the same command again at once.`);
  }
  // Wait for each to serve; the first time a host left its platform is kept.
  const known = [...new Set([st.frozen, ...(st.commits ?? []), ...range])]; // the platforms also build what was shipped since
  const served = await waitServing(ctx, ctx.hosts, toWorker ? 'worker' : 'pages', known, st.recording);
  const oldest = Math.min(ctx.now(), ...ctx.hosts.map((h) => Date.parse(tr[h]?.leftAt)).filter(Number.isFinite));
  const ago = Math.round((ctx.now() - oldest) / 1000);
  for (const h of ctx.hosts) if (tr[h]) tr[h].servedAt = served ? (tr[h].servedAt ?? new Date(ctx.now()).toISOString()) : null;
  saveState(ctx.stateDir, st);
  if (!served) {
    const over = ctx.now() - oldest > TARGET_MS;
    note(run, false, `Not every host serves ${toWorker ? 'the Worker' : 'Pages'} yet (${ago} seconds since the first left its platform)`);
    if (over) {
      run.next = toWorker ? 'node move-to-workers.mjs undo' : 'node move-to-workers.mjs move';
      throw new Stop(1, `${Math.round(ago / 60)} minutes after the first host left its platform, a host does not serve ${toWorker ? 'the Worker' : 'Pages'}. That is past the ${TARGET_MS / 60_000}-minute target: ${toWorker ? 'undo' : 'go forward with move'}.`);
    }
    run.next = `node move-to-workers.mjs ${dir} --confirm ${ctx.opts.confirm}`;
    throw new Stop(4, `${ago} seconds since the first host left its platform; not every host serves ${toWorker ? 'the Worker' : 'Pages'} yet. Run the same command again.`);
  }
  const verb = (one, many) => (ctx.hosts.length > 1 ? many : one); // the host list's verb: "serves" for one host, "serve" for several
  note(run, true, `Both answers in a row: ${ctx.hosts.join(', ')} ${verb('serves', 'serve')} ${toWorker ? 'the Worker' : 'Pages'}, ${ago} seconds after the first left its platform`);
  say(`Done: ${ctx.hosts.join(', ')} ${verb('serves', 'serve')} ${toWorker ? 'the Worker' : 'Pages again'} (${ago} seconds since the first host left its platform).`);
  say(`Now push commit ${short(commit)} to ${ctx.twoStage ? 'both main and production (git push origin HEAD:production HEAD:main)' : 'main'}, deploy it if the Worker has no Workers Builds, and run: node move-to-workers.mjs after`);
  run.next = 'node move-to-workers.mjs after';
  return 0;
}

async function cmdAfter(ctx, run) {
  const { say } = ctx;
  const st = await ensureOpenState(ctx, 'Run record and move first.');
  if (!st.open || !st.route) throw new Stop(1, 'No move has been confirmed yet, so there is nothing to check.');
  let live = await readLive(ctx);
  // A plain run's commit was asked for, not confirmed. It counts only when every host already sits
  // where it points (the steps were done by hand); otherwise the last confirmed direction stands.
  if (st.asked && st.asked.commit !== st.route.commit) {
    const there = st.asked.kind === 'route' ? 'worker' : 'pages';
    if (ctx.hosts.every((h) => { const hs = hostState(ctx, live, h); return settled(hs, there === 'worker'); })) {
      st.route = st.asked;
      st.direction = st.asked.kind === 'route' ? 'to-worker' : 'to-pages';
      delete st.asked;
      saveState(ctx.stateDir, st);
    }
  }
  const toWorker = st.route.kind === 'route'; // the commit waited for says where the hosts belong
  const expect = st.route.commit;
  const branches = ctx.twoStage ? [ctx.prodBranch, 'main'] : [ctx.prodBranch];
  const problems = [];
  const tips = {};
  for (const b of branches) tips[b] = await tipOf(ctx, b);
  for (const b of branches) if (tips[b] !== expect) problems.push(`${b} on GitHub is ${short(tips[b])}, not the ${st.route.kind} commit ${short(expect)}: push it`);
  if (problems.length) {
    problems.forEach((p) => note(run, false, p));
    run.next = `git push origin HEAD:${ctx.prodBranch}${ctx.twoStage ? ' HEAD:main' : ''}`;
    throw new Stop(1, ...problems, 'Push the commit, then run after again.');
  }
  note(run, true, `GitHub's ${branches.join(' and ')} ${branches.length > 1 ? 'are' : 'is'} the ${st.route.kind} commit ${short(expect)}`);
  const { list: unfinished } = await unfinishedBuilds(ctx, st.base ?? st.frozen, tips[ctx.prodBranch], { newest: Boolean(st.base), tips: Object.values(tips) });
  if (unfinished.length) {
    note(run, false, `Builds are unfinished: ${unfinished.join('; ')}`);
    run.next = 'node move-to-workers.mjs after';
    throw new Stop(4, `Builds are unfinished (${unfinished.join('; ')}). Run the same command again in a minute.`);
  }
  note(run, true, 'No build is unfinished');
  live = await readLive(ctx);
  const rec = st.recording;
  const wantWhere = toWorker ? 'worker' : 'pages';
  const coming = [];
  for (const h of ctx.hosts) {
    const hs = hostState(ctx, live, h);
    const good = settled(hs, toWorker);
    const state = `${WHERE_WORDS[hs.where]}${notActive(hs)}`;
    const waiting = !good && !toWorker && hs.where === 'pages' && hs.cname && COMING_UP.includes(hs.pagesStatus); // not wrong: Cloudflare is still bringing the domain up
    note(run, good ? true : waiting ? 'wait' : false, `${h} is ${state}${good ? '' : waiting ? ': a wait, not a failure' : `; it should be ${toWorker ? 'on the Worker' : 'on Pages with its CNAME and an active domain'}`}`);
    if (waiting) { coming.push(`${h} is ${state}: a wait, not a failure`); continue; }
    if (!good) { problems.push(`${h} is ${state}`); continue; }
    if (redirectedAtZone(rec, h)) { note(run, true, `${h} is redirected at the zone: only Cloudflare's lists say which platform has it`); continue; }
    const r = await ctx.siteFetch(`https://${h}/build.txt?${PROBE}=${ctx.now()}`, { headers: { 'cache-control': 'no-cache' } });
    const answers = r.status === 200 ? platformOf(r, r.body.toString('utf8')) : null;
    note(run, answers === wantWhere, `${h} /build.txt is answered by ${answers === 'pages' ? 'Pages' : answers === 'worker' ? 'the Worker' : `nothing (${r.status || r.error})`}`);
    if (answers !== wantWhere) problems.push(answers ? `${h} is ${toWorker ? 'on the Worker' : 'on Pages'} in Cloudflare's lists but is still answered by ${answers === 'pages' ? 'Pages' : 'the Worker'}` : `${h} answers /build.txt with ${r.status || r.error}`);
  }
  if (!problems.length && coming.length) {
    run.next = 'node move-to-workers.mjs after';
    throw new Stop(4, ...coming, 'Cloudflare is still bringing the Pages domain up. Run the same command again in a minute.');
  }
  if (problems.length) {
    run.next = toWorker ? 'node move-to-workers.mjs move --confirm <code>' : 'node move-to-workers.mjs undo --confirm <code>';
    throw new Stop(1, ...problems, ...coming, toWorker ? 'A build of the wrong commit may have put a host back (S9). Run move again to go forward, or undo.' : 'Run undo again.');
  }
  const unknown = [];
  const keep = () => saveState(ctx.stateDir, st);
  const ap = st.after?.expect === expect && st.after.kind === st.route.kind ? st.after : (st.after = { expect, kind: st.route.kind, entries: {} }); // kept across runs
  const parse = (l) => { try { return l ? new URL(l) : null; } catch { return null; } };
  for (const h of ctx.hosts) {
    ap.entries[h] ??= {};
    await fetchAll(ctx, `https://${h}`, rec.paths, rec.names, ap.entries[h], keep);
  }
  const lost = unanswered(ap, ctx.hosts.map((h) => ap.entries[h]));
  if (lost) {
    keep();
    run.next = 'node move-to-workers.mjs after';
    throw new Stop(4, `${lost} addresses did not answer; they are asked for again. Run the same command again.`);
  }
  for (const h of ctx.hosts) {
    const diffs = compare(rec.entries[h], ap.entries[h], { change: toWorker, onVersion: false, expect });
    run.diffs.push(...diffs.map((d) => ({ ...d, host: h })));
    unknown.push(...unknownOf(diffs).map((d) => ({ ...d, host: h })));
    // Plain http goes to https on the recorded host: this one, or the zone host the recording went to.
    const r = await ctx.siteFetch(`http://${h}/`);
    const was = rec.http?.[h];
    const wasTo = parse(was?.l);
    const hostWanted = wasTo && wasTo.hostname !== h && ctx.hosts.includes(wasTo.hostname) ? wasTo.hostname : h;
    const to = parse(r.headers.get('location'));
    const httpOk = REDIRECTS.includes(r.status) && to?.protocol === 'https:' && to.hostname === hostWanted && to.pathname === '/';
    note(run, httpOk, `http://${h}/ answers ${r.status}${r.headers.get('location') ? ` to ${r.headers.get('location')}` : ''}${httpOk ? ', a redirect to https' : `; it should redirect to https://${hostWanted}/`}`);
    if (!httpOk) unknown.push({ host: h, path: 'http://', field: 'redirect to https', expected: `a redirect to https://${hostWanted}/`, got: `${r.status} ${r.headers.get('location') ?? ''}` });
  }
  delete st.after; // the comparison is complete; a later one starts clean
  keep();
  const knownN = run.diffs.filter((d) => d.known).length;
  note(run, !unknown.length, `${rec.paths.length} addresses on each host compared with the recording: ${knownN} known differences, ${unknown.length} unknown`);
  if (unknown.length) {
    for (const d of unknown.slice(0, 20)) say(`  unknown: ${d.host}${d.path} ${d.field}: ${diffWords(d)}`);
    run.next = toWorker ? 'Read the differences; node move-to-workers.mjs undo if a visitor would notice.' : 'Read the differences.';
    throw new Stop(1, `${unknown.length} unknown differences between the live site and the recording.`);
  }
  const when = new Date(ctx.now()).toISOString();
  st.base = expect; // later builds are looked at from here on; it only moves forward
  if (toWorker) {
    st.passed = expect; // the stage marker: cleared when a switch starts, so a go-forward onto the same commit is not "passed"
    saveState(ctx.stateDir, st);
    const many = ctx.hosts.length > 1;
    say(`After passed: ${ctx.hosts.join(', ')} ${many ? 'serve' : 'serves'} the Worker and ${many ? 'match' : 'matches'} the recording. The move stays open, so undo works until the Pages project is retired.`);
    say('If you will not undo soon, delete the API token now: https://dash.cloudflare.com/profile/api-tokens. An undo later needs a new token, made the same way.');
    run.next = 'Nothing more for this script. Delete the API token now if you will not undo soon (an undo later needs a new one). Keep the Pages project 14 days, then retire it as the move section says.';
    run.done = true;
  } else {
    st.open = false;
    saveState(ctx.stateDir, st);
    renameSync(path.join(ctx.stateDir, 'state.json'), path.join(ctx.stateDir, `state-closed-${when.slice(0, 10)}-${randomBytes(3).toString('hex')}.json`));
    const many = ctx.hosts.length > 1;
    say(`After passed: ${ctx.hosts.join(', ')} ${many ? 'are' : 'is'} back on Pages and ${many ? 'match' : 'matches'} the recording. The move is closed; the next one starts with record.`);
    say('Delete the API token now: https://dash.cloudflare.com/profile/api-tokens.');
    run.next = 'The move is closed. To try again: node move-to-workers.mjs record';
    run.closed = true;
  }
  return 0;
}

// ---------------------------------------------------------------- the status page

const STAGE_NAMES = [
  ['Prepare', 'The site and its Worker are ready: same pages, a Workers config, serving with no domain. Not this script.'],
  ['Freeze and record', 'Nothing is merged while the move runs; what the live site serves is written down.'],
  ['Switch', 'Each host leaves the Pages project and goes to the Worker. Undo is possible.'],
  ['Check on the domain', 'The live site is compared with what was recorded.'],
  ['Clean up', 'The token is deleted; the Pages project is retired after 14 days. Not this script.'],
];

function stageOf(st, run) {
  if (run.closed) return 4; // an undo that passed its check
  if (!st) return run.stateRead ? 1 : 0; // a run that stopped before the state was read knows no stage
  if (st.open) {
    if (st.passed === st.route?.commit && st.route?.kind === 'route') return 5; // after passed for the commit waited for
    return run.cmd === 'after' ? 4 : 3;
  }
  return 2;
}

export function renderStatus(template, m) {
  const items = m.stages.map(([name, line], i) => {
    const cls = i + 1 === m.stage ? 'now' : i + 1 < m.stage ? 'past' : 'later';
    return `<li class="${esc(cls)}"><strong>${esc(i + 1)}. ${esc(name)}</strong>${i + 1 === m.stage ? ' <span class="tag">you are here</span>' : ''}<br><span>${esc(line)}</span></li>`;
  }).join('\n');
  const hosts = m.hosts.length ? m.hosts.map((h) => `<tr><td>${esc(h.name)}</td><td>${esc(h.where)}</td><td>${esc(h.since ?? '–')}</td></tr>`).join('\n') : '<tr><td colspan="3">No host is known yet.</td></tr>';
  const checks = m.checks.length ? m.checks.map((c) => `<li class="${c.ok === 'wait' ? 'wait' : c.ok ? 'ok' : 'bad'}">${c.ok === 'wait' ? 'Waiting' : c.ok ? 'OK' : 'Failed'}: ${esc(c.text)}</li>`).join('\n') : '<li>Nothing was checked in this run.</li>';
  const diffs = m.differences.length
    ? m.differences.map((d) => `<li><a href="${d.path === 'http://' ? `http://${esc(d.host)}/` : `https://${esc(d.host)}${esc(d.path)}`}" title="${esc(d.path)}">${d.path === 'http://' ? `http://${esc(d.host)}/` : `${esc(d.host)}${esc(d.path)}`}</a>: ${esc(d.field)}: ${d.field === 'commit line' ? esc(diffWords(d)) : `${esc(d.expected)} became ${esc(d.got)}`}</li>`).join('\n')
    : '<li>None.</li>';
  const fill = {
    title: esc(m.site), updated: esc(m.updated), command: esc(m.command), result: esc(m.result), stages: items, hosts, checks,
    differences: diffs, next: esc(m.next ?? 'Nothing.'), undo: esc(m.undo),
  };
  return template.replace(/\{\{(\w+)\}\}/g, (_, k) => (Object.hasOwn(fill, k) ? fill[k] : ''));
}

function writeStatus(ctx0, run, io, code, st, errLines) {
  if (!run.root) return;
  const here = path.dirname(realpathSync(fileURLToPath(import.meta.url)));
  let template;
  try { template = readFileSync(path.join(here, 'move-status.html'), 'utf8'); } catch { return; }
  const hostsList = st?.hosts ?? run.hosts ?? [];
  const m = {
    stages: STAGE_NAMES, stage: stageOf(st, run), site: st ? `${st.zone.name}: ${st.repository}` : (run.site ?? 'a Pages site'), updated: new Date(run.t0).toISOString(),
    command: `node move-to-workers.mjs ${run.cmd}${run.opts?.confirm ? ' --confirm …' : ''}`,
    result: code === 0 ? 'finished' : code === 3 ? 'waiting for your yes' : code === 4 ? 'stopped for time or a build: run the same command again' : `stopped: ${(errLines ?? [])[0] ?? 'see the terminal'}`,
    hosts: hostsList.map((h) => {
      const t = st?.track?.[st.direction === 'to-pages' ? 'undo' : 'move']?.[h]; // what this run read comes first
      return { name: h, where: run.where?.[h] ? WHERE_WORDS[run.where[h]] ?? run.where[h] : t?.where ? WHERE_WORDS[t.where] ?? t.where : 'not read in this run', since: t?.leftAt ? `left its platform ${t.leftAt}` : null };
    }),
    checks: run.checks, differences: run.diffs.filter((d) => !d.known).slice(0, 50),
    next: run.next,
    undo: st?.open && st.direction === 'to-worker' ? 'Undo works until the Pages project is retired: node move-to-workers.mjs undo (then --confirm with its code).'
      : st?.open ? 'An undo has started: node move-to-workers.mjs undo carries it on, and node move-to-workers.mjs move goes forward again from where it stopped.' : 'There is nothing to undo yet.',
  };
  try { writeFileSync(path.join(run.root, 'move-run', 'status.html'), renderStatus(template, m)); } catch { /* the page is a courtesy; the terminal has the report */ }
}

// ---------------------------------------------------------------- running it

export async function main(argv, io = {}) {
  const say = io.say ?? ((...l) => { for (const x of l) process.stdout.write(`${x}\n`); });
  io = { ...io, say };
  let opts;
  try { opts = parseArgs(argv); } catch (e) {
    if (!(e instanceof UsageError)) throw e;
    process.stderr.write(`move-to-workers: ${e.message}\n\n${USAGE}`);
    return 2;
  }
  if (opts.help) { say(USAGE); return 0; }
  const run = { cmd: opts.cmd, opts, checks: [], diffs: [], next: null, t0: (io.now ?? (() => Date.now()))(), release: null, root: null };
  const ctxBox = {};
  let code;
  let errLines = null;
  // Hosts that have left their platform in a switch, and hosts that are on neither (in either
  // direction, as saved or as this run read them): a run that ends early says so first.
  const leftLines = () => {
    const st = ctxBox.ctx?.state ?? run.state;
    if (!st?.open) return [];
    const move = st.direction !== 'to-pages';
    const tracks = st.track?.[move ? 'move' : 'undo'] ?? {};
    const lines = [];
    const placeOf = (h) => { const w = run.where?.[h]; return w && w !== 'unknown' ? w : tracks[h]?.where; }; // this run's read is the newer
    if (!(st.hosts ?? []).every((h) => placeOf(h) === (move ? 'worker' : 'pages'))) { // a finished switch has nothing to warn about
      for (const [h, t] of Object.entries(tracks)) if (t.leftAt) lines.push(`${h} has left ${move ? 'Pages' : 'the Worker'}; last read: ${WHERE_WORDS[placeOf(h)] ?? 'not read yet'}.`);
    }
    const down = new Set();
    for (const t of [st.track?.move, st.track?.undo]) for (const [h, x] of Object.entries(t ?? {})) if (x.where === 'neither') down.add(h);
    for (const [h, w] of Object.entries(run.where ?? {})) { // this run's own read is the newer
      if (w === 'neither') down.add(h);
      else if (w !== 'unknown') down.delete(h);
    }
    for (const h of down) if (!lines.some((l) => l.startsWith(`${h} `))) lines.push(`${h} is on neither platform: it is down until a run finishes it.`);
    return lines;
  };
  try {
    const ctx = await prepare(opts, io, run);
    ctxBox.ctx = ctx;
    run.site = `${ctx.zone.name}: ${ctx.repository}`;
    run.hosts = ctx.hosts;
    ctx.say = say;
    if (opts.cmd === 'check') code = await cmdCheck(ctx, run);
    else if (opts.cmd === 'record') code = await cmdRecord(ctx, run);
    else if (opts.cmd === 'move') code = await switchCommand(ctx, run, 'move');
    else if (opts.cmd === 'undo') code = await switchCommand(ctx, run, 'undo');
    else code = await cmdAfter(ctx, run);
  } catch (e) {
    if (e instanceof UsageError) { process.stderr.write(`move-to-workers: ${e.message}\n`); code = 2; }
    else if (e instanceof Deadline) {
      const at = !e.place ? '' : e.waiting ? ` while waiting on ${e.place} (${e.call})` : ` before its next call, to ${e.place} (${e.call}): the time went on the calls before it`;
      const k = e.kept;
      errLines = [
        `This run reached its time limit (${Math.round((io.runMs ?? RUN_MS) / 1000)} seconds) and stopped${at}.`,
        'What it changed stands; the next run reads what is there and carries on.',
        ...(k ? [`${k.n} of ${k.of} addresses on ${k.host} are read and kept; the next run starts after them.`,
          `Run the same command again, as long as the number for ${k.host} grows (a later stop may name another host: each run asks again for every address that got no answer).`]
          : ["Run the same command again. If runs keep stopping at the time limit, the run's calls take longer than it allows: the places it calls answer slowly from this computer, or there is a lot to read. Check the connection, or try again later."]),
      ];
      leftLines().forEach((l) => say(l));
      say('', ...errLines, 'Status 4.');
      run.next ??= `node move-to-workers.mjs ${opts.cmd}${opts.confirm ? ` --confirm ${opts.confirm}` : ''}`;
      code = 4;
    } else if (e instanceof Stop) {
      errLines = e.lines;
      leftLines().forEach((l) => say(l));
      say('', ...e.lines.map((l, i) => (i ? l : `Stopped: ${l}`)), `Status ${e.code}.`);
      code = e.code;
    } else throw e;
  } finally {
    run.release?.();
  }
  const ctx = ctxBox.ctx;
  writeStatus(ctx, run, io, code, ctx?.state ?? run.state ?? null, errLines);
  if (run.root && code !== 2) say(`Status page: ${path.join(run.root, 'move-run', 'status.html')}`);
  return code;
}

const isMain = (() => {
  try {
    const argv1 = process.argv[1];
    if (!argv1) return false;
    return import.meta.url === pathToFileURL(realpathSync(argv1)).href || path.basename(argv1) === 'move-to-workers.mjs';
  } catch { return false; }
})();
if (isMain) {
  if (Number(process.versions.node.split('.')[0]) < 18) {
    process.stderr.write(`move-to-workers needs Node 18 or newer; this is Node ${process.versions.node}.\n`);
    process.exit(2);
  }
  process.exitCode = await main(process.argv.slice(2), {});
}
