# Voice MVP Quick Start Guide

## 🎯 You Have Everything You Need!

All credentials are configured. Just need 2 things from you:

### 1. Your Vapi API Key
Get it from: https://dashboard.vapi.ai/account
- Look for "API Keys" section
- Copy the key (starts with `sk_live_` or `sk_test_`)

### 2. Your Frappe Admin Password
For: `https://jedilabs2.v.frappe.cloud`
- Your login password for the CRM

---

## ⚡ 5-Minute Setup

### Step 1: Copy and Configure Environment
```bash
cd /Users/fahadkiani/Desktop/development/crm-develop/crm-deployment/scripts/farfalle-main

# Copy template to actual .env
cp .env-template .env

# Edit the .env file and replace ONLY these 3 values:
# 1. VAPI_API_KEY=your_vapi_api_key_here  → paste your Vapi key
# 2. CRM_PASSWORD=your_frappe_admin_password_here  → paste your Frappe password
# 3. WHITELISTED_NUMBERS=+1234567890  → add YOUR phone number for testing
```

### Step 2: Start the Voice Server
```bash
# Activate virtual environment
source venv/bin/activate

# Start server
uvicorn simple_voice_server:app --reload --port 8000
```

Server should start at: `http://localhost:8000`

### Step 3: Test It Works
```bash
# In a new terminal, test health check:
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"...","components":{...}}
```

---

## 🧪 Your First Test Call

### Option A: Test with curl (Quick Smoke Test)
```bash
# Replace +1234567890 with YOUR whitelisted number
curl -X POST "http://localhost:8000/voice/initiate-call" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1234567890",
    "topic": "Test call from Voice MVP"
  }'
```

**Expected**: Your phone rings with a call from `+18559173947`

### Option B: Test with Dashboard Data (Verify CRM Connection)
```bash
curl http://localhost:8000/voice/dashboard-data
```

**Expected**: JSON with call statistics (will be empty if no calls yet)

---

## 📊 What's Already Configured

### ✅ Twilio (Production Ready)
- Account SID: `AC2122c6579ed1b5ffd03f4ba8912ccd94`
- Phone Number: `+18559173947`
- **Status**: Fully configured, ready to make calls

### ✅ Vapi AI Agent (Morgan)
- Agent ID: `0e006140-2a20-47d4-a899-b20bd636e51a`
- Agent Name: Morgan (GrowthPartners Sales Agent)
- Voice: Elliot (Vapi)
- Model: GPT-4o
- **Status**: Configured, just needs your API key

### ✅ Frappe CRM
- Site: `https://jedilabs2.v.frappe.cloud`
- **Status**: Ready to log calls, just needs your password

### ⚠️ Safety Controls (Active)
- **Sandbox Mode**: ON (prevents accidental calls)
- **Live Calls**: OFF (must whitelist numbers)
- **Whitelisted Numbers**: Empty (add yours!)

---

## 🔐 Security Note

**NEVER commit `.env` to git!** It contains:
- Real Twilio credentials
- Your Vapi API key
- Your Frappe password

The `.env` file is already in `.gitignore`.

---

## 🚀 Next Steps After First Test

### 1. Set Up Public Webhooks (for full features)
```bash
# Install ngrok if you don't have it
brew install ngrok

# Expose port 8000
ngrok http 8000

# Copy the https URL (e.g., https://abc123.ngrok.io)
```

Update your `.env`:
```bash
WEBHOOK_BASE_URL=https://abc123.ngrok.io
```

### 2. Configure Twilio Webhooks
Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming

Select your number: `+18559173947`

**Voice Configuration**:
- When a call comes in: `https://your-ngrok-url.ngrok.io/webhooks/twilio/voice`
- Method: `HTTP POST`

**Status Callbacks**:
- Status Callback URL: `https://your-ngrok-url.ngrok.io/webhooks/twilio/status`
- Method: `HTTP POST`

### 3. Configure Vapi Webhooks
Go to: https://dashboard.vapi.ai/assistants

Select Morgan agent, then Settings:
- Webhook URL: `https://your-ngrok-url.ngrok.io/webhooks/vapi`
- Events: `call.started`, `transcript.chunk`, `call.ended`, `call.summary`

### 4. CRM Twilio Settings
Go to: https://jedilabs2.v.frappe.cloud

Navigate to: **CRM Settings > Integrations > Twilio Settings**

Fill in:
- Account SID: `AC2122c6579ed1b5ffd03f4ba8912ccd94`
- Auth Token: `6f7d3dabb35074c50581f0a621d4e96f`
- Phone Number: `+18559173947`
- Enable Integration: ✅

---

## 🐛 Troubleshooting

### "Connection refused" error
- Make sure Farfalle server is running: `uvicorn simple_voice_server:app --reload --port 8000`
- Check port 8000 isn't already in use: `lsof -i :8000`

### "Number not whitelisted" error
- Update `WHITELISTED_NUMBERS` in `.env` with your phone number
- Restart the server after changing `.env`

### "CRM connection failed"
- Verify `CRM_PASSWORD` in `.env` is correct
- Test CRM access: `curl https://jedilabs2.v.frappe.cloud/api/method/ping`

### Phone doesn't ring
- Check Twilio account has credit
- Verify phone number format: must include `+` and country code (e.g., `+1234567890`)
- Check Twilio console for call logs: https://console.twilio.com/us1/monitor/logs/calls

---

## 📞 Support Contacts

**Twilio Console**: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
**Vapi Dashboard**: https://dashboard.vapi.ai
**Frappe CRM**: https://jedilabs2.v.frappe.cloud

---

## 🎉 You're Ready!

All the hard work is done. Just:
1. Get your Vapi API key
2. Add your Frappe password
3. Add your phone number
4. Start the server
5. Make a test call

**Good luck! 🚀**

