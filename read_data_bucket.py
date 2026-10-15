import io
import logging

import boto3
import xarray as xr

from botocore.exceptions import ClientError

from credentials_buckets import S3_BUCKET_NAME, S3_ACCESS_KEY, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL


def read_file(s3_client, file_name, bucket):
    """Read a file from an S3 bucket and return it as an in-memory buffer."""

    try:
        obj = s3_client.get_object(Bucket=bucket, Key=file_name)
        return io.BytesIO(obj["Body"].read())
    except ClientError as e:
        logging.error(e)
        return None


def iter_nc_keys(s3_client, bucket, prefix):
    """Yield all netCDF keys under a prefix."""

    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            key = item["Key"]
            if key.endswith(".nc"):
                yield key


def print_dataset_summary(key, dataset):
    print(f"\nFile: {key}")
    print(f"Dimensions: {dict(dataset.sizes)}")
    print(f"Data variables: {list(dataset.data_vars)}")
    print(dataset)


if __name__ == "__main__":
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    )

    years = [2013, 2014]
    months = range(4, 10)
    path_dir = "/data/sat/msg/ml_train_crops/IR_108-WV_062-CMA_FULL_EXPATS_DOMAIN"

    for year in years:
        for month in months:
            prefix = f"{path_dir}/{year:04d}/{month:02d}/"
            print(f"\nListing netCDF files under: {prefix}")

            try:
                for key in iter_nc_keys(s3, S3_BUCKET_NAME, prefix):
                    file_obj = read_file(s3, key, S3_BUCKET_NAME)
                    if file_obj is None:
                        continue

                    with xr.open_dataset(file_obj, engine="h5netcdf") as ds:
                        print_dataset_summary(key, ds)

            except ClientError as e:
                print(f"Failed to read files for {year}-{month:02d}: {e}")