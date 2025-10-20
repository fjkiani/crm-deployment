# 🚀 Deploy Voice MVP Now (10 Commands)

## ✅ **Everything is Ready**

- Backend API: ✅ Complete
- Farfalle Tools: ✅ Complete
- Frontend Dashboard: ✅ Complete (680 lines)
- Router Config: ✅ Complete (`/voice` route added)
- Documentation: ✅ Complete (5 comprehensive guides)
- Production Credentials: ✅ Configured

---

## 📦 **What You're Deploying**

### CRM Backend Changes:
```
crm/integrations/twilio/api.py
├─ initiate_outbound_call() - Starts Vapi AI calls
└─ vapi_webhook() - Processes call events
```

### CRM Frontend Changes:
```
frontend/src/router.js
└─ Added /voice route
```

---

## 🎯 **Deploy in 10 Commands (5 mins)**

### Step 1: Push CRM Changes (2 commands)
```bash
cd /Users/fahadkiani/Desktop/development/crm-develop/frappe-bench/apps/crm

# Push to repository
git push origin feat/fix-frappe-modules-import
```

### Step 2: Push Farfalle/Docs Changes (2 commands)
```bash
cd /Users/fahadkiani/Desktop/development/crm-develop/crm-deployment

# Push backend + docs
git push origin main
```

### Step 3: Deploy on Frappe Cloud (Manual - 3 mins)
```
1. Login: https://frappecloud.com/dashboard
2. Navigate to: jedilabs2.v.frappe.cloud
3. Click: "Actions" → "Pull"
4. Wait ~2 mins for pull to complete
5. Click: "Actions" → "Clear Cache"
6. Click: "Actions" → "Restart"
```

### Step 4: Configure Vapi (Manual - 2 mins)
```
1. Login: https://dashboard.vapi.ai
2. Navigate to Morgan agent
3. Add webhook URL:
   https://jedilabs2.v.frappe.cloud/api/method/crm.integrations.twilio.api.vapi_webhook
4. Save
```

### Step 5: Add Site Config (2 commands)
```bash
# SSH to Frappe Cloud or use console
bench --site jedilabs2.v.frappe.cloud set-config vapi_api_key "REDACTED"
bench --site jedilabs2.v.frappe.cloud set-config vapi_agent_id "REDACTED"
```

### Step 6: Test (1 command)
```bash
# Open Voice Dashboard
open https://jedilabs2.v.frappe.cloud/crm/voice
```

---

## 🧪 **Verify Deployment**

### Expected Results:
```
✅ https://jedilabs2.v.frappe.cloud/crm/voice loads
✅ System health cards display
✅ Call history table shows
✅ No console errors
✅ Dashboard auto-refreshes
```

### First Test Call:
```bash
# Via API (replace YOUR_KEY:YOUR_SECRET)
curl -X POST "https://jedilabs2.v.frappe.cloud/api/method/crm.integrations.twilio.api.initiate_outbound_call" \
  -H "Content-Type: application/json" \
  -H "Authorization: token YOUR_KEY:YOUR_SECRET" \
  -d '{
    "to_number": "+13476842656",
    "topic": "Production Test",
    "context": "Testing Voice MVP"
  }'
```

---

## 📊 **Post-Deployment Checklist**

- [ ] Voice Dashboard loads at `/crm/voice`
- [ ] System health shows Twilio connected
- [ ] Recent calls table displays (empty is OK)
- [ ] Test call API returns 200
- [ ] Vapi webhook creates CRM Call Log
- [ ] Transcript saved as FCRM Note
- [ ] Dashboard shows new call

---

## 🎉 **You're Live!**

Access your Voice Dashboard:
**https://jedilabs2.v.frappe.cloud/crm/voice**

Test phone number: **+1-347-684-2656**

---

## 📚 **Full Documentation**

- **Complete Guide**: `VOICE_MVP_READY.md`
- **Frontend Setup**: `FRONTEND_INTEGRATION.md`
- **Deployment Checklist**: `crm-deployment/VOICE_DEPLOYMENT_CHECKLIST.md`
- **Configuration**: `crm-deployment/VAPI_CONFIG.md`
- **Quick Start**: `crm-deployment/scripts/farfalle-main/QUICKSTART.md`

---

## 🆘 **If Something Goes Wrong**

### Dashboard doesn't load:
1. Clear browser cache
2. Check Frappe Cloud logs
3. Verify route in `router.js`
4. Rebuild frontend: `cd apps/crm/frontend && yarn build`

### API returns 404:
1. Verify `api.py` was deployed
2. Check Frappe Cloud pull succeeded
3. Restart site on Frappe Cloud

### Webhook not working:
1. Check Vapi webhook URL configured
2. Verify `vapi_api_key` in site_config
3. Check CRM logs for webhook errors

---

**Need help? All detailed troubleshooting in `VOICE_MVP_READY.md`**

