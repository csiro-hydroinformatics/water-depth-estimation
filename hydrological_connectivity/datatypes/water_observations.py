from datetime import datetime

from typing import Dict


class WaterObservations():
    """WaterObservation maps dates to the remote sensed grids of water classification"""

    def __init__(self, date_to_observation_file: Dict[datetime, str]):
        """ date_to_observation_file is a dictionary of the start-time of MIMS image to the actual file
        """
        self.date_to_observation_file = date_to_observation_file

    def get_closest_date(self, needle):
        comparison = {abs(candidate_date - needle).days: candidate_date for candidate_date
                      in self.date_to_observation_file.keys()}
        closest = min(comparison.keys())
        return comparison[closest]

    def __str__(self):
        return str(self.date_to_observation_file)
