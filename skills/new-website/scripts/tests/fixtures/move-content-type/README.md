# Where capture-record-2026-11-11-move-to-workers-7ef2f232.json comes from

What `move-to-workers.mjs record` (kit main 7ef2f232, unpatched) saved on 2026-11-11 for a real
site's Pages-to-Workers move. `lenas-backstube.example` is the Pages domain's answers, `version`
the Worker's version URL's. The capture holds seven addresses cut from the real recording; the
entries are not edited, except that the site's domain and its analytics host in the
content-security-policy headers are replaced by made-up ones.

`s` is the status, `t` the media type, `l` the Location, `h` the body hash, `hd` the compared headers.

By hand, from the capture: Pages sends `content-type` as `text/plain;charset=UTF-8` on the redirect
and `text/html; charset=utf-8`, `text/plain; charset=utf-8` or `text/css; charset=utf-8` on the
pages and files; the Worker sends the same media type with no charset, or no type at all on the
redirect. `/js/cta.js` goes from `application/javascript` to `text/javascript`.
`/.well-known/apple-app-site-association` is `application/json` on both.
