# Plan: check a diff's base, and lift the 117 KB limit

One-page plan for two changes to `skills/independent-review/scripts/independent_review.sh`, its
tests and its docs. Written against origin/main `6681e7be`, branch
`plan/review-input-base-and-size`. Both changes touch the script's input path, so they share one
plan and land one after the other.

## Status

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ revised through round 5 | this file |
| 2 | PLAN gate (Normal: a plan for a guard script's logic) | ▶ rounds 1 to 5, final full read and wording pass done; R4-02 waits on the maintainer | trail `REVIEW-plan-2026-10-21-plan-review-input-base-and-size-ad095f0.md` |
| 3 | The maintainer's go, and the answers under "Open" | ⏸ | — |
| 4 | Change 1 (base check) built, `make check` green, DIFF gate, PR | ⏸ | — |
| 5 | Change 2, step 0: probes P1 and P2 below | ⏸ | — |
| 6 | Change 2 built on top of change 1, `make check` green, DIFF gate, PR | ⏸ | — |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked

## What and why

On 2026-10-21 two things went wrong with the script's input.

1. A diff made against a stale base was reviewed without a word: it held other people's
   commits, and the reviewers spent a whole round on them. The script never compares a diff with
   git: the type comes from the flag or the file's extension
   (`case "$FILE" in -|*.diff|*.patch) TYPE="diff"`), and nothing more.
2. An artifact over 117 KB is refused: `CONTENT_BYTES`, the artifact plus any prior findings, must
   be at most 120,000 bytes, or exit 2. The whole prompt, those plus a few KB of instructions,
   rides in one argv argument, and Linux caps one at 128 KB. A change that moves many tests then
   has to be cut down by hand. Two of the seats never needed the cap: Melious and ollama's API
   transport already send a file body (`curl --data-binary @"$body"`).

## Change 1: refuse a diff on the wrong base

**Which base.** A new option, `--base <rev>|none`, for diff runs only. On a plan it is refused,
exit 2: a flag that does nothing must not pass silently. A value starting with `-` is refused, as
`--cut` does today, and a revision must resolve with
`git rev-parse --verify --quiet "<rev>^{commit}"`, as `merge_link.sh` does.

- **No `--base`**: the run reviews the whole change. The base is the merge base of `HEAD` with the
  tip of origin's default branch, fetched fresh with `git fetch --quiet origin HEAD`. That fetch
  needs no `origin/HEAD` and leaves the tip in `FETCH_HEAD`, a file each worktree has to itself
  (checked on git 2.33: `FETCH_HEAD` held the remote's new tip while `origin/<default>` stayed
  where it was). Fresh, because a branch the server updated with the base, then pulled by name,
  holds base commits a stale local ref has not seen. The fetch is bounded the way the site
  template's `git-stand.mjs` bounds its own: `GIT_TERMINAL_PROMPT=0`; ssh `BatchMode=yes` and
  `ConnectTimeout=10` unless the person set their own ssh command; `http.lowSpeedLimit=1000` and
  `lowSpeedTime=20`; and a 30-second limit (a Perl `alarm`, since macOS has no `timeout`). A
  fetch that fails or runs out of time refuses the run, printing the `--base` command that would
  go on with the local `origin/HEAD` where one is set. `--local-only` never fetches: it uses
  `origin/HEAD`, or refuses and names `--base`.
- **`--base <rev>`**: every diff that is not the whole change. A verification round (`--verify`
  on a diff needs it, or is refused), a merge link (`merge_link.sh` diffs from the last reviewed
  head), the wording pass and its confirmation, a closeout re-gate. Outside `--verify` that is the
  caller's duty, written in SKILL.md, not something the check can always see: a delta whose files
  did not change between the merge base and the reviewed head has the same headers either way and
  runs. Rule 5 then names on the `base:` line every changed file it leaves out, so the trail shows
  it was not the whole change.
- **The merge base is `HEAD`** (a diff made on the default branch itself): git's committed patch
  is empty, so rule 2 compares with the working tree. If that holds no change either, there is
  nothing to review: refused, naming `--base`.
- **`--base none`** skips the whole check, rules 1 to 5 below included, for a diff that did not
  come from `git diff` in this repo (a hand-made patch, `--no-index`, another project's patch). It
  runs anywhere, outside a repo too. The closing lines say `base: not checked (--base none)`.

**How it tells.** After the artifact is read and the type is known, and before any size limit,
any reviewer, or any of the artifact leaving the machine (the fetch above goes first):

1. The current directory must be inside a git work tree. Every git command below runs from the
   top of it (`git -C "$(git rev-parse --show-toplevel)"`), so paths are read from the repo root
   whatever directory the run starts in.
2. Git makes its own patch of the same base:
   `git diff --no-ext-diff --no-color --full-index --no-renames --src-prefix=a/ --dst-prefix=b/ <base> HEAD`,
   and only if some file's new side does not match `HEAD`, the same against the working tree
   (`<base>` alone). No path goes on argv, so a large diff cannot reach the argument limit, and
   git, not this script, hashes the working tree (filters, symlinks and submodules as the diff's
   own `index` line did).
3. One small reader, `perl/diff_headers.pl`, reads both the artifact and git's patch the same way:
   per `diff --git` record, old and new path, mode and id. Names come only from header lines,
   between `diff --git` and the record's first `@@` or `Binary files` line: `---` and `+++`,
   `rename from` and `rename to`, `copy from` and `copy to` (read only to refuse it). Each hunk
   is skipped by its line counts, so a removed line `-- x` (shown `--- x`) is never read as a
   header. A `\ No newline at end of file` line is not in those counts: any line starting with
   `\` is passed over without counting, inside a hunk or right after it. A C-quoted name is
   unquoted first, and the tab git adds after a name with a space is dropped. Prefixes: only
   git's default ones are accepted, `a/` on the old side and `b/` on the new. They appear only
   on the `diff --git`, `---` and `+++` lines, and are stripped there, once, after unquoting,
   and nowhere else: `rename from`/`to` and `copy from`/`to` carry no prefix, so their names are
   taken as written, and `/dev/null` (a new or deleted file) means "no file on
   this side". Any other prefix, git's mnemonic ones (`c/`, `i/`, `o/`, `w/`) included, or none,
   is refused with the remedy below, which sets `a/` and `b/` explicitly. It splits a `diff --git`
   line with no other name source where both halves name the same path, as `git apply` does. It
   uses Perl 5.8 syntax only, so `check_perl_minimum.sh` lists it as ungated; a missing `perl` or
   `git` refuses the run, except under `--base none`, which runs none of this.
4. Every mode and id the artifact states must match git's for that path and side: the old side
   against git's old side of the old path, the new side against git's new side of the new path.
   Ids compare as prefixes, at least 4 hex digits, git's shortest. A record with no `index` line
   is matched against git's own records, which carry no ids for it either (checked: git's patch
   has no `index` line for a mode-only change, even with `--full-index`): a mode-only change must
   be a mode-only record in git's patch with the same modes; a rename at 100% must appear there,
   with renames off, as a deletion of the old path and an addition of the new one with the same
   id. A path git's patch does not change cannot be claimed changed.
5. With no `--base` only: every file git's patch changes outside `docs/reviews/` that the artifact
   leaves out is named on the `base:` line. A note, not a refusal: a caller may leave a path out
   on purpose, and the reader of the trail can then see it.

| Input | Result |
|---|---|
| `git diff <merge base>..HEAD`, or `<merge base>` alone for uncommitted work | runs |
| A diff from a stale base, or a two-dot diff from a moved base | refused, every file whose old side differs listed |
| `HEAD` moved after the diff was made | refused, every file whose new side differs listed |
| Origin moved on, the branch did not take it, a three-dot diff | runs: the merge base did not move |
| Binary, new, deleted, symlink, submodule | checked by its `index` line |
| Rename or mode change with no `index` line | checked by rule 4 |
| A stale mode change (both trees already hold the new mode) | refused |
| `format-patch`, one patch or a series | one patch: checked like a diff; a series: refused, since a later patch's old side is an earlier one's new side |
| `diff --cc`, a copy record (`git diff -C`), prefixes other than `a/` and `b/` (mnemonic ones included), colour codes | refused, naming the command below |
| No `diff --git` record at all (hand-made, `diff -u`) | refused, naming `--base none` |
| `git diff --no-index` (git's format, paths from outside the repo's history) | checked like any diff: refused by rule 4 where its sides do not match, with `--base none` named |
| A diff with a side taken from the index | judged by its sides, not its command: `git diff --cached <base>` with the index at `HEAD` is the same patch and runs; plain `git diff` (index to working tree) is refused wherever the index differs from the base |
| stdin | the same check: the script reads stdin into the artifact first |
| Run from a subdirectory of the repo | the same result as from the top (rule 1) |
| Not in a work tree | refused, naming `--base none` |
| No merge base (a shallow clone, unrelated histories) | refused, naming `git fetch --unshallow` and `--base` |

A refusal exits 2. It names the base (the revision as given, its full id, how it was chosen),
lists every file that does not match and which side failed ("old side 8352675, the base has
1592e5c", "no such file at the base"), never cut short, and prints the command that makes a
correct diff in the form the artifact used:
`git -C <top> diff --no-ext-diff --no-color --src-prefix=a/ --dst-prefix=b/ <base-id> HEAD -- . ':(exclude)docs/reviews/'` for
committed work, or `<base-id>` alone where its new sides matched the working tree. It leaves out
rule 2's `--full-index --no-renames` on purpose: the diff is for reviewers, who read renames more
easily, and rule 4 accepts both short ids and rename records. With it goes the line
"for a delta since a reviewed head, pass --base <that head>".

**What the trail records.** Every diff run ends with a `base:` line beside `reviewers:` and
`timings:`, on stdout and stderr: `base: <id> (merge base with origin's HEAD <id>, fetched;
every changed tracked file present)` or `(…; not in this diff: <files>)`; untracked files
appear in neither git's patch nor a diff made with `git diff <base>`; under `--local-only`,
`(merge base with origin/HEAD <id>, not fetched: --local-only; …)`; `base: <id> (--base <as
given>)`; or `base: not checked (--base none)`. The trail template in `references/closeout.md`
already has a `Base` field and an "Artifact (full / delta since <sha>)" column: the `base:` line
fills both, and SKILL.md step 8 reports it with `timings:`.

**Considered and dropped:** the script building the diff itself from a revision range. That would
make round 1 stale-proof by construction and replace the header reader (about 150 lines of Perl
and the cases in the table, an estimate). It is dropped because files stay either way: merge
links, other skills' documented `--diff` commands (`website-review`, `seo-reposition`) and site
repos that vendor this skill send files, and the ask is that those files be checked. Built later,
it would sit beside the check, not replace it.

## Change 2: the 117 KB limit

**Today (checked in the script).** Codex gets the prompt as its last argv argument, the ollama CLI
transport as `ollama run MODEL "$PROMPT_TEXTONLY"`, agy as `-p "$PROMPT_AGY"`. Melious and ollama's
API transport write the request to a file, and ollama's sends no `num_ctx`, so a request is served
with whatever window the server defaults to.

**The change.** Every seat that can take the prompt off argv does, and the script-wide check moves
into each seat. What a seat may be sent depends on what probe P2 found its model does with a prompt
past its window, recorded per seat and model in a list beside the script (`seat_limits.txt`, read
like `melious_models.txt`):

- **Refuses**: the provider answered the probe with an error that names a context or token limit
  (its text and the date go in the list). No cap: a prompt past the window fails loud by itself,
  with the provider's message in the seat's `FAILED` section, as any failure does today.
- **Anything else**: a reply (the provider cut the prompt or took it whole), any other error (quota,
  sign-in, network, request size), or no probe at all, as for a model P2 did not cover such as a
  new `CODEX_MODEL`. Today's check: artifact plus prior findings at most 120,000 bytes.

The list is read like `melious_models.txt`: a missing list, or a line the script cannot read,
leaves every seat at 120,000.

Seats on argv (agy, and the ollama CLI if P1 fails) keep today's 120,000-byte check. A seat over its
cap is `FAILED` before anything is sent, and the other seats run. A round with fewer than two seats
is degraded, as today.

| Seat | Prompt travels by | Until P2 | After P2 |
|---|---|---|---|
| Codex | stdin: `codex exec … -`, reading the prompt file | 120,000 bytes | no cap if P1 shows its stdin arrives whole and its configured model refuses; else 120,000 |
| Melious | file body (no change) | 120,000 bytes | no cap if the model refuses; else 120,000 |
| ollama, API | file body (no change) | 120,000 bytes | no cap if the model refuses; else 120,000 |
| ollama, CLI | stdin if P1 passes, else argv | 120,000 bytes | stdin: as the API, P1 having shown it whole; argv: 120,000 |
| agy (opt-in) | argv (no change) | 120,000 bytes | 120,000 (not probed: a probe spends an Antigravity credit) |

Codex's help (codex-cli 0.163.0), quoted: "If not provided as an argument (or if `-` is used),
instructions are read from stdin." The prompt file goes in the run's private raw folder (mode 700,
already holding the request bodies) and joins the list of stale files cleared at start.

**Step 0 probes**, before building change 2:

- **P1, free.** Do the two CLIs that would read the prompt from stdin send a 400 KB prompt whole?
  Each is pointed at a stub server on 127.0.0.1 that records the request, and the prompt in the
  recorded request must equal the prompt sent, byte for byte. The ollama 0.40.7 CLI (its help
  shows stdin only with `--ask`) reaches it through `OLLAMA_HOST`; Codex through a model provider
  of its own (`-c model_provider=…` with a `base_url` on 127.0.0.1; not checked that 0.163.0
  accepts it). No model runs. A CLI that cannot be pointed at a stub, or whose recorded prompt
  differs, stays at 120,000, whatever P2 finds.
- **P2, the maintainer's call.** One prompt a little past each model's cited window, per seat and
  model in use (Codex's configured model, Melious's GLM 5.3, ollama cloud's GLM 5.3; the ollama
  CLI too if P1 passes), with the reply capped at a few tokens. It is repeated text with a random
  nonce on its first and last lines. Only an error naming a context or token limit counts as
  "refuses". A reply is recorded for information (its reported prompt tokens, and which nonce it
  can quote), never as a limit. One seat at a time; if one replies, stop and report before the
  next. Cost: expected nothing for a seat that refuses (whether a refused request is billed is not
  checked); up to one window of input tokens for a seat that replies (about 500,000 for Codex's
  model, 1,000,000 for GLM 5.3; cited, not measured).

**Considered and dropped:** a cap per seat at a size measured to arrive whole (round 2 of this
plan). It held only for text as dense in tokens as the probe's, for the probed model, and for the
artifact rather than the whole prompt. Then a cap at the point a cutting provider stops (round 3):
it rested on two claims nothing here checks, that every seat's tokenizer is byte-level and that a
reported prompt count is the cut point. The rule above needs neither. Also dropped: a
label of its own for a length refusal (a `CONTEXT_RE` beside `QUOTA_RE`), since the `FAILED` section
already quotes the provider's message; and a nonce check in every review, which needs the model to
cooperate every time, so a forgotten quote would fail a real review.

**What this does not see:** a provider that refuses the probe's prompt but cuts a prompt of some
other size (P2 tests one prompt per model; no finite probe proves "always refuses"); a provider
that later starts cutting instead of refusing; and Codex compacting its first message in a run
with heavy file reading. P2 can be run
again, and `seat_limits.txt` dates each result.

**The split the maintainer suggested**: give Codex the diff as a file to read from the checkout, and
GLM only the app code. Weighed:

- For: no prompt size for Codex at all, and fewer tokens to GLM.
- Against: a tool-using reviewer handed a path reads what it chooses, and nothing would show
  whether it read every hunk; today the whole artifact is in its context. A GLM that never sees the
  tests cannot check them, and tests are where intent lives. Telling app code from tests is a
  per-repo guess about paths.
- **Recommendation: not now.** If P2 finds that Codex and Melious refuse rather than cut, both
  default seats take any artifact up to their model's window, and one past it fails loud. A seat
  whose model cuts gains nothing from change 2: for that seat the split would be the way past
  120,000 bytes. Revisit only then, or if a real artifact goes over a seat's window. If a split
  is ever built, each seat's section and the `reviewers:` line must say what that seat saw, so a
  two-seat round is never read as two seats over the whole change.
- **Strongest case against this recommendation.** A model can read a very long prompt less
  carefully than a short one, and round 1 sends the whole change to every seat. Two focused halves
  might find more than one long whole. That is not measured either way.

## Order, and how the two checks meet

Change 1 lands first, in its own PR: it is the one that cost a wrong round. Its check goes just
before today's size check, so from the start a big stale diff is refused for its base, not its
size: cutting a wrong diff down is the wrong remedy. Change 2 follows in a second PR built on it,
after P2: it moves the script-wide check into each seat, still after the base check. A big delta
round passes the base check with `--base`, then meets each seat's limit on its own. `--base none`
skips only the base check, never a cap.

## Tests

In a new `test_base_check.sh` (listed in the Makefile) for change 1 and in
`test_failed_tier_report.sh` for change 2, all through the script itself, as a caller runs it,
with stub CLIs on `PATH`. The base cases build a throwaway repo with a bare `origin`, so the fetch
is real and local.

| # | Case | Pass when |
|---|---|---|
| T1 | Stale base: origin gains commits touching other files, the branch takes them (as the host's update button does), and the diff is made against the old local default branch | exit 2; stderr lists exactly those files and the command; no stub seat ran |
| T2 | Origin moved on, the branch did not take it, a three-dot diff against the old local branch | runs: the most common case, and the one a wrong check would refuse |
| T3 | Delta: `git diff A..HEAD` with `--verify prior.md --base A` | runs, `base:` names A. With `--verify` and no `--base`: refused, naming `--base`. A delta with no `--verify` and no `--base`, touching a file the branch changed before A: refused with the "--base <that head>" line; one touching only files unchanged before A: runs, and the `base:` line names the files it leaves out |
| T4 | Edge records, each from git itself: a rename at 100% and one below, mode change, binary, new, deleted, symlink, a path with a space and one with a tab, a working-tree diff, `git diff --cached <base>` with the index at `HEAD`, one-patch `format-patch`, a removed line `-- x` and an added `++ x`, a top-level folder named `w` with a 100% rename inside it, uncommitted work on the default branch itself, a file with no newline at its end on the old side, the new side and both; and the run started in a subdirectory (a modified and a new file) | each runs |
| T5 | Refusals: a stale mode change, a hand-made diff, a series, `diff --cc`, a copy record, `--no-prefix`, mnemonic prefixes, colour, plain `git diff` with the index ahead of the base, a run on the default branch itself with a clean working tree (merge base is `HEAD`), outside a work tree, a shallow clone, a fetch that fails, a fetch that hangs (a stub remote that never answers: refused within the limit), `--base -x`, `--base` on a plan | exit 2, each with its message; `--base none` runs, outside a repo too, and prints `base: not checked` |
| T6 | `--local-only` | no fetch reaches the stub remote; uses `origin/HEAD`, or refuses naming `--base` |
| T7 | Coverage: a diff of the last commit only, whose files no earlier commit of the branch touched, no `--base` | runs; the `base:` line names the files left out |
| T8 | Base before size: a stale diff over 120,000 bytes, with no seat measured | refused for its base, not its size |
| T9 | stdin to Codex, listed "refuses" in the `seat_limits.txt` of a copy of the script: the stub asserts its last argument is `-`, that no argument holds `--- BEGIN`, and that stdin carries a 400 KB prompt whole (same bytes, same hash) | passes |
| T10 | A 400 KB artifact, with every off-argv seat listed "refuses" in the `seat_limits.txt` of a copy of the script: each stub records the whole prompt | `reviewers:` reads OK for each |
| T11 | Caps: agy, an unlisted model (a new `CODEX_MODEL`), and a seat P2 found replying, each with a 200 KB artifact, beside a seat listed "refuses" | each capped seat `FAILED` before sending (its stub never ran); the "refuses" seat ran |
| T12 | A seat listed "refuses" whose stub answers with a length error | `FAILED`, quoting the stub's message, like any failed seat |
| T13 | A malformed `seat_limits.txt` line, a 200 KB artifact | every seat `FAILED` before sending, no stub ran, exit 4 as for any round with no reviewer |

The existing cases send a hand-made `change.diff` with no `index` line, from whatever directory
the suite runs in (the repo root under `make`), so they pass `--base none`. `make check` must be
green before each DIFF gate.

## Docs touched

The script's header (usage, `--base`, the closing lines); SKILL.md step 2 (the round-1 command,
the `base:` line, and "Over 117 KB: split it" replaced by the per-seat rule), step 6 (`--base` for
verification rounds, merge links, the wording pass and its confirmation) and step 8;
`references/closeout.md` (the trail's `Base` field and Artifact column, re-gates);
`skills/website-review/SKILL.md` and `skills/seo-reposition/SKILL.md`, whose `--diff` commands
gain a sentence on `--base`; and the README, since site repos that vendor this skill may have no
`origin` and must pass `--base`.

## Checked here, and not

Checked on 2026-10-21: the script's code paths quoted above; Codex's help (codex-cli 0.163.0);
Codex's model cache (500,000 tokens, 95% usable, for the model configured here); `ollama show`
(1,048,576 tokens for GLM 5.3); Melious's model list (no context field; a third-party listing says
1,000,000 tokens); `getconf ARG_MAX` on macOS (1,048,576). On git 2.33: a binary file has an
`index` line, a pure rename and a mode-only change have none, a working-tree diff's new id equals
`git hash-object -- <path>` of the file, a name with a space gets a tab after it on the `---` line,
`git fetch origin HEAD` fills `FETCH_HEAD` (per worktree) without moving `origin/<default>`, and
with `--full-index --no-renames` git's own patch has no `index` line for a mode-only change and
shows a rename as a deletion and an addition with the same id.

Not checked: the Linux argument limit (cited by the script today); whether the ollama CLI and
Codex send a large stdin prompt whole (P1); whether agy's `-p` reads stdin; what each seat does
past its window (P2); any provider's real serving window.

Outside this plan: under `--local-only`, a local model with a small context may cut the prompt
silently today, whatever its size. A BUGLOG row, not this change.

## Open for the maintainer

1. P2, and the risk it cannot close (R4-02 in the trail): test each seat once past its model's
   window, and accept that one refusal stands for "this provider refuses rather than cuts"? The
   probe is expected to cost nothing where the provider refuses (whether a refused request is
   billed is not checked); up to one window of input tokens (about 500,000 for Codex, 1,000,000
   for GLM 5.3) where it replies. Without both, change 2 moves the transports but
   every seat stays at 120,000 bytes, so it lifts nothing.
2. The split: build it, or leave it as recommended above?
