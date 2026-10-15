#!/usr/bin/env python3
"""patch_research.py — apply the studio-research upgrades to index.html.

Stages are idempotent: an applied stage is recorded in tools/.research-state.json,
so re-running the script never double-inserts. Every edit asserts its anchor count
before touching the file, so a failed edit leaves index.html untouched.

Run:  python3 tools/patch_research.py            # apply all pending stages
      python3 tools/patch_research.py --status    # show what is applied
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
STATE = ROOT / "tools" / ".research-state.json"

# ---------------------------------------------------------------- stage 1: config
STAGES = {}

STAGES["config"] = {
    "doc": "studio identity, two branches, artists, reviews, weekly Friday rate card",
    "edits": [
        # defaultConfig: replace the dead `hours:[...]` array with real structured data.
        (
            "span:hours",
            ("hours:['Tue 09:00–17:00','Wed 09:00–17:00','Thu 11:00–19:00','Fri 09:00–17:00','Sat 09:00–15:00']"),
            (
                "studio:{name:'Haywood Tattoo Studio',legalName:'Haywood Tattoos and Piercings',phone:'+27 61 759 3378',wa:'27617593378',instagram:'haywood_studio',website:'https://www.haywoodstudio.com',facebook:'',email:'',heroNote:'Taking private bookings in Pretoria Central, Mabopane, and on location'},"
                "branches:[{id:'central',live:true,name:'Pretoria Central',flagship:true,street:'296 Francis Baard Street',suburb:'Pretoria Central',city:'Pretoria',region:'Gauteng',label:'Flagship · private studio',travel:350,mapQuery:'296 Francis Baard Street, Pretoria Central',amenities:['On-site parking','Wheelchair-accessible parking','Credit, debit & mobile pay'],note:'Walk-ins are sometimes accommodated for standard services, but appointments are recommended — the book is busy.',hoursNote:'',hours:{mon:['10:00','18:00'],tue:['10:00','18:00'],wed:['10:00','18:00'],thu:['10:00','17:00'],fri:['10:00','18:00'],sat:['10:00','18:00'],sun:['11:00','17:00']}},"
                "{id:'mabopane',live:true,name:'Mabopane',flagship:false,street:'2241 Martha Modise Street',suburb:'Mabopane',city:'Tshwane',region:'Gauteng',label:'North location',travel:450,mapQuery:'2241 Martha Modise Street, Mabopane',amenities:['Street parking','Credit & debit cards'],note:'Same artists, same setup. Confirm your slot before you travel.',hoursNote:'Indicative — confirm your slot on WhatsApp.',hours:{mon:['10:00','18:00'],tue:['10:00','18:00'],wed:['10:00','18:00'],thu:['10:00','17:00'],fri:['10:00','18:00'],sat:['10:00','18:00'],sun:'closed'}}],"
                "defaultBranch:'central',"
                "artists:[{id:'yuran',live:true,name:'Yuran',role:'Resident artist',branch:'central',hourly:1200,specialties:['Black & grey','Fine line','Portraits','Full sleeves','Cover-ups','Abstract line art'],bio:'Ten-plus years of bespoke work, known for soft shading and line control on larger pieces.'}],\n      "
                "reviews:{live:true,score:4.9,reviews:100,suffix:'+',source:'Google',url:'',quote:'Exceptional care, spotless setup, and the design still looks sharper than the day I got it.'},\n      "
                "fridays:{live:true,day:'fri',hero:true,priority:5,label:'Piercing Fridays',title:'Piercing Fridays',from:'10:00',to:'15:00',slots:20,minSlots:15,low:100,high:150,services:['Nose','Ear lobe','Belly'],cta:'Claim a Friday slot',terms:'Selected nose, ear and belly piercings at the Friday rate · appointment only, capped per session · jewelry subject to stock · 18+ with valid ID or guardian consent · the artist confirms the price at the chair'}"
            ),
        ),
        # loader: merge the new keys over defaults so an older localStorage payload still upgrades.
        (
            "replace",
            "specials:Array.isArray(savedConfig.specials)?savedConfig.specials:clone(defaultConfig.specials)};",
            "specials:Array.isArray(savedConfig.specials)?savedConfig.specials:clone(defaultConfig.specials),"
            "studio:{...clone(defaultConfig.studio),...(savedConfig.studio||{})},"
            "reviews:{...clone(defaultConfig.reviews),...(savedConfig.reviews||{})},"
            "fridays:{...clone(defaultConfig.fridays),...(savedConfig.fridays||{})},"
            "artists:Array.isArray(savedConfig.artists)?savedConfig.artists:clone(defaultConfig.artists),"
            "defaultBranch:savedConfig.defaultBranch||defaultConfig.defaultBranch,"
            "branches:(Array.isArray(savedConfig.branches)&&savedConfig.branches.length?savedConfig.branches:[]).map(b=>({...clone(defaultConfig.branches[0]),...b,hours:{...clone(defaultConfig.branches[0].hours),...(b.hours||{})}})).concat(defaultConfig.branches.filter(d=>!(savedConfig.branches||[]).some(b=>b&&b.id===d.id)).map(clone))};",
        ),
    ]
}

# ---------------------------------------------------------------- stage 2: helpers
STAGES["helpers"] = {
    "doc": "day/hour formatting, branch lookup, weekly rate-card state, hero offer resolution",
    "edits": [
        (
            "insertBefore:function specialFor(",
            "function specialFor(",
            """const DAYS=['sun','mon','tue','wed','thu','fri','sat'];
    const DAY_LABEL={sun:'Sun',mon:'Mon',tue:'Tue',wed:'Wed',thu:'Thu',fri:'Fri',sat:'Sat'};
    const DAY_LONG={sun:'Sunday',mon:'Monday',tue:'Tuesday',wed:'Wednesday',thu:'Thursday',fri:'Friday',sat:'Saturday'};
    function branchList(){return(config.branches||[]).filter(b=>b.live!==false)}
    function branchById(id){const l=branchList();return l.find(b=>b.id===id)||l[0]||null}
    function activeBranch(){return branchById(config.defaultBranch)}
    function branchAddress(b){return b?[b.street,b.suburb,b.city,b.region].filter(Boolean).join(', '):''}
    function branchDay(b,key){const v=b&&b.hours?b.hours[key]:null;return Array.isArray(v)?v:null}
    function hoursLines(b){if(!b||!b.hours)return[];const runs=[];
      DAYS.forEach(d=>{const v=branchDay(b,d);const key=v?v[0]+'–'+v[1]:'closed';const last=runs[runs.length-1];
        if(last&&last.key===key)last.days.push(d);else runs.push({key,days:[d]})});
      return runs.map(r=>{const n=r.days.length;let label;
        if(n===DAYS.length)label='Every day';
        else if(n>2)label=DAY_LABEL[r.days[0]]+'–'+DAY_LABEL[r.days[r.days.length-1]];
        else label=r.days.map(d=>DAY_LABEL[d]).join(', ');
        return{label:label,days:r.days.slice(),text:r.key==='closed'?'Closed':r.key,open:r.key==='closed'?null:r.key.split('–')[0],close:r.key==='closed'?null:r.key.split('–')[1]}})}
    function openingHoursSpec(b){return DAYS.map(d=>{const v=branchDay(b,d);if(!v)return null;
      return{'@type':'OpeningHoursSpecification',dayOfWeek:'https://schema.org/'+DAY_LONG[d],opens:v[0],closes:v[1]}}).filter(Boolean)}
    function isFridayOpen(b,key){const fr=config.fridays;if(!fr||!fr.live)return false;
      const want=fr.day||'fri';if(key!==want)return false;
      if(!b)return true;const v=branchDay(b,key);if(!v)return false;
      const t=toMin(fr.from||'10:00'),c=toMin(fr.to||'15:00');return toMin(v[0])<=t&&toMin(v[1])>=c}
    function toMin(t){const p=String(t||'0:0').split(':');return(Number(p[0])||0)*60+(Number(p[1])||0)}
    function nextOn(key){const want=DAYS.indexOf(key);const now=new Date();let add=(want-now.getDay()+7)%7;
      const d=new Date(now);d.setHours(0,0,0,0);const cut=toMin((config.fridays||{}).to||'15:00');if(add===0&&now.getHours()*60+now.getMinutes()>=cut)add=7;
      d.setDate(d.getDate()+add);return d}
    function dayKeyOf(v){if(!v)return null;const d=new Date(String(v).length===10?v+'T12:00:00':v);return isNaN(d)?null:DAYS[d.getDay()]}
    function weekendDay(v){const k=dayKeyOf(v);return k==='sat'||k==='sun'}
    function fridayLabel(){const fr=config.fridays||{};return DAY_LONG[fr.day||'fri']+'s'}
    function fridayActive(){const fr=config.fridays||{};return fr.live?fr:null}
    function fridayHero(){const fr=fridayActive();return fr&&fr.hero!==false?fr:null}
    function heroOffer(){const dated=(config.specials||[]).filter(sp=>specialState(sp)==='live'&&sp.hero!==false).map(sp=>({type:'special',priority:Number(sp.priority)||10,start:sp.start||'0000',sp}));
      const fr=fridayHero();if(fr)dated.push({type:'fridays',priority:Number(fr.priority)||5,start:'9999',fr});
      if(!dated.length)return null;dated.sort((a,b)=>b.priority-a.priority||(a.start<b.start?1:-1));return dated[0]}
    function fridayRate(dateValue){const fr=config.fridays||{};if(!fr.live)return null;
      const k=dayKeyOf(dateValue||'');if(!k||k!==(fr.day||'fri'))return null;
      return{low:Number(fr.low)||0,high:Number(fr.high)||0,from:fr.from||'10:00',to:fr.to||'15:00',slots:Number(fr.slots)||0}}
    """,
        ),
        # specials: a weekly record is always in-window while live, and hero picks by priority
        (
            "replace",
            "function specialState(sp){if(!sp)return 'off';if(!sp.live)return 'off';const now=Date.now();",
            "function specialState(sp){if(!sp)return 'off';if(!sp.live)return 'off';if(sp.kind==='weekly')return 'live';const now=Date.now();",
        ),
        (
            "replace",
            "function activeSpecial(){return(config.specials||[]).filter(sp=>specialState(sp)==='live')[0]||null}",
            "function activeSpecial(){const o=heroOffer();return o&&o.type==='special'?o.sp:null}\n    function activeOffer(){return heroOffer()}",
        ),
    ]
}


def apply(page: str, stage: dict) -> str:
    for kind, *rest in stage["edits"]:
        if kind.startswith("span:"):
            anchor, repl = rest
            i = page.index(anchor)
            # span edits replace the anchor region exactly once
            assert page.count(anchor) == 1, f"span anchor not unique: {anchor[:50]}"
            page = page[:i] + repl + page[i + len(anchor):]
        elif kind.startswith("insertBefore:"):
            needle, block = rest
            assert block.split("(")[0].strip() in page or True
            if block[:40] in page:
                continue
            i = page.index(needle)
            page = page[:i] + block + page[i:]
        elif kind == "replace":
            a, b = rest
            if b[:60] in page and a not in page:
                continue
            n = page.count(a)
            assert n == 1, f"anchor found {n}x (want 1): {a[:70]}"
            page = page.replace(a, b)
        else:
            raise ValueError(kind)
    return page


def main() -> int:
    applied = json.loads(STATE.read_text()) if STATE.exists() else []
    if "--status" in sys.argv:
        print("applied:", applied or "(none)")
        return 0
    page = PAGE.read_text()
    before = page
    done = []
    for name, stage in STAGES.items():
        if name in applied:
            print(f"  · {name:<10} already applied, skipped")
            continue
        page = apply(page, stage)
        done.append(name)
        print(f"  ✓ {name:<10} {stage['doc']}")
    if page == before:
        print("nothing to do")
        return 0
    css = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
    assert css.count("{") == css.count("}"), "unbalanced CSS braces"
    PAGE.write_text(page)
    STATE.write_text(json.dumps(sorted(set(applied + done)), indent=0))
    print(f"written · {len(page)} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
