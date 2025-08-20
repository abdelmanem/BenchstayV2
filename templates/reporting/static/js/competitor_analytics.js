// Cache DOM elements
const dateRangeSelect = document.getElementById('date_range');
const customDateFields = document.querySelectorAll('.custom-date-range');
const analyticsForm = document.querySelector('form');
const ytdChart = document.getElementById('ytdAnalyticsChart');
const dailyChart = document.getElementById('dailyAnalyticsChart');

// Handle date range selection
dateRangeSelect.addEventListener('change', function() {
    if (this.value === 'custom') {
        customDateFields.forEach(field => field.style.display = 'block');
    } else {
        customDateFields.forEach(field => field.style.display = 'none');
    }
});

// Handle form submission
analyticsForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    
    try {
        const response = await fetch(window.location.href, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();
        updateCharts(data);
        updateTables(data);
    } catch (error) {
        console.error('Error:', error);
    }
});

// Update charts with new data
function updateCharts(data) {
    if (data.ytd_data) {
        updateYTDChart(data.ytd_data);
    }
    if (data.daily_data) {
        updateDailyChart(data.daily_data);
    }
}

// Update tables with new data
function updateTables(data) {
    if (data.ytd_data) {
        updateTableData('ytd-table', data.ytd_data);
    }
    if (data.daily_data) {
        updateTableData('daily-table', data.daily_data);
    }
}

// Helper function to update table data
function updateTableData(tableId, data) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    tbody.innerHTML = '';
    
    Object.entries(data).forEach(([hotelName, metrics]) => {
        const row = document.createElement('tr');
        const currencySymbol = document.getElementById('currency-symbol-data')?.dataset.symbol || '$';
        row.innerHTML = `
            <td>${hotelName}</td>
            <td>${metrics.rooms_available}</td>
            <td>${(metrics.occupancy_percentage).toFixed(2)}%</td>
            <td>${currencySymbol}${(metrics.average_rate).toFixed(2)}</td>
            <td>${metrics.rooms_sold}</td>
            <td>${currencySymbol}${(metrics.room_revenue).toFixed(2)}</td>
            <td>${currencySymbol}${(metrics.revpar).toFixed(2)}</td>
            <td>${(metrics.fair_market_share).toFixed(2)}%</td>
            <td>${(metrics.actual_market_share).toFixed(2)}%</td>
            <td>${metrics.mpi_rank}</td>
            <td>${(metrics.mpi).toFixed(2)}</td>
            <td>${metrics.ari_rank}</td>
            <td>${(metrics.ari).toFixed(2)}</td>
            <td>${metrics.rgi_rank}</td>
            <td>${(metrics.rgi).toFixed(2)}</td>
        `;
        tbody.appendChild(row);
    });
}

// Initialize charts when the page loads
document.addEventListener('DOMContentLoaded', function() {
    const ytdData = JSON.parse(document.getElementById('ytd-data').textContent || '{}');
    const dailyData = JSON.parse(document.getElementById('daily-data').textContent || '{}');
    
    if (Object.keys(ytdData).length) {
        updateYTDChart(ytdData);
    }
    if (Object.keys(dailyData).length) {
        updateDailyChart(dailyData);
    }
});