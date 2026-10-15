#!/usr/bin/env python3
"""Turn the flat red-square Haywood logo into clean, scalable site assets.

How it works
------------
The source (225x225 PNG) is pure-white artwork on a pure-red field (#d60000,
green channel 0). Every pixel is therefore a linear blend of white and red, so
`green / 255` *is* the coverage of the artwork -- an exact, halo-free matte.
Measured: re-compositing the extracted alpha over flat red reproduces the source
with a mean per-channel delta of 0.35/255.

The matte is then traced to a vector path (cv2 findContours + Douglas-Peucker),
so every PNG is rendered from geometry rather than upscaled pixels -- crisp at
16px and at 1024px alike.
"""
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC = Path("/home/user/uploads/pasted-image.png")
OUT = Path("/home/user/assets")
OUT.mkdir(exist_ok=True)

RED = (214, 0, 0)
RED_HEX = "#d60000"
INK_HEX = "#0d0d0f"
GRID = 1000  # vector coordinate space

# --- 1. matte ------------------------------------------------------------------
im = Image.open(SRC).convert("RGB")
arr = np.asarray(im).astype(np.float64)
alpha = np.clip(arr[..., 1] / 255.0, 0.0, 1.0)
over = 255.0 * alpha[..., None] + (1.0 - alpha[..., None]) * np.array(RED, dtype=np.float64)
print(f"source {im.size[0]}x{im.size[1]}   matte: mean delta "
      f"{np.abs(over - arr).mean():.2f}/255, p99 {np.percentile(np.abs(over - arr), 99):.1f}")

mask = (alpha > 0.5).astype(np.uint8)
ys, xs = np.where(mask)
top, bottom, left, right = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
print(f"glyph bbox: x {left}..{right}  y {top}..{bottom}  "
      f"({right-left}x{bottom-top} of {im.size[0]}x{im.size[1]})")
# square frame with even margins, so the mark centres itself anywhere
gw, gh = right - left, bottom - top
side = max(gw, gh)
pad = int(round(side * 0.06))
frame = side + 2 * pad
ox = left - (frame - gw) // 2
oy = top - (frame - gh) // 2
sub = alpha[oy:oy + frame, ox:ox + frame]
print(f"square frame: {frame}x{frame} at offset ({ox},{oy})")

# --- 2. trace to vector --------------------------------------------------------
submask = (sub > 0.5).astype(np.uint8) * 255
found, _ = cv2.findContours(submask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
diag = [(int(cv2.contourArea(p.reshape(-1, 1, 2))), len(p)) for p in found]
print("contours (area, points):", sorted(diag, reverse=True))
polys = [p.reshape(-1, 2).astype(np.float32) for p in found if cv2.contourArea(p.reshape(-1, 1, 2)) > 8]
print(f"kept {len(polys)} contour(s) with area > 8px")
ncomp, lab = cv2.connectedComponents(submask.astype(np.uint8), 8)
print(f"connected components of glyph: {ncomp-1}")
assert polys, "no contours traced"

K = GRID / frame          # scale factor into the 1000-unit vector space
best = None
for eps in (0.20, 0.30, 0.40, 0.50, 0.65, 0.80, 1.00):
    cand = [cv2.approxPolyDP(p.reshape(-1, 1, 2), eps, True).reshape(-1, 2) for p in polys]
    test = np.zeros((frame, frame), np.uint8)
    cv2.fillPoly(test, [c.astype(np.int32) for c in cand], 1)
    iou = float((test & submask.astype(bool)).sum()) / float((test | submask.astype(bool)).sum())
    print(f"  eps={eps:.2f}  vertices={sum(len(c) for c in cand):3d}  IoU vs source mask={iou:.4f}")
    if iou >= 0.995:
        best = (eps, cand, iou)
        break
if best is None:
    best = (0.30, [cv2.approxPolyDP(p.reshape(-1, 1, 2), 0.30, True).reshape(-1, 2) for p in polys], None)
eps, cand, iou = best
print(f"chosen epsilon={eps}  polygons={len(cand)}  vertices={sum(len(c) for c in cand)}  IoU={iou}")


def raster(size: int, colour_hex: str, scale: float = 1.0) -> Image.Image:
    """Anti-aliased render of the traced geometry at `size` px."""
    s = size * 4
    img = np.zeros((s, s), np.uint8)
    pts = [np.round((c * K * scale - GRID / 2) * (s / GRID) + s / 2).astype(np.int32) for c in cand]
    cv2.fillPoly(img, pts, 255, lineType=cv2.LINE_AA)
    m = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA).astype(np.float64) / 255.0
    r, g, b = (int(colour_hex[i:i + 2], 16) for i in (1, 3, 5))
    out = np.zeros((size, size, 4), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = r, g, b
    out[..., 3] = np.round(m * 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def save(img: Image.Image, name: str) -> None:
    p = OUT / name
    img.save(p, optimize=True)
    print(f"  assets/{name:26s} {img.size[0]:>4d}x{img.size[1]:<4d} {p.stat().st_size/1024:6.1f} KB")


# --- 3. SVG --------------------------------------------------------------------
def path_d(scale: float = 1.0) -> str:
    out = []
    for c in cand:
        pts = (c * K - GRID / 2) * scale + GRID / 2
        out.append("M" + "L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + "Z")
    return "".join(out)


svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GRID} {GRID}" '
       f'width="{GRID}" height="{GRID}" role="img" aria-label="Haywood">\n'
       f'  <path fill="currentColor" fill-rule="evenodd" d="{path_d()}"/>\n</svg>\n')
(OUT / "haywood-mark.svg").write_text(svg)
print(f"  assets/haywood-mark.svg          vector   {len(svg)/1024:6.1f} KB")

for suffix, fill in (("ink", INK_HEX), ("white", "#ffffff"), ("red", RED_HEX)):
    named = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GRID} {GRID}" '
             f'width="{GRID}" height="{GRID}" role="img" aria-label="Haywood">\n'
             f'  <path fill="{fill}" fill-rule="evenodd" d="{path_d()}"/>\n</svg>\n')
    (OUT / f"haywood-mark-{suffix}.svg").write_text(named)
    print(f"  assets/haywood-mark-{suffix}.svg    vector   {len(named)/1024:6.1f} KB")

badge_svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GRID} {GRID}" '
             f'width="{GRID}" height="{GRID}" role="img" aria-label="Haywood Tattoo Studio">\n'
             f'  <rect width="{GRID}" height="{GRID}" rx="170" fill="{RED_HEX}"/>\n'
             f'  <g transform="translate({GRID/2},{GRID/2}) scale(0.80) translate({-GRID/2},{-GRID/2})">\n'
             f'    <path fill="#ffffff" fill-rule="evenodd" d="{path_d()}"/>\n  </g>\n</svg>\n')
(OUT / "haywood-badge.svg").write_text(badge_svg)
print(f"  assets/haywood-badge.svg         vector   {len(badge_svg)/1024:6.1f} KB")

# --- 4. PNG marks --------------------------------------------------------------
print("\n-- glyph on transparency --")
for colour, name in (("#ffffff", "haywood-mark-white.png"),
                     (RED_HEX, "haywood-mark-red.png"),
                     (INK_HEX, "haywood-mark-black.png")):
    save(raster(1024, colour), name)

print("\n-- badge (white glyph on red rounded square) --")
BS = 1024
badge = Image.new("RGBA", (BS, BS), (0, 0, 0, 0))
ImageDraw.Draw(badge).rounded_rectangle([0, 0, BS - 1, BS - 1], radius=int(BS * 0.17), fill=RED_HEX)
bm = raster(int(BS * 0.80), "#ffffff")
badge.alpha_composite(bm, ((BS - bm.width) // 2, (BS - bm.height) // 2))
save(badge, "haywood-badge.png")

print("\n-- icons --")
def badge_at(sz: int, glyph_scale: float) -> Image.Image:
    b = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    ImageDraw.Draw(b).rounded_rectangle([0, 0, sz - 1, sz - 1], radius=max(1, int(sz * 0.17)), fill=RED_HEX)
    g = raster(max(8, int(sz * glyph_scale)), "#ffffff")
    b.alpha_composite(g, ((sz - g.width) // 2, (sz - g.height) // 2))
    return b


print("\n-- icons (tighter glyph for tiny sizes) --")
for sz, nm, sc in ((64, "favicon-64.png", 0.86), (48, "favicon-48.png", 0.86),
                   (32, "favicon-32.png", 0.88), (180, "apple-touch-icon.png", 0.80),
                   (512, "icon-512.png", 0.80)):
    save(badge_at(sz, sc), nm)

# --- 5. social card ------------------------------------------------------------
print("\n-- og-image.png --")
W, H = 1200, 630
yy = np.linspace(0, 1, H)[:, None]
grad = (16 + 30 * yy)
base = np.dstack([np.ones((H, W)) * grad, np.ones((H, W)) * grad * 0.94,
                  np.ones((H, W)) * grad * 1.22]).astype(np.uint8)
card = Image.fromarray(base, "RGB").convert("RGBA")
glow = Image.new("L", (W, H), 0)
ImageDraw.Draw(glow).ellipse([W - 540, -200, W + 340, 560], fill=95)
glow = glow.filter(ImageFilter.GaussianBlur(120)).point(lambda v: min(v, 46))
card = Image.composite(Image.new("RGBA", (W, H), RED + (255,)), card, glow)
c = ImageDraw.Draw(card, "RGBA")
c.rectangle([0, 0, 10, H], fill=RED_HEX)
bigm = raster(320, "#ffffff")
card.alpha_composite(bigm, (68, (H - bigm.height) // 2))


def font(px, bold=True):
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/" +
                              ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), px)


def spaced(dr, xy, text, f, fill, tracking=0):
    x, y = xy
    for ch in text:
        dr.text((x, y), ch, font=f, fill=fill)
        x += dr.textlength(ch, font=f) + tracking


c.line([452, 178, 452, 452], fill=(255, 255, 255, 46), width=1)
spaced(c, (508, 190), "HAYWOOD", font(72), "#ffffff", 11)
spaced(c, (508, 286), "TATTOO STUDIO", font(29, False), RED + (255,), 15)
spaced(c, (508, 346), "CUSTOM INK  ·  PRIVATE SESSIONS  ·  PRETORIA", font(18, False),
       (255, 255, 255, 200), 4)
c.line([508, 388, 508 + 470, 388], fill=(255, 255, 255, 40), width=1)
spaced(c, (508, 408), "BOOKINGS  061 759 3378", font(17, False), (255, 255, 255, 132), 3)
card.convert("RGB").save(OUT / "og-image.png", optimize=True)
print(f"  assets/og-image.png              {W}x{H}  {(OUT/'og-image.png').stat().st_size/1024:.1f} KB")

# --- 6. checks -----------------------------------------------------------------
print("\n-- verification --")
ref = np.asarray(Image.open(OUT / "haywood-mark-white.png").convert("RGBA")).astype(np.float64)
ref_a = ref[..., 3] / 255.0
small = raster(frame, "#ffffff")
sm = np.asarray(small)[..., 3].astype(np.float64) / 255.0
crop_ref = sub  # source matte in the same square frame
inter = np.minimum(sm, crop_ref).sum()
union = np.maximum(sm, crop_ref).sum()
print(f"  vector-vs-source soft IoU at 225px: {inter/union:.4f}")
fav = np.asarray(badge.resize((16, 16), Image.LANCZOS).convert("RGB"))
print(f"  16px favicon: mean {fav.mean():.0f}/255, brightest {fav.max()}, "
      f"red-channel spread {fav[...,0].min()}..{fav[...,0].max()}")
sizes = sorted([(f.stat().st_size, f.name) for f in OUT.iterdir() if f.suffix in ('.png', '.svg')])
print("\n-- assets/ inventory --")
for sz, nm in sizes:
    print(f"  {sz/1024:8.1f} KB  {nm}")
print(f"  {'-'*22}\n  {sum(s for s, _ in sizes)/1024/1024:8.2f} MB  total")
