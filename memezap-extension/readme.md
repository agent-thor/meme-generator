# MemeZap Chrome Extension

A browser extension that enhances Twitter by allowing users to automatically generate memes from images in quoted tweets.

## How It Works

1. When you want to memeify an image, quote tweet a tweet containing an image
2. Include `@memezap` in your tweet text (this is the trigger)
3. Add your caption text (this will be added to the meme)
4. The extension will:
   - Detect the `@memezap` trigger
   - Extract the image from the quoted tweet
   - Send it to your meme generator API
   - Replace the image with the meme version

## Installation

### Developer Mode (Local Installation)

1. Download or clone this repository
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable "Developer mode" by toggling the switch in the top right corner
4. Click "Load unpacked" and select the `memezap-extension` folder
5. The extension should now be installed and active

### Configuration

1. Click on the MemeZap extension icon in your browser toolbar
2. Select "Options" from the dropdown menu
3. Enter the URL of your meme generator API
   - Default: `http://localhost:8000/api/generate`
   - If you're hosting the API elsewhere, update this URL accordingly
4. Click "Save Settings"

## Requirements

- You need a running instance of the meme generator API
- The API should accept POST requests with:
  - `image_url`: URL of the image to memeify
  - `caption`: Text to add to the meme
- The API should return either:
  - A JSON response with `{ meme_url: "url_to_image" }`
  - Or directly return the image binary

## Using MemeZap

1. Find a tweet with an image you want to turn into a meme
2. Click the retweet button and select "Quote Tweet"
3. Type your caption and include `@memezap` anywhere in your text
4. The image should be automatically replaced with the meme version
5. Post your tweet with the meme!

## Troubleshooting

If the extension isn't working:

1. Check that the extension is enabled in Chrome
2. Verify that your meme generator API is running and accessible
3. Check the API URL in the extension options
4. Look for errors in the browser console (press F12 to open developer tools)

## Privacy

This extension:
- Only processes tweets containing the `@memezap` trigger
- Only sends image URLs and caption text to your configured API
- Does not collect any personal data
- Does not track your browsing activity 