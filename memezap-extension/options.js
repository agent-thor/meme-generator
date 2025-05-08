/**
 * MemeZap extension options page script
 * Handles loading and saving user configuration options
 */

// Default settings
const DEFAULT_SETTINGS = {
  apiUrl: 'http://localhost:8000/api/generate'
};

// DOM elements
const apiUrlInput = document.getElementById('apiUrl');
const saveButton = document.getElementById('saveButton');
const statusEl = document.getElementById('status');

/**
 * Load saved settings from Chrome storage
 */
function loadSavedSettings() {
  chrome.storage.sync.get(DEFAULT_SETTINGS, (items) => {
    apiUrlInput.value = items.apiUrl || '';
  });
}

/**
 * Save settings to Chrome storage
 */
function saveSettings() {
  const settings = {
    apiUrl: apiUrlInput.value.trim() || DEFAULT_SETTINGS.apiUrl
  };
  
  chrome.storage.sync.set(settings, () => {
    showStatus('Settings saved successfully!', 'success');
    
    // Reset status message after 3 seconds
    setTimeout(() => {
      hideStatus();
    }, 3000);
  });
}

/**
 * Displays a status message
 */
function showStatus(message, type) {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
}

/**
 * Hides the status message
 */
function hideStatus() {
  statusEl.className = 'status';
}

/**
 * Validates the API URL format
 */
function validateApiUrl(url) {
  try {
    new URL(url);
    return true;
  } catch (e) {
    return false;
  }
}

// Set up event listeners
document.addEventListener('DOMContentLoaded', loadSavedSettings);

saveButton.addEventListener('click', () => {
  const apiUrl = apiUrlInput.value.trim();
  
  // Validate API URL if provided
  if (apiUrl && !validateApiUrl(apiUrl)) {
    showStatus('Please enter a valid URL', 'error');
    return;
  }
  
  saveSettings();
});

// Handle input changes
apiUrlInput.addEventListener('input', () => {
  // Hide any status messages when the user starts typing
  hideStatus();
}); 