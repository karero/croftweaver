// Scorecard: a dated summary of this site's own test gate, written to scorecard.json
// so the site can publish it (src/components/Scorecard.astro renders it).
//
//   npm run scorecard
//       Runs the whole suite against a production build and writes scorecard.json.
//       Refuses when files are uncommitted (the card must describe a commit) and
//       writes nothing when a test fails: a card never shows a red run as green.
//   npm run scorecard -- --lighthouse <performance>,<accessibility>,<best-practices>,<seo> [--date YYYY-MM-DD] [--strategy mobile|desktop]
//       Records the four scores of a PageSpeed Insights run that the owner made on
//       the LIVE site. They are typed in, not fetched: Google's API refused an
//       unkeyed request ("quota exceeded") when this was written, and a key is one
//       more thing to set up. The card links to the same test so anyone can re-run it.
//
// The card records which commit it tested and the git id of the paths listed in
// TESTED. The component compares those ids with the build's own and says so when the
// site has been edited since. Nothing fails on an outdated card; it just stops
// claiming to describe the current site.
import { execFileSync, spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, readdirSync, realpathSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

export const FILE = 'scorecard.json';
// The paths that decide what the site serves or what the suite checks. A change to
// any of them after the run means the card no longer describes the site. Not here on
// purpose: documents (README, the content guide), scorecard.json itself, and CI
// workflows. A site with further root files that shape the build adds them here.
export const TESTED = [
  'src', 'public', 'tests', 'functions', 'scripts', 'astro.config.mjs', 'package.json',
  'package-lock.json', 'playwright.config.ts', 'tsconfig.json', '.nvmrc',
];
const LIGHTHOUSE = ['performance', 'accessibility', 'bestPractices', 'seo'];

const git = (...args) => execFileSync('git', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();

// path → git object id at HEAD, for the TESTED paths that exist. Throws without git.
export function tested() {
  return Object.fromEntries(git('ls-tree', 'HEAD', '--', ...TESTED).split('\n').filter(Boolean).map((line) => {
    const [meta, path] = line.split('\t');
    return [path, meta.split(' ')[2]];
  }));
}

// Same paths, same ids → the card describes this state of the site.
export function sameState(a, b) {
  const keys = new Set([...Object.keys(a ?? {}), ...Object.keys(b ?? {})]);
  return keys.size > 0 && [...keys].every((k) => a?.[k] === b?.[k]);
}

// What the page may say about a card: 'current' (the TESTED paths are as tested, and
// nothing in them is uncommitted), 'edited', or 'unknown' when git cannot answer.
export function stateOf(card) {
  try {
    const uncommitted = git('status', '--porcelain', '--', ...TESTED) !== '';
    return !uncommitted && sameState(tested(), card?.tested) ? 'current' : 'edited';
  } catch {
    return 'unknown';
  }
}

// scorecard.json as { card, broken }. A file that is not valid JSON is `broken`, never
// an exception: the page then shows no card, the spec fails with the reason, and
// `npm run scorecard` can still write a new one.
export function loadCard(file = FILE) {
  if (!existsSync(file)) return { card: null, broken: false };
  try {
    const card = JSON.parse(readFileSync(file, 'utf8'));
    return card && typeof card === 'object' && Array.isArray(card.checks) ? { card, broken: false } : { card: null, broken: true };
  } catch {
    return { card: null, broken: true };
  }
}

// Playwright's JSON report → one row per spec file. `expected` is a pass; a test that
// was skipped is counted, never hidden; anything else makes the run red.
export function summarize(report) {
  const rows = new Map();
  const walk = (suite, file) => {
    const name = (suite.file ?? file ?? 'unknown').replace(/\.spec\.[cm]?[jt]s$/, '');
    for (const spec of suite.specs ?? []) {
      for (const t of spec.tests ?? []) {
        const row = rows.get(name) ?? { area: name, passed: 0, skipped: 0, failed: 0 };
        if (t.status === 'expected') row.passed += 1;
        else if (t.status === 'skipped') row.skipped += 1;
        else row.failed += 1;
        rows.set(name, row);
      }
    }
    for (const child of suite.suites ?? []) walk(child, suite.file ?? file);
  };
  for (const suite of report.suites ?? []) walk(suite, suite.file);
  // The card is about the site, not about itself: its own spec (tests/scorecard.spec.ts)
  // stays out, or the first card would report "not applicable" for the file it is writing.
  rows.delete('scorecard');
  const checks = [...rows.values()].sort((a, b) => a.area.localeCompare(b.area));
  const total = (k) => checks.reduce((n, r) => n + r[k], 0);
  return { checks, passed: total('passed'), skipped: total('skipped'), failed: total('failed') };
}

// Today in the machine's own time zone, as YYYY-MM-DD (toISOString would be UTC, a day
// off late in the evening).
export function today(now = new Date()) {
  const two = (n) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${two(now.getMonth() + 1)}-${two(now.getDate())}`;
}

// "98,100,100,100" → the four scores, or a reason it is not usable. The date has to be
// a real day (not 30 February) that is not in the future.
export function parseLighthouse(scores, date, strategy = 'mobile', notAfter = today()) {
  const values = String(scores).split(',').map((s) => s.trim());
  if (values.length !== 4 || values.some((v) => !/^\d{1,3}$/.test(v) || Number(v) > 100)) {
    return { error: 'give four whole numbers from 0 to 100: performance,accessibility,best practices,seo' };
  }
  const real = /^\d{4}-\d{2}-\d{2}$/.test(date) && !Number.isNaN(Date.parse(`${date}T00:00:00Z`))
    && new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) === date;
  if (!real) return { error: `the date of the run must be a real day written like 2026-10-04, got "${date}"` };
  if (date > notAfter) return { error: `the date of the run (${date}) is in the future` };
  if (!['mobile', 'desktop'].includes(strategy)) return { error: 'the strategy is mobile or desktop' };
  return { value: { date, strategy, ...Object.fromEntries(LIGHTHOUSE.map((k, i) => [k, Number(values[i])])) } };
}

const fail = (msg) => { console.error('✗ ' + msg); process.exit(1); };
const writeCard = (card) => writeFileSync(FILE, JSON.stringify(card, null, 2) + '\n');

function recordLighthouse(argv) {
  const opt = (name, fallback) => (argv.includes(name) ? argv[argv.indexOf(name) + 1] : fallback);
  const parsed = parseLighthouse(opt('--lighthouse', ''), opt('--date', today()), opt('--strategy', 'mobile'));
  if (parsed.error) fail(parsed.error);
  const { card, broken } = loadCard();
  if (broken) fail(`${FILE} cannot be read. Run "npm run scorecard" to write a new one, then record the scores again.`);
  if (!card) fail(`${FILE} does not exist yet. Run "npm run scorecard" first.`);
  writeCard({ ...card, lighthouse: parsed.value });
  console.log(`✓ Lighthouse scores of ${parsed.value.date} recorded in ${FILE}. Commit it.`);
}

function pagesInSitemap() {
  if (!existsSync('dist')) return 0;
  return readdirSync('dist')
    .filter((f) => /^sitemap-\d+\.xml$/.test(f))
    .reduce((n, f) => n + (readFileSync(join('dist', f), 'utf8').match(/<loc>/g) ?? []).length, 0);
}

function runSuite() {
  if (git('status', '--porcelain')) {
    fail('There are uncommitted changes. Commit them first: the scorecard has to describe a commit, not a work in progress.');
  }
  const dir = mkdtempSync(join(tmpdir(), 'scorecard-'));
  const out = join(dir, 'report.json');
  console.log('Running the whole test suite against a production build. This takes a minute or two…');
  // CI is cleared so the run is the one a developer sees: retries would hide a flaky
  // test. --forbid-only does what the cleared CI no longer does: a stray test.only
  // must not shrink the run. SCORECARD_RUN makes tests/scorecard.spec.ts sit this run
  // out: it checks the card that is about to be replaced, and a card that is wrong
  // must not block its own repair.
  const env = { ...process.env, PLAYWRIGHT_JSON_OUTPUT_NAME: out, SCORECARD_RUN: '1' };
  delete env.CI;
  let run, report;
  try {
    run = spawnSync('npx', ['playwright', 'test', '--reporter=json', '--forbid-only'], { env, stdio: 'ignore' });
    report = existsSync(out) ? JSON.parse(readFileSync(out, 'utf8')) : null;
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
  if (!report) fail(`The test run produced no report (exit ${run.status}). Run "npm test" to see why.`);
  const result = summarize(report);
  // A spec file that fails to load has no failed test, only an error: red all the same.
  if (result.failed > 0 || run.status !== 0 || (report.errors ?? []).length > 0) {
    const red = result.checks.filter((r) => r.failed).map((r) => `${r.area} (${r.failed})`).join(', ');
    fail(`The run is red${red ? `: ${red}` : ` (exit ${run.status})`}. No scorecard written. Fix the tests ("npm test"), then run this again.`);
  }
  if (result.passed === 0) fail('The run reported no passed test. No scorecard written.');
  const suite = existsSync('tests/TESTS-VERSION')
    ? (readFileSync('tests/TESTS-VERSION', 'utf8').match(/^suite_commit: (\S+)/m)?.[1] ?? null)
    : null;
  const previous = loadCard();
  writeCard({
    generated: today(),
    commit: git('rev-parse', 'HEAD'),
    tested: tested(),
    pages: pagesInSitemap(),
    passed: result.passed,
    skipped: result.skipped,
    checks: result.checks.map(({ area, passed, skipped }) => ({ area, passed, skipped })),
    ...(suite ? { suite } : {}),
    ...(previous.card?.lighthouse ? { lighthouse: previous.card.lighthouse } : {}),
  });
  console.log(`✓ ${result.passed} checks passed${result.skipped ? `, ${result.skipped} not applicable` : ''}. Written to ${FILE}. Commit it.`);
  if (previous.broken) console.log('  The old file could not be read, so its Lighthouse scores are gone. Record them again if the site had any.');
}

// Run only when started as a script (not when the component or the spec imports it).
// realpath: Node hands over the path as typed, which may be a symlink.
if (process.argv[1] && import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href) {
  const argv = process.argv.slice(2);
  if (argv.includes('--lighthouse')) recordLighthouse(argv);
  else runSuite();
}
