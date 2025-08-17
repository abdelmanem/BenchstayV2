/**
 * Optimized Cache Control Utility
 * 
 * This script provides improved caching mechanisms for Benchstay application
 * with more efficient cache-busting and resource management.
 */

// Cache control namespace
const optimizedCacheControl = {
    // Cache version - increment when making significant changes to resources
    version: '1.0',
    
    /**
     * Add cache-busting parameter to URLs using a consistent version identifier
     * instead of random timestamps to improve caching behavior
     * @param {string} url - The URL to add cache-busting parameter to
     * @returns {string} URL with cache-busting parameter
     */
    addCacheBustParam: function(url) {
        if (!url) return url;
        
        // Remove any existing cache-busting parameter
        let cleanUrl = url.replace(/([?&])_=\d+(&|$)/, '$1');
        cleanUrl = cleanUrl.replace(/[?&]$/,'');
        
        // Add version-based cache-busting parameter
        const separator = cleanUrl.includes('?') ? '&' : '?';
        return `${cleanUrl}${separator}_v=${this.version}`;
    },
    
    /**
     * Selectively refresh resources without full page reload
     * @param {Array} resourceTypes - Types of resources to refresh ('scripts', 'styles', or 'both')
     */
    refreshResources: function(resourceTypes = 'both') {
        const refreshScripts = resourceTypes === 'scripts' || resourceTypes === 'both';
        const refreshStyles = resourceTypes === 'styles' || resourceTypes === 'both';
        
        if (refreshScripts) {
            const scripts = document.querySelectorAll('script[src]');
            scripts.forEach(script => {
                if (script.src && !script.src.includes('cdn.jsdelivr.net') && !script.src.includes('bootstrap')) {
                    const originalSrc = script.getAttribute('src');
                    const newScript = document.createElement('script');
                    
                    // Copy all attributes from the original script
                    Array.from(script.attributes).forEach(attr => {
                        if (attr.name !== 'src') {
                            newScript.setAttribute(attr.name, attr.value);
                        }
                    });
                    
                    // Set the new src with cache-busting
                    newScript.src = this.addCacheBustParam(originalSrc);
                    
                    // Replace the old script with the new one
                    script.parentNode.replaceChild(newScript, script);
                }
            });
        }
        
        if (refreshStyles) {
            const stylesheets = document.querySelectorAll('link[rel="stylesheet"]');
            stylesheets.forEach(stylesheet => {
                if (stylesheet.href && !stylesheet.href.includes('cdn.jsdelivr.net') && !stylesheet.href.includes('bootstrap')) {
                    const originalHref = stylesheet.getAttribute('href');
                    stylesheet.href = this.addCacheBustParam(originalHref);
                }
            });
        }
    },
    
    /**
     * Clear server-side cache and refresh client resources
     * @param {Function} callback - Optional callback function to execute after clearing cache
     */
    clearServerCache: function(callback) {
        fetch('/reports/clear-cache/', {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Refresh resources instead of reloading the page
                this.refreshResources();
                
                if (callback && typeof callback === 'function') {
                    callback(true);
                }
            } else {
                console.error('Error clearing server cache:', data.message);
                if (callback && typeof callback === 'function') {
                    callback(false);
                }
            }
        })
        .catch(error => {
            console.error('Error clearing cache:', error);
            if (callback && typeof callback === 'function') {
                callback(false);
            }
        });
    },
    
    /**
     * Get CSRF token from cookies
     * @returns {string} CSRF token
     */
    getCsrfToken: function() {
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
    },
    
    /**
     * Optimize AJAX requests by adding consistent cache-busting
     * and implementing request deduplication
     */
    setupAjaxOptimization: function() {
        // Store pending requests to prevent duplicates
        const pendingRequests = {};
        
        // Store the original open method
        const originalOpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;
        const self = this;
        
        // Override the open method to add cache-busting
        XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
            // Only add cache-busting for GET requests
            if (method.toLowerCase() === 'get') {
                this._optimizedUrl = self.addCacheBustParam(url);
            } else {
                this._optimizedUrl = url;
            }
            
            // Call the original open method
            return originalOpen.call(this, method, this._optimizedUrl, async, user, password);
        };
        
        // Override the send method to implement request deduplication
        XMLHttpRequest.prototype.send = function(data) {
            const method = this._method || 'GET';
            const requestKey = `${method}:${this._optimizedUrl}`;
            
            // For GET requests, check if there's already a pending identical request
            if (method.toLowerCase() === 'get' && pendingRequests[requestKey]) {
                // Cancel this request and wait for the pending one
                const pendingXhr = pendingRequests[requestKey];
                
                // Copy the response from the pending request when it completes
                const originalOnLoad = pendingXhr.onload;
                pendingXhr.onload = function() {
                    if (originalOnLoad) {
                        originalOnLoad.apply(this, arguments);
                    }
                    
                    // Simulate this request completing with the same response
                    if (this.readyState === 4) {
                        // Copy response properties
                        ['response', 'responseText', 'responseXML', 'status', 'statusText'].forEach(prop => {
                            Object.defineProperty(this, prop, {
                                get: function() { return pendingXhr[prop]; }
                            });
                        });
                        
                        // Trigger load event
                        if (this.onload) {
                            this.onload();
                        }
                    }
                }.bind(this);
                
                return;
            }
            
            // Store this request as pending
            pendingRequests[requestKey] = this;
            
            // Remove from pending when complete
            this.addEventListener('loadend', function() {
                delete pendingRequests[requestKey];
            });
            
            // Call the original send method
            return originalSend.call(this, data);
        };
    }
};

// Initialize AJAX optimization
optimizedCacheControl.setupAjaxOptimization();

// Export for use in other scripts
window.optimizedCacheControl = optimizedCacheControl;