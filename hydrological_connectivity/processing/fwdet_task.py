import logging
import os
import numpy
import rasterio
from rasterio.enums import Resampling
from rasterio.io import DatasetReader
from rasterio.vrt import WarpedVRT
import scipy
import scipy.ndimage
from hydrological_connectivity.datatypes.fwdet_outputs import FwdetOutputs
import time
import rasterio.mask
import rasterio.warp
from rasterio.windows import from_bounds
from scipy import interpolate
from scipy.ndimage import gaussian_filter


class FwdetTask():
    """Caculate flood depth using a fwdet method (Cohen et al. 2017, 2019)"""

    def __init__(self, fwdet_outputs: FwdetOutputs):
        self.WOfS_nodata_value = 0
        self.WOfS_dry_value = 2
        self.WOfS_wet_value = 3

        self.fwdet_outputs = fwdet_outputs
        if "FWDET_INTERP_METHOD" in os.environ:
            self.method = os.environ["FWDET_INTERP_METHOD"]
        else:
            self.method = ""

    def execute(self):
        self.read_dem()
        self.read_flood_extent()
        self.save_to_disk()

    def read_dem(self):
        left, bottom, right, top = self.fwdet_outputs.region_of_interest_albers.bounds
        logging.info(f"{left} {bottom} {right} {top}")

        with rasterio.open(self.fwdet_outputs.dem_path) as src_dem:
            window = from_bounds(
                left, bottom, right, top, src_dem.transform)
            logging.info(f'{window}')
            self.dem_transform = src_dem.window_transform(window)
            self.dem = src_dem.read(1, masked=True, window=window)

    def read_flood_extent(self):
        start_time = time.time()

        left, bottom, right, top = self.fwdet_outputs.region_of_interest_albers.bounds
        logging.info("Open Flood Extent")

        with rasterio.open(self.fwdet_outputs.flood_extent_path) as src_wgs84:
            with WarpedVRT(src_wgs84, crs='EPSG:3577', resampling=Resampling.nearest, transform=self.dem_transform, width=self.dem.shape[1], height=self.dem.shape[0]) as vrt:
                window = from_bounds(
                    left, bottom, right, top, vrt.transform)
                self.flood_extent = numpy.ma.asarray(
                    vrt.read(1, window=window).astype(numpy.int8))  # src.read(1)
        del src_wgs84

        # WORKAROUND FOR floating point arithmetic issue in Narran - extend window by a pixel
        if self.dem.shape != self.flood_extent.shape:
            logging.info(
                f"Shape mismatch (probably rounding error): expecting: {self.dem.shape} got {self.flood_extent.shape}")
            with rasterio.open(self.fwdet_outputs.flood_extent_path) as src_wgs84:
                with WarpedVRT(src_wgs84, crs='EPSG:3577', resampling=Resampling.nearest, transform=self.dem_transform, width=self.dem.shape[1]+1, height=self.dem.shape[0]) as vrt:
                    window = from_bounds(
                        left, bottom, right+5, top, vrt.transform)
                    self.flood_extent = numpy.ma.asarray(
                        vrt.read(1, window=window).astype(numpy.int8))  # src.read(1)
            del src_wgs84
            logging.info(f"New shape {self.flood_extent.shape}")

        not_wet = numpy.where(self.flood_extent == self.WOfS_dry_value, 1, 0)
        nodata = numpy.where(self.flood_extent == self.WOfS_nodata_value, 1, 0)
        self.flood_extent = numpy.ma.masked_where(
            self.flood_extent != self.WOfS_wet_value, self.flood_extent, False)
        print("--- Read flood extent %s seconds ---" %
              (time.time() - start_time))

        # ## Extract raster boundaries

        start_time = time.time()
        structure1 = numpy.ones((3, 3))
        bufferred = scipy.ndimage.binary_dilation(
            not_wet, structure=structure1).astype(numpy.int8)
        border = bufferred - not_wet - nodata
        border = numpy.where(border == 1, 1, 0).astype(numpy.int8)
        # clean memory for next steps
        del bufferred, not_wet, nodata
        print("--- Delineate borders %s seconds ---" %
              (time.time() - start_time))

        start_time = time.time()
        dem_extract = border * self.dem
        # clean memory for next steps
        del border
        print("--- Extract DEM to borders %s seconds ---" %
              (time.time() - start_time))

        # ## Interpolation using linear interpolation

        start_time = time.time()
        nrow, ncol = dem_extract.shape
        x = numpy.arange(0, ncol)
        y = numpy.arange(0, nrow)
        dem_extract = numpy.ma.masked_where(dem_extract == 0.0, dem_extract)
        xx, yy = numpy.meshgrid(x, y)
        # get only the valid values
        x1 = xx[~dem_extract.mask]
        y1 = yy[~dem_extract.mask]
        newarr = dem_extract[~dem_extract.mask]
        del dem_extract

        if self.method == "SMOOTHING":
            GD_nearest = interpolate.griddata((x1, y1), newarr.ravel(),
                                              (xx, yy), method='nearest', fill_value=numpy.nan)
            # Apply a low pass filter
            GD1 = gaussian_filter(GD_nearest, sigma=1)
            # For radius - see https://stackoverflow.com/questions/25216382/gaussian-filter-in-scipy
            # Set sigma/truncate - this default setting would give width of 9 (truncate=4)
            logging.info("Using nearest plus smoothing")
        elif self.method == "RIMFIM":
            # Also try linear trend removal then kriging
            # use lstsq(A,b) from scipy.linalg import lstsq
            # then https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.lstsq.html
            # https://scikit-learn.org/stable/modules/gaussian_process.html#gaussian-process-regression-gpr
            # import sklearn
            # gp = sklearn.gaussian_process.GaussianProcessRegressor(kernel=your_chosen_kernel)
            # gp.fit(X, y)
            logging.exception(f"Have not implemented RIMFIM method")
        else:
            GD1 = interpolate.griddata((x1, y1), newarr.ravel(),
                                       (xx, yy), method='linear', fill_value=numpy.nan)
        # clean memory for next steps
        del newarr, x, y, xx, yy, x1, y1
        print("--- Interpolation %s seconds ---" % (time.time() - start_time))

        # ## Estimate water depth
        #
        # Substracting ground elevation from interpolated flood water surface elevation

        # Interpolated floodwater elevation minus DEM

        water_depth = GD1 - self.dem
        del GD1
        water_depth[numpy.less(water_depth, 0., where=~
                               numpy.isnan(water_depth))] = 0
        water_depth[numpy.logical_or(
            self.flood_extent.mask, self.dem.mask)] = numpy.nan
        print("--- Substraction %s seconds ---" % (time.time() - start_time))

        if self.fwdet_outputs.channel_path is not None:
            start_time = time.time()
            with rasterio.open(self.fwdet_outputs.channel_path) as channel_wgs84:
                with WarpedVRT(channel_wgs84, crs='EPSG:3577', resampling=Resampling.bilinear, transform=self.dem_transform, width=self.dem.shape[1], height=self.dem.shape[0]) as vrt:
                    window = from_bounds(
                        left, bottom, right, top, vrt.transform)
                    channel = numpy.ma.asarray(
                        vrt.read(1, window=window).astype(numpy.float))
            del channel_wgs84, vrt

            channel[numpy.logical_or(channel.mask, numpy.isnan(channel))] = 0
            channel[channel < 0] = 0
            water_depth[~numpy.isnan(water_depth)] = water_depth[~numpy.isnan(
                water_depth)] + channel[~numpy.isnan(water_depth)]
            del channel
            print("--- Add channel depth %s seconds ---" %
                  (time.time() - start_time))
        self.water_depth = water_depth

    def save_to_disk(self):
        waterdepth_path = self.fwdet_outputs.output_path
        logging.info(f"Saving to disk: {waterdepth_path}")
        with rasterio.open(
                waterdepth_path, 'w',
                driver='COG',
                compress='LZW',
                dtype=self.water_depth.dtype,
                count=1,
                crs='EPSG:3577',
                nodata=numpy.nan,
                transform=self.dem_transform,
                width=self.dem.shape[1],
                height=self.dem.shape[0],
                resampling='average',
                overview_resampling='average') as dst:
            dst.write(self.water_depth, indexes=1)

    def save_input_to_disk(self):
        waterdepth_path = self.fwdet_outputs.output_path.replace(
            ".tif", "_input_flood_map.tif")
        logging.info(f"Saving to disk: {waterdepth_path}")
        with rasterio.open(
                waterdepth_path, 'w',
                driver='COG',
                compress='LZW',
                dtype=self.flood_extent.dtype,
                count=1,
                crs='EPSG:3577',
                nodata=numpy.nan,
                transform=self.dem_transform,
                width=self.flood_extent.shape[1],
                height=self.flood_extent.shape[0],
                resampling='average',
                overview_resampling='average') as dst:
            dst.write(self.flood_extent, indexes=1)

        waterdepth_path = self.fwdet_outputs.output_path.replace(
            ".tif", "_input_elev.tif")
        logging.info(f"Saving to disk: {waterdepth_path}")
        with rasterio.open(
                waterdepth_path, 'w',
                driver='COG',
                compress='LZW',
                dtype=self.dem.dtype,
                count=1,
                crs='EPSG:3577',
                nodata=numpy.nan,
                transform=self.dem_transform,
                width=self.dem.shape[1],
                height=self.dem.shape[0],
                resampling='average',
                overview_resampling='average') as dst:
            dst.write(self.dem, indexes=1)
