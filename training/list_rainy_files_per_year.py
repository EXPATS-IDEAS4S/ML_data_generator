"""
This code checks sorts the radar files for each year by file size, and then print the files 
with the largest file size for each year in a txt file
This is useful to identify the rainy files, which are usually larger than the non-rainy files.

author: Claudia Acquistapace
date: 2024-06-20
email: claudia.acquistapace@unipd.it

execute with command:
python3 -m training.list_rainy_files_per_year

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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
from .config import *
import boto3
from data_bucket_functions import list_files_bucket
from credentials_buckets import S3_ACCESS_KEY, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL

def main():

    # radar data bucket name
    bucket_name = BUCKET_NAMES[2] # select the bucket name for the radar data (RR_de or RR_it)
    s3 = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY)
    
    # extract for each file, filename and dimension of the file
    files_info = []
    for file in list_files_bucket(s3, bucket_name):
        files_info.append((file['Key'], file['Size'] / (1024 * 1024)))  # Convert size to MB

    # create one list fot each year with the files and their size

    # list years from 2013 to 2025
    year_list = [str(year) for year in range(2013, 2026)]

    # create list for each year and store them in txt files with the name "radar_files_year.txt"
    output_dir = "/home/claudia/info_data/"
    for year in year_list:
        files_info_year = [f for f in files_info if year in f[0]]
        files_info_year.sort(key=lambda x: x[1], reverse=True)  # sort by size in descending order
        with open(f"{output_dir}/radar_files_{year}.txt", "w") as f:
            for file_info in files_info_year:
                f.write(f"{file_info[0]}: {file_info[1]:.2f} MB\n")


    print(files_info)

if __name__ == "__main__":
    main()