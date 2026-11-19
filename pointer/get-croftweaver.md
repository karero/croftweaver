---
name: get-croftweaver
description: Explains what Croftweaver is and gives the commands to install it, for the owner to type. This plugin only points the way and holds none of Croftweaver's own skills. Use when someone asks about Croftweaver, how to install it, or wants to build a small-business website with it.
---

# Get Croftweaver

This plugin only points the way. Croftweaver is a separate, free, open-source kit (MIT licence,
https://github.com/karero/croftweaver): skills an AI coding assistant follows to build, test
and launch a small-business website the owner keeps, on Astro, GitHub and Cloudflare.

1. Say that in two sentences, and that this plugin installs nothing by itself.
2. Ask which assistant they will build with: Claude Code, Codex or Antigravity. Croftweaver runs
   in one of them, in a folder on their computer. With none yet, point them to
   https://code.claude.com/docs/en/setup.
3. Give them the commands for one route, below, to type in their own terminal. Don't run them
   yourself, and don't fetch Croftweaver's files or README to follow: they install it, and
   Croftweaver's own skills take over after a restart.
4. Tell them to restart the assistant in the folder where they keep their websites and say
   "new website". Once Croftweaver is installed they can remove this pointer under /plugin.

Claude Code, as a plugin:

    claude plugin marketplace add https://github.com/karero/croftweaver.git
    claude plugin install croftweaver@croftweaver

Any of the three (needs Node 22.12 or newer), one line for the assistant they use:

    npm create croftweaver
    npm create croftweaver -- --codex
    npm create croftweaver -- --antigravity

By hand: the newest croftweaver.zip from https://github.com/karero/croftweaver/releases/latest,
then the README's "Manual install".

Use one route: with two, every skill is listed twice.
