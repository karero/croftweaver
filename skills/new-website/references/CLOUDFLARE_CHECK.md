# The Cloudflare check: the checklist, run from outside

`scripts/cloudflare-check.mjs` asks a live site the questions the Cloudflare checklist
(`docs/CLOUDFLARE-CHECKLIST.md`) asks, and says for each item whether the answer is what the
checklist wants. It sends plain `GET` requests and nothing else: no token, no account, no
change. It needs Node 18 or newer, which every site made with the kit already has, and
nothing from npm.

It is the checklist's section 5 as a program, plus a list of the items that only the
dashboard can show. It does not replace the checklist: that file says why each setting is
what it is, and how to change it.

## Run it

```bash
node skills/new-website/scripts/cloudflare-check.mjs example.com --project my-project
```

In a scaffolded site the script is in the site's copy of the bundled skills, at
`<skills dir>/new-website/scripts/cloudflare-check.mjs`. Run it from anywhere: it reads no
file of the site.

| Option | What it does |
|---|---|
| `<domain>` | Your live domain, with no `https://` and no path. If your site lives on `www`, give `www.example.com`. |
| `--project <name>` | Your Pages project. Adds the checks of `<name>.pages.dev`: that it answers, and that it forwards to the domain. |
| `--hsts-on` | You have switched HSTS on. A missing header is then a failure, not a "look". |
| `--build <sha>` | The build you expect to be live. A different one in `/build.txt` is a failure. |
| `--json` | Print the results as JSON, for an assistant or another script. |
| `--timeout <s>` | Seconds to wait for each answer. The default is 15. |

Run it when the domain serves the site (the production deployment is Active, the custom
domain is Active), after you change a setting, and again after HSTS goes on. Before the
domain is live it only tells you that it is not.

## How to read it

| State | Means |
|---|---|
| `ok` | The answer is what the checklist wants. |
| `FAIL` | The checklist is not met, or the site did not answer. Fix these first. The line says which section to read. |
| `look` | Not wrong on its face, but only you can say whether it is what you meant: a redirect you set up on purpose, HSTS you have not switched on yet, rules for a crawler you named. |
| `by hand` | No request from outside can see this. The line gives the dashboard path. |
| `not run` | Not checked, with the reason: an option was not given, or the page it needs did not answer. |

The exit status is 0 when nothing failed, 1 when something failed or did not answer, and 2
when the command was wrong. **An empty answer is never a pass.** A site that does not answer
fails, and every item that needs its page is "not run", not "ok". An error page and a
challenge page are named as such, and the site is not judged from them. A home page that
redirects has its headers judged, and its source is not scanned.

## What each item looks at

| Checklist item | What the script asks | `FAIL` means |
|---|---|---|
| Create a Pages project (1) | `<name>.pages.dev` answers (needs `--project`) | The name is wrong, or it is a Worker |
| Attach your domain (1) | The home page over https answers below 400 | Error 522: the domain is not attached to the project. Other errors are named |
| Send pages.dev to your domain (1) | `<name>.pages.dev` answers 301 to your domain (needs `--project`) | It answers 200 or goes elsewhere: `CANONICAL_URL` is not in effect |
| Always Use HTTPS (2) | `http://domain/` answers 301 or 308 to `https://domain/`, whole address | No redirect, or one to another address |
| HSTS (2) | The `strict-transport-security` header: max-age in months, subdomains, preload | Missing, with `--hsts-on` |
| NEL off (3) | No `nel` header, no `report-to` header on the home page | The header is still sent |
| Bot Fight Mode off (3) | No `Set-Cookie` header and no `/cdn-cgi/challenge-platform/` script in the HTML | Either is there |
| Web Analytics off (3) | No `cloudflareinsights` script in the HTML | It is there |
| Email Address Obfuscation off (3) | No `email-decode` script and no `[email protected]` in the HTML | Either is there |
| AI crawlers allow (4) | Six requests that carry AI crawler names are not refused; `robots.txt` has no rules for named crawlers | Shown as `look`: a refusal may be your own choice to block Training |
| Your own robots.txt (5) | A robots file with a `Sitemap:` line that names your domain, not the starter's `example.com` | It is a web page, or still names `example.com` |
| The build that is live (5) | `/build.txt` serves a commit id, the one in `--build` if given | A different commit than `--build` |

The checklist says what to do about each. The script's own lines name the section.

## What it cannot see

- **The settings themselves.** Bot Fight Mode, Web Analytics, Email Address Obfuscation and
  the AI policies show only in what they add to the page. "No script in the page we
  received" is not proof the switch is off: a browser can receive more. Look at the page
  source in a browser once.
- **TLS 1.0 and 1.1.** The machine running the script often cannot speak them. Use
  ssllabs.com/ssltest, as the checklist says.
- **Crawler Hints, Fail open and the build settings.** They have no outside check. The report
  lists them as `by hand` with their path.
- **What a visitor from another country, or a visitor who is logged in, gets.** The script asks
  from one place, once.

The six crawler-named requests are plain requests from your machine with the crawler's name
in them. Cloudflare does not treat them as the real crawlers, so a 200 is consistent with
"Allow" and a refusal shows that some block is on. It is a hint, not a proof.

## For an assistant

Run it with `--json` and read `results`: a list, in the checklist's order, of
`{ id, section, title, state, detail, fix? }`, with a `summary` of counts. The `id`s are
stable: `pages`, `build-settings`, `domain`, `fail-open`, `canonical`, `https`, `tls`,
`hsts`, `nel`, `bot`, `analytics`, `email`, `hints`, `ai`, `robots`, `build`.

Say what the report says, in the owner's words: fix the `FAIL` lines first, ask about the
`look` lines, and list the `by hand` lines as what is left. Do not turn a `look` into an
instruction. If a check passes in the report but the owner sees the behaviour in a browser,
trust the browser and say the script could not see it.

Do not run it before the domain serves the site: the checklist's section 5 explains why a
request to the live domain before its build is Active can leave an error cached.

## By hand, always

No script, with or without a token, can do these for the owner:

- **Crawler Hints, and the off switch for Cloudflare Web Analytics.** The kit's notes say
  Cloudflare has no API for them.
- **HSTS, a few days after go-live.** The checklist's section 2 says why it goes on last.
- **The verification codes from Google and Bing.** They live in the owner's accounts there
  (`search-console-setup`).
- **Deleting the token**, if one was made (the checklist's section 6).

The domain's DNS moves to Cloudflare before any of this, and it is the riskiest moment,
mainly because of mail: see "Going live" in `CLOUDFLARE_FIRST_DEPLOY.md`.

## Keeping it true

The script's list of items and their dashboard paths is the checklist's. A test
(`make test-cloudflare-check`) reads `docs/CLOUDFLARE-CHECKLIST.md` and fails when an item or a
path differs, so a change to the checklist cannot leave the script behind unnoticed. The same
test file runs the script, as a program, against small servers on `127.0.0.1` that play a site
behind Cloudflare: one that is right, and one for each way it can be wrong.
