#!/usr/bin/env python3
"""Concierge upgrades: budget-aware guidance, artist-review gate, honest vision
note, per-turn credit metering, resumable refinement, and a hot-lead admin view."""
from pathlib import Path

P = Path('/home/user/index.html')
s = P.read_text()
log = []


def rep(old, new, label):
    global s
    assert old in s, f'ANCHOR MISSING: {label} :: {old[:70]!r}'
    s = s.replace(old, new, 1)
    log.append(label)


def span(a, b, new, label):
    global s
    i, j = s.index(a), s.index(b)
    assert j > i, label
    s = s[:i] + new + s[j:]
    log.append(label)


# 1 ── shared guidance logic (pure, deterministic — the model never invents prices)
GUIDE = r'''    /* ── Concierge guidance: budget fit, review gate, credit metering ──────── */
    const BUDGET_MAX={Low:2500,Mid:5000,High:Infinity,Open:Infinity};
    const SENSITIVE=['Ribs / torso','Chest / back','Neck','Hands','Face','Spine'];
    function budgetAdvice(b,low){
      const max=BUDGET_MAX[b.budget];if(max===undefined||max===Infinity)return '';
      if(low<=max)return '';
      return 'You named a comfort range under '+money(max)+', and this build comes in above it. Two honest ways to land there: drop a size step, or keep the size and lose the colour fill. The artist can also split it over two sessions so the deposit and each sitting stay manageable.'}
    function needsReview(b,e){
      const over=(e.high||0)>=(Number(config.pricing.threshold)||6000);
      const spot=SENSITIVE.some(x=>(b.placement||'').indexOf(x)>=0);
      return {flag:over||spot,reason:over?'a project above the R'+((Number(config.pricing.threshold)||6000)/1000)+'k review threshold':(spot?'a placement the artist always checks in person':'')}}
    function recapLine(b){
      const bits=[b.style,b.size&&(b.size==='Small'?'small':b.size==='Medium'?'medium':'large'),b.placement,b.detail&&({'Low':'clean','Medium':'moderate detail','High':'highly detailed'})[b.detail],b.mode==='Mobile'?'mobile session':'studio session'].filter(Boolean);
      return bits.length?('So: '+bits.join(', ')+'.'):''}
'''
rep("    const $=s=>document.querySelector(s);", GUIDE + "    const $=s=>document.querySelector(s);", 'guidance helpers')

# 2 ── showEstimate: recap, budget advice, review badge, handoff chips, dedupe
new_show = r'''function showEstimate(){const e=calculateEstimate();estimateBrief.estimate=e;
      const b=estimateBrief;const review=needsReview(b,e);
      const advice=budgetAdvice(b,e.low);
      const lead={id:Date.now(),type:'custom estimate',created:new Date().toLocaleString(),
        brief:{...b,range:money(e.low)+' – '+money(e.high),review:review.flag},transcript:chatLog.slice()};
      // refining the same brief replaces the previous estimate instead of stacking duplicates
      const last=leads[leads.length-1];
      if(last&&last.type==='custom estimate'&&last.session===estimateBrief.session)leads[leads.length-1]={...last,...lead};
      else{lead.session=b.session;leads.push(lead)}
      save();
      const sp=e.special;
      const spLine=sp?(sp.missed?('<div class="estimate-special note">'+sp.title+' starts above this brief — roughly '+money(sp.gap)+' more work unlocks it. Add size, detail, or colour and ask again.</div>')
        :('<div class="estimate-special applied"><b>'+sp.title+' applied</b> · you saved '+money(sp.cut)+(sp.end?(' · ends '+fmtDate(sp.end)):'')+' · still confirmed by the artist</div>')):'';
      const adviceLine=advice?('<div class="estimate-advice">'+advice+'</div>'):'';
      const reviewLine=review.flag?('<div class="estimate-review"><b>Artist review required</b> · this falls into '+review.reason+', so Haywood confirms feasibility and the final quote before any design work starts.</div>'):'';
      addMsg((recapLine(b)||'Here’s the clearest direction from what you’ve told me.')+' This is an indicative range; the artist confirms the final quote before the design is locked.'+(sp&&!sp.missed?' I’ve applied the live studio special, so this is the discounted range.':''),'bot');
      addMsg('<div class="estimate-card"><div class="estimate-label">Indicative Haywood investment</div><div class="estimate-price">'+money(e.low)+' – '+money(e.high)+'</div>'+spLine
        +'<div class="estimate-meta"><div><span>Direction</span><b>'+(b.style||'To discuss')+'</b></div><div><span>Placement</span><b>'+(b.placement||'To discuss')+'</b></div><div><span>Session</span><b>'+e.time+'</b></div></div>'+adviceLine+reviewLine
        +'<div class="small" style="color:#c7c0bf;margin-top:13px">Deposit from '+money(e.deposit)+' · '+(b.mode==='Mobile'?'Mobile travel included':'Private studio session')+'</div>'
        +'<div class="estimate-actions"><button class="btn btn-red" data-action="book-estimate">Choose a session ↗</button><button class="btn btn-ghost" data-action="handoff-artist">Send this brief to the artist</button></div>'
        +'<div class="estimate-fine">Indicative only · 18+ with valid ID · no medical advice · the artist reviews complex or sensitive placements</div></div>');
      if(review.flag&&config.ai.handoff){
        addMsg('Because this needs the artist’s eye, I can pass your brief across now — you’ll get a reply with real dates. Or we can keep shaping it.','bot',quick([{label:'Send it to the artist now',value:'handoff'},{label:'Keep refining the idea',value:'refine'}]));
      }
      assistantStep='done';
      $$('[data-action="book-estimate"]').forEach(x=>x.addEventListener('click',()=>openBooking({title:'Custom tattoo brief',price:money(e.low)+' – '+money(e.high),priceNum:e.deposit,detail:estimateBrief})));}
    '''
span('function showEstimate(){', 'function handleQuick(', new_show, 'showEstimate v2')

# 3 ── handleQuick: credits, handoff, refine loop, budget stored
rep("function handleQuick(v){addMsg(v.replace(/^\\w+:/,''),'user');",
    "function handleQuick(v){addMsg(v.replace(/^\\w+:/,''),'user');bumpCredits(1);if(typeof renderAdmin==='function')renderAdmin();",
    'credits per turn')
rep("if(v==='skip-image'||v==='upload'){assistantStep='style';askNext();return}",
    "if(v==='skip-image'||v==='upload'){assistantStep='style';askNext();return}"
    "if(v==='handoff'){handoffArtist();addMsg('Sent — the artist has your brief, reference notes and the indicative range. Expect a reply with real dates.');return}"
    "if(v==='refine'){assistantStep='size';addMsg('Good. Let’s re-run the size question and everything after it — the direction you picked stays put.');askNext();return}",
    'handoff + refine branches')

# 4 ── session id so refining does not stack duplicate leads
rep("function resetAssistant(mode='custom'){estimateBrief={};",
    "function resetAssistant(mode='custom'){estimateBrief={session:'S-'+Date.now().toString(36)};", 'session id')

# 5 ── honest reference-image note + credit bump
rep("addMsg('Reference image attached:<img src=\"'+reader.result+'\" alt=\"Uploaded tattoo reference\">','user');",
    "addMsg('Reference attached:<img src=\"'+reader.result+'\" alt=\"Client-uploaded tattoo reference, kept private and shown to the artist\">','user');"
    "addMsg('In production the vision model reads this for composition, density and flow before I ask anything — but the artist always sees it first, and nothing here replaces that look. What do you want kept from it, and what can go?','bot');",
    'honest vision note')

# 6 ── admin: hot leads + credit warning state
rep("$('#adminLeads').innerHTML=leads.slice().reverse().map(l=>`<div class=\"admin-list-row\"><div><b>${l.type}</b><span style=\"display:block\">${l.created}</span></div><span>${l.brief?.name||l.brief?.style||'New conversation'}</span></div>`).join('')||'<div class=\"small\">No leads yet.</div>';",
    "$('#adminLeads').innerHTML=leads.slice().reverse().map(l=>{const r=l.brief&&l.brief.review;return `<div class=\"admin-list-row\"><div><b>${l.type}</b>${r?'<span class=\"lead-flag\">needs artist review</span>':''}<span style=\"display:block\">${l.created}${l.brief&&l.brief.range?' · '+l.brief.range:''}</span></div><span>${l.brief?.name||l.brief?.style||'New conversation'}</span></div>`}).join('')||'<div class=\"small\">No leads yet.</div>';",
    'admin hot lead flags')
rep("if($('#adminCreditBar'))$('#adminCreditBar').style.width=pct+'%';",
    "if($('#adminCreditBar')){$('#adminCreditBar').style.width=pct+'%';$('#adminCreditBar').classList.toggle('warn',pct>=80)}",
    'credit warning state')

# 7 ── styling for the new estimate blocks + lead flag
rep('    .estimate-fine{margin-top:11px;',
    '''    .estimate-advice{margin:13px 0 0;font-size:12px;line-height:1.6;color:#e3dddb;background:rgba(255,255,255,.05);border-radius:11px;padding:12px 14px;border-left:2px solid rgba(255,255,255,.28)}
    .estimate-review{margin:13px 0 0;font-size:12px;line-height:1.6;color:#ffe0b8;background:rgba(255,176,32,.11);border:1px solid rgba(255,196,64,.3);border-radius:11px;padding:12px 14px}
    .estimate-review b{color:#ffc440}
    .lead-flag{display:inline-block;margin-left:8px;font-size:9px;letter-spacing:.12em;text-transform:uppercase;font-weight:900;color:#ffc440;background:rgba(255,196,64,.13);border:1px solid rgba(255,196,64,.3);border-radius:999px;padding:3px 8px;vertical-align:middle}
    #adminCreditBar.warn{background:linear-gradient(90deg,#ffb020,#d60000)}
    .estimate-fine{margin-top:11px;''', 'estimate guidance styles')

P.write_text(s)
print(f'patched: {len(log)} edits')
for l in log:
    print('  ✓', l)
