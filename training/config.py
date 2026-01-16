# config.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuration parameters for crop generation
N_BUCKETS = 2 # Number of buckets to use for reading input data
APPLY_CMA = True # Set to True if you want to apply (corrected) CMA mask to IR_108 channel
CROPPING_STRATEGY = 'random' # 'random' or 'fixed', ranodom mostly used for training, fixed for testing
N_SAMPLES = 2 # Number of random crops to generate per timestamp
TIME_LENGTH = 1 # In case 
TIME_JUMP = 1
TIME_RESOLUTION = '15min' # '15min', '1H', etc. time resolution of the input data
CROP_UL_LAT = 50.0
CROP_UL_LON = 6.5
VALUE_CLOUD_MASK_REPLACE = [320.0, 0.0] # value to insert in the cloud-free areas after applying CMA mask
X_PIXEL, Y_PIXEL = 70, 70 # size of the crops in pixels
OUTPUT_BASE = "/data1/crops" 
QUICKLOOKS_CROPS = True # if true, quicklooks of the generated crops will be created and saved in the img folder


# specific for data used in the paper: domain, temporal extent, paths, 
DOMAIN = (5, 16, 42, 51.5)
DOMAIN_NAME = 'EXPATS'
YEARS = [2013, 2014]
MONTHS = range(4, 5)
DAYS = range(1, 32)
MONTH_START, MONTH_END = '04', '09'
DAY_START, DAY_END = '01', '31'
HOUR_START, HOUR_END = '00', '24'


# variables to be processed and related input paths
CLOUD_PRM = ['IR_108', 'cma', 'RR'] #list of variable fields to use (sat channels, radar or other variables from different sources)
VALUE_MIN = [240., 0, 0.0]  # min value for each variable to consider as cloud-free when applying CMA mask
VALUE_MAX = [290., 1, 20.0] # max value for each variable to consider as cloud-free when applying CMA mask
PATH_DIR = ["/data/sat/msg/ml_train_crops/IR_108-WV_062-CMA_FULL_EXPATS_DOMAIN", "/data/sat/msg/ml_train_crops/IR_108-WV_062-CMA_FULL_EXPATS_DOMAIN", ""]
BASENAME = ["merged_MSG_CMSAF", "merged_MSG_CMSAF","_RR_15min_msg_res"] # name string for the output files of the crops
BUCKET_NAMES = ["expats-msg-training", "expats-msg-training", "expats-radar-germany"] # S3 bucket names for each variable