# HotelKit - Repairs Analytics Module

This Django module provides comprehensive repair request analytics and management functionality for hotel operations.

## Features

### Models
- **RepairRequest**: Complete model matching Excel structure with calculated duration fields
- Automatic calculation of response time, completion time, execution time, etc.
- SLA compliance tracking (4h, 24h, 48h)

### APIs
- **REST API endpoints** for all analytics data
- **File import** functionality for Excel/CSV files
- **Template download** for manual data entry

### Dashboard
- **Interactive dashboard** with TailwindCSS and Chart.js
- **KPI cards** showing key metrics
- **Trend analysis** with line charts
- **Type distribution** with pie charts
- **Location heatmap** for room analysis
- **Technician performance** tracking
- **SLA compliance** monitoring

## Usage

### Access the Dashboard
Visit: `/hotelkit/repairs/dashboard/`

### Import Data
1. Use the web interface: `/hotelkit/repairs/import/`
2. Or use the management command:
   ```bash
   python manage.py import_repairs path/to/file.xlsx
   ```

### Download Template
Visit: `/hotelkit/repairs/api/repairs/template/`

### Generate Excel Template Locally (one-click)
1. Install Python and `openpyxl` (`pip install openpyxl`).
2. In the `hotelkit` folder, double-click `run_excel_template.bat`.
3. The script creates `hotelkit_template.xlsx` in the same folder with the guest requests and repairs dashboards.

### API Endpoints
- `/hotelkit/repairs/api/repairs/` - CRUD operations
- `/hotelkit/repairs/api/repairs/kpis/` - Key performance indicators
- `/hotelkit/repairs/api/repairs/trend/` - Daily trends
- `/hotelkit/repairs/api/repairs/types/` - Type distribution
- `/hotelkit/repairs/api/repairs/heatmap/` - Location heatmap
- `/hotelkit/repairs/api/repairs/top-rooms/` - Top rooms by request count
- `/hotelkit/repairs/api/repairs/technicians/` - Technician performance
- `/hotelkit/repairs/api/repairs/sla/` - SLA compliance rates

## Data Structure

The module expects Excel files with the following columns:
- Position, ID, Creator, Recipients, Location, Location path
- Type, Type path, Assets, Ticket, Creation date, Priority, State
- Latest state change user, Latest state change time
- Time accepted, Time in progress, Time done, Time "in evaluation"
- Text, Link, Submitted result, Comments
- Parking reason, Parking information

## Installation

1. Add `hotelkit` to `INSTALLED_APPS` in settings.py
2. Run migrations: `python manage.py migrate`
3. Import your data using the provided tools
4. Access the dashboard at `/hotelkit/repairs/dashboard/`
