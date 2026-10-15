#!/usr/bin/env python3
"""patch_shop6.py — keep unsaved editor text when a picture is attached, and
describe the commerce panel the way it now behaves.

Idempotent, state in tools/.shop6-state.json.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
STATE = ROOT / "tools" / ".shop6-state.json"

SYNC = ("function syncEditors(ctl){if(!ctl)return;if(ctl.closest('#adminProducts'))saveProducts();"
        "if(ctl.closest('#adminLookbook'))saveLookbookRows()}\n    ")

PICK = "function onImagePicked(input){const ctl=input.closest('[data-imgscope]');if(!ctl)return;"
PICK_NEW = "function onImagePicked(input){const ctl=input.closest('[data-imgscope]');if(!ctl)return;\n      syncEditors(ctl);"
HANDLER_TAIL = "const key=imageKeyOf(scope,ctl);const t=imageTarget(scope,id);const v=t?t[key]:null;"

EDITS = [
    ("replace", PICK, PICK_NEW),
    ("replaceAll",
     "const ctl=e.target.closest('[data-imgscope]');const scope=ctl.dataset.imgscope,id=ctl.dataset.imgid,multi=ctl.hasAttribute('data-imgmultiple');",
     "const ctl=e.target.closest('[data-imgscope]');const scope=ctl.dataset.imgscope,id=ctl.dataset.imgid,multi=ctl.hasAttribute('data-imgmultiple');\n        syncEditors(ctl);"),
    ("insertBefore", "    function imageControl(", SYNC),
    ("replace",
     "<p>Products, inventory, collection, shipping, discounts, and order status.</p>",
     "<p>Products, delivery, collection and the order book. Edits save to this browser — exported pictures need a commit into assets/ to reach visitors.</p>"),
]

MARKERS = ["function syncEditors(ctl)", "syncEditors(ctl);",
           "Edits save to this browser — exported pictures need a commit into assets/"]


def main() -> int:
    applied = json.loads(STATE.read_text()) if STATE.exists() else []
    if "--status" in sys.argv:
        print("applied:", applied or "(none)")
        return 0
    page = PAGE.read_text()
    start = page
    for kind, *rest in EDITS:
        if kind == "insertBefore":
            needle, block = rest
            if block[:50] in page:
                continue
            i = page.index(needle)
            page = page[:i] + block + page[i:]
        elif kind == "replaceAll":
            a, b = rest
            if b in page and a not in page:
                continue
            if a in page:
                page = page.replace(a, b)
        else:
            a, b = rest
            if b in page and a not in page:
                continue
            n = page.count(a)
            assert n == 1, f"anchor {n}x: {a[:80]!r}"
            page = page.replace(a, b)
    missing = [m for m in MARKERS if m not in page]
    assert not missing, "markers absent:\n  " + "\n  ".join(missing)
    assert page.count("syncEditors(ctl);") == 4, page.count("syncEditors(ctl);")
    if page == start:
        print("nothing to do (markers verified)")
        return 0
    open("/tmp/shop6.js", "w").write(re.search(r"<script>(.*)</script>", page, re.S).group(1))
    PAGE.write_text(page)
    STATE.write_text(json.dumps(["sync"]))
    print(f"written · {len(page)} chars · {len(page)-len(start):+d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
