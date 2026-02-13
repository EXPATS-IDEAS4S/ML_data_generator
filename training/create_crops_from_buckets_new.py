"""
Script to create crops from data stored in S3 buckets.
It reads data from one or multiple S3 buckets, merges them if necessary, applies domain filtering,
and generates crops based on a specified strategy (random or fixed).
The crops are saved in NetCDF format and as images in the specified output directory.   

For Claudia:
to run on EWC. remember to activate the virtual environment first:
source  /home/claudia/.venv/bin/activate
and then call the script:


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
import boto3
from botocore.exceptions import ClientError
import sys

# instructiosn to import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cropping_functions import crops_nc_random, crops_nc_fixed, filter_by_domain, filter_by_time, apply_cma_mask
from credentials_buckets import S3_ACCESS_KEY, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL
from config import *
from data_bucket_functions import init_s3, list_files_bucket, check_file_bucket, read_file, read_bucket_name_path

from space_time_functions import calc_start_time_for_days_changing, calc_start_time_for_days_full, search_timewindow_without_nan
from utils import parse_timestamp, is_valid_time



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
        crops_nc_random(ds_timeseries, X_PIXEL, Y_PIXEL,filename_to_save, outpath, timestamp, domain)
    elif CROPPING_STRATEGY == 'fixed':
        crops_nc_fixed(ds_time, X_PIXEL, Y_PIXEL, [(CROP_UL_LAT, CROP_UL_LON)], filename_to_save, outpath, 'npy')
    else:
        raise ValueError(f"Invalid cropping strategy: {CROPPING_STRATEGY}")

    return


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

        # for RR then check file object
        if var_name == 'RR_de' or var_name == 'RR_it':

            # read file list on the bucket
            dict_list = list_files_bucket(s3, bucket_names[i_var])
            file_names = [dict_list[i]['Key']  for i in range(len(dict_list))]
            
            # find filename of the yyyymmdd of interest
            file_name_to_read = None
            for file_name in file_names:
                if f"{yyyy}{mm:02d}{dd:02d}" in file_name:
                    file_name_to_read = file_name
                    break
            if file_name_to_read is None:
                logging.info(f"File for {var_name} not found for date {yyyy}-{mm:02d}-{dd:02d} in bucket {bucket_names[i_var]}. Skipping this day.")
                return None, None
            
            # read file object from S3 bucket
            #print(f"Reading variable {var_name} from bucket {bucket_names[i_var]}, file {file_name_to_read}")

            file_obj = read_file(s3, file_name_to_read, bucket_names[i_var])
            
        else:
            # read file object from S3 bucket
            file_obj = read_file(s3, file_names[i_var], bucket_names[i_var])


        # if file not found, skip
        if file_obj is None:

            # write date to log file for info
            with open('log_skipped_dates.txt', 'a') as log_file:
                log_file.write(f"{yyyy}-{mm}-{dd} - missing {var_name} file \n")
            # return to main and skip the day
            return None, None
            
        # open dataset from file object
        if var_name == 'RR_de' or var_name == 'RR_it':
            var_name = 'RR'
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

    returns:
        ncfilename: name of the nc file where the crop is saved
        output_dir: directory where the crop is saved

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
    # build filename string as yyyymmmdd_starthourminute_endhourminute_VARIABLES
    end_time = ds_timeseries.time.values[-1]
    end_hour, end_month, end_day, end_yyyy, end_minute = parse_timestamp(end_time)

    # get the date and time of the first timestamp in the timeseries
    hour, month, day, yyyy, minute = parse_timestamp(timestamp_start)

    # generate filename to save crops
    var_string = "_".join(CLOUD_PRM)
    filename_to_save = f"{yyyy}{month}{day}_{hour}{minute}_{end_hour}{end_minute}_{var_string}"
    logging.info(f"filename to save: {filename_to_save}")
    logging.info(f"**************************************************************************")
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


    # generate crops based on the cropping strategy
    if CROPPING_STRATEGY == 'random':
        crops_nc_random(ds_timeseries, X_PIXEL, Y_PIXEL, filename_to_save, outpath, timestamp_start, domain)
        logging.info(f"Finished generating random crops for timestamp: {timestamp_start}")
        logging.info("--------------------------------------------------------------------------------")
    elif CROPPING_STRATEGY == 'fixed':
        crops_nc_fixed(ds_timeseries, X_PIXEL, Y_PIXEL, [(CROP_UL_LAT, CROP_UL_LON)], filename_to_save, outpath, 'npy')
        logging.info(f"Finished generating fixed crops for timestamp: {timestamp_start}")
        logging.info("--------------------------------------------------------------------------------")
    else:
        raise ValueError(f"Invalid cropping strategy: {CROPPING_STRATEGY}")

    return


def setup_logger():
    """
    Sets up the logging configuration.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():

    # get start time of this script
    start_time_script = time.time()

    # start logger and initialize s3 client
    setup_logger()
    s3 = init_s3()

    # creating output directory for nc files and images of the crops
    cloud_prm_str = "_".join(CLOUD_PRM)
    years_str = "-".join(map(str, YEARS))
    outpath = os.path.join(OUTPUT_BASE, f"crops_{cloud_prm_str}_{X_PIXEL}x{Y_PIXEL}_{years_str}_{N_SAMPLES}-{CROPPING_STRATEGY}-nframes-{TIME_LENGTH}")
    os.makedirs(outpath, exist_ok=True)

    # count days to estimate time taken to run the script per day
    count_days = 0

    # iterate over years, months, days to read daily files from S3 bucket
    for year in YEARS:

        # loop over months 
        for month in MONTHS:

            # initialization of variable to handle space-time crops between days
            if TIME_LENGTH > 1:
                # initialize variable indicating the presence of an incomplete timeserie in the previous day to none
                from_previous_day = None

            # loop over days
            for day in DAYS:

                # read variables to read and access all files with their corresponding paths built with a function
                bucket_names, file_names = read_bucket_name_path(year, month, day)

                # read, crop, resample and merge all variables of interest into a single dataset for the day
                ds_crop, domain_all_data = prepare_joint_dataset(s3, bucket_names, file_names, year, month, day)

                if ds_crop is None:
                    logging.info(f"Skipping {year}-{month:02d}-{day:02d} due to missing files.")
                    continue
                else:
                    logging.info(f"Processing date: {year}-{month:02d}-{day:02d} - all input data found")
                    logging.info('----------------------------------------------')
                    count_days += 1
                    
                # extraction of crops for each timestamp and plotting

                # processing for one only space cropping - 1 single time stamp
                # ************************************************************
                if TIME_LENGTH == 1:
                    logging.info("Processing single timestamp crops.")
                    for timestamp in ds_crop.time.values:
                        try:
                            ds_time = filter_by_time(ds_crop, timestamp)

                            # crop individual timestamp and save them to ncdf and as images
                            crop_individual_timestamps(ds_time, timestamp, domain_all_data, outpath)

                        except Exception as e:
                            logging.warning(f"Skipping timestamp {timestamp} due to (sono qui): {e}")
                            traceback.print_exc()


                # processing for space-time cropping - N_FRAMES time stamps
                # ************************************************************
                else:
                    logging.info(f"Processing space-time crops:{TIME_LENGTH} timestamps per sample.")

                    # if there is data carried over from the previous day, process it first
                    if from_previous_day is not None:
                        
                        logging.info("Processing timeseries from previous day before starting with the current day.")

                        # concatenate data from previous day to the beginning of the current day's dataset
                        ds_timeseries = xr.concat([from_previous_day, ds_crop], dim='time').isel(time=slice(0, N_FRAMES))

                        # check that selected timeserie is not nan for the MSG 10.8 channel 
                        is_all_nan = ds_timeseries[CLOUD_PRM[0]].isnull().all(dim=['lat', 'lon'])

                        # process this timeseries if it is complete before moving on with the normal processing of the next day
                        if not is_all_nan.any():

                            # define start time index for the next time series when data exists from previous day
                            start_next = calc_start_time_for_days_changing(from_previous_day)

                            # crop time series 
                            timestamp_start = ds_timeseries.time.values[0] # first time stamp of the dataset selected by merging
                            crop_multiple_timestamps(ds_timeseries, timestamp_start, domain_all_data, outpath)

                            # reset from_previous_day to None
                            from_previous_day = None

                            # updating start time for the next iteration
                            start_time = start_next
                        else:
                            logging.info("Skipping timeseries from previous day due to all NaN values.")
                            start_time = random.randint(0, int(N_FRAMES-1))

                        logging.info(f"start_time for next iteration: {ds_timeseries.time[start_time].values}, {start_time} index")
                        logging.info(f"**************************************************************************")
                    # no data from previous day, set start time randomly
                    else:

                        exit_to_new_day = False
                        # generate start_time index randomly based on MAX_TEMPORAL_OVERLAP and MAX_DAILY_OFFSET
                        start_time = calc_start_time_for_days_full()

                        logging.info(f"Initial start_time for the day: {ds_crop.time[start_time].values}")
                        

                        # loop over until the end of the day
                        while start_time < len(ds_crop.time.values):
                            
                            # find timeseries window without NaN values and next start time
                            ds_timeseries, start_next = search_timewindow_without_nan(ds_crop, start_time)

                            # if timeseries is incomplete, break the loop
                            if ds_timeseries is None:
                                from_previous_day = None
                                break
                            
                            # if timeseries in incomplete at the end of the day, store it for the next day
                            elif len(ds_timeseries.time.values) < N_FRAMES:
                                from_previous_day = ds_timeseries
                                exit_to_new_day = True
                                logging.info(f"Timeseries window is incomplete at the end of the day, storing it for the next day. Start time: {ds_timeseries.time[0].values}, number of frames: {len(ds_timeseries.time.values)}")
                                logging.info("**************************************************************************")

                                # go to next day
                                break

                            else:

                                logging.info(f"Start time of the current timeseries window: {ds_timeseries.time[0].values}")
                                logging.info(f"************++********************************************************************")
                                logging.info(f"start index of time for the next iteration: {start_next} index")
                                logging.info(f"************++********************************************************************")

                                # crop time series starting from start_time
                                timestamp_start = ds_timeseries.time.values[0]
                                crop_multiple_timestamps(ds_timeseries, timestamp_start, domain_all_data, outpath)   

                            # set start time for the next iteration of the loop to the start time of the next timeseries window
                            start_time = start_next
                            logging.info(f"index for start time of next iteration: {start_time} index")
                            logging.info(f"**************************************************************************")
                        
                            if exit_to_new_day:
                                break   

                    if exit_to_new_day:
                        exit_to_new_day = False
                        logging.info("Moving to the next day.")
                        logging.info(f"**************************************************************************")
                        continue

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
