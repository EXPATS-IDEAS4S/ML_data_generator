import os
import io
import boto3
from glob import glob
import logging
from botocore.exceptions import ClientError

from credentials_buckets import S3_BUCKET_NAME_CROPS, S3_ACCESS_KEY, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL

def upload_file(s3_client, file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)
    try:
        with open(file_name, "rb") as f:
            s3_client.upload_fileobj(f, bucket, file_name)
        #response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True
 


# Initialize the S3 client
s3 = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY
)

# # List the objects in our bucket
# response = s3.list_objects(Bucket=S3_BUCKET_NAME)
# for item in response['Contents']:
#     print(item['Key'])

#Directory with the data to upload
path_dir = "/data1/crops/test_case_essl_14-15-16-18-19-20-22-23-24_100x100_ir108_cma_traj/nc/1"

# Find all .nc files in the directory
data_filepattern = f"{path_dir}/*.nc"
file_list = sorted(glob(data_filepattern))

for file in file_list:
    print(f"Uploading: {file}")
    #Uploading a file to the bucket (make sure you have write access)
    upload_file(s3, file, S3_BUCKET_NAME_CROPS, file)
         


# List the objects in our bucket
response = s3.list_objects(Bucket=S3_BUCKET_NAME_CROPS)
for item in response['Contents']:
    print(item['Key'])

#1851259

