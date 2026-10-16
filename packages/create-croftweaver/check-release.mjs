#!/usr/bin/env node
// Run by npm before `npm publish` (prepublishOnly), and by hand after each release: does the
// installer in this folder take the latest Croftweaver release? It refuses a release whose
// zip does not match its SHA256SUMS, or that has none, so publishing it while the latest
// release fails would stop every install. Rather than a second copy of that check, this runs
// the installer itself, into a throwaway skills folder, and passes only if the install does.
// npm skips it with --ignore-scripts, ignore-scripts=true in an .npmrc, or a publish from a
// .tgz: then run `npm run prepublishOnly` by hand first. Not part of the package.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const INSTALLER = path.join(path.dirname(fileURLToPath(import.meta.url)), 'index.mjs');
const override = process.env.CROFTWEAVER_ZIP_URL;
if (override && process.env.npm_lifecycle_event === 'prepublishOnly') {
  console.error(`Not published: CROFTWEAVER_ZIP_URL is set (${override}), so this would check that address, not GitHub's latest release. Unset it, then publish again.`);
  process.exit(1);
}
if (override) console.error(`Checking ${override}, from CROFTWEAVER_ZIP_URL, not GitHub's latest release.`);

const home = fs.mkdtempSync(path.join(os.tmpdir(), 'croftweaver-check-release-'));
try {
  const env = { ...process.env, CLAUDE_SKILLS_DIR: path.join(home, 'skills'), HOME: home, USERPROFILE: home };
  const out = execFileSync(process.execPath, [INSTALLER], { env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  console.log(`The installer takes the latest release: ${out.split('\n')[0]}`);
} catch (e) {
  console.error(`Not published: the installer refuses the latest release.\n${(e.stderr || e.message).trim()}\nPublish once a release it takes is out.`);
  process.exitCode = 1;
} finally {
  fs.rmSync(home, { recursive: true, force: true });
}
