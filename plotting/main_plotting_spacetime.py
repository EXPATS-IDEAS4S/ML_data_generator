
"""
Main code to call plotting functions for space-time crops. 
This code is used to create quicklook images and videos of 
the space-time crop evolution in time.

author: Claudia Acquistapace
date: 2024-06-20


executee with command:
python3 -m plotting.main_plotting_spacetime

"""

import os
import sys
# Add the parent directory to sys.path so 'training' can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from training.config import *

from plotting.plot_crops import video_quicklook, plot_crops_quicklooks_2fields


def main():

    # Define the path to the ncdf files of the space-time crops and the output directory for the quicklooks
    path_nc_files = "/data1/crops/crops_IR_108_cma_RR_de_70x70_2013-2014_2-random-nframes-8"
    output_dir = path_nc_files + "/quicklooks/"
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    
    # list all ncdf files in the path
    nc_files = [f for f in os.listdir(path_nc_files) if f.endswith('.nc')]

    # select ncfiles for the date 20130526 (most rainy day in 2013-2014)
    nc_files_daySel = [f for f in nc_files if "20130525" in f]

    for file in nc_files:

        print(f"Creating quicklook for file: {file}")
        # create quicklook video for the selected ncdf file
        video_path = video_quicklook(os.path.join(path_nc_files, file), output_dir) 

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

