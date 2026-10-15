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
from matplotlib import image
from datetime import datetime

common_path = '/home/Daniele/data/msg/2013/' #now it contains from Apr to Jul (like the COT from DC)

output_path =  '/p/scratch/deepacf/kiste/DC/dataset/bigdata_centraleurope/global_domain_528x288/'
cropped_image_path = '/p/scratch/deepacf/kiste/DC/dataset/bigdata_centraleurope/random_crops/2015_rcrops/'
cropped_image_additional = '/p/scratch/deepacf/kiste/DC/dataset/bigdata_centraleurope/random_crops_additional/2015_rcrops_additional/' 
lat_lon_file = '/p/project/deepacf/kiste/DC/dataset/msevi_geolocation_rss_de_hr.nc'


#merge all msg file in nc format (they are organized in months folders)
msg_org_files = glob.glob(os.path.join(common_path,"*/*.nc")) 

print('total files are - '+ str(len(msg_org_files)))

exit()

x_pixel = 301
y_pixel = 201

new_x_pixel = 828    
new_y_pixel = 488

org_pixel = 128
org_x_pixel = 528
org_y_pixel = 288

file_format = '.tif'
file_format1 = '.npy'
cloud_prm = 'IR_108' #'cot', WV_062, IR_039

# Reading NC files
def file_detail(file_location):
    #TODO this needs to be adapted for my filename
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
        
        global_details = xarray.open_dataset(file_path).cot[0,y_pixel:new_y_pixel,x_pixel:new_x_pixel]  #entire domain?  
        cot_profile = global_details[y1:y1+ matrix,x1:x1 + matrix] #random crop?
        
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

        #It cropped all the variables in the small crop domain for each physical quantities, including lat/lon
        #then same them in a xarray dataset

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
        #save 5 different crops
        crop_data.to_netcdf(cropped_image_additional+filename+"_germany_" +str(i)+'.nc')
        #print('filesave')

    
    for i in range(len(sample_list)):
        
        fig = save_fig(sample_list[i],[org_pixel,org_pixel],cropped_image_path+ '_germany'+file_format)
        fig.savefig(cropped_image_path + filename+ "_germany_" +str(i)+ file_format, dpi=1)
        
        
filename_list = []
for file in msg_org_files[0:]: #loop over the nc files containing the channel (and phys quantities?)
    filename = file_detail(file) #extract info from the filename
    hour, month = int(filename[9:11]), int(filename[4:6]) #extract time and date from the filename
    file_initial = file[36:63] #extract timestamp (initial and final scan time?) --not used
    file_last = file[76:99] #extract timestamp (initial and final scan time?) --> not 
    #This line of code is performing a check to determine if there are any NaN (Not a Number) values in a specific slice of the data from a NetCDF file.
    #image read is just xr.open_dataset(), check the variable cot within some coordinates
    #sums the values in the selected slice along all dimensions. By setting skipna=False, the function ensures that if there are any NaN values present, the result of the sum will be NaN. 
    #This checks if the result of the sum is NaN. isnull returns True if the input is NaN and False otherwise.
    isnan_dshope = xarray.DataArray.isnull(xarray.DataArray.sum(image_read(file).cot[0,y_pixel:new_y_pixel,x_pixel:new_x_pixel],skipna=False))
    #if there are no Nan, the months is between April and September and time is before 17 UTC
    if isnan_dshope == False and month >= 4 and month <=9 and hour < 17:
        
        filename_list.append(filename) #store the file 
        # Saving global image 
        #save_fig(image, pixel_size, output_dir, **imshow_kwargs): take the cot, the pixel size: org_x_pixel = 528, org_y_pixel = 288 
        #and save in the output with the same filename and in tif
        fig = save_fig(image_read(file).cot[0,y_pixel:new_y_pixel,x_pixel:new_x_pixel],[org_x_pixel,org_y_pixel],output_path + filename + "_germany"+file_format)
        #once the fig instance is created it is then saved, why put it the output folder in save_fig?
        fig.savefig(output_path + filename+ "_germany" + file_format, dpi=1)

        # saving cropped image and saving cropped parameters
        #this is basically the path to the images that where previously saved (is this the entire DC domaain?)
        file1='/p/scratch/deepacf/kiste/DC/dataset/bigdata_centraleurope/global_domain_528x288/' + filename+ "_germany" + file_format
        #taking the images saved using the entire domain now it creates the crops?
        multi_crops(file, file1, filename) #filename is used only for saving purposes
