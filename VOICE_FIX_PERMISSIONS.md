# 🔧 Fix "Invalid page or not permitted to access" Error

## ❌ **The Problem**

You're getting `"Invalid page or not permitted to access"` because:

1. ✅ The route exists in code (`/voice`)
2. ✅ The component exists in code (`VoiceDashboard.vue`)
3. ❌ **The frontend hasn't been built on Frappe Cloud yet**

**Result**: Router can't find the component → shows error page

---

## ✅ **The Solution: Build Frontend on Frappe Cloud**

### **Option 1: Via Frappe Cloud Console** (Easiest)

1. **Go to Frappe Cloud**:
   ```
   https://frappecloud.com/dashboard
   → Select your site: jedilabs2
   ```

2. **Open Site Console**:
   ```
   Click "Console" or "Terminal" button
   ```

3. **Run Build Commands**:
   ```bash
   cd /home/frappe/frappe-bench/apps/crm/frontend
   yarn install  # Install any new dependencies
   yarn build    # Build the frontend
   ```

4. **Clear Cache & Restart**:
   ```bash
   cd /home/frappe/frappe-bench
   bench clear-cache
   bench restart
   ```

5. **Test**:
   ```
   Visit: https://jedilabs2.v.frappe.cloud/crm/voice
   Should work now! ✅
   ```

---

### **Option 2: Via SSH** (If you have SSH access)

1. **SSH into Frappe Cloud**:
   ```bash
   ssh frappe@jedilabs2.frappe.cloud
   # Or whatever your SSH credentials are
   ```

2. **Navigate to Frontend**:
   ```bash
   cd /home/frappe/frappe-bench/apps/crm/frontend
   ```

3. **Build**:
   ```bash
   yarn install
   yarn build
   ```

4. **Restart**:
   ```bash
   cd /home/frappe/frappe-bench
   bench clear-cache
   bench restart
   ```

5. **Exit and Test**:
   ```bash
   exit
   # Then visit https://jedilabs2.v.frappe.cloud/crm/voice
   ```

---

### **Option 3: Via Frappe Cloud "Pull & Deploy"** (Automated)

If you've pushed the frontend changes to GitHub:

1. **In Frappe Cloud Dashboard**:
   ```
   Your Site → Deploy → Pull from GitHub
   ```

2. **Select Branch**:
   ```
   Choose: main (or your current branch)
   ```

3. **Wait for Deploy**:
   ```
   Frappe Cloud will:
   - Pull latest code
   - Run `yarn build` automatically
   - Restart services
   ```

4. **Test**:
   ```
   Visit: https://jedilabs2.v.frappe.cloud/crm/voice
   ```

---

## 🔍 **Verify Before Building**

Check if the files exist on Frappe Cloud:

```bash
# SSH into server, then:
ls -la /home/frappe/frappe-bench/apps/crm/frontend/src/pages/VoiceDashboard.vue
ls -la /home/frappe/frappe-bench/apps/crm/frontend/src/router.js
```

**Expected**:
- ✅ `VoiceDashboard.vue` should exist (680 lines)
- ✅ `router.js` should have `/voice` route (line 27-30)

**If files missing**:
- You need to push code to GitHub first
- Or upload files directly (see below)

---

## 📤 **If Files Are Missing on Cloud**

### **Quick Upload via SCP**:

```bash
# From your local machine:
cd /Users/fahadkiani/Desktop/development/crm-develop

# Upload VoiceDashboard.vue
scp frappe-bench/apps/crm/frontend/src/pages/VoiceDashboard.vue \
  frappe@jedilabs2.frappe.cloud:/home/frappe/frappe-bench/apps/crm/frontend/src/pages/

# Upload router.js
scp frappe-bench/apps/crm/frontend/src/router.js \
  frappe@jedilabs2.frappe.cloud:/home/frappe/frappe-bench/apps/crm/frontend/src/
```

**Then SSH in and build**:
```bash
ssh frappe@jedilabs2.frappe.cloud
cd /home/frappe/frappe-bench/apps/crm/frontend
yarn build
cd ../..
bench clear-cache
bench restart
```

---

## 🔍 **Debug: Check Build Output**

After running `yarn build`, verify the files were created:

```bash
cd /home/frappe/frappe-bench/apps/crm/frontend/dist
ls -la assets/

# Should see new .js and .css files with recent timestamps
```

**Check if CRM is using the built files**:
```bash
cd /home/frappe/frappe-bench/apps/crm/public
ls -la js/

# Should see built assets here
```

---

## 🚨 **Common Build Errors**

### **Error: "yarn: command not found"**
```bash
# Install yarn
npm install -g yarn

# Or use npm instead
npm run build
```

### **Error: "Module not found"**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json yarn.lock
yarn install
yarn build
```

### **Error: "Out of memory"**
```bash
# Increase Node memory
export NODE_OPTIONS="--max-old-space-size=4096"
yarn build
```

### **Error: "Permission denied"**
```bash
# Fix permissions
cd /home/frappe/frappe-bench/apps/crm/frontend
sudo chown -R frappe:frappe .
chmod -R 755 .
yarn build
```

---

## 🎯 **After Build Success**

### **1. Verify Route Works**:
```bash
# From Frappe Cloud console:
bench console

# In Python console:
import frappe
frappe.init(site='jedilabs2.v.frappe.cloud')
frappe.connect()

# Check if app is installed
frappe.get_installed_apps()
# Should include 'crm'
```

### **2. Check Frontend Build**:
```bash
# List built assets
ls -la /home/frappe/frappe-bench/sites/assets/crm/frontend/
# Should see VoiceDashboard component in bundle
```

### **3. Test in Browser**:
```
1. Clear browser cache (Cmd+Shift+R on Mac)
2. Visit: https://jedilabs2.v.frappe.cloud/crm/voice
3. Open DevTools Console (F12)
4. Check for JavaScript errors
```

---

## 🔐 **Permissions Check**

If page loads but shows "Not permitted":

### **Check User Permissions**:
```bash
# In bench console:
bench console

# Check your role
frappe.get_roles('Fahad@jedilabs.org')

# Should include at least one of:
# - System Manager
# - Sales Manager
# - Sales User
```

### **Grant Access** (if needed):
```python
# In bench console:
frappe.init(site='jedilabs2.v.frappe.cloud')
frappe.connect()

# Add role to your user
frappe.get_doc('User', 'Fahad@jedilabs.org').add_roles('Sales Manager')
frappe.db.commit()
```

---

## 📋 **Complete Checklist**

- [ ] Files exist on Frappe Cloud
  - [ ] `VoiceDashboard.vue` present
  - [ ] `router.js` updated with `/voice` route
  
- [ ] Frontend built successfully
  - [ ] `cd frontend && yarn build` completed
  - [ ] No build errors
  - [ ] Assets in `dist/` folder
  
- [ ] Cache cleared
  - [ ] `bench clear-cache` run
  - [ ] Browser cache cleared
  
- [ ] Services restarted
  - [ ] `bench restart` completed
  - [ ] All services running
  
- [ ] User has permissions
  - [ ] Has Sales Manager or System Manager role
  - [ ] Can access other CRM pages
  
- [ ] Page loads
  - [ ] No 404 error
  - [ ] No "Invalid page" error
  - [ ] Dashboard visible

---

## 🎊 **Expected Result**

After successful build, visiting:
```
https://jedilabs2.v.frappe.cloud/crm/voice
```

Should show:
```
┌─────────────────────────────────────────────────┐
│  Voice Operations Dashboard                     │
├─────────────────────────────────────────────────┤
│  System Health: ✓ Twilio ✓ Vapi ✓ CRM          │
├─────────────────────────────────────────────────┤
│  Call Statistics & Recent Calls                 │
└─────────────────────────────────────────────────┘
```

---

## 🆘 **Still Not Working?**

### **Check Frappe Logs**:
```bash
tail -f /home/frappe/frappe-bench/logs/web.log
tail -f /home/frappe/frappe-bench/sites/jedilabs2.v.frappe.cloud/logs/error.log
```

### **Check Browser Console**:
```
F12 → Console tab
Look for errors like:
- "Failed to fetch component"
- "Module not found"
- "Route not found"
```

### **Verify Backend API**:
```bash
curl -X POST https://jedilabs2.v.frappe.cloud/api/method/crm.integrations.twilio.api.initiate_outbound_call \
  -H "Content-Type: application/json" \
  -d '{"to_number": "+13476842656"}'

# Should NOT return 404
```

---

## 🚀 **Quick Fix Summary**

**90% of the time, this is the fix**:

```bash
# SSH into Frappe Cloud
ssh frappe@jedilabs2.frappe.cloud

# Build frontend
cd /home/frappe/frappe-bench/apps/crm/frontend
yarn build

# Restart
cd /home/frappe/frappe-bench
bench clear-cache
bench restart

# Done! Test at https://jedilabs2.v.frappe.cloud/crm/voice
```

That's it! The build creates the JavaScript bundle that includes your Voice Dashboard component.



