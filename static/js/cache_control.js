/**
 * Cache Control Utility
 * 
 * This script provides functions to clear browser cache and prevent caching issues
 * by adding cache-busting parameters to AJAX requests.
 */

// Function to add cache-busting parameter to URLs
function addCacheBustParam(url) {
    // Add a timestamp parameter to prevent caching
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}_=${new Date().getTime()}`;
}

// Function to clear browser cache for specific resources
function clearResourceCache() {
    // Force reload of JavaScript and CSS files by appending a timestamp
    const scripts = document.querySelectorAll('script[src]');
    const stylesheets = document.querySelectorAll('link[rel="stylesheet"]');
    
    scripts.forEach(script => {
        if (script.src) {
            const originalSrc = script.src;
            script.src = addCacheBustParam(originalSrc);
        }
    });
    
    stylesheets.forEach(stylesheet => {
        if (stylesheet.href) {
            const originalHref = stylesheet.href;
            stylesheet.href = addCacheBustParam(originalHref);
        }
    });
}

// Function to clear all browser cache and reload the page
function clearBrowserCache() {
    // First clear the Django server cache
    fetch('/reports/clear-cache/', {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => {
        // Then reload the page with cache busting parameter
        window.location.href = addCacheBustParam(window.location.href);
    })
    .catch(error => {
        console.error('Error clearing cache:', error);
        // Still reload the page even if cache clearing fails
        window.location.href = addCacheBustParam(window.location.href);
    });
}

// Helper function to get CSRF token from cookies
function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Add cache-busting to all AJAX requests
(function() {
    // Store the original open method
    const originalOpen = XMLHttpRequest.prototype.open;
    
    // Override the open method to add cache-busting
    XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
        // Only add cache-busting for GET requests
        if (method.toLowerCase() === 'get') {
            url = addCacheBustParam(url);
        }
        
        // Call the original open method
        return originalOpen.call(this, method, url, async, user, password);
    };
})();

// Export functions for use in other scripts
window.cacheControl = {
    clearResourceCache,
    clearBrowserCache,
    addCacheBustParam
};