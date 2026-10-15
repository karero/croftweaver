// How the fixtures in this folder are made: from the captures of the two trials of the Cloudflare
// setup script (docs/reviews/SKILL-PLAN-cloudflare-setup.md, "What is known, and how"), which hold
// real names and ids and stay outside every repository. Not a test (never run by `node --test`).
//
//   node clean-captures.mjs <trial-1 captures> <trial-2 captures> <private map.json> <out folder>
//
// The private map gives each real name its made-up one, per trial ("T1", "T2", "both"); it is
// kept beside the captures. Everything else is replaced by rule, the same way every time: ids,
// commit hashes, the numeric GitHub ids, commit messages; email fields and the registrar's
// nameservers are left out. The fixture test (cloudflare-setup.test.mjs) then checks every id,
// address, host name, account name and commit message in the output against the made-up ones,
// so a value this file misses fails there.
import { readFileSync, readdirSync, writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';

// The captures committed, by trial and number, in two batches: those the setup stage's tests use,
// then those the launch stage's add (attaching a domain, its statuses, the host's record and its
// comment). Made-up ids are given batch by batch, so a later batch leaves the earlier files as they
// were. `excerpt` keeps part of a long list.
const SELECTION = [
  {
    T1: ['001', '002', '003', '013', '014', '015', '018', '019', '021', '027', '028', '030', '031', '033', '040',
      '048', '049', '050', '051', '052', '053', '054', '055', '061', '062', '063', '064',
      '067', '068', '069', '070', '071', '072', '073', '074', '075', '076', '077', '078', '079', '080', '081',
      '082', '083', '084', '143', '144', '145', '146', '148'],
    T2: ['001', '002', '003', '011', '016', '018', '021', '022', '023', '024', '025', '026', '028', '029',
      '035', '036', '037', '038', '039', '040', '041', '059', '060', '061', '062', '063', '064', '065', '066',
      '067', '073', '077'],
  },
  {
    // T1-102, the zone's list of records, is left out: it is the live zone's mail and other records.
    T1: ['085', '086', '104', '127', '129', '130', '131', '132', '141', '142'],
    T2: ['042', '043', '044', '045', '046', '047', '055', '056', '057', '058'],
  },
];
const DROP = new Set(['owner', 'email', 'original_dnshost', 'original_name_servers', 'original_registrar',
  'vanity_name_servers', 'vanity_name_servers_ips', 'tenant', 'tenant_unit']);

function main([t1, t2, mapFile, out]) {
  if (!out) throw new Error('usage: node clean-captures.mjs <trial-1 captures> <trial-2 captures> <private map.json> <out folder>');
  const map = JSON.parse(readFileSync(mapFile, 'utf8'));
  const dirs = { T1: t1, T2: t2 };
  // The trial's own helper, which made every request: kept beside the captures, committed with its
  // two local paths replaced. The deployment call's empty form is read from it, not written here.
  // Its first line is made a comment, so the repository's checks do not take the record for a script.
  const helper = readFileSync(path.join(t1, '..', 'cf.sh'), 'utf8')
    .replace(/^#!/, '# This is a record, never run. It began: #!')
    .replace(/dir="[^"]*"/, 'dir="<the trial\'s captures folder>"')
    .replace(/"\$HOME\/Devel\/[^"]*\/\.dev\.vars"/, '"<the throwaway repository>/.dev.vars"');
  const formLine = /-H 'Content-Type: (multipart\/form-data; boundary=[^']+)' --data-binary \$'([^']*)'/.exec(helper);
  if (!formLine) throw new Error('the helper has no empty-form line');
  const emptyForm = { contentType: formLine[1], bytes: formLine[2].replace(/\\r\\n/g, '\r\n') };
  const raw = [];
  for (const [batch, selection] of SELECTION.entries()) for (const trial of ['T1', 'T2']) {
    const files = readdirSync(dirs[trial]);
    for (const n of selection[trial]) {
      const base = files.find((f) => f.startsWith(`${n}-`) && f.endsWith('.request.txt')).replace(/\.request\.txt$/, '');
      const at = (ext) => path.join(dirs[trial], `${base}.${ext}`);
      const [line, ...bodyLines] = readFileSync(at('request.txt'), 'utf8').split('\n');
      const [method, p] = line.split(' ');
      const bodyText = bodyLines.join('\n').trim();
      let body = null;
      if (bodyText === '@form') {
        // The helper wrote "@form" for the deployment call and sent an empty multipart form: its
        // closing boundary alone (trial-helper.txt, the "@form" branch).
        body = { emptyForm };
      } else if (bodyText) { try { body = JSON.parse(bodyText); } catch { body = bodyText; } }
      const text = readFileSync(at('response.json'), 'utf8');
      raw.push({
        trial, n, batch, label: base.slice(4),
        capture: `${trial}-${n}`,
        request: { method, path: p, body },
        status: Number(readFileSync(at('status.txt'), 'utf8').trim()),
        response: text.trim() ? JSON.parse(text) : null,
      });
    }
  }

  // The account's list of projects (T1-019): each item as Cloudflare listed it, with its source,
  // domains and settings; its latest and canonical deployments, which hold another site's history,
  // are set to null.
  const list = raw.find((r) => r.capture === 'T1-019');
  for (const item of list.response.result) { item.latest_deployment = null; item.canonical_deployment = null; }
  list.excerpt = 'every project as listed, with latest_deployment and canonical_deployment set to null';

  // The live project's deployment list (T1-021 to T1-026, six pages) is long and holds its real
  // history: keep every ad_hoc deployment (uploads and builds) and the newest push build of each
  // environment, the shapes the classification reads, as one page.
  const live = raw.find((r) => r.capture === 'T1-021');
  const pages = ['022', '023', '024', '025', '026'].map((n) => {
    const f = readdirSync(t1).find((x) => x.startsWith(`${n}-`) && x.endsWith('.response.json'));
    return JSON.parse(readFileSync(path.join(t1, f), 'utf8')).result;
  });
  const every = [live.response.result, ...pages].flat();
  const keep = every.filter((d) => d.deployment_trigger.type === 'ad_hoc');
  for (const env of ['production', 'preview']) keep.push(every.find((d) => d.deployment_trigger.type === 'github:push' && d.environment === env));
  live.response.result = keep;
  live.response.result_info = { ...live.response.result_info, count: keep.length };
  const idle = (d, name) => d.stages.find((s) => s.name === name).status === 'idle';
  const uploads = keep.filter((d) => d.deployment_trigger.type === 'ad_hoc' && idle(d, 'clone_repo') && idle(d, 'build')).length;
  live.excerpt = `every ad_hoc deployment (${uploads} uploads, with clone_repo and build idle, and ${keep.length - 2 - uploads} built by Cloudflare) and the newest push build of each environment, of ${every.length} deployments on the six pages T1-021 to T1-026`;
  keep.filter((d) => d.environment === 'preview').forEach((d, i) => {
    const slug = (b) => b.replace(/[^a-z0-9]+/gi, '-').toLowerCase();
    const from = d.deployment_trigger.metadata.branch;
    const to = `lenas-pr-${i + 1}`;
    if (from !== 'main') {
      d.aliases = (d.aliases ?? []).map((a) => a.replace(`//${slug(from).slice(0, 28)}.`, `//${to}.`));
      d.deployment_trigger.metadata.branch = to;
    }
  });

  // Ids: one made-up value per real one, the same in every file. A made-up id is mostly zeros, so
  // no real id can look like one.
  const ids = new Map();
  const fake = (real, make) => { if (!ids.has(real)) ids.set(real, make(ids.size + 1)); return ids.get(real); };
  const pad = (n, width) => String(n).padStart(width, '0');
  const uuidsOf = (o) => JSON.stringify(o).match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g) ?? [];
  // A batch's uuids are given out, sorted, just before the batch is cleaned (below).
  const shortIds = new Map();
  const giveUuids = (batch) => {
    for (const u of [...new Set(uuidsOf(raw.filter((r) => r.batch === batch)))].sort()) {
      fake(u, (k) => `d${pad(k, 7)}-0000-4000-8000-000000000000`);
      shortIds.set(u.slice(0, 8), ids.get(u).slice(0, 8));
    }
  };
  const messages = new Map();
  const numbers = new Map();

  const names = (trial) => Object.entries({ ...map.both, ...map[trial] }).sort((a, b) => b[0].length - a[0].length);
  const cleanString = (s, trial) => {
    let v = s;
    for (const [real, madeUp] of names(trial)) v = v.split(real).join(madeUp).replace(new RegExp(real.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), madeUp);
    v = v.replace(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g, (u) => ids.get(u));
    // A run of hexadecimal digits is an id wherever it stands, beside an underscore or a letter too.
    v = v.replace(/(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])/g, (h) => fake(h, (k) => `f00d${pad(k, 60)}`));
    v = v.replace(/(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])/g, (h) => fake(h, (k) => `ba5e${pad(k, 36)}`));
    v = v.replace(/(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])/g, (h) => fake(h, (k) => `c0ffee${pad(k, 26)}`));
    v = v.replace(/\b[0-9a-f]{8}\b/g, (h) => shortIds.get(h) ?? h);
    v = v.replace(/pages-worker--\d+/g, 'pages-worker--1000001');
    return v;
  };
  const clean = (o, trial, key = '') => {
    if (typeof o === 'string') {
      if (key === 'commit_message') {
        if (!messages.has(o)) messages.set(o, `Made-up commit message ${messages.size + 1}`);
        return messages.get(o);
      }
      if (key === 'owner_id' || key === 'repo_id') {
        if (!numbers.has(o)) numbers.set(o, String(1000000 + numbers.size + 1));
        return numbers.get(o);
      }
      return cleanString(o, trial);
    }
    if (Array.isArray(o)) return o.map((x) => clean(x, trial, key));
    if (o && typeof o === 'object') {
      // A zone's `owner` is a record with an email in it; a source's `owner` is the GitHub owner, kept.
      return Object.fromEntries(Object.entries(o).filter(([k, v]) => !DROP.has(k) || (k === 'owner' && typeof v === 'string'))
        .map(([k, v]) => [k, clean(v, trial, k)]));
    }
    return o;
  };

  // The helper and the file names get the same check as the fixtures: no name from the map, no id.
  // Ids are found by their run of hexadecimal digits, so one beside an underscore or a letter counts.
  const real = (text, trial) => names(trial).some(([n]) => text.toLowerCase().includes(n.toLowerCase())) || /(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])/i.test(text);
  if (real(helper, 'T1') || real(helper, 'T2')) throw new Error('trial-helper.txt: a real name or id is still there');
  mkdirSync(out, { recursive: true });
  writeFileSync(path.join(out, 'trial-helper.txt'), helper);
  for (const r of raw) {
    if (r === raw.find((x) => x.batch === r.batch)) giveUuids(r.batch);
    const fixture = {
      capture: r.capture,
      ...(r.excerpt ? { excerpt: r.excerpt } : {}),
      request: { method: r.request.method, path: cleanString(r.request.path, r.trial), body: clean(r.request.body, r.trial) },
      status: r.status,
      response: clean(r.response, r.trial),
    };
    const text = `${JSON.stringify(fixture, null, 2)}\n`;
    // Nothing real may be left: no name from the map, no id that was not replaced.
    for (const [real] of names(r.trial)) if (text.toLowerCase().includes(real.toLowerCase())) throw new Error(`${r.capture}: "${real}" is still there`);
    for (const real of ids.keys()) if (text.includes(real)) throw new Error(`${r.capture}: an id is still there`);
    // And no id the replacement did not know: a hex run of 32 or more that is not a made-up one.
    for (const m of text.matchAll(/(?<![0-9a-f])[0-9a-f]{32,}(?![0-9a-f])/gi)) {
      if (!/^(?:c0ffee|ba5e|f00d)0+\d+$/.test(m[0])) throw new Error(`${r.capture}: an id the cleaner did not replace`);
    }
    const file = `${r.capture}-${r.label.replace(/^wc-/, '').replace(/croftweaver/g, 'live-project')}.json`;
    if (real(file, r.trial)) throw new Error(`${file}: a real name in the file name`);
    writeFileSync(path.join(out, file), text);
  }
}

main(process.argv.slice(2));
