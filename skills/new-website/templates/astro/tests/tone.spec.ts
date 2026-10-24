import { test, expect } from '@playwright/test';
import { PAGES, germanFunctionWordDensity, toneViolations } from './_helpers';

// Tone-of-voice guardrail (see the website-content-guide skill + CONTENT_GUIDE.md).
// Hard rules across all user-facing copy AND metadata. Genuinely quoted human/customer
// voice is exempt — wrap it in <blockquote>, <q>, or add data-tov-exempt.
//
// The rules themselves, and the ALLOWLIST of exact matches to tolerate, live in
// _helpers.ts (toneViolations): English rules for an <html lang> of en, German rules
// for de, and only the universal ones (the em-dash ban) for any other language.

test('tone — "entfesselt" is caught in every form, the superlative included', () => {
  // "entfesselteste" once passed: the rule had the case endings but no superlative.
  const forms = ['entfesselt', 'entfesselte', 'entfesseltem', 'entfesseltste', 'entfesseltsten',
    'entfesselteste', 'entfesseltester', 'entfesseltestes', 'entfesseltesten', 'entfesseltestem', 'nahtloseste'];
  for (const form of forms) expect(toneViolations(`Die ${form} Lösung.`, 'de'), form).toHaveLength(1);
});

for (const path of PAGES) {
  test(`tone — no banned phrasing on ${path}`, async ({ page }) => {
    await page.goto(path);
    const { text, lang } = await page.evaluate(() => {
      const body = document.body.cloneNode(true) as HTMLElement;
      body.querySelectorAll('[data-tov-exempt], blockquote, q, script, style, noscript').forEach((el) => el.remove());
      // Also scan <head> metadata: title / description / OG / Twitter are
      // user-facing (SERPs, social cards) but live outside <body>, so they would
      // otherwise slip past the tone rules.
      const metaSel = [
        'meta[name="description"]',
        'meta[property="og:title"]', 'meta[property="og:description"]',
        'meta[name="twitter:title"]', 'meta[name="twitter:description"]',
      ];
      const meta = [document.title, ...metaSel.map((s) => document.querySelector(s)?.getAttribute('content') ?? '')];
      return {
        text: meta.join('\n') + '\n' + body.innerText,
        lang: document.documentElement.lang || '',
      };
    });

    const violations = toneViolations(text, lang);
    // The primary subtag, read as toneViolations reads it: de, de-DE, de-AT, de-CH are German.
    const primaryLang = lang.toLowerCase().split('-')[0];
    expect(
      violations,
      `${path} (lang="${lang}") breaks the tone rules. Em dash → comma/period/colon · contraction → ` +
        `long form · drop the buzzword. Genuine quoted voice → [data-tov-exempt]/<blockquote>/<q>.\n` +
        violations.map((v) => '  • ' + v).join('\n'),
    ).toEqual([]);

    if (primaryLang === 'de') {
      // Wrong-language body (German pages, ANY site shape): a page declaring
      // lang="de" whose body is still English ships silently otherwise — the
      // multi-locale i18n.spec.ts catches this only on sites running
      // astro-i18n-setup, and single-locale German sites are the COMMON case.
      // Same helper and threshold as i18n.spec.ts (word list + math live in
      // _helpers.germanFunctionWordDensity); this extraction additionally
      // strips quoted-voice exemptions, see below. Threshold calibration:
      // real German PROSE runs ~15-20%; directory/legal-genre German
      // (addresses, register numbers — the shipped Impressum) runs ~4%, so 3%
      // keeps a real margin only over NON-German text (~0%) — that is the
      // failure this catches; don't raise the threshold. Pages under 30 body
      // words skip entirely: density is noise on tiny stubs.
      const bodyText = await page.evaluate(() => {
        const body = document.body.cloneNode(true) as HTMLElement;
        // Same exemptions as the rules loop above: quoted human voice
        // (blockquote/q/[data-tov-exempt]) must not trip the register or
        // density checks — a du-voiced customer testimonial on a Sie-register
        // site is the NORMAL case, not a violation.
        body.querySelectorAll('nav, header, footer, script, style, noscript, blockquote, q, [data-tov-exempt]').forEach((el) => el.remove());
        return body.innerText;
      });
      const bodyWords = bodyText.trim().split(/\s+/).filter(Boolean).length;
      if (bodyWords >= 30) {
        const density = germanFunctionWordDensity(bodyText);
        expect(
          density,
          `${path} (lang="de"): body reads as non-German (${(density * 100).toFixed(1)}% German ` +
            `function words in ${bodyWords} words, expected >=3%) — content left in the original ` +
            `language under a German lang attribute?`,
        ).toBeGreaterThanOrEqual(0.03);
      }

      // du/Sie register consistency: mixing informal and formal address on one
      // page reads as a translation error (CONTENT_GUIDE, website-content-guide).
      // PRECISION over recall — only UNAMBIGUOUS markers count, both sides
      // case-sensitive (no i flag):
      //  - informal: lowercase du-family words. Lowercase "du/dich/dein" can
      //    only be informal address in German (capitalized sentence-initial
      //    "Du" is skipped — ambiguous with the formal-letter Du-style).
      //  - formal: capitalized imperative verb+Sie phrases ("Kontaktieren
      //    Sie..."). Bare "Sie/Ihnen/Ihre" is deliberately NOT counted:
      //    sentence-initial it collides with sie=she/they and Ihre=her/their,
      //    and innerText loses too much sentence structure to disambiguate.
      // A miss ships (recall loss, acceptable); a false alarm on clean copy
      // should not — if this still over-fires, the fallback is documenting the
      // rule as manual review, not loosening the match.
      const informal = bodyText.match(/\b(du|dich|dir|dein|deine|deinen|deinem|deiner)\b/g) ?? [];
      const formal = bodyText.match(/\b(?:Kontaktieren|Erreichen|Melden|Rufen|Schreiben|Erfahren|Buchen|Vereinbaren|Testen|Starten|Entdecken|Fragen)\s+Sie\b/g) ?? [];
      expect(
        informal.length === 0 || formal.length === 0,
        `${path} (lang="de"): page mixes du-register (${[...new Set(informal)].join(', ')}) and ` +
          `Sie-register (${[...new Set(formal)].join(', ')}) address — pick ONE (CONTENT_GUIDE "du/Sie"). ` +
          `Genuinely quoted voice (a du-voiced testimonial on a Sie site) → <blockquote>/<q>/[data-tov-exempt].`,
      ).toBe(true);
    }
  });
}
