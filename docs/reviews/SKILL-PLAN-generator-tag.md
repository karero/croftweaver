# Plan: a generator tag in every starter site, told at build time

Status: plan, not built. Owner decisions, 2026-10-26 and 27: "Let's do the industry standard",
"Always allow off switch", "Tell at build time, with the off switch; at the badge question, a
reminder only, no second ask", and "add its not visible on the page, it's in the code. Word it
so a 5 year old understands it".

## What

Every page of a site made from the `new-website` starter carries one line in its `<head>`:

```html
<meta name="generator" content="Croftweaver">
```

- It is in the page's code only. Visitors do not see it on the page.
- It names the toolkit and nothing else: no link, no version, no script, no request to any
  server. It sends nothing to anyone.
- On by default. One line in `src/config.ts` turns it off: `export const GENERATOR_TAG = true;`
  set to `false`.

## Why

- A generator tag is the industry standard: WordPress and Wix, for example, write one by
  default. Anyone who reads a page's code can see which tool made it.
- It lets the maintainer find sites made with Croftweaver, without asking anyone and without
  telemetry. This is a floor, not a count: owners can switch it off. Judgment, not checked:
  which crawlers and site-profiling tools read it.

No version in the tag: the site has no release number to read (its `tests/TESTS-VERSION`
stamp is a commit and a date), and a version would go stale when the site is not updated.

## How

1. **Starter** (`skills/new-website/templates/astro/`):
   - `src/config.ts`: `GENERATOR_TAG = true`, with a one-line comment saying what it does and
     that `false` removes it.
   - `src/layouts/Base.astro`: in `<head>`, `{GENERATOR_TAG && <meta name="generator"
     content="Croftweaver" />}`.
2. **Tell the owner at build time.** `new-website` §3, step 5 (Confirm green), after the first
   green run, says once, in the chat:

   > One small thing you can't see: your pages' code has a tiny name tag that says "made with
   > Croftweaver". People who visit your site won't see it on the page. It doesn't send
   > anything to anyone and doesn't link anywhere. If you'd rather not have it, just say
   > "remove the Croftweaver tag" and I'll take it out.

   On "remove": set `GENERATOR_TAG = false`, run the tests, and record "generator tag: off"
   with the decision answers in the project README. Otherwise record "generator tag: on".
   A line there means it was told already: later sessions do not tell it again.
3. **At the badge question** (`new-website` §4b), the "No thanks" answer gets one reminder
   line, only while the README says "generator tag: on":

   > No problem. The little "made with Croftweaver" tag in your pages' code is still there,
   > where visitors can't see it. Say "remove the Croftweaver tag" any time if you'd like it
   > gone.

   No second request. §4b also gets one sentence saying the tag is not the credit: the credit
   is a visible link the owner chooses; the tag is a disclosed default, like the build tool's
   name, and is told at build time, not requested.
4. **Documents.**
   - `docs/WHAT-THE-SKILLS-RUN.md`, "Telemetry": a bullet naming the tag, saying it sends
     nothing, and how to switch it off.
   - `README.md`, "License & credits": one sentence on the tag and its switch.
5. **Existing sites** are not changed. A site that updates its starter files gets the tag only
   if it takes the changed `Base.astro` and `config.ts` (`scripts/whats-new.sh` lists changed
   starter files).

## Test

- `tests/seo.spec.ts` in the starter: for every page, read `GENERATOR_TAG` from `src/config.ts`.
  If true, the page has exactly one `meta[name="generator"]`, with content `Croftweaver`. If
  false, it has none. The test runs on the built site, the way a visitor's browser gets it.
- It can fail: removing the tag from `Base.astro` fails it with the default setting; a layout
  that ignores the switch fails it as soon as an owner sets `false`. Before the review of the
  build, both are run by hand once (a mutation check) and their output is quoted in the PR.
- The toolkit's template workflow (`.github/workflows/template-tests.yml`) runs `npm test` on
  the starter when its files change, so the new check runs in CI too.

## Not in scope

- croftweaver.com and the GenAI Wednesday site: their owner decides separately.
- A visible credit: unchanged, still only asked in §4b.
- Counting or reporting the tags found: a separate idea, not planned.
