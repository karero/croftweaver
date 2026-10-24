# Plan: list Croftweaver in Anthropic's plugin directory from a slim branch

Nothing here is built. The plan waits for the plan review gate and then the maintainer's go.

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-10-24 | this file |
| 2 | Plan review gate (High: a workflow that pushes what users install) | ⏳ | trail in `docs/reviews/` |
| 3 | Trial: one slim branch pushed by hand, Validate run on it | ⬜ waits for the go | — |
| 4 | Build: script, test, workflow step (one PR) | ⬜ only if step 3 passes | — |
| 5 | Directory form steps 2 to 5, then submit | ⬜ the maintainer's | — |

## What and why

Anthropic's directory (https://claude.ai/directory/manage, Submit new, Plugin bundle) checks a
plugin before it can be listed. For `karero/croftweaver@stable` with an empty plugin path, the
check timed out three times on 2026-10-16 and twice on 2026-10-24; on 2026-10-24 its
`ValidatePlugin` call returned 503. A three-file plugin from Anthropic's own repository passed
the same check in under 45 seconds the same day. The likely cause is size: the repo root at
v0.33 has 819 files, six non-image files over 256 KiB (three are the brand kit's tests, the
largest `test_install.py` at 448 KB; three are `docs/reviews/` raw trails), and every review trail.

A plugin needs only `.claude-plugin/plugin.json` and `skills/`. So: a branch `directory` that
holds the plugin and nothing else, made from each release, and submitted as
`karero/croftweaver@directory` with an empty plugin path.

## What the branch holds (measured on main at 11a13e2d)

- `.claude-plugin/plugin.json`, copied as it is (same name, same version: the version is what
  tells an installed plugin there is an update).
- `skills/`, except four folders of the toolkit's own tests, which no skill runs:
  `facts-check/scripts/tests`, `new-website/scripts/tests`, `search-console-insights/scripts/tests`,
  `website-brand-kit/scripts/tests` (158 files, about 3.2 MB). `new-website` already leaves the
  brand kit's tests out of every site. `wordpress-inspector/scripts/tests` stays: its SKILL.md
  runs it. `new-website/templates/astro/tests` stays: it is the site's own suite.
- `README.md`, `LICENSE`, `THIRD-PARTY-LICENSES.md`, `SECURITY.md`, copied as they are.
- `.gitattributes`, copied as it is: without it, Git for Windows checks the scripts out with
  CRLF and they fail (the file's own comment says why).
- Not `marketplace.json` (the directory is the marketplace) and not `.agents/`.

That is about 252 files and 4.4 MB; the largest left is the starter's `package-lock.json`,
174 KB, so no file over 256 KiB. Counts from `git ls-files`; the exact ones go in the PR.

## How it is made

- `scripts/build_directory_tree.sh <commit> <dir>`: `git archive <commit>` with the paths above
  and the four exclusions as pathspecs, unpacked into `<dir>`. The list lives in this script only.
- In `release-tag.yml`, a new last step, after `stable` has moved: build the tree from the tag,
  make one commit whose parent is the current `origin/directory` (none on the first run), with
  the message "Croftweaver v0.NN from <tag's commit>", and push it to `refs/heads/directory`
  without force. Every release is a fast-forward, so the push cannot lose history; a refused
  push turns the run red, and the README's release steps say how to push it by hand, as they do
  for `stable`.
- Not a committed folder on main: that would hold every skill twice and drift between releases.

## What stays as it is

- The own marketplace (`.claude-plugin/marketplace.json`) and the Codex plugin
  (`.agents/plugins/marketplace.json`) keep installing the whole repo from `stable`. Moving them
  to `directory` would shrink every install, but it changes what two working routes deliver:
  a BUGLOG row, not this plan.
- `.gitattributes` at the root: unchanged. Nothing has shown that the directory objects to it;
  if step 3's checks name it, that is a finding for step 4.
- The 35 `npx` lines in skills without a version (17 of them `npx wrangler`, which no starter
  pins; the rest run tools the site itself installs): unchanged unless step 3's checks name them.
  Then pinning is its own PR.
- A README section naming each outside service a skill contacts: the form's data-handling step
  (step 5) asks for it, and only after a pass. It is written then, as its own PR, from the list
  that form actually asks for.

## How it is tested

- `plugin-tests` (a required check) gains one test that enters through the real script: it builds
  the tree from `HEAD` into a temporary folder and checks that its file list is exactly
  `git ls-files` of the kept paths minus the four folders, byte for byte; that every path the
  existing `${CLAUDE_SKILL_DIR}` test resolves also exists in the tree; that no SKILL.md in the
  tree names one of the four folders; and that no file is over 256 KiB. The test fails if a
  skill starts running its own tests, or if a new large file lands, before any release.
- The workflow tests in `scripts/plugin.test.mjs` already read `release-tag.yml`; one more holds
  that the new step runs after `stable` moved, on a release tag only, and pushes without force.
- Step 3 is the test of the cause. Its result decides step 4:
  1. With the maintainer's go, push one branch `directory` by hand, built with the same steps
     the script will use, from the v0.33 tag.
  2. He signs in at https://claude.ai/directory/manage, chooses Plugin bundle, enters
     `karero/croftweaver`, branch `directory`, empty plugin path, and runs Validate. Nothing is
     submitted.
  3. Pass: write down every check it lists; step 4 follows. Time-out again: size was not the
     cause; stop, and delete the branch with his go.
- After the first real release with step 4: the run is green, and `git ls-remote origin
  directory` names a commit whose tree matches the script's output for the tag.

## Not checked

- Whether the directory takes a branch other than the default as the place it reads updates
  from, or copies one commit at submission and wants a new submission each release. The form
  asks for a branch; what happens after a listing is not known.
- Whether the time-out has a size limit behind it, and where. The trial says only whether this
  size passes.

Expected cost: the plan gate at High (Codex at its configured effort, GLM 5.3 on melious, and a
fresh-eyes pass on the host's model in rounds 1 to 3), likely 3 to 5 rounds. No red team: the
plan touches no user data, logins, money or schema, and deletes nothing without his go.
