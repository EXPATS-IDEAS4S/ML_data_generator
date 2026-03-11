# config.py
import sys
import os
from cmcrameri import cm
from matplotlib.colors import ListedColormap, BoundaryNorm

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

#  space-time parameters
################################################################
N_FRAMES = 16 # number of frames in time for space-time crops
# if N_FRAMES = 1 discard to set other space time parameters
N_RANDOM_TIMES = 4 # number of random start times to collect for each iteration of ind_start_time in range(0, len(ds_crop.time.values), N_FRAMES)
#MAX_TEMPORAL_OVERLAP = 0.25 # maximum temporal overlap between crops from the same time series (0.25 = 25%)
#MAX_DAILY_OFFSET = None  # one can set a random offset at the beginning of the day to introduce a randomness in the timeseries starting times
#MAX_CROPPING_ATTEMPTS =  10 
################################################################


# Configuration parameters for crop generation
################################################################
N_BUCKETS = 1 # Number of buckets to use for reading input data
APPLY_CMA = True # Set to True if you want to apply (corrected) CMA mask to IR_108 channel
CROPPING_STRATEGY = 'random' # 'random' or 'fixed', ranodom mostly used for training, fixed for testing / discarded, CMA is provided as input channel
N_SAMPLES = 4 # Number of random crops to generate in space per timestamp
if N_FRAMES > 1:
    TIME_LENGTH = N_FRAMES # for space-time crops
else:
    TIME_LENGTH = 1 # for spatial crops
TIME_JUMP = 1
TIME_RESOLUTION = '15min' # '15min', '1H', etc. time resolution of the input data
CROP_UL_LAT = 50.0
CROP_UL_LON = 6.5
X_PIXEL, Y_PIXEL = 100, 100 # size of the crops in pixels
OUTPUT_BASE = "/sat_data/GRL_training_crops/" # base path for the output crops, if BUCKET_NAMES is set to None, otherwise the crops will be directly uploaded to the buckets indicated in BUCKET_NAMES
QUICKLOOKS_CROPS = False # if true, quicklooks will be generated based on the parameters to set below 
################################################################


# specific for dataset used in the paper: domain, temporal extent, paths, 
################################################################
DOMAIN = (5, 16, 42, 51.5)
DOMAIN_NAME = 'EXPATS'
RESAMPLING_MTG_RES = False # if true, in case of N_BUCKETS = 1, data is resampled to MTG resolution
YEARS = [2011] # years to consider for the crop generation
MONTHS = [4, 5, 6, 7, 8, 9]
DAYS = range(1, 32)
MONTH_START, MONTH_END = '04', '09'
DAY_START, DAY_END = '01', '31'
HOUR_START, HOUR_END = '00', '24'
################################################################


# variables to be processed and related input paths
################################################################
"""
Note on vars to select in CLOUD_PRM: select one of the two radar variables RR_de or RR_it, not both.
RR_de: radar data for Germany from DWD
RR_it: radar data for Italy from ARPAE
For sampling from both domains, run the script twice with different CLOUD_PRM and PATH_DIR settings.
Select from template below the settings you want to use. Keep MSG channel as first variable in the list.
Order matters:  consult plotting/plotting_dict.py to check that the order is consistent with what indicated below

CLOUD_PRM = ['IR_108', 'cma', 'RR_de', "RR_it"] # list of variable fields to use (sat channels, radar or other variables from different sources)
VALUE_MIN = [240., 0, 0.0, 0.0]  # min value for each variable to consider as cloud-free when applying CMA mask
VALUE_MAX = [290., 1, 20.0, 20.] # max value for each variable to consider as cloud-free when applying CMA mask
PATH_DIR = ["/data/sat/msg/ml_train_crops/IR_108-WV_062-CMA_FULL_EXPATS_DOMAIN", "/data/sat/msg/ml_train_crops/IR_108-WV_062-CMA_FULL_EXPATS_DOMAIN", "", "/home/vpoli@ARPA.EMR.NET/dati_claudia/composito/"]
BASENAME = ["merged_MSG_CMSAF", "merged_MSG_CMSAF","_RR_DE_15min_msg_res", ""] # name string for the output files of the crops
BUCKET_NAMES = ["expats-msg-training", "expats-msg-training", "expats-radar-germany", "arpae-radar-composite"] # S3 bucket names for each variable
VALUE_CLOUD_MASK_REPLACE = [320.0, 0.0, 0.0, 0.0] # value to insert in the cloud-free areas after applying CMA mask

"""
vars = ['IR_108', 'cma', 'RR_de'] # list of variable fields to use (sat channels, radar or other variables from different sources)
paths = ["/data/sat/msg/ml_train_crops/IR_108-WV_062-CMA_FULL_EXPATS_DOMAIN", "/data/sat/msg/ml_train_crops/IR_108-WV_062-CMA_FULL_EXPATS_DOMAIN", ""]
basenames = ["merged_MSG_CMSAF", "merged_MSG_CMSAF","_RR_DE_15min_msg_res"] # name string for the output files of the crops
bucketnames = ["expats-msg-training", "expats-msg-training", "expats-radar-germany"] # S3 bucket names for each variable   
valuesCloudMaskReplace = [320.0, 0.0, 0.0] # value to insert in the cloud-free areas after applying CMA mask, if APPLY_CMA is True / discarded, CM is provided as input channel
valueCheckMin = [180., 0, 0.0]  # min value for quality check of the variable 
valueCheckMax = [310., 1, 50.0] # max value for quality check of the variable chat
valueMin = [240., 0, 0.0]  # min value for each variable to consider as cloud-free when applying CMA mask
valueMax = [290., 1, 20.0] # max value for each variable to consider as cloud-free when applying CMA mask
units = ['K', '', 'mm'] # units for each variable, used for plotting
titles = ['IR 10.8 Micron', 'Cloud mask', 'Accumulated rain'] # titles for each variable, used for plotting

# selecting vars to plot based on N_BUCKETS, if N_BUCKETS < len(CLOUD_PRM), the lists below will be sliced to keep only the first N_BUCKETS elements, otherwise all variables are kept
# NOTE: set to N_BUCKETS+1 to keep Cloud mask as variable
CLOUD_PRM = vars[:N_BUCKETS+1]
PATH_DIR = paths[:N_BUCKETS+1]
BASENAME = basenames[:N_BUCKETS+1]
BUCKET_NAMES = bucketnames[:N_BUCKETS+1]
VALUE_CLOUD_MASK_REPLACE = valuesCloudMaskReplace[:N_BUCKETS+1]
VALUE_CHECK_MIN = valueCheckMin[:N_BUCKETS+1]
VALUE_CHECK_MAX = valueCheckMax[:N_BUCKETS+1] 
VALUE_MIN = valueMin[:N_BUCKETS+1]
VALUE_MAX = valueMax[:N_BUCKETS+1]
UNITS = units[:N_BUCKETS+1]
TITLES = titles[:N_BUCKETS+1]
################################################################

# plotting parameters for each variable colorbar, see plotting/plotting_dict.py, if None, default settings are used in the plotting functions
######################################
# specific settings for the CMA mask, used for plotting, if CMA is applied and provided as input channel, see COLORBARS below
cmap_cma = ListedColormap(['lightgrey', 'yellow'])
bounds = [-0.5, 0.5, 1.5]
norm = BoundaryNorm(bounds, cmap_cma.N)

# colorbar settings
norms = [None, norm, None] # normalization for each variable, used for plotting, if None, no normalization is applied
cbar_ticks = [None, [0, 1], None] # colorbar ticks for each variable, used for plotting, if None, default ticks are used
colorbars = [cm.batlow_r, cmap_cma, cm.acton_r] # colorbar for each variable, used for plotting
################################################################
NORMS = norms[:N_BUCKETS+1]
CBAR_TICKS = cbar_ticks[:N_BUCKETS+1]
COLORBARS = colorbars[:N_BUCKETS+1]