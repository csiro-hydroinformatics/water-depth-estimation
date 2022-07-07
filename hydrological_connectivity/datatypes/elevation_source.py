class ElevationSource():
    """docstring for ElevationSource."""

    def __init__(self, elevation_filename):
        self.elevation_filename = elevation_filename

    def __str__(self):
        return self.elevation_filename

    __repr__ = __str__
