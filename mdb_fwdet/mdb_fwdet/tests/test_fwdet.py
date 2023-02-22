import logging
import unittest
from pathlib import Path
import os
import numpy as np
import xarray as xr

from mdb_fwdet.bimonth_time_range import BimonthTimeRange
from mdb_fwdet.delaunay_triangulation_interpolation_strategy import DelaunayTriangulationInterpolationStrategy
from mdb_fwdet.flood_depth_engine import FloodDepthEngine
from mdb_fwdet.fwdet_estimator import FwdetEstimator
from mdb_fwdet.kriging_interpolation_strategy import KrigingInterpolationStrategy
from mdb_fwdet.region import Region
from mdb_fwdet.region_definition import RegionDefinition
from mdb_fwdet.spatial_flood_extent_inputs import SpatialFloodExtentInputs
from mdb_fwdet.tps_interpolation_strategy import TpsInterpolationStrategy

logging.getLogger().setLevel('INFO')


class TestFwdetInterp(unittest.TestCase):

    def test_bimonth_time_range(self):
        bimonth_time_range = BimonthTimeRange(
            start='2022-01-01', end='2022-12-31')

        self.assertEqual(len(bimonth_time_range.full_date_range), 6,
                         "Expecting 6 entries for 2022, got {len(bimonth_time_range.full_date_range)}")
        logging.info(bimonth_time_range.full_date_range)

        self.assertEqual(bimonth_time_range.full_date_range, ['2022_01',
                         '2022_03', '2022_05', '2022_07', '2022_09', '2022_11'])

    def generate_mock_spatial_inputs() -> SpatialFloodExtentInputs:
        # Create 25x25 bowl dem (Elliptic Paraboloid)
        # z = c * (x^2/a^2 + y^2/b^2) using meshgrid
        x = np.arange(-12.5, 12.5, 1)
        y = np.arange(-12.5, 12.5, 1)
        xx, yy = np.meshgrid(x, y)
        dem = 1*((xx**2)/(4**2)+(yy**2)/(4**2))

        # Create 6x6 circular flood extent in 25x25 grid

        flood_mask = np.where(dem < 0.7, SpatialFloodExtentInputs.WOFS_WET_VALUE,
                              SpatialFloodExtentInputs.WOFS_DRY_VALUE)

        # Create 25x25 zeros for channel
        channel_depth = np.full_like(dem, np.nan)

        dem_xr = xr.DataArray(dem,
                              coords={'y': y, 'x': x},
                              dims=["y", "x"])

        flood_mask_xr = xr.DataArray(flood_mask,
                                     coords={'y': y, 'x': x},
                                     dims=["y", "x"])

        channel_depth_xr = xr.DataArray(channel_depth,
                                        coords={'y': y, 'x': x},
                                        dims=["y", "x"])

        mock_spatial_inputs = SpatialFloodExtentInputs(
            flood_mask_xr, dem_xr, channel_depth_xr)
        return mock_spatial_inputs

    def test_spatial_crop(self):
        mock_spatial_inputs = TestFwdetInterp.generate_mock_spatial_inputs()
        mock_region = Region(0, (0, 25, 0, 25))
        cropped_spatial_inputs = mock_spatial_inputs.crop(mock_region)

        logging.info(mock_spatial_inputs.dem)

        self.assertTrue(np.array_equal(mock_spatial_inputs.dem.to_numpy(),
                                       cropped_spatial_inputs.dem.to_numpy()), "Should be same data - DEM")
        self.assertTrue(np.array_equal(mock_spatial_inputs.mim_array.to_numpy(),
                                       cropped_spatial_inputs.mim_array.to_numpy()), "Should be same data - Flood Extent")
        self.assertTrue(np.array_equal(mock_spatial_inputs.channel.to_numpy(),
                                       cropped_spatial_inputs.channel.to_numpy(), True), "Should be same data - Channel")

    def test_fwdet_estimator_tps(self):
        mock_spatial_inputs = TestFwdetInterp.generate_mock_spatial_inputs()
        mock_region = Region(0, (0, 25, 0, 25))
        tps_interpolation_strategy = TpsInterpolationStrategy(1, 7)

        fwdet_estimator = FwdetEstimator(tps_interpolation_strategy)
        water_depth = fwdet_estimator.calculate(
            mock_spatial_inputs, [mock_region])
        logging.info(str(water_depth.to_numpy()))

    def test_fwdet_estimator_kriging(self):
        mock_spatial_inputs = TestFwdetInterp.generate_mock_spatial_inputs()
        mock_region = Region(0, (0, 25, 0, 25))

        kriging_interpolation_strategy = KrigingInterpolationStrategy(1)
        fwdet_estimator = FwdetEstimator(kriging_interpolation_strategy)
        water_depth = fwdet_estimator.calculate(
            mock_spatial_inputs, [mock_region])

        logging.info(str(water_depth.to_numpy()))

    def test_fwdet_estimator_delaunay(self):
        mock_spatial_inputs = TestFwdetInterp.generate_mock_spatial_inputs()
        mock_region = Region(0, (0, 25, 0, 25))

        delaunay_interpolation_strategy = DelaunayTriangulationInterpolationStrategy()
        fwdet_estimator = FwdetEstimator(delaunay_interpolation_strategy)
        water_depth = fwdet_estimator.calculate(
            mock_spatial_inputs, [mock_region])
        logging.info(str(water_depth.to_numpy()))

    def test_fwdet_engine(self):
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

        result_list = flood_depth_engine.calculate()
        self.assertEqual(len(result_list.values()), 4,
                         "Should be four depth rasters")

        whole_of_region_depth = flood_depth_engine.merge_results_into_one_raster(
            result_list)

        mock_global_region = Region(0, (0, 25, 0, 25))
        global_water_depth = fwdet_estimator.calculate(
            mock_spatial_inputs, [mock_global_region])

        print(str(whole_of_region_depth.to_numpy()[12:25, 0:25]))
        print(str(global_water_depth.to_numpy()[12:25, 0:25]))
        self.assertTrue(np.array_equal(whole_of_region_depth.to_numpy()[12:25, 0:25],
                                       global_water_depth.to_numpy()[12:25, 0:25], True), "Data for the lower half should be the same - compute by region vs compute altogether")

        self.assertTrue(not (np.array_equal(whole_of_region_depth.to_numpy()[0:12, 0:25],
                                            global_water_depth.to_numpy()[0:12, 0:25], True)), "Data for the lower half should be the same - compute by region vs compute altogether")


if __name__ == '__main__':
    unittest.main()
