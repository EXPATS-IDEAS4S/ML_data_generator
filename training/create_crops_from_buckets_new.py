"""
Script to create crops from data stored in S3 buckets.
It reads data from one or multiple S3 buckets, merges them if necessary, applies domain filtering,
and generates crops based on a specified strategy (random or fixed).
The crops are saved in NetCDF format and as images in the specified output directory.   

For Claudia:
to run on EWC. remember to activate the virtual environment first:
source  /home/claudia/.venv/bin/activate
and then call the script:

log files produced in the log_files folder in the output directory, with a subfolder for each run based on the config parameters, 
with indication of the parameters in the name of the folder, to keep track of the different runs and their settings. 
The log files are:

    -   log_skipped_dates_joint_dataset.txt ( in prepare_joint_dataset function )
            logs the days for which one or more of the input files were missing, with indication of which variable was missing
    -   log_skipped_timeseries.txt ( in crop_multiple_timestamps function and in main)
            logs the start time and index of the time series that were skipped due to all NaN values in the channel, 
            to have a record of which time series were not included in the dataset and
    -   log_index_timeserie.txt ( in main function )
            logs the reference index and the random indices selected for each time series selection, 
            to have a record of which time series were selected for cropping
    -   log_files_produced  ( in main function )
            logs the number of files produced for each day, and the number of missing time series due 
            to all NaN values in the channel, to have a record of the output dataset and the number
            of missing time series for each day.
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
import pandas as pd

# instructiosn to import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cropping_functions import crops_nc_random, crops_nc_fixed, filter_by_domain, filter_by_time, apply_cma_mask
from credentials_buckets import S3_ACCESS_KEY, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL
from config import *
from data_bucket_functions import init_s3, list_files_bucket, check_file_bucket, read_file, read_bucket_name_path

from space_time_functions import calc_start_time_for_days_changing, calc_start_time_for_days_full, search_timewindow_without_nan, calc_random_indices
from utils import parse_timestamp, is_valid_time, write_to_missing_timeseries_log, search_all_nans_or_outside_range
from plotting.plot_crops import plot_data_for_timestamp, video_quicklook


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
     
    # search for all nans in vars except RR and for values outside the specified range in all variables of CLOUD_PRM
    is_all_nan_ds, is_outside_range = search_all_nans_or_outside_range(ds_crop)

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
        crops_nc_random(ds_time, X_PIXEL, Y_PIXEL, filename_to_save, outpath, timestamp, domain)
    elif CROPPING_STRATEGY == 'fixed':
        crops_nc_fixed(ds_time, X_PIXEL, Y_PIXEL, [(CROP_UL_LAT, CROP_UL_LON)], filename_to_save, outpath, 'npy')
    else:
        raise ValueError(f"Invalid cropping strategy: {CROPPING_STRATEGY}")

    return


def prepare_joint_dataset(s3, bucket_names, file_names, yyyy,mm, dd, today_str, log_path):
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
        today_str: string representing today's date in the format yyyymmdd, used for logging purposes
        log_path: path to the log directory where logs will be saved
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
            with open(os.path.join(log_path, f'{today_str}_log_skipped_dates_joint_dataset.txt'), 'a') as log_file:
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


def crop_multiple_timestamps(ds_timeseries, timestamp_start, domain, outpath, count_invalid):
    """
    Script to process space-time crops from the dataset and generate crops. 

    It allows cropping at fixed locations or random locations based on the configuration.
    It also checks for NaN values and value ranges before cropping.

    input:
        ds_timeserie: xarray Dataset for the specific sample of N_FRAMES timestamps
        timestamp_start: specific start timestamp being processed
        domain: domain for the input file
        outpath: output directory to save crops
        count_invalid: counter for the number of invalid time series (all NaN or values outside range) encountered, to log the information

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


    # generate crops based on the cropping strategy
    if CROPPING_STRATEGY == 'random':
        count_invalid = crops_nc_random(ds_timeseries, X_PIXEL, Y_PIXEL, filename_to_save, outpath, timestamp_start, domain, count_invalid)
        logging.info(f"Finished generating random crops for timestamp: {timestamp_start}")
        logging.info("--------------------------------------------------------------------------------")
        
    elif CROPPING_STRATEGY == 'fixed':
        crops_nc_fixed(ds_timeseries, X_PIXEL, Y_PIXEL, [(CROP_UL_LAT, CROP_UL_LON)], filename_to_save, outpath, 'npy')
        logging.info(f"Finished generating fixed crops for timestamp: {timestamp_start}")
        logging.info("--------------------------------------------------------------------------------")
    else:
        raise ValueError(f"Invalid cropping strategy: {CROPPING_STRATEGY}")

    return count_invalid


def setup_logger():
    """
    Sets up the logging configuration.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():

    # get start time of this script
    start_time_script = time.time()

    # prepare today string of the form yyyymmdd for the file name where today is the day in which the code is run
    today_str = datetime.now().strftime("%Y%m%d")

    # start logger and initialize s3 client
    setup_logger()
    s3 = init_s3()

    # creating output directory for nc files and images of the crops
    cloud_prm_str = "_".join(CLOUD_PRM)
    years_str = "-".join(map(str, YEARS))
    outpath = os.path.join(OUTPUT_BASE, f"crops_{cloud_prm_str}_{X_PIXEL}x{Y_PIXEL}_{years_str}_{N_SAMPLES}-{CROPPING_STRATEGY}-nframes-{TIME_LENGTH}")
    os.makedirs(outpath, exist_ok=True)

    # create string to identify current run based on config parameters to created a log folder for this run
    # string format: run_2013-2014_4-5-6-7-8-9_Nframes8_Nrandtime3_Nrandspace2
    string_folder = f"run_{years_str}_{'-'.join(map(str, MONTHS))}_Nframes{N_FRAMES}_Nrandtime{N_RANDOM_TIMES}_Nrandspace{N_SAMPLES}"
    log_path = os.path.join(outpath, "log_files/", f"{string_folder}/")
    os.makedirs(log_path, exist_ok=True)
    
    # if the folder already exists, ask the user if they want 
    # to do again the run and overwrite the existing log files
    if os.listdir(log_path):
        answer = input(f"Log folder {log_path} already exists. Do you want to do the run again and overwrite the existing log files? (y/n) ")
        if answer.lower() != 'y':
            print("Exiting the code.")
            return
        else:
            print("Proceeding with the run and overwriting existing log files.")

    # count days to estimate time taken to run the script per day
    count_days = 0

    # iterate over years, months, days to read daily files from S3 bucket
    for year in YEARS:

        # loop over months 
        for month in MONTHS:


            # loop over days
            for day in DAYS:

                # save list of indeces and day counteres that are selected
                ind_selected = []
                count_missing_timeseries = 0

                # read variables to read and access all files with their corresponding paths built with a function
                bucket_names, file_names = read_bucket_name_path(year, month, day)

                # read, crop, resample and merge all variables of interest into a single dataset for the day
                ds_crop, domain_all_data = prepare_joint_dataset(s3, bucket_names, file_names, year, month, day, today_str)

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
                            # filter dataset for the specific timestamp
                            ds_time = filter_by_time(ds_crop, timestamp)

                            if QUICKLOOKS_CROPS:

                                # create output directory for quicklooks
                                outpath_quicklooks = os.path.join(outpath, "quicklooks/original_data")
                                os.makedirs(outpath_quicklooks, exist_ok=True)  

                                # plot all original data for the selected timestamp for check on data selection
                                plot_data_for_timestamp(ds_time, timestamp, outpath_quicklooks)
                            
                            # crop individual timestamp and save them to ncdf and as images
                            crop_individual_timestamps(ds_time, timestamp, domain_all_data, outpath)


                        except Exception as e:
                            logging.warning(f"Skipping timestamp {timestamp} due to (sono qui): {e}")
                
                            traceback.print_exc()
                            pdb.set_trace()

                # processing for space-time cropping - N_FRAMES time stamps
                # ************************************************************
                else:

                    logging.info(f"Processing space-time crops:{TIME_LENGTH} timestamps per sample.")
                    logging.info(f"Expected to extract { int(len(ds_crop.time.values)/N_FRAMES) * N_RANDOM_TIMES *  N_SAMPLES} samples.")
                    
                    # loop on time dimension in base N_FRAMES:
                    for ind_reference in range(0, len(ds_crop.time.values), N_FRAMES):
                        
                        """ selection strategy: for each loop, collect the time series initiating
                         at ind_reference, and then N_RANDOM_TIMES-1 more initiating at a random start between
                          ind_start and ind_start + N_FRAMES, to have a total of N_RANDOM_TIMES 
                          samples collected for each time window of N_FRAMES, with different 
                          random start times, to increase the variability of the samples and 
                          avoid overfitting on specific start times. if there are not enough
                          timestamps at the end of the day, we take the remaining ones from 
                          the next day """

                        # calculate list of initial time stamps for this loop
                        inds_random = calc_random_indices(ind_reference)

                        # adding indeces to the list 
                        ind_selected.extend(inds_random)

                        # write aa file where each line is for an iteration
                        with open(os.path.join(log_path, f'{today_str}_log_index_timeserie.txt'), 'a') as log_file:
                            log_file.write(f"Reference index: {ind_reference}, Random indices: {inds_random} \n")
                       
                        print(f"Random indices for time series selection: {inds_random}, at ind_reference {ind_reference}")

                        for ind_start_time in inds_random:

                            # check if ind_start_time + N_FRAMES exceeds the length of the dataset,
                            logging.info(f"Producing crops for {ind_start_time} to {ind_start_time + N_FRAMES}")
                            logging.info("*******************************************************************************************")
                            # if yes, take remaining timestamps from the next day
                            if ind_start_time + N_FRAMES > len(ds_crop.time.values):

                                logging.info(f"Not enough timestamps remaining in the day starting from index {ind_start_time}, taking remaining ones from the next day.")
                                ds_timeseries = ds_crop.isel(time=slice(ind_start_time, len(ds_crop.time.values)))

                                print("lenght of ds_timeseries with remaining timestamps from the day: ", len(ds_timeseries.time.values))

                                # read data from the next day
                                next_day = datetime(year, month, day) + pd.Timedelta(days=1)
                                yyyy_next, mm_next, dd_next = next_day.year, next_day.month, next_day.day
                                ds_crop_next, domain_all_data_next = prepare_joint_dataset(s3, bucket_names, file_names, yyyy_next, mm_next, dd_next, today_str, log_path)

                                if ds_crop_next is not None:
                                    # concatenate data from the next day to the current timeseries
                                    ds_timeseries = xr.concat([ds_timeseries, ds_crop_next], dim='time').isel(time=slice(0, N_FRAMES))

                                    print("lenght of ds_timeseries after concatenating with next day: ", len(ds_timeseries.time.values))
                                    print("lenght of ds_timeseries at final stage: ", len(ds_timeseries.time.values))
                                    if len(ds_timeseries.time.values) != N_FRAMES:
                                        # abort the code execution 
                                        raise ValueError(f"Error in concatenating data from the next day, expected length of timeseries: {N_FRAMES}, actual length: {len(ds_timeseries.time.values)}")
                                    

                                else:
                                    logging.info(f"Next day {yyyy_next}-{mm_next:02d}-{dd_next:02d} data not found, skipping this time series.")
                                    count_missing_timeseries += 1
                                    crops_affected = 'both' # both because the time series is missing due to missing data and we cannot apply cropping
                                    # add to file log_skipped_timeseries the exact start time of the missing time serie and the index
                                    write_to_missing_timeseries_log(ds_crop, ds_crop.time.values[ind_start_time], ind_start_time, crops_affected, today_str, log_path)
                                    # go to the next iteration of the loop to select another time series
                                    continue

                            else:
                                # extracting timeserie 
                                ds_timeseries = ds_crop.isel(time=slice(ind_start_time, ind_start_time + N_FRAMES))
                                timestamp_start = ds_timeseries.time.values[0]
                                timestamp_end = ds_timeseries.time.values[-1]
                                hh_st, mm_st, dd_st,  yy_st, min_st = parse_timestamp(timestamp_start)
                                hh_end, mm_end, dd_end,  yy_end, min_end = parse_timestamp(timestamp_end)
                                logging.info(f"Selected time series for day {dd_st}/{mm_st}/{yy_st} from {hh_st}:{min_st} to {hh_end}:{min_end} ")
                                logging.info("******************************************************************************************")
                            
                            # plot quicklook of the selected time series for check on data selection
                            if QUICKLOOKS_CROPS:

                                outpath_quicklooks = os.path.join(outpath, "quicklooks/original_data")
                                os.makedirs(outpath_quicklooks, exist_ok=True)  

                                # plot all original data for the selected timestamp for check on data selection
                                for ind_time_series, time_value in enumerate(ds_timeseries.time.values):
                                    plot_data_for_timestamp(ds_timeseries, time_value, outpath_quicklooks)

                            # check if for some timestamps 10.8 IR channel is all nan
                            is_all_nan = ds_timeseries[CLOUD_PRM[0]].isnull().all(dim=['lat', 'lon'])

                            if is_all_nan.any():
                                
                                # write date and time to log file for info
                                crops_affected = 'both' # both because the time series is missing due to all NaN values and we cannot apply cropping
                                write_to_missing_timeseries_log(ds_crop, ds_crop.time.values[ind_start_time], ind_start_time, crops_affected, today_str, log_path)
                                count_missing_timeseries += 1
                                logging.info(f"Skipping time series starting at {timestamp_start} due to all NaN values in {CLOUD_PRM[0]} channel.")
                                continue

                            else: 
                                # apply time series cropping and save crops to ncdf
                                count_miss_before = count_missing_timeseries
                                count_missing_timeseries = crop_multiple_timestamps(ds_timeseries, timestamp_start, domain_all_data, outpath, count_missing_timeseries)
                                # if count of missing time series increased, it means that the time series was skipped due to all NaN values in the channel,
                                # so we add it to the log file with the exact start time of the time series and the index
                                if count_missing_timeseries > count_miss_before:
                                    # if the difference is 1, it means that only one time series was skipped, so we log it as 1 crop affected 
                                    if count_missing_timeseries - count_miss_before == 1:
                                        crops_affected = 'one'
                                    elif count_missing_timeseries - count_miss_before > 1:
                                        crops_affected = 'both' # both because more than one time series was skipped due to all NaN values and we cannot apply cropping
                                    write_to_missing_timeseries_log(ds_crop, ds_crop.time.values[ind_start_time], ind_start_time, crops_affected, today_str, log_path)

                # end of loop over days
                # make a list of all nc files produced for this day
                nc_file_list = [f for f in os.listdir(outpath) if f.endswith('.nc') and f"{year}{month:02d}{day:02d}" in f]                
                num_files_produced = len(nc_file_list)
                expected_files = int(len(ds_crop.time.values)/N_FRAMES) * N_RANDOM_TIMES * N_SAMPLES

                # plot video quicklooks of the selected crops
                if QUICKLOOKS_CROPS:

                    outpath_quicklooks = os.path.join(outpath, "video_quicklooks")
                    os.makedirs(outpath_quicklooks, exist_ok=True)  

                    # plot all original data for the selected timestamp for check on data selection
                    for file in nc_file_list:

                        # read if the ncdf is from crop 0 or crop 1, to select the correct plotting function
                        if "_0.nc" in file:
                            crop_id = 0
                        elif "_1.nc" in file:
                            crop_id = 1

                        print(f"Creating quicklook for file: {file} with crop_id: {crop_id}")
                        # create quicklook video for the selected ncdf file and removes then gif and png 
                        video_path = video_quicklook(os.path.join(outpath, file), outpath_quicklooks, crop_id) 

                # number of files written in the log of missing files for the day
                with open('log_files_produced.txt', 'a') as log_file:
                    log_file.write(f"{year}-{month:02d}-{day:02d} - produced {num_files_produced} files \n")
                    log_file.write(f"{year}-{month:02d}-{day:02d} - missing {count_missing_timeseries} time series \n")
                    log_file.write(f"{year}-{month:02d}-{day:02d} - expected files {expected_files} \n")    

                print("******************************************************************************************")
                print(f" number of starting time stamps {len(ind_selected)}")
                print(f"number of expected files (twice the number of starting time stamps): {expected_files}")
                print(f" invalid time series: {count_missing_timeseries} ")

            
        # print progress
        print("----------------------------------------------", flush=True)
        temp_runtime = time.time() - start_time_script
        print(f"{count_days} days processed: {temp_runtime/count_days:.2f} seconds or {temp_runtime/count_days/60:.2f} minutes per day", flush=True)
        print(f"total runtime until now: {temp_runtime/60:.2f} minutes or {temp_runtime/60/60:.2f} hours", flush=True)


    # print and store config file in the output directory
    config_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../training/config.py')
    config_dst = os.path.join(os.path.dirname(log_path), f'{today_str}_config_used.py')
    os.system(f"cp {config_src} {config_dst}")
    logging.info(f"Copied config file to {config_dst}")

if __name__ == "__main__":
    main()
