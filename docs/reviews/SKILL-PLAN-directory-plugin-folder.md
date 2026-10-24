# Plan: list Croftweaver in Anthropic's plugin directory from a slim branch

Nothing here is built. The plan waits for the plan review gate and then the maintainer's go.

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-10-24 | this file |
| 2 | Plan review gate (High: a workflow that pushes what users install) | ⏳ | trail in `docs/reviews/` |
| 3 | Trial: one slim branch pushed by hand, Validate run on it | ⬜ waits for the go | — |
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

- `.claude-plugin/plugin.json`, copied as it is (same name and version; it declares no
  components, so it points at nothing outside the branch).
- `skills/`, except four folders of the toolkit's own tests, which no skill runs:
  `facts-check/scripts/tests`, `new-website/scripts/tests`, `search-console-insights/scripts/tests`,
  `website-brand-kit/scripts/tests` (158 files, 2.8 MB). `new-website` already leaves the
  brand kit's tests out of every site. `wordpress-inspector/scripts/tests` stays: its SKILL.md
  runs it. `new-website/templates/astro/tests` stays: it is the site's own suite.
- `docs/CLOUDFLARE-CHECKLIST.md` and `docs/PAGES-OR-WORKERS.md`: skills send the reader to them
  "in the Croftweaver folder" (for example `new-website/SKILL.md:167`, `search-console-setup/SKILL.md:102`,
  `new-website/references/WEBSITE_ARCHITECTURE.md:66`).
- `README.md`, `LICENSE`, `THIRD-PARTY-LICENSES.md`, `SECURITY.md`, copied as they are. The
  README's links to `scripts/` and other `docs/` files go nowhere in the branch; accepted, since
  on the listing they are links, and the README stays the one source.
- `.gitattributes`, copied as it is: it keeps LF line endings on Git for Windows (its comment
  says why). It holds only `text` and `eol`, none of the attributes the checklist refuses
  (`export-ignore`, `export-subst`, `filter`).
- Not `marketplace.json` (the directory is the marketplace) and not `.agents/`.

That is 254 files and 3.9 MB; the largest is the starter's `package-lock.json`, 174 KB. Two
are images (a JPEG and a PNG, both allowed). No `.DS_Store`, symlink or submodule.

## How it is made

- `scripts/build_directory_tree.sh <commit> <dir>`: `git archive <commit>` with the paths above
  and the four exclusions as pathspecs, unpacked into `<dir>`.
- In `release-tag.yml`, a new last step that runs only on a release tag and only after `stable`
  moved in the same run: build the tree from the tag; read the tag's commit recorded in
  `origin/directory`'s last commit (a `Source:` line in its message) and refuse unless that
  commit is an ancestor of this tag's; if the built tree equals `origin/directory`'s tree,
  stop green (a re-run); else make one commit with `git commit-tree`, parent
  `origin/directory` (none on the first run), author and committer `github-actions[bot]`,
  message "Croftweaver v0.NN" plus `Source: <tag's commit>`; push it to `refs/heads/directory`
  without force; then check that `origin/directory`'s tree is the built tree.
  A `concurrency` group on the job keeps two release runs from overlapping. A refused push
  turns the run red, and the README's release steps say how to push by hand, as they do for
  `stable`. The permissions comment (`contents: write`, "nothing else is written") is updated.
- The `main checks` ruleset covers the default branch only, and `stable` has no protection
  either. The same rule for `directory` (no deletion, no force push) is the maintainer's
  setting to add, at step 4.
- Not a committed folder on main: that would hold every skill twice and drift between releases.

## What stays as it is

- The own marketplace (`.claude-plugin/marketplace.json`) and the Codex plugin
  (`.agents/plugins/marketplace.json`) keep installing the whole repo from `stable`. Moving them
  to `directory` would shrink every install, but it changes what two working routes deliver:
  a BUGLOG row, not this plan.
- An install from `directory` has no `scripts/whats-new.sh`, so `new-website`'s stamp step
  takes its existing fallback (`suite_commit: unknown`, `new-website/SKILL.md:622`), as a zip
  install does. Whether a plugin install from `stable` keeps `.git` and so ever stamps is not
  known.
- The checklist marks an `npx` without an exact version as Blocking. Skills carry 35 such lines
  (`git ls-files skills | grep -v /scripts/tests/ | xargs grep -nE '\b(npx|bunx|uvx) ' | grep -vE 'npx (-[a-z-]+ )*[a-z@/._-]+@[0-9]'`),
  17 of them `npx wrangler`, which no starter pins. Most run in a site that installs the tool
  itself; whether the validator tells the two apart is not known. Step 3's report lists the
  lines it flags, and step 5 fixes those in its own PR.
- The security scan asks the README to describe "everything the plugin runs, sends, or
  fetches". That README section is step 5, its own PR, before submitting.

## How it is tested

- `plugin-tests` (a required check) gains one test that runs the real script on `HEAD` into a
  temporary folder. Its expected list is written in the test, not read from the script:
  everything tracked under `skills/` except the four folders, plus the eight files above. It
  checks the file list and every file's bytes against that; that every path the existing
  `${CLAUDE_SKILL_DIR}` test resolves exists in the tree; that every toolkit `docs/*.md` (not
  `docs/reviews/`) and root `scripts/` file named in a kept file is in the tree, except
  `scripts/whats-new.sh` and `scripts/check_model_agnostic.sh` (named in comments, with the
  fallback above); that no kept file outside the four folders names one of them by its path,
  except the lines listed in the test (`new-website/SKILL.md:568` removes one from sites,
  `geo-check.md:448` describes one); and, as a warning in its output only, the file count and
  any non-image file over 256 KiB (the reviewer-hold limits, not blocks). What it does not
  catch: a script that finds a tests folder by itself, without naming its path.
- The workflow tests in `scripts/plugin.test.mjs` already run `release-tag.yml`'s shell blocks.
  New cases, on a scratch repo: the step runs only after `stable` moved on a release tag; a
  re-run pushes nothing; an older tag than `directory`'s source is refused; no `git push` in the
  step carries `-f`, `--force` in any form, or a `+` refspec.
- Step 3 is the trial:
  1. With the maintainer's go, push one branch `directory` by hand, built with the same steps
     the script will use, from the v0.33 tag.
  2. He signs in at https://claude.ai/directory/manage, chooses Plugin bundle, enters
     `karero/croftweaver`, branch `directory`, empty plugin path, and runs Validate. Nothing is
     submitted.
  3. A report: write down every finding and its result (Blocks, Policy hold, Warning, Note);
     step 4 follows, and step 5 takes the Blocking ones. A time-out again: inconclusive (an
     unknown limit, or the service); stop and decide with him whether to retry later or delete
     the branch.
- After the first release with step 4: the run is green, and its last check has compared the
  pushed tree with the built one.

## Not checked

- Updates: Anthropic's page https://claude.com/docs/directory/publish says the listing keeps
  current "by merging to the tracked branch"; each new commit is scanned and served once
  published. Not yet seen for this plugin.
- Why the repo root times out. The trial says only whether this tree gets a report.

Expected cost: the plan gate at High (Codex at its configured effort, GLM 5.3 on melious, and a
fresh-eyes pass on the host's model in rounds 1 to 3), likely 3 to 5 rounds. No red team: the
plan touches no user data, logins, money or schema, and deletes nothing without his go.
