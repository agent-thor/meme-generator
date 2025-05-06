"""
Twitter bot for meme generation based on mentions.
"""
import os
import time
import logging
import requests
import tweepy
from pathlib import Path
import sys
import uuid
import shutil
from dotenv import load_dotenv

# Add parent directory to sys.path to allow importing from other modules
sys.path.append(str(Path(__file__).parent.parent))
from ai_services.meme_service import MemeService
from utils.s3_utils import upload_file_to_s3
from utils.utils import download_image_from_url

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "twitter_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MemeTwitterBot:
    """Twitter bot for meme generation."""
    
    def __init__(self):
        """Initialize Twitter bot with API credentials."""
        # Twitter API credentials
        self.consumer_key = os.environ.get('TWITTER_CONSUMER_KEY')
        self.consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET')
        self.access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        self.bearer_token = os.environ.get('TWITTER_BEARER_TOKEN')
        
        # Validate credentials
        self._validate_credentials()
        
        # Initialize API
        self.client = tweepy.Client(
            bearer_token=self.bearer_token,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret
        )
        
        # Initialize v1 API for media upload
        self.api_v1 = tweepy.API(tweepy.OAuth1UserHandler(
            self.consumer_key,
            self.consumer_secret,
            self.access_token,
            self.access_token_secret
        ))
        
        # Initialize meme service
        self.meme_service = MemeService()
        
        # Configure directories
        self.user_query_dir = Path(__file__).parent.parent / "data" / "user_query_meme"
        self.user_response_dir = Path(__file__).parent.parent / "data" / "user_response_meme"
        
        # Create directories if they don't exist
        self.user_query_dir.mkdir(parents=True, exist_ok=True)
        self.user_response_dir.mkdir(parents=True, exist_ok=True)
        
        # Track processed tweets to avoid duplicates
        self.processed_tweets = set()
        
        # Get bot username
        try:
            self.bot_username = self.client.get_me().data.username
            logger.info(f"Bot initialized with username @{self.bot_username}")
        except Exception as e:
            logger.error(f"Failed to get bot username: {e}")
            self.bot_username = None
    
    def _validate_credentials(self):
        """Validate that all required credentials are set."""
        missing_keys = [
            key for key in [
                'TWITTER_CONSUMER_KEY', 
                'TWITTER_CONSUMER_SECRET', 
                'TWITTER_ACCESS_TOKEN', 
                'TWITTER_ACCESS_TOKEN_SECRET',
                'TWITTER_BEARER_TOKEN'
            ] if os.environ.get(key) is None
        ]
        
        if missing_keys:
            raise ValueError(f"Missing Twitter API credentials: {', '.join(missing_keys)}")
    
    def start(self, polling_interval=60):
        """
        Start the Twitter bot to monitor mentions.
        
        Args:
            polling_interval: Seconds between checks for new mentions
        """
        logger.info("Starting Twitter meme bot...")
        
        if not self.bot_username:
            logger.error("Bot username unknown, can't monitor mentions")
            return
        
        latest_id = None
        
        while True:
            try:
                # Get mentions
                mentions = self.client.get_users_mentions(
                    id=self.client.get_me().data.id,
                    since_id=latest_id,
                    expansions=['attachments.media_keys', 'referenced_tweets.id'],
                    media_fields=['url', 'preview_image_url']
                )
                
                if mentions.data:
                    # Update latest ID for pagination
                    latest_id = max(mention.id for mention in mentions.data)
                    
                    # Process each mention
                    for mention in mentions.data:
                        if mention.id not in self.processed_tweets:
                            self._process_mention(mention, mentions.includes)
                            self.processed_tweets.add(mention.id)
                
                # Cleanup processed tweets list occasionally to avoid memory bloat
                if len(self.processed_tweets) > 1000:
                    # Keep only the 100 most recent
                    self.processed_tweets = set(sorted(self.processed_tweets)[-100:])
                
            except Exception as e:
                logger.error(f"Error processing mentions: {e}")
            
            # Wait before next check
            logger.info(f"Waiting {polling_interval} seconds before next check...")
            time.sleep(polling_interval)
    
    def _process_mention(self, mention, includes):
        """
        Process a mention and generate a meme if it contains an image.
        
        Args:
            mention: The tweet mention object
            includes: Additional data included with the API response
        """
        try:
            tweet_id = mention.id
            tweet_text = mention.text
            logger.info(f"Processing mention [{tweet_id}]: {tweet_text}")
            
            # Extract text for meme (remove the @username part)
            meme_text = ' '.join(
                word for word in tweet_text.split()
                if not word.startswith('@')
            ).strip()
            
            # If no text provided, use a generic message
            if not meme_text:
                meme_text = "Add your caption here!"
            
            # Check if the tweet has media or is a retweet with media
            media_url = self._get_media_url(mention, includes)
            
            if not media_url:
                # Reply that we need an image
                self.client.create_tweet(
                    text="Please include an image to create a meme!",
                    in_reply_to_tweet_id=tweet_id
                )
                return
            
            # Download the image
            image_path = self._download_image(media_url)
            if not image_path:
                logger.error(f"Failed to download image from {media_url}")
                return
            
            # Upload image to S3
            s3_url = upload_file_to_s3(image_path)
            if not s3_url:
                logger.warning("S3 upload failed, using local file")
                s3_url = f"file://{image_path}"
            
            # Generate the meme
            meme_path = self._generate_meme(image_path, meme_text)
            if not meme_path:
                logger.error("Failed to generate meme")
                return
            
            # Upload meme to S3
            meme_s3_url = upload_file_to_s3(meme_path)
            if not meme_s3_url:
                logger.warning("S3 upload of meme failed, using local file")
                meme_s3_url = f"file://{meme_path}"
            
            # Reply with the meme
            self._reply_with_meme(tweet_id, meme_path)
            
        except Exception as e:
            logger.error(f"Error processing mention {mention.id}: {e}")
    
    def _get_media_url(self, mention, includes):
        """
        Extract media URL from a mention or its referenced tweet.
        
        Args:
            mention: The tweet mention object
            includes: Additional data included with the API response
            
        Returns:
            URL of the first image found, or None if no images
        """
        # Check if media is directly in the mention
        if hasattr(mention, 'attachments') and mention.attachments:
            media_keys = mention.attachments.get('media_keys', [])
            if media_keys and 'media' in includes:
                for media in includes['media']:
                    if media.media_key in media_keys and media.type == 'photo':
                        return media.url or media.preview_image_url
        
        # Check if it's a retweet/quote with media
        if hasattr(mention, 'referenced_tweets') and mention.referenced_tweets:
            for ref_tweet in mention.referenced_tweets:
                if ref_tweet.type in ('retweeted', 'quoted'):
                    # Look up the referenced tweet
                    if 'tweets' in includes:
                        for tweet in includes['tweets']:
                            if tweet.id == ref_tweet.id and hasattr(tweet, 'attachments'):
                                media_keys = tweet.attachments.get('media_keys', [])
                                if media_keys and 'media' in includes:
                                    for media in includes['media']:
                                        if media.media_key in media_keys and media.type == 'photo':
                                            return media.url or media.preview_image_url
        
        return None
    
    def _download_image(self, image_url):
        """
        Download an image from a URL and save it to the user_query_meme directory.
        
        Args:
            image_url: URL of the image to download
            
        Returns:
            Path to the downloaded image or None if download failed
        """
        try:
            # Generate a unique filename
            timestamp = int(time.time())
            filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
            save_path = self.user_query_dir / filename
            
            # Download image
            response = requests.get(image_url, stream=True, timeout=10)
            response.raise_for_status()
            
            # Save the image
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            
            logger.info(f"Downloaded image from {image_url} to {save_path}")
            return str(save_path)
            
        except Exception as e:
            logger.error(f"Error downloading image from {image_url}: {e}")
            return None
    
    def _generate_meme(self, image_path, text):
        """
        Generate a meme from an image and text.
        
        Args:
            image_path: Path to the input image
            text: Text to add to the image
            
        Returns:
            Path to the generated meme or None if generation failed
        """
        try:
            # Split text by pipe or newline for multiple captions
            text_list = text.split('|') if '|' in text else text.split('\n')
            
            # Generate the meme
            temp_output = self.meme_service.generate_meme(image_path, text_list)
            
            # Copy to user_response_meme with a unique name
            output_filename = f"twitter_response_{os.path.basename(image_path)}"
            output_path = str(self.user_response_dir / output_filename)
            
            # Copy the file
            shutil.copy2(temp_output, output_path)
            
            logger.info(f"Generated meme saved to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating meme: {e}")
            return None
    
    def _reply_with_meme(self, tweet_id, meme_path):
        """
        Reply to a tweet with the generated meme.
        
        Args:
            tweet_id: ID of the tweet to reply to
            meme_path: Path to the meme image
        """
        try:
            # Upload media using v1 API
            media = self.api_v1.media_upload(meme_path)
            media_id = media.media_id_string
            
            # Reply with the meme
            self.client.create_tweet(
                text="Here's your meme! #MemeGenerator",
                media_ids=[media_id],
                in_reply_to_tweet_id=tweet_id
            )
            
            logger.info(f"Successfully replied to tweet {tweet_id} with meme")
            
        except Exception as e:
            logger.error(f"Error replying with meme: {e}")

if __name__ == "__main__":
    try:
        # Create and start the Twitter bot
        bot = MemeTwitterBot()
        bot.start()
    except Exception as e:
        logger.critical(f"Fatal error in Twitter bot: {e}") 