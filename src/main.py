import argparse, csv, hashlib, json, random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

TABLES = ['sku','location','supplier','supplier_capacity','lead_time','forecast_demand','inventory','purchase_order','production_plan','shortage','mitigation_option']

def save(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows: return
    with path.open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def build(out, skus=30, locations=5, weeks=8, suppliers=10, orders=100, seed=20261022):
    r=random.Random(seed); out=Path(out); out.mkdir(parents=True, exist_ok=True)
    sku=[{'sku_id':f'SKU-{i:06d}','name':f'Product {i}','uom':'EA','unit_cost':r.randint(10,200)} for i in range(1,skus+1)]
    loc=[{'location_id':f'LOC-{i:04d}','name':f'Warehouse {i}'} for i in range(1,locations+1)]
    sup=[{'supplier_id':f'SUP-{i:04d}','name':f'Supplier {i}','status':'ACTIVE'} for i in range(1,suppliers+1)]
    caps=[]; leads=[]
    for s in sup:
        caps.append({'capacity_id':f'CAP-{s["supplier_id"]}','supplier_id':s['supplier_id'],'weekly_capacity':r.randint(200,1000),'moq':10,'effective_from':'2025-12-29','effective_to':'2027-01-01'})
        leads.append({'lead_time_id':f'LT-{s["supplier_id"]}','supplier_id':s['supplier_id'],'lead_days':r.randint(7,28),'effective_from':'2025-12-29','effective_to':'2027-01-01'})
    forecast=[]; inv=[]; po=[]; prod=[]; shortages=[]; mits=[]; truth=[]
    start=date.fromisocalendar(2026,1,1)
    for a in sku:
        for b in loc:
            inv.append({'inventory_id':f'INV-{a["sku_id"]}-{b["location_id"]}','sku_id':a['sku_id'],'location_id':b['location_id'],'as_of_date':start.isoformat(),'on_hand':r.randint(80,350),'uom':'EA'})
            for w in range(1,weeks+1):
                qty=r.randint(15,65)*(3 if w in (6,12,40) and r.random()<.12 else 1)
                forecast.append({'demand_id':f'DEM-{a["sku_id"]}-{b["location_id"]}-2026W{w:02d}','sku_id':a['sku_id'],'location_id':b['location_id'],'week':f'2026W{w:02d}','quantity':qty,'uom':'EA'})
    for i in range(1,orders+1):
        a=r.choice(sku); b=r.choice(loc); s=r.choice(sup); wk=r.randint(1,weeks)
        arrival=start+timedelta(weeks=wk-1,days=r.choice([0,0,0,7]))
        po.append({'po_id':f'PO-2026-{i:06d}','sku_id':a['sku_id'],'location_id':b['location_id'],'supplier_id':s['supplier_id'],'quantity':r.randint(10,80),'ordered_on':(arrival-timedelta(days=28)).isoformat(),'expected_arrival':arrival.isoformat(),'status':'OPEN','uom':'EA'})
    arrivals=defaultdict(int)
    for p in po:
        d=date.fromisoformat(p['expected_arrival']); week=d.isocalendar().week
        if d.year==2026 and week<=weeks: arrivals[(p['sku_id'],p['location_id'],week)]+=p['quantity']
    demand={(d['sku_id'],d['location_id'],int(d['week'][-2:])):d['quantity'] for d in forecast}
    balances={(i['sku_id'],i['location_id']):i['on_hand'] for i in inv}
    counter=0
    for w in range(1,weeks+1):
        for a in sku:
            for b in loc:
                key=(a['sku_id'],b['location_id']); before=balances[key]; inbound=arrivals.get((*key,w),0); need=demand[(*key,w)]; after=before+inbound-need
                if after<0:
                    counter+=1; sid=f'SHORT-2026-{counter:06d}'; missing=-after
                    shortages.append({'shortage_id':sid,'sku_id':key[0],'location_id':key[1],'week':f'2026W{w:02d}','opening_balance':before,'inbound':inbound,'demand':need,'projected_balance':after,'shortage_qty':missing,'priority_score':missing*int(a['unit_cost']),'status':'OPEN','cause':'DEMAND_EXCEEDS_AVAILABLE'})
                    mits.append({'mitigation_id':f'MIT-{sid}-01','shortage_id':sid,'option_type':'EXPEDITE_SUPPLY','quantity':missing,'estimated_cost':round(missing*float(a['unit_cost'])*1.25,2),'status':'CANDIDATE_UNVERIFIED','reason':'Requires supplier capacity, MOQ and lead-time confirmation'})
                balances[key]=after
    # Labeled anomaly scenarios are isolated from valid baseline inputs.
    for idx,kind in enumerate(['INBOUND_DOUBLE_COUNT','UNAPPROVED_SUBSTITUTE','SUPPLIER_CAPACITY_EXCEEDED','LEAD_TIME_IGNORED','UOM_MISMATCH'],1):
        truth.append({'case_id':f'CASE-{idx:03d}','issue_type':kind,'expected_decision':'FLAG_FOR_REVIEW','description':'Synthetic isolated test case; not applied to baseline tables'})
    tables=dict(zip(TABLES,[sku,loc,sup,caps,leads,forecast,inv,po,prod,shortages,mits]))
    for name,rows in tables.items():
        if rows: save(out/f'{name}.csv',rows)
        else: (out/f'{name}.csv').write_text('',encoding='utf-8')
    save(out/'ground_truth.csv',truth)
    manifest={'seed':seed,'parameters':dict(skus=skus,locations=locations,weeks=weeks,suppliers=suppliers,orders=orders),'row_counts':{k:len(v) for k,v in tables.items()},'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.csv'))}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',default='outputs/run'); p.add_argument('--skus',type=int,default=30); p.add_argument('--locations',type=int,default=5); p.add_argument('--weeks',type=int,default=8); p.add_argument('--suppliers',type=int,default=10); p.add_argument('--orders',type=int,default=100); p.add_argument('--seed',type=int,default=20261022)
    a=p.parse_args(); print(json.dumps(build(a.out,a.skus,a.locations,a.weeks,a.suppliers,a.orders,a.seed),indent=2))
