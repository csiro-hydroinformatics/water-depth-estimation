import xarray
from xarray import DataArray
import rioxarray
import numpy
import xarray
import s3fs
from mdb_fwdet.configuration import Configuration
from mdb_fwdet.spatial_flood_extent_inputs import SpatialFloodExtentInputs
import logging
import boto3
from botocore.errorfactory import ClientError
import pickle 

class SpatialInputHelper():
    """Load and cache the spatial inputs"""

    def __init__(self, cache_location):
        self.s3 = s3fs.S3FileSystem(anon=False, s3_additional_kwargs={
            "ACL": "bucket-owner-full-control"})
        
        if self.s3.exists(cache_location):
            logging.info(f"Using cached inputs")
            self.input_dataset: xarray.Dataset = xarray.open_zarr(
                cache_location)
        else:
            logging.info(f"Loading new inputs")
            self.input_dataset: xarray.Dataset = self._load_from_rasters()
            self._save_rasters(self.input_dataset, cache_location)

    def _load_from_rasters(self) -> xarray.Dataset:

        regions = rioxarray.open_rasterio(
            Configuration.region_raster_location, chunks=(1, 4944, 4944))
        regions.name = 'regions'
        regions_int32 = regions[0].astype(numpy.int32)
        regions_nonan_uint16 = xarray.where(
            regions_int32 == regions_int32.attrs['_FillValue'], 65535, regions_int32).astype(numpy.uint16)

        dem = rioxarray.open_rasterio(
            Configuration.dem_raster_location, chunks=(1, 4944, 4944))
        dem.name = 'dem'

        channel = rioxarray.open_rasterio(
            Configuration.channel_raster_location, chunks=(1, 4944, 4944))
        channel.name = 'channel'
        my_dataset = xarray.merge(objects=[regions_nonan_uint16, dem[0], channel[0]], compat='override',
                                  join='override', fill_value=65535, combine_attrs='drop').chunk({'x': 4944, 'y': 4944})
        my_dataset = my_dataset.rename({'x': 'longitude', 'y': 'latitude'})
        # my_dataset = my_dataset.drop_vars('band', errors='ignore')

        my_dataset.regions.attrs = regions_nonan_uint16.attrs
        my_dataset.dem.attrs = dem.attrs
        my_dataset.channel.attrs = channel.attrs

        logging.info(my_dataset)

        return my_dataset

    def _save_rasters(self, my_dataset: xarray.Dataset, filename: str):
        self.s3.invalidate_cache()
        s3_store = s3fs.S3Map(root=filename, s3=self.s3, check=False)
        z = my_dataset.chunk({"longitude": 4944, "latitude": 4944}).to_zarr(s3_store, mode="w", compute=True, encoding={
            "regions": {"dtype": "uint16"}, "dem": {"dtype": "float32"}, "channel": {"dtype": "float64"}})

    def get_spatial_flood_extents(self, mim_array: DataArray):
        return SpatialFloodExtentInputs(mim_array, self.input_dataset.dem, self.input_dataset.channel)

    def get_regions(self) -> DataArray:
        return self.regions
