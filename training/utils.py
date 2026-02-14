"""
Collection of functions that do basic operations on the data, such initializing logger, 
check if time is valid, parse timestamps etc
date: 2024-06-20
author: Claudia Acquistapace
"""

from training.config import *
import logging
import os


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


def write_to_missing_timeseries_log(ds_crop, timestamp, ind_start_time):
    """
    Writes the given timestamp and index to a log file for missing time series.
    Input
    - ds_crop: the dataset crop that is being processed
    - timestamp: the timestamp that is being processed
    - ind_start_time: the index of the timestamp in the dataset

    Output
    None, but writes to a log file named 'log_skipped_timeseries.txt' in
    the current working directory.
    """
    with open('log_skipped_timeseries.txt', 'a') as log_file:
        time_missing = timestamp
        hour_miss, month_miss, day_miss, yyyy_miss, minute_miss = parse_timestamp(time_missing)
        month_miss, day_miss, hour_miss = int(month_miss), int(day_miss), int(hour_miss)
        log_file.write(f"date: {yyyy_miss}-{month_miss:02d}-{day_miss:02d} {hour_miss}:{minute_miss} for index {ind_start_time}\n")
    return
