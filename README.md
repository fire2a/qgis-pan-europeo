# Pan European Raster Algorithms (PERA) project

This repository contains the code for the Pan European Raster Algo (PERA) project. The PERA project is a collaboration between PEACH (Protection of Environment and Cultural Heritage) and the FIG(Fire Investigacion and Goverance). The project aims to develop a set of algorithms to process raster data in a distributed computing environment. The algorithms are designed to work with large-scale raster datasets, such as those produced by Technosylva and ERICO.

## How to?

Put `pan_batido` directory in you qgis plugin folder

## Current status
### Features:
#### 1. Reads all layers available and draws a dialog with:

A. Each row belonging to a layer, containing
- layer name 
- weight attributes (checkbox for dis/en-abling, spinbox & slider in 0,100 range) 
- utility function configuration x2:
-- Min-Max scaling, with a invert checkbox
-- Bi-Piecewise-Linear, with spinboxes&sliders for its two 2 points (where the range are the raster min-max values)
  
B. A Toolbox with standard buttons (Ok, Cancel, Reset)

#### 2. The user can:
- Press Cancel nothing is done
- Press Reset to destory current read layers and configuration options
- Press Ok a new layer is calculated:

#### 3. The new layer is calculated as follows:
- The current mapCanvas is selected as extent for the new layer
- Raster data is gathered up to default (1920x1080 pixels of 100m side) resolution, else is nearest neighbor down-sampled
- The selected weight attributes are multiplied by the utility function

### TODO Roadmap:
1. Target resolution selector (3 spinboxes with the target resolution of the new raster width, height, pixel size)
2. Resampling method combobox selector for each layer
3. DataType target selector float32, uint16 o uint 8
4. Add and use raster overviews `gdaladdo`

### Development notes:
* dialog_base.ui is dummy
* pan_frances.py is not used right now but will allocate all methods from pan_batido.py except the plugin class itself
* an installation of fire2-lib will be required, eventually moving common methods outside of pan_batido.py
```
pip install git+https://github.com/fire2a/fire2a-lib.git
or 
git clone git@github.com:fire2a/fire2a-lib.git
cd fire2a-lib
pip install -e .
```

# Dev Notes References

    nodata = band.GetNoDataValue()
    rasterArray = np.ma.masked_equal(rasterArray, nodata)
    raster = None
    band = None

https://gdal.org/api/python/raster_api.html#osgeo.gdal.Band.ReadAsArray
    
    resample_alg (int, default = gdal.GRIORA_NearestNeighbour.) -- Specifies the resampling algorithm to use when the size of the read window and the buffer are not equal.

    [ins] In [2]: gdal.GRIORA_Average, gdal.GRIORA_Bilinear, gdal.GRIORA_Cubic, gdal.GRIORA_CubicSpline, gdal.GRIORA_Gauss, gdal.GRIORA_Lanczos, gdal.GRIORA_Mode, gdal.GRIORA_NearestNeighbour, gdal.GRIO
    Out[2]: (5, 1, 2, 3, 7, 4, 6, 0, 14)

        Nearest Neighbor (gdal.GRIORA_NearestNeighbour):
        This is the default and fastest algorithm.
        It assigns the value of the closest pixel in the original raster to the corresponding pixel in the output array.
        This method can introduce sharp edges and blockiness in the resampled image.

    Bilinear (gdal.GRIORA_Bilinear):
        This method considers the four nearest neighboring pixels in the original raster.
        It calculates a weighted average of their values based on their distance to the new pixel location in the output array.
        Bilinear interpolation produces smoother results compared to nearest neighbor but may introduce some blurring.

    Cubic (gdal.GRIORA_Cubic):
        This method involves a 4x4 neighborhood of pixels in the original raster.
        It uses a polynomial function to interpolate a new value for the output pixel based on the values of surrounding pixels.
        Cubic interpolation provides smoother results than bilinear but is computationally more expensive.

    Cubic Spline (gdal.GRIORA_CubicSpline):
        This method uses cubic spline interpolation, which is a more advanced technique compared to regular cubic interpolation.
        It offers smoother results but is even more computationally intensive.

    Gauss (gdal.GRIORA_Gauss):
        This method utilizes a Gaussian distribution to weight the values of neighboring pixels in the original raster.
        It can be useful for datasets with continuous variation but is less common than other resampling methods.

    Lanczos (gdal.GRIORA_Lanczos):
        This method employs a Lanczos filter for interpolation, known for its good preservation of high-frequency details.
        It can be computationally expensive but may be preferred for resampling imagery with sharp edges or fine details.

    Mode (gdal.GRIORA_Mode):
        This method assigns the value that appears most frequently among the neighboring pixels in the original raster to the output pixel.
        It can be useful for categorical data but may not be suitable for continuous datasets.

    Average (gdal.GRIORA_Average):
        This method calculates the average value of all neighboring pixels in the original raster and assigns it to the output pixel.
        It can be useful for smoothing noisy data but may blur sharp features.

https://gdal.org/programs/gdaladdo.html

    gdaladdo [--help] [--help-general]
             [-r {nearest|average|rms|gauss|cubic|cubicspline|lanczos|average_mp|average_magphase|mode}]
             [-ro] [-clean] [-q] [-oo <NAME>=<VALUE>]... [-minsize <val>]
             [--partial-refresh-from-source-timestamp]
             [--partial-refresh-from-projwin <ulx> <uly> <lrx> <lry>]
             [--partial-refresh-from-source-extent <filename1>[,<filenameN>]...]
             <filename> [<levels>]...
