"""Static pages for search engines and link previews: one page per area
(site/areas/<slug>.html), an index of areas, sitemap.xml and robots.txt.

Called by build.py in website mode with the built rows and geo data. Each page
lists the area's places with a link straight to that place on the map."""
import html, json, os, re

ESC = html.escape


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("&", "and")).strip("-")


def place_key(name, lat, lng):
    """Same key as the page's JavaScript: djb2 over 'name|lat|lng' (4 decimals), base 36."""
    h = 5381
    for ch in f"{name}|{lat:.4f}|{lng:.4f}":
        h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while True:
        h, r = divmod(h, 36)
        out = digits[r] + out
        if h == 0:
            return out


CSS = """
:root { --bg:#f7f5f2; --panel:#fff; --ink:#241a14; --muted:#76675c; --line:#e7e0d9; --chip:#f1ece6; --cafe:#c2410c; --rest:#0f8b7d; --veg:#1e8a3c; --nonveg:#b3261e; --star:#b7791f; }
@media (prefers-color-scheme: dark) { :root { --bg:#15110e; --panel:#1d1814; --ink:#f0e7de; --muted:#a8998c; --line:#352c25; --chip:#2a231d; --cafe:#e0703a; --rest:#3fb9a8; --veg:#5cc77c; --nonveg:#f08a80; --star:#e9b44c; color-scheme: dark; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.55 "Inter", system-ui, -apple-system, "Segoe UI", sans-serif; }
.wrap { max-width: 880px; margin: 0 auto; padding-block: 28px 48px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
a { color: var(--cafe); }
.crumbs { font-size: 13px; color: var(--muted); }
h1 { font: 700 clamp(26px, 5vw, 38px)/1.1 "Bricolage Grotesque", system-ui, sans-serif; letter-spacing: -.02em; margin: 10px 0 8px; text-wrap: balance; }
h2 { font: 700 20px/1.2 "Bricolage Grotesque", system-ui, sans-serif; margin: 32px 0 10px; }
.lede { color: var(--muted); max-width: 62ch; }
.cta { display: inline-block; margin-top: 14px; background: var(--cafe); color: #fff; text-decoration: none; font-weight: 700; padding: 10px 16px; border-radius: 10px; }
.stats { display: flex; gap: 18px; flex-wrap: wrap; margin-top: 16px; font-size: 14px; }
.stats b { font-size: 20px; display: block; font-variant-numeric: tabular-nums; }
ul.places { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
ul.places li { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; }
.pn { font-weight: 700; text-decoration: none; color: var(--ink); }
.pn:hover { color: var(--cafe); }
.meta { font-size: 13px; color: var(--muted); margin-top: 2px; }
.tag { display: inline-block; font-size: 11px; font-weight: 700; padding: 1px 8px; border-radius: 99px; background: var(--chip); margin-right: 4px; }
.tag.cafe { color: var(--cafe); } .tag.rest { color: var(--rest); } .tag.veg { color: var(--veg); } .tag.nonveg { color: var(--nonveg); }
.stars { color: var(--star); font-weight: 700; }
.areas { columns: 3 200px; column-gap: 24px; padding: 0; list-style: none; }
.areas li { break-inside: avoid; padding: 3px 0; }
.areas .n { color: var(--muted); font-size: 13px; }
footer { margin-top: 40px; font-size: 12px; color: var(--muted); }
"""


def head(title, desc, url, cfg, image):
    gc = cfg.get("goatcounter") or ""
    analytics = (f'<script data-goatcounter="https://{ESC(gc)}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>'
                 if gc else "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{ESC(title)}</title>
<meta name="description" content="{ESC(desc)}">
<link rel="canonical" href="{ESC(url)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{ESC(cfg['site_name'])}">
<meta property="og:title" content="{ESC(title)}"><meta property="og:description" content="{ESC(desc)}">
<meta property="og:url" content="{ESC(url)}"><meta property="og:image" content="{ESC(image)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#c2410c">
<link rel="icon" href="../icons/icon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700&family=Inter:wght@400;600;700&display=swap">
<style>{CSS}</style>{analytics}
</head><body><div class="wrap">"""


FOOT = """<footer>Map and place data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>.
Ratings and cost for two come from the listing named on each place and can differ between sites.</footer></div></body></html>"""


def build_pages(site_dir, rows, geo, snapshot, cfg):
    base = cfg["site_url"].rstrip("/") + "/"
    image = base + "og.png"
    out = os.path.join(site_dir, "areas")
    os.makedirs(out, exist_ok=True)
    zones = [z["name"] for z in geo["zones"]]
    by_zone = {}
    for r in rows:
        by_zone.setdefault(zones[r[16]], []).append(r)
    # Groups like "Bandra" (West + East) get a page too.
    groups = {g: parts for g, parts in geo["groups"].items()}
    pages = {}
    for z, rs in by_zone.items():
        pages[z] = rs
    for g, parts in groups.items():
        if g in pages:
            continue
        rs = [r for p in parts for r in by_zone.get(p, [])]
        if rs:
            pages[g] = rs

    def li(r):
        name, rest, kind, address, lat, lng = r[0], r[1], r[2], r[3], r[4], r[5]
        cuisine = r[6].split(";") if r[6] else []
        rating, rsrc, price, diet = r[17], r[18], r[13], r[20]
        key = place_key(name, lat, lng)
        tags = [f'<span class="tag {"rest" if rest else "cafe"}">{ESC(kind)}</span>']
        if diet & 1:
            tags.append('<span class="tag veg">Pure veg</span>')
        elif diet & 4:
            tags.append('<span class="tag nonveg">Non-veg</span>')
        if diet & 2:
            tags.append('<span class="tag">Jain food</span>')
        bits = []
        if rating:
            bits.append(f'<span class="stars">★ {rating:.1f}</span> ({ESC(rsrc)})')
        if price:
            bits.append(f"≈ ₹{price:,} for two")
        if cuisine:
            bits.append(ESC(", ".join(cuisine)))
        return (f'<li><a class="pn" href="../#p-{key}">{ESC(name)}</a> {"".join(tags)}'
                f'<div class="meta">{" · ".join(bits) + " · " if bits else ""}{ESC(address)}</div></li>')

    sitemap = [base]
    index_rows = []
    for name, rs in sorted(pages.items(), key=lambda kv: kv[0]):
        s = slug(name)
        url = f"{base}areas/{s}.html"
        sitemap.append(url)
        cafes = sorted([r for r in rs if not r[1]], key=lambda r: (-(r[17] or 0), r[0].lower()))
        rests = sorted([r for r in rs if r[1]], key=lambda r: (-(r[17] or 0), r[0].lower()))
        rated = sum(1 for r in rs if r[17])
        veg = sum(1 for r in rs if r[20] & 1)
        title = f"Cafes & restaurants in {name}, Mumbai"
        desc = (f"{len(cafes)} cafes and {len(rests)} restaurants in {name}: cuisine, veg and Jain options, "
                f"ratings and cost for two where listed, menus and directions. Updated {snapshot}.")
        ld = {"@context": "https://schema.org", "@type": "ItemList", "name": title,
              "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": {
                  "@type": "CafeOrCoffeeShop" if not r[1] else "Restaurant", "name": r[0], "address": r[3],
                  "geo": {"@type": "GeoCoordinates", "latitude": r[4], "longitude": r[5]},
                  **({"servesCuisine": r[6].split(";")} if r[6] else {}),
                  "url": f"{base}#p-{place_key(r[0], r[4], r[5])}"}} for i, r in enumerate((cafes + rests)[:50])]}
        body = f"""{head(title, desc, url, cfg, image)}
<p class="crumbs"><a href="../">Map</a> › <a href="./">Areas</a> › {ESC(name)}</p>
<h1>Cafes &amp; restaurants in {ESC(name)}</h1>
<p class="lede">Every named cafe and restaurant in {ESC(name)}, Mumbai, from OpenStreetMap and current listings. Tap a place to see it on the map with directions and menu links.</p>
<div class="stats"><span><b>{len(cafes)}</b>cafes</span><span><b>{len(rests)}</b>restaurants</span><span><b>{rated}</b>with ratings</span><span><b>{veg}</b>pure veg</span></div>
<a class="cta" href="../?area={ESC(name.replace(' ', '%20').replace('&', '%26'))}">Open {ESC(name)} on the map</a>
{f'<h2>Cafes</h2><ul class="places">{"".join(li(r) for r in cafes)}</ul>' if cafes else ""}
{f'<h2>Restaurants</h2><ul class="places">{"".join(li(r) for r in rests)}</ul>' if rests else ""}
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>
{FOOT}"""
        open(os.path.join(out, f"{s}.html"), "w", encoding="utf-8").write(body)
        index_rows.append((name, s, len(rs)))

    title = "Cafes & restaurants by area, Mumbai to Thane, Kalyan and Panvel"
    desc = f"Browse {len(rows):,} cafes and restaurants across {len(index_rows)} areas, from Colaba to Mira Road, Thane, Kalyan and Panvel."
    items = "".join(f'<li><a href="{s}.html">{ESC(n)}</a> <span class="n">{c}</span></li>' for n, s, c in index_rows)
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(f"""{head(title, desc, base + 'areas/', cfg, image)}
<p class="crumbs"><a href="../">Map</a> › Areas</p>
<h1>Browse by area</h1>
<p class="lede">{ESC(desc)} Updated {ESC(snapshot)}.</p>
<a class="cta" href="../">Open the map</a>
<h2>All areas</h2><ul class="areas">{items}</ul>
{FOOT}""")
    sitemap.insert(1, base + "areas/")
    open(os.path.join(site_dir, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{ESC(u)}</loc></url>\n" for u in sitemap) + "</urlset>\n")
    open(os.path.join(site_dir, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n")
    return len(index_rows)
