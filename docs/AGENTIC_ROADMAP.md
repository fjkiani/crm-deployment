# Agentic CRM Roadmap (A→Z)

## Goals
- Proactive, AI-assisted CRM that automates intake, routing, outreach, and follow-ups.

## Phases
1) Data foundation
- Ensure audit fields across DocTypes; enrich Lead/Deal with signals
- Add webhooks for external sources (ads/web forms) → Lead ingest

2) Sensing and enrichment
- Auto-enrich Leads (company info, emails, risk) via 3rd parties
- Deduplicate and merge

3) Reasoning and routing
- Lead scoring (model), auto-assign () based on load/territory
- SLA-aware reminders using 

4) Action generation
- Generate suggested next_steps per Lead/Deal
- Draft emails/WhatsApp, call scripts; schedule tasks

5) Loop closure
- Track outcomes (opens/replies/calls) → adjust score/next actions
- Escalations when SLA breached

6) UX integration
- Add Assistant panel in  (frontend store + components)
- Server methods:  to orchestrate steps

## Implementation Notes
- Use existing  to trigger agent
- Use background jobs for scoring/enrichment
- Log actions on  and Activities
- Guard with roles and feature flag in Settings
