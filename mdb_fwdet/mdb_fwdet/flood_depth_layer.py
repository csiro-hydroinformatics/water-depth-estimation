import time
from time import gmtime
import logging
import pytz
from datetime import datetime

from mdb_fwdet.configuration import Configuration
from mdb_fwdet.delaunay_triangulation_interpolation_strategy import DelaunayTriangulationInterpolationStrategy
from mdb_fwdet.tps_interpolation_strategy import TpsInterpolationStrategy
from mdb_fwdet.flood_depth_engine import FloodDepthEngine
from mdb_fwdet.fwdet_estimator import FwdetEstimator
from mdb_fwdet.geotiff_utils import GeotiffUtils
from mdb_fwdet.region_definition import RegionDefinition
from mdb_fwdet.spatial_flood_extent_inputs import SpatialFloodExtentInputs

from dask.distributed import wait


class FloodDepthLayer():
    """A flood depth layer"""

    def __init__(self, image_date: str, spatial_raster_inputs, mdb_region_bounds_list):
        self.image_date = image_date
        self.spatial_raster_inputs = spatial_raster_inputs
        self.mdb_region_bounds_list = mdb_region_bounds_list

    def generate(self, client):
        """Generate a flood depth layer using the dask client"""
        start_time = time.time()
        logging.info(
            f'1 - starting query for: {self.image_date} - {datetime.now().astimezone(pytz.timezone(Configuration.output_time_zone))}')

        regions = RegionDefinition(
            self.mdb_region_bounds_list, self.spatial_raster_inputs.input_dataset['regions'])

        #interpolation_strategy = DelaunayTriangulationInterpolationStrategy()
        
        interpolation_strategy = TpsInterpolationStrategy()
        fwdet_estimator = FwdetEstimator(interpolation_strategy)

        mim_input = SpatialFloodExtentInputs.load_mim_input(self.image_date)
        spatial_inputs = self.spatial_raster_inputs.get_spatial_flood_extents(
            mim_input)

        flood_depth_engine = FloodDepthEngine(
            spatial_inputs,
            regions,
            fwdet_estimator)

        result_list = flood_depth_engine.calculate_dask(client)

        elapsed_time = time.time() - start_time
        new_start_time = time.time()
        logging.info(
            f'2 - running calculate_dask for: {self.image_date} -  {time.strftime("%H:%M:%S", gmtime(elapsed_time))}')

        self.whole_of_region_depth_future = flood_depth_engine.merge_results_into_one_raster_dask(client,
                                                                                                  result_list)

        elapsed_time = time.time() - new_start_time
        logging.info(
            f'3 - running merge_results_into_one_raster for: {self.image_date} -  {time.strftime("%H:%M:%S", gmtime(elapsed_time))}')

    def save(self, client, bucket: str, prefix: str, save_file_format_string: str):
        """Save the flood depth layer to the selected location on s3 based on bucket/prefix & format strings"""
        start_time = time.time()
        result = GeotiffUtils.save_geotiff(
            client, self.whole_of_region_depth_future, bucket, prefix, save_file_format_string.format(image_date = self.image_date))
        wait(result)
        elapsed_time = time.time() - start_time
        logging.info(
            f'4 - running save for: {self.image_date} -  {time.strftime("%H:%M:%S", gmtime(elapsed_time))}')
