from xarray import DataArray
import xarray
from typing import Dict, List
from mdb_fwdet.configuration import Configuration
from mdb_fwdet.fwdet_estimator import FwdetEstimator
from mdb_fwdet.region import Region
from mdb_fwdet.region_definition import RegionDefinition
from mdb_fwdet.spatial_flood_extent_inputs import SpatialFloodExtentInputs
from mdb_fwdet.tps_interpolation_strategy import TpsInterpolationStrategy
from mdb_fwdet.spatial_input_helper import SpatialInputHelper
from dask.distributed import wait
import numpy as np
import logging

class FloodDepthEngine():
    """Calculate flood depths"""

    def __init__(self, spatial_inputs: SpatialFloodExtentInputs, region_definition: RegionDefinition, estimator):
        self.spatial_inputs = spatial_inputs
        self.region_definition = region_definition
        self.estimator = estimator

    def output_name(image_date):
        save_file_name = Configuration.save_file_format_string.format(
            image_date=image_date)
        return save_file_name



    def output_exists(s3, image_date):
        output_name = FloodDepthEngine.output_name(image_date)
        full_url = f"s3://{Configuration.bucket}/{Configuration.prefix}/{output_name}"
        logging.info(full_url)
        return s3.exists(full_url)

    def calculate(self) -> Dict[Region, DataArray]:
        depth_by_region: Dict[Region, DataArray] = {}
        for region in self.region_definition.region_bounds:
            cropped_spatial_inputs = self.spatial_inputs.crop(
                region)
            region_depth = self.estimator.calculate(
                cropped_spatial_inputs, region)
            depth_by_region[region] = region_depth

        return depth_by_region

    def merge_results_into_one_raster(self, depth_by_region: Dict[Region, DataArray]):
        region_template = self.region_definition.region_grid.copy().astype(np.uint16)
        whole_of_region_depth = region_template.copy()
        for (region, fwdet) in depth_by_region.items():
            whole_of_region_depth = FloodDepthEngine.update_in_place(
                region, fwdet, whole_of_region_depth)
        return whole_of_region_depth

    def update_in_place(region: Region, fwdet: DataArray, whole_of_region_depth: DataArray):
        mask_bounds = region.bounding_box
        whole_of_region_depth[mask_bounds[0]:mask_bounds[1],
                              mask_bounds[2]:mask_bounds[3]] = fwdet.values

        return whole_of_region_depth

    def calculate_dask(self, client) -> Dict[Region, DataArray]:
        depth_by_region: Dict[Region, DataArray] = {}
        for region in self.region_definition.region_bounds:
            cropped_spatial_inputs = self.spatial_inputs.crop(
                region)
            # logging.info(f"dem shape: {cropped_spatial_inputs.dem.shape}")
            # logging.info(f"mim_array shape: {cropped_spatial_inputs.mim_array.shape}")
            # logging.info(f"channel shape: {cropped_spatial_inputs.channel.shape}")

            dem = client.scatter(cropped_spatial_inputs.dem)
            mim_array = client.scatter(cropped_spatial_inputs.mim_array)
            channel = client.scatter(cropped_spatial_inputs.channel)

            cropped_spatial_inputs = client.scatter(cropped_spatial_inputs)

            region_depth_task = client.submit(self.estimator.calculate,cropped_spatial_inputs, region)
            depth_by_region[region] = region_depth_task

        # Can wait on list (can not wait on generic enumerable such as dictionary.values())
        wait_results = wait(list(depth_by_region.values()))

        return depth_by_region

    def merge_results_into_one_raster_dask(self, client, depth_by_region: Dict[Region, DataArray]):
        region_template = self.region_definition.region_grid.copy().astype(np.uint16)
        client.scatter(region_template, hash=False)
        whole_of_region_depth = client.submit(
            xarray.core.dataarray.DataArray.copy, region_template)

        # logging.info(f'region_template shape = {region_template.shape}')
        for (region, fwdet) in depth_by_region.items():
            
            # logging.info(f'fwdet shape = {client.submit(lambda a: a.shape, fwdet).result()}')
            
            whole_of_region_depth = client.submit(FloodDepthEngine.update_in_place_dask,
                                                  region, fwdet, region_template, whole_of_region_depth)
            
        wait(whole_of_region_depth)
        logging.info(f"Merge status was: {whole_of_region_depth.status}")
        if (whole_of_region_depth.status == 'error'):
            logging.error(whole_of_region_depth.exception())
        return whole_of_region_depth

    def update_in_place_dask(region: Region, fwdet: DataArray, region_template: DataArray, whole_of_region_depth: DataArray):
        basis = region_template.copy().astype(np.uint16)

        mask_bounds = region.bounding_box
        basis[mask_bounds[0]:mask_bounds[1],
                              mask_bounds[2]:mask_bounds[3]] = fwdet.values

        revised_whole_of_region_depth = xarray.where(region_template==region.region_number+1, basis, whole_of_region_depth)

        return revised_whole_of_region_depth

