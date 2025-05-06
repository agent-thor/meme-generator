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
}); 