
""" functions for processing space time crops

    author: Claudia Acquistapace
    date: 2024-06-20

"""
from config import *
import random
import logging
import numpy as np  


def calc_start_time_for_days_changing(from_previous_day):
    """
    Calculates the start time for cropping when transitioning between days.
    It considers a maximum daily offset if specified in the configuration.

    input:
        from_previous_day: xarray Dataset containing data from the previous day
    output:
        start_time: datetime index representing the start time for cropping
    """
    # determine the maximum daily offset
    earliest_start = max(int(N_FRAMES - MAX_TEMPORAL_OVERLAP*N_FRAMES - len(from_previous_day.time.values)), 0)

    # pick start time randomly between the earliest start and N_FRAMES -1
    start_next = random.randint(earliest_start, int(N_FRAMES-1))

    return start_next





def calc_start_time_for_days_full():
    """
    Calculates the start time for cropping
    It considers a maximum daily offset if specified in the configuration.
    - If MAX_DAILY_OFFSET is not set, the start time is chosen randomly between 0 and N_FRAMES-1.
    - If MAX_DAILY_OFFSET is set, the start time is chosen randomly between 0 and round(MAX_DAILY_OFFSET*N_FRAMES)+1, 
    where MAX_DAILY_OFFSET represents the maximum random offset at the beginning of the day 
    to introduce randomness in the timeseries starting times.

    output:
        start_time: datetime index representing the start time for cropping
    """
    if MAX_DAILY_OFFSET is not None:
        start_time = random.randint(0, round(MAX_DAILY_OFFSET*N_FRAMES)+1)
    else:
        start_time = random.randint(0, int(N_FRAMES-1))


    if MAX_DAILY_OFFSET is None:
        logging.info(f"Start time for cropping: {start_time} (randomly chosen between 0 and {N_FRAMES-1})")
    else:
        logging.info(f"Start time for cropping: {start_time} (randomly chosen between 0 and {round(MAX_DAILY_OFFSET*N_FRAMES)+1} based on MAX_DAILY_OFFSET")
    logging.info(f"-------------------------------------------------------------------------")
    return start_time




def search_timewindow_without_nan(ds_day, start_time):

    """
    Function to identify a time serie of N_FRAMES without NaN values in the dataset
    :param ds_day: Dataset for the current day
    :param start_time: Start time of the timeseries window
        
    :return: ds_timeseries: Dataset for the timeseries window
             start_time_next: Start time of the next timeseries window
    """
    # end time given the start time and N_FRAMES
    end_time = start_time + N_FRAMES

    # flag to indicate if still searching for timeseries window without NaNs
    searching_timeseries_window = True

    # loop until a timeseries window without NaNs is found
    while searching_timeseries_window:
        
        # slice small timeseries from dataset
        ds_timeseries = ds_day.isel(time=slice(start_time, end_time))

        # check at each timestamp if all data is NaN, i.e. MSG timestamp is missing
        is_all_nan = ds_timeseries[CLOUD_PRM[0]].isnull().all(dim=['lat', 'lon'])

        # move on to after missing timestamp
        if is_all_nan.any():
            
            # moving to next available timestamp
            ind_nan_last = np.where(is_all_nan.values)[0][-1]

            # shift start and end time to next available timestamp
            start_time += ind_nan_last + 1
            end_time = start_time + N_FRAMES

            # check if start time is still within the dataset
            if start_time >= len(ds_day.time.values):
                # if not, end this loop
                searching_timeseries_window = False
                start_time_next = None
                ds_timeseries = None
                break

            # if start and end within daytime - continue to the next iteration of the loop   
            continue
        
        # end the loop if all timestamps are available
        searching_timeseries_window = False

        # set the start for the next timeseries using the randomization function 
        """add to end_time a random offset ranging between -MAX_TEMPORAL_OVERLAP 
        and zero of the time window length, 
        to introduce some random overlap in the timeseries windows 
        and avoid always having the same start and end times for the crops """
        start_time_next = end_time + random.randint(-round(MAX_TEMPORAL_OVERLAP*N_FRAMES), 0)
        
        #calc_start_time_for_days_full()
        """ COMMENT: In paula's version, this line was
        start_time_next = end_time
        i.e. the new timeseries starts right after the end of the previous one, 
        without randomization. I changed it to introduce randomization between
         timeseries windows, but we can change it back if we want to have 
         consecutive timeseries without gaps in between. """

    return ds_timeseries, start_time_next
