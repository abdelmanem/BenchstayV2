# Deploying BenchstayV2 with Apache2 on Windows

This guide provides specific instructions for deploying the BenchstayV2 Django application with Apache2 on Windows systems.

## Prerequisites

1. Apache2 for Windows installed
2. mod_wsgi for Windows installed and enabled
3. Python 3.x and virtualenv
4. PostgreSQL database
5. Redis server

## Installation Steps

### 1. Install Apache for Windows

1. Download Apache for Windows from the Apache Lounge website: https://www.apachelounge.com/download/
2. Extract the downloaded ZIP file to a location like `C:\Apache24`
3. Open a command prompt as Administrator and run:

```cmd
cd C:\Apache24\bin
httpd.exe -k install
```

### 2. Install mod_wsgi for Windows

1. Install the mod_wsgi module that matches your Python version:

```cmd
pip install mod_wsgi
```

2. Generate the Apache module file:

```cmd
mod_wsgi-express module-config
```

3. Copy the output and add it to your Apache configuration file (`C:\Apache24\conf\httpd.conf`):

```apache
LoadFile "C:/path/to/python/python3x.dll"
LoadModule wsgi_module "C:/path/to/python/lib/site-packages/mod_wsgi/server/mod_wsgi.cp3x-win_amd64.pyd"
WSGIPythonHome "C:/path/to/python"
```

### 3. Configure Apache Virtual Host

1. Create a directory for your virtual host configurations:

```cmd
mkdir C:\Apache24\conf\sites-available
mkdir C:\Apache24\conf\sites-enabled
```

2. Add the following to your `httpd.conf` file:

```apache
# Virtual hosts
Include conf/sites-enabled/*.conf
```

3. Copy the provided configuration files to the Apache sites directory:

```cmd
copy C:\Trae\BenchstayV2\apache2.conf C:\Apache24\conf\sites-available\benchstay.conf
copy C:\Trae\BenchstayV2\apache2-ssl.conf C:\Apache24\conf\sites-available\benchstay-ssl.conf
```

4. Create symbolic links to enable the sites:

```cmd
mklink /H C:\Apache24\conf\sites-enabled\benchstay.conf C:\Apache24\conf\sites-available\benchstay.conf
mklink /H C:\Apache24\conf\sites-enabled\benchstay-ssl.conf C:\Apache24\conf\sites-available\benchstay-ssl.conf
```

5. Edit the configuration files to update:
   - ServerName and ServerAlias to match your domain
   - Paths to SSL certificates (for HTTPS)
   - Ensure all file paths use Windows-style paths with forward slashes (e.g., `C:/Trae/BenchstayV2`)

### 4. Enable Required Apache Modules

Ensure the following modules are enabled in your `httpd.conf` file:

```apache
LoadModule deflate_module modules/mod_deflate.so
LoadModule headers_module modules/mod_headers.so
LoadModule expires_module modules/mod_expires.so
LoadModule ssl_module modules/mod_ssl.so
```

### 5. Prepare the Django Application

1. Collect static files:

```cmd
cd C:\Trae\BenchstayV2
python manage.py collectstatic
```

2. Update Django settings for production:

```python
# In benchstay/settings.py
DEBUG = False
ALLOWED_HOSTS = ['benchstay.example.com', 'www.benchstay.example.com', 'localhost']

# Generate a new secret key for production
SECRET_KEY = 'your-secure-secret-key'
```

3. Ensure database migrations are applied:

```cmd
python manage.py migrate
```

### 6. Set File Permissions

Ensure the Apache service has access to the necessary files:

1. Right-click on the `C:\Trae\BenchstayV2` folder
2. Select Properties → Security → Edit
3. Add the user that the Apache service runs as (typically `SYSTEM` or `Network Service`)
4. Grant Read & Execute permissions

### 7. Configure Windows Hosts File

If testing locally, update your hosts file (`C:\Windows\System32\drivers\etc\hosts`):

```
127.0.0.1 benchstay.example.com www.benchstay.example.com
```

### 8. Restart Apache

```cmd
net stop Apache2.4
net start Apache2.4
```

Or use the Apache Monitor in the system tray.

## Troubleshooting

1. Check Apache error logs:

```cmd
type C:\Apache24\logs\error.log
type C:\Apache24\logs\benchstay_error.log
```

2. Verify Apache configuration:

```cmd
C:\Apache24\bin\httpd.exe -t
```

3. Common Windows-specific issues:
   - Path separators (use forward slashes in Apache configs)
   - File permissions
   - Firewall blocking Apache
   - Port conflicts (ensure ports 80 and 443 are available)

## Additional Windows Considerations

1. Configure Apache as a Windows service with automatic startup
2. Consider using a tool like XAMPP for easier management
3. Ensure Windows Firewall allows traffic on ports 80 and 443
4. For production, consider using a reverse proxy like Nginx in front of Apache