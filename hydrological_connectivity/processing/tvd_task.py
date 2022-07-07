import logging
import os
import numpy
import numpy.ma
import rasterio
from rasterio.enums import Resampling
from rasterio.io import DatasetReader
from rasterio.vrt import WarpedVRT
import scipy
import scipy.ndimage
from hydrological_connectivity.datatypes.tvd_outputs import TvdOutputs
import time
import rasterio.mask
import rasterio.warp
from rasterio.windows import from_bounds
import rasterio
from scipy import ndimage
import itertools
from functools import reduce
import scipy.spatial.distance
from sklearn import linear_model
from pyproj import Transformer


class TvdTask():
    """Caculate flood depth using Teng-Vaze-Dutta (TVD) method"""

    def __init__(self, tvd_outputs: TvdOutputs):
        self.WOfS_nodata_value = 0
        self.WOfS_dry_value = 2
        self.WOfS_wet_value = 3

        self.tvd_outputs = tvd_outputs

    def execute(self):

        self.read_dem()
        self.adjust_slope()
        self.read_flood_extent()
        self.save_to_disk()

    def read_dem(self):

        left, bottom, right, top = self.tvd_outputs.region_of_interest_albers.bounds
        logging.info(f"{left} {bottom} {right} {top}")

        with rasterio.open(self.tvd_outputs.dem_path) as src_dem:
            window = from_bounds(
                left, bottom, right, top, src_dem.transform)
            logging.info(f'{window}')
            self.dem_transform = src_dem.window_transform(window)
            self.dem_crs = src_dem.crs
            self.dem_nodata_vals = src_dem.nodatavals
            self.dem_masked = src_dem.read(1, masked=True, window=window)
            self.window_positions = src_dem.index(
                left, top)

        self.dem = self.dem_masked.data
        self.dem[self.dem_masked.mask] = numpy.nan
        self.coords = [Transformer.from_crs("epsg:4326", self.dem_crs).transform(coord[1], coord[0])
                       for coord in self.tvd_outputs.coords]
        logging.info(
            f"Sample points {str(self.tvd_outputs.coords)} translated to {str(self.coords)}")

    def interpolate_gradient(points, heights, cols, rows):
        clf = linear_model.LinearRegression()
        clf.fit(points, heights)

        # All the possible points in the grid
        c = numpy.zeros((len(rows)*len(cols), 2), dtype=int)
        c[:, 0] = numpy.repeat(rows, len(cols))
        c[:, 1] = numpy.tile(cols, len(rows))

        output = clf.predict(c).reshape((len(rows), len(cols)))
        return output

    def adjust_slope(self, final_height_adjustment=0, angle_adjustment=0., interpolation_fn=interpolate_gradient):
        """ Adjust the DEM to account for slope of the river
            E.g.
            FloodExtent_tif = os.path.join('data', 'FloodExtent_modified.tif')
            DEM_tif = os.path.join('data', 'Elevation.tif')
            output_path = os.path.join('data','Adjusted_DEM.tif')

            adjust_slope(DEM_tif, output_path, coords[0], coords[1],0,0)
        Args:
            final_height_adjustment (int, optional): [description]. Defaults to 0.
            angle_adjustment (float, optional): [description]. Defaults to 0.
            interpolation_fn (function, optional): [description]. Defaults to interpolate_gradient.
        """

        # 1) Extract points as close to the coordinates (a) and (b) as possible
        # 2) Get the index of the src_dem that is closest to the coordinates
        with rasterio.open(self.tvd_outputs.dem_path) as src_dem:
            heights = list(src_dem.sample(self.coords))
            grid_positions = [numpy.subtract(src_dem.index(
                coord[0], coord[1]), self.window_positions) for coord in self.coords]

        points = numpy.array(grid_positions)

        original_heights = heights.copy()

        logging.info("Original heights %s" % original_heights)
        point_dist = scipy.spatial.distance.euclidean(points[0], points[1])
        height_difference = original_heights[0] - original_heights[1]
        if height_difference == 0:
            theta = numpy.pi / 2
        else:
            theta = numpy.arctan(point_dist / height_difference)
        logging.info("Gradient angle A -> B %.2f" % numpy.degrees(theta))

        line_count = numpy.max(numpy.abs(points[0] - points[1])) + 1
        line_points = numpy.round(numpy.column_stack([
            numpy.linspace(points[0, 0], points[1, 0], line_count),
            numpy.linspace(points[0, 1], points[1, 1], line_count)
        ])).astype(numpy.int)
        line_heights = []
        for pnt in line_points:
            line_heights.append(self.dem[pnt[0], pnt[1]])
        line_heights = numpy.array(line_heights)

        if numpy.any(numpy.isnan(line_heights)):
            line_points = line_points[~numpy.isnan(line_heights)]
            line_heights = line_heights[~numpy.isnan(line_heights)]
        predicted_heights = interpolation_fn(
            line_points, line_heights, points[:, 1], points[:, 0])
        heights = predicted_heights[[0, 1], [0, 1]]
        logging.info("Predicted heights %s" % heights)
        if angle_adjustment != 0.:
            point_dist = scipy.spatial.distance.euclidean(points[0], points[1])
            height_difference = heights[0] - heights[1]
            if height_difference == 0:
                theta = numpy.radians(angle_adjustment)
                adjacent = point_dist * numpy.tan(theta)
            else:
                theta = numpy.arctan(point_dist / height_difference) + \
                    numpy.radians(angle_adjustment)
                adjacent = height_difference / numpy.tan(theta)
            heights[1] += height_difference - adjacent

        step_size = 20
        min_adjustment = numpy.inf
        max_adjustment = -numpy.inf
        self.adjusted_dem = numpy.empty_like(self.dem)
        self.gradient_dest = numpy.empty_like(self.dem)
        for row_start, column_start in itertools.product(numpy.arange(0, self.dem.shape[0], step_size),
                                                         numpy.arange(0, self.dem.shape[1], step_size)):
            window = (
                (row_start, min(row_start + step_size, self.dem.shape[0])),
                (column_start, min(column_start +
                                   step_size, self.dem.shape[1]))
            )

            rows = numpy.arange(row_start, min(
                row_start + step_size, self.dem.shape[0]))
            cols = numpy.arange(column_start, min(
                column_start + step_size, self.dem.shape[1]))

            src_dem_data = self.dem[slice(*window[0]), slice(*window[1])]

            gradient = interpolation_fn(points, heights, cols, rows)[
                :src_dem_data.shape[0], :src_dem_data.shape[1]]
            min_adjustment = numpy.min([min_adjustment, numpy.min(gradient)])
            max_adjustment = numpy.max([max_adjustment, numpy.max(gradient)])
            interp = (src_dem_data - gradient +
                      numpy.min(heights) + final_height_adjustment)
            write_window = (
                (row_start, row_start + src_dem_data.shape[0]),
                (column_start, column_start + src_dem_data.shape[1])
            )
            # re-nodata incoming nodata
            #interp[reduce(numpy.logical_or, [src_dem_data == f for f in src.nodatavals])] = src.nodatavals[0]
            self.adjusted_dem[slice(*write_window[0]),
                              slice(*write_window[1])] = interp
            self.gradient_dest[slice(*write_window[0]),
                               slice(*write_window[1])] = gradient
        self.adjusted_dem[(numpy.isnan(self.dem))] = numpy.nan

        final_heights = numpy.array(
            [self.adjusted_dem[points[0][0], points[0][1]], self.adjusted_dem[points[1][0], points[1][1]]])

        logging.info("Slope adjusted heights %s" % final_heights)
        point_dist = scipy.spatial.distance.euclidean(points[0], points[1])
        height_difference = final_heights[0] - final_heights[1]
        if height_difference == 0:
            theta = numpy.pi / 2
        else:
            theta = numpy.arctan(point_dist / height_difference)
        logging.info("Gradient angle A -> B %.2f" % numpy.degrees(theta))
        max_adjustment -= numpy.min(heights)
        min_adjustment -= numpy.min(heights)
        logging.info("Maximum adjustment %s, minimum adjustment %s" %
                     (max_adjustment, min_adjustment))

    def read_flood_extent(self):
        start_time = time.time()

        left, bottom, right, top = self.tvd_outputs.region_of_interest_albers.bounds
        logging.info("Open Flood Extent")

        with rasterio.open(self.tvd_outputs.flood_extent_path) as src_wgs84:
            with WarpedVRT(src_wgs84, crs='EPSG:3577', resampling=Resampling.bilinear, transform=self.dem_transform, width=self.dem.shape[1], height=self.dem.shape[0]) as vrt:
                window = from_bounds(
                    left, bottom, right, top, vrt.transform)
                self.flood_extent = vrt.read(1, window=window)

        self.out_mask = self.flood_extent != self.WOfS_wet_value
        wet = numpy.where(self.flood_extent == self.WOfS_wet_value, 1, 0)
        logging.info("--- %s seconds ---" % (time.time() - start_time))
        structure = numpy.ones((3, 3))

        dem = self.adjusted_dem

        # All
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
        # original_dem_path = self.tvd_outputs.output_path.replace(
        #     '.tif', f'_orig_dem.tif')
        # logging.info(f"Saving to disk: {original_dem_path}")
        # with rasterio.open(
        #         original_dem_path, 'w',
        #         driver='COG',
        #         compress='LZW',
        #         dtype=self.adjusted_dem.dtype,
        #         count=1,
        #         crs=self.dem_crs,
        #         nodata=numpy.nan,
        #         transform=self.dem_transform,
        #         width=self.dem.shape[1],
        #         height=self.dem.shape[0],
        #         resampling='average',
        #         overview_resampling='average') as dst:
        #     dst.write(self.dem, indexes=1)

        adjusted_dem_path = self.tvd_outputs.output_path.replace(
            '.tif', f'_adj.tif')
        logging.info(f"Saving to disk: {adjusted_dem_path}")
        with rasterio.open(
                adjusted_dem_path, 'w',
                driver='COG',
                compress='LZW',
                dtype=self.adjusted_dem.dtype,
                count=1,
                crs=self.dem_crs,
                nodata=-9999,
                transform=self.dem_transform,
                width=self.dem.shape[1],
                height=self.dem.shape[0],
                resampling='average',
                overview_resampling='average') as dst:
            dst.write(self.adjusted_dem, indexes=1)

        # gradient_dem_path = self.tvd_outputs.output_path.replace(
        #     '.tif', f'_grad.tif')
        # logging.info(f"Saving to disk: {gradient_dem_path}")
        # with rasterio.open(
        #         gradient_dem_path, 'w',
        #         driver='COG',
        #         compress='LZW',
        #         dtype=self.gradient_dest.dtype,
        #         count=1,
        #         crs=self.dem_crs,
        #         nodata=numpy.nan,
        #         transform=self.dem_transform,
        #         width=self.dem.shape[1],
        #         height=self.dem.shape[0],
        #         resampling='average',
        #         overview_resampling='average') as dst:
        #     dst.write(self.gradient_dest, indexes=1)

        waterdepth_all_path = self.tvd_outputs.output_path.replace(
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

        waterdepth_path = self.tvd_outputs.output_path.replace(
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
