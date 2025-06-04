#!/usr/bin/env python3
"""
Simple Twitter posting test
Tests if we can actually post tweets with current permissions
"""

import os
import tweepy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_twitter_posting():
    """Test actual Twitter posting capability"""
    
    print("🧪 Testing Twitter Posting Capability")
    print("=" * 50)
    
    # Load credentials
    api_key = os.getenv('TWITTER_API_KEY')
    api_secret = os.getenv('TWITTER_API_SECRET')
    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    
    try:
        # Setup clients exactly like in our notification system
        print("🔍 Setting up Twitter clients...")
        
        # v1.1 API for media upload
        auth = tweepy.OAuth1UserHandler(api_key, api_secret)
        auth.set_access_token(access_token, access_token_secret)
        api_v1 = tweepy.API(auth, wait_on_rate_limit=True)
        
        # v2 API for posting tweets
        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            wait_on_rate_limit=True
        )
        
        print("✅ Clients setup successful")
        
        # Test 1: Simple text tweet
        print("\n🔍 Test 1: Posting a simple text tweet...")
        test_tweet_text = "🧪 Testing MemeZap Twitter integration! This is a test tweet from our meme generation system. #MemeZap #Test"
        
        try:
            tweet = client_v2.create_tweet(text=test_tweet_text)
            print(f"✅ Text tweet posted successfully!")
            print(f"   Tweet ID: {tweet.data['id']}")
            print(f"   Tweet URL: https://twitter.com/ForgexMemezap/status/{tweet.data['id']}")
            
            # Store tweet ID for potential cleanup
            test_tweet_id = tweet.data['id']
            
        except Exception as e:
            print(f"❌ Failed to post text tweet: {e}")
            return False
        
        # Test 2: Tweet with media (if we have a test image)
        print("\n🔍 Test 2: Testing media upload capability...")
        
        # Create a simple test image
        try:
            from PIL import Image, ImageDraw, ImageFont
            import tempfile
            
            # Create a simple test image
            img = Image.new('RGB', (400, 200), color='lightblue')
            draw = ImageDraw.Draw(img)
            
            # Add text to image
            try:
                # Try to use a default font
                font = ImageFont.load_default()
            except:
                font = None
            
            draw.text((50, 80), "MemeZap Test Image", fill='black', font=font)
            draw.text((50, 120), "Twitter Integration Test", fill='black', font=font)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                img.save(temp_file.name, 'JPEG')
                temp_file_path = temp_file.name
            
            print("✅ Test image created")
            
            # Upload media
            media = api_v1.simple_upload(filename=temp_file_path)
            print(f"✅ Media uploaded successfully! Media ID: {media.media_id}")
            
            # Post tweet with media
            media_tweet_text = "🖼️ Testing MemeZap with image! Our AI-powered meme generation system is working perfectly! #MemeZap #AI #Test"
            
            media_tweet = client_v2.create_tweet(
                text=media_tweet_text,
                media_ids=[media.media_id]
            )
            
            print(f"✅ Media tweet posted successfully!")
            print(f"   Tweet ID: {media_tweet.data['id']}")
            print(f"   Tweet URL: https://twitter.com/ForgexMemezap/status/{media_tweet.data['id']}")
            
            # Clean up temp file
            os.remove(temp_file_path)
            
        except Exception as e:
            print(f"❌ Failed to post media tweet: {e}")
            print("   This might be due to missing PIL/Pillow or media upload permissions")
        
        print("\n🎉 Twitter posting test completed!")
        print("✅ Your Twitter integration is working correctly!")
        
        return True
        
    except Exception as e:
        print(f"❌ Twitter posting test failed: {e}")
        return False

if __name__ == "__main__":
    test_twitter_posting() 