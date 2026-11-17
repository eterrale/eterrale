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

# ---- palette ---------------------------------------------------------------
VIOLET_DARK = "#1a0b2e"
VIOLET = "#2d1458"
PURPLE = "#5b2a9e"
ORCHID = "#c77dff"
LAVENDER = "#e0b8ff"
PINK = "#ff4fa3"
PINK_SOFT = "#ff9ad0"
ICE = "#e8f4ff"
ICE_BLUE = "#9fd8ff"
LIME = "#b6ff3b"  # acid accent (jet-set-radio green), used sparingly
CYAN = "#3be8ff"  # chromatic-aberration accent
SCREEN = "#2b1166"  # CRT "screen" colour shared by the banner and the footer
PANEL = VIOLET_DARK
PANEL_HI = "#241046"

SANS = "'Trebuchet MS', 'Segoe UI', Verdana, sans-serif"
MONO = "'Courier New', ui-monospace, Menlo, Consolas, monospace"
MONO_W = 0.6  # approx glyph width / font-size for the mono stack

MESH_BRIGHT = [VIOLET_DARK, PURPLE, "#a23fc4", PINK]
MESH_DARK = ["#150829", "#241046", "#3a1670", "#5a1f8a"]  # only used by card_style "lowpoly"

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


# Vertical nudge (as a fraction of the font size) that puts each glyph's ink on the centre line.
ASCII_DY = {".": -0.28, "'": 0.3, "*": 0.22, "+": 0.0, "x": 0.05, "o": 0.05, "O": 0.0}


def ascii_twinkle(x, y, size, frames, delay, color, dur):
    """An ASCII character that twinkles by flipping through `frames` (one <text> per frame, shown in turn)."""
    n = len(frames)
    key_times = ";".join("%.4g" % (k / n) for k in range(n))
    out = f'<g font-family="{MONO}" font-size="{size:.1f}" font-weight="700" fill="{color}" text-anchor="middle" dominant-baseline="central">'
    for k, ch in enumerate(frames):
        vals = ";".join("1" if j == k else "0" for j in range(n))
        out += (
            f'<text x="{x:.1f}" y="{y + ASCII_DY.get(ch, 0) * size:.1f}" opacity="{1 if k == 0 else 0}">{escape(ch)}'
            f'<animate attributeName="opacity" values="{vals}" keyTimes="{key_times}" calcMode="discrete" '
            f'dur="{dur:g}s" begin="{-delay:g}s" repeatCount="indefinite"/></text>'
        )
    return out + "</g>"


def sparkle(x, y, r, delay=0.0, color="#ffffff", dur=3.0):
    """ASCII star: . + * + (r is roughly the old star radius)."""
    return ascii_twinkle(x, y, r * 2.4, (".", "+", "*", "+"), delay, color, dur)


def line_sparkle(x, y, r, delay=0.0, color="#ffffff", dur=3.6):
    """Lighter ASCII sparkle: ' + x + ."""
    return ascii_twinkle(x, y, r * 1.7, ("'", "+", "x", "+", "."), delay, color, dur)


def sparkles(w, h, n, seed, rmin=5, rmax=13, colors=("#ffffff", ICE_BLUE, PINK_SOFT), box=None, line_ratio=0.3,
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
    '<linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="#ffffff"/><stop offset="0.45" stop-color="{ICE}"/>'
    f'<stop offset="0.5" stop-color="{ICE_BLUE}"/><stop offset="1" stop-color="{ORCHID}"/></linearGradient>'
    '<linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">'
    f'<stop offset="0" stop-color="{PINK}"/><stop offset="1" stop-color="{PURPLE}"/></linearGradient>'
    '<linearGradient id="pill" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="#ffffff"/><stop offset="0.5" stop-color="{ICE}"/>'
    f'<stop offset="1" stop-color="{LAVENDER}"/></linearGradient>'
    # glossy XP-style window buttons: lilac (min/max) and hot pink (close)
    '<linearGradient id="btn" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#e9d9ff"/><stop offset="0.5" stop-color="#b98cff"/>'
    '<stop offset="0.52" stop-color="#9a62f0"/><stop offset="1" stop-color="#7a3fd8"/></linearGradient>'
    '<linearGradient id="btnx" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#ffd6ea"/><stop offset="0.5" stop-color="#ff86bd"/>'
    '<stop offset="0.52" stop-color="#ff4fa3"/><stop offset="1" stop-color="#e0246f"/></linearGradient>'
)

# extra gradients for the media-player strip in the about window
CONTROL_DEFS = (
    '<linearGradient id="ctrl" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#3a1b72"/><stop offset="1" stop-color="#1c0a3a"/></linearGradient>'
    '<radialGradient id="playbtn" cx="0.4" cy="0.3" r="0.8">'
    '<stop offset="0" stop-color="#ffd6ec"/><stop offset="0.55" stop-color="#ff4fa3"/>'
    '<stop offset="1" stop-color="#b8186a"/></radialGradient>'
    '<radialGradient id="knob" cx="0.4" cy="0.35" r="0.7">'
    f'<stop offset="0" stop-color="#f6ffd6"/><stop offset="0.6" stop-color="{LIME}"/>'
    '<stop offset="1" stop-color="#63b800"/></radialGradient>'
    '<linearGradient id="seekfill" x1="0" y1="0" x2="1" y2="0">'
    f'<stop offset="0" stop-color="{PINK}"/><stop offset="1" stop-color="{ORCHID}"/></linearGradient>'
)


def window_chrome(w, h, title, x=0, y=0, bar=34, body_fill=VIOLET_DARK):
    """A Y2K / XP-style window: glossy gradient title bar with min, max and close buttons."""
    cy = y + bar / 2
    btns = ""
    for i, (gid, kind) in enumerate((("btnx", "close"), ("btn", "max"), ("btn", "min"))):
        cx = x + w - 24 - i * 28
        btns += (f'<rect x="{cx - 11:g}" y="{cy - 11:g}" width="22" height="22" rx="5" '
                 f'fill="url(#{gid})" stroke="#fff" stroke-width="1.6"/>')
        if kind == "close":
            btns += (f'<path d="M{cx - 4:g} {cy - 4:g}l8 8m0 -8l-8 8" stroke="#fff" '
                     'stroke-width="2.4" stroke-linecap="round"/>')
        elif kind == "max":
            btns += (f'<rect x="{cx - 4.5:g}" y="{cy - 4.5:g}" width="9" height="9" fill="none" '
                     'stroke="#fff" stroke-width="2"/>')
        else:
            btns += f'<rect x="{cx - 4.5:g}" y="{cy + 1.5:g}" width="9" height="3" fill="#fff"/>'
    gloss = (f'<path d="M{x} {y + bar / 2:g}V{y + 10}Q{x} {y} {x + 10} {y}H{x + w - 10}'
             f'Q{x + w} {y} {x + w} {y + 10}V{y + bar / 2:g}Z" fill="#fff" opacity="0.16"/>')
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{body_fill}" stroke="#fff" stroke-width="2"/>'
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
    w = pill_width(text, font)
    return w, (
        '<rect x="%d" y="%d" width="%d" height="30" rx="15" fill="url(#%s)" stroke="%s" stroke-width="1.5"/>'
        '<text x="%d" y="%d" text-anchor="middle" font-family="%s" font-size="%d" font-weight="700" fill="%s">%s</text>'
        % (x, y, w, fill_id, PINK, x + w / 2, y + 20, MONO, font, VIOLET_DARK, escape(text))
    )


def card_style(cfg):
    style = cfg.get("card_style", "grid")
    if style not in CARD_STYLES:
        sys.exit('card_style must be one of: %s (got "%s")' % (", ".join(CARD_STYLES), style))
    return style


def card_bg(style, w, h, seed=1):
    """Background for a card body: returns (defs, markup). The caller clips the markup."""
    defs = (
        '<linearGradient id="panelbg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{PANEL_HI}"/><stop offset="1" stop-color="{PANEL}"/></linearGradient>'
    )
    base = f'<rect width="{w}" height="{h}" fill="url(#panelbg)"/>'
    if style == "glow":  # soft orchid light from the top-right corner
        defs += (
            f'<radialGradient id="cardglow" gradientUnits="userSpaceOnUse" cx="{w * 0.9:g}" cy="0" r="{w * 0.7:g}">'
            f'<stop offset="0" stop-color="{ORCHID}" stop-opacity="0.4"/>'
            f'<stop offset="1" stop-color="{ORCHID}" stop-opacity="0"/></radialGradient>'
        )
        return defs, base + f'<rect width="{w}" height="{h}" fill="url(#cardglow)"/>'
    if style == "grid":  # hairline grid that fades out towards the bottom-right
        step = 22
        defs += (
            f'<pattern id="cardgrid" width="{step}" height="{step}" patternUnits="userSpaceOnUse">'
            f'<path d="M{step} 0H0V{step}" fill="none" stroke="{LAVENDER}" stroke-width="1" opacity="0.14"/></pattern>'
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
            lv = levels - k
            rects = "".join(f'<rect x="{c * cell}" y="{r * cell}" width="{cell}" height="{cell}"/>'
                            for r in range(4) for c in range(4) if bayer[r][c] < lv)
            defs += (f'<pattern id="dth{lv}" width="{4 * cell}" height="{4 * cell}" patternUnits="userSpaceOnUse" '
                     f'fill="{ORCHID}" fill-opacity="0.2">{rects}</pattern>')
            bands += f'<rect y="{k * band_h}" width="{w}" height="{band_h}" fill="url(#dth{lv})"/>'
        return defs, base + bands
    if style == "lowpoly":
        return defs, (mesh(w, h, 40, MESH_DARK, seed=seed, bias=0.5)
                      + f'<rect width="{w}" height="{h}" fill="{PANEL}" opacity="0.55"/>')
    return defs, base  # "flat"


def crt(w, h):
    """A glowing CRT screen filling (0,0)-(w,h): returns (defs, markup). The caller clips it."""
    defs = (
        '<radialGradient id="crtpink" cx="0.88" cy="0.95" r="0.6">'
        f'<stop offset="0" stop-color="{PINK}" stop-opacity="0.38"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="crtorchid" cx="0.12" cy="0.1" r="0.6">'
        f'<stop offset="0" stop-color="{ORCHID}" stop-opacity="0.4"/><stop offset="1" stop-color="{ORCHID}" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="crtvig" cx="0.5" cy="0.5" r="0.72"><stop offset="0.6" stop-color="#000" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{VIOLET_DARK}" stop-opacity="0.75"/></radialGradient>'
        '<linearGradient id="crtglare" x1="0" y1="0" x2="0.6" y2="1">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0.12"/><stop offset="0.45" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<linearGradient id="crtroll" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.5" stop-color="#fff" stop-opacity="0.07"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<pattern id="crtscan" width="4" height="4" patternUnits="userSpaceOnUse">'
        '<rect width="4" height="1.5" fill="#000" opacity="0.18"/></pattern>'
    )
    markup = (
        f'<rect width="{w}" height="{h}" fill="{SCREEN}"/>'
        f'<rect width="{w}" height="{h}" fill="url(#crtorchid)"/>'
        f'<rect width="{w}" height="{h}" fill="url(#crtpink)"/>'
        # slow roll bar drifting down the screen
        f'<rect y="-60" width="{w}" height="60" fill="url(#crtroll)">'
        f'<animate attributeName="y" values="-60;{h}" dur="6s" repeatCount="indefinite"/></rect>'
        f'<rect width="{w}" height="{h}" fill="url(#crtscan)"/>'
        f'<rect width="{w}" height="{h}" fill="url(#crtvig)"/>'
        f'<rect width="{w}" height="{h}" fill="url(#crtglare)"/>'
    )
    return defs, markup


# ---- assets ----------------------------------------------------------------
def build_banner(cfg):
    w, h = 1000, 300
    crt_defs, screen_bg = crt(w, h)
    # the name as an inverted BSOD-style label, same as the footer's, scaled up
    fs = 80
    lw = (len(cfg["name"]) + 2) * fs * MONO_W + 4
    lh = 112
    ly = (h - lh) // 2  # vertically centred
    body = (
        f'<clipPath id="clip"><rect width="{w}" height="{h}" rx="14"/></clipPath>'
        f'<g clip-path="url(#clip)">{screen_bg}'
        f'{sparkles(w, h, 14, 3, avoid=[(300, ly - 25, 700, ly + lh + 25)])}</g>'
        f'<rect x="3" y="3" width="{w - 6}" height="{h - 6}" rx="12" fill="none" stroke="#fff" stroke-width="3" opacity="0.9"/>'
        f'<rect x="{500 - lw / 2:g}" y="{ly}" width="{lw:g}" height="{lh}" fill="{ICE}"/>'
        f'<text x="500" y="{ly + lh / 2 + fs * 0.35:g}" text-anchor="middle" font-family="{MONO}" font-size="{fs}" '
        f'font-weight="700" fill="{SCREEN}">{escape(cfg["name"])}</text>'
    )
    write("banner.svg", svg(w, h, body, CHROME_DEFS + crt_defs))


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
        f'<stop offset="0" stop-color="{PINK}"/><stop offset="0.5" stop-color="{ORCHID}"/>'
        f'<stop offset="1" stop-color="{ICE_BLUE}"/></linearGradient>'
    )
    body = (
        f'<g fill="url(#wave)">{bars}</g>'
        + sparkle(500, 22, 15, 0, "#ffffff", 2.6)
        + sparkle(466, 22, 6, 0.5, PINK, 2.6)
        + sparkle(534, 22, 6, 1.0, ICE_BLUE, 2.6)
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
    """The art 'screen': neon glow, white frame, crossfading pictures, CRT scanlines and glare."""
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
               f'{mesh(inner, inner, 34, MESH_BRIGHT, seed=21, bias=0.4)}'
               f'<text x="{inner // 2}" y="{inner // 2 + 5}" text-anchor="middle" font-family="{SANS}" '
               'font-size="16" fill="#fff">your art here</text></svg>')
    return (
        # two-tone neon halo: cyan up-left, pink down-right
        '<g filter="url(#neon)" fill="none" stroke-width="9">'
        f'<rect x="{x - 3}" y="{y - 3}" width="{size}" height="{size}" rx="12" stroke="{CYAN}" opacity="0.55"/>'
        f'<rect x="{x + 3}" y="{y + 3}" width="{size}" height="{size}" rx="12" stroke="{PINK}" opacity="0.8"/></g>'
        f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="12" fill="#0b0418" stroke="#fff" stroke-width="3"/>'
        f'<clipPath id="screenclip"><rect x="{ix}" y="{iy}" width="{inner}" height="{inner}" rx="7"/></clipPath>'
        f'<g clip-path="url(#screenclip)">{art}'
        f'<rect x="{ix}" y="{iy}" width="{inner}" height="{inner}" fill="url(#scan)"/>'
        f'<path d="M{ix} {iy}h{inner * 0.55:g}l-{inner * 0.55:g} {inner * 0.55:g}z" fill="#fff" opacity="0.08"/></g>'
    )


def menu_bar(x, y, w, h):
    """Dark-lilac menu strip (File View Play Tools Help) under the title bar."""
    out = (f'<rect x="{x + 1}" y="{y}" width="{w - 2}" height="{h}" fill="#34196a"/>'
           f'<rect x="{x + 1}" y="{y + h - 1}" width="{w - 2}" height="1" fill="{PURPLE}"/>')
    tx = x + 16
    for item in ("File", "View", "Play", "Tools", "Help"):
        out += (f'<text x="{tx}" y="{y + 17}" font-family="{SANS}" font-size="13" fill="{LAVENDER}">{item}</text>'
                f'<rect x="{tx}" y="{y + 19}" width="7" height="1" fill="{LAVENDER}"/>')  # XP-style mnemonic underline
        tx += len(item) * 8 + 22
    return out


def control_bar(x, y, w, h):
    """Media-player strip: transport buttons, seek bar, equalizer and volume."""
    cy = y + h // 2 + 1
    o = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#ctrl)"/>',
        f'<rect x="{x}" y="{y}" width="{w}" height="2" fill="{ORCHID}" opacity="0.55"/>',
    ]
    # play
    px = x + 46
    o += [
        f'<circle cx="{px}" cy="{cy}" r="19" fill="url(#playbtn)" stroke="#fff" stroke-width="2"/>',
        f'<ellipse cx="{px}" cy="{cy - 8}" rx="13" ry="7" fill="#fff" opacity="0.35"/>',
        f'<path d="M{px - 5} {cy - 8}l13 8l-13 8z" fill="#fff"/>',
    ]
    # stop
    sx = x + 94
    o += [
        f'<circle cx="{sx}" cy="{cy}" r="12" fill="url(#btn)" stroke="#fff" stroke-width="1.6"/>',
        f'<rect x="{sx - 4}" y="{cy - 4}" width="8" height="8" rx="1" fill="#fff"/>',
    ]
    # previous / next
    for bx, s in ((x + 140, -1), (x + 182, 1)):
        o += [
            f'<rect x="{bx - 16}" y="{cy - 11}" width="32" height="22" rx="11" fill="url(#btn)" stroke="#fff" stroke-width="1.6"/>',
            f'<path d="M{bx + s * 6} {cy - 5}V{cy + 5}" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>',
            f'<path d="M{bx - s * 5} {cy - 5}L{bx + s * 3} {cy}L{bx - s * 5} {cy + 5}z" fill="#fff"/>',
        ]
    # seek bar: progress and knob creep along the track (starts ~30% in)
    x0, span = x + 235, 405
    done = round(span * 0.3)
    o += [
        f'<rect x="{x0}" y="{cy - 4}" width="{span}" height="8" rx="4" fill="#10052a" stroke="{PURPLE}" stroke-width="1.5"/>',
        f'<rect x="{x0}" y="{cy - 4}" width="{done}" height="8" rx="4" fill="url(#seekfill)">'
        f'<animate attributeName="width" values="0;{span}" dur="40s" begin="-12s" repeatCount="indefinite"/></rect>',
        f'<circle cx="{x0 + done}" cy="{cy}" r="8" fill="url(#knob)" stroke="#fff" stroke-width="2">'
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
            f'<rect x="{x + 676 + 9 * k}" y="{base - hs[0]}" width="6" height="{hs[0]}" rx="2" fill="{LIME}">'
            f'<animate attributeName="height" values="{hv}" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="{yv}" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/></rect>'
        )
    # volume
    vx = x + 796
    o += [
        f'<path d="M{vx} {cy - 4}h4l6 -5v18l-6 -5h-4z" fill="{ICE}"/>',
        f'<path d="M{vx + 13} {cy - 5}q5 5 0 10" fill="none" stroke="{ICE}" stroke-width="2" stroke-linecap="round"/>',
        f'<rect x="{x + 818}" y="{cy - 3}" width="112" height="6" rx="3" fill="#10052a" stroke="{PURPLE}" stroke-width="1.2"/>',
        f'<rect x="{x + 818}" y="{cy - 3}" width="78" height="6" rx="3" fill="{LIME}"/>',
        f'<circle cx="{x + 896}" cy="{cy}" r="6.5" fill="#fff" stroke="{ORCHID}" stroke-width="1.5"/>',
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

    glyphs = (("♡", PINK_SOFT), ("★", ICE_BLUE), ("✧", LAVENDER), ("♪", PINK_SOFT))
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
        bio += f'<text x="80" y="{y}" font-family="{MONO}" font-size="21" fill="{ICE}">{escape(chunk)}</text>'
    title = (f'<text x="48" y="{title_y}" font-family="{SANS}" font-size="34" font-weight="800" fill="url(#chrome)" '
             f'stroke="{PURPLE}" stroke-width="1" paint-order="stroke">hi, i\'m {escape(cfg["name"])} ✧</text>')

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
        + f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="10" fill="none" stroke="#fff" stroke-width="2"/>'
        + sparkle(960, sy - 2, 13, 0.3, "#ffffff", 3.2)
        + line_sparkle(708, sy + size + 4, 16, 1.0, ICE_BLUE)
        + sparkle(694, 150, 6, 1.6, PINK_SOFT, 2.8)
        + line_sparkle(962, sy + size - 8, 11, 2.0)
    )
    write("about-window.svg", svg(w, h, body, defs))


def build_skills(cfg):
    """One card per skill category, two per row; an odd last card spans the full width.

    Cards that share a row share a height. Returns [(category, filename, is_wide)].
    """
    style = card_style(cfg)
    cats = list(cfg["skills"].items())
    fills = ["pill", "pillp", "pilli"]
    cards = []
    for idx, (cat, items) in enumerate(cats):
        wide = len(cats) % 2 == 1 and idx == len(cats) - 1
        w = 990 if wide else 490
        body, x, y = "", 28, 56
        for i, item in enumerate(items):
            if x > 28 and x + pill_width(item) > w - 28:
                x, y = 28, y + 42
            pw, el = pill(x, y, item, fills[i % 3])
            body += el
            x += pw + 10
        cards.append({"cat": cat, "body": body, "w": w, "h": y + 52, "row": idx // 2, "wide": wide})
    row_h = {}
    for c in cards:
        row_h[c["row"]] = max(row_h.get(c["row"], 0), c["h"])
    defs = CHROME_DEFS + (
        '<linearGradient id="pillp" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/>'
        '<stop offset="0.5" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
        '<linearGradient id="pilli" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/>'
        '<stop offset="0.5" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
        % (PINK_SOFT, PINK, ICE, ICE_BLUE)
    )
    out = []
    for c in cards:
        cat, w, h = c["cat"], c["w"], row_h[c["row"]]
        bg_defs, bg = card_bg(style, w, h, seed=hash_seed(cat))
        full = (
            '<clipPath id="clip"><rect x="2" y="2" width="%d" height="%d" rx="12"/></clipPath>'
            '<g clip-path="url(#clip)">%s</g>'
            '<rect x="2" y="2" width="%d" height="%d" rx="12" fill="none" stroke="%s" stroke-width="2"/>'
            '<text x="28" y="36" font-family="%s" font-size="21" font-weight="800" fill="url(#chrome)" '
            'stroke="%s" stroke-width="0.8" paint-order="stroke">✦ %s</text>%s%s'
            % (w - 4, h - 4, bg,
               w - 4, h - 4, ORCHID, SANS, PURPLE, escape(cat.lower()), c["body"],
               sparkles(w, h, 2, hash_seed(cat) + 1, 4, 8, box=(w * 0.6, 10, w - 20, 40)))
        )
        name = "skills-%s.svg" % slug(cat)
        write(name, svg(w, h, full, defs + bg_defs))
        out.append((cat, name, c["wide"]))
    return out


def hash_seed(s):
    return sum(ord(c) * (i + 1) for i, c in enumerate(s))


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
        body = (
            '<clipPath id="clip"><rect x="3" y="3" width="%d" height="%d" rx="9"/></clipPath>'
            '<g clip-path="url(#clip)">%s</g>'
            "%s"
            '<text font-family="%s" font-size="14" fill="%s">%s</text>%s%s'
            % (w - 6, h - 6, bg,
               window_chrome(w, h, "%s.exe" % p["name"], 0, 0, 34, body_fill="none"),
               MONO, ICE, dt, tags, sparkles(w, h, 2, 90 + i, 4, 8, box=(400, 50, 465, 135)))
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
            '<rect x="2" y="2" width="%d" height="40" rx="20" fill="url(#pill)" stroke="%s" stroke-width="2.5"/>'
            '<text x="%d" y="28" text-anchor="middle" font-family="%s" font-size="16" font-weight="800" fill="%s">♡ %s ♡</text>'
            % (w - 4, PINK, w // 2, MONO, VIOLET_DARK, escape(label))
        )
        name = "link-%s.svg" % slug(label)
        write(name, svg(w, 44, body, CHROME_DEFS))
        out.append((ln, name))
    return out


def build_footer(cfg):
    """A 'blue screen' (on the same CRT screen as the banner) sitting on an XP taskbar."""
    w, scr_h, tb_h = 1000, 160, 44
    h = scr_h + tb_h
    fs = 17
    cw = fs * MONO_W
    name = cfg["name"]
    lw = (len(name) + 2) * cw + 4
    stop = "*** STOP: 0x00000042 (THANKS_FOR_STOPPING_BY)"
    press = "Press any key to continue "
    px0 = 500 - (len(press) + 1) * cw / 2
    crt_defs, screen_bg = crt(w, scr_h)
    screen = (
        screen_bg
        + f'<rect x="{500 - lw / 2:g}" y="30" width="{lw:g}" height="26" fill="{ICE}"/>'
        f'<text x="500" y="49" text-anchor="middle" font-family="{MONO}" font-size="{fs}" font-weight="700" '
        f'fill="{SCREEN}">{escape(name)}</text>'
        f'<text x="500" y="92" text-anchor="middle" font-family="{MONO}" font-size="{fs}" fill="#fff">{escape(stop)}</text>'
        f'<text x="{px0:g}" y="128" font-family="{MONO}" font-size="{fs}" fill="#fff" xml:space="preserve">{escape(press)}</text>'
        f'<rect x="{px0 + len(press) * cw:g}" y="130" width="{cw:g}" height="3" fill="#fff">'
        '<animate attributeName="opacity" values="1;0" calcMode="discrete" dur="1.1s" repeatCount="indefinite"/></rect>'
    )

    ty = scr_h
    cy = ty + tb_h / 2
    # start button: rounded on the right, flush left (the outer clip rounds the corner)
    start = (
        f'<rect x="-24" y="{ty}" width="146" height="{tb_h}" rx="{tb_h / 2:g}" fill="url(#btnx)"/>'
        f'<rect x="-24" y="{ty + 2}" width="140" height="{tb_h / 2 - 4:g}" rx="10" fill="#fff" opacity="0.22"/>'
        f'<rect x="-24" y="{ty}" width="146" height="{tb_h}" rx="{tb_h / 2:g}" fill="none" stroke="#fff" stroke-width="1.5"/>'
    )
    for (dx, dy), col in zip(((0, 0), (9, 0), (0, 9), (9, 9)), ("#ffffff", ICE_BLUE, LAVENDER, PINK_SOFT)):
        start += f'<rect x="{17 + dx}" y="{cy - 9 + dy:g}" width="8" height="8" rx="1.5" fill="{col}"/>'
    start += (
        f'<text x="45" y="{cy + 7:g}" font-family="{SANS}" font-size="20" font-weight="700" font-style="italic" '
        'fill="#000" opacity="0.3">start</text>'
        f'<text x="44" y="{cy + 6:g}" font-family="{SANS}" font-size="20" font-weight="700" font-style="italic" '
        'fill="#fff">start</text>'
    )
    tasks, tx = "", 138
    for label, pressed, icon in (("about_me.exe", True, PINK_SOFT), ("skills", False, ICE_BLUE), ("projects", False, LAVENDER)):
        tw = 168
        tasks += (
            f'<rect x="{tx}" y="{ty + 7}" width="{tw}" height="{tb_h - 14}" rx="4" '
            f'fill="url(#{"taskdown" if pressed else "task"})" stroke="{"#2a0f5c" if pressed else "#c9a8ff"}" stroke-width="1"/>'
            f'<rect x="{tx + 10}" y="{cy - 6:g}" width="12" height="12" rx="2.5" fill="{icon}"/>'
            f'<text x="{tx + 30}" y="{cy + 5:g}" font-family="{SANS}" font-size="13" '
            f'font-weight="{700 if pressed else 400}" fill="#fff">{escape(label)}</text>'
        )
        tx += tw + 6
    trx = 838
    tray = (
        f'<rect x="{trx}" y="{ty}" width="{w - trx}" height="{tb_h}" fill="url(#tray)"/>'
        f'<rect x="{trx}" y="{ty}" width="1" height="{tb_h}" fill="#b48cff"/>'
        f'<path d="M{trx + 18} {cy - 3:g}h3l5 -4v14l-5 -4h-3z" fill="{ICE}"/>'
        f'<path d="M{trx + 29} {cy - 4:g}q4 4 0 8" fill="none" stroke="{ICE}" stroke-width="1.6" stroke-linecap="round"/>'
        + "".join(f'<rect x="{trx + 46 + 5 * i}" y="{cy + 6 - 4 * (i + 1):g}" width="3" height="{4 * (i + 1)}" fill="{ICE}" '
                  f'opacity="{0.55 + 0.15 * i:g}"/>' for i in range(3))
        + f'<text x="{w - 46}" y="{cy + 5:g}" text-anchor="middle" font-family="{SANS}" font-size="14" fill="#fff">00:42</text>'
    )
    taskbar = (
        f'<rect y="{ty}" width="{w}" height="{tb_h}" fill="url(#taskbar)"/>'
        f'<rect y="{ty}" width="{w}" height="1.5" fill="#d9c2ff"/>'
        + tasks + tray + start
    )
    defs = CHROME_DEFS + crt_defs + (
        f'<clipPath id="clip"><rect width="{w}" height="{h}" rx="14"/></clipPath>'
        '<linearGradient id="taskbar" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#9a6af0"/><stop offset="0.15" stop-color="#7440d0"/>'
        '<stop offset="0.6" stop-color="#5a2aae"/><stop offset="1" stop-color="#42198a"/></linearGradient>'
        '<linearGradient id="task" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#a77cf5"/><stop offset="1" stop-color="#7a48d6"/></linearGradient>'
        '<linearGradient id="taskdown" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#3a1478"/><stop offset="1" stop-color="#4f2296"/></linearGradient>'
        '<linearGradient id="tray" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#6a36c4"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>'
    )
    body = (
        f'<g clip-path="url(#clip)">{screen}{taskbar}</g>'
        f'<rect x="1.5" y="1.5" width="{w - 3}" height="{h - 3}" rx="13" fill="none" stroke="#fff" stroke-width="3" opacity="0.9"/>'
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
    r = ['<div align="center">', "",
         '<img src="assets/banner.svg" alt="%s" width="100%%"/>' % attr(cfg["name"]), "",
         '<img src="assets/about-window.svg" alt="About me: %s" width="100%%"/>' % attr(" ".join(cfg["bio"])), "",
         divider, ""]
    r += table([('<img src="assets/%s" alt="%s: %s" width="100%%"/>'
                 % (name, attr(cat), attr(", ".join(cfg["skills"][cat]))), 2 if wide else 1)
                for cat, name, wide in skills])
    r += [divider, ""]
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
    # drop generated files from a previous run so removed skills/projects don't linger
    card_style(cfg)  # fail early on a typo
    for pattern in ("skills.svg", "skills-*.svg", "project-*.svg", "link-*.svg"):
        for stale in ASSETS.glob(pattern):
            stale.unlink()
    build_banner(cfg)
    build_divider()
    build_about(cfg)
    skills = build_skills(cfg)
    projects = build_projects(cfg)
    links = build_links(cfg)
    build_footer(cfg)
    build_readme(cfg, skills, projects, links)
    print("done.")


if __name__ == "__main__":
    main()
