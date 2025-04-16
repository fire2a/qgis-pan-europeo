#!python
"""
qgis
# fmt: off
from qgis.PyQt.QtCore import pyqtRemoveInputHook
pyqtRemoveInputHook()
from IPython.terminal.embed import InteractiveShellEmbed
InteractiveShellEmbed()()
# fmt: on

# layer.dataProvider().bandStatistics(1).minimumValue,
# layer.dataProvider().bandStatistics(1).maximumValue,
"""
import json
from copy import deepcopy
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from re import sub
from tempfile import NamedTemporaryFile

from numpy import isnan
from numpy import max as np_max
from numpy import min as np_min
from osgeo.gdal import GA_ReadOnly  # type: ignore
from osgeo.gdal import ApplyGeoTransform, GA_Update, InvGeoTransform, Open
from osgeo_utils.gdal_calc import Calc
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QTimer, QVariant
from qgis.core import QgsMessageLog  # type: ignore
from qgis.core import (Qgis, QgsApplication, QgsFeatureRequest, QgsProcessingAlgRunnerTask,
                       QgsProcessingFeatureSourceDefinition, QgsProject, QgsRasterLayer, QgsRectangle, QgsTask,
                       QgsVectorLayer)

from ..constants import TAG, UTILITY_FUNCTIONS


def breakit():
    # fmt: off
    from IPython.terminal.embed import InteractiveShellEmbed
    from qgis.PyQt.QtCore import pyqtRemoveInputHook  # type: ignore
    pyqtRemoveInputHook()
    # fmt: on
    return InteractiveShellEmbed()


def dict_to_cattr(data: dict, cls: type) -> object:
    """
    Manually convert a dictionary to an instance of the given class.
    """
    instance = cls()
    for key, value in data.items():
        if hasattr(instance, key):
            setattr(instance, key, value)
    return instance


def cattr_to_dict(instance: object) -> dict:
    """
    Manually convert an instance of a class to a dictionary.
    """
    return instance.__dict__


@dataclass
class Layer:
    id: str = ""
    visibility: bool = False
    name: str = ""
    filepath: str = ""
    weight: float = 1.0
    min: float | None = None
    max: float | None = None
    extent: QgsRectangle | None = None
    util_funcs: list[dict] = field(default_factory=lambda: deepcopy(UTILITY_FUNCTIONS))
    uf_idx: int = 0  # CURRENTLY SELECTED utility function index


class Model(QtCore.QAbstractItemModel):
    visibilityChanged = QtCore.pyqtSignal(str, bool)

    def __init__(self, *args, iface=None, context=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.iface = iface
        self.context = context
        self.layers = []
        self.load_layers()
        QgsProject.instance().layersRemoved.connect(self.on_layers_removed)
        QgsProject.instance().layersAdded.connect(self.on_layers_added)
        self.visibilityChanged.connect(self.update_layer_visibility)
        self.iface.mapCanvas().selectionChanged.connect(self.on_iface_selection_changed)
        self.tasks = []  # : QgsProcessingAlgRunnerTask

    def reset(self):
        self.cancel_tasks()
        self.layers = []
        self.load_layers()

    def cancel_tasks(self):
        for task in self.tasks:
            try:
                if task.isActive():
                    task.cancel()
                    QgsMessageLog.logMessage(f"Task '{task.description()}' canceled", tag=TAG, level=Qgis.Warning)
            except RuntimeError as e:
                if str(e).endswith("has been deleted"):
                    continue

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        if not parent.isValid():
            return self.createIndex(row, column, self.layers[row])
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        return QtCore.QModelIndex()

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            return len(self.layers)
        return 0

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 5

    def data(self, index, role):
        if not index.isValid():
            return QVariant()

        row, column = index.row(), index.column()
        layer = self.layers[row]

        if role == Qt.CheckStateRole and column == 0:
            return Qt.Checked if layer.visibility else Qt.Unchecked
        if role == Qt.DisplayRole and column == 1:
            # print(f"Model:data: ({row}, {column}), {layer.name=}")
            return layer.name
        if role == Qt.EditRole and column == 2:
            # print(f"Model:data: ({row}, {column}), {layer.weight=}")
            return layer.weight
        if role == Qt.EditRole and column == 3:
            combo = {"cb": layer.util_funcs, "idx": layer.uf_idx}
            # print(f"Model:data: ({row}, {column}), {combo=}")
            return combo
        if role == Qt.EditRole and column == 4:
            sliders = [
                (text, values["min"], values["value"], values["max"])
                for text, values in layer.util_funcs[layer.uf_idx]["params"].items()
            ]
            # print(f"Model:data: ({row}, {column}), {sliders=}")
            return sliders

        return QVariant()

    def setData(self, index, value, role):
        row, column = index.row(), index.column()
        if role == Qt.CheckStateRole and column == 0:
            lid = self.layers[row].id
            if QgsProject.instance().layerTreeRoot().findLayer(lid):
                self.layers[row].visibility = value == Qt.Checked
                self.dataChanged.emit(index, index)
                # self.save()
                self.visibilityChanged.emit(lid, value == Qt.Checked)
                return True
        if role == Qt.EditRole and column == 2:
            self.layers[index.row()].weight = value
            self.dataChanged.emit(index, index)
            # self.save()
            return True
        if role == Qt.EditRole and column == 3:
            # print(f"Model:setData: ({row}, {column}), {value=}, {role=}")
            layer = self.layers[row]
            layer.util_funcs = value["cb"]
            layer.uf_idx = value["idx"]
            self.dataChanged.emit(index, index, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])
            # self.save()
            return True
        if role == Qt.EditRole and column == 4:
            # print(f"Model:setData: ({row}, {column}), {value=}, {role=}")
            # breakit()()
            layer = self.layers[row]
            for slider in value:
                param_name, _, val, _ = slider
                layer.util_funcs[layer.uf_idx]["params"][param_name]["value"] = val
            self.dataChanged.emit(index, index)
            # self.save()
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        if index.column() == 0:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
        if index.column() in [2, 3, 4]:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if section == 0:
                return "Active"
            if section == 1:
                return "Layer name"
            if section == 2:
                return "Weight %"
            if section == 3:
                return "Utility function"
            if section == 4:
                return "Params"

    def load(self):
        try:
            with open("data.db", "r") as f:
                self.layers = [Layer(**layer) for layer in json.load(f)]
        except Exception:
            self.layers = []

    def save(self):
        # with open(Path(__file__).parent / "data.db", "w") as f:
        #     json.dump([cattr_to_dict(layer) for layer in self.layers], f)
        # from pprint import pprint

        for layer in self.layers:
            print(layer.name, layer.weight)
            # for uf in layer.util_funcs:
            #     pprint(uf)

    def load_layers(self):
        for lid, layer in QgsProject.instance().mapLayers().items():
            if isinstance(layer, QgsRasterLayer) and Path(layer.publicSource()).is_file():
                min_, max_, extent = get_file_info(layer.publicSource())
                layer_tree_layer = QgsProject.instance().layerTreeRoot().findLayer(lid)
                layer_tree_layer.visibilityChanged.connect(self.on_layer_visibility_changed)
                self.layers += [
                    Layer(
                        id=lid,
                        visibility=layer_tree_layer.isVisible(),
                        name=layer.name(),
                        filepath=layer.publicSource(),
                        min=min_,
                        max=max_,
                        extent=extent,
                    )
                ]
        self.dataChanged.emit(
            self.index(0, self.columnCount() - 1), self.index(len(self.layers) - 1, self.columnCount() - 1)
        )

    def on_layer_visibility_changed(self, node):
        layer_id = node.layerId()
        for i, layer in enumerate(self.layers):
            if layer.id == layer_id:
                self.layers[i].visibility = node.isVisible()
                self.dataChanged.emit(self.index(i, 0), self.index(i, 0))
                break

    def on_layers_removed(self, rem_layers):
        for lid in rem_layers:
            self.layers = [lyr for lyr in self.layers if lyr.id != lid]
        self.layoutChanged.emit()
        # self.save()

    def on_layers_added(self, add_layers):
        for layer in add_layers:
            if isinstance(layer, QgsRasterLayer) and Path(layer.publicSource()).is_file():
                min_, max_, extent = get_file_info(layer.publicSource())
                self.layers += [
                    Layer(
                        id=layer.id(),
                        visibility=True,
                        name=layer.name(),
                        min=min_,
                        max=max_,
                        extent=extent,
                    )
                ]
                QTimer.singleShot(0, lambda lid=layer.id(): self.connect_layer_visibility_signal(lid))
        self.layoutChanged.emit()
        # self.save()

    def connect_layer_visibility_signal(self, layer_id):
        layer_tree_layer = QgsProject.instance().layerTreeRoot().findLayer(layer_id)
        if layer_tree_layer:
            layer_tree_layer.visibilityChanged.connect(self.on_layer_visibility_changed)

    def update_layer_visibility(self, layer_id, visibility):
        layer_tree_layer = QgsProject.instance().layerTreeRoot().findLayer(layer_id)
        if layer_tree_layer:
            layer_tree_layer.setItemVisibilityChecked(visibility)

    def on_iface_selection_changed(self, layer):
        """Handle the selectionChanged signal from the map canvas."""
        # print(f"iface.selectionChanged: {layer=}")
        if not isinstance(layer, QgsVectorLayer):
            QgsMessageLog.logMessage("Not QgsVectorLayer selected", tag=TAG, level=Qgis.Warning)
            return
        if layer.selectedFeatureCount() == 0:
            QgsMessageLog.logMessage("No features selected", tag=TAG, level=Qgis.Warning)
            return

        for raster in self.layers:
            # print(f"{raster.name=}, {raster.filepath=}")
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
                    "INPUT_RASTER": raster.filepath,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                    "RASTER_BAND": 1,
                    "STATISTICS": [5, 6],
                },
                context=self.context,
            )
            # description = f"Min&Max Zonal Statistics for {raster.name}, on {layer.selectedFeatureCount()} selected  features of {layer.name()}"
            raster_short_name = raster.name[:6] + "..." if len(raster.name) > 6 else raster.name
            layer_short_name = layer.name()[:6] + "..." if len(layer.name()) > 6 else layer.name
            description = f"Min&Max Zonal Statistics for {raster_short_name}, on {layer_short_name} x{layer.selectedFeatureCount()}"
            task.setDescription(description)
            task.executed.connect(
                partial(
                    self.on_iface_selection_changed_task_finished,
                    context=self.context,
                    description=description,
                    raster=raster,
                )
            )
            self.tasks += [task]
            QgsApplication.taskManager().addTask(task)
        # print(f"iface.selectionChanged_end: {self.tasks=}")

    def on_iface_selection_changed_task_finished(self, successful, results, context=None, description="", raster=None):
        # print(f"iface.selectionChanged_task_finished: {successful=} {results=}")
        pre_msg = f'Task "{description}"'
        if not successful:
            QgsMessageLog.logMessage(f"{pre_msg} finished unsuccessfully", tag=TAG, level=Qgis.Warning)
            QgsMessageLog.logMessage(f"{pre_msg} {results=}", tag=TAG, level=Qgis.Critical)
            return
        output_layer = context.getMapLayer(results["OUTPUT"])
        # print(output_layer.fields().names())
        if not output_layer:
            QgsMessageLog.logMessage(f"{pre_msg} No output layer", tag=TAG, level=Qgis.Warning)
            return
        if not output_layer.isValid():
            QgsMessageLog.logMessage(f"{pre_msg} Output layer is not valid", tag=TAG, level=Qgis.Warning)
            return
        # QgsProject.instance().addMapLayer(context.takeResultLayer(output_layer.id()))
        if output_layer.featureCount() == 0:
            QgsMessageLog.logMessage(f"{pre_msg} Output layer has no features", tag=TAG, level=Qgis.Warning)
            return

        # get min and max values from the output layer
        min_, max_ = float("inf"), float("-inf")
        for feat in output_layer.getFeatures():
            # print(f"{feat['_min']=}, {feat['_max']=}")
            if feat["_min"] < min_:
                min_ = feat["_min"]
            if feat["_max"] > max_:
                max_ = feat["_max"]

        # set the min and max values to the model layers
        # print(f"View:on_iface_selection_changed_task_finished:321 {pre_msg=}")
        # breakit()()
        any_change = False
        for util_func in raster.util_funcs:
            if "percent" in util_func["name"]:
                continue
            for name, params in util_func["params"].items():
                if "min" in params:
                    # params["min"] = min_
                    uf_id = raster.util_funcs.index(util_func)
                    raster.util_funcs[uf_id]["params"][name]["min"] = min_
                    any_change = True
                if "max" in params:
                    # params["max"] = max_
                    uf_id = raster.util_funcs.index(util_func)
                    raster.util_funcs[uf_id]["params"][name]["max"] = max_
                    any_change = True
        if any_change:
            # create a QModelIndex for the layer
            # TODO use self.index instead ?
            # print(f"View:on_iface_selection_changed_task_finished:342 {pre_msg=}")
            # breakit()()
            index = self.index(self.layers.index(raster), 4)
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            # top_left_index = self.index(self.layers.index(raster), 3)
            # bottom_right_index = self.index(self.layers.index(raster), 4)
            # self.dataChanged.emit(top_left_index, bottom_right_index, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])
            self.layoutChanged.emit()
            # self.save()

            # for lyrs in self.layers:
            #     if lyrs.name == raster.name:
            #        print("heyy0")
            #        for util_func in lyrs.util_funcs:
            #            print(f"\t{util_func['name']}")
            #            for name, params in util_func["params"].items():
            #                print(f"\t\t{name}, {params}")
            #        for util_func in raster.util_funcs:
            #            print(f"\t{util_func['name']}")
            #            for name, params in util_func["params"].items():
            #                print(f"\t\t{name}, {params}")
            #        assert lyrs.util_funcs == raster.util_funcs
            #        print("heyy1")

        QgsMessageLog.logMessage(
            f"{pre_msg} finished successfully, new {min_=}, {max_=}, {any_change=}", tag=TAG, level=Qgis.Info
        )

    def balance_weights(self):
        total = sum(layer.weight for layer in self.layers if layer.visibility) / 100
        for i, layer in enumerate(self.layers):
            if layer.visibility:
                layer.weight /= total
                self.dataChanged.emit(self.index(i, 2), self.index(i, 2), [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])
        self.layoutChanged.emit()
        # self.save()

    def doit(self, load_normalized=False, no_data=None, rtype=7, projwin=None, outfile=""):
        """
        from osgeo_utils.gdal_calc import GDALDataTypeNames
        rtype 7: Float32 : GDALDataTypeNames[7]
        """
        print(f"Model.doit: {load_normalized=}, {no_data=}, {rtype=}")
        self.save()
        norm_files = []
        norm_tasks = []
        norm_names = []
        for raster in self.layers:
            if not raster.visibility:
                continue
            print(f"{raster.name=}, {raster.filepath=}")
            norm_names += [clean_str(raster.name)]
            util_func = raster.util_funcs[raster.uf_idx]
            # normalization method
            method = util_func["name"]
            print(f"{method=}")
            # don't need minmax
            if method in ["minmax", "maxmin", "bipiecewiselinear_percent", "stepup_percent", "stepdown_percent"]:
                minimum, maximum = None, None
            else:
                params = util_func["params"]
                if len(params) > 0:
                    first = list(params.values())[0]
                    minimum, maximum = first["min"], first["max"]
                else:
                    # print("no params!?")
                    minimum, maximum = None, None
            # params
            func_params = util_func["params"]
            func_values_str = " ".join([str(param["value"]) for param in func_params.values()])
            print(f"{func_values_str=}")
            # output file
            norm_file = NamedTemporaryFile(suffix=".tif", delete=False).name
            norm_files += [norm_file]

            task = QgsProcessingAlgRunnerTask(
                algorithm=QgsApplication.processingRegistry().algorithmById("paneuropeo:normalizator"),
                parameters={
                    "EXTENT_OPT": 0,
                    "INPUT_A": raster.filepath,
                    "MAX": maximum,
                    "METHOD": raster.uf_idx,
                    "MIN": minimum,
                    "NO_DATA": no_data,
                    "OUTPUT": norm_file,
                    "PARAMS": func_values_str,
                    "PROJWIN": projwin,
                    "RTYPE": rtype,
                },
                context=self.context,
            )
            if func_values_str:
                func_values_str = f" {func_values_str}"
            raster_short_name = raster.name[:6] + "..." if len(raster.name) > 6 else raster.name
            description = f"Normalize {raster_short_name} {method} {func_values_str}"
            task.setDescription(description)
            metadata = {
                "DESCRIPTION": clean_str(raster.name) + " " + clean_str(method) + " " + clean_str(func_values_str),
                "AUTHOR": "PanEuropeo",
            }
            task.executed.connect(
                partial(
                    self.on_doit_task_finished,
                    force_name="norm_" + raster.name,
                    add2map=load_normalized,
                    description=description,
                    metadata=metadata,
                )
            )
            norm_tasks += [task]
            # report
            QgsMessageLog.logMessage(f'Adding task "{description}". Weight:{raster.weight}%', tag=TAG, level=Qgis.Info)

        weights = [r.weight / 100 for r in self.layers if r.visibility]
        weights_str = " ".join(map(str, weights))
        dot_prod_str = " + ".join([f"{w:0.5f} x {n}" for w, n in zip(weights, norm_names)])
        final_task = QgsProcessingAlgRunnerTask(
            algorithm=QgsApplication.processingRegistry().algorithmById("paneuropeo:weightedsummator"),
            parameters={
                "EXTENT_OPT": 0,
                "INPUT": norm_files,
                "NO_DATA": None,
                "OUTPUT": "TEMPORARY_OUTPUT" if outfile == "" else outfile,
                "PROJWIN": None,
                "RTYPE": 7,
                "WEIGHTS": weights_str,
            },
            context=self.context,
        )
        description = f"Weighted Sum of {len(norm_files)} normalized rasters"
        final_task.executed.connect(
            partial(
                self.on_doit_task_finished,
                force_name="WEIGHTED_SUM" if outfile == "" else Path(outfile).stem,
                add2map=True,
                description=description,
                metadata={"DESCRIPTION": f"Summary: {dot_prod_str}", "AUTHOR": "PanEuropeo"},
            )
        )
        for task in norm_tasks:
            # final_task.addDependentTask(task) same ?
            final_task.addSubTask(task, [], QgsTask.SubTaskDependency.ParentDependsOnSubTask)

        self.tasks += [final_task] + norm_tasks
        QgsApplication.taskManager().addTask(final_task)
        QgsMessageLog.logMessage(f'Starting parent Task "{description}"', tag=TAG, level=Qgis.Info)
        # print(f"Model.doit: {self.tasks=}")

    def on_doit_task_finished(
        self, successful, results, force_name="Result", add2map=lambda: True, description="", metadata={}
    ):
        pre_msg = f'Task "{description}"'
        if not successful:
            QgsMessageLog.logMessage(f"{pre_msg} finished unsuccessfully", tag=TAG, level=Qgis.Warning)
            QgsMessageLog.logMessage(
                f"{pre_msg} {results=}, check the Processing tab logs for more info!", tag=TAG, level=Qgis.Critical
            )
            return
        output_layer = self.context.getMapLayer(results["OUTPUT"])
        # QgsMessageLog.logMessage(f"Task finished successfully {results}", tag=TAG, level=Qgis.Info)
        if add2map:
            if output_layer and output_layer.isValid():
                layer = self.context.takeResultLayer(output_layer.id())
                filename = layer.publicSource()
                if metadata:
                    add_metadata(filename, metadata)
                QgsProject.instance().addMapLayer(layer)
                QgsMessageLog.logMessage(f"{pre_msg} added raster from context layer.", tag=TAG, level=Qgis.Success)
                # print("from context")
            elif Path(results["OUTPUT"]).is_file():
                filename = results["OUTPUT"]
                if metadata:
                    add_metadata(filename, metadata)
                layer = QgsRasterLayer(filename, force_name)
                QgsProject.instance().addMapLayer(layer)
                QgsMessageLog.logMessage(f"{pre_msg} added raster from file.", tag=TAG, level=Qgis.Success)
                # print("from file")

    def calc_extent_minmax(self, extent):
        # QgsMessageLog.logMessage("Model.calc_extent_minmax 0", TAG, Qgis.Info)
        # print("Model.calc_extent_minmax 0")
        for raster in self.layers:
            if extent.contains(raster.extent):
                self.restore_minmax()
                QgsMessageLog.logMessage("Extent contains raster, restoring file min, max", TAG, Qgis.Info)
                continue
            if extent.intersect(raster.extent).isEmpty():
                QgsMessageLog.logMessage("No intersection between the extents.", TAG, Qgis.Warning)
                continue
            task = QgsTask.fromFunction(
                "Get min & max from extent of raster " + raster.name,
                get_minmax_task,
                raster=raster,
                extent=extent,
                on_finished=partial(self.set_minmax_on_fin, raster),
            )
            self.tasks += [task]
            QgsApplication.taskManager().addTask(task)
            # print(f"Model.calc_extent_minmax: task {raster.name=}, {task=}")
            QgsMessageLog.logMessage(f"Task sent: {task.description()}", TAG, Qgis.Info)
        # print("Model.calc_extent_minmax 1")

    def set_minmax_on_fin(self, raster, _, min_, max_):
        # print("Model.set_minmax_on_fin 0 {raster.name=}")
        if not min_ and not max_:
            return
        any_change = False
        for util_func in raster.util_funcs:
            if "percent" in util_func["name"]:
                continue
            for name, params in util_func["params"].items():
                if "min" in params:
                    # params["min"] = min_
                    uf_id = raster.util_funcs.index(util_func)
                    if min_:
                        raster.util_funcs[uf_id]["params"][name]["min"] = min_
                        # print(f"changed min {uf_id=} {name=} {min_=}")
                        any_change = True
                if "max" in params:
                    # params["max"] = max_
                    uf_id = raster.util_funcs.index(util_func)
                    if max_:
                        raster.util_funcs[uf_id]["params"][name]["max"] = max_
                        # print(f"changed max {uf_id=} {name=} {max_=}")
                        any_change = True
        if any_change:
            index = self.index(self.layers.index(raster), 4)
            self.dataChanged.emit(index, index, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])
        # print("Model.set_minmax_on_fin 1 {raster.name=}")

    def restore_minmax(self):
        # print("Model:restore_minmax 0")
        for raster in self.layers:
            any_change = False
            for util_func in raster.util_funcs:
                if "percent" in util_func["name"]:
                    continue
                for name, params in util_func["params"].items():
                    if "min" in params:
                        # params["min"] = min_
                        uf_id = raster.util_funcs.index(util_func)
                        raster.util_funcs[uf_id]["params"][name]["min"] = raster.min
                        any_change = True
                    if "max" in params:
                        # params["max"] = max_
                        uf_id = raster.util_funcs.index(util_func)
                        raster.util_funcs[uf_id]["params"][name]["max"] = raster.max
                        any_change = True
            if any_change:
                index = self.index(self.layers.index(raster), 4)
                self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
                self.layoutChanged.emit()
        # print("Model:restore_minmax 1")


def get_minmax_task(task, raster, extent):
    # f"Model.calc_extent_minmax.get_minmax_task:0 {raster.name=}, {str(extent)=}", TAG, Qgis.Info
    QgsMessageLog.logMessage(f"Task {task.description()} start!", TAG, Qgis.Info)
    try:
        min_, max_ = get_minmax_with_gdal_open(raster, extent)
    except RuntimeError:
        QgsMessageLog.logMessage(
            "Task {task.description()} failed, raster doesn't fit in memory! Trying gdal_calc...", TAG, Qgis.Warning
        )
        try:
            min_, max_ = get_minmax_with_gdal_calc(raster.filepath, extent)
        except RuntimeError:
            QgsMessageLog.logMessage(
                "Task {task.description()} gdal_cal failed! Try selecting a polygon feature instead..." + raster.name,
                TAG,
                Qgis.Warning,
            )
            return None, None
    QgsMessageLog.logMessage(f"Task {task.description()} got {min_=}, {max_=}", TAG, Qgis.Info)
    return min_, max_


def get_file_info(filename, force=True):
    # try:
    dataset = Open(filename, GA_ReadOnly)
    # except RuntimeError as e:
    #     if "not recognized as a supported file format" in str(e):
    #         raise FileNotFoundError("not recognized as a supported file format " + filename)
    if dataset is None:
        raise FileNotFoundError(filename)
    # extent
    geotransform = dataset.GetGeoTransform()
    x_size = dataset.RasterXSize
    y_size = dataset.RasterYSize
    x_min, y_max = ApplyGeoTransform(geotransform, 0, 0)
    x_max, y_min = ApplyGeoTransform(geotransform, x_size, y_size)
    extent = QgsRectangle(x_min, y_min, x_max, y_max)
    raster_band = dataset.GetRasterBand(1)
    # max min
    rmin = raster_band.GetMinimum()
    rmax = raster_band.GetMaximum()
    if not rmin or not rmax or force:
        (rmin, rmax) = raster_band.ComputeRasterMinMax(True)
    #
    return rmin, rmax, extent


def clean_str(astring: str):
    """Replace all non word characters with _, Word characters include letters (a-z, A-Z), digits (0-9), and underscores (_)."""
    # from string import printable
    # from re import sub
    # print(printable, sub(r"\W+", "_", printable))
    return sub(r"\W+", "_", astring)


def add_metadata(filename, metadata):
    """Add metadata to the raster file."""
    # filename = "ws.tif"
    # metadata = {"HOLA": "mundo", "QUE": "tal", "DESCRIPTION":"Esto es una prueba"}
    dataset = Open(filename, GA_Update)
    if dataset is None:
        raise FileNotFoundError(filename)
    for key, value in metadata.items():
        dataset.SetMetadataItem(key, value)
    dataset.FlushCache()
    dataset = None


def get_minmax_with_gdal_calc(filename, extent=None):
    """
    Get the minimum and maximum values of a raster using gdal_calc.
    This works reading large rasters in chunks, so it is not memory intensive.

    :param filename: Path to the raster file.
    :param extent: QgsRectangle object defining the extent to calculate min/max.
    :return: Tuple of (min_value, max_value) within the extent.
    """

    # minx maxy maxx miny
    rextent = [extent.xMinimum(), extent.yMaximum(), extent.xMaximum(), extent.yMinimum()]

    outfile = NamedTemporaryFile(prefix="pan_europeo_minmax_extent_", suffix=".tif", delete=False).name

    Calc(
        calc=["numpy.min(A)", "numpy.max(A)"],
        A=filename,
        outfile=outfile,
        projwin=rextent,
        overwrite=True,
        # quiet=True,
    )

    dataset = Open(outfile)
    if dataset is None:
        raise FileNotFoundError(f"Raster file not found: {outfile}")
    band_min = dataset.GetRasterBand(1)
    band_max = dataset.GetRasterBand(2)
    array_min = band_min.ReadAsArray()
    array_max = band_max.ReadAsArray()
    min_value = array_min[0, 0]
    max_value = array_max[0, 0]

    return min_value, max_value


def get_minmax_with_gdal_open(raster, extent):
    """
    Get the minimum and maximum values of a raster using GDAL and NumPy.
    This reads the raster in memory so it is not memory efficient for large rasters, use with try/catch.

    :param filename: Path to the raster file.
    :param extent: QgsRectangle object defining the extent to calculate min/max.
    :return: Tuple of (min_value, max_value) within the extent.
    """
    # print("get_minmax_with_gdal_open 0")

    dataset = Open(raster.filepath, GA_ReadOnly)
    if dataset is None:
        raise FileNotFoundError(f"Raster file not found: {raster.filepath}")
    geotransform = dataset.GetGeoTransform()
    band = dataset.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    x_size = dataset.RasterXSize
    y_size = dataset.RasterYSize

    intersection = extent.intersect(raster.extent)
    inv_geotransform = InvGeoTransform(geotransform)
    if not inv_geotransform:
        raise RuntimeError("Failed to invert geotransform.")
    x_min, y_min = ApplyGeoTransform(inv_geotransform, intersection.xMinimum(), intersection.yMaximum())
    x_max, y_max = ApplyGeoTransform(inv_geotransform, intersection.xMaximum(), intersection.yMinimum())

    x_off = int(x_min)
    y_off = int(y_min)
    win_xsize = int(x_max - x_min)
    win_ysize = int(y_max - y_min)

    # avoid reading outside raster bounds
    # TODO can't read outside as it's intersecting first?
    adjusted_win_xsize = min(win_xsize, x_size - x_off)
    adjusted_win_ysize = min(win_ysize, y_size - y_off)

    # Read the data within the intersection as a NumPy array
    array = band.ReadAsArray(x_off, y_off, adjusted_win_xsize, adjusted_win_ysize)
    if array is None:
        raise ValueError("Failed to read raster data within the specified extent.")
    # filter nodata
    data = array[(array != nodata) & ~isnan(array)]
    if data.size > 0:
        # print("get_minmax_with_gdal_open 1")
        return np_min(data), np_max(data)
    else:
        # print("get_minmax_with_gdal_open 1")
        return None, None
