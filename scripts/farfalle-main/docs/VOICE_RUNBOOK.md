# Voice Integration Runbook

## Overview
This runbook covers the operation, troubleshooting, and maintenance of the Vapi + Twilio voice integration with the CRM system.

## Architecture
```
Chat Input → Voice Router → Twilio/Vapi → Call Execution → Webhooks → CRM Records
```

## Environment Setup

### Required Environment Variables
```bash
# Voice Providers
VAPI_API_KEY=your_vapi_api_key
VAPI_AGENT_ID=your_agent_id (optional)
VAPI_WEBHOOK_SECRET=your_webhook_secret (optional)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=+1234567890

# Webhook Configuration
WEBHOOK_BASE_URL=https://your-domain.com
# For development: https://abc123.ngrok.io

# Safety Settings
VOICE_SANDBOX=true
ALLOW_LIVE_CALLS=false
WHITELISTED_NUMBERS=+15005550006,+15005550009

# CRM Integration
CRM_BASE_URL=https://your-crm.frappe.cloud
CRM_USER=your_crm_user
CRM_PASSWORD=your_crm_password
```

### Development Setup
1. **Install ngrok**: `npm install -g ngrok` or download from ngrok.com
2. **Expose local server**: `ngrok http 8000`
3. **Set webhook URL**: Copy ngrok URL to `WEBHOOK_BASE_URL`
4. **Configure Twilio webhooks**:
   - Status Callback URL: `{WEBHOOK_BASE_URL}/voice/webhooks/twilio`
   - Voice URL: `{WEBHOOK_BASE_URL}/voice/twiml`
5. **Configure Vapi webhooks**:
   - Server URL: `{WEBHOOK_BASE_URL}/voice/webhooks/vapi`

## API Endpoints

### Voice Control
- **POST** `/voice/initiate` - Initiate a call
- **POST** `/voice/end` - End an active call
- **GET** `/voice/status/{call_id}` - Get call status

### Webhooks
- **POST** `/voice/webhooks/twilio` - Twilio status callbacks
- **POST** `/voice/webhooks/vapi` - Vapi agent events
- **GET/POST** `/voice/twiml` - TwiML response for Twilio

## Usage Examples

### Initiate a Call
```bash
curl -X POST http://localhost:8000/voice/initiate \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+15005550006",
    "topic": "Follow up on proposal",
    "context": "Customer interested in our CRM solution",
    "provider": "twilio"
  }'
```

### End a Call
```bash
curl -X POST http://localhost:8000/voice/end \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "CA1234567890abcdef"
  }'
```

### Check Call Status
```bash
curl http://localhost:8000/voice/status/CA1234567890abcdef
```

## Safety Mechanisms

### Sandbox Mode
When `VOICE_SANDBOX=true`:
- Only Twilio test numbers and whitelisted numbers can be called
- Prevents accidental calls to real numbers during development
- Test numbers: `+15005550006` (valid), `+15005550009` (invalid)

### Live Calls
When `ALLOW_LIVE_CALLS=true`:
- All phone numbers are allowed (use with caution)
- Should only be enabled in production with proper safeguards

### Whitelisted Numbers
- Comma-separated list in `WHITELISTED_NUMBERS`
- Always allowed even in sandbox mode
- Use for specific test numbers or approved contacts

## Monitoring and Logging

### Log Levels
- **INFO**: Call initiation, completion, CRM record creation
- **DEBUG**: Transcript buffering, detailed webhook processing
- **ERROR**: Failed calls, webhook processing errors, CRM integration failures
- **WARNING**: Blocked calls, missing configurations

### Key Metrics to Monitor
- Call success rate
- Webhook processing latency
- CRM record creation success rate
- Failed call attempts (especially blocked numbers)

### Log Examples
```
INFO: Call initiated via twilio to ***0006: CA1234567890abcdef
INFO: Created call log: CRM-CALL-LOG-001 for call CA1234567890abcdef
ERROR: Failed to create call log for CA1234567890abcdef: API timeout
WARNING: Call blocked to ***4567 - not in whitelist
```

## Troubleshooting

### Common Issues

#### 1. Call Initiation Fails
**Symptoms**: `POST /voice/initiate` returns error
**Causes**:
- Missing/invalid Twilio credentials
- Phone number not allowed (sandbox mode)
- Webhook URL not accessible
- CRM contact not found

**Solutions**:
- Verify Twilio credentials in environment
- Check `VOICE_SANDBOX` and `WHITELISTED_NUMBERS` settings
- Test webhook URL accessibility: `curl {WEBHOOK_BASE_URL}/voice/webhooks/twilio`
- Verify contact exists in CRM

#### 2. Webhooks Not Received
**Symptoms**: Calls initiated but no CRM records created
**Causes**:
- Webhook URL not publicly accessible
- Twilio/Vapi webhook configuration incorrect
- Firewall blocking incoming requests
- Server not running or crashed

**Solutions**:
- Test webhook URL from external service
- Verify Twilio webhook configuration in console
- Check server logs for incoming webhook requests
- Ensure FastAPI server is running on correct port

#### 3. CRM Records Not Created
**Symptoms**: Webhooks received but no CRM Call Log/Notes
**Causes**:
- CRM API credentials invalid
- CRM server unreachable
- DocType permissions insufficient
- Field validation errors

**Solutions**:
- Test CRM credentials: `curl -u user:pass {CRM_BASE_URL}/api/method/login`
- Check CRM server status
- Verify user has permissions to create Call Log, Note, ToDo
- Check CRM error logs for validation issues

#### 4. Vapi Transcripts Missing
**Symptoms**: Calls complete but no transcript in notes
**Causes**:
- Vapi webhook not configured
- Transcript events not received
- Transcript processing errors
- Note creation failures

**Solutions**:
- Verify Vapi webhook URL configuration
- Check logs for transcript events
- Test note creation manually
- Verify FCRM Note DocType exists

### Debug Commands

#### Test Twilio Connection
```bash
# Test Twilio credentials
python3 -c "
from adapters.twilio_vapi.client import TwilioVoiceClient
client = TwilioVoiceClient()
print('Twilio connection successful')
"
```

#### Test Vapi Connection
```bash
# Test Vapi credentials
python3 -c "
from adapters.twilio_vapi.client import VapiClient
client = VapiClient()
result = client._make_request('GET', '/call')
print('Vapi connection:', result['success'])
"
```

#### Test CRM Connection
```bash
# Test CRM connection
python3 -c "
from crm.client import CrmClient
client = CrmClient()
client.login()
print('CRM connection successful')
"
```

#### Test Phone Number Safety
```bash
# Test phone number validation
python3 -c "
from adapters.twilio_vapi.client import is_phone_number_allowed
print('Test number allowed:', is_phone_number_allowed('+15005550006'))
print('Random number allowed:', is_phone_number_allowed('+15551234567'))
"
```

## Maintenance Tasks

### Daily
- Monitor call success rates
- Check for failed webhook processing
- Review blocked call attempts

### Weekly
- Clean up old call sessions from memory
- Review and rotate webhook secrets
- Update whitelisted numbers as needed

### Monthly
- Review call logs and usage patterns
- Update Twilio/Vapi account limits if needed
- Test disaster recovery procedures

## Emergency Procedures

### Disable Voice Calling
```bash
# Temporarily disable all voice calls
export ALLOW_LIVE_CALLS=false
export VOICE_SANDBOX=true
export WHITELISTED_NUMBERS=""
# Restart server
```

### Webhook Failure Recovery
1. Check webhook endpoint accessibility
2. Review recent webhook logs
3. Manually create missing CRM records if needed
4. Update webhook URLs in provider consoles

### High Call Volume
1. Monitor Twilio/Vapi account limits
2. Check CRM API rate limits
3. Scale webhook processing if needed
4. Consider implementing call queuing

## Security Considerations

### Webhook Security
- Use HTTPS for all webhook URLs
- Implement webhook signature verification (Vapi)
- Validate all incoming webhook data
- Rate limit webhook endpoints

### Data Privacy
- Never log full phone numbers (use sanitization)
- Redact sensitive transcript content
- Implement transcript retention policies
- Ensure GDPR/compliance requirements

### Access Control
- Restrict voice calling to authorized users
- Implement role-based permissions
- Monitor and audit call activities
- Secure credential storage

## Performance Optimization

### Webhook Processing
- Use background tasks for CRM operations
- Implement idempotency for webhook handling
- Add retry logic for failed operations
- Monitor processing latency

### Call Quality
- Monitor call success rates
- Track call duration and completion rates
- Optimize TwiML responses
- Configure appropriate timeouts

### Resource Management
- Clean up expired call sessions
- Implement connection pooling for CRM API
- Monitor memory usage for transcript buffering
- Set appropriate rate limits

## Contact Information

### Support Escalation
- **Level 1**: Check this runbook, review logs
- **Level 2**: Contact development team
- **Level 3**: Engage Twilio/Vapi support if provider issue

### Provider Support
- **Twilio**: https://support.twilio.com
- **Vapi**: https://docs.vapi.ai/support
- **CRM**: Internal support team



