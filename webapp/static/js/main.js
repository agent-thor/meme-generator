/**
 * Main JavaScript for MemeZap
 */

document.addEventListener('DOMContentLoaded', function() {
    // Theme toggle functionality
    const themeToggleBtn = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;
    const themeIcon = themeToggleBtn.querySelector('i');
    
    // Function to update theme icon
    function updateThemeIcon(isDark) {
        if (isDark) {
            themeIcon.classList.remove('fa-sun');
            themeIcon.classList.add('fa-moon');
        } else {
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
        }
    }
    
    // Initialize theme based on saved preference or system preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        htmlElement.setAttribute('data-bs-theme', savedTheme);
        updateThemeIcon(savedTheme === 'dark');
    } else {
        // Check system preference
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        htmlElement.setAttribute('data-bs-theme', systemPrefersDark ? 'dark' : 'light');
        updateThemeIcon(systemPrefersDark);
    }
    
    // Toggle theme on button click
    themeToggleBtn.addEventListener('click', function() {
        const currentTheme = htmlElement.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        htmlElement.setAttribute('data-bs-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme === 'dark');
    });
    
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
    
    // Enhance meme source indicators
    const templateIndicators = document.querySelectorAll('.template-indicator');
    templateIndicators.forEach(indicator => {
        // Add animation effect
        indicator.style.opacity = '0.85';
        
        // Add hover effect
        indicator.addEventListener('mouseenter', function() {
            this.style.opacity = '1';
        });
        
        indicator.addEventListener('mouseleave', function() {
            this.style.opacity = '0.85';
        });
        
        // Add icon based on source
        if (indicator.classList.contains('from-template')) {
            // Make sure it shows the correct class
            indicator.classList.remove('no-template');
            indicator.classList.add('from-template');
            
            if (!indicator.querySelector('.fas.fa-check-circle')) {
                const icon = document.createElement('i');
                icon.className = 'fas fa-check-circle me-1';
                indicator.prepend(icon);
            }
        } else if (indicator.classList.contains('no-template')) {
            // Make sure it shows the correct class
            indicator.classList.remove('from-template');
            indicator.classList.add('no-template');
            
            if (!indicator.querySelector('.fas.fa-image')) {
                const icon = document.createElement('i');
                icon.className = 'fas fa-image me-1';
                indicator.prepend(icon);
            }
        }
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
    
    // Enhance meme result cards
    const memeResultDiv = document.getElementById('meme-result');
    if (memeResultDiv) {
        const memeImg = memeResultDiv.querySelector('img');
        if (memeImg) {
            // Add click to enlarge functionality
            memeImg.style.cursor = 'pointer';
            memeImg.addEventListener('click', function() {
                const modal = document.createElement('div');
                modal.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
                modal.style.backgroundColor = 'rgba(0,0,0,0.85)';
                modal.style.zIndex = '9999';
                
                const modalImg = document.createElement('img');
                modalImg.src = this.src;
                modalImg.className = 'img-fluid';
                modalImg.style.maxHeight = '90vh';
                modalImg.style.maxWidth = '90vw';
                modalImg.style.objectFit = 'contain';
                modalImg.style.boxShadow = '0 0 20px rgba(0,0,0,0.5)';
                
                modal.appendChild(modalImg);
                document.body.appendChild(modal);
                
                // Close on click
                modal.addEventListener('click', function() {
                    this.remove();
                });
            });
        }
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
        
        const spinnerContainer = document.createElement('div');
        spinnerContainer.className = 'd-flex flex-column align-items-center';
        
        const spinner = document.createElement('div');
        spinner.className = 'spinner-border text-light';
        spinner.style.width = '3rem';
        spinner.style.height = '3rem';
        spinner.setAttribute('role', 'status');
        
        const loadingText = document.createElement('span');
        loadingText.className = 'ms-3 text-light mt-3';
        loadingText.textContent = 'Generating Meme...';
        
        spinnerContainer.appendChild(spinner);
        spinnerContainer.appendChild(loadingText);
        
        loadingEl.appendChild(spinnerContainer);
        document.body.appendChild(loadingEl);
    } else {
        loadingEl.style.display = 'flex';
    }
} 