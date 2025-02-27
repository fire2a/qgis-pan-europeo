# Easy Raster Summarization tool for QGIS

## Usage

1. Prepare rasters: Match all raster CRS and extents (squared or projected please)
2. Put them on a QGIS project (same CRS)
3. Launch the plugin dialog
4. For each raster:
    1. Select the relative weight for the final summation
    2. Select the utility function (some require moving sliders for configuration)
5. Set the work area, by selecting polygon(s) or use the extent selector
6. Ok (a cancellable task will run in the background)

## Installation
Install the plugin from the QGIS plugin repository

- Dialog plugin : ![Pan Batido](https://plugins.qgis.org/plugins/pan_batido/)

- TODO: publish the GdalAlgorithmProcessing plugin acting as backend: ![Panettone](panettone/README.md)

### Development
Clone, symlink, restart QGIS and enable the plugin
```
git clone
cd ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins
ln -s /path/to/this/repo/pan_batido .
ln -s /path/to/this/repo/panettone .
```

#### TODO:
- [ ] bug on view update, recalculating min max based on the selected feature
- [ ] Ouput with zonal statistics
- [ ] packaging
- [ ] Data server ...

#### Changelog
1. Target resolution: scrapped!
2. Resampling method: scrapped!
3. DataType target selector: ok!
4. backend changed to gdalcal 

#### References

    nodata = band.GetNoDataValue()
    rasterArray = np.ma.masked_equal(rasterArray, nodata)
    raster = None
    band = None

    min = band.GetMinimum()
    max = band.GetMaximum()
    if not min or not max:
        (min,max) = band.ComputeRasterMinMax(True)

https://gdal.org/api/python/raster_api.html#osgeo.gdal.Band.ReadAsArray
    
    resample_alg (int, default = gdal.GRIORA_NearestNeighbour.) -- Specifies the resampling algorithm to use when the size of the read window and the buffer are not equal.

    [ins] In [5]: gdal.GRIORA_NearestNeighbour, gdal.GRIORA_Bilinear, gdal.GRIORA_Cubic, gdal.GRIORA_CubicSpline, gdal.GRIORA_Lanczos, gdal.GRIORA_Average, gdal.GRIORA_Mode, gdal.GRIORA_Gauss
    Out[5]: (0, 1, 2, 3, 4, 5, 6, 7)

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

    Lanczos (gdal.GRIORA_Lanczos):
        This method employs a Lanczos filter for interpolation, known for its good preservation of high-frequency details.
        It can be computationally expensive but may be preferred for resampling imagery with sharp edges or fine details.

    Average (gdal.GRIORA_Average):
        This method calculates the average value of all neighboring pixels in the original raster and assigns it to the output pixel.
        It can be useful for smoothing noisy data but may blur sharp features.

    Mode (gdal.GRIORA_Mode):
        This method assigns the value that appears most frequently among the neighboring pixels in the original raster to the output pixel.
        It can be useful for categorical data but may not be suitable for continuous datasets.

    Gauss (gdal.GRIORA_Gauss):
        This method utilizes a Gaussian distribution to weight the values of neighboring pixels in the original raster.
        It can be useful for datasets with continuous variation but is less common than other resampling methods.


https://gdal.org/programs/gdaladdo.html

    gdaladdo [--help] [--help-general]
             [-r {nearest|average|rms|gauss|cubic|cubicspline|lanczos|average_mp|average_magphase|mode}]
             [-ro] [-clean] [-q] [-oo <NAME>=<VALUE>]... [-minsize <val>]
             [--partial-refresh-from-source-timestamp]
             [--partial-refresh-from-projwin <ulx> <uly> <lrx> <lry>]
             [--partial-refresh-from-source-extent <filename1>[,<filenameN>]...]
             <filename> [<levels>]...
