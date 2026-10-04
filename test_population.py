"""Known-answer integration tests; run with python -m unittest -v."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

SCRIPT=Path(__file__).with_name('estimate_population.py')
class PopulationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.raster=self.root/'pop.tif'
        with rasterio.open(self.raster,'w',driver='GTiff',height=1,width=2,count=1,
               dtype='float32',crs='EPSG:4326',transform=from_origin(0,1,1,1),nodata=-9999) as r:
            r.write(np.array([[100,200]],dtype='float32'),1)
    def tearDown(self): self.tmp.cleanup()
    def run_case(self,geometries,expected=None):
        b=self.root/'wards.geojson'
        gpd.GeoDataFrame({'state':['Test']*len(geometries),'lga':['LGA']*len(geometries),
            'ward':[str(i) for i in range(len(geometries))],'geometry':geometries},crs=4326).to_file(b,driver='GeoJSON')
        result=subprocess.run([sys.executable,str(SCRIPT),'estimate','--raster',str(self.raster),
            '--boundaries',str(b),'--out',str(self.root/'out')],capture_output=True,text=True)
        if expected is None: self.assertNotEqual(result.returncode,0,result.stdout)
        else:
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads((self.root/'out'/'run.json').read_text())
            self.assertAlmostEqual(data['population_total'],expected,places=4)
    def test_fractional_cells(self): self.run_case([box(.5,0,1.5,1)],150)
    def test_adjacent_conserve_total(self): self.run_case([box(0,0,1,1),box(1,0,2,1)],300)
    def test_overlaps_rejected(self): self.run_case([box(0,0,1.5,1),box(1,0,2,1)])
    def test_outside_raster_rejected(self): self.run_case([box(0,0,3,1)])
    def test_nodata_rejected(self):
        with rasterio.open(self.raster,'r+') as r: r.write(np.array([[-9999,-9999]],dtype='float32'),1)
        self.run_case([box(0,0,1,1)])

if __name__=='__main__': unittest.main()
