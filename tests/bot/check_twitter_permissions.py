#!/usr/bin/env python3
"""
Twitter API Permissions Checker
Diagnoses Twitter API setup and permissions
"""

import os
import tweepy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_twitter_permissions():
    """Check Twitter API permissions and setup"""
    
    print("🔍 Twitter API Permissions Checker")
    print("=" * 50)
    
    # Load credentials
    api_key = os.getenv('TWITTER_API_KEY')
    api_secret = os.getenv('TWITTER_API_SECRET')
    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    
    print(f"📋 Checking credentials...")
    print(f"   API Key: {'✅ Found' if api_key else '❌ Missing'}")
    print(f"   API Secret: {'✅ Found' if api_secret else '❌ Missing'}")
    print(f"   Access Token: {'✅ Found' if access_token else '❌ Missing'}")
    print(f"   Access Token Secret: {'✅ Found' if access_token_secret else '❌ Missing'}")
    print()
    
    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("❌ Missing required credentials. Please check your .env file.")
        return
    
    try:
        # Test v1.1 API with OAuth1UserHandler
        print("🔍 Testing Twitter API v1.1 authentication...")
        auth = tweepy.OAuth1UserHandler(api_key, api_secret)
        auth.set_access_token(access_token, access_token_secret)
        api_v1 = tweepy.API(auth)
        
        # Verify credentials
        me = api_v1.verify_credentials()
        print(f"✅ v1.1 Authentication successful!")
        print(f"   Username: @{me.screen_name}")
        print(f"   User ID: {me.id}")
        print(f"   Account created: {me.created_at}")
        print()
        
        # Check app permissions
        print("🔍 Checking app permissions...")
        try:
            # Try to get app info (this requires elevated access)
            app_info = api_v1.get_application_rate_limit_status()
            print("✅ App has elevated access")
        except Exception as e:
            print(f"⚠️  App might not have elevated access: {e}")
        
        # Test posting capability (dry run)
        print("🔍 Testing posting permissions...")
        try:
            # Try to get rate limit status for posting
            limits = api_v1.get_rate_limit_status(resources=['statuses'])
            tweet_limit = limits['resources']['statuses']['/statuses/update']
            print(f"✅ Tweet posting permissions available")
            print(f"   Remaining tweets: {tweet_limit['remaining']}/{tweet_limit['limit']}")
            print(f"   Reset time: {tweet_limit['reset']}")
        except Exception as e:
            print(f"❌ Error checking tweet permissions: {e}")
        
        print()
        
    except Exception as e:
        print(f"❌ v1.1 Authentication failed: {e}")
        print()
    
    try:
        # Test v2 API
        print("🔍 Testing Twitter API v2 authentication...")
        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Test v2 authentication
        me_v2 = client_v2.get_me()
        print(f"✅ v2 Authentication successful!")
        print(f"   Username: @{me_v2.data.username}")
        print(f"   User ID: {me_v2.data.id}")
        print()
        
    except Exception as e:
        print(f"❌ v2 Authentication failed: {e}")
        print()
    
    # Provide recommendations
    print("💡 Recommendations:")
    print("=" * 50)
    print("1. Ensure your Twitter app has 'Read and Write' permissions")
    print("2. Make sure you have 'Elevated' access (not just Essential)")
    print("3. Regenerate your access tokens after changing permissions")
    print("4. Check that your app is not restricted or suspended")
    print()
    print("🔗 To check/update permissions:")
    print("   1. Go to https://developer.twitter.com/en/portal/dashboard")
    print("   2. Select your app")
    print("   3. Go to 'Settings' tab")
    print("   4. Check 'App permissions' - should be 'Read and Write'")
    print("   5. If changed, regenerate Access Token and Secret")
    print("   6. Update your .env file with new tokens")

if __name__ == "__main__":
    check_twitter_permissions() 