"""Fetch suburban railway, metro and monorail stations in the region from
OpenStreetMap. Writes data/transit.json: [{name, type: rail|metro|mono, lat, lng, lines}].

Each station gets the lines whose track runs within 150 m of it ("Western",
"Central", "Line 1", ...), taken from the local and metro route relations."""
import json, math, os, re, sys, time, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
UA = "cafe-finder-prototype/0.1"
BB = "18.85,72.74,19.35,73.21"
MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]

# Region outline (same as build.py): Mira Road / Bhayandar to Kalyan, Panvel and Colaba.
OUTLINE = [(19.340, 72.760), (19.340, 73.100), (19.275, 73.195), (19.190, 73.195), (19.100, 73.125), (19.020, 73.150),
           (18.960, 73.150), (18.945, 73.050), (18.950, 72.980), (18.860, 72.900), (18.860, 72.760)]

Q = f"""[out:json][timeout:180];
(
  nwr["railway"~"^(station|halt)$"]({BB});
  nwr["public_transport"="station"]({BB});
);
out tags center;
"""
QR = f"""[out:json][timeout:240];
rel["type"="route"]["route"~"^(train|subway|monorail)$"]["network"~"Mumbai Suburban Railway|Mumbai Metro|Navi Mumbai Metro|Monorail"]({BB});
out geom;
"""
# Suburban stations OpenStreetMap only has as platforms, placed by hand.
EXTRA = [("Dockyard Road", "rail", 18.9663, 72.8443), ("Mansarovar", "rail", 19.0167, 73.0805),
         ("Khandeshwar", "rail", 19.0076, 73.0950)]


def overpass(q, label):
    last = None
    for attempt in range(4):
        for m in MIRRORS:
            try:
                req = urllib.request.Request(m, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": UA})
                d = json.loads(urllib.request.urlopen(req, timeout=200).read())
                if "remark" in d:
                    raise RuntimeError("incomplete: " + d["remark"][:100])
                print(f"  {label}: {len(d['elements'])} elements from {m.split('/')[2]}", flush=True)
                return d
            except Exception as e:
                last = e
                print(f"  {label}: {m.split('/')[2]} failed ({str(e)[:70]})", flush=True)
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"{label} failed: {last}")


def inside(lat, lng, poly=OUTLINE):
    res, j = False, len(poly) - 1
    for i in range(len(poly)):
        (yi, xi), (yj, xj) = poly[i], poly[j]
        if (yi > lat) != (yj > lat) and lng < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            res = not res
        j = i
    return res


def kind(t):
    s = " ".join(str(t.get(k, "")) for k in ("station", "network", "operator", "name", "subway", "monorail")).lower()
    if t.get("station") == "monorail" or t.get("monorail") == "yes" or "monorail" in s:
        return "mono"
    if t.get("station") in ("subway", "light_rail") or t.get("subway") == "yes" or "metro" in s:
        return "metro"
    if t.get("railway") in ("station", "halt") or t.get("train") == "yes" or t.get("station") == "train":
        return "rail"
    return None


def skip(t):
    name = t.get("name:en") or t.get("name") or ""
    if not name or any(k.startswith(("construction", "proposed", "disused", "abandoned")) for k in t):
        return True
    if t.get("usage") in ("freight", "industrial", "military") or re.search(r"goods|yard|depot|siding|cabin|proposed", name, re.I):
        return True
    return False


def line_label(t):
    """Short line name from a route relation: 'Western', 'Harbour', 'Line 2', 'NM Metro Line 1'..."""
    s = " ".join(str(t.get(k, "")) for k in ("name:en", "name", "ref", "network"))
    low = s.lower()
    if re.search(r"u/c|under construction|proposed|line 11\b", low):
        return None
    if re.search(r"nerul.uran", low):
        return "Nerul–Uran"
    if re.search(r"vasai.*diva|diva.*vasai", low):
        return "Vasai–Diva"
    if re.search(r"trans.?harbour", low):
        return "Trans-Harbour"
    m = re.search(r"\b(western|central|harbour)\b", low)
    if m:
        return m.group(1).title()
    if "navi mumbai metro" in low:
        m = re.search(r"\bline\s*(\d+)", low)
        return "NM Metro Line " + (m.group(1) if m else "1")
    m = re.search(r"\bline\s*(\d+[a-z]?)\b", low)
    if m:
        return "Line " + m.group(1).upper()
    if "monorail" in low:
        return "Monorail"
    return None


def near_line(lat, lng, pts, limit_km=0.15):
    kx = 111.0 * math.cos(math.radians(lat))
    for a, b in pts:
        if abs(a - lat) < 0.002 and abs(b - lng) < 0.002 and math.hypot((a - lat) * 111.0, (b - lng) * kx) <= limit_km:
            return True
    return False


def main():
    els = overpass(Q, "stations")["elements"]
    line_pts = {}
    for r in overpass(QR, "routes")["elements"]:
        lab = line_label(r.get("tags", {}))
        if not lab:
            continue
        pts = line_pts.setdefault(lab, [])
        for mem in r.get("members", []):
            geom = mem.get("geometry") or ([{"lat": mem["lat"], "lon": mem["lon"]}] if "lat" in mem else [])
            pts.extend((g["lat"], g["lon"]) for g in geom)
    print("  lines:", {k: len(v) for k, v in sorted(line_pts.items())})

    out = []
    for e in els:
        t = e.get("tags", {})
        k = kind(t)
        if not k or skip(t):
            continue
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lng = e.get("lon") or (e.get("center") or {}).get("lon")
        if lat is None or not inside(lat, lng):
            continue
        name = (t.get("name:en") or t.get("name")).strip()
        name = re.sub(r"\s*\b(railway|metro|monorail)?\s*station\b\s*$", "", name, flags=re.I).strip() or name
        out.append({"name": name, "type": k, "lat": round(lat, 5), "lng": round(lng, 5), "lines": []})
    for name, k, lat, lng in EXTRA:
        out.append({"name": name, "type": k, "lat": lat, "lng": lng, "lines": []})

    for s in out:
        if s["type"] == "mono":
            s["lines"] = ["Monorail"]
            continue
        metro = s["type"] == "metro"
        s["lines"] = sorted(lab for lab, pts in line_pts.items()
                            if lab.startswith(("Line", "NM")) == metro and near_line(s["lat"], s["lng"], pts))

    RENAME = {"Line 2": "Line 2A"}                                  # OSM's "Line 2" is the open Line 2A
    for s in out:
        s["lines"] = sorted({RENAME.get(x, x) for x in s["lines"]})
        # "Ghatkopar L1", "Dahisar (East) [Line 7]", "Panvel (Suburban)", "Jogeshwari (Harbour Line)"
        s["name"] = re.sub(r"\s*\[Line [^\]]*\]$|\s+L\d+$|\s*\((Suburban|Harbour Line|Western Line|Central Line)\)$", "", s["name"]).strip()
        if s["type"] == "rail" and not s["lines"]:
            s["lines"] = ["Long-distance terminus"] if re.search(r"terminus", s["name"], re.I) else ["Diva–Panvel"]
    # A metro "station" on no metro line is a mistag (Harbour stations, bus stops): drop it.
    out = [s for s in out if not (s["type"] == "metro" and not s["lines"])]

    # One entry per station: same name + type within 600 m (node and area, entrances).
    merged = []
    for s in sorted(out, key=lambda s: (s["type"], s["name"])):
        same = next((m for m in merged if m["type"] == s["type"] and m["name"].lower() == s["name"].lower()
                     and math.hypot((m["lat"] - s["lat"]) * 111, (m["lng"] - s["lng"]) * 105) < 0.6), None)
        if same:
            same["lines"] = sorted(set(same["lines"]) | set(s["lines"]))
        else:
            merged.append(s)
    json.dump(merged, open(os.path.join(HERE, "..", "data", "transit.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    for k in ("rail", "metro", "mono"):
        xs = [m for m in merged if m["type"] == k]
        print(f"{k}: {len(xs)} stations, {sum(1 for x in xs if x['lines'])} with lines; "
              f"no line: {[x['name'] for x in xs if not x['lines']][:25]}")


if __name__ == "__main__":
    main()
