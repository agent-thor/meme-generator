"""
Handles Twitter mentions and media extraction for meme generation.
"""
import logging
import tweepy
import yaml
from typing import Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class TweetListener(tweepy.StreamingClient):
    def __init__(self, meme_generator, fallback_ai, bearer_token: str):
        super().__init__(bearer_token)
        self.meme_generator = meme_generator
        self.fallback_ai = fallback_ai
        self.config = self._load_config()
        
    def _load_config(self) -> dict:
        """Load configuration from config.yaml"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def on_tweet(self, tweet):
        """Handle incoming tweets."""
        try:
            # Check if tweet is a mention
            if not tweet.referenced_tweets:
                return
            
            # Extract media from tweet
            media_urls = self._extract_media(tweet)
            if not media_urls:
                logger.info(f"No media found in tweet {tweet.id}")
                return
            
            # Generate meme
            meme_path = self.meme_generator.generate_meme(media_urls[0])
            
            # Generate caption using AI
            caption = self.fallback_ai.generate_caption(meme_path)
            
            # Reply with the meme
            self._reply_with_meme(tweet, meme_path, caption)
            
        except Exception as e:
            logger.error(f"Error processing tweet {tweet.id}: {e}")
    
    def _extract_media(self, tweet) -> List[str]:
        """Extract media URLs from tweet."""
        media_urls = []
        if hasattr(tweet, 'attachments'):
            for media in tweet.attachments.get('media', []):
                if media['type'] == 'photo':
                    media_urls.append(media['url'])
        return media_urls
    
    def _reply_with_meme(self, tweet, meme_path: str, caption: str):
        """Reply to tweet with generated meme."""
        try:
            # Upload media
            media = self.api.media_upload(meme_path)
            
            # Create reply
            self.api.update_status(
                status=caption,
                in_reply_to_status_id=tweet.id,
                media_ids=[media.media_id]
            )
            
            logger.info(f"Successfully replied to tweet {tweet.id}")
        except Exception as e:
            logger.error(f"Error replying to tweet {tweet.id}: {e}") 