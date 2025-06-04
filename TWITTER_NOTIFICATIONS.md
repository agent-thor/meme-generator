# Twitter Notification System

The MemeZap Twitter notification system automatically posts promotional tweets whenever memes are generated via the `smart_generate` API endpoint. This creates buzz around your meme generation engine and showcases the AI-powered capabilities.

## Features

🔥 **Automatic Promotional Tweets**: Posts engaging tweets when memes are generated  
🤖 **OpenAI-Powered Content**: Uses GPT-4o-mini to generate viral-worthy promotional text  
🖼️ **Image Attachments**: Includes the generated meme in the tweet  
📊 **Template Matching Info**: Shows similarity scores when templates are used  
⚙️ **Configurable**: Easy to enable/disable via environment variables  
🛡️ **Error Resilient**: API calls don't fail if Twitter posting fails  

## How It Works

1. **User generates meme** via `/api/smart_generate` endpoint
2. **Meme is successfully created** and saved
3. **Twitter notification triggers** automatically
4. **OpenAI generates promotional text** based on the input text
5. **Tweet is posted** with the meme image attached
6. **Buzz is created** about your meme generation platform!

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Twitter API Keys (required)
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Twitter Notifications (optional)
TWITTER_NOTIFICATIONS_ENABLED=true

# OpenAI API Key (optional, for better promotional text)
OPENAI_API_KEY=your_openai_api_key
```

### Enable/Disable Notifications

```bash
# Enable notifications
TWITTER_NOTIFICATIONS_ENABLED=true

# Disable notifications
TWITTER_NOTIFICATIONS_ENABLED=false
```

## Example Promotional Tweets

### With OpenAI (Dynamic)
```
🔥 Just witnessed pure meme magic! Someone dropped "When you realize it's Friday but you still have work to do" and our AI turned it into comedy gold! ✨ #MemeZap #AI #ViralContent 🎯 85.5% template match!
```

### Fallback (Without OpenAI)
```
🔥 Just generated an epic meme! Someone said: 'When you realize it's Friday but you still have work to do' and our AI-powered MemeZap engine created pure gold! ✨ #MemeGeneration #AI #Memes
```

## API Integration

The notification system is automatically integrated into the `smart_generate` endpoint:

```python
# In routes.py - automatically called after meme generation
twitter_success = notify_meme_generated(
    input_text=original_caption,
    meme_image_path=output_path,
    from_template=from_template,
    similarity_score=similarity_score
)
```

## Manual Usage

You can also trigger notifications manually:

```python
from bot.twitter_notif import notify_meme_generated, notify_simple

# Full notification with meme image
notify_meme_generated(
    input_text="Your meme text here",
    meme_image_path="/path/to/meme.jpg",
    from_template=True,
    similarity_score=85.5
)

# Simple text-only notification
notify_simple("Your meme text here")
```

## Testing

Run the test script to verify everything works:

```bash
cd memezap-backend
python test_twitter_notif.py
```

## Error Handling

- **Twitter API failures**: Logged but don't break meme generation
- **Missing OpenAI key**: Falls back to predefined promotional messages
- **Missing meme image**: Posts text-only notification
- **Rate limiting**: Automatically handled by tweepy
- **Disabled notifications**: Silently skipped

## Promotional Strategy

The system creates buzz by:

1. **Showcasing AI capabilities**: Mentions AI-powered generation
2. **Including user input**: Shows the original text that inspired the meme
3. **Adding viral elements**: Uses emojis, hashtags, and engaging language
4. **Template matching**: Highlights when AI finds similar templates
5. **Real-time posting**: Creates immediate social proof

## Security Notes

- Twitter API credentials are loaded from environment variables
- No sensitive user data is included in tweets
- Only the input text and generated meme are shared
- Rate limiting prevents spam
- Can be completely disabled if needed

## Troubleshooting

### Common Issues

1. **"Missing Twitter API credentials"**
   - Ensure all Twitter API keys are set in `.env`
   - Check that keys are valid and have proper permissions

2. **"Twitter notifications are disabled"**
   - Set `TWITTER_NOTIFICATIONS_ENABLED=true` in `.env`

3. **"OpenAI API key not found"**
   - Add `OPENAI_API_KEY` to `.env` for better promotional text
   - System will work with fallback messages if OpenAI is unavailable

4. **"Rate limit hit"**
   - Twitter has rate limits; notifications will resume automatically
   - Consider reducing notification frequency if needed

### Logs

Check the application logs for Twitter notification status:

```
✅ Successfully posted promotional tweet about generated meme
ℹ️ Twitter notification was not posted (disabled or failed)
❌ Error posting Twitter notification: [error details]
```

## Future Enhancements

- **Scheduled posting**: Batch notifications to avoid rate limits
- **Analytics tracking**: Monitor engagement on promotional tweets
- **Custom templates**: Different promotional text styles
- **Multi-platform**: Extend to other social media platforms
- **User mentions**: Tag users who generate particularly good memes 