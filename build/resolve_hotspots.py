"""Match hotspot listings to map places (attach rating / cost / source) or,
when missing, place them at their geocoded locality as web listings.
Writes hotspots_resolved.json."""
import glob, json, math, os, re, sys, time, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")   # inputs and generated data
sys.path.insert(0, HERE)
from hotspots import H, SRC  # noqa: E402

CACHE = sys.argv[1]
UA = "cafe-finder-prototype/0.1"
files = sorted(glob.glob(os.path.join(CACHE, "osm_*.json")), key=os.path.getmtime, reverse=True)
places = json.load(open(files[0], encoding="utf-8"))["places"]
print("matching against", os.path.basename(files[0]), len(places), "places")

GEO_CACHE = os.path.join(DATA_DIR, "geocode_cache.json")
gcache = json.load(open(GEO_CACHE, encoding="utf-8")) if os.path.exists(GEO_CACHE) else {}


def geocode(q):
    if q in gcache:
        return gcache[q]
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q + ", Maharashtra", "format": "json", "limit": 1, "countrycodes": "in",
         "viewbox": "72.74,19.35,73.21,18.85", "bounded": 1})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
            res = json.loads(r.read().decode())
        pt = [float(res[0]["lat"]), float(res[0]["lon"])] if res else None
    except Exception as e:
        print("  geocode failed", q, e)
        pt = None
    gcache[q] = pt
    time.sleep(1.1)
    return pt


def norm(n):
    n = re.sub(r"\(.*?\)", "", n.lower())
    n = n.replace("&", " and ").replace("café", "cafe").replace("thé", "the")
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    n = re.sub(r"\b(the|restaurant|and bar|bar|cafe and bar)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def km(a, b):
    return math.hypot((a[0] - b[0]) * 111, (a[1] - b[1]) * 111 * math.cos(math.radians(19.1)))


out, matched = [], 0
for name, loc, kind, rating, rsrc, price, psrc, skey, veg in H:
    pt = geocode(loc) or geocode(loc.split(",")[-1].strip())
    key = norm(name)
    best = None
    if pt:
        for p in places:
            pn = norm(p["name"])
            if len(pn) < 4 or len(key) < 4:
                continue
            if key == pn or (key in pn and len(key) >= 5) or (pn in key and len(pn) >= 6):
                d = km(pt, (p["lat"], p["lng"]))
                if (d <= 2.2 or (key == pn and d <= 3.5 and "(" not in name)) and (best is None or d < best[0]):
                    best = (d, p)
    rec = {"name": name, "loc": loc, "kind": kind, "rating": rating, "ratingSrc": rsrc, "priceTwo": price,
           "priceSrc": psrc, "srcUrl": SRC[skey], "pureVeg": veg, "lat": pt[0] if pt else None, "lng": pt[1] if pt else None}
    if best:
        rec["matchId"] = best[1]["id"]
        matched += 1
        print(f"  MATCH  {name:42s} -> {best[1]['name']} ({best[0]:.1f} km)")
    else:
        print(f"  ADD    {name:42s} @ {loc} {'(no geocode)' if not pt else ''}")
    out.append(rec)

json.dump(gcache, open(GEO_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
json.dump(out, open(os.path.join(DATA_DIR, "hotspots_resolved.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(out)} hotspot listings: {matched} matched to map places, {len(out) - matched} added")
