#!/usr/bin/env python3
"""patch_research2.py — public markup, admin panels, renderers, FAQ and schema
for the researched studio facts (2 branches, real hours, Piercing Fridays,
Yuran, 4.9/100+ Google reviews as copy only).

Same engine as patch_research.py: idempotent stages, asserted anchors, and
index.html is only written if every edit applied cleanly.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
STATE = ROOT / "tools" / ".research-state2.json"

# ------------------------------------------------------------------ fragments
VISIT_HTML = """<section class="visit" id="visit"><div class="container"><div class="section-head"><div><div class="eyebrow">Where and when</div><h2>Two <span class="serif">locations.</span></h2></div><p>A flagship private studio in Pretoria Central and a second room in Mabopane. Both take custom tattoo work and piercings; hours below are the real book.</p></div><div class="visit-grid" id="visitGrid"><article class="visit-card is-flagship" data-branch="central"><div class="visit-head"><div><h3>Pretoria Central</h3><span class="visit-tag">Flagship · private studio</span></div><span class="visit-flag">Flagship</span></div><p class="visit-addr">296 Francis Baard Street, Pretoria Central, Pretoria, Gauteng</p><p class="visit-note">Walk-ins are sometimes accommodated for standard services, but appointments are recommended — the book is busy.</p><div class="visit-hours"><b>Opening hours</b><ul><li><span>Mon–Wed</span><i>10:00–18:00</i></li><li><span>Thu</span><i>10:00–17:00</i></li><li><span>Fri–Sat</span><i>10:00–18:00</i></li><li><span>Sun</span><i>11:00–17:00</i></li></ul></div><div class="visit-meta"><span>On-site parking</span><span>Wheelchair-accessible parking</span><span>Credit, debit &amp; mobile pay</span></div><div class="visit-foot"><a class="btn btn-ghost" href="https://www.google.com/maps/search/?api=1&amp;query=296+Francis+Baard+Street%2C+Pretoria+Central" target="_blank" rel="noopener noreferrer">Directions <span aria-hidden="true">↗</span></a><button class="btn btn-dark" data-action="book-branch" data-branch="central">Book here</button></div></article><article class="visit-card" data-branch="mabopane"><div class="visit-head"><div><h3>Mabopane</h3><span class="visit-tag">North location</span></div></div><p class="visit-addr">2241 Martha Modise Street, Mabopane, Tshwane, Gauteng</p><p class="visit-note">Same artists, same setup. Confirm your slot before you travel.</p><div class="visit-hours"><b>Opening hours</b><ul><li><span>Mon–Wed</span><i>10:00–18:00</i></li><li><span>Thu</span><i>10:00–17:00</i></li><li><span>Fri–Sat</span><i>10:00–18:00</i></li><li data-closed><span>Sun</span><i>Closed</i></li></ul><p class="visit-hours-note">Indicative — confirm your slot on WhatsApp.</p></div><div class="visit-meta"><span>Street parking</span><span>Credit &amp; debit cards</span></div><div class="visit-foot"><a class="btn btn-ghost" href="https://www.google.com/maps/search/?api=1&amp;query=2241+Martha+Modise+Street%2C+Mabopane" target="_blank" rel="noopener noreferrer">Directions <span aria-hidden="true">↗</span></a><button class="btn btn-dark" data-action="book-branch" data-branch="mabopane">Book here</button></div></article></div><div class="visit-aside"><div class="rating-card" id="ratingCard"><span class="rating-stars" aria-hidden="true">★★★★★</span><b id="ratingScore">4.9</b><span id="ratingMeta">from 100+ Google reviews</span><p id="ratingQuote">“Exceptional care, spotless setup, and the design still looks sharper than the day I got it.”</p><a id="ratingLink" href="#" hidden>Read the reviews <span aria-hidden="true">↗</span></a></div><div class="artist-list" id="artistList"><article class="artist-card"><b>Yuran</b><span>Resident artist · Pretoria Central</span><p>Black &amp; grey · Fine line · Portraits · Full sleeves · Cover-ups · Abstract line art</p><p class="artist-bio">Ten-plus years of bespoke work, known for soft shading and line control on larger pieces.</p></article></div></div></div></section>

    """

FRIDAY_HTML = """<section class="fridays" id="fridays"><div class="container"><div class="friday-band" id="fridayBand"><div class="friday-main"><span class="friday-flag" id="friFlag">Every Friday</span><h3 id="friTitle">Piercing Fridays</h3><p id="friCopy">Selected nose, ear lobe and belly piercings at the Friday rate — R100 to R150, between 10:00 and 15:00. Appointment only, capped at 20 slots.</p><p class="friday-fine" id="friFine">Selected nose, ear and belly piercings at the Friday rate · appointment only, capped per session · jewelry subject to stock · 18+ with valid ID or guardian consent · the artist confirms the price at the chair</p></div><div class="friday-side"><div class="friday-price"><span>Friday rate</span><b id="friPrice">R100–R150</b></div><p class="friday-when" id="friWhen">Next Friday in 0 days · 10:00–15:00</p><p class="friday-svc" id="friServices">Nose · Ear lobe · Belly</p><button class="btn btn-red" data-action="book-piercing">Claim a Friday slot <span aria-hidden="true">↗</span></button><p class="friday-perk" id="friPerk">Weekend perk: book a piercing on Saturday or Sunday and a temporary tooth gem is on the studio — subject to stock and artist sign-off.</p></div></div></div></section>

    """

HELPERS = """function renderVisit(){const grid=document.getElementById('visitGrid');if(!grid)return;
    grid.innerHTML=branchList().map(b=>{const lines=hoursLines(b);const flag=b.flagship?' is-flagship':'';
      return `<article class="visit-card${flag}" data-branch="${b.id}"><div class="visit-head"><div><h3>${b.name}</h3>${b.label?`<span class="visit-tag">${b.label}</span>`:''}</div>${b.flagship?'<span class="visit-flag">Flagship</span>':''}</div><p class="visit-addr">${branchAddress(b)}</p>${b.note?`<p class="visit-note">${b.note}</p>`:''}<div class="visit-hours"><b>Opening hours</b><ul>${lines.map(l=>`<li${l.text==='Closed'?' data-closed':''}><span>${l.label}</span><i>${l.text}</i></li>`).join('')}</ul>${b.hoursNote?`<p class="visit-hours-note">${b.hoursNote}</p>`:''}</div><div class="visit-meta">${(b.amenities||[]).map(a=>`<span>${a}</span>`).join('')}</div><div class="visit-foot"><a class="btn btn-ghost" href="${mapsUrl(b)}" target="_blank" rel="noopener noreferrer">Directions <span aria-hidden="true">↗</span></a><button class="btn btn-dark" data-action="book-branch" data-branch="${b.id}">Book here</button></div></article>`}).join('')}
    function renderFriday(){const band=document.getElementById('fridayBand');if(!band)return;const fr=fridayActive();
      if(!fr){band.hidden=true;return}band.hidden=false;
      const put=(id,txt)=>{const el=document.getElementById(id);if(el)el.textContent=txt};
      const svc=(fr.services||[]).map(s=>s.trim()).filter(Boolean);
      put('friFlag',fr.label||'Every Friday');put('friTitle',fr.title||'Piercing Fridays');
      put('friCopy',`Selected ${svc.length?svc.join(', ').toLowerCase():'nose, ear and belly'} piercings at the Friday rate — R${group(fr.low)} to R${group(fr.high)}, between ${fr.from} and ${fr.to}. Appointment only, capped at ${fr.slots} slots.`);
      put('friFine',fr.terms||'');put('friPrice',`R${group(fr.low)}–R${group(fr.high)}`);
      put('friServices',svc.join(' · '));
      const nx=nextOn(fr.day||'fri');const today=new Date();today.setHours(0,0,0,0);
      const left=Math.round((nx-today)/86400000);
      put('friWhen',left<=0?`It is on today · ${fr.from}–${fr.to} · ${fr.slots} slots`:`Next ${DAY_LONG[fr.day||'fri']} in ${left} day${left===1?'':'s'} · ${fr.from}–${fr.to}`);
      const perk=document.getElementById('friPerk');if(perk){perk.textContent=fr.perk||'';perk.hidden=!fr.perk}}
    function renderArtists(){const box=document.getElementById('artistList');if(!box)return;
      const as=(config.artists||[]).filter(a=>a.live!==false);
      box.innerHTML=as.map(a=>{const b=branchById(a.branch);
        return `<article class="artist-card"><b>${a.name}</b><span>${a.role||'Artist'}${b?' · '+b.name:''}</span><p>${(a.specialties||[]).join(' · ')}</p>${a.bio?`<p class="artist-bio">${a.bio}</p>`:''}</article>`}).join('')||'<p class="small">No artists published yet.</p>'}
    function renderRating(){const r=config.reviews||{};const on=r.live!==false&&Number(r.score)>0;
      const card=document.getElementById('ratingCard');if(card)card.hidden=!on;
      const score=document.getElementById('ratingScore');if(score)score.textContent=Number(r.score||0).toFixed(1);
      const meta=document.getElementById('ratingMeta');if(meta)meta.textContent=`from ${r.reviews||0}${r.suffix||''} ${r.source||'reviews'}`;
      const q=document.getElementById('ratingQuote');if(q){q.textContent=r.quote?'“'+r.quote+'”':'';q.hidden=!r.quote}
      const lnk=document.getElementById('ratingLink');if(lnk){if(on&&r.url){lnk.href=r.url;lnk.hidden=false}else{lnk.removeAttribute('href');lnk.hidden=true}}
      const note=document.getElementById('heroNote');
      if(note)note.innerHTML=`<span class="dot" aria-hidden="true"></span>${esc((config.studio||{}).heroNote||'Pretoria, South Africa')}${on?` · <span class="hero-rate">${Number(r.score||0).toFixed(1)}★ ${r.reviews||0}${esc(r.suffix||'')} ${esc(r.source||'')}</span>`:''}`}
    function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
    function renderBookingOptions(){const bb=document.getElementById('bookingBranch');const ba=document.getElementById('bookingArtist');
      if(bb){const cur=bb.value;bb.innerHTML=branchList().map(b=>`<option value="${b.id}">${b.name} — ${b.street}</option>`).join('');
        bb.value=cur||config.defaultBranch||'';if(!bb.value&&branchList()[0])bb.value=branchList()[0].id}
      if(ba){const cur=ba.value;ba.innerHTML='<option value="">No preference</option>'+(config.artists||[]).filter(a=>a.live!==false).map(a=>`<option value="${a.id}">${a.name}</option>`).join('');if(cur)ba.value=cur}
      bookingHint()}
    function bookingHint(){const el=document.getElementById('bookingHint');if(!el)return;
      const dv=(document.getElementById('bookingDate')||{}).value;const rate=fridayRate(dv);
      const b=branchById((document.getElementById('bookingBranch')||{}).value);const bits=[];
      if(rate){const hrs=b&&branchDay(b,config.fridays.day||'fri');
        bits.push(`Friday rate applies at ${b?b.name:'the studio'}: nose, ear and belly piercings R${group(rate.low)}–R${group(rate.high)} between ${rate.from} and ${rate.to}${rate.slots?`, ${rate.slots} slots only`:''}. Tattoo sessions are quoted as usual.`)}
      else if(weekendDay(dv)&&(config.fridays||{}).perk)bits.push(config.fridays.perk);
      if(!rate&&dv){const k=dayKeyOf(dv);const hrs=k&&branchDay(b,k);if(hrs)bits.push(`${DAY_LONG[k]}s at ${b.name}: ${hrs[0]}–${hrs[1]} · we will confirm your exact time on WhatsApp.`);else if(k&&b)bits.push(`${b.name} is closed on ${DAY_LONG[k]}s — pick another day or ask about a mobile session.`)}
      el.textContent=bits.join(' ');el.hidden=!bits.length}
    function renderStructuredData(){const sc=document.querySelector('script[type="application/ld+json"]');if(!sc)return;
      let data;try{data=JSON.parse(sc.textContent)}catch(e){return}
      const g=data['@graph']||[];const biz=g.find(x=>x['@type']==='TattooParlor');if(!biz)return;
      const st=config.studio||{};const bs=branchList();const cb=branchById(config.defaultBranch)||bs[0];
      if(st.name)biz.name=st.name;if(st.legalName)biz.legalName=st.legalName;
      if(st.phone)biz.telephone=String(st.phone).replace(/[^+0-9]/g,'');
      if(st.email)biz.email=st.email;
      if(cb){biz.address={'@type':'PostalAddress',streetAddress:cb.street,addressLocality:cb.city,addressRegion:cb.region,addressCountry:'ZA'};
        biz.openingHoursSpecification=openingHoursSpec(cb);biz.hasMap=mapsUrl(cb);
        biz.amenityFeature=(cb.amenities||[]).map(a=>({'@type':'LocationFeatureSpecification',name:a,value:true}))}
      delete biz.openingHours;delete biz.memberOf;
      biz.areaServed=bs.length>1?bs.map(b=>({'@type':'City',name:b.city})):{'@type':'City',name:'Pretoria'};
      biz.department=bs.map(b=>({'@type':'TattooParlor','@id':(biz['@id']||'')+'#'+b.id,name:(st.name||'Haywood')+' — '+b.name,url:biz.url,telephone:biz.telephone,address:{'@type':'PostalAddress',streetAddress:b.street,addressLocality:b.city,addressRegion:b.region,addressCountry:'ZA'},openingHoursSpecification:openingHoursSpec(b),hasMap:mapsUrl(b)}));
      const same=new Set(biz.sameAs||[]);if(st.instagram)same.add('https://instagram.com/'+String(st.instagram).replace(/^@/,''));if(st.website)same.add(st.website);if(st.facebook)same.add(st.facebook);
      biz.sameAs=Array.from(same);
      sc.textContent=JSON.stringify(data)}
    function renderFridayHero(box,fr){box.hidden=false;box.dataset.special='fridays';box.dataset.friday='live';
      const put=(id,txt)=>{const el=document.getElementById(id);if(el)el.textContent=txt};
      put('offerFlag',fr.label||'Every week');put('offerTitle',fr.title||'Piercing Fridays');
      const svc=(fr.services||[]).join(', ').toLowerCase()||'nose, ear and belly';
      put('offerCopy',`Selected ${svc} piercings at the Friday rate — R${group(fr.low)} to R${group(fr.high)}, ${fr.from} to ${fr.to}. Capped at ${fr.slots} slots, appointment only.`);
      put('offerFine',fr.terms||'');put('offerScope','Piercing · '+fridayLabel());
      const nx=nextOn(fr.day||'fri');const today=new Date();today.setHours(0,0,0,0);const left=Math.round((nx-today)/86400000);
      const count=document.getElementById('offerCount');if(count)count.textContent=left<=0?('Today · '+fr.from+'–'+fr.to):('in '+left+' day'+(left===1?'':'s'));
      const cta=document.getElementById('offerCta');if(cta){cta.innerHTML=(fr.cta||'Claim a Friday slot')+' <span aria-hidden="true">↗</span>';cta.dataset.action='book-piercing'}}
    function renderStudioAll(){renderVisit();renderFriday();renderArtists();renderRating();renderBookingOptions();renderStructuredData()}
    """

ADMIN_HTML = """<div class="studio-panel" id="admin-locations"><div class="admin-card"><div class="admin-card-head"><div><h3>Locations &amp; hours</h3><p>These hours drive the visit section, the booking hints, and the opening-hours data Google reads for each branch.</p></div><span class="integration-status"><span class="led"></span><span>Published</span></span></div><div class="admin-note">Editing hours here does <b>not</b> lock the calendar on its own — mock availability in the booking flow still comes from the slot generator. Keep the two in step.</div><div id="locEditor"></div><div class="admin-actions-row"><button class="btn btn-red btn-sm" data-action="save-locations">Save locations &amp; hours</button><label class="check-row" style="margin-left:auto"><input id="locDefault" type="checkbox" /> <span>Flagship is the default booking location</span></label></div></div></div><div class="studio-panel" id="admin-fridays"><div class="admin-card"><div class="admin-card-head"><div><h3>Piercing Fridays</h3><p>A standing weekly rate card — different from a scheduled special. It never touches tattoo quotes.</p></div><span class="integration-status"><span class="led"></span><span id="friStatus">Live</span></span></div><div class="admin-form-grid"><div class="field"><label>Headline</label><input id="frTitle" placeholder="Piercing Fridays" /></div><div class="field"><label>Flag / eyebrow</label><input id="frFlag" placeholder="Every Friday" /></div><div class="field"><label>Day</label><select id="frDay"><option value="mon">Monday</option><option value="tue">Tuesday</option><option value="wed">Wednesday</option><option value="thu">Thursday</option><option value="fri">Friday</option><option value="sat">Saturday</option><option value="sun">Sunday</option></select></div><div class="field"><label>Opens</label><input id="frFrom" type="time" value="10:00" /></div><div class="field"><label>Last start</label><input id="frTo" type="time" value="15:00" /></div><div class="field"><label>Client cap</label><input id="frSlots" type="number" min="1" placeholder="20" /></div><div class="field"><label>Rate from (R)</label><input id="frLow" type="number" min="0" placeholder="100" /></div><div class="field"><label>Rate to (R)</label><input id="frHigh" type="number" min="0" placeholder="150" /></div><div class="field full"><label>Eligible piercings (comma separated)</label><input id="frServices" placeholder="Nose, Ear lobe, Belly" /></div><div class="field full"><label>Weekend perk (leave blank to hide)</label><input id="frPerk" placeholder="Free temporary tooth gem on weekend piercing bookings" /></div><div class="field"><label>Button label</label><input id="frCta" placeholder="Claim a Friday slot" /></div><div class="field"><label>Hero priority</label><input id="frPriority" type="number" placeholder="5" /></div><div class="field full"><label>Fine print</label><textarea id="frTerms" rows="2"></textarea></div><label class="check-row"><input id="frLive" type="checkbox" /> <span>Rate card is live (shown on the site and applied in the booking flow)</span></label><label class="check-row"><input id="frHero" type="checkbox" /> <span>Also take over the hero offer card when no dated special outranks it</span></label></div><div class="admin-actions-row"><button class="btn btn-red btn-sm" data-action="save-fridays">Save Piercing Fridays</button><span class="small" id="friPreview"></span></div></div></div><div class="studio-panel" id="admin-artists"><div class="admin-card"><div class="admin-card-head"><div><h3>Artists</h3><p>Who works where, what they are known for, and the rate shown on the site. Quotes still come from the pricing engine.</p></div><span class="integration-status"><span class="led"></span><span id="artistCount">1 published</span></span></div><div id="artistEditor"></div><div class="admin-actions-row"><button class="btn btn-red btn-sm" data-action="save-artists">Save artists</button><button class="btn btn-light btn-sm" data-action="add-artist">＋ Add artist</button></div></div></div><div class="studio-panel" id="admin-reviews"><div class="admin-card"><div class="admin-card-head"><div><h3>Reviews &amp; reputation</h3><p>Shown as plain copy on the site and in the concierge. Never written into structured data.</p></div><span class="integration-status"><span class="led"></span><span id="revStatus">Visible</span></span></div><div class="admin-note">We deliberately do <b>not</b> emit <code>aggregateRating</code> in JSON-LD: a self-serving rating on your own site, with no third-party widget, is the pattern Google has been retiring. The number stays visible to visitors, and a real review markup belongs on the Google Business Profile instead.</div><div class="admin-form-grid"><div class="field"><label>Score</label><input id="revScore" type="number" step="0.1" min="0" max="5" placeholder="4.9" /></div><div class="field"><label>Review count</label><input id="revCount" type="number" min="0" placeholder="100" /></div><div class="field"><label>Count suffix</label><input id="revSuffix" placeholder="+" /></div><div class="field"><label>Source</label><input id="revSource" placeholder="Google reviews" /></div><div class="field full"><label>Link to the reviews</label><input id="revUrl" placeholder="https://g.page/… (blank hides the link)" /></div><div class="field full"><label>Pull quote shown on the site</label><textarea id="revQuote" rows="2"></textarea></div><label class="check-row"><input id="revLive" type="checkbox" /> <span>Show the rating pill in the hero, the visit section, and the concierge recap</span></label></div><div class="admin-actions-row"><button class="btn btn-red btn-sm" data-action="save-reviews">Save reputation</button><span class="small" id="revPreview"></span></div></div></div>
    """

ADMIN_JS = """function renderAdminLocations(){const box=document.getElementById('locEditor');if(!box)return;
      const dd=[['mon','Mon'],['tue','Tue'],['wed','Wed'],['thu','Thu'],['fri','Fri'],['sat','Sat'],['sun','Sun']];
      box.innerHTML=(config.branches||[]).map(b=>`<div class="loc-row" data-loc="${b.id}"><h4>${b.name}${b.flagship?' · flagship':''}</h4>
        <div class="field"><label>Display name</label><input data-loc="${b.id}" data-field="name" value="${esc(b.name)}" /></div>
        <div class="field"><label>Tag line</label><input data-loc="${b.id}" data-field="label" value="${esc(b.label||'')}" /></div>
        <div class="field"><label>Street</label><input data-loc="${b.id}" data-field="street" value="${esc(b.street)}" /></div>
        <div class="field"><label>Suburb</label><input data-loc="${b.id}" data-field="suburb" value="${esc(b.suburb||'')}" /></div>
        <div class="field"><label>City</label><input data-loc="${b.id}" data-field="city" value="${esc(b.city||'')}" /></div>
        <div class="field"><label>Mobile travel fee (R)</label><input data-loc="${b.id}" data-field="travel" type="number" min="0" value="${Number(b.travel)||0}" /></div>
        <div class="field full"><label>Note shown to clients</label><input data-loc="${b.id}" data-field="note" value="${esc(b.note||'')}" /></div>
        <div class="field full"><label>Hours caveat (blank = none)</label><input data-loc="${b.id}" data-field="hoursNote" value="${esc(b.hoursNote||'')}" /></div>
        <div class="field full"><label>Amenities (comma separated)</label><input data-loc="${b.id}" data-field="amenities" value="${esc((b.amenities||[]).join(', '))}" /></div>
        <div class="loc-hours">${dd.map(([k,l])=>{const v=Array.isArray(b.hours&&b.hours[k])?b.hours[k]:null;
          return `<div class="day"><span>${l}</span><select data-loc="${b.id}" data-day="${k}" data-part="state"><option value="open"${v?' selected':''}>Open</option><option value="closed"${v?'':' selected'}>Closed</option></select><input type="time" data-loc="${b.id}" data-day="${k}" data-part="open" value="${v?v[0]:'10:00'}" /><input type="time" data-loc="${b.id}" data-day="${k}" data-part="close" value="${v?v[1]:'18:00'}" /></div>`}).join('')}</div>
        <label class="check-row"><input type="checkbox" data-loc="${b.id}" data-field="live" ${b.live!==false?'checked':''} /> <span>Published on the site</span></label>
        <label class="check-row"><input type="checkbox" data-loc="${b.id}" data-field="flagship" ${b.flagship?'checked':''} /> <span>Flagship branch</span></label></div>`).join('');
      const dflt=document.getElementById('locDefault');if(dflt)dflt.checked=(config.defaultBranch||'central')===((config.branches||[]).find(b=>b.flagship)||{}).id}
    function saveLocations(){(config.branches||[]).forEach(b=>{const hours={};
        $$('#locEditor [data-loc="'+b.id+'"][data-day]').forEach(el=>{const k=el.dataset.day;if(el.dataset.part==='state')return;
          const state=($('#locEditor [data-loc="'+b.id+'"][data-day="'+k+'"][data-part="state"]')||{}).value;
          if(state==='closed')hours[k]='closed';else{const o=$('#locEditor [data-loc="'+b.id+'"][data-day="'+k+'"][data-part="open"]').value;const c=$('#locEditor [data-loc="'+b.id+'"][data-day="'+k+'"][data-part="close"]').value;hours[k]=[o||'10:00',c||'18:00']}});
        b.hours=hours;
        $$('#locEditor [data-loc="'+b.id+'"][data-field]').forEach(el=>{const f=el.dataset.field;
          if(f==='live'||f==='flagship')b[f]=el.checked;
          else if(f==='travel')b[f]=Number(el.value)||0;
          else if(f==='amenities')b[f]=el.value.split(',').map(s=>s.trim()).filter(Boolean);
          else b[f]=el.value.trim()})});
      const firstFlag=(config.branches||[]).find(b=>b.flagship)||(config.branches||[])[0];
      if($('#locDefault')&&$('#locDefault').checked&&firstFlag)config.defaultBranch=firstFlag.id;
      else if(!branchById(config.defaultBranch)&&firstFlag)config.defaultBranch=firstFlag.id}
    function renderAdminFridays(){const fr=config.fridays||{};
      const set=(id,v)=>{const el=document.getElementById(id);if(!el)return;if(el.type==='checkbox')el.checked=!!v;else el.value=v==null?'':v};
      set('frTitle',fr.title);set('frFlag',fr.label);set('frDay',fr.day||'fri');set('frFrom',fr.from);set('frTo',fr.to);
      set('frSlots',fr.slots);set('frLow',fr.low);set('frHigh',fr.high);set('frServices',(fr.services||[]).join(', '));
      set('frPerk',fr.perk);set('frCta',fr.cta);set('frPriority',fr.priority);set('frTerms',fr.terms);
      set('frLive',fr.live!==false);set('frHero',fr.hero!==false);
      const pv=document.getElementById('friPreview');if(pv)pv.textContent=fr.live?`Hero priority ${fr.priority||0} · next ${DAY_LONG[fr.day||'fri']} ${fmtDate(nextOn(fr.day||'fri').toISOString().slice(0,10))}`:'paused';
      const st=document.getElementById('friStatus');if(st)st.textContent=fr.live?'Live':'Paused'}
    function saveFridays(){const fr=config.fridays;const gv=id=>document.getElementById(id);
      fr.title=gv('frTitle').value.trim()||'Piercing Fridays';fr.label=gv('frFlag').value.trim()||'Every Friday';
      fr.day=gv('frDay').value;fr.from=gv('frFrom').value||'10:00';fr.to=gv('frTo').value||'15:00';
      fr.slots=Math.max(0,Number(gv('frSlots').value)||0);fr.low=Number(gv('frLow').value)||0;fr.high=Number(gv('frHigh').value)||fr.low;
      fr.services=gv('frServices').value.split(',').map(s=>s.trim()).filter(Boolean);
      fr.perk=gv('frPerk').value.trim();fr.cta=gv('frCta').value.trim()||'Claim a Friday slot';
      fr.priority=Number(gv('frPriority').value)||0;fr.terms=gv('frTerms').value.trim();
      fr.live=gv('frLive').checked;fr.hero=gv('frHero').checked}
    function renderAdminArtists(){const box=document.getElementById('artistEditor');if(!box)return;
      const br=branchList();
      box.innerHTML=(config.artists||[]).map((a,i)=>`<div class="loc-row" data-artist="${i}"><h4>${esc(a.name)||'Artist '+(i+1)}</h4>
        <div class="field"><label>Name</label><input data-artist-field="name" value="${esc(a.name)}" /></div>
        <div class="field"><label>Role</label><input data-artist-field="role" value="${esc(a.role||'')}" /></div>
        <div class="field"><label>Branch</label><select data-artist-field="branch">${br.map(b=>`<option value="${b.id}"${a.branch===b.id?' selected':''}>${b.name}</option>`).join('')}</select></div>
        <div class="field"><label>Rate shown (R/hr)</label><input type="number" min="0" data-artist-field="hourly" value="${Number(a.hourly)||0}" /></div>
        <div class="field full"><label>Known for (comma separated)</label><input data-artist-field="specialties" value="${esc((a.specialties||[]).join(', '))}" /></div>
        <div class="field full"><label>Bio</label><textarea rows="2" data-artist-field="bio">${esc(a.bio||'')}</textarea></div>
        <label class="check-row"><input type="checkbox" data-artist-field="live" ${a.live!==false?'checked':''} /> <span>Published</span></label>
        <div class="admin-actions-row"><button class="btn btn-light btn-sm" data-action="remove-artist" data-artist="${i}">Remove</button></div></div>`).join('')||'<p class="small">No artists yet — add the first one.</p>';
      const c=document.getElementById('artistCount');if(c)c.textContent=(config.artists||[]).filter(a=>a.live!==false).length+' published'}
    function saveArtists(){$$('#artistEditor [data-artist]').forEach(row=>{const a=config.artists[Number(row.dataset.artist)];if(!a)return;
      $$('[data-artist-field]',row).forEach(el=>{const f=el.dataset.artistField;
        if(f==='live')a[f]=el.checked;else if(f==='hourly')a[f]=Number(el.value)||0;
        else if(f==='specialties')a[f]=el.value.split(',').map(s=>s.trim()).filter(Boolean);
        else a[f]=el.value.trim()})})}
    function renderAdminReviews(){const r=config.reviews||{};const set=(id,v)=>{const el=document.getElementById(id);if(!el)return;if(el.type==='checkbox')el.checked=!!v;else el.value=v==null?'':v};
      set('revScore',r.score);set('revCount',r.reviews);set('revSuffix',r.suffix||'');set('revSource',r.source);set('revUrl',r.url);set('revQuote',r.quote);set('revLive',r.live!==false);
      const pv=document.getElementById('revPreview');if(pv)pv.textContent=r.live!==false?`${Number(r.score||0).toFixed(1)}★ from ${r.reviews||0}${r.suffix||''} ${r.source||''} (copy only, not in schema)`:'hidden';
      const st=document.getElementById('revStatus');if(st)st.textContent=r.live!==false?'Visible':'Hidden'}
    function saveReviews(){const r=config.reviews;const gv=id=>document.getElementById(id);
      r.score=Math.min(5,Math.max(0,Number(gv('revScore').value)||0));r.reviews=Math.max(0,Number(gv('revCount').value)||0);
      r.suffix=gv('revSuffix').value.trim();r.source=gv('revSource').value.trim()||'Google reviews';
      r.url=gv('revUrl').value.trim();r.quote=gv('revQuote').value.trim();r.live=gv('revLive').checked}
    """

STYLE_CSS = """
    /* Locations, hours, artists, reputation, Piercing Fridays */
    .visit{padding:96px 0;background:linear-gradient(180deg,#0c0b0d,#141317 55%,#0c0b0d);color:#f7f6f3}
    .visit .section-head p{color:#a9a5a8}
    .visit-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px}
    .visit-card{position:relative;padding:26px 26px 24px;border-radius:22px;background:linear-gradient(180deg,rgba(255,255,255,.055),rgba(255,255,255,.02));border:1px solid rgba(255,255,255,.12);box-shadow:0 26px 60px rgba(0,0,0,.36)}
    .visit-card.is-flagship{border-color:rgba(185,20,43,.5)}
    .visit-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
    .visit-head h3{margin:0;font-family:Georgia,serif;font-weight:400;font-size:27px;line-height:1.05}
    .visit-tag{display:block;font-size:9.5px;letter-spacing:.16em;text-transform:uppercase;color:#8b878a;margin-top:7px}
    .visit-flag{font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:#fff;background:var(--red);padding:6px 9px;border-radius:999px;white-space:nowrap}
    .visit-addr{margin:16px 0 0;font-size:14px;line-height:1.55;color:#e7e5e3}
    .visit-note{margin:10px 0 0;font-size:12.5px;color:#9d999c;line-height:1.55}
    .visit-hours{margin-top:18px;padding-top:15px;border-top:1px solid rgba(255,255,255,.1)}
    .visit-hours>b{display:block;font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;color:#7d797d;margin-bottom:9px}
    .visit-hours ul{list-style:none;margin:0;padding:0;display:grid;gap:6px}
    .visit-hours li{display:flex;justify-content:space-between;gap:12px;font-size:13px;color:#cfcbc9}
    .visit-hours li i{font-style:normal;color:#fff;font-variant-numeric:tabular-nums}
    .visit-hours li[data-closed] i{color:#ff7d90}
    .visit-hours-note{margin:9px 0 0;font-size:11px;color:#827e81}
    .visit-meta{display:flex;flex-wrap:wrap;gap:7px;margin-top:16px}
    .visit-meta span{font-size:10.5px;color:#d7d4d2;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.11);padding:6px 10px;border-radius:999px}
    .visit-foot{display:flex;gap:9px;margin-top:19px;flex-wrap:wrap}
    .visit-foot .btn{text-decoration:none}
    .visit-aside{display:grid;gap:16px;margin-top:18px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
    .rating-card{padding:24px;border-radius:22px;background:linear-gradient(150deg,rgba(185,20,43,.24),rgba(255,255,255,.04));border:1px solid rgba(255,255,255,.14)}
    .rating-stars{color:#ff4e69;letter-spacing:3px;font-size:13px}
    .rating-card b{display:block;font-family:Georgia,serif;font-size:44px;line-height:1;margin:8px 0 3px}
    .rating-card>span:not(.rating-stars){font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#e6e3e1}
    .rating-card p{margin:14px 0 0;font-size:13px;line-height:1.6;color:#dcd9d7;font-style:italic}
    .rating-card a{display:inline-block;margin-top:13px;color:#fff;font-size:12px;text-decoration:underline;text-underline-offset:3px}
    .artist-list{display:grid;gap:12px;align-content:start}
    .artist-card{padding:20px 22px;border-radius:18px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.1)}
    .artist-card b{font-family:Georgia,serif;font-size:21px;font-weight:400}
    .artist-card>span{display:block;font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:#8b878a;margin:6px 0 10px}
    .artist-card p{margin:0;font-size:12.5px;color:#d3d0ce;line-height:1.6}
    .artist-bio{margin-top:8px!important;color:#9b979a!important}
    .fridays{padding:0 0 96px;background:#0c0b0d}
    .friday-band{display:grid;grid-template-columns:1.55fr 1fr;gap:26px;padding:30px 32px;border-radius:26px;background:radial-gradient(120% 140% at 0 0,rgba(185,20,43,.34),rgba(185,20,43,0) 62%),linear-gradient(180deg,#1b1a1e,#131215);border:1px solid rgba(255,255,255,.13);box-shadow:0 34px 80px rgba(0,0,0,.42);color:#f7f6f3}
    .friday-band[hidden]{display:none}
    .friday-flag{display:inline-block;font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;color:#fff;background:rgba(185,20,43,.9);padding:6px 11px;border-radius:999px}
    .friday-main h3{margin:13px 0 0;font-family:Georgia,serif;font-weight:400;font-size:clamp(28px,3.4vw,40px);line-height:1.03}
    .friday-main p{margin:12px 0 0;font-size:14px;line-height:1.65;color:#cbc7c5;max-width:58ch}
    .friday-fine{font-size:11.5px!important;color:#8e8a8d!important;line-height:1.6}
    .friday-side{display:grid;gap:11px;align-content:start;padding-left:26px;border-left:1px solid rgba(255,255,255,.12)}
    .friday-price span,.friday-when,.friday-svc{font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:#8b878a;margin:0}
    .friday-price b{display:block;font-family:Georgia,serif;font-size:36px;font-weight:400;line-height:1;margin-top:5px}
    .friday-when{color:#ff8fa0!important;letter-spacing:.1em!important}
    .friday-svc{color:#d7d4d2!important;letter-spacing:.05em!important;text-transform:none!important;font-size:12.5px!important}
    .friday-perk{margin:2px 0 0;font-size:11.5px;line-height:1.55;color:#9b979a}
    .friday-perk[hidden]{display:none}
    .hero-rate{border:1px solid rgba(255,255,255,.22);border-radius:999px;padding:3px 8px;font-size:10.5px;letter-spacing:.05em;color:#fff}
    .hero-note a{color:inherit;text-decoration:underline;text-underline-offset:3px}
    .booking-hint{margin:14px 0 0;padding:12px 14px;border-radius:14px;background:rgba(185,20,43,.08);border:1px solid rgba(185,20,43,.26);font-size:12px;line-height:1.55;color:#2c2930}
    .booking-hint[hidden]{display:none}
    .loc-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;padding:16px;border-radius:16px;background:#18181b;border:1px solid #2b2a2e;margin-bottom:12px}
    .loc-row h4{margin:0 0 8px;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#ff8fa0;grid-column:1/-1}
    .loc-row .field{display:grid;gap:5px;align-content:start}
    .loc-row label{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#777}
    .loc-row input,.loc-row select,.loc-row textarea{width:100%;padding:9px 10px;border-radius:10px;background:#0f0f11;border:1px solid #33323a;color:#f1eff0;font-size:13px;font-family:inherit}
    .loc-hours{grid-column:1/-1;display:grid;grid-template-columns:repeat(auto-fit,minmax(112px,1fr));gap:8px;padding-top:12px;margin-top:4px;border-top:1px solid #2b2a2e}
    .loc-hours .day{display:grid;gap:4px}
    .loc-hours .day>span{font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:#6f6c70}
    .loc-hours .day input,.loc-hours .day select{padding:7px 8px;font-size:12px}
    .admin-note{margin:0 0 14px;padding:12px 14px;border-radius:13px;background:rgba(255,78,105,.08);border:1px solid rgba(255,78,105,.22);font-size:11.5px;line-height:1.6;color:#d9d5d7}
    .admin-note b{color:#fff}
    .admin-note code{background:rgba(0,0,0,.4);padding:1px 5px;border-radius:5px;font-size:11px}
    @media(max-width:900px){.visit{padding:60px 0}.visit-card{padding:21px}.friday-band{grid-template-columns:1fr;gap:20px;padding:23px 20px}.friday-side{padding-left:0;border-left:0;padding-top:18px;border-top:1px solid rgba(255,255,255,.12)}.visit-foot .btn{flex:1}.fridays{padding-bottom:60px}}
    @media(max-width:560px){.visit-head{flex-direction:column;align-items:flex-start}.rating-card b{font-size:36px}.loc-hours{grid-template-columns:repeat(2,1fr)}}
    @media(prefers-reduced-motion:reduce){.visit-card,.friday-band{box-shadow:none}}
"""

FAQ_NEW = """<details class="faq-item"><summary><b>Which piercings do you do, and do you do surface piercings?</b><span aria-hidden="true">＋</span></summary><p>Ear (lobe and cartilage: helix, tragus, conch), nose, tongue, belly, and dermal anchors. Surface piercings are not offered — the rejection risk is not worth your skin. Jewelry is implant-grade and priced with the slot.</p></details><details class="faq-item"><summary><b>What are Piercing Fridays?</b><span aria-hidden="true">＋</span></summary><p>A standing weekly rate: selected nose, ear and belly piercings at R100–R150, Fridays only, between 10:00 and 15:00. Slots are capped at around 15–20 clients, so it is strictly appointment-only. Book the slot, bring ID, and the artist confirms the exact price at the chair.</p></details><details class="faq-item"><summary><b>Where are you, and can I just park outside?</b><span aria-hidden="true">＋</span></summary><p>Two locations: the private flagship at 296 Francis Baard Street, Pretoria Central, and a second studio at 2241 Martha Modise Street in Mabopane. Pretoria Central has on-site and wheelchair-accessible parking; Mabopane is street parking. Both take cards and mobile pay, and both run on a book — so lock the time before you travel.</p></details>"""


def patch(page, stage):
    for kind, *rest in stage["edits"]:
        if kind == "insertBefore":
            needle, block = rest
            if block[:60] in page:
                continue
            i = page.index(needle)
            page = page[:i] + block + page[i:]
        elif kind == "insertAfter":
            needle, block = rest
            if block[:60] in page:
                continue
            i = page.index(needle) + len(needle)
            page = page[:i] + block + page[i:]
        elif kind == "replace":
            a, b = rest
            if b[:60] in page and a not in page:
                continue
            n = page.count(a)
            assert n == 1, f"anchor {n}x (want 1): {a[:80]}"
            page = page.replace(a, b)
        elif kind == "subn":
            pat, repl = rest
            page, n = re.subn(pat, repl, page, count=1)
            assert n == 1, f"regex miss: {pat[:70]}"
        else:
            raise ValueError(kind)
    return page


STAGES = {}

# ------------------------------------------------------------------ hours order
STAGES["week-order"] = {
    "doc": "display hours Mon-first instead of Sun-first",
    "edits": [
        ("replace",
         "const DAYS=['sun','mon','tue','wed','thu','fri','sat'];",
         "const DAYS=['sun','mon','tue','wed','thu','fri','sat'];\n    const WEEK=['mon','tue','wed','thu','fri','sat','sun'];"),
        ("replace",
         "function hoursLines(b){if(!b||!b.hours)return[];const runs=[];\n      DAYS.forEach(d=>{",
         "function hoursLines(b){if(!b||!b.hours)return[];const runs=[];\n      WEEK.forEach(d=>{"),
    ],
}

# ------------------------------------------------------- perk field for the band
STAGES["perk"] = {
    "doc": "weekend perk string on the Friday rate card",
    "edits": [
        ("replace",
         "services:['Nose','Ear lobe','Belly'],cta:'Claim a Friday slot'",
         "services:['Nose','Ear lobe','Belly'],cta:'Claim a Friday slot',perk:'Weekend perk: book a piercing on Saturday or Sunday and a temporary tooth gem is on the studio — subject to stock and artist sign-off.'"),
    ],
}

# --------------------------------------------------------------------- markup
STAGES["markup"] = {
    "doc": "visit section, Friday band, hero note fix, nav links, piercing copy, booking fields",
    "edits": [
        # hero note: hoist out of #heroOffer so hiding an offer never hides the studio line
        ("replace",
         '<p class="hero-note"><span class="dot" aria-hidden="true"></span>Taking private bookings in Pretoria and on location</p></div></div>',
         '</div><p class="hero-note" id="heroNote"><span class="dot" aria-hidden="true"></span>Two Pretoria locations · private and mobile sessions<span class="hero-rate">4.9★ 100+ Google reviews</span></p></div>'),
        # piercing service card: name the actual menu, state the exclusion
        ("replace",
         "<h3>Piercing</h3><p>Thoughtful placement, quality jewelry, clear preparation, and aftercare you can actually follow.</p>",
         "<h3>Piercing</h3><p>Ear lobe and cartilage (helix, tragus, conch), nose, tongue, belly and dermal anchors, with implant-grade jewelry and aftercare you can actually follow. Surface piercings are not offered.</p>"),
        # Friday band after the services section
        ("insertBefore", '\n    <section class="shop" id="shop">', FRIDAY_HTML.rstrip("\n") + "\n    "),
        # visit section before the FAQ
        ("insertBefore", '<section class="faq" id="faq">', VISIT_HTML.rstrip("\n") + "\n    "),
        # nav + mobile sheet
        ("replace", '<a href="#faq">FAQ</a><a href="#about">About</a>',
         '<a href="#faq">FAQ</a><a href="#visit">Visit</a><a href="#about">About</a>'),
        ("replace", '<a href="#faq"><b>FAQ</b>',
         '<a href="#visit"><b>Visit</b><span>Both locations, hours, and parking</span></a>\n      <a href="#faq"><b>FAQ</b>'),
        ("replace", '<a href="#faq">FAQ</a><a href="#about">About Haywood</a>',
         '<a href="#faq">FAQ</a><a href="#visit">Visit &amp; hours</a><a href="#fridays">Piercing Fridays</a><a href="#about">About Haywood</a>'),
        # booking fields: branch + artist + contextual hint
        ("replace",
         '<select id="bookingMode"><option>Private studio — Pretoria</option><option>Mobile session — artist review</option></select></div>',
         '<select id="bookingMode"><option>Private studio — Pretoria</option><option>Mobile session — artist review</option></select></div><div class="field"><label>Studio location</label><select id="bookingBranch"></select></div><div class="field"><label>Preferred artist (optional)</label><select id="bookingArtist"><option value="">No preference</option><option value="yuran">Yuran</option></select></div>'),
        ("replace",
         'want Haywood to contact me about this request.</label></div></div><div class="modal-actions">',
         'want Haywood to contact me about this request.</label></div><p class="booking-hint" id="bookingHint" hidden></p></div><div class="modal-actions">'),
    ],
}

# ----------------------------------------------------------------------- css
# -------------------------------------------------------------------- mapsUrl
STAGES["mapsurl"] = {"doc": "Google Maps search link builder (referenced by renderVisit + schema)", "edits": [
    ("insertBefore", "function hoursLines(b){",
     "function mapsUrl(b){const q=b&&(b.mapQuery||branchAddress(b));return 'https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(q||'Haywood Tattoo Studio Pretoria')}\n    "),
]}

STAGES["style"] = {"doc": "visit / friday / admin editor styles", "edits": [
    ("insertBefore", "  </style>", STYLE_CSS),
]}

# ----------------------------------------------------------------------- faq
FAQ_TAIL = ("<p>No. Every figure you see here is an indicative range produced by the brief you fill in, "
            "and any live studio special is applied to that range automatically. The confirmed quote always "
            "comes from the artist.</p></details>")

STAGES["faq"] = {"doc": "corrected walk-in answer + 3 researched questions", "edits": [
    ("replace",
     "<b>Do you tattoo walk-ins?</b><span aria-hidden=\"true\">＋</span></summary><p>No. Haywood is a private, by-appointment studio with one artist, so each session gets the whole day and no waiting room. Send a brief over WhatsApp or through the concierge and you will get a reply with available dates.</p>",
     "<b>Do you tattoo walk-ins?</b><span aria-hidden=\"true\">＋</span></summary><p>For tattoos, effectively no: Haywood is a private, by-appointment studio, so each session gets the whole day and no waiting room. Standard piercing work is the exception — a walk-in can sometimes be taken when a slot is open, which is most likely on a Friday. Send a brief over WhatsApp or through the concierge and you will get a reply with available dates.</p>"),
    ("insertAfter", FAQ_TAIL, FAQ_NEW),
]}

# ------------------------------------------------------------------- handlers
STAGES["handlers"] = {"doc": "click handlers for the new admin panels", "edits": [
    ("replace",
     "if(action==='handoff-artist')handoffArtist();",
     "if(action==='save-locations'){saveLocations();save();renderAdmin();toast('Locations and hours saved');}"
     "if(action==='save-fridays'){saveFridays();save();renderAdmin();toast('Piercing Fridays updated');}"
     "if(action==='save-artists'){saveArtists();save();renderAdmin();toast('Artist roster saved');}"
     "if(action==='add-artist'){(config.artists=config.artists||[]).push({id:'artist-'+Date.now().toString(36),live:true,name:'',role:'',branch:(activeBranch()||{}).id,hourly:config.pricing.hourly,specialties:[],bio:''});save();renderAdmin();toast('Draft artist added — fill it in, then save');}"
     "if(action==='remove-artist'){config.artists=(config.artists||[]).filter((a,i)=>i!==Number(e.target.dataset.artist));save();renderAdmin();toast('Artist removed');}"
     "if(action==='save-reviews'){saveReviews();save();renderAdmin();toast('Reputation settings saved');}"
     "if(action==='handoff-artist')handoffArtist();"),
    # the day word must come from the day itself, not the eyebrow label
    ("replace",
     "const price=fr?`R${group(fr.low)}–R${group(fr.high)} on ${(config.fridays.label||'Piercing Fridays').replace(/^Piercing /,'')}${fr.day?'s':''} · from R 650 otherwise`:'From R 650';",
     "const price=fr?`R${group(fr.low)}–R${group(fr.high)} on ${fridayLabel()} · from R 650 otherwise`:'From R 650';"),
]}

# ---------------------------------------------------------------- review fixes
E = [
 # $$ has no root argument — a scoped lookup must use the element itself
 ('replace',
  "function saveArtists(){$$('#artistEditor [data-artist]').forEach(row=>{const a=config.artists[Number(row.dataset.artist)];if(!a)return;\n      $$('[data-artist-field]',row).forEach(el=>{const f=el.dataset.artistField;",
  "function saveArtists(){$$('#artistEditor .loc-row[data-artist]').forEach(row=>{const a=config.artists[Number(row.dataset.artist)];if(!a)return;\n      [...row.querySelectorAll('[data-artist-field]')].forEach(el=>{const f=el.dataset.artistField;"),
 # two-day runs read better as a range, and it matches the printed card
 ('replace', "else if(n>2)label=DAY_LABEL[r.days[0]]+'–'+DAY_LABEL[r.days[r.days.length-1]];",
             "else if(n>1)label=DAY_LABEL[r.days[0]]+'–'+DAY_LABEL[r.days[r.days.length-1]];",),
 # escape every admin-entered string before it reaches innerHTML
 ('replace', "<h3>${b.name}</h3>${b.label?`<span class=\"visit-tag\">${b.label}</span>`:''}",
             "<h3>${esc(b.name)}</h3>${b.label?`<span class=\"visit-tag\">${esc(b.label)}</span>`:''}",),
 ('replace', "<p class=\"visit-addr\">${branchAddress(b)}</p>${b.note?`<p class=\"visit-note\">${b.note}</p>`:''}",
             "<p class=\"visit-addr\">${esc(branchAddress(b))}</p>${b.note?`<p class=\"visit-note\">${esc(b.note)}</p>`:''}",),
 ('replace', "<li${l.text==='Closed'?' data-closed':''}><span>${l.label}</span><i>${l.text}</i></li>",
             "<li${l.text==='Closed'?' data-closed':''}><span>${esc(l.label)}</span><i>${esc(l.text)}</i></li>",),
 ('replace', "${b.hoursNote?`<p class=\"visit-hours-note\">${b.hoursNote}</p>`:''}",
             "${b.hoursNote?`<p class=\"visit-hours-note\">${esc(b.hoursNote)}</p>`:''}",),
 ('replace', "${(b.amenities||[]).map(a=>`<span>${a}</span>`).join('')}",
             "${(b.amenities||[]).map(a=>`<span>${esc(a)}</span>`).join('')}",),
 ('replace', "<h4>${b.name}${b.flagship?' · flagship':''}</h4>",
             "<h4>${esc(b.name)}${b.flagship?' · flagship':''}</h4>",),
 ('replace', "<b>${a.name}</b><span>${a.role||'Artist'}${b?' · '+b.name:''}</span><p>${(a.specialties||[]).join(' · ')}</p>${a.bio?`<p class=\"artist-bio\">${a.bio}</p>`:''}",
             "<b>${esc(a.name)}</b><span>${esc(a.role||'Artist')}${b?' · '+esc(b.name):''}</span><p>${esc((a.specialties||[]).join(' · '))}</p>${a.bio?`<p class=\"artist-bio\">${esc(a.bio)}</p>`:''}",),
 # a stale payload may still carry the retired hours array
 ('replace', "let bookings=JSON.parse(localStorage.getItem('haywoodBookings')||'[]');",
             "delete config.hours;const HOURS_RETIRED=true;\n    let bookings=JSON.parse(localStorage.getItem('haywoodBookings')||'[]');",),
 # point the owner at the other promo engine
 ('replace', "<p>Publish a promotion to the hero, schedule it, and let the estimate calculator apply it automatically.</p>",
             "<p>Publish a promotion to the hero, schedule it, and let the estimate calculator apply it automatically. <b>Piercing Fridays</b> is not managed here — that standing weekly rate card lives under <i>Piercing Fridays</i>.</p>",),
]
STAGES["fixes"] = {"doc": "scoped field writes, Mon-first ranges, escaping, legacy key removal, admin cross-reference", "edits": E}

# --------------------------------------------------------------------- admin
STAGES["admin"] = {"doc": "four new Studio OS panels + sidebar entries + titles", "edits": [
    # sidebar: add the new tabs after specials
    ("replace",
     '<button data-admin-tab="commerce"><span>♧</span>Commerce & orders</button>',
     '<button data-admin-tab="fridays"><span>◷</span>Piercing Fridays</button><button data-admin-tab="locations"><span>⌖</span>Locations &amp; hours</button><button data-admin-tab="commerce"><span>♧</span>Commerce &amp; orders</button>'),
    ("replace",
     '<button data-admin-tab="ai"><span>✦</span>AI configuration</button>',
     '<button data-admin-tab="artists"><span>☖</span>Artists</button><button data-admin-tab="reviews"><span>★</span>Reviews &amp; reputation</button><button data-admin-tab="ai"><span>✦</span>AI configuration</button>'),
    # panels
    ("insertBefore", '<div class="studio-panel" id="admin-specials">',
     ADMIN_HTML.split('<div class="studio-panel" id="admin-fridays">')[0] + '<div class="studio-panel" id="admin-fridays">' + ADMIN_HTML.split('<div class="studio-panel" id="admin-fridays">')[1].split('<div class="studio-panel" id="admin-artists">')[0]),
    ("insertBefore", '<div class="studio-panel" id="admin-ai">',
     '<div class="studio-panel" id="admin-artists">' + ADMIN_HTML.split('<div class="studio-panel" id="admin-artists">')[1]),
    # titles map
    ("replace",
     "specials:['Specials &amp; offers','Create hero promotions, schedule them, and let the estimator apply them.'],",
     "specials:['Specials &amp; offers','Create hero promotions, schedule them, and let the estimator apply them.'],\nfridays:['Piercing Fridays','The standing weekly piercing rate card, its caps, and the weekend perk.'],\nlocations:['Locations &amp; hours','Addresses, opening hours, travel fees, and what Google reads per branch.'],\nartists:['Artists','Who is publishing, what they are known for, and where they work.'],\nreviews:['Reviews &amp; reputation','How the studio shows its rating — copy only, never structured data.'],"),
]}

# --------------------------------------------------------------------- wiring
STAGES["wire"] = {"doc": "renderers, admin hooks, booking flow, hero for the weekly card", "edits": [
    # helpers live next to the other renderers
    ("insertBefore", "function renderSpecial(){", HELPERS),
    ("insertBefore", "function renderAdmin(){", ADMIN_JS),
    # hero: one renderer for both a dated special and the weekly card
    ("replace",
     "function renderSpecial(){const box=document.getElementById('heroOffer');if(!box)return;const sp=activeSpecial();\n      if(!sp){box.hidden=true;return}box.hidden=false;box.dataset.special=sp.id;",
     "function renderSpecial(){const box=document.getElementById('heroOffer');if(!box)return;const hero=heroOffer();\n      if(!hero){box.hidden=true;return}\n      if(hero.type==='fridays'){renderFridayHero(box,hero.fr);return}\n      const sp=hero.sp;box.hidden=false;box.dataset.special=sp.id;box.removeAttribute('data-friday');\n      const spCta=document.getElementById('offerCta');if(spCta)spCta.dataset.action='open-estimate';"),
    # admin render hooks
    ("replace",
     "$('#statLookbook').textContent=lookbook.length;",
     "$('#statLookbook').textContent=lookbook.length;renderAdminLocations();renderAdminFridays();renderAdminArtists();renderAdminReviews();"),
    # save(): keep the public page in sync with anything the admin touched
    ("replace",
     "localStorage.setItem('haywoodCart',JSON.stringify(cart));}",
     "localStorage.setItem('haywoodCart',JSON.stringify(cart));renderStudioAll();}"),
    # booking: carry branch + artist, honour the Friday card, note the perk
    ("replace",
     "deposit:activeProject?.priceNum||Math.round(config.pricing.base*config.pricing.deposit/100)};",
     "deposit:activeProject?.priceNum||Math.round(config.pricing.base*config.pricing.deposit/100),branch:(document.getElementById('bookingBranch')||{}).value||config.defaultBranch,branchName:(branchById((document.getElementById('bookingBranch')||{}).value)||{}).name||'',artist:(document.getElementById('bookingArtist')||{}).value||'',friday:!!fridayRate($('#bookingDate').value),weekend:weekendDay($('#bookingDate').value)};"),
    ("replace",
     "const msg=`Hi Haywood Tattoo Studio, I’d like to confirm booking ${b.id}. Name: ${b.name}. Project: ${b.project}. Preferred date: ${b.date}. Mode: ${b.mode}. I’m ready to arrange the ${money(b.deposit)} deposit.`;",
     "const msg=`Hi ${(config.studio||{}).name||'Haywood Tattoo Studio'}, I’d like to confirm booking ${b.id}. Name: ${b.name}. Project: ${b.project}. Preferred date: ${b.date}. Mode: ${b.mode}${b.branchName?'. Location: '+b.branchName:''}${b.artist?'. Artist: '+((config.artists||[]).find(a=>a.id===b.artist)||{}).name:''}${b.friday?'. Piercing Friday rate applies':''}. I’m ready to arrange the ${money(b.deposit)} deposit.`;"),
    ("replace",
     "function openPiercing(){activeProject={title:'Piercing appointment',price:'From R 650',priceNum:650,detail:{service:'Piercing'}};$('#bookingSummary').innerHTML='<h4>Piercing appointment</h4><p>Choose your piercing and jewelry in your notes. Starting deposit from R 650.</p>';openOverlay('#bookingOverlay')}",
     "function openPiercing(){const fr=fridayActive();const price=fr?`R${group(fr.low)}–R${group(fr.high)} on ${(config.fridays.label||'Piercing Fridays').replace(/^Piercing /,'')}${fr.day?'s':''} · from R 650 otherwise`:'From R 650';activeProject={title:'Piercing appointment',price:price,priceNum:650,detail:{service:'Piercing'}};$('#bookingSummary').innerHTML=`<h4>Piercing appointment</h4><p>${price}</p>${fr?`<p class=\"small\">Fridays ${fr.from}–${fr.to}${fr.slots?', capped at '+fr.slots+' slots':''} · jewelry subject to stock · 18+ with ID or guardian consent</p>`:''}<p class=\"small\">Deposit is held from the standard piercing rate, not the promo rate.</p>`;openOverlay('#bookingOverlay')}"
     ),
    # booking summary shows the chosen branch
    ("replace",
     "${d.price||d.priceNum||'Artist review required'} · ${d.detail?.mode==='Mobile'?'Mobile session':'Private studio, Pretoria'}",
     "${d.price||d.priceNum||'Artist review required'} · ${d.detail?.mode==='Mobile'?'Mobile session':'Private studio, '+(branchById((document.getElementById('bookingBranch')||{}).value)||{name:'Pretoria'}).name}"
     ),
    # keep the hint in step with the form
    ("replace",
     "$('#chatInput').addEventListener('keydown'",
     "$('#bookingDate').addEventListener('change',bookingHint);if($('#bookingBranch'))$('#bookingBranch').addEventListener('change',bookingHint);\n    $('#chatInput').addEventListener('keydown'"),
    # hero CTA for the weekly card + public branch shortcut
    ("replace",
     "if(action==='handoff-artist')handoffArtist();",
     "if(action==='handoff-artist')handoffArtist();if(action==='book-branch'){config.defaultBranch=e.target.dataset.branch;save();openBooking();toast('Booking for '+(branchById(e.target.dataset.branch)||{}).name)}"),
    # init
    ("replace",
     "renderLookbook();renderProducts();renderCart();renderAdmin();renderSpecial();",
     "renderLookbook();renderProducts();renderCart();renderAdmin();renderSpecial();renderStudioAll();"),
]}

# --------------------------------------------------------------------- schema
STAGES["schema"] = {"doc": "static JSON-LD gains both branches, street address, hours, amenities, legalName", "edits": []}


def schema_post(page):
    i = page.index('<script type="application/ld+json">')
    j = page.index("</script>", i)
    data = json.loads(page[i + len('<script type="application/ld+json">'):j])
    g = data["@graph"]
    biz = [x for x in g if x.get("@type") == "TattooParlor"][0]
    base = "https://demo0ps.github.io/haywood-tattoo-studio/"
    hours = {k: v for k, v in [
        ("mon", ["10:00", "18:00"]), ("tue", ["10:00", "18:00"]), ("wed", ["10:00", "18:00"]),
        ("thu", ["10:00", "17:00"]), ("fri", ["10:00", "18:00"]), ("sat", ["10:00", "18:00"]),
        ("sun", ["11:00", "17:00"])]}
    long = {"mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
            "fri": "Friday", "sat": "Saturday", "sun": "Sunday"}
    spec = [{"@type": "OpeningHoursSpecification", "dayOfWeek": "https://schema.org/" + long[k],
             "opens": v[0], "closes": v[1]} for k, v in hours.items()]
    biz["legalName"] = "Haywood Tattoos and Piercings"
    biz["description"] = ("Private tattoo and piercing studio in Pretoria with a second location in Mabopane. "
                          "Custom tattoo work, piercings, mobile sessions, and transparent indicative pricing.")
    biz["address"] = {"@type": "PostalAddress", "streetAddress": "296 Francis Baard Street, Pretoria Central",
                      "addressLocality": "Pretoria", "addressRegion": "Gauteng", "addressCountry": "ZA"}
    biz["paymentAccepted"] = "Cash, Credit cards, Debit cards, NFC mobile payments, Yoco"
    biz["hasMap"] = "https://www.google.com/maps/search/?api=1&query=296+Francis+Baard+Street%2C+Pretoria+Central"
    biz["amenityFeature"] = [{"@type": "LocationFeatureSpecification", "name": n, "value": True} for n in
                             ["On-site parking", "Wheelchair-accessible parking", "Private studio", "Card terminal on site"]]
    biz["openingHoursSpecification"] = spec
    del biz["openingHours"]
    del biz["memberOf"]
    biz["areaServed"] = [{"@type": "City", "name": "Pretoria"}, {"@type": "City", "name": "Tshwane"},
                         {"@type": "AdministrativeArea", "name": "Gauteng"}]
    biz["employee"] = {"@type": "Person", "name": "Yuran", "jobTitle": "Resident artist"}
    biz["department"] = [{
        "@type": "TattooParlor", "@id": biz["@id"] + "#mabopane",
        "name": "Haywood Tattoo Studio — Mabopane", "url": base + "#visit",
        "telephone": "+27617593378",
        "address": {"@type": "PostalAddress", "streetAddress": "2241 Martha Modise Street, Mabopane",
                    "addressLocality": "Tshwane", "addressRegion": "Gauteng", "addressCountry": "ZA"},
        "openingHoursSpecification": [s for s in spec if s["dayOfWeek"].endswith("Sunday") is False],
        "hasMap": "https://www.google.com/maps/search/?api=1&query=2241+Martha+Modise+Street%2C+Mabopane"}]
    biz["sameAs"] = ["https://instagram.com/haywood_studio", "https://www.haywoodstudio.com"]
    faq = [x for x in g if x.get("@type") == "FAQPage"][0]
    new_q = [
        ("Which piercings do you do, and do you do surface piercings?",
         "Ear lobe and cartilage (helix, tragus, conch), nose, tongue, belly, and dermal anchors. Surface piercings are not offered."),
        ("What are Piercing Fridays?",
         "Selected nose, ear and belly piercings at R100–R150, Fridays only, between 10:00 and 15:00. Appointment only, capped at about 15–20 clients."),
        ("Where are you, and can I just park outside?",
         "296 Francis Baard Street in Pretoria Central with on-site and wheelchair-accessible parking, and 2241 Martha Modise Street in Mabopane with street parking. Both take cards and mobile pay."),
    ]
    have = {q["name"] for q in faq["mainEntity"]}
    for qn, qa in new_q:
        if qn not in have:
            faq["mainEntity"].append({"@type": "Question", "name": qn,
                                      "acceptedAnswer": {"@type": "Answer", "text": qa}})
    for x in g:
        if x.get("@type") == "FAQPage":
            for q in x["mainEntity"]:
                if q["name"] == "Do you tattoo walk-ins?":
                    q["acceptedAnswer"]["text"] = (
                        "Tattoo sessions are appointment-only. Standard piercings can sometimes be taken as a walk-in "
                        "when a slot is open, which is most likely on a Friday.")
    page = page[:i + len('<script type="application/ld+json">')] + json.dumps(data, separators=(",", ":")) + page[j:]
    return page


def main() -> int:
    applied = json.loads(STATE.read_text()) if STATE.exists() else []
    if "--status" in sys.argv:
        print("applied:", applied or "(none)")
        return 0
    page = PAGE.read_text()
    start = page
    done = []
    for name, stage in STAGES.items():
        if name in applied:
            print(f"  · {name:<11} already applied")
            continue
        page = patch(page, stage)
        if name == "schema":
            page = schema_post(page)
        done.append(name)
        print(f"  ✓ {name:<11} {stage['doc']}")
    if page == start:
        print("nothing to do")
        return 0
    css = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
    assert css.count("{") == css.count("}"), f"unbalanced CSS braces {css.count('{')}/{css.count('}')}"
    PAGE.write_text(page)
    STATE.write_text(json.dumps(sorted(set(applied + done)), indent=0))
    print(f"written · {len(page)} chars · +{len(page)-len(start)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
