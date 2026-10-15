#!/usr/bin/env python3
"""patch_shop3.py — round-6 fixes found by tests/commerce.test.js.

  * the lookbook gallery control wrote over the primary picture (shared key)
  * exported filenames collided for extra shots of the same project
  * the shop grid ignored a product's published/unpublished state

Idempotent, state in tools/.shop3-state.json.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
STATE = ROOT / "tools" / ".shop3-state.json"

EDITS = [
    # ---- assetName learns about the slot key and the shot number -------------
    ("replace",
     "function assetName(scope,id,ext){const base=scope==='fridays'?'piercing-fridays':scope+'-'+slug(id);return base+'.'+(ext||'webp')}",
     "function assetName(scope,id,ext,key,seq){const base=(scope==='fridays'?'piercing-fridays':scope+'-'+slug(id))"
     "+(key&&key!==(IMAGE_KEY[scope]||'image')?'-'+slug(key):'')+(seq?'-'+seq:'');return base+'.'+(ext||'webp')}"),
    # ---- the control takes an explicit key and numbers gallery exports -------
    ("replace",
     "function imageControl(scope,id,ref,label,multi){ref=ref||null;const key=imageKeyOf(scope);",
     "function imageControl(scope,id,ref,label,multi,keyOverride){ref=ref||null;const key=keyOverride||imageKeyOf(scope);\n"
     "      const tgt=imageTarget(scope,id);const list=tgt?tgt[key]:null;const seq=multi&&Array.isArray(list)?list.length:0;"),
    ("replace",
     "const ext=ref&&ref.type==='jpg'?'jpg':'webp';const name=assetName(scope,id,ext);const bytes=approxBytes(ref);",
     "const ext=ref&&ref.type==='jpg'?'jpg':'webp';const name=assetName(scope,id,ext,key,seq);const bytes=approxBytes(ref);"),
    ("replace",
     "const ext=ref.type==='jpg'?'jpg':'webp';const name=assetName(scope,id,ext);",
     "const ext=ref.type==='jpg'?'jpg':'webp';const arr=multi&&Array.isArray(v)?v:null;const name=assetName(scope,id,ext,key,arr?arr.indexOf(ref)+1:0);"),
    # ---- the lookbook editor passes the gallery key --------------------------
    ("replace",
     "'Extra shots of the piece',true)}",
     "'Extra shots of the piece',true,'gallery')}"),
    # ---- unpublished products stay out of the shop ---------------------------
    ("replace",
     "function renderProducts(){ $('#productGrid').innerHTML=products.map(p=>",
     "function renderProducts(){ const liveProducts=products.filter(p=>p.live!==false);\n"
     "      $('#productGrid').innerHTML=liveProducts.map(p=>"),
    ("replace",
     "<h4>${esc(p.name)||'Product '+(i+1)}</h4>",
     "<h4>${esc(p.name)||'Product '+(i+1)}${p.live!==false?'':' · hidden'}</h4>"),
]

MARKERS = ["assetName(scope,id,ext,key,seq)", "keyOverride||imageKeyOf(scope)",
           "'Extra shots of the piece',true,'gallery'", "const liveProducts=products.filter(p=>p.live!==false)",
           " · hidden'}</h4>"]


def patch(page):
    for kind, *rest in EDITS:
        assert kind == "replace", kind
        a, b = rest
        if b in page and a not in page:
            continue
        n = page.count(a)
        assert n == 1, f"anchor {n}x (want 1): {a[:90]!r}"
        page = page.replace(a, b)
    missing = [m for m in MARKERS if m not in page]
    assert not missing, "markers absent:\n  " + "\n  ".join(missing)
    return page


def main() -> int:
    applied = json.loads(STATE.read_text()) if STATE.exists() else []
    if "--status" in sys.argv:
        print("applied:", applied or "(none)")
        return 0
    if applied:
        page = PAGE.read_text()
        missing = [m for m in MARKERS if m not in page]
        assert not missing, "state says applied but markers are missing: " + ", ".join(missing)
        print("nothing to do (markers verified)")
        return 0
    page = PAGE.read_text()
    start = page
    page = patch(page)
    assert page != start, "nothing applied — anchors spent?"
    open("/tmp/shop3.js", "w").write(re.search(r"<script>(.*)</script>", page, re.S).group(1))
    PAGE.write_text(page)
    STATE.write_text(json.dumps(["fixes"]))
    print(f"written · {len(page)} chars · {len(page)-len(start):+d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
