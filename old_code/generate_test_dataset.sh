#!/bin/bash

# Paths to the folders
folder1="/data1/crops/ir108_2013-2014-2015-2016_200K-300K_CMA/1"
folder2="/data1/crops/ir108_2013-2014-2015-2016_200K-300K_CMA_test_msg_icon/1"

# Count the number of files in each folder
count1=$(find "$folder1" -type f | wc -l)
count2=$(find "$folder2" -type f | wc -l)

# Calculate how many files are needed to fill the second folder
difference=$((count1 - count2))

# Check if the second folder needs more files
if [ "$difference" -gt 0 ]; then
    echo "Folder 2 needs $difference more files to match Folder 1."
    
    # Randomly select files from the first folder
    files_to_copy=$(find "$folder1" -type f | shuf -n "$difference")
    
    # Copy the selected files to the second folder
    for file in $files_to_copy; do
        cp "$file" "$folder2"
    done
    
    echo "Copied $difference files from Folder 1 to Folder 2."
else
    echo "Folder 2 already has the same or more files than Folder 1. No action needed."
fi
