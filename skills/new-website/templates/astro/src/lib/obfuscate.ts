// Build-time email obfuscation so crawlers / scrapers never see a plaintext
// address in the HTML source. The address is reversed + base64-encoded at build;
// a tiny client script (in EmailLink.astro) decodes it on the visitor's machine.

export function encodeEmail(address: string): string {
  // The client decode (atob + character reversal in EmailLink.astro) only
  // round-trips ASCII, and the decoded address goes into a mailto: href verbatim —
  // so umlauts/IDN mangle, and spaces/'?'/'&' would break the href. Fail loud at
  // build rather than ship a mailto that decodes to garbage.
  if (!/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(address)) {
    throw new Error(`encodeEmail: "${address}" is not a plain ASCII email address — this obfuscation scheme cannot encode it safely`);
  }
  const reversed = address.split('').reverse().join('');
  // Buffer is available at build time (Node); the browser decodes with atob().
  return Buffer.from(reversed, 'utf-8').toString('base64');
}

// Human-readable no-JS fallback: "name [at] domain [dot] com" — localized
// ("[punkt]" for German) so the fallback reads naturally in the page's
// language. CHANGES IN LOCKSTEP with EmailLink.astro's decode script, which
// keys on the "[at]" literal to know a hint is still un-decoded.
const DOT_WORD: Record<string, string> = { en: 'dot', de: 'punkt' };
export function emailHint(address: string, lang = 'en'): string {
  const [user, domain = ''] = address.split('@');
  const dot = DOT_WORD[lang.toLowerCase().split('-')[0]] ?? 'dot';
  return `${user} [at] ${domain.replace(/\./g, ` [${dot}] `)}`;
}
