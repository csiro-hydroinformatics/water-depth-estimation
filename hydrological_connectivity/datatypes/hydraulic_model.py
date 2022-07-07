import numpy

from datetime import datetime, timedelta
from time import time


class HydraulicModel():
    """HydraulicModel defines the properties of a hydraulic model such as name."""

    def __init__(self, model_name, elevation_source, depth_outputs, elevation_outputs):
        """Create a HydraulicModel description

        Args:
            model_name (str): Name attributed to the model
            elevation_source (str): The source of elevation data for the model (path)
            depth_outputs (Dict[datetime, str]): List of paths representing depth outputs on particular dates
            elevation_outputs (Dict[datetime, str]): List of paths representing elevation outputs on particular dates
        """
        self.model_name = model_name
        self.depth_outputs = depth_outputs
        self.elevation_outputs = elevation_outputs
        self.elevation_source = elevation_source

    def start_simulation(self):
        return min(self.depth_outputs.keys())

    def end_simulation(self):
        return max(self.depth_outputs.keys())

    def timestep(self):
        keys = list(self.depth_outputs.keys())
        if len(keys) == 1:
            return datetime(1900, 1, 1) - datetime(1900, 1, 2)
        keys.sort()

        return numpy.min(numpy.subtract(keys[1:len(keys)], keys[0:len(keys)-1]))
        # return keys[1] - keys[0]

    def get_contiguous_date_ranges(self):
        time_step = self.timestep()
        ranges = []
        sentinel_depth = datetime(1900, 1, 1)  # not-found value
        last_depth = sentinel_depth
        first_depth = sentinel_depth
        for depth_date in self.depth_outputs.keys():
            if last_depth + time_step != depth_date:  # there is a break, depth_date is the start of the new break
                if last_depth != sentinel_depth:  # this is not the first timestamp
                    ranges.append({
                        'start': first_depth,
                        'end': last_depth,
                        'timestep': time_step
                    }
                    )
                first_depth = depth_date
            last_depth = depth_date
        ranges.append({
            'start': first_depth,
            'end': last_depth,
            'timestep': time_step
        }
        )
        return ranges

    def __str__(self):
        return "{0} with {1} depth and {2} elevation references from {3} to {4}".format(
            self.model_name, len(self.depth_outputs), len(
                self.elevation_outputs),
            self.start_simulation(), self.end_simulation())

    __repr__ = __str__
