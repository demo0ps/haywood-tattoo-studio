#!/usr/bin/env python3
"""patch_shop4.py — delivery settings the owner can actually change, and shop copy.

  * a Delivery card in Studio OS (courier name, flat fee, free-over threshold, transit)
  * the shop section states the fulfilment promise, built from config so it cannot drift
  * an empty shelf explains itself instead of showing nothing

Idempotent, state in tools/.shop4-state.json.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
STATE = ROOT / "tools" / ".shop4-state.json"

DELIVERY_CARD = (
    '<div class="admin-card"><div class="admin-card-head"><div><h3>Delivery</h3>'
    '<p>What customers see at checkout: the courier, the flat fee, and the spend that waives it.</p></div>'
    '<button class="btn btn-red btn-sm" data-action="save-shipping">Save delivery</button></div>'
    '<div class="loc-row"><div class="field"><label>Courier service</label><input id="adminShipName" /></div>'
    '<div class="field"><label>Flat fee (R)</label><input type="number" min="0" id="adminShipFee" /></div>'
    '<div class="field"><label>Free over (R)</label><input type="number" min="0" id="adminShipFree" /></div>'
    '<div class="field"><label>Typical transit</label><input id="adminShipEta" placeholder="2–4 working days" /></div>'
    '<p class="small">Collection stays free at both branches. Fees are what the checkout charges — '
    'the studio confirms the final amount on the order before it ships.</p></div></div>'
)

SHIPPING_JS = r"""function renderShipNote(){const el=document.getElementById('shipNote');if(!el)return;const sh=config.shipping||{};
      const fee=Number(sh.fee)||0,free=Number(sh.freeOver)||0;
      el.textContent=[fee?('Courier nationwide '+money(fee)+(free?(' · free over '+money(free)):'')):'Courier quoted per address',
        sh.eta?('Usually '+sh.eta):'', 'Free collection at '+branchList().map(b=>b.name).join(' or ')]
        .filter(Boolean).join(' · ')}
    function renderAdminShipping(){const sh=config.shipping||{};
      setVal('adminShipName',sh.courier||'');setVal('adminShipFee',Number(sh.fee)||0);
      setVal('adminShipFree',Number(sh.freeOver)||0);setVal('adminShipEta',sh.eta||'')}
    """

STAGE = {
    "doc": "delivery settings card, shop fulfilment line, empty shelf state",
    "edits": [
        ("replace",
         '<div class="admin-card"><div class="admin-card-head"><div><h3>Orders</h3>',
         DELIVERY_CARD + '<div class="admin-card"><div class="admin-card-head"><div><h3>Orders</h3>'),
        ("insertBefore", "function renderAdminOrders(){", SHIPPING_JS),
        ("replace", "renderAdminLocations();renderAdminFridays();renderAdminArtists();renderAdminReviews();renderAdminOrders();",
         "renderAdminLocations();renderAdminFridays();renderAdminArtists();renderAdminReviews();renderAdminOrders();renderAdminShipping();"),
        ("replace", "if(action==='export-orders')exportOrdersCsv();",
         "if(action==='save-shipping'){const sh=config.shipping;const g=id=>{const el=document.getElementById(id);return el?el.value.trim():''};\n"
         "          sh.courier=g('adminShipName')||sh.courier;sh.fee=Math.max(0,Number(g('adminShipFee'))||0);\n"
         "          sh.freeOver=Math.max(0,Number(g('adminShipFree'))||0);sh.eta=g('adminShipEta')||sh.eta;\n"
         "          save();renderShipNote();renderCheckoutTotals();renderAdmin();toast('Delivery settings saved')}\n"
         "        if(action==='export-orders')exportOrdersCsv();"),
        # the promise the customer reads before adding anything to the bag
        ("replace",
         "<p>Small essentials for new work, healing skin, and the jewelry you want to keep wearing.</p>",
         '<p>Small essentials for new work, healing skin, and the jewelry you want to keep wearing.</p>'
         '<p class="ship-note" id="shipNote"></p>'),
        ("replace", "renderLookbook();renderProducts();renderCart();renderAdmin();renderSpecial();renderStudioAll();",
         "renderLookbook();renderProducts();renderCart();renderAdmin();renderSpecial();renderShipNote();renderStudioAll();"),
        ("replace",
         "$('#productGrid').innerHTML=liveProducts.map(p=>",
         "$('#productGrid').innerHTML=(liveProducts.length?liveProducts.map(p=>"),
        ("replace",
         "</div></div></article>`).join('');$$('[data-add]')",
         "</div></div></article>`).join(''):'<p class=\"shelf-empty\">Nothing on the shelf right now — aftercare and jewelry are restocked between sessions, and the studio can hold pieces for your appointment.</p>');$$('[data-add]')"),
        # keep the line honest when the catalog or the fee changes
        ("replace", "saveProducts();save();renderProducts();renderCart();renderAdmin();",
         "saveProducts();save();renderProducts();renderCart();renderAdmin();renderShipNote();"),
        ("insertBefore", "  </style>", """
    .ship-note{margin-top:10px;font-size:12px;color:var(--muted);letter-spacing:.01em}
    .shelf-empty{grid-column:1/-1;padding:34px 22px;border:1px dashed var(--line);border-radius:18px;text-align:center;color:var(--muted)}
"""),
    ],
}

MARKERS = ["function renderShipNote()", "function renderAdminShipping()", "id=\"shipNote\"",
           "action==='save-shipping'", "renderAdminShipping();", "renderShipNote();",
           "shelf-empty", "Nothing on the shelf right now", "<h3>Delivery</h3>"]


def patch(page):
    for kind, *rest in STAGE["edits"]:
        if kind == "insertBefore":
            needle, block = rest
            if block[:60] in page:
                continue
            i = page.index(needle)
            page = page[:i] + block + page[i:]
        else:
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
    page = PAGE.read_text()
    start = page
    if applied:
        missing = [m for m in MARKERS if m not in page]
        assert not missing, "state claims applied but markers missing: " + ", ".join(missing)
        print("nothing to do (markers verified)")
        return 0
    page = patch(page)
    assert page != start, "nothing applied"
    css = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
    assert css.count("{") == css.count("}"), "unbalanced CSS"
    open("/tmp/shop4.js", "w").write(re.search(r"<script>(.*)</script>", page, re.S).group(1))
    PAGE.write_text(page)
    STATE.write_text(json.dumps(["delivery"]))
    print(f"written · {len(page)} chars · {len(page)-len(start):+d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
