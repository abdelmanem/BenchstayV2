// Competitor Data Visualization JavaScript

// Cache DOM elements
let dailyChart, mtdChart, ytdChart, comparisonChart, mpiComparisonChart, ariComparisonChart, rgiComparisonChart;
let currentMetric = 'occupancy_percentage';
let currentChartType = 'bar';
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
        // Get currency symbol from the data attribute we'll add to the page
        const currencySymbol = document.getElementById('currency-symbol-data').dataset.symbol;
        return currencySymbol + value.toFixed(2);
    } else {
        return value.toFixed(2);
    }
}

// Generate colors for chart datasets
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

// Create chart for a specific period
function createChart(canvasId, data, period) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    const hotelNames = Object.keys(data);
    const metricValues = hotelNames.map(hotel => data[hotel][currentMetric]);
    const colors = generateColors(hotelNames.length);
    
    // Highlight the user's hotel
    const userHotelName = document.querySelector('.metrics-summary').getAttribute('data-hotel-name');
    const backgroundColors = colors.map((color, index) => {
        return hotelNames[index] === userHotelName ? color.replace('0.7', '0.9') : color;
    });
    
    // Destroy existing chart if it exists
    if (window[period + 'Chart']) {
        window[period + 'Chart'].destroy();
    }
    
    // Create new chart
    window[period + 'Chart'] = new Chart(ctx, {
        type: currentChartType,
        data: {
            labels: hotelNames,
            datasets: [{
                label: metricLabels[currentMetric],
                data: metricValues,
                backgroundColor: currentChartType === 'bar' ? backgroundColors : 'rgba(0, 0, 0, 0)',
                borderColor: backgroundColors.map(color => color.replace('0.7', '1')),
                borderWidth: 1,
                tension: 0.1,
                fill: currentChartType === 'line' ? false : true
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
            backgroundColor: currentChartType === 'bar' ? 'rgba(255, 193, 7, 0.7)' : 'rgba(0, 0, 0, 0)',
            borderColor: 'rgba(255, 193, 7, 1)',
            borderWidth: 1,
            tension: 0.1,
            fill: currentChartType === 'line' ? false : true
        },
        {
            label: 'MTD',
            data: hotelNames.map(hotel => mtdData[hotel][currentMetric]),
            backgroundColor: currentChartType === 'bar' ? 'rgba(25, 135, 84, 0.7)' : 'rgba(0, 0, 0, 0)',
            borderColor: 'rgba(25, 135, 84, 1)',
            borderWidth: 1,
            tension: 0.1,
            fill: currentChartType === 'line' ? false : true
        },
        {
            label: 'YTD',
            data: hotelNames.map(hotel => ytdData[hotel][currentMetric]),
            backgroundColor: currentChartType === 'bar' ? 'rgba(13, 110, 253, 0.7)' : 'rgba(0, 0, 0, 0)',
            borderColor: 'rgba(13, 110, 253, 1)',
            borderWidth: 1,
            tension: 0.1,
            fill: currentChartType === 'line' ? false : true
        }
    ];
    
    // Destroy existing chart if it exists
    if (comparisonChart) {
        comparisonChart.destroy();
    }
    
    // Create new chart
    comparisonChart = new Chart(ctx, {
        type: currentChartType,
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

// Create index comparison charts
function createIndexComparisonCharts() {
    const dailyData = JSON.parse(document.getElementById('daily-data').textContent);
    const mtdData = JSON.parse(document.getElementById('mtd-data').textContent);
    const ytdData = JSON.parse(document.getElementById('ytd-data').textContent);
    
    // Get hotel names
    const hotelNames = Object.keys(dailyData);
    
    // Create MPI comparison chart
    createIndexChart('mpi-comparison-chart', 'mpi', hotelNames, dailyData, mtdData, ytdData);
    
    // Create ARI comparison chart
    createIndexChart('ari-comparison-chart', 'ari', hotelNames, dailyData, mtdData, ytdData);
    
    // Create RGI comparison chart
    createIndexChart('rgi-comparison-chart', 'rgi', hotelNames, dailyData, mtdData, ytdData);
}

// Create index chart
function createIndexChart(canvasId, indexType, hotelNames, dailyData, mtdData, ytdData) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Prepare datasets
    const datasets = [
        {
            label: 'Custom Date Range',
            data: hotelNames.map(hotel => dailyData[hotel][indexType]),
            backgroundColor: currentChartType === 'bar' ? 'rgba(255, 193, 7, 0.7)' : 'rgba(0, 0, 0, 0)',
            borderColor: 'rgba(255, 193, 7, 1)',
            borderWidth: 1,
            tension: 0.1,
            fill: currentChartType === 'line' ? false : true
        },
        {
            label: 'MTD',
            data: hotelNames.map(hotel => mtdData[hotel][indexType]),
            backgroundColor: currentChartType === 'bar' ? 'rgba(25, 135, 84, 0.7)' : 'rgba(0, 0, 0, 0)',
            borderColor: 'rgba(25, 135, 84, 1)',
            borderWidth: 1,
            tension: 0.1,
            fill: currentChartType === 'line' ? false : true
        },
        {
            label: 'YTD',
            data: hotelNames.map(hotel => ytdData[hotel][indexType]),
            backgroundColor: currentChartType === 'bar' ? 'rgba(13, 110, 253, 0.7)' : 'rgba(0, 0, 0, 0)',
            borderColor: 'rgba(13, 110, 253, 1)',
            borderWidth: 1,
            tension: 0.1,
            fill: currentChartType === 'line' ? false : true
        }
    ];
    
    // Destroy existing chart if it exists
    if (window[indexType + 'ComparisonChart']) {
        window[indexType + 'ComparisonChart'].destroy();
    }
    
    // Create new chart
    window[indexType + 'ComparisonChart'] = new Chart(ctx, {
        type: currentChartType,
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
                            return context.dataset.label + ': ' + formatValue(context.parsed.y, indexType);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatValue(value, indexType);
                        }
                    }
                }
            }
        }
    });
    
    return window[indexType + 'ComparisonChart'];
}

// Update summary metrics
function updateSummaryMetrics() {
    const dailyData = JSON.parse(document.getElementById('daily-data').textContent);
    const mtdData = JSON.parse(document.getElementById('mtd-data').textContent);
    const ytdData = JSON.parse(document.getElementById('ytd-data').textContent);
    
    // Get user's hotel name
    const userHotelName = document.querySelector('.metrics-summary').getAttribute('data-hotel-name');
    
    // Update occupancy
    document.getElementById('summary-occupancy').textContent = formatValue(dailyData[userHotelName].occupancy_percentage, 'occupancy_percentage');
    
    // Update average rate
    document.getElementById('summary-rate').textContent = formatValue(dailyData[userHotelName].average_rate, 'average_rate');
    
    // Update RevPAR
    document.getElementById('summary-revpar').textContent = formatValue(dailyData[userHotelName].revpar, 'revpar');
    
    // Update MPI
    document.getElementById('summary-mpi').textContent = formatValue(dailyData[userHotelName].mpi, 'mpi');
    
    // Add trend indicators
    addTrendIndicator('trend-occupancy', dailyData[userHotelName].occupancy_percentage, mtdData[userHotelName].occupancy_percentage);
    addTrendIndicator('trend-rate', dailyData[userHotelName].average_rate, mtdData[userHotelName].average_rate);
    addTrendIndicator('trend-revpar', dailyData[userHotelName].revpar, mtdData[userHotelName].revpar);
    addTrendIndicator('trend-mpi', dailyData[userHotelName].mpi, mtdData[userHotelName].mpi);
}

// Add trend indicator
function addTrendIndicator(elementId, currentValue, previousValue) {
    const element = document.getElementById(elementId);
    const difference = currentValue - previousValue;
    const percentChange = previousValue !== 0 ? (difference / previousValue) * 100 : 0;
    
    let indicator = '';
    if (difference > 0) {
        indicator = `<span class="text-success"><i class="fas fa-arrow-up"></i> <span class="ms-1">+${Math.abs(percentChange).toFixed(1)}% vs last period</span></span>`;
    } else if (difference < 0) {
        indicator = `<span class="text-danger"><i class="fas fa-arrow-down"></i> <span class="ms-1">-${Math.abs(percentChange).toFixed(1)}% vs last period</span></span>`;
    } else {
        indicator = `<span class="text-secondary"><i class="fas fa-minus"></i> <span class="ms-1">0.0% vs last period</span></span>`;
    }
    
    element.innerHTML = indicator;