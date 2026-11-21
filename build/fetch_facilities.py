"""Facilities for each place from OpenStreetMap, plus parking and EV charging nearby.

Writes data/facilities.json:
  {"places": {"osm/node/123": {"wifi": 1, "outdoor": 1, ...}},
   "parking": [[lat, lng], ...], "charging": [[lat, lng], ...]}

Tags read: internet_access (Wi-Fi), outdoor_seating, indoor_seating, air_conditioning,
wheelchair, takeaway, delivery, capacity. These are what mappers have recorded; a
missing tag means "not known", not "no"."""
import json, os, sys, time, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
UA = "cafe-finder-prototype/0.1"
BB = "18.85,72.74,19.35,73.21"
MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]

Q_PLACES = f"""[out:json][timeout:240];
nwr["amenity"~"^(cafe|restaurant|fast_food|ice_cream|food_court)$"]["name"]
   [~"^(internet_access|outdoor_seating|indoor_seating|air_conditioning|wheelchair|takeaway|delivery|capacity)$"~"."]({BB});
out tags;
"""
# Parking and charging, fetched in four tiles (one big query overloads the servers).
TILES = ["18.85,72.74,19.10,72.98", "19.10,72.74,19.35,72.98", "18.85,72.98,19.10,73.21", "19.10,72.98,19.35,73.21"]
Q_PARK = """[out:json][timeout:180];
(
  nwr["amenity"="parking"]["access"!~"^(private|no)$"]({bb});
  nwr["amenity"="charging_station"]({bb});
);
out center qt;
"""


def overpass(q, label):
    last = None
    for attempt in range(4):
        for m in MIRRORS:
            try:
                req = urllib.request.Request(m, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": UA})
                d = json.loads(urllib.request.urlopen(req, timeout=260).read())
                if "remark" in d:
                    raise RuntimeError("incomplete: " + d["remark"][:100])
                print(f"  {label}: {len(d['elements'])} elements from {m.split('/')[2]}", flush=True)
                return d
            except Exception as e:
                last = e
                print(f"  {label}: {m.split('/')[2]} failed ({str(e)[:70]})", flush=True)
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"{label} failed: {last}")


def yes(v):
    return str(v).lower() in ("yes", "only", "designated", "limited", "wlan", "wifi", "free", "customers", "terminal;wlan", "wlan;terminal")


def main():
    places = {}
    for e in overpass(Q_PLACES, "places with facility tags")["elements"]:
        t = e.get("tags", {})
        f = {}
        if t.get("internet_access") and t["internet_access"].lower() not in ("no", "none"):
            f["wifi"] = 1
        for key, name in (("outdoor_seating", "outdoor"), ("indoor_seating", "indoor"), ("air_conditioning", "ac"),
                          ("takeaway", "takeaway"), ("delivery", "delivery")):
            if key in t and yes(t[key]):
                f[name] = 1
            elif key in t and t[key].lower() == "no":
                f[name] = 0
        if t.get("wheelchair") in ("yes", "limited", "designated"):
            f["wheelchair"] = 1
        elif t.get("wheelchair") == "no":
            f["wheelchair"] = 0
        try:
            cap = int(str(t.get("capacity", "")).split(";")[0])
            if 0 < cap < 2000:
                f["seats"] = cap
        except ValueError:
            pass
        if f:
            places[f"osm/{e['type']}/{e['id']}"] = f

    path = os.path.join(HERE, "..", "data", "facilities.json")
    old = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {"parking": [], "charging": []}
    parking, charging, ok = [], [], True
    for i, bb in enumerate(TILES):
        try:
            els = overpass(Q_PARK.format(bb=bb), f"parking and charging {i + 1}/4")["elements"]
        except RuntimeError as e:
            print("  ", e, "- keeping the previous parking data")
            ok = False
            break
        for e in els:
            lat = e.get("lat") or (e.get("center") or {}).get("lat")
            lng = e.get("lon") or (e.get("center") or {}).get("lon")
            if lat is None:
                continue
            (charging if e.get("tags", {}).get("amenity") == "charging_station" else parking).append([round(lat, 5), round(lng, 5)])
    if not ok:
        parking, charging = old.get("parking", []), old.get("charging", [])

    out = {"places": places, "parking": parking, "charging": charging}
    json.dump(out, open(os.path.join(HERE, "..", "data", "facilities.json"), "w", encoding="utf-8"), separators=(",", ":"))
    counts = {}
    for f in places.values():
        for k, v in f.items():
            if v and k != "seats":
                counts[k] = counts.get(k, 0) + 1
    print(f"{len(places)} places with facility tags {counts}; {len(parking)} public parking, {len(charging)} EV charging points")


if __name__ == "__main__":
    main()
