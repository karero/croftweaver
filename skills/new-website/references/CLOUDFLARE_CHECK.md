# The Cloudflare check: the checklist, run from outside

`scripts/cloudflare-check.mjs` asks a live site the questions the Cloudflare checklist
(`docs/CLOUDFLARE-CHECKLIST.md`) asks, and says for each item whether the answer is what the
checklist wants. It sends plain `GET` requests and nothing else: no token, no account, no
change. It needs Node 18 or newer, which every site made with the kit already has, and
nothing from npm.

It is the checklist's section 5 as a program, plus a list of the items that only the
dashboard can show. It does not replace the checklist: that file says why each setting is
what it is, and how to change it.

## Where it is, and how to run it

The script belongs to the `new-website` skill. It is in the Croftweaver folder at
`skills/new-website/scripts/cloudflare-check.mjs`, and in the installed skill at
`$SKILLS_ROOT/new-website/scripts/cloudflare-check.mjs` (`~/.claude/skills`, `~/.agents/skills`
or `~/.gemini/config/skills`, wherever the suite is installed; as a Claude Code plugin, the
`skills` folder under the install path that `claude plugin list --json` prints). A scaffolded site does not
carry a copy: `new-website` is not one of the skills copied into a site. Run it from
anywhere; it reads no file of the site.

```bash
node "$SKILLS_ROOT/new-website/scripts/cloudflare-check.mjs" example.com --project my-project
```

| Option | What it does |
|---|---|
| `<domain>` | Your live domain, with no `https://` and no path. If your site lives on `www`, give `www.example.com`. A page on this machine can be given as `http://localhost:4321`; any other `http://` address is refused. |
| `--project <name>` | Your Pages project (`my-project` or `my-project.pages.dev`). Adds the checks of its `pages.dev` address: that it answers, and that it forwards to the domain. |
| `--hsts-on` | You have switched HSTS on. A missing header is then a failure, not a "look". |
| `--build <sha>` | The commit you expect to be live: 7 to 40 hexadecimal characters. Without it the live build is only shown, not compared. |
| `--json` | Print the results as JSON, for an assistant or another script. |
| `--timeout <s>` | Seconds to wait for each answer, from 1 to 120. The default is 15. |

Run it when the domain serves the site (the production deployment is Active, the custom
domain is Active), after you change a setting, and again after HSTS goes on. Before the
domain is live it reports that the domain does not answer, or does not come through
Cloudflare, and most items are "not run".

## How to read it

| State | Means |
|---|---|
| `ok` | The answer is what the checklist wants. |
| `FAIL` | The checklist is not met, or something did not answer. Fix these first. The line says which section to read. |
| `look` | Not wrong on its face, but only you can say whether it is what you meant: a redirect you set up on purpose, HSTS you have not switched on yet, rules for a crawler you named. |
| `by hand` | No request from outside can see this, or only a hint. The line gives the dashboard path. |
| `not run` | Not checked, with the reason: an option was not given, or the page it needs could not be read. |

**The exit status** is 0 when nothing failed and everything was asked and judged. It is 1 when
an item failed, when a request got no answer, or when the home page could not be judged
(it redirected to another address, answered something other than a 200 page of HTML, or was
a challenge page), so that items are "not run" for that reason. It is 2 when the command was
wrong. "Not run" because you did not give `--project` does not change it. **An empty answer is
never a pass.**

A home page that redirects to the same address (a language redirect, for instance) is
followed up to three times and judged where it ends; a header or cookie on any answer on the
way counts. A redirect to another address (`www`, say) is not followed: the line names it,
and you run the check on that address. A redirect that goes on after three, or that has
nowhere to go, is said so and the page is not judged.

## What each item looks at

| Checklist item | What the script asks | `FAIL` means |
|---|---|---|
| Create a Pages project (1) | `<name>.pages.dev` answers below 400 (needs `--project`) | The name does not answer, or it answers an error |
| Attach your domain (1) | The home page over https answers 200, through Cloudflare (a `cf-ray` header) | No answer, an error (522: the domain is probably not attached), a challenge page. No `cf-ray` is a `look` |
| Send pages.dev to your domain (1) | `<name>.pages.dev` answers 301 to your domain (needs `--project`) | It answers 200 or goes elsewhere: `CANONICAL_URL` is not in effect |
| Always Use HTTPS (2) | `http://domain/` answers 301 or 308 to `https://domain/`, as an address | No redirect, or one to another address |
| HSTS (2) | The `strict-transport-security` header, read as directives: max-age in months, subdomains, preload | Missing, with `--hsts-on` |
| NEL off (3) | No `nel` header; no `report-to` header carrying Cloudflare's group | The header is still sent. Another `report-to` group is a `look`. So is Cloudflare's script monitor (Client-side security), which the line names: a `report-to` group, a `reporting-endpoints` entry or a `report-uri` of a report-only policy that lists an address on csp-reporting.cloudflare.com, judged by the host of that address and not by a name. It names what Cloudflare sends and does not decide what a browser would do with a header. NEL on still fails, and the line names the monitor beside it |
| Bot Fight Mode off (3) | No Cloudflare cookie, and no `/cdn-cgi/challenge-platform/` address in the page's tags or scripts | Either is there. A cookie of your own is a `look` |
| Web Analytics off (3) | No `<script src>` at `static.cloudflareinsights.com` and no `data-cf-beacon` attribute | It is there |
| Email Address Obfuscation off (3) | No `email-decode.min.js` at Cloudflare's path, no `/cdn-cgi/l/email-protection` link and no `data-cfemail` attribute | Any is there |
| AI crawlers allow (4) | Six requests that carry AI crawler names are not refused; `robots.txt` has no rules for named crawlers | Never `FAIL`: a refusal is a `look` (blocking Training may be your choice), and the policy itself is `by hand` |
| Your own robots.txt (5) | A robots file with a `Sitemap:` line that names your domain, not the starter's `example.com` | It is a web page, tells every crawler to stay out (`Disallow: /`, `/*` or `*` for `User-agent: *`, unless the same group has an `Allow` of that kind that is as long or longer: RFC 9309, 2.2.2, "the match that has the most octets", a tie to allow), or the sitemap host is the placeholder |
| The build that is live (5) | `/build.txt` is a full commit id; with `--build`, the one you gave | A different commit than `--build` |
| No scripts you didn't add (5) | No `/cdn-cgi/` path in the page other than the three above | Never `FAIL`: another path (Rocket Loader, Zaraz, image resizing) is a `look` that names it |

The checklist says what to do about each. The script's own lines name the section.

The script reads a page as HTML, with quotes respected: the addresses in `src`, `href` and
the like (read against the page's own address, with character references decoded), the names of
the attributes Cloudflare adds (`data-cf-beacon`, `data-cfemail`), and the text of scripts, for
`/cdn-cgi/` paths. Comments, the words a person reads, the text of a `textarea` or `title`, and
the values of descriptive attributes such as `title` or `alt` are left out, so a page that
talks about these scripts is not taken for one that loads them (inside an `<svg>` a `title`
holds markup, and is read as markup; a `script` there is still read as text to its end tag,
and a self-closed one has no text).
It is not a browser: a page built to confuse an HTML
reader can confuse this one. The headers of each answer on the way
are read one answer at a time, and HSTS is the page's own. A page larger than 5 MB is read for its first 5 MB only, and then the source
items are a `look`, never `ok`.

## What it cannot see

- **The settings themselves.** Bot Fight Mode, Web Analytics, Email Address Obfuscation and
  the AI policies show only in what they add to the page. "Not in the page we received" is
  not proof the switch is off: a browser can receive more, and a feature can behave
  differently for a visitor than for a plain request. Look at the page source in a browser
  once.
- **TLS 1.0 and 1.1.** The machine running the script often cannot speak them. Use
  ssllabs.com/ssltest, as the checklist says.
- **A header Cloudflare sends on a sample of pages.** The script monitor's headers came on 2 of
  40 requests on the one site we saw it on, and on none of 200 after it was switched off. A run
  that sees none does not show it is off, and neither does any number of requests: how often
  Cloudflare sends them is not documented. The switch is at Your domain → Security → Settings →
  filter by Client-side abuse → Continuous script monitoring; after switching it off, count
  requests to see that the headers stopped. This prints how many of 100 answered with one of
  the monitor's three headers (`report-to`, `reporting-endpoints` or
  `content-security-policy-report-only`; a site that sets one itself counts too), how many
  without one, and how many failed:

  ```bash
  for i in $(seq 1 100); do
    h=$(curl -sS --http1.1 -D - -o /dev/null "https://example.com/?cb=$RANDOM") || { echo failed; continue; }
    if printf '%s\n' "$h" | grep -qiE '^(report-to|reporting-endpoints|content-security-policy-report-only):'; then echo header; else echo none; fi
  done | sort | uniq -c
  ```
- **Crawler Hints, Fail open and the build settings.** They have no outside check. The report
  lists them as `by hand` with their path.
- **What a visitor from another country, or a visitor who is logged in, gets.** The script asks
  from one place, once.
- **A network behind a proxy.** The script uses Node's own HTTP client, which does not read
  proxy settings the way curl does. If it cannot reach a site that curl reaches, run the
  checklist's commands instead.
- **Whether a crawler name is treated as the real crawler.** The six crawler-named requests
  are plain requests from your machine with the crawler's name in them. Cloudflare may tell
  the real crawlers apart by more than their name, so "none was refused" is a hint, not a
  proof, and the policy is listed `by hand`.
- **Cloudflare's reasons.** The lines say what was seen ("answered 522"), and what that
  usually points to. They are not a diagnosis.

## For an assistant

Run it with `--json` and read the object: `domain`, `checkedAt`, `summary` (counts of `ok`,
`fail`, `look`, `hand`, `skip`), `unanswered` (requests that got no answer),
`couldNotJudge` (ids that were "not run" because the page could not be judged) and `results`.
`results` is a list in the checklist's order of `{ id, section, title, state, detail, fix? }`,
plus `blocked: true` on an item that could not be judged. `state` is one of `ok`, `fail`,
`look`, `hand`, `skip` (the screen says "FAIL", "by hand" and "not run"). `fix` is present
only on a `fail` or a `look`. The ids are stable: `pages`, `build-settings`, `domain`,
`fail-open`, `canonical`, `https`, `tls`, `hsts`, `nel`, `bot`, `analytics`, `email`, `hints`,
`ai`, `robots`, `build`, `scripts`.

Say what the report says, in the owner's words: fix the `FAIL` lines first, ask about the
`look` lines, and list the `by hand` lines as what is left. Do not turn a `look` into an
instruction. If a check passes in the report but the owner sees the behaviour in a browser,
trust the browser and say the script could not see it. Give `--build` the commit that was
deployed, so the live build is compared and not only shown.

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
(`make test-cloudflare-check`) reads `docs/CLOUDFLARE-CHECKLIST.md` and fails when an item
title or a dashboard path differs, so a renamed item cannot leave the script behind unnoticed.
It does not compare what each check wants (six months, a 301 or 308, preload off): when the
checklist changes a requirement, change the script and its tests by hand.

The same test file runs the script as a program against small servers on `127.0.0.1` that
play a site behind Cloudflare, with real requests and real exit statuses: one site that is
right, and a server for each way of being wrong the tests name. One test serves real TLS with
a certificate made for the run. The positives (a cookie, a beacon, the address hiding) are
tested on pages the test author wrote, in the shapes Cloudflare's documentation describes;
none was checked against a zone that has the feature on. The script monitor's headers are copied from one capture of a live site, not from Cloudflare's documentation, which names the `content-security-policy-report-only` header but not the other two.
