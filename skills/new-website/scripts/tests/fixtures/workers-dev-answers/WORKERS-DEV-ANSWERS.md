# Cloudflare's answers for workers.dev addresses

`answers-2026-11-06.json` holds real answers, trimmed. The tests read it and answer with it.
Hosts are made up in the tests. Header values that name an account or a request (`cf-ray`, the
NEL report signature) are replaced; date, `alt-svc`, `etag` and security headers are cut; a long
body is cut to its first 100 characters, and `body_bytes_in_capture` is the full length.

| Key | What was asked | Answer |
|---|---|---|
| `address_off_no_accept_encoding` | a Worker's `workers.dev` address, `workers_dev` off, no `accept-encoding` header | 404, text/plain, `error code: 1042` |
| `address_off_accept_encoding_identity` | the same, with `accept-encoding: identity` | 404, an HTML page of 19,984 bytes |
| `address_on_no_accept_encoding` | the same address with `workers_dev` on, no `accept-encoding` header | 200, the site, `x-robots-tag: noindex` |
| `version_link_live` | a live version link of the Worker | 200, the site, `x-robots-tag: noindex` |
| `address_never_created_no_accept_encoding` | the address of a Worker name that was never created, no `accept-encoding` header | the same answer as `address_off_no_accept_encoding` |
| `preview_alias_live` | a live Preview (alias) link | 200, the site, `x-robots-tag: noindex` |
| `preview_alias_dead` | an alias that does not exist | 404, HTML, `x-preview-user-error: true` |

Taken on 2026-11-06 (22:58 to 23:05 UTC) with curl 8.7.1, one GET of `/` each, except
`address_on_no_accept_encoding`: 2026-11-07 09:29 UTC with curl 8.7.1, a Mozilla user agent and an
HTML `Accept`, `accept-encoding` removed (`-H 'Accept-Encoding:'`), on a throwaway Worker whose
setting was switched on for that one request and off again at once.

A Worker name that does not exist gets the same 1042 answer as an address that is off. That is
why the check asks for a served version link as well.

The checker's own request (its User-Agent and Accept, no `accept-encoding`), sent by Node's
`https.request` (v26.13.0) on 2026-11-06 about 23:50 UTC, got the same two answers: 404 `error code:
1042` for an address that is off and for a Worker name never created, and the 404 HTML page when
`accept-encoding: identity` was sent.
