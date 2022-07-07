

from hydrological_connectivity.datatypes.hydraulic_model import HydraulicModel


class ZoneDefinition():
    """Defines an area of a hydraulic model used as a zone"""

    def __init__(self, zone_name, hydraulic_model, zone_boundary):
        self.zone_name = zone_name
        self.hydraulic_model = hydraulic_model
        self.zone_boundary = zone_boundary

    def __str__(self):
        return "{0}: {1}".format(self.zone_name, self.hydraulic_model)

    __repr__ = __str__
