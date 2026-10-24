# Onboarding — the first-use wizard

Read this when the skill is invoked and no reviewer that is **cross-model for
the CURRENT host** is installed and working. "The Reviewer stack", "the
Independence rule", and numbered "Procedure step N" references below refer to
SKILL.md.

## Contents
- Step 1 — Sell the benefit first
- Step 2 — Check what's already there
- Step 3 — Help them choose
- Step 4 — The human-only steps (4a — your steps · 4b — ollama: pick the model from RAM)
- Step 5 — Confirm it's actually working
- Step 6 — Teach them how to use it


**Everything below assumes a Claude Code host (the common case), where both
Codex and Antigravity are cross-model and either one satisfies the gate.**
If the current host is itself Codex or Antigravity/Gemini, substitute per
the Independence-rule table above wherever this wizard names a specific tool
as "the" recommended reviewer or as satisfying/not-satisfying the gate —
don't apply the Claude-host examples literally on a different host. This
applies to every step below, including the default recommendation in Step 3
and the fallback description in Step 6, not just the detection logic in
Step 2.

**When invoked and no reviewer that's gate-satisfying for the current host is
installed and working** (see Step 2's fuller definition below — not just
"nothing is installed at all"), do not dump install commands. Walk the user
through it like a friendly wizard.
Assume a non-technical user who has never used a terminal seriously — do the
heavy lifting yourself; clearly flag the few things only they can do. Full
install commands, the tool comparison table, and the ollama RAM/model tables
referenced below all live in `references/setup-guide.md` — pull from it as
needed rather than re-deriving any of this from general knowledge, since
exact free-tier limits and install commands drift and that file has current
sourcing plus an explicit "don't quote a stale number" caveat. **Numbers
belong in that reference file, not hardcoded in this wizard** — when a step
below needs a figure (a time estimate, a limit, a lockout report), pull it
from there rather than restating one here from memory, so there is exactly
one place to update when it goes stale.

**"Installed" is not "working" — three distinct checks, don't conflate them.**
On macOS/Linux, run these directly. **On Windows, if the agent's own shell is
PowerShell rather than a POSIX shell (WSL, git-bash), `command -v`/`test -f`
won't work as written** — use the PowerShell equivalents shown:
1. *On PATH* — `p="$(command -v codex)" && test -f "$p" && test -x "$p"` /
   same for `agy`/`ollama` (a bare `command -v` alone can match a shell
   alias or function, not the real binary; `test -x` alone isn't enough
   either — a directory can be `-x` without being the binary — so require
   both `-f` and `-x` on the resolved path). This is a best-effort check,
   not a perfect one — an edge case remains where `command -v` returns a
   bare function name and a same-named executable happens to sit in the
   current directory; don't spend more effort closing that specific gap,
   Step 5's real-review-output check is what actually matters. (PowerShell:
   `Get-Command codex -CommandType Application -ErrorAction
   SilentlyContinue`, same pattern for `agy`/`ollama` — `-CommandType
   Application` is the equivalent guard against matching an alias or
   function instead of the actual binary).
   Proves the binary exists, nothing more.
2. *Looks authenticated* — `test -f ~/.codex/auth.json` (PowerShell:
   `Test-Path -LiteralPath "$HOME\.codex\auth.json" -PathType Leaf` — plain
   `Test-Path` without `-PathType Leaf` would also match a directory
   accidentally named `auth.json`) for Codex; `agy models` returns a model
   list, not an error (Antigravity); `ollama list` returns without error
   (ollama, though this only proves the daemon runs, not that any model is
   pulled yet). A stale/expired token can still pass this check.
3. *Actually works* — a real review request returns real review-shaped
   output. This is the only check that proves the tool is usable right now;
   see Step 5. Don't report "done" off checks 1–2 alone.

### Step 1 — Sell the benefit first (before asking for anything)

In 3–4 plain sentences:
- *"Before I hand you a finished plan, or before we merge a real change, I can
  get it checked by a completely different AI — one that didn't write it, so
  it can catch mistakes I might miss myself. Think of it as a second, more
  skeptical pair of eyes."*
- *"This is free to set up — no new subscription required. Most of the setup
  is something I can do for you; you'll just need to click a couple of
  sign-in prompts yourself."*

Then ask **"Want to set this up now?"** If they say **no**, don't proceed —
but don't silently treat the artifact as reviewed either: this skill's own
rule is BLOCK until reviewed or explicitly waived (see Procedure step 5).
Tell them plainly: *"OK — I won't set this up now. That means I can't run an
independent review until either you change your mind, or you explicitly tell
me to skip the review this time (I'll record that as your call, not mine)."*
Record a decline as a named owner waiver if a gated action (merge, ship) is
actually blocked on it — don't just drop the topic.

### Step 2 — Check what's already there; never re-onboard a returning user

Run the detection commands above. **The skip condition is "the user's actual
request is already satisfied AND the gate is actually satisfiable with
what's installed," not "any one tool works":** per this skill's own
Independence rule above, a reviewer only satisfies the gate if it's
**cross-model relative to the CURRENT host**, not just "installed" — ollama
LOCAL never satisfies it regardless of host (tier 5 — sanity pass only), but
ollama CLOUD (a signed-in `:cloud`-tagged model) DOES count, same as
Codex/Antigravity — it's tier 2, part of the standard default pair (see
Reviewer stack above), not tier 5. Which cloud
tool(s) count as cross-model depends on what's running this wizard: on a
Claude Code host, Codex and/or ollama-cloud and/or Antigravity all count; on
a Codex host, Codex CLI alone does NOT (same family as the host) —
ollama-cloud or Antigravity are the cross-model options there; on an
Antigravity/Gemini host, the reverse (Codex or ollama-cloud count,
Antigravity doesn't).
- If the user asked generically for review setup, and ≥1 reviewer that is
  **cross-model for the current host** (per the table above — not LOCAL
  ollama alone, and not same-family-as-host alone) is already installed and
  authenticated: **first run one real test review per Step 5's evidence
  standard — installed-and-authenticated is checks 1–2, not proof it
  works — then, only once that passes, skip the rest of onboarding and go
  straight to Step 6.** A failed test run means treat it as broken, not as
  done (see the last bullet below).
- If only LOCAL ollama is set up so far, treat that the same as "nothing set
  up yet" for gate purposes — it's a fine backup to already have, but proceed
  to Step 3 to add a cloud reviewer (including ollama-cloud itself — `ollama
  signin` on the same install), don't report the wizard as done.
- If the user asked for a **specific** tool that isn't set up yet (e.g. "set
  up ollama too" when only Codex is working), don't skip — go set up the one
  they actually asked for, even though the gate is already technically
  satisfiable without it.
- If a previously-working tool now fails (expired login, uninstalled), say
  plainly which one broke and offer to either fix it or move on with what's
  still working — don't restart the whole wizard for the tools that are fine.

### Step 3 — Help them choose (they don't need all three)

Present the three options as a short, plain-language summary — pull the full
comparison table from `references/setup-guide.md` if the user wants more
detail, but lead with this, not the table:

- **Codex CLI (OpenAI)** — free ChatGPT account, no payment. Of the two
  hosted-CLI options, the more predictable free tier (see `references/setup-guide.md`
  for what's currently known about its limits — pull the actual figures from
  there, don't restate a number from memory here).
- **Antigravity (Google)** — free personal Gmail account, no payment. Just as
  sharp a reviewer, but **its free-tier usage limit is tight and not clearly
  published.** Pull the current, sourced detail (including a dated real-world
  report of severe lockouts) from `references/setup-guide.md` and say it
  plainly — don't undersell it, and don't guess at numbers not in that file.
- **ollama** — free either way, two distinct modes:
  - *Cloud* (any `:cloud`-tagged model — the script auto-uses whichever one
    the signin provides) — needs a one-time `ollama signin` (free, no
    payment) but nothing beyond that; runs on Ollama's own servers, so it
    DOES leave the machine. This is the script's actual
    standard second reviewer — sharp enough to satisfy the gate on its own,
    same tier as Codex/Antigravity.
  - *Local* (a model pulled to this computer) — completely free, unlimited,
    private (nothing leaves the machine), no account at all. Quality depends
    on the computer's RAM, and even a well-equipped machine's best local
    model lags the cloud options on subtle bugs — sanity-pass only, never
    satisfies the gate alone. Good as a free unlimited *backup*.

**Default recommendation if they're unsure (Claude Code host — see the note
at the top of this section for any other host):** set up Codex CLI plus
ollama-cloud (a free `ollama signin` — no payment method required) — that's the script's
actual standard default pair, and it runs automatically with no flags once
both are set up. Add a local ollama model pull too, as a free unlimited
backup for whenever Codex or ollama-cloud's free tier is temporarily tapped
out. Antigravity is worth adding on top if they want a third, independent
model family and are comfortable with a less predictable free tier — it is
not required. **If the current host is itself Codex, swap this
recommendation: Codex CLI would be same-family and wouldn't satisfy the
gate — recommend ollama-cloud (the script's standard automatic second reviewer)
as the main reviewer instead**, with local ollama as the same free backup either
way. Antigravity stays what it is everywhere else in this skill: an opt-in extra
that spends a scarce credit, never the default recommendation.

Ask which one(s) to set up, then proceed per tool below.

### Step 4 — The human-only steps ( 🧑 **you do this** )

Regardless of which tool(s): a sign-in step always needs the user's own
click, and installing anything means running a command in their terminal for
the first time — walk them to opening a terminal (Terminal.app on macOS,
PowerShell on Windows, their terminal of choice on Linux) if they've never
done it, one plain instruction at a time.

- 🧑 **Codex:** open a terminal, paste the install command I give you, press
  enter, wait for it to finish. Then run `codex` and follow the "Sign in with
  ChatGPT" prompt in the browser window that opens — one click to approve.
- 🧑 **Antigravity/`agy`:** same shape — paste the install command, then run
  `agy models` and follow the Google sign-in prompt (personal Gmail account).
- 🧑 **ollama:** for macOS/Windows, download and open the installer like any
  normal app (no terminal for the install itself) — but the model download
  in Step 4b still needs a terminal command; on Linux there's a single
  terminal install command. **For ollama-cloud** (the script's actual
  standard second reviewer), also run `ollama signin` once and follow the
  browser sign-in prompt — one click, free, no payment. For the local backup
  model, tell me your available RAM (or let me detect it) so I can recommend
  one — do NOT let them guess a model size themselves; see Step 4b.

Hand these over **one at a time**, wait for confirmation each step landed,
don't paste all the commands at once.

### Step 4a — Your steps ( 🤖 **I do this** )

- 🤖 Give the exact install command for their OS (from
  `references/setup-guide.md`), one tool at a time.
- 🤖 After each install, verify it actually landed using check 1's `-f`/`-x`
  test above (not a bare `command -v`, which check 1 itself says can match an
  alias or function rather than the real binary) before declaring success —
  a "looks done" claim without checking is exactly the kind of thing this
  skill exists to prevent elsewhere; don't do it here either.
- 🤖 If a `PATH`/"command not found" issue comes up after an apparently
  successful install, try the standard fix (new terminal window) before
  escalating — see the Gotchas in `references/setup-guide.md`.

### Step 4b — ollama only: pick the model from RAM, don't guess

**This is a machine-capability decision, not a preference — check before
recommending.**

- 🤖 Detect **total installed** RAM using the OS-appropriate command from
  `references/setup-guide.md` (`sysctl hw.memsize` on macOS, `systeminfo` or
  Task Manager on Windows, `free -h` on Linux) — most of these print BOTH a
  total and a free/available figure side by side; use the total one, not
  the free/available one printed next to it. If the machine is under heavy
  memory pressure from other apps, say so rather than silently dropping a
  tier. If
  you can't run the command directly (e.g. the user is on a different
  machine than the one you have shell access to), ask them to run it and
  paste back the number.
- 🤖 Look up the matching row in the RAM → model table in
  `references/setup-guide.md` and recommend exactly ONE model tag — don't
  offer the full menu and make a non-technical user pick blind.
- 🤖 **Warn about the download before pulling it** — model files run
  multiple GB; say the size and ask before running `ollama pull <model>` on
  a metered or slow connection.
- 🤖 State the honest ceiling plainly: *"This will catch a lot of the
  obvious stuff for free, but it's not as sharp as Codex or Antigravity on
  subtle bugs — think of it as a backup, not a replacement."* Don't let
  "free and unlimited" imply "just as good."

### Step 5 — Confirm it's actually working (with evidence, not a claim)

Run one real, small test review with each newly-configured tool — a trivial
throwaway artifact is fine (e.g. a two-line diff). **Quote or closely
paraphrase one actual line the reviewer produced**, not just your own
success claim: *"✅ Codex is working — I gave it a small test diff and it
came back with: '[actual excerpt from its output]'."* An assertion of
success with no quoted output is not evidence and doesn't satisfy this step.
A tool that installed but can't produce a real review (bad auth, model
unavailable, `looks_like_review()` in the script would reject its output) is
not done — fix it or tell the user honestly it isn't working yet.

**For Antigravity/`agy` specifically, this step must also confirm the
*model*, not just that a review came back.** `agy models` (used in Step
2/4a) only proves models can be listed — it says nothing about which model
the CLI will actually use for a review. Apply the ONE rule this whole skill
uses everywhere else (see the Independence rule table) — don't re-derive a
per-host list here, that's what kept breaking across earlier drafts of this
paragraph: **the reviewer's confirmed model family must differ from the
CURRENT host's family. That's it — check it against whichever host is
actually running right now, for whichever reviewer is actually being
verified, every time.**

`agy` runs whatever model its CLI is configured for — typically a
Gemini-family default from the Antigravity login (`independent_review.sh`
passes `--model "$AGY_MODEL"` only when that env var is set — the var is
this script's own convention, mapped straight onto `agy`'s real `--model`
flag; it is not a native `agy` setting, so don't expect it to do anything
outside this script). Don't assume the default's family: confirm it from
the run's own output and apply the one rule — on a Gemini host
specifically, `agy` satisfies the gate only with `AGY_MODEL` overridden to
a non-Gemini family; on any other host its Gemini-family default typically
satisfies it, once confirmed. If a fallback reviewer is needed
because `agy`'s model can't be confirmed, apply the same one rule to pick
it — check whichever candidate's model family actually differs from the
current host's, rather than defaulting to a fixed choice; on most hosts
that resolves to Codex (cross-model everywhere except when the host is
itself Codex), but it's a derived result of the rule, not a hardcoded
default.

Look for a model identifier in the test review's own output — the actual
invocation's reported model, not a config file (a valid Codex install may
have no `config.toml`, or one with no explicit `model` entry, sourcing its
effective model from defaults/profile/CLI args instead; `codex exec` does
reliably print its effective config in its own output regardless, e.g.
a `model: <name>` line — that's the thing to read, not the file). `agy`'s
output format for this wasn't independently confirmed while writing this
skill, so treat that pattern as a lead to check, not a guarantee. **If no
model identifier can be confirmed at all, do not report `agy` as
gate-satisfying** — "a review came back" and "a review came back from a
confirmed cross-model model" are different claims, and only the second one
closes the gate; say plainly that the model couldn't be verified and pick a
fallback the same way (the one rule, above) rather than defaulting to any
specific tool by name.

### Step 6 — THEN teach them how to use it. Don't skip this.

Tell the user they never need to touch the terminal again for this — from
now on, in any normal session, they just ask in plain language: *"get this
reviewed,"* *"codex review,"* *"antigravity review,"* *"independent review
this before we merge,"* or similar (see the trigger phrases in this skill's
frontmatter) and the review runs automatically using whichever tool(s) are
set up.

**Set the free-tier expectation now, not when it surprises them — and be
accurate about what "fallback" actually means:** *"Codex and Antigravity are
free but not unlimited — you may occasionally hit a limit (see
references/setup-guide.md for what's currently known about each). Here's
what actually happens if you do, depending on how review is run: by
default Codex and ollama-cloud run together each time — **Antigravity never
runs by default, even once it's set up**, because it spends one of your scarce
credits and waits for you to ask — so if Codex is temporarily rate-limited,
that round still runs with the ollama seat (cloud if it's available, local as a
degraded fallback). **That keeps you fully covered only if a
cross-model reviewer for this host is still available — if LOCAL ollama is the
only thing left, that round is a lighter-weight, degraded pass, not a full
substitute** (same rule as everywhere else in this skill: LOCAL ollama alone
never closes the gate on its own — signed-in ollama-cloud does). If review is
run in quick 'first available'
mode instead, it tries Codex first and only moves to the next one if Codex
fails outright. Either way, having a **locally pulled** ollama model (not
just `ollama signin`) means there's always a free, unlimited, fully-private
option in the mix — just know it's a lighter-weight reviewer, not a
like-for-like replacement."*
