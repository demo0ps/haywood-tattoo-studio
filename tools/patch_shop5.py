#!/usr/bin/env python3
"""patch_shop5.py — one FAQ entry so answer engines can explain delivery.

Adds the same question to the visible FAQ and to the FAQPage JSON-LD, worded the
way the checkout actually behaves (flat courier fee, free over the threshold, free
collection at both branches, studio confirms before dispatch).

Idempotent, state in tools/.shop5-state.json.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
STATE = ROOT / "tools" / ".shop5-state.json"

Q = 'Do you ship jewelry and aftercare?'
A = ('Yes. Courier anywhere in South Africa is a flat R120 and free once your bag reaches R1,500 — '
     'usually 2–4 working days. Collection at either studio is free and can wait for your appointment. '
     'The studio confirms the address and the contents before anything is dispatched, and jewelry is '
     'checked and sized by the artist first.')

DETAILS = (f'<details class="faq-item"><summary><b>{Q}</b><span aria-hidden="true">＋</span></summary>'
           f'<p>{A}</p></details>')
JSONLD = ('{"@type":"Question","name":' + json.dumps(Q, ensure_ascii=False) + ',"acceptedAnswer":{"@type":"Answer","text":'
          + json.dumps(A, ensure_ascii=False) + '}}')

EDITS = [
    ("replace",
     "so lock the time before you travel.</p></details></div>",
     "so lock the time before you travel.</p></details>" + DETAILS + "</div>"),
    ("replace",
     'Both take cards and mobile pay."}}]}',
     'Both take cards and mobile pay."}},' + JSONLD + ']}' ),
]


def main() -> int:
    applied = json.loads(STATE.read_text()) if STATE.exists() else []
    if "--status" in sys.argv:
        print("applied:", applied or "(none)")
        return 0
    page = PAGE.read_text()
    start = page
    for kind, a, b in EDITS:
        if b in page and a not in page:
            continue
        n = page.count(a)
        assert n == 1, f"anchor {n}x: {a[:80]!r}"
        page = page.replace(a, b)
    assert page.count('class="faq-item"') == 14, page.count('class="faq-item"')
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    ld = json.loads(blocks[0])
    nodes = ld if isinstance(ld, list) else (ld.get("@graph") or [ld])
    faqnode = [n for n in nodes if isinstance(n, dict) and n.get("@type") == "FAQPage"]
    assert faqnode and len(faqnode[0]["mainEntity"]) == 14, f'json-ld faq={len(faqnode[0]["mainEntity"]) if faqnode else "none"}'
    open("/tmp/shop5.js", "w").write(re.search(r"<script>(.*)</script>", page, re.S).group(1))
    PAGE.write_text(page)
    STATE.write_text(json.dumps(["faq"]))
    print(f"written · {len(page)} chars · {len(page)-len(start):+d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
