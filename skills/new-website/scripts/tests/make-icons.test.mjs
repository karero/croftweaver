// Tests for the starter's scripts/make-icons.mjs, run on the starter with its real sharp:
//   MAKE_ICONS_NODE_MODULES=<the starter's node_modules> node --test skills/new-website/scripts/tests/make-icons.test.mjs
// template-tests.yml runs it. It is not in `make check`, which installs no packages.
//
// Each test makes a small site (the starter's config, stylesheet and public/ folder, the script, a
// stand-in for the scaffold's two favicons) in a temp folder and runs the script as a program.
// Expected letters, colours, sizes and pixels are written here by hand.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdtempSync, readFileSync, symlinkSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TEMPLATE = path.resolve(HERE, '..', '..', 'templates', 'astro');
const NODE_MODULES = process.env.MAKE_ICONS_NODE_MODULES;
assert.ok(NODE_MODULES && existsSync(path.join(NODE_MODULES, 'sharp')),
  'set MAKE_ICONS_NODE_MODULES to the starter\'s node_modules (npm ci in templates/astro), which holds sharp');
const sharp = createRequire(path.join(NODE_MODULES, 'x.js'))('sharp');
const script = await import(pathToFileURL(path.join(TEMPLATE, 'scripts', 'make-icons.mjs')).href);

const FILES = ['public/favicon.svg', 'public/favicon.ico', 'public/apple-touch-icon.png', 'public/icon-192.png',
  'public/icon-512.png', 'public/icon-maskable-512.png', 'public/images/logo.png'];
const sha = (buf) => createHash('sha256').update(buf).digest('hex');

// ---- a site to run the script in ---------------------------------------------------------

// The scaffold's own favicons are stood in for by bytes of no meaning: the script must not need to know them.
// name null leaves the starter's "Example".
function makeSite({ name = 'Krume', brand, modules = true, scaffold = true } = {}) {
  const site = mkdtempSync(path.join(tmpdir(), 'make-icons-'));
  for (const rel of ['src/config.ts', 'src/styles/global.css', 'package.json', 'public', 'scripts/make-icons.mjs']) {
    cpSync(path.join(TEMPLATE, rel), path.join(site, rel), { recursive: true });
  }
  if (modules) symlinkSync(NODE_MODULES, path.join(site, 'node_modules'));
  if (name !== null) edit(site, 'src/config.ts', "  name: 'Example',", `  name: ${JSON.stringify(name).replace(/^"|"$/g, "'")},`);
  if (brand) edit(site, 'src/styles/global.css', '  --brand: #000000;', `  --brand: ${brand};`);
  if (scaffold) {
    writeFileSync(path.join(site, 'public/favicon.svg'), '<svg xmlns="http://www.w3.org/2000/svg"><!-- scaffold stand-in --></svg>\n');
    writeFileSync(path.join(site, 'public/favicon.ico'), Buffer.from('scaffold stand-in'));
  }
  return site;
}

function edit(site, rel, from, to) {
  const file = path.join(site, rel);
  const text = readFileSync(file, 'utf8');
  assert.ok(text.includes(from), `${rel} has no "${from}"`);
  writeFileSync(file, text.replace(from, to));
}

const run = (site, ...args) => spawnSync(process.execPath, ['scripts/make-icons.mjs', ...args], { cwd: site, encoding: 'utf8' });
const read = (site, rel) => readFileSync(path.join(site, rel));
const have = (site) => FILES.filter((rel) => existsSync(path.join(site, rel)));
const record = (site) => JSON.parse(read(site, 'scripts/icons-made.json'));

// ---- reading the files back, by hand -------------------------------------------------------

const pngSize = (buf) => {
  assert.equal(buf.subarray(0, 8).toString('hex'), '89504e470d0a1a0a', 'a PNG signature');
  return [buf.readUInt32BE(16), buf.readUInt32BE(20)];
};

// The frames of an ICO: header 6 bytes, 16 bytes per entry, each frame a PNG; the last frame ends the file.
function icoFrames(buf) {
  assert.deepEqual([buf.readUInt16LE(0), buf.readUInt16LE(2)], [0, 1], 'an ICO header');
  const n = buf.readUInt16LE(4);
  const frames = [];
  let end = 6 + 16 * n;
  for (let i = 0; i < n; i++) {
    const at = 6 + 16 * i;
    const [w, h, planes, bits, size, offset] = [buf[at], buf[at + 1], buf.readUInt16LE(at + 4), buf.readUInt16LE(at + 6), buf.readUInt32LE(at + 8), buf.readUInt32LE(at + 12)];
    assert.deepEqual([planes, bits], [1, 32]);
    assert.equal(offset, end, 'frames follow each other');
    end = offset + size;
    const png = buf.subarray(offset, end);
    assert.deepEqual(pngSize(png), [w, h], 'the entry and its PNG agree');
    frames.push(w);
  }
  assert.equal(end, buf.length, 'nothing after the last frame');
  return frames;
}

async function pixel(buf, x, y) {
  const { data, info } = await sharp(buf).raw().toBuffer({ resolveWithObject: true });
  const at = (y * info.width + x) * info.channels;
  return [data[at], data[at + 1], data[at + 2]];
}
const near = (got, want, why) => assert.ok(got.every((v, i) => Math.abs(v - want[i]) <= 2), `${why}: got ${got}, want ${want}`);

function assertSevenFiles(site) {
  assert.deepEqual(have(site), FILES, 'all seven files exist');
  assert.deepEqual(pngSize(read(site, 'public/apple-touch-icon.png')), [180, 180]);
  assert.deepEqual(pngSize(read(site, 'public/icon-192.png')), [192, 192]);
  assert.deepEqual(pngSize(read(site, 'public/icon-512.png')), [512, 512]);
  assert.deepEqual(pngSize(read(site, 'public/icon-maskable-512.png')), [512, 512]);
  assert.deepEqual(pngSize(read(site, 'public/images/logo.png')), [512, 512]);
  assert.deepEqual(read(site, 'public/images/logo.png'), read(site, 'public/icon-512.png'), 'logo.png is the 512 icon');
  assert.deepEqual(icoFrames(read(site, 'public/favicon.ico')), [16, 32, 48, 64]);
  assert.match(read(site, 'public/favicon.svg').toString(), /^<!-- Made by scripts\/make-icons\.mjs: /);
}

// ---- S1: the starter's own colour --------------------------------------------------------

test('S1: a new site gets its initial in white on the starter\'s black, and a record', async () => {
  const site = makeSite({ name: 'Bäckerei Krume' });
  const r = run(site, '--setup');
  assert.equal(r.status, 0, r.stderr);
  assertSevenFiles(site);
  const svg = read(site, 'public/favicon.svg').toString();
  assert.ok(svg.startsWith('<!-- Made by scripts/make-icons.mjs: the letter B on #000000.'), svg.split('\n')[0]);
  const png = read(site, 'public/icon-512.png');
  near(await pixel(png, 20, 20), [0, 0, 0], 'the tile');
  near(await pixel(png, 72, 256), [0, 0, 0], 'plain tile between the edge and the letter: no outline');
  near(await pixel(png, 144, 330), [255, 255, 255], "the stem of the B, lower half");
  near(await pixel(png, 256, 330), [0, 0, 0], "the lower counter of the B is open");
  const rec = record(site);
  assert.deepEqual([rec.letter, rec.colour], [{ value: 'B', from: 'name' }, { value: '#000000', from: 'brand' }]);
  for (const rel of FILES) assert.deepEqual(rec.files[rel], [sha(read(site, rel))], rel);
});

// ---- S2, S3, S4: the letter --------------------------------------------------------------

test('S2, S3: the first letter or digit, accents folded, signs before it skipped', () => {
  const cases = [
    ['Ölmühle Rapp', 'O'], ['Straße', 'S'], ['Æble', 'A'], ['Østerbro', 'O'], ['Œuvre', 'O'], ['Łódź', 'L'],
    ['Đorđe', 'D'], ['Ðor', 'D'], ['élan', 'E'], ['bäckerei', 'B'], ['3D-Druck Weber', '3'], ['„Café Mohn“', 'C'],
    ['  - "x', 'X'], ['O' + String.fromCharCode(0x308) + 'l', 'O'],
  ];
  for (const [name, want] of cases) assert.equal(script.letterFor(name), want, name);
});

test('S4: a letter it has no drawing for, or none at all, is refused with the way out', () => {
  assert.throws(() => script.letterFor('Жар-птица'), (e) => e instanceof script.IconsError && e.message.includes('"Ж"') && e.message.includes('--letter X'));
  assert.throws(() => script.letterFor('„—“ ...'), (e) => e instanceof script.IconsError && e.message.includes('no letter or digit') && e.message.includes('--letter X'));
});

test('S4: run on such a name it writes nothing; with --letter it draws that letter', () => {
  const site = makeSite({ name: 'Жар-птица' });
  const r = run(site, '--setup');
  assert.equal(r.status, 1);
  assert.match(r.stderr, /"Ж"/);
  assert.deepEqual(have(site), ['public/favicon.svg', 'public/favicon.ico'], 'only the scaffold stand-ins');
  assert.ok(!existsSync(path.join(site, 'scripts/icons-made.json')));
  const again = run(site, '--setup', '--letter', 'x');
  assert.equal(again.status, 0, again.stderr);
  assert.match(read(site, 'public/favicon.svg').toString(), /the letter X on/);
  assert.deepEqual(record(site).letter, { value: 'X', from: 'flag' });
});

test('--letter and --colour must be one letter or digit and #rrggbb', () => {
  const site = makeSite();
  const refusals = [[['--letter', 'AB'], /--letter takes one letter/], [['--letter', 'Ж'], /--letter takes one letter/],
    [['--colour', 'red'], /--colour takes a colour/], [['--colour', '#fff'], /--colour takes a colour/], [['--nonsense'], /Unknown argument/]];
  for (const [args, message] of refusals) {
    const r = run(site, '--setup', ...args);
    assert.equal(r.status, 1, args.join(' '));
    assert.match(r.stderr, message);
    assert.deepEqual(have(site), ['public/favicon.svg', 'public/favicon.ico']);
  }
});

// ---- S5: the mark's colour ---------------------------------------------------------------

test('S5: black on a light tile, white on a dark one', () => {
  const cases = [['#f2d16b', '#000000'], ['#000000', '#ffffff'], ['#767676', '#ffffff'], ['#999999', '#000000'], ['#ffffff', '#000000']];
  for (const [tile, want] of cases) assert.equal(script.markColour(tile), want, tile);
});

test('S5: on #f2d16b the letter is black, in every file', async () => {
  const site = makeSite({ brand: '#f2d16b' });
  const r = run(site, '--setup');
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /in black on #f2d16b/);
  const png = read(site, 'public/icon-512.png');
  near(await pixel(png, 20, 20), [242, 209, 107], 'the tile');
  near(await pixel(png, 144, 256), [0, 0, 0], 'the stem of the K');
  near(await pixel(png, 72, 256), [242, 209, 107], 'plain tile between the edge and the letter: no outline');
  // The maskable icon draws the whole icon at 70 % on the tile colour: the K's stem lands at 178 across.
  const maskable = read(site, 'public/icon-maskable-512.png');
  near(await pixel(maskable, 178, 256), [0, 0, 0], 'the stem of the K, scaled to 70 %');
  near(await pixel(maskable, 127, 256), [242, 209, 107], 'plain tile left of the letter');
  near(await pixel(maskable, 20, 256), [242, 209, 107], 'the colour the drawing sits on');
});

test('a --brand that is not #rrggbb is refused, and --colour overrides it', () => {
  const site = makeSite({ brand: 'rgb(1, 2, 3)' });
  const r = run(site, '--setup');
  assert.equal(r.status, 1);
  assert.match(r.stderr, /not #rrggbb/);
  assert.deepEqual(have(site), ['public/favicon.svg', 'public/favicon.ico']);
  assert.equal(run(site, '--setup', '--colour', '#336699').status, 0);
  assert.deepEqual(record(site).colour, { value: '#336699', from: 'flag' });
});

// ---- S6: the name ------------------------------------------------------------------------

test('S6: the starter as shipped (name "Example") writes nothing and says to set SITE.name', () => {
  const site = makeSite({ name: null });
  const r = run(site, '--setup');
  assert.equal(r.status, 1);
  assert.match(r.stderr, /Set SITE\.name/);
  assert.deepEqual(have(site), ['public/favicon.svg', 'public/favicon.ico']);
});

test('S6: a [SLOT] as the name, or a name that is not one plain string, is refused', () => {
  for (const name of ['[SITE NAME]', '[Your Site]']) {
    const site = makeSite({ name });
    const r = run(site, '--setup');
    assert.equal(r.status, 1, name);
    assert.match(r.stderr, /Set SITE\.name/, name);
  }
  const site = makeSite({ name: null });
  edit(site, 'src/config.ts', "  name: 'Example',", "  name: 'A' + 'B',");
  const r = run(site, '--setup');
  assert.equal(r.status, 0, 'the import reads it as the string "AB"');
  const broken = makeSite({ name: null });
  edit(broken, 'src/config.ts', "  name: 'Example',", '  name: 42,');
  const refused = run(broken, '--setup');
  assert.equal(refused.status, 1, 'a number is not a name');
  assert.match(refused.stderr, /Set SITE\.name/);
});

test('S6: when config.ts cannot be imported, the name: line is read, and must be one quoted string', () => {
  // A line that makes the import fail at once, as an older Node does.
  const site = makeSite({ name: 'Krume' });
  edit(site, 'src/config.ts', 'export const SITE = {', "import './does-not-exist.js';\nexport const SITE = {");
  const r = run(site, '--setup');
  assert.equal(r.status, 0, r.stderr);
  assert.match(read(site, 'public/favicon.svg').toString(), /the letter K on/);
  const computed = makeSite({ name: null });
  edit(computed, 'src/config.ts', 'export const SITE = {', "import './does-not-exist.js';\nexport const SITE = {");
  edit(computed, 'src/config.ts', "  name: 'Example',", "  name: 'A' + 'B',");
  const refused = run(computed, '--setup');
  assert.equal(refused.status, 1);
  assert.match(refused.stderr, /Set SITE\.name/);
});

// ---- S7: no sharp ------------------------------------------------------------------------

test('S7: without sharp it writes nothing, gives the brand kit\'s advice and leaves package.json alone', () => {
  const site = makeSite({ modules: false });
  const before = read(site, 'package.json');
  const r = run(site, '--setup');
  assert.equal(r.status, 1);
  assert.match(r.stderr, /npm install --include=optional/);
  assert.match(r.stderr, /never adds sharp to the site's package\.json/);
  assert.deepEqual(have(site), ['public/favicon.svg', 'public/favicon.ico']);
  assert.ok(!existsSync(path.join(site, 'scripts/icons-made.json')));
  assert.deepEqual(read(site, 'package.json'), before);
});

// ---- S8: whose files these are -----------------------------------------------------------

const MARK = "<!-- Installed by the website-brand-kit skill (brand_intake.py install) from the logo it was given. When the site's colours change, the icons are drawn again from this file. -->\n";
const MARK_CURRENT = MARK.slice(0, -5) + ' The logo was given in currentColor and is drawn here in #1f5c3a. -->\n';
const MARK_CURRENT_OWN = MARK_CURRENT.slice(0, -5) + ' A part of it has that colour as its own. -->\n';

test('S8: without --setup the scaffold\'s favicons are not its own, and nothing is written', () => {
  const site = makeSite();
  const r = run(site);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /public\/favicon\.svg, public\/favicon\.ico/);
  assert.match(r.stderr, /--replace/);
  assert.deepEqual(have(site), ['public/favicon.svg', 'public/favicon.ico']);
  assert.ok(!existsSync(path.join(site, 'scripts/.icons-tmp')));
});

for (const [form, line] of [['MARK', MARK], ['MARK_CURRENT', MARK_CURRENT], ['MARK_CURRENT_OWN', MARK_CURRENT_OWN]]) {
  test(`S8: a brand-kit favicon (${form}) is named as the brand kit's, with or without --setup`, () => {
    for (const flags of [[], ['--setup']]) {
      const site = makeSite();
      const brandKit = line + '<svg xmlns="http://www.w3.org/2000/svg"/>\n';
      writeFileSync(path.join(site, 'public/favicon.svg'), brandKit);
      const r = run(site, ...flags);
      assert.equal(r.status, 1, flags.join(' '));
      assert.match(r.stderr, /brand kit/);
      assert.equal(read(site, 'public/favicon.svg').toString(), brandKit, 'untouched');
      assert.ok(!existsSync(path.join(site, 'public/icon-512.png')));
    }
  });
}

test('S8: --setup refuses a site where one of the other five files already exists', () => {
  const site = makeSite();
  writeFileSync(path.join(site, 'public/icon-512.png'), 'somebody else\'s picture');
  const r = run(site, '--setup');
  assert.equal(r.status, 1);
  assert.match(r.stderr, /--setup is for a new site/);
  assert.match(r.stderr, /public\/icon-512\.png/);
  assert.equal(read(site, 'public/icon-512.png').toString(), 'somebody else\'s picture');
});

test('S8: a file it did not make stops a plain run; --replace overrides', () => {
  const site = makeSite();
  assert.equal(run(site, '--setup').status, 0);
  const mine = read(site, 'public/icon-192.png');
  writeFileSync(path.join(site, 'public/icon-192.png'), 'drawn by hand');
  const r = run(site);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /public\/icon-192\.png/);
  assert.equal(read(site, 'public/icon-192.png').toString(), 'drawn by hand');
  assert.equal(run(site, '--replace').status, 0);
  assert.deepEqual(read(site, 'public/icon-192.png'), mine);
});

test('S8: a run on its own files works again, and an unreadable record is named', () => {
  const site = makeSite();
  assert.equal(run(site, '--setup').status, 0);
  assert.equal(run(site, '--colour', '#336699').status, 0, 'its own files are overwritten without a flag');
  assert.match(read(site, 'public/favicon.svg').toString(), /on #336699/);
  assertSevenFiles(site);
  writeFileSync(path.join(site, 'scripts/icons-made.json'), '{ not json');
  const r = run(site);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /scripts\/icons-made\.json cannot be read/);
});

// ---- a run stopped at each step of the write ------------------------------------------------

const STEPS = [
  'files-in-temp', 'record-with-both-in-temp', 'record-with-both',
  'renamed public/favicon.svg', 'renamed public/favicon.ico', 'renamed public/apple-touch-icon.png',
  'renamed public/icon-192.png', 'renamed public/icon-512.png', 'renamed public/icon-maskable-512.png',
  'renamed public/images/logo.png', 'record-final-in-temp', 'record-final',
];

const load = (site) => import(pathToFileURL(path.join(site, 'scripts/make-icons.mjs')).href);

test('a run lists exactly the steps this test stops at', async () => {
  const site = makeSite();
  const seen = [];
  await (await load(site)).makeIcons({ root: site, setup: true, checkpoint: async (step) => { seen.push(step); } });
  assert.deepEqual(seen, STEPS);
});

for (const step of STEPS) {
  test(`stopped after "${step}" on a new site: setting up again puts it right, without --replace`, async () => {
    const site = makeSite();
    await assert.rejects(
      (await load(site)).makeIcons({ root: site, setup: true, checkpoint: async (s) => { if (s === step) throw new Error('stopped'); } }),
      /stopped/);
    const r = run(site, '--setup');
    assert.equal(r.status, 0, `${step}: ${r.stderr}`);
    assertSevenFiles(site);
    const rec = record(site);
    for (const rel of FILES) assert.deepEqual(rec.files[rel], [sha(read(site, rel))], `${step}: ${rel}`);
    assert.ok(!existsSync(path.join(site, 'scripts/.icons-tmp')), 'the temporary folder is gone');
  });

  test(`stopped after "${step}" on a site with icons: a plain run puts it right, without --replace`, async () => {
    const site = makeSite();
    assert.equal(run(site, '--setup', '--letter', 'A', '--colour', '#336699').status, 0);
    await assert.rejects(
      (await load(site)).makeIcons({ root: site, letter: 'K', colour: '#aa3300', checkpoint: async (s) => { if (s === step) throw new Error('stopped'); } }),
      /stopped/);
    const r = run(site, '--letter', 'K', '--colour', '#aa3300');
    assert.equal(r.status, 0, `${step}: ${r.stderr}`);
    assertSevenFiles(site);
    assert.match(read(site, 'public/favicon.svg').toString(), /the letter K on #aa3300/);
    const rec = record(site);
    for (const rel of FILES) assert.deepEqual(rec.files[rel], [sha(read(site, rel))], `${step}: ${rel}`);
  });
}

// ---- S12's warnings ----------------------------------------------------------------------

test('S12: the icon test warns when --brand changed, and says what to run', async () => {
  const site = makeSite({ name: 'Krume' });
  assert.equal(run(site, '--setup').status, 0);
  const mod = await load(site);
  assert.deepEqual(await mod.staleReasons(site), [], 'fresh icons');
  edit(site, 'src/styles/global.css', '  --brand: #000000;', '  --brand: #112233;');
  const reasons = await mod.staleReasons(site);
  assert.equal(reasons.length, 1);
  assert.match(reasons[0], /#112233.*#000000.*node scripts\/make-icons\.mjs/);
});

test('S12: it warns when the name\'s letter changed (a fresh process reads the new name)', async () => {
  const site = makeSite({ name: 'Krume' });
  assert.equal(run(site, '--setup').status, 0);
  edit(site, 'src/config.ts', "  name: 'Krume',", "  name: 'Mohn',");
  const reasons = await (await load(site)).staleReasons(site);
  assert.equal(reasons.length, 1);
  assert.match(reasons[0], /starts with M but the icons show K/);
});

test('S12: it says nothing when one of the seven is not its own', async () => {
  const site = makeSite({ name: 'Krume' });
  assert.equal(run(site, '--setup').status, 0);
  edit(site, 'src/styles/global.css', '  --brand: #000000;', '  --brand: #112233;');
  writeFileSync(path.join(site, 'public/icon-192.png'), 'drawn by hand');
  assert.deepEqual(await (await load(site)).staleReasons(site), []);
});

test('S12: a --brand the script cannot read is a warning, not a failure', async () => {
  const site = makeSite({ name: 'Krume' });
  assert.equal(run(site, '--setup').status, 0);
  edit(site, 'src/styles/global.css', '  --brand: #000000;', '  --brand: rgb(17, 34, 51);');
  const reasons = await (await load(site)).staleReasons(site);
  assert.equal(reasons.length, 1);
  assert.match(reasons[0], /rgb\(17, 34, 51\).*not #rrggbb/);
  assert.ok(reasons[0].includes("--colour '#rrggbb'"), 'the colour in the hint is quoted, so a shell does not read it as a comment');
});

test('S12: the command it names is a plain run, and that run keeps a letter set with a flag', async () => {
  const site = makeSite({ name: 'Krume' });
  assert.equal(run(site, '--setup', '--letter', 'Z').status, 0);
  edit(site, 'src/styles/global.css', '  --brand: #000000;', '  --brand: #112233;');
  const reasons = await (await load(site)).staleReasons(site);
  assert.equal(reasons.length, 1);
  assert.match(reasons[0], /Run: node scripts\/make-icons\.mjs$/);
  assert.equal(run(site).status, 0);
  assert.match(read(site, 'public/favicon.svg').toString(), /the letter Z on #112233/);
  assert.deepEqual(record(site).letter, { value: 'Z', from: 'flag' });
});

test('a plain rerun keeps a letter and a colour given with flags, even on a name it cannot draw', () => {
  const site = makeSite({ name: 'Жар-птица' });
  assert.equal(run(site, '--setup', '--letter', 'Z', '--colour', '#336699').status, 0);
  const r = run(site);
  assert.equal(r.status, 0, r.stderr);
  assert.match(read(site, 'public/favicon.svg').toString(), /the letter Z on #336699/);
  assert.deepEqual(record(site).colour, { value: '#336699', from: 'flag' });
  assert.equal(run(site, '--letter', 'Q').status, 0, 'a new flag still wins');
  assert.match(read(site, 'public/favicon.svg').toString(), /the letter Q on #336699/);
});

test('S12: a letter or colour set with a flag does not warn when the site\'s values differ', async () => {
  const site = makeSite({ name: 'Krume' });
  assert.equal(run(site, '--setup', '--letter', 'Z', '--colour', '#336699').status, 0);
  assert.deepEqual(await (await load(site)).staleReasons(site), []);
});

// ---- the glyphs --------------------------------------------------------------------------

const lumaAt = async (svg, size) => {
  const { data } = await sharp(Buffer.from(svg), { density: (72 * size) / 512 }).resize(size, size).flatten({ background: '#000000' })
    .greyscale().raw().toBuffer({ resolveWithObject: true });
  return data;
};
const alone = (letter) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" fill="#000000"/>` +
  `<path d="${script.glyphPath(letter)}" fill="none" stroke="#ffffff" stroke-width="${script.STROKE}" stroke-linejoin="round" stroke-linecap="round"/></svg>`;

test('there are 36 glyphs: A to Z and 0 to 9', () => {
  assert.deepEqual(Object.keys(script.GLYPHS).sort(), [...'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'].sort());
});

for (const size of [32, 64]) {
  test(`every glyph, drawn at ${size} px, shows and stays inside the tile with clear space`, async () => {
    // 64 units clear of each edge of the 512 tile, which also keeps it off the rounded corners (rx 104).
    const lo = Math.floor((64 / 512) * size), hi = Math.ceil((448 / 512) * size) - 1;
    for (const letter of Object.keys(script.GLYPHS)) {
      const data = await lumaAt(alone(letter), size);
      let lit = 0, x0 = size, x1 = -1, y0 = size, y1 = -1;
      data.forEach((v, i) => {
        if (v < 64) return;
        lit++;
        const [x, y] = [i % size, Math.floor(i / size)];
        x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
      });
      assert.ok(lit >= size / 2, `${letter} at ${size}: ${lit} lit pixels, so little that it is not there`);
      assert.ok(x0 >= lo && x1 <= hi && y0 >= lo && y1 <= hi, `${letter} at ${size} reaches ${x0},${y0} to ${x1},${y1}; the clear area is ${lo} to ${hi}`);
    }
  });
}

// Regression floors, not proof of legibility (the glyph sheet is checked by eye): the drawing
// with the inner outline fell under both.
for (const [size, floor] of [[16, 6], [32, 16]]) test(`no two glyphs give the same picture at ${size} px`, async () => {
  const pictures = {};
  for (const letter of Object.keys(script.GLYPHS)) pictures[letter] = await lumaAt(script.drawSvg(letter, '#000000'), size);
  const letters = Object.keys(pictures);
  let least = Infinity;
  for (let i = 0; i < letters.length; i++) {
    for (let j = i + 1; j < letters.length; j++) {
      const [a, b] = [pictures[letters[i]], pictures[letters[j]]];
      let differ = 0;
      for (let k = 0; k < a.length; k++) if (Math.abs(a[k] - b[k]) > 64) differ++;
      least = Math.min(least, differ);
      assert.ok(differ >= floor, `${letters[i]} and ${letters[j]} differ in ${differ} pixels at ${size}`);
    }
  }
  console.log(`# the two most alike glyphs differ in ${least} pixels at ${size}`);
});
