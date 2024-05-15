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
