# Where cloudflare-api-zones-list-account-only-token-2026-11-08.json comes from

A real answer from Cloudflare, read on 2026-11-08: `GET /client/v4/zones?per_page=50` with a
token its maker made with account permissions only, as far as they could tell (Cloudflare Pages
Edit and Workers Scripts Edit; the token's own permission list was not read). The move script
refused it on 2026-11-07 because more than one zone reached DNS.

The account has seven zones and the answer lists all seven. Every one of them carries
`#dns_records:edit` and `#dns_records:read`, beside the Workers permission's reach (`#worker:*`,
`#analytics:read`, `#organization:*`, `#zone:read`, `#domain:read`). Which token permission put
the DNS reach there is not known. Whether the token can in fact edit those records was not tested.

Cut and replaced, nothing else edited: three of the seven zones are kept, in the order the answer
gave them; the account's name and id, the zone ids, the zone names, the plan id and the name
servers are made-up; the original registrar is made-up. `result_info` says 3 where the answer
said 7, because three entries are left.
