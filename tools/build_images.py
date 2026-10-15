#!/usr/bin/env python3
"""Responsive image variants for the two 3D renders.

Both source renders are fully opaque RGB PNGs (1.9 MB and 1.4 MB) that were being
shipped whole to every device, including the hero background on a phone. This
builds small raster variants and reports the saving.
"""
from pathlib import Path
from PIL import Image

A = Path('/home/user/assets')
SRC = {'hero': A / 'haywood-hero.png', 'mascot': A / 'haywood-mascot.png'}
# (name, width, jpg quality, webp quality)
JOBS = [
    ('haywood-hero-1200', 1200, 80, 80),
    ('haywood-hero-800',   800, 80, 80),
    ('haywood-mascot-900', 900, 84, 84),
    ('haywood-mascot-480', 480, 86, 86),
    ('haywood-mascot-160', 160, 88, 88),
]

made = []
for which, src in SRC.items():
    im = Image.open(src).convert('RGB')
    for name, w, jq, wq in JOBS:
        if which not in name:
            continue
        if w >= im.width:
            continue
        h = round(im.height * w / im.width)
        out = im.resize((w, h), Image.LANCZOS)
        j = A / f'{name}.jpg'
        o = A / f'{name}.webp'
        out.save(j, 'JPEG', quality=jq, optimize=True, progressive=True)
        out.save(o, 'WEBP', quality=wq, method=6)
        made.append((name, w, h, j.stat().st_size, o.stat().st_size))

print(f"{'file':26s} {'size':11s} {'jpg':>9s} {'webp':>9s}")
for name, w, h, js, os_ in made:
    print(f'{name+".jpg":26s} {w}x{h:<6d} {js/1024:8.0f}K {os_/1024:8.0f}K')

old = sum(p.stat().st_size for p in SRC.values())
new_wide = sum(m[3] for m in made if m[1] >= 900)
new_phone = next(m[3] for m in made if m[0] == 'haywood-hero-800') + next(m[3] for m in made if m[0] == 'haywood-mascot-160')
print(f'\nsource PNGs together          {old/1024/1024:6.2f} MB')
print(f'desktop set (jpg)             {new_wide/1024:6.0f} KB')
print(f'phone set (hero-800 + 160)    {new_phone/1024:6.0f} KB   ({old/new_phone:.1f}x smaller than the PNGs)')
