"""Download detailed OpenStreetMap layers for the map (raw, saved per layer
under raw/ so processing can be re-run without downloading again)."""
import json, os, sys, time, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")   # inputs and generated data
RAW = os.path.join(HERE, "raw")
os.makedirs(RAW, exist_ok=True)
UA = "cafe-finder-prototype/0.1"
MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
S, W, N, E = 18.84, 72.72, 19.36, 73.22
BB = f"{S},{W},{N},{E}"


def overpass(q, label):
    last = None
    for attempt in range(6):
        for m in MIRRORS:
            try:
                req = urllib.request.Request(m, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": UA})
                d = json.loads(urllib.request.urlopen(req, timeout=300).read())
                if "remark" in d:
                    raise RuntimeError("incomplete: " + d["remark"][:90])
                print(f"  {label}: {len(d['elements'])} elements ({m.split('/')[2]})", flush=True)
                return d
            except Exception as e:
                last = e
                print(f"  {label}: {m.split('/')[2]} failed ({str(e)[:60]})", flush=True)
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"{label}: {last}")


def save(name, q):
    path = os.path.join(RAW, name + ".json")
    if os.path.exists(path):
        print(f"  {name}: cached")
        return
    d = overpass(q, name)
    json.dump(d["elements"], open(path, "w", encoding="utf-8"))


H = "[out:json][timeout:280];"
save("coast", H + f'way["natural"="coastline"]({BB});out geom;')
save("water", H + f'(way["natural"="water"]({BB});rel["natural"="water"]({BB});'
                  f'way["waterway"="riverbank"]({BB});rel["waterway"="riverbank"]({BB}););out geom;')
save("green", H + f'(way["leisure"~"^(park|garden|golf_course|nature_reserve)$"]({BB});'
                  f'rel["leisure"~"^(park|garden|nature_reserve)$"]({BB});'
                  f'way["landuse"~"^(forest|grass|recreation_ground|meadow|village_green|cemetery)$"]({BB});'
                  f'rel["landuse"~"^(forest|grass|recreation_ground)$"]({BB});'
                  f'way["natural"~"^(wood|scrub|grassland)$"]({BB});rel["natural"~"^(wood|scrub)$"]({BB});'
                  f'rel["boundary"="national_park"]({BB}););out geom;')
save("wetland", H + f'(way["natural"="wetland"]({BB});rel["natural"="wetland"]({BB}););out geom;')
save("roads_major", H + f'way["highway"~"^(motorway|trunk|primary|secondary|tertiary)(_link)?$"]({BB});out geom tags;')
save("rail", H + f'way["railway"~"^(rail|subway|light_rail|monorail)$"]["service"!~"."]({BB});out geom tags;')
# Minor streets are the bulk of the data: fetch in tiles.
rows, cols = 3, 3
for i in range(rows):
    for j in range(cols):
        s = S + (N - S) * i / rows; n = S + (N - S) * (i + 1) / rows
        w = W + (E - W) * j / cols; e = W + (E - W) * (j + 1) / cols
        save(f"roads_minor_{i}{j}", H + f'way["highway"~"^(residential|unclassified|living_street|pedestrian)$"]({s},{w},{n},{e});out geom;')
print("done")
