# Measurements: Codex review runs with and without MCP servers (2026-11-17)

All on the maintainer's Mac, codex-cli 0.169.0, under heavy load (1-minute load average 165 at the
first run, 65 at the last). One run per variant, so the figures are rough. Home and scratch paths
are replaced with `<home>` and `<scratch>`.

## What the Codex config starts

`codex mcp list --json`, names and state only:

```
chrome-devtools enabled     (config: npx chrome-devtools-mcp@latest)
codex_app       disabled    (from a plugin)
computer-use    disabled    (config, enabled = false)
cua_repl        enabled     (from a plugin)
node_repl       enabled     (config)
```

## Which switches turn them off (checked with `codex mcp list --json`, no model call)

| Switch | Result |
|---|---|
| `-c 'mcp_servers={}'` | no change: all five listed as before (the override merges, it does not replace) |
| `--disable plugins` | `cua_repl` and `codex_app` gone; `chrome-devtools` and `node_repl` still enabled |
| `--disable plugins -c mcp_servers.node_repl.enabled=false -c mcp_servers.chrome-devtools.enabled=false` | all three left are `False` |
| `-c mcp_servers.cua_repl.enabled=false` (a plugin's server) | `Error: failed to load bootstrap configuration` / `Caused by: invalid transport` / ``in `mcp_servers.cua_repl` `` |
| `-c mcp_servers.no_such_server.enabled=false` | the same error, naming `mcp_servers.no_such_server` |
| `-c mcp_servers.a.b.enabled=false` (a dotted name) | exit 1, the same `invalid transport` error |
| `--disable no_such_feature` | exit 1, `Error: Unknown feature flag: no_such_feature` |

So a name that is not already a configured server breaks the run. A fixed list of names would
break Codex on any machine that lacks one of them.

## Process tree of one run (sampled every 0.5 s)

Prompt: "Reply with the single word OK. Do not run any commands." Flags: the review script's
(`exec -s read-only --skip-git-repo-check -c project_doc_max_bytes=0 -c skills.include_instructions=false`),
prompt on stdin, run in a scratch folder that is not a git repo.

| Variant | Extra flags | Wall | Peak tree RSS | Helper processes seen |
|---|---|---|---|---|
| A, as today | none | 12 s | 294 MB | `node_repl` ×2 (18.7 + 18.3 MB), `npx chrome-devtools-mcp@latest` (116.7 MB) |
| B, servers off | `--disable plugins -c mcp_servers.node_repl.enabled=false -c mcp_servers.chrome-devtools.enabled=false` | 11 s | 166 MB | none |
| C | `--ignore-user-config` | 7 s | 180 MB | none, but `reasoning effort: none` where A printed `medium`: it drops the config's defaults |

All three answered `OK`. Both A and B also showed a short `zsh -lc` (Codex's shell snapshot); it
is not an MCP server and this plan leaves it alone.

A real review by another session, seen once at 17:32 with `ps` (read only, not touched): `codex`
122 MB, `node_repl` ×2 (11.7 MB each), `npm exec chrome-devtools-mcp@latest` 47 MB and its child
`chrome-devtools-mcp` 49 MB, `codex-code-mode-host` 22 MB. RSS under full swap reads low.

## CPU, one run each under `/usr/bin/time -l`

| Variant | real | user | sys | max RSS (largest single process) |
|---|---|---|---|---|
| A, as today | 23.42 s | 2.34 s | 1.83 s | 172,900,352 |
| B, servers off | 14.09 s | 0.81 s | 0.54 s | 162,168,832 |

`codex mcp list --json --disable plugins` itself, twice: 1.04 s / 0.21 s real, 0.12 s / 0.03 s
CPU, 39 MB max RSS.

## Text that bears on the why

`codex exec --help` (0.169.0), on `--trust`: "Save trust for this project and future chats,
including MCP commands outside the sandbox." Whether a `-s read-only` review run can call an MCP
tool without asking was not checked.
