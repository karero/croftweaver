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
message by "Made-up commit message N". Email fields and the registrar's nameservers are left
out. A test checks every id, address, host, account, repository, project and commit message
in these files against the made-up values, and every free-text string against a list, so a
value the cleaner missed fails it. `T1-021` is an excerpt: every `ad_hoc` deployment (two
uploads and one that Cloudflare built) and one push build of each environment, from the six
pages of a live project's deployments (T1-021 to T1-026); it says so in its `excerpt` field.
The deployment call's request (T1-030 and the others) is the empty form the trial's helper
sent, recorded as `emptyForm`.

## Which file backs which claim

| The plan's claim | Files |
|---|---|
| A project created with a `source` builds from GitHub; creating it starts no build | T1-027, T1-028 |
| The deployment call with an empty form builds the head of the production branch, as production, `ad_hoc` | T1-030 |
| A second call while the first is queued starts a second build | T1-031, T1-033, T1-040 |
| A Cloudflare build has `clone_repo` and `build` `success`; an upload has them `idle` | T1-021, T1-040 |
| A PATCH holding only the change keeps every other variable and secret, the build settings, the production branch and Fail open; a secret reads back empty | T1-048 to T1-053, T1-061 |
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

Not here yet, since only the launch stage uses them: attaching a domain and its statuses
(first trial 085 to 142, second trial 042 to 056) and a record's comment and its length
(second trial 046, 047, 057, 058). They come with the launch stage.
