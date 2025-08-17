# BenchstayV2 Production Deployment

This document provides an overview of the production-ready configuration for the BenchstayV2 application.

## Production Files

The following files have been created or modified for production deployment:

1. **`benchstay/settings_production.py`**: Production-ready Django settings with security configurations.
2. **`benchstay/wsgi_production.py`**: WSGI configuration for production.
3. **`.env.template`**: Template for environment variables (copy to `.env` and fill in values).
4. **`production_deployment_checklist.md`**: Comprehensive checklist for deployment.
5. **`security_best_practices.md`**: Security guidelines for production environment.
6. **`gunicorn_config.py`**: Optimized Gunicorn configuration for production.

## Key Features

### Security Enhancements

- Secure Django settings with `DEBUG=False`
- New randomly generated `SECRET_KEY`
- HTTPS enforcement with HSTS
- Secure cookie settings
- XSS and CSRF protection
- Content security headers
- SQL injection prevention
- File upload security

### Performance Optimizations

- Database connection pooling
- Redis caching configuration
- Static file serving optimization
- Gunicorn worker configuration
- Compression and browser caching

### Deployment Infrastructure

- PostgreSQL database configuration
- Gunicorn application server
- Nginx web server setup
- SSL/TLS with Let's Encrypt
- Systemd service configuration

### Monitoring and Maintenance

- Comprehensive logging setup
- Automated database backups
- Media file backups
- Security monitoring
- Update procedures

## Deployment Process

Follow these steps to deploy the application to production:

1. **Prepare Environment**:
   - Create a `.env` file from `.env.template`
   - Set all required environment variables

2. **Server Setup**:
   - Follow the `production_deployment_checklist.md` for detailed steps
   - Set up the server, database, and web server

3. **Application Deployment**:
   - Deploy the code to the server
   - Install dependencies
   - Apply migrations
   - Collect static files

4. **Security Configuration**:
   - Follow `security_best_practices.md` for security hardening
   - Set up SSL/TLS
   - Configure firewall

5. **Monitoring and Backup**:
   - Set up logging
   - Configure automated backups
   - Implement monitoring

## Environment Variables

The following environment variables should be set in the `.env` file:

```
DJANGO_SECRET_KEY=your_secret_key
DJANGO_SETTINGS_MODULE=benchstay.settings_production
DB_NAME=Benchstay
DB_USER=Benchstaydbuser
DB_PASSWORD=secure_password_here
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/1
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_password
DEFAULT_FROM_EMAIL=noreply@your-domain.com
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-server-ip
```

## Maintenance

Regular maintenance tasks include:

1. **Database Backups**: Automated daily backups
2. **Security Updates**: Keep the system and dependencies updated
3. **Log Rotation**: Ensure logs don't fill up disk space
4. **Performance Monitoring**: Monitor application performance
5. **SSL Certificate Renewal**: Ensure SSL certificates are renewed

## Troubleshooting

Common issues and solutions:

1. **Application Not Loading**: Check Gunicorn and Nginx logs
2. **Database Connection Issues**: Verify database credentials and connection
3. **Static Files Not Loading**: Check file permissions and Nginx configuration
4. **SSL Certificate Problems**: Verify certificate renewal and configuration

## Support

For additional support, refer to:

- Django Documentation: https://docs.djangoproject.com/
- Gunicorn Documentation: https://docs.gunicorn.org/
- Nginx Documentation: https://nginx.org/en/docs/
- PostgreSQL Documentation: https://www.postgresql.org/docs/