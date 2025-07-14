/**
 * Common JavaScript utilities used across all pages
 */

// Common utility functions
const Utils = {
    // Show/hide loading state on buttons
    setButtonLoading: function(button, isLoading, loadingText = 'Loading...') {
        if (isLoading) {
            button.disabled = true;
            button.dataset.originalText = button.textContent;
            button.textContent = loadingText;
            button.classList.add('loading');
        } else {
            button.disabled = false;
            button.textContent = button.dataset.originalText || button.textContent;
            button.classList.remove('loading');
        }
    },

    // Format numbers with commas
    formatNumber: function(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    },

    // Show alert messages
    showAlert: function(containerId, type, title, message) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        container.innerHTML = `
            <div class="alert alert-${type}" role="alert">
                <h4 class="alert-heading">${title}</h4>
                <p>${message}</p>
            </div>
        `;
    },

    // Handle API errors consistently
    handleApiError: function(error, containerId) {
        console.error('API Error:', error);
        this.showAlert(containerId, 'danger', 'Error', 'An unexpected error occurred. Please try again.');
    }
};

// Make Utils available globally
window.Utils = Utils;
