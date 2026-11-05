# Where cloudflare-api-pages-domains-2026-11-05.json comes from

A real answer from Cloudflare, read on 2026-11-05: `GET /client/v4/accounts/<account>/pages/projects/<project>/domains`
with the token CLOUDFLARE_MOVE.md tells a User to make, on a project that held two active custom
domains. The entries are as Cloudflare sent them.

Replaced, nothing else edited: the two host names (`lenas-backstube.example` and its `www`), the
domain ids, and the zone tag are made-up. Each entry's `status` is a string (`active`); the nested
`verification_data.status` and `validation_data.status` are separate fields. `result_info` shows
`per_page` 20 and `total_pages` 1: the answer is paged, and the script reads page 1 only.

A capture with a pending domain is not in this folder yet.
