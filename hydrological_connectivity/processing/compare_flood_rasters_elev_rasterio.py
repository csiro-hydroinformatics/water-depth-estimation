import logging
import numpy
import rasterio
from rasterio.enums import Resampling
from rasterio.io import DatasetReader
from rasterio.vrt import WarpedVRT
from rasterio.windows import from_bounds


class CompareFloodRastersElevRasterIo():
    """ Compare two sources of information about a flood """

    def __init__(self, truth_raster_elev, comparison_raster_depth, elevation_raster, region_of_interest_albers, result_raster, include_all_pixels_as_error=True):
        self.truth_raster = truth_raster_elev
        self.comparison_raster = comparison_raster_depth
        self.elevation_raster = elevation_raster
        self.result_raster = result_raster
        self.region_of_interest_albers = region_of_interest_albers
        self.include_all_pixels_as_error = include_all_pixels_as_error

    def __str__(self):
        return "compare {0} to {1} and produce {2}".format(self.truth_raster, self.comparison_raster, self.result_raster)

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

        # with rasterio.open(self.elevation_raster) as src_dem:
        #    window = from_bounds(
        #        left, bottom, right, top, src_dem.transform)
        #    logging.info(f'{window}')
        #    dem_transform = src_dem.window_transform(window)
        #    dem = src_dem.read(1, masked=True, window=window)

        with rasterio.open(self.elevation_raster) as src_dem_orig:
            with WarpedVRT(src_dem_orig, crs='EPSG:3577', resampling=Resampling.nearest,
                           transform=self.comp_transform, width=self.comparison.shape[1], height=self.comparison.shape[0]) as src_dem:
                window = from_bounds(
                    left, bottom, right, top, src_dem.transform)
                dem = src_dem.read(1, window=window, masked=True)

        with rasterio.open(self.truth_raster) as src_mga:
            with WarpedVRT(src_mga, crs='EPSG:3577', resampling=Resampling.bilinear,
                           transform=self.comp_transform, width=self.comparison.shape[1], height=self.comparison.shape[0]) as vrt:
                window = from_bounds(
                    left, bottom, right, top, vrt.transform)
                self.truth = vrt.read(1, window=window, masked=True)

        if (self.comparison.shape[0] != dem.shape[0]) or (self.comparison.shape[1] != dem.shape[1]):
            logging.warning(
                f"Inconsistent shapes: comparison shape {self.comparison.shape}, dem shape {dem.shape}, truth shape {self.truth.shape} (using dem shape)")
            logging.info(
                f"comparison shape {self.comparison.shape}, transform {self.comp_transform }, window {window}")
            self.comparison = self.comparison[0:dem.shape[0], 0:dem.shape[1]]

        # we have "truth" raster (the hydraulic model output)
        # we have "comparison" raster (the r/s model output)
        # calculate the difference
        # we need to be carefull with no data values
        if self.include_all_pixels_as_error:
            self.truth[self.truth.mask | dem.mask] = numpy.nan
            self.comparison[self.comparison.mask] = numpy.nan

            self.depth_difference = numpy.full_like(self.truth, numpy.nan)

            mask1 = numpy.isnan(self.truth) & ~numpy.isnan(self.comparison)
            dif1 = 0-self.comparison
            self.depth_difference[mask1] = dif1[mask1]
            del dif1
            mask2 = ~numpy.isnan(self.truth) & numpy.isnan(self.comparison)
            self.depth_difference[mask2] = self.truth[mask2] - dem[mask2]
            mask3 = ~numpy.isnan(self.truth) & ~numpy.isnan(self.comparison)
            dif3 = self.truth - (dem + self.comparison)
            self.depth_difference[mask3] = dif3[mask3]
            del dif3
        else:
            self.depth_difference = self.truth - (dem + self.comparison)
            self.depth_difference[numpy.isnan(self.truth)] = numpy.nan
            self.depth_difference[numpy.isnan(self.comparison)] = numpy.nan
            self.depth_difference[numpy.isnan(dem)] = numpy.nan
            self.depth_difference[self.depth_difference < -10000] = numpy.nan
            self.depth_difference[self.depth_difference > 10000] = numpy.nan
            self.depth_difference = self.depth_difference.filled(numpy.nan)

        # save raster
        logging.info(f"Saving to disk: {self.result_raster}")
        with rasterio.open(
                self.result_raster, 'w',
                driver='COG',
                compress='LZW',
                dtype=rasterio.float32,
                count=1,
                crs='EPSG:3577',
                nodata=numpy.nan,
                transform=self.comp_transform,
                width=self.comparison.shape[1],
                height=self.comparison.shape[0],
                resampling='average',
                overview_resampling='average') as dst:
            dst.write(self.depth_difference, indexes=1)

    __repr__ = __str__
