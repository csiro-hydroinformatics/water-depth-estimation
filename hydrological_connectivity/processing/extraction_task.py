from hydrological_connectivity.datatypes.elevation_source import ElevationSource
from hydrological_connectivity.datatypes.zone_definition import ZoneDefinition


class ExtractionTask():
    """Extract the DEM for the region of interest"""

    def __init__(self, target_filename, elevation_source: ElevationSource, zone_definition: ZoneDefinition):
        self.target_filename = target_filename
        self.zone_definition = zone_definition
        self.elevation_source = elevation_source

    def run():
        zone_definition = ZoneDefinition()
