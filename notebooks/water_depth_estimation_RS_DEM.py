#!/usr/bin/env python
# coding: utf-8

#   
# # Water Depth Estimation using Remote Sensing and DEM
# ## FWDET method
#  
# **Author:** Jin Teng (jin.teng@csiro.au)
# 
# **Compatability:** Notebook currently compatible with the NCI.
# 
# **Dependencies:** The code below requires installation of following packages:
# 
#     rasterio
#     numpy
#     scipy
# 
# ## Description
# 
# This water depth estimation tool is inspired by the Floodwater Depth Estimation Tool (FwDET) https://github.com/csdms-contrib/fwdet (Cohen et al. 2017, 2019). It is developed to add value to remote sensing (RS) analysis by calculating
# water depth based solely on an inundation map with an associated digital elevation model (DEM).
# 
# The main steps of the algorithm are:
# 
#     (1) extract the grid cells that lay on the outline of the inundation extent from the raster; 
#     (2) extract the DEM value (elevation) for these grid cells (referred to as boundary grid cells);
#     (3) interpolate the local floodwater elevation from the boundary grid cells;
#     (4) calculate floodwater depth by subtracting topographic elevation from local floodwater elevation at each grid cell within the flooded domain.
# 
# The theory here is very similar to FwDET except step 4 which utilise a geospatial interpolation using sklearn's KNN machine learning algorithm instead of allocating the local floodwater elevation for each grid cell within the flooded domain from its nearest boundary grid cell. This results in a smoother water depth raster and avoids an extra step of smoothing. However, this may cause problems when using a coarse DEM with many outliers at the boundary. The KNN interpolation code is adapted from the skspatial package https://github.com/rosskush/skspatial. It can be computational expensive with large dataset. Testing using larger scale data is underway.
# 
# We have included a run-down of the tool that is demonstrated in the notebook. 
# 
# ## Getting started
# 
# To run this analysis, run all the cells in the notebook, starting with the "Load packages" cell.
# 
# ## Load packages
# 
# Import Python packages that are used for the analysis.
# 


# get_ipython().run_line_magic('matplotlib', 'inline')
# import matplotlib.pyplot as plt
import os
import sys
import time
import rasterio
import numpy as np
from scipy import ndimage
from scipy import interpolate
#from rasterio.warp import reproject, Resampling

# ## Set input variables
#MEMDIR = sys.argv[2]
#FloodExtent_tif = os.path.join(MEMDIR, sys.argv[1].split('/')[-1])#"/datasets/work/lw-mdb-ef/work/Physical/Jin_Teng/wde_rs_dem/WOFSwater_resize.tif"#os.path.join('data', 'FloodExtent_modified.tif')#'WOFS_clip.tif')
FloodExtent_tif = sys.argv[1]
outDir = sys.argv[2]
DEM_tif = os.path.join(outDir, "DEM_resized.tif")#r"/scratch1/ten023/FWDET/SRTM_LIDAR_combined_1sec_WGS84_conformed_to_WOFS.tif"#MDB_dem_reprojected.tif"#os.path.join('data', 'Elevation.tif')#'dem_clip.tif')
ChannelDepth_tif = os.path.join(outDir, "ChannelDepth_resized.tif")#r"/scratch1/ten023/FWDET/MDB_channel_depth_new.tif"
# FloodExtent_3857 = r"/scratch1/ten023/FWDET/MIM_WOFS_Max_water_4326tiles_2011_01_TwoMonthlyMax_CloudGapSlopeMskd_WaterDepth_3857_Steve.tif"
if FloodExtent_tif.find(".gz") == -1:
	WaterDepth_tif = os.path.join(outDir, FloodExtent_tif.split('/')[-1].replace(".tif","_WaterDepth.tif"))
else:
	WaterDepth_tif = os.path.join(outDir,FloodExtent_tif.split('/')[-1].replace(".tif.gz","_WaterDepth.tif"))# "/scratch1/ten023/FWDET/output_wd_idw.tif"#os.path.join('data','output_wd_idw.tif')
WOfS_nodata_value = 200#0
WOfS_dry_value = 0#2
WOfS_wet_value = 1#3


## Read flood extent raster

start_time = time.time()
if FloodExtent_tif.find(".gz") == -1:
	with rasterio.open(FloodExtent_tif) as src:
		flood_extent = np.ma.asarray(src.read(1).astype(np.int8))#src.read(1)
else:
	with rasterio.open(r'/vsigzip/'+ FloodExtent_tif) as src:
		flood_extent = np.ma.asarray(src.read(1).astype(np.int8))#src.read(1)
#del src
wet = np.where(flood_extent==WOfS_wet_value,1,0)
nodata = np.where(flood_extent==WOfS_nodata_value,1,0)
flood_extent = np.ma.masked_where(flood_extent!=WOfS_wet_value, flood_extent, False)
print("--- Read flood extent %s seconds ---" % (time.time() - start_time))


# ## Extract raster boundaries
# ## Changed into outer boundaries for version 2

start_time = time.time()
structure1 = np.ones((3,3))
bufferred = ndimage.binary_dilation(wet, structure=structure1).astype(np.int8)
border = bufferred - wet - nodata
border = np.where(border==1,1,0).astype(np.int8)
# clean memory for next steps
del bufferred, wet, nodata
print("--- Delineate borders %s seconds ---" % (time.time() - start_time))

# ## Read DEM
start_time = time.time()
with rasterio.open(DEM_tif) as src_dem:
    dem = np.ma.asarray(src_dem.read(1, masked = True).astype(np.float))#src_dem.read(1, masked = True)
print("--- Read DEM %s seconds ---" % (time.time() - start_time))

del src_dem

# ## Extract DEM values using the outline
 
start_time = time.time()
dem_extract = border * dem
# clean memory for next steps
del border, dem
print("--- Extract DEM to borders %s seconds ---" % (time.time() - start_time))

# ## Intetpolation using linear interpolation

start_time = time.time()
nrow, ncol = dem_extract.shape
x = np.arange(0, ncol)
y = np.arange(0, nrow)
dem_extract =np.ma.masked_where(dem_extract==0.0, dem_extract)
xx, yy = np.meshgrid(x, y)
# get only the valid values
x1 = xx[~dem_extract.mask]
y1 = yy[~dem_extract.mask]
newarr = dem_extract[~dem_extract.mask]
del dem_extract
GD1 = interpolate.griddata((x1, y1), newarr.ravel(), (xx, yy), method='linear',fill_value=np.nan)
# clean memory for next steps
del newarr, x, y, xx, yy, x1, y1
print("--- Interpolation %s seconds ---" % (time.time() - start_time))

# ## Estimate water depth 
# 
# Substracting ground elevation from interpolated flood water surface elevation

start_time = time.time()
with rasterio.open(DEM_tif) as src_dem:
    dem = np.ma.asarray(src_dem.read(1, masked = True).astype(np.float))#src_dem.read(1, masked = True)
del src_dem

#Interpolated floodwater elevation minus DEM

water_depth = GD1 - dem
del GD1
water_depth[np.less(water_depth, 0., where=~np.isnan(water_depth))] = 0
water_depth[np.logical_or(flood_extent.mask, dem.mask)] = np.nan
del flood_extent, dem
print("--- Substraction %s seconds ---" % (time.time() - start_time))

start_time = time.time()
with rasterio.open(ChannelDepth_tif) as src:
    Channel = np.ma.asarray(src.read(1, masked = True).astype(np.float))
#del src

Channel[np.logical_or(Channel.mask, np.isnan(Channel))]=0
Channel[Channel<0]=0
water_depth[~np.isnan(water_depth)] = water_depth[~np.isnan(water_depth)] + Channel[~np.isnan(water_depth)]
del Channel
print("--- Add channel depth %s seconds ---" % (time.time() - start_time))

# ## Write output
# start_time = time.time()
# with rasterio.open("/scratch1/ten023/FWDET/test_output/MIM_WOFS_Max_water_4326tiles_2011_01_TwoMonthlyMax_CloudGapSlopeMskd_WaterDepth_v2_3857.tif") as src:
    # water_depth = np.ma.asarray(src.read(1, masked = True).astype(np.float))
# print("--- Read output %s seconds ---" % (time.time() - start_time))

start_time = time.time()
with rasterio.open(
    WaterDepth_tif, 'w',
    driver='COG',
    dtype=rasterio.float32,
    count=1,
    nodata=-9999,
    compress='lzw',
    crs = src.crs,
    transform = src.transform,
    width=src.width,
    height=src.height,
	resampling="nearest") as dst:
    dst.write(water_depth.astype(np.float32), indexes=1)
print("--- Write COG output %s seconds ---" % (time.time() - start_time))

del dst

# Reproject to EPSG:3857
# start_time = time.time()
# rasterio version: not working for bilinear resampling

# src2 = rasterio.open(FloodExtent_3857)
# reproj_template = np.ma.asarray(src2.read(1).astype(np.float)) # read reprojection template

# reproject(
        # water_depth,
        # reproj_template,
        # src_transform=src.transform,
        # src_crs=src.crs,
        # src_nodata=src.nodata,
        # dst_transform=src2.transform,
        # dst_crs=src2.crs,
        # dst_nodata=-9999,
        # resampling=Resampling.nearest)
# del src, water_depth

# with rasterio.open(
    # WaterDepth_tif.replace(".tif","_3857.tif"), 'w',
    # driver='COG',
    # dtype=rasterio.float32,
    # count=1,
    # nodata=-9999,
    # compress='lzw',
    # crs = src2.crs,
    # transform = src2.transform,
    # width=src2.width,
    # height=src2.height) as dst:
    # dst.write(reproj_template.astype(np.float32), indexes=1)
# print("--- Preproject and write output %s seconds ---" % (time.time() - start_time))

# del dst

# gdal version
# from osgeo import gdal, ogr, osr, gdalconst
# src_ds = gdal.Open(WaterDepth_tif)
# match_ds = gdal.Open(FloodExtent_3857)

# src_proj = src_ds.GetProjection()
# match_proj = match_ds.GetProjection()
# match_geotrans = match_ds.GetGeoTransform()
# data_type = match_ds.GetRasterBand(1).DataType
# width = match_ds.RasterXSize
# height = match_ds.RasterYSize

# raster_out = WaterDepth_tif.replace(".tif","_3857.tif")
# dst = gdal.GetDriverByName('COG').Create(
	# raster_out, width, height, 1, data_type)
# dst.SetGeoTransform(match_geotrans)
# dst.SetProjection(match_proj)

# gdal.ReprojectImage(src_ds, dst, src_proj, match_proj, gdal.GRA_Bilinear)
# del dst  # Flush



# # convert normal geotiff to COG
# from rio_cogeo.cogeo import cog_translate

# def _translate(src_path, dst_path, profile="webp", profile_options={}, **options):
    # """Convert image to COG."""
    # # Format creation option (see gdalwarp `-co` option)
    # output_profile = cog_profiles.get(profile)
    # output_profile.update(dict(BIGTIFF="IF_SAFER"))
    # output_profile.update(profile_options)

    # # Dataset Open option (see gdalwarp `-oo` option)
    # config = dict(
        # GDAL_NUM_THREADS="ALL_CPUS",
        # GDAL_TIFF_INTERNAL_MASK=True,
        # GDAL_TIFF_OVR_BLOCKSIZE="128",
    # )

    # cog_translate(
        # src_path,
        # dst_path,
        # output_profile,
        # config=config,
        # in_memory=False,
        # quiet=True,
        # **options,
    # )
    # return True
	
# _translate(WaterDepth_tif.replace(".tif","_3857.tif"), WaterDepth_tif.replace(".tif","_3857_COG.tif"), blocksize=512)

# from rasterio.io import MemoryFile
# from rasterio.transform import from_bounds

# from rio_cogeo.cogeo import cog_translate
# from rio_cogeo.profiles import cog_profiles

# with MemoryFile() as memfile:
    # with memfile.open(**src2) as mem:
        # # Populate the input file with numpy array
        # mem.write(reproj_template)

        # dst_profile = cog_profiles.get("deflate")
        # cog_translate(
            # mem,
            # WaterDepth_tif.replace(".tif","_3857_COG_mem.tif"),
            # dst_profile,
            # in_memory=True,
            # quiet=True,
        # )

print("Completed")