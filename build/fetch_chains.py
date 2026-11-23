"""Chain outlets across the region, so every McDonald's, KFC, Domino's… shows on the map.

Sources:
  - All The Places (alltheplaces.xyz, CC0): outlet lists collected from each brand's own store
    locator. Spiders used: Burger King, KFC, Domino's, Pizza Hut, Baskin-Robbins, Chaayos,
    Taco Bell and Third Wave Coffee (India).
  - Brands' own outlet pages for Bhagat Tarachand and Kailash Parbat (pins placed at the mall /
    street named in the address, so they're marked approximate).
McDonald's, Subway and Starbucks come from OpenStreetMap (already in the places data); their
store locators can't be read without a browser.

Writes data/chains.json: [{name, lat, lng, address, hours, phone, website, kind, rest, cuisine,
diet, src, srcUrl, approx}]. build.py merges these with the map places, skipping any outlet
already on the map within 250 m."""
import json, os, sys, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
UA = "cafe-finder-prototype/0.1"
RUNS = "https://alltheplaces-data.openaddresses.io/runs/history.json"
OUTLINE = [(19.340, 72.760), (19.340, 73.100), (19.275, 73.195), (19.190, 73.195), (19.100, 73.125), (19.020, 73.150),
           (18.960, 73.150), (18.945, 73.050), (18.950, 72.980), (18.860, 72.900), (18.860, 72.760)]

# spider -> (name on the map, is restaurant, kind, cuisine, diet bits: 1 pure veg, 2 Jain, 4 non-veg, 8 veg options)
ATP = {
    "burger_king_in": ("Burger King", 1, "Fast food", "Burger", 12),
    "kfc_in": ("KFC", 1, "Fast food", "Chicken", 12),
    "dominos_pizza_in": ("Domino's", 1, "Fast food", "Pizza", 12),
    "pizza_hut_in": ("Pizza Hut", 1, "Restaurant", "Pizza", 12),
    "baskin_robbins_in": ("Baskin-Robbins", 0, "Dessert & ice cream", "Ice Cream", 1),
    "chaayos_in": ("Chaayos", 0, "Cafe", "Tea", 8),
    "taco_bell_in": ("Taco Bell", 1, "Fast food", "Mexican", 12),
    "third_wave_coffee_in": ("Third Wave Coffee Roasters", 0, "Cafe", "Coffee Shop", 8),
    "monginis_in": ("Monginis", 0, "Bakery cafe", "Cake;Bakery", 8),
}

BT = ("Bhagat Tarachand", 1, "Restaurant", "North Indian;Vegetarian", 3, "https://bhagattarachand.com/locations/")
KP = ("Kailash Parbat", 1, "Restaurant", "North Indian;Chaat;Vegetarian", 3, "https://kailashparbatgroup.com/locations-india/")
MANUAL = [  # brand, address (as listed), lat, lng (the mall / street named)
    (BT, "69/75 Mumbadevi Commercial Centre, Shaikh Memon Street, Zaveri Bazaar", 18.9497, 72.8331),
    (BT, "47/55 Mumbadevi Road, next to IDBI Bank, Pydhonie", 18.9531, 72.8327),
    (BT, "Mahavir Ratan, Sector 12, Vashi, Navi Mumbai", 19.0750, 73.0010),
    (BT, "Matulya Centre, A Wing, Ground Floor, Lower Parel", 18.9985, 72.8270),
    (BT, "Ghanshyam Chambers, opp. Citi Mall, New Link Road, Andheri West", 19.1378, 72.8327),
    (BT, "Viviana Mall, 2nd Floor Food Court, Thane West", 19.2087, 72.9712),
    (BT, "Seawoods Grand Central Mall, 2nd Floor Food Court, Seawoods", 19.0208, 73.0186),
    (BT, "Inorbit Mall, 2nd Floor Food Court, Malad West", 19.1730, 72.8355),
    (BT, "Inorbit Mall, 2nd Floor Food Court, Sector 30A, Vashi", 19.0657, 73.0014),
    (KP, "Inorbit Mall, Food Court, Malad West", 19.1731, 72.8357),
    (KP, "T2, Chhatrapati Shivaji Maharaj International Airport", 19.0974, 72.8742),
    (KP, "Lodha Xperia Mall, Food Court, Palava, Dombivli", 19.1622, 73.0786),
    (KP, "Seawoods Grand Central Mall, Food Court, Nerul", 19.0209, 73.0188),
    (KP, "AHCL Homes, New Link Road, Shimpoli, Borivali West", 19.2295, 72.8420),
]


def inside(lat, lng, poly=OUTLINE):
    res, j = False, len(poly) - 1
    for i in range(len(poly)):
        (yi, xi), (yj, xj) = poly[i], poly[j]
        if (yi > lat) != (yj > lat) and lng < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            res = not res
        j = i
    return res


def tidy(s):
    """Undo common mis-encoded punctuation in source addresses (e.g. 'â€œ' for '“')."""
    for bad, good in (("â€œ", "“"), ("â€�", "”"), ("â€\x9d", "”"), ("â€™", "’"), ("â€˜", "‘"), ("â€“", "–"), ("â€”", "—"), ("Â", ""), ("�", "")):
        s = s.replace(bad, good)
    return " ".join(s.split())


CHAIN_RE = ("Theobroma|Monginis|Merwan|Birdy|Ribbons ?(&|and) ?Balloons|Candies|Grandmama|Starbucks|Coffee Day|Third Wave|Blue Tokai|Tea Villa|"
            "Natural'?s? Ice ?Cream|Naturals|Belgian Waffle|Bachelorr?'?s|Havmor|Baskin|Giani|Love ?(&|and) ?Cheesecake|Haldiram|Shiv ?Sagar|Sukh ?Sagar|"
            "Bhagat Tarachand|Cream Cent(re|er)|Kailash Parbat|Prashant Corner|Mamledar|Jumbo King|Goli|Tibb'?s|Bikanervala|Banana Leaf|Jaffer ?Bhai|"
            "Behrouz|Faasos|Box8|Charcoal Eats|Copper Chimney|Persian Darbar|Mahesh Lunch|Gajalee|Domino|Pizza Hut|McDonald|Burger King|KFC|Subway|"
            "Popeyes|Taco Bell|Wow! ?Momo|Wow! ?China|Mainland China|Social|Pop Tate|Barbeque Nation|Sigree|Chili'?s")


def osm_chains():
    """All OpenStreetMap places in the region named / branded as one of the chains (cafes, restaurants, bakeries…)."""
    import time, urllib.parse
    bb = "18.85,72.74,19.35,73.21"
    q = (f'[out:json][timeout:200];('
         f'nwr["name"~"{CHAIN_RE}",i]["amenity"~"^(cafe|restaurant|fast_food|ice_cream|food_court|bar|pub)$"]({bb});'
         f'nwr["name"~"{CHAIN_RE}",i]["shop"~"^(bakery|confectionery|ice_cream|pastry|coffee|tea|deli|chocolate|food|sweets)$"]({bb});'
         f'nwr["brand"~"{CHAIN_RE}",i]["amenity"]({bb});nwr["brand"~"{CHAIN_RE}",i]["shop"]({bb}););out tags center;')
    for m in ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"] * 4:
        try:
            req = urllib.request.Request(m, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": UA})
            return json.loads(urllib.request.urlopen(req, timeout=220).read())["elements"]
        except Exception as e:
            print("  overpass retry:", str(e)[:60])
            time.sleep(12)
    raise RuntimeError("OpenStreetMap chain query failed")


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=240) as r:
        return r.read()


def main():
    runs = [r for r in json.loads(fetch(RUNS)) if r.get("output_url")]
    run = runs[-1]["run_id"]
    print("All The Places run", run)
    out = []
    for spider, (name, rest, kind, cuisine, diet) in ATP.items():
        d = json.loads(fetch(f"https://alltheplaces-data.openaddresses.io/runs/{run}/output/{spider}.geojson"))
        n = 0
        for f in d["features"]:
            g, p = f.get("geometry"), f.get("properties", {})
            if not g or not g.get("coordinates"):
                continue
            lng, lat = g["coordinates"][:2]
            if not inside(lat, lng):
                continue
            addr = p.get("addr:full") or ", ".join(x for x in (p.get("addr:street_address"), p.get("addr:city")) if x)
            out.append({"name": name, "lat": round(lat, 6), "lng": round(lng, 6), "address": tidy(addr).strip(" ,")[:160],
                        "hours": p.get("opening_hours", ""), "phone": p.get("phone", ""), "website": p.get("website", ""),
                        "kind": kind, "rest": rest, "cuisine": cuisine, "diet": diet, "src": f"{name} store locator",
                        "srcUrl": p.get("website") or f"https://www.alltheplaces.xyz/", "approx": 0})
            n += 1
        print(f"  {name}: {n} outlets in the region")
    for (name, rest, kind, cuisine, diet, url), addr, lat, lng in MANUAL:
        out.append({"name": name, "lat": lat, "lng": lng, "address": addr, "hours": "", "phone": "", "website": url,
                    "kind": kind, "rest": rest, "cuisine": cuisine, "diet": diet, "src": f"{name} outlet list",
                    "srcUrl": url, "approx": 1})
    print(f"  Bhagat Tarachand + Kailash Parbat: {len(MANUAL)} outlets from their own pages")

    # OpenStreetMap outlets of the chains (incl. bakeries / dessert shops the places download skips).
    els = osm_chains()
    n = 0
    for e in els:
        t = e.get("tags", {})
        name = t.get("name") or t.get("brand")
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lng = e.get("lon") or (e.get("center") or {}).get("lon")
        if not name or lat is None or not inside(lat, lng):
            continue
        a, s = t.get("amenity", ""), t.get("shop", "")
        kind = ("Fast food" if a == "fast_food" else "Cafe" if a == "cafe" or s in ("coffee", "tea") else
                "Dessert & ice cream" if a == "ice_cream" or s in ("ice_cream", "confectionery", "chocolate") else
                "Bakery cafe" if s in ("bakery", "pastry") else "Food court" if a == "food_court" else "Restaurant")
        addr = ", ".join(x for x in (t.get("addr:housenumber"), t.get("addr:street"), t.get("addr:suburb")) if x)
        out.append({"name": name, "lat": round(lat, 6), "lng": round(lng, 6), "address": tidy(addr), "hours": t.get("opening_hours", ""),
                    "phone": t.get("phone", ""), "website": t.get("website", ""), "kind": kind,
                    "rest": 1 if kind in ("Restaurant", "Fast food") else 0, "cuisine": ";".join(c.strip().replace("_", " ").title() for c in t.get("cuisine", "").split(";") if c.strip()),
                    "diet": 1 if t.get("diet:vegetarian") == "only" else 0, "src": "OpenStreetMap",
                    "srcUrl": f"https://www.openstreetmap.org/{e['type']}/{e['id']}", "approx": 0})
        n += 1
    print(f"  OpenStreetMap chain outlets: {n}")

    # Malls: outlets listed on the malls' own websites (data/mall_outlets.json), pinned at the mall.
    malls = json.load(open(os.path.join(HERE, "..", "data", "mall_outlets.json"), encoding="utf-8"))["malls"]
    KIND = {"restaurant": ("Restaurant", 1), "fast food": ("Fast food", 1), "food court": ("Fast food", 1), "cafe": ("Cafe", 0),
            "dessert": ("Dessert & ice cream", 0), "bakery": ("Bakery cafe", 0), "bar": ("Restaurant", 1)}
    n = 0
    for m in malls:
        seen = set()
        for name, typ in m["outlets"]:
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            kind, rest = KIND.get(typ, ("Restaurant", 1))
            out.append({"name": name, "lat": m["lat"], "lng": m["lng"], "address": m["mall"], "hours": "", "phone": "", "website": "",
                        "kind": kind, "rest": rest, "cuisine": "", "diet": 0, "src": m["mall"] + " directory", "srcUrl": m["source"],
                        "approx": 1, "radius": 0.4})
            n += 1
    print(f"  Mall directories: {n} outlets in {len(malls)} malls")
    json.dump(out, open(os.path.join(HERE, "..", "data", "chains.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(out), "chain outlets written")


if __name__ == "__main__":
    main()
