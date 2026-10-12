# Does AI name you? — the weekly GEO check

More and more buyers ask an AI assistant instead of searching Google: *"Where can I buy
sourdough bread in Schwabing?"* This check asks the AI engines exactly that kind of
question every week, **without naming the business**, and counts how often the business
comes up in the answer. It is the AI-age twin of "where do I rank on Google".

Script: `scripts/geo_check.py`. The weekly `track.sh` runs it after Google and Bing.
The design and its review: `docs/reviews/SKILL-PLAN-geo-check.md` in the Croftweaver repo.

**Quick path** (a site that is already set up). Run these with `~/.config/gsc-insights/venv/bin/python scripts/geo_check.py <domain> …`:

1. `--check-drift`: is the question still right? (see "Every session")
2. no flag: ask the engines (a few minutes); `--engines google-ai-mode,gemini` asks only the listed engines.
3. `--report`: the owner's page. `--trend`: week over week.

Three rules that are easy to miss: say **"N of M"** with the numbers from the report, because not
every assistant is asked both ways; never answer the questions yourself or through a coding
assistant (see "Why the engines are asked blind"); commit results only to a **private** repo.

**Contents** (the sections of this file, in order, with shortened names): What it measures · The engines, and how to pay for them
(costs, HTTP 402) · Setting it up · Every session: is the question still right? · Reading the
results (why 0 from memory, stray copies, handing over) · Why the engines are asked "blind" ·
Engines: request shapes (for maintenance).

## What it measures — two columns per engine

| Column | How it asks | What it tells the owner |
|---|---|---|
| **Knows you** | no web search — the model answers from what it learned in training | Whether the AI already "knows" the business. The long-term goal. Judge it over several weeks, not from one week to the next: a single run is only 3 answers per question. |
| **Finds you** | web search switched on | What a buyer actually gets today, and which sites the engine cited (for Perplexity, the check can only tell which search results it returned, not which of them it quoted). Can move week to week. If it cites directories or review sites instead of the owner's site, that is the next job (see `business-listings-setup`). |

Each engine gets up to three questions:

- **broad**: the buyer's everyday question
- **narrow**: the same question with the niche or neighbourhood
- **branded**: *"What is <name>?"*, as a sanity check

Broad and narrow get 3 answers each per run, because AI answers vary. The branded question
gets one answer. It is **never scored**, because an answer repeats the name even when it
says "I don't know it". Read it instead to see whether the engine describes the business
correctly.

## The engines, and how to pay for them

**The simple way (the default): one OpenRouter key.** OpenRouter is a service that passes
the questions on to ChatGPT, Claude, Gemini and Perplexity, and bills all four from **one
prepaid balance**. It uses each assistant's **own** web search, so "ChatGPT with web search on"
is what a ChatGPT user gets. The owner tops up once (5 or 10 USD/EUR is plenty to start; see
Costs for how long that lasts) and adds one key. They pay what the AI companies charge, plus
a top-up fee (5.5%, at least $0.80); OpenRouter says it doesn't store the questions or answers
by default.

| Assistant | From memory | With web search on | Key (in `~/.config/gsc-insights/.env`) |
|---|---|---|---|
| ChatGPT, Claude | ✓ | ✓ | `GEO_OPENROUTER_API_KEY` (or a direct key, below) |
| Gemini | ✓ | — (see below) | `GEO_OPENROUTER_API_KEY` (or a free direct key) |
| Perplexity | — via OpenRouter; ✓ with a direct key | ✓ | `GEO_OPENROUTER_API_KEY` (or a direct key) |
| Google AI Mode, AI Overview | — | ✓ | `SERPAPI_KEY` (optional, the same key as the Top-10 check) |

- **With an OpenRouter key, it is used for all four chat assistants.** Direct keys
  (`GEO_GEMINI_API_KEY`, `GEO_OPENAI_API_KEY`, `GEO_ANTHROPIC_API_KEY`,
  `GEO_PERPLEXITY_API_KEY`) are only used when there is no OpenRouter key, or for the assistants
  named in `GEO_DIRECT_ENGINES` (for example `GEO_DIRECT_ENGINES=gemini,perplexity`: those two
  use their own keys, ChatGPT and Claude stay on OpenRouter; a named assistant without its own key
  stays on OpenRouter). Reasons to name one: Gemini's free direct key instead of paid credit, and
  Perplexity's "from memory" column plus the site's country sent with its search. The report says which route each assistant went through, and a switch
  between routes is marked in the trend.
- **Through OpenRouter, this check sends no country with the web searches.** For ChatGPT and Claude
  it asks OpenRouter's `web` plugin (engine `native`) to search, and OpenRouter's documentation
  (openrouter.ai/docs/guides/features/plugins/web-search) shows no location setting for that
  plugin; Perplexity's model searches by itself, with no plugin. The direct keys send the country.
  OpenRouter's documentation, read 2026-10-09
  (openrouter.ai/docs/guides/features/server-tools/web-search), describes a newer web search
  server tool, `openrouter:web_search`, still in beta, whose `user_location` takes a country, city,
  region and timezone. It works only with a provider's own search and is ignored with OpenRouter's
  Exa, Firecrawl, Parallel and Perplexity search. This check does not use it: it is in beta, and
  nobody has captured a request showing that it changes the results.
  For a local business this barely matters, because its questions name the place
  ("… in Munich-Schwabing"). A business that sells everywhere gets search results without a
  country, which can lean towards the US; if that matters, use direct keys or name the market in
  the question.
- **Perplexity through OpenRouter only answers "with web search on".** Its model always searches
  by itself, so there is no "from memory" answer to collect on that route (checked: even "What is
  2 + 2?" came back with 20 web sources).
- **A free start:** a direct Gemini key from Google AI Studio costs nothing (outside the EU/UK/CH)
  and gives Gemini's "from memory" column. Everything else needs a paid route.

Every engine is optional. Without a key an engine is skipped with a one-line hint; the report
says e.g. "1 checked, 0 failed, 5 not set up". The script reads **only** these names, never a
generic `OPENAI_API_KEY`, so a key someone exported for other work is never billed by accident.
`--engines google-ai-mode,gemini` asks only the listed engines for one run.

**Google's own AI answers** come through SerpApi: **AI Mode** (Google's chat-style answer) and
the **AI Overview** (the box above the normal results). Both are live Google search by nature,
so they only have "finds you", and each question is asked **once** per run rather than three
times. That is a cost choice (every call spends a paid SerpApi search), and it makes Google's
line a thinner signal: judge it over several weeks. Google doesn't show an AI Overview for every question; when it shows none, the
line says "Google showed no AI Overview". That is useful to know in itself, and it isn't the
same as "not named". SerpApi collects Google's results automatically, and the risk under
Google's terms is SerpApi's business model (this skill already relies on it for the Top-10
check); the Gemini clause above covers only the Gemini API.

**Why Gemini has no "Finds you".** Google's terms for search-grounded Gemini answers say:
"You will not, and will not allow your end user or any third party to, cache, frame,
syndicate, resell, analyze, train on, or otherwise learn from Grounded Results". Counting
mentions and keeping the answers to compare week to week is exactly that, so Gemini is
only asked without search. Answers without search are not covered by that clause.

**The free path, and its limit.** A free Gemini key gives "Knows you" only. For "Finds you"
the owner needs one paid key: one OpenRouter key covers all four assistants; see Costs.

**EU / UK / Switzerland (a cautious reading, not legal advice).** Google's terms say: "You
may use only Paid Services when making API Clients available to users in the European
Economic Area, Switzerland, or the United Kingdom." Whether an owner running this script
for themselves counts is unclear. So tell owners there: **turn on billing for the Gemini
key**. At this volume that should cost next to nothing, but check the pricing page.

**When prepaid credit runs out (HTTP 402).** What happens and what to top up depends on the route
(see "The simple way" above):

| Route | What stops | Top up | Rerun |
|---|---|---|---|
| **Gemini on its own key** (no OpenRouter key, or `GEO_DIRECT_ENGINES` names it) | Gemini only; the other assistants run normally | Google AI Studio, the project **the key belongs to**, then its billing page | `~/.config/gsc-insights/venv/bin/python scripts/geo_check.py <domain> --engines gemini` |
| **Through OpenRouter** (the default for the four chat assistants) | **All** assistants on that route, for the run | openrouter.ai, Credits | the same command without `--engines`, or `--engines` naming the assistants that failed |

The own-key run prints `gemini FAILED: HTTP 402: Your prepayment credits are depleted.` (seen on a
real run, 2026-10). The top-up pages, taken from that error text, are https://ai.studio/projects and
Google's explanation at https://ai.google.dev/gemini-api/docs/billing#prepay (button names may
differ from what is on screen).

What the history keeps: a failed engine writes its rows, marked failed ("N of M failed"), and the
trend shows "latest attempt failed" next to the last good numbers. History keeps one row per
engine, mode, question and settings per day, and never swaps a better row for a worse one. So a
rerun **on the same day with the same settings** replaces the failed rows, and a failure that
comes **after a good run on the same day** (same settings) is not recorded at all (the run's own "FAILED" line is then the only trace). A
rerun on a later day leaves the earlier day's failed row in place. None of this needs editing by hand.

### Costs (measured 2026-09-26 through OpenRouter; prices change, so recheck on openrouter.ai)

A full weekly check for **one site** asks ChatGPT, Claude, Gemini and Perplexity 42 times in total.
Through OpenRouter it cost **$0.72 a week per site**. The top-up fee comes on top when buying credit:
5.5%, at least $0.80, so a $5 top-up costs $5.80 and a $10 top-up $10.80.

| Prepaid once | Lasts for one site | For three sites |
|---|---|---|
| 5 USD/EUR | about 6 weeks | about 2 weeks |
| 10 USD/EUR | about 13 weeks | about 4 weeks |

Where the money goes: nearly all of it is ChatGPT's and Claude's **web search** answers (about
$0.05 each: the pages they read count as input). Answers from memory cost fractions of a cent;
Perplexity's searches about half a cent. OpenRouter's **Activity** page shows every call and its
cost, and each weekly run prints its own total ("cost of this run via OpenRouter").

Google AI Mode and AI Overview (if switched on) come on top: 6–9 SerpApi searches per site per
week, from the SerpApi plan's monthly allowance.

Override any model with `GEO_<ENGINE>_OPENROUTER_MODEL=...` (OpenRouter route) or
`GEO_<ENGINE>_MODEL=...` (direct keys) in `.env`. **Providers retire models**
(Claude Haiku 4.5 retires around 15 Oct 2026), and a retired model shows up as a weekly
"FAILED" line. The fix is to set a current model there. Changing a model marks the next
trend line "model changed".

## Setting it up (🧑 owner, 🤖 you)

Sell it first, in plain words, then ask:
*"Want to know if ChatGPT and other AI assistants mention your business when someone asks
for what you offer? I can check that every week, next to your Google rankings. You prepay
once, 5 or 10 dollars or euros, and that covers the checks for weeks."*

1. 🤖 **Draft the questions.**
   - Read the live homepage and `POSITIONING.md` (if the site repo has one).
   - Write a **broad** and a **narrow** buyer question in the site's language, the way a real customer would type it.
   - For a **local** business, **name the place** in both: engines without location settings (Gemini, and any assistant asked through OpenRouter) otherwise answer for anywhere. A business that sells everywhere (an app, an online shop) leaves the place out.
   - Never put the business name in them.
   - Also write the **branded** question.
   - Show all three to the owner and ask them to confirm or change the wording.
2. 🤖 **Prepare the key file**: run `~/.config/gsc-insights/venv/bin/python scripts/geo_check.py --prepare-env`, then
   `open -e ~/.config/gsc-insights/.env`. The first adds the empty lines (`GEO_GEMINI_API_KEY=`
   and so on) without touching anything already there. The second opens the file in TextEdit.
   Tell the owner where it lives in words they can use. The `.config` folder is hidden in Finder:
   **Go → Go to Folder…** (⇧⌘G), then `~/.config/gsc-insights`, or ⇧⌘. to show hidden files.
3. 🧑 **Get the key — usually just one.** Explain the choice in plain words first:
   *"The simplest way is one account at OpenRouter: you prepay once, 5 or 10 dollars or euros,
   and it pays ChatGPT, Claude, Gemini and Perplexity for you from that balance, for weeks. If you'd
   rather start free, a Gemini key costs nothing but only shows what Gemini knows from memory."*
   Hand over the steps, wait until the owner says it's done, then run
   `~/.config/gsc-insights/venv/bin/python scripts/geo_check.py --keys` (it shows "set ✓" or
   "empty", never the key itself). **Never ask for a key in the chat.** If a key is pasted there
   anyway, tell the owner to delete it at the provider and make a new one.

   Button names come from the providers' pages (checked 2026-09) and may be worded slightly
   differently on screen; say so.

   **OpenRouter (the default: one key for all four)**
   1. openrouter.ai → sign in (a Google login works).
   2. **Credits → Add credits**: 5 or 10 USD/EUR. That is a one-time top-up, not a subscription;
      it lasts for weeks (see Costs). OpenRouter's fee is 5.5%, at least $0.80, so $10 is the better value.
   3. **Keys → Create Key**, name it "AI check". Setting a **credit limit** on the key (for
      example the amount just added) means it can never spend more. Don't set it below a
      few dollars, or calls get refused.
   4. Copy the key and paste it after `GEO_OPENROUTER_API_KEY=`, with no space and no quotes. Save (⌘S).
   5. Later, **Activity** on openrouter.ai shows every call and what it cost.

   **Gemini direct (free, "from memory" only; optional)**
   1. aistudio.google.com → **Get API key** → **Create API key**; pick the project AI Studio already
      created (usually "Gemini API").
   2. In the EU/UK/Switzerland: **Set up billing** for that project (see the EU note).
   3. Paste it after `GEO_GEMINI_API_KEY=`. With an OpenRouter key set, OpenRouter is used instead,
      unless `GEO_DIRECT_ENGINES` names gemini.

   **Direct keys per provider (advanced; used without an OpenRouter key, or for the assistants
   `GEO_DIRECT_ENGINES` names)**: OpenAI
   (platform.openai.com → Billing → API keys → Create, restricted to "Model capabilities: Write"),
   Anthropic (console.anthropic.com → Billing → API Keys), Perplexity (perplexity.ai → Settings →
   API). Each needs its own prepaid credit. The only reason to prefer them: Perplexity's "from
   memory" column, which OpenRouter can't provide.

   **SerpApi (Google's AI answers, optional)**: if the owner already set up the Top-10 check,
   `SERPAPI_KEY` is already there. Otherwise: serpapi.com → sign up → Dashboard → copy "Your
   Private API Key" → paste it after `SERPAPI_KEY=`. Either way, Google is **off until the owner
   switches it on for the site**, because it spends paid searches: ask first, then run
   `~/.config/gsc-insights/venv/bin/python scripts/geo_check.py <domain> --google on`.
4. 🤖 **Save the site and its questions** with the confirmed wording. Write each question to a
   small text file first. Never put it inside a shell command string: an apostrophe
   ("contacts' plans") breaks the quoting.
   ```bash
   ~/.config/gsc-insights/venv/bin/python scripts/geo_check.py example.com --init --name "Bäckerei Example" \
       [--legal-name "..."] [--alias "..."] --lang de --country DE
   ~/.config/gsc-insights/venv/bin/python scripts/geo_check.py example.com --set-question --slot broad   --text-file broad.txt
   ~/.config/gsc-insights/venv/bin/python scripts/geo_check.py example.com --set-question --slot narrow  --text-file narrow.txt
   ~/.config/gsc-insights/venv/bin/python scripts/geo_check.py example.com --set-question --slot branded --text-file branded.txt
   ~/.config/gsc-insights/venv/bin/python scripts/geo_check.py example.com --check-drift
   # read the homepage text it prints with the owner, then save exactly that page:
   ~/.config/gsc-insights/venv/bin/python scripts/geo_check.py example.com --confirm --expect <page code>
   ```
   - `--name` comes from the site's `src/config.ts` (`SITE.name`); `--legal-name` from `SITE.legalName`.
   - Add an alias for each other spelling the owner uses ("ExampleCo" for "Example-Co").
   - To change names later: `--set-names --alias "..."` **adds** an alias; `--set-names --name "..."`
     replaces the whole list (name, then any `--legal-name` / `--alias` given with it). Either
     marks the next trend line "settings changed".
   - `--domain` defaults to the site's domain.
   - `--check-drift` prints the homepage's title, description and main heading, and a **page code**. Read them with the owner;
     only if it is the real homepage (not a cookie banner or a "checking your browser" page) run
     `--confirm --expect <page code>`. It saves only if the page still matches that preview.
5. 🤖 **Run it once** (`~/.config/gsc-insights/venv/bin/python scripts/geo_check.py example.com`), then open the report
   (`--report`) and walk the owner through it. It takes a few minutes with every engine on. If an engine shows FAILED, read its
   reason: "HTTP 401/403" means the key or its permissions; "HTTP 429" means rate limit or no credit; "HTTP 402" means prepaid credit ran out (see "When prepaid credit runs out" above; on OpenRouter it stops every assistant that goes through it).
6. 🤖 If the site isn't on weekly tracking yet, **ask** (SKILL.md "Weekly auto-tracking"). The AI check rides along with it.

## Every session: is the question still right?

The questions only mean something while they match what the business sells. **At the start
of any session that looks at this site's AI results, run
`~/.config/gsc-insights/venv/bin/python scripts/geo_check.py <domain> --check-drift`.** It prints the homepage's title,
description and main heading, and says whether they changed since the questions were confirmed.

- **State: same.** Go on.
- **State: changed.** Read the homepage and POSITIONING.md, then show the owner each saved question next to a proposed replacement. Ask: *"Your homepage changed. Should I keep asking the AI engines these questions, or switch to these?"*
  - **Switch:** `--set-question` for each changed slot, then `--confirm --expect <page code>`.
  - **Keep:** `--confirm --expect <page code>` only.
  - First check that the "now" text really is the homepage: under this design a cookie or bot
    page also lands in "changed". If it isn't, don't ask about questions; say the page couldn't
    be read properly this time.
  - A changed question gets a new revision. Its next trend line is marked "question changed", because the old and new numbers aren't comparable.
- **Couldn't read the homepage.** Tell the owner, and don't `--confirm`.
- **State: unconfirmed.** A question was changed (or never checked) since the last `--confirm`.
  Review the questions against the homepage with the owner, then `--confirm --expect <page code>`.
- **`--confirm` always needs `--expect <page code>` from a `--check-drift` you and the owner
  just read.** If that text isn't the business's real homepage (a cookie banner, "checking your
  browser", a login wall), don't confirm: tell the owner and try again later. The code rejects only pages that fail to load or name neither the business nor its
  domain anywhere in their text (including the title and hidden elements); everything else is your judgment.

The unattended weekly job never changes questions. On a changed homepage it runs the old
ones, keeps the week's data and logs a warning. Asking is this session's job.

## Reading the results

**The owner's way in:** they ask *"Show me my AI report for example.com"* (or "how is my
business doing with AI?"). Run `~/.config/gsc-insights/venv/bin/python scripts/geo_check.py <domain> --report`: it builds
one page from each assistant's latest answers and opens it in the browser. The page is written
for the owner, so let it speak first, then add two or three sentences of your own:

- **At the top:** how many assistants named the business at least once with web search on, and
  how many from memory, with one plain sentence each. Only answers that count go into these
  numbers: to the current question, from an assistant that is on now, that actually came back.
  "In every answer to every question" means exactly that; a 1-of-3 is "at least once".
- **"How to read this":** what was asked (and that it checks whether the name appears, not
  whether the assistant recommends it), what "with web search on" and "from memory" mean, and why
  each question is asked 3 times: an assistant can write a different answer each time.
- **One table per question:** ✓ named in every answer, ◐ sometimes, ✗ not named, ! no answer this
  time (the weekly log says why), — Google showed no AI answer, — not asked (with the reason),
  plus whether their own website was a source (for Perplexity, among its search results) and how
  many answers failed. `*` marks an answer
  to an earlier version of the question. The answers are folded away under "Read what they said".
- **"Do they describe you correctly?":** the branded answers, to read, never counted.

Each weekly run writes a new page in `~/.config/gsc-insights/geo/reports/<domain>/`; an older
page is not updated. If the owner wants the latest without asking you, it is the newest file
in that folder.

For the week-over-week movement, `~/.config/gsc-insights/venv/bin/python scripts/geo_check.py <domain> --trend` (track.sh prints
it every week):

```
gemini     knows you broad   named 0/3 (2026-09-28) → 1/3 (2026-10-05) ▲
openai     finds you broad   named 1/3 (2026-09-28) → 3/3, cited 2/3 (2026-10-05) ▲
anthropic  finds you narrow  named 2/3 (…) → 2/3, cited 0/3, searched only 1/3 (…) →  ‡ model changed — not directly comparable
```

- **named 2/3**: the business was named in 2 of the 3 answers.
- **cited 2/3**: the owner's own site was among the cited sources in 2 of 3. For ChatGPT, and for
  Claude on its own key, the captured answers tie each citation to the text. For Claude through
  OpenRouter and for Google's AI Overview the captures show a source list with no offsets or marks
  to check it against, and Google's AI Mode tags only some of its blocks with the references they
  use. Whether those lists hold only the sources the answer quotes is not verified, so "cited"
  there means "listed as a source". A paired capture would settle it: the same question through
  OpenRouter and through Claude's own key, or Google's references next to the answer as Google
  shows them.
- **in its results 2/3**: what the trend says for Perplexity instead of "cited". In the captured
  answer from its own key, Perplexity returned the search results it retrieved with no annotations
  and no [n] markers, so this check cannot tell which of them the answer quotes. Through
  OpenRouter the captured text marks the quoted ones with [1], [2]…, which index the list, but the
  list it came with is longer than the marks (18 pages, 10 marked), no entry carries an offset
  into the text, and this check does not read the marks. Either way the number is how often the owner's site was among the
  results (once per answer, however often it appears). Because the results include more than
  the quoted ones, it can be higher than a citation count would be. The report words it the
  same way ("your website was among its search results") and captions the list "Search results
  returned".
- **searched only 1/3**: the engine answered from memory in the other two, even with search on. Those answers are closer to "knows you".
- **‡ …**: a change that makes the two numbers not directly comparable: the question, the model, the settings (names, domain, country), or the route (direct key ↔ OpenRouter).
- **latest attempt failed**: the last run for that line didn't get an answer. The numbers shown are the last good ones, with their dates.

Every answer is saved verbatim with its sources under
`~/.config/gsc-insights/geo/answers/<domain>/<run>/`. Quote from those files when explaining a
result, and read the branded answers for accuracy.

**Why "from memory" is usually 0 at first, and what to tell the owner.** A model is
much more likely to "remember" a name it saw in many independent places before it was trained:
press, listings, other people's pages. Wikipedia is one such source, not the only one, and the
owner's own site is one among many. These are general explanations, not something this check
measures, so offer them as the usual reasons, not as proof. Two usual reasons for 0, and a third
that says how long to wait:

- **A young site.** If the website launched recently, most models were trained before it existed.
  Ask the owner when it went live; a business can be years old and its site still new to the models.
- **Small models.** The cheaper, faster model of an assistant tends to know fewer niche names. The
  first line of each saved answer file names the model that answered (for example `model=…-flash-lite`).
- **Retraining is slow.** This column mostly moves when a new model is released, so judge it over
  months, not weeks. Never promise the owner a date for being "in the models".

A sentence the owner can use as is, with the numbers from the latest report: *"[N] of [M] assistants
named us from memory. That is normal for a business this size. An assistant only 'remembers' a
name that appeared in many places before it was trained. [Only if true in the latest run: When the
same assistants can search the web, all of them find us.]"* Take every number from the report, not
from this text: not every assistant is asked both ways. Gemini is never asked with search.
Perplexity through OpenRouter is only ever asked with search (no "from memory" answer exists on
that route). So count the assistants actually asked each way, and keep the last sentence only if
every one of them was asked with search and found the business. A hand-asked Gemini answer can
back the claim for Gemini; say that it was asked once by hand.

**Look for stray copies of the owner's site.** The listed sources can reveal an address the owner
may have forgotten: a hosting preview such as `*.workers.dev`, `*.pages.dev`, `*.vercel.app`,
`*.netlify.app` or `*.github.io` that serves the same site. Cheap check over the saved answers:

```
rg -o -N --no-filename -i -P '[a-z0-9.-]+\.(workers\.dev|pages\.dev|vercel\.app|netlify\.app|github\.io)(?![a-z0-9-]|\.[a-z0-9-])(/[^ )"<>,;]*)?' \
  ~/.config/gsc-insights/geo/answers/<domain>/ | sort | uniq -c
```

`-P` needs a ripgrep built with PCRE2; if it says so, drop `-P` and the `(?!…)` part (you then get a
few false matches such as `foo.github.io.example.com`).

The counts only show how often an address was listed (the same answers repeat it), not how many
copies exist. It also lists other people's addresses (another business's site on `vercel.app`);
look only at ones that carry the owner's name, and strip a trailing `.` before opening one. Open the
full URL from the saved answer. An engine citing an address shows that it exists, not that it
still works, so say nothing until you have opened it. If it serves the site, **ask the owner**
whether that copy is meant to exist before suggesting any change; it may be intentional.

**Hand the results over as files in the owner's repo.** The reports and answers sit in the hidden
`~/.config/gsc-insights/` folder, which the Claude desktop app may not open (links into it did not
open when tried once), so a link to a path there may do nothing for the owner. Copy the report
page(s) and the answers of the run into the site's repo (for example `docs/geo/<date>/`), put the
readable summary next to them, and send the files to the owner.

- **Keep them out of a public repo.** The reports and answers hold the questions, the answers
  word for word, and every listed source. Commit them only to a **private** repo; for a public one,
  send the files to the owner and commit nothing, or commit only a summary you wrote.
- **The "Also see" link breaks in a copy.** A report page may link to the Google page by a relative
  path (`../../../reports/<domain>/google.html`). In the copy that link does not work; tell the
  owner so, rather than letting them find a dead link.
- **Before moving or deleting a file** another session or a note might point at, search for its
  path first.

When the broad question has named nobody for about four weeks, suggest the owner focus on
the narrow one. The owner decides.

How to **improve** these numbers is `ai-seo`'s job (and `business-listings-setup` for
the directories an engine cites). This check only measures.

## Why the engines are asked "blind"

The script sends the bare question. No system prompt, no chat history, no account memory: those
are features of the consumer apps, not the APIs. That keeps it repeatable and close to a
first-time buyer. It is not proof of what the ChatGPT app would say to a particular person;
a mention via the API is good evidence, not a guarantee.

**Never answer the questions yourself, and never run them through a coding assistant in the
site's repo.** Those see CLAUDE.md, memory and the conversation, which all describe the
business.

For a manual spot check in the apps, use a private mode: ChatGPT "Temporary chat", Claude
"Incognito chat", Gemini with activity turned off.

## Engines — request shapes (for maintenance)

Checked against the providers' docs on 2026-09-26:
- **OpenRouter (the default route):** `POST https://openrouter.ai/api/v1/chat/completions`, `Authorization:
  Bearer`, models `google/gemini-3.5-flash-lite`, `openai/gpt-6-luna`, `anthropic/claude-sonnet-5`,
  `perplexity/sonar`. "Finds" adds `plugins: [{"id": "web", "engine": "native"}]` (the provider's own
  search; Perplexity's Sonar gets no plugin, it always searches and has no native option there).
  `max_tokens: 4000` (without it OpenRouter reserves credit for 65k tokens and refuses small
  balances) and `usage: {"include": true}` (the reply carries its real cost). Citations are
  `choices[0].message.annotations[type=url_citation]`, else the top-level `citations` (some
  replies list their sources only there). For Perplexity the list is every source it came with,
  not only the ones its text marks.
  "No credit" arrives as HTTP 402 and stops the whole route for that run.

- **Gemini:** `POST …/v1beta/models/{model}:generateContent`, key in the `x-goog-api-key` header; the answer is in `candidates[0].content.parts[].text` and the model in `modelVersion`. No tools (see the terms above).
- **OpenAI:** Responses API `POST /v1/responses`, `store: false`. For "finds": the `web_search` tool with `user_location: {type: "approximate", country}` (omitting it silently means United States) and `tool_choice: "required"`. Citations are `url_citation` annotations; a `web_search_call` output item means a search ran.
- **Anthropic:** `POST /v1/messages`, `anthropic-version: 2023-06-01`. For "finds": the `web_search_20250305` tool (works on every current model) with `user_location`. Citations are on the text blocks, and `usage.server_tool_use.web_search_requests` counts searches. An org admin can disable web search, which makes these calls fail with a 400.
- **Google AI Mode / AI Overview (SerpApi):** `GET https://serpapi.com/search` with
  `engine=google_ai_mode` (answer in `reconstructed_markdown` or `text_blocks[]`, sources in
  `references[].link`) or `engine=google` (the `ai_overview` block, whose `page_token` sometimes
  requires a second call with `engine=google_ai_overview` within ~4 minutes). `no_cache=true`,
  `gl` = country, `hl` = language. The key is a query parameter, so errors are redacted. SerpApi
  also reports failures inside an HTTP 200 `{"error": ...}`.
- **Perplexity:** the Agent API `POST /v1/agent`, which replaced Sonar chat completions (retired 2026-09-27). The model is named directly (a preset keeps search on regardless). "Finds" adds the `web_search` tool with `user_location: {country}`. Sources are in `output[type=search_results].results[]`.

Tests: `scripts/tests/test_geo_check.py` (the pieces) and `test_track_entry.py` (the weekly
job, end to end), both against a local stub. No real engine is called.
