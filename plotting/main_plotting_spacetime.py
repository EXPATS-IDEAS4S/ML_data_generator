
"""
Main code to call plotting functions for space-time crops. 
This code is used to create quicklook images and videos of 
the space-time crop evolution in time.

author: Claudia Acquistapace
date: 2024-06-20


executee with command:
python3 -m plotting.main_plotting_spacetime

"""
import logging
import os
import sys
# Add the parent directory to sys.path so 'training' can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from training.config import *

from plotting.plot_crops import video_quicklook, plot_crops_quicklooks_2fields

def setup_logger():
    """
    Sets up the logging configuration.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():

    # start logger and initialize s3 client
    setup_logger()

    # Define the path to the ncdf files of the space-time crops and the output directory for the quicklooks
    path_nc_files = "/data1/crops/crops_IR_108_cma_RR_de_70x70_2013-2014_2-random-nframes-8"
    output_dir = path_nc_files + "/quicklooks/"
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    
    # list all ncdf files in the path
    nc_files = [f for f in os.listdir(path_nc_files) if f.endswith('.nc')]

    # sort ncdf files by timestamp
    nc_files = sorted(nc_files)
    logging.info(f"files to process: {nc_files}")
    logging.info(f"number of files to process: {len(nc_files)}")

    for file in nc_files:

        print(f"Creating quicklook for file: {file}")

        # read if the ncdf is from crop 0 or crop 1, to select the correct plotting function
        if "_0.nc" in file:
            crop_id = 0
        elif "_1.nc" in file:
            crop_id = 1
        
        print(f"Creating quicklook for file: {file} with crop_id: {crop_id}")

        # create quicklook video for the selected ncdf file
        video_path = video_quicklook(os.path.join(path_nc_files, file), output_dir, crop_id) 

        # if quicklook video is created, remove all png images in the output directory
        if os.path.exists(video_path):
            for f in os.listdir(output_dir):
                if f.endswith('.png'):
                    os.remove(os.path.join(output_dir, f))

    if os.path.exists(video_path):
        for f in os.listdir(output_dir):
            if f.endswith('.png'):
                os.remove(os.path.join(output_dir, f))

if __name__ == "__main__":
    main()

