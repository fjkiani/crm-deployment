#!/bin/bash
# Voice MVP Setup Script - Creates .env with production credentials

echo "🚀 Setting up Voice MVP environment..."

# Create .env from template
cp .env-template .env

# Replace placeholders with actual values
sed -i '' 's/VAPI_API_KEY=your_vapi_api_key_here/VAPI_API_KEY=53593b76-8c70-46e2-b01a-d2996afec5ba/' .env
sed -i '' 's/CRM_PASSWORD=your_frappe_admin_password_here/CRM_PASSWORD=Kiani11209!/' .env
sed -i '' 's/WHITELISTED_NUMBERS=+1234567890/WHITELISTED_NUMBERS=+13476842656/' .env

echo "✅ .env file created with production credentials"
echo ""
echo "📋 Configuration Summary:"
echo "  - Vapi API Key: ✅ Configured"
echo "  - Frappe CRM: ✅ jedilabs2.v.frappe.cloud"
echo "  - Twilio Phone: ✅ +18559173947"
echo "  - Test Number: ✅ +1-347-684-2656"
echo ""
echo "⚠️  Safety Controls Active:"
echo "  - VOICE_SANDBOX=true (prevents unauthorized calls)"
echo "  - ALLOW_LIVE_CALLS=false (only whitelisted numbers)"
echo "  - WHITELISTED_NUMBERS=+13476842656 (your phone only)"
echo ""
echo "🎯 Next Steps:"
echo "  1. Start server: uvicorn simple_voice_server:app --reload --port 8000"
echo "  2. Test call: curl -X POST http://localhost:8000/voice/initiate-call -H 'Content-Type: application/json' -d '{\"phone\":\"+13476842656\",\"topic\":\"Test\"}'"
echo ""
echo "📖 See QUICKSTART.md for detailed instructions"

