# 🚀 Deploy Voice MVP RIGHT NOW

## ✅ What's Done:
- CRM backend endpoints: **initiate_outbound_call** + **vapi_webhook**
- Farfalle voice server: **Running on port 8000**
- Authentication: **Working with Fahad@jedilabs.org**
- Test phone: **+1-347-684-2656 whitelisted**
- Code: **Committed and ready to push**

---

## 🎯 3-Step Deployment (15 minutes)

### STEP 1: Push to Repository (2 mins)
```bash
cd /Users/fahadkiani/Desktop/development/crm-develop/crm-deployment
git push origin main
```

### STEP 2: Deploy on Frappe Cloud (5 mins)
1. Go to: https://frappecloud.com/dashboard/sites/jedilabs2
2. Click **"Pull"** or **"Deploy"** button
3. Wait for deployment (~2-3 mins)
4. Click **"Site Config"** or open console
5. Add these two lines to `site_config.json`:
   ```json
   {
     "vapi_api_key": "53593b76-8c70-46e2-b01a-d2996afec5ba",
     "vapi_agent_id": "0e006140-2a20-47d4-a899-b20bd636e51a"
   }
   ```
6. Save and restart site

### STEP 3: Configure Vapi Webhook (3 mins)
1. Go to: https://dashboard.vapi.ai
2. Find agent: **Morgan** (ID: `0e006140-2a20-47d4-a899-b20bd636e51a`)
3. Go to **Settings → Webhooks**
4. Add webhook URL:
   ```
   https://jedilabs2.v.frappe.cloud/api/method/crm.integrations.twilio.api.vapi_webhook
   ```
5. Select events:
   - ✅ call.started
   - ✅ call.ended  
   - ✅ call.completed
6. Save

---

## 🧪 Test It (5 mins)

### Test 1: Make a Call
```bash
cd /Users/fahadkiani/Desktop/development/crm-develop/crm-deployment/scripts/farfalle-main

# Initiate call to your phone
curl -X POST "http://localhost:8000/voice/initiate-call?phone=%2B13476842656&topic=Voice%20MVP%20Test&context=Testing%20complete%20integration" 
```

### Test 2: Check CRM
1. Open: https://jedilabs2.v.frappe.cloud
2. Go to: **CRM → Call Logs**
3. See new call log:
   - Status: "in-progress" (then "completed" after call)
   - Medium: "Vapi AI"
   - Your phone number

### Test 3: After Call Ends
Check CRM for:
- ✅ Call Log with duration
- ✅ FCRM Note with transcript
- ✅ ToDo for follow-up (if keywords detected)

---

## 🎉 You're Done When:

- [ ] Code pushed to GitHub
- [ ] Frappe Cloud deployed successfully
- [ ] Vapi webhook configured
- [ ] Test call works
- [ ] Call log appears in CRM
- [ ] Transcript saved as Note
- [ ] ToDo created for follow-up

---

## 🐛 If Something Fails:

### Error: "417 EXPECTATION FAILED"
**Fix**: Add Vapi config to site_config.json (Step 2.5 above)

### Error: "401 UNAUTHORIZED"
**Fix**: Username should be `Fahad@jedilabs.org` not "Administrator"

### Call doesn't appear in CRM
**Fix**: Check webhook is configured in Vapi dashboard

---

## 📞 Ready? Let's Go!

**Everything is ready. Just run Step 1, Step 2, Step 3, and test!**



