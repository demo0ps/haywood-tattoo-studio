# Tests

These suites load `index.html` in jsdom and drive **the page's own functions** —
`calculateEstimate()`, `handleQuick()`, `renderSpecial()`, the admin handlers — so they
fail when the shipped code breaks, not when a re-implementation drifts.

```bash
cd tests
npm install jsdom
node run-all.js
```

| suite | covers |
|---|---|
| `specials.test.js` | special state machine (live / scheduled / expired / paused), scope matching, discount maths and clamping against the studio minimum, hero card render/hide, admin CRUD, validation guards, transcript + credit metering, localStorage persistence |
| `ui.test.js` | what a crawler sees in the raw HTML (lookbook, shop, FAQ, pricing, special), mobile nav sheet, sticky bar, Studio OS drawer on a phone, shop cart flow, responsive plumbing (safe-area, dvh, lazy loading, reduced motion), address privacy |
| `assistant.test.js` | concierge intake flow, budget-conflict advice, artist-review gate, handoff to WhatsApp, refine-without-duplicate-leads, honesty guardrails |

No framework, no build step — plain assertions, exit code 1 on any failure.
