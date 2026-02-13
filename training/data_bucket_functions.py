import boto3
import os
import logging
from botocore.exceptions import ClientError
from credentials_buckets import S3_ACCESS_KEY, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL
from config import *

def list_files_bucket(s3, S3_BUCKET_NAME):
    """
    script to list files in the bucket
    - s3: bucket to be checked
    
    """
    # List the objects in our bucket
    response = s3.list_objects(Bucket=S3_BUCKET_NAME)
    
    # set flag to false if file is not found
    filefound = False
    if "Contents" not in response:
        print(f"No files on bucket")
        return([])
    else:
        return(response["Contents"])
    


def check_file_bucket(file2find, domain):
    """code to check if a file is on the bucket
    input:
    file2find: filename with path to find n bucket
    domain: string, 'DE' or 'IT' for the domain to check the bucket
    
    return:
    filefound (boolean) true if file is found, false if file is not on the bucket
    """
    from readers.data_buckets_funcs import Initialize_s3_client, upload_file
    import boto3

    if domain == 'DE':
        from readers.s3_bucket_credentials import S3_BUCKET_NAME, S3_ACCESS_KEY, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL
        bucket_name = S3_BUCKET_NAME

    elif domain == 'IT':
        from readers.s3_bucket_credentials import S3_ACCESS_KEY, S3_SECRET_ACCESS_KEY, S3_ENDPOINT_URL
        bucket_name = "expats-radar-italy"
    else:
        print('domain not recognized')
        return(False)
    
    s3 = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY)
    
    
    # List the objects in our bucket
    response = s3.list_objects(Bucket=bucket_name)
    
    # set flag to false if file is not found
    filefound = False
    if "Contents" not in response:
        print(f"No files on bucket")
        
    
    # loop on files found on bucket
    for obj in response["Contents"]:
        key = obj["Key"]
        if key == file2find:
            filefound = True
            return filefound
        else:
            continue

    return filefound



def init_s3():
    """
    Initializes and returns an S3 client using the provided credentials and endpoint.
    """

    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY, 
    )

def read_file(s3, file_path, bucket):
    """ Reads a file from the specified S3 bucket and returns its content.
    :param s3: An initialized S3 client.
    :param file_path: The path to the file within the S3 bucket.
    :param bucket: The name of the S3 bucket.
    :return: The content of the file if it exists, otherwise None.
    """

    # print all files in the bucket for debugging
    #all_files = print_list_files_in_bucket(s3, bucket)
    # example: /data/sat/msg/ml_train_crops/IR_108-WV_062-CMA_FULL_EXPATS_DOMAIN/2025/08/merged_MSG_CMSAF_2025-08-22.nc

    try:
        obj = s3.get_object(Bucket=bucket, Key=file_path)
        return obj['Body'].read()
    except ClientError as e:
        logging.warning(f"Failed to read file {file_path}: {e}")
        return None



def read_bucket_name_path(year, month, day):

    """Returns the S3 bucket name based on the variable and on the date.
    This function determines the appropriate S3 bucket name for a given variable and date.
    :param var: str
        The variable for which to determine the S3 bucket name (e.g., 'IR_108', 'RR', 'lightning').
    :param yy: int
        The year component of the date.
    :param mm: int
        The month component of the date.
    :param dd: int
        The day component of the date.
    :return: str
        The name of the S3 bucket corresponding to the variable and date.   
    : returns: path_dir: str
        The path directory within the S3 bucket for the specified variable and date.
    
    """
    bucket_names = []
    file_names = []

    for i, var in enumerate(CLOUD_PRM):

        # read bucket name for the selected variable
        bucket_name = BUCKET_NAMES[i]

        # bucket names depending on the bucket to read from
        if var == 'IR_108' or var == 'HRV' or var == 'WV_062' or var == 'WV_073' or var == 'WV_087' or var == 'CMA':
            file_path = f"{PATH_DIR[i]}/{year:04d}/{month:02d}/{BASENAME[i]}_{year:04d}-{month:02d}-{day:02d}.nc"

        elif var == 'RR_de':
            #            20130908_RR_15min_msg_res.nc.gz. _RR_DE_15min_msg_res

            file_path = f"{year:04d}{month:02d}{day:02d}{BASENAME[i]}.nc.gz"

        elif var == 'RR_it':
            file_path = f"{PATH_DIR[i]}/COMP_{year:04d}{month:02d}{day:02d}{BASENAME[i]}.nc.gz"

        # appending to lists
        bucket_names.append(bucket_name)
        file_names.append(file_path)


    return bucket_names, file_names




def print_list_files_in_bucket(s3, S3_BUCKET_NAME):
    """Lists all files in the specified S3 bucket.
    input:
        s3: S3 client
        bucket: Name of the S3 bucket
    output:
        List of file keys in the bucket.
    """
    # Pagination to get all objects
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET_NAME)
    all_objects = []
    for page in pages:
        if "Contents" in page:
            for obj in page['Contents']:
                print(obj['Key'])  # Only print the Key
            all_objects.extend(page["Contents"])
    return all_objects



def list_files_bucket(s3, S3_BUCKET_NAME):
    """
    script to list files in the bucket
    - s3: bucket to be checked
    - S3_BUCKET_NAME: Name of the S3 bucket
    """
    # List the objects in our bucket
    response = s3.list_objects(Bucket=S3_BUCKET_NAME)
    
    # set flag to false if file is not found
    filefound = False
    if "Contents" not in response:
        print(f"No files on bucket")
        return([])
    else:
        return(response["Contents"])
