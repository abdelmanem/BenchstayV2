#!/bin/bash

# Benchstay Installation/Upgrade Script
# This script automates the setup process for the Benchstay application
# It can be used for both new installations and upgrades

# Determine if this is a new installation or an upgrade
if [ -d "venv" ] || [ -f "db.sqlite3" ] || sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "Benchstay"; then
    INSTALLATION_TYPE="upgrade"
    echo "=== Starting Benchstay Upgrade ==="
else
    INSTALLATION_TYPE="new"
    echo "=== Starting New Benchstay Installation ==="
fi

# Check for required dependencies
check_dependencies() {
    echo "Checking dependencies..."
    
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        echo "Error: Python 3 is required but not installed."
        echo "Please install Python 3 and try again."
        exit 1
    fi
    
    # Check for pip
    if ! command -v pip &> /dev/null; then
        echo "Error: pip is required but not installed."
        echo "Please install pip and try again."
        exit 1
    fi
    
    # Check for PostgreSQL
    if ! command -v psql &> /dev/null; then
        echo "Error: PostgreSQL is required but not installed."
        echo "Please install PostgreSQL and try again."
        exit 1
    fi
    
    echo "All dependencies are installed."
}

# Setup virtual environment
setup_venv() {
    echo "Setting up virtual environment..."
    
    # Check if venv directory already exists and remove it
    if [ -d "venv" ]; then
        if [ "$INSTALLATION_TYPE" = "upgrade" ]; then
            echo "Upgrading existing virtual environment..."
            # Backup the existing venv just in case
            mv venv venv_backup_$(date +%Y%m%d%H%M%S)
        else
            echo "Removing existing virtual environment..."
            rm -rf venv
        fi
    fi
    
    # Create new virtual environment
    echo "Creating new virtual environment..."
    python3 -m venv venv
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    echo "Virtual environment is set up and activated."
}

# Install required packages
install_packages() {
    echo "Installing required packages..."
    
    # Install packages from requirements.txt
    pip install -r requirements.txt
    
    echo "All packages installed successfully."
}

# Setup PostgreSQL database
setup_database() {
    echo "Setting up PostgreSQL database..."
    
    # Load environment variables
    if [ -f ".env" ]; then
        source <(grep -v '^#' .env | sed -E 's/(.*)=(.*)/export \1="\2"/')
        echo "Environment variables loaded."
    else
        echo "Error: .env file not found."
        exit 1
    fi
    
    # Check if database already exists
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        echo "Database $DB_NAME already exists."
        
        if [ "$INSTALLATION_TYPE" = "upgrade" ]; then
            echo "Backing up existing database before upgrade..."
            BACKUP_FILE="${DB_NAME}_backup_$(date +%Y%m%d%H%M%S).sql"
            sudo -u postgres pg_dump "$DB_NAME" > "$BACKUP_FILE"
            echo "Database backed up to $BACKUP_FILE"
        fi
    else
        echo "Creating database $DB_NAME..."
        sudo -u postgres psql -c "CREATE DATABASE \"$DB_NAME\";"
        
        # Create database user if it doesn't exist
        if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
            echo "Creating database user $DB_USER..."
            sudo -u postgres psql -c "CREATE USER \"$DB_USER\" WITH PASSWORD '$DB_PASSWORD';"
        fi
        
        # Grant privileges to user
        echo "Granting privileges to $DB_USER..."
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO \"$DB_USER\";"
        sudo -u postgres psql -c "ALTER USER \"$DB_USER\" CREATEDB;"
    fi
    
    echo "Database setup completed."
}

# Apply Django migrations
apply_migrations() {
    echo "Applying Django migrations..."
    
    python manage.py makemigrations
    python manage.py migrate
    
    echo "Migrations applied successfully."
}

# Clear user sessions
clear_sessions() {
    echo "Clearing user sessions..."
    
    python manage.py clearsessions
    
    echo "User sessions cleared successfully."
}

# Collect static files
collect_static() {
    echo "Collecting static files..."
    
    python manage.py collectstatic --noinput
    
    echo "Static files collected successfully."
}

# Create superuser
create_superuser() {
    echo "Creating superuser..."
    
    # Check if superuser already exists
    if python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); exit(0 if User.objects.filter(is_superuser=True).exists() else 1)"; then
        echo "Superuser already exists."
    else
        echo "Please provide details for the superuser account:"
        python manage.py createsuperuser
    fi
}

# Test database connectivity
test_connectivity() {
    echo "Testing database connectivity..."
    
    # Load environment variables if not already loaded
    if [ -z "$DB_NAME" ] && [ -f ".env" ]; then
        source <(grep -v '^#' .env | sed -E 's/(.*)=(.*)/export \1="\2"/')
        echo "Environment variables loaded for connectivity test."
    fi
    
    # Test PostgreSQL connection
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ Database connection successful!"
        echo "   - Host: $DB_HOST:$DB_PORT"
        echo "   - Database: $DB_NAME"
        echo "   - User: $DB_USER"
        return 0
    else
        echo "❌ Failed to connect to the database!"
        echo "   - Host: $DB_HOST:$DB_PORT"
        echo "   - Database: $DB_NAME"
        echo "   - User: $DB_USER"
        echo ""
        echo "Please check your database credentials and ensure PostgreSQL is running."
        return 1
    fi
}

# Main installation process
main() {
    check_dependencies
    setup_venv
    install_packages
    setup_database
    apply_migrations
    clear_sessions
    collect_static
    
    # Only prompt to create superuser for new installations
    if [ "$INSTALLATION_TYPE" = "new" ]; then
        create_superuser
    fi
    
    # Test connectivity after setup
    test_connectivity
    
    if [ "$INSTALLATION_TYPE" = "upgrade" ]; then
        echo "\n=== Benchstay Upgrade Completed Successfully ==="
    else
        echo "\n=== Benchstay Installation Completed Successfully ==="
    fi
    echo "You can now start the development server with: python manage.py runserver"
}

# Run the main function
main