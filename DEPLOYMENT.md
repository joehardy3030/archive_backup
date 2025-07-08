# Archive Backup System - Production Deployment Guide

This guide covers deploying the Archive Backup System to a production server with the new Archive.org-compliant models.

## 📋 Prerequisites

- **Server**: Ubuntu 20.04+ LTS (recommended)
- **Resources**: 
  - Minimum: 2 CPU cores, 4GB RAM, 100GB storage
  - Recommended: 4+ CPU cores, 8GB+ RAM, 500GB+ storage
- **Network**: Public IP address with domain name
- **Access**: SSH access with sudo privileges

## 🚀 Quick Deployment

For automated deployment, run the provided script:

```bash
# 1. Copy files to your server
scp -r . user@your-server:/tmp/archive_backup

# 2. SSH to your server
ssh user@your-server

# 3. Run deployment script
cd /tmp/archive_backup
./deploy.sh
```

## 📝 Manual Deployment Steps

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib redis-server nginx supervisor git curl wget
```

### 2. Create Application User

```bash
sudo useradd -r -s /bin/bash -d /var/lib/archive_backup archive
sudo mkdir -p /var/lib/archive_backup
sudo mkdir -p /var/log/archive_backup
sudo chown -R archive:archive /var/lib/archive_backup /var/log/archive_backup
```

### 3. Set Up Application

```bash
# Copy application code
sudo cp -r . /var/lib/archive_backup/
sudo chown -R archive:archive /var/lib/archive_backup

# Set up Python environment
sudo -u archive python3 -m venv /var/lib/archive_backup/venv
sudo -u archive /var/lib/archive_backup/venv/bin/pip install -r /var/lib/archive_backup/requirements.txt
```

### 4. Configure Database

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE archive_backup_prod;
CREATE USER archive_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE archive_backup_prod TO archive_user;
\\q
```

### 5. Environment Configuration

```bash
# Copy and edit environment file
sudo -u archive cp /var/lib/archive_backup/.env.production /var/lib/archive_backup/.env

# Edit the environment file with your settings
sudo -u archive nano /var/lib/archive_backup/.env
```

**Required changes in `.env`:**
- `DATABASE_URL`: Update with your PostgreSQL credentials
- `SECRET_KEY`: Generate a strong secret key
- Storage paths (if different from defaults)

### 6. Database Migration

```bash
cd /var/lib/archive_backup
sudo -u archive /var/lib/archive_backup/venv/bin/flask db upgrade
```

### 7. Set Up Services

#### Gunicorn Service

```bash
sudo cp /var/lib/archive_backup/systemd/archive_backup.service /etc/systemd/system/
sudo systemctl enable archive_backup
sudo systemctl start archive_backup
```

#### Celery Worker Service

```bash
sudo cp /var/lib/archive_backup/systemd/archive_backup_worker.service /etc/systemd/system/
sudo systemctl enable archive_backup_worker
sudo systemctl start archive_backup_worker
```

### 8. Configure Nginx

```bash
# Copy Nginx configuration
sudo cp /var/lib/archive_backup/nginx.conf /etc/nginx/sites-available/archive_backup
sudo ln -s /etc/nginx/sites-available/archive_backup /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Update domain name in config
sudo nano /etc/nginx/sites-available/archive_backup

# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx
```

## 🔒 Security Configuration

### 1. SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

### 2. Firewall

```bash
# Configure UFW
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 3. System Security

```bash
# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Restart SSH
sudo systemctl restart ssh
```

## 📊 Monitoring & Maintenance

### Service Status

```bash
# Check application status
sudo systemctl status archive_backup
sudo systemctl status archive_backup_worker

# View logs
sudo journalctl -u archive_backup -f
sudo journalctl -u archive_backup_worker -f
```

### Application Logs

```bash
# Application logs
sudo tail -f /var/log/archive_backup/app.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Database Backup

Automated daily backups are set up via cron:

```bash
# Manual backup
sudo -u archive /var/lib/archive_backup/backup_db.sh

# View backup files
ls -la /var/lib/archive_backup/backups/
```

### Health Checks

```bash
# Application health
curl http://localhost:5000/health

# Database connectivity
sudo -u archive psql -h localhost -U archive_user -d archive_backup_prod -c "SELECT 1;"
```

## 🔄 Updates & Deployment

### Updating the Application

```bash
# 1. Backup current version
sudo -u archive cp -r /var/lib/archive_backup/app /var/lib/archive_backup/app.backup.$(date +%Y%m%d)

# 2. Update code
sudo -u archive git pull  # or copy new files

# 3. Update dependencies
sudo -u archive /var/lib/archive_backup/venv/bin/pip install -r requirements.txt

# 4. Run migrations
sudo -u archive /var/lib/archive_backup/venv/bin/flask db upgrade

# 5. Restart services
sudo systemctl restart archive_backup
sudo systemctl restart archive_backup_worker
```

### Rolling Back

```bash
# Stop services
sudo systemctl stop archive_backup archive_backup_worker

# Restore backup
sudo -u archive rm -rf /var/lib/archive_backup/app
sudo -u archive mv /var/lib/archive_backup/app.backup.YYYYMMDD /var/lib/archive_backup/app

# Restart services
sudo systemctl start archive_backup archive_backup_worker
```

## 🐳 Docker Deployment (Alternative)

For containerized deployment, see the included `docker-compose.yml`:

```bash
# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Scale workers
docker-compose up -d --scale worker=3
```

## 📈 Performance Tuning

### Database Optimization

```sql
-- PostgreSQL configuration recommendations
-- Add to /etc/postgresql/*/main/postgresql.conf

shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
```

### Application Scaling

- **Horizontal scaling**: Add more Gunicorn workers
- **Background tasks**: Scale Celery workers
- **Database**: Use connection pooling (PgBouncer)
- **Caching**: Add Redis caching for API responses

## 🆘 Troubleshooting

### Common Issues

1. **Service won't start**: Check logs with `journalctl -u archive_backup`
2. **Database connection failed**: Verify credentials in `.env`
3. **Permission denied**: Check file ownership and permissions
4. **Nginx 502 error**: Ensure Gunicorn is running on correct port
5. **Storage errors**: Verify storage directories exist and are writable

### Support

- **Logs**: `/var/log/archive_backup/`
- **Configuration**: `/var/lib/archive_backup/.env`
- **Service status**: `systemctl status archive_backup`
- **Health check**: `curl http://localhost:5000/health`

## 📋 Production Checklist

- [ ] Server provisioned with adequate resources
- [ ] Domain name configured and DNS pointing to server
- [ ] SSL certificate installed and configured
- [ ] Firewall configured (UFW)
- [ ] Database created with secure credentials
- [ ] Environment variables configured
- [ ] Database migrations completed
- [ ] Services enabled and running
- [ ] Nginx configured and running
- [ ] Backup system configured
- [ ] Monitoring and logging set up
- [ ] Health checks passing
- [ ] Security hardening completed