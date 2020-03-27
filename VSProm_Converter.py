try:
>>> try:
...     import arcpy
...     from arcpy import env
...     #Set up environment
...     env.workspace = C:\Users\nsusm\Desktop\GIS
...     #Start the loop
...     for raster in env.workspace():
...     #convert tiff to ESRI grd
...     arcpy.RasterToOtherFormat_conversion(InRaster,Outworkspace,"GRID")
...     for GRID in env.workspace():
...         #mosaic GRID
...         arcpy.MosaicToNewRaster_management(input_rasters,env.workspace,vsprom,{},{16_BIT_UNSIGNED-A},{},{sum},{})
...         #convert to vector polyon
...         arcpy.RasterToPolygon_conversion(vsprom,vsprom,"NO_SIMPLIFY",{COUNT},"SINGLE_OUTER_PART",{})
...         #loop clipping place boundaries shapefiles to vector conversion of visual prominence
...    arcpy.env.workspace = D:\Documents\Archaeology\Dissertation\Data\GIS\Places_Bounds\Places\Exploded_Bilinear\Argolid.gdb     
...    for fc in arcpy.Clip_analysis(vsprom, PI_1, %name%, {})
