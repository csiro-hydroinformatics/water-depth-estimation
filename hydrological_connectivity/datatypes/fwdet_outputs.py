from hydrological_connectivity.datatypes.hydraulic_model import HydraulicModel

import os.path


class FwdetOutputs():
    """Location of files for fwdet processing"""

    def __init__(self, short_description, flood_extent_path, dem_path, channel_path, hydraulic_model: HydraulicModel, simulation_timespan, region_of_interest_albers, region_of_interest_wgs84, segment_index,  output_path):
        self.short_description = short_description
        self.flood_extent_path = flood_extent_path
        self.dem_path = dem_path
        self.hydraulic_model = hydraulic_model
        self.simulation_timespan = simulation_timespan
        self.region_of_interest_albers = region_of_interest_albers
        self.region_of_interest_wgs84 = region_of_interest_wgs84
        self.output_path = output_path
        self.segment_index = segment_index
        self.channel_path = channel_path

    def exists(self, ext):
        return os.path.isfile(self.output_path)

    def __str__(self):
        return "Flood Extent: {0}, DEM Path: {1} Hydraulic Model: {2} ({3} - {4}) Output: {5}".format(
            self.flood_extent_path, self.dem_path,
            self.hydraulic_model.model_name, str(self.simulation_timespan['start']), str(
                self.simulation_timespan['end']),
            self.output_path)

    __repr__ = __str__
