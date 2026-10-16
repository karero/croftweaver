// Tests for check-release.mjs, the guard npm runs before `npm publish`. The installer refuses
// a release with no SHA256SUMS, so publishing it while the latest release has none would stop
// every install: the guard must stop the publish then, and only then. A stub on 127.0.0.1
// stands in for GitHub; no real requests.
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import http from 'node:http';
import path from 'node:path';
import { after, before, test } from 'node:test';
import { fileURLToPath } from 'node:url';

const GUARD = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'check-release.mjs');
const SUM = 'a'.repeat(64);
let served = { status: 404, body: '' };
const server = http.createServer((req, res) => res.writeHead(served.status).end(served.body));
let url;
before(async () => {
  await new Promise((done) => server.listen(0, '127.0.0.1', done));
  url = `http://127.0.0.1:${server.address().port}/latest/download/SHA256SUMS`;
});
after(() => server.close());

const guard = () => new Promise((resolve) => {
  execFile(process.execPath, [GUARD], { env: { ...process.env, CROFTWEAVER_SUMS_URL: url } },
    (error, stdout, stderr) => resolve({ code: error ? error.code : 0, stdout, stderr }));
});

test('the publish stops while the latest release has no SHA256SUMS, as 0.31 has none', async () => {
  served = { status: 404, body: 'Not Found' };
  const result = await guard();
  assert.equal(result.code, 1, result.stdout);
  assert.match(result.stderr, /^Not published: the latest Croftweaver release has no SHA256SUMS/);
});

test('the publish stops when SHA256SUMS does not list croftweaver.zip', async () => {
  for (const body of ['', `${SUM}  other.zip\n`, `${SUM.slice(1)}  croftweaver.zip\n`]) {
    served = { status: 200, body };
    assert.equal((await guard()).code, 1, JSON.stringify(body));
  }
});

test('the publish goes ahead once the latest release lists croftweaver.zip, in the form release tools write', async () => {
  for (const body of [`${SUM}  croftweaver.zip\n`, `${SUM} *croftweaver.zip\r\n`]) {
    served = { status: 200, body };
    const result = await guard();
    assert.equal(result.code, 0, result.stderr);
  }
});

test('nothing answers: the publish stops', async () => {
  const closed = http.createServer();
  await new Promise((done) => closed.listen(0, '127.0.0.1', done));
  const { port } = closed.address();
  await new Promise((done) => closed.close(done));
  const result = await new Promise((resolve) => {
    execFile(process.execPath, [GUARD], { env: { ...process.env, CROFTWEAVER_SUMS_URL: `http://127.0.0.1:${port}/SHA256SUMS` } },
      (error, stdout, stderr) => resolve({ code: error ? error.code : 0, stdout, stderr }));
  });
  assert.equal(result.code, 1);
  assert.match(result.stderr, /could not be read/);
});
