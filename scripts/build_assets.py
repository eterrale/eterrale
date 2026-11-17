#!/usr/bin/env python3
"""Build every SVG asset and README.md from profile.config.json.

Usage (from repo root):  python3 scripts/build_assets.py
Standard library only.
"""
import base64
import json
import math
import mimetypes
import random
import re
import sys
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

sys.dont_write_bytecode = True  # keep scripts/__pycache__ out of the repo
from gen_lowpoly import mesh  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# ---- palette: sober violet -------------------------------------------------------
# One violet family plus a near-white lavender for text. Change colours here only.
INK = "#0d0818"        # deepest violet-black: tracks, screen background
PANEL = "#130c23"      # window / card body
PANEL_HI = "#1e1436"   # top of panels, menu bars
RAISED = "#2b1f4f"     # control strip, raised surfaces
LINE = "#4a3a80"       # hairline borders
LINE_HI = "#6f5bb8"    # emphasised borders
ACCENT = "#8f72e8"     # the violet
ACCENT_HI = "#b7a3f5"  # soft violet: glyphs, sparkles, highlights
TEXT = "#ece7fb"       # near-white lavender
MUTED = "#a79ccb"      # secondary text
PLUM = "#a24d9c"       # close buttons
ROSE = "#e7a6cf"       # soft powder pink: only ever the warm end of a gradient
ROSE_DEEP = "#b8689f"  # muted mauve-pink

SANS = "'Trebuchet MS', 'Segoe UI', Verdana, sans-serif"
MONO = "'Courier New', ui-monospace, Menlo, Consolas, monospace"
MONO_W = 0.6  # approx glyph width / font-size for the mono stack

MESH_HERO = [INK, "#22154a", "#3d2a85", "#6a50c0"]  # banner / footer low-poly
MESH_CARD = ["#0f0820", "#190f33", "#241649", "#2f1d5c"]  # only used by card_style "lowpoly"

CARD_STYLES = ("flat", "glow", "grid", "dither", "lowpoly")


# ---- helpers ---------------------------------------------------------------
def svg(width, height, body, defs=""):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d" role="img">\n<defs>%s</defs>\n%s\n</svg>\n'
        % (width, height, width, height, defs, body)
    )


def write(name, content):
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / name).write_text(content, encoding="utf-8")
    print("  wrote assets/%s (%d bytes)" % (name, len(content.encode("utf-8"))))


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def attr(text):
    return escape(text, {'"': "&quot;"})


def data_uri(path):
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return "data:%s;base64,%s" % (mime, base64.b64encode(path.read_bytes()).decode())


def hash_seed(s):
    return sum(ord(c) * (i + 1) for i, c in enumerate(s))


def sparkle(x, y, r, delay=0.0, color="#ffffff", dur=3.0):
    """Solid 4-point star that pulses."""
    d = "M0 %g Q0 0 %g 0 Q0 0 0 %g Q0 0 %g 0 Q0 0 0 %g Z" % (-r, r, r, -r, -r)
    return (
        '<g transform="translate(%.1f %.1f)"><g>'
        '<path d="%s" fill="%s"/>'
        '<animateTransform attributeName="transform" type="scale" values="0.35;1;0.35" '
        'dur="%gs" begin="%gs" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0.25;1;0.25" dur="%gs" begin="%gs" repeatCount="indefinite"/>'
        "</g></g>" % (x, y, d, color, dur, delay, dur, delay)
    )


def line_sparkle(x, y, r, delay=0.0, color="#ffffff", dur=3.6):
    """Thin 4-point sparkle: a plus with a gap in the middle and short diagonal ticks."""
    g, a, b = r * 0.3, r * 0.4, r * 0.62
    d = (f"M0 {-r:g}V{-g:g}M0 {g:g}V{r:g}M{-r:g} 0H{-g:g}M{g:g} 0H{r:g}"
         f"M{a:g} {-a:g}L{b:g} {-b:g}M{-a:g} {-a:g}L{-b:g} {-b:g}"
         f"M{a:g} {a:g}L{b:g} {b:g}M{-a:g} {a:g}L{-b:g} {b:g}")
    return (
        f'<g transform="translate({x:.1f} {y:.1f})"><path d="{d}" fill="none" stroke="{color}" '
        'stroke-width="1.6" stroke-linecap="round">'
        f'<animate attributeName="opacity" values="0.3;1;0.3" dur="{dur:g}s" begin="{delay:g}s" repeatCount="indefinite"/>'
        "</path></g>"
    )


def sparkles(w, h, n, seed, rmin=5, rmax=13, colors=("#ffffff", ACCENT_HI, "#d8ccfa"), box=None, line_ratio=0.3,
             avoid=()):
    """n random sparkles (a mix of solid and thin-line ones) inside `box`, never inside an `avoid` rectangle."""
    rng = random.Random(seed)
    x0, y0, x1, y1 = box or (15, 12, w - 15, h - 12)
    out = []
    for _ in range(n):
        for _try in range(30):
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if not any(ax0 <= x <= ax1 and ay0 <= y <= ay1 for ax0, ay0, ax1, ay1 in avoid):
                break
        r = rng.uniform(rmin, rmax)
        delay, color, dur = rng.uniform(0, 3), rng.choice(colors), rng.uniform(2.4, 4.2)
        if rng.random() < line_ratio:
            out.append(line_sparkle(x, y, r * 1.3, delay, color, dur))
        else:
            out.append(sparkle(x, y, r, delay, color, dur))
    return "\n".join(out)


CHROME_DEFS = (
    # violet chrome for the big titles
    '<linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#ffffff"/><stop offset="0.45" stop-color="#f1ecff"/>'
    '<stop offset="0.5" stop-color="#d4c6fa"/><stop offset="1" stop-color="#c38fd4"/></linearGradient>'
    # window title bars
    '<linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">'
    '<stop offset="0" stop-color="#6a50c0"/><stop offset="1" stop-color="#9a5ca8"/></linearGradient><linearGradient id="edge" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8f72e8"/><stop offset="1" stop-color="#e7a6cf"/></linearGradient>'
    # glossy window buttons: violet (min/max) and plum (close)
    '<linearGradient id="btn" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#d5c8fb"/><stop offset="0.5" stop-color="#9c84ee"/>'
    '<stop offset="0.52" stop-color="#7c61d6"/><stop offset="1" stop-color="#5a42b0"/></linearGradient>'
    '<linearGradient id="btnx" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#ecc4ea"/><stop offset="0.5" stop-color="#c476bc"/>'
    f'<stop offset="0.52" stop-color="{PLUM}"/><stop offset="1" stop-color="#7a3376"/></linearGradient>'
    # skill chips: three close tones of violet
    '<linearGradient id="pill" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#3f2e76"/><stop offset="1" stop-color="#2a1e52"/></linearGradient>'
    '<linearGradient id="pill2" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#4a3786"/><stop offset="1" stop-color="#33255f"/></linearGradient>'
    '<linearGradient id="pill3" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#36306f"/><stop offset="1" stop-color="#252058"/></linearGradient>'
)

# extra gradients for the media-player strip in the about window
CONTROL_DEFS = (
    '<linearGradient id="ctrl" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{RAISED}"/><stop offset="1" stop-color="#170f2c"/></linearGradient>'
    '<radialGradient id="playbtn" cx="0.4" cy="0.3" r="0.8">'
    f'<stop offset="0" stop-color="#d9ccfb"/><stop offset="0.55" stop-color="{ACCENT}"/>'
    '<stop offset="1" stop-color="#4a359a"/></radialGradient>'
    '<radialGradient id="knob" cx="0.4" cy="0.35" r="0.7">'
    f'<stop offset="0" stop-color="#ffffff"/><stop offset="0.6" stop-color="#d4c8fa"/>'
    f'<stop offset="1" stop-color="{ACCENT}"/></radialGradient>'
    '<linearGradient id="seekfill" x1="0" y1="0" x2="1" y2="0">'
    f'<stop offset="0" stop-color="{ACCENT}"/><stop offset="1" stop-color="{ROSE}"/></linearGradient>'
    '<linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="#d8ccfa"/><stop offset="1" stop-color="{ACCENT}"/></linearGradient>'
)


def window_chrome(w, h, title, x=0, y=0, bar=34, body_fill=PANEL):
    """A Y2K / XP-style window: glossy title bar with min, max and close buttons."""
    cy = y + bar / 2
    btns = ""
    for i, (gid, kind) in enumerate((("btnx", "close"), ("btn", "max"), ("btn", "min"))):
        cx = x + w - 24 - i * 28
        btns += (f'<rect x="{cx - 11:g}" y="{cy - 11:g}" width="22" height="22" rx="5" '
                 f'fill="url(#{gid})" stroke="{TEXT}" stroke-width="1.4"/>')
        if kind == "close":
            btns += (f'<path d="M{cx - 4:g} {cy - 4:g}l8 8m0 -8l-8 8" stroke="#fff" '
                     'stroke-width="2.4" stroke-linecap="round"/>')
        elif kind == "max":
            btns += (f'<rect x="{cx - 4.5:g}" y="{cy - 4.5:g}" width="9" height="9" fill="none" '
                     'stroke="#fff" stroke-width="2"/>')
        else:
            btns += f'<rect x="{cx - 4.5:g}" y="{cy + 1.5:g}" width="9" height="3" fill="#fff"/>'
    gloss = (f'<path d="M{x} {y + bar / 2:g}V{y + 10}Q{x} {y} {x + 10} {y}H{x + w - 10}'
             f'Q{x + w} {y} {x + w} {y + 10}V{y + bar / 2:g}Z" fill="#fff" opacity="0.14"/>')
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{body_fill}" stroke="{LINE_HI}" stroke-width="2"/>'
        f'<rect x="{x}" y="{y}" width="{w}" height="{bar}" rx="10" fill="url(#bar)"/>'
        f'<rect x="{x}" y="{y + bar - 12}" width="{w}" height="12" fill="url(#bar)"/>'
        f'{gloss}'
        f'<text x="{x + 17}" y="{y + 24}" font-family="{SANS}" font-size="15" font-weight="700" fill="#000" opacity="0.35">{escape(title)}</text>'
        f'<text x="{x + 16}" y="{y + 23}" font-family="{SANS}" font-size="15" font-weight="700" fill="#fff">{escape(title)}</text>'
        f'{btns}'
    )


def pill_width(text, font=13):
    return int(len(text) * font * MONO_W + 26)


def pill(x, y, text, fill_id="pill", font=13):
    """A skill chip: dark violet body, hairline border, light text."""
    w = pill_width(text, font)
    return w, (
        f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="15" fill="url(#{fill_id})" stroke="{LINE_HI}" stroke-width="1.2"/>'
        f'<rect x="{x + 9}" y="{y + 1.5}" width="{w - 18}" height="1" rx="0.5" fill="#fff" opacity="0.22"/>'
        f'<text x="{x + w / 2:g}" y="{y + 20}" text-anchor="middle" font-family="{MONO}" font-size="{font}" '
        f'font-weight="700" fill="{TEXT}">{escape(text)}</text>'
    )


def card_style(cfg):
    style = cfg.get("card_style", "flat")
    if style not in CARD_STYLES:
        sys.exit('card_style must be one of: %s (got "%s")' % (", ".join(CARD_STYLES), style))
    return style


def card_bg(style, w, h, seed=1):
    """Background for a card or window body: returns (defs, markup). The caller clips the markup."""
    defs = (
        '<linearGradient id="panelbg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{PANEL_HI}"/><stop offset="1" stop-color="{PANEL}"/></linearGradient>'
    )
    base = f'<rect width="{w}" height="{h}" fill="url(#panelbg)"/>'
    if style == "glow":  # soft violet light coming from the top-right corner
        defs += (
            f'<radialGradient id="cardglow" gradientUnits="userSpaceOnUse" cx="{w * 0.9:g}" cy="0" r="{w * 0.7:g}">'
            f'<stop offset="0" stop-color="{ACCENT}" stop-opacity="0.45"/>'
            f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient>'
        )
        return defs, base + f'<rect width="{w}" height="{h}" fill="url(#cardglow)"/>'
    if style == "grid":  # hairline grid that fades out towards the bottom-right
        step = 22
        defs += (
            f'<pattern id="cardgrid" width="{step}" height="{step}" patternUnits="userSpaceOnUse">'
            f'<path d="M{step} 0H0V{step}" fill="none" stroke="{ACCENT_HI}" stroke-width="1" opacity="0.13"/></pattern>'
            f'<linearGradient id="gridfade" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{w}" y2="{h}">'
            f'<stop offset="0" stop-color="{PANEL}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{PANEL}" stop-opacity="0.95"/></linearGradient>'
        )
        return defs, (base + f'<rect width="{w}" height="{h}" fill="url(#cardgrid)"/>'
                      f'<rect width="{w}" height="{h}" fill="url(#gridfade)"/>')
    if style == "dither":  # ordered-dither gradient: pixel dots thinning out from top to bottom
        cell, levels = 3, 7
        bayer = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
        band_h = math.ceil(h / (levels + 1))
        bands = ""
        for k in range(levels):
            lv = levels - k  # lv of the 16 cells of each 4x4 tile are lit
            rects = "".join(f'<rect x="{c * cell}" y="{r * cell}" width="{cell}" height="{cell}"/>'
                            for r in range(4) for c in range(4) if bayer[r][c] < lv)
            defs += (f'<pattern id="dth{lv}" width="{4 * cell}" height="{4 * cell}" patternUnits="userSpaceOnUse" '
                     f'fill="{ACCENT}" fill-opacity="0.2">{rects}</pattern>')
            bands += f'<rect y="{k * band_h}" width="{w}" height="{band_h}" fill="url(#dth{lv})"/>'
        return defs, base + bands
    if style == "lowpoly":  # the original look, kept for comparison
        return defs, (mesh(w, h, 40, MESH_CARD, seed=seed, bias=0.5)
                      + f'<rect width="{w}" height="{h}" fill="{PANEL}" opacity="0.55"/>')
    return defs, base  # "flat"


# ---- assets ----------------------------------------------------------------
# 5x7 pixel font, lowercase. Rows 0-6 sit on the baseline; g j p q y add two descender rows.
PIXEL_FONT = {
    "a": [".....", ".....", ".###.", "....#", ".####", "#...#", ".####"],
    "b": ["#....", "#....", "####.", "#...#", "#...#", "#...#", "####."],
    "c": [".....", ".....", ".####", "#....", "#....", "#....", ".####"],
    "d": ["....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"],
    "e": [".....", ".....", ".###.", "#...#", "#####", "#....", ".####"],
    "f": ["..##.", ".#...", "####.", ".#...", ".#...", ".#...", ".#..."],
    "g": [".....", ".....", ".####", "#...#", "#...#", "#...#", ".####", "....#", ".###."],
    "h": ["#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"],
    "i": ["..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."],
    "j": ["...#.", ".....", "..##.", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "k": ["#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."],
    "l": [".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "m": [".....", ".....", "####.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"],
    "n": [".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"],
    "o": [".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."],
    "p": [".....", ".....", "####.", "#...#", "#...#", "#...#", "####.", "#....", "#...."],
    "q": [".....", ".....", ".####", "#...#", "#...#", "#...#", ".####", "....#", "....#"],
    "r": [".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."],
    "s": [".....", ".....", ".####", "#....", ".###.", "....#", "####."],
    "t": [".#...", ".#...", "####.", ".#...", ".#...", ".#..#", "..##."],
    "u": [".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####"],
    "v": [".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "w": [".....", ".....", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."],
    "x": [".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"],
    "y": [".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####", "....#", ".###."],
    "z": [".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"],
    " ": ["...", "...", "...", "...", "...", "...", "..."],
}


def pixel_cells(text):
    """[(col, row)] of lit pixels and the total width in columns, or None if a character has no glyph."""
    cells, x = [], 0
    for ch in text.lower():
        glyph = PIXEL_FONT.get(ch)
        if glyph is None:
            return None
        for r, row in enumerate(glyph):
            cells += [(x + c, r) for c, v in enumerate(row) if v == "#"]
        x += len(glyph[0]) + 1
    return cells, x - 1


def wordmark(cfg, cx, baseline):
    """The name as a pixel-art wordmark (or as plain chrome text). Returns (defs, markup)."""
    name = cfg["name"]
    cells = pixel_cells(name) if cfg.get("wordmark", "pixel") == "pixel" else None
    if cells is None:
        t = f'text-anchor="middle" font-family="{SANS}" font-size="96" font-weight="900" letter-spacing="4"'
        n = escape(name)
        return "", (
            '<g filter="url(#glow)">'
            f'<text x="{cx - 3}" y="{baseline + 1}" {t} fill="#7b8cff" opacity="0.8">{n}</text>'
            f'<text x="{cx + 3}" y="{baseline + 4}" {t} fill="{ROSE}" opacity="0.8">{n}</text>'
            f'<text x="{cx}" y="{baseline}" {t} fill="url(#chrome)" stroke="#2a1b55" stroke-width="2.5" '
            f'paint-order="stroke">{n}</text></g>'
        )
    cell, gap = 16, 2
    pts, cols = cells
    x0, top = cx - cols * cell / 2, baseline - 7 * cell
    rects = "".join(f'<rect x="{x0 + c * cell:g}" y="{top + r * cell:g}" width="{cell - gap}" height="{cell - gap}"/>'
                    for c, r in pts)
    defs = (
        f'<g id="wm">{rects}</g>'
        f'<linearGradient id="wmfill" gradientUnits="userSpaceOnUse" x1="0" y1="{top:g}" x2="0" y2="{baseline:g}">'
        '<stop offset="0" stop-color="#ffffff"/><stop offset="0.48" stop-color="#eee6ff"/>'
        f'<stop offset="0.52" stop-color="#d2c2fa"/><stop offset="1" stop-color="{ROSE}"/></linearGradient>'
    )
    markup = (
        '<use href="#wm" transform="translate(6 6)" fill="#160d30" opacity="0.9"/>'  # hard pixel shadow
        '<g filter="url(#glow)">'
        '<use href="#wm" transform="translate(-3 0)" fill="#7b8cff" opacity="0.55"/>'
        f'<use href="#wm" transform="translate(3 0)" fill="{ROSE}" opacity="0.55"/>'
        '<use href="#wm" fill="url(#wmfill)"/></g>'
    )
    return defs, markup


def build_banner(cfg):
    w, h = 1000, 300
    bg_defs, bg = card_bg("grid", w, h)
    wm_defs, wm = wordmark(cfg, 500, 166)
    body = (
        f'<clipPath id="clip"><rect width="{w}" height="{h}" rx="14"/></clipPath>'
        f'<g clip-path="url(#clip)">{bg}'
        f'<rect width="{w}" height="{h}" fill="url(#glowl)"/><rect width="{w}" height="{h}" fill="url(#glowr)"/>'
        f'<rect width="{w}" height="{h}" fill="url(#vig)"/>'
        '<rect x="-200" y="-20" width="90" height="340" fill="#fff" opacity="0.06" transform="skewX(-20)">'
        '<animate attributeName="x" values="-200;1200" dur="7s" repeatCount="indefinite"/></rect>'
        f'{sparkles(w, h, 8, 3, 5, 11, colors=("#ffffff", ACCENT_HI, ROSE), avoid=[(290, 40, 710, 228)])}</g>'
        f'<rect x="2.5" y="2.5" width="{w - 5}" height="{h - 5}" rx="12" fill="none" stroke="url(#edge)" stroke-width="2.5"/>'
        f'{wm}'
        f'<text x="500" y="216" text-anchor="middle" font-family="{SANS}" font-size="22" letter-spacing="3" fill="{TEXT}">'
        f'<tspan fill="{ROSE}">✦</tspan> {escape(cfg["tagline"])} <tspan fill="{ROSE}">✦</tspan></text>'
    )
    defs = CHROME_DEFS + bg_defs + wm_defs + (
        '<radialGradient id="glowl" cx="0.18" cy="0.25" r="0.55">'
        f'<stop offset="0" stop-color="{ACCENT}" stop-opacity="0.38"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="glowr" cx="0.85" cy="0.85" r="0.55">'
        f'<stop offset="0" stop-color="{ROSE}" stop-opacity="0.22"/><stop offset="1" stop-color="{ROSE}" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="vig" cx="0.5" cy="0.5" r="0.75"><stop offset="0.55" stop-color="#000" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{INK}" stop-opacity="0.55"/></radialGradient>'
        '<filter id="glow" x="-10%" y="-30%" width="120%" height="160%">'
        '<feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
    )
    write("banner.svg", svg(w, h, body, defs))


def build_divider():
    """An audio waveform with a sparkle in the middle."""
    w, h = 1000, 44
    rng = random.Random(8)
    n = 96
    bars = ""
    for i in range(n):
        x = 20 + i * (w - 40) / (n - 1)
        if abs(x - 500) < 30:  # leave room for the centre sparkle
            continue
        amp = 2 + 17 * math.sin(math.pi * i / (n - 1)) ** 0.7 * (0.25 + 0.75 * rng.random())
        bars += f'<rect x="{x - 2:.1f}" y="{22 - amp:.1f}" width="4" height="{2 * amp:.1f}" rx="2"/>'
    defs = (
        f'<linearGradient id="wave" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{w}" y2="0">'
        f'<stop offset="0" stop-color="#5b43ad"/><stop offset="0.5" stop-color="{ACCENT}"/>'
        f'<stop offset="1" stop-color="{ROSE}"/></linearGradient>'
    )
    body = (
        f'<g fill="url(#wave)">{bars}</g>'
        + sparkle(500, 22, 14, 0, "#ffffff", 2.6)
        + sparkle(468, 22, 5, 0.5, ACCENT_HI, 2.6)
        + sparkle(532, 22, 5, 1.0, ACCENT_HI, 2.6)
    )
    write("divider.svg", svg(w, h, body, defs))


def fade_track(i, n, f):
    """keyTimes / values for picture i of n in a looping crossfade (f = fade length as a fraction of the loop)."""
    slot = 1.0 / n
    if i == 0:
        pts = [(0, 1), (slot - f, 1), (slot, 0), (1 - f, 0), (1, 1)]
    else:
        pts = [(0, 0), (i * slot - f, 0), (i * slot, 1)]
        pts += [(1 - f, 1), (1, 0)] if i == n - 1 else [((i + 1) * slot - f, 1), ((i + 1) * slot, 0), (1, 0)]
    return ";".join(f"{t:.4g}" for t, _ in pts), ";".join(str(v) for _, v in pts)


def screen(cfg, x, y, size):
    """The art 'screen': soft violet halo, frame, crossfading pictures, CRT scanlines and glare."""
    pad = 6
    ix, iy, inner = x + pad, y + pad, size - 2 * pad
    arts = []
    for a in cfg.get("avatars", []):
        if (ROOT / a).is_file():
            arts.append(a)
        else:
            print("  warning: art file not found, skipped: %s" % a)
    n = len(arts)
    cycle = 4.0 * n  # 4 s per picture
    f = 0.6 / cycle  # 0.6 s fades
    if n:
        art = ""
        for i, a in enumerate(arts):
            anim = ""
            if n > 1:
                kt, vals = fade_track(i, n, f)
                anim = (f'<animate attributeName="opacity" keyTimes="{kt}" values="{vals}" '
                        f'dur="{cycle:g}s" repeatCount="indefinite"/>')
            art += (f'<image x="{ix}" y="{iy}" width="{inner}" height="{inner}" preserveAspectRatio="xMidYMid slice" '
                    f'opacity="{1 if i == 0 else 0}" href="{data_uri(ROOT / a)}">{anim}</image>')
    else:  # placeholder until some art is configured
        art = (f'<svg x="{ix}" y="{iy}" width="{inner}" height="{inner}" viewBox="0 0 {inner} {inner}">'
               f'{mesh(inner, inner, 34, MESH_HERO, seed=21, bias=0.4)}'
               f'<text x="{inner // 2}" y="{inner // 2 + 5}" text-anchor="middle" font-family="{SANS}" '
               f'font-size="16" fill="{TEXT}">your art here</text></svg>')
    return (
        '<g filter="url(#neon)" fill="none" stroke-width="9">'
        f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="12" stroke="{ACCENT}" opacity="0.7"/></g>'
        f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="12" fill="{INK}" stroke="{TEXT}" stroke-width="2.5"/>'
        f'<clipPath id="screenclip"><rect x="{ix}" y="{iy}" width="{inner}" height="{inner}" rx="7"/></clipPath>'
        f'<g clip-path="url(#screenclip)">{art}'
        f'<rect x="{ix}" y="{iy}" width="{inner}" height="{inner}" fill="url(#scan)"/>'
        f'<path d="M{ix} {iy}h{inner * 0.55:g}l-{inner * 0.55:g} {inner * 0.55:g}z" fill="#fff" opacity="0.08"/></g>'
    )


def menu_bar(x, y, w, h):
    """Menu strip (File View Play Tools Help) under the title bar."""
    out = (f'<rect x="{x + 1}" y="{y}" width="{w - 2}" height="{h}" fill="{PANEL_HI}"/>'
           f'<rect x="{x + 1}" y="{y + h - 1}" width="{w - 2}" height="1" fill="{LINE}"/>')
    tx = x + 16
    for item in ("File", "View", "Play", "Tools", "Help"):
        out += (f'<text x="{tx}" y="{y + 17}" font-family="{SANS}" font-size="13" fill="{MUTED}">{item}</text>'
                f'<rect x="{tx}" y="{y + 19}" width="7" height="1" fill="{MUTED}"/>')  # XP-style mnemonic underline
        tx += len(item) * 8 + 22
    return out


def control_bar(x, y, w, h):
    """Media-player strip: transport buttons, seek bar, equalizer and volume."""
    cy = y + h // 2 + 1
    o = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#ctrl)"/>',
        f'<rect x="{x}" y="{y}" width="{w}" height="2" fill="{LINE_HI}" opacity="0.7"/>',
    ]
    # play
    px = x + 46
    o += [
        f'<circle cx="{px}" cy="{cy}" r="19" fill="url(#playbtn)" stroke="{TEXT}" stroke-width="2"/>',
        f'<ellipse cx="{px}" cy="{cy - 8}" rx="13" ry="7" fill="#fff" opacity="0.28"/>',
        f'<path d="M{px - 5} {cy - 8}l13 8l-13 8z" fill="#fff"/>',
    ]
    # stop
    sx = x + 94
    o += [
        f'<circle cx="{sx}" cy="{cy}" r="12" fill="url(#btn)" stroke="{TEXT}" stroke-width="1.4"/>',
        f'<rect x="{sx - 4}" y="{cy - 4}" width="8" height="8" rx="1" fill="#fff"/>',
    ]
    # previous / next
    for bx, s in ((x + 140, -1), (x + 182, 1)):
        o += [
            f'<rect x="{bx - 16}" y="{cy - 11}" width="32" height="22" rx="11" fill="url(#btn)" stroke="{TEXT}" stroke-width="1.4"/>',
            f'<path d="M{bx + s * 6} {cy - 5}V{cy + 5}" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>',
            f'<path d="M{bx - s * 5} {cy - 5}L{bx + s * 3} {cy}L{bx - s * 5} {cy + 5}z" fill="#fff"/>',
        ]
    # seek bar: progress and knob creep along the track (starts ~30% in)
    x0, span = x + 235, 405
    done = round(span * 0.3)
    o += [
        f'<rect x="{x0}" y="{cy - 4}" width="{span}" height="8" rx="4" fill="{INK}" stroke="{LINE}" stroke-width="1.5"/>',
        f'<rect x="{x0}" y="{cy - 4}" width="{done}" height="8" rx="4" fill="url(#seekfill)">'
        f'<animate attributeName="width" values="0;{span}" dur="40s" begin="-12s" repeatCount="indefinite"/></rect>',
        f'<circle cx="{x0 + done}" cy="{cy}" r="8" fill="url(#knob)" stroke="{TEXT}" stroke-width="1.6">'
        f'<animate attributeName="cx" values="{x0};{x0 + span}" dur="40s" begin="-12s" repeatCount="indefinite"/></circle>',
    ]
    # equalizer
    rng = random.Random(5)
    base = cy + 13
    for k in range(10):
        hs = [rng.randint(5, 26) for _ in range(4)]
        hs.append(hs[0])
        dur, begin = round(rng.uniform(0.7, 1.3), 2), -round(rng.uniform(0, 1.0), 2)
        hv = ";".join(str(v) for v in hs)
        yv = ";".join(str(base - v) for v in hs)
        o.append(
            f'<rect x="{x + 676 + 9 * k}" y="{base - hs[0]}" width="6" height="{hs[0]}" rx="2" fill="url(#eq)">'
            f'<animate attributeName="height" values="{hv}" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="{yv}" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/></rect>'
        )
    # volume
    vx = x + 796
    o += [
        f'<path d="M{vx} {cy - 4}h4l6 -5v18l-6 -5h-4z" fill="{TEXT}"/>',
        f'<path d="M{vx + 13} {cy - 5}q5 5 0 10" fill="none" stroke="{TEXT}" stroke-width="2" stroke-linecap="round"/>',
        f'<rect x="{x + 818}" y="{cy - 3}" width="112" height="6" rx="3" fill="{INK}" stroke="{LINE}" stroke-width="1.2"/>',
        f'<rect x="{x + 818}" y="{cy - 3}" width="78" height="6" rx="3" fill="{ACCENT}"/>',
        f'<circle cx="{x + 896}" cy="{cy}" r="6.5" fill="#fff" stroke="{LINE_HI}" stroke-width="1.5"/>',
    ]
    return "".join(o)


def wrap_bullets(lines, width):
    """[(bullet index, text chunk, is first chunk of its bullet)] for every wrapped line."""
    out = []
    for i, line in enumerate(lines):
        for j, chunk in enumerate(textwrap.wrap(line, width) or [""]):
            out.append((i, chunk, j == 0))
    return out


def build_about(cfg):
    """The intro, dressed as a media-player window with the art on its 'screen'."""
    w, h = 1000, 420
    wx, wy, ww, wh = 20, 20, 960, 380  # the window
    bar, menu_h, ctrl_h = 34, 24, 52
    top, bottom = wy + bar + menu_h, wy + wh - ctrl_h
    mid = (top + bottom) / 2  # vertical centre of the content area
    size = 240
    sy = round(mid - size / 2)

    glyphs = (("♡", ACCENT_HI), ("★", "#d8ccfa"), ("✧", ACCENT_HI), ("♪", "#d8ccfa"))
    rows = wrap_bullets(cfg["bio"], 46)
    pitch = 36
    title_y = max(top + 38, round(mid - 18 - 18 * (len(rows) - 1)))
    first_y = title_y + 56
    bio = ""
    for k, (idx, chunk, first) in enumerate(rows):
        y = first_y + pitch * k
        if first:
            glyph, color = glyphs[idx % len(glyphs)]
            bio += f'<text x="48" y="{y}" font-family="{SANS}" font-size="21" fill="{color}">{glyph}</text>'
        bio += f'<text x="80" y="{y}" font-family="{MONO}" font-size="21" fill="{TEXT}">{escape(chunk)}</text>'
    title = (f'<text x="48" y="{title_y}" font-family="{SANS}" font-size="34" font-weight="800" fill="url(#chrome)" '
             f'stroke="#2a1b55" stroke-width="1" paint-order="stroke">hi, i\'m {escape(cfg["name"])} ✧</text>')

    defs = CHROME_DEFS + CONTROL_DEFS + (
        f'<clipPath id="winclip"><rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="10"/></clipPath>'
        '<filter id="neon" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="6"/></filter>'
        '<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
        '<rect width="4" height="1.5" fill="#000" opacity="0.16"/></pattern>'
    )
    body = (
        window_chrome(ww, wh, cfg["window_title"], wx, wy, bar)
        + menu_bar(wx, wy + bar, ww, menu_h)
        + title + bio
        + screen(cfg, 716, sy, size)
        + f'<g clip-path="url(#winclip)">{control_bar(wx, wy + wh - ctrl_h, ww, ctrl_h)}</g>'
        + f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="10" fill="none" stroke="{LINE_HI}" stroke-width="2"/>'
        + sparkle(960, sy - 2, 12, 0.3, "#ffffff", 3.2)
        + line_sparkle(708, sy + size + 4, 15, 1.0, ACCENT_HI)
        + sparkle(694, 150, 5, 1.6, ACCENT_HI, 2.8)
    )
    write("about-window.svg", svg(w, h, body, defs))


def group_box(bx, by, bw, bh, label):
    """XP-style group box: a rounded frame whose top border breaks around its label."""
    r = 8
    lw = len(label) * 8.1 + 30  # label + leading sparkle + padding
    gx0, gx1 = bx + 10, bx + 10 + lw
    frame = (f"M{gx1:g} {by}H{bx + bw - r}Q{bx + bw} {by} {bx + bw} {by + r}V{by + bh - r}"
             f"Q{bx + bw} {by + bh} {bx + bw - r} {by + bh}H{bx + r}Q{bx} {by + bh} {bx} {by + bh - r}"
             f"V{by + r}Q{bx} {by} {bx + r} {by}H{gx0:g}")
    return (
        f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="{r}" fill="{PANEL}" opacity="0.6"/>'
        f'<path d="{frame}" fill="none" stroke="{LINE_HI}" stroke-width="1.5"/>'
        f'<text x="{gx0 + 6:g}" y="{by + 5}" font-family="{SANS}" font-size="15" font-weight="700" fill="{TEXT}">'
        f'<tspan fill="{ROSE}">✦</tspan> {escape(label)}</text>'
    )


def tab(x, y, w, h, label, active):
    r = 6
    d = f"M{x} {y + h}V{y + r}Q{x} {y} {x + r} {y}H{x + w - r}Q{x + w} {y} {x + w} {y + r}V{y + h}"
    if active:
        return (
            f'<path d="{d}Z" fill="{PANEL_HI}"/>'
            f'<path d="{d}" fill="none" stroke="{LINE_HI}" stroke-width="1.5"/>'
            f'<path d="M{x + 1} {y + 4}Q{x + 1} {y + 1} {x + r} {y + 1}H{x + w - r}Q{x + w - 1} {y + 1} {x + w - 1} {y + 4}" '
            'fill="none" stroke="url(#tabhi)" stroke-width="3" stroke-linecap="round"/>'
            f'<text x="{x + w / 2:g}" y="{y + h / 2 + 5:g}" text-anchor="middle" font-family="{SANS}" font-size="14" '
            f'font-weight="700" fill="{TEXT}">{escape(label)}</text>'
        )
    return (
        f'<path d="{d}Z" fill="#1a1131" stroke="{LINE}" stroke-width="1.2"/>'
        f'<text x="{x + w / 2:g}" y="{y + h / 2 + 5:g}" text-anchor="middle" font-family="{SANS}" font-size="13" '
        f'fill="{MUTED}">{escape(label)}</text>'
    )


def build_skills_window(cfg):
    """All skill categories in one XP window: decorative tabs, then a group box per category."""
    style = card_style(cfg)
    w = 1000
    wx, wy, ww, bar = 20, 20, 960, 34
    tab_y, tab_h = wy + bar + 12, 30
    body_x, body_y, body_w = wx + 12, tab_y + tab_h, ww - 24
    pad, col_gap, row_gap = 22, 18, 26
    inner_w = body_w - 2 * pad
    col_w = (inner_w - col_gap) // 2

    def chips(items, bw):
        placed, x, y = [], 18, 24
        for i, item in enumerate(items):
            pw = pill_width(item)
            if x > 18 and x + pw > bw - 18:
                x, y = 18, y + 42
            placed.append((x, y, item, i))
            x += pw + 10
        return placed, y + 30 + 18

    cats = list(cfg["skills"].items())
    boxes = []
    for idx, (cat, items) in enumerate(cats):
        wide = len(cats) % 2 == 1 and idx == len(cats) - 1
        bw = inner_w if wide else col_w
        placed, bh = chips(items, bw)
        boxes.append({"cat": cat, "bw": bw, "bh": bh, "placed": placed, "row": idx // 2, "col": 0 if wide else idx % 2})
    rows = sorted({b["row"] for b in boxes})
    row_h = {r: max(b["bh"] for b in boxes if b["row"] == r) for r in rows}
    y, row_y = body_y + pad + 6, {}
    for r in rows:
        row_y[r] = y
        y += row_h[r] + row_gap
    body_h = y - row_gap + pad - body_y
    status_y = body_y + body_h + 10
    status_h = 24
    wh = status_y + status_h - wy
    h = wy + wh + 20

    fills = ["pill", "pill2", "pill3"]
    content = ""
    for b in boxes:
        bx = body_x + pad + b["col"] * (col_w + col_gap)
        by, bh = row_y[b["row"]], row_h[b["row"]]
        content += group_box(bx, by, b["bw"], bh, b["cat"].lower())
        for x, cy, item, i in b["placed"]:
            content += pill(bx + x, by + cy, item, fills[i % 3])[1]

    bg_defs, bg = card_bg(style, body_w, body_h)
    tabs, tx = "", body_x + 10
    active_tab = ""
    for label, active in (("Skills", True), ("Projects", False), ("About", False)):
        tw = len(label) * 9 + 36
        if active:  # drawn last so it sits over the body's top border
            active_tab = tab(tx, tab_y - 3, tw, tab_h + 4, label, True)
        else:
            tabs += tab(tx, tab_y + 2, tw, tab_h - 2, label, False)
        tx += tw + 4
    n_skills = sum(len(v) for v in cfg["skills"].values())
    status = (
        f'<rect x="{wx + 1}" y="{status_y}" width="{ww - 2}" height="{status_h}" fill="{PANEL_HI}"/>'
        f'<rect x="{wx + 1}" y="{status_y}" width="{ww - 2}" height="1" fill="{LINE}"/>'
        f'<text x="{wx + 16}" y="{status_y + 16}" font-family="{MONO}" font-size="12" fill="{MUTED}">'
        f'{len(cats)} categories</text>'
        f'<rect x="{wx + 150}" y="{status_y + 5}" width="1" height="14" fill="{LINE}"/>'
        f'<text x="{wx + 164}" y="{status_y + 16}" font-family="{MONO}" font-size="12" fill="{MUTED}">'
        f'{n_skills} skills</text>'
        + "".join(f'<rect x="{wx + ww - 10 - 4 * i}" y="{status_y + status_h - 6 - 4 * j}" width="2" height="2" fill="{LINE_HI}"/>'
                  for i in range(3) for j in range(3) if i + j < 3)  # resize grip
    )
    defs = CHROME_DEFS + bg_defs + (
        f'<clipPath id="winclip"><rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="10"/></clipPath>'
        f'<clipPath id="bodyclip"><rect width="{body_w}" height="{body_h}" rx="6"/></clipPath>'
        '<linearGradient id="tabhi" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{ROSE}"/><stop offset="1" stop-color="{ROSE_DEEP}"/></linearGradient>'
    )
    body = (
        window_chrome(ww, wh, "skills.exe", wx, wy, bar)
        + tabs
        + f'<g transform="translate({body_x} {body_y})"><g clip-path="url(#bodyclip)">{bg}</g>'
        + f'<rect width="{body_w}" height="{body_h}" rx="6" fill="none" stroke="{LINE_HI}" stroke-width="1.5"/></g>'
        + active_tab
        + content
        + f'<g clip-path="url(#winclip)">{status}</g>'
        + f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="10" fill="none" stroke="{LINE_HI}" stroke-width="2"/>'
    )
    write("skills.svg", svg(w, h, body, defs))
    return "skills.svg"


def build_projects(cfg):
    style = card_style(cfg)
    w, h = 480, 200
    out = []
    for i, p in enumerate(cfg["projects"]):
        desc = textwrap.wrap(p["description"], 40)[:3]
        dt = "".join('<tspan x="22" y="%d">%s</tspan>' % (88 + 22 * j, escape(l)) for j, l in enumerate(desc))
        tags, x = "", 22
        for t in p["tags"]:
            pw = pill_width(t, 12)
            if x + pw > w - 22:
                break
            tags += pill(x, 154, t, "pill", 12)[1]
            x += pw + 8
        bg_defs, bg = card_bg(style, w, h, seed=40 + i)
        title = p["name"] + ".exe"
        body = (
            f'<clipPath id="clip"><rect x="3" y="3" width="{w - 6}" height="{h - 6}" rx="9"/></clipPath>'
            f'<g clip-path="url(#clip)">{bg}</g>'
            f'{window_chrome(w, h, title, 0, 0, 34, body_fill="none")}'
            f'<text font-family="{MONO}" font-size="14" fill="{TEXT}">{dt}</text>{tags}'
        )
        name = "project-%d.svg" % (i + 1)
        write(name, svg(w, h, body, CHROME_DEFS + bg_defs))
        out.append((p, name))
    return out


def build_links(cfg):
    out = []
    for ln in cfg["links"]:
        label = ln["label"]
        w = int(len(label) * 15 * MONO_W + 70)
        body = (
            f'<rect x="2" y="2" width="{w - 4}" height="40" rx="20" fill="url(#pill)" stroke="{LINE_HI}" stroke-width="1.5"/>'
            f'<text x="{w // 2}" y="28" text-anchor="middle" font-family="{MONO}" font-size="16" font-weight="800" '
            f'fill="{TEXT}">{escape(label)}</text>'
        )
        name = "link-%s.svg" % slug(label)
        write(name, svg(w, 44, body, CHROME_DEFS))
        out.append((ln, name))
    return out


def build_footer(cfg):
    """A violet 'blue screen' sitting on an XP taskbar."""
    w, scr_h, tb_h = 1000, 160, 44
    h = scr_h + tb_h
    bsod = "#2a1f7a"
    fs = 17
    cw = fs * MONO_W
    name = cfg["name"]
    lw = (len(name) + 2) * cw + 4
    stop = "*** STOP: 0x00000042 (THANKS_FOR_STOPPING_BY)"
    press = "Press any key to continue "
    px0 = 500 - (len(press) + 1) * cw / 2
    screen = (
        f'<rect width="{w}" height="{scr_h}" fill="{bsod}"/>'
        f'<rect width="{w}" height="{scr_h}" fill="url(#bsglow)"/>'
        f'<rect x="{500 - lw / 2:g}" y="30" width="{lw:g}" height="26" fill="#d9d0f5"/>'
        f'<text x="500" y="49" text-anchor="middle" font-family="{MONO}" font-size="{fs}" font-weight="700" '
        f'fill="{bsod}">{escape(name)}</text>'
        f'<text x="500" y="92" text-anchor="middle" font-family="{MONO}" font-size="{fs}" fill="{TEXT}">{escape(stop)}</text>'
        f'<text x="{px0:g}" y="128" font-family="{MONO}" font-size="{fs}" fill="{TEXT}" xml:space="preserve">{escape(press)}</text>'
        f'<rect x="{px0 + len(press) * cw:g}" y="130" width="{cw:g}" height="3" fill="{TEXT}">'
        '<animate attributeName="opacity" values="1;0" calcMode="discrete" dur="1.1s" repeatCount="indefinite"/></rect>'
        f'<rect width="{w}" height="{scr_h}" fill="url(#scan)"/>'
    )

    ty = scr_h
    cy = ty + tb_h / 2
    # start button: rounded on the right, flush left (the outer clip rounds the corner)
    start = (
        f'<rect x="-24" y="{ty}" width="146" height="{tb_h}" rx="{tb_h / 2:g}" fill="url(#startbtn)"/>'
        f'<rect x="-24" y="{ty + 2}" width="140" height="{tb_h / 2 - 4:g}" rx="10" fill="#fff" opacity="0.18"/>'
        f'<rect x="-24" y="{ty}" width="146" height="{tb_h}" rx="{tb_h / 2:g}" fill="none" stroke="#7a3f6e" stroke-width="1"/>'
    )
    for (dx, dy), col in zip(((0, 0), (9, 0), (0, 9), (9, 9)), ("#ffffff", "#f6d3ea", "#d9ccfa", "#b7a3f5")):
        start += f'<rect x="{17 + dx}" y="{cy - 9 + dy:g}" width="8" height="8" rx="1.5" fill="{col}"/>'
    start += (
        f'<text x="45" y="{cy + 7:g}" font-family="{SANS}" font-size="20" font-weight="700" font-style="italic" '
        'fill="#000" opacity="0.3">start</text>'
        f'<text x="44" y="{cy + 6:g}" font-family="{SANS}" font-size="20" font-weight="700" font-style="italic" '
        'fill="#fff">start</text>'
    )
    tasks, tx = "", 138
    for label, pressed, icon in (("about_me.exe", False, ROSE), ("skills.exe", True, ACCENT_HI), ("projects", False, "#d9ccfa")):
        tw = 168
        tasks += (
            f'<rect x="{tx}" y="{ty + 7}" width="{tw}" height="{tb_h - 14}" rx="4" '
            f'fill="url(#{"taskdown" if pressed else "task"})" stroke="{"#1f1550" if pressed else "#8a75e0"}" stroke-width="1"/>'
            f'<rect x="{tx + 10}" y="{cy - 6:g}" width="12" height="12" rx="2.5" fill="{icon}"/>'
            f'<text x="{tx + 30}" y="{cy + 5:g}" font-family="{SANS}" font-size="13" '
            f'font-weight="{700 if pressed else 400}" fill="#fff">{escape(label)}</text>'
        )
        tx += tw + 6
    trx = 838
    tray = (
        f'<rect x="{trx}" y="{ty}" width="{w - trx}" height="{tb_h}" fill="url(#tray)"/>'
        f'<rect x="{trx}" y="{ty}" width="1" height="{tb_h}" fill="#7d68d8"/>'
        # volume
        f'<path d="M{trx + 18} {cy - 3:g}h3l5 -4v14l-5 -4h-3z" fill="{TEXT}"/>'
        f'<path d="M{trx + 29} {cy - 4:g}q4 4 0 8" fill="none" stroke="{TEXT}" stroke-width="1.6" stroke-linecap="round"/>'
        # signal bars
        + "".join(f'<rect x="{trx + 46 + 5 * i}" y="{cy + 6 - 4 * (i + 1):g}" width="3" height="{4 * (i + 1)}" fill="{TEXT}" '
                  f'opacity="{0.55 + 0.15 * i:g}"/>' for i in range(3))
        + f'<text x="{w - 46}" y="{cy + 5:g}" text-anchor="middle" font-family="{SANS}" font-size="14" fill="#fff">00:42</text>'
    )
    taskbar = (
        f'<rect y="{ty}" width="{w}" height="{tb_h}" fill="url(#taskbar)"/>'
        f'<rect y="{ty}" width="{w}" height="1.5" fill="#a08cf0"/>'
        + tasks + tray + start
    )
    defs = CHROME_DEFS + (
        f'<clipPath id="clip"><rect width="{w}" height="{h}" rx="14"/></clipPath>'
        '<radialGradient id="bsglow" cx="0.92" cy="1" r="0.6">'
        f'<stop offset="0" stop-color="{ROSE}" stop-opacity="0.22"/><stop offset="1" stop-color="{ROSE}" stop-opacity="0"/></radialGradient>'
        '<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
        '<rect width="4" height="1.5" fill="#000" opacity="0.14"/></pattern>'
        '<linearGradient id="taskbar" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#6650c2"/><stop offset="0.15" stop-color="#4b379f"/>'
        '<stop offset="0.6" stop-color="#3b2b88"/><stop offset="1" stop-color="#2d2070"/></linearGradient>'
        '<linearGradient id="startbtn" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#f2c3df"/><stop offset="0.45" stop-color="#d48dbb"/>'
        f'<stop offset="0.55" stop-color="{ROSE_DEEP}"/><stop offset="1" stop-color="#8c4a80"/></linearGradient>'
        '<linearGradient id="task" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#6b57c8"/><stop offset="1" stop-color="#4a379c"/></linearGradient>'
        '<linearGradient id="taskdown" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#241a5c"/><stop offset="1" stop-color="#34267c"/></linearGradient>'
        '<linearGradient id="tray" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#4a38a4"/><stop offset="1" stop-color="#2a1e68"/></linearGradient>'
    )
    body = (
        f'<g clip-path="url(#clip)">{screen}{taskbar}</g>'
        f'<rect x="1.5" y="1.5" width="{w - 3}" height="{h - 3}" rx="13" fill="none" stroke="url(#edge)" stroke-width="2.5"/>'
    )
    write("footer.svg", svg(w, h, body, defs))


# ---- README ----------------------------------------------------------------
def table(cells):
    """cells: [(html, span)], span 1 or 2, laid out in a two-column full-width grid."""
    rows, cur, used = [], [], 0
    for html, span in cells:
        cur.append('<td align="center" valign="top"%s>%s</td>' % (' colspan="2"' if span == 2 else "", html))
        used += span
        if used >= 2:
            rows.append(cur)
            cur, used = [], 0
    if cur:
        rows.append(cur)
    return ['<table width="100%">'] + ["<tr>%s</tr>" % "".join(r) for r in rows] + ["</table>", ""]


def build_readme(cfg, skills, projects, links):
    divider = '<img src="assets/divider.svg" alt="" width="100%"/>'
    skills_alt = "; ".join("%s: %s" % (cat, ", ".join(items)) for cat, items in cfg["skills"].items())
    r = ['<div align="center">', "",
         '<img src="assets/banner.svg" alt="%s - %s" width="100%%"/>' % (attr(cfg["name"]), attr(cfg["tagline"])), "",
         '<img src="assets/about-window.svg" alt="About me: %s" width="100%%"/>' % attr(" ".join(cfg["bio"])), "",
         divider, "",
         '<img src="assets/%s" alt="Skills. %s" width="100%%"/>' % (skills, attr(skills_alt)), "",
         divider, ""]
    r += table([('<a href="%s"><img src="assets/%s" alt="%s: %s" width="100%%"/></a>'
                 % (attr(p["url"]), name, attr(p["name"]), attr(p["description"])), 1)
                for p, name in projects])
    r += [divider, ""]
    if links:
        r += ["<p>" + " ".join('<a href="%s"><img src="assets/%s" alt="%s" height="44"/></a>'
                               % (attr(ln["url"]), name, attr(ln["label"])) for ln, name in links) + "</p>", ""]
    r += ['<img src="assets/footer.svg" alt="*** STOP: 0x00000042 (THANKS_FOR_STOPPING_BY)" width="100%"/>', "",
          "</div>", ""]
    (ROOT / "README.md").write_text("\n".join(r), encoding="utf-8")
    print("  wrote README.md")


def main():
    cfg = json.loads((ROOT / "profile.config.json").read_text(encoding="utf-8"))
    print("building assets...")
    card_style(cfg)  # fail early on a typo
    # drop generated files from a previous run so removed skills/projects don't linger
    for pattern in ("skills-*.svg", "project-*.svg", "link-*.svg"):
        for stale in ASSETS.glob(pattern):
            stale.unlink()
    build_banner(cfg)
    build_divider()
    build_about(cfg)
    skills = build_skills_window(cfg)
    projects = build_projects(cfg)
    links = build_links(cfg)
    build_footer(cfg)
    build_readme(cfg, skills, projects, links)
    print("done.")


if __name__ == "__main__":
    main()
