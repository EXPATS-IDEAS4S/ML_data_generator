import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime 
import xarray
import os, sys
import glob
from random import randrange
import json
from PIL import Image
import PIL
import torchvision
import torchvision.transforms as transforms
from matplotlib import image
from datetime import datetime

common_path = '/p/scratch/deepacf/kiste/DC/dataset/hope2015_hartwig/' #/p/scratch/deepacf/kiste/DC/dataset/hope2016_hartwig/2016/
msg_org_files = glob.glob(os.path.join(common_path,"*.nc")) 
output_path =  '/p/scratch/deepacf/kiste/DC/dataset/bigdata_centraleurope/global_domain_528x288/'
cropped_image_path = '/p/scratch/deepacf/kiste/DC/dataset/bigdata_centraleurope/random_crops/2015_rcrops/'
cropped_image_additional = '/p/scratch/deepacf/kiste/DC/dataset/bigdata_centraleurope/random_crops_additional/2015_rcrops_additional/' 
lat_lon_file = '/p/project/deepacf/kiste/DC/dataset/msevi_geolocation_rss_de_hr.nc'


#print('total files are - '+ str(len(msg_org_files)))

x_pixel = 301
y_pixel = 201

new_x_pixel = 828    
new_y_pixel = 488

org_pixel=128
org_x_pixel = 528
org_y_pixel = 288

file_format = '.tif'
file_format1 = '.npy'
cloud_prm = 'cot'

# Reading NC files
def file_detail(file_location):
    detail = file_location[len(file_location)-36:len(file_location)-23]
    return detail

def image_read(file_loc):
    ds_hope = xarray.open_dataset(file_loc)
    return ds_hope

def save_fig(image, pixel_size, output_dir, **imshow_kwargs):
    """
    Saves a matplotlib figure to given output directory with given pixel size.
    :param image: image that can be plotted with matplotlib imshow function
    :param pixel_size: pixel sizes (width and height), will be the figsize (with dpi=1)
    :param output_dir: string or path
    :param imshow_kwargs: kwargs for matplotlib imshow function
    :return:
    """
    fig, ax = plt.subplots(figsize=pixel_size, dpi=1)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.imshow(image, cmap='Spectral_r')
    ax.axis(False)
    plt.close(fig)
    return fig
    
    
def multi_crops(file_path, image_path, filename):
    img = Image.open(image_path)  
    x, y = img.size

    matrix = 128
    sample = 5
    sample_list = []
    
    x_pixel = 301
    y_pixel = 201

    new_x_pixel = 828    
    new_y_pixel = 488
    
    _file_lat = xarray.open_dataset(lat_lon_file).lat
    _file_lon = xarray.open_dataset(lat_lon_file).lon

    for i in range(sample):

        x1 = randrange(0, x - matrix)
        y1 = randrange(0, y - matrix)
        
        
        sds_profile = np.zeros((matrix, matrix))
        sds_profile.fill(np.nan)
        cot_profile = np.zeros((matrix, matrix))
        cot_profile.fill(np.nan)
        trs_profile = np.zeros((matrix, matrix))
        trs_profile.fill(np.nan)
        cth_profile = np.zeros((matrix, matrix))
        cth_profile.fill(np.nan)
        cph_profile = np.zeros((matrix, matrix))
        cph_profile.fill(np.nan)
        lat_profile = np.zeros((matrix, matrix))
        lat_profile.fill(np.nan)
        lon_profile = np.zeros((matrix, matrix))
        lon_profile.fill(np.nan)
        ctp_profile = np.zeros((matrix, matrix))
        ctp_profile.fill(np.nan)
        cldmask_profile = np.zeros((matrix, matrix))
        cldmask_profile.fill(np.nan)
        ctt_profile = np.zeros((matrix, matrix))
        ctt_profile.fill(np.nan)
        
        global_details = xarray.open_dataset(file_path).cot[0,y_pixel:new_y_pixel,x_pixel:new_x_pixel]    
        cot_profile = global_details[y1:y1+ matrix,x1:x1 + matrix]
        
        #if np.isnan(cot_profile).any() == False:
            
        sample_list.append(img.crop((x1, y1, x1 + matrix, y1 + matrix)))


        global_details = xarray.open_dataset(file_path).sds[0,y_pixel:new_y_pixel,x_pixel:new_x_pixel]    
        sds_profile = global_details[y1:y1+ matrix,x1:x1 + matrix]


        global_details = xarray.open_dataset(file_path).trs[0,y_pixel:new_y_pixel,x_pixel:new_x_pixel]    
        trs_profile = global_details[y1:y1+ matrix,x1:x1 + matrix]


        global_details = xarray.open_dataset(file_path).cth[0,y_pixel:new_y_pixel,x_pixel:new_x_pixel]    
        cth_profile = global_details[y1:y1+ matrix,x1:x1 + matrix]


        global_details = xarray.open_dataset(file_path).cph[0,y_pixel:new_y_pixel,x_pixel:new_x_pixel]    
        cph_profile = global_details[y1:y1+ matrix,x1:x1 + matrix]


        global_details = _file_lat[y_pixel:new_y_pixel,x_pixel:new_x_pixel]    
        lat_profile = _file_lat[y1:y1+ matrix,x1:x1 + matrix]


        global_details = _file_lon[y_pixel:new_y_pixel,x_pixel:new_x_pixel]    
        lon_profile = _file_lon[y1:y1+ matrix,x1:x1 + matrix]


        global_details = xarray.open_dataset(file_path).ctp[0,y_pixel:new_y_pixel,x_pixel:new_x_pixel]    
        ctp_profile = global_details[y1:y1+ matrix,x1:x1 + matrix]


        global_details = xarray.open_dataset(file_path).cldmask[0,y_pixel:new_y_pixel,x_pixel:new_x_pixel]    
        cldmask_profile = global_details[y1:y1+ matrix,x1:x1 + matrix]


        global_details = xarray.open_dataset(file_path).ctt[0,y_pixel:new_y_pixel,x_pixel:new_x_pixel]    
        ctt_profile = global_details[y1:y1+ matrix,x1:x1 + matrix]

        crop_data = xarray.Dataset(
            data_vars={

            "sds": (('lat','lon'), sds_profile, {'long_name': 'surface downwelling solar radiation', 'units':'W m-2', "standard_name": "sds"}),
            "cot": (('lat','lon'), cot_profile, {'long_name': 'atmosphere_optical_thickness_due_to_cloud', 'units':'', "standard_name": "cot"}),
            "trs": (('lat','lon'), trs_profile, {'long_name': 'TOA reflected solar radiation', 'units':'W m-2', "standard_name": "trs"}),
            "cth": (('lat','lon'), cth_profile, {'long_name': 'Cloud Top Altitude above geoid', 'units':'m', "standard_name": "cth"}),
            "cph": (('lat','lon'), cph_profile, {'long_name': 'thermodynamic_phase_of_cloud_water_particles_at_cloud_top status_flag', 'units':'1', "standard_name": "cph"}),
            "ctp": (('lat','lon'), ctp_profile, {'long_name': 'air_pressure_at_cloud_top', 'units':'hPa', "standard_name": "ctp"}),
            "cmask": (('lat','lon'), cldmask_profile, {'long_name': 'cloud_area_fraction status_flag', 'units':'1', "standard_name": "cmask"}),
            "ctt": (('lat','lon'), ctt_profile, {'long_name': 'air_pressure_at_cloud_top', 'units':'hPa', "standard_name": "ctt"}),
            },
            coords={
            "lat_crop": (('lat','lon'), lat_profile ,{"axis": "pressure_level","standard_name": "latitude","units": "degrees_north", "long_name":'pixel latitude'}), 
            "lon_crop": (('lat','lon'), lon_profile, {"axis": "pressure_level","standard_name": "longitude","units": "degrees_east", "long_name":'pixel longitude'}),
            },
            attrs={'CREATED_BY'     : 'Dwaipayan Chatterjee',
                    'CREATED_ON'       : str(datetime.now()),
                    'FILL_VALUE'       : 'NaN',
                    'IMAGE_NAME'       : filename, 
                    'PI_NAME'          : 'Dwaipayan Chatterjee',
                    'PI_AFFILIATION'   : 'University of Cologne (UNI), Germany',
                    'PI_ADDRESS'       : 'Institute for geophysics and meteorology, Pohligstrasse 3, 50969 Koeln',
                    'PI_MAIL'          : 'dchatter@meteo.uni-koeln.de',
                    'DATA_DESCRIPTION' : 'Macro-physics cloud parameters from Hartwig Deneke for random crops ',
                    'DATA_DISCIPLINE'  : 'Atmospheric Physics - Remote Sensing Radar Profiler',
                    'DATA_GROUP'       : 'MSG - MTG',
                    'DATA_LOCATION'    : 'Central European Domain',
                    'DATA_SOURCE'      : 'Hartwig_Leipzig_Tropos',
                    'DATA_PROCESSING'  : 'https://github.com/DC95/',
                    'COMMENT'          : '' }
        )

        crop_data = crop_data.assign_attrs({
            "Conventions": "CF-1.8",
            "title": crop_data.attrs["DATA_DESCRIPTION"],
            "institution": crop_data.attrs["PI_AFFILIATION"],
            "history": "".join([
                "source: " + crop_data.attrs["DATA_SOURCE"] + "\n",
                "processing: " + crop_data.attrs["DATA_PROCESSING"] + "\n",
                " adapted to enhance CF compatibility\n",
            ]),  # the idea of this attribute is that each applied transformation is appended to create something like a log
            "featureType": "trajectoryProfile",
        })

        crop_data.to_netcdf(cropped_image_additional+filename+"_germany_" +str(i)+'.nc')
        #print('filesave')

    
    for i in range(len(sample_list)):
        
        fig = save_fig(sample_list[i],[org_pixel,org_pixel],cropped_image_path+ '_germany'+file_format)
        fig.savefig(cropped_image_path + filename+ "_germany_" +str(i)+ file_format, dpi=1)
        
        
filename_list = []
for file in msg_org_files[0:]:
    filename = file_detail(file)
    hour, month = int(filename[9:11]), int(filename[4:6])
    file_initial = file[36:63]
    file_last = file[76:99]
    isnan_dshope = xarray.DataArray.isnull(xarray.DataArray.sum(image_read(file).cot[0,y_pixel:new_y_pixel,x_pixel:new_x_pixel],skipna=False))
    if isnan_dshope == False and month >= 4 and month <=9 and hour < 17:
        
        filename_list.append(filename)
        # Saving global image 
        fig = save_fig(image_read(file).cot[0,y_pixel:new_y_pixel,x_pixel:new_x_pixel],[org_x_pixel,org_y_pixel],output_path + filename + "_germany"+file_format)
        fig.savefig(output_path + filename+ "_germany" + file_format, dpi=1)

        # saving cropped image and saving cropped parameters
        file1='/p/scratch/deepacf/kiste/DC/dataset/bigdata_centraleurope/global_domain_528x288/' + filename+ "_germany" + file_format
        multi_crops(file, file1, filename)
