# Voice MVP Production Deployment Plan

## Current Status: 80% Complete (Backend MVP Done)

### ✅ What's Working Now
- CRM Twilio integration extended with outbound call + Vapi webhook endpoints
- Farfalle voice orchestration server running on port 8000
- Voice Dashboard UI component created (678 lines)
- CRM Call Log, FCRM Note, ToDo integration complete
- Mock testing successful (no credentials)

### 🚧 What's Blocking Production
1. **No real credentials** - Using mock data
2. **Frontend not wired** - Dashboard exists but not routed
3. **No Vapi agent** - AI integration not configured
4. **Webhooks not public** - Running on localhost
5. **No safety testing** - Sandbox mode untested

---

## A-Z Production Deployment Roadmap

### PHASE 1: Get Real Credentials & Test Accounts (2 hours)
**Goal**: Replace mock data with real test infrastructure

#### 1.1 Twilio Setup
- [ ] Sign up for Twilio account (or use existing)
- [ ] Get **Test Credentials** from Twilio Console:
  - Account SID (starts with `AC...`)
  - Auth Token
  - Twilio phone number (or use test number)
- [ ] Configure Twilio Console webhooks (we'll update URLs later)

#### 1.2 Vapi Setup  
- [ ] Sign up for Vapi account at https://vapi.ai
- [ ] Create new AI assistant/agent
- [ ] Configure agent prompts and behavior:
  ```
  Example prompt: "You are a professional sales assistant. 
  When calling a prospect, introduce yourself politely, 
  explain the purpose of the call, and gather key information. 
  Be concise and respectful of their time."
  ```
- [ ] Get **Vapi Credentials**:
  - API Key
  - Agent ID
  - Webhook Secret (if available)

#### 1.3 CRM Access
- [ ] Confirm CRM site URL: `https://________.frappe.cloud`
- [ ] Get API credentials (username + password OR API key/secret)
- [ ] Test CRM API access:
  ```bash
  curl -X POST https://your-site.frappe.cloud/api/method/login \
    -H "Content-Type: application/json" \
    -d '{"usr":"your_user","pwd":"your_password"}'
  ```

**Deliverable**: Credentials documented in secure password manager

---

### PHASE 2: Environment Configuration (1 hour)
**Goal**: Configure production environment variables and CRM settings

#### 2.1 Farfalle Environment Setup
Create/update: `crm-deployment/scripts/farfalle-main/.env`

```bash
# CRM Connection
CRM_BASE_URL=https://your-actual-site.frappe.cloud
CRM_USER=your_actual_username
CRM_PASSWORD=your_actual_password

# Twilio (from Phase 1.1)
TWILIO_ACCOUNT_SID=AC________________________
TWILIO_AUTH_TOKEN=________________________
TWILIO_PHONE_NUMBER=+1__________

# Vapi (from Phase 1.2)
VAPI_API_KEY=________________________
VAPI_AGENT_ID=________________________
VAPI_WEBHOOK_SECRET=________________________  # if applicable

# Webhook Base (will update in Phase 4)
WEBHOOK_BASE_URL=https://your-ngrok-or-production-url.com

# Safety Controls (start with strict settings)
VOICE_SANDBOX=true
ALLOW_LIVE_CALLS=false
WHITELISTED_NUMBERS=+1234567890,+1987654321  # your test numbers only
```

#### 2.2 CRM Twilio Settings Configuration
In CRM interface (https://your-site.frappe.cloud):

1. Navigate to: **CRM Settings > Integrations > Twilio Settings**
2. Fill in:
   - Account SID: `AC...` (from Twilio)
   - Auth Token: `...` (from Twilio)
   - Phone Number: `+1...` (from Twilio)
   - Enable Integration: ✅
3. Save settings

#### 2.3 Test CRM Connection
```bash
cd crm-deployment/scripts/farfalle-main
source venv/bin/activate
python -c "from crm.client import CrmClient; print(CrmClient().get('Lead', limit=1))"
```
Should return real CRM data, not mock.

**Deliverable**: `.env` configured, CRM connection verified

---

### PHASE 3: Frontend Integration (2 hours)
**Goal**: Wire Voice Dashboard into CRM SPA

#### 3.1 Add Voice Dashboard Route
**File**: `frappe-bench/apps/crm/frontend/src/router.js`

Add after line 111 (before the catch-all route):
```javascript
{
  path: '/voice',
  name: 'Voice Dashboard',
  component: () => import('@/pages/VoiceDashboard.vue'),
},
```

#### 3.2 Update VoiceDashboard.vue API Calls
**File**: `frappe-bench/apps/crm/frontend/src/pages/VoiceDashboard.vue`

Add at top of `<script setup>`:
```javascript
const FARFALLE_API_URL = import.meta.env.VITE_FARFALLE_API_URL || 'http://localhost:8000'
```

Add initiate call function (around line 400):
```javascript
const initiateCall = async (phone, contactId = null, topic = null) => {
  try {
    loading.value = true
    
    const response = await fetch(`${FARFALLE_API_URL}/voice/initiate-call`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        phone: phone,
        contact_id: contactId,
        topic: topic
      })
    })
    
    const result = await response.json()
    
    if (result.status === 'success') {
      // Show success message
      await refreshData() // Reload dashboard
    }
  } catch (error) {
    console.error('Failed to initiate call:', error)
  } finally {
    loading.value = false
  }
}
```

#### 3.3 Add Frontend Environment Variable
**File**: `frappe-bench/apps/crm/frontend/.env.development`

```bash
VITE_FARFALLE_API_URL=http://localhost:8000
```

#### 3.4 Add Quick Call Button (Optional but Useful)
In VoiceDashboard.vue template, add test call button:
```vue
<button 
  @click="initiateCall('+1234567890', null, 'Test call')"
  class="btn btn-success"
>
  🧪 Test Call
</button>
```

#### 3.5 Build and Test Frontend
```bash
cd frappe-bench/apps/crm/frontend
npm run dev
```
Then navigate to: `http://localhost:8080/crm/voice`

**Deliverable**: Voice Dashboard accessible in CRM, can initiate calls

---

### PHASE 4: Webhook & Public URL Setup (1 hour)
**Goal**: Make webhooks publicly accessible for Twilio/Vapi callbacks

#### 4.1 Option A: Development (ngrok)
```bash
# Install ngrok if needed
brew install ngrok  # or download from ngrok.com

# Start ngrok tunnel
ngrok http 8000

# Copy the public URL (e.g., https://abc123.ngrok.io)
```

#### 4.2 Option B: Production (Deploy Farfalle)
Deploy to a cloud service:
- **Railway**: `railway up` (from farfalle-main directory)
- **Render**: Connect GitHub repo, deploy FastAPI app
- **Heroku**: `git push heroku main`
- **VPS**: Use systemd + nginx reverse proxy

Get public URL (e.g., `https://farfalle-voice.railway.app`)

#### 4.3 Update Environment Variables
Update `.env` with public URL:
```bash
WEBHOOK_BASE_URL=https://your-public-url.com
```

Restart Farfalle server:
```bash
cd crm-deployment/scripts/farfalle-main
source venv/bin/activate
uvicorn simple_voice_server:app --reload --port 8000
```

#### 4.4 Configure Twilio Webhooks
In Twilio Console > Phone Numbers > Your Number:

**Voice Configuration**:
- When a call comes in: `https://your-public-url.com/webhooks/twilio/voice`
- Method: `HTTP POST`

**Status Callbacks**:
- Status Callback URL: `https://your-public-url.com/webhooks/twilio/status`
- Method: `HTTP POST`
- Events: `completed`, `failed`, `busy`, `no-answer`

#### 4.5 Configure Vapi Webhooks
In Vapi Dashboard > Agent Settings:

**Webhook URL**: `https://your-public-url.com/webhooks/vapi`
**Events**: 
- `call.started`
- `transcript.chunk`
- `call.ended`
- `call.summary`

**Deliverable**: Public webhooks configured and receiving events

---

### PHASE 5: Safety Testing (2 hours)
**Goal**: Verify safety controls prevent unauthorized calls

#### 5.1 Test Sandbox Mode
Ensure `.env` has:
```bash
VOICE_SANDBOX=true
ALLOW_LIVE_CALLS=false
WHITELISTED_NUMBERS=+1234567890  # your test number
```

#### 5.2 Test Safety Scenarios

**Test 1: Blocked Number (should fail)**
```bash
curl -X POST "http://localhost:8000/voice/initiate-call" \
  -H "Content-Type: application/json" \
  -d '{"phone":"+19999999999","topic":"Test"}'
```
Expected: Error "Number not whitelisted in sandbox mode"

**Test 2: Whitelisted Number (should succeed)**
```bash
curl -X POST "http://localhost:8000/voice/initiate-call" \
  -H "Content-Type: application/json" \
  -d '{"phone":"+1234567890","topic":"Test call"}'
```
Expected: Success, call initiated

**Test 3: Dashboard Safety Indicators**
- Navigate to Voice Dashboard
- Verify sandbox mode indicator shows "SANDBOX MODE ACTIVE"
- Verify whitelisted numbers display correctly
- Test "Override" toggle (should require confirmation)

#### 5.3 Verify CRM Permissions
Test with different CRM user roles:
- Sales User (should be able to initiate calls)
- Guest (should NOT be able to initiate calls)

**Deliverable**: All safety controls verified working

---

### PHASE 6: End-to-End Testing (3 hours)
**Goal**: Complete call flow from initiation to CRM artifacts

#### 6.1 Test Complete Call Flow

**Step 1: Initiate Call**
```bash
curl -X POST "http://localhost:8000/voice/initiate-call" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1234567890",
    "contact_id": "CONT-0001",  # use real contact ID from CRM
    "topic": "Product demo follow-up",
    "context": "Discussed pricing on previous call"
  }'
```

**Step 2: Answer Call (on your phone)**
- Phone should ring
- Vapi AI agent should speak
- Have a short conversation (30-60 seconds)
- Hang up

**Step 3: Verify CRM Artifacts**

In CRM, check:
1. **CRM Call Log** created:
   - Status: "Completed"
   - Duration: ~30-60 seconds
   - Linked to Contact: CONT-0001
   - Provider Call ID populated

2. **FCRM Note** created:
   - Linked to CRM Call Log
   - Contains call summary/transcript
   - Title: "Call Summary: [Topic]"

3. **ToDo** created (if configured):
   - Description: Follow-up action
   - Linked to Contact
   - Due date set

#### 6.2 Test Dashboard Data
Navigate to Voice Dashboard:
- Total Calls should increment
- Recent Calls should show your test call
- Analytics should update (success rate, avg duration)
- Call details modal should show transcript

#### 6.3 Test Error Scenarios

**Failed Call**:
```bash
curl -X POST "http://localhost:8000/voice/initiate-call" \
  -H "Content-Type: application/json" \
  -d '{"phone":"+1000000000","topic":"Test"}'  # invalid number
```
Verify: Call Log shows "Failed" status

**Webhook Retry**:
- Temporarily stop Farfalle server
- Initiate call from Twilio
- Restart server
- Verify webhooks eventually process

#### 6.4 Performance Testing
Run 10 concurrent calls (if budget allows):
```bash
for i in {1..10}; do
  curl -X POST "http://localhost:8000/voice/initiate-call" \
    -H "Content-Type: application/json" \
    -d "{\"phone\":\"+1234567890\",\"topic\":\"Load test $i\"}" &
done
```
Verify: All calls complete, no data loss

**Deliverable**: Full call flow tested, all artifacts verified

---

### PHASE 7: Production Hardening (2 hours)
**Goal**: Prepare for real user traffic

#### 7.1 Security Checklist
- [ ] Enable HTTPS on Farfalle server (not HTTP)
- [ ] Verify CORS only allows CRM domain
- [ ] Add webhook signature validation:
  - Twilio: Verify `X-Twilio-Signature`
  - Vapi: Verify webhook secret
- [ ] Enable rate limiting (10 calls/minute per user)
- [ ] Add IP whitelisting for CRM callbacks

#### 7.2 Error Handling & Logging
Add to `simple_voice_server.py`:
```python
import sentry_sdk  # or your error tracking service

sentry_sdk.init(
    dsn="your-sentry-dsn",
    environment="production"
)

# Add request ID logging
import uuid
from fastapi import Request

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    logger.info(f"Request {request.state.request_id}: {request.method} {request.url}")
    response = await call_next(request)
    return response
```

#### 7.3 Monitoring Setup
Add health check monitoring:
```bash
# Add to cron or monitoring service
curl https://your-farfalle-url.com/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "components": {
    "crm": true,
    "twilio": true,
    "vapi": true
  }
}
```

Set up alerts:
- Webhook failures > 5% in 5 minutes
- Call initiation errors > 3 in 1 minute
- CRM connection lost

#### 7.4 PII & Compliance
- [ ] Enable transcript redaction in Vapi (if needed)
- [ ] Add phone number masking in logs:
  ```python
  def mask_phone(phone: str) -> str:
      return phone[:2] + "****" + phone[-4:]
  ```
- [ ] Document data retention policy
- [ ] Add user consent tracking for call recording

#### 7.5 Backup & Rollback Plan
```bash
# Backup current state
git tag v1.0-voice-mvp
git push origin v1.0-voice-mvp

# Document rollback procedure
echo "To rollback: git checkout v1.0-voice-mvp && restart services" > ROLLBACK.md
```

**Deliverable**: Production-grade security and monitoring

---

### PHASE 8: Go Live (1 hour)
**Goal**: Enable production access for real users

#### 8.1 Enable Live Calls
Update `.env`:
```bash
VOICE_SANDBOX=false  # Turn off sandbox
ALLOW_LIVE_CALLS=true  # Enable real calls
WHITELISTED_NUMBERS=  # Can be empty or keep some restrictions
```

Restart Farfalle server.

#### 8.2 User Training
Create quick guide for sales team:

**Voice Operations Quick Start**
1. Navigate to Voice Dashboard: `/crm/voice`
2. System health indicators (green = ready)
3. To call a contact:
   - Go to Contact page
   - Click "Call" button OR
   - Use chat: "Call John Smith about proposal"
4. During call: Vapi AI handles conversation
5. After call: Check CRM Call Log for transcript and follow-ups

#### 8.3 Soft Launch
- [ ] Enable for 2-3 test users first
- [ ] Monitor for 24 hours
- [ ] Collect feedback
- [ ] Fix any issues
- [ ] Gradually roll out to all users

#### 8.4 Post-Launch Monitoring (First 7 Days)
Daily checks:
- Total calls made
- Success rate (should be >85%)
- Average call duration
- Webhook failure rate (should be <1%)
- User feedback/complaints

**Deliverable**: Voice MVP live in production

---

## Critical Questions I Need Answered

### 🔴 URGENT (Needed for Phase 1)
1. **CRM Site URL**: What is your actual Frappe Cloud site URL?
   - Format: `https://________.frappe.cloud`

2. **Test Phone Number**: What phone number should I use for testing?
   - Must be a real number you can answer

3. **Vapi Use Case**: What should the AI agent say/do on calls?
   - Sales outreach?
   - Customer support?
   - Appointment scheduling?
   - General conversation?

### 🟡 IMPORTANT (Needed for Phase 3-4)
4. **Deployment Preference**: Where do you want Farfalle hosted?
   - [ ] Railway (easiest, $5/month)
   - [ ] Render (free tier available)
   - [ ] Your own VPS
   - [ ] Other: __________

5. **Budget for Testing**: How many test calls can we make?
   - Twilio costs ~$0.01-0.05/minute
   - Recommend budget: $10-20 for thorough testing

6. **User Roles**: Which CRM roles should be able to initiate calls?
   - Sales User?
   - Sales Manager?
   - System Manager?
   - Custom role: __________

### 🟢 NICE TO HAVE (Can decide later)
7. **Call Recording**: Do you want calls recorded and stored?
   - Legal implications vary by jurisdiction
   - Requires user consent in some regions

8. **AI Agent Customization**: Any specific requirements?
   - Language/accent
   - Tone (formal/casual)
   - Industry-specific knowledge

9. **Analytics Dashboard**: What metrics are most important?
   - Call volume
   - Success rates
   - Average duration
   - Cost per call
   - AI sentiment analysis

---

## Success Criteria

### MVP Launch Success = All These True:
- ✅ Can initiate call from CRM to real phone number
- ✅ Vapi AI agent answers and has coherent conversation
- ✅ Call creates CRM Call Log with correct data
- ✅ Transcript saved as FCRM Note
- ✅ Follow-up ToDo created automatically
- ✅ Voice Dashboard shows accurate real-time data
- ✅ No unauthorized calls possible (safety controls work)
- ✅ Webhooks process reliably (>99% success rate)
- ✅ Users can access via CRM interface
- ✅ System handles errors gracefully (no crashes)

---

## Estimated Timeline

**Fast Track (with all credentials ready)**: 2-3 days
**Normal Pace (realistic)**: 1 week
**With testing & refinement**: 2 weeks

**Today's Action Plan** (if you want to start now):
1. Get Twilio test account (30 minutes)
2. Get Vapi account and create agent (1 hour)
3. Share CRM URL and credentials with me (5 minutes)
4. I'll configure Phase 2 while you set up Phase 1

**Want me to start on any specific phase while you gather credentials?**


