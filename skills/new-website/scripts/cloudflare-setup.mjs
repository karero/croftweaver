#!/usr/bin/env node
// cloudflare-setup.mjs: put a site that lives on GitHub onto Cloudflare Pages, connected to its
// repository, with the settings of the Cloudflare checklist (docs/CLOUDFLARE-CHECKLIST.md), through
// Cloudflare's API and one short-lived token.
//
//   node cloudflare-setup.mjs setup [--project <name>] [--skip <id>]... [--record "<type> <name> <content>"]...
//                                   [--confirm <code>]
//
// Run it in the site's folder. A run with something to change prints its question and a code,
// changes nothing, and ends with 3; the same command with --confirm <code> makes the changes the
// question named. It needs Node 18 or newer and nothing from npm, and it never runs Wrangler. What it
// does, and the exit statuses, are in references/CLOUDFLARE_FIRST_DEPLOY.md next to this folder.
// The `launch` stage, which attaches the domain, is not in this version.
import http from 'node:http';
import https from 'node:https';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { Resolver, promises as dnsPromises } from 'node:dns';
import { existsSync, readFileSync, realpathSync } from 'node:fs';
import { isDeepStrictEqual } from 'node:util';
import { pathToFileURL } from 'node:url';

const API_HOST = 'https://api.cloudflare.com';
const API_PREFIX = '/client/v4';
const RUN_MS = 55_000; // one deadline per run: it leaves time to report before an assistant's 60 seconds
const MAX_TOKEN_MS = 8 * 86_400_000; // "a week at most": the dashboard sets an end DATE, which can end late on day 7
const UA = 'croftweaver-cloudflare-setup/1';
const BUILD = { build_command: 'npm run build', destination_dir: 'dist' };
const STOCK_URL = /^https?:\/\/(?:www\.)?example\.com\/?$/i; // the starter's SITE.url, never filled in

// The permission rows of the checklist's section 6, named when Cloudflare refuses something.
const ROW = {
  zone: 'Zone → Zone → Read',
  settings: 'Zone → Zone Settings → Edit',
  bot: 'Zone → Bot Management → Edit',
  dns: 'Zone → DNS → Edit',
  pages: 'Account → Cloudflare Pages → Edit',
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
    path: 'Your domain → Security → Settings → filter by Bot traffic → Configure AI bot policies',
    visitor: "AI crawlers, training ones included, are no longer blocked or led into AI Labyrinth, and Cloudflare adds no lines to robots.txt" },
];
const BOT_PUT_FIELDS = ['fight_mode', 'enable_js', 'ai_bots_protection', 'ai_search', 'ai_user', 'ai_training',
  'crawler_protection', 'content_bots_protection', 'cf_robots_variant'];
export const SKIP_IDS = [...SETTINGS.map((s) => s.id), ...BOT_LINES.map((b) => b.id)];
const LAUNCH_SKIP_IDS = ['canonical', 'nel-rule'];
// Hosts a verification record points AT. A record whose NAME ends in one has name and target swapped.
const VERIFY_TARGETS = ['verify.bing.com'];

export class UsageError extends Error {}
class Stop extends Error { // the run ends here with `code`; `lines` say why
  constructor(code, ...lines) { super(lines[0]); this.code = code; this.lines = lines; }
}
class Deadline extends Error {}

// ---------------------------------------------------------------- what was asked for

const USAGE = `Usage: node cloudflare-setup.mjs setup [options]

Run it in the site's folder, with the token in CLOUDFLARE_API_TOKEN or in .dev.vars (a file git
ignores). A run with something to change asks first: it prints the list and a code, changes
nothing, and ends with 3. On the owner's yes, run the same command again with --confirm <code>.

  setup                  the project, its connection to GitHub, the checklist's settings, and
                         the records given with --record (setup day)
  --project <name>       the Pages project to use or create (by default the one connected to
                         this repository, or one named like it)
  --skip <id>            leave one line as it is: ${SKIP_IDS.join(', ')}
  --record "<type> <name> <content>"
                         a verification record to write, DNS only: TXT or CNAME, a name relative
                         to the domain (@ for the domain itself) or a full name, then the content
                         (at most five)
  --confirm <code>       the code of the question the owner said yes to
  -h, --help             this text

Exit status: 0 finished, and in effect as far as Cloudflare's API shows; 1 something failed or
was refused (the report says what); 2 the command was wrong; 3 waiting for a yes; 4 waiting for
Cloudflare or for a push: run the same command again in a few minutes.
`;

export function parseArgs(argv) {
  const opts = { stage: null, project: null, skip: [], records: [], confirm: null, help: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const value = () => {
      const v = argv[++i];
      if (v === undefined || (v.startsWith('-') && v !== '-')) throw new UsageError(`${a} needs a value`);
      return v;
    };
    if (a === '-h' || a === '--help') opts.help = true;
    else if (a === '--project') opts.project = value();
    else if (a === '--skip') opts.skip.push(value());
    else if (a === '--record') opts.records.push(value());
    else if (a === '--confirm') opts.confirm = value();
    else if (a.startsWith('-')) throw new UsageError(`unknown option ${a}`);
    else if (opts.stage === null) opts.stage = a;
    else throw new UsageError(`unexpected "${a}": give one stage`);
  }
  if (opts.help) return opts;
  if (opts.stage === 'launch') {
    throw new UsageError('the launch stage is not in this version of the script. Attach the domain by hand, as "Going live" in references/CLOUDFLARE_FIRST_DEPLOY.md says');
  }
  if (opts.stage !== 'setup') throw new UsageError(opts.stage ? `unknown stage "${opts.stage}"` : 'give the stage: setup');
  for (const id of opts.skip) {
    if (LAUNCH_SKIP_IDS.includes(id)) throw new UsageError(`--skip ${id} belongs to the launch stage`);
    if (!SKIP_IDS.includes(id)) throw new UsageError(`--skip takes one of ${SKIP_IDS.join(', ')} (got "${id}")`);
  }
  opts.skip = [...new Set(opts.skip)].sort();
  if (opts.project !== null && !/^[a-z0-9](?:[a-z0-9-]{0,56}[a-z0-9])?$/.test(opts.project)) {
    throw new UsageError(`"${opts.project}" is not a Pages project name: lower-case letters, digits and hyphens, at most 58, no hyphen at either end`);
  }
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

// The name a new project gets: the repository's, lower-cased, every character other than a letter,
// digit or hyphen made a hyphen, cut to 58, hyphens trimmed from both ends.
export function defaultName(repo) {
  return repo.toLowerCase().replace(/[^a-z0-9-]/g, '-').slice(0, 58).replace(/^-+|-+$/g, '');
}

// One call to Cloudflare's API, given only the time left. Never rejects for an HTTP status: the
// status and the parsed body come back. A connection that fails rejects with a Stop.
function makeApi(origin, token, clock) {
  return (method, p, { json, form } = {}) => new Promise((resolve, reject) => {
    const ms = clock.left();
    if (ms <= 0) { reject(new Deadline()); return; }
    const url = new URL(`${API_PREFIX}${p}`, origin);
    const lib = url.protocol === 'https:' ? https : http;
    const headers = { authorization: `Bearer ${token}`, accept: 'application/json', 'user-agent': UA };
    let body = null;
    if (json !== undefined) {
      body = JSON.stringify(json);
      headers['content-type'] = 'application/json';
    } else if (form) {
      // An empty multipart form: the deployment call then builds the head of the production branch.
      body = '------croftweaver--\r\n';
      headers['content-type'] = 'multipart/form-data; boundary=----croftweaver';
    }
    const signal = AbortSignal.timeout(ms);
    const req = lib.request(url, { method, headers, signal, agent: false }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('error', () => {});
      res.on('close', () => {
        if (signal.aborted) { reject(new Deadline()); return; }
        const text = Buffer.concat(chunks).toString('utf8');
        let parsed = null;
        try { parsed = text ? JSON.parse(text) : null; } catch { parsed = null; }
        resolve({ status: res.statusCode, body: parsed });
      });
    });
    req.on('error', (e) => {
      if (signal.aborted) reject(new Deadline());
      else reject(new Stop(1, `Cloudflare's API did not answer (${e.code || e.message}). Is this computer online? Run the same command again.`));
    });
    req.end(body ?? undefined);
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

// The project's deployments, newest first, read a page at a time and only as far as a question needs.
function deploymentReader(api, base) {
  let seen = [];
  let page = 0;
  let done = false;
  const more = async () => {
    page++;
    if (page > 200) throw new Stop(1, 'The project has more than 200 pages of deployments; the script does not decide from part of the list.');
    const r = await api('GET', `${base}/deployments?page=${page}`);
    if (!ok(r)) throw new Stop(1, `Cloudflare did not list the project's deployments: ${refusal(r, ROW.pages)}.`);
    const got = Array.isArray(r.body?.result) ? r.body.result : [];
    seen = seen.concat(got);
    const pages = r.body?.result_info?.total_pages;
    if (!got.length || !pages || page >= pages) done = true;
  };
  return {
    async find(pred) {
      for (let i = 0; ;) {
        for (; i < seen.length; i++) if (pred(seen[i])) return seen[i];
        if (done) return null;
        await more();
      }
    },
    reset() { seen = []; page = 0; done = false; },
  };
}

// ---------------------------------------------------------------- reading a deployment

const stageOf = (d, name) => d?.stages?.find((s) => s.name === name)?.status;
const commitOf = (d) => d?.deployment_trigger?.metadata?.commit_hash ?? '';
const short = (sha) => String(sha).slice(0, 7);
// Cloudflare built it: an upload has the stages clone_repo and build idle (captures 021 to 026).
export const cloudflareBuilt = (d) => stageOf(d, 'clone_repo') === 'success' && stageOf(d, 'build') === 'success';
export const succeeded = (d) => d?.latest_stage?.name === 'deploy' && d.latest_stage.status === 'success';
// Running: queued or under way, or between two stages (a stage before deploy that has succeeded), or
// with no stage given yet.
export const running = (d) => Boolean(d) && !d.is_skipped && (!d.latest_stage || ['idle', 'active'].includes(d.latest_stage.status)
  || (d.latest_stage.status === 'success' && d.latest_stage.name !== 'deploy'));
// Failed, or ended in a way the trials never saw: whatever is neither skipped, running nor succeeded
// (no trial had a failed build; Cloudflare's reference names its status "failure"). Read so, a word
// the script does not know stops it instead of starting the same build again.
export const failed = (d) => Boolean(d) && !d.is_skipped && !running(d) && !succeeded(d);
// A good production build of a commit: production, that commit, succeeded, built by Cloudflare, and
// made while the production branch was the one it is now (a deployment records it, capture 055).
export const goodProductionBuild = (d, sha, prod) => d?.environment === 'production' && commitOf(d) === sha
  && succeeded(d) && cloudflareBuilt(d) && d.production_branch === prod;
// The proof of the connection: a deployment Cloudflare started from a push and did not skip.
export const pushProof = (d) => d?.deployment_trigger?.type === 'github:push' && !d.is_skipped;

function describeDeployment(d) {
  const where = d.environment === 'production' ? 'production' : `a preview of ${d.deployment_trigger?.metadata?.branch ?? 'a branch'}`;
  const stage = d.latest_stage ? `${d.latest_stage.name}: ${d.latest_stage.status}` : 'no stage';
  return `${where}, commit ${short(commitOf(d))} (${stage})`;
}

// ---------------------------------------------------------------- the code of a question

// Made from the end state the question names and from the changes it listed (`listed`, one key per
// line, the build with its commit). A later run accepts the code for any part of that list: what was
// done since drops out, so the script's own writes keep it (R8), and anything new, or a build of
// another commit, needs a new yes (R1). What is there now (an old value) is shown but not in it.
export function setupCode(input, listed = []) {
  const settings = {};
  for (const s of SETTINGS) if (!input.skip.includes(s.id)) settings[s.id] = s.value;
  for (const b of BOT_LINES) if (!input.skip.includes(b.id)) settings[b.id] = b.fields;
  const end = {
    stage: 'setup',
    account: input.account,
    project: input.project,
    repository: input.repository.toLowerCase(),
    production_branch: input.productionBranch,
    ...BUILD,
    fail_open: true,
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

async function setupStage(opts, io) {
  const { say, cwd } = io;
  const clock = makeClock();
  const apiOrigin = loopback('CLOUDFLARE_SETUP_API', process.env.CLOUDFLARE_SETUP_API, { origin: true });
  const resolverAt = loopback('CLOUDFLARE_SETUP_RESOLVER', process.env.CLOUDFLARE_SETUP_RESOLVER, { origin: false });
  if (apiOrigin) say(`Test mode: Cloudflare's API is replaced by ${apiOrigin}.`);
  if (resolverAt) say(`Test mode: the zone's nameservers are replaced by ${resolverAt}.`);

  // 1. The repository: GitHub's owner and name, its branches, its config at the head of main.
  // The token is known from the start when it comes from the environment; from .dev.vars, once read.
  let env = childEnv((process.env.CLOUDFLARE_API_TOKEN ?? '').trim() || null);
  const git = (...args) => runProgram('git', args, { cwd, env, clock });
  const top = await git('rev-parse', '--show-toplevel');
  if (top.code !== 0) throw new Stop(1, 'This folder is not a git repository. Run the script in the site\'s folder.');
  const root = top.stdout.trim();
  const remote = await git('config', '--get', 'remote.origin.url');
  const gh = remote.code === 0 ? githubRepo(remote.stdout) : null;
  if (!gh) throw new Stop(1, 'The remote "origin" is not a repository on GitHub, so Cloudflare cannot build from it. Push the site to GitHub first (new-website §4).');
  const repository = `${gh.owner}/${gh.repo}`;

  const token = await readToken(root, git);
  env = childEnv(token);
  const api = makeApi(apiOrigin ?? API_HOST, token, clock);

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
  const config = await git('show', `${mainSha}:src/config.ts`);
  if (config.code !== 0) throw new Stop(1, `src/config.ts is missing at the head of main (${short(mainSha)}): is this a site made with the kit?`);
  const prodBranch = /^export const PROD_BRANCH = ['"]([^'"]*)['"];?/m.exec(config.stdout)?.[1];
  const siteBlock = config.stdout.slice(config.stdout.search(/^export const SITE = \{/m));
  const siteUrl = /^\s*url:\s*['"]([^'"]+)['"]/m.exec(siteBlock)?.[1];
  if (!prodBranch) throw new Stop(1, 'src/config.ts at the head of main has no line "export const PROD_BRANCH = \'…\';".');
  if (!siteUrl) throw new Stop(1, 'src/config.ts at the head of main has no SITE.url.');
  if (STOCK_URL.test(siteUrl)) throw new Stop(1, 'SITE.url in src/config.ts is still the starter\'s https://example.com. Set your own domain there, on main, first.');
  let host;
  try { host = new URL(siteUrl).hostname.toLowerCase(); } catch { throw new Stop(1, `SITE.url in src/config.ts is not an address: ${siteUrl}`); }

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
  const zones = await allPages(api, '/zones', 50);
  if (!zones.items) throw new Stop(1, `Cloudflare refused to list the token's zones (${cfWords(zones.r)}). Make a new token with the row ${ROW.zone} (the checklist's section 6).`);
  if (zones.items.length > 1) {
    throw new Stop(1, `This token reaches ${zones.items.length} zones. Make one limited to the site's own zone (Zone Resources: your one domain). A token narrowed just now may need a few minutes before Cloudflare shows the change: then run this again.`);
  }
  const zone = zones.items[0];
  if (!zone || !(host === zone.name || host.endsWith(`.${zone.name}`))) {
    throw new Stop(1, `Cloudflare has no zone for ${host} that this token reaches${zone ? ` (it reaches ${zone.name})` : ''}. The domain must be on Cloudflare first ("Going live" in CLOUDFLARE_FIRST_DEPLOY.md), and the token limited to it.`);
  }
  if (zone.status !== 'active') throw new Stop(1, `The zone ${zone.name} is ${zone.status} on Cloudflare, not active: its nameservers must point to Cloudflare first.`);
  const account = { id: zone.account?.id, name: zone.account?.name ?? zone.account?.id };
  if (!account.id) throw new Stop(1, 'Cloudflare did not say which account the zone belongs to.');

  // 3. The project: by --project, or the one connected to this repository, or one named like it.
  const projectsAt = `/accounts/${account.id}/pages/projects`;
  const projects = await allPages(api, projectsAt);
  if (!projects.items) throw new Stop(1, `Cloudflare refused to list the account's Pages projects: ${refusal(projects.r, ROW.pages)}.`);
  const connected = (p) => p.source?.type === 'github'
    && String(p.source.config?.owner).toLowerCase() === gh.owner.toLowerCase()
    && String(p.source.config?.repo_name).toLowerCase() === gh.repo.toLowerCase();
  const elsewhere = (p) => (p.source?.config ? `${p.source.config.owner}/${p.source.config.repo_name}` : 'another source');
  const directUpload = (name) => new Stop(1,
    `A Pages project named ${name} exists, but it is not connected to Git: a Direct Upload project. Cloudflare cannot connect one to GitHub.`,
    'website-team-setup §6, item 9, has the way round: a connected project under a new name (give it with --project), then the domain moved over.');
  let project = null;
  let name;
  if (opts.project) {
    name = opts.project;
    project = projects.items.find((p) => p.name === name) ?? null;
    if (project && !project.source) throw directUpload(name);
    if (project && !connected(project)) throw new Stop(1, `The project ${name} is connected to ${elsewhere(project)}, not to ${repository}. Give another --project, or leave it out.`);
  } else {
    const mine = projects.items.filter(connected);
    if (mine.length > 1) throw new Stop(1, `${mine.length} projects are connected to ${repository}: ${mine.map((p) => p.name).join(', ')}. Say which with --project <name>.`);
    if (mine.length === 1) {
      project = mine[0];
      name = project.name;
    } else {
      name = defaultName(gh.repo);
      if (!name) throw new Stop(1, `No project name can be made from the repository's name. Give one with --project <name>.`);
      project = projects.items.find((p) => p.name === name) ?? null;
      if (project && !project.source) throw directUpload(name);
      if (project && !connected(project)) throw new Stop(1, `A project named ${name} exists and is connected to ${elsewhere(project)}. Give another name with --project <name>.`);
    }
  }
  const projectAt = `${projectsAt}/${name}`;
  // The list gave the name; what is decided (its domains, variables, Fail open) is read from the
  // project itself, in the shape the trial captured (T1-054).
  if (project) {
    const one = await api('GET', projectAt);
    if (!ok(one) || !one.body?.result) throw new Stop(1, `Cloudflare did not return the project ${name}: ${refusal(one, ROW.pages)}.`);
    project = one.body.result;
    if (!connected(project)) throw new Stop(1, `The project ${name}, read by its name, is not connected to ${repository}. Nothing was changed.`);
    if (!Array.isArray(project.domains) || !project.deployment_configs) {
      throw new Stop(1, `Cloudflare returned the project ${name} without its domains or settings, so the script cannot tell whether it is live. Nothing was changed.`);
    }
  }
  const custom = project ? project.domains.filter((d) => d !== project.subdomain) : [];

  // What changes on the project: created whole, or a PATCH that holds only what changes.
  let create = null;
  const patch = {};
  const projectSay = [];
  const projectKeys = [];
  if (!project) {
    create = {
      name,
      production_branch: prodBranch,
      build_config: { ...BUILD, root_dir: '' },
      source: {
        type: 'github',
        config: {
          owner: gh.owner, repo_name: gh.repo, production_branch: prodBranch, pr_comments_enabled: true,
          deployments_enabled: true, production_deployments_enabled: true, preview_deployment_setting: 'all',
        },
      },
      deployment_configs: { production: { fail_open: true }, preview: { fail_open: true } },
    };
    projectKeys.push('project:create');
    projectSay.push(`Create the Pages project ${name}, connected to ${repository}: production branch ${prodBranch}, build command ${BUILD.build_command}, output folder ${BUILD.destination_dir}, Fail open on for production and previews. Cloudflare gives it its pages.dev address.`);
  } else {
    if (project.production_branch !== prodBranch) {
      if (custom.length) {
        throw new Stop(1,
          `The project ${name} publishes ${project.production_branch} to ${custom.join(', ')}, and this site's production branch is ${prodBranch}. The site is live, and this script does not repair a live site.`,
          'The checklist\'s section 1 says how to change the production branch by hand. Nothing was changed.');
      }
      patch.production_branch = prodBranch;
      projectKeys.push(`project:production_branch=${prodBranch}`);
      projectSay.push(model === 'two-stage' && project.production_branch === 'main'
        ? `Production branch: main → ${prodBranch}. Today your live address would publish main, the preview; I will set the production branch to ${prodBranch}.`
        : `Production branch: ${project.production_branch} → ${prodBranch}.`);
    }
    const bc = {};
    for (const [k, v] of Object.entries(BUILD)) if (project.build_config?.[k] !== v) bc[k] = v;
    if (Object.keys(bc).length) {
      patch.build_config = bc;
      projectKeys.push(...Object.keys(bc).map((k) => `project:${k}`));
      projectSay.push(`Build settings: ${Object.entries(bc).map(([k, v]) => `${k === 'build_command' ? 'build command' : 'output folder'} ${project.build_config?.[k] || '(none)'} → ${v}`).join(', ')}.`);
    }
    const fo = project.deployment_configs ?? {};
    if (fo.production?.fail_open !== true || fo.preview?.fail_open !== true) {
      patch.deployment_configs = { production: { fail_open: true }, preview: { fail_open: true } };
      projectKeys.push('project:fail_open');
      projectSay.push(`Fail open: ${fo.production?.fail_open === true ? 'on' : 'off'} for production, ${fo.preview?.fail_open === true ? 'on' : 'off'} for previews → on for both. Its variables and secrets are not sent and stay as they are.`);
    }
  }

  // 4. The first build: only for a project with no custom domain and no good production build of
  // the head of the production branch.
  const deps = deploymentReader(api, projectAt);
  let build = { kind: 'none' };
  if (custom.length) build = { kind: 'live' };
  else if (!project) build = { kind: 'needed' };
  else {
    const busy = await deps.find((d) => d.environment === 'production' && running(d));
    const newest = busy ? null : await deps.find((d) => d.environment === 'production' && commitOf(d) === prodSha);
    if (busy) build = { kind: 'running', d: busy };
    else if (newest && goodProductionBuild(newest, prodSha, prodBranch)) build = { kind: 'good', d: newest };
    else if (newest && failed(newest)) build = { kind: 'failed', d: newest };
    else build = { kind: 'needed' };
  }

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
    if (opts.skip.includes(b.id)) { line.state = 'skipped'; continue; }
    if (!bot) { line.state = 'unread'; line.why = refusal(botRead, ROW.bot); continue; }
    line.state = isDeepStrictEqual(line.now, b.fields) ? 'as-is' : 'change';
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
      else line.state = 'change';
    }
    return line;
  });

  // The question, and its code: one key per change it lists.
  const codeInput = {
    account: account.id, project: name, repository, productionBranch: prodBranch, zone: zone.id,
    skip: opts.skip, hosts, records: recs.map((l) => l.rec),
  };
  const lineKey = (l) => (l.kind === 'record' ? `record:${l.rec.type} ${l.rec.fullName} ${l.rec.content}` : `setting:${l.id}`);
  const left = [...projectKeys, ...(build.kind === 'needed' ? [`build:${prodSha}`] : []),
    ...lines.filter((l) => l.state === 'change').map(lineKey)];
  const possible = ['project:create', `project:production_branch=${prodBranch}`, ...Object.keys(BUILD).map((k) => `project:${k}`), 'project:fail_open', `build:${prodSha}`,
    ...lines.filter((l) => l.kind === 'record' || !opts.skip.includes(l.id)).map(lineKey)];
  const code = setupCode(codeInput, left);
  const changes = left.length;
  const buildsNoPreviews = (p) => p.source?.config?.preview_deployment_setting !== 'all';
  const previewsOff = Boolean(project) && buildsNoPreviews(project);

  say(`Cloudflare setup for ${host} (zone ${zone.name}, account ${account.name})`);
  say(`Repository ${repository}, ${model}: ${model === 'two-stage' ? 'production is the live branch, main the preview' : 'main is the live branch'}. Project ${name}${project ? ` (exists${custom.length ? `, serves ${custom.join(', ')}` : ''})` : ' (to be created)'}.`);

  if (changes && !(opts.confirm && codeFits(opts.confirm, codeInput, left, possible))) {
    if (opts.confirm) say('', `The code ${opts.confirm} does not fit this question: it lists something the question you said yes to did not (a change, or a build of another commit), or something that question covered has changed. Nothing was changed. Here is the question as it stands now.`);
    say('', 'Nothing has been changed yet. If you say yes, I will:');
    let n = 0;
    const item = (text, ...more) => { n++; say(`  ${String(n).padStart(2)}. ${text}`); for (const m of more) say(`      ${m}`); };
    for (const t of projectSay) item(t);
    if (build.kind === 'needed') item(`Start one build of ${prodBranch} (commit ${short(prodSha)}), so the project has a live build at its pages.dev address. Your domain is not attached and gets nothing.`);
    for (const l of lines.filter((x) => x.state === 'change')) {
      if (l.kind === 'record') {
        item(`Write the record ${l.rec.type} ${l.rec.fullName} → ${l.rec.content}, DNS only.`,
          ...(l.beside?.length ? [`It goes beside the TXT records already there, which stay: ${l.beside.join(' · ')}`] : []));
      } else {
        const now = l.kind === 'bot' ? Object.entries(l.def.fields).filter(([k, v]) => !isDeepStrictEqual(l.now[k], v)).map(([k, v]) => `${k} ${show(l.now[k])} → ${show(v)}`).join(', ') : `${show(l.now)} → ${show(l.def.value)}`;
        item(`${l.title} (${now}).`, hostsSay, `For a visitor there: ${l.def.visitor}.`);
      }
    }
    reportQuiet(say, lines, opts);
    if (build.kind === 'failed') say('', `Not on the list: the newest production build of ${short(prodSha)} failed (${describeDeployment(build.d)}). The yes starts no new build of it; look at its log first (Workers & Pages → ${name} → Deployments).`);
    say('', `Afterwards ${previewsOff ? `the production branch gets one push (${model === 'two-stage' ? 'npm run ship, on your word' : 'a merge to main'})` : 'the assistant pushes one commit to a pull request'}, so that a build Cloudflare starts from GitHub shows the connection works.`);
    say('Before you say yes: the token\'s Account Resources should name your one account.');
    say('', `To go ahead, run the same command again with: --confirm ${code}`);
    return 3;
  }

  // ---- with the yes (or with nothing to change): carry it out, one call per write.
  const results = { failed: [], waiting: [] };
  if (create) {
    const r = await api('POST', projectsAt, { json: create });
    if (!ok(r)) throw new Stop(1, `Cloudflare did not create the project: ${refusal(r, ROW.pages)}.`, 'If it says the name is taken (pages.dev names are global), run again with --project <another-name>. If it cannot reach the repository, give Cloudflare\'s GitHub app access to it (GitHub → Settings → Applications → Cloudflare Workers and Pages → Configure).');
    if (!wholeProject(r.body?.result)) throw new Stop(1, `Cloudflare says it created the project ${name}, but did not return it whole (its address, source and settings). Look at it in the dashboard (Workers & Pages), then run this again.`);
    project = r.body.result;
    say('', `  done     Created the project ${name}, connected to ${repository}. Its address: https://${project.subdomain}/`);
  } else if (Object.keys(patch).length) {
    const before = varNames(project);
    const r = await api('PATCH', projectAt, { json: patch });
    if (!ok(r)) throw new Stop(1, `Cloudflare refused the change to the project: ${refusal(r, ROW.pages)}. Nothing else was changed.`);
    if (!wholeProject(r.body?.result)) throw new Stop(1, 'Cloudflare accepted the change to the project but did not return it whole, so its variables cannot be listed after it. Look at the project in the dashboard (Workers & Pages → the project → Settings → Variables and Secrets).');
    const after = varNames(r.body.result);
    const lost = before.filter((v) => !after.includes(v));
    say('', `  done     ${projectSay.join(' ')}`);
    say(`           Variables and secrets before: ${before.join(', ') || 'none'}; after: ${after.join(', ') || 'none'}.`);
    if (lost.length) throw new Stop(1, `After the change, Cloudflare no longer lists ${lost.join(', ')}. The script cannot put a secret back (its value reads empty): set ${lost.length === 1 ? 'it' : 'them'} again by hand, under the project's Settings → Variables and Secrets.`);
    project = r.body.result;
    const fo = project.deployment_configs ?? {};
    if (project.production_branch !== prodBranch || fo.production?.fail_open !== true || fo.preview?.fail_open !== true
      || Object.entries(BUILD).some(([k, v]) => project.build_config?.[k] !== v)) {
      throw new Stop(1, 'Cloudflare accepted the change to the project, but the project it returned does not read as wanted. Look at it in the dashboard: Workers & Pages → the project → Settings.');
    }
    if (patch.deployment_configs) say('           Fail open now reads on. Whether that reaches the build that is live, or only later ones, is not known: a deployment does not record it.');
  } else if (project) {
    say('', `  as is    The project ${name}: production branch ${prodBranch}, ${BUILD.build_command}, ${BUILD.destination_dir}, Fail open on.`);
  }

  // The first build: never while one of the production branch is queued or building.
  if (build.kind === 'needed') {
    deps.reset();
    const busy = await deps.find((d) => d.environment === 'production' && running(d));
    if (busy) {
      build = { kind: 'running', d: busy };
    } else {
      const r = await api('POST', `${projectAt}/deployments`, { form: true });
      if (!ok(r)) throw new Stop(1, `Cloudflare did not start the build: ${refusal(r, ROW.pages)}.`);
      const started = r.body.result;
      const now = await api('GET', `${projectAt}/deployments/${started.id}`);
      build = { kind: 'running', d: ok(now) ? now.body.result : started, started: true };
    }
  }
  if (build.kind === 'running') {
    say(`  waiting  ${build.started ? 'Started a build' : 'A build is under way'}: ${describeDeployment(build.d)}.`);
    results.waiting.push('the build');
  } else if (build.kind === 'failed') {
    say(`  FAILED   The newest production build of ${short(prodSha)} failed: ${describeDeployment(build.d)}. No new build was started. Look at its log: Workers & Pages → ${name} → Deployments.`);
    results.failed.push('the build');
  } else if (build.kind === 'good') {
    say(`  as is    A build of ${prodBranch} (${short(prodSha)}) by Cloudflare is live at https://${project.subdomain}/`);
  } else if (build.kind === 'live') {
    say(`  as is    The project serves ${custom.join(', ')}: this stage starts no build on it.`);
  }

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
    for (const l of botLines) Object.assign(body, l.def.fields);
    const r = await api('PUT', `${zoneAt}/bot_management`, { json: body });
    if (!ok(r)) {
      for (const l of botLines) { l.state = 'hand'; l.why = refusal(r, ROW.bot); }
    } else {
      const back = await api('GET', `${zoneAt}/bot_management`);
      const want = { ...bot, ...body };
      const off = ok(back) ? Object.keys(want).filter((k) => !isDeepStrictEqual(back.body.result?.[k], want[k])) : [];
      for (const l of botLines) {
        if (!ok(back)) { l.state = 'hand'; l.why = `Cloudflare accepted the change, but it could not be read back: ${refusal(back, ROW.bot)}`; } else if (off.length) { l.state = 'hand'; l.why = `Cloudflare accepted the change, but ${off.map((k) => `${k} reads ${show(back.body.result?.[k])}, not ${show(want[k])}`).join('; ')}`; } else l.state = 'done';
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

  // 7. The proof of the connection.
  deps.reset();
  const proof = await deps.find(pushProof);
  const skipped = proof ? null : await deps.find((d) => d.deployment_trigger?.type === 'github:push' && d.is_skipped);
  const previewsOffNow = buildsNoPreviews(project);

  // The report.
  for (const l of lines) reportLine(say, l, hostsSay);
  reportQuiet(say, lines, opts, { done: true });
  for (const l of lines) if (['hand', 'unread', 'clash'].includes(l.state)) results.failed.push(l.title);

  if (proof) {
    say('', failed(proof)
      ? `Connected to GitHub: Cloudflare started a build of this commit (${short(commitOf(proof))}) from a push, and it failed: ${describeDeployment(proof)}. The connection works; look at that build's log.`
      : `Connected to GitHub: Cloudflare started a build from a push: ${describeDeployment(proof)}.`);
  } else {
    results.waiting.push('a push');
    say('', 'Not shown yet: that GitHub and Cloudflare are connected. That takes a build Cloudflare starts itself, from a push.');
    if (skipped) say(`Cloudflare saw a push (${skipped.deployment_trigger?.metadata?.branch ?? 'a branch'}) but skipped it, since this project builds no previews: that is not proof.`);
    if (previewsOffNow) {
      say(`This project does not build previews (its setting is ${project.source?.config?.preview_deployment_setting ?? 'not set'}), so a pull request may not show it. The push that does is to the production branch: ${model === 'two-stage'
        ? 'on this two-stage site that is npm run ship, on your word, once main has a commit production lacks (a merged pull request). Ship\'s own last check then reports an old build, since no domain is attached yet; that is expected'
        : 'on this single-stage site, a merge to main'}.`);
    } else {
      say('Next: the assistant pushes one commit to a pull request (an empty commit will do), then runs this again.');
    }
    say('If no build comes within a few minutes, look at Workers & Pages → the project → Deployments:',
      '  - a build of your commit, queued: Cloudflare saw the push and has not started yet; wait;',
      '  - nothing for your commit: the push did not reach Cloudflare. Either the connection was never made or is broken (the project page then shows a banner about the Git connection; give Cloudflare\'s GitHub app access to the repository again), or builds are paused in the project\'s build settings.');
  }

  say('');
  if (results.failed.length) {
    say(`Not finished: ${results.failed.join(', ')} ${results.failed.length === 1 ? 'needs' : 'need'} you (above). Status 1.`);
    return 1;
  }
  if (results.waiting.length) {
    say(`Waiting for ${results.waiting.join(' and ')}. Run the same command again in a few minutes. Status 4.`);
    return 4;
  }
  say(`Setup is done, as far as Cloudflare's API shows: the settings were read back through the API only. Requests to the domain come on launch day, which checks them from outside and adds the NEL header rule if the headers are still sent. The launch stage is not in this version: attach the domain by hand ("Going live" in CLOUDFLARE_FIRST_DEPLOY.md). The live build is at https://${project.subdomain}/`);
  return 0;
}

// What the script reads from a project answer: its address, its source and its settings (T1-027,
// T1-054 and the PATCH answers T1-048, T1-049, T1-051 to T1-053 and T1-061 all carry them).
// Checked field by field, since an empty object would pass a check for the object alone.
const wholeProject = (p) => typeof p?.subdomain === 'string' && p.subdomain.length > 0
  && typeof p.source?.config?.owner === 'string' && typeof p.source.config.repo_name === 'string'
  && typeof p.source.config.preview_deployment_setting === 'string'
  && typeof p.production_branch === 'string'
  && typeof p.deployment_configs?.production === 'object' && p.deployment_configs.production !== null
  && typeof p.deployment_configs.preview === 'object' && p.deployment_configs.preview !== null
  && typeof p.build_config === 'object' && p.build_config !== null;

function varNames(p) {
  const dc = p?.deployment_configs ?? {};
  return [...new Set([
    ...Object.keys(dc.production?.env_vars ?? {}).map((k) => `${k} (production)`),
    ...Object.keys(dc.preview?.env_vars ?? {}).map((k) => `${k} (previews)`),
  ])].sort();
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

function reportLine(say, l, hostsSay) {
  if (l.kind === 'record') {
    const served = l.served === true ? 'the nameservers show it' : 'written; the nameservers do not show it yet';
    if (l.state === 'done') say(`  done     ${l.title} → ${l.rec.content}, DNS only. Read back through the API; ${served}.`);
    else if (l.state === 'as-is') say(`  as is    ${l.title} → ${l.rec.content} was there already${l.served === true ? '; the nameservers show it' : '; the nameservers do not show it yet'}.`);
    else if (l.state === 'hand' || l.state === 'clash' || l.state === 'unread') say(`  by hand  ${l.title} → ${l.rec.content}: ${l.why}.`);
    return;
  }
  const now = l.kind === 'bot' ? null : show(l.now);
  if (l.state === 'done') say(`  done     ${l.title}${now ? ` (was ${now})` : ''}. Read back through the API only. ${hostsSay}`);
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
    return await setupStage(opts, { say: sink, cwd: io.cwd ?? process.cwd() });
  } catch (e) {
    if (e instanceof UsageError) {
      process.stderr.write(`cloudflare-setup: ${e.message}\n`);
      return 2;
    }
    if (e instanceof Deadline) {
      sink('', 'This run reached its time limit (55 seconds) and stopped. What it wrote stands; the next run reads what is there and carries on. Run the same command again. Status 4.');
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
