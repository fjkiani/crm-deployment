# Voice MVP Testing Guide

## 🚀 Quick Start Testing

### 1. Environment Setup

Create `.env` file in `crm-deployment/scripts/farfalle-main/`:

```bash
# === REQUIRED FOR TESTING ===

# CRM Integration (MUST HAVE)
CRM_BASE_URL=https://your-site.frappe.cloud
CRM_USER=your_username@domain.com
CRM_PASSWORD=your_password

# Basic LLM (for Farfalle backend)
GEMINI_API_KEY=your_gemini_key_here

# Database (SQLite for local testing)
DATABASE_URL=sqlite:///./farfalle_test.db
DB_ENABLED=true

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000

# === OPTIONAL FOR VOICE ===

# Vapi (only if testing AI voice)
VAPI_API_KEY=your_vapi_key_here
VAPI_AGENT_ID=your_vapi_agent_id

# Safety Settings
VOICE_SANDBOX=true
ALLOW_LIVE_CALLS=false
WHITELISTED_NUMBERS=+1234567890

# Webhook URL (use ngrok for testing)
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok.io

# === OPTIONAL FOR INTELLIGENCE ===
TAVILY_API_KEY=your_tavily_key
```

### 2. Start Farfalle Backend

```bash
cd crm-deployment/scripts/farfalle-main
poetry install
poetry run uvicorn backend.main:app --reload --port 8000
```

### 3. Test CRM Connection

```bash
# Test basic CRM connection
curl -X GET http://localhost:8000/voice/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "crm": "healthy",
    "twilio": "unknown",
    "vapi": "unknown"
  }
}
```

## 🧪 Testing Scenarios

### Scenario 1: Basic Voice Call Initiation

```bash
# Test call initiation
curl -X POST http://localhost:8000/voice/initiate \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1234567890",
    "topic": "Test call from Voice MVP",
    "context": "Testing the integration"
  }'
```

**Expected Result:**
- ✅ Call initiated via CRM Twilio API
- ✅ CRM Call Log created
- ✅ Response includes `call_sid` and `call_log_name`

### Scenario 2: Contextual Call with Company Intel

```bash
# Test contextual call
curl -X POST http://localhost:8000/voice/call-with-context \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1234567890",
    "company": "Abbey Capital",
    "contact_name": "John Smith",
    "include_intel": true
  }'
```

**Expected Result:**
- ✅ Call initiated with context
- ✅ Pre-call context generated
- ✅ CRM Call Log includes company and contact info

### Scenario 3: Voice Dashboard Data

```bash
# Test dashboard data
curl -X GET http://localhost:8000/voice/dashboard
```

**Expected Result:**
```json
{
  "success": true,
  "dashboard_data": {
    "total_calls": 5,
    "active_calls": 1,
    "recent_calls": [...],
    "analytics": {
      "success_rate": 80.0,
      "average_duration": 120.5
    }
  }
}
```

### Scenario 4: CRM Voice Dashboard UI

1. **Start CRM Development Server:**
```bash
cd frappe-bench
bench serve --port 8001
```

2. **Navigate to Voice Dashboard:**
```
http://localhost:8001/crm/voice
```

**Expected Result:**
- ✅ System health indicators
- ✅ Call analytics from CRM data
- ✅ Recent calls table
- ✅ Active calls monitoring

## 🔍 Troubleshooting

### Issue: "CRM tools not available"

**Cause:** Import path issues in Farfalle
**Fix:**
```bash
cd crm-deployment/scripts/farfalle-main
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
poetry run uvicorn backend.main:app --reload --port 8000
```

### Issue: "Authentication failed"

**Cause:** Invalid CRM credentials
**Fix:**
1. Verify CRM_BASE_URL is correct
2. Test login manually at your CRM site
3. Check CRM_USER has proper permissions

### Issue: "Twilio not configured"

**Cause:** CRM Twilio Settings not enabled
**Fix:**
1. Login to your CRM
2. Go to Settings → Integrations → Twilio
3. Enable and configure with your Twilio credentials

### Issue: Voice dashboard not loading

**Cause:** CRM API permissions
**Fix:**
1. Verify user has access to CRM Call Log DocType
2. Check browser console for API errors
3. Test CRM APIs directly

## 📊 Test Results Validation

### ✅ Success Criteria

**Phase 1: CRM Integration**
- [ ] Farfalle backend starts without errors
- [ ] CRM health check returns "healthy"
- [ ] Voice endpoints respond correctly

**Phase 2: Call Orchestration**
- [ ] Call initiation creates CRM Call Log
- [ ] Call status can be retrieved
- [ ] Dashboard shows call analytics

**Phase 3: UI Integration**
- [ ] Voice dashboard loads in CRM
- [ ] System health indicators work
- [ ] Call data displays correctly

### 📈 Performance Benchmarks

- **API Response Time:** < 2 seconds
- **CRM Call Log Creation:** < 1 second
- **Dashboard Load Time:** < 3 seconds
- **Voice Health Check:** < 500ms

## 🔐 Security Testing

### Sandbox Mode Verification

```bash
# Test sandbox enforcement
curl -X POST http://localhost:8000/voice/initiate \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1999999999"
  }'
```

**Expected:** Should reject non-whitelisted numbers when `VOICE_SANDBOX=true`

### Authentication Testing

```bash
# Test with invalid CRM credentials
# Should return authentication error
```

## 🚀 Production Readiness Checklist

### Before Production Deployment:

- [ ] All tests pass
- [ ] CRM Twilio Settings configured
- [ ] Voice sandbox disabled: `VOICE_SANDBOX=false`
- [ ] Webhook URLs updated to production
- [ ] Monitoring and logging enabled
- [ ] Error handling verified
- [ ] Performance benchmarks met

## 📞 Manual Testing Workflow

### 1. Voice Call End-to-End Test

1. **Initiate Call:**
   - Use API or chat interface
   - Verify call appears in CRM

2. **Monitor Call:**
   - Check voice dashboard
   - Watch call status updates

3. **Verify Data:**
   - Confirm CRM Call Log created
   - Check notes and transcripts
   - Validate follow-up tasks

### 2. Intelligence Integration Test

1. **Research Company:**
   - Use `/intel/analyze` endpoint
   - Verify structured response

2. **Contextual Call:**
   - Use research data for call context
   - Verify context appears in call log

3. **Follow-up Actions:**
   - Check created notes and tasks
   - Validate CRM data linkage

## 🎯 Success Metrics

### Quantitative Metrics
- **API Uptime:** > 99%
- **Response Time:** < 2s average
- **Error Rate:** < 1%
- **CRM Integration Success:** > 95%

### Qualitative Metrics
- **User Experience:** Seamless integration
- **Data Accuracy:** Correct call logging
- **System Reliability:** Graceful error handling
- **Performance:** Responsive dashboard

This testing guide ensures comprehensive validation of the Voice MVP integration while maintaining safety and reliability standards.



