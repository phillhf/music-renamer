"""Erzeugt installer/app.ico (Musiknote mit Lupe) ohne externe Bibliotheken.

Ausfuehren:  python installer/make_icon.py
Die Formen werden als Abstandsfunktionen beschrieben und mit 4x4-Supersampling gerastert,
dadurch sind die Kanten in jeder Groesse glatt.
"""
import math
import os
import struct
import zlib

SIZES = (16, 24, 32, 48, 64, 128, 256)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.ico")


def hexcol(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def rrect(cx, cy, hw, hh, r):
    def d(x, y):
        qx, qy = abs(x - cx) - hw + r, abs(y - cy) - hh + r
        return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r
    return d


def ring(cx, cy, radius, width):
    return lambda x, y: abs(math.hypot(x - cx, y - cy) - radius) - width / 2


def disc(cx, cy, radius):
    return lambda x, y: math.hypot(x - cx, y - cy) - radius


def ellipse(cx, cy, rx, ry, angle):
    c, s = math.cos(angle), math.sin(angle)

    def d(x, y):
        dx, dy = x - cx, y - cy
        u, v = (dx * c + dy * s) / rx, (-dx * s + dy * c) / ry
        return (math.hypot(u, v) - 1) * min(rx, ry)
    return d


def segment(ax, ay, bx, by, width):
    def d(x, y):
        px, py, vx, vy = x - ax, y - ay, bx - ax, by - ay
        t = max(0.0, min(1.0, (px * vx + py * vy) / (vx * vx + vy * vy)))
        return math.hypot(px - vx * t, py - vy * t) - width / 2
    return d


OUTLINE = hexcol("#1e2433")
WHITE = hexcol("#ffffff")
lens = (0.71, 0.71)
# Ebenen von hinten nach vorne: (Form, Farbe)
LAYERS = [
    (rrect(0.46, 0.46, 0.42, 0.42, 0.10), hexcol("#2f6fe4")),
    (rrect(0.46, 0.46, 0.39, 0.39, 0.08), hexcol("#3b82f6")),
    (ellipse(0.27, 0.62, 0.105, 0.08, -0.35), WHITE),                     # Notenkoepfe
    (ellipse(0.57, 0.54, 0.105, 0.08, -0.35), WHITE),
    (segment(0.355, 0.60, 0.355, 0.20, 0.05), WHITE),                     # Haelse
    (segment(0.655, 0.52, 0.655, 0.13, 0.05), WHITE),
    (segment(0.355, 0.235, 0.655, 0.165, 0.10), WHITE),                   # Balken
    (segment(0.83, 0.83, 0.95, 0.95, 0.12), OUTLINE),                     # Lupengriff
    (segment(0.84, 0.84, 0.94, 0.94, 0.07), hexcol("#4b5563")),
    (disc(*lens, 0.20), OUTLINE),
    (disc(*lens, 0.16), hexcol("#dbeafe", 0.70)),                         # Glas
    (ring(*lens, 0.165, 0.055), hexcol("#f59e0b")),                       # Lupenring
    (ring(*lens, 0.165, 0.015), hexcol("#fbbf24")),
]


def render(size):
    ss = 4
    rows = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            acc = [0.0, 0.0, 0.0, 0.0]
            for sy in range(ss):
                for sx in range(ss):
                    x = (px + (sx + 0.5) / ss) / size
                    y = (py + (sy + 0.5) / ss) / size
                    r = g = b = a = 0.0
                    for shape, (cr, cg, cb, ca) in LAYERS:
                        if shape(x, y) <= 0:
                            # "source over" mit vormultipliziertem Alpha
                            r, g, b, a = cr * ca + r * (1 - ca), cg * ca + g * (1 - ca), cb * ca + b * (1 - ca), ca + a * (1 - ca)
                    acc[0] += r; acc[1] += g; acc[2] += b; acc[3] += a
            n = ss * ss
            a = acc[3] / n
            if a > 0:
                row += bytes((round(acc[0] / n / a * 255), round(acc[1] / n / a * 255),
                              round(acc[2] / n / a * 255), round(a * 255)))
            else:
                row += b"\0\0\0\0"
        rows.append(bytes(row))
    return rows


def png(size, rows):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\0" + r for r in rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main():
    images = [(s, png(s, render(s))) for s in SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, data = b"", b""
    for s, img in images:
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(img), offset + len(data))
        data += img
    with open(OUT, "wb") as f:
        f.write(header + entries + data)
    # Vorschau fuer die Doku
    with open(os.path.join(os.path.dirname(OUT), "app_256.png"), "wb") as f:
        f.write(images[-1][1])
    # macOS: eigenes Containerformat, die Bilder bleiben PNG
    entries = b""
    for kind, size in ((b"ic07", 128), (b"ic08", 256), (b"ic09", 512)):
        img = png(size, render(size))
        entries += kind + struct.pack(">I", len(img) + 8) + img
    with open(OUT.replace(".ico", ".icns"), "wb") as f:
        f.write(b"icns" + struct.pack(">I", len(entries) + 8) + entries)
    print(f"{OUT} geschrieben ({len(images)} Groessen)")


if __name__ == "__main__":
    main()
