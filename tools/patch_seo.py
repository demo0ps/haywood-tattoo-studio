#!/usr/bin/env python3
"""SEO + answer-engine work: indexable static content, content sections, metadata, files."""
from pathlib import Path
import re

P = Path('/home/user/index.html')
s = P.read_text()
SITE = "https://demo0ps.github.io/haywood-tattoo-studio/"
log = []


def rep(old, new, label, count=1):
    global s
    assert old in s, f'ANCHOR MISSING: {label} :: {old[:80]!r}'
    s = s.replace(old, new, count)
    log.append(label)


def span(a, b, new, label):
    global s
    i, j = s.index(a), s.index(b)
    assert j > i, label
    s = s[:i] + new + s[j:]
    log.append(label)


# ── 1. document head ─────────────────────────────────────────────────────────
rep('<html lang="en">', '<html lang="en-ZA">', 'lang en-ZA')
rep('<meta name="viewport" content="width=device-width, initial-scale=1" />',
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />',
    'viewport-fit')
rep('<meta name="theme-color" content="#b9142b" />',
    '<meta name="theme-color" content="#0d0d0f" media="(prefers-color-scheme: dark)" />\n'
    '  <meta name="theme-color" content="#b9142b" />\n'
    '  <meta name="format-detection" content="telephone=no,address=no" />\n'
    '  <meta name="referrer" content="strict-origin-when-cross-origin" />\n'
    '  <meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1" />',
    'theme-color + robots')
rep('  <title>Haywood Tattoo Studio — Custom artwork. Private sessions.</title>',
    '  <title>Custom Tattoo &amp; Piercing Studio in Pretoria | Haywood Tattoo Studio</title>',
    'title keyword-rich')
rep('<meta name="description" content="Haywood Tattoo Studio - premium custom tattooing, piercing and private aftercare in Pretoria. Design concierge, transparent indicative pricing, studio or mobile sessions. WhatsApp 061 759 3378." />',
    '<meta name="description" content="Custom tattoo and piercing in Pretoria, by private appointment or on location. Get an indicative range in minutes, then book. WhatsApp 061 759 3378." />',
    'meta description')
rep('  <link rel="apple-touch-icon" sizes="180x180" href="assets/apple-touch-icon.png" />',
    '  <link rel="apple-touch-icon" sizes="180x180" href="assets/apple-touch-icon.png" />\n'
    '  <link rel="manifest" href="manifest.webmanifest" />\n'
    '  <link rel="preload" as="image" href="assets/haywood-hero-1200.jpg" media="(min-width:901px)" fetchpriority="high" />\n'
    '  <link rel="preload" as="image" href="assets/haywood-hero-800.jpg" media="(max-width:900px)" fetchpriority="high" />\n'
    '  <meta property="og:image:type" content="image/png" />\n'
    '  <meta property="og:image:secure_url" content="' + SITE + 'assets/og-image.png" />\n'
    '  <meta name="twitter:image:alt" content="The Haywood gothic H mark in white on deep red" />\n'
    '  <link rel="alternate" hreflang="en-za" href="' + SITE + '" />',
    'manifest + preload + extras')

# ── 2. structured data: one graph, answer-engine friendly ────────────────────
faq = [
    ("How much does a custom tattoo cost in Pretoria?",
     "Custom work starts at a studio minimum of R1,800. Most medium pieces land between R2,500 and R6,000 once size, placement, detail level and colour are accounted for. The design concierge on this page gives you an indicative range from your brief; the artist confirms the final quote before a design is locked."),
    ("Do you tattoo walk-ins?",
     "No. Haywood is a private, by-appointment studio with one artist, so each session gets the whole day and no waiting room. Send a brief over WhatsApp or through the concierge and you will get a reply with available dates."),
    ("How do I book a session?",
     "Describe the piece, get an indicative range, then pay a deposit to hold the date. The deposit is credited to your final price. You can book a ready-to-run lookbook piece directly, or ask for one to be adapted."),
    ("Can you come to me?",
     "Yes. Mobile tattoo sessions are available in Pretoria and roughly 30 km around it, with a travel fee that is currently set at R350 and confirmed in your brief before anything is booked."),
    ("How big is the deposit?",
     "Thirty per cent of the quoted range, calculated from the lower end so it never surprises you. It secures your slot and comes off the final amount."),
    ("Do you do cover-ups and touch-ups?",
     "Yes, subject to assessment. Send clear, straight-on photos of the existing work in daylight and the artist will tell you honestly whether it needs one session, two, or laser first."),
    ("How old do I have to be?",
     "Eighteen or older with a valid South African ID or passport, checked and kept on file at your first session. There are no exceptions, including for clients with a parent or guardian."),
    ("What aftercare does a new piercing need?",
     "Sterile saline once or twice a day, leave the jewelry in, keep hair, phone screens and helmets clean, and avoid swimming for the healing window. Follow the sheet you are handed at the studio. If something worries you, see a clinician — the studio does not diagnose or treat reactions."),
    ("Who owns the design afterwards?",
     "The artwork remains the artist's intellectual property; your tattoo is yours on your body. Haywood asks not to have its designs copied by other studios."),
    ("Are the prices on this site final?",
     "No. Every figure you see here is an indicative range produced by the brief you fill in, and any live studio special is applied to that range automatically. The confirmed quote always comes from the artist."),
]
def jesc(t):
    return t.replace('"', "'").replace('\u201c', "'").replace('\u201d', "'").replace('&', '& ')
faq_items = ",".join(
    '{"@type":"Question","name":"' + jesc(q) + '","acceptedAnswer":{"@type":"Answer","text":"' + jesc(a) + '"}}'
    for q, a in faq)

ld = ('  <script type="application/ld+json">\n'
      '  {"@context":"https://schema.org","@graph":[\n'
      '    {"@type":"TattooParlor","@id":"' + SITE + '#studio","name":"Haywood Tattoo Studio","url":"' + SITE + '",'
      '"image":"' + SITE + 'assets/og-image.png","logo":"' + SITE + 'assets/haywood-badge.png",'
      '"description":"Private, by-appointment tattoo and piercing studio in Pretoria. Custom design, mobile sessions, transparent indicative pricing.",'
      '"telephone":"+27617593378","email":"","priceRange":"R1800+","currenciesAccepted":"ZAR","paymentAccepted":"Cash, Card, Yoco mobile card terminal",'
      '"address":{"@type":"PostalAddress","addressLocality":"Pretoria","addressRegion":"Gauteng","addressCountry":"ZA"},"areaServed":{"@type":"City","name":"Pretoria"},'
      '"sameAs":["https://instagram.com/haywood_studio"],"openingHours":"Tu-Sa","founder":{"@type":"Person","name":"Haywood"},"memberOf":{"@type":"Organization","name":"Private studio, by appointment only"},'
      '"hasOfferCatalog":{"@type":"OfferCatalog","name":"Studio services","itemListElement":['
      '{"@type":"Offer","itemOffered":{"@type":"Service","name":"Custom tattoo design and session","serviceType":"Tattoo","description":"One-off custom work built from your brief, quoted as a range and confirmed by the artist.","areaServed":"Pretoria","url":"' + SITE + '#services"}},'
      '{"@type":"Offer","itemOffered":{"@type":"Service","name":"Piercing","serviceType":"Piercing","description":"Lobe, cartilage and facial piercing with quality jewelry and written aftercare.","url":"' + SITE + '#services"}},'
      '{"@type":"Offer","itemOffered":{"@type":"Service","name":"Mobile tattoo session","serviceType":"Tattoo","description":"The same private setup at your location within roughly 30 km of Pretoria, with a travel fee confirmed in the brief.","url":"' + SITE + '#services"}},'
      '{"@type":"Offer","itemOffered":{"@type":"Service","name":"Lookbook and flash pieces","serviceType":"Tattoo","description":"Ready-to-book artwork from the artist, some exclusive, some repeatable.","url":"' + SITE + '#lookbook"}},'
      '{"@type":"Offer","itemOffered":{"@type":"Service","name":"Tattoo aftercare and jewelry","serviceType":"Retail","description":"Sterile saline, titanium and steel jewelry, and care kits.","url":"' + SITE + '#shop"}}]}},'
      '    {"@type":"FAQPage","@id":"' + SITE + '#faq","mainEntity":[' + faq_items + ']},\n'
      '    {"@type":"WebSite","@id":"' + SITE + '#website","url":"' + SITE + '","name":"Haywood Tattoo Studio","inLanguage":"en-ZA","publisher":{"@id":"' + SITE + '#studio"}}\n'
      '  ]}\n'
      '  </script>\n')
i = s.index('  <script type="application/ld+json">')
j = s.index('  </script>', i) + len('  </script>\n')
s = s[:i] + ld + s[j:]
log.append('JSON-LD graph (TattooParlor+OfferCatalog, FAQPage, WebSite)')

# ── 3. skip link ─────────────────────────────────────────────────────────────
rep('<body>\n  <div class="topline">',
    '<body>\n  <a class="skip-link" href="#lookbook">Skip to the work</a>\n  <div class="topline">',
    'skip link')

# ── 4. nav: pricing + faq ────────────────────────────────────────────────────
rep('<nav class="navlinks"><a href="#lookbook">Lookbook</a><a href="#services">Services</a><a href="#shop">Shop</a><a href="#about">About</a></nav>',
    '<nav class="navlinks" aria-label="Primary"><a href="#lookbook">Lookbook</a><a href="#services">Services</a><a href="#pricing">Pricing</a><a href="#shop">Shop</a><a href="#faq">FAQ</a><a href="#about">About</a></nav>',
    'desktop nav links')

# ── 5. indexable static content for the JS-rendered grids ────────────────────
static_look = '''<div class="lookbook-grid" id="lookbookGrid">
          <article class="look-card" data-project="serpent-sun"><div class="look-image dark"><span class="availability">Limited</span></div><div class="look-info"><h3>Serpent / Sun Study</h3><div class="look-meta"><span>Adaptable concept</span><span class="look-price">R 3,800 – R 5,200</span></div><div class="look-meta" style="margin-top:7px"><span>Upper arm · back</span><span>3–5 hours</span></div><span class="look-link">Ask about this piece ↗</span></div></article>
          <article class="look-card" data-project="red-altar"><div class="look-image red"><span class="availability">Exclusive</span></div><div class="look-info"><h3>Red Altar</h3><div class="look-meta"><span>Ready-to-book flash</span><span class="look-price">R 2,900</span></div><div class="look-meta" style="margin-top:7px"><span>Chest · sternum</span><span>2–3 hours</span></div><span class="look-link">Ask about this piece ↗</span></div></article>
          <article class="look-card" data-project="thorn-eye"><div class="look-image paper"><span class="availability">Repeatable</span></div><div class="look-info"><h3>Thorn Eye</h3><div class="look-meta"><span>Repeatable study</span><span class="look-price">R 2,200 – R 3,100</span></div><div class="look-meta" style="margin-top:7px"><span>Forearm · calf</span><span>2–3 hours</span></div><span class="look-link">Ask about this piece ↗</span></div></article>
        </div>'''
rep('<div class="lookbook-grid" id="lookbookGrid"></div>', static_look, 'static lookbook cards')

static_shop = '''<div class="product-grid" id="productGrid">
          <article class="product" data-product="saline"><div class="product-info"><h3>Sterile Saline Mist</h3><p>Gentle piercing aftercare</p><div class="product-row"><span>R180</span><button class="btn btn-dark btn-sm" data-add="saline">Add</button></div></div></article>
          <article class="product" data-product="onyx-hoop"><div class="product-info"><h3>Onyx Clicker Hoop</h3><p>316L surgical steel · 8mm</p><div class="product-row"><span>R420</span><button class="btn btn-dark btn-sm" data-add="onyx-hoop">Add</button></div></div></article>
          <article class="product" data-product="red-gem"><div class="product-info"><h3>Red Stone Labret</h3><p>Titanium · internally threaded</p><div class="product-row"><span>R560</span><button class="btn btn-dark btn-sm" data-add="red-gem">Add</button></div></div></article>
          <article class="product" data-product="healing-kit"><div class="product-info"><h3>Fresh Ink Care Kit</h3><p>Aftercare essentials</p><div class="product-row"><span>R320</span><button class="btn btn-dark btn-sm" data-add="healing-kit">Add</button></div></div></article>
        </div>'''
rep('<div class="product-grid" id="productGrid"></div>', static_shop, 'static shop cards')

# ── 6. new content sections ──────────────────────────────────────────────────
SECTIONS = '''
    <section class="pricing" id="pricing"><div class="container"><div class="section-head"><div><div class="eyebrow">Transparent pricing</div><h2>What a piece <span class="serif">actually costs.</span></h2></div><p>No “from R500” bait. These are the working numbers behind every estimate on this site, and the artist can change any of them.</p></div><div class="pricing-grid"><div class="price-card price-lead"><span class="price-label">Studio minimum</span><b>R1,800</b><p>The floor for any custom piece, including small blackwork. It covers the design time, setup, sterilisation and the first hour on the chair.</p></div><div class="price-card"><span class="price-label">Session rate</span><b>R1,200<span>/hour</span></b><p>Applied once you are past the minimum. Long days are quoted as a project, not clocked hour by hour.</p></div><div class="price-card"><span class="price-label">Deposit</span><b>30%</b><p>Taken from the lower end of your range to hold the date, then credited back against the final price.</p></div><div class="price-card"><span class="price-label">Mobile travel</span><b>R350</b><p>Within Pretoria and roughly 30 km around it. Anything further gets quoted with you before it is booked.</p></div><div class="price-card"><span class="price-label">Adds</span><b>R700 – R1,400</b><p>Medium and large sizes and high-detail work move the number up. Colour work adds about R700.</p></div><div class="price-card price-quote"><span class="price-label">Get a real range</span><p>Tell the concierge the idea, size, placement and detail level and it will calculate an indicative range against these same rules — including any live special.</p><button class="btn btn-red" data-action="open-estimate">Build a brief ↗</button></div></div><p class="pricing-note">Ranges, not promises. Complex, sensitive or large placements are always reviewed by the artist in person or from photos before a quote is confirmed. All prices in South African rand, inclusive of VAT where applicable.</p></div></section>

    <section class="aftercare" id="aftercare"><div class="container"><div class="section-head"><div><div class="eyebrow">Healing</div><h2>Look after it, <span class="serif">keep it sharp.</span></h2></div><p>What you do in the first two weeks decides how the piece ages. You also leave every session with a printed sheet.</p></div><div class="aftercare-grid"><div class="aftercare-card"><h3><span aria-hidden="true">01</span>Fresh tattoo</h3><ol><li><b>Wrap stays on</b> for the first three to five hours, then remove it gently.</li><li><b>Wash</b> twice a day with lukewarm water and fragrance-free soap, pat dry — never rub.</li><li><b>Moisturise</b> in a thin layer, two or three times a day for about two weeks. Heavy layers suffocate the skin.</li><li><b>Leave flakes alone.</b> Peeling pulls ink out with it.</li><li><b>Six weeks off</b> the pool, the sea, and the gym’s benches. Sun is the long-term enemy — factor 50 once healed.</li></ol></div><div class="aftercare-card"><h3><span aria-hidden="true">02</span>Fresh piercing</h3><ol><li><b>Sterile saline</b> once or twice a day. Clean hands before you touch anything.</li><li><b>Do not twist or remove</b> the jewelry, even overnight.</li><li><b>Watch the friction:</b> hair, phone, masks, helmet straps, pillows.</li><li><b>No swimming</b> for the healing window — oceans and pools are the worst offenders.</li><li><b>Lobe:</b> about six weeks. <b>Cartilage:</b> three to nine months, sometimes more.</li></ol></div></div><p class="aftercare-note">This is general aftercare, not medical advice. Haywood does not diagnose or treat infections or reactions — if something worries you, see a clinician, then tell the studio. <a href="#shop">Stock up on saline and care kits →</a></p></div></section>

    <section class="faq" id="faq"><div class="container"><div class="section-head"><div><div class="eyebrow">Straight answers</div><h2>Asked <span class="serif">all the time.</span></h2></div><p>If your question is not here, the concierge or a WhatsApp message will sort it out.</p></div><div class="faq-grid">''' + \
    "".join(f'<details class="faq-item"{" open" if k < 2 else ""}><summary><b>{q}</b><span aria-hidden="true">＋</span></summary><p>{a}</p></details>' for k, (q, a) in enumerate(faq)) + \
    '''</div></div></section>

    <section class="legal" id="privacy"><div class="container legal-grid"><div><h2>Privacy</h2><p><b>What this demo stores:</b> your brief, reference image name, cart and booking details stay in your own browser via <code>localStorage</code>. Nothing is sent anywhere in demo mode. The concierge keeps the conversation so the artist can read it — it does not speak for the studio, and it will not quote a final price.</p><p><b>When the studio goes live:</b> your name, number, email, brief, reference images and payment status are held to book and follow up on your session, and are handled in line with POPIA. You can ask for your record to be corrected or deleted at any time on WhatsApp.</p><p><b>Card details</b> are never stored here — payments run through a hosted Yoco checkout, and the studio keeps only the receipt reference.</p></div><div><h2 id="terms">Terms</h2><p><b>Age:</b> 18+ with valid ID, checked at every first session. <b>Health:</b> tell the artist about medication, skin conditions, allergies, pregnancy or anything else relevant before you book — the studio may ask you to wait, and that call is the artist’s to make.</p><p><b>Deposits:</b> secure a slot and are credited to your final price; they are not refunded if you simply do not show, but they move with you if you give notice. Reschedule requests go straight to the artist over WhatsApp.</p><p><b>Designs:</b> the artwork is the artist’s intellectual property; the tattoo on your skin is yours. <b>Prices:</b> every number on this site, including any live special, is indicative until the artist confirms it.</p></div></div></section>
'''
i = s.index('\n  </main>\n') + 1
s = s[:i] + SECTIONS + s[i:]
log.append('pricing + aftercare + faq + legal sections')

# ── 7. responsive images ────────────────────────────────────────────────────
rep("<img class=\"mascot-render\" src=\"assets/haywood-mascot.png\" alt=\"3D Haywood sacred heart and serpent mascot\">",
    "<picture><source type=\"image/webp\" srcset=\"assets/haywood-mascot-900.webp\" /><img class=\"mascot-render\" src=\"assets/haywood-mascot-900.jpg\" alt=\"3D render of the Haywood mascot: a sacred heart with a coiled serpent and tattoo needle on deep red\" width=\"900\" height=\"491\" loading=\"lazy\" decoding=\"async\" /></picture>",
    'mascot picture element')
rep('<img src="assets/haywood-mascot.png" alt="Haywood Guide mascot">',
    '<picture><source type="image/webp" srcset="assets/haywood-mascot-160.webp 1x" /><img src="assets/haywood-mascot-160.jpg" alt="" width="160" height="87" loading="lazy" decoding="async" aria-hidden="true" /></picture>',
    'mascot button picture')
rep("url('assets/haywood-hero.png') center/cover", "url('assets/haywood-hero-1200.jpg') center/cover", 'hero bg to jpg')


# ── 8. CSS for the new sections ──────────────────────────────────────────────
rep('  </style>', '''
    /* ── indexable content sections ─────────────────────────────────── */
    img{max-width:100%;height:auto}
    .skip-link{position:absolute;left:14px;top:-60px;z-index:80;background:var(--ink);color:#fff;padding:12px 18px;border-radius:0 0 12px 12px;font-size:12px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;transition:top .2s}
    .skip-link:focus{top:0}
    .pricing,.aftercare,.faq,.legal{padding:88px 0;border-top:1px solid var(--line)}
    .aftercare{background:var(--soft-red)}
    .pricing-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:8px}
    .price-card{background:var(--white);border:1px solid var(--line);border-radius:var(--radius);padding:24px;display:flex;flex-direction:column;gap:9px;box-shadow:0 10px 30px rgba(15,11,11,.05)}
    .price-label{font-size:10px;letter-spacing:.2em;text-transform:uppercase;font-weight:900;color:var(--red)}
    .price-card b{font-size:34px;line-height:1;letter-spacing:-.04em;font-weight:900}
    .price-card b span{font-size:13px;font-weight:600;color:var(--muted);letter-spacing:0;margin-left:5px}
    .price-card p{margin:0;font-size:13px;line-height:1.6;color:var(--muted)}
    .price-lead{background:var(--ink);border-color:var(--ink)}
    .price-lead b,.price-lead p{color:#fff}
    .price-lead p{color:#c9c3c1}
    .price-quote{background:linear-gradient(140deg,#1b0d10,#0d0d0f);border-color:rgba(214,0,0,.5)}
    .price-quote p{color:#d3cdcb}
    .price-quote .btn{margin-top:auto;align-self:flex-start}
    .pricing-note{margin:26px 0 0;font-size:12.5px;line-height:1.65;color:var(--muted);max-width:80ch;border-left:2px solid var(--red);padding-left:15px}
    .aftercare-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
    .aftercare-card{background:var(--white);border:1px solid rgba(185,20,43,.16);border-radius:var(--radius);padding:26px}
    .aftercare-card h3{margin:0 0 14px;font-size:19px;display:flex;align-items:center;gap:11px;letter-spacing:-.02em}
    .aftercare-card h3 span{font-size:10px;letter-spacing:.18em;color:#fff;background:var(--red);border-radius:999px;padding:5px 9px;font-weight:900}
    .aftercare-card ol{margin:0;padding-left:0;list-style:none;display:grid;gap:11px}
    .aftercare-card li{font-size:13.5px;line-height:1.6;color:#4b4644;padding-left:22px;position:relative}
    .aftercare-card li:before{content:"";position:absolute;left:0;top:8px;width:7px;height:7px;border-radius:2px;background:var(--red);transform:rotate(45deg)}
    .aftercare-card li b{color:var(--ink)}
    .aftercare-note{margin:24px 0 0;font-size:12.5px;line-height:1.6;color:#6f5a5e;max-width:86ch}
    .aftercare-note a{color:var(--red);font-weight:800;text-decoration:underline;text-underline-offset:3px}
    .faq-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;align-items:start}
    .faq-item{background:var(--white);border:1px solid var(--line);border-radius:16px;padding:0;overflow:hidden;transition:border-color .2s,box-shadow .2s}
    .faq-item[open]{border-color:rgba(185,20,43,.4);box-shadow:0 14px 34px rgba(15,11,11,.07)}
    .faq-item summary{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:17px 20px;cursor:pointer;list-style:none;font-size:14.5px;line-height:1.4;min-height:56px}
    .faq-item summary::-webkit-details-marker{display:none}
    .faq-item summary b{font-weight:800;letter-spacing:-.01em}
    .faq-item summary span{flex:0 0 auto;width:26px;height:26px;border-radius:50%;border:1px solid var(--line);display:grid;place-items:center;font-size:14px;color:var(--red);transition:transform .2s,background .2s}
    .faq-item[open] summary span{transform:rotate(45deg);background:var(--soft-red)}
    .faq-item p{margin:0;padding:0 20px 19px;font-size:13.5px;line-height:1.7;color:#57524f;max-width:62ch}
    .legal{padding:64px 0 74px;background:var(--ink);color:#cfc9c7}
    .legal-grid{display:grid;grid-template-columns:1fr 1fr;gap:34px}
    .legal h2{margin:0 0 13px;color:#fff;font-size:21px;letter-spacing:-.02em}
    .legal p{margin:0 0 13px;font-size:12.5px;line-height:1.75;color:#a8a2a0;max-width:70ch}
    .legal b{color:#fff}
    .legal code{background:rgba(255,255,255,.09);border-radius:5px;padding:2px 6px;font-size:11.5px;color:#ff8095}
    @media(max-width:900px){.pricing-grid{grid-template-columns:1fr 1fr}.aftercare-grid,.faq-grid,.legal-grid{grid-template-columns:1fr;gap:12px}}
    @media(max-width:600px){.pricing,.aftercare,.faq,.legal{padding:58px 0}.pricing-grid{grid-template-columns:1fr}.price-card{padding:20px}.price-card b{font-size:29px}.faq-item summary{padding:15px 16px;font-size:14px}.faq-item p{padding:0 16px 17px}.aftercare-card{padding:20px}}
  </style>''', 'content CSS')

# footer link to the new sections
rep('<a href="#lookbook">Lookbook</a><a href="#services">Services</a><a href="#shop">Shop</a><a href="#about">About Haywood</a>',
    '<a href="#lookbook">Lookbook</a><a href="#services">Services</a><a href="#pricing">Pricing</a><a href="#aftercare">Aftercare</a><a href="#shop">Shop</a><a href="#faq">FAQ</a><a href="#about">About Haywood</a><a href="#privacy">Privacy</a><a href="#terms">Terms</a>',
    'footer links')

P.write_text(s)
print(f'patched: {len(log)} edits')
for l in log:
    print('  ✓', l)
print('bytes', len(s.encode()))
