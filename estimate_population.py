"""Headless GRID3 population aggregation. See README.md for examples and assumptions."""
import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import requests
from exactextract import exact_extract
from shapely.geometry import box

BASE = 'https://data.worldpop.org/repo/wopr/NGA/population/v3.0/'
WARD_SERVICE = 'https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/GRID3_NGA_operational_wards_v3_0/FeatureServer/0'
WARD_ITEM = 'https://www.arcgis.com/home/item.html?id=45cd2ef592094d12aca43113a90a6054'

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def api(url, params):
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    j = r.json()
    if 'error' in j: raise ValueError(f"Service error: {j['error']}")
    return j

def fetch(url, path):
    path = Path(path)
    if path.exists(): return
    tmp = path.with_suffix(path.suffix+'.part')
    with requests.get(url, stream=True, timeout=(30,120)) as r:
        r.raise_for_status()
        with tmp.open('wb') as f:
            for chunk in r.iter_content(1024*1024): f.write(chunk)
    tmp.replace(path)

def download(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    archive = out/'NGA_population_v3_0_gridded.zip'
    fetch(BASE+archive.name, archive)
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            target = (out/name).resolve()
            if not target.is_relative_to(out.resolve()): raise ValueError('Unsafe archive path')
        z.extractall(out)
    raster=out/'NGA_population_v3_0_gridded.tif'
    if not raster.exists():
        matches=list(out.rglob(raster.name))
        if len(matches)!=1: raise ValueError('Could not identify population raster in download')
        matches[0].replace(raster)
    fetch(BASE+'NGA_population_v3_0_README.pdf',out/'NGA_population_v3_0_README.pdf')
    # Query IDs first, then retrieve batches: avoids the ArcGIS response-size limit.
    state = args.state.replace("'", "''")
    where = f"state = '{state}'"
    ids = api(WARD_SERVICE+'/query', {'f':'json','where':where,'returnIdsOnly':'true'}).get('objectIds') or []
    if not ids: raise ValueError(f'No v3 wards for {args.state}; v3 covers 24 states. Supply another boundary dataset for other states.')
    features=[]
    for i in range(0,len(ids),100):
        j=api(WARD_SERVICE+'/query',{'f':'geojson','objectIds':','.join(map(str,ids[i:i+100])),
              'outFields':'*','outSR':4326,'returnGeometry':'true'})
        if j.get('exceededTransferLimit'): raise ValueError('Boundary query truncated')
        features.extend(j['features'])
    if len(features)!=len(ids): raise ValueError('Incomplete boundary download')
    boundary=out/f'{args.state.lower().replace(" ","_")}_wards_v3.geojson'
    boundary.write_text(json.dumps({'type':'FeatureCollection','features':features}),encoding='utf-8')
    (out/'sources.json').write_text(json.dumps({'population_url':BASE+archive.name,
       'population_year':2025,'population_version':'3.0','boundary_item':WARD_ITEM,
       'boundary_version':'3.0','boundary_service':WARD_SERVICE,'state':args.state,
       'features':len(features),'retrieved_utc':datetime.now(timezone.utc).isoformat(),
       'boundary_sha256':digest(boundary),'archive_sha256':digest(archive)},indent=2),encoding='utf-8')
    print(f'Downloaded {len(features)} wards to {boundary}; population raster in {out}')

def read_boundaries(path, layer=None):
    g = gpd.read_file(path, **({'layer':layer} if layer else {}))
    if g.empty: raise ValueError('Empty boundary dataset')
    if g.crs is None: raise ValueError('Boundary CRS missing; assign its known CRS before use')
    return g

def field(g, explicit, choices):
    if explicit:
        if explicit not in g: raise ValueError(f'Field {explicit!r} missing; available: {list(g.columns)}')
        return explicit
    return next((c for c in choices if c in g),None)

def inspect(args):
    if args.boundaries:
        g=read_boundaries(args.boundaries,args.layer)
        print('CRS:',g.crs,'Features:',len(g),'Fields:',', '.join(g.columns))
        for choices in [('state','state_name'),('lga','lga_name'),('ward','ward_name')]:
            c=field(g,None,choices)
            if c: print(c,':',', '.join(sorted(g[c].dropna().astype(str).unique())))
    if args.raster:
        with rasterio.open(args.raster) as r:
            print('Raster:',r.shape,'CRS:',r.crs,'Bounds:',r.bounds,'NoData:',r.nodata,'Resolution:',r.res)

def estimate(args):
    out=Path(args.out)
    if out.exists() and any(out.iterdir()): raise ValueError('Output folder is not empty; choose a new folder to preserve previous runs')
    g=read_boundaries(args.boundaries,args.layer)
    sc=field(g,args.state_field,('state','state_name'))
    lc=field(g,args.lga_field,('lga','lga_name'))
    wc=field(g,args.ward_field,('ward','ward_name'))
    for selected,col,label in [(args.state,sc,'state'),(args.lga,lc,'LGA'),(args.ward,wc,'ward')]:
        if selected:
            if not col: raise ValueError(f'No {label} field; supply --{label.lower()}-field')
            available=set(g[col].astype(str).str.strip().str.casefold())
            missing=[v for v in selected if v.strip().casefold() not in available]
            if missing: raise ValueError(f'Unknown {label} names: {missing}. Use inspect to see available names.')
            g=g[g[col].astype(str).str.strip().str.casefold().isin([v.strip().casefold() for v in selected])]
    if g.empty: raise ValueError('No matching boundaries. Use inspect to see available names.')
    if g.geometry.isna().any() or g.geometry.is_empty.any(): raise ValueError('Null or empty geometries')
    if not g.geometry.geom_type.isin(['Polygon','MultiPolygon']).all(): raise ValueError('Polygon boundaries required')
    if not g.geometry.is_valid.all(): raise ValueError('Invalid boundary geometry; repair and inspect before estimating')
    # Keep names/codes, exclude legacy statistics to avoid confusion with new results.
    keep=[c for c in g.columns if c!='geometry' and not c.startswith('_') and c not in ['population','valid_cell_equivalents']]
    g=g[keep+['geometry']].copy()
    if args.level=='ward':
        if not wc: raise ValueError('Ward field required for --level ward')
        keys=[c for c in [sc,lc,wc] if c]
        g=g[keys+['geometry']].dissolve(by=keys,as_index=False)
    elif args.level=='lga':
        if not lc: raise ValueError('LGA field required for --level lga')
        keys=[c for c in [sc,lc] if c]
        g=g[keys+['geometry']].dissolve(by=keys,as_index=False)
    else:
        g=gpd.GeoDataFrame({'area_name':[args.name or 'Selected area'],'geometry':[g.geometry.union_all()]},crs=g.crs)
    g=g.reset_index(drop=True)
    if not g.geometry.is_valid.all(): raise ValueError('Invalid geometry after dissolving boundaries')
    # Evaluate overlaps in an equal-area CRS; overlaps would double count population.
    area=g.to_crs(6933)
    union=area.geometry.union_all()
    overlap=float(area.geometry.area.sum()-union.area)
    if overlap>max(1.0,union.area*1e-8): raise ValueError(f'Overlapping output zones ({overlap:.1f} m2); resolve before summing')
    with rasterio.open(args.raster) as r:
        if not r.crs: raise ValueError('Raster CRS missing')
        if r.count!=1: raise ValueError('Single-band people-per-cell population raster required')
        if r.transform.b or r.transform.d: raise ValueError('Rotated raster unsupported; supply an unrotated grid')
        zones=g.to_crs(r.crs)
        extent=box(*r.bounds)
        if any(not extent.buffer(max(abs(r.res[0]),abs(r.res[1]))*1e-7).covers(x) for x in zones.geometry):
            raise ValueError('Selected boundary extends outside raster extent; use a larger/unclipped raster')
        stats=exact_extract(r,zones,['sum','count'],output='pandas')
        if not np.isfinite(stats['sum']).all() or (stats['sum']<0).any(): raise ValueError('Invalid population values')
        if (stats['count']==0).any(): raise ValueError('A zone contains no valid raster cells; investigate NoData before reporting zero population')
        total_zone=gpd.GeoDataFrame(geometry=[zones.geometry.union_all()],crs=r.crs)
        total=float(exact_extract(r,total_zone,['sum'],output='pandas')['sum'].iloc[0])
        raster_meta={'crs':str(r.crs),'width':r.width,'height':r.height,'nodata':r.nodata,'transform':list(r.transform)}
    g['population']=stats['sum'].to_numpy()
    g['valid_cell_equivalents']=stats['count'].to_numpy()
    summed=float(g.population.sum())
    if not np.isclose(summed,total,rtol=1e-6,atol=.01): raise ValueError('Zone totals disagree with union total')
    out.mkdir(parents=True,exist_ok=True)
    g.drop(columns='geometry').to_csv(out/'population.csv',index=False)
    g.to_crs(4326).to_file(out/'population.geojson',driver='GeoJSON')
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'command':sys.argv,
       'raster_path':str(Path(args.raster).resolve()),'raster_sha256':digest(args.raster),
       'boundary_path':str(Path(args.boundaries).resolve()),'boundary_sha256':digest(args.boundaries),
       'population_year':args.year,'population_version':args.population_version,
       'boundary_version':args.boundary_version,'level':args.level,'zone_count':len(g),
       'population_total':total,'sum_of_zones':summed,'overlap_m2':overlap,
       'method':'sum of people-per-cell multiplied by fractional cell coverage',
       'assumptions':['Uniform population within a partially intersected raster cell',
          'NoData excluded; consult the specific release statement for its meaning',
          'Modelled estimates, not a census; no uncertainty interval inferred from cell means',
          'LGA totals dissolved from supplied wards reflect those ward boundaries'],
       'raster':raster_meta}
    (out/'run.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    if args.plot:
        import os
        os.environ.setdefault('MPLCONFIGDIR',str((out/'plot_cache').resolve()))
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(9,8))
        g.to_crs(32631).plot(column='population',legend=True,edgecolor='white',linewidth=.4,ax=ax)
        ax.set_title(f'Estimated population by {args.level}'+(f' ({args.year})' if args.year else ''))
        ax.set_axis_off();fig.tight_layout();fig.savefig(out/'population_map.png',dpi=180);plt.close(fig)
    print(f'{len(g)} zones; estimated total {total:,.2f} people. Results: {out.resolve()}')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    d=sub.add_parser('download',help='Download Nigeria 2025 population and one state of v3 wards')
    d.add_argument('--state',default='Ogun');d.add_argument('--out',default='data');d.set_defaults(func=download)
    i=sub.add_parser('inspect',help='Show raster metadata and boundary field names')
    i.add_argument('--boundaries');i.add_argument('--raster');i.add_argument('--layer');i.set_defaults(func=inspect)
    e=sub.add_parser('estimate',help='Calculate fractional-coverage population totals')
    e.add_argument('--raster',required=True);e.add_argument('--boundaries',required=True);e.add_argument('--layer')
    for name in ['state','lga','ward']:
        e.add_argument('--'+name,action='append',help='Exact name; repeat to select multiple areas')
        e.add_argument('--'+name+'-field')
    e.add_argument('--level',choices=['ward','lga','area'],default='ward')
    e.add_argument('--name',help='Label for a custom area or union')
    e.add_argument('--year',type=int);e.add_argument('--population-version');e.add_argument('--boundary-version')
    e.add_argument('--out',required=True);e.add_argument('--plot',action='store_true');e.set_defaults(func=estimate)
    args=p.parse_args()
    try: args.func(args)
    except (ValueError,OSError,requests.RequestException) as ex:
        p.exit(2,f'Error: {ex}\n')

if __name__=='__main__': main()
