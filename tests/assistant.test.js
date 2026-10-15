#!/usr/bin/env node
const path = require('path');
const ROOT = path.join(__dirname, '..', '') + path.sep;
const IDX = path.join(ROOT, 'index.html');
/* Concierge flow tests: drive the page's own handleQuick / showEstimate / handoffArtist. */
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
const txt = () => $('#chat').textContent;
let pass = 0, fail = 0;
const ok = (n, c, x) => {
  if (c) { pass++; console.log('  \x1b[32mPASS\x1b[0m ' + n + (x ? '  ' + x : '')); }
  else { fail++; console.log('  \x1b[31mFAIL\x1b[0m ' + n + (x ? '  ' + x : '')); }
};

function runBrief(steps) {
  ev("resetAssistant('custom')");
  ev("handleQuick('estimate')");
  steps.forEach(([k, v]) => ev(`handleQuick('${k}:${v}')`));
}

console.log('\n── brief 1: large colour piece on the ribs, tight budget ──');
runBrief([['style', 'Colour'], ['size', 'Large'], ['detail', 'High'], ['placement', 'Ribs / torso'], ['mode', 'Studio'], ['budget', 'Low']]);
ok('estimate card rendered', /Indicative Haywood investment/.test(txt()));
ok('artist-review gate fired for ribs + threshold', /Artist review required/.test(txt()));
ok('review reason names the threshold or placement', /review threshold|placement the artist always checks/.test(txt()));
ok('budget conflict advice shown', /comfort range under R2,500/.test(txt()));
ok('advice offers concrete levers', /drop a size step|lose the colour fill|two sessions/.test(txt()));
ok('handoff chips offered because ai.handoff is on', !!$('#chat [data-quick="handoff"]') && !!$('#chat [data-quick="refine"]'));
ok('special still below threshold note (short brief)', /starts above this brief/.test(txt()) === false);
const credits1 = ev('config.ai.creditUsed');
ok('credits metered per answer (7 turns)', credits1 > 180, 'used=' + credits1);
const leadsA = ev("leads.filter(l=>l.type==='custom estimate').length");
ok('lead stored with review flag + range', ev("leads[leads.length-1].brief.review") === true && /R/.test(ev("leads[leads.length-1].brief.range")));
ok('transcript saved with the lead', ev('leads[leads.length-1].transcript.length') >= 7);

console.log('\n── refine: re-answer and keep one lead per session ───────');
ev("handleQuick('refine')");
ok('refine re-opens the size question', ev('assistantStep') === 'size');
ok('refine message reassures the direction is kept', /size question|stays put/.test(txt()));
ev("handleQuick('size:Small')"); ev("handleQuick('placement:Forearm')");
ev("handleQuick('detail:Low')"); ev("handleQuick('mode:Studio')");
ev("handleQuick('budget:Low')");
ok('second estimate replaces the session lead, no duplicates', ev("leads.filter(l=>l.type==='custom estimate').length") === leadsA);
const est2 = JSON.parse(ev('JSON.stringify(estimateBrief.estimate)'));
ok('range shrank after resizing down (R5,490 → R2,500)', est2.low === 2500 && est2.high === 4400, `low=${est2.low} high=${est2.high}`);
ok('review gate now off for a forearm piece', ev('needsReview(estimateBrief, estimateBrief.estimate).flag') === false);

console.log('\n── handoff chip ──────────────────────────────────────────');
opened = [];
ev("handleQuick('handoff')");
ok('handoff opened WhatsApp with a summary', opened.length === 1 && opened[0].startsWith('https://wa.me/27617593378?text='));
const wa = opened[0] ? decodeURIComponent(opened[0]) : '';
ok('summary carries direction, placement, range', /Direction:/.test(wa) && /Placement:/.test(wa) && /Indicative range: R/.test(wa));
ok('summary states it is not a confirmed quote', /not a confirmed quote/.test(wa));
ok('handoff logged as its own lead type', ev("leads[leads.length-1].type") === 'concierge handoff');
ok('client told it was sent', /Sent — the artist has your brief/.test(txt()));

console.log('\n── brief 2: comfortable budget, quiet placement ──────────');
runBrief([['style', 'Fine-line'], ['size', 'Medium'], ['detail', 'Low'], ['placement', 'Forearm'], ['mode', 'Studio'], ['budget', 'High']]);
ok('no review badge for a fine-line forearm', ev('needsReview(estimateBrief, estimateBrief.estimate).flag') === false);
ok('no budget-conflict advice when the range fits', !/comfort range under/.test(txt()));
ok('recap line opens the estimate', /So: Fine-line, medium, Forearm, clean, studio session\./.test(txt()), (txt().match(/So: [^.]*\./) || [''])[0]);
ok('deposit line present', /Deposit from R/.test(txt()));
ok('guardrail fine print present', /18\+ with valid ID/.test(txt()) && /no medical advice/.test(txt()));

console.log('\n── brief 3: mobile session picks up the travel fee ───────');
runBrief([['style', 'Blackwork'], ['size', 'Medium'], ['detail', 'Medium'], ['placement', 'Upper arm'], ['mode', 'Mobile'], ['budget', 'Open']]);
const est = JSON.parse(ev('JSON.stringify(calculateEstimate())'));
ok('mobile travel fee included in the low end', est.low === 1800 + 700 + 500 + 350, 'low=' + est.low);
ok('copy says travel is included', /Mobile travel included/.test(txt()));

console.log('\n── special interaction ───────────────────────────────────');
runBrief([['style', 'Colour'], ['size', 'Large'], ['detail', 'High'], ['placement', 'Chest / back'], ['mode', 'Studio'], ['budget', 'Open']]);
const big = JSON.parse(ev('JSON.stringify(estimateBrief.estimate)'));
ok('live special applied to a qualifying brief', big.special && big.special.cut > 0, 'cut=' + (big.special && big.special.cut));
ok('discount surfaced in the card', /applied<\/b> · you saved|you saved/.test(txt().replace(/<[^>]+>/g, '')) || /you saved R/.test(txt()));
ok('admin list shows the lead as needing review', ev("leads[leads.length-1].brief.review") === true);
ev('renderAdmin()');
ok('admin renders the review flag pill', /needs artist review/.test($('#adminLeads').innerHTML));
ev("config.ai.creditLimit=200;config.ai.creditUsed=190;renderAdmin()");
ok('credit bar switches to warn state at 80%+', $('#adminCreditBar').classList.contains('warn'));

console.log('\n── honesty guardrails ────────────────────────────────────');
const refNote = html.match(/In production the vision model reads this[\s\S]{0,200}/);
ok('reference note defers to the artist', !!refNote && /artist always sees it first/.test(refNote[0]));
ok('no promise of a final price anywhere in the flow copy', !/guaranteed price|price is final/i.test(html));
ok('concierge never claims to be the artist', !/I am the artist|i’m the artist/i.test(html));
ok('no runtime errors', errors.length === 0, errors.slice(0, 2).join(' | '));
console.log(`\n${pass} passed, ${fail} failed\n`);
process.exit(fail ? 1 : 0);
