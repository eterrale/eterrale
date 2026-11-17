"""Seeded low-poly mesh generator: returns SVG <polygon> markup.

A jittered grid is split into triangles; each triangle is filled from a
gradient defined by colour stops, with a little random lightness variation so
the facets catch the light like a low-poly render.
"""
import random


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _lerp_stops(stops, t):
    t = max(0.0, min(1.0, t))
    n = len(stops) - 1
    i = min(int(t * n), n - 1)
    local = t * n - i
    a, b = _hex(stops[i]), _hex(stops[i + 1])
    return tuple(a[k] + (b[k] - a[k]) * local for k in range(3))


def _shade(rgb, delta):
    out = []
    for v in rgb:
        v = v + (255 - v) * delta if delta > 0 else v * (1 + delta)
        out.append(max(0, min(255, int(round(v)))))
    return "#%02x%02x%02x" % tuple(out)


def mesh(width, height, cell, stops, seed=1, jitter=0.35, variation=0.10, bias=0.7):
    """Return a string of <polygon> elements covering width x height.

    stops     -- list of hex colours, interpolated along a diagonal gradient
    bias      -- weight of x vs y in the gradient direction (0..1)
    variation -- max per-facet lightness change (+/-)
    """
    rng = random.Random(seed)
    cols = max(2, round(width / cell))
    rows = max(2, round(height / cell))
    dx, dy = width / cols, height / rows

    pts = []
    for r in range(rows + 1):
        row = []
        for c in range(cols + 1):
            x, y = c * dx, r * dy
            # keep boundary points on the edge so the mesh fills the frame
            if 0 < c < cols:
                x += rng.uniform(-jitter, jitter) * dx
            if 0 < r < rows:
                y += rng.uniform(-jitter, jitter) * dy
            row.append((x, y))
        pts.append(row)

    def facet(a, b, c):
        cx = (a[0] + b[0] + c[0]) / 3 / width
        cy = (a[1] + b[1] + c[1]) / 3 / height
        t = cx * bias + cy * (1 - bias)
        color = _shade(_lerp_stops(stops, t), rng.uniform(-variation, variation))
        p = " ".join("%.1f,%.1f" % q for q in (a, b, c))
        return '<polygon points="%s" fill="%s" stroke="%s" stroke-width="0.4" stroke-opacity="0.5"/>' % (p, color, color)

    out = []
    for r in range(rows):
        for c in range(cols):
            tl, tr = pts[r][c], pts[r][c + 1]
            bl, br = pts[r + 1][c], pts[r + 1][c + 1]
            if rng.random() < 0.5:
                out.append(facet(tl, tr, bl))
                out.append(facet(tr, br, bl))
            else:
                out.append(facet(tl, tr, br))
                out.append(facet(tl, br, bl))
    return "\n".join(out)
