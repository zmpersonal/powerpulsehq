#!/usr/bin/env python3
from pathlib import Path
import json,csv,re
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'data/electricity.json').read_text())
devices=json.loads((ROOT/'data/devices.json').read_text())

def pct(v): return 'n/a' if v is None else f'{v:+.1f}%'
def cost(rate,kwh): return rate/100*kwh

def replace(path, patterns):
    p=ROOT/path
    if not p.exists(): return
    t=p.read_text()
    for pat,repl in patterns:t=re.sub(pat,repl,t,flags=re.S)
    p.write_text(t)

# Rebuild data CSVs.
with (ROOT/'data/electricity.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['state_code','state','period','rate_cents_kwh','month_over_month_pct','year_over_year_pct','five_year_pct','live'])
    for s in d['states']:w.writerow([s['code'],s['name'],s['period'],s['rate_cents_kwh'],s['mom_pct'],s['yoy_pct'],s['five_year_pct'],s['live']])
with (ROOT/'data/device-cost-index.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['device_slug','device','category','annual_kwh','scenario','state_code','state','period','rate_cents_kwh','annual_cost_usd','monthly_cost_usd'])
    for dv in devices:
        for s in d['states']:
            annual=cost(s['rate_cents_kwh'],dv['annual_kwh']);w.writerow([dv['slug'],dv['name'],dv['category'],dv['annual_kwh'],dv['scenario'],s['code'],s['name'],s['period'],s['rate_cents_kwh'],round(annual,2),round(annual/12,2)])

# Instead of fragile patching, regenerate state pages and device tables from known markers embedded below.
# Shared static shell is deliberately kept simple here.
CSS='/assets/style.css';JS='/assets/app.js'
HEADER='''<div class="topline"></div><header><div class="wrap"><nav><a class="brand" href="/"><span class="mark">⚡</span>POWERPULSE<b>HQ</b></a><div class="navlinks"><a href="/electricity-prices/">Price Index</a><a href="/cost-to-run/">Cost to Run</a><a href="/rankings/">Rankings</a><a href="/calculator/">Calculator</a><a href="/data-download/">Data</a><span class="status">LIVE GRID</span></div></nav></div></header>'''
FOOTER='''<footer><div class="wrap foot"><div>PowerPulseHQ · U.S. electricity price intelligence and operating-cost benchmarks.</div><div><a href="/methodology/">Methodology</a><a href="/home-wellness-equipment/">Home wellness</a></div></div></footer>'''
def page(title,desc,path,body):
    import html
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc)}"><link rel="canonical" href="https://powerpulsehq.com{path}"><link rel="stylesheet" href="{CSS}"><script defer src="{JS}"></script></head><body>{HEADER}{body}{FOOTER}</body></html>'

def banner():return '' if d.get('live') else '<div class="starter">Starter snapshot: run the GitHub data workflow to replace preview rates with current monthly EIA data.</div>'

# Electricity table
rows=''.join(f'<tr><td><a href="/states/{s["code"].lower()}/">{s["name"]}</a></td><td>{s["rate_cents_kwh"]:.2f}¢</td><td>{pct(s["mom_pct"])}</td><td>{pct(s["yoy_pct"])}</td><td>{pct(s["five_year_pct"])}</td><td>{s["period"]}</td></tr>' for s in sorted(d['states'],key=lambda x:x['rate_cents_kwh']))
body=f'<main><section class="hero"><div class="wrap">{banner()}<div class="eyebrow">POWERPULSE U.S. ELECTRICITY PRICE INDEX</div><h1>Residential electricity prices by state.</h1><p class="lead">Compare the latest available average residential electricity rate in every state and Washington, D.C., plus monthly, annual and five-year price changes.</p></div></section><section class="section"><div class="wrap"><div class="table-wrap"><table><thead><tr><th>State</th><th>Rate</th><th>1 month</th><th>1 year</th><th>5 years</th><th>Period</th></tr></thead><tbody>{rows}</tbody></table></div></div></section></main>'
(ROOT/'electricity-prices/index.html').write_text(page('Electricity Prices by State — PowerPulse U.S. Electricity Price Index','Compare residential electricity prices and price changes across all 50 states plus Washington, D.C.','/electricity-prices/',body))

# State pages
for s in d['states']:
    dr=''.join(f'<tr><td><a href="/cost-to-run/{dv["slug"]}/">{dv["name"]}</a></td><td>{dv["annual_kwh"]:,.0f}</td><td>${cost(s["rate_cents_kwh"],dv["annual_kwh"])/12:,.0f}</td><td>${cost(s["rate_cents_kwh"],dv["annual_kwh"]):,.0f}</td></tr>' for dv in devices)
    body=f'<main><section class="hero"><div class="wrap"><div class="eyebrow">STATE ELECTRICITY REPORT / {s["code"]}</div><h1>{s["name"]} electricity prices and operating costs.</h1><p class="lead">Latest residential average: <strong>{s["rate_cents_kwh"]:.2f}¢/kWh</strong> for {s["period"]}.</p></div></section><section class="section"><div class="wrap"><div class="metric-grid"><div class="metric"><span class="label">Residential rate</span><strong>{s["rate_cents_kwh"]:.2f}¢</strong></div><div class="metric"><span class="label">1 month</span><strong>{pct(s["mom_pct"])}</strong></div><div class="metric"><span class="label">1 year</span><strong>{pct(s["yoy_pct"])}</strong></div><div class="metric"><span class="label">5 years</span><strong>{pct(s["five_year_pct"])}</strong></div></div><div class="article"><h2>Cost to run common equipment in {s["name"]}</h2><p>Every row uses the same standardized annual kWh assumption used on the national Cost to Run Index.</p></div><div class="table-wrap"><table><thead><tr><th>Equipment</th><th>Annual kWh</th><th>Monthly cost</th><th>Annual cost</th></tr></thead><tbody>{dr}</tbody></table></div></div></section></main>'
    p=ROOT/'states'/s['code'].lower();p.mkdir(parents=True,exist_ok=True);(p/'index.html').write_text(page(f'{s["name"]} Electricity Prices & Cost to Run Index — PowerPulseHQ',f'Current {s["name"]} residential electricity prices, price changes and standardized equipment operating costs.',f'/states/{s["code"].lower()}/',body))

# Device pages
for dv in devices:
    ranked=sorted(d['states'],key=lambda s:cost(s['rate_cents_kwh'],dv['annual_kwh']))
    table=''.join(f'<tr><td>#{i}</td><td><a href="/states/{s["code"].lower()}/">{s["name"]}</a></td><td>{s["rate_cents_kwh"]:.2f}¢</td><td>${cost(s["rate_cents_kwh"],dv["annual_kwh"])/12:,.0f}</td><td>${cost(s["rate_cents_kwh"],dv["annual_kwh"]):,.0f}</td></tr>' for i,s in enumerate(ranked,1))
    us=cost(d['national_rate_cents_kwh'],dv['annual_kwh'])
    body=f'<main><section class="hero"><div class="wrap"><div class="eyebrow">COST TO RUN / {dv["category"].upper()}</div><h1>Cost to run a {dv["name"].lower()} by state.</h1><p class="lead">Standardized scenario: <strong>{dv["scenario"]}</strong>. Annual energy use: <strong>{dv["annual_kwh"]:,.0f} kWh</strong>.</p></div></section><section class="section"><div class="wrap"><div class="metric-grid"><div class="metric"><span class="label">U.S. benchmark</span><strong>${us:,.0f}/yr</strong></div><div class="metric"><span class="label">Annual energy</span><strong>{dv["annual_kwh"]:,.0f} kWh</strong></div><div class="metric"><span class="label">Cheapest market</span><strong>{ranked[0]["name"]}</strong></div><div class="metric"><span class="label">Highest-cost market</span><strong>{ranked[-1]["name"]}</strong></div></div><div class="table-wrap" style="margin-top:30px"><table><thead><tr><th>Rank</th><th>State</th><th>Rate</th><th>Monthly benchmark</th><th>Annual benchmark</th></tr></thead><tbody>{table}</tbody></table></div></div></section></main>'
    p=ROOT/'cost-to-run'/dv['slug'];p.mkdir(parents=True,exist_ok=True);(p/'index.html').write_text(page(f'Cost to Run a {dv["name"]} by State — PowerPulseHQ',f'Compare standardized electricity costs to run a {dv["name"].lower()} in every state.',f'/cost-to-run/{dv["slug"]}/',body))

# Rankings
specs=[('cheapest','Cheapest Electricity by State','rate_cents_kwh',False),('most-expensive','Most Expensive Electricity by State','rate_cents_kwh',True),('fastest-rising','Fastest-Rising Electricity Prices','yoy_pct',True),('five-year','Biggest Five-Year Electricity Price Increases','five_year_pct',True)]
for slug,title,key,rev in specs:
    vals=[s for s in d['states'] if s.get(key) is not None]
    vals=sorted(vals,key=lambda x:x[key],reverse=rev)
    items=''.join(f'<div class="rank-item"><div class="rank-no">#{i}</div><div><a style="color:var(--text);text-decoration:none;font-weight:800" href="/states/{s["code"].lower()}/">{s["name"]}</a></div><div class="rank-value">{(f"{s[key]:.2f}¢" if key=="rate_cents_kwh" else pct(s[key]))}</div></div>' for i,s in enumerate(vals,1)) or '<div class="starter">This ranking requires monthly history and will populate after the first live EIA update.</div>'
    body=f'<main><section class="hero"><div class="wrap"><div class="eyebrow">U.S. ELECTRICITY RANKING</div><h1>{title}.</h1><p class="lead">Automatically rebuilt from the latest EIA residential electricity price data.</p></div></section><section class="section"><div class="wrap"><div class="rank-list">{items}</div></div></section></main>'
    p=ROOT/'rankings'/slug;p.mkdir(parents=True,exist_ok=True);(p/'index.html').write_text(page(f'{title} — PowerPulseHQ',title,f'/rankings/{slug}/',body))

# Home: update server-rendered headline metrics and equipment costs for crawlers as well as JS users.
home=(ROOT/'index.html').read_text()
home=re.sub(r'<div class="starter">.*?</div>','' if d.get('live') else '<div class="starter">Starter snapshot: run <strong>Update PowerPulse data and deploy</strong> in GitHub Actions to load current monthly EIA data.</div>',home,count=1,flags=re.S)
home=re.sub(r'<span data-national-rate>.*?</span>',f'<span data-national-rate>{d["national_rate_cents_kwh"]:.2f}</span>',home)
home=re.sub(r'<span data-period>.*?</span>',f'<span data-period>{d["period"]}</span>',home)
for key in ('mom_pct','yoy_pct','five_year_pct'):
    v=d.get('national',{}).get(key); val=pct(v); css='flat' if v is None or v==0 else ('up' if v>0 else 'down')
    home=re.sub(fr'<strong data-{key} class="[^"]*">.*?</strong>',f'<strong data-{key} class="{css}">{val}</strong>',home)
srt=sorted(d['states'],key=lambda x:x['rate_cents_kwh'])
home=re.sub(r'<strong data-low>.*?</strong>',f'<strong data-low>{srt[0]["name"]} {srt[0]["rate_cents_kwh"]:.2f}¢</strong>',home)
home=re.sub(r'<strong data-high>.*?</strong>',f'<strong data-high>{srt[-1]["name"]} {srt[-1]["rate_cents_kwh"]:.2f}¢</strong>',home)
for dv in devices[:6]:
    annual=cost(d['national_rate_cents_kwh'],dv['annual_kwh'])
    pat=fr'(<a class="device-card" href="/cost-to-run/{re.escape(dv["slug"])}/">.*?<div class="device-cost">)\$[0-9,]+(<span class="tiny">/yr</span>)'
    home=re.sub(pat,fr'\g<1>${annual:,.0f}\g<2>',home,flags=re.S)
(ROOT/'index.html').write_text(home)

# Cost-to-run landing page: keep all national benchmark cards current.
landing=(ROOT/'cost-to-run/index.html').read_text()
for dv in devices:
    annual=cost(d['national_rate_cents_kwh'],dv['annual_kwh'])
    pat=fr'(<a class="device-card" href="/cost-to-run/{re.escape(dv["slug"])}/">.*?<div class="device-cost">)\$[0-9,]+(<span class="tiny">/year at starter U.S. rate</span>)'
    landing=re.sub(pat,fr'\g<1>${annual:,.0f}<span class="tiny">/year at latest U.S. rate</span>',landing,flags=re.S)
(ROOT/'cost-to-run/index.html').write_text(landing)

# Sitemap
urls=['/','/electricity-prices/','/rankings/','/rankings/cheapest/','/rankings/most-expensive/','/rankings/fastest-rising/','/rankings/five-year/','/cost-to-run/','/calculator/','/methodology/','/data-download/','/home-wellness-equipment/']
urls += [f'/states/{s["code"].lower()}/' for s in d['states']]
urls += [f'/cost-to-run/{dv["slug"]}/' for dv in devices]
(ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>https://powerpulsehq.com{u}</loc></url>\n' for u in urls)+'</urlset>\n')
print(f'Rebuilt {len(d["states"])} state pages, {len(devices)} equipment pages, rankings, CSVs and sitemap.')
