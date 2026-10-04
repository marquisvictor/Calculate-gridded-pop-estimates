"""Portable convenience command using the downloaded GRID3 v3 datasets."""
import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',default='Ogun')
    p.add_argument('--lga',action='append',help='Repeat for multiple LGAs; defaults to both Abeokuta LGAs in Ogun')
    p.add_argument('--ward',action='append',default=[])
    p.add_argument('--level',choices=['ward','lga','area'],default='ward')
    p.add_argument('--name',help='Label for --level area')
    p.add_argument('--out',type=Path,help='New output folder; defaults to a timestamped results folder')
    p.add_argument('--plot',action='store_true')
    args=p.parse_args()
    if not args.lga and args.state.strip().casefold()!='ogun':
        p.error('For a state other than Ogun, supply at least one --lga. To process a whole state, use estimate_population.py directly.')
    lgas=args.lga or ['Abeokuta North','Abeokuta South']
    data=ROOT/'data'
    raster=data/'NGA_population_v3_0_gridded.tif'
    boundaries=data/(args.state.lower().replace(' ','_')+'_wards_v3.geojson')
    script=str(ROOT/'estimate_population.py')
    if not raster.exists() or not boundaries.exists():
        print('Downloading population data and state boundaries...',flush=True)
        subprocess.run([sys.executable,script,'download','--state',args.state,'--out',str(data)],check=True)
    out=args.out or ROOT/'results'/datetime.now(timezone.utc).strftime('run_%Y%m%d_%H%M%S_%f')
    cmd=[sys.executable,script,'estimate','--raster',str(raster),'--boundaries',str(boundaries),
         '--state',args.state,'--level',args.level,'--year','2025','--population-version','3.0',
         '--boundary-version','3.0','--out',str(out)]
    for lga in lgas: cmd.extend(['--lga',lga])
    for ward in args.ward: cmd.extend(['--ward',ward])
    if args.plot: cmd.append('--plot')
    if args.name: cmd.extend(['--name',args.name])
    try: subprocess.run(cmd,check=True)
    except subprocess.CalledProcessError as e: return e.returncode
    return 0

if __name__=='__main__': sys.exit(main())
