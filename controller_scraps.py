import tempfile
from pathlib import Path
from tempfile import mktemp

import numpy as np
from fire2a.raster import extent_to_projwin, gdal_calc_norm, gdal_calc_sum, read_raster
from osgeo import gdal
from qgis.core import (Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsMapLayer, QgsProject,
                       QgsRasterLayer, QgsRectangle)

from .config import UTILITY_FUNCTIONS, qprint


class Marraqueta:
    def __init__(self, iface):
        self.common_extent = None
        self.map_extent = None
        self.selected_extent = None

    def handle_extent_change(self, *args, **kwargs):
        # if not self.iface.mapCanvas().isDrawing():
        #     self.map_extent = self.iface.mapCanvas().extent()
        #     qprint(f"extent is {self.map_extent.asWktCoordinates()} {args=}, {kwargs=}")
        self.map_extent = self.iface.mapCanvas().extent()
        qprint(f"{self.map_extent.asWktCoordinates()=}")

    def handle_selection_changed(self, layer):
        # print(f"{self.selected_layer=}")
        if not layer:
            self.selected_extent = None
            return
        if layer.selectedFeaturesCount() == 0:
            self.selected_extent = None
            return
        elif layer.selectedFeaturesCount() == 1:
            self.selected_extent = self.selected_layer.selectedFeatures()[0].geometry().boundingBox()
        else:
            min_x = float("inf")
            max_x = -float("inf")
            min_y = float("inf")
            max_y = -float("inf")

            for feat in layer.selectedFeatures():
                bbox = feat.geometry().boundingBox()
                min_x = min(bbox.xMinimum(), min_x)
                max_x = max(bbox.xMaximum(), max_x)
                min_y = min(bbox.yMinimum(), min_y)
                max_y = max(bbox.yMaximum(), max_y)

            self.selected_extent = QgsRectangle(min_x, min_y, max_x, max_y)

        # bbox = self.selected_extent
        # vl = QgsVectorLayer("Polygon?crs=epsg:3035", "bbox", "memory")
        # pr = vl.dataProvider()
        # f = QgsFeature()
        # f.setGeometry(QgsGeometry.fromRect(bbox))
        # pr.addFeatures([f])
        # vl.updateExtents()
        # QgsProject.instance().addMapLayer(vl)
        qprint(f"{self.selected_extent.asWktCoordinates()=}")

    def run(self):
        """Run method that performs all the real work"""
        # qprint("current layers", self.iface.mapCanvas().layers())

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            if len(self.iface.mapCanvas().layers()) == 0:
                qprint("No layers loaded. Not loading the dialog!", level=Qgis.Critical)
                # display a message in system toolbar
                self.iface.messageBar().pushMessage(
                    "No layers loaded",
                    "Please load some raster layers before launching the PAN-BATIDO plugin",
                    level=Qgis.Critical,
                    duration=5,
                )
                return
            self.first_start = False
            self.iface.mapCanvas().extentsChanged.connect(self.handle_extent_change)
            self.iface.mapCanvas().selectionChanged.connect(self.handle_selection_changed)
            self.dlg = MarraquetaDialog()
            self.lyr_data = []
            for dlg_row in self.dlg.rows:
                # layer = self.iface.mapCanvas().layer(dlg_row["layer_id"])
                layer = QgsProject.instance().layerTreeRoot().findLayer(dlg_row["layer_id"]).layer()
                _, info = read_raster(layer.publicSource(), data=False, info=True)
                self.lyr_data += [
                    {"layer": layer, "info": info, "name": layer.name(), "extent": layer.extent(), "crs": layer.crs()}
                ]
                rimin, rimax = int(np.floor(info["Minimum"])), int(np.ceil(info["Maximum"]))
                xsize, ysize = info["RasterXSize"], info["RasterYSize"]
                qprint(
                    f"layer name: {layer.name()}, value range ({rimin},{rimax}), size w: {xsize}, h:{ysize}, authid: {layer.crs().authid()},  id: {dlg_row['layer_id']}"
                )
                # set ranges for utility functions
                for letters in ["a", "b", "e", "g"]:
                    for wid in ["spinbox", "slider"]:
                        name = f"{letters}_{wid}"
                        dlg_row[name].setRange(rimin, rimax)
            # qprint(f"{self.lyr_data=}")
            self.common_extent = projected_extent(self.lyr_data[0]["extent"], self.lyr_data[0]["crs"])
            # qprint(f"0 {self.common_extent=}")
            # cc = 0
            for lyr in self.lyr_data[1:]:
                self.common_extent = self.common_extent.intersect(projected_extent(lyr["extent"], lyr["crs"]))
                # qprint(f"{cc} {lyr['extent']=}, {self.common_extent=}")
                # cc += 1
            if self.common_extent.isEmpty():
                qprint("No common extent between raster layers, aborting start", level=Qgis.Critical)
                self.iface.messageBar().pushMessage(
                    "Overlap between rasters is empty!",
                    "Please make sure all rasters intersect PAN-BATIDO plugin and restart it",
                    level=Qgis.Critical,
                    duration=5,
                )
                return

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # qprint(f"{result=} {self.dlg.DialogCode()=}")
        # See if OK was pressed
        if result == 1:
            self.dlg.rescale_weights()

            # extent calculation
            # polygon selected?
            if lyrs_w_selection := [
                lyr
                for lyr in QgsProject.instance().mapLayers().values()
                if lyr and lyr.type() == QgsMapLayer.VectorLayer and lyr.selectedFeatureCount() == 1
            ]:
                if len(lyrs_w_selection) > 1:
                    qprint("Warning: more than one layer with one selected feature, using the first one")
                lyrs_w_selection = lyrs_w_selection[0]
                feat_bbox = lyrs_w_selection.selectedFeatures()[0].geometry().boundingBox()
                extent = self.common_extent.intersect(projected_extent(feat_bbox, lyrs_w_selection.crs()))
                if extent.isEmpty():
                    qprint("No common extent between selected polygon and rasters", level=Qgis.Critical)
                    self.iface.messageBar().pushMessage(
                        "No overlap with area of study",
                        "Please select make sure there's common ground",
                        level=Qgis.Critical,
                        duration=3,
                    )
                    return
            # visible extent
            else:
                extent = self.common_extent.intersect(self.iface.mapCanvas().extent())
                qprint(f"No feature selected using from visible {extent=}")
            # qprint(f"{extent.area()=}")

            # TODO variable datatypes
            data_type = self.dlg.data_type.currentText()

            did_any = False
            log_instance_params = []
            outfiles = []
            weights = []
            for dlg_row in self.dlg.rows:
                lyr = self.lyr_data[dlg_row["i"]]
                log_row = {
                    "name": lyr["name"],
                    "enabled": dlg_row["weight_checkbox"].isChecked(),
                }
                if dlg_row["weight_checkbox"].isChecked() and dlg_row["weight_spinbox"].value() != 0:
                    log_row.update(
                        {
                            "weight": dlg_row["weight_spinbox"].value(),
                            "utility function": dlg_row["ufunc_dropdown"].currentText(),
                            "resample method": dlg_row["resample_dropdown"].currentText(),
                        }
                    )
                    weight = dlg_row["weight_spinbox"].value()
                    lyr_nodata = lyr["info"]["NoDataValue"]
                    ufdci = dlg_row["ufunc_dropdown"].currentIndex()
                    infile = lyr["layer"].publicSource()
                    method = UTILITY_FUNCTIONS[ufdci]["name"]
                    qprint(f"{ufdci=} {method=}", level=Qgis.Info)
                    nodata = lyr_nodata
                    projwin = extent_to_projwin(extent)
                    params = []
                    match method:
                        case "minmax" | "maxmin":
                            did_any = True
                        case "bipiecewiselinear":
                            a = dlg_row["a_spinbox"].value()
                            b = dlg_row["b_spinbox"].value()
                            log_row["min"] = a
                            log_row["max"] = b
                            if a != b:
                                params = [a, b]
                                did_any = True
                        case "bipiecewiselinear_percent":
                            c = dlg_row["c_spinbox"].value()
                            d = dlg_row["d_spinbox"].value()
                            log_row["min"] = c
                            log_row["max"] = d
                            if c != d:
                                params = [c, d]
                                did_any = True
                        case "stepup":
                            e = dlg_row["e_spinbox"].value()
                            log_row["threshold"] = e
                            params = [e]
                            did_any = True
                        case "stepup_percent":
                            f = dlg_row["f_spinbox"].value()
                            log_row["threshold"] = f
                            params = [f]
                            did_any = True
                        case "stepdown":
                            g = dlg_row["g_spinbox"].value()
                            log_row["threshold"] = g
                            params = [g]
                            did_any = True
                        case "stepdown_percent":
                            h = dlg_row["h_spinbox"].value()
                            log_row["threshold"] = h
                            params = [h]
                            did_any = True
                        case _:
                            raise ValueError(f"Utility function at index:{ufdci} not implemented")

                    params_str = "_" + "_".join(map(str, params)) + "_" if params else "_"
                    outfile = tempfile.mktemp(
                        prefix=Path(lyr["layer"].publicSource()).stem + "_" + method + params_str,
                        suffix=".tif",
                    )
                    cmd = [
                        "-i",
                        infile,
                        "-o",
                        outfile,
                        "-m",
                        method,
                        "-p",
                        *map(str, projwin),
                        "-n",
                        str(nodata),
                        "--",
                        *(map(str, params) if params else ""),
                    ]
                    print(cmd)
                    if gdal_calc_norm.main(cmd) != 0:
                        qprint(f"Error processing {lyr['name']}", level=Qgis.Critical)
                        return
                    outfiles += [outfile]
                    weights += [weight / 100]

                    log_instance_params += [log_row]

            if not did_any:
                qprint("Nothing to do, all layers unselected or 0 weight")
                return

            qprint(outfiles, level=Qgis.Info)

            afile = mktemp(suffix=".tif")
            cmd = ["-o", afile, "-w", *map(str, weights), "-p", *map(str, projwin), "-n", str(-9999), "--", *outfiles]
            print(cmd)
            if gdal_calc_sum.main(cmd) != 0:
                qprint("Error processing final sum", level=Qgis.Critical)
                return

            qprint(
                f"Created {afile=}, by combining:",
                level=Qgis.Success,
            )
            # add the raster layer to the canvas
            layer = self.iface.addRasterLayer(afile, Path(afile).stem)
            if data_type not in ["Byte(0-255)", "UInt16(0-65535)"]:
                qgis_paint(layer)

            log_instance_params = sorted(log_instance_params, key=lambda x: x["enabled"])
            for itm in log_instance_params:
                if not itm.get("enabled", False):
                    qprint(f"  {itm}", level=Qgis.Warning)
                    continue
                qprint(f"  {itm}", level=Qgis.Success)


def get_colormap(num_colors: int, colormap: str = "turbo") -> list:
    from matplotlib import colormaps
    from matplotlib.colors import LinearSegmentedColormap, ListedColormap
    from numpy import linspace

    cm = colormaps.get(colormap)
    if isinstance(cm, LinearSegmentedColormap):
        colors = cm(linspace(0, 1, num_colors))
    elif isinstance(cm, ListedColormap):
        colors = cm.resampled(num_colors).colors
    return (colors * 255).astype(int)


def band_paint(band: gdal.Band) -> None:
    """Paints a gdal raster using band.SetRasterColorTable, only works for Byte and UInt16 bands
    Args:
        band (gdal.Band): band to paint
        colormap (str): name of the colormap to use
    """
    if band.DataType == gdal.GDT_Byte:
        # byte 2**8 = 256
        num_colors = 256
    elif band.DataType == gdal.GDT_UInt16:
        # uint16 2**16 = 65,536
        num_colors = 65536
    else:
        return

    color_table = gdal.ColorTable()
    colors = get_colormap(num_colors)
    for i, color in enumerate(colors):
        color_table.SetColorEntry(i, tuple(color))
    band.SetRasterColorTable(color_table)


def qgis_paint(layer: QgsRasterLayer):
    from PyQt5.QtGui import QColor
    from qgis.core import QgsColorRampShader, QgsRasterShader, QgsSingleBandPseudoColorRenderer

    num_colors = 10
    colors = get_colormap(num_colors)
    fcn = QgsColorRampShader(minimumValue=0, maximumValue=1)
    fcn.setColorRampType(QgsColorRampShader.Interpolated)
    fcn.setColorRampItemList([QgsColorRampShader.ColorRampItem(0.1 * i, QColor(*clr)) for i, clr in enumerate(colors)])
    shader = QgsRasterShader()
    shader.setRasterShaderFunction(fcn)

    band = layer.bandCount()  # Assuming you want to use the last band
    renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), band, shader)
    layer.setRenderer(renderer)

    # Trigger a repaint for the layer
    layer.triggerRepaint()


def get_extent_size(extent: QgsRectangle):
    """Returns the width and height of the current displayed extent in meters"""
    # Create a CRS for meters (for example, WGS 84 / Pseudo-Mercator)
    crs_meters = QgsCoordinateReferenceSystem("EPSG:3857")

    # Get the current CRS
    crs_current = QgsProject.instance().crs()

    # Create a coordinate transform
    transform = QgsCoordinateTransform(crs_current, crs_meters, QgsProject.instance())

    # Transform the extent
    extent_meters = transform.transformBoundingBox(extent)

    # Get the width and height
    width = extent_meters.width()
    height = extent_meters.height()
    qprint(f"get_extent_size  {width=}, {height=}")
    return width, height


def projected_extent(
    extent: QgsRectangle,
    crs_from: QgsCoordinateReferenceSystem,
    crs_to: QgsCoordinateReferenceSystem = QgsProject.instance().crs(),
):
    return QgsCoordinateTransform(crs_from, crs_to, QgsProject.instance()).transformBoundingBox(extent)


def resolution_filter(extent: QgsRectangle, resolution=(1920, 1080), pixel_size=100):
    """Returns a resolution that is at most the input resolution, else returns a smaller one."""
    extent_with, extent_height = get_extent_size(extent)
    extent_xpx = int(extent_with / pixel_size)
    extent_ypx = int(extent_height / pixel_size)
    resx = resolution[0] if extent_xpx > resolution[0] else extent_xpx
    resy = resolution[1] if extent_ypx > resolution[1] else extent_ypx
    qprint(f"resolution_filter {resx=}, {resy=}")
    return resx, resy


def current_displayed_pixels(iface):
    extent = iface.mapCanvas().extent()
    layer = iface.activeLayer()
    px_size_x = layer.rasterUnitsPerPixelX()
    px_size_y = layer.rasterUnitsPerPixelY()
    xsize = int((extent.xMaximum() - extent.xMinimum()) / px_size_x)
    ysize = int((extent.yMinimum() - extent.yMaximum()) / px_size_y)
    return xsize, ysize
