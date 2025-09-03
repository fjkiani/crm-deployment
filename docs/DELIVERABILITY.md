# Email Deliverability Runbook (SPF/DKIM/DMARC)

## Goal
Achieve SPF, DKIM, DMARC = PASS; reduce spam placement; enable monitoring.

## 1) Prereqs
- Sending identity: the Email Account configured in CRM (e.g., `fahad@crispro.ai`).
- Access to DNS for the sending domain (e.g., `crispro.ai`).
- If using Google Workspace: Admin access to verify domain and get DKIM.

## 2) SPF
Add (or edit) TXT record at root (`@`):
```
v=spf1 include:_spf.google.com ~all
```
Notes:
- If sending via another provider, include their mechanism (e.g., `include:sendgrid.net`).
- Only one SPF TXT at root. Merge mechanisms if needed.

## 3) DKIM
- If Google Workspace: Admin Console → Apps → Gmail → Authenticate email → Generate DKIM → add CNAME(s) as instructed.
- For other providers: publish the provided DKIM selector CNAMEs.
- Verify DKIM after DNS propagates; rotate keys periodically.

## 4) DMARC
Add TXT at `_dmarc`:
```
v=DMARC1; p=none; rua=mailto:dmarc@<your-domain>; ruf=mailto:dmarc@<your-domain>; fo=1; adkim=s; aspf=s
```
Notes:
- Start with `p=none` for monitoring. Move to `p=quarantine` after testing.
- `adkim=s`, `aspf=s` enforce strict alignment.

## 5) Alignment
- Ensure the From domain equals the domain authenticated by SPF/DKIM.
- In CRM, set the Email Account sender to the authenticating mailbox (avoid mismatched aliases during warm-up).

## 6) Monitoring & Warm-up
- Google Postmaster Tools: add domain, verify DNS.
- Seed testing: send to Gmail + Outlook test inboxes; check headers.
- Ramp volume gradually; keep complaint rate low.

## 7) Content & List Hygiene
- Plain-language subject; low link/image ratio initially; avoid heavy tracking.
- Unsubscribe link if bulk; honor bounces/complaints; validate emails on import.

## 8) Verification Checklist
- SPF: PASS (check `Received-SPF` in headers)
- DKIM: PASS (check `DKIM-Signature` and `Authentication-Results`)
- DMARC: PASS (check `Authentication-Results`)
- Inbox placement improves on seed accounts

## 9) Troubleshooting
- Multiple SPF TXT: consolidate into one.
- DKIM fail: selector missing or CNAME not propagated.
- DMARC fail: From domain not aligned with SPF/DKIM.
- Still spam: reduce links/images, use consistent sending pattern, increase engagement.

## 10) CRM Settings Tips
- Use the actual mailbox as sender (avoid `Administrator <alias@other-domain>`).
- Configure a default signature; keep it simple during warm-up.
- If external provider sends (EAIA via Gmail), sync Message-ID/Thread-ID to `Communication`.
