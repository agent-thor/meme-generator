/**
 * MemeZap Chrome Extension
 * Monitors Twitter for @memezap mentions in quoted tweets
 * and replaces images with meme-ified versions
 */

// Config - change API_URL to your actual backend URL
const CONFIG = {
  API_URL: 'http://localhost:8000/api/generate',
  TRIGGER_TAG: '@memezap',
  DEBUG: true  // Enable detailed logging
};

// Store processed tweets to avoid duplicates
const processedTweets = new Set();

/**
 * Logging function that respects debug setting
 */
function log(...args) {
  if (CONFIG.DEBUG) {
    console.log('MemeZap:', ...args);
  }
}

/**
 * Main initialization function
 */
function initMemeZap() {
  log('Extension initialized');
  
  // Start observing the page for tweet composition or quote tweets
  observeTwitterPage();
  
  // Load options from storage
  chrome.storage.sync.get(['apiUrl'], function(result) {
    if (result.apiUrl) {
      CONFIG.API_URL = result.apiUrl;
      log('Loaded API URL from settings:', CONFIG.API_URL);
    }
  });
  
  // Add manual tweet scan every second to catch tweets that might be missed
  setInterval(scanPageForTweets, 1000);
  
  // Log confirmation
  log('Watching for tweets containing:', CONFIG.TRIGGER_TAG);
  
  // Add debug menu
  addDebugMenu();
}

/**
 * Adds a debug popup menu for testing
 */
function addDebugMenu() {
  const menu = document.createElement('div');
  menu.id = 'memezap-debug';
  menu.innerHTML = `
    <div class="memezap-debug-menu">
      <h3>MemeZap Debug</h3>
      <button id="memezap-scan">Scan page for tweets</button>
      <button id="memezap-test">Test API connection</button>
      <div id="memezap-status"></div>
    </div>
  `;
  
  const style = document.createElement('style');
  style.textContent = `
    #memezap-debug {
      position: fixed;
      bottom: 20px;
      left: 20px;
      z-index: 10000;
      background: rgba(0, 0, 0, 0.8);
      border-radius: 5px;
      padding: 10px;
      color: white;
      font-family: sans-serif;
      font-size: 12px;
      display: none;
    }
    .memezap-debug-menu button {
      display: block;
      margin: 5px 0;
      padding: 5px;
      width: 100%;
      cursor: pointer;
    }
    #memezap-status {
      margin-top: 10px;
      padding: 5px;
      background: rgba(255, 255, 255, 0.1);
      max-height: 100px;
      overflow-y: auto;
    }
  `;
  
  document.head.appendChild(style);
  document.body.appendChild(menu);
  
  // Add Alt+M shortcut to toggle debug menu
  document.addEventListener('keydown', (e) => {
    if (e.altKey && e.key === 'm') {
      const menu = document.getElementById('memezap-debug');
      menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    }
  });
  
  // Add button event listeners
  document.getElementById('memezap-scan').addEventListener('click', () => {
    document.getElementById('memezap-status').textContent = 'Scanning...';
    const found = scanPageForTweets();
    document.getElementById('memezap-status').textContent = 
      `Scan complete. Found ${found} potential tweets.`;
  });
  
  document.getElementById('memezap-test').addEventListener('click', () => {
    document.getElementById('memezap-status').textContent = 'Testing API...';
    fetch(CONFIG.API_URL, { method: 'GET' })
      .then(response => {
        document.getElementById('memezap-status').textContent = 
          `API test: ${response.status} ${response.statusText}`;
      })
      .catch(error => {
        document.getElementById('memezap-status').textContent = 
          `API test failed: ${error.message}`;
      });
  });
}

/**
 * Sets up mutation observers to watch for Twitter content changes
 */
function observeTwitterPage() {
  // Observer for the entire page to catch new tweets and composition areas
  const pageObserver = new MutationObserver(mutations => {
    // Process mutations to find new content
    for (const mutation of mutations) {
      if (mutation.addedNodes && mutation.addedNodes.length > 0) {
        // Check for composing area
        const tweetBoxes = document.querySelectorAll('[data-testid="tweetTextarea_0"], [role="textbox"]');
        tweetBoxes.forEach(tweetBox => {
          if (!tweetBox.dataset.memezapMonitored) {
            tweetBox.dataset.memezapMonitored = 'true';
            tweetBox.addEventListener('input', handleTweetInput);
            log('Monitoring tweet composition area', tweetBox);
          }
        });
      }
    }
    
    // Check for quoted tweets
    scanPageForTweets();
  });

  // Start observing the page
  pageObserver.observe(document.body, { 
    childList: true, 
    subtree: true,
    characterData: true
  });
  
  log('Page observer started');
}

/**
 * Scans the entire page for tweets that might contain memezap
 */
function scanPageForTweets() {
  log('Scanning page for tweets');
  
  // Find all text content on the page
  const textElements = document.querySelectorAll('[data-testid="tweetText"], [role="textbox"]');
  let foundCount = 0;
  
  textElements.forEach(element => {
    const text = element.textContent || element.innerText;
    if (text && text.toLowerCase().includes(CONFIG.TRIGGER_TAG.toLowerCase())) {
      log('Found text with trigger:', text);
      foundCount++;
      
      // Get the closest tweet container
      const tweetContainer = element.closest('[data-testid="tweet"], [data-testid="tweetText"]');
      if (tweetContainer) {
        log('Found tweet container with trigger');
        processTweetWithMemeZap(tweetContainer);
      } else {
        // Might be in composition mode
        const composerBox = element.closest('[role="textbox"]');
        if (composerBox) {
          log('Found composer with trigger');
          processQuotedTweet();
        }
      }
    }
  });
  
  log(`Found ${foundCount} texts containing the trigger`);
  return foundCount;
}

/**
 * Handles input in the tweet composition area
 */
function handleTweetInput(event) {
  const text = event.target.innerText || event.target.textContent || '';
  log('Tweet input detected:', text);
  
  if (text.toLowerCase().includes(CONFIG.TRIGGER_TAG.toLowerCase())) {
    log('Trigger detected in tweet composition!');
    processQuotedTweet();
  }
}

/**
 * Processes a tweet that contains @memezap
 */
function processTweetWithMemeZap(tweetContainer) {
  // Try to get a unique ID for this tweet
  const tweetId = tweetContainer.dataset.testid || 
                  tweetContainer.getAttribute('aria-labelledby') || 
                  Date.now().toString();
  
  // Skip if already processed
  if (processedTweets.has(tweetId)) {
    log('Tweet already processed, skipping:', tweetId);
    return;
  }
  
  processedTweets.add(tweetId);
  log('Processing new tweet:', tweetId);
  
  // Look for quoted tweet
  const quotedTweet = tweetContainer.querySelector('[data-testid="quotedTweet"]') || 
                      tweetContainer.querySelector('[role="blockquote"]');
  
  if (quotedTweet) {
    log('Found quoted tweet, processing it');
    processQuotedTweetElement(quotedTweet, tweetContainer);
  } else {
    log('No quoted tweet found in:', tweetContainer);
  }
}

/**
 * Processes a quoted tweet that was found to contain @memezap
 */
function processQuotedTweet() {
  log('Attempting to find quoted tweet in composition mode');

  // Get the quoted tweet container - trying multiple selectors for robustness
  const quotedTweetSelectors = [
    '[data-testid="quotedTweet"]',
    '[role="blockquote"]',
    '[aria-labelledby*="quoted-tweet"]',
    '[aria-label*="Quote"]',
    '[aria-label*="quote"]'
  ];

  let quotedTweet = null;
  for (const selector of quotedTweetSelectors) {
    const element = document.querySelector(selector);
    if (element) {
      quotedTweet = element;
      log(`Found quoted tweet with selector: ${selector}`);
      break;
    }
  }

  if (!quotedTweet) {
    // Try finding by container relationships
    log('Trying to find quoted tweet by composition context');
    
    const compositionBox = document.querySelector('[data-testid="tweetTextarea_0"], [role="textbox"]');
    if (compositionBox) {
      // Look up to 5 levels up for a container that might contain the quoted tweet
      let current = compositionBox;
      for (let i = 0; i < 5; i++) {
        current = current.parentElement;
        if (!current) break;
        
        // Look for elements that might be media containers
        const mediaContainers = current.querySelectorAll('div[data-testid*="media"], [aria-labelledby*="image"], [role="img"]');
        if (mediaContainers.length > 0) {
          // Check if any contain images
          for (const container of mediaContainers) {
            const images = container.querySelectorAll('img');
            if (images.length > 0) {
              log('Found potential quoted tweet by media container');
              quotedTweet = container;
              break;
            }
          }
        }
        
        if (quotedTweet) break;
      }
    }
  }

  if (!quotedTweet) {
    // Last resort: look for any large image containers in the composition area
    const composers = document.querySelectorAll('[role="dialog"], [aria-label*="Compose"]');
    for (const composer of composers) {
      const images = composer.querySelectorAll('img[src*="twimg"]');
      if (images.length > 0) {
        log('Found image within composer dialog, treating parent as quoted tweet');
        // Use the closest container of the first image as the "quoted tweet"
        let container = images[0].parentElement;
        // Go up a couple levels to get a better container
        for (let i = 0; i < 3 && container; i++) {
          quotedTweet = container;
          container = container.parentElement;
        }
        break;
      }
    }
  }

  if (!quotedTweet) {
    log('No quoted tweet found in composition mode after all attempts');
    showErrorMessage('No quoted tweet found. Make sure you have an image in the quoted tweet.');
    return;
  }
  
  log('Found quoted tweet in composition mode, processing it');
  // Process the quoted tweet
  processQuotedTweetElement(quotedTweet);
}

/**
 * Processes a quoted tweet element to extract the image and send it to the backend
 */
function processQuotedTweetElement(quotedTweet, parentTweet = null) {
  log('Processing quoted tweet element:', quotedTweet);
  
  // Log all images in the quoted tweet for debugging
  const allImages = quotedTweet.querySelectorAll('img');
  log(`Found ${allImages.length} total images in quoted tweet`);
  allImages.forEach((img, i) => {
    log(`Image ${i+1} src: ${img.src.substring(0, 100)}...`);
  });
  
  // Find the image in the quoted tweet - try multiple selectors with more aggressive matching
  const imageSelectors = [
    'img[src*="pbs.twimg.com/media"]',
    'img[src*="twimg.com"]',
    '[data-testid="tweetPhoto"] img',
    'div[data-testid="tweetPhoto"] img',
    'div[aria-label="Image"] img',
    'div[role="img"] img',
    'img[alt]',
    'img'  // Last resort - any image
  ];
  
  let tweetImage = null;
  for (const selector of imageSelectors) {
    const images = quotedTweet.querySelectorAll(selector);
    if (images.length > 0) {
      // Prioritize larger images (likely the main tweet image)
      let bestImage = images[0];
      let largestArea = 0;
      
      for (const img of images) {
        const area = img.width * img.height;
        if (area > largestArea) {
          largestArea = area;
          bestImage = img;
        }
      }
      
      tweetImage = bestImage;
      log(`Found image with selector: ${selector}`);
      break;
    }
  }
  
  if (!tweetImage) {
    log('No image found in quoted tweet using standard selectors');
    
    // Last resort: look for any image in the quoted tweet's first 3 levels
    try {
      function findFirstImage(element, depth = 0) {
        if (depth > 3) return null;
        
        if (element.tagName === 'IMG' && element.src && !element.src.includes('profile')) {
          return element;
        }
        
        for (const child of element.children) {
          const found = findFirstImage(child, depth + 1);
          if (found) return found;
        }
        
        return null;
      }
      
      tweetImage = findFirstImage(quotedTweet);
      if (tweetImage) {
        log('Found image using recursive search:', tweetImage.src.substring(0, 100) + '...');
      }
    } catch (e) {
      log('Error in recursive image search:', e);
    }
  }
  
  if (!tweetImage) {
    log('No image found in quoted tweet after all attempts');
    showErrorMessage('No image found in the quoted tweet');
    return;
  }
  
  // Get the original image URL (highest quality)
  let originalImgUrl = tweetImage.src;
  // Replace any sizing parameters to get full resolution
  originalImgUrl = originalImgUrl.replace(/&name=\w+/, '&name=orig');
  
  log('Found image in quoted tweet:', originalImgUrl);
  log('Image dimensions:', tweetImage.width, 'x', tweetImage.height);
  
  // Get text from parent tweet to use as caption (excluding @memezap)
  let captionText = '';
  if (parentTweet) {
    const tweetTextElement = parentTweet.querySelector('[data-testid="tweetText"]');
    if (tweetTextElement) {
      captionText = tweetTextElement.innerText || tweetTextElement.textContent || '';
      captionText = captionText.replace(new RegExp(CONFIG.TRIGGER_TAG, 'i'), '').trim();
    }
  } else {
    // If in composition mode, get text from the composition area
    const compositionArea = document.querySelector('[data-testid="tweetTextarea_0"], [role="textbox"]');
    if (compositionArea) {
      captionText = compositionArea.innerText || compositionArea.textContent || '';
      captionText = captionText.replace(new RegExp(CONFIG.TRIGGER_TAG, 'i'), '').trim();
    }
  }
  
  log('Caption text:', captionText);
  
  // Send to backend
  sendImageToBackend(originalImgUrl, captionText, (memeUrl) => {
    if (memeUrl) {
      log('Received meme URL from backend:', memeUrl);
      
      // Replace the image in the tweet with the meme
      replaceImageInTweet(tweetImage, memeUrl);
      
      // If we're in composition mode, add the meme to the tweet composer
      if (!parentTweet) {
        addMemeToComposer(memeUrl);
      }
    }
  });
}

/**
 * Sends the image to the backend for processing
 */
function sendImageToBackend(imageUrl, caption, callback) {
  // Create form data for the API request
  const formData = new FormData();
  formData.append('image_url', imageUrl);
  formData.append('caption', caption);
  
  log('Sending to API:', imageUrl, caption);
  
  // Show loading state
  showLoadingState();
  
  fetch(CONFIG.API_URL, {
    method: 'POST',
    body: formData
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    // Check response type
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return response.json().then(data => {
        hideLoadingState();
        log('Received JSON response:', data);
        callback(data.meme_url);
      });
    } else {
      // Handle image response
      return response.blob().then(blob => {
        const url = URL.createObjectURL(blob);
        hideLoadingState();
        log('Received binary image response');
        callback(url);
      });
    }
  })
  .catch(error => {
    log('Error calling backend:', error);
    hideLoadingState();
    showErrorMessage(error.message);
    callback(null);
  });
}

/**
 * Replaces an image in a tweet with the meme version
 */
function replaceImageInTweet(imageElement, memeUrl) {
  // Get the original dimensions to maintain aspect ratio
  const originalWidth = imageElement.width;
  const originalHeight = imageElement.height;
  
  log('Replacing image:', originalWidth, 'x', originalHeight);
  
  // Create a new image element to replace the original
  const newImage = document.createElement('img');
  newImage.src = memeUrl;
  newImage.width = originalWidth;
  newImage.height = originalHeight;
  newImage.style.maxWidth = '100%';
  newImage.alt = 'Meme generated by MemeZap';
  
  // Replace the original image with the new one
  imageElement.parentNode.replaceChild(newImage, imageElement);
  
  // Show success message
  showSuccessMessage('Meme successfully generated!');
}

/**
 * Adds the meme to the tweet composer
 */
function addMemeToComposer(memeUrl) {
  // Check if there's already an image in the composer
  const existingImage = document.querySelector('[data-testid="attachments"] img');
  
  if (existingImage) {
    // Replace existing image
    log('Replacing existing image in composer');
    existingImage.src = memeUrl;
  } else {
    // Unfortunately, Twitter doesn't provide an easy way to programmatically add images
    log('Adding new image to composer not implemented - would need to simulate file input');
    showNotification('Your meme has been generated! Download and attach it to your tweet.', 'info');
    
    // Create a link to download the meme
    const downloadLink = document.createElement('a');
    downloadLink.href = memeUrl;
    downloadLink.download = 'memezap-meme.jpg';
    downloadLink.style.display = 'none';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
  }
}

/**
 * Shows a loading state when processing images
 */
function showLoadingState() {
  const loadingEl = document.createElement('div');
  loadingEl.id = 'memezap-loading';
  loadingEl.innerHTML = `
    <div class="memezap-overlay">
      <div class="memezap-spinner"></div>
      <div class="memezap-text">Generating meme...</div>
    </div>
  `;
  
  // Add styles
  const style = document.createElement('style');
  style.textContent = `
    #memezap-loading {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .memezap-overlay {
      background: rgba(0, 0, 0, 0.7);
      border-radius: 10px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .memezap-spinner {
      width: 50px;
      height: 50px;
      border: 5px solid #f3f3f3;
      border-top: 5px solid #1DA1F2;
      border-radius: 50%;
      animation: memezap-spin 1s linear infinite;
    }
    .memezap-text {
      color: white;
      margin-top: 10px;
      font-weight: bold;
    }
    @keyframes memezap-spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  `;
  
  document.head.appendChild(style);
  document.body.appendChild(loadingEl);
}

/**
 * Hides the loading state
 */
function hideLoadingState() {
  const loadingEl = document.getElementById('memezap-loading');
  if (loadingEl) {
    loadingEl.remove();
  }
}

/**
 * Shows a success message
 */
function showSuccessMessage(message) {
  showNotification(message, 'success');
}

/**
 * Shows an error message
 */
function showErrorMessage(message) {
  showNotification(`Error: ${message}`, 'error');
}

/**
 * Shows a notification message
 */
function showNotification(message, type) {
  const notificationEl = document.createElement('div');
  notificationEl.id = 'memezap-notification';
  notificationEl.className = `memezap-notification memezap-${type}`;
  notificationEl.innerHTML = `
    <div class="memezap-notification-content">
      <span>${message}</span>
    </div>
  `;
  
  // Add styles
  const style = document.createElement('style');
  style.textContent = `
    .memezap-notification {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 10000;
      min-width: 200px;
      padding: 10px 15px;
      border-radius: 5px;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
      animation: memezap-fade 4s forwards;
    }
    .memezap-success {
      background-color: #4CAF50;
      color: white;
    }
    .memezap-error {
      background-color: #F44336;
      color: white;
    }
    .memezap-info {
      background-color: #2196F3;
      color: white;
    }
    @keyframes memezap-fade {
      0% { opacity: 0; transform: translateY(20px); }
      10% { opacity: 1; transform: translateY(0); }
      90% { opacity: 1; transform: translateY(0); }
      100% { opacity: 0; transform: translateY(-20px); }
    }
  `;
  
  document.head.appendChild(style);
  document.body.appendChild(notificationEl);
  
  // Remove after animation completes
  setTimeout(() => {
    if (notificationEl.parentNode) {
      notificationEl.parentNode.removeChild(notificationEl);
    }
  }, 4000);
}

// Initialize the extension
initMemeZap();

// Also run after a delay to ensure it works on slow pages
setTimeout(initMemeZap, 1000);
setTimeout(scanPageForTweets, 2000);
setTimeout(scanPageForTweets, 5000); 





