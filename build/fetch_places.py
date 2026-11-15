"""Refresh data/places_osm.json: every named cafe and restaurant in the region
from OpenStreetMap, using the same classification as the first prototype
(legacy/server.py). Run, then  py build/build.py  to rebuild the site.

Refuses to save (exit code 2) when the new download has under 90% of the
places the current file has: that usually means the map server sent back a
cut-short answer, and saving it would silently drop real places."""
import datetime, importlib.util, json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
TARGET = os.path.join(DATA_DIR, "places_osm.json")

spec = importlib.util.spec_from_file_location("legacy_server", os.path.join(HERE, "..", "legacy", "server.py"))
srv = importlib.util.module_from_spec(spec)
src = open(spec.origin, encoding="utf-8").read().split("if __name__ ==")[0]
exec(compile(src, spec.origin, "exec"), srv.__dict__)

b = srv.LOCATIONS["mumbai"]["bbox"]
print("downloading places for", srv.LOCATIONS["mumbai"]["name"], "...", flush=True)
data = srv.osm_tile(b["s"], b["w"], b["n"], b["e"])
before = len(json.load(open(TARGET, encoding="utf-8"))["places"]) if os.path.exists(TARGET) else 0
after = len(data["places"])
if before and after < 0.9 * before:
    print(f"refusing to save: only {after} places, the current file has {before}")
    sys.exit(2)

today = datetime.date.today()
data["fetched"] = today.isoformat()
data["fetched_label"] = f"{today.day} {today.strftime('%B %Y')}"
json.dump(data, open(TARGET, "w", encoding="utf-8"), ensure_ascii=False)
print(f"{after} places saved (was {before}). Next:  py build/build.py")
