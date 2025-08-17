# Deploying BenchstayV2 with Apache2 on Ubuntu Server

This guide provides specific instructions for deploying the BenchstayV2 Django application with Apache2 on Ubuntu servers.

## Prerequisites

1. Ubuntu Server (18.04 LTS or newer)
2. Apache2 installed
3. Python 3.x and virtualenv
4. PostgreSQL database
5. Redis server

## Installation Steps

### 1. Install Required Packages

```bash
# Update package lists
sudo apt update

# Install Apache and required modules
sudo apt install apache2 libapache2-mod-wsgi-py3 python3-dev python3-pip python3-venv postgresql postgresql-contrib redis-server

# Enable required Apache modules
sudo a2enmod wsgi ssl headers expires deflate rewrite
```

### 2. Create Directory Structure

```bash
# Create application directory
sudo mkdir -p /opt/Benchstay/BenchstayV2

# Set ownership (replace 'ubuntu' with your username)
sudo chown -R ubuntu:ubuntu /opt/Benchstay
```

### 3. Set Up the Application

```bash
# Clone the repository or copy your application files
# Example if using git:
git clone https://your-repository-url.git /opt/Benchstay/BenchstayV2

# Or copy files from another location
# sudo cp -r /path/to/source/* /opt/Benchstay/BenchstayV2/

# Navigate to the project directory
cd /opt/Benchstay/BenchstayV2

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install additional packages if needed
pip install gunicorn psycopg2-binary
```

### 4. Configure PostgreSQL Database

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user (in PostgreSQL shell)
CREATE DATABASE benchstay;
CREATE USER benchstaydbuser WITH PASSWORD 'your-secure-password';
ALTER ROLE benchstaydbuser SET client_encoding TO 'utf8';
ALTER ROLE benchstaydbuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE benchstaydbuser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE benchstay TO benchstaydbuser;
\q
```

### 5. Configure Django Settings

Update the `benchstay/settings.py` file with production settings:

```python
# Set DEBUG to False for production
DEBUG = False

# Add your domain to allowed hosts
ALLOWED_HOSTS = ['benchstay.example.com', 'www.benchstay.example.com']

# Update database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'benchstay',
        'USER': 'benchstaydbuser',
        'PASSWORD': 'your-secure-password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Update Redis settings if needed
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Generate a new secret key for production
SECRET_KEY = 'your-secure-secret-key'

# Static and media files configuration
STATIC_ROOT = '/opt/Benchstay/BenchstayV2/staticfiles'
MEDIA_ROOT = '/opt/Benchstay/BenchstayV2/media'
```

### 6. Initialize the Django Application

```bash
# Activate virtual environment if not already activated
source /opt/Benchstay/BenchstayV2/venv/bin/activate

# Navigate to project directory
cd /opt/Benchstay/BenchstayV2

# Apply migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser (follow prompts)
python manage.py createsuperuser
```

### 7. Configure Apache

1. Copy the Apache configuration files to the appropriate location:

```bash
sudo cp /opt/Benchstay/BenchstayV2/apache2-ubuntu.conf /etc/apache2/sites-available/benchstay.conf
sudo cp /opt/Benchstay/BenchstayV2/apache2-ubuntu-ssl.conf /etc/apache2/sites-available/benchstay-ssl.conf
```

2. Edit the configuration files if needed to update:
   - ServerName and ServerAlias to match your domain
   - Paths to SSL certificates (for HTTPS)

3. Enable the sites:

```bash
sudo a2ensite benchstay.conf
sudo a2ensite benchstay-ssl.conf
```

4. Disable the default site (optional):

```bash
sudo a2dissite 000-default.conf
```

### 8. Set File Permissions

```bash
# Set appropriate permissions for Apache
sudo chown -R www-data:www-data /opt/Benchstay/BenchstayV2/media
sudo chown -R www-data:www-data /opt/Benchstay/BenchstayV2/staticfiles

# Make sure the wsgi.py file is accessible
sudo chmod 664 /opt/Benchstay/BenchstayV2/benchstay/wsgi.py

# Make sure directories are executable
sudo find /opt/Benchstay/BenchstayV2 -type d -exec chmod 755 {} \;
```

### 9. Set Up SSL Certificates

For production, use Let's Encrypt to obtain free SSL certificates:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-apache

# Obtain and install certificates
sudo certbot --apache -d benchstay.example.com -d www.benchstay.example.com
```

Alternatively, if you have your own certificates, place them in the appropriate locations and update the Apache configuration accordingly.

### 10. Restart Apache

```bash
sudo systemctl restart apache2
```

### 11. Test the Deployment

Visit your domain in a web browser to verify that the application is working correctly.

## Troubleshooting

1. Check Apache error logs:

```bash
sudo tail -f /var/log/apache2/benchstay_error.log
sudo tail -f /var/log/apache2/benchstay_ssl_error.log
```

2. Check Apache configuration:

```bash
sudo apache2ctl configtest
```

3. Check permissions:

```bash
# Verify that Apache can access the necessary files
sudo -u www-data test -r /opt/Benchstay/BenchstayV2/benchstay/wsgi.py && echo "Readable" || echo "Not readable"
```

4. Check the virtual environment:

```bash
# Verify that the virtual environment is correctly set up
source /opt/Benchstay/BenchstayV2/venv/bin/activate
python -c "import django; print(django.__version__)"
```

## Maintenance

### Updating the Application

```bash
# Navigate to the project directory
cd /opt/Benchstay/BenchstayV2

# Pull the latest changes (if using git)
git pull

# Activate the virtual environment
source venv/bin/activate

# Install any new dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart Apache
sudo systemctl restart apache2
```

### Backup

Regularly backup your database and media files:

```bash
# Backup PostgreSQL database
sudo -u postgres pg_dump benchstay > /path/to/backup/benchstay_$(date +%Y%m%d).sql

# Backup media files
sudo tar -czf /path/to/backup/media_$(date +%Y%m%d).tar.gz /opt/Benchstay/BenchstayV2/media
```

## Security Considerations

1. Keep your Ubuntu server updated:

```bash
sudo apt update && sudo apt upgrade
```

2. Configure a firewall:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

3. Set up automatic security updates:

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

4. Regularly check for and apply security updates to Django and other dependencies.

5. Consider setting up fail2ban to protect against brute force attacks.

## Performance Optimization

1. Enable caching as configured in the Apache files
2. Consider using a CDN for static files
3. Optimize database queries
4. Monitor server resources and scale as needed
5. Consider using Nginx as a reverse proxy in front of Apache for better performance