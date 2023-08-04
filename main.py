import json
import os
import subprocess
import sys

from osgeo import gdal, ogr
from asf_tools import dem
from hyp3lib.rtc2color import rtc2color
import sarsen


gdal.UseExceptions()


def get_geometry_from_kml(kml_file: str) -> ogr.Geometry:
    cmd = ['ogr2ogr', '-wrapdateline', '-datelineoffset', '20', '-f', 'GeoJSON', '-mapfieldtype', 'DateTime=String',
           '/vsistdout', kml_file]
    geojson_str = subprocess.run(cmd, stdout=subprocess.PIPE, check=True).stdout
    geometry = json.loads(geojson_str)['features'][0]['geometry']
    return ogr.CreateGeometryFromJson(json.dumps(geometry))


def create_browse(grd_safe_directory: str, outfile: str = 'rgb.tif'):
    kml_file = os.path.join(grd_safe_directory, 'preview/map-overlay.kml')
    dem_vrt = 'dem.vrt'
    dem_geotiff = 'dem.tif'

    geometry = get_geometry_from_kml(kml_file)
    dem.prepare_dem_vrt(dem_vrt, geometry)

    envelope = geometry.GetEnvelope()
    proj_win = [envelope[0], envelope[3], envelope[1], envelope[2]]
    gdal.Translate(destName=dem_geotiff, srcDS=dem_vrt, projWin=proj_win, width=2048)

    for polarization in ['VV', 'VH']:
        product = sarsen.Sentinel1SarProduct(grd_safe_directory, measurement_group=f'IW/{polarization}')
        sarsen.terrain_correction(product=product, dem_urlpath=dem_geotiff, output_urlpath=f'{polarization}.tif')

    rtc2color(copol_tif='VV.tif', crosspol_tif='VH.tif', threshold=-24, out_tif=outfile)


if __name__ == '__main__':
    create_browse(sys.argv[1])
