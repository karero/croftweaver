# Plan: check a diff's base, and lift the 117 KB limit

One-page plan for two changes to `skills/independent-review/scripts/independent_review.sh`, its
tests and its docs. Written against origin/main `6681e7be`, branch
`plan/review-input-base-and-size`. Both changes touch the script's input path, so they share one
plan and land one after the other.

## Status

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written | this file |
| 2 | PLAN gate (Normal: review tooling is never Light) | ⏸ | — |
| 3 | The maintainer's go, and the answers under "Open" | ⏸ | — |
| 4 | Change 1 (base check) built, `make check` green, DIFF gate, PR | ⏸ | — |
| 5 | Change 2, step 0: the probes below | ⏸ | — |
| 6 | Change 2 built on top of change 1, `make check` green, DIFF gate, PR | ⏸ | — |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked

## What and why

On 2026-10-21 two things went wrong with the script's input.

1. A diff made against a stale base was reviewed without a word: it held other people's
   commits, and the reviewers spent a whole round on them. The script never compares a diff with
   git: the type comes from the flag or the file's extension
   (`case "$FILE" in -|*.diff|*.patch) TYPE="diff"`), and nothing more.
2. A diff over 117 KB is refused (`CONTENT_BYTES -gt 120000`, exit 2), because the whole prompt
   rides in one argv argument and Linux caps one at 128 KB. A change that moves many tests then
   has to be cut down by hand. Two of the seats never needed the cap: Melious and ollama's API
   transport already send a file body (`curl --data-binary @"$body"`).

## Change 1: refuse a diff on the wrong base

**Which base.** A new option, `--base <rev>|none`, for diff runs only (on a plan it is refused,
exit 2: a flag that does nothing must not pass silently).

- No `--base`, no `--verify` (round 1, a final full read): the script runs
  `git fetch --quiet origin <default>`, where `<default>` comes from `origin/HEAD`, and takes
  `git merge-base origin/<default> HEAD`. Fresh, because a branch the server updated with the
  base (the host's "update branch" button), then pulled by name (`git pull origin <branch>`
  fetches that branch alone), holds base commits the local `origin/<default>` has not seen, and a
  stale ref would let them through. A failed fetch, or an unset `origin/HEAD`, refuses the run and
  prints the `--base` command that would go on with the local ref. `--local-only` never fetches:
  it uses the local ref, and says so.
- `--verify` on a diff needs `--base <last-reviewed-head>`, or it is refused. A verification round
  sends a delta (`git diff <last-reviewed-head>..HEAD`) or a merge link (`merge_link.sh`, which also
  diffs from the last reviewed head). A default of the merge base would refuse every one of them.
- `--base none` skips the check, for a diff that did not come from `git diff` in this repo (a
  hand-made patch, `--no-index`, another project's patch). The closing lines then say
  `base: not checked (--base none)`, so nobody reads it as checked.

Considered and dropped: a mode where the script builds the diff itself from a range. It adds a
second input path, and a file still needs this check for deltas.

**How it tells.** After the artifact is read and the type is known, before any size rule, before
any reviewer starts, and before anything leaves the machine:

1. The current directory must be inside a git work tree, or the run is refused: the diff's paths
   mean nothing elsewhere, and Codex reads the same directory to check the diff's claims.
2. A small Perl reader (`perl/diff_sides.pl`, beside the script's other Perl programs) splits the
   diff into one record per `diff --git` header: old path, new path, old id, new id. Names come
   from `---`/`+++`, `rename from/to` or `copy from/to`, and else from the `diff --git` line when
   both names are equal. A C-quoted name is unquoted; the tab git adds after a name with a space
   (seen: `--- a/sp ace.txt<TAB>`) is dropped.
3. One `git --literal-pathspecs ls-tree -z` per side looks up every path: the base for the old
   side, `HEAD` for the new. The old id must be a prefix of the base's id, and the new id a prefix
   of `HEAD`'s or of the working tree's (`git hash-object --path=<p>`, for a diff of uncommitted
   work). All zeros means the file must be absent on that side. An id shorter than 4 hex digits,
   git's shortest, is a malformed record.
4. A record with no `index` line (a rename at 100% similarity, a mode-only change) must have the
   same id at the base's old path and at the new path in `HEAD` or the working tree.

| Input | Result |
|---|---|
| Diff made from the right base, new side at `HEAD` or the working tree | runs |
| Diff from a stale base, or two-dot from a moved base | refused, every file whose old side differs listed |
| `HEAD` moved after the diff was made | refused, the files whose new side differs listed |
| Binary file, new file, deleted file, submodule | checked by its `index` line like any file |
| Rename or mode change with no `index` line | checked by rule 4 |
| `format-patch` file with one patch | checked like a diff, against the base the run names |
| `format-patch` series (more than one `From <40 hex>` header) | refused: a later patch's old side is an earlier patch's new side, not the base; use `git diff <base>..HEAD` |
| Combined diff (`diff --cc`) | refused: it has no single old side |
| No `diff --git` record at all (hand-made, `diff -u`) | refused, naming `--base none` |
| `--no-index` diff | its paths and ids do not match the repo: refused, naming `--base none` |
| stdin | the same check: the script reads stdin into the artifact before checking |
| Current directory not the diff's repo | refused (rule 1) or every file listed (rule 3) |

A refusal exits 2. It names the base it used (the revision as given, its full id, and how it was
chosen), lists every file that does not match and which side failed ("old side 8352675, the base
has 1592e5c" or "no such file at the base"), and prints the command that makes a correct diff for
that base: `git diff <base-id>..HEAD -- . ':(exclude)docs/reviews/'`. The list is never cut short.

**What the trail records.** Every diff run ends with a `base:` line beside `reviewers:` and
`timings:`, on stdout and stderr: `base: <full id> (merge base with origin/main, fetched)`,
`base: <full id> (--base <as given>)`, or `base: not checked (--base none)`. SKILL.md step 8
already has the host report the `timings:` line each round; this change adds the `base:` line
there and to the trail entry in `references/closeout.md`, so every round's record says its base.

## Change 2: the 117 KB limit

**Today (checked in the script).** Codex gets the prompt as its last argv argument, the ollama CLI
transport as `ollama run MODEL "$PROMPT_TEXTONLY"`, agy as `-p "$PROMPT_AGY"`. Melious and ollama's
API transport write the request to a file.

**The change.** Every seat that can take the prompt off argv does, and the script-wide 120,000-byte
check goes. Each seat then has its own limit, and a seat over it fails loud in its own `FAILED`
section while the others run. A seat never reviews part of the artifact.

| Seat | Prompt travels by | Its limit | Source | Over the limit |
|---|---|---|---|---|
| Codex | stdin: `codex exec … -` reading the prompt file | the configured model's window, less the room it needs to read files and reply: 500,000 tokens, 95% usable, for the model configured here | Codex's own model cache (read 2026-10-21) | the CLI's or API's refusal, named (not checked) |
| Melious | file body (no change) | 1,000,000 tokens | a third-party listing; Melious's `/v1/models` gives none (checked) | the API's refusal, named (not checked) |
| ollama, API | file body (no change) | 1,048,576 tokens | `ollama show` on ollama 0.40.7, GLM 5.3 on ollama cloud | not checked |
| ollama, CLI | stdin, if probe P1 passes; else argv | argv: 128,000 bytes of prompt | the Linux argument limit the script cites today | argv: refused before sending |
| agy (opt-in) | argv (no change) | 128,000 bytes of prompt | the same | refused before sending |

Codex's help (codex-cli 0.163.0), quoted: "If not provided as an argument (or if `-` is used),
instructions are read from stdin." The prompt file goes in the run's private raw folder (mode 700),
which already holds the request bodies, so nothing new is exposed. agy keeps argv: whether its
`-p` reads stdin is unknown, and finding out spends an Antigravity credit.

A refusal for length is named apart from other failures, the way a quota refusal is today: a
`CONTEXT_RE` beside `QUOTA_RE`, reading only the error lines the quota check reads, so an echoed
artifact that talks about context windows does not trip it (the tests already pin an echoed
artifact that mentions a 429). The summary reads, for example,
`melious FAILED (input over the model's limit: …)`, with the remedy "split it, or keep the round
with the seats that took it whole".

**Step 0 probes**, before building change 2:

- **P1, free.** Does the ollama 0.40.7 CLI send a piped stdin, whole, as the prompt? Its help shows
  stdin only with `--ask`. Checked against a stub server on 127.0.0.1 (`OLLAMA_HOST`) that records
  the request: no model runs.
- **P2, the maintainer's call.** One prompt past each cited window, to Codex, Melious and ollama
  cloud: does each refuse, or cut silently? A refusal costs nothing; a silent cut costs one window
  of input tokens. A seat that cuts silently gets a limit checked before sending: its window less
  its reply room, counted at one byte per token (a byte-level tokenizer never makes a token of less
  than one byte; not checked for every tokenizer). Without P2 the table's "not checked" stays,
  and the risk is named in the script's comments.

**The split the maintainer suggested**: give Codex the diff as a file to read from the checkout, and
GLM only the app code. Weighed:

- For: no prompt size for Codex at all, and fewer tokens to GLM.
- Against: a tool-using reviewer handed a path reads what it chooses, and nothing would show
  whether it read every hunk; today the whole artifact is in its context. A GLM that never sees the
  tests cannot check them, and tests are where intent lives. Telling app code from tests is a
  per-repo guess about paths.
- **Recommendation: not now.** With the cap gone, a 200 KB diff is roughly 50,000 to 70,000 tokens
  (at 3 to 4 bytes a token, usual for code; not measured here), well under every cited window, so
  every seat takes it whole. Revisit only if a real artifact exceeds a seat's window. If a split is
  ever built, each seat's section and the `reviewers:` line must say what that seat saw, so a
  two-seat round is never read as two seats over the whole change.
- **Strongest case against this recommendation.** A model can read a very long prompt less
  carefully than a short one, and round 1 sends the whole change to every seat. Two focused halves
  might find more than one long whole. That is not measured either way.

## Order, and how the two checks meet

Change 1 lands first, in its own PR: it is the one that cost a wrong round. Its check goes just
before today's size check, so from the start a big stale diff is refused for its base, not its
size: cutting a wrong diff down is the wrong remedy. Change 2 follows in a second PR built on it:
it removes the script-wide size check and adds the per-seat limits, still after the base check.
A big delta round passes the base check with `--base`, then meets each seat's limit on its own.
`--base none` skips only the base check, never a size limit.

## Tests

All in `test_failed_tier_report.sh` (or a new `test_base_check.sh`, listed in the Makefile), and
all through the script itself, as a caller runs it, with stub CLIs on `PATH`. The base cases build
a throwaway repo with a bare `origin`, so the fetch is real and local.

| # | Case | Pass when |
|---|---|---|
| T1 | Stale base: origin moved on by commits touching other files; the diff made against the old local default branch | exit 2; stderr lists exactly those files and the correct `git diff` command; no stub seat ran |
| T2 | Delta round: `git diff A..HEAD` with `--verify prior.md --base A` | runs; `base:` names A's full id. The same delta without `--base`: refused, naming `--base` |
| T3 | Base checked before size: a 300 KB stale diff | refused for its base, not its size |
| T4 | Edge records: rename, mode change, binary, new, deleted, quoted path with a space, working-tree diff, one-patch `format-patch` | each runs |
| T5 | Refusals: hand-made diff, series, `diff --cc`, cwd outside a repo, fetch failure, `--base` on a plan | exit 2, each with its message; `--base none` runs and prints `base: not checked` |
| T6 | stdin to Codex: the stub asserts its last argument is `-`, that no argument holds `--- BEGIN`, and that stdin carries the artifact | passes, with a 200 KB artifact arriving whole (same byte count and hash) |
| T7 | A 200 KB diff reaches every seat that takes it: Codex, Melious, ollama API (and the CLI if P1 passed) | each stub records the artifact whole; `reviewers:` reads OK for each |
| T8 | Over a seat's limit: agy with a 200 KB artifact; a Melious stub answering HTTP 400 "maximum context length is N tokens" | agy `FAILED` before sending; Melious `FAILED (input over the model's limit …)`; the other seats ran, the round reports fewer than 2 as today |
| T9 | Change 2 only: an artifact over 117 KB no longer exits 2 | runs |

The existing cases send a hand-made `change.diff` from outside a repo, so they pass `--base none`.
`make check` must be green before each DIFF gate.

## Docs touched

The script's header (usage, `--base`, the closing lines); SKILL.md step 2 (the round-1 command,
the `base:` line, and "Over 117 KB: split it" replaced by the per-seat rule) and step 6 (`--verify`
needs `--base`); `references/closeout.md` where the trail copies the closing lines.

## Checked here, and not

Checked on 2026-10-21: the script's code paths quoted above; Codex's help (codex-cli 0.163.0);
Codex's model cache (500,000 tokens, 95% usable); `ollama show` (1,048,576 tokens); Melious's
model list (no context field); `getconf ARG_MAX` on macOS (1,048,576); on git 2.33, that a binary
file has an `index` line, a pure rename and a mode-only change have none, a working-tree diff's new
id equals `git hash-object --path`, and `ls-tree` takes literal paths.

Not checked: the Linux argument limit (cited by the script today, not re-run); whether the ollama
CLI reads stdin as the prompt (P1); whether agy's `-p` reads stdin; how each provider answers a
prompt past its window (P2); Melious's own window (third-party figure only).

Outside this plan: under `--local-only`, a local model with a small context may cut the prompt
silently today, whatever its size. A BUGLOG row, not this change.

## Open for the maintainer

1. P2: spend up to one window of input tokens per seat, if a seat cuts silently, to learn each
   seat's real behaviour? Without it the seats keep a named, unchecked risk.
2. The split: build it, or leave it as recommended above?
