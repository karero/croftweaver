# Setup: accounts, tools, git, and Claude permissions

One-time machine setup for building/deploying the sites this skill scaffolds. Copy this
file into a handed-off repo so the receiving party can get running too.

---

## 1. Accounts to create (human action — Claude can't do these)

1. **GitHub — a PRIVATE account/repo.** https://github.com/signup. Client work stays in
   **private** repos. Run `gh auth login` (see tools) so pushes need no password.
   **Recommended: protect the account.** The account and the website in it are yours, and
   whoever gets into the account can change or delete the site. At
   https://github.com/settings/security, turn on **two-factor authentication** and add a
   **passkey** (sign in with fingerprint, face or phone; with two-factor on, a passkey covers
   both steps at once). Optional unless GitHub asks for it: GitHub requires two-factor only
   for some accounts, and tells those by email and on the site.
2. **Cloudflare account.** https://dash.cloudflare.com/sign-up. Hosts the site
   (Pages) and, if you move the domain's DNS there, the DNS. The free plan covers a small
   site. Cloudflare serves plain files free and without limit only while no Function runs,
   and this site's `functions/_middleware.ts` runs on every request: each page view, image
   and crawler visit counts against the free plan's 100,000 Functions requests a day, shared
   by every Pages Function and Worker in the account and reset at midnight UTC. After the
   first deploy, set the project's **Settings → Runtime → Fail open / closed** to **Fail
   open** (a free-plan setting), so the site stays online if that runs out. Upgrade to
   Workers Paid ($5/mo) when a feature needs it or a site gets near the limit.
   **Recommended: protect this account too.** It decides whether your website is online and,
   with the DNS here, where your domain points. In the dashboard, **My Profile →
   Authentication**, turn on **two-factor authentication**; a security key is the strongest
   choice, and your device's own fingerprint or face unlock (Touch ID, Android fingerprint,
   Windows Hello) counts as one; an authenticator app or email codes also work. Optional
   unless your Cloudflare account's administrator requires it: Cloudflare offers it at
   sign-in and lets you skip.

---

## 2. Tools to install

### macOS — via [Homebrew](https://brew.sh)
```bash
brew install node          # JS runtime + npm — runs Astro, the build, the tests
brew install git           # version control (the deploy = "push to GitHub")
brew install gh            # GitHub CLI — create repos & push from the terminal
npm  install -g wrangler   # Cloudflare CLI — local Functions preview & manual deploys

# image optimisation (see website-design-system)
brew install webp          # cwebp/dwebp — PNG/JPG → WebP
brew install libavif       # avifenc — → AVIF (smallest modern format)
brew install oxipng        # lossless PNG shrink (favicons/icons)
npm  install -g svgo       # minify SVGs (npm, not brew — needs node, above)
brew install jpegoptim     # optimise JPEGs
brew install exiftool      # strip EXIF/GPS from photos before publishing (privacy)
brew install imagemagick   # `magick` — resize/crop/convert, build responsive sizes
pip3 install Pillow        # OG share-card generator (`npm run og`); see og-images skill

# Markdown reader/editor (read & edit CONTENT_GUIDE.md, BRAND.md, README, etc.)
brew install --cask obsidian   # free Markdown editor (point a vault at the repo folder)

# per machine, once (re-run after a Playwright upgrade):
npx playwright install chromium   # the headless browser the tests drive
```

### Windows — via [winget](https://learn.microsoft.com/windows/package-manager/) (built into Win 11)
```powershell
winget install OpenJS.NodeJS.LTS      # Node + npm
winget install Git.Git                # git
winget install GitHub.cli             # gh
npm  install -g wrangler              # Cloudflare CLI
winget install ImageMagick.ImageMagick # `magick` — convert/resize, incl. WebP & AVIF
winget install Python.Python.3.13      # Python — runtime for the OG share-card generator
py -m pip install Pillow               # OG share-card generator (`npm run og`); see og-images skill
npm  install -g svgo                   # minify SVGs
winget install OliverBetz.ExifTool     # strip EXIF/GPS (verify id; or download the .exe)
winget install Obsidian.Obsidian       # Markdown reader/editor
# cwebp/dwebp CLIs: download libwebp from Google if needed — otherwise `magick` does WebP.
# oxipng / jpegoptim: optional on Windows; `magick` covers PNG/JPEG optimisation + AVIF.
npx playwright install chromium        # per machine, once
```
> On Windows, prefer building/testing inside **WSL2 (Ubuntu)** for parity with Cloudflare's
> Linux build environment — fewer line-ending/path surprises. If you build in WSL2, install
> the tools with the macOS/Linux commands above (including `pip3 install Pillow`) inside the
> WSL2 shell, not the PowerShell ones.

> **Node ≥22.23.4 required** (this starter's floor, never below Astro's own). Node's
> current security fixes are in **22.23.4, 24.22.1 and 26.12.1**: use the 22, 24 or 26
> line, at that version or newer, because older versions have known security flaws. A new
> site's `package.json` makes npm warn when its Node is older than that. After installing, and
> if Node is already on your computer, run `node --version` and update it the way you
> installed it when it is older. The repo's
> `.nvmrc` pins 24 for local + Cloudflare Pages. On **npm ≥11.16**, `npm install` warns
> "packages have install scripts not yet covered" for scripts it hasn't been told to trust
> — per npm's own docs this is currently advisory only (the scripts still run; a future
> npm release will start blocking them). The starter's `package.json` already approves the
> one package that still has an install script, `fsevents` (macOS only), so there is
> nothing to approve. (Until 7.3.8, Astro installed `esbuild`, which needed approving; since
> 0.35, sharp ships prebuilt binaries and needs nothing.)
> Approvals are pinned to the exact version reviewed (npm's own default, by design) — if a
> later update brings a package with an install script, the warning names it: approve it
> with `npm approve-scripts <name>`.

### What each tool does
| Tool | Function |
|---|---|
| node / npm | Runs Astro, builds the site, runs the test suite. |
| git | Version control; the deploy is "push to GitHub". |
| gh | Create the GitHub repo + push without a browser. |
| wrangler | Cloudflare CLI — `wrangler pages dev` local Functions, manual deploys. |
| @playwright/test | Drives a real browser for the tests (per-project dev dep). |
| @axe-core/playwright | WCAG accessibility scanner inside Playwright (per-project dev dep). |
| cwebp / avifenc | Convert raster images to WebP / AVIF. |
| imagemagick (`magick`) | Resize/crop/convert; generate the responsive size set. |
| oxipng / jpegoptim / svgo | Squeeze PNG / JPG / SVG. |
| exiftool | Strip camera EXIF + GPS from photos (privacy). |
| Obsidian | Read/edit the repo's Markdown docs (`CONTENT_GUIDE.md`, `BRAND.md`, READMEs) with live preview — open the site folder as a vault. Free; macOS + Windows. (VS Code's built-in Markdown preview also works if you'd rather not add an app.) |

---

## 3. Bootstrap git + .gitignore FIRST (before any code)

Initialise version control **before** scaffolding, so secrets and `node_modules` can never
be committed by accident:
```bash
mkdir <site> && cd <site>
git init
# Where the suite is installed: ~/.claude/skills (Claude Code) · ~/.agents/skills (Codex)
# · ~/.gemini/config/skills (Antigravity). Honour an explicit $SKILLS_ROOT; else auto-detect.
# Installed as a Claude Code plugin, it is in none of the three: set SKILLS_ROOT to the
# `skills` folder under the install path that `claude plugin list --json` prints.
if [ -z "${SKILLS_ROOT:-}" ]; then
  SKILLS_ROOT="$HOME/.claude/skills"
  for d in "$HOME/.claude/skills" "$HOME/.gemini/config/skills" "$HOME/.agents/skills"; do
    [ -d "$d/new-website" ] && SKILLS_ROOT="$d" && break
  done
fi
cp "$SKILLS_ROOT/new-website/templates/.gitignore" .
git add .gitignore && git commit -m "chore: init repo with .gitignore"
```
The template `.gitignore` excludes `node_modules/`, `dist/`, `.astro/`, Playwright artifacts,
`.env*` secrets, `.wrangler/`, and OS/editor cruft. **Never commit a `.env` or any token** —
Cloudflare/analytics secrets live in the Cloudflare dashboard's env vars, not the repo.

When you create the GitHub repo (`gh repo create … --private`), also turn on auto-delete of
merged PR head branches — the assistant always works through pull requests (`AGENTS.md`
§2), so this keeps stale branches from piling up from day one (GitHub never deletes a
PR's *base* branch, so long-lived staging/production branches are safe). Pair it with
fetch-time pruning so the deleted branches also disappear from local `origin/…` references
(prune only cleans tracking refs, never local branches):
```bash
gh repo edit --delete-branch-on-merge
git config --global fetch.prune true   # once per machine; use --local to scope per repo
```

Then let GitHub warn you about security holes in the site's building blocks (the npm
packages it installs) and, where a fixed version exists, send the fix as a pull request.
When none can be applied, the warning still shows under the repo's **Security** tab.
Both are free on every plan, but a private repo starts with them off. A fix pull request
is checked by CI like any other; merge it once it is green. Run this in the site's
folder; it works the same for a site you already have.
```bash
gh repo view --json nameWithOwner --jq '"repo: \(.nameWithOwner)"'   # check: your site?
gh api -X PUT "repos/{owner}/{repo}/vulnerability-alerts"        # Dependabot alerts
gh api -X PUT "repos/{owner}/{repo}/automated-security-fixes"    # Dependabot security updates
gh api --silent "repos/{owner}/{repo}/vulnerability-alerts" 2>/dev/null && echo "alerts: on" || echo "alerts: off"
gh api "repos/{owner}/{repo}/automated-security-fixes" \
  --jq 'if .paused then "security updates: paused" elif .enabled then "security updates: on" else "security updates: off" end'
```
The first line names the repo the commands change: if it names another repo, or none,
stop and move to the site's folder. The last two lines check the result: they should
print `alerts: on` and `security updates: on`. Anything else (`off`, `paused` or an
error): open the repo's **Settings → Code security** and turn on Dependabot alerts, then
Dependabot security updates.

The starter also ships `.github/dependabot.yml`. Once a month Dependabot then opens one
grouped pull request for the minor and patch updates of the site's packages, and one for
the GitHub Actions the workflow uses. A new major version of any package other than the two held
back arrives as a pull request of its own and can stay open until you want it. Dependabot raises no
new version pull request while five are open (security pull requests have a separate limit), so merge
or close the ones you do not want to keep, or the monthly one stops coming. Someone has to merge the
monthly ones once CI is green: name that person in the README. If nobody will, delete the file; the security updates above stay on
without it. Dependabot opens its pull requests against the repo's default branch, so check
which that is (`gh repo view --json defaultBranchRef`): on a two-stage site it should be
`main`, the preview stage, so nothing goes live before `npm run ship`.

### Pre-push quality gate (auto-wired by `npm install`)

The `prepare` script in `package.json` (`node scripts/wire-hooks.mjs`) points
`core.hooksPath` at `scripts/hooks`, so the shipped **`pre-push` hook** runs `scripts/verify.mjs`
(the same as `npm run verify`: type check, then the tests, which build the site) and
**blocks a push that's red** — the local enforcement of "fails → does not ship" (Cloudflare
deploys independently of CI, so this is what makes that true on a direct-push workflow). It
needs `npx playwright install chromium` (above). Relax for one push with
`git push --no-verify`; disable with `git config --unset core.hooksPath`. See `website-qa`
§1c — offer this choice, don't impose it.
`prepare` wires the hook only when the site is the root of its git repo. Kept in a subfolder
of a bigger repo, it leaves that repo's hooks alone, and the gate does not run on push.
It is a Node script, so it needs no particular shell: on Windows npm runs scripts through
`cmd.exe` by default. An older `prepare` line calls `git config` itself; that is sh syntax,
and nothing shows it works there. Such a line without `--show-prefix` also rewired the bigger
repo, to a `scripts/hooks` that repo does not have; git then runs none of its hooks. The
header of `scripts/hooks/pre-push` quotes the current line and says how to repair both.

The hook also contains a commented-out **PR-only-main guard** (the `website-team-setup`
skill enables it when a team forms and the plan offers no server-side ruleset): enable it when several people
or parallel AI agents share the checkout and new commits should reach `main` only via reviewed
PRs (server-side branch protection needs a paid plan on private repos). It's a **local,
advisory convention, not an enforced one** — `ALLOW_MAIN_PUSH=1`, `git push --no-verify`, unsetting
`core.hooksPath`, or pushing from a different clone all bypass it — so it only helps when
everyone sharing the checkout has it enabled and respects it; it rejects direct pushes to
`main` (`ALLOW_MAIN_PUSH=1` overrides) from a checkout that has it on, while ship flows
pushing `main:production` and GitHub PR merges are unaffected either way.

---

## 4. Stop Claude asking permission for every command

**Claude Code only.** Copy the permission allowlist into the project so routine build
commands (npm/astro/playwright/git read+commit, image tools) run without a prompt:
```bash
mkdir -p .claude/hooks && cp "$SKILLS_ROOT/new-website/templates/claude/settings.json" .claude/settings.json
cp "$SKILLS_ROOT/new-website/templates/claude/hooks/git-stand.mjs" .claude/hooks/
```
The settings also register `.claude/hooks/git-stand.mjs`: at every session start (and
again once the last sync is 2 hours old) it runs `git fetch` and tells you and Claude what
changed on GitHub. It never pulls, merges or changes files.
> **Codex / Antigravity:** skip this — `.claude/settings.json` is Claude Code-specific. On
> Codex, durable project instructions live in `AGENTS.md` (the scaffold ships one; `CLAUDE.md`
> imports it) and command approval in Codex's own rules/config. Antigravity uses its own
> sandbox/approval model.
It blocks destructive/irreversible commands (`rm -rf`, the usual force pushes,
`git reset --hard`, `wrangler … delete`, `gh repo delete`): Claude Code refuses them
outright, with no question, so run one yourself in a terminal if you really mean it. A
force flag bundled with others (`git push -uf`) is not caught: a rule only matches text. `git push` and `gh repo create` *are* allowed (own private repos, smooth workflow);
remove them from `allow` if you'd rather confirm each push.

`settings.json` is committed (shared project policy). Personal/secret overrides go in
`.claude/settings.local.json`, which the `.gitignore` keeps out of the repo. To extend the
list later, run `/fewer-permission-prompts`.
