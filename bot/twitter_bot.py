#!/usr/bin/env python3
"""
MemeZap Twitter Bot - Public meme generation bot
Anyone can mention @memezap with an image to generate memes
"""

import tweepy
import requests
import os
import time
import logging
from PIL import Image
from io import BytesIO
import textwrap
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('meme_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MemeZapBot:
    def __init__(self):
        """Initialize the MemeZap bot"""
        # Load API credentials from environment variables
        self.api_key = os.getenv('TWITTER_API_KEY')
        self.api_secret = os.getenv('TWITTER_API_SECRET')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        
        # MemeZap API configuration
        self.memezap_api_url = os.getenv('MEMEZAP_API_URL', 'http://127.0.0.1:5003/api/smart_generate')
        
        if not all([self.api_key, self.api_secret, self.access_token, 
                   self.access_token_secret, self.bearer_token]):
            raise ValueError("Missing Twitter API credentials in environment variables")
        
        # Initialize Twitter API clients
        self.setup_twitter_clients()
        
        # Track processed tweets to avoid duplicates
        self.processed_tweets = set()
        self.load_processed_tweets()
        
        # Bot configuration
        self.trigger_phrases = ["meme", "make meme", "meme this", "generate meme"]
        self.max_text_length = 200
        
        # Get bot's user info
        self.bot_user_id = None
        self.bot_username = None
        self.get_bot_info()
        
        # Rate limiting
        self.last_check_time = None
        self.check_interval = 180  # 3 minutes between checks
    
    def setup_twitter_clients(self):
        """Setup Twitter API clients"""
        try:
            # Twitter API v1.1 (for media upload and posting)
            auth = tweepy.OAuthHandler(self.api_key, self.api_secret)
            auth.set_access_token(self.access_token, self.access_token_secret)
            self.api_v1 = tweepy.API(auth, wait_on_rate_limit=False)
            
            # Twitter API v2 (for reading tweets)
            self.client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=False
            )
            
            # Test authentication
            me = self.api_v1.verify_credentials()
            logger.info(f"🤖 MemeZap Bot authenticated as @{me.screen_name}")
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Twitter API: {e}")
            raise
    
    def get_bot_info(self):
        """Get the bot's user info"""
        try:
            me_v1 = self.api_v1.verify_credentials()
            me_v2 = self.client.get_me()
            
            self.bot_user_id = me_v2.data.id
            self.bot_username = me_v1.screen_name.lower()
            
            logger.info(f"🎭 Bot Username: @{me_v1.screen_name}")
            logger.info(f"📝 Anyone can mention @{me_v1.screen_name} to generate memes!")
            
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
    
    def load_processed_tweets(self):
        """Load previously processed tweet IDs"""
        try:
            if os.path.exists('processed_tweets.json'):
                with open('processed_tweets.json', 'r') as f:
                    self.processed_tweets = set(json.load(f))
        except Exception as e:
            logger.warning(f"Could not load processed tweets: {e}")
            self.processed_tweets = set()
    
    def save_processed_tweets(self):
        """Save processed tweet IDs"""
        try:
            with open('processed_tweets.json', 'w') as f:
                json.dump(list(self.processed_tweets), f)
        except Exception as e:
            logger.error(f"Could not save processed tweets: {e}")
    
    def check_mentions(self):
        """Check for new mentions from ANY Twitter user"""
        try:
            # Rate limiting check
            current_time = time.time()
            if self.last_check_time and (current_time - self.last_check_time) < self.check_interval:
                return
            
            self.last_check_time = current_time
            
            try:
                # Get mentions timeline - this gets ALL mentions of @memezap from ANY user
                mentions = self.api_v1.mentions_timeline(
                    count=20,  # Check more mentions
                    include_entities=True,
                    tweet_mode='extended'
                )
                
                if not mentions:
                    logger.info("No new mentions found")
                    return
                
                logger.info(f"📬 Found {len(mentions)} mentions to process")
                
                for tweet in mentions:
                    # Skip if already processed
                    if str(tweet.id) in self.processed_tweets:
                        continue
                    
                    # Skip if it's the bot's own tweet
                    if tweet.user.id == int(self.bot_user_id):
                        continue
                    
                    # Process the mention (any mention of @memezap)
                    logger.info(f"👤 Processing mention from @{tweet.user.screen_name}: {tweet.full_text[:50]}...")
                    self.process_meme_request(tweet)
                        
                    # Mark as processed
                    self.processed_tweets.add(str(tweet.id))
                
                self.save_processed_tweets()
                
            except tweepy.TooManyRequests:
                logger.warning("⏰ Rate limit hit, waiting...")
                return
            except tweepy.Unauthorized:
                logger.error("❌ Unauthorized - check API credentials")
                return
            except Exception as api_error:
                logger.error(f"API error: {api_error}")
                return
                
        except Exception as e:
            logger.error(f"Error checking mentions: {e}")
    
    def process_meme_request(self, tweet):
        """Process a meme request from ANY user"""
        try:
            # Extract image URL if present
            image_url = self.extract_image_url(tweet)
            
            if not image_url:
                # Try to get image from quoted tweet or reply chain
                image_url = self.get_image_from_context(tweet)
            
            if not image_url:
                self.reply_no_image(tweet.id, tweet.user.screen_name)
                return
            
            # Extract text for meme
            meme_text = self.extract_meme_text(tweet.full_text)
            
            # Create meme using MemeZap API
            logger.info(f"🎨 Generating meme for @{tweet.user.screen_name}")
            meme_image = self.create_meme_with_api(image_url, meme_text)
            
            if meme_image:
                # Reply with meme
                self.reply_with_meme(tweet.id, tweet.user.screen_name, meme_image)
            else:
                self.reply_error(tweet.id, tweet.user.screen_name)
                
        except Exception as e:
            logger.error(f"Error processing meme request: {e}")
            self.reply_error(tweet.id, tweet.user.screen_name)
    
    def extract_image_url(self, tweet):
        """Extract image URL from tweet"""
        try:
            # Check for images in the tweet
            if hasattr(tweet, 'entities') and 'media' in tweet.entities:
                for media in tweet.entities['media']:
                    if media['type'] == 'photo':
                        return media['media_url_https']
            
            if hasattr(tweet, 'extended_entities') and 'media' in tweet.extended_entities:
                for media in tweet.extended_entities['media']:
                    if media['type'] == 'photo':
                        return media['media_url_https']
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting image URL: {e}")
            return None
    
    def get_image_from_context(self, tweet):
        """Get image from quoted tweet or reply chain"""
        try:
            # Check if this is a quote tweet
            if hasattr(tweet, 'quoted_status'):
                return self.extract_image_url(tweet.quoted_status)
            
            # Check if this is a reply
            if tweet.in_reply_to_status_id:
                try:
                    referenced_tweet = self.api_v1.get_status(
                        tweet.in_reply_to_status_id,
                        tweet_mode='extended',
                        include_entities=True
                    )
                    return self.extract_image_url(referenced_tweet)
                except:
                    pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting image from context: {e}")
            return None
    
    def extract_meme_text(self, tweet_text):
        """Extract meme text from tweet"""
        import re
        
        # Remove bot mention
        text = re.sub(f'@{self.bot_username}', '', tweet_text, flags=re.IGNORECASE)
        
        # Remove trigger phrases
        for phrase in self.trigger_phrases:
            text = text.replace(phrase, "")
        
        # Remove other mentions and URLs
        words = text.split()
        filtered_words = [word for word in words if not word.startswith('@') and not word.startswith('http')]
        
        meme_text = ' '.join(filtered_words).strip()
        
        # Remove extra whitespace
        meme_text = re.sub(r'\s+', ' ', meme_text)
        
        # Default text if empty
        if not meme_text or len(meme_text) < 3:
            meme_text = "When someone mentions me|But forgets the text"
        
        return meme_text[:self.max_text_length]
    
    def create_meme_with_api(self, image_url, text):
        """Create meme using MemeZap API"""
        try:
            data = {
                'image_url': image_url,
                'caption': text
            }
            
            response = requests.post(
                self.memezap_api_url,
                data=data,
                timeout=120
            )
            
            if response.status_code == 200:
                logger.info("✅ Meme generated successfully")
                return BytesIO(response.content)
            else:
                logger.error(f"❌ MemeZap API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling MemeZap API: {e}")
            return None
    
    def reply_with_meme(self, tweet_id, username, meme_image):
        """Reply with generated meme"""
        try:
            # Upload media
            media = self.api_v1.media_upload(filename="meme.jpg", file=meme_image)
            
            # Reply with meme
            reply_text = f"@{username} Here's your meme! 🎭✨ #MemeZap #AI"
            self.api_v1.update_status(
                status=reply_text,
                in_reply_to_status_id=tweet_id,
                media_ids=[media.media_id]
            )
            
            logger.info(f"✅ Replied to @{username} with meme")
            
        except Exception as e:
            logger.error(f"Error replying with meme: {e}")
    
    def reply_no_image(self, tweet_id, username):
        """Reply when no image found"""
        try:
            reply_text = f"@{username} I need an image to make a meme! 📸\n\nTry:\n• Quote tweet an image with @{self.bot_username} text1|text2\n• Reply to an image with @{self.bot_username} your text"
            
            self.api_v1.update_status(
                status=reply_text,
                in_reply_to_status_id=tweet_id
            )
            
            logger.info(f"📝 Replied to @{username} - no image found")
            
        except Exception as e:
            logger.error(f"Error replying no image: {e}")
    
    def reply_error(self, tweet_id, username):
        """Reply when error occurs"""
        try:
            reply_text = f"@{username} Sorry, I couldn't generate your meme right now! 😅 Please try again later."
            
            self.api_v1.update_status(
                status=reply_text,
                in_reply_to_status_id=tweet_id
            )
            
            logger.info(f"⚠️ Replied to @{username} - error occurred")
            
        except Exception as e:
            logger.error(f"Error replying error: {e}")
    
    def run(self):
        """Main bot loop"""
        logger.info("🚀 Starting MemeZap Bot...")
        logger.info(f"🎯 Listening for mentions of @{self.bot_username}")
        logger.info(f"🔗 MemeZap API: {self.memezap_api_url}")
        logger.info(f"⏱️ Check interval: {self.check_interval} seconds")
        
        while True:
            try:
                logger.info("👀 Checking for new mentions...")
                self.check_mentions()
                logger.info(f"😴 Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(60)

def main():
    """Entry point"""
    try:
        bot = MemeZapBot()
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main()