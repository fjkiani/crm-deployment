"""
Deliverability Engine
=====================
Ensures emails land in inbox, not spam.

Components:
  1. Domain Rotation  — rotate across N sending domains per campaign
  2. Warm-Up Tracker  — new domains ramp from 5 → 50 emails/day over 30 days
  3. Rate Limiter     — per-domain daily send limits with backpressure
  4. Headers          — RFC 8058 List-Unsubscribe-Post on every email
  5. Sender Health    — bounce rate, complaint tracking per domain
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Domain Pool ───────────────────────────────────────────────────────────────

class DomainPool:
    """Manages a pool of sending domains with rotation, warm-up, and rate limits."""

    def __init__(self):
        # Load from env: SEND_DOMAINS="nyx.io,mail.nyx.io,outreach.nyx.io"
        domains_str = os.getenv("SEND_DOMAINS", "")
        self.domains = [d.strip() for d in domains_str.split(",") if d.strip()]

        if not self.domains:
            # Fallback to primary SMTP user domain
            smtp_user = os.getenv("GMAIL_USER", os.getenv("SMTP_USER", ""))
            if smtp_user and "@" in smtp_user:
                self.domains = [smtp_user.split("@")[1]]

        # State: per-domain tracking (in production, persist to Redis/DB)
        self._state: Dict[str, Dict] = {}
        for d in self.domains:
            self._state[d] = {
                "created_at": os.getenv(f"DOMAIN_{d.replace('.','_').upper()}_CREATED", datetime.now().isoformat()),
                "sends_today": 0,
                "sends_total": 0,
                "bounces": 0,
                "complaints": 0,
                "last_send": None,
                "paused": False,
            }

    def get_next_domain(self) -> Optional[str]:
        """Round-robin domain selection, skipping paused/exhausted domains.

        Returns:
            Best available domain, or None if all exhausted
        """
        available = []
        for domain in self.domains:
            state = self._state[domain]
            if state["paused"]:
                continue
            limit = self._daily_limit(domain)
            if state["sends_today"] >= limit:
                continue
            available.append((domain, state["sends_today"]))

        if not available:
            return None

        # Return the domain with fewest sends today (load balance)
        available.sort(key=lambda x: x[1])
        return available[0][0]

    def record_send(self, domain: str):
        """Record a successful send for rate tracking."""
        if domain in self._state:
            self._state[domain]["sends_today"] += 1
            self._state[domain]["sends_total"] += 1
            self._state[domain]["last_send"] = datetime.now().isoformat()

    def record_bounce(self, domain: str):
        """Record a bounce event."""
        if domain in self._state:
            self._state[domain]["bounces"] += 1
            # Auto-pause if bounce rate > 5%
            total = self._state[domain]["sends_total"]
            bounces = self._state[domain]["bounces"]
            if total > 20 and (bounces / total) > 0.05:
                self._state[domain]["paused"] = True
                logger.warning(f"🛑 Domain {domain} auto-paused: bounce rate {bounces/total:.1%}")

    def record_complaint(self, domain: str):
        """Record a spam complaint."""
        if domain in self._state:
            self._state[domain]["complaints"] += 1
            # Auto-pause if complaint rate > 0.1%
            total = self._state[domain]["sends_total"]
            complaints = self._state[domain]["complaints"]
            if total > 50 and (complaints / total) > 0.001:
                self._state[domain]["paused"] = True
                logger.warning(f"🛑 Domain {domain} auto-paused: complaint rate {complaints/total:.3%}")

    def reset_daily_counts(self):
        """Called by daily cron to reset send counts."""
        for domain in self._state:
            self._state[domain]["sends_today"] = 0

    def _daily_limit(self, domain: str) -> int:
        """Calculate daily send limit based on warm-up age.

        Warm-up schedule:
          Day 1-3:  5 emails/day
          Day 4-7:  10 emails/day
          Day 8-14: 25 emails/day
          Day 15-30: 40 emails/day
          Day 31+:  50 emails/day (max)
        """
        try:
            created = datetime.fromisoformat(self._state[domain]["created_at"])
            age_days = (datetime.now() - created).days
        except (KeyError, ValueError):
            age_days = 0

        if age_days <= 3:
            return 5
        elif age_days <= 7:
            return 10
        elif age_days <= 14:
            return 25
        elif age_days <= 30:
            return 40
        else:
            return 50

    def get_health(self) -> Dict[str, Dict]:
        """Return health stats for all domains."""
        result = {}
        for domain in self.domains:
            state = self._state[domain]
            total = state["sends_total"] or 1  # avoid div by zero
            result[domain] = {
                "status": "paused" if state["paused"] else "active",
                "daily_limit": self._daily_limit(domain),
                "sends_today": state["sends_today"],
                "sends_total": state["sends_total"],
                "bounce_rate": round(state["bounces"] / total, 4),
                "complaint_rate": round(state["complaints"] / total, 4),
                "last_send": state["last_send"],
            }
        return result


# ── Email Headers ─────────────────────────────────────────────────────────────

def get_deliverability_headers(from_domain: str, lead_email: str = "") -> Dict[str, str]:
    """Generate RFC-compliant headers for deliverability.

    Includes:
    - List-Unsubscribe (RFC 2369)
    - List-Unsubscribe-Post (RFC 8058) — one-click unsubscribe
    - Feedback-ID for complaint tracking
    - X-Nyx-Campaign for tracking
    """
    unsubscribe_url = os.getenv("UNSUBSCRIBE_URL", f"https://{from_domain}/unsubscribe")

    return {
        "List-Unsubscribe": f"<{unsubscribe_url}?email={lead_email}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        "Feedback-ID": f"nyx:{from_domain}:{datetime.now().strftime('%Y%m%d')}",
        "X-Nyx-Campaign": f"siege-{datetime.now().strftime('%Y%m%d')}",
        "Precedence": "bulk",
    }


# ── Send with Deliverability ─────────────────────────────────────────────────

# Singleton pool
_pool: Optional[DomainPool] = None


def get_pool() -> DomainPool:
    """Get or create the global domain pool singleton."""
    global _pool
    if _pool is None:
        _pool = DomainPool()
    return _pool


def send_with_deliverability(
    to_email: str,
    subject: str,
    body: str,
    reply_to: str = "",
) -> Dict:
    """Send an email with full deliverability protections.

    1. Picks the best available domain (warm-up aware, rate limited)
    2. Injects RFC 8058 unsubscribe headers
    3. Records send for tracking
    4. Returns send result with domain used

    Args:
        to_email: Recipient email
        subject: Email subject
        body: Email body
        reply_to: Optional reply-to address
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    pool = get_pool()
    domain = pool.get_next_domain()

    if not domain:
        return {
            "sent": False,
            "error": "All sending domains exhausted or paused",
            "health": pool.get_health(),
        }

    # Build SMTP credentials (fallback to primary)
    smtp_user = os.getenv("GMAIL_USER", os.getenv("SMTP_USER", ""))
    smtp_pass = os.getenv("GMAIL_APP_PASSWORD", os.getenv("SMTP_PASS", ""))
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not (smtp_user and smtp_pass):
        return {"sent": False, "error": "No SMTP credentials configured"}

    # Build email with deliverability headers
    msg = MIMEMultipart()
    msg["From"] = f"Nyx <noreply@{domain}>" if domain != smtp_user.split("@")[-1] else smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to

    # Add deliverability headers
    headers = get_deliverability_headers(domain, to_email)
    for key, value in headers.items():
        msg[key] = value

    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, [to_email], msg.as_string())

        pool.record_send(domain)
        logger.info(f"📬 SENT via {domain}: {to_email} ({pool._state[domain]['sends_today']}/{pool._daily_limit(domain)} today)")

        return {
            "sent": True,
            "to": to_email,
            "domain": domain,
            "sends_today": pool._state[domain]["sends_today"],
            "daily_limit": pool._daily_limit(domain),
        }

    except Exception as e:
        logger.error(f"Send failed via {domain}: {e}")
        # Check if bounce
        err_str = str(e).lower()
        if any(w in err_str for w in ["bounce", "rejected", "invalid", "550", "551", "552", "553"]):
            pool.record_bounce(domain)

        return {"sent": False, "error": str(e), "domain": domain}
