# Frappe CRM Development Setup Guide

This comprehensive guide covers the complete setup of a Frappe CRM development environment on macOS, including all the components, configurations, and troubleshooting steps we used.

## 📋 Table of Contents

1. [System Prerequisites](#system-prerequisites)
2. [Database Setup (MySQL/MariaDB)](#database-setup-mysqlmariadb)
3. [Redis Setup](#redis-setup)
4. [Python Environment](#python-environment)
5. [Frappe Bench Installation](#frappe-bench-installation)
6. [CRM App Development](#crm-app-development)
7. [Local Development Server](#local-development-server)
8. [Frappe Cloud Deployment](#frappe-cloud-deployment)
9. [Troubleshooting](#troubleshooting)
10. [Common Commands Reference](#common-commands-reference)

## 🖥️ System Prerequisites

### Install Homebrew (macOS Package Manager)
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Add Homebrew to PATH (usually added automatically)
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc
```

### Install Required System Packages
```bash
# Install MariaDB (MySQL-compatible database)
brew install mariadb

# Install Redis (caching and background jobs)
brew install redis

# Install Node.js (for frontend assets)
brew install node

# Install Yarn (package manager for Node.js)
brew install yarn

# Install Python 3.10+ (if not already installed)
brew install python@3.10

# Install Git (version control)
brew install git

# Install pkg-config (needed for some Python packages)
brew install pkg-config
```

### Verify Installations
```bash
# Check versions
python3 --version
node --version
yarn --version
git --version
brew --version

# Check Homebrew packages
brew list
```

## 🗄️ Database Setup (MySQL/MariaDB)

### Start MariaDB Service
```bash
# Start MariaDB service
brew services start mariadb

# Verify service is running
brew services list | grep mariadb

# Secure MariaDB installation (optional but recommended)
sudo mysql_secure_installation
```

### Configure MariaDB Root User
```bash
# Connect to MariaDB as root
sudo mysql -u root

# In MySQL prompt, set root password and create user
ALTER USER 'root'@'localhost' IDENTIFIED BY 'your_root_password';
CREATE USER 'fahadkiani'@'localhost' IDENTIFIED BY '';
GRANT ALL PRIVILEGES ON *.* TO 'fahadkiani'@'localhost' WITH GRANT OPTION;
FLUSH PRIVILEGES;
EXIT;
```

### Test Database Connection
```bash
# Test connection with new user
mysql -u fahadkiani -e "SELECT VERSION();"

# Create test database
mysql -u fahadkiani -e "CREATE DATABASE test_crm;"
mysql -u fahadkiani -e "SHOW DATABASES;"
```

## 🔴 Redis Setup

### Start Redis Services
```bash
# Start Redis cache service
brew services start redis

# Verify Redis is running
brew services list | grep redis

# Test Redis connection
redis-cli ping
# Should return: PONG
```

### Configure Redis for Frappe
Redis will run on default ports:
- Cache: Port 6379
- Queue: Port 6380 (configured by Frappe Bench)

## 🐍 Python Environment

### Install Python Dependencies
```bash
# Install pipx for isolated Python tool installation
brew install pipx
pipx ensurepath

# Restart terminal or source shell profile
source ~/.zshrc

# Install Frappe Bench using pipx
pipx install frappe-bench

# Verify bench installation
bench --version
```

### Create Virtual Environment (Optional)
```bash
# Create Python virtual environment
python3 -m venv frappe-env

# Activate virtual environment
source frappe-env/bin/activate

# Install additional dependencies if needed
pip install wheel setuptools
```

## 🔧 Frappe Bench Installation

### Initialize New Frappe Bench
```bash
# Create new bench directory
mkdir ~/frappe-bench
cd ~/frappe-bench

# Initialize bench with Python 3
bench init frappe-bench --python python3

# Change to bench directory
cd frappe-bench
```

### Configure Bench Environment
```bash
# Set up environment variables
export PATH="$HOME/.local/bin:$PATH"

# Verify bench commands work
bench --help
bench doctor
```

### Install Frappe Framework
```bash
# Get Frappe framework (version 15)
bench get-app frappe https://github.com/frappe/frappe.git --branch version-15

# Verify frappe app is installed
bench list-apps
```

## 📱 CRM App Development

### Get CRM App Source
```bash
# Clone CRM app from GitHub
bench get-app crm https://github.com/frappe/crm.git

# Verify CRM app is installed
bench list-apps
```

### Create Development Site
```bash
# Create new site for development
bench new-site crm.localhost --db-name crm_db --install-app crm

# Verify site creation
bench list-sites
```

### Configure Site Settings
```bash
# Access site configuration
bench --site crm.localhost console

# In Python console:
site_config = frappe.get_site_config()
print(site_config)
exit()
```

## 🌐 Local Development Server

### Start Development Server
```bash
# Method 1: Use bench start (requires process manager)
bench start

# Method 2: Use bench serve (simpler for development)
bench serve --port 8000
```

### Install Process Manager (For bench start)
```bash
# Install honcho (process manager for bench start)
source env/bin/activate
pip install honcho
```

### Access Development Site
```bash
# Open in browser
open http://crm.localhost:8000

# Or access via IP
open http://localhost:8000

# CRM specific URL
open http://crm.localhost:8000/crm
```

### Development Workflow
```bash
# Make changes to CRM app code
# Restart development server
bench restart

# Clear cache if needed
bench --site crm.localhost clear-cache

# Run migrations if schema changes
bench --site crm.localhost migrate
```

## ☁️ Frappe Cloud Deployment

### Prepare Deployment Repository
```bash
# Create deployment directory
cd /path/to/crm-develop
mkdir crm-deployment
cd crm-deployment

# Copy CRM app files only (no frappe framework)
cp -r ../frappe-bench/apps/crm/crm .

# Create essential packaging files
# setup.py, pyproject.toml, requirements.txt, MANIFEST.in
```

### Repository Structure for Frappe Cloud
```
crm-deployment/
├── crm/                    # CRM app code
├── setup.py               # Python packaging
├── pyproject.toml         # Modern Python metadata
├── requirements.txt       # Dependencies
├── MANIFEST.in           # Package data inclusion
├── README.md             # Documentation
└── .gitignore           # Git ignore rules
```

### Deploy to Frappe Cloud
1. **Create GitHub Repository**
   ```bash
   # Initialize git
   git init
   git add .
   git commit -m "Initial CRM deployment setup"

   # Create GitHub repo and push
   git remote add origin https://github.com/yourusername/crm-deployment.git
   git push -u origin main
   ```

2. **Deploy on Frappe Cloud**
   - Go to [Frappe Cloud](https://frappecloud.com)
   - Create new site
   - Select "Deploy from Git"
   - Choose your repository
   - Deploy!

3. **Access Deployed Application**
   - CRM Interface: `https://yoursite.frappe.cloud/crm`
   - Admin Panel: `https://yoursite.frappe.cloud`
   - API: `https://yoursite.frappe.cloud/api/`

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. "No process manager found" Error
```bash
# Install honcho
source env/bin/activate
pip install honcho

# Or use bench serve instead
bench serve --port 8000
```

#### 2. MySQL Connection Issues
```bash
# Check MySQL service
brew services list | grep mariadb

# Restart MySQL service
brew services restart mariadb

# Test connection
mysql -u fahadkiani -e "SELECT 1;"

# Reset permissions if needed
sudo mysql -u root
GRANT ALL PRIVILEGES ON *.* TO 'fahadkiani'@'localhost';
FLUSH PRIVILEGES;
```

#### 3. Redis Connection Issues
```bash
# Check Redis service
brew services list | grep redis

# Restart Redis
brew services restart redis

# Test connection
redis-cli ping
```

#### 4. Site Migration Issues
```bash
# Run migrations
bench --site crm.localhost migrate

# Clear cache
bench --site crm.localhost clear-cache

# Rebuild assets
bench --site crm.localhost build
```

#### 5. Permission Issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER ~/frappe-bench

# Fix database permissions
mysql -u fahadkiani -e "GRANT ALL ON crm_db.* TO 'fahadkiani'@'localhost';"
```

### Debug Commands
```bash
# Check bench status
bench doctor

# View site configuration
bench --site crm.localhost show-config

# View installed apps
bench --site crm.localhost list-apps

# Check site logs
tail -f ~/frappe-bench/sites/crm.localhost/logs/web.log
```

## 📚 Common Commands Reference

### Bench Commands
```bash
# Initialize new bench
bench init frappe-bench

# Get app
bench get-app crm https://github.com/frappe/crm.git

# Create new site
bench new-site crm.localhost

# Install app on site
bench --site crm.localhost install-app crm

# Start development server
bench start
bench serve --port 8000

# Stop server
bench stop

# Clear cache
bench --site crm.localhost clear-cache

# Run migrations
bench --site crm.localhost migrate
```

### MySQL Commands
```bash
# Connect to database
mysql -u fahadkiani

# Show databases
SHOW DATABASES;

# Create database
CREATE DATABASE crm_db;

# Show tables
USE crm_db;
SHOW TABLES;

# Backup database
mysqldump -u fahadkiani crm_db > backup.sql

# Restore database
mysql -u fahadkiani crm_db < backup.sql
```

### Redis Commands
```bash
# Connect to Redis
redis-cli

# Check connection
PING

# View all keys
KEYS *

# Clear all data
FLUSHALL

# View Redis info
INFO
```

### Git Commands
```bash
# Initialize repository
git init

# Add files
git add .

# Commit changes
git commit -m "Initial commit"

# Push to GitHub
git remote add origin https://github.com/username/repo.git
git push -u origin main

# Pull changes
git pull origin main
```

## 🎯 Development Best Practices

### Code Organization
- Keep CRM app code in `crm/` directory
- Use proper Python package structure
- Follow Frappe naming conventions
- Document your code

### Version Control
- Use meaningful commit messages
- Create feature branches for development
- Test changes before committing
- Keep sensitive data out of version control

### Database Management
- Use migrations for schema changes
- Backup database regularly
- Test migrations on staging first
- Document database changes

### Performance Optimization
- Use Redis for caching
- Optimize database queries
- Minimize frontend assets
- Monitor resource usage

## 📞 Support and Resources

### Official Documentation
- [Frappe Framework Docs](https://frappeframework.com/docs)
- [Frappe Cloud Docs](https://frappecloud.com/docs)
- [CRM App Docs](https://github.com/frappe/crm)

### Community Resources
- [Frappe Community Forum](https://discuss.frappe.io)
- [GitHub Issues](https://github.com/frappe/frappe/issues)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/frappe)

### Getting Help
1. Check this guide first
2. Search existing issues
3. Ask on community forum
4. Create GitHub issue if needed

---

## ✅ Quick Setup Checklist

- [ ] Homebrew installed
- [ ] MariaDB/Redis/Node.js/Yarn installed
- [ ] Python 3.10+ available
- [ ] Frappe Bench installed
- [ ] Bench initialized
- [ ] CRM app installed
- [ ] Development site created
- [ ] Server running
- [ ] Can access CRM interface

**Congratulations! You now have a fully functional Frappe CRM development environment!** 🚀

---

*This guide was created based on our successful Frappe CRM deployment experience. Last updated: $(date)*

