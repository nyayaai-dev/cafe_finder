"""Fetch a light Mumbai base map (coastline, main roads, rail, big lakes) and
area bounding boxes, simplified for embedding in a static page."""
import json, os, sys, time, urllib.parse, urllib.request

OUT = os.path.dirname(os.path.abspath(__file__))
B = {"s": 18.890, "w": 72.775, "n": 19.275, "e": 72.990}
PAD = 0.03
BB = f"{B['s']-PAD},{B['w']-PAD},{B['n']+PAD},{B['e']+PAD}"
UA = "cafe-finder-prototype/0.1"
MIRRORS = [
    "https://overpass-api.de/api/interpreter",

    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def overpass(q):
    last = None
    for attempt in range(2):
        for m in MIRRORS:
            try:
                return get(m + "?" + urllib.parse.urlencode({"data": q}))
            except Exception as e:
                last = e
                print("  mirror failed:", m, str(e)[:80], file=sys.stderr)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(last)


def dp(pts, tol):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = (dx * dx + dy * dy) ** 0.5 or 1e-12
    imax, dmax = 0, 0
    for i in range(1, len(pts) - 1):
        x, y = pts[i]
        d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norm
        if d > dmax:
            imax, dmax = i, d
    if dmax > tol:
        return dp(pts[: imax + 1], tol)[:-1] + dp(pts[imax:], tol)
    return [pts[0], pts[-1]]


def lines(data, tol):
    out = []
    for el in data.get("elements", []):
        g = el.get("geometry")
        if not g:
            continue
        pts = dp([(p["lat"], p["lon"]) for p in g], tol)
        if len(pts) >= 2:
            out.append([[round(a, 4), round(b, 4)] for a, b in pts])
    return out


geo = {}
print("coastline…")
geo["coast"] = lines(overpass(f'[out:json][timeout:120];way["natural"="coastline"]({BB});out geom;'), 0.0002)
print("roads…")
roads = overpass(f'[out:json][timeout:150];way["highway"~"^(motorway|trunk|primary)$"]({BB});out geom tags;')
geo["major"] = lines({"elements": [e for e in roads["elements"] if e["tags"]["highway"] in ("motorway", "trunk")]}, 0.0002)
geo["primary"] = lines({"elements": [e for e in roads["elements"] if e["tags"]["highway"] == "primary"]}, 0.0002)
print("rail…")
geo["rail"] = lines(overpass(f'[out:json][timeout:120];way["railway"="rail"]["service"!~"."]({BB});out geom;'), 0.0003)
print("lakes…")
lakes = overpass(f'[out:json][timeout:120];(way["natural"="water"]["water"~"lake|reservoir"]({BB}););out geom;')
geo["lakes"] = [l for l in lines(lakes, 0.0003) if len(l) > 8]

AREAS = ["Colaba", "Fort", "Churchgate", "Marine Lines", "Girgaon", "Malabar Hill", "Grant Road",
         "Byculla", "Tardeo", "Worli", "Lower Parel", "Prabhadevi", "Dadar", "Matunga", "Mahim",
         "Sion", "Wadala", "Bandra West", "Bandra East", "Bandra Kurla Complex", "Khar", "Santacruz",
         "Vile Parle", "Juhu", "Versova", "Andheri West", "Andheri East", "Jogeshwari", "Goregaon",
         "Malad", "Kandivali", "Borivali", "Dahisar", "Powai", "Kurla", "Ghatkopar", "Vikhroli",
         "Bhandup", "Mulund", "Chembur"]
areas = []
for name in AREAS:
    q = urllib.parse.urlencode({"q": name + ", Mumbai", "format": "json", "limit": 1, "countrycodes": "in",
                                "viewbox": f"{B['w']},{B['n']},{B['e']},{B['s']}", "bounded": 1})
    try:
        r = get("https://nominatim.openstreetmap.org/search?" + q, 30)
    except Exception as e:
        r = []
        print("  nominatim failed", name, e, file=sys.stderr)
    if r:
        s, n, w, e = (float(x) for x in r[0]["boundingbox"])
        lat, lon = float(r[0]["lat"]), float(r[0]["lon"])
        half = 0.006
        if n - s < 2 * half: s, n = lat - half, lat + half
        if e - w < 2 * half: w, e = lon - half, lon + half
        areas.append({"name": name, "lat": round(lat, 4), "lng": round(lon, 4),
                      "bbox": [round(s, 4), round(w, 4), round(n, 4), round(e, 4)]})
        print(" ", name, areas[-1]["bbox"])
    time.sleep(1.1)  # Nominatim usage policy: 1 request per second
geo["areas"] = areas

with open(os.path.join(OUT, "geo.json"), "w") as fh:
    json.dump(geo, fh, separators=(",", ":"))
print({k: len(v) for k, v in geo.items()}, os.path.getsize(os.path.join(OUT, "geo.json")), "bytes")
