# Frappe CRM Deployment

This repository contains a Frappe CRM application ready for deployment on Frappe Cloud.

## 🚀 Quick Deploy to Frappe Cloud

### ✅ **Repository Status: READY FOR DEPLOYMENT**
- **GitHub Repository**: https://github.com/fjkiani/crm-deployment
- **Branch**: main
- **Apps**: crm v1.0.0, frappe v15.0.0
- **Compatibility**: ✅ pyproject.toml files included

### Step 1: Access Frappe Cloud
1. Go to **[Frappe Cloud Dashboard](https://frappecloud.com/dashboard)**
2. Sign in to your account (or create a free account)

### Step 2: Create New Site
1. Click **"New Site"** or **"Create Site"**
2. Choose your plan:
   - **Free Tier**: 1GB database, 10GB bandwidth (perfect for testing!)
   - **Starter**: $10/month - 5GB database, 100GB bandwidth
   - **Professional**: $25/month - 25GB database, 100GB bandwidth

### Step 3: Deploy from Git
1. Select **"Deploy from Git"** option
2. Connect your GitHub account (if not connected)
3. Select repository: **`fjkiani/crm-deployment`**
4. Select branch: **`main`**
5. Click **"Deploy"**

### Step 4: Access Your CRM
After deployment completes (usually 5-10 minutes):
- **CRM Interface**: `https://YOUR_SITE_NAME.frappe.cloud/crm`
- **Admin Panel**: `https://YOUR_SITE_NAME.frappe.cloud`
- **API Endpoints**: `https://YOUR_SITE_NAME.frappe.cloud/api/`

## 📱 Features Included

- ✅ **Lead Management** - Track and manage potential customers
- ✅ **Deal Pipeline (Kanban)** - Visual sales pipeline management
- ✅ **Contact Management** - Comprehensive contact database
- ✅ **Task Management** - Assign and track tasks
- ✅ **WhatsApp Integration** - Connect with customers via WhatsApp
- ✅ **Email Integration** - Send and receive emails
- ✅ **Call Logging** - Track all customer interactions
- ✅ **Customizable Dashboards** - Real-time analytics and reporting
- ✅ **Mobile Responsive** - Works perfectly on all devices

## 🛠 Technical Details

### Apps Included
- **crm v1.0.0**: The CRM application with all features
- **frappe v15.0.0**: The Frappe framework (latest stable version)

### Dependencies
- **Python**: >= 3.10
- **Database**: MariaDB/MySQL
- **Cache**: Redis
- **Web Server**: Gunicorn

### Build System
- **Build Backend**: setuptools
- **Package Management**: pyproject.toml (modern Python packaging)
- **Requirements**: All dependencies included

## 🔧 Development Setup (Local)

If you want to develop locally:

```bash
# Clone the repository
git clone https://github.com/fjkiani/crm-deployment.git
cd crm-deployment

# Install frappe-bench
pip install frappe-bench

# Initialize bench
bench init frappe-bench

# Get apps
cd frappe-bench
bench get-app crm ../crm
bench get-app frappe ../frappe

# Create site
bench new-site crm.localhost
```

## 📞 Support & Documentation

- [Frappe Cloud Documentation](https://frappecloud.com/docs)
- [Frappe Framework Docs](https://frappeframework.com/docs)
- [CRM App Repository](https://github.com/frappe/crm)
- [Frappe Community Forum](https://discuss.frappe.io)

## 📝 License

This project is licensed under the MIT License - see the LICENSE files for details.