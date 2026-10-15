#!/usr/bin/env python3
"""patch_shop.py — admin picture uploads + real commerce management (round 6).

Idempotent stages, asserted anchors; index.html is only written if every edit in
the run applied cleanly. State: tools/.shop-state.json

  persist-catalog  products + lookbook saved with the config (they used to vanish)
  shipping         courier / collection model, address capture, live fee math
  orders-admin     orders table, search + status filter, detail drawer, CSV export
  editors          product CRUD + lookbook manager (Add product had no handler)
  images-core      file pick -> canvas downscale -> data URL, export for /assets
  images-slots     the picture control in every slot + card rendering
  css              styles for all of the above
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
STATE = ROOT / "tools" / ".shop-state.json"


MARKERS = [
    "config.products=clone(products)", "stripPhotos(c)",
    "shipping:{courier:", "id=\"checkoutTotals\"", "function cartItems()",
    "function fulfilLabel(v)", "function renderOrderProvinces()", "history:[{at:new Date().toLocaleString(),status:'Unpaid'",
    "id=\"adminOrders\"", "function renderAdminOrders()", "function orderRow(o)", "function exportOrdersCsv()",
    "data-order-status", "function showOrderDetail(id)", "renderAdminOrders();",
    "function imageControl(scope,id,ref,label,multi)", "data-img-input", "action==='img-export'", "action==='img-commit'", "action==='img-clear'",
    "renderAdminProducts();", "renderAdminLookbook();", "action==='save-products'", "action==='new-look'",
    "hasPhoto(p.image)", "galleryHtml(activeProject)", "id=\"offerArt\"", "id=\"fridayArt\"",
    "imageControl('special'", "imageControl('artist'", "imageControl('fridays'", ".imgctl{",
]


def assert_markers(page):
    missing = [m for m in MARKERS if m not in page]
    assert not missing, "markers absent (a stage edit was silently skipped):\n  " + "\n  ".join(missing)

def patch(page, stage):
    for kind, *rest in stage["edits"]:
        if kind == "insertBefore":
            needle, block = rest
            if block[:60] in page:
                continue
            i = page.index(needle)
            page = page[:i] + block + page[i:]
        elif kind == "replace":
            a, b = rest
            if b[:70] in page and a not in page:
                continue
            n = page.count(a)
            assert n == 1, f"anchor {n}x (want 1): {a[:90]}"
            page = page.replace(a, b)
        else:
            raise ValueError(kind)
    return page


STAGES = {}

# ------------------------------------------------------------------ 1. persist
STAGES["persist-catalog"] = {
    "doc": "products + lookbook persist through config",
    "edits": [
        ("replace",
         "delete config.hours;const HOURS_RETIRED=true;",
         "delete config.hours;"
         "if(Array.isArray(savedConfig.products)&&savedConfig.products.length){products.length=0;savedConfig.products.forEach(p=>products.push(p))}"
         "if(Array.isArray(savedConfig.lookbook)&&savedConfig.lookbook.length){lookbook.length=0;savedConfig.lookbook.forEach(p=>lookbook.push(p))}"),
        ("replace",
         "function save(){localStorage.setItem('haywoodConfig',JSON.stringify(config));",
         "function saveSlim(){try{const c=clone(config);stripPhotos(c);localStorage.setItem('haywoodConfig',JSON.stringify(c));return true}catch(e){return false}}"
         "function stripPhotos(c){const drop=o=>{if(!o)return;if(o.image&&o.image.local)delete o.image.local;"
         "[o.images,o.gallery].forEach(list=>{if(Array.isArray(list))list.forEach(g=>{if(g&&g.local)delete g.local})})};"
         "(c.products||[]).forEach(drop);(c.lookbook||[]).forEach(drop);(c.artists||[]).forEach(drop);(c.specials||[]).forEach(drop);if(c.fridays)drop(c.fridays)}"
         "function save(){config.products=clone(products);config.lookbook=clone(lookbook);try{localStorage.setItem('haywoodConfig',JSON.stringify(config))}"
         "catch(err){if(!saveSlim())toast('Local storage is full — export pictures for /assets instead of keeping them in the browser.')}"),
    ],
}

# ------------------------------------------------------------------ 2. shipping
CHECKOUT_FIELDS = (
    '<div class="field"><label>Fulfilment</label><select id="orderFulfilment">'
    '<option value="collect-central">Collect — Pretoria Central (free)</option>'
    '<option value="collect-mabopane">Collect — Mabopane (free)</option>'
    '<option value="courier">Courier to my address</option></select></div>'
    '<div class="field"><label>Province</label><select id="orderProvince"></select></div>'
    '<div class="field full" id="orderAddressWrap" hidden><div class="addr-grid">'
    '<input id="orderStreet" placeholder="Street address" />'
    '<input id="orderSuburb" placeholder="Suburb" />'
    '<input id="orderCity" placeholder="City" />'
    '<input id="orderPostal" placeholder="Postal code" inputmode="numeric" /></div>'
    '<p class="small">The courier needs a reachable phone number — double-check the one above.</p></div>'
    '<div class="field full"><label>Notes for this order</label><textarea id="orderNote" rows="2" '
    'placeholder="Gift wrapping, jewelry size, gate code…"></textarea></div>'
    '<div class="checkout-totals" id="checkoutTotals"></div>'
)

CHECKOUT_JS = r"""function cartItems(){const by={};cart.forEach(id=>{const p=products.find(x=>x.id===id);if(!p)return;
      if(!by[p.id])by[p.id]={id:p.id,name:p.name,price:p.price,qty:0};by[p.id].qty++});return Object.values(by)}
    function fulfilLabel(v){return v==='courier'?'Courier':(v==='collect-mabopane'?'Collect · Mabopane':'Collect · Pretoria Central')}
    function shippingFee(sub,fulfilment){const sh=config.shipping||{};if(fulfilment!=='courier')return 0;
      const freeOver=Number(sh.freeOver);if(isFinite(freeOver)&&sub>=freeOver)return 0;return Math.max(0,Number(sh.fee)||0)}
    function orderTotals(){const items=cartItems();const sub=items.reduce((s,p)=>s+p.price*p.qty,0);
      const el=document.getElementById('orderFulfilment');const f=el?el.value:'collect-central';
      const fee=shippingFee(sub,f);return{items,sub,fee,total:sub+fee,fulfilment:f}}
    function renderCheckoutTotals(){const box=document.getElementById('checkoutTotals');if(!box)return;
      const t=orderTotals();const sh=config.shipping||{};const freeOver=Number(sh.freeOver)||0;
      box.innerHTML=`<div><span>Items (${t.items.reduce((s,p)=>s+p.qty,0)})</span><b>${money(t.sub)}</b></div>`+
        `<div><span>${t.fulfilment==='courier'?esc(sh.courier||'Courier')+(sh.eta?' · '+esc(sh.eta):''):fulfilLabel(t.fulfilment)}</span><b>${t.fee?money(t.fee):'Free'}</b></div>`+
        (t.fulfilment==='courier'&&freeOver&&t.sub<freeOver?`<p class="small">Add ${money(freeOver-t.sub)} for free courier delivery.</p>`:'')+
        `<div class="checkout-total"><span>Total</span><b>${money(t.total)}</b></div>`;
      const wrap=document.getElementById('orderAddressWrap');if(wrap)wrap.hidden=t.fulfilment!=='courier'}
    function renderOrderProvinces(){const sel=document.getElementById('orderProvince');if(!sel||sel.options.length>1)return;
      const list=((config.shipping||{}).provinces||[]).concat(['Other']);
      sel.innerHTML='<option value="">Select province</option>'+list.map(p=>`<option value="${esc(p)}">${esc(p)}</option>`).join('')}
    function openCheckout(){if(!cart.length){toast('Your bag is empty.');return}renderOrderProvinces();
      const items=cartItems();
      $('#checkoutSummary').innerHTML=`<h4>${items.length} product${items.length>1?'s':''} in your order</h4><p>${items.map(p=>esc(p.name)+(p.qty>1?' ×'+p.qty:'')).join(' · ')}</p>`;
      renderCheckoutTotals();openOverlay('#checkoutOverlay')}
    function completeOrder(){const name=$('#orderName').value.trim(),email=$('#orderEmail').value.trim(),phone=$('#orderPhone').value.trim();
      const t=orderTotals();
      if(!name||!email){toast('Please add your name and email.');return}
      if(!phone){toast('A phone number is required so the studio can reach you about the order.');return}
      const gv=id=>{const el=document.getElementById(id);return el?el.value.trim():''};
      const a={street:gv('orderStreet'),suburb:gv('orderSuburb'),city:gv('orderCity'),province:($('#orderProvince')||{}).value||'',postal:gv('orderPostal')};
      if(t.fulfilment==='courier'&&(!a.street||!a.city||!a.province)){toast('The courier needs a street address, a city and a province.');return}
      const o={id:'ORD-'+String(Date.now()).slice(-6),created:new Date().toLocaleString(),name,phone,email,
        items:t.items,subTotal:t.sub,shipFee:t.fee,total:t.total,fulfilment:t.fulfilment,fulfilmentLabel:fulfilLabel(t.fulfilment),
        address:t.fulfilment==='courier'?a:null,branch:t.fulfilment==='collect-mabopane'?'mabopane':'central',
        note:gv('orderNote'),status:'Unpaid',tracking:'',
        history:[{at:new Date().toLocaleString(),status:'Unpaid',note:'Demo checkout — connect Yoco to capture payment'}]};
      orders.push(o);cart=[];save();renderCart();closeOverlays();
      toast('Order '+o.id+' saved — '+(o.fulfilment==='courier'?'courier label pending':'ready for collection'));renderAdmin()}
    """

STAGES["shipping"] = {
    "doc": "courier + collection, address capture, live totals, real order record",
    "edits": [
        ("replace", "ownerEmail:''}};",
         "ownerEmail:''},shipping:{courier:'The Courier Guy',fee:120,freeOver:1500,eta:'2–4 working days',"
         "provinces:['Gauteng','Western Cape','KwaZulu-Natal','Eastern Cape','Free State','Mpumalanga','Limpopo','North West','Northern Cape'],"
         "packedAt:'Pretoria Central flagship'}};"),
        ("replace",
         "artists:Array.isArray(savedConfig.artists)?savedConfig.artists:clone(defaultConfig.artists),",
         "artists:Array.isArray(savedConfig.artists)?savedConfig.artists:clone(defaultConfig.artists),"
         "shipping:{...clone(defaultConfig.shipping),...(savedConfig.shipping||{})},"),
        ("replace",
         '<div class="field"><label>Fulfilment</label><select id="orderFulfilment"><option>Collect from Pretoria studio</option><option>Delivery — fee confirmed after checkout</option></select></div>',
         CHECKOUT_FIELDS),
        ("replace",
         "function openCheckout(){if(!cart.length){toast('Your bag is empty.');return}const items=cart.map(id=>products.find(p=>p.id===id)).filter(Boolean),total=items.reduce((s,p)=>s+p.price,0);$('#checkoutSummary').innerHTML=`<h4>${items.length} item${items.length>1?'s':''} in your order</h4><p>${items.map(p=>p.name).join(' · ')}<br><strong style=\"color:var(--red);font-size:18px\">${money(total)}</strong></p>`;openOverlay('#checkoutOverlay')}",
         CHECKOUT_JS),
        ("replace",
         "function completeOrder(){const name=$('#orderName').value.trim(),email=$('#orderEmail').value.trim();if(!name||!email){toast('Please add your name and email.');return}const total=cart.map(id=>products.find(p=>p.id===id)).filter(Boolean).reduce((s,p)=>s+p.price,0);orders.push({id:'ORD-'+String(Date.now()).slice(-6),name,email,total,status:'Yoco demo paid',created:new Date().toLocaleString()});cart=[];save();renderCart();closeOverlays();toast('Demo order confirmed — welcome to the aftercare club.');renderAdmin()}",
         ""),
        ("replace", "$('#bookingDate').addEventListener('change',bookingHint);",
         "$('#orderFulfilment').addEventListener('change',renderCheckoutTotals);\n    "
         "['orderStreet','orderSuburb','orderCity','orderPostal'].forEach(id=>{const el=document.getElementById(id);if(el)el.addEventListener('input',renderCheckoutTotals)});\n    "
         "$('#bookingDate').addEventListener('change',bookingHint);"),
    ],
}

# ------------------------------------------------------------------- 3. orders
ORDERS_ADMIN_HTML = (
    '<div class="admin-card"><div class="admin-card-head"><div><h3>Orders</h3>'
    '<p>Who bought what, where it goes, and where it sits in the book.</p>'
    '<p class="small" id="orderSummaryLine"></p></div>'
    '<div class="orders-tools"><select id="orderFilter" aria-label="Filter by status"><option value="">All statuses</option></select>'
    '<input id="orderSearch" placeholder="Name, id, email, phone…" aria-label="Search orders" />'
    '<button class="btn btn-light btn-sm" data-action="export-orders">Export CSV</button></div></div>'
    '<div class="admin-list" id="adminOrders"></div></div>'
    '<div class="admin-card" id="orderDetailCard" hidden><div class="admin-card-head"><div><h3 id="orderDetailId">Order</h3><p id="orderDetailMeta"></p></div>'
    '<div class="orders-tools"><button class="btn btn-light btn-sm" data-action="order-whatsapp">WhatsApp the buyer</button>'
    '<button class="btn btn-light btn-sm" data-action="close-order-detail">Close</button></div></div>'
    '<div id="orderDetail"></div></div>'
)

ORDERS_JS = r"""const ORDER_FLOW=['Unpaid','Paid','Packed','Shipped','Delivered'];
    const ORDER_STATES=ORDER_FLOW.concat(['Cancelled','Refunded']);
    let activeOrder=null;
    function findOrder(id){return orders.find(o=>o.id===id)}
    function orderRow(o){const qty=o.items?o.items.reduce((s,i)=>s+i.qty,0):1;
      const where=o.fulfilment==='courier'?(o.address?esc([o.address.street,o.address.city,o.address.province].filter(Boolean).join(', ')):'<span class="warn">address missing</span>')
        :esc(o.fulfilmentLabel||fulfilLabel(o.fulfilment))+' · '+esc((branchById(o.branch)||{}).name||'');
      return `<div class="order-row" data-order="${o.id}"><div class="order-who"><b>${esc(o.name)}</b><span>${esc(o.id)} · ${qty} item${qty>1?'s':''} · ${esc(o.created||'')}</span></div>`+
        `<div class="order-what">${esc((o.items||[]).map(i=>i.name+(i.qty>1?' ×'+i.qty:'')).join(', '))||'items not captured'}</div>`+
        `<div class="order-where">${where}</div>`+
        `<div class="order-amt"><b>${money(o.total||0)}</b>${o.shipFee?`<span>+${money(o.shipFee)} courier</span>`:''}</div>`+
        `<div class="order-status"><select data-order-status="${o.id}" aria-label="Status for ${esc(o.id)}">${ORDER_STATES.map(s=>`<option${s===o.status?' selected':''}>${s}</option>`).join('')}</select></div></div>`}
    function filteredOrders(){const input=document.getElementById('orderSearch');
      const q=input?input.value.trim().toLowerCase():'';const f=(document.getElementById('orderFilter')||{}).value||'';
      return orders.slice().reverse().filter(o=>(!f||o.status===f)&&(!q||[o.id,o.name,o.email,o.phone,(o.items||[]).map(i=>i.name).join(' ')].join(' ').toLowerCase().includes(q)))}
    function renderAdminOrders(){const box=document.getElementById('adminOrders');if(!box)return;
      const sel=document.getElementById('orderFilter');
      if(sel&&!sel.dataset.built){sel.dataset.built='1';sel.innerHTML='<option value="">All statuses</option>'+ORDER_STATES.map(s=>`<option>${s}</option>`).join('')}
      const rows=filteredOrders();
      box.innerHTML=rows.length?rows.map(orderRow).join(''):'<p class="small">No orders in this view yet. A completed checkout lands here with items, contacts and the delivery address.</p>';
      const need=orders.filter(o=>['Delivered','Cancelled','Refunded'].indexOf(o.status)<0).length;
      const sum=orders.filter(o=>o.status!=='Cancelled').reduce((s,o)=>s+(o.total||0),0);
      const unpaid=orders.filter(o=>o.status==='Unpaid').length;
      const meta=document.getElementById('orderSummaryLine');
      if(meta)meta.textContent=`${orders.length} order(s) · ${need} awaiting action · ${money(sum)} booked${unpaid?(' · '+unpaid+' unpaid'):''}`;
      if(activeOrder)showOrderDetail(activeOrder)}
    function showOrderDetail(id){const card=document.getElementById('orderDetailCard');const host=document.getElementById('orderDetail');if(!card||!host)return;
      const o=findOrder(id);if(!o){card.hidden=true;activeOrder=null;return}activeOrder=o.id;card.hidden=false;
      $('#orderDetailId').textContent='Order '+o.id;
      $('#orderDetailMeta').textContent='Placed '+o.created+' · '+(o.fulfilmentLabel||fulfilLabel(o.fulfilment));
      const at=ORDER_FLOW.indexOf(o.status);const nxt=at<0?'Paid':ORDER_FLOW[Math.min(ORDER_FLOW.length-1,at+1)];
      const b=branchById(o.branch)||{};
      const addr=o.address?`<p>${esc(o.address.street||'')}${o.address.suburb?', '+esc(o.address.suburb):''}<br>${esc(o.address.city||'')}${o.address.postal?' · '+esc(o.address.postal):''}<br>${esc(o.address.province||'')}</p>`
        :`<p>Collection at <b>${esc(b.name||'Pretoria Central')}</b>${b.street?', '+esc(b.street):''}</p>`;
      host.innerHTML=`<div class="order-detail-grid">
        <section><h4>Packing list</h4><ul class="order-items">${(o.items||[]).map(i=>`<li><span>${esc(i.name)}</span><b>${i.qty} × ${money(i.price)} = ${money(i.qty*i.price)}</b></li>`).join('')||'<li>Items were not captured for this order.</li>'}</ul>
          <div class="order-totals"><span>Items</span><b>${money(o.subTotal||0)}</b></div>
          <div class="order-totals"><span>${o.fulfilment==='courier'?'Courier':'Collection'}</span><b>${o.shipFee?money(o.shipFee):'Free'}</b></div>
          <div class="order-totals total"><span>Total</span><b>${money(o.total||0)}</b></div>
          <p class="small">${esc((config.shipping||{}).packedAt||'Packed at the studio')} · ${esc((config.shipping||{}).courier||'courier')}${(config.shipping||{}).eta?' · '+esc((config.shipping||{}).eta):''}</p></section>
        <section><h4>Buyer</h4><p><b>${esc(o.name||'')}</b><br><a href="tel:${esc(String(o.phone||'').replace(/[^0-9+]/g,''))}">${esc(o.phone||'no number given')}</a><br><a href="mailto:${esc(o.email||'')}">${esc(o.email||'no email given')}</a></p>
          <h4>Where it goes</h4>${addr}${o.note?`<h4>Notes</h4><p class="muted">${esc(o.note)}</p>`:''}
          <div class="field"><label>Courier tracking number</label><input id="orderTracking" value="${esc(o.tracking||'')}" placeholder="e.g. CGS-4471902" /></div>
          <div class="admin-actions-row"><button class="btn btn-red btn-sm" data-action="order-advance" data-order="${o.id}">Mark as ${esc(nxt)}</button>
          <button class="btn btn-light btn-sm" data-action="order-save-note" data-order="${o.id}">Save tracking</button></div></section>
        <section><h4>History</h4><ol class="order-history">${(o.history||[]).slice().reverse().map(h=>`<li><b>${esc(h.status)}</b><span>${esc(h.at)}${h.note?' · '+esc(h.note):''}</span></li>`).join('')}</ol></section></div>`}
    function setOrderStatus(id,status,note){const o=findOrder(id);if(!o||o.status===status)return;
      o.status=status;o.history=o.history||[];o.history.push({at:new Date().toLocaleString(),status,note:note||''});
      save();renderAdmin();toast(o.id+' → '+status)}
    function exportOrdersCsv(){if(!orders.length){toast('No orders to export yet.');return}
      const cols=['id','created','status','name','phone','email','items','subTotal','shipFee','total','fulfilment','collectionBranch','street','suburb','city','province','postal','tracking','note'];
      const cell=v=>'"'+String(v==null?'':v).replace(/"/g,'""')+'"';
      const lines=[cols.join(',')].concat(orders.map(o=>[o.id,o.created,o.status,o.name,o.phone,o.email,
        (o.items||[]).map(i=>i.name+' x'+i.qty).join(' | '),o.subTotal,o.shipFee,o.total,o.fulfilmentLabel||fulfilLabel(o.fulfilment),
        o.fulfilment==='courier'?'':((branchById(o.branch)||{}).name||''),(o.address||{}).street,(o.address||{}).suburb,(o.address||{}).city,
        (o.address||{}).province,(o.address||{}).postal,o.tracking,o.note].map(cell).join(',')));
      downloadFile('haywood-orders.csv',new Blob([lines.join('\r\n')],{type:'text/csv;charset=utf-8'}))}
    function orderWhatsApp(o){const t=String(o.phone||'').replace(/[^0-9]/g,'').replace(/^0/,'27');
      if(!t){toast('No phone number on this order.');return}
      const ready=o.fulfilment==='courier'?('It will go out with '+(config.shipping.courier||'the courier')+'.')
        :('It is ready for collection at '+((branchById(o.branch)||{}).name||'the studio')+'.');
      const msg='Hi '+o.name+', this is Haywood. Order '+o.id+' ('+(o.items||[]).map(i=>i.name+(i.qty>1?' x'+i.qty:'')).join(', ')+') is '+o.status+'. '+ready+
        (o.tracking?' Tracking: '+o.tracking+'.':'')+' Total '+money(o.total||0)+'.';
      window.open('https://wa.me/'+t+'?text='+encodeURIComponent(msg),'_blank')}
    """

ORDERS_HANDLERS = r"""if(action==='close-order-detail'){activeOrder=null;const c=document.getElementById('orderDetailCard');if(c)c.hidden=true}
        if(action==='order-advance'){const o=findOrder(e.target.dataset.order);if(o){const i=ORDER_FLOW.indexOf(o.status);setOrderStatus(o.id,ORDER_FLOW[Math.min(ORDER_FLOW.length-1,i+1)],'Advanced from the dashboard')}}
        if(action==='order-save-note'){const o=findOrder(e.target.dataset.order);if(o){o.tracking=((document.getElementById('orderTracking')||{}).value||'').trim();o.history=o.history||[];o.history.push({at:new Date().toLocaleString(),status:o.status,note:'Tracking '+(o.tracking||'cleared')});save();renderAdmin();toast('Tracking saved')}}
        if(action==='order-whatsapp'){const o=findOrder(activeOrder);if(o)orderWhatsApp(o)}
        if(action==='export-orders')exportOrdersCsv();
        """

STAGES["orders-admin"] = {
    "doc": "orders table, filters, detail drawer, status flow, CSV export",
    "edits": [
        ("replace",
         '<div class="admin-list"></div><div class="admin-list" id="adminProducts"></div></div></div>',
         '<div class="admin-list"></div><div class="admin-list" id="adminProducts"></div></div>' + ORDERS_ADMIN_HTML + '</div>'),
        ("insertBefore", "function renderAdmin(){", ORDERS_JS),
        ("replace", "if(action==='handoff-artist')handoffArtist();",
         ORDERS_HANDLERS + "if(action==='handoff-artist')handoffArtist();"),
        ("replace", "renderAdminLocations();renderAdminFridays();renderAdminArtists();renderAdminReviews();",
         "renderAdminLocations();renderAdminFridays();renderAdminArtists();renderAdminReviews();renderAdminOrders();"),
        ("replace", "$('#chatInput').addEventListener('keydown'",
         "document.addEventListener('click',e=>{const row=e.target.closest('.order-row');if(row&&!e.target.closest('select')&&!e.target.closest('button')&&!e.target.closest('.imgctl'))showOrderDetail(row.dataset.order)});\n    "
         "document.addEventListener('change',e=>{const st=e.target.closest('[data-order-status]');if(st){setOrderStatus(st.dataset.orderStatus,st.value,'Changed from the orders list');return}"
         "if(e.target.id==='orderFilter')renderAdminOrders()});\n    "
         "document.addEventListener('input',e=>{if(e.target.id==='orderSearch')renderAdminOrders()});\n    $('#chatInput').addEventListener('keydown'"),
    ],
}

# ------------------------------------------------------------------ 5. images
IMAGES_JS = r"""const IMG_MAX=1400,IMG_QUALITY=.82;
    const IMAGE_KEY={product:'image',lookbook:'image',special:'image',artist:'portrait',fridays:'image'};
    function slug(s){return String(s==null?'':s).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'')||'image'}
    function assetName(scope,id,ext){const base=scope==='fridays'?'piercing-fridays':scope+'-'+slug(id);return base+'.'+(ext||'webp')}
    function humanBytes(b){return b>1048576?(b/1048576).toFixed(1)+' MB':Math.max(1,Math.round(b/1024))+' KB'}
    function approxBytes(ref){const s=(ref&&ref.local)||(ref&&ref.src)||'';const i=String(s).indexOf(',');return i<0?0:Math.round((String(s).length-i-1)*.75)}
    function hasPhoto(ref){return !!(ref&&ref.src&&ref.kind!=='gen')}
    function photoSrc(ref){if(!hasPhoto(ref))return '';if(ref.pending&&ref.local)return ref.local;return ref.src}
    function photoTag(ref,alt,cls){const s=photoSrc(ref);if(!s)return '';return `<img src="${s}" alt="${esc(alt||'studio picture')}" class="${cls||'photo-fill'}" loading="lazy" decoding="async" />`}
    function galleryHtml(p){if(!p||!Array.isArray(p.gallery)||!p.gallery.length)return '';
      return `<div class="look-gallery">${p.gallery.map(g=>photoTag(g,'additional view of '+String(p.title||'the piece'),'')).filter(Boolean).join('')}</div>`}
    function readFileImage(file){return new Promise((res,rej)=>{if(!file)return rej(new Error('No file selected.'));
      if(file.type&&!/^image\//.test(file.type))return rej(new Error('That is not an image file.'));
      const fr=new FileReader();fr.onload=()=>res(String(fr.result));fr.onerror=()=>rej(new Error('Could not read that file.'));fr.readAsDataURL(file)})}
    function fitImage(dataUrl,max,q){max=max||IMG_MAX;q=q==null?IMG_QUALITY:q;
      return new Promise(res=>{const img=new window.Image();
        img.onload=()=>{const w0=img.naturalWidth||img.width||max,h0=img.naturalHeight||img.height||max;
          const scale=Math.min(1,max/Math.max(w0,h0));const w=Math.max(1,Math.round(w0*scale)),h=Math.max(1,Math.round(h0*scale));
          let out=dataUrl,type='jpg',usedW=w0,usedH=h0;
          try{const c=document.createElement('canvas');c.width=w;c.height=h;const cx=c.getContext('2d');
            if(cx){cx.drawImage(img,0,0,w,h);const webp=c.toDataURL('image/webp',q);
              if(webp&&webp.indexOf('image/webp')>0){out=webp;type='webp'}else{const jpg=c.toDataURL('image/jpeg',q);if(jpg&&jpg.indexOf('image/jpeg')>0)out=jpg}
              usedW=w;usedH=h}}catch(e){}
          res({src:out,width:usedW,height:usedH,type})};
        img.onerror=()=>res({src:dataUrl,width:0,height:0,type:'original',error:'decode failed'});
        img.src=dataUrl})}
    function dataUrlToBlob(dataUrl){const s=String(dataUrl||'');const i=s.indexOf(',');if(i<0)return new Blob([s],{type:'text/plain'});
      const dec=window.atob||atob;const bin=dec(s.slice(i+1));const bytes=new Uint8Array(bin.length);for(let n=0;n<bin.length;n++)bytes[n]=bin.charCodeAt(n);
      return new Blob([bytes],{type:(s.slice(0,i).match(/:(.*?);/)||[])[1]||'application/octet-stream'})}
    function downloadFile(name,content){let url,revoke=false;
      if(typeof Blob!=='undefined'&&content instanceof Blob){url=URL.createObjectURL(content);revoke=true}else{url=String(content)}
      const a=document.createElement('a');a.href=url;a.download=name;a.rel='noopener';document.body.appendChild(a);a.click();a.remove();
      if(revoke&&URL.revokeObjectURL)setTimeout(()=>URL.revokeObjectURL(url),2000);return name}
    function imageTarget(scope,id){if(scope==='product')return products.find(p=>p.id===id);if(scope==='lookbook')return lookbook.find(p=>p.id===id);
      if(scope==='special')return(config.specials||[]).find(s=>s.id===id);if(scope==='artist')return(config.artists||[]).find(a=>a.id===id);
      if(scope==='fridays')return config.fridays;return null}
    function imageKeyOf(scope,el){if(el&&el.dataset&&el.dataset.imgkey)return el.dataset.imgkey;return IMAGE_KEY[scope]||'image'}
    function applyPicture(scope,id,key,ref,multi){const t=imageTarget(scope,id);if(!t)return;
      if(multi){t[key]=Array.isArray(t[key])?t[key]:[];t[key].push(ref)}else{t[key]=ref}
      save();renderProducts();renderLookbook();renderAdmin();
      toast('Picture attached for this browser — export it for /assets to publish it to visitors')}
    function imageControl(scope,id,ref,label,multi){ref=ref||null;const key=imageKeyOf(scope);
      const ext=ref&&ref.type==='jpg'?'jpg':'webp';const name=assetName(scope,id,ext);const bytes=approxBytes(ref);
      return `<div class="imgctl" data-imgscope="${scope}" data-imgid="${esc(id)}" data-imgkey="${key}"${multi?' data-imgmultiple="1"':''}>
        <div class="imgctl-side"><b>${esc(label||'Picture')}</b>
          <div class="imgctl-box">${ref?`<img src="${photoSrc(ref)}" alt="${esc(label||'preview')}" />`:'<span>Generated artwork in place</span>'}</div>
          <p class="small">${ref?esc((ref.width||'?')+'×'+(ref.height||'?')+' · '+humanBytes(bytes)+(ref.pending?' · this browser only':' · served from the repo')):'Upload a photo or a render and it replaces the generated art everywhere it is used.'}</p></div>
        <div class="imgctl-actions">
          <label class="btn btn-light btn-sm file-btn">${multi?'Add another shot':'Choose file'}<input type="file" accept="image/*" data-img-input hidden /></label>
          ${ref?`<button class="btn btn-red btn-sm" data-action="img-export" data-imgscope="${scope}" data-imgid="${esc(id)}"${multi?' data-imgmultiple="1"':''}>Download for /assets</button>`:''}
          ${ref&&ref.pending?`<button class="btn btn-light btn-sm" data-action="img-commit" data-imgscope="${scope}" data-imgid="${esc(id)}"${multi?' data-imgmultiple="1"':''}>I have committed it</button>`:''}
          ${ref?`<button class="btn btn-light btn-sm" data-action="img-clear" data-imgscope="${scope}" data-imgid="${esc(id)}"${multi?' data-imgmultiple="1"':''}>Remove</button>`:''}
          <code>assets/${esc(name)}</code></div></div>`}
    function onImagePicked(input){const ctl=input.closest('[data-imgscope]');if(!ctl)return;
      const scope=ctl.dataset.imgscope,id=ctl.dataset.imgid,key=imageKeyOf(scope,ctl),multi=ctl.hasAttribute('data-imgmultiple');
      const file=input.files&&input.files[0];if(!file)return;
      readFileImage(file).then(d=>fitImage(d)).then(f=>{
        applyPicture(scope,id,key,{kind:'data',src:f.src,local:f.src,width:f.width,height:f.height,type:f.type||'webp',pending:true},multi)
      }).catch(err=>toast((err&&err.message)||'Could not read that image.'));
      input.value=''}
    """

IMAGE_HANDLERS = r"""if(action==='img-export'){const ctl=e.target.closest('[data-imgscope]');const scope=ctl.dataset.imgscope,id=ctl.dataset.imgid,multi=ctl.hasAttribute('data-imgmultiple');
        const key=imageKeyOf(scope,ctl);const t=imageTarget(scope,id);const v=t?t[key]:null;
        const ref=multi&&Array.isArray(v)?v[v.length-1]:v;
        if(!ref||!ref.local){toast('Nothing to export yet.');return}
        const ext=ref.type==='jpg'?'jpg':'webp';const name=assetName(scope,id,ext);
        downloadFile(name,dataUrlToBlob(ref.local));
        ref.src='assets/'+name;ref.kind='asset';ref.pending=true;
        save();renderProducts();renderLookbook();renderAdmin();
        toast('Saved '+name+' — put it in assets/ then press “I have committed it”')}
        if(action==='img-commit'){const ctl=e.target.closest('[data-imgscope]');const scope=ctl.dataset.imgscope,id=ctl.dataset.imgid,multi=ctl.hasAttribute('data-imgmultiple');
          const key=imageKeyOf(scope,ctl);const t=imageTarget(scope,id);const v=t?t[key]:null;const ref=multi&&Array.isArray(v)?v[v.length-1]:v;
          if(!ref)return;ref.pending=false;delete ref.local;save();renderProducts();renderLookbook();renderAdmin();toast('Now served from '+ref.src)}
        if(action==='img-clear'){const ctl=e.target.closest('[data-imgscope]');const scope=ctl.dataset.imgscope,id=ctl.dataset.imgid,multi=ctl.hasAttribute('data-imgmultiple');
          const key=imageKeyOf(scope,ctl);const t=imageTarget(scope,id);if(!t)return;
          if(multi&&Array.isArray(t[key]))t[key]=t[key].slice(0,-1);else delete t[key];
          save();renderProducts();renderLookbook();renderAdmin();toast('Reverted to generated artwork')}
        """

STAGES["images-core"] = {
    "doc": "pick → compress → preview pipeline, asset naming, export, commit",
    "edits": [
        ("insertBefore", "function renderProducts(", IMAGES_JS),
        ("replace", "if(action==='handoff-artist')handoffArtist();",
         IMAGE_HANDLERS + "if(action==='handoff-artist')handoffArtist();"),
        ("replace", "$('#chatInput').addEventListener('keydown'",
         "document.addEventListener('change',e=>{if(e.target&&e.target.matches&&e.target.matches('input[type=file][data-img-input]'))onImagePicked(e.target)});\n    "
         "$('#chatInput').addEventListener('keydown'"),
    ],
}

# ------------------------------------------------------------------ 4. editors
PRODUCT_JS = r"""function renderAdminProducts(){const box=document.getElementById('adminProducts');if(!box)return;
      box.innerHTML=products.length?products.map((p,i)=>`<div class="loc-row" data-prod="${i}"><h4>${esc(p.name)||'Product '+(i+1)}</h4>
        <div class="field"><label>Name</label><input data-prod-field="name" value="${esc(p.name)}" /></div>
        <div class="field"><label>Price (R)</label><input type="number" min="0" data-prod-field="price" value="${Number(p.price)||0}" /></div>
        <div class="field"><label>Kind</label><select data-prod-field="type">${['aftercare','jewelry','both'].map(t=>`<option value="${t}"${p.type===t?' selected':''}>${t}</option>`).join('')}</select></div>
        <div class="field"><label>Fallback artwork</label><select data-prod-field="icon">${[['bottle','Bottle'],['hoop','Hoop'],['gem','Stone'],['kit','Kit']].map(kv=>`<option value="${kv[0]}"${(p.icon||'bottle')===kv[0]?' selected':''}>${kv[1]}</option>`).join('')}</select></div>
        <div class="field full"><label>Short description</label><input data-prod-field="desc" value="${esc(p.desc||'')}" /></div>
        <div class="field full">${imageControl('product',p.id,p.image,'Tile picture')}</div>
        <label class="check-row"><input type="checkbox" data-prod-field="live" ${p.live!==false?'checked':''} /> <span>Shown in the shop</span></label>
        <div class="admin-actions-row"><button class="btn btn-light btn-sm" data-action="remove-product" data-prod="${i}">Remove</button></div></div>`).join('')
        :'<p class="small">No products yet — add the first one.</p>'}
    function saveProducts(){const rows=document.querySelectorAll('#adminProducts .loc-row[data-prod]');
      [...rows].forEach(row=>{const p=products[Number(row.dataset.prod)];if(!p)return;
        [...row.querySelectorAll('[data-prod-field]')].forEach(el=>{const f=el.dataset.prodField;
          if(f==='live')p[f]=el.checked;else if(f==='price')p[f]=Number(el.value)||0;else p[f]=el.value.trim()})})}
    """

LOOKBOOK_JS = r"""function renderAdminLookbook(){const box=document.getElementById('adminLookbook');if(!box)return;
      box.innerHTML=lookbook.length?lookbook.map((p,i)=>`<div class="loc-row" data-look="${i}"><h4>${esc(p.title)||'Untitled project'}</h4>
        <div class="field"><label>Title</label><input data-look-field="title" value="${esc(p.title||'')}" /></div>
        <div class="field"><label>Category</label><select data-look-field="category">${['Ready-to-book flash','Adaptable concept','Repeatable study','Commission slot'].map(c=>`<option${p.category===c?' selected':''}>${c}</option>`).join('')}</select></div>
        <div class="field"><label>Availability</label><select data-look-field="status">${['Exclusive','Limited','Repeatable','Reserved','Archived'].map(s=>`<option${p.status===s?' selected':''}>${s}</option>`).join('')}</select></div>
        <div class="field"><label>Price or range (text)</label><input data-look-field="price" value="${esc(p.price||'')}" /></div>
        <div class="field"><label>Lead price (R)</label><input type="number" min="0" data-look-field="priceNum" value="${Number(p.priceNum)||0}" /></div>
        <div class="field"><label>Placement guidance</label><input data-look-field="placement" value="${esc(p.placement||'')}" /></div>
        <div class="field"><label>Size</label><input data-look-field="size" value="${esc(p.size||'')}" /></div>
        <div class="field"><label>Estimated sessions</label><input data-look-field="time" value="${esc(p.time||'')}" /></div>
        <div class="field"><label>Style</label><input data-look-field="style" value="${esc(p.style||'')}" /></div>
        <div class="field"><label>Artwork tone</label><select data-look-field="tone">${[['dark','Dark'],['red','Red'],['paper','Paper']].map(t=>`<option value="${t[0]}"${p.tone===t[0]?' selected':''}>${t[1]}</option>`).join('')}</select></div>
        <div class="field full"><label>Description</label><textarea rows="2" data-look-field="desc">${esc(p.desc||'')}</textarea></div>
        <div class="field full"><label>Tags (comma separated)</label><input data-look-field="tags" value="${esc((p.tags||[]).join(', '))}" /></div>
        <div class="field full"><label>What the artist asks first (one per line)</label><textarea rows="2" data-look-field="questions">${esc((p.questions||[]).join('\n'))}</textarea></div>
        <div class="field full">${imageControl('lookbook',p.id,p.image,'Card + detail picture')}</div>
        <div class="field full">${imageControl('lookbook',p.id,(p.gallery||[]).length?p.gallery[p.gallery.length-1]:null,'Extra shots of the piece',true)}</div>
        <label class="check-row"><input type="checkbox" data-look-field="live" ${p.live!==false?'checked':''} /> <span>Published in the lookbook</span></label>
        <div class="admin-actions-row"><button class="btn btn-light btn-sm" data-action="remove-look" data-look="${i}">Remove</button></div></div>`).join('')
        :'<p class="small">No projects published. Add one and the shop, the lookbook and the concierge all pick it up.</p>'}
    function saveLookbookRows(){const rows=document.querySelectorAll('#adminLookbook .loc-row[data-look]');
      [...rows].forEach(row=>{const p=lookbook[Number(row.dataset.look)];if(!p)return;
        [...row.querySelectorAll('[data-look-field]')].forEach(el=>{const f=el.dataset.lookField;
          if(f==='live')p.live=el.checked;
          else if(f==='priceNum')p.priceNum=Number(el.value)||0;
          else if(f==='tags')p.tags=el.value.split(',').map(s=>s.trim()).filter(Boolean);
          else if(f==='questions')p.questions=el.value.split('\n').map(s=>s.trim()).filter(Boolean);
          else p[f]=el.value.trim()})})}
    """

STAGES["editors"] = {
    "doc": "product CRUD + lookbook manager, both persisted",
    "edits": [
        ("replace",
         "$('#adminProducts').innerHTML=products.map(p=>`<div class=\"admin-list-row\"><div><b>${p.name}</b><span style=\"display:block\">${p.desc} · Inventory tracked</span></div><b style=\"color:#ff4e69\">${money(p.price)}</b></div>`).join('');",
         "renderAdminProducts();"),
        ("replace",
         "$('#adminLookbook').innerHTML=lookbook.map(p=>`<div class=\"admin-list-row\"><div><b>${p.title}</b><span style=\"display:block\">${p.category} · ${p.status} · ${p.placement}</span></div><b style=\"color:#ff4e69\">${p.price}</b></div>`).join('');",
         "renderAdminLookbook();"),
        ("insertBefore", "function renderAdmin(){", PRODUCT_JS + LOOKBOOK_JS),
        ("replace",
         '<button class="btn btn-red btn-sm" data-action="new-product">＋ Add product</button>',
         '<div class="orders-tools"><button class="btn btn-light btn-sm" data-action="save-products">Save products</button><button class="btn btn-red btn-sm" data-action="new-product">＋ Add product</button></div>'),
        ("replace",
         '<div class="admin-list" id="adminLookbook"></div>',
         '<div class="admin-list" id="adminLookbook"></div><div class="admin-actions-row"><button class="btn btn-red btn-sm" data-action="save-look">Publish lookbook</button><button class="btn btn-light btn-sm" data-action="new-look">＋ New project</button></div>'),
        ("replace",
         "if(action==='handoff-artist')handoffArtist();",
         "if(action==='new-product'){products.push({id:'product-'+Date.now().toString(36),name:'',desc:'',price:0,type:'aftercare',tone:'',icon:'bottle',live:true});save();renderAdmin();toast('Draft product added — fill it in, then save products')}"
         "if(action==='save-products'){saveProducts();save();renderProducts();renderCart();renderAdmin();toast('Products saved')}"
         "if(action==='remove-product'){products.splice(Number(e.target.dataset.prod),1);save();renderProducts();renderCart();renderAdmin();toast('Product removed')}"
         "if(action==='new-look'){lookbook.push({id:'project-'+Date.now().toString(36),title:'Untitled project',category:'Adaptable concept',status:'Limited',price:'R 0',priceNum:0,placement:'',size:'',time:'',style:'',tone:'dark',desc:'',questions:[],tags:[],live:false});save();renderAdmin();toast('Draft project added')}"
         "if(action==='save-look'){saveLookbookRows();save();renderLookbook();renderAdmin();toast('Lookbook published')}"
         "if(action==='remove-look'){lookbook.splice(Number(e.target.dataset.look),1);save();renderLookbook();renderAdmin();toast('Project removed')}"
         "if(action==='handoff-artist')handoffArtist();"),
    ],
}

# ------------------------------------------------------------------ 6. slots
OFFER_ART_JS = r"""function renderOfferArt(ref,alt){const host=document.getElementById('offerArt');if(!host)return;
      if(hasPhoto(ref)){host.hidden=false;host.innerHTML=photoTag(ref,alt||'Offer picture','')}
      else{host.hidden=true;host.innerHTML=''}}
    """

STAGES["images-slots"] = {
    "doc": "photos on product tiles, lookbook cards + detail, offer strip, Friday band, portraits",
    "edits": [
        ("replace",
         '<div class="product-art ${p.tone}">${iconSvg(p.icon)}</div>',
         '<div class="product-art ${p.tone}${hasPhoto(p.image)?\' has-photo\':\'\'}">${photoTag(p.image,p.name)||iconSvg(p.icon)}</div>'),
        ("replace",
         '<div class="look-image ${p.tone}"><span class="availability">${p.status}</span>${artSvg(p.tone)}</div>',
         '<div class="look-image ${p.tone}${hasPhoto(p.image)?\' has-photo\':\'\'}"><span class="availability">${p.status}</span>${photoTag(p.image,p.title)||artSvg(p.tone)}</div>'),
        ("replace",
         '`<div class="look-image ${activeProject.tone} look-modal-art">${artSvg(activeProject.tone)}</div>',
         '`<div class="look-image ${activeProject.tone} look-modal-art${hasPhoto(activeProject.image)?\' has-photo\':\'\'}">${photoTag(activeProject.image,activeProject.title)||artSvg(activeProject.tone)}${galleryHtml(activeProject)}</div>'),
        # artist portrait
        ("replace",
         'return `<article class="artist-card"><b>${esc(a.name)}</b>',
         'return `<article class="artist-card${hasPhoto(a.portrait)?\' has-photo\':\'\'}"><div class="artist-id"><div>${photoTag(a.portrait,a.name+\' — portrait\',\'artist-photo\')}</div><div><b>${esc(a.name)}</b>'),
        ("replace",
         '<span>${esc(a.role||\'Artist\')}${b?\' · \'+esc(b.name):\'\'}</span><p>${esc((a.specialties||[]).join(\' · \'))}</p>',
         '<span>${esc(a.role||\'Artist\')}${b?\' · \'+esc(b.name):\'\'}</span></div></div><p>${esc((a.specialties||[]).join(\' · \'))}</p>'),
        # hero offer picture, driven by the live special
        ("replace", "put('offerCopy',sp.copy||'');",
         "put('offerCopy',sp.copy||'');\n      renderOfferArt(sp.image,sp.title)"),
        ("insertBefore", "function renderSpecial(){", OFFER_ART_JS),
        ("replace",
         '<p class="offer-fine" id="offerFine">Ends 30 Nov 2026 · Indicative discount · final quote confirmed by the artist · deposit still secures the slot · 18+ with valid ID</p></div>',
         '<p class="offer-fine" id="offerFine">Ends 30 Nov 2026 · Indicative discount · final quote confirmed by the artist · deposit still secures the slot · 18+ with valid ID</p><div class="offer-art" id="offerArt" hidden></div></div>'),
        # Friday band picture
        ("replace", '<p class="friday-perk" id="friPerk">',
         '<div class="friday-art" id="fridayArt" hidden></div><p class="friday-perk" id="friPerk">'),
        ("replace", "const perk=document.getElementById('friPerk');if(perk){perk.textContent=fr.perk||'';perk.hidden=!fr.perk}",
         "const perk=document.getElementById('friPerk');if(perk){perk.textContent=fr.perk||'';perk.hidden=!fr.perk}\n      "
         "const fart=document.getElementById('fridayArt');if(fart){if(hasPhoto(fr.image)){fart.hidden=false;fart.innerHTML=photoTag(fr.image,fr.title||'Piercing Fridays','')}else{fart.hidden=true;fart.innerHTML=''}}"),
        # specials list: one control per published row, where the id already exists
        ("replace",
         "+(sp.end?fmtDate(sp.end):'no end date')+'</span></div>'",
         "+(sp.end?fmtDate(sp.end):'no end date')+'</span>'+imageControl('special',sp.id,sp.image,'Offer picture')+'</div>'"),
        # artists roster row gains the portrait control
        ("replace",
         '<div class="field full"><label>Bio</label><textarea rows="2" data-artist-field="bio">${esc(a.bio||\'\')}</textarea></div>',
         '<div class="field full"><label>Bio</label><textarea rows="2" data-artist-field="bio">${esc(a.bio||\'\')}</textarea></div>'
         + '<div class="field full">${imageControl(\'artist\',a.id,a.portrait,\'Portrait\')}</div>'),
        # Fridays panel: the band's own picture
        ("replace",
         "set('frLive',fr.live!==false);set('frHero',fr.hero!==false);",
         "set('frLive',fr.live!==false);set('frHero',fr.hero!==false);\n      "
         "const friImg=document.getElementById('friImage');"
         "if(friImg)friImg.innerHTML=imageControl('fridays','fridays',(config.fridays||{}).image,'Band picture')"),
        ("replace",
         '<span>Also take over the hero offer card when no dated special outranks it</span></label></div><div class="admin-actions-row">',
         '<span>Also take over the hero offer card when no dated special outranks it</span></label></div>'
         '<div class="field full" id="friImage"></div><div class="admin-actions-row">'),
    ],
}

# ---------------------------------------------------------------------- 7. css
SHOP_CSS = """
    /* uploads, orders, checkout */
    .has-photo{position:relative;overflow:hidden}
    .photo-fill{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;background:#0f0e10}
    .look-image.has-photo .availability{position:relative;z-index:2;display:inline-block;margin:12px 0 0 12px}
    .product-art.has-photo{min-height:150px}
    .product-art.has-photo>.photo-fill{z-index:1}
    .offer-art{margin:14px 0 0;border-radius:15px;overflow:hidden;border:1px solid rgba(255,255,255,.14)}
    .offer-art img{display:block;width:100%;height:180px;object-fit:cover}
    .offer-art[hidden]{display:none}
    .friday-art{border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,.13);margin-bottom:14px}
    .friday-art img{display:block;width:100%;height:150px;object-fit:cover}
    .friday-art[hidden]{display:none}
    .artist-card.has-photo .artist-id{display:grid;grid-template-columns:58px 1fr;gap:14px;align-items:center;margin-bottom:8px}
    .artist-id>div:first-child{width:58px;height:58px;border-radius:14px;overflow:hidden;position:relative;background:#15141a}
    .artist-photo{border-radius:14px}
    .look-gallery{position:absolute;left:12px;right:12px;bottom:12px;display:grid;grid-template-columns:repeat(3,1fr);gap:6px;z-index:2}
    .look-gallery img{width:100%;height:52px;object-fit:cover;border-radius:9px;border:1px solid rgba(255,255,255,.22);display:block;background:#0f0e10}
    .imgctl{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;padding:13px;border-radius:14px;background:#131316;border:1px solid #2c2b31;margin-top:6px}
    .imgctl-side b{display:block;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:#ff8fa0;margin-bottom:9px}
    .imgctl-box{aspect-ratio:4/3;border-radius:11px;background:#0b0b0d;border:1px dashed #3a393f;display:grid;place-items:center;overflow:hidden;position:relative}
    .imgctl-box img{width:100%;height:100%;object-fit:cover;display:block}
    .imgctl-box span{font-size:11px;color:#6f6c70;padding:0 12px;text-align:center}
    .imgctl-side .small{margin:8px 0 0;font-size:10.5px;color:#8b878a;line-height:1.5}
    .imgctl-actions{display:grid;gap:7px;align-content:start}
    .imgctl-actions .btn{width:100%;justify-content:center}
    .file-btn{position:relative;overflow:hidden;cursor:pointer}
    .imgctl-actions code{font-size:9.5px;color:#7f7c80;word-break:break-all;background:#0d0d0f;padding:6px 7px;border-radius:8px;border:1px solid #26252b}
    .special-row{display:grid}
    .orders-tools{display:flex;gap:7px;align-items:center;flex-wrap:wrap}
    .orders-tools select,.orders-tools input{padding:8px 10px;border-radius:10px;background:#0f0f11;border:1px solid #33323a;color:#f1eff0;font-size:12px;font-family:inherit}
    .orders-tools input{min-width:170px}
    .order-row{display:grid;grid-template-columns:1.1fr 1.4fr 1.2fr .7fr auto;gap:14px;align-items:center;padding:13px 12px;border-radius:13px;border:1px solid #2b2a2e;background:#18181b;cursor:pointer}
    .order-row+.order-row{margin-top:8px}
    .order-row:hover{border-color:#43424a;background:#1d1d21}
    .order-who b{display:block;font-size:13.5px;color:#fff}
    .order-who span{display:block;font-size:10.5px;color:#7f7c80;margin-top:3px}
    .order-what,.order-where{font-size:12px;color:#c6c2c4;line-height:1.45}
    .order-where .warn{color:#ffb3bf}
    .order-amt{text-align:right}.order-amt b{display:block;color:#ff4e69;font-size:14px}
    .order-amt span{display:block;font-size:10px;color:#7f7c80}
    .order-status select{padding:8px 9px;border-radius:9px;background:#0f0f11;border:1px solid #3a3940;color:#fff;font-size:11.5px}
    .order-detail-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px}
    .order-detail-grid section{min-width:0}
    .order-detail-grid h4{margin:0 0 8px;font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:#7f7c80}
    .order-detail-grid h4:not(:first-child){margin-top:18px}
    .order-detail-grid p{margin:0 0 10px;font-size:12.5px;line-height:1.6;color:#d3d0ce}
    .order-detail-grid a{color:#ff8fa0;text-decoration:none}
    .order-items{list-style:none;margin:0 0 12px;padding:0;display:grid;gap:7px}
    .order-items li{display:flex;justify-content:space-between;gap:12px;font-size:12.5px;color:#d3d0ce;padding-bottom:7px;border-bottom:1px solid #26252b}
    .order-items li b{color:#fff;font-weight:600;white-space:nowrap;font-variant-numeric:tabular-nums}
    .order-totals{display:flex;justify-content:space-between;font-size:12.5px;color:#a9a5a8;padding:4px 0}
    .order-totals b{color:#f1eff0;font-variant-numeric:tabular-nums}
    .order-totals.total{margin-top:6px;padding-top:9px;border-top:1px solid #34333a;font-size:14px}
    .order-totals.total b{color:#ff4e69}
    .order-history{list-style:none;margin:0;padding:0;display:grid;gap:9px}
    .order-history li{display:grid;gap:2px;font-size:12px;color:#a9a5a8;padding-left:14px;position:relative}
    .order-history li:before{content:'';position:absolute;left:0;top:6px;width:6px;height:6px;border-radius:50%;background:#43424a}
    .order-history li:first-child:before{background:#ff4e69}
    .order-history b{color:#f1eff0;font-weight:600}
    .addr-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:9px;margin-bottom:7px}
    .checkout-totals{margin-top:18px;padding:15px 17px;border-radius:16px;background:rgba(17,16,18,.045);border:1px solid var(--line)}
    .checkout-totals div{display:flex;justify-content:space-between;gap:12px;font-size:12.5px;color:var(--muted);padding:3px 0}
    .checkout-totals div b{color:#111;font-variant-numeric:tabular-nums}
    .checkout-totals .checkout-total{margin-top:8px;padding-top:9px;border-top:1px solid var(--line);font-size:15px}
    .checkout-totals .checkout-total b{color:var(--red);font-family:Georgia,serif;font-size:22px;font-weight:400}
    .checkout-totals p{margin:8px 0 0;font-size:11.5px}
    @media(max-width:900px){.order-row{grid-template-columns:1fr 1fr;gap:9px}.order-row .order-what{grid-column:1/-1}.order-amt{text-align:left}.imgctl{grid-template-columns:1fr}}
    @media(max-width:600px){.orders-tools input{min-width:0;width:100%}.order-row{grid-template-columns:1fr}.look-gallery{grid-template-columns:repeat(2,1fr)}}
"""

STAGES["css"] = {"doc": "orders, checkout, upload control styles", "edits": [
    ("insertBefore", "  </style>", SHOP_CSS),
]}

# ---------------------------------------------------------------- 8. downloads

ORDER = ["persist-catalog", "shipping", "orders-admin", "images-core",
         "editors", "images-slots", "css"]


def main() -> int:
    applied = json.loads(STATE.read_text()) if STATE.exists() else []
    if "--status" in sys.argv:
        print("applied:", applied or "(none)")
        return 0
    page = PAGE.read_text()
    start = page
    done = []
    for name in ORDER:
        if name in applied:
            print(f"  · {name:<16} already applied")
            continue
        page = patch(page, STAGES[name])
        done.append(name)
        print(f"  ✓ {name:<16} {STAGES[name]['doc']}")
    if page == start:
        # the state file may claim credit for a page that was restored: verify anyway
        assert_markers(page)
        print("nothing to do (markers verified)")
        return 0
    assert_markers(page)
    css = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
    assert css.count("{") == css.count("}"), f"unbalanced CSS {css.count('{')}/{css.count('}')}"
    open("/tmp/shop.js", "w").write(re.search(r"<script>(.*)</script>", page, re.S).group(1))
    PAGE.write_text(page)
    STATE.write_text(json.dumps(sorted(set(applied + done)), indent=0))
    print(f"written · {len(page)} chars · +{len(page)-len(start)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
