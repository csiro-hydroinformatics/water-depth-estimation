import numpy as np
import xarray


class DelaunayTriangulationInterpolationStrategy():
    """Interpolate the depth of inundation using delaunay triangulation of perimeter pixels"""

    def __init__(self):
        pass

    def interpolate(self, dem_extract):
        dem_extract = xarray.where(
            dem_extract == 0, np.nan, dem_extract)
        dem_extract.rio.write_nodata(np.nan, encoded=True, inplace=True)
        dem_extract.rio.write_crs(4326, inplace=True)
        filled = dem_extract.rio.interpolate_na(method='linear')
        return filled
