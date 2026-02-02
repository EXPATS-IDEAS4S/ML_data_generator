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

# instructiosn to import from parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cropping_functions import crops_nc_random, crops_nc_fixed, filter_by_domain, filter_by_time, apply_cma_mask
from credentials_buckets import S3_ACCESS_KEY, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL
from config import *

import boto3
from botocore.exceptions import ClientError


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
            file_path = f"{year:04d}{month:02d}{day:02d}{BASENAME[i]}.nc.gz"

        elif var == 'RR_it':
            file_path = f"{PATH_DIR[i]}/COMP_{year:04d}{month:02d}{day:02d}{BASENAME[i]}.nc.gz"
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
    is_all_nan_ds = all([xr.DataArray.isnull(ds_time[var]).all() for var in ds_time.data_vars])
    is_outside_range = any(
        [((ds_time[var] < vmin) | (ds_time[var] > vmax)).any()
         for var, vmin, vmax in zip(ds_time.data_vars, VALUE_MIN, VALUE_MAX)]
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

def prepare_joint_dataset(s3, bucket_names, file_names):
    """
    Prepares a joint xarray Dataset by reading and merging data from multiple S3 buckets. it reads and 
    then merges the datasets for all variables specified in CLOUD_PRM. It identifies the common domain across all datasets
    and resamples datasets to the highest resolution before merging.

    input:
        s3: S3 client
        bucket_names: list of S3 bucket names for each variable
        file_names: list of file paths within the buckets for each variable
    output:
        Merged xarray Dataset containing data from all specified buckets and files.
        domain where all data are available: tuple with (lon_min, lon_max, lat_min, lat_max)
    dependencies:
        read_file
        CLOUD_PRM

    """
    # initialize lists to store datasets and domain edges
    ds_arr = []
    lats_min_list = []
    lons_min_list = []
    lats_max_list = []
    lons_max_list = []

    # read and process each variable from its respective bucket
    for i_var, var_name in enumerate(CLOUD_PRM):

        # read file object from S3 bucket
        file_obj = read_file(s3, file_names[i_var], bucket_names[i_var])

        if var_name == 'RR_it':
            # print files in the bucket
            all_files = print_list_files_in_bucket(s3, bucket_names[i_var])
            # if file not found, skip
            pdb.set_trace()


        if file_obj is None:
            continue
        if var_name == 'RR_de' or var_name == 'RR_it':
            # decompress gzip file
            ds = xr.open_dataset(io.BytesIO(gzip.decompress(file_obj)))
        else:
            ds = xr.open_dataset(io.BytesIO(file_obj))
        print(ds)
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



def main():

    # start logger and initialize s3 client
    setup_logger()
    s3 = init_s3()

    # creating output directory for nc files and images of the crops
    cloud_prm_str = "_".join(CLOUD_PRM)
    years_str = "-".join(map(str, YEARS))
    outpath = os.path.join(OUTPUT_BASE, f"crops_{cloud_prm_str}_{X_PIXEL}x{Y_PIXEL}_{years_str}_{N_SAMPLES}-{CROPPING_STRATEGY}/nc")
    os.makedirs(outpath, exist_ok=True)

    # iterate over years, months, days to read files from S3 bucket
    for year in YEARS:
        for month in MONTHS:
            for day in DAYS:

                # read variables to read and access all files with their corresponding paths built with a function
                bucket_names, file_names = read_bucket_name_path(year, month, day)

                # prepare joint dataset
                ds_crop, domain_all_data = prepare_joint_dataset(s3, bucket_names, file_names)

                if ds_crop is None:
                    logging.info(f"No valid data found for {year}-{month:02d}-{day:02d}. Skipping.")
                    continue
                
                # extraction of crops for each timestamp and plotting
                for timestamp in ds_crop.time.values:
                    try:
                        ds_time = filter_by_time(ds_crop, timestamp)
                        crop_individual_timestamps(ds_time, timestamp, domain_all_data, outpath)
                    except Exception as e:
                        logging.warning(f"Skipping timestamp {timestamp} due to (sono qui): {e}")
                        traceback.print_exc()


    # print and store config file in the output directory
    config_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../training/config.py')
    config_dst = os.path.join(os.path.dirname(outpath), 'config_used.py')
    os.system(f"cp {config_src} {config_dst}")
    logging.info(f"Copied config file to {config_dst}")

if __name__ == "__main__":
    main()
