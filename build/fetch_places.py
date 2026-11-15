"""Refresh data/places_osm.json: every named cafe and restaurant in the region
from OpenStreetMap, using the same classification as the first prototype
(legacy/server.py). Run, then  py build/build.py  to rebuild the site."""
import importlib.util, json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
spec = importlib.util.spec_from_file_location("legacy_server", os.path.join(HERE, "..", "legacy", "server.py"))
srv = importlib.util.module_from_spec(spec)
src = open(spec.origin, encoding="utf-8").read().split("if __name__ ==")[0]
exec(compile(src, spec.origin, "exec"), srv.__dict__)

b = srv.LOCATIONS["mumbai"]["bbox"]
print("downloading places for", srv.LOCATIONS["mumbai"]["name"], "...", flush=True)
data = srv.osm_tile(b["s"], b["w"], b["n"], b["e"])
before = len(json.load(open(os.path.join(DATA_DIR, "places_osm.json"), encoding="utf-8"))["places"]) \
    if os.path.exists(os.path.join(DATA_DIR, "places_osm.json")) else 0
json.dump(data, open(os.path.join(DATA_DIR, "places_osm.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(f"{len(data['places'])} places saved (was {before}). Next:  py build/build.py")
