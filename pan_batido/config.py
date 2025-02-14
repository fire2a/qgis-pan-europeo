#!python3
from numpy import float32, float64, uint8, uint16
from osgeo.gdal import (GDT_Byte, GDT_Float32, GDT_Float64, GDT_UInt16,
                        GRIORA_Average, GRIORA_Bilinear, GRIORA_Cubic,
                        GRIORA_CubicSpline, GRIORA_Gauss, GRIORA_Lanczos,
                        GRIORA_Mode, GRIORA_NearestNeighbour)
from qgis.core import Qgis, QgsMessageLog
from qgis.PyQt.QtCore import QCoreApplication

DATATYPES = {
    "Byte(0-255)": {"gdal": GDT_Byte, "numpy": uint8},
    "UInt16(0-65535)": {"gdal": GDT_UInt16, "numpy": uint16},
    "Float32(0-1)": {"gdal": GDT_Float32, "numpy": float32},
    "Float64(0-1)": {"gdal": GDT_Float64, "numpy": float64},
}

GRIORAS = {
    "Nearest Neighbor": GRIORA_NearestNeighbour,
    "Bilinear (2x2 kernel)": GRIORA_Bilinear,
    "Cubic Convolution Approximation (4x4 kernel)": GRIORA_Cubic,
    "Cubic B-Spline Approximation (4x4 kernel)": GRIORA_CubicSpline,
    "Lanczos windowed sinc interpolation (6x6 kernel)": GRIORA_Lanczos,
    "Average": GRIORA_Average,
    "Mode": GRIORA_Mode,
    "Gauss blurring": GRIORA_Gauss,
    "None": None,
}

UTILITY_FUNCTIONS = [
    {"name": "minmax", "description": "min-max", "numvars": 0},
    {"name": "maxmin", "description": "max-min", "numvars": 0},
    {"name": "bipiecewiselinear", "description": "bi-piecewise-linear values", "numvars": 2},
    {"name": "bipiecewiselinear_percent", "description": "bi-piecewise-linear percentages", "numvars": 2},
    {"name": "stepup", "description": "step up value", "numvars": 1},
    {"name": "stepup_percent", "description": "step up percentage", "numvars": 1},
    {"name": "stepdown", "description": "step down value", "numvars": 1},
    {"name": "stepdown_percent", "description": "step down percentage", "numvars": 1},
]  # no cambiar orden!


def qprint(*args, tag="Marraqueta", level=Qgis.Info, sep=" ", end="", **kwargs):
    QgsMessageLog.logMessage(sep.join(map(str, args)) + end, tag, level, **kwargs)
    QCoreApplication.processEvents()


def get_key_by_subdict_item(dict_, subkey, subval):
    for key, sdict in dict_.items():
        for sk, sv in sdict.items():
            if sk == subkey and sv == subval:
                return key
    return None
