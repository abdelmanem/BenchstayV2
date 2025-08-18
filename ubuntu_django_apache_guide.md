# Complete Guide: Deploying Django Applications on Ubuntu with Apache

This guide covers deploying a Django application (like BenchStay) on Ubuntu Server with Apache, PostgreSQL, and Redis.

## Prerequisites
- Ubuntu 20.04+ Server
- Root or sudo access
- Basic command line knowledge

---

## 1. System Updates and Package Installation

### Update system packages:
```bash
sudo apt update && sudo apt upgrade -y
```

### Install required packages:
```bash
sudo apt install -y \
    apache2 \
    libapache2-mod-wsgi-py3 \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    redis-server \
    git \
    nano \
    ufw
```

### Enable and start services:
```bash
sudo systemctl enable apache2
sudo systemctl enable postgresql
sudo systemctl enable redis-server
sudo systemctl start apache2
sudo systemctl start postgresql
sudo systemctl start redis-server
```

---

## 2. PostgreSQL Database Setup

### Switch to postgres user and create database:
```bash
sudo -u postgres psql
```

### In PostgreSQL shell, create database and user:
```sql
-- Create database (use lowercase for consistency)
CREATE DATABASE benchstay;

-- Create user (use lowercase for consistency)
CREATE USER benchstay WITH PASSWORD 'your_secure_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE benchstay TO benchstay;

-- Configure user settings
ALTER ROLE benchstay SET client_encoding TO 'utf8';
ALTER ROLE benchstay SET default_transaction_isolation TO 'read committed';
ALTER ROLE benchstay SET timezone TO 'UTC';

-- Exit PostgreSQL
\q
```

### Test database connection:
```bash
psql -U benchstay -d benchstay -h localhost -W
```

---

## 3. Project Directory Setup

### Create project directory:
```bash
sudo mkdir -p /var/www/benchstay
sudo mkdir -p /var/www/benchstay/logs
sudo chown -R www-data:www-data /var/www/benchstay
```

### Copy your Django project:
```bash
# If uploading via SCP/SFTP, copy to /var/www/benchstay
# If using Git:
cd /var/www
sudo -u www-data git clone https://your-repo-url.git benchstay
```

---

## 4. Python Virtual Environment Setup

### Create virtual environment:
```bash
cd /var/www/benchstay
sudo -u www-data python3 -m venv venv
```

### Activate virtual environment and install dependencies:
```bash
sudo -u www-data /var/www/benchstay/venv/bin/pip install --upgrade pip
sudo -u www-data /var/www/benchstay/venv/bin/pip install django
sudo -u www-data /var/www/benchstay/venv/bin/pip install psycopg2-binary
sudo -u www-data /var/www/benchstay/venv/bin/pip install django-redis
sudo -u www-data /var/www/benchstay/venv/bin/pip install python-dotenv

# If you have a requirements.txt file:
# sudo -u www-data /var/www/benchstay/venv/bin/pip install -r requirements.txt
```

---

## 5. Django Settings Configuration

### Create environment variables file:
```bash
sudo -u www-data nano /var/www/benchstay/.env
```

### Add environment variables:
```env
# Database Settings
DB_NAME=benchstay
DB_USER=benchstay
DB_PASSWORD=your_secure_password_here
DB_HOST=localhost
DB_PORT=5432

# Django Settings
DJANGO_SECRET_KEY=your-new-secret-key-here
DJANGO_DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-server-ip,localhost,127.0.0.1

# Redis Settings
REDIS_URL=redis://127.0.0.1:6379/1
```

### Set proper permissions:
```bash
sudo chmod 600 /var/www/benchstay/.env
sudo chown www-data:www-data /var/www/benchstay/.env
```

### Update Django settings.py:
```bash
sudo nano /var/www/benchstay/benchstay/settings.py
```

Add these imports at the top:
```python
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).resolve().parent.parent / '.env')
```

Update key settings:
```python
# Security
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'fallback-key')
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'benchstay'),
        'USER': os.environ.get('DB_USER', 'benchstay'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 300,
    }
}

# Static and Media files
STATIC_URL = '/static/'
STATIC_ROOT = '/var/www/benchstay/staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = '/var/www/benchstay/media'

# Cache with Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

---

## 6. Django Application Setup

### Run Django management commands:
```bash
cd /var/www/benchstay

# Check for issues
sudo -u www-data ./venv/bin/python manage.py check

# Create database tables
sudo -u www-data ./venv/bin/python manage.py migrate

# Collect static files
sudo -u www-data ./venv/bin/python manage.py collectstatic --noinput

# Create superuser
sudo -u www-data ./venv/bin/python manage.py createsuperuser
```

### Set proper permissions:
```bash
sudo chown -R www-data:www-data /var/www/benchstay
sudo chmod -R 755 /var/www/benchstay
sudo chmod -R 644 /var/www/benchstay/benchstay/*.py
sudo chmod +x /var/www/benchstay/manage.py
```

---

## 7. Apache Configuration

### Enable required Apache modules:
```bash
sudo a2enmod wsgi
sudo a2enmod rewrite
sudo a2enmod ssl  # If using HTTPS
```

### Create Apache virtual host:
```bash
sudo nano /etc/apache2/sites-available/benchstay.conf
```

### Add virtual host configuration:
```apache
<VirtualHost *:80>
    ServerName your-domain.com
    ServerAlias www.your-domain.com
    DocumentRoot /var/www/benchstay
    
    # WSGI Configuration
    WSGIDaemonProcess benchstay python-home=/var/www/benchstay/venv python-path=/var/www/benchstay
    WSGIProcessGroup benchstay
    WSGIScriptAlias / /var/www/benchstay/benchstay/wsgi.py
    WSGIApplicationGroup %{GLOBAL}
    
    # Static files
    Alias /static /var/www/benchstay/staticfiles
    <Directory /var/www/benchstay/staticfiles>
        Require all granted
    </Directory>
    
    # Media files
    Alias /media /var/www/benchstay/media
    <Directory /var/www/benchstay/media>
        Require all granted
    </Directory>
    
    # Django project directory
    <Directory /var/www/benchstay/benchstay>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>
    
    # Main project directory
    <Directory /var/www/benchstay>
        Options -Indexes
        AllowOverride None
        Require all granted
    </Directory>
    
    # Logging
    ErrorLog /var/www/benchstay/logs/apache_error.log
    CustomLog /var/www/benchstay/logs/apache_access.log combined
    LogLevel info
</VirtualHost>
```

### Enable site and disable default:
```bash
sudo a2ensite benchstay.conf
sudo a2dissite 000-default.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

---

## 8. Django URL Configuration Fix

### Ensure your main urls.py has a root path:
```bash
sudo nano /var/www/benchstay/benchstay/urls.py
```

### Make sure it includes a root URL pattern:
```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('hotel/', include('hotel_management.urls', namespace='hotel_management')),
    path('reports/', include('reporting.urls')),
    # Add root URL - redirect to hotel management or create a home view
    path('', lambda request: redirect('/hotel/'), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

---

## 9. Firewall Configuration

### Configure UFW firewall:
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Apache Full'
sudo ufw status
```

---

## 10. Testing and Troubleshooting

### Test Django directly:
```bash
cd /var/www/benchstay
sudo -u www-data ./venv/bin/python manage.py runserver 0.0.0.0:8001
```

### Monitor logs in real-time:
```bash
# Apache error log
sudo tail -f /var/log/apache2/error.log

# Custom application logs
sudo tail -f /var/www/benchstay/logs/apache_error.log
```

### Common troubleshooting commands:
```bash
# Check Apache status
sudo systemctl status apache2

# Restart services
sudo systemctl restart apache2
sudo systemctl restart postgresql
sudo systemctl restart redis-server

# Test Apache configuration
sudo apache2ctl configtest

# Check Django settings
sudo -u www-data ./venv/bin/python manage.py check

# Test database connection
sudo -u www-data ./venv/bin/python manage.py dbshell
```

---

## 11. Security Hardening (Production)

### Update .env file for production:
```bash
sudo nano /var/www/benchstay/.env
```

```env
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=generate-a-new-long-random-secret-key
```

### Additional security settings in settings.py:
```python
# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# If using HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## 12. SSL/HTTPS Setup (Optional)

### Install Certbot:
```bash
sudo apt install certbot python3-certbot-apache
```

### Get SSL certificate:
```bash
sudo certbot --apache -d your-domain.com -d www.your-domain.com
```

### Auto-renewal:
```bash
sudo crontab -e
# Add this line:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

---

## 13. Maintenance Commands

### Regular maintenance tasks:
```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Django migrations (when needed)
cd /var/www/benchstay
sudo -u www-data ./venv/bin/python manage.py migrate

# Collect static files (after updates)
sudo -u www-data ./venv/bin/python manage.py collectstatic --noinput

# Clear Django cache
sudo -u www-data ./venv/bin/python manage.py shell -c "from django.core.cache import cache; cache.clear()"
```

---

## Success!

Your Django application should now be accessible at:
- **Main Application**: `http://your-domain.com` or `http://your-server-ip`
- **Admin Panel**: `http://your-domain.com/admin`

### Default Login
Use the superuser credentials you created during setup.

---

## Common Issues and Solutions

### 1. 500 Internal Server Error
- Check Apache error logs: `sudo tail -f /var/log/apache2/error.log`
- Verify settings.py syntax: `sudo -u www-data ./venv/bin/python manage.py check`

### 2. Database Connection Error
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Test connection: `psql -U benchstay -d benchstay -h localhost -W`
- Check .env file values

### 3. Static Files Not Loading
- Run: `sudo -u www-data ./venv/bin/python manage.py collectstatic --noinput`
- Check Apache alias configuration
- Verify file permissions

### 4. 404 on Root URL
- Ensure you have a root URL pattern in urls.py
- Add: `path('', lambda request: redirect('/hotel/'), name='home'),`

This guide provides a complete production-ready Django deployment on Ubuntu with Apache!