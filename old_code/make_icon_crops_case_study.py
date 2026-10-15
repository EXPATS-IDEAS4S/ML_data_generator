import os
import xarray as xr
import numpy as np
from glob import glob

def crop_and_save_nc(crop_folder, data_folder, output_folder, variable_name):
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # List crop files and data files
    crop_files = sorted(glob(os.path.join(crop_folder, "*20220915*.nc")))
    data_files = sorted([os.path.join(data_folder, f) for f in os.listdir(data_folder) if f.endswith("reg.grb.nc")])
    #print(crop_files)
    #print(len(data_files))  

    # Loop through crop files and process
    for crop_file in crop_files:
        # Open crop file and get timestamp and coordinates
        crop_ds = xr.open_dataset(crop_file)
        #print(crop_ds)

        crop_time = crop_ds.time.values  # Assuming 'time' is the time coordinate
        crop_lat = crop_ds.lat.values    # Assuming 'lat' is the latitude coordinate
        crop_lon = crop_ds.lon.values    # Assuming 'lon' is the longitude coordinate

        # Match data file by timestamp
        matching_data_file = None
        for data_file in data_files:
            data_ds = xr.open_dataset(data_file)
          
            if crop_time in data_ds.time.values:
                matching_data_file = data_file
                data_ds.close()
                break
            data_ds.close()

        if matching_data_file is None:
            print(f"No matching data file found for time {crop_time}")
            continue

        # Open matching data file and extract the specified variable
        data_ds = xr.open_dataset(matching_data_file)
        selected_var = data_ds[variable_name]

        # Interpolate the data onto the grid of crop_ds
        interpolated_data = selected_var.interp(
            lat=crop_ds.lat,
            lon=crop_ds.lon,
            method="linear"  # You can use "nearest", "linear", or "cubic" as needed
        )

        #print(interpolated_data)
        #exit()

        # Save the cropped data to a new NetCDF file
        output_filename = os.path.join(output_folder, f"cropped_icon_{crop_time[0]}.nc")
        interpolated_data.to_netcdf(output_filename)
        print(f"Saved cropped file: {output_filename}")

        # Close datasets
        crop_ds.close()
        data_ds.close()

# Define paths and variable name
crop_folder = "/data1/other_data/Case_Studies/Marche_Flood_22/MSG/nc"
data_folder = "/data1/other_data/Case_Studies/Marche_Flood_22/ICON/full_nc"
output_folder = "/data1/other_data/Case_Studies/Marche_Flood_22/ICON/crop_nc"
variable_name = "synmsg_bt_cl_ir10.8"  # Replace with the actual variable name

# Run the function
crop_and_save_nc(crop_folder, data_folder, output_folder, variable_name)
