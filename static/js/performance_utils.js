/**
 * Performance Utilities for Benchstay
 * 
 * This script provides performance optimization utilities for the Benchstay application,
 * focusing on efficient resource loading, chart rendering, and DOM manipulation.
 */

// Namespace for performance utilities
const performanceUtils = {
    // Chart optimization utilities
    charts: {
        /**
         * Updates an existing chart instead of destroying and recreating it
         * @param {Chart} chart - The Chart.js instance to update
         * @param {Object} newData - The new data for the chart
         * @param {Object} options - Additional options for the update
         * @returns {Chart} The updated chart instance
         */
        updateChart: function(chart, newData, options = {}) {
            if (!chart) return null;
            
            // Update labels if provided
            if (newData.labels) {
                chart.data.labels = newData.labels;
            }
            
            // Update datasets
            if (newData.datasets) {
                // Match datasets by index or id
                newData.datasets.forEach((newDataset, i) => {
                    if (chart.data.datasets[i]) {
                        // Update existing dataset
                        Object.keys(newDataset).forEach(key => {
                            chart.data.datasets[i][key] = newDataset[key];
                        });
                    } else {
                        // Add new dataset
                        chart.data.datasets.push(newDataset);
                    }
                });
                
                // Remove extra datasets if needed
                if (options.removeExtra && chart.data.datasets.length > newData.datasets.length) {
                    chart.data.datasets.splice(newData.datasets.length);
                }
            }
            
            // Update options if provided
            if (options.chartOptions) {
                chart.options = { ...chart.options, ...options.chartOptions };
            }
            
            // Update the chart with animation or without based on options
            chart.update(options.animate !== false);
            
            return chart;
        },
        
        /**
         * Creates or updates a chart based on whether it already exists
         * @param {string} canvasId - The ID of the canvas element
         * @param {Object} config - The chart configuration
         * @param {string} chartVar - The variable name that holds the chart instance
         * @returns {Chart} The created or updated chart instance
         */
        createOrUpdateChart: function(canvasId, config, chartVar) {
            const ctx = document.getElementById(canvasId).getContext('2d');
            
            // If chart already exists, update it instead of recreating
            if (window[chartVar]) {
                return this.updateChart(window[chartVar], {
                    labels: config.data.labels,
                    datasets: config.data.datasets
                }, {
                    chartOptions: config.options,
                    animate: true
                });
            } else {
                // Create new chart
                window[chartVar] = new Chart(ctx, config);
                return window[chartVar];
            }
        }
    },
    
    // Resource loading optimization
    resources: {
        /**
         * Lazy loads JavaScript files
         * @param {string} src - The source URL of the script
         * @param {Function} callback - Optional callback function to execute when script is loaded
         * @param {boolean} async - Whether to load the script asynchronously
         */
        lazyLoadScript: function(src, callback, async = true) {
            const script = document.createElement('script');
            script.src = src;
            script.async = async;
            
            if (callback && typeof callback === 'function') {
                script.onload = callback;
            }
            
            document.body.appendChild(script);
        },
        
        /**
         * Lazy loads CSS files
         * @param {string} href - The href URL of the stylesheet
         * @param {Function} callback - Optional callback function to execute when stylesheet is loaded
         */
        lazyLoadCSS: function(href, callback) {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = href;
            
            if (callback && typeof callback === 'function') {
                link.onload = callback;
            }
            
            document.head.appendChild(link);
        },
        
        /**
         * Preloads resources for better performance
         * @param {Array} resources - Array of resource objects with type and url properties
         */
        preloadResources: function(resources) {
            resources.forEach(resource => {
                const link = document.createElement('link');
                link.rel = 'preload';
                link.href = resource.url;
                link.as = resource.type; // 'script', 'style', 'image', etc.
                
                if (resource.crossorigin) {
                    link.crossOrigin = resource.crossorigin;
                }
                
                document.head.appendChild(link);
            });
        }
    },
    
    // DOM optimization
    dom: {
        /**
         * Efficiently updates a table with new data using document fragments
         * @param {string} tableId - The ID of the table element
         * @param {Array} data - Array of data objects
         * @param {Function} rowRenderer - Function that returns HTML for a row
         */
        updateTableEfficiently: function(tableId, data, rowRenderer) {
            const table = document.getElementById(tableId);
            if (!table) return;
            
            const tbody = table.querySelector('tbody');
            const fragment = document.createDocumentFragment();
            
            // Create all rows in the fragment (off-DOM)
            data.forEach(item => {
                const row = document.createElement('tr');
                row.innerHTML = rowRenderer(item);
                fragment.appendChild(row);
            });
            
            // Clear the tbody and append the fragment (single DOM operation)
            tbody.innerHTML = '';
            tbody.appendChild(fragment);
        },
        
        /**
         * Throttles a function to limit how often it can be called
         * @param {Function} func - The function to throttle
         * @param {number} limit - The time limit in milliseconds
         * @returns {Function} The throttled function
         */
        throttle: function(func, limit) {
            let inThrottle;
            return function() {
                const args = arguments;
                const context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        },
        
        /**
         * Debounces a function to delay its execution until after a wait period
         * @param {Function} func - The function to debounce
         * @param {number} wait - The wait time in milliseconds
         * @returns {Function} The debounced function
         */
        debounce: function(func, wait) {
            let timeout;
            return function() {
                const context = this;
                const args = arguments;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), wait);
            };
        }
    }
};

// Export the utilities for use in other scripts
window.performanceUtils = performanceUtils;