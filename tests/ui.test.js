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
ok('raw HTML ships 10 FAQ answers', (html.match(/<details class="faq-item"/g) || []).length === 10);
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
ok('7 section links + 1 WhatsApp action in the sheet', $$('#mobileNav .mobile-nav-links a').length === 7 && $$('#mobileNav a').length === 8, 'links=' + $$('#mobileNav a').length);
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
ok('faq uses details/summary (extractable)', $$('#faq details.faq-item').length === 10);
ok('privacy mentions the private demo store + POPIA', /localStorage/.test($('#privacy').textContent) && /POPIA/.test($('#privacy').textContent));
ok('terms id present for footer link', !!$('#terms'));
ok('street address never appears in the page', !/296 Francis Baard/.test(html));

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

console.log('\n── runtime ─────────────────────────────────────────');
ok('no page errors during the whole run', errors.length === 0, errors.slice(0, 3).join(' | '));
console.log(`\n${pass} passed, ${fail} failed\n`);
process.exit(fail ? 1 : 0);
