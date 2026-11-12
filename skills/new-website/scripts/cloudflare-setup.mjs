#!/usr/bin/env node
// cloudflare-setup.mjs: put a site that lives on GitHub onto a Cloudflare Worker, with the settings of
// the Cloudflare checklist (docs/CLOUDFLARE-CHECKLIST.md), through Cloudflare's API and one short-lived
// token.
//
//   node cloudflare-setup.mjs setup [--skip <id>]... [--record "<type> <name> <content>"]... [--confirm <code>]
//   node cloudflare-setup.mjs launch [--skip <id>]... [--confirm <code>]
//
// Run it in the site's folder. A run with something to change prints its question and a code,
// changes nothing, and ends with 3; the same command with --confirm <code> makes the changes the
// question named. It needs Node 18 or newer and nothing from npm, and it never runs Wrangler. What it
// does, and the exit statuses, are in references/CLOUDFLARE_FIRST_DEPLOY.md next to this folder.
// `setup` is setup day; `launch`, which attaches the domain and makes the site public, is launch day.
// It reads the Worker (deployments, version link) and creates none: the first deploy does.
import http from 'node:http';
import https from 'node:https';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { Resolver, promises as dnsPromises } from 'node:dns';
import { existsSync, readFileSync, realpathSync, writeFileSync, renameSync, mkdirSync, rmSync, readdirSync } from 'node:fs';
import { isDeepStrictEqual } from 'node:util';
import { fileURLToPath, pathToFileURL } from 'node:url';
// The move script imports githubRepo and running from here: neither module's top level may use the
// other's exports, only code that runs later.
import { Stop, readWorkersConfig, workerVersion, ensureRouteCommit, takeLock, routesOf } from './move-to-workers.mjs';

const API_HOST = 'https://api.cloudflare.com';
const API_PREFIX = '/client/v4';
const RUN_MS = 55_000; // one deadline per run: it leaves time to report before an assistant's 60 seconds
const REQUEST_MS = 8_000; // one call to Cloudflare gets this long at most, so the time kept for the launch's steps holds
const HOST_RESERVE_MS = 5 * REQUEST_MS + 5_000; // the export, the DELETE, the PUT, a put-back and one more, plus 5 seconds
const MAX_TOKEN_MS = 8 * 86_400_000; // "a week at most": the dashboard sets an end DATE, which can end late on day 7
const UA = 'croftweaver-cloudflare-setup/1';
const STOCK_URL = /^https?:\/\/(?:www\.)?example\.com\/?$/i; // the starter's SITE.url, never filled in
const WORKER_NAME = /^[A-Za-z0-9][A-Za-z0-9-]{0,62}$/;
const RECORD_FIELDS = ['type', 'name', 'content', 'proxied', 'ttl', 'comment', 'tags', 'settings']; // what a record is put back with

// The permission rows of the checklist's section 6, named when Cloudflare refuses something.
const ROW = {
  zone: 'Zone → Zone → Read',
  settings: 'Zone → Zone Settings → Edit',
  bot: 'Zone → Bot Management → Edit',
  dns: 'Zone → DNS → Edit',
  rules: 'Zone → Transform Rules → Edit',
  workers: 'Account → Workers Scripts → Edit',
};

// The zone settings the script writes. `title` and `path` are the checklist's own words, and
// `api`/`value` stand in its section 6: a test keeps the three in step.
export const SETTINGS = [
  { id: 'https', title: 'Always Use HTTPS: On', api: 'always_use_https', value: 'on',
    path: 'Your domain → SSL/TLS → Overview (check the encryption mode is not Off) → Edge Certificates → Always Use HTTPS',
    visitor: 'whoever opens an http:// address there is sent to https://' },
  { id: 'tls', title: 'Minimum TLS Version: TLS 1.2', api: 'min_tls_version', value: '1.2',
    path: 'Your domain → SSL/TLS → Edge Certificates → Minimum TLS Version',
    visitor: 'a device that speaks only TLS 1.0 or 1.1 gets no connection there' },
  { id: 'email', title: 'Email Address Obfuscation: Off', api: 'email_obfuscation', value: 'off',
    path: 'Your domain → Security → Settings → filter by Client-side abuse → Email Address Obfuscation',
    visitor: 'email addresses in its pages are no longer rewritten, and no email-decode script is added' },
  { id: 'nel', title: 'Network Error Logging (NEL): Off', api: 'nel', value: { enabled: false },
    path: 'Account home → Network → Network Error Logging Monitoring',
    visitor: "the visitor's browser is no longer asked to send error reports to Cloudflare (if the header stays, launch day adds a rule)" },
];
// Two lines of one call, Bot Management's update. The PUT sends BOT_PUT_FIELDS as read, apart from
// what a line changes, and bot_preference_sync_enabled only when the `ai` line is in. It never sends
// is_robots_txt_managed: Cloudflare refused it as true (code 10400), so sending it as read could fail.
export const BOT_LINES = [
  { id: 'bot', title: 'Bot Fight Mode: Off', fields: { fight_mode: false },
    path: 'Your domain → Security → Settings → filter by Bot traffic → Bot fight mode',
    visitor: 'simple bots are no longer challenged there, and no challenge script or cookie is added' },
  { id: 'ai', title: 'AI crawlers: allow',
    fields: {
      ai_bots_protection: 'disabled', ai_search: 'disabled', ai_user: 'disabled', ai_training: 'disabled',
      crawler_protection: 'disabled', content_bots_protection: 'disabled', bot_preference_sync_enabled: false,
    },
    path: 'Your domain → Security → Settings → filter by Bot traffic → AI Crawler and Agent access policies',
    visitor: "AI crawlers, training ones included, are no longer blocked or led into AI Labyrinth, each personal AI agent Cloudflare lists is set to the API's disabled, and Cloudflare adds no lines to robots.txt" },
];
// Bot Management's ai_agents, when it is a plain object of strings (the only form a capture shows).
const isAgentMap = (v) => v !== null && typeof v === 'object' && !Array.isArray(v) && Object.values(v).every((x) => typeof x === 'string');
// The agents of a map that are not `disabled`, each set to `disabled`: what the PUT sends.
const agentsToDisable = (map) => Object.fromEntries(Object.keys(map).filter((k) => map[k] !== 'disabled').map((k) => [k, 'disabled']));
// The `ai` line's end state for one zone: its fields, and every agent the first GET lists set to `disabled`.
const aiWant = (fields, agents) => (isAgentMap(agents) ? { ...fields, ai_agents: Object.fromEntries(Object.keys(agents).map((k) => [k, 'disabled'])) } : fields);
// The AI bot policies' values, per field, as the third trial read them for each choice in the
// dashboard (fixtures T3-001 to T3-013); ai_bots_protection's "block" is T2-016's. A value not here
// gets a note that the kit does not know it, never a guess.
const AI_FIELDS = {
  ai_training: { label: 'Training', values: { disabled: 'Allow (do not block)', block: 'Block', only_on_ad_pages: 'Block on pages with ads', disallow: 'Disallow' } },
  ai_search: { label: 'Search', values: { disabled: 'Allow (do not block)', block: 'Block', only_on_ad_pages: 'Block on pages with ads' } },
  ai_user: { label: 'Agent', values: { disabled: 'Allow (do not block)', block: 'Block', only_on_ad_pages: 'Block on pages with ads' } },
  ai_bots_protection: { label: 'The older Block AI bots setting', values: { disabled: 'disabled', block: 'block' } },
};
const stayInSearch = (skipping) => `Cloudflare's way to refuse AI training and stay in Google, Bing and Apple search (the kit has not tested how crawlers are treated): choose Disallow for Training in the dashboard, turn Bot Preference Sync on there too (choosing Disallow does not turn it on), and ${skipping === 'launch' ? 'run the setup stage with --skip ai from then on' : `${skipping ? 'keep running this with' : 'run this with'} --skip ai`}.`;
const STAY_IN_SEARCH = stayInSearch(false);

// The notes on what the AI bot policies mean for search, from the `ai` line's values read at the
// start of the run (`now`) and its state at the point of printing. They change nothing.
export function aiNotes(now, state) {
  if (!now) return [];
  const where = BOT_LINES.find((b) => b.id === 'ai').path;
  const notes = [];
  for (const [k, f] of Object.entries(AI_FIELDS)) {
    const v = now[k];
    if (typeof v !== 'string' || !Object.hasOwn(f.values, v)) {
      notes.push(`${f.label} ${v === undefined ? 'was missing from what Cloudflare returned' : `reads ${show(v)}`} at the start of this run: a value this kit does not know, so it cannot say what it means for search. Look at it in the dashboard: ${where}.`);
      continue;
    }
    if (v === 'disabled') continue;
    const label = f.values[v];
    if (state === 'hand') {
      notes.push(`${f.label} read ${label} before this run; Cloudflare did not confirm the change, so look at it in the dashboard: ${where}.`);
      if (k === 'ai_training' && v !== 'disallow') notes.push(STAY_IN_SEARCH);
      continue;
    }
    if (k !== 'ai_training') {
      if (state === 'skipped' || state === 'unread' || state === 'launch') notes.push(`${f.label} is set to ${label}, and ${state === 'launch' ? 'launch day' : 'this run'} leaves it as it is. Section 4 of the Cloudflare checklist says what the kit sets there, and why.`);
      continue;
    }
    if (state === 'done') { notes.push(`Training was ${label} and is now Allow (do not block). ${STAY_IN_SEARCH}`); continue; }
    if (v === 'disallow') {
      if (state === 'change') notes.push('Training is set to Disallow. If you say yes, it becomes Allow (do not block), and AI training crawlers are let in. To keep Disallow, run this with --skip ai.');
      if (state === 'unread') notes.push('Training is set to Disallow. This run could not change it; the AI crawlers line says why. To keep Disallow on a later run, run it with --skip ai.');
      if (state === 'skipped' || state === 'unread' || state === 'launch') {
        const sync = now.bot_preference_sync_enabled;
        if (sync === false) notes.push(`Bot Preference Sync is off, so Disallow writes no no-training preference into robots.txt. To publish it there, turn Sync on in the dashboard: ${where}.`);
        else if (sync !== true) notes.push(`Bot Preference Sync ${sync === undefined ? 'was missing from what Cloudflare returned' : `reads ${show(sync)}`} at the start of this run: a value this kit does not know, so it cannot say whether robots.txt carries the no-training preference. Look at it in the dashboard: ${where}.`);
      }
      continue;
    }
    const ads = v === 'only_on_ad_pages' ? ' on pages that show ads' : '';
    const said = `Training is set to ${label}. Cloudflare says ${label} also keeps Googlebot, Bingbot and Applebot out${ads}, which affects search.`;
    if (state === 'change') notes.push(`${said} If you say yes, it becomes Allow (do not block). ${STAY_IN_SEARCH}`);
    else if (state === 'skipped') notes.push(`${said} This run leaves it as it is. ${stayInSearch(true)}`);
    else if (state === 'unread') notes.push(`${said} This run could not change it; the AI crawlers line says why. ${STAY_IN_SEARCH}`);
    else if (state === 'launch') notes.push(`${said} Launch day changes no AI setting. ${stayInSearch('launch')}`);
  }
  if (Object.hasOwn(now, 'ai_agents')) notes.push(...agentNotes(now.ai_agents, state, where));
  return notes;
}
// The notes on personal agents, from the first read's values (`ai_agents`). Values are printed as read.
function agentNotes(agents, state, where) {
  const unknown = (what) => `${what} at the start of this run: a value this kit does not know, so it cannot say what it means for search. Look at it in the dashboard: ${where}.`;
  if (!isAgentMap(agents)) return [unknown(`Personal agents (ai_agents) read ${show(agents)}`)];
  const notes = [];
  for (const [k, v] of Object.entries(agents)) {
    if (v === 'disabled') continue;
    if (v !== 'block' && v !== 'only_on_ad_pages') notes.push(unknown(`Personal agent ${k} reads ${v}`));
    else if (state === 'hand') notes.push(`Personal agent ${k} read ${v} at the start of this run; Cloudflare did not confirm the change, so look at it in the dashboard: ${where}.`);
    else if (state === 'skipped' || state === 'unread' || state === 'launch') notes.push(`Personal agent ${k} read ${v} at the start of this run, and ${state === 'launch' ? 'launch day' : 'this run'} leaves it as it is. Section 4 of the Cloudflare checklist says what the kit sets there, and why.`);
  }
  return notes;
}
const BOT_PUT_FIELDS = ['fight_mode', 'enable_js', 'ai_bots_protection', 'ai_search', 'ai_user', 'ai_training',
  'crawler_protection', 'content_bots_protection', 'cf_robots_variant'];
export const SKIP_IDS = [...SETTINGS.map((s) => s.id), ...BOT_LINES.map((b) => b.id)];
export const LAUNCH_SKIP_IDS = ['nel-rule'];
// Hosts a verification record points AT. A record whose NAME ends in one has name and target swapped.
const VERIFY_TARGETS = ['verify.bing.com'];

export class UsageError extends Error {}
// The run's time: the run's own limit, or one call's cap. `call` names the call that got no answer.
class Deadline extends Error {
  constructor(call = null) { super('deadline'); this.call = call; }
}

// ---------------------------------------------------------------- what was asked for

const USAGE = `Usage: node cloudflare-setup.mjs setup|launch [options]

Run it in the site's folder, with the token in CLOUDFLARE_API_TOKEN or in .dev.vars (a file git
ignores). A run with something to change asks first: it prints the list and a code, changes
nothing, and ends with 3. On the owner's yes, run the same command again with --confirm <code>.

  setup                  the Worker's state, the checklist's settings, and the records given
                         with --record (setup day)
  launch                 attach the domain to the Worker, list it as a route in the config, and
                         add the NEL rule if the headers are still sent (launch day: this makes
                         the site public)
  --skip <id>            leave one line as it is: ${SKIP_IDS.join(', ')}; on launch also
                         ${LAUNCH_SKIP_IDS.join(', ')}
  --record "<type> <name> <content>"
                         setup only: a verification record to write, DNS only: TXT or CNAME, a
                         name relative to the domain (@ for the domain itself) or a full name,
                         then the content (at most five)
  --confirm <code>       the code of the question the owner said yes to
  -h, --help             this text

Exit status: 0 finished, and in effect as far as Cloudflare's API shows; 1 something failed or
was refused (the report says what); 2 the command was wrong; 3 waiting for a yes; 4 waiting for
Cloudflare, a build or a push: run the same command again in a few minutes.
`;

export function parseArgs(argv) {
  const opts = { stage: null, skip: [], records: [], confirm: null, help: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const value = () => {
      const v = argv[++i];
      if (v === undefined || (v.startsWith('-') && v !== '-')) throw new UsageError(`${a} needs a value`);
      return v;
    };
    if (a === '-h' || a === '--help') opts.help = true;
    else if (a === '--skip') opts.skip.push(value());
    else if (a === '--record') opts.records.push(value());
    else if (a === '--confirm') opts.confirm = value();
    else if (a.startsWith('-')) throw new UsageError(`unknown option ${a}`);
    else if (opts.stage === null) opts.stage = a;
    else throw new UsageError(`unexpected "${a}": give one stage`);
  }
  if (opts.help) return opts;
  if (opts.stage !== 'setup' && opts.stage !== 'launch') throw new UsageError(opts.stage ? `unknown stage "${opts.stage}"` : 'give the stage: setup or launch');
  const ids = opts.stage === 'launch' ? [...SKIP_IDS, ...LAUNCH_SKIP_IDS] : SKIP_IDS;
  for (const id of opts.skip) {
    if (opts.stage === 'setup' && LAUNCH_SKIP_IDS.includes(id)) throw new UsageError(`--skip ${id} belongs to the launch stage`);
    if (!ids.includes(id)) throw new UsageError(`--skip takes one of ${ids.join(', ')} (got "${id}")`);
  }
  if (opts.stage === 'launch' && opts.records.length) throw new UsageError('--record belongs to the setup stage');
  opts.skip = [...new Set(opts.skip)].sort();
  if (opts.confirm !== null && !/^[0-9a-f]{16}$/.test(opts.confirm)) {
    throw new UsageError('--confirm takes the 16-character code the question printed');
  }
  if (opts.records.length > 5) throw new UsageError('give at most five --record options in one run');
  opts.records = opts.records.map(parseRecord);
  return opts;
}

// "<type> <name> <content>": the first two words, then the rest as it is, spaces and all.
export function parseRecord(text) {
  const m = /^\s*(\S+)\s+(\S+)\s+(\S.*?)\s*$/s.exec(text);
  if (!m) throw new UsageError(`--record "${text}": give the type, the name and the content, for example --record "TXT @ google-site-verification=…"`);
  const type = m[1].toUpperCase();
  if (type !== 'TXT' && type !== 'CNAME') throw new UsageError(`--record "${text}": only TXT and CNAME records are written (verification records); add others by hand`);
  const rec = { type, name: m[2].toLowerCase().replace(/\.$/, ''), content: m[3] };
  if (type === 'CNAME') rec.content = rec.content.toLowerCase().replace(/\.$/, '');
  const swapped = looksSwapped(rec);
  if (swapped) throw new UsageError(`--record "${text}": ${swapped}. Check which is the name and which the target, and give the record again`);
  return rec;
}

// The shape of a record given the wrong way round: the launch day's Bing record had verify.bing.com
// as its name. Bing's record is a CNAME from a name of 32 hexadecimal characters to verify.bing.com.
export function looksSwapped(rec) {
  const bare = rec.name.replace(/\.$/, '');
  const target = VERIFY_TARGETS.find((t) => bare === t || bare.endsWith(`.${t}`));
  if (target) return `the name ends in ${target}, which is where such a record points: name and target look swapped`;
  if (rec.type === 'CNAME' && !rec.content.includes('.')) return `the target "${rec.content}" has no dot, which a host name has: name and target look swapped`;
  return null;
}

// A literal loopback address, for the tests only: never a name, never from .dev.vars.
function loopback(name, value, { origin }) {
  if (!value) return null;
  const host = origin ? /^http:\/\/(127(?:\.\d{1,3}){3}|\[::1\]):(\d{1,5})\/?$/.exec(value) : /^(127(?:\.\d{1,3}){3}|\[::1\]):(\d{1,5})$/.exec(value);
  if (!host || Number(host[2]) > 65535 || (host[1].startsWith('127') && host[1].split('.').some((n) => Number(n) > 255))) {
    throw new UsageError(`${name} must be a literal loopback address (${origin ? 'http://127.0.0.1:<port>' : '127.0.0.1:<port>'}), for tests only`);
  }
  return origin ? value.replace(/\/$/, '') : value;
}

// ---------------------------------------------------------------- the clock, git, Cloudflare

function makeClock(ms = RUN_MS) {
  const end = Date.now() + ms;
  return { left: () => end - Date.now() };
}

// The environment every program the script starts gets: the token removed, and git told never to
// wait for a typed password.
function childEnv(token) {
  const env = {};
  for (const [k, v] of Object.entries(process.env)) {
    if (k === 'CLOUDFLARE_API_TOKEN' || (token && v === token)) continue;
    env[k] = v;
  }
  env.GIT_TERMINAL_PROMPT = '0';
  return env;
}

// A program with its input closed, given only the time left. At the deadline it is killed at once
// (SIGKILL), and the run goes on without waiting for its output to close: git has nothing to tidy
// up for a read. On POSIX it runs in a group of its own and the whole group is killed, so the
// programs it started (ssh, a credential helper) end with it; on Windows only the program itself
// is, and the run still goes on.
function runProgram(cmd, args, { cwd, env, clock }) {
  return new Promise((resolve, reject) => {
    const ms = clock.left();
    if (ms <= 0) { reject(new Deadline()); return; }
    const posix = process.platform !== 'win32';
    let out = '';
    let err = '';
    let settled = false;
    let child;
    try {
      child = spawn(cmd, args, { cwd, env, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, detached: posix });
    } catch (e) {
      reject(new Stop(1, `could not run ${cmd}: ${e.message}`));
      return;
    }
    const settle = (fn) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      fn();
    };
    const timer = setTimeout(() => {
      try {
        if (posix) process.kill(-child.pid, 'SIGKILL');
        else child.kill('SIGKILL');
      } catch { /* it has ended */ }
      child.stdout.destroy();
      child.stderr.destroy();
      settle(() => reject(new Deadline()));
    }, ms);
    child.stdout.on('data', (c) => { out += c; });
    child.stderr.on('data', (c) => { err += c; });
    child.on('error', (e) => settle(() => reject(new Stop(1, e.code === 'ENOENT' ? `${cmd} is not installed, or not on the PATH` : `could not run ${cmd}: ${e.message}`))));
    child.on('close', (code) => settle(() => resolve({ code, stdout: out, stderr: err })));
  });
}

// Owner and repository from the remote's address, in any of its forms. The address itself is
// never printed: a user name part can hold a credential.
export function githubRepo(url) {
  const s = String(url).trim();
  const m = /^(?:https?|git|ssh):\/\/(?:[^@/]*@)?github\.com(?::\d+)?\/([^/]+)\/([^/]+?)(?:\.git)?\/?$/i.exec(s)
    || /^(?:[^@/:]+@)?github\.com:\/?([^/]+)\/([^/]+?)(?:\.git)?\/?$/i.exec(s);
  return m ? { owner: m[1], repo: m[2] } : null;
}

// ---------------------------------------------------------------- the gate and Cloudflare

const ADDRESS_TYPES = ['A', 'AAAA', 'CNAME'];
const PHASE = 'http_response_headers_transform';

// Every call to Cloudflare passes here first. `g` is what this run has learned: the account, the zone,
// the Worker, the hosts of this site, and, once the launch has read them, the one record it may delete
// (`recordId`) and the record as it may be put back (`note`). Anything not listed is refused.
export function gate(method, url, body, g) {
  const [route, query = ''] = url.split('?');
  const refuse = (why) => { throw new Stop(1, `gate: refused ${method} ${route}${why ? ` (${why})` : ''}`); };
  if (/\.\.|%|\\|\/\/|[^\x21-\x7e]/.test(url)) refuse('odd path');
  if (/\/pages(?:\/|$)/.test(route)) refuse('Pages is not used any more');
  const paged = /^(?:(?:page|per_page)=\d{1,4})?(?:&(?:page|per_page)=\d{1,4})*$/.test(query.replace(/^&/, ''));
  const hosts = g.hosts ?? new Set();
  const A = g.accountId ? `/accounts/${g.accountId}` : null;
  const Z = g.zoneId ? `/zones/${g.zoneId}` : null;
  const W = A && g.worker ? `${A}/workers` : null;
  const tail = (prefix) => (prefix && route.startsWith(`${prefix}/`) ? route.slice(prefix.length + 1) : null);
  if (method === 'GET') {
    if (route === '/user/tokens/verify' && !query) return;
    if (route === '/zones' && paged) return;
    if (W && route === `${W}/scripts/${g.worker}/deployments` && !query) return;
    if (W && route === `${W}/subdomain` && !query) return;
    if (W && route === `${W}/domains` && (!query || query === `service=${g.worker}`)) return;
    if (Z && (route === Z || route.startsWith(`${Z}/`)) && (!query || paged)) return;
    refuse();
  }
  if (W && route === `${W}/domains` && method === 'PUT' && !query && body
    && Object.keys(body).every((k) => ['hostname', 'service', 'zone_id', 'environment'].includes(k))
    && hosts.has(body.hostname) && body.service === g.worker && body.zone_id === g.zoneId && body.environment === 'production') return;
  const dr = tail(Z && `${Z}/dns_records`);
  if (dr !== null && method === 'DELETE' && !query) {
    if (/^[0-9a-f]{32}$/.test(dr) && g.recordId && dr === g.recordId) return;
    refuse('not the one record this run read at the host');
  }
  if (Z && route === `${Z}/dns_records` && method === 'POST' && !query && body) {
    const atHost = hosts.has(body.name) && ADDRESS_TYPES.includes(body.type);
    if (atHost) {
      if (g.note && isDeepStrictEqual(body, g.note)) return;
      refuse(g.note ? 'not the record as it was read' : 'an address record at the site\'s host');
    }
    if (['TXT', 'CNAME'].includes(body.type)) return; // a verification record, as --record writes it
  }
  if (Z && method === 'PATCH' && !query && SETTINGS.some((s) => route === `${Z}/settings/${s.api}`)) return;
  if (Z && route === `${Z}/bot_management` && method === 'PUT' && !query) return;
  if (Z && method === 'PUT' && route === `${Z}/rulesets/phases/${PHASE}/entrypoint` && !query) return;
  if (tail(Z) !== null && method === 'POST' && /^rulesets\/[0-9a-f]{32}\/rules$/.test(tail(Z)) && !query) return;
  refuse();
}

// One call to Cloudflare's API, given only the time left and 8 seconds at most. It answers
// { status, body, text }; an HTTP status never rejects. A call that gets no answer in time rejects with
// a Deadline that names it; a connection that fails rejects with a Stop.
export function makeApi(origin, token, clock, g) {
  return (method, p, { json } = {}) => new Promise((resolve, reject) => {
    const wire = json === undefined ? undefined : JSON.stringify(json);
    gate(method, p, wire === undefined ? undefined : JSON.parse(wire), g); // the gate sees what is sent
    const call = `${method} ${p.split('?')[0].replace(/\/(accounts|zones|dns_records|domains)\/[^/]+/g, '/$1/…')}`;
    const ms = Math.min(REQUEST_MS, clock.left());
    if (ms <= 0) { reject(new Deadline(call)); return; }
    const url = new URL(`${API_PREFIX}${p}`, origin);
    const lib = url.protocol === 'https:' ? https : http;
    const headers = { authorization: `Bearer ${token}`, accept: 'application/json', 'user-agent': UA };
    if (wire !== undefined) headers['content-type'] = 'application/json';
    const signal = AbortSignal.timeout(ms);
    const req = lib.request(url, { method, headers, signal, agent: false }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('error', () => {});
      res.on('close', () => {
        if (signal.aborted) { reject(new Deadline(call)); return; }
        const text = Buffer.concat(chunks).toString('utf8');
        let parsed = null;
        try { parsed = text ? JSON.parse(text) : null; } catch { parsed = null; }
        resolve({ status: res.statusCode, body: parsed, text });
      });
    });
    req.on('error', (e) => {
      if (signal.aborted) reject(new Deadline(call));
      else reject(new Stop(1, `Cloudflare's API did not answer (${e.code || e.message}). Is this computer online? Run the same command again.`));
    });
    req.end(wire);
  });
}

const ok = (r) => r.status >= 200 && r.status < 300 && r.body?.success !== false;
// Cloudflare's own words for a refusal: its error codes and messages (a 10400's detail is in messages).
function cfWords(r) {
  const all = [...(r.body?.errors ?? []), ...(r.body?.messages ?? [])]
    .filter((e) => e && e.message)
    .map((e) => (e.code ? `${e.message} (code ${e.code})` : e.message));
  return all.length ? [...new Set(all)].join('; ') : `HTTP ${r.status}`;
}
const refusal = (r, row) => (r.status === 403
  ? `Cloudflare refused it (403${r.body?.errors?.[0]?.code ? `, code ${r.body.errors[0].code}` : ''}): the token needs the row ${row}`
  : `Cloudflare refused it: ${cfWords(r)}`);

// Every page of a list. Returns null items when a page is refused.
async function allPages(api, p, perPage) {
  const items = [];
  for (let page = 1; page <= 200; page++) {
    const sep = p.includes('?') ? '&' : '?';
    const r = await api('GET', `${p}${sep}${perPage ? `per_page=${perPage}&` : ''}page=${page}`);
    if (!ok(r)) return { r, items: null };
    const got = Array.isArray(r.body?.result) ? r.body.result : [];
    items.push(...got);
    const pages = r.body?.result_info?.total_pages;
    if (!got.length || !pages || page >= pages) return { r, items };
  }
  throw new Stop(1, `Cloudflare's list at ${p.split('?')[0]} runs past 200 pages; the script does not decide from part of a list.`);
}

// Running: queued or under way, or between two stages (a stage before deploy that has succeeded), or
// with no stage given yet. The move script reads Pages deployments with it.
export const running = (d) => Boolean(d) && !d.is_skipped && (!d.latest_stage || ['idle', 'active'].includes(d.latest_stage.status)
  || (d.latest_stage.status === 'success' && d.latest_stage.name !== 'deploy'));
const short = (sha) => String(sha).slice(0, 7);

// ---------------------------------------------------------------- the code of a question

// Made from the end state the question names and from the changes it listed (`listed`, one key per
// line). A later run accepts the code for any part of that list: what was done since drops out, so
// the script's own writes keep it (R8), and anything new needs a new yes (R1). What is there now (an
// old value) is shown but not in it.
export function setupCode(input, listed = []) {
  const settings = {};
  for (const s of SETTINGS) if (!input.skip.includes(s.id)) settings[s.id] = s.value;
  for (const b of BOT_LINES) if (!input.skip.includes(b.id)) settings[b.id] = b.id === 'ai' && input.aiAgents ? { ...b.fields, ai_agents: Object.fromEntries(input.aiAgents.map((k) => [k, 'disabled'])) } : b.fields;
  const end = {
    stage: 'setup',
    account: input.account,
    worker: input.worker,
    repository: input.repository.toLowerCase(),
    zone: input.zone,
    settings,
    skip: [...input.skip].sort(),
    hosts: Object.keys(settings).length ? [...input.hosts].sort() : [],
    records: input.records.map((r) => `${r.type} ${r.fullName} ${r.content}`).sort(),
  };
  return createHash('sha256').update(JSON.stringify({ end, listed: [...listed].sort() })).digest('hex').slice(0, 16);
}

// Does `code` fit what is left to do? It fits when some list the question could have shown, all that
// is left (`left`) plus any of the lines that could since have been done (`possible`), gives it.
export function codeFits(code, input, left, possible) {
  const done = possible.filter((k) => !left.includes(k));
  for (let mask = 0; mask < 2 ** done.length; mask++) {
    if (setupCode(input, [...left, ...done.filter((_, i) => mask & (2 ** i))]) === code) return true;
  }
  return false;
}

// ---------------------------------------------------------------- the stage

const unquote = (s) => (/^".*"$/s.test(s) ? s.slice(1, -1) : s);
const show = (v) => (typeof v === 'string' ? v : JSON.stringify(v));

// The one run limit a test may shorten, and only below the real one.
function runLimit() {
  const v = process.env.CLOUDFLARE_SETUP_RUN_MS;
  if (v === undefined || v === '') return RUN_MS;
  if (!/^\d{1,5}$/.test(v) || Number(v) >= RUN_MS) throw new UsageError(`CLOUDFLARE_SETUP_RUN_MS must be a whole number of milliseconds below ${RUN_MS}, for tests only`);
  return Number(v);
}

// The Worker as Cloudflare shows it: not there, there and serving a commit of this repository (its
// version link's build.txt), or there with nothing but the template Cloudflare's Builds uploads before
// its first build. Any other Worker of the name is not this site's, and is refused.
async function readWorker(ctx) {
  const { api, worker, account, configFile } = ctx;
  const dep = await api('GET', `/accounts/${account.id}/workers/scripts/${worker}/deployments`);
  if (dep.status === 404 && dep.body?.errors?.some((e) => e.code === 10007)) return { kind: 'missing' };
  if (!ok(dep)) throw new Stop(1, `Cloudflare did not return the deployments of the Worker ${worker}: ${refusal(dep, ROW.workers)}.`);
  const sources = (dep.body.result?.deployments ?? []).map((d) => d.source);
  const v = await workerVersion(ctx);
  const url = ctx.previewAt ? `${ctx.previewAt}/build.txt` : `https://${v.host}/build.txt`;
  const link = ctx.previewAt ? `http://${v.host}.test:${new URL(ctx.previewAt).port}` : `https://${v.host}`;
  const call = `GET https://${v.host}/build.txt`;
  const ms = Math.min(REQUEST_MS, ctx.clock.left());
  if (ms <= 0) throw new Deadline(call);
  let status = 0;
  let text = '';
  try {
    const r = await fetch(url, { redirect: 'manual', headers: { 'user-agent': UA }, signal: AbortSignal.timeout(ms) });
    status = r.status;
    text = (await r.text()).slice(0, 200);
  } catch {
    if (ctx.clock.left() <= 0) throw new Deadline(call);
  }
  if (status === 0) throw new Stop(4, `The version link of the Worker ${worker} (${v.host}) did not answer. Run the same command again in a minute. Nothing was changed.`);
  const sha = status === 200 ? text.split('\n')[0].trim() : '';
  if (/^[0-9a-f]{7,40}$/.test(sha)) {
    const there = await ctx.git('cat-file', '-e', `${sha}^{commit}`);
    if (there.code !== 0) throw new Stop(1, `A Worker named ${worker} exists, and its version link serves the commit ${short(sha)}, which this repository does not have: it is not this site's. Pick another name in ${configFile} ("name"), then run this again. Nothing was changed.`);
    return { kind: 'serves', sha, link, version: v };
  }
  if (sources.length && sources.every((s) => s === 'dash_template')) return { kind: 'pending', link, version: v };
  throw new Stop(1, `A Worker named ${worker} exists, and its version link serves no build.txt that names a commit: it is not this site's. Pick another name in ${configFile} ("name"), then run this again. Nothing was changed.`);
}

// Script step 1, both stages: the repository and its publish model, the token, the zone, the Worker's
// config and the Worker itself. `launch` also reads src/config.ts at the commit that goes live.
async function prepare(opts, io) {
  const { say, cwd } = io;
  const clock = makeClock(runLimit());
  const apiOrigin = loopback('CLOUDFLARE_SETUP_API', process.env.CLOUDFLARE_SETUP_API, { origin: true });
  const resolverAt = loopback('CLOUDFLARE_SETUP_RESOLVER', process.env.CLOUDFLARE_SETUP_RESOLVER, { origin: false });
  const previewAt = loopback('CLOUDFLARE_SETUP_PREVIEW', process.env.CLOUDFLARE_SETUP_PREVIEW, { origin: true });
  if (apiOrigin) say(`Test mode: Cloudflare's API is replaced by ${apiOrigin}.`);
  if (resolverAt) say(`Test mode: the zone's nameservers are replaced by ${resolverAt}.`);
  if (previewAt) say(`Test mode: the Worker's version link is replaced by ${previewAt}.`);
  if (process.env.CLOUDFLARE_SETUP_RUN_MS) say(`Test mode: this run lasts ${process.env.CLOUDFLARE_SETUP_RUN_MS} ms.`);

  // 1. The repository: GitHub's owner and name, its branches, its config at the head of main.
  // The token is known from the start when it comes from the environment; from .dev.vars, once read.
  let env = childEnv((process.env.CLOUDFLARE_API_TOKEN ?? '').trim() || null);
  const git = (...args) => runProgram('git', args, { cwd, env, clock });
  const gitOut = async (...args) => {
    const r = await git(...args);
    if (r.code !== 0) throw new Stop(1, `git ${args[0]} failed: ${(r.stderr || r.stdout).trim().split('\n')[0] ?? ''}`);
    return r.stdout.trim();
  };
  const top = await git('rev-parse', '--show-toplevel');
  if (top.code !== 0) throw new Stop(1, 'This folder is not a git repository. Run the script in the site\'s folder.');
  const root = top.stdout.trim();
  const remote = await git('config', '--get', 'remote.origin.url');
  const gh = remote.code === 0 ? githubRepo(remote.stdout) : null;
  if (!gh) throw new Stop(1, 'The remote "origin" is not a repository on GitHub, so Cloudflare cannot build from it. Push the site to GitHub first (new-website §4).');
  const repository = `${gh.owner}/${gh.repo}`;

  const token = await readToken(root, git);
  env = childEnv(token);
  const g = { hosts: new Set(), worker: null, accountId: null, zoneId: null, recordId: null, note: null };
  const api = makeApi(apiOrigin ?? API_HOST, token, clock, g);

  let heads;
  try {
    heads = await git('ls-remote', '--heads', 'origin');
  } catch (e) {
    if (!(e instanceof Deadline)) throw e;
    throw new Stop(1, `git did not finish reading the branches of ${repository} within the run's time. A program git started (ssh, or a credential helper) did not end: run git ls-remote origin once yourself to see why, then run this again.`);
  }
  if (heads.code !== 0) throw new Stop(1, `git could not read the branches of ${repository} on GitHub. Check that this computer can reach it (git fetch origin), then run again.`);
  const branch = new Map(heads.stdout.split('\n').map((l) => l.split('\t')).filter((p) => p.length === 2)
    .map(([sha, ref]) => [ref.replace(/^refs\/heads\//, ''), sha]));
  const mainSha = branch.get('main');
  if (!mainSha) throw new Stop(1, `${repository} has no branch main on GitHub. The kit's sites keep their reviewed work there.`);
  const present = await git('cat-file', '-e', `${mainSha}^{commit}`);
  if (present.code !== 0) throw new Stop(1, `The head of main on GitHub (${short(mainSha)}) is not in this folder yet. Run git fetch origin, then run this again.`);
  const { prodBranch, host: mainHost } = await readConfig(git, mainSha, 'main');
  let host = mainHost;

  // The publish model: the value of PROD_BRANCH and the branches on GitHub must agree.
  let model;
  if (prodBranch === 'main' && !branch.has('production')) model = 'single-stage';
  else if (prodBranch === 'production' && branch.has('production')) model = 'two-stage';
  else {
    throw new Stop(1,
      `The two signs of the publish model disagree: src/config.ts says PROD_BRANCH is "${prodBranch}", and GitHub has ${branch.has('production') ? 'a' : 'no'} branch production.`,
      'Two-stage (main is the preview, production the live site): PROD_BRANCH is "production" and the branch production exists. On the owner\'s word, the assistant creates it from the reviewed main (new-website §4).',
      'Single-stage (main is the live site): PROD_BRANCH is "main", and there is no branch production.');
  }
  const prodSha = branch.get(prodBranch);
  // `launch` reads the site at the commit that goes live, the head of the production branch.
  if (opts.stage === 'launch' && prodSha !== mainSha) {
    const here = await git('cat-file', '-e', `${prodSha}^{commit}`);
    if (here.code !== 0) throw new Stop(1, `The head of ${prodBranch} on GitHub (${short(prodSha)}) is not in this folder yet. Run git fetch origin, then run this again.`);
    const live = await readConfig(git, prodSha, prodBranch);
    if (live.prodBranch !== prodBranch) {
      throw new Stop(1, `src/config.ts says PROD_BRANCH is "${prodBranch}" at the head of main and "${live.prodBranch}" at the head of ${prodBranch}, the commit that would go live. Publish main to ${prodBranch} first (npm run ship, on the owner's word).`);
    }
    host = live.host;
  }
  const wc = await readWorkersConfig(git, mainSha);
  const worker = wc.cfg.name;
  if (!WORKER_NAME.test(worker)) throw new Stop(1, `${wc.file} names the Worker "${worker}": a Worker's name is letters, digits and hyphens, at most 63, starting with a letter or a digit.`);
  if (wc.cfg.workers_dev !== false) throw new Stop(1, `${wc.file} does not say "workers_dev": false, so the Worker would answer at its own workers.dev address as well as at the domain. Set it, commit it to main, then run this again.`);
  g.hosts.add(host);
  g.worker = worker;

  // 2. The token: verified, with an end date a week away at most, and reaching this one zone.
  const verify = await api('GET', '/user/tokens/verify');
  if (!ok(verify) || verify.body?.result?.status !== 'active') {
    throw new Stop(1, `Cloudflare did not accept the token (${ok(verify) ? `its status is ${verify.body?.result?.status}` : cfWords(verify)}). It may be revoked, or not valid yet: a start date in the future does that. Make a new token as the checklist's section 6 says, with no start date.`);
  }
  const expires = Date.parse(verify.body.result.expires_on ?? '');
  if (!Number.isFinite(expires)) {
    throw new Stop(1, 'This token has no end date. Make one with an end date: tomorrow, a week at most (the checklist\'s section 6), and delete this one.');
  }
  if (expires - Date.now() > MAX_TOKEN_MS) {
    throw new Stop(1, `This token ends on ${verify.body.result.expires_on.slice(0, 10)}. The checklist says a week at most: make one that ends tomorrow, or within the week, and delete this one.`);
  }
  // Workers Scripts Edit lists every zone of the account, so the zone is the one that lists DNS Edit.
  // A token made for the account alone is listed with DNS Edit in every zone: that is refused.
  const zones = await allPages(api, '/zones', 50);
  if (!zones.items) throw new Stop(1, `Cloudflare refused to list the token's zones (${cfWords(zones.r)}). Make a new token with the row ${ROW.zone} (the checklist's section 6).`);
  const accounts = [...new Set(zones.items.map((z) => z.account?.id))];
  if (accounts.length > 1) {
    throw new Stop(1, `The zones this token lists belong to ${accounts.length} accounts. The script works in one account: make the token for the one account the site's domain is in (the checklist's section 6).`);
  }
  const editable = zones.items.filter((z) => Array.isArray(z.permissions) && z.permissions.includes('#dns_records:edit'));
  if (!editable.length) {
    throw new Stop(1, `This token lists ${zones.items.length} zone${zones.items.length === 1 ? '' : 's'}, none with DNS Edit. Make one with the row ${ROW.dns}, limited to the site's own zone (Zone Resources: your one domain; the checklist's section 6).`);
  }
  if (editable.length > 1) {
    throw new Stop(1, `This token has DNS Edit in ${editable.length} zones (${editable.map((z) => z.name).join(', ')}). Make one limited to the site's own zone (Zone Resources: your one domain): a token made for the account alone gets DNS Edit in every zone. A token narrowed just now may need a few minutes before Cloudflare shows the change: then run this again.`);
  }
  const zone = editable[0];
  if (!(host === zone.name || host.endsWith(`.${zone.name}`))) {
    throw new Stop(1, `The zone this token can edit is ${zone.name}, and ${host} is not in it. The domain must be on Cloudflare first ("Going live" in CLOUDFLARE_FIRST_DEPLOY.md), and the token limited to it.`);
  }
  if (zone.status !== 'active') throw new Stop(1, `The zone ${zone.name} is ${zone.status} on Cloudflare, not active: its nameservers must point to Cloudflare first.`);
  const account = { id: zone.account?.id, name: zone.account?.name ?? zone.account?.id };
  if (!account.id) throw new Stop(1, 'Cloudflare did not say which account the zone belongs to.');
  g.accountId = account.id;
  g.zoneId = zone.id;

  // 3. The Worker's config, and the Worker.
  if (wc.cfg.account_id && wc.cfg.account_id !== account.id) {
    throw new Stop(1, `${wc.file} names the account ${wc.cfg.account_id}, and the zone ${zone.name} is in the account ${account.id}. A Worker is made in the account its config names: take account_id out, or give the right one.`);
  }
  const routes = routesOf(wc.cfg, wc.file);
  if (routes.some((r) => r !== host)) {
    throw new Stop(1, `${wc.file} routes ${routes.filter((r) => r !== host).join(', ')}. This script manages the route of ${host} only, and only on launch day: take the others out, or attach them by hand.`);
  }
  if (routes.includes(host)) {
    const on = await api('GET', `/accounts/${account.id}/workers/domains?service=${worker}`);
    if (!ok(on) || !Array.isArray(on.body?.result) || !on.body.result.some((d) => d.hostname === host && d.service === worker)) {
      throw new Stop(1, `${wc.file} already routes ${host}, and Cloudflare does not show ${host} on the Worker ${worker}${ok(on) ? '' : ` (${refusal(on, ROW.workers)})`}. The route belongs in the config once the domain is attached: take it out, or attach the domain.`);
    }
  }
  const ctx = { say, clock, apiOrigin, resolverAt, previewAt, git, gitOut, root, gh, repository, token, api, g, branch, mainSha, prodBranch, host, model, prodSha,
    zone, account, worker, configFile: wc.file, hosts: [host], allowed: new Set() };
  ctx.childEnv = () => env;
  ctx.state = await readWorker(ctx);
  return ctx;
}

const workerWords = (ctx, state) => {
  const { worker, configFile, repository } = ctx;
  if (state.kind === 'serves') return `The Worker ${worker} serves commit ${short(state.sha)} at its version link.`;
  if (state.kind === 'pending') return `The Worker ${worker} exists, and Cloudflare's Builds has uploaded only its template so far: no build of this site has passed. Look at Workers & Pages → ${worker} → Builds, and run this again after a build passes. If Builds shows no repository connected, this Worker is not this site's: rename it in ${configFile}.`;
  return `The Worker ${worker} is not on Cloudflare yet. The script makes none; the first deploy does. Either connect the repository to Workers Builds, or deploy once from this computer:`;
};
// What to do when the Worker is missing: Builds (with the token D33 asks for), or one deploy by hand.
function missingWorkerSteps(ctx) {
  const { worker, configFile, repository } = ctx;
  return [
    `  1. Connect ${repository}: Workers & Pages → Create → Import a repository. The Worker's name comes from ${configFile} ("${worker}"). Under Advanced settings, the API token field picks an existing token by default: choose "Create new token", so this Worker has a token of its own.`,
    '     Then cut that token down in place (its Build settings, in this Worker): Account → Workers Scripts → Edit and Account Settings → Read; User → Memberships → Read and User Details → Read; and, for this site\'s own zone only, Zone → Workers Routes → Edit and SSL and Certificates → Edit. If other Workers live in that account, use a separate Cloudflare account for the site: Workers Scripts Edit reaches every Worker in the account it is given for.',
    '  2. Or deploy once from this computer: npm run deploy:live (it needs Wrangler signed in to the account).',
    'Cloudflare makes the Worker when the first build or deploy finishes. Run this again after that.',
  ];
}

async function setupStage(opts, io) {
  const ctx = await prepare(opts, io);
  const { say, clock, resolverAt, repository, api, host, model, zone, account, worker, state } = ctx;

  // 5. The zone: its proxied hosts and records, its settings, Bot Management.
  const zoneAt = `/zones/${zone.id}`;
  const dns = await allPages(api, `${zoneAt}/dns_records`, 100);
  const records = dns.items;
  const hosts = records ? [...new Set(records.filter((r) => r.proxied && ['A', 'AAAA', 'CNAME'].includes(r.type)).map((r) => r.name))].sort() : [];
  const hostsSay = records
    ? `It changes the whole domain ${zone.name}, not only this site: ${hosts.length ? `the hosts that run through Cloudflare are ${hosts.join(', ')}` : 'no host runs through Cloudflare yet'}.`
    : `It changes the whole domain ${zone.name}, not only this site; which hosts run through it could not be read (the token needs the row ${ROW.dns}).`;

  // R5: a zone-wide change is asked only with the hosts it touches named.
  const hostsUnknown = `The zone's records could not be read, so the hosts this setting changes cannot be named; the token needs the row ${ROW.dns}`;
  const lines = []; // one per setting and record: { id, title, state, now, want, say }
  for (const s of SETTINGS) {
    const line = { id: s.id, title: s.title, path: s.path, kind: 'setting', def: s };
    lines.push(line);
    const r = await api('GET', `${zoneAt}/settings/${s.api}`);
    if (opts.skip.includes(s.id)) { line.state = 'skipped'; line.now = ok(r) ? r.body.result?.value : undefined; continue; }
    if (!ok(r)) { line.state = 'unread'; line.why = refusal(r, ROW.settings); continue; }
    line.now = r.body.result?.value;
    line.state = isDeepStrictEqual(line.now, s.value) ? 'as-is' : 'change';
    if (line.state === 'change' && !records) { line.state = 'unread'; line.why = hostsUnknown; }
  }
  const botRead = await api('GET', `${zoneAt}/bot_management`);
  const bot = ok(botRead) ? botRead.body.result ?? {} : null;
  for (const b of BOT_LINES) {
    const line = { id: b.id, title: b.title, path: b.path, kind: 'bot', def: b };
    lines.push(line);
    line.now = bot ? Object.fromEntries(Object.keys(b.fields).map((k) => [k, bot[k]])) : undefined;
    // Only the `ai` line reads ai_agents, when Cloudflare lists it (a zone or an answer without it has none to set).
    const agentsListed = b.id === 'ai' && bot && 'ai_agents' in bot;
    if (agentsListed) line.now.ai_agents = bot.ai_agents;
    line.want = agentsListed ? aiWant(b.fields, bot.ai_agents) : b.fields;
    if (opts.skip.includes(b.id)) { line.state = 'skipped'; continue; }
    if (!bot) { line.state = 'unread'; line.why = refusal(botRead, ROW.bot); continue; }
    if (agentsListed && !isAgentMap(bot.ai_agents)) { line.state = 'unread'; line.why = `Cloudflare's ai_agents reads ${show(bot.ai_agents)}, a form this kit does not know`; continue; }
    if (line.want.ai_agents) line.agentsWas = Object.fromEntries(Object.entries(bot.ai_agents).filter(([, v]) => v !== 'disabled'));
    line.state = isDeepStrictEqual(line.now, line.want) ? 'as-is' : 'change';
    if (line.state === 'change' && !records) { line.state = 'unread'; line.why = hostsUnknown; }
  }

  // 6. The records given with --record.
  const recs = opts.records.map((r) => {
    const fullName = r.name === '@' ? zone.name : (r.name === zone.name || r.name.endsWith(`.${zone.name}`) ? r.name : `${r.name}.${zone.name}`);
    const line = { id: 'record', kind: 'record', rec: { ...r, fullName }, title: `${r.type} ${fullName}` };
    lines.push(line);
    if (!records) { line.state = 'unread'; line.why = `Cloudflare refused to list the zone's records (${cfWords(dns.r)}): the token needs the row ${ROW.dns}`; return line; }
    const here = records.filter((x) => x.name === fullName);
    if (r.type === 'TXT') {
      line.beside = here.filter((x) => x.type === 'TXT').map((x) => x.content);
      line.state = here.some((x) => x.type === 'TXT' && unquote(x.content) === unquote(r.content)) ? 'as-is' : 'change';
    } else {
      const address = here.find((x) => ['A', 'AAAA', 'CNAME'].includes(x.type));
      const sameTarget = address && address.type === 'CNAME' && address.content.toLowerCase().replace(/\.$/, '') === r.content;
      if (sameTarget && !address.proxied) line.state = 'as-is';
      else if (sameTarget) { line.state = 'clash'; line.why = `${fullName} already points to ${r.content}, but through Cloudflare (proxied); a verification record must be DNS only. Switch its proxy off by hand (DNS → Records → the record → Proxy status)`; }
      else if (address) { line.state = 'clash'; line.why = `${fullName} already has ${address.type} ${address.content}; this one would point it to ${r.content}. Cloudflare allows one of them, and the script changes no record it did not make: decide which is right and change it by hand`; }
      else if (fullName === host) { line.state = 'clash'; line.why = `${fullName} is the site's own host: the launch makes its address record and replaces any record there, so a verification record cannot be written at it by this script. Add it by hand after the launch`; }
      else line.state = 'change';
    }
    return line;
  });

  // The question, and its code: one key per change it lists.
  const aiLine = lines.find((l) => l.id === 'ai');
  const codeInput = {
    account: account.id, worker, repository, zone: zone.id,
    skip: opts.skip, hosts, records: recs.map((l) => l.rec),
    aiAgents: aiLine.want?.ai_agents ? Object.keys(aiLine.want.ai_agents).sort() : null,
  };
  const lineKey = (l) => (l.kind === 'record' ? `record:${l.rec.type} ${l.rec.fullName} ${l.rec.content}` : `setting:${l.id}`);
  const left = lines.filter((l) => l.state === 'change').map(lineKey);
  const possible = lines.filter((l) => l.kind === 'record' || !opts.skip.includes(l.id)).map(lineKey);
  const code = setupCode(codeInput, left);
  const changes = left.length;

  say(`Cloudflare setup for ${host} (zone ${zone.name}, account ${account.name})`);
  say(`Repository ${repository}, ${model}: ${model === 'two-stage' ? 'production is the live branch, main the preview' : 'main is the live branch'}. Worker ${worker}.`);

  if (changes && !(opts.confirm && codeFits(opts.confirm, codeInput, left, possible))) {
    if (opts.confirm) say('', `The code ${opts.confirm} does not fit this question: it lists something the question you said yes to did not, or something that question covered has changed. Nothing was changed. Here is the question as it stands now.`);
    say('', 'Nothing has been changed yet. If you say yes, I will:');
    let n = 0;
    const item = (text, ...more) => { n++; say(`  ${String(n).padStart(2)}. ${text}`); for (const m of more) say(`      ${m}`); };
    for (const l of lines.filter((x) => x.state === 'change')) {
      if (l.kind === 'record') {
        item(`Write the record ${l.rec.type} ${l.rec.fullName} → ${l.rec.content}, DNS only.`,
          ...(l.beside?.length ? [`It goes beside the TXT records already there, which stay: ${l.beside.join(' · ')}`] : []));
      } else {
        const agents = l.agentsWas ? Object.entries(l.agentsWas).map(([k, v]) => `ai_agents.${k} ${show(v)} → disabled`) : [];
        const now = l.kind === 'bot' ? [...Object.entries(l.def.fields).filter(([k, v]) => !isDeepStrictEqual(l.now[k], v)).map(([k, v]) => `${k} ${show(l.now[k])} → ${show(v)}`), ...agents].join(', ') : `${show(l.now)} → ${show(l.def.value)}`;
        item(`${l.title} (${now}).`, hostsSay, `For a visitor there: ${l.def.visitor}.`, ...(l.want?.ai_agents ? ['Every personal agent ends disabled.'] : []));
      }
    }
    reportQuiet(say, lines, opts);
    sayAiNotes(say, lines);
    say('', workerWords(ctx, state));
    say('Before you say yes: the token\'s Account Resources should name your one account. Its Workers permission reaches every Worker in that account.');
    say('', `To go ahead, run the same command again with: --confirm ${code}`);
    return 3;
  }

  // ---- with the yes (or with nothing to change): carry it out, one call per write.
  const results = { failed: [], waiting: [] };

  // The settings: one write each, read back.
  for (const l of lines.filter((x) => x.kind === 'setting' && x.state === 'change')) {
    const r = await api('PATCH', `${zoneAt}/settings/${l.def.api}`, { json: { value: l.def.value } });
    if (!ok(r)) { l.state = 'hand'; l.why = refusal(r, ROW.settings); continue; }
    const back = await api('GET', `${zoneAt}/settings/${l.def.api}`);
    if (!ok(back) || !isDeepStrictEqual(back.body.result?.value, l.def.value)) {
      l.state = 'hand';
      l.why = `Cloudflare accepted the change, but it reads back as ${ok(back) ? show(back.body.result?.value) : 'nothing'}`;
    } else l.state = 'done';
  }
  const botLines = lines.filter((x) => x.kind === 'bot' && x.state === 'change');
  if (botLines.length) {
    const body = Object.fromEntries(BOT_PUT_FIELDS.filter((k) => k in bot).map((k) => [k, bot[k]]));
    for (const l of botLines) {
      Object.assign(body, l.def.fields);
      // Only the agents that change: Cloudflare merges the map per key (T4-008), so the rest are not overwritten.
      const moves = l.want?.ai_agents ? agentsToDisable(l.now.ai_agents) : {};
      if (Object.keys(moves).length) body.ai_agents = moves;
    }
    const r = await api('PUT', `${zoneAt}/bot_management`, { json: body });
    if (!ok(r)) {
      for (const l of botLines) { l.state = 'hand'; l.why = refusal(r, ROW.bot); }
    } else {
      const back = await api('GET', `${zoneAt}/bot_management`);
      const want = { ...bot, ...body };
      // With the `ai` line written, ai_agents has its own rule: every agent listed before or after reads disabled.
      const strict = botLines.some((l) => l.id === 'ai') && ok(back) && ('ai_agents' in bot || 'ai_agents' in (back.body.result ?? {}));
      const off = ok(back) ? Object.keys(want).filter((k) => !(strict && k === 'ai_agents') && !isDeepStrictEqual(back.body.result?.[k], want[k]))
        .map((k) => `${k} reads ${show(back.body.result?.[k])}, not ${show(want[k])}`) : [];
      if (strict) {
        const first = isAgentMap(bot.ai_agents) ? bot.ai_agents : {};
        const got = back.body.result.ai_agents;
        const disabled = Object.fromEntries([...new Set([...Object.keys(first), ...(isAgentMap(got) ? Object.keys(got) : [])])].map((k) => [k, 'disabled']));
        if (!isAgentMap(got) || Object.keys(first).some((k) => !(k in got)) || Object.values(got).some((v) => v !== 'disabled')) off.push(`ai_agents reads ${show(got)}, not ${show(disabled)}`);
      }
      for (const l of botLines) {
        if (!ok(back)) { l.state = 'hand'; l.why = `Cloudflare accepted the change, but it could not be read back: ${refusal(back, ROW.bot)}`; } else if (off.length) { l.state = 'hand'; l.why = `Cloudflare accepted the change, but ${off.join('; ')}`; } else l.state = 'done';
      }
    }
  }

  // The records: one create each, read back, then asked of the zone's nameservers.
  for (const l of recs.filter((x) => x.state === 'change')) {
    const r = await api('POST', `${zoneAt}/dns_records`, { json: {
      type: l.rec.type, name: l.rec.fullName, ttl: 1, proxied: false,
      content: l.rec.type === 'TXT' && !/^".*"$/s.test(l.rec.content) ? `"${l.rec.content}"` : l.rec.content,
    } });
    if (!ok(r)) {
      if (r.body?.errors?.some((e) => e.code === 81058)) { l.state = 'as-is'; continue; } // written meanwhile
      l.state = 'hand';
      l.why = refusal(r, ROW.dns);
      continue;
    }
    const back = await api('GET', `${zoneAt}/dns_records/${r.body.result?.id}`);
    const got = back.body?.result;
    if (!ok(back) || got?.type !== l.rec.type || got?.name !== l.rec.fullName || unquote(String(got?.content)).toLowerCase() !== unquote(l.rec.content).toLowerCase()) {
      l.state = 'hand';
      l.why = 'Cloudflare accepted it, but it does not read back as written';
    } else l.state = 'done';
  }
  const asked = recs.filter((l) => l.state === 'done' || l.state === 'as-is');
  if (asked.length) {
    const seen = await askNameservers(zone, asked.map((l) => l.rec), { resolverAt, clock });
    asked.forEach((l, i) => { l.served = seen[i]; });
  }

  // The report.
  for (const l of lines) reportLine(say, l, hostsSay);
  reportQuiet(say, lines, opts, { done: true });
  sayAiNotes(say, lines);
  for (const l of lines) if (['hand', 'unread', 'clash'].includes(l.state)) results.failed.push(l.title);

  say('', workerWords(ctx, state));
  if (state.kind === 'missing') {
    for (const l of missingWorkerSteps(ctx)) say(l);
    results.waiting.push('the Worker');
  } else if (state.kind === 'pending') results.waiting.push('the first build');

  say('');
  if (results.failed.length) {
    say(`Not finished: ${results.failed.join(', ')} ${results.failed.length === 1 ? 'needs' : 'need'} you (above). Status 1.`);
    return 1;
  }
  if (results.waiting.length) {
    say(`Waiting for ${results.waiting.join(' and ')}. Run the same command again in a few minutes. Status 4.`);
    return 4;
  }
  say('Setup is done, as far as Cloudflare\'s API shows: the settings were read back through the API only. Requests to the domain come on launch day, which checks them from outside and adds the NEL header rule if the headers are still sent.');
  say(`On launch day, once the site is finished: node cloudflare-setup.mjs launch${opts.skip.map((id) => ` --skip ${id}`).join('')}`);
  return 0;
}

// src/config.ts at a commit: PROD_BRANCH, and the host of SITE.url, which must not be the starter's.
async function readConfig(git, sha, where) {
  const config = await git('show', `${sha}:src/config.ts`);
  if (config.code !== 0) throw new Stop(1, `src/config.ts is missing at the head of ${where} (${short(sha)}): is this a site made with the kit?`);
  const prodBranch = /^export const PROD_BRANCH = ['"]([^'"]*)['"];?/m.exec(config.stdout)?.[1];
  const siteBlock = config.stdout.slice(config.stdout.search(/^export const SITE = \{/m));
  const siteUrl = /^\s*url:\s*['"]([^'"]+)['"]/m.exec(siteBlock)?.[1];
  if (!prodBranch) throw new Stop(1, `src/config.ts at the head of ${where} has no line "export const PROD_BRANCH = '…';".`);
  if (!siteUrl) throw new Stop(1, `src/config.ts at the head of ${where} has no SITE.url.`);
  if (STOCK_URL.test(siteUrl)) throw new Stop(1, `SITE.url in src/config.ts is still the starter's https://example.com. Set your own domain there, on ${where}, first.`);
  try {
    return { prodBranch, host: new URL(siteUrl).hostname.toLowerCase() };
  } catch {
    throw new Stop(1, `SITE.url in src/config.ts is not an address: ${siteUrl}`);
  }
}

function reportQuiet(say, lines, opts, { done = false } = {}) {
  const asIs = lines.filter((l) => l.state === 'as-is' && l.kind !== 'record');
  const left = lines.filter((l) => l.state === 'skipped');
  const unread = lines.filter((l) => l.state === 'unread');
  const clash = lines.filter((l) => l.state === 'clash');
  if (!done && asIs.length) say('', `Already as the checklist wants: ${asIs.map((l) => l.title).join('; ')}.`);
  const stays = (l) => (l.now === undefined ? 'stays as it is (it could not be read)'
    : `stays ${l.kind === 'bot' ? Object.entries(l.now).map(([k, v]) => `${k} ${show(v)}`).join(', ') : show(l.now)}`);
  if (left.length) say('', `Left out on purpose (--skip): ${left.map((l) => `${l.title.split(':')[0]} ${stays(l)}`).join('; ')}.`);
  if (!done) {
    for (const l of [...unread, ...clash]) say(`By hand: ${l.title}. ${l.why}. ${l.path ? `Dashboard: ${l.path}.` : ''}`.trimEnd());
  }
}

function sayAiNotes(say, lines) {
  const ai = lines.find((l) => l.id === 'ai');
  const notes = aiNotes(ai.now, ai.state);
  if (notes.length) say('', ...notes);
}

function reportLine(say, l, hostsSay) {
  if (l.kind === 'record') {
    const served = l.served === true ? 'the nameservers show it' : 'written; the nameservers do not show it yet';
    if (l.state === 'done') say(`  done     ${l.title} → ${l.rec.content}, DNS only. Read back through the API; ${served}.`);
    else if (l.state === 'as-is') say(`  as is    ${l.title} → ${l.rec.content} was there already${l.served === true ? '; the nameservers show it' : '; the nameservers do not show it yet'}.`);
    else if (l.state === 'hand' || l.state === 'clash' || l.state === 'unread') say(`  by hand  ${l.title} → ${l.rec.content}: ${l.why}.`);
    return;
  }
  const now = l.kind === 'bot' ? null : show(l.now);
  const wasAgents = l.agentsWas && Object.keys(l.agentsWas).length ? `personal agents were: ${Object.entries(l.agentsWas).map(([k, v]) => `${k} ${show(v)}`).join(', ')}` : '';
  if (l.state === 'done') say(`  done     ${l.title}${now ? ` (was ${now})` : wasAgents ? ` (${wasAgents})` : ''}. Read back through the API only. ${hostsSay}`);
  else if (l.state === 'as-is') say(`  as is    ${l.title}.`);
  else if (l.state === 'hand' || l.state === 'unread') say(`  by hand  ${l.title}: ${l.why}. Dashboard: ${l.path}.`);
}

// Is each record served by the zone's own nameservers? Asked within the run, a few times; a record
// not seen is "not yet", never a failure.
async function askNameservers(zone, recs, { resolverAt, clock }) {
  const seen = recs.map(() => false);
  let servers = [];
  if (resolverAt) servers = [resolverAt];
  else {
    for (const ns of zone.name_servers ?? []) {
      try {
        servers.push(...await withTimeout(dnsPromises.resolve4(ns), Math.min(3000, clock.left() - 5000)));
      } catch { /* that nameserver's address could not be looked up: ask the others */ }
    }
  }
  if (!servers.length) return seen;
  for (let attempt = 0; attempt < 3 && seen.includes(false); attempt++) {
    if (attempt) await new Promise((r) => setTimeout(r, 2000));
    if (clock.left() < 6000) break;
    const resolver = new Resolver({ timeout: 2000, tries: 1 });
    resolver.setServers(servers);
    await Promise.all(recs.map(async (rec, i) => {
      if (seen[i]) return;
      try {
        if (rec.type === 'TXT') {
          const answers = await withTimeout(promisify(resolver, 'resolveTxt', rec.fullName), 3000);
          seen[i] = answers.some((chunks) => chunks.join('') === unquote(rec.content));
        } else {
          const answers = await withTimeout(promisify(resolver, 'resolveCname', rec.fullName), 3000);
          seen[i] = answers.some((a) => a.toLowerCase().replace(/\.$/, '') === rec.content);
        }
      } catch { /* not there yet, or no answer */ }
    }));
    resolver.cancel();
  }
  return seen;
}
const promisify = (resolver, fn, name) => new Promise((resolve, reject) => {
  resolver[fn](name, (err, value) => (err ? reject(err) : resolve(value)));
});
function withTimeout(promise, ms) {
  let timer;
  return Promise.race([
    promise,
    new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('timed out')), Math.max(ms, 1)); }),
  ]).finally(() => clearTimeout(timer));
}

// The token: CLOUDFLARE_API_TOKEN, or else .dev.vars, which git must neither track nor fail to
// ignore. The file is not read until both are known.
async function readToken(root, git) {
  const fromEnv = (process.env.CLOUDFLARE_API_TOKEN ?? '').trim();
  if (fromEnv) return fromEnv;
  const file = path.join(root, '.dev.vars');
  if (!existsSync(file)) {
    throw new Stop(1, 'No token: set CLOUDFLARE_API_TOKEN for this session, or put CLOUDFLARE_API_TOKEN=… in .dev.vars (a file git ignores). The checklist\'s section 6 says how to make it.');
  }
  const tracked = await git('-C', root, 'ls-files', '--error-unmatch', '--', '.dev.vars');
  if (tracked.code === 0) {
    throw new Stop(1, 'git tracks .dev.vars, so a token in it would be committed. The file was not read. Stop tracking it (git rm --cached .dev.vars), add .dev.vars to .gitignore, and make a new token: the old one may already be in the history.');
  }
  const ignored = await git('-C', root, 'check-ignore', '-q', '--', '.dev.vars');
  if (ignored.code !== 0) {
    throw new Stop(1, '.dev.vars is not ignored by git, so the next commit could take the token with it. The file was not read. Add .dev.vars to .gitignore, then run this again.');
  }
  const m = /^\s*CLOUDFLARE_API_TOKEN\s*=\s*["']?([^"'\s]+)["']?\s*$/m.exec(readFileSync(file, 'utf8'));
  if (!m) throw new Stop(1, '.dev.vars has no line CLOUDFLARE_API_TOKEN=….');
  return m[1];
}

// ---------------------------------------------------------------- the launch stage

// The checklist's rule that removes the NEL headers (its section 3, step 4), as the trials wrote it
// (T2-023): found again by its description.
const NEL_RULE = {
  action: 'rewrite', expression: 'true', description: 'Remove NEL headers',
  action_parameters: { headers: { NEL: { operation: 'remove' }, 'Report-To': { operation: 'remove' } } }, enabled: true,
};
const RUN_DIR = 'setup-run'; // in the site's folder, ignored by git: the lock, the kept record, pending.json
// Beside this file's real path: the skills are symlinked into place, as the run-as-program check below knows.
const CHECK_SCRIPT = path.join(path.dirname(realpathSync(fileURLToPath(import.meta.url))), 'cloudflare-check.mjs');

// What a `fail` of each check item gives at the end of a launch run: 1; 0; a --skip id, which makes
// it 0 when the run was given it; or null for an item that never fails (it gives 1 if it does).
export const LAUNCH_FAIL = {
  pages: 1, 'build-settings': null, domain: 1, 'fail-open': null, canonical: 'canonical', https: 'https', tls: null,
  hsts: null, nel: 'nel-rule', bot: 'bot', analytics: 0, email: 'email', hints: null, ai: null, robots: 1, build: 1, scripts: null,
  'workers-dev': null, previews: null,
};

// The exit status a launch run takes from the check's JSON, in the plan's order: no answer or an item
// not judged gives 1 whatever the rest says; then a counted `fail` gives 1; then 0.
export function launchVerdict(check, skip) {
  const silent = check.unanswered ?? [];
  const blocked = check.results.filter((r) => r.blocked).map((r) => r.id);
  const fails = check.results.filter((r) => r.state === 'fail');
  const let0 = (r) => LAUNCH_FAIL[r.id] === 0 || (typeof LAUNCH_FAIL[r.id] === 'string' && skip.includes(LAUNCH_FAIL[r.id]));
  const counted = fails.filter((r) => !let0(r));
  const code = silent.length || blocked.length || counted.length ? 1 : 0;
  return { code, silent, blocked, counted, passed: fails.filter(let0) };
}

// The code of the launch question: its end state, the record it replaces (as printed) and the actions it
// listed (`attach`, `route`, `nel`), as for setup. A later run takes the code for any part of that list,
// so the stage's own writes keep it; an action the question did not list needs a new yes (R1).
export function launchCode(input, listed = []) {
  const end = {
    stage: 'launch', worker: input.worker, account: input.account, zone: input.zone, host: input.host, commit: input.commit,
    record: input.record ?? null, nelRule: input.nelRule, hosts: input.nelRule ? [...input.hosts].sort() : [],
  };
  return createHash('sha256').update(JSON.stringify({ end, listed: [...listed].sort() })).digest('hex').slice(0, 16);
}

// Does `code` fit what is left to do? As codeFits: some list made of all that is left and any of the
// actions that could since have been done gives it.
export function launchFits(code, input, left, possible) {
  const done = possible.filter((k) => !left.includes(k));
  for (let mask = 0; mask < 2 ** done.length; mask++) {
    if (launchCode(input, [...left, ...done.filter((_, i) => mask & (2 ** i))]) === code) return true;
  }
  return false;
}

// The text of a regular expression or a grep pattern that stands for a fixed string: "\[MISSING:" is
// "[MISSING:". Anything that is more than a fixed string gives null.
export function fixedText(pattern) {
  const unescaped = pattern.replace(/\\[[\]().*+?^${}|\\/:-]/g, '');
  if (/[[\]().*+?^${}|\\]/.test(unescaped)) return null;
  return pattern.replace(/\\(.)/g, '$1');
}

// Script step 8's reading of the site at the commit that goes live: the list of pages still unfilled,
// and the draft token in src/ and public/. `cannot` says why the script cannot tell.
async function draftsAt(git, sha) {
  const cannot = (why) => ({ cannot: why });
  const spec = await git('show', `${sha}:tests/placeholders.spec.ts`);
  if (spec.code !== 0) return cannot('tests/placeholders.spec.ts is missing at that commit');
  const list = /^const UNFILLED_UNTIL_LAUNCH = new Set<string>\(\[(.*)\]\);$/m.exec(spec.stdout);
  const tokenLine = /^const DRAFT_TOKEN = \/\^(.+)\/;$/m.exec(spec.stdout);
  if (!list || list[1].replace(/'[^']*'|"[^"]*"/g, '').replace(/[\s,]/g, '')) return cannot('its UNFILLED_UNTIL_LAUNCH line is not in the starter\'s form, so the script cannot read it');
  if (!tokenLine) return cannot('its DRAFT_TOKEN line is not in the starter\'s form, so the script cannot read it');
  const token = fixedText(tokenLine[1]);
  if (!token) return cannot(`its DRAFT_TOKEN (/^${tokenLine[1]}/) is more than a fixed text, so the script cannot search for it`);
  const ci = await git('show', `${sha}:.github/workflows/ci.yml`);
  const ciLine = ci.code === 0 ? /grep -rnI '([^']+)' src public/.exec(ci.stdout) : null;
  if (!ciLine) return cannot('.github/workflows/ci.yml at that commit has no search for the draft token in the starter\'s form');
  const ciToken = fixedText(ciLine[1]);
  if (ciToken !== token) return cannot(`DRAFT_TOKEN in tests/placeholders.spec.ts is "${token}" and ci.yml searches for "${ciToken ?? ciLine[1]}": the two must be the same`);
  const unfilled = [...list[1].matchAll(/'([^']*)'|"([^"]*)"/g)].map((m) => m[1] ?? m[2]);
  const found = await git('grep', '-n', '-I', '-F', '-e', token, sha, '--', 'src', 'public');
  if (found.code > 1) return cannot(`git could not search the commit for "${token}"`);
  const hits = found.code === 0 ? found.stdout.split('\n').filter(Boolean).map((l) => l.slice(sha.length + 1).split(':').slice(0, 2).join(':')) : [];
  return { token, unfilled, hits };
}

// The nameservers' addresses, for the check's lookups of the domain (script step 11). None found is
// a wait, never a quiet fall back to this computer's own lookup, which is what the option avoids.
export async function nameserverIps(zone, { resolverAt, clock, resolve4 = (n) => dnsPromises.resolve4(n) }) {
  if (resolverAt) return [resolverAt];
  const ips = [];
  for (const ns of zone.name_servers ?? []) {
    if (clock.left() < 4000) break;
    try {
      ips.push(...await withTimeout(resolve4(ns), 3000));
    } catch { /* ask the others */ }
  }
  // One message for every way of finding none, with no guess at the cause.
  if (!ips.length) {
    throw new Stop(4, `This run found no address for the zone's nameservers (Cloudflare lists: ${(zone.name_servers ?? []).join(', ') || 'none'}), and the domain is asked only through them. Run the same command again in a minute; if this repeats, look them up by hand (dig NS ${zone.name ?? 'your domain'}).`);
  }
  return [...new Set(ips)];
}

// The check script's arguments: the domain (or, in the tests, the loopback address standing in for it),
// the Worker's version link, the commit, and the nameservers when the domain is asked by its name.
export function checkArgs({ site, preview, commit, timeoutS, only, nameservers, configFile }) {
  return [CHECK_SCRIPT, site, '--json', '--timeout', String(timeoutS), '--site', '.', '--config', configFile, '--preview', preview, '--build', commit,
    ...(only ? ['--only', only.join(',')] : []), ...(nameservers?.length ? ['--nameserver', nameservers.join(',')] : [])];
}

async function runCheck(ctx, { commit, only }) {
  const timeoutS = Math.min(120, Math.floor(ctx.clock.left() / 4000));
  if (timeoutS < 1) throw new Deadline();
  const nameservers = ctx.siteOverride ? null : await nameserverIps(ctx.zone, ctx);
  const args = checkArgs({ site: ctx.siteOverride ?? ctx.host, preview: ctx.state.link, commit, timeoutS, only, nameservers, configFile: ctx.configFile });
  const r = await runProgram(process.execPath, args, { cwd: ctx.root, env: ctx.childEnv(), clock: ctx.clock });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { /* reported below */ }
  if (!json || !Array.isArray(json.results)) throw new Stop(1, `The check script did not answer as expected (status ${r.code}): ${(r.stderr || r.stdout).trim().split('\n')[0] ?? ''}`);
  return Object.assign(json, { by: Object.fromEntries(json.results.map((x) => [x.id, x])) });
}

// ---- the folder and the files of a launch run

// setup-run/ holds a .gitignore of `*`, and is refused if git tracks a file in it.
async function runFolder(ctx) {
  const dir = path.join(ctx.root, RUN_DIR);
  const tracked = await ctx.git('-C', ctx.root, 'ls-files', '--', RUN_DIR);
  if (tracked.code !== 0 || tracked.stdout.trim()) throw new Stop(1, `git tracks a file in ${RUN_DIR}/ (or could not be asked): that folder holds the replaced record and the lock, and must stay out of git. Remove it from git (git rm --cached), then run this again.`);
  mkdirSync(dir, { recursive: true, mode: 0o700 });
  if (!existsSync(path.join(dir, '.gitignore'))) writeFileSync(path.join(dir, '.gitignore'), '*\n');
  return dir;
}
// A file appears whole or not at all: written beside, then renamed.
function writeAtomic(file, text) {
  const tmp = `${file}.tmp-${process.pid}`;
  writeFileSync(tmp, text, { mode: 0o600 });
  renameSync(tmp, file);
}
// The record as it may be put back: the eight fields it is read with, as JSON sends them.
const noteOf = (record) => JSON.parse(JSON.stringify(Object.fromEntries(RECORD_FIELDS.map((k) => [k, record[k]]))));
const KEPT_AT = /^\d{8}T\d{6}Z\.json$/;
// The kept file of a record this host's launch replaced: its record, or a Stop that says what is wrong.
function readKept(dir, name, host) {
  const bad = (why) => new Stop(1, `${RUN_DIR}/${name} ${why}. It holds the record that was deleted from ${host}: look at it before anything else, and add the record back by hand (DNS → Records → Add record) if the host has none. Nothing was changed.`);
  if (!name.startsWith(`replaced-${host}-`) || !KEPT_AT.test(name.slice(`replaced-${host}-`.length))) throw bad('is not a name this script wrote');
  let j;
  try { j = JSON.parse(readFileSync(path.join(dir, name), 'utf8')); } catch { throw bad('cannot be read'); }
  if (j?.host !== host || typeof j.record !== 'object' || j.record === null || ['type', 'name', 'content'].some((k) => typeof j.record[k] !== 'string')) throw bad('does not hold a record of this host');
  return { name, note: noteOf(j.record) };
}
// pending.json marks a launch between its DELETE and its PUT; it names the kept file.
function readPending(dir, host) {
  const f = path.join(dir, 'pending.json');
  if (!existsSync(f)) return null;
  let j;
  try { j = JSON.parse(readFileSync(f, 'utf8')); } catch { throw new Stop(1, `${RUN_DIR}/pending.json cannot be read. It marks a launch that stopped after deleting the record of ${host}: look at the newest ${RUN_DIR}/replaced-${host}-… file, add that record back by hand if the host has none, then delete pending.json.`); }
  if (j?.host !== host || typeof j.file !== 'string') throw new Stop(1, `${RUN_DIR}/pending.json is not for ${host}. Look at it, then delete it if the record it names is back.`);
  return { path: f, ...readKept(dir, j.file, host) };
}
// The newest kept file of this host, for the code of a run that comes after the attach.
function lastKept(dir, host) {
  const prefix = `replaced-${host}-`;
  const names = existsSync(dir) ? readdirSync(dir).filter((f) => f.startsWith(prefix) && KEPT_AT.test(f.slice(prefix.length))).sort() : [];
  return names.length ? readKept(dir, names[names.length - 1], host) : null;
}
const recordWords = (note) => ['  The record, as Cloudflare had it:', ...JSON.stringify(note, null, 2).split('\n').map((l) => `    ${l}`)];
const byHand = (host) => `Add it back by hand if ${host} has none: DNS → Records → Add record, with those values.`;

async function launchStage(opts, io) {
  const siteOverride = loopback('CLOUDFLARE_SETUP_SITE', process.env.CLOUDFLARE_SETUP_SITE, { origin: true });
  const ctx = await prepare(opts, io);
  ctx.siteOverride = siteOverride;
  const run = { release: null };
  try {
    return await launchRun(opts, ctx, run);
  } finally {
    if (run.release) run.release();
  }
}

// Is the commit `a` an ancestor of `b`? Then the Worker is only behind: a build may still be coming.
async function isAncestor(git, a, b) {
  const r = await git('merge-base', '--is-ancestor', a, b);
  return r.code === 0;
}

async function launchRun(opts, ctx, run) {
  const { say, git, gitOut, api, g, clock, prodBranch, host, model, prodSha, mainSha, zone, account, worker, repository, state, configFile } = ctx;
  if (ctx.siteOverride) say(`Test mode: the domain is asked at ${ctx.siteOverride}.`);
  const dir = await runFolder(ctx);
  takeLock(dir, run, say);
  const zoneAt = `/zones/${zone.id}`;
  const skip = (id) => opts.skip.includes(id);

  say(`Cloudflare launch for ${host} (zone ${zone.name}): Worker ${worker}.`);
  say(`Repository ${repository}, ${model}: ${model === 'two-stage' ? `${prodBranch} goes live` : 'main goes live'}.`);

  // 1. The Worker, the domains, the host's records.
  if (state.kind === 'missing') throw new Stop(1, `The Worker ${worker} is not on Cloudflare yet. Run the setup stage first: node cloudflare-setup.mjs setup`);
  if (state.kind === 'pending') {
    say('', `${workerWords(ctx, state)} Nothing was changed. Status 4.`);
    return 4;
  }
  const domains = await api('GET', `/accounts/${account.id}/workers/domains`);
  if (!ok(domains) || !Array.isArray(domains.body?.result)) throw new Stop(1, `Cloudflare did not list the domains of the Worker ${worker}: ${refusal(domains, ROW.workers)}. Nothing was changed.`);
  const onThis = domains.body.result.some((d) => d.hostname === host && d.service === worker);
  const onOther = domains.body.result.find((d) => d.hostname === host && d.service !== worker);
  if (onOther) throw new Stop(1, `${host} is attached to the Worker ${onOther.service}, not to ${worker}. The script moves no domain from one Worker to another: take it off that Worker by hand (Workers & Pages → ${onOther.service} → Settings → Domains & Routes) if that is wanted. Nothing was changed.`);
  const dns = await allPages(api, `${zoneAt}/dns_records`, 100);
  if (!dns.items) {
    throw new Stop(1, `Cloudflare refused to list the zone's records (${cfWords(dns.r)}): the token needs the row ${ROW.dns}. The script will not attach a domain whose records it cannot see. "Going live" in CLOUDFLARE_FIRST_DEPLOY.md has the way by hand.`);
  }
  const here = dns.items.filter((r) => r.name === host);
  // Cloudflare's own record for a domain on a Worker is read-only; it is not the owner's.
  const ownRecord = (r) => r.meta?.read_only === true;
  const address = here.filter((r) => ADDRESS_TYPES.includes(r.type) && !(onThis && ownRecord(r)));
  const otherHosts = [...new Set(dns.items.filter((r) => r.proxied && ADDRESS_TYPES.includes(r.type) && r.name !== host).map((r) => r.name))].sort();

  let pending = readPending(dir, host);
  if (pending && (onThis || address.length)) {
    rmSync(pending.path, { force: true });
    say(`${RUN_DIR}/pending.json is removed: ${onThis ? `${host} is on the Worker` : `${host} has a record again`}.`);
    pending = null;
  }
  if (pending) {
    say('', `A launch stopped after it deleted the record of ${host}, and the host has no record. The record is kept in ${RUN_DIR}/${pending.name}:`, ...recordWords(pending.note), `  ${byHand(host)}`);
  }
  const mode = onThis ? 'attached' : address.length === 1 ? 'fresh' : pending ? 'recover' : 'fresh';
  const replacing = mode === 'fresh' && address.length === 1 ? address[0] : null;
  let kept = mode === 'recover' ? pending : mode === 'attached' ? lastKept(dir, host) : null;
  const noteNow = replacing ? noteOf(replacing) : kept?.note ?? null;

  // The conditions (script step 1) and the route commit's: collected, then refused together.
  const stops = [];
  const headSha = await gitOut('rev-parse', 'HEAD');
  const tree = await gitOut('status', '--porcelain');
  if (tree) stops.push(`The working tree has changes (${tree.split('\n')[0].trim()}${tree.includes('\n') ? ', …' : ''}). Commit them or put them away: the route commit is written on a clean tree.`);
  const headCfg = await readWorkersConfig(git, 'HEAD');
  if (headCfg.file !== configFile || headCfg.cfg.name !== worker) stops.push(`HEAD's Workers config is ${headCfg.file} naming ${headCfg.cfg.name}; main's is ${configFile} naming ${worker}. The route commit is for the Worker this run attaches: bring HEAD level with main first.`);
  if (headCfg.cfg.account_id && headCfg.cfg.account_id !== account.id) stops.push(`${headCfg.file} at HEAD names the account ${headCfg.cfg.account_id}, and the zone is in ${account.id}.`);
  const headRoutes = routesOf(headCfg.cfg, headCfg.file);
  if (headRoutes.some((r) => r !== host)) stops.push(`${headCfg.file} at HEAD routes ${headRoutes.filter((r) => r !== host).join(', ')}: the script manages the route of ${host} only.`);
  const needsRoute = !(headRoutes.length === 1 && headRoutes[0] === host);
  if (needsRoute && headSha !== mainSha) stops.push(`HEAD (${short(headSha)}) is not the head of main on GitHub (${short(mainSha)}). The route commit is written on top of main only: bring this folder level with it (git fetch origin, then check out main at origin/main), then run this again.`);
  let waitFor = null;
  let commit = state.sha;
  if (mode !== 'attached') {
    commit = prodSha;
    if (state.sha !== prodSha) {
      if (await isAncestor(git, state.sha, prodSha)) waitFor = `the Worker to serve ${short(prodSha)}, the head of ${prodBranch} (its version link serves ${short(state.sha)}, an earlier commit)`;
      else stops.push(`The Worker's version link serves ${short(state.sha)}, which is not the head of ${prodBranch} (${short(prodSha)}) or an earlier commit of it. Deploy the head of ${prodBranch} first.`);
    }
    // The legal segments below are LEGAL_LAST_SEGMENTS in the starter's tests/placeholders.spec.ts; change both.
    const drafts = await draftsAt(git, prodSha);
    if (drafts.cannot) stops.push(`At ${short(prodSha)}, ${drafts.cannot}. So the script cannot tell whether the site is finished. The domain can be attached by hand ("Going live" in CLOUDFLARE_FIRST_DEPLOY.md).`);
    else {
      if (drafts.unfilled.length) stops.push(`At ${short(prodSha)}, UNFILLED_UNTIL_LAUNCH in tests/placeholders.spec.ts still lists ${drafts.unfilled.join(', ')}: fill ${drafts.unfilled.length === 1 ? 'that page' : 'those pages'}, ${drafts.unfilled.some((u) => /^(privacy|datenschutz|impressum|legal-notice)$/.test(u.split('/').filter(Boolean).pop() ?? '')) ? 'clear the draft notice on a legal page as AGENTS.md section 5 says, ' : ''}and empty the list first (new-website §4).`);
      if (drafts.hits.length) stops.push(`At ${short(prodSha)}, the search for "${drafts.token}" in src/ and public/ finds ${drafts.hits.join(', ')}: fill ${drafts.hits.length === 1 ? 'it' : 'them'} first.`);
    }
    if (address.length > 1) stops.push(`${host} has ${address.length} address records (${address.map((r) => `${r.type} ${r.content}`).join(', ')}). The script replaces one record and deletes no other: remove the others by hand ("Going live" in CLOUDFLARE_FIRST_DEPLOY.md).`);
    const besides = host === zone.name ? [] : here.filter((r) => !ADDRESS_TYPES.includes(r.type));
    if (besides.length) stops.push(`${host} also has ${besides.map((r) => `a ${r.type} record`).join(', ')}, and the domain's own record cannot stand beside a record of another type below the apex. Move or remove ${besides.length === 1 ? 'it' : 'them'} by hand ("Going live").`);
    const pagesCname = address.find((r) => r.type === 'CNAME' && /\.pages\.dev\.?$/i.test(String(r.content)));
    if (pagesCname) stops.push(`${host} is a CNAME to ${pagesCname.content}: the site is live on Cloudflare Pages. This script does not move a live Pages site: docs/MOVE-TO-WORKERS.md says how.`);
  }
  if (stops.length) {
    say('', `Not launched: the script does not attach ${host} while any of these holds.`);
    for (const s of stops) say(`  - ${s}`);
    say('These are the script\'s own stops, not the launch check: that stays new-website §4 and the site\'s tests.');
    throw new Stop(1, `${stops.length === 1 ? 'one condition' : `${stops.length} conditions`} of the launch ${stops.length === 1 ? 'is' : 'are'} not met (above). Nothing was changed.`);
  }
  if (waitFor) {
    say('', `Waiting for ${waitFor}. Nothing was changed. Run the same command again in a few minutes. Status 4.`);
    return 4;
  }

  // ---- the question.
  const nelRule = !skip('nel-rule');
  const codeInput = { worker, account: account.id, zone: zone.id, host, commit, record: noteNow, nelRule, hosts: otherHosts };
  const possible = ['attach', 'route', ...(nelRule ? ['nel'] : [])];
  const fits = (left) => Boolean(opts.confirm) && launchFits(opts.confirm, codeInput, left, possible);
  const nelLine = `If the domain still sends the NEL headers: add the checklist's rule "Remove NEL headers" to the zone's response header rules. It changes the whole domain ${zone.name}: ${otherHosts.length ? `besides ${host}, the hosts that run through Cloudflare are ${otherHosts.join(', ')}` : 'no other host runs through Cloudflare'}.`;
  const ask = (lines, listed, intro) => {
    const code = launchCode(codeInput, listed);
    if (opts.confirm) say('', `The code ${opts.confirm} does not fit this question: it lists something the question you said yes to did not, or the commit, the Worker, the domain, the record, the hosts it names or a --skip have changed. Nothing was changed. Here is the question as it stands now.`);
    if (intro) say('', intro);
    say('', 'Nothing has been changed yet. If you say yes, I will:');
    lines.forEach((t, i) => say(...(Array.isArray(t) ? [`  ${String(i + 1).padStart(2)}. ${t[0]}`, ...t.slice(1).map((m) => `      ${m}`)] : [`  ${String(i + 1).padStart(2)}. ${t}`])));
    say('These are the script\'s own checks, not the launch check: that stays new-website §4 and the site\'s tests.');
    say('', `To go ahead, run the same command again with: --confirm ${code}`);
    return 3;
  };
  const leftNow = [...(mode !== 'attached' ? ['attach'] : []), ...(needsRoute ? ['route'] : [])];
  if (leftNow.length && !fits(leftNow)) {
    const lines = [];
    if (mode !== 'attached') {
      if (noteNow && mode === 'recover') lines.push([`The record of ${host} is already deleted and kept in ${RUN_DIR}/. Attach ${host} now; a refused attach puts it back at once:`, ...recordWords(noteNow)]);
      else if (noteNow) lines.push([`Delete the record of ${host}, after keeping it in ${RUN_DIR}/ (it is printed here in full, and a refused attach puts it back at once):`, ...recordWords(noteNow)]);
      else lines.push(`${host} has no record to replace.`);
      lines.push(`Attach ${host} to the Worker ${worker} (Cloudflare makes the record that points it there).${host === zone.name ? ' A www that is a CNAME to the apex is not attached by this.' : ''}`);
    }
    if (needsRoute) lines.push(`Write one commit in this folder that lists ${host} as a custom-domain route in ${configFile}. It is not pushed: on the owner's word the assistant pushes it, so the next build keeps the domain.`);
    if (mode !== 'attached') lines.push(`This makes the site public: https://${host}/ serves commit ${short(commit)} (${prodBranch}). Visitors may get errors for a few minutes while Cloudflare takes the domain on.`);
    if (nelRule) lines.push(nelLine);
    return ask(lines, possible.filter((k) => k !== 'attach' || mode !== 'attached').filter((k) => k !== 'route' || needsRoute));
  }

  // ---- the yes. Steps 2 to 4: note the record, delete it, attach.
  let replaced = noteNow ? { note: noteNow, name: kept?.name ?? null } : null;
  if (mode !== 'attached') {
    if (clock.left() < HOST_RESERVE_MS) {
      say('', `This run has ${Math.floor(clock.left() / 1000)} seconds left, and replacing the record and attaching the domain needs ${HOST_RESERVE_MS / 1000}. Nothing was written. Run the same command again. Status 4.`);
      return 4;
    }
    if (replacing) {
      const exp = await api('GET', `${zoneAt}/dns_records/export`);
      if (exp.status !== 200 || !/^\S+\s+\d+\s+IN\s+SOA\s+\S+/m.test(exp.text)) throw new Stop(1, `The zone's DNS export has no SOA record (HTTP ${exp.status}); not going on without a copy of the zone. Nothing was changed.`);
      const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+/, '');
      const name = `replaced-${host}-${stamp}.json`;
      if (existsSync(path.join(dir, name))) throw new Stop(1, `${RUN_DIR}/${name} exists already: two launches in one second. Run this again. Nothing was changed.`);
      writeAtomic(path.join(dir, name), `${JSON.stringify({ host, zone: zone.name, saved: new Date().toISOString(), record: replacing, export: exp.text }, null, 2)}\n`);
      writeAtomic(path.join(dir, 'pending.json'), `${JSON.stringify({ host, file: name })}\n`);
      kept = { name, note: noteNow };
      replaced = { note: noteNow, name };
      say('', `  kept     The record ${replacing.type} ${replacing.content}, ${replacing.proxied ? 'proxied' : 'DNS only'}, is saved in ${RUN_DIR}/${name}, with the zone's export. The script never deletes that file.`);
    }
    g.note = noteNow;
    if (replacing) {
      g.recordId = replacing.id;
      const del = await api('DELETE', `${zoneAt}/dns_records/${replacing.id}`);
      g.recordId = null;
      if (!ok(del)) {
        rmSync(path.join(dir, 'pending.json'), { force: true });
        throw new Stop(1, `Cloudflare did not delete the record of ${host}: ${refusal(del, ROW.dns)}. The record is as it was. Nothing else was changed.`);
      }
      say(`  done     Deleted ${replacing.type} ${host}.`);
    }
    let put;
    try {
      put = await api('PUT', `/accounts/${account.id}/workers/domains`, { json: { hostname: host, service: worker, zone_id: zone.id, environment: 'production' } });
    } catch (e) {
      if (noteNow) say('', `The attach got no answer, so ${host} may have no record now. The record is kept in ${RUN_DIR}/${kept.name}:`, ...recordWords(noteNow), `  ${byHand(host)}`, 'The next run reads Cloudflare first and carries on from there.');
      throw e;
    }
    if (!ok(put)) {
      if (!noteNow) throw new Stop(1, `Cloudflare did not attach ${host} to the Worker ${worker}: ${refusal(put, ROW.workers)}. Nothing was changed.`);
      let back;
      try {
        back = await api('POST', `${zoneAt}/dns_records`, { json: noteNow });
      } catch {
        back = { status: 0, body: null };
      }
      if (!ok(back)) {
        throw new Stop(1, `Cloudflare did not attach ${host}: ${cfWords(put)}. The record was deleted first, and putting it back failed too (${back.status ? cfWords(back) : 'no answer'}). ${host} has no record now. The record is kept in ${RUN_DIR}/${kept.name}:`,
          ...recordWords(noteNow), `${byHand(host)} ${RUN_DIR}/pending.json stays until the host has a record.`);
      }
      rmSync(path.join(dir, 'pending.json'), { force: true });
      throw new Stop(1, `Cloudflare did not attach ${host} to the Worker ${worker}: ${cfWords(put)}. The record is back as it was (kept in ${RUN_DIR}/${kept.name}). Nothing else was changed.`);
    }
    rmSync(path.join(dir, 'pending.json'), { force: true });
    say(`  done     Attached ${host} to the Worker ${worker}. Cloudflare made the record that points it there.`);
  }

  // Step 5: the route commit, local only.
  let committed = null;
  if (needsRoute) {
    try {
      committed = await ensureRouteCommit(ctx, [host], 'launch');
    } catch (e) {
      if (e instanceof Stop) e.lines.push(`${configFile} may be edited and not committed: commit it or restore it by hand before the next run.`);
      throw e;
    }
    say(`  done     Committed ${short(committed.commit)} here: ${host} as a custom-domain route in ${configFile}. It is not pushed.`);
  }

  // Step 6: the first request, through the check script.
  const first = await runCheck(ctx, { commit, only: ['build', 'nel'] });
  if (first.by.build?.state === 'skip') {
    say('', `${host} is attached but did not answer the check yet: ${first.by.build.detail} Run the same command, with the same code, again in a few minutes. Status 4.`);
    return 4;
  }
  if (first.by.build?.state !== 'ok') {
    throw new Stop(1, `${host} is attached, but the check of its build is not ok: ${first.by.build?.detail ?? 'no answer'}`, `It should serve ${short(commit)}. Nothing more was changed: the NEL rule waits until it does.`);
  }
  say('', `  ok       ${host} serves ${short(commit)}.`);

  // Step 7: the NEL rule, only when the headers are still sent.
  let ruleset;
  if (first.by.nel?.state === 'fail' && nelRule) {
    ruleset = await readRuleset(api, zoneAt);
    if (ruleset?.rules?.some((x) => x.description === NEL_RULE.description)) {
      throw new Stop(1, `The domain still sends the NEL headers, and the zone's response header rules already hold "${NEL_RULE.description}": the rule is there and the headers still come. Look at it in Rules → Transform Rules (the checklist's section 3, step 4).`);
    }
    if (!fits(['nel'])) {
      return ask([nelLine.replace(/^If the domain still sends the NEL headers: a/, 'The domain still sends the NEL headers: a')], ['nel'], `${host} is live and serves commit ${short(commit)}.`);
    }
    await addNelRule(api, zoneAt, ruleset);
    say(`  done     Added the rule "${NEL_RULE.description}". It took effect within 20 seconds in the trial; the next run asks the domain again.`);
    say('', 'Waiting for the NEL rule to take effect. Run the same command, with the same code, again in a few minutes. Status 4.');
    return 4;
  }

  // ---- nothing left to do: the whole check decides the status; the report adds Bot Management's AI
  // notes. A time limit in either ends the run with 4 before the report starts.
  const ai = await readAiNow(api, zoneAt);
  const whole = await runCheck(ctx, { commit });
  return launchReport(ctx, { whole, opts, commit, nelRule, ai, replaced, needsRoute, committed });
}

// The end of a launch run with nothing left to do: the whole check, read by LAUNCH_FAIL, the report the
// plan asks for, and the steps back.
async function launchReport(ctx, { whole, opts, commit, nelRule, ai, replaced, committed }) {
  const { say, host, worker, configFile } = ctx;
  const v = launchVerdict(whole, opts.skip);
  say('', `The check of ${host}, from outside:`);
  for (const r of whole.results) say(`  ${(r.state === 'fail' ? 'FAIL' : r.state === 'hand' ? 'by hand' : r.state === 'skip' ? 'not run' : r.state).padEnd(8)} ${r.title.replace(/`/g, '')}: ${r.detail}`);
  if (v.silent.length) say(`No answer, which counts as a failure: ${v.silent.join(', ')}.`);
  if (v.blocked.length) say(`Not judged, which counts as a failure: ${v.blocked.join(', ')}.`);
  for (const r of v.counted) {
    const id = Object.entries({ https: 'https', nel: 'nel-rule', bot: 'bot', email: 'email' }).find(([k]) => k === r.id)?.[1];
    if (id) say(`If ${r.title.replace(/`/g, '')} was left out on purpose, its --skip ${id} belongs on the command.`);
  }
  for (const r of v.passed) say(`Left to you: ${r.title.replace(/`/g, '')} fails, and was left out on purpose (or is yours to decide).`);
  if (ai.why) {
    say('', `Bot Management could not be read: ${ai.why}. The notes on the AI bot policies are not shown; the setup stage, run again, shows them.`);
  } else {
    const notes = aiNotes(ai.now, 'launch');
    if (notes.length) say('', 'The AI bot policies, as Cloudflare reads them now:', ...notes);
  }

  say('', `Live: https://${host}/ serves ${short(commit)}.`);
  if (!nelRule) say('The NEL rule was left out (--skip nel-rule).');
  say(`The route commit is in this folder${committed ? ` (${short(committed.commit)})` : ' already'} and is not pushed. On the owner's word the assistant pushes it (git push origin main), so the next build keeps the domain.`);
  if (replaced) {
    say('', `The record that ${host} had before is kept in ${RUN_DIR}/${replaced.name ?? '(its file)'} and reads:`, ...recordWords(replaced.note));
  }
  say('To undo the launch: remove the domain from the Worker (Workers & Pages → ' + worker + ' → Settings → Domains & Routes)' + (replaced ? ', add the record back (DNS → Records → Add record, with the values above)' : '') + `, and take ${host} out of "routes" in ${configFile} in a new commit.`);
  const hsts = new Date(Date.now() + 3 * 86_400_000).toISOString().slice(0, 10);
  say('Left to do by hand (CLOUDFLARE_CHECK.md, "By hand, always"): Crawler Hints, the Web Analytics switch, the script monitor\'s switch (the checklist\'s section 3, step 5),',
    `and HSTS once the site has worked for a few days, not before ${hsts} (the checklist's section 2).`);
  say('Previews can be put behind a sign-in (Cloudflare Access); the script does not do that.');
  say('Delete the token now: My Profile → API Tokens → ⋯ → Delete.');
  say('', v.code ? 'Not finished: the lines above say what fails. Status 1.' : 'Launched. Status 0.');
  return v.code;
}

// The zone's ruleset for the response header phase, or null when it has none (code 10003, T2-018).
async function readRuleset(api, zoneAt) {
  const r = await api('GET', `${zoneAt}/rulesets/phases/${PHASE}/entrypoint`);
  if (r.status === 404 && r.body?.errors?.some((e) => e.code === 10003)) return null;
  if (!ok(r) || !r.body?.result) throw new Stop(1, `Cloudflare did not show the zone's response header rules: ${refusal(r, ROW.rules)}. Add the NEL rule by hand (the checklist's section 3, step 4).`);
  return r.body.result;
}

// One rule added to the ruleset (T2-024, T2-025: the rules already there keep their ids and versions),
// or, with no ruleset, one created holding it (T2-023), after reading the phase once more just before.
async function addNelRule(api, zoneAt, ruleset) {
  let rs = ruleset;
  if (!rs) {
    rs = await readRuleset(api, zoneAt);
    if (rs?.rules?.some((x) => x.description === NEL_RULE.description)) {
      throw new Stop(1, `A ruleset holding "${NEL_RULE.description}" appeared while this run read the zone, and the domain still sends the NEL headers. Nothing was added. Run the same command again.`);
    }
  }
  const r = rs
    ? await api('POST', `${zoneAt}/rulesets/${rs.id}/rules`, { json: NEL_RULE })
    : await api('PUT', `${zoneAt}/rulesets/phases/${PHASE}/entrypoint`, { json: { rules: [NEL_RULE] } });
  if (!ok(r)) throw new Stop(1, `Cloudflare did not add the NEL rule: ${refusal(r, ROW.rules)}. Add it by hand (the checklist's section 3, step 4).`);
  const kept = rs ? rs.rules.map((x) => x.id) : [];
  const after = r.body?.result?.rules ?? [];
  if (!after.some((x) => x.description === NEL_RULE.description) || kept.some((id) => !after.some((x) => x.id === id))) {
    throw new Stop(1, 'Cloudflare accepted the NEL rule, but the ruleset does not read back with it and every rule that was there. Look at Rules → Transform Rules.');
  }
}

// The `ai` line's fields as Bot Management reads them, for launch day's notes. A refusal or a dropped
// connection comes back as `why`, never a stop; a time limit still rejects with Deadline.
async function readAiNow(api, zoneAt) {
  let r;
  try {
    r = await api('GET', `${zoneAt}/bot_management`);
  } catch (e) {
    if (e instanceof Stop) return { why: "Cloudflare's API did not answer" };
    throw e;
  }
  if (!ok(r)) return { why: refusal(r, ROW.bot) };
  const bot = r.body.result ?? {};
  const now = Object.fromEntries(Object.keys(BOT_LINES.find((b) => b.id === 'ai').fields).map((k) => [k, bot[k]]));
  if ('ai_agents' in bot) now.ai_agents = bot.ai_agents;
  return { now };
}
// ---------------------------------------------------------------- running it

export async function main(argv, io = {}) {
  const say = io.say ?? ((...l) => { for (const x of l) process.stdout.write(`${x}\n`); });
  const sink = say;
  let opts;
  try {
    opts = parseArgs(argv);
  } catch (e) {
    if (!(e instanceof UsageError)) throw e;
    process.stderr.write(`cloudflare-setup: ${e.message}\n\n${USAGE}`);
    return 2;
  }
  if (opts.help) { say(USAGE); return 0; }
  try {
    const stage = opts.stage === 'launch' ? launchStage : setupStage;
    return await stage(opts, { say: sink, cwd: io.cwd ?? process.cwd() });
  } catch (e) {
    if (e instanceof UsageError) {
      process.stderr.write(`cloudflare-setup: ${e.message}\n`);
      return 2;
    }
    if (e instanceof Deadline) {
      sink('', ...(e.call ? [`Cloudflare gave no answer to ${e.call} in time.`] : []), `This run reached its time limit and stopped. What it wrote stands; the next run reads what is there and carries on. Run the same command again. Status 4.`);
      return 4;
    }
    if (e instanceof Stop) {
      sink('', ...e.lines.map((l, i) => (i ? l : `Stopped: ${l}`)), `Status ${e.code}.`);
      return e.code;
    }
    throw e;
  }
}

// Run as a program. Skills are symlinked into place, so compare real paths; and if the runtime was
// told to keep symlinks, the file's own name still says it was run directly.
const isMain = (() => {
  try {
    const argv1 = process.argv[1];
    if (!argv1) return false;
    return import.meta.url === pathToFileURL(realpathSync(argv1)).href
      || path.basename(argv1) === 'cloudflare-setup.mjs';
  } catch {
    return false;
  }
})();
if (isMain) {
  if (Number(process.versions.node.split('.')[0]) < 18) {
    process.stderr.write(`cloudflare-setup needs Node 18 or newer; this is Node ${process.versions.node}.\n`);
    process.exit(2);
  }
  process.exitCode = await main(process.argv.slice(2));
}
