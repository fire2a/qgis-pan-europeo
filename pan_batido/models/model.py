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
from functools import partial
from pathlib import Path

from attrs import define, field
from cattrs import structure, unstructure
from osgeo.gdal import GA_ReadOnly, Open
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QTimer, QVariant
from qgis.core import (Qgis, QgsApplication, QgsFeatureRequest, QgsMessageLog, QgsProcessingAlgRunnerTask,
                       QgsProcessingFeatureSourceDefinition, QgsProject, QgsRasterLayer, QgsVectorLayer)

from ..constants import TAG, UTILITY_FUNCTIONS


def breakit():
    # fmt: off
    from IPython.terminal.embed import InteractiveShellEmbed
    from qgis.PyQt.QtCore import pyqtRemoveInputHook
    pyqtRemoveInputHook()
    # fmt: on
    return InteractiveShellEmbed()


def dict_to_cattr(data: dict, cls: type) -> object:
    return structure(data, cls)


def cattr_to_dict(instance: object) -> dict:
    return unstructure(instance)


@define
class Layer:
    id: str = ""
    visibility: bool = False
    name: str = ""
    filepath: str = ""
    weight: float = 1.0
    min: float | None = None
    max: float | None = None
    util_funcs: list[dict] = field(factory=lambda: UTILITY_FUNCTIONS.copy())
    uf_idx: int = 0  # CURRENTLY SELECTED utility function index


class Model(QtCore.QAbstractItemModel):
    visibilityChanged = QtCore.pyqtSignal(str, bool)

    def __init__(self, *args, iface=None, context=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.iface = iface
        self.context = context
        print(f"{self.iface=}, {self.context=}")
        self.layers = []
        self.load_layers()
        QgsProject.instance().layersRemoved.connect(self.on_layers_removed)
        QgsProject.instance().layersAdded.connect(self.on_layers_added)
        self.visibilityChanged.connect(self.update_layer_visibility)
        self.iface.mapCanvas().selectionChanged.connect(self.on_iface_selection_changed)
        self.tasks = []  # : QgsProcessingAlgRunnerTask

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

        layer = self.layers[index.row()]
        row, column = index.row(), index.column()

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
            print(f"Model:data: ({row}, {column}), {combo=}")
            return combo
        if role == Qt.EditRole and column == 4:
            sliders = [
                (text, values["min"], values["value"], values["max"])
                for text, values in layer.util_funcs[layer.uf_idx]["params"].items()
            ]
            print(f"Model:data: ({row}, {column}), {sliders=}")
            return sliders

        return QVariant()

    def setData(self, index, value, role):
        row, column = index.row(), index.column()
        if role == Qt.CheckStateRole and column == 0:
            lid = self.layers[row].id
            if QgsProject.instance().layerTreeRoot().findLayer(lid):
                self.layers[row].visibility = value == Qt.Checked
                self.dataChanged.emit(index, index)
                self.save()
                self.visibilityChanged.emit(lid, value == Qt.Checked)
                return True
        if role == Qt.EditRole and column == 2:
            self.layers[index.row()].weight = value
            self.dataChanged.emit(index, index)
            self.save()
            return True
        if role == Qt.EditRole and column == 3:
            print(f"Model:setData: ({row}, {column}), {value=}, {role=}")
            layer = self.layers[index.row()]
            layer.util_funcs = value["cb"]
            layer.uf_idx = value["idx"]
            self.dataChanged.emit(index, index, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])
            self.save()
            return True
        if role == Qt.EditRole and column == 4:
            print(f"Model:setData: ({row}, {column}), {value=}, {role=}")
            # breakit()()
            layer = self.layers[index.row()]
            for slider in value:
                param_name, _, val, _ = slider
                layer.util_funcs[layer.uf_idx]["params"][param_name]["value"] = val
            self.dataChanged.emit(index, index)
            self.save()
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
        from pprint import pprint

        for layer in self.layers:
            pprint(layer.name, layer.util_funcs)

    def load_layers(self):
        for lid, layer in QgsProject.instance().mapLayers().items():
            if isinstance(layer, QgsRasterLayer) and Path(layer.publicSource()).is_file():
                min_, max_ = get_file_minmax(layer.publicSource())
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
                    )
                ]

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
        self.save()

    def on_layers_added(self, add_layers):
        for layer in add_layers:
            if isinstance(layer, QgsRasterLayer) and Path(layer.publicSource()).is_file():
                min_, max_ = get_file_minmax(layer.publicSource())
                self.layers += [
                    Layer(
                        id=layer.id(),
                        visibility=True,
                        name=layer.name(),
                        min=min_,
                        max=max_,
                    )
                ]
                QTimer.singleShot(0, lambda lid=layer.id(): self.connect_layer_visibility_signal(lid))
        self.layoutChanged.emit()
        self.save()

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
            print(f"{feat['_min']=}, {feat['_max']=}")
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
            index = self.index(self.layers.index(raster), 3)
            self.dataChanged.emit(index, index, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])
            # top_left_index = self.index(self.layers.index(raster), 3)
            # bottom_right_index = self.index(self.layers.index(raster), 4)
            # self.dataChanged.emit(top_left_index, bottom_right_index, [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole])
            self.layoutChanged.emit()
            self.save()

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


def get_file_minmax(filename, force=True):
    # try:
    dataset = Open(filename, GA_ReadOnly)
    # except RuntimeError as e:
    #     if "not recognized as a supported file format" in str(e):
    #         raise FileNotFoundError("not recognized as a supported file format " + filename)
    if dataset is None:
        raise FileNotFoundError(filename)
    raster_band = dataset.GetRasterBand(1)
    rmin = raster_band.GetMinimum()
    rmax = raster_band.GetMaximum()
    if not rmin or not rmax or force:
        (rmin, rmax) = raster_band.ComputeRasterMinMax(True)
    return rmin, rmax
