"""GET /api/place?name=..&lat=..&lng=..  ->  live Google details for one place.

Runs as a Vercel Python function (and locally through dev_server.py). The
Google key stays on the server in the GOOGLE_MAPS_API_KEY environment variable.

    /api/place?probe=1  ->  {"configured": true|false}   (the page checks this first)

One Google Places Text Search call per lookup, biased to 300 m around the
place, picking the closest result within 400 m. The page asks only when a
place's popup is opened, so costs stay proportional to real use.
"""
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

FIELDS = ",".join([
    "places.id", "places.displayName", "places.location", "places.rating", "places.userRatingCount",
    "places.priceLevel", "places.priceRange", "places.servesVegetarianFood",
    "places.currentOpeningHours.openNow", "places.googleMapsUri", "places.websiteUri",
])
PRICE = {"PRICE_LEVEL_FREE": 0, "PRICE_LEVEL_INEXPENSIVE": 1, "PRICE_LEVEL_MODERATE": 2,
         "PRICE_LEVEL_EXPENSIVE": 3, "PRICE_LEVEL_VERY_EXPENSIVE": 4}
# Only answer for places inside the region the site covers.
REGION = (18.80, 72.70, 19.40, 73.25)


def key():
    return os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()


def metres(a, b):
    dy = (a[0] - b[0]) * 111_320
    dx = (a[1] - b[1]) * 111_320 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


def money(m):
    return int(m["units"]) if m and m.get("units") is not None else None


def lookup(name, lat, lng):
    body = {
        "textQuery": name,
        "pageSize": 3,
        "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": 300.0}},
    }
    req = urllib.request.Request(
        "https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": key(), "X-Goog-FieldMask": FIELDS})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode())
    best = None
    for p in data.get("places", []):
        loc = p.get("location", {})
        d = metres((lat, lng), (loc.get("latitude", 0), loc.get("longitude", 0)))
        if d <= 400 and (best is None or d < best[0]):
            best = (d, p)
    if not best:
        return {"found": False}
    p = best[1]
    pr = p.get("priceRange", {})
    return {
        "found": True,
        "name": p.get("displayName", {}).get("text"),
        "rating": p.get("rating"),
        "reviews": p.get("userRatingCount", 0),
        "priceLevel": PRICE.get(p.get("priceLevel")),
        "priceFrom": money(pr.get("startPrice")),     # per person, rupees
        "priceTo": money(pr.get("endPrice")),
        "veg": p.get("servesVegetarianFood"),
        "openNow": p.get("currentOpeningHours", {}).get("openNow"),
        "url": p.get("googleMapsUri"),
        "website": p.get("websiteUri"),
        "metres": round(best[0]),
    }


def respond(query):
    """(status, payload, cache seconds) for a parsed query dict."""
    if "probe" in query:
        return 200, {"configured": bool(key())}, 0
    if not key():
        return 503, {"error": "Google lookups are not set up on this site."}, 0
    try:
        name = query.get("name", "").strip()[:120]
        lat, lng = float(query["lat"]), float(query["lng"])
    except (KeyError, ValueError):
        return 400, {"error": "name, lat and lng are required"}, 0
    if not name or not (REGION[0] <= lat <= REGION[2] and REGION[1] <= lng <= REGION[3]):
        return 400, {"error": "place is outside the covered region"}, 0
    try:
        return 200, lookup(name, lat, lng), 86400
    except urllib.error.HTTPError as e:
        return 502, {"error": f"Google returned {e.code}"}, 0
    except Exception:
        return 502, {"error": "Google lookup failed"}, 0


class handler(BaseHTTPRequestHandler):  # Vercel's Python runtime looks for this name
    def do_GET(self):
        q = {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).items()}
        status, payload, cache = respond(q)
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        # Cache at the edge for a day so repeat opens of a popup cost nothing.
        self.send_header("Cache-Control", f"public, max-age=0, s-maxage={cache}" if cache else "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
