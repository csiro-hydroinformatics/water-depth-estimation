from datetime import datetime
from time import time
from dask.distributed import Client
from mdb_fwdet.bimonth_time_range import BimonthTimeRange
from mdb_fwdet.configuration import Configuration
from mdb_fwdet.flood_depth_layer import FloodDepthLayer
from mdb_fwdet.geotiff_utils import GeotiffUtils
from mdb_fwdet.spatial_flood_extent_inputs import SpatialFloodExtentInputs
from mdb_fwdet.spatial_input_helper import SpatialInputHelper
from mdb_fwdet.tests.test_fwdet import TestFwdetInterp
import logging
import unittest
import numpy as np

from mdb_fwdet.delaunay_triangulation_interpolation_strategy import DelaunayTriangulationInterpolationStrategy
from mdb_fwdet.flood_depth_engine import FloodDepthEngine
from mdb_fwdet.fwdet_estimator import FwdetEstimator
from mdb_fwdet.region import Region
from mdb_fwdet.region_definition import RegionDefinition
import s3fs

from mdb_fwdet.dask_install_worker_plugin import DaskInstallWorkerPlugin

from dask.distributed import wait
from time import strftime
from dask.distributed import Client
from dask_gateway import Gateway
import dask
from datacube.utils.aws import configure_s3_access
import os
logging.getLogger().setLevel('INFO')
import uuid 
from time import sleep, gmtime

class TestFwdetDaskInterp(unittest.TestCase):

    def setup_small_client():
        client = Client()  # set up local cluster on your laptop
        return client

    def teardown_small_client(client):
        client.close()

    def setup_large_cluster():
        dask.config.set({"array.slicing.split_large_chunks": False})
        dask.config.set({"distributed.scheduler.worker-ttl": "10 mins"})

        gateway = Gateway()
        options = gateway.cluster_options()
        # display(options)
        options.node_selection = "worker8x"
        options.worker_cores = 15
        options.worker_threads = 2
        options.worker_memory = 42

        # options.node_selection = 'worker'
        # options.worker_cores = 4
        # options.worker_threads = 4
        # options.worker_memory = 16

        clusters = gateway.list_clusters()
        if not clusters:
            logging.info("Creating new cluster. Please wait for this to finish.")
            cluster = gateway.new_cluster(cluster_options=options)
        else:
            logging.info(
                f"An existing cluster was found. Connected to cluster \033[1m{clusters[0].name}\033[0m"
            )
            cluster = gateway.connect(clusters[0].name)
        logging.info(cluster)
        min_number_of_workers = 23
        max_number_of_workers = 23


        # Adaptive scaling
        cluster.adapt(minimum=min_number_of_workers, maximum=max_number_of_workers)
        client = cluster.get_client()
        # client.wait_for_workers(n_workers=min_number_of_workers)
        logging.info(client)
        return (cluster, client)

    def teardown_large_cluster(cluster, client):
        client.close()
        cluster.shutdown()

    def test_save_geotiff(self):
        mock_spatial_inputs = TestFwdetInterp.generate_mock_spatial_inputs()
        client = TestFwdetDaskInterp.setup_small_client()
        logging.info(f"Saving s3://{Configuration.bucket}/{Configuration.prefix}/...test_dem.tif")
        result = GeotiffUtils.save_geotiff(
            client, mock_spatial_inputs.dem, Configuration.bucket, Configuration.prefix, "test_dem.tif")
        wait(result)
        status = result.status
        logging.info(f"Result of geotiff save '{status}'")
        self.assertTrue(status!='error', "Error raised when saving geotiff, see the test python test logs.")

    def test_fwdet_engine_dask(self):
        mock_spatial_inputs = TestFwdetInterp.generate_mock_spatial_inputs()
        mock_region_list = RegionDefinition.dict_to_regions(
            RegionDefinition.MOCK_REGIONS)
        mock_region_grid = RegionDefinition.generate_mock_spatial_array(mock_region_list,
                                                                        mock_spatial_inputs.channel)
        mock_regions = RegionDefinition(mock_region_list, mock_region_grid)

        delaunay_interpolation_strategy = DelaunayTriangulationInterpolationStrategy()
        fwdet_estimator = FwdetEstimator(delaunay_interpolation_strategy)

        flood_depth_engine = FloodDepthEngine(
            mock_spatial_inputs, mock_regions, fwdet_estimator)

        client = TestFwdetDaskInterp.setup_small_client()

        result_list = flood_depth_engine.calculate_dask(client)
        self.assertEqual(len(result_list.values()), 4,
                         "Should be four depth rasters")

        whole_of_region_depth_future = flood_depth_engine.merge_results_into_one_raster_dask(client,
                                                                                             result_list)

        whole_of_region_depth = whole_of_region_depth_future.result()

        mock_global_region = Region(0, (0, 25, 0, 25))
        global_water_depth = fwdet_estimator.calculate(
            mock_spatial_inputs, [mock_global_region])

        print(str(whole_of_region_depth.to_numpy()[12:25, 0:25]))
        print(str(global_water_depth.to_numpy()[12:25, 0:25]))
        self.assertTrue(np.array_equal(whole_of_region_depth.to_numpy()[12:25, 0:25],
                                       global_water_depth.to_numpy()[12:25, 0:25], True), "Data for the lower half should be the same - compute by region vs compute altogether")

        self.assertTrue(not (np.array_equal(whole_of_region_depth.to_numpy()[0:12, 0:25],
                                            global_water_depth.to_numpy()[0:12, 0:25], True)), "Data for the lower half should be the same - compute by region vs compute altogether")
        TestFwdetDaskInterp.teardown_small_client(client)

    def test_file_exists(self):     
        configure_s3_access()
        s3 = s3fs.S3FileSystem()
        image_date ='2005_05'
        if FloodDepthEngine.output_exists(s3, image_date):
            logging.info("exists")
        else:
            logging.info("does not exist")

    def test_fwdet_prebuild_inputs(self):
        client = TestFwdetDaskInterp.setup_small_client()
        mdb_region_bounds_list = RegionDefinition.dict_to_regions(
                RegionDefinition.MDB_REGIONS)
        spatial_raster_inputs = SpatialInputHelper(Configuration.input_cache_location)  # (lazy) loads data
        TestFwdetDaskInterp.teardown_small_client(client)

    def test_local_ls(self):
        logging.info(os.listdir())

    

    def test_push_package(self):
        (cluster, client) = TestFwdetDaskInterp.setup_large_cluster()
        
        DaskInstallWorkerPlugin.install_package(client, [r"/home/jovyan/MDB_FwDET/dist/mdb_fwdet-1.0.17-py3-none-any.whl"]) # use wheel
        

    def test_fwdet_large_process(self):
        (cluster, client) = TestFwdetDaskInterp.setup_large_cluster()
        client.wait_for_workers(n_workers=23)
        DaskInstallWorkerPlugin.install_package(client, [r"/home/jovyan/MDB_FwDET/dist/mdb_fwdet-1.0.17-py3-none-any.whl"]) # use wheel

        try:
            start = '1988-01-01'
            #end = '2022-06-30'
            #start = '2021-11-01'
            end = '2022-12-31'
            bimonth_time_range = BimonthTimeRange(start=start, end=end)
            full_date_range = bimonth_time_range.full_date_range

            # Read in the extent
            start_time = time()
            very_start_time = time()
            logging.info("Loading inputs...")

            mdb_region_bounds_list = RegionDefinition.dict_to_regions(
                RegionDefinition.MDB_REGIONS)
            spatial_raster_inputs = SpatialInputHelper(Configuration.input_cache_location)  # (lazy) loads data

            logging.info("--- %s seconds ---" % (time() - start_time))

            run_list = full_date_range # [0:1]  # Full range 0:207
            # run_list.reverse() # from 206 to zero
            logging.info(str(np.array(run_list)))

            s3 = s3fs.S3FileSystem()

            for image_date in run_list:
                if FloodDepthEngine.output_exists(s3, image_date):
                    logging.info(
                        f"Exists already - skipping: {SpatialFloodExtentInputs.mim_input_location(image_date)}")
                    continue

                start_time = time()

                flood_depth_layer = FloodDepthLayer(
                    image_date, spatial_raster_inputs, mdb_region_bounds_list)
                flood_depth_layer.generate(client)
                flood_depth_layer.save(
                    client, Configuration.bucket, Configuration.prefix, Configuration.save_file_format_string)

                elapsed_time = time() - start_time
                logging.info(
                    f'Total time for: {image_date} -  {strftime("%H:%M:%S", gmtime(elapsed_time))}')
                
                if not(FloodDepthEngine.output_exists(s3, image_date)):
                    logging.error(
                        f"Exiting, Failed to produce: {SpatialFloodExtentInputs.mim_input_location(image_date)}")
                    break

            elapsed_time = time() - very_start_time
            logging.info(
                f'Total time for entire run: {image_date} -  {strftime("%H:%M:%S", gmtime(elapsed_time))}')
        finally:
            # logging.info(client.get_worker_logs())
            TestFwdetDaskInterp.teardown_large_cluster(cluster, client) 

if __name__ == '__main__':
    unittest.main()
