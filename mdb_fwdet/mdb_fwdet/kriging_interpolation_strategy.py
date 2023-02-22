import numpy
import pandas
from scipy import interpolate
from sklearn.gaussian_process.kernels import RBF
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.linear_model import LinearRegression


class KrigingInterpolationStrategy():
    """Strategy for interpolating across perimeter of wet polygons using ordinary kriging"""

    def __init__(self, averaging_constant=60) -> None:
        self.averaging_constant = averaging_constant
        """averaging constant is the area to assume low surface water elevation difference. For
        example 60 for 25m resolution product or 300 for 5m resolution product"""

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
        XY_fn_nan = lumped_df.groupby(
            ['X', 'Y']).mean().reset_index().to_numpy()

        # TODO - I suspect there is a problem with treatments of nulls
        XY_fn = XY_fn_nan[~numpy.isnan(XY_fn_nan[:, 2])]

        coords = XY_fn[:, [0, 1]]
        actual = XY_fn[:, [2]]
        reg = LinearRegression().fit(coords, actual)
        # logging.info(
        #    f"Fitted linear regression (score = {reg.score(coords, actual)}) with coefficients: {reg.coef_} and intercept: {reg.intercept_}")
        linear_estimates = reg.predict(coords)
        residual = actual - linear_estimates
        # 72x90m = 6480m which is an average radial basis range from rimfim
        radial_basis_function = RBF(72/4)
        gp = GaussianProcessRegressor(kernel=radial_basis_function)
        gp.fit(coords, residual)

        entire_region_lumped_coords = numpy.array(
            [(xx.reshape(-1)+self.averaging_constant//2)//self.averaging_constant,
             (yy.reshape(-1)+self.averaging_constant//2)//self.averaging_constant])
        entire_region_lumped_df = pandas.DataFrame(
            entire_region_lumped_coords.T, columns=["X", "Y"])
        entire_region_XY = entire_region_lumped_df.groupby(
            ['X', 'Y']).size().reset_index().to_numpy()[:, 0:2]
        linear_prediction = reg.predict(entire_region_XY)
        residual_prediction = gp.predict(entire_region_XY)

        prediction = linear_prediction.ravel() + residual_prediction.ravel()

        del linear_prediction, residual_prediction

        filled = interpolate.griddata(entire_region_XY*self.averaging_constant, prediction.ravel(),
                                      (xx, yy), method='nearest', fill_value=numpy.nan)
        del xx, yy, reg, gp, entire_region_XY, prediction
        return filled
