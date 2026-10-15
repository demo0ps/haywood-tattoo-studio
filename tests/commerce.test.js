#!/usr/bin/env node
/* Round-6 suite: persisted catalog, courier/collection checkout, order management,
   product + lookbook editors, and the picture-upload pipeline.
   Usage: cd tests && npm i jsdom && node commerce.test.js */
const path = require('path');
const fs = require('fs');
const ROOT = path.join(__dirname, '..', '') + path.sep;
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const { JSDOM } = require('jsdom');

const dom = new JSDOM(html, { url: 'http://localhost:4173/', runScripts: 'dangerously', pretendToBeVisual: true });
const { window } = dom;
const errors = [];
window.addEventListener('error', e => errors.push(e.message));
window.console.error = (...a) => errors.push('console: ' + a.join(' '));
window.console.warn = () => {};

const opened = [];
window.open = (u) => { opened.push(u); return { focus() {} } };
const downloads = [];
window.HTMLAnchorElement.prototype.click = function () { downloads.push({ name: this.download, href: this.getAttribute('href') }); };

// jsdom decodes no images and has no canvas: stub the two things fitImage needs.
window.HTMLCanvasElement.prototype.getContext = () => ({ drawImage() {} });
window.HTMLCanvasElement.prototype.toDataURL = (type, q) =>
  String(type).includes('webp') ? 'data:image/webp;base64,WEBP' + q : '';
window.Image = class FakeImage {
  constructor() { this.naturalWidth = 3000; this.naturalHeight = 2000; }
  set src(v) { this._src = v; setTimeout(() => this.onload && this.onload(), 0); }
  get src() { return this._src }
};

const ev = c => window.eval(c);
const $ = s => window.document.querySelector(s);
const $$ = s => Array.from(window.document.querySelectorAll(s));
const click = el => el && el.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true }));
const txt = s => (($$(s)[0] || {}).textContent || '').replace(/\s+/g, ' ').trim();
let pass = 0, fail = 0;
const ok = (n, c, x) => {
  if (c) { pass++; console.log('  \x1b[32mPASS\x1b[0m ' + n + (x ? '  ' + x : '')); }
  else { fail++; console.log('  \x1b[31mFAIL\x1b[0m ' + n + (x ? '  ' + x : '')); }
};
const setV = (sel, val) => ev(`(()=>{const el=document.querySelector(${JSON.stringify(sel)});if(!el)return 'MISSING';el.value=${JSON.stringify(String(val))};return 'ok'})()`);
const fireV = (sel, type) => ev(`(()=>{const el=document.querySelector(${JSON.stringify(sel)});if(!el)return 'MISSING';el.dispatchEvent(new Event(${JSON.stringify(type)},{bubbles:true}));return 'ok'})()`);
const clickV = sel => ev(`(()=>{const el=document.querySelector(${JSON.stringify(sel)});if(!el)return 'MISSING:'+${JSON.stringify(sel)};el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));return 'ok'})()`);
const setMany = pairs => ev('(()=>{' + Object.entries(pairs).map(([k, v]) =>
  `const ${k.replace(/[^A-Za-z]/g, '_')}=document.getElementById('${k.slice(1)}');if(${k.replace(/[^A-Za-z]/g, '_')})${k.replace(/[^A-Za-z]/g, '_')}.value=${JSON.stringify(v)};`).join('') + '})()');
const tick = (n = 8) => new Promise(r => { let i = 0; const step = () => (++i >= n ? r() : setTimeout(step, 0)); step(); });
const toastIs = re => re.test(txt('#toast'));
const isOpen = sel => $(sel).classList.contains('open');

const pickFile = (ctlSel, name, type, bytes) => ev(`(()=>{const ctl=document.querySelector(${JSON.stringify(ctlSel)});if(!ctl)return 'NOCONTROL';
  const inp=ctl.querySelector('input[data-img-input]');if(!inp)return 'NOINPUT';
  const f=new File([new Uint8Array(${JSON.stringify(bytes)})],${JSON.stringify(name)},{type:${JSON.stringify(type)}});
  Object.defineProperty(inp,'files',{value:[f],configurable:true});
  inp.dispatchEvent(new Event('change',{bubbles:true}));return 'ok'})()`);

(async () => {
  ev('save();renderAdmin()');

  console.log('\n── catalog persistence ─────────────────────────────');
  ok('save() writes the catalog into config', ev("JSON.parse(localStorage.getItem('haywoodConfig')).products.length") === 4
    && ev("JSON.parse(localStorage.getItem('haywoodConfig')).lookbook.length") === 3);
  ok('shipping defaults live in config', ev('config.shipping.fee') === 120 && ev('config.shipping.freeOver') === 1500
    && ev('config.shipping.provinces.length') === 9);
  ev("products[0].price=199;save()");
  ok('a price edit survives a save', ev("JSON.parse(localStorage.getItem('haywoodConfig')).products[0].price") === 199);
  ev('products[0].price=180;save()');
  ok('lookbook edits persist too', (() => { ev("lookbook[0].title='Serpent Study';save()"); const r = ev("JSON.parse(localStorage.getItem('haywoodConfig')).lookbook[0].title"); ev("lookbook[0].title='Serpent / Sun Study';save()"); return r === 'Serpent Study' })());
  ok('legacy storage without a catalog keeps the defaults', (() => {
    const d2 = new JSDOM(html, { url: 'http://localhost:4173/', runScripts: 'dangerously', beforeParse(w) { w.localStorage.setItem('haywoodConfig', JSON.stringify({ pricing: { base: 2000 } })) } });
    const r = { products: d2.window.eval('products.length'), look: d2.window.eval('lookbook.length'), base: d2.window.eval('config.pricing.base') };
    d2.window.close();
    return r.products === 4 && r.look === 3 && r.base === 2000;
  })());
  ok('saved catalog rehydrates on the next load', (() => {
    const cfg = JSON.parse(ev("localStorage.getItem('haywoodConfig')"));
    cfg.products = [{ id: 'stored', name: 'Stored Only', desc: '', price: 55, type: 'aftercare', icon: 'bottle', live: true }];
    const d3 = new JSDOM(html, { url: 'http://localhost:4173/', runScripts: 'dangerously', beforeParse(w) { w.localStorage.setItem('haywoodConfig', JSON.stringify(cfg)) } });
    const r = { len: d3.window.eval('products.length'), name: d3.window.eval('products[0].name'), grid: d3.window.document.querySelectorAll('#productGrid .product').length };
    d3.window.close();
    return r.len === 1 && r.name === 'Stored Only' && r.grid === 1;
  })());

  console.log('\n── fulfilment + totals ─────────────────────────────');
  ok('three fulfilment routes', $$('#orderFulfilment option').length === 3 && !!$('#orderFulfilment [value="courier"]'));
  ok('address block hidden until courier is chosen', $('#orderAddressWrap').hidden === true);
  ok('fee maths comes from config', ev("shippingFee(1499,'courier')") === ev('config.shipping.fee')
    && ev("shippingFee(1500,'courier')") === 0 && ev("shippingFee(10,'collect-central')") === 0
    && ev("shippingFee(10,'collect-mabopane')") === 0);
  ev("cart.length=0;cart.push('saline','saline','healing-kit');renderCart();openCheckout()");
  ok('the bag aggregates quantities for checkout', ev('cartItems().length') === 2 && ev("cartItems().find(p=>p.id==='saline').qty") === 2);
  ok('collection is free', /Free/.test(txt('#checkoutTotals')) && !/120/.test(txt('#checkoutTotals')));
  const sub = ev('orderTotals().sub');
  setV('#orderFulfilment', 'courier'); fireV('#orderFulfilment', 'change');
  ok('courier fee is added to the total', ev('orderTotals().fee') === 120 && ev('orderTotals().total') === sub + 120);
  ok('the courier line names the service and the eta', /The Courier Guy/.test(txt('#checkoutTotals')) && !!$('#orderFulfilment [value="courier"]'));
  ok('province list is populated', $('#orderProvince').options.length === 11);
  ok('address block reveals itself', $('#orderAddressWrap').hidden === false);
  setV('#orderFulfilment', 'collect-central'); fireV('#orderFulfilment', 'change');
  ok('switching back to collection drops the fee', ev('orderTotals().fee') === 0);

  console.log('\n── the order record ────────────────────────────────');
  setV('#orderFulfilment', 'courier');
  setV('#orderName', 'Thoko M'); setV('#orderEmail', 'thoko@example.com'); setV('#orderPhone', '');
  clickV('[data-action="complete-order"]');
  ok('a phone number is required', ev('orders.length') === 0 && toastIs(/phone number is required/i));
  setV('#orderPhone', '082 555 1234');
  clickV('[data-action="complete-order"]');
  ok('a courier order needs a real address', ev('orders.length') === 0 && toastIs(/street address/i));
  setV('#orderStreet', '12 Pretorius St'); setV('#orderSuburb', 'Hateas'); setV('#orderCity', 'Pretoria');
  setV('#orderPostal', '0002'); setV('#orderProvince', 'Gauteng'); setV('#orderNote', 'Gift wrap please');
  clickV('[data-action="complete-order"]');
  const o = JSON.parse(ev('JSON.stringify(orders[0])'));
  ok('order captured with everything fulfilment needs', o && o.items.length === 2 && o.items[0].qty === 2
    && o.phone === '082 555 1234' && o.status === 'Unpaid' && o.shipFee === 120 && o.total === o.subTotal + 120,
    o ? 'items=' + o.items.length + ' total=' + o.total : 'no order');
  ok('address is stored for the courier', !!(o.address && o.address.city === 'Pretoria' && o.address.postal === '0002' && o.address.province === 'Gauteng'));
  ok('fulfilment + note recorded', o.fulfilment === 'courier' && o.fulfilmentLabel === 'Courier' && o.note === 'Gift wrap please');
  ok('history starts the timeline', o.history.length === 1 && o.history[0].status === 'Unpaid' && /Yoco/.test(o.history[0].note));
  ok('order persists to storage', ev("JSON.parse(localStorage.getItem('haywoodOrders'))[0].id") === o.id);
  ok('the bag empties after checkout', ev('cart.length') === 0 && $('#cartCount').textContent === '0');
  ok('checkout closed on success', !isOpen('#checkoutOverlay'));
  ev("cart.length=0;cart.push('healing-kit');renderCart();openCheckout()");
  ev("document.getElementById('orderName').value='Ana';document.getElementById('orderEmail').value='ana@example.com';"
    + "document.getElementById('orderPhone').value='0711112222';document.getElementById('orderFulfilment').value='collect-mabopane'");
  ev('completeOrder()');
  const o2 = JSON.parse(ev('JSON.stringify(orders[1])'));
  ok('collection orders carry a branch, no address', o2.fulfilment === 'collect-mabopane' && o2.branch === 'mabopane'
    && o2.address === null && o2.shipFee === 0);

  console.log('\n── order management ────────────────────────────────');
  ev('renderAdmin()');
  ok('every order gets a row', $$('#adminOrders .order-row').length === 2);
  const rowOf = id => $('#adminOrders .order-row[data-order="' + id + '"]');
  ok('row shows buyer, items and destination', (() => { const r = rowOf(o.id); return !!r && /Thoko M/.test(r.textContent) && /Sterile Saline Mist/.test(r.textContent) && /Pretorius St/.test(r.textContent) })());
  ok('the amount column carries the courier fee', /R1,?120|R 1,120/.test(rowOf(o.id).querySelector('.order-amt').textContent) || rowOf(o.id).querySelector('.order-amt').textContent.includes('120'));
  ok('summary line counts the book', /2 order\(s\)/.test(txt('#orderSummaryLine')) && /unpaid/.test(txt('#orderSummaryLine')), txt('#orderSummaryLine'));
  setV('#orderSearch', 'ana'); ev('renderAdminOrders()');
  ok('search narrows the list', $$('#adminOrders .order-row').length === 1 && /Ana/.test($('#adminOrders .order-row').textContent));
  setV('#orderSearch', ''); setV('#orderFilter', 'Shipped'); ev('renderAdminOrders()');
  ok('status filter works', $$('#adminOrders .order-row').length === 0);
  setV('#orderFilter', ''); ev('renderAdminOrders()');
  click(rowOf(o.id));
  ok('row click opens the detail drawer', $('#orderDetailCard').hidden === false && /Packing list/.test(txt('#orderDetail')));
  ok('packing list has quantities and line totals', $$('#orderDetail .order-items li').length === 2 && /2 ×/.test(txt('#orderDetail .order-items li')));
  ok('buyer contacts are actionable', !!$('#orderDetail a[href="tel:0825551234"]') && !!$('#orderDetail a[href="mailto:thoko@example.com"]'));
  ok('destination shown for courier', /Pretorius St/.test(txt('#orderDetail')) && /Gauteng/.test(txt('#orderDetail')));
  click($('#orderDetailCard [data-action="close-order-detail"]'));
  ok('collection drawer names the branch', (() => { click(rowOf(o2.id)); return /Mabopane/.test(txt('#orderDetail')) })());
  click($('#orderDetailCard [data-action="close-order-detail"]'));
  ev(`(()=>{const s=document.querySelector('[data-order="${o.id}"] select[data-order-status]');s.value='Paid';s.dispatchEvent(new Event('change',{bubbles:true}))})()`);
  ok('status select advances the workflow', ev("orders.find(o=>o.name==='Thoko M').status") === 'Paid'
    && ev("orders.find(o=>o.name==='Thoko M').history.length") === 2
    && ev("orders.find(o=>o.name==='Thoko M').history[1].status") === 'Paid'
    && ev("orders.find(o=>o.name==='Thoko M').history[1].at.length") > 5);
  click(rowOf(o.id));
  ok('drawer shows the current state', new RegExp(o.id).test(txt('#orderDetailId')));
  click($('#orderDetail [data-action="order-advance"]'));
  ok('drawer advances to the next stage', ev("orders.find(o=>o.name==='Thoko M').status") === 'Packed');
  ev("orders.forEach(o=>o.status='Delivered');renderAdmin()");
  click($('#adminOrders .order-row'));
  ok('Delivered is terminal', $('#orderDetail [data-action="order-advance"]').textContent.trim() === 'Mark as Delivered');
  setV('#orderTracking', 'CGS-99887766');
  click($('#orderDetail [data-action="order-save-note"]'));
  ok('tracking number saved on the order', ev("orders.find(o=>o.tracking).tracking") === 'CGS-99887766'
    && ev("JSON.parse(localStorage.getItem('haywoodOrders')).find(o=>o.tracking).tracking") === 'CGS-99887766');
  const bcsv = downloads.length;
  clickV('[data-action="export-orders"]');
  const csv = decodeURIComponent(downloads[bcsv].href.split(',').slice(1).join(','));
  ok('CSV exports a row per order', downloads.length === bcsv + 1 && downloads[bcsv].name === 'haywood-orders.csv'
    && csv.split('\r\n').length === ev('orders.length') + 1);
  ok('CSV header covers fulfilment', csv.startsWith('id,created,status,name,phone,email,items,subTotal,shipFee,total,fulfilment,collectionBranch,street,suburb,city,province,postal,tracking,note'));
  ok('CSV line has items, city and tracking', /Saline Mist x2/.test(csv) && /Pretoria/.test(csv) && /CGS-99887766/.test(csv));
  ev('orders.length=0;orders.push({id:"ORD-9",created:"now",name:\'Bo "The Big" Kamva\',phone:"082",email:"b@e.com",items:[{id:"a",name:\'Hoop "Classic"\',price:10,qty:1}],subTotal:10,shipFee:0,total:10,fulfilment:"collect-central",fulfilmentLabel:"Collect · Pretoria Central",address:null,branch:"central",note:"",status:"Unpaid",tracking:"",history:[]});renderAdmin()');
  const d2n = downloads.length;
  clickV('[data-action="export-orders"]');
  const csv2 = decodeURIComponent(downloads[d2n].href.split(',').slice(1).join(','));
  ok('double quotes in data survive CSV escaping', /""The Big""/.test(csv2) && /""Classic""/.test(csv2));
  ev('orders.length=0;orders.push({id:"ORD-12",created:"now",name:"Naledi",phone:"0821112222",email:"n@e.com",items:[{id:"saline",name:"Sterile Saline Mist",price:180,qty:2}],subTotal:360,shipFee:120,total:480,fulfilment:"courier",fulfilmentLabel:"Courier",address:{street:"1 Berg St",suburb:"Heartbeat",city:"Mabopane",province:"North West",postal:"0200"},note:"",branch:"central",status:"Packed",tracking:"",history:[]});renderAdmin();showOrderDetail("ORD-12")');
  const wBefore = opened.length;
  click($('#orderDetailCard [data-action="order-whatsapp"]'));
  const wa = decodeURIComponent(opened[wBefore] || '');
  ok('WhatsApp handoff uses the buyer number and the order', /wa\.me\/27821112222/.test(opened[wBefore] || '')
    && /ORD-12/.test(wa) && /Packed/.test(wa) && /Saline/.test(wa));

  console.log('\n── product editor ──────────────────────────────────');
  ev('renderAdmin()');
  ok('one editable row per product', $$('#adminProducts .loc-row[data-prod]').length === 4);
  ok('row has the picture control', !!$('#adminProducts .loc-row[data-prod="0"] .imgctl input[data-img-input]'));
  clickV('[data-action="new-product"]');
  ok('the dead button now creates a draft', $$('#adminProducts .loc-row[data-prod]').length === 5 && ev('products[4].name') === '');
  setV('#adminProducts .loc-row[data-prod="4"] [data-prod-field="name"]', 'Serpent Balm');
  setV('#adminProducts .loc-row[data-prod="4"] [data-prod-field="price"]', '240');
  setV('#adminProducts .loc-row[data-prod="4"] [data-prod-field="type"]', 'jewelry');
  clickV('[data-action="save-products"]');
  ok('product edits reach the shop grid', /Serpent Balm/.test(txt('#productGrid')) && /R\s?240/.test(txt('#productGrid')));
  ok('and into the saved config', ev("JSON.parse(localStorage.getItem('haywoodConfig')).products[4].name") === 'Serpent Balm'
    && ev("JSON.parse(localStorage.getItem('haywoodConfig')).products[4].type") === 'jewelry');
  ev('products[4].live=false;save();renderProducts();renderAdmin()');
  ok('unpublishing hides it from the shop but keeps it in admin', !/Serpent Balm/.test(txt('#productGrid'))
    && $$('#adminProducts .loc-row[data-prod]').length === 5);
  ev('products[4].live=true;save();renderProducts();renderAdmin()');
  ok('republishing puts it back', /Serpent Balm/.test(txt('#productGrid')));
  click($('#adminProducts .loc-row[data-prod="4"] [data-action="remove-product"]'));
  ok('remove drops it everywhere', ev('products.length') === 4 && !/Serpent Balm/.test(txt('#productGrid')));
  ok('a price change re-prices the bag', (() => {
    ev("cart.length=0;cart.push('saline');renderCart()");
    const t1 = $('#cartTotal').textContent;
    ev("products[0].price=200;save();renderCart()");
    const t2 = $('#cartTotal').textContent;
    ev('products[0].price=180;save();renderCart()');
    return t1 !== t2;
  })());

  console.log('\n── lookbook editor ─────────────────────────────────');
  ok('one row per project', $$('#adminLookbook .loc-row[data-look]').length === 3);
  ok('availability + category are choices, not free text', $$('#adminLookbook .loc-row[data-look="0"] select[data-look-field="status"] option').length === 5
    && $$('#adminLookbook .loc-row[data-look="0"] select[data-look-field="category"] option').length === 4);
  setV('#adminLookbook .loc-row[data-look="0"] [data-look-field="title"]', 'Serpent Sun');
  setV('#adminLookbook .loc-row[data-look="0"] [data-look-field="questions"]', 'How much skin?\nAny scars there?');
  setV('#adminLookbook .loc-row[data-look="0"] [data-look-field="tags"]', 'blackwork, serpent');
  setV('#adminLookbook .loc-row[data-look="0"] [data-look-field="priceNum"]', '4100');
  clickV('[data-action="save-look"]');
  ok('questions become a list the concierge can ask', ev('lookbook[0].questions.length') === 2 && ev("lookbook[0].questions[1]") === 'Any scars there?');
  ok('tags and lead price persist', ev("lookbook[0].tags.join('|')") === 'blackwork|serpent' && ev('lookbook[0].priceNum') === 4100);
  ok('the card re-renders with the new title', /Serpent Sun/.test(txt('#lookbookGrid')));
  clickV('[data-action="new-look"]');
  ok('a draft project starts unpublished', ev('lookbook.length') === 4 && $$('#lookbookGrid .look-card').length === 3
    && ev('lookbook[3].live') === false);
  ev('lookbook.pop();save();renderLookbook();renderAdmin()');

  console.log('\n── picture uploads ────────────────────────────────');
  ok('a picture upload keeps unsaved text in the same editor', await (async () => {
    setV('#adminProducts .loc-row[data-prod="2"] [data-prod-field="name"]', 'Red Labret V2');
    pickFile('#adminProducts .loc-row[data-prod="2"] .imgctl', 'x.jpg', 'image/jpeg', [1]);
    await tick();
    const kept = ev('products[2].name') === 'Red Labret V2' && ev('!!products[2].image') === true;
    ev('delete products[2].image;products[2].name="Red Stone Labret";save();renderProducts();renderAdmin()');
    return kept;
  })());
  ok('naming follows the slot and the id', ev("assetName('lookbook','serpent-sun','webp')") === 'lookbook-serpent-sun.webp'
    && ev("assetName('product','healing-kit','webp')") === 'product-healing-kit.webp'
    && ev("assetName('fridays','fridays')") === 'piercing-fridays.webp');
  ok('asset name slugifies awkward ids', ev("assetName('lookbook','Serpent & Sun!','webp')") === 'lookbook-serpent-sun.webp');
  ok('generated art is the default (no img tags yet)', !$('#productGrid .product-art img') && !$('#lookbookGrid .look-image img'));
  ok('the control explains that state', /Generated artwork in place/.test(txt('#adminProducts .loc-row[data-prod="0"] .imgctl')));
  ok('the file pick reaches the page', pickFile('#adminProducts .loc-row[data-prod="0"] .imgctl', 'photo.png', 'image/png', [1, 2, 3]) === 'ok');
  await tick();
  const ref = JSON.parse(ev('JSON.stringify(products[0].image)'));
  ok('upload replaces the generated art in the model', !!ref && ref.kind === 'data' && ref.pending === true && ref.type === 'webp'
    && ref.width === 1400 && ref.height === 933, ref.width + 'x' + ref.height + ' ' + ref.type);
  ok('the tile renders the photo with alt text', !!$('#productGrid .product-art img.photo-fill[alt="Sterile Saline Mist"]')
    && /has-photo/.test($('#productGrid .product-art').className));
  ok('the admin control reports what it measured', /1400×933/.test(txt('#adminProducts .loc-row[data-prod="0"] .imgctl .small'))
    && /this browser only/.test(txt('#adminProducts .loc-row[data-prod="0"] .imgctl .small')));
  const dl = downloads.length;
  click($('#adminProducts .loc-row[data-prod="0"] [data-action="img-export"]'));
  ok('export downloads a repo-ready filename', downloads.length === dl + 1 && downloads[dl].name === 'product-saline.webp'
    && /^data:image\/webp;base64,/.test(downloads[dl].href));
  const ref2 = JSON.parse(ev('JSON.stringify(products[0].image)'));
  ok('export flips the reference to /assets', ref2.kind === 'asset' && ref2.src === 'assets/product-saline.webp' && ref2.pending === true);
  ok('the preview still shows while uncommitted', $('#productGrid .product-art img').getAttribute('src').indexOf('data:image/webp') === 0);
  click($('#adminProducts .loc-row[data-prod="0"] [data-action="img-commit"]'));
  const ref3 = JSON.parse(ev('JSON.stringify(products[0].image)'));
  ok('commit serves the file from the repo', ref3.pending === false && ref3.src === 'assets/product-saline.webp' && ref3.local === undefined);
  ok('committed path is what visitors load', $('#productGrid .product-art img').getAttribute('src') === 'assets/product-saline.webp');
  ok('and it is in the saved config', ev("JSON.parse(localStorage.getItem('haywoodConfig')).products[0].image.src") === 'assets/product-saline.webp');
  ok('committed payload no longer carries the fat', ev("JSON.stringify(config.products[0].image).length") < 200);
  click($('#adminProducts .loc-row[data-prod="0"] [data-action="img-clear"]'));
  ok('remove falls back to generated artwork', ev('!products[0].image') === true && !$('#productGrid .product-art img'));
  ok('the primary card picture is separate from the gallery', ev("lookbook[0].image") === undefined);
  pickFile('#adminLookbook .loc-row[data-look="0"] .imgctl[data-imgmultiple]', 'a.jpg', 'image/jpeg', [4, 5]);
  await tick();
  pickFile('#adminLookbook .loc-row[data-look="0"] .imgctl[data-imgmultiple]', 'b.jpg', 'image/jpeg', [6, 7]);
  await tick();
  ok('extra shots collect into a gallery', ev('(lookbook[0].gallery||[]).length') === 2
    && ev('(lookbook[0].gallery||[]).every(g=>g.kind===\'data\')') === true);
  ok('a gallery upload leaves the card picture alone', ev('lookbook[0].image') === undefined
    && ev("Array.isArray(lookbook[0].image)") === false);
  ok('gallery exports get their own filenames', ev("assetName('lookbook','serpent-sun','webp','gallery',1)") === 'lookbook-serpent-sun-gallery-1.webp');
  ok('the project detail renders the gallery', (() => { clickV('[data-project="serpent-sun"]'); return $$('#projectDetail .look-gallery img').length === 2 })());
  ev('closeOverlays();lookbook[0].gallery=[];save();renderLookbook();renderAdmin()');
  pickFile('#adminLookbook .loc-row[data-look="1"] .imgctl:not([data-imgmultiple])', 'hero.jpg', 'image/jpeg', [8]);
  await tick();
  ok('the card picture drives the grid', ev('!!lookbook[1].image') === true && $$('#lookbookGrid .look-image img').length === 1);
  ok('availability still shows over a photo', !!$('#lookbookGrid .look-image.has-photo .availability'));
  ev('delete lookbook[1].image;save();renderLookbook();renderAdmin()');
  pickFile('#friImage .imgctl', 'friday.jpg', 'image/jpeg', [9]);
  await tick();
  ok('the Friday band takes its own picture', ev('!!config.fridays.image') === true && !!$('#fridayArt img'));
  ev('delete config.fridays.image;save();renderFriday();renderAdmin()');
  ok('clearing it removes the band art', !$('#fridayArt img') && $('#fridayArt').hidden === true);
  ok('each published special gets a picture slot', $$('#adminSpecials .special-row .imgctl').length === ev('config.specials.length'));
  ev("(()=>{const sp=config.specials[0];if(!sp)return;sp.image={kind:'data',src:'data:image/webp;base64,XX',local:'data:image/webp;base64,XX',width:1200,height:600,type:'webp',pending:true};sp.start=null;sp.end=null;sp.live=true;save();renderSpecial()})()");
  ok('a special with a photo paints the hero card', $('#offerArt').hidden === false && !!$('#offerArt img'));
  ev("(()=>{const sp=config.specials[0];if(sp){delete sp.image;sp.live=false;renderSpecial()}})()");
  ok('the hero art clears when the offer stops applying', $('#offerArt').hidden === true && $('#offerArt').innerHTML === '');
  pickFile('#artistEditor .loc-row[data-artist="0"] .imgctl', 'face.jpg', 'image/jpeg', [11]);
  await tick();
  ok('artist portraits upload and render publicly', ev('!!config.artists[0].portrait') === true && !!$('#artistList .artist-photo'));
  ev('delete config.artists[0].portrait;save();renderArtists();renderAdmin()');
  ok('removing the portrait returns the text card', !$('#artistList .artist-photo') && /Yuran/.test(txt('#artistList')));
  pickFile('#adminProducts .loc-row[data-prod="1"] .imgctl', 'notes.txt', 'text/plain', [1, 2]);
  await tick();
  ok('non-images are refused with a readable message', toastIs(/not an image/i) && ev('!products[1].image') === true);
  const upSrc = (html.match(/function onImagePicked[\s\S]{0,700}/) || [''])[0];
  ok('the upload path never pretends there is a server', !!upSrc && !/fetch\(|XMLHttpRequest|FormData|axios/.test(upSrc));

  console.log('\n── delivery settings ───────────────────────────────');
  ok('the shop states the fulfilment promise', /Courier nationwide R120/.test(txt('#shipNote'))
    && /free over R1,?500/.test(txt('#shipNote').replace(/\s/g,' ')) && /Free collection at Pretoria Central or Mabopane/.test(txt('#shipNote')), txt('#shipNote'));
  ok('the commerce panel now covers products, delivery, orders and the drawer', (() => {
    const cards = $$('#admin-commerce .admin-card');
    const heads = cards.map(c => ((c.querySelector('h3') || {}).textContent || '').trim());
    return cards.length === 4 && heads[0] === 'Commerce & orders' && heads[1] === 'Delivery' && heads[2] === 'Orders'
      && cards[3].id === 'orderDetailCard' && !!$('#adminShipFee') && !!$('#adminOrders') && !!$('#adminProducts');
  })(), $$('#admin-commerce .admin-card h3').map(h => h.textContent.trim()).join(' | '));
  setV('#adminShipFee', '95'); setV('#adminShipFree', '2000'); setV('#adminShipEta', '3–5 working days');
  clickV('[data-action="save-shipping"]');
  ok('fee changes land in config and storage', ev('config.shipping.fee') === 95 && ev('config.shipping.freeOver') === 2000
    && ev("JSON.parse(localStorage.getItem('haywoodConfig')).shipping.eta") === '3–5 working days');
  ok('the shop line follows the settings', /R95/.test(txt('#shipNote').replace(/\s/g, '')) && /free over R2,?000/.test(txt('#shipNote')));
  ok('checkout threshold follows too', ev("shippingFee(1999,'courier')") === 95 && ev("shippingFee(2000,'courier')") === 0);
  ev("config.shipping.fee=120;config.shipping.freeOver=1500;config.shipping.eta='2–4 working days';save();renderShipNote();renderAdmin()");
  ok('reverting restores the original maths', ev("shippingFee(1499,'courier')") === 120 && /R120/.test(txt('#shipNote').replace(/\s/g, '')));
  ok('the delivery inputs read back from config', $('#adminShipFee').value === '120' && $('#adminShipFree').value === '1500'
    && $('#adminShipEta').value === '2–4 working days');
  ev("products.forEach(p=>p.live=false);save();renderProducts()");
  ok('an emptied shelf explains itself', /Nothing on the shelf right now/.test(txt('#productGrid'))
    && $$('#productGrid .product').length === 0);
  ev("products.forEach(p=>p.live=true);save();renderProducts()");
  ok('and comes back when products are republished', $$('#productGrid .product').length === 4);

  console.log('\n── storage guards ──────────────────────────────────');
  ev("products[0].image={kind:'data',src:'data:image/webp;base64,'+'A'.repeat(3000000),local:'data:image/webp;base64,'+'A'.repeat(3000000),pending:true,width:1400,height:933,type:'webp'}");
  const realSet = window.localStorage.setItem.bind(window.localStorage);
  window.localStorage.setItem = (k, v) => { if (k === 'haywoodConfig') throw new Error('QuotaExceededError'); return realSet(k, v) };
  let threw = null;
  try { ev('save()') } catch (e) { threw = e.message }
  window.localStorage.setItem = realSet;
  ok('a full browser store does not crash the dashboard', threw === null, threw || 'no throw');
  ok('it retries with the picture payload stripped', (() => {
    const c = JSON.parse(ev("localStorage.getItem('haywoodConfig')"));
    const im = c.products[0].image;
    return !!(im && im.src && !im.local);
  })());
  ev('delete products[0].image;save();renderProducts();renderAdmin()');
  ev("cart.length=0;renderCart();openCheckout()");
  ok('the empty bag is refused politely', /bag is empty/i.test(txt('#toast')) && !isOpen('#checkoutOverlay'));

  console.log('\n── runtime ─────────────────────────────────────────');
  ok('no page errors during the whole run', errors.length === 0, errors.slice(0, 3).join(' | '));
  console.log(`\n${pass} passed, ${fail} failed\n`);
  process.exit(fail ? 1 : 0);
})();
