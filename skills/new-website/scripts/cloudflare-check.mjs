#!/usr/bin/env node
// cloudflare-check.mjs: look at a live site from outside and say, item by item, how the
// Cloudflare checklist (docs/CLOUDFLARE-CHECKLIST.md) comes out.
//
//   node cloudflare-check.mjs example.com [--project my-pages-project] [--hsts-on]
//                                          [--build <sha>] [--json] [--timeout <seconds>]
//                                          [--only <id>,<id>] [--nameserver <address>,<address>]
//
// Read-only. It sends GET requests and nothing else: no token, no account, no change. It
// needs Node 18 or newer and nothing from npm. What it prints, and what it cannot see, is
// in references/CLOUDFLARE_CHECK.md next to this folder.
import http from 'node:http';
import https from 'node:https';
import path from 'node:path';
import { isIP } from 'node:net';
import { Resolver } from 'node:dns';
import { realpathSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const UA = 'Mozilla/5.0 (compatible; croftweaver-cloudflare-check/1)';
const MONTH = 2629800; // seconds in an average month; the dashboard offers whole months
// The least a month can be: February in a common year. This is the check's own acceptance policy: a
// max-age under it is shorter than the one month the checklist starts with whatever Cloudflare counts a
// month as. The cost is that 28 or 29 days passes as ok, though Cloudflare's month may be longer. Compared
// with MONTH, an average month, a live site's header (2592000 seconds, 30 days, on 14 October 2026) was
// called shorter than one month.
const SHORTEST_MONTH_DAYS = 28;
const SHORTEST_MONTH = SHORTEST_MONTH_DAYS * 86400;
const MAX_BODY = 5_000_000; // bytes of a page read before judging what we have
const MAX_HOPS = 3; // redirects followed on the home page, to the same address only
const CF_COOKIE = /^(__cf_bm|cf_clearance|__cflb|_cfuvid)$/; // the names Cloudflare's own cookies carry
// http:// is for a page on this machine or a test name, never for a live domain.
const LOCAL_HOST = /^(?:localhost|127(?:\.\d{1,3}){3}|\[::1\]|[^.]+\.localhost|.+\.test)$/i;

// Crawler names the AI-crawler item sends. Cloudflare may tell the real crawlers from a
// request that only carries their name, so a 200 here is a hint and not a proof.
const CRAWLERS = [
  ['GPTBot', 'Mozilla/5.0 (compatible; GPTBot/1.1; +https://openai.com/gptbot)'],
  ['OAI-SearchBot', 'Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)'],
  ['ClaudeBot', 'Mozilla/5.0 (compatible; ClaudeBot/1.0)'],
  ['PerplexityBot', 'Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)'],
  ['CCBot', 'CCBot/2.0 (https://commoncrawl.org/faq/)'],
  ['Amazonbot', 'Mozilla/5.0 (compatible; Amazonbot/0.1; +https://developer.amazon.com/support/amazonbot)'],
];

export class UsageError extends Error {}

// The items, in the checklist's order. `title` is the checklist's own bold text, without its
// final full stop or colon: a test keeps the two in step. An item with a `path` is one no
// request from outside can see; the report then says where to look.
export const SECTIONS = {
  1: 'Set up the site',
  2: 'Safe connections',
  3: 'Keep the privacy page true',
  4: 'Be found, by search engines and AI assistants',
  5: 'Check your work',
};
export const ITEMS = [
  { id: 'pages', section: 1, title: 'Create a Pages project, not a Worker' },
  { id: 'build-settings', section: 1, title: 'Build settings',
    path: 'your project → Settings → Builds & deployments',
    lookFor: 'build command npm run build, output directory dist, framework preset Astro or none; on a two-stage site the Production branch is production' },
  { id: 'domain', section: 1, title: 'Attach your domain to the project' },
  { id: 'fail-open', section: 1, title: 'Set Fail open',
    path: 'Workers & Pages → your project → Settings → Runtime → Fail open / closed',
    lookFor: 'it should say Fail open' },
  { id: 'canonical', section: 1, title: 'Send the `<project>.pages.dev` address to your live domain (301)' },
  { id: 'https', section: 2, title: 'Always Use HTTPS: On' },
  { id: 'tls', section: 2, title: 'Minimum TLS Version: TLS 1.2',
    path: 'Your domain → SSL/TLS → Edge Certificates → Minimum TLS Version',
    lookFor: 'then run the domain through ssllabs.com/ssltest: TLS 1.0 and 1.1 should say No' },
  { id: 'hsts', section: 2, title: 'HSTS: On, and last' },
  { id: 'nel', section: 3, title: 'Network Error Logging (NEL): Off' },
  { id: 'bot', section: 3, title: 'Bot Fight Mode: Off' },
  { id: 'analytics', section: 3, title: 'Cloudflare Web Analytics: Off' },
  { id: 'email', section: 3, title: 'Email Address Obfuscation: Off' },
  { id: 'hints', section: 4, title: 'Crawler Hints: On',
    path: 'Your domain → Caching → Configuration → Crawler Hints',
    lookFor: 'there is no outside check for this one' },
  { id: 'ai', section: 4, title: 'AI crawlers: allow',
    path: 'Your domain → Security → Settings → filter by Bot traffic → Configure AI bot policies',
    lookFor: 'Search, Agent and Training each set to Allow (do not block); AI Labyrinth Off; Bot Preference Sync Off unless you block Training; the content-bot block Off, which may show only through the API' },
  { id: 'robots', section: 5, title: 'Your own robots.txt' },
  { id: 'build', section: 5, title: 'The build that is live' },
  { id: 'scripts', section: 5, title: 'No scripts you didn\'t add' },
];

// ---------------------------------------------------------------- what was asked for

const USAGE = `Usage: node cloudflare-check.mjs <domain> [options]

  <domain>            your live domain, for example example.com (no https://, no path)
  --project <addr>    your Pages project's own address (my-project.pages.dev, as Cloudflare
                      shows it: not always the name), to check that it forwards to the domain
  --hsts-on           you have switched HSTS on: a missing header is then a failure
  --build <sha>       the commit you expect the live domain to serve (from /build.txt)
  --json              print the results as JSON
  --timeout <s>       seconds to wait for each answer, 1 to 120 (default 15)
  --only <id>,<id>    judge only these items (the ids under "For an assistant" in
                      CLOUDFLARE_CHECK.md), and send only the requests they need
  --nameserver <ip>   look the domain up at this nameserver (an IP address, with :port if
                      not 53; several separated by commas), not at this computer's own
  -h, --help          this text

Exit status: 0 nothing failed and everything was asked and judged; 1 something failed, did
not answer or could not be judged (the report says which); 2 the command was wrong.
`;

export function parseArgs(argv) {
  const opts = { json: false, hstsOn: false, timeoutMs: 15000, project: null, build: null, only: null, nameservers: null, help: false };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const value = () => {
      const v = argv[++i];
      if (v === undefined || v.startsWith('-')) throw new UsageError(`${a} needs a value`);
      return v;
    };
    if (a === '--json') opts.json = true;
    else if (a === '--hsts-on') opts.hstsOn = true;
    else if (a === '--project') opts.project = value();
    else if (a === '--build') opts.build = value();
    else if (a === '--only') opts.only = parseOnly(value());
    else if (a === '--nameserver') opts.nameservers = parseNameservers(value());
    else if (a === '--timeout') {
      const n = Number(value());
      if (!(n >= 1 && n <= 120)) throw new UsageError('--timeout takes a number of seconds from 1 to 120');
      opts.timeoutMs = Math.round(n * 1000);
    } else if (a === '-h' || a === '--help') opts.help = true;
    else if (a.startsWith('-')) throw new UsageError(`unknown option ${a}`);
    else rest.push(a);
  }
  if (opts.help) return { opts, domain: null };
  if (opts.build !== null && !/^[0-9a-f]{7,40}$/i.test(opts.build)) {
    throw new UsageError('--build takes a commit id: 7 to 40 hexadecimal characters');
  }
  if (rest.length === 0) throw new UsageError('give your domain, for example: example.com');
  if (rest.length > 1) throw new UsageError(`give one domain only (got ${rest.length})`);
  return { opts, domain: rest[0] };
}

// --only: ids of ITEMS, separated by commas; one given twice counts once.
export function parseOnly(arg) {
  const ids = String(arg).split(',').map((x) => x.trim()).filter(Boolean);
  const known = ITEMS.map((i) => i.id);
  const bad = ids.filter((id) => !known.includes(id));
  if (!ids.length || bad.length) throw new UsageError(`--only takes item ids separated by commas, from: ${known.join(', ')}${bad.length ? ` (not an id: ${bad.join(', ')})` : ''}`);
  return [...new Set(ids)];
}

// --nameserver: IP addresses, each with an optional port ("192.0.2.53", "192.0.2.53:5353",
// "[2001:db8::53]:53"), separated by commas. Never a name: a name would itself need looking up.
export function parseNameservers(arg) {
  const list = String(arg).split(',').map((x) => x.trim()).filter(Boolean);
  for (const ns of list) {
    const bracketed = /^\[([^\]]+)\](?::(\d{1,5}))?$/.exec(ns);
    const m = bracketed ?? /^([^:]+)(?::(\d{1,5}))?$/.exec(ns);
    const port = m?.[2] === undefined ? 53 : Number(m[2]);
    if (!m || !isIP(m[1]) || (bracketed && isIP(m[1]) !== 6) || port < 1 || port > 65535) throw new UsageError(`--nameserver takes IP addresses, with :port if not 53 (got "${ns}")`);
  }
  if (!list.length) throw new UsageError('--nameserver needs an address');
  return list;
}

// A lookup that asks only the given nameservers, for the domain's own requests: a computer that
// asked for the host before its record existed can go on answering "no such host" for minutes
// after the domain is live, while the zone's nameservers give the address at once.
function lookupAt(servers) {
  const resolver = new Resolver({ timeout: 3000, tries: 2 });
  resolver.setServers(servers);
  return (hostname, options, callback) => {
    const cb = typeof options === 'function' ? options : callback;
    const all = typeof options === 'object' && options?.all;
    const done = (list, family) => (all ? cb(null, list.map((address) => ({ address, family }))) : cb(null, list[0], family));
    resolver.resolve4(hostname, (e4, a4) => {
      if (!e4 && a4.length) { done(a4, 4); return; }
      resolver.resolve6(hostname, (e6, a6) => {
        if (!e6 && a6.length) { done(a6, 6); return; }
        // No address from either question: "no such name" when both said so, else the resolver's own
        // code (a timeout, a refusal), so a failing nameserver is not reported as a missing name.
        const codes = [e4?.code, e6?.code].filter(Boolean);
        const err = new Error(`${hostname} has no address at ${servers.join(', ')}`);
        err.code = codes.length && codes.every((c) => c === 'ENOTFOUND' || c === 'ENODATA') ? 'ENOTFOUND' : (e6?.code ?? e4?.code ?? 'ENOTFOUND');
        cb(err);
      });
    });
  };
}

// A bare domain means https://<domain>. A page on this machine ("http://127.0.0.1:4321") is
// taken as given: that is how a local preview, or the script's own tests, are checked.
export function parseTarget(arg) {
  const raw = String(arg).trim();
  let url;
  try {
    url = new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(raw) ? raw : `https://${raw}`);
  } catch {
    throw new UsageError(`"${raw}" is not a domain`);
  }
  if (url.protocol !== 'https:' && url.protocol !== 'http:') throw new UsageError(`"${raw}" is not a web address`);
  if (url.protocol === 'http:' && !LOCAL_HOST.test(url.hostname)) {
    throw new UsageError(`"${raw}": http:// is for a page on this machine. Give your domain without a scheme: ${url.hostname}`);
  }
  if (url.username || url.password || url.search || url.hash || url.pathname !== '/') {
    throw new UsageError(`give the domain only, with no path: "${url.hostname}", not "${raw}"`);
  }
  return {
    host: url.host,
    origin: url.origin,
    httpProbe: `http://${url.protocol === 'http:' ? url.host : url.hostname}/`,
    httpsOrigin: `https://${url.host}`,
  };
}

export function parseProject(arg) {
  const raw = String(arg).trim();
  const nameOk = (n) => /^[a-z0-9][a-z0-9-]{0,57}$/i.test(n);
  if (/^https?:\/\//i.test(raw)) {
    let u;
    try { u = new URL(raw); } catch { throw new UsageError(`"${raw}" is not a web address`); }
    const pagesDev = u.protocol === 'https:' && /^[a-z0-9-]+\.pages\.dev$/i.test(u.hostname);
    if (!pagesDev && !(u.protocol === 'http:' && LOCAL_HOST.test(u.hostname))) {
      throw new UsageError(`"${raw}" is not a pages.dev address: give the project's name, for example my-project`);
    }
    return { origin: u.origin, host: u.host, pagesDev };
  }
  const name = raw.replace(/\.pages\.dev$/i, '');
  if (!nameOk(name)) throw new UsageError(`"${raw}" is not a Pages project name (letters, digits and hyphens)`);
  return { origin: `https://${name}.pages.dev`, host: `${name}.pages.dev`, pagesDev: true };
}

// ---------------------------------------------------------------- asking

// One GET, never followed, never rejected: an error is part of the answer. A body is read up
// to MAX_BODY bytes (a page of the kit is a few hundred kilobytes); an answer that ends
// early, or does not end in time, is an error, never a page.
function get(url, { timeoutMs, ua = UA, accept = 'text/html,application/xhtml+xml,*/*;q=0.8', lookup }) {
  return new Promise((resolve) => {
    const signal = AbortSignal.timeout(timeoutMs);
    let done = false;
    const finish = (extra) => {
      if (done) return;
      done = true;
      resolve({ url, ...extra });
    };
    let u;
    try {
      u = new URL(url);
    } catch (e) {
      return finish({ error: { code: 'EBADURL', message: e.message } });
    }
    const lib = u.protocol === 'https:' ? https : http;
    const req = lib.request(u, {
      method: 'GET',
      signal,
      agent: false, // one connection per request, closed after it: nothing lingers
      ...(lookup ? { lookup } : {}),
      headers: { 'user-agent': ua, accept, 'accept-encoding': 'identity' },
    }, (res) => {
      const chunks = [];
      let size = 0;
      let capped = false;
      res.on('data', (c) => {
        size += c.length;
        if (size <= MAX_BODY) chunks.push(c);
        else if (!capped) {
          capped = true;
          res.destroy();
        }
      });
      res.on('error', () => {});
      res.on('close', () => {
        if (signal.aborted) return finish({ error: { code: 'ETIMEDOUT', message: 'timed out' } });
        if (!res.complete && !capped) {
          return finish({ error: { code: 'EINCOMPLETE', message: 'the answer was cut off' } });
        }
        return finish({
          status: res.statusCode,
          headers: res.headers,
          body: Buffer.concat(chunks).toString('utf8'),
          truncated: capped,
        });
      });
    });
    req.on('error', (e) => finish({
      error: { code: signal.aborted ? 'ETIMEDOUT' : (e.code || e.name), message: e.message },
    }));
    req.end();
  });
}

const header = (r, name) => {
  const v = r.headers?.[name];
  return Array.isArray(v) ? v.join(', ') : (v ?? '');
};

// The home page: a redirect to the same address is followed (a language redirect, say), so
// the page is judged where it ends. `hops` says what was followed.
async function getHome(url, t, stamp) {
  const hops = [];
  const chain = []; // the headers of every answer on the way: NEL or a cookie on a hop counts
  const chainUrls = []; // the address each of those answers came from, in the same order
  let r = await get(url, t);
  if (!r.error) { chain.push(r.headers); chainUrls.push(r.url); }
  while (!r.error && r.status >= 300 && r.status < 400 && hops.length < MAX_HOPS) {
    if (!header(r, 'location')) break; // nowhere to go
    let next;
    try {
      next = new URL(header(r, 'location'), r.url);
    } catch {
      break; // a Location that is not an address
    }
    if (next.origin !== new URL(url).origin) break; // another address: a person decides
    next.searchParams.set('cb', String(stamp));
    if (next.href === r.url) break; // to the page we are on
    hops.push({ status: r.status, location: header(r, 'location') });
    r = await get(next.href, t);
    if (!r.error) { chain.push(r.headers); chainUrls.push(r.url); }
  }
  return { ...r, hops, chain, chainUrls };
}

// The requests each item needs, beside the home page, which every run asks for. With --only, the
// others are not sent; they stand in the observation as "not asked", and count as no answer for
// nothing.
const NEEDS = { robots: ['robots'], ai: ['robots', 'crawlers'], https: ['httpProbe'], build: ['build'],
  pages: ['alias'], canonical: ['alias', 'aliasProbe'], nel: ['alias'] };
// The second request to the pages.dev address: a page with a query, which the forwarding must keep.
export const PROBE_PATH = '/robots.txt';

export async function observe(target, { timeoutMs, alias, only = null, nameservers = null }) {
  const stamp = Math.floor(Date.now() / 1000);
  const lookup = nameservers ? lookupAt(nameservers) : undefined; // the domain's requests only
  const t = { timeoutMs, lookup };
  const text = { timeoutMs, accept: 'text/plain,*/*;q=0.8', lookup };
  const homeUrl = `${target.origin}/?cb=${stamp}`;
  const asked = only ? new Set(only.flatMap((id) => NEEDS[id] ?? [])) : null;
  const ask = (name, url, fn) => (!asked || asked.has(name) ? fn() : Promise.resolve({ url, notAsked: true, error: { code: 'ENOTASKED', message: 'not asked' } }));
  const aliasProbeUrl = alias ? `${alias.origin}${PROBE_PATH}?cb=${stamp}` : null;
  const [home, robots, httpProbe, build, aliasHome, aliasProbe, ...crawlers] = await Promise.all([
    getHome(homeUrl, t, stamp),
    ask('robots', `${target.origin}/robots.txt`, () => get(`${target.origin}/robots.txt`, text)),
    ask('httpProbe', target.httpProbe, () => get(target.httpProbe, t)),
    ask('build', `${target.origin}/build.txt?cb=${stamp}`, () => get(`${target.origin}/build.txt?cb=${stamp}`, text)),
    alias ? ask('alias', `${alias.origin}/?cb=${stamp}`, () => get(`${alias.origin}/?cb=${stamp}`, { timeoutMs })) : Promise.resolve(null),
    alias ? ask('aliasProbe', aliasProbeUrl, () => get(aliasProbeUrl, { timeoutMs })) : Promise.resolve(null),
    ...CRAWLERS.map(([, ua]) => ask('crawlers', homeUrl, () => get(homeUrl, { timeoutMs, ua, lookup }))),
  ]);
  return {
    stamp, home, robots, httpProbe, build, alias: aliasHome, aliasProbe,
    crawlers: crawlers.map((r, i) => ({ name: CRAWLERS[i][0], ...r })),
  };
}

// Every request that was sent and got no answer at all.
export function unanswered(obs) {
  return [obs.home, obs.robots, obs.httpProbe, obs.build, obs.alias, obs.aliasProbe, ...obs.crawlers]
    .filter((r) => r && r.error && !r.notAsked)
    .map((r) => (r.name ? `${r.name} ${bare(r.url)}` : bare(r.url)));
}

// ---------------------------------------------------------------- judging

const bare = (url) => url.replace(/\?cb=\d+$/, '');

function whyNoAnswer(err, timeoutMs) {
  const known = {
    ENOTFOUND: 'the name could not be looked up (it may not exist, or this network blocks it)',
    EAI_AGAIN: 'the name could not be looked up',
    ECONNREFUSED: 'the connection was refused',
    ECONNRESET: 'the connection was reset',
    EINCOMPLETE: 'the answer was cut off before it was complete',
    ETIMEDOUT: `no answer within ${timeoutMs / 1000} second${timeoutMs === 1000 ? '' : 's'}`,
    CERT_HAS_EXPIRED: 'its certificate has expired',
    ERR_TLS_CERT_ALTNAME_INVALID: 'its certificate is for another name',
    DEPTH_ZERO_SELF_SIGNED_CERT: 'its certificate cannot be trusted',
    SELF_SIGNED_CERT_IN_CHAIN: 'its certificate cannot be trusted',
    UNABLE_TO_VERIFY_LEAF_SIGNATURE: 'its certificate cannot be trusted',
  };
  return known[err.code] ?? err.message;
}

// Do two addresses name the same page? Compared as addresses, not as text: "https://host"
// and "https://host:443/" are the page "https://host/".
function leadsTo(location, base, wanted) {
  try {
    const a = new URL(location, base);
    const b = new URL(wanted);
    return a.origin === b.origin && a.pathname === b.pathname;
  } catch {
    return false;
  }
}

// The same address, query included: what forwarding a page with a query must keep.
function sameExactly(location, base, wanted) {
  try {
    const a = new URL(location, base);
    const b = new URL(wanted);
    return a.origin === b.origin && a.pathname === b.pathname && a.search === b.search;
  } catch {
    return false;
  }
}

function addressOf(location, base) {
  try {
    return location ? new URL(location, base) : null;
  } catch {
    return null;
  }
}
function sameAddress(location, base) {
  return addressOf(location, base)?.origin === new URL(base).origin;
}

// A small reader of HTML: the tags of a page with their attributes (quotes respected, so a
// ">" inside a value does not end a tag), and the text of its scripts. Comments are skipped.
// It is not a browser. It is enough to tell what a page loads from what it says.
const RAW_TEXT = new Set(['script', 'style', 'textarea', 'title']);
const COMMENT_END = /--!?>/g;
export function readHtml(html) {
  // Only A to Z are lower-cased: Unicode lower-casing can change a string's length, and the
  // offsets found in this copy are used in the original.
  const lower = html.replace(/[A-Z]/g, (c) => String.fromCharCode(c.charCodeAt(0) + 32));
  const n = html.length;
  const tags = [];
  const scripts = [];
  // Foreign content: inside an <svg> the elements that are raw text in HTML (script, style,
  // textarea, title) hold markup, as in a browser; a <foreignObject> inside it is HTML again.
  const ctx = []; // 'svg' or 'html', innermost last
  let i = 0;
  while (i < n) {
    const lt = html.indexOf('<', i);
    if (lt === -1) break;
    if (html.startsWith('<!--', lt)) {
      // A comment ends at "-->" or "--!>", and "<!-->" and "<!--->" are whole comments.
      const abrupt = /^<!--(?:-?>)/.exec(html.slice(lt, lt + 8));
      if (abrupt) {
        i = lt + abrupt[0].length;
        continue;
      }
      // The first closer from here, found without copying the page and without looking for a
      // second closer that may not exist (that scan would run to the end, for every comment).
      COMMENT_END.lastIndex = lt + 4;
      const end = COMMENT_END.exec(html);
      i = end ? end.index + end[0].length : n;
      continue;
    }
    if (html[lt + 1] === '!' || html[lt + 1] === '?') {
      // <!doctype>, <![CDATA[...]]> and <?...?> are not tags: skip to the next ">".
      const end = html.indexOf('>', lt + 2);
      i = end === -1 ? n : end + 1;
      continue;
    }
    const m = /^<(\/?)([a-z][a-z0-9:-]*)/i.exec(html.slice(lt, lt + 64));
    if (!m) {
      i = lt + 1;
      continue;
    }
    const name = m[2].toLowerCase();
    let j = lt + m[0].length;
    const attrs = [];
    let selfClosing = false;
    while (j < n) {
      let last = '';
      while (j < n && /[\s/]/.test(html[j])) last = html[j++];
      if (j >= n) break;
      if (html[j] === '>') {
        selfClosing = last === '/'; // "<svg/>", not "<svg id=x/>" (there the slash is the value's)
        j++;
        break;
      }
      let k = j;
      while (k < n && !/[\s=>/]/.test(html[k])) k++;
      const attr = html.slice(j, k).toLowerCase();
      j = k === j ? j + 1 : k;
      while (j < n && /\s/.test(html[j])) j++;
      let value = '';
      if (html[j] === '=') {
        j++;
        while (j < n && /\s/.test(html[j])) j++;
        const q = html[j];
        if (q === '"' || q === "'") {
          const end = html.indexOf(q, j + 1);
          value = html.slice(j + 1, end === -1 ? n : end);
          j = end === -1 ? n : end + 1;
        } else {
          let e = j;
          while (e < n && !/[\s>]/.test(html[e])) e++;
          value = html.slice(j, e);
          j = e;
        }
      }
      if (attr) attrs.push([attr, value]);
    }
    i = j;
    if (m[1] === '') {
      if (name === 'svg' && !selfClosing) ctx.push('svg');
      else if (name === 'foreignobject' && !selfClosing) ctx.push('html'); // every start is paired with its end
    } else if (name === 'foreignobject' && ctx.at(-1) === 'html') {
      ctx.pop();
    } else if (name === 'svg') {
      while (ctx.length && ctx.pop() !== 'svg');
    }
    const foreign = ctx.at(-1) === 'svg';
    if (m[1] === '') {
      tags.push({ name, attrs });
      // The text of script, style, textarea and title is not markup in HTML, and a self-closing
      // slash on them is ignored there, as in a browser. In an svg these hold markup, except a
      // script, whose text is still read to its end tag (a CDATA section included), unless the
      // script is self-closed ("<script href=.../>").
      if (RAW_TEXT.has(name) && (!foreign || (name === 'script' && !selfClosing))) {
        // The text of these elements is not markup. Its end tag is "</name" followed by
        // white space, "/" or ">": "</scripture>" does not end a script.
        let end = i;
        for (;;) {
          end = lower.indexOf(`</${name}`, end);
          if (end === -1 || /[\s/>]/.test(lower[end + 2 + name.length] ?? '>')) break;
          end += 2;
        }
        if (end === -1) end = n;
        if (name === 'script') scripts.push(html.slice(i, end));
        i = end;
      }
    }
  }
  return { tags, scripts };
}

// The character references an address is likely to be written with. Not the whole table:
// numeric ones in full, and the few named ones that stand for a character of an address.
const NAMED = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", sol: '/', colon: ':', period: '.', lowbar: '_', hyphen: '-', num: '#', quest: '?', equals: '=', percnt: '%', comma: ',', semi: ';', nbsp: ' ' };
function decodeReferences(v) {
  return v.replace(/&(?:#(\d+);?|#x([0-9a-f]+);?|([a-z]+);)/gi, (all, dec, hex, name) => {
    const code = dec !== undefined ? Number(dec) : hex !== undefined ? parseInt(hex, 16) : null;
    if (code !== null) return Number.isFinite(code) && code > 0 && code < 0x110000 ? String.fromCodePoint(code) : all;
    return NAMED[name.toLowerCase()] ?? all;
  });
}

// What a page loads, as addresses: the paths under /cdn-cgi/ that its tags and scripts use,
// the hosts its tags point at, and the attribute names Cloudflare adds. Comments, the words a
// person reads, and descriptive attributes such as title or alt are not in it.
const POINTS_AT = new Set(['src', 'href', 'data-src', 'action', 'poster']);
function scanPage(body, base) {
  const { tags, scripts } = readHtml(body);
  const scriptHosts = new Set(); // the hosts a <script src> points at
  const attrNames = new Set();
  const address = (u) => {
    try {
      return new URL(decodeReferences(u.trim()), base);
    } catch {
      return null; // not an address
    }
  };
  const paths = new Set();
  for (const t of tags) {
    for (const [k, v] of t.attrs) {
      attrNames.add(k);
      const list = k === 'srcset' ? v.split(',').map((x) => x.trim().split(/\s+/)[0]).filter(Boolean) : POINTS_AT.has(k) ? [v] : [];
      for (const u of list) {
        const a = address(u);
        if (!a) continue;
        if (t.name === 'script' && k === 'src') scriptHosts.add(a.hostname.toLowerCase());
        if (a.pathname.toLowerCase().startsWith('/cdn-cgi/')) paths.add(a.pathname.toLowerCase());
      }
    }
  }
  for (const text of scripts) {
    for (const m of text.matchAll(/\/cdn-cgi\/[^\s"'`<>)\\?#;,]+/gi)) paths.add(m[0].toLowerCase());
  }
  return { paths: [...paths], scriptHosts, attrNames };
}

// The paths of Cloudflare's three named features, whole and anchored: a longer path that
// only contains one of these words is something else.
const KNOWN_CDN_CGI = [
  /^\/cdn-cgi\/challenge-platform\//,
  /^\/cdn-cgi\/l\/email-protection$/,
  /^\/cdn-cgi\/scripts\/[^/]+\/cloudflare-static\/email-decode\.min\.js$/,
];

// A report-to header is a list of JSON objects. Is Cloudflare's NEL group among them?
// null when it cannot be read.
function cloudflareGroup(value) {
  let groups;
  try {
    groups = JSON.parse(`[${value}]`).flat();
  } catch {
    return null;
  }
  const nelHost = (e) => {
    try { return /(^|\.)nel\.cloudflare\.com$/i.test(new URL(e.url).hostname); } catch { return false; }
  };
  return groups.some((g) => g && (g.group === 'cf-nel' || (Array.isArray(g.endpoints) && g.endpoints.some(nelHost))));
}

// Cloudflare's script monitor (Client-side security, formerly Page Shield) has browsers report
// the scripts a page loads to csp-reporting.cloudflare.com, on a sample of pages. It shows in a
// report-to group, in a reporting-endpoints entry and in the report-uri of a report-only policy;
// any one of the three names it. This names what Cloudflare sends; it does not decide what a
// browser would make of a header (a malformed one is read the same way, and an address that a
// browser would ignore, a duplicate directive for one, still names it). Each header is read by the
// syntax it is written in, and only the addresses it lists to REPORT TO are judged, by their host:
// not a group's name, and not text that quotes the host in a path, a query or a user name, or that
// lists it as a source.
const monitorHost = (u) => {
  if (typeof u !== 'string') return false;
  try { return /(^|\.)csp-reporting\.cloudflare\.com$/i.test(new URL(u).hostname.replace(/\.$/, '')); } catch { return false; }
};
// With Client-Side Security Advanced, Cloudflare can send the same reports to the site's own host
// instead, at this path (Cloudflare's settings page, read 14 October 2026: hyphens here, an
// underscore in the path on its own host). Only this exact path on the origin (scheme, host and
// port) of the answer that carries the header counts, and an address written relative to that
// answer is read against its address.
const OWN_HOST_REPORT_PATH = '/cdn-cgi/script-monitor/report';
export const ownHostReport = (page) => (u) => {
  if (typeof u !== 'string' || !page) return false;
  try {
    const a = new URL(u, page);
    return a.origin === new URL(page).origin && a.pathname === OWN_HOST_REPORT_PATH;
  } catch { return false; }
};
// A reporting-endpoints header is written as a dictionary: name="address", name="address";p="x".
// The string after a member's `=` is its address; a parameter's string is not, and a string may hold
// \" or a comma. This is not a Structured Fields validator.
function endpointAddresses(value) {
  const members = [];
  let current = '';
  let quoted = false;
  for (let i = 0; i < value.length; i++) {
    const c = value[i];
    if (quoted && c === '\\') { current += c + (value[i + 1] ?? ''); i++; continue; }
    if (c === '"') quoted = !quoted;
    if (c === ',' && !quoted) { members.push(current); current = ''; continue; }
    current += c;
  }
  members.push(current);
  return members
    .map((m) => /^\s*[A-Za-z*][A-Za-z0-9_.*-]*\s*=\s*"((?:[^"\\]|\\.)*)"/.exec(m))
    .filter(Boolean)
    .map((m) => m[1].replace(/\\(.)/g, '$1'));
}
// isMonitor judges one address: monitorHost, or ownHostReport(page) for the site's own host.
function cloudflareMonitor(name, value, isMonitor = monitorHost) {
  if (name === 'report-to') { // a list of JSON groups; a value that does not parse is not read
    let groups;
    try { groups = JSON.parse(`[${value}]`).flat(); } catch { return false; }
    return groups.some((g) => g && Array.isArray(g.endpoints) && g.endpoints.some((e) => e && isMonitor(e.url)));
  }
  if (name === 'reporting-endpoints') return endpointAddresses(value).some(isMonitor);
  // content-security-policy-report-only: policies are written split at commas, directives at
  // semicolons; any report-uri directive that lists the address names it (never hidden behind
  // another one: whether a browser uses a duplicate is not decided here)
  return value.split(',').some((policy) => policy.split(';').some((d) => {
    const [directive, ...addresses] = d.trim().split(/\s+/);
    return /^report-uri$/i.test(directive) && addresses.some(isMonitor);
  }));
}

// robots.txt, read the way a crawler reads it: groups of User-agent lines with their rules.
function readRobots(body) {
  const groups = [];
  const sitemaps = [];
  let signals = false;
  let current = null;
  let lastWasAgent = false;
  for (const raw of body.split(/\r?\n/)) {
    const m = /^([a-z-]+)\s*:\s*(.*)$/i.exec(raw.replace(/#.*/, '').trim());
    if (!m) continue;
    const key = m[1].toLowerCase();
    const val = m[2].trim();
    if (key === 'user-agent') {
      if (!current || !lastWasAgent) {
        current = { agents: [], rules: [] };
        groups.push(current);
      }
      current.agents.push(val);
      lastWasAgent = true;
      continue;
    }
    lastWasAgent = false;
    if (key === 'sitemap') sitemaps.push(val);
    else if (key === 'content-signal') signals = true;
    else if ((key === 'allow' || key === 'disallow') && current) current.rules.push([key, val]);
  }
  // "/", "/*" and "*" all name every path. When a group both disallows and allows such a
  // pattern, RFC 9309 2.2.2 decides: "The most specific match is the match that has the most
  // octets ... If an "allow" rule and a "disallow" rule are equivalent, then the "allow" rule
  // SHOULD be used." So "Disallow: /*" (two octets) beats "Allow: /" (one), and "Disallow: /"
  // with "Allow: /" is open. The length is that of the pattern, as in Google's published parser
  // (github.com/google/robotstxt at 50a0dac, robots.cc: MatchAllow and MatchDisallow return
  // pattern.length() as the priority, and a path is disallowed only when the disallow priority
  // is greater than the allow priority). Read as the octets a URI matches, "Disallow: /*" would
  // leave "/" itself open. Either way every other page is blocked, which is what the verdict
  // says.
  const everything = (v) => v === '/' || /^\/?\*+$/.test(v);
  const longest = (g, kind) => g.rules.reduce((m, [k, v]) => (k === kind && everything(v) ? Math.max(m, v.length) : m), 0);
  const blocks = (g) => longest(g, 'disallow') > longest(g, 'allow');
  const named = groups.flatMap((g) => g.agents).filter((a) => a !== '*');
  return {
    hasStar: groups.some((g) => g.agents.includes('*')),
    blocksAll: groups.some((g) => g.agents.includes('*') && blocks(g)),
    named,
    signals,
    sitemaps,
  };
}

export function evaluate(obs, target, opts) {
  const out = new Map();
  const blocked = new Set(); // "not run" because something could not be judged, not because it was not asked for
  const put = (id, state, detail, fix) => {
    const r = { state, detail };
    if (fix && (state === 'fail' || state === 'look')) r.fix = fix;
    out.set(id, r);
  };
  const skip = (id, detail, { couldNot = true } = {}) => {
    put(id, 'skip', detail);
    if (couldNot) blocked.add(id);
  };
  const { home, robots, httpProbe, build, alias, crawlers } = obs;
  const noAnswer = (r) => `no answer from ${bare(r.url)}: ${whyNoAnswer(r.error, opts.timeoutMs)}`;
  const section = (n) => `See section ${n} of the Cloudflare checklist.`;

  // 1. The domain answers, and the answer is the site's. Everything about the page hangs on it.
  const challenged = !home.error && header(home, 'cf-mitigated') === 'challenge';
  const seen = !home.error && !challenged && home.status < 400; // its headers can be judged
  const offPage = seen && home.status !== 200; // ... but a redirect, a 204 and the like are not the page
  const empty = seen && home.status === 200 && home.body.trim() === '';
  const page = seen && home.status === 200 && !empty && /html/i.test(header(home, 'content-type'));
  const whyNot = home.error ? noAnswer(home)
    : challenged ? `Cloudflare answered ${home.status} with a challenge page, so the site itself was not seen`
      : `the home page answered ${home.status}${empty ? ' with an empty page' : page ? '' : ', not a 200 page of HTML'}`;
  const notChecked = `not checked: ${whyNot}`;
  const cloudflareError = {
    522: 'Cloudflare cannot reach your Pages project: the domain is probably not attached to it',
    523: 'Cloudflare cannot reach the origin',
    525: 'the secure connection to the origin failed',
    526: 'the origin certificate is not valid',
  };
  const hopsNote = home.hops?.length
    ? ` It answered ${home.hops[0].status} first and sent us to ${home.hops[0].location}${home.hops.length > 1 ? ' and on' : ''}; the page is judged where that ends.`
    : '';
  const where = bare(home.url);
  // The headers of each answer on the way, the page's own last. Each is read by itself: two
  // values joined are not one value.
  const values = (name) => (home.chain ?? []).map((h) => [].concat(h[name] ?? []).join(', ')).filter(Boolean);

  if (home.error) put('domain', 'fail', noAnswer(home), `Is the domain attached to the project, and are its DNS records on Cloudflare? ${section(1)}`);
  else if (challenged) put('domain', 'fail', `Cloudflare answered ${home.status} with a challenge page, so the site itself was not seen. Bot Fight Mode, or a rule, is challenging requests like this one.`, section(3));
  else if (home.status >= 400) put('domain', 'fail', `${where} answered ${home.status}${cloudflareError[home.status] ? `: ${cloudflareError[home.status]}` : ''}.`, section(1));
  else if (home.status >= 300 && !addressOf(header(home, 'location'), home.url)) put('domain', 'look', `${where} answered ${home.status} with ${header(home, 'location') ? `a Location that is not an address (${header(home, 'location').slice(0, 60)})` : home.headers.location === undefined ? 'no Location header' : 'an empty Location header'}, so the page was not judged.`);
  else if (home.status >= 300 && sameAddress(header(home, 'location'), home.url)) put('domain', 'look', `${where} redirected ${home.hops.length + 1 === 1 ? 'once' : `${home.hops.length + 1} times`} on this address and was still redirecting (to ${header(home, 'location')}), so the page was not judged.`);
  else if (home.status >= 300) put('domain', 'look', `${where} answered ${home.status} and sends visitors to ${header(home, 'location')}. That is another address, so the page was not judged: run the check on it.`, 'Is that redirect yours (www, another language)? Run the check against the address it leads to.');
  else if (home.status !== 200) put('domain', 'look', `${where} answered ${home.status}, not a 200 page, so the page was not judged.`);
  else if (empty) put('domain', 'fail', `${where} answered 200 with nothing in it: an empty page is not your site.`, section(1));
  else if (!header(home, 'cf-ray')) put('domain', 'look', `${where} answered 200, but no cf-ray header came with the answer, so there is no sign it came through Cloudflare. Are this domain's DNS records on Cloudflare yet, and is this your site?${hopsNote}`, section(1));
  else if (home.hops?.length) put('domain', 'look', `${where} answered 200.${hopsNote}`);
  else put('domain', 'ok', `${where} answered 200.`);

  // 2. http:// goes to https://
  if (httpProbe.error) put('https', 'fail', noAnswer(httpProbe), section(2));
  else {
    const loc = header(httpProbe, 'location');
    const to = leadsTo(loc, httpProbe.url, `${target.httpsOrigin}/`);
    const s = httpProbe.status;
    if ((s === 301 || s === 308) && to) put('https', 'ok', `http:// answers ${s} and sends visitors to ${loc}.`);
    else if (s >= 300 && s < 400 && to) put('https', 'look', `http:// answers ${s}, a temporary redirect, to ${loc}. Visitors arrive on https, but Always Use HTTPS sends a 301.`, section(2));
    else if (s >= 300 && s < 400) put('https', 'fail', `http:// sends visitors to ${loc || 'another address'}, not to ${target.httpsOrigin}/`, section(2));
    else put('https', 'fail', `http:// answers ${s} with no redirect: Always Use HTTPS is off, or does not reach this address.`, section(2));
  }

  // 3. HSTS
  if (!seen) skip('hsts', notChecked);
  else {
    const sts = header(home, 'strict-transport-security');
    const earlierOnly = !sts && values('strict-transport-security').length > 0;
    const via = offPage ? ` (judged from the ${home.status} answer, not the page)` : '';
    if (!sts) {
      const note = earlierOnly ? ' (only the redirect before it carried one)' : '';
      if (opts.hstsOn) put('hsts', 'fail', `you said HSTS is on, but the answer has no strict-transport-security header${note}${via}.`, section(2));
      else put('hsts', 'look', `not on yet${note}${via}. Switch it on a few days after go-live, then run this check again with --hsts-on.`);
    } else {
      const age = Number(/(?:^|;)\s*max-age\s*=\s*"?(\d+)"?\s*(?:;|$)/i.exec(sts)?.[1] ?? NaN);
      const sub = /(?:^|;)\s*includesubdomains\s*(?:;|$)/i.test(sts);
      const pre = /(?:^|;)\s*preload\s*(?:;|$)/i.test(sts);
      const months = Math.round(age / MONTH);
      const shown = `on: max-age ${age} (about ${months} month${months === 1 ? '' : 's'}), subdomains ${sub ? 'on' : 'off'}, preload ${pre ? 'on' : 'off'}.`;
      if (!(age > 0)) put('hsts', 'look', `${sts}: a max-age of 0, or none, switches HSTS off in browsers.`, section(2));
      else if (age < SHORTEST_MONTH) put('hsts', 'look', `${shown} That is shorter than the one month (at least ${SHORTEST_MONTH_DAYS} days, ${SHORTEST_MONTH} seconds) the checklist starts with.`, section(2));
      else if (pre) put('hsts', 'look', `${shown} The checklist says preload Off: it needs 12 months and can lock visitors out if HTTPS ever breaks.`, section(2));
      else if (offPage) put('hsts', 'look', `${shown} Judged from the ${home.status} answer, not the page.`);
      else put('hsts', 'ok', shown);
    }
  }

  // 4. NEL
  if (!seen) skip('nel', notChecked);
  else {
    const policies = values('nel').map((v) => {
      try { return JSON.parse(v); } catch { return null; } // not JSON is still a nel header
    });
    const live = policies.find((p) => p === null || p.max_age !== 0); // a policy that is not a withdrawal
    const withdrawn = policies.length > 0 && !live;
    const reports = values('report-to');
    const cfReport = reports.some((v) => cloudflareGroup(v) === true);
    const monitorHeaders = ['report-to', 'reporting-endpoints', 'content-security-policy-report-only'];
    const monitorAt = (isMonitor) => monitorHeaders.some((name) => values(name).some((v) => cloudflareMonitor(name, v, isMonitor)));
    // An own-host address is judged answer by answer, against the address of the answer that carries
    // it: a hop's relative address is read against the hop, as the Cloudflare host is read on hops too.
    const monitorOwn = (home.chain ?? []).some((h, i) => monitorHeaders
      .some((name) => [].concat(h[name] ?? []).some((v) => cloudflareMonitor(name, v, ownHostReport(home.chainUrls?.[i])))));
    const monitor = monitorOwn || monitorAt(monitorHost);
    const nel = policies.length > 0;
    const age = Number.isFinite(live?.max_age) ? ` (max_age ${live.max_age} seconds)` : '';
    const aliasSends = alias && !alias.error ? ['nel', 'report-to'].filter((h) => header(alias, h)) : [];
    const aliasNel = aliasSends.length
      ? ` The pages.dev address still sends ${aliasSends.map((h) => `a ${h} header`).join(' and ')}; the header rule cannot reach it, and no way to remove ${aliasSends.length > 1 ? 'them' : 'it'} there has been found.` : '';
    const via = offPage ? ` (judged from the ${home.status} answer, not the page)` : '';
    // The script monitor is named wherever it is seen, beside a NEL failure too: it is not NEL,
    // and the header rule for NEL removes only NEL and Report-To, so it does not switch it off.
    const monitorWhat = `Cloudflare says it adds a content-security-policy-report-only header to a sample of pages, and that visitors' browsers then send reports to Cloudflare. On the one site where this was seen it came with a report-to group, cf-csp-endpoint, at csp-reporting.cloudflare.com. That is not NEL.${monitorOwn ? " Here a header lists the site's own address, /cdn-cgi/script-monitor/report, as where to report: Cloudflare offers that with Client-Side Security Advanced." : ''}`;
    const monitorAlso = monitor ? ` Cloudflare's script monitor is switched on as well: ${monitorWhat}` : '';
    const monitorFix = "Your domain → Security → Settings → filter by Client-side abuse → Continuous script monitoring: Off. The checklist's header rule for NEL removes only the NEL and Report-To headers; it does not switch the monitor off.";
    const sampleNote = " Cloudflare's script monitor adds its headers to a sample of pages only, so this one answer cannot show that it is off.";
    if (nel && live !== undefined) put('nel', 'fail', `the answer carries a nel header${age}: Network Error Logging is on${via}.${monitorAlso}`, `Switch it off and, if the header stays, add the header rule. ${section(3)}`);
    else if (cfReport) put('nel', 'fail', `the answer carries Cloudflare's NEL reporting group in a report-to header${via}.${monitorAlso}`, `Remove it with the header rule. ${section(3)}`);
    else if (withdrawn) put('nel', 'look', `the nel header says max_age 0, which tells browsers to forget the policy${via}.${monitorAlso}${aliasNel}`, section(3));
    else if (monitor) put('nel', 'look', `no nel header, but Cloudflare's script monitor is switched on${via}: ${monitorWhat}${aliasNel}`, monitorFix);
    else if (reports.length) put('nel', 'look', `no nel header, but a report-to header is sent${via}. If it is not yours, remove it with the header rule; if your site sets its own reporting groups, leave it.${aliasNel}`, section(3));
    else if (offPage) put('nel', 'look', `no nel and no report-to header, judged from the ${home.status} answer, not the page.${sampleNote}${aliasNel}`);
    else put('nel', 'ok', `no nel and no report-to header on the home page.${sampleNote}${aliasNel}`);
  }

  // 5. What Cloudflare adds to the page: cookies and scripts.
  const scanned = page ? scanPage(home.body, home.url) : null;
  const partial = page && home.truncated;
  const partialNote = 'the page is larger than 5 MB and only the first 5 MB were read';
  const unseenPage = !seen ? notChecked : `not checked: ${whyNot}, so its source was not read`;
  const cookies = seen ? [...new Set((home.chain ?? []).flatMap((h) => [].concat(h['set-cookie'] ?? [])).map((c) => c.split('=')[0].trim()))] : [];
  const cfCookies = cookies.filter((c) => CF_COOKIE.test(c));
  const found = {
    bot: scanned?.paths.some((p) => KNOWN_CDN_CGI[0].test(p)) ?? false,
    analytics: scanned ? scanned.attrNames.has('data-cf-beacon') || scanned.scriptHosts.has('static.cloudflareinsights.com') : false,
    email: scanned ? scanned.attrNames.has('data-cfemail') || scanned.paths.some((p) => KNOWN_CDN_CGI[1].test(p) || KNOWN_CDN_CGI[2].test(p)) : false,
  };
  const judgeSource = (id, hit, hitText, okText) => {
    if (hit) put(id, 'fail', hitText, section(3));
    else if (partial) put(id, 'look', `nothing found, but ${partialNote}.`);
    else if (scanned) put(id, 'ok', okText);
    else skip(id, unseenPage);
  };

  if (cfCookies.length) {
    put('bot', 'fail', `the home page sets ${cfCookies.length === 1 ? 'a cookie' : 'cookies'} that belong${cfCookies.length === 1 ? 's' : ''} to Cloudflare: ${cfCookies.join(', ')}.`, section(3));
  } else if (found.bot) {
    put('bot', 'fail', 'the page loads Cloudflare\'s bot-detection script (/cdn-cgi/challenge-platform/).', section(3));
  } else if (cookies.length) {
    put('bot', 'look', `the home page sets ${cookies.length === 1 ? 'a cookie' : 'cookies'} that ${cookies.length === 1 ? 'is' : 'are'} not Cloudflare's own: ${cookies.join(', ')}. The privacy page promises none: find out what sets ${cookies.length === 1 ? 'it' : 'them'}.`, section(3));
  } else judgeSource('bot', false, '', 'no cookie and no bot-detection script in the page we received. A browser can see more: view the source once.');

  judgeSource('analytics', found.analytics, 'the page loads Cloudflare\'s measurement script (static.cloudflareinsights.com, or a data-cf-beacon attribute).', 'no Cloudflare measurement script in the page we received.');
  judgeSource('email', found.email, 'the page carries Cloudflare\'s address hiding (its email-decode script, a /cdn-cgi/l/email-protection link, or data-cfemail).', 'no Cloudflare address hiding (email-decode script, protected link or data-cfemail) in the page we received.');

  // Anything else from /cdn-cgi/: Rocket Loader, Zaraz, image resizing, whatever comes next.
  if (scanned) {
    const others = scanned.paths.filter((p) => !KNOWN_CDN_CGI.some((re) => re.test(p)));
    if (others.length) put('scripts', 'look', `the page uses ${others.slice(0, 4).join(', ')}${others.length > 4 ? ` and ${others.length - 4} more` : ''}. These are Cloudflare features (Rocket Loader, Zaraz, image resizing and the like). Did you switch them on?`, section(5));
    else if (partial) put('scripts', 'look', `nothing found, but ${partialNote}.`);
    else put('scripts', 'ok', 'no other /cdn-cgi/ path in the page we received.');
  } else skip('scripts', unseenPage);

  // 6. robots.txt, and what the AI crawlers get.
  let rb = null; // what could be read of robots.txt
  let robotsRead = false;
  if (robots.error) {
    if (home.error) skip('robots', notChecked);
    else put('robots', 'fail', noAnswer(robots), 'The starter\'s robots.txt, with your own domain in the Sitemap line.');
  } else if (robots.truncated) {
    put('robots', 'look', 'robots.txt is larger than 5 MB and only the start was read: it was not judged.', 'The starter\'s robots.txt is a few lines long.');
  } else if (robots.status === 404) {
    put('robots', 'look', 'no robots.txt (404). The starter ships one; without it search engines crawl everything.', 'The starter\'s robots.txt, with your own domain in the Sitemap line.');
  } else if (robots.status !== 200) {
    put('robots', 'fail', `robots.txt answered ${robots.status}.`, 'The starter\'s robots.txt, with your own domain in the Sitemap line.');
  } else if (/^\s*<(?:!doctype|html|head|body)\b/i.test(robots.body)) {
    put('robots', 'fail', 'robots.txt answers with a web page, not a robots file.', 'The starter\'s robots.txt, with your own domain in the Sitemap line.');
  } else {
    rb = readRobots(robots.body);
    robotsRead = true;
    const hostOf = (u) => { try { return new URL(u).host; } catch { return ''; } };
    const stripWww = (h) => h.replace(/^www\./i, '').toLowerCase();
    const placeholder = rb.sitemaps.find((s) => /^(?:www\.)?example\.(?:com|org|net)$/i.test(hostOf(s)) && stripWww(hostOf(s)) !== stripWww(target.host));
    const fix = 'The starter\'s robots.txt, with your own domain in the Sitemap line.';
    if (rb.blocksAll) put('robots', 'fail', 'robots.txt tells every crawler to stay out (Disallow: /): search engines and AI assistants will not read your pages.', section(4));
    else if (!rb.hasStar) put('robots', 'look', 'no "User-agent: *" group: is this your own file?', fix);
    else if (placeholder) put('robots', 'fail', `the Sitemap line still names the starter's placeholder (${placeholder}). Set your real domain.`, fix);
    else if (!rb.sitemaps.length) put('robots', 'look', 'no Sitemap line.', fix);
    else if (!rb.sitemaps.some((s) => stripWww(hostOf(s)) === stripWww(target.host))) put('robots', 'look', `the Sitemap line names ${hostOf(rb.sitemaps[0]) || rb.sitemaps[0]}, not ${target.host}.`, fix);
    else put('robots', 'ok', `a robots file with a Sitemap line that names ${target.host}.`);
  }

  // AI crawlers: the policy is a dashboard setting. Outside, there is a hint and a robots file.
  const refused = seen ? crawlers.filter((c) => !c.error && c.status >= 400).map((c) => `${c.name} (${c.status})`) : [];
  const silent = crawlers.filter((c) => c.error).map((c) => c.name);
  const named = [...(rb?.named ?? []), ...(rb?.signals ? ['(content-signal lines)'] : [])];
  const aiPath = ITEMS.find((i) => i.id === 'ai').path;
  const aiHand = `The policies are in the dashboard (${aiPath}) and cannot be read from outside. Nor can the switches the checklist lists after the policies: AI Labyrinth, Bot Preference Sync (Off unless you block Training; what it adds shows in robots.txt) and the content-bot block.`;
  if (!seen) skip('ai', notChecked);
  else if (refused.length) put('ai', 'look', `these crawler names were refused: ${refused.join(', ')}. If you chose to block Training that is expected; otherwise set Search, Agent and Training to Allow.`, section(4));
  else if (rb?.blocksAll) put('ai', 'look', 'robots.txt tells every crawler to stay out, AI crawlers included.', section(4));
  else if (silent.length === crawlers.length) skip('ai', 'not checked: no crawler request got an answer.');
  else if (silent.length) put('ai', 'look', `${silent.length} of ${crawlers.length} crawler requests got no answer (${silent.join(', ')}), so they were not all tried. ${aiHand}`, section(4));
  else if (named.length) put('ai', 'look', `no crawler name was refused, but robots.txt has rules for ${named.join(', ')}. Confirm you wrote them or chose them in Cloudflare. ${aiHand}`, section(4));
  else put('ai', 'hand', `outside evidence: none of ${crawlers.length} AI crawler names was refused${robotsRead ? ', and robots.txt names no crawler' : ' (robots.txt could not be read)'}. A name alone may not be treated as the real crawler, so this is a hint. ${aiHand}`);

  // 7. build.txt: which build is live.
  if (build.error && home.error) skip('build', notChecked);
  else if (build.error) put('build', 'look', `could not read build.txt: ${whyNoAnswer(build.error, opts.timeoutMs)}.`);
  else if (build.truncated) put('build', 'look', 'build.txt is larger than 5 MB: that is not a build marker.');
  else if (build.status !== 200) put('build', 'look', `no build.txt (${build.status}). Sites made with the kit write one at build time, so this says nothing about which build is live.`);
  else {
    const sha = build.body.trim();
    if (sha === 'dev') put('build', 'look', 'build.txt says "dev": that build was not made by Cloudflare or from a git checkout.');
    else if (!/^[0-9a-f]{40}$/i.test(sha)) put('build', 'look', /^[0-9a-f]+$/i.test(sha) ? `build.txt holds ${sha.length} characters: the kit writes the full 40-character commit id.` : 'build.txt is not a build marker (the answer is not a commit id).');
    else if (!opts.build) put('build', 'look', `serves build ${sha.slice(0, 12)}. Nothing was compared: pass --build <commit you deployed> to check that it is the live one.`);
    else if (sha.toLowerCase().startsWith(opts.build.toLowerCase())) put('build', 'ok', `serves build ${sha.slice(0, 12)}, the one you expected.`);
    else put('build', 'fail', `serves build ${sha.slice(0, 12)}, but you expected ${opts.build.toLowerCase().slice(0, 12)}: the live domain is on another build. Wait for the deploy, or look at Deployments.`, section(5));
  }

  // 8. The pages.dev address (only when --project is given).
  if (!alias) {
    skip('pages', 'not checked: give --project <address> (the project\'s pages.dev address) to check that it answers (a Worker answers on workers.dev).', { couldNot: false });
    skip('canonical', 'not checked: give --project <address> (the project\'s pages.dev address) to check that it forwards to your domain.', { couldNot: false });
  } else if (alias.error) {
    const gone = alias.error.code === 'ENOTFOUND';
    put('pages', 'fail', `${noAnswer(alias)}${gone ? '. Check the project name: a Worker would answer on a workers.dev address, not pages.dev.' : ''}`, section(1));
    skip('canonical', 'not checked: the pages.dev address did not answer.');
  } else {
    const aliasChallenged = header(alias, 'cf-mitigated') === 'challenge';
    if (aliasChallenged) put('pages', 'fail', `${bare(alias.url)} answered ${alias.status} with a challenge page, so the project was not seen.`, section(1));
    else if (alias.status >= 400) put('pages', 'fail', `${bare(alias.url)} answers ${alias.status}: the project has no live deployment, or something is wrong with it.`, section(1));
    else if (!obs.aliasIsPagesDev) put('pages', 'look', `${bare(alias.url)} answers ${alias.status}, but it is not a pages.dev address, so it is not known to be a Pages project.`);
    else put('pages', 'ok', `${bare(alias.url)} answers ${alias.status}: this is a Pages project.`);
    const loc = header(alias, 'location');
    const to = leadsTo(loc, alias.url, `${target.httpsOrigin}/`);
    // The forwarding must keep a page's path and query (follow-up U1): a page with a query is
    // asked too, and must be sent to the same page on the domain.
    const probe = obs.aliasProbe;
    if (alias.status === 301 && to) {
      const probeLoc = probe && !probe.error ? header(probe, 'location') : '';
      const wanted = probe ? (() => { const u = new URL(probe.url); return `${target.httpsOrigin}${u.pathname}${u.search}`; })() : '';
      if (!probe || probe.error) skip('canonical', `not checked whole: / answers 301 to ${loc}, but ${probe ? `${bare(probe.url)} got no answer` : 'no page with a query was asked'}, so whether a page keeps its path and query is not known.`);
      else if (probe.status === 301 && sameExactly(probeLoc, probe.url, wanted)) put('canonical', 'ok', `answers 301 and sends visitors to ${loc}; a page keeps its path and query (${probe.url} goes to ${probeLoc}).`);
      else put('canonical', 'fail', `/ answers 301 to ${loc}, but ${probe.url} answers ${probe.status}${probeLoc ? ` to ${probeLoc}` : ''}, not 301 to ${wanted}: a page loses its path or its query on the way.`, section(1));
    } else if (alias.status >= 300 && alias.status < 400 && to) put('canonical', 'look', `answers ${alias.status}, not 301, to ${loc}.`, section(1));
    else if (alias.status >= 300 && alias.status < 400) put('canonical', 'fail', `sends visitors to ${loc || 'another address'}, not to ${target.httpsOrigin}/`, section(1));
    else if (alias.status === 200) put('canonical', 'fail', 'answers 200: CANONICAL_URL is not under Production, is misnamed or malformed, the deployment is older than the variable, or the day\'s Functions allowance ran out with Fail open on.', section(1));
    else put('canonical', 'fail', `answers ${alias.status}.`, section(1));
  }

  // The items nothing from outside can see (the AI policy was settled above).
  for (const item of ITEMS.filter((i) => i.path && i.id !== 'ai')) {
    const place = item.path.startsWith('your project') ? `Workers & Pages → ${item.path}` : item.path;
    put(item.id, 'hand', `${place}: ${item.lookFor}.`);
  }

  const results = ITEMS.filter((item) => !opts.only || opts.only.includes(item.id)).map((item) => {
    const r = out.get(item.id);
    if (!r) throw new Error(`cloudflare-check: no result for "${item.id}"`);
    return { id: item.id, section: item.section, title: item.title, ...r, ...(blocked.has(item.id) ? { blocked: true } : {}) };
  });
  return results;
}

// ---------------------------------------------------------------- saying it

const WORD = { ok: 'ok', fail: 'FAIL', look: 'look', hand: 'by hand', skip: 'not run' };

export function summarize(results) {
  const n = { ok: 0, fail: 0, look: 0, hand: 0, skip: 0 };
  for (const r of results) n[r.state]++;
  return n;
}

export function render(results, target, when, silent = [], only = null) {
  const lines = [`Cloudflare check for ${target.host}`, `Looked from outside with plain GET requests, ${when}. Nothing was changed.`];
  if (only) lines.push(`Only these items were judged (--only): ${only.join(', ')}.`);
  let section = 0;
  for (const r of results) {
    if (r.section !== section) {
      section = r.section;
      lines.push('', `${section} · ${SECTIONS[section]}`);
    }
    lines.push(`  ${WORD[r.state].padEnd(8)} ${r.title.replace(/`/g, '')}`);
    lines.push(`           ${r.detail}`);
    if (r.fix) lines.push(`           → ${r.fix}`);
  }
  const n = summarize(results);
  const stuck = results.filter((r) => r.blocked).length;
  lines.push('', `Result: ${n.ok} ok, ${n.fail} FAIL, ${n.look} look, ${n.hand} by hand, ${n.skip} not run.`);
  if (silent.length) lines.push(`${silent.length} request${silent.length === 1 ? '' : 's'} got no answer, which counts as a failure: ${silent.join(', ')}`);
  if (stuck) lines.push(`${stuck} item${stuck === 1 ? '' : 's'} could not be judged, which counts as a failure: they are the "not run" lines that say "not checked".`);
  if (n.fail) lines.push('FAIL means the checklist is not met and it is worth fixing first. The checklist says how.');
  if (n.look) lines.push('"look" means the answer is not wrong on its face but needs a person to say whether it is what you meant.');
  if (n.hand) lines.push('"by hand" items have no outside check, or only a hint: open the dashboard path shown.');
  return `${lines.join('\n')}\n`;
}

export async function main(argv, now = () => new Date()) {
  const fail = (e) => ({ code: 2, stdout: '', stderr: `cloudflare-check: ${e.message}\n\n${USAGE}` });
  let parsed;
  try {
    parsed = parseArgs(argv);
  } catch (e) {
    if (!(e instanceof UsageError)) throw e;
    return fail(e);
  }
  if (parsed.opts.help) return { code: 0, stdout: USAGE, stderr: '' };
  let target;
  let alias = null;
  try {
    target = parseTarget(parsed.domain);
    if (parsed.opts.project) alias = parseProject(parsed.opts.project);
  } catch (e) {
    if (!(e instanceof UsageError)) throw e;
    return fail(e);
  }
  const obs = await observe(target, { timeoutMs: parsed.opts.timeoutMs, alias, only: parsed.opts.only, nameservers: parsed.opts.nameservers });
  obs.aliasIsPagesDev = alias?.pagesDev ?? false;
  const results = evaluate(obs, target, parsed.opts);
  const n = summarize(results);
  const silent = unanswered(obs);
  const stuck = results.filter((r) => r.blocked).map((r) => r.id);
  const code = n.fail || silent.length || stuck.length ? 1 : 0;
  const when = now().toISOString().replace(/\.\d+Z$/, 'Z');
  if (parsed.opts.json) {
    const body = { domain: target.host, checkedAt: when, ...(parsed.opts.only ? { only: parsed.opts.only } : {}), summary: n, unanswered: silent, couldNotJudge: stuck, results };
    return { code, stderr: '', stdout: `${JSON.stringify(body, null, 2)}\n` };
  }
  return { code, stderr: '', stdout: render(results, target, when, silent, parsed.opts.only) };
}

// Run as a program. Skills are symlinked into place, so compare real paths; and if the
// runtime was told to keep symlinks, the file's own name still says it was run directly.
const isMain = (() => {
  try {
    const argv1 = process.argv[1];
    if (!argv1) return false;
    return import.meta.url === pathToFileURL(realpathSync(argv1)).href
      || path.basename(argv1) === 'cloudflare-check.mjs';
  } catch {
    return false;
  }
})();
if (isMain) {
  if (Number(process.versions.node.split('.')[0]) < 18) {
    process.stderr.write(`cloudflare-check needs Node 18 or newer; this is Node ${process.versions.node}.\n`);
    process.exit(2);
  }
  const r = await main(process.argv.slice(2));
  process.stdout.write(r.stdout);
  process.stderr.write(r.stderr);
  process.exitCode = r.code;
}
