# Working on the [SITE_NAME] website — a one-page guide for collaborators

You change the site by describing the change to an AI assistant (Codex or Claude
Code). The assistant edits the files, runs the checks, and hands the result to GitHub.
You look at the preview and press one button. The rules the assistant follows are in
`AGENTS.md` in the repository; you do not have to read them, but you can.

Repository: https://github.com/[OWNER]/[REPO] · Who to ask: [OWNER_NAME]

<!-- website-team-setup: keep the option(s) the team uses, delete the other. Fill the
     [BRACKET] slots. Translate for a non-English team, keep the four moves intact. -->

## Option A — Codex in the browser (nothing to install)

1. Open Codex in your browser (ChatGPT → Codex) and connect your GitHub account once;
   pick the repository above.
2. Start a **new task** for every change and describe it in plain words, e.g. "Update
   the opening hours on the contact page to Mon–Fri 9–17". Codex starts from a fresh
   copy of the site.
3. When Codex is done, press **Create PR**. That uploads the change as a *pull
   request* — a proposal, not yet on the site.
4. On GitHub, open the pull request: wait for the **green tick** (the automatic
   checks take a few minutes), open the **preview link** listed under the checks and
   look at your change, then [MERGE_STEP: press **Merge pull request** | tell
   [OWNER_NAME] it is ready to merge].

## Option B — Codex or Claude Code on your computer

One-time setup: follow `SETUP.md` in the repository (Node, git, the GitHub CLI, and
Codex or Claude Code), then:
```bash
git clone https://github.com/[OWNER]/[REPO].git && cd [REPO]
npm ci && npx playwright install chromium
```
Per change: open the assistant in that folder and describe the change. It fetches
the latest state first, works on its own branch, runs the checks, and uploads a pull
request. Then, on GitHub, open the pull request: wait for the **green tick**, open
the **preview link** under the checks and look at your change, then [MERGE_STEP:
press **Merge pull request**, or tell the assistant "merge" | tell [OWNER_NAME] it is
ready to merge].

## The four moves, whichever option

| Move | What it means | Who does it |
|---|---|---|
| **Start** | Get the newest state of the site before changing anything | the assistant |
| **Branch** | Work on a copy, never on the shared line | the assistant |
| **Pull request** | Upload the change as a proposal; checks and a preview run automatically | the assistant (in the browser: you press "Create PR") |
| **Merge** | Take the proposal into the site — only when green and previewed | [MERGE_RULE: **you**, for your own pull requests (the button on GitHub; an assistant on your computer also merges when you tell it to) \| the owner] |

What "merge" does on this site: [MERGE_MEANS: updates the preview at [PREVIEW_URL];
live needs `npm run ship` by [SHIP_RIGHTS] | goes live at [LIVE_URL] within minutes].

Two things to set up once. First, **protect your GitHub account** (recommended): the
website belongs to [OWNER_NAME], and anyone who gets into your account could change it.
Open https://github.com/settings/security, turn on **two-factor authentication**, and add a
**passkey**, so you sign in with your fingerprint, face or phone. It's your choice unless
GitHub asks you for it. Second, on the repository page, press the **Watch** button so GitHub
emails you when something happens to your pull request. Nothing else to set up.

## When to ask instead of pressing on

- The checks are **red**, or a message mentions a **conflict**: do not merge; ask.
- The assistant wrote a `"[MISSING: …]"` placeholder because a fact was not given:
  supply the fact, or leave the pull request as a draft until it is filled.
- The assistant says it cannot fetch, cannot push, or something "already exists":
  stop and ask. Never force anything.
- Someone else's pull request: only merge after asking them (if merging is yours to do
  at all, see the Merge row above).
