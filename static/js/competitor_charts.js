// Competitor Charts JavaScript

// Cache DOM elements
let dailyChart, mtdChart, ytdChart, comparisonChart;
let currentMetric = 'occupancy_percentage';
let metricLabels = {
    'occupancy_percentage': 'Occupancy %',
    'average_rate': 'Average Rate',
    'revpar': 'RevPAR',
    'mpi': 'Market Penetration Index',
    'ari': 'Average Rate Index',
    'rgi': 'Revenue Generation Index'
};

// Format values based on metric type
function formatValue(value, metric) {
    if (metric === 'occupancy_percentage') {
        return value.toFixed(2) + '%';
    } else if (metric === 'average_rate' || metric === 'revpar') {
        return 'EGP' + value.toFixed(2);
    } else {
        return value.toFixed(2);
    }
}

// Generate random colors for chart datasets
function generateColors(count) {
    const colors = [];
    const baseColors = [
        'rgba(255, 99, 132, 0.7)',   // Red
        'rgba(54, 162, 235, 0.7)',   // Blue
        'rgba(255, 206, 86, 0.7)',   // Yellow
        'rgba(75, 192, 192, 0.7)',   // Green
        'rgba(153, 102, 255, 0.7)',  // Purple
        'rgba(255, 159, 64, 0.7)',   // Orange
        'rgba(199, 199, 199, 0.7)',  // Gray
        'rgba(83, 102, 255, 0.7)',   // Indigo
        'rgba(255, 99, 255, 0.7)',   // Pink
        'rgba(0, 162, 152, 0.7)'     // Teal
    ];
    
    for (let i = 0; i < count; i++) {
        colors.push(baseColors[i % baseColors.length]);
    }
    
    return colors;
}

// Create bar chart for a specific period
function createBarChart(canvasId, data, period) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    const hotelNames = Object.keys(data);
    const metricValues = hotelNames.map(hotel => data[hotel][currentMetric]);
    const colors = generateColors(hotelNames.length);
    
    // Destroy existing chart if it exists
    if (window[period + 'Chart']) {
        window[period + 'Chart'].destroy();
    }
    
    // Create new chart
    window[period + 'Chart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hotelNames,
            datasets: [{
                label: metricLabels[currentMetric],
                data: metricValues,
                backgroundColor: colors,
                borderColor: colors.map(color => color.replace('0.7', '1')),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return formatValue(context.parsed.y, currentMetric);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatValue(value, currentMetric);
                        }
                    }
                }
            }
        }
    });
    
    return window[period + 'Chart'];
}

// Create comparison chart for all periods
function createComparisonChart() {
    const ctx = document.getElementById('comparison-chart').getContext('2d');
    const dailyData = JSON.parse(document.getElementById('daily-data').textContent);
    const mtdData = JSON.parse(document.getElementById('mtd-data').textContent);
    const ytdData = JSON.parse(document.getElementById('ytd-data').textContent);
    
    // Get hotel names (should be the same across all periods)
    const hotelNames = Object.keys(dailyData);
    
    // Prepare datasets
    const datasets = [
        {
            label: 'Custom Date Range',
            data: hotelNames.map(hotel => dailyData[hotel][currentMetric]),
            backgroundColor: 'rgba(255, 193, 7, 0.7)',
            borderColor: 'rgba(255, 193, 7, 1)',
            borderWidth: 1
        },
        {
            label: 'MTD',
            data: hotelNames.map(hotel => mtdData[hotel][currentMetric]),
            backgroundColor: 'rgba(25, 135, 84, 0.7)',
            borderColor: 'rgba(25, 135, 84, 1)',
            borderWidth: 1
        },
        {
            label: 'YTD',
            data: hotelNames.map(hotel => ytdData[hotel][currentMetric]),
            backgroundColor: 'rgba(13, 110, 253, 0.7)',
            borderColor: 'rgba(13, 110, 253, 1)',
            borderWidth: 1
        }
    ];
    
    // Destroy existing chart if it exists
    if (comparisonChart) {
        comparisonChart.destroy();
    }
    
    // Create new chart
    comparisonChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hotelNames,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + formatValue(context.parsed.y, currentMetric);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatValue(value, currentMetric);
                        }
                    }
                }
            }
        }
    });
    
    return comparisonChart;
}

// Update all charts with the selected metric
function updateCharts() {
    const dailyData = JSON.parse(document.getElementById('daily-data').textContent);
    const mtdData = JSON.parse(document.getElementById('mtd-data').textContent);
    const ytdData = JSON.parse(document.getElementById('ytd-data').textContent);
    
    // Update individual period charts
    createBarChart('daily-chart', dailyData, 'daily');
    createBarChart('mtd-chart', mtdData, 'mtd');
    createBarChart('ytd-chart', ytdData, 'ytd');
    
    // Update comparison chart
    createComparisonChart();
}

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Parse data from JSON elements
    const dailyData = JSON.parse(document.getElementById('daily-data').textContent);
    const mtdData = JSON.parse(document.getElementById('mtd-data').textContent);
    const ytdData = JSON.parse(document.getElementById('ytd-data').textContent);
    
    // Create initial charts
    createBarChart('daily-chart', dailyData, 'daily');
    createBarChart('mtd-chart', mtdData, 'mtd');
    createBarChart('ytd-chart', ytdData, 'ytd');
    createComparisonChart();
    
    // Add event listeners to metric selector buttons
    const metricButtons = document.querySelectorAll('.metric-selector .btn');
    metricButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Update active button
            metricButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            // Update current metric
            currentMetric = this.getAttribute('data-metric');
            
            // Update charts
            updateCharts();
        });
    });
    
    // Handle form submission
    const dateFilterForm = document.getElementById('date-filter-form');
    if (dateFilterForm) {
        dateFilterForm.addEventListener('submit', function(e) {
            // Form will be submitted normally, no need to prevent default
            // The page will reload with new data
        });
    }
});