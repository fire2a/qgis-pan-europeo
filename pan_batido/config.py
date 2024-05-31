#!python3
from numpy import float32, float64, uint8, uint16
from osgeo.gdal import (GDT_Byte, GDT_Float32, GDT_Float64, GDT_UInt16,
                        GRIORA_Average, GRIORA_Bilinear, GRIORA_Cubic,
                        GRIORA_CubicSpline, GRIORA_Gauss, GRIORA_Lanczos,
                        GRIORA_Mode, GRIORA_NearestNeighbour)
from qgis.core import Qgis, QgsMessageLog

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
}


def qprint(*args, tag="Marraqueta", level=Qgis.Info, sep=" ", end="\n", **kwargs):
    QgsMessageLog.logMessage(sep.join(map(str, args)) + end, tag, level, **kwargs)
