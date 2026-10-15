# %%
import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import xarray as xr
import glob
from helper_data_generation import npdatetime_to_string, \
    get_ymd_from_msg_filename, get_all_files_in_study_period

def crop_to_image_size(data_array, image_size):
    n_pix_lat, n_pix_lon = data_array.shape

    # get indices to crop data to given image size
    idx_lat_start = int(n_pix_lat/2) - int(image_size/2)
    idx_lat_end = int(n_pix_lat/2) + int(image_size/2)
    idx_lon_start = int(n_pix_lon/2) - int(image_size/2)
    idx_lon_end = int(n_pix_lon/2) + int(image_size/2)

    return data_array[idx_lat_start: idx_lat_end, idx_lon_start: idx_lon_end]

def save_image(data_array, img_path, cmap, vmin, vmax): 
    # convert to image and save
    plt.imsave(img_path, 
               data_array[::-1,::-1], # array must be flipped along both axes to fit to imshow input
               cmap=cmap, vmin=vmin, vmax=vmax)
    plt.close()

# %%
def generate_images_from_msg_dataset(msg_files, out_path, channel_settings, 
                                     image_size, hour_start, hour_end):

    # loop over files
    for f in msg_files:

        # get year and month from filename
        year, month, day = get_ymd_from_msg_filename(f)

        # define start and end thresholds each day in form of np.datetime64
        # to better compare to timestamps in data file
        day_start = np.datetime64(f"{year}-{month}-{day}T{hour_start}")
        day_end = np.datetime64(f"{year}-{month}-{day}T{hour_end}")

        # open data file
        with xr.open_dataset(f) as data_msg:

            # loop over timestamps
            for timestamp in data_msg.time.values:

                #TODO: this selection of daytimes using xr
                # check if is in given daytime range
                if timestamp > day_start and timestamp < day_end:
                    
                    # select data of this timestamp
                    data_timestamp = data_msg.sel(time=timestamp)

                    # loop over channels that you want to convert into images
                    for ch in channel_settings:

                        # get data from channel and dimensions
                        data_channel = data_timestamp[ch].values

                        #TODO: cropping to image size using xr
                        # crop data to given image size
                        data_channel_crop = crop_to_image_size(data_channel, image_size)

                        # convert to image and save
                        img_path = f"{out_path}/{ch}"
                        if not os.path.exists(img_path):
                            os.makedirs(img_path)
                        img_file = f"{img_path}/{npdatetime_to_string(timestamp)}_{ch}.png"
                        save_image(data_channel_crop, img_file, channel_settings[ch]['cmap'], 
                                   channel_settings[ch]['vmin'], channel_settings[ch]['vmax'])


# %%
if __name__ == "__main__":
    years = [2023]
    months = [7]
    hour_start = "10:00:00"
    hour_end = "16:00:00"
    image_size = 200

    # channel settings (colormaps and value ranges)
    channel_settings = {"VIS006": {"cmap": "gray", 
                                   "vmin": 0.540,  # use minimum of dataset or some quantile?
                                   "vmax": 95.286},  # max of dataset: 93.858  # 0.999 quantile: 83.018
                        "IR_108": {"cmap": "gray_r", 
                                   "vmin": 212.531,  # min of dataset: 212.531, # 0.001 quantile: 216.636
                                   "vmax": 302.123}}  # max of dataset: 302.123  # 0.999 quantile: 297.985

    # define absolute path to msg data
    MSG_PATH = f"/net/merisi/pbigalke/teaching/METFUT2024/msg_test_data"

    # path to project directory
    PROJECT_DIR = "/net/merisi/pbigalke/teaching/METFUT2024/CGAN_Pix2Pix_MSG"
    out_path = f"{PROJECT_DIR}/test_data"
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    # get all msg files within study period
    msg_files = get_all_files_in_study_period(MSG_PATH, years, months)

    # generate images from msg files
    generate_images_from_msg_dataset(msg_files[:1], out_path, channel_settings, 
                                     image_size, hour_start, hour_end)

# %%
