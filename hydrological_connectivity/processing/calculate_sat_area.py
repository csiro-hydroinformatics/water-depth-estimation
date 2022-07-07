import logging
import numpy
import rasterio
from rasterio.enums import Resampling
from rasterio.io import DatasetReader
from rasterio.vrt import WarpedVRT
from rasterio.windows import from_bounds


class CalculateSatArea():
    """ Calculate the volume of hydraulic model output """

    def __init__(self, extent_raster, zone, zone_transform, region_of_interest_gda94, segment_number, in_albers=False):
        self.extent_raster = extent_raster
        self.segment_number = segment_number
        self.region_of_interest_gda94 = region_of_interest_gda94
        self.in_albers = in_albers
        self.zone = zone
        self.zone_transform = zone_transform
        self.dry_total_extent = numpy.nan
        self.wet_total_extent = numpy.nan
        self.nodata_total_extent = numpy.nan

        self.WOfS_nodata_value = 0
        self.WOfS_dry_value = 2
        self.WOfS_wet_value = 3

    def __str__(self):
        return f"calculate depth of {self.extent_raster}"

    def execute(self):
        left, bottom, right, top = self.region_of_interest_gda94.bounds
        # self.zone_raster = ...\segments_v3_albers.tif"
        # with rasterio.open(self.zone_raster) as src_zone:
        #     window = from_bounds(
        #         left, bottom, right, top, src_zone.transform)
        #     logging.info(f'{window}')
        #     zone_transform = src_zone.window_transform(window)
        #     zone = src_zone.read(1, masked=True, window=window)

        # with rasterio.open(self.extent_raster) as src_wgs84:
        #    with WarpedVRT(src_wgs84, crs='EPSG:4326', resampling=Resampling.bilinear, transform=self.zone_transform, width=self.zone.shape[1], height=self.zone.shape[0]) as vrt:
        #        window = from_bounds(
        #            left, bottom, right, top, vrt.transform)
        #        extent = vrt.read(1, masked=True,  window=window)

        with rasterio.open(self.extent_raster) as src_extent_raster:
            window = from_bounds(
                left, bottom, right, top, src_extent_raster.transform)
            # logging.info(f'{window}')
            extent = src_extent_raster.read(1, window=window)

        # if extent.shape[0] == 0:
        #    return

        dry = numpy.where((extent == self.WOfS_dry_value)
                          & (self.zone == self.segment_number), 1, 0)
        wet = numpy.where((extent == self.WOfS_wet_value)
                          & (self.zone == self.segment_number), 1, 0)
        nodata = numpy.where((extent == self.WOfS_nodata_value)
                             & (self.zone == self.segment_number), 1, 0)
        self.dry_total_extent = numpy.nansum(dry)
        self.wet_total_extent = numpy.nansum(wet)
        self.nodata_total_extent = numpy.nansum(nodata)

    __repr__ = __str__
