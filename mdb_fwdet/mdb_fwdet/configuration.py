class Configuration():
    """Helper class defining the locations of files used for processing fwdet"""
    bucket = 'bucket-name'
    prefix = 'FWDET/v3.6/4326'

    # Available at https://data.csiro.au/collection/csiro:50243
    region_raster_location = f'/vsis3/{bucket}/FWDET/SpatialInputs/MDB_Sub_Div_23zone_1sec.tif'

    # Available at https://doi.org/10.25919/5n0m-1682
    dem_raster_location = f'/vsis3/{bucket}/FWDET/SpatialInputs/SRTM_LIDAR_combined_1sec_WGS84_conformed_to_WOFS_v2022_48592x51668.tif'

    # Available at https://data.csiro.au/collection/csiro:50243
    # MDB_permanent_water_correction and MDB_channel_depth_SA_SetZero_COG are synonymous
    # channel_raster_location = f'/vsis3/{bucket}/FWDET/SpatialInputs/MDB_channel_depth_SA_SetZero_COG.tif'
    channel_raster_location = f'/vsis3/{bucket}/FWDET/SpatialInputs/MDB_permanent_water_correction.tif'

    input_cache_location = f's3://{bucket}/FWDET/SpatialInputs/FwDET_inputs_v3_4.zarr'

    reporting_time_zone = "Australia/Canberra"

    save_file_format_string = r'FwDET_v3_TPS_{image_date}.tif'
    image_date_format_string = f"s3://{bucket}/FWDET/MIM_V3/MIM_WOFS_SnowMasked2_LS9/MIM_WOFS_V3_{{image_date}}_WATER.tif"

    output_time_zone = "Australia/Canberra"
