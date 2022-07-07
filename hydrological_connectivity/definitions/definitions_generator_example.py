from datetime import datetime, timedelta
import logging
import geopandas

from pytz import timezone
from shapely.geometry import base
from hydrological_connectivity.datatypes import fwdet_outputs, tvd_outputs
from hydrological_connectivity.datatypes.elevation_source import ElevationSource
from hydrological_connectivity.datatypes.hand_outputs import HandOutputs
from hydrological_connectivity.datatypes.hydraulic_model import HydraulicModel
from hydrological_connectivity.datatypes.simple_outputs import SimpleOutputs
from hydrological_connectivity.datatypes.water_observations import WaterObservations
from hydrological_connectivity.datatypes.zone_definition import ZoneDefinition
from hydrological_connectivity.definitions.definitions_generator import DefinitionsGenerator
import os
from dotenv import load_dotenv
load_dotenv()


class DefinitionsGeneratorExample(DefinitionsGenerator):
    """DefinitionsGenerator creates the hydraulic model & zone definitions."""

    def __init__(self, exclude=[]):
        super().__init__(exclude)
        self.exclude = exclude

        self.base_folder = os.environ['INPUT_FOLDER']

        self.global_elevation = ElevationSource(
            self.base_folder + f"{os.path.sep}DEM.tif")
        self.elevation_region = {
            # or a subregion if different dem for each region
            "Murray": self.global_elevation
        }
        self.elevation_location = {
            # or a subregion if different dem for each region
            "Gunbower-Koondrook-Perricoota Forest": self.global_elevation
        }

        kpf_model_name = "Murray"
        # _XX time step where XX starts with 00 from 01/08/2016 and ends with 24 (25/08/2016). They are in daily time steps.
        timezone_est = timezone('Australia/NSW')
        output_date = timezone_est.localize(datetime(2016, 8, 18))
        kpf_model = HydraulicModel(
            kpf_model_name, self.global_elevation,
            {output_date: self.base_folder + f"{os.path.sep}hydraulic_depth.tif"},
            {output_date: self.base_folder + f"{os.path.sep}hydraulic_surface_elevation.tif"})

        self.models = {kpf_model_name: kpf_model}
        self.zones = {kpf_model_name:
                      ZoneDefinition(
                          kpf_model_name, kpf_model, self.base_folder + f'{os.path.sep}segments_albers.shp')
                      }
        timezone_est = timezone('Australia/NSW')
        self.water_observations = WaterObservations({
            timezone_est.localize(datetime(2016, 7, 1)):  # Need to know the date
            self.base_folder + f'{os.path.sep}flood_mask.tif'})

        self.zone_definition_albers_shape = os.environ['ZONE_DEF_ALBERS']
        self.zone_definition_wgs84_shape = os.environ['ZONE_DEF_WGS84']

    def generate(self):
        super().create_model_outputs()
