"""
Script to create crops from data stored in S3 buckets.
It reads data from one or multiple S3 buckets, merges them if necessary, applies domain filtering,
and generates crops based on a specified strategy (random or fixed).
The crops are saved in NetCDF format and as images in the specified output directory.   

For Claudia:
to run on EWC. remember to activate the virtual environment first:
source  /home/claudia/.venv/bin/activate

"""

import os
import io
import gzip
import pdb
import logging
import xarray as xr
import numpy as np
from matplotlib.colors import ListedColormap
from datetime import datetime
import random
import time
import traceback

# instructiosn to import from parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cropping_functions import crops_nc_random, crops_nc_fixed, filter_by_domain, filter_by_time, apply_cma_mask
from credentials_buckets import S3_ACCESS_KEY, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL
from config import *

import boto3
from botocore.exceptions import ClientError


def check_file_bucket(file2find, domain):
    """code to check if a file is on the bucket
    input:
    file2find: filename with path to find n bucket
    domain: string, 'DE' or 'IT' for the domain to check the bucket
    
    return:
    filefound (boolean) true if file is found, false if file is not on the bucket
    """
    from readers.data_buckets_funcs import Initialize_s3_client, upload_file
    import boto3

    if domain == 'DE':
        from readers.s3_bucket_credentials import S3_BUCKET_NAME, S3_ACCESS_KEY, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL
        bucket_name = S3_BUCKET_NAME

    elif domain == 'IT':
        from readers.s3_bucket_credentials import S3_ACCESS_KEY, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL
        bucket_name = "expats-radar-italy"
    else:
        print('domain not recognized')
        return(False)
    
    s3 = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY)
    
    
    # List the objects in our bucket
    response = s3.list_objects(Bucket=bucket_name)
    
    # set flag to false if file is not found
    filefound = False
    if "Contents" not in response:
        print(f"No files on bucket")
        
    
    # loop on files found on bucket
    for obj in response["Contents"]:
        key = obj["Key"]
        if key == file2find:
            filefound = True
            return filefound
        else:
            continue

    return filefound


def list_files_bucket(s3, S3_BUCKET_NAME):
    """
    script to list files in the bucket
    - s3: bucket to be checked
    
    """
    # List the objects in our bucket
    response = s3.list_objects(Bucket=S3_BUCKET_NAME)
    
    # set flag to false if file is not found
    filefound = False
    if "Contents" not in response:
        print(f"No files on bucket")
        return([])
    else:
        return(response["Contents"])

def read_bucket_name_path(year, month, day):

    """Returns the S3 bucket name based on the variable and on the date.
    This function determines the appropriate S3 bucket name for a given variable and date.
    :param var: str
        The variable for which to determine the S3 bucket name (e.g., 'IR_108', 'RR', 'lightning').
    :param yy: int
        The year component of the date.
    :param mm: int
        The month component of the date.
    :param dd: int
        The day component of the date.
    :return: str
        The name of the S3 bucket corresponding to the variable and date.   
    : returns: path_dir: str
        The path directory within the S3 bucket for the specified variable and date.
    
    """
    bucket_names = []
    file_names = []

    for i, var in enumerate(CLOUD_PRM):

        # read bucket name for the selected variable
        bucket_name = BUCKET_NAMES[i]

        # bucket names depending on the bucket to read from
        if var == 'IR_108' or var == 'HRV' or var == 'WV_062' or var == 'WV_073' or var == 'WV_087' or var == 'CMA':
            file_path = f"{PATH_DIR[i]}/{year:04d}/{month:02d}/{BASENAME[i]}_{year:04d}-{month:02d}-{day:02d}.nc"

        elif var == 'RR_de':
            #            20130908_RR_15min_msg_res.nc.gz. _RR_DE_15min_msg_res

            file_path = f"{year:04d}{month:02d}{day:02d}{BASENAME[i]}.nc.gz"

        elif var == 'RR_it':
            file_path = f"{PATH_DIR[i]}/COMP_{year:04d}{month:02d}{day:02d}{BASENAME[i]}.nc.gz"

        # appending to lists
        bucket_names.append(bucket_name)
        file_names.append(file_path)


    return bucket_names, file_names



def setup_logger():
    """
    Sets up the logging configuration.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def init_s3():
    """
    Initializes and returns an S3 client using the provided credentials and endpoint.
    """

    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY, 
    )

def read_file(s3, file_path, bucket):

    # print all files in the bucket for debugging
    #all_files = print_list_files_in_bucket(s3, bucket)
    # example: /data/sat/msg/ml_train_crops/IR_108-WV_062-CMA_FULL_EXPATS_DOMAIN/2025/08/merged_MSG_CMSAF_2025-08-22.nc

    try:
        obj = s3.get_object(Bucket=bucket, Key=file_path)
        return obj['Body'].read()
    except ClientError as e:
        logging.warning(f"Failed to read file {file_path}: {e}")
        return None


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


def crop_individual_timestamps(ds_time, timestamp, domain, outpath):

    """
    Script to process a single timeestamp from the dataset and generate crops.
    It allows cropping at fixed locations or random locations based on the configuration.
    It also checks for NaN values and value ranges before cropping.

    input:
        ds_time: xarray Dataset for the specific timestamp
        timestamp: specific timestamp being processed
        domain: domain for the input file 
        outpath: output directory to save crops

    dependencies:
        uses global config variables: 
          VALUE_MIN, 
          VALUE_MAX, 
          CROPPING_STRATEGY,
          X_PIXEL, 
          Y_PIXEL, 
          N_SAMPLES, 
          DOMAIN_NAME,
          CROP_UL_LAT,
          CROP_UL_LON

        crops_nc_random 
        crops_nc_fixed 
        parse_timestamp

    output:
        Saves crops to the specified output directory:
        - ncdf in nc folder
        - images in images folder
    """
    # define timestamps for defition of output filename
    hour, month, day, yyyy, minute = parse_timestamp(timestamp)
    print(hour, month, day, minute, yyyy)

    # check for all NaN values or values outside the specified range
    # select all data vars except RR_de and RR_it for the check of all NaN values
    vars = [var for var in ds_timeseries.data_vars if var not in ['RR_de', 'RR_it']]
    value_min = [vmin for i, vmin in enumerate(VALUE_MIN) if CLOUD_PRM[i] in vars]
    value_max = [vmax for i, vmax in enumerate(VALUE_MAX) if CLOUD_PRM[i] in vars]

    # check for all NaN values or values outside the specified range
    is_all_nan_ds = all([xr.DataArray.isnull(ds_timeseries[var]).all() for var in vars])
    is_outside_range = any(
        [((ds_timeseries[var] < vmin) | (ds_timeseries[var] > vmax)).any()
         for var, vmin, vmax in zip(vars, value_min, value_max)]
    )
    if is_all_nan_ds or is_outside_range:
        logging.info(f"Skipping timestamp {timestamp} due to all NaN or values outside range.")
        return

    # check if the timestamp is within the valid time ranges
    if not is_valid_time(timestamp, month, day, hour):
        logging.info(f"Skipping timestamp {timestamp} due to time filter.")
        return

    logging.info(f"Processing timestamp: {timestamp}")

    # generate filename to save crops
    var_string = "_".join(CLOUD_PRM)
    filename_to_save = f"{yyyy}{month}{day}_{hour}{minute}_{DOMAIN_NAME}_{var_string}"

    logging.info(f"Generating crops for timestamp: {timestamp}, saving as: {filename_to_save}")
    # generate crops based on the cropping strategy
    if CROPPING_STRATEGY == 'random':
        crops_nc_random(ds_time, X_PIXEL, Y_PIXEL, N_SAMPLES, filename_to_save, outpath, timestamp, domain)
    elif CROPPING_STRATEGY == 'fixed':
        crops_nc_fixed(ds_time, X_PIXEL, Y_PIXEL, [(CROP_UL_LAT, CROP_UL_LON)], filename_to_save, outpath, 'npy')
    else:
        raise ValueError(f"Invalid cropping strategy: {CROPPING_STRATEGY}")

    return

def print_list_files_in_bucket(s3, S3_BUCKET_NAME):
    """Lists all files in the specified S3 bucket.
    input:
        s3: S3 client
        bucket: Name of the S3 bucket
    output:
        List of file keys in the bucket.
    """
    # Pagination to get all objects
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET_NAME)
    all_objects = []
    for page in pages:
        if "Contents" in page:
            for obj in page['Contents']:
                print(obj['Key'])  # Only print the Key
            all_objects.extend(page["Contents"])
    return all_objects

def prepare_joint_dataset(s3, bucket_names, file_names, yyyy,mm, dd):
    """
    Prepares a joint xarray Dataset by reading and merging data from multiple S3 buckets. it reads and 
    then merges the datasets for all variables specified in CLOUD_PRM. It identifies the common domain across all datasets
    and resamples datasets to the highest resolution before merging.
    If any of the daily files are not found, we skip the day and return None

    input:
        s3: S3 client
        bucket_names: list of S3 bucket names for each variable
        file_names: list of file paths within the buckets for each variable
        yyyy: year of the data
        mm: month of the data
        dd: day of the data
    output:
        Merged xarray Dataset containing data from all specified buckets and files.
        domain where all data are available: tuple with (lon_min, lon_max, lat_min, lat_max)
    dependencies:
        read_file
        CLOUD_PRM;  list of variable fields to use (sat channels, radar or other variables from different sources)

    """
    # initialize lists to store datasets and domain edges
    ds_arr = []
    lats_min_list = []
    lons_min_list = []
    lats_max_list = []
    lons_max_list = []

    # read and process each variable from its respective bucket ; 
    # CLOUD_PRM: loop in on the list of variable fields to use (sat channels, radar or other variables from different sources) 
    for i_var, var_name in enumerate(CLOUD_PRM):

        print(f"Reading variable {var_name} from bucket {bucket_names[i_var]}, file {file_names[i_var]}")

        # read file object from S3 bucket
        file_obj = read_file(s3, file_names[i_var], bucket_names[i_var])

        # if file not found, skip
        if file_obj is None:

            # write date to log file for info
            with open('log_skipped_dates.txt', 'a') as log_file:
                log_file.write(f"{yyyy}-{mm}-{dd} - missing {var_name} file \n")
            # return to main and skip the day
            return None, None
            
        if var_name == 'RR_de' or var_name == 'RR_it':
            # decompress gzip file
            ds = xr.open_dataset(io.BytesIO(gzip.decompress(file_obj)))
        else:
            ds = xr.open_dataset(io.BytesIO(file_obj))

        # select only variable of interest
        ds_var = ds[var_name]

        # define edges of the domain
        lat_min, lat_max = ds_var.lat.min().item(), ds_var.lat.max().item()
        lon_min, lon_max = ds_var.lon.min().item(), ds_var.lon.max().item()
        
        # store values to calcuate common domain
        lats_min_list.append(lat_min)
        lats_max_list.append(lat_max)
        lons_min_list.append(lon_min)
        lons_max_list.append(lon_max)
        
        ds_arr.append(ds_var)

    # identify common domain across all datasets and crop them on that
    # define common domain
    lat_min_common = max(lats_min_list)
    lat_max_common = min(lats_max_list)
    lon_min_common = max(lons_min_list)
    lon_max_common = min(lons_max_list)
    domain_all_data = (lon_min_common, lon_max_common, lat_min_common, lat_max_common)
    logging.info(f"Common domain for cropping: {domain_all_data}")

    # select only areas where data are in the domain for all ds_var in ds_arr
    for i, ds_var in enumerate(ds_arr):
        ds_arr[i] = ds_var.sel(lat=slice(lat_min_common, lat_max_common), lon=slice(lon_min_common, lon_max_common))
    
    # resample all datasets to the ds with the highest resolution (smallest pixel size)
    pixel_sizes = []
    for ds_var in ds_arr:
        lat_diff = np.abs(ds_var.lat[1] - ds_var.lat[0]).item()
        lon_diff = np.abs(ds_var.lon[1] - ds_var.lon[0]).item()
        pixel_size = (lat_diff + lon_diff) / 2
        pixel_sizes.append(pixel_size)
    highest_res_index = np.argmin(pixel_sizes)
    ds_ref = ds_arr[highest_res_index]
    for i, ds_var in enumerate(ds_arr):
        if i != highest_res_index:
            ds_arr[i] = ds_var.interp(lat=ds_ref.lat, lon=ds_ref.lon, method='nearest')

    # merge all datasets into a single dataset
    ds_crop = xr.merge(ds_arr)
    return ds_crop, domain_all_data



def calc_start_time_for_days_changing(from_previous_day):
    """
    Calculates the start time for cropping when transitioning between days.
    It considers a maximum daily offset if specified in the configuration.

    input:
        from_previous_day: xarray Dataset containing data from the previous day
    output:
        start_time: datetime object representing the start time for cropping
    """
    # determine the maximum daily offset
    earliest_start = max(int(N_FRAMES - MAX_TEMPORAL_OVERLAP*N_FRAMES - len(from_previous_day.time.values)), 0)

    # pick start time randomly between the earliest start and N_FRAMES -1
    start_time = random.randint(earliest_start, int(N_FRAMES-1))

    return start_time
def calc_start_time_for_days_full():
    """
    Calculates the start time for cropping when processing a full day starting at 00.00 UTC
    It considers a maximum daily offset if specified in the configuration.
    The start time is chosen randomly between 0 and N_FRAMES-1 if MAX_DAILY_OFFSET is not set.
    if MAX_DAILY_OFFSET is set, it is chosen randomly between 0 and round(MAX_DAILY_OFFSET*N_FRAMES)+1 
    where MAX_DAILY_OFFSET represents the maximum random offset at the beginning of the day
    output:
        start_time: datetime object representing the start time for cropping
    """
    if MAX_DAILY_OFFSET is not None:
        start_time = random.randint(0, round(MAX_DAILY_OFFSET*N_FRAMES)+1)
    else:
        start_time = random.randint(0, int(N_FRAMES-1))
    return start_time

def search_timewindow_without_nan(ds_day, start_time):

    """
    Function to identify a time serie of N_FRAMES without NaN values in the dataset
    :param ds_day: Dataset for the current day
    :param start_time: Start time of the timeseries window
        
    :return: ds_timeseries: Dataset for the timeseries window
             start_time_next: Start time of the next timeseries window
    """
    # end time given the start time and N_FRAMES
    end_time = start_time + N_FRAMES

    # flag to indicate if still searching for timeseries window without NaNs
    searching_timeseries_window = True

    # loop until a timeseries window without NaNs is found
    while searching_timeseries_window:
        
        # slice small timeseries from dataset
        ds_timeseries = ds_day.isel(time=slice(start_time, end_time))

        # check at each timestamp if all data is NaN, i.e. MSG timestamp is missing
        is_all_nan = ds_timeseries[CLOUD_PRM[0]].isnull().all(dim=['lat', 'lon'])

        # move on to after missing timestamp
        if is_all_nan.any():
            
            # moving to next available timestamp
            ind_nan_last = np.where(is_all_nan.values)[0][-1]

            # shift start and end time to next available timestamp
            start_time += ind_nan_last + 1
            end_time = start_time + N_FRAMES

            # check if start time is still within the dataset
            if start_time >= len(ds_day.time.values):
                # if not, end this loop
                searching_timeseries_window = False
                start_time_next = None
                ds_timeseries = None
                break

            # if start and end within daytime - continue to the next iteration of the loop   
            continue
        
        # end the loop if all timestamps are available
        searching_timeseries_window = False

        # set the start for the next timeseries
        start_time_next = end_time

    return ds_timeseries, start_time_next






def crop_multiple_timestamps(ds_timeseries, timestamp_start, domain, outpath):
    """
    Script to process space-time crops from the dataset and generate crops. 

    It allows cropping at fixed locations or random locations based on the configuration.
    It also checks for NaN values and value ranges before cropping.

    input:
        ds_timeserie: xarray Dataset for the specific sample of N_FRAMES timestamps
        timestamp_start: specific start timestamp being processed
        domain: domain for the input file
        outpath: output directory to save crops

    dependencies:
        uses global config variables: 
          VALUE_MIN, 
          VALUE_MAX, 
          CROPPING_STRATEGY,
          X_PIXEL, 
          Y_PIXEL, 
          N_SAMPLES, 
          DOMAIN_NAME,
          CROP_UL_LAT,
          CROP_UL_LON

        crops_nc_random 
        crops_nc_fixed 
        parse_timestamp

    output:
        Saves crops to the specified output directory:
        - ncdf in nc folder
        - images in images folder
    """
   

    # get the date and time of the first timestamp in the timeseries
    hour, month, day, yyyy, minute = parse_timestamp(timestamp_start)
    print(hour, month, day, minute, yyyy)

    # check for all NaN values or values outside the specified range
    # select all data vars except RR_de and RR_it for the check of all NaN values
    vars = [var for var in ds_timeseries.data_vars if var not in ['RR_de', 'RR_it']]
    value_min = [vmin for i, vmin in enumerate(VALUE_MIN) if CLOUD_PRM[i] in vars]
    value_max = [vmax for i, vmax in enumerate(VALUE_MAX) if CLOUD_PRM[i] in vars]

    # check for all NaN values or values outside the specified range
    is_all_nan_ds = all([xr.DataArray.isnull(ds_timeseries[var]).all() for var in vars])
    is_outside_range = any(
        [((ds_timeseries[var] < vmin) | (ds_timeseries[var] > vmax)).any()
         for var, vmin, vmax in zip(vars, value_min, value_max)]
    )

    if is_all_nan_ds or is_outside_range:
        logging.info(f"Skipping timestamp {timestamp_start} due to all NaN or values outside range.")
        return

    # generate filename to save crops
    var_string = "_".join(CLOUD_PRM)
    filename_to_save = f"{yyyy}{month}{day}_{hour}{minute}_{DOMAIN_NAME}_{var_string}"

    logging.info(f"Generating crops for timestamp: {timestamp_start}, saving as: {filename_to_save}")

    # generate crops based on the cropping strategy
    if CROPPING_STRATEGY == 'random':
        crops_nc_random(ds_time, X_PIXEL, Y_PIXEL, N_SAMPLES, filename_to_save, outpath, timestamp_start, domain)
    elif CROPPING_STRATEGY == 'fixed':
        crops_nc_fixed(ds_time, X_PIXEL, Y_PIXEL, [(CROP_UL_LAT, CROP_UL_LON)], filename_to_save, outpath, 'npy')
    else:
        raise ValueError(f"Invalid cropping strategy: {CROPPING_STRATEGY}")
    return


def main():

    # get start time of this script
    start_time_script = time.time()

    # count days to estimate later runtime per day
    count_days = 0
    
    # start logger and initialize s3 client
    setup_logger()
    s3 = init_s3()

    # creating output directory for nc files and images of the crops
    cloud_prm_str = "_".join(CLOUD_PRM)
    years_str = "-".join(map(str, YEARS))
    outpath = os.path.join(OUTPUT_BASE, f"crops_{cloud_prm_str}_{X_PIXEL}x{Y_PIXEL}_{years_str}_{N_SAMPLES}-{CROPPING_STRATEGY}-nframes-{TIME_LENGTH}.nc")
    os.makedirs(outpath, exist_ok=True)

    # iterate over years, months, days to read daily files from S3 bucket
    for year in YEARS:

        # initialization of variable to handle space-time crops 
        if TIME_LENGTH > 1:
            # initialize variable indicating the presence of an incomplete timeserie in the previous day to none
            from_previous_day = None

        # loop over months and days
        for month in MONTHS:
            for day in DAYS:

                # read variables to read and access all files with their corresponding paths built with a function
                bucket_names, file_names = read_bucket_name_path(year, month, day)

                # read, crop, resample and merge all variables of interest into a single dataset 
                ds_crop, domain_all_data = prepare_joint_dataset(s3, bucket_names, file_names, year, month, day)
                if ds_crop is None:
                    logging.info(f"Skipping {year}-{month:02d}-{day:02d} due to missing files.")
                    continue

                # extraction of crops for each timestamp and plotting

                # processing for one only space cropping - 1 single time stamp
                # ************************************************************
                if TIME_LENGTH == 1:
                    for timestamp in ds_crop.time.values:
                        try:
                            ds_time = filter_by_time(ds_crop, timestamp)
                            crop_individual_timestamps(ds_time, timestamp, domain_all_data, outpath)
                        except Exception as e:
                            logging.warning(f"Skipping timestamp {timestamp} due to (sono qui): {e}")
                            traceback.print_exc()


                # processing for space-time cropping - N_FRAMES time stamps
                # ************************************************************
                else:

                    # if there is data carried over from the previous day, process it first
                    if from_previous_day is not None:

                        # concatenate data from previous day to the beginning of the current day's dataset
                        ds_timeseries = xr.concat([from_previous_day, ds_crop], dim='time').isel(time=slice(0, N_FRAMES))

                        # check that selected timeserie is not nan for the MSG 10.8 channel 
                        is_all_nan = ds_timeseries[CLOUD_PRM[0]].isnull().all(dim=['lat', 'lon'])

                        # process this timeseries if it is complete before moving on with the normal processing of the next day
                        if not is_all_nan.any():

                            # define start time index for the cropping at the next time stamp
                            start_time = calc_start_time_for_days_changing(from_previous_day)

                            # crop time series 
                            timestamp_start = ds_timeseries.time.values[0]
                            crop_multiple_timestamps(ds_timeseries, timestamp_start, domain_all_data, outpath)

                            # reset from_previous_day to None
                            from_previous_day = None


                        else:
                            logging.info("Skipping timeseries from previous day due to all NaN values.")
                            start_time = random.randint(0, int(N_FRAMES-1))

                    # no data from previous day, set start time randomly
                    else:

                        # generate start_time index randomly based on MAX_TEMPORAL_OVERLAP and 
                        start_time = calc_start_time_for_days_full()

                        # loop over until the end of the day
                        while start_time < len(ds_crop.time.values):

                            # find timeseries window without NaN values and next start time
                            ds_timeseries, start_time = search_timewindow_without_nan(ds_crop, start_time)

                            # if timeseries is incomplete, break the loop
                            if ds_timeseries is None:
                                from_previous_day = None
                                break
                            
                            # if timeseries in incomplete at the end of the day, store it for the next day
                            elif len(ds_timeseries.time.values) < N_FRAMES:
                                from_previous_day = ds_timeseries
                                break

                            else:
                                # crop time series starting from start_time
                                timestamp_start = ds_timeseries.time.values[0]
                                crop_multiple_timestamps(ds_timeseries, timestamp_start, domain_all_data, outpath)   
        
        # print progress
        print("----------------------------------------------", flush=True)
        temp_runtime = time.time() - start_time_script
        print(f"{count_days} days processed: {temp_runtime/count_days:.2f} seconds or {temp_runtime/count_days/60:.2f} minutes per day", flush=True)
        print(f"total runtime until now: {temp_runtime/60:.2f} minutes or {temp_runtime/60/60:.2f} hours", flush=True)

    # runnning time of the script in minutes
    runtime = time.time() - start_time_script
    print()
    print(f"Total runtime: {runtime/60:.2f} minutes or {runtime/60/60:.2f} hours", flush=True)
    print(f"Runtime per day: {runtime/count_days:.2f} seconds or {runtime/count_days/60:.2f} minutes", flush=True)


    # print and store config file in the output directory
    config_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../training/config.py')
    config_dst = os.path.join(os.path.dirname(outpath), 'config_used.py')
    os.system(f"cp {config_src} {config_dst}")
    logging.info(f"Copied config file to {config_dst}")

if __name__ == "__main__":
    main()
