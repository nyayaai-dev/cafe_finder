"""Turn raw OpenStreetMap layers into compact map data for the page.

Writes map_base.json (land, water, green areas, main roads, rail; embedded in
the page) and map_minor.json (residential streets; loaded when zoomed in).
Coordinates are delta-encoded integers (1e5 degrees, about 1 m)."""
import json, math, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")   # inputs and generated data
RAW = os.path.join(HERE, "raw")
# View rectangle the land polygons are closed against (slightly inside the download box).
S, W, N, E = 18.85, 72.73, 19.35, 73.21
Q = 1e5


def load(name):
    return json.load(open(os.path.join(RAW, name + ".json"), encoding="utf-8"))


def simplify(pts, tol):
    """Iterative Douglas-Peucker on (lat, lng) tuples."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (y1, x1), (y2, x2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy)
        imax, dmax = -1, 0.0
        for i in range(a + 1, b):
            y, x = pts[i]
            # closed ring (first point == last point): measure distance from that point
            d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norm if norm > 1e-12 else math.hypot(x - x1, y - y1)
            if d > dmax:
                imax, dmax = i, d
        if dmax > tol and imax > 0:
            keep[imax] = True
            stack += [(a, imax), (imax, b)]
    return [p for p, k in zip(pts, keep) if k]


def enc(pts):
    out, py, px = [], 0, 0
    for y, x in pts:
        iy, ix = round(y * Q), round(x * Q)
        out += [iy - py, ix - px]
        py, px = iy, ix
    return out


def geom(el):
    return [(p["lat"], p["lon"]) for p in el.get("geometry") or [] if p]


# ------------------------------------------------------------------ land from coastline
def chain_ways(ways):
    """Join directed coastline ways end-to-start into chains."""
    key = lambda p: (round(p[0], 7), round(p[1], 7))
    chains = [w for w in ways if len(w) >= 2]
    merged = True
    while merged:
        merged = False
        starts = {}
        for i, c in enumerate(chains):
            if key(c[0]) != key(c[-1]):
                starts.setdefault(key(c[0]), i)
        used, out = set(), []
        for i, c in enumerate(chains):
            if i in used:
                continue
            cur = c
            used.add(i)
            while key(cur[0]) != key(cur[-1]):
                j = starts.get(key(cur[-1]))
                if j is None or j in used:
                    break
                cur = cur + chains[j][1:]
                used.add(j)
                merged = True
            out.append(cur)
        chains = out
    return chains


def inside(p):
    return S <= p[0] <= N and W <= p[1] <= E


def clip_segment(a, b):
    """Liang-Barsky: returns (t0, t1) of the part of a->b inside the box, or None."""
    (y0, x0), (y1, x1) = a, b
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - W), (dx, E - x0), (-dy, y0 - S), (dy, N - y0)):
        if p == 0:
            if q < 0:
                return None
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
    return (t0, t1) if t0 <= t1 else None


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def clip_chain(c):
    """Split a chain into pieces inside the box; returns (closed_rings, open_pieces)."""
    closed = c[0] == c[-1]
    if closed and all(inside(p) for p in c):
        return [c], []
    pieces, cur = [], None
    for a, b in zip(c, c[1:]):
        r = clip_segment(a, b)
        if r is None:
            if cur:
                pieces.append(cur); cur = None
            continue
        t0, t1 = r
        pa, pb = lerp(a, b, t0), lerp(a, b, t1)
        if cur is None:
            cur = [pa]
        cur.append(pb)
        if t1 < 1.0:      # left the box
            pieces.append(cur); cur = None
    if cur:
        pieces.append(cur)
    return [], [p for p in pieces if len(p) >= 2]


def perim(p):
    """Position on the box boundary, counter-clockwise from the south-west corner (0..4)."""
    y, x = p
    d = [abs(y - S), abs(x - E), abs(y - N), abs(x - W)]
    side = d.index(min(d))
    if side == 0:
        return (x - W) / (E - W)
    if side == 1:
        return 1 + (y - S) / (N - S)
    if side == 2:
        return 2 + (E - x) / (E - W)
    return 3 + (N - y) / (N - S)


CORNERS = [(1.0, (S, E)), (2.0, (N, E)), (3.0, (N, W)), (4.0, (S, W))]


def walk(t_from, t_to):
    """Corners passed going counter-clockwise from t_from to t_to."""
    d = (t_to - t_from) % 4
    pts, k = [], math.floor(t_from) + 1
    while k - t_from <= d + 1e-12 and len(pts) < 4:
        pts.append(CORNERS[(k - 1) % 4][1])
        k += 1
    return pts


def land_rings(coast):
    rings, pieces = [], []
    for c in chain_ways([geom(w) for w in coast]):
        r, p = clip_chain(c)
        rings += r
        pieces += p
    # Ends that stop short of the box (data gaps) are extended straight to the nearest edge.
    fixed = []
    for p in pieces:
        for end in (0, -1):
            y, x = p[end]
            d = [abs(y - S), abs(x - E), abs(y - N), abs(x - W)]
            if min(d) > 1e-9:
                side = d.index(min(d))
                snap = [(S, x), (y, E), (N, x), (y, W)][side]
                if end == 0:
                    p.insert(0, snap)
                else:
                    p.append(snap)
        fixed.append(p)
    info = [{"pts": p, "ts": perim(p[0]), "te": perim(p[-1])} for p in fixed]
    unused = set(range(len(info)))
    while unused:
        first = unused.pop()
        ring = list(info[first]["pts"])
        cur = first
        for _ in range(len(info) + 2):
            te = info[cur]["te"]
            cands = list(unused) + [first]
            nxt = min(cands, key=lambda j: (info[j]["ts"] - te) % 4)
            ring += walk(te, info[nxt]["ts"])
            if nxt == first:
                break
            ring += info[nxt]["pts"]
            unused.discard(nxt)
            cur = nxt
        ring.append(ring[0])
        rings.append(ring)
    return rings


# ------------------------------------------------------------------ polygons from ways / relations
def assemble(ways):
    """Join unordered member ways into closed rings."""
    key = lambda p: (round(p[0], 7), round(p[1], 7))
    segs = [w for w in ways if len(w) >= 2]
    rings = []
    while segs:
        cur = segs.pop()
        changed = True
        while key(cur[0]) != key(cur[-1]) and changed:
            changed = False
            for i, s in enumerate(segs):
                if key(s[0]) == key(cur[-1]):
                    cur = cur + s[1:]
                elif key(s[-1]) == key(cur[-1]):
                    cur = cur + s[::-1][1:]
                elif key(s[-1]) == key(cur[0]):
                    cur = s + cur[1:]
                elif key(s[0]) == key(cur[0]):
                    cur = s[::-1] + cur[1:]
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        if key(cur[0]) == key(cur[-1]) and len(cur) >= 4:
            rings.append(cur)
    return rings


def polygons(elements):
    out = []
    for el in elements:
        if el["type"] == "way":
            g = geom(el)
            if len(g) >= 4 and g[0] == g[-1]:
                out.append((el.get("tags", {}), g))
        elif el["type"] == "relation":
            outers = [[(p["lat"], p["lon"]) for p in m["geometry"] if p] for m in el.get("members", [])
                      if m.get("type") == "way" and m.get("role") in ("outer", "") and m.get("geometry")]
            for r in assemble(outers):
                out.append((el.get("tags", {}), r))
    return out


def size_ok(r, min_deg):
    ys = [p[0] for p in r]; xs = [p[1] for p in r]
    return (max(ys) - min(ys)) > min_deg or (max(xs) - min(xs)) > min_deg


def poly_layer(items, tol, min_deg):
    out = []
    for r in items:
        if not size_ok(r, min_deg):
            continue
        s = simplify(r, tol)
        if len(s) >= 4:
            out.append(enc(s))
    return out


def green_class(t):
    if t.get("boundary") == "national_park" or t.get("leisure") == "nature_reserve" or \
            t.get("landuse") == "forest" or t.get("natural") == "wood":
        return "forest"
    if t.get("leisure") in ("park", "garden", "golf_course"):
        return "park"
    return "grass"


# ------------------------------------------------------------------ build
base = {}
coast = load("coast")
land = land_rings(coast)
base["land"] = poly_layer(land, 0.00008, 0.0005)
print("land rings:", len(base["land"]))

water = polygons(load("water"))
base["water"] = poly_layer([r for _, r in water], 0.00006, 0.0006)
wet = polygons(load("wetland"))
base["mangrove"] = poly_layer([r for t, r in wet], 0.00008, 0.0008)
green = polygons(load("green"))
for cls in ("forest", "park", "grass"):
    base[cls] = poly_layer([r for t, r in green if green_class(t) == cls], 0.00006, 0.0006)
print({k: len(v) for k, v in base.items()})

ROAD_CLASS = {"motorway": "motorway", "trunk": "trunk", "primary": "primary", "secondary": "secondary", "tertiary": "tertiary"}
CELL = 0.04


def cell_of(pts):
    y, x = pts[len(pts) // 2]
    return f"{int((y - 18) / CELL)}_{int((x - 72) / CELL)}"


roads = {}
for el in load("roads_major"):
    hw = el.get("tags", {}).get("highway", "").replace("_link", "")
    cls = ROAD_CLASS.get(hw)
    g = geom(el)
    if not cls or len(g) < 2:
        continue
    s = simplify(g, 0.00003)
    roads.setdefault(cls, {}).setdefault(cell_of(s), []).append(enc(s))
base["roads"] = roads

rail = {}
for el in load("rail"):
    t = el.get("tags", {})
    kind = {"subway": "metro", "light_rail": "metro", "monorail": "metro"}.get(t.get("railway"), "rail")
    g = geom(el)
    if len(g) >= 2:
        rail.setdefault(kind, []).append(enc(simplify(g, 0.00004)))
base["rail"] = rail

minor = {}
n_minor = 0
for i in range(3):
    for j in range(3):
        path = os.path.join(RAW, f"roads_minor_{i}{j}.json")
        if not os.path.exists(path):
            continue
        for el in json.load(open(path, encoding="utf-8")):
            g = geom(el)
            if len(g) >= 2:
                s = simplify(g, 0.00004)
                minor.setdefault(cell_of(s), []).append(enc(s))
                n_minor += 1

json.dump(base, open(os.path.join(DATA_DIR, "map_base.json"), "w"), separators=(",", ":"))
json.dump({"cell": CELL, "cells": minor}, open(os.path.join(DATA_DIR, "map_minor.json"), "w"), separators=(",", ":"))
print("base", os.path.getsize(os.path.join(DATA_DIR, "map_base.json")) // 1024, "KB;",
      "minor", os.path.getsize(os.path.join(DATA_DIR, "map_minor.json")) // 1024, "KB,", n_minor, "streets in", len(minor), "cells")
