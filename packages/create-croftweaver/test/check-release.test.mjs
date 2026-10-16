// Tests for check-release.mjs, the guard npm runs before `npm publish`. The installer refuses
// a release whose zip does not match its SHA256SUMS, or that has none, so publishing it while
// the latest release fails that check would stop every install. The guard runs the installer
// itself into a throwaway folder: these tests show it passes exactly when an install would,
// and touches nothing of the user's. A stub on 127.0.0.1 stands in for GitHub, with the same
// "latest" redirect to the release's folder; no real requests.
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { after, before, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { makeZip } from './zip.mjs';

const GUARD = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'check-release.mjs');
const ZIP = makeZip({ 'skills/new-website/SKILL.md': 'orchestrator', 'skills/alpha/SKILL.md': 'alpha' });
const SUM = crypto.createHash('sha256').update(ZIP).digest('hex');
let served = {};
const server = http.createServer((req, res) => {
  const { zip = ZIP, sums = `${SUM}  croftweaver.zip\n`, sumsStatus = 200 } = served;
  if (req.url === '/latest/download/croftweaver.zip') res.writeHead(302, { location: '/download/v9.3/croftweaver.zip' }).end();
  else if (req.url === '/download/v9.3/croftweaver.zip') res.writeHead(200).end(zip);
  else if (req.url === '/download/v9.3/SHA256SUMS') res.writeHead(sumsStatus).end(sums);
  else res.writeHead(404).end('not here');
});
let url;
before(async () => {
  await new Promise((done) => server.listen(0, '127.0.0.1', done));
  url = `http://127.0.0.1:${server.address().port}/latest/download/croftweaver.zip`;
});
after(() => server.close());

const guard = (env = {}) => new Promise((resolve) => {
  execFile(process.execPath, [GUARD], { env: { ...process.env, CROFTWEAVER_ZIP_URL: url, npm_lifecycle_event: '', ...env } },
    (error, stdout, stderr) => resolve({ code: error ? error.code : 0, stdout, stderr }));
});

test('the publish goes ahead when the installer takes the latest release, and the user\'s skills are not touched', async () => {
  served = {};
  const home = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'check-release-home-')));
  try {
    const result = await guard({ HOME: home, USERPROFILE: home, CLAUDE_SKILLS_DIR: '' });
    assert.equal(result.code, 0, result.stderr);
    assert.match(result.stdout, /The installer takes the latest release. What it printed:\nCroftweaver v9\.3 is installed/);
    assert.deepEqual(fs.readdirSync(home), []);
  } finally {
    fs.rmSync(home, { recursive: true, force: true });
  }
});

test('the publish stops whenever the installer would refuse the latest release', async (t) => {
  const refused = {
    'no SHA256SUMS, as 0.31 has none': [{ sums: 'Not Found', sumsStatus: 404 }, /has no SHA256SUMS file/],
    'SHA256SUMS answers 500': [{ sumsStatus: 500 }, /answered 500/],
    'the zip is listed twice': [{ sums: `${SUM}  croftweaver.zip\n${SUM}  croftweaver.zip\n` }, /exactly once/],
    'the zip does not match its sum': [{ sums: `${'c'.repeat(64)}  croftweaver.zip\n` }, /does not match the checksum/],
    'the zip matches but holds no Croftweaver skills': [{ zip: makeZip({ 'skills/alpha/SKILL.md': 'x' }), sums: null }, /could not be unpacked: it holds no Croftweaver skills/],
  };
  for (const [name, [change, why]] of Object.entries(refused)) {
    await t.test(name, async () => {
      served = { ...change };
      if (change.sums === null) {   // a matching sum for this other zip
        served.sums = `${crypto.createHash('sha256').update(change.zip).digest('hex')}  croftweaver.zip\n`;
      }
      const result = await guard();
      assert.equal(result.code, 1, result.stdout);
      assert.match(result.stderr, /^(Checking .*\n)?Not published: the installer refuses the latest release/);
      assert.match(result.stderr, why);
    });
  }
  await t.test('nothing answers at the address', async () => {
    const closed = http.createServer();
    await new Promise((done) => closed.listen(0, '127.0.0.1', done));
    const { port } = closed.address();
    await new Promise((done) => closed.close(done));
    const result = await guard({ CROFTWEAVER_ZIP_URL: `http://127.0.0.1:${port}/latest/download/croftweaver.zip` });
    assert.equal(result.code, 1);
    assert.match(result.stderr, /Not published: the installer refuses the latest release/);
    assert.match(result.stderr, /the download from .* failed/);
  });
});

// A test address left in the shell would point the guard away from GitHub.
test('during npm publish, an address from CROFTWEAVER_ZIP_URL stops the publish; run by hand, it is named', async () => {
  served = {};
  const publishing = await guard({ npm_lifecycle_event: 'prepublishOnly' });
  assert.equal(publishing.code, 1);
  assert.match(publishing.stderr, /^Not published: CROFTWEAVER_ZIP_URL is set/);
  const byHand = await guard();
  assert.equal(byHand.code, 0, byHand.stderr);
  assert.match(byHand.stderr, /from CROFTWEAVER_ZIP_URL, not GitHub's latest release/);
});
