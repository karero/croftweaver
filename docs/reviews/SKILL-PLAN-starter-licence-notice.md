# Plan: the starter carries Croftweaver's licence notice

Status: plan, not built. Decision row of 2026-10-29 in `docs/DECISIONS_PENDING.md` (PR #442);
the maintainer chose "build it, for 0.35" on 2026-10-29.

## What and why

Every site that `new-website` scaffolds gets Croftweaver's own files: test suites, scripts,
hooks and workflow files. MIT asks that its copyright and permission notice stay with copies
or substantial portions. Today the starter has no licence file, so a site whose owner hands the
source on (to a client or another developer) or publishes it, for example in a public GitHub
repository, carries Croftweaver's files without the notice. Whether a few test files count as
a substantial portion is not settled; this plan does not decide it and is not legal advice. It
makes the question moot at the cost of one small file.

The credit request (README, croftweaver.com/partner-assets, the ask-once step) stays as it is.
This file is about the licence, not credit.

## How

1. **The file.** `skills/new-website/templates/astro/CROFTWEAVER-LICENSE.md`: the repository's
   `LICENSE` byte for byte. Nothing is added inside it: no explanation, no link. Keeping it an
   exact copy is what lets a test compare it with one constant (the root `LICENSE`). The
   template's `README.md` gets one line in its file list: "`CROFTWEAVER-LICENSE.md`: the licence
   of the Croftweaver files in this folder (tests, scripts, hooks). Keep it when you hand the
   source on." The site's own code and content are the owner's; the line does not say otherwise.
2. **Scaffold copy.** `new-website` §3 names what it copies from the overlay. Add
   `CROFTWEAVER-LICENSE.md` to that list, in `SKILL.md` and in `templates/astro/README.md`
   (step 2).
3. **Built pages.** The file sits at the site root, outside `src/` and `public/`, so Astro never
   puts it in `dist/`. The starter's served-build test reads `dist/`; add one assertion there
   (or in `seo.spec.ts`) that no `CROFTWEAVER-LICENSE` file is in `dist/`, so a later move into
   `public/` fails.
4. **Drift for existing sites.** Add the path to `TEMPLATE_TRACKED` in `scripts/whats-new.sh`.
   `check_template_coverage.sh` then accounts for it, and for a site scaffolded before 0.35
   `whats-new` lists it as MISSING ("copy it in, there is nothing to merge"). That is the
   update route for every site scaffolded before 0.35.
5. **Name check.** `scripts/check_clean.sh` leaves the root `LICENSE` out of the name denylist,
   and already drops the lines of one copy of it, `packages/create-croftweaver/LICENSE`, by
   exact path and only while `cmp -s` finds it byte-identical (lines 251–255 and 300–302).
   The template copy gets the same treatment, the same way: one more exact path under the same
   condition, denylist only (the email, home-path and secret checks still scan it). A copy that
   has drifted is then scanned like any other file. `test_clean_denylist.sh` already has a case
   for the installer copy; add the same two cases for this path.
6. **The guard.** That exemption fails only when a drifted copy contains a listed name, so a
   drift elsewhere in the text would pass. A new check (in `make check`, beside the
   template-coverage check) fails when either copy, the installer's or the template's, is not
   byte-identical to `LICENSE`, names the file, and says how to fix it (`cp LICENSE <path>`). It
   compares bytes with `cmp`, parses nothing, and fails loudly when any of the three files is
   missing. The installer's copy has no such guard today; this one list covers both.
7. **Version.** No version bump of its own: it ships in 0.35 with the Workers work. The 0.35
   release notes get one line (a BUGLOG release-notes row, as usual).

## Scenarios

- S1. A new site scaffolded from 0.35 has `CROFTWEAVER-LICENSE.md` at its root, identical to
  the toolkit's `LICENSE`, and the built site has no such file.
- S2. Someone edits the template copy (or `LICENSE` changes, say a new year): `make check` fails
  and names the fix.
- S3. Someone moves the file into `public/`: the starter's test fails, because it would then be
  served on the site.
- S4. `make whats-new PROJECT=<a site from 0.34>` lists `CROFTWEAVER-LICENSE.md` as MISSING.
- S5. The name check still finds a denylisted name in any other file under `skills/`, including
  another `.md` in the same folder (the exemption is one exact path, not a pattern).

## Tests (what each one proves)

- The byte-compare guard: run it on the real files (pass), then, for each copy, on one with a
  byte changed and on a missing one (all fail). Proves S2 and that it cannot pass silently.
- `test_clean_denylist.sh`: a denylisted name in a sibling `.md` of the template copy (still
  caught), in the exempt copy while it equals `LICENSE` (allowed), and in a drifted exempt copy
  (caught). Proves S5.
- The starter test from step 3, run in a `git archive` copy of the template (port 4979), once
  as is and once with the file copied into `public/` (fails). Proves S1's second half and S3.
- `test_template_coverage.sh` passes with the new path tracked; `whats-new.sh` run on a scratch
  site stamped at v0.34 lists it as MISSING. Proves S4.

## Not in this plan

Adding the notice to existing sites (each takes it through `whats-new` at its next
update); a NOTICE or SPDX header in each file; any change to the credit request.

## Open for the maintainer

None. The design choices above (an exact copy, one exempt path, no bump of its own) are the
plan's; say if any should change.
