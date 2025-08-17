# Configuring Django Settings for IP-Based Hosting

When using an IP address instead of a domain name for your BenchstayV2 application, you need to make specific changes to your Django settings. This guide explains the necessary modifications.

## Update ALLOWED_HOSTS Setting

The most important change is to add your server's IP address to the `ALLOWED_HOSTS` setting in your Django settings file.

1. Open the settings file at `benchstay/settings.py`

2. Locate the `ALLOWED_HOSTS` setting (currently empty):

   ```python
   ALLOWED_HOSTS = []
   ```

3. Add your server's IP address to the list:

   ```python
   ALLOWED_HOSTS = ['your.server.ip.address']
   ```

   Replace `your.server.ip.address` with your actual server IP address (e.g., `192.168.1.100`).

4. If you're deploying to a production environment, also set `DEBUG` to `False`:

   ```python
   DEBUG = False
   ```

## Example Settings for Production

Here's a complete example of the relevant settings for a production deployment using an IP address:

```python
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Add your server's IP address to allowed hosts
ALLOWED_HOSTS = ['192.168.1.100']  # Replace with your actual IP address

# If you need to access the site from localhost during testing
# ALLOWED_HOSTS = ['192.168.1.100', 'localhost', '127.0.0.1']

# Generate a new secure secret key for production
SECRET_KEY = 'your-secure-secret-key-here'

# Configure database settings for production
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

# Static and media files configuration
STATIC_ROOT = '/opt/BenchstayV2/staticfiles'
MEDIA_ROOT = '/opt/BenchstayV2/media'
```

## Special Considerations for IP-Based Hosting

1. **CSRF Protection**: Django's CSRF protection may require additional configuration when using an IP address. If you encounter CSRF errors, you may need to add the following setting:

   ```python
   CSRF_TRUSTED_ORIGINS = ['http://your.server.ip.address']
   ```

2. **Session Cookies**: Some browsers have security restrictions for cookies on IP addresses. You may need to adjust your session settings:

   ```python
   SESSION_COOKIE_SECURE = False  # Set to True only if using HTTPS
   ```

3. **Security Considerations**: IP-based hosting without HTTPS is less secure. Consider this setup only for development or internal testing environments.

## Testing Your Configuration

After updating your settings, restart your Django application and Apache server:

```bash
sudo systemctl restart apache2
```

Then access your application using the IP address in your browser:

```
http://your.server.ip.address/
```