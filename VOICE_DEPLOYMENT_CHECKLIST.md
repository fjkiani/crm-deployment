# Voice MVP Deployment Checklist

## 🎯 Complete End-to-End Setup Guide

### Phase 1: CRM Backend Deployment (15 mins)

#### Step 1: Deploy Code to Frappe Cloud
```bash
cd /Users/fahadkiani/Desktop/development/crm-develop/crm-deployment

# Commit the new voice endpoints
git add crm/integrations/twilio/api.py
git commit -m "feat: Add Vapi voice integration endpoints

- initiate_outbound_call: Create calls via Vapi AI
- vapi_webhook: Handle call events and transcripts
- Auto-create Call Logs, Notes, and ToDos"

# Push to repository
git push origin main
```

#### Step 2: Pull Changes in Frappe Cloud
1. Go to: https://frappecloud.com/dashboard/sites/jedilabs2
2. Click "Pull" or "Deploy" to update the site
3. Wait for deployment to complete (~2-3 mins)

#### Step 3: Add Vapi Configuration
```bash
# Option A: Via Frappe Cloud Console
bench --site jedilabs2.v.frappe.cloud set-config vapi_api_key "53593b76-8c70-46e2-b01a-d2996afec5ba"
bench --site jedilabs2.v.frappe.cloud set-config vapi_agent_id "0e006140-2a20-47d4-a899-b20bd636e51a"

# Option B: Edit site_config.json directly
# Add to /home/frappe/frappe-bench/sites/jedilabs2.v.frappe.cloud/site_config.json:
{
  "vapi_api_key": "53593b76-8c70-46e2-b01a-d2996afec5ba",
  "vapi_agent_id": "0e006140-2a20-47d4-a899-b20bd636e51a"
}
```

#### Step 4: Verify CRM Endpoints
```bash
# Test initiate_outbound_call endpoint
curl -X POST https://jedilabs2.v.frappe.cloud/api/method/crm.integrations.twilio.api.initiate_outbound_call \
  -H "Authorization: token <your_api_key>" \
  -d "to_number=+13476842656&topic=Test"

# Expected: {success: true, call_sid: "...", message: "Call initiated"}
```

---

### Phase 2: Vapi Agent Configuration (5 mins)

#### Step 1: Configure Webhook in Vapi Dashboard
1. Go to: https://dashboard.vapi.ai
2. Select your agent: **Morgan** (ID: 0e006140-2a20-47d4-a899-b20bd636e51a)
3. Navigate to "Webhooks" section
4. Add webhook URL:
   ```
   https://jedilabs2.v.frappe.cloud/api/method/crm.integrations.twilio.api.vapi_webhook
   ```
5. Select events:
   - ✅ call.started
   - ✅ call.ended
   - ✅ call.completed
   - ✅ transcript.update (optional)

#### Step 2: Test Webhook
```bash
# Vapi will send test event when you save the webhook
# Check CRM logs to verify receipt:
# Error Log → "Vapi Webhook" entries
```

---

### Phase 3: Farfalle Server Setup (Already Done! ✅)

#### Verify Farfalle is Running
```bash
cd /Users/fahadkiani/Desktop/development/crm-develop/crm-deployment/scripts/farfalle-main

# Check if server is running
curl http://localhost:8000/health
# Expected: {"status": "healthy", "service": "voice-mvp"}

# Check CRM connection
curl http://localhost:8000/voice/dashboard-data
# Expected: {"status": "success", "data": {...}}
```

#### Environment Variables (Already Configured! ✅)
```bash
# Verify .env has all credentials
grep -E "^VAPI_|^CRM_|^TWILIO_" .env

# Should show:
# VAPI_API_KEY=53593b76-8c70-46e2-b01a-d2996afec5ba
# VAPI_AGENT_ID=0e006140-2a20-47d4-a899-b20bd636e51a  
# CRM_BASE_URL=https://jedilabs2.v.frappe.cloud
# CRM_USER=Fahad@jedilabs.org
# CRM_PASSWORD=Kiani11209!
# TWILIO_PHONE_NUMBER=+18559173947
```

---

### Phase 4: End-to-End Test (5 mins)

#### Test 1: Initiate Call via Farfalle
```bash
# Make a real call to your test number
curl -X POST "http://localhost:8000/voice/initiate-call?phone=%2B13476842656&topic=Voice%20MVP%20Test&context=Testing%20integration" 

# Expected response:
# {
#   "status": "success",
#   "call_sid": "vapi-call-id",
#   "call_log_id": "CRM-CALL-00001",
#   "message": "Call initiated successfully"
# }
```

#### Test 2: Verify in CRM
1. Log into: https://jedilabs2.v.frappe.cloud
2. Navigate to: **CRM → Call Logs**
3. Find the new call log:
   - Status: "in-progress"
   - To: +1-347-684-2656
   - Medium: "Vapi AI"
   - Provider Call ID: (Vapi call ID)

#### Test 3: Verify Call Completion
1. Answer your phone when Vapi calls
2. Have a brief conversation with Morgan
3. After call ends, check CRM again:
   - Call Log status: "completed"
   - Duration: calculated
   - New **FCRM Note** created with transcript
   - New **ToDo** created (if keywords detected)

#### Test 4: Dashboard Analytics
```bash
# Check dashboard data
curl http://localhost:8000/voice/dashboard-data | python3 -m json.tool

# Expected:
# {
#   "total_calls": 1,
#   "completed": 1,
#   "recent_calls": [...]
# }
```

---

### Phase 5: Frontend Integration (Optional - 10 mins)

#### Add Voice Dashboard Route
Edit: `frappe-bench/apps/crm/frontend/src/router.js`

```javascript
{
  path: '/voice',
  name: 'Voice Dashboard',
  component: () => import('@/pages/VoiceDashboard.vue'),
  meta: {
    requiresAuth: true,
    title: 'Voice Operations'
  }
}
```

#### Update Navigation
Add to CRM sidebar:
```javascript
{
  label: 'Voice',
  icon: 'phone',
  to: '/voice'
}
```

---

### Phase 6: Production Deployment (When Ready)

#### Deploy Farfalle to Cloud
```bash
# Option A: Deploy to Frappe Cloud (alongside CRM)
# Option B: Deploy to separate service (Heroku, Railway, etc.)
# Option C: Use ngrok for now

# For quick testing with ngrok:
ngrok http 8000

# Update WEBHOOK_BASE_URL in .env to ngrok URL
# Update Vapi webhook to point to ngrok URL
```

---

## 🎉 Success Criteria

### You're Done When:
- ✅ CRM endpoints deployed and accessible
- ✅ Vapi webhook configured and receiving events
- ✅ Farfalle server connects to CRM successfully
- ✅ Test call creates Call Log in CRM
- ✅ Call completion creates Note and ToDo
- ✅ Dashboard shows analytics

---

## 🐛 Troubleshooting

### CRM Endpoints Return 417
**Cause**: Vapi config missing from site_config.json
**Fix**: Add vapi_api_key and vapi_agent_id (see Phase 1, Step 3)

### CRM Authentication Failed
**Cause**: Wrong username/password
**Fix**: Use `Fahad@jedilabs.org` (not "Administrator")

### Webhook Not Receiving Events
**Cause**: Vapi not configured
**Fix**: Add webhook URL in Vapi dashboard (see Phase 2)

### Call Log Not Created
**Cause**: CRM Call Log DocType might need field
**Fix**: Check that "medium" field exists, add if needed

---

## 📞 Test Phone Number
- **Your Test Number**: +1-347-684-2656
- **Twilio Number**: +1-855-917-3947
- **Vapi Agent**: Morgan (Growth Partners)

---

## 🔐 Credentials Summary

```bash
# CRM (Frappe Cloud)
URL: https://jedilabs2.v.frappe.cloud
User: Fahad@jedilabs.org
Password: Kiani11209!

# Vapi
API Key: 53593b76-8c70-46e2-b01a-d2996afec5ba
Agent ID: 0e006140-2a20-47d4-a899-b20bd636e51a

# Twilio
Account SID: AC2122c6579ed1b5ffd03f4ba8912ccd94
Auth Token: 6f7d3dabb35074c50581f0a621d4e96f
Phone: +18559173947
```

---

## 📝 Next Steps After MVP

1. **Security**: Add API key authentication to Farfalle endpoints
2. **Monitoring**: Add Datadog/Sentry for error tracking
3. **Scaling**: Deploy Farfalle to production server
4. **Features**:
   - Call scheduling
   - Bulk calling campaigns
   - Advanced analytics
   - Call recording playback

