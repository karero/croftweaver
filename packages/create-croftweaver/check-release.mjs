#!/usr/bin/env node
// Run by npm before `npm publish` (prepublishOnly): this installer refuses a release with no
// SHA256SUMS, so publishing it while the latest Croftweaver release has none would stop every
// install. It asks GitHub for the latest release's SHA256SUMS, the way the installer does,
// and stops the publish unless that file lists croftweaver.zip. Not part of the package.
const SUMS_URL = process.env.CROFTWEAVER_SUMS_URL
  || 'https://github.com/karero/croftweaver/releases/latest/download/SHA256SUMS';

let res;
try {
  res = await fetch(SUMS_URL, { signal: AbortSignal.timeout(60_000) });
} catch (e) {
  console.error(`Not published: ${SUMS_URL} could not be read (${e.cause?.code ?? e.message}).`);
  process.exit(1);
}
const text = res.ok ? await res.text() : '';
if (!text.split(/\r?\n/).some((line) => /^[0-9a-f]{64} [ *]croftweaver\.zip$/.test(line))) {
  console.error(`Not published: the latest Croftweaver release has no SHA256SUMS listing croftweaver.zip (${SUMS_URL} answered ${res.status}).\nThis installer would refuse it. Publish once a release with SHA256SUMS is out.`);
  process.exit(1);
}
console.log(`The latest release lists croftweaver.zip in its SHA256SUMS (${res.url}).`);
