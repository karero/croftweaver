# Where cloudflare-api-zones-list-move-token-2026-11-04.json comes from

A real answer from Cloudflare, read on 2026-11-04: `GET /client/v4/zones?per_page=50` with the
token CLOUDFLARE_MOVE.md tells a User to make (Zone Read and DNS Edit on one zone; Cloudflare Pages
Edit and Workers Scripts Edit on the account; an end date).

The account has seven zones and the answer lists all seven. Only the zone the token's Zone
Resources name carries `#dns_records:*`; the six others carry the account-level Workers
permission's reach (`#worker:*`, `#analytics:read`, `#organization:*`, `#zone:read`). The person who made the token reported a DNS read on one of those six
answering 403; that call is not in this file.

Cut and replaced, nothing else edited: three of the seven zones are kept (the site's zone and two
others, in the order the answer gave them); the account's name and id, the zone ids, the zone names and the name
servers are made-up; the registrar and the original name servers are made-up. `result_info` says 3
where the answer said 7, because three entries are left.
