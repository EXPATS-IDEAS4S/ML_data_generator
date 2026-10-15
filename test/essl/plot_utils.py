import random
from matplotlib.patches import Rectangle
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os
import numpy as np
import pandas as pd
from botocore.exceptions import ClientError
import sys
import boto3
import logging
import xarray as xr
import io
from data_utils import haversine_km

sys.path.append('/home/Daniele/codes/ML_data_generator/')
from credentials_buckets import S3_BUCKET_NAME, S3_ACCESS_KEY, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL


path_dir = f"/data/sat/msg/ml_train_crops/IR_108-WV_062-CMA_FULL_EXPATS_DOMAIN"
basename = "merged_MSG_CMSAF"

def read_file(s3, file_name, bucket):
    """Upload a file to an S3 bucket
    :param s3: Initialized S3 client object
    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :return: object if file was uploaded, else False
    """
    try:
        #with open(file_name, "rb") as f:
        obj = s3.get_object(Bucket=bucket, Key=file_name)
        #print(obj)
        myObject = obj['Body'].read()
    except ClientError as e:
        logging.error(e)
        return None
    return myObject


def initialize_s3_client():
    """
    Initialize S3 client using credentials from s3_credentials_buckets.py
    """
    # Initialize the S3 client
    s3 = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY
    )
    return s3


def plot_clusters(df, title, output_dir):
    """
    Quick visual check: plot events colored by cluster ID.
    """
    # Handle empty dataframe
    if df is None or df.empty:
        print("plot_clusters: empty dataframe, nothing to plot")
        return

    # Prepare figure with two subplots sharing the same geographic projection
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(16, 7),
        subplot_kw={"projection": ccrs.PlateCarree()}
    )
    ax_all, ax_centers = axes

    # Determine extent from the full dataset (with a small margin)
    lon_min, lon_max = df["LONGITUDE"].min(), df["LONGITUDE"].max()
    lat_min, lat_max = df["LATITUDE"].min(), df["LATITUDE"].max()
    margin = 0.5
    ax_all.set_extent([lon_min - margin, lon_max + margin, lat_min - margin, lat_max + margin])
    ax_centers.set_extent([lon_min - margin, lon_max + margin, lat_min - margin, lat_max + margin])

    for ax in (ax_all, ax_centers):
        ax.add_feature(cfeature.BORDERS, linestyle=":")
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.LAND, alpha=0.2)
        ax.add_feature(cfeature.RIVERS, alpha=0.3)

    # Left subplot: all events (uniform blue markers)
    ax_all.scatter(
        df["LONGITUDE"],
        df["LATITUDE"],
        color="blue",
        s=12,
        alpha=0.7,
        transform=ccrs.PlateCarree(),
    )
    ax_all.set_title(f"All events — {title}", fontsize=13, fontweight="bold")

    # Right subplot: cluster centers only
    # Prefer existing cluster center columns, otherwise compute from clustered points
    if "cluster_lat" in df.columns and "cluster_lon" in df.columns:
        centers = df[df["cluster_id"] >= 0][["cluster_id", "cluster_lat", "cluster_lon"]].drop_duplicates(subset=["cluster_id"]) 
        centers = centers.rename(columns={"cluster_lat": "LATITUDE", "cluster_lon": "LONGITUDE"})
    else:
        centers = (
            df[df["cluster_id"] >= 0]
            .groupby("cluster_id")[['LATITUDE', 'LONGITUDE']]
            .mean()
            .reset_index()
            .rename(columns={"LATITUDE": "LATITUDE", "LONGITUDE": "LONGITUDE"})
        )

    if centers is None or centers.empty:
        ax_centers.text(0.5, 0.5, "No cluster centers found", transform=ax_centers.transAxes,
                        ha="center", va="center")
    else:
        ax_centers.scatter(
            centers["LONGITUDE"],
            centers["LATITUDE"],
            color="blue",
            s=70,
            alpha=0.9,
            edgecolor="black",
            transform=ccrs.PlateCarree(),
        )

        ax_centers.set_title(f"Cluster centers — {title}", fontsize=13, fontweight="bold")

    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    outpath = os.path.join(output_dir, f"{title.replace(' ', '_')}.png")
    fig.savefig(outpath, dpi=150)
    plt.close(fig)




def plot_random_days_msg_clusters(
    df,
    n_days=1,
    max_slots=10,
    time_col="time_slot",
    domain=(5, 16, 42, 51.5),   # lon_min, lon_max, lat_min, lat_max
    res_deg=0.04,
    crop_pixels=100,
    seed=42,
    output_dir=None,
    filename="msg_physical_clusters"
):
    """
    Plot clustered events on a true MSG-like 0.04° grid
    with physically correct 100x100 pixel crops.
    """
    
    s3 = initialize_s3_client()
    
    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col], utc=True)

    random.seed(seed)

    lon_min, lon_max, lat_min, lat_max = domain

    # --- crop geometry (exact) ---
    crop_size_deg = crop_pixels * res_deg   # = 4.0°
    crop_half = crop_size_deg / 2            # = 2.0°

    days = sorted(df[time_col].dt.date.unique())
    days = random.sample(days, min(n_days, len(days)))

    for day in days:
        df_day = df[df[time_col].dt.date == day]
        slots = sorted(df_day[time_col].unique())[:max_slots]

        if len(slots) == 0:
            continue

        ncols = 5
        nrows = int(np.ceil(len(slots) / ncols))

        fig, axes = plt.subplots(
            nrows,
            ncols,
            figsize=(4.8 * ncols, 4.8 * nrows),
            subplot_kw=dict(projection=ccrs.PlateCarree()),
        )
        axes = np.atleast_1d(axes).flatten()

        for ax, slot in zip(axes, slots):
            print(f"Plotting {day} {slot}...")
            ax.set_extent(domain)
            
            #add actual MSG field from S3
            year = slot.year
            month = f"{slot.month:02d}"
            day = slot.day
            file = f"{path_dir}/{year:04d}/{month}/{basename}_{year:04d}-{month}-{day:02d}.nc"
            print(file)
            my_obj = read_file(s3, file, S3_BUCKET_NAME)
            if my_obj is not None:
                ds_day = xr.open_dataset(io.BytesIO(my_obj), engine='h5netcdf')
                #print(ds_day)
                
                #select only variable of interest
                ds_day_var = ds_day['IR_108']

                #select time nearest to slot
                #remove utc timezone for selection
                slot_naive = slot.tz_convert(None)
                ds_slot = ds_day_var.sel(time=slot_naive, method='nearest')
                #plot
                img = ds_slot.plot.imshow(
                    ax=ax,
                    transform=ccrs.PlateCarree(),
                    cmap='gray_r',
                    vmin=240,
                    vmax=300,
                )
            else:
                ax.add_feature(cfeature.COASTLINE)
                ax.add_feature(cfeature.BORDERS, linestyle=":")
                ax.add_feature(cfeature.LAND, alpha=0.25)
            # --- draw true MSG grid ---
            gl = ax.gridlines(
                draw_labels=False,
                linewidth=0.3,
                color="gray",
                alpha=0.3,
            )
            gl.xlocator = plt.MultipleLocator(res_deg)
            gl.ylocator = plt.MultipleLocator(res_deg)

            slot_df = df_day[df_day[time_col] == slot]

            # --- plot events ---
            for event_type in ['PRECIP', 'HAIL']:
                color = 'blue' if event_type == 'PRECIP' else 'green'
                ax.scatter(
                    slot_df.loc[slot_df.TYPE_EVENT == event_type, "LONGITUDE"],
                    slot_df.loc[slot_df.TYPE_EVENT == event_type, "LATITUDE"],
                    s=25,
                    c=color,
                    alpha=0.7,
                    label=event_type,
                )

            # --- cluster centers ---
            centers = (
                slot_df[slot_df.cluster_id >= 0]
                .drop_duplicates("cluster_id")
            )
            #colot clusters by event type majority
            ax.scatter(
                centers.cluster_lon,
                centers.cluster_lat,
                s=140,
                marker="X",
                color=color,
                edgecolor="white",
                linewidth=1.2,
                zorder=6,
                label="Cluster center",
            )

            # --- draw physically correct crop ---
            for _, row in centers.iterrows():
                cx, cy = row.cluster_lon, row.cluster_lat

                x0 = np.clip(cx - crop_half, lon_min, lon_max - crop_size_deg)
                y0 = np.clip(cy - crop_half, lat_min, lat_max - crop_size_deg)

                rect = Rectangle(
                    (x0, y0),
                    crop_size_deg,
                    crop_size_deg,
                    linewidth=2.2,
                    edgecolor="red",
                    facecolor="none",
                    zorder=5,
                )
                ax.add_patch(rect)

            ax.set_title(
                slot.strftime(f"%Y-%m-%d %H:%M UTC"),
                fontsize=12,
                fontweight="bold",
            )

        for ax in axes[len(slots):]:
            ax.axis("off")

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=4)

        fig.suptitle(
            f"{day} - MSG-like clusters",
            fontsize=17,
            fontweight="bold",
        )

        plt.tight_layout(rect=[0, 0.06, 1, 0.95])

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            out = f"{output_dir}/{filename}_{day}.png"
            plt.savefig(out, dpi=200)
            print(f"✅ Saved {out}")

        plt.show()
        plt.close(fig)



def trajectory_diagnostics_plot(
    df_traj,
    storm_id_col="merged_storm_id",
    n_days=3,
    domain=(5, 16, 42, 51.5),
    res_deg=0.04,
    crop_pixels=100,
    seed=42,
    output_dir=None,
):
    """
    General diagnostic and plotting function for storm trajectories.

    Parameters
    ----------
    df_traj : pd.DataFrame
        Trajectory dataframe with columns:
        ['time', 'storm_id', 'lat', 'lon', 'cluster_event_type', 'source', 'storm_type', 'type_transition']
        'source' = observed / interpolated / extrapolated
    n_days : int
        Number of random days to plot
    max_slots : int
        Maximum number of time slots per day
    domain : tuple
        (lon_min, lon_max, lat_min, lat_max)
    res_deg : float
        MSG grid resolution in degrees
    crop_pixels : int
        Crop size in pixels
    seed : int
        Random seed for day selection
    output_dir : str
        Optional directory to save plots
    """
    s3 = initialize_s3_client()
    df_traj = df_traj.copy()
    
    # Ensure proper datetime
    df_traj['time'] = pd.to_datetime(df_traj['time'], utc=True)
    df_traj['date'] = df_traj['time'].dt.date

    lon_min, lon_max, lat_min, lat_max = domain
    crop_size_deg = crop_pixels * res_deg
    crop_half = crop_size_deg / 2

    np.random.seed(seed)

    # ---- Randomly select days to plot ----
    days = sorted(df_traj['date'].unique())
    plot_dates = np.random.choice(days, size=min(n_days, len(days)), replace=False)
  
    for date in plot_dates:
        df_day = df_traj[df_traj['date']==date]
        #trajectory_type = df_day['storm_type'].iloc[0]
        slots = sorted(df_day['time'].unique()) #slots are the timestamps for that day
        if len(slots) == 0:
            continue

        day_storms_ids = df_day[storm_id_col].unique()
        n_storms = len(day_storms_ids)
        #take a categorical list of color (RGB) to macht the storms ids
        colors = plt.cm.get_cmap('tab20', n_storms).colors

        ncols = 8
        nrows = int(np.ceil(len(slots)/ncols))
        fig, axes = plt.subplots(
            nrows, ncols,
            figsize=(4.8*ncols, 4.8*nrows),
            subplot_kw=dict(projection=ccrs.PlateCarree())
        )
        axes = np.atleast_1d(axes).flatten()

        #add actual MSG field from S3
        year = date.year
        month = f"{date.month:02d}"
        day = date.day
        file = f"{path_dir}/{year:04d}/{month}/{basename}_{year:04d}-{month}-{day:02d}.nc"
        print(file)
        my_obj = read_file(s3, file, S3_BUCKET_NAME)
        if my_obj is not None:
            ds_msg_day = xr.open_dataset(io.BytesIO(my_obj), engine='h5netcdf')
            #select only variable of interest
            ds_msg_day_var = ds_msg_day['IR_108']

            for ax, slot in zip(axes, slots):
                print(f"Plotting {day} {slot}...")
                ax.set_extent(domain)
                #select time nearest to slot
                #remove utc timezone for selection
                slot_naive = slot.tz_convert(None)
                ds_msg_slot = ds_msg_day_var.sel(time=slot_naive, method='nearest')
                #check if ds_slot is filled with NaNs
                if ds_msg_slot.isnull().all():
                    ax.add_feature(cfeature.COASTLINE)
                    ax.add_feature(cfeature.BORDERS, linestyle=":")
                    ax.add_feature(cfeature.LAND, alpha=0.25)
                    ax.gridlines(draw_labels=False, linewidth=0.3, color='gray', alpha=0.3)
                    continue                
                else:
                    #plot (no colorbar)
                    ds_msg_slot.plot.imshow(
                        ax=ax,
                        transform=ccrs.PlateCarree(),
                        cmap='gray_r',
                        vmin=240,
                        vmax=300,
                        add_colorbar=False
                    )

                df_slot = df_day[df_day['time']==slot]
                #time,storm_id,lat,lon,cluster_event_type,source,storm_type,type_transition
                #print(df_slot)
                #get evetntype 
                slot_storms_ids = df_slot[storm_id_col].unique()
                #find the index matching the storm ids to have consistent colors
                slot_colors = colors[[np.where(day_storms_ids == sid)[0][0] for sid in slot_storms_ids]]
    
                #take a categorical list of color (RGB) to macht the storms ids
                for storm, color in zip(slot_storms_ids, slot_colors):
                    df_strom = df_slot[df_slot[storm_id_col]==storm]
                    storm_type = df_strom['storm_type'].iloc[0]
                    if storm_type is None:
                        marker = 'x'
                    else:
                        marker = 'o' if storm_type == 'PRECIP' else '^' if storm_type == 'HAIL' else 's'

                    # --- plot events by type ---
                    #for event_type, color in zip(['PRECIP','HAIL','MIXED'], ['blue','green','orange']):
                    ax.scatter(
                        df_strom['lon'].iloc[0],
                        df_strom['lat'].iloc[0],
                        s=200, color=color, alpha=0.7, marker=marker,
                        edgecolor='black',
                    )
                    #chech source and set marker style
                    source = df_strom['source'].iloc[0]
                    if source == 'observed':
                        linestyle = '-'
                    elif source == 'interpolated':
                        linestyle = '--'
                    elif source == 'extrapolated': 
                        linestyle = ':'

                    # --- draw crop rectangle ---
                    cx, cy = df_strom['lon'].iloc[0], df_strom['lat'].iloc[0]
                    x0 = np.clip(cx - crop_half, lon_min, lon_max - crop_size_deg)
                    y0 = np.clip(cy - crop_half, lat_min, lat_max - crop_size_deg)
                    rect = Rectangle((x0,y0), crop_size_deg, crop_size_deg,
                                    linewidth=7, edgecolor=color, facecolor='none', zorder=5, linestyle=linestyle)
                    ax.add_patch(rect)

                ax.set_title(slot.strftime("%Y-%m-%d %H:%M UTC"), fontsize=12, fontweight='bold')

        for ax in axes[len(slots):]:
            ax.axis('off')

        
        fig.suptitle(f"{date} - Trajectories of {n_storms} cells/storms", fontsize=17, fontweight='bold')
        plt.tight_layout(rect=[0,0.06,1,0.95])

        if output_dir:
            import os
            os.makedirs(output_dir, exist_ok=True)
            outpath = f"{output_dir}/trajectory_plot_{day}.png"
            plt.savefig(outpath, dpi=200)
            print(f"✅ Saved {outpath}")

        plt.show()
        plt.close(fig)




def trajectory_diagnostics_stats(
    df_traj,
    storm_id_col="merged_storm_id",
    time_col="time",
    lat_col="lat",
    lon_col="lon",
    type_col="cluster_event_type",
    source_col="source",
    intensity_col="max_intensity",   # can be None or mean_intensity
    output_dir=None,
):
    """
    Compute detailed diagnostics for merged storm trajectories.

    Parameters
    ----------
    df_traj : pd.DataFrame
        Trajectory dataframe AFTER merging.
    """

    df = df_traj.copy()

    # ---- ensure datetime ----
    df[time_col] = pd.to_datetime(df[time_col], utc=True)

    traj_stats = []

    for sid, g in df.groupby(storm_id_col):

        g = g.sort_values(time_col)

        times = g[time_col].values
        lats = g[lat_col].values
        lons = g[lon_col].values

        # -------------------------
        # 1. Temporal properties
        # -------------------------
        start_time = g[time_col].min()
        end_time = g[time_col].max()
        lifetime_min = (end_time - start_time).total_seconds() / 60

        # -------------------------
        # 2. Distance & speed
        # -------------------------
        dists = [0.0]
        speeds = [0.0]

        for i in range(1, len(g)):
            d = haversine_km(
                lats[i-1], lons[i-1],
                lats[i], lons[i]
            )
            dt_h = (times[i] - times[i-1]) / np.timedelta64(1, "h")

            dists.append(d)
            speeds.append(d / dt_h if dt_h > 0 else 0.0)

        total_distance_km = np.sum(dists)
        mean_speed_kmh = np.mean(speeds)
        max_speed_kmh = np.max(speeds)

        # -------------------------
        # 3. Source diagnostics
        # -------------------------
        n_observed = (g[source_col] == "observed").sum()
        n_interpolated = (g[source_col] == "interpolated").sum()
        n_extrapolated = (g[source_col] == "extrapolated").sum()

        # -------------------------
        # 4. Event-type diagnostics
        # -------------------------
        n_hail = (g['n_hail']).sum()
        n_precip = (g['n_precip']).sum()

        if n_hail > 0 and n_precip > 0:
            storm_type = "MIXED"
        elif n_hail > 0 and n_precip == 0:
            storm_type = "HAIL"
        elif n_precip > 0 and n_hail == 0:
            storm_type = "PRECIP"
        else:
            storm_type = "UNKNOWN"

        # -------------------------
        # 5. Intensity diagnostics
        # -------------------------
        max_intensity_hail = None
        mean_intensity_hail = None
        max_intensity_precip = None
        mean_intensity_precip = None

        if intensity_col and intensity_col in g.columns:

            hail_vals = g.loc[g[type_col] == "HAIL", intensity_col].dropna()
            precip_vals = g.loc[g[type_col] == "PRECIP", intensity_col].dropna()

            if len(hail_vals) > 0:
                max_intensity_hail = hail_vals.max()
                mean_intensity_hail = hail_vals.mean()

            if len(precip_vals) > 0:
                max_intensity_precip = precip_vals.max()
                mean_intensity_precip = precip_vals.mean()

        # -------------------------
        # 6. Collect stats
        # -------------------------
        traj_stats.append({
            "merged_storm_id": sid,
            "storm_type": storm_type,

            "n_points": len(g),
            "start_time": start_time,
            "end_time": end_time,
            "lifetime_min": lifetime_min,

            "total_distance_km": total_distance_km,
            "mean_speed_kmh": mean_speed_kmh,
            "max_speed_kmh": max_speed_kmh,

            "n_observed": n_observed,
            "n_interpolated": n_interpolated,
            "n_extrapolated": n_extrapolated,

            "n_hail": n_hail,
            "n_precip": n_precip,

            "max_intensity_hail": max_intensity_hail,
            "mean_intensity_hail": mean_intensity_hail,
            "max_intensity_precip": max_intensity_precip,
            "mean_intensity_precip": mean_intensity_precip,
        })

    stats_df = pd.DataFrame(traj_stats)
    print(stats_df.head())

    print("\nTrajectory diagnostics summary:")
    #print all columns statistics clearly
    for col in stats_df.columns:
        print(f"\n--- {col} ---")
        print(stats_df[col].describe(include="all"))
    #print(stats_df.describe(include="all"))

    #save them in a csv file
    if output_dir:
        outpath = f"{output_dir}/trajectory_diagnostics_stats.csv"
        stats_df.to_csv(outpath, index=False)
        print(f"✅ Saved {outpath}")

    return stats_df
