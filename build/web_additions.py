"""Cafes in Malad-Dahisar that current web listings name but OpenStreetMap lacks.
Each is placed at its locality (geocoded) and flagged in the page as a web
listing with an approximate pin; Directions searches Google Maps by name."""
import json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")   # inputs and generated data
UA = "cafe-finder-prototype/0.1"

# name, locality to geocode, area label shown, kind, price for two (Rs) or None, source label, source url
CAFES = [
    ("Brunch 'N' Munch", "Orlem, Malad West", "Orlem, Malad West", "Cafe", 950, "District", "https://www.district.in/blog/mumbai-breakfast-cafes"),
    ("The Burrow Cafe", "Malad West", "Malad West", "Cafe", 900, "Free Press Journal", "https://www.freepressjournal.in/lifestyle/best-breakfast-spots-in-mumbais-western-suburbs-5-cafes-you-cant-miss"),
    ("Love & Latte", "Malad West", "Malad West", "Cafe", 650, "Swiggy", "https://www.localsamosa.com/food-and-drinks/coffee-shops-in-mumbai-10068806"),
    ("Blue Tokai Coffee Roasters (Malad West)", "Evershine Nagar, Malad West", "Evershine Nagar, Malad West", "Coffee shop", None, "Blue Tokai", "https://bluetokaicoffee.com/pages/blue-tokai-coffee-roasters-malad-west"),
    ("Circle Cafe", "Kanchpada, Malad West", "Kanchpada, Malad West", "Cafe", None, "Explurger", "https://www.explurger.com/pd/oyk1jaydvsbzqpbzk"),
    ("Aaron's Bake n Brew House", "Orlem, Malad West", "Orlem, Malad West", "Bakery cafe", None, "Foursquare", "https://lv.foursquare.com/anisha27310/list/the-best-afterwork-drink-spots-in-mumbai"),
    ("Magari", "Mahavir Nagar, Kandivali West", "Mahavir Nagar, Kandivali West", "Cafe", None, "Yappe", "https://yappe.in/maharashtra/mumbai/magari/280394"),
    ("Mittea Cafe", "Shantilal Modi Road, Kandivali West", "Shantilal Modi Road, Kandivali West", "Cafe", 300, "District", "https://www.district.in/dining/mumbai/mittea-cafe-kandivali-west"),
    ("Cafe Ville Villa", "Mhada Colony, Kandivali West", "MHB Colony, Kandivali West", "Cafe", None, "LBB", "https://lbb.in/places/Cafe-Ville-Villa-kandivali-west-0834d6"),
    ("Third Wave Coffee (Kandivali West)", "Mahavir Nagar, Kandivali West", "Sai Baba Extension Road, Mahavir Nagar, Kandivali West", "Coffee shop", None, "eChai", "https://echai.ventures/grid/mumbai/third-wave-coffee-35"),
    ("The Chocolate Room", "Mahavir Nagar, Kandivali West", "Mahavir Nagar, Kandivali West", "Cafe", None, "Foursquare", "https://lv.foursquare.com/anisha27310/list/the-best-afterwork-drink-spots-in-mumbai"),
    ("Blue Tokai Coffee Roasters (Kandivali East)", "Kandivali East", "Kandivali East", "Coffee shop", None, "Blue Tokai", "https://stores.bluetokaicoffee.com/blue-tokai-coffee-roasters-kandivali-east-cafe-kandivali-east-mumbai-436746/Home"),
    ("Tea Post", "Borivali West", "Borivali West", "Tea shop", None, "Trip101", "https://trip101.com/article/cafes-in-borivali"),
    ("Blue Bliss Cafe", "Borivali West", "Borivali West", "Cafe", None, "Trip101", "https://trip101.com/article/cafes-in-borivali"),
    ("Cafe Pibatie", "Borivali West", "Borivali West", "Cafe", None, "eChai", "https://echai.ventures/grid/mumbai/cafe-pibatie-borivali"),
    ("Third Wave Coffee (Borivali West)", "Roshan Nagar, Borivali West", "Roshan Nagar, Borivali West", "Coffee shop", None, "eChai", "https://echai.ventures/grid/mumbai/third-wave-coffee-34"),
    ("Blue Tokai Coffee Roasters (IC Colony)", "IC Colony, Borivali West", "IC Colony, Borivali West", "Coffee shop", None, "Blue Tokai", "https://stores.bluetokaicoffee.com/blue-tokai-coffee-roasters-ic-colony-borivali-cafe-borivali-west-mumbai-436750/Contact-Us/"),
    ("Bunkerzzz Cafe", "Borivali West", "Borivali", "Cafe", None, "Curly Tales", "https://curlytales.com/5-instagram-worthy-cafes-in-borivali-to-chill-after-a-long-day-at-work"),
    ("June Bistro & Bar", "Dahisar West", "Dahisar West", "Cafe & restaurant", None, "VenueLook", "https://www.venuelook.com/mumbai/locality/dahisar-west/venuetype/cafes"),
]

# Station fallbacks if a locality can't be geocoded.
FALLBACK = {"Malad West": (19.1868, 72.8420), "Kandivali West": (19.2043, 72.8440), "Kandivali East": (19.2043, 72.8620),
            "Borivali West": (19.2290, 72.8480), "Borivali": (19.2290, 72.8480), "Dahisar West": (19.2502, 72.8520)}
B = "72.80,19.28,72.90,19.16"


def geocode(q):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q + ", Mumbai", "format": "json", "limit": 1, "countrycodes": "in", "viewbox": B, "bounded": 1})
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
        res = json.loads(r.read().decode())
    return (float(res[0]["lat"]), float(res[0]["lon"])) if res else None


cache, out = {}, []
for name, loc, label, kind, price, src, url in CAFES:
    if loc not in cache:
        try:
            cache[loc] = geocode(loc)
        except Exception as e:
            print("geocode failed", loc, e, file=sys.stderr)
            cache[loc] = None
        time.sleep(1.1)
    pt = cache[loc]
    how = "street"
    if not pt:
        side = next(k for k in FALLBACK if loc.endswith(k))
        pt, how = FALLBACK[side], "station"
    out.append({"name": name, "lat": round(pt[0], 5), "lng": round(pt[1], 5), "kind": kind, "address": label,
                "priceTwo": price, "src": src, "srcUrl": url})
    print(f"{name:45s} {loc:38s} {pt[0]:.4f},{pt[1]:.4f} ({how})")

json.dump(out, open(os.path.join(DATA_DIR, "web_additions.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out), "web additions")
