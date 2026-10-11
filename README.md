# website-builder

[![Latest release](https://img.shields.io/github/v/release/karero/website-builder?label=latest%20release&color=2ea44f)](https://github.com/karero/website-builder/releases/latest)

**Build a fast, mobile-friendly, SEO-ready website with help from an AI coding assistant.**

website-builder is an open-source skill suite for **Claude Code**, **OpenAI Codex**, and
**Google Antigravity**. It turns a short brief into a complete website — content, mobile-first
responsive design, SEO, accessibility checks, schema markup, tests, and launch support — on a
modern, privacy-friendly stack (Astro → GitHub → Cloudflare Pages).

You can use it even if you're not deeply technical. Whether you're a founder, a community
organiser, a solo builder, a small team, or a developer, **the easiest way to start is to
let your AI assistant guide you step by step.**

> 🧭 **Never opened a terminal before?** Start with the gentle walkthrough in
> [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md).

> 🇩🇪 **Auch auf Deutsch:** Deine KI spricht Deutsch mit dir — du kannst mit dem Baukasten
> deutsche Webseiten bauen, mit denselben SEO- und GEO-Leitlinien wie auf Englisch und
> mit deutschen Qualitätsprüfungen für Texte, Rechtstexte und Metadaten.
> Schreib deinem Assistenten einfach auf Deutsch, er antwortet auf Deutsch — der
> Copy-paste-Prompt unten funktioniert genauso, oder häng „Bitte auf Deutsch.“ an.

## What it helps you build

Real sites people ship with it:

- event and community sites
- startup landing pages
- expert / personal profiles
- resource hubs
- small studio or agency websites

It's **not** a hosted no-code website builder. You own the code, the repository, and the
domain — there's no platform you're locked into, and no hosted-builder subscription required
to keep a basic static site online. (Your domain registration and your AI tool may still have
their own costs.)

## You don't do this alone

At any point — setup, building, or launch — just ask your AI assistant to **guide you in
plain language**. It will:

- check what you already have installed,
- explain what each step does before doing it,
- install any missing tools **only when they're needed** (always asking first), and
- run the commands for you, with your approval.

If you ever feel lost, you can literally type *"what does this do?"* and it will explain.

## The easiest way to start

1. **Install one AI assistant** — [Claude Code](https://code.claude.com/docs/en/setup)
   (recommended), or Google Antigravity, or OpenAI Codex.
2. **Open it** and paste the prompt below.
3. **Answer its questions.** That's it — it handles the rest.

**Copy-paste starter prompt:**

> I want to use the website-builder skill suite (https://github.com/karero/website-builder)
> to create a new website. Please guide me step by step in plain language.
> First, check which required tools this computer already has.
> Explain every command before you run it, and install missing tools only when they're
> actually needed. Then install the website-builder skills. My websites live in one
> folder: check which folder you're open in and ask me whether that's it; if not, ask me
> which one it is (suggest Documents/Websites unless I already keep my projects somewhere
> else, or my Documents folder syncs to iCloud or OneDrive — then suggest a Websites
> folder in my home folder). Tell me when to restart or reopen you in that folder so the
> skills load, then start `new website` there. When the site has its own folder, tell me
> where it is on my computer (its full path).

You don't have to memorise any of this — the assistant runs the real commands for you. (If
you'd rather type the commands yourself, see [Manual install](#manual-install--technical-reference)
below.)

> 📦 **Prefer a download?** Grab the newest `website-builder.zip` from the
> [Releases page](https://github.com/karero/website-builder/releases/latest) — each release
> also tells you, in plain language, what's new.

## What you need

- an **AI coding assistant** — Claude Code, OpenAI Codex, or Google Antigravity
- a **GitHub account** (free) to store your site's code — it's yours, so we recommend
  protecting it with two-factor sign-in and a passkey
- a **computer** where you can run basic commands (macOS, Linux, or Windows)
- *optionally*, a **Cloudflare account** (free) when you're ready to publish

You **don't** need to install Node, git, the GitHub CLI, image tools, or anything else
upfront — the assistant checks for those and helps you install them only when the moment
comes.

> **On Windows?** The smoothest path is **WSL2** (Ubuntu) — it matches the Linux setup your
> site is built and published on, so everything just works. Your assistant can help you set
> it up; just ask. (Native Windows works too — see [SETUP.md](skills/new-website/templates/SETUP.md).)

## What happens next

Once you run `new website`, the assistant will:

1. Ask what kind of website you want to build.
2. Help shape its positioning and structure.
3. Create the website (Astro) with a mobile-first, responsive layout.
4. Draft your pages and content.
5. Add SEO metadata, schema markup, and accessibility checks.
6. Run tests and quality gates.
7. Help you prepare the site for launch.

---

## Manual install & technical reference

*If you already know your way around a terminal, here are the exact commands. Everything
below is also what the AI assistant runs on your behalf.*

This repository is the **single source of truth** for the website-builder skill suite — an
orchestrated set of agent skills that build a new website end-to-end (insights →
positioning → content → SEO/GEO → design → QA → review → launch), on the house stack
**Astro → GitHub → Cloudflare Pages**.

Developed and used with **Claude Code**. It also works with **Google Antigravity** and
**OpenAI Codex** — the skills are plain `SKILL.md` files, so any of the three can run the
same suite (see the per-tool notes below).

It replaces the previous arrangement where the suite lived in three hand-synced copies
(`~/.claude/skills/`, a de-personalized `_new-site/` package, and a hand-built zip), which
constantly drifted. Now there is one canonical copy here; the global install is **derived**
from it.

### Quick start — build your first site

You need [Claude Code](https://code.claude.com/docs/en/setup) (a paid Claude plan or a
Console/API account). Then, **three steps**:

```bash
# 1. Get the files, then cd into the folder — unzip the handoff zip, OR clone the repo:
unzip website-builder.zip && cd website-builder
#   from source instead:  git clone https://github.com/karero/website-builder.git && cd website-builder

# 2. From that folder, install the skills globally. Claude only loads skills from
#    ~/.claude/skills/, so this one command is the whole setup — no copying by hand.
./scripts/install.sh          # symlinks every skill into ~/.claude/skills/ (idempotent)
                              # macOS/Linux/WSL/Git-Bash. Or: make install
                              # A skill you pinned yourself — symlinked into another
                              # worktree of this repo — is kept and reported;
                              # ./scripts/install.sh --force relinks those too.
```

```
# 3. Restart Claude Code so it discovers the new skills, opening it in your websites
#    folder — Documents/Websites, or wherever you keep your projects — and say:
       new website
```

The scaffold makes a new folder for the site inside the one you opened, so that folder
doesn't need to be empty. The `new-website` orchestrator takes over from there: it runs the stack-decision
interview, scaffolds a git-first repo (Astro overlay + test suite + permission
allowlist), then sequences the sibling skills through **positioning → content → SEO/GEO
→ design → QA → review → launch**. It also walks you through the one-time build tools
(Node, git, `gh`, `wrangler`, image tools) the first time you actually build.

> **Updating later:** git is the version — tagged [releases](https://github.com/karero/website-builder/releases)
> mark the human-readable milestones on top (see *Releases & versioning* below).
> Skills are changed only in this repo (branch → edit → review → merge; never edit
> `~/.claude/skills/` directly, those are symlinks into the repo). If you cloned,
> `git pull` therefore updates every installed skill at once — nothing to re-install;
> to undo an update, `git revert` is equally live. From a zip, re-run
> `./scripts/install.sh` in a newer unzipped copy.
>
> Sites already scaffolded by `new-website` hold frozen **copies** of the skills and
> don't update with the suite. Each carries a `SUITE-VERSION` stamp recording the suite
> commit it was scaffolded from; `make whats-new PROJECT=<site-dir>` (needs the git
> clone) lists which of its bundled skills changed upstream since, and
> `./scripts/whats-new.sh --refresh <site-dir>` re-copies exactly those and re-stamps —
> note it **overwrites local edits** to those copies (it refuses while the site has
> uncommitted skill changes, so an overwrite stays recoverable via the site's git
> history). A skill deliberately forked for one site (e.g. localized copy) can be
> pinned: list its name in `<skills_dir>/REFRESH-KEEP` (one per line, `#` comments)
> and `--refresh` will never touch it — reports mark it "(pinned)". Plain
> `make whats-new` shows the suite's recent skill changes.
> Frozen template files (`tests/*` incl. `_helpers.ts`, plus `CONTENT_GUIDE.md`,
> `AGENTS.md`, `PUBLISHING.md`, `SETUP.md`, `playwright.config.ts`,
> `functions/_middleware.ts`, `.github/workflows/ci.yml`,
> `scripts/anchor-ids.mjs`, `scripts/check_external_links.sh`,
> `scripts/check_internal_links.sh`, `scripts/run_og.mjs`, `tsconfig.json`,
> `public/_headers`, `scripts/ship.sh`, `scripts/build-marker.mjs`,
> `scripts/set_pdf_title.py`, `scripts/hooks/pre-push`, `scripts/wire-hooks.mjs`,
> `scripts/verify.mjs`, `.nvmrc`, `.gitattributes`, `.claude/settings.json`, and
> `.claude/hooks/git-stand.mjs`) are **frozen one-time copies**, not vendored skills —
> `--refresh` never touches them. `whats-new` reports
> their upstream drift via the site's `tests/TESTS-VERSION` stamp (pre-existing sites
> fall back to the `SUITE-VERSION` baseline); merge those changes by hand, then
> `./scripts/whats-new.sh --stamp-tests <site>/tests`. A changed file the site has no copy
> of is marked **MISSING** and listed again at the end: copy it in, there is nothing to merge.
> `PUBLISHING.md` is the exception: an owner may keep a translation under another name, so it is
> never marked MISSING.
>
> **Windows:** run `./scripts/install.sh` from **Git Bash** or **WSL**, or copy
> `skills\*` into `%USERPROFILE%\.claude\skills\` with PowerShell
> (`Copy-Item -Recurse -Force .\skills\* "$env:USERPROFILE\.claude\skills\"`).

### Releases & versioning

Every version is a git tag + a [GitHub Release](https://github.com/karero/website-builder/releases)
whose notes are the human-readable "what's new", with the handoff zip attached as the
download asset. Underneath, updates stay commit-based (`git pull`, `SUITE-VERSION`
stamps, `whats-new`) — a release just names a milestone. Versions step by **0.01**
(0.1 → 0.11 → 0.12 → …). To cut one:

```bash
make smoke                        # clean-check + build + verify dist/website-builder.zip
git tag -a v0.11 -m "website-builder 0.11" && git push origin v0.11
gh release create v0.11 dist/website-builder.zip --title "0.11" --latest \
  --generate-notes                # or write the notes by hand
```

Zip users download the newest release from the Releases page; clone users keep using
`git pull` and don't need to care about tags.

### Using with Google Antigravity

This suite is **100% compatible** with Google Antigravity, which natively understands the
`SKILL.md` format and can orchestrate the whole pipeline (it can even run skills like
`customer-research` or `seo-audit` as asynchronous subagents). Install the skills into your
global config, then type `new website` in chat:

```bash
mkdir -p ~/.gemini/config/skills && cp -R skills/* ~/.gemini/config/skills/
```

See [docs/ANTIGRAVITY.md](docs/ANTIGRAVITY.md) for install options and the minor
permission differences, and [docs/ANTIGRAVITY-TEST.md](docs/ANTIGRAVITY-TEST.md) for a
step-by-step compatibility checklist.

### Using with OpenAI Codex

Codex runs the same suite through a thin adaptation layer — `skills/*` stays the single
source of truth. Install, restart Codex, and say `new website` (or `$new-website`):

```bash
./scripts/install-codex.sh        # symlinks skills/* into ~/.agents/skills/  (or: make install-codex)
```

See [docs/CODEX.md](docs/CODEX.md) for the clone/zip install, usage, and the differences
from Claude Code, and [docs/CODEX-TEST.md](docs/CODEX-TEST.md) for a step-by-step
compatibility checklist.

### Layout

```
skills/            the suite skills (canonical)
  new-website/     orchestrator + templates/ (Astro starter overlay + test suite) +
                   references/WEBSITE_ARCHITECTURE.md (hosting-tier 1/2/3 decision doc,
                   the companion to the orchestrator's stack-decision interview)
  website-*        siblings (run in order): positioning (the strategic spine — what you
                   offer, for whom, what category; worked out FIRST, enforced by
                   positioning.spec.ts), content-guide, seo-geo, design-system,
                   testimonials, qa, review; plus permissions (the allowlist) and
                   positioning-check (the optional one-screen diagnostic), which
                   sit outside the chain
  ai-seo, schema-markup, seo-audit, site-architecture, customer-research,
  copywriting, image, og-images, outgoing-link-audit, internal-link-audit,
  search-console-setup, business-listings-setup   (bundled deps)
  facts-check      (read-only, any live site on any stack: one approved facts list
                   in, every page in the sitemap compared with it, each differing
                   figure and retired phrase out; plus the positioning check, each
                   page against the term it owns per audience; runs weekly beside
                   the AI check)
  website-motion   (optional polish — count-ups + scroll reveals with the
                   reduced-motion contract; copied to every site, never runs unasked)
  website-story    (optional story layer — the home page as the customer's story:
                   STORY.md + an opt-in story.spec.ts; offered once after positioning,
                   copied to every site, never runs unasked)
  website-scorecard   (optional public scorecard — a dated section showing what the
                   site's own test gate checked, plus the owner's Lighthouse scores;
                   copied to every site, never runs unasked)
  website-team-setup   (on-demand: turns a one-owner repo into a team repo — invites,
                   settings, CI proof, push block, Cloudflare, rights in AGENTS.md;
                   copied to every site, runs only when a second person joins)
  independent-review, double-knuth, seo-reposition   (review gates + SEO
                   repositioning: cross-model PLAN/DIFF review via
                   independent-review/scripts/independent_review.sh, two-pass
                   consistency audit, trap-test → wedge → guard-tests method)
  astro-i18n-setup, keystatic-setup, website-contact-form   (opt-in setup skills — see below)
scripts/
  install.sh       symlink skills/* into ~/.claude/skills/ (Claude Code)
  install-codex.sh symlink skills/* into ~/.agents/skills/ (OpenAI Codex)
  package.sh       build dist/website-builder.zip for handoff (+ verify its contents)
  whats-new.sh     skill changes since a project was scaffolded (--refresh re-copies them)
  check_clean.sh   scan skills/ + root docs for names / contact info / credentials (make check)
  check_model_agnostic.sh   keep independent-review free of concrete model names (make check)
  check_template_coverage.sh  every astro template file is bucketed for drift tracking (make check)
  check_skill_budgets.sh    per-skill size budgets: description hard limit + line budget (make check)
  check_cdpath_safe.sh      an exported CDPATH changes no script's behaviour (make check)
  check_pipefail_pipes.sh   no pipe into head / grep -q / … under pipefail (make check)
  list_shell_scripts.sh     every shell script in the suite, found by shebang (the two guards above use it)
  test_clean_denylist.sh    the private-name check also runs in a linked worktree, which has no copy of the name list, and CI's masked mode prints no scanned text (make check)
  test_install_pin.sh       installers keep a pinned skill instead of clobbering it (make check)
  test_whats_new_removed_skill.sh  whats-new marks a bundled skill the suite removed, names the two ways out, and reads as before otherwise (make check)
  test_git_stand_hook.sh    the site template's Claude Code sync hook reports news, failures and retries correctly (make check)
  test_package_leak.sh      package.sh's leak check still fires on a leak past a pipe buffer (make check)
  test_pre_push_hook.sh     the site pre-push hook gates, skips and blocks the right pushes, and is wired only at a repo's root, by a line that holds no shell syntax (make check)
  test_verify.sh            the site's verify script reinstalls only when package.json or the lockfile changed, and stops at the first red step (make check)
  test_whats_new.sh         whats-new marks a frozen template file the site lacks as MISSING, and shows and checks the same site path for every tracked file with a fixed one (all but PUBLISHING.md) (make check)
  test_mktemp_guard.sh      each script it lists that builds a throwaway folder stops with an error, and leaves the folder it ran from alone, when mktemp fails; a new script that calls mktemp must be listed or exempted in it (make check)
  check_lf_checkout.sh      every text file checks out LF, even where Git converts to CRLF (make check)
docs/          (all of these ship in the zip; docs/reviews/ and docs/local/ do not)
  GETTING-STARTED.md   the gentle version — start here if the suite is new to you
  UPGRADING.md     upgrading a built site's Astro version (whats-new.sh points here)
  ANTIGRAVITY.md   using the suite with Google Antigravity
  CODEX.md         using the suite with OpenAI Codex
  ANTIGRAVITY-TEST.md  testing the suite itself with Antigravity
  CODEX-TEST.md    testing the suite itself with Codex
  DECISIONS_PENDING.md  maintainer-internal: open questions on the toolkit itself
  PROCESS-DIAGRAM.html  how the suite builds a site (SEO / GEO / EEAT)
  PROGRESS-TRACKER.html progress-tracker mockup
```

### Opt-in and on-demand setup skills

Four skills are **not run** by the default build — the orchestrator copies the first three
into a site only when the decision interview calls for them; the fourth travels with every
site (like `website-motion`) but runs only when a team forms:

- **`astro-i18n-setup`** — turnkey multi-language: Astro i18n routing (clean default locale
  + prefixed others), self-referencing hreflang + `x-default`, sitemap alternates, a language
  switcher, and per-locale test harness. Use it for a **two-language launch**, or for a
  **phased rollout** where the primary language ships first and a secondary prefixed locale is
  added later while default URLs stay unchanged. (The costly retrofit is moving the default
  locale off `/`; adding a secondary locale is additive.) Triggered by interview Q4.
- **`keystatic-setup`** — adds **Keystatic**, a git-based CMS (by the Keystone team), so a
  non-technical person edits content through a UI while the data stays as Markdown in the
  repo. Wires **local mode** by default (edit via the dev server, commit to git) and
  documents the optional upgrade to **GitHub mode** for in-browser editing (commits straight
  to the repo, no dev server). Run at scaffold time when interview Q3 = *a non-technical
  person edits content*; don't install speculatively.
- **`website-contact-form`** — our suggestion for a **contact form**: the visitor writes a
  message, presses a button, and their own email program opens with the message
  to the owner, ready to send. No server, no account, no setting and no company in between,
  so it works on any host and the privacy page needs nothing new. Adds a form component
  with its texts in English and German, one small script of the site's own (so a strict
  Content-Security-Policy holds) and a test of the link the button opens. The owner's
  address always shows under the form, for visitors without a mail program set up. Run
  when interview Q2 = *a contact form*, or later when the owner asks for one.
- **`website-team-setup`** — turns a one-person repo into one several people and several
  AI assistants (Codex in the browser or locally, Claude Code) can work on at once: invites
  collaborators, sets "Update branch" + auto-delete of merged branches, **proves** the CI
  workflow really starts on its own, blocks direct pushes to `main` (ruleset, or the
  shipped pre-push hook on a private free-plan repo), connects Cloudflare Pages to GitHub
  without the known traps, and sets the collaborators' rights level and who may publish
  live in `AGENTS.md`. Every scaffold already ships the `AGENTS.md` working rules (fetch
  first, pull request instead of a push, never invent facts, the new-page checklist) — this
  skill adds only what a team needs. Run once, when the second person joins.

A site with one language, a developer-edited repo, no contact form and a single owner runs
none of them.
Every scaffold does get the `AGENTS.md` + `CLAUDE.md` working rules, so the day a team
forms, `website-team-setup` only adds what a team needs.

Four more skills are optional in a different way: `website-motion`, `website-story`,
`website-scorecard` and `website-positioning-check` are **copied into every site** so the
recipient can use them later, but **never run unless asked** (`website-story` is offered
once, after positioning, with a plain-language explanation; the other three only on
request).

### Use it locally

```bash
make install         # symlink every skill into ~/.claude/skills/  (Claude Code, idempotent)
make install-codex   # symlink every skill into ~/.agents/skills/   (OpenAI Codex)
```

Edit a skill once, here, and the change is live everywhere (the global location is a
symlink, not a copy). Restart your session to pick up new/renamed skills.

### Hand it off

```bash
make package     # → dist/website-builder.zip  (runs `make check` first)
```

A recipient unzips it and runs `scripts/install.sh` (Claude Code),
`scripts/install-codex.sh` (Codex), or copies `skills/*` into their tool's skills root
(Antigravity → `~/.gemini/config/skills/`). The repo is the thing you share — by clone or by zip.

### Stay generic (no names, no secrets)

The suite is a handoff artifact, so it must carry **no personal names, contact info, or
credentials**.

```bash
make check       # PII/secrets + model-agnostic + template coverage + per-skill size budgets
```

`scripts/check_clean.sh` runs a denylist (owner / sites / org / home paths) plus generic
catches (any real email, credential/token formats, secret-looking assignments). The
denylist is a gitignored local file. CI gets it from the `CLEAN_DENYLIST` repository
secret, which `make push-denylist` sets from the local list, base64-encoded. Run it after
every change to the list: once you have pushed from a checkout, `make check` there fails
until the names are pushed again (it cannot see a push of another copy of the list from
elsewhere). The logs are public, so CI prints no scanned text, only which checks failed
and how many lines they found; run the check locally to see them. A pull request from a fork or from Dependabot gets no
secrets, so it skips the name check with a warning, as does a fork of the repo;
anywhere else a missing secret, or one with no names, fails the job.
The script runs in CI on every pull request and every push to `main`
(`.github/workflows/clean.yml`) and is a prerequisite of `make package`: in a checkout
that has the list, a listed name in a file the script scans stops the build, unless the
file is gitignored or the match is this repo's own `karero/website-builder` reference. The name check also covers `scripts/`,
since those files ship in the zip; the generic catches leave `scripts/` out, because its
files define their patterns. The name check skips only `LICENSE`, which carries the
owner's name. A genuine false positive is fixed by tightening a pattern in the script —
never by loosening it. The same `make check` (and the same CI workflow) also keeps
`independent-review` free of concrete model names outside its setup guide
(`scripts/check_model_agnostic.sh`) and holds every skill to its size budgets
(`scripts/check_skill_budgets.sh`).

### Merging stacked PRs

A PR whose base is **another feature branch** (not `main`) is *stacked* — e.g. a docs PR
based on the feature PR it documents. Stacks are fine, but the merge order is a trap:

> **What can go wrong:** if you merge the **base** PR into `main` first, and then merge the
> **child** PR into that base branch, the child's content lands in a branch that has already
> been folded into `main` — so it **never reaches `main`**, even though GitHub marks the child
> "Merged". GitHub only auto-retargets a child to `main` if the child is still **open** when
> its base merges; merging both at nearly the same time loses that window.

Merge a stack with one of these orders, never both halves at once:

1. **Up the stack (simplest):** merge the **child into its base branch** first, then merge the
   **base PR (now containing both) into `main`**. One PR reaches `main`; nothing is stranded.
2. **Retarget:** merge the **base PR into `main`**, then **retarget the child's base to `main`**
   (GitHub usually does this automatically for an open child), confirm the child's diff vs
   `main` is what you expect, and merge it.

**Always verify after merging — trust the tree, not the badge:**

```bash
git fetch origin && git ls-tree -r --name-only origin/main -- <a file the PR added>
```

If an expected file is missing from `origin/main`, the merge stranded it; re-land the work in
a fresh PR based on current `main` (rebase the branch onto `origin/main`, open a new PR).

## License & credits

MIT — see [LICENSE](LICENSE). Seven bundled skills (`ai-seo`, `seo-audit`,
`schema-markup`, `site-architecture`, `copywriting`, `customer-research`, `image`) are
derived from [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills)
(MIT, © 2025 Corey Haines); their notice is in
[THIRD-PARTY-LICENSES.md](THIRD-PARTY-LICENSES.md). Everything else is original to this
project. Two skills follow published frameworks in this project's own words and bundle no
third-party text: `website-positioning` uses April Dunford's positioning components
([*Obviously Awesome*](https://www.aprildunford.com/books)) and `website-story` is inspired
by Donald Miller's StoryBrand framework
([*Building a StoryBrand 2.0*](https://storybrand.com/building-a-storybrand-book-new/));
StoryBrand is a trademark of its owner and neither author endorses this project.
