# Benchstay Database Connectivity Test Script (PowerShell version)
# This script tests the connection to the PostgreSQL database
# It can be run independently of the installation process

Write-Host "=== Benchstay Database Connectivity Test ===" -ForegroundColor Cyan

# Load environment variables
if (Test-Path ".env") {
    Write-Host "Loading environment variables..."
    $envContent = Get-Content ".env" | Where-Object { $_ -notmatch '^#' -and $_ -match '=' }
    foreach ($line in $envContent) {
        $key, $value = $line -split '=', 2
        Set-Variable -Name $key -Value $value
    }
    Write-Host "Environment variables loaded." -ForegroundColor Green
} else {
    Write-Host "Error: .env file not found." -ForegroundColor Red
    exit 1
}

# Test PostgreSQL connection
Write-Host "Testing connection to PostgreSQL database..."
Write-Host "  - Host: $DB_HOST`:$DB_PORT"
Write-Host "  - Database: $DB_NAME"
Write-Host "  - User: $DB_USER"
Write-Host ""

# Check if PostgreSQL is installed
$psqlPath = $null
$pgIsReadyPath = $null

# Try to find PostgreSQL binaries in common installation locations
$possiblePaths = @(
    "C:\Program Files\PostgreSQL\*\bin",
    "C:\Program Files (x86)\PostgreSQL\*\bin"
)

foreach ($path in $possiblePaths) {
    $binPaths = Resolve-Path $path -ErrorAction SilentlyContinue
    if ($binPaths) {
        foreach ($binPath in $binPaths) {
            if (Test-Path "$binPath\psql.exe") {
                $psqlPath = "$binPath\psql.exe"
                $pgIsReadyPath = "$binPath\pg_isready.exe"
                break
            }
        }
    }
    if ($psqlPath) { break }
}

if (-not $psqlPath) {
    Write-Host "❌ PostgreSQL client tools not found!" -ForegroundColor Red
    Write-Host "Please install PostgreSQL or ensure it's in your PATH." -ForegroundColor Yellow
    exit 1
}

# Test PostgreSQL connection
$env:PGPASSWORD = $DB_PASSWORD
try {
    $result = & $psqlPath -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();" -t 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Database connection successful!" -ForegroundColor Green
        
        # Get PostgreSQL version
        Write-Host ""
        Write-Host "PostgreSQL Server Information:" -ForegroundColor Cyan
        Write-Host $result
        
        # Test Django connection
        Write-Host ""
        Write-Host "Testing Django database connection..." -ForegroundColor Cyan
        try {
            # Activate virtual environment if it exists
            if (Test-Path "venv\Scripts\Activate.ps1") {
                . .\venv\Scripts\Activate.ps1
            }
            
            $djangoTest = python -c "import django; django.setup(); from django.db import connection; connection.ensure_connection(); print('✅ Django database connection successful!')"
            Write-Host $djangoTest -ForegroundColor Green
            Write-Host "All connectivity tests passed!" -ForegroundColor Green
        } catch {
            Write-Host "❌ Django database connection failed!" -ForegroundColor Red
            Write-Host "PostgreSQL connection works, but Django cannot connect." -ForegroundColor Yellow
            Write-Host "Please check your Django settings." -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ Failed to connect to the PostgreSQL database!" -ForegroundColor Red
        Write-Host "Please check:" -ForegroundColor Yellow
        Write-Host "  1. PostgreSQL service is running" -ForegroundColor Yellow
        Write-Host "  2. Database credentials in .env file are correct" -ForegroundColor Yellow
        Write-Host "  3. Network connectivity to database server" -ForegroundColor Yellow
        Write-Host "  4. Database '$DB_NAME' exists" -ForegroundColor Yellow
        Write-Host "  5. User '$DB_USER' has access to the database" -ForegroundColor Yellow
        
        # Check if PostgreSQL is running
        if ($pgIsReadyPath) {
            Write-Host ""
            Write-Host "Checking if PostgreSQL server is running..." -ForegroundColor Cyan
            $pgIsReadyResult = & $pgIsReadyPath -h $DB_HOST -p $DB_PORT
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ PostgreSQL server is running but connection failed." -ForegroundColor Yellow
                Write-Host "   This suggests an authentication or database issue." -ForegroundColor Yellow
            } else {
                Write-Host "❌ PostgreSQL server is not running or not reachable." -ForegroundColor Red
            }
        }
    }
} catch {
    Write-Host "❌ Error executing PostgreSQL command: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Connectivity Test Completed ===" -ForegroundColor Cyan