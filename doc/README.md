# Pan European Proof of Concept

This QGIS plugin allows its users to calculate a summary cualitative raster from a set of large input rasters; by defining for each one its relative weight, utility attribute function parameters, and a resampling method.

# Quick start
- Install QGIS (latest desktop version on qgis.org)
- On the QGIS menu, go to Plugins > Manage and Install Plugins 
- All (vertical tab on the left) > Search for "Pan European Proof of Concept" (top horizontal input) > Select the plugin (checkbox) > Click "Install" (bottom right)
- The plugin will be available on the "Plugins" section of the toolbar or on the "Plugins" menu

# How to use
1. Open QGIS
2. Load a set of raster layers (current shared rasters are @f2a googledrive, ask for access)
3. Click on the "Pan European Proof of Concept" plugin icon
4. A dialog will appear with a list of the loaded layers, each one with a set of configuration options
- Set weight attributes (checkbox for dis/en-abling, spinbox & slider in 0,100 range)
- Set utility function configuration x2:
-- Min-Max scaling, with a invert checkbox
-- Bi-Piecewise-Linear, with spinboxes&sliders for its two 2 points (where the range are the raster min-max values)
5. Press "Ok" to calculate a new layer
6. Export the new layer as a pdf or png file (right click on the layer > Export > Save as Image)
