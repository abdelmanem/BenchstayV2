// RevPAR Matrix Chart Functionality

let revparChart; // Global variable to store the chart instance for current period
let revparChartPrevYear; // Global variable to store the chart instance for previous year
let currentMonth;
let currentYear;
let currentView = 'month'; // 'month' or '3month'

// Initialize the chart when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Set default values to current month and year
    const today = new Date();
    currentMonth = today.getMonth() + 1; // JavaScript months are 0-indexed
    currentYear = today.getFullYear();
    
    // Update dropdown buttons to show current month and year
    document.getElementById('monthFilterDropdown').textContent = getMonthName(currentMonth);
    document.getElementById('yearFilterDropdown').textContent = currentYear;
    
    // Initialize the charts with current month data
    initializeCharts();
    
    // Set up event listeners for the filter buttons
    setupEventListeners();
});

// Initialize both RevPAR matrix charts
function initializeCharts() {
    // Initialize current period chart
    initializeChart('revparMatrix', 'current');
    
    // Initialize previous year chart if the element exists
    const prevYearCanvas = document.getElementById('revparMatrixPrevYear');
    if (prevYearCanvas) {
        initializeChart('revparMatrixPrevYear', 'prevYear');
    }
}

// Initialize a single RevPAR matrix chart
function initializeChart(canvasId, chartType) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return; // Skip if canvas doesn't exist
    
    const ctx = canvas.getContext('2d');
    
    // Determine which chart instance to use
    let chartInstance = chartType === 'current' ? revparChart : revparChartPrevYear;
    
    // If chart already exists, destroy it first
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    // Get initial data from data attributes
    const hotelOccIndex = parseFloat(canvas.dataset.hotelOccIndex) || 100;
    const hotelAdrIndex = parseFloat(canvas.dataset.hotelAdrIndex) || 100;
    const competitorData = JSON.parse(canvas.dataset.competitorData || '[]');
    
    // Create the chart with initial data
    const newChart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Your Hotel',
                data: [{
                    x: hotelOccIndex,
                    y: hotelAdrIndex
                }],
                backgroundColor: 'rgba(255, 99, 132, 1)',
                borderColor: 'rgba(255, 99, 132, 1)',
                pointRadius: 8
            },
            {
                label: 'Competitors',
                data: competitorData,
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgba(54, 162, 235, 1)',
                pointRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Occupancy Index'
                    },
                    suggestedMin: 60,
                    suggestedMax: 140
                },
                y: {
                    title: {
                        display: true,
                        text: 'ADR Index'
                    },
                    suggestedMin: 60,
                    suggestedMax: 140
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: chartType === 'current' ? 'Current Period' : 'Previous Year',
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const name = context.raw.name || '';
                            return (name ? name : label) + ': (' +
                                context.parsed.x.toFixed(1) + ', ' +
                                context.parsed.y.toFixed(1) + ')';
                        }
                    }
                }
            }
        }
    });
    
    // Store the chart instance in the appropriate variable
    if (chartType === 'current') {
        revparChart = newChart;
    } else {
        revparChartPrevYear = newChart;
    }
    
    return newChart;
}

// Set up event listeners for all filter buttons and dropdowns
function setupEventListeners() {
    // Month dropdown event listeners
    document.querySelectorAll('#monthDropdown .dropdown-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const month = parseInt(this.dataset.month);
            currentMonth = month;
            document.getElementById('monthFilterDropdown').textContent = getMonthName(month);
            fetchAndUpdateChart();
        });
    });
    
    // Year dropdown event listeners
    document.querySelectorAll('#yearDropdown .dropdown-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const year = parseInt(this.dataset.year);
            currentYear = year;
            document.getElementById('yearFilterDropdown').textContent = year;
            fetchAndUpdateChart();
        });
    });
    
    // Current Month button event listener
    document.getElementById('currentMonthBtn').addEventListener('click', function() {
        currentView = 'month';
        // Toggle active class
        document.getElementById('threeMonthBtn').classList.remove('active');
        this.classList.add('active');
        fetchAndUpdateChart();
    });
    
    // 3 Month Average button event listener
    document.getElementById('threeMonthBtn').addEventListener('click', function() {
        currentView = '3month';
        // Toggle active class
        document.getElementById('currentMonthBtn').classList.remove('active');
        this.classList.add('active');
        fetchAndUpdateChart();
    });
}

// Fetch data for the selected month/year and update both charts
function fetchAndUpdateChart() {
    // Show loading indicators
    const currentChartContainer = document.getElementById('revparMatrix').parentNode;
    currentChartContainer.classList.add('loading');
    
    // Check if previous year chart exists
    const prevYearCanvas = document.getElementById('revparMatrixPrevYear');
    const prevYearChartContainer = prevYearCanvas ? prevYearCanvas.parentNode : null;
    if (prevYearChartContainer) {
        prevYearChartContainer.classList.add('loading');
    }
    
    // Calculate date range based on selected month and year for current period
    let startDate, endDate;
    
    if (currentView === 'month') {
        // First day to last day of selected month
        startDate = new Date(currentYear, currentMonth - 1, 1);
        endDate = new Date(currentYear, currentMonth, 0); // Last day of month
    } else {
        // 3 month average (current month and 2 previous months)
        endDate = new Date(currentYear, currentMonth, 0); // Last day of current month
        startDate = new Date(currentYear, currentMonth - 3, 1); // First day of 3 months ago
    }
    
    // Calculate date range for previous year (same period)
    const prevYearStartDate = new Date(startDate);
    prevYearStartDate.setFullYear(prevYearStartDate.getFullYear() - 1);
    
    const prevYearEndDate = new Date(endDate);
    prevYearEndDate.setFullYear(prevYearEndDate.getFullYear() - 1);
    
    // Format dates for API requests
    const formattedStartDate = formatDate(startDate);
    const formattedEndDate = formatDate(endDate);
    const formattedPrevYearStartDate = formatDate(prevYearStartDate);
    const formattedPrevYearEndDate = formatDate(prevYearEndDate);
    
    // Make AJAX request for current period data
    const currentPeriodPromise = fetch(`/hotel_management/api/revpar-matrix/?start_date=${formattedStartDate}&end_date=${formattedEndDate}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        });
    
    // Make AJAX request for previous year data
    const prevYearPromise = fetch(`/hotel_management/api/revpar-matrix/?start_date=${formattedPrevYearStartDate}&end_date=${formattedPrevYearEndDate}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        });
    
    // Wait for both requests to complete
    Promise.all([currentPeriodPromise, prevYearPromise])
        .then(([currentData, prevYearData]) => {
            // Update current period chart
            updateChartData(currentData, 'current');
            // Update previous year chart
            updateChartData(prevYearData, 'prevYear');
            
            // Hide loading indicators
            currentChartContainer.classList.remove('loading');
            if (prevYearChartContainer) {
                prevYearChartContainer.classList.remove('loading');
            }
            
            // Update date range displays
            const currentPeriodDateRange = document.getElementById('currentPeriodDateRange');
            if (currentPeriodDateRange) {
                currentPeriodDateRange.textContent = 
                    `${formatDisplayDate(currentData.start_date)} - ${formatDisplayDate(currentData.end_date)}`;
            }
            
            const prevYearDateRange = document.getElementById('prevYearDateRange');
            if (prevYearDateRange) {
                prevYearDateRange.textContent = 
                    `${formatDisplayDate(prevYearData.start_date)} - ${formatDisplayDate(prevYearData.end_date)}`;
            }
        })
        .catch(error => {
            console.error('Error fetching data:', error);
            // Hide loading indicators
            currentChartContainer.classList.remove('loading');
            if (prevYearChartContainer) {
                prevYearChartContainer.classList.remove('loading');
            }
            // Show error message
            alert('Error loading data. Please try again.');
        });
}

// Update a chart with new data
function updateChartData(data, chartType) {
    // Determine which chart to update
    const chart = chartType === 'current' ? revparChart : revparChartPrevYear;
    
    if (!chart) return;
    
    // Update hotel data point
    chart.data.datasets[0].data = [{
        x: data.hotel_data.occupancy_index,

// Helper function to get month name from month number
function getMonthName(monthNumber) {
    const months = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];
    return months[monthNumber - 1];
}

// Helper function to format date for API request (YYYY-MM-DD)
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Helper function to format date for display (Month DD, YYYY)
function formatDisplayDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
}