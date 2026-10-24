# Plan: list Croftweaver in Anthropic's plugin directory from a slim branch

Nothing here is built. The plan waits for the plan review gate and then the maintainer's go.

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-10-24 | this file |
| 2 | Plan review gate (High: a workflow that pushes what users install) | ✅ 5 rounds, 48 findings, no BUG open; final full read (6 more); wording pass and its confirmation | `docs/reviews/REVIEW-plan-2026-10-24-directory-plugin-folder.md` |
| 3 | Trial: one slim branch pushed by hand, Validate run on it | ✅ 2026-10-24: **Validation passed** in about 20 s (`ValidatePlugin` 200): 7 checks, 0 Blocking, 9 warnings (8 download-and-run, mostly docs; no icon), 26 policy holds (16 "uses a credential from the user's machine", 10 for `og/default.jpg` named by code). Unpinned `npx` did not block. Draft cleared, nothing submitted | `directory` at `c88e1ef5` (parent `9bae3ea0`, the tree as planned); `c88e1ef5` leaves out `independent-review` (223 files) |
| 4 | Build: script, test, workflow step (one PR) | ⬜ only if step 3 gets a report | — |
| 5 | Fix what step 3's report marks Blocking (likely the `npx` lines), and the README section on what the skills contact, each its own PR | ⬜ | — |
| 6 | Directory form steps 2 to 5, then submit | ⬜ the maintainer's | — |

## What and why

Anthropic's directory (https://claude.ai/directory/manage, Submit new, Plugin bundle) checks a
plugin before it can be listed. For `karero/croftweaver@stable` with an empty plugin path, the
check timed out three times on 2026-10-16 and twice on 2026-10-24; on 2026-10-24 its
`ValidatePlugin` call returned 503 (seen in the browser's network list; no copy kept). A
three-file plugin from Anthropic's own repository passed the same check in under 45 seconds
the same day.

The repo is inside the hard limits that Anthropic's checklist
(https://claude.com/docs/plugins/pre-submission-checklist) names for "Repository too large to
validate": v0.33 (a1f30899) archives to 4.4 MB and 15 MB unpacked, 819 files, against 50 MiB,
256 MiB and 10,000. So the time-out has no documented cause. But the same checklist holds a
version for a reviewer when the plugin folder has more than 512 files or any non-image file
over 256 KiB, and the repo root has 819 files and six such files (three brand-kit tests, the
largest `test_install.py` at 448 KB, and three `docs/reviews/` raw trails). It also says
"people who install the plugin get only the plugin folder", and some checks read the whole
repository. A smaller repository is the cheapest thing to try, and is needed anyway.

So: a branch `directory` that holds the plugin and nothing else, made from each release, and
submitted as `karero/croftweaver@directory` with an empty plugin path. A branch rather than a
subfolder of `stable`: the checklist reads the rest of the repository for some checks, and
holds more for a subfolder plugin ("keep the plugin at the root of its own repository").

## What the branch holds (measured at v0.33; main at 11a13e2d differs in one file)

- `.claude-plugin/icon.png`, the listing icon (the site's moss-green mark, 512 px; the
  maintainer's choice, 2026-10-25). The portal fixes the icon at the first save or submission.
- `.claude-plugin/plugin.json`, copied as it is (same name and version). It declares no
  components today (only name, displayName, version, description, author, homepage, repository, license); the test holds that.
- `skills/`, except four folders of the toolkit's own tests, which no skill runs:
  `facts-check/scripts/tests`, `new-website/scripts/tests`, `search-console-insights/scripts/tests`,
  `website-brand-kit/scripts/tests` (158 files, 2.8 MB). `new-website` already leaves the
  brand kit's tests out of every site. `wordpress-inspector/scripts/tests` stays: its SKILL.md
  runs it. `new-website/templates/astro/tests` stays: it is the site's own suite.
- `docs/CLOUDFLARE-CHECKLIST.md` and `docs/PAGES-OR-WORKERS.md`: skills send the reader to them
  "in the Croftweaver folder" (for example `new-website/SKILL.md:167`, `search-console-setup/SKILL.md:102`,
  `new-website/references/WEBSITE_ARCHITECTURE.md:66`). And `docs/WHAT-THE-SKILLS-RUN.md`,
  which `SECURITY.md` links to: it says what the skills run, which the security scan asks about.
- `README.md`, `LICENSE`, `THIRD-PARTY-LICENSES.md`, `SECURITY.md`, copied as they are. The
  README's links to `scripts/` and other `docs/` files, and `.gitattributes`'s mention of
  `scripts/check_lf_checkout.sh`, go nowhere in the branch; accepted: these files are prose for
  people, copied verbatim, and the README stays the one source.
- `.gitattributes`, copied as it is: it keeps LF line endings on Git for Windows (its comment
  says why). It holds only `text` and `eol`, none of the attributes the checklist refuses
  (`export-ignore`, `export-subst`, `filter`).
- Not `marketplace.json` (the directory is the marketplace) and not `.agents/`.
- Not `skills/independent-review/` (the maintainer's decision, 2026-10-24, "go for the trial,
  without independent-review"): it is a review tool, not one that builds sites, and OpenAI's
  scanner flagged it three times. In the kept files it is named only as an optional escalation
  the owner opts into (`website-review/SKILL.md` checks the folder exists before offering it;
  `seo-reposition/SKILL.md`), and in the README and `docs/WHAT-THE-SKILLS-RUN.md`, which are
  prose. `new-website` does not copy it; `website-review` says to copy it from the suite,
  which the GitHub repository still holds. With it out: 223 files, 3.4 MB. The script's list and
  the test's expected list leave it out too, and the `${CLAUDE_SKILL_DIR}` and name checks run
  on what is left.

Before the icon and the `independent-review` decision, that was 255 files and 4.0 MB; with both,
224 files and 3.4 MB; the largest is the starter's `package-lock.json`, 174 KB. Two
are images (a JPEG and a PNG, both allowed). No `.DS_Store`, symlink or submodule.

## How it is made

- `scripts/build_directory_tree.sh <commit>` prints a tree id: in a temporary index
  (`read-tree --empty`), it puts `git ls-tree -r <commit>`'s entries for the kept paths, minus
  the four folders and `skills/independent-review/`, through `update-index --index-info`, then `write-tree`. The blobs are the
  commit's own, so nothing is converted. (Tried on v0.33: 255 entries.) `--out <dir>` also
  unpacks it with `git archive <tree>`, for the trial and the test.
- In `release-tag.yml`, a new last step. The "Move stable" step gains `id: move`, and the new
  step's `if:` is `steps.release.outputs.tag != '' && (steps.move.outcome == 'success' ||
  github.ref_type == 'branch')`: a tag run whose `stable` push succeeded (on a re-run that push
  changes nothing and succeeds), or the run on a hand-moved `stable`, so the README's hand
  recovery for `stable` also brings `directory` along. "Move stable" refuses a tag not on main
  (`release-tag.yml:73-77`), but it does not run on the branch run, so the new step checks it
  again itself, reading the tag from `steps.release.outputs.tag` (on the branch run
  `github.ref_name` is `stable`): `git fetch origin main`, and refuse unless the tag's commit is an ancestor of
  it. Then: `git ls-remote --exit-code origin refs/heads/directory` decides whether `directory`
  exists (exit 2: the first run); if it does, `git fetch origin
  +refs/heads/directory:refs/remotes/origin/directory`, and every check below reads
  `refs/remotes/origin/directory`. Build the tree from the tag; if `directory` exists, read the
  `Source:` line of its last commit's message, refuse when there is none, and refuse unless
  the commit the `Source:` line names is an ancestor of the tag's commit; if `Source:` already
  names the tag's commit (a re-run), stop green; else make one commit with `git commit-tree`
  (parent `directory`, none on the first run; author and committer `github-actions[bot]`;
  message "Croftweaver v0.NN" plus `Source: <tag's commit>`), even when the tree is unchanged,
  so `Source:` always names the newest release published; push it to `refs/heads/directory` without force; then `git ls-remote origin
  refs/heads/directory` must name that commit. The job already checks out with `fetch-depth: 0`.
  A `concurrency` group on the job keeps two release runs from overlapping. A refused push
  turns the run red; the README's release steps gain the hand commands (the script and the
  same `commit-tree` line). The permissions comment (`contents: write`, "nothing else is
  written") and the header comment, which describes only `stable`, are updated.
- The `main checks` ruleset covers the default branch only, and `stable` has no protection
  either. The same rule for `directory` (no deletion, no force push) is the maintainer's
  setting to add, at step 4: it is the guard against a force push, which the test below can
  check only in the step's literal text.
- Not a committed folder on main: that would hold every skill twice and drift between releases.

## What stays as it is

- The own marketplace (`.claude-plugin/marketplace.json`) and the Codex plugin
  (`.agents/plugins/marketplace.json`) keep installing the whole repo from `stable`. Moving them
  to `directory` would shrink every install, but it changes what two working routes deliver:
  a BUGLOG row, not this plan.
- Skills name toolkit `make` targets (`make whats-new`, `make test-cloudflare-check`,
  `make test-wordpress-inventory`), and the branch has no Makefile. These are for someone
  working in the toolkit's own folder; accepted, like the README's links.
- An install from `directory` has no `scripts/whats-new.sh`, so `new-website`'s stamp step
  takes its existing fallback (`suite_commit: unknown`, `new-website/SKILL.md:622`), as a zip
  install does. Whether a plugin install from `stable` keeps `.git` and so ever stamps is not
  known.
- The checklist marks an `npx` without an exact version as Blocking. The kept skills carry 35
  such lines (`git ls-files skills | grep -vE '^skills/(facts-check|new-website|search-console-insights|website-brand-kit)/scripts/tests/' | xargs grep -nE '\b(npx|bunx|uvx|pnpm dlx|yarn dlx|pipx run|uv run) ' | grep -vE '\b(npx|bunx|uvx) (-[a-z-]+ )*[a-z@/._-]+(@|==)[0-9]'`),
  17 of them `npx wrangler`, which no starter pins. Most run in a site that installs the tool
  itself; whether the validator tells the two apart is not known. Step 3's report lists the
  lines it flags, and step 5 fixes those in its own PR.
- The security scan asks the README to describe "everything the plugin runs, sends, or
  fetches". That README section is step 5, its own PR, before submitting.

## How it is tested

- `plugin-tests` (a required check) gains one test that runs the real script on `HEAD` into a
  temporary folder. Its expected list is written in the test, not read from the script:
  everything tracked under `skills/` except the four folders and `skills/independent-review/`,
  plus the icon and the nine files above. It
  checks the tree's entries against that list and each blob against the commit's; that every
  path the existing `${CLAUDE_SKILL_DIR}` test resolves exists in the tree; that `plugin.json`
  declares no component paths (or each resolves in the tree); that `.gitattributes` holds no
  `export-ignore`, `export-subst` or `filter`. Two name checks read the kept files under
  `skills/` only (what an assistant follows; the root files are prose for people):
  - every tracked toolkit `docs/*.md` or root `scripts/` file they name, as the literal path, is
    in the tree. `docs/reviews/` is left out: skills name it for the site's own review folder
    (independent-review writes its trails there) or for design history ("in the Croftweaver
    repo"), which no skill needs to run and which stays readable on GitHub. Six lines in three
    files are allowed, each matched by file and its exact full text, written in the test (a
    changed or new line fails until someone checks it): `new-website/SKILL.md`'s four lines
    naming `scripts/whats-new.sh` (606, 612, 614, 618 at v0.33: called behind an `[ -f ]`
    check, with the fallback above); `independent-review/scripts/melious_models.txt`'s one
    naming `scripts/check_model_agnostic.sh` (a comment); `website-contact-form/templates/mail-form-text.ts`'s
    one naming `docs/BUGLOG.md` (a comment);
  - none names one of the four folders, either as `<skill>/scripts/tests` or, inside that skill,
    as `scripts/tests`, except three lines, each matched by file and its exact full text: in `new-website/SKILL.md`,
    the line beginning "# The brand kit's scripts/tests is the toolkit's own test suite" and
    `rm -rf "$PROJECT_SKILLS_DIR"/website-brand-kit/scripts/tests` (they remove it from sites);
    in `search-console-insights/references/geo-check.md`, the line beginning "Tests:
    `scripts/tests/test_geo_check.py`" (describes one). The test holds each whole line.
  Both are inventories of literal references: they do not see where a line sits. So one more
  case runs `new-website`'s stamp block, taken from SKILL.md, with no `scripts/whats-new.sh`
  beside it, and expects `suite_commit: unknown` and exit 0.
  As a warning in its output only: the file count and any non-image file over 256 KiB (the
  reviewer-hold limits, not blocks). What the checks do not catch: a path built from pieces,
  a script that finds a tests folder by itself, and `make` targets (accepted above).
- The workflow tests in `scripts/plugin.test.mjs` already run `release-tag.yml`'s `run:`
  blocks on a scratch repo; they do not run its `if:` lines. New cases: read from the YAML, the
  step is last and its `if:` is the condition above; run on a scratch repo, the first run
  (no `directory`) makes a parentless commit, a re-run pushes nothing, a newer release with an unchanged tree still advances `Source:`,
  releases A, B and then a late run for C (between them) is refused, an older tag than
  `directory`'s source is refused, a `directory` tip with no `Source:` line is refused, a tag
  not on main is refused on the branch run; and no `git push` in the step's text carries
  `-f`, `--force` in any form, or a `+` refspec (a literal-text check only).
- Step 3 is the trial:
  1. With the maintainer's go, push one branch `directory` by hand: the tree from the steps
     the script will use, from the v0.33 tag, in one commit made with the same `commit-tree`
     line ("Croftweaver v0.33", `Source: a1f308998e8d412fb3fa9df77a02248fd5c1c6e8`).
  2. He signs in at https://claude.ai/directory/manage, chooses Plugin bundle, enters
     `karero/croftweaver`, branch `directory`, empty plugin path, and runs Validate. Nothing is
     submitted.
  3. A report: write down every finding and its result (Blocks, Policy hold, Warning, Note);
     step 4 follows, and step 5 takes the Blocking ones. A time-out again: inconclusive (an
     unknown limit, or the service); stop and decide with him whether to retry later or delete
     the branch.
- After the first release with step 4: the run is green, and its last check has found the new
  commit on GitHub's `directory`.

## Not checked

- Updates: Anthropic's page https://claude.com/docs/directory/publish says the listing keeps
  current "by merging to the tracked branch"; each new commit is scanned and served once
  published. Not yet seen for this plugin.
- Why the repo root times out. The trial says only whether this tree gets a report.

Cost of the plan gate at High: 5 rounds (Codex at its configured effort and GLM 5.3 on melious
every round, fresh-eyes on the host's model in rounds 1 to 3), 54 findings with the final full read, about 1.07 million
reviewer tokens (the trail's figures); the host's own work is not counted. No red team: the
plan touches no user data, logins, money or schema, and deletes nothing without his go.
