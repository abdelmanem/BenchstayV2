// Cache DOM elements
const analyticsTables = document.querySelectorAll('.analytics-table');
let isRefreshing = false; // Flag to prevent multiple simultaneous refreshes

// Sorting state
let currentSortColumn = null;
let currentSortDirection = 'asc';

// Function to sort table data
function sortTable(table, columnIndex, sortDirection) {
    const tbody = table.querySelector('tbody');
    
    // Save the total row (with class table-dark) to append it at the end after sorting
    const totalRow = tbody.querySelector('tr.table-dark');
    
    // Get all rows except the total row
    const rows = Array.from(tbody.querySelectorAll('tr:not(.table-dark)'));
    const headerRow = table.querySelector('thead tr:last-child');
    const headers = headerRow.querySelectorAll('th');
    
    // Clear previous sort indicators
    table.querySelectorAll('thead th').forEach(header => {
        header.classList.remove('sort-asc', 'sort-desc');
    });
    
    // Add sort indicator to current header
    if (columnIndex !== null) {
        // Find the correct header based on the column index
        // This accounts for the complex table structure with rowspan attributes
        const allHeaders = Array.from(table.querySelectorAll('thead th'));
        const visibleHeaders = allHeaders.filter(th => {
            // Only consider headers that are visible in the last row or have rowspan > 1
            return th.closest('tr') === headerRow || parseInt(th.getAttribute('rowspan') || 1) > 1;
        });
        
        if (visibleHeaders[columnIndex]) {
            visibleHeaders[columnIndex].classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
        }
    }
    
    // Sort the rows
    if (columnIndex !== null) {
        rows.sort((rowA, rowB) => {
            const cellA = rowA.querySelectorAll('td')[columnIndex];
            const cellB = rowB.querySelectorAll('td')[columnIndex];
            
            if (!cellA || !cellB) return 0;
            
            let valueA = cellA.textContent.trim();
            let valueB = cellB.textContent.trim();
            
            // Handle different data types
            if (valueA.includes('%')) {
                // Percentage values
                valueA = parseFloat(valueA.replace('%', ''));
                valueB = parseFloat(valueB.replace('%', ''));
            } else if (valueA.includes('$') || valueA.includes('EGP')) {
                // Currency values
                valueA = parseFloat(valueA.replace('$', '').replace('EGP', '').replace(/,/g, ''));
                valueB = parseFloat(valueB.replace('$', '').replace('EGP', '').replace(/,/g, ''));
            } else if (!isNaN(parseFloat(valueA))) {
                // Numeric values
                valueA = parseFloat(valueA);
                valueB = parseFloat(valueB);
            }
            
            // Compare values
            if (valueA < valueB) {
                return sortDirection === 'asc' ? -1 : 1;
            }
            if (valueA > valueB) {
                return sortDirection === 'asc' ? 1 : -1;
            }
            return 0;
        });
    }
    
    // Clear the tbody
    while (tbody.firstChild) {
        tbody.removeChild(tbody.firstChild);
    }
    
    // Append the sorted rows
    rows.forEach(row => {
        tbody.appendChild(row);
    });
    
    // Append the total row at the end if it exists
    if (totalRow) {
        tbody.appendChild(totalRow);
    }
}



// Update tables with new data
function updateTables(data) {
    if (data.ytd_data) {
        updateTableData('ytd-table', data.ytd_data, data.ytd_totals);
    }
    if (data.daily_data) {
        updateTableData('daily-table', data.daily_data, data.daily_totals);
    }
    if (data.mtd_data) {
        updateTableData('mtd-table', data.mtd_data, data.mtd_totals);
    }
    
    // Re-apply sorting if a column was previously sorted
    if (currentSortColumn !== null) {
        analyticsTables.forEach(table => {
            sortTable(table, currentSortColumn, currentSortDirection);
        });
    }
    
    // Update the refresh button state
    isRefreshing = false;
    const refreshButton = document.getElementById('refresh-all-button');
    if (refreshButton) {
        refreshButton.disabled = false;
        refreshButton.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Refresh Data';
    }
}

// Helper function to update table data
function updateTableData(tableId, data, totals) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    tbody.innerHTML = '';
    
    // Add hotel rows
    Object.entries(data).forEach(([hotelName, metrics]) => {
        const row = document.createElement('tr');
        // Check if this is the user's hotel to highlight it
        if (document.querySelector(`tr.table-primary td:first-child`).textContent.trim() === hotelName) {
            row.classList.add('table-primary');
        }
        row.innerHTML = `
            <td>${hotelName}</td>
            <td>${metrics.rooms_available}</td>
            <td>${(metrics.occupancy_percentage).toFixed(2)}%</td>
            <td>EGP${(metrics.average_rate).toFixed(2)}</td>
            <td>${metrics.rooms_sold}</td>
            <td>EGP${(metrics.room_revenue).toFixed(2)}</td>
            <td>EGP${(metrics.revpar).toFixed(2)}</td>
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
    
    // Add total row if totals are provided
    if (totals) {
        const totalRow = document.createElement('tr');
        totalRow.classList.add('table-dark');
        totalRow.innerHTML = `
            <td>Total</td>
            <td>${totals.rooms_available}</td>
            <td>${(totals.occupancy_percentage).toFixed(2)}%</td>
            <td>EGP${(totals.average_rate).toFixed(2)}</td>
            <td>${totals.rooms_sold}</td>
            <td>EGP${(totals.room_revenue).toFixed(2)}</td>
            <td>EGP${(totals.revpar).toFixed(2)}</td>
            <td>100.00%</td>
            <td>100.00%</td>
            <td>-</td>
            <td>-</td>
            <td>-</td>
            <td>-</td>
            <td>-</td>
            <td>-</td>
        `;
        tbody.appendChild(totalRow);
    }
}

// Function to refresh data via AJAX
function refreshData() {
    if (isRefreshing) return;
    
    isRefreshing = true;
    const refreshButton = document.getElementById('refresh-all-button');
    if (refreshButton) {
        refreshButton.disabled = true;
        refreshButton.innerHTML = '<i class="bi bi-arrow-clockwise animate-spin"></i> Refreshing...';
    }
    
    // Get the current filter values
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
    
    // Create form data
    const formData = new FormData();
    formData.append('csrfmiddlewaretoken', csrfToken);
    formData.append('start_date', startDateInput.value);
    formData.append('end_date', endDateInput.value);
    
    // Make the AJAX request to the refresh endpoint
    fetch('/reports/ajax/refresh-competitor-analytics/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Get the data directly from the JSON response
        const ytdData = data.ytd_data;
        const dailyData = data.daily_data;
        const mtdData = data.mtd_data;
        
        // Get totals directly from the JSON response
        const ytdTotals = data.ytd_totals;
        const dailyTotals = data.daily_totals;
        const mtdTotals = data.mtd_totals;
        
        // Update the tables with the new data
        updateTables({
            ytd_data: ytdData,
            daily_data: dailyData,
            mtd_data: mtdData,
            ytd_totals: ytdTotals,
            daily_totals: dailyTotals,
            mtd_totals: mtdTotals
        });
    })
    .catch(error => {
        console.error('Error refreshing data:', error);
        alert('Failed to refresh data. Please try again.');
        isRefreshing = false;
        if (refreshButton) {
            refreshButton.disabled = false;
            refreshButton.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Refresh Data';
        }
    });
}

// Helper function to extract totals from the HTML
function extractTotals(container, tableSelector) {
    const table = container.querySelector(tableSelector);
    if (!table) return null;
    
    const totalRow = table.querySelector('tbody tr.table-dark');
    if (!totalRow) return null;
    
    const cells = totalRow.querySelectorAll('td');
    return {
        rooms_available: parseInt(cells[1].textContent.trim()),
        occupancy_percentage: parseFloat(cells[2].textContent.trim().replace('%', '')),
        average_rate: parseFloat(cells[3].textContent.trim().replace('$', '').replace('EGP', '')),
        rooms_sold: parseInt(cells[4].textContent.trim()),
        room_revenue: parseFloat(cells[5].textContent.trim().replace('$', '').replace('EGP', '')),
        revpar: parseFloat(cells[6].textContent.trim().replace('$', '').replace('EGP', ''))
    };
}

// Function to export table data
function exportTable(tableId, format) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;
    
    // Construct the export URL
    let exportUrl = `/reports/export-competitor-analytics/?format=${format}`;
    exportUrl += `&start_date=${startDate}&end_date=${endDate}`;
    
    // Open the export URL in a new tab
    window.open(exportUrl, '_blank');
}

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Clear resource cache to ensure fresh data
    if (window.cacheControl && typeof window.cacheControl.clearResourceCache === 'function') {
        window.cacheControl.clearResourceCache();
    }
    
    // Set default date to yesterday
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    
    if (startDateInput && endDateInput) {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const yesterdayFormatted = yesterday.toISOString().split('T')[0];
        
        // Always set to yesterday as default
        startDateInput.value = yesterdayFormatted;
        endDateInput.value = yesterdayFormatted;
        
        // Trigger initial data refresh with yesterday's date
        refreshData();
    }
    
    // Add click event listeners to table headers for sorting
    analyticsTables.forEach(table => {
        // Get all headers from the table
        const allHeaders = table.querySelectorAll('thead th');
        
        allHeaders.forEach((header) => {
            header.addEventListener('click', () => {