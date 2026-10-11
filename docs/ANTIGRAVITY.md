# Using website-builder with Google Antigravity

The `website-builder` skill suite was originally designed for Claude Code, but its underlying architecture (Markdown files with YAML frontmatter, sibling directories, and template folders) is **100% compatible with Google Antigravity**.

Antigravity natively understands the `SKILL.md` format and can seamlessly orchestrate the pipeline from insights to launch.

> Want to verify it works on your setup? Run through [ANTIGRAVITY-TEST.md](ANTIGRAVITY-TEST.md) — a step-by-step compatibility checklist with a report-back template.

## 1. Installation

Antigravity automatically discovers skills placed in its customization roots. You have two options for installation:

### Option A: Global Install (Recommended)
To make the website-builder suite available to Antigravity no matter what directory you are in:
```bash
# From the root of this website-builder repository:
mkdir -p ~/.gemini/config/skills
cp -R skills/* ~/.gemini/config/skills/
```
*(You can also use `ln -s` if you prefer to keep the skills symlinked to the repo.)*

### Option B: Workspace Install
If you only want these skills active within a specific project folder:
```bash
mkdir -p .agents/skills
cp -R path/to/website-builder/skills/* .agents/skills/
```

## 2. Usage

Once installed, open an Antigravity chat. With a global install (Option A), open it in your websites folder (`Documents/Websites`, or wherever you keep your projects). With a workspace install (Option B), open it in the folder that contains `.agents/skills`. Then simply trigger the orchestrator just as you would with Claude:

> *"I want to build a new website"* or *"new website"*

Antigravity will recognize the `new-website` skill, run the stack-decision interview, scaffold the `templates/astro` overlay, and sequence the rest of the `website-*` skills perfectly.

When the suite is installed through Antigravity (`$SKILLS_ROOT` = `~/.gemini/config/skills`), the scaffold bundles the project's skills into **`.agents/skills/`** (which Antigravity reads as workspace skills), so the generated project is self-contained for Antigravity rather than Claude's `.claude/skills/`. To force it regardless: `export PROJECT_SKILLS_DIR=.agents/skills` before scaffolding.

## 3. Key Differences & "Claude-isms" to Ignore

Because Antigravity and Claude Code handle permissions differently, you will notice a few minor discrepancies that you can safely ignore:

*   **Permissions & Sandboxing:** The `templates/claude/settings.json` file dictates allowed commands for Claude. Antigravity uses a different security model: it runs in a sandbox and asks for your manual approval on **every** shell command it proposes through its `run_command` tool (`mkdir`, `cp`, `npm install`, etc.) — not only ones that need network access. So the `.claude/settings.json` allowlist does nothing here; you can ignore the `.claude` folder entirely, and expect to approve the scaffold's commands as they run.
*   **The `website-permissions` Skill:** This skill is bundled to help Claude safely extend its allowlist. It won't do anything for Antigravity, as Antigravity doesn't use the allowlist model.
*   **Path references:** Wherever a skill shows a path under `~/.claude/skills/...`, read it as your Antigravity skills root (`~/.gemini/config/skills/...`). The scaffold's `new-website` skill resolves this automatically via `$SKILLS_ROOT`.

## 4. Why Antigravity Excels Here

Antigravity is uniquely well-suited for this suite because it supports **Subagents**. During the build pipeline, Antigravity can spin up background subagents to asynchronously run the `customer-research` or `seo-audit` skills while the primary agent continues scaffolding your Astro components!
