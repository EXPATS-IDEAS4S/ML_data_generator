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


