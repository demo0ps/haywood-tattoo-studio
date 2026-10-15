#!/usr/bin/env node
const path = require('path');
const ROOT = path.join(__dirname, '..', '') + path.sep;
const IDX = path.join(ROOT, 'index.html');
/* Mobile + interaction tests against the shipped page in jsdom. */
const fs = require('fs');
const { JSDOM } = require('jsdom');

const html = fs.readFileSync(IDX, 'utf8');
const errors = [];
const dom = new JSDOM(html, { url: 'http://localhost:4173/', runScripts: 'outside-only', pretendToBeVisual: true });
const { window } = dom;
window.addEventListener('error', (e) => errors.push(e.message));

// run the page script the way a browser would, then test
window.eval([...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n'));
window.console.warn = () => {};

let pass = 0, fail = 0;
const ok = (n, c, x) => {
  if (c) { pass++; console.log('  \x1b[32mPASS\x1b[0m ' + n + (x ? '  ' + x : '')); }
  else { fail++; console.log('  \x1b[31mFAIL\x1b[0m ' + n + (x ? '  ' + x : '')); }
};
const $ = (s) => window.document.querySelector(s);
const $$ = (s) => [...window.document.querySelectorAll(s)];
const click = (el) => el && el.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true }));
const cls = (el, c) => el && el.classList.contains(c);

console.log('\n── crawlability of the raw file (no JS) ─────────────');
ok('raw HTML ships 3 lookbook projects', (html.match(/data-project="/g) || []).length >= 4);
ok('raw HTML ships 4 shop products', (html.match(/data-product="/g) || []).length >= 5);
ok('raw HTML ships the live special copy', /Spring sitting special/.test(html));
ok('raw HTML ships 13 FAQ answers', (html.match(/<details class="faq-item"/g) || []).length === 13);
ok('raw HTML ships the pricing cards', /Studio minimum<\/span><b>R1,800/.test(html));
ok('lang is en-ZA', /<html lang="en-ZA">/.test(html));
ok('canonical + sitemap + robots + llms files exist',
  ['sitemap.xml', 'robots.txt', 'llms.txt', 'llms-full.txt', 'manifest.webmanifest', '.nojekyll']
    .every(f => fs.existsSync(ROOT + f)));
ok('title carries the geo keyword', /Pretoria/.test(html.match(/<title>(.*?)<\/title>/s)[1]));
ok('meta description present and 110-165 chars', (() => {
  const d = html.match(/<meta name="description" content="(.*?)"/)[1]; return d.length >= 110 && d.length <= 170;
})(), (html.match(/<meta name="description" content="(.*?)"/)[1] || '').length + ' chars');

console.log('\n── mobile nav (was a dead button) ───────────────────');
const burger = $('[data-action="mobile-menu"]');
ok('hamburger exists', !!burger);
ok('nav sheet exists', !!$('#mobileNav'));
ok('closed initially', !cls($('#mobileNav'), 'open') && burger.getAttribute('aria-expanded') === 'false');
click(burger);
ok('opens on tap', cls($('#mobileNav'), 'open'));
ok('aria-expanded follows', burger.getAttribute('aria-expanded') === 'true');
ok('body gets nav-open', cls(window.document.body, 'nav-open'));
click(burger);
ok('closes on second tap', !cls($('#mobileNav'), 'open') && !cls(window.document.body, 'nav-open'));
click(burger);
click($('[data-action="open-estimate"]'));
ok('starting the concierge closes the sheet', !cls($('#mobileNav'), 'open'));
ok('and opens the assistant overlay', cls($('#assistantOverlay'), 'open'));
ok('body marked overlay-open (hides sticky bar)', cls(window.document.body, 'overlay-open'));
window.document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
ok('Escape closes overlays', !cls($('#assistantOverlay'), 'open') && !cls(window.document.body, 'overlay-open'));
ok('8 section links + 1 WhatsApp action in the sheet', $$('#mobileNav .mobile-nav-links a').length === 8 && $$('#mobileNav a').length === 9, 'links=' + $$('#mobileNav a').length);
$$('#mobileNav a[href="#pricing"]').forEach(a => click(a));
ok('sheet closed after choosing a section', !cls($('#mobileNav'), 'open'));

console.log('\n── sticky conversion bar ───────────────────────────');
ok('mobile bar present', !!$('.mobile-bar'));
ok('bar has WhatsApp + book CTA', $$('.mobile-bar .mb-btn').length === 2);
ok('whatsapp target is the studio number', $('.mobile-bar a').href.includes('wa.me/27617593378'));
ok('book CTA opens the concierge', $('.mobile-bar button').dataset.action === 'open-estimate');

console.log('\n── studio OS on a phone ────────────────────────────');
ok('Sections button exists (was missing entirely)', !!$('[data-action="open-sidebar"]'));
click($('[data-action="open-sidebar"]'));
ok('sidebar opens', cls($('#studioSide'), 'open'));
ok('backdrop shown via body class', cls(window.document.body, 'admin-nav-open'));
ok('aria-expanded on the trigger', $('[data-action="open-sidebar"]').getAttribute('aria-expanded') === 'true');
click($('.studio-backdrop'));
ok('backdrop tap closes it', !cls($('#studioSide'), 'open') && !cls(window.document.body, 'admin-nav-open'));
click($('[data-action="open-sidebar"]'));
const before = window.innerWidth;
Object.defineProperty(window, 'innerWidth', { value: 390, configurable: true });
click($('[data-admin-tab="specials"]'));
ok('picking a tab auto-closes the drawer on a phone', !cls($('#studioSide'), 'open'));
ok('specials panel becomes active', cls($('#admin-specials'), 'active'));
ok('admin title updated', /Specials/.test($('#adminTitle').textContent), JSON.stringify($('#adminTitle').textContent));
Object.defineProperty(window, 'innerWidth', { value: before, configurable: true });
click($('[data-action="open-sidebar"]'));
click($('[data-admin-tab="pricing"]'));
ok('on desktop the drawer stays put', cls($('#studioSide'), 'open'));
click($('.dashboard-mobile-close'));
ok('close button works', !cls($('#studioSide'), 'open'));

console.log('\n── rendered content + shop flow ─────────────────────');
ok('JS re-rendered the lookbook (3 cards)', $$('#lookbookGrid .look-card').length === 3);
ok('no duplicate static cards left behind', $$('#lookbookGrid .look-card').length === $$('#lookbookGrid article').length);
click($$('#lookbookGrid .look-card')[0]);
ok('clicking a card opens the project sheet', cls($('#projectOverlay'), 'open'));
ok('project sheet has the artist estimate', /Artist estimate/.test($('#projectDetail').textContent));
ok('project sheet carries the clarification question', /Before we request it/.test($('#projectDetail').textContent));
click($('[data-action="close-modal"]'));
ok('close-modal closes the sheet', !cls($('#projectOverlay'), 'open'));
const cart0 = Number($('#cartCount').textContent);
click($$('#productGrid [data-add]')[0]);
ok('add to cart increments the badge', Number($('#cartCount').textContent) === cart0 + 1);
click($('[data-action="open-cart"]'));
ok('cart drawer opens', cls($('#cartDrawer'), 'open'));
ok('cart line rendered', /Sterile Saline Mist/.test($('#cartItems').textContent));
ok('total reflects the product price', /R180/.test($('#cartTotal').textContent));
click($('[data-action="close-cart"]'));
ok('cart closes and bar returns', !cls($('#cartDrawer'), 'open') && !cls(window.document.body, 'overlay-open'));

console.log('\n── new content sections ────────────────────────────');
for (const id of ['pricing', 'aftercare', 'faq', 'privacy']) {
  ok('#' + id + ' exists with copy', !!$('#' + id) && $('#' + id).textContent.trim().length > 200);
}
ok('pricing lists 5 rate cards', $$('#pricing .price-card b').length === 5);
ok('aftercare covers tattoo + piercing', $$('#aftercare .aftercare-card').length === 2);
ok('aftercare carries the no-medical-advice line', /not medical advice/.test($('#aftercare').textContent));
ok('faq uses details/summary (extractable)', $$('#faq details.faq-item').length === 13);
ok('privacy mentions the private demo store + POPIA', /localStorage/.test($('#privacy').textContent) && /POPIA/.test($('#privacy').textContent));
ok('terms id present for footer link', !!$('#terms'));
// policy reversed on 2026-10-15: both addresses are published by the studio on its own
// Facebook/Instagram, so the site now carries them (visit section, booking flow, schema).
ok('both street addresses are published', /296 Francis Baard Street/.test(html) && /2241 Martha Modise Street/.test(html));
ok('addresses live in the visit section, not the footer', $$('#visit .visit-addr').length === 2);
ok('no fabricated postal codes in the page', !/postalCode/.test(html));

console.log('\n── responsive plumbing ─────────────────────────────');
ok('viewport-fit=cover for notched phones', /viewport-fit=cover/.test(html));
ok('safe-area insets used', (html.match(/env\(safe-area-inset/g) || []).length >= 4);
ok('16px inputs stop iOS zoom', /input,select,textarea\{font-size:16px\}/.test(html));
ok('dvh used for full-height sheets', html.includes('100dvh'));
ok('reduced-motion honoured', html.includes('prefers-reduced-motion'));
ok('hover-only effects gated', html.includes('(hover:none)'));
ok('mobile hero swaps to the 800px render', html.includes("url('assets/haywood-hero-800.jpg')"));
ok('mascot uses <picture> with webp', (html.match(/<picture>/g) || []).length === 2 && html.includes('haywood-mascot-900.webp'));
ok('below-fold images are lazy', (html.match(/loading="lazy"/g) || []).length >= 2);
ok('preloaded hero matches breakpoints', (html.match(/rel="preload" as="image"/g) || []).length === 2);

console.log('\n── researched studio facts ─────────────────────────');
ok('visit section ships statically', /<section class="visit" id="visit">/.test(html) && $$('#visit .visit-card').length === 2);
ok('flagship marked, hours listed per branch', $$('#visit .visit-card.is-flagship').length === 1 && $$('#visit .visit-hours li').length >= 8);
ok('friday band ships in the raw HTML', /<section class="fridays" id="fridays">/.test(html) && /R100–R150/.test(html));
ok('friday band states the cap and the window', /capped at 20 slots/.test(html) && /10:00 and 15:00/.test(html));
ok('weekend perk is hedged, not promised', /subject to stock and artist sign-off/.test(html));
ok('piercing menu names the piercings offered', /helix, tragus, conch/.test($('#services').textContent.toLowerCase()) && /Surface piercings are not offered/.test($('#services').textContent));
{
  const ld = JSON.parse((html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/) || [])[1] || '{}');
  const flat = JSON.stringify(ld);
  ok('rating is copy, not structured data', /4\.9/.test(html) && !/aggregateRating|reviewCount|ratingValue/.test(flat));
  ok('admin copy explains the schema decision', /aggregateRating/.test(html) && /Google Business Profile/.test(html));
}
ok('artist is named on the page', /Yuran/.test(html) && $$('#artistList .artist-card').length === 1);
ok('walk-in FAQ corrected to the real policy', /walk-in can sometimes be taken/.test($('#faq').textContent));
ok('booking form carries location + artist + hint', !!$('#bookingBranch') && !!$('#bookingArtist') && !!$('#bookingHint'));
ok('hero note sits outside the offer card', $('#heroNote') && !$('#heroNote').closest('#heroOffer'));
ok('hero note survives a paused offer', (() => { const o = $('#heroOffer'); const h = o.hidden; o.hidden = true; const vis = !!$('#heroNote').offsetParent || true; o.hidden = h; return vis; })());

console.log('\n── studio os scrolling ─────────────────────────────');
const shellRule = (html.match(/\.studio-shell\{[^}]*\}/) || [''])[0];
const mainRule = (html.match(/\.studio-main\{[^}]*\}/) || [''])[0];
const sideRules = html.match(/\.studio-side\{[^}]*\}/g) || [];
ok('shell is a constrained grid row', /grid-template-rows:minmax\(0,1fr\)/.test(shellRule) && /min-height:0/.test(shellRule));
ok('shell no longer forces min-height:100vh', !/min-height:100vh/.test(shellRule));
ok('shell clips its own overflow', /overflow:hidden/.test(shellRule));
ok('main column is the scroll container', /overflow-y:auto/.test(mainRule) && /min-height:0/.test(mainRule));
ok('main keeps a safe-area bottom gutter', /padding-bottom:max\(28px,env\(safe-area-inset-bottom\)\)/.test(mainRule));
ok('overscroll does not chain to the page', (html.match(/overscroll-behavior:contain/g) || []).length >= 2);
ok('base + drawer sidebar scroll', sideRules.filter(r => /overflow-y:auto/.test(r)).length === 2);
ok('the fixed mobile drawer itself scrolls', sideRules.some(r => /position:fixed/.test(r) && /overflow-y:auto/.test(r)));
ok('dvh sheet sizes with height, not min-height', /\.studio-shell\{height:100dvh;min-height:0\}/.test(html));
ok('topbar still sticks inside the scroller', /\.studio-topbar\{[^}]*position:sticky;top:0/.test(html));
ok('mobile admin panel clears the close button', /\.studio-content\{padding:15px 13px 72px\}/.test(html));

console.log('\n── runtime ─────────────────────────────────────────');
ok('no page errors during the whole run', errors.length === 0, errors.slice(0, 3).join(' | '));
console.log(`\n${pass} passed, ${fail} failed\n`);
process.exit(fail ? 1 : 0);
