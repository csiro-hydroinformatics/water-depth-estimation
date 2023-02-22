from typing import Union
from dask import delayed
from boto3 import client
from datacube.utils.aws import configure_s3_access
import rioxarray
from datacube.utils.cog import to_cog
from xarray import DataArray
from dask.distributed import Client
from distributed.client import Future


class GeotiffUtils():
    """GeotiffUtils provides extensions/helpers for exporting DaskArrays to s3"""

    def s3write(data, bucket_name, key_name):
        configure_s3_access()
        client("s3").put_object(Body=data, Bucket=bucket_name,
                                Key=key_name, ACL="bucket-owner-full-control")

    def add_georef(xarray_raster: Union[DataArray, Future]):
        import rioxarray
        from datacube.utils.geometry import assign_crs
        bandless = xarray_raster.drop_vars('band', errors='ignore')
        bandless.rio.write_crs("EPSG:4326", inplace=True)
        geoboxed_raster = assign_crs(bandless)
        return geoboxed_raster

    def save_geotiff(client: Client, floodwater_depth_array: Union[DataArray, Future], bucket_name: str, key_prefix: str, save_file_name: str):
        s3write_delayed = delayed(GeotiffUtils.s3write)
        add_georef_delayed = delayed(GeotiffUtils.add_georef)

        georef_result = add_georef_delayed(floodwater_depth_array)
        dl = s3write_delayed(to_cog(georef_result, nodata=65535),
                                          bucket_name, key_prefix + "/" + save_file_name)
        result = client.compute(dl, fifo_timeout=0)
        return result
