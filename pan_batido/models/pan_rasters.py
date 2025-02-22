from copy import deepcopy
from functools import partial
from math import isclose
from pathlib import Path

from osgeo.gdal import GA_ReadOnly, Open
from qgis.core import (Qgis, QgsApplication, QgsFeatureRequest, QgsMessageLog, QgsProcessingAlgRunnerTask,
                       QgsProcessingFeatureSourceDefinition, QgsProject, QgsRasterLayer, QgsVectorLayer)
from qgis.PyQt.QtCore import QObject, pyqtSignal

from ..constants import TAG, UTILITY_FUNCTIONS

# from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsRasterLayer


class PanRasters(QObject):
    visibilityChanged = pyqtSignal(str, bool)

    def __init__(self, iface, context):
        super().__init__()
        self.context = context
        self.iface = iface
        self.rasters = {}
        self.raster_params = {}
        self.current_utility_function = {}
        self.weights = {}
        self.visibility = {}
        self.deleted = {}
        self.min = {}
        self.max = {}

    def on_visibility_changed(self, node):
        """Handle the visibilityChanged signal."""
        if layer := node.layer():
            raster_name = layer.name()
            visible = node.isVisible()
            self.set_visibility(raster_name, visible)
            self.visibilityChanged.emit(raster_name, visible)

    def set_visibility(self, raster_name, visible):
        """Set the visibility for a raster."""
        self.visibility[raster_name] = visible
        if node := self.get_layer_tree_node(raster_name):
            node.setItemVisibilityChecked(visible)

    def get_visibility(self, raster_name):
        """Get the visibility for a raster."""
        return self.visibility.get(raster_name, False)

    def get_layer_tree_node(self, raster_name):
        """Get the QgsLayerTreeNode for a raster."""
        try:
            if raster := self.rasters.get(raster_name):
                return QgsProject.instance().layerTreeRoot().findLayer(raster.id())
        except RuntimeError as e:
            if str(e) == "wrapped C/C++ object of type QgsRasterLayer has been deleted":
                return None

    def reset(self):
        """Clear the model."""
        self.rasters = {}
        self.raster_params = {}
        self.current_utility_function = {}
        self.weights = {}
        self.visibility = {}
        self.deleted = {}
        self.min = {}
        self.max = {}

    def create(self):
        """Create the list of rasters from the current QGIS project."""
        for raster in QgsProject.instance().mapLayers().values():
            if (
                isinstance(raster, QgsRasterLayer)
                and raster.publicSource() != ""
                and Path(raster.publicSource()).is_file()
            ):
                name = raster.name()
                self.rasters[name] = raster
                self.raster_params[name] = {func["name"]: deepcopy(func["params"]) for func in UTILITY_FUNCTIONS}
                self.current_utility_function[name] = None
                self.weights[name] = 1
                self.set_minmax(name, *self.get_file_minmax(name, raster.publicSource()))
                if layer := QgsProject.instance().layerTreeRoot().findLayer(raster.id()):
                    self.visibility[name] = layer.isVisible()
                    layer.visibilityChanged.connect(self.on_visibility_changed)

    def update_rasters(self):
        """Update the list of rasters from the current QGIS project."""
        map_layers = QgsProject.instance().mapLayers()
        new_rasters = {
            layer.name(): layer
            for layer in map_layers.values()
            if isinstance(layer, QgsRasterLayer)
            and layer.publicSource() != ""
            and Path(layer.publicSource()).is_file()
            and layer.name() not in self.rasters
        }

        for raster_name, raster in new_rasters.items():
            self.rasters[raster_name] = raster
            self.raster_params[raster_name] = {func["name"]: deepcopy(func["params"]) for func in UTILITY_FUNCTIONS}
            self.current_utility_function[raster_name] = None
            self.weights[raster_name] = 1
            self.set_minmax(raster_name, *self.get_file_minmax(raster_name, raster.publicSource()))

        for raster_name in self.rasters:
            if raster_name in [r.name() for r in map_layers.values()]:
                raster = [r for r in map_layers.values() if r.name() == raster_name][0]
                if layer := QgsProject.instance().layerTreeRoot().findLayer(raster.id()):
                    self.visibility[raster_name] = layer.isVisible()
                    layer.visibilityChanged.connect(self.on_visibility_changed)
                self.set_raster_deleted(raster_name, False)
            else:
                self.set_raster_deleted(raster_name, True)

    def update_params_range(self, raster_name, min_value, max_value):
        """Update the range of a parameter for a utility function."""
        for func in UTILITY_FUNCTIONS:
            if "percent" in func["name"]:
                continue
            if params := self.get_raster_params(raster_name, func["name"]):
                for param in params.values():
                    param["min"] = min_value
                    param["max"] = max_value
                    param["value"] = max(min(param["value"], param["max"]), param["min"])
                self.set_raster_params(raster_name, func["name"], params)

    def get_rasters(self):
        """Get the list of rasters."""
        if self.rasters == {}:
            self.create()
            return self.rasters
        else:
            self.update_rasters()
            return {name: raster for name, raster in self.rasters.items() if not self.is_raster_deleted(name)}

    def get_raster_names(self):
        """Get the names of the rasters."""
        return [raster.name() for raster in self.rasters.values()]

    def get_utility_function_by_name(self, name):
        """Get a utility function by its name."""
        for func in UTILITY_FUNCTIONS:
            if func["name"] == name:
                return func
        raise ValueError(f"Utility function {name} not found")

    def set_raster_params(self, raster_name, utility_name, params):
        """Set the parameters for a raster and utility function."""
        self.raster_params[raster_name][utility_name] = params

    def get_raster_params(self, raster_name, utility_name):
        """Get the parameters for a raster and utility function."""
        return self.raster_params[raster_name].get(utility_name, {})

    def set_current_utility_function_name(self, raster_name, utility_name):
        """Set the current utility function for a raster."""
        self.current_utility_function[raster_name] = utility_name

    def get_current_utility_function_name(self, raster_name):
        """Get the current utility function name for a raster."""
        return self.current_utility_function.get(raster_name, None)

    def get_current_utility_function(self, raster_name):
        """Get the current utility function object for a raster."""
        current_func_name = self.get_current_utility_function_name(raster_name)
        for func in UTILITY_FUNCTIONS:
            if func["name"] == current_func_name:
                return func

    def set_weight(self, raster_name, weight):
        """Set the weight for a raster."""
        self.weights[raster_name] = weight

    def get_weight(self, raster_name):
        """Get the weight for a raster."""
        return self.weights[raster_name]

    def balance_weights(self):
        """Balance the weights of the rasters, so the sum is 100, only for non-deleted rasters."""
        rasters = [
            raster_name
            for raster_name in self.rasters
            if not self.is_raster_deleted(raster_name) and self.get_visibility(raster_name)
        ]
        total = sum(self.get_weight(raster_name) for raster_name in rasters)
        for raster_name in rasters:
            self.set_weight(raster_name, 100 * self.get_weight(raster_name) / total)

    def set_raster_deleted(self, raster_name, deleted: bool):
        """Mark a raster as deleted."""
        self.deleted[raster_name] = deleted

    def is_raster_deleted(self, raster_name):
        """Check if a raster is deleted."""
        return self.deleted.get(raster_name, None)

    # def check_raster_deleted(self, raster_name):
    #     """Check if a raster layer is valid."""
    #     try:
    #         raster = self.rasters.get(raster_name)
    #         retval = raster is None or not raster.isValid()
    #     except RuntimeError as e:
    #         if str(e) == "wrapped C/C++ object of type QgsRasterLayer has been deleted":
    #             retval = True
    #         else:
    #             raise
    #     self.set_raster_deleted(raster_name, retval)
    #     return retval

    def print_all_params(self):
        """Print all parameters for all rasters and utility functions."""
        print("print_all_params")
        for raster_name, funcs in self.raster_params.items():
            weight = self.get_weight(raster_name)
            for func_name, params in funcs.items():
                print(f"{raster_name=}, {weight=}, {func_name=}, {params=}")

    def print_current_params(self):
        print("print_cur_params")
        for raster_name, raster in self.rasters.items():
            weight = self.get_weight(raster_name)
            current_func = self.current_utility_function[raster_name]
            params = self.raster_params[raster_name].get(current_func, {})
            visibility = self.visibility[raster_name]
            deleted = self.is_raster_deleted(raster_name)
            print(f"{raster_name[:7]=},\t{weight=},\t{current_func[:7]=},\t{params=},\t{visibility=},\t{deleted=}")

    def get_minmax(self, raster_name):
        return self.min.get(raster_name, None), self.max.get(raster_name, None)

    def set_minmax(self, raster_name, min_value, max_value):
        self.min[raster_name] = min_value
        self.max[raster_name] = max_value
        self.update_params_range(raster_name, min_value, max_value)

    def get_file_minmax(self, raster_name, filename, force=True):
        try:
            dataset = Open(filename, GA_ReadOnly)
        except Exception as e:
            if "not recognized as a supported file format" in str(e):
                self.iface.messageBar().pushMessage(
                    f"{raster_name=}, {filename} is not a GDAL supported file format, remove the raster layer, and try again.",
                    level=Qgis.Critical,
                )
            self.set_raster_deleted(raster_name, True)
        if dataset is None:
            raise FileNotFoundError(filename)
        raster_band = dataset.GetRasterBand(1)
        rmin = raster_band.GetMinimum()
        rmax = raster_band.GetMaximum()
        if not rmin or not rmax or force:
            # start = time()
            (rmin, rmax) = raster_band.ComputeRasterMinMax(True)
            # QgsMessageLog.logMessage(
            #     f"ComputeRasterMinMax took {time()-start} seconds {rmin=}, {rmax=}, {filename=}",
            #     tag=TAG,
            #     level=Qgis.Info,
            # )
        return rmin, rmax

    def calculate_zonal_statistics(self, layer):
        """Calculate zonal statistics for the rasters in the model."""
        if not isinstance(layer, QgsVectorLayer):
            QgsMessageLog.logMessage("Not QgsVectorLayer selected", tag=TAG, level=Qgis.Warning)
            return
        if layer.selectedFeatureCount() == 0:
            QgsMessageLog.logMessage("No features selected", tag=TAG, level=Qgis.Warning)
            return

        tasks = []
        for raster_name, raster in self.rasters.items():
            if raster.isValid() and Path(raster.publicSource()).is_file():
                task = QgsProcessingAlgRunnerTask(
                    algorithm=QgsApplication.processingRegistry().algorithmById("native:zonalstatisticsfb"),
                    parameters={
                        "COLUMN_PREFIX": "_",
                        "INPUT": QgsProcessingFeatureSourceDefinition(
                            layer.publicSource(),
                            selectedFeaturesOnly=True,
                            featureLimit=-1,
                            geometryCheck=QgsFeatureRequest.GeometryAbortOnInvalid,
                        ),
                        "INPUT_RASTER": raster,
                        "OUTPUT": "TEMPORARY_OUTPUT",
                        "RASTER_BAND": 1,
                        "STATISTICS": [5, 6],
                    },
                    context=self.context,
                )
                task.executed.connect(partial(self.task_finished, raster_name=raster_name))
                tasks.append(task)

        for task in tasks:
            QgsApplication.taskManager().addTask(task)

    def task_finished(self, successful, results, raster_name):
        if not successful:
            QgsMessageLog.logMessage(f"Zonal Statistics finished badly for {raster_name}", tag=TAG, level=Qgis.Critical)
        else:
            QgsMessageLog.logMessage(f"Zonal Statistics finished good for {raster_name}", tag=TAG, level=Qgis.Success)
            output_layer = self.context.getMapLayer(results["OUTPUT"])
            if output_layer and output_layer.isValid():
                was = self.get_minmax(raster_name)
                min_ = float("inf")
                max_ = -float("inf")
                for feat in output_layer.getFeatures():
                    min_ = min(feat["_min"], min_)
                    max_ = max(feat["_max"], max_)
                now = (min_, max_)
                if isclose(was[0], min_, rel_tol=1e-3) and isclose(was[1], max_, rel_tol=1e-3):
                    QgsMessageLog.logMessage(
                        f"Min-max did not change >1e-3 for {raster_name}", tag=TAG, level=Qgis.Warning
                    )
                    return
                self.set_minmax(raster_name, min_, max_)
                self.visibilityChanged.emit(raster_name, True)  # Emit signal to update the view
                QgsMessageLog.logMessage(
                    f"Min-max {was=}, {now=}, over:{output_layer.featureCount()} features for {raster_name}",
                    tag=TAG,
                    level=Qgis.Info,
                )
            else:
                QgsMessageLog.logMessage(f"Invalid output for {raster_name}", tag=TAG, level=Qgis.Critical)
