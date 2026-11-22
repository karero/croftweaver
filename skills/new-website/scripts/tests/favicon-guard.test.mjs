// Tests for the starter's scripts/build-marker.mjs, which refuses create-astro's default icons
// (and has --check for the launch check). Run on the starter with its real node_modules:
//   MAKE_ICONS_NODE_MODULES=<the starter's node_modules> node --test skills/new-website/scripts/tests/favicon-guard.test.mjs
// template-tests.yml runs it. It is not in `make check`, which installs no packages.
//
// The Astro files in fixtures/favicon/ are Astro's real ones (see the README there). Expected
// verdicts, exit codes and file contents are written here by hand. The first group runs the
// commands a site's owner and Cloudflare run (npm run verify, build, deploy:live, wrangler) in a
// copy of the starter; the rest run the script as a program in a temp folder.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import {
  cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, symlinkSync, writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TEMPLATE = path.resolve(HERE, '..', '..', 'templates', 'astro');
const FIX = path.join(HERE, 'fixtures', 'favicon');
const NODE_MODULES = process.env.MAKE_ICONS_NODE_MODULES;
assert.ok(NODE_MODULES && existsSync(path.join(NODE_MODULES, 'sharp')),
  'set MAKE_ICONS_NODE_MODULES to the starter\'s node_modules (npm ci in templates/astro)');
const SCRIPT = path.join(TEMPLATE, 'scripts', 'build-marker.mjs');
const make = await import(pathToFileURL(path.join(TEMPLATE, 'scripts', 'make-icons.mjs')).href);

const sha256 = (buf) => createHash('sha256').update(buf).digest('hex');
const fx = (name) => readFileSync(path.join(FIX, name));
const made = [];
process.on('exit', () => {
  for (const dir of made) {
    try { rmSync(dir, { recursive: true, force: true }); } catch { /* a locked temp folder must not fail the run */ }
  }
});
const tmp = (prefix) => {
  const dir = mkdtempSync(path.join(tmpdir(), `favicon-guard-${prefix}-`));
  made.push(dir);
  return dir;
};
const ls = (dir) => readdirSync(dir).sort();

// Astro's files, by the blob id in their names; each with the size and SHA-256 the file has on
// GitHub (read 2026-11-18), so a fixture damaged by a line-ending change fails here first.
const ASTRO = {
  svg2023: { file: 'astro-minimal-favicon-f157bd1c.svg', bytes: 749, sha: '2d7a310283d6f9cc753210d83224cd6db6348cb82a5536348884e5831d46203f' },
  svg2022: { file: 'astro-minimal-favicon-0f390629.svg', bytes: 873, sha: 'dddac3870e66889496da35eed0f2ae5c3393efb45edf6ac349c8e08a4f617918' },
  ico2026: { file: 'astro-minimal-favicon-7f48a94d.ico', bytes: 655, sha: '09d2ac08d8cca9b6e1f90221f345a8c4dd0371c64a0dc52b6f96fc589b1e3d67' },
  ico2021: { file: 'astro-minimal-favicon-578ad458.ico', bytes: 4286, sha: '5af608ecd60d93abd453f78896e95a7c8c0a2c632a92a10e57f19423f333bc46' },
  svgo2023: { file: 'astro-minimal-favicon-f157bd1c.svgo-4.1.0.svg', bytes: 644, sha: 'c98ef972cd0a097ef32ad0f6d17e08d8e015a630a43b87be015e70d6d329dc32' },
  svgo2022: { file: 'astro-minimal-favicon-0f390629.svgo-4.1.0.svg', bytes: 787, sha: 'd7adbb88b727be7b4df28b8a98f9f48699168ce20504faea2eaf3483ebda1d02' },
  abs2023: { file: 'astro-minimal-favicon-f157bd1c.svgo-4.1.0-absolute.svg', bytes: 770, sha: 'dc3e867993b0205e6a569ca09101e4164a2fc0cbd12115064c99b39b5aa0756f' },
  abs2022: { file: 'astro-minimal-favicon-0f390629.svgo-4.1.0-absolute.svg', bytes: 885, sha: '6d0ea9fa154171a5efd30d0af01cd99f7f8902c958ad9fc037958f9a46b96ae1' },
};
const astro = (key) => fx(ASTRO[key].file);
const astroText = (key) => astro(key).toString('utf8');

// Environment for every spawned process: nothing of the caller's Cloudflare setup.
function cleanEnv(extra = {}) {
  const env = { ...process.env };
  for (const k of Object.keys(env)) if (/^(CF_|CLOUDFLARE_|WORKERS_CI|SITE_TEST_BUILD)/.test(k)) delete env[k];
  return { ...env, ASTRO_TELEMETRY_DISABLED: '1', WRANGLER_SEND_METRICS: 'false', ...extra };
}

const MARKER_SHA = '0123456789abcdef0123456789abcdef01234567';
// The script as a program, in a folder of its own; it reads dist/ relative to that folder.
const marker = (cwd, ...args) => spawnSync(process.execPath, [SCRIPT, ...args], {
  cwd, encoding: 'utf8', env: cleanEnv({ CF_PAGES_COMMIT_SHA: MARKER_SHA }),
});

// A folder whose dist/ holds the given files.
function distWith(files) {
  const dir = tmp('dist');
  mkdirSync(path.join(dir, 'dist'));
  for (const [name, body] of Object.entries(files)) writeFileSync(path.join(dir, 'dist', name), body);
  return dir;
}

// ---- icons that are the site's own ----------------------------------------------------------

// The site's name must not be the starter's "Example" before make-icons.mjs will draw a letter.
function nameTheSite(site) {
  const file = path.join(site, 'src/config.ts');
  const text = readFileSync(file, 'utf8');
  assert.ok(text.includes("  name: 'Example',"), 'the starter\'s config.ts has its placeholder name');
  writeFileSync(file, text.replace("  name: 'Example',", "  name: 'Krume',"));
}

// make-icons.mjs --setup run on a site with no icons (the starter ships none), as a new site does.
function siteWithCopyOfStarter() {
  const site = tmp('site');
  for (const rel of ['src/config.ts', 'src/styles/global.css', 'package.json', 'public', 'scripts/make-icons.mjs']) {
    cpSync(path.join(TEMPLATE, rel), path.join(site, rel), { recursive: true });
  }
  symlinkSync(NODE_MODULES, path.join(site, 'node_modules'));
  nameTheSite(site);
  return site;
}
let ownIconsCache;
function ownIcons() {
  if (!ownIconsCache) {
    const site = siteWithCopyOfStarter();
    const r = spawnSync(process.execPath, ['scripts/make-icons.mjs', '--setup'], { cwd: site, encoding: 'utf8' });
    assert.equal(r.status, 0, r.stderr);
    ownIconsCache = { svg: readFileSync(path.join(site, 'public/favicon.svg')), ico: readFileSync(path.join(site, 'public/favicon.ico')) };
  }
  return ownIconsCache;
}
const brandKitSvg = () => readFileSync(path.resolve(HERE, '..', '..', '..', 'website-brand-kit', 'scripts', 'tests', 'fixtures', 'matplotlib-3.11.2-svg11-doctype.svg'));

// ---- the fixtures are Astro's files, byte for byte -------------------------------------------

test('the fixtures are Astro\'s files as read: size and SHA-256', () => {
  for (const [key, want] of Object.entries(ASTRO)) {
    const buf = astro(key);
    assert.equal(buf.length, want.bytes, `${want.file} size`);
    assert.equal(sha256(buf), want.sha, `${want.file} SHA-256`);
  }
});

// ---- the recogniser, as a program (S4, S5, S6) -------------------------------------------------

const reindented = (text) => text.replace(/^[ \t]+/gm, '\t\t');
// An editor that wraps long path data: a line break and indent at every fourth space inside d="…".
const wrapped = (text) => text.replace(/ d="([^"]*)"/g, (_, d) => ` d="${d.split(' ').map((w, i) => (i && i % 4 === 0 ? `\n      ${w}` : w)).join(' ')}"`);

const REFUSED_SVG = [
  ['the 2023 logo as Astro ships it', () => astro('svg2023')],
  ['the 2023 logo with Windows line endings', () => astroText('svg2023').replace(/\n/g, '\r\n')],
  ['the 2023 logo re-indented', () => reindented(astroText('svg2023'))],
  ['the 2023 logo with its path wrapped over lines', () => wrapped(astroText('svg2023'))],
  ['the 2023 logo after svgo 4.1.0', () => astro('svgo2023')],
  ['the 2022 logo as Astro ships it', () => astro('svg2022')],
  ['the 2022 logo with Windows line endings', () => astroText('svg2022').replace(/\n/g, '\r\n')],
  ['the 2022 logo after svgo 4.1.0', () => astro('svgo2022')],
  // svgo's path rewriting can change the path data: with forceAbsolutePath the opening is another one.
  ['the 2023 logo after svgo 4.1.0 with forceAbsolutePath', () => astro('abs2023')],
  ['the 2022 logo after svgo 4.1.0 with forceAbsolutePath', () => astro('abs2022')],
  // A "<!--" inside CDATA or <?…?> must not hide the real path that follows it.
  ['the 2023 logo with a "<!--" in CDATA before it and a comment after', () => astroText('svg2023')
    .replace(/(<svg[^>]*>)/, '$1<metadata><![CDATA[<!--]]></metadata>').replace('</svg>', '<!-- end --></svg>')],
  ['the 2023 logo with a "<!--" in <?…?> before it and a comment after', () => astroText('svg2023')
    .replace(/(<svg[^>]*>)/, '$1<?note <!-- ?>').replace('</svg>', '<!-- end --></svg>')],
  // A self-closing <title/> has no content to drop: it must not run on to a later </title>.
  ['the 2023 logo between a self-closing <title/> and a later <title>', () => astroText('svg2023')
    .replace(/(<svg[^>]*>)/, '$1<title/>').replace('</svg>', '<title>Logo</title></svg>')],
  ['the 2023 logo between a self-closing <title data-note=">"/> and a later <title>', () => astroText('svg2023')
    .replace(/(<svg[^>]*>)/, '$1<title data-note=">"/>').replace('</svg>', '<title>Logo</title></svg>')],
  // An element that never closes drops nothing: the path after it is still read.
  ['the 2023 logo after an unclosed <desc>', () => astroText('svg2023').replace(/(<svg[^>]*>)/, '$1<desc>')],
  ['the 2023 logo after an unclosed <!--', () => astroText('svg2023').replace(/(<svg[^>]*>)/, '$1<!-- ')],
];
const REFUSED_ICO = [
  ['the 2026 icon (a PNG with an .ico name)', () => astro('ico2026')],
  ['the 2021 icon (a real ICO)', () => astro('ico2021')],
];

for (const [name, body] of REFUSED_SVG) {
  test(`S4: the build stops for ${name}`, () => {
    const dir = distWith({ 'favicon.svg': body() });
    const r = marker(dir);
    assert.equal(r.status, 1);
    assert.match(r.stderr, /^✗ dist\/favicon\.svg is Astro's default icon \(public\/favicon\.svg, from create-astro\)\./);
    assert.match(r.stderr, /make-icons\.mjs --setup/);
    assert.match(r.stderr, /website-brand-kit/);
    assert.equal(r.stdout, '', 'nothing on stdout, where Playwright would hide it');
    assert.deepEqual(ls(dir), [], 'dist/ is removed, so no deploy finds a build');
  });
}
for (const [name, body] of REFUSED_ICO) {
  test(`the build stops for ${name}`, () => {
    const dir = distWith({ 'favicon.ico': body() });
    const r = marker(dir);
    assert.equal(r.status, 1);
    assert.match(r.stderr, /^✗ dist\/favicon\.ico is Astro's default icon \(public\/favicon\.ico, from create-astro\)\./);
    assert.match(r.stderr, /replace public\/favicon\.ico by hand with an ICO/);
    assert.deepEqual(ls(dir), []);
  });
}

// Astro's path as text, outside a d="…" attribute, draws nothing: a site's own icon that holds it
// (in its metadata, say) is not Astro's icon and must build.
const astroPath = () => /\sd="([^"]*)"/.exec(astroText('svg2023'))[1];
for (const [where, wrap] of [
  ['<metadata>', (p) => `<metadata>${p}</metadata>`],
  ['<desc>', (p) => `<desc>${p}</desc>`],
  ['a CDATA section', (p) => `<style><![CDATA[${p}]]></style>`],
  ['a d="…" written in a CDATA section', (p) => `<style><![CDATA[ d="${p}" ]]></style>`],
  ['a d="…" written in <?…?>', (p) => `<?note d="${p}"?>`],
  ['a d="…" written in <desc>', (p) => `<desc>Example d="${p}"</desc>`],
  ['a d="…" written in <title>', (p) => `<title>Example d='${p}'</title>`],
  ['a d="…" written in <metadata>', (p) => `<metadata><note d="${p}"/></metadata>`],
  ['a d="…" written in <desc> after a self-closing <title/>', (p) => `<title/><desc>d="${p}"</desc>`],
  ['a d="…" in a <desc> whose CDATA holds a "</desc>"', (p) => `<desc><![CDATA[</desc> d="${p}"]]></desc>`],
  ['a d="…" in a <desc> whose comment holds a "</desc>"', (p) => `<desc><!-- </desc> -->d="${p}"</desc>`],
]) {
  test(`Astro's path inside ${where} of the site's own icon does not stop the build`, () => {
    const own = ownIcons().svg.toString('utf8').replace(/(<svg[^>]*>)/, `$1${wrap(astroPath())}`);
    assert.ok(own.includes(astroPath()), 'the path is in the file');
    const dir = distWith({ 'favicon.svg': own });
    const r = marker(dir);
    assert.equal(r.status, 0, r.stderr);
    assert.ok(existsSync(path.join(dir, 'dist', 'build.txt')));
  });
}

// A file of many unclosed elements is read in one pass: a quadratic scan took a minute on 300 KB.
test('many unclosed <desc> and <!-- in the site\'s own icon do not stall the build', () => {
  const junk = '<desc>'.repeat(20_000) + '<!-- '.repeat(20_000);
  const own = ownIcons().svg.toString('utf8').replace(/(<svg[^>]*>)/, `$1${junk}`);
  const dir = distWith({ 'favicon.svg': own });
  const r = spawnSync(process.execPath, [SCRIPT], {
    cwd: dir, encoding: 'utf8', env: cleanEnv({ CF_PAGES_COMMIT_SHA: MARKER_SHA }), timeout: 30_000,
  });
  assert.equal(r.status, 0, r.stderr);
});

test('a site without scripts/make-icons.mjs is not told to run it', () => {
  const dir = distWith({ 'favicon.svg': astro('svg2023') });
  mkdirSync(path.join(dir, 'scripts'));
  cpSync(SCRIPT, path.join(dir, 'scripts', 'build-marker.mjs'));
  const r = spawnSync(process.execPath, ['scripts/build-marker.mjs'], { cwd: dir, encoding: 'utf8', env: cleanEnv() });
  assert.equal(r.status, 1);
  assert.match(r.stderr, /Astro's default icon/);
  assert.doesNotMatch(r.stderr, /make-icons\.mjs --setup/);
  assert.match(r.stderr, /This site has no scripts\/make-icons\.mjs/);
  assert.match(r.stderr, /website-brand-kit/);
});

test('S6: Astro\'s ICO beside the site\'s own SVG: the build stops and names favicon.ico alone', () => {
  const dir = distWith({ 'favicon.svg': ownIcons().svg, 'favicon.ico': astro('ico2026') });
  const r = marker(dir);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /dist\/favicon\.ico is Astro's default icon/);
  assert.doesNotMatch(r.stderr, /favicon\.svg/);
  assert.deepEqual(ls(dir), []);
});

test('both files are Astro\'s: one block each, in one run', () => {
  const dir = distWith({ 'favicon.svg': astro('svg2023'), 'favicon.ico': astro('ico2026') });
  const r = marker(dir);
  assert.equal(r.status, 1);
  assert.equal(r.stderr.match(/is Astro's default icon/g).length, 2);
  assert.match(r.stderr, /dist\/favicon\.svg/);
  assert.match(r.stderr, /dist\/favicon\.ico/);
  assert.deepEqual(ls(dir), []);
});

const PASSING = [
  ['make-icons.mjs output', () => ({ 'favicon.svg': ownIcons().svg, 'favicon.ico': ownIcons().ico })],
  ['a brand-kit SVG', () => ({ 'favicon.svg': brandKitSvg(), 'favicon.ico': ownIcons().ico })],
  ['only an SVG of the site\'s own', () => ({ 'favicon.svg': ownIcons().svg })],
  ['only an ICO of the site\'s own', () => ({ 'favicon.ico': ownIcons().ico })],
  ['no favicon at all', () => ({})],
  // Astro's outline inside a comment is not drawn, so this is a circle, not Astro's icon.
  ['a circle with Astro\'s outline in a comment', () => ({
    'favicon.svg': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><!-- ${astroText('svg2023')} --><circle cx="5" cy="5" r="4"/></svg>`,
  })],
];
for (const [name, files] of PASSING) {
  test(`S5: the build passes with ${name} and writes build.txt`, () => {
    const dir = distWith(files());
    const r = marker(dir);
    assert.equal(r.status, 0, r.stderr);
    assert.equal(r.stderr, '');
    assert.equal(readFileSync(path.join(dir, 'dist', 'build.txt'), 'utf8'), `${MARKER_SHA}\n`);
  });
}

// ---- --check: the same verdicts on files, and nothing written ------------------------------------

// A folder to run in (empty) and a folder with the files to look at.
function check(files) {
  const cwd = tmp('cwd');
  const filesDir = tmp('files');
  const paths = Object.entries(files).map(([name, body]) => {
    writeFileSync(path.join(filesDir, name), body);
    return path.join(filesDir, name);
  });
  const r = marker(cwd, '--check', ...paths);
  assert.deepEqual(ls(cwd), [], '--check writes nothing');
  return r;
}

for (const [name, body] of REFUSED_SVG) {
  test(`--check refuses ${name}`, () => {
    const r = check({ 'favicon.svg': body() });
    assert.equal(r.status, 1);
    assert.match(r.stderr, /favicon\.svg is Astro's default icon/);
    assert.doesNotMatch(r.stderr, /not an icon/);
  });
}
for (const [name, body] of REFUSED_ICO) {
  test(`--check refuses ${name}`, () => {
    const r = check({ 'favicon.ico': body() });
    assert.equal(r.status, 1);
    assert.match(r.stderr, /favicon\.ico is Astro's default icon/);
    assert.doesNotMatch(r.stderr, /not an icon/, 'a PNG named .ico is Astro\'s, and says so');
  });
}
test('--check on two files refuses when either is Astro\'s', () => {
  const r = check({ 'favicon.svg': ownIcons().svg, 'favicon.ico': astro('ico2026') });
  assert.equal(r.status, 1);
  assert.match(r.stderr, /favicon\.ico is Astro's default icon/);
});

const NOT_ICONS = [
  ['an HTML page starting <!DOCTYPE html>', '<!DOCTYPE html>\n<html><body>Not found</body></html>\n'],
  ['an HTML page after a BOM and whitespace', '﻿ \n\t<html><body>Not found</body></html>\n'],
  ['an HTML page whose body holds an <svg>, after a comment', '<!-- x --><html><body><svg></svg></body></html>'],
  ['an SVG whose comment never ends', '<!-- <svg></svg>'],
  ['an empty file', ''],
];
for (const [name, body] of NOT_ICONS) {
  for (const file of ['favicon.svg', 'favicon.ico']) {
    test(`--check: ${name}, saved as ${file}, is not an icon`, () => {
      const r = check({ [file]: body });
      assert.equal(r.status, 1);
      assert.match(r.stderr, new RegExp(`${file.replace('.', '\\.')} is not an icon`));
      assert.doesNotMatch(r.stderr, /Astro's default icon/);
    });
  }
}

const OWN_SVGS = [
  ['make-icons.mjs output', () => ownIcons().svg],
  ['a brand-kit SVG (an XML declaration, a DOCTYPE)', () => brandKitSvg()],
  ['an SVG with an XML declaration', () => '<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg"/>'],
  ['an SVG with a stylesheet instruction', () => '<?xml version="1.0"?>\n<?xml-stylesheet href="a.css" type="text/css"?>\n<svg xmlns="http://www.w3.org/2000/svg"/>'],
  ['an SVG with a comment after the DOCTYPE', () => '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n<!-- made by hand -->\n<svg xmlns="http://www.w3.org/2000/svg"/>'],
  ['an SVG after a BOM', () => '﻿<svg xmlns="http://www.w3.org/2000/svg"></svg>'],
];
for (const [name, body] of OWN_SVGS) {
  test(`--check passes ${name}`, () => {
    const r = check({ 'favicon.svg': body() });
    assert.equal(r.status, 0, r.stderr);
    assert.equal(r.stderr, '');
  });
}
test('--check passes make-icons.mjs\'s ICO', () => {
  const r = check({ 'favicon.ico': ownIcons().ico });
  assert.equal(r.status, 0, r.stderr);
});

test('--check with no file exits 2 with a usage line and writes nothing', () => {
  const cwd = tmp('cwd');
  const r = marker(cwd, '--check');
  assert.equal(r.status, 2);
  assert.match(r.stderr, /^usage: node scripts\/build-marker\.mjs \[--check /);
  assert.deepEqual(ls(cwd), []);
});

test('a file that is not .svg or .ico, or arguments without --check, exit 2 and write nothing', () => {
  for (const args of [['--check', 'logo.png'], ['favicon.svg'], ['--verbose']]) {
    const cwd = tmp('cwd');
    const r = marker(cwd, ...args);
    assert.equal(r.status, 2, args.join(' '));
    assert.match(r.stderr, /^usage: /);
    assert.deepEqual(ls(cwd), []);
  }
});

test('--check on a file that is not there exits 1 and says so', () => {
  const cwd = tmp('cwd');
  const r = marker(cwd, '--check', path.join(cwd, 'gone.svg'));
  assert.equal(r.status, 1);
  assert.match(r.stderr, /gone\.svg could not be read/);
});

// The launch check probes a site's copy with `--check` and no file. A copy from before 0.36
// reads no arguments, so the probe must not look like a pass: it does not exit 2, and it writes nothing.
test('the launch check\'s probe tells a pre-0.36 build-marker.mjs from this one', () => {
  const cwd = tmp('cwd');
  const old = spawnSync(process.execPath, [path.join(FIX, 'build-marker.pre-0.36.mjs'), '--check'], { cwd, encoding: 'utf8', env: cleanEnv() });
  assert.notEqual(old.status, 2, 'the old script is not mistaken for the new one');
  assert.deepEqual(ls(cwd), [], 'and left nothing behind');
  assert.equal(marker(cwd, '--check').status, 2);
});

// ---- the lists agree (S8's tie) -------------------------------------------------------------------

test('every hash in make-icons.mjs SCAFFOLD_FAVICONS has a fixture, and the guard refuses it', () => {
  const byHash = new Map(readdirSync(FIX).map((name) => [sha256(readFileSync(path.join(FIX, name))), name]));
  for (const [rel, hashes] of Object.entries(make.SCAFFOLD_FAVICONS)) {
    for (const hash of hashes) {
      const name = byHash.get(hash);
      assert.ok(name, `${rel}: no fixture has the hash ${hash}`);
      const r = check({ [path.basename(rel)]: readFileSync(path.join(FIX, name)) });
      assert.equal(r.status, 1, `${name} is refused`);
      assert.match(r.stderr, /is Astro's default icon/);
    }
  }
});

test('make-icons --setup replaces the two current Astro files, and the guard then passes them', () => {
  const site = siteWithCopyOfStarter();
  writeFileSync(path.join(site, 'public/favicon.svg'), astro('svg2023'));
  writeFileSync(path.join(site, 'public/favicon.ico'), astro('ico2026'));
  const r = spawnSync(process.execPath, ['scripts/make-icons.mjs', '--setup'], { cwd: site, encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  assert.match(readFileSync(path.join(site, 'public/favicon.svg'), 'utf8'), /^<!-- Made by scripts\/make-icons\.mjs: /);
  const after = check({ 'favicon.svg': readFileSync(path.join(site, 'public/favicon.svg')), 'favicon.ico': readFileSync(path.join(site, 'public/favicon.ico')) });
  assert.equal(after.status, 0, after.stderr);
});

// ---- through the commands production runs (S1, S3, S6) ------------------------------------------------
// A copy of the starter set up as tests/check_deploy.sh sets its copy up: a git repo on the
// production branch with a real Worker name and one commit. node_modules is a folder of links to
// the real one, so `npm run verify` finds the install it wants and does not run `npm ci`.

const GIT_ENV = { GIT_AUTHOR_NAME: 'check', GIT_AUTHOR_EMAIL: 'check@example.com', GIT_COMMITTER_NAME: 'check', GIT_COMMITTER_EMAIL: 'check@example.com' };
const git = (cwd, ...args) => {
  const r = spawnSync('git', ['-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', ...args], { cwd, encoding: 'utf8', env: cleanEnv(GIT_ENV) });
  assert.equal(r.status, 0, `git ${args.join(' ')}: ${r.stderr}`);
  return r.stdout.trim();
};

function productionCopy() {
  const copy = tmp('copy');
  cpSync(TEMPLATE, copy, {
    recursive: true,
    filter: (src) => !/^(node_modules|dist|\.astro|\.git)$/.test(path.relative(TEMPLATE, src).split(path.sep)[0]),
  });
  const gitignore = existsSync(path.join(TEMPLATE, '.gitignore')) ? path.join(TEMPLATE, '.gitignore') : path.join(TEMPLATE, '..', '.gitignore');
  cpSync(gitignore, path.join(copy, '.gitignore'));
  mkdirSync(path.join(copy, 'node_modules'));
  for (const name of readdirSync(NODE_MODULES)) {
    if (name !== '.verify-lock-hash') symlinkSync(path.join(NODE_MODULES, name), path.join(copy, 'node_modules', name));
  }
  // The stamp `npm run verify` looks for: the hash of the lockfile and package.json it would install from.
  const stamp = createHash('sha256').update(readFileSync(path.join(copy, 'package-lock.json'))).update('\0').update(readFileSync(path.join(copy, 'package.json')));
  writeFileSync(path.join(copy, 'node_modules', '.verify-lock-hash'), `${stamp.digest('hex')}\n`);
  // A real Worker name: the starter's placeholder is refused by deploy.sh.
  const conf = path.join(copy, 'wrangler.jsonc');
  const text = readFileSync(conf, 'utf8');
  assert.ok(text.includes('"name": "example-site"'));
  writeFileSync(conf, text.replace('"name": "example-site"', '"name": "favicon-guard-site"'));
  const branch = readFileSync(path.join(copy, 'src/config.ts'), 'utf8').match(/^export const PROD_BRANCH = '([^']+)'/m)[1];
  git(copy, 'init', '-q', '-b', branch);
  mkdirSync(path.join(copy, '.git', 'info'), { recursive: true });
  writeFileSync(path.join(copy, '.git', 'info', 'exclude'), 'node_modules\n');
  // A new site's icons, as `node scripts/make-icons.mjs --setup` draws them.
  nameTheSite(copy);
  const r = spawnSync(process.execPath, ['scripts/make-icons.mjs', '--setup'], { cwd: copy, encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  git(copy, 'add', '-A');
  git(copy, 'commit', '-q', '-m', 'a new site');
  return copy;
}

// An npm script in the copy, as the owner (or Cloudflare) runs it; output is stdout then stderr.
function npmRun(copy, script, ...extra) {
  const r = spawnSync('npm', ['run', script, ...extra], { cwd: copy, encoding: 'utf8', env: cleanEnv(), timeout: 600_000, maxBuffer: 64 * 1024 * 1024 });
  return { status: r.status, out: r.stdout + r.stderr, stderr: r.stderr };
}

test('S1, S3, S6: with Astro\'s icons in public/, verify, build and deploy:live stop at the build; wrangler finds no dist/', { timeout: 1_500_000 }, () => {
  const copy = productionCopy();
  const MESSAGE = /✗ dist\/favicon\.svg is Astro's default icon \(public\/favicon\.svg, from create-astro\)\./;
  const MESSAGE_ICO = /✗ dist\/favicon\.ico is Astro's default icon \(public\/favicon\.ico, from create-astro\)\./;
  writeFileSync(path.join(copy, 'public/favicon.svg'), astro('svg2023'));
  writeFileSync(path.join(copy, 'public/favicon.ico'), astro('ico2026'));
  git(copy, 'add', '-A');
  git(copy, 'commit', '-q', '-m', 'Astro\'s icons');

  // What the pre-push gate runs.
  const verify = npmRun(copy, 'verify');
  assert.notEqual(verify.status, 0, verify.out);
  assert.match(verify.out, MESSAGE, 'verify shows the message');
  assert.match(verify.out, MESSAGE_ICO);

  // What Cloudflare runs.
  const build = npmRun(copy, 'build');
  assert.equal(build.status, 1, build.out);
  assert.match(build.stderr, MESSAGE, 'on stderr');
  assert.match(build.stderr, MESSAGE_ICO);
  assert.equal(existsSync(path.join(copy, 'dist')), false, 'dist/ is gone');
  const wrangler = spawnSync('npx', ['wrangler', 'deploy', '--dry-run'], { cwd: copy, encoding: 'utf8', env: cleanEnv() });
  assert.notEqual(wrangler.status, 0, 'wrangler stops on the missing dist/');
  assert.match(wrangler.stdout + wrangler.stderr, /dist|assets|exist/i);

  // What an owner without GitHub runs.
  const deploy = npmRun(copy, 'deploy:live', '--', '--dry-run');
  assert.notEqual(deploy.status, 0, deploy.out);
  assert.match(deploy.out, MESSAGE);
  assert.match(deploy.out, /The build failed\. Nothing was deployed\./);
  assert.doesNotMatch(deploy.out, /wrangler deploy/, 'Wrangler was never reached');

  // S6, through the same build: the site's own SVG beside Astro's ICO.
  writeFileSync(path.join(copy, 'public/favicon.svg'), ownIcons().svg);
  git(copy, 'add', '-A');
  git(copy, 'commit', '-q', '-m', 'own SVG, Astro\'s ICO');
  const icoOnly = npmRun(copy, 'build');
  assert.equal(icoOnly.status, 1, icoOnly.out);
  assert.match(icoOnly.stderr, MESSAGE_ICO);
  assert.doesNotMatch(icoOnly.stderr, /favicon\.svg/);

  // S5, through the same build: the site's own icons build as before.
  writeFileSync(path.join(copy, 'public/favicon.ico'), ownIcons().ico);
  git(copy, 'add', '-A');
  git(copy, 'commit', '-q', '-m', 'own icons');
  const good = npmRun(copy, 'build');
  assert.equal(good.status, 0, good.out);
  assert.equal(readFileSync(path.join(copy, 'dist/build.txt'), 'utf8'), `${git(copy, 'rev-parse', 'HEAD')}\n`);
});
