import { test, expect } from '@playwright/test';
import { PAGES } from './_helpers';

// Outgoing-link guard: domains you have deliberately migrated AWAY from must never
// reappear in an anchor href. Each entry pairs the dead/retired domain with WHY it's
// dead, so a regression (an old link copy-pasted back in, or a fresh page reusing a
// stale URL) fails loudly here instead of silently shipping a redirect/dead link.
//
// This is the deterministic, OFFLINE half of outgoing-link hygiene — it makes no
// network calls, so it stays in CI. The *liveness* of the links you DO keep (are they
// still 200? did one rebrand to a new domain?) is network-dependent and checked
// out-of-band by `scripts/check_external_links.sh` + the `outgoing-link-audit` skill,
// deliberately NOT in this hermetic gate. When that audit finds a newly dead/rebranded
// domain, add it here so it can never be re-introduced.
//
// Starts empty: a brand-new site has retired nothing yet. Grow it from audit findings.
const STALE_DOMAINS: { domain: string; reason: string }[] = [
  // { domain: 'oldvendor.com', reason: 'rebranded to newvendor.io in 2026 — use https://newvendor.io' },
];

for (const path of PAGES) {
  test(`links: ${path} has no stale outgoing domains`, async ({ page }) => {
    await page.goto(path, { waitUntil: 'load' });
    const hrefs = await page
      .locator('a[href]')
      .evaluateAll((els) => els.map((e) => (e as HTMLAnchorElement).getAttribute('href') || ''));
    const offenders = STALE_DOMAINS.flatMap(({ domain, reason }) =>
      hrefs.filter((h) => h.includes(domain)).map((h) => `${h} → ${reason}`),
    );
    expect(offenders, `stale outgoing link(s) on ${path}:\n${offenders.join('\n')}`).toEqual([]);
  });
}
