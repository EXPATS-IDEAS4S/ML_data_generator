
from training.config import *
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
import boto3
from training.data_bucket_functions import init_s3
# instructiosn to import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():


    print(" checking the disk space occupied by data buckets")
    buckets_name_list = ["expats-radar-germany", 
                        "expats-radar-italy",
                        "expats-cmsaf-cloud", 
                        "arpae-radar-composite", 
                        "expats-imerg-prec", 
                        "hsaf-h10-nc", 
                        "expats-euclid",
                        "expats-msg-training",
                        "radar-protezione-civile",
                        "radar-ch"
                        ]

    s3 = init_s3()
    total_bucket_size = 0
    for bucket in buckets_name_list:

        total_size = 0
        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                total_size += obj["Size"]

        print(f"Total size for bucket {bucket}: {total_size / (1024**3):.2f} GB")
        total_bucket_size += total_size

    print(f"Total size for all buckets: {total_bucket_size / (1024**3):.2f} GB")



if __name__ == "__main__":
    main()

