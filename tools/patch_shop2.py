#!/usr/bin/env python3
"""patch_shop2.py — round-6 polish on top of patch_shop.py.

  * downloads use data URLs (works without URL.createObjectURL, which jsdom lacks)
  * one refreshMedia() pass so an uploaded picture repaints every surface that uses it
  * CSV rows are real CRLF lines
  * photo-fill never escapes its container; the hero offer art clears with the card

Idempotent, state in tools/.shop2-state.json.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
STATE = ROOT / "tools" / ".shop2-state.json"

REFRESH_JS = r"""function refreshMedia(){renderProducts();renderLookbook();renderCart();
      if(typeof renderArtists==='function')renderArtists();
      if(typeof renderFriday==='function')renderFriday();
      if(typeof renderSpecial==='function')renderSpecial();
      if(typeof renderSpecials==='function')renderSpecials();
      if(typeof renderAdmin==='function')renderAdmin()}"""

EDITS = [
    # ---- a shared refresh so uploads land everywhere at once -----------------
    ("insertBefore", "    function onImagePicked(input){", REFRESH_JS + "\n"),
    ("replaceAll", "save();renderProducts();renderLookbook();renderAdmin();", "save();refreshMedia();"),
    ("replaceAll", "save();renderProducts();renderLookbook();renderAdmin();\n      toast(", "save();refreshMedia();\n      toast("),
    # ---- downloads without blob URLs ----------------------------------------
    ("replace", r"""function downloadFile(name,content){let url,revoke=false;
      if(typeof Blob!=='undefined'&&content instanceof Blob){url=URL.createObjectURL(content);revoke=true}else{url=String(content)}
      const a=document.createElement('a');a.href=url;a.download=name;a.rel='noopener';document.body.appendChild(a);a.click();a.remove();
      if(revoke&&URL.revokeObjectURL)setTimeout(()=>URL.revokeObjectURL(url),2000);return name}""",
     None),  # filled in below from REFRESH-style raw text
    ("replace", "downloadFile(name,dataUrlToBlob(ref.local));", "downloadFile(name,ref.local);"),
    ("replace", r"""    function dataUrlToBlob(dataUrl){const s=String(dataUrl||'');const i=s.indexOf(',');if(i<0)return new Blob([s],{type:'text/plain'});
      const dec=window.atob||atob;const bin=dec(s.slice(i+1));const bytes=new Uint8Array(bin.length);for(let n=0;n<bin.length;n++)bytes[n]=bin.charCodeAt(n);
      return new Blob([bytes],{type:(s.slice(0,i).match(/:(.*?);/)||[])[1]||'application/octet-stream'})}
""", ""),
    # ---- CSV: plain data URL, real CRLF -------------------------------------
    ("replace", "new Blob([lines.join(", "'data:text/csv;charset=utf-8,'+encodeURIComponent(lines.join("),
    ("replace", "],{type:'text/csv;charset=utf-8'}))}", "))}"),
    # ---- hero offer art must not linger on the weekly card ------------------
    ("replace", "if(!hero){box.hidden=true;return}", "if(!hero){box.hidden=true;renderOfferArt(null);return}"),
    ("replace", "if(hero.type==='fridays'){renderFridayHero(box,hero.fr);return}",
     "if(hero.type==='fridays'){renderFridayHero(box,hero.fr);renderOfferArt(null);return}"),
    # ---- positioning guards for images inside non-positioned hosts ----------
    ("insertBefore", "  </style>", """
    .look-image,.product-art,.artist-id>div:first-child{position:relative}
    .offer-art .photo-fill,.friday-art .photo-fill,.look-gallery .photo-fill{position:static}
    .look-gallery .photo-fill{height:52px}
    .special-row>div:first-child{min-width:0}
    .friday-band{align-items:center}
"""),
]

OLD_DL = r"""function downloadFile(name,content){let url,revoke=false;
      if(typeof Blob!=='undefined'&&content instanceof Blob){url=URL.createObjectURL(content);revoke=true}else{url=String(content)}
      const a=document.createElement('a');a.href=url;a.download=name;a.rel='noopener';document.body.appendChild(a);a.click();a.remove();
      if(revoke&&URL.revokeObjectURL)setTimeout(()=>URL.revokeObjectURL(url),2000);return name}"""

NEW_DL = r"""function downloadFile(name,href){const a=document.createElement('a');a.href=String(href);a.download=name;a.rel='noopener';
      document.body.appendChild(a);a.click();a.remove();
      if(String(href).indexOf('blob:')===0&&window.URL&&URL.revokeObjectURL)setTimeout(()=>URL.revokeObjectURL(href),2000);return name}"""


def patch(page):
    for kind, *rest in EDITS:
        if kind == "insertBefore":
            needle, block = rest
            if block[:60] in page:
                continue
            i = page.index(needle)
            page = page[:i] + block + page[i:]
        elif kind == "replace":
            a, b = rest
            if b is None:
                a, b = OLD_DL, NEW_DL
            if b[:70] in page and a not in page:
                continue
            n = page.count(a)
            assert n == 1, f"anchor {n}x (want 1): {a[:90]!r}"
            page = page.replace(a, b)
        elif kind == "replaceAll":
            a, b = rest
            if b in page and a not in page:
                continue
            if a in page:
                page = page.replace(a, b)
        else:
            raise ValueError(kind)
    return page


def main() -> int:
    applied = STATE.exists() and json.loads(STATE.read_text())
    if "--status" in sys.argv:
        print("applied:", applied or "(none)")
        return 0
    if applied:
        print("nothing to do (already applied)")
        return 0
    page = PAGE.read_text()
    start = page
    page = patch(page)
    css = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
    assert css.count("{") == css.count("}"), "unbalanced CSS"
    open("/tmp/shop2.js", "w").write(re.search(r"<script>(.*)</script>", page, re.S).group(1))
    PAGE.write_text(page)
    STATE.write_text(json.dumps(["polish"]))
    print(f"written · {len(page)} chars · +{len(page)-len(start)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
