import logging
import os
import numpy
import rasterio
from rasterio.enums import Resampling
from rasterio.io import DatasetReader
from rasterio.vrt import WarpedVRT
import scipy
import scipy.ndimage
from hydrological_connectivity.datatypes.simple_outputs import SimpleOutputs
import time
import rasterio.mask
import rasterio.warp
from rasterio.windows import from_bounds


class SimpleTask():
    """Caculate flood depth using a simplistic method"""

    def __init__(self, simple_outputs: SimpleOutputs):
        self.WOfS_nodata_value = 0
        self.WOfS_dry_value = 2
        self.WOfS_wet_value = 3

        self.simple_outputs = simple_outputs

    def execute(self):
        self.read_dem()
        self.read_flood_extent()
        self.save_to_disk()

    def read_dem(self):
        left, bottom, right, top = self.simple_outputs.region_of_interest_albers.bounds
        logging.info(f"{left} {bottom} {right} {top}")

        with rasterio.open(self.simple_outputs.dem_path) as src_dem:
            window = from_bounds(
                left, bottom, right, top, src_dem.transform)
            logging.info(f'{window}')
            self.dem_transform = src_dem.window_transform(window)
            self.dem_masked = src_dem.read(1, masked=True, window=window)

        self.dem = self.dem_masked.data
        self.dem[self.dem_masked.mask] = numpy.nan

    def read_flood_extent(self):
        start_time = time.time()

        left, bottom, right, top = self.simple_outputs.region_of_interest_albers.bounds
        logging.info("Open Flood Extent")

        with rasterio.open(self.simple_outputs.flood_extent_path) as src_wgs84:
            with WarpedVRT(src_wgs84, crs='EPSG:3577', resampling=Resampling.nearest, transform=self.dem_transform, width=self.dem.shape[1], height=self.dem.shape[0]) as vrt:
                window = from_bounds(
                    left, bottom, right, top, vrt.transform)
                self.flood_extent = vrt.read(1, window=window)

        self.out_mask = self.flood_extent != self.WOfS_wet_value
        wet = numpy.where(self.flood_extent == self.WOfS_wet_value, 1, 0)
        logging.info("--- %s seconds ---" % (time.time() - start_time))
        structure = numpy.ones((3, 3))

        dem = self.dem

        wet_dem_roi = dem[(wet == 1) & (~numpy.isnan(dem))]
        mean = numpy.mean(wet_dem_roi)
        std = numpy.std(wet_dem_roi)
        min = numpy.min(wet_dem_roi)
        max = mean + 2 * std
        logging.info(
            f"The estimated maximum water height is {max}m from mean {mean} + 2 * stdev of {std} (min was {min})")
        max2 = numpy.max(wet_dem_roi)
        if (max2 < max):
            logging.info(
                f"The maximum water height is {max2}m - using that instead")
            max = max2
        self.water_depth_a = max - dem
        self.water_depth_a[self.water_depth_a < 0] = 0
        self.water_depth_a[self.out_mask | numpy.isnan(dem)] = numpy.nan

        wet_non_nan = numpy.where(
            (self.flood_extent == self.WOfS_wet_value) & (~numpy.isnan(dem)), 1, 0)
        groups, num_ids = scipy.ndimage.label(wet_non_nan, structure=structure)
        group_ids = numpy.arange(0, num_ids + 1)

        # Individual
        groups_mean = scipy.ndimage.mean(dem, groups, group_ids)
        groups_std = scipy.ndimage.standard_deviation(
            dem, groups, group_ids)
        # groups_max = scipy.ndimage.maximum(dem, groups, group_ids)
        groups_max = groups_mean+2*groups_std
        self.water_depth_i = numpy.array(
            [groups_max[x] for x in groups]) - dem
        self.water_depth_i[self.water_depth_i < 0] = 0
        self.water_depth_i[self.out_mask | numpy.isnan(dem)] = numpy.nan

    def save_to_disk(self):
        waterdepth_all_path = self.simple_outputs.output_path.replace(
            '.tif', f'_all.tif')
        logging.info(f"Saving to disk: {waterdepth_all_path}")
        with rasterio.open(
                waterdepth_all_path, 'w',
                driver='COG',
                compress='LZW',
                dtype=self.water_depth_a.dtype,
                count=1,
                crs='EPSG:3577',
                nodata=numpy.nan,
                transform=self.dem_transform,
                width=self.dem.shape[1],
                height=self.dem.shape[0],
                resampling='average',
                overview_resampling='average') as dst:
            dst.write(self.water_depth_a, indexes=1)

        waterdepth_path = self.simple_outputs.output_path.replace(
            '.tif', f'_ind.tif')
        logging.info(f"Saving to disk: {waterdepth_path}")
        with rasterio.open(
                waterdepth_path, 'w',
                driver='COG',
                compress='LZW',
                crs='EPSG:3577',
                dtype=self.water_depth_i.dtype,
                count=1,
                nodata=numpy.nan,
                transform=self.dem_transform,
                width=self.dem.shape[1],
                height=self.dem.shape[0],
                resampling='average',
                overview_resampling='average') as dst:
            dst.write(self.water_depth_i, indexes=1)
