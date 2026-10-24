// Post-build: write the commit SHA this build was made from to dist/build.txt.
// Why: "push = live" is a promise, not a fact — Cloudflare Pages can silently
// stop building (webhook auth lapse; seen in production 2026-07-02: two green
// pushes, no deploy for 40+ min). The marker lets `npm run ship` VERIFY the
// live site actually serves the new build instead of hoping. On Cloudflare the
// SHA comes from CF_PAGES_COMMIT_SHA; locally from git; 'dev' as last resort.
// (Exposes only the bare SHA — no repo content; harmless on a public site.)
import { writeFileSync } from 'node:fs';
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
