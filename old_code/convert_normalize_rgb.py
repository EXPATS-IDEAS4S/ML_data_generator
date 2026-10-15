import rasterio
import numpy as np
import matplotlib.pyplot as plt
import glob

#TODO do it with quantiles to avoid outliers
def compute_global_min_max(tiff_paths):
    """
    Compute the global minimum and maximum values across all TIFF images.

    :param tiff_paths: List of paths to TIFF images.
    :return: (global_min, global_max) values.
    """
    global_min = float('inf')
    global_max = float('-inf')
    
    for path in tiff_paths:
        with rasterio.open(path) as src:
            # Read the image data (assuming the data is in the first band)
            data = src.read(1)
            data_min = np.min(data)
            data_max = np.max(data)
            
            # Update global min and max
            global_min = min(global_min, data_min)
            global_max = max(global_max, data_max)
    
    return global_min, global_max

def normalize_image(image, vmin, vmax):
    """
    Normalize the image data to the range [0, 1] using vmin and vmax.

    :param image: The image data to be normalized.
    :param vmin: The global minimum value for normalization.
    :param vmax: The global maximum value for normalization.
    :return: Normalized image data.
    """
    return (image - vmin) / (vmax - vmin)

def create_rgb_image(normalized_image, cmap='Spectral_r'):
    """
    Convert normalized image data to RGB using a colormap.

    :param normalized_image: The normalized image data.
    :param cmap: The colormap to be used.
    :return: RGB image data.
    """
    colormap = plt.get_cmap(cmap)
    return (colormap(normalized_image)[:, :, :3] * 255).astype(np.uint8)  # Exclude alpha channel


def process_tiff_to_rgb(input_tiff_path, output_tiff_path, vmin, vmax):
    """
    Process a single TIFF image to convert it to RGB using global normalization.

    :param input_tiff_path: Path to the input TIFF image.
    :param output_tiff_path: Path to save the RGB TIFF image.
    :param vmin: Global minimum value for normalization.
    :param vmax: Global maximum value for normalization.
    """
    with rasterio.open(input_tiff_path) as src:
        image = src.read(1)  # Read the first band
        normalized_image = normalize_image(image, vmin, vmax)
        rgb_image = create_rgb_image(normalized_image)

        # Update metadata
        metadata = src.meta.copy()
        metadata.update({
            'count': 3,
            'dtype': 'uint8'
        })

    # Save the RGB image
    with rasterio.open(output_tiff_path, 'w', **metadata) as dst:
        dst.write(rgb_image[:, :, 0], 1)  # Red band
        dst.write(rgb_image[:, :, 1], 2)  # Green band
        dst.write(rgb_image[:, :, 2], 3)  # Blue band
    
    print('rgb image saved:', output_path)


# Example usage
path_dir = '/home/Daniele/data/ir108_2013_128_germany/1/'
tiff_paths = sorted(glob.glob(path_dir+'*.tif'))
print(tiff_paths)
global_min, global_max = compute_global_min_max(tiff_paths)
print(f'Global Min: {global_min}, Global Max: {global_max}')
#ir 2013 128x128 expats: Global Min: 50, Global Max: 254--no sense
exit()

# Example usage
for path in tiff_paths:
    output_path = path.replace('.tif', '_rgb.tif')
    process_tiff_to_rgb(path, output_path, global_min, global_max)

