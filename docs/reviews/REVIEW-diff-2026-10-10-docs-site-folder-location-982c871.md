# DIFF review — branch docs/site-folder-location — say where a new site's folder should live
Base `3911725` · depth: Normal (steps a person follows are never Light) · verdict: CLEAN (F13 waived by the owner) · authority used: WORKTREE-WRITE — atom A (this session created the worktree `website-builder-site-folder`); BRANCH-COMMIT — atom A (this session created branch `docs/site-folder-location` and made every commit). POST AUTHORITY and GATED-THIS-DIFF not used: no PR yet, no stamp.

| Round | Head | Artifact | Reviewers: model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT (distinct, new) |
|---|---|---|---|---|---|
| 1 | 982c871 | full | fresh-eyes (host-family sub-agent, read-only); Codex (default effort, read-only); GLM 5.3 on melious (text only) | fresh-eyes 273 s / 148,189; Codex 314 s / 86,567; GLM 61 s / 13,038 | 0 / 5 / 6 |
| 2 | e6615ab | delta since 982c871 | Codex (medium, read-only); GLM 5.3 on melious | Codex 204 s / 74,109; GLM 156 s / 22,990 | 2 / 4 / 4 |
| 3 | ba81801 | delta since e6615ab | Codex (medium, read-only); GLM 5.3 on melious | Codex 116 s / 52,462; GLM 56 s / 10,875 | 1 / 0 / 1 (F13 raised again) |
| 4 | 4e37aae | delta since ba81801 | Codex (medium, read-only); GLM 5.3 on melious | Codex 72 s / 27,809; GLM 30 s / 7,322 | 0 / 0 / 1 (F13 raised again) |

24 distinct findings from 35 raw seat findings. Each round ran with `reviewers: codex OK, melious OK`.

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | RISK | fresh-eyes, GLM, Codex | 1 | the starter prompt asked for the folder after "install, restart"; the quick path had no folder step; the guide re-asked a chosen folder | fixed; externally_reverified r2 | 7b38a9f; prompt asks once, at the reopen; both prompt copies compared by script |
| F2 | RISK | fresh-eyes | 1 | test docs ran `ls .agents/skills` and `npm install` in the websites folder | fixed; externally_reverified r2 | 7b38a9f; `<site>` paths; joined with `&&` in ba81801 (F12) |
| F3 | RISK | fresh-eyes, Codex | 1 | text promised assistant behaviour (path reported, subfolder made) | fixed; externally_reverified r2 | 7b38a9f; "ask the assistant"; test docs check subfolder, untouched parent, path |
| F4 | RISK | fresh-eyes | 1 | Documents may sync to iCloud or OneDrive; the guide was silent | fixed; externally_reverified r2 | e6615ab, owner's decision: one sentence in the guide, same clause in the prompt |
| F5 | RISK | Codex, fresh-eyes, GLM | 1 | Finder/File Explorer sidebar and right-click claims unverified | fixed; externally_reverified r2 | 7b38a9f; claims removed, fallback added |
| F6–F11 | NIT | fresh-eyes, Codex, GLM | 1 | six wording points: "that folder" vs "your websites folder" and a circular "ask it"; Finder-only wording; "full path" jargon; unclear "it" in CODEX.md; workspace-install wording; "site's folder is ready" | fixed; externally_reverified r2 | 7b38a9f |
| F12 | RISK | Codex | 2 | a standalone `cd <site>` lets npm run in the old folder if the cd fails | fixed; externally_reverified r3 | ba81801; `cd <site> && npm install && …`; Codex reproduced the failed-cd case |
| F13 | RISK | Codex (r2, r3, r4), GLM | 2 | "backed up on GitHub" leaves out files git skips (`.env*`, `.dev.vars*`) | waived by the owner, 2026-10-11 | `skills/new-website/templates/.gitignore` lines 20-24, checked with `git check-ignore`; wording says "site's files"; the owner asked for one sentence |
| F14 | BUG | Codex, GLM | 2 | the sync advice, then "Open Documents" for every reader | fixed; externally_reverified r3 | ba81801; "in the place you chose above" |
| F15 | RISK | Codex | 2 | the prompt asked the folder again after step 2 | fixed; externally_reverified r3 | ba81801; the prompt has the assistant check which folder it is open in |
| F16 | BUG | Codex | 2 | README said "four steps" above three | fixed; externally_reverified r3 | ba81801; README lines 136, 140, 150 count three |
| F17 | RISK | GLM | 2 | nothing shows a GitHub remote exists when the reader is told to sync | fixed; externally_reverified r3 | ba81801; wording "you set that up with your assistant"; `SETUP.md:135`, `PUBLISHING.md:186` |
| F18–F21 | NIT | GLM | 2 | CODEX.md "inside your websites folder"; test docs "can tell you the path"; "home folder" on Windows; "It only protects" | fixed; externally_reverified r3 | ba81801; the prompt keeps "home folder", both copies identical |
| F22 | BUG | Codex, GLM | 3 | "say yes" to "is this your websites folder?" was unconditional | fixed; externally_reverified r4 | 4e37aae; "say yes only if it's the one you chose in step 1" |
| F23 | NIT | GLM | 3 | a 106-character line in the Antigravity test doc | fixed; locally_verified | 4e37aae, then 2c8c374 (see F24) |
| F24 | NIT | Codex, GLM | 4 | the F23 rewrap left a 125-character line | fixed; locally_verified | 2c8c374; not re-reviewed |

Waivers and deferrals: F13 waived by the owner, 2026-10-11, after my recommendation to waive it with the evidence that `SETUP.md:132-133` keeps Cloudflare and analytics secrets in the Cloudflare dashboard, not on the computer. His reply, verbatim: "waie push open merge".
Follow-ups: the gentle guide does not say where local keys and passwords are kept; `SETUP.md:132-133` does (F13); a workspace-only skills install also needs `export SKILLS_ROOT=…` (SKILL.md:262-266, predates this change); the README's manual install unzips into the current folder; Windows with WSL2 keeps files under a `\\wsl$` path; `<site>` is not defined in SKILL.md, so "the site gets its own folder inside the one you opened" rests on `mkdir <site>`.
Notes: round 1 had a fresh-eyes seat on the host's own model family. Rounds 2-3 were owed by fixes to instructions a reader follows; round 4 was earned by round 3's BUG (a reader could confirm the wrong folder). Stopped under (a2): round 4 had no BUG and no in-scope RISK other than F13. No final full read was run. Wording pass over the rewrap (2c8c374), Codex alone, 92 s / 55,142 tokens: no finding about the text (its words checked against SKILL.md:272-311). It raised one BUG about the pass's own brief ("one hunk in one file"), refuted: two more non-trail files changed since 4e37aae (docs/BUGLOG.md, skills/ai-seo/SKILL.md), but they came with the base merge (other PRs, already merged), not from this change; `merge_link.sh 3911725 4e37aae fb25ad7` lists only the rewrap. The base was merged at bcff443 (merge-base fb25ad7); none of its changes touch this change's files. The trail and the waiver edit are not in the reviewed artifact (docs/reviews/ is excluded). Not tested on a clean machine, in Codex, or in the desktop apps.
