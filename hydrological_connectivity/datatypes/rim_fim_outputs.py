class RimFimOutputs():
    """docstring for RimFimOutputs."""

    def __init__(self, mask_location, elevation_location, flow_to_depth, gauges, zone_alias, processing_format_string):
        self.flow_to_depth = flow_to_depth
        self.gauges = gauges
        self.mask_location = mask_location
        self.elevation_location = elevation_location
        self.zone_alias = zone_alias
        self.processing_format_string = processing_format_string

    def first_scene(self):
        return min(self.flow_to_depth.keys())

    def last_scene(self):
        return max(self.flow_to_depth.keys())

    def produce_file(self, identifier, flow_indicator, date_if_relevant=""):
        """The output filename that could be produced as part of analysis

        Args:
            identifier (str): a text string unique to this processing operation
            flow_indicator (int): the flow rounded to the nearest GL/day

        Returns:
            str: The output filename that could be produced as part of analysis
        """
        return self.processing_format_string.format(identifier, date_if_relevant, flow_indicator)

    def __str__(self):
        return "{0} scenes from {1} to {2} GL/day at gauges {3}".format(len(self.flow_to_depth),
                                                                        self.first_scene(), self.last_scene(), str(self.gauges))

    __repr__ = __str__
