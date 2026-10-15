# Plan: moving an existing domain to Cloudflare, led by the assistant

Requirements record for a part of the kit that does not exist yet: the assistant's guide to
moving a domain that lives with another registrar or DNS host onto Cloudflare, before the
setup script runs. Where this plan and the shipped files disagree, the files win until plan
step 5 changes them. Names of sites and people stay out of this public repo on purpose; the
business in the scenarios is made up, the same one as in
`docs/reviews/SKILL-PLAN-cloudflare-setup.md`.

Nothing of Cloudflare's side of this plan has been tried for the move. What Cloudflare does
is "seen in the setup plan's trial" (on an active zone, cited by capture), "read in the
reference, not tried" (the table under "What is read, and what is not verified", with each
page, read 2026-10-15), or "not verified"; plan step 3, a trial on a domain registered elsewhere,
settles most of them, and each item names what settles it.

## Status, 2026-10-15 · the kit's files read at origin/main `8f7c98b`, and karero/croftweaver#328's branch at `a31c4ca`

| # | Plan step | State | Evidence |
|---|-----------|-------|----------|
| 1 | Requirements and scenarios (this file) | ▶ written 2026-10-15; PLAN gate (High) under way | this file; trail: `docs/reviews/REVIEW-plan-2026-10-15-cloudflare-domain-move.md` |
| 2 | The maintainer's decisions | ✅ 2026-10-15; decisions 3 and 4 corrected and decision 6 added the same day: the assistant suggests (b), the final screenshot comes either way, one token may serve both days | section "Decisions taken" |
| 3 | A trial on a domain registered elsewhere, with mail-shaped records, DNSSEC and a CAA record ("Not verified" 1 to 7, 10, 11, 13, 14; 8 is not planned, 9 is only told to the owner, 12 may fall to plan step 6) | ⏸ not started; needs a domain registered outside Cloudflare, and the maintainer has not yet said whether one is available | — |
| 4 | One link from `docs/reviews/SKILL-PLAN-cloudflare-setup.md` to this file | ⏸ waits for karero/croftweaver#328 to merge: that pull request edits the setup plan | — |
| 5 | The kit's guide for the move, and the files that point to it (list under "Hooks") | ⏸ not started; after plan step 3, and after karero/croftweaver#328 merges, since that pull request edits `CLOUDFLARE_FIRST_DEPLOY.md` and adds `cloudflare-setup.mjs` | — |
| 6 | Review gate on the guide (High: mail and the whole domain are at stake) | ⏸ not started | — |
| 7 | One real move with the owner watching | ⏸ not started | — |
| 8 | Release note line, in a release after 0.32 | ⏸ not started | — |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked · ⚠ deviated

## Why

When people start building a website they mostly have a domain already. Its nameservers, its
DNS records and often its mail sit with another registrar or host. The setup plan assumes the
domain is on Cloudflare: its script, `cloudflare-setup.mjs` (karero/croftweaver#328, open),
stops when Cloudflare has no active zone for the site's host (setup plan, "Which project and
which publish model"). Today the move is the
checklist "Going live: moving an existing domain's DNS to Cloudflare — verify twice" in
`skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md`: import, compare every record
twice, a screenshot, the records that must stay DNS only, DNSSEC off first, TTLs lowered,
the old setup kept through propagation.

That checklist is right, and it leaves the owner alone with it. Cloudflare's import scan
misses records: on a real move in 2026 it missed the Microsoft 365 entries (the Outlook
mail records), and the assistant found them (the maintainer's account, 2026-10-15; "Going
live" records a missing `autodiscover`). Cloudflare's own reference says the scan "is
not guaranteed to find all existing DNS records", and expects it to miss unusual names such
as a custom `_domainkey`. A missing mail record breaks mail silently, on
the day the owner is least likely to notice. So the assistant leads the move, step by step,
and checks every record against the old DNS before the owner switches nameservers.

## Requirements

M1. **The move comes first, and the assistant leads it.** Order: move the domain, wait until
Cloudflare calls the zone active, then `setup`, then `launch` (setup plan). The move is not a
stage of the setup script.

M2. **The switch changes nothing anyone can see.** After the nameservers change, every name
the domain had answers as it did before, mail included, unless the owner chose a change and
the assistant named it. The old website keeps being served from the old host until `launch`.

M3. **Every record is checked against the old DNS.** Two sources: a lookup from outside of
every name the assistant knows to ask for (the domain itself, `www`, mail, and the names
Microsoft 365, Google Workspace and similar services use), and the old provider's zone export
where the owner can download one. Without an export the assistant says plainly that a name it
could not guess may be missing, and asks the owner which services use the domain (a
newsletter tool, a shop, a booking page, a helpdesk).

M4. **Only web hosts are proxied, and not yet.** Mail records, the hosts mail points to, and
every CNAME that is not the website (`autodiscover`, DKIM selectors, verification records,
other services) stay DNS only. The old website's records stay DNS only too, until `launch`
points the site's host at Pages (judgment call J1).

M5. **The owner chooses how the records get fixed; the assistant suggests (b).** (b) The
assistant writes the missing and corrected records through Cloudflare's API with a
short-lived token, on a yes of its own to the list. (a) The owner makes the changes in
Cloudflare's dashboard from the assistant's list and sends another screenshot; no token is
needed before setup day. The assistant offers both and suggests (b): the owner still checks
every entry before the switch (M6), so nothing the API wrote goes unseen.

M6. **Only the owner switches the nameservers,** at the old registrar. Before that, either
way, the owner checks all entries once more themselves, on a final screenshot looked at with
the assistant. Under (b) the assistant also reads the zone through the API. Where
Cloudflare's nameservers answer for the pending zone, as its reference says ("Not verified"
4, J8), it compares their answers with the old nameservers' name by name. And it handles
DNSSEC first.

M7. **No guessing about time.** The assistant never waits in a running command for
Cloudflare or the registrar. It tells the owner what to expect, and checks again when the
owner comes back.

M8. **A way back stays open.** The old zone, website and mail stay as they are until the
new setup is shown to work, and the owner is asked not to end the old provider's DNS service
before then. TTLs are lowered at the old provider a day before the switch, so answers cached
from it run out within minutes once resolvers ask Cloudflare. The quick way back after the
switch is fixing the record in Cloudflare (a TTL of Auto is 300 seconds). Switching the
nameservers back is the last resort: it works only while the old zone exists and DNSSEC is
off, and resolvers may keep asking Cloudflare for as long as the top-level domain's TTL on
the nameserver records, which lowering the old TTLs does not shorten ("Not verified" 13).

M9. **Shown to work, not assumed.** After the zone turns active, the assistant looks up every
name again from outside and compares, and the owner sends a test email in both directions.
Where DNSSEC was on before the move, the assistant offers to turn it on again once the
owner retires the old setup, not before: Cloudflare's DS record at the registrar ends the
switch back of M8 (old nameservers under a new DS fail to resolve). The old setup is
retired, and the DS published, no sooner after the switch than the longer of the two TTLs
resolvers may hold the old delegation by: the top-level domain's on the nameserver records,
and the old zone's own on its NS records, both read before the switch ("Not verified" 13).
In Cloudflare first, then the DS record Cloudflare gives, entered by the owner at the
registrar ("Not verified" 10). Since that comes days or weeks after the move, the
assistant writes a dated line in the site's README, beside its "Deploy" paragraph: DNSSEC
was on before the move, the two TTLs, and the earliest day it may go back on. A later
session reads it there; the by-hand lists only remind it to look ("Hooks").

M10. **The token for (b) is narrow and short-lived.** One zone, an end date a week out at most
(`docs/CLOUDFLARE-CHECKLIST.md`, section 6: "a week at most", read as the setup script reads it: eight days, since the
dashboard sets an end date that can fall late on the seventh, `MAX_TOKEN_MS` in
karero/croftweaver#328). Its rows are the two the move needs, or, where the owner wants it to
serve setup day too and setup day falls inside its life, the setup plan's rows, which include
DNS Edit (J5). It reaches the assistant as that section says: an environment
variable for the session, or `.dev.vars`, a file the repository must ignore, which the
assistant checks git ignores before the owner writes to it. No token is used without the
owner's screenshot of Cloudflare's summary of it, taken before it is created: that is the
one check that shows its rows and its zones ("Under (b)"). It is never printed, never written to a file git
tracks, and goes only to `api.cloudflare.com`.

M11. **What the owner sends stays private.** Screenshots, zone exports and lookups hold the
owner's records; they are not committed to any repository, the site's included.

M12. **Each check says how it was made.** The assistant reports for every record what it
compared, against which source, and what it could not see (a value cut off on a screenshot, a
name it could not guess).

## Scenarios

The owner is Lena. Her domain `lenas-backstube.example` is registered at another registrar,
which also hosts its DNS. Her old website runs at her old host; her mail is at Microsoft 365.
Unless a row says otherwise, Lena has added the domain in Cloudflare's dashboard and let it
scan the records. The "Settled by" column names what will show the row works: the trial (plan
step 3), the guide's review (plan step 6), or the real move (plan step 7).

| # | Given | When | Then | Settled by |
|---|-------|------|------|------------|
| | **Before the switch: comparing** | | | |
| 1 | the scan found the apex A record, `www`, the MX record and the SPF TXT record, and missed `autodiscover`, the two DKIM selector CNAMEs and the two SRV records Microsoft 365 uses for Teams | Lena sends a screenshot of the records Cloudflare suggests | the assistant looks up the known Microsoft 365 names at the old provider's nameservers, finds the five, and lists each as missing, with its type, name and value as the lookup returned it | trial |
| 2 | her mail is at Google Workspace instead; the scan missed the DKIM TXT record at `google._domainkey` | the same | the assistant lists that record as missing, with the value from the lookup | trial |
| 3 | her old provider offers a zone export; it holds `k1._domainkey` (a newsletter tool's DKIM) and `termine` (a booking page), names no list knows | Lena downloads the export and gives it to the assistant | both are listed as missing; the export is compared record by record with what Cloudflare suggests | trial |
| 4 | the old provider offers no export | the assistant has compared what it could look up | it says that names it could not guess may be missing, and asks Lena which services use her domain; for each she names, it looks up that service's names | real move |
| 5 | the scan suggests `autodiscover` as a proxied CNAME | the assistant reads the screenshot | it says this one must be DNS only, and why: "Going live" says a stray orange cloud on `autodiscover` breaks the service (the kit's checklist, not tried) | guide review |
| 6 | her MX record points to `mail.lenas-backstube.example`, whose A record the scan proxied | the same | it says mail breaks if `mail` is proxied, and lists that record as "DNS only" | trial |
| 7 | the scan proxied the apex and `www`, which serve her old website | the same | it lists both as "DNS only until launch", and says why: nothing changes for her visitors before the new site is ready (J1) | trial |
| 8 | a long TXT value (a DKIM key, an SPF record) is cut off on the screenshot | the assistant compares | it compares the part it can see, says what it could not see, and asks for that record's edit view, or Cloudflare's own export of the zone (J2) | trial |
| 9 | a wildcard record `*` and a subdomain handed to other nameservers (`shop`, NS records) are in the export | the same | both are listed by name, the wildcard DNS only: "Going live" says both are commonly skipped | trial |
| 10 | her apex has a CAA record that allows one certificate authority, not one Cloudflare uses | the assistant looks up CAA | it says Cloudflare could not issue a certificate for her domain, which `launch` needs, and lists the CAA records to add for `letsencrypt.org`, `pki.goog` and `ssl.com`, the three Cloudflare's Pages reference names; her old site keeps its own certificate | trial |
| 11 | the old provider's nameservers do not answer a lookup at all, or answer for a name with an error | the assistant compares | it says which names it could not look up, does not count them as matching, and asks for the export or the old provider's record list | trial |
| | **Fixing: the owner chooses** | | | |
| 12 | the list holds missing, wrong and wrongly proxied records | the assistant has finished the list | it offers Lena both ways, says what each needs, and suggests (b); she decides | guide review |
| 13 | Lena chooses (a) | she has changed the records in the dashboard and sends a new screenshot | the assistant compares again, from the start; the list is empty, or it gives the next list | trial |
| 14 | Lena chooses (b) and makes a token: her one zone, Zone → Zone → Read and Zone → DNS → Edit, ending in three days; before creating it she sends a screenshot of Cloudflare's summary of the token | the assistant has checked the summary, then the token | it shows each record it will create and each it will change, with type, name, value and proxy state before and after, and writes nothing until Lena says yes to that list | trial |
| 15 | the same, after her yes | the assistant writes | each missing record is created and each wrong one changed, one call each, and read back through the API; a refused write is listed "by hand" with Cloudflare's words; a record already as wanted is not sent again; nothing is deleted (J6) | trial |
| 16 | Lena's token has no end date, or reaches all her zones, or ends in thirty days | the assistant checks it | it uses none of it and names the token to make instead, as the setup plan's scenarios 33 and 40 do | guide review |
| 16a | Lena wants one token for the move and setup day, which falls inside its life | she asks | the assistant names the setup plan's rows (which include DNS Edit) for it, says the move uses only its Zone Read and DNS Edit rows, and that setup day still asks its own yes | guide review |
| 17 | under (b), a record in the zone should not be there at all (a scan guess at a name the old DNS never had) | the assistant's list says so | Lena deletes it in the dashboard: the move deletes nothing through the API (J6) | guide review |
| | **The switch** | | | |
| 18 | the list is empty | the assistant is asked whether Lena can switch | it asks Lena to check every entry once more, on a final screenshot it looks at with her, either way; under (b) it also reads the whole zone through the API; both compared with the old DNS once more; and it asks every name of the comparison at the old nameservers and at Cloudflare's two, and lists each answer that differs (J8) | trial |
| 19 | DNSSEC is on at her registrar (the domain's DS record answers from outside) | the last check is clean | it says to turn DNSSEC off at the registrar first and to wait until the DS record is gone from outside plus its TTL (the reference: commonly a day or two); it checks that from outside before saying "switch now" | trial |
| 20 | her old provider's TTLs are a day long | the assistant plans the switch | it asks her to lower them a day before, and says why: once resolvers ask Cloudflare, answers cached from the old provider run out within minutes, not a day; it does not promise a quick switch back, which can take the top-level domain's TTL (M8). Where her old provider does not let her change TTLs, it says so, and the old setup is kept the longer: as long as the old TTLs, after the switch | trial |
| 21 | all checks agree | Lena is ready | the assistant gives her Cloudflare's two nameservers as Cloudflare shows them, to replace every old one at the registrar; she switches; the assistant does nothing at the registrar | real move |
| | **After the switch** | | | |
| 22 | the zone is still pending three hours later | Lena asks what is wrong | the assistant looks up the domain's nameservers at its top-level domain, says whether the registrar has passed the change on, and what to expect (the reference: up to 24 hours at the registrar; the "Re-check nameservers" button on the zone's Overview page); it starts no waiting command | trial |
| 23 | the zone turns active | Lena comes back | the assistant looks up every name of the comparison again, now answered by Cloudflare, and compares with the old answers; then asks Lena to send an email from outside to her address and one from her address to outside | trial |
| 24 | a test email bounces | the assistant compares | it names the record that differs, and Lena fixes it in the dashboard (or, under (b), the assistant creates or changes it on her yes to that record); if no record explains it, the last resort is the old nameservers, while the old zone still exists, and it can take the top-level domain's TTL to take hold (M8) | real move |
| 25 | the zone is active and mail works both ways | the move is done | the assistant says what comes next (`setup`, then `launch`), that the old zone stays until mail and the site are shown to work for a few days, and, under (b), to delete the token, unless it is to serve setup day inside its life; where DNSSEC was on before, it says it will offer to turn it on again once the old setup is retired (M9) | guide review |
| | **Edges** | | | |
| 26 | Lena's domain has an active zone in her own Cloudflare account | she asks to move it | there is nothing to move: the assistant goes on with `setup` | guide review |
| 26a | her domain's nameservers are Cloudflare's, but the zone lives in another account (her former agency's), so her token reaches no zone for it | `setup` stops | the move applies as written, the old provider being that account: its zone answers at its own Cloudflare nameservers, and its export comes from whoever holds that account; the switch is to the two nameservers her own account is given ("Not verified" 14) | trial |
| 27 | Lena's domain has no mail and no website yet | the move starts | the comparison is short, but DNSSEC and CAA are still checked | trial |
| 28 | Lena also wants to change her mail provider | she asks during the move | the assistant keeps the two apart: the move first, mail as it is; the mail change afterwards, as its own step | guide review |
| 29 | Lena added the domain and never switched the nameservers | days pass | the assistant says Cloudflare removes a Free-plan zone not activated within 28 days (the reference), and that adding it again repeats the comparison | guide review |
| 30 | her old provider serves the apex through an ALIAS (or ANAME) record | the assistant compares | a lookup shows only the addresses it points to now, the same as a plain A record, and an export may show the same; so the assistant asks Lena, export or not, whether her old provider shows an ALIAS or ANAME at the apex, and where she sees one, what it points at, rather than copy addresses that may change | guide review |
| 31 | her apex has an A and an AAAA record, or her `www` an A and a TXT record, all for the old website | the move is done | the report names them: on launch day the setup plan's `launch` refuses such a host (its scenario 24) and sends the owner to attach the domain by hand ("Hooks") | guide review |
| 32 | DNSSEC was on before the move; weeks later Lena retires her old provider's DNS | a session reads the by-hand list, or launch day's report, and then the site's README | it finds the README's dated line, checks that its earliest day has passed, and offers to turn DNSSEC on: in Cloudflare, then the DS record at the registrar; once done, the line says so | guide review |

## Shape

Kept short on purpose: what is unknown about Cloudflare's side is listed under "Not
verified", and the trial settles it before the guide is written.

**Where it lives.** A reference of its own in the `new-website` skill,
`skills/new-website/references/CLOUDFLARE_DOMAIN_MOVE.md`. The "Going live" checklist in
`CLOUDFLARE_FIRST_DEPLOY.md` becomes a short pointer to it. The setup script's stop for a
domain with no active zone names it.

**What the owner does, none of it in a terminal:** adds the domain in Cloudflare's dashboard;
sends screenshots, and the old provider's export where there is one; picks (a) or (b); under
(b) makes the token and says yes to the list, under (a) changes the records in the dashboard;
checks every entry on the final screenshot;
lowers the TTLs; turns DNSSEC off at the registrar; switches the nameservers; sends the test
emails.

**What the assistant does:**

1. **Looks up the old DNS from outside.** It asks the old provider's own nameservers, not a
   public resolver, so no cache stands between. It learns their names from an NS lookup of
   the domain through the computer's own resolver, which answers from the zone, and their
   addresses the same way, since Node's resolver takes addresses, not names. It then uses
   Node's resolver set to those addresses: the kit already needs Node, and the setup plan's trial saw Node's resolver answer a
   TXT lookup that way. The names it asks for are a list in the guide: the domain itself,
   `www`, the MX targets, `_dmarc`, and the names of Microsoft 365, Google Workspace and the
   other services the guide names. It asks for the types A, AAAA, CNAME, MX, TXT, SRV, CAA
   and NS where they apply. Two answers come from the top-level domain, not from the old
   provider, and Node's resolver cannot read them: it has no DS type (asking throws
   `ERR_INVALID_ARG_VALUE`), and a referral, which is how a top-level domain names a
   domain's nameservers, reads as "no data". So the DS record and the nameservers the
   top-level domain names are asked with another tool ("Not verified" 13); a lookup that
   fails counts as DNSSEC on, and the assistant does not say "switch now".
2. **Reads what Cloudflare suggests,** from the screenshots, or Cloudflare's export where the
   owner sends one (J2).
3. **Gives one list:** missing, wrong, proxied where it must not be, and what it could not
   see. Each line has the type, name and value to set.
4. **Offers both ways and suggests (b),** and works the way the owner picks until the list
   is empty.
5. **Asks for the last check:** the owner's own, on a final screenshot looked at together;
   under (b) also its own read of the whole zone through the API; and every name asked at
   the old nameservers and at Cloudflare's (J8). Then it handles DNSSEC and tells the owner
   when to switch.
6. **After the switch,** compares again and asks for the test emails; where DNSSEC was on,
   says it will offer it again once the old setup is retired, and writes the dated line of
   M9 in the site's README.

**Under (b),** the assistant sends each call with Node's own `fetch`, the token read inside
the program from `CLOUDFLARE_API_TOKEN`, or, when that is not set, from `.dev.vars`, as the
setup script does, refusing the file if git tracks it or does not ignore it; never from the
command line, and never printed.
It checks the token first: Cloudflare's summary of it, from the owner's screenshot before
it is created (its rows, its zone, its end date), then token verify, which carries
`expires_on` only for a token with an end date (setup plan, "The token", captures 001 and
003), and the zone list, which must show this one zone. The zone list cannot show the rows,
or tell a one-zone token from an all-zones one while the account has one zone; the summary
is what shows those ("Not verified" 5). Then it creates each missing record
(`POST /zones/{zone_id}/dns_records`) and changes each wrong one with a PATCH that keeps its
id (the setup plan's trial saw that on an active zone, capture 132), one call each, and reads
each back. It deletes nothing (J6). The first version ships no script for this (J3).

## What is read, and what is not verified

**Read in Cloudflare's reference, 2026-10-15, not tried:**

| What the reference says | Page |
|---|---|
| The quick scan runs only while a domain is added in the dashboard; it "is not guaranteed to find all existing DNS records" and is expected to miss unusual names, such as a custom `_domainkey`; review and add missing records before changing nameservers | [quick scan](https://developers.cloudflare.com/dns/zone-setups/reference/dns-quick-scan/), [full setup](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/) |
| Proxying is on by default for a domain added in the dashboard; only A, AAAA and CNAME records can be proxied. Which scanned records end up proxied is not said | [proxy status](https://developers.cloudflare.com/dns/proxy-status/) |
| The host an MX record points to must resolve DNS only, or mail clients cannot connect | [email issues](https://developers.cloudflare.com/dns/troubleshooting/email-issues/) |
| A Free-plan zone not activated within 28 days is deleted. Cloudflare first checks the nameservers after 60 seconds, then at growing intervals; a re-check can be started on the zone's Overview page, or by API once an hour on Free | [domain status](https://developers.cloudflare.com/dns/zone-setups/reference/domain-status/), [activation check](https://developers.cloudflare.com/api/resources/zones/subresources/activation_check/methods/trigger/) |
| "Cloudflare responds to DNS queries for pending zones on the assigned Cloudflare nameserver IPs" | [domain status](https://developers.cloudflare.com/dns/zone-setups/reference/domain-status/) |
| At the registrar: remove the existing nameservers, add Cloudflare's two exactly, only Cloudflare's listed; allow up to 24 hours | [full setup](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/), [troubleshooting](https://developers.cloudflare.com/dns/zone-setups/full-setup/troubleshooting/) |
| DNSSEC: turn it off at the registrar before replacing nameservers, wait for the DS record's TTL to expire at the parent (commonly 24 to 48 hours), re-enable in Cloudflare once active. A multi-signer migration keeps DNSSEC on, where the old provider accepts the other's keys at the apex | [DNSSEC](https://developers.cloudflare.com/dns/dnssec/), [migration](https://developers.cloudflare.com/dns/dnssec/dnssec-active-migration/) |
| Cloudflare's certificates come from Let's Encrypt, Google Trust Services and SSL.com. The SSL reference says Cloudflare adds its own CAA records, not shown in the dashboard, where a zone with Universal SSL has any; the Pages custom-domain page says to add CAA records for `letsencrypt.org`, `pki.goog` and `ssl.com` yourself | [authorities](https://developers.cloudflare.com/ssl/reference/certificate-authorities/), [CAA](https://developers.cloudflare.com/ssl/edge-certificates/caa-records/), [Pages custom domains](https://developers.cloudflare.com/pages/configuration/custom-domains/) |
| The zone's records can be exported (a BIND file) in the dashboard and by API; a BIND file can be imported, by API with a `proxied` field whose default is not stated, returning counts of records added and parsed. The old scan call is deprecated; its successor finds records and adds none until they are accepted | [import and export](https://developers.cloudflare.com/dns/manage-dns-records/how-to/import-and-export/), [import](https://developers.cloudflare.com/api/resources/dns/subresources/records/methods/import/), [scan review](https://developers.cloudflare.com/api/resources/dns/subresources/records/methods/scan_review/) |
| A token can be limited to one named zone; listing and creating records takes DNS Edit. Creating a zone takes Zone Edit or DNS Edit; whether such a token can be limited to a zone that does not exist yet is not said | [create token](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/), [create zone](https://developers.cloudflare.com/api/resources/zones/methods/create/) |
| A TTL of Auto is 300 seconds | [TTL](https://developers.cloudflare.com/dns/manage-dns-records/reference/ttl/) |

**Not verified.** Each with the trial step that settles it. All need a domain registered
outside Cloudflare.

1. Which records Cloudflare's scan finds and which it misses, for Microsoft 365 and Google
   Workspace records, in October 2026. Seen once: a real move in 2026 missed the Microsoft
   365 entries, which the assistant found; which entries exactly is not recorded here. Trial:
   put the services' record shapes (made-up values) on the trial domain at its old provider,
   add it to Cloudflare, and read what the scan suggests.
2. Which records the scan suggests as proxied. The reference says proxying is on by default
   for a domain added in the dashboard, and names no list. Trial: the same scan.
3. Whether a screenshot of the suggested records shows each value whole and the proxy state of
   each, and whether the dashboard's export works for a pending zone. Trial: screenshot and
   export the trial zone while pending.
4. That Cloudflare's assigned nameservers answer for the pending zone, as the reference says,
   with the records the zone holds. The last check leans on it (J8). Trial: look up each record
   of the trial zone at an assigned nameserver while pending.
5. Under (b): whether a token can be limited to a zone that is still pending (the reference
   says one named zone, and does not say pending), and whether Zone → Zone → Read and Zone →
   DNS → Edit are enough. The reference has DNS Edit cover the records; the Zone Read row is
   for the zone list that shows the token's reach, as in the setup plan's scenario 33. And
   whether Cloudflare's summary page, before a token is created, shows its rows, its zone and
   its end date in one screenshot. Trial: make such a token on the
   pending trial zone, verify it, list the zone.
6. Under (b): writing and changing records in a pending zone through the API, and reading
   them back. Trial: create a TXT, a CNAME DNS only, and an SRV record; change one value and
   one proxy state with a PATCH; read back.
7. Under (b): what the API's import of a zone file returns, which records it skips, and
   whether it proxies them. The first version does not use it: it creates record by record
   (J3). Trial: import the old provider's export into the trial zone after items 1 to 6 are
   read, with the scanned records removed first (adding the zone again would scan again),
   and read what came in.
8. Creating a zone through the API. Not needed: the owner adds the domain in the dashboard
   (decision 2). Not tried and not planned.
9. How long a zone stays pending before Cloudflare removes it, and how often it re-checks the
   nameservers: read in the reference (28 days on Free; 60 seconds, then growing intervals),
   not tried. The move only tells the owner, so the trial need not wait 28 days.
10. DNSSEC: how long the DS record stays visible after the registrar turns DNSSEC off (the
    reference: the DS TTL, commonly 24 to 48 hours), and whether some registrars remove it on
    their own when the nameservers change. And that a DS published after the old setup is
    retired resolves cleanly. Trial: turn DNSSEC on, then off, at the trial domain's
    registrar and time it; after the switch, turn it on in Cloudflare, enter its DS at the
    registrar, and ask a validating resolver.
11. Whether Cloudflare adds CAA records of its own where a zone has some: the SSL reference
    says it does, the Pages custom-domain page says to add them yourself. The move follows the
    Pages page (scenario 10); a record Cloudflare also adds does no harm. Trial: a restrictive
    CAA record on the trial domain, then a throwaway Pages project's custom domain on it,
    before and after the three CAA records are added, and the certificate it serves.
12. Node's resolver set to a nameserver, on Windows. Seen on a Mac only. Trial: one lookup on
    Windows, or in the guide's review if no Windows machine is at hand.
13. The tool for the two answers Node's resolver cannot read: the DS record and the
    nameservers the top-level domain names (Shape, step 1), on Mac and Windows: `nslookup`,
    which both ship, or DNS over HTTPS to a named public resolver through Node's `fetch`. And
    the TTL the top-level domain gives the nameserver records, which bounds a switch back
    (M8), and the old zone's own TTL on its NS records; the longer of the two sets the wait
    before DNSSEC goes back on (M9). Trial: read both for the trial domain with each
    candidate, before and after DNSSEC goes off and the nameservers change.
14. A domain active in another Cloudflare account (scenario 26a): whether Cloudflare lets it
    be added, pending, to a second account, and gives that account other nameservers. Read
    nowhere yet. Trial: add the trial domain, once active, to a second account.

## Judgment calls

Facts above are seen or read; these were weighed. Each with the strongest case against.

- **J1. The old website's records stay DNS only until launch.** Judgment: proxying the old
  site gains nothing for the move and can break it (Cloudflare's encryption mode against the
  old host's certificate; redirect loops). DNS only keeps it exactly as before (M2).
  *Against:* Cloudflare's scan proxies them (to be seen, "Not verified" 2), so the owner must
  change them, and the old site's address stays visible, as it was before the move.
- **J2. Screenshots by default, with Cloudflare's export as a fallback.** Decision 2 names the
  screenshot. Judgment: where a value is cut off, ask for the record's edit view or the
  export rather than pass it on the visible part. *Against:* one more step for the owner, and
  the export may not work while the zone is pending ("Not verified" 3).
- **J3. No script for the move in the first version.** Judgment: the assistant leads it, as
  decision 1 says, with lookups and calls the guide shows. *Against:* commands written in a
  guide are untested in a way a script with tests is not; an error in one (a wrong record
  type, a token printed) is found by the owner, not by CI. Revisit after the trial and the
  first real move.
- **J4. DNSSEC: off and wait, not a migration that keeps it on.** Judgment: the plain path is
  one the owner can follow at any registrar. *Against:* the domain is unsigned from the day
  DNSSEC goes off until the owner turns it on again after the move (M9), days at the least; Cloudflare documents a path that keeps it signed, which a careful owner may want.
- **J5. One token or two, the owner's pick.** Decision 6 lets the (b) token serve setup day
  inside its life. Judgment: the assistant asks which the owner wants, a move-only token with
  the two rows, or one with the setup plan's rows from the start, and names the first as the
  narrower. *Against:* the wider token holds Pages and settings rights through the move,
  which the move never uses; the narrower one means a second token in the same week.
- **J6. Under (b), create and change, never delete.** Judgment: a record that should not be
  there at all is deleted by the owner in the dashboard; the guide sends no delete call. The
  token could delete: its DNS Edit row allows it, so this is the guide's rule, not the
  token's limit. *Against:* (b) then still sends the owner to the dashboard for those, which
  (b) was chosen to avoid.
- **J7. The move and a mail change stay apart.** Judgment: two changes at once make a bounced
  email impossible to trace. *Against:* the owner may want one disruption, not two.
- **J8. The last check also asks Cloudflare's nameservers.** Decision 4 names the final
  screenshot, looked at together. Judgment: add a lookup of every name at Cloudflare's two
  nameservers, compared with the old ones', since the reference says they answer for a pending
  zone; it sees what a screenshot cuts off, and what a person misreads. *Against:* it rests on
  the reference ("Not verified" 4), and it compares only the names the assistant knows: a
  clean result proves nothing about a name no one asked for, so it adds to the screenshot
  and never replaces it.

## Decisions taken

The maintainer's, 2026-10-15. Recorded, not open.

1. **The assistant leads the move, not a stage of the setup script, and it comes before
   `setup`:** move, wait until the zone is active, then `setup`, then `launch`.
2. **The owner adds the domain in Cloudflare; Cloudflare suggests records; the owner sends a
   screenshot of them; the assistant checks them against the old DNS** (looked up from
   outside for the known names, Microsoft 365, Google Workspace and the like, and the old
   provider's zone export where the owner can download one), and says what is missing, wrong
   or wrongly proxied.
3. **The assistant offers both ways and suggests (b)** (corrected 2026-10-15, the same day:
   "suggest b but also offer a, the User still has to do the final verification, so b is
   fine"). (b): the assistant writes the missing and corrected records through Cloudflare's
   API with a short-lived token, on a yes of its own. (a): the owner makes the changes in the
   dashboard from the assistant's list and sends another screenshot; no token is needed
   before setup day. The first word that day had named (a) first, as the default. The yes of
   (b) cannot join setup day's yes, since `setup` runs only once the zone is active, after the
   move. So (b) adds a yes, for owners who choose it, beside the two yeses of the setup plan's
   D1.
4. **Either way, the owner changes the nameservers at the old registrar; nobody else can.**
   Before that, the owner checks all entries once more themselves, on a final screenshot
   looked at with the assistant (corrected 2026-10-15; the first word had, for (b), a read of
   the zone through the API in its place; the assistant still makes that read, beside the
   owner's check), and the assistant handles DNSSEC first. After the switch: wait
   for the zone to turn active, then a test email in both directions.
5. **Release: not 0.32.** 0.32 carries the setup script for domains already on Cloudflare;
   the move comes in a later release.
6. **The (b) token may also serve setup day,** if setup day falls inside its life
   (2026-10-15, with the correction to decision 3).

## Hooks

Plan step 5 brings these in line, after karero/croftweaver#328 merges. Line numbers are
#328's at `a31c4ca`; plan step 5 finds each again in the merged files by its quoted text:

- `skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md`: the move's points in "Going
  live" (import, compare twice, screenshot, DNS only, DNSSEC, CAA) and its box "Make rollback
  cheap" (TTLs, keep the old setup) move to the new guide, the box's rollback wording
  rewritten to M8. What stays is the attach step, which karero/croftweaver#328 makes the
  place for attaching the domain by hand on launch day (its lines 12 and 85): the Pages box
  on attaching the custom domain (the 522), under a heading renamed for that step, with a
  pointer to the guide; its own pointers to "Going live" for that step (#328's lines 12 and
  85) take the new heading. It gains how to handle a host with an A and an AAAA record, or a
  `www` with a TXT record, which the setup plan's `launch` refuses (its scenario 24; here
  scenario 31). #328's line 37 ("'Going live' below if it is not") sends a domain not yet
  on Cloudflare to the move: it points to the new guide instead.
- `skills/new-website/SKILL.md` §1, question 6 ("DNS moves to Cloudflare"), where the
  assistant first learns the domain lives elsewhere, and §4, which sends the owner to
  `CLOUDFLARE_FIRST_DEPLOY.md` for the first deploy: each gains one line, move first.
- `skills/new-website/scripts/cloudflare-setup.mjs` on karero/croftweaver#328's branch: its
  stop for a host with no zone the token reaches (line 502) names the guide, and so does its
  stop for a zone that is not active (line 504), the one an owner in the middle of a move
  meets. Its two pointers to "Going live" for attaching the domain (line 130, and the
  message "Setup is done, as far as Cloudflare's API shows", line 859) name the renamed
  heading.
- `docs/CLOUDFLARE-CHECKLIST.md` (two places) and
  `skills/new-website/references/CLOUDFLARE_CHECK.md` (one), which send the reader to "Going
  live" for moving a domain and for DNS and mail records. `CLOUDFLARE_CHECK.md`'s "By hand,
  always" also gains one line: DNSSEC back on, where the site's README records that a move
  turned it off, on or after the day it names (M9, scenario 32).
- `docs/reviews/SKILL-PLAN-cloudflare-setup.md`: in plan step 4, the one link: "What the owner
  does" has "moved there as 'Going live' in `CLOUDFLARE_FIRST_DEPLOY.md` says", which points
  here instead. With plan step 5, scenario 24's "points to 'Going live'" takes the renamed
  heading, and the launch report of scenario 36 names DNSSEC among what is left by hand,
  where a move turned it off.

## Review trail

`docs/reviews/REVIEW-plan-2026-10-15-cloudflare-domain-move.md`, at High depth: mail and the
whole domain are at stake.
