# Where redirect-old-page-2026-11-05.json comes from

The answers for `/old-page` (a `_redirects` line, `/old-page /privacy 301`) from the kit
throwaway site.

- `domain_on_pages`: a real answer, `curl -si https://<the throwaway's domain>/old-page` while the
  domain was on Pages, read on 2026-11-04. The body is as sent.
- `domain_on_the_worker` and `version_url_of_the_worker`: a real answer each, from
  `curl-8.7.1-worker-redirect-old-page-2026-11-05.txt` next to this file (curl 8.7.1, 2026-11-05,
  after the domain moved to the Worker). In the text file the hosts, the version prefix, `cf-ray`
  and the NEL report URL's signature are replaced. In the JSON the `date`, `server`, `cf-ray` and
  `alt-svc` headers are cut as well, as in `domain_on_pages`; nothing else is edited.

By hand, from the captures: Pages sends a text/plain body of 23 bytes; the Worker sends
`content-length: 0`, no `content-type` and no body, on the domain and on the version URL; only the
version URL has `nel` and `report-to`; the status (301) and Location (`/privacy`) are the same on
all three. All three send `x-robots-tag: noindex`.
