# Setting up a reviewer — full detail

The onboarding wizard in `SKILL.md` points here for the install commands, the
full tool comparison, and the ollama model/RAM tables. This file is reference
material for the agent to pull from during the wizard — it is not meant to be
dumped on the user wholesale.

**Freshness warning:** pricing, free-tier quotas, and exact install commands
for all three tools change often (Codex CLI's pricing model itself changed
once already in 2026, message-based → token/credit-based). Nothing below
should be presented to the user as a permanent guarantee — see "Verify before
quoting a number" at the bottom.

## The three options, compared

| | Codex CLI (OpenAI) | Antigravity / `agy` (Google) | ollama (local) |
|---|---|---|---|
| **Account needed** | Free ChatGPT account | Free personal Gmail account | None |
| **Cost** | Free tier, paid plans from $20/mo | Free tier, paid plans from $20/mo | $0, always |
| **Setup effort (non-technical)** | ~10–20 min; one terminal command + browser sign-in | ~10–20 min; IDE is a plain installer, but the `agy` CLI (what this skill actually uses) needs a separate terminal command | ~10–20 min install + a model download (minutes to tens of minutes depending on connection and model size) |
| **Needs a terminal at all?** | Yes, once, to install | Yes, once, to install `agy` (the IDE alone is terminal-free, but doesn't power this skill) | Yes, once, to install and pull a model |
| **Review quality** | Sharp, frontier-class | Sharp, frontier-class (Gemini family) | Noticeably weaker unless the machine can run a large (20B+) model — see below |
| **Usage limits on free tier** | Rolling window, resets in hours; exact numbers are not reliably published and vary by plan/model — see caveat below | "Basic weekly rate limits," no published number; **one dated real-world report (XDA Developers, May 12 2026) describes a lockout of up to ~7 days after as little as 20–30 minutes of use** — the free tier is tight and its limits are opaque by design; see caveat below | None — fully unlimited, runs entirely on your own machine |
| **Privacy** | Diff/plan text leaves your machine to OpenAI | Diff/plan text leaves your machine to Google | Nothing leaves your machine |
| **What happens when you hit the limit** | Current task finishes; new tasks pause until the window resets, or upgrade, or (if configured) pay per token via an API key | Locked out until the weekly reset — no pay-as-you-go on the free tier itself (that requires upgrading to Pro/Ultra) | N/A — never happens |

**Recommendation to give a non-technical user who asks "which one?" (assumes
the AI assistant running this guide is Claude Code — the common case; if the
assistant IS Codex or Antigravity/Gemini itself, that tool is same-family
with itself and doesn't satisfy the skill's cross-model gate, so swap the
recommendation to whichever cloud tool is genuinely a different model
family — see SKILL.md's Independence rule):**
Set up Codex CLI first (most predictable free tier of the two cloud options,
least surprising). Set up ollama alongside it as a free, unlimited backup —
it's the fallback for whenever Codex's limit is hit, or for a totally private
review with nothing leaving the machine. Antigravity is worth adding too if
they're comfortable with the tighter/less predictable free tier and want a
third, genuinely independent model family in the mix — the skill's own
design values having more than one cross-model reviewer.

## Install commands per tool

### Codex CLI

- **macOS (Homebrew):** `brew install --cask codex`
- **macOS/Linux (no Homebrew):** `curl -fsSL https://chatgpt.com/codex/install.sh | sh`
- **Windows (PowerShell):** `powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"`
- **Any OS with Node.js already installed:** `npm install -g @openai/codex`

First run: type `codex` in a terminal → it prompts to authenticate → choose
"Sign in with ChatGPT" (opens a browser, one click to approve).

**Gotchas:**
- Fresh Mac, first-ever `brew` command: macOS may prompt to install Xcode
  Command Line Tools first (a separate few-minute download) — normal, let it
  finish, then re-run the `brew install` command.
- The `npm install -g` path needs Node.js already on the machine — if
  `npm: command not found`, install Node.js first (nodejs.org, the LTS
  installer) or use one of the other install paths instead.
- After install, if `codex: command not found` in a *new* terminal window,
  the install path isn't on `PATH` — closing and reopening the terminal
  usually fixes it; if not, this is a "🧑 hand-off to a human with more
  terminal experience" situation, not something to keep guessing at.

### Antigravity IDE + `agy` CLI

These are **two separate installs** that happen to share a login. The IDE is
a normal point-and-click app; `agy` is what this skill's automated reviews
actually use, and it needs a terminal command to install.

- **IDE (optional — only needed if the user also wants to use Antigravity
  themselves interactively):** download the installer from
  antigravity.google/download (macOS `.dmg`, Windows `.exe`, Linux `.tar.gz`)
  and install like any normal app. macOS with Homebrew:
  `brew install --cask antigravity-ide`.
- **`agy` CLI (this is the one the skill needs):**
  - macOS/Linux: `curl -fsSL https://antigravity.google/cli/install.sh | bash`
  - Windows PowerShell: `irm https://antigravity.google/cli/install.ps1 | iex`
  - macOS with Homebrew: `brew install --cask antigravity-cli`

First run: `agy` prompts a Google sign-in (personal Gmail account, no
Workspace/corporate account needed — those go through a separate enterprise
path and aren't relevant here). `agy models` afterward lists available
models and confirms the login worked.

**Gotchas:**
- Don't confuse "I installed the Antigravity IDE" with "the skill can use
  Antigravity" — they're separate installs. Only `agy` on `PATH` and signed
  in makes the skill's automated review work.
- The free tier's weekly limit is opaque (Google doesn't publish an exact
  number) and real-world reports describe getting locked out after quite
  light use. Tell the user this plainly *before* they rely on it for
  anything time-sensitive — see the comparison table above.
- `agy --help` run with no arguments outside a script context can launch the
  full Antigravity GUI app instead of printing help text — don't probe it
  curiously; use `agy models` to check the install/login instead.

### ollama (local, no account)

- **macOS:** download the `.dmg` from ollama.com/download, open it, drag the
  app to Applications. (Or `brew install ollama`.)
- **Windows:** download and run the `.exe` installer from ollama.com/download
  — installs and starts like any normal Windows app.
- **Linux:** `curl -fsSL https://ollama.com/install.sh | sh`

After install, model download and every future run happens from a terminal
(`ollama pull <model>`, `ollama run <model>`) regardless of OS — there's no
avoiding the terminal for this step, unlike the IDE-only Antigravity path.

### melious.ai (API key, no install)

The fallback for the ollama seat (SKILL.md, reviewer stack, item 2): with `MELIOUS_MODEL` set, a
round whose ollama seat did not count (no model or CLI, a quota refusal or other failure, a local
sanity pass) sends the same text-only prompt here, so the pair keeps its second reviewer. Nothing
to install beyond `curl` and Perl 5.10 or newer (with JSON::PP), which the ollama API path needs
too. When one is missing, the Melious seat is skipped, and so is ollama on its API path; the
summary names what is missing, as in `melious SKIPPED (curl not found)`.

- **Key, on your own machine:** `~/.config/reviewers/melious.env`, `chmod 600`, one line
  `MELIOUS_API_KEY=<key>`, the key alone (a trailing comment would become part of it). Never
  source, cat or echo it. Check it is there with
  `grep -c '^MELIOUS_API_KEY=' ~/.config/reviewers/melious.env` (prints 1). Another path:
  `MELIOUS_ENV_FILE`.
- **Key, in a cloud session:** an API credential for `api.melious.ai` in the environment's
  settings (cloud environment menu → Edit): the proxy adds it to each call, and the seat sends no
  key of its own when `MELIOUS_API_KEY` and the env file are both absent. An environment variable
  `MELIOUS_API_KEY` works too. The host must be allowed under Network access, or every call fails
  with a proxy 403, which the FAILED section reports as "is the host allowed by the network
  policy?". Settings take effect in a NEW session.
- **Model:** `MELIOUS_MODEL=<id>`, an id from `GET https://api.melious.ai/v1/models`. The seat
  names no default.
- **Budget:** `MELIOUS_MAX_TOKENS` (default 96000; a reasoning model ran out at 48000 on a
  27 KB diff, and finished at 96000 in 296-1624 s; `MELIOUS_API_TIMEOUT` defaults to 3600 s). A
  model whose output cap is lower answers with an error, quoted in the FAILED section: lower the
  budget for it. A reasoning model can still spend all of it thinking and return no text; the
  seat fails and says so. Raise it and run again.
- **Reasoning that leaks into the reply:** the provider can end a reasoning model's thinking at a
  closing think tag the model writes or quotes (from the artifact, or typed while reasoning
  about tag handling), and send the rest of the trace as the reply (seen 2026-10-05: 100-290 KB
  of trace, the review at the very end). The seat therefore asks for a marker line,
  `=== FINAL REVIEW <random hex> ===`, new on each run so the reviewed diff cannot contain it,
  before the final answer and keeps what follows the last marker that ends a line and has
  findings after it (Markdown around the marker is fine; a marker repeated at the end or quoted
  after the review does not count). Text before it on its line is fine too, as when the model
  glues it to its last line of reasoning, and the section then says so. A marker that looks
  quoted is skipped (after other text on a finding line, right after a backtick, or just inside
  a fence), so a finding that quotes the marker does not cut the findings above it; when more
  than one marker has findings after it, the section says so too, as a skip or a quote the rules
  miss can move the cut. The section says how much was dropped, and
  the reply as it came is in `melious.full` in the raw dir. With no usable marker the whole
  reply is kept and the section always warns that it may be leaked reasoning rather than a
  finished review: read it from the end, and rerun the round if it is working notes (a 21 KB reply
  of notes with no marker was seen; size alone does not tell). A leak can also run on with no marker until the connection drops (seen once,
  after 38 minutes): the seat fails with "reply cut off" and keeps what came in `melious.resp`;
  run it again. The seat and its tests build think tags at runtime, so this repo's files carry none.
- **Run:** set `MELIOUS_MODEL=<id>` and run the pair as usual; the seat stands in when ollama did
  not count. `--seat melious` runs it alone (the wording pass, a re-gate); `--seat ollama` never
  falls back to it, and `--local-only` never calls it. The cost log records the seat as `melious` with
  the model in its own column. To make Melious the second seat and ollama its fallback, add
  `SECOND_SEAT=melious` (and an `OLLAMA_MODEL` for the fallback, or the first `:cloud` tag is used).
- **First use per repo:** ask the owner before a repo's content goes to melious.ai the first time
  (SKILL.md, Procedure step 1).

## Picking a model — RAM decides this, don't guess

**Check installed RAM first, then pick from the table — don't let the user
guess or default to the biggest model "to be safe."** A model that doesn't
fit in RAM either fails to load or runs so slowly it's unusable. The table
below is keyed to *installed* RAM, not RAM free at this exact moment — if the
machine is already under heavy memory pressure from other apps, the honest
move is telling the user to close them first, not silently dropping a tier.

**Check the machine:**
- macOS: `sysctl hw.memsize` (answer is in bytes — divide by 1,073,741,824
  for GB), or Apple menu → About This Mac.
- Windows: Task Manager (Ctrl+Shift+Esc) → Performance tab → Memory; the same
  tab's GPU entry shows dedicated VRAM if there's a discrete GPU. Or
  `systeminfo` in Command Prompt → "Total Physical Memory."
- Linux: `free -h` for RAM; `nvidia-smi` (NVIDIA GPU) or `lspci | grep -i vga`
  to check for a discrete GPU.

Apple Silicon Macs (M1–M4) use unified memory — there's no separate VRAM
number to check; the figure from `sysctl hw.memsize` is the whole budget.

**RAM → model table** (dated examples for the LOCAL sanity tier only — the
review pipeline itself is model-agnostic and hardcodes none of them; sizes are each tag's default-pull download size, not
a uniform quantization scheme — ollama's per-tag default varies (e.g.
`gpt-oss` ships natively in MXFP4, `deepseek-coder-v2:16b` defaults to
Q4_0); run `ollama show <tag>` if the exact quantization matters for your
case, don't assume Q4_K_M applies to every row. Sized to leave headroom for
the OS — each row's model is meaningfully smaller than the RAM tier it's
keyed to, on purpose. One default tag per row — recommend exactly that one;
mention a row's noted exception only when the user explicitly accepts its
stated constraints, never as an unprompted choice to pick between):

| Installed RAM | Pull this | Size | What it's realistically good for |
|---|---|---|---|
| 8 GB | `qwen2.5-coder:7b` | 4.7 GB | Surface-level bugs: obvious null-check gaps, off-by-ones, inverted conditionals. Close other apps first — it's tight. |
| 16 GB | `deepseek-coder-v2:16b` | 8.9 GB | Noticeably better context-holding than 7B; still not adversarial-grade. (`gpt-oss:20b`, 14 GB, is sharper but leaves only ~2 GB for the OS and everything else — don't recommend it as the default; mention it only if the user says they'll close every other app first.) |
| 32 GB | `qwen3-coder:30b` | ~19 GB | The best currently-realistic local option — meaningfully narrows the gap to cloud models, though still a notch below Codex/Antigravity on subtle, multi-file, or business-logic bugs. |
| 64–95 GB | `llama3.3:70b` | ~43 GB | Diminishing returns vs. 30B for most review purposes; only worth it if the RAM is already sitting there unused. |
| 96 GB+ | `gpt-oss:120b` | 65 GB | Same diminishing-returns caveat as `llama3.3:70b` — a 65 GB model needs real headroom above it, which is why it's a separate tier rather than folded into the 64 GB row (a 64 GB machine can't fit it at all). |

Tags and sizes above were spot-checked at the time of writing; ollama library
retags occasionally change a tag's underlying quantization or default
variant. If a pull comes back a meaningfully different size than the table
says, trust `ollama list`'s actual reported size over this table and recheck
against RAM before proceeding — don't assume the table is still current.

(`qwen3-coder:30b` and `gpt-oss:20b` are mixture-of-experts models — despite
the "30B"/"20B" name, they only load their active-expert weights, which is
why their RAM footprint tracks the download size, not the full parameter
count. This is why a "30B" model fits in ~20 GB.)

**Be honest about the ceiling.** Even the best model that fits on a normal
laptop (`qwen3-coder:30b`) still lags frontier cloud models (Codex,
Antigravity/Gemini, Claude) on subtle, multi-file, or business-logic-context
bugs, and is more prone to confidently-wrong explanations. Per the skill's
own reviewer-tier rules, ollama **never satisfies the review gate alone** —
it's a free, always-available sanity pass and a backup when the cloud
options are unavailable or rate-limited, not a standing replacement for them.
Say this to the user directly; don't let "it's free and unlimited" imply
"it's just as good."

**Legacy models to skip:** `codellama` (Meta, 2023) is superseded by
`qwen2.5-coder`/`deepseek-coder-v2`/`qwen3-coder` on essentially every coding
benchmark — don't recommend it as a first choice. `granite-code` (IBM) is a
reasonable niche pick only for legacy enterprise languages (COBOL, older
Java) — not a general recommendation.

## Getting a Claude/Anthropic reviewer on a non-Claude host

When the assistant running this skill is itself Codex or Antigravity/Gemini, SKILL.md's
Independence rule already lists cross-model options that don't require Claude at all — e.g. on a
Codex host, ollama-cloud or Gemini both satisfy the gate alone. Claude is an *additional* option,
not a requirement: useful when you specifically want a third, distinct model family in the mix,
or when the other options are unavailable or rate-limited. The Antigravity CLI (`agy`) can reach one —
set `AGY_MODEL` to a Claude model from `agy models` and the script runs
`agy --sandbox --mode plan --model "<that model>" -p "<review prompt>"` (`run_agy` in
`scripts/independent_review.sh`), via the same free Antigravity/Gemini login used for the Gemini
seat elsewhere in this guide. Onboarding's model-confirmation step (Step 5 at this writing) covers
checking which model actually ran.
Confirm the model family from the run's own output, per that same step's rule — the confirmed
family, not an assumed default, is what satisfies the gate. The older `agy --sandbox -p` form worked
headless on 2026-07-02 but returned nothing on 2026-09-26 (a tool call auto-denied), which is why
`--mode plan` and a text-only prompt were added. On 2026-09-27 a plan-mode run still came back
empty: the prompt said "You have NO tools", the model tried `echo` to test that, and the refusal
ended the run. agy now gets its own prompt, which drops that claim, asks for no tool calls, and
says a call can lose the review. Neither change makes an empty run impossible: re-verify before
relying on it.

This is **not** a separate free lane — it's the same `agy` CLI and the same scarce-quota,
opt-in-only rule as every other Antigravity use in this skill (see SKILL.md's reviewer stack).
Claude Code itself has no free tier (Pro/API only); the free claude.ai paste tier (tier 6, manual
paste) fits a plan or a small diff at best.

## Verify before quoting a number

Two things researched for this guide are explicitly **unstable and likely to
drift**:

1. **Codex CLI's exact free-tier usage numbers.** Independent sources gave
   inconsistent ranges for "messages per 5-hour window" depending on plan and
   model, and OpenAI's own canonical pricing page could not be fetched
   directly during this research (blocked). Don't state a specific number to
   a user — point them at OpenAI's current pricing page
   ([chatgpt.com/codex/pricing](https://chatgpt.com/codex/pricing)) if they
   want exact figures, and describe the shape qualitatively instead ("a
   rolling several-hour window, resets automatically, current task finishes
   even if you hit it mid-task").
2. **Antigravity's exact free-tier quota.** Google has deliberately not
   published a number ("basic weekly rate limits" is the entire official
   description as of this writing). The one concrete data point available is
   a single dated report — XDA Developers, May 12 2026, ["I tried Google's
   Antigravity for a week, and this limitation made me close it for
   good"](https://www.xda-developers.com/tried-googles-antigravity-limitation-made-close-it-good/)
   — describing a real-world lockout of up to ~7 days after roughly 20–30
   minutes of active use. Cite it as exactly that (one reviewer's dated
   account, not an
   official guarantee), not as a hard fact about what every user will
   experience — and don't drop the citation when quoting the number; the
   number without its source is exactly the kind of stale-prone claim this
   caveat exists to prevent.

If either tool's pricing page is reachable when this guide is next revisited,
re-verify and update this file rather than propagating stale numbers forward.
