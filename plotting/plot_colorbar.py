import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

def plot_colorbar(
    vmin,
    vmax,
    colormap_name,
    out_dir,
    title='',
    unit='',
    ticks=None,
    orientation='horizontal',
    label_fontsize=20,
    tick_fontsize=18,
    labelpad=20,
):
    """
    Plot a colorbar with the specified colormap, value range, title, and unit.

    Parameters:
    vmin (float): The minimum value of the scale.
    vmax (float): The maximum value of the scale.
    colormap_name (str): The name of the colormap to use.
    title (str): The title of the colorbar.
    unit (str): The unit of the colorbar values.
    """
    # Create a colormap instance
    colormap = plt.get_cmap(colormap_name)

    # Normalize the color scale
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    # Create a scalar mappable object
    scalar_mappable = plt.cm.ScalarMappable(norm=norm, cmap=colormap)

    # Plot the colorbar
    fig_size = (0.75, 10) if orientation == 'vertical' else (15, 0.75)
    fig, ax = plt.subplots(figsize=fig_size)
    cbar = fig.colorbar(scalar_mappable, cax=ax, orientation=orientation, ticks=ticks)

    # Set the colorbar title and unit
    cbar.set_label(f'{title} [{unit}]', fontweight='bold', fontsize=label_fontsize, labelpad=labelpad)

    # Ensure ticks and tick labels are displayed
    if ticks is not None:
        cbar.set_ticks(ticks)
        cbar.set_ticklabels([f'{tick:.0f}' for tick in ticks])

    cbar.ax.tick_params(labelsize=tick_fontsize)

    # Keep tick labels horizontal for vertical colorbars
    if orientation == 'vertical':
        cbar.ax.set_yticklabels(cbar.ax.get_yticklabels(), rotation=0)
    else:
        cbar.ax.set_xticklabels(cbar.ax.get_xticklabels(), rotation=0)

    # Disable the main axis frame and labels, but keep the ticks
    ax.set_frame_on(False)
    if orientation == 'vertical':
        ax.yaxis.set_tick_params(size=0)
    else:
        ax.xaxis.set_tick_params(size=0)

    safe_title = title.replace(' ', '_')
    fig.savefig(f'{out_dir}colorbar_{safe_title}_{orientation}.png', bbox_inches='tight')
    plt.close(fig)

data_dir = '/data1/fig/dcv2_resnet_k7_ir108_100x100_2013-2017-2021-2025_2xrandomcrops_1xtimestamp_cma_nc/'

#open max and min
#vmin , vmax = np.load(data_dir+'global_min_max.npy')
vmin = 240
vmax = 320

print(vmin, vmax)
#Computed global min: 202.13882446289062 and global max: 313.4286193847656

#create ticks
ticks = np.arange(vmin, vmax+10, 10)

plot_colorbar(
    vmin,
    vmax,
    'Greys',
    data_dir,
    title='IR_108 Brightness Temperature',
    unit='K',
    ticks=ticks,
    orientation='horizontal',
)

plot_colorbar(
    vmin,
    vmax,
    'Greys',
    data_dir,
    title='IR_108 Brightness Temperature',
    unit='K',
    ticks=ticks,
    orientation='vertical',
)
