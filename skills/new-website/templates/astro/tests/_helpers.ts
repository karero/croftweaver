// One source of truth for routes. Every suite iterates PAGES — add a route here
// and the a11y / SEO / navigation / image checks all cover it automatically.
// CONVENTION: NO trailing slash (matches `trailingSlash: 'never'`); home stays '/'.
export const PAGES = [
  '/',
  '/privacy',
  '/impressum',  // German-market legal page; non-DE/AT/CH sites delete it (see new-website checklist)
  // '/about',
  // '/contact',
] as const;

// a11y (and any visual check) runs in both themes; the toggle is driven by
// localStorage['theme'], read by the no-FOUC script in Base.astro's <head>.
export const THEMES = ['light', 'dark'] as const;

// German function-word density — the wrong-language detector shared by
// tone.spec.ts (single-locale German sites) and astro-i18n-setup's
// i18n.spec.ts (multi-locale). ONE implementation so the two enforcement
// points can't drift. Real German prose runs ~15-20% density, directory/legal
// genre (addresses, register numbers) ~4%, a non-German body ~0% — these exact
// words essentially don't occur in other languages, which is the margin the 3%
// threshold actually relies on.
export const GERMAN_FUNCTION_WORDS = /\b(der|die|das|und|ist|nicht|mit|für|von|auf|dass|sich|eine?|den|dem|des|sind|wird|werden|können|kann|auch|oder)\b/gi;
export function germanFunctionWordDensity(text: string): number {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  const hits = (text.match(GERMAN_FUNCTION_WORDS) || []).length;
  return words === 0 ? 0 : hits / words;
}

// The tone rules (see tone.spec.ts and the website-content-guide skill), here so that
// every spec holding text to them uses one copy: tone.spec.ts for the pages, and any
// other spec that checks text a page shows only after a click. A new banned word or an
// ALLOWLIST entry goes here.
//
// Language-aware: contraction/buzzword rules are ENGLISH rules. German gets its own
// enforced ruleset (GERMAN_RULES below) — buzzwords and AI-tell phrases — but
// deliberately NO German "contraction" rule: colloquial elisions (geht's, kommt's)
// are natural informal register, not an AI tell. Any other <html lang> (French,
// Spanish, …) gets only the universal rules — French elisions (c'est, d'une) would
// otherwise false-positive. The em-dash ban applies to every language.
const UNIVERSAL_RULES: { label: string; re: RegExp }[] = [
  { label: 'em dash —', re: /—/g },
];
const ENGLISH_RULES: { label: string; re: RegExp }[] = [
  // ANY apostrophe contraction (don't, doesn't, won't, we're, you've, I'll, I'd, I'm) —
  // generic, so the guard can't silently lag behind an enumerated list.
  // Known gaps (accepted): y'all, 'tis, int'l, ma'am slip through; gov't/cont'd/OK'd
  // false-positive (ALLOWLIST them). Names like O'Brien/o'clock are safe (suffix list).
  { label: 'contraction', re: /\b[a-z]+[’'](t|re|ve|ll|d|m)\b/gi },
  // 's only on pronouns/determiners — possessives ("the company's", "one's") stay legal.
  { label: "'s contraction", re: /\b(it|that|what|there|here|who|let|she|he|how|where|when)[’']s\b/gi },
  { label: 'buzzword', re: /\b(supercharge|world-class|best in class|best-in-class|leverage|leverages|leveraging|unlock|unlocks|unlocking|utilize|utilizes|seamless|seamlessly|robust|cutting-edge|empower|empowers|holistic|game-changing|revolutionary|synergy|synergies|next-level|turbocharge)\b/gi },
];
const GERMAN_RULES: { label: string; re: RegExp }[] = [
  // Buzzword/AI-tell vocabulary — the German counterpart to ENGLISH_RULES' buzzword
  // line. Deliberately no German "contraction" rule: colloquial elisions (geht's,
  // kommt's) are natural informal register, not an AI tell (see header comment).
  //
  // Unicode-aware boundaries: JS's bare \b is defined against \w, which is only
  // [A-Za-z0-9_] — it does NOT include ä/ö/ü/ß. A plain /\bwort\b/ regex can
  // silently fail to match at a real word boundary when the word starts or ends
  // with one of those characters (JS sees "non-word" on both sides of the
  // boundary, so \b never fires). None of the words below happen to start/end
  // with ä/ö/ü/ß once correctly spelled, but to stay robust against a future edit
  // (e.g. adding "überzeugend"), use \p{L} lookaround + the u flag instead of \b.
  {
    label: 'buzzword',
    // "massgeschneidert" alongside "maßgeschneidert": Swiss German writes ß as ss, and
    // the /i flag does not fold ß↔ss for us. entfesselt gets the same endings as every
    // other entry, its superlative in both spellings ("entfesseltste", "entfesselteste").
    // Endings cover all four cases incl. dative -em ("mit nahtlosem Übergang"
    // previously slipped through) and superlatives (-ste/-ster/-stes/-sten/-stem,
    // "die nahtloseste Erfahrung").
    re: /(?<!\p{L})(ganzheitlich(?:e|er|es|en|em|ste[mnrs]?)?|nahtlos(?:e|er|es|en|em|este[mnrs]?)?|synergien?|synergieeffekt(?:e|en)?|bahnbrechend(?:e|er|es|en|em|ste[mnrs]?)?|revolutionär(?:e|er|es|en|em|ste[mnrs]?)?|wegweisend(?:e|er|es|en|em|ste[mnrs]?)?|erstklassig(?:e|er|es|en|em|ste[mnrs]?)?|(?:ma(?:ß|ss)geschneidert)(?:e|er|es|en|em|ste[mnrs]?)?|hochmodern(?:e|er|es|en|em|ste[mnrs]?)?|zukunftsweisend(?:e|er|es|en|em|ste[mnrs]?)?|transformativ(?:e|er|es|en|em|ste[mnrs]?)?|unschlagbar(?:e|er|es|en|em|ste[mnrs]?)?|entfesseln|entfesselt(?:e|er|es|en|em|e?ste[mnrs]?)?|spitzenreiter)(?!\p{L})/gui,
  },
  // Multi-word AI-tell phrases — own rule/label (not merged into the buzzword
  // list above). \s+ tolerates whitespace variation between words; same
  // \p{L}-lookaround rationale as the buzzword rule applies at the phrase edges.
  {
    label: 'AI-tell phrase',
    // "in der heutigen ... Welt" tolerates up to two modifiers (the canonical
    // double "schnelllebigen digitalen Welt" and the bare form) plus compound
    // Welt-nouns via \p{L}*welt ("Geschäftswelt", incl. modifiers+compound).
    // The intervening-word slots REJECT determiners/possessives so a real
    // clause boundary can't be swallowed ("in der heutigen Zeit, die Welt
    // dreht sich" and "in der heutigen Ausgabe unserer Welt-Reihe" stay
    // clean). Known accepted edge: "in der heutigen Umwelt" matches (rare,
    // and usually filler prose anyway). The eintauchen family covers
    // Sie/du/wir registers (lassen Sie uns / lass uns / lasst uns).
    re: /(?<!\p{L})(in\s+der\s+heutigen(?:,?\s+(?!(?:der|die|das|den|dem|des|unser\p{L}*|euer|eure\p{L}*|ihr\p{L}*)\b)\p{L}+){0,2}?[\s-]*\p{L}*welt|es\s+ist\s+wichtig\s+zu\s+(?:betonen|beachten|erwähnen),?\s+dass|zusammenfassend\s+lässt\s+sich\s+sagen|lass(?:en\s+sie|t)?\s+uns\s+(?:eintauchen|einen\s+blick\s+werfen))(?!\p{L})/gui,
  },
];
// Exact matches to tolerate (lowercase) — e.g. a brand name like "rock 'n' roll".
const ALLOWLIST = new Set<string>([]);

// Every place `text` breaks the tone rules for `lang` (an <html lang> value), each as
// its rule's label and the words around it. Empty when the text is clean.
export function toneViolations(text: string, lang: string): string[] {
  // Primary subtag only (not startsWith) -- startsWith('de') happens to be correct for every
  // real BCP-47 German tag (de, de-DE, de-AT, de-CH all start with "de"), but primary-subtag
  // comparison is the precise form and can't be fooled by a malformed/non-German tag that
  // merely begins with those two letters.
  const primaryLang = lang.toLowerCase().split('-')[0];
  const rules = primaryLang === 'en'
    ? [...UNIVERSAL_RULES, ...ENGLISH_RULES]
    : primaryLang === 'de'
      ? [...UNIVERSAL_RULES, ...GERMAN_RULES]
      : UNIVERSAL_RULES;

  const violations: string[] = [];
  for (const { label, re } of rules) {
    for (const m of text.matchAll(re)) {
      // Normalize the apostrophe so one ALLOWLIST entry covers ’ and '.
      if (ALLOWLIST.has(m[0].toLowerCase().replace(/’/g, "'"))) continue;
      const i = m.index ?? 0;
      const ctx = text.slice(Math.max(0, i - 25), i + 25).replace(/\s+/g, ' ').trim();
      violations.push(`"${label}" → …${ctx}…`);
    }
  }
  return violations;
}
