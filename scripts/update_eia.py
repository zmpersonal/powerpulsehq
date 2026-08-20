#!/usr/bin/env python3
import os,json,urllib.parse,urllib.request
from pathlib import Path
from datetime import datetime,timezone,date
from collections import defaultdict,Counter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/electricity.json'
KEY=os.environ.get('EIA_API_KEY','').strip()
if not KEY: raise RuntimeError('EIA_API_KEY is not set. Add it under Settings > Secrets and variables > Actions.')
STATE_NAMES={'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','DC':'District of Columbia','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming'}

def fetch():
    # Six years gives enough history for same-month five-year comparisons while staying well below EIA pagination limits.
    params=[('api_key',KEY),('frequency','monthly'),('data[]','price'),('facets[sectorid][]','RES'),('sort[0][column]','period'),('sort[0][direction]','desc'),('offset','0'),('length','5000')]
    url='https://api.eia.gov/v2/electricity/retail-sales/data/?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={'User-Agent':'PowerPulseHQ/2.0 electricity index'})
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)

def pct(a,b):
    if a is None or b in (None,0):return None
    return round((a/b-1)*100,2)

def shift_month(period,delta):
    y,m=map(int,period.split('-')); idx=y*12+(m-1)+delta; return f'{idx//12:04d}-{idx%12+1:02d}'

raw=fetch(); rows=raw.get('response',{}).get('data',[])
if not rows: raise RuntimeError('EIA returned no residential retail-price rows')
series=defaultdict(dict)
for r in rows:
    sid=r.get('stateid'); period=r.get('period')
    try: price=float(r.get('price'))
    except: continue
    if sid in STATE_NAMES or sid=='US': series[sid][period]=price
if len([k for k in series if k in STATE_NAMES])<45: raise RuntimeError(f'EIA returned only {len(series)} jurisdictions')
# Use the most common latest period across state series to avoid one lagging jurisdiction defining the national release date.
latest_periods=[max(series[c]) for c in STATE_NAMES if series.get(c)]
period=Counter(latest_periods).most_common(1)[0][0]
states=[]
for code,name in STATE_NAMES.items():
    s=series.get(code,{})
    current=s.get(period)
    actual_period=period
    if current is None and s:
        actual_period=max(s);current=s[actual_period]
    if current is None: continue
    pm=shift_month(actual_period,-1);py=shift_month(actual_period,-12);p5=shift_month(actual_period,-60)
    states.append({'code':code,'name':name,'period':actual_period,'rate_cents_kwh':round(current,4),'prior_month_rate':s.get(pm),'prior_year_rate':s.get(py),'five_year_rate':s.get(p5),'mom_pct':pct(current,s.get(pm)),'yoy_pct':pct(current,s.get(py)),'five_year_pct':pct(current,s.get(p5)),'live':True})
if len(states)<50: raise RuntimeError(f'Only {len(states)} state/DC records could be built')
us=series.get('US',{})
us_period=period if period in us else (max(us) if us else None)
us_rate=us.get(us_period) if us_period else None
if us_rate is None: us_rate=sum(s['rate_cents_kwh'] for s in states)/len(states)
nat={'mom_pct':pct(us_rate,us.get(shift_month(us_period,-1)) if us_period else None),'yoy_pct':pct(us_rate,us.get(shift_month(us_period,-12)) if us_period else None),'five_year_pct':pct(us_rate,us.get(shift_month(us_period,-60)) if us_period else None)}
history=[]
if us:
    for p in sorted(us)[-72:]: history.append({'period':p,'rate':us[p]})
out={'updated':datetime.now(timezone.utc).isoformat(),'period':period,'national_rate_cents_kwh':round(us_rate,4),'national':nat,'live':True,'note':'Latest available EIA monthly residential average electricity prices with PowerPulse change metrics.','states':states,'history':history}
OUT.write_text(json.dumps(out,indent=2)+'\n')
print(f'EIA OK: {len(states)} states/DC; period {period}; U.S. {us_rate:.2f}¢/kWh')
print(f'National changes: 1m={nat["mom_pct"]}%, 1y={nat["yoy_pct"]}%, 5y={nat["five_year_pct"]}%')
