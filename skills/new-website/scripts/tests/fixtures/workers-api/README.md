# Cloudflare's Workers API, as row 0.4 saw it

Each file is one call to Cloudflare's API from the checks of row 0.4 (Croftweaver's
`workers-for-new-sites/PLAN-setup-workers.md`, C1 to C7), as `{ capture, request, status, response }`:
`R04-002` is the second capture kept from them. The tests' stub of the API (`../../cloudflare-stub.mjs`) builds
its Workers answers from them.

The captures themselves hold a real account, zone and host and are kept outside the repository. These
files hold made-up values only: the account, the zone, the Worker and every id are the bakery's
(`lenas-backstube.example`), numbered as `../cloudflare-api` numbers them. A test
(`cloudflare-setup.test.mjs`, "every string, key and number in the Workers fixtures") fails on any value
that is neither made up by pattern nor on `allowed-values.json`.

| File | What it is |
|---|---|
| `R04-001` | the account's workers.dev subdomain |
| `R04-002` | a Worker's deployments, two uploads from wrangler (C2) |
| `R04-003` | the deployments of a Worker that does not exist: 404, code 10007 (C2) |
| `R04-004` | the deployments of a Worker Builds made from its template: two `dash_template` uploads (C4) |
| `R04-005` | the account's domains on Workers |
| `R04-006` | a read refused for want of Workers Scripts Edit: 403, code 10000. It is the answer of the scripts list; the deployments read answers the same way (C2) |
| `R04-007` | the attach over an existing address record: 409, code 100117 (C3) |
| `R04-008` | a DNS record deleted |
| `R04-009` | the attach: the domain made |
| `R04-010` | the record Cloudflare makes for it: a read-only AAAA `100::` |
| `R04-011` | the domain removed: 204 |
| `R04-012` | the record put back with a POST of its eight fields, reading back equal |

What is MADE, not captured: the id, strategy and versions of the `R04-004` deployments (the capture kept
only their source and time); the zone's DNS export text (the capture kept a note: BIND text with an SOA
line), which the stub writes itself.
