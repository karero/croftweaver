# What the skills run on your computer

This page says what Croftweaver does on your computer and on the internet: which commands
its skills run, which services they talk to, what they write outside your site's folder,
where your keys are kept, and how a release is made. It was written by reading the scripts
and the skill files, not from memory.

**Checked on 2026-10-14, against `main` at commit `e038603`.** A later change can make a
line here wrong. Where something could not be checked, the line says so.

A skill is a set of written instructions for your AI assistant (Claude Code, Codex or
Antigravity). Some skills also bring small scripts. The assistant reads the instructions
and runs the commands; the skills cannot run anything by themselves.

## The short version

- **Nothing reports to the maintainer.** No skill, script or installer sends usage data,
  error reports or anything else to Croftweaver or its maintainer. See
  [Telemetry](#telemetry) for how this was checked, for the one optional step that reads
  croftweaver.com, and for two tools the site uses that do send anonymous usage data to
  their own makers.
- **Every outside service is yours.** Each network call goes to a service you sign up for,
  with your own key or sign-in (Google, Bing, GitHub, Cloudflare, and the AI services you
  choose), or it reads something public: web pages, packages, program downloads.
- **Writes outside your site's folder are few.** The main ones: the skills folder the
  installer fills, `~/.config/gsc-insights/` for the optional Search Console reports, one
  scheduled job on macOS if you ask for weekly tracking, and a log for the review tool.
  The full list is in [Writes outside your site's folder](#writes-outside-your-sites-folder).
- **In Claude Code, routine build commands run without asking**, because each site made
  with Claude Code gets a permission list (see
  [What runs without asking](#what-runs-without-asking)). That list also lets `node`,
  `npm run` and `git push` run without asking. It saves clicks; it is not a safety fence.
- **Releases carry no checksum file and no signature of our own.** GitHub shows a SHA-256
  for each download. See [Releases](#releases).

## What runs without asking

**Claude Code.** Every new site made with Claude Code gets `.claude/settings.json`
([template](../skills/new-website/templates/claude/settings.json)). The `website-permissions`
skill installs the same file into an existing site. It has three parts:

- **Runs without asking:** `npm install`, `npm ci`, `npm run …`, `npm test …`, `npm exec …`,
  `npx astro`, `npx keystatic`, `npx playwright`, `wrangler pages dev` and `wrangler whoami`
  (each plain or with `npx`),
  `astro`, `playwright`, `node …`, `bash scripts/check_external_links.sh`, most everyday git
  commands (`status`, `diff`, `log`, `show`, `add`, `commit`, `branch`, `checkout`, `switch`,
  `init`, `merge`, `restore`, `stash`, `remote`, `fetch`, `pull`, `rev-parse`, `push`),
  `gh auth status`, `gh repo view`, `gh repo create`, `gh pr view`, `gh pr list`, the image
  tools (`cwebp`, `dwebp`, `avifenc`, `magick`, `convert`, `oxipng`, `jpegoptim`, `svgo`,
  `exiftool`), file commands (`ls`, `cat`, `head`, `tail`, `wc`, `tree`, `find`, `grep`,
  `rg`, `mkdir`, `cp`, `mv`, `touch`, `echo`, `open`), and reading three documentation sites
  (docs.astro.build, developers.cloudflare.com, keystatic.com).
- **Blocked:** `rm -rf`, `git push --force` and `git push -f`, `git reset --hard`,
  `gh repo delete`, `wrangler delete` and `wrangler pages delete` (with or without `npx`).
  Claude Code's [permission documentation](https://code.claude.com/docs/en/permissions)
  says a block rule prevents the command; it does not ask. You run such a command yourself
  if you really mean it. (Some skill texts say these commands "still ask". This was read
  from the documentation, not tried in a live session.)
- **Everything else asks first**, as long as Claude Code is in its normal mode. If you
  switch Claude Code to a mode that approves everything, nothing asks.

What this list does and does not protect:

- `node …`, `npm run …` and `npm exec …` can run any program. So the list is a way to stop
  routine prompts, not a sandbox. Apart from the list, the site's `AGENTS.md` tells the
  assistant never to run `npm run ship` unasked and to merge a pull request only when you
  say so. Those are written rules for the assistant, not something Claude Code enforces.
- `git push` and `gh repo create` are allowed on purpose. `SETUP.md` in each site says to
  take them out of the list if you would rather confirm each push.
- The block rules match the command as written, from its start. `git push origin main
  --force` and `git push origin +main` do not begin with `git push --force`, so they fall
  under the `git push` rule and run without asking. So does `git push --delete`. (Read from
  the rules and from Claude Code's documented matching; not tried in a live session.)
- `find` with `-delete` or `-exec` still asks: Claude Code's documentation says a `find`
  rule cannot approve a `find` that deletes, writes or runs commands.

**Codex and Antigravity** do not read `.claude/settings.json`. They use their own approval
settings, which Croftweaver does not change.

**The starter prompt** in the README asks the assistant to explain every command before
it runs it, and to install a missing tool only when it is needed.

## What each skill runs

### Skills with no scripts and almost no commands

These are instructions only: `ai-seo`, `copywriting`, `customer-research`, `schema-markup`,
`site-architecture`, `website-design-system`, `seo-audit`, `search-console-setup` (you click
through Google's and Cloudflare's pages; the assistant drafts the values) and
`website-motion` (it copies one test file into the site).

Three more bring no scripts but name a few commands:

- `business-listings-setup` has the assistant request each profile address your site
  links to (Google, LinkedIn and the like), the way `outgoing-link-audit` does, to see
  whether it still works.
- `image` shows example commands for image tools (`cwebp`, `mogrify`, `jpegoptim`) and a
  `curl` that reads a page's image list. It may suggest an image service (Gemini, Flux,
  Ideogram, OpenAI) that you use with your own account and key.
- `website-permissions` copies `.claude/settings.json` and its hook into the site (see
  above).

### Skills that run the site's own build and tests

`website-content-guide`, `website-positioning`, `website-story`, `website-tagline`,
`website-testimonials`, `astro-i18n-setup`, `website-positioning-check`, `website-qa`,
`website-review`, `internal-link-audit`, `og-images`, `website-seo-geo`, `double-knuth`,
`website-contact-form` and `website-scorecard` run commands such as `npm run build`,
`npm test`, `npm run verify`, `npm run og`, `git status`, `git log` and `git diff` in the
site's folder. Some copy template files into the site. All of this stays in the site's
folder, apart from what npm and Playwright download (see [Network calls](#network-calls))
and a short-lived folder `website-scorecard` makes in your temp folder for the test report
and deletes again.

What the site's own scripts do (from `package.json` in the
[template](../skills/new-website/templates/astro/package.json)):

- `npm run build` builds the site with Astro, then two small scripts add anchor names and
  a `build.txt` with the commit id.
- `npm test` runs the Playwright tests against the built site on your computer.
- `npm run og` makes share images with a Python script (needs Pillow).
- `npm run verify` installs the exact packages if needed, then checks, builds and tests.
- `npm install` also runs `scripts/wire-hooks.mjs`. When the site is the top folder of its
  git repository, it points the repository's git hooks at `scripts/hooks`
  (`git config core.hooksPath scripts/hooks`, for this repository only). The pre-push hook
  then runs `npm run verify` before each push, except a push that only deletes a branch.
- `npm run ship` (two-stage sites) pushes `main` to the `production` branch on GitHub,
  which makes Cloudflare publish the live site, then reads the live `build.txt` until it
  shows the new commit. It refuses to run on a branch other than `main`, with unsaved
  changes, or when `production` has moved on its own, and it never force-pushes.

`website-contact-form` builds a `mailto:` link: the visitor's own mail program sends the
message. There is no form server.

### Skills with their own scripts

- **`new-website`** creates the site folder (in the folder you confirm), runs `git init`,
  `npm create astro@latest`, copies the templates and 26 skills into the site, and runs the
  build and tests. For Cloudflare it uses `npx wrangler pages project create` and
  `npx wrangler pages deploy` with a token you make, or `npx wrangler login`. Its
  `scripts/cloudflare-check.mjs` reads your site's public addresses to check the Cloudflare
  settings; it needs no token. It also sends requests that carry the names of AI crawlers
  (GPTBot, ClaudeBot and others) to your own domain, to see whether Cloudflare lets them in.
- **`website-team-setup`** uses `gh` to change GitHub settings once you ask for team
  setup: invite collaborators, edit repository settings, create and update branch rules,
  start a check run, and push and close a throwaway test branch. It runs these without a
  separate question for each; deleting a branch rule needs your go-ahead.
- **`keystatic-setup`** (only if you chose a content editor) installs `@keystatic/core` and
  `@keystatic/astro` with npm and runs `npx astro add react markdoc`.
- **`facts-check`** runs `facts_check.py`, which reads your site's public pages and its
  sitemap and compares facts across them. It edits nothing.
- **`wordpress-inspector`** runs `wp_inventory.py` and `check_move.py`, which read a
  WordPress site's public pages, its public `wp-json` data and its sitemaps. They need no
  sign-in.
- **`outgoing-link-audit`** runs `scripts/check_external_links.sh`, which builds the site
  if needed and then requests every outside link on it with `curl`.
- **`search-console-insights`** (optional) builds a Python environment in
  `~/.config/gsc-insights/venv` and installs `google-api-python-client`,
  `google-auth-oauthlib` and `requests` into it, after you say yes to connecting. Its
  scripts read your Search Console and Bing data, look up search results, and run the
  weekly AI check. `schedule_tracking.sh install` sets up a weekly run on macOS, and only
  on an explicit yes. Once per site per session it runs `schedule_tracking.sh status`, which
  only reads.
- **`seo-reposition`** uses `search-console-insights`' scripts (`serp_check.py` and the
  Search Console data) and may offer `independent-review`.
- **`independent-review`** is for people who change the toolkit or their site's code. It
  sends a plan or a code change to outside AI reviewers (see the next section). The skill
  asks before a repository's content goes to each service for the first time.
  `seo-reposition` and `website-review` offer it only with your OK. It is not copied into
  new sites.

### Tools the skills help you install

`SETUP.md` in each site lists the build tools: Node, git, the GitHub CLI, image tools
(through Homebrew or winget), `npm install -g wrangler` and `svgo`, `pip3 install Pillow`,
and `npx playwright install chromium`. The assistant walks you through them and installs a
tool only when it is needed. `website-seo-geo` may need `pip install pypdf`.

`independent-review`'s setup guide lists install commands for its reviewers, three of them
in the form `curl … | sh` from chatgpt.com, antigravity.google and ollama.com, next to
Homebrew and npm alternatives. Its setup wizard asks you to paste these yourself.

## Network calls

| Who | Used by | Key or sign-in | Reads or sends |
|---|---|---|---|
| GitHub | git (`fetch`, `pull`, `push`), `gh`, `npm run ship`, the sync hook | your git and `gh` sign-in | reads, and sends your site's code when pushing |
| GitHub release downloads | `npm create croftweaver` | none | reads `croftweaver.zip` from the newest release |
| npm registry | `npm install`, `npm ci`, `npx`, `npm create astro` | none | reads packages |
| Playwright's download servers | `npx playwright install chromium` | none | reads the test browser |
| Homebrew, winget, PyPI | installing the build tools, Pillow, pypdf and the Search Console libraries | none | reads programs |
| chatgpt.com, antigravity.google, ollama.com | the `curl … \| sh` install lines in `independent-review`'s setup guide, if you use them | none | reads the installers |
| croftweaver.com | `new-website`'s footer credit step, only if you say yes | none | reads the badge code from `/partner-assets` and the badge files |
| An image service you choose | `image`, if you use one | your own key | sends your image prompts |
| Cloudflare | `wrangler` (deploy, project create, deployment list) | an API token you make, or `wrangler login` | sends the built site |
| Google Search Console | `search-console-insights` (`gsc_query.py`, `search_report.py`, `insights.py`) | your own Google sign-in, scope `webmasters.readonly` | reads only; asks for clicks, impressions and positions |
| Bing Webmaster | `bing_query.py` | your `BING_API_KEY` | reads only |
| Serper or SerpApi | `serp_check.py` | your `SERPER_API_KEY` or `SERPAPI_KEY` | sends a keyword, country and language; reads search results |
| OpenRouter, or Gemini, OpenAI, Anthropic, Perplexity directly | the weekly AI check (`geo_check.py`) | your own key for each (`GEO_…_API_KEY`) | sends the questions you confirmed, one of which names your business; reads the answers |
| SerpApi (Google's AI answers) | `geo_check.py`, only if you switch it on | your `SERPAPI_KEY` | sends the same questions |
| Your own home page | `geo_check.py` | none | reads it, to notice when it changed |
| OpenAI (through the Codex app) | `independent-review` | your Codex sign-in | sends the plan or code change |
| ollama.com | `independent-review` | your `OLLAMA_API_KEY` or `ollama signin` | sends the plan or code change |
| melious.ai | `independent-review`, only when a model is named for it | your `MELIOUS_API_KEY` | sends the plan or code change |
| Google Antigravity | `independent-review`, only when you ask for it | your Antigravity sign-in | sends the plan or code change |
| Public web pages | `facts-check`, `wordpress-inspector`, `outgoing-link-audit`, `business-listings-setup`, `cloudflare-check.mjs` | none | reads only |
| Your analytics (Plausible), if you set it up | the built site, live version only | none | your visitors' page views go to the analytics address you set |

Some details:

- **The Search Console sign-in asks for read-only access.** The scripts ask Google only
  for the `webmasters.readonly` scope and use only its query and list calls.
- **The AI check** sends only your question texts, plus model, country and language.
  Whether an answer names your business is counted on your computer. When you use
  OpenRouter, the request names the app as "Croftweaver AI check" to OpenRouter.
- **The review tool and Codex.** Codex runs as an agent in your project folder with a
  read-only setting. It can read other files in that folder, and could send them along.
  Whether its sandbox blocks writes is not tested. The script's own header says so.
- **Crawler manners.** `facts-check` and `wp_inventory.py` follow `robots.txt` and say who
  they are in their user agent. `check_move.py` does not read `robots.txt`, because it
  checks your own new site. `check_external_links.sh` and `geo_check.py` send a browser's
  user agent.
- **The built site**, apart from the optional analytics script, loads no fonts, scripts
  or styles from other servers. Its security header (`public/_headers`) allows scripts only
  from the site itself and from the analytics address you set. Analytics run only on the
  live site, not on previews.

## Telemetry

Croftweaver sends nothing to its maintainer. This was checked in two passes:

- Every script, template and installer (`*.py`, `*.sh`, `*.mjs`, `*.js`, `*.ts`, `*.astro`,
  `*.json`, `*.yml`, `Makefile`, the pre-push hook) was searched for analytics and tracking
  terms (`telemetry`, `analytics`, `beacon`, `sentry`, `posthog`, `plausible`, `umami`,
  `gtag`, `mixpanel`, `segment`, `amplitude` and others) and for every network call
  (`curl`, `wget`, `fetch(`, `urllib`, `requests`, `http.client`, `https://`, `gh api`,
  `git push`).
- Every skill text and the plugin files (`*.md`, `.claude-plugin/`) were searched for
  `croftweaver.com`, the repository's GitHub account name, `telemetry`, `beacon` and
  wording that asks the assistant to report back.

What touches the maintainer's own places:

- `npm create croftweaver` reads the release zip from GitHub, and Claude Code reads the
  plugin from GitHub.
- After launch, `new-website` asks you once whether you want a "Built with Croftweaver"
  credit in your footer. Only if you say yes does the assistant read the badge code and
  files from croftweaver.com. The badge is then saved in your site, so your visitors load
  it from your site, not from croftweaver.com; the credit is a link to croftweaver.com.
- `croftweaver.com` and `github.com/karero/croftweaver` otherwise appear only as links.

Two tools the site uses collect anonymous usage data by default, for their own makers and
not for Croftweaver:

- **Astro** (the site builder) collects anonymous data about which commands run, its
  version and the setup ([Astro's telemetry page](https://astro.build/telemetry/)). Turn it
  off with `npx astro telemetry disable`.
- **Wrangler** (Cloudflare's tool) collects anonymous data about commands and deploys
  ([Wrangler's telemetry notes](https://github.com/cloudflare/workers-sdk/blob/main/packages/wrangler/telemetry.md)).
  Turn it off with `npx wrangler telemetry disable`.

Croftweaver does not switch either off for you. Your AI assistant is a separate product
with its own terms.

## Writes outside your site's folder

| Path | Written by | When | How to undo |
|---|---|---|---|
| `~/.claude/skills/<skill>` (Claude Code), `~/.agents/skills/<skill>` (Codex), `~/.gemini/config/skills/<skill>` (Antigravity) | `npm create croftweaver` copies the skills there; `scripts/install.sh` and `install-codex.sh` link them to the downloaded folder | when you install | delete those skill folders; there is no uninstall command |
| `~/.claude/skills/.croftweaver.json` (or the same in the other skills folders) | `npm create croftweaver` | when you install | delete it |
| `<skill>.pre-website-builder.bak` next to the skills | `scripts/install.sh` | when a folder with a skill's name was already there | rename it back |
| `skills-before-croftweaver-…` next to the skills folder | `npm create croftweaver` | when the skills folder held folders it did not recognise | move them back |
| `~/.config/gsc-insights/` (Python environment, `token.json`, `.env`, `history.csv`, `sites/`, `reports/`, `geo/`, `logs/`) | `search-console-insights` | when you connect Search Console or run the AI check | delete the folder |
| `~/Library/LaunchAgents/com.gsc-insights.<site>.plist` | `schedule_tracking.sh install` (macOS only) | when you say yes to weekly tracking | `schedule_tracking.sh remove <site>` (leaves the log and history behind) |
| `~/.local/state/independent-review/runs.tsv` | `independent-review` | each review (turn off with `REVIEW_LOG=off`) | delete it |
| a folder in your temp folder | `independent-review` | each review; holds the reviewers' answers, readable only by you | the skill tells the assistant to delete it at the end |
| `~/.gitconfig`: `fetch.prune true` | you or the assistant, from `SETUP.md` and `website-team-setup` | once per computer, when you set up git or a team | `git config --global --unset fetch.prune` |
| a short-lived folder in your temp folder | `website-scorecard` | each scorecard run | deleted at the end of the run |

Inside the site's own `.git` folder, the sync hook (`.claude/hooks/git-stand.mjs`, at
session start and again once the last sync is 2 hours old) keeps a small marker file,
`.git/claude-git-stand`. If `.git` cannot be written, the file goes to your temp folder
instead.

`git config core.hooksPath` is set for the site's repository only, never globally. No
script writes to the keychain, `crontab`, Windows Task Scheduler or `systemd`. On Linux
the weekly run is something you set up yourself; the skill says how.

`npm create croftweaver` also removes skills that an earlier run of it installed and that
the new release no longer has.

## Keys and passwords

| Key | Where it is kept |
|---|---|
| Google sign-in (OAuth client) | `~/.config/gsc-insights/client_secret.json`, which you download from Google |
| Google sign-in token | `~/.config/gsc-insights/token.json`, readable only by you (set by the script) |
| Bing, Serper, SerpApi and AI-check keys | environment variables, or `~/.config/gsc-insights/.env` |
| melious.ai key | `MELIOUS_API_KEY`, or `~/.config/reviewers/melious.env` (the setup guide says to make it readable only by you) |
| ollama.com key | `OLLAMA_API_KEY` |
| Codex, Antigravity, GitHub, Cloudflare sign-ins | each tool's own login |
| Cloudflare API token | an environment variable for the session; the guide asks for a narrow token that expires in about a week, and also names `.dev.vars` in the site (git ignores it), though whether Wrangler reads its sign-in token from that file was not checked |

All of these live outside the site's folder, except `.dev.vars`, which the site's
`.gitignore` excludes along with `.env`, `.env.*` and `.wrangler/`. The review tool passes
its keys to `curl` through standard input, not on the command line. The Bing script
removes the key from error messages before they reach a log; a test guards this.

Known gaps:

- `~/.config/gsc-insights/.env` is made readable only by you when `geo_check.py
  --prepare-env` adds lines to it. A file you create or edit by hand keeps whatever
  permissions it gets. `client_secret.json` is never tightened.
- If you run `gsc_query.py` from a site folder without `--client-secret`, it looks for
  `client_secret.json` in that folder. The site's `.gitignore` does not list
  `client_secret.json` or `token.json`, so a copy placed there could be committed.
  Keep them in `~/.config/gsc-insights/`.

## Releases

How a release is made (README, "Releases & versioning", and
[`.github/workflows/release-tag.yml`](../.github/workflows/release-tag.yml)):

1. A pull request raises the version in `.claude-plugin/plugin.json`.
2. `make smoke` runs the suite's checks (`make check`) and builds and checks
   `dist/croftweaver.zip`.
3. The maintainer tags the release (`v0.32`) and creates a GitHub release with the zip.
4. The tag starts a workflow that checks the version number and moves the branch `stable`
   to the release. The Claude Code plugin installs from `stable`.

What protects a download today:

- GitHub shows a SHA-256 for each file on the release page. For v0.31,
  `croftweaver.zip` and `website-builder.zip` are the same file:
  `sha256:ac18578f2746af5a5e7f02fa6b30c45e869c4f86d973d994574c68407a952a76`.
- There is no checksum file and no signature of our own. `npm create croftweaver` checks
  each skill file it unpacks (its CRC) and refuses links and odd entries, but it does not
  compare the download with a known checksum.
- The release is not marked immutable on GitHub, so its files could be replaced after
  publishing.
- Releases v0.29 to v0.31 are plain tags; the README's command makes annotated ones. The
  commit v0.31 points at is a merge commit signed by GitHub.
- `create-croftweaver` 0.1.0 on npm has no provenance record.
- As of 2026-10-14 the branch `stable` does not exist yet: the first release after the
  plugin was added (0.32) creates it.

## Outside audits

[skills.sh](https://skills.sh) shows audit results from Gen Agent Trust Hub, Socket and
Snyk. Checked on 2026-10-14:

- It lists the repository under its old name,
  [karero/website-builder](https://skills.sh/karero/website-builder), with 29 of today's 36
  skills. `facts-check`, `website-contact-form`, `website-scorecard`, `website-story`,
  `website-tagline`, `website-team-setup` and `wordpress-inspector` are missing.
  `skills.sh/karero/croftweaver` does not exist.
- The audits are from 6 July to 6 September 2026, so they describe older versions.
- **Socket:** pass on all 29.
- **Gen Agent Trust Hub:** pass on 28. Warning on `outgoing-link-audit`: it runs a shell
  script and requests outside links.
- **Snyk:** pass on 19. Warning on 9 skills for reading outside text that could carry
  instructions to the assistant (`customer-research`, `image`, `independent-review`,
  `outgoing-link-audit`, `schema-markup`, `search-console-insights`, `seo-reposition`,
  `website-positioning-check`, `website-qa`). `independent-review` was also warned
  for the `curl … | sh` install lines in its setup guide.
  **Fail on `search-console-setup`** (25 August 2026), because the assistant writes out
  the Google site-verification value for your DNS record. That value is not a password:
  it ends up in a public DNS record. We read this as a false alarm, but it is Snyk's
  result and stands as published.

## Reporting a problem

Report a security problem privately, as [SECURITY.md](../SECURITY.md) describes: GitHub's
private vulnerability reporting, on the repository's Security tab.

## What was not checked

- Whether Claude Code's block and allow rules behave as its documentation describes; this
  was read, not tried.
- Whether Codex and Antigravity ignore `.claude/settings.json`; this was read from the
  toolkit's own setup notes.
- What Astro, Wrangler, npm, Playwright and the AI services do with the data they receive,
  beyond their own published pages.
- The Codex sandbox (see above).
- Whether `facts-check` follows a redirect to another host.
