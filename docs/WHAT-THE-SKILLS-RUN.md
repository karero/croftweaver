# What the skills run on your computer

This page says what Croftweaver does on your computer and on the internet: which commands
its skills run, which services they talk to, what they write outside your site's folder,
where your keys are kept, and how a release is made. It was written by reading the scripts
and the skill files, not from memory.

**Checked on 2026-10-14, against `main` at commit `e038603`; the changes up to `034472d`
were read again, and those up to `edf97ba` (the brand kit, the weekly fix proposal and the
analytics folder) on the same day. On 2026-10-20 the parts that changed after that were
read again, up to `92cfb26`: the weekly job's start time, the one-at-a-time AI check, the
Search Console sign-in, the installer's checksum check, and the state of release v0.32.**
A later change can make a line here wrong. Where something could not be checked, the line
says so.

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
  [What runs without asking](#what-runs-without-asking); read from Claude Code's
  documentation on permission rules, not tried in a live session). That list also lets `node`,
  `npm run` and `git push` run without asking. It saves clicks; it is not a safety fence.
- **Releases carry no signature of our own.** Since v0.32 a `SHA256SUMS` file sits beside
  the zip, the release cannot change once published, and GitHub signs a record of it;
  v0.31 and earlier have none of this, but GitHub shows a SHA-256 for each download. See
  [Releases](#releases).

## What runs without asking

**Claude Code.** Every new site made with Claude Code gets `.claude/settings.json`
([template](../skills/new-website/templates/claude/settings.json)). The `website-permissions`
skill installs the same file into an existing site. It has three parts. What each part
does below is how Claude Code's
[permission documentation](https://code.claude.com/docs/en/permissions) describes it; it
was read, not tried in a live session.

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
- **Blocked:** `rm -rf`, the usual force pushes (`--force`, `--force-with-lease`, `-f` or
  a `+branch`, wherever it stands in the command), `git reset --hard`, `gh repo delete`,
  `wrangler delete` and `wrangler pages delete` (with or without `npx`). The documentation
  says a block rule prevents the command; it does not ask. You run such a command yourself
  if you really mean it.
- **Everything else asks first**, as long as Claude Code is in its normal mode. If you
  switch Claude Code to a mode that approves everything, nothing asks.

What this list does and does not protect:

- `node …`, `npm run …` and `npm exec …` can run any program. So the list is a way to stop
  routine prompts, not a sandbox. Apart from the list, the site's `AGENTS.md` tells the
  assistant never to run `npm run ship` unasked and to merge a pull request only when you
  say so. Those are written rules for the assistant, not something Claude Code enforces.
- `git push` and `gh repo create` are allowed on purpose. `SETUP.md` in each site says to
  take them out of the list if you would rather confirm each push.
- The block rules match the command as written. Besides `git push --force` and
  `git push -f` at the start, three rules catch a force flag or a `+` later in a push, so
  `git push origin main --force` and `git push origin +main` are blocked too.
  `git push --delete` is allowed: tidying up merged branches needs it. Tested on
  2026-10-14 with Claude Code 2.1.287, run headless with these settings in a throwaway
  repository: all seven force-push forms tried were blocked, and `--delete`, a plain push
  and `--follow-tags` ran. With the rules as they were before, five of the seven ran,
  `git push --force-with-lease` at the start among them. A force flag bundled with others
  still runs (`git push -uf origin main` and `git push origin main -vf`, tested the same
  day): a rule broad enough to catch it would also block `--follow-tags` and branch names
  with `-f` in them.
- `find` with `-delete` or `-exec` should still ask: Claude Code's documentation says a
  `find` rule cannot approve a `find` that deletes, writes or runs commands. (Read, not
  tried in a live session.)

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

Two more name a few commands:

- `business-listings-setup` has the assistant request each profile address your site
  links to (Google, LinkedIn and the like), the way `outgoing-link-audit` does, to see
  whether it still works.
- `image` shows example commands for image tools (`cwebp`, `mogrify`, `jpegoptim`) and a
  `curl` that reads a page's image list. It may suggest an image service (Gemini, Flux,
  Ideogram, OpenAI) that you use with your own account and key.

### Skills that run the site's own build and tests

`website-content-guide`, `website-positioning`, `website-story`, `website-tagline`,
`website-testimonials`, `astro-i18n-setup`, `website-positioning-check`, `website-qa`,
`website-review`, `internal-link-audit`, `og-images`, `website-seo-geo`, `double-knuth`,
`website-contact-form`, `website-scorecard` and `website-brand-kit` run commands such as
`npm run build`, `npm test`, `npm run verify`, `npm run og`, `git status`, `git log` and
`git diff` in the site's folder. Some copy template files into the site. All of this stays
in the site's folder, apart from what npm and Playwright download (see [Network calls](#network-calls))
and the short-lived folders `website-scorecard` and `website-brand-kit` make in your temp
folder and delete again.

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
  then runs `npm run verify` before each push, except a push that only deletes branches or
  tags.
- `npm run ship` (two-stage sites) pushes `main` to the `production` branch on GitHub,
  which makes Cloudflare publish the live site, then reads the live `build.txt` until it
  shows the new commit. It refuses to run on a branch other than `main`, with unsaved
  changes, or when `production` has moved on its own, and it never force-pushes.

`website-contact-form` builds a `mailto:` link: the visitor's own mail program sends the
message. There is no form server. If the site's analytics are on, the press also counts as
an "Email Tap" event there, as a click on an email address does.

### Skills that run scripts

- **`new-website`** creates the site folder (in the folder you confirm), runs `git init`,
  `npm create astro@latest`, copies the templates and 27 skills into the site, and runs the
  build and tests. For Cloudflare it uses `npx wrangler pages project create` and
  `npx wrangler pages deploy` with a token you make, or `npx wrangler login`. Its
  `scripts/cloudflare-check.mjs` reads your site's public addresses to check the Cloudflare
  settings; it needs no token. It also sends requests that carry the names of AI crawlers
  (GPTBot, ClaudeBot and others) to your own domain, to see whether Cloudflare lets them in.
  Its `scripts/cloudflare-setup.mjs` changes your Cloudflare account through Cloudflare's API,
  with a short-lived token you make: it creates the Pages project or uses the one connected
  to your repository, starts its first build, changes your domain's settings from the
  Cloudflare checklist, and writes the verification records you give it. It changes nothing
  until you have said yes to the list it prints, and it deletes nothing. It runs `git` to read
  your repository's branches and `src/config.ts`, and asks your domain's nameservers whether
  a record it wrote is there. It sends your domain no request.
- **`website-team-setup`** uses `gh` to change GitHub settings once you ask for team
  setup: invite collaborators, edit repository settings, create and update branch rules,
  start a check run, and push and close a throwaway test branch. It runs these without a
  separate question for each; deleting a branch rule needs your go-ahead.
- **`keystatic-setup`** (only if you chose a content editor) installs `@keystatic/core` and
  `@keystatic/astro` with npm and runs `npx astro add react markdoc`.
- **`facts-check`** runs `facts_check.py`, which reads your site's public pages and its
  sitemap and compares facts across them. It changes none of your pages; where the site has
  an `analytics/` folder, its report is saved there.
- **`wordpress-inspector`** runs `wp_inventory.py` and `check_move.py`, which read a
  WordPress site's public pages, its public `wp-json` data and its sitemaps. They need no
  sign-in. Its `make_redirects.py` reads only local files and writes the new site's
  `public/_redirects`.
- **`outgoing-link-audit`** runs `scripts/check_external_links.sh`, which builds the site
  if needed and then requests every outside link on it with `curl`.
- **`search-console-insights`** (optional) builds a Python environment in
  `~/.config/gsc-insights/venv` and installs `google-api-python-client`,
  `google-auth-oauthlib` and `requests` into it, after you say yes to connecting. Its
  scripts read your Search Console and Bing data, look up search results, and run the
  weekly AI check. `ai_reports.py` reads the Google and Bing AI reports you download and hand
  over, on your computer only, and with `--keep-in` keeps a copy in the site's `analytics/`
  folder. `schedule_tracking.sh install` sets up a weekly run on macOS, and only on an
  explicit yes: it gives each site's job its own start minute where one is free, so several sites are
  less likely to run at once (a re-install keeps a free minute the site already has; with
  all twelve slots at one day and hour taken, a site shares :00 and the script says so). Once per site per session it runs `schedule_tracking.sh status`, which only
  reads. The AI check takes turns: a run waits (up to 90 minutes, then goes on anyway) while
  another site's AI check holds a lock file, so the AI services see one site at a time. If
  Google refuses the saved Search Console sign-in, running `gsc_query.py` by hand opens the
  browser to sign in again. The weekly job, `insights.py` and the weekly report never open a
  browser: they report it, and you reconnect by running `gsc_query.py`.
  - The weekly fix proposal: `fix_proposal.py` keeps the list of proposed page fixes in
    `~/.config/gsc-insights/sites/` and asks GitHub (`gh pr view`) whether a pull request it
    recorded was merged. The weekly report reads your own live pages (only on your own
    domain) to check what a fix changed. When you say yes to a proposal, the assistant edits
    that page's title, heading and first paragraph on a new branch, runs the site's checks
    and opens a pull request; it does not merge it unasked.
  - The analytics folder: `analytics_snapshot.py` copies the reports from
    `~/.config/gsc-insights/` into an `analytics/` folder in the site, which the starter's
    `.gitignore` keeps out of git. It reads nothing from the network, and it refuses to write
    a file git would track, unless you choose to keep the folder in a private repository
    (`--commit-ok`).
- **`website-brand-kit`** (only when you ask for help with colours or a logo) runs
  `brand_intake.py`, which reads a palette or a logo package you hand over and installs it:
  it edits the site's colours, `src/config.ts`, the web manifest and the share-card script,
  writes the icons and a `brand-handoff/` folder (kept out of git), and makes the share
  cards again. To do that it runs the site's own `node` and Python scripts and then the
  site's build and tests (`npm run build && npm test`, or a test command the assistant
  names). It draws the icons with the site's own `sharp` package, without a browser. It
  makes no network call of its own and needs no key; the site's build and tests it runs are the site's own, and whatever they fetch is not covered here. In Claude Code, `python3` is not on the
  allowlist, so starting it asks; the commands it runs from there are not asked one by one.
- **`website-permissions`** copies `.claude/settings.json` and the sync hook script it
  registers (`git-stand.mjs`, which runs `git fetch`) into the site (see
  [What runs without asking](#what-runs-without-asking)).
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
tool only when it is needed. `website-seo-geo` may need `pip install pypdf`, and
`website-brand-kit` may ask for `npm install --include=optional` (for `sharp`) or
`pip3 install Pillow`.

`independent-review`'s setup guide lists install commands for its reviewers, three of them
in the form `curl … | sh` from chatgpt.com, antigravity.google and ollama.com, next to
Homebrew and npm alternatives. Its setup wizard asks you to paste these yourself.

## Network calls

| Who | Used by | Key or sign-in | Reads or sends |
|---|---|---|---|
| GitHub | git (`fetch`, `pull`, `push`), `gh`, `npm run ship`, the sync hook, the weekly fix proposal (`gh pr view`, and a pull request when you accept a fix) | your git and `gh` sign-in | reads, and sends your site's code when pushing; a fix proposal's pull request carries search figures if the repository is private, and in a public one only if you have said yes (the assistant asks once) |
| GitHub release downloads | `npm create croftweaver` | none | reads `croftweaver.zip` and its `SHA256SUMS` from the newest release |
| npm registry | `npm install`, `npm ci`, `npx`, `npm create astro` | none | reads packages |
| Playwright's download servers | `npx playwright install chromium` | none | reads the test browser |
| Homebrew, winget, PyPI | installing the build tools, Pillow, pypdf and the Search Console libraries | none | reads programs |
| chatgpt.com, antigravity.google, ollama.com | the `curl … \| sh` install lines in `independent-review`'s setup guide, if you use them | none | reads the installers |
| croftweaver.com | `new-website`'s footer credit step, only if you say yes | none | reads the badge code from `/partner-assets` and the badge files |
| An image service you choose | `image`, if you use one | your own key | sends your image prompts |
| Cloudflare | `wrangler` (deploy, project create, deployment list) | an API token you make, or `wrangler login` | sends the built site |
| Cloudflare's API | `cloudflare-setup.mjs` | an API token you make, ending within a week | reads your zone, its records and your Pages projects; after your yes, creates or changes the project, starts a build, and writes zone settings, Bot Management and DNS records |
| Your domain's nameservers | `cloudflare-setup.mjs` | none | asks whether a record it wrote is served |
| Google Search Console | `search-console-insights` (`gsc_query.py`, `search_report.py`, `insights.py`) | your own Google sign-in, scope `webmasters.readonly` | reads only; asks for clicks, impressions and positions |
| Bing Webmaster | `bing_query.py` | your `BING_API_KEY` | reads only |
| Serper or SerpApi | `serp_check.py` | your `SERPER_API_KEY` or `SERPAPI_KEY` | sends a keyword, country and language; reads search results |
| OpenRouter, or Gemini, OpenAI, Anthropic, Perplexity directly | the weekly AI check (`geo_check.py`) | your own key for each (`GEO_…_API_KEY`) | sends the questions you confirmed, one of which names your business; reads the answers |
| SerpApi (Google's AI answers) | `geo_check.py`, only if you switch it on | your `SERPAPI_KEY` | sends the same questions |
| Your own site's pages | `geo_check.py` (the home page), the weekly search report (pages a fix changed) | none | reads them; the report follows redirects only on your own domain |
| OpenAI (through the Codex app) | `independent-review` | your Codex sign-in | sends the plan or code change |
| ollama.com | `independent-review` | your `OLLAMA_API_KEY` or `ollama signin` | sends the plan or code change |
| melious.ai | `independent-review`, only when a model is named for it | your `MELIOUS_API_KEY` | sends the plan or code change |
| Google Antigravity | `independent-review`, only when you ask for it | your Antigravity sign-in | sends the plan or code change |
| Public web pages | `facts-check`, `wordpress-inspector`, `outgoing-link-audit`, `business-listings-setup`, `cloudflare-check.mjs` | none | reads only |
| docs.astro.build, developers.cloudflare.com, keystatic.com | the assistant, when it looks up documentation (allowed without asking in Claude Code) | none | reads only |
| Your analytics (Plausible), if you set it up | the built site, live version only | none | your visitors' page views, and an "Email Tap" event when a visitor clicks an email address or presses the contact form's button and the form's checks pass, go to the analytics address you set. The site's code passes Plausible only the event name; Plausible's script adds what it adds to every event (the code's comments name the page and the referrer). This was read from the code, not measured. In server mode the site's Cloudflare Function sends instead, from Cloudflare: per page view the page address, the referrer, the visitor's user agent and IP; per email tap the event name and the page (measured in a trial, 2026-10-15), plus the visitor's user agent and IP (read from the code). The contact form's button is not counted then |

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
  checks your own new site. The weekly search report says who it is
  (`search-console-insights fix check`). `check_external_links.sh` and `geo_check.py` send a
  browser's user agent.
- **The built site**, apart from the optional analytics script, loads no fonts, scripts
  or styles from other servers. Its security header (`public/_headers`) allows scripts only
  from the site itself, and from the analytics address you set once you switch analytics
  on: the starter ships with it off. Analytics run only on the live site, not on previews. In analytics
  server mode no analytics script loads at all.

## Telemetry

Croftweaver sends nothing to its maintainer. This was checked in two passes, and again on
the code up to `edf97ba`:

- Every script, template and installer (`*.py`, `*.sh`, `*.mjs`, `*.js`, `*.ts`, `*.astro`,
  `*.json`, `*.yml`, `Makefile`, the pre-push hook) was searched for analytics and tracking
  terms (`telemetry`, `analytics`, `beacon`, `sentry`, `posthog`, `plausible`, `umami`,
  `gtag`, `mixpanel`, `segment`, `amplitude` and others) and for every network call
  (`curl`, `wget`, `fetch(`, `urllib`, `requests`, `http.client`, `https://`, `gh api`,
  `git push`).
- Every skill text and the plugin files (`*.md`, `.claude-plugin/`, `.agents/plugins/`) were
  searched for `croftweaver.com`, the repository's GitHub account name, `telemetry`,
  `beacon` and wording that asks the assistant to report back.

What touches the maintainer's own places:

- `npm create croftweaver` reads the release zip and its `SHA256SUMS` from GitHub, Claude Code and Codex
  read the plugin from GitHub, and a `git clone` of the toolkit (one of the README's install
  routes) reads it from GitHub.
- After launch, `new-website` asks you once whether you want a "Built with Croftweaver"
  credit in your footer. Only if you say yes does the assistant read the badge code and
  files from croftweaver.com; like any web request, that one shows up in croftweaver.com's
  server logs. The skill tells the assistant to save the badge in your site. The starter's
  security header (`public/_headers`) lets images load only from the site itself or as
  inline data (`img-src 'self' data:`), so a browser that applies it does not fetch a
  badge from croftweaver.com. (Read from the starter; not tested on a live site.) The credit is a link
  to croftweaver.com.
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
| `~/.config/gsc-insights/` (Python environment, `token.json`, `.env`, `history.csv`, `sites/` with the fix proposals, `reports/`, `geo/` with `ai-check.lock`, `logs/`, a lock file per site) | `search-console-insights` | when you connect Search Console, run the AI check or the weekly report, or answer a fix proposal | delete the folder |
| `~/Library/LaunchAgents/com.gsc-insights.<site>.plist` | `schedule_tracking.sh install` (macOS only) | when you say yes to weekly tracking (the start minute is the first of :00, :15, :30 and :45, then 5-minute steps, that no other site uses at that day and hour; a re-install keeps a free minute, and with all twelve taken the site shares :00) | `schedule_tracking.sh remove <site>` (leaves the log and history behind) |
| `~/.local/state/independent-review/runs.tsv` | `independent-review` | each review (turn off with `REVIEW_LOG=off`) | delete it |
| a folder in your temp folder | `independent-review` | each review; holds the reviewers' answers, readable only by you | the skill tells the assistant to delete it at the end |
| `~/.gitconfig`: `fetch.prune true` | you or the assistant, from `SETUP.md` and `website-team-setup` | once per computer, when you set up git or a team | `git config --global --unset fetch.prune` |
| a short-lived folder in your temp folder | `website-scorecard`, `website-brand-kit`, `analytics_snapshot.py` | each run | deleted at the end of the run |

In the site repository's git folder, the sync hook (`.claude/hooks/git-stand.mjs`, at
session start and again once the last sync is 2 hours old) keeps a small marker file,
`claude-git-stand`: normally `.git/claude-git-stand`, and for a git worktree in that
worktree's folder under the main checkout's `.git/worktrees/`. If the git folder cannot be
written, the file goes to your temp folder instead.

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
| Cloudflare API token | an environment variable for the session (Wrangler 4.151.0 read a token from the shell and not from `.dev.vars`, tested 2026-10-14); the guide asks for a narrow token that expires in about a week |

All of these live outside the site's folder. The site's `.gitignore` also excludes `.env`,
`.env.*` (but not `.env.example`), `.dev.vars`, `.wrangler/` and, at the site's top level,
`client_secret*.json` and `token.json`, in case a copy lands there, and `analytics/`, where
the reports are kept. The review tool passes
its keys to `curl` through standard input, not on the command line. The Bing script
removes the key from error messages before they reach a log; a test guards this.

Known gap: `~/.config/gsc-insights/.env` is made readable only by you when `geo_check.py
--prepare-env` adds lines to it. A file you create or edit by hand keeps whatever
permissions it gets. `client_secret.json` is never tightened.

## Releases

How a release is made (README, "Releases & versioning", and
[`.github/workflows/release-tag.yml`](../.github/workflows/release-tag.yml)):

1. A pull request raises the version in `.claude-plugin/plugin.json`.
2. `make smoke` runs the suite's checks (`make check`), builds and checks
   `dist/croftweaver.zip`, then writes its checksum to `dist/SHA256SUMS`.
3. The maintainer tags the release (`v0.32`) and creates a GitHub release with the zip and
   `SHA256SUMS`, in one command.
4. The tag starts a workflow that checks the version number and moves the branch `stable`
   to the release. The Claude Code plugin installs from `stable`.

What protects a download today:

- GitHub shows a SHA-256 for each file on the release page. For v0.31,
  `croftweaver.zip` and `website-builder.zip` are the same file:
  `sha256:ac18578f2746af5a5e7f02fa6b30c45e869c4f86d973d994574c68407a952a76`.
- Up to v0.31 there is no checksum file. Since v0.32 (published 2026-10-16), `SHA256SUMS`
  sits beside `croftweaver.zip`; the README ("Releases & versioning") says how to check a
  download against it. GitHub shows `croftweaver.zip` of v0.32 as
  `sha256:d8caec1ad00c3b5a996f0c6bc7a29001cb927a35bc5ca131ca8a7166f169061d`.
- There is no signature of our own. From version 0.2.0, `npm create croftweaver` compares the
  download with the SHA-256 the release's `SHA256SUMS` lists for it before unpacking, and
  refuses a release without that file (v0.31 and older). Both files come from the same
  release, so this catches a download that was damaged or cut short on the way, or that
  belongs to another release, not a change by anyone who can alter what GitHub serves.
  It also checks each skill file it unpacks (its CRC) and refuses links and odd entries.
  Version 0.1.0 does not compare the download with a checksum.
- v0.31 is not marked immutable on GitHub, so its files could be replaced after
  publishing. Since 2026-10-14 the repository has release immutability on: v0.32 is marked
  immutable on GitHub, so its files and tag cannot change, and `gh release verify v0.32`
  passed on 2026-10-20 (GitHub's signed record of the tag, commit and files).
- Releases v0.29 to v0.32 are plain tags (checked for v0.32: `git cat-file -t` says
  `commit`, not `tag`); the README's command makes annotated ones. The commit v0.31 points
  at is a merge commit signed by GitHub; v0.32 was not checked for that.
- `create-croftweaver` 0.2.0 is the newest on npm (checked 2026-10-20). `npm view` shows no
  provenance record for it, and 0.1.0 has none.
- The branch `stable` exists and points at v0.32's commit (`a0fbfb1`, checked 2026-10-20).
- Before the maintainer publishes a new version of `create-croftweaver` to npm, its
  `prepublishOnly` step runs `packages/create-croftweaver/check-release.mjs`, which downloads
  the latest GitHub release and runs the installer on it; if the installer would refuse it,
  the publish stops. That runs on the maintainer's computer only, and npm skips it if the maintainer publishes with `--ignore-scripts`.

## Outside audits

[skills.sh](https://skills.sh) shows audit results from Gen Agent Trust Hub, Socket and
Snyk. Checked on 2026-10-14:

- At that check it listed the repository under its old name,
  [karero/website-builder](https://skills.sh/karero/website-builder), with 29 of the then 36
  skills. `facts-check`, `website-contact-form`, `website-scorecard`, `website-story`,
  `website-tagline`, `website-team-setup` and `wordpress-inspector` were missing, and
  `skills.sh/karero/croftweaver` did not exist. Later that day, after one install under the
  new name, the listing moved to
  [karero/croftweaver](https://www.skills.sh/karero/croftweaver) with all 37 skills, and the
  old address forwards there (the README's install section says the same).
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

- Whether Claude Code's block and allow rules behave as its documentation describes,
  beyond the push test above; the rest was read, not tried. The test ran headless, where a
  command that is not allowed is refused without a question, so it shows that the force
  pushes did not run, not that a blocked command never asks.
- Whether Codex and Antigravity ignore `.claude/settings.json`; this was read from the
  toolkit's own setup notes.
- What Astro, Wrangler, npm, Playwright and the AI services do with the data they receive,
  beyond their own published pages.
- The Codex sandbox (see above).
- Whether `facts-check` follows a redirect to another host.
