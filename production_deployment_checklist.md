# BenchstayV2 Production Deployment Checklist

This checklist covers all the necessary steps to deploy the BenchstayV2 application to a production environment.

## Pre-Deployment Preparation

- [ ] Create a backup of the development database
- [ ] Run all tests and ensure they pass
- [ ] Create a `.env` file from the `.env.template` with actual production values
- [ ] Generate and set a new secure `SECRET_KEY` in the `.env` file
- [ ] Set `DEBUG=False` in production settings
- [ ] Configure proper `ALLOWED_HOSTS` with your domain and server IP
- [ ] Update database credentials in the `.env` file
- [ ] Configure email settings in the `.env` file
- [ ] Set up Redis for caching

## Server Setup

- [ ] Install required system packages:
  ```bash
  sudo apt update
  sudo apt install python3 python3-pip python3-venv postgresql postgresql-contrib nginx redis-server
  ```
- [ ] Create a dedicated user for the application:
  ```bash
  sudo adduser benchstay
  sudo usermod -aG sudo benchstay
  ```
- [ ] Create application directory:
  ```bash
  sudo mkdir -p /opt/BenchstayV2
  sudo chown benchstay:benchstay /opt/BenchstayV2
  ```

## Database Setup

- [ ] Create PostgreSQL database and user:
  ```bash
  sudo -u postgres psql
  CREATE DATABASE benchstay;
  CREATE USER benchstaydbuser WITH PASSWORD 'secure_password_here';
  ALTER ROLE benchstaydbuser SET client_encoding TO 'utf8';
  ALTER ROLE benchstaydbuser SET default_transaction_isolation TO 'read committed';
  ALTER ROLE benchstaydbuser SET timezone TO 'UTC';
  GRANT ALL PRIVILEGES ON DATABASE benchstay TO benchstaydbuser;
  \q
  ```

## Application Deployment

- [ ] Clone the repository to the server:
  ```bash
  cd /opt/BenchstayV2
  git clone https://github.com/your-username/BenchstayV2.git .
  ```
- [ ] Create and activate a virtual environment:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- [ ] Install dependencies:
  ```bash
  pip install -r requirements.txt
  pip install gunicorn psycopg2-binary
  ```
- [ ] Copy the `.env` file to the server
- [ ] Create necessary directories:
  ```bash
  mkdir -p /opt/BenchstayV2/staticfiles
  mkdir -p /opt/BenchstayV2/media
  mkdir -p /opt/BenchstayV2/logs
  ```
- [ ] Apply migrations:
  ```bash
  python manage.py migrate --settings=benchstay.settings_production
  ```
- [ ] Collect static files:
  ```bash
  python manage.py collectstatic --no-input --settings=benchstay.settings_production
  ```
- [ ] Create a superuser:
  ```bash
  python manage.py createsuperuser --settings=benchstay.settings_production
  ```

## Web Server Configuration

- [ ] Set up Gunicorn service:
  ```bash
  sudo nano /etc/systemd/system/gunicorn_benchstay.service
  ```
  Add the following content:
  ```ini
  [Unit]
  Description=gunicorn daemon for BenchstayV2
  After=network.target

  [Service]
  User=benchstay
  Group=www-data
  WorkingDirectory=/opt/BenchstayV2
  EnvironmentFile=/opt/BenchstayV2/.env
  ExecStart=/opt/BenchstayV2/venv/bin/gunicorn --workers 3 --bind unix:/opt/BenchstayV2/benchstay.sock benchstay.wsgi:application
  Restart=on-failure

  [Install]
  WantedBy=multi-user.target
  ```

- [ ] Start and enable Gunicorn service:
  ```bash
  sudo systemctl start gunicorn_benchstay
  sudo systemctl enable gunicorn_benchstay
  ```

- [ ] Configure Nginx:
  ```bash
  sudo nano /etc/nginx/sites-available/benchstay
  ```
  Add the following content:
  ```nginx
  server {
      listen 80;
      server_name your-domain.com www.your-domain.com;

      location = /favicon.ico { access_log off; log_not_found off; }

      location /static/ {
          root /opt/BenchstayV2;
      }

      location /media/ {
          root /opt/BenchstayV2;
      }

      location / {
          include proxy_params;
          proxy_pass http://unix:/opt/BenchstayV2/benchstay.sock;
      }
  }
  ```

- [ ] Enable the Nginx site:
  ```bash
  sudo ln -s /etc/nginx/sites-available/benchstay /etc/nginx/sites-enabled
  sudo nginx -t
  sudo systemctl restart nginx
  ```

## SSL Configuration

- [ ] Install Certbot:
  ```bash
  sudo apt install certbot python3-certbot-nginx
  ```

- [ ] Obtain SSL certificate:
  ```bash
  sudo certbot --nginx -d your-domain.com -d www.your-domain.com
  ```

- [ ] Verify auto-renewal:
  ```bash
  sudo certbot renew --dry-run
  ```

## Post-Deployment Verification

- [ ] Check application logs for errors:
  ```bash
  tail -f /opt/BenchstayV2/logs/django.log
  ```

- [ ] Verify the site is accessible via HTTPS
- [ ] Test all critical functionality
- [ ] Verify static files are being served correctly
- [ ] Verify media uploads are working
- [ ] Check admin interface functionality
- [ ] Verify database connections and queries
- [ ] Test caching functionality

## Security Checks

- [ ] Ensure firewall is properly configured:
  ```bash
  sudo ufw allow 'Nginx Full'
  sudo ufw allow ssh
  sudo ufw enable
  sudo ufw status
  ```

- [ ] Set up automatic security updates:
  ```bash
  sudo apt install unattended-upgrades
  sudo dpkg-reconfigure -plow unattended-upgrades
  ```

- [ ] Check file permissions:
  ```bash
  sudo chown -R benchstay:www-data /opt/BenchstayV2
  sudo chmod -R 755 /opt/BenchstayV2
  sudo chmod -R 750 /opt/BenchstayV2/media
  ```

## Backup Configuration

- [ ] Set up database backups:
  ```bash
  sudo mkdir -p /opt/backups/benchstay
  sudo chown benchstay:benchstay /opt/backups/benchstay
  ```

- [ ] Create a backup script:
  ```bash
  sudo nano /opt/BenchstayV2/backup.sh
  ```
  Add the following content:
  ```bash
  #!/bin/bash
  DATE=$(date +%Y-%m-%d_%H-%M-%S)
  BACKUP_DIR="/opt/backups/benchstay"
  
  # Database backup
  pg_dump -U benchstaydbuser -h localhost benchstay > "$BACKUP_DIR/benchstay_db_$DATE.sql"
  
  # Media files backup
  tar -czf "$BACKUP_DIR/benchstay_media_$DATE.tar.gz" -C /opt/BenchstayV2 media
  
  # Remove backups older than 30 days
  find "$BACKUP_DIR" -type f -name "benchstay_*" -mtime +30 -delete
  ```

- [ ] Make the script executable and set up a cron job:
  ```bash
  sudo chmod +x /opt/BenchstayV2/backup.sh
  sudo crontab -e
  ```
  Add the following line:
  ```
  0 2 * * * /opt/BenchstayV2/backup.sh
  ```

## Monitoring Setup

- [ ] Install monitoring tools:
  ```bash
  sudo apt install htop iotop fail2ban
  ```

- [ ] Configure fail2ban for additional security
- [ ] Consider setting up a monitoring service like Prometheus, Grafana, or a simpler solution like Monit

## Final Steps

- [ ] Document the deployment process and server configuration
- [ ] Create a disaster recovery plan
- [ ] Set up regular maintenance schedule
- [ ] Train team members on deployment and maintenance procedures