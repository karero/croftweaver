// Tests for check-release.mjs, the guard npm runs before `npm publish`. The installer refuses
// a release whose zip does not match its SHA256SUMS, or that has none, so publishing it while
// the latest release fails that check would stop every install: the guard must stop the
// publish then, and only then. A stub on 127.0.0.1 stands in for GitHub, with the same
// "latest" redirect to the release's folder; no real requests.
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import crypto from 'node:crypto';
import http from 'node:http';
import path from 'node:path';
import { after, before, test } from 'node:test';
import { fileURLToPath } from 'node:url';

const GUARD = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'check-release.mjs');
const ZIP = Buffer.from('a release zip');
const SUM = crypto.createHash('sha256').update(ZIP).digest('hex');
// What the stub serves: the zip's status, and SHA256SUMS as a body or a status.
let served = { zip: 200, sums: `${SUM}  croftweaver.zip\n`, sumsStatus: 200 };
const asked = [];
const server = http.createServer((req, res) => {
  asked.push(req.url);
  if (req.url === '/latest/download/croftweaver.zip') res.writeHead(302, { location: '/download/v9.3/croftweaver.zip' }).end();
  else if (req.url === '/download/v9.3/croftweaver.zip') res.writeHead(served.zip).end(served.zip === 200 ? ZIP : 'no');
  else if (req.url === '/download/v9.3/SHA256SUMS') res.writeHead(served.sumsStatus).end(served.sums);
  else res.writeHead(404).end('not here');
});
let url;
before(async () => {
  await new Promise((done) => server.listen(0, '127.0.0.1', done));
  url = `http://127.0.0.1:${server.address().port}/latest/download/croftweaver.zip`;
});
after(() => server.close());

const guard = (zipUrl = url) => new Promise((resolve) => {
  execFile(process.execPath, [GUARD], { env: { ...process.env, CROFTWEAVER_ZIP_URL: zipUrl } },
    (error, stdout, stderr) => resolve({ code: error ? error.code : 0, stdout, stderr }));
});

test('the publish goes ahead only when the latest release would pass the installer\'s own check', async (t) => {
  await t.test('a matching SHA256SUMS, from the folder the redirect names', async () => {
    served = { zip: 200, sums: `${SUM}  croftweaver.zip\n`, sumsStatus: 200 };
    asked.length = 0;
    const result = await guard();
    assert.equal(result.code, 0, result.stderr);
    assert.deepEqual(asked, ['/latest/download/croftweaver.zip', '/download/v9.3/croftweaver.zip', '/download/v9.3/SHA256SUMS']);
  });
  await t.test('the binary-mode form, with Windows line ends and another file listed', async () => {
    served = { zip: 200, sums: `${'b'.repeat(64)}  other.txt\r\n${SUM} *croftweaver.zip\r\n`, sumsStatus: 200 };
    assert.equal((await guard()).code, 0);
  });
});

test('the publish stops whenever the installer would refuse the latest release', async (t) => {
  const refused = {
    'no SHA256SUMS, as 0.31 has none': [{ sums: 'Not Found', sumsStatus: 404 }, /has no SHA256SUMS/],
    'SHA256SUMS answers 500, even with a matching line': [{ sums: `${SUM}  croftweaver.zip\n`, sumsStatus: 500 }, /has no SHA256SUMS/],
    'the zip is listed twice': [{ sums: `${SUM}  croftweaver.zip\n${SUM}  croftweaver.zip\n` }, /exactly once/],
    'the sum is for another file': [{ sums: `${SUM}  other.zip\n` }, /exactly once/],
    'the zip does not match its sum': [{ sums: `${'c'.repeat(64)}  croftweaver.zip\n` }, /does not match its SHA256SUMS/],
    'the zip cannot be downloaded': [{ zip: 404 }, /croftweaver\.zip could not be downloaded/],
  };
  for (const [name, [change, why]] of Object.entries(refused)) {
    await t.test(name, async () => {
      served = { zip: 200, sums: `${SUM}  croftweaver.zip\n`, sumsStatus: 200, ...change };
      const result = await guard();
      assert.equal(result.code, 1, result.stdout);
      assert.match(result.stderr, /Not published: /);
      assert.match(result.stderr, why);
    });
  }
  await t.test('nothing answers', async () => {
    const closed = http.createServer();
    await new Promise((done) => closed.listen(0, '127.0.0.1', done));
    const { port } = closed.address();
    await new Promise((done) => closed.close(done));
    const result = await guard(`http://127.0.0.1:${port}/latest/download/croftweaver.zip`);
    assert.equal(result.code, 1);
    assert.match(result.stderr, /could not be read/);
  });
});

// A test address left in the shell would point the guard away from GitHub: it says so.
test('an address from CROFTWEAVER_ZIP_URL is named, so a publish cannot check the wrong place unseen', async () => {
  served = { zip: 200, sums: `${SUM}  croftweaver.zip\n`, sumsStatus: 200 };
  const result = await guard();
  assert.match(result.stderr, /from CROFTWEAVER_ZIP_URL, not GitHub's latest release/);
});
