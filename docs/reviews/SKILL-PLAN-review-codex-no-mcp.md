# Plan: Codex review runs start no MCP servers (independent-review)

Status: plan only; nothing built. Building waits for the owner's go.
Evidence: `evidence-codex-no-mcp/measurements.md` (same folder).

## What

`independent_review.sh` runs the Codex seat as `codex exec -s read-only …`. Each run also starts
every enabled MCP server in the User's Codex config and plugins, though a review uses none. After
this change the Codex seat turns off, for that run only, every server it can name; one it cannot
name stays on and is named on stderr. The User's `~/.codex/config.toml` and their interactive
Codex stay as they are.

## Why

- **Cost per run** (one run each, measured under heavy load, so rough): as today, 3 helper
  processes (`node_repl` ×2 and `npx chrome-devtools-mcp@latest`; npx's network traffic was not
  measured), peak tree RSS 294 MB, 4.17 s CPU. With the servers off: no helpers, 166 MB, 1.35 s
  CPU. So about 130 MB and 2.8 s CPU per run, times the reviews running at once.
- **Less beside a reviewer of untrusted text.** The reviewed diff or plan sits in the prompt. One
  server drives a browser, another runs JavaScript, and Codex's own help says MCP commands run
  "outside the sandbox". Whether a read-only review run could call one without asking was not
  checked; with them off the question does not arise.
- **Not a fix for the load.** At load 400–860, 130 MB and 3 s per run is a small share. The
  saving is modest; the narrower surface is the stronger reason. If the owner weighs the build's
  review cost (below) above both, drop it.

## How

1. In `run_codex`, before `exec`: run `codex mcp list --json --disable plugins` in the same
   folder `exec` will run in, stdin from `/dev/null`, bounded by `perl/run_limited.pl` (20 s).
   A new `perl/codex_mcp_off.pl` (JSON::PP, as the ollama tier uses) reads it and prints one
   `mcp_servers.<name>.enabled=false` for each entry whose `enabled` field is true.
2. The run then gets `--disable plugins` (this drops the servers plugins bring, which cannot be
   named in `-c`) and one `-c` per printed line, placed right after
   `-c skills.include_instructions=false` and before the model and effort overrides, appended to
   the positional parameters as the rest of the argv is. Names come from the list, never from a
   fixed set: naming a server that is not configured stops Codex ("invalid transport"), so a
   fixed list would break the seat on any machine without one of them.
3. A name that is not a TOML bare key (`A-Za-z0-9_-`) is not passed (a dotted one also stops
   Codex, checked in round 1); stderr names it and says it stays on. The rest still go off.
4. If the list fails (exit, timeout, bad JSON; for example an older codex answering
   "Unknown feature flag: plugins"), or perl or JSON::PP is missing, the run goes exactly as today,
   and stderr says the servers were left on and why. A review never fails over this.
5. The comment block above `run_codex` gets two lines on the new switches and why, and so do the
   two docs that list the Codex flags today: `references/setup-guide.md` and
   `references/rationale.md`. Past trails in `docs/reviews/` stay as they are.

Not adopted:
- `--ignore-user-config`: it also drops the config's model and effort defaults (measured: effort
  went from `medium` to `none`).
- A second `codex mcp list` to confirm all are off: it reads the same config view as step 1, so
  it cannot show what `exec` starts. The live check below does that once; a later codex that
  changes these switches would show only as helpers coming back, which costs memory, not a wrong
  review.
- Codex's shell snapshot (`zsh -lc`), `codex-code-mode-host` and the config's `notify` program are
  not MCP servers and stay as they are.

Not covered: a server defined in a project's own `.codex/config.toml`. Step 1 runs in the same
folder as `exec`, so it should list one, but no run tested that.

## How it is tested

- **T1, through the real entry point:** a new `test_codex_mcp_off.sh` runs `independent_review.sh
  --seat codex` with a stub `codex` on `PATH` and a stub `HOME`, as `test_failed_tier_report.sh`
  does. The stub's first line handles `mcp list` (answers from a committed capture, records the
  call) and exits before any of its `exec` marks or checks. Cases: (a) two enabled servers, one
  disabled: the exact `exec` argv, with `--disable plugins` and exactly two `-c` in the place
  step 2 names, none for the disabled one; (b) the list exits 1 with the captured
  unknown-feature text: argv exactly as today, stderr says why; (c) a name with a dot: named on
  stderr, the other still off; (d) the list sleeps past the bound: argv as today, stderr says it
  timed out; (e) `[]`: `--disable plugins`, no `-c`, no warning. Each case also checks the
  review section still counts.
- **Real capture (rule 5):** the fixture is a trimmed `codex mcp list --json` from codex-cli
  0.169.0, entries cut, home paths and env values replaced with made-up ones, in `fixtures/` named
  like the others (`codex-cli-0.169.0_<date>_mcp-list.json`). Expected values in T1 are written
  by hand.
- **Existing stubs:** `test_failed_tier_report.sh`, `test_base_check.sh` and
  `test_round_checks.sh` stub `codex`. Each stub gets the same first-line `mcp list` branch,
  answering `[]`. The exact argv the first pins (its no-git case, `want=`, and §26's `base=`) gains
  `[--disable][plugins]` after `skills.include_instructions=false`.
- **Wiring:** T1 joins the `check` target in `Makefile`, the `review-reporting` job in
  `.github/workflows/clean.yml`, the lists in `scripts/check_cdpath_safe.sh`,
  `scripts/test_mktemp_guard.sh` and `scripts/package.sh`. `codex_mcp_off.pl` joins `GATED` in
  `check_perl_minimum.sh` (it needs JSON::PP) and the list in `scripts/package.sh`.
- **Mutations:** with `mutation-check`, revert each of steps 2–4 in turn (no `--disable plugins`;
  no `-c`; no name filter; no fallback); a T1 case must fail for each.
- **Live check, before merge:** one real `--seat codex` review with the process tree sampled
  every 0.5 s (the sampler behind the evidence file): no `node_repl`, `npx` or
  `chrome-devtools-mcp` child, and the review section counts. Quoted in the PR. A server that
  lives less than half a second between samples would escape it.
- `make check` before each review round and after the last edit.

## Review and record

- PLAN gate: Codex + GLM 5.3 on melious, Normal (every plan; not High, since it only removes
  tools from a read-only run). Plan gates since 2026-11-03 logged a median of 536k tokens (p75
  965k). The DIFF gate later is Normal, Codex alone.
- No red team: the change touches none of the risky list (the box, user data, logins or
  permissions, money, deletion, a schema); it only takes tools away from a read-only run.
- When built: an entry at the top of § Changelog in the maintainer's `~/.claude/HARNESS-CHANGES.md`
  (`harness:` prefix, about 15 lines, linking this plan and the DIFF trail). `HARNESS.md` §1's
  `codex` wrapper row needs no change: it already passes `--disable` and `-c` through (both are on
  its option lists).
- Rollback: revert the commit. The change keeps no state.
