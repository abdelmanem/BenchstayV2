# BenchstayV2 Security Best Practices

This document outlines security best practices for the BenchstayV2 application in a production environment.

## Django Security Settings

### Critical Settings

- **DEBUG**: Always set `DEBUG = False` in production to prevent leaking sensitive information.
  ```python
  DEBUG = False
  ```

- **SECRET_KEY**: Use a strong, unique secret key and keep it confidential.
  ```python
  # Store in environment variable, not in code
  SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
  ```

- **ALLOWED_HOSTS**: Explicitly list all domains/IPs that can serve your application.
  ```python
  ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']
  ```

### HTTPS and Cookie Security

- **SECURE_SSL_REDIRECT**: Force HTTPS for all connections.
  ```python
  SECURE_SSL_REDIRECT = True
  ```

- **SESSION_COOKIE_SECURE**: Only send session cookies over HTTPS.
  ```python
  SESSION_COOKIE_SECURE = True
  ```

- **CSRF_COOKIE_SECURE**: Only send CSRF cookies over HTTPS.
  ```python
  CSRF_COOKIE_SECURE = True
  ```

- **SECURE_HSTS_SECONDS**: Implement HTTP Strict Transport Security.
  ```python
  SECURE_HSTS_SECONDS = 31536000  # 1 year
  SECURE_HSTS_INCLUDE_SUBDOMAINS = True
  SECURE_HSTS_PRELOAD = True
  ```

### Content Security

- **SECURE_CONTENT_TYPE_NOSNIFF**: Prevent MIME type sniffing.
  ```python
  SECURE_CONTENT_TYPE_NOSNIFF = True
  ```

- **SECURE_BROWSER_XSS_FILTER**: Enable browser XSS protection.
  ```python
  SECURE_BROWSER_XSS_FILTER = True
  ```

- **X_FRAME_OPTIONS**: Prevent clickjacking attacks.
  ```python
  X_FRAME_OPTIONS = 'DENY'
  ```

## Database Security

- **Use Environment Variables**: Never hardcode database credentials in settings files.
  ```python
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.postgresql',
          'NAME': os.environ.get('DB_NAME'),
          'USER': os.environ.get('DB_USER'),
          'PASSWORD': os.environ.get('DB_PASSWORD'),
          'HOST': os.environ.get('DB_HOST'),
          'PORT': os.environ.get('DB_PORT'),
      }
  }
  ```

- **SSL for Database Connections**: Enable SSL for database connections when possible.
  ```python
  'OPTIONS': {
      'sslmode': 'require',
  }
  ```

- **Least Privilege**: Database user should have only the permissions it needs.
  ```sql
  -- Example: Grant only necessary permissions
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO benchstaydbuser;
  ```

## File Upload Security

- **Validate File Types**: Always validate uploaded file types and content.

- **Limit File Size**: Set maximum upload size to prevent DoS attacks.
  ```python
  DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
  FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
  ```

- **Secure File Permissions**: Set proper permissions for uploaded files.
  ```python
  FILE_UPLOAD_PERMISSIONS = 0o644
  FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755
  ```

## Authentication and Authorization

- **Strong Password Policy**: Enforce strong passwords.
  ```python
  AUTH_PASSWORD_VALIDATORS = [
      {
          'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
      },
      {
          'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
          'OPTIONS': {
              'min_length': 10,
          }
      },
      {
          'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
      },
      {
          'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
      },
  ]
  ```

- **Session Security**: Configure secure session settings.
  ```python
  SESSION_COOKIE_AGE = 86400  # 1 day in seconds
  SESSION_COOKIE_SECURE = True
  SESSION_COOKIE_HTTPONLY = True
  ```

- **Rate Limiting**: Implement rate limiting for login attempts to prevent brute force attacks.

## Server Security

### Firewall Configuration

- Only open necessary ports (typically 80, 443, and SSH).
  ```bash
  sudo ufw allow 'Nginx Full'
  sudo ufw allow ssh
  sudo ufw enable
  ```

### Regular Updates

- Keep the server OS and all software up to date.
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```

- Configure automatic security updates.
  ```bash
  sudo apt install unattended-upgrades
  sudo dpkg-reconfigure -plow unattended-upgrades
  ```

### Secure SSH

- Disable root login and password authentication.
  ```bash
  # Edit /etc/ssh/sshd_config
  PermitRootLogin no
  PasswordAuthentication no
  ```

- Use SSH key authentication only.

### Fail2Ban

- Install and configure Fail2Ban to protect against brute force attacks.
  ```bash
  sudo apt install fail2ban
  ```

## Application Security

### Input Validation

- Always validate and sanitize user input.
- Use Django forms and model validation.
- Implement CSRF protection for all forms.

### SQL Injection Prevention

- Use Django ORM and parameterized queries.
- Avoid raw SQL when possible.
- If raw SQL is necessary, use prepared statements.

### XSS Prevention

- Use Django's template system which automatically escapes variables.
- For JavaScript-heavy applications, consider using Content Security Policy (CSP).

### CSRF Protection

- Ensure CSRF protection is enabled for all POST requests.
  ```python
  MIDDLEWARE = [
      # ...
      'django.middleware.csrf.CsrfViewMiddleware',
      # ...
  ]
  ```

## Dependency Security

- Regularly update dependencies to patch security vulnerabilities.
  ```bash
  pip install --upgrade pip
  pip install --upgrade -r requirements.txt
  ```

- Use tools like `safety` to check for known vulnerabilities.
  ```bash
  pip install safety
  safety check
  ```

## Logging and Monitoring

- Configure comprehensive logging.
  ```python
  LOGGING = {
      'version': 1,
      'disable_existing_loggers': False,
      'handlers': {
          'file': {
              'level': 'WARNING',
              'class': 'logging.handlers.RotatingFileHandler',
              'filename': '/opt/BenchstayV2/logs/django.log',
              'maxBytes': 10485760,  # 10MB
              'backupCount': 10,
          },
          'mail_admins': {
              'level': 'ERROR',
              'class': 'django.utils.log.AdminEmailHandler',
          }
      },
      'loggers': {
          'django': {
              'handlers': ['file'],
              'level': 'WARNING',
              'propagate': True,
          },
          'django.request': {
              'handlers': ['mail_admins'],
              'level': 'ERROR',
              'propagate': False,
          },
      },
  }
  ```

- Monitor for suspicious activity.
- Set up alerts for security events.

## Backup and Recovery

- Implement regular automated backups.
- Test backup restoration procedures.
- Store backups securely, preferably off-site.

## Security Headers

- Implement security headers in your web server configuration.
  ```nginx
  # Nginx example
  add_header X-Content-Type-Options "nosniff";
  add_header X-Frame-Options "DENY";
  add_header X-XSS-Protection "1; mode=block";
  add_header Content-Security-Policy "default-src 'self';";
  add_header Referrer-Policy "strict-origin-when-cross-origin";
  ```

## Regular Security Audits

- Conduct regular security audits of your application.
- Consider using automated security scanning tools.
- Stay informed about security best practices and vulnerabilities.

## Incident Response Plan

1. **Preparation**: Document security procedures and contacts.
2. **Detection**: Monitor logs and alerts for security incidents.
3. **Containment**: Isolate affected systems to prevent further damage.
4. **Eradication**: Remove the cause of the breach.
5. **Recovery**: Restore systems to normal operation.
6. **Lessons Learned**: Document the incident and improve security measures.

## Additional Resources

- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top Ten](https://owasp.org/www-project-top-ten/)
- [Mozilla Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)