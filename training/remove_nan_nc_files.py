#!/usr/bin/env python3

import os
import shutil
import xarray as xr

def move_nc_files_with_nan(root_dir, nan_dir):
    """
    Recursively checks all .nc files in `root_dir` for NaN values.
    Files containing NaNs are moved to `nan_dir`, preserving the
    original directory structure.
    """
    moved_files = []

    os.makedirs(nan_dir, exist_ok=True)

    for dirpath, _, filenames in os.walk(root_dir):
        for file in filenames:
            if file.endswith(".nc"):
                filepath = os.path.join(dirpath, file)

                try:
                    ds = xr.open_dataset(filepath, engine="h5netcdf")

                    has_nan = any(ds[var].isnull().any().item() for var in ds.data_vars)

                    ds.close()

                    if has_nan:
                        # Preserve relative directory structure
                        rel_path = os.path.relpath(filepath, root_dir)
                        destination = os.path.join(nan_dir, rel_path)

                        os.makedirs(os.path.dirname(destination), exist_ok=True)

                        shutil.move(filepath, destination)
                        moved_files.append(destination)

                        print(f"Moved file with NaNs:")
                        print(f"  {filepath}")
                        print(f"  --> {destination}")

                except Exception as e:
                    print(f"Error processing {filepath}: {e}")

    print(f"\n✅ Finished checking. {len(moved_files)} files moved.")
    return moved_files


move_nc_files_with_nan(
    "/sat_data/crops/test_grl_2026/1",
    "/sat_data/crops/test_grl_2026_nan"
)