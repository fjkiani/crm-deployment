# Voice Operations Dashboard

## Overview
The Voice Operations Dashboard provides comprehensive 360° visibility into your VOIP engine pipeline, enabling real-time monitoring, debugging, and system optimization for Twilio + Vapi voice integrations.

## Features

### 🎯 **Complete Pipeline Visibility**
- **System Health Monitoring**: Real-time status of all components (Twilio, Vapi, CRM, Webhooks)
- **Active Call Tracking**: Live monitoring of ongoing calls with detailed information
- **Call Analytics**: Performance metrics, success rates, and trend analysis
- **Safety Controls**: Comprehensive safety mechanisms with visual indicators

### 🛡️ **Built-in Safety Checks**
- **Sandbox Mode**: Automatic blocking of non-whitelisted numbers
- **Emergency Stop**: One-click termination of all active calls
- **Phone Number Testing**: Validate numbers against safety settings
- **Live Call Controls**: Granular permissions and restrictions

### 📊 **Analytics & Insights**
- **Real-time Metrics**: Call volume, success rates, duration trends
- **Performance Tracking**: Webhook latency, system response times
- **Historical Analysis**: Configurable timeframes (1h, 24h, 7d, 30d)
- **Trend Visualization**: Charts and graphs for pattern recognition

### 🔧 **Debugging Tools**
- **Comprehensive Diagnostics**: Automated system health checks
- **Manual Testing**: Direct call initiation and flow testing
- **Webhook Simulation**: Test webhook processing without live calls
- **Connection Testing**: Validate all external integrations

## Dashboard Panels

### 1. System Health Panel
```
✅ Twilio Connection      45ms
✅ Vapi Connection        67ms  
✅ CRM Integration       123ms
✅ Webhook Endpoint       34ms
✅ Database               12ms

Overall Health Score: 98%
```

**Features:**
- Real-time connection testing
- Latency monitoring
- One-click reconnection
- Health score calculation

### 2. Active Calls Panel
```
📞 CA1234567890abcdef
   Provider: Twilio | Status: in-progress | Duration: 2m 25s
   Contact: John Doe | Topic: Follow up on proposal
   [View Details] [End Call]
```

**Features:**
- Live call monitoring
- Call duration tracking
- Contact information display
- Manual call termination
- Detailed call inspection

### 3. Call Analytics Panel
```
Total Calls: 247 (+12% vs yesterday)
Success Rate: 94.3% (+2.1% vs yesterday)
Avg Duration: 156s (-8s vs yesterday)
Webhook Latency: 89ms (+15ms vs yesterday)
```

**Features:**
- Key performance indicators
- Trend comparisons
- Visual charts and graphs
- Configurable timeframes

### 4. Safety Controls Panel
```
🛡️ SAFE MODE

☑️ Sandbox Mode          (Block non-whitelisted numbers)
☐ Allow Live Calls       (Enable calls to real numbers)

Whitelisted Numbers:
+15005550006,+15005550009

[Test Phone Number] [Emergency Stop All]
```

**Features:**
- Visual safety status
- Runtime setting updates
- Phone number validation
- Emergency controls

### 5. Webhook Monitor Panel
```
🌐 Webhook Status: Connected
Base URL: https://abc123.ngrok.io

Recent Activity:
12:34:56 | Twilio | call-completed | CA123 | ✅
12:34:26 | Vapi   | transcript     | vapi_456 | ✅
12:33:56 | Twilio | call-initiated | CA789 | ✅
```

**Features:**
- Webhook endpoint testing
- Real-time activity log
- Provider event tracking
- Status monitoring

### 6. CRM Integration Panel
```
📊 CRM Statistics
Call Logs Created: 89
Notes Created: 67
ToDos Created: 45
Failed Operations: 3

[Test CRM] [Sync Data] [View Logs]
```

**Features:**
- CRM operation tracking
- Success/failure metrics
- Manual sync capabilities
- Connection testing

### 7. Debug Console Panel
```
🐛 Debug Console

Quick Tests:
[Run Diagnostics] [Test Call Flow] [Simulate Webhook]

Manual Call Test:
Phone: [+15005550006] Topic: [Test call] Provider: [Twilio ▼] [Initiate]

Debug Log:
12:34:56 INFO  Voice dashboard initialized
12:34:51 INFO  Health checks completed
12:34:45 ERROR Call initiation failed: Invalid phone number
```

**Features:**
- Automated diagnostics
- Manual call testing
- Webhook simulation
- Real-time debug logging

## API Endpoints

### Dashboard Data
- `GET /voice/dashboard/health` - System health status
- `GET /voice/dashboard/active-calls` - Current active calls
- `GET /voice/dashboard/analytics` - Call analytics and metrics
- `GET /voice/dashboard/safety-settings` - Current safety configuration
- `GET /voice/dashboard/webhook-activity` - Recent webhook events
- `GET /voice/dashboard/crm-stats` - CRM integration statistics

### Control Endpoints
- `POST /voice/dashboard/safety-settings` - Update safety settings
- `POST /voice/test-phone` - Test phone number permissions
- `POST /voice/emergency-stop` - Emergency stop all calls
- `POST /voice/test-crm` - Test CRM connection
- `GET /voice/webhooks/test` - Test webhook accessibility

## Safety Mechanisms

### Sandbox Mode
```javascript
// Environment: VOICE_SANDBOX=true
// Only these numbers can be called:
- +15005550006 (Twilio test - valid)
- +15005550009 (Twilio test - invalid)  
- Numbers in WHITELISTED_NUMBERS
```

### Live Call Protection
```javascript
// Environment: ALLOW_LIVE_CALLS=false (default)
// Blocks all real phone numbers
// Override per-call: { "allow_live_calls": true }
```

### Emergency Controls
- **Emergency Stop**: Terminates all active calls immediately
- **Real-time Monitoring**: Tracks all call states and durations
- **Automatic Cleanup**: Removes stale call sessions

## Integration with Agents

### Future Agent Capabilities
The dashboard is designed to support AI agents for:

1. **Automated Optimization**
   - Performance analysis and recommendations
   - Automatic safety setting adjustments
   - Predictive failure detection

2. **Intelligent Monitoring**
   - Anomaly detection in call patterns
   - Automated troubleshooting
   - Performance optimization suggestions

3. **Enhanced Analytics**
   - AI-powered trend analysis
   - Predictive capacity planning
   - Intelligent alerting

## Usage Examples

### Quick Health Check
```bash
curl http://localhost:8000/voice/dashboard/health
```

### Test Phone Number
```bash
curl -X POST http://localhost:8000/voice/test-phone \
  -H "Content-Type: application/json" \
  -d '{"phone": "+15005550006"}'
```

### Emergency Stop
```bash
curl -X POST http://localhost:8000/voice/emergency-stop
```

### Update Safety Settings
```bash
curl -X POST http://localhost:8000/voice/dashboard/safety-settings \
  -H "Content-Type: application/json" \
  -d '{"voice_sandbox": true, "allow_live_calls": false}'
```

## Monitoring & Alerting

### Key Metrics to Monitor
- **System Health Score**: Should stay above 95%
- **Call Success Rate**: Target 90%+ success rate
- **Webhook Latency**: Should be under 200ms
- **Active Call Duration**: Monitor for stuck calls
- **Failed Operations**: Should be minimal

### Alert Conditions
- Health score drops below 80%
- Call success rate drops below 85%
- Webhook latency exceeds 500ms
- Any component shows "error" status
- Emergency stop is activated

## Development & Testing

### Local Development
1. Start Farfalle backend: `poetry run uvicorn backend.main:app --reload`
2. Access dashboard: `http://localhost:8000/voice-dashboard`
3. Use ngrok for webhook testing: `ngrok http 8000`

### Testing Scenarios
1. **Connection Testing**: Verify all health checks pass
2. **Call Flow Testing**: Test complete call workflow
3. **Webhook Testing**: Simulate provider webhooks
4. **Safety Testing**: Validate phone number restrictions
5. **Emergency Testing**: Test emergency stop functionality

## Future Enhancements

### Phase 1: Enhanced Monitoring
- Real-time call quality metrics
- Advanced analytics and reporting
- Custom dashboard layouts
- Export capabilities

### Phase 2: AI Integration
- Intelligent anomaly detection
- Predictive analytics
- Automated optimization
- Smart alerting

### Phase 3: Advanced Features
- Multi-tenant support
- Role-based access controls
- Advanced reporting
- Integration with Grafana/Prometheus

## Troubleshooting

### Common Issues
1. **Dashboard not loading**: Check backend server status
2. **Health checks failing**: Verify environment variables
3. **Webhook data missing**: Check WEBHOOK_BASE_URL configuration
4. **Call data not updating**: Verify webhook endpoints are accessible

### Debug Steps
1. Check browser console for JavaScript errors
2. Verify API endpoints are responding
3. Check backend logs for errors
4. Test webhook connectivity with ngrok
5. Validate environment variable configuration

## Security Considerations

### Data Privacy
- Phone numbers are sanitized in logs (show only last 4 digits)
- Transcript data is handled securely
- Webhook payloads are validated

### Access Control
- Dashboard requires authentication
- API endpoints have proper authorization
- Emergency controls are logged and audited

### Network Security
- HTTPS required for webhook endpoints
- Webhook signature verification (where supported)
- Rate limiting on API endpoints



