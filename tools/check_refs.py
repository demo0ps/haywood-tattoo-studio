#!/usr/bin/env python3
"""Verify every asset referenced from index.html exists on disk."""
import re
from pathlib import Path

ROOT = Path('/home/user')
s = (ROOT / 'index.html').read_text()

css = re.findall(r"""url\(['"]?(assets/[^'")]+)['"]?\)""", s)
attrs = re.findall(r"""(?:src|href)=['"](assets/[^'"]+)['"]""", s)
inline = re.findall(r"""['"](assets/[A-Za-z0-9._/-]+)['"]""", s)

refs = sorted(set(css) | set(attrs) | set(inline))
print(f"reference styles -> css:{len(set(css))} attr:{len(set(attrs))}")
missing = []
for r in refs:
    ok = (ROOT / r).exists()
    size = (ROOT / r).stat().st_size if ok else 0
    print(f"  {'OK     ' if ok else 'MISSING'}  {r:34s} {size/1024:8.1f} KB")
    if not ok:
        missing.append(r)

used = set(refs)
on_disk = {f"assets/{p.name}" for p in (ROOT / 'assets').iterdir()}
print("\nunreferenced files in assets/ (built but not linked):")
for r in sorted(on_disk - used):
    print("  ", r, f"{(ROOT / r).stat().st_size/1024:.1f} KB")
print(f"\n{len(refs)} referenced, {len(missing)} missing")
