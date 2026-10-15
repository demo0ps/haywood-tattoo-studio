#!/usr/bin/env python3
"""Mobile pass: working hamburger nav, sticky conversion bar, thumb targets,
safe-area insets, and a Studio OS that can actually be driven from a phone."""
from pathlib import Path

P = Path('/home/user/index.html')
s = P.read_text()
log = []


def rep(old, new, label, count=1):
    global s
    assert old in s, f'ANCHOR MISSING: {label} :: {old[:70]!r}'
    s = s.replace(old, new, count)
    log.append(label)


# ── 1. base / document level ─────────────────────────────────────────────────
rep('html{scroll-behavior:smooth}',
    'html{scroll-behavior:smooth;scroll-padding-top:96px}\n'
    '    main>section{scroll-margin-top:96px}\n'
    '    body{-webkit-text-size-adjust:100%}\n'
    '    button,a,summary,input,select,textarea{touch-action:manipulation}',
    'scroll padding + touch action')

# ── 2. mobile nav sheet + sticky bar markup ─────────────────────────────────
rep('  </header>\n',
    '''  </header>
  <div class="mobile-nav" id="mobileNav" aria-label="Site sections">
    <div class="mobile-nav-inner"><nav class="mobile-nav-links">
      <a href="#lookbook"><b>Lookbook</b><span>Artist-led pieces, ready or adaptable</span></a>
      <a href="#services"><b>Services</b><span>Custom tattoo, piercing, mobile sessions</span></a>
      <a href="#pricing"><b>Pricing</b><span>How a quote is built, in rand</span></a>
      <a href="#aftercare"><b>Aftercare</b><span>Healing a fresh tattoo or piercing</span></a>
      <a href="#shop"><b>Shop</b><span>Jewelry and aftercare essentials</span></a>
      <a href="#faq"><b>FAQ</b><span>Deposits, age, cover-ups, booking</span></a>
      <a href="#about"><b>About</b><span>The Haywood difference</span></a>
    </nav><div class="mobile-nav-actions">
      <button class="btn btn-red" data-action="open-estimate">Start a brief ↗</button>
      <a class="btn btn-light" href="https://wa.me/27617593378" target="_blank" rel="noopener">WhatsApp 061 759 3378</a>
    </div></div>
  </div>
''', 'mobile nav sheet markup')

rep('<button class="menu-btn" data-action="mobile-menu" aria-label="Open menu">☰</button>',
    '<button class="menu-btn" data-action="mobile-menu" aria-expanded="false" aria-controls="mobileNav" aria-label="Open menu"><span class="menu-icon" aria-hidden="true"></span></button>',
    'hamburger button')

rep('<button class="mascot-btn"',
    '''<div class="mobile-bar" role="navigation" aria-label="Quick actions">
    <a class="mb-btn" href="https://wa.me/27617593378" target="_blank" rel="noopener"><span aria-hidden="true">✆</span>WhatsApp</a>
    <button class="mb-btn primary" data-action="open-estimate"><span aria-hidden="true">↗</span>Book a session</button>
  </div>

  <button class="mascot-btn"''', 'sticky mobile bar')

# ── 3. admin: sidebar opener + backdrop (there was no way to open it on a phone) ─
rep('<div class="studio-top-actions">',
    '<button class="btn btn-light btn-sm admin-menu-btn" data-action="open-sidebar" aria-controls="studioSide" aria-expanded="false"><span aria-hidden="true">☰</span>Sections</button><div class="studio-top-actions">',
    'admin sidebar opener')
rep('<aside class="studio-side" id="studioSide">',
    '<div class="studio-backdrop" data-action="close-sidebar" aria-hidden="true"></div><aside class="studio-side" id="studioSide">',
    'admin backdrop')

# ── 4. JS wiring ─────────────────────────────────────────────────────────────
rep("function openOverlay(id){$(id).classList.add('open');document.body.style.overflow='hidden'}\n"
    "    function closeOverlays(){ $$('.overlay').forEach(x=>x.classList.remove('open'));document.body.style.overflow=''}",
    "function openOverlay(id){$(id).classList.add('open');document.body.style.overflow='hidden';document.body.classList.add('overlay-open')}\n"
    "    function closeOverlays(){ $$('.overlay').forEach(x=>x.classList.remove('open'));document.body.style.overflow='';document.body.classList.remove('overlay-open')}\n"
    "    function setMobileNav(on){const m=document.getElementById('mobileNav');const b=document.querySelector('[data-action=\"mobile-menu\"]');if(!m)return;m.classList.toggle('open',on);document.body.classList.toggle('nav-open',on);if(b){b.setAttribute('aria-expanded',on?'true':'false');b.classList.toggle('is-open',on)}}\n"
    "    function toggleAdminNav(on){const side=document.getElementById('studioSide');if(!side)return;const want=on==null?!side.classList.contains('open'):on;side.classList.toggle('open',want);document.body.classList.toggle('admin-nav-open',want);const btn=document.querySelector('[data-action=\"open-sidebar\"]');if(btn)btn.setAttribute('aria-expanded',want?'true':'false')}",
    'nav + sidebar controllers')

rep("if(action==='close-sidebar')$('#studioSide').classList.remove('open');",
    "if(action==='close-sidebar')toggleAdminNav(false);if(action==='open-sidebar')toggleAdminNav(true);"
    "if(action==='mobile-menu'){const m=document.getElementById('mobileNav');setMobileNav(!(m&&m.classList.contains('open')))}"
    "if(action==='open-estimate'||action==='book-piercing'){setMobileNav(false)}",
    'nav actions wired')

rep("document.querySelectorAll('a[href^=\"#\"]').forEach(a=>a.addEventListener('click',()=>$('#cartDrawer').classList.remove('open')));",
    "document.querySelectorAll('a[href^=\"#\"]').forEach(a=>a.addEventListener('click',()=>{$('#cartDrawer').classList.remove('open');setMobileNav(false);toggleAdminNav(false)}));\n"
    "    document.addEventListener('keydown',e=>{if(e.key==='Escape'){setMobileNav(false);toggleAdminNav(false);closeOverlays()}});",
    'close on anchor + Escape')

rep("if(window.innerWidth<901)$('#studioSide').classList.remove('open')",
    "if(window.innerWidth<901)toggleAdminNav(false)", 'tab click closes admin nav')

# cart drawer also hides the sticky bar while open
rep("if(action==='open-cart'){$('#cartDrawer').classList.add('open');renderCart()}if(action==='close-cart')$('#cartDrawer').classList.remove('open');",
    "if(action==='open-cart'){$('#cartDrawer').classList.add('open');document.body.classList.add('overlay-open');renderCart()}if(action==='close-cart'){$('#cartDrawer').classList.remove('open');document.body.classList.remove('overlay-open')}",
    'cart drawer body class')

# ── 5. mobile CSS ────────────────────────────────────────────────────────────
rep('  </style>', '''
    /* ── mobile: nav sheet, sticky bar, thumb targets, Studio OS ─────── */
    .menu-icon{position:relative;display:block;width:17px;height:2px;background:currentColor;border-radius:2px;transition:transform .2s,background .2s}
    .menu-icon:before,.menu-icon:after{content:"";position:absolute;left:0;width:17px;height:2px;background:currentColor;border-radius:2px;transition:transform .2s,opacity .2s}
    .menu-icon:before{top:-6px}.menu-icon:after{top:6px}
    .menu-btn.is-open .menu-icon{background:transparent}
    .menu-btn.is-open .menu-icon:before{transform:translateY(6px) rotate(45deg)}
    .menu-btn.is-open .menu-icon:after{transform:translateY(-6px) rotate(-45deg)}
    .mobile-nav{display:grid;grid-template-rows:0fr;transition:grid-template-rows .28s cubic-bezier(.4,0,.2,1);background:linear-gradient(180deg,#0d0d0f,#1a1214);border-bottom:1px solid rgba(255,255,255,.08)}
    .mobile-nav.open{grid-template-rows:1fr}
    .mobile-nav>*{overflow:hidden;min-height:0}
    .mobile-nav-inner{padding:0 20px}
    .mobile-nav.open .mobile-nav-inner{padding:16px 20px 20px}
    .mobile-nav-links{display:grid}
    .mobile-nav-links a{display:flex;flex-direction:column;gap:3px;padding:13px 2px;border-bottom:1px solid rgba(255,255,255,.08);color:#fff;text-decoration:none}
    .mobile-nav-links a b{font-size:14px;letter-spacing:.04em;text-transform:uppercase}
    .mobile-nav-links a span{font-size:11.5px;color:#a29c9a;line-height:1.4}
    .mobile-nav-actions{display:grid;gap:9px;margin-top:16px}
    .mobile-nav-actions .btn{width:100%;min-height:47px}
    .mobile-bar{position:fixed;left:0;right:0;bottom:0;z-index:18;display:none;gap:9px;padding:9px 14px calc(9px + env(safe-area-inset-bottom));background:rgba(13,13,15,.94);backdrop-filter:blur(16px);border-top:1px solid rgba(255,255,255,.1);box-shadow:0 -14px 40px rgba(0,0,0,.34);transition:transform .2s,opacity .2s}
    .mb-btn{flex:1 1 0;display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:47px;border-radius:14px;font-size:12px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;color:#fff;background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.16)}
    .mb-btn.primary{background:var(--red);border-color:var(--red);box-shadow:0 10px 26px rgba(214,0,0,.34)}
    .mb-btn span{font-size:15px}
    body.overlay-open .mobile-bar,body.nav-open .mobile-bar{transform:translateY(115%);opacity:0;pointer-events:none}
    .admin-menu-btn{display:none}
    .studio-backdrop{display:none;position:fixed;inset:0;background:rgba(4,3,4,.6);z-index:4}
    @media(max-width:900px){.mobile-nav{position:sticky;top:77px;z-index:19}}
    .studio-backdrop.show{display:block}
    @media(max-width:900px){
      .admin-menu-btn{display:inline-flex;align-items:center;gap:7px;min-height:40px;padding:9px 14px;font-size:10.5px}
      .studio-side{box-shadow:24px 0 60px rgba(0,0,0,.5);width:min(280px,86vw)}
      body.admin-nav-open .studio-backdrop{display:block}
      .studio-nav button{min-height:44px;font-size:12.5px}
      .modal{max-height:none;height:100dvh}
      .studio-shell{min-height:100dvh}
    }
    @media(max-width:600px){
      .hero h1{font-size:clamp(36px,11.4vw,57px);letter-spacing:-.05em}
      .hero{padding:46px 0 44px}
      .hero-copy{font-size:14.5px;margin-bottom:4px}
      .hero-actions{flex-direction:column;align-items:stretch;gap:10px}
      .hero-actions .btn{width:100%;min-height:48px;font-size:11.5px}
      .hero-offer{margin-top:22px;padding:15px 16px;gap:12px;border-radius:15px}
      .offer-title{font-size:17px}
      .offer-copy{font-size:12.5px}
      .offer-side{grid-template-columns:1fr 1fr;align-items:center;gap:8px}
      .offer-side .btn{grid-column:1/-1}
      .section-head h2{font-size:clamp(29px,8.6vw,43px);letter-spacing:-.04em}
      .btn{min-height:46px;padding:14px 18px}
      .icon-btn,.menu-btn{width:44px;height:44px}
      .service,.look-card,.product{scroll-margin-top:20px}
      .service button,.look-link,.product-row .btn{min-height:44px}
      .product-grid{grid-template-columns:1fr 1fr;gap:10px}
      .product-row{flex-wrap:wrap}
      .field label{font-size:11.5px}
      input,select,textarea{font-size:16px}
      .faq-item summary{min-height:52px}
      .mascot-btn{right:14px;bottom:calc(76px + env(safe-area-inset-bottom));width:56px;height:56px;border-width:2px}
      .mascot-btn picture,.mascot-btn img{width:100%;height:100%;border-radius:50%;object-fit:cover}
      .mobile-bar{display:flex}
      body{padding-bottom:calc(65px + env(safe-area-inset-bottom))}
      .mobile-nav{top:67px}
      .modal{border-radius:0}
      .chat{max-height:min(48dvh,340px)}
      .admin-kpis{grid-template-columns:1fr}
      .admin-card{padding:15px;border-radius:13px}
      .studio-content{padding:15px 13px}
      .studio-topbar{padding:0 13px;gap:11px}
      .studio-topbar h2{font-size:17px}
      .studio-top-actions{gap:7px}
      .admin-list-row{flex-direction:column;align-items:stretch;gap:10px;padding:14px}
      .admin-list-row>div:last-child,.special-actions{justify-content:flex-start}
      .special-actions .btn{flex:1 1 auto;min-height:42px;font-size:10.5px;padding:10px 12px}
      .admin-list-row b{font-size:14px}
      .admin-card-head{flex-direction:column;align-items:flex-start;gap:11px}
      .admin-card-head .btn{width:100%}
      .dashboard-mobile-close{width:44px;height:44px;right:10px;top:12px;font-size:24px}
      .check-row{font-size:14px;line-height:1.5}
      .topline{padding:8px 14px;line-height:1.5;padding-top:calc(8px + env(safe-area-inset-top))}
      header{padding-top:env(safe-area-inset-top)}
      .cart-drawer{padding:18px 16px calc(18px + env(safe-area-inset-bottom))}
      .marquee-track{animation-duration:38s}
    }
    @media(max-width:600px) and (hover:none){
      .look-card:hover,.service:hover,.product:hover{transform:none}
      .btn:active{transform:scale(.975)}
      .faq-item summary:active{background:rgba(185,20,43,.05)}
    }
    @media(prefers-reduced-motion:reduce){
      html{scroll-behavior:auto}
      *,*:before,*:after{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important}
      .marquee-track{animation:none}
    }
  </style>''', 'mobile CSS')

# hero-art responsive background swap
rep('@media(max-width:900px){.navlinks{display:none}',
    '@media(max-width:900px){.hero-art{background-image:linear-gradient(180deg,rgba(8,7,8,.2),rgba(8,7,8,.8)),url(\'assets/haywood-hero-800.jpg\')}}\n'
    '    @media(max-width:900px){.navlinks{display:none}', 'mobile hero bg')

P.write_text(s)
print(f'patched: {len(log)} edits')
for l in log:
    print('  ✓', l)
