// Tests for create-croftweaver. Every case runs the installer the way `npm create` does, as
// a process of its own, against a stub of GitHub's release download on 127.0.0.1: the
// "latest" address redirects to one that names the release, as GitHub's does. No real
// requests. Why each case matters is in its name: an installer writes into the folder an
// assistant takes its instructions from, so what it leaves alone counts as much as what it
// copies.
import assert from 'node:assert/strict';
import { execFile, execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { after, before, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { makeZip } from './zip.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const INSTALLER = path.join(HERE, '..', 'index.mjs');
const REPO = path.join(HERE, '..', '..', '..');
const POSIX = process.platform !== 'win32';

// What the stub serves next. Tests in one file run one after another, so one slot is enough.
// `sums` is the release's SHA256SUMS: left out, the right line for the zip, as a release
// carries it; null, no such file (404); a number, that status; a string, served as it is.
let served = { status: 200, release: 'v9.1', zip: Buffer.alloc(0) };
const sha256 = (data) => crypto.createHash('sha256').update(data).digest('hex');
const asked = [];   // every path the stub was asked for, in order
const server = http.createServer((req, res) => {
  asked.push(req.url);
  if (req.url === '/latest/download/croftweaver.zip') {
    res.writeHead(302, { location: `/download/${served.release}/croftweaver.zip` }).end();
  } else if (req.url.endsWith('/SHA256SUMS')) {
    const { sums = `${sha256(served.zip)}  croftweaver.zip\n` } = served;
    if (sums === null) res.writeHead(404).end('not here');
    else if (typeof sums === 'number') res.writeHead(sums).end('no');
    else res.writeHead(200).end(sums);
  } else {
    res.writeHead(served.status).end(served.status === 200 ? served.zip : 'not here');
  }
});
let latest;
const scratch = [];
before(async () => {
  await new Promise((done) => server.listen(0, '127.0.0.1', done));
  latest = `http://127.0.0.1:${server.address().port}/latest/download/croftweaver.zip`;
});
after(() => {
  server.close();
  for (const dir of scratch) fs.rmSync(dir, { recursive: true, force: true });
});

function tmp() {
  // The real path: the installer names the backup folder by it, and the temp folder is
  // reached through a link on macOS and by a short name on Windows runners.
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'create-croftweaver-test-')));
  scratch.push(dir);
  return dir;
}

// Runs the installer with `home` as the home folder, and without the developer's own overrides.
function run(home, args = [], env = {}) {
  const base = { ...process.env };
  delete base.CLAUDE_SKILLS_DIR;
  delete base.CODEX_SKILLS_DIR;
  return new Promise((resolve) => {
    execFile(process.execPath, [INSTALLER, ...args],
      { env: { ...base, HOME: home, USERPROFILE: home, CROFTWEAVER_ZIP_URL: latest, ...env } },
      (error, stdout, stderr) => resolve({ code: error ? error.code : 0, stdout, stderr }));
  });
}


// Every file under `dir` as { 'a/b.md': text }. Links are not followed.
function tree(dir) {
  const files = {};
  for (const entry of fs.readdirSync(dir, { recursive: true, withFileTypes: true })) {
    if (!entry.isFile()) continue;
    const file = path.join(entry.parentPath, entry.name);
    files[path.relative(dir, file).split(path.sep).join('/')] = fs.readFileSync(file, 'utf8');
  }
  return files;
}

const manifest = (dest) => JSON.parse(fs.readFileSync(path.join(dest, '.croftweaver.json'), 'utf8'));
const backups = (home) => fs.readdirSync(path.join(home, '.claude')).filter((n) => n.startsWith('skills-before-croftweaver-'));
const link = (target, at) => fs.symlinkSync(target, at, POSIX ? 'dir' : 'junction');

const V1 = {
  'README.md': 'not a skill',
  'docs/GETTING-STARTED.md': 'not a skill either',
  'docs/guides/deep.md': 'three folders deep, as a skill\'s files are, and still not a skill',
  'skills/new-website/SKILL.md': 'orchestrator, 9.1',
  'skills/alpha/SKILL.md': 'alpha, 9.1',
  'skills/alpha/scripts/run.sh': { data: '#!/bin/sh\necho 9.1\n', mode: 0o100755 },
  'skills/alpha/references/old.md': 'only in 9.1',
  'skills/gone/SKILL.md': 'dropped after 9.1',
};
const V2 = {
  'skills/new-website/SKILL.md': 'orchestrator, 9.2',
  'skills/alpha/SKILL.md': 'alpha, 9.2',
  'skills/alpha/scripts/run.sh': { data: '#!/bin/sh\necho 9.2\n', mode: 0o100755 },
  'skills/fresh/SKILL.md': { data: 'new in 9.2', store: true },
};

test('a first run installs every skill of the latest release, and nothing else from the zip', async () => {
  const home = tmp();
  const dest = path.join(home, '.claude', 'skills');
  served = { status: 200, release: 'v9.1', zip: makeZip(V1) };

  const result = await run(home);

  assert.equal(result.code, 0, result.stderr);
  assert.deepEqual(fs.readdirSync(dest).sort(), ['.croftweaver.json', 'alpha', 'gone', 'new-website']);
  assert.deepEqual(tree(path.join(dest, 'alpha')), {
    'SKILL.md': 'alpha, 9.1', 'scripts/run.sh': '#!/bin/sh\necho 9.1\n', 'references/old.md': 'only in 9.1',
  });
  assert.deepEqual(manifest(dest), { release: 'v9.1', skills: ['alpha', 'gone', 'new-website'] });
  if (POSIX) {
    // A skill's script is run as ./scripts/…, so a copy that drops the bit breaks the skill.
    assert.ok(fs.statSync(path.join(dest, 'alpha', 'scripts', 'run.sh')).mode & 0o111, 'run.sh lost its executable bit');
    assert.equal(fs.statSync(path.join(dest, 'alpha', 'SKILL.md')).mode & 0o111, 0);
  }
  // The owner's next step is the point of the whole run.
  assert.match(result.stdout, /Croftweaver v9\.1 is installed: 3 skills in /);
  assert.match(result.stdout, /restart Claude Code/);
  assert.match(result.stdout, /\n {4}new website\n/);
});

test('a second run makes the folder match the new release: changed, added and dropped skills', async () => {
  const home = tmp();
  const dest = path.join(home, '.claude', 'skills');
  served = { status: 200, release: 'v9.1', zip: makeZip(V1) };
  assert.equal((await run(home)).code, 0);
  served = { status: 200, release: 'v9.2', zip: makeZip(V2) };

  const result = await run(home);

  assert.equal(result.code, 0, result.stderr);
  assert.deepEqual(fs.readdirSync(dest).sort(), ['.croftweaver.json', 'alpha', 'fresh', 'new-website']);
  // references/old.md is gone: a skill is replaced, not merged with what was there.
  assert.deepEqual(tree(path.join(dest, 'alpha')), { 'SKILL.md': 'alpha, 9.2', 'scripts/run.sh': '#!/bin/sh\necho 9.2\n' });
  assert.equal(fs.readFileSync(path.join(dest, 'fresh', 'SKILL.md'), 'utf8'), 'new in 9.2');
  assert.deepEqual(manifest(dest), { release: 'v9.2', skills: ['alpha', 'fresh', 'new-website'] });
  assert.match(result.stdout, /Removed, no longer part of Croftweaver: gone/);
  // An update of our own copies is not a reason for a backup folder.
  assert.deepEqual(backups(home), []);
});

test('a folder someone else put under a skill\'s name is moved beside the skills folder, not lost and not left to load twice', async () => {
  const home = tmp();
  const dest = path.join(home, '.claude', 'skills');
  fs.mkdirSync(path.join(dest, 'alpha'), { recursive: true });
  fs.writeFileSync(path.join(dest, 'alpha', 'SKILL.md'), 'my own alpha');
  fs.mkdirSync(path.join(dest, 'my-notes'));
  fs.writeFileSync(path.join(dest, 'my-notes', 'SKILL.md'), 'not a Croftweaver name');
  served = { status: 200, release: 'v9.1', zip: makeZip(V1) };

  const result = await run(home);

  assert.equal(result.code, 0, result.stderr);
  assert.equal(fs.readFileSync(path.join(dest, 'alpha', 'SKILL.md'), 'utf8'), 'alpha, 9.1');
  assert.equal(fs.readFileSync(path.join(dest, 'my-notes', 'SKILL.md'), 'utf8'), 'not a Croftweaver name');
  const [backup, ...more] = backups(home);
  assert.deepEqual(more, []);
  assert.deepEqual(tree(path.join(home, '.claude', backup)), { 'alpha/SKILL.md': 'my own alpha' });
  assert.ok(result.stdout.includes(path.join(home, '.claude', backup)), 'the output does not say where the folder went');
});

test('skills linked from a toolkit folder are left alone, and --force swaps the link for a copy without touching that folder', async () => {
  const home = tmp();
  const dest = path.join(home, '.claude', 'skills');
  const toolkit = path.join(home, 'toolkit', 'skills', 'alpha');
  fs.mkdirSync(toolkit, { recursive: true });
  fs.writeFileSync(path.join(toolkit, 'SKILL.md'), 'alpha from the toolkit folder');
  fs.mkdirSync(dest, { recursive: true });
  link(toolkit, path.join(dest, 'alpha'));
  served = { status: 200, release: 'v9.1', zip: makeZip(V1) };

  const kept = await run(home);

  assert.equal(kept.code, 0, kept.stderr);
  assert.ok(fs.lstatSync(path.join(dest, 'alpha')).isSymbolicLink(), 'the link was replaced');
  assert.equal(fs.readFileSync(path.join(dest, 'alpha', 'SKILL.md'), 'utf8'), 'alpha from the toolkit folder');
  // Not in the list of copies: a later run must not treat the link's name as its own.
  assert.deepEqual(manifest(dest).skills, ['gone', 'new-website']);
  assert.match(kept.stdout, /Left as it is: 1 skill linked from another folder/);
  assert.match(kept.stdout, /is installed: 2 skills/);
  assert.doesNotMatch(kept.stdout, /No skill was changed/);
  assert.match(kept.stdout, /npm create croftweaver -- --force/);

  const forced = await run(home, ['--force']);

  assert.equal(forced.code, 0, forced.stderr);
  assert.ok(!fs.lstatSync(path.join(dest, 'alpha')).isSymbolicLink(), 'the link is still there');
  assert.equal(fs.readFileSync(path.join(dest, 'alpha', 'SKILL.md'), 'utf8'), 'alpha, 9.1');
  assert.equal(fs.readFileSync(path.join(toolkit, 'SKILL.md'), 'utf8'), 'alpha from the toolkit folder');
  assert.deepEqual(backups(home), []);
});

test('with every skill linked it says that no skill was changed, unless it removed one', async () => {
  const home = tmp();
  const dest = path.join(home, '.claude', 'skills');
  const only = { 'skills/new-website/SKILL.md': 'orchestrator, 9.1' };
  served = { status: 200, release: 'v9.1', zip: makeZip({ ...only, 'skills/gone/SKILL.md': 'dropped after 9.1' }) };
  assert.equal((await run(home)).code, 0);
  // The owner switches to a cloned toolkit: the orchestrator becomes a link.
  const toolkit = path.join(home, 'toolkit', 'skills', 'new-website');
  fs.mkdirSync(toolkit, { recursive: true });
  fs.writeFileSync(path.join(toolkit, 'SKILL.md'), 'orchestrator from the toolkit folder');
  fs.rmSync(path.join(dest, 'new-website'), { recursive: true });
  link(toolkit, path.join(dest, 'new-website'));
  served = { status: 200, release: 'v9.2', zip: makeZip(only) };

  const removing = await run(home);

  assert.equal(removing.code, 0, removing.stderr);
  assert.match(removing.stdout, /Removed, no longer part of Croftweaver: gone/);
  assert.doesNotMatch(removing.stdout, /No skill was changed|is installed/);

  const idle = await run(home);

  assert.equal(idle.code, 0, idle.stderr);
  assert.match(idle.stdout, /^No skill was changed in /);
  assert.match(idle.stdout, /Left as it is: 1 skill linked from another folder/);
});

test('a skill folder may have any name that is one folder name: the installer is published once and must take later releases', async () => {
  const home = tmp();
  const dest = path.join(home, '.claude', 'skills');
  const odd = ['Odd_Name.v2', 'café', 'website tools', '_helper'];
  served = { status: 200, release: 'v9.1', zip: makeZip({ ...V1, ...Object.fromEntries(odd.map((name) => [`skills/${name}/SKILL.md`, `this is ${name}`])) }) };

  const result = await run(home);

  assert.equal(result.code, 0, result.stderr);
  for (const name of odd) assert.equal(fs.readFileSync(path.join(dest, name, 'SKILL.md'), 'utf8'), `this is ${name}`);
  // And a second run knows them as its own: nothing is moved to a backup.
  assert.equal((await run(home)).code, 0);
  assert.deepEqual(backups(home), []);
});

test('a staging folder that is not this run\'s is left alone, however old: it may be a live run\'s', async () => {
  const home = tmp();
  const dest = path.join(home, '.claude', 'skills');
  const old = path.join(dest, '.croftweaver-staging-old');
  const fresh = path.join(dest, '.croftweaver-staging-fresh');
  for (const dir of [old, fresh]) {
    fs.mkdirSync(path.join(dir, 'alpha'), { recursive: true });
    fs.writeFileSync(path.join(dir, 'alpha', 'SKILL.md'), 'unpacked by another run');
  }
  const twoDaysAgo = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000);
  fs.utimesSync(old, twoDaysAgo, twoDaysAgo);
  served = { status: 200, release: 'v9.1', zip: makeZip(V1) };

  const result = await run(home);

  assert.equal(result.code, 0, result.stderr);
  assert.deepEqual(fs.readdirSync(dest).sort(), ['.croftweaver-staging-fresh', '.croftweaver-staging-old', '.croftweaver.json', 'alpha', 'gone', 'new-website']);
  // The other runs can still finish: what they unpacked is all there.
  for (const dir of [old, fresh]) assert.deepEqual(tree(dir), { 'alpha/SKILL.md': 'unpacked by another run' });
});

test('where the skills folder is itself a link, the backup goes beside the real folder', async () => {
  const home = tmp();
  const real = path.join(home, 'elsewhere', 'skills');
  fs.mkdirSync(path.join(real, 'alpha'), { recursive: true });
  fs.writeFileSync(path.join(real, 'alpha', 'SKILL.md'), 'my own alpha');
  fs.mkdirSync(path.join(home, '.claude'));
  link(real, path.join(home, '.claude', 'skills'));
  served = { status: 200, release: 'v9.1', zip: makeZip(V1) };

  const result = await run(home);

  assert.equal(result.code, 0, result.stderr);
  assert.equal(fs.readFileSync(path.join(real, 'alpha', 'SKILL.md'), 'utf8'), 'alpha, 9.1');
  const [backup, ...more] = fs.readdirSync(path.join(home, 'elsewhere')).filter((n) => n.startsWith('skills-before-croftweaver-'));
  assert.deepEqual(more, []);
  assert.deepEqual(tree(path.join(home, 'elsewhere', backup)), { 'alpha/SKILL.md': 'my own alpha' });
  // Beside the link there is only the link.
  assert.deepEqual(fs.readdirSync(path.join(home, '.claude')), ['skills']);
});

test('a link whose folder is gone is replaced: keeping it would keep a skill that cannot load', async () => {
  const home = tmp();
  const dest = path.join(home, '.claude', 'skills');
  fs.mkdirSync(dest, { recursive: true });
  link(path.join(home, 'deleted-toolkit', 'skills', 'alpha'), path.join(dest, 'alpha'));
  served = { status: 200, release: 'v9.1', zip: makeZip(V1) };

  const result = await run(home);

  assert.equal(result.code, 0, result.stderr);
  assert.ok(!fs.lstatSync(path.join(dest, 'alpha')).isSymbolicLink());
  assert.equal(fs.readFileSync(path.join(dest, 'alpha', 'SKILL.md'), 'utf8'), 'alpha, 9.1');
});

test('each assistant gets its own folder, and the two overrides of the shell installers hold here too', async () => {
  served = { status: 200, release: 'v9.1', zip: makeZip(V1) };
  const home = tmp();

  const codex = await run(home, ['--codex']);
  assert.equal(codex.code, 0, codex.stderr);
  assert.ok(fs.existsSync(path.join(home, '.agents', 'skills', 'new-website', 'SKILL.md')));
  assert.match(codex.stdout, /restart Codex/);

  const antigravity = await run(home, ['--antigravity']);
  assert.equal(antigravity.code, 0, antigravity.stderr);
  assert.ok(fs.existsSync(path.join(home, '.gemini', 'config', 'skills', 'new-website', 'SKILL.md')));
  assert.match(antigravity.stdout, /restart Antigravity/);

  // Neither run may have written to the default assistant's folder.
  assert.ok(!fs.existsSync(path.join(home, '.claude')));

  const custom = path.join(home, 'custom', 'claude-skills');
  assert.equal((await run(home, [], { CLAUDE_SKILLS_DIR: custom })).code, 0);
  assert.ok(fs.existsSync(path.join(custom, 'new-website', 'SKILL.md')));
  const customCodex = path.join(home, 'custom', 'codex-skills');
  assert.equal((await run(home, ['--codex'], { CODEX_SKILLS_DIR: customCodex })).code, 0);
  assert.ok(fs.existsSync(path.join(customCodex, 'new-website', 'SKILL.md')));
  assert.ok(!fs.existsSync(path.join(home, '.claude')));
});

test('a download that cannot be used changes nothing in an install that works', async (t) => {
  const home = tmp();
  const dest = path.join(home, '.claude', 'skills');
  served = { status: 200, release: 'v9.1', zip: makeZip(V1) };
  assert.equal((await run(home)).code, 0);
  const working = tree(dest);

  const good = makeZip(V2);
  const wrongOffsets = Buffer.from(good);
  wrongOffsets.writeUInt32LE(0x7fffffff, wrongOffsets.length - 6);
  const bad = {
    'the server has no such file': { status: 404, zip: good },
    'the zip is cut short': { status: 200, zip: good.subarray(0, good.length - 40) },
    'the zip points past its own end': { status: 200, zip: wrongOffsets },
    'a file fails its checksum': { status: 200, zip: makeZip({ ...V2, 'skills/alpha/SKILL.md': { data: 'x', crc: 1 } }) },
    'a path climbs out of the skills folder': { status: 200, zip: makeZip({ ...V2, 'skills/alpha/../../../escaped.txt': 'out' }) },
    'a path climbs out the Windows way': { status: 200, zip: makeZip({ ...V2, 'skills/alpha/..\\..\\..\\escaped.txt': 'out' }) },
    'a skill name is not a plain name': { status: 200, zip: makeZip({ ...V2, 'skills/.croftweaver.json/x': 'out' }) },
    'a path names a Windows drive': { status: 200, zip: makeZip({ ...V2, 'skills/alpha/D:escaped.txt': 'out' }) },
    'a path steps sideways into another folder': { status: 200, zip: makeZip({ ...V2, 'skills/alpha/../ghost/SKILL.md': 'x' }) },
    'a skill is named but has no folder': { status: 200, zip: makeZip({ ...V2, 'skills/empty/./x/../../late/SKILL.md': 'x' }) },
    'the orchestrator\'s SKILL.md is a folder': { status: 200, zip: makeZip({ 'skills/alpha/SKILL.md': 'a', 'skills/new-website/SKILL.md/x': 'not a file' }) },
    'the zip holds a link': { status: 200, zip: makeZip({ ...V2, 'skills/alpha/link': { data: '/etc', mode: 0o120777 } }) },
    'the zip is not a Croftweaver release': { status: 200, zip: makeZip({ 'skills/alpha/SKILL.md': 'no orchestrator' }) },
  };
  for (const [name, { status, zip }] of Object.entries(bad)) {
    await t.test(name, async () => {
      served = { status, release: 'v9.2', zip };

      const result = await run(home);

      assert.equal(result.code, 1, result.stdout);
      assert.match(result.stderr, /^Croftweaver was not installed: /);
      assert.deepEqual(tree(dest), working);
      assert.deepEqual(fs.readdirSync(dest).sort(), ['.croftweaver.json', 'alpha', 'gone', 'new-website']);
      assert.deepEqual(tree(home), Object.fromEntries(Object.entries(working).map(([file, text]) => [`.claude/skills/${file}`, text])));
    });
  }

  await t.test('on a computer without the skills, a failed run leaves no empty folder behind', async () => {
    const fresh = tmp();
    served = { status: 200, release: 'v9.2', zip: makeZip({ 'skills/alpha/SKILL.md': 'no orchestrator' }) };

    const result = await run(fresh);

    assert.equal(result.code, 1, result.stdout);
    assert.deepEqual(fs.readdirSync(fresh), []);
    // The same with part of the way already there: only what this run created goes.
    fs.mkdirSync(path.join(fresh, '.claude'));
    fs.writeFileSync(path.join(fresh, '.claude', 'settings.json'), '{}');
    assert.equal((await run(fresh)).code, 1);
    assert.deepEqual(tree(fresh), { '.claude/settings.json': '{}' });
    assert.deepEqual(fs.readdirSync(path.join(fresh, '.claude')), ['settings.json']);
  });

  await t.test('nothing answers at the address', async () => {
    const closed = http.createServer();
    await new Promise((done) => closed.listen(0, '127.0.0.1', done));
    const { port } = closed.address();
    await new Promise((done) => closed.close(done));

    const result = await run(home, [], { CROFTWEAVER_ZIP_URL: `http://127.0.0.1:${port}/croftweaver.zip` });

    assert.equal(result.code, 1, result.stdout);
    assert.match(result.stderr, /^Croftweaver was not installed: the download from .* failed/);
    assert.match(result.stderr, /Check your internet connection/);
    assert.deepEqual(tree(dest), working);
  });
});

// The zip's own CRCs only show the file is whole as zipped. SHA256SUMS, written when the
// release was built and uploaded with it, also catches a download that was damaged, cut
// short or swapped for another release's on the way. It is only as trustworthy as the
// release it comes from. Without it, or against it, nothing is unpacked.
test('a download that its release\'s SHA256SUMS does not vouch for changes nothing', async (t) => {
  const home = tmp();
  const dest = path.join(home, '.claude', 'skills');
  served = { status: 200, release: 'v9.1', zip: makeZip(V1) };
  assert.equal((await run(home)).code, 0);
  const working = tree(dest);
  const zip = makeZip(V2);
  const bad = {
    'the release has no SHA256SUMS (as 0.31 and older)': [null, /has no SHA256SUMS file to check the download against/],
    'SHA256SUMS cannot be fetched': [500, /could not be downloaded \(the server answered 500\)/],
    'the zip does not match its sum': [`${sha256(makeZip(V1))}  croftweaver.zip\n`, /does not match the checksum/],
    'the sum is for another file': [`${sha256(zip)}  something-else.zip\n`, /does not list croftweaver\.zip exactly once/],
    'the zip is listed twice': [`${sha256(zip)}  croftweaver.zip\n${sha256(zip)}  croftweaver.zip\n`, /exactly once/],
    'the sum is cut short': [`${sha256(zip).slice(0, 63)}  croftweaver.zip\n`, /exactly once/],
    'the file is empty': ['', /exactly once/],
  };
  for (const [name, [sums, why]] of Object.entries(bad)) {
    await t.test(name, async () => {
      served = { status: 200, release: 'v9.2', zip, sums };

      const result = await run(home);

      assert.equal(result.code, 1, result.stdout);
      assert.match(result.stderr, /^Croftweaver was not installed: /);
      assert.match(result.stderr, why);
      assert.deepEqual(tree(dest), working);
      assert.deepEqual(fs.readdirSync(dest).sort(), ['.croftweaver.json', 'alpha', 'gone', 'new-website']);
    });
  }

  // The check comes before the unpacking, not after it: a zip that is wrong in two ways is
  // refused for its sum, so not one of its bytes was written into the skills folder first.
  await t.test('the sum is checked before anything is unpacked', async () => {
    served = { status: 200, release: 'v9.2', zip: makeZip({ ...V2, 'skills/alpha/../../../escaped.txt': 'out' }), sums: null };

    const result = await run(home);

    assert.equal(result.code, 1, result.stdout);
    assert.match(result.stderr, /has no SHA256SUMS file/);
    assert.doesNotMatch(result.stderr, /could not be unpacked/);
    assert.deepEqual(tree(dest), working);
    assert.ok(!fs.existsSync(path.join(home, '.claude', 'escaped.txt')), 'the climbing entry was written');
  });

  await t.test('on a computer without the skills, a refused download leaves no folder behind', async () => {
    const fresh = tmp();
    served = { status: 200, release: 'v9.2', zip, sums: null };

    assert.equal((await run(fresh)).code, 1);
    assert.deepEqual(fs.readdirSync(fresh), []);
  });
});

test('SHA256SUMS comes from the release the redirect names, and is read the way release tools write it', async (t) => {
  const zip = makeZip(V1);
  await t.test('the sum is fetched from the same release folder as the zip', async () => {
    const home = tmp();
    served = { status: 200, release: 'v9.3', zip };
    asked.length = 0;

    assert.equal((await run(home)).code, 0);
    assert.deepEqual(asked, ['/latest/download/croftweaver.zip', '/download/v9.3/croftweaver.zip', '/download/v9.3/SHA256SUMS']);
  });
  const forms = {
    'binary mode, a star before the name': `${sha256(zip)} *croftweaver.zip\n`,
    'Windows line ends, with other files listed too': `${sha256('x')}  other.txt\r\n${sha256(zip)}  croftweaver.zip\r\n`,
    'no line end at the end': `${sha256(zip)}  croftweaver.zip`,
  };
  for (const [name, sums] of Object.entries(forms)) {
    await t.test(name, async () => {
      served = { status: 200, release: 'v9.3', zip, sums };
      const result = await run(tmp());
      assert.equal(result.code, 0, result.stderr);
    });
  }
  // An address may spell the file name with %-escapes; SHA256SUMS spells it plainly.
  await t.test('a file name written with %-escapes in the address is the same name', async () => {
    served = { status: 200, release: 'v9.3', zip };
    const port = new URL(latest).port;
    const result = await run(tmp(), [], { CROFTWEAVER_ZIP_URL: `http://127.0.0.1:${port}/download/v9.3/croft%77eaver.zip` });
    assert.equal(result.code, 0, result.stderr);
  });
  // scripts/package.sh writes the file with sha256sum on Linux and `shasum -a 256` on macOS.
  await t.test('the line sha256sum or shasum writes for the zip', { skip: POSIX ? false : 'Windows runners have neither tool' }, async () => {
    const folder = tmp();
    fs.writeFileSync(path.join(folder, 'croftweaver.zip'), zip);
    let tool = ['sha256sum'];
    try { execFileSync('sha256sum', ['--version'], { stdio: 'ignore' }); } catch { tool = ['shasum', '-a', '256']; }
    const sums = execFileSync(tool[0], [...tool.slice(1), 'croftweaver.zip'], { cwd: folder, encoding: 'utf8' });
    served = { status: 200, release: 'v9.3', zip, sums };

    const result = await run(tmp());

    assert.equal(result.code, 0, result.stderr);
  });
});

test('an argument it does not know stops it before anything is downloaded or written', async () => {
  const home = tmp();
  served = { status: 200, release: 'v9.1', zip: makeZip(V1) };

  for (const args of [['--nope'], ['--codex', '--antigravity'], ['extra']]) {
    const result = await run(home, args);
    assert.equal(result.code, 2, args.join(' '));
    assert.match(result.stderr, /^usage: npm create croftweaver/);
  }
  assert.deepEqual(fs.readdirSync(home), []);
});

// npm puts the package's own LICENSE into the tarball. It is a copy, and a copy drifts.
test('the LICENSE that ships to npm is the repo\'s', () => {
  assert.ok(fs.readFileSync(path.join(HERE, '..', 'LICENSE')).equals(fs.readFileSync(path.join(REPO, 'LICENSE'))));
});

// The cases above read zips this file wrote itself, so a mistake shared by its writer and
// the installer's reader would pass. These two read the real skills from zips other programs
// wrote, and compare each installed file with git's own record of it: its blob id and
// whether it is executable.
function gitBlobId(data) {
  return crypto.createHash('sha1').update(`blob ${data.length}\0`).update(data).digest('hex');
}

async function installsHeadExactly(zip) {
  const home = tmp();
  const dest = path.join(home, '.claude', 'skills');
  served = { status: 200, release: 'v9.9', zip };

  const result = await run(home);

  assert.equal(result.code, 0, result.stderr);
  // "100755 blob <id>\tskills/<file>", one line per file at HEAD.
  const recorded = execFileSync('git', ['ls-tree', '-r', 'HEAD', 'skills'], { cwd: REPO, encoding: 'utf8' })
    .split('\n').filter(Boolean).map((line) => /^(\d+) blob ([0-9a-f]+)\tskills\/(.+)$/.exec(line));
  assert.ok(recorded.length > 100 && recorded.every(Boolean), 'git ls-tree did not list the skills as expected');
  const installed = fs.readdirSync(dest, { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => path.relative(dest, path.join(entry.parentPath, entry.name)).split(path.sep).join('/'))
    .filter((file) => file !== '.croftweaver.json')
    .sort();
  assert.deepEqual(installed, recorded.map(([, , , file]) => file).sort());
  for (const [, mode, id, file] of recorded) {
    const to = path.join(dest, file);
    assert.equal(gitBlobId(fs.readFileSync(to)), id, `${file} differs`);
    if (POSIX) assert.equal((fs.statSync(to).mode & 0o111) !== 0, mode === '100755', `${file}: executable bit`);
  }
  assert.deepEqual(manifest(dest).skills, [...new Set(recorded.map(([, , , file]) => file.split('/')[0]))].sort());
}

// git writes zips too, on every system, so this one also runs on Windows.
test('the real skills, zipped by git, arrive file for file', async () => {
  await installsHeadExactly(execFileSync('git', ['archive', '--format=zip', 'HEAD', 'skills'], { cwd: REPO, maxBuffer: 256 * 1024 * 1024 }));
});

// scripts/package.sh builds the release with `zip -r -X`; this is that tool's output.
test('the real skills, zipped the way a release is, arrive file for file with their executable bits',
  { skip: POSIX ? false : 'Windows runners have no zip tool; the test above reads the real skills there' }, async () => {
    const source = tmp();
    const tar = execFileSync('git', ['archive', '--format=tar', 'HEAD', 'skills'], { cwd: REPO, maxBuffer: 256 * 1024 * 1024 });
    execFileSync('tar', ['-x', '-f', '-', '-C', source], { input: tar });
    const zipFile = path.join(tmp(), 'croftweaver.zip');
    execFileSync('zip', ['-r', '-X', '-q', zipFile, 'skills'], { cwd: source });
    await installsHeadExactly(fs.readFileSync(zipFile));
  });
