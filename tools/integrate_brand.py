#!/usr/bin/env python3
"""Wire the extracted Haywood mark into index.html: icons, social meta, brand marks."""
from pathlib import Path

P = Path('/home/user/index.html')
s = P.read_text()
orig = s
SITE = "https://demo0ps.github.io/haywood-tattoo-studio/"
n = 0


def sub(old, new, count=1):
    global s, n
    assert old in s, f"NOT FOUND: {old[:90]}"
    s = s.replace(old, new, count)
    n += 1


# ------------------------------------------------------------------ head meta --
anchor = '  <meta name="theme-color" content="#b9142b" />\n  <title>Haywood Tattoo Studio — Custom artwork. Private sessions.</title>\n'
meta = anchor + f'''  <link rel="canonical" href="{SITE}" />
  <link rel="icon" type="image/png" sizes="32x32" href="assets/favicon-32.png" />
  <link rel="icon" type="image/png" sizes="48x48" href="assets/favicon-48.png" />
  <link rel="icon" type="image/png" sizes="64x64" href="assets/favicon-64.png" />
  <link rel="apple-touch-icon" sizes="180x180" href="assets/apple-touch-icon.png" />
  <meta name="description" content="Haywood Tattoo Studio - premium custom tattooing, piercing and private aftercare in Pretoria. Design concierge, transparent indicative pricing, studio or mobile sessions. WhatsApp 061 759 3378." />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Haywood Tattoo Studio" />
  <meta property="og:locale" content="en_ZA" />
  <meta property="og:url" content="{SITE}" />
  <meta property="og:title" content="Haywood Tattoo Studio - Custom artwork. Private sessions." />
  <meta property="og:description" content="Premium custom tattooing and piercing in Pretoria. Bring a reference, get an indicative range, book a private or mobile session." />
  <meta property="og:image" content="{SITE}assets/og-image.png" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:image:alt" content="Haywood gothic H mark on deep red, with the studio wordmark" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="Haywood Tattoo Studio - Custom artwork. Private sessions." />
  <meta name="twitter:description" content="Premium custom tattooing and piercing in Pretoria. Studio or mobile sessions, private bookings." />
  <meta name="twitter:image" content="{SITE}assets/og-image.png" />
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"TattooParlor","name":"Haywood Tattoo Studio","url":"{SITE}","image":"{SITE}assets/og-image.png","description":"Premium custom tattooing, piercing and private aftercare in Pretoria, South Africa. Sessions are by appointment, in studio or on location.","telephone":"+27617593378","address":{{"@type":"PostalAddress","addressLocality":"Pretoria","addressRegion":"Gauteng","addressCountry":"ZA"}},"areaServed":"Pretoria and surrounds","sameAs":["https://instagram.com/haywood_studio"]}}
  </script>
'''
sub(anchor, meta)
# NOTE: deliberately no streetAddress - the studio address is private / by appointment.

# ----------------------------------------------------------------- brand img --
sub('.brand svg{width:42px;height:52px}',
    '.brand svg{width:42px;height:52px}.brand .brand-mark{width:44px;height:44px;border-radius:10px;display:block;box-shadow:0 6px 18px rgba(15,11,11,.18)}')
sub('.brand svg{width:34px}', '.brand svg{width:34px}.brand .brand-mark{width:34px;height:34px}')
sub('.studio-brand-mark{width:38px;height:45px;border:1px solid rgba(255,78,105,.65);border-radius:11px;display:grid;place-items:center;color:#ff4e69;font-family:Georgia;font-size:27px}',
    '.studio-brand-mark{width:42px;height:42px;border:1px solid rgba(255,78,105,.65);border-radius:11px;display:grid;place-items:center;color:#ff4e69;font-family:Georgia;font-size:27px;object-fit:cover}')

import re
IMG = '<img class="brand-mark" src="assets/haywood-badge.svg" width="44" height="44" alt="" aria-hidden="true" />'
s, k = re.subn(r'<svg viewBox="0 0 60 72" aria-hidden="true">.*?</svg>', IMG, s, flags=re.S)
print(f"brand marks replaced: {k}")
assert k == 2, f"expected 2 brand marks, got {k}"

s, k2 = re.subn(r'<div class="studio-brand-mark">H</div>',
                '<img class="studio-brand-mark" src="assets/haywood-badge.png" width="42" height="42" alt="" aria-hidden="true" />',
                s)
print(f"studio OS mark replaced: {k2}")
assert k2 == 1

P.write_text(s)
print(f"applied {n} replacements, {len(orig)} -> {len(s.encode())} bytes "
      f"({len(s.encode())-len(orig):+d})")
