# Trial: website-launch-check on a fixture site, 2026-10-25

The plan's row 5: one recorded run of the skill on a fixture, not a regression test. It credits
exactly the cases listed here.

**Fixture.** The starter (`skills/new-website/templates/astro` at this branch) scaffolded as a
German site: `SITE.locale` `'de'`, the `/datenschutz` swap from `_datenschutz.astro`'s header
(so `seo.spec.ts` carries the `OWN_CARD_EXEMPT` edit), pages `/ueber-uns` and `/leistungen`, three
named testimonials in `src/data/testimonials.ts`, the imprint and privacy slots left unfilled.
The README records the interview answers and "story layer declined"; an untracked root
`.launch-check-config.json` in the old format. Three git tags: `baseline`; `prelaunch` (a bare
`<table>` on `/leistungen`, so `tables.spec.ts` fails; a noindex page `/intern` outside `PAGES`
with an `<img>` without alt; `/ueber-uns` and `/leistungen` share a title); `relaunch`
(`public/_redirects` for two of the moves). The old site was a local stub (a `sitemap.xml` of
nine addresses on 127.0.0.1), with the owner's `moves.csv`. Built by one agent; the skill was run
by a second, fresh agent that followed SKILL.md with scripted owner answers (German) and was not
told what was planted.

## Results

| Case | Expected (plan) | Seen |
|---|---|---|
| S12, old settings file | moved with `mv` (untracked), said so | moved with `mv`, said so; old keys renamed |
| S1, baseline | settings from the README, no story question; verdict "Baseline, not a launch verdict" | no story question; `launch-check-2026-10-25-baseline.md` + `.html`, "Baseline, kein Launch-Urteil" |
| S13, German | everything the owner sees in German | questions, reports and HTML in German, `lang="de"` |
| S5, Authority | "not checked: no outside data", averaged rows named | "nicht geprüft: keine Daten von außen"; overall "über Erfahrung, Fachwissen, Vertrauen, Lokal" |
| S4, warnings | every `⚠ placeholders:` line a blocker | the three "not ready to launch" lines (`/impressum`, `/datenschutz`, the manifest) as blockers |
| S4, red spec | 🔴, the test named | 🔴 "Nicht bereit", `tables` test and its message first |
| S3, coverage per page | alt text, one H1, title and description length left to the tests on each page whose test passed | both rows, on the five `PAGES` routes |
| D2, pages outside `PAGES` | checked by the check | `/404` and `/intern` checked; `/intern`'s missing alt found |
| Two pages sharing a title | found | found |
| S7, consent | asked per named person; "don't know" a blocker | asked for each of the three; the third ("Weiß ich nicht") a blocker |
| Skip arm | the skip a finding; that page's categories the check's | `/leistungen`'s head-contract checks done by the check; the skip reported |
| Spec removed | alt text the check's on every page | yes |
| Spec left out of the command | the same | yes; the agent found the missing titles by name |
| `-g` to `/`'s image test | alt text the check's except on `/` | yes; and see fix 1 below |
| S8–S10, relaunch | comparison with every old address once; undecided, a decided move without a redirect and a missing `keep` path as before-launch items; PageSpeed "not measured" | `launch-comparison-2026-10-25.md` + `.html`; 9 sitemap entries as 8 addresses (`/team` and `/team/` once); `/kontakt` keep missing, `/alt-impressum` without a redirect, `/galerie` and `/?p=12` undecided as ❌; PageSpeed old "nicht gemessen", new "noch nicht gemessen: … bei Schritt 12a" |
| S14, rebuild | an edited report's HTML shows the edit after the next run | yes (`grep -c Teständerung` on the HTML: 1) |
| D6, same day | a second pre-launch report gets `-2` | `launch-check-2026-10-25-prelaunch-2.md` |
| D7, the pages | load nothing | no `<script>`, `<img>`, `<link>` or `<iframe>` element in any of the four pages |

## What the trial found in the skill text, and the fix

1. A narrowed `test` script hid the failing test and the warnings, not only coverage. Fix: §2 and
   `test-coverage.md` run the whole suite with `npx playwright test`; a `test` script other
   than `playwright test` is a 🟡 finding.
2. A filtered-out test leaves no line and no count. Fix: `test-coverage.md` says to check by the
   test titles expected for each page in `PAGES`.
3. No severity for a skipped test, a shared title, the starter's example values. Fix: 🟡, 🟡, 🔴.
4. A preview left running makes the tests fail. Fix: §3 says to run the preview after the tests
   and stop it.
5. The old settings file's keys and whether a moved file counts as saved settings. Fix: §0 maps
   the old keys and says it does.
6. Consent on every run or once. Fix: at each pre-launch run.
7. A trade registered with a chamber (Handwerkskammer) was missing from the regulated
   professions. Fix: added to §3.
8. Nothing said to ask for the old site's PageSpeed numbers. Fix: `relaunch.md` §3 asks, and
   says what to write when the old site cannot be tested.
9. An empty decision in `moves.csv`. Fix: "no decision yet".
10. No `-2` rule for a second comparison, and no `replaces` field in the report's settings line.
    Fix: both added.
11. Whether a re-run builds on the earlier report. Fix: §5, each run starts from the template.

## Not in the trial

S6 (its fixture would need no testimonials), S11 (a live site), S12's tracked and both-exist
arms, S15 (a public repo); S14's rendering is the unit tests'. The live re-check (12a) and a real
PageSpeed run were not tried. Noticed in the environment, not the skill: the trial's agent found
the stub server's port taken by another session's server and used the next one.
