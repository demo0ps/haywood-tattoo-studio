#!/usr/bin/env python3
"""Contact sheet for eyeball QA of the extracted Haywood mark at real sizes."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

A = Path('/home/user/assets')
OUT = Path('/home/user/uploads/brand-sheet.png')
INK, PAPER, RED = (13, 13, 15), (247, 246, 243), (214, 0, 0)
F = lambda p, b=True: ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/" + ("DejaVuSans-Bold.ttf" if b else "DejaVuSans.ttf"), p)

W, H = 1180, 1000
sheet = Image.new('RGB', (W, H), (30, 30, 34))
c = ImageDraw.Draw(sheet, 'RGBA')
c.text((28, 22), "HAYWOOD — extracted mark QA", font=F(24), fill=(255, 255, 255))
c.text((28, 56), "white-H-on-red extracted from the 225px source  ·  vector-traced  ·  no pixel upscaling",
       font=F(15, False), fill=(255, 255, 255, 160))

def place(img, x, y, bg=None, label=''):
    if bg is not None:
        base = Image.new('RGB', img.size, bg)
        base.paste(img, (0, 0), img if img.mode == 'RGBA' else None)
        sheet.paste(base, (x, y))
    else:
        sheet.paste(img, (x, y), img)
    if label:
        c.text((x, y + img.height + 6), label, font=F(13, False), fill=(255, 255, 255, 200))

# --- row 1: icons on light and dark ------------------------------------------
c.text((28, 96), "FAVICONS / TOUCH ICONS — composited on light, then on dark", font=F(14), fill=(*RED, 255))
y0 = 126
sizes = [(16, 'favicon-32.png', '16px'), (32, 'favicon-32.png', '32px'), (48, 'favicon-48.png', '48px'),
         (64, 'favicon-64.png', '64px'), (180, 'apple-touch-icon.png', '180px')]
x = 28
for target, name, lab in sizes:
    img = Image.open(A / name).convert('RGBA')
    if img.size[0] != target:
        img = img.resize((target, target), Image.LANCZOS)
    place(img, x, y0 + (180 - target) // 2, PAPER, lab)
    place(img, x, y0 + 180 + 26 + (180 - target) // 2, INK, lab + ' on ink')
    x += 210

# --- row 2: mark on transparency + zoom of edges -----------------------------
c.text((28, 560), "GLYPH ON TRANSPARENCY + 6× EDGE ZOOM", font=F(14), fill=(*RED, 255))
white = Image.open(A / 'haywood-mark-white.png').convert('RGBA').resize((200, 200), Image.LANCZOS)
ink = Image.open(A / 'haywood-mark-black.png').convert('RGBA').resize((200, 200), Image.LANCZOS)
place(white, 28, 592, INK, 'white mark (footer/dark)')
place(ink, 250, 592, PAPER, 'ink mark (on paper)')
red = Image.open(A / 'haywood-mark-red.png').convert('RGBA').resize((200, 200), Image.LANCZOS)
place(red, 472, 592, PAPER, 'red mark #d60000')

# source vs rebuilt crop, zoomed
src = Image.open('/home/user/uploads/pasted-image.png').convert('RGB').crop((36, 26, 130, 120)).resize((280, 280), Image.NEAREST)
sheet.paste(src, (700, 592))
c.text((700, 584 - 8), "SOURCE (nearest-zoom, note soft edge)", font=F(11, False), fill=(255, 255, 255, 170))
b = Image.open(A / 'haywood-badge.png').convert('RGBA').resize((104, 104), Image.LANCZOS).crop((8, 18, 112, 122)).resize((280, 280), Image.NEAREST)
sheet.paste(b, (1000 - 280, 592))
c.text((1000 - 280, 584 - 8), "REBUILT (nearest-zoom, crisp)", font=F(11, False), fill=(255, 255, 255, 170))

# --- row 3: header + footer + admin mockups ----------------------------------
mock = Image.new('RGB', (W - 56, 150), PAPER)
m = ImageDraw.Draw(mock, 'RGBA')
badge = Image.open(A / 'haywood-badge.png').convert('RGBA').resize((42, 42), Image.LANCZOS)
mock.paste(badge, (22, 54), badge)
m.text((76, 58), "HAYWOOD", font=F(15), fill=INK)
m.text((76, 80), "TATTOO STUDIO", font=F(10, False), fill=RED)
for i, t in enumerate(["LOOKBOOK", "SERVICES", "SHOP", "ABOUT"]):
    m.text((430 + i * 92, 68), t, font=F(12), fill=(111, 106, 103))
m.rounded_rectangle([880, 54, 1104, 96], radius=6, fill=RED)
m.text((900, 68), "Get an estimate", font=F(13), fill=(255, 255, 255))
m.line([0, 149, mock.width, 149], fill=(231, 227, 223))
sheet.paste(mock, (28, 812))
c.text((28, 796), "HEADER 1:1 MOCKUP (paper)", font=F(14), fill=(*RED, 255))
c.text((28, 830 - 178), "", font=F(12))
sheet.save(OUT)
print(f"wrote {OUT}  {sheet.size}")
