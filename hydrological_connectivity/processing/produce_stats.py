import logging
import numpy
import rasterio
from rasterio.enums import Resampling
from rasterio.io import DatasetReader
from rasterio.vrt import WarpedVRT
from rasterio.windows import from_bounds


class ProduceStats():
    """ Produce stats from a comparison raster """

    def __init__(self, comparison_raster, truth_raster, zone_raster,  segment_number, region_of_interest_albers):
        self.comparison_raster = comparison_raster
        self.truth_raster = truth_raster
        self.segment_number = segment_number
        self.zone_raster = zone_raster
        self.region_of_interest_albers = region_of_interest_albers

    def __str__(self):
        return "produce stats for {0}".format(self.comparison_raster)

    def execute(self):
        left, bottom, right, top = self.region_of_interest_albers.bounds
        logging.info("Open Flood Extent")

        with rasterio.open(self.comparison_raster) as src_comparison:
            window = from_bounds(
                left, bottom, right, top, src_comparison.transform)
            logging.info(f'{window}')
            self.comp_transform = src_comparison.window_transform(window)
            self.comparison = src_comparison.read(
                1, masked=True, window=window)

        with rasterio.open(self.zone_raster) as src_zone:
            with WarpedVRT(src_zone, crs='EPSG:3577', resampling=Resampling.nearest,
                           transform=self.comp_transform, width=self.comparison.shape[1], height=self.comparison.shape[0]) as vrt:
                window = from_bounds(
                    left, bottom, right, top, vrt.transform)
                zone = vrt.read(1, window=window, masked=True)

        # we have "truth" raster (the hydraulic model output)
        # we have "comparison" raster (the r/s model output)
        # calculate the difference
        # we need to be carefull with no data values

        self.comparison.mask[(zone == self.segment_number)
                             & ~self.comparison.mask] = False
        self.comparison.mask[zone != self.segment_number] = True

        with rasterio.open(self.truth_raster) as src_truth:
            with WarpedVRT(src_truth, crs='EPSG:3577', resampling=Resampling.nearest,
                           transform=self.comp_transform, width=self.comparison.shape[1], height=self.comparison.shape[0]) as vrt:
                window = from_bounds(
                    left, bottom, right, top, vrt.transform)
                self.truth = vrt.read(1, window=window, masked=True)

        self.truth.mask[(zone == self.segment_number)
                        & ~self.truth.mask & ~self.comparison.mask] = False
        self.truth.mask[zone != self.segment_number] = True
        # numpy.quantile(self.comparison, )

    __repr__ = __str__
