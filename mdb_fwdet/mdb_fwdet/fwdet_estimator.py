from mdb_fwdet.region import Region
from mdb_fwdet.spatial_flood_extent_inputs import SpatialFloodExtentInputs
import numpy as np
import time
import rioxarray
import dask.array as da
from dask_image import ndmorph
import xarray


class FwdetEstimator():
    """Estimate the flood depth across a floodplain using Cohen's FwDET"""

    def __init__(self, interpolation_strategy):
        self.interpolation_strategy = interpolation_strategy
        """Method for interpolating between points on the perimeter of flooded areas"""
        self.verbose = False
        """Print debugging information"""


    def calculate(self, spatial_flood_extent_inputs: SpatialFloodExtentInputs, region: Region) -> xarray.DataArray:
        """Calculate flood depth"""
        self.spatial_flood_extent_inputs = spatial_flood_extent_inputs
        """Spatial inputs to fwdet - flood extent, dem, etc."""

        start_time = time.time()

        if self.verbose:
            print("Calculating FwDET...")

        wet = da.where(spatial_flood_extent_inputs.mim_array ==
                       SpatialFloodExtentInputs.WOFS_WET_VALUE, 1, 0)
        nodata = da.where(
            spatial_flood_extent_inputs.mim_array == SpatialFloodExtentInputs.WOFS_NODATA_VALUE, 1, 0)

        # ## Extract raster boundaries (code from Jin)
        if self.verbose:
            print("Extracting mim extent boundaries...")
        structure1 = np.ones((3, 3))

        bufferred = ndmorph.binary_dilation(
            wet, structure=structure1).astype(np.int8)
        border = bufferred - wet - nodata
        #border = da.where(border == 1, 1, 0).astype(np.int8)
        border = da.where(border == 1, 1, 0)
        # clean memory for next steps
        del bufferred, nodata, wet
        if self.verbose:
            print("--- %s seconds ---" % round(time.time() - start_time))
            start_time = time.time()

        # # ## Extract DEM values using the outline (code from Jin)
        if self.verbose:
            print("Extracting dem values for boundary outline...")

        dem_extract = border * \
            spatial_flood_extent_inputs.dem

        # clean memory for next steps
        del border,  # dem
        if self.verbose:
            print("--- %s seconds ---" % round(time.time() - start_time))
            start_time = time.time()

        # Intetpolation using linear interpolation
        if self.verbose:
            print("Interpolating...")

        filled = self.interpolation_strategy.interpolate(dem_extract)
        del dem_extract

        if self.verbose:
            print("--- %s seconds ---" % round(time.time() - start_time))
            start_time = time.time()

        # Subtracting ground elevation from interpolated flood water surface elevation
        # Interpolated floodwater elevation minus DEM
        if self.verbose:
            print("Subtracting dem...")
        water_depth = filled - spatial_flood_extent_inputs.dem
        wet = da.where(spatial_flood_extent_inputs.mim_array ==
                       SpatialFloodExtentInputs.WOFS_WET_VALUE, 1, 0)
        dry = da.where(spatial_flood_extent_inputs.mim_array ==
                       SpatialFloodExtentInputs.WOFS_DRY_VALUE, 1, 0)
        water_depth = xarray.where(wet == 1, water_depth, np.nan)
        del filled, spatial_flood_extent_inputs.dem, wet

        if self.verbose:
            print("--- %s seconds ---" % round(time.time() - start_time))
            start_time = time.time()

        if self.verbose:
            print("Adding channel depth...")
        spatial_flood_extent_inputs.channel = xarray.where(
            np.isnan(spatial_flood_extent_inputs.channel), 0, spatial_flood_extent_inputs.channel)
        water_depth = xarray.where(
            ~np.isnan(water_depth), water_depth + spatial_flood_extent_inputs.channel, np.nan)
        del spatial_flood_extent_inputs.channel
        water_depth = xarray.where(
            water_depth <= 0, 0.001, water_depth)  # minimum depth = 1
        water_depth = xarray.where(
            water_depth > 65.534, 65.534, water_depth)  # maximum depth = 65534
        water_depth = xarray.where(
            np.isnan(water_depth), 65.535, water_depth)  # nodata = 65535
        water_depth = xarray.where(dry == 1, 0, water_depth)  # dry = 0
        water_depth = np.rint(water_depth*1000).astype(np.uint16)

        if self.verbose:
            print("--- %s seconds ---" % round(time.time() - start_time))
            print("Completed.")

        water_depth.attrs['region'] = region
        return water_depth
