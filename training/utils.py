"""
Collection of functions that do basic operations on the data, such initializing logger, 
check if time is valid, parse timestamps etc
date: 2024-06-20
author: Claudia Acquistapace
"""

from training.config import *
import logging
import os
import xarray as xr
import numpy as np
import pdb


def is_valid_time(timestamp, month, day, hour):
    """
    Checks if the given timestamp falls within the specified month, day, and hour ranges of the config 
    """
    return (
        MONTH_START <= month <= MONTH_END and
        HOUR_START <= hour < HOUR_END and
        DAY_START <= day <= DAY_END 

    )

def parse_timestamp(timestamp):
    """
    Extracts hour, month, day, year, and minute from a timestamp.
    """
    # extract hour from timestamp
    hour = str(timestamp).split('T')[1][0:2]
    month = str(timestamp).split('T')[0].split('-')[1]
    day = str(timestamp).split('T')[0].split('-')[2]
    yyyy = str(timestamp).split('T')[0].split('-')[0]
    minute = str(timestamp).split('T')[1][3:5]

    return hour, month, day, yyyy, minute


def write_to_missing_timeseries_log(ds_crop, timestamp, ind_start_time, crops_affected, today_str, log_path):
    """
    Writes the given timestamp and index to a log file for missing time series.
    Input
    - ds_crop: the dataset crop that is being processed
    - timestamp: the timestamp that is being processed
    - ind_start_time: the index of the timestamp in the dataset
    - crops_affected: a string indicating which crops are affected by the missing time series (e.g., 'both' if both the current and next time series are affected)
    - today_str: the current date as a string, used for naming the log file
    - log_path: the path where the log file is stored
    
    Output
    None, but writes to a log file named 'log_skipped_timeseries.txt' in
    the specified log path.
    """
    if crops_affected == 'both':
        with open(f'{log_path}/{today_str}_log_skipped_timeseries.txt', 'a') as log_file:
            time_missing = timestamp
            hour_miss, month_miss, day_miss, yyyy_miss, minute_miss = parse_timestamp(time_missing)
            month_miss, day_miss, hour_miss = int(month_miss), int(day_miss), int(hour_miss)
            log_file.write(f"date: {yyyy_miss}-{month_miss:02d}-{day_miss:02d} {hour_miss}:{minute_miss} for index {ind_start_time} - crops affected: {crops_affected}\n")
    return


def search_all_nans_or_outside_range(ds_crop):
    """
    function to check if:
    - variables in input except RR are all NaN in the crop
    - any variable in the crop has values outside the specified range defined in config.py

    input: 
    - ds_crop: xarray dataset containing the crop to check
    output:
    - is_all_nan_ds: bool, True if all variables except RR are NaN in the crop, False otherwise
    - is_outside_range: bool, True if any variable in the crop has values outside the specified range, False otherwise

    author: Claudia Acquistapace
    email. claudia.acquistapace@unipd.it
    date: 15/02/2026
    """

    # select all data vars except RR_de and RR_it for the check of all NaN values
    vars = [var for var in ds_crop.data_vars if var not in ['RR_de', 'RR_it']]
    is_all_nan_ds = all([xr.DataArray.isnull(ds_crop[var]).all() for var in vars])

    # check for values outside the specified range
    vars_all = [var for var in ds_crop.data_vars if var in CLOUD_PRM] # check all CLOUD_PRM
    value_min = [vmin for i, vmin in enumerate(VALUE_CHECK_MIN) if CLOUD_PRM[i] in vars_all]
    value_max = [vmax for i, vmax in enumerate(VALUE_CHECK_MAX) if CLOUD_PRM[i] in vars_all]
    is_outside_range = any(
        [((ds_crop[var] < vmin) | (ds_crop[var] > vmax)).any()
        for var, vmin, vmax in zip(vars_all, value_min, value_max)]
    )
    
    return is_all_nan_ds, is_outside_range


            
            
def resample_on_lat_lon_MTG(ds):
    """
    Load original latitude and longitude coordinate grid for a channel.

    Parameters:
        folder (Path): Base directory containing coordinate files.
        channel (str): Data channel name.

    Returns:
        xarray.Dataset: Dataset containing latitude and longitude arrays.
    """
    coord_file = f"/home/claudia/auxiliary_data/20250507_MTG_fci_hrfi_lats_lons.nc"
    ds_coords = xr.open_dataset(coord_file)
    lat = ds_coords['lat_105'].values
    lon = ds_coords['lon_105'].values

     # Debug: print coordinate info
    print("--- DEBUG: ds.lat ---")
    print(getattr(ds, 'lat', 'No lat attribute'))
    if 'lat' in ds.coords:
        print("ds.lat min:", ds['lat'].values.min(), "max:", ds['lat'].values.max(), "dtype:", ds['lat'].values.dtype)
    else:
        print("ds has no 'lat' coordinate")
    print("--- DEBUG: ds.lon ---")
    print(getattr(ds, 'lon', 'No lon attribute'))
    if 'lon' in ds.coords:
        print("ds.lon min:", ds['lon'].values.min(), "max:", ds['lon'].values.max(), "dtype:", ds['lon'].values.dtype)
    else:
        print("ds has no 'lon' coordinate")
    print("--- DEBUG: target lat ---")
    print("lat min:", lat.min(), "max:", lat.max(), "dtype:", lat.dtype)
    print("--- DEBUG: target lon ---")
    print("lon min:", lon.min(), "max:", lon.max(), "dtype:", lon.dtype)

    # Restrict interpolation to overlapping region
    lat_min, lat_max = ds['lat'].values.min(), ds['lat'].values.max()
    lon_min, lon_max = ds['lon'].values.min(), ds['lon'].values.max()
    lat_overlap = lat[(lat >= lat_min) & (lat <= lat_max)]
    lon_overlap = lon[(lon >= lon_min) & (lon <= lon_max)]
    if lat_overlap.size == 0 or lon_overlap.size == 0:
        print("WARNING: No overlap between source and target lat/lon. Interpolation will result in all NaNs.")
    else:
        print(f"Overlapping lat: {lat_overlap.min()} to {lat_overlap.max()} ({lat_overlap.size} values)")
        print(f"Overlapping lon: {lon_overlap.min()} to {lon_overlap.max()} ({lon_overlap.size} values)")

    ds_resampled = ds.interp(lat=lat_overlap, lon=lon_overlap, method='nearest')

    # Debug: check IR_108 after interpolation
    if 'IR_108' in ds_resampled:
        arr = ds_resampled['IR_108'].values
        print(f"IR_108 after interp: shape={arr.shape}, nan count={np.isnan(arr).sum()}, total={arr.size}")
    else:
        print("IR_108 not found in ds_resampled.")

    # resample ds on the lat-lon grid of MTG
    return ds_resampled