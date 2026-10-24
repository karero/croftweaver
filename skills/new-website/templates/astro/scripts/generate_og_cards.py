#!/usr/bin/env python3
"""Generate branded 1200×630 Open Graph share cards — one per page, plus a default.

Why this exists: when a URL is shared (WhatsApp, Slack, iMessage, X, LinkedIn) the
`og:image` IS the preview. WhatsApp silently DROPS images heavier than ~300 KB and
crops anything that isn't 1.91:1, so a raw screenshot or a square logo previews badly
or not at all. This renders a consistent on-brand 1200×630 JPEG (< 300 KB, real JPEG
bytes) for each page you list below — reproducible, idempotent, and with no edge
function or third-party service needed.

How it fits the suite:
  - Each page sets   image="/images/og/<slug>.jpg"   on its <Base> (src/layouts/Base.astro).
  - Pages with no `image=` fall back to /images/og/default.jpg (the Base default).
  - tests/seo.spec.ts verifies every referenced card exists, is ≤ 300 KB, a real
    JPEG/PNG, and exactly 1200×630 — so a missing or oversized card fails the build.

Run from the project root:   npm run og        (= node scripts/run_og.mjs → python3/py/python)
Add --check to FAIL (exit 1) if any card would exceed 300 KB:   npm run og -- --check

Requires Pillow (local authoring tool — not a runtime dep):   pip3 install Pillow

EDIT TWO THINGS for your site:
  1) BRAND  — colours, logo, brand name. Copy the hexes from src/styles/global.css.
  2) PAGES  — one entry per page that needs its own card (title + up to two subtitles).
Commit the generated public/images/og/*.jpg files; CI only validates them.
"""
from __future__ import annotations
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ModuleNotFoundError:
    sys.exit("Pillow is required: pip3 install Pillow  (one-time, local only)")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public/images/og"

W, H = 1200, 630
MAX_KB = 300

# ── BRAND ─────────────────────────────────────────────────────────────────────
# The card is a DARK share card (light text on a deep background): it reads well in
# every chat app regardless of whether your SITE theme is light or dark. Copy the
# hexes from src/styles/global.css / BRAND.md and tune to taste.
BRAND_NAME = "Your Brand"          # wordmark, top-left
SITE_URL_LABEL = "example.com"     # footer text — your bare domain (no https://)
LOGO = None                        # faint emblem watermark, right side. Point at a
                                   # transparent PNG (e.g. ROOT/"public/logo.png");
                                   # leave None for clean text-only cards. (SVG won't
                                   # load — Pillow needs raster.)
BG_TOP = (30, 33, 64)              # background gradient, top    (deep brand tone)
BG_BOT = (10, 11, 30)              # background gradient, bottom (near-black)
TITLE_COL = (255, 255, 255)        # headline
SUB_COL = (138, 160, 255)          # subtitle lines  (--accent on dark)
ACCENT = (138, 160, 255)           # accent bar      (--accent)
FOOTER_COL = (150, 150, 170)       # footer url (muted)

# Home + fallback card (this is Base.astro's default `image`). Edit for your site.
DEFAULT_TITLE = BRAND_NAME
DEFAULT_SUBTITLES = ["Your one-line promise —", "who it's for, in plain words."]

# ── PAGES ─────────────────────────────────────────────────────────────────────
# One entry per page that should have its OWN card. The slug is the output filename
# AND what the page references: set image="/images/og/<slug>.jpg" on its <Base>.
# Pages you don't list here fall back to default.jpg automatically.
# Title: short, punchy (wraps to ≤ 3 lines). Subtitles: 0–2 supporting lines.
PAGES: list[tuple[str, str, list[str]]] = [
    # ("about",    "What we do",  ["One clear promise —", "for the people it's for."]),
    # ("services", "Services",    ["What you get,", "in plain words."]),
]

# ── Font resolution (cross-platform; first family with a regular+bold pair wins) ──
# (regular_path, regular_index, bold_path, bold_index)
_FONT_CANDIDATES = [
    ("/System/Library/Fonts/HelveticaNeue.ttc", 0, "/System/Library/Fonts/HelveticaNeue.ttc", 1),  # macOS
    ("/System/Library/Fonts/Supplemental/Arial.ttf", 0, "/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),  # Linux
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 0, "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 0),
    ("C:/Windows/Fonts/arial.ttf", 0, "C:/Windows/Fonts/arialbd.ttf", 0),  # Windows
]


def _resolve_fonts():
    for reg, ri, bold, bi in _FONT_CANDIDATES:
        if Path(reg).exists() and Path(bold).exists():
            return (reg, ri), (bold, bi)
    return None, None  # → PIL bitmap default (ugly but never crashes)


_REG, _BOLD = _resolve_fonts()


def font(bold: bool, size: int):
    spec = _BOLD if bold else _REG
    if spec is None:
        return ImageFont.load_default()
    path, idx = spec
    return ImageFont.truetype(path, size, index=idx)


def vgradient(w, h, top, bot):
    base = Image.new("RGB", (1, h))
    px = base.load()
    for y in range(h):
        t = y / (h - 1)
        px[0, y] = tuple(round(top[i] + (bot[i] - top[i]) * t) for i in range(3))
    return base.resize((w, h))


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def fit_title(draw, text, max_w, max_lines=3, hi=84, lo=52):
    """Largest bold size that wraps `text` into ≤ max_lines AND fits max_w.

    Line count alone is not enough: wrap() splits on whitespace, so one long
    unbreakable word (a German compound like "Suchmaschinenoptimierung") becomes
    its own line that can be wider than max_w at EVERY size — a naive line-count
    check accepts it and the headline draws past the card edge.
    """
    for size in range(hi, lo - 1, -2):
        fnt = font(True, size)
        lines = wrap(draw, text, fnt, max_w)
        if len(lines) <= max_lines and all(draw.textlength(ln, font=fnt) <= max_w for ln in lines):
            return fnt, lines, size
    # Nothing fits, even at the smallest size. Fail loud instead of drawing
    # off-card (deliberately unconditional, not gated behind --check: that flag
    # guards file SIZE; clipped text should never ship silently). No automatic
    # hyphenation on purpose — a wrong mid-compound break is worse than an error.
    fnt = font(True, lo)
    lines = wrap(draw, text, fnt, max_w)
    overflow = [ln for ln in lines if draw.textlength(ln, font=fnt) > max_w]
    if overflow:
        sys.exit(
            f"OG card OVERFLOW: {overflow!r} is wider than the {max_w}px text area "
            f"even at the smallest size ({lo}pt). Shorten the title, or insert a "
            f"space at a natural compound boundary (e.g. 'Suchmaschinen Optimierung')."
        )
    # Same fail-loud rule vertically: > max_lines at the smallest size would push
    # the title into the subtitles/footer and off the card bottom.
    sys.exit(
        f"OG card OVERFLOW: title needs {len(lines)} lines even at {lo}pt "
        f"(max {max_lines}). Shorten the title — it will not fit the card."
    )


def _emblem(card):
    """Faint brand emblem watermark on the right (optional)."""
    if not LOGO:
        return W - 2 * 64 - 40  # full text width when there's no emblem
    try:
        em = Image.open(LOGO).convert("RGBA").resize((460, 460), Image.LANCZOS)
    except Exception:
        return W - 2 * 64 - 40
    em.putalpha(em.getchannel("A").point(lambda a: a * 20 // 100))  # ~20% watermark
    card.alpha_composite(em, (W - 460 + 70, (H - 460) // 2))
    return W - 2 * 64 - 120  # leave clearance from the emblem


def build_page(slug: str, title: str, subtitles: list[str]) -> Path:
    card = vgradient(W, H, BG_TOP, BG_BOT).convert("RGBA")
    MARGIN = 64
    text_w = _emblem(card)
    draw = ImageDraw.Draw(card)

    # wordmark
    draw.text((MARGIN, 54), BRAND_NAME, font=font(True, 30), fill=TITLE_COL)

    # title
    fnt, lines, size = fit_title(draw, title, text_w)
    lh = round(size * 1.12)
    y = 196
    draw.rounded_rectangle((MARGIN, y, MARGIN + 64, y + 7), radius=3, fill=ACCENT)
    y += 30
    for ln in lines:
        draw.text((MARGIN, y), ln, font=fnt, fill=TITLE_COL)
        y += lh

    # subtitles — same width rule as the title: never draw past the text area
    # (long German compounds clip here just as silently as they did in titles).
    sub_font = font(False, 30)
    for i, sub in enumerate(subtitles[:2]):
        if draw.textlength(sub, font=sub_font) > text_w:
            sys.exit(
                f"OG card OVERFLOW: subtitle {sub!r} is wider than the {text_w}px "
                f"text area. Shorten it — subtitles render at a fixed 30pt."
            )
        draw.text((MARGIN, y + 10 + i * 40), sub, font=sub_font, fill=SUB_COL)

    # footer url
    draw.text((MARGIN, H - 52), SITE_URL_LABEL, font=font(False, 22), fill=FOOTER_COL)
    return _encode(card, OUT / f"{slug}.jpg")


def _encode(card, out: Path) -> Path:
    """Save as progressive JPEG, stepping quality down to stay ≤ MAX_KB."""
    out.parent.mkdir(parents=True, exist_ok=True)
    final = card.convert("RGB")
    for q in (88, 84, 80, 76, 72):
        final.save(out, "JPEG", quality=q, optimize=True, progressive=True)
        if out.stat().st_size <= MAX_KB * 1024:
            break
    return out


def main():
    check = "--check" in sys.argv
    over = []
    jobs = [("default (home + fallback)", lambda: build_page("default", DEFAULT_TITLE, DEFAULT_SUBTITLES))]
    jobs += [(slug, lambda s=slug, t=title, sub=subs: build_page(s, t, sub)) for slug, title, subs in PAGES]
    for label, make in jobs:
        out = make()
        kb = out.stat().st_size / 1024
        flag = "  ⚠ OVER" if kb > MAX_KB else ""
        if kb > MAX_KB:
            over.append(out.name)
        with Image.open(out) as im:
            dim = f"{im.width}×{im.height}"
        print(f"  {label:34} {dim:9} {kb:6.1f} KB{flag}")
    print(f"\n{len(jobs)} card(s) → {OUT.relative_to(ROOT)}")
    if over:
        print(f"OVER {MAX_KB} KB: {over}")
        if check:
            sys.exit(1)


if __name__ == "__main__":
    main()
