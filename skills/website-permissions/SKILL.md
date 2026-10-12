---
name: website-permissions
description: >
  Cut the number of permission prompts on a new-website repo to near-zero for the
  routine build loop, while keeping destructive actions gated. Installs the bundled
  `.claude/settings.json` allowlist into the project, explains the allow/deny model
  (npm / astro / playwright / git commit / gh-read / image tools / the link script
  are pre-approved; `rm -rf`, `git push --force`, `git reset --hard`, and any
  `wrangler/gh … delete` stay prompted), and safely EXTENDS the allowlist from the
  commands you keep approving — narrowly, never with a blanket wildcard. The allowlist
  travels with the repo, so a handoff party also gets the quiet build loop. Trigger
  phrases: "reduce permission prompts", "too many permission prompts", "stop asking me
  to approve", "set up permissions for this site", "fewer prompts", "allowlist this
  repo", "why does it keep asking me".
---

# Website permissions — fewer prompts, same guardrails

A build is a tight loop of `npm`/`astro`/`playwright`/`git` calls. Approving each one
by hand is friction with no safety benefit — those commands can't hurt you. This skill
gets the repo to "quiet for the safe stuff, still asks for the dangerous stuff", and
keeps it that way as the project grows.

## 1. Install the bundled allowlist (the 90% fix)

The `new-website` kit ships a curated `.claude/settings.json`. Copy it into the repo
(this is also scaffold step 3.2 — do it here if it was skipped). The two files are in the
`new-website` skill's `templates/claude/` folder, and that skill sits beside this one
wherever the whole suite is installed. The copy of this skill inside a site has no such
neighbour, so the lines below look there first and then in the installed suite. In the
first line Claude Code puts this skill's own folder where the name in braces stands; left
as written it names no folder, and the second line takes over.

```bash
src='${CLAUDE_SKILL_DIR}/../new-website/templates/claude'
[ -d "$src" ] || src="${SKILLS_ROOT:-$HOME/.claude/skills}/new-website/templates/claude"
mkdir -p .claude/hooks
cp "$src/settings.json" .claude/settings.json
cp "$src/hooks/git-stand.mjs" .claude/hooks/
```

If both `cp` lines fail, the suite is not installed on this computer where these lines
look (as a plugin, or for another assistant, it is elsewhere): set `SKILLS_ROOT` to its
`skills` folder and run them again.

The settings also register a sync hook (`.claude/hooks/git-stand.mjs`, `AGENTS.md` §1):
copy the script with them, or every session start reports a missing file. A repo whose
`.claude/settings.json` already has its own rules: merge the template's `hooks` block in
instead of overwriting the file.

`.claude/settings.json` is **per-project** and committed, so it travels with the repo
— the handoff party inherits the same quiet loop. Restart Claude Code (or reload the
project) after editing so the new rules take effect.

## 2. The model — what's pre-approved vs always gated

**Pre-approved (`allow`)** — the build loop and read-only inspection:
`npm install/ci/run/test/exec`, `astro`, `playwright`, `node`, the **git write subset**
(`add`, `commit`, `branch`, `checkout`, `switch`, `merge`, `restore`, `stash`,
`fetch`, `pull`, `push`), `gh` **read** verbs (`auth status`, `repo view`,
`pr view/list`), `wrangler pages dev` / `whoami`, the image tools (`cwebp`, `avifenc`,
`magick`, `oxipng`, `svgo`, `exiftool`, …), file inspection (`ls`/`cat`/`grep`/`rg`/
`find` …), and `bash scripts/check_external_links.sh` (the outgoing-link sweep).

**Always gated (`deny`)** — irreversible or destructive, must stay prompted:
`rm -rf`, `git push --force` / `-f`, `git reset --hard`, `gh repo delete`,
`wrangler pages delete`, `wrangler delete`. **Do not move these to `allow`.**

## 3. Extend it safely when a new prompt recurs

When you keep approving the *same* command, add it — but narrowly:

- **Scope every rule** to the binary + a `:*` arg glob, e.g. `Bash(turnstile:*)`,
  not `Bash(*)` and never a bare `Bash`. A blanket grant defeats the point and the
  harness's auto-approve classifier will reject broad widening anyway.
- **Let the built-in do the scan.** `/fewer-permission-prompts` reads your recent
  transcripts and proposes a prioritized allowlist from what you actually approved —
  run it, then keep only the rules that fit the rules above. Use `/update-config` (or
  hand-edit `.claude/settings.json`) to apply changes.
- **Never add `Bash(curl:*)` or other broad network/exec wildcards** to the project
  allowlist. The link sweep already runs `curl` *inside* its allowed script, so no
  separate `curl` grant is needed.
- **Keep secrets out of settings.** Tokens/keys belong in env or a gitignored file,
  never in `.claude/settings.json` (it's committed).

## 4. Where rules live (precedence)

- `.claude/settings.json` — project, committed, travels with the repo (use this).
- `.claude/settings.local.json` — project, gitignored, for personal-only rules.
- `~/.claude/settings.json` — your global default across every project.

Project rules layer on top of global. Put repo-specific build grants in the project
file so the handoff party gets them; keep machine-specific paths in the `.local` file.

## Scope note

This skill manages the *permission allowlist*, not what the commands do. For automated
behaviours (run X after Y) you need hooks via `/update-config`, not an allowlist entry.
