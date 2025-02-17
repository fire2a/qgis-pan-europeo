from copy import deepcopy
from math import ceil, floor
from pathlib import Path

from fire2a.raster import read_raster
from qgis.core import QgsProject, QgsRasterLayer

UTILITY_FUNCTIONS = [
    {"name": "minmax", "description": "min-max", "numvars": 0, "params": {}},
    {"name": "maxmin", "description": "max-min", "numvars": 0, "params": {}},
    {
        "name": "bipiecewiselinear",
        "description": "bi-piecewise-linear values",
        "numvars": 2,
        "params": {"a": {"min": 0, "max": 100, "value": 50}, "b": {"min": 0, "max": 100, "value": 50}},
    },
    {
        "name": "bipiecewiselinear_percent",
        "description": "bi-piecewise-linear percentages",
        "numvars": 2,
        "params": {"a": {"min": 0, "max": 100, "value": 50}, "b": {"min": 0, "max": 100, "value": 50}},
    },
    {
        "name": "stepup",
        "description": "step up value",
        "numvars": 1,
        "params": {"threshold": {"min": 0, "max": 100, "value": 50}},
    },
    {
        "name": "stepup_percent",
        "description": "step up percentage",
        "numvars": 1,
        "params": {"threshold": {"min": 0, "max": 100, "value": 50}},
    },
    {
        "name": "stepdown",
        "description": "step down value",
        "numvars": 1,
        "params": {"threshold": {"min": 0, "max": 100, "value": 50}},
    },
    {
        "name": "stepdown_percent",
        "description": "step down percentage",
        "numvars": 1,
        "params": {"threshold": {"min": 0, "max": 100, "value": 50}},
    },
]


class RasterModel:
    def __init__(self):
        self.rasters = {}
        self.utility_functions = UTILITY_FUNCTIONS
        self.raster_params = {}
        self.current_utility_function = {}
        self.weights = {}
        self.visibility = {}
        self.deleted = {}
        self.info = {}

    def clear_rasters(self):
        """Clear the model."""
        self.rasters = {}
        self.raster_params = {}
        self.current_utility_function = {}
        self.weights = {}
        self.visibility = {}
        self.deleted = {}
        self.info = {}

    def load_rasters(self):
        """Update the list of rasters from the current QGIS project."""
        self.rasters = {
            layer.name(): layer
            for layer in QgsProject.instance().mapLayers().values()
            if isinstance(layer, QgsRasterLayer) and layer.publicSource() != "" and Path(layer.publicSource()).is_file()
        }
        for raster_name, raster in self.rasters.items():
            self.raster_params[raster_name] = {
                func["name"]: deepcopy(func["params"]) for func in self.utility_functions
            }
            self.current_utility_function[raster_name] = None
            self.weights[raster_name] = 1
            self.info[raster_name] = read_raster(raster.publicSource(), data=False, info=True)[1]
            self.info[raster_name]["path"] = raster.publicSource()
            self.update_params_range(raster_name, self.info[raster_name]["Minimum"], self.info[raster_name]["Maximum"])
            self.visibility[raster_name] = QgsProject.instance().layerTreeRoot().findLayer(raster.id()).isVisible()

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
            self.raster_params[raster_name] = {
                func["name"]: deepcopy(func["params"]) for func in self.utility_functions
            }
            self.current_utility_function[raster_name] = None
            self.weights[raster_name] = 1
            self.info[raster_name] = read_raster(raster.publicSource(), data=False, info=True)[1]
            self.info[raster_name]["path"] = raster.publicSource()
            self.update_params_range(raster_name, self.info[raster_name]["Minimum"], self.info[raster_name]["Maximum"])

        for raster_name in self.rasters:
            if raster_name in [r.name() for r in map_layers.values()]:
                raster = [r for r in map_layers.values() if r.name() == raster_name][0]
                if lyr := QgsProject.instance().layerTreeRoot().findLayer(raster.id()):
                    self.set_visibility(raster_name, lyr.isVisible())
                self.set_raster_deleted(raster_name, False)
            else:
                self.set_raster_deleted(raster_name, True)

    def update_params_range(self, raster_name, min_value, max_value):
        """Update the range of a parameter for a utility function."""
        for func in self.utility_functions:
            if "percent" in func["name"]:
                continue
            if params := self.get_raster_params(raster_name, func["name"]):
                for param in params.values():
                    param["min"] = floor(min_value)
                    param["max"] = ceil(max_value)
                    param["value"] = max(min(param["value"], param["max"]), param["min"])
                self.set_raster_params(raster_name, func["name"], params)

    def get_rasters(self):
        """Get the list of rasters."""
        if self.rasters == {}:
            self.load_rasters()
            return self.rasters
        else:
            self.update_rasters()
            return {name: raster for name, raster in self.rasters.items() if not self.is_raster_deleted(name)}

    def get_raster_names(self):
        """Get the names of the rasters."""
        return [raster.name() for raster in self.rasters.values()]

    def get_utility_functions(self):
        """Get the list of utility functions."""
        return self.utility_functions

    def get_utility_function_by_name(self, name):
        """Get a utility function by its name."""
        for func in self.utility_functions:
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
        for func in self.utility_functions:
            if func["name"] == current_func_name:
                return func

    def set_weight(self, raster_name, weight):
        """Set the weight for a raster."""
        self.weights[raster_name] = weight

    def get_weight(self, raster_name):
        """Get the weight for a raster."""
        return self.weights[raster_name]

    def set_visibility(self, raster_name, visible):
        """Set the visibility for a raster."""
        self.visibility[raster_name] = visible

    def get_visibility(self, raster_name):
        """Get the visibility for a raster."""
        return self.visibility[raster_name]

    def set_raster_deleted(self, raster_name, deleted: bool):
        """Mark a raster as deleted."""
        self.deleted[raster_name] = deleted

    def is_raster_deleted(self, raster_name):
        """Check if a raster is deleted."""
        return self.deleted.get(raster_name, False)

    def check_raster_deleted(self, raster_name):
        """Check if a raster layer is valid."""
        try:
            raster = self.rasters.get(raster_name)
            retval = raster is None or not raster.isValid()
        except RuntimeError as e:
            if str(e) == "wrapped C/C++ object of type QgsRasterLayer has been deleted":
                retval = True
            else:
                raise
        self.set_raster_deleted(raster_name, retval)
        return retval

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
