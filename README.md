# Pan European Raster Algo

This repository contains the code for the Pan European Raster Algo (PERA) project. The PERA project is a collaboration between PEACH (Protection of Environment and Cultural Heritage) and the FIG(Fire Investigacion and Goverance). The project aims to develop a set of algorithms to process raster data in a distributed computing environment. The algorithms are designed to work with large-scale raster datasets, such as those produced by Technosylva and ERICO.

## How to?

Put `pan_batido` directory in you qgis plugin folder

## Current status
### Features:
* Reads all layers available and draws a dialog with each row belonging to a layer, containing
- layer name 
- weight attributes (checkbox for dis/en-abling, spinbox & slider in 0,100 range) 
- utility function configuration x2:
-- Min-Max scaling, with a invert checkbox
-- Bi-Piecewise-Linear, with spinboxes&sliders for its two 2 points (where the range are the raster min-max values)

### Development notes:
* dialog_base.ui is dummy
* pan_frances.py is not used right now
* a installation of fire2-lib is required
```
pip install git+https://github.com/fire2a/fire2a-lib.git
or 
git clone git@github.com:fire2a/fire2a-lib.git
cd fire2a-lib
pip install -e .
```


