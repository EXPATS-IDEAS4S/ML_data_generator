"""Generate cropped training samples from MSG/CMA files stored in S3."""

from calendar import monthrange
import io
import logging
import os
from pathlib import Path
import sys

import numpy as np
import xarray as xr

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from cropping_functions import apply_cma_mask, crops_nc_fixed, crops_nc_random, filter_by_domain
from credentials_buckets import S3_ACCESS_KEY, S3_BUCKET_NAME, S3_ENDPOINT_URL, S3_SECRET_ACCESS_KEY
from training.config import (
    APPLY_CMA,
    BASENAME,
    CMA_APPLY_CLOSING,
    CMA_CLOSING_STRUCTURE,
    CLOUD_PRM,
    CROPPING_STRATEGY,
    CROP_UL_LAT,
    CROP_UL_LON,
    DOMAIN,
    DOMAIN_NAME,
    HOURS,
    MONTHS,
    N_SAMPLES,
    OUTPUT_BASE,
    PATH_DIR,
    RANDOM_SEED,
    VALUE_MAX,
    VALUE_MIN,
    YEARS,
    X_PIXEL,
    Y_PIXEL,
)

ALLOWED_HOURS = {f"{hour:02d}" for hour in HOURS}

import boto3
from botocore.exceptions import ClientError


def setup_logger():
    """Configure concise INFO-level logging for the batch job."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def init_s3():
    """Create an S3 client using the configured endpoint and credentials."""
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY
    )


def read_file(s3, file_path, bucket):
    """Read a single object from S3 and return its raw bytes, or None on failure."""
    try:
        obj = s3.get_object(Bucket=bucket, Key=file_path)
        return obj['Body'].read()
    except ClientError as e:
        logging.warning(f"Failed to read file {file_path}: {e}")
        return None


def _timestamp_parts(timestamp):
    """Return the hour and minute strings for a NumPy/Xarray timestamp."""
    timestamp_str = np.datetime_as_string(timestamp, unit="m")
    return timestamp_str[11:13], timestamp_str[14:16]


def _has_valid_value_range(ds_time):
    """Return True when every selected channel stays inside its configured value range."""
    for var, vmin, vmax in zip(CLOUD_PRM, VALUE_MIN, VALUE_MAX):
        data = ds_time[var]
        if data.min(skipna=True).item() < vmin or data.max(skipna=True).item() > vmax:
            return False
    return True


def process_timestamp(ds_time, file_name, timestamp, output_base):
    """Validate one time slice and dispatch the configured crop writer."""
    hour, minute = _timestamp_parts(timestamp)

    if not _has_valid_value_range(ds_time):
        return

    filename_to_save = f"{Path(file_name).stem}_{hour}:{minute}_{DOMAIN_NAME}"

    if CROPPING_STRATEGY == 'random':
        crops_nc_random(ds_time, X_PIXEL, Y_PIXEL, N_SAMPLES, filename_to_save, output_base, random_seed=RANDOM_SEED)
    elif CROPPING_STRATEGY == 'fixed':
        crops_nc_fixed(ds_time, X_PIXEL, Y_PIXEL, [(CROP_UL_LAT, CROP_UL_LON)], filename_to_save,  output_base)
    else:
        raise ValueError(f"Invalid cropping strategy: {CROPPING_STRATEGY}")


def main():
    """Iterate over configured dates, crop valid time slices, and write outputs."""
    setup_logger()
    s3 = init_s3()

    os.makedirs(OUTPUT_BASE, exist_ok=True)

    for year in YEARS:
        for month in MONTHS:
            days_in_month = monthrange(year, month)[1]
            for day in range(1, days_in_month + 1):
                file_path = f"{PATH_DIR}/{year:04d}/{month:02d}/{BASENAME}_{year:04d}-{month:02d}-{day:02d}.nc"
                logging.info(f"Processing file: {file_path}")
                file_obj = read_file(s3, file_path, S3_BUCKET_NAME)

                if file_obj is None:
                    continue

                try:
                    with xr.open_dataset(io.BytesIO(file_obj)) as ds_day:
                        ds_day_var = ds_day[CLOUD_PRM]

                        if APPLY_CMA and "cma" in ds_day and "IR_108" in CLOUD_PRM:
                            ds_day_var = apply_cma_mask(
                                ds_day,
                                ds_day_var,
                                VALUE_MAX,
                                apply_closing=CMA_APPLY_CLOSING,
                                closing_structure=CMA_CLOSING_STRUCTURE,
                            )

                        ds_day_var = filter_by_domain(ds_day_var, DOMAIN)

                        for timestamp in ds_day_var.time.values:
                            hour, _ = _timestamp_parts(timestamp)
                            if hour not in ALLOWED_HOURS:
                                continue

                            ds_time = ds_day_var.sel(time=timestamp)
                            process_timestamp(ds_time, file_path, timestamp, OUTPUT_BASE)
                except ValueError as e:
                    logging.warning(f"Skipping file due to domain error: {e}")
                except Exception as e:
                    logging.warning(f"Skipping file {file_path} due to: {e}")


if __name__ == "__main__":
    main()
