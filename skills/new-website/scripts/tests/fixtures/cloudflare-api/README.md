# Cloudflare's API, as two trials saw it

Each file here is one call to Cloudflare's API from the two trials of the setup script
(`docs/reviews/SKILL-PLAN-cloudflare-setup.md` in the Croftweaver repository, "What is
known, and how"): the request, the status and the answer, as `{ capture, request, status,
response }`. `T1-048` is the first trial's capture 048, `T2-061` the second trial's 061, the
numbers the plan cites. The tests' stub of the API (`../../cloudflare-stub.mjs`) builds its
answers from them, and `cloudflare-setup.test.mjs` replays the captured calls against the
stub and compares.

The captures themselves hold real names and ids and are kept outside every repository.
`clean-captures.mjs` makes these files from them: every name is replaced by the scenarios'
made-up ones (Lena's bakery, `lenas-backstube`), from a private map kept beside the
captures; every id, commit hash and GitHub id by a made-up one, mostly zeros; every commit
message by "Made-up commit message N"; a 64-character hash too. Email fields and the
registrar's nameservers are left out. A test checks every string, key and number in every
JSON file here but `allowed-values.json`: each must be a made-up id, hash, date or commit
message, matched by pattern, or be on that list; a host, an address or a request path passes
when each of its parts does.
Anything else fails, whatever field it is in. Add a value to that list only after looking at it:
the list is what keeps real names out. A second test plants the values earlier versions of the
check let through (a name with an accent, a branch, a hash, a host label) and must see each fail. `T1-021` is an excerpt: every `ad_hoc` deployment (two
uploads and one that Cloudflare built) and one push build of each environment, from the six
pages of a live project's deployments (T1-021 to T1-026); it says so in its `excerpt` field.
The deployment call's request (T1-030 and the others) is the empty form the trial's helper
sent, recorded as `emptyForm` and read from the helper itself: `trial-helper.txt` is that
helper, with its two local paths replaced. `T1-019`, the account's list of projects, has each
item's latest and canonical deployment set to null: they hold another site's history.

## Which file backs which claim

| The plan's claim | Files |
|---|---|
| A project created with a `source` builds from GitHub; creating it starts no build | T1-027, T1-028 |
| The list of projects holds each project whole: source, domains, settings; a Direct Upload project has no source; a name is not always the first part of the address | T1-019 |
| The deployment call with an empty form builds the head of the production branch, as production, `ad_hoc` | T1-030 |
| A second call while the first is queued starts a second build | T1-031, T1-033, T1-040 |
| A Cloudflare build has `clone_repo` and `build` `success`; an upload has them `idle` | T1-021, T1-040 |
| A PATCH holding only the change keeps every other variable, the build settings, the production branch and Fail open, and every secret by name; a secret's value reads back empty, so whether the value is kept is not shown here (the first real site is to show it) | T1-048 to T1-053, T1-061 |
| Fail open for one environment alone is refused, code 8000066 | T1-050 |
| A changed production branch is also the source's; a deployment records the production branch of its time | T1-052, T1-054, T1-055 |
| A deployment records its variables, a secret by name with its value empty, and its build settings | T1-030, T1-062, T1-063 |
| Token verify: no `expires_on` for a token with no end date | T1-001, T1-003, T1-064, T1-148, T2-001 |
| A refused read: 403, code 10000, no reason; a zone's `permissions` are not the token's | T1-014, T1-015, T1-018 |
| Zone settings: a PATCH of `{"value": …}`, read back; NEL's value is `{"enabled": false}` | T1-067 to T1-078 |
| An empty zone's defaults: Always Use HTTPS off, TLS 1.0, obfuscation on, NEL on | T2-035 to T2-039 |
| Bot Management's fields; a PUT of the zone's own values changed nothing | T1-013, T1-079 to T1-081 |
| A PUT that changes a value works and keeps the fields it leaves out; `is_robots_txt_managed: true` is refused, 10400 | T2-040, T2-059 to T2-066, T2-073, T2-077 |
| The header rule: a PUT with the existing rule kept it, its id and its version | T1-082 to T1-084 |
| A missing response-header ruleset answers 10003; one PUT creates it with one rule; the add-rule call appends and leaves the first rule as it was | T2-018, T2-023 to T2-025, T2-041, T2-067 |
| A second TXT at a name is accepted; an identical one is refused, 81058; a second address record, 81053 | T1-143 to T1-146 |
| The zone list shows a token's reach: eight zones, then one once narrowed | T2-002, T2-011 |
| The accounts list is empty with the plan's rows | T2-003 |
| With previews off, a push to a pull request leaves a skipped `github:push` deployment; a push to the production branch builds | T2-021, T2-022, T2-026, T2-028, T2-029 |

| Attaching a domain creates no record: `initializing`, then `pending` with "CNAME record not set" | T1-085, T1-086, T1-130, T1-131, T2-043, T2-044 |
| A proxied CNAME to the `pages.dev` address turns the domain `active`; its verification turns active first | T1-104, T1-127, T1-141, T1-142, T2-055, T2-056 |
| Attaching keeps the host's A record; one PATCH turns it into a proxied CNAME, with a comment, and keeps its id. Cloudflare's answer to that PATCH says changing a record's type is deprecated | T1-129, T1-132, T2-042, T2-045 to T2-047 |
| A record comment holds 100 characters; 101 is refused, code 9313 | T2-057, T2-058 |

T1-102, the zone's list of records on launch day, is not here: it is the live zone's mail and
other records. `clean-captures.mjs` takes the captures in two batches, the setup stage's and
then the launch stage's, and gives the second its made-up ids after the first, so adding it left
the first batch's files as they were.
