#!/usr/bin/env python3
"""
Test script for Twitter notification system
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from bot.twitter_notif import notify_meme_generated, notify_simple

def test_twitter_notification():
    """Test the Twitter notification system"""
    
    print("🧪 Testing Twitter Notification System")
    print("=" * 50)
    
    # Test input
    test_input_text = "When you realize it's Friday but you still have work to do"
    test_meme_path = "data/user_response_meme/test_meme.jpg"  # This would be a real meme path
    
    print(f"📝 Test input text: {test_input_text}")
    print(f"🖼️  Test meme path: {test_meme_path}")
    print()
    
    # Test 1: Simple notification (text only)
    print("🔍 Test 1: Simple text notification")
    try:
        result = notify_simple(test_input_text)
        if result:
            print("✅ Simple notification posted successfully!")
        else:
            print("ℹ️  Simple notification was not posted (disabled or failed)")
    except Exception as e:
        print(f"❌ Error in simple notification: {e}")
    
    print()
    
    # Test 2: Full notification with meme (if meme file exists)
    print("🔍 Test 2: Full notification with meme image")
    if os.path.exists(test_meme_path):
        try:
            result = notify_meme_generated(
                input_text=test_input_text,
                meme_image_path=test_meme_path,
                from_template=True,
                similarity_score=85.5
            )
            if result:
                print("✅ Full notification with meme posted successfully!")
            else:
                print("ℹ️  Full notification was not posted (disabled or failed)")
        except Exception as e:
            print(f"❌ Error in full notification: {e}")
    else:
        print(f"⚠️  Meme file not found at {test_meme_path}, skipping full notification test")
    
    print()
    print("🏁 Test completed!")

if __name__ == "__main__":
    test_twitter_notification() 