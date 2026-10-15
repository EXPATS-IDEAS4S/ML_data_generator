# %%
import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib as mpl
from helper_data_generation import get_all_files_in_study_period, get_ymd_from_msg_filename

# get path to current directory
current_dir = os.path.dirname(os.path.realpath(__file__))

def read_all_values_in_daytime_range(msg_files, channel, hour_start, hour_end):
    """reads all values of given channel from given files within given daytime range
    Args:
        channel (str): name of MSG channel
        msg_files (list(str)): list of files to consider
        hours_start (str): start of started daytime range (hh:mm)
        hours_end (_type_): _description_

    Returns:
        _type_: _description_
    """
    # store values in this array
    all_values = None

    # loop over files
    for f in msg_files:

        # get year and month from filename
        year, month, day = get_ymd_from_msg_filename(f)

        # define start and end thresholds each day in form of np.datetime64
        # to better compare to timestamps in data file
        day_start = np.datetime64(f"{year}-{month}-{day}T{hour_start}")
        day_end = np.datetime64(f"{year}-{month}-{day}T{hour_end}")

        # open dataset
        with xr.open_dataset(f) as data_test:

            # loop over timestamps
            for timestamp in data_test.time.values:

                if timestamp > day_start and timestamp < day_end:
                    # select data of this timestamp
                    # check if is in given daytime range
                    data_daytime = data_test.sel(time=timestamp)[channel].values.flatten()
                    if all_values is None:
                        all_values = data_daytime[np.newaxis, :]
                    else:
                        all_values = np.concatenate((all_values, data_daytime[np.newaxis, :]), axis=0)
    
    return all_values

def get_quantiles(data_array, quantiles):
    """calculates quantiles of given data array
    Args:
        data_array (np.array(float)): given data array
        quantiles (float or array-like): either single quantile or array-like sequence of quantiles
    Returns:
        float: values of given quantiles calculated on data array
    """

    # calculate quantiles
    return np.quantile(data_array, quantiles)

def plot_distribution_and_quantiles(data_array, quantiles, xlabel=None, ylabel="occurence N", title=None, out_file=None):
    """
    plots distribution of given data array, marking given quantiles
    Args:
        channel (str): name of channel for title
        data_array (np.array(float)): given data array
        quantiles (float or array-like): either single quantile or array-like sequence of quantiles
    """
    # store quantiles here
    quantile_values = get_quantiles(data_array, quantiles)
    if not isinstance(quantile_values, list):
        quantile_values = list(quantile_values)

    # define colors for quantiles to draw later into histogram
    cmap = mpl.colormaps['plasma']
    colors = cmap(np.linspace(0, 1, len(quantiles)))

    # plot distribution including quantiles
    plt.hist(data_array.flatten(), bins=100, histtype="stepfilled")
    for q, quant in enumerate(quantile_values):
        plt.axvline(quant, label=f"{quantiles[q]:.3f} quantile = {quant:.2f}", color=colors[q])

    plt.ylabel(ylabel)
    plt.xlabel("" if xlabel is None else xlabel)
    plt.legend(loc="upper center")

    if title is not None:
        plt.title(title)

    # save figure if output file is given
    if out_file is not None:
        plt.savefig(out_file, bbox_inches="tight")
        plt.close()
    else:
        plt.show()
        plt.close()

# method that does the whole value range analysis
def investigate_range_of_dataset(msg_files, channels, 
                                 hour_start, hour_end, 
                                 quantiles, output_path):

    # loop over channels of interest
    for ch in channels:
        print("channel: ", ch)

        # read all values of this channel from selected data files
        all_values = read_all_values_in_daytime_range(msg_files, ch, hour_start, hour_end)
        
        # print quantile values
        print("quantiles: ", quantiles)
        print("values: ", get_quantiles(all_values, quantiles))

        # plot histogram of distribution
        out_file = f"{output_path}value_distribution_{ch}.png"
        ylabel = "occurence N"
        xlabel = "reflectance" if "VIS" in ch else "brightness temp [K]"
        title = f"distribution of channel {ch}"
        out_file = f"{output_path}/value_distribution_{ch}.png"
        plot_distribution_and_quantiles(all_values, quantiles, 
                                        xlabel=xlabel, ylabel=ylabel, 
                                        title=title, out_file=out_file)
        print("save plot of distribution to file: ", out_file)

# %%
if __name__ == "__main__":
    # examplary use of this script

    # define study period and daytime range
    years = [2023]
    months = [7]
    hour_start = "10:00:00"
    hour_end = "16:00:00"

    # define data path and path to save plots to
    msg_path = f"/net/merisi/pbigalke/teaching/METFUT2024/msg_test_data"
    output_path = f"{current_dir}/../output/preprocessing_dataset/"
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # define channels of interest and quantiles to be calculated from whole value distribution
    channels = ["VIS006", "VIS008", "IR_108"]
    quantiles = [0, 0.001, 0.01, 0.99, 0.999, 1]

        # read all MSG files within study period:
    msg_files = get_all_files_in_study_period(msg_path, years, months)

    # run the investigation of value range in dataset
    investigate_range_of_dataset(msg_files, channels, 
                                 hour_start, hour_end, 
                                 quantiles, output_path)


# %%
