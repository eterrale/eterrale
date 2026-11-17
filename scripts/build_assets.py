#!/usr/bin/env python3
"""Build every SVG asset and README.md from profile.config.json.

Usage (from repo root):  python3 scripts/build_assets.py
Standard library only.
"""
import base64
import json
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


def sparkle(x, y, r, delay=0.0, color="#ffffff", dur=3.0):
    d = "M0 %g Q0 0 %g 0 Q0 0 0 %g Q0 0 %g 0 Q0 0 0 %g Z" % (-r, r, r, -r, -r)
    return (
        '<g transform="translate(%.1f %.1f)"><g>'
        '<path d="%s" fill="%s"/>'
        '<animateTransform attributeName="transform" type="scale" values="0.35;1;0.35" '
        'dur="%gs" begin="%gs" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0.25;1;0.25" dur="%gs" begin="%gs" repeatCount="indefinite"/>'
        "</g></g>" % (x, y, d, color, dur, delay, dur, delay)
    )


def sparkles(w, h, n, seed, rmin=5, rmax=13, colors=("#ffffff", ICE_BLUE, PINK_SOFT), box=None):
    rng = random.Random(seed)
    x0, y0, x1, y1 = box or (15, 12, w - 15, h - 12)
    return "\n".join(
        sparkle(rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(rmin, rmax),
                rng.uniform(0, 3), rng.choice(colors), rng.uniform(2.4, 4.2))
        for _ in range(n)
    )


CHROME_DEFS = (
    '<linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#ffffff"/><stop offset="0.45" stop-color="%s"/>'
    '<stop offset="0.5" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
    '<linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">'
    '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
    '<linearGradient id="pill" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#ffffff"/><stop offset="0.5" stop-color="%s"/>'
    '<stop offset="1" stop-color="%s"/></linearGradient>'
    % (ICE, ICE_BLUE, ORCHID, PINK, PURPLE, ICE, LAVENDER)
)


def window_chrome(w, h, title, x=0, y=0, bar=34, body_fill=VIOLET_DARK):
    """A Y2K window frame: bevelled body, gradient title bar, 3 buttons."""
    btn = ""
    for i, col in enumerate((ICE, LAVENDER, PINK_SOFT)):
        cx = x + w - 22 - i * 26
        btn += '<rect x="%d" y="%d" width="20" height="20" rx="4" fill="%s" stroke="#fff" stroke-width="1.5"/>' % (cx - 10, y + 7, col)
    btn += '<path d="M%d %d l8 8 m0 -8 l-8 8" stroke="%s" stroke-width="2" fill="none"/>' % (x + w - 26, y + 13, VIOLET)
    return (
        '<rect x="%d" y="%d" width="%d" height="%d" rx="10" fill="%s" stroke="#fff" stroke-width="2"/>'
        '<rect x="%d" y="%d" width="%d" height="%d" rx="10" fill="url(#bar)"/>'
        '<rect x="%d" y="%d" width="%d" height="12" fill="url(#bar)"/>'
        '<text x="%d" y="%d" font-family="%s" font-size="15" font-weight="700" fill="#fff">%s</text>%s'
        % (x, y, w, h, body_fill, x, y, w, bar, x, y + bar - 12, w, x + 16, y + 23, SANS, escape(title), btn)
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
    body = (
        '<clipPath id="clip"><rect width="%d" height="%d" rx="14"/></clipPath>'
        '<g clip-path="url(#clip)">%s'
        '<rect width="%d" height="%d" fill="url(#vig)"/>'
        '<rect x="-200" y="-20" width="90" height="340" fill="#fff" opacity="0.12" transform="skewX(-20)">'
        '<animate attributeName="x" values="-200;1200" dur="7s" repeatCount="indefinite"/></rect>'
        "%s</g>"
        '<rect x="3" y="3" width="%d" height="%d" rx="12" fill="none" stroke="#fff" stroke-width="3" opacity="0.9"/>'
        '<g filter="url(#glow)">'
        '<text x="504" y="168" text-anchor="middle" font-family="%s" font-size="96" font-weight="900" '
        'letter-spacing="4" fill="%s" opacity="0.85">%s</text>'
        '<text x="500" y="163" text-anchor="middle" font-family="%s" font-size="96" font-weight="900" '
        'letter-spacing="4" fill="url(#chrome)" stroke="%s" stroke-width="2.5" paint-order="stroke">%s</text></g>'
        '<text x="500" y="215" text-anchor="middle" font-family="%s" font-size="22" letter-spacing="3" fill="#fff">✦ %s ✦</text>'
        '<text x="500" y="255" text-anchor="middle" font-family="%s" font-size="16" fill="%s">%s</text>'
        % (w, h, mesh(w, h, 50, MESH_BRIGHT, seed=7), w, h,
           sparkles(w, h, 16, 3), w - 6, h - 6, SANS, PINK, escape(cfg["name"]),
           SANS, VIOLET, escape(cfg["name"]), SANS, escape(cfg["tagline"]), SANS, ICE, escape(cfg["greeting"]))
    )
    defs = CHROME_DEFS + (
        '<radialGradient id="vig" cx="0.5" cy="0.5" r="0.7"><stop offset="0.5" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="%s" stop-opacity="0.55"/></radialGradient>'
        '<filter id="glow" x="-10%%" y="-30%%" width="120%%" height="160%%">'
        '<feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        % VIOLET_DARK
    )
    write("banner.svg", svg(w, h, body, defs))


def build_divider():
    w, h = 1000, 44
    dots = "".join('<circle cx="%d" cy="22" r="2.5" fill="%s" opacity="%.2f"/>' % (x, PINK_SOFT, 0.35 + 0.65 * abs(((x // 20) % 6) - 3) / 3) for x in range(40, 450, 20))
    dots2 = "".join('<circle cx="%d" cy="22" r="2.5" fill="%s" opacity="%.2f"/>' % (w - x, ICE_BLUE, 0.35 + 0.65 * abs(((x // 20) % 6) - 3) / 3) for x in range(40, 450, 20))
    body = (
        dots + dots2
        + sparkle(500, 22, 15, 0, "#ffffff", 2.6)
        + sparkle(462, 22, 7, 0.5, PINK, 2.6)
        + sparkle(538, 22, 7, 1.0, ICE_BLUE, 2.6)
    )
    write("divider.svg", svg(w, h, body))


def _avatar(cfg, x, y, w, h):
    path = cfg.get("avatar")
    if path and (ROOT / path).exists():
        p = ROOT / path
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        data = base64.b64encode(p.read_bytes()).decode()
        return '<image x="%d" y="%d" width="%d" height="%d" preserveAspectRatio="xMidYMid slice" href="data:%s;base64,%s"/>' % (x, y, w, h, mime, data)
    # placeholder: low-poly mini scene + hint text
    return (
        '<svg x="%d" y="%d" width="%d" height="%d" viewBox="0 0 %d %d">%s'
        '<text x="%d" y="%d" text-anchor="middle" font-family="%s" font-size="14" fill="#fff">your art here</text>'
        '<text x="%d" y="%d" text-anchor="middle" font-family="%s" font-size="22" fill="#fff">%s</text></svg>'
        % (x, y, w, h, w, h, mesh(w, h, 34, MESH_BRIGHT, seed=21, bias=0.4),
           w // 2, h // 2 - 4, SANS, w // 2, h // 2 + 24, SANS, escape(cfg["kaomoji"]))
    )


def wrap_bullets(lines, width):
    """[(bullet index, text chunk, is first chunk of its bullet)] for every wrapped line."""
    out = []
    for i, line in enumerate(lines):
        for j, chunk in enumerate(textwrap.wrap(line, width) or [""]):
            out.append((i, chunk, j == 0))
    return out


def build_about(cfg):
    w, h = 1000, 360
    glyphs = (("♡", PINK_SOFT), ("★", ICE_BLUE), ("✧", LAVENDER), ("♪", PINK_SOFT))
    rows = wrap_bullets(cfg["bio"], 46)
    pitch = 36
    # centre the title + bio block vertically in the window body (y 54..340)
    title_y = max(96, 179 - 18 * (len(rows) - 1))
    first_y = title_y + 56
    bio = ""
    for k, (idx, chunk, first) in enumerate(rows):
        y = first_y + pitch * k
        if first:
            glyph, color = glyphs[idx % len(glyphs)]
            bio += '<text x="48" y="%d" font-family="%s" font-size="21" fill="%s">%s</text>' % (y, SANS, color, glyph)
        bio += '<text x="80" y="%d" font-family="%s" font-size="21" fill="%s">%s</text>' % (y, MONO, ICE, escape(chunk))
    title = (
        '<text x="48" y="%d" font-family="%s" font-size="34" font-weight="800" fill="url(#chrome)" '
        'stroke="%s" stroke-width="1" paint-order="stroke">hi, i\'m %s ✧</text>'
        % (title_y, SANS, PURPLE, escape(cfg["name"]))
    )
    body = (
        window_chrome(w - 40, h - 40, cfg["window_title"], 20, 20)
        + title + bio
        + '<rect x="722" y="86" width="236" height="236" rx="8" fill="none" stroke="#fff" stroke-width="3"/>'
        + '<rect x="714" y="78" width="236" height="236" rx="8" fill="none" stroke="%s" stroke-width="2" stroke-dasharray="6 5"/>' % PINK
        + _avatar(cfg, 726, 90, 228, 228)
        + sparkles(w, h, 5, 11, 5, 10, box=(665, 60, 700, 320))
    )
    write("about-window.svg", svg(w, h, body, CHROME_DEFS))


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
        defs = CHROME_DEFS
        name = "project-%d.svg" % (i + 1)
        write(name, svg(w, h, body, defs))
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
    w, h = 1000, 170
    body = (
        '<clipPath id="clip"><rect width="%d" height="%d" rx="14"/></clipPath>'
        '<g clip-path="url(#clip)">%s%s</g>'
        '<rect x="3" y="3" width="%d" height="%d" rx="12" fill="none" stroke="#fff" stroke-width="3" opacity="0.9"/>'
        '<text x="500" y="82" text-anchor="middle" font-family="%s" font-size="30" font-weight="900" fill="url(#chrome)" '
        'stroke="%s" stroke-width="1.5" paint-order="stroke">thanks for stopping by ♡</text>'
        '<text x="500" y="118" text-anchor="middle" font-family="%s" font-size="16" fill="#fff">%s</text>'
        % (w, h, mesh(w, h, 50, list(reversed(MESH_BRIGHT)), seed=99), sparkles(w, h, 12, 5),
           w - 6, h - 6, SANS, PURPLE, SANS, escape(cfg["kaomoji"] + "   see you in the next level   " + cfg["kaomoji"]))
    )
    write("footer.svg", svg(w, h, body, CHROME_DEFS))


# ---- README ----------------------------------------------------------------
def attr(text):
    return escape(text, {'"': "&quot;"})


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
    build_footer(cfg)
    build_readme(cfg, skills, projects, links)
    print("done.")


if __name__ == "__main__":
    main()
