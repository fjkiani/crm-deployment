# CRM API Index

## Core APIs

### Authentication
- `crm.api.auth.login` - User login
- `crm.api.auth.logout` - User logout
- `crm.api.auth.get_user_info` - Get current user info

### Leads & Contacts
- `crm.api.contact.get_contacts` - List contacts
- `crm.api.contact.create_contact` - Create new contact
- `crm.api.contact.update_contact` - Update contact
- `crm.api.contact.delete_contact` - Delete contact

### Organizations
- `crm.api.contact.get_organizations` - List organizations
- `crm.api.contact.create_organization` - Create organization
- `crm.api.contact.update_organization` - Update organization

### Activities & Tasks
- `crm.api.activities.get_activities` - List activities
- `crm.api.activities.create_activity` - Create activity
- `crm.api.activities.update_activity` - Update activity
- `crm.api.todo.get_todos` - List todos
- `crm.api.todo.create_todo` - Create todo

### Comments & Notes
- `crm.api.comment.get_comments` - List comments
- `crm.api.comment.add_comment` - Add comment

## Email & Communication APIs

### Basic Email Operations
- `crm.api.email.get_inbox` - Get recent communications
- `crm.api.email.thread_context` - Get email thread context
- `crm.api.email.save_draft` - Create email draft
- `crm.api.email.send` - Send email
- `crm.api.email.link_provider_ids` - Link external provider IDs

### 🤖 AI-Powered Email Features (NEW)
- `crm.api.email.triage_email` - AI email triage and classification
- `crm.api.email.draft_ai_response` - AI-powered email response drafting

## Agent Command Router

### `crm.api.agent.run`
Central command router for agentic operations. Supported commands:

#### Email Commands
- `email.triage` - AI-powered email triage
  ```json
  {
    "command": "email.triage",
    "params": {
      "communication_name": "COMM-2025-00001"
    }
  }
  ```

- `email.draft_ai` - AI-powered response drafting
  ```json
  {
    "command": "email.draft_ai", 
    "params": {
      "communication_name": "COMM-2025-00001",
      "tone": "professional",
      "include_context": true
    }
  }
  ```

- `email.draft` - Create manual draft
  ```json
  {
    "command": "email.draft",
    "params": {
      "reference_doctype": "CRM Lead",
      "reference_name": "CRM-LEAD-2025-00001", 
      "to": "client@example.com",
      "subject": "Follow up",
      "html": "<p>Email content</p>"
    }
  }
  ```

- `email.send` - Send email
  ```json
  {
    "command": "email.send",
    "params": {
      "communication_name": "COMM-2025-00001"
    }
  }
  ```

- `email.link_provider_ids` - Link external IDs
  ```json
  {
    "command": "email.link_provider_ids",
    "params": {
      "communication_name": "COMM-2025-00001",
      "provider": "gmail",
      "provider_message_id": "msg_123",
      "provider_thread_id": "thread_456"
    }
  }
  ```

## Settings & Configuration
- `crm.api.settings.create_email_account` - Create email account
- `crm.api.settings.get_settings` - Get app settings
- `crm.api.settings.update_settings` - Update settings

## Notifications
- `crm.api.notifications.get_notifications` - Get user notifications
- `crm.api.notifications.mark_read` - Mark notification as read

## Session Management
- `crm.api.session.get_session_info` - Get session details
- `crm.api.session.refresh_session` - Refresh session

## Views & UI
- `crm.api.views.get_dashboard_data` - Get dashboard data
- `crm.api.views.get_kanban_data` - Get kanban board data

## Demo & Testing
- `crm.api.demo.create_sample_data` - Create demo data
- `crm.api.demo.clear_sample_data` - Clear demo data

## WhatsApp Integration
- `crm.api.whatsapp.send_message` - Send WhatsApp message
- `crm.api.whatsapp.get_messages` - Get WhatsApp messages

## Authentication
All API calls require authentication via:
- API Key + Secret in Authorization header: `Authorization: token KEY:SECRET`
- Or session-based auth for web interface

## Error Handling
- 401: Unauthorized (invalid credentials)
- 403: Forbidden (insufficient permissions)  
- 404: Not found
- 422: Validation error
- 500: Internal server error

## Rate Limiting
- 100 requests per minute per API key
- 1000 requests per hour per user

## Webhooks
- `crm_email_draft_created` - Fired when AI draft is created
- `crm_lead_status_changed` - Fired when lead status changes
- `crm_activity_created` - Fired when activity is created
