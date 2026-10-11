// The mail-app contact form's words and limits (the website-contact-form skill),
// installed as src/components/mail-form-text.ts. The form
// (src/components/MailForm.astro) and its test (tests/mail-form.spec.ts) import it, so
// a language is added, or a sentence changed, here and nowhere else.

// The longest message the form takes, in typed characters. Every one travels
// inside one mailto: link, encoded: a space takes 3 characters there, an umlaut 6, a
// line break 6, so 2,000 typed characters make a link of roughly 2,800 (English prose)
// to 12,000 (umlauts only). Some mail programs cut a very long link; at what length was
// not measured (docs/BUGLOG.md), so this cap is not tied to any program's limit. The
// visitor can write on in their mail program.
export const LIMITS = { message: 2000 };

// Everything a visitor reads, by language. The mail itself is the visitor's message as
// typed, and its subject line is not here: each site chooses its own (the `subject`
// prop). tests/mail-form.spec.ts holds every text here to the
// site's tone rules (tests/_helpers.ts): no long dash in any language, and the rules
// of the text's own language where there are some (English: no contraction, no
// buzzword; German: no buzzword, no stock AI phrase). In German they address nobody,
// so the form fits a "du" site and a "Sie" site alike. A language that leaves one of
// these out fails `npm run check`.
//
//   message, send        the label and the button
//   note                 the line above the button: what pressing it does
//   opened               the line after pressing it
//   direct               the words before the plain address under the form
type Texts = {
  message: string; send: string; note: string; opened: string; direct: string;
};
export const TEXT = {
  en: {
    message: 'Message',
    send: 'Open in my email program',
    note: 'The button opens your own email program with this message ready. It is sent only when you press Send there, and this website keeps nothing.',
    opened: 'Your email program should now show the message. Press Send there to send it. If nothing opened, please write to the address below.',
    direct: 'Prefer a blank email? Write to us directly:',
  },
  de: {
    message: 'Nachricht',
    send: 'Im E-Mail-Programm öffnen',
    note: 'Der Knopf öffnet das eigene E-Mail-Programm mit dieser Nachricht. Gesendet wird sie erst mit Senden dort, und diese Website speichert nichts.',
    opened: 'Das E-Mail-Programm sollte die Nachricht jetzt zeigen. Gesendet wird sie mit Senden dort. Hat sich nichts geöffnet, bitte an die Adresse unten schreiben.',
    direct: 'Lieber eine leere E-Mail? Direkt schreiben an:',
  },
} satisfies Record<string, Texts>;

export type Language = keyof typeof TEXT;

// Whether there are texts for a language. Own keys only: "constructor" is not one.
export const hasText = (lang: string): lang is Language => Object.hasOwn(TEXT, lang);
