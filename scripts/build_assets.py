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

SANS = "'Trebuchet MS', 'Segoe UI', Verdana, sans-serif"
MONO = "'Courier New', ui-monospace, Menlo, Consolas, monospace"
MONO_W = 0.6  # approx glyph width / font-size for the mono stack

MESH_BRIGHT = [VIOLET_DARK, PURPLE, "#a23fc4", PINK]
MESH_DARK = ["#150829", "#241046", "#3a1670", "#5a1f8a"]


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


def sparkles(w, h, n, seed, rmin=5, rmax=13, colors=("#ffffff", ICE_BLUE, PINK_SOFT), box=None, line_ratio=0.3):
    """n random sparkles (a mix of solid and thin-line ones) inside `box`."""
    rng = random.Random(seed)
    x0, y0, x1, y1 = box or (15, 12, w - 15, h - 12)
    out = []
    for _ in range(n):
        x, y, r = rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(rmin, rmax)
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


# ---- assets ----------------------------------------------------------------
def build_banner(cfg):
    w, h = 1000, 300
    name = escape(cfg["name"])
    t = f'text-anchor="middle" font-family="{SANS}" font-size="96" font-weight="900" letter-spacing="4"'
    body = (
        f'<clipPath id="clip"><rect width="{w}" height="{h}" rx="14"/></clipPath>'
        f'<g clip-path="url(#clip)">{mesh(w, h, 50, MESH_BRIGHT, seed=7)}'
        f'<rect width="{w}" height="{h}" fill="url(#vig)"/>'
        '<rect x="-200" y="-20" width="90" height="340" fill="#fff" opacity="0.12" transform="skewX(-20)">'
        '<animate attributeName="x" values="-200;1200" dur="7s" repeatCount="indefinite"/></rect>'
        f'{sparkles(w, h, 16, 3)}</g>'
        f'<rect x="3" y="3" width="{w - 6}" height="{h - 6}" rx="12" fill="none" stroke="#fff" stroke-width="3" opacity="0.9"/>'
        # chromatic split: cyan fringe left, pink fringe right, chrome title on top
        '<g filter="url(#glow)">'
        f'<text x="495" y="159" {t} fill="{CYAN}" opacity="0.9">{name}</text>'
        f'<text x="505" y="164" {t} fill="{PINK}" opacity="0.9">{name}</text>'
        f'<text x="500" y="158" {t} fill="url(#chrome)" stroke="{VIOLET}" stroke-width="2.5" paint-order="stroke">{name}</text></g>'
        f'<text x="500" y="212" text-anchor="middle" font-family="{SANS}" font-size="24" letter-spacing="3" fill="#fff">'
        f'✦ {escape(cfg["tagline"])} ✦</text>'
    )
    defs = CHROME_DEFS + (
        '<radialGradient id="vig" cx="0.5" cy="0.5" r="0.7"><stop offset="0.5" stop-color="#000" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{VIOLET_DARK}" stop-opacity="0.55"/></radialGradient>'
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
        full = (
            '<clipPath id="clip"><rect x="2" y="2" width="%d" height="%d" rx="12"/></clipPath>'
            '<g clip-path="url(#clip)">%s<rect width="%d" height="%d" fill="%s" opacity="0.55"/></g>'
            '<rect x="2" y="2" width="%d" height="%d" rx="12" fill="none" stroke="%s" stroke-width="2"/>'
            '<text x="28" y="36" font-family="%s" font-size="21" font-weight="800" fill="url(#chrome)" '
            'stroke="%s" stroke-width="0.8" paint-order="stroke">✦ %s</text>%s%s'
            % (w - 4, h - 4, mesh(w, h, 44, MESH_DARK, seed=hash_seed(cat)), w, h, VIOLET_DARK,
               w - 4, h - 4, ORCHID, SANS, PURPLE, escape(cat.lower()), c["body"],
               sparkles(w, h, 2, hash_seed(cat) + 1, 4, 8, box=(w * 0.6, 10, w - 20, 40)))
        )
        name = "skills-%s.svg" % slug(cat)
        write(name, svg(w, h, full, defs))
        out.append((cat, name, c["wide"]))
    return out


def hash_seed(s):
    return sum(ord(c) * (i + 1) for i, c in enumerate(s))


def build_projects(cfg):
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
        body = (
            '<clipPath id="clip"><rect x="3" y="3" width="%d" height="%d" rx="9"/></clipPath>'
            '<g clip-path="url(#clip)">%s<rect width="%d" height="%d" fill="%s" opacity="0.62"/></g>'
            "%s"
            '<text font-family="%s" font-size="14" fill="%s">%s</text>%s%s'
            % (w - 6, h - 6, mesh(w, h, 40, MESH_DARK, seed=40 + i, bias=0.5), w, h, VIOLET_DARK,
               window_chrome(w, h, "%s.exe" % p["name"], 0, 0, 34, body_fill="none"),
               MONO, ICE, dt, tags, sparkles(w, h, 2, 90 + i, 4, 8, box=(400, 50, 465, 135)))
        )
        name = "project-%d.svg" % (i + 1)
        write(name, svg(w, h, body, CHROME_DEFS))
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


def build_footer():
    w, h = 1000, 130
    body = (
        f'<clipPath id="clip"><rect width="{w}" height="{h}" rx="14"/></clipPath>'
        f'<g clip-path="url(#clip)">{mesh(w, h, 50, list(reversed(MESH_BRIGHT)), seed=99)}{sparkles(w, h, 10, 5)}</g>'
        f'<rect x="3" y="3" width="{w - 6}" height="{h - 6}" rx="12" fill="none" stroke="#fff" stroke-width="3" opacity="0.9"/>'
        f'<text x="500" y="77" text-anchor="middle" font-family="{SANS}" font-size="30" font-weight="900" '
        f'fill="url(#chrome)" stroke="{PURPLE}" stroke-width="1.5" paint-order="stroke">thanks for stopping by ♡</text>'
    )
    write("footer.svg", svg(w, h, body, CHROME_DEFS))


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
         '<img src="assets/banner.svg" alt="%s - %s" width="100%%"/>' % (attr(cfg["name"]), attr(cfg["tagline"])), "",
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
    r += ['<img src="assets/footer.svg" alt="thanks for stopping by" width="100%"/>', "", "</div>", ""]
    (ROOT / "README.md").write_text("\n".join(r), encoding="utf-8")
    print("  wrote README.md")


def main():
    cfg = json.loads((ROOT / "profile.config.json").read_text(encoding="utf-8"))
    print("building assets...")
    # drop generated files from a previous run so removed skills/projects don't linger
    for pattern in ("skills-*.svg", "project-*.svg", "link-*.svg"):
        for stale in ASSETS.glob(pattern):
            stale.unlink()
    build_banner(cfg)
    build_divider()
    build_about(cfg)
    skills = build_skills(cfg)
    projects = build_projects(cfg)
    links = build_links(cfg)
    build_footer()
    build_readme(cfg, skills, projects, links)
    print("done.")


if __name__ == "__main__":
    main()
