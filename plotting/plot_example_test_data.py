import os
import io
import random
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import boto3
import sys
from scipy.ndimage import binary_closing
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# =========================
# CONFIG
# =========================
VAR_NAME = "IR_108"
FRAME_SIZE_PX = 100
N_TIMES = 3
N_DAYS = 10
BT_MIN = 200
BT_MAX = 320
RAIN_COLOR = "coral"
HAIL_COLOR = "aqua"

OUTPUT_BASE = (
    "/data1/crops/"
    "test_case_essl_14-15-16-18-19-20-22-23-24_100x100_ir108_cma"
)

EVENT_CSV = f"{OUTPUT_BASE}/eswd-v2-2012-2025_expats.csv"

RANDOM_SEED = 42
DOMAIN_EXTENT = [5, 16, 42, 51.5]  # lonmin, lonmax, latmin, latmax
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

OUTPUT_DIR = os.path.join(OUTPUT_BASE, f"test_examples_seed_{RANDOM_SEED}")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# S3
# =========================
sys.path.append("/home/Daniele/codes/ML_data_generator/")
from credentials_buckets import (
    S3_BUCKET_NAME,
    S3_ACCESS_KEY,
    S3_SECRET_ACCESS_KEY,
    S3_ENDPOINT_URL
)

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY,
)

def read_s3_nc(key):
    obj = s3.get_object(Bucket=S3_BUCKET_NAME, Key=key)
    return xr.open_dataset(io.BytesIO(obj["Body"].read()), engine="h5netcdf")

# =========================
# LOAD EVENT DATA
# =========================
#only open csv keep columns: TIME_EVENT, LONGITUDE, LATITUDE, TYPE_EVENT
events = pd.read_csv(EVENT_CSV, usecols=["TIME_EVENT", "LONGITUDE", "LATITUDE", "TYPE_EVENT"])
events["TIME_EVENT"] = pd.to_datetime(events["TIME_EVENT"], utc=True)

precip_grp = pd.read_csv(f"{OUTPUT_BASE}/PRECIP_grouped.csv")
hail_grp   = pd.read_csv(f"{OUTPUT_BASE}/HAIL_grouped.csv")
#print(precip_grp, hail_grp) 
#exit()
#Index(['LATITUDE', 'LONGITUDE', 'QC_LEVEL', 'TIME_EVENT', 'TYPE_EVENT','MAX_HAIL_DIAMETER', 'date', 'cluster_id', 'cluster_lat', 'cluster_lon','day_id'],


# =========================
# MAIN FUNCTION
# =========================
def plot_day(ds, day_events, day_clusters, outname):

    times = ds.time.values
    #select the first, the last and one random time in between
    sel_times = [times[0], times[-1]]
    #add timestamp at 16:00 UTC if exists
    time_1600 = np.datetime64(f"{np.datetime_as_string(times[0], unit='D')}T16:00")
    if time_1600 in times:
        sel_times.append(time_1600)
    else:
        sel_times.append(random.choice(times[1:-1]))
    # if N_TIMES > 2:
    #     sel_times.insert(1, np.random.choice(times[1:-1], 1)[0])
    sel_times = sorted(sel_times)

    lon = ds.lon.values
    lat = ds.lat.values
    dx = lon[1] - lon[0]
    dy = lat[1] - lat[0]

    # --- layout: image | ... | image | ... | image
    ncols = 5
    nrowws = 1
    fig = plt.figure(figsize=(18, 6))
    proj = ccrs.PlateCarree()

    gs = fig.add_gridspec(
        nrows=nrowws,
        ncols=ncols,
        width_ratios=[1, 0.08, 1, 0.08, 1],  # reduced ellipsis space
        wspace=0.05,
    )


    for i, t in enumerate(sel_times):
        col = i * 2
        ax = fig.add_subplot(gs[0, col], projection=proj)

        # --- ellipsis
        if col + 1 < ncols:
            ax_dots = fig.add_subplot(gs[0, col + 1])
            ax_dots.axis("off")
            ax_dots.text(
                0.5, 0.5, "...",
                fontsize=28,
                ha="center",
                va="center",
            )

        ir = ds[VAR_NAME].sel(time=t).values
        cma = ds["cma"].sel(time=t).values
        #close cma holes
        cma = binary_closing(cma, structure=np.ones((3,3))).astype(cma.dtype)  
        ir = ir.copy()
        ir[cma == 0] = 320.0

        ax.pcolormesh(
            lon, lat, ir,
            cmap="gray_r",
            vmin=200, vmax=320,
            transform=ccrs.PlateCarree()
        )

        ax.coastlines("50m", linewidth=0.8, color="yellow")
        ax.add_feature(cfeature.BORDERS, linewidth=0.5, edgecolor="yellow")

        # raw events
        p = day_events[day_events.TYPE_EVENT == "PRECIP"]
        h = day_events[day_events.TYPE_EVENT == "HAIL"]

        ax.scatter(p.LONGITUDE, p.LATITUDE, s=35, c=RAIN_COLOR, marker="o", transform=ccrs.PlateCarree())
        ax.scatter(h.LONGITUDE, h.LATITUDE, s=35, c=HAIL_COLOR, marker="o", transform=ccrs.PlateCarree())

        #cluster centers for PRECIP
        cluster_p = day_clusters[day_clusters.TYPE_EVENT == "PRECIP"]
        cluster_h = day_clusters[day_clusters.TYPE_EVENT == "HAIL"]
     
        ax.scatter(
            cluster_p.cluster_lon,
            cluster_p.cluster_lat,
            s=150, c=RAIN_COLOR, marker="*", edgecolor="black",
            transform=ccrs.PlateCarree()
        )
        ax.scatter(
            cluster_h.cluster_lon,
            cluster_h.cluster_lat,
            s=150, c=HAIL_COLOR, marker="*", edgecolor="black", #use star marker
            transform=ccrs.PlateCarree()
        )

        # ---- Frames around clusters (boundary-safe)
        ny, nx = len(lat), len(lon)
        half = FRAME_SIZE_PX // 2

        for _, c in day_clusters.iterrows():
            if c.TYPE_EVENT == "PRECIP":
                color = RAIN_COLOR
            else:
                color = HAIL_COLOR

            # Nearest grid point to cluster center
            ix_c = int(np.argmin(np.abs(lon - c.cluster_lon)))
            iy_c = int(np.argmin(np.abs(lat - c.cluster_lat)))

            # Desired lower-left pixel index (centered frame)
            ix0 = ix_c - half
            iy0 = iy_c - half

            # Shift frame if it would exceed domain boundaries (add one pixel margin)
            ix0 = max(1, min(ix0, nx - FRAME_SIZE_PX - 1))
            iy0 = max(1, min(iy0, ny - FRAME_SIZE_PX - 1))

            # Convert pixel indices back to lon/lat
            lon0 = lon[ix0]
            lat0 = lat[iy0]

            rect = patches.Rectangle(
                (lon0, lat0),
                FRAME_SIZE_PX * dx,
                FRAME_SIZE_PX * dy,
                linewidth=3,
                edgecolor=color,
                facecolor="none",
                transform=ccrs.PlateCarree(),
                zorder=6
            )

            ax.add_patch(rect)

        ax.set_title(np.datetime_as_string(t, unit="m"),
                            fontsize=16, fontweight="bold")

        gl = ax.gridlines(
                crs=ccrs.PlateCarree(),
                draw_labels=True,
                linewidth=0.8,
                color="gray",
                alpha=0.8,
                linestyle="--",
            )

        gl.top_labels = False
        gl.right_labels = False
        gl.left_labels = True
        gl.bottom_labels = True

        # ---- formatting
        gl.xlabel_style = {"size": 12}
        gl.ylabel_style = {"size": 12}
        
        # show only 4 integer values per axis 
        gl.xlocator = plt.MaxNLocator(4, integer=True)
        gl.ylocator = plt.MaxNLocator(4, integer=True)


    handles = [
        # ---- PRECIP ----
        Line2D([], [], marker='o', linestyle='None',
            markerfacecolor=RAIN_COLOR, markeredgecolor=RAIN_COLOR,
            label='Rain event'),
        Line2D([], [], marker='*', linestyle='None',
            color=RAIN_COLOR, markersize=8,
            label='Rain cluster'),
        Patch(facecolor='none', edgecolor=RAIN_COLOR, linewidth=2,
            label='Rain cluster crop'),

        # ---- HAIL ----
        Line2D([], [], marker='o', linestyle='None',
            markerfacecolor=HAIL_COLOR, markeredgecolor=HAIL_COLOR,
            label='Hail event'),
        Line2D([], [], marker='*', linestyle='None',
            color=HAIL_COLOR, markersize=8,
            label='Hail cluster'),
        Patch(facecolor='none', edgecolor=HAIL_COLOR, linewidth=2,
            label='Hail cluster crop'),
    ]

    fig.legend(
        handles=handles,
        loc="center right",
        #increase spacing to the right edge
        bbox_to_anchor=(1.02, 0.5),
        title="Event legend",
        fontsize=12,
        title_fontsize=14
    )

    #title for the entire figure (closer to the subplots)
    plt.suptitle(f"Test Dataset Preparation",fontsize=16, fontweight="bold", y=0.93)
    plt.savefig(outname, dpi=300, bbox_inches="tight")
    plt.close()


years = [2014, 2015, 2016, 2018, 2019, 2020, 2022, 2023, 2024]
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

    #extract day_id
    sample_day = os.path.basename(key).split("_")[-1].replace(".nc","")
    print(f"day_id: {sample_day}")
    sample_day_dt = pd.to_datetime(sample_day)

    # filter events
    day_events = events[events.TIME_EVENT.dt.date == sample_day_dt.date()]

    day_clusters = pd.concat([
        precip_grp[precip_grp.day_id == sample_day],
        hail_grp[hail_grp.day_id == sample_day]
    ])

    plot_day(
        ds,
        day_events,
        day_clusters,
        os.path.join(OUTPUT_DIR, f"events_{sample_day}.png")
    )
