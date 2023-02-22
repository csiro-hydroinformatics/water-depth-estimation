import numpy
import pandas
from scipy.interpolate import RBFInterpolator
from scipy import interpolate


class TpsInterpolationStrategy():
    """Thin Plate Spline algorithm to interpolate across inundation perimeter"""

    def __init__(self, averaging_constant=60, neighbors=100) -> None:
        self.averaging_constant = averaging_constant
        """averaging constant is the area to assume low surface water elevation difference. For
        example 60 for 25m resolution product or 300 for 5m resolution product"""
        self.neighbors = neighbors
        """the number of neighbors that must be included in the thin plate spline"""

    def interpolate(self, dem_extract):
        """Interpolate - 
        note: for memory reasons this has the side-effect of deleting dem_extract """
        nrow, ncol = dem_extract.shape
        x = numpy.arange(0, ncol)
        y = numpy.arange(0, nrow)
        dem_extract = numpy.ma.masked_where(
            dem_extract == 0.0, dem_extract)

        xx, yy = numpy.meshgrid(x, y)
        # get only the valid values
        x1 = xx[~dem_extract.mask].ravel()
        y1 = yy[~dem_extract.mask].ravel()

        newarr = dem_extract[~dem_extract.mask].ravel()
        del dem_extract

        lumped = numpy.array(
            [(x1+self.averaging_constant//2)//self.averaging_constant,
             (y1+self.averaging_constant//2)//self.averaging_constant, newarr])

        lumped_df = pandas.DataFrame(lumped.T, columns=["X", "Y", "Z"])

        XY_fn = lumped_df.groupby(
            ['X', 'Y']).mean().reset_index().to_numpy()

        coords = XY_fn[:, [0, 1]]
        actual = XY_fn[:, [2]]

        interpolator = RBFInterpolator(
            coords, actual, kernel='thin_plate_spline', smoothing=0, neighbors=self.neighbors)

        entire_region_lumped_coords = numpy.array(
            [(xx.reshape(-1)+self.averaging_constant//2)//self.averaging_constant,
             (yy.reshape(-1)+self.averaging_constant//2)//self.averaging_constant])

        entire_region_lumped_df = pandas.DataFrame(
            entire_region_lumped_coords.T, columns=["X", "Y"])
        del entire_region_lumped_coords

        entire_region_XY = entire_region_lumped_df.groupby(
            ['X', 'Y']).size().reset_index().to_numpy()[:, 0:2]

        del entire_region_lumped_df

        # This next line does not scale well. I expect there is both an unnecessary innefficiency
        # in the scipy libraries and a bug that causes dask not to return results
        GD_regional = interpolator(entire_region_XY)
        del interpolator

        filled = interpolate.griddata(entire_region_XY*self.averaging_constant, GD_regional.ravel(),
                                      (xx, yy), method='linear', fill_value=numpy.nan)

        del xx, yy, GD_regional, entire_region_XY
        return filled
