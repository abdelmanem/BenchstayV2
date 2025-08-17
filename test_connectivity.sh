#!/bin/bash

# Benchstay Database Connectivity Test Script
# This script tests the connection to the PostgreSQL database
# It can be run independently of the installation process

echo "=== Benchstay Database Connectivity Test ==="

# Load environment variables
if [ -f ".env" ]; then
    source <(grep -v '^#' .env | sed -E 's/(.*)=(.*)/export \1="\2"/')
    echo "Environment variables loaded."
else
    echo "Error: .env file not found."
    exit 1
fi

# Test PostgreSQL connection
echo "Testing connection to PostgreSQL database..."
echo "  - Host: $DB_HOST:$DB_PORT"
echo "  - Database: $DB_NAME"
echo "  - User: $DB_USER"
echo ""

if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" > /dev/null 2>&1; then
    echo "✅ Database connection successful!"
    
    # Get PostgreSQL version
    echo ""
    echo "PostgreSQL Server Information:"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" -t
    
    # Test Django connection
    echo ""
    echo "Testing Django database connection..."
    if python -c "import django; django.setup(); from django.db import connection; connection.ensure_connection(); print('✅ Django database connection successful!')" 2>/dev/null; then
        echo "All connectivity tests passed!"
    else
        echo "❌ Django database connection failed!"
        echo "PostgreSQL connection works, but Django cannot connect."
        echo "Please check your Django settings."
    fi
else
    echo "❌ Failed to connect to the PostgreSQL database!"
    echo "Please check:"
    echo "  1. PostgreSQL service is running"
    echo "  2. Database credentials in .env file are correct"
    echo "  3. Network connectivity to database server"
    echo "  4. Database '$DB_NAME' exists"
    echo "  5. User '$DB_USER' has access to the database"
    
    # Check if PostgreSQL is running
    if command -v pg_isready > /dev/null; then
        echo ""
        echo "Checking if PostgreSQL server is running..."
        if pg_isready -h "$DB_HOST" -p "$DB_PORT"; then
            echo "✅ PostgreSQL server is running but connection failed."
            echo "   This suggests an authentication or database issue."
        else
            echo "❌ PostgreSQL server is not running or not reachable."
        fi
    fi
fi

echo ""
echo "=== Connectivity Test Completed ==="