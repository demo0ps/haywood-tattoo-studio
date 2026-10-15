#!/usr/bin/env python3
"""Generate llms.txt (concise) + llms-full.txt (complete) from the page itself,
so the answer-engine files cannot drift from what is actually published."""
import re
from pathlib import Path

ROOT = Path('/home/user')
s = (ROOT / 'index.html').read_text()
SITE = re.search(r'<link rel="canonical" href="([^"]+)"', s).group(1).rstrip('/') + '/'


def clean(t):
    t = re.sub(r'<[^>]+>', ' ', t)
    for ent, ch in (('&amp;', '&'), ('&nbsp;', ' '), ('&lt;', '<'), ('&gt;', '>'), ('&#39;', "'")):
        t = t.replace(ent, ch)
    return re.sub(r'\s+', ' ', t).replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').strip()


def slice_section(anchor):
    i = s.index(anchor)
    return s[i:s.index('</section>', i)]


pricing = slice_section('id="pricing"')
faqsec = slice_section('id="faq"')
after = slice_section('id="aftercare"')

prices = []
for card in re.split(r'<div class="price-card', pricing)[1:]:
    lab = re.search(r'<span class="price-label">(.*?)</span>', card, re.S)
    val = re.search(r'<b>(.*?)</b>', card, re.S)
    txt = re.search(r'<p>(.*?)</p>', card, re.S)
    if lab and val and txt:
        prices.append((clean(lab.group(1)), clean(val.group(1)), clean(txt.group(1))))

faq = [(clean(a), clean(b)) for a, b in
       re.findall(r'<summary><b>(.*?)</b>.*?<p>(.*?)</p>', faqsec, re.S)]

services = [(clean(a), clean(b)) for a, b in
            re.findall(r'<div class="service-num">\d+</div><h3>(.*?)</h3><p>(.*?)</p>', s, re.S)]

book = [(clean(a), clean(b), clean(c)) for a, b, c in
        re.findall(r'<article class="look-card"[^>]*>.*?<h3>(.*?)</h3><div class="look-meta"><span>(.*?)</span><span class="look-price">(.*?)</span>', s, re.S)
        if '${' not in (a + b + c)]

sp = re.search(r"id:'spring-sitting'.*?title:'(.*?)',copy:'(.*?)'.*?value:(\d+).*?minQuote:(\d+).*?end:'(\d{4}-\d{2}-\d{2})'", s, re.S)

title = clean(re.search(r'<title>(.*?)</title>', s, re.S).group(1))
desc = clean(re.search(r'<meta name="description" content="(.*?)"', s).group(1))

assert len(prices) == 5 and len(faq) == 10 and len(services) == 3 and len(book) == 3, \
    f'extraction drift: prices={len(prices)} faq={len(faq)} services={len(services)} lookbook={len(book)}'

L = [f'# {title.split("|")[0].strip()}', '', f'> {desc}', '',
     'Private, by-appointment tattoo and piercing studio in central Pretoria, Gauteng, South Africa. '
     'One artist, no walk-ins. Sessions also run on location within roughly 30 km. '
     'Every price on this site is an **indicative range** built from the client brief — the artist confirms the final quote before a design is locked.',
     '', '## Contact and booking', '',
     '- WhatsApp / calls: 061 759 3378 (https://wa.me/27617593378)',
     '- Instagram: @haywood_studio (https://instagram.com/haywood_studio)',
     '- Website: ' + SITE,
     '- Location: Pretoria, South Africa. The exact studio address is private and is shared once a session is confirmed.',
     '- Hours: Tuesday to Saturday, by appointment only.',
     '- Age: 18 or older with a valid South African ID or passport, checked at the first session.',
     '', '## Services', '']
L += [f'- {n}: {b}' for n, b in services]
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
      '', '## Policies that shape a quote', '',
      '- Deposit: 30% of the lower end of the range, credited to the final price.',
      '- Cover-ups and touch-ups: subject to assessment from clear daylight photos.',
      '- Designs remain the artist\'s intellectual property; the tattoo belongs to the client.',
      '- Payments run through a hosted Yoco checkout; the studio never stores card data.',
      '', '## FAQ (full answers in llms-full.txt)', '']
L += [f'- {q}' for q, _ in faq]
L += ['', '## Files', '', f'- Page: {SITE}', f'- Full facts: {SITE}llms-full.txt',
      f'- Structured data: JSON-LD in the page head (TattooParlor with OfferCatalog, FAQPage, WebSite)', '']
llms = '\n'.join(L)
(ROOT / 'llms.txt').write_text(llms, encoding='utf-8')

F = [title, '================', '', f'Canonical URL: {SITE}',
     'Language: en-ZA · Currency: ZAR · Market: Pretoria, Gauteng, South Africa',
     'Business type: TattooParlor / piercing studio, private appointment, solo artist', '', llms.rstrip(),
     '', '## FAQ with answers', '']
for q, a in faq:
    F += [f'### {q}', '', a, '']
F += ['## Page structure', '',
      'hero + live special · lookbook · about · design concierge · services · pricing · aftercare · FAQ · shop (jewelry and aftercare) · privacy · terms', '',
      '## Note on this build', '',
      'This is a front-end prototype: prices, hours, lookbook projects and products are editable demo values held in the '
      'browser, the checkout is a Yoco test flow, and no live payment, email or WhatsApp API call is made. '
      'Quote the studio facts, not the demo state.']
(ROOT / 'llms-full.txt').write_text('\n'.join(F) + '\n', encoding='utf-8')

print(f'llms.txt      {len(llms)/1024:5.1f} KB · prices={len(prices)} faq={len(faq)} services={len(services)} lookbook={len(book)}')
print(f'llms-full.txt {len("\n".join(F))/1024:5.1f} KB')
bad = [l for l in llms.split('\n') if len(l) > 400]
print('over-long lines (extraction leak):', len(bad))
