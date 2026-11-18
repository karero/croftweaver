# Live check before merge — real `--seat codex` runs, child processes sampled

Plan: `../SKILL-PLAN-review-codex-no-mcp.md`. Tool: codex-cli 0.169.0, run on 2026-11-17 from a
checkout of this branch (head 01814861 for the first sample, bf704e27 for the second) with the
maintainer's own Codex config, which names a browser driver (`chrome-devtools`) and a JavaScript
runner (`node_repl`) as enabled MCP servers, and a third, `computer-use`, that is disabled.

How: `independent_review.sh <one-line plan> --plan --seat codex --depth normal` started in the
background; a 15-line Python loop (`ps -axo pid=,ppid=,command=` every 0.5 s, the descendants of
the script's pid, each distinct command counted by samples) ran until the script ended. The same
plan was run twice.

Result, both runs (counts are 0.5 s samples; commands cut to their first 100 characters):

| samples | child command |
|---|---|
| 30 | `bash …/independent_review.sh …` (the script itself) |
| 30 | `/opt/homebrew/bin/codex exec -s read-only --skip-git-repo-check -c project_doc_max_bytes=0 -c skills.include_instructions=false --disable pl…` |
| 17 | `/opt/homebrew/Caskroom/codex/0.169.0/bin/codex-code-mode-host --listen grpc+stdio://` |
| 1 | `…/SkyComputerUseClient … t…` (the config's `notify` program, run when the turn ends; not an MCP server) |
| 1 each | `git`, `awk`, `zsh`, `bash` (the reviewer's own commands) |

Not seen in either run, though both are enabled in that config: `node_repl`, `npx`,
`chrome-devtools-mcp`. Both runs exited 0 and printed a counted review section ("No BUG/RISK/NIT
findings." for the one-line plan).

Not shown: the sampled lists are kept as the author's notes, not committed; this table is their
content. The run is a before-merge check by hand, not a CI test: CI has no Codex login.
