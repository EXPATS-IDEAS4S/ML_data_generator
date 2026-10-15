import xarray as xr
import os
from glob import glob
import time
import numpy as np
import matplotlib.pyplot as plt

import PIL



def create_fig(image, pixel_size, cmap, dpi=1, vmin=None, vmax=None, flip=True):
    """
    Creates and returns a matplotlib figure with the given pixel size from an image.

    This function generates a matplotlib figure using the specified image and pixel size. 
    The figure is created with `dpi=1` to ensure the pixel size directly corresponds 
    to the figure size.

    :param image: The image to be plotted, compatible with matplotlib's imshow function.
    :param pixel_size: A tuple representing the pixel size (width, height) to be used as the figure size.
    :param vmin: The minimum data value that corresponds to the colormap's lower limit.
    :param vmax: The maximum data value that corresponds to the colormap's upper limit.
    :param flip: If True, the image will be flipped upside down before being plotted.
    :return: The created matplotlib figure.
    """
    if flip:
        image = np.flipud(image)
    fig, ax = plt.subplots(figsize=pixel_size, dpi=dpi)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.imshow(image, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.axis(False)
    plt.close(fig)
    return fig



def convert_crops_to_images(ds_image, x_pixel, y_pixel, filename, format, out_path, cmap, vmin, vmax, norm_type, color_mode, apply_cma):
    """
    Generates a cropped image from the input dataset and saves it in the specified format.

    This function takes an input dataset and generates a cropped image based on the specified 
    pixel dimensions (x_pixel, y_pixel). The cropped image is saved using the specified format 
    (e.g., TIFF, PNG) and file path. The function uses the provided colormap and value range 
    (vmin, vmax) to enhance the image visualization. It also allows saving images in RGB or greyscale.

    Parameters:
    -----------
    ds_image : xarray.Dataset or xarray.DataArray
        The input dataset or data array containing the image data, typically including 
        associated latitude and longitude coordinates.
    
    x_pixel : int
        The width of the crop in pixels.
    
    y_pixel : int
        The height of the crop in pixels.
    
    filename : str
        The base filename used to save the cropped image.
    
    format : str
        The format in which the cropped image will be saved (e.g., 'tiff', 'png').
    
    out_path : str
        The directory path where the cropped image will be saved.
    
    cmap : str
        The colormap to use for visualizing the image.
    
    vmin : float
        The minimum value for color scaling in the image visualization.
    
    vmax : float
        The maximum value for color scaling in the image visualization.
    
    color_mode : str, optional (default='RGB')
        The color mode for saving the image, either 'RGB' or 'greyscale'.

    Returns:
    --------
    None
        The function does not return any value. It saves the cropped image to the specified file path.
    """

    
    #save the images
    fig = create_fig(ds_image.values.squeeze(),[x_pixel,y_pixel], cmap, 1, vmin, vmax)

    # Define output directory
    out_dir = f'{out_path}{format}_{norm_type}_{color_mode}'

    # Check if the directory exists
    if not os.path.exists(out_dir):
        # Create the directory if it doesn't exist
        os.makedirs(out_dir) 

    crop_filepath = f'{out_dir}/{filename}_{norm_type}_{color_mode}.{format}'
    if apply_cma:
        crop_filepath = f'{out_dir}/{filename}_{norm_type}_{color_mode}_CMA.{format}'

    fig.savefig(crop_filepath, dpi=1)

    print(f'{crop_filepath} is saved')

    # Open the saved image for conversion
    image = PIL.Image.open(crop_filepath)

    # Convert based on the specified color mode
    if color_mode == 'RGB':
        converted_image = image.convert('RGB')
        converted_image.save(crop_filepath)
        print(f'{crop_filepath} converted to RGB')
    elif color_mode == 'greyscale':
        converted_image = image.convert('L')  # 'L' mode is greyscale in PIL
        converted_image.save(crop_filepath)
        print(f'{crop_filepath} converted to greyscale')
    else: 
        print('color mode not recognized!')

    # Close the image to free resources
    converted_image.close()
    image.close()


# Function to extract time from a NetCDF file
def extract_time(nc_file):
    with xr.open_dataset(nc_file) as ds:
        # Adjust based on your NetCDF time variable name
        return ds['time'].values if 'time' in ds else None



start_time = time.time()

image_format = 'tif'

cloud_prm = "synmsg_bt_cl_ir10.8" #'IR_108' #'cot', WV_062, IR_039

cmap='Greys' #'Spectral_r' #Gray

colormode = 'greyscale'

x_pixel = 128
y_pixel = 128

crops_path = '/data1/other_data/Case_Studies/Marche_Flood_22/ICON/crop_nc/'

cma_path = '/data1/other_data/Case_Studies/Marche_Flood_22/MSG/nc_clouds/'

apply_cma = False

out_dir = f'/data1/other_data/Case_Studies/Marche_Flood_22/ICON/'

crop_file_list = sorted(glob(crops_path+'*.nc'))
print('total msg crops are - '+ str(len(crop_file_list)))

cma_file_list = sorted(glob(cma_path+'*.nc'))
print('total cma crops are - '+ str(len(cma_file_list)))

if apply_cma and len(crop_file_list)!=len(cma_file_list):
    print('crops and cma do not match!')
    #exit()

# Open the csv file with hte crops statistics
#crop_stat = os.path.join(out_dir, f'{cloud_prm}_statistics.csv')

if apply_cma:
    #crop_stat = os.path.join(out_dir, f'{cloud_prm}_statistics_CMA.csv')
    out_dir = out_dir+'CMA/'
    


#df = pd.read_csv(crop_stat)

# Define the name of the normalization depending on the lower and upper bounds
norm_types =  ['200K-300K'] #['Min-Max', '1th-99th', '5th-95th','10th-90th','25th-75th']

# Preprocess CMA files to index by time for easy lookup
cma_time_to_file = {}
for cma_file in cma_file_list:
    cma_time = extract_time(cma_file)
    if cma_time is not None:
        cma_time_to_file[cma_time] = cma_file

# Loop over normalization types
for norm_type in norm_types:
    print(norm_type)
    vmin = 200
    vmax = 300

    # Loop over the MSG crop files
    for msg_crop in crop_file_list:
        # Extract filename and time
        filename = msg_crop.split('/')[-1].split('.')[0]
        print(f"Processing {filename}...")
        msg_time = extract_time(msg_crop)[0]
        print(msg_time)

        # Find the matching CMA file by time
        cma_crop = cma_time_to_file.get(msg_time)

        if not cma_crop:
            print(f"No matching CMA file found for {filename}. Skipping.")
            continue

        # Open the MSG crop
        msg_ds = xr.open_dataset(msg_crop)
        msg_ds = msg_ds[cloud_prm]

        # Apply cloud mask if enabled
        if apply_cma:
            cma_ds = xr.open_dataset(cma_crop)
            cloud_mask = cma_ds['cma']
            msg_ds = msg_ds.where(cloud_mask == 1, vmax)

        # Convert crops to images
        convert_crops_to_images(
            msg_ds, x_pixel, y_pixel, filename, image_format, out_dir,
            cmap, vmin, vmax, norm_type, colormode, apply_cma
        )

print('Crops conversion to images is done!')
            
end_time = time.time()

elapsed_time = end_time - start_time
print(f"Total execution time: {elapsed_time:.2f} seconds")     