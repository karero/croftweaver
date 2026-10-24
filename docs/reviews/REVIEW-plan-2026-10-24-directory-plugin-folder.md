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

## Round 2 (verification, plan at a3639d0e)

timings: codex 436s (59,517 tokens), melious 151s (23,503 tokens), fresh-eyes 174s (126,007 tokens).
F2 to F17 confirmed by the seats except as below; F1 and F12 reopened (F18, F19, F21).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F18 | codex, fresh-eyes | BUG | The new name checks fail on v0.33: README, SECURITY.md and `.gitattributes` name root files not in the branch; `mail-form-text.ts:10` names `docs/BUGLOG.md`; README:277 and `new-website/SKILL.md:566` name an excluded folder. | Fixed: both checks read kept files under `skills/` only (root files are prose, accepted); the exceptions were inventoried by grep on v0.33 and are listed by file and text, not line number. |
| F19 | codex | RISK | The scratch harness runs only `run:` blocks, so a wrong `if:` or step order escapes. | Fixed: a case reads the YAML for the step's position and `if:`. |
| F20 | fresh-eyes, melious (NIT) | RISK | The trial commit carries no `Source:` line; a missing line is undefined. | Fixed: the trial uses the same `commit-tree` line with `Source: a1f30899…`; a missing line refuses; a test case. |
| F21 | codex | RISK | `origin/directory` is a local ref: the post-push check can read stale state. | Fixed: `git ls-remote origin refs/heads/directory` must name the new commit. |
| F22 | fresh-eyes | RISK | A hand push to `stable` (the README's recovery) starts a branch run where the step never runs. | Fixed: the step also runs on that run. |
| F23 | fresh-eyes | RISK | `docs/WHAT-THE-SKILLS-RUN.md` (linked from SECURITY.md) is what the scan asks about. | Fixed: in the branch (nine files, 255 in all). |
| F24 | melious | RISK | "plugin.json declares no components" unchecked. | Fixed: stated what it holds; a test assertion. |
| F25 | melious | RISK | "A tag not on main is refused" is not in the plan. | Fixed: cited (`release-tag.yml:73-77`); the new step depends on that step. |
| F26 | melious | NIT | "After `stable` moved" is ambiguous on a re-run. | Fixed: "the Move stable step succeeded"; on a re-run its push changes nothing and succeeds. |
| F27 | melious | NIT | The `npx` count dropped wordpress-inspector's kept tests and pinned `uvx`. | Fixed: command excludes only the four folders, pattern takes `@` and `==`; still 35, 17 wrangler. |
| F28 | melious | NIT | `.gitattributes` claim unchecked. | Fixed: a test assertion. |
| F29 | melious | NIT | Root paths other than docs/scripts unchecked; match rule unspecified. | Fixed: match is the literal path; paths built from pieces are named as not caught. Other root paths: accepted as prose (F18). |
| F30 | melious | NIT | The step's fetch needs are unstated. | Fixed: `git fetch origin directory`; checkout already has `fetch-depth: 0`. |
| F31 | fresh-eyes | NIT | Match rule and line-number pinning. | Fixed with F18. |
| F32 | fresh-eyes | NIT | whats-new.sh is called, not only named. | Fixed: "called behind an `[ -f ]` check". |
| F33 | fresh-eyes | NIT | How the folder becomes a tree is unsaid. | Fixed: the script builds the tree in a temporary index from the commit's own blobs (tried on v0.33: 255 entries); the folder is unpacked from it. |

UNVERIFIABLE (codex, melious): Anthropic's page contents (the host fetched both on 2026-10-24;
quotes in the plan), GitHub Actions engine behaviour (concurrency, `if:` gating), Windows checkout.

Round 3 is earned by F18 (BUG).

## Round 3 (verification, plan at f347a826)

timings: codex 487s (79,294 tokens), melious 293s (31,334 tokens), fresh-eyes 122s (102,987 tokens).
F18 to F33 confirmed except as below. Last round with fresh-eyes (High: rounds 1 to 3).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F34 | codex (BUG), fresh-eyes (RISK) | BUG | The hand-moved `stable` run (F22) skips "Move stable", so its main-ancestry check never runs there; an off-main tag could reach `directory`. | Fixed: the new step fetches `main` and refuses a tag not on it, on both runs; a scratch case on the branch run. |
| F35 | codex (BUG), melious, fresh-eyes (NIT) | BUG | "Four lines" for six. | Fixed: six lines in three files, each by file and the path it names. |
| F36 | melious | RISK | `git fetch origin directory` fails when the branch is absent (checked: "couldn't find remote ref"); how existence is decided is unsaid; no first-run case. | Fixed: `ls-remote --exit-code` decides; fetch with an explicit refspec into `refs/remotes/origin/directory`, which every check reads; a first-run scratch case. |
| F37 | codex | RISK | A computed `+` refspec gets past a literal-text force check. | Re-sorted: rare (no ordinary edit writes one). The plan now calls it a literal-text check and names the branch rule as the guard. |
| F38 | melious | NIT | The three folder exceptions were pinned by line number. | Fixed: matched by file and literal text. |
| F39 | melious | NIT | `docs/reviews/` exempted silently. | Fixed: the plan says why (the site's own review folder, or design history on GitHub); checked by grep on v0.33 (both kinds occur). |
| F40 | fresh-eyes | NIT | plugin.json also holds `displayName`. | Fixed: the full key list. |
| F41 | fresh-eyes | NIT | "Move stable succeeded" needs a step id. | Fixed: `id: move`, and the `if:` written out. |
| F42 | melious | NIT (outside scope) | The README hand path for `directory` does not repeat the step's refusals. | Follow-up: with F22 the hand recovery is pushing `stable`, which reruns the step; the hand `commit-tree` line is only for a refused `directory` push. |

Round 4 (pair only) is earned by F34 and F35.

## Round 4 (verification, pair only, plan at b02008ae)

timings: codex 355s (83,740 tokens), melious 175s (24,292 tokens). F34 to F42 confirmed by
both seats. No BUG.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F43 | codex | RISK | Release order A, C, B with trees X, Y, X: publishing B stops green on the equal tree and leaves `Source: A`, so a late run for C passes both checks and publishes Y (older contents, silently). | Fixed: stop green only when `Source:` already names the tag's commit; otherwise commit even with an unchanged tree, so `Source:` always names the newest release; two scratch cases. Counted though rare: a silent wrong result. |
| F44 | melious | RISK | The six root-file exceptions matched by file and named path let a future unguarded line through. | Fixed (the cut for kind exception-inventory, which earned rounds 3 and 4): every exception, root-file and folder alike, matches by file and its exact full text, written in the test. |
| F45 | codex, melious | NIT (outside scope) | The README's hand `commit-tree` recovery repeats none of the step's refusals. | Follow-up, as F42. |

Round 5 is earned by F43 (kind source-order) and F44 (kind exception-inventory, cut above).

## Round 5 (verification, pair only, plan at 9ef903b0)

timings: codex 300s (48,978 tokens), melious 146s (23,452 tokens). F43 and F44 confirmed. No
BUG; no earning RISK left after the fixes below, so the rounds end here.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F46 | codex | RISK | Exact-text exceptions do not see structure: moving the unchanged `--stamp-tests` line below `fi` keeps every text but calls the missing script. | Fixed: the plan calls both checks literal-reference inventories, and adds one case that runs the stamp block from SKILL.md with no `whats-new.sh` and expects `suite_commit: unknown`. Not re-verified by a round; the final full read and wording pass read it. |
| F47 | melious | NIT | "that commit" could mean `directory`'s tip, which is never on main. | Fixed: "the commit the `Source:` line names". |
| F48 | melious | NIT | The F43 rewrite tangled the commit-tree clause. | Fixed: re-ordered. |

## Final full read (plan at a430fe7b)

Kimi K3 on ollama was meant to read it: refused, weekly quota used up (429). Stand-in, as the
skill allows: a fresh pass on the host's model (Opus 5.5, a new instance that had not seen the
plan), 227s, 126,682 tokens. No BUG.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F49 | full read | RISK | Skills name toolkit `make` targets; the branch has no Makefile; no check sees it. | Fixed as wording: accepted under "What stays as it is" and named in what the checks do not catch. No design change. |
| F50 | full read | RISK | Where the step gets the tag is unsaid; on the branch run `github.ref_name` is `stable`. | Fixed as wording: the step reads `steps.release.outputs.tag`. |
| F51 | full read | NIT | Launcher grep narrower than the checklist's list. | Fixed: grep widened (`pnpm dlx`, `yarn dlx`, `pipx run`, `uv run`); still 35. |
| F52 | full read | NIT | The workflow's header comment describes only `stable`. | Fixed: updated too. |
| F53 | full read | NIT | Status row 2 and the cost line stale. | Fixed. |
| F54 | full read | NIT | A fragment quoted as "exact full text". | Fixed: "the line beginning …"; the test holds the whole line. |

Neither RISK changes the design, so no verification round; the wording pass reads them.

## Wording pass (Codex alone, diff 9ef903b0..81b3c111)

timings: codex 294s (73,810 tokens).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F55 | codex | BUG | "About 1.3 million tokens" contradicts the trail: its figures total 959,955. | Fixed: the trail's figures (rounds 1-5 with fresh-eyes 833,273, the full read 126,682, this pass 73,810) total 1,033,765; the plan says "about 1.03 million reviewer tokens", not counting the host's own work. (The cost log holds 110,000 for the full read, an estimate typed before its figure came; this table has the real one.) |
| F56 | codex | RISK | Status row 2 claims a wording pass whose result is not in the trail. | Fixed: this section; the row now names the confirmation too. |

## Confirmation (Codex alone, diff 81b3c111..74544d67)

timings: codex 68s (39,657 tokens). It recomputed F55's sums (833,273; 959,955; 1,033,765) and
confirmed F56's record. Its one finding: status row 2 named this confirmation before the trail
recorded it; this section records it. With it the reviewer total is 1,073,422 tokens, so the
plan now says "about 1.07 million". Not re-read by a reviewer: this section and that number.

Gate closed: no BUG open; RISK F37 re-sorted as rare; F42/F45 a follow-up (the README's hand
`commit-tree` recovery repeats none of the step's refusals) for the build PR.
