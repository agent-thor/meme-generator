# Twitter Meme Generator Bot

This bot monitors Twitter mentions and automatically generates memes from images in the tweets it's mentioned in.

## How It Works

1. A Twitter user mentions the bot in a tweet containing an image and text
2. The bot downloads the image and saves it to the `data/user_query_meme` directory
3. The bot uploads the image to S3 for storage
4. The bot processes the text in the tweet to generate a meme
5. The generated meme is saved to the `data/user_response_meme` directory
6. The meme is uploaded to Twitter as a reply to the original tweet

## Setup Instructions

### 1. Twitter API Credentials

You'll need to create a Twitter Developer account and create a project with both v1 and v2 API access. The Twitter bot requires the following credentials:

- Consumer Key (API Key)
- Consumer Secret (API Secret)
- Access Token
- Access Token Secret
- Bearer Token

Add these to your `.env` file:

```
TWITTER_CONSUMER_KEY=your_consumer_key
TWITTER_CONSUMER_SECRET=your_consumer_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
TWITTER_BEARER_TOKEN=your_bearer_token
```

### 2. Required Python Packages

The bot requires the `tweepy` package in addition to the other dependencies used by the meme generator. Install it with:

```bash
pip install tweepy
```

### 3. Running the Bot

To start the Twitter bot, run:

```bash
python bot/twitter_bot.py
```

The bot will start monitoring Twitter for mentions and responding with generated memes.

## Usage

To use the bot once it's running:

1. Mention the bot in a tweet that contains an image: `@YourBotUsername This text will be added to the meme!`
2. The bot will reply with a generated meme including your text
3. For multiple text lines, separate with pipe (`|`) or newlines

## Features

- Processes mentions in real-time
- Handles images in original tweets or retweets
- Maintains original image in `user_query_meme` directory
- Saves generated memes in `user_response_meme` directory
- Falls back to local storage if S3 upload fails
- Comprehensive error handling and logging

## Troubleshooting

If the bot is not responding to mentions:

1. Check the log file at `logs/twitter_bot.log`
2. Verify your Twitter API credentials are correct
3. Ensure the Twitter account has proper read/write permissions
4. Make sure your S3 configuration is correct (or the bot will use local files) 