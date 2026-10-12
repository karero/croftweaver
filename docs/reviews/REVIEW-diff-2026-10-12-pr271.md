# DIFF review — karero/croftweaver#271 — `new-website` asks once for a credit after the site is live; the README asks for the same

Base `origin/main` (`d382cbe` for rounds 1 to 3 and both re-gates; `4e5ff23` after the merge of `main`) · depth: **Normal** (`skills/new-website/SKILL.md` is an instruction file an assistant follows; the README sentences alone would be Light, and a mixed diff takes its riskiest file's depth) · verdict: **CLEAN** · authority used: WORKTREE-WRITE, BRANCH-COMMIT and POST AUTHORITY — atom A, this session created the worktree, the branch and the PR; GATED-THIS-DIFF — atom A, the verification chain in the first table

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `e7eb4a9` | full, `origin/main...e7eb4a9` without `docs/reviews/` | codex-cli 0.162.1, `gpt-6.1-sol`, effort from its config file, read-only · `glm-5.3` on Melious, HTTP API, text only · fresh-eyes: a `sonnet` sub-agent with no shared context, read-only | codex 270 s, 88,735 · melious 86 s, 14,160 · fresh-eyes 82 s, 105,073 | 1 / 3 / 5 after dedup (raw 1 / 4 / 6) |
| 2 | `88ccf22` | delta since `e7eb4a9` | codex at medium · melious as above | codex 117 s, 53,075 · melious 77 s, 13,984 | 0 / 1 / 1 |
| 3 | `9961e09` | delta since `88ccf22` | the same pair | codex 71 s, 28,659 · melious 58 s, 12,999 | 0 / 1 / 2 |
| re-gate 1 (not a round) | `f938274` | delta since `9961e09` | the same pair | codex 78 s, 35,567 · melious 108 s, 12,381 | 0 / 1 / 1 |
| re-gate 2 (not a round) | `8148500` | delta since `f938274` | the same pair | codex 62 s, 36,042 · melious 26 s, 6,976 | 0 / 0 / 0 |
| merge link (not a round) | `8255822` | `merge_link.sh d382cbe 8148500 4e5ff23`: one hunk, written on `main`, in another section of `README.md` | codex at medium | codex 60 s, 38,356 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | RISK | codex | 1 | The answer was recorded after installing and publishing, so an interrupted session let a later one ask again | fixed `88ccf22`; locally_verified; externally_reverified in round 2 | "**Record the answer first**, before any other step" is the first bullet after the options |
| F2 | RISK | codex, fresh-eyes | 1 | The code fetched from the partner page might fail the starter's image test (description, size, loading setting) | refuted; one sentence added in `88ccf22` | The site's `image` helper emits `alt`, `width`, `height` and `loading="lazy"` (`src/pages/partner-assets.astro` lines 44-45 in the site's repository), and its `tests/navigation.spec.ts` asserts them for every HTML snippet. Added for a later change of that page: "if a test objects to the pasted code, tell the user and do not change the test" |
| F3 | RISK | melious | 1 | The assistant pasted whatever the remote page served, with no check of its shape | fixed `88ccf22`, sharpened by F11; externally_reverified in rounds 2 and 3 | "The HTML is one `<a>` link around one `<img>` … If the page offers anything else … do not paste it: tell the user." |
| F4 | BUG (wording, not substantive) | codex; melious as NIT | 1 | "allow images from the site itself only" is wrong: the starter's rule also allows `data:` images | fixed `88ccf22`; externally_reverified in round 2 | Now "the starter's security rules block images from other sites"; `templates/astro/public/_headers` line 12 has `img-src 'self' data:` |
| F5 | NIT | codex | 1 | The checklist item "Credit asked once" left out the outcome "already in the footer" | fixed `88ccf22`; externally_reverified in round 2 | "**Credit settled** (§4b) … asked once, or found already in the footer" |
| F6 | NIT | melious | 1 | "otherwise skip silently" contradicted the third condition, which records a line | fixed `88ccf22`; externally_reverified in round 2 | "Ask only when all three hold; otherwise do not ask:" |
| F7 | NIT | fresh-eyes | 1 | The bare folder address of the badge files may not answer | fixed `88ccf22`; externally_reverified in round 2 | "save each file the chosen code's note names, from `https://croftweaver.com/brand/badge/<file name>`" |
| F8 | NIT | fresh-eyes | 1 | "licence" where the repository writes "license" | fixed `88ccf22`; externally_reverified in round 2 | At `origin/main` in `skills/*.md`, `README.md` and `docs/*.md`: "license" 6 times, "licence" none |
| F9 | NIT | fresh-eyes | 1 | Nothing tied the ask to the launch; a later session on an older site would pass all three conditions | fixed `88ccf22`; externally_reverified in round 2 | "This step belongs to the launch checklist (§4). Do not raise it in a later session that is doing other work on the site" |
| F10 | RISK | melious | 2 | Recording first left a state nothing could finish: "credit: badge" in the README, the session cut short before the code was pasted | fixed `9961e09`; externally_reverified in round 3 | The "unfinished yes" exception. `caused-by: F1 (introduced)` |
| F11 | NIT | melious | 2 | The shape rule also fitted the page's Markdown code | fixed `9961e09`; externally_reverified in round 3 | "Use the page's HTML code, never its Markdown code, which is for a README." |
| F12 | RISK | codex; again by both seats in re-gate 1 | 3 | The exception looked at the source footer, so a credit that was pasted (and even committed) but never published switched it off | fixed in two steps, `f938274` then `8148500`; externally_reverified in re-gate 2 | The exception now reads "the footer of the live site has no link to `croftweaver.com`", which is true in every interrupted state. `caused-by: F10 (partial)` |
| F13 | NIT | melious | 3 | "the footer" could mean the live site's or the source file's | fixed `f938274`, `8148500`; externally_reverified in both re-gates | The first ask reads "the footer in the site's source"; the exception reads "the footer of the live site" |
| F14 | NIT | melious | 3 | The exception had no end state for "not now" or for no answer | fixed `f938274`; externally_reverified in re-gate 1 | "On any other answer, or none, change the line to "credit: declined"." |

Waivers: none. Deferrals: none.

Follow-ups (raised outside a pass's scope, or in a re-gate; none blocks):
- FU1 (melious, round 2): "No answer" is recorded as declined, which also settles it for a user who only missed the message. Kept: section 2a of the same file does the same.
- FU2 (melious, round 2): the message says the credit "links to croftweaver.com" while the code links to `croftweaver.com/partner-assets?ref=badge`. True as written; the owner has decided that the code will link to the home page.
- FU3 (melious, re-gate 1): a session that ends between "say so once" and the user's answer leaves the README line unchanged, so the next session says it once more.
- FU4 (melious, re-gate 2): a session that ends between the user's answer and its recording leaves no line, so a later run of the launch checklist asks again.
- The size guard warns that `skills/new-website/SKILL.md` is 705 lines, over its 500-line soft budget. It was over before this change, which adds 69 lines; moving section 4b to `references/` would cut them.

## Test record, taken before round 1

- Command: `make check` in the worktree at head `7eeb4f5404d5a58c9db12759bb6fd8c555f440b7`, started 2026-10-12T18:56:47Z.
- Result: exit status 0; 1,083 lines of output; no line starting `not ok` or `FAIL`.
- Skipped, 7: the minimum-Perl check (`Perl::MinimumVersion` is not installed on this machine) and six shell tests that need `/proc`. CI runs both.
- An earlier complete run on `d4376c6` (the first commit, before the README sentences and the wording fix) also ended with exit status 0 and the same 7 skips.
- The whole output of the run on `7eeb4f5` is in a second comment on the PR, linked from the review comment.
- No test covers the wording of section 4b: it is prose an assistant follows, and the suite has no check of what an assistant asks.
- After the review's fixes and the merge of `main`, `make check` was not run again on this machine. On the merged head, `scripts/check_clean.sh` and `scripts/check_skill_budgets.sh` were run and ended with exit status 0, the second with the warning named under Follow-ups. CI runs the whole of it on the pushed head.

## Files the change takes

`skills/new-website/SKILL.md` (69 lines added) and `README.md` (5 lines added), plus this trail. The README commit `fa4c94a` is a cherry-pick of `f8f035d`, written on 2026-10-10 by an earlier session on the local branch `docs/readme-credit-line` and never pushed.

Notes:
- Three rounds, 14 findings; none of them a substantive BUG, so the rounds ended after round 3. Round 3's RISK and NITs were fixed on the owner's standing preference that review findings are fixed, not carried over, and those fixes were then read by both seats in two re-gates.
- A chain of three: F1's fix caused F10, and F10's fix left F12. Each was a gap in the bookkeeping of "asked once". It ended when the exception stopped tracking steps and looked at the live footer instead.
- Fresh-eyes ran in round 1 only, by design at this depth. No final full read is due: the depth is Normal and the change is not a spec. The stamp for the merged head relies on Codex's chain, which includes the merge link; Melious's chain ends at `8148500`.
- UNVERIFIABLE entries (questions, not findings): 12 asked in round 1 and looked at, none confirmed beyond the rows above. In later passes the seats kept three open that this repository cannot settle: what the partner page serves, what a browser does with the deployed headers, and whether an assistant follows the section.
- Data check: the diff and the briefs hold no credentials and no private names. Destinations: Codex, and GLM 5.3 on Melious, the owner's standing pair for this repository; the repository is public. The briefs quote the constants of `src/pages/partner-assets.astro` from the site's repository that produce the code shown on the public page. Outside this repository: that code links to the page itself today; the owner decided on 2026-10-12 that it will link to the home page, and that change is not made yet.
