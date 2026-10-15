#!/usr/bin/env python3
"""tune_llms.py — teach the extractor and the UI counts about the 14th FAQ + the shop.

One-shot, guarded: every replacement asserts it found exactly one anchor.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sub(text, a, b, label):
    n = text.count(a)
    assert n == 1, f"{label}: anchor found {n}x"
    return text.replace(a, b)


# ------------------------------------------------------------------ ui counts
ui = ROOT / "tests" / "ui.test.js"
s = ui.read_text()
if '=== 14' not in s:
    s = sub(s, '(html.match(/<details class="faq-item"/g) || []).length === 13',
            '(html.match(/<details class="faq-item"/g) || []).length === 14', 'ui raw')
    s = sub(s, "$$('#faq details.faq-item').length === 13",
            "$$('#faq details.faq-item').length === 14", 'ui dom')
    ui.write_text(s)
    print('ui.test.js: faq counts -> 14')
else:
    print('ui.test.js: already at 14')

# -------------------------------------------------------------- llms builder
bl = ROOT / "tools" / "build_llms.py"
s = bl.read_text()
if 'shelf' in s:
    print('build_llms.py: shop block already present')
    raise SystemExit(0)

s = sub(s, 'assert len(prices) == 5 and len(faq) == 13 and',
        'assert len(prices) == 5 and len(faq) == 14 and', 'faq count')

SHOP = "\n".join([
    '# ------------------------------------------------------------- shop + delivery',
    'shopsec = slice_section(\'id="shop"\')',
    'shelf = []',
    'for art in re.split(r\'<article class="product"\', shopsec)[1:]:',
    '    nm = re.search(r\'<h3>(.*?)</h3>\', art, re.S)',
    '    pr = re.search(r\'<span>(.*?)</span>\', art, re.S)',
    '    if nm and pr:',
    '        shelf.append((clean(nm.group(1)), clean(pr.group(1))))',
    'ship = re.search(r"shipping:\\{courier:\'([^\']*)\',fee:(\\d+),freeOver:(\\d+),eta:\'([^\']*)\'", s)',
    'assert len(shelf) == 4 and ship, f\'shop drift: shelf={len(shelf)} ship={bool(ship)}\'',
    '',
])
i = s.index("assert len(prices) == 5")
s = s[:i] + SHOP + "\n" + s[i:]

L_SEC = "\n".join([
    "      '', '## Shop, delivery & collection', '',",
    "      '- On the shelf: ' + '; '.join(f'{n} {p}' for n, p in shelf) + '.',",
    "      f'- Courier nationwide via {ship.group(1)}: R{int(ship.group(2)):,} flat, free over '",
    "      f'R{int(ship.group(3)):,}, usually {ship.group(4)}.',",
    "      '- Collection is free at either studio and can be timed with an appointment.',",
    "      '- The studio confirms the delivery address and the contents before dispatch.',",
    "      '', '## Policies that shape a quote', '',",
])
s = sub(s, "      '', '## Policies that shape a quote', '',", L_SEC, 'llms shop section')

F_SEC = "\n".join([
    "F += ['## Shop (jewelry and aftercare)', '']",
    "for n, pr in shelf:",
    "    F += [f'- {n}: {pr}']",
    "F += ['', f'- Delivery: {ship.group(1)}, R{int(ship.group(2)):,} flat, free over R{int(ship.group(3)):,}, '",
    "      f'usually {ship.group(4)}.', '- Collection: free at either branch, timed with the appointment.', '',",
    "      '## Piercing Fridays', '', fri_copy,",
])
s = sub(s, "F += ['## Piercing Fridays', '', fri_copy,", F_SEC, 'full shop block')

s = sub(s, "'aftercare · visit (locations, hours, artists, reputation) · FAQ · shop (jewelry and aftercare) · privacy · terms', '',",
        "'aftercare · visit (locations, hours, artists, reputation) · FAQ · shop (jewelry, aftercare, delivery '\n"
        "      'and collection) · privacy · terms', '',", 'page structure line')

bl.write_text(s)
import ast
ast.parse(s)
print('build_llms.py: shop + delivery facts added')
