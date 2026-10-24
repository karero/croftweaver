#!/usr/bin/env bash
# track.sh — one-command weekly tracker. Pulls GSC + Bing for the target keywords,
# appends each run to a history CSV, then prints the week-over-week position trend.
# Run it every 1–2 weeks (not daily — daily is noise at low volume).
#
#   bash track.sh <domain> "<comma,separated,keywords>"
#   bash track.sh example.com "AI Events Munich,AI Meetups Munich,AI Treffen München"
#
# Reads keys from ~/.config/gsc-insights/.env (SERPER not needed here; Bing optional).
set -euo pipefail

DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ENV="$HOME/.config/gsc-insights/.env"
PY="$HOME/.config/gsc-insights/venv/bin/python"
DOMAIN="${1:?domain required (e.g. example.com)}"
KEYWORDS="${2:?keywords required (comma-separated)}"

[ -x "$PY" ] || { echo "✗ venv missing at $PY — see SKILL.md setup"; exit 1; }
# Per-site settings arrive in the environment from the site's launchd plist
# (schedule_tracking.sh install writes both keys, an empty one meaning "none").
# The shared .env holds API keys; sourcing it with `set -a` would overwrite
# those per-site values with any stale global ones, so hold them across the
# source and put them back. Set-ness, not non-emptiness, is what counts: a
# site installed with an empty country must run unfiltered even if .env still
# says deu. Unset (an ad-hoc run by hand) keeps the .env fallback.
site_csv_set="${GSC_HISTORY_CSV+set}"; site_csv="${GSC_HISTORY_CSV:-}"
site_country_set="${GSC_COUNTRY+set}"; site_country="${GSC_COUNTRY:-}"
[ -f "$ENV" ] && { set -a; . "$ENV"; set +a; }
[ -n "$site_csv_set" ] && GSC_HISTORY_CSV="$site_csv"
[ -n "$site_country_set" ] && GSC_COUNTRY="$site_country"
# An empty value means "none": drop it so the Python scripts (which read
# os.environ.get with a default) never see "" as a file name or a country.
[ -n "${GSC_HISTORY_CSV:-}" ] || unset GSC_HISTORY_CSV
[ -n "${GSC_COUNTRY:-}" ] || unset GSC_COUNTRY
CSV="${GSC_HISTORY_CSV:-$HOME/.config/gsc-insights/history.csv}"

# Every step runs, whatever happened before it, and each thing that went wrong is
# collected in `problems` and printed at the end. A scheduled run's exit code is the
# only unattended signal, so it is nonzero whenever that list isn't empty:
#   GSC's own code if GSC failed (a dead sign-in keeps its familiar exit 2),
#   else 4 if a history write failed (as before), else 1.
# Exit 4 from gsc_query.py/bing_query.py means "the pull succeeded but the history
# CSV write failed" (they catch write errors so an ad-hoc report never crashes —
# see _history.py); here that is a problem, because building history is the job.
# A GSC failure used to abort the run on the spot, which also cost the week's Bing
# and AI data — see docs/reviews/SKILL-PLAN-geo-check.md.
problems=()
gsc_rc=0
history_gap=0

# Record the settings this run resolved, so an on-demand report page (search_report.py) uses
# exactly what the weekly job uses without re-reading .env or the launchd job. Written through a
# temporary file of its own (an overlapping run can't collide) and dated, so the page can say how
# old a record is; nothing is deleted on failure (it could be another run's good record). `bing`
# records only whether a key resolved, never the key.
SITE_FILE="$HOME/.config/gsc-insights/sites/$(printf '%s' "$DOMAIN" | tr '[:upper:]' '[:lower:]').json"
if ! { mkdir -p "$(dirname "$SITE_FILE")" &&
       "$PY" -c 'import datetime,json,os,sys,tempfile; d,k,c,h,b,f=sys.argv[1:7]
fd,t=tempfile.mkstemp(dir=os.path.dirname(f), prefix=".site-", suffix=".tmp")
try:
    with os.fdopen(fd,"w") as o:
        json.dump({"domain":d,"keywords":[x.strip() for x in k.split(",") if x.strip()],"country":c,"csv":h,"bing":b=="1","recorded":datetime.date.today().isoformat()}, o, ensure_ascii=False, indent=1)
    os.replace(t,f)
except BaseException:
    os.path.exists(t) and os.remove(t); raise' \
         "$DOMAIN" "$KEYWORDS" "${GSC_COUNTRY:-}" "$CSV" "$([ -n "${BING_API_KEY:-}" ] && echo 1 || echo 0)" "$SITE_FILE"; }; then
  echo "  ⚠ could not record this site's settings in $SITE_FILE — the report page shows the date of any older record"
  problems+=("site settings not recorded")
fi

echo "▶ Google Search Console …"
# GSC_COUNTRY (ISO alpha-3, e.g. deu): optional country filter so the tracked
# history matches ad-hoc --country reports (env-var pattern like GSC_HISTORY_CSV).
# 28-day window (GSC_TRACK_DAYS overrides): weekly points from a 90-day window
# are ~92% the same data — real moves show up damped and weeks late. 28 matches
# the SKILL.md cadence. NOTE: changing the window shifts the level of the
# recorded positions once, so the first post-change trend line is not comparable.
# --no-browser: nobody is at the screen for a scheduled run, so a sign-in that can't
# renew silently must exit 2 with instructions instead of waiting for a browser.
rc=0
"$PY" "$DIR/gsc_query.py" --site "sc-domain:$DOMAIN" --days "${GSC_TRACK_DAYS:-28}" \
  --keywords "$KEYWORDS" --csv "$CSV" ${GSC_COUNTRY:+--country "$GSC_COUNTRY"} \
  --no-browser >/dev/null || rc=$?
if [ "$rc" = 4 ]; then
  echo "  ⚠ GSC pulled fine but the history write failed — this run added nothing to the trend."
  problems+=("GSC history write failed"); history_gap=1
elif [ "$rc" != 0 ]; then
  echo "  ✗ GSC failed (exit $rc) — see the message above; Bing and the AI check still run."
  problems+=("GSC: exit $rc"); gsc_rc="$rc"
fi

echo "▶ Bing Webmaster …"
rc=0
"$PY" "$DIR/bing_query.py" --site "https://$DOMAIN" \
  --keywords "$KEYWORDS" --csv "$CSV" >/dev/null || rc=$?
if [ "$rc" = 3 ]; then
  echo "  (Bing skipped — set BING_API_KEY in $ENV to include it)"
elif [ "$rc" = 4 ]; then
  echo "  ⚠ Bing pulled fine but the history write failed — this run added nothing to the trend."
  problems+=("Bing history write failed"); history_gap=1
elif [ "$rc" != 0 ]; then
  # Used to be swallowed; now listed like every other failure (the "needs attention" list).
  echo "  ✗ Bing API error (exit $rc) — run bing_query.py directly to see why"
  problems+=("Bing: exit $rc")
fi

echo "▶ AI answers (does AI name you?) …"
# geo_check.py prints its own warnings and skips, so its stdout is NOT discarded.
# rc 3 = the AI check isn't set up for this site (it's opt-in): not a problem.
# Any other nonzero rc — including a crash — is.
rc=0
"$PY" "$DIR/geo_check.py" "$DOMAIN" || rc=$?
if [ "$rc" != 0 ] && [ "$rc" != 3 ]; then
  problems+=("AI check: exit $rc (see the ⚠ lines above)")
fi

echo "▶ Report page (how people find you on Google) …"
# After the AI check, so the page links to this week's AI report. It writes a page even when
# Google can't be reached (the page says so at the top), so a nonzero exit means no page at
# all. Listed like every other failure; it never replaces GSC's exit code or the history's 4.
rc=0
"$PY" "$DIR/search_report.py" "$DOMAIN" --keywords "$KEYWORDS" --csv "$CSV" \
  --country "${GSC_COUNTRY:-}" || rc=$?
[ "$rc" = 0 ] || problems+=("report page: exit $rc")

echo
echo "═══ Position trend — lower is better; ▲ = improved since last run ═══"
rc=0
"$PY" "$DIR/_history.py" "$CSV" || rc=$?
[ "$rc" = 0 ] || problems+=("keyword trend failed: exit $rc")
echo
rc=0
"$PY" "$DIR/geo_check.py" "$DOMAIN" --trend || rc=$?
[ "$rc" = 0 ] || [ "$rc" = 3 ] || problems+=("AI trend failed: exit $rc")
echo
echo "History CSV: $CSV"

# Nonzero whenever anything went wrong, even though the trends printed fine — a
# launchd log nobody tails wouldn't otherwise surface it.
if [ "${#problems[@]}" -gt 0 ]; then
  echo
  echo "⚠ This run needs attention:"
  for p in "${problems[@]}"; do echo "  - $p"; done
  [ "$gsc_rc" != 0 ] && exit "$gsc_rc"
  [ "$history_gap" != 0 ] && exit 4
  exit 1
fi
