// The mail-app contact form (the website-contact-form skill), installed as
// tests/mail-form.spec.ts. Set PAGE, TO and SUBJECT below; the spec fails while one is
// empty.
// One copy guards one form: a site with the form on pages in two languages gets two
// copies (tests/mail-form.de.spec.ts), each with its own PAGE.
//
// Every test enters the way a visitor does: the page as built, the real button. The
// mail program itself is out of reach of a test; what is checked is the mailto: link
// the browser is asked to open, which is everything the mail program receives.
//
// It imports `toneViolations` from tests/_helpers.ts, the tone rules the site's pages
// are held to. A site made from an older starter lacks it: see the skill, §1.
import { test, expect, type Page } from '@playwright/test';
import { LIMITS, TEXT, hasText } from '../src/components/mail-form-text';
import { toneViolations } from './_helpers';

const PAGE = '';    // the page with the form, e.g. '/contact'
const TO = '';      // the address given to <MailForm to="…">
const SUBJECT = ''; // the subject given to <MailForm subject="…">
const LANG = '';    // only if the page passes lang="…": that language; else the page's own

// The mailto: link the button asks the browser to open. The browser hands it to the
// mail program; Playwright sees it as a request.
async function pressSend(page: Page): Promise<string> {
  const lang = await formLanguage(page);
  const asked = page.waitForRequest((r) => r.url().startsWith('mailto:'), { timeout: 5000 });
  await form(page).getByRole('button', { name: TEXT[lang].send, exact: true }).click();
  return (await asked).url();
}

// The link's parts, each decoded once. Not URLSearchParams: it reads "+" as a space.
function parse(mailto: string) {
  expect(mailto.startsWith('mailto:'), `a mailto: link, not "${mailto.slice(0, 40)}"`).toBe(true);
  const [encodedAddress, query = ''] = mailto.slice('mailto:'.length).split('?');
  const address = decodeURIComponent(encodedAddress);
  const params = Object.fromEntries(query.split('&').map((pair) => {
    const [key, value = ''] = pair.split('=');
    return [key, decodeURIComponent(value)];
  }));
  return { address, encodedAddress, query, params };
}

// Every lookup stays inside the form, so a second status line or a "Company name"
// field elsewhere on the page cannot be taken for one of the form's.
const form = (page: Page) => page.locator('form[data-mail-form]');

async function formLanguage(page: Page) {
  const lang = (await page.locator('form[data-mail-form]').getAttribute('lang')) ?? '';
  expect(hasText(lang), `the form speaks "${lang}", which has no texts in mail-form-text.ts`).toBe(true);
  // By itself, in the language of the page it is on (<html lang>, as Base.astro sets it),
  // unless the page passes another one: then LANG names it.
  const pageLang = ((await page.locator('html').getAttribute('lang')) ?? '').toLowerCase().split('-')[0];
  // The form keeps the first part of a language code (de-DE → de), and so does LANG here.
  const want = (LANG || pageLang).toLowerCase().split('-')[0];
  expect(lang, `the form speaks "${lang}" on a page in "${pageLang}"; a page that passes lang="…" sets LANG in this spec`).toBe(want);
  return lang as keyof typeof TEXT;
}

test('mail form — the install is complete: the form\'s page, its address and its subject are named', () => {
  expect(PAGE, 'set PAGE in tests/mail-form.spec.ts to the page with the form').not.toBe('');
  expect(TO, 'set TO in tests/mail-form.spec.ts to the address given to <MailForm to="…">').not.toBe('');
  expect(SUBJECT, 'set SUBJECT in tests/mail-form.spec.ts to the subject given to <MailForm subject="…">').not.toBe('');
});

test('mail form — the button opens a mail to the owner with everything the visitor wrote', async ({ page }) => {
  await page.goto(PAGE);
  const lang = await formLanguage(page);
  // Characters that break a link unless each is encoded: & ? # % + = and a line break,
  // and letters outside ASCII.
  const message = 'Is 100% possible? Price #1 + extras = fine.\n\n  Zweite Zeile: Grüße, ça va';
  // Typed with a blank line, spaces and a tab around it: those edges are dropped, the rest
  // kept.
  await form(page).getByLabel(TEXT[lang].message, { exact: true }).fill(`\n \t ${message}\t  \n`);
  const mailto = await pressSend(page);
  const { address, query, params } = parse(mailto);

  expect(address, 'the mail goes to TO: the address was decoded right').toBe(TO);
  expect(Object.keys(params).sort(), 'a subject and a body, nothing else').toEqual(['body', 'subject']);
  expect(params.subject, 'the subject the site chose').toBe(SUBJECT);
  expect(toneViolations(SUBJECT, lang), 'the subject keeps to the site\'s tone rules').toEqual([]);
  // Every character outside the few a link may carry as they are arrives encoded, so
  // nothing the visitor typed can end the subject early or start a new part.
  expect(query, 'the subject and body are URL-encoded').toMatch(/^subject=[A-Za-z0-9\-_.!~*'()%]*&body=[A-Za-z0-9\-_.!~*'()%]*$/);
  expect(query, 'a line break is %0D%0A (RFC 6068), never a bare %0A').not.toMatch(/(?<!%0D)%0A/);
  // The message as typed, less the empty space around it: the visitor writes their own
  // greeting and sign-off.
  expect(params.body).toBe(message.replace(/\n/g, '\r\n'));

  // The site cannot know whether the mail program opened, so it says what to do next.
  await expect(form(page).getByRole('status')).toHaveText(TEXT[lang].opened);
});

test('mail form — fields the owner adds go into the mail by their labels; one left empty does not', async ({ page }) => {
  await page.goto(PAGE);
  const lang = await formLanguage(page);
  await page.locator('form[data-mail-form] button[type="submit"]').evaluate((button) => {
    for (const [id, label] of [['added-phone', 'Phone'], ['added-company', 'Company']]) {
      const p = document.createElement('p');
      p.innerHTML = `<label for="${id}">${label}</label><input id="${id}" name="${id}" type="text">`;
      button.closest('p')!.before(p);
    }
    // A named group has no value of its own, and must not stop the mail.
    const group = document.createElement('fieldset');
    group.name = 'added-group';
    button.closest('p')!.before(group);
    const p = document.createElement('p');
    p.innerHTML = '<label for="added-days">Days</label><select id="added-days" name="days" multiple><option>Monday</option><option>Tuesday</option><option>Friday</option></select>';
    button.closest('p')!.before(p);
  });
  await form(page).getByLabel(TEXT[lang].message, { exact: true }).fill('Hello there');
  await form(page).getByLabel('Phone', { exact: true }).fill('+49 30 1234');
  await form(page).getByLabel('Days', { exact: true }).selectOption(['Monday', 'Friday']);
  const { params } = parse(await pressSend(page));
  expect(params.body).toBe('Hello there\r\n\r\nPhone: +49 30 1234\r\nDays: Monday, Friday');
  expect(params.body).not.toContain('Company');
});

test('mail form — a % in the address, which the starter allows, is escaped in the link', async ({ page }) => {
  await page.goto(PAGE);
  const lang = await formLanguage(page);
  // The address the page would carry for a%b@example.com, encoded as encodeEmail does.
  await form(page).evaluate((f: HTMLFormElement) => { f.dataset.to = btoa('a%b@example.com'.split('').reverse().join('')); });
  await form(page).getByLabel(TEXT[lang].message, { exact: true }).fill('Hello');
  const { address, encodedAddress } = parse(await pressSend(page));
  expect(encodedAddress).toBe('a%25b@example.com');
  expect(address).toBe('a%b@example.com');
});

test('mail form — an empty message stops the browser, and no mail opens', async ({ page }) => {
  await page.goto(PAGE);
  const lang = await formLanguage(page);
  let opened = false;
  page.on('request', (r) => { if (r.url().startsWith('mailto:')) opened = true; });
  await form(page).getByRole('button', { name: TEXT[lang].send, exact: true }).click();
  await page.waitForTimeout(500);
  expect(opened, 'no mail opened without a message').toBe(false);
  await expect(form(page).getByLabel(TEXT[lang].message, { exact: true })).toBeFocused();
  await expect(form(page).getByRole('status')).toHaveText('');
});

test('mail form — a message of spaces counts as empty, and no mail opens', async ({ page }) => {
  await page.goto(PAGE);
  const lang = await formLanguage(page);
  let opened = false;
  page.on('request', (r) => { if (r.url().startsWith('mailto:')) opened = true; });
  await form(page).getByLabel(TEXT[lang].message, { exact: true }).fill('   \n  ');
  await form(page).getByRole('button', { name: TEXT[lang].send, exact: true }).click();
  await page.waitForTimeout(500);
  expect(opened, 'no mail opened with a message of spaces').toBe(false);
  await expect(form(page).getByLabel(TEXT[lang].message, { exact: true })).toBeFocused();
});

test('mail form — the message takes no more than the limit', async ({ page }) => {
  await page.goto(PAGE);
  const lang = await formLanguage(page);
  await expect(form(page).getByLabel(TEXT[lang].message, { exact: true })).toHaveAttribute('maxlength', String(LIMITS.message));
});

test('mail form — every field has a label, and Tab goes from the message to the button', async ({ page }) => {
  await page.goto(PAGE);
  const lang = await formLanguage(page);
  const order = [form(page).getByLabel(TEXT[lang].message, { exact: true }), form(page).getByRole('button', { name: TEXT[lang].send, exact: true })];
  // Every control in the form is one of these: none without a label slipped in.
  await expect(page.locator('form[data-mail-form] :is(input, textarea, select, button)')).toHaveCount(order.length);
  await order[0].focus();
  for (const next of order.slice(1)) {
    await page.keyboard.press('Tab');
    await expect(next).toBeFocused();
  }
});

test('mail form — the plain address shows under the form, ready to copy and to click', async ({ page }) => {
  await page.goto(PAGE);
  const lang = await formLanguage(page);
  const direct = page.locator('.mail-form-direct');
  await expect(direct).toContainText(TEXT[lang].direct);
  const link = direct.getByRole('link');
  await expect(link).toHaveText(TO);
  // The same address and subject as the form's, so a blank email starts as the same
  // request. Read as a mail program reads the link, whatever the encoding.
  const linked = parse((await link.getAttribute('href')) ?? '');
  expect(linked.address).toBe(TO);
  expect(linked.params).toEqual({ subject: SUBJECT });
});

test('mail form — without JavaScript the form stays hidden and the address is shown', async ({ browser, baseURL }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await context.newPage();
  const response = await page.goto(PAGE);
  const html = await response!.text();
  expect(html.includes(TO), 'the address is never in the HTML as plain text').toBe(false);
  // A form that cannot open a mail program is not shown at all.
  await expect(page.locator('form[data-mail-form]')).toBeHidden();
  const [user, domain] = TO.split('@');
  await expect(page.locator('.mail-form-direct')).toBeVisible();
  await expect(page.locator('.mail-form-direct')).toContainText(`${user} [at] ${domain.split('.')[0]}`);
  await context.close();
});

test('mail form — it works under a strict Content-Security-Policy that allows the site\'s own scripts only', async ({ page }) => {
  await page.route(`**${PAGE}`, async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, headers: { ...response.headers(), 'content-security-policy': "script-src 'self'" } });
  });
  await page.goto(PAGE);
  const lang = await formLanguage(page);
  await expect(page.locator('form[data-mail-form]')).toBeVisible();
  await form(page).getByLabel(TEXT[lang].message, { exact: true }).fill('Hello');
  expect(parse(await pressSend(page)).address).toBe(TO);
});

test('mail form — every text of the form keeps to the site\'s tone rules, in every language', () => {
  const found = Object.entries(TEXT).flatMap(([lang, texts]) =>
    Object.entries(texts).flatMap(([key, text]) => toneViolations(text, lang).map((v: string) => `  • ${lang}.${key}: ${v}`)));
  expect(found, `texts in src/components/mail-form-text.ts break the tone rules:\n${found.join('\n')}`).toEqual([]);
});
