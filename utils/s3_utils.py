"""
S3 utility functions for uploading images to AWS S3.
"""
import logging
import boto3
import yaml
import os
from pathlib import Path
import uuid
from botocore.exceptions import ClientError, NoCredentialsError, CredentialRetrievalError
from dotenv import load_dotenv
import aioboto3
import aiofiles
import asyncio
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_aws_credentials():
    """
    Debug AWS credentials to check if they're properly set.
    
    Returns:
        dict: Debug information about the credentials
    """
    debug_info = {
        "env_variables_set": False,
        "access_key_present": False,
        "secret_key_present": False,
        "region_present": False,
        "bucket_present": False,
        "aws_config_file_present": False,
        "aws_credential_file_present": False,
        "credentials_in_config": False,
        "boto3_session_valid": False,
        "aws_keys": {}
    }
    
    # Check environment variables
    access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    region = os.environ.get('AWS_REGION_NAME')
    bucket = os.environ.get('AWS_S3_BUCKET')
    
    debug_info["access_key_present"] = access_key is not None
    debug_info["secret_key_present"] = secret_key is not None
    debug_info["region_present"] = region is not None
    debug_info["bucket_present"] = bucket is not None
    debug_info["env_variables_set"] = all([
        debug_info["access_key_present"],
        debug_info["secret_key_present"],
        debug_info["region_present"],
        debug_info["bucket_present"]
    ])
    
    # Check AWS config/credential files
    user_home = os.path.expanduser("~")
    aws_config_path = os.path.join(user_home, ".aws", "config")
    aws_credential_path = os.path.join(user_home, ".aws", "credentials")
    
    debug_info["aws_config_file_present"] = os.path.exists(aws_config_path)
    debug_info["aws_credential_file_present"] = os.path.exists(aws_credential_path)
    
    # Check config file
    config = load_config()
    aws_config = config.get('aws', {})
    debug_info["credentials_in_config"] = (
        aws_config.get('access_key_id') is not None and 
        aws_config.get('secret_access_key') is not None
    )
    
    # Safely display part of the keys for debugging (never full key)
    if access_key:
        debug_info["aws_keys"]["access_key_id_prefix"] = access_key[:4] + "..." + access_key[-4:]
    if secret_key:
        debug_info["aws_keys"]["secret_key_length"] = len(secret_key)
        debug_info["aws_keys"]["secret_key_prefix"] = secret_key[:4] + "..."
    
    # Try to create a boto3 session
    try:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        if session.get_credentials():
            debug_info["boto3_session_valid"] = True
    except Exception as e:
        debug_info["boto3_session_error"] = str(e)
    
    return debug_info

def load_config():
    """
    Load the configuration from config.yaml and substitute environment variables.
    
    Returns:
        dict: Configuration with environment variables substituted
    """
    config_path = Path(__file__).parent.parent / "config.yaml"
    
    with open(config_path, 'r') as f:
        yaml_content = f.read()
        
    # Replace environment variables placeholders
    for env_var in os.environ:
        placeholder = "${" + env_var + "}"
        if placeholder in yaml_content:
            yaml_content = yaml_content.replace(placeholder, os.environ[env_var])
    
    # Load the substituted YAML content
    return yaml.safe_load(yaml_content)

def get_s3_client():
    """
    Get an AWS S3 client using credentials from environment or config file.
    
    Returns:
        boto3.client: An S3 client
    """
    # First try to get credentials directly from environment variables
    access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    region = os.environ.get('AWS_REGION_NAME')
    
    # If not all environment variables are set, fall back to config
    if not all([access_key, secret_key, region]):
        config = load_config()
        aws_config = config.get('aws', {})
        
        access_key = access_key or aws_config.get('access_key_id')
        secret_key = secret_key or aws_config.get('secret_access_key')
        region = region or aws_config.get('region_name')
        
        if not all([access_key, secret_key, region]):
            logger.warning("AWS credentials not fully configured in environment variables or config.yaml")
            
            # Log detailed debug information
            debug_info = debug_aws_credentials()
            logger.warning(f"AWS credential debug info: {debug_info}")
    
    try:
        return boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
    except (NoCredentialsError, CredentialRetrievalError) as e:
        logger.error(f"AWS credential error: {e}")
        debug_info = debug_aws_credentials()
        logger.error(f"AWS credential debug info: {debug_info}")
        raise

def upload_file_to_s3(file_path, content_type=None):
    """
    Upload a file to an S3 bucket
    
    Args:
        file_path: Path to the file to upload
        content_type: Optional content type of the file
        
    Returns:
        URL of the uploaded file if successful, None otherwise
    """
    try:
        # Get bucket name from environment variable or config
        bucket_name = os.environ.get('AWS_S3_BUCKET')
        
        # If not in environment, try config
        if not bucket_name:
            config = load_config()
            bucket_name = config.get('aws', {}).get('s3_bucket')
        
        if not bucket_name:
            logger.error("S3 bucket name not configured in environment or config.yaml")
            return None
        
        # Generate a unique object name using UUID
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_name)[1]
        object_name = f"uploads/{uuid.uuid4()}{file_extension}"
        
        # Debug AWS credentials first
        logger.info("Checking AWS credentials before upload...")
        debug_info = debug_aws_credentials()
        logger.info(f"AWS credential status: {debug_info['boto3_session_valid']}")
        
        if not debug_info['boto3_session_valid']:
            logger.error("AWS credentials are invalid or incomplete")
            logger.error(f"Debug info: {debug_info}")
            
            # Temporary local fallback for testing
            local_url = f"file://{file_path}"
            logger.warning(f"Using local file path instead of S3: {local_url}")
            return local_url
        
        # Create S3 client
        s3_client = get_s3_client()
        
        # Set extra args if content type is provided
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        
        # Upload the file with extra args only if they exist
        if extra_args:
            s3_client.upload_file(
                file_path, 
                bucket_name, 
                object_name,
                ExtraArgs=extra_args
            )
        else:
            s3_client.upload_file(
                file_path, 
                bucket_name, 
                object_name
            )
        
        # Generate URL
        region = os.environ.get('AWS_REGION_NAME') or load_config().get('aws', {}).get('region_name')
        s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{object_name}"
        
        logger.info(f"File {file_path} uploaded to S3 bucket {bucket_name}")
        return s3_url
            
    except ClientError as e:
        error_msg = str(e)
        logger.error(f"Error uploading file to S3: {error_msg}")
        
        # Add more debug information for specific errors
        if 'AccessDenied' in error_msg:
            logger.error("Access denied. Check if your AWS credentials have permission to upload to this bucket.")
        elif 'NoSuchBucket' in error_msg:
            logger.error(f"Bucket '{bucket_name}' does not exist. Create it in the AWS console.")
        elif 'InvalidAccessKeyId' in error_msg:
            logger.error("Invalid AWS Access Key ID. Check your credentials.")
        elif 'SignatureDoesNotMatch' in error_msg:
            logger.error("Signature doesn't match. Check your AWS Secret Access Key.")
        elif 'AccessControlListNotSupported' in error_msg:
            logger.error("ACLs are not supported on this bucket. The bucket likely has ObjectOwnership set to 'Bucket owner enforced'.")
        
        # Fall back to local file for testing
        local_url = f"file://{file_path}"
        logger.warning(f"Using local file path instead of S3: {local_url}")
        return local_url
        
    except (NoCredentialsError, CredentialRetrievalError) as e:
        logger.error(f"AWS credential error: {e}")
        debug_info = debug_aws_credentials()
        logger.error(f"AWS credential debug info: {debug_info}")
        
        # Fall back to local file for testing
        local_url = f"file://{file_path}"
        logger.warning(f"Using local file path instead of S3: {local_url}")
        return local_url
        
    except Exception as e:
        logger.error(f"Unexpected error uploading to S3: {str(e)}")
        
        # Fall back to local file for testing
        local_url = f"file://{file_path}"
        logger.warning(f"Using local file path instead of S3: {local_url}")
        return local_url
        
def upload_image_to_s3(file_path):
    """
    Upload an image file to S3 with appropriate content-type.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        URL of the uploaded image
    """
    # Map file extensions to MIME types
    extension_to_content_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    
    # Determine content type from file extension
    file_extension = os.path.splitext(file_path)[1].lower()
    content_type = extension_to_content_type.get(file_extension, 'application/octet-stream')
    
    return upload_file_to_s3(file_path, content_type)

async def upload_file_to_s3_async(file_path, content_type=None):
    """
    Asynchronously upload a file to S3 and return the URL.
    
    Args:
        file_path: Path to the file to upload
        content_type: MIME type of the file (optional)
        
    Returns:
        URL of the uploaded file
    """
    try:
        # Get configuration
        config = load_config()
        bucket_name = config.get('bucket_name')
        
        # If no bucket name is configured, return local file path
        if not bucket_name:
            logger.warning("No S3 bucket configured, using local file path")
            local_url = f"file://{file_path}"
            return local_url
        
        # Generate a unique key for the file
        file_name = os.path.basename(file_path)
        key = f"uploads/{datetime.now().strftime('%Y%m%d')}/{str(uuid.uuid4())[:8]}/{file_name}"
        
        # Create a session
        session = aioboto3.Session()
        
        # Read file content asynchronously
        async with aiofiles.open(file_path, 'rb') as f:
            file_content = await f.read()
        
        # Upload to S3
        async with session.client('s3', 
                                  region_name=config.get('region_name'),
                                  aws_access_key_id=config.get('aws_access_key_id'),
                                  aws_secret_access_key=config.get('aws_secret_access_key')) as s3:
            
            # Set content type if provided, otherwise let S3 determine it
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            # Add public read permission
            extra_args['ACL'] = 'public-read'
            
            # Upload the file
            await s3.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=file_content,
                **extra_args
            )
            
            # Generate the URL
            url = f"https://{bucket_name}.s3.amazonaws.com/{key}"
            logger.info(f"File uploaded to S3: {url}")
            return url
            
    except Exception as e:
        logger.error(f"Unexpected error uploading to S3 asynchronously: {str(e)}")
        
        # Fall back to local file for testing
        local_url = f"file://{file_path}"
        logger.warning(f"Using local file path instead of S3: {local_url}")
        return local_url

async def upload_image_to_s3_async(file_path):
    """
    Asynchronously upload an image file to S3 with appropriate content-type.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        URL of the uploaded image
    """
    # Map file extensions to MIME types
    extension_to_content_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    
    # Determine content type from file extension
    file_extension = os.path.splitext(file_path)[1].lower()
    content_type = extension_to_content_type.get(file_extension, 'application/octet-stream')
    
    return await upload_file_to_s3_async(file_path, content_type) 