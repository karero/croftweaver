# Using Croftweaver with OpenAI Codex

The Croftweaver skill suite is developed and used with Claude Code. The skills are plain
Markdown (`SKILL.md` + templates), so Codex reads the same skills through a small
adaptation layer. **`skills/*` stays the single source of truth** — nothing is duplicated
for Codex. The suite has been tested from start to finish with Codex on one site.

> Want to verify it works on your setup? Run through [CODEX-TEST.md](CODEX-TEST.md) — a step-by-step compatibility checklist with a report-back template.

## Install

**As a Codex plugin** (from release 0.32 on):
```bash
codex plugin marketplace add https://github.com/karero/croftweaver.git
codex plugin add croftweaver@croftweaver
```

Codex keeps the plugin in its own folder (`~/.codex/plugins/cache/croftweaver/`), installs
releases only, and `codex plugin marketplace upgrade` brings you the newest one. The skills
carry the plugin's name in front: `$croftweaver:new-website`. Use this route or the one
below, not both: with both, every skill is listed twice. The same holds in a site built with
the suite, for the skills the site carries in its `.agents/skills/`.

**From a clone:**
```bash
git clone https://github.com/karero/croftweaver.git
cd croftweaver
./scripts/install-codex.sh
```

**From the handoff zip** (after unzipping, from the extracted folder):
```bash
./scripts/install-codex.sh
```

What it does: symlinks `skills/*` into `~/.agents/skills/` (the equivalent of
`make install-codex`). Re-running just refreshes the links — except one you pinned
yourself into another worktree of this repo, which is kept and reported;
`./scripts/install-codex.sh --force` relinks those too. Keep the unzipped or cloned folder
where it is: the links point into it.

## Use

Restart Codex, open it in your websites folder (`Documents/Websites`, or wherever you keep
your projects), and say:

```text
new website
```

or invoke the orchestrator explicitly:

```text
$new-website
```

Codex runs the stack-decision interview, scaffolds the `templates/astro` overlay into a
new folder for the site inside the folder you opened Codex in, and sequences the rest of
the `website-*` skills.

> With a large skill set, Codex itself notes it may not surface every skill automatically
> when context is tight. Not a breakage — invoke any skill by name: `$og-images`, `$seo-audit`, etc.

> **On a machine that also has Claude Code or Antigravity installed,** the scaffold's
> auto-detect prefers them over Codex (order: Claude Code → Antigravity → Codex). Force
> Codex's copy first:
> ```bash
> export SKILLS_ROOT="$HOME/.agents/skills"
> ```

## Differences from Claude Code

- Codex reads user skills from **`~/.agents/skills`**, not `~/.claude/skills`. The
  installer above handles this; the `new-website` scaffold resolves the right source via
  `$SKILLS_ROOT`, so it works regardless of which tool installed the suite.
- Codex can also read **repo-scoped** skills from `.agents/skills` within a project. If you
  install them that way, open Codex in the folder that contains `.agents/skills`.
- `templates/claude/settings.json` is Claude Code-specific (its command-allowlist model).
  For Codex, durable project instructions live in **`AGENTS.md`** — every scaffold ships
  one (`templates/AGENTS.md`: fetch the latest state first, pull request instead of a
  direct push, merge conditions, never invent facts, the new-page checklist; `CLAUDE.md`
  imports it so Claude Code follows the same rules) — and command-approval policy in
  Codex's own rules/config. The bundled `website-permissions` skill is a no-op for Codex.
  `AGENTS.md` also has a dedicated **Codex cloud** path: a browser task starts from a
  fresh clone, fetches nothing, and the person presses "Create PR".
- Project-bundled skills are copied into `.claude/skills/` by default (so a Claude
  recipient is self-contained). The scaffold derives `$PROJECT_SKILLS_DIR` automatically —
  if the suite was installed through Codex or Antigravity (`$SKILLS_ROOT` = `~/.agents/skills`
  or `~/.gemini/config/skills`), generated projects bundle into `.agents/skills/` instead, so
  they're self-contained for that tool. Force it with `export PROJECT_SKILLS_DIR=.agents/skills`
  for a **Codex or Antigravity handoff**.

## Scope

The plugin is a marketplace entry and nothing more: `.agents/plugins/marketplace.json`
points Codex at the branch `stable`, and Codex reads the plugin's name and number from
`.claude-plugin/plugin.json`, the Claude Code plugin's manifest. There are no icons, no MCP
server and no listing in OpenAI's public plugin directory; those would need a submission
to OpenAI.
