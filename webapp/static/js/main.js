/**
 * Main JavaScript for Meme Generator
 */

document.addEventListener('DOMContentLoaded', function() {
    // Handle image preview
    const imageInputs = document.querySelectorAll('input[type="file"]');
    
    imageInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            
            // Check if file exists and is an image
            if (file && file.type.match('image.*')) {
                // Find closest form container to add preview to
                const formGroup = this.closest('.mb-3');
                
                // Remove any existing preview
                const existingPreview = formGroup.querySelector('.image-preview');
                if (existingPreview) {
                    existingPreview.remove();
                }
                
                // Create preview image
                const reader = new FileReader();
                reader.onload = function(e) {
                    const preview = document.createElement('img');
                    preview.src = e.target.result;
                    preview.className = 'image-preview';
                    preview.alt = 'Preview';
                    
                    formGroup.appendChild(preview);
                }
                reader.readAsDataURL(file);
            }
        });
    });
    
    // Scroll chat to bottom
    const chatContainer = document.getElementById('chatContainer');
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        // Auto-scroll when new messages appear
        const observer = new MutationObserver(() => {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        });
        
        observer.observe(chatContainer, { 
            childList: true,
            subtree: true 
        });
    }
    
    // Confirm clear chat
    const clearChatForm = document.querySelector('form[action*="clear-chat"]');
    if (clearChatForm) {
        clearChatForm.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to clear the chat history?')) {
                e.preventDefault();
            }
        });
    }
    
    // Form validation feedback
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Clear previously generated meme on page load
    clearPreviousMeme();
    
    // Add submit handler to meme generation form
    const memeForm = document.querySelector('form');
    if (memeForm) {
        memeForm.addEventListener('submit', function(e) {
            // Show loading spinner
            showLoadingSpinner();
        });
    }
});

// Function to clear previously generated meme
function clearPreviousMeme() {
    // Check if we're on a new page load (not form submission)
    if (document.referrer !== document.location.href) {
        // Hide the meme section if it exists
        const memeSection = document.querySelector('.card:has(img[src^="/data/"])');
        if (memeSection) {
            memeSection.style.display = 'none';
        }
    }
}

// Function to show loading spinner
function showLoadingSpinner() {
    // Create loading element if it doesn't exist
    let loadingEl = document.getElementById('loading-spinner');
    if (!loadingEl) {
        loadingEl = document.createElement('div');
        loadingEl.id = 'loading-spinner';
        loadingEl.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
        loadingEl.style.backgroundColor = 'rgba(0,0,0,0.5)';
        loadingEl.style.zIndex = '9999';
        
        const spinner = document.createElement('div');
        spinner.className = 'spinner-border text-light';
        spinner.style.width = '3rem';
        spinner.style.height = '3rem';
        spinner.setAttribute('role', 'status');
        
        const loadingText = document.createElement('span');
        loadingText.className = 'ms-3 text-light';
        loadingText.textContent = 'Generating Meme...';
        
        const spinnerContainer = document.createElement('div');
        spinnerContainer.className = 'd-flex flex-column align-items-center';
        spinnerContainer.appendChild(spinner);
        spinnerContainer.appendChild(loadingText);
        
        loadingEl.appendChild(spinnerContainer);
        document.body.appendChild(loadingEl);
    } else {
        loadingEl.style.display = 'flex';
    }
} 