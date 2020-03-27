#!/usr/bin/env python
#
#########################################################################
#
# MODULE:       GRASS Visibility Calculation
#
# AUTHOR(S):    nsusm
#
# PURPOSE:      Basic visibility calculation for integration with Compute Viewshed Parallel (Brian Gregor
#
# DATE:         May 15, 2018
#
#########################################################################

#%module
#% description: Module description
#%end

import sys
import os
import atexit

import grass.script as gscript


# Import SHAPEFILE and set region
v.import --overwrite input=C:\Users\nsusm\Desktop\GIS layer=OP output=OP

# Import RASTER digital elevation model and set region

r.in.gdal input=D:\Documents\Archaeology\Dissertation\Data\GIS\GRASS\Viewshed\Data\pelop1arcm34b.tif output=dem

# Run VIEWSHED directing calculation to the vector observer point file

r.viewshed.cva input=pelop1arc34mb@Viewshed vector=OP@Viewshed output=cvsoa200 observer_elevation=1.65 memory=1000000000 refraction_coeff=0.13

