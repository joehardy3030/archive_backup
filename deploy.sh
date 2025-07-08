#!/bin/bash

# Archive Backup System Deployment Script
# This script deploys the Archive Backup System to a production server

set -e  # Exit on any error

echo "🚀 Starting Archive Backup System Deployment..."

# Configuration
APP_NAME="archive_backup"
APP_USER="archive"
APP_DIR="/var/lib/archive_backup"
LOG_DIR="/var/log/archive_backup"
SYSTEMD_SERVICE="/etc/systemd/system/archive_backup.service"
NGINX_CONFIG="/etc/nginx/sites-available/archive_backup"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   print_status "Please run as a regular user with sudo privileges"
   exit 1
fi

# Update system packages
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies
print_status "Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    supervisor \
    git \
    curl \
    wget

# Create application user
print_status "Creating application user..."
if ! id "$APP_USER" &>/dev/null; then
    sudo useradd -r -s /bin/bash -d $APP_DIR $APP_USER
    print_status "Created user: $APP_USER"
else
    print_warning "User $APP_USER already exists"
fi

# Create application directories
print_status "Creating application directories..."
sudo mkdir -p $APP_DIR
sudo mkdir -p $LOG_DIR
sudo mkdir -p $APP_DIR/storage/metadata
sudo mkdir -p $APP_DIR/storage/files
sudo chown -R $APP_USER:$APP_USER $APP_DIR
sudo chown -R $APP_USER:$APP_USER $LOG_DIR

# Clone/copy application code
print_status "Setting up application code..."
if [ -d "$APP_DIR/app" ]; then
    print_warning "Application directory exists, backing up..."
    sudo -u $APP_USER mv $APP_DIR/app $APP_DIR/app.backup.$(date +%Y%m%d_%H%M%S)
fi

# Copy current directory to app directory
sudo -u $APP_USER cp -r . $APP_DIR/
sudo chown -R $APP_USER:$APP_USER $APP_DIR

# Set up Python virtual environment
print_status "Setting up Python virtual environment..."
sudo -u $APP_USER python3 -m venv $APP_DIR/venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt

# Set up PostgreSQL database
print_status "Setting up PostgreSQL database..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user (you'll need to set password manually)
sudo -u postgres psql -c "CREATE DATABASE archive_backup_prod;" || print_warning "Database may already exist"
sudo -u postgres psql -c "CREATE USER archive_user WITH PASSWORD 'your_secure_password_here';" || print_warning "User may already exist"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE archive_backup_prod TO archive_user;" || print_warning "Privileges may already be granted"

# Set up environment file
print_status "Setting up environment configuration..."
sudo -u $APP_USER cp $APP_DIR/.env.production $APP_DIR/.env
print_warning "Please edit $APP_DIR/.env with your production settings"

# Run database migrations
print_status "Running database migrations..."
cd $APP_DIR
sudo -u $APP_USER $APP_DIR/venv/bin/flask db upgrade

# Set up systemd service
print_status "Setting up systemd service..."
sudo tee $SYSTEMD_SERVICE > /dev/null <<EOF
[Unit]
Description=Archive Backup System
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=notify
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --config gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Set up Celery worker service (for background tasks)
print_status "Setting up Celery worker service..."
sudo tee /etc/systemd/system/archive_backup_worker.service > /dev/null <<EOF
[Unit]
Description=Archive Backup Celery Worker
After=network.target redis.service
Wants=redis.service

[Service]
Type=forking
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/celery -A app.celery worker --loglevel=info --pidfile=/tmp/celery.pid --detach
ExecStop=/bin/kill -s TERM \$MAINPID
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Set up Nginx configuration
print_status "Setting up Nginx configuration..."
sudo cp $APP_DIR/nginx.conf $NGINX_CONFIG
sudo ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/archive_backup
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Enable and start services
print_status "Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable redis-server
sudo systemctl enable postgresql
sudo systemctl enable nginx
sudo systemctl enable archive_backup
sudo systemctl enable archive_backup_worker

sudo systemctl start redis-server
sudo systemctl start postgresql
sudo systemctl start archive_backup
sudo systemctl start archive_backup_worker
sudo systemctl restart nginx

# Set up log rotation
print_status "Setting up log rotation..."
sudo tee /etc/logrotate.d/archive_backup > /dev/null <<EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 0644 $APP_USER $APP_USER
    postrotate
        systemctl reload archive_backup
    endscript
}
EOF

# Create backup script
print_status "Creating backup script..."
sudo tee $APP_DIR/backup_db.sh > /dev/null <<EOF
#!/bin/bash
# Database backup script
BACKUP_DIR="$APP_DIR/backups"
DATE=\$(date +%Y%m%d_%H%M%S)
mkdir -p \$BACKUP_DIR
pg_dump -h localhost -U archive_user archive_backup_prod > \$BACKUP_DIR/archive_backup_\$DATE.sql
gzip \$BACKUP_DIR/archive_backup_\$DATE.sql
# Keep only last 7 days of backups
find \$BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
EOF

sudo chmod +x $APP_DIR/backup_db.sh
sudo chown $APP_USER:$APP_USER $APP_DIR/backup_db.sh

# Add daily backup cron job
print_status "Setting up daily database backup..."
(sudo -u $APP_USER crontab -l 2>/dev/null; echo "0 2 * * * $APP_DIR/backup_db.sh") | sudo -u $APP_USER crontab -

print_status "Deployment completed successfully! 🎉"
echo
print_warning "IMPORTANT: Please complete these manual steps:"
echo "1. Edit $APP_DIR/.env with your production settings"
echo "2. Update PostgreSQL password in the environment file"
echo "3. Generate a strong SECRET_KEY and update the environment file"
echo "4. Update the domain name in $NGINX_CONFIG"
echo "5. Set up SSL certificates (Let's Encrypt recommended)"
echo "6. Configure firewall (ufw) to allow ports 80 and 443"
echo "7. Test the application at http://your-domain.com"
echo
print_status "Service status:"
sudo systemctl status archive_backup --no-pager -l
echo
print_status "View logs with: sudo journalctl -u archive_backup -f"
print_status "Application directory: $APP_DIR"
print_status "Log directory: $LOG_DIR"