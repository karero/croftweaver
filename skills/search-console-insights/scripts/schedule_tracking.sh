#!/usr/bin/env bash
# schedule_tracking.sh — opt-in WEEKLY trend tracking via launchd (macOS).
#
# Runs track.sh on a schedule (GSC + Bing → history CSV → trend), logging to
# ~/.config/gsc-insights/logs/<domain>.log (dots become dashes: example-com.log), so the
# trend data accumulates unattended
# and "is my ranking improving?" always has real week-over-week history to answer from.
#
# One LaunchAgent PER SITE — the user chooses which sites to schedule and can remove
# any independently. macOS uses launchd (NOT cron, by project policy). On Linux, run
# the same track.sh from a systemd user timer or cron instead.
#
#   bash schedule_tracking.sh install <domain> "<comma,keywords>" [weekday 0-7] [hour 0-23]
#     weekday: launchd values — 1=Mon … 6=Sat, and BOTH 0 and 7 = Sunday (default 1=Mon).
#     The minute is picked for you: each site starts in its own slot (see "Start minute").
#   bash schedule_tracking.sh remove  <domain>
#   bash schedule_tracking.sh list
#   bash schedule_tracking.sh status <domain>   # exact match for ONE site — see below
#
# `list` prints SANITIZED labels (dots/etc. become dashes: example.com -> example-com),
# not the literal domain, and two different domains can sanitize to the same label — so
# it is NOT reliable for "is <this exact domain> scheduled?". `status <domain>` answers
# that precisely instead: sanitize() is lossy (e.g. "a.b-c.com" and "a-b.c.com" both land
# on "a-b-c-com"), so plist EXISTENCE at the derived path is not proof it's THIS domain's
# plist — status also reads the literal domain back out of ProgramArguments (which install
# writes verbatim) via `plutil -extract` and only reports "scheduled" if that literal
# domain actually matches. It also cross-checks `launchctl print` so a plist that exists
# but never successfully loaded (a failed bootstrap, e.g. a permissions issue) reports
# "not scheduled" rather than trusting file-existence alone.
set -euo pipefail

DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
LA_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/.config/gsc-insights/logs"
PREFIX="com.gsc-insights"

sanitize() { echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g'; }
label_for() { echo "$PREFIX.$(sanitize "$1")"; }
plist_for() { echo "$LA_DIR/$(label_for "$1").plist"; }
# The literal domain install wrote into the plist ("" if no plist / not readable).
plist_domain() { plutil -extract ProgramArguments.2 raw -o - "$1" 2>/dev/null || true; }
plist_env() { plutil -extract "EnvironmentVariables.$2" raw -o - "$1" 2>/dev/null || true; }
lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }
site_settings_file() { echo "$HOME/.config/gsc-insights/sites/$(lower "$1").json"; }
# JSON through python, so a keyword with a quote or a backslash can't break the file.
write_site_settings() {
  local f py; f="$(site_settings_file "$1")"; mkdir -p "$(dirname "$f")"
  py="$HOME/.config/gsc-insights/venv/bin/python"; [ -x "$py" ] || py=python3
  "$py" -c 'import datetime,json,sys; d,k,c,h,f=sys.argv[1:6]; json.dump({"domain":d,"keywords":[x.strip() for x in k.split(",") if x.strip()],"country":c,"csv":h,"recorded":datetime.date.today().isoformat()}, open(f,"w"), ensure_ascii=False, indent=1)' \
    "$1" "$2" "$3" "$4" "$f" || echo "  ⚠ could not write $f — the Google report page will read the job instead"
}
# Values land inside XML text; an unescaped & or < makes a plist launchd rejects.
xml_esc() { printf '%s' "$1" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'; }
plist_when() { plutil -extract "StartCalendarInterval.$2" raw -o - "$1" 2>/dev/null || true; }
# A day and hour in one form, so Sunday 7 matches Sunday 0 and "09" matches 9.
nozero() { local n="${1#"${1%%[!0]*}"}"; echo "${n:-0}"; }
day_hour() { local d; d="$(nozero "$1")"; [ "$d" = 7 ] && d=0; echo "$d $(nozero "$2")"; }

cmd="${1:-}"; shift || true
case "$cmd" in
  install)
    domain="${1:?domain required (e.g. example.com)}"
    keywords="${2:?keywords required (comma-separated)}"
    weekday="${3:-1}"   # 1 = Monday (launchd: 0 & 7 = Sunday)
    hour="${4:-9}"
    [ -x "$DIR/track.sh" ] || chmod +x "$DIR/track.sh"
    mkdir -p "$LA_DIR" "$LOG_DIR"
    label="$(label_for "$domain")"
    plist="$(plist_for "$domain")"
    log="$LOG_DIR/$(sanitize "$domain").log"
    # Per-site settings ride in the plist's environment (track.sh lets them beat
    # the shared .env): GSC_HISTORY_CSV (this site's own history file) and
    # GSC_COUNTRY (market filter). Set in the caller's environment they are written
    # as given -- an empty value clears one. Unset, they are carried over from THIS
    # domain's existing plist: re-installing (to add a keyword, say) used to rewrite
    # the plist without them, so a site whose history lived in its own file silently
    # went back to the shared default -- one trend split across two files. Domains
    # are case-insensitive, and so is the "is this the same site" check; the
    # sanitize() collision case ("a.b-c.com" vs "a-b.c.com") carries nothing over.
    same_site=""
    if [ "$(lower "$(plist_domain "$plist")")" = "$(lower "$domain")" ]; then
      same_site=1
      [ -n "${GSC_HISTORY_CSV+set}" ] || GSC_HISTORY_CSV="$(plist_env "$plist" GSC_HISTORY_CSV)"
      [ -n "${GSC_COUNTRY+set}" ] || GSC_COUNTRY="$(plist_env "$plist" GSC_COUNTRY)"
    fi
    hist="${GSC_HISTORY_CSV:-}"; country="${GSC_COUNTRY:-}"
    # Start minute. Every job used to start at :00, so several sites ran at once and the
    # AI check's parallel calls hit the providers' rate limits (HTTP 429 from Anthropic
    # and Perplexity, 2026-10-12). Re-installing at the same day and hour keeps this
    # site's minute unless another site's job has it too (as every job from before this
    # change does); otherwise it takes the first of :00, :15, :30, :45 (then the
    # 5-minute gaps) that no other site's job uses at that day and hour.
    want="$(day_hour "$weekday" "$hour")"; taken=" "
    for other in "$LA_DIR/$PREFIX."*.plist; do
      [ -f "$other" ] && [ "$other" != "$plist" ] || continue
      d="$(plist_when "$other" Weekday)"; h="$(plist_when "$other" Hour)"
      [ -n "$d" ] && [ -n "$h" ] && [ "$(day_hour "$d" "$h")" = "$want" ] || continue
      taken="$taken$(nozero "$(plist_when "$other" Minute)") "
    done
    minute=""
    if [ -n "$same_site" ] && [ "$(day_hour "$(plist_when "$plist" Weekday)" "$(plist_when "$plist" Hour)")" = "$want" ]; then
      minute="$(plist_when "$plist" Minute)"
      if [ -n "$minute" ]; then
        minute="$(nozero "$minute")"
        case "$taken" in *" $minute "*) minute="" ;; esac
      fi
    fi
    if [ -z "$minute" ]; then
      for m in 0 15 30 45 5 20 35 50 10 25 40 55; do
        case "$taken" in *" $m "*) ;; *) minute=$m; break ;; esac
      done
      if [ -z "$minute" ]; then
        minute=0; echo "  ⚠ every slot at this day and hour is taken; this site shares :00 — consider another hour"
      fi
    fi
    cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$(xml_esc "$label")</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$(xml_esc "$DIR/track.sh")</string>
    <string>$(xml_esc "$domain")</string>
    <string>$(xml_esc "$keywords")</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>GSC_HISTORY_CSV</key><string>$(xml_esc "$hist")</string>
    <key>GSC_COUNTRY</key><string>$(xml_esc "$country")</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>$weekday</integer>
    <key>Hour</key><integer>$hour</integer>
    <key>Minute</key><integer>$minute</integer>
  </dict>
  <key>StandardOutPath</key><string>$(xml_esc "$log")</string>
  <key>StandardErrorPath</key><string>$(xml_esc "$log")</string>
  <key>RunAtLoad</key><false/>
</dict></plist>
PLIST
    # The same settings as a small file an on-demand report can read without launchd
    # (search_report.py; docs/reviews/SKILL-PLAN-gsc-report.md, Design → Site settings file).
    # An empty country or history means "none", as it does for the job.
    write_site_settings "$domain" "$keywords" "$country" "$hist"
    # Reload idempotently. bootout/bootstrap is the modern path; fall back to load/unload.
    launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || launchctl unload "$plist" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$plist" 2>/dev/null || launchctl load "$plist"
    echo "✓ Weekly tracking scheduled for $domain — weekday $weekday at $(nozero "$hour"):$(printf '%02d' "$minute")."
    echo "  label : $label"
    echo "  log   : $log"
    echo "  history: ${hist:-(shared default file)}"
    echo "  country: ${country:-(none — blended global numbers)}"
    # Same environment the job gets, so a hand run lands in the same history file.
    echo "  test now:  GSC_HISTORY_CSV=\"$hist\" GSC_COUNTRY=\"$country\" bash \"$DIR/track.sh\" \"$domain\" \"$keywords\""
    ;;
  remove)
    domain="${1:?domain required}"
    label="$(label_for "$domain")"; plist="$(plist_for "$domain")"
    if [ -f "$plist" ]; then
      launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || launchctl unload "$plist" 2>/dev/null || true
      rm -f "$plist" "$(site_settings_file "$domain")"
      echo "✓ Removed weekly tracking for $domain."
    else
      echo "No schedule found for $domain."
    fi
    ;;
  list)
    found=$(ls "$LA_DIR/$PREFIX."*.plist 2>/dev/null || true)
    if [ -n "$found" ]; then
      echo "Scheduled sites (label form — dots/etc. shown as dashes; use 'status <domain>' to check one exact domain):"
      echo "$found" | sed 's#.*/'"$PREFIX"'\.##; s/\.plist$//; s/^/  - /'
    else
      echo "No sites scheduled yet."
    fi
    ;;
  status)
    domain="${1:?domain required}"
    plist="$(plist_for "$domain")"
    label="$(label_for "$domain")"
    recorded="$(plist_domain "$plist")"
    if [ "$(lower "$recorded")" != "$(lower "$domain")" ]; then
      # Either no plist at that derived path, or one exists but a DIFFERENT
      # domain landed there via a sanitize() collision (e.g. "a.b-c.com" and
      # "a-b.c.com" both sanitize to "a-b-c-com") -- either way, THIS domain
      # is not scheduled.
      echo "not scheduled"
    elif launchctl print "gui/$(id -u)/$label" >/dev/null 2>&1; then
      echo "scheduled"
    else
      echo "not scheduled (plist exists but the launchd job isn't loaded — try re-running install)"
    fi
    ;;
  *)
    echo "usage: schedule_tracking.sh install <domain> \"<keywords>\" [weekday 0-7] [hour 0-23]"
    echo "       schedule_tracking.sh remove <domain>"
    echo "       schedule_tracking.sh list"
    echo "       schedule_tracking.sh status <domain>"
    exit 1
    ;;
esac
