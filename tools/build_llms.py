#!/usr/bin/env python3
"""Generate llms.txt (concise) + llms-full.txt (complete) from the page itself,
so the answer-engine files cannot drift from what is actually published.

Every block is extracted with a bounded slice + a count assertion, because an
unbounded regex once swallowed 26 KB of the page into llms.txt.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
s = (ROOT / 'index.html').read_text()
SITE = re.search(r'<link rel="canonical" href="([^"]+)"', s).group(1).rstrip('/') + '/'


def clean(t):
    t = re.sub(r'<[^>]+>', ' ', t)
    for ent, ch in (('&amp;', '&'), ('&nbsp;', ' '), ('&lt;', '<'), ('&gt;', '>'), ('&#39;', "'"),
                    ('&rsquo;', "'"), ('&ldquo;', '"'), ('&rdquo;', '"')):
        t = t.replace(ent, ch)
    return re.sub(r'\s+', ' ', t).replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').strip()


def slice_section(anchor):
    i = s.index(anchor)
    end = s.index('</section>', i)
    seg = s[i:end]
    assert seg.count('<section') <= 1, f'section slice over-ran for {anchor}'
    return seg


# ---------------------------------------------------------------- pricing cards
pricing = slice_section('id="pricing"')
prices = []
for card in re.split(r'<div class="price-card', pricing)[1:]:
    lab = re.search(r'<span class="price-label">(.*?)</span>', card, re.S)
    val = re.search(r'<b>(.*?)</b>', card, re.S)
    txt = re.search(r'<p>(.*?)</p>', card, re.S)
    if lab and val and txt:
        prices.append((clean(lab.group(1)), clean(val.group(1)), clean(txt.group(1))))

# ------------------------------------------------------------------------- faq
faqsec = slice_section('id="faq"')
faq = [(clean(a), clean(b)) for a, b in
       re.findall(r'<summary><b>(.*?)</b>.*?<p>(.*?)</p>', faqsec, re.S)]

# -------------------------------------------------------------------- services
services = [(clean(a), clean(b)) for a, b in
            re.findall(r'<div class="service-num">\d+</div><h3>(.*?)</h3><p>(.*?)</p>', s, re.S)]

# --------------------------------------------------------------------- lookbook
book = [(clean(a), clean(b), clean(c)) for a, b, c in
        re.findall(r'<article class="look-card"[^>]*>.*?<h3>(.*?)</h3><div class="look-meta"><span>(.*?)</span><span class="look-price">(.*?)</span>', s, re.S)
        if '${' not in (a + b + c)]

# --------------------------------------------------------------------- branch data
visit = slice_section('id="visit"')
branches = []
for card in re.split(r'<article class="visit-card', visit)[1:]:
    name = clean(re.search(r'<h3>(.*?)</h3>', card, re.S).group(1))
    addr = clean(re.search(r'<p class="visit-addr">(.*?)</p>', card, re.S).group(1))
    hours = [(clean(a), clean(b)) for a, b in re.findall(r'<li[^>]*><span>(.*?)</span><i>(.*?)</i></li>', card, re.S)]
    meta = re.search(r'<div class="visit-meta">(.*?)</div>', card, re.S)
    amenities = [clean(x) for x in re.findall(r'<span>(.*?)</span>', meta.group(1))] if meta else []
    caveat = re.search(r'<p class="visit-hours-note">(.*?)</p>', card, re.S)
    branches.append({'name': name, 'addr': addr, 'hours': hours, 'amenities': amenities,
                     'caveat': clean(caveat.group(1)) if caveat else ''})

rating = {'score': clean(re.search(r'id="ratingScore">(.*?)<', s).group(1)),
          'meta': clean(re.search(r'id="ratingMeta">(.*?)</span>', s).group(1))}

# ------------------------------------------------------------------- friday card
fridays = slice_section('id="fridays"')
fri_title = clean(re.search(r'id="friTitle">(.*?)</h3>', fridays, re.S).group(1))
fri_copy = clean(re.search(r'id="friCopy">(.*?)</p>', fridays, re.S).group(1))
fri_price = clean(re.search(r'id="friPrice">(.*?)</b>', fridays, re.S).group(1))
fri_svc = clean(re.search(r'id="friServices">(.*?)</p>', fridays, re.S).group(1))
fri_perk = clean(re.search(r'id="friPerk">(.*?)</p>', fridays, re.S).group(1))
fri_terms = clean(re.search(r'id="friFine">(.*?)</p>', fridays, re.S).group(1))

# ---------------------------------------------------------------- live special
sp = re.search(r"id:'spring-sitting'.*?title:'(.*?)',copy:'(.*?)'.*?value:(\d+).*?minQuote:(\d+).*?end:'(\d{4}-\d{2}-\d{2})'", s, re.S)
studio = re.search(r"legalName:'(.*?)',phone", s)

title = clean(re.search(r'<title>(.*?)</title>', s, re.S).group(1))
desc = clean(re.search(r'<meta name="description" content="(.*?)"', s).group(1))

# ------------------------------------------------------------- shop + delivery
shopsec = slice_section('id="shop"')
shelf = []
for art in re.split(r'<article class="product"', shopsec)[1:]:
    nm = re.search(r'<h3>(.*?)</h3>', art, re.S)
    pr = re.search(r'<span>(.*?)</span>', art, re.S)
    if nm and pr:
        shelf.append((clean(nm.group(1)), clean(pr.group(1))))
ship = re.search(r"shipping:\{courier:'([^']*)',fee:(\d+),freeOver:(\d+),eta:'([^']*)'", s)
assert len(shelf) == 4 and ship, f'shop drift: shelf={len(shelf)} ship={bool(ship)}'

assert len(prices) == 5 and len(faq) == 14 and len(services) == 3 and len(book) == 3, \
    f'extraction drift: prices={len(prices)} faq={len(faq)} services={len(services)} lookbook={len(book)}'
assert len(branches) == 2 and all(len(b['hours']) == 4 for b in branches), \
    f'visit drift: branches={len(branches)} hours={[len(b["hours"]) for b in branches]}'
assert len(book) == 3 and re.search(r'id="faq"', s) and 'aggregateRating' not in s.split('<script type="application/ld+json">')[1].split('</script>')[0], \
    'a rating leaked into structured data'

L = [f'# {title.split("|")[0].strip()}', '', f'> {desc}', '',
     'Private tattoo and piercing studio trading as **Haywood Tattoos and Piercings**, with a flagship in '
     'Pretoria Central and a second studio in Mabopane, Gauteng, South Africa.',
     'Custom work is quoted as an **indicative range** built from the client brief — the artist confirms the '
     'final quote before a design is locked.',
     'Tattoo sessions run by appointment; standard piercings can sometimes be taken as a walk-in when a slot '
     'is open (most likely on a Friday).',
     '', '## Contact and booking', '',
     '- WhatsApp / calls: 061 759 3378 (https://wa.me/27617593378)',
     '- Instagram: @haywood_studio (https://instagram.com/haywood_studio)']
if studio:
    L += [f'- Trading name: {studio.group(1)} · website www.haywoodstudio.com']
L += ['- Booking site: ' + SITE,
      '- Age: 18 or older with a valid South African ID or passport, checked at the first session. Minors need a parent or guardian for piercings.',
      '- Reputation: ' + rating['score'] + ' stars, ' + re.sub(r'^from\\s+', '', rating['meta']) + ' (reported by clients on Google; shown as copy, not as a structured-data claim).',
      '', '## Locations and hours', '']
for b in branches:
    L += [f'- {b["name"]}: {b["addr"]}']
    L += [f'  - {lbl} {txt}' for lbl, txt in b['hours']]
    if b['amenities']:
        L += ['  - Amenities: ' + ', '.join(b['amenities'])]
    if b['caveat']:
        L += ['  - ' + b['caveat']]
L += ['', '## Services', '']
L += [f'- {n}: {b}' for n, b in services]
L += ['', '## Piercing Fridays (standing weekly rate)', '',
      f'- {fri_title}: {fri_copy}',
      f'- Rate: {fri_price} · eligible: {fri_svc}',
      f'- {fri_perk}',
      f'- Conditions: {fri_terms}']
L += ['', '## Indicative pricing', '']
L += [f'- {lab}: {val} — {txt}' for lab, val, txt in prices]
if sp:
    L += ['', '## Live studio special', '',
          f'- {sp.group(1)}: {sp.group(2)} '
          f'({sp.group(3)}% off quotes from R{sp.group(4)}, running until {sp.group(5)}). '
          'Applied automatically to the indicative range; still confirmed by the artist.']
L += ['', '## Lookbook (ready or adaptable artwork)', '']
L += [f'- {n} — {k}, {p}' for n, k, p in book]
L += ['', '## Aftercare (general guidance, not medical advice)', '',
      '- Fresh tattoo: covering off after 3–5 hours, gentle wash twice daily, thin moisturiser for about two weeks, no picking, no swimming or direct sun for six weeks, SPF 50 once healed.',
      '- Fresh piercing: sterile saline once or twice daily, do not twist or remove jewelry, avoid friction, no swimming during healing. Lobes around 6 weeks, cartilage 3–9 months.',
      '- The studio does not diagnose or treat infections or reactions — anyone concerned should see a clinician.',
      '', '## Shop, delivery & collection', '',
      '- On the shelf: ' + '; '.join(f'{n} {p}' for n, p in shelf) + '.',
      f'- Courier nationwide via {ship.group(1)}: R{int(ship.group(2)):,} flat, free over '
      f'R{int(ship.group(3)):,}, usually {ship.group(4)}.',
      '- Collection is free at either studio and can be timed with an appointment.',
      '- The studio confirms the delivery address and the contents before dispatch.',
      '', '## Policies that shape a quote', '',
      '- Deposit: 30% of the lower end of the range, credited to the final price.',
      '- Cover-ups and touch-ups: subject to assessment from clear daylight photos.',
      '- Designs remain the artist\'s intellectual property; the tattoo belongs to the client.',
      '- Payments run through a hosted Yoco checkout; the studio never stores card data. Cards, debit and mobile pay are accepted at both locations.',
      '', '## FAQ (full answers in llms-full.txt)', '']
L += [f'- {q}' for q, _ in faq]
L += ['', '## Files', '', f'- Page: {SITE}', f'- Full facts: {SITE}llms-full.txt',
      '- Locations and hours are also in the page as JSON-LD `openingHoursSpecification`, one set per branch.',
      f'- Structured data: JSON-LD in the page head (TattooParlor with OfferCatalog, FAQPage, WebSite)', '']
llms = '\n'.join(L)
(ROOT / 'llms.txt').write_text(llms, encoding='utf-8')

F = [title, '================', '', f'Canonical URL: {SITE}',
     'Language: en-ZA · Currency: ZAR · Market: Pretoria / Tshwane, Gauteng, South Africa',
     'Business type: TattooParlor + piercing studio · private studio · resident artist (Yuran)', '', llms.rstrip(),
     '', '## Studio locations (full)', '']
for b in branches:
    F += [f'### {b["name"]}', '', b['addr'], '']
    for lbl, txt in b['hours']:
        F += [f'- {lbl}: {txt}']
    F += ['', f'- Amenities: {", ".join(b["amenities"]) or "not listed"}', '']
F += ['## Shop (jewelry and aftercare)', '']
for n, pr in shelf:
    F += [f'- {n}: {pr}']
F += ['', f'- Delivery: {ship.group(1)}, R{int(ship.group(2)):,} flat, free over R{int(ship.group(3)):,}, '
      f'usually {ship.group(4)}.', '- Collection: free at either branch, timed with the appointment.', '',
      '## Piercing Fridays', '', fri_copy, '', f'- Rate: {fri_price} · eligible: {fri_svc}',
      f'- {fri_perk}', f'- Conditions: {fri_terms}', '', '## FAQ with answers', '']
for q, a in faq:
    F += [f'### {q}', '', a, '']
F += ['## Page structure', '',
      'hero + live offer · lookbook · about · design concierge · services · Piercing Fridays · pricing · '
      'aftercare · visit (locations, hours, artists, reputation) · FAQ · shop (jewelry, aftercare, delivery '
      'and collection) · privacy · terms', '',
      '## Note on this build', '',
      'This is a front-end prototype: prices, hours, lookbook projects and products are editable demo values held in the '
      'browser, the checkout is a Yoco test flow, and no live payment, email or WhatsApp API call is made. '
      'Quote the studio facts, not the demo state. Mabopane hours are flagged as indicative on the page.']
(ROOT / 'llms-full.txt').write_text('\n'.join(F) + '\n', encoding='utf-8')

print(f'llms.txt      {len(llms)/1024:5.1f} KB · prices={len(prices)} faq={len(faq)} services={len(services)} '
      f'lookbook={len(book)} branches={len(branches)}')
print(f'llms-full.txt {len(chr(10).join(F))/1024:5.1f} KB')
bad = [l for l in llms.split('\n') if len(l) > 400]
print('over-long lines (extraction leak):', len(bad))
for name in ('aggregateRating', 'apiKey', 'smtp', 'localStorage'):
    if name in llms:
        raise SystemExit(f'SECRET/DRIFT LEAK into llms.txt: {name}')
print('leak check: clean')
