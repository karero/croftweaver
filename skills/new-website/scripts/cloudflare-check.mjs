#!/usr/bin/env node
// cloudflare-check.mjs: look at a live site from outside and say, item by item, how the
// Cloudflare checklist (docs/CLOUDFLARE-CHECKLIST.md) comes out.
//
//   node cloudflare-check.mjs example.com [--project my-pages-project] [--hsts-on]
//                                          [--build <sha>] [--json] [--timeout <seconds>]
//
// Read-only. It sends GET requests and nothing else: no token, no account, no change. It
// needs Node 18 or newer and nothing from npm. What it prints, and what it cannot see, is
// in references/CLOUDFLARE_CHECK.md next to this folder.
import http from 'node:http';
import https from 'node:https';
import { realpathSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const UA = 'Mozilla/5.0 (compatible; croftweaver-cloudflare-check/1)';
const MONTH = 2629800; // seconds in an average month; the dashboard offers whole months
const CF_COOKIE = /^(__cf_bm|cf_clearance|__cflb|_cfuvid)$/; // the names Cloudflare's own cookies carry

// Crawler names the AI-crawler item sends. A spoofed name is not the real crawler, so a 200
// here is consistent with "Allow" and a refusal shows that some block is on.
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
  5: 'The files the checks rely on',
};
export const ITEMS = [
  { id: 'pages', section: 1, title: 'Create a Pages project, not a Worker' },
  { id: 'build-settings', section: 1, title: 'Build settings',
    path: 'your project → Settings → Builds & deployments',
    lookFor: 'framework preset Astro, build command npm run build, output directory dist; on a two-stage site the Production branch is production' },
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
  { id: 'ai', section: 4, title: 'AI crawlers: allow' },
  { id: 'robots', section: 5, title: 'Your own robots.txt' },
  { id: 'build', section: 5, title: 'The build that is live' },
];

// ---------------------------------------------------------------- what was asked for

const USAGE = `Usage: node cloudflare-check.mjs <domain> [options]

  <domain>            your live domain, for example example.com (no https://, no path)
  --project <name>    your Pages project, to check that <name>.pages.dev forwards to the domain
  --hsts-on           you have switched HSTS on: a missing header is then a failure
  --build <sha>       the build you expect the live domain to serve (from /build.txt)
  --json              print the results as JSON
  --timeout <s>       seconds to wait for each answer (default 15)
  -h, --help          this text

Exit status: 0 nothing failed, 1 something failed or did not answer, 2 the command was wrong.
`;

export function parseArgs(argv) {
  const opts = { json: false, hstsOn: false, timeoutMs: 15000, project: null, build: null, help: false };
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
    else if (a === '--timeout') {
      const n = Number(value());
      if (!(n >= 1 && n <= 120)) throw new UsageError('--timeout takes a number of seconds from 1 to 120');
      opts.timeoutMs = n * 1000;
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

// A bare domain means https://<domain>. An origin ("http://127.0.0.1:4321") is taken as given,
// which is how a local preview, or the script's own tests, are checked.
export function parseTarget(arg) {
  const raw = String(arg).trim();
  let url;
  try {
    url = new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(raw) ? raw : `https://${raw}`);
  } catch {
    throw new UsageError(`"${raw}" is not a domain`);
  }
  if (url.protocol !== 'https:' && url.protocol !== 'http:') throw new UsageError(`"${raw}" is not a web address`);
  if (url.username || url.password || url.search || url.hash || url.pathname !== '/') {
    throw new UsageError(`give the domain only, with no path: "${url.hostname}", not "${raw}"`);
  }
  return {
    host: url.host,
    origin: url.origin,
    httpProbe: `http://${url.protocol === 'http:' ? url.host : url.hostname}/`,
    httpsPrefix: `https://${url.host}/`,
  };
}

function parseProject(arg) {
  const raw = arg.trim();
  if (/^https?:\/\//i.test(raw)) {
    try {
      const u = new URL(raw);
      return { origin: u.origin, host: u.host };
    } catch {
      throw new UsageError(`"${raw}" is not a web address`);
    }
  }
  const name = raw.replace(/\.pages\.dev$/i, '');
  if (!/^[a-z0-9][a-z0-9-]{0,57}$/i.test(name)) {
    throw new UsageError(`"${raw}" is not a Pages project name (letters, digits and hyphens)`);
  }
  return { origin: `https://${name}.pages.dev`, host: `${name}.pages.dev` };
}

// ---------------------------------------------------------------- asking

// One GET, never followed, never rejected: an error is part of the answer. The body is
// read up to a megabyte.
function get(url, { timeoutMs, ua = UA, accept = 'text/html,application/xhtml+xml,*/*;q=0.8' }) {
  return new Promise((resolve) => {
    const signal = AbortSignal.timeout(timeoutMs);
    const finish = (extra) => resolve({ url, ...extra });
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
      headers: { 'user-agent': ua, accept, 'accept-encoding': 'identity' },
    }, (res) => {
      const chunks = [];
      let size = 0;
      res.on('data', (c) => {
        size += c.length;
        if (size <= 1_000_000) chunks.push(c);
        else res.destroy();
      });
      res.on('error', () => {});
      res.on('close', () => finish({
        status: res.statusCode,
        headers: res.headers,
        body: Buffer.concat(chunks).toString('utf8'),
      }));
    });
    req.on('error', (e) => finish({
      error: { code: signal.aborted ? 'ETIMEDOUT' : (e.code || e.name), message: e.message },
    }));
    req.end();
  });
}

export async function observe(target, { timeoutMs, alias }) {
  const stamp = Math.floor(Date.now() / 1000);
  const t = { timeoutMs };
  const text = { timeoutMs, accept: 'text/plain,*/*;q=0.8' };
  const homeUrl = `${target.origin}/?cb=${stamp}`;
  const [home, robots, httpProbe, build, aliasHome, ...crawlers] = await Promise.all([
    get(homeUrl, t),
    get(`${target.origin}/robots.txt`, text),
    get(target.httpProbe, t),
    get(`${target.origin}/build.txt?cb=${stamp}`, text),
    alias ? get(`${alias.origin}/?cb=${stamp}`, t) : Promise.resolve(null),
    ...CRAWLERS.map(([, ua]) => get(homeUrl, { timeoutMs, ua })),
  ]);
  return {
    stamp, home, robots, httpProbe, build, alias: aliasHome,
    crawlers: crawlers.map((r, i) => ({ name: CRAWLERS[i][0], ...r })),
  };
}

// ---------------------------------------------------------------- judging

const header = (r, name) => {
  const v = r.headers?.[name];
  return Array.isArray(v) ? v.join(', ') : (v ?? '');
};
const bare = (url) => url.replace(/\?cb=\d+$/, '');

function whyNoAnswer(err, timeoutMs) {
  const known = {
    ENOTFOUND: 'the name does not exist',
    EAI_AGAIN: 'the name could not be looked up',
    ECONNREFUSED: 'the connection was refused',
    ECONNRESET: 'the connection was reset',
    ETIMEDOUT: `no answer within ${timeoutMs / 1000} seconds`,
    CERT_HAS_EXPIRED: 'its certificate has expired',
    ERR_TLS_CERT_ALTNAME_INVALID: 'its certificate is for another name',
    DEPTH_ZERO_SELF_SIGNED_CERT: 'its certificate cannot be trusted',
    SELF_SIGNED_CERT_IN_CHAIN: 'its certificate cannot be trusted',
    UNABLE_TO_VERIFY_LEAF_SIGNATURE: 'its certificate cannot be trusted',
  };
  return known[err.code] ?? err.message;
}

export function evaluate(obs, target, opts) {
  const out = new Map();
  const put = (id, state, detail, fix) => out.set(id, fix ? { state, detail, fix } : { state, detail });
  const { home, robots, httpProbe, build, alias, crawlers } = obs;
  const noAnswer = (r) => `no answer from ${bare(r.url)}: ${whyNoAnswer(r.error, opts.timeoutMs)}`;
  const section = (n) => `See section ${n} of the Cloudflare checklist.`;

  // 1. The domain answers. Everything about the home page hangs on this one.
  const challenged = !home.error && header(home, 'cf-mitigated') === 'challenge';
  const seen = !home.error && !challenged && home.status < 400; // headers of the home page can be judged
  const page = seen && home.status === 200 && /html/i.test(header(home, 'content-type'));
  const whyNot = home.error ? noAnswer(home)
    : challenged ? `Cloudflare answered ${home.status} with a challenge page, so the site itself was not seen`
      : `the home page answered ${home.status}`;
  const notChecked = `not checked: ${whyNot}`;
  const cloudflareError = { 522: 'Cloudflare cannot reach your Pages project: the domain is probably not attached to it',
    523: 'Cloudflare cannot reach the origin', 525: 'the secure connection to the origin failed',
    526: 'the origin certificate is not valid' };

  if (home.error) put('domain', 'fail', noAnswer(home), `Is the domain attached to the project, and are its DNS records on Cloudflare? ${section(1)}`);
  else if (challenged) put('domain', 'fail', `Cloudflare answered ${home.status} with a challenge page, so the site itself was not seen. Bot Fight Mode, or a rule, is challenging requests like this one.`, section(3));
  else if (home.status >= 400) put('domain', 'fail', `${bare(home.url)} answered ${home.status}${cloudflareError[home.status] ? `: ${cloudflareError[home.status]}` : ''}.`, section(1));
  else if (home.status >= 300) put('domain', 'look', `${bare(home.url)} answered ${home.status} and sends visitors to ${header(home, 'location') || 'another address'}. Something redirects your live domain (a language or www redirect is fine): find out what before you trust the rest.`);
  else put('domain', 'ok', `${bare(home.url)} answered ${home.status}.`);

  // 2. http:// goes to https://
  if (httpProbe.error) put('https', 'fail', noAnswer(httpProbe), section(2));
  else {
    const loc = header(httpProbe, 'location');
    const to = loc.toLowerCase().startsWith(target.httpsPrefix.toLowerCase());
    const s = httpProbe.status;
    if ((s === 301 || s === 308) && to) put('https', 'ok', `http:// answers ${s} and sends visitors to ${loc}.`);
    else if (s >= 300 && s < 400 && to) put('https', 'look', `http:// answers ${s}, a temporary redirect, to ${loc}. Visitors arrive on https, but Always Use HTTPS sends a 301.`);
    else if (s >= 300 && s < 400) put('https', 'fail', `http:// sends visitors to ${loc || 'another address'}, not to ${target.httpsPrefix}`, section(2));
    else put('https', 'fail', `http:// answers ${s} with no redirect: Always Use HTTPS is off, or does not reach this address.`, section(2));
  }

  // 3. HSTS
  if (!seen) put('hsts', 'skip', notChecked);
  else {
    const sts = header(home, 'strict-transport-security');
    if (!sts) {
      if (opts.hstsOn) put('hsts', 'fail', 'you said HSTS is on, but the home page has no strict-transport-security header.', section(2));
      else put('hsts', 'look', 'not on yet. Switch it on a few days after go-live, then run this check again with --hsts-on.');
    } else {
      const age = Number((/max-age=(\d+)/i.exec(sts) ?? [])[1] ?? NaN);
      const sub = /includesubdomains/i.test(sts);
      const pre = /preload/i.test(sts);
      const months = Math.round(age / MONTH);
      const shown = `on: max-age ${age} (about ${months} month${months === 1 ? '' : 's'}), subdomains ${sub ? 'on' : 'off'}, preload ${pre ? 'on' : 'off'}.`;
      if (!(age > 0)) put('hsts', 'look', `${sts}: a max-age of 0, or none, switches HSTS off in browsers.`, section(2));
      else if (pre) put('hsts', 'look', `${shown} The checklist says preload Off: it needs 12 months and can lock visitors out if HTTPS ever breaks.`, section(2));
      else put('hsts', 'ok', shown);
    }
  }

  // 4. NEL
  if (!seen) put('nel', 'skip', notChecked);
  else {
    const nel = header(home, 'nel');
    const rt = header(home, 'report-to');
    let age = '';
    try { age = ` (max_age ${JSON.parse(nel).max_age} seconds)`; } catch { /* not JSON: say nothing */ }
    const aliasNel = alias && !alias.error && (header(alias, 'nel') || header(alias, 'report-to'))
      ? ' The pages.dev address still sends them; the header rule cannot reach it, and no way to remove them there has been found.' : '';
    if (nel) put('nel', 'fail', `the home page sends a nel header${age}: Network Error Logging is on.`, `Switch it off and, if the header stays, add the header rule. ${section(3)}`);
    else if (rt) put('nel', 'look', `no nel header, but a report-to header is sent. If it is Cloudflare's reporting group, remove it with the header rule; if your site sets its own reporting groups, leave it.${aliasNel}`, section(3));
    else put('nel', 'ok', `no nel and no report-to header on the home page.${aliasNel}`);
  }

  // 5. What Cloudflare adds to the page: cookies and scripts.
  const html = page ? home.body.toLowerCase() : null;
  const cookies = seen ? [].concat(home.headers['set-cookie'] ?? []).map((c) => c.split('=')[0].trim()) : [];
  const unseenPage = !seen ? notChecked : 'not checked: the home page did not answer 200 with HTML, so its source was not read';
  if (cookies.length) {
    const cf = cookies.filter((c) => CF_COOKIE.test(c));
    put('bot', 'fail', `the home page sets ${cookies.length === 1 ? 'a cookie' : 'cookies'}: ${cookies.join(', ')}${cf.length ? ' (Cloudflare\'s bot cookie)' : ''}.`, section(3));
  } else if (html?.includes('cdn-cgi/challenge-platform')) {
    put('bot', 'fail', 'the HTML loads Cloudflare\'s bot-detection script (/cdn-cgi/challenge-platform/).', section(3));
  } else if (html) {
    put('bot', 'ok', 'no cookie and no bot-detection script in the page we received. A browser can see more: view the source once.');
  } else put('bot', 'skip', unseenPage);

  if (html?.includes('cloudflareinsights')) put('analytics', 'fail', 'the HTML loads Cloudflare\'s measurement script (cloudflareinsights).', section(3));
  else if (html) put('analytics', 'ok', 'no cloudflareinsights script in the page we received.');
  else put('analytics', 'skip', unseenPage);

  if (html && /email-decode|cdn-cgi\/l\/email-protection|data-cfemail|\[email(&#160;|&nbsp;| )protected\]/.test(html)) {
    put('email', 'fail', 'the HTML carries Cloudflare\'s address hiding (email-decode or [email protected]).', section(3));
  } else if (html) put('email', 'ok', 'no email-decode script and no [email protected] in the page we received.');
  else put('email', 'skip', unseenPage);

  // 6. robots.txt, and what the AI crawlers get.
  let agents = [];
  let robotsFile = null; // 'ok' | 'look' | 'fail' with detail, computed below
  // A dead domain is one failure, said once above; robots.txt then is not checked, not a second failure.
  if (robots.error) robotsFile = home.error ? ['skip', notChecked] : ['fail', noAnswer(robots)];
  else if (robots.status === 404) robotsFile = ['look', 'no robots.txt (404). The starter ships one; without it search engines crawl everything.'];
  else if (robots.status !== 200) robotsFile = ['fail', `robots.txt answered ${robots.status}.`];
  else if (/<html|<!doctype/i.test(robots.body)) robotsFile = ['fail', 'robots.txt answers with a web page, not a robots file.'];
  else {
    const lines = robots.body.split(/\r?\n/).map((l) => l.replace(/#.*/, '').trim()).filter(Boolean);
    const field = (name) => lines.filter((l) => l.toLowerCase().startsWith(`${name}:`)).map((l) => l.slice(name.length + 1).trim());
    agents = field('user-agent').filter((a) => a !== '*');
    const sitemaps = field('sitemap');
    const signals = field('content-signal').length > 0;
    const hostOf = (u) => { try { return new URL(u).host; } catch { return ''; } };
    if (!field('user-agent').includes('*')) robotsFile = ['look', 'no "User-agent: *" group: is this your own file?'];
    else if (sitemaps.some((s) => /example\.(com|org|net)/i.test(s))) robotsFile = ['fail', `the Sitemap line still names the starter's placeholder (${sitemaps.find((s) => /example\./i.test(s))}). Set your real domain.`];
    else if (!sitemaps.length) robotsFile = ['look', 'no Sitemap line.'];
    else if (!sitemaps.some((s) => hostOf(s).replace(/^www\./, '') === target.host.replace(/^www\./, ''))) robotsFile = ['look', `the Sitemap line names ${hostOf(sitemaps[0]) || sitemaps[0]}, not ${target.host}.`];
    else robotsFile = ['ok', `a robots file with a Sitemap line that names ${target.host}.`];
    if (signals) agents.push('(content-signal lines)');
  }
  put('robots', robotsFile[0], robotsFile[1], robotsFile[0] === 'ok' ? undefined : 'The starter\'s robots.txt, with your own domain in the Sitemap line.');

  const refused = seen ? crawlers.filter((c) => !c.error && c.status >= 400).map((c) => `${c.name} (${c.status})`) : [];
  const failed = crawlers.filter((c) => c.error).length;
  const dashboard = 'The setting itself is in the dashboard (Security → Settings → Configure AI bot policies) and cannot be read from outside.';
  if (!seen) put('ai', 'skip', notChecked);
  else if (refused.length) put('ai', 'look', `these crawler names were refused: ${refused.join(', ')}. If you chose to block Training that is expected; otherwise set Search, Agent and Training to Allow.`, section(4));
  else if (failed === crawlers.length) put('ai', 'skip', 'not checked: no crawler request got an answer.');
  else if (agents.length) put('ai', 'look', `no crawler name was refused, but robots.txt has rules for ${agents.join(', ')}. Confirm you wrote them or chose them in Cloudflare.`, section(4));
  else put('ai', 'ok', `none of ${crawlers.length} AI crawler names was refused, and robots.txt names no crawler. ${dashboard}`);

  // 7. build.txt: which build is live.
  if (build.error && home.error) put('build', 'skip', notChecked);
  else if (build.error) put('build', 'look', `could not read build.txt: ${whyNoAnswer(build.error, opts.timeoutMs)}.`);
  else if (build.status !== 200) put('build', 'look', `no build.txt (${build.status}). Sites made with the kit write one at build time, so a pass here says nothing about which build is live.`);
  else {
    const sha = build.body.trim();
    if (sha === 'dev') put('build', 'look', 'build.txt says "dev": that build was not made by Cloudflare or from a git checkout.');
    else if (!/^[0-9a-f]{7,40}$/i.test(sha)) put('build', 'look', 'build.txt is not a build marker (the answer is not a commit id).');
    else if (!opts.build) put('build', 'ok', `serves build ${sha.slice(0, 12)}. Pass --build <sha> to compare it with the one you expect.`);
    else {
      const a = sha.toLowerCase();
      const b = opts.build.toLowerCase();
      if (a.startsWith(b) || b.startsWith(a)) put('build', 'ok', `serves build ${sha.slice(0, 12)}, the one you expected.`);
      else put('build', 'fail', `serves build ${sha.slice(0, 12)}, but you expected ${b.slice(0, 12)}: the live domain is on another build. Wait for the deploy, or look at Deployments.`);
    }
  }

  // 8. The pages.dev address (only when --project is given).
  if (!alias) {
    put('pages', 'skip', 'not checked: give --project <name> to check that <name>.pages.dev answers (a Worker answers on workers.dev).');
    put('canonical', 'skip', 'not checked: give --project <name> to check that <name>.pages.dev forwards to your domain.');
  } else if (alias.error) {
    const missing = alias.error.code === 'ENOTFOUND';
    put('pages', 'fail', `${noAnswer(alias)}${missing ? '. Check the project name: a Worker would answer on a workers.dev address, not pages.dev.' : ''}`, section(1));
    put('canonical', 'skip', 'not checked: the pages.dev address did not answer.');
  } else {
    put('pages', 'ok', `${bare(alias.url)} answers ${alias.status}: this is a Pages project.`);
    const loc = header(alias, 'location');
    const to = loc.toLowerCase().startsWith(target.httpsPrefix.toLowerCase());
    if (alias.status === 301 && to) put('canonical', 'ok', `answers 301 and sends visitors to ${loc}.`);
    else if (alias.status >= 300 && alias.status < 400 && to) put('canonical', 'look', `answers ${alias.status}, not 301, to ${loc}.`, section(1));
    else if (alias.status >= 300 && alias.status < 400) put('canonical', 'fail', `sends visitors to ${loc || 'another address'}, not to ${target.httpsPrefix}`, section(1));
    else if (alias.status === 200) put('canonical', 'fail', 'answers 200: CANONICAL_URL is not under Production, is misnamed or malformed, the deployment is older than the variable, or the day\'s Functions allowance ran out with Fail open on.', section(1));
    else put('canonical', 'fail', `answers ${alias.status}.`, section(1));
  }

  // The items nothing from outside can see.
  for (const item of ITEMS.filter((i) => i.path)) {
    const where = item.path.startsWith('your project') ? `Workers & Pages → ${item.path}` : item.path;
    put(item.id, 'hand', `${where}: ${item.lookFor}.`);
  }

  return ITEMS.map((item) => {
    const r = out.get(item.id);
    if (!r) throw new Error(`cloudflare-check: no result for "${item.id}"`);
    return { id: item.id, section: item.section, title: item.title, ...r };
  });
}

// ---------------------------------------------------------------- saying it

const WORD = { ok: 'ok', fail: 'FAIL', look: 'look', hand: 'by hand', skip: 'not run' };

export function summarize(results) {
  const n = { ok: 0, fail: 0, look: 0, hand: 0, skip: 0 };
  for (const r of results) n[r.state]++;
  return n;
}

export function render(results, target, when) {
  const lines = [`Cloudflare check for ${target.host}`, `Looked from outside with plain GET requests, ${when}. Nothing was changed.`];
  let section = 0;
  for (const r of results) {
    if (r.section !== section) {
      section = r.section;
      lines.push('', `${section} · ${SECTIONS[section]}`);
    }
    lines.push(`  ${WORD[r.state].padEnd(8)} ${r.title.replace(/`/g, '')}`);
    lines.push(`           ${r.detail}`);
    if (r.fix && (r.state === 'fail' || r.state === 'look')) lines.push(`           → ${r.fix}`);
  }
  const n = summarize(results);
  lines.push('', `Result: ${n.ok} ok, ${n.fail} FAIL, ${n.look} look, ${n.hand} by hand, ${n.skip} not run.`);
  if (n.fail) lines.push('FAIL means the checklist is not met and it is worth fixing first. The checklist says how.');
  if (n.look) lines.push('"look" means the answer is not wrong on its face but needs a person to say whether it is what you meant.');
  if (n.hand) lines.push('"by hand" items have no outside check: open the dashboard path shown.');
  return `${lines.join('\n')}\n`;
}

export async function main(argv, now = () => new Date()) {
  let parsed;
  try {
    parsed = parseArgs(argv);
  } catch (e) {
    if (!(e instanceof UsageError)) throw e;
    return { code: 2, stdout: '', stderr: `cloudflare-check: ${e.message}\n\n${USAGE}` };
  }
  if (parsed.opts.help) return { code: 0, stdout: USAGE, stderr: '' };
  let target;
  let alias = null;
  try {
    target = parseTarget(parsed.domain);
    if (parsed.opts.project) alias = parseProject(parsed.opts.project);
  } catch (e) {
    if (!(e instanceof UsageError)) throw e;
    return { code: 2, stdout: '', stderr: `cloudflare-check: ${e.message}\n\n${USAGE}` };
  }
  const obs = await observe(target, { timeoutMs: parsed.opts.timeoutMs, alias });
  const results = evaluate(obs, target, parsed.opts);
  const n = summarize(results);
  const code = n.fail ? 1 : 0;
  const when = now().toISOString().replace(/\.\d+Z$/, 'Z');
  if (parsed.opts.json) {
    return { code, stderr: '', stdout: `${JSON.stringify({ domain: target.host, checkedAt: when, summary: n, results }, null, 2)}\n` };
  }
  return { code, stderr: '', stdout: render(results, target, when) };
}

// Run as a program. Skills are symlinked into place, so compare real paths.
const isMain = (() => {
  try {
    return process.argv[1] && import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href;
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
