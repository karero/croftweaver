// Post-build: write the commit SHA this build was made from to dist/build.txt.
// Why: "push = live" is a promise, not a fact — Cloudflare can silently stop building
// (webhook auth lapse; seen in production 2026-07-02: two green pushes, no deploy for
// 40+ min). The marker lets `npm run ship` VERIFY the live site actually serves the new
// build instead of hoping. The SHA comes from CF_PAGES_COMMIT_SHA (Pages) or
// WORKERS_CI_COMMIT_SHA (Workers Builds; set by Cloudflare, see
// developers.cloudflare.com/workers/ci-cd/builds/configuration), else from git; 'dev' as
// last resort. Workers Builds' variable holds a branch name, not a commit, in the build
// it runs when a Worker is first connected (tests/fixtures/workers-builds-2026-11-08.txt),
// so only a full commit id counts there.
// (Exposes only the bare SHA — no repo content; harmless on a public site.)
// Test builds only: playwright.config.ts sets SITE_TEST_BUILD to a random id per test run, and
// it goes into dist/test-build-id.txt, so tests/served-build.spec.ts can tell this run's build
// from any other. Any other build deletes that file, so a production build never carries one.
import { rmSync, writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';

let sha = process.env.CF_PAGES_COMMIT_SHA;
const workersSha = process.env.WORKERS_CI_COMMIT_SHA;
if (!sha && /^([0-9a-f]{40}|[0-9a-f]{64})$/.test(workersSha ?? '')) sha = workersSha;
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
