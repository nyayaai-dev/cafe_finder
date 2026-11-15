"""Cafe Finder prototype server (Python standard library only).

Serves the UI from ./public and exposes a small JSON API:

  GET /api/config                         -> which data source is active
  GET /api/locations                      -> preset areas (Mumbai for now)
  GET /api/geocode?q=Bandra West          -> bounding box for a place inside Mumbai
  GET /api/tile?s=..&w=..&n=..&e=..       -> cafes inside one rectangle

Data sources
  * Google Places API (New) Text Search, when GOOGLE_MAPS_API_KEY is set.
    One call returns at most 20 results and pagination stops at 60, so the
    browser splits the area into tiles and subdivides any tile that hits the
    60 cap ("saturated") until every tile is below it. That is how the crawl
    reaches every cafe Google has in the area rather than just the top 60.
  * OpenStreetMap (Overpass API) otherwise, so the prototype works without a key.

Every tile response is cached on disk in ./cache, so re-running a crawl is free.

Run:  py server.py            (then open http://127.0.0.1:8770)
      set GOOGLE_MAPS_API_KEY=...  (or put it in a .env file next to this script)
"""

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
CACHE = os.path.join(ROOT, "cache")
PORT = int(os.environ.get("PORT", "8770"))
USER_AGENT = "cafe-finder-prototype/0.1"

# Google place types treated as "cafe". Each type is queried separately.
GOOGLE_TYPES = ["cafe", "coffee_shop", "restaurant"]
DATA_VERSION = "v6"  # bump when the stored fields change, so old cache files are ignored
GOOGLE_MAX_PER_QUERY = 60  # Text Search hard cap (3 pages x 20)

LOCATIONS = {
    "mumbai": {
        "name": "Mumbai, Thane, Kalyan, Bhiwandi, Navi Mumbai and Panvel",
        # Colaba to Mira Road, Thane, Bhiwandi and Kalyan-Dombivli, Navi Mumbai down to Panvel.
        "bbox": {"s": 18.860, "w": 72.760, "n": 19.340, "e": 73.200},
        # Outline (lat, lng); Uran and the open sea stay out.
        "polygon": [
            (19.340, 72.760), (19.340, 73.100), (19.275, 73.195), (19.190, 73.195),
            (19.100, 73.125), (19.020, 73.150), (18.960, 73.150), (18.945, 73.050),
            (18.950, 72.980), (18.860, 72.900), (18.860, 72.760),
        ],
    },
}


def load_dotenv():
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_dotenv()
GOOGLE_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
SOURCE = "google" if GOOGLE_KEY else "osm"


# ---------------------------------------------------------------- helpers

def http_json(url, data=None, headers=None, timeout=60):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method="POST" if body else "GET")
    req.add_header("User-Agent", USER_AGENT)
    if body:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"{err.code} from upstream: {detail}") from None


def cache_get(key):
    path = os.path.join(CACHE, key + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return None


def cache_put(key, value):
    os.makedirs(CACHE, exist_ok=True)
    with open(os.path.join(CACHE, key + ".json"), "w", encoding="utf-8") as fh:
        json.dump(value, fh)


def tile_key(source, s, w, n, e):
    raw = f"{DATA_VERSION}|{source}|{s:.6f}|{w:.6f}|{n:.6f}|{e:.6f}|{','.join(GOOGLE_TYPES)}"
    return source + "_" + hashlib.sha1(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------- Google

GOOGLE_FIELDS = ",".join([
    "places.id", "places.displayName", "places.formattedAddress",
    "places.shortFormattedAddress", "places.location", "places.rating",
    "places.userRatingCount", "places.priceLevel", "places.priceRange", "places.googleMapsUri",
    "places.businessStatus", "places.primaryTypeDisplayName",
    "places.currentOpeningHours.openNow", "places.nationalPhoneNumber",
    "places.websiteUri", "places.types", "places.primaryType", "places.servesVegetarianFood", "nextPageToken",
])

# Google place types that describe what a cafe serves.
CUISINE_TYPES = {
    "coffee_shop", "bakery", "tea_house", "dessert_shop", "ice_cream_shop",
    "juice_shop", "sandwich_shop", "confectionery", "chocolate_shop", "donut_shop",
    "bagel_shop", "acai_shop", "cafeteria", "bar", "pub", "wine_bar",
}


def google_cuisine(types):
    out = []
    for t in types or []:
        if t in CUISINE_TYPES or (t.endswith("_restaurant") and t != "restaurant"):
            label = t.replace("_restaurant", "").replace("_shop", "").replace("_", " ").title()
            if label not in out:
                out.append(label)
    return out


MEAT_CUISINE = re.compile(r"chicken|seafood|fish|kebab|kabab|biryani|barbecue|bbq|mutton|steak|sushi|"
                          r"burger|shawarma|mughlai|malvani|goan|parsi|korean|japanese|thai|wings|meat|grill", re.I)


def osm_diet(t):
    """Pure veg / Jain / non-veg facts from the map's tags (None when unknown)."""
    veg = t.get("diet:vegetarian")
    pure_veg = veg == "only" or t.get("diet:vegan") == "only"
    jain = t.get("diet:jain") in ("yes", "only")
    meat = t.get("diet:meat") in ("yes", "only") or t.get("diet:non_vegetarian") in ("yes", "only") \
        or t.get("diet:non-vegetarian") in ("yes", "only")
    if not pure_veg and not meat and MEAT_CUISINE.search(t.get("cuisine") or ""):
        meat = True
    if pure_veg:
        meat = False
    return {"pureVeg": pure_veg or None, "jain": jain or None, "nonVeg": meat if (meat or pure_veg) else None,
            "vegOptions": veg in ("yes", "only") or None}


def osm_cuisine(tags):
    out = []
    for part in (tags.get("cuisine") or "").split(";"):
        label = part.strip().replace("_", " ").title()
        if label and label not in out:
            out.append(label)
    if tags.get("diet:vegetarian") in ("yes", "only") and "Vegetarian" not in out:
        out.append("Vegetarian" + (" only" if tags.get("diet:vegetarian") == "only" else ""))
    return out

CAFE_TYPES = {"cafe", "coffee_shop", "tea_house", "cat_cafe", "dog_cafe", "internet_cafe"}


def google_category(p):
    """'cafe' or 'restaurant', judged by the place's main type first."""
    primary = p.get("primaryType", "")
    if primary in CAFE_TYPES:
        return "cafe"
    if "restaurant" in primary or primary in ("meal_takeaway", "meal_delivery", "food_court", "diner"):
        return "restaurant"
    return "cafe" if CAFE_TYPES & set(p.get("types") or []) else "restaurant"


PRICE = {
    "PRICE_LEVEL_FREE": 0, "PRICE_LEVEL_INEXPENSIVE": 1, "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3, "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}


def money(m):
    """Google Money {currencyCode, units} -> whole rupees, or None."""
    if not m or m.get("units") is None:
        return None
    return int(m["units"])


def google_tile(s, w, n, e):
    places, saturated, calls = {}, False, 0
    for place_type in GOOGLE_TYPES:
        token, got = None, 0
        while True:
            body = {
                "textQuery": place_type.replace("_", " "),
                "includedType": place_type,
                "strictTypeFiltering": True,
                "pageSize": 20,
                "locationRestriction": {"rectangle": {
                    "low": {"latitude": s, "longitude": w},
                    "high": {"latitude": n, "longitude": e},
                }},
            }
            if token:
                body["pageToken"] = token
            data = http_json(
                "https://places.googleapis.com/v1/places:searchText", body,
                {"X-Goog-Api-Key": GOOGLE_KEY, "X-Goog-FieldMask": GOOGLE_FIELDS},
            )
            calls += 1
            for p in data.get("places", []):
                got += 1
                if p.get("businessStatus") == "CLOSED_PERMANENTLY":
                    continue
                loc = p.get("location", {})
                places[p["id"]] = {
                    "id": p["id"],
                    "name": p.get("displayName", {}).get("text", "Unnamed"),
                    "address": p.get("shortFormattedAddress") or p.get("formattedAddress", ""),
                    "lat": loc.get("latitude"), "lng": loc.get("longitude"),
                    "rating": p.get("rating"), "reviews": p.get("userRatingCount", 0),
                    "price": PRICE.get(p.get("priceLevel")),
                    # Google gives a per-person range, e.g. Rs 200-400.
                    "priceFrom": money(p.get("priceRange", {}).get("startPrice")),
                    "priceTo": money(p.get("priceRange", {}).get("endPrice")),
                    "openNow": p.get("currentOpeningHours", {}).get("openNow"),
                    "category": google_category(p),
                    "kind": p.get("primaryTypeDisplayName", {}).get("text", ""),
                    "cuisine": google_cuisine(p.get("types")),
                    # Google only says whether vegetarian food is served; it has no pure-veg or Jain flag.
                    "diet": {"pureVeg": None, "jain": None, "nonVeg": None,
                             "vegOptions": p.get("servesVegetarianFood")},
                    "phone": p.get("nationalPhoneNumber"),
                    "website": p.get("websiteUri"),
                    "url": p.get("googleMapsUri"),
                    "status": p.get("businessStatus"),
                }
            token = data.get("nextPageToken")
            if not token:
                break
        if got >= GOOGLE_MAX_PER_QUERY:
            saturated = True  # there may be more here than Google will page through
    return {"places": [p for p in places.values() if in_region(p)], "saturated": saturated, "calls": calls}


# ---------------------------------------------------------------- OpenStreetMap

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


CAFE_NAME = re.compile(r"\b(caf[eé]|cafe|coffee|kaapi|chai|tea|cha|crepe|patisserie|creamery)\b", re.I)


GENERIC_NAME = re.compile(r"^(cafe|café|cafeteria|canteen|restaurant|hotel|food|fast food|tea|tea stall|"
                          r"tea shop|chai|dhaba|bakery|snacks|juice|coffee|bar)$", re.I)


def place_name(t):
    """Best real name from any name tag, or None. Generic words don't count."""
    keys = ["name", "name:en", "brand", "alt_name", "official_name", "short_name"]
    keys += sorted(k for k in t if k.startswith("name:") and k not in ("name:en", "name:signed"))
    for k in keys:
        v = (t.get(k) or "").strip()
        if v and v.lower() != "no" and not GENERIC_NAME.match(v):
            return v
    return None


def classify(t):
    """(category, label) for an OSM element, or None to leave it out."""
    amenity, shop = t.get("amenity"), t.get("shop")
    name = t.get("name") or t.get("name:en") or ""
    cafe_name = bool(CAFE_NAME.search(name))
    if amenity == "cafe":
        return "cafe", "Cafe"
    if shop in ("coffee", "tea") and amenity is None:
        return "cafe", "Coffee shop" if shop == "coffee" else "Tea shop"
    if amenity == "ice_cream":
        return "cafe", "Dessert & ice cream"
    if shop in ("bakery", "pastry"):
        # Plain bakeries are shops; keep only the ones that run as cafes.
        return ("cafe", "Bakery cafe") if cafe_name or "coffee" in (t.get("cuisine") or "") else None
    if amenity in ("restaurant", "fast_food", "food_court"):
        if amenity == "restaurant" and re.search(r"\bcaf[eé]\b", name, re.I):
            return "cafe", "Cafe & restaurant"   # e.g. Mumbai's Irani cafes
        return "restaurant", {"fast_food": "Fast food", "food_court": "Food court"}.get(amenity, "Restaurant")
    return None


def osm_tile(s, w, n, e):
    query = f"""
[out:json][timeout:180];
(
  nwr["amenity"~"^(cafe|restaurant|fast_food|food_court|ice_cream)$"]({s},{w},{n},{e});
  nwr["shop"~"^(coffee|tea|bakery|pastry)$"]({s},{w},{n},{e});
);
out center tags;
"""
    data, last_err = None, None
    for attempt in range(2):
        for mirror in OVERPASS_MIRRORS:
            try:
                answer = http_json(mirror + "?" + urllib.parse.urlencode({"data": query}), timeout=240)
                if "remark" in answer:  # Overpass flags a cut-short answer here
                    raise RuntimeError("incomplete answer: " + answer["remark"][:120])
                data = answer
                break
            except Exception as exc:  # busy / timed out: try the next mirror
                last_err = exc
        if data is not None:
            break
        time.sleep(2 + 3 * attempt)
    if data is None:
        raise RuntimeError(f"All OpenStreetMap servers are busy, try again shortly ({last_err})")
    places = []
    for el in data.get("elements", []):
        t = el.get("tags", {})
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lng = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None:
            continue
        addr = ", ".join(x for x in [
            " ".join(filter(None, [t.get("addr:housenumber"), t.get("addr:street")])),
            t.get("addr:suburb") or t.get("addr:neighbourhood"),
            t.get("addr:city"),
        ] if x)
        kinds = classify(t)
        if not kinds:
            continue
        is_cafe = kinds[0] == "cafe"
        kind = kinds[1]
        name = place_name(t)
        if not name:
            continue  # no usable name anywhere in the data: leave it out
        places.append({
            "id": f"osm/{el['type']}/{el['id']}",
            "name": name, "address": addr, "lat": lat, "lng": lng,
            "rating": None, "reviews": 0, "price": None, "openNow": None,
            "category": "cafe" if is_cafe else "restaurant",
            "kind": kind,
            "cuisine": osm_cuisine(t),
            "diet": osm_diet(t),
            "phone": t.get("phone") or t.get("contact:phone"),
            "website": t.get("website") or t.get("contact:website"),
            "hours": t.get("opening_hours"),
            "menu": t.get("website:menu") or t.get("menu:url") or t.get("contact:menu") or t.get("menu"),
            "url": "https://www.google.com/maps/search/?api=1&query="
                   + urllib.parse.quote(f"{name} {lat},{lng}"),
        })
    return {"places": places, "saturated": False, "calls": 1}


def in_polygon(lat, lng, poly):
    """Ray casting point-in-polygon test on (lat, lng) pairs."""
    inside, j = False, len(poly) - 1
    for i in range(len(poly)):
        yi, xi = poly[i]
        yj, xj = poly[j]
        if (xi > lng) != (xj > lng) and lat < (yj - yi) * (lng - xi) / (xj - xi) + yi:
            inside = not inside
        j = i
    return inside


def in_region(p):
    return any(in_polygon(p["lat"], p["lng"], c["polygon"]) for c in LOCATIONS.values() if "polygon" in c)


def osm_area(s, w, n, e):
    """Cafes in a rectangle, served from a cached city-wide OSM download."""
    city = next((c["bbox"] for c in LOCATIONS.values()
                 if c["bbox"]["s"] <= s and c["bbox"]["w"] <= w
                 and n <= c["bbox"]["n"] and e <= c["bbox"]["e"]), None)
    box = city or {"s": s, "w": w, "n": n, "e": e}
    key = tile_key("osm", box["s"], box["w"], box["n"], box["e"])
    data = cache_get(key)
    cached = data is not None
    if not cached:
        data = osm_tile(box["s"], box["w"], box["n"], box["e"])
        cache_put(key, data)
    places = [p for p in data["places"] if s <= p["lat"] <= n and w <= p["lng"] <= e and in_region(p)]
    return {"places": places, "saturated": False, "calls": data["calls"], "cached": cached}


# ---------------------------------------------------------------- HTTP

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=PUBLIC, **kw)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s\n" % (fmt % args))

    def send_json(self, obj, code=200):
        raw = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if not url.path.startswith("/api/"):
            return super().do_GET()
        q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        try:
            if url.path == "/api/config":
                return self.send_json({"source": SOURCE, "types": GOOGLE_TYPES})
            if url.path == "/api/locations":
                return self.send_json(LOCATIONS)  # includes the outline polygon
            if url.path == "/api/geocode":
                return self.send_json(self.geocode(q.get("q", ""), q.get("city", "mumbai")))
            if url.path == "/api/tile":
                s, w, n, e = (float(q[k]) for k in ("s", "w", "n", "e"))
                key = tile_key(SOURCE, s, w, n, e)
                hit = cache_get(key)
                if hit is not None:
                    hit["cached"] = True
                    return self.send_json(hit)
                if SOURCE == "osm":
                    # One Overpass query covers the whole city; areas are filtered from it.
                    return self.send_json(osm_area(s, w, n, e))
                result = google_tile(s, w, n, e)
                cache_put(key, result)
                result["cached"] = False
                return self.send_json(result)
            return self.send_json({"error": "not found"}, 404)
        except Exception as exc:  # surface upstream errors to the UI
            return self.send_json({"error": str(exc)}, 502)

    def geocode(self, text, city):
        loc = LOCATIONS.get(city, LOCATIONS["mumbai"])
        b = loc["bbox"]
        if not text.strip() or text.strip().lower() in ("mumbai", "bombay", "all"):
            return {"name": loc["name"], "bbox": b}
        params = urllib.parse.urlencode({
            "q": text, "format": "json", "limit": 1, "countrycodes": "in",
            "viewbox": f"{b['w']},{b['n']},{b['e']},{b['s']}", "bounded": 1,
        })
        res = http_json("https://nominatim.openstreetmap.org/search?" + params)
        if not res:
            raise RuntimeError(f"Couldn't find '{text}' inside {loc['name']}")
        s, n, w, e = (float(x) for x in res[0]["boundingbox"])
        # Very small results (a single building) get padded to roughly 1 km.
        pad = 0.005
        if n - s < 2 * pad:
            s, n = s - pad, n + pad
        if e - w < 2 * pad:
            w, e = w - pad, e + pad
        # Clamp to the city box.
        s, w, n, e = max(s, b["s"]), max(w, b["w"]), min(n, b["n"]), min(e, b["e"])
        return {"name": res[0]["display_name"].split(",")[0], "bbox": {"s": s, "w": w, "n": n, "e": e}}


if __name__ == "__main__":
    print(f"Cafe Finder on http://127.0.0.1:{PORT}  (data source: {SOURCE})")
    if SOURCE == "osm":
        print("  No GOOGLE_MAPS_API_KEY found - using OpenStreetMap data.")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
