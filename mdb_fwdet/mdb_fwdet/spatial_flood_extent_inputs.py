from mdb_fwdet.configuration import Configuration
from mdb_fwdet.region import Region
from xarray import DataArray
import rioxarray


class SpatialFloodExtentInputs():
    """Spatial inputs to flood water depth algorithms for a region """

    def __init__(self, mim_array: DataArray, dem: DataArray, channel: DataArray):
        self.mim_array = mim_array
        """ Input flood extent mask for cropped region using multi-index model index codes (nodata = 0, dry = 2, wet = 3) """
        self.dem = dem
        """ Input dem cropped to region (float32) """
        self.channel = channel
        """ Input channel depth cropped to region (float) """

    def mim_input_location(image_date_label) -> str:
        return Configuration.image_date_format_string.format(
            image_date= image_date_label)

    def load_mim_input(image_date_label) -> DataArray:
        image_date_file_location = SpatialFloodExtentInputs.mim_input_location(
            image_date_label)
        xds = rioxarray.open_rasterio(image_date_file_location)
        xds.attrs['image_date'] = image_date_label
        return xds[0]

    WOFS_NODATA_VALUE = 0
    WOFS_DRY_VALUE = 2
    WOFS_WET_VALUE = 3

    def crop(self, region: Region):
        """ Crop spatial flood extent inputs to a specific region"""
        mask_bounds = region.bounding_box
        cropped_mim_array = self.mim_array[mask_bounds[0]:mask_bounds[1], mask_bounds[2]:mask_bounds[3]]
        cropped_dem = self.dem[mask_bounds[0]:mask_bounds[1], mask_bounds[2]:mask_bounds[3]]
        cropped_channel = self.channel[mask_bounds[0]:mask_bounds[1], mask_bounds[2]:mask_bounds[3]]
        return SpatialFloodExtentInputs(cropped_mim_array, cropped_dem, cropped_channel)
