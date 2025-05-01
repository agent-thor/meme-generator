"""
Main entrypoint for the Twitter bot.
Handles initialization and main event loop.
"""
import logging
from tweet_listener import TweetListener
from meme_generator import MemeGenerator
from fallback_ai import FallbackAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Initialize and run the Twitter bot."""
    try:
        # Initialize components
        meme_generator = MemeGenerator()
        fallback_ai = FallbackAI()
        listener = TweetListener(meme_generator, fallback_ai)
        
        # Start listening for mentions
        logger.info("Starting Twitter bot...")
        listener.start()
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main() 
