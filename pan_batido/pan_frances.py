#!python3
"""
This will be the api for the pan_europeo plugin
For developing comfort, right now the functions are pasted into pan_batido.py
When the api stabilizes, they'll be called from here
"""
import numpy as np


def min_max_scaling(data, nodata, invert=False):
    min_val = data[data != nodata].min()
    max_val = data[data != nodata].max()
    if max_val != min_val:
        ret_val = (data - min_val) / (max_val - min_val)
        if invert:
            return np.float32(1 - ret_val)
        return np.float32(ret_val)
    else:
        return np.zeros_like(data, dtype=np.float32)


def bi_piecewise_linear(data, nodata, a, b):
    ret_val = np.empty_like(data, dtype=np.float32)
    ret_val[data != nodata] = (data[data != nodata] - a) / (b - a)
    ret_val[data == nodata] = data[data == nodata]
    return np.float32(ret_val)

def get_raster_data(raster_path, extent, resolution=(1920,1080)):
    """
    Returns the data of the raster in the form of a numpy array
    """
    import gdal
    ds = gdal.Open(raster_path)
    if ds is None:
        raise ValueError("Could not open raster file")
    band1 = ds.GetRasterBand(1)
    # num_overviews = band1.GetOverviewCount()
    # calculate extent to xoff yoff
    srs = ds.GetProjection()
    geotransform = ds.GetGeoTransform()
    xoff = int((extent.xMinimum - geotransform[0]) / geotransform[1])
    yoff = int((extent.yMaximum - geotransform[3]) / geotransform[5])
    xsize = int((extent.xMaximum - extent.xMinimum) / geotransform[1])
    ysize = int((extent.yMinimum - extent.yMaximum) / geotransform[5])
    # print(xoff, yoff, xsize, ysize)
    buf_xsize = int(xsize * resolution[0] / xsize)
    buf_ysize = int(ysize * resolution[1] / ysize)
    ret_array = band1.ReadAsArray(xoff=xoff, yoff=yoff, xsize=xsize, ysize=ysize, buf_xsize=buf_xsize, buf_ysize=buf_ysize)
    # band1.ReadAsArray(xoff=0, yoff=0, xsize=None, ysize=None, buf_obj=None, buf_xsize=None, buf_ysize=None, buf_type=None, resample_alg=0, callback=None, callback_data=None, interleave='band', band_list=None)
    # return ds.GetRasterBand(1).ReadAsArray()
    return ret_array

def get_displayed_pixel_count(rlayer = iface.activeLayer(), canvas_extent = iface.mapCanvas().extent()):
    """
    Estimates the number of displayed pixels for a raster layer based on current extent and resolution.
  
    Args:
        raster_layer: QgsRaster layer object.
        canvas_extent : defaults to current iface.mapCanvas().extent()
  
    Returns:
        int: Estimated number of displayed pixels.
    """
    rlayer = iface.activeLayer()
    canvas_extent = iface.mapCanvas().extent()
    rinfo = {
            "width": rlayer.width(),
            "height": rlayer.height(),
            "extent": rlayer.extent(),
            "crs": rlayer.crs(),
            "cellsize_x": rlayer.rasterUnitsPerPixelX(),
            "cellsize_y": rlayer.rasterUnitsPerPixelY(),
            "bands": rlayer.bandCount(),
    }
  
    # Calculate the intersection between canvas extent and raster extent.
    intersection_extent = canvas_extent.intersect(rinfo ['extent'])
    # Check if there's any intersection.
    if intersection_extent.isNull():
        print('isnull')

    # v0 : won't with degree crs
    # intersection_extent.area() / rinfo['cellsize_x'] / rinfo['cellsize_y']
    # v1: Calculate the width and height of the intersection in raster coordinates.
    intersection_width = intersection_extent.xMaximum() - intersection_extent.xMinimum()
    intersection_height = intersection_extent.yMaximum() - intersection_extent.yMinimum()
  
    # Estimate the number of displayed pixels based on resolution and intersection size.
    estimated_pixels = int(intersection_width / rinfo['cellsize_x'] * intersection_height / rinfo['cellsize_y'])
  
    return estimated_pixels
  
# Example usage:
layer = iface.activeLayer()  # Assuming your raster layer is active

if layer is not None and layer.type() == LayerType.RasterLayer:
    displayed_pixels = get_displayed_pixel_count(layer, iface)
  print(f"Estimated displayed pixels: {displayed_pixels}")
else:
    print("No active raster layer found.")

