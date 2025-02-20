# Panetteria Panettone

Is a processing algorithms plugin, to wrap the wrappers of `gdal_calc.py` scripts, using GdalAlgorithm instead of QgsProcessingAlgorithm. All because QgsTask don't set the visual progress right!

### Based on

    /usr/share/qgis/python/plugins/processing/algs/gdal/gdalcalc.py
    /usr/lib/python3/dist-packages/osgeo_utils/gdal_calc.py

### Implements the following processing algorithms

    panettone_gdal_calc_norm.py  "panettone:normalizator"
    panettone_gdal_calc_sum.py   "panettone:weightedsummator"

### That wraps the following scripts

    gdal_calc_norm
    gdal_calc_sum

### Corresponding to the modules

    fire2a.raster.gdal_calc_norm
    fire2a.raster.gdal_calc_sum

### Requires (TODO remove requirement)

    pip install fire2a-lib
