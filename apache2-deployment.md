# Deploying BenchstayV2 with Apache2

This document provides instructions for deploying the BenchstayV2 Django application with Apache2.

## Prerequisites

1. Apache2 installed
2. mod_wsgi installed and enabled
3. Python 3.x and virtualenv
4. PostgreSQL database
5. Redis server

## Installation Steps

### 1. Install Required Apache Modules

```bash
# For Debian/Ubuntu
sudo apt-get update
sudo apt-get install apache2 libapache2-mod-wsgi-py3

# Enable required modules
sudo a2enmod wsgi
sudo a2enmod ssl
sudo a2enmod headers
sudo a2enmod expires
sudo a2enmod deflate
```

### 2. Configure Apache Virtual Host

1. Copy the provided configuration files to the Apache sites directory:

```bash
# For HTTP
sudo cp apache2.conf /etc/apache2/sites-available/benchstay.conf

# For HTTPS
sudo cp apache2-ssl.conf /etc/apache2/sites-available/benchstay-ssl.conf
```

2. Edit the configuration files to update:
   - ServerName and ServerAlias to match your domain
   - Paths to SSL certificates (for HTTPS)
   - Adjust file paths if your deployment location differs

3. Enable the sites:

```bash
sudo a2ensite benchstay.conf
sudo a2ensite benchstay-ssl.conf
```

### 3. Prepare the Django Application

1. Collect static files:

```bash
python manage.py collectstatic
```

2. Update Django settings for production:

```python
# In benchstay/settings.py
DEBUG = False
ALLOWED_HOSTS = ['benchstay.example.com', 'www.benchstay.example.com']

# Generate a new secret key for production
SECRET_KEY = 'your-secure-secret-key'
```

3. Ensure database migrations are applied:

```bash
python manage.py migrate
```

### 4. Set File Permissions

Ensure Apache can access the necessary files:

```bash
# Adjust these commands based on your system's user/group for Apache
sudo chown -R www-data:www-data /path/to/BenchstayV2/media
sudo chmod -R 755 /path/to/BenchstayV2/staticfiles
```

### 5. Restart Apache

```bash
sudo systemctl restart apache2
```

## Troubleshooting

1. Check Apache error logs:

```bash
sudo tail -f /var/log/apache2/benchstay_error.log
sudo tail -f /var/log/apache2/benchstay_ssl_error.log
```

2. Verify WSGI configuration:

```bash
sudo apache2ctl -t
```

3. Common issues:
   - File permission problems
   - Incorrect paths in Apache configuration
   - Missing Apache modules
   - Django settings not properly configured for production

## Security Considerations

1. Always use HTTPS in production
2. Keep your Django SECRET_KEY secure and unique for production
3. Regularly update all packages and dependencies
4. Consider implementing a firewall
5. Set up regular database backups

## Performance Optimization

1. Enable caching as configured in the Apache files
2. Consider using a CDN for static files
3. Optimize database queries
4. Monitor server resources and scale as needed