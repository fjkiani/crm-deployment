# Vapi Configuration for Frappe Cloud

## Add to site_config.json

In your Frappe Cloud site, add these keys to `site_config.json`:

```json
{
  "vapi_api_key": "53593b76-8c70-46e2-b01a-d2996afec5ba",
  "vapi_agent_id": "0e006140-2a20-47d4-a899-b20bd636e51a"
}
```

## How to Add (Frappe Cloud Console)

1. Go to https://frappecloud.com/dashboard/sites/jedilabs2
2. Click "Site Config" or use bench console:
   ```bash
   bench --site jedilabs2.v.frappe.cloud set-config vapi_api_key "53593b76-8c70-46e2-b01a-d2996afec5ba"
   bench --site jedilabs2.v.frappe.cloud set-config vapi_agent_id "0e006140-2a20-47d4-a899-b20bd636e51a"
   ```

3. Restart site (Frappe Cloud will do this automatically on config change)

## Verify Configuration

Test with:
```python
import frappe
vapi_key = frappe.get_site_config().get('vapi_api_key')
vapi_agent = frappe.get_site_config().get('vapi_agent_id')
print(f"Vapi Key: {vapi_key[:20]}...")
print(f"Agent ID: {vapi_agent}")
```

## Webhook URL for Vapi Dashboard

Configure this webhook URL in your Vapi agent settings:

```
https://jedilabs2.v.frappe.cloud/api/method/crm.integrations.twilio.api.vapi_webhook
```

This endpoint will receive call events (started, ended, transcripts).



