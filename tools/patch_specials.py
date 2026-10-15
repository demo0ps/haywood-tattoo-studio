#!/usr/bin/env python3
"""Add admin-managed specials that appear in the hero and feed the estimate maths."""
from pathlib import Path
import re

P = Path('/home/user/index.html')
s = P.read_text()
log = []


def rep(old, new, label, count=1):
    global s
    assert old in s, f'ANCHOR MISSING: {label} -> {old[:70]!r}'
    assert s.count(old) >= count, f'only {s.count(old)} of {label}'
    s = s.replace(old, new, count)
    log.append(label)


def span(a, b, new, label):
    """Replace everything from marker a up to marker b."""
    global s
    i, j = s.find(a), s.find(b)
    assert i >= 0 and j > i, f'SPAN FAIL {label}: a={i} b={j}'
    s = s[:i] + new + s[j:]
    log.append(label)


# 1 ── seeded special in defaults + config merge --------------------------------
rep("const defaultConfig={pricing:{base:1800,hourly:1200,travel:350,deposit:30,medium:700,high:1400,colour:700,threshold:6000},",
    "const defaultConfig={pricing:{base:1800,hourly:1200,travel:350,deposit:30,medium:700,high:1400,colour:700,threshold:6000},"
    "specials:[{id:'spring-sitting',live:true,flag:'Studio special',title:'Spring sitting special',"
    "copy:'Ten per cent off any custom piece quoted from R4,000, for weekday studio sessions booked before the end of November.',"
    "cta:'Claim it in your brief',discount:{type:'percent',value:10},minQuote:4000,appliesTo:'tattoo',"
    "start:'2026-10-15',end:'2026-11-30',"
    "terms:'Indicative discount · final quote confirmed by the artist · deposit still secures the slot · 18+ with valid ID'}],",
    'default specials seeded')
rep("security:{ownerEmail:''}};", "security:{ownerEmail:''}};", 'noop')
rep("security:{...defaultConfig.security,...(savedConfig.security||{})}};",
    "security:{...defaultConfig.security,...(savedConfig.security||{})},specials:Array.isArray(savedConfig.specials)?savedConfig.specials:structuredClone(defaultConfig.specials)};",
    'config merge specials')

# 2 ── engine ---------------------------------------------------------------
HELPER = r'''
    /* ── Specials: hero offers that also drive the estimator ─────────────────── */
    function fmtDate(v){if(!v)return '';const d=new Date(v.length===10?v+'T00:00:00':v);return isNaN(d)?v:d.toLocaleDateString('en-ZA',{day:'numeric',month:'short',year:'numeric'})}
    function specialState(sp){if(!sp)return 'off';if(!sp.live)return 'off';const now=Date.now();
      if(sp.start&&now<new Date(sp.start.length===10?sp.start+'T00:00':sp.start).getTime())return 'scheduled';
      if(sp.end&&now>new Date(sp.end.length===10?sp.end+'T23:59:59':sp.end).getTime())return 'expired';return 'live'}
    function activeSpecial(){return(config.specials||[]).filter(sp=>specialState(sp)==='live')[0]||null}
    function specialFor(scope){const list=(config.specials||[]).filter(sp=>specialState(sp)==='live');
      if(!list.length)return null;if(!scope)return list[0];
      return list.find(sp=>{const a=sp.appliesTo||'all';return a==='all'||a===scope})||null}
    function daysToGo(sp){if(!sp||!sp.end)return 0;return Math.max(0,Math.ceil((new Date(sp.end.length===10?sp.end+'T23:59:59':sp.end).getTime()-Date.now())/86400000))}
    function specialCut(quote,sp){const d=sp&&sp.discount;if(!d||d.type==='none')return 0;
      const min=Number(sp.minQuote)||0;if(quote<min)return 0;
      const raw=d.type==='percent'?Math.round(quote*Number(d.value)/100):Math.round(Number(d.value)||0);
      const floor=Number(config.pricing.base)||0;return Math.max(0,Math.min(raw,Math.max(0,quote-floor)))}
    function renderSpecial(){const box=document.getElementById('heroOffer');if(!box)return;const sp=activeSpecial();
      if(!sp){box.hidden=true;return}box.hidden=false;box.dataset.special=sp.id;
      const put=(id,txt)=>{const el=document.getElementById(id);if(el)el.textContent=txt};
      put('offerFlag',sp.flag||'Studio special');put('offerTitle',sp.title||'');put('offerCopy',sp.copy||'');
      put('offerFine',[sp.end?('Ends '+fmtDate(sp.end)):'',sp.terms||''].filter(Boolean).join(' · '));
      const cta=document.getElementById('offerCta');if(cta)cta.innerHTML=(sp.cta||'Claim it in your brief')+' <span aria-hidden="true">↗</span>';
      const left=daysToGo(sp),count=document.getElementById('offerCount');if(count)count.textContent=left>0?(left+' day'+(left===1?'':'s')+' left'):'Final day';
      const scope=document.getElementById('offerScope');
      if(scope)scope.textContent={all:'Everything in the studio',tattoo:'Custom tattoo work',piercing:'Piercing appointments',mobile:'Mobile sessions',flash:'Lookbook & flash pieces'}[sp.appliesTo||'all']||'Custom tattoo work'}
    function renderSpecials(){const list=document.getElementById('adminSpecials');if(!list)return;
      const rows=(config.specials||[]).map(sp=>{const st=specialState(sp);
        const cut=sp.discount&&sp.discount.type==='percent'?(sp.discount.value+'% off'):sp.discount&&sp.discount.type==='amount'?('R'+Number(sp.discount.value).toLocaleString('en-ZA')+' off'):'Display only';
        return '<div class="admin-list-row special-row"><div><b>'+(sp.title||'Untitled special')+'</b><span style="display:block">'+cut+(sp.minQuote?(' · from R'+Number(sp.minQuote).toLocaleString('en-ZA')):'')+' · '+({all:'everything',tattoo:'custom tattoo',piercing:'piercing',mobile:'mobile',flash:'lookbook & flash'}[sp.appliesTo||'all'])+' · '+(sp.start?fmtDate(sp.start):'immediate')+' → '+(sp.end?fmtDate(sp.end):'no end date')+'</span></div>'
          +'<div class="special-actions"><span class="status '+st+'">'+st+'</span>'
          +'<button class="btn btn-light btn-sm" data-action="edit-special" data-id="'+sp.id+'">Edit</button>'
          +'<button class="btn btn-light btn-sm" data-action="toggle-special" data-id="'+sp.id+'">'+(sp.live?'Pause':'Publish')+'</button>'
          +'<button class="btn btn-ghost btn-sm" data-action="delete-special" data-id="'+sp.id+'">Delete</button></div></div>'}).join('');
      list.innerHTML=rows||'<div class="small">No specials yet. Add one and it appears in the hero immediately.</div>';
      const live=(config.specials||[]).filter(sp=>specialState(sp)==='live').length;
      const st=document.getElementById('specialStatus');
      if(st)st.innerHTML='<b>'+live+'</b> live now · <b>'+(config.specials||[]).length+'</b> total · live specials are applied automatically by the estimate calculator';
      const box=document.getElementById('spPreviewRange');
      if(box){const probe={low:4000};const sp=specialFor('tattoo');const c=specialCut(probe.low,sp);
        box.textContent='Test: a R4,000 brief → '+(c?('−R'+Number(c).toLocaleString('en-ZA')+', now from R'+Number(probe.low-c).toLocaleString('en-ZA')):'no change')}
    function specialFormValues(){const v=id=>{const el=document.getElementById(id);return el?el.value:''};
      return{id:v('spId')||('sp-'+Date.now().toString(36)),flag:v('spFlag')||'Studio special',title:v('spTitle')||'Untitled special',
        copy:v('spCopy'),cta:v('spCta')||'Claim it in your brief',discount:{type:v('spType'),value:Number(v('spValue'))||0},
        minQuote:Number(v('spMin'))||0,appliesTo:v('spScope')||'tattoo',start:v('spStart'),end:v('spEnd'),terms:v('spTerms'),
        live:!!(document.getElementById('spLive')||{}).checked}}
    function saveSpecial(){const f=specialFormValues();if(!f.title||f.title==='Untitled special'){toast('Give the special a headline first.');return}
      if(f.discount.type!=='none'&&!f.discount.value){toast('Set the discount value, or choose “Display only”.');return}
      if(f.end&&f.start&&f.end<f.start){toast('The end date is before the start date.');return}
      const arr=config.specials||[];const i=arr.findIndex(x=>x.id===f.id);
      if(i>=0)arr[i]=f;else arr.unshift(f);config.specials=arr;save();
      const el=document.getElementById('spId');if(el)el.value=f.id;renderSpecials();renderSpecial();
      toast(i>=0?'Special updated':'Special published to the hero')}
    function editSpecial(id){const sp=(config.specials||[]).find(x=>x.id===id);if(!sp)return;
      const set=(v,val)=>{const el=document.getElementById(v);if(el)el.value=val==null?'':val};
      set('spId',sp.id);set('spFlag',sp.flag);set('spTitle',sp.title);set('spCopy',sp.copy);set('spCta',sp.cta);
      set('spType',sp.discount?sp.discount.type:'none');set('spValue',sp.discount?sp.discount.value:'');
      set('spMin',sp.minQuote);set('spScope',sp.appliesTo);set('spStart',sp.start);set('spEnd',sp.end);set('spTerms',sp.terms);
      const live=document.getElementById('spLive');if(live)live.checked=!!sp.live;
      renderSpecials();toast('Loaded “'+sp.title+'” into the form')}
    function clearSpecialForm(){['spId','spFlag','spTitle','spCopy','spCta','spValue','spMin','spStart','spEnd','spTerms'].forEach(id=>{const el=document.getElementById(id);if(el)el.value=id==='spFlag'?'Studio special':''});
      const t=document.getElementById('spType');if(t)t.value='percent';const sc=document.getElementById('spScope');if(sc)sc.value='tattoo';
      const live=document.getElementById('spLive');if(live)live.checked=true}
'''
rep("    let cart=JSON.parse(localStorage.getItem('haywoodCart')||'[]');\n",
    "    let cart=JSON.parse(localStorage.getItem('haywoodCart')||'[]');\n" + HELPER,
    'special engine helpers')

# 3 ── estimator integration -------------------------------------------------
new_calc = r'''function calculateEstimate(){const b=estimateBrief;let low=config.pricing.base;let high=config.pricing.base+config.pricing.hourly;const size=b.size==='Small'?0:b.size==='Medium'?config.pricing.medium:config.pricing.medium+1000;const detail=b.detail==='Low'?0:b.detail==='Medium'?500:config.pricing.high;const color=b.style==='Colour'?config.pricing.colour:0;const placement=['Ribs / torso','Chest / back'].includes(b.placement)?500:0;const mobile=b.mode==='Mobile'?config.pricing.travel:0;low+=size+detail+color+placement+mobile;high+=size+detail+color+placement+mobile+(b.size==='Large'?1800:700);
      const sp=specialFor('tattoo');let cut=0,gap=0,missed=false;
      if(sp){const min=Number(sp.minQuote)||0;if(min&&low<min){missed=true;gap=min-low}else{cut=specialCut(low,sp);if(cut>0){low=Math.max(0,low-cut);high=Math.max(low,high-cut)}}}
      const deposit=Math.round((low*config.pricing.deposit)/100);
      return {low,high,deposit,time:b.size==='Large'?'4–6 hours':b.size==='Medium'?'2–4 hours':'1–2 hours',special:sp?{title:sp.title,cut,gap,missed,end:sp.end}:null}}
    '''
i = s.index('function calculateEstimate(){')
j = s.index('function handleQuick(')
log.append('calculateEstimate + showEstimate (special, transcript, handoff)')

new_show = r'''function showEstimate(){const e=calculateEstimate();estimateBrief.estimate=e;
      leads.push({id:Date.now(),type:'custom estimate',created:new Date().toLocaleString(),brief:{...estimateBrief},transcript:chatLog.slice()});save();
      const sp=e.special;
      const spLine=sp?(sp.missed?('<div class="estimate-special note">'+sp.title+' starts above this brief — roughly '+money(sp.gap)+' more work unlocks it. Add size, detail, or colour and ask again.</div>')
        :('<div class="estimate-special applied"><b>'+sp.title+' applied</b> · you saved '+money(sp.cut)+(sp.end?(' · ends '+fmtDate(sp.end)):'')+' · still confirmed by the artist</div>')):'';
      addMsg('Here’s the clearest direction from what you’ve told me. This is an indicative range; the artist confirms the final quote before the design is locked.'+(sp&&!sp.missed?' I have already applied the live studio special to it, so you are seeing the discounted range.':''),'bot');
      addMsg('<div class="estimate-card"><div class="estimate-label">Indicative Haywood investment</div><div class="estimate-price">'+money(e.low)+' – '+money(e.high)+'</div>'+spLine
        +'<div class="estimate-meta"><div><span>Direction</span><b>'+estimateBrief.style+'</b></div><div><span>Placement</span><b>'+estimateBrief.placement+'</b></div><div><span>Session</span><b>'+e.time+'</b></div></div>'
        +'<div class="small" style="color:#c7c0bf;margin-top:13px">Deposit from '+money(e.deposit)+' · '+(estimateBrief.mode==='Mobile'?'Mobile travel included':'Private studio session')+'</div>'
        +'<div class="estimate-actions"><button class="btn btn-red" data-action="book-estimate">Choose a session ↗</button><button class="btn btn-ghost" data-action="handoff-artist">Send this brief to the artist</button></div>'
        +'<div class="estimate-fine">Indicative only · 18+ with valid ID · the artist reviews complex or sensitive placements · no medical advice</div></div>');
      assistantStep='done';
      $$('[data-action="book-estimate"]').forEach(b=>b.addEventListener('click',()=>openBooking({title:'Custom tattoo brief',price:money(e.low)+' – '+money(e.high),priceNum:e.deposit,detail:estimateBrief})));}
    '''
s = s[:i] + new_calc + new_show + '    ' + s[j:]



# 4 ── chat log + credits ----------------------------------------------------
rep("function addMsg(text,who='bot',extra=''){const chat=$('#chat');const el=document.createElement('div');el.className='bubble '+(who==='user'?'user':'');el.innerHTML=text+extra;chat.appendChild(el);chat.scrollTop=chat.scrollHeight}",
    "const chatLog=[];function logChat(text,who){chatLog.push({who,t:text.replace(/<[^>]+>/g,' ').replace(/\\s+/g,' ').trim().slice(0,240),at:new Date().toLocaleTimeString('en-ZA')});if(chatLog.length>60)chatLog.shift()}\n"
    "    function bumpCredits(n){config.ai.creditUsed=Math.min(Number(config.ai.creditLimit)||1000,(Number(config.ai.creditUsed)||0)+n)}\n"
    "    function addMsg(text,who='bot',extra=''){const chat=$('#chat');const el=document.createElement('div');el.className='bubble '+(who==='user'?'user':'');el.innerHTML=text+extra;chat.appendChild(el);chat.scrollTop=chat.scrollHeight;logChat(text,who)}",
    'addMsg transcript + credit meter')
rep("let estimateBrief={};let activeProject=null;let assistantStep='intro';",
    "let estimateBrief={};let activeProject=null;let assistantStep='intro';", 'noop2')

# 5 ── hero offer card -------------------------------------------------------
rep('<div class="hero-note"><span class="dot"></span>Taking private bookings in Pretoria and on location</div>',
    '''<div class="hero-offer" id="heroOffer" data-special="spring-sitting"><span class="offer-flag" id="offerFlag">Studio special</span><div class="offer-main"><h2 class="offer-title" id="offerTitle">Spring sitting special</h2><p class="offer-copy" id="offerCopy">Ten per cent off any custom piece quoted from R4,000, for weekday studio sessions booked before the end of November.</p><p class="offer-fine" id="offerFine">Ends 30 Nov 2026 · Indicative discount · final quote confirmed by the artist · deposit still secures the slot · 18+ with valid ID</p></div><div class="offer-side"><span class="offer-scope" id="offerScope">Custom tattoo work</span><span class="offer-count" id="offerCount">Days left</span><button class="btn btn-red" data-action="open-estimate" id="offerCta">Claim it in your brief <span aria-hidden="true">↗</span></button></div><p class="hero-note"><span class="dot" aria-hidden="true"></span>Taking private bookings in Pretoria and on location</p></div>''',
    'hero offer card')

# 6 ── admin nav + panel -----------------------------------------------------
rep('<button data-admin-tab="pricing"><span>↗</span>Pricing engine</button>',
    '<button data-admin-tab="pricing"><span>↗</span>Pricing engine</button><button data-admin-tab="specials"><span>％</span>Specials &amp; offers</button>',
    'admin nav specials tab')

PANEL = '''<div class="studio-panel" id="admin-specials"><div class="admin-card"><div class="admin-card-head"><div><h3>Specials &amp; offers</h3><p>Publish a promotion to the hero, schedule it, and let the estimate calculator apply it automatically.</p></div><span class="integration-status"><span class="led"></span><span>Live on the site</span></span></div><p class="special-status" id="specialStatus"></p><div class="admin-form-grid"><input id="spId" type="hidden" /><div class="field"><label>Flag / eyebrow</label><input id="spFlag" placeholder="Studio special" /></div><div class="field"><label>Headline</label><input id="spTitle" placeholder="Spring sitting special" /></div><div class="field full"><label>Body copy</label><textarea id="spCopy" rows="2" placeholder="What the client gets, in one clear sentence."></textarea></div><div class="field"><label>Button label</label><input id="spCta" placeholder="Claim it in your brief" /></div><div class="field"><label>Discount type</label><select id="spType"><option value="percent">Percentage off</option><option value="amount">Fixed rand amount off</option><option value="none">Display only (no price change)</option></select></div><div class="field"><label>Discount value</label><input id="spValue" type="number" min="0" placeholder="10" /></div><div class="field"><label>Minimum quote to qualify (R)</label><input id="spMin" type="number" min="0" placeholder="4000" /></div><div class="field"><label>Applies to</label><select id="spScope"><option value="tattoo">Custom tattoo work</option><option value="piercing">Piercing appointments</option><option value="mobile">Mobile sessions only</option><option value="flash">Lookbook &amp; flash pieces</option><option value="all">Everything in the studio</option></select></div><div class="field"><label>Starts</label><input id="spStart" type="date" /></div><div class="field"><label>Ends</label><input id="spEnd" type="date" /></div><div class="field full"><label>Fine print / terms shown under the offer</label><textarea id="spTerms" rows="2" placeholder="Weekday sessions · deposit still secures the slot · 18+ with valid ID"></textarea></div><label class="check-row"><input id="spLive" type="checkbox" checked /><span>Published (visible in the hero and applied by the estimator while inside the date range)</span></label></div><div class="admin-actions-row"><button class="btn btn-red btn-sm" data-action="save-special">Save special</button><button class="btn btn-light btn-sm" data-action="clear-special">New / clear form</button><span class="small" id="spPreviewRange"></span></div></div><div class="admin-card"><div class="admin-card-head"><div><h3>Published specials</h3><p>Only one special runs at a time — the top live row wins. Everything else stays scheduled or paused.</p></div></div><div class="admin-list" id="adminSpecials"></div></div></div>
      '''
rep('<div class="studio-panel" id="admin-ai">', PANEL + '<div class="studio-panel" id="admin-ai">', 'admin specials panel')

rep("setVal('adminOwnerEmail',config.security.ownerEmail)}",
    "setVal('adminOwnerEmail',config.security.ownerEmail);renderSpecials()}", 'renderAdmin hook')

rep("communications:['Communications','Connect SMTP email and WhatsApp automation.'],",
    "communications:['Communications','Connect SMTP email and WhatsApp automation.'],specials:['Specials &amp; offers','Create hero promotions, schedule them, and let the estimator apply them.'],",
    'admin tab title')

rep("if(action==='close-sidebar')$('#studioSide').classList.remove('open');",
    "if(action==='close-sidebar')$('#studioSide').classList.remove('open');if(action==='save-special')saveSpecial();if(action==='clear-special')clearSpecialForm();if(action==='edit-special')editSpecial(e.target.dataset.id);if(action==='toggle-special'){const sp=(config.specials||[]).find(x=>x.id===e.target.dataset.id);if(sp){sp.live=!sp.live;save();renderSpecials();renderSpecial();toast(sp.live?'Published to the hero':'Paused')}}if(action==='delete-special'){config.specials=(config.specials||[]).filter(x=>x.id!==e.target.dataset.id);save();renderSpecials();renderSpecial();toast('Special removed')}if(action==='handoff-artist')handoffArtist();",
    'admin + handoff actions')

# 7 ── handoff to the artist -------------------------------------------------
HELPER2 = r'''
    function handoffArtist(){const b=estimateBrief;const e=b.estimate||calculateEstimate();
      const g=k=>b[k]||'To be discussed';
      const lines=['Haywood brief — via the design concierge','','Direction: '+g('style'),'Size: '+g('size'),'Placement: '+g('placement'),'Detail: '+g('detail'),'Session: '+g('mode'),'Reference attached: '+(b.reference||'none'),
        'Indicative range: '+money(e.low)+' – '+money(e.high)+' (deposit from '+money(e.deposit)+')'];
      if(e.special&&!e.special.missed)lines.push('Live special applied: '+e.special.title+' · −'+money(e.special.cut));
      lines.push('','Conversation:','');chatLog.slice(-14).forEach(m=>lines.push((m.who==='user'?'Client: ':'Guide: ')+m.t));
      lines.push('','This is an indicative brief from the concierge, not a confirmed quote.');
      const text=lines.join('\n');
      leads.push({id:Date.now(),type:'concierge handoff',created:new Date().toLocaleString(),brief:{name:'Concierge brief',style:g('style'),size:g('size'),placement:g('placement'),mode:g('mode'),range:money(e.low)+' – '+money(e.high),reference:b.reference||null},transcript:chatLog.slice()});save();
      renderAdmin&&renderAdmin();
      window.open('https://wa.me/27617593378?text='+encodeURIComponent(text),'_blank');
      toast('Brief saved and handed to the artist')}
'''
rep("    function attachReference(file){", HELPER2 + "    function attachReference(file){", 'handoff function')

rep("reader.readAsDataURL(file)}",
    "reader.readAsDataURL(file);bumpCredits(3);if(typeof renderAdmin==='function')renderAdmin()}",
    'credits on image attach')

# 8 ── flash / lookbook note -------------------------------------------------
rep("function openProject(id){activeProject=lookbook.find(p=>p.id===id);if(!activeProject)return;",
    "function openProject(id){activeProject=lookbook.find(p=>p.id===id);if(!activeProject)return;const _sp=specialFor('flash');"
    "const _note=_sp?('<div class=\"look-special\"><b>'+_sp.title+'</b> applies to lookbook pieces · ask the Guide before you request it.</div>'):'';",
    'project special note anchor')
rep('<div class="question-box"><b>Before we request it</b>', '${_note}<div class="question-box"><b>Before we request it</b>', 'project special note render')

# 9 ── CSS ------------------------------------------------------------------
rep('  </style>', '''
    /* ── hero special ─────────────────────────────────────────────── */
    .hero-offer{position:relative;display:grid;grid-template-columns:auto 1fr auto;gap:18px 22px;align-items:center;margin-top:30px;padding:19px 22px 17px;border-radius:18px;background:linear-gradient(118deg,rgba(13,13,15,.96),rgba(38,16,20,.9) 55%,rgba(13,13,15,.94));border:1px solid rgba(214,0,0,.42);box-shadow:0 22px 55px rgba(15,11,11,.24),inset 0 1px 0 rgba(255,255,255,.07);overflow:hidden}
    .hero-offer[hidden]{display:none}
    .hero-offer:before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:linear-gradient(180deg,#ff4e69,#d60000)}
    .hero-offer:after{content:"";position:absolute;right:-70px;top:-90px;width:220px;height:220px;border-radius:50%;background:radial-gradient(circle,rgba(214,0,0,.5),transparent 68%);pointer-events:none}
    .offer-flag{align-self:start;font-size:9px;font-weight:900;letter-spacing:.2em;text-transform:uppercase;color:#fff;background:var(--red);padding:7px 11px;border-radius:999px;white-space:nowrap;box-shadow:0 8px 22px rgba(214,0,0,.42)}
    .offer-main{min-width:0}
    .offer-title{margin:0 0 6px;font-size:19px;line-height:1.2;color:#fff;letter-spacing:-.02em;font-weight:900}
    .offer-copy{margin:0;font-size:13px;line-height:1.55;color:#ded8d6;max-width:46ch}
    .offer-fine{margin:9px 0 0;font-size:10.5px;line-height:1.5;color:#9a9391;letter-spacing:.02em}
    .offer-side{display:grid;gap:9px;justify-items:stretch;text-align:right;border-left:1px solid rgba(255,255,255,.11);padding-left:20px}
    .offer-scope,.offer-count{font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:#ff8095;font-weight:800}
    .offer-count{color:#8f8987;letter-spacing:.06em;text-transform:none;font-weight:600}
    .offer-side .btn{font-size:11px;padding:12px 16px;white-space:nowrap}
    .hero-offer .hero-note{grid-column:1/-1;margin:2px 0 0;padding-top:13px;border-top:1px solid rgba(255,255,255,.09);color:#a09a98;font-size:11px}
    .estimate-special{margin:14px 0 0;font-size:11.5px;line-height:1.5;border-radius:11px;padding:11px 13px}
    .estimate-special.applied{background:rgba(214,0,0,.16);border:1px solid rgba(255,78,105,.4);color:#ffd9df}
    .estimate-special.note{background:rgba(255,255,255,.05);border:1px dashed rgba(255,255,255,.24);color:#c9c3c1}
    .estimate-special b{color:#fff}
    .estimate-actions{display:flex;flex-wrap:wrap;gap:9px;margin-top:16px}
    .estimate-actions .btn{flex:1 1 auto;font-size:11px;padding:13px 15px}
    .estimate-fine{margin-top:11px;font-size:9.5px;letter-spacing:.05em;color:#8b8583;line-height:1.55}
    .look-special{margin-top:14px;font-size:12px;color:var(--red);background:var(--soft-red);border:1px solid rgba(185,20,43,.22);border-radius:12px;padding:11px 14px}
    .special-row{gap:14px;flex-wrap:wrap}
    .special-actions{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
    .status.live{background:rgba(35,160,85,.16);color:#57d98a;border:1px solid rgba(87,217,138,.32)}
    .status.scheduled{background:rgba(255,196,64,.14);color:#ffc440;border:1px solid rgba(255,196,64,.3)}
    .status.expired,.status.off{background:rgba(255,255,255,.06);color:#8f8987;border:1px solid rgba(255,255,255,.14)}
    .special-status{margin:0 0 16px;font-size:12px;color:#a8a2a0;background:rgba(255,255,255,.04);border:1px solid #303035;border-radius:12px;padding:11px 14px}
    .special-status b{color:#fff}
    .admin-actions-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:16px;padding-top:16px;border-top:1px solid #303035}
    .check-row{display:flex;align-items:center;gap:10px;font-size:12.5px;color:#cfc9c7;grid-column:1/-1;margin-top:4px;cursor:pointer}
    .check-row input{width:18px;height:18px;accent-color:var(--red);flex:0 0 auto}
    .field textarea{font:inherit;resize:vertical;min-height:64px;width:100%}
    @media(max-width:900px){.hero-offer{grid-template-columns:1fr;gap:14px;padding:17px}.offer-side{border-left:0;padding-left:0;justify-items:start;text-align:left;border-top:1px solid rgba(255,255,255,.1);padding-top:14px}.offer-side .btn{width:100%}}
  </style>''', 'specials CSS')

# 10 ── init -----------------------------------------------------------------
rep('renderLookbook();renderProducts();renderCart();renderAdmin();',
    'renderLookbook();renderProducts();renderCart();renderAdmin();renderSpecial();', 'init renderSpecial')

P.write_text(s)
print('patched: %d edits' % len(log))
for l in log:
    print('  ✓', l)
print('size', len(s), 'bytes')
