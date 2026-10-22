# Onboarding — the agent runs this wizard on first use

**When invoked and the user is NOT yet connected** (no token at
`~/.config/gsc-insights/token.json`), do **not** dump commands. Walk the user through
it like a friendly wizard, in the order below. Assume a non-technical site owner who
has never heard of an "API". Do the heavy lifting yourself; clearly flag which steps
only they can do.

### Step 1 — Sell the benefit FIRST (before asking for anything)
In 3–4 plain sentences, tell them what they get and why ~10 minutes is worth it:
- *"Google Search Console is **free** and shows the **real** words people typed into
  Google to find your site, exactly where you rank for each, and how often you get
  clicked — data no guesswork keyword tool has."*
- *"Once connected, I can tell you in seconds: the keywords you're **almost** on page 1
  for (your fastest wins), the pages that get seen but not clicked (a quick title fix),
  and — with a free add-on — who's beating you in the Top 10."*
- *"It's **read-only** and free. The one-time setup is ~10 minutes — I do most of it;
  you do a few clicks inside Google's console that I'm not allowed to do for you."*

Then ask **"Want to connect it now?"** and only continue on a yes.

### Step 2 — Check what's already done; ask only for what's missing
So a returning user is never re-onboarded:
- token at `~/.config/gsc-insights/token.json` → **already connected**, skip to Step 5.
- `~/.config/gsc-insights/client_secret.json` exists → creds done; just venv + first run.
  Still ask them to check the **Publish app** part of Step 3c: the app's **Audience** tab
  must read **In production** (or **Internal**), or the weekly check stops after a week.
- venv at `~/.config/gsc-insights/venv` exists → deps done.

### Step 3 — The human-only steps ( 🧑 **you do this** )
You cannot click inside Google's console. Hand these over **one at a time** and wait —
do not paste all five at once. Reassure them it's one-time. **Console UI labels are
localized** — if the owner's Google account language isn't English, translate the
quoted labels for them (German: *APIs und Dienste → Bibliothek*, *Anmeldedaten →
Anmeldedaten erstellen → OAuth-Client-ID*, *Computeranwendung*, *Testnutzer*; translate the
others, such as **Publish app**, as you meet them):
- 🧑 a. Open https://console.cloud.google.com → create or pick any project.
- 🧑 b. **APIs & Services → Library** → search & **enable "Google Search Console API"**.
- 🧑 c. **APIs & Services → Google Auth Platform → Audience** → add your Google email
       as a **Test user** (the "OAuth consent screen" was renamed Google Auth Platform).
       Then, on the same page, **Publish app** → Confirm, so the status reads **In
       production**. Say why: while the app is in "Testing", Google ends the sign-in 7 days
       after it is given, so the weekly check would stop after its first week. If the tab
       already reads **In production** or **Internal**, skip Publish and leave it as it is.
- 🧑 d. **APIs & Services → Credentials → Create credentials → OAuth client ID →
       Desktop app → Create → Download JSON**.
- 🧑 e. Tell me where it downloaded (usually `~/Downloads`).

### Step 4 — Your steps ( 🤖 **I do this** )
- 🤖 Move their JSON to `~/.config/gsc-insights/client_secret.json`.
- 🤖 Build the venv + install deps (see SKILL.md's "One-time setup").
- 🤖 Run `gsc_query.py` once — **a browser opens for their consent click**, then
  the token caches and every future run is silent. Google may first warn that it has not
  verified the app: tell them it is their own app, reading only their own Search Console
  data, and that if the screen offers a way on, they take it. Check first that the screen
  names their own app and asks only to view Search Console data; if it asks for more, or
  names another app, stop. Neither the screen nor its wording was checked with a first
  sign-in. If Google blocks the sign-in instead, stop and say so: the app may then need
  Google's verification.

### Step 5 — Confirm the connection in plain words
After the first successful run: *"✅ Connected — Google confirms you own `<site>`
(access: `<permissionLevel>`)."* If the property is freshly verified and the report is
near-empty, **say so honestly** — data accrues over days; that's not a failure.

### Step 6 — THEN teach them how to use it (SKILL.md's "Once connected"). Don't skip this.

### Step 7 — Ask about weekly tracking, for THIS site specifically
Every ad-hoc run now quietly builds position history on its own (every query script
auto-appends to the history CSV), but that still only happens when someone remembers to ask. On
macOS, check `bash scripts/schedule_tracking.sh status <site>` (exact match for this
one domain — not `list`, whose sanitized labels can collide between different domains);
on Linux there's nothing to query (no systemd/cron integration here), so just ask
directly whether they already have a recurring job for this site. If it's not
scheduled, close onboarding by actually asking, not just mentioning it in passing:
*"Want me to also schedule this to check automatically once a week, so you don't have
to remember to ask? Takes one command, and it's specific to `<site>` — nothing else
changes."* Wait for a real yes before running `schedule_tracking.sh install` (SKILL.md's
"Weekly auto-tracking" — never auto-install). A no is a fine, complete answer; don't
re-ask later in the same session. This is a per-site decision — connecting a second
site later means asking again for that one, not assuming the first answer carries over.
The same check applies outside onboarding too: any ranking check on an already-connected
site that comes back "not scheduled" is a prompt to ask, not just a first-connection
step (see SKILL.md's "Once connected — how to use it").

### Step 8 — Offer the AI check (optional, once)
After the weekly-tracking question, and only if the site has no AI check yet
(`~/.config/gsc-insights/venv/bin/python scripts/geo_check.py <site> --check-drift` says "not set up"), offer it in one or two
plain sentences: *"One more, optional: I can also check every week whether ChatGPT and other AI
assistants mention your business when someone asks for what you offer. You prepay once, 5 or 10
dollars or euros, and that covers the checks for weeks."* On a yes, follow `references/geo-check.md` → "Setting
it up". Unlike Google and Bing above, this one can cost money and sends your questions to the AI
companies you choose (through OpenRouter, unless you use each company's own key), so say that plainly. After the first run, show the report page and tell them how to see it
again: *"Just ask me: show me my AI report."* A no is a complete answer; don't re-ask in the same
session.
