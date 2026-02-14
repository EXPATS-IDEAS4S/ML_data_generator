import xarray as xr
from random import randrange
import numpy as np
import matplotlib.pyplot as plt
import os
import PIL
from scipy.ndimage import binary_closing
from config import *
import matplotlib.pyplot as plt
import cartopy.feature as cfeature  
import cartopy.crs as ccrs
import numpy as np
import logging
import pdb
import matplotlib.gridspec as gridspec
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.colors import ListedColormap
from training.config import *
import ffmpeg

def read_orography():

    ds = xr.open_dataset("/data1/DEM_EXPATS_0.01x0.01.nc")
    print(ds)

    return ds



def retrieve_plotting_params_from_config(variable):
    """
    Retrieve plotting parameters for a given variable from the plotting_dict 
    using settings defined in the config file. This allows to keep all 
    plotting parameters in a single place and avoid hardcoding them 
    in the plotting functions.
    The plotting_dict is generated as a loop on CLOUD_PRM, to 
    ensure consistency with the variables selected in the config
     file and to avoid hardcoding the variable names and related 
     parameters in the plotting

    input:
    - variable: name of the variable for which to retrieve the 
    plotting parameters, should be one of the variables in CLOUD_PRM
    output:
    - dictionary with plotting parameters for the given variable,
    including colormap, colorbar limits, units, title, variable name in the dataset

    """
    # generate plotting dictionart as a loop on cloud_prm, to avoid hardcoding the variable names and related parameters in the plotting functions, 
    # but keep them in a single place for easier maintenance and consistency check with the config settings
    plotting_dict = {}
    for var, vmin, vmax, unit, color, norm, cbar_ticks, title in zip(CLOUD_PRM, VALUE_MIN, VALUE_MAX, UNITS, COLORBARS, NORMS, CBAR_TICKS, TITLES):
        if var == 'cma': # if variable is CMA mask, use specific colormap and normalization settings defined in the config file
            plotting_dict[var] = {
                'variable': var,
                'colormap': color,
                'vmin': vmin,
                'vmax': vmax,
                'units': unit,
                'title': title,
                'norm': norm, 

                'cbar_ticks': cbar_ticks, # use specific colorbar ticks for the CMA mask, defined in the config file
                'var_nc': var # for CMA mask, the name in the dataset is the same as the variable name in CLOUD_PRM
            }
        else: 
            plotting_dict[var] = {
                'variable': var,
                'colormap': color,
                'vmin': vmin,
                'vmax': vmax,
                'units': unit,
                'title': title,
                'var_nc': var if var != 'RR_de' and var != 'RR_it' else 'RR' # for radar variable, the name in the dataset is RR, not RR_de or RR_it
            }
    if variable in plotting_dict:
        return plotting_dict[variable]
    else:
        raise ValueError(f"Variable {variable} not found in plotting_dict. Please check the variable name and the plotting_dict configuration.")




def plot_crops_quicklooks_2fields(ds_crop, filename, out_path, timestamp, domain, crop_position):
    """
    Generates and saves quicklook images for the given crop dataset.
    This function creates quicklook images for the provided crop dataset and saves them
    in the specified output directory. The quicklook images are saved in an 'img' subdirectory.
    :param ds_crop: xarray.Dataset or xarray.DataArray
        The input dataset containing the cropped image data.
    :param filename: str
        The base filename for saving the quicklook images.
    :param out_path: str
        The output directory where the quicklook images will be saved.
    :param timestamp: str           
        The timestamp associated with the dataset, used for naming the output files.    
    :param domain: tuple
        The domain for the input file (lon_min, lon_max, lat_min, lat_max).
    :param crop_position: tuple
        tuple containing (lon_min, lon_max, lat_min, lat_max) of each crop.
    :return: None
    """

    # check if the plot already exists, if yes, skip the plotting
    if os.path.exists(os.path.join(out_path, filename)):
        print(f'Plot for timestamp {timestamp} already exists, skipping plotting.')
        return None

    else:

        # set all font size of the plot to 20
        plt.rcParams.update({'font.size': 20})

        # read orography data
        ds_orog = read_orography()
        ds_orog_crop = ds_orog.sel(lat=ds_crop.lat, lon=ds_crop.lon, method='nearest')

        # select data for the given time stamp
        if ds_crop.dims.get('time') is not None:
            data = ds_crop.sel(time=timestamp)  # Select first (only) time index
        else:
            data = ds_crop
        
        # creating figure with 4 sublots: one for each variable in CLOUD_PRM, 
        # with the same domain and extent of the crop, and one with all variables 
        # superimposed, with rectangles for each crop and cloud mask as hatched areas.
        # The first three subplots are in the top row, the last subplot is in the bottom
        # row and spans all columns. The title of the figure is the timestamp of the data.
        # The output image is saved in the output directory with the name defined above.

        if len(CLOUD_PRM) == 3:
            fig, axes = plt.subplots(2, 2, figsize=(20, 20), subplot_kw={'projection': ccrs.PlateCarree()},  constrained_layout=True)
        else:
            raise ValueError("Number of variables in CLOUD_PRM not supported for plotting. Please select 3 variables.")

        # flatten axes for easier indexing
        axes = axes.flatten()

        # loop on variables and plot them in the subplots
        for i, var in enumerate(CLOUD_PRM):

            # retrieving parameters for the variable from the config file  
            plotting_params = retrieve_plotting_params_from_config(var)

            # start plotting subplots
            if not var == 'cma': # if variable is not CMA mask, plot it with the specified colormap and colorbar limits
                c = axes[i].pcolormesh(data.lon, 
                                        data.lat, 
                                        data[plotting_params['var_nc']],
                                        cmap=plotting_params['colormap'], 
                                        vmin=plotting_params['vmin'], 
                                        vmax=plotting_params['vmax'], 
                                        transform=ccrs.PlateCarree())
                cbar = plt.colorbar(c, ax=axes[i], orientation="vertical", pad=0.02)
                # make cbar aligned with plot margins   
                cbar.set_label(plotting_params['units'])
                cbar.ax.xaxis.set_label_position('top')
                cbar.ax.xaxis.set_ticks_position('top')

            else:
                # if variable is CMA mask, plot it with the specified colormap and normalization settings defined in the config file
                c = axes[i].pcolormesh(data.lon, data.lat, data[plotting_params['var_nc']], 
                                        cmap=plotting_params['colormap'], 
                                        norm=plotting_params['norm'], 
                                        transform=ccrs.PlateCarree())
                cbar = plt.colorbar(c, ax=axes[i], orientation="vertical", pad=0.02,
                                    boundaries=plotting_params['norm'].boundaries,
                                    ticks=plotting_params['cbar_ticks'])
                cbar.ax.set_yticklabels(['clear', 'cloudy'])

            # adding borders, coastlines, and setting extent for each subplot
            cbar.set_label(plotting_params['units'])
            axes[i].set_title(plotting_params['title'])
            axes[i].set_xlabel("Longitude")
            axes[i].set_ylabel("Latitude")
            axes[i].add_feature(cfeature.BORDERS, linestyle='-', linewidth=2, color="black")  
            axes[i].add_feature(cfeature.COASTLINE)  
            #axes[i].set_extent([crop_position[0], crop_position[1], crop_position[2], crop_position[3]], crs=ccrs.PlateCarree())

        # adding last subplot
        axes[3].set_title("All fields superimposed")
        axes[3].set_xlabel("Longitude")
        axes[3].set_ylabel("Latitude")
        axes[3].set_extent([DOMAIN[0], DOMAIN[1], DOMAIN[2], DOMAIN[3]], crs=ccrs.PlateCarree())
        axes[3].add_feature(cfeature.BORDERS, linestyle='-', linewidth=2, color="black")
        axes[3].add_feature(cfeature.COASTLINE)

        # plot all fields superimposed
        plotting_par_IR = retrieve_plotting_params_from_config(CLOUD_PRM[0])
        c4 = axes[3].pcolormesh(data.lon, 
                            data.lat, 
                            data[plotting_par_IR['var_nc']], 
                            cmap=plotting_par_IR['colormap'], 
                            vmin=plotting_par_IR['vmin'],
                            vmax=plotting_par_IR['vmax'],
                            transform=ccrs.PlateCarree())

        plotting_par_radar = retrieve_plotting_params_from_config(CLOUD_PRM[2])
        c44 = axes[3].pcolormesh(data.lon, 
                            data.lat, 
                            data[plotting_par_radar['var_nc']], 
                            cmap=plotting_par_radar['colormap'],
                            vmin=plotting_par_radar['vmin'],
                            vmax=plotting_par_radar['vmax'],
                            alpha=0.6,
                            transform=ccrs.PlateCarree())
        
        # plot white hatched areas for cloud mask
        plotting_par_cma = retrieve_plotting_params_from_config(CLOUD_PRM[1])
        contour = axes[3].contourf(data.lon, 
                            data.lat, 
                            data[plotting_par_cma['var_nc']], 
                            levels=[0.5, 1.5], 
                            colors='none',  # No fill color
                            hatches=['.'],  # Hatch pattern
                            transform=ccrs.PlateCarree())

    # add rectangles of crop position to the last subplot
    lonmin, lonmax, latmin, latmax = crop_position
    rect0 = plt.Rectangle((lonmin, latmin), lonmax - lonmin, latmax - latmin,
                             linewidth=3, edgecolor='orange', facecolor='none', transform=ccrs.PlateCarree())
    axes[3].add_patch(rect0)

    # position title closer to the plots

    fig.savefig(os.path.join(out_path, filename), transparent=True, dpi=300)
    plt.close() 

    print(os.path.join(out_path, filename), 'SAVED PNG')
    return None


def plot_single_crops_images(timestamp, out_path, filename):
    """
    function to read ncdf for the given timestamp and plot images of each variable separately for each crop position.
    :param timestamp: str           
        The timestamp associated with the dataset, used for naming the output files.
    : param out_path: str
        The output directory where the quicklook images will be saved.
    : param filename: str
        The base filename for nc files to read
    return: None

    """
    # create output directory for quicklooks if it does not exist
    quicklook_dir = out_path[:-3] + '/img/crops_images/'
    if not os.path.exists(quicklook_dir):
        os.makedirs(quicklook_dir)


    from create_crops_from_buckets_new import parse_timestamp
    hour, month, day, yyyy, minute = parse_timestamp(timestamp)


    for i in range(N_SAMPLES):

        # construct filenames
        file_name = out_path+'/'+filename+"_"+str(i)+".nc"
        # read ncdf file
        ds_crop = xr.open_dataset(file_name)
        
        cmaps = {'IR_108': 'Greys', 'cma': ListedColormap(['lightgrey', 'yellow']), 'RR': 'viridis'}
        # loop on variables
        for i_var, var in enumerate(CLOUD_PRM):
            
            # read variable 
            output_file_name = f"{quicklook_dir}/{i}_{yyyy}-{month}-{day}_{hour}{minute}_{var}.png"
            data = ds_crop.sel(time=timestamp)[var]

            plt.imsave(output_file_name, data, cmap=cmaps[var], vmax=VALUE_MAX[i_var], vmin=VALUE_MIN[i_var])    
            print(f'Saved crop image: {output_file_name}')

    return None





def video_quicklook(crop_file, output_dir, crop_id):
    """
    (ds_crop, x_pixel, y_pixel, filename, out_path, timestamp, domain, crop_position)
    Creates a video quicklook of the space-time crop evolution in time.

    input:
        crop_file: path to the netcdf file containing the space-time crop
        output_dir: directory where the video quicklook will be saved
        crop_id: spatial id of the crop to plot, should be 0 or 1, used to select the correct plotting function for the quicklook
    """

    ds = xr.open_dataset(crop_file)
    n_time_stamps = len(ds.time.values) 

    # read latmax, latmin, lonmax, lonmin of the crop from the attributes of the nc file
    lat_min = ds.attrs['latmin']
    lat_max = ds.attrs['latmax']
    lon_min = ds.attrs['lonmin']
    lon_max = ds.attrs['lonmax']
    crop_position = (lon_min, lon_max, lat_min, lat_max)

    # init list to store the images for the video
    images = []

    # loop on time stamps
    for i in range(n_time_stamps):
        
        # select the data for the current time stamp
        data = ds.isel(time=i)
        timestamp = str(data.time.values)
        string_timestamp = timestamp.split('T')[0].split('-')[0] + timestamp.split('T')[0].split('-')[1] + timestamp.split('T')[0].split('-')[2] + '_' + timestamp.split('T')[1][0:2] + timestamp.split('T')[1][3:5]
        
        # save the first and the last timestamp for the title of the video
        if i == 0:
            start_time = string_timestamp
        elif i == n_time_stamps-1:
            end_time = string_timestamp[9:13]
        else: 
            pass

        # build image filename
        filename = f'{string_timestamp}_crop_{i}_spacecrop_{crop_id}.png'

        # extract string from time stamp
        year = str(timestamp).split('T')[0].split('-')[0]

        # creat filename
        image_path = os.path.join(output_dir, filename)

        # call the function plot_crops_quicklooks_2fields to plot the data
        plot_crops_quicklooks_2fields(data, filename, output_dir, timestamp, DOMAIN, crop_position)

        # check if output dir exists and if not create it
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        images.append(PIL.Image.open(image_path))

    # create video from the images
    video_path = os.path.join(output_dir, f'{start_time}_{end_time}_spatialcrop_{crop_id}_vquicklook.gif')
    images[0].save(video_path, save_all=True, append_images=images[1:], duration=500, loop=0)
    print(f'Video quicklook saved at: {video_path}')    

    # convert gif to mpf using ffmpeg, to reduce the file size and make it easier to visualize
    video_path_mp4 = video_path.replace('.gif', '.mp4')
    os.system(f'ffmpeg -i {video_path} -vcodec libx264 -pix_fmt yuv420p {video_path_mp4}')
    print(f'Video quicklook saved at: {video_path_mp4}')

    # if present, re\move the gif file to save space
    if os.path.exists(video_path):
        os.remove(video_path)

    # if quicklook video is created, remove all png images in the output directory
    if os.path.exists(video_path_mp4):
        for f in os.listdir(output_dir):
            if f.endswith('.png'):
                os.remove(os.path.join(output_dir, f))
    
    return video_path



def plot_data_for_timestamp(ds_time, timestamp, out_path):
    """
    Plots the original data for the given timestamp and saves the plot in the output directory.
    This function is used to check the data selection for each timestamp.
    :param ds_time: xarray.Dataset
        The input dataset containing the original data for all timestamps.
    :param timestamp: str           
        The timestamp associated with the dataset, used for naming the output files.    
    :param out_path: str
        The output directory where the plot will be saved.
    :param domain: tuple
        The domain for the input file (lon_min, lon_max, lat_min, lat_max).
    :return: None

    The plot is a collection of suplots for all the variables in CLOUD_PRM

    input:
        - ds_time: xarray.Dataset containing the original data for the selected timestamp to plot
        - timestamp: str, the timestamp associated with the dataset, used for naming the output files
        - out_path: str, the output directory where the plot will be saved

    dependencies:
    - retrieve_plotting_params_from_config: function to retrieve plotting parameters for 
    each variable from the config file, used to keep all plotting parameters in a single
     place and avoid hardcoding them in the plotting functions

    returns:
    - None, the function saves the plot in the output directory and does not return anything
    """
    # define output filename based on timestamp, with format YYYYMMDD_HHMM_original_data.png
    # format time stamp as YYYYMMDD_HHMM
    out_path = os.path.join(out_path, 'original_data')
    str_timestamp = str(timestamp)
    timestamp_string = str_timestamp.split('T')[0].split('-')[0] + str_timestamp.split('T')[0].split('-')[1] + str_timestamp.split('T')[0].split('-')[2] + '_' + str_timestamp.split('T')[1][0:2] + str_timestamp.split('T')[1][3:5]
    filename = f'{timestamp_string}_original_data.png'

    # check if the plot already exists, if yes, skip the plotting
    if os.path.exists(os.path.join(out_path, filename)):
        print(f'Plot for timestamp {timestamp} already exists, skipping plotting.')
        return None
    else:

        # set all font size of the plot to 20
        plt.rcParams.update({'font.size': 20})
        
        # based on the number of variables in CLOUD_PRM, create a grid of subplots
        if len(CLOUD_PRM) == 1:
            fig, ax = plt.subplots(1, 1, figsize=(10, 10), subplot_kw={'projection': ccrs.PlateCarree()})
            axes = [ax]
        elif len(CLOUD_PRM) == 2:
            fig, axes = plt.subplots(1, 2, figsize=(20, 10), subplot_kw={'projection': ccrs.PlateCarree()})
        elif len(CLOUD_PRM) == 3:
            fig, axes = plt.subplots(1, 3, figsize=(30, 10), subplot_kw={'projection': ccrs.PlateCarree()})
        elif len(CLOUD_PRM) == 4:
            fig, axes = plt.subplots(2, 2, figsize=(30, 20), subplot_kw={'projection': ccrs.PlateCarree()})
            axes = axes.flatten()
        else:
            raise ValueError("Number of variables in CLOUD_PRM not supported for plotting. Please select 1, 2, 3 or 4 variables.")

        # loop on variables and plot them in the subplots
        for i, var in enumerate(CLOUD_PRM):
            #print(f"Plotting variable: {var} for timestamp: {timestamp}")  

            plotting_params = retrieve_plotting_params_from_config(var)

            if var == 'RR_de' or var == 'RR_it':
                var_plot = 'RR'
            else:
                var_plot = var

            if not var == 'cma': # if variable is not CMA mask, plot it with the specified colormap and colorbar limits
                c = axes[i].pcolormesh(ds_time.lon, ds_time.lat, ds_time[var_plot][0],
                                        cmap=plotting_params['colormap'], 
                                        vmin=plotting_params['vmin'], 
                                        vmax=plotting_params['vmax'], 
                                        transform=ccrs.PlateCarree())
                cbar = plt.colorbar(c, ax=axes[i], orientation="horizontal", pad=0.02, shrink=0.8)
            else:
                # if variable is CMA mask, plot it with the specified colormap and normalization settings defined in the config file
                c = axes[i].pcolormesh(ds_time.lon, ds_time.lat, ds_time[var][0], 
                                        cmap=plotting_params['colormap'], 
                                        norm=plotting_params['norm'], 
                                        transform=ccrs.PlateCarree())
                cbar = plt.colorbar(c, ax=axes[i], orientation="horizontal", pad=0.02, shrink=0.8,
                                    boundaries=plotting_params['norm'].boundaries,
                                    ticks=plotting_params['cbar_ticks'])
                cbar.ax.set_xticklabels(['clear', 'cloudy'])

            cbar.set_label(plotting_params['units'])
            axes[i].set_title(plotting_params['title'])
            axes[i].set_xlabel("Longitude")
            axes[i].set_ylabel("Latitude")
            axes[i].add_feature(cfeature.BORDERS, linestyle='-', linewidth=2, color="black")  
            axes[i].add_feature(cfeature.COASTLINE)  
            axes[i].set_extent([DOMAIN[0], DOMAIN[1], DOMAIN[2], DOMAIN[3]], crs=ccrs.PlateCarree())



        # save plot with name containing the timestamp
        
        plt.savefig(os.path.join(out_path, filename), dpi=300)
        plt.close()
        
        #print(f'Original data plot saved at: {os.path.join(out_path, filename)}')
        return None
