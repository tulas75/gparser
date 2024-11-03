import boto3
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# AWS S3 Configuration
S3_BUCKET = os.environ['S3_BUCKET']
AWS_REGION = os.environ['AWS_REGION']
S3_ENDPOINT = os.environ['S3_ENDPOINT']
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
    endpoint_url=S3_ENDPOINT
)

def upload_file_to_s3(file, s3_file_name):
    """
    Upload a file to S3 bucket
    """
    try:
        s3_client.upload_fileobj(file, S3_BUCKET, s3_file_name)
        return True
    except Exception as e:
        raise Exception(f"Failed to upload file to S3: {str(e)}")
