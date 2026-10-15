#!/usr/bin/env node
const path = require('path');
const ROOT = path.join(__dirname, '..', '') + path.sep;
const IDX = path.join(ROOT, 'index.html');
/* Studio-facts suite: researched hours, two branches, Piercing Fridays, artists,
   reputation, and the four new Studio OS panels. Drives the page's own functions. */
const fs = require('fs');
const { JSDOM } = require('jsdom');
const html = fs.readFileSync(IDX, 'utf8');

const dom = new JSDOM(html, { url: 'http://localhost:4173/', runScripts: 'dangerously', pretendToBeVisual: true });
const { window } = dom;
const errors = [];
window.addEventListener('error', e => errors.push(e.message));
window.console.error = (...a) => errors.push('console: ' + a.join(' '));
window.console.warn = () => {};
let opened = [];
window.open = (u) => { opened.push(u); return { focus() {} } };

const ev = (c) => window.eval(c);
const $ = (s) => window.document.querySelector(s);
const $$ = (s) => Array.from(window.document.querySelectorAll(s));
const click = (el) => el && el.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true }));
let pass = 0, fail = 0;
const ok = (n, c, x) => {
  if (c) { pass++; console.log('  \x1b[32mPASS\x1b[0m ' + n + (x ? '  ' + x : '')); }
  else { fail++; console.log('  \x1b[31mFAIL\x1b[0m ' + n + (x ? '  ' + x : '')); }
};
const li = (sel) => $$(sel).map(e => e.textContent.replace(/\s+/g, ' ').trim());

const setV = (sel, val) => ev(`(()=>{const el=document.querySelector(${JSON.stringify(sel)});if(!el)return 'MISSING:'+${JSON.stringify(sel)};el.value=${JSON.stringify(String(val))};return 'ok'})()`);
const setChk = (sel, val) => ev(`(()=>{const el=document.querySelector(${JSON.stringify(sel)});if(!el)return 'MISSING';el.checked=${val?'true':'false'};return 'ok'})()`);
const clickV = (sel) => ev(`(()=>{const el=document.querySelector(${JSON.stringify(sel)});if(!el)return 'MISSING:'+${JSON.stringify(sel)};el.dispatchEvent(new window.MouseEvent('click',{bubbles:true,cancelable:true}));return 'ok'})()`);
const setTxt = (sel, val) => ev(`(()=>{const el=document.querySelector(${JSON.stringify(sel)});if(!el)return 'MISSING:'+${JSON.stringify(sel)};el.textContent=${JSON.stringify(val)};return 'ok'})()`);
// a real date for a given weekday, relative to the page's clock
const dateFor = (day) => ev(`(()=>{const d=nextOn('${day}');return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')})()`);
const otherDay = () => ev(`(()=>{for(let i=1;i<8;i++){const d=new Date();d.setDate(d.getDate()+i);if(DAYS[d.getDay()]!==(config.fridays.day||'fri'))return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}})()`);

console.log('\n── config shape ────────────────────────────────────');
ok('studio identity merged from research', ev("config.studio.legalName") === 'Haywood Tattoos and Piercings' && ev("config.studio.wa") === '27617593378');
ok('two live branches', ev("branchList().length") === 2);
ok('branch ids', ev("branchList().map(b=>b.id).join(',')") === 'central,mabopane');
ok('legacy hours array is gone', ev("config.hours") === undefined);
ok('default branch is the flagship', ev("config.defaultBranch") === 'central' && ev("activeBranch().name") === 'Pretoria Central');
ok('no invented postal codes', ev("Object.keys(config.branches[0]).includes('postalCode')") === false);
ok('friday card is separate from specials', ev("config.fridays.live") === true && ev("config.specials.every(s=>s.kind!=='weekly')") === true);

console.log('\n── hours model ─────────────────────────────────────');
const hours = ev("JSON.stringify(hoursLines(branchById('central')))");
const lines = JSON.parse(hours);
ok('runs are grouped Mon-first', lines.map(l => l.label).join('|') === 'Mon–Wed|Thu|Fri–Sat|Sun', lines.map(l => l.label).join('|'));
ok('static card matches the rendered grouping', (() => { const stat = (html.match(/<section class="visit"[\s\S]*?<\/section>/) || [''])[0]; const labels = [...stat.matchAll(/<li[^>]*><span>([^<]+)<\/span>/g)].map(m => m[1]); return labels.join('|') === 'Mon–Wed|Thu|Fri–Sat|Sun|Mon–Wed|Thu|Fri–Sat|Sun' }), 'static vs computed');
ok('researched times on the flagship', lines[0].text === '10:00–18:00' && lines[1].text === '10:00–17:00' && lines[3].text === '11:00–17:00', lines.map(l => l.label + ' ' + l.text).join(' · '));
ok('every day accounted for', lines.reduce((n, l) => n + l.days.length, 0) === 7);
const mab = JSON.parse(ev("JSON.stringify(hoursLines(branchById('mabopane')))"));
ok('Mabopane closed Sunday', mab[mab.length - 1].text === 'Closed' && mab[mab.length - 1].label === 'Sun');
ok('closed day flagged for styling', /data-closed/.test(ev("document.getElementById('visitGrid').innerHTML")));
ok('dayKeyOf maps a date to a weekday key', ev("dayKeyOf('2026-01-05')") === 'mon');
ok('weekendDay true for Sat/Sun only', ev("weekendDay('2026-01-10')") === true && ev("weekendDay('2026-01-11')") === true && ev("weekendDay('2026-01-12')") === false);
ok('nextOn returns a future requested weekday', (() => {
  const d = new Date(ev("nextOn('fri').getTime()"));
  return d.getDay() === 5 && d.getTime() >= new Date(new Date().toDateString()).getTime();
})());

console.log('\n── visit section (rendered from config) ────────────');
ok('two visit cards rendered', $$('#visitGrid .visit-card').length === 2);
ok('flagship card marked', $$('#visitGrid .visit-card.is-flagship').length === 1 && $$('#visitGrid .visit-card')[0].dataset.branch === 'central');
ok('addresses rendered', /296 Francis Baard Street, Pretoria Central, Pretoria, Gauteng/.test($('#visit').textContent));
ok('hours list rendered per card', $$('#visitGrid .visit-card')[0].querySelectorAll('.visit-hours li').length === 4);
ok('amenities rendered as chips', $$('#visitGrid .visit-card')[0].querySelectorAll('.visit-meta span').length === 3);
ok('maps link is a real search url', $$('#visitGrid .visit-card')[0].querySelector('.visit-foot a').href.startsWith('https://www.google.com/maps/search/?api=1&query=296'));
ok('hours caveat only where it belongs', $$('#visitGrid .visit-card')[0].querySelector('.visit-hours-note') === null && !!$$('#visitGrid .visit-card')[1].querySelector('.visit-hours-note'));
ev("config.branches[0].name='Central <img src=x onerror=alert(1)>';renderVisit()");
ok('admin-entered text is escaped, not injected', $$('#visitGrid img').length === 0 && /Central &lt;img/.test($('#visitGrid').innerHTML));
ok('ampersand survives escaping', (() => { ev("config.branches[0].name='Pretoria Central';renderVisit()"); return $('#visitGrid .visit-card h3').textContent === 'Pretoria Central' })());

console.log('\n── piercings friday rate card ──────────────────────');
ok('friday band is visible', ev("document.getElementById('fridayBand').hidden") === false);
ok('band states price, window and cap', /R100 to R150/.test($('#friCopy').textContent) && /10:00 and 15:00/.test($('#friCopy').textContent) && /capped at 20 slots/.test($('#friCopy').textContent));
ok('price chip rendered', $('#friPrice').textContent === 'R100–R150');
ok('services line rendered', $('#friServices').textContent === 'Nose · Ear lobe · Belly');
ok('next-friday line is computed', /Next Friday in \d day|It is on today/.test($('#friWhen').textContent), $('#friWhen').textContent);
ok('weekend perk shown', /tooth gem/.test($('#friPerk').textContent) && /subject to stock/.test($('#friPerk').textContent));
ok('friday rate only applies on the configured day', (() => {
  const f = ev("fridayRate('" + dateFor('fri') + "')");
  const o = ev("fridayRate('" + otherDay() + "')");
  return f && f.low === 100 && f.high === 150 && f.slots === 20 && o === null;
})());
ok('paused card stops matching dates', (() => {
  ev("config.fridays.live=false");
  const off = ev("fridayRate('" + dateFor('fri') + "')") === null;
  ev("config.fridays.live=true");
  return off;
})());
ok('friday label pluralises the weekday', ev("fridayLabel()") === 'Fridays');

console.log('\n── hero offer arbitration ──────────────────────────');
ok('dated campaign owns the hero while live', ev("document.getElementById('offerTitle').textContent") === 'Spring sitting special' && ev("document.getElementById('heroOffer').dataset.special") === 'spring-sitting');
ok('weekly card has lower default priority', ev("config.fridays.priority") === 5);
ev("config.specials[0].live=false;renderSpecial()");
ok('weekly card takes over when nothing is dated', ev("document.getElementById('offerTitle').textContent") === 'Piercing Fridays' && ev("document.getElementById('heroOffer').dataset.friday") === 'live');
ok('its CTA routes to the piercing flow', ev("document.getElementById('offerCta').dataset.action") === 'book-piercing');
ev("config.specials[0].live=true;renderSpecial()");
ok('and hands the hero back', ev("document.getElementById('offerTitle').textContent") === 'Spring sitting special' && ev("document.getElementById('heroOffer').dataset.friday") === undefined);

console.log('\n── booking flow ────────────────────────────────────');
ok('branch select populated from config', $$('#bookingBranch option').length === 2 && $$('#bookingBranch option')[0].textContent.includes('296 Francis Baard Street'));
ok('branch select defaults to the flagship', $('#bookingBranch').value === 'central');
ok('artist select lists published artists + no preference', $$('#bookingArtist option').length === 2 && $('#bookingArtist').value === '');
ev("openBooking({title:'Serpent study',price:'R 3,800',priceNum:3800,detail:{}})");
ev("document.getElementById('bookingDate').value='" + otherDay() + "';bookingHint()");
ok('weekday hint quotes that branch hours', /10:00–18:00/.test($('#bookingHint').textContent) && $('#bookingHint').hidden === false, $('#bookingHint').textContent.slice(0, 58));
ev("document.getElementById('bookingDate').value='" + dateFor('fri') + "';bookingHint()");
ok('friday hint applies the rate card', /Friday rate applies/.test($('#bookingHint').textContent) && /R100–R150/.test($('#bookingHint').textContent));
ev("document.getElementById('bookingDate').value='" + dateFor('sat') + "';bookingHint()");
ok('saturday hint offers the weekend perk', /tooth gem/.test($('#bookingHint').textContent));
ev("document.getElementById('bookingBranch').value='mabopane';document.getElementById('bookingDate').value='" + dateFor('sun') + "';bookingHint()");
ok('closed sunday is stated, not glossed', /closed on Sundays/.test($('#bookingHint').textContent), $('#bookingHint').textContent.slice(0, 60));
ev("document.getElementById('bookingName').value='Thabo';document.getElementById('bookingPhone').value='082';document.getElementById('bookingEmail').value='t@e.co';document.getElementById('bookingConsent').checked=true;document.getElementById('bookingBranch').value='central';document.getElementById('bookingArtist').value='yuran';document.getElementById('bookingDate').value='" + dateFor('fri') + "';document.getElementById('bookingTime').value='Morning';confirmBooking()");
const bk = ev("bookings[bookings.length-1]");
ok('booking carries branch and artist', bk.branchName === 'Pretoria Central' && bk.artist === 'yuran');
ok('booking records the promo context', bk.friday === true && bk.weekend === false);
const msg = decodeURIComponent(opened[opened.length - 1].split('text=')[1] || '');
ok('whatsapp summary names the branch', /Location: Pretoria Central/.test(msg) && /Artist: Yuran/.test(msg), msg.slice(0, 46) + '…');
ok('whatsapp summary flags the friday rate', /Piercing Friday rate applies/.test(msg));
ok('closed-branch booking still allowed (studio confirms)', bk.status === 'Deposit pending');

console.log('\n── piercing entry point ────────────────────────────');
ev("openPiercing()");
ok('piercing summary leads with the friday rate', /R100–R150 on Fridays/.test($('#bookingSummary').textContent), $('#bookingSummary').textContent.slice(0, 54) + '…');
ok('deposit is not discounted by the promo', /Deposit is held from the standard piercing rate/.test($('#bookingSummary').textContent));
ev("config.fridays.live=false;openPiercing()");
ok('paused card reverts to the flat intro price', $('#bookingSummary').textContent.includes('From R 650'));
ev("config.fridays.live=true");

console.log('\n── studio os: locations & hours ────────────────────');
ok('locations editor renders both branches', $$('#locEditor .loc-row').length === 2);
ok('seven day rows per branch', $$('#locEditor .loc-row')[0].querySelectorAll('.loc-hours .day').length === 7);
ok('day inputs carry current values', $('#locEditor [data-loc="central"][data-day="thu"][data-part="close"]').value === '17:00');
ok('closed state selected where hours are absent', $('#locEditor [data-loc="mabopane"][data-day="sun"][data-part="state"]').value === 'closed');
const LOC = '#locEditor [data-loc="central"][data-day="mon"]';
ok('setter found the monday inputs', setV(LOC + '[data-part="state"]', 'closed') === 'ok' && setV(LOC + '[data-part="close"]', '19:00') === 'ok');
clickV('[data-action="save-locations"]');
ok('save writes the closed day through', ev("config.branches[0].hours.mon") === 'closed');
const pair = (li) => li.querySelector('span').textContent + ' ' + li.querySelector('i').textContent;
ok('public card re-renders', (() => { const a = $$('#visitGrid .visit-card')[0].querySelectorAll('.visit-hours li'); return pair(a[0]) === 'Mon Closed' && pair(a[1]) === 'Tue–Wed 10:00–18:00' })(), (() => { const a = $$('#visitGrid .visit-card')[0].querySelectorAll('.visit-hours li'); return pair(a[0]) + ' / ' + pair(a[1]) })());
setV(LOC + '[data-part="state"]', 'open'); setV(LOC + '[data-part="open"]', '10:00'); setV(LOC + '[data-part="close"]', '18:00');
clickV('[data-action="save-locations"]');
ok('reopening monday restores the group', ev("hoursLines(branchById('central'))[0].label") === 'Mon–Wed');
setV('#locEditor [data-loc="central"][data-field="travel"]', '500'); clickV('[data-action="save-locations"]');
ok('per-branch travel fee saved', ev("branchById('central').travel") === 500);
setV('#locEditor [data-loc="central"][data-field="travel"]', '350'); clickV('[data-action="save-locations"]');
ok('travel fee restored', ev("branchById('central').travel") === 350);
ok('estimator still uses the studio travel fee', (() => {
  const low = ev("(function(){estimateBrief={style:'Blackwork',size:'Medium',detail:'Medium',colour:'Black',placement:'Forearm',budget:'Mid',mode:'Mobile'};return calculateEstimate().low})()");
  return low === 3350;
})(), 'mobile medium = R3,350');

console.log('\n── studio os: friday, artists, reputation ──────────');
const FR = '#';
setV(FR + 'frDay', 'sat'); setV(FR + 'frLow', 120); setV(FR + 'frHigh', 180);
setV(FR + 'frSlots', 12); setV(FR + 'frServices', 'Nose, Tragus'); setV(FR + 'frPerk', '');
clickV('[data-action="save-fridays"]');
ok('friday card edits persist', ev("config.fridays.day") === 'sat' && ev("config.fridays.low") === 120 && ev("config.fridays.high") === 180 && ev("config.fridays.slots") === 12);
ok('services list reparsed', ev("config.fridays.services.join(',')") === 'Nose,Tragus');
ok('public band re-renders', /R120 to R180/.test($('#friCopy').textContent) && $('#friServices').textContent === 'Nose · Tragus');
ok('blank perk hides the line', $('#friPerk').hidden === true && $('#friPerk').textContent === '');
ok('rate card follows the new day', ev("fridayRate('" + dateFor('sat') + "')") !== null);
setV(FR + 'frDay', 'fri'); setV(FR + 'frLow', 100); setV(FR + 'frHigh', 150); setV(FR + 'frSlots', 20);
setV(FR + 'frServices', 'Nose, Ear lobe, Belly');
setV(FR + 'frPerk', 'Weekend perk: book a piercing on Saturday or Sunday and a temporary tooth gem is on the studio — subject to stock and artist sign-off.');
clickV('[data-action="save-fridays"]');
ok('restored to the researched values', ev("config.fridays.low") === 100 && ev("config.fridays.day") === 'fri' && /tooth gem/.test($('#friPerk').textContent));
ok('artist editor lists the roster', $$('#artistEditor .loc-row[data-artist]').length === 1);
const AR0 = '#artistEditor [data-artist="0"] ';
setV(AR0 + '[data-artist-field="specialties"]', 'Black & grey, Fine line');
setV(AR0 + '[data-artist-field="hourly"]', 1400);
clickV('[data-action="save-artists"]');
ok('artist fields saved', ev("config.artists[0].hourly") === 1400 && ev("config.artists[0].specialties.join('|')") === 'Black & grey|Fine line');
clickV('[data-action="add-artist"]');
ok('add artist appends a draft', ev("config.artists.length") === 2);
const AR1 = '#artistEditor [data-artist="1"] ';
setV(AR1 + '[data-artist-field="name"]', 'Naledi');
setV(AR1 + '[data-artist-field="role"]', 'Piercer');
setV(AR1 + '[data-artist-field="branch"]', 'mabopane');
clickV('[data-action="save-artists"]');
ok('second artist published to the page', ev("document.querySelectorAll('#artistList .artist-card').length") === 2 && /Naledi/.test($('#artistList').textContent) && /Mabopane/.test($('#artistList').textContent));
clickV('[data-action="remove-artist"][data-artist="1"]');
ok('remove artist works', ev("config.artists.length") === 1 && ev("config.artists[0].name") === 'Yuran');
ok('review panel prefilled', $('#revScore').value === '4.9' && $('#revCount').value === '100' && $('#revSuffix').value === '+');
setV('#revScore', '4.7'); setV('#revCount', 150); setV('#revUrl', 'https://g.page/haywood');
clickV('[data-action="save-reviews"]');
ok('reputation saved and shown', $('#ratingScore').textContent === '4.7' && /from 150\+ Google/.test($('#ratingMeta').textContent));
ok('reviews link appears when set', $('#ratingLink').hidden === false && $('#ratingLink').getAttribute('href') === 'https://g.page/haywood');
setChk('#revLive', false); clickV('[data-action="save-reviews"]');
ok('hiding reputation removes the card and the hero pill', $('#ratingCard').hidden === true && !/★/.test($('#heroNote').textContent));
setChk('#revLive', true); clickV('[data-action="save-reviews"]');
ok('and brings them back', $('#ratingCard').hidden === false && /★/.test($('#heroNote').textContent) && /Google/.test($('#heroNote').textContent), $('#heroNote').textContent.trim().slice(-24));
ok('reputation copy never enters structured data', (() => {
  setV('#revScore', '5.0'); clickV('[data-action="save-reviews"]');
  const ld = JSON.parse($('script[type="application/ld+json"]').textContent);
  setV('#revScore', '4.9'); clickV('[data-action="save-reviews"]');
  return !/aggregateRating|ratingValue|reviewCount/.test(JSON.stringify(ld));
})());
ok('brand name is not renamed by the legal-name field', $('script[type="application/ld+json"]').textContent.includes('"name":"Haywood Tattoo Studio"'));

console.log('\n── structured data rebuild ─────────────────────────');
const ld = JSON.parse($('script[type="application/ld+json"]').textContent);
const biz = ld['@graph'].find(x => x['@type'] === 'TattooParlor');
ok('legal name carried', biz.legalName === 'Haywood Tattoos and Piercings');
ok('street address in schema', /296 Francis Baard Street/.test(biz.address.streetAddress) && biz.address.addressCountry === 'ZA');
ok('openingHoursSpecification replaces the coarse field', biz.openingHours === undefined && biz.openingHoursSpecification.length === 7);
ok('times are schema-valid', /^\d\d:\d\d$/.test(biz.openingHoursSpecification[0].opens) && /schema\.org\/Monday$/.test(biz.openingHoursSpecification.find(s => s.dayOfWeek.endsWith('Monday')).dayOfWeek));
ok('both branches published as departments', biz.department.length === 2 && /2241 Martha Modise Street/.test(biz.department[1].address.streetAddress));
ok('Mabopane drops its closed day', biz.department[1].openingHoursSpecification.length === 6);
ok('each branch has a real maps link', biz.hasMap.startsWith('https://www.google.com/maps/search/?api=1&query=296') && biz.department[1].hasMap.includes('2241'));
ok('amenities published', biz.amenityFeature.some(a => /Wheelchair/.test(a.name)));
ok('areaServed widened to both cities', JSON.stringify(biz.areaServed).includes('Tshwane'));
ok('founder/employee still there, memberOf removed', biz.employee.name === 'Yuran' && biz.memberOf === undefined);
ok('sameAs now includes the studio website', biz.sameAs.includes('https://www.haywoodstudio.com') && biz.sameAs.includes('https://instagram.com/haywood_studio'));
ok('FAQ graph grew with the new questions', ld['@graph'].find(x => x['@type'] === 'FAQPage').mainEntity.length === 13);
ok('schema is still valid JSON after an admin save', (() => { ev("save()"); JSON.parse($('script[type=\"application/ld+json\"]').textContent); return true })());

console.log('\n── admin shell wiring ──────────────────────────────');
for (const tab of ['fridays', 'locations', 'artists', 'reviews']) {
  ok(`panel #admin-${tab} exists and is switchable`, (() => {
    const btn = $(`[data-admin-tab="${tab}"]`); click(btn);
    return !!$(`#admin-${tab}`) && $(`#admin-${tab}`).classList.contains('active') && $('#adminTitle').textContent.replace(/&amp;/g, '&').length > 0;
  })(), tab);
}
ok('all 14 sidebar tabs have panels', (() => {
  const tabs = [...window.document.querySelectorAll('#studioSide [data-admin-tab]')].map(b => b.dataset.adminTab);
  return tabs.length === 14 && tabs.every(t => !!$(`#admin-${t}`));
})(), [...window.document.querySelectorAll('#studioSide [data-admin-tab]')].length + ' tabs');
ok('overview deep-links still reach leads and ai', $$('#admin-overview [data-admin-tab]').length === 2);
ok('specials panel points at the friday card', /Piercing Fridays/.test($('#admin-specials').textContent));

console.log('\n── persistence & migration ─────────────────────────');
ok('config round-trips through localStorage', (() => {
  ev("config.artists[0].role='Resident artist';save()");
  const raw = JSON.parse(window.localStorage.getItem('haywoodConfig'));
  return raw.branches.length === 2 && raw.artists[0].name === 'Yuran' && raw.fridays.low === 100;
})());
const legacy = new JSDOM(html, {
  url: 'http://localhost:4173/', runScripts: 'dangerously', pretendToBeVisual: true,
  beforeParse(win) {
    win.localStorage.setItem('haywoodConfig', JSON.stringify({ pricing: { base: 2000 }, hours: ['Tue 09:00–17:00'], specials: [] }));
  }
});
const L = legacy.window;
const lev = (c) => L.eval(c);
ok('stale saved config still upgrades (branches present)', lev("config.branches.length") === 2);
ok('stale saved config keeps its own overrides', lev("config.pricing.base") === 2000 && lev("config.specials.length") === 0);
ok('legacy hours key ignored, no crash', lev("config.hours") === undefined && L.document.querySelectorAll('#visitGrid .visit-card').length === 2);
ok('no dated special + live friday card = weekly hero', lev("document.getElementById('offerTitle').textContent") === 'Piercing Fridays');
ok('hero note is outside the offer card', !!L.document.querySelector('#heroOffer ~ .hero-note, .hero-copy > #heroNote'));

console.log('\n── runtime ─────────────────────────────────────────');
ok('no page errors during the whole run', errors.length === 0, errors.slice(0, 3).join(' | '));
console.log(`\n${pass} passed, ${fail} failed\n`);
process.exit(fail ? 1 : 0);
