# Croftweaver

[![Latest release](https://img.shields.io/github/v/release/karero/croftweaver?label=latest%20release&color=2ea44f)](https://github.com/karero/croftweaver/releases/latest)

**Build for search and AI.**

Croftweaver is a free, open-source suite of website skills: instructions your AI coding
assistant follows to build and test a site you own. Build or rebuild your site with your
assistant, so people can find it on Google and in AI answers. From a short brief it makes a
complete website — content, mobile-first responsive design, SEO, accessibility checks, schema
markup, tests, and launch support — on Astro → GitHub → Cloudflare Pages, and its test suites
check every change by default. After launch, your Search Console data and a weekly check of
which AI assistants name your site point to the next edit for SEO and GEO (how your site shows
up in AI answers). Developed and used with **Claude Code**; the install guides also cover
**OpenAI Codex** and **Google Antigravity**, and both have been tested from start to finish on
one site.

**Already have a website?** Part of Croftweaver works on a site that is already live, on any
stack, without a rebuild: the checks and measurements. They are Search Console insights, the
weekly AI check, the SEO audit, the positioning check, and the facts check. Three limits:
the ready-made test suite and the two link audits need the Croftweaver starter, the facts
check does not run a page's JavaScript, and there is no automatic import of an existing site
yet. See [Croftweaver for established sites](https://croftweaver.com/established-sites).

**Who maintains it.** Croftweaver is maintained by Daniel Melter (Munich). It grew out of
GenAI Wednesday Munich. The [LICENSE](LICENSE) file names the same person as copyright
holder, and the [imprint](https://croftweaver.com/imprint) names the company that operates
the website croftweaver.com.

> **Formerly website-builder.** Same project, new name. GitHub redirects old repository links
> and existing clones here. To point a clone at the new address, run
> `git remote set-url origin https://github.com/karero/croftweaver.git`.

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
   (recommended), or Google Antigravity, or OpenAI Codex. Croftweaver is developed and used
   with Claude Code; the other two have been tested from start to finish on one site.
2. **Open it** and paste the prompt below.
3. **Answer its questions.** That's it — it handles the rest.

**Copy-paste starter prompt:**

<!-- This prompt is also in docs/GETTING-STARTED.md. If you change one copy, change the other to match. -->

> I want to use the Croftweaver skill suite (https://github.com/karero/croftweaver)
> to create a new website. Please guide me step by step in plain language.
> First, check which required tools this computer already has.
> Explain every command before you run it, and install missing tools only when they're
> actually needed. My websites live in one folder: check which folder you're open in and
> ask me whether that's it; if not, ask me which one it is (suggest Documents/Websites
> unless I already keep my projects somewhere else, or my Documents folder syncs to iCloud
> or OneDrive — then suggest a Websites folder in my home folder). Put the downloaded
> Croftweaver files in a folder of their own and leave them there: for example a
> folder called croftweaver in my home folder, not Downloads and not my websites
> folder. Then install the Croftweaver skills. Tell me when to restart or reopen you
> so the skills load — in my websites folder — then start `new website` there. When the
> site has its own folder, tell me where it is on my computer (its full path).

You don't have to memorise any of this — the assistant runs the real commands for you. (If
you'd rather type the commands yourself, see [Manual install](#manual-install--technical-reference)
below.)

> 📦 **Prefer a download?** Grab the newest `croftweaver.zip` from the
> [Releases page](https://github.com/karero/croftweaver/releases/latest) — each release
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

This repository is the **single source of truth** for the Croftweaver skill suite — an
orchestrated set of agent skills that build a new website end-to-end (insights →
positioning → content → SEO/GEO → design → QA → review → launch), on the house stack
**Astro → GitHub → Cloudflare Pages**.

Developed and used with **Claude Code**. The skills are plain `SKILL.md` files, and the
install guides also cover **Google Antigravity** and **OpenAI Codex**; the suite has been
tested from start to finish with each on one site (see the per-tool notes below).

It replaces the previous arrangement where the suite lived in three hand-synced copies
(`~/.claude/skills/`, a de-personalized `_new-site/` package, and a hand-built zip), which
constantly drifted. Now there is one canonical copy here; the global install is **derived**
from it.

### Quick start — build your first site

You need [Claude Code](https://code.claude.com/docs/en/setup) (a paid Claude plan or a
Console/API account).

**The short way.** With [Node](https://nodejs.org) 22.12 or newer, one command installs the
skills. It runs in any terminal, on Windows too:

```bash
npm create croftweaver
```

It copies the skills of the latest release into `~/.claude/skills/` and tells you the next
step, which is step 3 below. To update, run it again. For Codex add `-- --codex`, for
Antigravity `-- --antigravity`.

**As a Claude Code plugin**, from release 0.32 on. Claude Code installs the suite itself:
no Node, no script, no folder to keep.

```bash
claude plugin marketplace add https://github.com/karero/croftweaver.git
claude plugin install croftweaver@croftweaver
```

(The address is written out in full so that nothing needs a GitHub key.)

Then go to step 3. As a plugin the skills carry its name in front
(`/croftweaver:new-website`). You stay on the release you installed until you run
`claude plugin update croftweaver@croftweaver`, or turn on auto-update for the marketplace
under `/plugin`; what lands on main between releases does not reach you. Use one route:
with the plugin and a copy in `~/.claude/skills/` (from `npm create croftweaver` or
`install.sh`), every skill is listed twice. The same holds in a site built with the suite,
for the skills the site carries.

**As a Codex plugin**, also from release 0.32 on. The same repository is a Codex plugin
marketplace:

```bash
codex plugin marketplace add https://github.com/karero/croftweaver.git
codex plugin add croftweaver@croftweaver
```

(Or, after the first line, type `/plugins` inside Codex and pick Croftweaver there.) Start
a new Codex session in your websites folder and say `new website`. The skills carry the
plugin's name in front (`$croftweaver:new-website`). Like the Claude Code plugin, it installs
releases only; `codex plugin marketplace upgrade` brings you the newest one. Use one route
here too: the plugin and a copy in `~/.agents/skills/` list every skill twice. The same holds
in a site built with the suite, for the skills the site carries in its `.agents/skills/`.

**With the `skills` command** ([skills.sh](https://skills.sh)), for Claude Code, Codex,
Antigravity and other assistants:

```bash
npx skills add karero/croftweaver --skill '*' -g
```

It asks which assistants to install for. Take all the skills (`--skill '*'`): `new-website`
copies its sibling skills into each new site, so a site built from a partial install is
missing some. This route installs the newest state of `main`, not a release, and records no
version, so a site built from it is stamped `suite_commit: unknown`. To update, run
`npx skills update`. skills.sh lists the suite at https://www.skills.sh/karero/croftweaver and
counts the installs made with this command; its page under the old name,
`karero/website-builder`, forwards there (seen on 2026-10-14).

**By hand**, in three steps:

```bash
# 1. Get the files, then cd into the folder — unzip the handoff zip, OR clone the repo.
#    Do it in a place of its own, not in your websites folder or Downloads: step 2 links
#    your skills to this folder, so it has to stay where it is.
unzip croftweaver.zip -d croftweaver && cd croftweaver
#   from source instead:  git clone https://github.com/karero/croftweaver.git && cd croftweaver

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

> **Updating later:** git is the version — tagged [releases](https://github.com/karero/croftweaver/releases)
> mark the human-readable milestones on top (see *Releases & versioning* below).
> Skills are changed only in this repo (branch → edit → review → merge; never edit
> `~/.claude/skills/` directly, those are symlinks into the repo). If you cloned,
> `git pull` therefore updates every installed skill at once — nothing to re-install;
> to undo an update, `git revert` is equally live. From a zip, re-run
> `./scripts/install.sh` in a newer unzipped copy. After `npm create croftweaver` the
> installed skills are copies, not symlinks: run the command again, and it replaces them
> with the latest release. A site scaffolded from those copies is stamped
> `suite_commit: unknown`, as one scaffolded from a zip is, so `make whats-new` has no
> baseline for it.
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
>
> One folder never reaches a site: `website-brand-kit/scripts/tests`, the toolkit's own
> test suite. The scaffold and `--refresh` both leave it out, and a change inside it alone
> is not reported as an update.
>
> Frozen template files (`tests/*` incl. `_helpers.ts`, plus `CONTENT_GUIDE.md`,
> `AGENTS.md`, `PUBLISHING.md`, `SETUP.md`, `playwright.config.ts`,
> `functions/_middleware.ts`, `functions/go/email.ts`, `.github/workflows/ci.yml`,
> `scripts/anchor-ids.mjs`, `scripts/check_external_links.sh`,
> `scripts/check_internal_links.sh`, `scripts/run_og.mjs`, `tsconfig.json`,
> `public/_headers`, `scripts/ship.sh`, `scripts/build-marker.mjs`,
> `scripts/set_pdf_title.py`, `scripts/hooks/pre-push`, `scripts/wire-hooks.mjs`,
> `scripts/verify.mjs`, `.nvmrc`, `.gitattributes`, `.claude/settings.json`, and
> `.claude/hooks/git-stand.mjs`) are **frozen one-time copies**, not vendored skills —
> `--refresh` never touches them. `whats-new` reports
> their upstream drift via the site's `tests/TESTS-VERSION` stamp (pre-existing sites
> fall back to the `SUITE-VERSION` baseline); merge those changes by hand, then
> `./scripts/whats-new.sh --stamp-tests <site-dir>/tests`. A changed file the site has no copy
> of is marked **MISSING** and listed again at the end: copy it in, there is nothing to merge.
> `PUBLISHING.md` is the exception: an owner may keep a translation under another name, so it is
> never marked MISSING.
>
> **Windows:** `npm create croftweaver` (above) runs in any terminal. By hand, run
> `./scripts/install.sh` from **Git Bash** or **WSL**, or copy
> `skills\*` into `%USERPROFILE%\.claude\skills\` with PowerShell
> (`Copy-Item -Recurse -Force .\skills\* "$env:USERPROFILE\.claude\skills\"`).

### Releases & versioning

Every version is a git tag + a [GitHub Release](https://github.com/karero/croftweaver/releases)
whose notes are the human-readable "what's new", with the handoff zip attached as the
download asset and a `SHA256SUMS` file beside it. Underneath, updates stay commit-based
(`git pull`, `SUITE-VERSION` stamps, `whats-new`) — a release just names a milestone.
Versions step by **0.01** (0.1 → 0.11 → 0.12 → …). To cut one:

```bash
# First, in a pull request of its own: the release's number in .claude-plugin/plugin.json
# ("version": "0.11.0"). A changed version is what tells Claude Code there is an update.
make smoke                        # clean-check + build + verify dist/croftweaver.zip,
                                  # then write its checksum to dist/SHA256SUMS
# The tag takes its name from that number (0.11.0 gives v0.11), so the two cannot differ.
# A number that was not raised names the last release's tag, and git refuses to make it.
v="v$(node -p 'require("./.claude-plugin/plugin.json").version.replace(/\.0$/, "")')"
git tag -a "$v" -m "Croftweaver ${v#v}" && git push origin "$v"
gh release create "$v" dist/croftweaver.zip dist/SHA256SUMS --title "${v#v}" --latest \
  --generate-notes                # or write the notes by hand
# Both files go up in this one command: a release marked immutable takes no files later.
# The plugin is installed from the branch `stable`. The release-tag workflow, started by
# the tag, checks the number against it and moves `stable` to the release. A red run means
# plugin users are still on the release before. If the step that moves the branch failed,
# move it yourself:  git push origin "$v^{commit}:refs/heads/stable"
# If the check of the number failed, the tag was not made as above: leave `stable` where
# it is, and plugin users get the next release.

# After every release: `npm create croftweaver` refuses a release whose zip does not match
# its SHA256SUMS, and a published release takes no files later. This runs that installer
# on the release now live, into a throwaway folder; it must print "The installer takes the
# latest release". If it does not, read why. A download or network error: run it again. A
# refusal of the release itself (no SHA256SUMS, a mismatch, a zip it cannot unpack): every
# install fails the same way until a fixed release is out.
node packages/create-croftweaver/check-release.mjs
# Only when packages/create-croftweaver changed, once the line above passes: publish the
# installer. npm runs the same check before publishing, except with --ignore-scripts or
# ignore-scripts=true in an .npmrc: hence running it by hand first.
(cd packages/create-croftweaver && npm run prepublishOnly && npm publish)
```

Zip users download the newest release from the Releases page; clone users keep using
`git pull` and don't need to care about tags. To check a downloaded zip, put `SHA256SUMS`
from the same release beside it and run `shasum -a 256 -c SHA256SUMS` (macOS) or
`sha256sum -c SHA256SUMS` (Linux); it prints `croftweaver.zip: OK`. On Windows, run
`(Get-FileHash croftweaver.zip -Algorithm SHA256).Hash` in PowerShell and compare the
hash it prints with the one in `SHA256SUMS` (it prints capitals, the file small letters).

### Using with Google Antigravity

The skills go into Google Antigravity unchanged, as plain `SKILL.md` files. The suite has been
tested from start to finish with Antigravity on one site. Install the skills into your global
config, then type `new website` in chat:

```bash
mkdir -p ~/.gemini/config/skills && cp -R skills/* ~/.gemini/config/skills/
```

See [docs/ANTIGRAVITY.md](docs/ANTIGRAVITY.md) for install options and the minor
permission differences, and [docs/ANTIGRAVITY-TEST.md](docs/ANTIGRAVITY-TEST.md) for a
step-by-step compatibility checklist.

### Using with OpenAI Codex

Codex reads the same skills through a thin adaptation layer — `skills/*` stays the single
source of truth. The suite has been tested from start to finish with Codex on one site.
Install, restart Codex, and say `new website` (or `$new-website`):

```bash
./scripts/install-codex.sh        # symlinks skills/* into ~/.agents/skills/  (or: make install-codex)
```

Or install it as a Codex plugin (from release 0.32 on; see *Quick start* above).
`.agents/plugins/marketplace.json` is Codex's marketplace entry; Codex reads the plugin's
name and number from the same `.claude-plugin/plugin.json` as Claude Code, so a release
raises the number once for both.

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
  wordpress-inspector (read-only, any live WordPress site: counts each content type the
                   site's REST API lists (WordPress's internal ones left out, media as
                   one number), the sitemap's addresses and where the two
                   disagree, shows signs of a page builder and forms, and says when
                   the count is incomplete; the first step before moving a site, and
                   the basis for an estimate. From the owner's decisions it writes
                   the new site's redirects. After the move it asks the new site for
                   each address the count listed and names those that are missing,
                   were sent to the home page, or end where the decisions do not say)
  website-motion   (optional polish — count-ups + scroll reveals with the
                   reduced-motion contract; copied to every site, never runs unasked)
  website-story    (optional story layer — the home page as the customer's story:
                   STORY.md + an opt-in story.spec.ts; offered once after positioning,
                   copied to every site, never runs unasked)
  website-scorecard   (optional public scorecard — a dated section showing what the
                   site's own test gate checked, plus the owner's Lighthouse scores;
                   copied to every site, never runs unasked)
  website-brand-kit   (optional colours and logo — three prompts for the owner's own
                   design tool, then a checked install: every text colour on every
                   background in both themes, a safety check of the SVG, the seven icon files;
                   asked about once after positioning, copied to every site, never
                   runs unasked)
  website-tagline  (optional line under the logo — starts from the purpose, shows
                   the owner six to eight lines, the owner picks one: TAGLINE.md +
                   SITE.tagline, and an opt-in tagline.spec.ts for a site that shows
                   the line; the skill is copied to every site, never runs unasked)
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
  package.sh       build dist/croftweaver.zip for handoff (+ verify its contents)
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
  test_package_leak.sh      package.sh's leak check still fires on a leak past a pipe buffer, and fails the build when a maintainer tracker (docs/BUGLOG.md, docs/DECISIONS_PENDING.md) is in the zip (make check)
  test_pre_push_hook.sh     the site pre-push hook gates, skips and blocks the right pushes, and is wired only at a repo's root, by a line that holds no shell syntax (make check)
  test_verify.sh            the site's verify script reinstalls only when package.json or the lockfile changed, and stops at the first red step (make check)
  test_whats_new.sh         whats-new marks a frozen template file the site lacks as MISSING, and shows and checks the same site path for every tracked file with a fixed one (all but PUBLISHING.md) (make check)
  test_mktemp_guard.sh      each script it lists that builds a throwaway folder stops with an error, and leaves the folder it ran from alone, when mktemp fails; a new script that calls mktemp must be listed or exempted in it (make check)
  check_lf_checkout.sh      every text file checks out LF, even where Git converts to CRLF (make check)
docs/          (these ship in the zip, except the two marked repo only; docs/reviews/ and docs/local/ do not ship either)
  GETTING-STARTED.md   the gentle version — start here if the suite is new to you
  UPGRADING.md     upgrading a built site's Astro version (whats-new.sh points here)
  CLOUDFLARE-CHECKLIST.md  the Cloudflare settings a site relies on (HTTPS, privacy, search and AI visibility), each with its dashboard path, and an outside check where one exists
  ANTIGRAVITY.md   using the suite with Google Antigravity
  CODEX.md         using the suite with OpenAI Codex
  ANTIGRAVITY-TEST.md  testing the suite itself with Antigravity
  CODEX-TEST.md    testing the suite itself with Codex
  DECISIONS_PENDING.md  repo only, maintainer-internal: open questions on the toolkit itself
  BUGLOG.md             repo only, maintainer-internal: small bugs and follow-ups kept for a later sweep (a few shipped comments name it; read it in the repo)
  PAGES-OR-WORKERS.md   for the kit's maintainer: what moving the kit from Cloudflare Pages to Workers would change (no site has to act on it)
  PROCESS-DIAGRAM.html  how the suite builds a site (SEO / GEO / EEAT)
  PROGRESS-TRACKER.html progress-tracker mockup
.claude-plugin/  (repo only) plugin.json and marketplace.json: the suite as a Claude Code plugin, installed
                   from the branch `stable`, which the release-tag workflow moves to each release (make test-plugin)
.agents/plugins/ (repo only) marketplace.json: the same plugin for Codex, from the same branch; Codex reads
                   its name and number from .claude-plugin/plugin.json (make test-plugin)
packages/      (repo only: the zip does not hold it)
  create-croftweaver   the `npm create croftweaver` installer: downloads the latest release and copies its skills
                   into the assistant's skills folder. The maintainer publishes it to npm (make test-create)
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

Six more skills are optional in a different way: `website-motion`, `website-story`,
`website-brand-kit`, `website-scorecard`, `website-tagline` and `website-positioning-check`
are **copied into every site** so the recipient can use them later, but **never run unless
asked** (`website-story` is offered once, after positioning, with a plain-language explanation;
`website-brand-kit` is asked about once, right after it, with one plain question; the
other four only on request).

### Use it locally

```bash
make install         # symlink every skill into ~/.claude/skills/  (Claude Code, idempotent)
make install-codex   # symlink every skill into ~/.agents/skills/   (OpenAI Codex)
```

Edit a skill once, here, and the change is live everywhere (the global location is a
symlink, not a copy). Restart your session to pick up new/renamed skills.

### Hand it off

```bash
make package     # → dist/croftweaver.zip  (runs `make check` first)
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
file is gitignored or the match is this repo's own `karero/croftweaver` reference (or its former
name, `karero/website-builder`). The name check also covers `scripts/`,
since those files ship in the zip; the generic catches leave `scripts/` out, because its
files define their patterns. In the repo both also cover `packages/`, which the zip does
not hold. The name check skips only `LICENSE`, which carries the owner's name, and the
installer's copy of it (`packages/create-croftweaver/LICENSE`) while that copy is the same
file byte for byte. A genuine false positive is fixed by tightening a pattern in the
script — never by loosening it. The same `make check` (and the same CI workflow) also keeps
`independent-review` free of the model names and tags the pattern in
`scripts/check_model_agnostic.sh` knows, outside its setup guide and its list of the models
the Melious seat may run, and holds every skill to its size budgets
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

If you built a site with Croftweaver, we would be glad of a link back to
[croftweaver.com/partner-assets](https://croftweaver.com/partner-assets), with the badge or as
plain text. It is a request, not a condition: the MIT license asks only that its notice stays
with copies of the software.
