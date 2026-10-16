# DIFF review — branch `feat/installer-checks-sha256sums` — create-croftweaver 0.2.0 checks the zip against the release's SHA256SUMS; a publish guard

Base `38b6878` · depth: High (code that downloads files and writes them into the folder an AI assistant loads instructions from; a publish step that can stop every install) · verdict: CLEAN · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch); POST AUTHORITY — atom B (the owner, 2026-10-16: "I'd prefer to do everything in 0.32", and the chosen option "Fix locally … then the PR")

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `103e466` | full since `38b6878` | Codex gpt-6.1-sol, config effort, read-only; GLM 5.3 on melious; fresh-eyes Claude Opus sub-agent | Codex 269 s, 60,535; melious 316 s, 24,336; fresh-eyes 268 s, 125,377 | 1/5/7 |
| 2 | `ef54587` | delta since `103e466` | Codex (config); GLM 5.3; fresh-eyes Opus | fresh-eyes 151 s, 101,183 | 0/2/4 |
| 3 | `279e4ab` | delta since `ef54587` | Codex (config); GLM 5.3; fresh-eyes Opus | Codex 228 s, 53,047; melious 261 s, 15,269; fresh-eyes 331 s, 101,868 | 0/4/4 |
| final full read | `b60ba5e` | full since `38b6878` | fresh Claude Opus sub-agent (Kimi on ollama FAILED: quota) | 295 s, 124,314 | 0/2/6 |
| re-gate | `5c09fe0` | delta since `279e4ab` | Codex (config); GLM 5.3 | Codex 256 s, 57,358; melious 264 s, 21,823 | 1/1/4 |
| confirmation | `f3dc1c9` | delta since `5c09fe0` | Codex (config); GLM 5.3 | Codex 189 s, 43,658; melious 243 s, 13,468 | 0/1/1 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| I1 | BUG | Codex | 1 | a test comment said SHA256SUMS proves the zip was the one built and tested | fixed, externally_reverified (r2) | comment now: catches damaged, cut short, another release's; only as trustworthy as its release. A comment: not substantive |
| I2 | RISK | Codex, GLM | 1 | GitHub's redirects and asset paths shown only by the stub | refuted | live curl 2026-10-16: `latest/download/croftweaver.zip` → 302 `/releases/download/v0.31/croftweaver.zip`; `download/v0.31/croftweaver.zip` → 302 `release-assets.githubusercontent.com/…`; `download/v0.31/SHA256SUMS` → 404 |
| I3 | RISK | GLM | 1 | nothing shown that writes SHA256SUMS | refuted | `scripts/package.sh` 142–148; README `gh release create … dist/SHA256SUMS` |
| I4 | NIT | GLM | 1 | pin `from` on any redirect | refuted | a tag's download URL redirects to file storage (I2) |
| I5 | NIT | GLM, fresh-eyes | 1 | the 404 message named a version | fixed, externally_reverified (r2) | |
| I6 | RISK | fresh-eyes | 1 | no test pinned the check before the unpack | fixed, externally_reverified (r2) | subtest; moving the call after `unpackSkills` → 2 fail |
| I7 | RISK | fresh-eyes, GLM | 1, 2 | publishing 0.2.0 before a release with SHA256SUMS stops every install | fixed, externally_reverified (re-gate, confirmation) | `prepublishOnly` guard, now running the installer itself; README step; live today: exit 1 |
| I8 | NIT | fresh-eyes | 1 | WHAT-THE-SKILLS-RUN overstated what the check catches | fixed, externally_reverified (r2) | |
| I9 | NIT | fresh-eyes | 1 | `res.text()` outside the try | fixed, externally_reverified (r2, probed) | |
| I10 | NIT | fresh-eyes | 1 | `decodeURIComponent` throws on a stray % | fixed, externally_reverified (r2, probed); tested after the final read | %-escaped name test; removing the decode → 2 fail |
| I11 | NIT | fresh-eyes | 1 | the 2026-10-14 BUGLOG row still open | fixed | row marked fixed on this branch, live once 0.2.0 is on npm |
| R2-1 | NIT | fresh-eyes, GLM | 2 | the order test asserted the message only | fixed, externally_reverified (r3) | also tree unchanged, no escaped.txt |
| R2-2 | NIT | fresh-eyes, GLM | 2 | a paragraph not rewrapped | fixed | |
| R3-1 | RISK | Codex, GLM, fresh-eyes | 3 | the guard passed a doubled line and did not compare the hash | fixed, externally_reverified (re-gate) | owner: "Fix locally"; the guard now runs the installer |
| R3-2 | RISK | fresh-eyes | 3 | npm skips `prepublishOnly` under ignore-scripts or a .tgz | fixed | README runs `npm run prepublishOnly` by hand first; npm 11.20.0 `lib/commands/publish.js` read by the reviewer |
| F-1 | RISK | final read | final | the guard was a second copy and already drifted (BOM, %-name, redirect regex, 500 wording) | fixed, externally_reverified (re-gate) | the guard runs `index.mjs` into a throwaway folder |
| F-2 | RISK | final read | final | only package changes ran the check, though every release is load-bearing | fixed, externally_reverified (re-gate) | README: run it after every release |
| F-3…6 | NIT | final read | final | override during publish; untested decode; a doc line; a misreported 500 | fixed, externally_reverified (re-gate) | |
| RG1 | BUG | Codex | re-gate | the README said a failing check means every install fails | fixed, externally_reverified (confirmation, Codex clean) | README now tells a passing network error from a refused release |
| RG2 | RISK | GLM | re-gate, confirmation | the throwaway folder holds only if the installer reads nothing else | refuted (leg a); follow-up (leg b) | `index.mjs`: `claude.dir()` = `CLAUDE_SKILLS_DIR` or `os.homedir()/.claude/skills`; backup beside `realpathSync(dest)`; no --codex/--antigravity passed. GLM is text-only and could not open it; Codex, with files, found nothing. Leg b (the test cannot see a write outside the throwaway home) is a follow-up |
| RG3–5 | NIT | Codex, GLM | re-gate | a hedged regex; only line 1 printed; the connection-refused case dropped | fixed, externally_reverified (confirmation) | |
| C-1 | NIT | GLM | confirmation | spawnSync gives the child a stdin pipe | follow-up | the installer reads no input (only argv) |

Waivers and deferrals: none.
Follow-ups: RG2 leg b (point the guard's TMPDIR into the test home so a stray write would show); C-1 (`stdio: ['ignore','pipe','pipe']`); after 0.32 is live, one real `npm create croftweaver` and `node packages/create-croftweaver/check-release.mjs`.
Notes: data check 2026-10-16: no keys or customer data in the diff. Consent for Codex and melious as for #345 in the same session. The final full read ran on a fresh host-family Opus sub-agent because ollama was out of quota (no Kimi). Rounds stopped after 3 (no BUG in round 3); the re-gate and its confirmation are the two re-gate attempts closeout allows. Stamp seats: Codex and GLM, unbroken chain `103e466` → `ef54587` → `279e4ab` → `5c09fe0` → `f3dc1c9`.
