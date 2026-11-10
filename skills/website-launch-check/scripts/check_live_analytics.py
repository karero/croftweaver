#!/usr/bin/env python3
"""check_live_analytics.py — compare the live home page's analytics tag with src/config.ts.

    python3 check_live_analytics.py <live address>    # run in the site's folder (where src/config.ts is)

Exit 0: the page matches the config. Exit 1: it does not (what was found, and likely causes).
Exit 2: not checked (config unreadable, page not fetched); never a verdict. Reads one page, the home
page, with a cache-busting query; on Workers static assets a fresh query is no proof of a fresh
page, so run it again a minute after a publish before acting on a failure. The counting follows
the starter's tests/check_analytics_gate.sh, which does the same on a build. Standard library only.
"""
import http.client
import random
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG = Path("src/config.ts")
USE_LINE = re.compile(r"^export const USE_ANALYTICS = (true|false);?[ \t]*(//.*)?$")
HOST_LINE = re.compile(r"""^\s*scriptHost:\s*['"]([^'"]*)['"]""")
ID_LINE = re.compile(r"""^\s*scriptId:\s*['"]([^'"]*)['"]""")
# A line that starts with the mode key must be exactly one of the starter's forms, else the file is
# refused: anything cleverer (an expression, a computed or quoted key) is not read, never guessed.
MODE_START = re.compile(r"""^\s*(?:\[|['"`]*mode\b)""")
MODE_LINE = re.compile(
    r"""^\s*mode:\s*'(script|server)'(?:\s+as\s+'(?:script|server)'(?:\s*\|\s*'(?:script|server)')?)?\s*,?\s*(?://.*)?$""")
BLOCK_START = re.compile(r"^export const ANALYTICS\s*=\s*\{")
BLOCK_END = re.compile(r"^\}")

# The gate's expressions (check_analytics_gate.sh, tags_program): comments dropped outside
# script elements, an opening tag read with its quoted values, one attribute at a time.
STRIP = re.compile(
    r"""(<script(?=[\s/>])(?:[^>"']|"[^"]*"|'[^']*')*>.*?</script\s*>)|<!--.*?-->""", re.I | re.S | re.A)
SCRIPT_OPEN = re.compile(r"<script(?=[\s/>])", re.I | re.A)
ATTR = re.compile(r"""\s*([^\s"'>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?""", re.A)
OTHER_SRC = re.compile(r"/js/(?:script(?:\.[\w.-]+)?|pa-[\w-]+)\.js(?:[?#]|$)", re.A)
BODY = re.compile(r"[^>]*>(.*?)</script\b", re.I | re.S | re.A)
STUB = re.compile(r"\bplausible\.init\s*\(", re.A)
JS_TYPES = {"", "text/javascript", "application/javascript", "module"}


class NotChecked(Exception):
    pass


def read_config():
    """Returns (use_analytics, src, scriptId, mode)."""
    try:
        text = CONFIG.read_text(encoding="utf-8")
    except OSError as e:
        raise NotChecked(f"cannot read {CONFIG}: {e.strerror or e}")
    except UnicodeError:
        raise NotChecked(f"{CONFIG} is not UTF-8 text")
    lines = text.splitlines()
    uses = [m.group(1) for m in map(USE_LINE.match, lines) if m]
    if not uses:
        if "USE_ANALYTICS" in text:
            raise NotChecked(
                f'{CONFIG} names USE_ANALYTICS, but not as one line "export const USE_ANALYTICS = true;" '
                'or "= false;" (a // comment after it is fine)')
        uses = ["true"]  # a site made before the switch
    if len(uses) > 1:
        raise NotChecked(f"{CONFIG} has more than one USE_ANALYTICS line")
    block, inside = [], False
    for line in lines:
        if not inside and BLOCK_START.match(line):
            inside = True
        elif inside and BLOCK_END.match(line):
            break
        if inside:
            block.append(line)
    if not block:
        raise NotChecked(f'no "export const ANALYTICS = {{ … }}" block in {CONFIG}')

    def first(pattern):
        found = [m.group(1) for m in map(pattern.match, block) if m]
        return found[0] if found else ""

    host, sid = first(HOST_LINE), first(ID_LINE)
    host = host[:-1] if host.endswith("/") else host
    if not host or not sid:
        raise NotChecked(f"no scriptHost: '…' and scriptId: '…' lines in the ANALYTICS block of {CONFIG}")
    if any("/*" in line for line in block):
        raise NotChecked(f"the ANALYTICS block of {CONFIG} has a /* comment: use // comments there")
    starts = [line for line in block if MODE_START.match(line)]
    found = [m.group(1) for m in map(MODE_LINE.match, starts) if m]
    if len(found) != len(starts) or len(starts) > 1:
        raise NotChecked(f"the mode line in the ANALYTICS block of {CONFIG} is not one line written as "
                         "mode: 'script' or 'server' (a // comment after it is fine)")
    mode = found[0] if found else "script"
    return uses[0] == "true", f"{host}/js/{sid}.js", sid, mode


def fetch(address):
    if not re.match(r"https?://[^/\s]", address):
        raise NotChecked(f"the address {address!r} is not an http(s) address")
    cb = f"cb={random.getrandbits(40):x}"
    url = f"{address}&{cb}" if "?" in address else f"{address.rstrip('/')}/?{cb}"
    req = urllib.request.Request(url, headers={"User-Agent": "croftweaver-launch-check"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode("utf-8", errors="replace")
            status = r.status
    except urllib.error.HTTPError as e:
        raise NotChecked(f"{url} answered {e.code}")
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as e:
        raise NotChecked(f"{url} could not be fetched: {getattr(e, 'reason', e)}")
    if not 200 <= status < 300:
        raise NotChecked(f"{url} answered {status}")
    if not body.strip():
        raise NotChecked(f"{url} answered with an empty page")
    return body


def count_tags(page, want):
    """Returns (script, stub, other), as the gate's counter does."""
    text = STRIP.sub(lambda m: m.group(1) or "", page)
    script = stub = other = 0
    pos = 0
    while True:
        m = SCRIPT_OPEN.search(text, pos)
        if not m:
            break
        pos = m.end()
        attrs = {}
        while True:
            a = ATTR.match(text, pos)
            if not a:
                break
            pos = a.end()
            val = a.group(2) if a.group(2) is not None else a.group(3) if a.group(3) is not None \
                else a.group(4) if a.group(4) is not None else ""
            attrs[a.group(1).lower()] = val
        if "src" in attrs:
            if attrs["src"] == want:
                script += 1
            elif OTHER_SRC.search(attrs["src"]):
                other += 1
            elif "data-domain" in attrs:
                other += 1
        else:
            if "data-domain" in attrs:
                other += 1
            b = BODY.match(text, pos)
            if b:
                pos = b.end()
                if attrs.get("type", "").lower() in JS_TYPES and STUB.search(b.group(1)):
                    stub += 1
    return script, stub, other


def main(argv):
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) != 2:
        print("usage: check_live_analytics.py <live address>   (run in the site's folder)", file=sys.stderr)
        return 2
    try:
        on, want, sid, mode = read_config()
        page = fetch(argv[1])
    except NotChecked as e:
        print(f"not checked: {e}")
        return 2
    script, stub, other = count_tags(page, want)
    found = f"{script} analytics script tag(s), {stub} init stub(s), {other} other analytics tag(s)"
    if not on:
        if script or stub or other:
            print(f"✗ the live page carries an analytics tag that {CONFIG} has off: {found}.")
            return 1
        if want in page or sid in page:
            print(f"✗ the live page names the analytics script or id ({want}); check whether it loads analytics.")
            return 1
        print(f"✓ analytics is off in {CONFIG}, and the live page has no tag and does not name the script.")
        return 0
    if mode == "server":
        if script or stub or other:
            print(f"✗ browser analytics on the page in server mode: {found}.")
            return 1
        print(f"✓ server mode in {CONFIG}, and the live page carries no browser tag.")
        return 0
    if (script, stub, other) == (1, 1, 0):
        print(f"✓ the live page carries the analytics tag {CONFIG} asks for ({want}): {found}.")
        return 0
    print(f"✗ {CONFIG} has analytics on ({want}), but the live page has {found}; expected 1, 1 and 0.")
    if script == 0 and other == 0:
        print("  The page carries no analytics script tag the config names. Likely causes:")
        print("  - the build that made the live site had analytics off;")
        print("  - on Workers Builds, the enabled: line must read WORKERS_CI_BRANCH (the 0.35 release notes),")
        print("    or the build needs the variable CF_PAGES_BRANCH=<the value of PROD_BRANCH in src/config.ts>;")
        print("  - on Pages, the project's production branch must be the value of PROD_BRANCH.")
        print("  Whether the server side counts anything is not checked (a Pages site with PLAUSIBLE_HOST and")
        print("  PLAUSIBLE_DOMAIN set may send events from its Function whatever src/config.ts says).")
    elif script == 0:
        print(f"  The tag on the page is not the one {CONFIG} names (another id or host, or the older form).")
    print("  If the site was just published, the page may come from a cache: run this again in a minute.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
