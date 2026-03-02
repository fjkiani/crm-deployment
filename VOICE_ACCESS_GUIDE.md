# 🎙️ How to Access Your Voice Dashboard

## 🌐 **Direct URL Access** (Easiest)

### Production (Frappe Cloud):
```
https://jedilabs2.v.frappe.cloud/crm/voice
```

### Local Development:
```
http://localhost:8080/voice
```

**Just paste this URL in your browser!** ✅

---

## 🧭 **Add to Sidebar Navigation** (Optional)

Currently, the Voice Dashboard route exists but isn't in the sidebar menu. Here's how to add it:

### **File to Edit**:
```
frappe-bench/apps/crm/frontend/src/components/Layouts/AppSidebar.vue
```

### **What to Add** (Lines 209-260):

**BEFORE** (Current):
```vue
const links = [
  {
    label: 'Dashboard',
    icon: LucideLayoutDashboard,
    to: 'Dashboard',
  },
  {
    label: 'Leads',
    icon: LeadsIcon,
    to: 'Leads',
  },
  {
    label: 'Deals',
    icon: DealsIcon,
    to: 'Deals',
  },
  // ... rest of links
]
```

**AFTER** (Add Voice):
```vue
const links = [
  {
    label: 'Dashboard',
    icon: LucideLayoutDashboard,
    to: 'Dashboard',
  },
  {
    label: 'Voice',           // ← ADD THIS
    icon: PhoneIcon,          // ← Uses existing PhoneIcon
    to: 'Voice Dashboard',    // ← Route name from router.js
  },
  {
    label: 'Leads',
    icon: LeadsIcon,
    to: 'Leads',
  },
  // ... rest of links
]
```

### **Steps**:
1. Open `AppSidebar.vue`
2. Find the `links` array (around line 209)
3. Add the Voice object after Dashboard
4. Save and rebuild: `cd frontend && yarn build`
5. Restart bench

**Note**: `PhoneIcon` is already imported in the file, so no additional imports needed!

---

## 📱 **What You'll See**

### **System Health Panel**:
```
┌─────────────────────────────────────────────────┐
│  System Health                                  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐  │
│  │Twilio  │ │Vapi AI │ │CRM     │ │Farfalle│  │
│  │✓ OK    │ │✓ OK    │ │✓ OK    │ │✓ OK    │  │
│  └────────┘ └────────┘ └────────┘ └────────┘  │
└─────────────────────────────────────────────────┘
```

### **Call Statistics**:
```
Total Calls: 156
Active Calls: 2
Success Rate: 94.2%
Avg Duration: 3m 42s
Total Duration: 9h 23m
```

### **Recent Calls Table**:
```
Time     | From          | To            | Status    | Duration
---------|---------------|---------------|-----------|----------
10:34 AM | +1-855-917... | +1-347-684... | Completed | 4m 12s
10:12 AM | +1-855-917... | +1-212-555... | Completed | 2m 38s
09:45 AM | +1-855-917... | +1-646-321... | Missed    | 0m 00s
```

### **Call Details Modal**:
Click any call to see:
- Full transcript
- Call recordings (if enabled)
- Notes created during call
- Follow-up tasks generated
- Linked CRM records (Lead/Deal/Contact)

---

## 🎯 **Quick Test Checklist**

After deployment, verify:

### **1. Dashboard Loads** ✅
```
Visit: https://jedilabs2.v.frappe.cloud/crm/voice
Expected: Dashboard appears with health indicators
```

### **2. System Health Shows Connected** ✅
```
Check: All 4 systems show green/connected
- Twilio: ✓ Connected
- Vapi AI: ✓ Connected
- CRM: ✓ Healthy
- Farfalle: ✓ Online
```

### **3. Can View Call History** ✅
```
Check: Recent Calls table populated
Should show: Existing CRM Call Logs if any
```

### **4. Can Initiate Test Call** ✅
```
Action: Use "Initiate Call" button
Enter: +1-347-684-2656 (your test number)
Expected: Call placed via Vapi/Twilio
```

### **5. Webhooks Working** ✅
```
After call ends:
- Check CRM Call Log created
- Check FCRM Note with transcript
- Check ToDo for follow-up (if action items detected)
```

---

## 🔧 **Troubleshooting**

### **Dashboard Not Loading**:
```bash
# Check if frontend was built
cd frappe-bench/apps/crm/frontend
yarn build

# Restart bench
bench restart
```

### **404 Error**:
```bash
# Verify route exists
grep -r "path: '/voice'" frappe-bench/apps/crm/frontend/src/router.js

# Should show:
# path: '/voice',
# name: 'Voice Dashboard',
```

### **Component Not Found**:
```bash
# Verify component exists
ls -la frappe-bench/apps/crm/frontend/src/pages/VoiceDashboard.vue

# Should exist (680 lines)
```

### **System Health Shows Offline**:

**Twilio Offline**:
```bash
# Check CRM Twilio Settings
Visit: https://jedilabs2.v.frappe.cloud/app/crm-twilio-settings

# Verify credentials:
Account SID: AC2122c6579ed1b5ffd03f4ba8912ccd94
Auth Token: (check if set)
Phone Number: +18559173947
```

**Vapi AI Offline**:
```bash
# Check site_config.json
bench set-config vapi_api_key "53593b76-8c70-46e2-b01a-d2996afec5ba"
bench set-config vapi_agent_id "0e006140-2a20-47d4-a899-b20bd636e51a"
```

**Farfalle Offline**:
```bash
# Farfalle server not required for basic voice features
# Voice calls work directly: CRM → Vapi → Twilio
# Farfalle only needed for advanced analytics
```

---

## 🚀 **Next Steps After Accessing**

### **1. Configure Vapi Webhook** (CRITICAL):
```
Vapi Dashboard → Your Agent → Server URL:
https://jedilabs2.v.frappe.cloud/api/method/crm.integrations.twilio.api.vapi_webhook
```

### **2. Test First Call**:
```
1. Open Voice Dashboard
2. Click "Initiate Call" (if button exists)
3. Or use CRM Contact → "Call" button
4. Dial: +1-347-684-2656
5. Verify:
   - Call connects
   - Transcript appears in dashboard
   - CRM Call Log created
   - Note added to contact
```

### **3. Monitor Call Quality**:
```
- Watch "Active Calls" counter
- Check success rate percentage
- Review call durations
- Verify webhook activity
```

---

## 📊 **Dashboard Features Available**

### **Real-Time Monitoring**:
- ✅ Active call counter
- ✅ System health indicators
- ✅ Auto-refresh every 30 seconds

### **Call Analytics**:
- ✅ Total calls count
- ✅ Success rate percentage
- ✅ Average call duration
- ✅ Total talk time

### **Call History**:
- ✅ Recent calls table
- ✅ Call status (completed/missed/failed)
- ✅ Click for full details
- ✅ View transcript
- ✅ See linked records

### **Safety Controls**:
- ✅ Sandbox mode indicator
- ✅ Whitelisted numbers display
- ✅ Live calls toggle status

### **Debug Console**:
- ✅ Webhook activity log
- ✅ API call history
- ✅ Error messages
- ✅ Integration status

---

## 🎯 **Alternative Access Methods**

### **Method 1: Direct URL** (Recommended)
```
https://jedilabs2.v.frappe.cloud/crm/voice
```
✅ Works immediately, no code changes needed

### **Method 2: Add to Workspace** (Advanced)
Edit CRM workspace to include Voice link:
```
Visit: https://jedilabs2.v.frappe.cloud/app/workspace/CRM
Add custom link to Voice Dashboard
```

### **Method 3: Create Desk Shortcut** (Advanced)
Add Voice Dashboard to desk shortcuts via:
```
Site: Customize Workspace
Add: Voice Dashboard custom route
```

### **Method 4: Sidebar Link** (Requires Build)
See instructions above to add to AppSidebar.vue

---

## 📝 **Important Notes**

1. **Voice Dashboard is DEPLOYED** ✅
   - Route configured in router.js
   - Component exists (680 lines)
   - Just needs direct URL access

2. **No Additional Code Required** ✅
   - Everything already deployed
   - Frontend built
   - Backend API ready

3. **Sidebar Link is OPTIONAL** ⏳
   - Not required for functionality
   - Just adds convenience
   - Can be added later

4. **Farfalle Not Required** ℹ️
   - Voice calls work without it
   - Direct integration: CRM ↔ Vapi ↔ Twilio
   - Farfalle only for advanced features

---

## 🎊 **You're Ready!**

**Just visit**: `https://jedilabs2.v.frappe.cloud/crm/voice`

The dashboard should load immediately. If not, check the troubleshooting section above.

**Enjoy your Voice MVP!** 🚀



