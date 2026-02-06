import boto3
import os
import logging
from botocore.exceptions import ClientError

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
    