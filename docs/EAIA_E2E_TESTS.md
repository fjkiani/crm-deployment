### EAIA x CRM Email E2E Checklist

1) Migrate
- Deploy latest code; run migrate; clear cache; restart.

2) Create Email Account
- Use `crm.api.settings.create_email_account` for Gmail/Outlook.

3) Inbound
- Send an email to the mailbox. Confirm `Communication` is created and linked (Lead/Contact).

4) EAIA triage
- Run EAIA ingest/triage. Post a draft via `crm.api.agent.run` email.draft.
- Check realtime event; confirm draft appears in CRM.

5) Approve & Send
- Approve draft; call `crm.api.agent.run` email.send.
- Verify sent status; optional: link provider IDs (`email.link_provider_ids`).

6) Thread context
- Call `crm.api.email.thread_context` for the doc or a communication and verify chronological history.


