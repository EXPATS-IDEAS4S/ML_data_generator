import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import xarray as xr
from glob import glob
import os

def generate_transparent_overlay_from_grid(lat_array, lon_array, output_file):
    """
    Generate a transparent overlay image with borders and lat/lon ticks using latitude and longitude arrays.

    Parameters:
    - lat_array: 1D array of latitude values.
    - lon_array: 1D array of longitude values.
    - output_file: Path to save the transparent image (e.g., 'overlay.png').
    """
    # Get bounds from the latitude and longitude arrays
    lat_min, lat_max = lat_array.min(), lat_array.max()
    lon_min, lon_max = lon_array.min(), lon_array.max()

    # Create a figure with transparent background
    fig, ax = plt.subplots(
        figsize=(10, 8),
        subplot_kw={"projection": ccrs.PlateCarree()},
        dpi=300
    )
    fig.patch.set_alpha(0)  # Make the entire figure background transparent
    ax.patch.set_alpha(0)   # Make the axis background transparent

    # Set the extent (lat/lon bounds) and add borders
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.BORDERS, linestyle='-', edgecolor='black', linewidth=1)
    ax.add_feature(cfeature.COASTLINE, edgecolor='black', linewidth=1)

    # Add gridlines and show ticks only on one side (e.g., left and bottom)
    gl = ax.gridlines(draw_labels=True, color='gray', alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
    gl.left_labels = True
    gl.bottom_labels = True
    gl.xlabel_style = {"size": 10, "color": "black"}
    gl.ylabel_style = {"size": 10, "color": "black"}

    # Remove all other visual elements
    ax.spines['geo'].set_visible(False)

    # Save the figure with transparent background
    plt.savefig(output_file, transparent=True, bbox_inches='tight', pad_inches=0)
    plt.close()
    print(f"Overlay image saved to {output_file}")


def plot_variable_from_nc(
    title,
    nc_file, 
    variable_name, 
    vmin=None, 
    vmax=None,
    figsize=(10, 8), 
    cmap="viridis", 
    output_file=None,
    borders_color="red",
    ticks=True
):
    """
    Plot a variable from a NetCDF file with borders and optional latitude/longitude ticks.

    Parameters:
    - nc_file: Path to the NetCDF file.
    - variable_name: Name of the variable to plot.
    - figsize: Tuple specifying the figure size (width, height).
    - cmap: Colormap to use for the variable.
    - vmin: Minimum value for the color scale (optional).
    - vmax: Maximum value for the color scale (optional).
    - output_file: Path to save the output plot (optional). If None, the plot is displayed.
    - borders_color: Color for the country borders.
    - ticks: Whether to show latitude and longitude ticks.
    """
    
    # Load the NetCDF file
    with xr.open_dataset(nc_file) as ds:
        # Extract latitude, longitude, and the selected variable
        lat = ds["lat"].values
        lon = ds["lon"].values
        data = ds[variable_name].values.squeeze()
    #print(lat)
    #print(lon)
    #print(data)
    # Create the figure and axis with a Cartopy projection
    fig, ax = plt.subplots(
        figsize=figsize,
        subplot_kw={"projection": ccrs.PlateCarree()}
    )

    # Plot the variable as an image
    img = ax.pcolormesh(lon, lat, data, cmap=cmap, vmin=vmin, vmax=vmax, transform=ccrs.PlateCarree())

    # Add borders
    ax.add_feature(cfeature.BORDERS, edgecolor=borders_color, linewidth=1)
    ax.add_feature(cfeature.COASTLINE, edgecolor=borders_color, linewidth=0.8)

    # Optionally add gridlines for lat/lon ticks
    if ticks:
        gl = ax.gridlines(draw_labels=True, color="gray", alpha=0.5, linestyle="--")
        gl.right_labels = False
        gl.top_labels = False
        gl.xlabel_style = {"size": 7}
        gl.ylabel_style = {"size": 7}

    # Add a colorbar
    cbar = fig.colorbar(img, ax=ax, orientation="vertical", shrink=0.7, pad=0.05)
    cbar.set_label(variable_name, fontsize=12)

    # Add a title
    #ax.set_title(f"{variable_name} from {nc_file.split('/')[-1]}", fontsize=14)
    ax.set_title(f"{title}", fontsize=12, fontweight='bold')

    # Save or show the plot
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"Plot saved to {output_file}")
    else:
        plt.show()

    # Close the figure
    plt.close(fig)


# # Example usage
# nc_file = "/data1/other_data/Case_Studies/Marche_Flood_22/MSG/nc/IR_108_128x128_20220914_20:00.nc"  # Replace with your NetCDF file path
# output_file = "/data1/other_data/Case_Studies/Marche_Flood_22/overlay.png"  # Path to save the transparent overlay

# # Open the NetCDF file and extract lat/lon arrays
# with xr.open_dataset(nc_file) as ds:
#     lat_array = ds['lat'].values  # Replace 'lat' with the correct variable name in your file
#     lon_array = ds['lon'].values  # Replace 'lon' with the correct variable name in your filen

# generate_transparent_overlay_from_grid(lat_array, lon_array, output_file)

input_type = 'MSG'  # 'msg' or 'icon'

# Inputs
nc_file_folder = f"/data1/other_data/Case_Studies/Marche_Flood_22/{input_type}/"

output_folder = f"/data1/other_data/Case_Studies/Marche_Flood_22/{input_type}/image_to_plot/"
os.makedirs(output_folder, exist_ok=True)

# open tif files ised to training to maintain same name formate
training_folder = '/data1/crops/ir108_2013-2014-2015-2016_200K-300K_CMA_test_msg_icon/1/'

if input_type == 'ICON':
    variable_name = "synmsg_bt_cl_ir10.8"
    file_list = sorted(glob(nc_file_folder + "crop_nc/*.nc"))
    tif_files = sorted(glob(training_folder + "cropped_icon_*_200K-300K_greyscale.tif"))
elif input_type == 'MSG':
    variable_name = "IR_108"
    file_list = sorted(glob(nc_file_folder + "nc/IR_108_128x128_20220915_*:00.nc"))
    tif_files = sorted(glob(training_folder + "IR_108_128x128_20220915_*_200K-300K_greyscale_CMA.tif"))
else:
    print('input type not recognized')

vmin = 200
vmax = 300
figsize = (3, 3)  # Set the size of the plot
cmap = "coolwarm"  # Choose a colormap

for nc_file, tif_file in zip(file_list, tif_files): 

    # extract filename
    filename = tif_file.split('/')[-1]
    print(filename)

    # Generate plot
    plot_variable_from_nc(
        title=input_type,
        nc_file=nc_file,
        variable_name=variable_name,
        vmin=vmin,
        vmax=vmax,
        figsize=figsize,
        cmap=cmap,
        output_file=output_folder+filename,  # Save the plot (optional)
        borders_color="black",
        ticks=True
    )
    

