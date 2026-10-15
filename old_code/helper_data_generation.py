import glob
import os

def get_all_files_in_study_period(msg_path, years, months):
    """gets paths to all files within defined study period
    Args:
        msg_path (str): root path to msg data
        years (list(int)): list of years considered in study
        months (list(int)): list of months considered in study
    Returns:
        list(str): list of all file paths in study period
    """
    msg_files = []
    # loop over given years and months and collect path to all files
    for year in years:
        for month in months:
            msg_path_month = f"{msg_path}/{year}/{month:02}"
            msg_files.extend(glob.glob(msg_path_month + '/*.nc'))

    return msg_files

def get_ymd_from_msg_filename(filename):
    """
    retreives year, month and day from MSG filename
    Args:
        filename (str, path-likt): filename of MSG netcdf data
    Returns:
        (str, str, str): (year, month, day)
    """
    dt_string = os.path.basename(filename)[:8]
    year = dt_string[:4]
    month = dt_string[4:6]
    day = dt_string[6:]
    return year, month, day

def npdatetime_to_string(timestamp):
    """converts np.datetime64 to string
    Args:
        timestamp (np.datetime64): timestamp
    Returns:
        str: timestamp string in form of (yyyymmdd_hhmm)
    """
    return str(timestamp).replace('-', '').replace('T', '_').replace(':', '')[:13]