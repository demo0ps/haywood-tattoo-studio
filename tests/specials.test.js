#!/usr/bin/env node
const path = require('path');
const ROOT = path.join(__dirname, '..', '') + path.sep;
const IDX = path.join(ROOT, 'index.html');
/* Drives the REAL functions shipped inside index.html via jsdom.
   Nothing here re-implements the pricing maths — every assertion calls the
   page's own calculateEstimate / renderSpecial / admin handlers. */
const fs = require('fs');
const { JSDOM } = require('jsdom');

const html = fs.readFileSync(IDX, 'utf8');
const errors = [];
const dom = new JSDOM(html, {
  url: 'http://localhost:4173/',
  runScripts: 'dangerously',
  pretendToBeVisual: true,
  resources: undefined,
});
const win = dom.window;
win.addEventListener('error', (e) => errors.push('window error: ' + e.message));
win.console.error = (...a) => errors.push('console.error: ' + a.join(' '));
win.console.warn = () => {};
let opened = [];
win.open = (u) => { opened.push(u); return { focus() {} }; };

const ev = (code) => win.eval(code);
let pass = 0, fail = 0;
const ok = (name, cond, extra) => {
  if (cond) { pass++; console.log('  \x1b[32mPASS\x1b[0m ' + name + (extra ? '  ' + extra : '')); }
  else { fail++; console.log('  \x1b[31mFAIL\x1b[0m ' + name + (extra ? '  ' + extra : '')); }
};
const near = (a, b) => Math.abs(Number(a) - Number(b)) < 1;

setTimeout(() => {
  console.log('\n── load ─────────────────────────────────────────────');
  ok('page scripts ran without errors', errors.length === 0, errors.slice(0, 3).join(' | '));
  ok('config.specials seeded', ev('config.specials.length') === 1);
  ok('special id present', ev('config.specials[0].id') === 'spring-sitting');

  console.log('\n── state machine ────────────────────────────────────');
  ok('spring special is live', ev('specialState(config.specials[0])') === 'live');
  ok('activeSpecial() finds it', ev('activeSpecial() && activeSpecial().title') === 'Spring sitting special');
  ev("config.specials.push({id:'t-off',live:false,title:'off',discount:{type:'percent',value:5}})");
  ok('paused special reports off', ev("specialState(config.specials[1])") === 'off');
  ev("config.specials.push({id:'t-future',live:true,title:'soon',start:'2030-01-01',end:'2030-02-01',discount:{type:'percent',value:5}})");
  ok('future window reports scheduled', ev("specialState(config.specials[2])") === 'scheduled');
  ev("config.specials.push({id:'t-past',live:true,title:'old',start:'2020-01-01',end:'2020-02-01',discount:{type:'percent',value:5}})");
  ok('past window reports expired', ev("specialState(config.specials[3])") === 'expired');
  ok('expired/paused never win: still spring', ev("activeSpecial().id") === 'spring-sitting');
  ev("config.specials=config.specials.slice(0,1)");

  console.log('\n── scope guards ─────────────────────────────────────');
  ok('tattoo scope matches', ev("specialFor('tattoo') && specialFor('tattoo').id") === 'spring-sitting');
  ok('piercing excluded', ev("specialFor('piercing')") === null);
  ok('flash excluded', ev("specialFor('flash')") === null);
  ev("config.specials[0].appliesTo='all'");
  ok('appliesTo=all covers piercing', ev("specialFor('piercing') && specialFor('piercing').id") === 'spring-sitting');
  ev("config.specials[0].appliesTo='mobile'");
  ok('appliesTo=mobile excludes tattoo scope', ev("specialFor('tattoo')") === null);
  ev("config.specials[0].appliesTo='tattoo'");

  console.log('\n── estimator maths ──────────────────────────────────');
  // below the R4,000 threshold -> no discount, gap reported
  ev("estimateBrief={style:'Fine-line',size:'Small',detail:'Low',placement:'Forearm / wrist',mode:'Studio',colour:'Black'}");
  let small = JSON.parse(ev('JSON.stringify(calculateEstimate())'));
  ok('small brief keeps base low', near(small.low, 1800), 'low=' + small.low);
  ok('small brief flags threshold miss', small.special && small.special.missed === true);
  ok('small brief gap = 2,200', near(small.special.gap, 2200), 'gap=' + small.special.gap);
  ok('small brief no discount applied', near(small.special.cut, 0));

  // large/colour/detail-heavy -> 10% off, clamped above the studio minimum
  ev("estimateBrief={style:'Colour',size:'Large',detail:'High',placement:'Ribs / torso',mode:'Mobile'}");
  let big = JSON.parse(ev('JSON.stringify(calculateEstimate())'));
  ok('big brief low = 5,805 after 10%', near(big.low, 5805), 'low=' + big.low);
  ok('big brief high = 8,805 after 10%', near(big.high, 8805), 'high=' + big.high);
  ok('big brief cut = 645', near(big.special.cut, 645), 'cut=' + big.special.cut);
  ok('deposit recalculated on discounted low', near(big.deposit, Math.round(5805 * 0.3)), 'deposit=' + big.deposit);
  const undiscountedLow = 1800 + 1700 + 1400 + 700 + 500 + 350;
  ok('undiscounted would have been 6,450', undiscountedLow === 6450);

  // absurd fixed discount must never push below the studio minimum
  ev("config.specials[0].discount={type:'amount',value:999999}");
  let clamp = JSON.parse(ev('JSON.stringify(calculateEstimate())'));
  ok('fixed discount clamps at the minimum charge', near(clamp.low, 1800), 'low=' + clamp.low);
  ok('clamped cut = 4,650', near(clamp.special.cut, 4650), 'cut=' + clamp.special.cut);
  ev("config.specials[0].discount={type:'percent',value:10}");

  // display-only specials must not touch the money
  ev("config.specials[0].discount={type:'none',value:0}");
  let disp = JSON.parse(ev('JSON.stringify(calculateEstimate())'));
  ok('display-only special leaves price untouched', near(disp.low, 6450) && near(disp.special.cut, 0), 'low=' + disp.low);
  ev("config.specials[0].discount={type:'percent',value:10}");

  console.log('\n── hero render ──────────────────────────────────────');
  ok('hero headline rendered', ev("document.getElementById('offerTitle').textContent") === 'Spring sitting special');
  ok('hero flag rendered', ev("document.getElementById('offerFlag').textContent") === 'Studio special');
  ok('hero copy rendered', ev("document.getElementById('offerCopy').textContent").length > 40);
  ok('fine print includes end date', /Ends \d/.test(ev("document.getElementById('offerFine').textContent")), ev("document.getElementById('offerFine').textContent").slice(0, 34));
  ok('countdown rendered', /day/.test(ev("document.getElementById('offerCount').textContent")), ev("document.getElementById('offerCount').textContent"));
  ok('scope label rendered', ev("document.getElementById('offerScope').textContent") === 'Custom tattoo work');
  ok('card visible while live', ev("document.getElementById('heroOffer').hidden") === false);
  ev("config.specials[0].live=false;renderSpecial()");
  ok('card hidden when paused', ev("document.getElementById('heroOffer').hidden") === true);
  ev("config.specials[0].end='2020-02-01';config.specials[0].live=true;renderSpecial()");
  ok('card hidden after expiry', ev("document.getElementById('heroOffer').hidden") === true);
  ev("config.specials[0].end='2026-11-30';renderSpecial()");
  ok('card returns when back in range', ev("document.getElementById('heroOffer').hidden") === false);

  console.log('\n── admin CRUD ───────────────────────────────────────');
  ok('admin list rendered', ev("document.querySelectorAll('#adminSpecials .special-row').length") === 1);
  ok('status text present', ev("document.getElementById('specialStatus').textContent").includes('1 live now'), ev("document.getElementById('specialStatus').textContent").trim());
  ev("document.getElementById('spTitle').value='Piercing week';document.getElementById('spFlag').value='Flash week';document.getElementById('spCopy').value='Test copy';document.getElementById('spType').value='amount';document.getElementById('spValue').value=300;document.getElementById('spMin').value=1000;document.getElementById('spScope').value='piercing';document.getElementById('spStart').value='2026-12-01';document.getElementById('spEnd').value='2026-12-08';document.getElementById('spTerms').value='Test terms';document.getElementById('spLive').checked=true;document.querySelector('[data-action=\"save-special\"]').click()");
  ok('new special saved', ev('config.specials.length') === 2, 'ids=' + ev('config.specials.map(s=>s.id).join(",")'));
  ok('scheduled special does not apply yet', ev("specialFor('piercing')") === null);
  ok('tattoo special still active for tattoo scope', ev("specialFor('tattoo').title") === 'Spring sitting special');
  ev("config.specials.forEach(s=>{if(s.title==='Piercing week'){s.start='2026-10-01';s.end='2026-12-31'}});renderSpecials();renderSpecial()");
  ok('after date fix, piercing scope resolves', ev("specialFor('piercing').title") === 'Piercing week');
  ok('a piercing special does NOT kill the tattoo offer', ev("specialFor('tattoo').title") === 'Spring sitting special');
  ok('and the piercing offer does not leak onto tattoos', ev("config.specials.find(s=>s.title==='Spring sitting special').appliesTo") === 'tattoo');
  ev("document.getElementById('spId').value='spring-sitting';document.querySelector('[data-action=\"edit-special\"][data-id=\"spring-sitting\"]').click()");
  ok('edit loads form values', ev("document.getElementById('spTitle').value") === 'Spring sitting special');
  ok('edit loaded discount', ev("document.getElementById('spValue').value") === '10' && ev("document.getElementById('spType').value") === 'percent');
  ev("document.getElementById('spTitle').value='Spring sitting special v2';document.querySelector('[data-action=\"save-special\"]').click()");
  ok('update replaces instead of appending', ev('config.specials.length') === 2 && ev("config.specials.find(s=>s.id==='spring-sitting').title") === 'Spring sitting special v2');
  ev("document.querySelector('[data-action=\"toggle-special\"][data-id=\"spring-sitting\"]').click()");
  ok('toggle pauses the special', ev("config.specials.find(s=>s.id==='spring-sitting').live") === false);
  ok('hero now shows the other live special', ev("activeSpecial().title") === 'Piercing week' && ev("document.getElementById('offerTitle').textContent") === 'Piercing week');
  ev("document.querySelector('[data-action=\"delete-special\"][data-id=\"spring-sitting\"]').click()");
  ok('delete removes it', ev('config.specials.length') === 1);
  ev("config.specials=[{id:'spring-sitting',live:true,flag:'Studio special',title:'Spring sitting special',copy:'Ten per cent off any custom piece quoted from R4,000, for weekday studio sessions booked before the end of November.',cta:'Claim it in your brief',discount:{type:'percent',value:10},minQuote:4000,appliesTo:'tattoo',start:'2026-10-15',end:'2026-11-30',terms:'Indicative discount · final quote confirmed by the artist'}];save();renderSpecials();renderSpecial()");

  console.log('\n── validation guards ────────────────────────────────');
  ev("clearSpecialForm();document.querySelector('[data-action=\"save-special\"]').click()");
  ok('blank headline rejected (no phantom special)', ev('config.specials.length') === 1);
  ev("clearSpecialForm();document.getElementById('spTitle').value='Broken';document.getElementById('spType').value='percent';document.getElementById('spValue').value=0;document.querySelector('[data-action=\"save-special\"]').click()");
  ok('zero-value discount rejected', ev('config.specials.length') === 1);
  ev("clearSpecialForm();document.getElementById('spTitle').value='Bad dates';document.getElementById('spType').value='none';document.getElementById('spStart').value='2026-12-10';document.getElementById('spEnd').value='2026-12-01';document.querySelector('[data-action=\"save-special\"]').click()");
  ok('end-before-start rejected', ev('config.specials.length') === 1);

  console.log('\n── concierge + credits + persistence ────────────────');
  const before = JSON.parse(ev('JSON.stringify(chatLog.length)'));
  ev("addMsg('Test message <b>bold</b>','user')");
  ok('transcript recorded', ev('chatLog.length') === before + 1);
  ok('transcript strips markup', ev("chatLog[chatLog.length-1].t") === 'Test message bold');
  ok('bubble rendered in chat', ev("document.querySelectorAll('#chat .bubble').length") > 0);
  ev("config.ai.creditUsed=0;bumpCredits(2)");
  ok('credits increment', ev('config.ai.creditUsed') === 2);
  ev("config.ai.creditUsed=999;config.ai.creditLimit=1000;bumpCredits(50)");
  ok('credits clamped at the limit', ev('config.ai.creditUsed') === 1000);
  ev("config.ai.creditUsed=180");
  ev("estimateBrief={style:'Blackwork',size:'Medium',detail:'Medium',placement:'Upper arm',mode:'Studio'};showEstimate()");
  const estLead = JSON.parse(ev("JSON.stringify(leads.filter(l=>l.type==='custom estimate').slice(-1)[0])"));
  ok('estimate saved as a lead with transcript', Array.isArray(estLead.transcript) && estLead.transcript.length > 0, 'transcript=' + estLead.transcript.length);
  opened = [];
  ev("handoffArtist()");
  ok('handoff opens WhatsApp with a summary', opened.length === 1 && opened[0].startsWith('https://wa.me/27617593378?text='));
  ok('handoff text carries the range', decodeURIComponent(opened[0]).includes('Indicative range: R'));
  ok('handoff text carries the transcript', decodeURIComponent(opened[0]).includes('Conversation:'));
  ok('handoff logged as a lead', ev("leads[leads.length-1].type") === 'concierge handoff');
  ev("save()");
  const stored = JSON.parse(win.localStorage.getItem('haywoodConfig'));
  ok('specials persist to localStorage', stored.specials && stored.specials.length === 1 && stored.specials[0].id === 'spring-sitting');
  ok('leads persist', JSON.parse(win.localStorage.getItem('haywoodLeads')).length > 0);

  console.log('\n── re-render after everything ───────────────────────');
  ok('no runtime errors across the whole run', errors.length === 0, errors.slice(0, 4).join(' | '));

  console.log(`\n${pass} passed, ${fail} failed\n`);
  process.exit(fail ? 1 : 0);
}, 400);
