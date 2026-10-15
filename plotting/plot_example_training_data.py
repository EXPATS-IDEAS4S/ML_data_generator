#!/usr/bin/env python3
import os
import io
import random
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import boto3
from botocore.exceptions import ClientError
import sys
from scipy.ndimage import binary_closing

# =========================
# CONFIG
# =========================
VAR_NAME = "IR_108"
CMA_NAME = "CMA"

N_DAYS = 10
N_TIMES_PER_DAY = 3

FRAME_SIZE_PX = 100
N_FRAMES = 2

IR_VMIN = 200
IR_VMAX = 320

OUTPUT_BASE = (
    "/data1/crops/"
    "ir108_100x100_2013-2017-2021-2025_2xrandomcrops_1xtimestamp_cma_nc"
)


RANDOM_SEED = 37
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

OUTPUT_DIR = os.path.join(OUTPUT_BASE, f"train_crops_full_domain_seed_{RANDOM_SEED}")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# S3 SETUP
# =========================
sys.path.append("/home/Daniele/codes/ML_data_generator/")
from credentials_buckets import (
    S3_BUCKET_NAME,
    S3_ACCESS_KEY,
    S3_SECRET_ACCESS_KEY,
    S3_ENDPOINT_URL,
)

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY,
)

# =========================
# HELPERS
# =========================
def read_s3_nc(key):
    try:
        obj = s3.get_object(Bucket=S3_BUCKET_NAME, Key=key)
        return xr.open_dataset(io.BytesIO(obj["Body"].read()), engine="h5netcdf")
    except ClientError as e:
        print(f"Failed to read {key}: {e}")
        return None


def plot_day_timeseries(ds_day, outpath, day_idx):
    times = ds_day.time.values
    if len(times) < 3:
        return

    # --- select 3 random timestamps
    sel_times = sorted(np.random.choice(times, 3, replace=False))

    # --- layout: ... | image | ... | image | ... | image | ...
    ncols = 2 * N_TIMES_PER_DAY + 1
    fig = plt.figure(figsize=(16, 5))

    gs = fig.add_gridspec(
        nrows=1,
        ncols=ncols,
        width_ratios=[0.05 if i % 2 == 0 else 1 for i in range(ncols)],  # reduced ellipsis space
        wspace=0.1,
    )

    lon = ds_day.lon.values
    lat = ds_day.lat.values
    proj = ccrs.PlateCarree()

    for i, t in enumerate(sel_times):
        col = i * 2 + 1
        ax = fig.add_subplot(gs[0, col], projection=proj)

        # --- extract data
        da_ir = ds_day["IR_108"].sel(time=t)
        da_cma = ds_day["cma"].sel(time=t)
        #close cma using binary closing to fill small holes
        
        da_cma = xr.DataArray(
            binary_closing(da_cma.values, structure=np.ones((3,3))).astype(int),
            coords=da_cma.coords,
            dims=da_cma.dims,
        )

        # --- apply CMA mask directly to IR
        da_ir_plot = da_ir.where(da_cma == 1, 320.0)

        # --- plot IR
        ax.pcolormesh(
            lon,
            lat,
            da_ir_plot,
            cmap="gray_r",
            vmin=180,
            vmax=320,
            transform=proj,
        )

        # --- cartopy features
        ax.coastlines(resolution="50m", linewidth=0.8, color="yellow")
        ax.add_feature(cfeature.BORDERS, linewidth=0.5, edgecolor="yellow")

        # --- random 100x100 frames
        ny, nx = da_ir.shape
        dx = lon[1] - lon[0]
        dy = lat[1] - lat[0]

        for _ in range(2):
            ix = random.randint(0, nx - FRAME_SIZE_PX - 1)
            iy = random.randint(0, ny - FRAME_SIZE_PX - 1)

            rect = patches.Rectangle(
                (lon[ix], lat[iy]),
                FRAME_SIZE_PX * dx,
                FRAME_SIZE_PX * dy,
                linewidth=3,
                edgecolor="darkorange",
                facecolor="none",
                transform=proj,
                zorder=10,
            )
            ax.add_patch(rect)

        # --- title (timestamp only)
    
        ax.set_title(
            t.astype("datetime64[m]").astype(object).strftime("%H:%M UTC"),
            fontsize=16,
            fontweight="bold",
        )

        gl = ax.gridlines(
            crs=ccrs.PlateCarree(),
            draw_labels=True,
            linewidth=0.8,
            color="gray",
            alpha=0.8,
            linestyle="--",
        )

        # ---- control which labels appear
        gl.top_labels = False
        gl.right_labels = False

        # show longitude labels only on bottom (single row → always true)
        gl.bottom_labels = True
        # show latitude labels only on the first subplot
        gl.left_labels = (i == 0)

        # ---- formatting
        gl.xlabel_style = {"size": 14}
        gl.ylabel_style = {"size": 14}
        
        # show only 4 integer values per axis 
        gl.xlocator = plt.MaxNLocator(4, integer=True)
        gl.ylocator = plt.MaxNLocator(4, integer=True)


        # --- ellipsis on the left of each image except the last (both sides)
        if (i*2) % 2 == 0:
            ax_dots = fig.add_subplot(gs[0, (i*2)])
            ax_dots.axis("off")
            ax_dots.text(
                0.5, 0.5, "...",
                fontsize=28,
                ha="center",
                va="center",
            )
        
    ax_dots = fig.add_subplot(gs[0, 6])
    ax_dots.axis("off")
    ax_dots.text(
        0.5, 0.5, "...",
        fontsize=28,
        ha="center",
        va="center",
    )

    outfile = os.path.join(outpath, f"daily_timeseries_{day_idx:02d}.png")
    plt.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved {outfile}")



# =========================
# LIST DAILY FILES (S3)
# =========================
years = [2013, 2017, 2021, 2025]
months = range(4, 10)

daily_keys = []

for y in years:
    for m in months:
        prefix = (
            f"/data/sat/msg/ml_train_crops/"
            f"IR_108-WV_062-CMA_FULL_EXPATS_DOMAIN/"
            f"{y}/{m:02d}"
        )

        response = s3.list_objects_v2(
            Bucket=S3_BUCKET_NAME, Prefix=prefix
        )
        for obj in response.get("Contents", []):
            if obj["Key"].endswith(".nc"):
                daily_keys.append(obj["Key"])

print(f"Found {len(daily_keys)} daily files")

random_days = random.sample(daily_keys, min(N_DAYS, len(daily_keys)))

# =========================
# MAIN LOOP
# =========================
for i, key in enumerate(random_days):
    print(f"Processing {key}")
    ds = read_s3_nc(key)

    if ds is None or VAR_NAME not in ds:
        continue

    plot_day_timeseries(ds, OUTPUT_DIR, i)

print("✅ Done.")
