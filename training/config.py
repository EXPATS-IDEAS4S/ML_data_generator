# config.py
CLOUD_PRM = ['IR_108'] #list of the channels to use
APPLY_CMA = True # Set to True if you want to apply (corrected) CMA mask to IR_108 channel
CMA_APPLY_CLOSING = True # Apply morphological closing to the CMA mask before masking
CMA_CLOSING_STRUCTURE = [[1, 1, 1], [1, 1, 1], [1, 1, 1]] # Structuring element for CMA closing
CROPPING_STRATEGY = 'random' # 'random' or 'fixed', ranodom mostly used for training, fixed for testing
N_SAMPLES = 2 # Number of random crops to generate per timestamp
TIME_LENGTH = 1 # In case 
TIME_JUMP = 1
CROP_UL_LAT = 50.0
CROP_UL_LON = 6.5
VALUE_MIN = [180.0, 200.0]
VALUE_MAX = [320.0, 260.0]
X_PIXEL, Y_PIXEL = 75, 75
DOMAIN = (5, 16, 42, 51.5)
DOMAIN_NAME = 'EXPATS'
YEARS = [2013, 2017, 2021, 2025]
MONTHS = range(4, 10)
DAYS = range(1, 32)
HOURS = range(0, 24)
PATH_DIR = "/data/sat/msg/ml_train_crops/IR_108-WV_062-CMA_FULL_EXPATS_DOMAIN"
BASENAME = "merged_MSG_CMSAF"
OUTPUT_BASE = "/sat_data/crops/crops_IR_108_CMA_75x75_2013-2017-2021-2025_2-randomcrops/nc/1"
RANDOM_SEED = 42

#nohup  168305 - no closing