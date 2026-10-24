# Review trail: plan for a slim `directory` branch (PLAN gate, High)

Artifact: `docs/reviews/SKILL-PLAN-directory-plugin-folder.md`. Depth High: the plan adds a
workflow step that pushes a branch users install from (deploy). Seats: Codex (gpt-6.1-sol,
`CODEX_EFFORT=config`) + GLM 5.3 on melious; fresh-eyes (Opus 5.5) in rounds 1 to 3. Gate id
20261024T201702Z-44869.

## Round 1 (plan at acf5b01f)

timings: codex 299s (96,080 tokens), melious 179s (21,261 tokens), fresh-eyes 140s (112,828 tokens).

Between rounds the host read Anthropic's pre-submission checklist
(https://claude.com/docs/plugins/pre-submission-checklist) and publish page
(https://claude.com/docs/directory/publish). Its facts rewrote "What and why" (512 files and
256 KiB hold for a reviewer, they do not block; the hard limits are 50 MiB / 256 MiB / 10,000
files, and the repo is inside them), the `npx` bullet (unpinned launchers Block), the README
bullet (the security scan asks for it), and "Not checked" (updates follow the tracked branch).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F1 | codex (BUG), melious, fresh-eyes | BUG | "No SKILL.md names an excluded folder" already fails on `new-website/SKILL.md:568`, and watches SKILL.md only. | Fixed: the check covers every kept file, with the two known lines (568, `geo-check.md:448`) listed in the test; the plan states what it cannot catch (a script finding a tests folder by itself). |
| F2 | fresh-eyes | RISK | Skills point at `docs/CLOUDFLARE-CHECKLIST.md` (13 mentions) and `docs/PAGES-OR-WORKERS.md` "in the Croftweaver folder"; the branch dropped them. | Fixed: both files are in the branch; a test checks every toolkit `docs/*.md` and root `scripts/` file a kept file names is there, two named exceptions. |
| F3 | fresh-eyes | RISK | The file-list test compared the script with itself. | Fixed: the expected list is written in the test. |
| F4 | fresh-eyes | RISK | No git identity on the runner for the commit. | Fixed: `git commit-tree` with `github-actions[bot]` as author and committer; permissions comment updated. |
| F5 | fresh-eyes | RISK | A re-run adds a duplicate commit. | Fixed: equal tree stops green; a test case. |
| F6 | codex | RISK | An older release finishing later could publish older contents as a fast-forward. | Fixed: a `Source:` line records the tag's commit; the step refuses a source that is not an ancestor; a `concurrency` group; a test case. |
| F7 | codex | RISK | A second time-out does not prove size was not the cause. | Fixed: a time-out is "inconclusive"; stop and decide with the maintainer. |
| F8 | codex, melious (NIT) | RISK | Directory update behaviour after listing unchecked. | Fixed: Anthropic's publish page quoted ("by merging to the tracked branch"); still marked not yet seen for this plugin. |
| F9 | melious | RISK | Measured at 11a13e2d, trial built from v0.33. | Fixed: measured at v0.33 (a1f30899); main differs in one file. |
| F10 | melious | NIT | "Without force" as a substring check misses `-f`, `--force-with-lease`, `+refspec`. | Fixed: the test names every form. |
| F11 | melious | NIT | Size check only where the required check runs. | Partly: the 256 KiB limit is a reviewer hold, not a block, so the test warns only. Tags come from main, where the required checks run (the workflow refuses a tag not on main). |
| F12 | melious | NIT | End-to-end tree check manual and one-time. | Fixed: the workflow compares the pushed tree with the built one on every release. |
| F13 | melious | NIT | `directory` would have no branch protection. | Fixed: stated that neither `stable` nor `directory` is protected today (ruleset covers the default branch only); the rule is the maintainer's setting at step 4. |
| F14 | fresh-eyes | NIT | `directory` installs lose the whats-new stamp. | Fixed: listed under "What stays as it is", with the existing fallback line. |
| F15 | fresh-eyes | NIT | 4.4 MB was allocated size; bytes are 3.9 MB. | Fixed: byte counts. |
| F16 | fresh-eyes | NIT | The `npx` count did not reproduce. | Fixed: the exact command is in the plan (35). |
| F17 | fresh-eyes | NIT | README links to files not in the branch. | Fixed: stated and accepted. |

UNVERIFIABLE entries (both seats): the dated Validate attempts (browser evidence not kept;
the plan now says so), required-check status (memory: `plugin-tests` required since 2026-10-13;
not re-read), Windows CRLF behaviour (rests on `.gitattributes`'s comment; keeping the file is
harmless).

Round 2 is earned by F1 (BUG) and by the redesign of "What and why" from the checklist.
