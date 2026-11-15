"""Draw the app icon (coffee cup on a map pin colour) as PNG and SVG, with no
image libraries: a tiny anti-aliased rasteriser and PNG writer.

    py build/make_icons.py   ->  site/icons/icon-192.png, icon-512.png, icon.svg"""
import math, os, struct, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "site", "icons")
BG = (194, 65, 12)       # pin orange, matches --pin-cafe
FG = (255, 255, 255)

# Shapes in a 0..1 square (cup body, handle ring, saucer, steam), maskable-safe (inside the centre 80%).


def inside(x, y):
    # cup body: rounded-bottom rectangle
    if 0.27 <= x <= 0.63 and 0.40 <= y <= 0.62:
        return True
    if 0.27 <= x <= 0.63 and 0.62 < y <= 0.70:
        cx, r = 0.45, 0.18
        if (x - cx) ** 2 / r ** 2 + (y - 0.62) ** 2 / 0.08 ** 2 <= 1:
            return True
    # handle: ring on the right
    d = math.hypot(x - 0.665, y - 0.515)
    if 0.045 <= d <= 0.085 and x > 0.63:
        return True
    # saucer
    if 0.22 <= x <= 0.68 and 0.73 <= y <= 0.765:
        return True
    # steam: three short wavy strokes
    for sx in (0.36, 0.45, 0.54):
        if 0.22 <= y <= 0.35:
            wx = sx + 0.018 * math.sin((y - 0.22) * 40)
            if abs(x - wx) <= 0.014:
                return True
    return False


def rounded_bg(x, y, r=0.22):
    # full-bleed square for maskable icons; rounded only in the SVG
    return True


def render(size, ss=3):
    rows = []
    for py in range(size):
        row = bytearray([0])
        for px in range(size):
            hits = 0
            for sy in range(ss):
                for sx in range(ss):
                    x = (px + (sx + 0.5) / ss) / size
                    y = (py + (sy + 0.5) / ss) / size
                    hits += inside(x, y)
            a = hits / (ss * ss)
            row += bytes(round(BG[i] * (1 - a) + FG[i] * a) for i in range(3)) + b"\xff"
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<rect width="100" height="100" rx="22" fill="#c2410c"/>
<g fill="#fff"><path d="M27 40h36v22a18 8 0 0 1-36 0z"/><rect x="22" y="73" width="46" height="3.5" rx="1.75"/></g>
<circle cx="66.5" cy="51.5" r="6.5" fill="none" stroke="#fff" stroke-width="4"/>
<g fill="none" stroke="#fff" stroke-width="2.8" stroke-linecap="round"><path d="M36 22c2 3-2 6 0 10M45 22c2 3-2 6 0 10M54 22c2 3-2 6 0 10"/></g>
</svg>
"""

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for size in (192, 512):
        open(os.path.join(OUT, f"icon-{size}.png"), "wb").write(render(size, 3 if size == 192 else 2))
    open(os.path.join(OUT, "icon.svg"), "w", encoding="utf-8").write(SVG)
    print("icons written to", os.path.normpath(OUT))
