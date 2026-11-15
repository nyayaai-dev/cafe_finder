"""Run the website locally the way Vercel serves it: static files from site/
and the /api/place function from api/place.py.

    py dev_server.py          ->  http://127.0.0.1:8780

Put GOOGLE_MAPS_API_KEY in a .env file next to this script to try live
Google details locally (the same variable you set on Vercel).
"""
import importlib.util
import json
import os
import sys
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
PORT = int(os.environ.get("PORT", "8780"))

env = os.path.join(ROOT, ".env")
if os.path.exists(env):
    for line in open(env, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

spec = importlib.util.spec_from_file_location("place", os.path.join(ROOT, "api", "place.py"))
place = importlib.util.module_from_spec(spec)
spec.loader.exec_module(place)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=SITE, **kw)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s\n" % (fmt % args))

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path.rstrip("/") == "/api/place":
            q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
            status, payload, _ = place.respond(q)
            raw = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        super().do_GET()


if __name__ == "__main__":
    if not os.path.exists(os.path.join(SITE, "index.html")):
        sys.exit("site/ is empty: run  py build/build.py  first")
    print(f"Cafe Finder on http://127.0.0.1:{PORT}  (Google lookups: {'on' if place.key() else 'off, no key'})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
