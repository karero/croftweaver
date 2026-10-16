#!/usr/bin/env node
// Run by npm before `npm publish` (prepublishOnly): this installer refuses a release whose
// zip does not match its SHA256SUMS, or that has none, so publishing it while the latest
// Croftweaver release fails that check would stop every install. It makes the installer's
// own check on the latest release: the zip, then SHA256SUMS from the release folder the
// "latest" redirect names, exactly one line for croftweaver.zip, and the same SHA-256.
// npm skips it with --ignore-scripts, ignore-scripts=true in an .npmrc, or a publish from a
// .tgz: then run `npm run prepublishOnly` by hand first. Not part of the package.
import crypto from 'node:crypto';

const ZIP_URL = process.env.CROFTWEAVER_ZIP_URL
  || 'https://github.com/karero/croftweaver/releases/latest/download/croftweaver.zip';
const SUM_LINE = /^([0-9a-f]{64}) [ *](.+)$/;
const stop = (why) => {
  console.error(`Not published: ${why}\nThis installer would refuse the latest release. Publish once a release with a matching SHA256SUMS is out.`);
  process.exit(1);
};
if (process.env.CROFTWEAVER_ZIP_URL) console.error(`Checking ${ZIP_URL}, from CROFTWEAVER_ZIP_URL, not GitHub's latest release.`);

async function get(url, redirect = 'follow') {
  try {
    const res = await fetch(url, { redirect, signal: AbortSignal.timeout(300_000) });
    return { res, body: res.ok ? Buffer.from(await res.arrayBuffer()) : null };
  } catch (e) {
    return stop(`${url} could not be read (${e.cause?.code ?? e.message}).`);
  }
}

// As the installer's download(): the redirect names the release folder, where both files sit.
let from = new URL(ZIP_URL);
let { res, body: zip } = await get(ZIP_URL, 'manual');
const next = res.headers.get('location');
if (res.status >= 300 && res.status < 400 && next) {
  if (/\/download\/v?[0-9][0-9A-Za-z.-]*\//.test(next)) from = new URL(next, ZIP_URL);
  ({ res, body: zip } = await get(new URL(next, ZIP_URL)));
}
if (!zip) stop(`the latest release's croftweaver.zip could not be downloaded (the server answered ${res.status}).`);
const sumsUrl = new URL('SHA256SUMS', from);
const { res: sumsRes, body: sums } = await get(sumsUrl);
if (!sums) stop(`the latest release has no SHA256SUMS (${sumsUrl} answered ${sumsRes.status}).`);
const name = from.pathname.split('/').pop();
const listed = sums.toString('utf8').split(/\r?\n/).map((line) => SUM_LINE.exec(line)).filter((m) => m?.[2] === name);
if (listed.length !== 1) stop(`the latest release's SHA256SUMS does not list ${name} exactly once.`);
if (crypto.createHash('sha256').update(zip).digest('hex') !== listed[0][1]) {
  stop(`the latest release's ${name} does not match its SHA256SUMS.`);
}
console.log(`The latest release's ${name} matches its SHA256SUMS (${sumsUrl}).`);
