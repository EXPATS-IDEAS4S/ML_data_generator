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

def read_orography():

    ds = xr.open_dataset("/data1/DEM_EXPATS_0.01x0.01.nc")
    print(ds)

    return ds




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

    # read orography data
    ds_orog = read_orography()
    ds_orog_crop = ds_orog.sel(lat=ds_crop.lat, lon=ds_crop.lon, method='nearest')


    # set all fontsize of the plot to 20
    plt.rcParams.update({'font.size': 18})

    # read year, month, day, minute, hour from timestamp
    from create_crops_from_buckets_new import parse_timestamp
    hour, month, day, yyyy, minute = parse_timestamp(timestamp)

    # create output directory for quicklooks if it does not exist
    quicklook_dir = out_path 
    if not os.path.exists(quicklook_dir):
        os.makedirs(quicklook_dir)
    
    logging.info(f"created path for quicklooks: {quicklook_dir}")

    # Extract variables
    if ds_crop.dims.get('time') is not None:

        data = ds_crop.sel(time=timestamp)  # Select first (only) time index
    else:
        data = ds_crop

    lons, lats = data.lon, data.lat
    
    # plot 4 subplots with: 
    # - IR in greyscale,
    # - RR with transparent colormap for zero values, 
    # - cloud mask, 
    # - all fields superimposed with rectangles for each crop, cloud mask as hatched areas, IR grey scale, RR in Oranges.
    fig = plt.figure(figsize=(15, 15), constrained_layout=True)

    # defining new grid layout
    gs = gridspec.GridSpec(2, 3, height_ratios=[1, 2])

    # Top row: three panels
    ax1 = fig.add_subplot(gs[0, 0], projection=ccrs.PlateCarree())
    ax2 = fig.add_subplot(gs[0, 1], projection=ccrs.PlateCarree())
    ax3 = fig.add_subplot(gs[0, 2], projection=ccrs.PlateCarree())
    ax4 = fig.add_subplot(gs[1, :], projection=ccrs.PlateCarree())

    # plot the first variable in greyscale
    c = ax1.pcolormesh(lons, 
                        lats, 
                        data[CLOUD_PRM[0]], 
                        cmap="Greys", 
                        vmin=VALUE_MIN[0],
                        vmax=VALUE_MAX[0],
                        transform=ccrs.PlateCarree())

    cbar = plt.colorbar(c, ax=ax1, orientation="horizontal", pad=0.02)                        
    cbar.set_label("IR 108 Temperature [K]")

    # plot the second variable with transparent colormap for zero values

    # set to zero all values where CMA is nan
    data[CLOUD_PRM[1]] = data[CLOUD_PRM[1]].fillna(0.)

    cmap_cma = ListedColormap(['lightgrey', 'yellow'])
    bounds = [-0.5, 0.5, 1.5]
    norm = BoundaryNorm(bounds, cmap_cma.N)

    # print unique values of cloud mask
    unique_values = np.unique(data[CLOUD_PRM[1]].values)
    print("Unique values in cloud mask:", unique_values)    

    # plot of cloud mask
    c2 = ax2.pcolormesh(lons, 
                        lats, 
                        data[CLOUD_PRM[1]], 
                        cmap=cmap_cma, 
                        norm=norm,
                        transform=ccrs.PlateCarree())

    cbar = plt.colorbar(c2, 
                        ax=ax2,
                        orientation="horizontal", 
                        pad=0.02,
                        boundaries=[-0.5, 0.5, 1.5],
                        ticks=[0., 1.])
    cbar.ax.set_xticklabels(['clear', 'cloudy'])    
    cbar.set_label("Cloud Mask") 


    # third plot: rain rate
    # Create a viridis colormap
    viridis = plt.cm.viridis(np.linspace(0, 1, 255))
    # Prepend white for zero
    colors = np.vstack(([1, 1, 1, 1], viridis))  # RGBA for white

    custom_cmap = ListedColormap(colors)
    print(CLOUD_PRM[2])
    if (CLOUD_PRM[2] == 'RR_de') or (CLOUD_PRM[2] == 'RR_it'):
        print('plotting RR')
        par_plot = 'RR'
    else:
        par_plot = CLOUD_PRM[2]

    c3 = ax3.pcolormesh(lons, 
                        lats, 
                        data[par_plot], 
                        cmap=custom_cmap, 
                        vmin=0.,
                        vmax=40.,
                        transform=ccrs.PlateCarree())   
    cbar3 = plt.colorbar(c3, ax=ax3, orientation="horizontal", pad=0.02)                        
    cbar3.set_label("RR [mm/h]")


    # add orography contours to RR plot
    orog_contour = ax3.contour(ds_orog_crop['lon'],
                        ds_orog_crop['lat'],
                        ds_orog_crop['DEM'],
                        levels=[500., 1000., 1500.],
                        colors='grey',
                        linewidths=1.,
                        transform=ccrs.PlateCarree())
    ax3.clabel(orog_contour, fmt='%d', inline=True, fontsize=10)

    # plot all fields superimposed
    c4 = ax4.pcolormesh(lons, 
                        lats, 
                        data[CLOUD_PRM[0]], 
                        cmap="Greys", 
                        vmin=VALUE_MIN[0],
                        vmax=VALUE_MAX[0],
                        transform=ccrs.PlateCarree())

    c44 = ax4.pcolormesh(lons, 
                        lats, 
                        data[par_plot], 
                        cmap=custom_cmap,
                        vmin=VALUE_MIN[2],
                        vmax=VALUE_MAX[2],
                        alpha=0.6,
                        transform=ccrs.PlateCarree())
    
    # plot white hatched areas for cloud mask
    levels = [0., 0.5]  # Only hatch values above 0.5
    contour = ax4.contourf(lons, 
                        lats, 
                        data['cma'], 
                        levels=levels, 
                        colors='none',  # No fill color
                        hatches=['x'],  # Hatch pattern
                        transform=ccrs.PlateCarree())

    # add country borders and coastline to all subplots
    for axi in [ax1, ax2, ax3, ax4]:
        axi.add_feature(cfeature.BORDERS, linestyle='-', linewidth=2, color="black")  
        axi.add_feature(cfeature.COASTLINE)  
        axi.set_extent([domain[0], domain[1], domain[2], domain[3]], crs=ccrs.PlateCarree())
    
    # add rectangles for each crop to both subplots

    lonmin, lonmax, latmin, latmax = crop_position
    rect0 = plt.Rectangle((lonmin, latmin), lonmax - lonmin, latmax - latmin,
                             linewidth=3, edgecolor='orange', facecolor='none', transform=ccrs.PlateCarree())
    ax4.add_patch(rect0)


    # position title closer to the plots
    fig.suptitle(f'{yyyy}-{month}-{day} {hour}:{minute} UTC', y=0.95)
    fig.savefig(os.path.join(out_path, filename), transparent=True, dpi=300)
    plt.close() 

    print(os.path.join(out_path, filename), 'SAVED PNG')

    return None

def plot_test():

    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    
    fig = plt.figure(figsize=(15, 10))
    gs = gridspec.GridSpec(2, 3, height_ratios=[1, 1.2])
    
    # Top row: three panels
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])
    
    # Bottom row: one big panel spanning all columns
    ax4 = fig.add_subplot(gs[1, :])
    
    # Example: plot something
    # ax1.plot(...), ax2.plot(...), ax3.plot(...), ax4.plot(...)
    
    plt.tight_layout()
    # save fig
    plt.savefig('test_grid_layout.png', dpi=300)
    plt.show()

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





def video_quicklook(crop_file, output_dir):
    """
    (ds_crop, x_pixel, y_pixel, filename, out_path, timestamp, domain, crop_position)
    Creates a video quicklook of the space-time crop evolution in time.

    input:
        crop_file: path to the netcdf file containing the space-time crop
        output_dir: directory where the video quicklook will be saved
    """

    ds = xr.open_dataset(crop_file)
    n_time_stamps = len(ds.time.values) 

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
        
        # find lat max and lat min of the crop
        lat_min = np.nanmin(data.lat.values)
        lat_max = np.nanmax(data.lat.values)
        lon_min = np.nanmin(data.lon.values)
        lon_max = np.nanmax(data.lon.values)
        crop_position = (lon_min, lon_max, lat_min, lat_max)
        print(crop_position)

        # build image filename
        filename = f'{string_timestamp}_crop_{i}.png'

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
    video_path = os.path.join(output_dir, f'{start_time}_{end_time}_video_quicklook.gif')
    images[0].save(video_path, save_all=True, append_images=images[1:], duration=500, loop=0)
    print(f'Video quicklook saved at: {video_path}')    

    return video_path