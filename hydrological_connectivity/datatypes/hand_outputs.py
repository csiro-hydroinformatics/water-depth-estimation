from hydrological_connectivity.datatypes.hydraulic_model import HydraulicModel

import os.path
import logging
import pandas


class HandOutputs():
    """Location of files for hand processing"""

    def __init__(self, short_description, flood_extent_path, dem_path, hydraulic_model: HydraulicModel, simulation_timespan,
                 flood_depth, region_of_interest_albers, region_of_interest_wgs84, segment_index, output_path):
        self.short_description = short_description
        self.flood_extent_path = flood_extent_path
        self.dem_path = dem_path
        self.hydraulic_model = hydraulic_model
        self.simulation_timespan = simulation_timespan
        self.flood_depth = flood_depth
        self.region_of_interest_albers = region_of_interest_albers
        self.region_of_interest_wgs84 = region_of_interest_wgs84
        self.segment_index = segment_index
        self.output_path = output_path

    def __hash__(self):
        return hash(self.output_path)

    def __eq__(self, other):
        return self.output_path == other.output_path

    def __ne__(self, other):
        # Not strictly necessary, but to avoid having both x==y and x!=y
        # True at the same time
        return not(self == other)

    def exists(self, accumulation_threshold, ext):
        waterdepth_all_path = self.output_path.replace(
            '.tif', f'_{ext}_{str(accumulation_threshold)}.tif')
        logging.debug(f"Looking for: {waterdepth_all_path}")
        return os.path.isfile(waterdepth_all_path)

    def get_hand_level(hand_level_definition_path, image, date):
        """
        for an image number (0-10) and text date (e.g. 1998-07-01), return a level
        """
        hand_definition = list(pandas.read_csv(
            hand_level_definition_path, dtype=str).T.to_dict(orient='dict').values())
        for record in hand_definition:
            if (record['image'] == image and record['date'] == date):
                return float(record['level'])

        return -1

    def __str__(self):
        return "Flood Extent: {0}, DEM Path: {1} Hydraulic Model: {2} ({3} - {4}) Output: {5}".format(
            self.flood_extent_path, self.dem_path,
            self.hydraulic_model.model_name, str(self.simulation_timespan['start']), str(
                self.simulation_timespan['end']),
            self.output_path)

    __repr__ = __str__
