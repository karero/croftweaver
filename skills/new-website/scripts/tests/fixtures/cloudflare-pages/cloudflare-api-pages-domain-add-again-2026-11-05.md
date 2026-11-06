# Where cloudflare-api-pages-domain-add-again-2026-11-05.json comes from

A real answer from Cloudflare, read on 2026-11-05: `POST /client/v4/accounts/<account>/pages/projects/<project>/domains`
with a domain the project already holds, using the token CLOUDFLARE_MOVE.md tells a User to make.
The status is HTTP 400 (not 409); `errors[0].code` is 8000018. The answer holds no host name or id,
so nothing was replaced.
