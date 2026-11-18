// Post-build, two jobs.
// 1. Refuse create-astro's default icons: if dist/favicon.svg or dist/favicon.ico is Astro's
//    logo, say so on stderr (Playwright's webServer shows stderr, not stdout), remove dist/ so
//    no deploy can pick the build up, and exit 1. An absent file passes. Why: a site went live
//    with Astro's icon because the checks only asked whether the files exist.
//    `node scripts/build-marker.mjs --check <file>…` runs just that test (plus "does it start
//    like an icon") on the named files and writes nothing; the launch check uses it on the live
//    files, and exits 2 with a usage line when given no file.
// 2. Write the commit SHA this build was made from to dist/build.txt.
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
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';

// Astro's default icons, from withastro/astro examples/*/public (blob ids in the names of the
// fixtures in the toolkit's tests). An SVG is known by the opening of its outline path with all
// whitespace dropped, so line endings, re-indenting and svgo do not hide it; an ICO is a
// bitmap and is known by its SHA-256. The 2023 drawing and the 2022 one; the 2026 ICO (a PNG
// with an .ico name) and the 2021 one. The maintainer's release runbook (step 1b) checks these
// against Astro's examples before each release.
const ASTRO_SVG_OPENINGS = [
  'M50.478.5a75.175.1000-28.56.9l24.2-65.7c.7-21.9-3.23.4-3.2h29c1.502.71.23.43.2l24.265.7s-11.6-7-28.5-7L6745.5',
  'M22.254h-8.5a11000-.96.73l-5.5419.4a.5.5000.62.62l5.05-1.44',
];
const ASTRO_ICO_HASHES = [
  '09d2ac08d8cca9b6e1f90221f345a8c4dd0371c64a0dc52b6f96fc589b1e3d67',
  '5af608ecd60d93abd453f78896e95a7c8c0a2c632a92a10e57f19423f333bc46',
];

const isAstroSvg = (buf) => {
  // Comments are not drawn, so Astro's path inside one is not Astro's icon.
  const flat = buf.toString('utf8').replace(/<!--[\s\S]*?-->/g, '').replace(/\s/g, '');
  return ASTRO_SVG_OPENINGS.some((opening) => flat.includes(opening));
};
const isAstroIco = (buf) => ASTRO_ICO_HASHES.includes(createHash('sha256').update(buf).digest('hex'));
const isAstro = (kind, buf) => (kind === 'svg' ? isAstroSvg(buf) : isAstroIco(buf));

// --check only: does the body start like the file it is named? The first element of an SVG must
// be <svg, after an optional BOM, whitespace, <?…?> instructions, comments and one <!DOCTYPE svg>;
// an ICO starts with 00 00 01 00. This is how it starts, not proof of a working icon.
function startsLikeSvg(buf) {
  const text = buf.toString('utf8');
  let i = text.charCodeAt(0) === 0xfeff ? 1 : 0;
  let doctype = false;
  for (;;) {
    while (i < text.length && /\s/.test(text[i])) i++;
    let end = -1;
    const close = (open, shut) => {
      const at = text.indexOf(shut, i + open.length);
      return at === -1 ? null : at + shut.length;
    };
    if (text.startsWith('<?', i)) end = close('<?', '?>');
    else if (text.startsWith('<!--', i)) end = close('<!--', '-->');
    else if (!doctype) {
      const m = /^<!DOCTYPE\s+svg\b[^>[]*(\[[^\]]*\])?\s*>/i.exec(text.slice(i));
      if (m) { doctype = true; end = i + m[0].length; }
    }
    if (end === null) return false; // an unclosed instruction or comment
    if (end === -1) break;
    i = end;
  }
  return /^<svg[\s>/]/.test(text.slice(i));
}
const startsLikeIco = (buf) => buf.length >= 4 && buf.readUInt16LE(0) === 0 && buf.readUInt16LE(2) === 1;

function astroMessage(shown, publicName, kind, stopped) {
  const own = kind === 'svg' ? 'an SVG' : 'an ICO';
  return [
    `✗ ${shown} is Astro's default icon (${publicName}, from create-astro).`,
    stopped
      ? '  A site must not go live with it. This build was stopped, so nothing from it can be published.'
      : '  A site must not go live with it. Replace it, then publish again.',
    "  New site: node scripts/make-icons.mjs --setup  (draws the site's letter on its colour).",
    '  If --setup says the icons are not ones it made (an older Astro icon), run it with --replace',
    '  instead: only for a site with no icons of its own.',
    '  A site with a logo or icons of its own: the website-brand-kit skill, given the logo,',
    `  or replace ${publicName} by hand with ${own} of the site's own.`,
    stopped ? '  Then build again.' : '  Google may keep showing the old icon for some weeks.',
  ].join('\n');
}

const args = process.argv.slice(2);
const kindOf = (file) => (/\.svg$/i.test(file) ? 'svg' : /\.ico$/i.test(file) ? 'ico' : null);
const USAGE = 'usage: node scripts/build-marker.mjs [--check <file.svg|file.ico>…]';

if (args.length) {
  if (args[0] !== '--check' || args.length < 2 || args.slice(1).some((f) => !kindOf(f))) {
    console.error(USAGE);
    process.exit(2);
  }
  let bad = 0;
  for (const file of args.slice(1)) {
    const kind = kindOf(file);
    let buf;
    try {
      buf = readFileSync(file);
    } catch (err) {
      console.error(`✗ ${file} could not be read (${err.code ?? err.message}).`);
      bad = 1;
      continue;
    }
    if (isAstro(kind, buf)) {
      console.error(astroMessage(file, `public/favicon.${kind}`, kind, false));
      bad = 1;
    } else if (!(kind === 'svg' ? startsLikeSvg(buf) : startsLikeIco(buf))) {
      console.error(`✗ ${file} is not an icon: it does not start like ${kind === 'svg' ? 'an SVG' : 'an ICO'} file.`);
      bad = 1;
    } else {
      console.log(`✓ ${file} is not Astro's default icon`);
    }
  }
  process.exit(bad);
}

// The build: both files are checked before the exit. dist/ goes so no deploy can find it:
// without it `wrangler deploy` stops on the missing assets folder.
let astroFound = false;
for (const kind of ['svg', 'ico']) {
  const file = `dist/favicon.${kind}`;
  if (existsSync(file) && isAstro(kind, readFileSync(file))) {
    console.error(astroMessage(file, `public/favicon.${kind}`, kind, true));
    astroFound = true;
  }
}
if (astroFound) {
  rmSync('dist', { recursive: true, force: true });
  process.exit(1);
}

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
