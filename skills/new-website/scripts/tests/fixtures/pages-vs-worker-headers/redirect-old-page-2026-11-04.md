# Where redirect-old-page-2026-11-04.json comes from

The two answers for `/old-page` (a `_redirects` line, `/old-page /privacy 301`) from the kit
throwaway site, read on 2026-11-04.

- `domain_on_pages`: a real answer, `curl -si https://<the throwaway's domain>/old-page` while the
  domain was on Pages. Cut, not edited: the `date`, `server`, `cf-cache-status`, `cf-ray` and
  `alt-svc` headers. The body is as sent.
- `version_url_of_the_worker`: NOT captured here. It is put together from what the move script
  recorded for the Worker's version URL in its own state file (status, Location, the security
  headers, a body hash equal to that of an empty body) and from what the session that ran the throwaway
  reported curl showing: `content-length: 0`, no `content-type`, and the `nel` and `report-to` lines
  (the `s=` token is made up). The raw curl of the version URL is still to be added.

By hand: Pages sends a text/plain body of 23 bytes; the Worker's answer has no body and no media
type; only the Worker's answer has `nel` and `report-to`; the status and Location are the same.
