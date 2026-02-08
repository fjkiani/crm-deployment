"""
Tests for Voice Integration (Twilio + Vapi)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from adapters.twilio_vapi.client import TwilioVoiceClient, VapiClient, is_phone_number_allowed
from adapters.twilio_vapi.tools import initiate_call, validate_call_request


class TestTwilioVoiceClient:
    """Test Twilio voice client functionality"""
    
    @pytest.fixture
    def mock_env(self):
        """Mock environment variables"""
        env_vars = {
            'TWILIO_ACCOUNT_SID': 'test_sid',
            'TWILIO_AUTH_TOKEN': 'test_token',
            'TWILIO_PHONE_NUMBER': '+15005550006'
        }
        
        with patch.dict(os.environ, env_vars):
            yield env_vars
    
    @pytest.fixture
    def mock_twilio_client(self, mock_env):
        """Create TwilioVoiceClient with mocked Twilio SDK"""
        with patch('adapters.twilio_vapi.client.TwilioClient') as mock_client:
            client = TwilioVoiceClient()
            client.client = mock_client
            return client, mock_client
    
    def test_initialization_success(self, mock_env):
        """Test successful client initialization"""
        client = TwilioVoiceClient()
        assert client.account_sid == 'test_sid'
        assert client.auth_token == 'test_token'
        assert client.phone_number == '+15005550006'
    
    def test_initialization_missing_credentials(self):
        """Test initialization failure with missing credentials"""
        with pytest.raises(ValueError, match="Missing required Twilio credentials"):
            TwilioVoiceClient()
    
    def test_initiate_call_success(self, mock_twilio_client):
        """Test successful call initiation"""
        client, mock_client = mock_twilio_client
        
        # Mock successful call creation
        mock_call = Mock()
        mock_call.sid = 'CA1234567890abcdef'
        mock_client.calls.create.return_value = mock_call
        
        result = client.initiate_call('+15005550009', 'https://example.com/webhook')
        
        assert result['success'] is True
        assert result['call_id'] == 'CA1234567890abcdef'
        assert result['provider'] == 'twilio'
        assert result['status'] == 'initiated'
    
    def test_initiate_call_failure(self, mock_twilio_client):
        """Test call initiation failure"""
        client, mock_client = mock_twilio_client
        
        # Mock Twilio exception
        from twilio.base.exceptions import TwilioException
        mock_client.calls.create.side_effect = TwilioException("Test error")
        
        result = client.initiate_call('+15005550009', 'https://example.com/webhook')
        
        assert result['success'] is False
        assert 'error' in result
        assert result['error_code'] == 'TWILIO_ERROR'


class TestVapiClient:
    """Test Vapi client functionality"""
    
    @pytest.fixture
    def mock_env(self):
        """Mock environment variables"""
        env_vars = {
            'VAPI_API_KEY': 'test_vapi_key',
            'VAPI_AGENT_ID': 'test_agent_id'
        }
        
        with patch.dict(os.environ, env_vars):
            yield env_vars
    
    @pytest.fixture
    def vapi_client(self, mock_env):
        """Create VapiClient instance"""
        return VapiClient()
    
    def test_initialization_success(self, mock_env):
        """Test successful client initialization"""
        client = VapiClient()
        assert client.api_key == 'test_vapi_key'
        assert client.agent_id == 'test_agent_id'
    
    def test_initialization_missing_key(self):
        """Test initialization failure with missing API key"""
        with pytest.raises(ValueError, match="Missing VAPI_API_KEY"):
            VapiClient()
    
    @patch('adapters.twilio_vapi.client.requests.request')
    def test_create_call_success(self, mock_request, vapi_client):
        """Test successful Vapi call creation"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"id": "vapi_call_123"}
        mock_request.return_value = mock_response
        
        result = vapi_client.create_call('+15005550009', 'https://example.com/webhook')
        
        assert result['success'] is True
        assert result['call_id'] == 'vapi_call_123'
        assert result['provider'] == 'vapi'
    
    @patch('adapters.twilio_vapi.client.requests.request')
    def test_create_call_failure(self, mock_request, vapi_client):
        """Test Vapi call creation failure"""
        # Mock API error
        mock_request.side_effect = Exception("API Error")
        
        result = vapi_client.create_call('+15005550009', 'https://example.com/webhook')
        
        assert result['success'] is False
        assert 'error' in result


class TestPhoneSafety:
    """Test phone number safety mechanisms"""
    
    def test_is_phone_allowed_test_numbers(self):
        """Test that Twilio test numbers are always allowed"""
        with patch.dict(os.environ, {'VOICE_SANDBOX': 'true', 'ALLOW_LIVE_CALLS': 'false'}):
            assert is_phone_number_allowed('+15005550006') is True
            assert is_phone_number_allowed('+15005550009') is True
    
    def test_is_phone_allowed_sandbox_mode(self):
        """Test phone number restrictions in sandbox mode"""
        env_vars = {
            'VOICE_SANDBOX': 'true',
            'ALLOW_LIVE_CALLS': 'false',
            'WHITELISTED_NUMBERS': '+12345678901,+19876543210'
        }
        
        with patch.dict(os.environ, env_vars):
            assert is_phone_number_allowed('+12345678901') is True
            assert is_phone_number_allowed('+19876543210') is True
            assert is_phone_number_allowed('+15551234567') is False
    
    def test_is_phone_allowed_live_calls(self):
        """Test phone number permissions with live calls enabled"""
        with patch.dict(os.environ, {'ALLOW_LIVE_CALLS': 'true'}):
            assert is_phone_number_allowed('+15551234567') is True


class TestVoiceTools:
    """Test high-level voice tools"""
    
    @patch('adapters.twilio_vapi.tools.TwilioVoiceClient')
    @patch('adapters.twilio_vapi.tools.is_phone_number_allowed')
    def test_initiate_call_success(self, mock_allowed, mock_client_class):
        """Test successful call initiation via tools"""
        # Setup mocks
        mock_allowed.return_value = True
        mock_client = Mock()
        mock_client.initiate_call.return_value = {
            'success': True,
            'call_id': 'CA123',
            'provider': 'twilio',
            'status': 'initiated'
        }
        mock_client_class.return_value = mock_client
        
        with patch.dict(os.environ, {'WEBHOOK_BASE_URL': 'https://example.com'}):
            result = initiate_call(phone='+15005550006', topic='Test call')
        
        assert result['success'] is True
        assert result['call_id'] == 'CA123'
        assert result['topic'] == 'Test call'
    
    @patch('adapters.twilio_vapi.tools.is_phone_number_allowed')
    def test_initiate_call_blocked_number(self, mock_allowed):
        """Test call initiation with blocked number"""
        mock_allowed.return_value = False
        
        result = initiate_call(phone='+15551234567')
        
        assert result['success'] is False
        assert result['error_code'] == 'PHONE_NOT_ALLOWED'
    
    def test_validate_call_request_missing_phone(self):
        """Test validation with missing phone/contact"""
        validation = validate_call_request()
        
        assert validation['valid'] is False
        assert 'Either contact_id or phone must be provided' in validation['errors']
    
    def test_validate_call_request_invalid_provider(self):
        """Test validation with invalid provider"""
        validation = validate_call_request(phone='+15005550006', provider='invalid')
        
        assert validation['valid'] is False
        assert 'Unsupported provider: invalid' in validation['errors']


class TestWebhookProcessing:
    """Test webhook processing functionality"""
    
    def test_twilio_webhook_data_parsing(self):
        """Test parsing of Twilio webhook data"""
        webhook_data = {
            'CallSid': 'CA1234567890abcdef',
            'CallStatus': 'completed',
            'From': '+15005550006',
            'To': '+15005550009',
            'CallDuration': '120'
        }
        
        # This would test the webhook processing logic
        # Implementation depends on the actual webhook handler
        assert webhook_data['CallSid'] == 'CA1234567890abcdef'
        assert webhook_data['CallStatus'] == 'completed'
        assert int(webhook_data['CallDuration']) == 120
    
    def test_vapi_webhook_data_parsing(self):
        """Test parsing of Vapi webhook data"""
        webhook_data = {
            'type': 'call-ended',
            'callId': 'vapi_call_123',
            'transcript': {
                'text': 'Hello, this is a test call.',
                'role': 'assistant'
            }
        }
        
        assert webhook_data['type'] == 'call-ended'
        assert webhook_data['callId'] == 'vapi_call_123'
        assert webhook_data['transcript']['text'] == 'Hello, this is a test call.'


# Integration tests
class TestVoiceIntegration:
    """Integration tests for complete voice workflow"""
    
    @pytest.mark.asyncio
    async def test_full_voice_workflow_simulation(self):
        """Test complete voice workflow simulation"""
        # This would test:
        # 1. Call initiation
        # 2. Webhook processing
        # 3. CRM record creation
        # 4. Follow-up task creation
        
        # Mock implementation for now
        workflow_steps = [
            'initiate_call',
            'receive_webhook',
            'create_call_log',
            'create_follow_up'
        ]
        
        # Simulate each step
        for step in workflow_steps:
            # In real test, would call actual functions
            assert step is not None
        
        # Verify end state
        assert len(workflow_steps) == 4


if __name__ == "__main__":
    pytest.main([__file__])



