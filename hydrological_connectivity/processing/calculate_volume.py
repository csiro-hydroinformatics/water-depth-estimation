import logging
import numpy
import rasterio
from rasterio.enums import Resampling
from rasterio.io import DatasetReader
from rasterio.vrt import WarpedVRT
from rasterio.windows import from_bounds


class CalculateVolume():
    """ Calculate the volume of hydraulic model output """

    def __init__(self, depth_raster, zone, zone_transform, region_of_interest_albers, segment_number, in_albers=False):
        self.depth_raster = depth_raster
        self.segment_number = segment_number
        self.region_of_interest_albers = region_of_interest_albers
        self.in_albers = in_albers
        self.zone = zone
        self.zone_transform = zone_transform

    def __str__(self):
        return f"calculate depth of {self.depth_raster}"

    def execute(self):
        left, bottom, right, top = self.region_of_interest_albers.bounds

        # self.zone_raster = r"...\segments_v3_albers.tif"
        # with rasterio.open(self.zone_raster) as src_zone:
        #     window = from_bounds(
        #         left, bottom, right, top, src_zone.transform)
        #     logging.info(f'{window}')
        #     zone_transform = src_zone.window_transform(window)
        #     zone = src_zone.read(1, masked=True, window=window)

        if self.in_albers:
            with rasterio.open(self.depth_raster) as src_depth_raster:
                window = from_bounds(
                    left, bottom, right, top, src_depth_raster.transform)
                logging.info(f'{window}')
                depth = src_depth_raster.read(1, masked=True, window=window)
        else:
            with rasterio.open(self.depth_raster) as src_mga:
                with WarpedVRT(src_mga, crs='EPSG:3577', resampling=Resampling.bilinear,
                               transform=self.zone_transform, width=self.zone.shape[1], height=self.zone.shape[0]) as vrt:
                    window = from_bounds(
                        left, bottom, right, top, vrt.transform)
                    depth = vrt.read(1, window=window, masked=True)

        depth.mask[(self.zone == self.segment_number) & ~depth.mask] = False
        depth.mask[self.zone != self.segment_number] = True
        self.total_depth = numpy.nansum(depth)

    __repr__ = __str__
