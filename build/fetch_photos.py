"""Free-licensed photos of places from Wikimedia Commons (no copyrighted listing-site photos).

For each non-chain place, search Commons files for "<name> Mumbai" and keep a file only if:
  - every distinctive word of the place's name is in the file title, and
  - when the file is geotagged, it was taken within 1.5 km of the place;
  - it is a photo (jpg/png/webp), not a logo, map, scan or a news photo of an attack or fire.
Photos showing the inside (interior, seating, bar, counter, mural…) are listed first.

Writes data/photos.json: {placeKey: [[thumbUrl, pageUrl, author, licence, inside(0/1), title], ...]}
Credits (author, licence, link) are shown with every photo, as the licences require."""
import html, json, math, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
from make_pages import place_key  # noqa: E402

API = "https://commons.wikimedia.org/w/api.php"
UA = "cafe-finder-prototype/0.1 (open-source; github.com/nyayaai-dev/cafe_finder)"
GENERIC = set("""cafe café caffe coffee restaurant restaurants resto hotel bar and the of & house kitchen food foods
corner centre center point mumbai bombay pure veg veggie new shree shri sri sai sweet sweets snacks snack bakery
dhaba lunch home bhavan bhuvan tea stall juice fast family garden express cuisine bistro diner co company india""".split())
BAD = re.compile(r"logo|map\b|menu card|attack|terror|bullet|blast|fire|protest|\.pdf|\.djvu|\.svg|\.tif|\.gif|\.webm|\.ogv|book|almanack|scan|stamp", re.I)
INSIDE = re.compile(r"interior|inside|indoor|dining|seating|tables?\b|counter|kitchen|bar\b|jukebox|mural|ceiling|hall|lounge|chairs?\b|decor", re.I)
FREE = re.compile(r"^(cc0|cc[- ]by|public domain|pd|gfdl|attribution|no restrictions)", re.I)


def get(params, tries=4):
    params = dict(params, format="json", formatversion="2")
    url = API + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == tries - 1:
                print("  failed:", str(e)[:80])
                return {}
            time.sleep(2 * (i + 1))


def tokens(s):
    s = html.unescape(s).lower().replace("&", " ")
    s = re.sub(r"\(.*?\)", " ", s)
    return [t for t in re.findall(r"[a-z0-9]+", s)]


def distinctive(name):
    return [t for t in tokens(name) if t not in GENERIC and len(t) >= 3]


def title_ok(title, words):
    t = " ".join(tokens(title))
    squashed = t.replace(" ", "")
    return all((w in t.split()) or (w in squashed) for w in words)


def load_places():
    s = open(os.path.join(ROOT, "site", "data", "places.js"), encoding="utf-8").read()
    rows = json.loads(re.search(r"RAW = (\[.*?\]);\n", s, re.S).group(1))
    count = {}
    for r in rows:
        k = " ".join(tokens(r[0]))
        count[k] = count.get(k, 0) + 1
    out = []
    for r in rows:
        if count[" ".join(tokens(r[0]))] >= 3:          # chains: a photo of one branch would mislead
            continue
        words = distinctive(r[0])
        if not words or sum(len(w) for w in words) < 4:
            continue
        out.append({"key": place_key(r[0], r[4], r[5]), "name": r[0], "lat": r[4], "lng": r[5], "words": words})
    return out


def search(p):
    q = " ".join(p["words"]) + " Mumbai"
    d = get({"action": "query", "list": "search", "srnamespace": 6, "srlimit": 12, "srsearch": q})
    titles = [x["title"] for x in (d.get("query") or {}).get("search", [])]
    return p, [t for t in titles if not BAD.search(t) and re.search(r"\.(jpe?g|png|webp)$", t, re.I) and title_ok(t[5:], p["words"])]


def info(titles):
    d = get({"action": "query", "titles": "|".join(titles), "prop": "imageinfo|coordinates",
             "iiprop": "url|extmetadata", "iiurlwidth": 640, "iiextmetadatafilter": "Artist|LicenseShortName|ImageDescription"})
    out = {}
    for pg in (d.get("query") or {}).get("pages", []):
        ii = (pg.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "")
        artist = re.sub(r"<[^>]+>", "", html.unescape((meta.get("Artist") or {}).get("value", ""))).strip() or "Wikimedia Commons contributor"
        desc = re.sub(r"<[^>]+>", " ", html.unescape((meta.get("ImageDescription") or {}).get("value", "")))
        co = (pg.get("coordinates") or [None])[0]
        out[pg["title"]] = {"thumb": ii.get("thumburl") or ii.get("url"), "page": ii.get("descriptionurl"),
                            "artist": artist[:80], "lic": lic, "desc": desc, "coord": (co["lat"], co["lon"]) if co else None}
    return out


def main():
    places = load_places()
    print(len(places), "places to search")
    found = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        for i, (p, titles) in enumerate(ex.map(search, places)):
            if titles:
                found[p["key"]] = (p, titles[:6])
            if (i + 1) % 250 == 0:
                print(f"  {i + 1}/{len(places)} searched, {len(found)} with candidate photos", flush=True)
    all_titles = sorted({t for _, ts in found.values() for t in ts})
    meta = {}
    for i in range(0, len(all_titles), 40):
        meta.update(info(all_titles[i:i + 40]))
        time.sleep(0.3)
    photos = {}
    for key, (p, titles) in found.items():
        keep = []
        for t in titles:
            m = meta.get(t)
            if not m or not m["thumb"] or not FREE.search(m["lic"] or ""):
                continue
            if m["coord"]:
                d = math.hypot((m["coord"][0] - p["lat"]) * 111, (m["coord"][1] - p["lng"]) * 105)
                if d > 1.5:
                    continue
            inside = 1 if INSIDE.search(t) or INSIDE.search(m["desc"] or "") else 0
            keep.append([m["thumb"], m["page"], m["artist"], m["lic"], inside, re.sub(r"\.\w+$", "", t[5:])])
        keep.sort(key=lambda x: -x[4])
        if keep:
            photos[key] = keep[:4]
    json.dump(photos, open(os.path.join(ROOT, "data", "photos.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    n_in = sum(1 for v in photos.values() if any(x[4] for x in v))
    print(f"{len(photos)} places with free photos ({sum(len(v) for v in photos.values())} photos), {n_in} with an inside photo")
    for key, v in list(photos.items())[:40]:
        print("  ", next(p["name"] for p in places if p["key"] == key), "->", [x[5][:45] + (" [inside]" if x[4] else "") for x in v])


if __name__ == "__main__":
    main()
