// Post-build: write the commit SHA this build was made from to dist/build.txt.
// Why: "push = live" is a promise, not a fact — Cloudflare Pages can silently
// stop building (webhook auth lapse; seen in production 2026-07-02: two green
// pushes, no deploy for 40+ min). The marker lets `npm run ship` VERIFY the
// live site actually serves the new build instead of hoping. On Cloudflare the
// SHA comes from CF_PAGES_COMMIT_SHA; locally from git; 'dev' as last resort.
// (Exposes only the bare SHA — no repo content; harmless on a public site.)
// Test builds only: playwright.config.ts sets SITE_TEST_BUILD to a random id per test run, and
// it goes into dist/test-build-id.txt, so tests/served-build.spec.ts can tell this run's build
// from any other. Any other build deletes that file, so a production build never carries one.
import { rmSync, writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';

let sha = process.env.CF_PAGES_COMMIT_SHA;
if (!sha) {
  try {
    sha = execSync('git rev-parse HEAD', { encoding: 'utf8' }).trim();
  } catch {
    sha = 'dev';
  }
}
writeFileSync('dist/build.txt', sha + '\n');
console.log(`build marker: dist/build.txt = ${sha.slice(0, 12)}`);

if (process.env.SITE_TEST_BUILD) {
  writeFileSync('dist/test-build-id.txt', process.env.SITE_TEST_BUILD + '\n');
} else {
  rmSync('dist/test-build-id.txt', { force: true });
}
