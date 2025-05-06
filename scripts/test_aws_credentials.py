#!/usr/bin/env python
"""
Script to test AWS credentials and check if they are configured correctly.
"""
import os
import sys
import json
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import AWS credential debugging function
from utils.s3_utils import debug_aws_credentials

def main():
    """Run the AWS credentials test and display results."""
    print("\n===== AWS Credentials Test =====\n")
    
    # Get debug information
    debug_info = debug_aws_credentials()
    
    # Display basic status
    print(f"Environment variables present: {debug_info['env_variables_set']}")
    print(f"AWS_ACCESS_KEY_ID set: {debug_info['access_key_present']}")
    print(f"AWS_SECRET_ACCESS_KEY set: {debug_info['secret_key_present']}")
    print(f"AWS_REGION_NAME set: {debug_info['region_present']}")
    print(f"AWS_S3_BUCKET set: {debug_info['bucket_present']}")
    print()
    
    # Display partial key info (for safety)
    if debug_info['access_key_present'] and 'aws_keys' in debug_info:
        print(f"Access Key ID: {debug_info['aws_keys'].get('access_key_id_prefix', 'N/A')}")
        if 'secret_key_length' in debug_info['aws_keys']:
            print(f"Secret Key: {debug_info['aws_keys'].get('secret_key_prefix', '')} (length: {debug_info['aws_keys'].get('secret_key_length', 0)})")
    print()
    
    # Display boto3 session status
    print(f"Boto3 session valid: {debug_info['boto3_session_valid']}")
    if 'boto3_session_error' in debug_info:
        print(f"Boto3 session error: {debug_info['boto3_session_error']}")
    print()
    
    # Display AWS config file status
    print(f"AWS config file present: {debug_info['aws_config_file_present']}")
    print(f"AWS credentials file present: {debug_info['aws_credential_file_present']}")
    print()
    
    # Overall assessment
    if debug_info['boto3_session_valid']:
        print("✅ AWS credentials appear to be valid!")
        print("You can now try uploading files to S3.")
    else:
        print("❌ AWS credentials validation failed!")
        print("\nPossible issues:")
        
        if not debug_info['env_variables_set']:
            print("- Environment variables not properly set in .env file")
            print("  Make sure you have the correct values in your .env file")
        
        if not any([debug_info['aws_config_file_present'], debug_info['aws_credential_file_present']]):
            print("- No AWS configuration files found in your home directory")
        
        print("\nRecommendations:")
        print("1. Check your .env file and make sure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set correctly")
        print("2. Verify that your AWS credentials have S3 permissions")
        print("3. Confirm that the bucket name is correct and exists in your AWS account")
        print("4. If you don't need S3 uploads, you can continue testing with local file storage")
    
    print("\n================================\n")

if __name__ == "__main__":
    main() 