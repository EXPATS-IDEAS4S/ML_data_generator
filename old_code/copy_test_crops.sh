#!/bin/bash

# Set the source folder, destination folder, and filename pattern here
SOURCE_FOLDER="/data1/other_data/Case_Studies/Marche_Flood_22/ICON/tif_200K-300K_greyscale"
DESTINATION_FOLDER="/data1/crops/ir108_2013-2014-2015-2016_200K-300K_CMA_test_msg_icon/1"
FILENAME_PATTERN="cropped_icon_2022-09-15T*_200K-300K_greyscale.tif" # Change this pattern as needed

# Create the destination folder if it doesn't exist
mkdir -p "$DESTINATION_FOLDER"

# Copy files matching the pattern
find "$SOURCE_FOLDER" -type f -name "$FILENAME_PATTERN" -exec cp {} "$DESTINATION_FOLDER" \;

echo "Files matching pattern '$FILENAME_PATTERN' have been copied from '$SOURCE_FOLDER' to '$DESTINATION_FOLDER'."
