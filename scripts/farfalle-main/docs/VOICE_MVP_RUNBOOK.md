# Voice MVP Integration Runbook

## Overview

This runbook documents the **CORRECTED** Voice MVP integration that leverages existing CRM Twilio infrastructure instead of building parallel systems.

## Architecture (CORRECTED)

### ✅ What We Built (Correct Approach)
```
Farfalle Chat → CRM Twilio API → Existing Infrastructure → CRM Call Log
     ↓              ↓                    ↓                    ↓
Chat Interface  Orchestration    Production Twilio    Existing DocTypes
```

### ❌ What We Avoided (Wrong Approach)
```
Farfalle → New Twilio Client → Duplicate Systems → New Call Logs
```

## Components Implemented

### 1. CRM Backend Extensions
**File**: `crm-deployment/crm/integrations/twilio/api.py`

**Added Functions**:
- `initiate_outbound_call()` - Leverages existing Twilio infrastructure
- `vapi_webhook()` - Handles Vapi transcripts and creates FCRM Notes

**Key Features**:
- ✅ Uses existing `Twilio.connect()` and `create_call_log()`
- ✅ Respects existing CRM permissions and data models
- ✅ Creates proper `CRM Call Log` entries with linking
- ✅ Adds context notes and follow-up todos

### 2. Farfalle Orchestration Layer
**File**: `crm-deployment/scripts/farfalle-main/crm/tools.py`

**Added Functions**:
- `initiate_voice_call()` - Thin wrapper calling CRM API
- `get_call_status()` - Queries existing CRM Call Log
- `get_voice_dashboard_data()` - Analytics from CRM data
- `call_with_context()` - Combines voice + intelligence

**Key Features**:
- ✅ Thin orchestration layer, no duplicate logic
- ✅ Uses existing CRM client and authentication
- ✅ Provides chat-friendly interface to voice capabilities

### 3. CRM Voice Dashboard
**File**: `frappe-bench/apps/crm/frontend/src/pages/VoiceDashboard.vue`

**Features**:
- ✅ System health monitoring (Twilio, Vapi, CRM, Farfalle)
- ✅ Real-time call analytics from existing CRM Call Log
- ✅ Active calls monitoring with auto-refresh
- ✅ Recent calls table with details modal
- ✅ Call recordings and notes integration

**Route**: `/crm/voice` (added to `router.js`)

### 4. Farfalle Voice API
**File**: `crm-deployment/scripts/farfalle-main/src/backend/voice/simple_router.py`

**Endpoints**:
- `POST /voice/initiate` - Basic call initiation
- `POST /voice/call-with-context` - Contextual calls with intel
- `GET /voice/status/{call_sid}` - Call status from CRM
- `GET /voice/dashboard` - Dashboard data from CRM
- `GET /voice/contact/{contact_id}` - Contact lookup
- `GET /voice/health` - Health check

## Usage Examples

### 1. Basic Call via Farfalle API
```bash
curl -X POST http://localhost:8000/voice/initiate \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1234567890",
    "topic": "Business discussion",
    "context": "Follow up on proposal"
  }'
```

### 2. Contextual Call with Intel
```bash
curl -X POST http://localhost:8000/voice/call-with-context \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1234567890",
    "company": "Abbey Capital",
    "contact_name": "John Smith",
    "include_intel": true
  }'
```

### 3. Check Call Status
```bash
curl http://localhost:8000/voice/status/CA1234567890abcdef
```

### 4. Voice Dashboard Data
```bash
curl http://localhost:8000/voice/dashboard
```

## Data Flow

### Call Initiation Flow
1. **User**: "Call John at Abbey Capital" (Farfalle chat)
2. **Farfalle**: Calls `crm.integrations.twilio.api.initiate_outbound_call`
3. **CRM**: Uses existing `Twilio.connect()` and `twilio_handler.py`
4. **Twilio**: Places call using existing webhooks
5. **CRM**: Creates `CRM Call Log` with existing `create_call_log()`
6. **Response**: Returns call details to Farfalle/user

### Vapi Webhook Flow
1. **Vapi**: Sends transcript to `crm.integrations.twilio.api.vapi_webhook`
2. **CRM**: Creates `FCRM Note` with transcript/summary
3. **CRM**: Links note to existing `CRM Call Log`
4. **CRM**: Creates follow-up `ToDo` if needed
5. **Storage**: All data in existing CRM DocTypes

## Configuration

### CRM Configuration (Existing)
- Uses existing `CRM Twilio Settings` DocType
- Configured via CRM interface (not environment variables)
- Already handles Account SID, Auth Token, Phone Numbers

### Farfalle Configuration (Minimal)
```bash
# .env
CRM_BASE_URL=https://your-site.frappe.cloud
CRM_USER=your_user
CRM_PASSWORD=your_password
VAPI_API_KEY=your_vapi_key  # Optional
```

## Testing

### 1. Test CRM Extension
```python
# In Frappe console
import frappe
result = frappe.call("crm.integrations.twilio.api.initiate_outbound_call", 
                    to_number="+1234567890", 
                    topic="Test call")
print(result)
```

### 2. Test Farfalle Orchestration
```python
# In Farfalle environment
from crm.tools import initiate_voice_call
result = initiate_voice_call("+1234567890", topic="Test")
print(result)
```

### 3. Test Voice Dashboard
- Navigate to `/crm/voice` in CRM interface
- Verify system health indicators
- Check call analytics and recent calls

## Deployment

### CRM Deployment
1. Deploy updated `crm/integrations/twilio/api.py` to Frappe Cloud
2. Add new voice dashboard route to CRM frontend
3. Test existing Twilio configuration

### Farfalle Deployment
1. Deploy updated CRM tools and voice router
2. Configure environment variables
3. Test API endpoints

## Monitoring

### Health Checks
- `GET /voice/health` - Overall voice integration health
- CRM Twilio Settings - Check existing Twilio configuration
- Call Log queries - Verify data flow

### Key Metrics
- Call success rate (from CRM Call Log)
- Average call duration
- Active calls count
- System health status

## Troubleshooting

### Common Issues

#### 1. "CRM tools not available"
- **Cause**: Import path issues in Farfalle
- **Fix**: Verify `sys.path` in `simple_router.py`
- **Check**: CRM client authentication

#### 2. "Twilio not configured" 
- **Cause**: CRM Twilio Settings not enabled
- **Fix**: Configure via CRM → Settings → Integrations → Twilio
- **Check**: Account SID, Auth Token, Phone Numbers

#### 3. "Call log not created"
- **Cause**: Permissions or DocType issues
- **Fix**: Check user permissions for CRM Call Log
- **Check**: Frappe logs for detailed errors

#### 4. Voice dashboard not loading
- **Cause**: CRM API permissions or data access
- **Fix**: Verify user has access to CRM Call Log DocType
- **Check**: Browser console for API errors

## Key Lessons Learned

### ✅ Correct Approach
1. **Audit existing infrastructure first** - CRM had complete Twilio setup
2. **Extend, don't replace** - Added 2 functions vs building new system  
3. **Respect existing data models** - Used CRM Call Log, FCRM Note, ToDo
4. **Build thin orchestration** - Farfalle calls CRM, doesn't duplicate
5. **Leverage production-ready code** - CRM's Twilio integration is battle-tested

### ❌ Mistakes Avoided
1. **Building parallel systems** - Would have duplicated working infrastructure
2. **Creating new DocTypes** - CRM already has proper call logging
3. **Over-engineering** - Simple extensions beat complex new systems
4. **Ignoring existing APIs** - CRM has whitelisted methods for everything

## Future Enhancements

### Phase 2 (Planned)
- **Intel Integration**: Pre-call company research via `/intel/analyze`
- **Real-time Transcription**: Live transcript display in dashboard
- **Advanced Analytics**: Success scoring, conversation analysis

### Phase 3 (Planned)  
- **Multi-channel**: SMS, WhatsApp integration via existing CRM
- **AI Coaching**: Call quality analysis and suggestions
- **Automation**: Follow-up task creation based on call outcomes

## File Structure (Final)

```
crm-deployment/
├── crm/integrations/twilio/api.py          # ✅ Extended with voice functions
├── scripts/farfalle-main/
│   ├── crm/tools.py                        # ✅ Added voice orchestration
│   ├── src/backend/voice/simple_router.py  # ✅ Minimal API layer
│   └── src/backend/main.py                 # ✅ Includes voice router
└── docs/VOICE_MVP_RUNBOOK.md               # ✅ This documentation

frappe-bench/apps/crm/frontend/
├── src/pages/VoiceDashboard.vue            # ✅ Voice dashboard in CRM
└── src/router.js                           # ✅ Added /voice route
```

This MVP leverages 80% existing infrastructure and adds only 20% new code for voice orchestration and Vapi integration.



