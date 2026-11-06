# Where the initializing and pending domain lists come from

Two real answers from Cloudflare, read on 2026-11-05: the same `GET .../pages/projects/<project>/domains`
as `cloudflare-api-pages-domains-2026-11-05.json`, polled every 3 to 4 seconds while two domains were
added to a Pages project (an undo). Hosts, ids and the zone tag are made up; nothing else is edited.

- `...-initializing-...`: the first seconds. Both entries have `status` `initializing`; the apex's
  `verification_data` says `CNAME record not set`, seconds after its CNAME was written.
- `...-pending-...`: later. Both entries have `status` `pending`, `verification_data.status` `active`.

What the poll showed, by hand: the list holds a domain 2 seconds after it is added, as `initializing`;
`pending` came about a minute later and `active` about 80 seconds after that. The project's own
`domains` held a host only from the moment it was `active`. Both hosts served Pages while still
`pending`.
