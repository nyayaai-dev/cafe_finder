"""Build the Cafe Finder website from data/.

    py build/build.py                      -> site/ (index.html + data files), what Vercel serves
    py build/build.py --single page.html   -> one self-contained HTML file (shareable artifact)

Places snapshot + web-listed cafes, every place tagged with its locality and
suburb, the region outline, the OpenStreetMap-style base map and Leaflet CSS."""
import json, math, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")   # inputs and generated data
SITE_DIR = os.path.join(HERE, "..", "site")
SINGLE = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--single" else None

# Colaba to Mira Road, Thane, Bhiwandi, Kalyan-Dombivli and Navi Mumbai to Panvel.
OUTLINE = [
    (19.340, 72.760), (19.340, 73.100), (19.275, 73.195), (19.190, 73.195),
    (19.100, 73.125), (19.020, 73.150), (18.960, 73.150), (18.945, 73.050),
    (18.950, 72.980), (18.860, 72.900), (18.860, 72.760),
]


def diet_bits(d):
    d = d or {}
    return (1 if d.get("pureVeg") else 0) | (2 if d.get("jain") else 0) | (4 if d.get("nonVeg") else 0) | (8 if d.get("vegOptions") else 0)


def inside(lat, lng, poly=OUTLINE):
    res, j = False, len(poly) - 1
    for i in range(len(poly)):
        yi, xi = poly[i]; yj, xj = poly[j]
        if (xi > lng) != (xj > lng) and lat < (yj - yi) * (lng - xi) / (xj - xi) + yi:
            res = not res
        j = i
    return res


# ---------------------------------------------------------------- places
src = os.path.join(DATA_DIR, "places_osm.json")
data = json.load(open(src, encoding="utf-8"))
assert data["places"] and "category" in data["places"][0], "places_osm.json is not categorised data"

items, seen = [], set()
for p in data["places"]:
    key = (p["name"].lower(), round(p["lat"], 4), round(p["lng"], 4))
    if key in seen or not inside(p["lat"], p["lng"]):
        continue
    seen.add(key)
    items.append(dict(id=p["id"], name=p["name"], rest=1 if p["category"] == "restaurant" else 0, kind=p["kind"],
                      street=p.get("address") or "", lat=p["lat"], lng=p["lng"],
                      cuisine=";".join(p.get("cuisine") or []), hours=p.get("hours") or "",
                      phone=p.get("phone") or "", website=p.get("website") or "", menu=p.get("menu") or "",
                      src="", srcUrl="", priceTwo=0, rating=0, ratingSrc="", priceSrc="",
                      diet=diet_bits(p.get("diet")), web=0))

# Cafes named by current web listings but missing from OpenStreetMap.
web = json.load(open(os.path.join(DATA_DIR, "web_additions.json"), encoding="utf-8"))
MANUAL = {"Blue Tokai Coffee Roasters (IC Colony)": (19.2450, 72.8500)}
used = {}
for w in web:
    lat, lng = MANUAL.get(w["name"], (w["lat"], w["lng"]))
    k = (round(lat, 4), round(lng, 4)); n = used.get(k, 0); used[k] = n + 1
    lat += 0.00045 * (n % 3) - 0.00045; lng += 0.00045 * (n // 3)   # keep stacked pins clickable
    items.append(dict(id="", name=w["name"], rest=0, kind=w["kind"], street=w["address"], lat=lat, lng=lng, cuisine="",
                      hours="", phone="", website="", menu="", src=w["src"], srcUrl=w["srcUrl"], priceTwo=w["priceTwo"] or 0,
                      rating=0, ratingSrc="", priceSrc=w["src"] if w["priceTwo"] else "", diet=0, web=1))

# Hotspot listings: attach rating / cost for two to map places, add the missing ones.
hot = json.load(open(os.path.join(DATA_DIR, "hotspots_resolved.json"), encoding="utf-8"))
by_id = {it["id"]: it for it in items if it["id"]}
added = enriched = 0
for h in hot:
    src_name = h["ratingSrc"] or h["priceSrc"] or "listing"
    extra = dict(rating=h["rating"] or 0, ratingSrc=h["ratingSrc"] or "", priceTwo=h["priceTwo"] or 0,
                 priceSrc=h["priceSrc"] or "", srcUrl=h["srcUrl"], src=src_name)
    if h.get("matchId") in by_id:
        it = by_id[h["matchId"]]
        it.update(extra)
        if h["pureVeg"]:
            it["diet"] |= 1
        enriched += 1
    elif h["lat"] is not None and inside(h["lat"], h["lng"]):
        k = (round(h["lat"], 4), round(h["lng"], 4)); n = used.get(k, 0); used[k] = n + 1
        lat = h["lat"] + 0.00045 * (n % 3) - 0.00045; lng = h["lng"] + 0.00045 * (n // 3)
        items.append(dict(id="", name=h["name"], rest=1 if h["kind"] == "rest" else 0,
                          kind="Cafe" if h["kind"] == "cafe" else "Restaurant", street=h["loc"], lat=lat, lng=lng,
                          cuisine="", hours="", phone="", website="", menu="", diet=1 if h["pureVeg"] else 0, web=1, **extra))
        added += 1
print(f"hotspots: {enriched} map places given ratings/cost, {added} added from listings")

# ---------------------------------------------------------------- localities
region = json.load(open(os.path.join(DATA_DIR, "region.json"), encoding="utf-8"))


def clean(n):
    n = re.sub(r"\s*\[[^\]]*\]$", "", n.strip())                       # "[Line 7]"
    n = re.sub(r"\s*\((?:harbour|western|central|trans[- ]harbour)\s+line\)$", "", n, flags=re.I)
    n = re.sub(r"\s*\((?:chembur|mumbai|thane)\)$", "", n, flags=re.I)
    n = {"Mira": "Mira Road"}.get(n, n)
    n = re.sub(r"\s*\((?:mumbai|navi mumbai|thane)\)$", "", n.strip(), flags=re.I)
    n = re.sub(r"\s+(railway\s+)?station$", "", n, flags=re.I)
    n = re.sub(r"\s+(metro|monorail)$", "", n, flags=re.I)
    n = re.sub(r"\s*\((?:west|w)\)$", " West", n, flags=re.I)
    n = re.sub(r"\s*\((?:east|e)\)$", " East", n, flags=re.I)
    return n.strip()


SUB_PLACES = {"town", "suburb", "city"}   # "city" brings in Panvel; Mumbai itself is skipped by name
suburbs, locs = {}, {}
for l in region["localities"]:
    if not inside(l["lat"], l["lng"]):
        continue
    name = clean(l["name"])
    if not name or not re.search(r"[A-Za-z]", name) or name.lower() in ("mumbai", "navi mumbai", "bombay", "thane", "mira-bhayandar", "mira-bhayander", "mira bhayander"):
        continue
    key = re.sub(r"[^a-z]", "", name.lower())   # "Lal Baug" and "Lalbaug" are one place
    target = suburbs if l["place"] in SUB_PLACES else locs
    # Prefer a rail station's position over metro/monorail for the same name.
    rank = 0 if l["station"] and not (l["subway"] or l["mono"]) else 1
    if key not in target or rank < target[key]["rank"]:
        target[key] = {"name": name, "lat": l["lat"], "lng": l["lng"], "rank": rank}

# Western suburbs split West / East of the railway, centres 1.3 km either side of the station.
SPLIT = {"Malad": (19.1868, 72.8486), "Kandivali": (19.2043, 72.8517), "Borivali": (19.2290, 72.8573),
         "Dahisar": (19.2502, 72.8594), "Goregaon": (19.1649, 72.8495), "Jogeshwari": (19.1360, 72.8487),
         "Andheri": (19.1197, 72.8464), "Vile Parle": (19.0997, 72.8436), "Santacruz": (19.0818, 72.8414),
         "Bandra": (19.0544, 72.8406), "Khar": (19.0690, 72.8400)}
for base, (lat, lng) in SPLIT.items():
    k = re.sub(r"[^a-z]", "", base.lower())
    for side in ("", "west", "east", "w", "e"):
        suburbs.pop(k + side, None)
    suburbs[k + "west"] = {"name": f"{base} West", "lat": lat, "lng": lng - 0.013, "rank": 0}
    suburbs[k + "east"] = {"name": f"{base} East", "lat": lat, "lng": lng + 0.013, "rank": 0}
    locs.setdefault(k, {"name": base, "lat": lat, "lng": lng, "rank": 0})

# Every suburb centre also counts as a locality.
for k, s in suburbs.items():
    locs.setdefault(k, dict(s))

SUBS = sorted(suburbs.values(), key=lambda s: s["name"])
LOCS = sorted(locs.values(), key=lambda s: s["name"])
COS = math.cos(math.radians(19.1))


def nearest(lat, lng, pts):
    best, bd = 0, 1e9
    for i, a in enumerate(pts):
        d = (lat - a["lat"]) ** 2 + ((lng - a["lng"]) * COS) ** 2
        if d < bd:
            best, bd = i, d
    return best, math.sqrt(bd) * 111.0   # km


# Main areas: the hand-checked Mumbai list (west/east split where the railway
# divides a suburb) plus the Navi Mumbai, Mira-Bhayandar and Panvel nodes.
old = json.load(open(os.path.join(DATA_DIR, "geo.json"), encoding="utf-8"))["areas"]
FIXZ = {"Prabhadevi": (19.0166, 72.8295), "Dahisar": (19.2502, 72.8594), "Bandra Kurla Complex": (19.0660, 72.8680)}
ZONES = {}
for a in old:
    lat, lng = FIXZ.get(a["name"], (a["lat"], a["lng"]))
    base = re.sub(r"\s+(west|east)$", "", a["name"], flags=re.I)
    if base in SPLIT or a["name"] in ("Versova",):
        continue
    ZONES[a["name"]] = (lat, lng)
for base, (lat, lng) in SPLIT.items():
    ZONES[f"{base} West"] = (lat, lng - 0.013)
    ZONES[f"{base} East"] = (lat, lng + 0.013)
for s in SUBS:
    if s["lng"] > 72.95 or s["lat"] > 19.265 or "panvel" in s["name"].lower():
        ZONES.setdefault(s["name"], (s["lat"], s["lng"]))
for n, ll in {"Mulund West": (19.1726, 72.9425), "Mulund East": (19.1700, 72.9640), "Wadala": (19.0170, 72.8580),
              "Sewri": (19.0000, 72.8570), "Parel": (19.0030, 72.8400), "Kurla": (19.0650, 72.8790),
              "Mahalaxmi": (18.9830, 72.8240), "Marine Drive": (18.9440, 72.8230), "Nariman Point": (18.9256, 72.8242), "Kala Ghoda": (18.9285, 72.8320),
              "Cuffe Parade": (18.9120, 72.8190)}.items():
    ZONES.setdefault(n, ll)
ZLIST = [{"name": n, "lat": ll[0], "lng": ll[1]} for n, ll in sorted(ZONES.items())]

rows = []
for it in items:
    si, _ = nearest(it["lat"], it["lng"], SUBS)
    zi, _ = nearest(it["lat"], it["lng"], ZLIST)
    li, dkm = nearest(it["lat"], it["lng"], LOCS)
    sub, loc = SUBS[si]["name"], LOCS[li]["name"]
    near = loc if loc.lower() == sub.lower() or sub.lower().startswith(loc.lower()) else f"{loc}, {sub}"
    # Every place gets an address: its own street address where mapped, plus the locality.
    street = it["street"]
    if street and (loc.lower() in street.lower() or sub.lower() in street.lower()):
        address = street
    elif street:
        address = f"{street}, {near}"
    else:
        address = f"Near {near}" if dkm > 0.35 else near
    rows.append([it["name"], it["rest"], it["kind"], address, round(it["lat"], 5), round(it["lng"], 5),
                 it["cuisine"], it["hours"], it["phone"], it["website"], it["menu"],
                 it["src"], it["srcUrl"], it["priceTwo"], si, li, zi,
                 it["rating"], it["ratingSrc"], it["priceSrc"], it["diet"], it["web"]])
rows.sort(key=lambda r: (r[4], r[5]))

# Groups: West + East together, the north-west strip, Navi Mumbai and Mira-Bhayandar.
groups = {}
for base in SPLIT:
    groups[base] = [f"{base} West", f"{base} East"]
groups["Malad to Dahisar"] = [f"{b} {s}" for b in ("Malad", "Kandivali", "Borivali", "Dahisar") for s in ("West", "East")]
groups["Navi Mumbai"] = [z["name"] for z in ZLIST if z["lng"] > 72.985 and (z["lat"] < 19.175 or z["name"] == "Digha")]
groups["Mira Road & Bhayandar"] = [z["name"] for z in ZLIST if z["lat"] > 19.265 and z["lng"] < 72.92]
groups["Thane"] = [z["name"] for z in ZLIST if 72.95 < z["lng"] < 73.06 and 19.175 <= z["lat"] < 19.30 and z["name"] != "Digha"]
groups["Kalyan & Dombivli"] = [z["name"] for z in ZLIST if z["lng"] >= 73.06 and 19.15 <= z["lat"] < 19.275]
groups["Bhiwandi"] = [z["name"] for z in ZLIST if z["lat"] >= 19.27 and z["lng"] >= 72.98]
groups = {k: v for k, v in groups.items() if v}

geo = {}  # base map now comes from map_base.json
geo["lakes"] = []
geo["suburbs"] = [{"name": s["name"], "lat": round(s["lat"], 4), "lng": round(s["lng"], 4)} for s in SUBS]
geo["locs"] = [{"name": s["name"], "lat": round(s["lat"], 4), "lng": round(s["lng"], 4)} for s in LOCS]
geo["groups"] = groups
geo["zones"] = [{"name": z["name"], "lat": round(z["lat"], 4), "lng": round(z["lng"], 4)} for z in ZLIST]
geo["outline"] = OUTLINE

vendor = "\n".join(open(os.path.join(HERE, "vendor", n), encoding="utf-8").read()
                   for n in ("leaflet.css", "MarkerCluster.css", "MarkerCluster.Default.css"))
vendor = re.sub(r"url\(images/[^)]*\)", "none", vendor)


def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


SNAPSHOT = data.get("fetched_label") or "15 November 2026"
mapbase = open(os.path.join(DATA_DIR, "map_base.json"), encoding="utf-8").read()
streets = open(os.path.join(DATA_DIR, "map_minor.json"), encoding="utf-8").read()
html = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
parts = os.path.join(HERE, "parts")
html = (html.replace("/*__VENDOR_CSS__*/", vendor)
            .replace("/*__FEATURES_CSS__*/", open(os.path.join(parts, "features.css"), encoding="utf-8").read())
            .replace("/*__FEATURES_JS__*/", open(os.path.join(parts, "features.js"), encoding="utf-8").read())
            .replace("__SNAPSHOT__", SNAPSHOT))
start, end = html.index("<!--DATA-->"), html.index("<!--/DATA-->") + len("<!--/DATA-->")

if SINGLE:
    # Everything inline: the shareable page can't load other files.
    block = ('<script type="application/json" id="minor-streets">' + streets.replace("</", "<\\/") + "</script>\n"
             "<script>\nconst SITE_MODE = false;\nconst RAW = " + js(rows) + ";\nconst GEO = " + js(geo) + ";\nconst MAPD = " + mapbase + ";\n</script>")
    OUT = SINGLE
    page = html[:start] + block + html[end:]
    open(OUT, "w", encoding="utf-8").write(page.replace("<!--PWA-->", ""))
else:
    # Website: data in separate, cacheable files; streets load on first zoom-in.
    os.makedirs(os.path.join(SITE_DIR, "data"), exist_ok=True)
    open(os.path.join(SITE_DIR, "data", "places.js"), "w", encoding="utf-8").write(
        "const RAW = " + js(rows) + ";\nconst GEO = " + js(geo) + ";\n")
    open(os.path.join(SITE_DIR, "data", "basemap.js"), "w", encoding="utf-8").write("const MAPD = " + mapbase + ";\n")
    open(os.path.join(SITE_DIR, "data", "streets.json"), "w", encoding="utf-8").write(streets)
    block = '<script>const SITE_MODE = true;</script>\n<script src="data/places.js"></script>\n<script src="data/basemap.js"></script>'
    OUT = os.path.join(SITE_DIR, "index.html")

    # Installable app: manifest, icons and an offline cache (service worker).
    import hashlib, subprocess
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "make_icons.py")], check=True, stdout=subprocess.DEVNULL)
    version = hashlib.sha1((js(rows) + mapbase[:5000] + html).encode()).hexdigest()[:10]
    manifest = {
        "name": "Mumbai Cafe & Restaurant Finder", "short_name": "Cafe Finder",
        "description": "Every cafe and restaurant from Colaba to Thane, Kalyan and Panvel on one map.",
        "start_url": "./", "scope": "./", "display": "standalone",
        "background_color": "#f7f5f2", "theme_color": "#c2410c",
        "icons": [
            {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            {"src": "icons/icon.svg", "sizes": "any", "type": "image/svg+xml"},
        ],
    }
    json.dump(manifest, open(os.path.join(SITE_DIR, "manifest.webmanifest"), "w", encoding="utf-8"), indent=1)
    sw = open(os.path.join(HERE, "sw.template.js"), encoding="utf-8").read().replace("__VERSION__", version)
    open(os.path.join(SITE_DIR, "sw.js"), "w", encoding="utf-8").write(sw)
    cfg = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
    base_url = cfg["site_url"].rstrip("/") + "/"
    share_desc = (f"Find {len(rows):,} cafes and restaurants from Colaba to Mira Road, Thane, Kalyan and Panvel: "
                  "areas, cuisine, veg and Jain filters, ratings, cost for two, menus and directions.")
    gc = (cfg.get("goatcounter") or "").strip()
    pwa = ('<meta property="og:type" content="website">\n'
           f'<meta property="og:site_name" content="{cfg["site_name"]}">\n'
           f'<meta property="og:title" content="{cfg["site_name"]}">\n'
           f'<meta property="og:description" content="{share_desc}">\n'
           f'<meta property="og:url" content="{base_url}">\n'
           f'<meta property="og:image" content="{base_url}og.png">\n'
           '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">\n'
           '<meta name="twitter:card" content="summary_large_image">\n'
           f'<link rel="canonical" href="{base_url}">\n'
           '<link rel="preload" href="data/places.js" as="script">\n'
           + (f'<script data-goatcounter="https://{gc}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>\n' if gc else "")
           + '<link rel="manifest" href="manifest.webmanifest">\n'
           '<meta name="theme-color" content="#c2410c">\n'
           '<link rel="icon" href="icons/icon.svg" type="image/svg+xml">\n'
           '<link rel="apple-touch-icon" href="icons/icon-192.png">\n'
           '<meta name="apple-mobile-web-app-capable" content="yes">\n'
           f'<meta name="description" content="{share_desc}">\n'
           "<script>if ('serviceWorker' in navigator && window.isSecureContext) "
           "addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));</script>")
    # A real document shell: standards mode and a mobile viewport (the claude.ai page adds these itself).
    shell = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
             '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
    page = (html[:start] + block + html[end:]).replace("<!--PWA-->", pwa).replace('<meta charset="utf-8">\n', "", 1)
    open(OUT, "w", encoding="utf-8").write(shell + page + "\n</html>\n")

    # Area pages, sitemap and robots.txt for search engines; og.png is drawn on Windows by make_og.ps1.
    sys.path.insert(0, HERE)
    import make_pages
    n_pages = make_pages.build_pages(SITE_DIR, rows, geo, SNAPSHOT, cfg)
    print(f"{n_pages} area pages written")
print(f"{len(rows)} places ({sum(r[21] for r in rows)} from web listings, {sum(1 for r in rows if r[17])} with ratings, {sum(1 for r in rows if r[13])} with cost for two, {sum(1 for r in rows if r[20] & 1)} pure veg, {sum(1 for r in rows if r[20] & 2)} jain, {sum(1 for r in rows if r[20] & 4)} non-veg) from {os.path.basename(src)}; "
      f"{len(ZLIST)} main areas, {len(SUBS)} neighbourhoods, {len(LOCS)} localities; groups: { {k: len(v) for k, v in groups.items()} }; "
      f"{os.path.getsize(OUT)/1024:.0f} KB")
