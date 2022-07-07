import logging
import numpy
import rasterio
from rasterio.enums import Resampling
from rasterio.io import DatasetReader
from rasterio.vrt import WarpedVRT
from rasterio.windows import from_bounds
from pyproj import Transformer


class CalculateHydraulicLevel():
    """ Calculate the level at a point in a hydraulic model output """

    def __init__(self, depth_raster, coords):
        self.depth_raster = depth_raster
        self.coords = coords
        self.heights = []

    def __str__(self):
        return f"calculate depth of {self.depth_raster}"

    def execute(self):
        with rasterio.open(self.depth_raster) as src_mga:
            transformed_coords = [Transformer.from_crs("epsg:4326", src_mga.crs).transform(coord[1], coord[0])
                                  for coord in self.coords]
            self.heights = list(src_mga.sample(transformed_coords))

    __repr__ = __str__
