"""Fetch named localities, stations and a simplified base map for the region
Mira Road (north) to Panvel (east/south-east). Writes region.json."""
import json, os, sys, time, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")   # inputs and generated data
UA = "cafe-finder-prototype/0.1"
BB = "18.85,72.74,19.35,73.21"
MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]


def overpass(q, label):
    last = None
    for attempt in range(6):
        for m in MIRRORS:
            try:
                req = urllib.request.Request(m, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": UA})
                d = json.loads(urllib.request.urlopen(req, timeout=180).read())
                if "remark" in d:
                    raise RuntimeError("incomplete: " + d["remark"][:100])
                print(f"  {label}: {len(d['elements'])} elements from {m.split('/')[2]}", flush=True)
                return d
            except Exception as e:
                last = e
                print(f"  {label}: {m.split('/')[2]} failed ({str(e)[:70]})", flush=True)
        time.sleep(8 * (attempt + 1))
    raise RuntimeError(f"{label} failed: {last}")


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


def lines(els, tol):
    out = []
    for el in els:
        g = el.get("geometry")
        if g:
            pts = dp([(p["lat"], p["lon"]) for p in g], tol)
            if len(pts) >= 2:
                out.append([[round(a, 4), round(b, 4)] for a, b in pts])
    return out


region = {}
loc = overpass(f'''[out:json][timeout:150];(
 node["place"~"^(city|town|suburb|quarter|neighbourhood|village)$"]["name"]({BB});
 node["railway"="station"]["name"]({BB});
);out body;''', "localities")
region["localities"] = [{"name": e["tags"].get("name:en") or e["tags"]["name"], "lat": e["lat"], "lng": e["lon"],
                         "place": e["tags"].get("place"), "station": e["tags"].get("railway") == "station",
                         "subway": e["tags"].get("station") == "subway" or e["tags"].get("subway") == "yes",
                         "mono": "monorail" in (e["tags"].get("station") or "") or e["tags"].get("monorail") == "yes"}
                        for e in loc["elements"]]
coast = overpass(f'[out:json][timeout:150];way["natural"="coastline"]({BB});out geom;', "coastline")
region["coast"] = lines(coast["elements"], 0.0002)
roads = overpass(f'[out:json][timeout:180];way["highway"~"^(motorway|trunk|primary)$"]({BB});out geom tags;', "roads")
region["major"] = lines([e for e in roads["elements"] if e["tags"]["highway"] in ("motorway", "trunk")], 0.0002)
region["primary"] = lines([e for e in roads["elements"] if e["tags"]["highway"] == "primary"], 0.00025)
rail = overpass(f'[out:json][timeout:150];way["railway"="rail"]["service"!~"."]({BB});out geom;', "rail")
region["rail"] = lines(rail["elements"], 0.0003)

json.dump(region, open(os.path.join(DATA_DIR, "region.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print({k: len(v) for k, v in region.items()}, os.path.getsize(os.path.join(DATA_DIR, "region.json")), "bytes")
